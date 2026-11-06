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
from func_module.module_management.arxml_handler.config_comparator import ConfigComparator
from basic_func_module.autosar_utils.utils import get_short_name


class ComStackEcucBaseClass:

    def __init__(self, module_name, sort_container_path_list=[]):
        self.module_name = module_name
        self.sort_container_path_list = sort_container_path_list

    def set_module_name(self, module_name):
        self.module_name = module_name

    def get_new_ecuc_from_different_initial(self, old_initial, new_initial, autosar_ecuc):
        """
        get new communication protocol stack modules ecuc according to old_initial and new_initial

        """
        new_initial_module = new_initial.find(f"/InitialEcuC/{self.module_name}")
        old_initial_module = old_initial.find(f"/InitialEcuC/{self.module_name}")

        if new_initial_module is None or old_initial_module is None:
            return autosar_ecuc

        # Compare the difference between two config
        initial_ecuc_comparator = ConfigComparator(old_initial_module, new_initial_module)
        initial_ecuc_comparator.config_comparator()
        new_ecuc = initial_ecuc_comparator.update_ecuc_config(autosar_ecuc)
        self.container_sort(new_ecuc)
        return new_ecuc

    def container_sort(self, ecuc_autosar):
        for sort_container_path in self.sort_container_path_list:
            sort_list = ecuc_autosar.find(sort_container_path)
            if sort_list is not None:
                if isinstance(getattr(sort_list.SUB_CONTAINERS, "ECUC_CONTAINER_VALUE"), list):
                    sort_list.SUB_CONTAINERS.ECUC_CONTAINER_VALUE.sort(key=lambda x: get_short_name(x))
        return ecuc_autosar
