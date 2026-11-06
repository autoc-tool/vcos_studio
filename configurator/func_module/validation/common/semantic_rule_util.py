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
import json
import re
from func_module.validation.common.validation_def import SemanticRuleData
from func_module.health_monitor.logger import logger
from basic_func_module.autosar_utils.utils import get_upper_multiplicity, get_upper_multiplicity_infinite


class SemanticRuleUtil:

    plug_in_path = ""

    @classmethod
    def update_plug_in_path(cls, plug_in_path):
        cls.plug_in_path = plug_in_path

    @classmethod
    def get_module_cfg_path(cls, module_name):
        """get the validation cfg file path of the module"""
        validation_dir = os.path.abspath(
            os.path.join(cls.plug_in_path.get(module_name, ""), "config_plug_in/validation")
        )
        config_file_path = os.path.join(validation_dir, "config", f"{module_name}_semantic_rule.json")

        return config_file_path

    @classmethod
    def load_semantic_rule(cls, module_name_list: list = []):
        """加载语义校验规则配置文件"""
        semantic_rules_dict: dict = {}
        for module_name in module_name_list:
            config_file_path = cls.get_module_cfg_path(module_name)
            if os.path.exists(config_file_path) is False:
                logger.info(f"File '{config_file_path}' not found, and there are no platform based validation rules.")
                continue
            with open(config_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                semantic_rules_dict[module_name] = {}
                for k, v in data.items():
                    semantic_rules_dict[module_name][k] = SemanticRuleData(
                        module_name,
                        v["rule_name"],
                        v["rule_type"],
                        v["rule_ruleset"],
                        v["rule_summary"],
                        v["rule_message"],
                        v.get("auto_solve_list", []),
                        v.get("manual_solve_list", []),
                    )

        return semantic_rules_dict

    @classmethod
    def find_validated_container(cls, base_path, ecuc_obj, ecuc_path, container_list=None):
        """获取被校验配置项的container数据和路径"""
        if container_list is None:
            container_list = []

        for k, v in ecuc_obj.items():
            if k == "DefinitionRef":
                if v == base_path:
                    return [(ecuc_path, ecuc_obj)]
                else:
                    continue
            if not isinstance(v, dict) or "Locked" == k:
                continue

            if base_path == v["DefinitionRef"]:
                container_list.append((f"{ecuc_path}/{k}", v))
            elif base_path.startswith(v["DefinitionRef"]):
                cls.find_validated_container(base_path, v, f"{ecuc_path}/{k}", container_list)

        return container_list

    @classmethod
    def find_validated_parameter(cls, mod_path, ecuc_obj, ecuc_path, validated_data_list=None):
        """获取被校验配置项的数据和路径"""
        if validated_data_list is None:
            validated_data_list = []

        for k, v in ecuc_obj.items():
            if k == "DefinitionRef" or not isinstance(v, dict):
                continue
            if mod_path == v["DefinitionRef"]:
                validated_data_list.append(
                    {"param_value": cls.get_param_value(v), "param_path": f"{ecuc_path}/{mod_path.split('/')[-1]}"}
                )
            elif mod_path.startswith(v["DefinitionRef"]):
                cls.find_validated_parameter(mod_path, v, f"{ecuc_path}/{k}", validated_data_list)

        return validated_data_list

    @classmethod
    def get_param_value(cls, param_obj):
        param_value = ""
        if "Value" in param_obj:
            param_value = param_obj["Value"]
        elif "ValueRef" in param_obj:
            param_value = param_obj["ValueRef"]
        elif "ValueIRef" in param_obj:
            param_value = param_obj["ValueIRef"]

        return param_value

    @classmethod
    def is_multi_instance_param(cls, module_name, mod_path, autosar_mod_class):
        param_def = autosar_mod_class[module_name].find(mod_path)
        if get_upper_multiplicity(param_def) > 1 or get_upper_multiplicity_infinite(param_def):
            return True
        return False

    @classmethod
    def str_to_num(cls, in_str: str):
        ret_num = None
        try:
            if in_str.startswith("0x") or in_str.startswith("0X"):
                ret_num = int(in_str, 16)
            elif in_str.startswith("0o") or in_str.startswith("0O"):
                ret_num = int(in_str, 8)
            elif in_str.startswith("0b") or in_str.startswith("0B"):
                ret_num = int(in_str, 2)
            else:
                try:
                    ret_num = int(in_str)
                except ValueError:
                    ret_num = float(in_str)
        except Exception:
            return ret_num
        return ret_num

    @staticmethod
    def get_parent_path(param_path):
        return os.path.dirname(param_path)

    @classmethod
    def param_value_2_expression_str(cls, param_value):
        # convert param_value to string according to its type
        if isinstance(param_value, (int, float)):
            return str(param_value)
        elif isinstance(param_value, str):
            if len(param_value) > 2 and param_value[0:2] in ("0x", "0o", "0b", "0X", "0O", "0B"):
                return str(param_value)
            elif param_value.lower() in ["true", "false"]:
                return str(param_value)
        elif not param_value:
            return str(param_value)
        elif isinstance(param_value, list) or isinstance(param_value, dict) or isinstance(param_value, set):
            return f"{param_value}"

        return f"'{param_value}'"

    @staticmethod
    def get_module_name_from_mod_path(mod_path: str):
        MODULE_IDX_IN_MOD_PATH = 3
        return mod_path.split("/")[MODULE_IDX_IN_MOD_PATH]

    @staticmethod
    def check_ipv4_address(ip_addr_str: str):
        if not str:
            return False
        ip_parts = ip_addr_str.split(".")
        return all([part.isdigit() and 0 <= int(part) <= 255 for part in ip_parts])

    @staticmethod
    def is_valid_function_name(function_name):
        """Check if the function name definition is reasonable"""
        pattern = r"^[a-zA-Z_][a-zA-Z0-9_]*$"
        if re.match(pattern, function_name):
            return True
        else:
            return False

    @staticmethod
    def is_valid_header_name(name):
        """Check if the header file definition is reasonable"""
        pattern = r"^[a-zA-Z_][a-zA-Z0-9_\.]*\.(h|H)$"
        if re.match(pattern, name):
            return True
        else:
            return False
