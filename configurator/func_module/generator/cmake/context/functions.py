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
appl模板内函数定义模块.

定义jinja2模板中所使用的函数.

用法示例:
{{get_core_id_list()}}
"""
import os
import sys
from jinja2 import pass_context
from func_module.health_monitor.logger import logger
from func_module.generator.common.common import FunctionBase
from basic_func_module.path_handler.path_converter import PathConverter_Adaptor


def to_forward_slash(path: str):
    result = path
    if "\\" in path:
        result = path.replace("\\", "/")
    return result


def compatible_linux_and_windows_path_symbols(path):
    path = os.path.abspath(path).replace("\\", "/")
    return path


class Function(FunctionBase):
    """
    Class containing all functions. Add new static functions here
    to be included in the jinja2 context
    """

    @staticmethod
    @pass_context
    def get_module_build_info_list(context):
        kfg_module_all_list = context["sys_config"]["modules_info"]["kfg_module_all_list"]
        return kfg_module_all_list

    @staticmethod
    @pass_context
    def get_gendata_path(context):
        sys_config = context["sys_config"]
        gendata_path = sys_config.get("gendata_path")
        if not gendata_path and not os.path.exists(gendata_path):
            assert f"gendata_path: {gendata_path} not exists "
        apps_path = sys_config["path"].get("application_path", None)
        if not apps_path and not os.path.exists(apps_path):
            assert f"apps_path: {apps_path} not exists "
            return ""
        if PathConverter_Adaptor.is_same_disk(gendata_path, apps_path):
            relative_path = os.path.relpath(gendata_path, apps_path)
            return "$(APPLICATION_PATH)/" + to_forward_slash(relative_path)
        else:
            relative_path = compatible_linux_and_windows_path_symbols(gendata_path)
            return relative_path

    @staticmethod
    @pass_context
    def get_system_path(context):
        sys_config = context["sys_config"]
        system_path = sys_config["path"].get("system_path", None)
        if not system_path and not os.path.exists(system_path):
            assert f"system_path: {system_path} not exists "

        application_path = sys_config["path"].get("application_path", None)
        if not application_path and not os.path.exists(application_path):
            assert f"application_path: {application_path} not exists "
            return ""
        if PathConverter_Adaptor.is_same_disk(system_path, application_path):
            relative_path = os.path.relpath(system_path, application_path)
            return "$(APPLICATION_PATH)/" + to_forward_slash(relative_path)
        else:

            relative_path = compatible_linux_and_windows_path_symbols(system_path)

            return relative_path

    @staticmethod
    @pass_context
    def get_mcal_gendate_path(context):
        sys_config = context["sys_config"]
        mcal_gendata_path = sys_config["path"].get("mcal_gendata_path", None)
        if not mcal_gendata_path:
            logger.warning("get mcal_gendate_path failed, please supplement.")
            return ""

        application_path = sys_config["path"].get("application_path", None)
        if not application_path:
            logger.exception("get root_path failed")
            return ""
        if PathConverter_Adaptor.is_same_disk(mcal_gendata_path, application_path):
            relative_path = os.path.relpath(mcal_gendata_path, application_path)
            return "$(APPLICATION_PATH)/" + to_forward_slash(relative_path)
        else:
            relative_path = compatible_linux_and_windows_path_symbols(mcal_gendata_path)
            return relative_path

    @staticmethod
    @pass_context
    def get_mcal_path(context):
        sys_config = context["sys_config"]
        mcal_path = sys_config["path"].get("mcal_path", None)
        if not mcal_path:
            logger.exception("get system_path failed")
            return ""

        application_path = sys_config["path"].get("application_path", None)
        if not application_path:
            logger.exception("get root_path failed")
            return ""
        if PathConverter_Adaptor.is_same_disk(mcal_path, application_path):
            relative_path = os.path.relpath(mcal_path, application_path)
            return "$(APPLICATION_PATH)/" + to_forward_slash(relative_path)
        else:
            relative_path = compatible_linux_and_windows_path_symbols(mcal_path)
            return relative_path

    @staticmethod
    @pass_context
    def get_project_name(context):
        sys_config = context["sys_config"]
        path = sys_config.get("project", None)
        if not path:
            logger.exception("get project path failed")
            return ""

        return path

    @staticmethod
    @pass_context
    def get_swc_template_path(context):
        sys_config = context["sys_config"]
        swc_template_path = sys_config["path"].get("swc_template_path", None)
        if not swc_template_path:
            logger.exception("get root path failed")
            return ""
        apps_path = sys_config["path"].get("application_path", None)
        if not apps_path:
            logger.exception("get apps_path failed")
            return ""
        if PathConverter_Adaptor.is_same_disk(swc_template_path, apps_path):
            relative_path = os.path.relpath(swc_template_path, apps_path)
            return "./" + to_forward_slash(relative_path)
        else:
            relative_path = compatible_linux_and_windows_path_symbols(swc_template_path)
            return relative_path

    @staticmethod
    @pass_context
    def get_target(context):
        sys_config = context["sys_config"]
        target = sys_config.get("target", None)
        if not target:
            logger.exception("get target failed")
            return ""
        return target

    @staticmethod
    @pass_context
    def get_compiler(context):
        sys_config = context["sys_config"]
        compiler = sys_config.get("compiler", None)
        if not compiler:
            logger.exception("get compiler failed")
            return ""

        return compiler

    @staticmethod
    @pass_context
    def get_mcal_version(context):
        sys_config = context["sys_config"]
        mcal_version = sys_config.get("mcal_version", None)
        if not mcal_version:
            logger.exception("get compiler failed")
            return ""

        return mcal_version

    @staticmethod
    @pass_context
    def get_compiler_path(context):
        sys_config = context["sys_config"]
        compiler_path = sys_config["path"].get("compiler_path", "")
        if not compiler_path:
            return ""

        apps_path = sys_config["path"].get("application_path", None)
        if not apps_path:
            logger.exception("get apps_path failed")
            return ""
        if PathConverter_Adaptor.is_same_disk(compiler_path, apps_path):
            relative_path = os.path.relpath(compiler_path, apps_path)
        else:
            relative_path = compatible_linux_and_windows_path_symbols(compiler_path)

        if sys.platform.startswith("win"):
            return to_forward_slash(relative_path) + "/"
        elif sys.platform.startswith("linux"):
            return compiler_path + "/"
        else:
            logger.exception("get system type failed")
            return ""

    @staticmethod
    @pass_context
    def get_tool_chain_path(context):
        if sys.platform.startswith("win"):
            return "$(BUILD_TOOL_PATH)/MakeSystemTool/windows/usr/bin/"
        elif sys.platform.startswith("linux"):
            return "/usr/bin/"
        else:
            logger.exception("get system type failed")
            return ""

    @staticmethod
    @pass_context
    def get_build_mode(context):
        sys_config = context["sys_config"]
        build_mode = sys_config.get("mode", None)
        if not build_mode:
            logger.exception("get apps_path failed")
            return ""
        logger.debug(f"build_mode:{build_mode}")
        return build_mode

    @staticmethod
    @pass_context
    def get_kfg_module_all_list(context):
        enable_module_list = context["sys_config"]["modules_info"]["kfg_module_all_list"]

        return enable_module_list

    @staticmethod
    @pass_context
    def get_enable_module_list(context):
        bsw_module_list = set()
        enable_module_list = context["sys_config"]["modules_info"]["enabled_module_list"]
        for module_name in enable_module_list:
            if module_name not in context["sys_config"]["sys_target_dict"]["module_cfg"]:
                logger.debug(f"{module_name} is CDD, generate module enable macros")
            elif (
                "is_mcal" in context["sys_config"]["sys_target_dict"]["module_cfg"][module_name]
                and context["sys_config"]["sys_target_dict"]["module_cfg"][module_name]["is_mcal"] is True
            ):
                logger.debug(f"{module_name} is MCAL, Do not generate module enable macros")
                continue

            bsw_module_list.add(module_name)
        return sorted(list(bsw_module_list))

    @staticmethod
    @pass_context
    def get_bswm_user_callout_path(context):
        sys_config = context["sys_config"]
        bswcallout_path = sys_config["path"].get("bswcallout_path", None)
        if not bswcallout_path:
            logger.exception("get bswcallout path failed")
            return ""

        apps_path = sys_config["path"].get("application_path", None)
        if not apps_path:
            logger.exception("get apps_path failed")
            return ""

        if PathConverter_Adaptor.is_same_disk(bswcallout_path, apps_path):
            relative_path = os.path.relpath(bswcallout_path, apps_path)
            return to_forward_slash(relative_path)
        else:
            relative_path = compatible_linux_and_windows_path_symbols(bswcallout_path)
            return relative_path

    @staticmethod
    @pass_context
    def get_project_file_path(context):
        sys_config = context["sys_config"]
        config_path = sys_config.get("config_path", None)
        if not config_path:
            logger.exception("get bswcallout path failed")
            return ""
        project_file_path = os.path.join(config_path, "..")

        apps_path = sys_config["path"].get("application_path", None)
        if not apps_path:
            logger.exception("get apps_path failed")
            return ""

        if PathConverter_Adaptor.is_same_disk(project_file_path, apps_path):
            relative_path = os.path.relpath(project_file_path, apps_path)
            return to_forward_slash(relative_path)
        else:
            relative_path = compatible_linux_and_windows_path_symbols(project_file_path)
            return relative_path
