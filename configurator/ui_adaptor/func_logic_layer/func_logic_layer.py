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
from collections import defaultdict
import os
import json
import time
from typing import Iterable
from func_module.project_management.project_file_parser import ProjectFileParser
from func_module.project_management.project_xml_info import ProjectXmlInfoHandler
from func_module.project_management.sys_info_class import SysInfoClass
from func_module.project_management.studio_cfg_handler import StudioCfgHandler
from ui_adaptor.func_logic_layer.import_files_logic import ImportFilesLogic
from ui_adaptor.func_logic_layer.module_manage_logic import ModuleManageLogic
from ui_adaptor.func_logic_layer.port_mapping_func import PortMappingFunc
from ui_adaptor.func_logic_layer.service_mapping_func import ServiceMappingFunc
from ui_adaptor.func_logic_layer.data_mapping_func import DataMappingFunc
from ui_adaptor.func_logic_layer.task_mapping_func import TaskMappingFunc
from ui_adaptor.func_logic_layer.bsw_editor_ui_func import BswEditorUIFunc
from ui_adaptor.func_logic_layer.validation_func import ValidationFunc
from ui_adaptor.func_logic_layer.export_file_func import ExportFileFunc
from ui_adaptor.func_logic_layer.os_cfg_ui_func import OsConfigureUIFunc
from func_module.generator import generator as vcos_generator
from func_module.generator.ssc_type import generator as arxml_generator
from func_module.generator.common.common import generator_utility
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlSaveHandler, ArxmlParseHandler
from func_module.project_management.project_file_lock import ProjectFileLock
from func_module.project_management.project_handler import ProjectHandler
from func_module.module_management.arxml_handler.ecuc_arxml_updater import EcucArxmlUpdater
from func_module.module_management.arxml_handler.system.system_arxmls_manager import SystemArxmlsManager
from func_module.module_management.arxml_handler.ib_bswmd_process.ib_bswmd_process import IbBswmdProcess
from func_module.module_management.arxml_handler.rte_instances.rte_instances_manager import (
    update_rte_instances_and_os_resource_spinlock,
)
from ui_adaptor.ui_interaction.ui_logger import logger
from ui_adaptor.data_management import data_management
from func_module.project_management.version_management.upgrade import UpgradeCliProject
from func_module.project_management.version_management.upgrade import UpgradeCli
from func_module.project_management.version_management.vcos_version import VCOS_VERSION
from basic_func_module.file_validation.arxml_validator import ArxmlFileValidator
from func_module.project_management.version_management.upgrade import VersionUpgradeProject
from ui_adaptor.func_logic_layer.task_analysis_logic import TaskAnalysisLogic
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from func_module.module_management.arxml_handler.config_comparator import ConfigComparator
from func_module.mapping.task_mapping_core import TaskMappingInstance
from ui_adaptor.func_logic_layer.vfb_trace_function import VfbTraceFunction
from func_module.generator.rte import rte_parser
from func_module.health_monitor.perf_record import log_function_stats
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlIncrementalSaveHandler
from func_module.project_management.project_save_handler import ProjectSaveHandlerFunc
import threading
from func_module.validation.validator import Validator
from func_module.module_management.base_config import BASE_CONFIG_PATH
from func_module.project_management.version_management.vcos_version import JSON_FILE_PATH

BASE_ARXML_PATH = os.path.join(BASE_CONFIG_PATH, "base_arxml")
GENERAL_JSON_PATH = os.path.join(BASE_CONFIG_PATH, "configrator_general.json")
SCHEMA_XSD_FILE = os.path.join(BASE_CONFIG_PATH, "autosar_cfg/AUTOSAR_00046.xsd")


class FuncLogicLayer:

    def __init__(self) -> None:
        self.init_obj()
        self.threading_lock = threading.Lock()
        self.__init_function()

    def __init_function(self):
        self.port_mapping_func = PortMappingFunc()
        self.service_mapping_func = ServiceMappingFunc()
        self.data_mapping_func = DataMappingFunc()
        self.task_mapping_func = TaskMappingFunc()
        self.bsw_editor_ui_func = BswEditorUIFunc()
        self.export_file_func = ExportFileFunc()
        self.import_files_logic = ImportFilesLogic()
        self.validation_func = ValidationFunc()
        self.task_analysis_func = TaskAnalysisLogic()
        self.vfb_trace_function = VfbTraceFunction()
        self.save_configuration_func = ProjectSaveHandlerFunc(self.threading_lock)

    def init_obj(self):
        self.project_file_parser = ProjectFileParser()
        self.project_file_lock = ProjectFileLock()
        self.project_path = ""
        self.general_data = {"save_cycle": ""}
        self.arxml_file_validator = ArxmlFileValidator()
        self.arxml_file_validator.set_arxml_schema(SCHEMA_XSD_FILE)
        # Init module management module
        self.module_manage_logic = ModuleManageLogic()

    def import_asw_parser(self):
        pass

    def update_mode_info(self, info_dict):
        data_management.sys_info_class.mode = info_dict["mode_info"]
        data_management.sys_info_class.incremental_generation = info_dict["incremental_generation_info"]
        data_management.sys_info_class.generation_limit = info_dict.get("generation_limit", "Error")
        data_management.sys_info_class.sim_mode = info_dict.get("sim_mode", False)

    def get_module_type(self):
        module_cfg = getattr(data_management, "sys_target_dict", {}).get("module_cfg", {})
        module_type_dict = {}
        for module_name, module_cfb_obj in module_cfg.items():
            module_type_dict[module_name] = {"is_mcal": module_cfb_obj.get("is_mcal", False)}

        return module_type_dict

    def get_prj_path(self):
        return data_management.sys_info_class.project_path

    def get_sys_info(self):
        return data_management.sys_info_class

    def check_mcal_module_codegen_cmd_line_tool_exist(self, module_name):
        """
        检查选择的模块是否有代码命令行生成工具
        1. 如果不是mcal模块,无需关心
        2. 如果是mcal模块,但代码命令行生成工具不存在,返回False,返回被检查的路径
        3. 如果是mcal模块,且代码命令行生成工具存在,返回命令行工具的绝对路径
        """
        return generator_utility.func_module_check_mcal_module_codegen_cmd_line_tool_exist(data_management, module_name)

    def check_and_upgrade_project_file(self, file_path):
        # 代开文件
        if not os.path.exists(file_path):
            logger.error(f"{file_path} not exist!")
            return False
        info_dict = {}
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                info_dict = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"{type(e).__name__} - {str(e)}")
                return False
        # 检查及升级
        vcosproject_version_list = self.upgrade_pro_check(info_dict)
        VersionUpgradeProject.upgrade_project_file(vcosproject_version_list, info_dict)
        # 保存文件
        with open(file_path, "w", encoding="utf-8") as f:
            try:
                json.dump(info_dict, f, indent=4)
            except json.JSONDecodeError as e:
                logger.error(f"{type(e).__name__} - {str(e)}")
                return False

    def update_plugin_dir_list(self, file_path_list):
        data_management.sys_info_class.import_plugin_path_list = file_path_list

    @log_function_stats(["VCOS工程管理", "打开工程"])
    def open_project(self, project_path):
        # ProjectFileParser提供工程文件配置解析
        project_path = os.path.realpath(project_path)
        result = ProjectXmlInfoHandler.load_xml_file(project_path)
        if result and result.get("asw_component") is not None:
            logger.debug({k: os.path.basename(v) for k, v in result.get("asw_component", {}).items()})
        if result and isinstance(data_management.component_arxml_path_dict, dict):
            data_management.component_arxml_path_dict = result
        else:
            logger.debug("vcos_project.xml not exist")

        result = self.project_file_parser.load_file(project_path)
        if result is False:
            return None, None, None

        compatibility_info = self.project_file_parser.get_version_compatibility_info()
        self.project_file_parser.process_compatibility_info(compatibility_info)
        check_result = self.project_file_parser.cfg_pre_check()
        """if return false """
        # 实例化SysInfoClass提供get、set方法
        self.sys_info_obj = SysInfoClass()
        # 从ProjectFileParser解析或者构造的配置设值sys_info_obj
        result = self.project_file_parser.init_sys_info(self.sys_info_obj)
        if result is False:
            return None, None, None
        data_management.sys_info_class = self.sys_info_obj
        data_management.sys_target_dict = data_management.sys_info_class.system_target_info
        data_management.sys_info_class.all_modules = self.project_file_parser.get_all_module_list(
            data_management.sys_target_dict
        )
        data_management.all_module_list = data_management.sys_info_class.all_modules
        if data_management.sys_info_class.target in data_management.sys_target_dict["validate"]["ignore_option"]:
            data_management.sys_target_dict["validate"]["ignore_option"] = data_management.sys_target_dict["validate"][
                "ignore_option"
            ][data_management.sys_info_class.target]
        data_management.sys_info_class.system_target_info.update(data_management.sys_target_dict)
        data_management.cfg_info_dict.update({"target": data_management.sys_info_class.target})
        result = self.upgrade_check()
        return check_result, result, compatibility_info

    def upgrade_check(self):
        self.upgrade_cli = UpgradeCli(
            self.project_file_parser.vcos_info.studio_version, self.project_file_parser.vcos_info.system_version
        )
        result = self.upgrade_cli.auto_cli_upgrade(data_management.sys_info_class, type=True)
        return result

    def upgrade_pro_check(self, cur_info_dict):
        self.upgrade_pro_cli = UpgradeCliProject(
            self.project_file_parser.vcos_info.studio_version,
            cur_info_dict,
            data_management.sys_info_class.plug_in_path,
        )
        vcosproject_version_list = self.upgrade_pro_cli.auto_cli_upgrade()
        return vcosproject_version_list

    def get_studio_version_func(self):
        from basic_func_module.file_handler.file_io_handler import FileIOHandler

        version_json_path = JSON_FILE_PATH
        if not os.path.exists(version_json_path):
            return ""
        data = FileIOHandler.load_json_file(version_json_path)
        return data["components"]["Studio"]["version"]

    def load_project_config(self, project_path, progress_signal):
        progress_signal.emit(f"load  {data_management.sys_info_class.project} configuration")
        config_path = data_management.sys_info_class.config_base_path
        enable_module_list = data_management.sys_info_class.enable_modules
        # 1. parse ecuc arxml
        # 2. parse ib arxml
        # 3. parse system arxml
        # 4. parse bswm arxml
        progress_signal.emit("parse project arxml")
        generator_utility.load_system_cfg_by_target(data_management)
        self.load_secondary_menu_cfg()
        self.load_init_function_settings_by_target()
        result = self.load_project_arxml(config_path, enable_module_list)
        data_management.autosar_system_class = result[0]
        data_management.autosar_bswmd_class = result[1]
        data_management.autosar_bsw_class = result[2]
        data_management.autosar_ib_class = result[3]
        data_management.autosar_asw_class = result[4]
        data_management.enable_module_list = data_management.sys_info_class.enable_modules
        data_management.sys_info_class.all_modules = data_management.all_module_list
        # update bsw_cfg with config_file_path while loading project for usages, such as functionality of finding
        ProjectHandler.update_bsw_module_cfg_path(data_management.sys_info_class)

        return data_management.autosar_bswmd_class, data_management.autosar_bsw_class

    def load_init_function_settings_by_target(self):

        sys_target = data_management.sys_target_dict["target"]
        target = data_management.sys_info_class.target
        system_path = data_management.sys_info_class.system_path

        init_function_settings_json_path = os.path.normpath(
            os.path.join(
                system_path,
                "platform_cfg",
                sys_target[target]["DERIVATIVE_GROUP"],
                target,
                "init_function_settings.json",
            )
        )
        data = StudioCfgHandler.load_studio_cfg_file(init_function_settings_json_path)
        if data is None:
            logger.info("Current chip does not have a separate init_function_settings_json_path.json")
            return
        data_management.sys_secondary_cfg_dict["init_function_settings"].update(
            data["init_function_settings"]
        )  # 替换芯片支持mcal模块的init function配置

    def load_project_arxml(self, config_path, enable_module_list) -> bool:
        asw_autosar_class = ArxmlParseHandler.parse_asw_arxml(config_path)
        system_autosar_class = ArxmlParseHandler.parse_system_dir_arxml(config_path)
        bswmd_autosar_class = ArxmlParseHandler.parse_all_bswmd_arxml(
            data_management.sys_info_class.plug_in_bswmd_path, enable_module_list, data_management.sys_info_class.target
        )
        ecuc_autosar_class = ArxmlParseHandler.parse_autosar_ecuc_arxml(config_path, enable_module_list)
        for instance_name, ecuc_obj in ecuc_autosar_class.items():
            module_obj = ecuc_obj.find(f"/ActiveEcuC/{instance_name}")
            module_name = getattr(getattr(module_obj, "DEFINITION_REF", ""), "valueOf_", "").split("/")[-1]
            if module_name not in bswmd_autosar_class:
                res = ArxmlParseHandler.parse_all_bswmd_arxml(
                    data_management.sys_info_class.plug_in_bswmd_path,
                    [module_name],
                    data_management.sys_info_class.target,
                )
                bswmd_autosar_class.update(res)
            bswmd_obj = bswmd_autosar_class.get(module_name)
            if not bswmd_obj:
                continue
            ecuc_updater = EcucArxmlUpdater(bswmd_obj, ecuc_obj)
            ecuc_updater.update_ecuc_with_default_value()

        ib_autosar_class = ArxmlParseHandler.parse_internal_behavior_arxml(
            config_path, enable_module_list, data_management.sys_target_dict
        )

        ArxmlIncrementalSaveHandler.get_autosar_class_hash(
            system_autosar_class,
            ecuc_autosar_class,
            ib_autosar_class,
            asw_autosar_class,
            data_management.sys_info_class,
        )

        return system_autosar_class, bswmd_autosar_class, ecuc_autosar_class, ib_autosar_class, asw_autosar_class

    @log_function_stats(["studio版本管理", "版本升级"])
    def studio_version_upgrade(self, path, progress_signal):
        progress_signal.emit("upgrade is executing")
        try:
            if self.threading_lock.acquire(blocking=True):
                result, bsw_ecuc_autosar_class, mod_autosar_dict, ib_autosar_class = (
                    self.upgrade_cli.vcos_version_upgrade(data_management)
                )
                data_management.autosar_bsw_class = bsw_ecuc_autosar_class
                data_management.autosar_bswmd_class = mod_autosar_dict
                data_management.autosar_ib_class = ib_autosar_class
                if result is False:
                    logger.warning("upgrade is not completed, please check upgrade-supported modules.")
                    return {}, {}
                ArxmlSaveHandler.save_bsw_ecuc_arxml(
                    data_management.autosar_bsw_class,
                    data_management.sys_info_class.config_base_path,
                    data_management.sys_info_class.enable_modules,
                )
                self.save_vcos_project_config_file(None, True, progress_signal)
        except Exception as e:
            logger.error(f"Error occurred while saving ARXML: {str(e)}")
        finally:
            self.threading_lock.release()
        return data_management.autosar_bswmd_class, data_management.autosar_bsw_class

    def vcos_bsw_rte_switch_tab(self, tab_name, prev_rte_tab_name, is_rte_parse_new_dict, progress_signal):
        progress_signal.emit("updating")
        update_data_info = {}
        if tab_name == "VCOS RTE":
            is_update_overview = True
            update_data_info.update({"Task Mapping": is_update_overview})
            self.update_mapping_data_status(update_data_info, prev_rte_tab_name)
        elif tab_name == "VCOS BSW":
            other_input_info = {
                "codegen_autosar_dict": vcos_generator.init_codegen_autosar_dict(data_management),
                "sys_info_class": data_management.sys_info_class,
                "sys_target_dict": data_management.sys_target_dict,
                "is_rte_parse_new_dict": is_rte_parse_new_dict,
            }
            IbBswmdProcess.update_all_ib_bswmd(
                data_management.autosar_ib_class,
                data_management.autosar_bsw_class,
                data_management.autosar_asw_class,
                data_management.autosar_system_class,
                other_input_info,
            )
            is_update_overview = False
            update_data_info.update({"Task Mapping": is_update_overview})
            # by default: show TASK MAPPING after switching to RTE view
            self.get_mapping_data("Task Mapping", "Task Mapping")
            # 更新bsw的信息
            pass
        else:
            logger.error("Unknown mapping")

        return update_data_info

    def get_secondary_module_enabled_state(self, module):
        enabled_module_list = data_management.sys_info_class.enable_modules
        return module in enabled_module_list

    def update_mapping_data_status(self, mapping_data_info, prev_tab_name):
        if prev_tab_name == "Task Mapping":
            mapping_data_info["prev_mapping"] = "task"
            mapping_data_info["is_prev_mapping_data_updated"] = self.task_mapping_func.is_mapping_data_updated()
        elif prev_tab_name == "Data Mapping":
            mapping_data_info["prev_mapping"] = "data"
            mapping_data_info["is_prev_mapping_data_updated"] = self.data_mapping_func.is_mapping_data_updated()
        elif prev_tab_name == "Service Mapping":
            mapping_data_info["prev_mapping"] = "serv"
            mapping_data_info["is_prev_mapping_data_updated"] = self.service_mapping_func.is_mapping_data_updated()
        elif prev_tab_name == "Port Mapping":
            mapping_data_info["prev_mapping"] = "port"
            mapping_data_info["is_prev_mapping_data_updated"] = self.port_mapping_func.is_mapping_data_updated()
        else:
            logger.error("Unknown mapping")

    def get_mapping_data(self, next_tab_name, prev_tab_name):
        mapping_data_info = {"is_prev_mapping_data_updated": True, "prev_mapping": None}
        if next_tab_name == "Task Mapping":
            self.task_mapping_func.init_mapping_data_status()
        elif next_tab_name == "Data Mapping":
            data = self.data_mapping_func.get_rte_editor_ui_data_mapping_table_data()
            mapping_data_info.update({"Data Mapping": data})
            self.data_mapping_func.init_mapping_data_status()
        elif next_tab_name == "Service Mapping":
            data = self.service_mapping_func.get_rte_editor_ui_service_mapping_table_data()
            mapping_data_info.update({"Service Mapping": data})
            self.service_mapping_func.init_mapping_data_status()
        elif next_tab_name == "Port Mapping":
            data = self.port_mapping_func.get_rte_editor_ui_port_mapping_table_data()
            mapping_data_info.update({"Port Mapping": data})
            self.port_mapping_func.init_mapping_data_status()
        else:
            logger.error("Unknown mapping")

        if next_tab_name != prev_tab_name:
            self.update_mapping_data_status(mapping_data_info, prev_tab_name)
        else:
            mapping_data_info["is_prev_mapping_data_updated"] = False
        return mapping_data_info

    def import_asw_arxml(self, args):
        print(args)
        pass

    def get_generate_configuration(self):
        enable_module_dict = {
            name: getattr(getattr(v, "DEFINITION_REF", ""), "valueOf_", "").split("/")[-1]
            for name, obj in data_management.autosar_bsw_class.items()
            for v in obj.find_nodes("ECUC-MODULE-CONFIGURATION-VALUES")
        }
        codegen_module_dict: dict = StudioCfgHandler.get_gen_or_validation_module_list(
            enable_module_dict, data_management.sys_target_dict, "support_generation"
        )
        enabled_codegen_module_list = data_management.sys_info_class.codegen_modules
        generation_limit = data_management.sys_info_class.generation_limit
        if codegen_module_dict == {}:
            logger.error("No codegen_moudle_list got!")
        return codegen_module_dict, enabled_codegen_module_list, generation_limit

    def common_post_process(self, is_rte_parse_new_dict, is_update_instance=True):
        other_input_info = {
            "codegen_autosar_dict": vcos_generator.init_codegen_autosar_dict(data_management),
            "sys_info_class": data_management.sys_info_class,
            "sys_target_dict": data_management.sys_target_dict,
            "is_rte_parse_new_dict": is_rte_parse_new_dict,
        }
        IbBswmdProcess.update_all_ib_bswmd(
            data_management.autosar_ib_class,
            data_management.autosar_bsw_class,
            data_management.autosar_asw_class,
            data_management.autosar_system_class,
            other_input_info,
        )
        update_rte_instances_and_os_resource_spinlock(
            data_management.autosar_bswmd_class,
            data_management.autosar_asw_class,
            data_management.autosar_bsw_class,
            data_management.autosar_ib_class,
        )
        if is_update_instance:
            try:
                self.task_mapping_func.update_instance()
            except Exception as e:
                logger.exception(e)

    # generate button
    def generate_modules(self, param, progress_signal):
        module_list = param["module_list"]
        progress_signal.emit("start generation with step of validation ...")
        data_management.sys_info_class.codegen_module_dict = module_list
        data_management.sys_info_class.codegen_modules = set(module_list)
        # 统一后处理操作
        self.common_post_process(True)
        progress_signal.emit("finish generation with step of validation ...")

        return self.validation_func.validate_module_with_result(module_list)

    # generate action
    def generate_vcos_c_code(self, codegen_module_list, other_info, progress_signal):
        # 如果Rte关键校验规则失败，则不生成任何的代码
        codegen_autosar_dict = vcos_generator.init_codegen_autosar_dict(data_management)
        data_management.sys_info_class.codegen_module_dict = codegen_module_list
        data_management.sys_info_class.codegen_modules = set(codegen_module_list)
        result = vcos_generator.generate_c_code(
            data_management.sys_info_class,
            codegen_autosar_dict,
            progress_signal=progress_signal,
            result_signal=None,
            other_info=other_info,
        )
        return result

    # validate button
    def validate_modules(self, param, progress_signal):
        progress_signal.emit("start validation ...")
        module_list = param["module_list"]
        # 统一后处理操作
        is_update_instance, _ = TaskMappingInstance.check_task_mapping_config(data_management.autosar_bsw_class)
        self.common_post_process(param["is_rte_parse_new_dict"], is_update_instance)
        count_log_dict, validation_result = self.validation_func.validate_module_with_result(module_list)
        for module, result in validation_result.items():
            if result is False:
                logger.ui_warning(f"Module {module} has validation errors, you can view them in Validation page.")
        progress_signal.emit("finish validation ...")

    def get_validation_configuration(self):
        return Validator.get_validation_configuration(data_management)

    def validation_vcos_c_code(self, args):
        print(args)
        pass

    def get_dependency_modules(self, module_list: Iterable[str]) -> list:
        # 获取依赖 module_list 中模块的所有模块
        module_dependency_dict = data_management.sys_target_dict["module_cfg"]
        dependecy_dict = defaultdict(list)
        for module_name in module_dependency_dict.keys():
            if module_name in data_management.sys_info_class.enable_modules:
                for dependent_module in module_dependency_dict[module_name]["dependency_list"]:
                    if dependent_module in module_list and module_name not in module_list:
                        dependecy_dict[dependent_module].append(module_name)

        return dependecy_dict

    def get_enable_modules(self) -> list:
        enable_module_list = []
        for value in data_management.sys_info_class.enable_modules:
            enable_module_list.append(value)
        return enable_module_list

    def update_vcos_service_arxml(self, progress_signal):
        sys_info_dict = vcos_generator.get_sys_info_dict(data_management.sys_info_class)
        config_path = sys_info_dict["config_path"]
        enabled_module_list = sys_info_dict.get("modules_info", {}).get("enabled_module_list", [])
        arxml_generator.generate_bsw_port_arxml(
            config_path, enabled_module_list, data_management.autosar_bsw_class, progress_signal
        )

        # update ib arxml
        other_input_info = {
            "codegen_autosar_dict": vcos_generator.init_codegen_autosar_dict(data_management),
            "sys_info_class": data_management.sys_info_class,
            "sys_target_dict": data_management.sys_target_dict,
            "is_rte_parse_new_dict": True,
        }
        IbBswmdProcess.update_all_ib_bswmd(
            data_management.autosar_ib_class,
            data_management.autosar_bsw_class,
            data_management.autosar_asw_class,
            data_management.autosar_system_class,
            other_input_info,
        )
        # Save SystemExtract.arxml before mrege
        tmp_se_path = os.path.join(config_path, "system/SystemExtract.arxml.new")
        se_obj = data_management.autosar_system_class["SystemExtract"]
        if se_obj:
            AutosarUtil.save_arxml(data_management.autosar_system_class["SystemExtract"], tmp_se_path)
        config_base_path = data_management.sys_info_class.config_base_path
        progress_signal.emit("Merge service arxml to system arxml")
        try:
            res, component_arxml_path_dict_info = ArxmlParseHandler.asw_arxml_merge(
                os.path.join(config_base_path, "asw"), config_base_path
            )
        except:
            raise
        finally:
            # Delete temp SystemExtract.arxml
            if os.path.exists(tmp_se_path):
                os.remove(tmp_se_path)
        logger.info("Merge service arxml completed")
        if "asw" not in res:
            logger.warning("Cannot get asw info")
        else:
            data_management.autosar_asw_class = res["asw"]
            system_arxml_manager = SystemArxmlsManager(data_management.autosar_bswmd_class)
            system_arxml_manager.update_flatextract_arxml_from_arxml_slot(
                data_management.autosar_asw_class, data_management.autosar_system_class
            )

        data_management.component_arxml_path_dict = {"asw_component": component_arxml_path_dict_info}

        return {"service"}

    @log_function_stats(["RTE", "Swc template", "UI生成SWC模板文件"])
    def generate_vcos_swc_template(self, swc_list, progress_signal):
        codegen_autosar_dict = vcos_generator.init_codegen_autosar_dict(data_management, True)
        return vcos_generator.generate_swc_template(
            data_management.sys_info_class, codegen_autosar_dict, swc_list, None
        )

    def get_vcos_swc_name_list(self):
        swc_appl_list = []
        if "Rte" in self.sys_info_obj.enable_modules:
            asw_autosar_dict = {"asw": data_management.autosar_asw_class}
            swc_appl_list = vcos_generator.get_swc_list_for_template_gereration(asw_autosar_dict)
        return swc_appl_list

    def close_vcos_project(self, args):
        print(args)
        pass

    def _save_vcos_project_config_file(self, args, progress_signal, module_list):
        """保存 VCOS 项目配置文件的内部方法。

        参数:
            args: 参数。
            progress_signal: 进度信号。
            module_list: 要保存的模块列表。
        """
        try:
            # get project path
            project_path = data_management.sys_info_class.project_path

            progress_signal.emit("save project arxml")
            config_path = data_management.sys_info_class.config_base_path

            progress_signal.emit("save ecuc arxml")
            ArxmlSaveHandler.save_bsw_ecuc_arxml(data_management.autosar_bsw_class, config_path, module_list)
            progress_signal.emit("save ib arxml")
            ArxmlSaveHandler.save_internal_behavior_arxml(data_management.autosar_ib_class, config_path, module_list)

            progress_signal.emit("save system arxml")
            ArxmlSaveHandler.save_system_dir_arxml(data_management.autosar_system_class, config_path)
            progress_signal.emit("save asw arxml")
            ArxmlSaveHandler.save_all_swc_components_arxml(data_management.autosar_asw_class, config_path)

            progress_signal.emit("save project config file")
            project_handler = ProjectHandler()
            remove_module_list = project_handler.get_remove_module_list(
                data_management.sys_info_class.enable_modules, data_management.enable_module_list
            )
            project_handler.update_bsw_module_cfg_path(data_management.sys_info_class)
            project_handler.remove_module_in_saving_project(remove_module_list, config_path)
            data_management.enable_module_list = data_management.sys_info_class.enable_modules

            # save project configuration
            self.project_file_parser.update_info_dict(data_management.sys_info_class)
            self.project_file_parser.save_file(project_path)
            result = ProjectXmlInfoHandler.save_xml_file(project_path, data_management.component_arxml_path_dict)
            if result is False:
                logger.debug("ProjectXmlInfoHandler.save_xml_file failed")
            self.bsw_editor_ui_func.save_schedule_table_ui_cfg()
            self.bsw_editor_ui_func.save_jitter_opt_history()
            project_path = project_path.replace("\\", "/")
            logger.ui_info(f"save project to {project_path}")
            return True
        except Exception as e:
            logger.ui_error(f"Failed to save project {project_path} config file: {e}")
            return False

    @log_function_stats(["VCOS工程管理", "保存工程"])
    def save_vcos_project_config_file(self, args, is_rte_parse_new_dict, progress_signal):
        """保存 VCOS 项目配置文件。"""
        start_time = time.time()
        try:
            self.common_post_process(is_rte_parse_new_dict)
        except Exception:
            logger.ui_warning(
                "Rte_ecuc.arxml and Os_ecuc.arxml update failed, Please resolve the verification error promptly"
            )
        module_list = data_management.sys_info_class.enable_modules
        self._save_vcos_project_config_file(args, progress_signal, module_list)
        end_time = time.time()
        elapsed_time = end_time - start_time
        round(elapsed_time, 3)
        return round(elapsed_time, 3)

    @log_function_stats(["代码生成", "增量代码生成保存"])
    def incremental_save_vcos_project_config_file(self, args, is_rte_parse_new_dict, progress_signal):
        """增量保存 VCOS 项目配置文件。"""
        self.common_post_process(is_rte_parse_new_dict)
        self.save_configuration_func.save_config_from_tmp_to_config(
            self.threading_lock,
            data_management.autosar_asw_class,
            data_management.autosar_bsw_class,
            data_management.autosar_system_class,
            data_management.autosar_ib_class,
            data_management.sys_info_class,
        )

    def codegen_save_vcos_project_config_file(self, args, is_rte_parse_new_dict, progress_signal):
        if data_management.sys_info_class.incremental_generation:
            self.incremental_save_vcos_project_config_file(args, is_rte_parse_new_dict, progress_signal)
        else:
            self.save_vcos_project_config_file(args, is_rte_parse_new_dict, progress_signal)

    def load_studio_plugin_config_file_action(self, system_path, type):
        """
        Instance class of SysInfoClass to save paras delivering from New Project UI
        """
        self.sys_info_obj = SysInfoClass()
        # ProjectFileParser提供工程文件配置解析
        self.project_file_parser.init_empty_project(system_path)
        """if return false """
        # 从ProjectFileParser解析或者构造的配置设值sys_info_obj
        self.project_file_parser.init_sys_info(self.sys_info_obj, system_path)
        data_management.sys_info_class = self.sys_info_obj
        data_management.sys_target_dict = data_management.sys_info_class.system_target_info
        compiler_target_list: dict = StudioCfgHandler.get_target_compiler(data_management.sys_target_dict)

        return compiler_target_list

    def update_vcos_project_config_file(self):
        """
        Instance class of SysInfoClass to save paras delivering from New Project UI
        """
        # ProjectFileParser提供工程文件配置解析
        """if return false """
        # 从ProjectFileParser解析或者构造的配置设值sys_info_obj
        reslut = self.project_file_parser.update_target_info(self.sys_info_obj)
        if reslut is None:
            return None
        data_management.sys_info_class.all_modules = self.project_file_parser.get_all_module_list(
            data_management.sys_target_dict
        )
        data_management.all_module_list = data_management.sys_info_class.all_modules
        data_management.autosar_system_class = ArxmlParseHandler.parse_system_dir_arxml(BASE_ARXML_PATH)

        # New project时获取target与compiler信息
        compiler_target_list: dict = StudioCfgHandler.get_target_compiler(data_management.sys_target_dict)
        if data_management.sys_info_class.target in data_management.sys_target_dict["validate"]["ignore_option"]:
            data_management.sys_target_dict["validate"]["ignore_option"] = data_management.sys_target_dict["validate"][
                "ignore_option"
            ][data_management.sys_info_class.target]
        data_management.sys_info_class.system_target_info.update(data_management.sys_target_dict)
        return compiler_target_list

    @log_function_stats(["BSW Editor", "配置文件解析和导入", "Ecuc和ASW arxml文件", "Ecuc arxml导出"])
    def export_ecuc_arxml_file(self, added_mudole_list: list, file_path: str, progress_signal):
        # 已经配置的所有模块信息：data_management.autosar_bsw_class
        module_autosar_obj_list = []
        for module_name in added_mudole_list:
            if module_name not in data_management.autosar_bsw_class.keys():
                logger.warning(f"Cannot export {module_name} bsw info")
                continue
            module_autosar_obj_list.append(data_management.autosar_bsw_class[module_name])
        progress_signal.emit("Merging all ecuc module configuration...")
        merged_ecuc_autosar_obj = AutosarUtil.merge_module_arxml(module_autosar_obj_list)
        progress_signal.emit("Saving bsw arxml file...")
        ArxmlSaveHandler.save_all_bsw_ecuc_arxml(merged_ecuc_autosar_obj, file_path)

    def validate_ecuc_and_asw_arxml_files(self, file_path_list: list, progress_signal):
        """判断一个 arxml 是否是一个可以被导入的文件"""
        valid_import_arxml_obj = {}

        for file_path in file_path_list:
            if file_path is None or os.path.exists(file_path) is False:
                logger.warning(f"file <{file_path}> is not exist, please check it.")
                continue
            try:
                progress_signal.emit(f"Varifing the {os.path.basename(file_path)} ...")
                file_obj = AutosarUtil.parse_arxml(file_path)
                if self.import_files_logic.judge_file_is_ecuc_arxml(file_obj):
                    valid_import_arxml_obj.update({file_path: {"arxml_obj": file_obj, "file_type": "ecuc"}})
                elif self.import_files_logic.judge_file_is_asw_arxml(file_obj):
                    valid_import_arxml_obj.update({file_path: {"arxml_obj": file_obj, "file_type": "asw"}})
                else:
                    logger.warning(f"{file_path} is illegal to import!")
            except Exception as e:
                raise Exception(f"parse <{file_path}> failed!") from e
        return valid_import_arxml_obj

    def parse_files_ecuc_to_module_dict(self, need_parsed_file_dict: dict, parsed_module_dict, progress_signal):
        sys_info_obj: SysInfoClass = data_management.sys_info_class
        unsupported_module_list = []
        module_cfg = getattr(data_management, "sys_target_dict", {}).get("module_cfg", {})

        for file_path, arxml_info in need_parsed_file_dict.items():
            progress_signal.emit(f"Parsing {os.path.basename(file_path)}...")
            bsw_modules_info = AutosarUtil.parse_bsw_module_class_list(arxml_info)
            # 字符串 empty "" 统一为 None，防止冲突检测出现问题
            for module_name, ecuc_obj in bsw_modules_info.items():
                # save unsupported_mcal_module(mod file not exist) list
                if module_cfg.get(module_name, {}).get("is_mcal", False):
                    if not ArxmlParseHandler.check_mod_files_exist(sys_info_obj.plug_in_bswmd_path, [module_name]):
                        unsupported_module_list.append(module_name)
                # update ecuc module obj with default value
                if module_name not in data_management.autosar_bswmd_class:
                    continue
                ecuc_updater = EcucArxmlUpdater(data_management.autosar_bswmd_class[module_name], ecuc_obj)
                ecuc_updater.update_ecuc_with_default_value()

            for unsupported_module in unsupported_module_list:
                del bsw_modules_info[unsupported_module]

            parsed_module_dict.update({file_path: bsw_modules_info})

        return parsed_module_dict

    def judge_config_has_diff(self, module_name, new_ecuc_obj) -> bool:
        new_ecuc_cfg = new_ecuc_obj.AR_PACKAGES.AR_PACKAGE[0].ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES[0]
        curr_module_ecuc_obj = data_management.autosar_bsw_class[module_name]
        old_ecuc_cfg = curr_module_ecuc_obj.AR_PACKAGES.AR_PACKAGE[0].ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES[0]
        comparator = ConfigComparator(old_ecuc_cfg, new_ecuc_cfg)
        comparator.config_comparator()
        return comparator

    def copy_file(self):
        # copy PlatformTypes_AR4.arxml
        destination_file = os.path.join(
            data_management.sys_info_class.config_base_path, "autosar", "PlatformTypes_AR4.arxml"
        )
        source_file = os.path.join(
            data_management.sys_info_class.studio_path,
            "func_module",
            "module_management",
            "base_config",
            "base_arxml",
            "autosar",
            "PlatformTypes_AR4.arxml",
        )
        result = ProjectHandler.copy_file(source_file, destination_file)
        if result is False:
            logger.error("copy PlatformTypes_AR4.arxml failed")

        # copy makefile_config.mk
        destination_file = os.path.join(data_management.sys_info_class.application_path)
        source_file = os.path.join(data_management.sys_info_class.studio_path, "vcos_tools/make_support")
        result = ProjectHandler.copy_dir(source_file, destination_file)
        if result is False:
            logger.error("copy make_support failed")

        # copy bat
        destination_dir = os.path.join(data_management.sys_info_class.application_path, "script")
        source_dir = os.path.join(data_management.sys_info_class.studio_path, "script_demo/cmd_demo")
        result = ProjectHandler.copy_cur_dir(source_dir, destination_dir)
        if result is False:
            logger.error("copy bat failed")

        return True

    @log_function_stats(["VCOS工程管理", "工程另存为"])
    def save_as_vcos_project_config_file(self, progress_signal):
        # step1：创建另存为工程目录
        progress_signal.emit("creating and copying vcos project's directory")
        self.project_file_parser.create_copy_dir(data_management)
        # step2：适配工程文件以及另存为工程的相关文件
        progress_signal.emit("synchronizing project's information")
        self.project_file_parser.modify_vcos_project(data_management)
        self.project_file_parser.modify_project(data_management)
        # step3：保存另存为工程的工程文件
        progress_signal.emit("saving vcos project's file")
        self.project_file_parser.update_info_dict(data_management.save_as_sys_info_class)
        self.project_file_parser.save_file(data_management.save_as_sys_info_class.project_path)

    def update_save_as_vcos_prj(self, save_as_sys_info_class):
        data_management.save_as_sys_info_class = save_as_sys_info_class

    def show_vcos_project_information(self):
        """
        获取工程配置支持Project Setting配置显示(中间变量)
        """
        info: dict = {}
        info.update({"project": data_management.sys_info_class.project})
        info.update({"project_path": data_management.sys_info_class.project_path})
        info.update({"config_base_path": data_management.sys_info_class.config_base_path})
        info.update({"application_path": data_management.sys_info_class.application_path})
        info.update({"internal_behavior_path": data_management.sys_info_class.internal_behavior_path})
        info.update({"log_path": data_management.sys_info_class.log_path})
        info.update({"gendata_path": data_management.sys_info_class.gendata_path})
        info.update({"swc_template_path": data_management.sys_info_class.swc_template_path})
        info.update({"bswcallout_path": data_management.sys_info_class.bswcallout_path})
        info.update({"user_plugin_output_path": data_management.sys_info_class.user_plugin_output_path})
        info.update({"service_component_path": data_management.sys_info_class.service_component_path})
        info.update({"compiler_path": data_management.sys_info_class.compiler_path})
        info.update({"compiler": data_management.sys_info_class.compiler})
        info.update({"target": data_management.sys_info_class.target})

        info.update({"mcal_path": data_management.sys_info_class.mcal_path})
        info.update({"mcal_gendata_path": data_management.sys_info_class.mcal_gendata_path})
        info.update({"system_path": data_management.sys_info_class.system_path})
        info.update({"mcal_version": data_management.sys_info_class.mcal_version})
        target_compiler_dict: dict = StudioCfgHandler.get_target_compiler(data_management.sys_target_dict)
        project_info = {"project_setting_action": info, "target_compiler_list": target_compiler_dict}
        return project_info

    def project_update(self, args, type, progress_signal):
        """
        更新Project Setting界面返回的工程配置,并更新sys_info_class
        """
        info: dict = args
        # 打开工程保存修改更新配置
        data_management.sys_info_class.project = info["project"]
        data_management.sys_info_class.project_path = info["project_path"]
        data_management.sys_info_class.config_base_path = info["config_base_path"]
        data_management.sys_info_class.application_path = info["application_path"]
        data_management.sys_info_class.internal_behavior_path = info["internal_behavior_path"]
        data_management.sys_info_class.log_path = info["log_path"]
        data_management.sys_info_class.gendata_path = info["gendata_path"]
        data_management.sys_info_class.swc_template_path = info["swc_template_path"]
        data_management.sys_info_class.bswcallout_path = info["bswcallout_path"]
        data_management.sys_info_class.user_plugin_output_path = info["user_plugin_output_path"]
        data_management.sys_info_class.service_component_path = info["service_component_path"]
        data_management.sys_info_class.compiler_path = info["compiler_path"]
        data_management.sys_info_class.compiler = info["compiler"]
        data_management.sys_info_class.target = info["target"]
        data_management.sys_info_class.mcal_path = info["mcal_path"]
        data_management.sys_info_class.mcal_gendata_path = info["mcal_gendata_path"]
        data_management.sys_info_class.system_path = info["system_path"]
        data_management.sys_info_class.mcal_version = info["mcal_version"]
        data_management.sys_info_class.studio_path = info["studio_path"]
        data_management.cfg_info_dict.update({"target": data_management.sys_info_class.target})

        if type == "NewProject":
            self.copy_file()
            result = self.update_vcos_project_config_file()
            if result is None:
                return None, None
        self.project_file_lock.add_file_lock(info["project_path"])
        self.load_secondary_menu_cfg()
        self.load_init_function_settings_by_target()
        return data_management.autosar_bswmd_class, data_management.autosar_bsw_class

    def parse_rte_codegen_dict(self):
        asw_dict = {
            "asw": data_management.autosar_asw_class,
            "FlatExtract": data_management.autosar_system_class["FlatExtract"],
        }
        cfg_dict = {"asw": "", "rte": {}, "bsw": {}, "dbc": [], "ldf": [], "cdd": {}, "eb": {}}
        rte_parser.get_rte_codegen_dict(
            asw_dict,
            data_management.autosar_bsw_class,
            data_management.autosar_system_class,
            data_management.autosar_ib_class,
            cfg_dict,
        )

    def get_vcos_version(self):
        return VCOS_VERSION

    def load_secondary_menu_cfg(self):
        folder_path = os.path.join(data_management.sys_info_class.system_path, "system_secondary")
        self.load_json_files_from_folder(folder_path)

    def load_json_files_from_folder(self, folder_path):
        json_files_data = {}
        for root, _, files in os.walk(folder_path):
            for filename in files:
                if filename.endswith(".json"):
                    file_path = os.path.join(root, filename)
                    with open(file_path, "r", encoding="utf-8") as json_file:
                        try:
                            data = json.load(json_file)  # 加载 JSON 文件内容
                            json_files_data.update(data)  # 将内容添加到列表中
                        except json.JSONDecodeError as e:
                            print(f"Error decoding JSON from file {filename}: {e}")
        data_management.sys_secondary_cfg_dict = json_files_data

    def delete_file_lock(self):
        self.project_file_lock.delete_file_lock()

    def add_file_lock(self, project_file_path):
        from ui_adaptor.ui_interaction.worker import Task

        if Task.is_debug:
            return True
        result = self.project_file_lock.add_file_lock(project_file_path)
        return result

    def get_secondary_menu_cfg(self):

        return data_management.sys_secondary_cfg_dict.get("secondary_menu_cfg", {})

    def get_module_dependency_tab_list(self):

        return data_management.sys_secondary_cfg_dict.get("module_dependency_tab_list", {})

    def cbk_get_vfb_trace_info(self):
        return rte_parser.get_vfb_trace_info(
            data_management.autosar_bsw_class, self.task_mapping_func.get_runnable_data()
        )

    def import_os_cfg(self, file_name, main_window, over_view_ui, progress_signal):
        """导入OS自动配置"""
        OsConfigureUIFunc.import_os_cfg(file_name, main_window, over_view_ui, progress_signal)

    def export_os_cfg(self, file_name, progress_signal):
        """导出OS现有配置"""
        OsConfigureUIFunc.export_os_cfg(file_name, progress_signal)

    def save_system_arxml_arxml(self):
        config_path = data_management.sys_info_class.config_base_path
        ArxmlSaveHandler.save_system_dir_arxml(data_management.autosar_system_class, config_path)

    def periodic_save_configuration(self, type=False):
        self.save_configuration_func.periodic_save_configuration(
            self.threading_lock,
            data_management.autosar_asw_class,
            data_management.autosar_bsw_class,
            data_management.autosar_system_class,
            data_management.autosar_ib_class,
            data_management.sys_info_class,
        )

    def check_save_project_thread(self, progress_signal, type=False):
        progress_signal.emit("Cleaning and processing data")
        self.save_configuration_func.check_thread_status()

    def get_periodic_save_time(self):
        general_json_path = GENERAL_JSON_PATH
        if not os.path.exists(general_json_path):
            return None

        with open(general_json_path) as f:
            self.general_data = json.load(f)
        if not self.general_data:
            return None
        return self.general_data

    def set_periodic_save_time(self, data):
        general_json_path = GENERAL_JSON_PATH
        # 写入JSON文件
        if not self.general_data:
            return
        self.general_data.update(data)

        with open(general_json_path, "w", encoding="utf-8") as json_file:
            json.dump(self.general_data, json_file, ensure_ascii=False, indent=4)
        pass
