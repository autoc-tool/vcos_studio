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
import re
from decimal import Decimal
from basic_func_module.autosar_utils.utils import (
    get_short_name,
    get_definition_ref,
    get_value_ref,
    get_value,
    get_start_on_event_ref,
    get_starts_on_event_ref,
    get_period,
    get_symbol,
)
from func_module.mapping.schedule_table_mapping import ScheduleTableManager


class TaskMappingInfo:
    """本class用于获取task mapping相关的信息"""

    @classmethod
    def convert_seconds_to_microseconds(cls, seconds) -> str:
        time_in_microseconds = Decimal(str(seconds)) * 1000000
        return str(time_in_microseconds.to_integral_value())

    @classmethod
    def convert_tick_to_microseconds(cls, task_offset_table, counter_info):
        os_seconds_per_tick = counter_info.get("OsSecondsPerTick")
        for task in task_offset_table.keys():
            task_offset_table[task] *= float(os_seconds_per_tick) * 1e6
        return task_offset_table

    @classmethod
    def convert_tick_by_alarm(cls, runnable_info, os_autosar):
        alarm_counter_dict = {}
        for task_name, runnable_list in runnable_info.items():
            for runnable in runnable_list:
                alarm_ref = runnable["alarm_ref"]
                if alarm_ref not in alarm_counter_dict.keys():
                    counter_obj = None
                    alarm_obj = os_autosar.find(alarm_ref)
                    for _ in ScheduleTableManager.get_reference_values(alarm_obj):
                        def_ref = get_definition_ref(_)
                        if def_ref.endswith("OsAlarmCounterRef"):
                            counter_obj = os_autosar.find(get_value_ref(_))
                            break
                    if counter_obj is None:
                        continue
                    for _ in ScheduleTableManager.get_numerical_param_values(counter_obj):
                        def_ref = get_definition_ref(_)
                        if def_ref.endswith("OsSecondsPerTick"):
                            alarm_counter_dict[alarm_ref] = get_value(_)
                            break
                runnable["runnable_period"] = ScheduleTableManager.convert_milliseconds_to_tick(
                    alarm_counter_dict[alarm_ref], runnable["runnable_period"]
                )
                runnable["runnable_offset"] = ScheduleTableManager.convert_milliseconds_to_tick(
                    alarm_counter_dict[alarm_ref], runnable["runnable_offset"]
                )
        return runnable_info

    @classmethod
    def get_event(cls, asw_autosar, ib_bswmds, pattern, event_ref):
        """获取<EVENTS>下的特定EVENT"""
        event = asw_autosar.find(event_ref)
        if not event:
            match = pattern.search(event_ref)
            if match:
                ib_autosar = ib_bswmds.get(match.group(1))
                if ib_autosar:
                    event = ib_autosar.find(event_ref)

        return event

    @classmethod
    def get_runnable_by_trigger_event(cls, rte_autosar, asw_autosar, ib_bswmds):
        """获取trigger event及对应runnable信息"""
        instances = ScheduleTableManager.get_ecuc_cfg(rte_autosar, "/ActiveEcuC/Rte", "Instance")

        ecuc_cfgs = {"non_timing": {}, "timing": {}}
        pattern = re.compile(r".*/(.*)_ib_bswmd/")
        for instance in instances:
            def_name = instance["DefName"]
            prefix = "RteBsw" if def_name.startswith("RteBsw") else "Rte"
            for sub_container in instance["SubContainers"]:
                if sub_container["DefName"].endswith(f"{prefix}EventToTaskMapping"):
                    event_ref = sub_container[f"{prefix}EventRef"] or ""
                    event = cls.get_event(asw_autosar, ib_bswmds, pattern, event_ref)
                    if not event:
                        continue
                    event_tag = event.get_tag() or ""
                    info = {}
                    position = int(sub_container.get(f"{prefix}PositionInTask", -1))
                    if position == -1:
                        continue
                    if prefix == "RteBsw":
                        start_ref = get_starts_on_event_ref(event) or ""
                    else:
                        start_ref = get_start_on_event_ref(event) or ""
                    runnable = event.find(start_ref)
                    runnable_name = get_short_name(runnable) or get_symbol(runnable) or ""
                    task_name = ScheduleTableManager.get_basename(sub_container[f"{prefix}MappedToTaskRef"])
                    event_name = ScheduleTableManager.get_basename(sub_container[f"{prefix}UsedOsEventRef"])
                    alarm_ref = sub_container[f"{prefix}UsedOsAlarmRef"] or ""
                    info["task_name"] = task_name
                    info["position"] = position
                    info["event_name"] = event_name
                    info["runnable_name"] = runnable_name
                    info["alarm_ref"] = alarm_ref

                    if event_tag.endswith("TIMING-EVENT"):
                        runnable_period = get_period(event) or 0
                        runnable_offset = float(sub_container[f"{prefix}ActivationOffset"] or 0.0)
                        info["runnable_period"] = cls.convert_seconds_to_microseconds(runnable_period)
                        info["runnable_offset"] = runnable_offset
                        if info not in ecuc_cfgs["timing"].setdefault(task_name, []):
                            ecuc_cfgs["timing"][task_name].append(info)
                    else:
                        if info not in ecuc_cfgs["non_timing"].setdefault(task_name, []):
                            ecuc_cfgs["non_timing"][task_name].append(info)

        for item in ecuc_cfgs.values():
            for cfg in item.values():
                cfg.sort(key=lambda x: x["position"])
        return ecuc_cfgs

    @classmethod
    def add_task_offset_to_runnable(cls, sch_runnable_in_ms, task_offset_table):
        for task_name, runnable_infos in sch_runnable_in_ms.items():
            task_offset = task_offset_table[task_name]
            for runnable_info in runnable_infos:
                runnable_info["runnable_offset"] += task_offset
        return sch_runnable_in_ms


class RunnableInfo:

    def __init__(
        self, runnable_name="", owner="", mapped_task="", position="", trigger_category="", trigger_condition=""
    ) -> None:
        self.trigger_entity = runnable_name
        self.owner = owner
        self.mapped_task = mapped_task
        self.position = position
        self.trigger_category = trigger_category
        self.trigger_condition = trigger_condition
