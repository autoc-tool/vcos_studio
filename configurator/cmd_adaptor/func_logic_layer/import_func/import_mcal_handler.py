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
from cmd_adaptor.data_management import data_management as data
from cmd_adaptor.func_logic_layer.load_save_project import LoadAndSaveProject
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlParseHandler
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.base_logger import logger
from func_module.health_monitor.perf_record import log_function_stats
from func_module.module_management.arxml_handler.mcal_ecuc.import_ecuc_cfg import EcucCfgImport


class ImportMcalHandler:

    def __init__(self) -> None:
        pass

    @classmethod
    @log_function_stats(["BSW Editor", "配置文件解析和导入", "命令行导入mcal arxml"])
    def import_mcal_arxml(cls, mcal_arxml_file_path, selected_mcal_modules_list_from_cmd=[]):
        need_update_ecuc_dcit = cls.get_all_module_cfg_of_mcal_arxml(
            mcal_arxml_file_path, selected_mcal_modules_list_from_cmd
        )

        EcucCfgImport.update_ecuc_autosar_dict(data, need_update_ecuc_dcit)

    def get_all_module_cfg_of_mcal_arxml(cls, file_path, selected_mcal_modules_list_from_cmd=[]):

        need_import_module_dict = {file_path: {}}
        # 1. 解析mcal文件
        if not file_path or not os.path.exists(file_path):
            logger.warning("You did not select the mcal arxml file or path does not exist, please select.")
            return None
        parse_res = ArxmlParseHandler.parse_mcal_arxml(file_path)
        ecuc_module_dict = AutosarUtil.parse_bsw_module_class_list(parse_res)

        if not selected_mcal_modules_list_from_cmd:
            selected_mcal_modules_list_from_cmd = list(ecuc_module_dict.keys())

        # remove unsupported modules
        unsupported_modules = []
        for module in selected_mcal_modules_list_from_cmd:
            if not ArxmlParseHandler.check_mod_files_exist(data.sys_info_class.plug_in_bswmd_path, [module]):
                logger.warning("module: {module} does not support import.")
                unsupported_modules.append(module)
        selected_mcal_modules_list_from_cmd = list(
            filter(lambda x: x not in unsupported_modules, selected_mcal_modules_list_from_cmd)
        )

        for module_name in selected_mcal_modules_list_from_cmd:
            if module_name in ecuc_module_dict:
                need_import_module_dict[file_path][module_name] = {"ecuc_module_obj": ecuc_module_dict[module_name]}

        return need_import_module_dict

    def execute_auto_import_mcal_arxml(self, project_file_path, mcal_arxml_file_path, selected_mcal_module_list=None):
        LoadAndSaveProject.import_mcal_load_project(project_file_path)
        self.import_mcal_arxml(mcal_arxml_file_path, selected_mcal_module_list)
        LoadAndSaveProject.import_dbc_ldf_save_project()
