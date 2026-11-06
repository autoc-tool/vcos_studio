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
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlParseHandler
from func_module.module_management.arxml_handler.system.system_arxmls_manager import SystemArxmlsManager
from func_module.module_management.arxml_handler.system.flatextract_arxml_manager import FlatExtractArxmlManager
from func_module.health_monitor.logger import logger
from func_module.project_management.sys_info_class import SysInfoClass
from func_module.module_management.base_config import BASE_CONFIG_PATH
from func_module.module_management.arxml_handler.ecuc_arxml_updater import EcucArxmlUpdater
from func_module.module_management.arxml_handler.base_ecuc_creator import BaseEcucCreator
from func_module.module_management.arxml_handler.rte_instances.rte_instances_manager import (
    RteBswInstancesManager,
    clear_automatic_os_resource_and_spinlock,
)
from func_module.mapping.task_mapping_core import TaskMappingInstance
from basic_func_module.base_common.load_plug_in import LoadPlugIn
from basic_func_module.autosar_utils.autosar_ecuc import AutosarEcuc
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.autosar_utils.utils import (
    get_definition_ref,
    get_upper_multiplicity,
    get_upper_multiplicity_infinite,
    set_short_name,
    get_admin_data_all,
)

CUR_DIR_PATH = os.path.abspath(os.path.dirname(__file__))
FUNC_MODULE_DIR_PATH = os.path.dirname(CUR_DIR_PATH)
STUDIO_DIR_PATH = os.path.dirname(FUNC_MODULE_DIR_PATH)
BASE_ECUC_DIR_PATH = os.path.join(STUDIO_DIR_PATH, "config", "ecuc")


class ModuleManagement:

    def __init__(self, sys_info: SysInfoClass, bsw_ecuc_info, bswmd_obj_dict, ib_obj_dict) -> None:
        self.sys_info = sys_info
        self.bsw_ecuc_info = bsw_ecuc_info
        self.bswmd_obj_dict = bswmd_obj_dict
        self.ib_obj_dict = ib_obj_dict

    @classmethod
    def change_module_name(cls, old_name, new_name, bsw_ecuc_obj_dict: dict):
        if old_name == new_name:
            return False
        if new_name in bsw_ecuc_obj_dict:
            logger.error("Same name as existing module!")
            return False
        old_path = ""
        new_path = ""
        ecuc_obj = bsw_ecuc_obj_dict.pop(old_name, None)
        for ecuc_conf_val in ecuc_obj.find_nodes("ECUC-MODULE-CONFIGURATION-VALUES"):
            old_path: str = ecuc_conf_val.get_path()
            if not old_path.endswith(old_name):
                continue
            new_path = old_path.replace(old_name, new_name, 1)
            set_short_name(ecuc_conf_val, new_name)
            cls.clear_file_label(f"{old_name}_ecuc.arxml", ecuc_obj)
            bsw_ecuc_obj_dict[new_name] = AutosarUtil.update_autosar(ecuc_obj)
        if not new_path:
            return False
        for ecuc_obj in bsw_ecuc_obj_dict.values():
            for value_ref_obj in ecuc_obj.find_nodes("VALUE-REF"):
                value_ref = getattr(value_ref_obj, "valueOf_", "") or ""
                if not value_ref.startswith(old_path):
                    continue
                setattr(value_ref_obj, "valueOf_", value_ref.replace(old_path, new_path, 1))
        logger.info(f"Successfully changed module name: {old_name} -> {new_name}.")
        return True

    @classmethod
    def clear_file_label(cls, file_name, ecuc_obj):
        for admin_data in ecuc_obj.find_nodes("ADMIN-DATA"):
            admin_data_all = get_admin_data_all(admin_data.get_parent()) or {}
            if file_name == (
                admin_data_all.get(AutosarEcuc.VCOS_DEFAULT_LABEL, {}).get(AutosarEcuc.VCOS_DEFAULT_FILE_LABEL)
                or admin_data_all.get(AutosarEcuc.VCOS_PATH_LABEL, {}).get(AutosarEcuc.VCOS_FILE_PATH_LABEL)
            ):
                admin_data.SDGS.SDG.clear()

    def get_all_module_list(self):
        all_module_list = sorted(self.sys_info.all_modules)
        return all_module_list

    def get_added_module_dict(self):
        added_module_dict = {}
        for module_instance_name, module_autosar in self.bsw_ecuc_info.items():
            module_obj = module_autosar.find(f"/ActiveEcuC/{module_instance_name}")
            def_ref = get_definition_ref(module_obj)
            if not isinstance(def_ref, str):
                continue
            module_name = def_ref.split("/")[-1]
            bswmd_obj = self.bswmd_obj_dict.get(module_name)
            ecuc_module_def_obj = bswmd_obj.find(def_ref)
            if ecuc_module_def_obj:
                upper = get_upper_multiplicity(ecuc_module_def_obj)
                infinite = get_upper_multiplicity_infinite(ecuc_module_def_obj)
            else:
                upper = 1
                infinite = False
            if infinite:
                upper = infinite
            added_module_dict[module_instance_name] = {"module_name": module_name, "multiple_instance": upper}

        return added_module_dict

    def get_appended_module_set(self, module_list: list):
        added_module_set: set = self.sys_info.enable_modules
        selected_module_set: set = set(module_list)
        appended_module_set = selected_module_set - added_module_set
        return appended_module_set

    def load_ecuc(self, module_name, instance_name, prefix=None):
        # 1. Try load base ecuc arxml
        class_dict = ArxmlParseHandler.parse_base_autosar_ecuc_arxml(
            self.sys_info.plug_in_path, self.sys_info.target, [module_name]
        )
        if module_name in class_dict:
            autosar_obj = class_dict[module_name]
            self.change_module_name(module_name, instance_name, class_dict)
            logger.debug(f"Parse base ecuc arxml of {module_name} success.")
            return autosar_obj
        else:
            logger.debug(f"Parse base ecuc arxml of {module_name} fail. Try infer base ecuc from bswmd.")

        # 2.Infer base ecuc according to bswmd. The bswmd must has been loaded
        base_ecuc_creator = BaseEcucCreator()
        return base_ecuc_creator.infer_base_ecuc(
            module_name, instance_name, self.bswmd_obj_dict[module_name], self.sys_info, prefix
        )

    def load_bswmd(self, module_name):
        if module_name in self.bswmd_obj_dict:
            return {module_name: self.bswmd_obj_dict[module_name]}
        return ArxmlParseHandler.parse_all_bswmd_arxml(
            self.sys_info.plug_in_bswmd_path, [module_name], self.sys_info.target
        )

    def load_ib(self, module_name):
        class_dict = ArxmlParseHandler.parse_base_internal_behavior_arxml(
            self.sys_info.plug_in_ib_path, self.sys_info.target, set([module_name]), self.sys_info.system_target_info
        )
        if module_name in class_dict:
            return class_dict[module_name]
        else:
            logger.debug(f"Parse base ib arxml of {module_name} fail")
            return None

    def append_module(self, module_name, instance_name=None, prefix=None):
        instance_name = instance_name or module_name
        if instance_name in self.sys_info.enable_modules:
            logger.info(f"{module_name} already added")
            return
        if module_name not in self.sys_info.all_modules:
            logger.info(f"{module_name} not supported ui")
            return
        ib_obj = self.load_ib(instance_name)
        bswmd_res = self.load_bswmd(module_name)
        self.bswmd_obj_dict.update(bswmd_res)
        ecuc_obj = self.load_ecuc(module_name, instance_name, prefix)
        AutosarEcuc.record_default_file(ecuc_obj.find(f"/ActiveEcuC/{instance_name}"), f"{instance_name}_ecuc.arxml")
        self.update_module_info(module_name, instance_name, ib_obj, bswmd_res, ecuc_obj)

    def update_ecuc_module_by_import(self, module_name, ecuc_obj):
        ib_obj = self.load_ib(module_name)
        bswmd_res = self.load_bswmd(module_name)
        self.bswmd_obj_dict.update(bswmd_res)
        self.update_module_info(module_name, module_name, ib_obj, bswmd_res, ecuc_obj)

    def update_module_info(self, module_name, instance_name, ib_obj, bswmd_res, ecuc_obj):
        if ecuc_obj is None:
            logger.ui_error(f"Cannot get base config of {module_name}, failed to add {instance_name} module.")
        elif not bswmd_res.get(module_name):
            logger.ui_error(f"Cannot load bswmd of {module_name}, failed to add {instance_name} module.")
        else:
            self.sys_info.enable_modules = self.sys_info.enable_modules | {instance_name}
            if ib_obj is not None:
                self.ib_obj_dict[instance_name] = ib_obj
            self.bsw_ecuc_info[instance_name] = ecuc_obj
            ecuc_updater = EcucArxmlUpdater(self.bswmd_obj_dict[module_name], ecuc_obj)
            ecuc_updater.update_ecuc_with_default_value()
            self.add_bsw_module_to_rte_bsw_module_instances(instance_name)
            logger.info(f"Add {instance_name} successfully")

    def remove_module(self, module_name, system_autosar_dict):
        if self.bsw_ecuc_info.pop(module_name, -1) != -1:
            task_mapping_instance = None
            if module_name == "Rte":
                task_mapping_instance = TaskMappingInstance.update_task_mapping_instance(
                    {}, self.bsw_ecuc_info, {}, {}, self.bswmd_obj_dict
                )
                task_mapping_instance.deinit()
                clear_automatic_os_resource_and_spinlock(self.bsw_ecuc_info.get("Os", None))
                com_ecuc_manager = LoadPlugIn.load_module("Com", "config_plug_in.update_ecuc.com_ecuc_manager")
                com_ecuc_manager.ComEcucManager.clear_rte_auto_derived_config(self.bsw_ecuc_info.get("Com", None))
                FlatExtractArxmlManager.del_all_assembly_sw_connectors(system_autosar_dict["FlatExtract"])
                system_autosar_dict["FlatExtract"] = AutosarUtil.update_autosar(system_autosar_dict["FlatExtract"])

            self.sys_info.enable_modules = self.sys_info.enable_modules - {module_name}
            self.sys_info.codegen_modules = self.sys_info.codegen_modules - {module_name}
            self.ib_obj_dict.pop(module_name, -1)
            self._remove_initial_autosar_module(module_name, system_autosar_dict)
            logger.info(f"Remove {module_name} successfully")
        else:
            logger.info(f"{module_name} not exists.")

    def update_modules(self, module_list: list, system_autosar_dict):
        logger.debug("Start update modules")
        appended_modules = list(self.get_appended_module_set(module_list))
        appended_modules.sort()
        if "Rte" in appended_modules:
            self.append_module("Rte")
            module_list.remove("Rte")
            appended_modules.remove("Rte")
        for module in appended_modules:
            self.append_module(module, module)
            module_list.remove(module)
        added_module_dict = self.get_added_module_dict()
        multinstance_module_set = {v["module_name"] for v in added_module_dict.values() if v["multiple_instance"] > 1}
        module_count = {}
        for module in module_list:
            if module not in multinstance_module_set:
                continue
            module_count.setdefault(module, 1)
            i = module_count[module]
            instance_name = f"{module}_{i:03}"
            while instance_name in added_module_dict:
                i += 1
                instance_name = f"{module}_{i:03}"
            module_count[module] = i
            self.append_module(module, instance_name)
            module_count[module] += 1

    def _remove_initial_autosar_module(self, module_name, system_autosar_dict):
        base_arxml_path = os.path.join(BASE_CONFIG_PATH, "base_arxml")
        system_arxmls_manager = SystemArxmlsManager(self.bswmd_obj_dict)
        system_arxmls_manager.remove_initial_autosar_module(module_name, system_autosar_dict, base_arxml_path)

    def add_bsw_module_to_rte_bsw_module_instances(self, instance_name):
        """add bsw module to Rte->BswModuleInstance

        Args:
            module_name (_type_): _description_
        """
        RteBswInstancesManager.add_rte_bsw_module_instance_from_ib(
            self.bswmd_obj_dict.get("Rte", None),
            self.bsw_ecuc_info.get("Rte", None),
            self.ib_obj_dict.get(instance_name, None),
            instance_name,
        )

    @classmethod
    def get_removed_module_by_path_update(cls, old_path_list, new_path_list):
        removed_paths = set(old_path_list) - set(new_path_list)

        return cls.get_module_info_by_spec_path(removed_paths)

    @classmethod
    def get_module_info_by_spec_path(cls, file_path_set: set):
        removed_modules = {path: os.path.basename(path) for path in file_path_set}

        return removed_modules

    @classmethod
    def get_module_path_info_by_spec_path(cls, file_path_set: set):
        module_path_info = {os.path.basename(path): path for path in file_path_set}

        return module_path_info
