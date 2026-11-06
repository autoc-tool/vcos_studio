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
Appl代码生成模块.

解析输入的josn object, 然后生成appl代码.
"""

import os
import inspect
import shutil
from func_module.generator.rte import context
from func_module.generator.rte import filter as rte_filter
from func_module.health_monitor.logger import logger
from jinja2 import Environment, FileSystemLoader, StrictUndefined, UndefinedError, Template

CUR_FILE_PATH = os.path.dirname(__file__)
DEFAULT_TEMPLATE_FILE_DIR = os.path.join(CUR_FILE_PATH, "template")


def generate(sys_config: dict, config_dict: dict, asw_autosar_dict, user_code={}, swc_app_list: list = []):
    if swc_app_list and "asw" in asw_autosar_dict:
        return swc_generate(sys_config, config_dict, user_code, swc_app_list)
    else:
        return False

def swc_generate(sys_config: dict, config_dict: dict, user_code={}, swc_app_list: list = []):
    """
    generate Rte_swc.c code
    """
    ret = False
    input_dict = rte_filter.get_template_input_parameter_dict_from_parsed_data(config_dict["rte"])
    config_dict = {
        "template_dir": DEFAULT_TEMPLATE_FILE_DIR,
        "output_dir": sys_config["path"]["swc_template_path"],
        "input_dict": input_dict,
        "sys_config": sys_config
    }
    # Build our rendering environment.
    env = Environment(loader=FileSystemLoader(os.path.abspath(config_dict["template_dir"])), undefined=StrictUndefined)
    env.filters.update(context.get_filters())
    env.globals.update(context.get_functions())
    # render swc template
    template_file_list = env.list_templates()
    template_dict = {}
    for template_file in template_file_list:
        if not template_file.endswith(".jinja2"):
            logger.warning(f"template_file: {template_file} is not jinja2 format")
            continue
        if 'Rte_Swc.c.jinja2' == template_file:
            template_dict[template_file] = env.get_template(template_file)
    try:
        render_rte_swc_c_file(sys_config, template_dict, config_dict, user_code, swc_app_list)
        ret = True
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
    except Exception as e:
        raise e
    return ret


def asw_cfg_add_user_code(user_code, input_dict):
    key_user_code = [
        "head_usercode", "tail_usercode", "unmatched_runnable", "const_mem",
        "calib_mem", "pri_ini_mem", "pri_no_ini_mem"
    ]
    for swc_key, swc_value in input_dict["asw_cfg"].items():
        input_dict["asw_cfg"][swc_key].update({"usercode": {}})
        for key in key_user_code:
            input_dict["asw_cfg"][swc_key]["usercode"].update(
                {key: user_code.get(swc_key, {}).get(key, [])})
        for runnable_key, _ in swc_value["runnables"].items():
            input_dict["asw_cfg"][swc_key]["runnables"][runnable_key][
                "user_code"] = user_code.get(swc_key,
                                             {}).get(runnable_key, [])
    return input_dict


def render_rte_swc_c_file(sys_config, template_dict, config_dict, user_code, swc_app_list):
    """
    Render swc.c template_file.
    """
    input_dict = asw_cfg_add_user_code(user_code, config_dict["input_dict"])
    output_dir = config_dict.get("output_dir")
    if output_dir is None:
        logger.error("Output directory is not set in config")
    template: Template = template_dict.get("Rte_Swc.c.jinja2")
    if template is not None:
        if os.path.exists(output_dir) is True:
            # shutil.rmtree(output_dir)
            # os.mkdir(output_dir)
            files = os.listdir(output_dir)
            for file in files:
                # 只删除当前路径下的c文件,保留Bsw_Callout文件夹
                if file.endswith('.c') and file.replace('.c', '') in swc_app_list:
                    # 将文件进行备份
                    dest_name = file + '.back'
                    source_path = os.path.join(output_dir, file)
                    dest_path = os.path.join(output_dir, dest_name)
                    shutil.copy(source_path, dest_path)
                    # 删除原文件
                    os.remove(os.path.join(output_dir, file))
        else:
            os.makedirs(output_dir)
        for swc_name, swc in input_dict["asw_cfg"].items():
            logger.debug(f"Start generating {swc_name}.c file")
            if swc_name not in swc_app_list:
                continue
            config = {"swc": swc, "sys_cfg": sys_config, "cal_prm": input_dict.get("cal_prm", {})}
            file_path = os.path.join(output_dir, f"{swc_name}.c")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(template.render(config))
            logger.info(f"Finish generating {swc_name}.c file")
