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
import os

from basic_func_module.autosar_utils.autosar_communication import (
    get_all_system_signal_mapping_info,
    ISignalIPduGroup,
    CanFrame,
    LinFrame,
    ISignalIPdu,
    ISignal,
    SystemSignal,
)
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from func_module.health_monitor.logger import logger
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlParseHandler
from func_module.module_management.arxml_handler.system.system_extract_generator import SystemExtractGenerator
from func_module.module_management.base_config import BASE_CONFIG_PATH

BASE_ARXML_PATH = os.path.join(BASE_CONFIG_PATH, "base_arxml")

class CommunicationArxmlManager:
    """
    Transform DBC/LDF to communication arxml object
    """

    pdus = []

    def __init__(self):
        self.ar_packages = {}

    @classmethod
    def get_all_system_signal_mapping_info_cls(cls, autosar_communication):
        return get_all_system_signal_mapping_info(autosar_communication)

    def update_communication_arxml_from_dbc_ldf(self, dic, system_autosar_dict, is_add_channel_name):
        communication_autosar = ArxmlParseHandler.parse_communication_arxml(BASE_ARXML_PATH)
        dbc_config_dict = get_config_json_template_input_dbc_list(dic.get("dbc", []), is_add_channel_name)
        ldf_config_dict = get_config_json_template_input_ldf_list(dic.get("ldf", []), is_add_channel_name)
        self.repeated_signal_add_network_name(dbc_config_dict, ldf_config_dict, is_add_channel_name)
        self.repeated_signalgroup_add_network_name(dbc_config_dict, is_add_channel_name)
        system_extract_autosar = SystemExtractGenerator().generate(dbc_config_dict)
        system_extract_autosar = system_extract_autosar or system_autosar_dict["SystemExtract"]
        communication_autosar = self.update_communication_arxml_from_add_dbc(dbc_config_dict, communication_autosar)
        if communication_autosar is None:
            return system_autosar_dict["Communication"], system_extract_autosar

        communication_autosar = self.update_communication_arxml_from_add_ldf(ldf_config_dict, communication_autosar)
        if communication_autosar is None:
            return system_autosar_dict["Communication"], system_extract_autosar

        return communication_autosar, system_extract_autosar

    def repeated_signal_add_network_name(self, dbc_config_dict, ldf_config_dict, is_add_channel_name):

        def update_system_signal_dict(file_name, file_type, msg, message_index):
            signals = msg.get("signals", {})
            network_name = msg.get("bus_name", None)
            message_name = msg.get("message_name", None)
            direction = msg.get("direction", None)
            if direction not in system_signal_dict.keys():
                return
            if network_name is None or message_name is None:
                return
            for idx in range(len(signals)):
                system_signal = signals[idx].get("signal_alias_name", None)
                if system_signal is None:
                    continue
                if system_signal not in system_signal_dict[direction].keys():
                    system_signal_dict[direction][system_signal] = []
                system_signal_dict[direction][system_signal].append(
                    {
                        "message_name": message_name,
                        "message_index": message_index,
                        "file_type": file_type,
                        "file_name": file_name,
                        "network_name": network_name,
                        "signal_index": idx,
                    }
                )

        system_signal_dict = {"Tx": {}, "Rx": {}}
        dbc_info_list = dbc_config_dict.get("config", {})
        ldf_info_list = ldf_config_dict.get("config", {})
        for file_name, file_info in dbc_info_list.items():
            msg_list = file_info.get("details", [])
            for i in range(len(msg_list)):
                update_system_signal_dict(file_name, "dbc", msg_list[i], i)
        for file_name, file_info in ldf_info_list.items():
            msg_list = file_info.get("details", [])
            for i in range(len(msg_list)):
                update_system_signal_dict(file_name, "ldf", msg_list[i], i)

        for direction, repeated_signal_dict in system_signal_dict.items():
            for system_signal_name, repeated_signal_list in repeated_signal_dict.items():
                if len(repeated_signal_list) <= 1:
                    continue
                network_name_set = set()
                network_name_isig_set = set()
                for repeated_signal in repeated_signal_list:
                    file_type = repeated_signal.get("file_type", "")
                    file_name = repeated_signal.get("file_name", "")
                    network_name = repeated_signal.get("network_name", "")
                    message_name = repeated_signal.get("message_name", "")
                    message_index = repeated_signal.get("message_index", 0)
                    signal_index = repeated_signal.get("signal_index", 0)

                    if is_add_channel_name:
                        postfix = 0
                        while postfix in network_name_set:
                            postfix += 1
                            logger.info(f"Processing repeat signal on same network: {network_name}_{postfix}")
                        network_name_set.add(postfix)
                    else:
                        num = 0
                        postfix = network_name
                        while postfix in network_name_set:
                            num += 1
                            postfix = f"{network_name}_{str(num)}"
                            logger.info(f"Processing repeat signal on same network: {postfix}")
                        network_name_set.add(postfix)

                    if file_type == "dbc":
                        message_wait_process = dbc_info_list.get(file_name, {}).get("details", [])[message_index]
                    elif file_type == "ldf":
                        message_wait_process = ldf_info_list.get(file_name, {}).get("details", [])[message_index]
                    else:
                        continue
                    if message_wait_process.get("message_name", None) != message_name:
                        continue
                    signals_wait_process = message_wait_process.get("signals", [])
                    signal_groups = message_wait_process.get("signal_groups", [])
                    signal_repeated = signals_wait_process[signal_index]
                    if signal_repeated is None:
                        continue
                    name_old = signal_repeated["signal_alias_name"]
                    signal_repeated["signal_alias_name"] += f"_vcos_{postfix}"
                    for signal_group in signal_groups:
                        if name_old in signal_group["group_signals_name"]:
                            index = signal_group["group_signals_name"].index(name_old)
                            signal_group["group_signals_name"][index] = signal_repeated["signal_alias_name"]
                            break

    def repeated_signalgroup_add_network_name(self, dbc_config_dict, is_add_channel_name):
        def update_system_signal_dict(file_name, file_type, msg, message_index):
            signal_groups = msg.get("signal_groups", [])
            network_name = msg.get("bus_name", None)
            message_name = msg.get("message_name", None)
            direction = msg.get("direction", None)
            if direction not in system_signalgroup_dict.keys():
                return
            if network_name is None or message_name is None:
                return
            for idx in range(len(signal_groups)):
                system_signal = signal_groups[idx].get("group_name", None)
                if system_signal is None:
                    continue
                if system_signal not in system_signalgroup_dict[direction].keys():
                    system_signalgroup_dict[direction][system_signal] = []
                system_signalgroup_dict[direction][system_signal].append(
                    {
                        "message_name": message_name,
                        "message_index": message_index,
                        "file_name": file_name,
                        "network_name": network_name,
                        "signal_index": idx,
                    }
                )

        system_signalgroup_dict = {"Tx": {}, "Rx": {}}
        dbc_info_list = dbc_config_dict.get("config", {})
        for file_name, file_info in dbc_info_list.items():
            msg_list = file_info.get("details", [])
            for i in range(len(msg_list)):
                update_system_signal_dict(file_name, "dbc", msg_list[i], i)
        for direction, repeated_signal_dict in system_signalgroup_dict.items():
            for system_signal_name, repeated_signal_list in repeated_signal_dict.items():
                if len(repeated_signal_list) <= 1:
                    continue
                network_name_set = set()
                for repeated_signal in repeated_signal_list:
                    file_name = repeated_signal.get("file_name", "")
                    network_name = repeated_signal.get("network_name", "")
                    message_name = repeated_signal.get("message_name", "")
                    message_index = repeated_signal.get("message_index", 0)
                    signal_index = repeated_signal.get("signal_index", 0)

                    if is_add_channel_name:
                        postfix = 0
                        while postfix in network_name_set:
                            postfix += 1
                            logger.info(f"Processing repeat signal on same network: {network_name}_{postfix}")
                        network_name_set.add(postfix)
                    else:
                        num = 0
                        postfix = network_name
                        while postfix in network_name_set:
                            num += 1
                            postfix = f"{network_name}_{str(num)}"
                            logger.info(f"Processing repeat signal on same network: {postfix}")
                        network_name_set.add(postfix)

                    message_wait_process = dbc_info_list.get(file_name, {}).get("details", [])[message_index]
                    if message_wait_process.get("message_name", None) != message_name:
                        continue
                    signal_groups = message_wait_process.get("signal_groups", [])
                    signal_repeated = signal_groups[signal_index]
                    if signal_repeated is None:
                        continue
                    signal_repeated["group_name"] += f"_vcos_{postfix}"

    def update_communication_info_from_dbc(self, dic):
        if "dbc" not in dic:
            return
        self.update_communication_arxml_from_add_dbc(dic["dbc"])

    def updata_communication_info_from_add_ldf(self, dic):
        if "ldf" not in dic:
            return
        self.update_communication_arxml_from_add_ldf(dic["ldf"])

    def check_communication_element_objects(self, communication_autosar):
        if communication_autosar is None:
            logger.error("Communication object is none")
            return False
        self.ar_packages["i_pdu_group_elements"] = communication_autosar.find("/IPDUGroup").ELEMENTS
        self.ar_packages["can_frame_elements"] = communication_autosar.find("/CanFrame").ELEMENTS
        self.ar_packages["lin_frame_elements"] = communication_autosar.find("/LinFrame").ELEMENTS
        self.ar_packages["pdu_elements"] = communication_autosar.find("/PDU").ELEMENTS
        self.ar_packages["i_signal_elements"] = communication_autosar.find("/ISignal").ELEMENTS
        self.ar_packages["system_signal_elements"] = communication_autosar.find("/Signal").ELEMENTS
        if _dict_has_empty_val(self.ar_packages):
            logger.error("Communication AR-PACKET Missing")
            return False
        return True

    def update_communication_arxml_from_add_dbc(self, dbc_config_dict, communication_autosar):
        rv = self.check_communication_element_objects(communication_autosar)
        if rv is not True:
            return
        self.parser_and_update_arxml(dbc_config_dict, "DBC", communication_autosar)
        communication_autosar = AutosarUtil.update_autosar(communication_autosar)
        return communication_autosar

    def update_communication_arxml_from_add_ldf(self, ldf_config_dict, communication_autosar):
        rv = self.check_communication_element_objects(communication_autosar)
        if rv is not True:
            return
        self.parser_and_update_arxml(ldf_config_dict, "LDF", communication_autosar)
        communication_autosar = AutosarUtil.update_autosar(communication_autosar)
        return communication_autosar

    def parser_and_update_arxml(self, com_config_json_dict, dbc_or_ldf, communication_autosar):
        com_json_config = com_config_json_dict["config"]
        # ipdu_group_refs = com_config_json_dict["ipdu_group_refs"]
        for comm_diag_name, value in com_json_config.items():
            if "networks_name" not in value:
                continue
            if communication_autosar.find("/IPDUGroup/" + value["networks_name"] + "_Tx"):
                continue
            i_pdu_group_tx = ISignalIPduGroup.create_full_i_signal_i_pdu_group(
                self.ar_packages["i_pdu_group_elements"], value["networks_name"] + "_Tx", "OUT"
            )
            i_pdu_group_rx = ISignalIPduGroup.create_full_i_signal_i_pdu_group(
                self.ar_packages["i_pdu_group_elements"], value["networks_name"] + "_Rx", "IN"
            )
            for message in value["details"]:
                i_signal_i_pdu = CommunicationArxmlManager.parser_message_to_i_signal_i_pdu(message)
                i_signal = CommunicationArxmlManager.parser_message_to_i_signal(message)
                system_signal = CommunicationArxmlManager.parser_message_to_system_signal(message)
                can_lin_frame = CommunicationArxmlManager.paser_message_to_can_lin_frame(message)
                if dbc_or_ldf == "DBC":
                    CanFrame.create_can_frame(self.ar_packages["can_frame_elements"], can_lin_frame)
                elif dbc_or_ldf == "LDF":
                    LinFrame.create_lin_frame(self.ar_packages["lin_frame_elements"], can_lin_frame)
                else:
                    continue
                if message["pdu_type"] == "com":
                    ISignalIPdu.create_full_i_signal_i_pdu(self.ar_packages["pdu_elements"], i_signal_i_pdu)
                elif message["pdu_type"] == "cannm":
                    ISignalIPdu.create_full_nm_pdu(self.ar_packages["pdu_elements"], i_signal_i_pdu)
                else:
                    continue
                if message["direction"] == "Tx":
                    ISignalIPduGroup.create_full_i_signal_i_pdu_ref_conditional(
                        i_pdu_group_tx.I_SIGNAL_I_PDUS, "/PDU/" + i_signal_i_pdu["short_name"]
                    )
                elif message["direction"] == "Rx":
                    ISignalIPduGroup.create_full_i_signal_i_pdu_ref_conditional(
                        i_pdu_group_rx.I_SIGNAL_I_PDUS, "/PDU/" + i_signal_i_pdu["short_name"]
                    )
                else:
                    continue
                # self._process_repeated_system_signal(self.system_autosar_dict["Communication"], i_signal,
                #                                      system_signal)
                ISignal.create_full_i_signals_and_i_signal_groups(self.ar_packages["i_signal_elements"], i_signal)
                SystemSignal.create_full_system_signals_and_signal_groups(
                    self.ar_packages["system_signal_elements"], system_signal
                )

    @classmethod
    def parser_message_to_i_signal_i_pdu(cls, message):
        i_signal_i_pdu = {}
        i_signal_i_pdu["short_name"] = message["message_name"]
        i_signal_i_pdu["length"] = message["message_size"]
        i_signal_i_pdu["i_pdu_timing"] = {}
        i_signal_i_pdu["i_pdu_timing"] = cls._parser_message_to_i_pdu_timing(message)
        i_signal_i_pdu["i_signal_to_i_pdu_mappings"] = cls._parser_message_to_i_signal_to_i_pdu_mappings(message)
        i_signal_i_pdu["unused_bit_pattern"] = 0
        cls.pdus.append(i_signal_i_pdu)
        return i_signal_i_pdu

    @classmethod
    def _parser_message_to_i_pdu_timing(cls, message):
        i_pdu_timing = {}
        i_pdu_timing["minimum_delay"] = message.get("gen_msg_delay_time", 0)
        i_pdu_timing["transmission_mode_false_timing"] = {}
        i_pdu_timing["transmission_mode_false_timing"]["time_offset"] = message.get("gen_msg_start_delay_time", 0)
        i_pdu_timing["transmission_mode_false_timing"]["time_period"] = message.get("gen_msg_cycle_time", 0)
        i_pdu_timing["transmission_mode_false_timing"]["number_of_repetitions"] = message.get(
            "gen_msg_nr_of_repetition", 0
        )
        i_pdu_timing["transmission_mode_false_timing"]["repetition_period"] = message.get("gen_msg_cycle_time_fast", 0)
        i_pdu_timing["transmission_mode_true_timing"] = i_pdu_timing["transmission_mode_false_timing"].copy()
        return i_pdu_timing

    @classmethod
    def _parser_message_to_i_signal_to_i_pdu_mappings(cls, message):
        i_signal_to_i_pdu_mappings = {"i_signals": [], "i_signal_groups": []}
        for signal in message["signals"]:
            if "pdu_type" in message and message["pdu_type"] == "cannm" and signal["bit_position"] < 16:
                continue
            mapping = {}
            mapping["short_name"] = signal["signal_alias_name"]
            mapping["i_signal_ref"] = "/ISignal/" + signal["signal_name"]
            mapping["packing_byte_order"] = (
                "LEAST-SIGNIFICANT-BYTE-FIRST"
                if signal["byte_order"] == "LITTLE_ENDIAN"
                else "MOST-SIGNIFICANT-BYTE-FIRST"
            )
            mapping["start_position"] = signal["bit_position"]
            mapping["transfer_property"] = signal["gen_sig_send_type"]
            i_signal_to_i_pdu_mappings["i_signals"].append(mapping)
        for signal_group in message["signal_groups"]:
            mapping = {}
            mapping["short_name"] = signal_group["group_name"]
            mapping["i_signal_group_ref"] = (
                "/ISignal/" + signal_group["group_name_in_dbc"] + "_o" + message["message_name"]
            )  # noqa:E501
            if len(signal_group["group_signals_name"]):
                signal_alias_name = signal_group["group_signals_name"][0]
                for signal in message["signals"]:
                    if signal["signal_alias_name"] == signal_alias_name:
                        mapping["transfer_property"] = signal["gen_sig_send_type"]
                        break
            if "transfer_property" not in mapping:
                mapping["transfer_property"] = "PENDING"
            i_signal_to_i_pdu_mappings["i_signal_groups"].append(mapping)
        return i_signal_to_i_pdu_mappings

    @classmethod
    def parser_message_to_i_signal(cls, message):
        i_signal_elements = {"i_signals": [], "i_signal_groups": []}
        for signal in message["signals"]:
            i_signal = cls.parser_signal_to_i_signal(message, signal)
            i_signal_elements["i_signals"].append(i_signal)
        for signal_group in message["signal_groups"]:
            i_signal_group = cls.parser_signal_group_to_i_signal(message, signal_group)
            i_signal_elements["i_signal_groups"].append(i_signal_group)
        return i_signal_elements

    @classmethod
    def parser_signal_to_i_signal(cls, message, signal):
        i_signal = {}
        i_signal["short_name"] = signal["signal_name"]
        i_signal["data_type_policy"] = "LEGACY"
        i_signal["i_signal_type"] = "PRIMITIVE"
        i_signal["init_value"] = signal["init_value"]
        i_signal["length"] = signal["signal_size"]
        i_signal["base_type_ref"] = "/DataType/" + signal["signal_type"].lower()
        i_signal["system_signal_ref"] = "/Signal/" + signal["signal_alias_name"]
        return i_signal

    @classmethod
    def parser_signal_group_to_i_signal(cls, message, signal_group):
        i_signal_group = {}
        i_signal_group["i_signal_refs"] = []
        i_signal_group["i_signal_ref_dest"] = "I-SIGNAL"
        i_signal_group["short_name"] = signal_group["group_name_in_dbc"] + "_o" + message["message_name"]
        i_signal_group["system_signal_group_ref"] = "/Signal/" + signal_group["group_name"]
        i_signal_group["system_signal_group_ref_dest"] = "SYSTEM-SIGNAL-GROUP"
        for signal_name in signal_group["group_i_sig_name"]:
            i_signal_group["i_signal_refs"].append("/ISignal/" + signal_name + "_o" + message["message_name"])
        return i_signal_group

    @classmethod
    def parser_message_to_system_signal(cls, message):
        system_signal_elements = {"system_signals": [], "system_signal_groups": []}
        for signal in message["signals"]:
            system_signal = cls.parser_signal_to_system_signal(message, signal)
            system_signal_elements["system_signals"].append(system_signal)
        for signal_group in message["signal_groups"]:
            system_signal_group = cls.parser_signal_group_to_system_signal(message, signal_group)
            system_signal_elements["system_signal_groups"].append(system_signal_group)
        return system_signal_elements

    @classmethod
    def parser_signal_to_system_signal(cls, message, signal):
        system_signal = {}
        system_signal["short_name"] = signal["signal_alias_name"]
        system_signal["dynamic_length"] = "false"
        system_signal["compu_method_ref"] = "/DataType/Semantics/CM_" + system_signal["short_name"]
        system_signal["data_constr_ref"] = "/DataType/Constraint/DC_" + system_signal["short_name"]
        return system_signal

    @classmethod
    def parser_signal_group_to_system_signal(cls, message, signal_group):
        system_signal_group = {}
        system_signal_group["short_name"] = signal_group["group_name"]
        system_signal_group["system_signal_refs"] = []
        system_signal_group["system_signal_ref_dest"] = "SYSTEM-SIGNAL"
        for signal_name in signal_group["group_signals_name"]:
            system_signal_group["system_signal_refs"].append("/Signal/" + signal_name)
        return system_signal_group

    @classmethod
    def paser_message_to_can_lin_frame(cls, message):
        can_lin_frame = {}
        can_lin_frame["short_name"] = message["message_name"]
        can_lin_frame["frame_length"] = message["message_size"]
        can_lin_frame["pdu_to_frame_mapping"] = {}
        can_lin_frame["pdu_to_frame_mapping"]["short_name"] = message["message_alias_name"]
        can_lin_frame["pdu_to_frame_mapping"]["packing_byte_order"] = "MOST-SIGNIFICANT-BYTE-LAST"
        can_lin_frame["pdu_to_frame_mapping"]["pdu_ref"] = "/PDU/" + message["message_name"]
        can_lin_frame["pdu_to_frame_mapping"]["start_position"] = 0
        return can_lin_frame

    def clear(cls):
        cls.pdus = []

    @classmethod
    def _process_repeated_system_signal(cls, autosar_communication, i_signals, system_signals):
        for system_signal in system_signals["system_signals"]:
            i = 0
            system_signal_original = system_signal["short_name"]
            while autosar_communication.find("/Signal/" + system_signal["short_name"]):
                i += 1
                system_signal["short_name"] += f"_{i}"
            if i:
                for i_signal in i_signals["i_signals"]:
                    if i_signal["system_signal_ref"].split("/")[-1] == system_signal_original:
                        i_signal["system_signal_ref"] += f"_{i}"
                        break


def get_gen_msg_send_type(gen_msg_send_type_value, msg_dict):
    """
    Get message send type.

    Arg:
        gen_msg_send_type_value: value from dbc file;
        msg_dict: dictionary that stores message.
    """

    if 0 == gen_msg_send_type_value or 2 == gen_msg_send_type_value:
        msg_dict["gen_msg_send_type"] = "PERIODIC"
    elif 1 == gen_msg_send_type_value or 3 == gen_msg_send_type_value or 6 == gen_msg_send_type_value:
        msg_dict["gen_msg_send_type"] = "DIRECT"
    elif 4 == gen_msg_send_type_value or 5 == gen_msg_send_type_value:
        msg_dict["gen_msg_send_type"] = "MIXED"
    elif 7 == gen_msg_send_type_value or 8 == gen_msg_send_type_value:
        msg_dict["gen_msg_send_type"] = "NONE"


def get_gen_sig_send_type(gen_sig_send_type_value, signal_dict):
    """
    Get singal send type.

    Arg:
        gen_sig_send_type_value: value from dbc file;
        signal_dict: dictionary that stores signal.
    """

    if 0 == gen_sig_send_type_value or 7 == gen_sig_send_type_value:
        signal_dict["gen_sig_send_type"] = "PENDING"
    elif 1 == gen_sig_send_type_value or 5 == gen_sig_send_type_value:
        signal_dict["gen_sig_send_type"] = "TRIGGERED_WITHOUT_REPETITION"
    elif 2 == gen_sig_send_type_value or 6 == gen_sig_send_type_value:
        signal_dict["gen_sig_send_type"] = "TRIGGERED"
    elif 3 == gen_sig_send_type_value:
        signal_dict["gen_sig_send_type"] = "TRIGGERED_ON_CHANGE_WITHOUT_REPETITION"
    elif 4 == gen_sig_send_type_value:
        signal_dict["gen_sig_send_type"] = "TRIGGERED_ON_CHANGE"


def get_dbc_signals(signal_dict, signal_value, is_add_channel_name, network_name):
    """
    Get all signals from the dbc file.

    Arg:
        signal_dict: dictionary that stores signal;
        signal_value: The single signal obtained.
    """

    signal_dict["signal_name"] = signal_value.signal_name
    signal_dict["i_sig_alias_name"] = signal_value.signal_alias_name
    signal_dict["signal_alias_name"] = (
        f"{signal_value.signal_alias_name}_{network_name}" if is_add_channel_name else signal_value.signal_alias_name
    )
    signal_dict["bit_position"] = signal_value.start
    signal_dict["signal_size"] = signal_value.length
    signal_dict["scale"] = signal_value.scale
    signal_dict["offset"] = signal_value.offset
    signal_dict["maximum"] = signal_value.maximum
    signal_dict["minimum"] = signal_value.minimum
    signal_dict["choices"] = signal_value.choices
    signal_dict["ComSignalLength"] = signal_dict["signal_size"] // 8 + int(bool(signal_dict["signal_size"] % 8))
    gen_sig_send_type_value = signal_value.signal_attributes["GenSigSendType"].value
    get_gen_sig_send_type(gen_sig_send_type_value, signal_dict)
    if "big_endian" == signal_value.byte_order:
        signal_dict["byte_order"] = "BIG_ENDIAN"
    elif "litter_endian" == signal_value.byte_order:
        signal_dict["byte_order"] = "LITTLE_ENDIAN"
    else:
        signal_dict["byte_order"] = "OPAQUE"
    signal_dict["init_value"] = 0
    get_signal_type(signal_dict, signal_value)


def get_signal_type(signal_dict, signal_value):
    """
    Get all signals from the dbc file.

    Arg:
        signal_dict: dictionary that stores signal;
        signal_value: The single signal obtained.
    """

    if signal_value.is_float is True:
        if signal_value.length <= 32:
            signal_dict["signal_type"] = "FLOAT32"
        else:
            signal_dict["signal_type"] = "FLOAT64"
    elif signal_value.is_signed is False and signal_value.is_float is False:
        get_unsigned_type(signal_dict, signal_value)
    elif signal_value.is_signed is True and signal_value.is_float is False:
        get_signed_type(signal_dict, signal_value)


def get_unsigned_type(signal_dict, signal_value):
    """
    Get an unsigned type.

    Arg:
        signal_dict: dictionary that stores signal;
        signal_value: The single signal obtained.
    """

    if signal_value.length <= 8:
        signal_dict["signal_type"] = "UINT8"
    elif signal_value.length <= 16:
        signal_dict["signal_type"] = "UINT16"
    elif signal_value.length <= 32:
        signal_dict["signal_type"] = "UINT32"
    elif signal_value.length <= 64:
        signal_dict["signal_type"] = "UINT64"
    else:
        signal_dict["signal_type"] = "UINT8_N"
        signal_dict["signal_size"] = 0


def get_signed_type(signal_dict, signal_value):
    """
    Get an signed type.

    Arg:
        signal_dict: dictionary that stores signal;
        signal_value: The single signal obtained.
    """

    if signal_value.length <= 8:
        signal_dict["signal_type"] = "SINT8"
    elif signal_value.length <= 16:
        signal_dict["signal_type"] = "SINT16"
    elif signal_value.length <= 32:
        signal_dict["signal_type"] = "SINT32"
    elif signal_value.length <= 64:
        signal_dict["signal_type"] = "SINT64"
    else:
        signal_dict["signal_type"] = "UINT8_N"
        signal_dict["signal_size"] = 0


def get_config_json_template_input_dbc_list(dbc_list: list, is_add_channel_name) -> dict:
    """
    Get input parameter for template Com_Cfg.json.

    Arg:
        config_list : All config list

    Return:
        Returns a dictionary of template input parameter
    """
    com_config_json_dict = {}
    com_config_json_dict["config"] = {}
    ipdu_group_refs = []
    for dbc in dbc_list:
        config_json_dict = []
        for msg_key, msg_value in dbc["details"].items():
            msg_dict = {}
            msg_dict["comm_diag_type"] = "dbc"
            msg_dict["message_name"] = msg_value.message_name
            msg_dict["message_alias_name"] = msg_value.message_alias_name
            msg_dict["protocol"] = msg_value.protocol if msg_value.protocol else ""
            msg_dict["bus_name"] = msg_value.bus_name
            networks_name = _get_dict_value_by_nested_keys(dbc, ["attributes", "network", "define_value", "DBName"])
            if networks_name is None:
                continue
            if (
                msg_value.bus_name not in ipdu_group_refs
                and "GenMsgILSupport" in msg_value.message_attributes
                and msg_value.message_attributes["GenMsgILSupport"].value == 1
            ):
                ipdu_group_refs.append(msg_value.bus_name)
            msg_dict["message_size"] = msg_value.length
            msg_dict["has_signal_groups"] = msg_value.has_signal_groups
            if "GenMsgSendType" in msg_value.message_attributes:
                gen_msg_send_type_value = msg_value.message_attributes["GenMsgSendType"].value
            else:
                gen_msg_send_type_value = 0
            if "GenMsgCycleTime" in msg_value.message_attributes:
                msg_dict["gen_msg_cycle_time"] = msg_value.message_attributes["GenMsgCycleTime"].value / 1000  # ms->s
            else:
                msg_dict["gen_msg_cycle_time"] = 0

            if "GenMsgStartDelayTime" in msg_value.message_attributes:
                msg_dict["gen_msg_start_delay_time"] = (
                    msg_value.message_attributes["GenMsgStartDelayTime"].value / 1000
                )  # ms->s
            else:
                msg_dict["gen_msg_start_delay_time"] = 0

            if "GenMsgNrOfRepetition" in msg_value.message_attributes:
                msg_dict["gen_msg_nr_of_repetition"] = msg_value.message_attributes["GenMsgNrOfRepetition"].value
            else:
                msg_dict["gen_msg_nr_of_repetition"] = 0

            if "GenMsgCycleTimeFast" in msg_value.message_attributes:
                msg_dict["gen_msg_cycle_time_fast"] = (
                    msg_value.message_attributes["GenMsgCycleTimeFast"].value / 1000
                )  # ms->s
            else:
                msg_dict["gen_msg_cycle_time_fast"] = 0

            if "GenMsgDelayTime" in msg_value.message_attributes:
                msg_dict["gen_msg_delay_time"] = msg_value.message_attributes["GenMsgDelayTime"].value / 1000  # ms->s
            else:
                msg_dict["gen_msg_delay_time"] = 0

            get_gen_msg_send_type(gen_msg_send_type_value, msg_dict)

            msg_dict["senders"] = msg_value.senders[0]
            if dbc["node_selected"] == msg_dict["senders"]:
                direction = "Tx"
            else:
                direction = "Rx"
            msg_dict["direction"] = direction
            signal_groups = []
            for signal_groups_key, signal_groups_value in msg_value.signal_groups.items():
                signal_group_dict = {}
                signal_group_dict["direction"] = direction
                signal_group_dict["group_name"] = (
                    f"{signal_groups_value.signal_group_name}_{networks_name}"
                    if is_add_channel_name
                    else signal_groups_value.signal_group_name
                )
                signal_group_dict["group_name_in_dbc"] = signal_groups_value.signal_group_name
                signal_group_dict["repetitions"] = signal_groups_value.repetitions
                signal_group_dict["group_signals_name"] = (
                    [f"{sig}_{networks_name}" for sig in signal_groups_value.group_signals_name]
                    if is_add_channel_name
                    else signal_groups_value.group_signals_name
                )
                signal_group_dict["group_i_sig_name"] = signal_groups_value.group_signals_name
                signal_groups.append(signal_group_dict)
            msg_dict["signal_groups"] = signal_groups
            signals = []
            for signal_key, signal_value in msg_value.signals.items():
                signal_dict = {}
                signal_dict["direction"] = direction
                get_dbc_signals(signal_dict, signal_value, is_add_channel_name, networks_name)
                signals.append(signal_dict)
            msg_dict["signals"] = signals
            if (
                (
                    "DiagRequest" in msg_value.message_attributes
                    and msg_value.message_attributes["DiagRequest"].value == 1
                )
                or (
                    "DiagResponse" in msg_value.message_attributes
                    and msg_value.message_attributes["DiagResponse"].value == 1
                )
                or (
                    "DiagState" in msg_value.message_attributes and msg_value.message_attributes["DiagState"].value == 1
                )
                or (
                    "GenMsgILSupport" in msg_value.message_attributes
                    and msg_value.message_attributes["GenMsgILSupport"].value == 0
                )
                or (
                    "NmAsrMessage" in msg_value.message_attributes
                    and msg_value.message_attributes["NmAsrMessage"].value == 1
                    and dbc["node_selected"] != msg_dict["senders"]
                )
            ):
                continue
            if (
                "NmAsrMessage" in msg_value.message_attributes
                and msg_value.message_attributes["NmAsrMessage"].value == 1
            ):
                msg_dict["pdu_type"] = "cannm"
            elif (
                "GenMsgILSupport" in msg_value.message_attributes
                and msg_value.message_attributes["GenMsgILSupport"].value == 1
            ):
                msg_dict["pdu_type"] = "com"
            else:
                continue
            config_json_dict.append(msg_dict)
        com_config_json_dict["config"][dbc["dbc_name"]] = {}
        com_config_json_dict["config"][dbc["dbc_name"]]["details"] = config_json_dict
        com_config_json_dict["config"][dbc["dbc_name"]]["node_selected"] = dbc["node_selected"]
        com_config_json_dict["config"][dbc["dbc_name"]]["networks_name"] = networks_name
    com_config_json_dict["ipdu_group_refs"] = ipdu_group_refs

    return com_config_json_dict


def get_config_json_template_input_ldf_list(ldf_list: list, is_add_channel_name) -> dict:
    """
    Get input parameter for template Com_Cfg.json.

    Arg:
        ldf_list : All config dictionary

    Return:
        Returns a dictionary of template input parameter
    """
    com_config_json_dict = {}
    com_config_json_dict["config"] = {}
    ipdu_group_refs = []
    for ldf in ldf_list:
        config_json_dict = []
        network_name = "LIN"
        for msg_key, msg_value in ldf["details"].items():
            msg_dict = {}
            msg_dict["bus_name"] = msg_value.bus_name
            ipdu_group_name = msg_value.bus_name
            if ipdu_group_name not in ipdu_group_refs:
                ipdu_group_refs.append(ipdu_group_name)
            if ipdu_group_name:
                network_name = ipdu_group_name

            msg_dict["comm_diag_type"] = "ldf"
            msg_dict["message_name"] = msg_value.message_name
            msg_dict["message_alias_name"] = msg_value.message_alias_name
            msg_dict["senders"] = msg_value.node_name
            msg_dict["has_signal_groups"] = 0
            msg_dict["signal_groups"] = []
            msg_dict["gen_msg_send_type"] = "NONE"
            msg_dict["message_size"] = msg_value.length
            msg_dict["gen_msg_cycle_time"] = 0
            msg_dict["gen_msg_cycle_time_fast"] = 0
            msg_dict["gen_msg_start_delay_time"] = 0
            msg_dict["gen_msg_nr_of_repetition"] = 0
            msg_dict["gen_msg_delay_time"] = 0
            busname = msg_dict["bus_name"]
            if msg_dict["message_name"].split(f"_o{busname}")[0] in ["MasterReq", "SlaveResp"]:
                continue
            signals = []
            if ldf["node_selected"] == msg_dict["senders"]:
                direction = "Tx"
            else:
                direction = "Rx"
            msg_dict["direction"] = direction
            for signal_key, signal_value in msg_value.signals.items():
                signal_dict = {}
                signal_dict["signal_name"] = signal_value.signal_name
                signal_dict["i_sig_alias_name"] = signal_value.signal_alias_name
                signal_dict["signal_alias_name"] = (
                    f"{signal_value.signal_alias_name}_{network_name}"
                    if is_add_channel_name
                    else signal_value.signal_alias_name
                )
                signal_dict["bit_position"] = signal_value.start
                signal_dict["signal_size"] = signal_value.length
                signal_dict["ComSignalLength"] = signal_dict["signal_size"] // 8 + int(
                    bool(signal_dict["signal_size"] % 8)
                )
                get_unsigned_type(signal_dict, signal_value)
                signal_dict["init_value"] = signal_value.initial
                signal_dict["direction"] = direction
                signal_dict["byte_order"] = "LITTLE_ENDIAN"
                signal_dict["gen_sig_send_type"] = "PENDING"
                signals.append(signal_dict)
            msg_dict["signals"] = signals
            msg_dict["pdu_type"] = "com"
            config_json_dict.append(msg_dict)
        com_config_json_dict["config"][ldf["ldf_name"]] = {}
        com_config_json_dict["config"][ldf["ldf_name"]]["details"] = config_json_dict
        com_config_json_dict["config"][ldf["ldf_name"]]["networks_name"] = network_name
        com_config_json_dict["config"][ldf["ldf_name"]]["node_selected"] = ldf["node_selected"]
    com_config_json_dict["ipdu_group_refs"] = ipdu_group_refs
    # com_config_json_dict["node_selected"] = config_dict["dbc"][0]["node_selected"]

    return com_config_json_dict


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


def _get_dict_value_by_nested_keys(target_dict, nested_key_list):
    rv = None
    find_value = target_dict
    if nested_key_list is None or len(nested_key_list) == 0:
        return rv
    for key in nested_key_list:
        if isinstance(find_value, dict) and key in find_value.keys():
            find_value = find_value[key]
        else:
            break
    else:
        rv = find_value
    return rv
