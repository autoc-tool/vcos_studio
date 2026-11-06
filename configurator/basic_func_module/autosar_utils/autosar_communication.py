# This Python file uses the following encoding: utf-8
############################################################################
# Copyright (c) 2025 Li Auto Inc. and its affiliates
# Licensed under the Apache License, Version 2.0(the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
############################################################################
from autosar44 import autosar44
from basic_func_module.autosar_utils.utils import set_short_name, get_short_name
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.base_logger import logger

"""
Communication.arxml API
"""

tag_to_class_dict = {
    "FRAME_LENGTH": autosar44.INTEGER,
    "PACKING_BYTE_ORDER": autosar44.BYTE_ORDER_ENUM,
    "PDU_REF": autosar44.PDU_REFType3556,
    "START_POSITION": autosar44.INTEGER,
    "I_PDU_TIMING_SPECIFICATIONS": autosar44.I_PDU_TIMING_SPECIFICATIONSType2761,
    "I_PDU_TIMING": autosar44.I_PDU_TIMING,
    "TRANSMISSION_MODE_DECLARATION": autosar44.TRANSMISSION_MODE_DECLARATION,
    "TRANSMISSION_MODE_TRUE_TIMING": autosar44.TRANSMISSION_MODE_TIMING,
    "CYCLIC_TIMING": autosar44.CYCLIC_TIMING,
    "TIME_PERIOD": autosar44.TIME_RANGE_TYPE,
    "TIME_OFFSET": autosar44.TIME_RANGE_TYPE,
    "VALUE": autosar44.TIME_VALUE,
}


def set_tag_value(node, tag_name, value):
    attr_value = getattr(node, tag_name, "N/A")
    if attr_value is None:
        tag_class = tag_to_class_dict.get(tag_name, None)
        if tag_class:
            tag_obj = tag_class()
            tag_obj.valueOf_ = value
            setattr(node, tag_name, tag_obj)
        else:
            print(f"Unsupported tag {tag_name}")
    elif attr_value == "N/A":
        print(f"InValid attribute {tag_name} of class {type(node)}")
    else:
        attr_value.valueOf_ = value


def set_tag_dest(node, tag_name, dest):
    attr_value = getattr(node, tag_name, "N/A")
    if attr_value is None:
        tag_class = tag_to_class_dict.get(tag_name, None)
        if tag_class:
            tag_obj = tag_class()
            tag_obj.DEST = dest
            setattr(node, tag_name, tag_obj)
        else:
            print(f"Unsupported tag {tag_name}")
    elif attr_value == "N/A":
        print(f"InValid attribute {tag_name} of class {type(node)}")
    else:
        attr_value.DEST = dest


def set_short_name_tag_value(parent, node, value):
    set_short_name(node, value)
    parent_path = parent.get_path()
    root_id = id(parent.get_root())
    short_name = get_short_name(node)
    path = f"{root_id}:{parent_path}/{short_name}"
    AutosarUtil.ar_paths[path] = node


def creat_container_from_tag_name(parent, tag_name):
    if parent is None:
        logger.warning("parent not found!")
        return None
    if tag_name not in tag_to_class_dict.keys():
        logger.warning(f"tag_name {tag_name} not found in tag_to_class_dict!")
        return None
    obj = tag_to_class_dict[tag_name]()
    AutosarUtil.set_tag(obj, tag_name.replace("_", "-"))
    AutosarUtil.set_parent(obj, parent)
    tag_obj = getattr(parent, tag_name, None)
    if isinstance(tag_obj, list):
        tag_obj.append(obj)
    else:
        setattr(parent, tag_name, obj)
    return obj


# CanFrame ELEMENTS start
class CanFrame:

    @staticmethod
    def create_pdu_to_frame_mapping(pdu_to_frame_mappings, pdu_to_frame_mapping_dict: dict):
        pdu_to_frame_mapping_obj = autosar44.PDU_TO_FRAME_MAPPING()
        pdu_to_frame_mappings.PDU_TO_FRAME_MAPPING.append(pdu_to_frame_mapping_obj)
        pdu_to_frame_mapping_obj.set_tag("PDU-TO-FRAME-MAPPING")
        pdu_to_frame_mapping_obj.set_parent(pdu_to_frame_mappings)
        set_short_name_tag_value(
            pdu_to_frame_mappings, pdu_to_frame_mapping_obj, pdu_to_frame_mapping_dict["short_name"]
        )
        set_tag_value(pdu_to_frame_mapping_obj, "PACKING_BYTE_ORDER", pdu_to_frame_mapping_dict["packing_byte_order"])
        set_tag_value(pdu_to_frame_mapping_obj, "PDU_REF", pdu_to_frame_mapping_dict["pdu_ref"])
        set_tag_dest(pdu_to_frame_mapping_obj, "PDU_REF", "I-SIGNAL-I-PDU")
        set_tag_value(pdu_to_frame_mapping_obj, "START_POSITION", pdu_to_frame_mapping_dict["start_position"])

    @staticmethod
    def create_can_frame(can_frame_elements, can_frame_dict: dict):
        parent = can_frame_elements
        can_frame_obj = autosar44.CAN_FRAME()
        can_frame_elements.CAN_FRAME.append(can_frame_obj)
        can_frame_obj.set_tag("CAN-FRAME")
        can_frame_obj.set_parent(can_frame_elements)
        set_short_name_tag_value(parent, can_frame_obj, can_frame_dict["short_name"])
        set_tag_value(can_frame_obj, "FRAME_LENGTH", can_frame_dict["frame_length"])

        pdu_to_frame_mapping_dict = can_frame_dict.get("pdu_to_frame_mapping")
        if pdu_to_frame_mapping_dict:
            pdu_to_frame_mappings_obj = autosar44.PDU_TO_FRAME_MAPPINGSType()
            pdu_to_frame_mappings_obj.set_tag("PDU-TO-FRAME-MAPPINGS")
            pdu_to_frame_mappings_obj.set_parent(can_frame_obj)
            can_frame_obj.PDU_TO_FRAME_MAPPINGS = pdu_to_frame_mappings_obj
            CanFrame.create_pdu_to_frame_mapping(pdu_to_frame_mappings_obj, pdu_to_frame_mapping_dict)


# CanFrame ELEMENTS end


# LinFrame ELEMENTS start
class LinFrame:

    @staticmethod
    def create_pdu_to_frame_mapping(pdu_to_frame_mappings, pdu_to_frame_mapping_dict: dict):
        pdu_to_frame_mapping_obj = autosar44.PDU_TO_FRAME_MAPPING()
        pdu_to_frame_mappings.PDU_TO_FRAME_MAPPING.append(pdu_to_frame_mapping_obj)
        pdu_to_frame_mapping_obj.set_tag("PDU-TO-FRAME-MAPPING")
        pdu_to_frame_mapping_obj.set_parent(pdu_to_frame_mappings)
        set_short_name_tag_value(
            pdu_to_frame_mappings, pdu_to_frame_mapping_obj, pdu_to_frame_mapping_dict["short_name"]
        )
        set_tag_value(pdu_to_frame_mapping_obj, "PACKING_BYTE_ORDER", pdu_to_frame_mapping_dict["packing_byte_order"])
        set_tag_value(pdu_to_frame_mapping_obj, "PDU_REF", pdu_to_frame_mapping_dict["pdu_ref"])
        set_tag_dest(pdu_to_frame_mapping_obj, "PDU_REF", "I-SIGNAL-I-PDU")
        set_tag_value(pdu_to_frame_mapping_obj, "START_POSITION", pdu_to_frame_mapping_dict["start_position"])

    @staticmethod
    def create_lin_frame(lin_frame_elements, lin_frame_dict: dict):
        parent = lin_frame_elements
        lin_frame_obj = autosar44.LIN_UNCONDITIONAL_FRAME()
        lin_frame_elements.LIN_UNCONDITIONAL_FRAME.append(lin_frame_obj)
        lin_frame_obj.set_tag("LIN-UNCONDITIONAL-FRAME")
        lin_frame_obj.set_parent(lin_frame_elements)
        set_short_name_tag_value(parent, lin_frame_obj, lin_frame_dict["short_name"])
        set_tag_value(lin_frame_obj, "FRAME_LENGTH", lin_frame_dict["frame_length"])

        pdu_to_frame_mapping_dict = lin_frame_dict.get("pdu_to_frame_mapping")
        if pdu_to_frame_mapping_dict:
            pdu_to_frame_mappings_obj = autosar44.PDU_TO_FRAME_MAPPINGSType()
            pdu_to_frame_mappings_obj.set_tag("PDU-TO-FRAME-MAPPINGS")
            pdu_to_frame_mappings_obj.set_parent(lin_frame_obj)
            lin_frame_obj.PDU_TO_FRAME_MAPPINGS = pdu_to_frame_mappings_obj
            LinFrame.create_pdu_to_frame_mapping(pdu_to_frame_mappings_obj, pdu_to_frame_mapping_dict)


# LinFrame ELEMENTS end


# IPDUGroup ELEMENTS start
class ISignalIPduGroup:

    @staticmethod
    def create_i_signal_i_pdu_group(parent=None, short_name=None):
        # short_name_obj = autosar44.IDENTIFIER(valueOf_ = short_name)
        rv_obj = autosar44.I_SIGNAL_I_PDU_GROUP(parent_object_=parent)
        set_short_name_tag_value(parent, rv_obj, short_name)
        rv_obj.set_tag("I-SIGNAL-I-PDU-GROUP")
        if parent and hasattr(parent, "I_SIGNAL_I_PDU_GROUP"):
            if isinstance(parent.I_SIGNAL_I_PDU_GROUP, list):
                parent.I_SIGNAL_I_PDU_GROUP.append(rv_obj)
        return rv_obj

    @staticmethod
    def create_communication_direction(parent=None, value=None):
        rv_obj = autosar44.COMMUNICATION_DIRECTION_TYPE(valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "COMMUNICATION_DIRECTION"):
            parent.COMMUNICATION_DIRECTION = rv_obj
        return rv_obj

    @staticmethod
    def create_i_signal_i_pdus(parent=None, i_signal_i_pdu_ref_conditional=None):
        rv_obj = autosar44.I_SIGNAL_I_PDUSType2769(
            I_SIGNAL_I_PDU_REF_CONDITIONAL=i_signal_i_pdu_ref_conditional, parent_object_=parent
        )
        if parent and hasattr(parent, "I_SIGNAL_I_PDUS"):
            parent.I_SIGNAL_I_PDUS = rv_obj
        return rv_obj

    @staticmethod
    def create_i_signal_i_pdu_ref_conditional(parent=None):
        rv_obj = autosar44.I_SIGNAL_I_PDU_REF_CONDITIONAL(parent_object_=parent)
        if parent and hasattr(parent, "I_SIGNAL_I_PDU_REF_CONDITIONAL"):
            if isinstance(parent.I_SIGNAL_I_PDU_REF_CONDITIONAL, list):
                parent.I_SIGNAL_I_PDU_REF_CONDITIONAL.append(rv_obj)
        return rv_obj

    @staticmethod
    def create_i_signal_i_pdu_ref(parent=None, value=None):
        rv_obj = autosar44.I_SIGNAL_I_PDU_REFType2772(DEST="I-SIGNAL-I-PDU", valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "I_SIGNAL_I_PDU_REF"):
            parent.I_SIGNAL_I_PDU_REF = rv_obj
        return rv_obj

    @staticmethod
    def create_full_i_signal_i_pdu_ref_conditional(parent=None, value=None):
        rv_obj = ISignalIPduGroup.create_i_signal_i_pdu_ref_conditional(parent)
        ISignalIPduGroup.create_i_signal_i_pdu_ref(rv_obj, value)
        return rv_obj

    @staticmethod
    def create_full_i_signal_i_pdu_group(parent=None, short_name=None, direction=None):
        rv_obj = ISignalIPduGroup.create_i_signal_i_pdu_group(parent, short_name)
        ISignalIPduGroup.create_communication_direction(rv_obj, direction)
        ISignalIPduGroup.create_i_signal_i_pdus(rv_obj)
        return rv_obj


# IPDUGroup ELEMENTS end


# PDU ELEMENTS start
class ISignalIPdu:
    @staticmethod
    def create_i_signal_i_pdu(parent=None, short_name=None):
        # short_name_obj = autosar44.IDENTIFIER(valueOf_ = short_name)
        rv_obj = autosar44.I_SIGNAL_I_PDU(parent_object_=parent)
        set_short_name_tag_value(parent, rv_obj, short_name)
        rv_obj.set_tag("I-SIGNAL-I-PDU")
        if parent and hasattr(parent, "I_SIGNAL_I_PDU"):
            if isinstance(parent.I_SIGNAL_I_PDU, list):
                parent.I_SIGNAL_I_PDU.append(rv_obj)
        return rv_obj

    @staticmethod
    def create_i_signal_length(parent=None, value=None):
        length = autosar44.INTEGER(valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "LENGTH"):
            parent.LENGTH = length
        return length

    @staticmethod
    def create_i_signal_to_pdu_mappings(parent=None, mapping_list=None):
        i_signal_to_pdu_mappings = autosar44.I_SIGNAL_TO_PDU_MAPPINGSType(
            I_SIGNAL_TO_I_PDU_MAPPING=mapping_list, parent_object_=parent
        )
        if parent and hasattr(parent, "I_SIGNAL_TO_PDU_MAPPINGS"):
            parent.I_SIGNAL_TO_PDU_MAPPINGS = i_signal_to_pdu_mappings
        return i_signal_to_pdu_mappings

    @staticmethod
    def create_i_signal_to_i_pdu_mapping(parent=None, short_name=None):
        # short_name_obj = autosar44.IDENTIFIER(valueOf_ = short_name)
        rv_obj = autosar44.I_SIGNAL_TO_I_PDU_MAPPING(parent_object_=parent)
        set_short_name_tag_value(parent, rv_obj, short_name)
        rv_obj.set_tag("I-SIGNAL-TO-I-PDU-MAPPING")
        if parent and hasattr(parent, "I_SIGNAL_TO_I_PDU_MAPPING"):
            if isinstance(parent.I_SIGNAL_TO_I_PDU_MAPPING, list):
                parent.I_SIGNAL_TO_I_PDU_MAPPING.append(rv_obj)
        return rv_obj

    @staticmethod
    def create_i_signal_ref(parent=None, value=None):
        i_signal_ref = autosar44.I_SIGNAL_REFType(DEST="I-SIGNAL", valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "I_SIGNAL_REF"):
            parent.I_SIGNAL_REF = i_signal_ref
        return i_signal_ref

    @staticmethod
    def create_i_signal_group_ref(parent=None, value=None):
        rv = autosar44.I_SIGNAL_GROUP_REFType2781(DEST="I-SIGNAL-GROUP", valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "I_SIGNAL_GROUP_REF"):
            parent.I_SIGNAL_GROUP_REF = rv
        return rv

    @staticmethod
    def create_packing_byte_order(parent=None, value=None):
        byte_order = autosar44.BYTE_ORDER_ENUM(valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "PACKING_BYTE_ORDER"):
            parent.PACKING_BYTE_ORDER = byte_order
        return byte_order

    @staticmethod
    def create_start_position(parent=None, value=None):
        start_position = autosar44.INTEGER(valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "START_POSITION"):
            parent.START_POSITION = start_position
        return start_position

    @staticmethod
    def create_transfer_property(parent=None, value=None):
        transfer_property = autosar44.TRANSFER_PROPERTY_ENUM(valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "TRANSFER_PROPERTY"):
            parent.TRANSFER_PROPERTY = transfer_property
        return transfer_property

    @staticmethod
    def creae_i_pdu_timing_specifications(parent, value_dict):
        i_pdu_timing_specifications = creat_container_from_tag_name(parent, "I_PDU_TIMING_SPECIFICATIONS")
        i_pdu_timing = creat_container_from_tag_name(i_pdu_timing_specifications, "I_PDU_TIMING")
        transmission_mode_declaration = creat_container_from_tag_name(i_pdu_timing, "TRANSMISSION_MODE_DECLARATION")
        transmission_mode_true_timing = creat_container_from_tag_name(
            transmission_mode_declaration, "TRANSMISSION_MODE_TRUE_TIMING"
        )
        cyclic_timing = creat_container_from_tag_name(transmission_mode_true_timing, "CYCLIC_TIMING")
        time_period = creat_container_from_tag_name(cyclic_timing, "TIME_PERIOD")
        set_tag_value(time_period, "VALUE", str(value_dict.get("time_period", "0")))
        time_offset = creat_container_from_tag_name(cyclic_timing, "TIME_OFFSET")
        set_tag_value(time_offset, "VALUE", str(value_dict.get("time_offset", "0")))
        return i_pdu_timing_specifications

    @staticmethod
    def create_full_i_signal_to_i_pdu_mapping(
        parent, signal_name, signal_ref, byte_order, start_position, transfer_property
    ):
        """
        create i_signal_to_i_pdu_mapping and its children, and set the values
        """
        i_signal_to_i_pdu_mapping = ISignalIPdu.create_i_signal_to_i_pdu_mapping(parent, signal_name)
        ISignalIPdu.create_i_signal_ref(i_signal_to_i_pdu_mapping, value=signal_ref)
        ISignalIPdu.create_packing_byte_order(i_signal_to_i_pdu_mapping, value=byte_order)
        ISignalIPdu.create_start_position(i_signal_to_i_pdu_mapping, value=start_position)
        ISignalIPdu.create_transfer_property(i_signal_to_i_pdu_mapping, value=transfer_property)
        return i_signal_to_i_pdu_mapping

    @staticmethod
    def create_full_i_signal_i_pdu(parent, pdu):
        i_signal_i_pdu = ISignalIPdu.create_i_signal_i_pdu(parent, pdu["short_name"])
        ISignalIPdu.creae_i_pdu_timing_specifications(
            i_signal_i_pdu, pdu["i_pdu_timing"]["transmission_mode_true_timing"]
        )
        ISignalIPdu.create_i_signal_length(i_signal_i_pdu, pdu["length"])
        i_signal_to_pdu_mappings = ISignalIPdu.create_i_signal_to_pdu_mappings(i_signal_i_pdu)
        for i_signal in pdu["i_signal_to_i_pdu_mappings"]["i_signals"]:
            i_signal_to_i_pdu_mapping = ISignalIPdu.create_i_signal_to_i_pdu_mapping(
                i_signal_to_pdu_mappings, i_signal["short_name"]
            )
            ISignalIPdu.create_i_signal_ref(i_signal_to_i_pdu_mapping, value=i_signal["i_signal_ref"])
            ISignalIPdu.create_packing_byte_order(i_signal_to_i_pdu_mapping, value=i_signal["packing_byte_order"])
            ISignalIPdu.create_start_position(i_signal_to_i_pdu_mapping, value=i_signal["start_position"])
            ISignalIPdu.create_transfer_property(i_signal_to_i_pdu_mapping, value=i_signal["transfer_property"])
            # ISignalIPdu.create_full_i_signal_to_i_pdu_mapping(
            #     i_signal_to_pdu_mappings, i_signal["short_name"], i_signal["i_signal_ref"],
            #     i_signal["packing_byte_order"], i_signal["start_position"], i_signal["transfer_property"])
        for i_signal_group in pdu["i_signal_to_i_pdu_mappings"]["i_signal_groups"]:
            i_signal_to_i_pdu_mapping = ISignalIPdu.create_i_signal_to_i_pdu_mapping(
                i_signal_to_pdu_mappings, i_signal_group["short_name"]
            )
            ISignalIPdu.create_i_signal_group_ref(i_signal_to_i_pdu_mapping, value=i_signal_group["i_signal_group_ref"])
            ISignalIPdu.create_transfer_property(i_signal_to_i_pdu_mapping, value=i_signal_group["transfer_property"])
        return i_signal_i_pdu

    @staticmethod
    def create_nm_pdu(parent=None, short_name=None):
        # short_name_obj = autosar44.IDENTIFIER(valueOf_ = short_name)
        rv_obj = autosar44.NM_PDU(parent_object_=parent)
        set_short_name_tag_value(parent, rv_obj, short_name)
        rv_obj.set_tag("NM-PDU")
        if parent and hasattr(parent, "NM_PDU"):
            if isinstance(parent.NM_PDU, list):
                parent.NM_PDU.append(rv_obj)
        return rv_obj

    @staticmethod
    def create_i_signal_to_i_pdu_mappings(parent=None, mapping_list=None):
        i_signal_to_i_pdu_mappings = autosar44.I_SIGNAL_TO_I_PDU_MAPPINGSType3345(
            I_SIGNAL_TO_I_PDU_MAPPING=mapping_list, parent_object_=parent
        )
        if parent and hasattr(parent, "I_SIGNAL_TO_I_PDU_MAPPINGS"):
            parent.I_SIGNAL_TO_I_PDU_MAPPINGS = i_signal_to_i_pdu_mappings
        return i_signal_to_i_pdu_mappings

    @staticmethod
    def create_full_nm_pdu(parent, pdu):
        nm_pdu = ISignalIPdu.create_nm_pdu(parent, pdu["short_name"])
        ISignalIPdu.creae_i_pdu_timing_specifications(nm_pdu, pdu["i_pdu_timing"]["transmission_mode_true_timing"])
        ISignalIPdu.create_i_signal_length(nm_pdu, pdu["length"])
        i_signal_to_pdu_mappings = ISignalIPdu.create_i_signal_to_i_pdu_mappings(nm_pdu)
        for i_signal in pdu["i_signal_to_i_pdu_mappings"]["i_signals"]:
            i_signal_to_i_pdu_mapping = ISignalIPdu.create_i_signal_to_i_pdu_mapping(
                i_signal_to_pdu_mappings, i_signal["short_name"]
            )
            ISignalIPdu.create_i_signal_ref(i_signal_to_i_pdu_mapping, value=i_signal["i_signal_ref"])
            ISignalIPdu.create_packing_byte_order(i_signal_to_i_pdu_mapping, value=i_signal["packing_byte_order"])
            ISignalIPdu.create_start_position(i_signal_to_i_pdu_mapping, value=i_signal["start_position"])
            ISignalIPdu.create_transfer_property(i_signal_to_i_pdu_mapping, value=i_signal["transfer_property"])
        return nm_pdu


# PDU ELEMENTS end


# ISignal ELEMENTS start
class ISignal:
    @staticmethod
    def create_i_signal(parent=None, short_name=None):
        # short_name_obj = autosar44.IDENTIFIER(valueOf_ = short_name)
        rv_obj = autosar44.I_SIGNAL(parent_object_=parent)
        set_short_name_tag_value(parent, rv_obj, short_name)
        rv_obj.set_tag("I-SIGNAL")
        if parent and hasattr(parent, "I_SIGNAL"):
            if isinstance(parent.I_SIGNAL, list):
                parent.I_SIGNAL.append(rv_obj)
        return rv_obj

    @staticmethod
    def create_data_type_policy(parent=None, value=None):
        data_type_policy = autosar44.DATA_TYPE_POLICY_ENUM(valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "DATA_TYPE_POLICY"):
            parent.DATA_TYPE_POLICY = data_type_policy
        return data_type_policy

    @staticmethod
    def create_i_signal_type(parent=None, value=None):
        i_signal_type = autosar44.I_SIGNAL_TYPE_ENUM(valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "I_SIGNAL_TYPE"):
            parent.I_SIGNAL_TYPE = i_signal_type
        return i_signal_type

    @staticmethod
    def create_init_value(parent=None, value=None):
        init_value = autosar44.INIT_VALUEType2747(valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "INIT_VALUE"):
            parent.INIT_VALUE = init_value
        return init_value

    @staticmethod
    def create_numerical_value_specification(parent=None, value=None):
        rv = autosar44.NUMERICAL_VALUE_SPECIFICATION(valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "NUMERICAL_VALUE_SPECIFICATION"):
            parent.NUMERICAL_VALUE_SPECIFICATION = rv
        return rv

    @staticmethod
    def create_numerical_value_variation_point(parent=None, value=None):
        rv = autosar44.NUMERICAL_VALUE_VARIATION_POINT(valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "VALUE"):
            parent.VALUE = rv
        return rv

    @staticmethod
    def create_i_signal_length(parent=None, value=None):
        length = autosar44.INTEGER(valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "LENGTH"):
            parent.LENGTH = length
        return length

    @staticmethod
    def create_network_representation_props(parent=None):
        rv = autosar44.SW_DATA_DEF_PROPS(parent_object_=parent)
        if parent and hasattr(parent, "NETWORK_REPRESENTATION_PROPS"):
            parent.NETWORK_REPRESENTATION_PROPS = rv
        return rv

    @staticmethod
    def creat_sw_data_def_props_variants(parent=None):
        rv = autosar44.SW_DATA_DEF_PROPS_VARIANTSType4706(parent_object_=parent)
        if parent and hasattr(parent, "SW_DATA_DEF_PROPS_VARIANTS"):
            parent.SW_DATA_DEF_PROPS_VARIANTS = rv
        return rv

    @staticmethod
    def create_sw_data_def_props_conditional(parent=None):
        rv = autosar44.SW_DATA_DEF_PROPS_CONDITIONAL(parent_object_=parent)
        if parent and hasattr(parent, "SW_DATA_DEF_PROPS_CONDITIONAL"):
            if isinstance(parent.SW_DATA_DEF_PROPS_CONDITIONAL, list):
                parent.SW_DATA_DEF_PROPS_CONDITIONAL.append(rv)
        return rv

    @staticmethod
    def create_base_type_ref(parent=None, value=None):
        rv = autosar44.BASE_TYPE_REFType4709(valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "BASE_TYPE_REF"):
            parent.BASE_TYPE_REF = rv
        return rv

    @staticmethod
    def create_system_signal_ref(parent=None, value=None):
        rv = autosar44.SYSTEM_SIGNAL_REFType(DEST="SYSTEM-SIGNAL", valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "SYSTEM_SIGNAL_REF"):
            parent.SYSTEM_SIGNAL_REF = rv
        return rv

    @staticmethod
    def create_i_signal_group(parent=None, short_name=None):
        # short_name_obj = autosar44.IDENTIFIER(valueOf_ = short_name)
        rv_obj = autosar44.I_SIGNAL_GROUP(parent_object_=parent)
        set_short_name_tag_value(parent, rv_obj, short_name)
        rv_obj.set_tag("I-SIGNAL-GROUP")
        if parent and hasattr(parent, "I_SIGNAL_GROUP"):
            if isinstance(parent.I_SIGNAL_GROUP, list):
                parent.I_SIGNAL_GROUP.append(rv_obj)
        return rv_obj

    @staticmethod
    def create_system_signal_group_ref(parent=None, value=None):
        rv = autosar44.SYSTEM_SIGNAL_GROUP_REFType(DEST="SYSTEM-SIGNAL-GROUP", valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "SYSTEM_SIGNAL_GROUP_REF"):
            parent.SYSTEM_SIGNAL_GROUP_REF = rv
        return rv

    @staticmethod
    def create_i_signal_refs(parent=None, i_signal_list=None):
        i_signal_refs = autosar44.I_SIGNAL_REFSType(I_SIGNAL_REF=i_signal_list, parent_object_=parent)
        if parent and hasattr(parent, "I_SIGNAL_REFS"):
            parent.I_SIGNAL_REFS = i_signal_refs
        return i_signal_refs

    @staticmethod
    def create_full_i_signal(parent, signal):
        """
        creat a i-signal
        """
        i_signal = ISignal.create_i_signal(parent, signal["short_name"])
        ISignal.create_data_type_policy(i_signal, signal["data_type_policy"])
        ISignal.create_i_signal_type(i_signal, signal["i_signal_type"])
        init_value = ISignal.create_init_value(i_signal)
        numerical_value_specification = ISignal.create_numerical_value_specification(init_value)
        ISignal.create_numerical_value_variation_point(numerical_value_specification, signal["init_value"])
        ISignal.create_i_signal_length(i_signal, signal["length"])
        network_representation_props = ISignal.create_network_representation_props(i_signal)
        sw_data_def_props_variants = ISignal.creat_sw_data_def_props_variants(network_representation_props)
        sw_data_def_props_conditional = ISignal.create_sw_data_def_props_conditional(sw_data_def_props_variants)
        ISignal.create_base_type_ref(sw_data_def_props_conditional, signal["base_type_ref"])
        ISignal.create_system_signal_ref(i_signal, signal["system_signal_ref"])
        return i_signal

    @staticmethod
    def create_i_signal_ref(parent=None, value=None):
        i_signal_ref = autosar44.I_SIGNAL_REFType(DEST="I-SIGNAL", valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "I_SIGNAL_REFS") and parent.I_SIGNAL_REFS:
            if isinstance(parent.I_SIGNAL_REFS.I_SIGNAL_REF, list):
                parent.I_SIGNAL_REFS.I_SIGNAL_REF.append(i_signal_ref)
        return i_signal_ref

    @staticmethod
    def create_full_i_signal_group(parent, signal_group):
        """
        creat a i-signal-group
        """
        i_signal_group = ISignal.create_i_signal_group(parent, signal_group["short_name"])
        ISignal.create_i_signal_refs(i_signal_group)
        for i_signal_ref in signal_group["i_signal_refs"]:
            ISignal.create_i_signal_ref(i_signal_group, i_signal_ref)
        ISignal.create_system_signal_group_ref(i_signal_group, signal_group["system_signal_group_ref"])
        return i_signal_group

    @staticmethod
    def create_full_i_signals_and_i_signal_groups(parent, signal_and_signalgroup):
        """
        creat i-signals and i-signal-groups
        """
        for signal in signal_and_signalgroup["i_signals"]:
            ISignal.create_full_i_signal(parent, signal)
        for signal_group in signal_and_signalgroup["i_signal_groups"]:
            ISignal.create_full_i_signal_group(parent, signal_group)


# ISignal ELEMENTS end


# Signal ELEMENTS (system signal) start
class SystemSignal:

    @staticmethod
    def create_system_signal(parent=None, short_name=None):
        # short_name_obj = autosar44.IDENTIFIER(valueOf_ = short_name)
        rv_obj = autosar44.SYSTEM_SIGNAL(parent_object_=parent)
        set_short_name_tag_value(parent, rv_obj, short_name)
        rv_obj.set_tag("SYSTEM-SIGNAL")
        if parent and hasattr(parent, "SYSTEM_SIGNAL"):
            if isinstance(parent.SYSTEM_SIGNAL, list):
                parent.SYSTEM_SIGNAL.append(rv_obj)
        return rv_obj

    @staticmethod
    def create_dynamic_length(parent=None, value=None):
        rv = autosar44.BOOLEAN(valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "DYNAMIC_LENGTH"):
            parent.DYNAMIC_LENGTH = rv
        return rv

    @staticmethod
    def create_physical_props(parent=None):
        rv = autosar44.SW_DATA_DEF_PROPS(parent_object_=parent)
        if parent and hasattr(parent, "PHYSICAL_PROPS"):
            parent.PHYSICAL_PROPS = rv
        return rv

    @staticmethod
    def creat_sw_data_def_props_variants(parent=None):
        rv = autosar44.SW_DATA_DEF_PROPS_VARIANTSType4706(parent_object_=parent)
        if parent and hasattr(parent, "SW_DATA_DEF_PROPS_VARIANTS"):
            parent.SW_DATA_DEF_PROPS_VARIANTS = rv
        return rv

    @staticmethod
    def create_sw_data_def_props_conditional(parent=None):
        rv = autosar44.SW_DATA_DEF_PROPS_CONDITIONAL(parent_object_=parent)
        if parent and hasattr(parent, "SW_DATA_DEF_PROPS_CONDITIONAL"):
            if isinstance(parent.SW_DATA_DEF_PROPS_CONDITIONAL, list):
                parent.SW_DATA_DEF_PROPS_CONDITIONAL.append(rv)
        return rv

    @staticmethod
    def create_compu_method_ref(parent=None, value=None):
        rv = autosar44.COMPU_METHOD_REFType4710(valueOf_=value, DEST="COMPU-METHOD", parent_object_=parent)
        if parent and hasattr(parent, "COMPU_METHOD_REF"):
            parent.COMPU_METHOD_REF = rv
        return rv

    @staticmethod
    def create_data_constr_ref(parent=None, value=None):
        rv = autosar44.DATA_CONSTR_REFType4711(valueOf_=value, DEST="DATA-CONSTR", parent_object_=parent)
        if parent and hasattr(parent, "DATA_CONSTR_REF"):
            parent.DATA_CONSTR_REF = rv
        return rv

    @staticmethod
    def create_unit_ref(parent=None, value=None):
        rv = autosar44.UNIT_REFType4714(valueOf_=value, DEST="UNIT", parent_object_=parent)
        if parent and hasattr(parent, "UNIT_REF"):
            parent.UNIT_REF = rv
        return rv

    @staticmethod
    def create_system_signal_group(parent=None, short_name=None):
        # short_name_obj = autosar44.IDENTIFIER(valueOf_ = short_name)
        rv_obj = autosar44.SYSTEM_SIGNAL_GROUP(parent_object_=parent)
        set_short_name_tag_value(parent, rv_obj, short_name)
        rv_obj.set_tag("SYSTEM-SIGNAL-GROUP")
        if parent and hasattr(parent, "SYSTEM_SIGNAL_GROUP"):
            if isinstance(parent.SYSTEM_SIGNAL_GROUP, list):
                parent.SYSTEM_SIGNAL_GROUP.append(rv_obj)
        return rv_obj

    @staticmethod
    def create_system_signal_refs(parent=None, value=None):
        rv = autosar44.SYSTEM_SIGNAL_REFSType4970(valueOf_=value, parent_object_=parent)
        if parent and hasattr(parent, "SYSTEM_SIGNAL_REFS"):
            parent.SYSTEM_SIGNAL_REFS = rv
        return rv

    @staticmethod
    def create_system_signal_ref(parent=None, value=None):
        rv = autosar44.TRANSFORMING_SYSTEM_SIGNAL_REFType4972(
            valueOf_=value, DEST="SYSTEM-SIGNAL", parent_object_=parent
        )
        if parent and hasattr(parent, "SYSTEM_SIGNAL_REF"):
            if isinstance(parent.SYSTEM_SIGNAL_REF, list):
                parent.SYSTEM_SIGNAL_REF.append(rv)
        return rv

    @staticmethod
    def create_full_system_signal(parent, signal):
        """
        system_signal
            |-short_name
            |-desc(TBD)
            |-dynamic_length
            |-physical_props
                |-sw_data_def_props_variants
                    |-sw_data_def_props_conditional
                        |-compu_method_ref
                        |-data_constr_ref
                        |-unit_ref(TBD)
        """
        if parent.find("/Signal/" + signal["short_name"]) is not None:
            return
        system_signal = SystemSignal.create_system_signal(parent, signal["short_name"])
        SystemSignal.create_dynamic_length(system_signal, signal["dynamic_length"])
        physical_props = SystemSignal.create_physical_props(system_signal)
        sw_data_def_props_variants = SystemSignal.creat_sw_data_def_props_variants(physical_props)
        sw_data_def_props_conditional = SystemSignal.create_sw_data_def_props_conditional(sw_data_def_props_variants)
        SystemSignal.create_compu_method_ref(sw_data_def_props_conditional, signal["compu_method_ref"])
        SystemSignal.create_data_constr_ref(sw_data_def_props_conditional, signal["data_constr_ref"])
        return system_signal

    @staticmethod
    def create_full_system_signal_group(parent, signal_group):
        """
        system_signal_group

        """
        system_signal_group = SystemSignal.create_system_signal_group(parent, signal_group["short_name"])
        system_signal_refs = SystemSignal.create_system_signal_refs(system_signal_group)
        for system_signal_ref in signal_group["system_signal_refs"]:
            SystemSignal.create_system_signal_ref(system_signal_refs, system_signal_ref)
        return system_signal_group

    @staticmethod
    def create_full_system_signals_and_signal_groups(parent, signal_and_group):
        for signal in signal_and_group["system_signals"]:
            SystemSignal.create_full_system_signal(parent, signal)
        for signal_group in signal_and_group["system_signal_groups"]:
            SystemSignal.create_full_system_signal_group(parent, signal_group)


# Signal ELEMENTS end


def get_system_signal_info(communication, system_signal_name):
    rv = {}
    info = {}
    if system_signal_name.startswith("/Signal"):
        sys_signal_ref = system_signal_name
    else:
        sys_signal_ref = f"/Signal/{system_signal_name}"
    sys_signal = communication.find(sys_signal_ref)
    if sys_signal is not None:
        i_signal_list = communication.find_nodes("I-SIGNAL")
        i_signal_group_list = communication.find_nodes("I-SIGNAL-GROUP")
        for i_signal in i_signal_list:
            if i_signal.SYSTEM_SIGNAL_REF and sys_signal_ref == i_signal.SYSTEM_SIGNAL_REF.get_valueOf_():
                break
        else:
            return {}
        info["system_signal"] = sys_signal_ref.split("/")[-1]
        info["system_signal_ref"] = sys_signal_ref
        info["i_signal"] = get_short_name(i_signal)
        info["i_signal_ref"] = "/ISignal/" + get_short_name(i_signal)
        if i_signal.LENGTH and hasattr(i_signal.LENGTH, "valueOf_"):
            info["length"] = i_signal.LENGTH.valueOf_
        i_signal_i_pdu_list = communication.find_nodes("I-SIGNAL-I-PDU")
        for i_signal_i_pdu in i_signal_i_pdu_list:
            for i_signal_to_pdu_mapping in i_signal_i_pdu.I_SIGNAL_TO_PDU_MAPPINGS:
                if (
                    i_signal_to_pdu_mapping.I_SIGNAL_REF
                    and info["i_signal_ref"] == i_signal_to_pdu_mapping.I_SIGNAL_REF.get_valueOf_()
                ):
                    break
            else:
                pass
    return rv


def get_all_communication_system_signals(communication):
    rv = {}
    system_signal = {}
    i_signal_i_pdu_dict = {}
    i_signal_i_pdu_list = communication.find_nodes("I-SIGNAL-I-PDU")
    for i_signal_i_pdu in i_signal_i_pdu_list:
        i_signal_i_pdu_short_name = get_short_name(i_signal_i_pdu)
        pdu_len = _get_value_by_attrs(i_signal_i_pdu, ["LENGTH", "valueOf_"])
        i_signal_i_pdu_temp = {}
        i_signal_i_pdu_temp["short_name"] = i_signal_i_pdu_short_name
        i_signal_i_pdu_temp["length"] = pdu_len
        mappings = _get_value_by_attrs(i_signal_i_pdu, ["I_SIGNAL_TO_PDU_MAPPINGS", "I_SIGNAL_TO_I_PDU_MAPPING"])
        if isinstance(mappings, list):
            for mapping in mappings:
                mapping_short_name = get_short_name(mapping)
                i_signal_ref = _get_value_by_attrs(mapping, ["I_SIGNAL_REF", "valueOf_"])
                i_signal_obj = communication.find(i_signal_ref)
                i_signal_dict = get_i_signal_dict_from_obj(i_signal_obj)

        else:
            continue
    return rv


def get_i_signal_dict_from_obj(obj):
    rv = {}
    rv["short_name"] = get_short_name(obj)
    length = _get_value_by_attrs(obj, ["LENGTH", "valueOf_"])
    if isinstance(length, str) and length.isdigit():
        rv["length"] = int(length)
    else:
        return
    base_type_ref_list = _get_value_by_attrs(
        obj, ["NETWORK_REPRESENTATION_PROPS", "SW_DATA_DEF_PROPS_VARIANTS", "SW_DATA_DEF_PROPS_CONDITIONAL"]
    )
    if isinstance(base_type_ref_list, list) and len(base_type_ref_list):
        rv["base_type_ref"] = _get_value_by_attrs(base_type_ref_list[0], ["BASE_TYPE_REF", "valueOf_"])
    else:
        rv["base_type_ref"] = ""
    rv["system_signal_ref"] = _get_value_by_attrs(obj, ["SYSTEM_SIGNAL_REF", "valueOf_"])
    if _dict_has_empty_val(rv):
        return None
    return rv


def get_i_signal_group_dict_from_obj(obj):
    rv = {}
    rv["short_name"] = get_short_name(obj)
    rv["i_signal_refs"] = []
    i_signal_refs = _get_value_by_attrs(obj, ["I_SIGNAL_REFS", "I_SIGNAL_REF"])
    system_signal_group_ref = _get_value_by_attrs(obj, ["SYSTEM_SIGNAL_GROUP_REF", "valueOf_"])
    rv["system_signal_group_ref"] = system_signal_group_ref
    if isinstance(i_signal_refs, list) and len(i_signal_refs):
        for ref in i_signal_refs:
            i_signal_ref = _get_value_by_attrs(ref, ["valueOf_"])
            rv["i_signal_refs"].append(i_signal_ref)
    if _dict_has_empty_val(rv):
        return None
    return rv


def get_i_signal_i_pdu_dict_from_obj(obj, pdu_type="app"):
    rv = {}
    rv["short_name"] = get_short_name(obj)
    length = _get_value_by_attrs(obj, ["LENGTH", "valueOf_"])
    if isinstance(length, str) and length.isdigit():
        rv["length"] = int(length)
    else:
        return
    rv["i_signal_to_i_pdu_mapping"] = {}
    rv["i_signal_group_to_i_pdu_mapping"] = {}

    i_pdu_timing_list = _get_value_by_attrs(obj, ["I_PDU_TIMING_SPECIFICATIONS", "I_PDU_TIMING"])
    time_period = "0"
    if isinstance(i_pdu_timing_list, list) and len(i_pdu_timing_list) > 0:
        para_list = [
            "TRANSMISSION_MODE_DECLARATION",
            "TRANSMISSION_MODE_TRUE_TIMING",
            "CYCLIC_TIMING",
            "TIME_PERIOD",
            "VALUE",
            "valueOf_",
        ]
        time_period = _get_value_by_attrs(i_pdu_timing_list[0], para_list)
        if time_period is None:
            time_period = "0"
    rv["pdu_period"] = time_period

    if pdu_type == "app":
        i_signal_to_i_pdu_mappings = _get_value_by_attrs(obj, ["I_SIGNAL_TO_PDU_MAPPINGS", "I_SIGNAL_TO_I_PDU_MAPPING"])
    elif pdu_type == "nm":
        i_signal_to_i_pdu_mappings = _get_value_by_attrs(
            obj, ["I_SIGNAL_TO_I_PDU_MAPPINGS", "I_SIGNAL_TO_I_PDU_MAPPING"]
        )
    else:
        return rv

    if isinstance(i_signal_to_i_pdu_mappings, list):
        for i_signal_to_i_pdu_mapping_obj in i_signal_to_i_pdu_mappings:
            mapping = {}
            mapping["short_name"] = get_short_name(i_signal_to_i_pdu_mapping_obj)
            i_signal_ref = _get_value_by_attrs(i_signal_to_i_pdu_mapping_obj, ["I_SIGNAL_REF", "valueOf_"])
            i_signal_group_ref = _get_value_by_attrs(i_signal_to_i_pdu_mapping_obj, ["I_SIGNAL_GROUP_REF", "valueOf_"])
            if i_signal_ref:
                mapping["i_signal_ref"] = i_signal_ref
                rv["i_signal_to_i_pdu_mapping"].update({mapping["i_signal_ref"].split("/")[-1]: mapping})
            elif i_signal_group_ref:
                mapping["i_signal_group_ref"] = i_signal_group_ref
                rv["i_signal_group_to_i_pdu_mapping"].update({mapping["i_signal_group_ref"].split("/")[-1]: mapping})
    return rv


def get_i_pdu_group_dict_from_obj(obj):
    rv = {}
    rv["short_name"] = get_short_name(obj)
    rv["i_signal_i_pdu_ref_list"] = []
    rv["communication_direction"] = _get_value_by_attrs(obj, ["COMMUNICATION_DIRECTION", "valueOf_"])
    i_signal_i_pdu_ref_conditional_list = _get_value_by_attrs(
        obj, ["I_SIGNAL_I_PDUS", "I_SIGNAL_I_PDU_REF_CONDITIONAL"]
    )
    for i_signal_i_pdu_ref_conditional_obj in i_signal_i_pdu_ref_conditional_list:
        i_signal_i_pdu_ref = _get_value_by_attrs(i_signal_i_pdu_ref_conditional_obj, ["I_SIGNAL_I_PDU_REF", "valueOf_"])
        rv["i_signal_i_pdu_ref_list"].append(i_signal_i_pdu_ref)
    if _dict_has_empty_val(rv):
        return None
    return rv


def get_system_signal_group_dict_from_obj(obj):
    rv = {}
    rv["short_name"] = get_short_name(obj)
    rv["system_signal_refs"] = []
    system_signal_refs = _get_value_by_attrs(obj, ["SYSTEM_SIGNAL_REFS", "SYSTEM_SIGNAL_REF"])
    if isinstance(system_signal_refs, list) and len(system_signal_refs):
        for ref in system_signal_refs:
            system_signal_ref = _get_value_by_attrs(ref, ["valueOf_"])
            rv["system_signal_refs"].append(system_signal_ref)
    if _dict_has_empty_val(rv):
        return None
    return rv


def get_all_system_signal_mapping_info(communication):
    """
    获得所有system signal->i signal->pdu(i signal i pdu)的关系字典
    """
    i_signal_dict = {}
    i_signal_group_dict = {}
    i_signal_i_pdu_dict = {}
    i_pdu_group_dict = {}
    system_signal_group_dict = {}

    if not communication:
        logger.error("Communication is not AUTOSAR object")
        return

    i_pdu_group_obj_list = communication.find_nodes("I-SIGNAL-I-PDU-GROUP")
    for i_pdu_group_obj in i_pdu_group_obj_list:
        i_pdu_group_temp = get_i_pdu_group_dict_from_obj(i_pdu_group_obj)
        if i_pdu_group_temp is None:
            continue
        i_pdu_group_short_name = i_pdu_group_temp["short_name"]
        i_pdu_group_dict.update({i_pdu_group_short_name: i_pdu_group_temp})

    i_signal_obj_list = communication.find_nodes("I-SIGNAL")
    for i_signal_obj in i_signal_obj_list:
        i_signal_temp = get_i_signal_dict_from_obj(i_signal_obj)
        if i_signal_temp is None:
            continue
        i_signal_short_name = i_signal_temp["short_name"]
        i_signal_dict.update({i_signal_short_name: i_signal_temp})

    i_signal_group_obj_list = communication.find_nodes("I-SIGNAL-GROUP")
    for i_signal_group_obj in i_signal_group_obj_list:
        i_signal_group_temp = get_i_signal_group_dict_from_obj(i_signal_group_obj)
        if i_signal_group_temp is None:
            continue
        i_signal_group_short_name = i_signal_group_temp["short_name"]
        i_signal_group_dict.update({i_signal_group_short_name: i_signal_group_temp})

    system_signal_group_obj_list = communication.find_nodes("SYSTEM-SIGNAL-GROUP")
    for system_signal_group_obj in system_signal_group_obj_list:
        system_signal_group_temp = get_system_signal_group_dict_from_obj(system_signal_group_obj)
        if system_signal_group_temp is None:
            continue
        short_name = system_signal_group_temp["short_name"]
        system_signal_group_dict.update({short_name: system_signal_group_temp})

    pdu_obj_dict = {}
    pdu_obj_dict["app"] = communication.find_nodes("I-SIGNAL-I-PDU")
    pdu_obj_dict["nm"] = communication.find_nodes("NM-PDU")
    if not isinstance(pdu_obj_dict["app"], list):
        pdu_obj_dict["app"] = []
    if not isinstance(pdu_obj_dict["nm"], list):
        pdu_obj_dict["nm"] = []
    for pdu_type, pdu_obj_list in pdu_obj_dict.items():
        for i_signal_i_pdu_obj in pdu_obj_list:
            i_signal_i_pdu_temp = get_i_signal_i_pdu_dict_from_obj(i_signal_i_pdu_obj, pdu_type)
            if i_signal_i_pdu_temp is None:
                continue
            i_signal_short_name = i_signal_i_pdu_temp["short_name"]
            i_signal_i_pdu_dict.update({i_signal_short_name: i_signal_i_pdu_temp})

    rv_system_signal_table = mapping_system_signal_i_signa_pdu(
        i_signal_dict, i_signal_group_dict, i_signal_i_pdu_dict, i_pdu_group_dict, system_signal_group_dict
    )
    return rv_system_signal_table


def mapping_system_signal_i_signa_pdu(
    i_signals, i_signal_groups, i_signal_i_pdus, i_pdu_group_dict, system_signal_group_dict
):
    rv = {
        "Tx": {"system_signal": {}, "system_signal_group": {}},
        "Rx": {"system_signal": {}, "system_signal_group": {}},
    }
    for pdu_name, i_signal_i_pdu in i_signal_i_pdus.items():
        direction = _get_pdu_direction(i_pdu_group_dict, pdu_name)
        if direction == "IN":
            direction = "Rx"
        elif direction == "OUT":
            direction = "Tx"
        else:
            continue
        for i_signal_short_name, i_signal_mapping in i_signal_i_pdu["i_signal_to_i_pdu_mapping"].items():
            map_info = i_signals.get(i_signal_short_name)
            if isinstance(map_info, dict):
                mapping_dict = {}
                mapping_dict["system_signal"] = map_info["system_signal_ref"].split("/")[-1]
                mapping_dict["short_name"] = mapping_dict["system_signal"]
                mapping_dict["direction"] = direction
                mapping_dict["base_type_ref"] = map_info["base_type_ref"]
                mapping_dict["length"] = map_info["length"]
                mapping_dict["i_signal_ref"] = i_signal_mapping["i_signal_ref"]
                mapping_dict["pdu"] = pdu_name
                mapping_dict["signal_type"] = "system_signal"
                mapping_dict["full_name"] = mapping_dict["i_signal_ref"].split("/")[-1]
                mapping_dict["pdu_period"] = i_signal_i_pdu["pdu_period"]
                rv[direction]["system_signal"].update({mapping_dict["system_signal"]: mapping_dict})
        for i_signal_group_short_name, i_signal_group_mapping in i_signal_i_pdu[
            "i_signal_group_to_i_pdu_mapping"
        ].items():
            map_info = i_signal_groups.get(i_signal_group_short_name)
            if isinstance(map_info, dict):
                mapping_dict = {}
                mapping_dict["i_signal_refs"] = []
                mapping_dict["system_signal_group"] = map_info["system_signal_group_ref"].split("/")[-1]
                mapping_dict["short_name"] = mapping_dict["system_signal_group"]
                mapping_dict["system_signal_refs"] = system_signal_group_dict.get(
                    mapping_dict["system_signal_group"], {}
                ).get("system_signal_refs", [])
                mapping_dict["direction"] = direction
                for ref in map_info["i_signal_refs"]:
                    mapping_dict["i_signal_refs"].append(ref)
                mapping_dict["pdu"] = pdu_name
                mapping_dict["signal_type"] = "system_signal_group"
                mapping_dict["full_name"] = i_signal_group_short_name
                mapping_dict["system_signal_to_i_signal"] = {}
                mapping_dict["pdu_period"] = i_signal_i_pdu["pdu_period"]
                mapping_dict["system_signal"] = {}
                for sys_signal_ref in mapping_dict["system_signal_refs"]:
                    sys_signal = sys_signal_ref.split("/")[-1]
                    i_signal = rv[direction]["system_signal"].get(sys_signal, None)
                    if i_signal is None:
                        logger.warning(f"sysyem signal: {sys_signal} not found i-signal!")
                        break
                    mapping_dict["system_signal_to_i_signal"].update({sys_signal: i_signal["full_name"]})
                    mapping_dict["system_signal"].update({sys_signal: i_signal})
                    rv[direction]["system_signal"].pop(sys_signal)
                rv[direction]["system_signal_group"].update({mapping_dict["system_signal_group"]: mapping_dict})
    return rv


def _get_pdu_direction(i_pdu_group_dict, pdu):
    for pdu_group in i_pdu_group_dict.values():
        if f"/PDU/{pdu}" in pdu_group["i_signal_i_pdu_ref_list"]:
            return pdu_group["communication_direction"]
    return None


def _get_value_by_attrs(obj, attrs_list):
    find_value = obj
    if attrs_list is None or len(attrs_list) == 0:
        return None
    for attr in attrs_list:
        if hasattr(find_value, attr):
            find_value = getattr(find_value, attr)
            if find_value is None:
                return None
        else:
            return None
    return find_value


def _dict_has_empty_val(dic):
    if not dic:
        return True
    if not isinstance(dic, dict):
        return True
    for val in dic.values():
        if val is None:
            return True
    return False
