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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains the Fallout 4 record classes."""
import operator

from ...bolt import Flags
from ...brec import MelBase, MelGroup, AMreHeader, MelSet, MelString, \
    MelStruct, MelNull, MelSimpleArray, AMreLeveledList, MelFid, MelAttx, \
    FID, MelLString, MelUInt8, MelFloat, MelBounds, MelEdid, MelUnloadEvent, \
    MelArray, AMreFlst, MelUInt8Flags, MelSorted, MelGroups, MelShortName, \
    MelUInt32, MelRecord, MelColorO, MelFull, MelBaseR, MelKeywords, MelRace, \
    MelColor, MelSound, MelSoundActivation, MelWaterType, MelAlchEnit, \
    MelActiFlags, MelInteractionKeyword, MelConditions, MelTruncatedStruct, \
    AMelNvnm, ANvnmContext, MelNodeIndex, MelAddnDnam, MelUnion, MelIcons, \
    AttrValDecider, MelSoundPickupDrop, MelEquipmentType, AMelVmad, MelFids, \
    MelDescription, MelEffects, AMelLLItems, MelValueWeight, AVmadContext, \
    MelIcon, MelConditionList, MelPerkData, MelNextPerk, MelSInt8, MelUInt16, \
    MelUInt16Flags, perk_effect_key, MelPerkParamsGroups, PerkEpdfDecider, \
    MelUInt32Flags, BipedFlags, MelArmaShared, MelEnchantment, MelObject, \
    MelIcons2, MelBids, MelBamt, MelTemplateArmor, MelObjectTemplate, \
    MelArtType, MelAspcRdat, MelAspcBnam, PartialLoadDecider, MelSeasons, \
    MelBookText, MelBookDescription, MelInventoryArt, MelUnorderedGroups, \
    MelImageSpaceMod, MelClmtWeatherTypes, MelClmtTiming, MelClmtTextures, \
    MelCobjOutput, AMreWithItems, AMelItems, MelContData, MelSoundClose, \
    MelCpthShared, FormVersionDecider, MelSoundLooping, MelDoorFlags, \
    MelRandomTeleports, MelIco2, MelEqupPnam, MelFlstFids, MelIngredient, \
    MelRelations, MelFactFlags, MelFactRanks, MelOptStruct, MelSInt32, \
    MelFactFids, MelFactVendorInfo, MelReadOnly, MelFurnMarkerData, \
    MelGrasData, MelHdptShared, MelIdleEnam, MelIdleRelatedAnims, \
    MelIdleData, MelCounter, MelIdleTimerSetting, MelIdlmFlags, MelIdlmIdla, \
    AMreImad, MelPartialCounter, perk_distributor, MelImgsCinematic, \
    MelImgsTint, MelIngrEnit, MelDecalData, MelIpctTextureSets, \
    MelIpctSounds, MelIpctHazard, MelIpdsPnam, MelSequential

##: What about texture hashes? I carried discarding them forward from Skyrim,
# but that was due to the 43-44 problems. See also #620.
#------------------------------------------------------------------------------
# Record Elements -------------------------------------------------------------
#------------------------------------------------------------------------------
class MelModel(MelGroup):
    """Represents a model subrecord."""
    # MODB and MODD are no longer used by TES5Edit
    typeSets = {
        b'MODL': (b'MODL', b'MODT', b'MODC', b'MODS', b'MODF'),
        b'MOD2': (b'MOD2', b'MO2T', b'MO2C', b'MO2S', b'MO2F'),
        b'MOD3': (b'MOD3', b'MO3T', b'MO3C', b'MO3S', b'MO3F'),
        b'MOD4': (b'MOD4', b'MO4T', b'MO4C', b'MO4S', b'MO4F'),
        b'MOD5': (b'MOD5', b'MO5T', b'MO5C', b'MO5S', b'MO5F'),
        b'DMDL': (b'DMDL', b'DMDT', b'DMDC', b'DMDS'),
    }

    def __init__(self, mel_sig=b'MODL', attr='model', *, swap_3_4=False,
            always_use_modc=False, skip_5=False):
        """Fallout 4 has a whole lot of model nonsense:

        :param swap_3_4: If True, swaps the third (*C) and fourth (*S)
            elements.
        :param always_use_modc: If True, use MODC for the third (*C) element,
            regardless of what mel_sig is.
        :param skip_5: If True, skip the fifth (*F) element."""
        types = self.__class__.typeSets[mel_sig]
        mdl_elements = [
            MelString(types[0], 'modPath'),
            # Ignore texture hashes - they're only an optimization, plenty
            # of records in Skyrim.esm are missing them
            MelNull(types[1]),
            MelFloat(b'MODC' if always_use_modc else types[2],
                'color_remapping_index'),
            MelFid(types[3], 'material_swap'),
        ]
        if swap_3_4:
            mdl_elements[2], mdl_elements[3] = mdl_elements[3], mdl_elements[2]
        if len(types) == 5 and not skip_5:
            mdl_elements.append(MelBase(types[4], 'unknown_modf'))
        super().__init__(attr, *mdl_elements)

#------------------------------------------------------------------------------
# A distributor config for use with MelObjectTemplate, since MelObjectTemplate
# also contains a FULL subrecord
_object_template_distributor = {
    b'FULL': 'full',
    b'OBTE': {
        b'FULL': 'ot_combinations',
    },
}

#------------------------------------------------------------------------------
class MelAnimationSound(MelFid):
    """Handles the common STCP (Animation Sound) subrecord."""
    def __init__(self):
        super().__init__(b'STCP', 'animation_sound')

#------------------------------------------------------------------------------
class MelAppr(MelSimpleArray):
    """Handles the common APPR (Attach Parent Slots) subrecord."""
    def __init__(self):
        super().__init__('attach_parent_slots', MelFid(b'APPR'))

#------------------------------------------------------------------------------
class MelBod2(MelUInt32Flags):
    """Handles the BOD2 (Biped Body Template) subrecord."""
    _bp_flags = BipedFlags.from_names()

    def __init__(self):
        super().__init__(b'BOD2', 'biped_flags', self._bp_flags)

#------------------------------------------------------------------------------
class MelBoneData(MelGroups):
    """Handles the bone data subrecord complex."""
    def __init__(self):
        super().__init__('bone_data',
            MelUInt32(b'BSMP', 'bone_scale_gender'),
            MelGroups('bone_weight_scales',
                MelString(b'BSMB', 'bone_name'),
                # In the latest version of xEdit's source code, the decoding
                # for this particular part is much more complex - would
                # probably have to require custom code to handle (custom
                # handler for duplicate signatures inside a single MelGroups,
                # plus conditional loading to read one subrecord ahead and
                # check its size). This works fine and is *way* simpler, so not
                # going to bother.
                MelSimpleArray('weight_scale_values', MelFloat(b'BSMS')),
                MelUInt32(b'BMMP', 'bone_modifies_gender'),
            ),
        )

#------------------------------------------------------------------------------
class MelDestructible(MelGroup):
    """Represents a collection of destruction-related subrecords."""
    _dest_header_flags = Flags.from_names('vats_targetable',
                                          'large_actor_destroys')
    _dest_stage_flags = Flags.from_names('cap_damage', 'disable', 'destroy',
                                         'ignore_external_damage',
                                         'becomes_dynamic')

    def __init__(self):
        super().__init__('destructible',
            MelStruct(b'DEST', ['i', '2B', '2s'], 'health', 'count',
                (self._dest_header_flags, 'dest_flags'),
                'dest_unknown'),
            MelResistances(b'DAMC'),
            MelGroups('stages',
                MelStruct(b'DSTD', ['4B', 'i', '2I', 'i'], 'health', 'index',
                          'damage_stage',
                          (self._dest_stage_flags, 'stage_flags'),
                          'self_damage_per_second', (FID, 'explosion'),
                          (FID, 'debris'), 'debris_count'),
                MelString(b'DSTA', 'sequence_name'),
                MelModel(b'DMDL'),
                MelBaseR(b'DSTF', 'dest_end_marker'),
            ),
        )

#------------------------------------------------------------------------------
class MelFtyp(MelFid):
    """Handles the common FTYP (Forced Loc Ref Type) subrecord."""
    def __init__(self):
        super().__init__(b'FTYP', 'forced_loc_ref_type')

#------------------------------------------------------------------------------
class MelItems(AMelItems):
    """Handles the COCT/CNTO/COED subrecords defining items."""

#------------------------------------------------------------------------------
class MelLLItems(AMelLLItems):
    """Handles the LLCT/LVLO/COED subrecords defining leveled list entries."""
    def __init__(self):
        super().__init__(MelStruct(b'LVLO', ['H', '2s', 'I', 'H', 'B', 's'],
            'level', 'unused1', (FID, 'listId'), ('count', 1), 'chance_none',
            'unused2'))

#------------------------------------------------------------------------------
class MelLocation(MelUnion):
    """A PLDT/PLVD (Location) subrecord. Occurs in PACK and FACT."""
    def __init__(self, sub_sig):
        super().__init__({
            (0, 1, 4, 6): MelOptStruct(sub_sig, ['i', 'I', 'i', 'I'],
                'location_type', (FID, 'location_value'), 'location_radius',
                'location_collection_index'),
            (2, 3, 7, 12, 13): MelOptStruct(sub_sig, ['i', '4s', 'i', 'I'],
                'location_type', 'location_value', 'location_radius',
                'location_collection_index'),
            (5, 10, 11): MelOptStruct(sub_sig, ['i', 'I', 'i', 'I'],
                'location_type', 'location_value', 'location_radius',
                'location_collection_index'),
            (8, 9, 14): MelOptStruct(sub_sig, ['3i', 'I'],
                'location_type', 'location_value', 'location_radius',
                'location_collection_index'),
            }, decider=PartialLoadDecider(
                loader=MelSInt32(sub_sig, 'location_type'),
                decider=AttrValDecider('location_type'))
        )

#------------------------------------------------------------------------------
class MelNativeTerminal(MelFid):
    """Handles the common NTRM (Native Terminal) subrecord."""
    def __init__(self):
        super().__init__(b'NTRM', 'native_terminal')

#------------------------------------------------------------------------------
class MelNotesTypeRule(MelSequential):
    """Handles the AACT/KYWD subrecords DNAM (Notes), TNAM (Type) and DATA
    (Attraction Rule)."""
    def __init__(self):
        super().__init__(
            MelString(b'DNAM', 'aact_kywd_notes'),
            MelUInt32(b'TNAM', 'aact_kywd_type'),
            MelFid(b'DATA', 'attraction_rule'),
        )

#------------------------------------------------------------------------------
class MelNvnm(AMelNvnm):
    """Handles the NVNM (Navmesh Geometry) subrecord."""
    class _NvnmContextFo4(ANvnmContext):
        """Provides NVNM context for Fallout 4."""
        max_nvnm_ver = 15
        cover_tri_mapping_has_covers = True
        nvnm_has_waypoints = True

    _nvnm_context_class = _NvnmContextFo4

#------------------------------------------------------------------------------
class MelPreviewTransform(MelFid):
    """Handles the common PTRN (Preview Transform) subrecord."""
    def __init__(self):
        super().__init__(b'PTRN', 'preview_transform')

#------------------------------------------------------------------------------
class MelProperties(MelSorted):
    """Handles the common PRPS (Properites) subrecord."""
    def __init__(self):
        super().__init__(MelArray('properties',
            MelStruct(b'PRPS', ['I', 'f'], (FID, 'prop_actor_value'),
                'prop_value'),
        ))

#------------------------------------------------------------------------------
class MelResistances(MelSorted):
    """Handles a sorted array of resistances. Signatures vary."""
    def __init__(self, res_sig):
        super().__init__(MelArray('resistances',
            MelStruct(res_sig, ['2I'], (FID, 'damage_type'),
                'resistance_value'),
        ), sort_by_attrs='damage_type')

#------------------------------------------------------------------------------
class MelSoundCrafting(MelFid):
    """Handles the common CUSD (Sound - Crafting) subrecord."""
    def __init__(self):
        super().__init__(b'CUSD', 'sound_crafting')

#------------------------------------------------------------------------------
class MelVmad(AMelVmad):
    class _VmadContextFo4(AVmadContext):
        """Provides VMAD context for Fallout 4."""
        max_vmad_ver = 6

    _vmad_context_class = _VmadContextFo4

#------------------------------------------------------------------------------
# Fallout 4 Records -----------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(AMreHeader):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'
    _post_masters_sigs = {b'ONAM', b'SCRN', b'TNAM', b'INTV', b'INCC'}

    melSet = MelSet(
        MelStruct(b'HEDR', [u'f', u'2I'], (u'version', 1.0), u'numRecords',
            (u'nextObject', 0x001)),
        MelNull(b'OFST'), # obsolete
        MelNull(b'DELE'), # obsolete
        AMreHeader.MelAuthor(),
        AMreHeader.MelDescription(),
        AMreHeader.MelMasterNames(),
        MelSimpleArray('overrides', MelFid(b'ONAM')),
        MelBase(b'SCRN', 'screenshot'),
        MelGroups('transient_types',
            MelSimpleArray('unknownTNAM', MelFid(b'TNAM'),
                prelude=MelUInt32(b'TNAM', 'form_type')),
        ),
        MelUInt32(b'INTV', 'unknownINTV'),
        MelUInt32(b'INCC', 'internal_cell_count'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAact(MelRecord):
    """Action."""
    rec_sig = b'AACT'

    melSet = MelSet(
        MelEdid(),
        MelColorO(),
        MelNotesTypeRule(),
        MelFull(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator."""
    rec_sig = b'ACTI'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelAnimationSound(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelProperties(),
        MelNativeTerminal(),
        MelFtyp(),
        MelColor(b'PNAM'),
        MelSound(),
        MelSoundActivation(),
        MelWaterType(),
        MelAttx(),
        MelActiFlags(),
        MelInteractionKeyword(),
        MelTruncatedStruct(b'RADR', ['I', '2f', '2B'], (FID, 'rr_sound_model'),
            'rr_frequency', 'rr_volume', 'rr_starts_active',
            'rr_no_signal_static', old_versions={'I2fB'}),
        MelConditions(),
        MelNvnm(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAddn(MelRecord):
    """Addon Node."""
    rec_sig = b'ADDN'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelNodeIndex(),
        MelSound(),
        MelFid(b'LNAM', 'addon_light'),
        MelAddnDnam(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAech(MelRecord):
    """Audio Effect Chain."""
    rec_sig = b'AECH'

    melSet = MelSet(
        MelEdid(),
        MelGroups('chain_effects',
            MelUInt32(b'KNAM', 'ae_type'),
            MelUnion({
                # BSOverdrive - 'Overdrive'
                0x864804BE: MelStruct(b'DNAM', ['I', '4f'], 'ae_enabled',
                    'od_input_gain', 'od_output_gain', 'od_upper_threshold',
                    'od_lower_threshold'),
                # BSStateVariableFilter - 'State Variable Filter'
                0xEF575F7F: MelStruct(b'DNAM', ['I', '2f', 'I'], 'ae_enabled',
                    'svf_center_freq', 'svf_q_value', 'svf_filter_mode'),
                # BSDelayEffect - 'Delay Effect'
                0x18837B4F: MelStruct(b'DNAM', ['I', '2f', 'I'], 'ae_enabled',
                    'de_feedback_pct', 'de_wet_mix_pct', 'de_delay_ms'),
            }, decider=AttrValDecider('ae_type')),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAlch(MelRecord):
    """Ingestible."""
    rec_sig = b'ALCH'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelKeywords(),
        MelModel(),
        MelIcons(),
        MelSoundPickupDrop(),
        MelEquipmentType(),
        MelSoundCrafting(),
        MelDestructible(),
        MelDescription(),
        MelAlchEnit(),
        MelLString(b'DNAM', 'addiction_name'),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmdl(MelRecord):
    """Aim Model."""
    rec_sig = b'AMDL'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DNAM', ['4f', 'I', '6f', 'I', '4f'], 'cof_min_angle',
            'cof_max_angle', 'cof_increase_per_shot', 'cof_decrease_per_shot',
            'cof_decrease_delay_ms', 'cof_sneak_mult',
            'recoil_diminish_spring_force', 'recoil_diminish_sights_mult',
            'recoil_max_per_shot', 'recoil_min_per_shot', 'recoil_hip_mult',
            'runaway_recoil_shots', 'recoil_arc', 'recoil_arc_rotate',
            'cof_iron_sights_mult', 'base_stability'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammunition."""
    rec_sig = b'AMMO'

    _ammo_flags = Flags.from_names('notNormalWeapon', 'nonPlayable',
        'has_count_based_3d')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelDescription(),
        MelKeywords(),
        MelValueWeight(),
        MelStruct(b'DNAM', ['I', 'B', '3s', 'f', 'I'], (FID, 'projectile'),
            (_ammo_flags, 'flags'), 'unused_dnam', 'damage', 'health'),
        MelShortName(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAnio(MelRecord):
    """Animated Object."""
    rec_sig = b'ANIO'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelUnloadEvent(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAoru(MelRecord):
    """Attraction Rule."""
    rec_sig = b'AORU'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'AOR2', ['3f', '2B', '2s'], 'attraction_radius',
            'attraction_min_delay', 'attraction_max_delay',
            'requires_line_of_sight', 'combat_target', 'unused_aor2'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArma(MelRecord):
    """Armor Addon."""
    rec_sig = b'ARMA'

    melSet = MelSet(
        MelEdid(),
        MelBod2(),
        MelRace(),
        MelArmaShared(MelModel),
        MelBoneData(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor."""
    rec_sig = b'ARMO'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelEnchantment(),
        MelModel(b'MOD2', 'maleWorld', always_use_modc=True, skip_5=True),
        MelIcons('maleIconPath', 'maleSmallIconPath'),
        MelModel(b'MOD4', 'femaleWorld', always_use_modc=True, skip_5=True),
        MelIcons2(),
        MelBod2(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelEquipmentType(),
        MelBids(),
        MelBamt(),
        MelRace(),
        MelKeywords(),
        MelDescription(),
        MelFid(b'INRD', 'instance_naming'),
        MelGroups('addons',
            MelUInt16(b'INDX', 'addon_index'),
            MelFid(b'MODL', 'addon_fid'),
        ),
        MelStruct(b'DATA', ['i', 'f', 'I'], 'value', 'weight', 'health'),
        MelStruct(b'FNAM', ['2H', 'B', '3s'], 'armorRating',
            'base_addon_index', 'stagger_rating', 'unknown_fnam'),
        MelResistances(b'DAMA'),
        MelTemplateArmor(),
        MelAppr(),
        MelObjectTemplate(),
    ).with_distributor(_object_template_distributor)
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArto(MelRecord):
    """Art Object."""
    rec_sig = b'ARTO'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelPreviewTransform(),
        MelKeywords(),
        MelModel(),
        MelArtType(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAspc(MelRecord):
    """Acoustic Space."""
    rec_sig = b'ASPC'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelSound(),
        MelAspcRdat(),
        MelAspcBnam(),
        MelUInt8(b'XTRI', 'aspc_is_interior'),
        MelUInt16(b'WNAM', 'weather_attenuation'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAvif(MelRecord):
    """Actor Value Information."""
    rec_sig = b'AVIF'

    _avif_flags = Flags.from_names(
        (1,  'af_skill'),
        (2,  'af_uses_enum'),
        (3,  'af_dont_allow_script_edits'),
        (4,  'af_is_full_av_cached'),
        (5,  'af_is_permanent_av_cached'),
        (10, 'af_default_to_0'),
        (11, 'af_default_to_1'),
        (12, 'af_default_to_100'),
        (15, 'af_contains_list'),
        (19, 'af_value_less_than_1'),
        (20, 'af_minimum_1'),
        (21, 'af_maximum_10'),
        (22, 'af_maximum_100'),
        (23, 'af_multiply_by_100'),
        (24, 'af_percentage'),
        (26, 'af_damage_is_positive'),
        (27, 'af_god_mode_immune'),
        (28, 'af_harcoded'),
    )

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelLString(b'ANAM', 'abbreviation'),
        MelFloat(b'NAM0', 'avif_default_value'),
        MelUInt32Flags(b'AVFL', 'avif_flags', _avif_flags),
        MelUInt32(b'NAM1', 'avif_type'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBnds(MelRecord):
    """Bendable Spline."""
    rec_sig = b'BNDS'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelStruct(b'DNAM', ['f', '2H', '5f'],'default_num_tiles',
            'default_num_slices', 'default_num_tiles_relative_to_length',
            'default_red', 'default_green', 'default_blue', 'wind_sensibility',
            'wind_flexibility'),
        MelFid(b'TNAM', 'spline_texture'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBook(MelRecord):
    """Book."""
    rec_sig = b'BOOK'

    _book_type_flags = Flags.from_names('advance_actor_value', 'cant_be_taken',
        'add_spell', 'add_perk')

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelBookText(),
        MelSoundPickupDrop(),
        MelKeywords(),
        MelFid(b'FIMD', 'featured_item_message'),
        MelValueWeight(),
        # The book_flags determine what kind of FormID is acceptable for
        # book_teaches, but we don't care about that - only that it is a FormID
        MelStruct(b'DNAM', ['B', '3I'], (_book_type_flags, 'book_flags'),
            (FID,'book_teaches'), 'text_offset_x', 'text_offset_y'),
        MelBookDescription(),
        MelInventoryArt(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBptd(MelRecord):
    """Body Part Data."""
    rec_sig = b'BPTD'

    _bpnd_flags = Flags.from_names('severable', 'hit_reaction',
        'hit_reaction_default', 'explodable', 'cut_meat_cap_sever',
        'on_cripple', 'explodable_absolute_chance', 'show_cripple_geometry')

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelSorted(MelUnorderedGroups('body_part_list',
            MelLString(b'BPTN', 'part_name'),
            MelString(b'BPNN', 'part_node'),
            MelString(b'BPNT', 'vats_target'),
            MelStruct(b'BPND',
                ['f', '2I', 'f', '2I', '7f', '2I', 'f', '3B', 'I', '8B', '4I',
                 'f', '2B'], 'bpnd_damage_mult',
                (FID, 'bpnd_explodable_debris'),
                (FID, 'bpnd_explodable_explosion'),
                'bpnd_explodable_debris_scale', (FID, 'bpnd_severable_debris'),
                (FID, 'bpnd_severable_explosion'),
                'bpnd_severable_debris_scale', 'bpnd_cut_min', 'bpnd_cut_max',
                'bpnd_cut_radius', 'bpnd_gore_effects_local_rotate_x',
                'bpnd_gore_effects_local_rotate_y', 'bpnd_cut_tesselation',
                (FID, 'bpnd_severable_impact_dataset'),
                (FID, 'bpnd_explodable_impact_dataset'),
                'bpnd_explodable_limb_replacement_scale',
                (_bpnd_flags, 'bpnd_flags'), 'bpnd_part_type',
                'bpnd_health_percent', 'bpnd_actor_value',
                'bpnd_to_hit_chance', 'bpnd_explodable_explosion_chance_pct',
                'bpnd_non_lethal_dismemberment_chance',
                'bpnd_severable_debris_count', 'bpnd_explodable_debris_count',
                'bpnd_severable_decal_count', 'bpnd_explodable_decal_count',
                'bpnd_geometry_segment_index',
                (FID, 'bpnd_on_cripple_art_object'),
                (FID, 'bpnd_on_cripple_debris'),
                (FID, 'bpnd_on_cripple_explosion'),
                (FID, 'bpnd_on_cripple_impact_dataset'),
                'bpnd_on_cripple_debris_scale', 'bpnd_on_cripple_debris_count',
                'bpnd_on_cripple_decal_count'),
            MelString(b'NAM1', 'limb_replacement_model'),
            MelString(b'NAM4', 'gore_effects_target_bone'),
            # Ignore texture hashes - they're only an optimization, plenty of
            # records in Skyrim.esm are missing them
            MelNull(b'NAM5'),
            MelString(b'ENAM', 'hit_reaction_start'),
            MelString(b'FNAM', 'hit_reaction_end'),
            MelFid(b'BNAM', 'gore_effects_dismember_blood_art'),
            MelFid(b'INAM', 'gore_effects_blood_impact_material_type'),
            MelFid(b'JNAM', 'on_cripple_blood_impact_material_type'),
            MelFid(b'CNAM', 'meat_cap_texture_set'),
            MelFid(b'NAM2', 'collar_texture_set'),
            MelString(b'DNAM', 'twist_variable_prefix'),
        ), sort_by_attrs='part_node'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCams(MelRecord):
    """Camera Shot."""
    rec_sig = b'CAMS'

    _cams_flags = Flags.from_names('position_follows_location',
        'rotation_follows_target', 'dont_follow_bone', 'first_person_camera',
        'no_tracer', 'start_at_time_zero', 'dont_reset_location_spring',
        'dont_reset_target_spring')

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelConditionList(),
        MelTruncatedStruct(b'DATA', ['4I', '12f'], 'cams_action',
            'cams_location', 'cams_target', (_cams_flags, 'cams_flags'),
            'time_mult_player', 'time_mult_target', 'time_mult_global',
            'cams_max_time', 'cams_min_time', 'target_pct_between_actors',
            'near_target_distance', 'location_spring', 'target_spring',
            'rotation_offset_x', 'rotation_offset_y', 'rotation_offset_z',
            old_versions={'4I9f', '4I7f'}),
        MelImageSpaceMod(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClas(MelRecord):
    """Class."""
    rec_sig = b'CLAS'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelIcon(),
        MelProperties(),
        MelStruct(b'DATA', ['4s', 'f'], 'unknown1', 'bleedout_default'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClfm(MelRecord):
    """Color."""
    rec_sig = b'CLFM'

    _clfm_flags = Flags.from_names('playable', 'remapping_index',
        'extended_lut')

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt32(b'CNAM', 'color_or_index'),
        MelUInt32Flags(b'FNAM', 'clfm_flags', _clfm_flags),
        MelConditionList(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClmt(MelRecord):
    """Climate."""
    rec_sig = b'CLMT'

    melSet = MelSet(
        MelEdid(),
        MelClmtWeatherTypes(),
        MelClmtTextures(),
        MelModel(),
        MelClmtTiming(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCmpo(MelRecord):
    """Component."""
    rec_sig = b'CMPO'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelSoundCrafting(),
        MelUInt32(b'DATA', 'auto_calc_value'),
        MelFid(b'MNAM', 'scrap_item'),
        MelFid(b'GNAM', 'mod_scrap_scalar'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCobj(MelRecord):
    """Constructible Object."""
    rec_sig = b'COBJ'
    ##: What about isKeyedByEid?

    melSet = MelSet(
        MelEdid(),
        MelSoundPickupDrop(),
        MelSorted(MelArray('cobj_components',
            MelStruct(b'FVPA', ['2I'], (FID, 'component_fid'),
                'component_count'),
        ), sort_by_attrs='component_fid'),
        MelDescription(),
        MelConditionList(),
        MelCobjOutput(),
        MelBase(b'NAM1', 'unused1'),
        MelBase(b'NAM2', 'unused2'),
        MelBase(b'NAM3', 'unused3'),
        MelFid(b'ANAM', 'menu_art_object'),
        MelSorted(MelSimpleArray('category_keywords', MelFid(b'FNAM'))),
        MelTruncatedStruct(b'INTV', ['2H'], 'created_object_count',
            'cobj_priority', old_versions={'H'}),
    )
    __slots__ = melSet.getSlotsUsed()

    def mergeFilter(self, modSet):
        self.cobj_components = [c for c in self.cobj_components
                                if c.component_fid.mod_fn in modSet]

#------------------------------------------------------------------------------
class MreCont(AMreWithItems):
    """Container."""
    rec_sig = b'CONT'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelItems(),
        MelDestructible(),
        MelContData(),
        MelKeywords(),
        MelFtyp(),
        MelProperties(),
        MelNativeTerminal(),
        MelSound(),
        MelSoundClose(),
        MelFid(b'TNAM', 'sound_take_all'),
        MelFid(b'ONAM', 'cont_filter_list'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCpth(MelRecord):
    """Camera Path."""
    rec_sig = b'CPTH'

    melSet = MelSet(
        MelEdid(),
        MelConditionList(),
        MelCpthShared(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCsty(MelRecord):
    """Combat Style."""
    rec_sig = b'CSTY'

    _csty_flags = Flags.from_names('dueling', 'flanking',
        'allow_dual_wielding', 'charging', 'retarget_any_nearby_melee_target')

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'CSGD', ['12f'], 'general_offensive_mult',
            'general_defensive_mult', 'general_group_offensive_mult',
            'general_equipment_score_mult_melee',
            'general_equipment_score_mult_magic',
            'general_equipment_score_mult_ranged',
            'general_equipment_score_mult_shout',
            'general_equipment_score_mult_unarmed',
            'general_equipment_score_mult_staff',
            'general_avoid_threat_chance', 'general_dodge_threat_chance',
            'general_evade_threat_chance'),
        MelBase(b'CSMD', 'unknown1'),
        MelTruncatedStruct(b'CSME', ['10f'], 'melee_attack_staggered_mult',
            'melee_power_attack_staggered_mult',
            'melee_power_attack_blocking_mult',
            'melee_bash_mult', 'melee_bash_recoil_mult',
            'melee_bash_attack_mult', 'melee_bash_power_attack_mult',
            'melee_special_attack_mult', 'melee_block_when_staggered_mult',
            'melee_attack_when_staggered_mult', old_versions={'9f'}),
        MelFloat(b'CSRA', 'ranged_accuracy_mult'),
        MelStruct(b'CSCR', ['9f', 'I', 'f'], 'close_range_dueling_circle_mult',
            'close_range_dueling_fallback_mult',
            'close_range_flanking_flank_distance',
            'close_range_flanking_stalk_time',
            'close_range_charging_charge_distance',
            'close_range_charging_throw_probability',
            'close_range_charging_sprint_fast_probability',
            'close_range_charging_sideswipe_probability',
            'close_range_charging_disengage_probability',
            'close_range_charging_throw_max_targets',
            'close_range_flanking_flank_variance'),
        MelTruncatedStruct(b'CSLR', ['5f'], 'long_range_strafe_mult',
            'long_range_adjust_range_mult', 'long_range_crouch_mult',
            'long_range_wait_mult', 'long_range_range_mult',
            old_versions={'4f', '3f'}),
        MelFloat(b'CSCV', 'cover_search_distance_mult'),
        MelStruct(b'CSFL', ['8f'], 'flight_hover_chance',
            'flight_dive_bomb_chance', 'flight_ground_attack_chance',
            'flight_hover_time', 'flight_ground_attack_time',
            'flight_perch_attack_chance', 'flight_perch_attack_time',
            'flight_flying_attack_chance'),
        MelUInt32Flags(b'DATA', 'csty_flags', _csty_flags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDfob(MelRecord):
    """Default Object."""
    rec_sig = b'DFOB'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'DATA', 'default_object'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDmgt(MelRecord):
    """Damage Type."""
    rec_sig = b'DMGT'

    melSet = MelSet(
        MelEdid(),
        MelUnion({
            True: MelArray('damage_types',
                MelStruct(b'DNAM', ['2I'], (FID, 'dt_actor_value'),
                    (FID, 'dt_spell')),
            ),
            False: MelSimpleArray('damage_types', MelUInt32(b'DNAM')),
        }, decider=FormVersionDecider(operator.ge, 78)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDobj(MelRecord):
    """Default Object Manager."""
    rec_sig = b'DOBJ'

    melSet = MelSet(
        MelEdid(),
        MelSorted(MelArray('default_objects',
            MelStruct(b'DNAM', ['2I'], 'default_object_use',
                (FID, 'default_object_fid')),
        ), sort_by_attrs='default_object_use'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDoor(MelRecord):
    """Door."""
    rec_sig = b'DOOR'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelNativeTerminal(),
        MelSound(),
        MelSoundClose(b'ANAM'),
        MelSoundLooping(),
        MelDoorFlags(),
        MelLString(b'ONAM', 'alternate_text_open'),
        MelLString(b'CNAM', 'alternate_text_close'),
        MelRandomTeleports(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEczn(MelRecord):
    """Encounter Zone."""
    rec_sig = b'ECZN'

    _eczn_flags = Flags.from_names('never_resets',
        'match_pc_below_minimum_level', 'disable_combat_boundary', 'workshop')

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', ['2I', '2b', 'B', 'b'],
            (FID, 'eczn_owner'), (FID, 'eczn_location'), 'eczn_rank',
            'eczn_minimum_level', (_eczn_flags, 'eczn_flags'),
            'eczn_max_level'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
##: Check if this record needs adding to skip_form_version_upgrade
class MreEfsh(MelRecord):
    """Effect Shader."""
    rec_sig = b'EFSH'

    _efsh_flags = Flags.from_names(
        (0,  'no_membrane_shader'),
        (1,  'membrane_grayscale_color'),
        (2,  'membrane_grayscale_alpha'),
        (3,  'no_particle_shader'),
        (4,  'ee_inverse'),
        (5,  'affect_skin_only'),
        (6,  'te_ignore_alpha'),
        (7,  'te_project_uvs'),
        (8,  'ignore_base_geometry_alpha'),
        (9,  'te_lighting'),
        (10, 'te_no_weapons'),
        (11, 'use_alpha_sorting'),
        (12, 'prefer_dismembered_limbs'),
        (15, 'particle_animated'),
        (16, 'particle_grayscale_color'),
        (17, 'particle_grayscale_alpha'),
        (24, 'use_blood_geometry'),
    )

    melSet = MelSet(
        MelEdid(),
        MelIcon('fill_texture'),
        MelIco2('particle_texture'),
        MelString(b'NAM7', 'holes_texture'),
        MelString(b'NAM8', 'membrane_palette_texture'),
        MelString(b'NAM9', 'particle_palette_texture'),
        MelBase(b'DATA', 'unknown_data'),
        MelUnion({
            True: MelStruct(b'DNAM',
                ['3I', '3B', 's', '9f', '3B', 's', '8f', 'I', '4f', 'I', '3B',
                 's', '3B', 's', 's', '6f', 'I', '2f'], 'ms_source_blend_mode',
                'ms_blend_operation', 'ms_z_test_function', 'fill_color1_red',
                'fill_color1_green', 'fill_color1_blue', 'unused1',
                'fill_alpha_fade_in_time', 'fill_full_alpha_time',
                'fill_alpha_fade_out_time', 'fill_persistent_alpha_ratio',
                'fill_alpha_pulse_amplitude', 'fill_alpha_pulse_frequency',
                'fill_texture_animation_speed_u',
                'fill_texture_animation_speed_v', 'ee_fall_off',
                'ee_color_red', 'ee_color_green', 'ee_color_blue', 'unused2',
                'ee_alpha_fade_in_time', 'ee_full_alpha_time',
                'ee_alpha_fade_out_time', 'ee_persistent_alpha_ratio',
                'ee_alpha_pulse_amplitude', 'ee_alpha_pulse_frequency',
                'fill_full_alpha_ratio', 'ee_full_alpha_ratio',
                'ms_dest_blend_mode', 'holes_start_time', 'holes_end_time',
                'holes_start_value', 'holes_end_value', (FID, 'sound_ambient'),
                'fill_color2_red', 'fill_color2_green', 'fill_color2_blue',
                'unused7', 'fill_color3_red', 'fill_color3_green',
                'fill_color3_blue', 'unused8', 'unknown1', 'fill_color1_scale',
                'fill_color2_scale', 'fill_color3_scale', 'fill_color1_time',
                'fill_color2_time', 'fill_color3_time',
                (_efsh_flags, 'efsh_flags'), 'fill_texture_scale_u',
                'fill_texture_scale_v'),
            False: MelStruct(b'DNAM',
                ['s', '3I', '3B', 's', '9f', '3B', 's', '8f', '5I', '19f',
                 '3B', 's', '3B', 's', '3B', 's', '11f', 'I', '5f', '3B', 's',
                 'f', '2I', '6f', 'I', '3B', 's', '3B', 's', '9f', '8I', '2f',
                 '2s'], 'unknown1', 'ms_source_blend_mode',
                'ms_blend_operation', 'ms_z_test_function', 'fill_color1_red',
                'fill_color1_green', 'fill_color1_blue', 'unused1',
                'fill_alpha_fade_in_time', 'fill_full_alpha_time',
                'fill_alpha_fade_out_time', 'fill_persistent_alpha_ratio',
                'fill_alpha_pulse_amplitude', 'fill_alpha_pulse_frequency',
                'fill_texture_animation_speed_u',
                'fill_texture_animation_speed_v', 'ee_fall_off',
                'ee_color_red', 'ee_color_green', 'ee_color_blue', 'unused2',
                'ee_alpha_fade_in_time', 'ee_full_alpha_time',
                'ee_alpha_fade_out_time', 'ee_persistent_alpha_ratio',
                'ee_alpha_pulse_amplitude', 'ee_alpha_pulse_frequency',
                'fill_full_alpha_ratio', 'ee_full_alpha_ratio',
                'ms_dest_blend_mode', 'ps_source_blend_mode',
                'ps_blend_operation', 'ps_z_test_function',
                'ps_dest_blend_mode', 'ps_particle_birth_ramp_up_time',
                'ps_full_particle_birth_time',
                'ps_particle_birth_ramp_down_time',
                'ps_full_particle_birth_ratio', 'ps_persistent_particle_count',
                'ps_particle_lifetime', 'ps_particle_lifetime_delta',
                'ps_initial_speed_along_normal',
                'ps_acceleration_along_normal', 'ps_initial_velocity1',
                'ps_initial_velocity2', 'ps_initial_velocity3',
                'ps_acceleration1', 'ps_acceleration2', 'ps_acceleration3',
                'ps_scale_key1', 'ps_scale_key2', 'ps_scale_key1_time',
                'ps_scale_key2_time', 'color_key1_red', 'color_key1_green',
                'color_key1_blue', 'unused3', 'color_key2_red',
                'color_key2_green', 'color_key2_blue', 'unused4',
                'color_key3_red', 'color_key3_green', 'color_key3_blue',
                'unused5', 'color_key1_alpha', 'color_key2_alpha',
                'color_key3_alpha', 'color_key1_time', 'color_key2_time',
                'color_key3_time', 'ps_initial_speed_along_normal_delta',
                'ps_initial_rotation', 'ps_initial_rotation_delta',
                'ps_rotation_speed', 'ps_rotation_speed_delta',
                (FID, 'addon_models'), 'holes_start_time', 'holes_end_time',
                'holes_start_value', 'holes_end_value', 'ee_width',
                'edge_color_red', 'edge_color_green', 'edge_color_blue',
                'unused6', 'explosion_wind_speed', 'texture_count_u',
                'texture_count_v', 'addon_models_fade_in_time',
                'addon_models_fade_out_time', 'addon_models_scale_start',
                'addon_models_scale_end', 'addon_models_scale_in_time',
                'addon_models_scale_out_time', (FID, 'sound_ambient'),
                'fill_color2_red', 'fill_color2_green', 'fill_color2_blue',
                'unused7', 'fill_color3_red', 'fill_color3_green',
                'fill_color3_blue', 'unused8', 'fill_color1_scale',
                'fill_color2_scale', 'fill_color3_scale', 'fill_color1_time',
                'fill_color2_time', 'fill_color3_time', 'color_scale',
                'birth_position_offset', 'birth_position_offset_range_delta',
                'psa_start_frame', 'psa_start_frame_variation',
                'psa_end_frame', 'psa_loop_start_frame',
                'psa_loop_start_variation', 'psa_frame_count',
                'psa_frame_count_variation', (_efsh_flags, 'efsh_flags'),
                'fill_texture_scale_u', 'fill_texture_scale_v', 'unused9'),
        }, decider=FormVersionDecider(operator.ge, 106)),
        MelModel(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEnch(MelRecord):
    """Object Effect."""
    rec_sig = b'ENCH'

    _enit_flags = Flags.from_names(
        (0, 'ench_no_auto_calc'),
        (2, 'extend_duration_on_recast'),
    )

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelStruct(b'ENIT', ['i', '2I', 'i', '2I', 'f', '2I'],
            'enchantment_cost', (_enit_flags, 'enit_flags'), 'cast_type',
            'enchantment_amount', 'enchantment_target_type',
            'enchantment_type', 'charge_time', (FID, 'base_enchantment'),
            (FID, 'worn_restrictions')),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEqup(MelRecord):
    """Equip Type."""
    rec_sig = b'EQUP'

    _equp_flags = Flags.from_names('use_all_parents', 'parents_optional',
        'item_slot')

    melSet = MelSet(
        MelEdid(),
        MelEqupPnam(),
        MelUInt32Flags(b'DATA', 'equp_flags', _equp_flags),
        MelFid(b'ANAM', 'condition_actor_value'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreExpl(MelRecord):
    """Explosion."""
    rec_sig = b'EXPL'

    _expl_flags = Flags.from_names(
        (1,  'always_uses_world_orientation'),
        (2,  'knock_down_always'),
        (3,  'knock_down_by_formula'),
        (4,  'ignore_los_check'),
        (5,  'push_explosion_source_ref_only'),
        (6,  'ignore_image_space_swap'),
        (7,  'explosion_chain'),
        (8,  'no_controller_vibration'),
        (9,  'placed_object_persists'),
        (10, 'skip_underwater_tests'),
    )

    class MelExplData(MelTruncatedStruct):
        """Handles the EXPL subrecord DATA, which requires special code."""
        def _pre_process_unpacked(self, unpacked_val):
            if len(unpacked_val) in (13, 14, 15):
                # Form Version 97 added the inner_radius float right before the
                # outer_radius float
                unpacked_val = (unpacked_val[:8] + self.defaults[8:9] +
                                unpacked_val[8:])
            return super()._pre_process_unpacked(unpacked_val)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelEnchantment(),
        MelImageSpaceMod(),
        MelExplData(b'DATA', ['6I', '6f', '2I', 'f', 'I', '4f', 'I'],
            (FID, 'expl_light'), (FID, 'expl_sound1'), (FID, 'expl_sound2'),
            (FID, 'expl_impact_dataset'), (FID, 'placed_object'),
            (FID, 'spawn_object'), 'expl_force', 'expl_damage', 'inner_radius',
            'outer_radius', 'is_radius', 'vertical_offset_mult',
            (_expl_flags, 'expl_flags'), 'expl_sound_level',
            'placed_object_autofade_delay', 'expl_stagger', 'expl_spawn_x',
            'expl_spawn_y', 'expl_spawn_z', 'expl_spawn_spread_degrees',
            'expl_spawn_count', old_versions={'6I6f2IfI', '6I5f2IfI',
                                              '6I5f2If', '6I5f2I'}),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction."""
    rec_sig = b'FACT'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelRelations(),
        MelFactFlags(),
        MelFactFids(),
        # 'cv_arrest' and 'cv_attack_on_sight' are actually bools, cv means
        # 'crime value' (which is what this struct is about)
        MelStruct(b'CRVA', ['2B', '5H', 'f', '2H'], 'cv_arrest',
            'cv_attack_on_sight', 'cv_murder', 'cv_assault', 'cv_trespass',
            'cv_pickpocket', 'cv_unknown', 'cv_steal_multiplier', 'cv_escape',
            'cv_werewolf'),
        MelFactRanks(),
        MelFactVendorInfo(),
        MelLocation(b'PLVD'),
        MelConditions(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFlor(MelRecord):
    """Flora."""
    rec_sig = b'FLOR'
    _has_duplicate_attrs = True # RNAM is an older version of ATTX

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelProperties(),
        MelColor(b'PNAM'),
        MelAttx(),
        # Older format - read, but only dump ATTX
        MelReadOnly(MelAttx(b'RNAM')),
        MelActiFlags(),
        MelIngredient(),
        MelSound(),
        MelSeasons(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFlst(AMreFlst):
    """FormID List."""
    rec_sig = b'FLST'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFlstFids(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
##: It should be possible to absorb this in MelArray, see MelWthrColorsFnv for
# a plan of attack. But note that if we have form version info, we should be
# able to pass that in too, since the other algorithm is ambigous once a
# subrecord of size lcm(new, old) is reached - MelFVDArray (form version
# dependent)?
class MelFurnMarkerParams(MelArray):
    """Handles the FURN subrecord SNAM (Furniture Marker Parameters), which
    requires special code."""
    _param_entry_types = Flags.from_names('entry_type_front',
        'entry_type_rear', 'entry_type_right', 'entry_type_left',
        'entry_type_other', 'entry_type_unused1', 'entry_type_unused2',
        'entry_type_unused3')

    def __init__(self):
        struct_args = (b'SNAM', ['4f', 'I', 'B', '3s'], 'param_offset_x',
                       'param_offset_y', 'param_offset_z', 'param_rotation_z',
                       (FID, 'param_keyword'),
                       (self._param_entry_types, 'param_entry_types'),
                       'param_unknown')
        # Trick MelArray into thinking we have a static-sized element
        super().__init__('furn_marker_parameters', MelStruct(*struct_args))
        self._real_loader = MelTruncatedStruct(*struct_args,
            old_versions={'4fI'})

    def _load_array(self, record, ins, sub_type, size_, *debug_strs):
        append_entry = getattr(record, self.attr).append
        entry_slots = self.array_element_attrs
        # Form version 125 added the entry types to the end
        entry_size = 24 if record.header.form_version >= 125 else 20
        load_entry = self._real_loader.load_mel
        for x in range(size_ // entry_size):
            arr_entry = MelObject()
            append_entry(arr_entry)
            arr_entry.__slots__ = entry_slots
            load_entry(arr_entry, ins, sub_type, entry_size, *debug_strs)

class MreFurn(AMreWithItems):
    """Furniture."""
    rec_sig = b'FURN'

    _active_markers_flags = Flags.from_names(
        (0,  'interaction_point_0'),
        (1,  'interaction_point_1'),
        (2,  'interaction_point_2'),
        (3,  'interaction_point_3'),
        (4,  'interaction_point_4'),
        (5,  'interaction_point_5'),
        (6,  'interaction_point_6'),
        (7,  'interaction_point_7'),
        (8,  'interaction_point_8'),
        (9,  'interaction_point_9'),
        (10, 'interaction_point_10'),
        (11, 'interaction_point_11'),
        (12, 'interaction_point_12'),
        (13, 'interaction_point_13'),
        (14, 'interaction_point_14'),
        (15, 'interaction_point_15'),
        (16, 'interaction_point_16'),
        (17, 'interaction_point_17'),
        (18, 'interaction_point_18'),
        (19, 'interaction_point_19'),
        (20, 'interaction_point_20'),
        (21, 'interaction_point_21'),
        (22, 'allow_awake_sound'),
        (23, 'enter_with_weapon_drawn'),
        (24, 'play_anim_when_full'),
        (25, 'disables_activation'),
        (26, 'is_perch'),
        (27, 'must_exit_to_talk'),
        (28, 'use_static_to_avoid_node'),
        (30, 'has_model'),
        (31, 'is_sleep_furniture'),
    )

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelProperties(),
        MelNativeTerminal(),
        MelFtyp(),
        MelColor(b'PNAM'),
        MelFid(b'WNAM', 'drinking_water_type'),
        MelAttx(),
        MelActiFlags(),
        MelConditions(),
        MelItems(),
        MelUInt32Flags(b'MNAM', 'active_markers_flags', _active_markers_flags),
        MelTruncatedStruct(b'WBDT', ['B', 'b'], 'bench_type', 'uses_skill',
            old_versions={'B'}),
        MelFid(b'NAM1', 'associated_form'),
        MelFurnMarkerData(),
        MelFurnMarkerParams(),
        MelAppr(),
        MelObjectTemplate(),
        MelNvnm(),
    ).with_distributor(_object_template_distributor)
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGdry(MelRecord):
    """God Rays."""
    rec_sig = b'GDRY'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', ['15f'], 'back_color_red', 'back_color_green',
            'back_color_blue', 'forward_color_red', 'forward_color_green',
            'forward_color_blue', 'godray_intensity', 'air_color_scale',
            'back_color_scale', 'forward_color_scale', 'back_phase',
            'air_color_red', 'air_color_green', 'air_color_blue',
            'forward_phase'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGras(MelRecord):
    """Grass."""
    rec_sig = b'GRAS'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelGrasData(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreHazd(MelRecord):
    """Hazard."""
    rec_sig = b'HAZD'

    _hazd_flags = Flags.from_names('affects_player_only',
        'inherit_duration_from_spawn_spell', 'align_to_impact_normal',
        'inherit_radius_from_spawn_spell', 'drop_to_ground',
        'taper_effectiveness_by_proximity')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelImageSpaceMod(),
        MelStruct(b'DNAM', ['I', '4f', '5I', '3f'], 'hazd_limit',
            'hazd_radius', 'hazd_lifetime', 'image_space_radius',
            'target_interval', (_hazd_flags, 'hazd_flags'),
            (FID, 'hazd_effect'), (FID, 'hazd_light'),
            (FID, 'hazd_impact_dataset'), (FID, 'hazd_sound'),
            'taper_full_effect_radius', 'taper_weight', 'taper_curse'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreHdpt(MelRecord):
    """Head Part."""
    rec_sig = b'HDPT'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelHdptShared(),
        MelConditionList(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIdle(MelRecord):
    """Idle Animation."""
    rec_sig = b'IDLE'

    melSet = MelSet(
        MelEdid(),
        MelConditionList(),
        MelString(b'DNAM', 'behavior_graph'),
        MelIdleEnam(),
        MelIdleRelatedAnims(),
        MelIdleData(),
        MelString(b'GNAM', 'animation_file'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIdlm(MelRecord):
    """Idle Marker."""
    rec_sig = b'IDLM'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelKeywords(),
        MelIdlmFlags(),
        MelCounter(MelUInt8(b'IDLC', 'idlm_animation_count'),
            counts='idlm_animations'),
        MelIdleTimerSetting(),
        MelIdlmIdla(),
        MelFid(b'QNAM', 'unknown_qnam'),
        MelModel(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
_dnam_attrs4 = ('dof_vignette_radius', 'dof_vignette_strength')
_dnam_counters4 = tuple(f'{x}_count' for x in _dnam_attrs4)
_dnam_counter_mapping = AMreImad.dnam_counter_mapping | dict(
    zip(_dnam_attrs4, _dnam_counters4))
_imad_sig_attr = AMreImad.imad_sig_attr.copy()
_imad_sig_attr.insert(12, (b'NAM5', 'dof_vignette_radius'))
_imad_sig_attr.insert(13, (b'NAM6', 'dof_vignette_strength'))

class MreImad(AMreImad): # see AMreImad for details
    """Image Space Adapter."""
    melSet = MelSet(
        MelEdid(),
        MelPartialCounter(MelTruncatedStruct(b'DNAM',
            ['I', 'f', '49I', '2f', '3I', '2B', '2s', '6I'], 'imad_animatable',
            'imad_duration', *AMreImad.dnam_counters1,
            'radial_blur_use_target', 'radial_blur_center_x',
            'radial_blur_center_y', *AMreImad.dnam_counters2,
            'dof_use_target', (AMreImad.imad_dof_flags, 'dof_flags'),
            'unused1', *AMreImad.dnam_counters3, *_dnam_counters4,
            old_versions={'If49I2f3I2B2s4I'}),
            counters=AMreImad.dnam_counter_mapping),
        *[AMreImad.special_impls[s](s, a) for s, a in _imad_sig_attr],
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImgs(MelRecord):
    """Image Space."""
    rec_sig = b'IMGS'

    melSet = MelSet(
        MelEdid(),
        # Only found in one record (DefaultImageSpaceExterior [IMGS:00000161]),
        # skip for everything else
        MelOptStruct(b'ENAM', ['14f'], 'enam_hdr_eye_adapt_speed',
            'enam_hdr_tonemap_e', 'enam_hdr_bloom_threshold',
            'enam_hdr_bloom_scale', 'enam_hdr_auto_exposure_min_max',
            'enam_hdr_sunlight_scale', 'enam_hdr_sky_scale',
            'enam_cinematic_saturation', 'enam_cinematic_brightness',
            'enam_cinematic_contrast', 'enam_tint_amount',
            'enam_tint_color_red', 'enam_tint_color_green',
            'enam_tint_color_blue'),
        MelStruct(b'HNAM', ['9f'], 'hdr_eye_adapt_speed', 'hdr_tonemap_e',
            'hdr_bloom_threshold', 'hdr_bloom_scale', 'hdr_auto_exposure_max',
            'hdr_auto_exposure_min', 'hdr_sunlight_scale', 'hdr_sky_scale',
            'hdr_middle_gray'),
        MelImgsCinematic(),
        MelImgsTint(),
        MelTruncatedStruct(b'DNAM', ['3f', '2s', 'H', '2f'], 'dof_strength',
            'dof_distance', 'dof_range', 'dof_unknown', 'dof_sky_blur_radius',
            'dof_vignette_radius', 'dof_vignette_strength',
            old_versions={'3f2sH'}),
        MelString(b'TX00', 'imgs_lut'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Dialog Response."""
    rec_sig = b'INFO'

    _info_response_flags = Flags.from_names(
        (0,  'start_scene_on_end'),
        (1,  'random'),
        (2,  'say_once'),
        (3,  'requires_player_activation'),
        (5,  'random_end'),
        (6,  'end_running_scene'),
        (7,  'force_greet_hello'),
        (8,  'player_address'),
        (9,  'force_subtitle'),
        (10, 'can_move_while_greeting'),
        (11, 'no_lip_file'),
        (12, 'requires_post_processing'),
        (13, 'audio_output_override'),
        (14, 'has_capture'),
    )
    _info_response_flags2 = Flags.from_names(
        (1,  'random'),
        (3,  'force_all_children_player_activate_only'),
        (5,  'random_end'),
        (8,  'child_infos_dont_inherit_reset_data'),
        (9,  'force_all_children_random'),
        (11, 'dont_do_all_before_repeating'),
    )

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelStruct(b'ENAM', ['3H'], (_info_response_flags, 'response_flags'),
            (_info_response_flags2, 'response_flags2'), 'reset_hours'),
        MelFid(b'TPIC', 'info_topic'),
        MelFid(b'PNAM', 'prev_info'),
        MelFid(b'DNAM', 'shared_info'),
        MelFid(b'GNAM', 'info_group'),
        MelString(b'IOVR', 'override_file_name'),
        MelGroups('info_responses',
            MelStruct(b'TRDA', ['I', 'B', 'I', 's', 'H', '2i'],
                (FID, 'rd_emotion'), 'rd_response_number', (FID, 'rd_sound'),
                'rd_unknown1', 'rd_interrupt_percentage',
                'rd_camera_target_alias', 'rd_camera_location_alias'),
            MelLString(b'NAM1', 'response_text'),
            MelString(b'NAM2', 'script_notes'),
            MelString(b'NAM3', 'response_edits'),
            MelString(b'NAM4', 'alternate_lip_text'),
            MelFid(b'SNAM', 'idle_animations_speaker'),
            MelFid(b'LNAM', 'idle_animations_listener'),
            MelUInt16(b'TNAM', 'interrupt_percentage'),
            MelBase(b'NAM9', 'response_text_hash'),
            MelFid(b'SRAF', 'response_camera_path'),
            MelBase(b'WZMD', 'stop_on_scene_end'),
        ),
        MelConditionList(),
        MelLString(b'RNAM', 'info_prompt'),
        MelFid(b'ANAM', 'info_speaker'),
        MelFid(b'TSCE', 'start_scene'),
        MelBase(b'INTV', 'unknown_intv'),
        MelSInt32(b'ALFA', 'forced_alias'),
        MelFid(b'ONAM', 'audio_output_override'),
        MelUInt32(b'GREE', 'greet_distance'),
        MelStruct(b'TIQS', ['2h'], 'spqs_on_begin', 'spqs_on_end'),
        MelString(b'NAM0', 'start_scene_phase'),
        MelUInt32(b'INCC', 'info_challenge'),
        MelFid(b'MODQ', 'reset_global'),
        MelUInt32(b'INAM', 'subtitle_priority'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIngr(MelRecord):
    """Ingredient."""
    rec_sig = b'INGR'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelKeywords(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelEquipmentType(),
        MelSoundPickupDrop(),
        MelValueWeight(),
        MelIngrEnit(),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreInnr(MelRecord):
    """Instance Naming Rules."""
    rec_sig = b'INNR'

    melSet = MelSet(
        MelEdid(),
        MelUInt32(b'UNAM', 'innr_target'),
        MelGroups('naming_rulesets',
            MelCounter(MelUInt32(b'VNAM', 'naming_rules_count'),
                counts='naming_rules'),
            MelGroups('naming_rules',
                MelLString(b'WNAM', 'naming_rule_text'),
                MelKeywords(),
                MelStruct(b'XNAM', ['f', '2B'], 'naming_rule_property_value',
                    'naming_rule_property_target', 'naming_rule_property_op'),
                MelUInt16(b'YNAM', 'naming_rule_index'),
            ),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIpct(MelRecord):
    rec_sig = b'IPCT'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelStruct(b'DATA', ['f', 'I', '2f', 'I', '2B', '2s'],
            'effect_duration', 'effect_orientation', 'angle_threshold',
            'placement_radius', 'ipct_sound_level', 'ipct_no_decal_data',
            'impact_result', 'unknown1'),
        MelDecalData(),
        MelIpctTextureSets(),
        MelIpctSounds(),
        MelFid(b'NAM3', 'footstep_explosion'),
        MelIpctHazard(),
        MelFloat(b'FNAM', 'footstep_particle_max_dist'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIpds(MelRecord):
    """Impact Dataset."""
    rec_sig = b'IPDS'

    melSet = MelSet(
        MelEdid(),
        MelIpdsPnam(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreKeym(MelRecord):
    """Key."""
    rec_sig = b'KEYM'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelKeywords(),
        MelValueWeight(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreKssm(MelRecord):
    """Sound Keyword Mapping."""
    rec_sig = b'KSSM'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'DNAM', 'primary_descriptor'),
        MelFid(b'ENAM', 'exterior_tail'),
        MelFid(b'VNAM', 'vats_descriptor'),
        MelFloat(b'TNAM', 'vats_threshold'),
        MelFids('kssm_keywords', MelFid(b'KNAM')),
        MelSorted(MelGroups('kssm_sounds',
            MelStruct(b'RNAM', ['2I'], 'reverb_class',
                (FID, 'sound_descriptor')),
        ), sort_by_attrs='reverb_class'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreKywd(MelRecord):
    """Keyword."""
    rec_sig = b'KYWD'
    _has_duplicate_attrs = True # NNAM is an older version of FULL

    melSet = MelSet(
        MelEdid(),
        MelColorO(),
        MelNotesTypeRule(),
        MelFull(),
        # Older format - read, but only dump FULL
        MelReadOnly(MelString(b'NNAM', 'full')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvli(AMreLeveledList):
    """Leveled Item."""
    rec_sig = b'LVLI'

    top_copy_attrs = ('chanceNone', 'maxCount', 'glob', 'filterKeywordChances',
                      'epicLootChance', 'overrideName')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8(b'LVLD', 'chanceNone'),
        MelUInt8(b'LVLM', 'maxCount'),
        MelUInt8Flags(b'LVLF', u'flags', AMreLeveledList._flags),
        MelFid(b'LVLG', 'glob'),
        MelLLItems(),
        MelArray('filterKeywordChances',
            MelStruct(b'LLKC', [u'2I'], (FID, u'keyword'), u'chance'),
        ),
        MelFid(b'LVSG', 'epicLootChance'),
        MelLString(b'ONAM', 'overrideName')
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvln(AMreLeveledList):
    """Leveled NPC."""
    rec_sig = b'LVLN'

    top_copy_attrs = ('chanceNone', 'maxCount', 'glob', 'filterKeywordChances',
                      'model', 'modt_p')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8(b'LVLD', 'chanceNone'),
        MelUInt8(b'LVLM', 'maxCount'),
        MelUInt8Flags(b'LVLF', u'flags', AMreLeveledList._flags),
        MelFid(b'LVLG', 'glob'),
        MelLLItems(),
        MelArray('filterKeywordChances',
            MelStruct(b'LLKC', [u'2I'], (FID, u'keyword'), u'chance'),
        ),
        MelString(b'MODL','model'),
        MelBase(b'MODT','modt_p'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePerk(MelRecord):
    """Perk."""
    rec_sig = b'PERK'

    _script_flags = Flags.from_names('run_immediately', 'replace_default')

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFull(),
        MelDescription(),
        MelIcon(),
        MelConditionList(),
        MelPerkData(),
        MelSound(),
        MelNextPerk(),
        MelString(b'FNAM', 'perk_swf'),
        MelSorted(MelGroups('perk_effects',
            MelStruct(b'PRKE', ['3B'], 'pe_type', 'pe_rank', 'pe_priority'),
            MelUnion({
                0: MelStruct(b'DATA', ['I', 'H'], (FID, 'pe_quest'),
                    'pe_quest_stage'),
                1: MelFid(b'DATA', 'pe_ability'),
                2: MelStruct(b'DATA', ['3B'], 'pe_entry_point', 'pe_function',
                    'pe_perk_conditions_tab_count'),
            }, decider=AttrValDecider('pe_type')),
            MelSorted(MelGroups('pe_conditions',
                MelSInt8(b'PRKC', 'pe_run_on'),
                MelConditionList(),
            ), sort_by_attrs='pe_run_on'),
            MelPerkParamsGroups(
                # EPFT has the following meanings:
                #  0: Unknown
                #  1: EPFD=float
                #  2: EPFD=float, float
                #  3: EPFD=fid (LVLI)
                #  4: EPFD=fid (SPEL), EPF2 and EPF3 are used
                #  5: EPFD=fid (SPEL)
                #  6: EPFD=string
                #  7: EPFD=lstring
                #  8: EPFD=fid (AVIF), float
                # There is a special case: if EPFT is 2 and the pe_function
                # (see DATA above) is one of 5, 12, 13 or 14, then
                # EPFD=fid (AVIF), float - same as in the 8 case above.
                MelUInt8(b'EPFT', 'pp_param_type'),
                MelUInt16(b'EPFB', 'pp_perk_entry_id'),
                MelLString(b'EPF2', 'pp_button_label'),
                MelUInt16Flags(b'EPF3', 'pp_script_flags', _script_flags),
                MelUnion({
                    0: MelBase(b'EPFD', 'pp_param1'),
                    1: MelFloat(b'EPFD', 'pp_param1'),
                    2: MelStruct(b'EPFD', ['2f'], 'pp_param1', 'pp_param2'),
                    (3, 4, 5): MelFid(b'EPFD', 'pp_param1'),
                    6: MelString(b'EPFD', 'pp_param1'),
                    7: MelLString(b'EPFD', 'pp_param1'),
                    8: MelStruct(b'EPFD', ['I', 'f'], (FID, 'pp_param1'),
                        'pp_param2'),
                }, decider=PerkEpdfDecider({5, 12, 13, 14})),
            ),
            MelBaseR(b'PRKF', 'pe_end_marker'),
        ), sort_special=perk_effect_key),
    ).with_distributor(perk_distributor)
    __slots__ = melSet.getSlotsUsed()
