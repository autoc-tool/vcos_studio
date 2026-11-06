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
from collections import defaultdict
from typing import List, Dict
from lxml import etree
from basic_func_module.autosar_utils.utils import (
    get_definition_ref,
    get_value_ref,
    get_value,
    get_short_name,
    get_period,
)
from func_module.mapping.schedule_table_mapping import ScheduleTableManager as STM
from func_module.module_management.bsw_editor.bsw_editor import BswEditor
from func_module.health_monitor.logger import logger

TICK_PER_SECOND = 1000000
SECONDS_PER_TICK = 1 / TICK_PER_SECOND
CAPACITY = "cet_max(ms)"


def add_sub_element(parent, tag, text="", **kwargs):
    sub_ele = etree.SubElement(parent, tag, **kwargs)
    if text:
        sub_ele.text = text
    return sub_ele


class CheddarCore:

    count = 0

    def __init__(self, name) -> None:
        self.name = name
        self.id = f"id_{self.count}"
        CheddarCore.count += 1
        self.scheduler_type = "POSIX_1003_HIGHEST_PRIORITY_FIRST_PROTOCOL"
        self.quantum = 0
        self.preemptive_type = "PREEMPTIVE"
        self.automaton_name = ""
        self.capacity = 0
        self.period = 0
        self.priority = 0
        self.user_defined_schedular_file_name = ""
        self.start_time = 0
        self.speed = 1
        self.l1_cache_system_name = ""

    def to_xml(self):
        core_unit = etree.Element("core_unit", id=self.id)
        add_sub_element(core_unit, "object_type", "CORE_OBJECT_TYPE")
        add_sub_element(core_unit, "name", self.name)

        sched = add_sub_element(core_unit, "scheduling")
        sched_param = add_sub_element(sched, "scheduling_parameters")
        add_sub_element(sched_param, "scheduler_type", self.scheduler_type)
        add_sub_element(sched_param, "quantum", str(self.quantum))
        add_sub_element(sched_param, "preemptive_type", self.preemptive_type)
        add_sub_element(sched_param, "capacity", str(self.capacity))
        add_sub_element(sched_param, "period", str(self.period))
        add_sub_element(sched_param, "priority", str(self.priority))
        add_sub_element(sched_param, "start_time", str(self.start_time))

        add_sub_element(core_unit, "speed", str(self.speed))
        add_sub_element(core_unit, "worstcase_perequest_intrabank_memory_interference", "0")
        add_sub_element(core_unit, "worstcase_perequest_interbank_memory_interference", "0")
        add_sub_element(core_unit, "isa", "I386")

        return core_unit


class CheddarProcessor:

    count = 0

    def __init__(self, name, type) -> None:
        self.name = name
        self.id = f"id_{self.count}"
        CheddarProcessor.count += 1
        self.network = ""
        self.type = type
        if self.type == "multi_cores_processor":
            self.processor_type = "IDENTICAL_MULTICORES_TYPE"
        elif self.type == "mono_core_processor":
            self.processor_type = "MONOCORE_TYPE"
        else:
            raise NotImplementedError(f"Unsupported processor type {type}")

        self.migration_type = "NO_MIGRATION_TYPE"
        self.core_l: List[CheddarCore] = []

    def add_core(self, core: CheddarCore):
        self.core_l.append(core)

    def to_xml(self):
        processor_item = etree.Element(self.type, id=self.id)
        add_sub_element(processor_item, "object_type", "PROCESSOR_OBJECT_TYPE")
        add_sub_element(processor_item, "name", self.name)
        add_sub_element(processor_item, "processor_type", self.processor_type)
        add_sub_element(processor_item, "migration_type", self.migration_type)

        # Multi core processor
        if self.type == "multi_cores_processor":
            cores = add_sub_element(processor_item, "cores")
            for core in self.core_l:
                add_sub_element(cores, "core_unit", ref=core.id)
        # Mono core processor
        elif self.type == "mono_core_processor":
            add_sub_element(processor_item, "core", ref=self.core_l[0].id)

        return processor_item


class CheddarAddressSpace:

    count = 0

    def __init__(self, name) -> None:
        self.name = name
        self.id = f"id_{self.count}"
        CheddarAddressSpace.count += 1
        self.processor: CheddarProcessor = None
        self.text_memory_size = 0
        self.stack_memory_size = 0
        self.data_memory_size = 0
        self.heap_memory_size = 0
        self.scheduler_type = "NO_SCHEDULING_PROTOCOL"
        self.quantum = 0
        self.preemptive_type = "PREEMPTIVE"
        self.automaton_name = ""
        self.capacity = 0
        self.period = 0
        self.priority = 0
        self.user_defined_schedular_file_name = ""
        self.start_time = 0

    def set_processor(self, processor: CheddarProcessor):
        self.processor = processor

    def to_xml(self):
        addr_spc_item = etree.Element("address_space", id=self.id)
        add_sub_element(addr_spc_item, "object_type", "ADDRESS_SPACE_OBJECT_TYPE")
        add_sub_element(addr_spc_item, "name", self.name)
        add_sub_element(addr_spc_item, "cpu_name", self.processor.name)
        add_sub_element(addr_spc_item, "text_memory_size", str(self.text_memory_size))
        add_sub_element(addr_spc_item, "stack_memory_size", str(self.stack_memory_size))
        add_sub_element(addr_spc_item, "data_memory_size", str(self.data_memory_size))
        add_sub_element(addr_spc_item, "heap_memory_size", str(self.heap_memory_size))

        sched = add_sub_element(addr_spc_item, "scheduling")
        sched_param = add_sub_element(sched, "scheduling_parameters")
        add_sub_element(sched_param, "scheduler_type", self.scheduler_type)
        add_sub_element(sched_param, "quantum", str(self.quantum))
        add_sub_element(sched_param, "preemptive_type", self.preemptive_type)
        add_sub_element(sched_param, "capacity", str(self.capacity))
        add_sub_element(sched_param, "period", str(self.period))
        add_sub_element(sched_param, "priority", str(self.priority))
        add_sub_element(sched_param, "start_time", str(self.start_time))

        add_sub_element(addr_spc_item, "mils_confidentiality_level", "TOP_SECRET")
        add_sub_element(addr_spc_item, "mils_integrity_level", "HIGH")
        add_sub_element(addr_spc_item, "mils_component", "SLS")
        add_sub_element(addr_spc_item, "mils_partition", "DEVICE")
        add_sub_element(addr_spc_item, "mils_compliant", "TRUE")

        return addr_spc_item


class CheddarTask:
    count = 0

    def __init__(self, name) -> None:
        self.name = name
        self.id = f"id_{self.count}"
        CheddarTask.count += 1
        self.task_type = ""
        self.processor: CheddarProcessor = None
        self.core: CheddarCore = None
        self.address_space: CheddarAddressSpace = None
        self.capacity = 0
        self.deadline = 0
        self.start_time = 0
        self.priority = 0
        self.blocking_time = 0
        self.policy = "SCHED_FIFO"
        self.text_memory_size = 0
        self.stack_memory_size = 0
        self.criticality = 0
        self.jitter = 0
        self.period = 0
        self.activation_rule = ""
        self.predictable = False

    def set_task_type(self, task_type):
        self.task_type = task_type

    def set_processor(self, processor: CheddarProcessor):
        self.processor = processor

    def set_core(self, core: CheddarCore):
        self.core = core

    def set_address_space(self, address_space: CheddarAddressSpace):
        self.address_space = address_space

    def set_capacity(self, capacity):
        self.capacity = capacity

    def set_deadline(self, deadline):
        self.deadline = deadline

    def set_start_time(self, start_time):
        self.start_time = start_time

    def set_priority(self, priority):
        self.priority = priority

    def set_period(self, period):
        self.period = period

    def to_xml(self):
        if self.task_type == "PERIODIC_TYPE":
            task_item = etree.Element("periodic_task", id=self.id)
        elif self.task_type == "APERIODIC_TYPE":
            task_item = etree.Element("aperiodic_task", id=self.id)
        else:
            raise NotImplementedError(f"Unsupported task type {self.task_type}")

        add_sub_element(task_item, "object_type", "TASK_OBJECT_TYPE")
        add_sub_element(task_item, "name", self.name)
        add_sub_element(task_item, "task_type", self.task_type)
        add_sub_element(task_item, "cpu_name", self.processor.name)
        add_sub_element(task_item, "address_space_name", self.address_space.name)
        if self.processor.type != "mono_core_processor":
            add_sub_element(task_item, "core_name", self.core.name)
        add_sub_element(task_item, "capacity", str(self.capacity))
        add_sub_element(task_item, "capacity_low", "0")
        add_sub_element(task_item, "energy_consumption", "0")
        add_sub_element(task_item, "deadline", str(self.deadline))
        add_sub_element(task_item, "start_time", str(self.start_time))
        add_sub_element(task_item, "priority", str(self.priority))
        add_sub_element(task_item, "blocking_time", str(self.blocking_time))
        add_sub_element(task_item, "policy", self.policy)
        add_sub_element(task_item, "text_memory_size", str(self.text_memory_size))
        add_sub_element(task_item, "text_memory_start_address", "0")
        add_sub_element(task_item, "stack_memory_size", str(self.stack_memory_size))
        add_sub_element(task_item, "criticality", str(self.criticality))
        add_sub_element(task_item, "context_switch_overhead", "0")
        add_sub_element(task_item, "cfg_relocatable", "FALSE")
        add_sub_element(task_item, "mils_confidentiality_level", "TOP_SECRET")
        add_sub_element(task_item, "mils_integrity_level", "HIGH")
        add_sub_element(task_item, "mils_component", "SLS")
        add_sub_element(task_item, "mils_task", "APPLICATION")
        add_sub_element(task_item, "mils_compliant", "TRUE")
        add_sub_element(task_item, "access_memory_number", "0")
        add_sub_element(task_item, "maximum_number_of_memory_request_per_job", "0")
        if self.task_type == "PERIODIC_TYPE":
            add_sub_element(task_item, "period", str(self.period))
            add_sub_element(task_item, "jitter", "0")
            add_sub_element(task_item, "every", "0")
            add_sub_element(task_item, "completion_time", "0")

        return task_item


class CheddarGenerator:

    def __init__(self) -> None:
        self.core_l: List[CheddarCore] = []
        self.processor_l: List[CheddarProcessor] = []
        self.address_spaces_l: List[CheddarAddressSpace] = []
        self.task_l: List[CheddarTask] = []

    def clear_id_count(self):
        """
        Clear id count of Core/Processor/AddressSpace/Task, to ensure id of them start from 0
        """
        CheddarCore.count = 0
        CheddarProcessor.count = 0
        CheddarAddressSpace.count = 0
        CheddarTask.count = 0

    def infer_task_period_from_mapping(self, autosar_bsw_class, autosar_ib_class, autosar_asw_class, task_list):
        """
        Infer period from task mapping according to
            1. If perioidic runnables mapping to task, the minimum runnable period is the task period
            1. If no perioidic runnables mapping to task, the task is not periodic
        """
        rte_ecuc = autosar_bsw_class["Rte"]

        rte_cfg = rte_ecuc.find("/ActiveEcuC/Rte")

        # Gather all period of periodic runnable
        task_period_mapping = defaultdict(set)
        for con in getattr(getattr(rte_cfg, "CONTAINERS", None), "ECUC_CONTAINER_VALUE", []):
            if get_definition_ref(con).split("/")[-1] == "RteBswModuleInstance":
                self.period_from_bsw(autosar_ib_class, task_period_mapping, con)
            elif get_definition_ref(con).split("/")[-1] == "RteSwComponentInstance":
                self.period_from_asw(autosar_asw_class, task_period_mapping, con)

        task_period = {}
        for task in task_list:
            if task in task_period_mapping:
                min_period = min({float(p) for p in task_period_mapping[task]})
                task_period[task] = STM.convert_milliseconds_to_tick(
                    SECONDS_PER_TICK, min_period * 1000
                )  # Convert second to tick
            else:
                task_period[task] = -1

        return task_period

    def period_from_asw(self, autosar_asw_class, task_period_mapping, asw_instance):
        """
        Find period of event mapping to task from RteSwComponentInstance
        """
        for sub_con in getattr(getattr(asw_instance, "SUB_CONTAINERS", None), "ECUC_CONTAINER_VALUE", []):
            if get_definition_ref(sub_con).split("/")[-1] == "RteEventToTaskMapping":
                # Get mapped task (from RteMappedToTaskRef value)
                task_ref_iter = filter(
                    lambda ref: get_definition_ref(ref).split("/")[-1] == "RteMappedToTaskRef",
                    getattr(getattr(sub_con, "REFERENCE_VALUES", None), "ECUC_REFERENCE_VALUE", []),
                )
                task_ref = get_value_ref(next(task_ref_iter))
                task_name = task_ref.split("/")[-1]

                # Find RteEventRef item values
                event_ref_iter = filter(
                    lambda ref: get_definition_ref(ref).split("/")[-1] == "RteEventRef",
                    getattr(getattr(sub_con, "REFERENCE_VALUES", None), "ECUC_REFERENCE_VALUE", []),
                )
                event_ref_path_s = {get_value_ref(ref) for ref in event_ref_iter}

                # Find event period form Asw arxml
                for p in event_ref_path_s:
                    event = autosar_asw_class.find(p)
                    if hasattr(event, "PERIOD"):
                        task_period_mapping[task_name].add(get_period(event))

    def period_from_bsw(self, autosar_ib_class, task_period_mapping, bsw_instance):
        """
        Find period of event mapping to task from RteBswModuleInstance
        """
        for sub_con in getattr(getattr(bsw_instance, "SUB_CONTAINERS", None), "ECUC_CONTAINER_VALUE", []):
            if get_definition_ref(sub_con).split("/")[-1] == "RteBswEventToTaskMapping":
                module_name = get_short_name(bsw_instance)

                # Get Get mapped task (from RteBswMappedToTaskRef value)
                task_ref_iter = filter(
                    lambda ref: get_definition_ref(ref).split("/")[-1] == "RteBswMappedToTaskRef",
                    getattr(getattr(sub_con, "REFERENCE_VALUES", None), "ECUC_REFERENCE_VALUE", []),
                )
                task_ref = get_value_ref(next(task_ref_iter))
                task_name = task_ref.split("/")[-1]

                # Find RteBswEventRef item values
                event_ref_iter = filter(
                    lambda ref: get_definition_ref(ref).split("/")[-1] == "RteBswEventRef",
                    getattr(getattr(sub_con, "REFERENCE_VALUES", None), "ECUC_REFERENCE_VALUE", []),
                )
                event_ref_path_s = {get_value_ref(ref) for ref in event_ref_iter}

                # Find event period form ib arxml
                ib_bswmd = autosar_ib_class[module_name]
                for p in event_ref_path_s:
                    event = ib_bswmd.find(p)
                    if hasattr(event, "PERIOD"):
                        task_period_mapping[task_name].add(get_period(event))

    def infer_task_offset(self, autosar_bsw_class: dict, autosar_asw_class, autosar_ib_class, task_list):
        """
        Infer task offset from schedual table and alarm
        """
        os_ecuc = autosar_bsw_class.get("Os", None)
        rte_ecuc = autosar_bsw_class.get("Rte", None)

        if not os_ecuc:
            logger.ui_error("Cannot find Os_ecuc")
            return {}
        if not rte_ecuc:
            logger.ui_error("Cannot find Rte_ecuc")
            return {}

        # Getting offset from sche table(and convert tick in vcos to tick in cheddar)
        sche_task = STM.re_reasoning_all(os_ecuc, rte_ecuc, autosar_asw_class, autosar_ib_class)
        sche_task = STM.convert_os_sch_tbl_cfg_to_ui(sche_task)
        task_sche_offset = {}
        for sche_tbl in sche_task:
            # Get 'OsSecondsPerTick' from counter
            counter = os_ecuc.find(sche_tbl["counter_ref"])
            sec_per_tick = next(
                filter(
                    lambda p: get_definition_ref(p).split("/")[-1] == "OsSecondsPerTick",
                    counter.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE,
                )
            )
            sec_per_tick = float(get_value(sec_per_tick))

            for task, offset in sche_tbl["task_offset_table"].items():
                sec_offset = offset * sec_per_tick  # Convert tick in vcso proj to second
                tick_offset = sec_offset * TICK_PER_SECOND  # Convert second to tick in cheddar
                task_sche_offset[task] = int(tick_offset)

        # Mapping from task to offset from alarm info, time unit is 'tick'
        task_alarm = {
            name: BswEditor.get_used_os_alarm_infos_by_task_ref(autosar_bsw_class, f"/ActiveEcuC/Os/{name}")
            for name in task_list
        }
        task_alarm_offset = {}
        for task_name, alarm_info_l in task_alarm.items():
            alarm_tick_l = []
            for alarm_info in alarm_info_l:
                # Find alarm and its counter to get second per tick
                alarm = os_ecuc.find(alarm_info["alarm_ref"])
                counter_ref = next(
                    filter(
                        lambda r: get_definition_ref(r).split("/")[-1] == "OsAlarmCounterRef",
                        alarm.REFERENCE_VALUES.ECUC_REFERENCE_VALUE,
                    )
                )
                counter_ref = get_value_ref(counter_ref)
                counter = os_ecuc.find(counter_ref)
                sec_per_tick = next(
                    filter(
                        lambda p: get_definition_ref(p).split("/")[-1] == "OsSecondsPerTick",
                        counter.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE,
                    )
                )
                sec_per_tick = float(get_value(sec_per_tick))

                offset = float(alarm_info["offset"])
                sec_offset = offset * sec_per_tick  # Convert tick in vcso proj to second
                tick_offset = sec_offset * TICK_PER_SECOND  # Convert second to tick in cheddar
                alarm_tick_l.append(int(tick_offset))

            # Select minimum offset as task offset
            if alarm_tick_l:
                task_alarm_offset[task_name] = min(alarm_tick_l)

        task_offset = {}
        for task in task_list:
            if task in task_sche_offset:
                task_offset[task] = task_sche_offset[task]
            elif task in task_alarm_offset:
                task_offset[task] = task_alarm_offset[task]
            else:
                task_offset[task] = 0

        return task_offset

    def infer_priority(self, autosar_bsw_class: dict, task_list):
        """
        Get task priority from Os_ecuc
        """
        os_ecuc = autosar_bsw_class.get("Os", None)

        if not os_ecuc:
            return {}

        task_priority = {}
        for task in task_list:
            task_obj = os_ecuc.find(f"/ActiveEcuC/Os/{task}")
            param_iter = filter(
                lambda ref: get_definition_ref(ref).split("/")[-1] == "OsTaskPriority",
                getattr(getattr(task_obj, "PARAMETER_VALUES", None), "ECUC_NUMERICAL_PARAM_VALUE", []),
            )
            priority = get_value(next(param_iter))
            task_priority[task] = int(priority)

        return task_priority

    def build_model(self, info: Dict[str, dict], autosar_bsw_class, autosar_ib_class, autosar_asw_class):
        # Now assume only one processor
        if len(info) > 1:
            processor = CheddarProcessor("processor0", "multi_cores_processor")
        else:
            processor = CheddarProcessor("processor0", "mono_core_processor")
        self.processor_l.append(processor)

        # Address space is none of time simulation bussiness,
        # just build a default one now
        address_space = CheddarAddressSpace("address_space0")
        address_space.set_processor(processor)
        self.address_spaces_l.append(address_space)

        task_l = [
            entity
            for core_info in info.values()
            for entity, entity_info in core_info.items()
            if entity_info["type"] == "task"
        ]
        # Get period of runnable mapping to task
        task_period = self.infer_task_period_from_mapping(
            autosar_bsw_class, autosar_ib_class, autosar_asw_class, task_l
        )

        # Get offset of task
        task_offset = self.infer_task_offset(autosar_bsw_class, autosar_asw_class, autosar_ib_class, task_l)

        # Get priority of task from Os_ecuc
        task_priority = self.infer_priority(autosar_bsw_class, task_l)

        # Build core info
        for core_name, task_info in info.items():
            core = CheddarCore(core_name)
            self.core_l.append(core)
            # Add core into processor
            processor.add_core(core)

            for task_name, attr in task_info.items():
                if attr["type"] == "task":
                    task = CheddarTask(task_name)
                    self.task_l.append(task)
                    if task_period[task_name] != -1:
                        task.set_task_type("PERIODIC_TYPE")
                        task.set_deadline(task_period[task_name])
                        task.set_period(task_period[task_name])
                    else:
                        task.set_task_type("APERIODIC_TYPE")
                        task.set_deadline(0)
                        task.set_period(0)
                    task.set_processor(processor)
                    task.set_address_space(address_space)
                    task.set_core(core)
                    capacity_ms = attr[CAPACITY] if attr[CAPACITY] else 0  # If no cet filled, default value is 0
                    capacity_tick = STM.convert_milliseconds_to_tick(
                        SECONDS_PER_TICK, capacity_ms
                    )  # Convert time unit to tick
                    task.set_capacity(capacity_tick if capacity_tick > 0 else 1)  # Capacity must be greater than 0
                    task.set_start_time(task_offset[task_name])
                    task.set_priority(task_priority[task_name])

    def gen_cheddar(self, target_path):
        # Create root element
        root = etree.Element("cheddar")

        # Add core info
        core_units = etree.SubElement(root, "core_units")
        for core in self.core_l:
            core_units.append(core.to_xml())

        # Add processor info
        processors = etree.SubElement(root, "processors")
        for processor in self.processor_l:
            processors.append(processor.to_xml())

        # Add address space info
        addr_spcs = etree.SubElement(root, "address_spaces")
        for addr_apc in self.address_spaces_l:
            addr_spcs.append(addr_apc.to_xml())

        # Add task info
        tasks = etree.SubElement(root, "tasks")
        for task in self.task_l:
            tasks.append(task.to_xml())

        # Save xml
        tree = etree.ElementTree(root)
        tree.write(target_path, encoding="utf-8", xml_declaration=True, pretty_print=True)
