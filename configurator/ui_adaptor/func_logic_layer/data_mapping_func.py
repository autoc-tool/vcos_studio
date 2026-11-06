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
from enum import Enum
from copy import deepcopy

from ui_adaptor.data_management import get_autosar_asw_class, get_autosar_system_class, get_autosar_bsw_class
from func_module.mapping.data_mapping import DataMapping, Compatibility
from func_module.health_monitor.logger import logger
from func_module.health_monitor.perf_record import log_function_stats

CUR_FILE_PATH = os.path.dirname(os.path.realpath(__file__))

_DATA_MAPPING_EDITOR = 0
_DATA_MAPPING_ASSISTANT = 1

_PORT_NAME = "port_name"
_COMPONENT_NAME = "component_name"
_IS_MAPPING = "mapping"
_DATA_ELEMENT_NAME = "data_element_name"
_SYSTEM_SIGNAL_NAME = "system_signal_name"
_DIRECTION = "direction"
_CHANNEL_NAME = "channel_name"
_CLUSTER_NAME = "cluster_name"
_PDU_NAME = "pdu_name"
_FRAME_NAME = "frame_name"
_COM_LDCOM = "com_ldcom"
_COMPATIBILITY = "compatibility"
_CHECKBOX_STATUS = "checkbox_sts"

DATA_MAPPING_UI_DEFAULT_VALUE = {
    "system_signal_to_be_mapped": "<Select signal...>",
    "channel": "CHNL",
    "com_ldcom": "Com",
}

NOT_SELECT_SIGNAL = ["", DATA_MAPPING_UI_DEFAULT_VALUE["system_signal_to_be_mapped"]]


class DMEditor_MainUI_Idx(Enum):  # Data Mapping Editor主界面标题栏索引
    port_prototype = (0, _PORT_NAME, "Port Prototype")
    component_prototype = (1, _COMPONENT_NAME, "Component Prototype")
    mapping = (2, _IS_MAPPING, "Mapping")
    communication_element = (3, _DATA_ELEMENT_NAME, "Communication Element")
    system_signal = (4, _SYSTEM_SIGNAL_NAME, "System Signal")
    direction = (5, _DIRECTION, "Direction")
    channel = (6, _CHANNEL_NAME, "Channel")
    cluster = (7, _CLUSTER_NAME, "Cluster")
    pdu = (8, _PDU_NAME, "Pdu")
    frame = (9, _FRAME_NAME, "Frame")
    com_ldcom = (10, _COM_LDCOM, "Com/Ldcom")

    @classmethod
    def get_header_list(cls):
        return [
            "Port Prototype",
            "Component Prototype",
            "Mapping",
            "Communication Element",
            "System Signal",
            "Direction",
            "Channel",
            "Cluster",
            "PDU",
            "Frame",
            "Com/LdCom",
        ]


class DMEditor_MapUI_Idx(Enum):  # Data Mapping Editor手动连接弹窗界面标题栏索引
    communication_element = (0, _DATA_ELEMENT_NAME, "Communication Element")
    component = (1, _COMPONENT_NAME, "Component Prototype")
    port_prototype = (2, _PORT_NAME, "Port Prototype")
    direction = (3, _DIRECTION, "Direction")
    compatibility = (4, _COMPATIBILITY, "Compatibility")
    system_signal_to_be_mapped = (5, _SYSTEM_SIGNAL_NAME, "System Signal To Be Mapped")
    channel = (6, _CHANNEL_NAME, "Channel")
    cluster = (7, _CLUSTER_NAME, "Cluster")
    pdu = (8, _PDU_NAME, "Pdu")
    frame = (9, _FRAME_NAME, "Frame")
    com_ldcom = (10, _COM_LDCOM, "Com/Ldcom")


class DMEditor_SignalUI_Idx(Enum):  # Data Mapping Editor手动连接Signal选择界面标题栏索引
    checkbox = (0, _CHECKBOX_STATUS, "checkbox")
    system_signal_name = (1, _SYSTEM_SIGNAL_NAME, "Name")
    serialized = (2, "serialized", "Serialized")
    channel = (3, _CHANNEL_NAME, "Channel")
    cluster = (4, _CLUSTER_NAME, "Cluster")
    pdu = (5, _PDU_NAME, "Pdu")
    frame = (6, _FRAME_NAME, "Frame")


class DMAssistant_MainUI_Idx(Enum):  # Data Mapping Assistant助手主界面标题栏索引
    checkbox = (0, _CHECKBOX_STATUS, "checkbox")
    component = (1, _COMPONENT_NAME, "Component")
    port_prototype = (2, _PORT_NAME, "Port Prototype")
    communication_element = (3, _DATA_ELEMENT_NAME, "Communication Element")
    direction = (4, _DIRECTION, "Direction")
    mapped_system_signals = (5, _SYSTEM_SIGNAL_NAME, "Mapped System Signals")
    channel = (6, _CHANNEL_NAME, "Channel")
    cluster = (7, _CLUSTER_NAME, "Cluster")
    pdu = (8, _PDU_NAME, "Pdu")
    frame = (9, _FRAME_NAME, "Frame")
    com_ldcom = (10, _COM_LDCOM, "Com/Ldcom")


DMAssistant_MapUI_Idx = DMEditor_MapUI_Idx  # Data Mapping Assistant助手连接界面标题栏索引

DMAssistant_SignalUI_Idx = DMEditor_SignalUI_Idx  # Data MappingAssistant助手Signal选择界面表格标题栏索引


class DataMappingUI_Idx(Enum):
    dmeditor_mainui_idx = 0
    dmeditor_mapui_idx = 1
    dmeditor_signalui_idx = 2
    dmassistant_mainui_idx = 3
    dmassistant_mapui_idx = 4
    dmassistant_signalui_idx = 5


class MAPPING_UI_PROCESS_STS(Enum):
    none = 0
    start_process_struct_data = 1


class DataMappingFunc:

    def __init__(self):
        self.asw_autosar_dict = get_autosar_asw_class()
        self.system_autosar_dict = get_autosar_system_class()
        self.user_selected_data = [""] * len(DataMappingUI_Idx)
        self.ui_data_buffer = [[]] * len(DataMappingUI_Idx)
        self.mapping_data = []

    def __get_mapping_data_info(self):
        return [[x for x in sublist] for sublist in self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value]]

    def init_mapping_data_status(self):
        self.mapping_data = self.__get_mapping_data_info()

    def is_mapping_data_updated(self) -> bool:
        latest_mapping_data = self.__get_mapping_data_info()
        if len(latest_mapping_data) != len(self.mapping_data):
            return True
        for d0, d1 in zip(latest_mapping_data, self.mapping_data):
            if d0 != d1:
                return True
        return False

    def update_data_mapping_ui_func_data(self):
        """DataMapping相关字典数据更新(打开工程)"""
        self.asw_autosar = get_autosar_asw_class()
        self.system_autosar_dict = get_autosar_system_class()
        self.asw_ports = DataMapping.get_all_swc_ports_dict(self.asw_autosar)
        self.flatextract_datamppings = DataMapping.get_port_to_signal_pairs_from_flatextract(
            self.system_autosar_dict.get("FlatExtract", None)
        )
        self.system_signals_dict = DataMapping.get_system_signal_to_isignal_mappings_info(
            self.system_autosar_dict.get("Communication", None), get_autosar_bsw_class().get("Com", None)
        )
        asw_ports_add_mappings_info = DataMapping.update_data_mappings_to_ports(
            self.asw_ports["all_port_data_s"], self.flatextract_datamppings, self.system_signals_dict
        )
        self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value] = self.port_data_mappings_to_ui_layout(
            asw_ports_add_mappings_info
        )

    def update_flatextract_data_mapping_after_import(self):
        """导入DBC/LDF、ASW更新flatextract"""
        DataMapping.update_flatextract_data_mapping_from_files_import(
            get_autosar_asw_class(), get_autosar_system_class(), get_autosar_bsw_class().get("Com", None)
        )
        self.update_data_mapping_ui_func_data()

    def get_rte_editor_ui_data_mapping_table_data(self):
        """页面切换到DataMapping时刷新界面

        Returns:
            _type_: _description_
        """
        self.update_data_mapping_ui_func_data()
        return self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value]

    def get_data_mapping_ui_data_after_user_operation(self):
        self.update_data_mapping_ui_func_data()
        return self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value]

    def cbk_get_main_table_data(self):
        return self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value]

    @log_function_stats(["RTE", "DataMapping", "手动连接"])
    def get_data_mapping_editor_map_ui_data_from_editor_main_ui(self, param_dict):
        """data_mapping_editor选择port后右键连接后弹出的map界面数据

        Args:
            param_dict (dict): _description_

        Returns:
            _type_: _description_
        """
        self.user_selected_data[DataMappingUI_Idx.dmeditor_mainui_idx.value] = param_dict["row_items"]
        self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mapui_idx.value] = self.get_first_popups_dialog_data(
            list(param_dict["row_items"].values()), _DATA_MAPPING_EDITOR
        )
        return self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mapui_idx.value]

    def get_data_mapping_editor_map_ui_data_from_editor_signal_ui(self, param_dict):
        """data_mapping_editor选择signal后回到map界面的数据

        Args:
            param_dict (_type_): _description_
        """
        self.user_selected_data[DataMappingUI_Idx.dmeditor_signalui_idx.value] = param_dict["row_items"]
        self.update_mapui_data(
            param_dict["row_items"],
            self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mapui_idx.value],
            _DATA_MAPPING_EDITOR,
        )
        return self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mapui_idx.value]

    def get_data_mapping_editor_signal_ui_data_from_editor_map_ui(self, param_dict):
        """data_mapping_editor map界面双击弹出signal选择界面的数据

        Args:
            param_dict (_type_): _description_

        Returns:
            _type_: _description_
        """
        self.user_selected_data[DataMappingUI_Idx.dmeditor_mapui_idx.value] = param_dict["row_items"]
        self.ui_data_buffer[DataMappingUI_Idx.dmeditor_signalui_idx.value] = self.get_second_popups_dialog_data(
            param_dict["row_items"], _DATA_MAPPING_EDITOR
        )
        return self.ui_data_buffer[DataMappingUI_Idx.dmeditor_signalui_idx.value]

    @log_function_stats(["RTE", "DataMapping", "完成连接"])
    def get_data_mapping_editor_main_ui_data_from_editor_map_ui(self, param_dict):
        """data_mapping_editor map界面点击finish完成mapping后回到主界面的数据

        Args:
            param_dict (_type_): _description_
        """
        self.user_selected_data[DataMappingUI_Idx.dmeditor_mapui_idx.value] = param_dict["row_items"]
        self.first_popups_dialog_finish_process(param_dict["row_items"])
        self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value] = (
            self.get_data_mapping_ui_data_after_user_operation()
        )
        return self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value]

    @log_function_stats(["RTE", "DataMapping", "手动断开连接"])
    def get_data_mapping_editor_main_ui_data_right_click_remove_mapping(self, param_dict):
        """data_mapping_editor 右键连接断开连接后主界面的数据

        Args:
            param_dict (_type_): _description_
        """
        self.manual_remove_data_mapping_process(param_dict["row_items"])
        self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value] = (
            self.get_data_mapping_ui_data_after_user_operation()
        )
        return self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value]

    @log_function_stats(["RTE", "DataMapping", "打开连接助手"])
    def get_data_mapping_assistant_main_ui_data_open_assistant(self, param_dict=None):
        """data_mapping_assistant 打开助手主界面的数据

        Args:
            param_dict (_type_): _description_
        """
        self.ui_data_buffer[DataMappingUI_Idx.dmassistant_mainui_idx.value] = (
            self._prepare_data_mapping_assistant_fitst_popups_data(
                self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value]
            )
        )
        return self.ui_data_buffer[DataMappingUI_Idx.dmassistant_mainui_idx.value]

    def get_data_mapping_assistant_map_ui_data_after_selecting_port(self, param_dict):
        """data_mapping_assistant 助手主界面选择port点击next后的map界面的数据

        Args:
            param_dict (_type_): _description_
        """
        selected_data = param_dict["selected_data"]
        self.ui_data_buffer[DataMappingUI_Idx.dmassistant_mapui_idx.value] = self.get_first_popups_dialog_data(
            selected_data, _DATA_MAPPING_ASSISTANT, param_dict["filter"]
        )
        return self.ui_data_buffer[DataMappingUI_Idx.dmassistant_mapui_idx.value]

    def get_data_mapping_assistant_map_ui_data_after_selecting_signal(self, param_dict):
        """data_mapping_assistant 在signal选择弹窗中选择signal并点击finish之后回到map界面的数据

        Args:
            param_dict (_type_): _description_
        """
        self.user_selected_data[DataMappingUI_Idx.dmassistant_signalui_idx.value] = param_dict["row_items"]
        if len(param_dict["row_items"]) > 1:
            logger.warning("DataMapping: Only one signal can be selected at a time!")
        self.ui_data_buffer[DataMappingUI_Idx.dmassistant_mapui_idx.value] = self.update_mapui_data(
            param_dict["row_items"],
            self.ui_data_buffer[DataMappingUI_Idx.dmassistant_mapui_idx.value],
            _DATA_MAPPING_ASSISTANT,
        )
        return self.ui_data_buffer[DataMappingUI_Idx.dmassistant_mapui_idx.value]

    def get_data_mapping_assistant_signal_ui_data(self, param_dict):
        """data_mapping_assistant 在map界面双击弹出signal选择界面的数据

        Args:
            param_dict (_type_): _description_
        """
        self.user_selected_data[DataMappingUI_Idx.dmassistant_mapui_idx.value] = param_dict["row_items"]
        self.ui_data_buffer[DataMappingUI_Idx.dmassistant_signalui_idx.value] = self.get_second_popups_dialog_data(
            param_dict["row_items"], _DATA_MAPPING_ASSISTANT
        )
        if len(self.ui_data_buffer[DataMappingUI_Idx.dmassistant_signalui_idx.value]) > 0:
            data = [""] * len(DMAssistant_SignalUI_Idx)
            data[DMAssistant_SignalUI_Idx.checkbox.value[0]] = False
            data[DMAssistant_SignalUI_Idx.system_signal_name.value[0]] = DATA_MAPPING_UI_DEFAULT_VALUE[
                "system_signal_to_be_mapped"
            ]
            self.ui_data_buffer[DataMappingUI_Idx.dmassistant_signalui_idx.value].insert(0, data)
        return self.ui_data_buffer[DataMappingUI_Idx.dmassistant_signalui_idx.value]

    def get_data_mapping_editor_main_ui_data_after_assistant_mapping(self, param_dict):
        """data_mapping_editor assistant map界面点击finish完成mapping后回到主界面的数据

        Args:
            param_dict (_type_): _description_
        """
        self.user_selected_data[DataMappingUI_Idx.dmassistant_mapui_idx.value] = param_dict["row_items"]
        self.first_popups_dialog_finish_process(param_dict["row_items"])
        self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value] = (
            self.get_data_mapping_ui_data_after_user_operation()
        )
        return self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value]

    @classmethod
    def port_data_mappings_to_ui_layout(cls, ports_mappings_info):

        def init_row_data(mapping_info=None, signal_type=None):
            data_s = []
            data = [""] * len(DMEditor_MainUI_Idx)
            data[DMEditor_MainUI_Idx.port_prototype.value[0]] = port_info["Name"]
            data[DMEditor_MainUI_Idx.component_prototype.value[0]] = port_info["Component"]
            data[DMEditor_MainUI_Idx.communication_element.value[0]] = swc_p_d.split("/")[-1]
            data[DMEditor_MainUI_Idx.direction.value[0]] = port_info["direction"]
            data[DMEditor_MainUI_Idx.mapping.value[0]] = "No"
            if signal_type is not None:
                data[DMEditor_MainUI_Idx.system_signal.value[0]] = mapping_info["short_name"]
                data[DMEditor_MainUI_Idx.channel.value[0]] = "CHNL"
                data[DMEditor_MainUI_Idx.cluster.value[0]] = ""
                data[DMEditor_MainUI_Idx.pdu.value[0]] = mapping_info["pdu"]
                data[DMEditor_MainUI_Idx.frame.value[0]] = mapping_info["pdu"]
                data[DMEditor_MainUI_Idx.com_ldcom.value[0]] = "Com"
                data[DMEditor_MainUI_Idx.mapping.value[0]] = "Yes"
            data_s.append(data)
            if signal_type == "system_signal_group":
                data_name = port_info["DATA-ELEMENT-REF"]["name"]
                type_mapping = port_info["type_mappings"].get(f"{mapping_info['full_name']}")  # TODO 异常处理
                group_name = mapping_info["short_name"]
                for record_element_mapping in type_mapping:
                    group_signal_name = record_element_mapping["system_signal_ref"].split("/")[-1]
                    record_element_name = record_element_mapping["implementation_record_element_ref"].split("/")[-1]
                    data = [""] * len(DMEditor_MainUI_Idx)
                    data[DMEditor_MainUI_Idx.port_prototype.value[0]] = port_info["Name"]
                    data[DMEditor_MainUI_Idx.component_prototype.value[0]] = port_info["Component"]
                    data[DMEditor_MainUI_Idx.communication_element.value[0]] = f"{data_name}.{record_element_name}"
                    data[DMEditor_MainUI_Idx.direction.value[0]] = port_info["direction"]
                    data[DMEditor_MainUI_Idx.system_signal.value[0]] = f"{group_name}.{group_signal_name}"
                    data[DMEditor_MainUI_Idx.channel.value[0]] = "CHNL"
                    data[DMEditor_MainUI_Idx.cluster.value[0]] = ""
                    data[DMEditor_MainUI_Idx.pdu.value[0]] = mapping_info["pdu"]
                    data[DMEditor_MainUI_Idx.frame.value[0]] = mapping_info["pdu"]
                    data[DMEditor_MainUI_Idx.com_ldcom.value[0]] = "Com"
                    data[DMEditor_MainUI_Idx.mapping.value[0]] = "Yes"
                    data_s.append(data)
            return data_s

        ui_data_list = []
        for swc_p_d, port_info in ports_mappings_info.items():
            if len(port_info.get("data_mappings", [])) == 0:
                row_data_s = init_row_data()
                ui_data_list += row_data_s
            for mapping in port_info.get("data_mappings", []):
                row_data_s = init_row_data(mapping, port_info["allowable_signal_type"])
                ui_data_list += row_data_s
        return ui_data_list

    @classmethod
    def _data_structure_conversion_to_dmeditor_mapui(cls, port_info, enable_compatibility=False):
        rv = []
        data = [""] * len(DMEditor_MapUI_Idx)
        data[DMEditor_MapUI_Idx.port_prototype.value[0]] = port_info["Name"]
        data[DMEditor_MapUI_Idx.component.value[0]] = port_info["Component"]
        data[DMEditor_MapUI_Idx.communication_element.value[0]] = port_info["DATA-ELEMENT-REF"]["name"]
        data[DMEditor_MapUI_Idx.direction.value[0]] = port_info["direction"]
        data[DMEditor_MapUI_Idx.system_signal_to_be_mapped.value[0]] = DATA_MAPPING_UI_DEFAULT_VALUE[
            "system_signal_to_be_mapped"
        ]
        signals_recommend = port_info.get("signals_recommend", [])
        signals_recommend.sort(key=lambda x: x["compatibility"].value[0])
        data_type_compatibility = False
        if len(signals_recommend) > 0:
            best_compatibility = signals_recommend[0]["compatibility"].value[0]
            if best_compatibility <= Compatibility.partial.value[0] or (
                best_compatibility <= Compatibility.partial_datalength_compatible.value[0]
                and enable_compatibility is True
            ):
                data_type_compatibility = True
                signal_info = signals_recommend[0]["signal"]
                data[DMEditor_MapUI_Idx.system_signal_to_be_mapped.value[0]] = signal_info["short_name"]
                data[DMEditor_MapUI_Idx.channel.value[0]] = "CHNL"
                data[DMEditor_MapUI_Idx.cluster.value[0]] = ""
                data[DMEditor_MapUI_Idx.pdu.value[0]] = signal_info["pdu"]
                data[DMEditor_MapUI_Idx.frame.value[0]] = signal_info["pdu"]
                data[DMEditor_MapUI_Idx.com_ldcom.value[0]] = "Com"
                data[DMEditor_MapUI_Idx.compatibility.value[0]] = signals_recommend[0]["compatibility"].value[1]
        rv.append(data)
        if port_info["allowable_signal_type"] == "system_signal_group":
            idt_detail = port_info["DATA-ELEMENT-REF"]["idt_detail"]
            data_name = port_info["DATA-ELEMENT-REF"]["name"]
            for member in idt_detail["members"]:
                data = [""] * len(DMEditor_MapUI_Idx)
                data[DMEditor_MapUI_Idx.port_prototype.value[0]] = port_info["Name"]
                data[DMEditor_MapUI_Idx.component.value[0]] = port_info["Component"]
                data[DMEditor_MapUI_Idx.communication_element.value[0]] = f'{data_name}.{member["name"]}'
                data[DMEditor_MapUI_Idx.direction.value[0]] = port_info["direction"]
                data[DMEditor_MapUI_Idx.system_signal_to_be_mapped.value[0]] = DATA_MAPPING_UI_DEFAULT_VALUE[
                    "system_signal_to_be_mapped"
                ]
                if len(signals_recommend) > 0 and data_type_compatibility:
                    group_signal_info = signals_recommend[0]["signal"]["type_mappings_brief"].get(member["name"], None)
                    if group_signal_info is not None:
                        signal_info = signals_recommend[0]["signal"]
                        data[DMEditor_MapUI_Idx.system_signal_to_be_mapped.value[0]] = (
                            f'{group_signal_info["group_name"]}.{group_signal_info["system_signal"]}'
                        )
                        data[DMEditor_MapUI_Idx.channel.value[0]] = "CHNL"
                        data[DMEditor_MapUI_Idx.cluster.value[0]] = ""
                        data[DMEditor_MapUI_Idx.pdu.value[0]] = signal_info["pdu"]
                        data[DMEditor_MapUI_Idx.frame.value[0]] = signal_info["pdu"]
                        data[DMEditor_MapUI_Idx.com_ldcom.value[0]] = "Com"
                        data[DMEditor_MapUI_Idx.compatibility.value[0]] = signals_recommend[0]["compatibility"].value[1]
                rv.append(data)
        return rv

    @classmethod
    def _data_structure_conversion_to_dmeditor_signalui(cls, signals: dict, page_type, signal_group_name=None):
        """布局转换: signal转换为信号选择界面的布局

        Args:
            signals (dict): key为信号名的字典

        Returns:
            list: 符合界面布局的list
        """
        rv = []
        if page_type == _DATA_MAPPING_EDITOR:
            for signal in signals.values():
                data = [""] * len(DMEditor_SignalUI_Idx)
                if signal_group_name is None:
                    data[DMEditor_SignalUI_Idx.system_signal_name.value[0]] = signal["short_name"]
                else:
                    data[DMEditor_SignalUI_Idx.system_signal_name.value[0]] = (
                        f'{signal_group_name}.{signal["short_name"]}'
                    )
                data[DMEditor_SignalUI_Idx.channel.value[0]] = "CHNL"
                data[DMEditor_SignalUI_Idx.cluster.value[0]] = ""
                data[DMEditor_SignalUI_Idx.pdu.value[0]] = signal["pdu"]
                data[DMEditor_SignalUI_Idx.frame.value[0]] = signal["pdu"]
                rv.append(data)
        elif page_type == _DATA_MAPPING_ASSISTANT:
            for signal in signals.values():
                data = [""] * len(DMAssistant_SignalUI_Idx)
                data[DMAssistant_SignalUI_Idx.checkbox.value[0]] = False
                if signal_group_name is None:
                    data[DMAssistant_SignalUI_Idx.system_signal_name.value[0]] = signal["short_name"]
                else:
                    data[DMAssistant_SignalUI_Idx.system_signal_name.value[0]] = (
                        f'{signal_group_name}.{signal["short_name"]}'
                    )
                data[DMAssistant_SignalUI_Idx.channel.value[0]] = "CHNL"
                data[DMAssistant_SignalUI_Idx.cluster.value[0]] = ""
                data[DMAssistant_SignalUI_Idx.pdu.value[0]] = signal["pdu"]
                data[DMAssistant_SignalUI_Idx.frame.value[0]] = signal["pdu"]
                rv.append(data)
        return rv

    def get_port_info_from_ui_row_data(self, ui_page_type, row_data):
        port_info = None
        if ui_page_type == DataMappingUI_Idx.dmeditor_mainui_idx.value:
            if len(row_data) != len(DMEditor_MainUI_Idx):
                logger.error("DataMapping: len(row_data) != len(DMEditor_MainUI_Idx)")
                return
            swc_name = row_data[DMEditor_MainUI_Idx.component_prototype.value[0]]
            port_name = row_data[DMEditor_MainUI_Idx.port_prototype.value[0]]
            data_name = row_data[DMEditor_MainUI_Idx.communication_element.value[0]]
        elif ui_page_type == DataMappingUI_Idx.dmeditor_mapui_idx.value:
            if len(row_data) != len(DMEditor_MapUI_Idx):
                logger.error("DataMapping: len(row_data) != len(DMEditor_MainUI_Idx)")
                return
            swc_name = row_data[DMEditor_MapUI_Idx.component.value[0]]
            port_name = row_data[DMEditor_MapUI_Idx.port_prototype.value[0]]
            data_name = row_data[DMEditor_MapUI_Idx.communication_element.value[0]]
        elif ui_page_type == DataMappingUI_Idx.dmassistant_mainui_idx.value:
            if len(row_data) != len(DMAssistant_MainUI_Idx):
                logger.error("DataMapping: len(row_data) != len(DMEditor_MainUI_Idx)")
                return
            swc_name = row_data[DMAssistant_MainUI_Idx.component.value[0]]
            port_name = row_data[DMAssistant_MainUI_Idx.port_prototype.value[0]]
            data_name = row_data[DMAssistant_MainUI_Idx.communication_element.value[0]]
        elif ui_page_type == DataMappingUI_Idx.dmassistant_signalui_idx.value:
            if len(row_data) != len(DMAssistant_MapUI_Idx):
                logger.error("DataMapping: len(row_data) != len(DMEditor_MainUI_Idx)")
                return
            swc_name = row_data[DMAssistant_MapUI_Idx.component.value[0]]
            port_name = row_data[DMAssistant_MapUI_Idx.port_prototype.value[0]]
            data_name = row_data[DMAssistant_MapUI_Idx.communication_element.value[0]]
        elif ui_page_type == DataMappingUI_Idx.dmassistant_mapui_idx.value:
            if len(row_data) != len(DMAssistant_MapUI_Idx):
                logger.error("DataMapping: len(row_data) != len(DMEditor_MainUI_Idx)")
                return
            swc_name = row_data[DMAssistant_MapUI_Idx.component.value[0]]
            port_name = row_data[DMAssistant_MapUI_Idx.port_prototype.value[0]]
            data_name = row_data[DMAssistant_MapUI_Idx.communication_element.value[0]]
        else:
            return
        port_name = port_name.split(".")[0]
        data_name = data_name.split(".")[0]
        swc_p_d = f"{swc_name}/{port_name}/{data_name}"
        port_info = self.asw_ports.get("all_port_data_s", {}).get(swc_p_d, None)
        if port_info is None:
            logger.error(f"DataMapping: Port not found ({swc_name} {port_name} {data_name})!")
        return port_info

    def get_signal_info(self, direction, signal_type, signal_name):
        """根据方向、类型和名字获取signal/signal group"""
        if "." in signal_name and signal_type == "system_signal":
            return (
                self.system_signals_dict.get(direction, {})
                .get("system_signal_group", {})
                .get(signal_name.split(".")[0], {})
                .get("system_signal", {})
                .get(signal_name.split(".")[-1], None)
            )
        else:
            return self.system_signals_dict.get(direction, {}).get(signal_type, {}).get(signal_name.split(".")[0], None)

    def get_groupsignal_info(self, direction, signal_name):
        """根据方向、类型和名字获取signal/signal group"""
        return self.system_signals_dict.get(direction, {}).get("system_signal", {}).get(signal_name, None)

    def manual_remove_data_mapping_process(self, selected_data_dict):
        dme_main_data = self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value]
        if len(selected_data_dict):
            for key, selected_data in selected_data_dict.items():
                if selected_data not in self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value]:
                    continue
                row = self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value].index(selected_data)
                if (
                    not isinstance(row, int)
                    or len(self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value]) <= row
                ):
                    return dme_main_data
                if (
                    self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value][row][
                        DMEditor_MainUI_Idx.mapping.value[0]
                    ]
                    != "Yes"
                ):
                    return dme_main_data
                delete_result = self._arxml_remove_mapping(
                    self.system_autosar_dict, self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value], row
                )
                if delete_result is not True:
                    sg = self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value][row][
                        DMEditor_MainUI_Idx.system_signal.value[0]
                    ]
                    pt = self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value][row][
                        DMEditor_MainUI_Idx.port_prototype.value[0]
                    ]
                    logger.warning(f"Can't find data mapping, signal:{sg}, port:{pt}")
        asw_ports_add_mappings_info = DataMapping.update_data_mappings_to_ports(
            self.asw_ports["all_port_data_s"], self.flatextract_datamppings, self.system_signals_dict
        )
        return self.port_data_mappings_to_ui_layout(asw_ports_add_mappings_info)

    def _ui_remove_mapping(self, main_table_data, row):
        if self._same_port_check(
            self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value], row, row - 1
        ) or self._same_port_check(self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value], row, row + 1):
            self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value].pop(row)
        else:
            self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value][row][
                DMEditor_MainUI_Idx.system_signal.value[0]
            ] = ""
            self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value][row][DMEditor_MainUI_Idx.pdu.value[0]] = ""
            self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value][row][
                DMEditor_MainUI_Idx.channel.value[0]
            ] = ""
            self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value][row][
                DMEditor_MainUI_Idx.frame.value[0]
            ] = ""
            self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value][row][
                DMEditor_MainUI_Idx.cluster.value[0]
            ] = ""
            self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value][row][
                DMEditor_MainUI_Idx.com_ldcom.value[0]
            ] = ""
            self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value][row][
                DMEditor_MainUI_Idx.mapping.value[0]
            ] = "No"

    @classmethod
    def _same_port_check(cls, main_table_data, row1, row2):
        if row2 < 0 or row2 >= len(main_table_data):
            return False
        if (
            main_table_data[row1][DMEditor_MainUI_Idx.port_prototype.value[0]]
            == main_table_data[row2][DMEditor_MainUI_Idx.port_prototype.value[0]]
            and main_table_data[row1][DMEditor_MainUI_Idx.component_prototype.value[0]]
            == main_table_data[row2][DMEditor_MainUI_Idx.component_prototype.value[0]]
            and main_table_data[row1][DMEditor_MainUI_Idx.communication_element.value[0]]
            == main_table_data[row2][DMEditor_MainUI_Idx.communication_element.value[0]]
            and main_table_data[row1][DMEditor_MainUI_Idx.direction.value[0]]
            == main_table_data[row2][DMEditor_MainUI_Idx.direction.value[0]]
        ):
            return True
        else:
            return False

    def _arxml_remove_mapping(self, system_autosar_dict, main_table_data, row):
        selected_data = main_table_data[row]
        port_info = self.get_port_info_from_ui_row_data(DataMappingUI_Idx.dmeditor_mainui_idx.value, selected_data)
        if port_info is None:
            logger.error("DataMapping: Port not found!")
            return
        signal_info = self.get_signal_info(
            port_info["direction"],
            port_info["allowable_signal_type"],
            selected_data[DMEditor_MainUI_Idx.system_signal.value[0]],
        )
        if signal_info is None:
            return
        rm_result = DataMapping.delete_data_mapping_from_arxml(system_autosar_dict, port_info, signal_info)
        if rm_result is True:
            if signal_info in port_info["data_mappings"]:
                port_info["data_mappings"].remove(signal_info)
            if port_info.get("type_mappings", {}).get(f'/Signal/{signal_info["short_name"]}', None) is not None:
                port_info["type_mappings"].pop(f'/Signal/{signal_info["short_name"]}', None)
        return rm_result

    def get_first_popups_dialog_data(self, selected_data_list, page_type, filter_conditions={}):
        rv = []
        if page_type == _DATA_MAPPING_EDITOR:
            for selected_data in selected_data_list:
                port_info = self.get_port_info_from_ui_row_data(
                    DataMappingUI_Idx.dmeditor_mainui_idx.value, selected_data
                )
                if port_info is None:
                    logger.error("DataMapping: Port not found!")
                    continue
                port_list = DataMapping.ports_to_signal_mapping_recommend([port_info], self.system_signals_dict, {})
                for port in port_list:
                    rv += self._data_structure_conversion_to_dmeditor_mapui(port, True)
        elif page_type == _DATA_MAPPING_ASSISTANT:
            for selected_data in selected_data_list:
                port_info = self.get_port_info_from_ui_row_data(
                    DataMappingUI_Idx.dmassistant_mainui_idx.value, selected_data
                )
                if port_info is None:
                    logger.error("DataMapping: Port not found!")
                    continue
                port_list = DataMapping.ports_to_signal_mapping_recommend(
                    [port_info], self.system_signals_dict, filter_conditions
                )
                for port in port_list:
                    rv += self._data_structure_conversion_to_dmeditor_mapui(
                        port, filter_conditions.get("match_compatibility", True)
                    )
        return rv

    def get_second_popups_dialog_data(self, selected_data_dict, page_type):

        rv = []
        signals_dict = {}
        for selected_data in selected_data_dict.values():
            if page_type == _DATA_MAPPING_EDITOR:
                ui_page_idx = DataMappingUI_Idx.dmeditor_mapui_idx
                mapui_idx = DMEditor_MapUI_Idx
            elif page_type == _DATA_MAPPING_ASSISTANT:
                ui_page_idx = DataMappingUI_Idx.dmassistant_mapui_idx
                mapui_idx = DMAssistant_MapUI_Idx
            else:
                return rv
            port_info = self.get_port_info_from_ui_row_data(ui_page_idx.value, selected_data)
            if port_info is None:
                logger.error(f'Port not found in row data "{selected_data}"!')
                continue
            filter_conditions = {
                "direction": selected_data[mapui_idx.direction.value[0]],
                "signal_type": port_info["allowable_signal_type"],
            }
            if "." not in selected_data[mapui_idx.communication_element.value[0]]:
                """不是结构体成员"""
                signals_dict = DataMapping.system_signals_filter(self.system_signals_dict, filter_conditions)
                rv = self._data_structure_conversion_to_dmeditor_signalui(signals_dict, page_type)
            else:
                element_split = selected_data[mapui_idx.communication_element.value[0]].split(".")
                data_name = element_split[0]
                signal_group = self.find_signal_group_from_ui_data(
                    self.ui_data_buffer[ui_page_idx.value], selected_data, data_name
                )
                if signal_group is None:
                    return []
                signals_dict = signal_group.get("system_signal", {})
                rv = self._data_structure_conversion_to_dmeditor_signalui(
                    signals_dict, page_type, signal_group["short_name"]
                )
        return rv

    def find_signal_group_from_ui_data(self, ui_data_buffer, selected_data, data_name):
        for row_data in ui_data_buffer:
            if (
                row_data[DMEditor_MapUI_Idx.communication_element.value[0]] == data_name
                and row_data[DMEditor_MapUI_Idx.port_prototype.value[0]]
                == selected_data[DMEditor_MapUI_Idx.port_prototype.value[0]]
                and row_data[DMEditor_MapUI_Idx.component.value[0]]
                == selected_data[DMEditor_MapUI_Idx.component.value[0]]
            ):
                port_info = self.get_port_info_from_ui_row_data(DataMappingUI_Idx.dmeditor_mapui_idx.value, row_data)
                if port_info is None:
                    return
                signal_group = self.get_signal_info(
                    port_info["direction"],
                    port_info["allowable_signal_type"],
                    row_data[DMEditor_MapUI_Idx.system_signal_to_be_mapped.value[0]],
                )
                return signal_group
        else:
            return

    def update_mapui_data(self, selected_data_dict, mapui_data, page_type):
        if page_type == _DATA_MAPPING_EDITOR:
            mapui_selected_data = self.user_selected_data[DataMappingUI_Idx.dmeditor_mapui_idx.value]
            mapui_idx_val = DataMappingUI_Idx.dmeditor_mapui_idx.value
        else:
            mapui_selected_data = self.user_selected_data[DataMappingUI_Idx.dmassistant_mapui_idx.value]
            mapui_idx_val = DataMappingUI_Idx.dmassistant_mapui_idx.value
        for selected_data in selected_data_dict.values():
            for row_data in mapui_selected_data.values():
                if row_data not in mapui_data:
                    continue
                idx = mapui_data.index(row_data)

                update_row_data = mapui_data[idx]
                port_name = update_row_data[DMEditor_MapUI_Idx.port_prototype.value[0]]
                port_detail_info = self.get_port_info_from_ui_row_data(mapui_idx_val, row_data)
                data_element_name = update_row_data[DMEditor_MapUI_Idx.communication_element.value[0]]
                signal_group_old = update_row_data[DMEditor_MapUI_Idx.system_signal_to_be_mapped.value[0]]
                signal_group_new = selected_data[DMEditor_SignalUI_Idx.system_signal_name.value[0]].split("/")[-1]
                if self._signal_group_change(port_name, port_detail_info, signal_group_old, signal_group_new):
                    self._clear_structure_elements_mapping_info(mapui_data, idx, data_element_name)
                signal_name = selected_data[DMEditor_SignalUI_Idx.system_signal_name.value[0]]
                update_row_data[DMEditor_MapUI_Idx.system_signal_to_be_mapped.value[0]] = selected_data[
                    DMEditor_SignalUI_Idx.system_signal_name.value[0]
                ].split("/")[-1]
                update_row_data[DMEditor_MapUI_Idx.channel.value[0]] = selected_data[
                    DMEditor_SignalUI_Idx.channel.value[0]
                ]
                update_row_data[DMEditor_MapUI_Idx.cluster.value[0]] = selected_data[
                    DMEditor_SignalUI_Idx.cluster.value[0]
                ]
                update_row_data[DMEditor_MapUI_Idx.pdu.value[0]] = selected_data[DMEditor_SignalUI_Idx.pdu.value[0]]
                update_row_data[DMEditor_MapUI_Idx.frame.value[0]] = selected_data[DMEditor_SignalUI_Idx.frame.value[0]]
                update_row_data[DMEditor_MapUI_Idx.com_ldcom.value[0]] = DATA_MAPPING_UI_DEFAULT_VALUE["com_ldcom"]
                update_row_data[DMEditor_MapUI_Idx.compatibility.value[0]] = DataMapping.get_port_signal_compatibility(
                    port_name, data_element_name, signal_name
                ).value[1]
                break
            break
        return mapui_data

    def _signal_group_change(self, port_name, port_detail_info, signal_group_old, signal_group_new):
        return (
            "." not in port_name
            and port_detail_info.get("allowable_signal_type", None) == "system_signal_group"
            and signal_group_old != signal_group_new
        )

    def _clear_structure_elements_mapping_info(self, mapui_data, idx, data_element_name):
        if len(mapui_data) < idx + 2:
            return
        for row_data in mapui_data[idx + 1 :]:
            data_element_dot_member = row_data[DMEditor_MapUI_Idx.communication_element.value[0]]
            if "." in data_element_dot_member and data_element_name == data_element_dot_member.split(".")[0]:
                row_data[DMEditor_MapUI_Idx.system_signal_to_be_mapped.value[0]] = DATA_MAPPING_UI_DEFAULT_VALUE[
                    "system_signal_to_be_mapped"
                ]
                row_data[DMEditor_MapUI_Idx.channel.value[0]] = ""
                row_data[DMEditor_MapUI_Idx.cluster.value[0]] = ""
                row_data[DMEditor_MapUI_Idx.pdu.value[0]] = ""
                row_data[DMEditor_MapUI_Idx.frame.value[0]] = ""
                row_data[DMEditor_MapUI_Idx.com_ldcom.value[0]] = ""
                row_data[DMEditor_MapUI_Idx.compatibility.value[0]] = ""
            else:
                break

    def first_popups_dialog_finish_process(self, selected_data_dict):

        self.user_selected_data[DataMappingUI_Idx.dmeditor_mapui_idx.value] = selected_data_dict
        mapping_temp = None
        for row_data in selected_data_dict.values():
            system_signal_to_be_mapped = row_data[DMEditor_MapUI_Idx.system_signal_to_be_mapped.value[0]]
            port_info = self.get_port_info_from_ui_row_data(DataMappingUI_Idx.dmeditor_mapui_idx.value, row_data)
            if port_info is None or system_signal_to_be_mapped in NOT_SELECT_SIGNAL:
                mapping_temp = None
                continue
            signal_info = self.get_signal_info(
                port_info["direction"], port_info["allowable_signal_type"], system_signal_to_be_mapped
            )
            if signal_info is None:
                mapping_temp = None
                logger.error(f"Signal {system_signal_to_be_mapped} not found!")
                continue
            if port_info["allowable_signal_type"] == "system_signal":
                mapping_temp = None
                if any(signal_info["short_name"] == x["short_name"] for x in port_info["data_mappings"]):
                    logger.ui_warning(
                        f'DataMappingUI: Port({port_info["Name"]}) already mapped to Signal({signal_info["short_name"]})'
                    )
                    continue
                sr_to_signal_mapping_dict = DataMapping.get_sr_to_signal_mapping_dict(
                    port_info["Tag"],
                    port_info["Component"],
                    port_info["Port_path"],
                    port_info["DATA-ELEMENT-REF"]["ref"],
                    signal_info["system_signal"],
                )
                DataMapping.add_new_data_mapping_arxml(self.system_autosar_dict, sr_to_signal_mapping_dict)
                port_info["data_mappings"].append(signal_info)
            elif port_info["allowable_signal_type"] == "system_signal_group":
                if "." not in system_signal_to_be_mapped:
                    mapping_temp = {"port": port_info, "signal_group": deepcopy(signal_info), "type_mapping": []}
                else:
                    group_dot_signal_name = system_signal_to_be_mapped
                    data_member = row_data[DMEditor_MapUI_Idx.communication_element.value[0]].split(".")[-1]
                    group_signal = self.get_signal_info(port_info["direction"], "system_signal", group_dot_signal_name)
                    if group_signal is None:
                        logger.error(f"Signal {group_dot_signal_name} not found!")
                        mapping_temp = None
                    if mapping_temp is None:
                        continue
                    mapping_temp["type_mapping"].append(
                        {
                            "implementation_record_element_ref": f'/DataTypes/{port_info["DATA-ELEMENT-REF"]["idt"]}/{data_member}',
                            "implementation_record_element": data_member,
                            "system_signal_ref": f'/Signal/{group_signal["short_name"]}',
                            "system_signal": group_signal["short_name"],
                        }
                    )
                    if len(mapping_temp["type_mapping"]) == len(
                        mapping_temp["port"]["DATA-ELEMENT-REF"]["idt_detail"]["members"]
                    ):
                        sr_to_signal_mapping_dict = DataMapping.get_sr_to_signalgroup_mapping_dict(
                            port_info, mapping_temp
                        )
                        mapping_temp = None
                        if any(signal_info["short_name"] == x["short_name"] for x in port_info["data_mappings"]):
                            logger.ui_warning(
                                f'DataMappingUI: Port({port_info["Name"]}) already mapped to SignalGroup({signal_info["short_name"]})'
                            )
                            continue
                        DataMapping.add_new_data_mapping_arxml(
                            self.system_autosar_dict, sr_to_signal_mapping_dict, "system_signal_group"
                        )
        return self.ui_data_buffer[DataMappingUI_Idx.dmeditor_mainui_idx.value]

    def _data_classifier_by_data_type(self, row_data_s):
        struct_data_s = []
        not_struct_data_s = []
        for row_data in row_data_s:
            port_info = self.get_port_info_from_ui_row_data(DataMappingUI_Idx.dmeditor_mapui_idx.value, row_data)
            if port_info is None:
                continue
            if port_info["allowable_signal_type"] == "system_signal_group":
                if row_data[DMEditor_MapUI_Idx.system_signal_to_be_mapped.value[0]] in NOT_SELECT_SIGNAL:

                    continue
                struct_data_s.append(row_data)
            elif port_info["allowable_signal_type"] == "system_signal":
                if row_data[DMEditor_MapUI_Idx.system_signal_to_be_mapped.value[0]] in NOT_SELECT_SIGNAL:
                    continue
                not_struct_data_s.append(row_data)
        return struct_data_s, not_struct_data_s

    @classmethod
    def _set_mapping_info(cls, component, context_port_ref, port_type, target_data_prototype_ref, signal):
        mapping_info = {
            "data_element_iref": {
                "context_component_ref": f"/COM/VCOS2/CFG/WORKFLOW/SYSDESC/SYNC/COMPOSITIONTYPE/{component}",
                "context_composition_ref": "/COM/VCOS2/CFG/WORKFLOW/SYSDESC/SYNC/SYSTEM/COMPOSITIONTYPE",
                "context_port_ref": context_port_ref,
                "port_type": port_type,
                "target_data_prototype_ref": target_data_prototype_ref,
            },
            "system_signal_ref": f"/Signal/{signal}",
            "type_mapping": {},
        }
        return mapping_info

    @classmethod
    def _prepare_data_mapping_assistant_fitst_popups_data(cls, main_table_data):
        rv = []
        for source_row_data in main_table_data:
            first_popups_row_data = cls._data_transformation_main_window_to_fitst_popups(False, source_row_data)
            rv.append(first_popups_row_data)
        return rv

    @classmethod
    def _update_data_mapping_main_window_data(
        cls, main_table_data, first_popups_table_data_list, second_popups_table_data_list
    ):
        rv = {}
        for second_popups_row_data in second_popups_table_data_list:
            if (
                second_popups_row_data[DMAssistant_MapUI_Idx.com_ldcom.value[0]]
                == DATA_MAPPING_UI_DEFAULT_VALUE["com_ldcom"]
                and second_popups_row_data[DMAssistant_MapUI_Idx.system_signal_to_be_mapped.value[0]]
                and second_popups_row_data[DMAssistant_MapUI_Idx.system_signal_to_be_mapped.value[0]]
                != DATA_MAPPING_UI_DEFAULT_VALUE["system_signal_to_be_mapped"]
            ):
                mappinged_main_table_row_data = cls._data_transformation_second_popups_to_main_table(
                    second_popups_row_data
                )
                ummapped_main_table_row_data = cls._data_transformation_second_popups_to_unmapped_main_table(
                    second_popups_row_data
                )
                if mappinged_main_table_row_data in main_table_data:
                    continue
                if ummapped_main_table_row_data in main_table_data:
                    idx = main_table_data.index(ummapped_main_table_row_data)
                    main_table_data[idx] = mappinged_main_table_row_data
                    mode = "modify"
                else:
                    idx = cls._get_insert_index(main_table_data, mappinged_main_table_row_data)
                    main_table_data.insert(idx, mappinged_main_table_row_data)
                    mode = "insert"

                rv.update({idx: {"data": mappinged_main_table_row_data, "mode": mode}})
        return rv

    @classmethod
    def _data_transformation_main_window_to_fitst_popups(cls, checkbox_state, source_row_data):
        first_popups_row_data = [""] * len(DMAssistant_MainUI_Idx)
        first_popups_row_data[DMAssistant_MainUI_Idx.checkbox.value[0]] = checkbox_state
        first_popups_row_data[DMAssistant_MainUI_Idx.component.value[0]] = source_row_data[
            DMEditor_MainUI_Idx.component_prototype.value[0]
        ]
        first_popups_row_data[DMAssistant_MainUI_Idx.port_prototype.value[0]] = source_row_data[
            DMEditor_MainUI_Idx.port_prototype.value[0]
        ]
        first_popups_row_data[DMAssistant_MainUI_Idx.communication_element.value[0]] = source_row_data[
            DMEditor_MainUI_Idx.communication_element.value[0]
        ]
        first_popups_row_data[DMAssistant_MainUI_Idx.direction.value[0]] = source_row_data[
            DMEditor_MainUI_Idx.direction.value[0]
        ]
        first_popups_row_data[DMAssistant_MainUI_Idx.mapped_system_signals.value[0]] = source_row_data[
            DMEditor_MainUI_Idx.system_signal.value[0]
        ]
        first_popups_row_data[DMAssistant_MainUI_Idx.channel.value[0]] = source_row_data[
            DMEditor_MainUI_Idx.channel.value[0]
        ]
        first_popups_row_data[DMAssistant_MainUI_Idx.cluster.value[0]] = source_row_data[
            DMEditor_MainUI_Idx.cluster.value[0]
        ]
        first_popups_row_data[DMAssistant_MainUI_Idx.pdu.value[0]] = source_row_data[DMEditor_MainUI_Idx.pdu.value[0]]
        first_popups_row_data[DMAssistant_MainUI_Idx.frame.value[0]] = source_row_data[
            DMEditor_MainUI_Idx.frame.value[0]
        ]
        first_popups_row_data[DMAssistant_MainUI_Idx.com_ldcom.value[0]] = source_row_data[
            DMEditor_MainUI_Idx.com_ldcom.value[0]
        ]
        return first_popups_row_data

    @classmethod
    def _data_transformation_second_popups_to_main_table(cls, source_row_data):
        rv = [""] * len(DMEditor_MainUI_Idx)
        rv[DMEditor_MainUI_Idx.port_prototype.value[0]] = source_row_data[DMAssistant_MapUI_Idx.port_prototype.value[0]]
        rv[DMEditor_MainUI_Idx.component_prototype.value[0]] = source_row_data[DMAssistant_MapUI_Idx.component.value[0]]
        rv[DMEditor_MainUI_Idx.mapping.value[0]] = "Yes"
        rv[DMEditor_MainUI_Idx.communication_element.value[0]] = source_row_data[
            DMAssistant_MapUI_Idx.communication_element.value[0]
        ]
        rv[DMEditor_MainUI_Idx.system_signal.value[0]] = source_row_data[
            DMAssistant_MapUI_Idx.system_signal_to_be_mapped.value[0]
        ]
        rv[DMEditor_MainUI_Idx.direction.value[0]] = source_row_data[DMAssistant_MapUI_Idx.direction.value[0]]
        rv[DMEditor_MainUI_Idx.channel.value[0]] = source_row_data[DMAssistant_MapUI_Idx.channel.value[0]]
        rv[DMEditor_MainUI_Idx.cluster.value[0]] = source_row_data[DMAssistant_MapUI_Idx.cluster.value[0]]
        rv[DMEditor_MainUI_Idx.pdu.value[0]] = source_row_data[DMAssistant_MapUI_Idx.pdu.value[0]]
        rv[DMEditor_MainUI_Idx.frame.value[0]] = source_row_data[DMAssistant_MapUI_Idx.frame.value[0]]
        rv[DMEditor_MainUI_Idx.com_ldcom.value[0]] = source_row_data[DMAssistant_MapUI_Idx.com_ldcom.value[0]]
        return rv

    @classmethod
    def _data_transformation_second_popups_to_unmapped_main_table(cls, source_row_data):
        rv = [""] * len(DMEditor_MainUI_Idx)
        rv[DMEditor_MainUI_Idx.port_prototype.value[0]] = source_row_data[DMAssistant_MapUI_Idx.port_prototype.value[0]]
        rv[DMEditor_MainUI_Idx.component_prototype.value[0]] = source_row_data[DMAssistant_MapUI_Idx.component.value[0]]
        rv[DMEditor_MainUI_Idx.mapping.value[0]] = "No"
        rv[DMEditor_MainUI_Idx.communication_element.value[0]] = source_row_data[
            DMAssistant_MapUI_Idx.communication_element.value[0]
        ]
        rv[DMEditor_MainUI_Idx.direction.value[0]] = source_row_data[DMAssistant_MapUI_Idx.direction.value[0]]
        return rv

    @classmethod
    def _get_insert_index(cls, main_table_data, new_mapping_row_data):
        idx = len(main_table_data)
        for find_index in range(len(main_table_data)):
            if (
                main_table_data[find_index][DMEditor_MainUI_Idx.port_prototype.value[0]]
                == new_mapping_row_data[DMEditor_MainUI_Idx.port_prototype.value[0]]
                and main_table_data[find_index][DMEditor_MainUI_Idx.component_prototype.value[0]]
                == new_mapping_row_data[DMEditor_MainUI_Idx.component_prototype.value[0]]
                and main_table_data[find_index][DMEditor_MainUI_Idx.mapping.value[0]]
                == new_mapping_row_data[DMEditor_MainUI_Idx.mapping.value[0]]
                and main_table_data[find_index][DMEditor_MainUI_Idx.communication_element.value[0]]
                == new_mapping_row_data[DMEditor_MainUI_Idx.communication_element.value[0]]
            ):
                idx = find_index
        if idx < len(main_table_data):
            idx += 1
        return idx
