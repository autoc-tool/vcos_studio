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
from cmd_adaptor.cmd_interaction.cmd_logger import logger
from func_module.health_monitor.perf_record import log_function_stats
from cmd_adaptor.data_management import data_management
from cmd_adaptor.func_logic_layer.load_save_project import LoadAndSaveProject
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlParseHandler
from cmd_adaptor.func_logic_layer.mapping_func.task_mapping_cmd_func import TaskMappingCmdFunc
from basic_func_module.file_validation.arxml_validator import ArxmlFileValidator
from func_module.module_management.base_config import BASE_CONFIG_PATH

SCHEMA_XSD_FILE = os.path.join(BASE_CONFIG_PATH, "autosar_cfg/AUTOSAR_00046.xsd")


class ImportAswHandler:

    def __init__(self) -> None:
        pass

    @classmethod
    def load_asw_arxml_from_import(cls, config_path, asw_dir_list):
        asw_autosar_dict, component_arxml_path_dict_info = ArxmlParseHandler.asw_arxml_merge(asw_dir_list, config_path)
        return asw_autosar_dict, component_arxml_path_dict_info

    @classmethod
    @log_function_stats(["BSW Editor", "配置文件解析和导入", "Ecuc和ASW arxml文件", "命令行导入ASW arxml"])
    def import_asw(cls, asw_dir):
        cls.arxml_file_validator = ArxmlFileValidator()
        cls.arxml_file_validator.set_arxml_schema(SCHEMA_XSD_FILE)
        config_path = data_management.sys_info_class.config_base_path
        asw_autosar_dict, component_arxml_path_dict_info = cls.load_asw_arxml_from_import(config_path, asw_dir)
        if asw_autosar_dict is None:
            logger.error("asw_autosar_dict is None")
            return False
        if "asw" not in asw_autosar_dict:
            logger.error("Cannot get asw info")
            return False

        data_management.component_arxml_path_dict = {"asw_component": component_arxml_path_dict_info}

        data_management.autosar_asw_class = asw_autosar_dict["asw"]
        TaskMappingCmdFunc.update_task_mapping_instance()
        return True

    def execute_auto_import_asw(self, project_file_path, asw_dir_list):
        autosar_system_class, sys_info_obj = LoadAndSaveProject.import_asw_load_project(project_file_path)
        data_management.sys_info_class.config_base_path = sys_info_obj.config_base_path

        self.import_asw(asw_dir_list)
        LoadAndSaveProject.import_asw_save_project()
        logger.info("finish execute import asw ...")
