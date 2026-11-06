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
from basic_func_module.base_logger import logger
from basic_func_module.autosar_utils.autosar_ecuc import AutosarEcuc
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlParseHandler
from func_module.module_management.module_management import ModuleManagement
from func_module.module_management.arxml_handler.system.system_arxmls_manager import SystemArxmlsManager


class EcucCfgImport:

    @classmethod
    def module_can_be_imported(cls, ecuc_module_info, autosar_mod_class, prefix_diff_modules, module_name, file_path):
        """checks whether the module can be imported and saves its info"""

        ecuc_module_obj = ecuc_module_info["ecuc_module_obj"]
        force_import = ecuc_module_info.get("force_import", False)
        ecuc_prefix = ArxmlParseHandler.get_ecuc_module_preifx(ecuc_module_obj)
        mod_prefix = ArxmlParseHandler.get_mod_perfix(module_name, autosar_mod_class)
        can_be_imported = True

        if mod_prefix is not None and ecuc_prefix != mod_prefix and not force_import:
            logger.ui_error(f"The chips in the project differ from the {module_name} in ARXML, causing import failure.")
            can_be_imported = False
            if file_path not in prefix_diff_modules:
                prefix_diff_modules[file_path] = {}
            prefix_diff_modules[file_path][module_name] = {"ecuc_module_obj": ecuc_module_obj, "force_import": False}

        return can_be_imported, ecuc_prefix

    @classmethod
    def update_ecuc_autosar_dict(cls, data, need_update_ecuc_dcit: dict):
        module_manage = ModuleManagement(
            data.sys_info_class, data.autosar_bsw_class, data.autosar_bswmd_class, data.autosar_ib_class
        )
        module_cfg = getattr(data, "sys_target_dict", {}).get("module_cfg", {})
        selected_mcal_modules_list = []
        mcal_prefix_dict = {}
        data.cfg_info_dict["eb"] = {"arxml": {}}
        prefix_diff_modules = {}
        imported_mcal_modules = {}

        for file_path, ecuc_module_dict in need_update_ecuc_dcit.items():
            for module_name, module_info in ecuc_module_dict.items():
                ecuc_obj = module_info["ecuc_module_obj"]
                # parse base ecuc for mcal modules
                if module_cfg.get(module_name, {}).get("is_mcal"):
                    # save eb file path
                    data.sys_info_class.eb_arxml = file_path
                    can_import, ecuc_prefix = cls.module_can_be_imported(
                        module_info, data.autosar_bswmd_class, prefix_diff_modules, module_name, file_path
                    )
                    if not can_import:
                        continue
                    mcal_prefix_dict[module_name] = ecuc_prefix
                    ecuc_cfg_obj_list = module_info["ecuc_module_obj"].find_nodes("ECUC-MODULE-CONFIGURATION-VALUES")
                    if not ecuc_cfg_obj_list:
                        continue
                    selected_mcal_modules_list.append(module_name)
                    data.cfg_info_dict["eb"]["arxml"][module_name] = (
                        AutosarUtil.to_ecuc_module_configuration_values_dict(ecuc_cfg_obj_list[0])
                    )
                    imported_mcal_modules[module_name] = ecuc_obj
                    if module_name in data.sys_info_class.enable_modules:
                        continue
                    # bswmd must be loaded before updating base ecuc
                    if module_name not in data.autosar_bswmd_class:
                        data.autosar_bswmd_class.update(
                            ArxmlParseHandler.parse_all_bswmd_arxml(
                                data.sys_info_class.plug_in_bswmd_path, [module_name], data.sys_info_class.target
                            )
                        )
                    # update ecuc module info by base ecuc
                    ecuc_obj = module_manage.load_ecuc(module_name, module_name, ecuc_prefix)
                    AutosarEcuc.record_default_file(
                        ecuc_obj.find(f"/ActiveEcuC/{module_name}"), f"{module_name}_ecuc.arxml"
                    )

                module_manage.update_ecuc_module_by_import(module_name, ecuc_obj)

        cls.mcal_update_com_stack_and_reasoning(module_manage, selected_mcal_modules_list, mcal_prefix_dict, data)
        # update impl cfg var and module desc ref
        cls.update_impl_variant_module_desc(data.autosar_bsw_class, imported_mcal_modules)

        return prefix_diff_modules

    @classmethod
    def mcal_update_com_stack_and_reasoning(
        cls, module_manage: ModuleManagement, selected_mcal_modules_list: list, mcal_prefix_dict: str, data
    ):

        if not selected_mcal_modules_list:
            return
        system_arxml_manager = SystemArxmlsManager(
            data.autosar_bswmd_class, data.sys_info_class, selected_mcal_modules_list
        )

        system_arxml_manager.set_selected_mcal_modules_list(selected_mcal_modules_list, data.sys_info_class)
        system_arxml_manager.update_com_stack_arxml_from_dbc_ldf(
            data.cfg_info_dict, data.autosar_bsw_class, data.autosar_system_class, "mcal_arxml_others"
        )
        if "Can" in selected_mcal_modules_list:  # 如果选择导入Can模块，需要同步更新CanIf模块
            mod_prefix = ArxmlParseHandler.get_mod_perfix("Can", data.autosar_bswmd_class)
            # 如果mod的前缀和mcal arxml中的前缀不同，表示工程使用的芯片和mcal arxml的不相同
            if mod_prefix != mcal_prefix_dict.get("Can"):
                logger.ui_error(
                    "The current module(Can) mcal arxml does not match the project. Do not update CanIf ecuc arxml"
                )
            else:
                module_manage.append_module("CanIf")
                system_arxml_manager.update_com_stack_arxml_from_dbc_ldf(
                    data.cfg_info_dict, data.autosar_bsw_class, data.autosar_system_class, "mcal_arxml"
                )
        if "Lin" in selected_mcal_modules_list:
            mod_prefix = ArxmlParseHandler.get_mod_perfix("Lin", data.autosar_bswmd_class)
            # 如果mod的前缀和mcal arxml中的前缀不同，表示工程使用的芯片和mcal arxml的不相同
            if mod_prefix != mcal_prefix_dict.get("Lin"):
                logger.ui_error(
                    "The current module(Lin) mcal arxml does not match the project. Do not update LinIf ecuc arxml"
                )
            elif "LinIf" in data.sys_info_class.enable_modules:
                system_arxml_manager.update_com_stack_arxml_from_dbc_ldf(
                    data.cfg_info_dict, data.autosar_bsw_class, data.autosar_system_class, "mcal_arxml"
                )

    @classmethod
    def update_impl_variant_module_desc(cls, bsw_ecuc_class, imported_mcal_modules):
        """
        update base ecuc implementation cfg variant and module description ref
        """
        for module_name, in_module_cfg in imported_mcal_modules.items():
            if not (curr_module_cfg := bsw_ecuc_class.get(module_name, None)):
                continue
            try:
                curr_module_cfg = curr_module_cfg.AR_PACKAGES.AR_PACKAGE[0].ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES[0]
                in_module_ecuc = in_module_cfg.AR_PACKAGES.AR_PACKAGE[0].ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES[0]
                curr_module_cfg.IMPLEMENTATION_CONFIG_VARIANT = in_module_ecuc.IMPLEMENTATION_CONFIG_VARIANT
                curr_module_cfg.MODULE_DESCRIPTION_REF = in_module_ecuc.MODULE_DESCRIPTION_REF
            except Exception as e:
                logger.error(f"update ecuc implementation cfg variant and module description ref error: {e}")
                continue
