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
from func_module.import_file.dbc_importer import DbcImporter
from func_module.import_file.ldf_importer import LdfImporter
from func_module.import_file.excel_importer import ExcelImporter
from func_module.project_management.sys_info_class import SysInfoClass
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlParseHandler
from func_module.module_management.arxml_handler.system.system_arxmls_manager import SystemArxmlsManager
from func_module.mapping.data_mapping import DataMapping
from cmd_adaptor.data_management import data_management
from cmd_adaptor.func_logic_layer.load_save_project import LoadAndSaveProject


class ImportDbcLdfHandler:

    def __init__(self) -> None:
        pass

    @classmethod
    def reload_mcal_arxml(cls):
        if data_management.cfg_info_dict["eb"]:
            return
        file_path = data_management.sys_info_class.eb_arxml
        if os.path.isfile(file_path):
            mcal_arxml = ArxmlParseHandler.parse_mcal_arxml(file_path)
            if len(mcal_arxml.AR_PACKAGES.AR_PACKAGE) < 10:
                return
            mcal_arxml_dict = AutosarUtil.to_bsw_dict(mcal_arxml)
            data_management.cfg_info_dict["eb"] = {"arxml": mcal_arxml_dict}

    @classmethod
    def cmd_args_to_sys_info_dict(cls, file_list, node_selected):
        dbc_sys_info = {"num": 0, "list": {}}
        ldf_sys_info = {"num": 0, "list": {}}

        for file_path in file_list:
            file_name = os.path.basename(file_path)
            if file_name.endswith(".dbc"):
                dbc_sys_info["list"][file_name] = {
                    "path": file_path,
                    "node_selected": node_selected,
                    "node_list": [node_selected],
                }
            elif file_name.endswith(".ldf"):
                ldf_sys_info["list"][file_name] = {
                    "path": file_path,
                    "node_selected": node_selected,
                    "node_list": [node_selected],
                }
        dbc_sys_info["num"] = len(dbc_sys_info["list"])
        ldf_sys_info["num"] = len(ldf_sys_info["list"])
        return dbc_sys_info, ldf_sys_info

    @classmethod
    def parse_excel_files(cls, excel_list):
        excel_importer = ExcelImporter()
        excel_contents: dict = excel_importer.parse_excel(excel_list)

        excel_files_path = {}
        if excel_contents:
            data_management.cfg_info_dict.pop("excel", None)
            data_management.cfg_info_dict.update({"excel": excel_contents})

        for excel_path in excel_list:
            excel_name = os.path.basename(excel_path)
            # Record excel which has been successfully parsed
            if excel_name in excel_contents:
                excel_files_path.update({excel_name: excel_path})
        sys_info_obj: SysInfoClass = data_management.sys_info_class
        sys_info_obj.excel = excel_files_path

    @classmethod
    def import_dbc_ldf(cls, file_list, node_selected, is_add_channel_name=False):
        data_management.sys_info_class.is_add_channel_name = is_add_channel_name

        data_management.sys_info_class.dbc, data_management.sys_info_class.ldf = cls.cmd_args_to_sys_info_dict(
            file_list, node_selected
        )

        excel_list = []
        for file in file_list:
            if file.endswith(file):
                excel_list.append(file)

        cls.parse_excel_files(excel_list)

        dbc_importer = DbcImporter(
            data_management.sys_info_class,
            data_management.autosar_bsw_class,
            data_management.autosar_bswmd_class,
            data_management.autosar_ib_class,
            data_management.autosar_system_class,
            data_management.cfg_info_dict,
            data_management.sys_target_dict,
        )
        ldf_importer = LdfImporter(
            data_management.sys_info_class,
            data_management.autosar_bsw_class,
            data_management.autosar_bswmd_class,
            data_management.autosar_ib_class,
            data_management.autosar_system_class,
            data_management.cfg_info_dict,
            data_management.sys_target_dict,
        )

        dbc_importer.apply_import()
        ldf_importer.apply_import()

        system_arxml_manager = SystemArxmlsManager(data_management.autosar_bswmd_class)
        system_arxml_manager.update_com_stack_arxml_from_dbc_ldf(
            data_management.cfg_info_dict,
            data_management.autosar_bsw_class,
            data_management.autosar_system_class,
            "dbc_or_ldf",
            is_add_channel_name,
        )
        DataMapping.update_flatextract_data_mapping_from_files_import(
            data_management.autosar_asw_class,
            data_management.autosar_system_class,
            data_management.autosar_bsw_class.get("Com", None),
        )

    def execute_auto_import_dbc_ldf(self, project_file_path, file_list, node_selected, is_add_channel_name=False):
        LoadAndSaveProject.import_dbc_ldf_load_project(project_file_path)
        self.import_dbc_ldf(file_list, node_selected, is_add_channel_name=is_add_channel_name)
        LoadAndSaveProject.import_dbc_ldf_save_project()
