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
BSW层代码生成模块, 通过调用BSW层子模块的generator.py生成BSW层代码.
"""
import importlib
from jinja2 import UndefinedError
import inspect
import os
import shutil

from basic_func_module.base_common.load_plug_in import LoadPlugIn
from func_module.health_monitor.logger import logger
from func_module.generator.common.common import check_and_warn_missing_dependencies
from func_module.generator.bsw.mcal_module import generator as mcal_module_generator
from func_module.module_management.module_management import ModuleManagement


def generate(
    sys_config: dict,
    config_dict: dict,
    ecuc_autosar_dict: dict,
    module_cfg: dict,
    mcal_module_codegen_cmd_line_dict: dict,
    progress_signal,
):
    """
    Generate bsw code
    Args:
        sys_config (dict): System configuration items
        config_dict (dict): config.json
    """

    return generate_c_code(sys_config, config_dict, module_cfg, mcal_module_codegen_cmd_line_dict, progress_signal)


def check_module_is_mcal(parser_module, module_info):
    if (
        parser_module in module_info
        and "is_mcal" in module_info[parser_module]
        and module_info[parser_module]["is_mcal"]
    ):
        return True
    else:
        return False


def generate_c_code(
    sys_config: dict, config_dict: dict, module_cfg: dict, mcal_module_codegen_cmd_line_dict: dict, progress_signal
):
    """
    Generate dynamic code
    Args:
        sys_config (dict): System configuration items
        config_dict (dict): config.json
    """

    sys_config["module_cfg"] = module_cfg
    enabled_module_list = sys_config.get("modules_info", {}).get("enabled_module_list", [])
    bsw_result_dict = {"bsw": {}}
    check_and_warn_missing_dependencies(module_cfg, "MemMap", enabled_module_list)
    plugin_module_info = ModuleManagement.get_module_path_info_by_spec_path(
        set(sys_config["path"]["import_plugin_path_list"])
    )
    for parser_module in sys_config["modules_info"]["codegen_module_list"]:
        check_and_warn_missing_dependencies(module_cfg, parser_module, enabled_module_list)
        try:
            # Cdd 的特殊处理逻辑
            parser_module_dict = config_dict["bsw"].get(parser_module.lower(), None)
            if (
                parser_module_dict is not None
                and "ArPackages" in parser_module_dict
                and "ActiveEcuC" in parser_module_dict["ArPackages"]
            ):
                defref = parser_module_dict["ArPackages"]["ActiveEcuC"][parser_module]["DefinitionRef"].split("/")[-1]
                if defref == "Cdd":
                    parser_module = "Cdd"
            if parser_module in {"Rte", "vcosMtnce"}:
                continue

            is_mcal = check_module_is_mcal(parser_module, sys_config["sys_target_dict"]["module_cfg"])
            if is_mcal is True:
                if mcal_module_codegen_cmd_line_dict and parser_module in mcal_module_codegen_cmd_line_dict.keys():
                    progress_signal.emit(f"Generating {parser_module} c code")
                    ret = mcal_module_generator.generate(parser_module, mcal_module_codegen_cmd_line_dict)
                    bsw_result_dict["bsw"].update({parser_module: {"result": ret}})
                continue
            else:
                if parser_module not in sys_config["plug_in_path"].keys():
                    logger.warning(f"{parser_module} does not support c code generation")
                    continue
                bsw_result_dict["bsw"].update({parser_module: {"result": False}})
                module_gendata_path = os.path.join(sys_config["gendata_path"], parser_module)
                if os.path.exists(module_gendata_path):
                    shutil.rmtree(module_gendata_path)
                    os.mkdir(module_gendata_path)
                else:
                    os.mkdir(module_gendata_path)
                if sys_config["sys_target_dict"]["module_cfg"][parser_module].get("user_plugin", None):
                    # 确保模块上一级添加进syspath，各个插件可能在不同的目录下
                    LoadPlugIn.append_sys_path(plugin_module_info[parser_module], parser_module)
                module_pkg = LoadPlugIn.load_module(parser_module, "config_plug_in.generator.generator")
                if module_pkg is None:
                    logger.exception(f"{parser_module} does not support c code generation")
                    continue
                generate_dynamic_code = getattr(module_pkg, "generate_dynamic_code")
                progress_signal.emit(f"Generating {parser_module} c code")
                ret = generate_dynamic_code(sys_config, config_dict)
                bsw_result_dict["bsw"].update({parser_module: {"result": ret}})
        except UndefinedError as e:
            error_info = None
            frame_info_list = inspect.trace()
            frame_info_list.reverse()
            for frame_info in frame_info_list:
                if frame_info.function == "top-level template code":
                    error_info = frame_info
                    break
            filename = os.path.basename(error_info.filename)
            error_line = error_info.lineno
            error_code = error_info.code_context[0].strip()
            logger.error(f"UndefinedError: {filename}:{error_line} {error_code} {e}")
            bsw_result_dict["bsw"].update({parser_module: {"result": False}})
        except Exception as e:
            logger.exception(f"{parser_module} codegen failed! {type(e)}")
            bsw_result_dict["bsw"].update({parser_module: {"result": False}})
    return bsw_result_dict
