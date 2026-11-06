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
def sort_module_list_based_on_dependency(module_list):
    module_list.sort()
    ind_rte = -1
    ind_os = -1
    for i, mod in enumerate(module_list):
        if mod == "Rte":
            ind_rte = i
        elif mod == "Os":
            ind_os = i
        if ind_rte > -1 and ind_os > -1:
            break
    num_mod = len(module_list)
    if (ind_rte != -1) and (ind_rte != num_mod - 1):
        module_list[ind_rte] = module_list[-1]
        module_list[-1] = "Rte"

    if (ind_os != -1) and (ind_os != 0):
        module_list[ind_os] = module_list[0]
        module_list[0] = "Os"

    # only Rte and Os module are considered now
    # other module dependencies can be resolved here later if necessary

    return module_list
