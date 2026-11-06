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
from basic_func_module.base_common.singleton import Singleton


class DataManagement(Singleton):

    def __init__(self) -> None:
        self.__sys_info_class = None
        self.__cfg_info_dict = {"ldf": None, "dbc": None, "eb": {}, "sidl_sdepl": {}}
        self.__autosar_asw_class = None
        self.__autosar_bsw_class = {}
        self.__autosar_system_class = {}
        self.__autosar_ib_class = {}
        self.__autosar_bswmd_class = {}
        self.__sys_target_dict = {}
        self.__component_arxml_path_dict = {"asw_component": {}}
        self.__all_module_list = set()
        self.__enable_module_list = set()
        self.__all_module_stack_dict = {}
        self.__sys_secondary_cfg_dict = {}
        self.__save_as_sys_info_class = {}
        self.__module_container_pre_cfg_dict = {}

    @property
    def all_module_stack_dict(self):
        return self.__all_module_stack_dict

    @all_module_stack_dict.setter
    def all_module_stack_dict(self, val):
        self.__all_module_stack_dict = val

    @property
    def enable_module_list(self):
        return self.__enable_module_list

    @enable_module_list.setter
    def enable_module_list(self, val):
        self.__enable_module_list = val

    @property
    def component_arxml_path_dict(self):
        return self.__component_arxml_path_dict

    @component_arxml_path_dict.setter
    def component_arxml_path_dict(self, val):
        self.__component_arxml_path_dict = val

    @property
    def all_module_list(self):
        return self.__all_module_list

    @all_module_list.setter
    def all_module_list(self, val):
        self.__all_module_list = val

    @property
    def sys_target_dict(self):
        return self.__sys_target_dict

    @sys_target_dict.setter
    def sys_target_dict(self, val):
        self.__sys_target_dict = val

    @property
    def sys_info_class(self):
        return self.__sys_info_class

    @sys_info_class.setter
    def sys_info_class(self, val):
        self.__sys_info_class = val

    @property
    def cfg_info_dict(self):
        return self.__cfg_info_dict

    @cfg_info_dict.setter
    def cfg_info_dict(self, val):
        self.__cfg_info_dict = val

    @property
    def autosar_asw_class(self):
        return self.__autosar_asw_class

    @autosar_asw_class.setter
    def autosar_asw_class(self, val):
        self.__autosar_asw_class = val

    @property
    def autosar_bsw_class(self):
        return self.__autosar_bsw_class

    @autosar_bsw_class.setter
    def autosar_bsw_class(self, val):
        if isinstance(val, dict):
            self.__autosar_bsw_class = val

    @property
    def autosar_system_class(self):
        return self.__autosar_system_class

    @autosar_system_class.setter
    def autosar_system_class(self, val):
        if isinstance(val, dict):
            self.__autosar_system_class = val

    @property
    def autosar_ib_class(self):
        return self.__autosar_ib_class

    @autosar_ib_class.setter
    def autosar_ib_class(self, val):
        if isinstance(val, dict):
            self.__autosar_ib_class = val

    @property
    def autosar_bswmd_class(self):
        return self.__autosar_bswmd_class

    @autosar_bswmd_class.setter
    def autosar_bswmd_class(self, val):
        if isinstance(val, dict):
            self.__autosar_bswmd_class = val
        else:
            self.__autosar_bswmd_class["All"] = val

    @property
    def autosar_ib(self):
        return self.__autosar_ib_class

    @autosar_ib.getter
    def autosar_ib(self, ib_name):
        return self.__autosar_ib_class.get(ib_name)

    @property
    def sys_secondary_cfg_dict(self):
        return self.__sys_secondary_cfg_dict

    @sys_secondary_cfg_dict.setter
    def sys_secondary_cfg_dict(self, val):
        self.__sys_secondary_cfg_dict = val

    @property
    def save_as_sys_info_class(self):
        return self.__save_as_sys_info_class

    @save_as_sys_info_class.setter
    def save_as_sys_info_class(self, val):
        self.__save_as_sys_info_class = val

    @property
    def module_container_pre_cfg_dict(self):
        return self.__module_container_pre_cfg_dict

    @module_container_pre_cfg_dict.setter
    def module_container_pre_cfg_dict(self, val):
        self.__module_container_pre_cfg_dict = val

    def clear_data_management(self):
        self.__sys_info_class = None
        self.__cfg_info_dict = {"ldf": None, "dbc": None, "eb": {}, "sidl_sdepl": {}}
        self.__autosar_asw_class = None
        self.__autosar_bsw_class = {}
        self.__autosar_system_class = {}
        self.__autosar_ib_class = {}
        self.__autosar_bswmd_class = {}
        self.__sys_target_dict = {}
        self.__all_module_list = set()
        self.__enable_module_list = set()
        self.__all_module_stack_dict = {}
        self.__sys_secondary_cfg_dict = {}
        self.__save_as_sys_info_class = {}
        self.__module_container_pre_cfg_dict = {}
