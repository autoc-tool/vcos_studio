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
import uuid
import math
import functools
from decimal import Decimal
from func_module.health_monitor.logger import logger
from func_module.mapping.schedule_table_mapping import ScheduleTableManager
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.autosar_utils.autosar_utils import AutosarUtils
from basic_func_module.autosar_utils.utils import (
    get_short_name,
    get_period,
    get_starts_on_event_ref,
    get_implemented_entry_ref,
    get_definition_ref,
    get_value_ref,
    get_value,
    set_value_ref,
    set_value,
    get_activation_reason_representation_ref,
    get_bit_position,
)


def get_run_data(asw_autosar_dict, ib_autosar_dict):
    run_data = {}

    application_component_data_dict, _ = AswManager.get_application_components_data(asw_autosar_dict)
    run_data["Application Components"] = application_component_data_dict

    service_component_data_dict, _ = AswManager.get_service_components_data(asw_autosar_dict)
    run_data["Service Components"] = service_component_data_dict

    schedulable_entities_data_dict, _ = IbManager.get_schedulable_entities_data(ib_autosar_dict)
    run_data["Schedulable Entities"] = schedulable_entities_data_dict

    return run_data


class TaskMappingItemData:

    def __init__(self, data):
        if isinstance(data, dict):
            data["Parent"] = self
        self._data = data
        self._mapped = False  # 默认为unmap状态
        self._uuid = str(uuid.uuid4())

    def __len__(self):
        if isinstance(self._data, str):
            return 1
        return len(self._data)

    def __str__(self):
        return self._data.__str__()

    def __setitem__(self, key: str, value):
        if key in self._data:
            self._data[key] = value
        else:
            return "key error"

    def __getitem__(self, key: str):
        if key in self._data:
            return self._data[key]
        else:
            return "key error"

    def update(self, data: dict):
        self._data.update(data)

    def __repr__(self):
        return repr(self._data)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @data.deleter
    def data(self):
        raise TypeError("cannot delete data")

    @property
    def id(self):
        return self._uuid

    @id.setter
    def id(self, value):
        self._uuid = value

    @property
    def mapped(self):
        return self._mapped

    @mapped.setter
    def mapped(self, v):
        self._mapped = v


class TaskMappingTreeItem:

    def __init__(self, data, parent=None):
        self.parent_item = parent  # 父节点
        self.child_items = []  # 子节点列表，用于对外显示
        self.child_map = {}  # 子节点map，用于查询数据
        self.item_data = TaskMappingItemData(data)  # 子节点对应数据
        self._row = -1

    def append_child(self, child: "TaskMappingTreeItem"):
        child.set_row(len(self.child_items))
        self.child_items.append(child)
        if isinstance(child.data, str):
            self.child_map[child.data] = child
        elif isinstance(child.data, dict):
            self.child_map[child.data["Name"]] = child
            if "OldName" in child.data and child.data["OldName"] not in self.child_map:
                self.child_map[child.data["OldName"]] = child

    def child(self, row):
        return self.child_items[row]

    def childCount(self):
        return len(self.child_items)

    def columnCount(self):
        return len(self.item_data)

    @property
    def data(self):
        if self.item_data:
            return self.item_data.data
        return self.item_data

    @property
    def id(self):
        if self.item_data:
            return self.item_data.id
        return ""

    @id.setter
    def id(self, value):
        if self.item_data:
            self.item_data.id = value

    @property
    def mapped(self):
        if self.item_data:
            return self.item_data.mapped
        return None

    @mapped.setter
    def mapped(self, v):
        if self.item_data:
            self.item_data.mapped = v

    def set_row(self, row: int):
        self._row = row

    def row(self):
        return self._row

    def parent(self):
        return self.parent_item if getattr(self, "parent_item", None) else None


class TaskMappingTableItem:

    def __init__(self, data):
        self.item_data: TaskMappingItemData = data
        self.bind_item_list = []

    @property
    def data(self):
        if self.item_data:
            return self.item_data.data
        return self.item_data

    @data.setter
    def data(self, value):
        if self.item_data:
            self.item_data.data = value

    @property
    def id(self):
        if self.item_data:
            return self.item_data.id
        return None

    @id.setter
    def id(self, value):
        self.item_data.id = value

    @property
    def mapped(self):
        if self.item_data:
            return self.item_data.mapped
        return None

    @mapped.setter
    def mapped(self, v):
        if self.item_data:
            self.item_data.mapped = v


class AswManager:

    @classmethod
    def get_events_from_swc(cls, swc):
        events = []
        for internal_behavior in getattr(getattr(swc, "INTERNAL_BEHAVIORS", None), "SWC_INTERNAL_BEHAVIOR", []):
            if internal_behavior.EVENTS is None:
                continue
            events += internal_behavior.EVENTS.INIT_EVENT
            events += internal_behavior.EVENTS.TIMING_EVENT
            events += internal_behavior.EVENTS.BACKGROUND_EVENT
            events += internal_behavior.EVENTS.DATA_RECEIVED_EVENT
            events += internal_behavior.EVENTS.DATA_RECEIVE_ERROR_EVENT
            events += internal_behavior.EVENTS.DATA_SEND_COMPLETED_EVENT
            events += internal_behavior.EVENTS.DATA_WRITE_COMPLETED_EVENT
            events += internal_behavior.EVENTS.OPERATION_INVOKED_EVENT
            events += internal_behavior.EVENTS.ASYNCHRONOUS_SERVER_CALL_RETURNS_EVENT
            events += internal_behavior.EVENTS.MODE_SWITCHED_ACK_EVENT
            events += internal_behavior.EVENTS.SWC_MODE_SWITCH_EVENT
            events += internal_behavior.EVENTS.EXTERNAL_TRIGGER_OCCURRED_EVENT
            events += internal_behavior.EVENTS.INTERNAL_TRIGGER_OCCURRED_EVENT
            events += internal_behavior.EVENTS.SWC_MODE_MANAGER_ERROR_EVENT
            events += internal_behavior.EVENTS.TRANSFORMER_HARD_ERROR_EVENT
        events.sort(key=lambda x: (len(str(get_short_name(x))), str(get_short_name(x)).lower()))
        return events

    @classmethod
    def get_trigger_info_from_event(cls, event):
        trigger_category = ""
        trigger_condition = ""
        event_tag = event.get_tag()
        event_type = AutosarUtils.EVENT_TYPE.get(event_tag)
        if event_type == "InitEvent":
            trigger_category = "Init"
        elif event_type == "BackgroundEvent":
            trigger_category = "Periodical in Background"
        elif event_type == "TimingEvent":
            period = event.PERIOD.valueOf_
            trigger_category = "Periodical"
            if period in ["None", None, ""]:
                logger.error(f"{get_short_name(event)} period format error!")
            else:
                trigger_condition = f"{int(float(period)*1000)}ms"
        elif event_type == "DataReceivedEvent":
            trigger_category = "Data Reception"
            data_iref = event.DATA_IREF
            rport = data_iref.CONTEXT_R_PORT_REF.valueOf_.split("/").pop()
            element = data_iref.TARGET_DATA_ELEMENT_REF.valueOf_.split("/").pop()
            trigger_condition = f"{rport}.{element}"
        elif event_type == "OperationInvokedEvent":
            trigger_category = "Operation Invocation"
            operation_iref = event.OPERATION_IREF
            service = operation_iref.CONTEXT_P_PORT_REF.valueOf_.split("/").pop()
            operation = operation_iref.TARGET_PROVIDED_OPERATION_REF.valueOf_.split("/").pop()
            trigger_condition = f"{service}.{operation}"
        elif event_type in {"DataSendCompletedEvent", "DataWriteCompletedEvent"}:
            trigger_category = "Data Send Completion"
            event_source = event.find(event.EVENT_SOURCE_REF.valueOf_)
            autosar_variable_iref = event_source.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF
            port_name = autosar_variable_iref.PORT_PROTOTYPE_REF.valueOf_.split("/").pop()
            data_element_name = autosar_variable_iref.TARGET_DATA_PROTOTYPE_REF.valueOf_.split("/").pop()
            trigger_condition = f"{port_name}.{data_element_name}"
        elif event_type == "ModeSwitchedAckEvent":
            trigger_category = "Mode Switch Acknowledge"
            mode_declaration_group = event.find(event.EVENT_SOURCE_REF.valueOf_)
            if mode_declaration_group:
                port = mode_declaration_group.MODE_GROUP_IREF.CONTEXT_P_PORT_REF.valueOf_.split("/").pop()
                group = mode_declaration_group.MODE_GROUP_IREF.TARGET_MODE_GROUP_REF.valueOf_.split("/").pop()
                trigger_condition = f"{port}.{group}"
        elif event_type == "SwcModeSwitchEvent":
            trigger_category = event.ACTIVATION.valueOf_
            entry_mode_iref = None
            exit_mode_iref = None
            if trigger_category == "ON-ENTRY":
                trigger_category = "Mode Entry"
                entry_mode_iref = event.MODE_IREFS.MODE_IREF[0]
            elif trigger_category == "ON-TRANSITION":
                trigger_category = "Mode Transition"
                exit_mode_iref = event.MODE_IREFS.MODE_IREF[0]
                entry_mode_iref = event.MODE_IREFS.MODE_IREF[1]
            elif trigger_category == "ON-EXIT":
                trigger_category = "Mode Exit"
                exit_mode_iref = event.MODE_IREFS.MODE_IREF[0]
            entry_tip = ""
            if entry_mode_iref:
                entry_port = entry_mode_iref.CONTEXT_PORT_REF.valueOf_.split("/").pop()
                entry_group = entry_mode_iref.CONTEXT_MODE_DECLARATION_GROUP_PROTOTYPE_REF.valueOf_.split("/").pop()
                entry_declaration = entry_mode_iref.TARGET_MODE_DECLARATION_REF.valueOf_.split("/").pop()
                entry_tip = f"{entry_port}.{entry_group}.{entry_declaration}"
            exit_tip = ""
            if exit_mode_iref:
                exit_port = exit_mode_iref.CONTEXT_PORT_REF.valueOf_.split("/").pop()
                exit_group = exit_mode_iref.CONTEXT_MODE_DECLARATION_GROUP_PROTOTYPE_REF.valueOf_.split("/").pop()
                exit_declaration = exit_mode_iref.TARGET_MODE_DECLARATION_REF.valueOf_.split("/").pop()
                exit_tip = f"{exit_port}.{exit_group}.{exit_declaration}"
            if trigger_category == "Mode Entry":
                trigger_condition = f"{entry_tip}"
            elif trigger_category == "Mode Transition":
                trigger_condition = f"{exit_tip} -> {entry_tip}"
            elif trigger_category == "Mode Exit":
                trigger_condition = f"{exit_tip}"
        elif event_type == "InternalTriggerOccurredEvent":
            trigger_category = "Internal Trigger Occurred"
            runnable = event.START_ON_EVENT_REF.valueOf_.split("/").pop()
            internal_trigger_point = event.EVENT_SOURCE_REF.valueOf_.split("/").pop()
            trigger_condition = f"{runnable}.{internal_trigger_point}"
        elif event_type == "ExternalTriggerOccurredEvent":
            trigger_category = "External Trigger Occurred"
            port = event.TRIGGER_IREF.CONTEXT_R_PORT_REF.valueOf_.split("/").pop()
            trigger = event.TRIGGER_IREF.TARGET_TRIGGER_REF.valueOf_.split("/").pop()
            trigger_condition = f"{port}.{trigger}"
        return trigger_category, trigger_condition

    @classmethod
    def get_old_event_name(cls, event, runnable_name):
        old_event_name = None
        event_tag = event.get_tag()
        if event_tag == "INIT-EVENT":
            old_event_name = f"{runnable_name}_InitEvent"
        elif event_tag == "TIMING-EVENT":
            old_event_name = f"TMT_{runnable_name}"
        elif event_tag == "BACKGROUND-EVENT":
            old_event_name = "Background_Event"
        elif event_tag == "DATA-RECEIVED-EVENT":
            rport = event.find(event.DATA_IREF.CONTEXT_R_PORT_REF.valueOf_)
            rport_name = get_short_name(rport)
            data_element = event.find(event.DATA_IREF.TARGET_DATA_ELEMENT_REF.valueOf_)
            data_element_name = get_short_name(data_element)
            old_event_name = f"DRT_{runnable_name}_{rport_name}_{data_element_name}"
        elif event_tag == "OPERATION-INVOKED-EVENT":
            pport = event.find(event.OPERATION_IREF.CONTEXT_P_PORT_REF.valueOf_)
            pport_name = get_short_name(pport)
            operation = event.find(event.OPERATION_IREF.TARGET_PROVIDED_OPERATION_REF.valueOf_)
            operation_name = get_short_name(operation)
            old_event_name = f"OIT_{runnable_name}_{pport_name}_{operation_name}"

        return old_event_name

    @classmethod
    def get_swc_events(cls, swc, is_mainfunction=False, is_service=False):
        events = {}
        swc_name = get_short_name(swc)

        for event in cls.get_events_from_swc(swc):
            # 1）判断START_ON_EVENT_REF是否存在
            if event.START_ON_EVENT_REF is None:
                continue

            # 2）判断runnable相关信息是否合法
            runnable_path = event.START_ON_EVENT_REF.valueOf_
            runnable_entity = swc.find(runnable_path)
            if not runnable_entity:
                logger.error(f"invalid {runnable_path}")
                continue
            runnable_name = (
                runnable_entity.SYMBOL.valueOf_ if runnable_entity.SYMBOL else get_short_name(runnable_entity)
            )

            # 3）判断event类型是否在关注列表中
            event_tag = event.get_tag()
            event_type = AutosarUtils.EVENT_TYPE.get(event_tag)

            activation_reason = None
            activation_reason_ref = get_activation_reason_representation_ref(event)
            if activation_reason_ref:
                _activation_reason = event.find(activation_reason_ref)
                activation_reason = {}
                activation_reason["Name"] = get_short_name(_activation_reason)
                activation_reason["BitPosition"] = get_bit_position(_activation_reason)

            if not event_type:
                logger.warning(f"Unsupported Event: {event_tag}")
                continue

            # 4）准备数据，保证swc中的event与os中的event一致
            event_name = get_short_name(event)
            if not event_name:
                continue

            old_event_name = cls.get_old_event_name(event, runnable_name)
            if old_event_name and old_event_name != event_name:
                # logger.debug(f"old: {old_event_name}, new: {event_name}")
                pass

            period = event.PERIOD.valueOf_ if hasattr(event, "PERIOD") and event.PERIOD else None
            trigger_category, trigger_condition = cls.get_trigger_info_from_event(event)
            event_ref = event.get_path()

            event_info = {}
            event_info["Parent"] = None
            event_info["Period"] = period
            event_info["IsServiceComponent"] = is_service
            event_info["IsMainFunction"] = is_mainfunction and event_tag == "TIMING-EVENT"
            event_info["EventRef"] = event_ref
            event_info["BindEvent"] = []
            event_info["TriggerEvent"] = event_type
            event_info["Component"] = swc_name
            event_info["RunnableName"] = runnable_name
            event_info["Name"] = event_name
            event_info["OldName"] = old_event_name
            event_info["TriggerCategory"] = trigger_category
            event_info["TriggerCondition"] = trigger_condition
            event_info["ActivationReason"] = activation_reason
            events[event_name] = event_info

        return events

    @classmethod
    def get_application_components_data(cls, asw_autosar):
        application_component_data_dict = {}
        component_types = []
        if not asw_autosar:
            return application_component_data_dict, component_types

        for comp_type in AutosarUtils.SUPPORT_APPL_COMPONENT_TYPE:
            component_types += asw_autosar.find_nodes(comp_type)
        component_types.sort(key=get_short_name)
        for swc in component_types:
            swc_name = get_short_name(swc)
            events = cls.get_swc_events(swc)
            application_component_data_dict.update({swc_name: events})
        return application_component_data_dict, component_types

    @classmethod
    def get_service_components_data(cls, asw_autosar):
        service_component_data_dict = {}
        component_types = []
        if not asw_autosar:
            return service_component_data_dict, component_types

        for comp_type in AutosarUtils.SUPPORT_SERVICE_COMPONENT_TYPE:
            component_types.extend(asw_autosar.find_nodes(comp_type))
        component_types.sort(key=get_short_name)
        for swc in component_types:
            swc_name = get_short_name(swc)
            events = cls.get_swc_events(swc, True, True)
            service_component_data_dict.update({swc_name: events})
        return service_component_data_dict, component_types


class IbManager:

    @classmethod
    def get_module_events(cls, bsw_module_description):
        events = {}
        if not bsw_module_description:
            return events
        module_name = get_short_name(bsw_module_description)
        timing_events = bsw_module_description.find_nodes("BSW-TIMING-EVENT")
        timing_events.sort(key=get_short_name)
        for timing_event in timing_events:
            period = get_period(timing_event)
            if period in ["None", None, ""]:
                logger.error(f"{module_name} module periodical error!")
                continue
            event_name = get_short_name(timing_event)
            if not event_name:
                continue
            starts_on_event_ref = get_starts_on_event_ref(timing_event)
            if starts_on_event_ref is None:
                continue
            schedulable_entity = timing_event.find(starts_on_event_ref)
            implemented_entry_ref = get_implemented_entry_ref(schedulable_entity)
            if implemented_entry_ref is None:
                continue
            module_entry = timing_event.find(implemented_entry_ref)
            main_function_name = get_short_name(module_entry)

            event_info = {}
            event_info["Parent"] = None
            event_info["Period"] = period
            event_info["IsServiceComponent"] = False
            event_info["IsMainFunction"] = True
            event_info["EventRef"] = timing_event.get_path()
            event_info["BindEvent"] = []
            event_info["TriggerEvent"] = "TimingEvent"
            event_info["Component"] = module_name
            event_info["RunnableName"] = main_function_name
            event_info["Name"] = event_name
            event_info["TriggerCategory"] = "Periodical"
            event_info["TriggerCondition"] = f"{int(float(period)*1000)}ms"
            events[event_name] = event_info
        return events

    @classmethod
    def get_schedulable_entities_data(cls, ib_autosar_dict):
        schedulable_entities_data_dict = {}
        bsw_module_descriptions = []
        for module_name, info in ib_autosar_dict.items():
            if not module_name or not info:
                continue
            bsw_module_description_list = info.find_nodes("BSW-MODULE-DESCRIPTION")
            if len(bsw_module_description_list) == 0:
                continue
            events = cls.get_module_events(bsw_module_description_list[0])
            schedulable_entities_data_dict[module_name] = events
            bsw_module_descriptions.append(bsw_module_description_list[0])
        return schedulable_entities_data_dict, bsw_module_descriptions


class RteManager:

    @classmethod
    def update_rte_sw_component_exclusive_area(cls, component_types, mod_autosar, rte_autosar):
        rte = rte_autosar.find("/ActiveEcuC/Rte")
        for component_type in component_types:
            tag = component_type.get_tag()
            component_name = get_short_name(component_type)
            if not tag.endswith("SW-COMPONENT-TYPE"):
                continue
            ea_conf_def = mod_autosar.find(
                "/AUTOSAR/EcucDefs/Rte/RteSwComponentInstance/RteExclusiveAreaImplementation"
            )
            component_name = f"{component_name}_EcuSwComposition"
            component_container = rte.find(f"./{component_name}")
            if component_container is None:
                conf_def = mod_autosar.find("/AUTOSAR/EcucDefs/Rte/RteSwComponentInstance")
                component_container = AutosarUtil.create_container_value(component_name, conf_def, rte)
            swc_internal_behaviors = getattr(
                getattr(component_type, "INTERNAL_BEHAVIORS", None), "SWC_INTERNAL_BEHAVIOR", []
            )
            cls.update_rte_exclusive_area_impl(swc_internal_behaviors, ea_conf_def, component_container)

    @classmethod
    def update_rte_bsw_module_exclusive_area(cls, bsw_module_descriptions, mod_autosar, rte_autosar):
        rte = rte_autosar.find("/ActiveEcuC/Rte")
        for bsw_module_description in bsw_module_descriptions:
            tag = bsw_module_description.get_tag()
            module_name = get_short_name(bsw_module_description)
            if tag != "BSW-MODULE-DESCRIPTION":
                continue
            ea_conf_def = mod_autosar.find("/AUTOSAR/EcucDefs/Rte/RteBswModuleInstance/RteBswExclusiveAreaImpl")
            component_container = rte.find(f"./{module_name}")
            if component_container is None:
                conf_def = mod_autosar.find("/AUTOSAR/EcucDefs/Rte/RteBswModuleInstance")
                component_container = AutosarUtil.create_container_value(module_name, conf_def, rte)
            cls.update_rte_exclusive_area_impl(
                bsw_module_description.INTERNAL_BEHAVIORS.BSW_INTERNAL_BEHAVIOR, ea_conf_def, component_container
            )

    @classmethod
    def update_rte_exclusive_area_impl(cls, internal_behaviors, ea_conf_def, parent):
        # 判断ib中是否有ea信息，有的话就在rte中创建或更新container
        for internal_behavior in internal_behaviors:
            if internal_behavior.EXCLUSIVE_AREAS is None:
                continue
            for exclusive_area in internal_behavior.EXCLUSIVE_AREAS.EXCLUSIVE_AREA:
                exclusive_area_name = get_short_name(exclusive_area)
                ea_container = parent.find(f"./{exclusive_area_name}")
                if ea_container is not None:
                    continue
                ea_container = AutosarUtil.create_container_value(exclusive_area_name, ea_conf_def, parent)
                values = ea_container.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE
                for value in values:
                    def_ref = get_definition_ref(value)
                    if def_ref.endswith("RteExclusiveAreaImplMechanism"):
                        set_value(value, "OS_INTERRUPT_BLOCKING")
                values = ea_container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE
                for value in values:
                    def_ref = get_definition_ref(value)
                    if def_ref.endswith("ExclusiveAreaRef"):
                        # RteExclusiveAreaRef or RteBswExclusiveAreaRef
                        exclusive_area_ref = exclusive_area.get_path()
                        set_value_ref(value, exclusive_area_ref)

    @classmethod
    def get_task_mapping_dict(cls, container_value, perfix):
        task_mapping_dict = {}
        duplicate_containers = []
        for sub_container_value in container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
            def_name = get_definition_ref(sub_container_value)
            if def_name is None:
                logger.error(f"{get_short_name(sub_container_value)} def_name is None")
            if not def_name.endswith(f"{perfix}EventToTaskMapping"):
                continue
            values = []
            if hasattr(sub_container_value, "PARAMETER_VALUES"):
                values += sub_container_value.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE
                values += sub_container_value.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE
            if hasattr(sub_container_value, "REFERENCE_VALUES"):
                values += sub_container_value.REFERENCE_VALUES.ECUC_REFERENCE_VALUE
            mapping_name = get_short_name(sub_container_value)
            mapping_cfg = {}
            mapping_cfg[f"{perfix}ActivationOffset"] = 0
            for value in values:
                value_type = get_definition_ref(value)
                if value_type.endswith(f"{perfix}ActivationOffset"):
                    mapping_cfg[f"{perfix}ActivationOffset"] = get_value(value)
                elif value_type.endswith(f"{perfix}PositionInTask"):
                    mapping_cfg[f"{perfix}PositionInTask"] = get_value(value)
                elif value_type.endswith(f"{perfix}EventRef"):
                    mapping_cfg[f"{perfix}EventRef"] = get_value_ref(value)
                elif value_type.endswith(f"{perfix}MappedToTaskRef"):
                    mapping_cfg[f"{perfix}MappedToTaskRef"] = get_value_ref(value)
                elif value_type.endswith(f"{perfix}UsedOsAlarmRef"):
                    mapping_cfg[f"{perfix}UsedOsAlarmRef"] = get_value_ref(value)
                elif value_type.endswith(f"{perfix}UsedOsEventRef"):
                    mapping_cfg[f"{perfix}UsedOsEventRef"] = get_value_ref(value)
            if mapping_name not in task_mapping_dict:
                task_mapping_dict[mapping_name] = mapping_cfg
            else:
                duplicate_containers.append(sub_container_value)
        # 删除重复的子container
        for sub_container_value in duplicate_containers:
            container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE.remove(sub_container_value)
        return task_mapping_dict

    @classmethod
    def get_rte_task_mapping_info(cls, rte_autosar):
        rte_swc_instances = {}
        rte_bsw_module_instances = {}
        rte_cfg = rte_autosar.find("/ActiveEcuC/Rte")
        container_values = rte_cfg.CONTAINERS.ECUC_CONTAINER_VALUE
        for container_value in container_values:
            if container_value.SUB_CONTAINERS is None:
                continue
            def_tag = get_definition_ref(container_value)
            if def_tag.endswith("RteBswModuleInstance"):
                module_name = get_short_name(container_value)
                task_mapping = cls.get_task_mapping_dict(container_value, "RteBsw")
                rte_bsw_module_instances[module_name] = task_mapping
            elif def_tag.endswith("RteSwComponentInstance"):
                swc_name = get_short_name(container_value)
                task_mapping = cls.get_task_mapping_dict(container_value, "Rte")
                rte_swc_instances[swc_name] = task_mapping
        return rte_swc_instances, rte_bsw_module_instances

    @classmethod
    def get_rte_used_alarm_count(cls, rte_autosar, alarm_name):
        rte_swc_instances, rte_bsw_module_instances = cls.get_rte_task_mapping_info(rte_autosar)
        used_alarm_count = 0
        for mapping_cfg in rte_swc_instances.values():
            if alarm_name in mapping_cfg["RteUsedOsAlarmRef"]:
                used_alarm_count += 1

        for mapping_cfg in rte_bsw_module_instances.values():
            if alarm_name in mapping_cfg["RteBswUsedOsAlarmRef"]:
                used_alarm_count += 1

        return used_alarm_count

    @classmethod
    def get_rte_used_event_count(cls, rte_autosar, event_name):
        rte_swc_instances, rte_bsw_module_instances = cls.get_rte_task_mapping_info(rte_autosar)
        used_event_count = 0
        for mapping_cfg in rte_swc_instances.values():
            if event_name in mapping_cfg["RteUsedOsEventRef"]:
                used_event_count += 1

        for mapping_cfg in rte_bsw_module_instances.values():
            if event_name in mapping_cfg["RteBswUsedOsEventRef"]:
                used_event_count += 1

        return used_event_count

    @classmethod
    def get_swc_os_info(cls, task_info, event_info):
        trigger_event = event_info["TriggerEvent"]
        task_name = task_info["OsTaskName"]
        os_event_name, os_alarm_name = None, None
        if trigger_event == "TimingEvent":
            period = Decimal(str(event_info["Period"]))
            fractional_part, _ = math.modf(period * 1000)
            if fractional_part > 0:
                unit = "us"
                period = int(Decimal(period) * 1000 * 1000)
            else:
                unit = "ms"
                period = int(Decimal(period) * 1000)
            # os_alarm_name = f"Rte_Al_TE_{task_name}_0_{period}{unit}"
            if task_info["OsTaskType"] == "EXTENDED":
                os_event_name = f"Rte_Ev_Cyclic_{task_name}_0_{period}{unit}"
        elif trigger_event == "DataReceivedEvent":
            os_event_name = cls.get_os_event_name(event_info)
        elif trigger_event == "OperationInvokedEvent":
            os_event_name = cls.get_os_event_name(event_info)
        elif trigger_event == "SwcModeSwitchEvent":
            os_event_name = cls.get_os_event_name(event_info)
        elif trigger_event in {"DataSendCompletedEvent", "DataWriteCompletedEvent"}:
            os_event_name = cls.get_os_event_name(event_info)
        elif trigger_event == "AsynchronousServerCallReturnsEvent":
            os_event_name = cls.get_os_event_name(event_info)
        elif trigger_event == "InternalTriggerOccurredEvent":
            os_event_name = cls.get_os_event_name(event_info)
        elif trigger_event == "ExternalTriggerOccurredEvent":
            os_event_name = cls.get_os_event_name(event_info)
        return os_event_name, os_alarm_name

    @classmethod
    def get_os_event_name(cls, event_info):
        os_event_name = ""
        if event_info["ActivationReason"]:
            bit_position = event_info["ActivationReason"]["BitPosition"]
            os_event_name = f"Rte_Ev_Run{bit_position}_{event_info['Component']}_{event_info['RunnableName']}"
        else:
            if event_info["TriggerCategory"] == "External Trigger Occurred":
                port_trigger = event_info["TriggerCondition"].replace(".", "_")
                os_event_name = f"Rte_Ev_Run_{event_info['Component']}_{event_info['RunnableName']}_{port_trigger}"
            else:
                os_event_name = f"Rte_Ev_Run_{event_info['Component']}_{event_info['RunnableName']}"
        return os_event_name

    @classmethod
    def get_bsw_os_info(cls, task_info, event_info):
        trigger_event = event_info["TriggerEvent"]
        task_name = task_info["OsTaskName"]
        os_event_name, os_alarm_name = None, None
        if trigger_event == "TimingEvent":
            period = Decimal(str(event_info["Period"]))
            fractional_part, _ = math.modf(period * 1000)
            if fractional_part > 0:
                unit = "us"
                period = int(period * 1000 * 1000)
            else:
                unit = "ms"
                period = int(period * 1000)
            # os_alarm_name = f"Rte_Al_TE2_{task_name}_0_{period}{unit}"
            if task_info["OsTaskType"] == "EXTENDED":
                os_event_name = f"Rte_Ev_Cyclic2_{task_name}_0_{period}{unit}"
        return os_event_name, os_alarm_name

    @classmethod
    def add_rte_bsw_instance(cls, rte_autosar, mod_autosar, bsw_module_instance, row, task_info, event_info):
        bsw_module_name = event_info["Component"]
        for reference in bsw_module_instance.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
            def_ref = get_definition_ref(reference)
            # this parameter is not used and is currently not supported
            # if def_ref.endswith("RteBswImplementationRef"):
            #     impl_ref = event_info["EventRef"].split("/")[:-2]
            #     set_value_ref(reference, "/".join(impl_ref))
            if def_ref.endswith("RteBswModuleConfigurationRef"):
                set_value_ref(reference, f"/ActiveEcuC/{bsw_module_name}")

        event_name = event_info["Name"]
        event_container = rte_autosar.find(f"/ActiveEcuC/Rte/{bsw_module_name}/{event_name}")
        if event_container is None:
            mapping_conf_def = mod_autosar.find("/AUTOSAR/EcucDefs/Rte/RteBswModuleInstance/RteBswEventToTaskMapping")
            event_container = AutosarUtil.create_sub_container_value(event_name, mapping_conf_def, bsw_module_instance)

        task_name = task_info["OsTaskName"]
        if event_info["IsMainFunction"]:
            os_event_name, os_alarm_name = cls.get_bsw_os_info(task_info, event_info)
        else:
            os_event_name, os_alarm_name = cls.get_swc_os_info(task_info, event_info)
        values = []
        values += event_container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE
        values += event_container.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE
        values += event_container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE
        for value in values:
            def_ref = get_definition_ref(value)
            if def_ref.endswith("RteBswImmediateRestart"):
                set_value(value, "false")
            elif def_ref.endswith("RteBswPositionInTask"):
                set_value(value, str(row))
            elif def_ref.endswith("RteBswEventRef"):
                rte_event_ref = event_info["EventRef"]
                set_value_ref(value, rte_event_ref)
            elif def_ref.endswith("RteBswMappedToTaskRef"):
                set_value_ref(value, f"/ActiveEcuC/Os/{task_name}")
            elif def_ref.endswith("RteBswUsedOsEventRef"):
                if os_event_name:
                    set_value_ref(value, f"/ActiveEcuC/Os/{os_event_name}")
                else:
                    set_value_ref(value, None)
            elif def_ref.endswith("RteBswUsedOsAlarmRef"):
                if os_alarm_name:
                    set_value_ref(value, f"/ActiveEcuC/Os/{os_alarm_name}")
                else:
                    set_value_ref(value, None)

    @classmethod
    def add_rte_swc_instance(cls, rte_autosar, mod_autosar, swc_instance, row, task_info, event_info):
        swc_name = get_short_name(swc_instance)

        event_name = event_info["Name"]
        event_container = rte_autosar.find(f"/ActiveEcuC/Rte/{swc_name}/{event_name}")
        if event_container is None:
            mapping_conf_def = mod_autosar.find("/AUTOSAR/EcucDefs/Rte/RteSwComponentInstance/RteEventToTaskMapping")
            event_container = AutosarUtil.create_sub_container_value(event_name, mapping_conf_def, swc_instance)

        task_name = task_info["OsTaskName"]
        if event_info["IsMainFunction"]:
            os_event_name, os_alarm_name = cls.get_bsw_os_info(task_info, event_info)
        else:
            os_event_name, os_alarm_name = cls.get_swc_os_info(task_info, event_info)

        values = []
        values += event_container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE
        values += event_container.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE
        values += event_container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE
        for value in values:
            def_ref = get_definition_ref(value)
            if def_ref.endswith("RteImmediateRestart"):
                set_value(value, "false")
            elif def_ref.endswith("RtePositionInTask"):
                set_value(value, str(row))
            elif def_ref.endswith("RteEventRef"):
                rte_event_ref = event_info["EventRef"]
                set_value_ref(value, rte_event_ref)
            elif def_ref.endswith("RteMappedToTaskRef"):
                set_value_ref(value, f"/ActiveEcuC/Os/{task_name}")
            elif def_ref.endswith("RteUsedOsEventRef"):
                if os_event_name:
                    set_value_ref(value, f"/ActiveEcuC/Os/{os_event_name}")
                else:
                    set_value_ref(value, None)
            elif def_ref.endswith("RteUsedOsAlarmRef"):
                if os_alarm_name:
                    set_value_ref(value, f"/ActiveEcuC/Os/{os_alarm_name}")
                else:
                    set_value_ref(value, None)

    @classmethod
    def add_rte_instance(cls, rte_autosar, mod_autosar, row, task_info, event_info):
        _, component_container = cls.get_rte_component_info(rte_autosar, event_info)
        if event_info["IsMainFunction"] and not event_info["IsServiceComponent"]:
            cls.add_rte_bsw_instance(rte_autosar, mod_autosar, component_container, row, task_info, event_info)
        else:
            cls.add_rte_swc_instance(rte_autosar, mod_autosar, component_container, row, task_info, event_info)

    @classmethod
    def remove_rte_instance(cls, rte_autosar, event_info):
        component_name, component_container = cls.get_rte_component_info(rte_autosar, event_info)
        event_name = event_info["Name"]
        event_container = rte_autosar.find(f"/ActiveEcuC/Rte/{component_name}/{event_name}")
        if event_container:
            AutosarUtil.remove_container_value(component_container.SUB_CONTAINERS.ECUC_CONTAINER_VALUE, event_container)

    @classmethod
    def get_rte_component_info(cls, rte_autosar, event_info):
        component_name = event_info["Component"]
        if event_info["IsMainFunction"] and not event_info["IsServiceComponent"]:
            component_container = rte_autosar.find(f"/ActiveEcuC/Rte/{component_name}")
        else:
            component_name = f"{component_name}_EcuSwComposition"
            component_container = rte_autosar.find(f"/ActiveEcuC/Rte/{component_name}")
        return component_name, component_container

    @classmethod
    def get_rte_param_container(cls, rte_autosar, event_info, param_name):
        # eg:ActivationOffset, 后面可以优化成枚举的形式
        value_container = None
        component_name, _ = cls.get_rte_component_info(rte_autosar, event_info)
        event_name = event_info["Name"]
        event_container = rte_autosar.find(f"/ActiveEcuC/Rte/{component_name}/{event_name}")
        if not event_container:
            return value_container

        values = []
        values += event_container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE
        values += event_container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE
        values += event_container.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE
        for value in values:
            def_ref = get_definition_ref(value)
            if def_ref.endswith(f"{param_name}"):
                value_container = value
                break
        return value_container

    @classmethod
    def get_rte_param_value(cls, rte_autosar, event_info, param_name):
        param_value = None
        value_container = cls.get_rte_param_container(rte_autosar, event_info, param_name)
        if not value_container:
            return param_value

        tag = value_container.original_tagname_
        if tag in ["ECUC-NUMERICAL-PARAM-VALUE", "ECUC-TEXTUAL-PARAM-VALUE"]:
            param_value = get_value(value_container)
        elif tag in ["ECUC-REFERENCE-VALUE"]:
            param_value = get_value_ref(value_container)

        return param_value

    @classmethod
    def set_rte_param_value(cls, rte_autosar, event_info, param_name, param_value):
        value_container = cls.get_rte_param_container(rte_autosar, event_info, param_name)
        if not value_container:
            return

        tag = value_container.original_tagname_
        if tag in ["ECUC-NUMERICAL-PARAM-VALUE", "ECUC-TEXTUAL-PARAM-VALUE"]:
            set_value(value_container, param_value)
        elif tag in ["ECUC-REFERENCE-VALUE"]:
            set_value_ref(value_container, param_value)
        return


class BasicTaskScheduleTableManager:

    @classmethod
    def get_os_init_schedule_table_name(cls, task_name):
        if task_name is None:
            return None

        return f"InitScheduleTable_{task_name}"

    @classmethod
    def get_os_main_schedule_table_name(cls, task_name):
        if task_name is None:
            return None

        return f"MainScheduleTable_{task_name}"

    @classmethod
    def get_lcm(cls, numbers):
        return functools.reduce((lambda x, y: int(x * y / math.gcd(x, y))), numbers)

    @classmethod
    def get_schedule_table_cfg(cls, timing_offset_dict, task_name):
        # 1) 判断参数合法性
        if not timing_offset_dict or not task_name:
            return None, None

        # 判断是否存在不同周期的runnable
        if len(timing_offset_dict) < 2:
            return None, None

        # NOTE Basic Task调度表目前不支持float的offset类型，不支持1ms以下的触发周期
        timing_offset_dict = {int(k): int(v) for k, v in timing_offset_dict.items()}
        # 周期最小值
        min_period = min(timing_offset_dict.keys())
        # 最大公约数
        gcd = functools.reduce(math.gcd, timing_offset_dict.keys())
        # 最小公倍数
        lcm = cls.get_lcm(timing_offset_dict.keys())
        if min_period <= 0 or gcd <= 0 or lcm <= 0:
            log_str = f"the min_period:{min_period}, gcd:{gcd}, lcm:{lcm} param error"
            logger.warning(log_str)
            return None, None

        max_offset = max(timing_offset_dict.values())
        min_offset = min(timing_offset_dict.values())

        # main的周期默认为最小公倍数
        main_duration = lcm
        # 如果周期最小值等于最大公约数且无偏移时，main的周期才等于最大公约数
        if min_period == gcd and max_offset == 0:
            main_duration = gcd

        # 记录period最新的index
        period_index_dict = {}
        # 2) 判断init schedule table是否存在，若存在则推理出相关配置
        init_schedule_table_cfg = None
        # init的周期默认为偏移最大值
        init_duration = max_offset
        if init_duration > 0:
            init_schedule_table_cfg = {
                "name": cls.get_os_init_schedule_table_name(task_name),
                "duration": 0,
                "repeat": False,
                "step_dict": {},
                "expiry_point_dict": {},
                "code_gen": True,
            }
            # 如果所有offset都相同，则init_duration需要叠加main_duration，且与main共享step调度关系
            if max_offset == min_offset:
                init_duration += main_duration
                init_schedule_table_cfg["code_gen"] = False

            init_schedule_table_cfg["duration"] = init_duration
            init_schedule_table_cfg["expiry_point_dict"] = cls.get_schedule_table_expiry_dict(
                0, init_duration, timing_offset_dict, period_index_dict
            )
            # 对于init schedule table来说，到期点个数就是step个数
            init_schedule_table_cfg["step_dict"] = init_schedule_table_cfg["expiry_point_dict"]

        # 3）推理出main schedule table的相关配置
        main_schedule_table_cfg = {
            "name": cls.get_os_main_schedule_table_name(task_name),
            "duration": main_duration,
            "repeat": True,
            "step_dict": {},
            "expiry_point_dict": {},
            "code_gen": True,
        }
        # 默认以lcm为上限来求step调度关系
        main_step_dict = cls.get_schedule_table_expiry_dict(
            init_duration, init_duration + lcm, timing_offset_dict, period_index_dict
        )
        # 对main schedule table统一做一个大小为init_duration的偏移
        main_step_dict = dict(
            zip([period - init_duration for period in main_step_dict.keys()], main_step_dict.values())
        )
        main_schedule_table_cfg["step_dict"] = main_step_dict
        # 以main_duration为上限来截断
        main_schedule_table_cfg["expiry_point_dict"] = {
            index: runnables for index, runnables in main_step_dict.items() if index < main_duration
        }

        return init_schedule_table_cfg, main_schedule_table_cfg

    @classmethod
    def get_schedule_table_expiry_dict(cls, start, end, timing_offset_dict, period_index_dict):
        expiry_point_dict = {}
        for index_ms in range(start, end):
            expiry_runnable_list = []
            # 1）首先查找offset未就位的且满足时刻要求的runnable，优先级最高
            offset_not_ready_dict = {
                period: offset
                for period, offset in timing_offset_dict.items()
                if offset <= index_ms and period not in period_index_dict
            }
            for period in offset_not_ready_dict.keys():
                expiry_runnable_list.append(period)
                period_index_dict.update({period: index_ms})

            # 2）然后查找所有已到期的period
            period_already_dict = {
                period: index for period, index in period_index_dict.items() if (index_ms - index) >= period
            }
            for period in period_already_dict.keys():
                period_index_dict.update({period: index_ms})
                if period not in expiry_runnable_list:
                    expiry_runnable_list.append(period)
            if not expiry_runnable_list:
                continue
            expiry_point_dict.update({index_ms: expiry_runnable_list})
            pass
        expiry_point_dict = dict(sorted(expiry_point_dict.items()))
        return expiry_point_dict

    # 检查mapping合法性和或获取timing_offset_dict
    @classmethod
    def get_timing_offset_dict(cls, rte_autosar, event_list, task_name):
        timing_offset_dict = {}
        if not event_list:
            return True, timing_offset_dict

        # basic task 上配置的event是否合法
        mapping_validation = True
        trigger_event_mask = 0
        log_str = None
        for event_info in event_list:
            trigger_event = event_info["TriggerEvent"]
            if trigger_event == "BackgroundEvent":
                trigger_event_mask = 1
            elif trigger_event == "InitEvent":
                trigger_event_mask |= 1 << 1
            elif trigger_event == "TimingEvent":
                trigger_event_mask |= 1 << 2
                period = Decimal(event_info["Period"]) * 1000
                offset = RteManager.get_rte_param_value(rte_autosar, event_info, "ActivationOffset")
                if not offset:
                    offset = 0
                if isinstance(offset, str):
                    offset = float(offset)
                if period not in timing_offset_dict:
                    timing_offset_dict.update({period: offset})
                else:
                    offset_value = timing_offset_dict.get(period)
                    if offset != offset_value:
                        log_str = f"the {event_info['Component']}.{event_info['RunnableName']} offset is different"
                        # TODO 转换为校验规则
                        logger.warning(log_str)
            else:
                mapping_validation = False
                trigger_event_mask = -1
                log_str = f"Basic Task {task_name} can't map runnable with event:{trigger_event}"
                break

        # 根据mask的值来判断runanble的组合形式，进一步判断合法性
        if trigger_event_mask == -1:
            # trigger_event_mask(-1): Other NG
            logger.error(log_str)
            return mapping_validation, timing_offset_dict
        elif trigger_event_mask in range(0, 4):
            # trigger_event_mask(1): Backgroung OK
            # trigger_event_mask(2): Init OK
            # trigger_event_mask(3): Background + Init OK
            return mapping_validation, timing_offset_dict
        elif trigger_event_mask == (1 << 2):
            return True, timing_offset_dict
        else:
            # trigger_event_mask(>4): Timing + Other NG
            log_str = f"Basic Task {task_name} can't map runnable with timing event and others together"
            # TODO 转换为校验规则
            logger.ui_error(log_str)
            return False, timing_offset_dict


class PortManager:

    # NOTE:有测试用例调用
    @classmethod
    def get_sr_nonq_ioc_port_config(cls, ports):
        ioc_pport_cfg, ioc_rport_cfg = {}, {}
        visited_port_key = set()
        for port in ports:
            if "port_full_key" in port and port["port_full_key"] in visited_port_key:
                continue
            # port中没有"appl_name"这个属性，说明port关联的runnable没有映射到某task上，这是不允许的
            if "appl_name" not in port or "task" not in port or "CoreId" not in port["task"]:
                continue
            if ("port_interface_type" not in port) or port["port_interface_type"] != "sr" or port["is_queued"]:
                continue
            if port["m_to_n"] == "0":
                continue
            if not port["has_prport"] and port["m_to_n"] == "mn":
                continue

            all_non_q_participant_ports = port["sr_port_group"]
            visited_port_key.update(port["port_full_key"] for port in all_non_q_participant_ports)

            # check if inter osa
            core_id = port["task"]["CoreId"]
            has_inter_core = False
            isValidConfig = True
            for curr_port in all_non_q_participant_ports:
                if port == curr_port:
                    continue
                if "task" not in curr_port or "CoreId" not in curr_port["task"]:
                    isValidConfig = False
                    break
                if core_id != curr_port["task"]["CoreId"]:
                    has_inter_core = True
                    break
            if not isValidConfig:
                continue

            # optimization based on datatype
            # exclud N:1 scen: as N:1 operations are NOT atomic
            datatype = port["arg"]["datatype"]
            is_data_type_free_from_lock = (
                datatype["native_category"] == "NUMERICAL" and datatype["basetype"] in AutosarUtils.AUTOMIC_DATATYPES
            )
            # currently, task does not support func safe resolving
            if (
                port["m_to_n"] != "n1" or (port["m_to_n"] == "n1" """and port["single_rec_buff_for_n1"]""")
            ) and is_data_type_free_from_lock:
                continue
            if has_inter_core:
                for curr_port in all_non_q_participant_ports:
                    if curr_port["is_p_port"]:
                        ioc_pport_cfg[f"{curr_port['swc_port_var']}"] = curr_port
                    else:
                        ioc_rport_cfg[f"{curr_port['swc_port_var']}"] = curr_port
                continue
        return ioc_pport_cfg, ioc_rport_cfg

    @classmethod
    def __parse_sr_11_1n_non_q_ioc_info(self, port, ioc_rport_cfg, os_spinlock_cfg):
        if port["m_to_n"] == "0":
            return
        datatype = port["data_element_ref"].split("/").pop()
        if datatype in AutosarUtils.AUTOMIC_DATATYPES:
            return
        if port["m_to_n"] == "11":
            opposite_port = port["conn_asw_ports"][0]
            key = opposite_port["swc_port_var"]
            if key not in ioc_rport_cfg:
                return
            receiver_appl_name = ioc_rport_cfg[key]["appl_name"]
            sender_appl_name = port["appl_name"]
            spinlock_id = f"OS_SPINLOCK_Rte_{port['swc_port_var']}_ID"
            spinlock_method = "LOCK_CAT2_INTERRUPTS"
            os_spinlock_cfg[spinlock_id] = [sender_appl_name, receiver_appl_name, spinlock_method]
        elif port["m_to_n"] == "1n":
            sender_appl_name = port["appl_name"]
            appl_name_set = {sender_appl_name}
            spinlock_method = "LOCK_CAT2_INTERRUPTS"
            for rport in port["conn_asw_ports"]:
                key = rport["swc_port_var"]
                if key not in ioc_rport_cfg:
                    return
                receiver_appl_name = ioc_rport_cfg[key]["appl_name"]
                appl_name_set.add(receiver_appl_name)
            spinlock_id = f"OS_SPINLOCK_Rte_{port['swc_port_var']}_ID"
            os_spinlock_cfg[spinlock_id] = list(sorted(appl_name_set))
            os_spinlock_cfg[spinlock_id].append(spinlock_method)

    @classmethod
    def __parse_sr_n_to_1_non_q_ioc_info(self, port, ioc_pport_cfg, os_spinlock_cfg):
        if port["m_to_n"] == "0":
            return
        datatype = port["data_element_ref"].split("/").pop()
        if datatype in AutosarUtils.AUTOMIC_DATATYPES:
            return
        if port["m_to_n"] == "n1":
            receiver_appl_name = port["appl_name"]
            appl_name_set = {receiver_appl_name}
            spinlock_method = "LOCK_CAT2_INTERRUPTS"
            for pport in port["conn_asw_ports"]:
                key = pport["swc_port_var"]
                if key not in ioc_pport_cfg:
                    continue
                sender_appl_name = ioc_pport_cfg[key]["appl_name"]
                appl_name_set.add(sender_appl_name)
            spinlock_id = f"OS_SPINLOCK_Rte_{port['swc_port_var']}_ID"
            os_spinlock_cfg[spinlock_id] = list(sorted(appl_name_set))
            os_spinlock_cfg[spinlock_id].append(spinlock_method)

    # NOTE:有测试用例调用
    @classmethod
    def get_sr_nonqueue_spinlock_info(cls, ioc_pport_cfg, ioc_rport_cfg):
        os_spinlock_cfg = {}
        # 1:1 and 1:N
        for port in ioc_pport_cfg.values():
            # if port["type"] in ["Server", "Sync Client", "Async Client"]:
            if port["type"] not in ["Explicit Sender", "Implicit Sender"]:
                continue
            cls.__parse_sr_11_1n_non_q_ioc_info(port, ioc_rport_cfg, os_spinlock_cfg)
        # N:1
        for port in ioc_rport_cfg.values():
            # if port["type"] in ["Server", "Sync Client", "Async Client"]:
            if port["type"] not in ["Explicit Receiver", "Implicit Receiver"]:
                continue
            cls.__parse_sr_n_to_1_non_q_ioc_info(port, ioc_pport_cfg, os_spinlock_cfg)
        return os_spinlock_cfg


    @classmethod
    def get_rte_schedule_table_info(cls, r_port):
        
        def get_entry_point_dict(timeout_tick):
            evt = r_port["schedule_table"].get("trigger_event", None)
            if not evt:
                return []
            else:
                return [(timeout_tick, {"task_name": r_port["schedule_table"].get("trigger_task", None), "event_name": evt,})]

        timeout_tick = ScheduleTableManager.convert_milliseconds_to_tick(r_port["schedule_table"]["counter"]["OsSecondsPerTick"], r_port["schedule_table"]["timeout"])
        return {
            "name": r_port["schedule_table"]["name"],
            "repeating": False,
            "counter_ref": r_port["schedule_table"]["counter"]["path"],
            "code_gen": False,
            "duration": timeout_tick + 1,
            "step_dict": {},
            "expiry_point_dict": {timeout_tick: get_entry_point_dict(timeout_tick)},
            "osa": r_port["osapplication"],
        }


    @classmethod
    def get_all_spinlocks_cs(cls, pport, spinlock_cfgs):
        if not pport["connected_ports"]:
            return

        core_id_set = {pport["core_id"]} if pport["core_id"] is not None else {}
        appl_name_set = {pport["osapplication"]} if pport["osapplication"] else {}
        for connected_rport in pport["connected_ports"]["ports"]:
            try:
                if connected_rport["osapplication"] and connected_rport["core_id"] is not None:
                    core_id_set.add(connected_rport["core_id"])
                    appl_name_set.add(connected_rport["osapplication"])
            except Exception:
                continue

        if len(core_id_set) < 2:
            return
        port_op = pport["name"].split("/")[-1]
        spinlock_method = "LOCK_CAT2_INTERRUPTS"
        spinlock_id = f'OS_SPINLOCK_Rte_{pport["component"]}_{port_op}_ID'
        spinlock_cfgs[spinlock_id] = list(sorted(appl_name_set))
        spinlock_cfgs[spinlock_id].append(spinlock_method)

    @classmethod
    def get_all_spinlocks_sr_nonq_p_port(cls, port, spinlock_cfgs):
        if port["lock"] == "SPINLOCK" and port["spinlock_cfg"]["lock_id"] not in spinlock_cfgs:
            spinlock_cfgs[port["spinlock_cfg"]["lock_id"]] = [osa for osa in port["spinlock_cfg"]["access_osa"]]
            spinlock_cfgs[port["spinlock_cfg"]["lock_id"]].append(port["spinlock_cfg"]["lock_metohd"])
        if "data_mapping_spinlock_cfg" in port and port["data_mapping_spinlock_cfg"]["lock_id"] not in spinlock_cfgs:
            spinlock_cfgs[port["data_mapping_spinlock_cfg"]["lock_id"]] = [
                osa for osa in port["data_mapping_spinlock_cfg"]["access_osa"]
            ]
            spinlock_cfgs[port["data_mapping_spinlock_cfg"]["lock_id"]].append(
                port["data_mapping_spinlock_cfg"]["lock_metohd"]
            )

    @classmethod
    def get_all_spinlocks_sr_nonq_r_port(cls, port, spinlock_cfgs):
        if port["lock"] == "SPINLOCK" and port["spinlock_cfg"]["lock_id"] not in spinlock_cfgs:
            spinlock_cfgs[port["spinlock_cfg"]["lock_id"]] = [osa for osa in port["spinlock_cfg"]["access_osa"]]
            spinlock_cfgs[port["spinlock_cfg"]["lock_id"]].append(port["spinlock_cfg"]["lock_metohd"])
        if "data_mapping_spinlock_cfg" in port and port["data_mapping_spinlock_cfg"]["lock_id"] not in spinlock_cfgs:
            spinlock_cfgs[port["data_mapping_spinlock_cfg"]["lock_id"]] = [
                osa for osa in port["data_mapping_spinlock_cfg"]["access_osa"]
            ]
            spinlock_cfgs[port["data_mapping_spinlock_cfg"]["lock_id"]].append(
                port["data_mapping_spinlock_cfg"]["lock_metohd"]
            )

    @classmethod
    def get_all_spinlocks_sr_queue(cls, r_port, spinlock_cfgs):
        if r_port["q_lock"] != "SPINLOCK":
            return
        if r_port["q_spinlock_cfg"]["lock_id"] in spinlock_cfgs:
            return
        spinlock_cfgs[r_port["q_spinlock_cfg"]["lock_id"]] = [osa for osa in r_port["q_spinlock_cfg"]["access_osa"]]
        spinlock_cfgs[r_port["q_spinlock_cfg"]["lock_id"]].append(r_port["q_spinlock_cfg"]["lock_metohd"])
