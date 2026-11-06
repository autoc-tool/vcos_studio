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
from abc import ABCMeta
import time
from func_module.validation.common.validation_def import ValidationLog


def timing_decorator(function):

    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = function(*args, **kwargs)
        end_time = time.time()
        rule_name = args[0].__module__.split(".")[-1]
        if rule_name in args[0].logs:
            args[0].logs[rule_name]["time"] = end_time - start_time
        return result

    return wrapper


class BasicRule(ValidationLog, metaclass=ABCMeta):

    # @abstractmethod
    def check(self):
        pass

    def check_validation_run(self) -> bool:
        return True

    def modules_are_exist(self, module_list: list, bsw_autosar_dict: dict) -> bool:
        if not bsw_autosar_dict:
            return False
        for module in module_list:
            key_list = [module, "ArPackages", "ActiveEcuC", module]
            curr_dict = bsw_autosar_dict
            for key in key_list:
                if key not in curr_dict.keys():
                    return False
                curr_dict = curr_dict[key]
        return True
