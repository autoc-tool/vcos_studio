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
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.autosar_utils.utils import set_short_name, get_short_name

"""
FlatExtract.arxml API
"""
tag_to_class_dict = {
    "SYSTEM_SIGNAL_REF": autosar44.SYSTEM_SIGNAL_REFType4309,
    "CONTEXT_COMPONENT_REF": autosar44.CONTEXT_COMPONENT_REFType5423,
    "CONTEXT_COMPOSITION_REF": autosar44.CONTEXT_COMPOSITION_REFType5424,
    "CONTEXT_PORT_REF": autosar44.CONTEXT_PORT_REFType5425,
    "TARGET_DATA_PROTOTYPE_REF": autosar44.TARGET_DATA_PROTOTYPE_REFType5426,
    "SIGNAL_GROUP_REF": autosar44.SIGNAL_GROUP_REFType4300,
    "TYPE_MAPPING": autosar44.TYPE_MAPPINGType4301,
    "SENDER_REC_RECORD_TYPE_MAPPING": autosar44.SENDER_REC_RECORD_TYPE_MAPPING,
    "RECORD_ELEMENT_MAPPINGS": autosar44.RECORD_ELEMENT_MAPPINGSType4275,
    "SENDER_REC_RECORD_ELEMENT_MAPPING": autosar44.SENDER_REC_RECORD_ELEMENT_MAPPING,
    "IMPLEMENTATION_RECORD_ELEMENT_REF": autosar44.IMPLEMENTATION_RECORD_ELEMENT_REFType4272,
    # "SYSTEM_SIGNAL_REF": autosar44.SYSTEM_SIGNAL_REFType4273,
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


def append_tag_value(node, tag_name, value):
    attr_value = getattr(node, tag_name, "N/A")
    if attr_value is not None:
        tag_class = tag_to_class_dict.get(tag_name, None)
        if tag_class:
            tag_obj = tag_class()
            tag_obj.valueOf_ = value
            attr_value.append(tag_obj)
            return tag_obj
            # setattr(node, tag_name, tag_obj)
        else:
            print(f"Unsupported tag {tag_name}")
    elif attr_value == "N/A":
        print(f"InValid attribute {tag_name} of class {type(node)}")


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


def create_data_element_iref(parent, data_element_iref_dict):
    data_element_iref_obj = autosar44.VARIABLE_DATA_PROTOTYPE_IN_SYSTEM_INSTANCE_REF()
    parent.DATA_ELEMENT_IREF = data_element_iref_obj
    data_element_iref_obj.set_tag("DATA-ELEMENT-IREF")  # CONTEXT-COMPOSITION-REF
    data_element_iref_obj.set_parent(parent)
    if "context_component_ref" in data_element_iref_dict:
        ref_obj = append_tag_value(
            data_element_iref_obj, "CONTEXT_COMPONENT_REF", data_element_iref_dict["context_component_ref"]
        )
        ref_obj.set_DEST("SW-COMPONENT-PROTOTYPE")
    set_tag_value(data_element_iref_obj, "CONTEXT_PORT_REF", data_element_iref_dict["context_port_ref"])
    set_tag_dest(data_element_iref_obj, "CONTEXT_PORT_REF", data_element_iref_dict["port_type"])
    set_tag_value(data_element_iref_obj, "CONTEXT_COMPOSITION_REF", data_element_iref_dict["context_composition_ref"])
    set_tag_dest(data_element_iref_obj, "CONTEXT_COMPOSITION_REF", "ROOT-SW-COMPOSITION-PROTOTYPE")
    set_tag_value(
        data_element_iref_obj, "TARGET_DATA_PROTOTYPE_REF", data_element_iref_dict["target_data_prototype_ref"]
    )
    set_tag_dest(data_element_iref_obj, "TARGET_DATA_PROTOTYPE_REF", "VARIABLE-DATA-PROTOTYPE")


def create_sender_receiver_to_signal_mapping(data_mappings, pdu_to_frame_mapping_dict: dict):
    """
    signal_dict = {
        "data_element_iref": {
            "context_component_ref": "/COM/VCOS2/CFG/WORKFLOW/SYSDESC/SYNC/COMPOSITIONTYPE/CAN_Outputs",
            "context_composition_ref": "/COM/VCOS2/CFG/WORKFLOW/SYSDESC/SYNC/SYSTEM/COMPOSITIONTYPE",
            "context_port_ref": "/ComponentTypes/CAN_Outputs/PI_Porttest",
            "port_type": "R-PORT-PROTOTYPE",
            "target_data_prototype_ref": "/PortInterfaces/PI_Porttest/Element1",
        },
        "system_signal_ref": "/Signal/FrtFootLampDrvSts",
        "type_mapping": {},
    }
    """
    parent = data_mappings
    sender_receiver_to_signal_mapping_obj = autosar44.SENDER_RECEIVER_TO_SIGNAL_MAPPING()
    sender_receiver_to_signal_mapping_obj.set_tag("SENDER-RECEIVER-TO-SIGNAL-MAPPING")
    sender_receiver_to_signal_mapping_obj.set_parent(parent)
    if "system_signal_ref" in pdu_to_frame_mapping_dict:
        set_tag_value(
            sender_receiver_to_signal_mapping_obj, "SYSTEM_SIGNAL_REF", pdu_to_frame_mapping_dict["system_signal_ref"]
        )
        set_tag_dest(sender_receiver_to_signal_mapping_obj, "SYSTEM_SIGNAL_REF", "SYSTEM-SIGNAL")
    create_data_element_iref(sender_receiver_to_signal_mapping_obj, pdu_to_frame_mapping_dict["data_element_iref"])
    parent.SENDER_RECEIVER_TO_SIGNAL_MAPPING.append(sender_receiver_to_signal_mapping_obj)


def create_sender_receiver_to_signal_group_mapping(data_mappings, sr_signalgroup_mapping: dict):
    if len(sr_signalgroup_mapping["type_mapping"]) == 0:
        return
    parent = data_mappings
    sender_receiver_to_signal_group_mapping_obj = autosar44.SENDER_RECEIVER_TO_SIGNAL_GROUP_MAPPING()
    sender_receiver_to_signal_group_mapping_obj.set_tag("SENDER-RECEIVER-TO-SIGNAL-GROUP-MAPPING")
    sender_receiver_to_signal_group_mapping_obj.set_parent(parent)
    set_tag_value(
        sender_receiver_to_signal_group_mapping_obj, "SIGNAL_GROUP_REF", sr_signalgroup_mapping["signal_group_ref"]
    )
    set_tag_dest(sender_receiver_to_signal_group_mapping_obj, "SIGNAL_GROUP_REF", "SYSTEM-SIGNAL-GROUP")
    create_data_element_iref(sender_receiver_to_signal_group_mapping_obj, sr_signalgroup_mapping["data_element_iref"])

    type_mapping = tag_to_class_dict["TYPE_MAPPING"]()
    type_mapping.set_tag("TYPE-MAPPING")
    type_mapping.set_parent(sender_receiver_to_signal_group_mapping_obj)
    sender_receiver_to_signal_group_mapping_obj.TYPE_MAPPING = type_mapping

    sender_rec_record_type_mapping = tag_to_class_dict["SENDER_REC_RECORD_TYPE_MAPPING"]()
    sender_rec_record_type_mapping.set_tag("SENDER-REC-RECORD-TYPE-MAPPING")
    sender_rec_record_type_mapping.set_parent(type_mapping)
    type_mapping.SENDER_REC_RECORD_TYPE_MAPPING = sender_rec_record_type_mapping

    record_element_mappings = tag_to_class_dict["RECORD_ELEMENT_MAPPINGS"]()
    record_element_mappings.set_tag("RECORD-ELEMENT-MAPPINGS")
    record_element_mappings.set_parent(sender_rec_record_type_mapping)
    sender_rec_record_type_mapping.RECORD_ELEMENT_MAPPINGS = record_element_mappings

    for record_element_mapping in sr_signalgroup_mapping["type_mapping"]:
        sender_rec_record_element_mapping = tag_to_class_dict["SENDER_REC_RECORD_ELEMENT_MAPPING"]()
        sender_rec_record_element_mapping.set_tag("SENDER-REC-RECORD-ELEMENT-MAPPING")
        sender_rec_record_element_mapping.set_parent(record_element_mappings)
        set_tag_value(
            sender_rec_record_element_mapping,
            "IMPLEMENTATION_RECORD_ELEMENT_REF",
            record_element_mapping["implementation_record_element_ref"],
        )
        set_tag_dest(
            sender_rec_record_element_mapping, "IMPLEMENTATION_RECORD_ELEMENT_REF", "IMPLEMENTATION-DATA-TYPE-ELEMENT"
        )
        set_tag_value(
            sender_rec_record_element_mapping, "SYSTEM_SIGNAL_REF", record_element_mapping["system_signal_ref"]
        )
        set_tag_dest(sender_rec_record_element_mapping, "SYSTEM_SIGNAL_REF", "SYSTEM-SIGNAL")
        sender_rec_record_type_mapping.RECORD_ELEMENT_MAPPINGS.SENDER_REC_RECORD_ELEMENT_MAPPING.append(
            sender_rec_record_element_mapping
        )
    parent.SENDER_RECEIVER_TO_SIGNAL_GROUP_MAPPING.append(sender_receiver_to_signal_group_mapping_obj)
