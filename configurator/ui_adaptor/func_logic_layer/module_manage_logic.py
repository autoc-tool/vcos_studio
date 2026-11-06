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
from func_module.module_management.module_management import ModuleManagement
from ui_adaptor.data_management import data_management as data
from ui_adaptor.ui_interaction.ui_logger import logger
from func_module.health_monitor.perf_record import log_function_stats


class ModuleManageLogic:

    def __init__(self) -> None:
        self.module_management = None

    @log_function_stats(["BSW Editor", "模块管理", "模块重命名"])
    def change_module_name(self, old_name, new_name, progress_signal):
        progress_signal.emit("Updating module name")
        res = ModuleManagement.change_module_name(old_name, new_name, data.autosar_bsw_class)
        if res:
            data.enable_module_list.add(new_name)
            data.sys_info_class.enable_modules = set(data.autosar_bsw_class)
            return new_name
        else:
            return old_name

    def init_module_management(self):
        self.module_management = ModuleManagement(
            data.sys_info_class, data.autosar_bsw_class, data.autosar_bswmd_class, data.autosar_ib_class
        )
        all_module_list = self.module_management.get_all_module_list()
        added_module_dict = self.module_management.get_added_module_dict()
        level_module_dict = data.sys_target_dict["level"]
        return all_module_list, added_module_dict, level_module_dict

    @log_function_stats(["BSW Editor", "模块管理", "批量增加和移除模块"])
    def apply_modules_change(self, module_list, progress_signal):
        progress_signal.emit("Updating modules")
        module_set = set(data.autosar_bsw_class)
        self.module_management.update_modules(module_list, data.autosar_system_class)
        module_set = set(data.autosar_bsw_class) - module_set
        data.enable_module_list.symmetric_difference_update(module_set)
        return data.autosar_bswmd_class, data.autosar_bsw_class

    def close_module_management(self):
        self.module_management = None
        return True

    @log_function_stats(["BSW Editor", "模块管理", "单独移除模块"])
    def remove_modules(self, removed_module_list, progress_signal):
        progress_signal.emit("Removing modules")
        self.module_management = ModuleManagement(
            data.sys_info_class, data.autosar_bsw_class, data.autosar_bswmd_class, data.autosar_ib_class
        )

        seen = set()
        unique_module_list = [x for x in removed_module_list if not (x in seen or seen.add(x))]
        for module in unique_module_list:
            self.module_management.remove_module(module, data.autosar_system_class)
        self.module_management = None
        return data.autosar_bswmd_class, data.autosar_bsw_class

    def get_current_project_module_info(self):
        self.module_management = ModuleManagement(
            data.sys_info_class, data.autosar_bsw_class, data.autosar_bswmd_class, data.autosar_ib_class
        )
        all_module_list = self.module_management.get_all_module_list()
        added_module_dict = self.module_management.get_added_module_dict()
        return all_module_list, added_module_dict

    def get_module_dependence(self, module_name):
        module_cfg: dict = data.sys_target_dict["module_cfg"]
        if module_info := module_cfg.get(module_name, None):
            module_info: dict
            return module_info.get("dependency_list", [])
        else:
            logger.error(f"Cannot find {module_name} in module_cfg of system_cfg.json")
            return []

    def get_module_dependence_by(self, module_name):
        module_cfg: dict = data.sys_target_dict["module_cfg"]
        dependence_by_list = []
        for module, cfg in module_cfg.items():
            if module_name in cfg.get("dependency_list", []):
                dependence_by_list.append(module)

        return dependence_by_list
