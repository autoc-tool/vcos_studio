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
from cmd_adaptor.cmd_interaction.cmd_logger import logger, progress_signal
from cmd_adaptor.data_management import data_management
from cmd_adaptor.data_management import (
    get_sys_info_class,
    get_autosar_bsw_class,
    get_sys_target_dict,
    get_all_module_list,
)
from cmd_adaptor.func_logic_layer.load_save_project import LoadAndSaveProject
from func_module.project_management.studio_cfg_handler import StudioCfgHandler
from func_module.generator import generator as vcos_generator
from func_module.generator.common.common import generator_utility
from func_module.module_management.user_plugin_manager.user_plugin_manager import UserPluginManager
from cmd_adaptor.func_logic_layer.validation_func.validate_cmd_func import ValidateCmdFunc

CUR_PATH = os.path.dirname(os.path.abspath(__file__))


class GenerateCmdFunc:

    @classmethod
    def vcos_studio_init_finish(cls):
        pass

    @classmethod
    def execute_auto_generate_c_code(cls, project_path, module_list, is_debug=False, forced_codegen=False, sim_mode=False) -> bool:
        GenerateCmdFunc.vcos_studio_init_finish()
        logger.info("Loading project file...")
        logger.info(project_path)
        result = LoadAndSaveProject.load_project(project_path)
        if result is False:
            return False
        # TODO 加载芯片system_cfg.json的模块情况,后续芯片json适配后取消注释
        generator_utility.load_system_cfg_by_target(data_management)
        # 命令行加载用户插件系统信息
        user_plugin_manager = UserPluginManager(
            sys_info_class=get_sys_info_class(),
            bsw_autosar_class=get_autosar_bsw_class(),
            sys_target_dict=get_sys_target_dict(),
            all_module_list=get_all_module_list(),
        )
        plugin_dirs = getattr(get_sys_info_class(), "import_plugin_path_list", []) if get_sys_info_class() else []
        user_plugin_manager.handle_valid_plugin_sys_cfg(plugin_dirs)
        validation_dict, _ = ValidateCmdFunc.validate_modules_with_result(module_list)
        # 若有校验错误,则拦截代码生成
        for module_name, val in validation_dict.items():
            if val is False:
                logger.error(f"Validation ERROR: Incorrect validation of {module_name} stopped code generation.")
                return False

        result = cls.execute_auto_generate(module_list, is_debug=is_debug, forced_codegen=forced_codegen, sim_mode=sim_mode)
        if result is False:
            return False

        logger.info("Start saving arxml ...")
        result = LoadAndSaveProject.generate_save_project()
        if result is False:
            return False

        logger.info("Finish saving arxml ...")

        return True

    @classmethod
    def execute_auto_generate(cls, module_list, is_debug=False, forced_codegen=False, sim_mode=False) -> bool:
        codegen_autosar_dict = vcos_generator.init_codegen_autosar_dict(data_management)
        enable_module_dict = {
            name: getattr(getattr(v, "DEFINITION_REF", ""), "valueOf_", "").split("/")[-1]
            for name, obj in data_management.autosar_bsw_class.items()
            for v in obj.find_nodes("ECUC-MODULE-CONFIGURATION-VALUES")
        }
        if module_list:
            enable_module_dict = GenerateCmdFunc.get_generate_module_list(module_list, enable_module_dict)

        codegen_module_list: dict = StudioCfgHandler.get_gen_or_validation_module_list(
            enable_module_dict, data_management.sys_target_dict, "support_generation"
        )

        filtered_codegen_module_list = {
            module_name: module_cfg
            for module_name, module_cfg in codegen_module_list.items()
            if generator_utility.func_module_check_mcal_module_codegen_cmd_line_tool_exist(
                data_management, module_name
            )[0]
        }
        for module_name in set(codegen_module_list) - set(filtered_codegen_module_list):
            ret, mcal_module_cmd_line_tool_path = (
                generator_utility.func_module_check_mcal_module_codegen_cmd_line_tool_exist(
                    data_management, module_name
                )
            )
            if not ret:
                message = (
                    f"{module_name} codegen cmd line tools({mcal_module_cmd_line_tool_path}) do not exist, "
                    "please confirm"
                )
                logger.warning(message)
        codegen_module_list = filtered_codegen_module_list

        codegen_modules: set = StudioCfgHandler.get_module_list(codegen_module_list)
        data_management.sys_info_class.codegen_module_dict = codegen_module_list
        data_management.sys_info_class.codegen_modules = codegen_modules

        result = cls.generate_c_code(data_management.sys_info_class, codegen_autosar_dict, is_debug, forced_codegen, sim_mode)
        return result

    @classmethod
    def generate_c_code(cls, sys_info_class, codegen_autosar_dict, is_debug=False, forced_codegen=False, sim_mode=False) -> bool:
        if is_debug:
            data_management.sys_info_class.mode = "debug"
        else:
            data_management.sys_info_class.mode = "release"
        if forced_codegen:
            data_management.sys_info_class.incremental_generation = False
        else:
            data_management.sys_info_class.incremental_generation = True
        data_management.sys_info_class.sim_mode = sim_mode
        result = vcos_generator.generate_c_code(sys_info_class, codegen_autosar_dict, progress_signal)
        return result

    @classmethod
    def execute_auto_generate_swc_template(cls, project_path, selected_swc) -> bool:
        result = LoadAndSaveProject.load_project(project_path)
        if result is False:
            return False
        codegen_autosar_dict = vcos_generator.init_codegen_autosar_dict(data_management, True)
        all_swc_list = vcos_generator.get_swc_list_for_template_gereration(codegen_autosar_dict["asw_autosar_dict"])
        if not selected_swc:
            codegen_swcs = all_swc_list
        else:
            from cmd_adaptor.cmd_interaction.cmd_interaction import CmdInteraction

            selected_swc_list = CmdInteraction.handle_cmd_input_modules(selected_swc)
            codegen_swcs = list(set(all_swc_list) & set(selected_swc_list))
            data_management.sys_info_class.codegen_swcs = codegen_swcs
        ret = vcos_generator.generate_swc_template(
            data_management.sys_info_class, codegen_autosar_dict, codegen_swcs, None
        )
        if ret:
            logger.info("start saving arxml ...")
            LoadAndSaveProject.generate_save_project()
            logger.info("finish saving arxml ...")
        else:
            logger.error("generate swc template failed")
        return ret

    @classmethod
    def get_generate_module_list(cls, module_list, enable_modules):
        generate_module_list = []

        if isinstance(module_list, str):
            if "," in module_list:
                generate_module_list = module_list.split(",")
            elif " " in module_list:
                generate_module_list = module_list.split(" ")
            else:
                generate_module_list = [module_list]
        elif isinstance(module_list, list) and ("," in module_list[0] or " " in module_list[0]):
            module_list = module_list[0]
            if "," in module_list:
                generate_module_list = module_list.split(",")
            elif " " in module_list:
                generate_module_list = module_list.split(" ")
            else:
                generate_module_list = [module_list]
        elif isinstance(module_list, list):
            generate_module_list = module_list

        generate_module_set = {x.replace(" ", "") for x in generate_module_list}
        generate_module_dict = {
            instance_name: module_name
            for instance_name, module_name in enable_modules.items()
            if instance_name in generate_module_set
        }
        return generate_module_dict
