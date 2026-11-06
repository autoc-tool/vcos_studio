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
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from func_module.mapping.port_mapping_core import PortMappingCore, MT_Index, FT_Index, ST_Index, TT_Index, CON_Index
from func_module.module_management.arxml_handler.system.flatextract_arxml_manager import FlatExtractArxmlManager
from func_module.health_monitor import perf_record
from ui_adaptor.data_management import get_autosar_asw_class, get_autosar_system_class

CUR_FILE_PATH = os.path.dirname(__file__)


class ServiceMappingFunc:

    def __init__(self):
        """
        数据初始化
        """
        self.clear_data()

    def __get_mapping_data_info(self):
        return [[x for x in sublist] for sublist in self.all_ports_list]

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

    @perf_record.log_function_stats(["RTE", "ServiceMapping", "手动连接"])
    def cbk_rte_right_click_connect(self, param_dict):
        """
        主界面,点击右键,连接
        """
        self.rte_window_selected_data = param_dict["row_items"]
        return self.get_first_level_dialog_data(param_dict["row_items"])

    @perf_record.log_function_stats(["RTE", "ServiceMapping", "手动断开连接"])
    def cbk_rte_right_click_disconnect(self, param_dict):
        """
        主界面,点击右键,断开连接
        """
        PortMappingCore.manual_remove_port_mapping(
            param_dict["row_items"],
            get_autosar_system_class(),
            self.all_service_ports_dict,
            self.all_ports_direction,
            self.all_ports_list,
            self.assembly_connectors,
            self.port_connections,
        )
        return PortMappingCore.get_main_table_data(param_dict, self.all_ports_list)

    @perf_record.log_function_stats(["RTE", "ServiceMapping", "完成连接"])
    def cbk_first_level_finish(self, param_dict):
        """
        主界面,点击右键,执行连接后点击finish
        """
        self.first_popups_dialog_finish(self.rte_window_selected_data.values(), param_dict["row_items"])
        return PortMappingCore.get_main_table_data(param_dict, self.all_ports_list)

    @perf_record.log_function_stats(["RTE", "ServiceMapping", "打开连接助手"])
    def cbk_rte_open_assistant(self, _):
        """
        打开mapping ui助手,显示第一个界面
        """
        return self.prepare_service_mapping_assistant_first_popups_data()

    def cbk_first_level_next(self, param_dict):
        """
        打开mapping ui助手,在第一个界面,点击next
        """
        return self.prepare_service_mapping_assistant_second_popups_data(param_dict["selected_data"])

    def cbk_second_level_next(self, param_dict):
        """
        打开mapping ui助手,在第二个界面,点击next
        """
        return self.prepare_service_mapping_assistant_third_popups_data(param_dict)

    def cbk_third_level_double_click_component(self, param_dict):
        """
        打开mapping ui助手,在第三个界面,双击component
        """
        return self.prepare_service_mapping_assistant_third_popups_double_click_component_data(param_dict["row_items"])

    def cbk_third_level_double_click_port(self, param_dict):
        """
        打开mapping ui助手,在第三个界面,双击port
        """
        return self.prepare_service_mapping_assistant_third_popups_double_click_port_data(param_dict)

    @perf_record.log_function_stats(["RTE", "ServiceMapping", "完成连接助手"])
    def cbk_third_level_finish(self, param_dict):
        """
        打开mapping ui助手,在第三个界面,点击finish
        """
        self.save_service_mapping_assistant_third_popups_table_mapping_data(param_dict["mapping_data"])
        return PortMappingCore.get_main_table_data(param_dict, self.all_ports_list)

    def cbk_third_level_component_finish(self, param_dict):
        """
        打开mapping ui助手,在第三个界面,选择component后,点击finish
        """
        self.set_service_mapping_assistant_third_popups_table_data_click_component_data_finish(param_dict)
        return None

    def cbk_third_level_port_finish(self, param_dict):
        """
        打开mapping ui助手,在第三个界面,选择port后,点击finish
        """
        self.set_service_mapping_assistant_third_popups_table_data_click_port_data_finish(param_dict)
        return None

    def cbk_get_main_table_data(self, param_dict):
        """
        获取显示于主界面的数据
        """
        return PortMappingCore.get_main_table_data(param_dict, self.all_ports_list)

    def cbk_get_all_service_component_name_to_update(self, category):
        """
        获取Component list
        """
        self.component_list = PortMappingCore.get_all_component_name_to_update(self.all_service_ports_dict, category)
        return self.component_list

    def update_service_mapping_table_after_import_asw(self):
        """
        导入asw文件夹后,先清空数据
        """
        self.clear_data()

    def update_service_mapping_table_after_load_project(self):
        """
        导入工程后,先清空数据
        """
        self.clear_data()

    def get_rte_editor_ui_service_mapping_table_data(self):
        """
        切换Tab界面后,清空并更新数据,更新界面显示
        """
        self.clear_data()
        self.update_all_ports()
        self.assembly_connectors, self.port_connections = PortMappingCore.update_all_ports_with_connector(
            {},
            {},
            self.all_service_ports_dict,
            self.all_ports_direction,
            get_autosar_system_class(),
            get_autosar_asw_class(),
            self.all_ports_list,
        )
        return self.all_ports_list

    def clear_data(self):
        """
        清空所有数据
        """
        self.component_list = []
        self.all_ports_list = []
        self.port_connections = {}
        self.ports_in_component = {}
        self.all_ports_direction = {}
        self.assembly_connectors = {}
        self.all_service_ports_dict = {}
        self.rte_window_selected_data = []

    def first_popups_dialog_finish(self, selected_row_values, selected_data_dict):
        mapping_info = {}
        avaliable_mapping_info = {}
        if not len(selected_data_dict):
            return
        row_data = list(selected_row_values)[0]
        add_port_connect_to_save = PortMappingCore.update_all_ports_with_connector(
            selected_data_dict,
            row_data,
            self.all_service_ports_dict,
            self.all_ports_direction,
            get_autosar_system_class(),
            get_autosar_asw_class(),
            self.all_ports_list,
        )
        mapping_info = PortMappingCore.get_port_mapping_info(add_port_connect_to_save, self.all_service_ports_dict)
        for connector_name in add_port_connect_to_save.keys():
            if connector_name in self.assembly_connectors:
                continue
            avaliable_mapping_info.update({connector_name: mapping_info[connector_name]})
            PortMappingCore.update_port_connection(
                connector_name,
                mapping_info[connector_name],
                self.all_service_ports_dict,
                self.all_ports_direction,
                self.assembly_connectors,
                self.port_connections,
                "add",
            )
        AutosarUtil.save_assembly_sw_connector(get_autosar_system_class()["FlatExtract"], [avaliable_mapping_info])

    def get_first_level_dialog_data(self, selected_data):
        """
        获取右键connect弹出界面中的路径
        """
        port_direction = list(selected_data.values())[0][MT_Index.Port_Direction]
        mapping_port_list = PortMappingCore.get_port_to_connect_dict(
            self.all_service_ports_dict, selected_data, port_direction
        )
        rv = list(mapping_port_list.values())
        rv.sort(key=lambda x: (-int(x[CON_Index.Compatibility]), x[CON_Index.Component]))
        return rv

    def update_all_ports(self):
        """
        获取所有的non-service类型的ports信息
        """
        if get_autosar_asw_class():
            all_service_ports_of_app_swc = PortMappingCore.get_all_app_ports_dict(get_autosar_asw_class(), "is_service")
            all_service_ports_of_service_swc = PortMappingCore.get_all_service_ports_dict(get_autosar_asw_class())
            self.all_service_ports_dict["pports"] = {
                **all_service_ports_of_app_swc["pports"],
                **all_service_ports_of_service_swc["pports"],
            }
            self.all_service_ports_dict["rports"] = {
                **all_service_ports_of_app_swc["rports"],
                **all_service_ports_of_service_swc["rports"],
            }
            self.all_ports_list, self.all_ports_direction, self.ports_in_component = (
                PortMappingCore.get_swc_all_ports_list(self.all_service_ports_dict)
            )

    def save_service_mapping_assistant_third_popups_table_mapping_data(self, mapping_data):
        mapping_info = {}
        if (
            mapping_data is None
            or len(mapping_data) == 0
            or all(data[TT_Index.Conn_Port] == "<Select port prototype...>" for data in mapping_data)
        ):
            return
        row_data = PortMappingCore.save_port_mapping_list(
            mapping_data, self.all_service_ports_dict, get_autosar_system_class()
        )
        # Part2 刷新界面显示
        if row_data:
            add_port_connect_to_save = PortMappingCore.update_all_ports_with_connector(
                {},
                row_data,
                self.all_service_ports_dict,
                self.all_ports_direction,
                get_autosar_system_class(),
                get_autosar_asw_class(),
                self.all_ports_list,
            )
            mapping_info = PortMappingCore.get_port_mapping_info(add_port_connect_to_save, self.all_service_ports_dict)
            for connector_name in add_port_connect_to_save.keys():
                if connector_name in self.assembly_connectors:
                    continue
                PortMappingCore.update_port_connection(
                    connector_name,
                    mapping_info[connector_name],
                    self.all_service_ports_dict,
                    self.all_ports_direction,
                    self.assembly_connectors,
                    self.port_connections,
                    "add",
                )

    def prepare_service_mapping_assistant_first_popups_data(self):
        rv = []
        if len(self.component_list) == 0:
            return rv
        for i in range(len(self.component_list)):
            rv.append([False, self.component_list[i], self.component_list[i]])
        rv.sort(key=lambda x: x[FT_Index.Component])
        return rv

    def prepare_service_mapping_assistant_second_popups_data(self, first_popups_table_data_list):
        selected_component_list = []
        selected_component_ports = []
        selected_component_list.extend(
            component for component in first_popups_table_data_list if component[FT_Index.Selected] == True
        )
        if not selected_component_list:
            return selected_component_ports
        for selected_component in selected_component_list:
            self.ports_in_component[selected_component[FT_Index.Component_Type]]
            for port in self.ports_in_component[selected_component[FT_Index.Component_Type]]:
                is_connected = (
                    "True"
                    if len(self.port_connections.get(port["Component"] + "_" + port["Name"], [])) > 0
                    else "False"
                )
                if [False, port["Component"], port["Name"], is_connected] in selected_component_ports:
                    continue
                selected_component_ports.append([False, port["Component"], port["Name"], is_connected])
        selected_component_ports.sort(key=lambda x: (x[ST_Index.Component], x[ST_Index.Port]))
        return selected_component_ports

    def prepare_service_mapping_assistant_third_popups_data(self, param_dict):
        rv = []
        if "FlatExtract" not in get_autosar_system_class():
            return rv
        selected_data = []
        ui_filter = param_dict["filter"]
        selected_data.extend(x for x in param_dict["selected_data"] if x[ST_Index.Selected])
        if not selected_data:
            return rv
        # mapping port
        ui_filter["selected_port_info"] = PortMappingCore.get_target_port_info(
            self.all_service_ports_dict, selected_data
        )
        rv, _ = PortMappingCore.map_port(
            self.all_service_ports_dict["pports"],
            self.all_service_ports_dict["rports"],
            FlatExtractArxmlManager.get_assembly_and_delegation_sw_connector(get_autosar_system_class()["FlatExtract"]),
            ui_filter,
        )
        return list(rv.values())

    def prepare_service_mapping_assistant_third_popups_double_click_component_data(self, row_items):
        rv = []
        selected_data = list(row_items.values())[0]
        if not selected_data:
            return rv
        if selected_data:
            rv.extend(
                [False, component]
                for component in self.component_list
                if component != selected_data[TT_Index.Component]
            )
        rv.sort(key=lambda x: x[ST_Index.Component])
        return rv

    def prepare_service_mapping_assistant_third_popups_double_click_port_data(self, param_dict):
        rv = []
        selected_data = list(param_dict["row_items"].values())
        port_to_mapping = PortMappingCore.get_target_port_info(self.all_service_ports_dict, selected_data)
        if not port_to_mapping:
            return rv
        compatibility = "0"
        port_interface_mapping = ""
        port_interface_mapping_set = ""
        connected_component_prototype = selected_data[0][TT_Index.Conn_Component]
        if connected_component_prototype not in self.ports_in_component:
            return rv
        for port in self.ports_in_component[selected_data[0][TT_Index.Conn_Component]]:
            list_add = [
                False,
                compatibility,
                port["Component"],
                port["Name"],
                port["Interface"].split("/")[-1],
                port_interface_mapping,
                port_interface_mapping_set,
            ]
            if list(port_to_mapping.values())[0]["Tag"] == "pr" and list_add not in rv:
                rv.append(list_add)
            elif list(port_to_mapping.values())[0]["Tag"] != port["Tag"] and list_add not in rv:
                rv.append(list_add)
        rv.sort(key=lambda x: x[TT_Index.Conn_Component])
        return rv

    def set_service_mapping_assistant_third_popups_table_data_click_component_data_finish(self, param_dict):
        confirmed_data_dict = param_dict["confirmed_data_dict"]
        row_items = param_dict["row_items"]
        component_row_items = param_dict["component_row_items"]
        for row_key, row_value in row_items.items():
            index = 0
            for selected_component in component_row_items:
                if index == 0:
                    confirmed_data_dict[row_key + index] = row_value.copy()
                    confirmed_data_dict[row_key + index][TT_Index.Conn_Component] = selected_component[
                        "Component Prototype"
                    ]
                    confirmed_data_dict[row_key + index][TT_Index.Conn_Port] = "<Select port prototype...>"
                    confirmed_data_dict[row_key + index][TT_Index.Conn_Port_Interface] = ""
                else:
                    confirmed_data_dict.insert(row_key + index, row_value.copy())
                    confirmed_data_dict[row_key + index][TT_Index.Conn_Component] = selected_component[
                        "Component Prototype"
                    ]
                    confirmed_data_dict[row_key + index][TT_Index.Conn_Port] = "<Select port prototype...>"
                    confirmed_data_dict[row_key + index][TT_Index.Conn_Port_Interface] = ""
                index += 1

    def set_service_mapping_assistant_third_popups_table_data_click_port_data_finish(self, param_dict):
        confirmed_data_dict = param_dict["confirmed_data_dict"]
        row_items = param_dict["row_items"]
        port_row_items = param_dict["port_row_items"]
        for row_key, row_value in row_items.items():
            index = 0
            for selected_port in port_row_items:
                if index == 0:
                    confirmed_data_dict[row_key + index] = row_value.copy()
                    confirmed_data_dict[row_key + index][TT_Index.Conn_Port] = selected_port["Port Prototype"]
                    confirmed_data_dict[row_key + index][TT_Index.Conn_Port_Interface] = selected_port["Port Interface"]
                else:
                    confirmed_data_dict.insert(row_key + index, row_value.copy())
                    confirmed_data_dict[row_key + index][TT_Index.Conn_Port] = selected_port["Port Prototype"]
                    confirmed_data_dict[row_key + index][TT_Index.Conn_Port_Interface] = selected_port["Port Interface"]
                index += 1
