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
rte代码生成模块.

解析输入的josn object, 然后生成rte代码.
"""

import shutil
import inspect
import os

from . import context
from func_module.health_monitor.logger import logger
from func_module.generator.rte import filter
from func_module.generator.common.common import ErrorCode
from basic_func_module.autosar_utils.autosar_utils import AutosarUtils
from jinja2 import Environment, FileSystemLoader, StrictUndefined, UndefinedError, Template

CUR_FILE_PATH = os.path.dirname(__file__)
DEFAULT_TEMPLATE_FILE_DIR = os.path.join(CUR_FILE_PATH, "template")


def get_rte_config_dict(config_dict, user_code={}) -> dict:
    input_dict = {}
    input_dict.setdefault("bsw_instances", config_dict["rte"]["bsw_instances"])
    if config_dict["parser_ret"] == ErrorCode.RTE_CODEGEN:
        input_dict = filter.get_template_input_parameter_dict_from_parsed_data(config_dict["rte"])
        input_dict = asw_cfg_add_user_code(user_code, input_dict)
        input_dict["osapplication_asw_cfg"] = _pack_asw_cfg_by_osapplication(input_dict.get("asw_cfg", {}))
    return input_dict


def get_rendering_context(file_template_name, input_dict, sys_config=None, appl=None, ecuc_autosar_dict=None):
    config = {}
    if file_template_name == "Rte_OsApplication.c.jinja2":
        osapplication_asw_cfg = _pack_asw_cfg_by_osapplication(input_dict["asw_cfg"])
        config = {
            "sys_cfg": sys_config,
            "task_mappings": input_dict["appl_to_task_dict"][appl],
            "asw_cfg": osapplication_asw_cfg[appl] if appl in osapplication_asw_cfg else {},
            "appl_name": appl,
            "mode_declaration_group": input_dict["mode_declaration_group"],
            "osapplication_asw_cfg": osapplication_asw_cfg,
            "com_module_osapplication": input_dict.get("com_module_osapplication", None),
            "appls_asw_cfg": input_dict["asw_cfg"],
            "sr_required_com_specs_dict": input_dict.get("sr_required_com_specs_dict", {}),
            "sr_dm_glob_vars": input_dict.get("sr_dm_glob_vars", {}),
            "RteGeneration_dict": input_dict.get("RteGeneration", {}),
            "appl_info": input_dict.get("appl_dict", {}).get(appl, {}),
            "os_counter": input_dict.get("os_counter", {}),
            "signal_dict": input_dict.get("signal_dict", {}),
            "ecuc_config": ecuc_autosar_dict,
            "bsw_instances": input_dict.get("bsw_instances", {}),
            "vfb_trace_hooks_info": input_dict.get("vfb_trace_hooks_info", []),
        }
    elif file_template_name == "Rte.c.jinja2":
        config = {
            "sys_cfg": sys_config,
            "core_id_list": input_dict["core_id_list"],
            "core_to_appl_dict": input_dict["core_to_appl_dict"],
            "core_to_task_dict": input_dict["core_to_task_dict"],
            "core_to_alarm_dict": input_dict["core_to_alarm_dict"],
            "task_to_st_dict": input_dict["task_to_st_dict"],
            "signals_and_signalgroups": input_dict["signals_and_signalgroups"],
            "data_received_event": input_dict["data_received_event"],
            "port_event_id_and_task_id": input_dict["port_event_id_and_task_id"],
            "asw_cfg": input_dict["asw_cfg"],
            "appl_list": input_dict["appl_list"],
            "mode_declaration_group": input_dict["mode_declaration_group"],
            "osapplication_asw_cfg": input_dict["osapplication_asw_cfg"],
            "com_module_osapplication": input_dict.get("com_module_osapplication", None),
            "com_core_id": input_dict.get("com_core_id", None),
            "sr_required_com_specs_dict": input_dict.get("sr_required_com_specs_dict", {}),
            "sr_dm_glob_vars": input_dict.get("sr_dm_glob_vars", {}),
            "RteGeneration_dict": input_dict.get("RteGeneration", {}),
            "signal_dict": input_dict.get("signal_dict", {}),
            "task_mappings": input_dict.get("task_mappings", {}),
            "cal_prm": input_dict.get("cal_prm", {}),
        }
    elif file_template_name == "Rte_Type.h.jinja2":
        osapplication_asw_cfg = _pack_asw_cfg_by_osapplication(input_dict["asw_cfg"])
        config = {
            "sys_cfg": sys_config,
            "core_id_list": input_dict["core_id_list"],
            "datatypes": input_dict["impl_datatype_dict"],
            "asw_cfg": input_dict["asw_cfg"],
            "appl_list": input_dict["appl_list"],
            "osapplication_asw_cfg": osapplication_asw_cfg,
            "com_module_osapplication": input_dict.get("com_module_osapplication", None),
            "com_core_id": input_dict.get("com_core_id", None),
            "core_to_appl_dict": input_dict.get("core_to_appl_dict", {}),
            "appls_asw_cfg": input_dict["asw_cfg"],
            "signal_dict": input_dict.get("signal_dict", {}),
            "sr_required_com_specs_dict": input_dict.get("sr_required_com_specs_dict", {}),
            "sr_dm_glob_vars": input_dict.get("sr_dm_glob_vars", {}),
            "RteGeneration_dict": input_dict.get("RteGeneration", {}),
            "task_mappings": input_dict.get("task_mappings", {}),
            "cal_prm": input_dict.get("cal_prm", {}),
        }
        if "activation_reasons" in input_dict:
            config["activation_reasons"] = input_dict["activation_reasons"]
    return config


def generate(sys_config: dict, config_dict: dict, user_code, parser_ret, ecuc_autosar_dict=None):
    """
    generate Rte_*.c/h code
    """
    rte_result_dict = {"Rte": {"result": False}}
    input_dict = get_rte_config_dict(config_dict, user_code=user_code)
    input_dict.setdefault("vfb_trace_hooks_info", config_dict["rte"].get("vfb_trace_hooks_info"))
    output_file_dir = os.path.join(sys_config["gendata_path"])
    if parser_ret == ErrorCode.RTE_CODEGEN:
        if os.path.exists(os.path.join(sys_config["gendata_path"], "Rte")):
            shutil.rmtree(os.path.join(sys_config["gendata_path"], "Rte"))
            os.makedirs(os.path.join(sys_config["gendata_path"], "Rte"), exist_ok=True)
        else:
            os.makedirs(os.path.join(sys_config["gendata_path"], "Rte"), exist_ok=True)
        # Create required directories
        rte_output_dir = os.path.realpath(os.path.join(output_file_dir, "Rte"))
        # logger.info(f"Creating {rte_output_dir} directories if they don't already exist")
        os.makedirs(rte_output_dir, exist_ok=True)
    # elif parser_ret ==  ErrorCode.SCHM_CODEGEN:
    schm_output_dir = os.path.realpath(os.path.join(output_file_dir, "SchM"))
    if os.path.exists(schm_output_dir):
        shutil.rmtree(schm_output_dir)
    os.makedirs(schm_output_dir, exist_ok=True)
    config_dict = {
        "template_dir": DEFAULT_TEMPLATE_FILE_DIR,
        "output_dir": output_file_dir,
        "input_dict": input_dict,
        "sys_config": sys_config,
    }

    # Build our rendering environment.
    env = Environment(loader=FileSystemLoader(os.path.abspath(config_dict["template_dir"])), undefined=StrictUndefined)
    env.filters.update(context.get_filters())
    env.globals.update(context.get_functions())

    # Render all of the files.
    # We use a gross while True loop to allow state.additional_files to
    # be appended to as it is processed.

    template_file_list = env.list_templates()
    template_dict = {}
    for template_file in template_file_list:
        if not template_file.endswith(".jinja2"):
            logger.warning(f"template_file: {template_file} is not jinja2 format")
            continue
        template_dict[template_file] = env.get_template(template_file)

    try:
        if parser_ret == ErrorCode.SCHM_CODEGEN:
            output_dir = config_dict.get("output_dir")
            render_rte_schm_file(sys_config, template_dict, input_dict, output_dir, "SchM")
        if parser_ret == ErrorCode.RTE_CODEGEN:
            render_files(sys_config, template_dict, config_dict, user_code, ecuc_autosar_dict)
        rte_result_dict.update({"Rte": {"result": True}})
    except UndefinedError as e:
        # find the error location in the template
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
    return rte_result_dict


def asw_cfg_add_user_code(user_code, input_dict):
    for swc_key, swc_value in input_dict["asw_cfg"].items():
        input_dict["asw_cfg"][swc_key].update({"usercode": {}})
        input_dict["asw_cfg"][swc_key]["usercode"].update({"head_usercode": {}})
        input_dict["asw_cfg"][swc_key]["usercode"].update({"tail_usercode": {}})
        if swc_key in user_code and "head_usercode" in user_code[swc_key]:
            input_dict["asw_cfg"][swc_key]["usercode"]["head_usercode"] = user_code[swc_key]["head_usercode"]
        if swc_key in user_code and "tail_usercode" in user_code[swc_key]:
            input_dict["asw_cfg"][swc_key]["usercode"]["tail_usercode"] = user_code[swc_key]["tail_usercode"]
        if swc_key in user_code and "unmatched_runnable" in user_code[swc_key]:
            input_dict["asw_cfg"][swc_key]["usercode"]["unmatched_runnable"] = user_code[swc_key]["unmatched_runnable"]
        for runnable_key, runnable_value in swc_value["runnables"].items():
            if swc_key in user_code.keys() and runnable_key in user_code[swc_key].keys():
                input_dict["asw_cfg"][swc_key]["runnables"][runnable_key]["user_code"] = user_code[swc_key][
                    runnable_key
                ]
    return input_dict


def render_files(sys_config, template_dict, config_dict, user_code, ecuc_autosar_dict):
    """
    Render template_file.
    """
    output_dir = config_dict.get("output_dir")
    input_dict = config_dict["input_dict"]
    render_rte_type_file(sys_config, template_dict, input_dict, output_dir)
    render_rte_swc_type_file(sys_config, template_dict, input_dict, output_dir)
    render_rte_osapplication_file(sys_config, template_dict, input_dict, output_dir, ecuc_autosar_dict)
    render_rte_main_file(sys_config, template_dict, input_dict, output_dir)
    render_rte_file(sys_config, template_dict, input_dict, output_dir)
    render_rte_cbk_file(sys_config, template_dict, input_dict, output_dir)
    render_rte_schm_file(sys_config, template_dict, input_dict, output_dir, "Rte")
    render_rte_swc_h_file(sys_config, template_dict, input_dict, output_dir)
    render_rte_dlog_file(sys_config, template_dict, input_dict, output_dir, ecuc_autosar_dict)
    render_rte_user_type_h_file(sys_config, template_dict, input_dict, output_dir)
    render_rte_hook_rtm_file(sys_config, template_dict, input_dict, output_dir, ecuc_autosar_dict)
    render_rte_hook_file(sys_config, template_dict, input_dict, output_dir, ecuc_autosar_dict)


def _pack_asw_cfg_by_osapplication(asw_cfg):
    osapplication_asw_cfg = {}
    for swc_name, swc in asw_cfg.items():
        if "osapplication" not in swc or not swc["osapplication"]:
            continue
        osapplication_name = swc["osapplication"]
        if osapplication_name not in osapplication_asw_cfg:
            osapplication_asw_cfg[osapplication_name] = {}
        osapplication_asw_cfg[osapplication_name][swc_name] = swc
    return osapplication_asw_cfg


def render_rte_osapplication_file(sys_config, template_dict, input_dict, output_dir, ecuc_autosar_dict=None):
    """
    Render Rte_OsApplication.c/h template file.
    """
    template: Template = template_dict.get("Rte_OsApplication.h.jinja2")
    if template is not None:
        for appl in input_dict["appl_list"]:
            file_path = os.path.join(output_dir, f"Rte/Rte_{appl}.h")
            logger.debug(f"Start generating Rte_{appl}.h file")
            with open(file_path, "w", encoding="utf-8") as out_stream:
                # process template file
                config = {
                    "sys_cfg": sys_config,
                    "appl_name": appl,
                    "task_mappings": input_dict["appl_to_task_dict"][appl],
                    "core_to_appl_dict": input_dict.get("core_to_appl_dict", {}),
                    "RteGeneration_dict": input_dict.get("RteGeneration", {}),
                }
                out_stream.write(template.render(config))
            logger.info(f"Finish generating Rte_{appl}.h file")

    file_template_name = "Rte_OsApplication.c.jinja2"
    template = template_dict.get(file_template_name)
    if template is not None:
        for appl in input_dict["appl_list"]:
            file_path = os.path.join(output_dir, f"Rte/Rte_{appl}.c")
            logger.debug(f"Start generating Rte_{appl}.c file")
            with open(file_path, "w", encoding="utf-8") as out_stream:
                # process template file
                out_stream.write(
                    template.render(
                        get_rendering_context(file_template_name, input_dict, sys_config, appl, ecuc_autosar_dict)
                    )
                )
            logger.info(f"Finish generating Rte_{appl}.c file")


def render_rte_file(sys_config, template_dict, input_dict, output_dir):
    """
    Render Rte.c/h template file.
    """
    file_template_name = "Rte.c.jinja2"
    template: Template = template_dict.get(file_template_name)
    if template is not None:
        file_path = os.path.join(output_dir, "Rte/Rte.c")
        logger.debug("Start generating Rte.c file")
        with open(file_path, "w", encoding="utf-8") as out_stream:
            # process template file
            out_stream.write(
                template.render(get_rendering_context(file_template_name, input_dict, sys_config=sys_config))
            )
            logger.info("Finish generating Rte.c file")

    template = template_dict.get("Rte.h.jinja2")
    if template is not None:
        file_path = os.path.join(output_dir, "Rte/Rte.h")
        logger.debug("Start generating Rte.h file")
        with open(file_path, "w", encoding="utf-8") as out_stream:
            # process template file
            config = {"sys_cfg": sys_config}
            out_stream.write(template.render(config))
            logger.info("Finish generating Rte.h file")


def render_rte_main_file(sys_config, template_dict, input_dict, output_dir):
    """
    Render Rte_Main.h template file.
    """
    file_template_name = "Rte_Main.h.jinja2"
    template: Template = template_dict.get(file_template_name)
    if template is not None:
        file_path = os.path.join(output_dir, "Rte/Rte_Main.h")
        logger.debug("Start generating Rte_Main.h file")
        with open(file_path, "w", encoding="utf-8") as out_stream:
            config = {
                "sys_cfg": sys_config,
                "appl_list": input_dict["appl_list"],
                "core_id_list": input_dict["core_id_list"],
                "asw_cfg": input_dict["asw_cfg"],
                "appls_asw_cfg": input_dict["asw_cfg"],
            }
            out_stream.write(template.render(config))
        logger.info("Finish generating Rte_Main.h file")


def render_rte_hook_rtm_file(sys_config, template_dict, input_dict, output_dir, ecuc_autosar_dict):
    file_template_name = "Rte_Hook_Rtm.c.jinja2"
    template: Template = template_dict.get(file_template_name)
    if template is not None:
        file_path = os.path.join(output_dir, "Rte/Rte_Hook_Rtm.c")
        logger.debug("Start generating Rte_Hook_Rtm.c file")
        with open(file_path, "w", encoding="utf-8") as out_stream:
            config = {
                "sys_cfg": sys_config,
                "vfb_trace_hooks_info": input_dict["vfb_trace_hooks_info"],
                "ecuc_config": ecuc_autosar_dict,
            }
            out_stream.write(template.render(config))
        logger.info("Finish generating Rte_Hook_Rtm.c file")


def render_rte_hook_file(sys_config, template_dict, input_dict, output_dir, ecuc_autosar_dict):
    file_template_name = "Rte_Hook.h.jinja2"
    template: Template = template_dict.get(file_template_name)
    if template is not None:
        file_path = os.path.join(output_dir, "Rte/Rte_Hook.h")
        logger.debug("Start generating Rte_Hook.h file")
        with open(file_path, "w", encoding="utf-8") as out_stream:
            config = {
                "sys_cfg": sys_config,
                "vfb_trace_hooks_info": input_dict["vfb_trace_hooks_info"],
                "ecuc_config": ecuc_autosar_dict,
            }
            out_stream.write(template.render(config))
        logger.info("Finish generating Rte_Hook.h file")


# 该函数未被调用
def render_rte_ecum_file(template_dict, input_dict, output_dir):
    """
    Render Rte_EcuM.h template file.
    """
    template: Template = template_dict.get("Rte_EcuM.h.jinja2")
    if template is not None:
        file_path = os.path.join(output_dir, "Rte/Rte_EcuM.h")
        logger.debug("Start generating Rte_EcuM.h file")
        with open(file_path, "w", encoding="utf-8") as out_stream:
            config = {"server_swc": {"ecum_swc": input_dict["ecum_swc"]}}
            out_stream.write(template.render(config))
        logger.info("Finish generating Rte_EcuM.h file")
    template = template_dict.get("Rte_EcuM_Type.h.jinja2")
    if template is not None:
        file_path = os.path.join(output_dir, "Rte/Rte_EcuM_Type.h")
        logger.debug("Start generating Rte_EcuM_Type.h file")
        with open(file_path, "w", encoding="utf-8") as out_stream:
            out_stream.write(template.render())
        logger.info("Finish generating Rte_EcuM_Type.h file")


# 该函数未被调用
def render_rte_dcm_file(template_dict, input_dict, output_dir):
    """
    Render Dcm template_file.
    """
    template: Template = template_dict.get("Rte_Dcm_Type.h.jinja2")
    if template is not None:
        file_path = os.path.join(output_dir, "Rte/Rte_Dcm_Type.h")
        logger.debug("Start generating Rte_Dcm_Type.h file")
        with open(file_path, "w", encoding="utf-8") as out_stream:
            out_stream.write(template.render())
        logger.info("Finish generating Rte_Dcm_Type.h file")
    template = template_dict.get("Rte_Dcm.h.jinja2")
    if template is not None:
        file_path = os.path.join(output_dir, "Rte/Rte_Dcm.h")
        logger.debug("Start generating Rte_Dcm.h file")
        with open(file_path, "w", encoding="utf-8") as out_stream:
            config = input_dict["dcm_swc"]
            out_stream.write(template.render(config))
        logger.info("Finish generating Rte_Dcm.h file")


def render_rte_type_file(sys_config, template_dict, input_dict, output_dir):
    """
    Render Rte_Type.h template.
    """
    file_template_name = "Rte_Type.h.jinja2"
    template: Template = template_dict.get(file_template_name)
    if template is not None:
        file_path = os.path.join(output_dir, "Rte", "Rte_Type.h")
        logger.debug("Start generating Rte_Type.h file ......")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(template.render(get_rendering_context(file_template_name, input_dict, sys_config=sys_config)))
        logger.info("Finish generating Rte_Type.h file")


def render_rte_user_type_h_file(sys_config, template_dict, input_dict, output_dir):
    """
    Render Rte_Type.h template.
    """
    template: Template = template_dict.get("Rte_UserTypes.h.jinja2")
    if template is not None:
        config = {"sys_cfg": sys_config}
        file_path = os.path.join(output_dir, "Rte", "Rte_UserTypes.h")
        logger.debug("Start generating Rte_UserTypes.h file ......")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(template.render(config))
        logger.info("Finish generating Rte_UserTypes.h file")


def render_rte_swc_type_file(sys_config, template_dict, input_dict, output_dir):
    """
    Render Application header template_file.
    """
    template: Template = template_dict.get("Rte_Swc_Type.h.jinja2")
    if template is not None:
        for swc in input_dict["asw_cfg"].values():
            if swc.get("type", "") == "NvBlockComponent":
                continue
            if swc.get("type", "") in AutosarUtils.NO_GEN_FILE_APPL_COMPONENT_TYPE:
                continue
            swc_name = swc["name"]
            config = {"sys_cfg": sys_config, "swc": swc, "mode_declaration_group": input_dict["mode_declaration_group"]}
            swc_type_h_relative_path = f"Rte/Rte_{swc_name}_Type.h"
            swc_type_h_path = os.path.join(output_dir, swc_type_h_relative_path)
            logger.debug(f"Start generating Rte_{swc_name}_Type.h file")
            with open(swc_type_h_path, "w", encoding="utf-8") as f:
                f.write(template.render(config))
            logger.info(f"Finish generating Rte_{swc_name}_Type.h file")


def render_rte_swc_h_file(sys_config, template_dict, input_dict, output_dir):
    """
    Render Application header template_file.
    """
    template: Template = template_dict.get("Rte_Swc.h.jinja2")
    if template is not None:
        for swc_name, swc in input_dict["asw_cfg"].items():
            if swc.get("type", "") == "NvBlockComponent":
                continue
            if swc.get("type", "") in AutosarUtils.NO_GEN_FILE_APPL_COMPONENT_TYPE:
                continue
            config = {
                "sys_cfg": sys_config,
                "swc": swc,
                "com_module_osapplication": input_dict.get("com_module_osapplication", None),
                "sr_required_com_specs_dict": input_dict.get("sr_required_com_specs_dict", {}),
                "RteGeneration_dict": input_dict.get("RteGeneration", {}),
                "iso_call_func_include_header_file": input_dict.get("iso_call_func_include_header_file", {}).get(
                    swc_name, []
                ),
                "cal_prm": input_dict.get("cal_prm", {}),
            }
            file_path = os.path.join(output_dir, f"Rte/Rte_{swc_name}.h")
            logger.debug(f"Start generating Rte_{swc_name}.h file")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(template.render(config))
            logger.info(f"Finish generating Rte_{swc_name}.h file")


def render_rte_cbk_file(sys_config, template_dict, input_dict, output_dir):
    """
    Render Rte_Cbk.h template.
    """
    template: Template = template_dict.get("Rte_Cbk.h.jinja2")
    if template is not None:
        config = {
            "sys_cfg": sys_config,
            "signals_and_signalgroups": input_dict["signals_and_signalgroups"],
            "data_received_event": input_dict["data_received_event"],
            "appl_list": input_dict["appl_list"],
            "asw_cfg": input_dict["asw_cfg"],
            "osapplication_asw_cfg": input_dict.get("osapplication_asw_cfg", {}),
            "com_module_osapplication": input_dict.get("com_module_osapplication", None),
            "com_core_id": input_dict.get("com_core_id", None),
            "sr_required_com_specs_dict": input_dict.get("sr_required_com_specs_dict", {}),
            "RteGeneration_dict": input_dict.get("RteGeneration", {}),
            "signal_dict": input_dict.get("signal_dict", {}),
        }
        file_path = os.path.join(output_dir, "Rte/Rte_Cbk.h")
        logger.debug("Start generating Rte_Cbk.h file")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(template.render(config))
        logger.info("Finish generating Rte_Cbk.h file")


def render_rte_schm_file(sys_config, template_dict, input_dict, output_dir, parent_dir):
    """
    Render SchM_<Bsw>.h SchM_<Bsw>_Type.h template.
    """
    template: Template = template_dict.get("SchM.h.jinja2")
    if template is not None:
        for bsw_module_name, bsw_instance_cfg in input_dict["bsw_instances"].items():
            # if bsw_instance_cfg.get("is_mcal") and not bsw_instance_cfg.get("support_ib_gen") :
            if bsw_instance_cfg.get("is_mcal"):
                continue
            bsw_instance_cfg["module_name"] = bsw_module_name
            symbol = bsw_instance_cfg.get("symbol") or bsw_module_name
            config = {"sys_cfg": sys_config, "bsw_instances": bsw_instance_cfg}
            file_name = f"SchM_{symbol}.h"
            file_path = os.path.join(output_dir, f"{parent_dir}/{file_name}")
            logger.debug(f"Start generating {file_name} file")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(template.render(config))
            logger.info(f"Finish generating {file_name} file")

    template: Template = template_dict.get("SchM_Type.h.jinja2")
    if template is not None:
        for bsw_module_name, bsw_instance_cfg in input_dict["bsw_instances"].items():
            # if bsw_instance_cfg.get("is_mcal") and not bsw_instance_cfg.get("support_ib_gen") :
            if bsw_instance_cfg.get("is_mcal"):
                continue
            bsw_instance_cfg["module_name"] = bsw_module_name
            symbol = bsw_instance_cfg.get("symbol") or bsw_module_name
            config = {"sys_cfg": sys_config, "bsw_instances": bsw_instance_cfg}
            file_name = f"SchM_{symbol}_Type.h"
            file_path = os.path.join(output_dir, f"{parent_dir}/{file_name}")
            logger.debug(f"Start generating {file_name} file")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(template.render(config))
            logger.info(f"Finish generating {file_name} file")


def render_rte_dlog_file(sys_config, template_dict, input_dict, output_dir, ecuc_autosar_dict):
    template: Template = template_dict.get("Rte_Dlog.c.jinja2")
    if template is not None:
        file_path = os.path.join(output_dir, "Rte/Rte_Dlog.c")
        logger.debug("Start generating Rte_Dlog.c file")
        with open(file_path, "w", encoding="utf-8") as out_stream:
            config = {
                "sys_cfg": sys_config,
                "asw_cfg": input_dict["asw_cfg"],
                "ecuc_config": ecuc_autosar_dict,
            }
            out_stream.write(template.render(config))
        logger.info("Finish generating Rte_Dlog.c file")

    template: Template = template_dict.get("Rte_Dlog.h.jinja2")
    if template is not None:
        file_path = os.path.join(output_dir, "Rte/Rte_Dlog.h")
        logger.debug("Start generating Rte_Dlog.h file")
        with open(file_path, "w", encoding="utf-8") as out_stream:
            config = {
                "sys_cfg": sys_config,
                "asw_cfg": input_dict["asw_cfg"],
                "data_received_event": input_dict["data_received_event"],
                "osapplication_asw_cfg": input_dict.get("osapplication_asw_cfg", {}),
                "com_module_osapplication": input_dict.get("com_module_osapplication", None),
                "com_core_id": input_dict.get("com_core_id", None),
                "signal_dict": input_dict.get("signal_dict", {}),
                "sr_required_com_specs_dict": input_dict.get("sr_required_com_specs_dict", {}),
                "RteGeneration_dict": input_dict.get("RteGeneration", {}),
            }
            out_stream.write(template.render(config))
        logger.info("Finish generating Rte_Dlog.h file")
