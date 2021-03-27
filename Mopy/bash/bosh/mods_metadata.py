# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from __future__ import division

import io
from collections import defaultdict, OrderedDict

from ._mergeability import is_esl_capable
from .. import balt, bolt, bush, bass, load_order
from ..bolt import dict_sort, structs_cache, SubProgress
from ..brec import ModReader, SubrecordBlob
from ..exception import CancelError
from ..mod_files import ModHeaderReader

_wrld_types = frozenset((b'CELL', b'WRLD'))

# BashTags dir ----------------------------------------------------------------
def get_tags_from_dir(plugin_name):
    """Retrieves a tuple containing a set of added and a set of deleted
    tags from the 'Data/BashTags/PLUGIN_NAME.txt' file, if it is
    present.

    :param plugin_name: The name of the plugin to check the tag file for.
    :return: A tuple containing two sets of added and deleted tags."""
    # Check if the file even exists first
    tag_files_dir = bass.dirs[u'tag_files']
    tag_file = tag_files_dir.join(plugin_name.body + u'.txt')
    if not tag_file.isfile(): return set(), set()
    removed, added = set(), set()
    # BashTags files must be in UTF-8 (or ASCII, obviously)
    with tag_file.open(u'r', encoding=u'utf-8') as ins:
        for tag_line in ins:
            # Strip out comments and skip lines that are empty as a result
            tag_line = tag_line.split(u'#')[0].strip()
            if not tag_line: continue
            for tag_entry in tag_line.split(u','):
                # Guard against things (e.g. typos) like 'TagA,,TagB'
                if not tag_entry: continue
                tag_entry = tag_entry.strip()
                # If it starts with a minus, it's removing a tag
                if tag_entry[0] == u'-':
                    # Guard against a typo like '- C.Water'
                    removed.add(tag_entry[1:].strip())
                else:
                    added.add(tag_entry)
    return added, removed

def save_tags_to_dir(plugin_name, plugin_tag_diff):
    """Compares plugin_tags to plugin_old_tags and saves the diff to
    Data/BashTags/PLUGIN_NAME.txt.

    :param plugin_name: The name of the plugin to modify the tag file for.
    :param plugin_tag_diff: A tuple of two sets, as returned by diff_tags,
        representing a diff of all bash tags currently applied to the
        plugin in question vs. all bash tags applied to the plugin
        by its description and the LOOT masterlist / userlist.."""
    tag_files_dir = bass.dirs[u'tag_files']
    tag_files_dir.makedirs()
    tag_file = tag_files_dir.join(plugin_name.body + u'.txt')
    # Calculate the diff and ignore the minus when sorting the result
    tag_diff_add, tag_diff_del = plugin_tag_diff
    processed_diff = sorted(tag_diff_add | {u'-' + t for t in tag_diff_del},
                            key=lambda t: t[1:] if t[0] == u'-' else t)
    # While BashTags files can be UTF-8, our generated files are only ever
    # going to be ASCII, so write them with that encoding
    with tag_file.open(u'w', encoding=u'ascii') as out:
        # Stick a header in there to indicate that it's machine-generated
        # Also print the version, which could be helpful
        out.write(u'# Generated by Wrye Bash %s\n' % bass.AppVersion)
        out.write(u', '.join(processed_diff) + u'\n')

def diff_tags(plugin_new_tags, plugin_old_tags):
    """Returns two sets, the first containing all added tags and the second all
    removed tags."""
    return plugin_new_tags - plugin_old_tags, plugin_old_tags - plugin_new_tags

#--Plugin Checker -------------------------------------------------------------
_cleaning_wiki_url = (u'[[!https://tes5edit.github.io/docs/7-mod-cleaning-and'
                      u'-error-checking.html|Tome of xEdit]]')

def checkMods(mc_parent, showModList=False, showCRC=False, showVersion=True,
              scan_plugins=True):
    """Checks currently loaded mods for certain errors / warnings.
    mod_checker should be the instance of PluginChecker, to scan."""
    # Setup some commonly used collections of plugin info
    from . import modInfos
    full_acti = load_order.cached_active_tuple()
    plugin_to_acti_index = {p: i for i, p in enumerate(full_acti)}
    all_present_minfs = [modInfos[x] for x in load_order.cached_lo_tuple()]
    all_active_plugins = set(full_acti)
    game_master_name = bush.game.master_file
    vanilla_masters = bush.game.bethDataFiles
    # All log operations that put FormIDs into the log must do it relative to
    # the entire load order and set this to True
    fids_in_log = False
    log = bolt.LogFile(io.StringIO())
    # -------------------------------------------------------------------------
    # The header we'll be showing at the start of the log. Separate so that we
    # can check if the log is empty
    log_header = u'= ' + _(u'Check Plugins') + u'\n'
    log_header += _(u'This is a report of any problems Wrye Bash was able to '
                    u'identify in your currently installed plugins.')
    # -------------------------------------------------------------------------
    # Check for ESL-capable plugins that aren't ESL-flagged.
    can_esl_flag = modInfos.mergeable if bush.game.check_esl else set()
    # -------------------------------------------------------------------------
    # Check for ESL-flagged plugins that aren't ESL-capable.
    remove_esl_flag = set()
    if bush.game.check_esl:
        for m, modinf in modInfos.iteritems():
            if not modinf.is_esl():
                continue # we check .esl extension and ESL flagged mods
            if not is_esl_capable(modinf, modInfos, reasons=None):
                remove_esl_flag.add(m)
    # -------------------------------------------------------------------------
    # Check for mergeable plugins that aren't merged into a BP.
    can_merge = ((all_active_plugins & modInfos.mergeable)
                 if not bush.game.check_esl else set())
    # Don't bug users to merge NoMerge-tagged plugins
    for mod in tuple(can_merge):
        if u'NoMerge' in modInfos[mod].getBashTags():
            can_merge.discard(mod)
    # -------------------------------------------------------------------------
    # Check for Deactivate-tagged plugins that are active and
    # MustBeActiveIfImported-tagged plugins that are imported, but inactive.
    should_deactivate = []
    should_activate = []
    for p_minf in all_present_minfs:
        p_ci_key = p_minf.ci_key
        p_active = p_ci_key in all_active_plugins
        p_imported = p_ci_key in modInfos.imported
        p_tags = p_minf.getBashTags()
        if u'Deactivate' in p_tags and p_active:
            should_deactivate.append(p_ci_key)
        if u'MustBeActiveIfImported' in p_tags and not p_active and p_imported:
            should_activate.append(p_ci_key)
    # -------------------------------------------------------------------------
    # Check for missing or delinquent masters
    seen_plugins = set()
    p_missing_masters = set()
    p_delinquent_masters = set()
    for p in load_order.cached_active_tuple():
        for p_master in modInfos[p].masterNames:
            if p_master not in all_active_plugins:
                p_missing_masters.add(p)
            if p_master not in seen_plugins:
                p_delinquent_masters.add(p)
        seen_plugins.add(p)
    # -------------------------------------------------------------------------
    # Check for plugins with invalid TES4 version.
    valid_vers = bush.game.Esp.validHeaderVersions
    invalid_tes4_versions = {x: unicode(round(modInfos[x].header.version, 6))
                             for x in all_active_plugins if round(
            modInfos[x].header.version, 6) not in valid_vers}
    # -------------------------------------------------------------------------
    # Check for cleaning information from LOOT.
    cleaning_messages = {}
    scan_for_cleaning = set()
    dirty_msgs = [(m.ci_key, m.getDirtyMessage()) for m in all_present_minfs]
    for x, y in dirty_msgs:
        if y[0]:
            cleaning_messages[x] = y[1]
        elif scan_plugins:
            scan_for_cleaning.add(x)
    # -------------------------------------------------------------------------
    # Scan plugins to collect data for more detailed analysis.
    scanning_canceled = False
    all_deleted_refs = defaultdict(list) # ci_key -> list[fid]
    all_deleted_navms = defaultdict(list) # ci_key -> list[fid]
    all_deleted_others = defaultdict(list) # ci_key -> list[fid]
    # fid -> (is_injected, orig_plugin, list[(eid, sig, plugin)])
    record_type_collisions = {}
    # fid -> (orig_plugin, list[(eid, sig, plugin)])
    probable_injected_collisions = {}
    if scan_plugins:
        progress = None
        try:
            # Extract data for all plugins (we'll need the context from all of
            # them, even the game master)
            progress = balt.Progress(
                _(u'Checking Plugins...'), u'\n' + u' ' * 60,
                parent=mc_parent, abort=True)
            load_progress = SubProgress(progress, 0, 0.7)
            load_progress.setFull(len(all_present_minfs))
            all_extracted_data = OrderedDict() # PY3: dict
            for i, present_minf in enumerate(all_present_minfs):
                mod_progress = SubProgress(load_progress, i, i + 1)
                ext_data = ModHeaderReader.extract_mod_data(present_minf,
                                                            mod_progress)
                all_extracted_data[present_minf.ci_key] = ext_data
            # Run over all plugin data once for efficiency, collecing
            # information such as deleted records and overrides
            scan_progress = SubProgress(progress, 0.7, 0.9)
            scan_progress.setFull(len(all_extracted_data))
            all_ref_types = bush.game.Esp.reference_types
            # Temporary place to collect (eid, sig, plugin)-lists
            all_record_versions = defaultdict(list)
            for i, (p_ci_key, ext_data) in enumerate(
                    all_extracted_data.iteritems()):
                scan_progress(i, (_(u'Scanning: %s') % p_ci_key))
                # Two situations where we can skip checking deleted records:
                # 1. The game master can't have deleted records (deleting a
                #    record from the master file that introduced it just
                #    removes the record from existence entirely).
                # 2. If we have a LOOT report for a plugin, we can skip every
                #    deleted reference and deleted navmesh and just use the
                #    LOOT report.
                scan_deleted = (p_ci_key != game_master_name and
                                p_ci_key in scan_for_cleaning)
                # We have to skip checking overrides if the plugin is inactive
                # because a whole-LO FormID is not a valid concept for inactive
                # plugins. Plus, collisions from inactive plugins are either
                # harmless (if the plugin really is inactive) or will show up
                # in the BP (if the plugin is actually merged into the BP).
                scan_overrides = p_ci_key in all_active_plugins
                deleted_refrs = all_deleted_refs[p_ci_key]
                deleted_refrs_append = deleted_refrs.append
                deleted_navms = all_deleted_navms[p_ci_key]
                deleted_navms_append = deleted_navms.append
                deleted_others = all_deleted_others[p_ci_key]
                deleted_others_append = deleted_others.append
                p_masters = modInfos[p_ci_key].masterNames + (p_ci_key,)
                p_num_masters = len(p_masters)
                for r, d in ext_data.iteritems():
                    for r_fid, (r_header, r_eid) in d.iteritems():
                        if scan_deleted:
                            # Check the deleted flag - unpacking flags is too
                            # expensive
                            if r_header.flags1 & 0x00000020:
                                w_rec_type = r_header.recType
                                if w_rec_type == b'NAVM':
                                    deleted_navms_append(r_fid)
                                elif w_rec_type in all_ref_types:
                                    deleted_refrs_append(r_fid)
                                else:
                                    deleted_others_append(r_fid)
                        r_mod_index = r_fid >> 24
                        # p_masters includes self, so >=
                        is_hitme = r_mod_index >= p_num_masters
                        if scan_overrides:
                            # Convert into a load order FormID - ugly but fast,
                            # inlined and hand-optmized from various methods.
                            # Calling them would be way too slow.
                            # PY3: drop the int() call
                            lo_fid = int(
                                r_fid & 0xFFFFFF | plugin_to_acti_index[
                                    p_masters[p_num_masters - 1 if is_hitme
                                              else r_mod_index]] << 24)
                            all_record_versions[lo_fid].append(
                                (r_eid, r_header.recType, p_ci_key))
            # Check for record type collisions, i.e. overrides where the record
            # type of at least one override does not match the base record's
            # type and probable injected collisions, i.e. injected records
            # where the EDID of at least one version does not match the EDIDs
            # of the other versions
            collision_progress = SubProgress(progress, 0.9, 1)
            # We can't get an accurate progress bar here, because the loop
            # below is far too hot. Instead, at least make sure the progress
            # bar updates on each collision by bumping the state.
            collision_progress.setFull(len(all_active_plugins))
            prog_msg = u'{}\n%s'.format(_(u'Looking for collisions...'))
            num_collisions = 0
            collision_progress(num_collisions, prog_msg % game_master_name)
            for r_fid, r_versions in all_record_versions.iteritems():
                first_eid, first_sig, first_plugin = r_versions[0]
                # These FormIDs are whole-LO and HITMEs are truncated, so this
                # is safe
                orig_plugin = full_acti[r_fid >> 24]
                # Record versions are sorted by load order, so if the first
                # version's originating plugin does not match the plugin that
                # the whole-LO FormID points to, this record must be injected
                is_injected = orig_plugin != first_plugin
                definite_collision = False
                probable_collision = False
                for r_eid, r_sig, _r_plugin in r_versions[1:]:
                    if first_sig != r_sig:
                        # At least one override has a different record type,
                        # this is for sure a collision.
                        definite_collision = True
                        break
                    if is_injected and first_eid != r_eid:
                        # This is an injected record and at least one override
                        # has a different EDID, this is probably a collision.
                        # However, we can't break because there might also be
                        # definite collision with a version after this one.
                        probable_collision = True
                if definite_collision:
                    num_collisions += 1
                    record_type_collisions[r_fid] = (is_injected, orig_plugin,
                                                     r_versions)
                    collision_progress(num_collisions, prog_msg % orig_plugin)
                elif probable_collision:
                    num_collisions += 1
                    probable_injected_collisions[r_fid] = (orig_plugin,
                                                           r_versions)
                    collision_progress(num_collisions, prog_msg % orig_plugin)
        except CancelError:
            scanning_canceled = True
        finally:
            if progress:
                progress.Destroy()
    # -------------------------------------------------------------------------
    # Check for deleted references
    if all_deleted_refs:
        for p_ci_key, deleted_refrs in all_deleted_refs.iteritems():
            if deleted_refrs:
                num_deleted = len(deleted_refrs)
                if num_deleted == 1: # I hate natural languages :/
                    del_msg = _(u'1 deleted reference')
                else:
                    del_msg = _(u'%d deleted references') % num_deleted
                cleaning_messages[p_ci_key] = del_msg
    # -------------------------------------------------------------------------
    # Check for deleted navmeshes
    deleted_navmeshes = {}
    if all_deleted_navms:
        for p_ci_key, deleted_navms in all_deleted_navms.iteritems():
            # Deleted navmeshes can't and shouldn't be fixed in vanilla files,
            # so don't show warnings for them
            plugin_is_vanilla = p_ci_key in vanilla_masters
            if deleted_navms and not plugin_is_vanilla:
                num_deleted = len(deleted_navms)
                if num_deleted == 1:
                    del_msg = _(u'1 deleted navmesh')
                else:
                    del_msg = _(u'%d deleted navmeshes') % num_deleted
                deleted_navmeshes[p_ci_key] = del_msg
    # -------------------------------------------------------------------------
    # Check for deleted base records
    deleted_base_recs = {}
    if all_deleted_others:
        for p_ci_key, deleted_others in all_deleted_others.iteritems():
            # Deleted navmeshes can't and shouldn't be fixed in vanilla files,
            # so don't show warnings for them
            plugin_is_vanilla = p_ci_key in vanilla_masters
            if deleted_others and not plugin_is_vanilla:
                num_deleted = len(deleted_others)
                if num_deleted == 1:
                    del_msg = _(u'1 deleted base record')
                else:
                    del_msg = _(u'%d deleted base records') % num_deleted
                deleted_base_recs[p_ci_key] = del_msg
    # -------------------------------------------------------------------------
    # Some helpers for building the log
    def log_plugins(plugin_list):
        """Logs a simple list of plugins."""
        for p in sorted(plugin_list):
            log(u'* __%s__' % p)
    def log_plugin_messages(plugin_dict):
        """Logs a list of plugins with a message after each plugin."""
        for p, p_msg in dict_sort(plugin_dict):
            log(u'* __%s:__  %s' % (p, p_msg))
    if bush.game.has_esl:
        # Need to undo the offset we applied to sort ESLs after regulars
        sort_offset = load_order.max_espms() - 1
        def format_fid(whole_lo_fid, fid_orig_plugin):
            """Formats a whole-LO FormID, which can exceed normal FormID limits
            (e.g. 211000800 is perfectly fine in a load order with ESLs), so
            that xEdit (and the game) can understand it."""
            orig_minf = modInfos[fid_orig_plugin]
            proper_index = orig_minf.real_index()
            if orig_minf.is_esl():
                return u'FE%03X%03X' % (proper_index - sort_offset,
                                        whole_lo_fid & 0x00000FFF)
            else:
                return u'%02X%06X' % (proper_index, whole_lo_fid & 0x00FFFFFF)
    else:
        def format_fid(whole_lo_fid, _fid_orig_plugin):
            # For non-ESL games simple hexadecimal formatting will do
            return u'%08X' % whole_lo_fid
    def log_collision(coll_fid, coll_inj, coll_plugin, coll_versions):
        """Logs a single collision with the specified FormID, injected status,
        origin plugin and collision info."""
        # FormIDs must be in long format at this point
        proper_fid = format_fid(coll_fid, coll_plugin)
        if coll_inj:
            log(u'* ' + _(u'%s injected into %s, colliding versions:')
                % (proper_fid, coll_plugin))
        else:
            log(u'* ' + _(u'%s from %s, colliding versions:')
                % (proper_fid, coll_plugin))
        for ver_eid, ver_sig, ver_orig_plugin in coll_versions:
            fmt_record = u'%s [%s:%s]' % (ver_eid, ver_sig, proper_fid)
            # Mark the base record if the record wasn't injected
            if not coll_inj and ver_orig_plugin == coll_plugin:
                log(u'  * ' + _(u'%s from %s (base record)') % (
                    fmt_record, ver_orig_plugin))
            else:
                log(u'  * ' + _(u'%s from %s') % (
                    fmt_record, ver_orig_plugin))
    # -------------------------------------------------------------------------
    # From here on we have data on all plugin problems, so it's purely a matter
    # of building the log
    if scanning_canceled:
        log.setHeader(u'=== ' + _(u'Plugin Loading Canceled'))
        log(_(u'The loading of plugins was canceled and the resulting report '
              u"may not be accurate. You can use the 'Update' button to load "
              u'plugins and generate a new report.'))
    if can_esl_flag:
        log.setHeader(u'=== ' + _(u'ESL Capable'))
        log(_(u'The following plugins could be assigned an ESL flag.'))
        log_plugins(can_esl_flag)
    if remove_esl_flag:
        log.setHeader(u'=== ' + _(u'Incorrect ESL Flag'))
        log(_(u'The following plugins have an ESL flag, but do not qualify. '
              u"Either remove the flag with 'Remove ESL Flag', or "
              u"change the extension to '.esp' if it is '.esl'."))
        log_plugins(remove_esl_flag)
    if can_merge:
        log.setHeader(u'=== ' + _(u'Mergeable'))
        log(_(u'The following plugins are active, but could be merged into '
              u'the Bashed Patch.'))
        log_plugins(can_merge)
    if should_deactivate:
        log.setHeader(u'=== ' + _(u'Deactivate-tagged But Active'))
        log(_(u"The following plugins are tagged with 'Deactivate' and should "
              u'be deactivated and imported into the Bashed Patch.'))
        log_plugins(should_deactivate)
    if should_activate:
        log.setHeader(u'=== '+_(u'MustBeActiveIfImported-tagged But Inactive'))
        log(_(u'The following plugins are tagged with '
              u"'MustBeActiveIfImported' and should be activated if they are "
              u'also imported into the Bashed Patch. They are currently '
              u'imported, but not active.'))
        log_plugins(should_activate)
    if p_missing_masters:
        log.setHeader(_(u'Missing Masters'))
        log(_(u'The following plugins have missing masters and are active. '
              u'This will cause a CTD at the main menu and must be '
              u'corrected.'))
        log_plugins(p_missing_masters)
    if p_delinquent_masters:
        log.setHeader(_(u'Delinquent Masters'))
        log(_(u'The following plugins have delinquent masters, i.e. masters '
              u'that are set to load after their dependent plugins. The game '
              u'will try to force them to load before the dependent plugins, '
              u'which can lead to unpredictable or undefined behavior and '
              u'must be corrected.'))
        log_plugins(p_delinquent_masters)
    if invalid_tes4_versions:
        # Always an ASCII byte string, so this is fine
        p_header_sig = bush.game.Esp.plugin_header_sig.decode(u'ascii')
        ver_list = u', '.join(
            sorted(unicode(v) for v in bush.game.Esp.validHeaderVersions))
        log.setHeader(u'=== ' + _(u'Invalid %s versions') % p_header_sig)
        log(_(u"The following plugins have a %s version that isn't "
              u'recognized as one of the standard versions (%s). This is '
              u'undefined behavior. It can possibly be corrected by resaving '
              u'the plugins in the %s.') % (p_header_sig, ver_list,
                                            bush.game.Ck.long_name))
        log_plugin_messages(invalid_tes4_versions)
    if cleaning_messages:
        log.setHeader(u'=== ' + _(u'Cleaning With %s Needed') %
                      bush.game.Xe.full_name)
        log(_(u'The following plugins have deleted references or other issues '
              u'that can and should be fixed with %(xedit_name)s. Visit the '
              u'%(cleaning_wiki_url)s for more information.') % {
            u'cleaning_wiki_url': _cleaning_wiki_url,
            u'xedit_name': bush.game.Xe.full_name})
        log_plugin_messages(cleaning_messages)
    if deleted_navmeshes:
        log.setHeader(u'=== ' + _(u'Deleted Navmeshes'))
        log(_(u'The following plugins have deleted navmeshes. They will cause '
              u'a CTD if another plugin references the deleted navmesh or a '
              u'nearby navmesh. They can only be fixed manually, which should '
              u'usually be done by the mod author. Failing that, the safest '
              u'course of action is to uninstall the plugin.'))
        log_plugin_messages(deleted_navmeshes)
    if deleted_base_recs:
        log.setHeader(u'=== ' + _(u'Deleted Base Records'))
        log(_(u'The following plugins have deleted base records. If another '
              u'plugin references the deleted record, the resulting behavior '
              u'is undefined. It may CTD, fail to delete the record or do any '
              u'number of other things. They can only be fixed manually, '
              u'which should usually be done by the mod author. Failing that, '
              u'the safest course of action is to uninstall the plugin.'))
        log_plugin_messages(deleted_base_recs)
    if record_type_collisions:
        log.setHeader(u'=== ' + _(u'Record Type Collisions'))
        log(_(u'The following records override each other, but have different '
              u'record types. This is undefined behavior, but will almost '
              u'certainly lead to CTDs. Such conflicts can only be fixed '
              u'manually, which should usually be done by the mod author. '
              u'Failing that, the safest course of action is to uninstall the '
              u'plugin.'))
        fids_in_log = True # PY3: nonlocal, move this into log_collision
        for orig_fid, (is_inj, orig_plugin, coll_info) in dict_sort(
                record_type_collisions):
            log_collision(orig_fid, is_inj, orig_plugin, coll_info)
    if probable_injected_collisions:
        log.setHeader(u'=== ' + _(u'Probable Injected Collisions'))
        log(_(u'The following injected records override each other, but have '
              u'different Editor IDs (EDIDs). This probably means that two '
              u'different injected records have collided, but have the same '
              u'record signature. The resulting behavior depends on what the '
              u'injecting plugins are trying to do with the record, but they '
              u'will most likely not work as intended. Such conflicts can '
              u'only be fixed manually, which should usually be done by the '
              u'mod author. Failing that, the safest course of action is to '
              u'uninstall the plugin '))
        fids_in_log = True
        for orig_fid, (orig_plugin, coll_info) in dict_sort(
                probable_injected_collisions):
            log_collision(orig_fid, True, orig_plugin, coll_info)
    # If we haven't logged anything (remember, the header is a separate
    # variable) then let the user know they have no problems.
    temp_log = log.out.getvalue()
    if not temp_log:
        log.setHeader(u'=== ' + _(u'No Problems Found'))
        if not scan_plugins:
            log(_(u'Wrye Bash did not find any problems with your installed '
                  u'plugins without loading them. Turning on loading of '
                  u'plugins may find more problems.'))
        else:
            log(_(u'Wrye Bash did not find any problems with your installed '
                  u'plugins. Congratulations!'))
    # We already logged missing or delinquent masters up above, so don't
    # duplicate that info in the mod list
    if showModList:
        log(u'\n' + modInfos.getModList(showCRC, showVersion, wtxt=True,
                                        log_problems=False).strip())
    # If the log includes any FormIDs, include a help note in the header
    if fids_in_log:
        log_header += u'\n\n~~%s~~ %s' % (
            _(u'Note that all FormIDs in the report are relative to the '
              u'entire load order.'),
            _(u'If you want to view these FormIDs in %(xedit_name)s, make '
              u'sure to load your entire load order (simply accept the '
              u"'Module Selection' prompt in %(xedit_name)s with OK).") % {
                u'xedit_name': bush.game.Xe.full_name})
    return log_header + u'\n\n' + log.out.getvalue()

#------------------------------------------------------------------------------
class NvidiaFogFixer(object):
    """Fixes cells to avoid nvidia fog problem."""
    def __init__(self,modInfo):
        self.modInfo = modInfo
        self.fixedCells = set()

    def fix_fog(self, progress, __unpacker=structs_cache[u'=12s2f2l2f'].unpack,
                __wrld_types=_wrld_types,
                __packer=structs_cache[u'12s2f2l2f'].pack):
        """Duplicates file, then walks through and edits file as necessary."""
        progress.setFull(self.modInfo.fsize)
        fixedCells = self.fixedCells
        fixedCells.clear()
        #--File stream
        minfo_path = self.modInfo.getPath()
        #--Scan/Edit
        with ModReader(self.modInfo.ci_key, minfo_path.open(u'rb')) as ins:
            with minfo_path.temp.open(u'wb') as  out:
                def copy(bsize):
                    buff = ins.read(bsize)
                    out.write(buff)
                while not ins.atEnd():
                    progress(ins.tell())
                    header = ins.unpackRecHeader()
                    _rsig = header.recType
                    #(type,size,str0,fid,uint2) = ins.unpackRecHeader()
                    out.write(header.pack_head())
                    if _rsig == b'GRUP':
                        if header.groupType != 0: #--Ignore sub-groups
                            pass
                        elif header.label not in __wrld_types:
                            copy(header.blob_size())
                    #--Handle cells
                    elif _rsig == b'CELL':
                        nextRecord = ins.tell() + header.blob_size()
                        while ins.tell() < nextRecord:
                            subrec = SubrecordBlob(ins, _rsig)
                            if subrec.mel_sig == b'XCLL':
                                color, near, far, rotXY, rotZ, fade, clip = \
                                    __unpacker(subrec.mel_data)
                                if not (near or far or clip):
                                    near = 0.0001
                                    subrec.mel_data = __packer(color, near,
                                        far, rotXY, rotZ, fade, clip)
                                    fixedCells.add(header.fid)
                            subrec.packSub(out, subrec.mel_data)
                    #--Non-Cells
                    else:
                        copy(header.blob_size())
        #--Done
        if fixedCells:
            self.modInfo.makeBackup()
            minfo_path.untemp()
            self.modInfo.setmtime(crc_changed=True) # fog fixes
        else:
            minfo_path.temp.remove()
