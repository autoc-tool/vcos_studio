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
from basic_func_module.file_handler.file_io_handler import FileIOHandler
from func_module.health_monitor.logger import logger


class StudioCfgHandler:

    @classmethod
    def load_studio_cfg_file(cls, studio_system_cfg_file_path):
        data = FileIOHandler.load_json_file(studio_system_cfg_file_path)

        return data

    @classmethod
    def get_module_list(cls, codegen_modules):
        generate_list = set()
        for module_name in codegen_modules.keys():
            generate_list.add(module_name)

        return generate_list

    @classmethod
    def get_validate_list(cls, studio_system_cfg_dict):
        validate_list = []

        return validate_list

    @classmethod
    def get_all_module_list(cls, studio_system_cfg_dict):
        all_module_list = set()
        for key, value in studio_system_cfg_dict["module_cfg"].items():
            if value.get("support_ui", False) is False:
                continue
            else:
                all_module_list.add(key)

        return all_module_list

    @classmethod
    def get_mcal_module_list(cls, sys_target_class: dict = None):
        mcal_module_list = set()
        for key, value in sys_target_class["module_cfg"].items():
            if value.get("is_mcal", None) and value["is_mcal"] is True:
                mcal_module_list.add(key)

        return mcal_module_list

    @classmethod
    def get_gen_or_validation_module_list(
        cls, enable_module_dict: dict = None, sys_target_class: dict = None, gen_or_val: str = ""
    ):
        """
        1.json中获取codegen 或者 validation module list
        2.codegen 和 validation 通用
        3.gen_or_val来区分codegen 或validation
        """
        ret_module_dict: dict = {}
        if not enable_module_dict or not sys_target_class:
            logger.error("Configuration not exist!")
        module_cfg = sys_target_class["module_cfg"]
        module_dict = {}
        for instance_name, module_name in enable_module_dict.items():
            config = module_cfg.get(module_name, {})
            if not config.get("support_ui", False) or not config.get(gen_or_val, False):
                continue
            module_dict.setdefault(module_name, []).append(instance_name)
            group: list = config["group"]
            dependency_list: list = config["dependency_list"]
            ret_module_dict.setdefault(instance_name, {})
            ret_module_dict[instance_name]["group"] = group
            ret_module_dict[instance_name]["module_name"] = module_name
            ret_module_dict[instance_name]["dependency_list"] = dependency_list
        for instance_name in ret_module_dict:
            dependency_list = ret_module_dict[instance_name]["dependency_list"]
            new_dependency_list = []
            for dependency_module in dependency_list:
                new_dependency_list.extend(module_dict.get(dependency_module, []))
            ret_module_dict[instance_name]["dependency_list"] = new_dependency_list
        return ret_module_dict

    @classmethod
    def get_target_compiler(cls, sys_target_dict):
        """get compiler list of all targets"""

        return sys_target_dict["target"]
