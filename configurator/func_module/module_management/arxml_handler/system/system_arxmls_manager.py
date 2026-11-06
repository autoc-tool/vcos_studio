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
from basic_func_module.base_common.singleton import Singleton
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlParseHandler
from func_module.module_management.arxml_handler.system.communication_arxml_manager import CommunicationArxmlManager
from func_module.module_management.arxml_handler.system.flatextract_arxml_manager import FlatExtractArxmlManager
from func_module.module_management.arxml_handler.system.initial_arxmls_manager import (
    InitialArxmlManager,
    COM_STACK_MODULES,
)
from func_module.health_monitor.logger import logger

CUR_FILE_PATH = os.path.dirname(os.path.realpath(__file__))
DIAG_STACK_MODULES = ["Dcm", "Dem", "NvM"]


class SystemArxmlsManager(Singleton):
    """
    Manage Communication, FlatExtract...
    """

    def __init__(self, mod_autosar_dict, sys_info_class=None, selected_mcal_modules_list=None):
        self.selected_mcal_modules_list = selected_mcal_modules_list
        self.sys_info_class = sys_info_class
        self.communication_arxml_manager = CommunicationArxmlManager()
        self.initial_arxmls_manager = InitialArxmlManager(
            mod_autosar_dict, sys_info_class, self.selected_mcal_modules_list
        )

    def set_selected_mcal_modules_list(self, selected_mcal_modules_list, sys_info_class):
        self.initial_arxmls_manager.set_selected_mcal_modules_list(selected_mcal_modules_list, sys_info_class)
        self.selected_mcal_modules_list = selected_mcal_modules_list
        self.sys_info_class = sys_info_class

    def update_communication_arxml_from_dbc_slot(self, dic):
        self.communication_arxml_manager.update_communication_info_from_dbc(dic)

    def update_communication_arxml_from_ldf_slot(self, dic):
        self.communication_arxml_manager.updata_communication_info_from_add_ldf(dic)

    @classmethod
    def update_flatextract_arxml_from_arxml_slot(cls, asw_autosar_dict, system_autosar_dict):
        FlatExtractArxmlManager.update_flatextract_info_from_asw_arxml(asw_autosar_dict, system_autosar_dict)

    @classmethod
    def get_communication_all_system_signal_mapping_info(cls, autosar_communication):
        return CommunicationArxmlManager.get_all_system_signal_mapping_info_cls(autosar_communication)

    @classmethod
    def get_all_data_mappings(cls, autosar_flatextract):
        return FlatExtractArxmlManager.get_all_data_mappings_from_flatextract(autosar_flatextract)

    @classmethod
    def paser_signal_mapping(cls, mapping_obj):
        return FlatExtractArxmlManager.paser_sender_receiver_to_signal_mapping(mapping_obj)

    @classmethod
    def paser_signal_group_mapping(cls, mapping_obj):
        return FlatExtractArxmlManager.paser_sender_receiver_to_signal_group_mapping(mapping_obj)

    def update_com_stack_arxml_from_dbc_ldf(
        self, cfg_dict, ecuc_autosar_dict, system_autosar_dict, import_file_type, is_add_channel_name=False
    ):
        """
        dbc ldf import slot: 负责通信协议栈相关initial和ecuc arxml的更新时序
        """
        self._update_initial_and_ecuc_arxml(
            cfg_dict, ecuc_autosar_dict, system_autosar_dict, import_file_type, is_add_channel_name
        )

    def reload_dbc(
        self,
    ):
        if len(self.cfg_info_dict["dbc"]):
            return None
        import_files_list = []
        dbc_file_config = self.sys_info_dict["path"]["config_file_path"]["dbc"]
        if "list" in dbc_file_config.keys():
            for key, value in dbc_file_config["list"].items():
                import_file = {}
                import_file["file_name"] = key
                import_file["node_selected"] = value["node_selected"]
                import_file["file_path"] = value["path"]
                import_files_list.append(import_file)
        ldf_file_config = self.sys_info_dict["path"]["config_file_path"]["ldf"]
        if "list" in ldf_file_config.keys():
            for key, value in ldf_file_config["list"].items():
                import_file = {}
                import_file["file_name"] = key
                import_file["node_selected"] = value["node_selected"]
                import_file["file_path"] = value["path"]
                import_files_list.append(import_file)
        InitialArxmlManager.combine_cfg_dict_dbcs_nm_message(
            self.import_dbc_and_ldf_paser._parser_all_import_files(import_files_list)
        )

    def reload_mcal_arxml(self):
        file_path = self.sys_info_dict["path"]["config_file_path"]["eb_arxml"]
        if os.path.isfile(file_path):
            mcal_arxml = AutosarUtil.parse_arxml(file_path)
            if len(mcal_arxml.AR_PACKAGES.AR_PACKAGE) < 10:
                return
            mcal_arxml_dict = AutosarUtil.to_bsw_dict(mcal_arxml)
            self.cfg_info_dict["eb"]["arxml"] = mcal_arxml_dict

    def _update_initial_and_ecuc_arxml(
        self, cfg_dict, ecuc_autosar_dict, system_autosar_dict, import_file_type, is_add_channel_name
    ):
        # self.reload_mcal_arxml()
        # self.reload_dbc()
        logger.debug("Update initial arxml...")
        initial_arxml_new = self.initial_arxmls_manager.update_initial_arxml_from_dbc_ldf_mcal(
            cfg_dict, ecuc_autosar_dict, system_autosar_dict, import_file_type
        )
        system_autosar_dict["Initial"] = initial_arxml_new
        logger.debug("Update communication/systemextract arxml...")
        if "dbc_or_ldf" == import_file_type:
            communication_arxml, sysem_extract_arxml = (
                self.communication_arxml_manager.update_communication_arxml_from_dbc_ldf(
                    cfg_dict, system_autosar_dict, is_add_channel_name
                )
            )
            system_autosar_dict["Communication"] = communication_arxml
            system_autosar_dict["SystemExtract"] = sysem_extract_arxml

    def remove_initial_autosar_module(self, module_name, system_autosar_dict, base_arxml_path):
        """
        remove 模块时移除initial中该模块的数据
        """
        initial_arxml_base = None
        module_container_base = None
        system_autosar_dict_key = "Initial"

        if module_name in COM_STACK_MODULES:
            system_autosar_dict_key = "Initial"
            initial_arxml_base = ArxmlParseHandler.parse_initial_arxml(base_arxml_path)
        elif module_name in DIAG_STACK_MODULES:
            system_autosar_dict_key = "DiagnosticsDescriptionData"
            initial_arxml_base = ArxmlParseHandler.parse_diagnostics_description_data_arxml(base_arxml_path)

        initial_autosar = system_autosar_dict[system_autosar_dict_key]
        if initial_autosar is None:
            return False

        module_path = f"/InitialEcuC/{module_name}"
        module_container = initial_autosar.find(module_path)
        if initial_arxml_base is not None:
            module_container_base = initial_arxml_base.find(module_path)
        if module_container is None:
            return False
        if hasattr(module_container.get_parent(), "ECUC_MODULE_CONFIGURATION_VALUES") and isinstance(
            module_container.get_parent().ECUC_MODULE_CONFIGURATION_VALUES, list
        ):
            module_list = module_container.get_parent().ECUC_MODULE_CONFIGURATION_VALUES
            if module_container in module_list:
                idx = module_list.index(module_container)
            else:
                return False
            AutosarUtil.remove_container_value(module_list, module_container)
            if module_container_base is not None:
                module_list.insert(idx, module_container_base)
            system_autosar_dict[system_autosar_dict_key] = AutosarUtil.update_autosar(initial_autosar)
        return True
