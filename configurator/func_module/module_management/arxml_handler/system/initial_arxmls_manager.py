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
from copy import deepcopy
from basic_func_module.base_common.load_plug_in import LoadPlugIn
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from func_module.health_monitor.logger import logger
from func_module.module_management.arxml_handler.system.initial_selected_mcal_modules_ecuc_parser import (
    InitialSelectedMcalModulesEcucParser,
)
from func_module.module_management.arxml_handler.com_stack_ecuc.com_stack_ecuc_base_class import ComStackEcucBaseClass
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlParseHandler
from func_module.module_management.base_config import BASE_CONFIG_PATH

BASE_ARXML_PATH = os.path.join(BASE_CONFIG_PATH, "base_arxml")

COM_STACK_MODULES = ["EcuC", "Com", "ComM", "PduR", "CanIf", "CanTp", "LinIf", "LinSM", "CanNm", "CanSM", "Nm"]
CAN_NM_RX_COMBINE_MODULES = ["EcuC", "CanIf", "CanNm"]


class InitialArxmlManager:

    def __init__(self, mod_autosar_dict, sys_info_class=None, selected_mcal_modules_list=None):
        self.selected_mcal_modules_list = selected_mcal_modules_list
        self.sys_info_class = sys_info_class
        self.ar_packages = {}
        self._initial_managers_init(mod_autosar_dict)
        self._ecuc_managers_init()

    def set_selected_mcal_modules_list(self, selected_mcal_modules_list, sys_info_class):
        self.initial_managers["MCALOTHERS"].set_selected_mcal_modules_list(selected_mcal_modules_list, sys_info_class)
        self.selected_mcal_modules_list = selected_mcal_modules_list
        self.sys_info_class = sys_info_class

    def _ecuc_managers_init(self):
        self.ecuc_managers = dict.fromkeys(COM_STACK_MODULES)
        for module_name in self.ecuc_managers.keys():
            try:
                package_path = f"config_plug_in.update_ecuc.{module_name.lower()}_ecuc_manager"
                module_obj = LoadPlugIn.load_module(module_name, package_path)
                if module_obj is None:
                    logger.debug(f"Module {module_name} not support update ecuc")
                    continue
                validate_rule_class = getattr(module_obj, f"{module_name}EcucManager")
                self.ecuc_managers[module_name] = validate_rule_class()
            except Exception as e:
                logger.ui_error(f"Module {module_name} update ecuc error! {e}")
        self.ecuc_managers["MCALOTHERS"] = ComStackEcucBaseClass("MCALOTHERS")

    def _initial_managers_init(self, mod_autosar_dict):
        self.initial_managers = dict.fromkeys(COM_STACK_MODULES)
        for module_name in self.initial_managers:
            try:
                package_path = f"config_plug_in.update_initial.initial_{module_name.lower()}_ecuc_parser"
                module_obj = LoadPlugIn.load_module(module_name, package_path)
                if module_obj is None:
                    logger.debug(f"Module {module_name} not support update ecuc")
                    continue
                validate_rule_class = getattr(module_obj, f"Initial{module_name}EcucParser")
                self.initial_managers[module_name] = validate_rule_class(mod_autosar_dict)
            except Exception as e:
                logger.ui_error(f"Module {module_name} update ecuc error! {e}")
        self.initial_managers["MCALOTHERS"] = InitialSelectedMcalModulesEcucParser(
            mod_autosar_dict, self.selected_mcal_modules_list, self.sys_info_class
        )

    def __update_can_multi_core_info(self, ecuc_autosar_dict, cfg_dict):
        if (
            ("ResourceM" not in ecuc_autosar_dict and "ResourceManager" not in ecuc_autosar_dict)
            or "Can" not in ecuc_autosar_dict
            or not cfg_dict
        ):
            return
        module_obj = LoadPlugIn.load_module("CanIf", "config_plug_in.update_initial.initial_can_common_ecuc_parser")
        InitialCanCommonEcucParser = getattr(module_obj, "InitialCanCommonEcucParser")
        try:
            InitialCanCommonEcucParser.update_dbc_coreInfo_by_resourcem(ecuc_autosar_dict, cfg_dict)
        except Exception:
            import traceback

            logger.error(traceback.format_exc())
            logger.ui_error("CanIf resolving and updating multi core info failed!")

    def get_new_initial_arxml(
        self, ecuc_autosar_dict, initial_arxml_base, cfg_dict, import_file_type, initial_arxml_old=None
    ):
        if "dbc_or_ldf" == import_file_type:
            self.__update_can_multi_core_info(ecuc_autosar_dict, cfg_dict)
            cfg_dict_combine = self.combine_cfg_dict_dbcs_nm_message(cfg_dict)
            cfg_dict_combine["ecuc_autosar"] = ecuc_autosar_dict
            cfg_dict["ecuc_autosar"] = ecuc_autosar_dict
            for module_name, module_obj in self.initial_managers.items():
                if module_obj is None:
                    print(f"get_new_initial_arxml: {module_name} object None")
                    continue
                if module_name not in ecuc_autosar_dict.keys():
                    continue
                if hasattr(module_obj, "update_initial_ecuc_from_dbc_ldf"):
                    if module_name in CAN_NM_RX_COMBINE_MODULES:
                        module_obj.update_initial_ecuc_from_dbc_ldf(initial_arxml_base, cfg_dict_combine)
                    else:
                        module_obj.update_initial_ecuc_from_dbc_ldf(initial_arxml_base, cfg_dict)
                else:
                    print(f"get_new_initial_arxml: {module_name} object lack of update function")
            return initial_arxml_base
        elif "mcal_arxml" == import_file_type:
            if "CanIf" in self.sys_info_class.enable_modules and self.initial_managers["CanIf"]:
                self.initial_managers["CanIf"].update_data_from_eb_can_arxml_slot(initial_arxml_base, cfg_dict)
            if "LinIf" in self.sys_info_class.enable_modules and self.initial_managers["LinIf"]:
                self.initial_managers["LinIf"].update_data_from_eb_arxml_slot(initial_arxml_base, cfg_dict)
            return initial_arxml_base
        elif "mcal_arxml_others" == import_file_type:
            if self.initial_managers["MCALOTHERS"]:
                new_initial_autosar = self.initial_managers[
                    "MCALOTHERS"
                ].update_initial_selected_mcal_modules_ecuc_from_mcal_arxml(
                    initial_arxml_base, cfg_dict, initial_arxml_old
                )
            return new_initial_autosar

    @classmethod
    def combine_cfg_dict_dbcs_nm_message(cls, cfg_dict):
        """合并同一个dbc中的接收NM报文"""
        if len(cfg_dict.get("dbc", [])) == 0:
            return cfg_dict
        cfg_dict_copy = deepcopy(cfg_dict)
        for dbc_info in cfg_dict_copy.get("dbc", []):
            cls.combine_dbc_nm_message(dbc_info)
        return cfg_dict_copy

    @classmethod
    def combine_dbc_nm_message(cls, dbc_info):
        had_can_nm_message = False
        node_selected = dbc_info.get("node_selected", None)
        messages_dict = dbc_info.get("details", {})
        message_name_list = list(messages_dict.keys())
        if node_selected is None:
            logger.error("DBC not select node!")
            return
        nm_message_name = ""
        network_name = ""
        message_info_backup = None
        for message_name in message_name_list:
            if not cls.is_rx_can_nm_message(messages_dict[message_name], node_selected):
                continue
            if had_can_nm_message is False:
                network_name = getattr(messages_dict[message_name], "bus_name", "")
                nm_message_name = f"NM_o{network_name}"
                message_info_backup = deepcopy(messages_dict[message_name])
                messages_dict.pop(message_name)
                had_can_nm_message = True
            else:
                messages_dict.pop(message_name)
        if had_can_nm_message:
            repeat_num = 0
            while nm_message_name in messages_dict.keys():
                repeat_num += 1
                nm_message_name = f"NM{str(repeat_num)}_o{network_name}"
                logger.warning(f"{network_name} can nm message name repeat!")
            message_info_backup.message_name = nm_message_name
            if repeat_num == 0:
                message_info_backup.message_alias_name = "NM"
            else:
                message_info_backup.message_alias_name = f"NM{str(repeat_num)}"
            messages_dict.update({nm_message_name: message_info_backup})

    @classmethod
    def is_rx_can_nm_message(cls, message_info, node_selected):
        senders = getattr(message_info, "senders", None)
        if not isinstance(senders, list) or len(senders) == 0:
            return False
        if node_selected in senders:  # 跳过发送报文
            return False
        nm_asr_message = getattr(message_info, "message_attributes", {}).get("NmAsrMessage", None)
        nm_asr_message_value = getattr(nm_asr_message, "value", 0)
        if nm_asr_message_value in [None, 0]:
            return False
        else:
            return True

    def update_initial_arxml_from_dbc_ldf_mcal(
        self, cfg_dict, ecuc_autosar_dict, system_autosar_dict, import_file_type
    ):
        initial_arxml_base = ArxmlParseHandler.parse_initial_arxml(BASE_ARXML_PATH)
        initial_arxml_old = system_autosar_dict["Initial"]
        initial_arxml_new = None
        if import_file_type in ["dbc_or_ldf", "mcal_arxml_others"]:
            # mcal_arxml_others表示除了can(canif)之外的mcal模块
            self.update_initial_arxml_base(initial_arxml_base, initial_arxml_old, import_file_type)
            initial_arxml_base = AutosarUtil.update_autosar(initial_arxml_base)
            initial_arxml_new = self.get_new_initial_arxml(
                ecuc_autosar_dict, initial_arxml_base, cfg_dict, import_file_type, initial_arxml_old
            )
        elif "mcal_arxml" == import_file_type:
            initial_arxml_old_tmp = AutosarUtil.update_autosar(initial_arxml_old)
            self.update_initial_arxml_old(initial_arxml_old, initial_arxml_old_tmp)
            initial_arxml_new = self.get_new_initial_arxml(
                ecuc_autosar_dict, initial_arxml_old_tmp, cfg_dict, import_file_type
            )

        if initial_arxml_old is None or initial_arxml_new is None:
            return
        self._update_com_stack_ecuc_arxml(ecuc_autosar_dict, initial_arxml_old, initial_arxml_new, import_file_type)
        return initial_arxml_new

    def _update_com_stack_ecuc_arxml(self, ecuc_autosar_dict, initial_arxml_old, initial_arxml_new, import_file_type):
        if import_file_type in ["dbc_or_ldf"]:
            for module_name, module_obj in self.ecuc_managers.items():
                if module_obj is None:
                    continue
                if module_name in ecuc_autosar_dict.keys():
                    ecuc_atuosar = ecuc_autosar_dict[module_name]
                    if hasattr(module_obj, "get_new_ecuc_from_different_initial"):
                        ecuc_autosar_dict[module_name] = module_obj.get_new_ecuc_from_different_initial(
                            initial_arxml_old, initial_arxml_new, ecuc_atuosar
                        )
                    else:
                        logger.warning(f"{module_name} don't have get_new_ecuc_from_different_initial")
        elif import_file_type in ["mcal_arxml"]:
            if "CanIf" in ecuc_autosar_dict.keys():
                ecuc_atuosar = ecuc_autosar_dict["CanIf"]
                if hasattr(self.ecuc_managers["CanIf"], "get_new_ecuc_from_different_initial"):
                    ecuc_autosar_dict["CanIf"] = self.ecuc_managers["CanIf"].get_new_ecuc_from_different_initial(
                        initial_arxml_old, initial_arxml_new, ecuc_atuosar
                    )
                else:
                    logger.debug(f"{module_obj} don't have get_new_ecuc_from_different_initial")
            if "LinIf" in ecuc_autosar_dict.keys():
                ecuc_atuosar = ecuc_autosar_dict["LinIf"]
                if hasattr(self.ecuc_managers["LinIf"], "get_new_ecuc_from_different_initial"):
                    ecuc_autosar_dict["LinIf"] = self.ecuc_managers["LinIf"].get_new_ecuc_from_different_initial(
                        initial_arxml_old, initial_arxml_new, ecuc_atuosar
                    )
                else:
                    logger.debug(f"{module_obj} don't have get_new_ecuc_from_different_initial")
        elif import_file_type in ["mcal_arxml_others"]:
            for module_name in self.selected_mcal_modules_list:
                if module_name in ecuc_autosar_dict.keys():
                    ecuc_atuosar = ecuc_autosar_dict[module_name]
                    if hasattr(self.ecuc_managers["MCALOTHERS"], "get_new_ecuc_from_different_initial"):
                        self.ecuc_managers["MCALOTHERS"].set_module_name(module_name)
                        ecuc_autosar_dict[module_name] = self.ecuc_managers[
                            "MCALOTHERS"
                        ].get_new_ecuc_from_different_initial(initial_arxml_old, initial_arxml_new, ecuc_atuosar)
                    else:
                        logger.debug(f"{module_obj} don't have get_new_ecuc_from_different_initial")

        if (
            isinstance(self.selected_mcal_modules_list, list)
            and (
                "ResourceM" in self.selected_mcal_modules_list
                or "ResourceManager" in self.selected_mcal_modules_list
                or "Can" in self.selected_mcal_modules_list
            )
        ) and (import_file_type not in ["dbc_or_ldf"]):
            if (
                "Can" in ecuc_autosar_dict.keys()
                and "CanIf" in ecuc_autosar_dict.keys()
                and ("ResourceM" in ecuc_autosar_dict.keys() or "ResourceManager" in ecuc_autosar_dict.keys())
            ):
                tmp_old = None
                # 当同时导入Can模块时，由于之前会根据Can更新CanIf配置到initial_arxml_new中
                # 为避免重复添加Can相关内容，此处使用已包含Can内容的initial_arxml_new代替initial_arxml_old进行对比更新
                if isinstance(self.selected_mcal_modules_list, list) and "Can" in self.selected_mcal_modules_list:
                    tmp_old = AutosarUtil.update_autosar(initial_arxml_new)
                else:
                    tmp_old = initial_arxml_old
                self.initial_managers["CanIf"].update_data_from_eb_resourcem_arxml_slot(
                    initial_arxml_new, self.sys_info_class, ecuc_autosar_dict
                )

                ecuc_atuosar = ecuc_autosar_dict["CanIf"]
                if hasattr(self.ecuc_managers["CanIf"], "get_new_ecuc_from_different_initial"):
                    ecuc_autosar_dict["CanIf"] = self.ecuc_managers["CanIf"].get_new_ecuc_from_different_initial(
                        tmp_old, initial_arxml_new, ecuc_atuosar
                    )
                else:
                    logger.debug(f"{self.ecuc_managers['CanIf']} don't have get_new_ecuc_from_different_initial")

    def update_initial_arxml_base(self, initial_arxml_base, initial_arxml_old, import_file_type):

        search_definition_refs = [
            "/AUTOSAR/EcucDefs/CanIf/CanIfInitCfg/CanIfBufferCfg",
            "/AUTOSAR/EcucDefs/CanIf/CanIfInitCfg/CanIfInitHohCfg/CanIfHrhCfg",
            "/AUTOSAR/EcucDefs/CanIf/CanIfInitCfg/CanIfInitHohCfg/CanIfHthCfg",
            "/AUTOSAR/EcucDefs/CanIf/CanIfCtrlDrvCfg/CanIfCtrlCfg",
        ]
        for i in range(len(initial_arxml_base.AR_PACKAGES.AR_PACKAGE[0].ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES)):
            if (
                "CanIf"
                == initial_arxml_base.AR_PACKAGES.AR_PACKAGE[0]
                .ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES[i]
                .SHORT_NAME.valueOf_
            ):
                canif_obj_initial = initial_arxml_base.AR_PACKAGES.AR_PACKAGE[
                    0
                ].ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES[i]

        for i in range(len(initial_arxml_old.AR_PACKAGES.AR_PACKAGE[0].ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES)):
            if (
                "CanIf"
                == initial_arxml_old.AR_PACKAGES.AR_PACKAGE[0]
                .ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES[i]
                .SHORT_NAME.valueOf_
            ):
                canif_obj_old = initial_arxml_old.AR_PACKAGES.AR_PACKAGE[0].ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES[i]

        for i in range(len(canif_obj_old.CONTAINERS.ECUC_CONTAINER_VALUE)):
            self.traversal_container_values(
                canif_obj_old.CONTAINERS.ECUC_CONTAINER_VALUE[i],
                canif_obj_initial,
                search_definition_refs,
                import_file_type,
            )
        if import_file_type == "dbc_or_ldf":
            self.add_mcal_module_configuration_to_base_initial(initial_arxml_base, initial_arxml_old)

    @classmethod
    def add_mcal_module_configuration_to_base_initial(cls, initial_arxml_base, initial_arxml_old):
        if initial_arxml_base is None or initial_arxml_old is None:
            logger.error("Initial is None!")
            return
        base_initial_ecuc = initial_arxml_base.find("/InitialEcuC")
        if getattr(getattr(base_initial_ecuc, "ELEMENTS", None), "ECUC_MODULE_CONFIGURATION_VALUES", None) is None:
            logger.error("Base Initial is Empyt!")
            return
        old_initial_ecuc = initial_arxml_old.find("/InitialEcuC")
        if getattr(getattr(old_initial_ecuc, "ELEMENTS", None), "ECUC_MODULE_CONFIGURATION_VALUES", None) is None:
            logger.error("Initial is Empyt!")
            return

        for module_configuration in old_initial_ecuc.ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES:
            path = AutosarUtil.get_path(module_configuration)
            if path is None:
                continue
            if base_initial_ecuc.find(path) is not None:
                continue
            base_initial_ecuc.ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES.append(module_configuration)

    def update_initial_arxml_old(self, initial_arxml_old, initial_arxml_old_tmp):
        search_definition_refs = [
            "/AUTOSAR/EcucDefs/CanIf/CanIfInitCfg/CanIfBufferCfg",
            "/AUTOSAR/EcucDefs/CanIf/CanIfInitCfg/CanIfInitHohCfg/CanIfHrhCfg",
            "/AUTOSAR/EcucDefs/CanIf/CanIfInitCfg/CanIfInitHohCfg/CanIfHthCfg",
            "/AUTOSAR/EcucDefs/CanIf/CanIfCtrlDrvCfg/CanIfCtrlCfg",
        ]
        for i in range(len(initial_arxml_old_tmp.AR_PACKAGES.AR_PACKAGE[0].ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES)):
            if (
                "CanIf"
                == initial_arxml_old_tmp.AR_PACKAGES.AR_PACKAGE[0]
                .ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES[i]
                .SHORT_NAME.valueOf_
            ):
                canif_obj_initial = initial_arxml_old_tmp.AR_PACKAGES.AR_PACKAGE[
                    0
                ].ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES[i]

        for i in range(len(initial_arxml_old.AR_PACKAGES.AR_PACKAGE[0].ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES)):
            if (
                "CanIf"
                == initial_arxml_old.AR_PACKAGES.AR_PACKAGE[0]
                .ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES[i]
                .SHORT_NAME.valueOf_
            ):
                canif_obj_old = initial_arxml_old.AR_PACKAGES.AR_PACKAGE[0].ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES[i]

        for i in range(len(canif_obj_old.CONTAINERS.ECUC_CONTAINER_VALUE)):
            self.traversal_container_values(
                canif_obj_old.CONTAINERS.ECUC_CONTAINER_VALUE[i],
                canif_obj_initial,
                search_definition_refs,
                "mcal_arxml",
            )

    def traversal_container_values(
        self, container_value_object, container_value_object_base, search_definition_refs, import_file_type
    ):
        if hasattr(container_value_object, "DEFINITION_REF"):
            for j in range(len(search_definition_refs)):
                if container_value_object.DEFINITION_REF.valueOf_ == search_definition_refs[j]:
                    if import_file_type in ["dbc_or_ldf", "mcal_arxml_others"]:
                        self.add_container_value_object_to_base_initial_arxml(
                            container_value_object, search_definition_refs[j], container_value_object_base
                        )
                    elif "mcal_arxml" == import_file_type:
                        self.delete_container_value_object_from_old_initial_arxml(
                            container_value_object, container_value_object_base
                        )
        if hasattr(container_value_object, "ECUC_CONTAINER_VALUE"):
            for i in range(len(container_value_object.ECUC_CONTAINER_VALUE)):
                self.traversal_container_values(
                    container_value_object.ECUC_CONTAINER_VALUE[i],
                    container_value_object_base,
                    search_definition_refs,
                    import_file_type,
                )
        if hasattr(container_value_object, "SUB_CONTAINERS"):
            if container_value_object.SUB_CONTAINERS is not None:
                self.traversal_container_values(
                    container_value_object.SUB_CONTAINERS,
                    container_value_object_base,
                    search_definition_refs,
                    import_file_type,
                )

    def add_container_value_object_to_base_initial_arxml(
        self, container_value_object, search_definition_ref, canif_obj_initial
    ):

        if (
            "/AUTOSAR/EcucDefs/CanIf/CanIfInitCfg/CanIfInitHohCfg/CanIfHrhCfg" == search_definition_ref
            or "/AUTOSAR/EcucDefs/CanIf/CanIfInitCfg/CanIfInitHohCfg/CanIfHthCfg" == search_definition_ref
        ):
            canif_obj_initial.CONTAINERS.ECUC_CONTAINER_VALUE[1].SUB_CONTAINERS.ECUC_CONTAINER_VALUE[
                0
            ].SUB_CONTAINERS.ECUC_CONTAINER_VALUE.append(container_value_object)
        elif "/AUTOSAR/EcucDefs/CanIf/CanIfInitCfg/CanIfBufferCfg" == search_definition_ref:
            canif_obj_initial.CONTAINERS.ECUC_CONTAINER_VALUE[1].SUB_CONTAINERS.ECUC_CONTAINER_VALUE.append(
                container_value_object
            )
        elif "/AUTOSAR/EcucDefs/CanIf/CanIfCtrlDrvCfg/CanIfCtrlCfg" == search_definition_ref:
            canif_obj_initial.CONTAINERS.ECUC_CONTAINER_VALUE[5].SUB_CONTAINERS.ECUC_CONTAINER_VALUE.append(
                container_value_object
            )

    def delete_container_value_object_from_old_initial_arxml(self, container_value_object, container_value_object_base):
        del_container_path = container_value_object.get_path()
        container_value_object_tmp = container_value_object_base.find(del_container_path)
        if container_value_object_tmp:
            AutosarUtil.remove_container_value(
                container_value_object_tmp.parent_object_.ECUC_CONTAINER_VALUE, container_value_object_tmp
            )
