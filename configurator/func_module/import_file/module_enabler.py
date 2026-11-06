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
import importlib
from enum import Enum
from func_module.health_monitor.logger import logger
from func_module.module_management.module_management import ModuleManagement


def dbc_auxiliary_info(file_info_dict: dict):
    """
    Gather all value of msg attr.
    Mainly used for module enablement check
    """
    attr_dict = {}
    for file_info in file_info_dict.values():
        dbc_info = file_info["parse_result"]
        for msg_val in dbc_info["details"].values():
            for name, obj in getattr(msg_val, "message_attributes", {}).items():
                val_set: set = attr_dict.setdefault(name, set())
                hasattr(obj, "value") and val_set.add(obj.value)

    return attr_dict


def check_simple_dbc_rule(rule: dict, auxiliary_dict: dict):
    # Empty rule means always add module
    if len(rule) == 0:
        return True
    elif len(rule) == 1:
        # Get the only one item of rule
        msg_attr, state = next(iter(rule.items()))
        if state in auxiliary_dict.get(msg_attr, set()):
            return True
        return False
    # More than one item is invalid
    else:
        logger.error(f"Invalid dbc rule: {rule}")
        return False


def check_simple_ldf_rule(rule: dict, auxiliary_dict: dict):
    if len(rule) == 0:
        return True
    else:
        logger.error(f"Invalid ldf rule: {rule}")
        return False


def check_simple_cdd_rule(rule: dict, auxiliary_dict: dict):
    if len(rule) == 0:
        return True
    else:
        logger.error(f"Invalid cdd rule: {rule}")
        return False


class FileType(Enum):
    DBC = {"string": "dbc", "auxi_gen": dbc_auxiliary_info, "simple_checker": check_simple_dbc_rule}
    LDF = {"string": "ldf", "auxi_gen": lambda x: x, "simple_checker": check_simple_ldf_rule}
    CDD = {"string": "cdd", "auxi_gen": lambda x: x, "simple_checker": check_simple_cdd_rule}

    @property
    def string(self):
        return self.value["string"]

    def gen_auxiliary(self, file_info):
        return self.value["auxi_gen"](file_info)

    def simple_check(self, rule, auxiliary_dict):
        return self.value["simple_checker"](rule, auxiliary_dict)


def complex_check(type: FileType, module_name: str, file_info):
    type_string = type.string
    module_name = module_name.lower()
    # For complex rule, load the module checker and get its checker function
    try:
        checker_module = importlib.import_module(f"func_module.import_file.{module_name}_checker")
        checker_func = getattr(checker_module, f"{type_string}_checker")
    # If cannot find checker, return False
    except ModuleNotFoundError:
        logger.error(f"Cannot find module: func_module.import_file.{module_name}_checker")
        return False
    # If cannot find the checker func, return False
    except AttributeError:
        logger.error(f"Cannot find {type_string}_checker in func_module.import_file.{module_name}_checker")
        return False
    return checker_func(file_info)


def enable_modules(type: FileType, file_info: dict, sys_target_dict: dict, module_manage: ModuleManagement):
    rule_dict: dict = sys_target_dict[f"{type.string}_family"]
    auxiliary_dict = type.gen_auxiliary(file_info)
    for module_name, rule in rule_dict.items():
        if isinstance(rule, dict):
            if type.simple_check(rule, auxiliary_dict):
                module_manage.append_module(module_name)
        else:
            if complex_check(type, module_name, file_info):
                module_manage.append_module(module_name)
