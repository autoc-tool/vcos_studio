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
更新bsw模块的ib_bswm对象
"""
from basic_func_module.base_common.load_plug_in import LoadPlugIn
from func_module.health_monitor.logger import logger
from func_module.module_management.module_dependency_resolver.module_dependency_resolver import (
    sort_module_list_based_on_dependency,
)


class IbBswmdProcess:
    module_pkgs = {}

    @classmethod
    def update_all_ib_bswmd(
        cls, internal_behavior_dict, ecuc_autosar_dict, asw_autosar_dict, system_autosar_dict, other_input_info
    ):
        """
        bsw模块ib_bswmd.arxml更新接口
        """
        sorted_module_list = sort_module_list_based_on_dependency(
            list(other_input_info["sys_info_class"].enable_modules)
        )
        for module_name in sorted_module_list:
            module_cfg_dict = ib_file_support = other_input_info["sys_target_dict"]["module_cfg"].get(module_name, None)
            if module_cfg_dict is None:
                logger.info(f"{module_name} not found in sys_target_dict!")
                continue
            ib_file_support = module_cfg_dict.get("internal_behavior", {}).get("support", None)
            ib_file_dynamic = module_cfg_dict.get("internal_behavior", {}).get("dynamic", None)
            if ib_file_support is None or ib_file_dynamic is None:
                logger.error(f"{module_name} internal behavior system config not found in sys_target_dict!")
                continue
            if ib_file_support is not True or ib_file_dynamic is not True:
                continue

            try:
                if module_name not in other_input_info["sys_info_class"].plug_in_path.keys():
                    logger.error(f"Module {module_name} not found in sys_info_class.plug_in_path!")
                    continue
                package_path = f"config_plug_in.ib_bswmd_process.{module_name.lower()}_ib_bswmd_process"
                module_pkg = LoadPlugIn.load_module(module_name, package_path)
                if module_pkg is None:
                    logger.debug(f"Module {module_name} not update internal behavior mainfunction or exclusive areas")
                    continue
                cls.module_pkgs[module_name] = module_pkg
                if module_name not in internal_behavior_dict.keys():
                    logger.error(f"Module {module_name} internal behavior not found!")
                    continue
                cls.module_pkgs[module_name].update_ib_bswmd(
                    internal_behavior_dict, ecuc_autosar_dict, asw_autosar_dict, system_autosar_dict, other_input_info
                )
            except Exception as e:
                logger.ui_error(
                    f"Module {module_name} update internal behavior mainfunction or exclusive areas error! {e}"
                )
