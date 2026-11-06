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
配置代码生成模块.
根据输入的config.json, 然后生成模块代码.
"""
import os
from . import context
from func_module.health_monitor.logger import logger
from jinja2 import Environment, FileSystemLoader, StrictUndefined, Template

CUR_FILE_PATH = os.path.dirname(__file__)
DEFAULT_TEMPLATE_FILE_DIR = os.path.join(CUR_FILE_PATH, "template")


def generate_project_cmake(sys_config: dict):
    result_dict = {"cmake": {"result": False}}
    logger.debug("Generate CMakeLists.txt file")
    try:
        template_dir = os.path.join(DEFAULT_TEMPLATE_FILE_DIR)
        output_dir = os.path.realpath(os.path.join(sys_config["gendata_path"]))
        env = Environment(loader=FileSystemLoader(os.path.abspath(template_dir)), undefined=StrictUndefined)
        env.filters.update(context.get_filters())
        env.globals.update(context.get_functions())
        render_cmakelists_file(env, output_dir, {"sys_config": sys_config})
        result_dict["cmake"]["result"] = True
        logger.info(f"Finish generating {output_dir}CMakeLists.txt file")
    except Exception as e:
        logger.exception(f"Error generating CMakeLists.txt file {e}")
    finally:
        return result_dict


def render_cmakelists_file(env, output_dir, config):

    template: Template = env.get_template("CMakeLists.txt.jinja2")
    file_path = os.path.join(output_dir, "CMakeLists.txt")
    if template is not None:
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))
        with open(file_path, "w", encoding="utf-8") as out_stream:
            out_stream.write(template.render(config))

    template: Template = env.get_template("gen_data.config.jinja2")
    file_path = os.path.join(output_dir, "gen_data.config")
    if template is not None:
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))
        with open(file_path, "w", encoding="utf-8") as out_stream:
            out_stream.write(template.render(config))


