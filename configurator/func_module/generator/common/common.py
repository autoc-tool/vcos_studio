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
"""
定义jinja2模板中所使用的公共函数.
"""
import os
from jinja2 import pass_context
from datetime import datetime
from func_module.health_monitor.logger import logger
from enum import IntEnum, auto
from func_module.project_management.studio_cfg_handler import StudioCfgHandler

LICENSE_TXT = ""
with open(os.path.join(os.path.dirname(__file__), "license.txt"), "r", encoding="utf-8") as f:
    LICENSE_TXT = f.read()


class ErrorCode(IntEnum):
    RTE_CODEGEN = 100
    SCHM_CODEGEN = auto()
    NO_CODEGEN = auto()


class FunctionBase:
    """
    Class containing all common functions.
    """

    @staticmethod
    @pass_context
    def get_vcos_version_temp(context):
        version = ""
        try:
            version = context["sys_cfg"]["version"]
        except Exception as e:
            logger.warning(f"{type(e)} {format(e)} get version failed")
        return version

    @staticmethod
    @pass_context
    def get_generation_time_temp(context):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    @pass_context
    def get_copyright(context):
        return LICENSE_TXT

    @staticmethod
    @pass_context
    def get_generation_time(context):
        title = "Generation Time"
        return f"{title:<16}" + ": " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    @pass_context
    def get_project_name(context):
        title = "Project Name"
        project = ""
        try:
            project = context["sys_cfg"]["project"]
        except Exception as e:
            logger.warning(f"{type(e)} {format(e)} get project name failed")

        return f"{title:<16}" + ": " + project

    @staticmethod
    @pass_context
    def get_vcos_version(context):
        title = "Tool Version"
        version = ""
        try:
            version = context["sys_cfg"]["version"]
        except Exception as e:
            logger.warning(f"{type(e)} {format(e)} get version failed")

        return f"{title:<16}" + ": " + version


def check_and_warn_missing_dependencies(module_cfg, module_name, enabled_module_list):
    """
    Check if the dependencies of a module exist in the enabled_module_list.
    If any dependency is missing, log a warning.

    Parameters:
    - module_cfg: The module configuration dictionary.
    - module_name: The name of the module to check dependencies for.
    - enabled_module_list: The list of enabled modules.

    Returns:
    - None
    """
    # Get the dependency list for the specified module
    dep_list = module_cfg.get(module_name, {}).get("dependency_list", [])

    # Check for missing dependencies
    missed_dep_list = [element for element in dep_list if element not in enabled_module_list]

    # Log a warning if there are missing dependencies
    if missed_dep_list:
        logger.warning(
            f"The modules {missed_dep_list} that {module_name} "
            "depends on do not exist (not added or have been removed)! Code generation may fail."
        )


def find_definition_ref_paths(data, current_path=None, ref_paths=None):
    """
    递归遍历字典寻找所有包含DefinitionRef的元素路径。

    :param data: 待搜索的字典或列表
    :param current_path: 当前元素的路径（递归过程中累积）
    :param ref_paths: 收集到的DefinitionRef的路径
    :return: 更新后的ref_paths
    """
    if current_path is None:
        current_path = []  # 如果是首次调用，初始化路径列表
    if ref_paths is None:
        ref_paths = {}  # 如果是首次调用，初始化结果字典

    if isinstance(data, dict):
        for key, value in data.items():
            # 如果找到了DefinitionRef，则收集路径信息
            if key == "DefinitionRef":
                ref_path = "/".join(current_path)
                if value not in ref_paths:
                    ref_paths[value] = []
                ref_paths[value].append(ref_path)
            else:
                # 递归遍历字典元素
                find_definition_ref_paths(value, current_path + [key], ref_paths)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            # 递归遍历列表元素
            find_definition_ref_paths(item, current_path + [str(index)], ref_paths)

    return ref_paths


class GeneratorUtility:

    @staticmethod
    def load_system_cfg_by_target(data_management):
        try:
            sys_target = data_management.sys_target_dict["target"]
            target = data_management.sys_info_class.target
            system_path = data_management.sys_info_class.system_path

            sys_json_path = os.path.normpath(
                os.path.join(
                    system_path,
                    "platform_cfg",
                    sys_target[target]["DERIVATIVE_GROUP"],
                    target,
                    "platform_cfg.json",
                )
            )

            data = StudioCfgHandler.load_studio_cfg_file(sys_json_path)

            if data is None:
                logger.info("Current chip does not have a separate system_cfg.json")
                return True

            data_management.sys_target_dict["module_cfg"].update(data["module_cfg"])

            cmd_line_rules = data.get("cmd_line_rules", {})

            for module_name, cmd_line_args in cmd_line_rules.items():
                paths = cmd_line_args.get("paths", {})
                cmd_args = cmd_line_args.get("cmd_args", {})

                paths["MCAL_PATH"] = data_management.sys_info_class.mcal_path
                paths["CONFIG_BASE_PATH"] = data_management.sys_info_class.config_base_path
                paths["MCAL_GENDATA_PATH"] = data_management.sys_info_class.mcal_gendata_path

                cmd_line_args["cmd_args"] = GeneratorUtility.replace_paths(cmd_args, paths)

            data_management.sys_target_dict["mcal_module_codegen_cmd_line_dict"] = cmd_line_rules
            return True
        except Exception as e:
            logger.error(f"load_system_cfg_by_target: {e}")
            return False

    @staticmethod
    def func_module_check_mcal_module_codegen_cmd_line_tool_exist(data_management, module_name):
        mcal_module_codegen_cmd_line_dict = data_management.sys_target_dict.get("mcal_module_codegen_cmd_line_dict")
        if mcal_module_codegen_cmd_line_dict is not None and module_name in mcal_module_codegen_cmd_line_dict.keys():
            mcal_module_cmd_line_tool_path = mcal_module_codegen_cmd_line_dict[module_name]["cmd_args"][
                0
            ]  # list中第一个元素为命令行工具的路径
            if os.path.exists(mcal_module_cmd_line_tool_path):
                return True, mcal_module_cmd_line_tool_path  # 路径存在，返回绝对路径
            else:
                return (
                    False,
                    mcal_module_cmd_line_tool_path,
                )  # 路径不存在，返回被检查的路径，提示用户指定的路径是什么，方便定位问题
        else:
            return True, ""

    # 替换cmd_args里的路径占位符
    def replace_paths(cmd_args, paths):
        replaced_args = []
        for arg in cmd_args:
            for key, value in paths.items():
                arg = arg.replace(key, value)
            replaced_args.append(arg)
        return replaced_args


generator_utility = GeneratorUtility()
