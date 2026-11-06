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
from cmd_adaptor.data_management import get_autosar_asw_class
from cmd_adaptor.data_management import get_autosar_bsw_class
from cmd_adaptor.data_management import get_autosar_ib_class
from cmd_adaptor.data_management import get_autosar_bswmd_class
from cmd_adaptor.data_management import get_sys_info_class
from cmd_adaptor.cmd_interaction.cmd_logger import logger
from func_module.mapping.schedule_table_mapping import ScheduleTableManager
from func_module.health_monitor.perf_record import log_function_stats


class ScheduleTableCmdFunc:

    @classmethod
    @log_function_stats(["二级菜单", "调度表", "命令行生成调度表"])
    def generate_schedule_table_cfg(cls):
        asw_autosar = get_autosar_asw_class()
        bsw_autosar_dict = get_autosar_bsw_class()
        bswmd_autosar_dict = get_autosar_bswmd_class()
        if "Os" not in bsw_autosar_dict:
            logger.error("OS not found in BSW")
            return False
        if "Rte" not in bsw_autosar_dict:
            logger.error("RTE not found in ASW")
            return False
        if "Os" not in bswmd_autosar_dict:
            logger.error("OS not found in BSWMD")
            return False
        os_mod_autosar = bswmd_autosar_dict["Os"]
        os_autosar = bsw_autosar_dict["Os"]
        rte_autosar = bsw_autosar_dict["Rte"]
        ib_autosar_dict = get_autosar_ib_class()
        os_sch_tbl_cfgs = ScheduleTableManager.re_reasoning_all(os_autosar, rte_autosar, asw_autosar, ib_autosar_dict)
        schedule_table_ui_cache = ScheduleTableManager.load_sch_tbl_ui_cfg(get_sys_info_class().config_base_path)
        sch_tbl_ui_cfg_list = []
        if not schedule_table_ui_cache:
            sch_tbl_ui_cfg_list = ScheduleTableManager.convert_os_sch_tbl_cfg_to_ui(os_sch_tbl_cfgs)
        else:
            for sch_tbl_cfg_name in set(schedule_table_ui_cache):
                if sch_tbl_cfg_name not in os_sch_tbl_cfgs:
                    schedule_table_ui_cache.pop(sch_tbl_cfg_name)
            for sch_tbl_cfg_name, table_offset_list in schedule_table_ui_cache.items():
                task_offset_table = {
                    task_name: row[0]
                    for row in table_offset_list
                    for task_name in row[1:]
                    if isinstance(row[0], int)
                    if task_name != ""
                }
                counter_ref = os_sch_tbl_cfgs.get(sch_tbl_cfg_name, {}).get("counter_ref")
                if counter_ref is None:
                    logger.error(f"{sch_tbl_cfg_name} OsScheduleTableCounterRef is None")
                    continue
                sch_tbl_ui_cfg = {
                    "name": sch_tbl_cfg_name,
                    "task_offset_table": task_offset_table,
                    "counter_ref": counter_ref,
                }
                sch_tbl_ui_cfg_list.append(sch_tbl_ui_cfg)
        sch_tbl_cfgs = ScheduleTableManager.reasoning_all(
            sch_tbl_ui_cfg_list, os_autosar, rte_autosar, asw_autosar, ib_autosar_dict
        )
        ScheduleTableManager.generate_all(os_autosar, os_mod_autosar, sch_tbl_cfgs)
        return True
