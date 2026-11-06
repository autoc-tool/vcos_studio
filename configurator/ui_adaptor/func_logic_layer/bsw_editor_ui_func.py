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
import logging
import threading
import subprocess
import xml.dom.minidom
from typing import Union
from datetime import datetime
from PySide6.QtGui import QUndoStack
from ui_adaptor.data_management import (
    get_autosar_bsw_class,
    get_autosar_bswmd_class,
    get_autosar_asw_class,
    get_autosar_system_class,
    get_autosar_ib_class,
    get_sys_info_class,
    get_component_arxml_path_dict,
    get_module_stack_dict,
    get_secondary_cfg_dict,
    get_module_container_pre_cfg_dict,
    data_management,
)
from func_module.module_management.bsw_editor.bsw_editor import BswEditor
from cfg_gui.widgets.undo_command import (
    BSWInputUndoCommand,
    BSWQReferenceUndoCommand,
    BSWQStringCommand,
    BSWContainerUndoCommand,
    BSWOutlineUndoCommand,
)
from func_module.health_monitor.logger import logger
from func_module.mapping.schedule_table_mapping import ScheduleTableManager
from func_module.health_monitor.perf_record import log_function_stats
from func_module.module_management.linkage.linkage_func import SetMethod
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlSaveHandler

CUR_FILE_PATH = os.path.dirname(os.path.realpath(__file__))


class BswEditorUIFunc:

    def __init__(self):
        self.lock = threading.Lock()
        self.init_flag = True
        self._jitter_opt_history = []
        self._schedule_table_ui_cache = {}

    @property
    def jitter_opt_history(self):
        if not self._jitter_opt_history and self.init_flag:
            self.init_flag = False
            self._jitter_opt_history = BswEditor.load_jitter_opt_history(
                data_management.sys_info_class.config_base_path
            )
        return self._jitter_opt_history

    @jitter_opt_history.setter
    def jitter_opt_history(self, value):
        self._jitter_opt_history = value

    def clear_jitter_opt_history(self, init_flag=False):
        self.init_flag = init_flag
        self._jitter_opt_history = []

    @property
    def schedule_table_ui_cache(self):
        if not self._schedule_table_ui_cache:
            self._schedule_table_ui_cache = ScheduleTableManager.load_sch_tbl_ui_cfg(
                data_management.sys_info_class.config_base_path
            )
        return self._schedule_table_ui_cache

    def clear_schedule_table_ui_cache(self):
        self._schedule_table_ui_cache = {}

    def bsw_editor_get_the_show_data_of_the_container(self, container_path_of_ecuc_arxml):

        self.bsw_ecuc_dict = get_autosar_bsw_class()
        self.bsw_mod_dict = get_autosar_bswmd_class()

        instance_name = container_path_of_ecuc_arxml.split("/")[2]
        container_cfg_obj = self.bsw_ecuc_dict[instance_name].find(container_path_of_ecuc_arxml)
        if container_cfg_obj is None:
            show_data = None
        else:
            module_value = container_cfg_obj.find_nodes("ECUC-MODULE-CONFIGURATION-VALUES")[-1]
            module_name = getattr(getattr(module_value, "DEFINITION_REF", ""), "valueOf_", "").split("/")[-1]
            container_definition_obj = BswEditor.get_container_definiton_obj(
                module_name, container_cfg_obj, self.bsw_mod_dict
            )
            show_data = BswEditor.get_show_data(instance_name, module_name, container_cfg_obj, container_definition_obj)
        return show_data

    def sec_bsw_editor_get_the_show_data_of_the_container(self, container_path_of_ecuc_arxml):

        self.bsw_ecuc_dict = get_autosar_bsw_class()
        self.bsw_mod_dict = get_autosar_bswmd_class()

        instance_name = container_path_of_ecuc_arxml.split("/")[2]
        container_cfg_obj = self.bsw_ecuc_dict[instance_name].find(container_path_of_ecuc_arxml)
        if container_cfg_obj is None:
            show_data = None
        else:
            module_value = container_cfg_obj.find_nodes("ECUC-MODULE-CONFIGURATION-VALUES")[-1]
            module_name = getattr(getattr(module_value, "DEFINITION_REF", ""), "valueOf_", "").split("/")[-1]
            container_definition_obj = BswEditor.get_container_definiton_obj(
                module_name, container_cfg_obj, self.bsw_mod_dict
            )
            show_data = BswEditor.get_show_data_action(
                instance_name, module_name, container_cfg_obj, container_definition_obj
            )

        return show_data

    def sec_get_bswm_mod_and_ecuc_obj(self, selected_item_path):

        self.bsw_ecuc_dict = get_autosar_bsw_class()
        self.bsw_mod_dict = get_autosar_bswmd_class()

        return BswEditor.sec_get_bswm_mod_and_ecuc_obj(selected_item_path, self.bsw_ecuc_dict, self.bsw_mod_dict)

    def bsw_editor_get_the_show_data_of_the_item(
        self, container_path_of_ecuc_arxml, item_path_of_mod_arxml, item_is_shortname
    ):
        """
        获取container中单个配置项的show_data,shortname类型的配置项需要特殊处理
        container_path_of_ecuc_arxml:container的ecuc路径
        item_path_of_mod_arxml:配置项的mod路径
        item_is_shortname:配置项是否为shortname类型
        """
        container_show_data = self.bsw_editor_get_the_show_data_of_the_container(container_path_of_ecuc_arxml)
        if item_is_shortname is True:
            item_path_of_mod_arxml = container_path_of_ecuc_arxml
        if item_path_of_mod_arxml not in container_show_data:
            return None
        return container_show_data[item_path_of_mod_arxml][0]

    def bsw_editor_get_all_internal_ref_targets_from_ecuc_arxml(self, mod_path, module_name):
        self.bsw_ecuc_dict = get_autosar_bsw_class()
        self.bsw_mod_dict = get_autosar_bswmd_class()

        return BswEditor.get_all_internal_ref_targets(mod_path, module_name, self.bsw_ecuc_dict, self.bsw_mod_dict)

    def bsw_editor_get_all_foreign_ref_targets_from_foreign_arxml(self, mod_path, module_name):
        bsw_mod_dict = get_autosar_bswmd_class()
        bsw_ecuc_dict = get_autosar_bsw_class()
        autosar_asw_class = get_autosar_asw_class()
        autosar_system_class = get_autosar_system_class()
        autosar_ib_class = get_autosar_ib_class()

        return BswEditor.get_all_foreign_ref_targets(
            mod_path,
            module_name,
            bsw_mod_dict,
            bsw_ecuc_dict,
            autosar_asw_class,
            autosar_system_class,
            autosar_ib_class,
        )

    def bsw_editor_editing_finished_and_write_to_ecuc_arxml(
        self, new_value, per_name, mod_path, module, ecuc_path, tag, index=None
    ):
        bsw_ecuc_dict = get_autosar_bsw_class()

        BswEditor.set_new_value_to_ecuc_arxml(
            bsw_ecuc_dict, new_value, per_name, mod_path, module, ecuc_path, tag, index
        )

        return bsw_ecuc_dict

    def update_module_container_pre_cfg(self, show_data_dict):
        """保存container下配置的进制信息保存进全局变量，下次加载时恢复"""

        def add_key_value_pair(module_container_dict, keys, value):
            # 递归遍历字典往全局变量中添加键值对
            cur_key = keys[0]
            if len(keys) == 1:
                module_container_dict.update({cur_key: value})
            else:
                if cur_key not in module_container_dict:
                    module_container_dict.update({cur_key: {}})
                add_key_value_pair(module_container_dict[cur_key], keys[1:], value)

        # 获取保存进制信息的全局变量
        module_container_dict = get_module_container_pre_cfg_dict()
        module = show_data_dict.get("module", "")
        ecuc_path = show_data_dict.get("ecuc_path", "")
        label_name = show_data_dict.get("label_name", "")
        num_format = show_data_dict.get("num_format", "")
        keys = [module, ecuc_path, label_name]

        # 全局变量中更新进制信息
        add_key_value_pair(module_container_dict, keys, num_format)
        return show_data_dict

    def get_module_container_pre_cfg(self):
        cfg_dict = get_module_container_pre_cfg_dict()
        return cfg_dict

    def update_container_short_name_to_ecuc_arxml(self, new_value, per_name, mod_path, module, ecuc_path, tag):
        bsw_ecuc_dict = get_autosar_bsw_class()

        final_short_name = BswEditor.update_container_short_name_to_ecuc_arxml(
            bsw_ecuc_dict, new_value, per_name, mod_path, module, ecuc_path, tag
        )

        return final_short_name, bsw_ecuc_dict

    def bsw_editor_update_all_configuration_items_that_reference_this_ref(
        self, new_value, per_name, mod_path, module, ecuc_path, tag
    ):
        bsw_ecuc_dict = get_autosar_bsw_class()
        old_ref_target = ecuc_path
        new_ref_target = ecuc_path.split(per_name)[0] + new_value
        BswEditor.update_all_configuration_items_that_reference_this_ref_to_ecuc_arxml(
            bsw_ecuc_dict, new_ref_target, old_ref_target, mod_path, module, ecuc_path, tag
        )

    def bsw_editor_add_param_item_and_write_to_ecuc_arxml(
        self, new_value, mod_path, module_name, ecuc_path, tag, index=None, instance_name=None
    ):
        bsw_ecuc_dict = get_autosar_bsw_class()
        bsw_mod_dict = get_autosar_bswmd_class()
        instance_name = instance_name or module_name
        BswEditor.add_param_item_and_write_to_ecuc_arxml(
            bsw_ecuc_dict, bsw_mod_dict, new_value, mod_path, module_name, ecuc_path, tag, index, instance_name
        )
        return bsw_ecuc_dict

    def bsw_editor_remove_param_item_and_write_to_ecuc_arxml(
        self, new_value, mod_path, module, ecuc_path, tag, index=None
    ):
        bsw_ecuc_dict = get_autosar_bsw_class()
        bsw_mod_dict = get_autosar_bswmd_class()

        BswEditor.remove_param_item_and_write_to_ecuc_arxml(
            bsw_ecuc_dict, bsw_mod_dict, new_value, mod_path, module, ecuc_path, tag, index
        )
        return bsw_ecuc_dict

    def bsw_editor_set_user_defined(self, per_name, mod_path, module, ecuc_path, tag):

        bsw_ecuc_dict = get_autosar_bsw_class()

        return BswEditor.set_user_defined(bsw_ecuc_dict, per_name, mod_path, module, ecuc_path, tag)

    def bsw_editor_remove_user_defined(self, per_name, mod_path, module, ecuc_path, tag):

        bsw_ecuc_dict = get_autosar_bsw_class()

        return BswEditor.remove_user_defined(bsw_ecuc_dict, per_name, mod_path, module, ecuc_path, tag)

    def bsw_editor_set_is_lock(self, per_name, mod_path, module, ecuc_path, tag):
        bsw_ecuc_dict = get_autosar_bsw_class()
        return BswEditor.set_is_lock(bsw_ecuc_dict, per_name, mod_path, module, ecuc_path, tag)

    def bsw_editor_remove_is_lock(self, per_name, mod_path, module, ecuc_path, tag):
        bsw_ecuc_dict = get_autosar_bsw_class()
        return BswEditor.remove_is_lock(bsw_ecuc_dict, per_name, mod_path, module, ecuc_path, tag)

    def bsw_editor_get_admin_data(self, module, mod_path):
        bswmd_dict = get_autosar_bswmd_class()
        bswmd_obj = bswmd_dict[module].find(mod_path)
        return BswEditor.get_admin_data(bswmd_obj)

    def bsw_editor_set_integer_format(self, module, mod_path, ecuc_path, cfg_value, tag, num_format):

        bsw_ecuc_dict = get_autosar_bsw_class()

        return BswEditor.set_integer_format(bsw_ecuc_dict, module, mod_path, ecuc_path, cfg_value, tag, num_format)

    def bsw_editor_all_ref_configuration_items_by_ref_target(self, ref_target):

        bsw_ecuc_dict = get_autosar_bsw_class()

        return BswEditor.get_all_ref_configuration_items_by_ref_target(bsw_ecuc_dict, ref_target)

    def bsw_editor_update_bsw_module_data(self, module_list, progress_signal=None):
        with self.lock:
            bsw_ecuc_dict = get_autosar_bsw_class()
            bsw_mod_dict = get_autosar_bswmd_class()
            for module_name in module_list:
                BswEditor.bsw_editor_update_bsw_module_data(bsw_ecuc_dict, bsw_mod_dict, module_name)
        return module_list

    def bsw_editor_update_modules(self, module_name_set, progress_signal):
        with self.lock:
            for module_name in module_name_set:
                progress_signal.emit(f"Updating {module_name} UI")
                bsw_ecuc_dict = get_autosar_bsw_class()
                bsw_mod_dict = get_autosar_bswmd_class()
                BswEditor.bsw_editor_update_bsw_module_data(bsw_ecuc_dict, bsw_mod_dict, module_name)

        tmp_path = os.path.abspath(os.path.join(data_management.sys_info_class.config_base_path, "..", ".config"))
        ArxmlSaveHandler.save_system_dir_arxml(data_management.autosar_system_class, tmp_path)
        return sorted(module_name_set)

    def get_all_element_items(self, filter_text):

        bsw_ecuc_dict = get_autosar_bsw_class()
        autosar_asw_class = get_autosar_asw_class()
        rv = BswEditor.bsw_editor_get_all_element_items(
            bsw_ecuc_dict, filter_text
        ) + BswEditor.bsw_editor_get_all_element_items_from_asw(autosar_asw_class, filter_text)
        return rv

    @log_function_stats(["BSW Editor", "全局搜索BSW配置项", "打开并跳转到配置项所在arxml文件行"])
    def open_arxml_file(self, element_string: str, type_string: str, editor_type: str) -> Union[int, str]:
        # arxml文件路径
        arxml_file_path = self.find_arxml_file_path(element_string, type_string)
        if arxml_file_path == "":
            return "Path of the arxml file is not found."

        # 定位到行数
        line_idx = self.find_arxml_file_line(arxml_file_path, element_string, type_string)
        if line_idx == -1:
            return "Target not found in the arxml file."

        # 跳转
        if editor_type == "vscode":
            # vscode编辑器打开并跳转
            command = "code --goto {}:{} ".format(arxml_file_path, line_idx)
            subprocess.call(command, shell=True)
        else:
            return "Selected editor is not supported now."

        return 0

    def find_arxml_file_path(self, element_string: str, type_string: str) -> str:
        arxml_file_path = ""
        # BSW目录
        if type_string in ["Parameter", "Container"]:
            sys_info_class = get_sys_info_class()
            module_name = element_string.split("/")[2]
            if module_name not in sys_info_class.bsw_cfg:
                module_name = module_name.lower()

            if module_name in sys_info_class.bsw_cfg:
                arxml_file_path = sys_info_class.bsw_cfg[module_name]
            else:
                arxml_file_path = os.path.join(
                    sys_info_class.config_base_path, "bsw", module_name, module_name + "_ecuc.arxml"
                )
        # ASW目录下的component和<PORTS>
        elif type_string in ["component", "pport", "rport"]:
            component_arxml_path_dict = get_component_arxml_path_dict()
            if type_string == "component":
                key_name = element_string.split("/")[-1]
            else:
                key_name = element_string.split("/")[-2]

            if key_name in component_arxml_path_dict["asw_component"]:
                arxml_file_path = component_arxml_path_dict["asw_component"][key_name]
        # ASW目录下的<INTERNAL-BEHAVIORS>
        elif type_string in [
            "swc_internal_behavior",
            "operation_invoked_event",
            "asynchronous_server_call_returns_event",
            "init_event",
            "background_event",
            "data_received_event",
            "swc_mode_switch_event",
            "timing_event",
            "data_send_completed_event",
            "data_write_completed_event",
            "runnable_entity",
            "variable_access",
            "runnables",
        ]:
            component_arxml_path_dict = get_component_arxml_path_dict()
            key_name = element_string.split("/")[2]
            if key_name in component_arxml_path_dict["asw_component"]:
                arxml_file_path = component_arxml_path_dict["asw_component"][key_name]
            else:
                key_name = element_string.split("/")[4]
                arxml_file_path = component_arxml_path_dict["asw_component"][key_name]

        return arxml_file_path

    def find_arxml_file_line(self, arxml_file_path: str, element_string: str, type_string: str) -> int:  # noqa: C901
        with open(arxml_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            content = "".join(lines)
        dom = xml.dom.minidom.parseString(content)
        support_component_type = [
            "APPLICATION-SW-COMPONENT-TYPE",
            "ECU-ABSTRACTION-SW-COMPONENT-TYPE",
            "COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE",
            "SERVICE-SW-COMPONENT-TYPE",
        ]

        # 获取目标文本
        target_string = ""
        if type_string == "Container":
            container_name = element_string.split("/")[-1]
            container_node_list = dom.getElementsByTagName("ECUC-CONTAINER-VALUE")
            for container_node in container_node_list:
                # container的shor-name只有一个
                container_short_name_node = container_node.getElementsByTagName("SHORT-NAME")[0]
                container_short_name_value = container_short_name_node.firstChild.data
                if container_short_name_value == container_name:
                    target_string = container_short_name_node.toxml()
                    break
        elif type_string == "Parameter":
            parameter_name = element_string.split("/")[-1]
            container_name = element_string.split("/")[-2]
            container_node_list = dom.getElementsByTagName("ECUC-CONTAINER-VALUE")
            for container_node in container_node_list:
                container_short_name_node = container_node.getElementsByTagName("SHORT-NAME")[0]
                container_short_name_value = container_short_name_node.firstChild.data
                if container_short_name_value == container_name:
                    # 获取当前节点下的所有PARAMETER-VALUES节点
                    parameter_node_list = container_node.getElementsByTagName("PARAMETER-VALUES")
                    for parameter_node in parameter_node_list:
                        # 获取PARAMETER-VALUES节点下的所有DEFINITION-REF节点
                        parameter_ref_elements = parameter_node.getElementsByTagName("DEFINITION-REF")
                        # 遍历每个PARAMETER-VALUES节点下的DEFINITION-REF节点并获取文本
                        for ref_element in parameter_ref_elements:
                            # a = ref_element.firstChild.nodeValue
                            if parameter_name == str(ref_element.firstChild.nodeValue).split("/")[-1]:
                                target_string = ref_element.firstChild.toxml()
                                break
                        if target_string:
                            break

                    reference_node_list = container_node.getElementsByTagName("REFERENCE-VALUES")
                    for reference_node in reference_node_list:
                        reference_ref_elements = reference_node.getElementsByTagName("DEFINITION-REF")
                        for ref_element in reference_ref_elements:
                            if parameter_name == str(ref_element.firstChild.nodeValue).split("/")[-1]:
                                target_string = ref_element.firstChild.toxml()
                                break
                        if target_string:
                            break
                    break
        elif type_string == "component":
            component_name = element_string.split("/")[-1]
            component_node_list = []
            for component_type in support_component_type:
                component_node_list += dom.getElementsByTagName(component_type)
            for component_node in component_node_list:
                component_short_name_node = component_node.getElementsByTagName("SHORT-NAME")[0]
                component_short_name_value = component_short_name_node.firstChild.data
                if component_short_name_value == component_name:
                    target_string = component_short_name_node.toxml()
                    break
        elif type_string == "pport":
            component_name = element_string.split("/")[-2]
            pport_name = element_string.split("/")[-1]
            component_node_list = []
            for component_type in support_component_type:
                component_node_list += dom.getElementsByTagName(component_type)
            for component_node in component_node_list:
                component_short_name_node = component_node.getElementsByTagName("SHORT-NAME")[0]
                component_short_name_value = component_short_name_node.firstChild.data
                if component_short_name_value == component_name:
                    pport_node_list = component_node.getElementsByTagName("P-PORT-PROTOTYPE")
                    for pport_node in pport_node_list:
                        pport_shor_name_node = pport_node.getElementsByTagName("SHORT-NAME")[0]
                        pport_shor_name_value = pport_shor_name_node.firstChild.data
                        if pport_name == pport_shor_name_value:
                            target_string = pport_shor_name_node.toxml()
                            break
                    break
        elif type_string == "rport":
            component_name = element_string.split("/")[-2]
            rport_name = element_string.split("/")[-1]
            component_node_list = []
            for component_type in support_component_type:
                component_node_list += dom.getElementsByTagName(component_type)
            for component_node in component_node_list:
                component_short_name_node = component_node.getElementsByTagName("SHORT-NAME")[0]
                component_short_name_value = component_short_name_node.firstChild.data
                if component_short_name_value == component_name:
                    rport_node_list = component_node.getElementsByTagName("R-PORT-PROTOTYPE")
                    for rport_node in rport_node_list:
                        rport_shor_name_node = rport_node.getElementsByTagName("SHORT-NAME")[0]
                        rport_shor_name_value = rport_shor_name_node.firstChild.data
                        if rport_name == rport_shor_name_value:
                            target_string = rport_shor_name_node.toxml()
                            break
                    break
        elif type_string in [
            "swc_internal_behavior",
            "operation_invoked_event",
            "asynchronous_server_call_returns_event",
            "init_event",
            "background_event",
            "data_received_event",
            "swc_mode_switch_event",
            "timing_event",
            "data_send_completed_event",
            "data_write_completed_event",
            "runnable_entity",
            "variable_access",
        ]:
            name = element_string.split("/")[-1]
            tag_name = type_string.upper().replace("_", "-")
            node_list = dom.getElementsByTagName(tag_name)
            for node in node_list:
                short_name_node = node.getElementsByTagName("SHORT-NAME")[0]
                short_name_value = short_name_node.firstChild.data
                if short_name_value == name:
                    target_string = short_name_node.toxml()
                    break
        # runnables就是swc_internal_behavior
        elif type_string == "runnables":
            swc_internal_behavior_name = element_string.split("/")[-1]
            swc_internal_behavior_node_list = dom.getElementsByTagName("SWC-INTERNAL-BEHAVIOR")
            for swc_internal_behavior_node in swc_internal_behavior_node_list:
                swc_internal_behavior_short_name_node = swc_internal_behavior_node.getElementsByTagName("SHORT-NAME")[0]
                swc_internal_behavior_short_name_value = swc_internal_behavior_short_name_node.firstChild.data
                if swc_internal_behavior_short_name_value == swc_internal_behavior_name:
                    target_string = swc_internal_behavior_short_name_node.toxml()
                    break

        # 遍历找出目标文本所在行数
        line_idx: int = -1
        if target_string == "":
            return line_idx
        for idx, line in enumerate(lines):
            if target_string in line:
                line_idx = idx + 1
                break
        return line_idx

    def get_ecuc_path_of_action_item(self, mod_path, container_ecuc_path, linked_mod_path, action_item):
        """
        获取被联动配置项所属container的ecuc路径
        mod_path:入口配置项mod路径
        container_ecuc_path:入口配置项所在container的ecuc路径
        linked_mod_path:被联动配置项的mod路径
        action_item:被联动配置项的动作内容
        """
        # ShortName配置项的mod路径与container的mod路径一致,将"/ShortName"去掉
        if mod_path.split("/")[-1] == "ShortName":
            mod_path = mod_path[: mod_path.rfind("/")]
        # 被联动的配置项是否为shortname
        linked_shortname_flag = False
        if linked_mod_path.split("/")[-1] == "ShortName":
            linked_mod_path = linked_mod_path[: linked_mod_path.rfind("/")]
            linked_shortname_flag = True

        linked_module_name: str = linked_mod_path.split("/")[3]  # 被联动配置项的所属模块名
        linked_container_ecuc_path_list: list = []
        # 1.不跨container
        if mod_path.split("/")[:-1] == linked_mod_path.split("/")[:-1]:
            linked_container_ecuc_path_list.append(container_ecuc_path)
        # 2.跨container
        else:
            bsw_ecuc_dict = get_autosar_bsw_class()
            if linked_module_name not in bsw_ecuc_dict:
                return linked_container_ecuc_path_list, linked_mod_path, linked_shortname_flag
            # 2.1.获取ref配置项向上两级父container的ecuc内容
            if "ref_judge_item" not in action_item:
                logger.error('ERROR: the action of "linked_mod_path" does not have key "ref_judge_item".')
                return linked_container_ecuc_path_list, linked_mod_path, linked_shortname_flag
            ref_mod_path = action_item["ref_judge_item"]
            # 获取mod路径对应的所有container路径
            if ref_mod_path is None:
                linked_container_mod_path = "/".join(linked_mod_path.split("/")[:-1])
                linked_parent_container_ecuc_path = "/ActiveEcuC/" + "/".join(linked_mod_path.split("/")[3:-2])
                linked_parent_container_ecuc_obj = bsw_ecuc_dict[linked_module_name].find(
                    linked_parent_container_ecuc_path
                )
                for linked_container_ecuc_obj in linked_parent_container_ecuc_obj.CONTAINERS.ECUC_CONTAINER_VALUE:
                    if linked_container_ecuc_obj.DEFINITION_REF.valueOf_ == linked_container_mod_path:
                        linked_container_ecuc_path_list.append(linked_container_ecuc_obj.get_path())
            # 获取有ref关系的container路径
            else:
                ref_parent_parent_container_ecuc_path = "/ActiveEcuC/" + "/".join(ref_mod_path.split("/")[3:-2])
                ref_parent_parent_container_ecuc_obj = bsw_ecuc_dict[linked_module_name].find(
                    ref_parent_parent_container_ecuc_path
                )
                # 2.2.遍历ref配置项向上一级父container里的ref数值,找出与入口配置项匹配的
                for (
                    ref_parent_container_ecuc_obj
                ) in ref_parent_parent_container_ecuc_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                    ref_parent_container_ecuc_path = ref_parent_container_ecuc_obj.get_path()
                    ref_show_data_dict = self.bsw_editor_get_the_show_data_of_the_item(
                        ref_parent_container_ecuc_path, ref_mod_path, False
                    )
                    if ref_show_data_dict is None:
                        continue
                    if ref_show_data_dict["cfg_value"] == container_ecuc_path:
                        linked_container_ecuc_path_list.append(ref_parent_container_ecuc_path)
        return linked_container_ecuc_path_list, linked_mod_path, linked_shortname_flag

    def bsw_editor_update_linked_cfg_item(  # noqa: C901
        self,
        module_name,
        mod_path,
        container_ecuc_path,
        data,
        updated_path_dict,
        basic_ui_handler,
        callback,
        main_window,
    ):
        """
        修改被联动配置项
        module_name:入口配置项模块
        mod_path:入口配置项mod路径
        container_ecuc_path:入口配置项所属container的ecuc路径
        data:入口配置项数据值
        updated_path_dict:联动链上的配置项路径,防止回环,{container ecuc path: [配置项 mod path]}
        basic_ui_handler:中间件UI处理机制
        callback:中间件回调机制
        main_window:主窗口
        """
        # 1.获取配置项当前数据对应的联动行为
        linkage_cfg_dict: dict = data_management.sys_info_class.linkage_cfg_dict
        if isinstance(linkage_cfg_dict, dict) is False:
            return
        if module_name not in linkage_cfg_dict:
            return
        cfg_list: list = linkage_cfg_dict[module_name].get(mod_path, None)
        if cfg_list is None:
            return
        if isinstance(cfg_list, list) is False:
            return
        action_dict: dict = None
        try:
            # 1.1.获取指定数据对应的联动行为
            for item_linkage_dict in cfg_list:
                if data in item_linkage_dict["value"]:
                    action_dict = item_linkage_dict["action"]
                    break
            # 1.2.获取一般数据对应的联动行为
            if action_dict is None:
                for item_linkage_dict in cfg_list:
                    if None in item_linkage_dict["value"]:
                        action_dict = item_linkage_dict["action"]
                        break
            # 1.3.如果没有对应的联动行为,直接返回
            if action_dict is None:
                return
        except Exception:
            logger.error(f'ERROR:the linkage rule of "{module_name}":"{mod_path}" in linkage_cfg.json is invalid.')
            return

        # 2.获取信息列表
        instance_info_list: list = []  # 被联动的ui配置项信息列表
        arxml_info_list: list = []  # 被联动的arxml配置项信息列表
        for linked_mod_path, action_item in action_dict.items():
            linked_mod_path_list = [linked_mod_path]
            if "other_linked_mod_path" in action_item and isinstance(action_item["other_linked_mod_path"], list):
                linked_mod_path_list = linked_mod_path_list + action_item["other_linked_mod_path"]
            for linked_mod_path in linked_mod_path_list:
                # 2.1.非arxml修改
                if ("is_arxml" not in action_item) or (action_item["is_arxml"] is False):
                    linked_container_ecuc_path_list, linked_mod_path, linked_shortname_flag = (
                        self.get_ecuc_path_of_action_item(mod_path, container_ecuc_path, linked_mod_path, action_item)
                    )
                    for linked_container_ecuc_path in linked_container_ecuc_path_list:
                        # 2.1.1.利用被联动配置项的路径信息,避免回环
                        if (linked_container_ecuc_path in updated_path_dict) and (
                            linked_mod_path in updated_path_dict[linked_container_ecuc_path]
                        ):
                            continue
                        # 2.1.2.获取被联动配置项的内存
                        linked_show_data_dict = self.bsw_editor_get_the_show_data_of_the_item(
                            linked_container_ecuc_path, linked_mod_path, linked_shortname_flag
                        )
                        if linked_show_data_dict is None:
                            continue
                        # 2.1.3.获取被联动配置项将要修改的数据
                        is_locked: bool = action_item["is_locked"] if "is_locked" in action_item else None
                        if "set_method" not in action_item:
                            logger.error(f'ERROR: "{mod_path}":"{linked_mod_path}" dose not have "set_method".')
                            continue
                        set_method_func = SetMethod.get_method(module_name, action_item["set_method"])
                        if set_method_func is None:
                            logger.error(f"ERROR: set_method {action_item['set_method']} is invalid.")
                            continue
                        method_parameter = (
                            action_item["method_parameter"] if "method_parameter" in action_item else None
                        )
                        mapped_data, mapped_locked = set_method_func(
                            data, linked_show_data_dict, data_management, self, method_parameter
                        )
                        is_locked = mapped_locked if mapped_locked is not None else is_locked
                        # 2.1.4.判断是否要修改,更新信息列表
                        if (linked_show_data_dict["cfg_value"] != mapped_data) or (is_locked is not None):
                            instance_info_list.append(
                                [
                                    {linked_mod_path: [linked_show_data_dict]},
                                    linked_mod_path,
                                    mapped_data,
                                    module_name,
                                    is_locked,
                                ]
                            )
                            if linked_container_ecuc_path not in updated_path_dict:
                                updated_path_dict[linked_container_ecuc_path] = [linked_mod_path]
                            else:
                                updated_path_dict[linked_container_ecuc_path].append(linked_mod_path)
                        # 2.1.5.是否存放被联动配置项的旧值
                        if ("store_old_data" in action_item) and (action_item["store_old_data"] is True):
                            self.modify_old_data_record(data_management, linked_show_data_dict)
                # 2.2.arxml修改
                else:
                    arxml_info_list.append([container_ecuc_path, linked_mod_path, action_item["set_method"]])
        # 3.修改ui配置项
        basic_ui_handler.update_linked_cfg_item(instance_info_list, updated_path_dict, callback, main_window)
        # 4.修改arxml配置项
        basic_ui_handler.update_linked_arxml_item(module_name, arxml_info_list, data_management)

    def modify_old_data_record(self, data_management, linked_show_data_dict):
        """记录被联动配置项的旧值"""
        if hasattr(data_management, "old_data_dict") is False:
            data_management.old_data_dict = {}
        data_management.old_data_dict[linked_show_data_dict["ecuc_path"] + linked_show_data_dict["mod_path"]] = (
            linked_show_data_dict["cfg_value"]
        )

    def bsw_editor_input_push_stack(
        self,
        old_data,
        new_data,
        module_name,
        show_data_dict,
        callback,
        overview_ui,
        basic_ui_handler,
        instance_type,
        linked_flag,
        modify_lock_flag,
        is_lock,
    ):
        if overview_ui is None:
            logging.info("ERROR: overview_ui can not be None,please check your code.")
            return

        module_stack_dict: dict = get_module_stack_dict()
        if module_name not in module_stack_dict:
            module_stack_dict[module_name] = QUndoStack()
            module_stack_dict[module_name].setUndoLimit(50)
        module_stack_dict[module_name].push(
            BSWInputUndoCommand(
                old_data,
                new_data,
                show_data_dict,
                callback,
                overview_ui,
                basic_ui_handler,
                instance_type,
                linked_flag,
                modify_lock_flag,
                is_lock,
            )
        )

    def bsw_editor_qreference_push_stack(
        self,
        item_index: int,
        list_count: int,
        item_text: str,
        operation: str,
        show_data_dict,
        callback,
        overview_ui,
        basic_ui_handler,
    ):
        if overview_ui is None:
            logging.info("ERROR: overview_ui can not be None,please check your code.")
            return

        module_name: str = show_data_dict["module"]
        module_stack_dict: dict = get_module_stack_dict()
        if module_name not in module_stack_dict:
            module_stack_dict[module_name] = QUndoStack()
            module_stack_dict[module_name].setUndoLimit(50)
        module_stack_dict[module_name].push(
            BSWQReferenceUndoCommand(
                item_index, list_count, item_text, operation, show_data_dict, callback, overview_ui, basic_ui_handler
            )
        )

    def bsw_editor_qstring_push_stack(
        self,
        item_index: int,
        list_count: int,
        item_text: str,
        operation: str,
        show_data_dict,
        callback,
        overview_ui,
        basic_ui_handler,
    ):
        if overview_ui is None:
            logging.info("ERROR: overview_ui can not be None,please check your code.")
            return

        module_name: str = show_data_dict["module"]
        module_stack_dict: dict = get_module_stack_dict()
        if module_name not in module_stack_dict:
            module_stack_dict[module_name] = QUndoStack()
            module_stack_dict[module_name].setUndoLimit(50)
        module_stack_dict[module_name].push(
            BSWQStringCommand(
                item_index, list_count, item_text, operation, show_data_dict, callback, overview_ui, basic_ui_handler
            )
        )

    def bsw_editor_container_outline_push_stack(
        self, operation, data, instance, show_data_dict, callback, overview_ui, basic_ui_handler
    ):
        if overview_ui is None:
            logging.info("ERROR: overview_ui can not be None,please check your code.")
            return

        module_name: str = overview_ui.cur_tab_name
        module_stack_dict: dict = get_module_stack_dict()
        if module_name not in module_stack_dict:
            module_stack_dict[module_name] = QUndoStack()
            module_stack_dict[module_name].setUndoLimit(50)
        module_stack_dict[module_name].push(
            BSWOutlineUndoCommand(operation, data, instance, show_data_dict, callback, overview_ui, basic_ui_handler)
        )

    def bsw_editor_container_push_stack(
        self, data, item_path, item_row, operation: str, callback, overview_ui, main_window=None
    ):
        if overview_ui is None:
            logging.info("ERROR: overview_ui can not be None,please check your code.")
            return

        module_name: str = overview_ui.cur_tab_name
        module_stack_dict: dict = get_module_stack_dict()
        if module_name not in module_stack_dict:
            module_stack_dict[module_name] = QUndoStack()
            module_stack_dict[module_name].setUndoLimit(50)
        module_stack_dict[module_name].push(
            BSWContainerUndoCommand(
                module_name, data, item_path, item_row, operation, callback, overview_ui, main_window
            )
        )

    def bsw_editor_undo(self, module_name):
        if module_name == "Overview":
            logging.info("Warning: Overview can not undo.")
            return

        module_stack_dict: dict = get_module_stack_dict()
        if module_name not in module_stack_dict:
            logging.info(f"ERROR: {module_name}'s stack is None.")
            return

        # 撤销
        undo_stack = module_stack_dict[module_name]
        if undo_stack.canUndo() is False:
            logging.info(f"{module_name}'s stack can't Undo.")
            return

        undo_stack.undo()
        while (undo_stack.canUndo() is True) and (undo_stack.command(undo_stack.index() - 1).linked_flag is True):
            undo_stack.undo()

    def bsw_editor_redo(self, module_name):
        if module_name == "Overview":
            logging.info("Warning: Overview can not undo.")
            return

        module_stack_dict: dict = get_module_stack_dict()
        if module_name not in module_stack_dict:
            logging.info(f"ERROR: {module_name}'s stack is None.")
            return

        # 反撤销
        undo_stack = module_stack_dict[module_name]
        if undo_stack.canRedo() is False:
            logging.info(f"{module_name}'s stack can't Redo.")
            return

        if undo_stack.command(undo_stack.index()).linked_flag is False:
            undo_stack.redo()
        else:
            while (undo_stack.canRedo() is True) and (undo_stack.command(undo_stack.index()).linked_flag is True):
                undo_stack.redo()
            if (undo_stack.canRedo() is True) and (undo_stack.command(undo_stack.index()).linked_flag is False):
                undo_stack.redo()

    @log_function_stats(["二级菜单", "调度表", "调度表刷新"])
    def get_schedule_table_data(self, show_data_dict, progress_signal):
        sch_tbl_cfg = {}
        table_offset_list = []
        bsw_ecuc_dict = get_autosar_bsw_class()
        os_autosar = bsw_ecuc_dict.get("Os")
        for data in show_data_dict.values():
            lable_name = data[0]["label_name"]
            if lable_name == "ShortName":
                sch_tbl_cfg["name"] = data[0]["cfg_value"]
            elif lable_name == "OsScheduleTableCounterRef":
                sch_tbl_cfg["counter_ref"] = data[0]["cfg_value"]
            else:
                sch_tbl_cfg[lable_name] = data[0]["cfg_value"]
        table_offset_list = self.schedule_table_ui_cache.get(sch_tbl_cfg["name"], [])
        sch_tbl_cfg["task_groups"] = self.schedule_table_ui_cache.get(f'{sch_tbl_cfg["name"]}_task_groups', {})
        if table_offset_list:
            for col in range(len(table_offset_list)):
                for row in range(1, len(table_offset_list[col])):
                    task_name = table_offset_list[col][row]
                    if not task_name:
                        continue
                    if os_autosar.find(f"/ActiveEcuC/Os/{task_name}") is None:
                        table_offset_list[col][row] = ""
                        if task_name not in sch_tbl_cfg["task_groups"]:
                            continue
                        group_base = sch_tbl_cfg["task_groups"].pop(task_name)
                        for task_name, group in list(sch_tbl_cfg["task_groups"].items()):
                            if group_base != group:
                                continue
                            sch_tbl_cfg["task_groups"].pop(task_name)
            return table_offset_list, sch_tbl_cfg
        self.update_schedule_table_ui_cache()
        table_offset_list = self.schedule_table_ui_cache.get(sch_tbl_cfg["name"], [])
        return table_offset_list, sch_tbl_cfg

    def update_schedule_table_ui_cache(self, all_sch_tbl_cfg=None):
        all_sch_tbl_cfg = all_sch_tbl_cfg or self.get_all_sch_table_cfg()
        for sch_tbl_cfg_name, sch_table_cfg in all_sch_tbl_cfg.items():
            table_offset_dict = sch_table_cfg.get("task_offset_dict", {})
            self.schedule_table_ui_cache[sch_tbl_cfg_name] = [
                [offset] + task_list for offset, task_list in table_offset_dict.items()
            ]

    def get_schedule_table_task_dict(self):
        bsw_ecuc_dict = get_autosar_bsw_class()
        ib_bswmds = get_autosar_ib_class()
        asw_autosar = get_autosar_asw_class()
        os_autosar = bsw_ecuc_dict.get("Os")
        rte_autosar = bsw_ecuc_dict.get("Rte")
        timing_eucu_cfgs = ScheduleTableManager.get_timing_ecuc_infos(os_autosar, rte_autosar, asw_autosar, ib_bswmds)
        os_task_data_dict = ScheduleTableManager.get_ecuc_cfg(os_autosar, "/ActiveEcuC/Os", "OsTask", 0)
        task_dict = {
            task_cfg["ShortName"]: timing_eucu_cfgs.get(task_cfg["ShortName"], {})
            for task_cfg in os_task_data_dict
            if not task_cfg["SubContainers"]
        }
        return task_dict

    def generate_schedule_table_cfg(self, sch_tbl_ui_cfg, progress_signal):
        bsw_ecuc_dict = get_autosar_bsw_class()
        bsw_mod_dict = get_autosar_bswmd_class()
        ib_bswmds = get_autosar_ib_class()
        asw_autosar = get_autosar_asw_class()
        os_autosar = bsw_ecuc_dict.get("Os")
        rte_autosar = bsw_ecuc_dict.get("Rte")
        os_mod_autosar = bsw_mod_dict.get("Os")
        init_sch_tbl_cfg, main_sch_tbl_cfg = ScheduleTableManager.reasoning(
            sch_tbl_ui_cfg, os_autosar, rte_autosar, asw_autosar, ib_bswmds
        )
        ScheduleTableManager.generate(os_autosar, os_mod_autosar, init_sch_tbl_cfg, main_sch_tbl_cfg)

    def generate_all_schedule_table_cfg(self, progress_signal):
        bsw_ecuc_dict = get_autosar_bsw_class()
        bsw_mod_dict = get_autosar_bswmd_class()
        ib_bswmds = get_autosar_ib_class()
        asw_autosar = get_autosar_asw_class()
        os_autosar = bsw_ecuc_dict.get("Os")
        rte_autosar = bsw_ecuc_dict.get("Rte")
        os_mod_autosar = bsw_mod_dict.get("Os")
        sch_tbl_ui_cfg_list = []
        all_sch_table_cfg = self.get_all_sch_table_cfg()
        if not self.schedule_table_ui_cache:
            self.update_schedule_table_ui_cache(all_sch_table_cfg)
        else:
            for sch_tbl_cfg_name in set(self.schedule_table_ui_cache):
                if sch_tbl_cfg_name not in all_sch_table_cfg:
                    self.schedule_table_ui_cache.pop(sch_tbl_cfg_name)
        for sch_tbl_cfg_name, table_offset_list in self.schedule_table_ui_cache.items():
            task_offset_table = {
                task_name: row[0]
                for row in table_offset_list
                for task_name in row[1:]
                if isinstance(row[0], int)
                if task_name != ""
            }
            counter_ref = all_sch_table_cfg.get(sch_tbl_cfg_name, {}).get("counter_ref")
            if counter_ref is None:
                logger.ui_error(f"{sch_tbl_cfg_name} OsScheduleTableCounterRef is None")
                continue
            sch_tbl_ui_cfg = {
                "name": sch_tbl_cfg_name,
                "task_offset_table": task_offset_table,
                "counter_ref": counter_ref,
            }
            sch_tbl_ui_cfg_list.append(sch_tbl_ui_cfg)
        sch_tbl_cfgs = ScheduleTableManager.reasoning_all(
            sch_tbl_ui_cfg_list, os_autosar, rte_autosar, asw_autosar, ib_bswmds
        )
        ScheduleTableManager.generate_all(os_autosar, os_mod_autosar, sch_tbl_cfgs)

    def get_all_sch_table_cfg(self):
        bsw_ecuc_dict = get_autosar_bsw_class()
        asw_autosar = get_autosar_asw_class()
        ib_bswmds = get_autosar_ib_class()
        os_autosar = bsw_ecuc_dict.get("Os")
        rte_autosar = bsw_ecuc_dict.get("Rte")
        all_sch_table_cfg = {}
        try:
            all_sch_table_cfg = ScheduleTableManager.re_reasoning_all(os_autosar, rte_autosar, asw_autosar, ib_bswmds)
        except Exception:
            logger.exception("ScheduleTableManager.re_reasoning_all ERROR!")
        return all_sch_table_cfg

    def generate_schedule_table_cfg_by_jitter(self, opt, progress_signal):
        all_sch_tbl_cfg = self.get_all_sch_table_cfg()
        task_dict = self.get_task_dict()
        os_counter_dict = self.get_os_counter_dict()
        try:
            config_base_path = data_management.sys_info_class.config_base_path
            from basic_func_module.base_common.load_plug_in import LoadPlugIn

            jitter = LoadPlugIn.load_module("Os", "config_plug_in.auto_config.jitter")
            jitter_auto_optimization = getattr(jitter, "jitter_auto_optimization")
            progress_signal.emit("Optimizing in progress...")
            jitter_cfg_dict = jitter_auto_optimization(
                config_base_path, all_sch_tbl_cfg, task_dict, os_counter_dict, opt
            )
            progress_signal.emit("Updating configuration...")
            return self.update_offset_by_jitter(all_sch_tbl_cfg, jitter_cfg_dict)
        except Exception as e:
            logger.ui_error(f"Optimizing ERROR {e}!")
            logger.exception("Optimizing ERROR!")

    def get_task_dict(self):
        bsw_ecuc_dict = get_autosar_bsw_class()
        ib_bswmds = get_autosar_ib_class()
        asw_autosar = get_autosar_asw_class()
        task_core_dict = BswEditor.get_core_task_dict(asw_autosar, bsw_ecuc_dict, ib_bswmds)
        return task_core_dict

    def get_os_counter_dict(self):
        bsw_ecuc_dict = get_autosar_bsw_class()
        os_autosar = bsw_ecuc_dict.get("Os")
        os_counters = ScheduleTableManager.get_ecuc_cfg(os_autosar, "/ActiveEcuC/Os", "OsCounter", 0)
        return {os_counter["ShortName"]: os_counter for os_counter in os_counters}

    def update_offset_by_jitter(self, all_sch_tbl_cfg, jitter_cfg_dict):
        bsw_ecuc_dict = get_autosar_bsw_class()
        bsw_mod_dict = get_autosar_bswmd_class()
        ib_bswmds = get_autosar_ib_class()
        asw_autosar = get_autosar_asw_class()
        os_autosar = bsw_ecuc_dict.get("Os")
        rte_autosar = bsw_ecuc_dict.get("Rte")
        os_mod_autosar = bsw_mod_dict.get("Os")
        sch_table_jitter_cfg = jitter_cfg_dict.get("sch_tbl", {})
        sch_tbl_ui_cfg_list = ScheduleTableManager.convert_os_sch_tbl_cfg_to_ui(all_sch_tbl_cfg)
        sch_tbl_cfgs = ScheduleTableManager.reasoning_all_by_jitter_config(
            sch_tbl_ui_cfg_list, os_autosar, rte_autosar, asw_autosar, ib_bswmds, sch_table_jitter_cfg
        )
        ScheduleTableManager.generate_all(os_autosar, os_mod_autosar, sch_tbl_cfgs)
        alarm_jitter_cfg = jitter_cfg_dict.get("alarm", {})
        offset_cfg = BswEditor.get_offset_cfg_by_jitter_config(bsw_ecuc_dict, alarm_jitter_cfg)
        BswEditor.set_used_alarm_offset_by_offset_cfg(bsw_ecuc_dict, offset_cfg)
        history = {}
        history["time"] = datetime.now().isoformat()
        history["sch_tbl"] = ScheduleTableManager.convert_os_sch_tbl_cfg_to_ui(all_sch_tbl_cfg)
        history["alarm"] = [alarm for offset in offset_cfg for alarm in offset[0]]
        self.jitter_opt_history.append(history)
        self.update_schedule_table_ui_cache()
        return history["time"]

    def get_jitter_opt_history_time(self):
        return [history["time"] for history in self.jitter_opt_history]

    def rollback_jitter_opt_history(self, time, progress_signal):
        index = -1
        for i, history in enumerate(self.jitter_opt_history):
            if history["time"] == time:
                index = i
                break
        if index == -1:
            return
        bsw_ecuc_dict = get_autosar_bsw_class()
        ib_bswmds = get_autosar_ib_class()
        bsw_mod_dict = get_autosar_bswmd_class()
        os_mod_autosar = bsw_mod_dict.get("Os")
        asw_autosar = get_autosar_asw_class()
        os_autosar = bsw_ecuc_dict.get("Os")
        rte_autosar = bsw_ecuc_dict.get("Rte")
        try:
            if not self.jitter_opt_history:
                logger.warning("jitter opt history ")
                return
            history = self.jitter_opt_history[index]
            progress_signal.emit("Rolling back...")
            sch_tbl_cfgs = ScheduleTableManager.reasoning_all(
                history["sch_tbl"], os_autosar, rte_autosar, asw_autosar, ib_bswmds
            )
            ScheduleTableManager.generate_all(os_autosar, os_mod_autosar, sch_tbl_cfgs)
            BswEditor.set_used_alarm_offset_by_mapping_list(bsw_ecuc_dict, history["alarm"])
            self.update_schedule_table_ui_cache()
            self.jitter_opt_history = self.jitter_opt_history[:i]
        except Exception:
            logger.exception("rollback jitter opt history ERROR!")

    def save_jitter_opt_history(self):
        config_base_path = data_management.sys_info_class.config_base_path
        BswEditor.save_jitter_opt_history(config_base_path, self.jitter_opt_history)

    def save_schedule_table_ui_data(self, table_offset_list, sch_tbl_cfg):
        if not sch_tbl_cfg.get("name"):
            return
        self.schedule_table_ui_cache[sch_tbl_cfg["name"]] = table_offset_list
        # self.schedule_table_ui_cache[f'{sch_tbl_cfg["name"]}_task_groups'] = sch_tbl_cfg["task_groups"]

    def save_schedule_table_ui_cfg(self):
        from cfg_gui.widgets.sec_widgets import sec_runtime_system_os_configuration_schedule_table_widget as sch_tbl_ui

        if sch_tbl_ui.CURRENT_SCHEDULE_TABLE_WIDGET:
            sch_tbl_ui.CURRENT_SCHEDULE_TABLE_WIDGET.save_cfg()
        sch_tbl_ui_cfg = {}
        try:
            for sch_tbl_cfg_name, value in self.schedule_table_ui_cache.items():
                if isinstance(value, list):
                    sch_tbl_ui_cfg[sch_tbl_cfg_name] = [
                        [row for row in rows if row != ""] for rows in value if isinstance(rows[0], int)
                    ]
                elif isinstance(value, dict):
                    value = dict(sorted(value.items(), key=lambda v: v[1]))
                    sch_tbl_ui_cfg[sch_tbl_cfg_name] = value
            ScheduleTableManager.save_sch_tbl_ui_cfg(data_management.sys_info_class.config_base_path, sch_tbl_ui_cfg)
        except Exception:
            logger.exception("save schedule table ui cfg ERROR!")

    def get_create_container_dialog_show_data(self, rule_detail):
        secondary_cfg_dict = get_secondary_cfg_dict()
        show_data_type = rule_detail["come_from"].split(".")[0]
        return BswEditor.bsw_editor_get_create_container_dialog_show_data(
            show_data_type, secondary_cfg_dict[show_data_type]
        )

    def get_init_function_settings(self):
        secondary_cfg_dict = get_secondary_cfg_dict()
        return secondary_cfg_dict["init_function_settings"]

    def get_enable_modules(self):
        sys_info_class = get_sys_info_class()
        enable_module_list = []
        for value in sys_info_class.enable_modules:
            enable_module_list.append(value)
        return enable_module_list

    def update_init_function_settings(self, init_function_settings):
        enable_module_list = self.get_enable_modules()
        enable_init_function_settings = {}
        for key, value in init_function_settings.items():
            if value["BswModule"] in enable_module_list:
                enable_init_function_settings[key] = value

        return enable_init_function_settings

    def reset_initialization(self, phase):
        module_name = "EcuM"
        secondary_cfg_dict = get_secondary_cfg_dict()
        bsw_ecuc_dict = get_autosar_bsw_class()
        bsw_mod_dict = get_autosar_bswmd_class()

        enable_init_function_settings = self.update_init_function_settings(secondary_cfg_dict["init_function_settings"])

        BswEditor.reset_initialization(phase, bsw_ecuc_dict, bsw_mod_dict, enable_init_function_settings)

        return [module_name]

    def get_sec_bsw_management_configuration(self, dialog_type):
        bsw_ecuc_dict = get_autosar_bsw_class()
        enable_module_list = self.get_enable_modules()
        system_path = data_management.sys_info_class.system_path
        dialog_cfg = BswEditor.get_sec_bsw_management_configuration(
            dialog_type, bsw_ecuc_dict, enable_module_list, system_path
        )
        return dialog_cfg

    def update_state_to_bswm_common_data(self, item_state_cache, dialog_type):

        bsw_ecuc_dict = get_autosar_bsw_class()
        dialog_cfg = BswEditor.update_state_to_bswm_common_data(item_state_cache, dialog_type, bsw_ecuc_dict)
        return dialog_cfg

    def check_container_of_bswm_ecuc(self, dialog_type, create_sub_container_rules):
        module_name = "BswM"
        bsw_ecuc_dict = get_autosar_bsw_class()
        bsw_mod_dict = get_autosar_bswmd_class()
        enable_module_list = self.get_enable_modules()
        system_path = data_management.sys_info_class.system_path
        BswEditor.check_container_of_bswm_ecuc(
            dialog_type, create_sub_container_rules, bsw_ecuc_dict, bsw_mod_dict, enable_module_list, system_path
        )

        return [module_name]

    def sec_get_init_functions_that_have_been_initialized_in_ecum(self):
        module_name = "EcuM"
        bsw_ecuc_dict = get_autosar_bsw_class()

        return BswEditor.sec_get_init_functions_that_have_been_initialized_in_ecum(module_name, bsw_ecuc_dict)

    def get_used_os_alarm_infos_by_task_ref(self, task_ref: str):
        return BswEditor.get_used_os_alarm_infos_by_task_ref(get_autosar_bsw_class(), task_ref)

    def set_used_alarm_offset_by_mapping_ref(self, mapping_ref_list: list, offset: str):
        return BswEditor.set_used_alarm_offset_by_mapping_ref(get_autosar_bsw_class(), mapping_ref_list, offset)

    def cbk_filter_referenced_configurations(self, origin_ref_dict: dict, mod_path, module_name, ecuc_path):
        no_repeat_ref = getattr(get_sys_info_class(), "system_target_info", {}).get("no_repeat_ref", {})
        target_cfg = {}
        for ref_cfg in no_repeat_ref.get(module_name, []):
            if isinstance(ref_cfg, dict) and mod_path in ref_cfg.get("param_path", []):
                target_cfg = ref_cfg
                break
        if not target_cfg:
            return
        bsw_ecuc_obj = get_autosar_bsw_class().get(module_name, None)
        if bsw_ecuc_obj is None:
            return
        index_gap = len(target_cfg.get("base_path", "").split("/")) - len(mod_path.split("/")) + 1
        parent_container_path = "/".join(ecuc_path.split("/")[:index_gap])
        container_obj = bsw_ecuc_obj.find(parent_container_path)
        if container_obj is None:
            return
        param_name = mod_path.split("/")[-1]
        result_dict = {}
        try:
            BswEditor.get_all_ref_param_values(container_obj, mod_path, param_name, result_dict)
        except Exception as e:
            logger.exception(f"ERROR: get all ref param values for {mod_path} failed: {e}.")
        for ref_list in result_dict.values():
            for ref_val in ref_list:
                if ref_val in origin_ref_dict:
                    origin_ref_dict.pop(ref_val)
