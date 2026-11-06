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
from cmd_adaptor.data_management.data_management import DataManagement

data_management = DataManagement()


def get_sys_info_class():
    return data_management.sys_info_class


def get_cfg_info_dict():
    return data_management.cfg_info_dict


def get_autosar_asw_class():
    return data_management.autosar_asw_class


def get_autosar_bsw_class():
    return data_management.autosar_bsw_class


def get_autosar_system_class():
    return data_management.autosar_system_class


def get_autosar_ib_class():
    return data_management.autosar_ib_class


def get_autosar_bswmd_class():
    return data_management.autosar_bswmd_class


def get_sys_target_dict():
    return data_management.sys_target_dict


def get_component_arxml_path_dict():
    return data_management.component_arxml_path_dict


def get_module_stack_dict():
    return data_management.all_module_stack_dict


def get_all_module_list():
    return data_management.all_module_list
