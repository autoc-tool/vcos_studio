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
import os
import re
import json
import math
import functools
from decimal import Decimal, ROUND_HALF_UP

from func_module.health_monitor.logger import logger
from basic_func_module.base_common.load_plug_in import LoadPlugIn
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.file_handler.file_io_handler import FileIOHandler
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


class ScheduleTableManager:

    @classmethod
    def get_gcd(cls, numbers) -> int:
        return functools.reduce(math.gcd, numbers)

    @classmethod
    def get_lcm(cls, numbers) -> int:
        return functools.reduce(lambda x, y: x * y // math.gcd(x, y), numbers)

    @classmethod
    def get_basename(cls, autosar_ref: str) -> str:
        if not autosar_ref:
            return ""
        return autosar_ref.split("/")[-1]

    @classmethod
    def get_sub_containers_path(cls, container):
        sub_containers = cls.get_container_values(container)
        parent_path = container.get_path()
        return [f"{parent_path}/{get_short_name(sub_container)}" for sub_container in sub_containers]

    @classmethod
    def get_definition_ref(cls, value) -> str:
        return get_definition_ref(value) or ""

    @classmethod
    def get_definition_name(cls, value) -> str:
        return cls.get_basename(cls.get_definition_ref(value))

    @classmethod
    def get_container_values(cls, container_value) -> list:
        containers = getattr(container_value, "CONTAINERS", None) or getattr(container_value, "SUB_CONTAINERS", None)
        return getattr(containers, "ECUC_CONTAINER_VALUE", [])

    @classmethod
    def get_reference_values(cls, container_value) -> list:
        return getattr(getattr(container_value, "REFERENCE_VALUES", None), "ECUC_REFERENCE_VALUE", [])

    @classmethod
    def get_param_values(cls, container_value) -> list:
        param_values = []
        param_values.extend(cls.get_numerical_param_values(container_value))
        param_values.extend(cls.get_textual_param_values(container_value))
        return param_values

    @classmethod
    def get_numerical_param_values(cls, container_value) -> list:
        return getattr(getattr(container_value, "PARAMETER_VALUES", None), "ECUC_NUMERICAL_PARAM_VALUE", [])

    @classmethod
    def get_textual_param_values(cls, container_value) -> list:
        return getattr(getattr(container_value, "PARAMETER_VALUES", None), "ECUC_TEXTUAL_PARAM_VALUE", [])

    @classmethod
    def get_main_duration(cls, has_extended_task, periods, offsets, gcd_period, lcm_period):
        main_duration = lcm_period
        min_period = min(periods)
        min_offset = min(offsets)
        max_offset = max(offsets)
        # 没有扩展任务时，如果周期最小值等于最大公约数且无偏移或所有偏移量相等，
        # 或周期最小值等于最大公约数等于最大偏移且所有偏移只有2个值且最小周期值的偏移等于最小偏移，
        # main的周期才等于最大公约数
        if not has_extended_task and min_period == gcd_period:
            min_periods_index = periods.index(gcd_period)
            if (
                max_offset == 0
                or max_offset == min_offset
                or (max_offset == gcd_period and len(set(offsets)) == 2 and offsets[min_periods_index] == min_offset)
            ):
                main_duration = gcd_period
        return main_duration

    @classmethod
    def get_schedule_step(cls, duration, max_offset, timing_offset_info):
        schedule_step = {}
        for period, offset, task_infos in timing_offset_info:
            if max_offset == 0 and offset > 0:
                # Init调度表的开始时间
                start = offset
            else:
                # 计算任务首次开始执行的时间点, 为下一个整除period的时间点
                start = max_offset + (period + offset - max_offset) % period
            for i in range(start, duration + max_offset, period):
                schedule_step.setdefault(i - max_offset, []).append((period, task_infos))
        schedule_step_sorted = dict(sorted(schedule_step.items(), key=lambda x: x[0]))
        for offset, schedule_step in schedule_step_sorted.items():
            schedule_step_sorted[offset] = sorted(schedule_step, key=lambda x: x[1]["task_position"])
        return schedule_step_sorted

    @classmethod
    def get_timing_ecuc_infos(cls, os_autosar, rte_autosar, asw_autosar, ib_bswmds):
        timing_eucu_cfgs = {}
        instances = cls.get_ecuc_cfg(rte_autosar, "/ActiveEcuC/Rte", "Instance")
        pattern = re.compile(r".*/(.*)_ib_bswmd/")
        for instance in instances:
            def_name = instance["DefName"]
            prefix = "RteBsw" if def_name.startswith("RteBsw") else "Rte"
            for sub_container in instance["SubContainers"]:
                if sub_container["DefName"].endswith(f"{prefix}EventToTaskMapping"):
                    event_ref = sub_container[f"{prefix}EventRef"] or ""
                    timing_event = cls.get_timing_event(asw_autosar, ib_bswmds, pattern, event_ref)
                    if timing_event:
                        timing_info = {}
                        position = int(sub_container.get(f"{prefix}PositionInTask", -1))
                        if position == -1:
                            continue
                        if prefix == "RteBsw":
                            start_ref = get_starts_on_event_ref(timing_event) or ""
                        else:
                            start_ref = get_start_on_event_ref(timing_event) or ""
                        runnable = timing_event.find(start_ref)
                        runnable_name = get_symbol(runnable) or get_short_name(runnable) or ""
                        runnable_period = get_period(timing_event) or "0"
                        runnable_offset = sub_container[f"{prefix}ActivationOffset"] or "0"
                        task_name = cls.get_basename(sub_container[f"{prefix}MappedToTaskRef"])
                        event_name = cls.get_basename(sub_container[f"{prefix}UsedOsEventRef"])
                        timing_info["task_name"] = task_name
                        timing_info["position"] = position
                        timing_info["event_name"] = event_name
                        timing_info["runnable_name"] = runnable_name
                        timing_info["runnable_period"] = cls.convert_seconds_to_milliseconds(runnable_period)
                        timing_info["runnable_offset"] = runnable_offset
                        timing_eucu_cfgs.setdefault(task_name, []).append(timing_info)
        for timing_infos in timing_eucu_cfgs.values():
            timing_infos.sort(key=lambda x: x["position"])
        return timing_eucu_cfgs

    @classmethod
    def get_timing_event(cls, asw_autosar, ib_bswmds, pattern, event_ref):
        event = asw_autosar.find(event_ref)
        if not event:
            match = pattern.search(event_ref)
            if match:
                ib_autosar = ib_bswmds.get(match.group(1))
                if ib_autosar:
                    event = ib_autosar.find(event_ref)
        if event:
            tag = event.get_tag() or ""
            if not tag.endswith("TIMING-EVENT"):
                return None
        return event

    @classmethod
    def get_timing_offset_info(cls, os_autosar, rte_autosar, asw_autosar, ib_bswmds, sch_tbl_ui_cfg, task_offsets=None):
        timing_offset_info = []
        timing_eucu_cfgs = cls.get_timing_ecuc_infos(os_autosar, rte_autosar, asw_autosar, ib_bswmds)
        if task_offsets:
            cls._update_timing_eucu_cfgs(task_offsets, timing_eucu_cfgs)
        os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
        OsManager = getattr(os_process, "OsManager")
        counter_info = OsManager.get_counter_info(os_autosar, sch_tbl_ui_cfg["counter_ref"])
        timing_ecuc_cfgs_in_tick = cls.convert_timing_cfgs_time_to_tick(timing_eucu_cfgs, counter_info)
        timing_offset_info = cls.add_task_offset_to_runnable(timing_ecuc_cfgs_in_tick, sch_tbl_ui_cfg)
        return timing_offset_info

    @classmethod
    def _update_timing_eucu_cfgs(cls, task_offsets, timing_eucu_cfgs):
        for task_offset in task_offsets:
            task_name = task_offset["task_name"]
            for timing_eucu_cfg in timing_eucu_cfgs.get(task_name, []):
                runnable_name = timing_eucu_cfg["runnable_name"]
                runnable_offset = timing_eucu_cfg["runnable_offset"]
                if runnable_name not in task_offset["runnable_offsets"] or isinstance(
                    task_offset["runnable_offsets"], dict
                ):
                    continue
                timing_eucu_cfg["runnable_offset"] = task_offset["runnable_offsets"].get(runnable_name, runnable_offset)

    @classmethod
    def get_ecuc_cfg(cls, ecuc_autosar, container_path="", def_name="", depth=-1):
        ecuc_cfgs = []
        container = ecuc_autosar.find(container_path) if container_path else ecuc_autosar
        container_values = cls.get_container_values(container)
        for container_value in container_values:
            def_ref = cls.get_definition_ref(container_value)
            if not def_ref.endswith(def_name):
                continue
            ecuc_cfg_dict = cls.get_container_cfg(container_value, depth)
            ecuc_cfgs.append(ecuc_cfg_dict)
        return ecuc_cfgs

    @classmethod
    def get_container_cfg(cls, container_value, depth=-1):
        short_name = get_short_name(container_value)
        def_name = cls.get_definition_name(container_value)
        is_automatic = AutosarUtil.is_automatic(container_value)
        schedule_table_dict = {"ShortName": short_name, "DefName": def_name, "IsAutomatic": is_automatic}
        param_values = cls.get_param_values(container_value)
        reference_values = cls.get_reference_values(container_value)
        for value in param_values + reference_values:
            cfg_name = cls.get_definition_name(value)
            if cfg_name in schedule_table_dict:
                schedule_table_dict[cfg_name] += ":" + (get_value_ref(value) or "")
            else:
                schedule_table_dict[cfg_name] = get_value(value) or get_value_ref(value) or ""
        if depth != 0:
            schedule_table_dict["SubContainers"] = cls.get_ecuc_cfg(container_value, depth=depth - 1)
        else:
            schedule_table_dict["SubContainers"] = cls.get_sub_containers_path(container_value)
        return schedule_table_dict

    @classmethod
    def get_sch_tbl_task_name_set(cls, sch_tbl_cfg):
        if not sch_tbl_cfg or not sch_tbl_cfg.get("expiry_point_dict"):
            return set()
        task_name_set = {exp["task_name"] for v in sch_tbl_cfg["expiry_point_dict"].values() for _, exp in v}
        return task_name_set

    @classmethod
    def get_sch_tbl_offset_dict(cls, os_sch_tbl_cfgs, sch_tbl_name):
        offset_dict = {}
        main_sch_tbl_exp_points = os_sch_tbl_cfgs[sch_tbl_name]["expiry_points"]
        for offset, exp_info in main_sch_tbl_exp_points.items():
            for exp in exp_info:
                offset_dict.setdefault(exp["task_name"], []).append(offset)
        return offset_dict

    @classmethod
    def convert_seconds_to_milliseconds(cls, seconds) -> str:
        # 1 秒等于 1000 毫秒
        time_in_milliseconds = Decimal(str(seconds)) * 1000
        return str(time_in_milliseconds.to_integral_value())

    @classmethod
    def convert_milliseconds_to_tick(cls, os_seconds_per_tick, milliseconds) -> int:
        seconds_per_tick = Decimal(str(os_seconds_per_tick))
        assert seconds_per_tick != 0
        miliseconds_per_tick = seconds_per_tick * 1000
        tick_count = int(((Decimal(str(milliseconds)) / miliseconds_per_tick)).quantize(0, ROUND_HALF_UP))
        return tick_count

    @classmethod
    def convert_tick_to_milliseconds(cls, os_seconds_per_tick, tick_count) -> int:
        seconds_per_tick = Decimal(str(os_seconds_per_tick))
        assert seconds_per_tick != 0
        miliseconds_per_tick = seconds_per_tick * 1000
        milliseconds = int(Decimal(str(tick_count)) * miliseconds_per_tick)
        return milliseconds

    @classmethod
    def convert_sch_tbl_tick_to_milliseconds(cls, sch_tbl_cfg, os_seconds_per_tick):
        if not sch_tbl_cfg or not sch_tbl_cfg.get("step_dict"):
            return

        def convert_func(x):
            return ScheduleTableManager.convert_tick_to_milliseconds(os_seconds_per_tick, x)

        for i, schedule_steps in sch_tbl_cfg["step_dict"].items():
            sch_tbl_cfg["step_dict"][i] = {convert_func(x[0]): x[1] for x in schedule_steps}

    @classmethod
    def convert_timing_cfgs_time_to_tick(cls, timing_ecuc_cfgs, counter_info):
        os_seconds_per_tick = counter_info.get("OsSecondsPerTick")
        if not os_seconds_per_tick:
            return timing_ecuc_cfgs
        for _, timing_infos in timing_ecuc_cfgs.items():
            cls.convert_timing_infos_time_to_tick(timing_infos, os_seconds_per_tick)
        return timing_ecuc_cfgs

    @classmethod
    def convert_timing_infos_time_to_tick(cls, timing_infos, os_seconds_per_tick):
        if not os_seconds_per_tick:
            return timing_infos
        for timing_info in timing_infos:
            timing_info["runnable_period_tick"] = cls.convert_milliseconds_to_tick(
                os_seconds_per_tick, timing_info["runnable_period"]
            )
            timing_info["runnable_offset_tick"] = cls.convert_milliseconds_to_tick(
                os_seconds_per_tick, timing_info["runnable_offset"]
            )
        return timing_infos

    @classmethod
    def convert_tick_to_time(cls, step_dict, counter_info):
        os_seconds_per_tick = counter_info.get("OsSecondsPerTick")
        if not os_seconds_per_tick:
            return step_dict
        for _, schedule_steps in step_dict.items():
            for i in range(len(schedule_steps)):
                period, task_infos = schedule_steps[i]
                period_ms = cls.convert_tick_to_milliseconds(os_seconds_per_tick, period)
                task_infos["runnable_period"] = period_ms
                schedule_steps[i] = (period_ms, task_infos)
        return step_dict

    @classmethod
    def add_task_offset_to_runnable(cls, timing_eucu_cfgs, sch_tbl_ui_cfg):
        timing_offset_info = []
        task_offset_table = sch_tbl_ui_cfg["task_offset_table"]
        task_table = list(sch_tbl_ui_cfg["task_offset_table"])
        for task_name, timing_infos in timing_eucu_cfgs.items():
            if task_name not in task_offset_table:
                continue
            task_offset = task_offset_table[task_name]
            for timing_info in timing_infos:
                timing_info["task_position"] = task_table.index(task_name)
                timing_info["runnable_offset_tick"] += task_offset
                timing_offset_info.append(
                    (timing_info["runnable_period_tick"], timing_info["runnable_offset_tick"], timing_info)
                )
        return timing_offset_info

    @classmethod
    def remove_unused_os_sch_tbl(cls, os_autosar, init_sch_tbl_cfg, main_sch_tbl_cfg, appl_container_list):
        os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
        OsManager = getattr(os_process, "OsManager")
        if not init_sch_tbl_cfg.get("expiry_point_dict"):
            init_sch_tbl_name = init_sch_tbl_cfg.get("name", "")
            OsManager.remove_os_sch_tbl(os_autosar, init_sch_tbl_name)
            OsManager.remove_appl_sch_tbl_ref(appl_container_list, init_sch_tbl_name)
        task_names = set()
        task_names.update(cls.get_sch_tbl_task_name_set(init_sch_tbl_cfg))
        task_names.update(cls.get_sch_tbl_task_name_set(main_sch_tbl_cfg))
        if not task_names:
            return
        old_sch_tbl_cfgs = OsManager.get_os_sch_tbl_cfgs(os_autosar)
        for sch_tbl in old_sch_tbl_cfgs.values():
            sch_tbl_name = sch_tbl["name"]
            repeating = sch_tbl["repeating"]
            is_automatic = sch_tbl["is_automatic"]
            is_autostart = sch_tbl["is_autostart"]
            if is_autostart or not repeating or not is_automatic or not sch_tbl_name.startswith("MainScheduleTable_"):
                continue
            task_name = sch_tbl_name.split("MainScheduleTable_")[-1]
            if task_name not in task_names:
                continue
            OsManager.remove_os_sch_tbl(os_autosar, sch_tbl_name)
            OsManager.remove_appl_sch_tbl_ref(appl_container_list, sch_tbl_name)
            init_sch_tbl_name = "InitScheduleTable_" + sch_tbl_name.split("MainScheduleTable_")[-1]
            OsManager.remove_os_sch_tbl(os_autosar, init_sch_tbl_name)
            OsManager.remove_appl_sch_tbl_ref(appl_container_list, init_sch_tbl_name)

    @classmethod
    def reasoning(cls, sch_tbl_ui_cfg, os_autosar, rte_autosar, asw_autosar, ib_bswmds):
        if not sch_tbl_ui_cfg.get("counter_ref"):
            return {}, {}
        timing_offset_info = cls.get_timing_offset_info(os_autosar, rte_autosar, asw_autosar, ib_bswmds, sch_tbl_ui_cfg)
        init_sch_tbl_cfg, main_sch_tbl_cfg = cls._reasoning(sch_tbl_ui_cfg, os_autosar, timing_offset_info)
        return init_sch_tbl_cfg, main_sch_tbl_cfg

    @classmethod
    def reasoning_by_jitter_config(cls, sch_tbl_ui_cfg, os_autosar, rte_autosar, asw_autosar, ib_bswmds, jitter_cfg):
        if not sch_tbl_ui_cfg.get("counter_ref"):
            return {}, {}
        if jitter_cfg.get("sch_tbl_name") != sch_tbl_ui_cfg["name"]:
            logger.error(f"sch_tbl_name {jitter_cfg.get('sch_tbl_name')} not equal {sch_tbl_ui_cfg['name']}")
            return {}, {}
        task_offsets = jitter_cfg.get("task_offsets", {})
        if not task_offsets:
            return {}, {}
        for task_offset in task_offsets:
            offset = task_offset["offset"]
            task_name = task_offset["task_name"]
            if task_name in sch_tbl_ui_cfg["task_offset_table"]:
                sch_tbl_ui_cfg["task_offset_table"][task_name] = offset
        timing_offset_info = cls.get_timing_offset_info(
            os_autosar, rte_autosar, asw_autosar, ib_bswmds, sch_tbl_ui_cfg, task_offsets
        )
        init_sch_tbl_cfg, main_sch_tbl_cfg = cls._reasoning(sch_tbl_ui_cfg, os_autosar, timing_offset_info)
        return init_sch_tbl_cfg, main_sch_tbl_cfg

    @classmethod
    def _reasoning(cls, sch_tbl_ui_cfg, os_autosar, timing_offset_info):
        has_extended_task = cls.has_extended_task(os_autosar, sch_tbl_ui_cfg)
        init_sch_tbl_cfg, main_sch_tbl_cfg = cls.reasoning_sch_tbl_cfg(timing_offset_info, has_extended_task)
        if init_sch_tbl_cfg:
            init_sch_tbl_cfg["counter_ref"] = sch_tbl_ui_cfg["counter_ref"]
        if main_sch_tbl_cfg:
            main_sch_tbl_cfg["counter_ref"] = sch_tbl_ui_cfg["counter_ref"]
        main_sch_tbl_cfg["name"] = sch_tbl_ui_cfg["name"]
        init_sch_tbl_cfg["name"] = "Init" + sch_tbl_ui_cfg["name"]
        return init_sch_tbl_cfg, main_sch_tbl_cfg

    @classmethod
    def reasoning_all(cls, sch_tbl_ui_cfg_list, os_autosar, rte_autosar, asw_autosar, ib_bswmds):
        sch_tbl_cfgs = []
        for sch_tbl_ui_cfg in sch_tbl_ui_cfg_list:
            sch_tbl_name = sch_tbl_ui_cfg["name"]
            sch_tbl_ref = f"/ActiveEcuC/Os/{sch_tbl_name}"
            if not os_autosar.find(sch_tbl_ref):
                continue
            init_sch_tbl_cfg, main_sch_tbl_cfg = cls.reasoning(
                sch_tbl_ui_cfg, os_autosar, rte_autosar, asw_autosar, ib_bswmds
            )
            sch_tbl_cfgs.append({"init": init_sch_tbl_cfg, "main": main_sch_tbl_cfg})
        return sch_tbl_cfgs

    @classmethod
    def reasoning_all_by_jitter_config(
        cls, sch_tbl_ui_cfg_list, os_autosar, rte_autosar, asw_autosar, ib_bswmds, jitter_configs
    ):
        sch_tbl_cfgs = []
        for sch_tbl_ui_cfg in sch_tbl_ui_cfg_list:
            sch_tbl_name = sch_tbl_ui_cfg["name"]
            sch_tbl_ref = f"/ActiveEcuC/Os/{sch_tbl_name}"
            if not os_autosar.find(sch_tbl_ref):
                continue
            jitter_config = jitter_configs.get(sch_tbl_name)
            if not jitter_config:
                continue
            init_sch_tbl_cfg, main_sch_tbl_cfg = cls.reasoning_by_jitter_config(
                sch_tbl_ui_cfg, os_autosar, rte_autosar, asw_autosar, ib_bswmds, jitter_config
            )
            sch_tbl_cfgs.append({"init": init_sch_tbl_cfg, "main": main_sch_tbl_cfg})
        return sch_tbl_cfgs

    @classmethod
    def reasoning_sch_tbl_cfg(cls, timing_offset_info, has_extended_task=False):
        if not timing_offset_info:
            return {}, {}
        periods, offsets, _ = zip(*timing_offset_info)
        min_period = min(periods)
        min_offset = min(offsets)
        max_offset = max(offsets)
        if min_period == 0 or min_offset < 0:
            return {}, {}
        init_sch_tbl_cfg = {"name": "", "repeating": False, "counter_ref": "", "code_gen": True}
        main_sch_tbl_cfg = {"name": "", "repeating": True, "counter_ref": "", "code_gen": True}
        gcd_period = cls.get_gcd(periods)
        lcm_period = cls.get_lcm(periods)
        main_duration = cls.get_main_duration(has_extended_task, periods, offsets, gcd_period, lcm_period)
        init_duration = max_offset
        init_step_dict = {}
        if init_duration > 0:
            # 如果所有offset都相同，则init_duration需要叠加main_duration，且与main共享step调度关系
            if max_offset == min_offset:
                init_duration += main_duration
                init_sch_tbl_cfg["code_gen"] = False
            init_step_dict = cls.get_schedule_step(init_duration, 0, timing_offset_info)
        if init_step_dict:
            init_sch_tbl_cfg.update(
                {
                    "duration": init_duration,
                    "step_dict": init_step_dict,
                    "expiry_point_dict": init_step_dict.copy(),
                }
            )
        else:
            init_sch_tbl_cfg.clear()
        main_step_dict = cls.get_schedule_step(lcm_period, max_offset, timing_offset_info)
        if main_step_dict:
            main_sch_tbl_cfg.update(
                {
                    "duration": main_duration,
                    "step_dict": main_step_dict,
                    "expiry_point_dict": {i: periods for i, periods in main_step_dict.items() if i < main_duration},
                }
            )
        return init_sch_tbl_cfg, main_sch_tbl_cfg

    @classmethod
    def re_reasoning_all(cls, os_autosar, rte_autosar, asw_autosar, ib_bswmds):
        timing_eucu_info = cls.get_timing_ecuc_infos(os_autosar, rte_autosar, asw_autosar, ib_bswmds)
        os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
        OsManager = getattr(os_process, "OsManager")
        os_sch_tbl_cfgs = OsManager.get_os_sch_tbl_cfgs(os_autosar)
        sch_tbl_ui_cfgs = cls.re_reasoning_sch_tbl_ui_cfgs(timing_eucu_info, os_sch_tbl_cfgs)
        return sch_tbl_ui_cfgs

    @classmethod
    def re_reasoning_sch_tbl_ui_cfgs(cls, timing_ecuc_info, os_sch_tbl_cfgs):
        sch_tbl_ui_cfgs = {}
        for sch_tbl in os_sch_tbl_cfgs.values():
            sch_tbl_name = sch_tbl["name"]
            repeating = sch_tbl["repeating"]
            is_automatic = sch_tbl["is_automatic"]
            is_autostart = sch_tbl["is_autostart"]
            if is_automatic or is_autostart or not repeating:
                continue
            os_seconds_per_tick = sch_tbl["counter_info"].get("OsSecondsPerTick", 0)
            if not os_seconds_per_tick:
                continue
            task_offset_dict = {}
            # InitScheduleTableName 等于“Init” + MainScheduleTableName
            init_sch_tbl_name = "Init" + sch_tbl_name
            if init_sch_tbl_name in os_sch_tbl_cfgs:
                init_offset_dict = cls.get_sch_tbl_offset_dict(os_sch_tbl_cfgs, init_sch_tbl_name)
                main_offset_dict = cls.get_sch_tbl_offset_dict(os_sch_tbl_cfgs, sch_tbl_name)
                for task_name, task_offsets in init_offset_dict.items():
                    timing_infos = timing_ecuc_info.get(task_name, [])
                    timing_infos_with_tick = cls.convert_timing_infos_time_to_tick(timing_infos, os_seconds_per_tick)
                    min_task_offset = min(task_offsets)
                    min_runnable_offset = min(
                        timing_infos_with_tick, key=lambda x: x["runnable_offset_tick"], default={}
                    ).get("runnable_offset_tick", 0)
                    task_offset = min_task_offset - min_runnable_offset
                    task_offset_dict.setdefault(task_offset, []).append(task_name)
                init_duration = os_sch_tbl_cfgs[init_sch_tbl_name]["duration"]
                main_duration = sch_tbl["duration"]
                for task_name, task_offset in main_offset_dict.items():
                    if task_name in init_offset_dict:
                        continue
                    timing_infos = timing_ecuc_info.get(task_name, [])
                    timing_infos_with_tick = cls.convert_timing_infos_time_to_tick(timing_infos, os_seconds_per_tick)
                    min_runnable_offset = min(
                        timing_infos_with_tick, key=lambda x: x["runnable_offset_tick"], default={}
                    ).get("runnable_offset_tick", 0)
                    if min_runnable_offset < init_duration:
                        task_offset = init_duration - min_runnable_offset
                    else:
                        # 对应所有offset都相同，init_duration叠加main_duration的情况
                        task_offset = init_duration - main_duration - min_runnable_offset
                    task_offset_dict.setdefault(task_offset, []).append(task_name)
            else:
                task_list = list({exp_cfg["task_name"]: 0 for v in sch_tbl["expiry_points"].values() for exp_cfg in v})
                if task_list:
                    task_offset_dict[0] = task_list
            sch_tbl_ui_cfgs[sch_tbl_name] = {
                "name": sch_tbl_name,
                "counter_ref": sch_tbl["counter_ref"],
                "task_offset_dict": task_offset_dict,
            }
        return sch_tbl_ui_cfgs

    @classmethod
    def generate(cls, os_autosar, mod_autosar, init_sch_tbl_cfg, main_sch_tbl_cfg):
        os_container = os_autosar.find("/ActiveEcuC/Os")
        appl_container_list = [
            appl
            for appl in cls.get_container_values(os_container)
            if cls.get_definition_ref(appl).endswith("OsApplication")
        ]
        cls.remove_unused_os_sch_tbl(os_autosar, init_sch_tbl_cfg, main_sch_tbl_cfg, appl_container_list)
        os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
        OsManager = getattr(os_process, "OsManager")
        appl_list = OsManager.get_os_sch_tbl_appl_list(os_autosar)
        ret = OsManager.update_os_schedule_table(os_autosar, mod_autosar, main_sch_tbl_cfg, appl_list)
        if ret:
            OsManager.update_os_schedule_table(os_autosar, mod_autosar, init_sch_tbl_cfg, appl_list)
            OsManager.update_appl_init_sch_tbl_ref(mod_autosar, appl_container_list, init_sch_tbl_cfg, main_sch_tbl_cfg)

    @classmethod
    def generate_all(cls, os_autosar, mod_autosar, sch_tbl_cfgs):
        for sch_tbl_cfg in sch_tbl_cfgs:
            cls.generate(os_autosar, mod_autosar, sch_tbl_cfg["init"], sch_tbl_cfg["main"])

    @classmethod
    def has_extended_task(cls, os_autosar, sch_tbl_ui_cfg):
        for task_name in sch_tbl_ui_cfg["task_offset_table"]:
            if cls.is_extended_task(os_autosar, f"/ActiveEcuC/Os/{task_name}"):
                return True
        return False

    @classmethod
    def is_extended_task(cls, os_autosar, task_ref):
        task = os_autosar.find(task_ref)
        for value in cls.get_textual_param_values(task):
            def_ref = cls.get_definition_ref(value)
            if def_ref.endswith("OsTaskType") and get_value(value) == "EXTENDED":
                return True
        return False

    @classmethod
    def convert_os_sch_tbl_cfg_to_ui(cls, os_sch_tbl_cfgs):
        sch_tbl_ui_cfg_list = []
        for sch_tbl_cfg in os_sch_tbl_cfgs.values():
            sch_tbl_ui_cfg = {}
            sch_tbl_ui_cfg["name"] = sch_tbl_cfg["name"]
            sch_tbl_ui_cfg["counter_ref"] = sch_tbl_cfg["counter_ref"]
            task_offset_dict = sch_tbl_cfg.get("task_offset_dict", {})
            task_offset_table = {
                task_name: offset for offset, task_list in task_offset_dict.items() for task_name in task_list
            }
            sch_tbl_ui_cfg["task_offset_table"] = task_offset_table
            sch_tbl_ui_cfg_list.append(sch_tbl_ui_cfg)
        return sch_tbl_ui_cfg_list

    @classmethod
    def load_sch_tbl_ui_cfg(cls, base_cfg_path):
        ui_cfg = FileIOHandler.load_json_file(os.path.join(base_cfg_path, "system/schedule_table.json"))
        return ui_cfg or {}

    @classmethod
    def save_sch_tbl_ui_cfg(cls, base_cfg_path, ui_cfg):
        with open(os.path.join(base_cfg_path, "system/schedule_table.json"), "w", encoding="utf-8") as f:
            json.dump(ui_cfg, f, indent=4)
