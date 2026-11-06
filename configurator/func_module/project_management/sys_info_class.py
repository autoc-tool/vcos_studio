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
from copy import deepcopy
from jsonschema import validate

LDF_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "num": {"type": "number"},
        "list": {
            "type": "object",
            "patternProperties": {
                ".*": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "node_selected": {"type": "string"},
                        "node_list": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["path", "node_selected", "node_list"],
                }
            },
        },
    },
    "required": ["num", "list"],
}

DBC_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "num": {"type": "number"},
        "list": {
            "type": "object",
            "patternProperties": {
                ".*": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "node_selected": {"type": "string"},
                        "node_list": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["path", "node_selected", "node_list"],
                }
            },
        },
    },
    "required": ["num", "list"],
}

CDD_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "num": {"type": "number"},
        "list": {
            "type": "object",
            "patternProperties": {
                ".*": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                    },
                    "additionalProperties": False,
                    "required": ["path"],
                }
            },
        },
        "single_signal": {"type": "boolean"},
    },
    "required": ["num", "list"],
}


class SysInfoClass:

    def __init__(self):
        self.__project_path = ""
        self.__project = ""
        self.__version = ""
        self.__system_version = ""
        self.__import_plugin_path_list = []
        self.__compiler = ""
        self.__target = ""
        self.__all_modules = set()
        self.__enable_modules = set()
        self.__codegen_module_dict = {}
        self.__codegen_modules = set()
        self.__validate_modules = set()
        self.__kfg_module_enabled_list = set()
        self.__kfg_module_all_list = {}
        self.__bsw_ecuc_hash = {}
        self.__codegen_swcs = set()
        self.__config_base_path = ""
        self.__gendata_path = ""
        self.__swc_template_path = ""
        self.__bswcallout_path = ""
        self.__user_plugin_output_path = ""
        self.__ldf = ({"num": 0, "list": {}},)
        self.__dbc = ({"num": 0, "list": {}},)
        self.__cdd = ({"num": 0, "list": {}, "single_signal": False},)
        self.__excel = {}
        self.__swc = ""
        self.__eb_arxml = ""
        self.__bsw_cfg = ""
        self.__communication = ""
        self.__flatextract = ""
        self.__flatmap = ""
        self.__systemextract = ""
        self.__diagnostics_description_data = ""
        self.__initial = ""
        self.__studio_path = ""
        self.__application_path = ""
        self.__internal_behavior_path = ""
        self.__log_path = ""
        self.__service_component_path = ""
        self.__compiler_path = ""
        self.__mode = ""
        self.__incremental_generation = False
        self.__mcal_path = ""
        self.__mcal_gendata_path = ""
        self.__system_path = ""
        self.__system_target_info = {}
        self.__resource_statistics_cfg = {}
        self.__generation_limit = "Error"
        self.__sys_secondary_cfg_dict = {}
        self.__linkage_cfg_dict = {}  # 配置项联动设置
        self.__plug_in_path = {}
        self.__plug_in_ib_path = {}
        self.__plug_in_bswmd_path = {}
        self.__mcal_version = ""
        self.__is_add_channel_name = False
        self.__cfg_hash = {"bsw": {}, "system": {}, "internal_behavior": {}}

    @property
    def cfg_hash(self):
        return self.__cfg_hash

    @cfg_hash.setter
    def cfg_hash(self, val):
        if isinstance(val, dict):
            self.__cfg_hash = val
        else:
            raise ProjectInfoError("Invalid value for cfg_hash")

    @property
    def plug_in_ib_path(self):
        return self.__plug_in_ib_path

    @plug_in_ib_path.setter
    def plug_in_ib_path(self, val):
        if isinstance(val, dict):
            self.__plug_in_ib_path = val
        else:
            raise ProjectInfoError("Invalid value for plug_in_ib_path")

    @property
    def is_add_channel_name(self):
        return self.__is_add_channel_name

    @is_add_channel_name.setter
    def is_add_channel_name(self, val):
        if isinstance(val, bool):
            self.__is_add_channel_name = val
        else:
            raise ProjectInfoError("Invalid value for is_add_channel_name")

    @property
    def plug_in_bswmd_path(self):
        return self.__plug_in_bswmd_path

    @plug_in_bswmd_path.setter
    def plug_in_bswmd_path(self, val):
        if isinstance(val, dict):
            self.__plug_in_bswmd_path = val
        else:
            raise ProjectInfoError("Invalid value for plug_in_bswmd_path")

    @property
    def mcal_version(self):
        return self.__mcal_version

    @mcal_version.setter
    def mcal_version(self, val):
        if isinstance(val, str):
            self.__mcal_version = val
        else:
            raise ProjectInfoError("Invalid value for mcal_version")

    @property
    def mcal_path(self):
        return self.__mcal_path

    @mcal_path.setter
    def mcal_path(self, val):
        if isinstance(val, str):
            self.__mcal_path = val
        else:
            raise ProjectInfoError("Invalid value for mcal_path")

    @property
    def mcal_gendata_path(self):
        return self.__mcal_gendata_path

    @mcal_gendata_path.setter
    def mcal_gendata_path(self, val):
        if isinstance(val, str):
            self.__mcal_gendata_path = val
        else:
            raise ProjectInfoError("Invalid value for mcal_gendata_path")

    @property
    def import_plugin_path_list(self):
        return self.__import_plugin_path_list

    @import_plugin_path_list.setter
    def import_plugin_path_list(self, val):
        if isinstance(val, list):
            self.__import_plugin_path_list = val
        else:
            raise ProjectInfoError("Invalid value for import_plugin_path_list")

    @property
    def system_path(self):
        return self.__system_path

    @system_path.setter
    def system_path(self, val):
        if isinstance(val, str):
            self.__system_path = val
        else:
            raise ProjectInfoError("Invalid value for system_path")

    @property
    def plug_in_path(self):
        return self.__plug_in_path

    @plug_in_path.setter
    def plug_in_path(self, val):
        if isinstance(val, dict):
            self.__plug_in_path = val
        else:
            raise ProjectInfoError("Invalid value for plug_in_path")

    @property
    def sys_secondary_cfg_dict(self):
        return self.__sys_secondary_cfg_dict

    @sys_secondary_cfg_dict.setter
    def sys_secondary_cfg_dict(self, val):
        if isinstance(val, dict):
            self.__sys_secondary_cfg_dict = val
        else:
            raise ProjectInfoError("Invalid value for sys_secondary_cfg_dict")

    @property
    def linkage_cfg_dict(self):
        return self.__linkage_cfg_dict

    @linkage_cfg_dict.setter
    def linkage_cfg_dict(self, val):
        if isinstance(val, dict):
            self.__linkage_cfg_dict = val
        else:
            raise ProjectInfoError("Invalid value for linkage_cfg_dict")

    @property
    def system_target_info(self):
        return self.__system_target_info

    @system_target_info.setter
    def system_target_info(self, val):
        if isinstance(val, dict):
            self.__system_target_info = val
        else:
            raise ProjectInfoError("Invalid value for system_target_info")

    @property
    def resource_statistics_cfg(self):
        return self.__resource_statistics_cfg

    @resource_statistics_cfg.setter
    def resource_statistics_cfg(self, val):
        if isinstance(val, dict):
            self.__resource_statistics_cfg = val
        else:
            raise ProjectInfoError("Invalid value for resource_statistics_cfg")

    @property
    def validate_modules(self):
        return deepcopy(self.__validate_modules)

    @validate_modules.setter
    def validate_modules(self, val):
        if isinstance(val, set):
            self.__validate_modules = deepcopy(val)
        else:
            raise ProjectInfoError("Invalid value for validate_modules")

    @property
    def project_path(self):
        return self.__project_path

    @project_path.setter
    def project_path(self, val):
        if isinstance(val, str):
            self.__project_path = val
        else:
            raise ProjectInfoError("Invalid value for project_path")

    @property
    def kfg_module_enabled_list(self):
        return self.__kfg_module_enabled_list

    @kfg_module_enabled_list.setter
    def kfg_module_enabled_list(self, val):
        self.__kfg_module_enabled_list = val

    @property
    def kfg_module_all_list(self):
        return self.__kfg_module_all_list

    @property
    def bsw_ecuc_hash(self):
        return self.__bsw_ecuc_hash

    @kfg_module_all_list.setter
    def kfg_module_all_list(self, val):
        if isinstance(val, dict):
            self.__kfg_module_all_list = val
        else:
            raise ProjectInfoError("Invalid value for kfg_module_all_list")

    @bsw_ecuc_hash.setter
    def bsw_ecuc_hash(self, val):
        if isinstance(val, dict):
            self.__bsw_ecuc_hash = val
        else:
            raise ProjectInfoError("Invalid value for bsw_ecuc_hash")

    @property
    def project(self):
        return self.__project

    @project.setter
    def project(self, val):
        if isinstance(val, str):
            self.__project = val
        else:
            raise ProjectInfoError("Invalid value for project")

    @property
    def version(self):
        return self.__version

    @version.setter
    def version(self, val):
        if isinstance(val, str):
            self.__version = val
        else:
            raise ProjectInfoError("Invalid value for version")

    @property
    def system_version(self):
        return self.__system_version

    @system_version.setter
    def system_version(self, val):
        if isinstance(val, str):
            self.__system_version = val
        else:
            raise ProjectInfoError("Invalid value for system_versions")

    @property
    def compiler(self):
        return self.__compiler

    @compiler.setter
    def compiler(self, val):
        if isinstance(val, str):
            self.__compiler = val
        else:
            raise ProjectInfoError("Invalid value for compiler")

    @property
    def target(self):
        return deepcopy(self.__target)

    @target.setter
    def target(self, val):
        if isinstance(val, str):
            self.__target = val
        else:
            raise ProjectInfoError("Invalid value for target")

    @property
    def all_modules(self):
        return deepcopy(self.__all_modules)

    @all_modules.setter
    def all_modules(self, val):
        if isinstance(val, set):
            self.__all_modules = deepcopy(val)
        else:
            raise ProjectInfoError("Invalid value for all_modules")

    @property
    def enable_modules(self):
        return deepcopy(self.__enable_modules)

    @enable_modules.setter
    def enable_modules(self, val):
        if isinstance(val, set):
            self.__enable_modules = deepcopy(val)
        else:
            raise ProjectInfoError("Invalid value for enable_modules")

    @property
    def codegen_modules(self):
        return deepcopy(self.__codegen_modules)

    @codegen_modules.setter
    def codegen_modules(self, val):
        if isinstance(val, set):
            self.__codegen_modules = deepcopy(val)
        else:
            raise ProjectInfoError("Invalid value for codegen_modules")

    @property
    def codegen_module_dict(self):
        return deepcopy(self.__codegen_module_dict)

    @codegen_module_dict.setter
    def codegen_module_dict(self, val):
        if isinstance(val, dict):
            self.__codegen_module_dict = deepcopy(val)
        else:
            raise ProjectInfoError("Invalid value for codegen_module_dict")

    @property
    def codegen_swcs(self):
        return deepcopy(self.__codegen_swcs)

    @codegen_swcs.setter
    def codegen_swcs(self, val):
        if isinstance(val, set):
            self.__codegen_swcs = deepcopy(val)
        else:
            raise ProjectInfoError("Invalid value for codegen_swcs")

    @property
    def config_base_path(self):
        return self.__config_base_path

    @config_base_path.setter
    def config_base_path(self, val):
        if isinstance(val, str):
            self.__config_base_path = val
        else:
            raise ProjectInfoError("Invalid value for config_base_path")

    @property
    def gendata_path(self):
        return deepcopy(self.__gendata_path)

    @gendata_path.setter
    def gendata_path(self, val):
        if isinstance(val, str):
            self.__gendata_path = val
        else:
            raise ProjectInfoError("Invalid value for gendata_path")

    @property
    def swc_template_path(self):
        return self.__swc_template_path

    @swc_template_path.setter
    def swc_template_path(self, val):
        if isinstance(val, str):
            self.__swc_template_path = val
        else:
            raise ProjectInfoError("Invalid value for swc_template_path")

    @property
    def bswcallout_path(self):
        return self.__bswcallout_path

    @bswcallout_path.setter
    def bswcallout_path(self, val):
        if isinstance(val, str):
            self.__bswcallout_path = val
        else:
            raise ProjectInfoError("Invalid value for bswcallout_path")

    @property
    def user_plugin_output_path(self):
        return self.__user_plugin_output_path

    @user_plugin_output_path.setter
    def user_plugin_output_path(self, val):
        if isinstance(val, str):
            self.__user_plugin_output_path = val
        else:
            raise ProjectInfoError("Invalid value for user_plugin_output_path")

    @property
    def ldf(self):
        return deepcopy(self.__ldf)

    @ldf.setter
    def ldf(self, val):
        if isinstance(val, dict):
            validate(instance=val, schema=LDF_INFO_SCHEMA)
            self.__ldf = deepcopy(val)
        else:
            raise ProjectInfoError("Invalid value for ldf")

    @property
    def dbc(self):
        return deepcopy(self.__dbc)

    @dbc.setter
    def dbc(self, val):
        if isinstance(val, dict):
            validate(instance=val, schema=DBC_INFO_SCHEMA)
            self.__dbc = deepcopy(val)
        else:
            raise ProjectInfoError("Invalid value for dbc")

    @property
    def cdd(self):
        return deepcopy(self.__cdd)

    @cdd.setter
    def cdd(self, val):
        if isinstance(val, dict):
            validate(instance=val, schema=CDD_INFO_SCHEMA)
            self.__cdd = deepcopy(val)
        else:
            raise ProjectInfoError("Invalid value for cdd")

    @property
    def excel(self):
        return deepcopy(self.__excel)

    @excel.setter
    def excel(self, val):
        if isinstance(val, dict):
            self.__excel = val
        else:
            raise ProjectInfoError("Invalid value for excel")

    @property
    def swc(self):
        return self.__swc

    @swc.setter
    def swc(self, val):
        if isinstance(val, str):
            self.__swc = val
        else:
            raise ProjectInfoError("Invalid value for swc")

    @property
    def eb_arxml(self):
        return self.__eb_arxml

    @eb_arxml.setter
    def eb_arxml(self, val):
        if isinstance(val, str):
            self.__eb_arxml = val
        else:
            raise ProjectInfoError("Invalid value for eb_arxml")

    @property
    def bsw_cfg(self):
        return deepcopy(self.__bsw_cfg)

    @bsw_cfg.setter
    def bsw_cfg(self, val):
        if isinstance(val, dict):
            self.__bsw_cfg = deepcopy(val)
        else:
            raise ProjectInfoError("Invalid value for bsw_cfg")

    @property
    def communication(self):
        return self.__communication

    @communication.setter
    def communication(self, val):
        if isinstance(val, str):
            self.__communication = val
        else:
            raise ProjectInfoError("Invalid value for communication")

    @property
    def flatextract(self):
        return self.__flatextract

    @flatextract.setter
    def flatextract(self, val):
        if isinstance(val, str):
            self.__flatextract = val
        else:
            raise ProjectInfoError("Invalid value for flatextract")

    @property
    def flatmap(self):
        return self.__flatmap

    @flatmap.setter
    def flatmap(self, val):
        if isinstance(val, str):
            self.__flatmap = val
        else:
            raise ProjectInfoError("Invalid value for flatmap")

    @property
    def systemextract(self):
        return self.__systemextract

    @systemextract.setter
    def systemextract(self, val):
        if isinstance(val, str):
            self.__systemextract = val
        else:
            raise ProjectInfoError("Invalid value for systemextract")

    @property
    def diagnostics_description_data(self):
        return self.__diagnostics_description_data

    @diagnostics_description_data.setter
    def diagnostics_description_data(self, val):
        if isinstance(val, str):
            self.__diagnostics_description_data = val
        else:
            raise ProjectInfoError("Invalid value for diagnostics_description_data")

    @property
    def initial(self):
        return self.__initial

    @initial.setter
    def initial(self, val):
        if isinstance(val, str):
            self.__initial = val
        else:
            raise ProjectInfoError("Invalid value for initial")

    @property
    def studio_path(self):
        return self.__studio_path

    @studio_path.setter
    def studio_path(self, val):
        if isinstance(val, str):
            self.__studio_path = val
        else:
            raise ProjectInfoError("Invalid value for studio_path")

    @property
    def application_path(self):
        return self.__application_path

    @application_path.setter
    def application_path(self, val):
        if isinstance(val, str):
            self.__application_path = val
        else:
            raise ProjectInfoError("Invalid value for application_path")

    @property
    def internal_behavior_path(self):
        return self.__internal_behavior_path

    @internal_behavior_path.setter
    def internal_behavior_path(self, val):
        if isinstance(val, str):
            self.__internal_behavior_path = val
        else:
            raise ProjectInfoError("Invalid value for internal_behavior_path")

    @property
    def log_path(self):
        return self.__log_path

    @log_path.setter
    def log_path(self, val):
        if isinstance(val, str):
            self.__log_path = val
        else:
            raise ProjectInfoError("Invalid value for log_path")

    @property
    def service_component_path(self):
        return self.__service_component_path

    @service_component_path.setter
    def service_component_path(self, val):
        if isinstance(val, str):
            self.__service_component_path = val
        else:
            raise ProjectInfoError("Invalid value for service_component_path")

    @property
    def compiler_path(self):
        return self.__compiler_path

    @compiler_path.setter
    def compiler_path(self, val):
        if isinstance(val, str):
            self.__compiler_path = val
        else:
            raise ProjectInfoError("Invalid value for compiler_path")

    @property
    def mode(self):
        return self.__mode

    @mode.setter
    def mode(self, val):
        if isinstance(val, str):
            self.__mode = val
        else:
            raise ProjectInfoError("Invalid value for version")

    @property
    def incremental_generation(self):
        return self.__incremental_generation

    @incremental_generation.setter
    def incremental_generation(self, val):
        if isinstance(val, bool):
            self.__incremental_generation = val
        else:
            raise ProjectInfoError("Invalid value for version")

    @property
    def generation_limit(self):
        return self.__generation_limit

    @generation_limit.setter
    def generation_limit(self, val):
        if isinstance(val, str):
            self.__generation_limit = val
        else:
            raise ProjectInfoError("Invalid value for generation limit")


class ProjectInfoError(ValueError):

    def __init__(self, *args: object) -> None:
        super().__init__(*args)
