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
from basic_func_module.base_common.load_plug_in import LoadPlugIn
from cmd_adaptor.data_management import get_autosar_bsw_class
from cmd_adaptor.data_management import get_autosar_bswmd_class
from func_module.health_monitor.perf_record import log_function_stats


class OsCmdFunc:

    @classmethod
    @log_function_stats(["RTE", "命令行添加spinlock"])
    def add_spinlock(cls, spinlock_info: dict) -> bool:
        if not spinlock_info:
            return False
        spinlock_id = spinlock_info.get("spinlock_id", None)
        spinlock_method = spinlock_info.get("spinlock_method", None)
        app_name_list = spinlock_info.get("app_name_list", None)

        if not spinlock_id or not spinlock_method or not app_name_list:
            return False
        if spinlock_method not in ("LOCK_ALL_INTERRUPTS", "LOCK_CAT2_INTERRUPTS", "LOCK_NOTHING"):
            return False
        if len(set(app_name_list)) < 2:
            return False

        autosar_bsw_class = get_autosar_bsw_class()
        autosar_mod_class = get_autosar_bswmd_class()
        os_autosar = autosar_bsw_class.get("Os", None)
        os_mod_autosar = autosar_mod_class.get("Os", None)
        if not os_autosar or not os_mod_autosar:
            return False

        os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
        OsManager = getattr(os_process, "OsManager")
        OsManager.remove_spinlock_info(os_autosar, spinlock_id)
        OsManager.add_spinlock_info(os_autosar, os_mod_autosar, spinlock_id, app_name_list + [spinlock_method], False)
        return True

    @classmethod
    @log_function_stats(["RTE", "命令行移除spinlock"])
    def remove_spinlock(cls, spinlock_id):
        autosar_bsw_class = get_autosar_bsw_class()
        os_autosar = autosar_bsw_class.get("Os", None)
        if not os_autosar:
            return False

        os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
        OsManager = getattr(os_process, "OsManager")
        OsManager.remove_spinlock_info(os_autosar, spinlock_id)

        return True
