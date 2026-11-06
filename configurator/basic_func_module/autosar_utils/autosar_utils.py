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
import copy
from enum import Enum
from collections import deque
from autosar44 import autosar44
from basic_func_module.autosar_utils import utils
from basic_func_module.base_logger import logger
from func_module.health_monitor.perf_record import log_function_stats


class MemmapCategory(Enum):
    OSA_PRIVATE = "OSA_PRIVATE"
    OSA_SHARED = "OSA_SHARED"
    CORE_SHARED = "SHARED_CORE"
    GLOBAL = "GLOBAL"

    def __lt__(self, other):
        if not isinstance(other, MemmapCategory):
            return NotImplemented
        return self.value < other.value

    def __eq__(self, other):
        return hasattr(self, "value") and hasattr(other, "value") and self.value == other.value

    def __hash__(self):
        return hash(self.value)


class VariableInitCategory(Enum):
    NO_INIT = "BSS"
    ZERO_INIT = "BSS"
    INIT = "DATA"  # non-zero init values


def topological_sort(dependencies):

    def visit(node, visited, stack):
        visited.add(node)
        if node in dependencies:
            for dependency in dependencies[node]:
                if dependency not in visited:
                    visit(dependency, visited, stack)
        stack.append(node)

    visited, stack = set(), deque()
    for node in sorted(dependencies):
        if node not in visited:
            visit(node, visited, stack)

    return list(stack)


class AutosarUtils:
    __rte_codegen_dict = {}
    __last_task_mapping_info = {}
    __last_data_mapping_info = {}

    is_debug = False

    cal_prm_rport_type = "CAL_PRM_RPORT"

    @classmethod
    def get_last_rte_codegen_dict(cls):
        return cls.__rte_codegen_dict

    @classmethod
    def get_last_task_mapping_info(cls):
        return cls.__last_task_mapping_info

    @classmethod
    def get_last_data_mapping_info(cls):
        return cls.__last_data_mapping_info

    @classmethod
    @log_function_stats(["RTE", "RTE信息推理"])
    def get_rte_codegen_dict(
        cls, asw_autosar_dict, data_mapping_info, task_mappings_info, com_cfg_dict, cfg_dict, parse_new_dict=True
    ):
        if (parse_new_dict) or (not cls.__rte_codegen_dict):
            if ("asw" not in asw_autosar_dict) or (asw_autosar_dict["asw"] is None):
                return {}
            cls.__to_asw_codegen_dict(asw_autosar_dict, data_mapping_info, task_mappings_info, com_cfg_dict, cfg_dict)
            cls.__last_task_mapping_info = task_mappings_info
        else:
            cfg_dict["rte"]["data_mapping_config"] = cls.__last_data_mapping_info
        return cls.__rte_codegen_dict

    NATIVE_DATATYPES = [
        "boolean",
        "float32",
        "float64",
        "uint8",
        "uint8_least",
        "sint8",
        "sint8_least",
        "uint16",
        "uint16_least",
        "sint16",
        "sint16_least",
        "uint32",
        "uint32_least",
        "sint32",
        "sint32_least",
        "uint64",
        "uint64_least",
        "sint64",
        "sint64_least",
        "void",
    ]
    AUTOMIC_DATATYPES = [
        "boolean",
        "float32",
        "uint8",
        "uint8_least",
        "sint8",
        "sint8_least",
        "uint16",
        "uint16_least",
        "sint16",
        "sint16_least",
        "uint32",
        "uint32_least",
        "sint32",
        "sint32_least",
    ]

    # NOTICE: compiler dependent
    NATIVE_DATATYPES_SIZE = {
        # short name
        "boolean": 1,
        "bool": 1,
        "uint8": 1,
        "sint8": 1,
        "uint16": 2,
        "sint16": 2,
        "uint32": 4,
        "sint32": 4,
        "uint64": 8,
        "sint64": 8,
        "float32": 4,
        "float64": 8,
        "uint8_least": 4,
        "sint8_least": 4,
        "uint16_least": 4,
        "sint16_least": 4,
        "uint32_least": 4,
        "sint32_least": 4,
        # native c
        "unsigned char": 1,
        "signed char": 1,
        "unsigned short": 2,
        "signed short": 2,
        "unsigned int": 4,
        "signed int": 4,
        "float": 4,
        "unsigned long long": 8,
        "signed long long": 8,
        "double": 8,
    }

    EVENT_TYPE = {
        "INIT-EVENT": "InitEvent",
        "TIMING-EVENT": "TimingEvent",
        "BACKGROUND-EVENT": "BackgroundEvent",
        "DATA-RECEIVED-EVENT": "DataReceivedEvent",
        "OPERATION-INVOKED-EVENT": "OperationInvokedEvent",
        "SWC-MODE-SWITCH-EVENT": "SwcModeSwitchEvent",
        "MODE-SWITCHED-ACK-EVENT": "ModeSwitchedAckEvent",
        "DATA-SEND-COMPLETED-EVENT": "DataSendCompletedEvent",
        "DATA-WRITE-COMPLETED-EVENT": "DataWriteCompletedEvent",
        "ASYNCHRONOUS-SERVER-CALL-RETURNS-EVENT": "AsynchronousServerCallReturnsEvent",
        "INTERNAL-TRIGGER-OCCURRED-EVENT": "InternalTriggerOccurredEvent",
        "EXTERNAL-TRIGGER-OCCURRED-EVENT": "ExternalTriggerOccurredEvent",
    }

    RUNNABLE_EVENT_TYPE = {
        "DATA-RECEIVED-EVENT": "DataReceivedEvent",
        "OPERATION-INVOKED-EVENT": "OperationInvokedEvent",
        "DATA-SEND-COMPLETED-EVENT": "DataSendCompletedEvent",
        "DATA-WRITE-COMPLETED-EVENT": "DataWriteCompletedEvent",
        "INTERNAL-TRIGGER-OCCURRED-EVENT": "InternalTriggerOccurredEvent",
        "EXTERNAL-TRIGGER-OCCURRED-EVENT": "ExternalTriggerOccurredEvent",
    }

    SUPPORT_APPL_COMPONENT_TYPE = [
        "APPLICATION-SW-COMPONENT-TYPE",
        "ECU-ABSTRACTION-SW-COMPONENT-TYPE",
        "COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE",
        "NV-BLOCK-SW-COMPONENT-TYPE",
        "PARAMETER-SW-COMPONENT-TYPE",
        "SENSOR-ACTUATOR-SW-COMPONENT-TYPE",
        "SERVICE-PROXY-SW-COMPONENT-TYPE",
    ]

    GEN_FILE_APPL_COMPONENT_TYPE = [
        "APPLICATION-SW-COMPONENT-TYPE",
        "ECU-ABSTRACTION-SW-COMPONENT-TYPE",
        "COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE",
        "SENSOR-ACTUATOR-SW-COMPONENT-TYPE",
        "SERVICE-PROXY-SW-COMPONENT-TYPE",
    ]

    # "NV-BLOCK-SW-COMPONENT-TYPE", "PARAMETER-SW-COMPONENT-TYPE"
    # 这两类不生成rte_swc_memmap.h/rte_swc.h/rte_swc_type.h/swc.c
    NO_GEN_FILE_APPL_COMPONENT_TYPE = list(set(SUPPORT_APPL_COMPONENT_TYPE) - set(GEN_FILE_APPL_COMPONENT_TYPE))

    SUPPORT_SERVICE_COMPONENT_TYPE = ["SERVICE-SW-COMPONENT-TYPE"]

    # 所有的component type
    SUPPORT_COMPONENT_TYPE = []
    SUPPORT_COMPONENT_TYPE.extend(SUPPORT_APPL_COMPONENT_TYPE)
    SUPPORT_COMPONENT_TYPE.extend(SUPPORT_SERVICE_COMPONENT_TYPE)

    GEN_FILE_COMPONENT_TYPE = []
    GEN_FILE_COMPONENT_TYPE.extend(GEN_FILE_APPL_COMPONENT_TYPE)
    GEN_FILE_COMPONENT_TYPE.extend(SUPPORT_SERVICE_COMPONENT_TYPE)

    datatype_mapping_sets = {}
    adt_mappings = {}
    idts = {}
    idts_dependency = {}
    consts = {}
    constraints = {}
    sw_component_types = []
    task_mappings = {}
    asw_events = {}
    runnable_tasks = {}
    runnable_events = {}
    port_events = {}
    port_data_element_access = {}
    port_operation_access = {}
    operation_access = {}
    run_operation_map = {}
    component_osapplications = {}
    mapped_schedulable_entitys = {}
    component_core_id = {}
    pport_api_options = {}
    # TODO: remove
    p_port_connection = {}
    r_port_connection = {}
    mode_groups = {}
    datatype_path_to_idt_mapping = {}
    const_to_datatype_mapping = {}
    port_prototypes = {}
    sr_p_port_path_to_asw_port_dict = {}
    sr_r_port_path_to_asw_port_dict = {}
    mode_r_port_path_to_asw_port_dict = {}
    p_connections = {}
    r_connections = {}
    is_ea_opt_enabled = False
    is_datamapping_opt_tx = False
    is_datamapping_opt_rx_1_1 = False
    is_datamapping_opt_rx_1_n = False
    sr_dm_glob_vars = {}
    server_runnable_connections = {}
    cs_ret_evt_trig_run = {}
    const_init_value = {}
    p_access_comspec_map = {}
    r_access_comspec_map = {}
    r_param_comspec_map = {}
    all_osa = []
    all_osa_set = set()
    rte_sch_tbl = {}
    os_counter = {}
    core_osa_map = {}
    iso_call_func = {}
    iso_call_func_include_header_file = {}

    @classmethod
    def get_os_counter(cls):
        return cls.os_counter

    @classmethod
    def __init_os_counter_cfg(cls, os_cfg):
        cls.os_counter.clear()
        for osa_name, osa_info in os_cfg["OsApplications"].items():
            counter_info = osa_info.get("OsAppCounter", {})
            if not counter_info:
                continue
            cls.os_counter[osa_name] = counter_info

    @classmethod
    def __init_data_mapping_cfg(cls, rte_cfg):
        cls.is_datamapping_opt_tx = (
            bool(rte_cfg)
            and ("RteGeneration" in rte_cfg)
            and ("DataMappingGenerationOptimizationPport" in rte_cfg["RteGeneration"])
            and rte_cfg["RteGeneration"]["DataMappingGenerationOptimizationPport"]
        )
        cls.is_datamapping_opt_rx_1_1 = (
            bool(rte_cfg)
            and ("RteGeneration" in rte_cfg)
            and ("DataMappingGenerationOptimization1To1Rport" in rte_cfg["RteGeneration"])
            and rte_cfg["RteGeneration"]["DataMappingGenerationOptimization1To1Rport"]
        )
        # represent: RX 1 signal -> N ports
        cls.is_datamapping_opt_rx_1_n = (
            bool(rte_cfg)
            and ("RteGeneration" in rte_cfg)
            and ("DataMappingGenerationOptimizationNTo1Rport" in rte_cfg["RteGeneration"])
            and rte_cfg["RteGeneration"]["DataMappingGenerationOptimizationNTo1Rport"]
        )
        cls.signal_compu_method_enabled = rte_cfg.get("RteGeneration", {}).get("RteSystemSignalCompuMethodEna", False)
        cls.sr_dm_glob_vars = {
            "individual": {
                "buff": {},
                "buff_last": {},
                "status": {},
            },
            "complex": {
                "flag_is_proxy_sending": {},
                "flag_is_updated_tx": {},
                "flag_is_updated_rx": {},
                "flag_is_received": {},
                "flag_is_timeout": {},
            },
            "macro": {
                "compu_method": {},
            },
        }

    @classmethod
    def __init_iso_call_func(cls, isolate_cfg):
        cls.iso_call_func.clear()
        cls.iso_call_func_include_header_file.clear()
        if (not isolate_cfg) or (not isolate_cfg["iso_func"]):
            return
        for func_name, func_info in isolate_cfg["iso_func"].items():
            osa_name = func_info["osa"]
            if osa_name not in cls.iso_call_func:
                cls.iso_call_func[osa_name] = {}
            cls.iso_call_func[osa_name][func_name] = func_info

    @classmethod
    def __init_global_vars_before_code_gen(cls, rte_cfg, isolate_cfg, os_cfg):
        cls.__rte_codegen_dict.clear()
        cls.sr_p_port_path_to_asw_port_dict.clear()
        cls.sr_r_port_path_to_asw_port_dict.clear()
        cls.mode_r_port_path_to_asw_port_dict.clear()
        cls.const_to_datatype_mapping.clear()
        cls.datatype_path_to_idt_mapping.clear()
        cls.run_operation_map.clear()
        cls.cs_ret_evt_trig_run.clear()
        cls.const_init_value.clear()
        cls.p_access_comspec_map.clear()
        cls.r_access_comspec_map.clear()
        cls.r_param_comspec_map.clear()
        cls.all_osa.clear()
        cls.all_osa_set.clear()
        cls.core_osa_map.clear()
        cls.__init_iso_call_func(isolate_cfg)
        cls.is_ea_opt_enabled = bool(rte_cfg) and rte_cfg.get("RteGeneration", {}).get("RteEaOptimization", False)
        cls.rte_dlog_enabled = bool(rte_cfg) and rte_cfg.get("RteGeneration", {}).get("RteDevErrorDetect", False)
        cls.__init_data_mapping_cfg(rte_cfg)
        cls.rte_sch_tbl.clear()
        cls.__init_os_counter_cfg(os_cfg)

    @classmethod
    def __get_memmap_category(cls, writers, readers):
        w_osas = set()
        r_osas = set()

        core_ids = set()
        for wr in writers:
            w_osas.add(wr["osa"] if "osa" in wr else wr["osapplication"])
            core_ids.add(wr["core_id"])
        for re in readers:
            r_osas.add(re["osa"] if "osa" in re else re["osapplication"])
            core_ids.add(re["core_id"])
        if len(w_osas) == 1:
            w_osas.update(r_osas)
            if len(w_osas) == 1:
                return MemmapCategory.OSA_PRIVATE
            else:
                return MemmapCategory.OSA_SHARED
        else:
            if len(core_ids) == 1:
                return MemmapCategory.CORE_SHARED
            else:
                return MemmapCategory.GLOBAL

    @classmethod
    def __pack_osa_info_from_ecuc_partition(cls):
        ecuc_partition_osa = {}
        swc_osa_from_ep = {}
        swc_core_id_from_ep = {}
        swc_ecuc_partition = {}
        for app, app_value in cls.cfg_dict.get("rte", {}).get("os_cfg", {}).get("OsApplications", {}).items():
            core_id = app_value["CoreId"]
            EcucPartition = app_value.get("EcucPartition", None)
            if EcucPartition:
                if EcucPartition not in ecuc_partition_osa:
                    ecuc_partition_osa.update({EcucPartition: set()})
                ecuc_partition_osa[EcucPartition].add(app)
            for swc in app_value.get("EcucPartitionSwcInstRef", []):
                if swc not in swc_osa_from_ep:
                    swc_osa_from_ep.update({swc: set()})
                swc_osa_from_ep[swc].add(app)

                if swc not in swc_core_id_from_ep:
                    swc_core_id_from_ep.update({swc: set()})
                swc_core_id_from_ep[swc].add(core_id)

                if swc not in swc_ecuc_partition:
                    swc_ecuc_partition.update({swc: set()})
                swc_ecuc_partition[swc].add(app_value["EcucPartition"])
        return ecuc_partition_osa, swc_osa_from_ep, swc_core_id_from_ep, swc_ecuc_partition

    @classmethod
    def __pack_sw_component_type_osapplication(cls):
        component_osapplication = {}
        mapped_schedulable_entity_set = set()
        component_core_id = {}
        osa_set = set()
        core_osa_set_map = {}
        for osapplication in cls.task_mappings.values():
            try:
                core_id = int(osapplication.get("core_id", None))
                osa = osapplication.get("application", None)
            except Exception:
                logger.error(
                    f"OsApplication <{osapplication}>'s core id <{osapplication.get('core_id', None)}>"
                    " can not be resolved to a valid integer!"
                )
                continue
            if (core_id is None) or (not osa):
                continue

            osa_set.add(osa)
            if core_id not in core_osa_set_map:
                core_osa_set_map[core_id] = set()
            core_osa_set_map[core_id].add(osa)
            for schedule_entity in osapplication["schedulable_entity_info_list"]:
                mapped_schedulable_entity_set.add(schedule_entity["name"])
                if schedule_entity["component"] not in component_osapplication:
                    component_osapplication.update({schedule_entity["component"]: osapplication["application"]})
                if schedule_entity["component"] not in component_core_id:
                    component_core_id.update({schedule_entity["component"]: core_id})
        cls.all_osa = list(sorted(osa_set))
        cls.all_osa_set = set(cls.all_osa)
        for core_id, osas in core_osa_set_map.items():
            cls.core_osa_map[core_id] = list(sorted(osas))
        return component_osapplication, mapped_schedulable_entity_set, component_core_id

    @classmethod
    def __pack_all_sw_component_type(cls, ar_asw):
        sw_component_types = []
        for comp_type in cls.SUPPORT_COMPONENT_TYPE:
            sw_component_types += ar_asw.find_nodes(comp_type)

        return sorted(sw_component_types, key=lambda ar_swc: utils.get_short_name(ar_swc))

    @classmethod
    def get_ecuc_partition_info(cls):
        ecuc_partition_osa, swc_osa_from_ep, swc_core_id_from_ep, swc_ecuc_partition = (
            cls.__pack_osa_info_from_ecuc_partition()
        )
        return ecuc_partition_osa, swc_osa_from_ep, swc_core_id_from_ep, swc_ecuc_partition

    @classmethod
    def get_all_sw_component_prototypes(cls, ar_asw):
        # 获取sw-component-type和sw-component-prototype的对应关系
        # 当前只支持实例化一个swc
        all_swc_prototypes = {}
        for component in ar_asw.find_nodes("COMPONENTS"):
            for swc_prototye in component.SW_COMPONENT_PROTOTYPE:
                swc_name = utils.get_valueOf(swc_prototye.SHORT_NAME)  # 实例化的swc名字
                base_swc_name = utils.get_valueOf(swc_prototye.TYPE_TREF).split("/")[-1]
                if base_swc_name not in all_swc_prototypes:
                    all_swc_prototypes.update({base_swc_name: []})
                    all_swc_prototypes[base_swc_name].append(swc_name)
                else:
                    all_swc_prototypes[base_swc_name].append(swc_name)
        return all_swc_prototypes

    @classmethod
    def get_all_appl_component_short_names(cls, ar_asw):
        if not ar_asw:
            return []
        name_list = set()
        sw_component_types = []
        # 只生成GEN_FILE_APPL_COMPONENT_TYPE这部分SWC列表
        for comp_type in cls.GEN_FILE_APPL_COMPONENT_TYPE:
            sw_component_types += ar_asw.find_nodes(comp_type)

        for swc_t in sw_component_types:
            name_list.add(utils.get_short_name(swc_t))
        return list(name_list)

    @classmethod
    def create_ar_inner_port_iref(
        cls, P_PORT_IN_COMPOSITION_INSTANCE_REF=None, R_PORT_IN_COMPOSITION_INSTANCE_REF=None, parent=None
    ) -> autosar44.INNER_PORT_IREFType:
        inner_port_iref = autosar44.INNER_PORT_IREFType(
            P_PORT_IN_COMPOSITION_INSTANCE_REF=P_PORT_IN_COMPOSITION_INSTANCE_REF,
            R_PORT_IN_COMPOSITION_INSTANCE_REF=R_PORT_IN_COMPOSITION_INSTANCE_REF,
        )
        inner_port_iref.set_parent(parent)
        return inner_port_iref

    @classmethod
    def create_ar_outer_port_ref(cls, dest=None, value=None, parent=None):
        outer_port_ref = autosar44.OUTER_PORT_REFType(DEST=dest, valueOf_=value)
        outer_port_ref.set_parent(parent)
        return outer_port_ref

    @classmethod
    def create_ar_delegation_sw_connector(
        cls,
        short_name: str,
        target_port_dest=None,
        context_component_ref_value=None,
        target_port_ref_value=None,
        outer_port_ref_value=None,
        parent=None,
    ) -> autosar44.DELEGATION_SW_CONNECTOR:
        short_name_obj = autosar44.IDENTIFIER(valueOf_=short_name)
        context_component_ref = autosar44.CONTEXT_COMPONENT_REFType(
            DEST="SW-COMPONENT-PROTOTYPE", valueOf_=context_component_ref_value
        )
        outer_port_ref = autosar44.OUTER_PORT_REFType(DEST=target_port_dest, valueOf_=outer_port_ref_value)
        if target_port_dest == "P-PORT-PROTOTYPE":
            target_port_ref = autosar44.TARGET_P_PORT_REFType(DEST=target_port_dest, valueOf_=target_port_ref_value)
            port_in_composition_instance_ref = autosar44.P_PORT_IN_COMPOSITION_INSTANCE_REF(
                CONTEXT_COMPONENT_REF=context_component_ref, TARGET_P_PORT_REF=target_port_ref
            )
            inner_port_iref = autosar44.INNER_PORT_IREFType(
                P_PORT_IN_COMPOSITION_INSTANCE_REF=port_in_composition_instance_ref
            )
        elif target_port_dest == "R-PORT-PROTOTYPE":
            target_port_ref = autosar44.TARGET_R_PORT_REFType(DEST=target_port_dest, valueOf_=target_port_ref_value)
            port_in_composition_instance_ref = autosar44.R_PORT_IN_COMPOSITION_INSTANCE_REF(
                CONTEXT_COMPONENT_REF=context_component_ref, TARGET_R_PORT_REF=target_port_ref
            )
            inner_port_iref = autosar44.INNER_PORT_IREFType(
                R_PORT_IN_COMPOSITION_INSTANCE_REF=port_in_composition_instance_ref
            )
        else:
            return None
        delegation_sw_connector = autosar44.DELEGATION_SW_CONNECTOR(
            SHORT_NAME=short_name_obj, INNER_PORT_IREF=inner_port_iref, OUTER_PORT_REF=outer_port_ref
        )

        delegation_sw_connector.set_parent(parent)
        outer_port_ref.set_parent(delegation_sw_connector)
        inner_port_iref.set_parent(delegation_sw_connector)
        port_in_composition_instance_ref.set_parent(inner_port_iref)
        context_component_ref.set_parent(port_in_composition_instance_ref)
        target_port_ref.set_parent(port_in_composition_instance_ref)

        return delegation_sw_connector

    @classmethod
    def parse_operation_content(cls, argument_data_prototype):
        operation_content_dict = {}
        operation_content_dict.update({"name": utils.get_short_name(argument_data_prototype)})
        operation_content_dict.update({"type": utils.get_type_tref(argument_data_prototype).split("/")[-1]})
        operation_content_dict.update({"direction": utils.get_direction(argument_data_prototype)})
        return operation_content_dict

    @classmethod
    def parse_value(cls, port_prototype, client_server_operation, swc_internal_behaviors):
        for sw_internal_behavior in swc_internal_behaviors:
            if hasattr(sw_internal_behavior, "PORT_API_OPTIONS") and sw_internal_behavior.PORT_API_OPTIONS is not None:
                port_api_options = sw_internal_behavior.PORT_API_OPTIONS.PORT_API_OPTION
                for port_api_option in port_api_options:
                    if utils.get_short_name(port_prototype) == utils.get_port_ref(port_api_option).split("/")[-1]:
                        port_defined_argument_values = port_api_option.PORT_ARG_VALUES.PORT_DEFINED_ARGUMENT_VALUE
                        for port_defined_argument_value in port_defined_argument_values:
                            value = int(
                                utils.get_value(port_defined_argument_value.VALUE.NUMERICAL_VALUE_SPECIFICATION)
                            )
                            return value

    @classmethod
    def parse_server_operation_content(cls, port_prototype, client_server_operation, swc_internal_behaviors):
        server_operation_content_dict = {}
        server_operation_content_dict.update({"name": utils.get_short_name(client_server_operation)})
        if (
            hasattr(client_server_operation.ARGUMENTS, "ARGUMENT_DATA_PROTOTYPE")
            and client_server_operation.ARGUMENTS.ARGUMENT_DATA_PROTOTYPE != []
        ):
            argument_data_prototypes = client_server_operation.ARGUMENTS.ARGUMENT_DATA_PROTOTYPE
            for argument_data_prototype in argument_data_prototypes:
                server_operation_content_dict.update(
                    {"type": utils.get_type_tref(argument_data_prototype).split("/")[-1]}
                )
                server_operation_content_dict.update({"direction": utils.get_direction(argument_data_prototype)})
                server_operation_content_dict["value"] = cls.parse_value(
                    port_prototype, client_server_operation, swc_internal_behaviors
                )
        return server_operation_content_dict

    @classmethod
    def parse_period_trigger_event(cls, runnable_entity, swc_internal_behavior):
        if not hasattr(swc_internal_behavior, "EVENTS"):
            return None, None
        period = None
        trigger_event = None
        events = []
        for key in cls.EVENT_TYPE.keys():
            events.extend(getattr(swc_internal_behavior.EVENTS, key.replace("-", "_")))

        for event in events:
            runnable_short_name = utils.get_short_name(runnable_entity)
            event_ref: str = utils.get_start_on_event_ref(event)
            if event_ref is None:
                continue
            if event_ref.endswith(runnable_short_name):
                event_tag = event.get_tag()
                event_type = cls.EVENT_TYPE.get(event_tag)
                if not event_type:
                    logger.debug(f"Unsupported Event: {event_tag}")
                    continue
                if event_type == "TimingEvent":
                    period = int(float(utils.get_period(event)) * 1000)
                trigger_event = event_type
        return period, trigger_event

    @classmethod
    def server_call_points(cls, server_call_points):
        server_call_points_dict = {}
        for server_call_point in server_call_points:
            operation_iref = server_call_point.OPERATION_IREF
            server_call_points_dict[utils.get_short_name(server_call_point)] = {
                "CONTEXT-R-PORT-REF": utils.get_context_r_port_ref(operation_iref),
                "TARGET-REQUIRED-OPERATION-REF": operation_iref.TARGET_REQUIRED_OPERATION_REF.valueOf_,
            }
        return server_call_points_dict

    @classmethod
    def parse_exclusive_area(cls):
        area_dict = {}
        area_dict["name"] = None
        area_dict["implementation"] = None
        area_dict["access_mode"] = None
        return area_dict

    @classmethod
    def __get_typesize_byte_from_ar_path(cls, type_ref):
        if (
            type_ref in cls.datatype_path_to_idt_mapping
            and "idt" in cls.datatype_path_to_idt_mapping[type_ref]
            and "typesize_byte_for_struct_align" in cls.datatype_path_to_idt_mapping[type_ref]["idt"]
        ):
            return cls.datatype_path_to_idt_mapping[type_ref]["idt"]["typesize_byte_for_struct_align"]
        else:
            return 8

    @classmethod
    def __parse_cs_port_interface_info(cls, rport_prototype, operation_path):
        operation = rport_prototype.find(operation_path)
        if not operation:
            return None
        possible_error_refs = getattr(operation, "POSSIBLE_ERROR_REFS", None)
        # 次数据结构为application error使用
        if not possible_error_refs:
            return None
        if len(operation_path.split("/")) < 2:
            # logger.debug(f"invalid cs operation path {operation_path}")
            return None
        port_interface_name = operation_path.split("/")[-2]
        # {application_error_name:application_error_code}
        application_error_dict = {}
        for possible_error_ref in getattr(possible_error_refs, "POSSIBLE_ERROR_REF", []):
            possible_error_path = utils.get_valueOf(possible_error_ref)
            possible_error = operation.find(possible_error_path)
            short_name = utils.get_valueOf(possible_error.SHORT_NAME)
            error_code = utils.get_valueOf(possible_error.ERROR_CODE)
            application_error_dict.update({short_name: error_code})
        sorted_application_error_dict = {k: application_error_dict[k] for k in sorted(application_error_dict)}
        port_interface_info = {port_interface_name: sorted_application_error_dict}
        return port_interface_info

    @classmethod
    def __parse_operation(cls, ar, operation_path, port_ref=None):
        args = {}
        return_type = "void"
        operation = ar.find(operation_path)
        if not operation or isinstance(operation, autosar44.VARIABLE_DATA_PROTOTYPE):
            return args, return_type, args
        if (
            hasattr(operation, "POSSIBLE_ERROR_REFS")
            and operation.POSSIBLE_ERROR_REFS
            and hasattr(operation.POSSIBLE_ERROR_REFS, "POSSIBLE_ERROR_REF")
            and operation.POSSIBLE_ERROR_REFS.POSSIBLE_ERROR_REF
        ):
            return_type = "Std_ReturnType"
        if operation.ARGUMENTS is None:
            return args, return_type, cls.get_sorted_args(args)
        arguments = operation.ARGUMENTS.ARGUMENT_DATA_PROTOTYPE
        for argument in arguments:
            argument_name = argument.SHORT_NAME.valueOf_
            type_ref = argument.TYPE_TREF.valueOf_
            argument_dict = {
                argument_name: {
                    "name": argument_name,
                    "type": cls.__parser_idt(argument, type_ref)[0],
                    "direction": argument.DIRECTION.valueOf_,
                    "category": cls.__parser_idt(argument, type_ref)[1],
                    "typesize_byte_for_struct_align": cls.__get_typesize_byte_from_ar_path(type_ref),
                    "base_type": cls.get_arguement_base_type(
                        cls.__parser_idt(argument, type_ref)[1], cls.__parser_idt(argument, type_ref)[0]
                    ),
                }
            }
            if argument_dict[argument_name]["type"] == "":
                raise Exception(f"operation {operation_path} arguments {argument_name}  can not find in arxml")
            args.update(argument_dict)
        return args, return_type, cls.get_sorted_args(args)

    @classmethod
    def __parse_operation_for_runnable(cls, ar, operation_path, port_ref=None):
        args = {}
        return_type = "void"
        operation = ar.find(operation_path)
        if not operation or isinstance(operation, autosar44.VARIABLE_DATA_PROTOTYPE):
            return args, return_type, args
        if hasattr(operation, "POSSIBLE_ERROR_REFS") and operation.POSSIBLE_ERROR_REFS:
            # if operation.POSSIBLE_ERROR_REFS is not None:
            return_type = "Std_ReturnType"
        port_define_args = cls.pport_api_options[port_ref] if port_ref in cls.pport_api_options else {}
        args.update(port_define_args)
        if operation.ARGUMENTS is None:
            return args, return_type, cls.get_sorted_args(args)
        arguments = operation.ARGUMENTS.ARGUMENT_DATA_PROTOTYPE
        for argument in arguments:
            argument_name = argument.SHORT_NAME.valueOf_
            type_ref = argument.TYPE_TREF.valueOf_
            argument_dict = {
                argument_name: {
                    "name": argument_name,
                    "type": cls.__parser_idt(argument, type_ref)[0],
                    "direction": argument.DIRECTION.valueOf_,
                    "category": cls.__parser_idt(argument, type_ref)[1],
                    "typesize_byte_for_struct_align": cls.__get_typesize_byte_from_ar_path(type_ref),
                    "base_type": cls.get_arguement_base_type(
                        cls.__parser_idt(argument, type_ref)[1], cls.__parser_idt(argument, type_ref)[0]
                    ),
                }
            }
            if argument_dict[argument_name]["type"] == "":
                raise Exception(f"operation {operation_path} arguments {argument_name}  can not find in arxml")
            args.update(argument_dict)
        return args, return_type, cls.get_sorted_args(args)

    @classmethod
    def get_arguement_base_type(cls, category, type):
        rv = None
        if category == "ARRAY":
            rv = cls.idts[type]["arr_basetype"]
        else:
            # TODO
            pass
        return rv

    @classmethod
    def get_sorted_args(cls, args):
        sorted_args = {8: {}, 4: {}, 2: {}, 1: {}}
        for arg_name, arg_info in args.items():
            typesize = arg_info["typesize_byte_for_struct_align"]
            sorted_args[typesize].update({arg_name: arg_info})
        return sorted_args

    @classmethod
    def __parser_idt(cls, argument, type_ref):
        type_obj = argument.find(type_ref)
        if utils.get_short_name(type_obj) is None:
            return "", ""
        category = cls.get_operation_category(type_obj)
        return utils.get_short_name(type_obj), category

    @classmethod
    def get_operation_category(cls, type_obj):
        category = type_obj.CATEGORY.valueOf_
        if category == "TYPE_REFERENCE":
            if cls.idts[utils.get_short_name(type_obj)]["native_category"] == "NUMERICAL":
                base_type = cls.idts[utils.get_short_name(type_obj)]["basetype"]
                if base_type in cls.NATIVE_DATATYPES:
                    category = base_type
                else:
                    # type ref
                    category = cls.idts[base_type]["basetype"]
            elif cls.idts[utils.get_short_name(type_obj)]["native_category"] in ["ARRAY", "STRUCTURE", "UNION"]:
                category = cls.idts[utils.get_short_name(type_obj)]["native_category"]
            else:
                # TODO
                pass
        elif category == "DATA_REFERENCE":
            category = cls.idts[utils.get_short_name(type_obj)]["native_category"]
        return category

    @classmethod
    def parse_return_trigger(cls, sw_comp, runnable, access_point):
        # 1. 遍历swc下的Event
        # 2. 找到EVENT-SOURCE-REF为给定access_point的ASYNCHRONOUS-SERVER-CALL-RETURNS-EVENT
        # 3. 判断ASYNCHRONOUS-SERVER-CALL-RETURNS-EVENT是否有START-ON-EVENT-REF，有则说明配置了return trigger event
        trigger_info_dict = {"ret_trigger_flag": False, "ret_event": "Fake_event"}
        if access_point is None:
            return trigger_info_dict
        ib_list = getattr(getattr(sw_comp, "INTERNAL_BEHAVIORS", None), "SWC_INTERNAL_BEHAVIOR", [])
        for ib in ib_list:
            asyn_event_list = getattr(getattr(ib, "EVENTS", None), "ASYNCHRONOUS_SERVER_CALL_RETURNS_EVENT", [])
            for asyn_event in asyn_event_list:
                start_on_ref = getattr(asyn_event, "START_ON_EVENT_REF", None)
                event_src_ref = getattr(asyn_event, "EVENT_SOURCE_REF", None)
                if event_src_ref:
                    res_pt = runnable.find(event_src_ref.valueOf_)
                    call_pt_path = res_pt.ASYNCHRONOUS_SERVER_CALL_POINT_REF.valueOf_
                    if call_pt_path == access_point.get_path() and start_on_ref is not None:
                        # trigger_runnable_name = start_on_ref.valueOf_.split("/")[-1]
                        runnable_obj = access_point.find(utils.get_valueOf(start_on_ref))
                        runnable_name = utils.get_short_name(runnable_obj)
                        runnable_symbol = utils.get_runnable_symbol(runnable_obj)
                        trigger_task = cls.runnable_tasks.get(runnable_symbol)
                        if not trigger_task or trigger_task not in cls.task_mappings:
                            continue
                        trigger_event_mask = list(
                            filter(
                                lambda x: x["name"] == runnable_name,
                                cls.task_mappings[trigger_task]["schedulable_entity_info_list"],
                            )
                        )[0]["event_mask"]
                        trigger_info_dict["ret_trigger_flag"] = True
                        trigger_info_dict["ret_event"] = trigger_event_mask
        return trigger_info_dict

    @classmethod
    def __update_cs_port_memmap(cls, rport):
        rv = {
            "mem_flag_client": MemmapCategory.GLOBAL,
            "mem_flag_server": MemmapCategory.GLOBAL,
            "mem_result": MemmapCategory.GLOBAL,
            "mem_arg_in": MemmapCategory.GLOBAL,
            "mem_arg_inout": MemmapCategory.GLOBAL,
            "mem_arg_out": MemmapCategory.GLOBAL,
        }
        con_ports_list = rport["connected_ports"]["ports"]
        mixed_ports_list = [rport] + con_ports_list
        # flag client is all client write，server read (1:1/1:N)
        rv["mem_flag_client"] = cls.__get_memmap_category([rport], con_ports_list)
        # flag server is server write，all client read (1:1/1:N)
        rv["mem_flag_server"] = cls.__get_memmap_category(con_ports_list, [rport])
        # result is server write，all client read（1:1/1:N)
        rv["mem_result"] = cls.__get_memmap_category(con_ports_list, [rport])
        # arg_in is all client write，server read（1:1/1:N)
        rv["mem_arg_in"] = cls.__get_memmap_category([rport], con_ports_list)
        # arg_in is all client write，server write（1:1/1:N)
        rv["mem_arg_inout"] = cls.__get_memmap_category(mixed_ports_list, mixed_ports_list)
        # arg_out is server write，all client read（1:1/1:N)
        rv["mem_arg_out"] = cls.__get_memmap_category(con_ports_list, [rport])
        return rv

    @classmethod
    def __update_cs_enqueue_memmap(cls, pport_dict, connection):
        # client enqueue
        rv = {
            "mem_q": MemmapCategory.GLOBAL,
            "mem_q_tail": MemmapCategory.GLOBAL,
            "mem_q_overflow0": MemmapCategory.GLOBAL,
        }
        con_ports_list = connection["ports"]
        # q is all client write，server read (1:1/1:N)
        rv["mem_q"] = cls.__get_memmap_category(con_ports_list, [pport_dict])
        # q_tail is all client write，server not read（1:1/1:N)
        rv["mem_q_tail"] = cls.__get_memmap_category(con_ports_list, [])
        # q_of0 is all client write，server read（1:1/1:N)
        rv["mem_q_overflow0"] = cls.__get_memmap_category(con_ports_list, [pport_dict])
        return rv

    @classmethod
    def __update_cs_dequeue_memmap(cls, pport_dict, connection):
        # server enqueue
        rv = {
            "mem_q_head": MemmapCategory.GLOBAL,
            "mem_q_overflow1": MemmapCategory.GLOBAL,
            "mem_q_element": MemmapCategory.GLOBAL,
        }
        con_ports_list = connection["ports"]
        mixed_ports_list = [pport_dict] + con_ports_list
        # q_head is server write，all client not read (1:1/1:N)
        rv["mem_q_head"] = MemmapCategory.OSA_PRIVATE
        # q_of1 is server write，all client read（1:1/1:N)
        rv["mem_q_overflow1"] = cls.__get_memmap_category([pport_dict], con_ports_list)
        # q_element is server write, all client write（1:1/1:N)
        rv["mem_q_element"] = cls.__get_memmap_category(mixed_ports_list, mixed_ports_list)
        return rv

    @classmethod
    def __update_ms_port_memmap(cls, pport):
        rv = {
            "mem_q": MemmapCategory.GLOBAL,
            "mem_tail": MemmapCategory.GLOBAL,
            "mem_head": MemmapCategory.GLOBAL,
            "mem_mode_machine": MemmapCategory.GLOBAL,
            "mem_ack_flags": MemmapCategory.GLOBAL,
            "mem_mode_dis_trig": MemmapCategory.GLOBAL,
        }
        con_ports_list = pport["conn_asw_ports"]
        mixed_ports_list = [pport] + con_ports_list
        # queue is mode manager write，mode user read (1:1/1:N)
        rv["mem_q"] = cls.__get_memmap_category([pport], con_ports_list)
        # tail is mode manager write，mode user read (1:1/1:N)
        rv["mem_tail"] = cls.__get_memmap_category([pport], con_ports_list)
        # head is mode user write, mode manager read (1:1/1:N)
        rv["mem_head"] = cls.__get_memmap_category(con_ports_list, [pport])
        # mode machine is mode manager write，mode user write (1:1/1:N)
        rv["mem_mode_machine"] = cls.__get_memmap_category(mixed_ports_list, mixed_ports_list)
        # ack flags is mode manager write，mode user read (1:1/1:N)
        rv["mem_ack_flags"] = cls.__get_memmap_category([pport], con_ports_list)
        # mode disable trigger is is mode manager write，mode user read
        rv["mem_mode_dis_trig"] = cls.__get_memmap_category([pport], con_ports_list)
        return rv

    @classmethod
    def parse_cs_client_rport(cls, access, runnable_entity, sw_component_type, type):
        swc_name = utils.get_short_name(sw_component_type)
        if not hasattr(access, "OPERATION_IREF"):
            return {}
        operation_iref = access.OPERATION_IREF
        context_r_port_ref = operation_iref.CONTEXT_R_PORT_REF
        target_required_operation_ref = operation_iref.TARGET_REQUIRED_OPERATION_REF
        if not target_required_operation_ref:
            raise Exception(
                f"swc: {swc_name}, runnable:{utils.get_short_name(runnable_entity)} "
                f"access point: {utils.get_short_name(access)}, TARGET_REQUIRED_OPERATION_REF is not defined"
            )
        operation_path = target_required_operation_ref.valueOf_
        operation = access.find(operation_path)
        if not operation:
            # logger.debug("invalid operation")
            return {}
        rport_path = utils.get_valueOf(context_r_port_ref)
        rport_prototype = access.find(rport_path)
        if not rport_prototype:
            return {}
        operation_name = utils.get_short_name(operation)
        operation_path_short = "/".join(operation_path.split("/")[-2:])
        # get port interface info
        port_interface_info = cls.__parse_cs_port_interface_info(rport_prototype, operation_path)

        port_name = utils.get_short_name(rport_prototype)
        new_port_name = port_name + "_" + operation_name
        rport_core_id = cls.__parse_sw_component_type_core_id(swc_name)
        rport_osapplication = cls.__parse_sw_component_type_osapplication(swc_name)
        args, return_type, sorted_args = cls.__parse_operation(access.find(rport_path), operation_path)
        runnable_name = utils.get_short_name(runnable_entity)
        runnable_symbol = utils.get_runnable_symbol(runnable_entity)
        rport_dict = {
            "sort_name": f"{swc_name}_{new_port_name}",
            "name": new_port_name,
            "port_key": new_port_name,
            "component": swc_name,
            "path": rport_path,
            "type": type,
            "operation": {"args": args, "sorted_args": sorted_args, "return_type": return_type},
            "runnable": [runnable_name],
            "symbol": [runnable_symbol],
            "runnable_path": [runnable_entity.get_path()],
            "task": (
                [cls.runnable_tasks[runnable_symbol]] if runnable_symbol in cls.runnable_tasks else []
            ),  # DONOT use None!
            "connected_ports": {},
            "timeout": int(float(access.TIMEOUT.valueOf_) * 1000) if access.TIMEOUT else 0,
            "ioc": False,
            "core_id": rport_core_id,
            "osapplication": rport_osapplication,
            "client_id": 0,
            "client_num": 0,
            "port_interface_info": port_interface_info,
            "result_run": cls.__parse_cs_rport_result_runnable(access, runnable_entity),
            "memmap": {},
            "schedule_table": {},
            # 'is_direct_call': True
        }
        rport_dict["return_mode"] = cls.__parse_cs_rport_return_mode(access)
        if rport_path not in cls.r_connections or not sw_component_type.find(cls.r_connections[rport_path][0]):
            rport_dict["connected_ports"] = None
            return rport_dict

        # parse 1:1 and 1:N (one server with multi client)
        connected_ports = {"category": "", "ports": []}
        pport_path = cls.r_connections[rport_path][0]
        rport_path_list = cls.p_connections[pport_path]
        connected_ports["category"] = "1:N" if len(rport_path_list) > 1 else "1:1"

        # 获取Server端的信息，此时PR两端均有runnable access
        symbol_name = ""
        pport_operation_path = ""
        connected_pport_path = cls.r_connections[rport_path][0]
        pport_operation_key = f"{connected_pport_path}{operation_path_short}"
        # operation of connected pport is not accessed by any runnable in the peer swc
        if pport_operation_key not in cls.port_operation_access:
            pass
        else:
            pport_runnable_path = list(cls.port_operation_access[pport_operation_key].keys())[0]
            pport_operation_path = list(cls.port_operation_access[pport_operation_key].values())[0][
                "original_operation_ref"
            ]
            runnable_obj = rport_prototype.find(pport_runnable_path)
            symbol_name = (
                utils.get_valueOf(runnable_obj.SYMBOL) if runnable_obj.SYMBOL else utils.get_short_name(runnable_obj)
            )

        rport_path_list.sort(key=lambda x: (len(x), x.lower()))
        rport_dict["client_id"] = rport_path_list.index(rport_path)
        rport_dict["client_num"] = len(rport_path_list)

        # connected_port = {"port_def_args": {}}
        port_def_args = {}
        if pport_path in cls.pport_api_options:
            port_def_args = cls.pport_api_options[pport_path]
            # connected_port["port_def_args"] = port_def_args
        new_pport_name = pport_path.split("/")[-1] + "_" + operation_name
        pport_swc_name = pport_path.split("/")[-2]
        pport_core_id = cls.__parse_sw_component_type_core_id(pport_swc_name)
        pport_osapplication = cls.__parse_sw_component_type_osapplication(pport_swc_name)
        has_task_mapping = False
        if cls.component_osapplications.get(pport_swc_name, None) is not None:
            has_task_mapping = True
        if (not pport_osapplication) or (
            has_task_mapping
            and pport_core_id
            and pport_core_id != rport_core_id
            and symbol_name not in cls.mapped_schedulable_entitys
        ):
            logger.error(f"Server runnable <{pport_swc_name}/{symbol_name}> not properly mapped to any Task")
            rport_dict["connected_ports"] = None
            return rport_dict

        connected_ports["ports"].append(
            {
                "name": new_pport_name,
                "component": pport_swc_name,
                "port_path": pport_path,
                "operation_path": pport_operation_path,
                "symbol": symbol_name,
                "runnable": symbol_name,  # check it
                "task": cls.runnable_tasks.get(symbol_name),
                "port_def_args": port_def_args,
                "core_id": pport_core_id,
                "osapplication": pport_osapplication,
            }
        )
        rport_dict["connected_ports"] = connected_ports

        # is isolcate call function: server run can be called directly from diff osa
        iso_call_func_info = cls.iso_call_func.get(pport_osapplication, {}).get(symbol_name, {})
        if iso_call_func_info:
            if pport_core_id != rport_core_id:
                rport_dict["ioc"] = True
            elif pport_osapplication != rport_osapplication:
                # update include header files
                if swc_name not in cls.iso_call_func_include_header_file:
                    cls.iso_call_func_include_header_file[swc_name] = set()
                cls.iso_call_func_include_header_file[swc_name].add(iso_call_func_info["header_file_name"])
        else:
            if "Sync Client" == rport_dict["type"]:
                pport_task = connected_ports["ports"][0]["task"]
                rport_task = rport_dict["task"][0] if rport_dict["task"] else ""
                if pport_task and pport_task != rport_task:
                    rport_dict["ioc"] = True
            else:
                if pport_osapplication != rport_osapplication:
                    rport_dict["ioc"] = True

        rport_dict["memmap"] = cls.__update_cs_port_memmap(rport_dict)
        if rport_dict["ioc"] and connected_ports:
            rport_dict["set_events"] = cls.__parse_cs_port_set_events_by_connected_ports(connected_ports)
            rport_dict["queue"] = cls.__pack_cs_ioc_client_queue_info(rport_dict, connected_ports)

        os_counter = cls.os_counter.get(rport_dict["osapplication"], {})
        if os_counter and rport_dict["ioc"] and rport_dict["timeout"] > 0.0:
            if rport_dict["return_mode"] == "polling":
                rport_dict["schedule_table"]["name"] = f"Rte_St_{swc_name}_{new_port_name}"
                rport_dict["schedule_table"]["id"] = f'OS_SCHEDTABLE_{rport_dict["schedule_table"]["name"].upper()}_ID'
                rport_dict["schedule_table"]["task"] = rport_dict["task"][0]
                rport_dict["schedule_table"]["counter"] = os_counter
                rport_dict["schedule_table"]["timeout"] = rport_dict["timeout"]
                rport_dict["schedule_table"]["trigger_task"] = None
                rport_dict["schedule_table"]["trigger_event"] = None
                if rport_dict["schedule_table"]["id"] not in cls.rte_sch_tbl:
                    cls.rte_sch_tbl[rport_dict["schedule_table"]["id"]] = rport_dict["schedule_table"]
            elif rport_dict["return_mode"] == "waiting":
                rport_dict["schedule_table"]["name"] = f"Rte_St_{swc_name}_{new_port_name}"
                rport_dict["schedule_table"]["id"] = f'OS_SCHEDTABLE_{rport_dict["schedule_table"]["name"].upper()}_ID'
                rport_dict["schedule_table"]["task"] = rport_dict["task"][0]
                rport_dict["schedule_table"]["counter"] = os_counter
                rport_dict["schedule_table"]["timeout"] = rport_dict["timeout"]
                rport_dict["schedule_table"]["trigger_task"] = rport_dict["task"][0]
                rport_dict["schedule_table"]["trigger_event"] = f'Rte_Ev_Timeout_{rport_dict["task"][0]}'
                if rport_dict["schedule_table"]["id"] not in cls.rte_sch_tbl:
                    cls.rte_sch_tbl[rport_dict["schedule_table"]["id"]] = rport_dict["schedule_table"]
        return rport_dict

    @classmethod
    def parse_cs_server_pport(cls, op_event, sw_component_type):
        swc_name = utils.get_short_name(sw_component_type)
        start_on_event_ref = op_event.START_ON_EVENT_REF
        operation_iref = op_event.OPERATION_IREF
        operation_path = utils.get_valueOf(operation_iref.TARGET_PROVIDED_OPERATION_REF)
        operation = op_event.find(operation_path)
        pport_path = utils.get_valueOf(operation_iref.CONTEXT_P_PORT_REF)
        port_def_args = {}
        if pport_path in cls.pport_api_options:
            port_def_args = cls.pport_api_options[pport_path]
        if not operation:
            # logger.debug("invalid operation")
            return {}
        # if pport_path not in cls.p_connections:
        #     return {}
        pport_prototype = op_event.find(pport_path)
        if not pport_prototype:
            return {}
        server_runnable = pport_prototype.find(start_on_event_ref.valueOf_)
        if not server_runnable:
            return {}

        operation_name = utils.get_short_name(operation)
        operation_path_short = "/".join(operation_path.split("/")[-2:])

        port_interface_info = cls.__parse_cs_port_interface_info(pport_prototype, operation_path)
        port_name = utils.get_short_name(pport_prototype)
        new_port_name = port_name + "_" + operation_name
        pport_core_id = cls.__parse_sw_component_type_core_id(swc_name)
        pport_osapplication = cls.__parse_sw_component_type_osapplication(swc_name)
        pport_dict = {
            "sort_name": f"{swc_name}_{new_port_name}",
            "name": new_port_name,
            "port_key": new_port_name,
            "type": "Server",
            "component": swc_name,
            "port_path": pport_path,
            "operation_path": operation_path,
            "operation": {"server_runnable_symbol": "", "args": {}, "return_type": "void"},
            "port_def_args": port_def_args,
            "connected_ports": {},
            "runnable": "",
            "task": "",
            "ioc": False,
            "core_id": pport_core_id,
            "osapplication": pport_osapplication,
            "client_num": len(cls.p_connections[pport_path]) if pport_path in cls.p_connections else 0,
            "port_interface_info": port_interface_info,
            "is_inter_osa_unmapped": True,
            # 'is_direct_call': False,
        }
        args, return_type, sorted_args = cls.__parse_operation(pport_prototype, operation_path)
        pport_dict["operation"]["args"] = args
        pport_dict["operation"]["sorted_args"] = sorted_args
        pport_dict["operation"]["return_type"] = return_type

        server_symbol_name = utils.get_runnable_symbol(server_runnable)
        pport_dict["operation"]["server_runnable_symbol"] = server_symbol_name
        pport_dict["runnable"] = server_symbol_name
        pport_dict["task"] = cls.runnable_tasks.get(server_symbol_name, "")

        # parse 1:1 and 1:N (one server with multi client)
        connected_ports = {"category": "", "ports": []}
        rport_path_list = cls.p_connections[pport_path] if pport_path in cls.p_connections else []
        connected_ports["category"] = "1:N" if len(rport_path_list) > 1 else "1:1"

        # is isolcate call function: server run can be called directly from diff osa
        is_iso_call_func = bool(cls.iso_call_func.get(pport_osapplication, {}).get(server_symbol_name, {}))

        for connected_rport_path in rport_path_list:
            if not sw_component_type.find(connected_rport_path):
                break
            rport_swc_name = connected_rport_path.split("/")[-2]
            rport_name = connected_rport_path.split("/")[-1]
            rport_operation_key = f"{connected_rport_path}{operation_path_short}"

            if rport_operation_key not in cls.port_operation_access:
                continue
            # the operation of connected rport is accessed by multi runnables in the peer swc
            for runnable_path, access_info in cls.port_operation_access[rport_operation_key].items():
                rport_core_id = cls.__parse_sw_component_type_core_id(rport_swc_name)
                rport_osapplication = cls.__parse_sw_component_type_osapplication(rport_swc_name)

                # error cfg
                if (
                    pport_core_id
                    and pport_core_id != rport_core_id
                    and server_symbol_name not in cls.mapped_schedulable_entitys
                ):
                    logger.error(f"Server runnable <{swc_name}/{server_symbol_name}> not properly mapped to any Task")
                    continue

                connected_component = sw_component_type.find("/".join(connected_rport_path.split("/")[:-1]))
                runnable_obj = sw_component_type.find(runnable_path)
                runnable_symbol = utils.get_runnable_symbol(runnable_obj)
                access = None
                for ele in getattr(
                    getattr(runnable_obj, "SERVER_CALL_POINTS", None), "ASYNCHRONOUS_SERVER_CALL_POINT", []
                ):
                    if ele.OPERATION_IREF.CONTEXT_R_PORT_REF.valueOf_ == connected_rport_path:
                        access = ele
                        rport_type = "Async Client"
                for ele in getattr(
                    getattr(runnable_obj, "SERVER_CALL_POINTS", None), "SYNCHRONOUS_SERVER_CALL_POINT", []
                ):
                    if ele.OPERATION_IREF.CONTEXT_R_PORT_REF.valueOf_ == connected_rport_path:
                        access = ele
                        rport_type = "Sync Client"

                if rport_core_id != pport_core_id:
                    pport_dict["is_inter_osa_unmapped"] = False
                elif rport_osapplication == pport_osapplication:
                    pport_dict["is_inter_osa_unmapped"] = False
                elif pport_dict["task"]:
                    pport_dict["is_inter_osa_unmapped"] = False

                rport_ioc = False
                if is_iso_call_func:
                    if rport_core_id != pport_core_id:
                        pport_dict["ioc"] = True
                        rport_ioc = True
                else:
                    if "Sync Client" == rport_type:
                        pport_task = pport_dict["task"]
                        rport_task = cls.runnable_tasks.get(runnable_symbol, "")
                        if pport_task and pport_task != rport_task:
                            pport_dict["ioc"] = True
                            rport_ioc = True
                    else:
                        if rport_osapplication != pport_osapplication:
                            pport_dict["ioc"] = True
                            rport_ioc = True
                # the actual rport, not access point (that is, multi access of rport is merged)
                # TODO refactor is necessary -> dict
                added_flag = False
                key_name = f"{rport_swc_name}_{rport_name}_{operation_name}"
                for conn_rport in connected_ports["ports"]:
                    if key_name == conn_rport["key_name"]:
                        added_flag = True
                        break
                if not added_flag:
                    connected_ports["ports"].append(
                        {
                            "name": rport_name + "_" + operation_name,
                            "component": rport_swc_name,
                            "key_name": f"{rport_swc_name}_{rport_name}_{operation_name}",
                            "type": rport_type,
                            "task": (
                                [cls.runnable_tasks[runnable_symbol]] if runnable_symbol in cls.runnable_tasks else []
                            ),
                            "runnable": [runnable_symbol],
                            "port_path": connected_rport_path,
                            "operation_path": access_info["original_operation_ref"],
                            "core_id": rport_core_id,
                            "osapplication": rport_osapplication,
                            "return_mode": cls.__parse_cs_rport_return_mode(access) if access else "error",
                            "return_trigger_event": cls.parse_return_trigger(connected_component, runnable_obj, access),
                            "ioc": rport_ioc,
                        }
                    )
                else:
                    for connted_rport in connected_ports["ports"]:
                        if key_name == conn_rport["key_name"]:
                            if runnable_symbol in cls.runnable_tasks:
                                connted_rport["task"].append(cls.runnable_tasks[runnable_symbol])
                                connted_rport["runnable"].append(runnable_symbol)
                            break
        # process the connection degradation caused by connected ports without access point
        if connected_ports and len(connected_ports["ports"]) <= 0:
            connected_ports = None
        if connected_ports:
            rport_path_list.sort(key=lambda x: (len(x), x.lower()))
            for rport in connected_ports["ports"]:
                rport["client_id"] = rport_path_list.index(rport["port_path"])
            connected_ports["ports"].sort(key=lambda x: (x["client_id"]))
        pport_dict["connected_ports"] = connected_ports
        if pport_dict["ioc"] and connected_ports:
            pport_dict["queue"] = cls.__pack_cs_ioc_server_queue_info(pport_dict, connected_ports)
        return pport_dict

    @classmethod
    def __parse_sr_port_accessed_variable_init_value(cls, access_variable_path, ar_port, datatype):
        # deprecated!
        init_value = {}
        com_specs = []
        nv_com_specs = []
        ar_init_value = None
        # TODO: optimization: polling -> lookup
        if ar_port.get_tag() == "P-PORT-PROTOTYPE":
            com_specs = ar_port.PROVIDED_COM_SPECS.NONQUEUED_SENDER_COM_SPEC
        elif ar_port.get_tag() == "R-PORT-PROTOTYPE":
            com_specs = ar_port.REQUIRED_COM_SPECS.NONQUEUED_RECEIVER_COM_SPEC
        elif ar_port.get_tag() == "PR-PORT-PROTOTYPE":
            nv_com_specs = (
                ar_port.REQUIRED_COM_SPECS.NV_REQUIRE_COM_SPEC
                if hasattr(ar_port, "REQUIRED_COM_SPECS") and ar_port.REQUIRED_COM_SPECS
                else ar_port.PROVIDED_COM_SPECS.NV_PROVIDE_COM_SPEC
            )

        for com_spec in com_specs:
            if not com_spec.DATA_ELEMENT_REF:
                continue
            if access_variable_path == utils.get_valueOf(com_spec.DATA_ELEMENT_REF):
                if hasattr(com_spec, "INIT_VALUE"):
                    ar_init_value = com_spec.INIT_VALUE
                break
        for nv_com_spec in nv_com_specs:
            if not nv_com_spec.VARIABLE_REF:
                continue
            if access_variable_path == utils.get_valueOf(nv_com_spec.VARIABLE_REF):
                if hasattr(nv_com_spec, "INIT_VALUE"):
                    ar_init_value = nv_com_spec.INIT_VALUE
                break
        if not ar_init_value:
            return init_value
        if ar_init_value.CONSTANT_REFERENCE:
            init_value = cls.__parse_sr_init_value_by_const_reference(ar_init_value, datatype)
        else:
            init_value = cls.__parse_sr_init_value_by_value_definition(ar_init_value, datatype)
        return init_value

    @classmethod
    def __parse_sr_accessed_variable_init_value(cls, comspec_key, datatype, is_p):
        comspec = (
            cls.p_access_comspec_map.get(comspec_key, None) if is_p else cls.r_access_comspec_map.get(comspec_key, None)
        )
        if not comspec:
            return {}
        if not hasattr(comspec, "INIT_VALUE"):
            return {}
        ar_init_value = comspec.INIT_VALUE
        if not ar_init_value:
            return {}

        if ar_init_value.CONSTANT_REFERENCE:
            init_value = cls.__parse_sr_init_value_by_const_reference(ar_init_value, datatype)
        else:
            init_value = cls.__parse_sr_init_value_by_value_definition(ar_init_value, datatype)
        return init_value

    @classmethod
    def __parse_cal_prm_const_init_value(cls, comspec_key, datatype, is_p):
        comspec = (
            cls.r_param_comspec_map.get(comspec_key, None) if is_p else cls.r_param_comspec_map.get(comspec_key, None)
        )
        if not comspec:
            return {}
        if not hasattr(comspec, "INIT_VALUE"):
            return {}
        ar_init_value = comspec.INIT_VALUE
        if not ar_init_value:
            return {}

        if ar_init_value.CONSTANT_REFERENCE:
            init_value = cls.__parse_sr_init_value_by_const_reference(ar_init_value, datatype)
        else:
            init_value = cls.__parse_sr_init_value_by_value_definition(ar_init_value, datatype)
        return init_value

    @classmethod
    def __parse_constant_value(cls, const, const_name, datatype):
        if const["ar_const"].VALUE_SPEC.NUMERICAL_VALUE_SPECIFICATION:
            const.update(
                {
                    "name": const_name,
                    "type": "UNION" if datatype["native_category"] == "UNION" else "NUMERICAL",
                    "value": cls.__parse_numerical_constant_value(
                        const["ar_const"].VALUE_SPEC.NUMERICAL_VALUE_SPECIFICATION, datatype
                    ),
                }
            )
        elif const["ar_const"].VALUE_SPEC.RECORD_VALUE_SPECIFICATION:
            const.update(
                {
                    "name": const_name,
                    "type": "STRUCTURE",
                    "value": cls.__parse_struct_value(
                        const["ar_const"].VALUE_SPEC.RECORD_VALUE_SPECIFICATION, datatype
                    ),
                }
            )
        elif const["ar_const"].VALUE_SPEC.ARRAY_VALUE_SPECIFICATION:
            const.update(
                {
                    "name": const_name,
                    "type": "ARRAY",
                    "value": cls.__parse_array_value(const["ar_const"].VALUE_SPEC.ARRAY_VALUE_SPECIFICATION, datatype),
                }
            )
        elif const["ar_const"].VALUE_SPEC.APPLICATION_VALUE_SPECIFICATION:
            pass  # TODO
        else:
            raise Exception(f"Can not parse Const {const_name} yet!")

    @classmethod
    def __parse_sr_init_value_by_const_reference(cls, ar_init_value, datatype):
        ref = ar_init_value.CONSTANT_REFERENCE.CONSTANT_REF
        if ref in cls.const_init_value:
            return cls.const_init_value[ref]
        init_value = {}
        const_name = utils.get_valueOf(ar_init_value.CONSTANT_REFERENCE.CONSTANT_REF).split("/")[-1]
        if const_name in cls.consts:
            ar_const = cls.consts[const_name]
            if "value" not in ar_const:
                cls.__parse_constant_value(ar_const, const_name, datatype)

            init_value.update(
                {
                    "category": "CONSTANT_REFERENCE",
                    "name": const_name,
                    "value": {"name": ar_const["name"], "type": ar_const["type"], "value": ar_const["value"]},
                }
            )
        cls.const_init_value[ref] = init_value
        return init_value

    @classmethod
    def __parse_sr_init_value_by_value_definition(cls, ar_initial_value, datatype):
        init_value = {}
        if (
            hasattr(ar_initial_value, "APPLICATION_VALUE_SPECIFICATION")
            and ar_initial_value.APPLICATION_VALUE_SPECIFICATION
        ):
            if utils.get_valueOf(ar_initial_value.APPLICATION_VALUE_SPECIFICATION.CATEGORY) == "VALUE":
                init_value.update(
                    {
                        "category": "APPLICATION_VALUE_SPECIFICATION",
                        "name": f"Rte_C_{datatype['name']}",
                        "value": cls.__parse_all_application_value(
                            ar_initial_value.APPLICATION_VALUE_SPECIFICATION, datatype
                        ),
                    }
                )
            else:
                # TODO, 待补充其他格式
                pass
        elif (
            hasattr(ar_initial_value, "NUMERICAL_VALUE_SPECIFICATION")
            and ar_initial_value.NUMERICAL_VALUE_SPECIFICATION
        ):
            init_value.update(
                {
                    "category": "NUMERICAL_VALUE_SPECIFICATION",
                    "name": f"Rte_C_{datatype['name']}",
                    "value": cls.__parse_all_numerical_value(ar_initial_value.NUMERICAL_VALUE_SPECIFICATION, datatype),
                }
            )
        elif hasattr(ar_initial_value, "ARRAY_VALUE_SPECIFICATION") and ar_initial_value.ARRAY_VALUE_SPECIFICATION:
            if (
                hasattr(ar_initial_value.ARRAY_VALUE_SPECIFICATION.ELEMENTS, "NUMERICAL_VALUE_SPECIFICATION")
                and ar_initial_value.ARRAY_VALUE_SPECIFICATION.ELEMENTS.NUMERICAL_VALUE_SPECIFICATION
            ):
                init_value.update(
                    {
                        "category": "ARRAY_VALUE_SPECIFICATION",
                        "name": f"Rte_C_{datatype['name']}",
                        "value": cls.__parse_all_array_value(ar_initial_value.ARRAY_VALUE_SPECIFICATION, datatype),
                    }
                )
            elif (
                hasattr(ar_initial_value.ARRAY_VALUE_SPECIFICATION.ELEMENTS, "APPLICATION_VALUE_SPECIFICATION")
                and ar_initial_value.ARRAY_VALUE_SPECIFICATION.ELEMENTS.APPLICATION_VALUE_SPECIFICATION
            ):
                init_value.update(
                    {
                        "category": "ARRAY_VALUE_SPECIFICATION",
                        "name": f"Rte_C_{datatype['name']}",
                        "value": cls.__parse_all_array_value(ar_initial_value.ARRAY_VALUE_SPECIFICATION, datatype),
                    }
                )
            elif (
                hasattr(ar_initial_value.ARRAY_VALUE_SPECIFICATION.ELEMENTS, "ARRAY_VALUE_SPECIFICATION")
                and ar_initial_value.ARRAY_VALUE_SPECIFICATION.ELEMENTS.ARRAY_VALUE_SPECIFICATION
            ):
                # multi-D array
                init_value.update(
                    {
                        "category": "ARRAY_VALUE_SPECIFICATION",
                        "name": f"Rte_C_{datatype['name']}",
                        "value": cls.__parse_all_array_value(ar_initial_value.ARRAY_VALUE_SPECIFICATION, datatype),
                    }
                )
        elif hasattr(ar_initial_value, "RECORD_VALUE_SPECIFICATION") and ar_initial_value.RECORD_VALUE_SPECIFICATION:
            init_value.update(
                {
                    "category": "RECORD_VALUE_SPECIFICATION",
                    "name": f"Rte_C_{datatype['name']}",
                    "value": cls.__parse_all_struct_value(ar_initial_value.RECORD_VALUE_SPECIFICATION, datatype),
                }
            )
        else:
            pass

        return init_value

    @classmethod
    def __convert_adt_to_idt(cls, adt_path, mapping_sets):
        idt_path = None
        if mapping_sets:
            for mapping_set in mapping_sets:
                try:
                    if adt_path in cls.datatype_mapping_sets[mapping_set]:
                        idt_path = cls.datatype_mapping_sets[mapping_set][adt_path]
                        break
                except Exception as e:
                    raise Exception(f"Mapping Set {mapping_set} is not defined!") from e
        else:
            try:
                idt_path = cls.adt_mappings[adt_path]
            except Exception as e:
                raise Exception(f"ADT {adt_path} is not mapped in any Mapping Set!") from e
        return idt_path

    @classmethod
    def __parse_sr_accessed_variable_arg(cls, accessed_variable, ar_port, mapping_sets, parse_init_value=True):
        # deprecated!
        arg = {}
        idt_path = None
        adt_path = None
        if accessed_variable.TYPE_TREF.DEST != "IMPLEMENTATION-DATA-TYPE":
            adt_path = utils.get_type_tref(accessed_variable)
            idt_path = cls.__convert_adt_to_idt(adt_path, mapping_sets)
            if not idt_path:
                raise Exception(f"ADT {adt_path} is not mapped in the specified Mapping Set!")
        else:
            idt_path = utils.get_type_tref(accessed_variable)

        datatype = cls.datatype_path_to_idt_mapping[idt_path]["idt"]
        init_value = {}
        if parse_init_value:
            init_value = cls.__parse_sr_port_accessed_variable_init_value(
                accessed_variable.get_path(), ar_port, datatype
            )
        arg = {"datatype": datatype, "init_value": init_value, "adt_path": adt_path, "idt_path": idt_path}
        return arg

    @classmethod
    def __parse_sr_accessed_variable(cls, accessed_variable, mapping_sets, comspec_key, is_p, parse_init_value=True):
        arg = {}
        idt_path = None
        adt_path = None
        if accessed_variable.TYPE_TREF.DEST != "IMPLEMENTATION-DATA-TYPE":
            adt_path = utils.get_type_tref(accessed_variable)
            idt_path = cls.__convert_adt_to_idt(adt_path, mapping_sets)
            if not idt_path:
                raise Exception(f"ADT {adt_path} is not mapped in the specified Mapping Set!")
        else:
            idt_path = utils.get_type_tref(accessed_variable)

        datatype = cls.datatype_path_to_idt_mapping[idt_path]["idt"]
        init_value = {}
        if parse_init_value:
            init_value = cls.__parse_sr_accessed_variable_init_value(comspec_key, datatype, is_p)
        arg = {
            "datatype": datatype,
            "init_value": init_value,
            "adt_path": adt_path,
            "idt_path": idt_path,
            "init_category": VariableInitCategory.ZERO_INIT,
        }
        return arg

    @classmethod
    def __parse_cal_prm_const_arg(cls, accessed_variable, mapping_sets, comspec_key, is_p, parse_init_value=True):
        arg = {}
        idt_path = None
        adt_path = None
        if accessed_variable.TYPE_TREF.DEST != "IMPLEMENTATION-DATA-TYPE":
            adt_path = utils.get_type_tref(accessed_variable)
            idt_path = cls.__convert_adt_to_idt(adt_path, mapping_sets)
            if not idt_path:
                raise Exception(f"ADT {adt_path} is not mapped in the specified Mapping Set!")
        else:
            idt_path = utils.get_type_tref(accessed_variable)

        datatype = cls.datatype_path_to_idt_mapping[idt_path]["idt"]
        datatype["array_dim"] = cls.__get_array_dimension(datatype)
        init_value = {}
        if parse_init_value:
            init_value = cls.__parse_cal_prm_const_init_value(comspec_key, datatype, is_p)
        arg = {
            "datatype": datatype,
            "init_value": init_value,
            "adt_path": adt_path,
            "idt_path": idt_path,
            "init_category": None,
        }
        return arg

    @classmethod
    def __get_array_dimension(cls, datatype):
        if datatype["native_category"] != "ARRAY":
            return 0
        dim = 1
        basetype_name = datatype["basetype"]
        while cls.idts.get(basetype_name, {}).get("native_category", None) == "ARRAY":
            dim += 1
            basetype_name = cls.idts.get(basetype_name, {}).get("basetype", None)
        return dim

    @classmethod
    def __update_port_data_element_access(cls, port_data_element_access, variable_access, runnable_path, access_type):
        data_element_path = utils.get_valueOf(
            variable_access.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF.TARGET_DATA_PROTOTYPE_REF
        )
        data_element_path_short = "/".join(data_element_path.split("/")[-2:])
        port_path = utils.get_valueOf(variable_access.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF.PORT_PROTOTYPE_REF)
        data_element = variable_access.find(data_element_path)
        if not data_element:
            logger.error(f"The data element <{data_element_path}> does not exist!")
            return
        port_data_element_key = f"{port_path}{data_element_path_short}"
        if cls.get_if_data_element_is_queued(data_element):
            if access_type == "Write":
                access_type = "Send"
            elif access_type == "Read":
                access_type = "Receive"
        if port_data_element_key not in port_data_element_access:
            port_data_element_access.update({port_data_element_key: {}})
        port_data_element_access[port_data_element_key].update(
            {
                runnable_path: {
                    "access_type": access_type,
                    "original_data_element_path": data_element_path,
                    "is_prport": True if variable_access.find(port_path).get_tag() == "PR-PORT-PROTOTYPE" else False,
                }
            }
        )
        if access_type == "Receive":
            port_data_element_access[port_data_element_key][runnable_path].update({"timeout": 0})

    @classmethod
    def __update_port_data_element_waitpoint(cls, port_data_element_access, waitpoints, runnable_ref):
        for waitpoint in waitpoints.WAIT_POINT:
            event = waitpoints.find(utils.get_valueOf(waitpoint.TRIGGER_REF))
            if not hasattr(event, "DATA_IREF"):
                continue
            rport_ref = utils.get_valueOf(event.DATA_IREF.CONTEXT_R_PORT_REF)
            data_element_path = utils.get_valueOf(event.DATA_IREF.TARGET_DATA_ELEMENT_REF)
            data_element_path_short = "/".join(data_element_path.split("/")[-2:])
            rport_data_element_key = f"{rport_ref}{data_element_path_short}"
            if rport_data_element_key not in port_data_element_access:
                port_data_element_access.update({rport_data_element_key: {}})
            if runnable_ref not in port_data_element_access[rport_data_element_key]:
                port_data_element_access[rport_data_element_key].update({runnable_ref: {}})
            port_data_element_access[rport_data_element_key][runnable_ref].update(
                {"access_type": "Receive", "timeout": int(float(utils.get_valueOf(waitpoint.TIMEOUT)) * 1000)}
            )

    @classmethod
    def __update_pport_operation_access(cls, port_operation_access, ar_event):
        operation_ref = utils.get_valueOf(ar_event.OPERATION_IREF.TARGET_PROVIDED_OPERATION_REF)
        pport_ref = utils.get_valueOf(ar_event.OPERATION_IREF.CONTEXT_P_PORT_REF)
        start_on_event_ref = utils.get_valueOf(ar_event.START_ON_EVENT_REF)
        # original_target_provided_operation_ref = target_provided_operation_ref
        # target_provided_operation_ref = '/'.join(target_provided_operation_ref.split('/')[-2:])
        operation_ref_short = "/".join(operation_ref.split("/")[-2:])
        port_operation_key = f"{pport_ref}{operation_ref_short}"
        if port_operation_key not in port_operation_access:
            port_operation_access.update({port_operation_key: {}})
        port_operation_access[port_operation_key].update(
            {start_on_event_ref: {"access_type": "Server", "original_operation_ref": operation_ref}}
        )
        # if target_provided_operation_ref not in access:
        #     access.update({
        #         target_provided_operation_ref: {
        #             "r_access_runnable": {},
        #             "p_access_runnable": {},
        #             "original_target_operation_ref": operation_ref,
        #         }
        #     })
        # if swc_name not in access[target_provided_operation_ref]["p_access_runnable"]:
        #     access[target_provided_operation_ref]["p_access_runnable"].update({swc_name: set()})
        # access[target_provided_operation_ref]["p_access_runnable"][swc_name].add(
        #     (start_on_event_ref, context_p_port_ref))

    @classmethod
    def __update_rport_operation_access(cls, port_operation_access, ar_runnable):
        server_call_points = ar_runnable.SERVER_CALL_POINTS
        if server_call_points is None:
            return
        for server_call_point in (
            server_call_points.SYNCHRONOUS_SERVER_CALL_POINT + server_call_points.ASYNCHRONOUS_SERVER_CALL_POINT
        ):
            if server_call_point.OPERATION_IREF.TARGET_REQUIRED_OPERATION_REF:
                operation_ref = utils.get_valueOf(server_call_point.OPERATION_IREF.TARGET_REQUIRED_OPERATION_REF)
                rport_ref = utils.get_valueOf(server_call_point.OPERATION_IREF.CONTEXT_R_PORT_REF)
                operation_ref_short = "/".join(operation_ref.split("/")[-2:])
                port_operation_key = f"{rport_ref}{operation_ref_short}"
                if port_operation_key not in port_operation_access:
                    port_operation_access.update({port_operation_key: {}})
                port_operation_access[port_operation_key].update(
                    {ar_runnable.get_path(): {"access_type": "Client", "original_operation_ref": operation_ref}}
                )

    @classmethod
    def __parse_component_trigger_access(cls, port_data_element_access, ar_component_type):
        if not hasattr(ar_component_type, "INTERNAL_BEHAVIORS"):
            return
        swc_type = utils.get_short_name(ar_component_type)
        swc_name = cls.sw_component_prototypes[swc_type][0] if swc_type in cls.sw_component_prototypes else swc_type
        for ar_behavior in ar_component_type.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR:
            if not ar_behavior.RUNNABLES:
                continue
            for ar_runnable in ar_behavior.RUNNABLES.RUNNABLE_ENTITY:
                runnable_path = ar_runnable.get_path()
                if ar_runnable.INTERNAL_TRIGGERING_POINTS:
                    for trigger_point in ar_runnable.INTERNAL_TRIGGERING_POINTS.INTERNAL_TRIGGERING_POINT:
                        sw_impl = utils.get_valueOf(trigger_point.SW_IMPL_POLICY)
                        trigger_path = trigger_point.get_path()
                        if trigger_path not in port_data_element_access:
                            port_data_element_access.update({trigger_path: {}})
                        port_data_element_access[trigger_path].update(
                            {
                                runnable_path: {
                                    "original_data_element_path": trigger_path,
                                    "port_path": None,
                                    "swc_name": swc_name,
                                    "sw_impl": sw_impl,
                                    "access_type": "Internal_Trigger",
                                    "is_prport": None,
                                }
                            }
                        )
                if ar_runnable.EXTERNAL_TRIGGERING_POINTS:
                    for trigger_point in ar_runnable.EXTERNAL_TRIGGERING_POINTS.EXTERNAL_TRIGGERING_POINT:
                        pport_ref = utils.get_valueOf(
                            trigger_point.TRIGGER_IREF.P_TRIGGER_IN_ATOMIC_SWC_TYPE_INSTANCE_REF.CONTEXT_P_PORT_REF
                        )
                        trigger_path = utils.get_valueOf(
                            trigger_point.TRIGGER_IREF.P_TRIGGER_IN_ATOMIC_SWC_TYPE_INSTANCE_REF.TARGET_TRIGGER_REF
                        )
                        port_trigger_key = f"{pport_ref}{trigger_path}"
                        if port_trigger_key not in port_data_element_access:
                            port_data_element_access.update({port_trigger_key: {}})
                        port_data_element_access[port_trigger_key].update(
                            {
                                runnable_path: {
                                    "original_data_element_path": trigger_path,
                                    "port_path": pport_ref,
                                    "swc_name": swc_name,
                                    "sw_impl": None,
                                    "access_type": "External_Trigger",
                                    "is_prport": None,
                                }
                            }
                        )

            if not ar_behavior.EVENTS:
                continue
            for ar_event in ar_behavior.EVENTS.INTERNAL_TRIGGER_OCCURRED_EVENT:
                runnable_path = utils.get_valueOf(ar_event.START_ON_EVENT_REF)
                trigger_path = utils.get_valueOf(ar_event.EVENT_SOURCE_REF)
                if trigger_path not in port_data_element_access:
                    port_data_element_access.update({trigger_path: {}})
                port_data_element_access[trigger_path].update(
                    {
                        runnable_path: {
                            "original_data_element_path": trigger_path,
                            "port_path": None,
                            "swc_name": swc_name,
                            "sw_impl": None,
                            "access_type": "Internal_Trigger",
                            "is_prport": None,
                        }
                    }
                )
            for ar_event in ar_behavior.EVENTS.EXTERNAL_TRIGGER_OCCURRED_EVENT:
                runnable_path = utils.get_valueOf(ar_event.START_ON_EVENT_REF)
                pport_ref = utils.get_valueOf(ar_event.TRIGGER_IREF.CONTEXT_R_PORT_REF)
                trigger_path = utils.get_valueOf(ar_event.TRIGGER_IREF.TARGET_TRIGGER_REF)
                port_trigger_key = f"{pport_ref}{trigger_path}"
                if port_trigger_key not in port_data_element_access:
                    port_data_element_access.update({port_trigger_key: {}})
                port_data_element_access[port_trigger_key].update(
                    {
                        runnable_path: {
                            "original_data_element_path": trigger_path,
                            "port_path": pport_ref,
                            "swc_name": swc_name,
                            "sw_impl": None,
                            "access_type": "External_Trigger",
                            "is_prport": None,
                        }
                    }
                )

    @classmethod
    def __parse_component_mode_group_access(cls, access, ar_component_type):
        swc_name = utils.get_short_name(ar_component_type)
        if not hasattr(ar_component_type, "INTERNAL_BEHAVIORS"):
            return
        for ar_behavior in ar_component_type.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR:
            if ar_behavior.RUNNABLES:
                for ar_runnable in ar_behavior.RUNNABLES.RUNNABLE_ENTITY:
                    if ar_runnable.MODE_SWITCH_POINTS:
                        for mode_switch_point in ar_runnable.MODE_SWITCH_POINTS.MODE_SWITCH_POINT:
                            if not mode_switch_point.MODE_GROUP_IREF:
                                raise Exception(
                                    f"mode_switch_point {mode_switch_point.SHORT_NAME.valueOf_} Invalid, "
                                    "check mode manager's arxml"
                                )
                            mode_group_iref = mode_switch_point.MODE_GROUP_IREF
                            context_p_port_ref = mode_group_iref.CONTEXT_P_PORT_REF.valueOf_
                            target_mode_group_ref = mode_group_iref.TARGET_MODE_GROUP_REF.valueOf_
                            assert context_p_port_ref
                            assert target_mode_group_ref
                            if target_mode_group_ref not in access:
                                access.update(
                                    {target_mode_group_ref: {"r_access_runnable": {}, "p_access_runnable": {}}}
                                )
                            if swc_name not in access[target_mode_group_ref]["p_access_runnable"]:
                                access[target_mode_group_ref]["p_access_runnable"][swc_name] = []
                            access[target_mode_group_ref]["p_access_runnable"][swc_name].append(
                                {"runnable_path": ar_runnable.get_path(), "port_path": context_p_port_ref}
                            )
                    if ar_runnable.MODE_ACCESS_POINTS:
                        for mode_access_point in ar_runnable.MODE_ACCESS_POINTS.MODE_ACCESS_POINT:
                            if not mode_access_point.MODE_GROUP_IREF:
                                raise Exception(
                                    f"mode_access_point {mode_access_point.SHORT_NAME.valueOf_} Invalid, "
                                    "check mode manager's arxml"
                                )
                            mode_group_iref = mode_access_point.MODE_GROUP_IREF
                            p_mode_group_in_atomic_swc_instance_ref = (
                                mode_group_iref.P_MODE_GROUP_IN_ATOMIC_SWC_INSTANCE_REF
                            )
                            r_mode_group_in_atomic_swc_instance_ref = (
                                mode_group_iref.R_MODE_GROUP_IN_ATOMIC_SWC_INSTANCE_REF
                            )
                            target_mode_group_ref = None
                            context_p_port_ref = (
                                p_mode_group_in_atomic_swc_instance_ref.CONTEXT_P_PORT_REF.valueOf_
                                if p_mode_group_in_atomic_swc_instance_ref
                                else None
                            )
                            context_r_port_ref = (
                                r_mode_group_in_atomic_swc_instance_ref.CONTEXT_R_PORT_REF.valueOf_
                                if r_mode_group_in_atomic_swc_instance_ref
                                else None
                            )
                            if p_mode_group_in_atomic_swc_instance_ref:
                                target_mode_group_ref = (
                                    p_mode_group_in_atomic_swc_instance_ref.TARGET_MODE_GROUP_REF.valueOf_
                                )
                            elif r_mode_group_in_atomic_swc_instance_ref:
                                target_mode_group_ref = (
                                    r_mode_group_in_atomic_swc_instance_ref.TARGET_MODE_GROUP_REF.valueOf_
                                )

                            assert context_p_port_ref or context_r_port_ref
                            assert target_mode_group_ref
                            if target_mode_group_ref not in access:
                                access.update(
                                    {target_mode_group_ref: {"r_access_runnable": {}, "p_access_runnable": {}}}
                                )
                            if swc_name not in access[target_mode_group_ref]["r_access_runnable"]:
                                access[target_mode_group_ref]["r_access_runnable"][swc_name] = []
                            access[target_mode_group_ref]["r_access_runnable"][swc_name].append(
                                {
                                    "runnable_path": ar_runnable.get_path(),
                                    "port_path": context_p_port_ref if context_p_port_ref else context_r_port_ref,
                                }
                            )
            if ar_behavior.EVENTS:
                for swc_mode_switch_event in ar_behavior.EVENTS.SWC_MODE_SWITCH_EVENT:
                    start_on_event_ref = swc_mode_switch_event.START_ON_EVENT_REF
                    mode_irefs = swc_mode_switch_event.MODE_IREFS.MODE_IREF
                    activation = swc_mode_switch_event.ACTIVATION
                    assert start_on_event_ref and mode_irefs and activation
                    ar_runnable = ar_component_type.find(start_on_event_ref.valueOf_)
                    runnable_name = utils.get_short_name(ar_runnable)
                    runnable_symbol = utils.get_runnable_symbol(ar_runnable)
                    task = cls.runnable_tasks.get(runnable_symbol)
                    osapplication = (
                        cls.component_osapplications[swc_name]
                        if cls.component_osapplications and swc_name in cls.component_osapplications
                        else None
                    )
                    transition_event = {"previous_mode": {}, "next_mode": {}, "runnable_name": ""}
                    entry_event = {"mode": {}, "runnable_name": ""}
                    exit_event = {"mode": {}, "runnable_name": ""}
                    event_info = {}
                    is_valid_mode_group = True
                    for index, mode_iref in enumerate(mode_irefs):
                        target_mode_group_ref = mode_iref.CONTEXT_MODE_DECLARATION_GROUP_PROTOTYPE_REF.valueOf_
                        context_port_ref = mode_iref.CONTEXT_PORT_REF.valueOf_
                        target_mode_declaration_ref = mode_iref.TARGET_MODE_DECLARATION_REF.valueOf_
                        mode_group_name = target_mode_declaration_ref.split("/")[-2]
                        mode_declaration = ar_component_type.find(target_mode_declaration_ref)
                        mode_name = utils.get_short_name(mode_declaration)
                        if mode_group_name not in cls.mode_groups:
                            logger.debug(
                                f"mode_group_name {mode_group_name} Invalid, "
                                "can not found in arxml or category is EXPLICIT_ORDER"
                            )
                            is_valid_mode_group = False
                            break
                        mode_value = cls.mode_groups[mode_group_name]["mode_declarations"][mode_name]
                        if "ON-TRANSITION" == activation.valueOf_:
                            if index == 0:
                                transition_event["previous_mode"].update({"name": mode_name, "value": mode_value})
                                transition_event["runnable_name"] = runnable_name
                                transition_event["task"] = task
                                transition_event["osapplication"] = osapplication
                                transition_event["swc_name"] = swc_name
                            elif index == 1:
                                transition_event["next_mode"].update({"name": mode_name, "value": mode_value})
                                transition_event["runnable_name"] = runnable_name
                                transition_event["task"] = task
                                transition_event["osapplication"] = osapplication
                                transition_event["swc_name"] = swc_name
                        elif "ON-ENTRY" == activation.valueOf_:
                            entry_event["mode"].update({"name": mode_name, "value": mode_value})
                            entry_event["runnable_name"] = runnable_name
                            entry_event["task"] = task
                            entry_event["osapplication"] = osapplication
                            entry_event["swc_name"] = swc_name

                        elif "ON-EXIT" == activation.valueOf_:
                            exit_event["mode"].update({"name": mode_name, "value": mode_value})
                            exit_event["runnable_name"] = runnable_name
                            exit_event["task"] = task
                            exit_event["osapplication"] = osapplication
                            exit_event["swc_name"] = swc_name
                        else:
                            pass
                    if not is_valid_mode_group:
                        continue
                    if "ON-TRANSITION" == activation.valueOf_:
                        if not transition_event["next_mode"] or not transition_event["previous_mode"]:
                            logger.debug(
                                f"swc_mode_switch_event:{utils.get_short_name(swc_mode_switch_event)} Invalid Config, "
                                "ON-TRANSITION event must have 2 mode ref!"
                            )
                            continue
                        event_info = {"ON-TRANSITION": transition_event}
                    elif "ON-ENTRY" == activation.valueOf_:
                        event_info = {"ON-ENTRY": entry_event}
                    elif "ON-EXIT" == activation.valueOf_:
                        event_info = {"ON-EXIT": exit_event}
                    else:
                        pass
                    if target_mode_group_ref not in access:
                        access.update(
                            {
                                target_mode_group_ref: {
                                    "r_access_runnable": {},
                                    "p_access_runnable": {},
                                }
                            }
                        )
                    if swc_name not in access[target_mode_group_ref]["r_access_runnable"]:
                        access[target_mode_group_ref]["r_access_runnable"][swc_name] = []
                    access[target_mode_group_ref]["r_access_runnable"][swc_name].append(
                        {
                            "runnable_path": start_on_event_ref.valueOf_,
                            "port_path": context_port_ref,
                            "swc_mode_switch_event": event_info,
                        }
                    )

    @classmethod
    def __parse_component_data_element_access(cls, port_data_element_access, ar_component_type):
        if not hasattr(ar_component_type, "INTERNAL_BEHAVIORS"):
            return
        for ar_behavior in ar_component_type.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR:
            if not ar_behavior.RUNNABLES:
                continue
            for ar_runnable in ar_behavior.RUNNABLES.RUNNABLE_ENTITY:
                runnable_path = ar_runnable.get_path()
                if ar_runnable.DATA_SEND_POINTS:
                    for variable_access in ar_runnable.DATA_SEND_POINTS.VARIABLE_ACCESS:
                        cls.__update_port_data_element_access(
                            port_data_element_access, variable_access, runnable_path, "Write"
                        )
                if ar_runnable.DATA_WRITE_ACCESSS:
                    for variable_access in ar_runnable.DATA_WRITE_ACCESSS.VARIABLE_ACCESS:
                        cls.__update_port_data_element_access(
                            port_data_element_access, variable_access, runnable_path, "IWrite"
                        )
                if ar_runnable.DATA_RECEIVE_POINT_BY_ARGUMENTS:
                    for variable_access in ar_runnable.DATA_RECEIVE_POINT_BY_ARGUMENTS.VARIABLE_ACCESS:
                        cls.__update_port_data_element_access(
                            port_data_element_access, variable_access, runnable_path, "Read"
                        )
                if ar_runnable.DATA_RECEIVE_POINT_BY_VALUES:
                    for variable_access in ar_runnable.DATA_RECEIVE_POINT_BY_VALUES.VARIABLE_ACCESS:
                        cls.__update_port_data_element_access(
                            port_data_element_access, variable_access, runnable_path, "DRead"
                        )
                if ar_runnable.DATA_READ_ACCESSS:
                    for variable_access in ar_runnable.DATA_READ_ACCESSS.VARIABLE_ACCESS:
                        cls.__update_port_data_element_access(
                            port_data_element_access, variable_access, runnable_path, "IRead"
                        )
                if ar_runnable.WAIT_POINTS:
                    cls.__update_port_data_element_waitpoint(
                        port_data_element_access, ar_runnable.WAIT_POINTS, runnable_path
                    )

    @classmethod
    def __get_prport_data_element_access_dict(cls, ar_component_type):
        port_data_element_access_dict = {}
        if not hasattr(ar_component_type, "INTERNAL_BEHAVIORS"):
            return port_data_element_access_dict

        if not ar_component_type.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR:
            return port_data_element_access_dict

        def update_result(port_data_element_access, port_data_element_access_dict):
            for key, value in port_data_element_access.items():
                if key not in port_data_element_access_dict:
                    port_data_element_access_dict.update({key: []})
                    port_data_element_access_dict[key].append(value)
                else:
                    port_data_element_access_dict[key].append(value)

        for ar_behavior in ar_component_type.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR:
            if not ar_behavior.RUNNABLES:
                continue
            for ar_runnable in ar_behavior.RUNNABLES.RUNNABLE_ENTITY:
                runnable_path = ar_runnable.get_path()
                if ar_runnable.DATA_SEND_POINTS:
                    for variable_access in ar_runnable.DATA_SEND_POINTS.VARIABLE_ACCESS:
                        port_data_element_access = {}
                        cls.__update_port_data_element_access(
                            port_data_element_access, variable_access, runnable_path, "Write"
                        )
                        update_result(port_data_element_access, port_data_element_access_dict)

                if ar_runnable.DATA_WRITE_ACCESSS:
                    for variable_access in ar_runnable.DATA_WRITE_ACCESSS.VARIABLE_ACCESS:
                        port_data_element_access = {}
                        cls.__update_port_data_element_access(
                            port_data_element_access, variable_access, runnable_path, "IWrite"
                        )
                        update_result(port_data_element_access, port_data_element_access_dict)

                if ar_runnable.DATA_RECEIVE_POINT_BY_ARGUMENTS:
                    for variable_access in ar_runnable.DATA_RECEIVE_POINT_BY_ARGUMENTS.VARIABLE_ACCESS:
                        port_data_element_access = {}
                        cls.__update_port_data_element_access(
                            port_data_element_access, variable_access, runnable_path, "Read"
                        )
                        update_result(port_data_element_access, port_data_element_access_dict)

                if ar_runnable.DATA_RECEIVE_POINT_BY_VALUES:
                    for variable_access in ar_runnable.DATA_RECEIVE_POINT_BY_VALUES.VARIABLE_ACCESS:
                        port_data_element_access = {}
                        cls.__update_port_data_element_access(
                            port_data_element_access, variable_access, runnable_path, "DRead"
                        )
                        update_result(port_data_element_access, port_data_element_access_dict)

                if ar_runnable.DATA_READ_ACCESSS:
                    for variable_access in ar_runnable.DATA_READ_ACCESSS.VARIABLE_ACCESS:
                        port_data_element_access = {}
                        cls.__update_port_data_element_access(
                            port_data_element_access, variable_access, runnable_path, "IRead"
                        )
                        update_result(port_data_element_access, port_data_element_access_dict)

                if ar_runnable.WAIT_POINTS:
                    port_data_element_access = {}
                    cls.__update_port_data_element_waitpoint(
                        port_data_element_access, ar_runnable.WAIT_POINTS, runnable_path
                    )
                    update_result(port_data_element_access, port_data_element_access_dict)
            return port_data_element_access_dict

        return {}

    @classmethod
    def __parse_component_operation_access(cls, port_operation_access, server_runnable_conns, ar_component_type):
        if not hasattr(ar_component_type, "INTERNAL_BEHAVIORS"):
            return
        for ar_behavior in ar_component_type.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR:
            if ar_behavior.EVENTS:
                for ar_event in ar_behavior.EVENTS.OPERATION_INVOKED_EVENT:
                    cls.__update_pport_operation_access(port_operation_access, ar_event)
                    cls.__update_aux_server_runnable_connections(server_runnable_conns, ar_event)
            if ar_behavior.RUNNABLES:
                for ar_runnable in ar_behavior.RUNNABLES.RUNNABLE_ENTITY:
                    cls.__update_rport_operation_access(port_operation_access, ar_runnable)

    @classmethod
    def __get_typesize_byte_from_path_and_name(cls, value_type_tref_value, type_name):
        if (
            value_type_tref_value in cls.datatype_path_to_idt_mapping
            and "typesize_byte_for_struct_align" in cls.datatype_path_to_idt_mapping[value_type_tref_value]["idt"]
        ):
            return cls.datatype_path_to_idt_mapping[value_type_tref_value]["idt"]["typesize_byte_for_struct_align"]
        elif type_name in cls.idts and "typesize_byte_for_struct_align" in cls.idts[type_name]:
            return cls.idts[type_name]["typesize_byte_for_struct_align"]
        else:
            return 8

    @classmethod
    def __parse_component_pport_api_options(cls, pport_api_options, ar_component_type):
        if not hasattr(ar_component_type, "INTERNAL_BEHAVIORS"):
            return
        for ar_behavior in ar_component_type.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR:
            if ar_behavior.PORT_API_OPTIONS:
                for port_api_option in ar_behavior.PORT_API_OPTIONS.PORT_API_OPTION:
                    if port_api_option.PORT_ARG_VALUES and port_api_option.PORT_REF:
                        port_def_args = {}
                        para_num = 0
                        for port_defined_argument_value in port_api_option.PORT_ARG_VALUES.PORT_DEFINED_ARGUMENT_VALUE:
                            value_spec = None
                            if port_defined_argument_value.VALUE.TEXT_VALUE_SPECIFICATION:
                                value_spec = port_defined_argument_value.VALUE.TEXT_VALUE_SPECIFICATION
                            elif port_defined_argument_value.VALUE.NUMERICAL_VALUE_SPECIFICATION:
                                value_spec = port_defined_argument_value.VALUE.NUMERICAL_VALUE_SPECIFICATION
                            if not value_spec:
                                continue
                            value = value_spec.VALUE.valueOf_
                            value_type_tref_value = port_defined_argument_value.VALUE_TYPE_TREF.valueOf_
                            arg_name = f"parg{para_num}"
                            category = cls.__parser_idt(ar_component_type, value_type_tref_value)[1]
                            type_name = cls.__parser_idt(ar_component_type, value_type_tref_value)[0]
                            type_name = value_type_tref_value.split("/")[-1]
                            port_def_args.update(
                                {
                                    arg_name: {
                                        "name": arg_name,
                                        "type": type_name,
                                        "category": category,
                                        "direction": "IN",
                                        "value": value,
                                        "typesize_byte_for_struct_align": cls.__get_typesize_byte_from_path_and_name(
                                            value_type_tref_value, type_name
                                        ),
                                    }
                                }
                            )
                            para_num += 1
                        pport_api_options.update({port_api_option.PORT_REF.valueOf_: port_def_args})

    @classmethod
    def __parse_dataelement_operation_modegroup_access(cls):
        port_data_element_access = {}
        port_operation_access = {}
        operation_access = {}
        server_runnable_conns = {}
        for ar_component_type in cls.sw_component_types:
            if ar_component_type.get_tag() not in cls.SUPPORT_COMPONENT_TYPE:
                continue
            cls.__parse_component_data_element_access(port_data_element_access, ar_component_type)
            cls.__parse_component_operation_access(port_operation_access, server_runnable_conns, ar_component_type)
            cls.__parse_component_mode_group_access(operation_access, ar_component_type)
            cls.__parse_component_trigger_access(port_data_element_access, ar_component_type)
        return port_data_element_access, port_operation_access, operation_access, server_runnable_conns

    @classmethod
    def get_prport_data_element_access_dict(cls):
        prport_data_element_access_dict = {}
        for ar_component_type in cls.sw_component_types:
            if ar_component_type.get_tag() not in cls.SUPPORT_COMPONENT_TYPE:
                continue
            port_data_element_access_dict = cls.__get_prport_data_element_access_dict(ar_component_type)
            prport_data_element_access_dict.update(port_data_element_access_dict)
        return prport_data_element_access_dict

    @classmethod
    def __parse_all_port_prototypes(cls):
        port_prototypes = {}
        for component_type in cls.sw_component_types:
            if component_type.get_tag() not in cls.SUPPORT_COMPONENT_TYPE:
                continue
            port_prototypes.update(cls.__parse_component_port_prototype_info(component_type))
        return port_prototypes

    @classmethod
    def __parse_component_port_prototype_info(cls, component_type):
        port_dict = {}
        if not hasattr(component_type, "PORTS") or not component_type.PORTS:
            return port_dict
        if hasattr(component_type.PORTS, "R_PORT_PROTOTYPE") and component_type.PORTS.R_PORT_PROTOTYPE:
            for rport in component_type.PORTS.R_PORT_PROTOTYPE:
                if not rport.REQUIRED_COM_SPECS:
                    continue
                port_path = rport.get_path()
                port_dict.update({port_path: {}})
                if rport.REQUIRED_COM_SPECS.QUEUED_RECEIVER_COM_SPEC:
                    for com_spec in rport.REQUIRED_COM_SPECS.QUEUED_RECEIVER_COM_SPEC:
                        port_dict[port_path].update(
                            {
                                utils.get_valueOf(com_spec.DATA_ELEMENT_REF): {
                                    "queue_size": int(utils.get_valueOf(com_spec.QUEUE_LENGTH))
                                }
                            }
                        )
                if rport.REQUIRED_COM_SPECS.NONQUEUED_RECEIVER_COM_SPEC:
                    for com_spec in rport.REQUIRED_COM_SPECS.NONQUEUED_RECEIVER_COM_SPEC:
                        enable_update = False
                        if (
                            hasattr(com_spec, "ENABLE_UPDATE")
                            and com_spec.ENABLE_UPDATE
                            and utils.get_valueOf(com_spec.ENABLE_UPDATE) == "true"
                        ):
                            enable_update = True
                        port_dict[port_path].update(
                            {utils.get_valueOf(com_spec.DATA_ELEMENT_REF): {"enable_update": enable_update}}
                        )
        if hasattr(component_type.PORTS, "P_PORT_PROTOTYPE") and component_type.PORTS.P_PORT_PROTOTYPE:
            for pport in component_type.PORTS.P_PORT_PROTOTYPE:
                if not pport.PROVIDED_COM_SPECS or not pport.PROVIDED_COM_SPECS.SERVER_COM_SPEC:
                    continue
                port_path = pport.get_path()
                port_dict.update({port_path: {}})
                for com_spec in pport.PROVIDED_COM_SPECS.SERVER_COM_SPEC:
                    if not hasattr(com_spec, "OPERATION_REF") or not com_spec.OPERATION_REF:
                        continue
                    port_dict[port_path].update(
                        {
                            utils.get_valueOf(com_spec.OPERATION_REF): {
                                "queue_size": int(utils.get_valueOf(com_spec.QUEUE_LENGTH))
                            }
                        }
                    )
        if hasattr(component_type.PORTS, "PR_PORT_PROTOTYPE") and component_type.PORTS.PR_PORT_PROTOTYPE:
            for prport in component_type.PORTS.PR_PORT_PROTOTYPE:
                port_path = prport.get_path()
                port_dict.update({port_path: {}})
                if prport.REQUIRED_COM_SPECS and prport.REQUIRED_COM_SPECS.NONQUEUED_RECEIVER_COM_SPEC:
                    for com_spec in prport.REQUIRED_COM_SPECS.NONQUEUED_RECEIVER_COM_SPEC:
                        enable_update = False
                        if (
                            hasattr(com_spec, "ENABLE_UPDATE")
                            and com_spec.ENABLE_UPDATE
                            and utils.get_valueOf(com_spec.ENABLE_UPDATE) == "true"
                        ):
                            enable_update = True
                        port_dict[port_path].update(
                            {utils.get_valueOf(com_spec.DATA_ELEMENT_REF): {"enable_update": enable_update}}
                        )
        return port_dict

    @classmethod
    def __parse_all_pport_api_options(cls):
        pport_api_options = {}
        for ar_component_type in cls.sw_component_types:
            if ar_component_type.get_tag() not in cls.SUPPORT_COMPONENT_TYPE:
                continue
            cls.__parse_component_pport_api_options(pport_api_options, ar_component_type)
        return pport_api_options

    @classmethod
    def parse_all_pport_api_options_for_compatibility(cls, sw_component_types):
        """
        获取所有api-options,用于port mapping兼容性判断

        Args:
            sw_component_types(class)

        Returns:
            pport_api_options(dict)
        """
        pport_api_options = {}
        for ar_component_type in sw_component_types:
            if ar_component_type.get_tag() not in cls.SUPPORT_COMPONENT_TYPE:
                continue
            cls.__parse_component_pport_api_options(pport_api_options, ar_component_type)
        return pport_api_options

    @classmethod
    def parse_operation_for_compatibility(cls, port_prototype, operation_path):
        """
        获取operation用于兼容性判断
        Args:
            port_prototype (class):
            operation_path (str):

        Returns:
            arg/return_type/sorted_args
        """
        args = {}
        operation = port_prototype.find(operation_path)
        if not operation or isinstance(operation, autosar44.VARIABLE_DATA_PROTOTYPE):
            return args
        if operation.ARGUMENTS is None:
            return args
        arguments = operation.ARGUMENTS.ARGUMENT_DATA_PROTOTYPE
        for argument in arguments:
            argument_name = argument.SHORT_NAME.valueOf_
            type_ref = argument.TYPE_TREF.valueOf_
            type, category = cls.__parser_idt(argument, type_ref)
            argument_dict = {
                argument_name: {
                    "name": argument_name,
                    "type": type,
                    "direction": argument.DIRECTION.valueOf_,
                    "category": category,
                    "typesize_byte_for_struct_align": cls.__get_typesize_byte_from_ar_path(type_ref),
                    "base_type": cls.get_arguement_base_type(category, type),
                    "constraint": cls.__get_constraint_for_compatibility(
                        type, argument.find(utils.get_type_tref(argument)), "CS"
                    ),
                }
            }
            if argument_dict[argument_name]["type"] == "":
                raise Exception(f"operation {operation_path} arguments {argument_name}  can not find in arxml")
            args.update(argument_dict)
        return args

    @classmethod
    def parse_de_for_compatibility(cls, data_element, port_prototype, mapping_sets, auxiliary_data):
        """
        获取data element用于兼容性判断
        Args:
            data_element (class):
            port_prototype (class):
            mapping_sets(dict):

        Returns:
            arg(dict)
        """
        arg = copy.deepcopy(cls.__parse_sr_accessed_variable_arg(data_element, port_prototype, mapping_sets, False))
        if arg.get("datatype", {}):
            arg["datatype"]["constraint"] = cls.__get_constraint_for_compatibility(arg, data_element, "SR")
        return arg

    @classmethod
    def parse_datatype_mapping_sets_for_compatibility(cls, asw_class):
        cls.datatype_mapping_sets, cls.adt_mappings = cls.__parse_datatype_mapping_sets(asw_class)

    @classmethod
    def __get_constraint_for_compatibility(cls, arg, data_element, type="SR"):
        """
        此函数用于获取参数中的约束,综合考虑basetype和element的约束
        """
        constraint = None
        idt_name = arg["datatype"]["name"] if type == "SR" else arg
        if cls.idts[idt_name]["native_category"] == "NUMERICAL" or cls.idts[idt_name]["native_category"] == "VALUE":
            constraint = cls.__get_numerical_constraint_for_compatibility(arg, idt_name, data_element, type)
        elif cls.idts[idt_name]["native_category"] == "STRUCTURE":
            constraint = cls.__get_struct_constraint_for_compatibility(arg, idt_name, data_element, type)
        elif cls.idts[idt_name]["native_category"] == "ARRAY":
            constraint = cls.__get_array_constraint_for_compatibility(arg, idt_name, data_element, type)
        elif cls.idts[idt_name]["native_category"] == "UNION":
            logger.warning(f"{idt_name} contains UNION data type which is not support yet!")
        elif cls.idts[idt_name]["native_category"] == "TYPE_REFERENCE":
            constraint = cls.__get_reference_constraint_for_compatibility(arg, idt_name, data_element, type)
        else:
            # TODO
            pass
        return constraint

    @classmethod
    def __get_reference_constraint_for_compatibility(cls, arg, idt_name, data_element, type):
        constraint = None
        if cls.idts[idt_name]["basetype"] in cls.NATIVE_DATATYPES:
            constraint = cls.__get_numerical_constraint_for_compatibility(arg, idt_name, data_element, type)
        else:
            inner_idt = cls.idts[cls.idts[idt_name]["basetype"]]
            if inner_idt["native_category"] == "STRUCTURE":
                constraint = cls.__get_struct_constraint_for_compatibility(arg, inner_idt["name"], data_element, type)
            elif inner_idt["native_category"] == "ARRAY":
                for i in range(0, cls.idts[idt_name]["size"]):
                    constraint = []
                    constraint.append(
                        cls.__get_array_constraint_for_compatibility(arg, inner_idt["name"], data_element, type)
                    )
            elif inner_idt["native_category"] == "UNION":
                # 数组元素是UNION类型暂不支持
                idt_name = inner_idt["name"]
                logger.warning(f"{idt_name} contains UNION data type which is not support yet!")
            elif inner_idt["native_category"] == "TYPE_REFERENCE":
                constraint = cls.__get_reference_constraint_for_compatibility(
                    arg, inner_idt["name"], data_element, type
                )
            else:
                # TODO
                idt_name = inner_idt["name"]
                idt_type = inner_idt["native_category"]
                logger.warning(f"{idt_name} contains {idt_type} is not support yet!")
        return constraint

    @classmethod
    def __get_array_constraint_for_compatibility(cls, arg, idt_name, data_element, type):
        constraint = []
        if cls.idts[idt_name]["basetype"] in cls.NATIVE_DATATYPES:
            for i in range(0, cls.idts[idt_name]["size"]):
                constraint.append(cls.__get_numerical_constraint_for_compatibility(arg, idt_name, data_element, type))
        else:
            inner_idt = cls.idts[cls.idts[idt_name]["basetype"]]
            if inner_idt["native_category"] in ["NUMERICAL", "VALUE"]:
                for i in range(0, cls.idts[idt_name]["size"]):
                    constraint.append(
                        cls.__get_numerical_constraint_for_compatibility(arg, inner_idt["name"], data_element, type)
                    )
            elif inner_idt["native_category"] == "STRUCTURE":
                if data_element.CATEGORY and data_element.CATEGORY.valueOf_ == "TYPE_REFERENCE":
                    ref_idt_path = (
                        data_element.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[
                            0
                        ].IMPLEMENTATION_DATA_TYPE_REF.valueOf_
                    )
                    idt_ref = data_element.find(ref_idt_path)
                elif utils.get_type_tref(data_element):
                    type_tref_de = data_element.find(utils.get_type_tref(data_element))
                    if data_element.CATEGORY and type_tref_de.CATEGORY.valueOf_ == "TYPE_REFERENCE":
                        ref_idt_path = (
                            type_tref_de.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[
                                0
                            ].IMPLEMENTATION_DATA_TYPE_REF.valueOf_
                        )
                        idt_ref = data_element.find(ref_idt_path)
                    else:
                        idt_ele = type_tref_de.SUB_ELEMENTS.IMPLEMENTATION_DATA_TYPE_ELEMENT[0]
                        idt_ref_path = (
                            idt_ele.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[
                                0
                            ].IMPLEMENTATION_DATA_TYPE_REF.valueOf_
                        )
                        idt_ref = data_element.find(idt_ref_path)
                else:
                    idt_ele = data_element.SUB_ELEMENTS.IMPLEMENTATION_DATA_TYPE_ELEMENT[0]
                    idt_ref_path = idt_ele.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[
                        0
                    ].IMPLEMENTATION_DATA_TYPE_REF.valueOf_
                    idt_ref = data_element.find(idt_ref_path)
                for i in range(0, cls.idts[idt_name]["size"]):
                    constraint.append(
                        cls.__get_struct_constraint_for_compatibility(arg, inner_idt["name"], idt_ref, type)
                    )
            elif inner_idt["native_category"] == "ARRAY":
                for i in range(0, cls.idts[idt_name]["size"]):
                    constraint.append(
                        cls.__get_array_constraint_for_compatibility(arg, inner_idt["name"], data_element, type)
                    )
            elif inner_idt["native_category"] == "UNION":
                # 数组元素是UNION类型暂不支持
                idt_name = inner_idt["name"]
                logger.warning(f"{idt_name} contains UNION data type which is not support yet!")
            elif inner_idt["native_category"] == "TYPE_REFERENCE":
                for i in range(0, cls.idts[idt_name]["size"]):
                    constraint.append(
                        cls.__get_reference_constraint_for_compatibility(arg, inner_idt["name"], data_element, type)
                    )
        return constraint

    @classmethod
    def __get_struct_constraint_for_compatibility(cls, arg, idt_name, data_element, type):
        constraint = {}
        arg_name = arg["datatype"]["name"] if type == "SR" else arg
        for member in cls.idts[idt_name]["members"]:
            if utils.get_type_tref(data_element):
                type_tref_de = data_element.find(utils.get_type_tref(data_element))
                if type_tref_de.CATEGORY and type_tref_de.CATEGORY.valueOf_ == "TYPE_REFERENCE":
                    ref_idt_path = (
                        type_tref_de.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[
                            0
                        ].IMPLEMENTATION_DATA_TYPE_REF.valueOf_
                    )
                    elements = data_element.find(ref_idt_path).SUB_ELEMENTS.IMPLEMENTATION_DATA_TYPE_ELEMENT
                else:
                    elements = type_tref_de.SUB_ELEMENTS.IMPLEMENTATION_DATA_TYPE_ELEMENT
            else:
                elements = data_element.SUB_ELEMENTS.IMPLEMENTATION_DATA_TYPE_ELEMENT
            if member["category"] == "VALUE" or member["datatype"].lower() in cls.NATIVE_DATATYPES:
                constr_max = (
                    cls.__get_constr_min_max(member["datatype"], cls.idts[member["datatype"]]["constraint"]["max"])
                    if cls.idts[member["datatype"]]["constraint"]
                    else float("INF")
                )
                constr_min = (
                    cls.__get_constr_min_max(member["datatype"], cls.idts[member["datatype"]]["constraint"]["min"])
                    if cls.idts[member["datatype"]]["constraint"]
                    else float("-INF")
                )
                constr_max1 = float("INF")
                constr_min1 = float("-INF")
                for element in elements:
                    if member["name"] == utils.get_short_name(element):
                        data_constr_ref = (
                            element.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[
                                0
                            ].DATA_CONSTR_REF
                        )
                        if data_constr_ref:
                            constr_max1 = cls.__get_constr_min_max(
                                member["datatype"], cls.constraints[utils.get_valueOf(data_constr_ref)]["max"]
                            )
                            constr_min1 = cls.__get_constr_min_max(
                                member["datatype"], cls.constraints[utils.get_valueOf(data_constr_ref)]["min"]
                            )
                        else:
                            constr_max1, constr_min1 = constr_max, constr_min
                        break
                constraint.update(
                    {member["name"]: {"max": min(constr_max, constr_max1), "min": max(constr_min, constr_min1)}}
                )
            elif member["category"] == "ARRAY":
                if member["is_user_typed"]:
                    continue
                for element in elements:
                    if member["name"] == utils.get_short_name(element):
                        if element.CATEGORY.valueOf_ == "TYPE_REFERENCE":
                            idt_ele = element.find(
                                element.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[
                                    0
                                ].IMPLEMENTATION_DATA_TYPE_REF.valueOf_
                            )
                        constraint.update(
                            {
                                member["name"]: cls.__get_array_constraint_for_compatibility(
                                    arg, member["datatype"], idt_ele, type
                                )
                            }
                        )
                        break
            elif member["category"] == "STRUCTURE":
                for element in elements:
                    if member["name"] == utils.get_short_name(element):
                        if element.CATEGORY.valueOf_ == "TYPE_REFERENCE":
                            idt_ele = element.find(
                                element.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[
                                    0
                                ].IMPLEMENTATION_DATA_TYPE_REF.valueOf_
                            )
                        constraint.update(
                            {
                                member["name"]: cls.__get_struct_constraint_for_compatibility(
                                    arg, member["datatype"], idt_ele, type
                                )
                            }
                        )
                        break
            elif member["category"] == "UNION":
                # UNION暂不支持解析, 赋空值
                constraint.update({member["name"]: None})
                logger.warning(f"{arg_name} contains UNION data type which is not support yet!")
            elif member["category"] == "TYPE_REFERENCE":
                constraint.update(
                    {
                        member["name"]: cls.__get_reference_constraint_for_compatibility(
                            arg, member["datatype"], data_element, type
                        )
                    }
                )
            else:
                # TODO
                mem_dt = member["datatype"]
                mem_cat = member["category"]
                logger.warning(f"{arg_name} contains {mem_dt} or {mem_cat} is not support yet!")
        return constraint

    @classmethod
    def __get_numerical_constraint_for_compatibility(cls, arg, idt_name, data_element, type):
        # basetype数据约束可以直接从idts中获取
        constraint = (
            copy.deepcopy(cls.idts[cls.idts[idt_name]["basetype"]]["constraint"])
            if cls.idts[idt_name]["basetype"] in cls.idts
            else {}
        )
        constr_max = (
            cls.__get_constr_min_max(cls.idts[idt_name]["basetype"], constraint["max"]) if constraint else float("INF")
        )
        constr_min = (
            cls.__get_constr_min_max(cls.idts[idt_name]["basetype"], constraint["min"]) if constraint else float("-INF")
        )
        constraint.update({"max": constr_max, "min": constr_min})
        # 如果element和basetype同时有约束，取element处的约束
        if data_element:
            cls.__update_constraint_of_input(data_element, arg, cls.idts[idt_name]["basetype"], constraint)
        return constraint

    @classmethod
    def __update_constraint_of_input(cls, ar_in, arg, idt_name, constraint):
        constraint_path = None
        if not ar_in:
            return
        try:
            constraint_path = utils.get_valueOf(
                ar_in.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[0].DATA_CONSTR_REF
            )
        except Exception:
            pass
        if constraint_path in cls.constraints:
            if type(arg) is dict and "constraint" not in arg["datatype"]:
                arg["datatype"].update({"constraint": {}})
            constr_max = cls.__get_constr_min_max(idt_name, cls.constraints[constraint_path]["max"])
            constr_min = cls.__get_constr_min_max(idt_name, cls.constraints[constraint_path]["min"])
            if constraint.get("max", None) is None or constr_max < constraint["max"]:
                constraint.update({"max": constr_max})
            if constraint.get("min", None) is None or constr_min > constraint["min"]:
                constraint.update({"min": constr_min})
        # TODO: compumethod of ADT

    @classmethod
    def __get_constr_min_max(cls, idt_name, constr):
        rv = 0
        """
        constraint中min/max为字符串,将其转换为数值,便于后续的比对
        """
        if constr in ["INF", "-INF", float("INF"), -float("INF")]:
            rv = float(constr)
        else:
            de_basetype = cls.idts[idt_name]["basetype"]
            if "float" in de_basetype.lower():
                rv = float(constr)
            elif "sint" in de_basetype.lower() or "uint" in de_basetype.lower() or "bool" in de_basetype.lower():
                rv = int(constr)
            elif "void" in de_basetype.lower():
                pass
        return rv

    @classmethod
    def get_all_constraints_for_compatibility(cls, ar_asw):
        """
        获取所有的约束用于兼容性判断
        Args:
            ar_asw (class):

        Returns:
            constrs(dict)
        """
        cls.constraints = cls.__parse_all_data_constraints(ar_asw)

    @classmethod
    def get_idts_for_compatibility(cls, ar_asw):
        """
        获取所有的idts用于兼容性判断
        Args:
            ar_asw (class):

        Returns:
            idts(dict)
        """
        cls.idts, _, cls.datatype_path_to_idt_mapping = cls.__parse_all_idts_and_dependency(ar_asw)

    @classmethod
    def get_arg_base_type(cls, arg_name):
        """
        此函数用于获取参数中真正的basetype
        Args:
            arg_name (str): 入参为operation/data element中arg name

        Returns:
            arg_basetype[str/list/dict]
        """
        arg_basetype = None
        if cls.idts[arg_name]["native_category"] in ["NUMERICAL", "VALUE"]:
            arg_basetype = cls.idts[arg_name]["basetype"]
        elif cls.idts[arg_name]["native_category"] == "STRUCTURE":
            arg_basetype = cls.get_arg_base_type_of_struct(arg_name)
        elif cls.idts[arg_name]["native_category"] == "ARRAY":
            arg_basetype = cls.get_arg_base_type_of_array(arg_name)
        elif cls.idts[arg_name]["native_category"] == "UNION":
            arg_basetype = cls.get_arg_base_type_of_union(arg_name)
        elif cls.idts[arg_name]["native_category"] == "TYPE_REFERENCE":
            arg_basetype = cls.get_arg_base_type_of_reference(arg_name)
        else:
            # TODO
            pass
        return arg_basetype

    @classmethod
    def get_arg_base_type_of_union(cls, arg_name):
        """
        获取真正的basetype
        """
        basetype = None
        member = cls.idts[arg_name]["members"][0]  # the first member is used to init-value codegen
        if member["category"] == "VALUE" or member["datatype"].lower() in cls.NATIVE_DATATYPES:
            basetype = cls.idts[member["datatype"]]["basetype"]
        elif member["category"] == "ARRAY":
            basetype = []
            basetype = cls.get_arg_base_type_of_array(member["datatype"])
        elif member["category"] == "STRUCTURE":
            basetype = {}
            basetype = cls.get_arg_base_type_of_struct(member["datatype"])
        elif member["category"] == "UNION":
            basetype = cls.get_arg_base_type_of_union(member["datatype"])
        elif member["category"] == "TYPE_REFERENCE":
            basetype = cls.get_arg_base_type_of_reference(member["datatype"])
        else:
            # TODO
            mem_dt = member["datatype"]
            mem_cat = member["category"]
            logger.warning(f"{arg_name} contains {mem_dt} or {mem_cat} is not support yet!")
        return basetype

    @classmethod
    def get_arg_base_type_of_array(cls, arg_name):
        """
        获取真正的basetype
        """
        basetype = []
        if not arg_name:
            return basetype
        if cls.idts[arg_name]["basetype"] in cls.NATIVE_DATATYPES:
            for i in range(0, cls.idts[arg_name]["size"]):
                basetype.append(cls.idts[arg_name]["basetype"])
        else:
            inner_idt = cls.idts[cls.idts[arg_name]["basetype"]]
            if inner_idt["native_category"] in ["NUMERICAL", "VALUE"]:
                for i in range(0, cls.idts[arg_name]["size"]):
                    basetype.append(inner_idt["basetype"])
            elif inner_idt["native_category"] == "STRUCTURE":
                for i in range(0, cls.idts[arg_name]["size"]):
                    basetype.append(cls.get_arg_base_type_of_struct(inner_idt["name"]))
            elif inner_idt["native_category"] == "ARRAY":
                for i in range(0, cls.idts[arg_name]["size"]):
                    basetype.append(cls.get_arg_base_type_of_array(inner_idt["name"]))
            elif inner_idt["native_category"] == "UNION":
                basetype.append(cls.get_arg_base_type_of_union(inner_idt["name"]))
            elif inner_idt["native_category"] == "TYPE_REFERENCE":
                for i in range(0, cls.idts[arg_name]["size"]):
                    basetype.append(cls.get_arg_base_type_of_reference(inner_idt["name"]))
            else:
                # TODO
                idt_name = inner_idt["name"]
                idt_type = inner_idt["native_category"]
                logger.warning(f"{idt_name} contains {idt_type} is not support yet!")
        return basetype

    @classmethod
    def get_arg_base_type_of_struct(cls, arg_name):
        """
        获取真正的basetype
        """
        basetype = {}
        for member in cls.idts[arg_name]["members"]:
            if member["category"] == "VALUE" or member["datatype"].lower() in cls.NATIVE_DATATYPES:
                basetype.update({member["name"]: cls.idts[member["datatype"]]["basetype"]})
            elif member["category"] == "ARRAY":
                basetype.update({member["name"]: cls.get_arg_base_type_of_array(member["datatype"])})
            elif member["category"] == "STRUCTURE":
                basetype.update({member["name"]: cls.get_arg_base_type_of_struct(member["datatype"])})
            elif member["category"] == "UNION":
                basetype.update({member["name"]: cls.get_arg_base_type_of_union(member["datatype"])})
            elif member["category"] == "TYPE_REFERENCE":
                basetype.update({member["name"]: cls.get_arg_base_type_of_reference(member["datatype"])})
            else:
                # TODO
                mem_dt = member["datatype"]
                mem_cat = member["category"]
                logger.warning(f"{arg_name} contains {mem_dt} or {mem_cat} is not support yet!")
        return basetype

    @classmethod
    def get_arg_base_type_of_reference(cls, arg_name):
        basetype = None
        if cls.idts[arg_name]["basetype"] in cls.NATIVE_DATATYPES:
            basetype = cls.idts[arg_name]["basetype"]
        else:
            inner_idt = cls.idts[cls.idts[arg_name]["basetype"]]
            if inner_idt["native_category"] == "STRUCTURE":
                basetype = cls.get_arg_base_type_of_struct(inner_idt["name"])
            elif inner_idt["native_category"] == "ARRAY":
                for i in range(0, cls.idts[arg_name]["size"]):
                    basetype = []
                    basetype.append(cls.get_arg_base_type_of_array(inner_idt["name"]))
            elif inner_idt["native_category"] == "UNION":
                basetype = cls.get_arg_base_type_of_union(inner_idt["name"])
            elif inner_idt["native_category"] == "TYPE_REFERENCE":
                basetype = cls.get_arg_base_type_of_reference(inner_idt["name"])
            else:
                # TODO
                idt_name = inner_idt["name"]
                idt_type = inner_idt["native_category"]
                logger.warning(f"{idt_name} contains {idt_type} is not support yet!")
        return basetype

    @classmethod
    def __parse_asw_runnable_events_dict(cls):
        events_dict = {}
        for sw_component in cls.sw_component_types:
            for behavior in getattr(getattr(sw_component, "INTERNAL_BEHAVIORS", None), "SWC_INTERNAL_BEHAVIOR", []):
                if not behavior.EVENTS:
                    continue
                events = []
                for key in cls.RUNNABLE_EVENT_TYPE.keys():
                    events.extend(getattr(behavior.EVENTS, key.replace("-", "_")))
                for event in events:
                    tag = event.get_tag()
                    event_ref = event.get_path()
                    # exclude S/R queue waitpoint
                    if not event.START_ON_EVENT_REF:
                        continue
                    runnable = event.find(event.START_ON_EVENT_REF.valueOf_)
                    runnable_symbol = utils.get_runnable_symbol(runnable)
                    port_dataelement_name = ""
                    if tag == "DATA-RECEIVED-EVENT":
                        port_dataelement_name = (
                            event.DATA_IREF.CONTEXT_R_PORT_REF.valueOf_.split("/")[-1]
                            + "_"
                            + event.DATA_IREF.TARGET_DATA_ELEMENT_REF.valueOf_.split("/")[-1]
                        )
                    elif tag == "OPERATION-INVOKED-EVENT":
                        port_name = event.OPERATION_IREF.CONTEXT_P_PORT_REF.valueOf_.split("/")[-1]
                        operation_name = event.OPERATION_IREF.TARGET_PROVIDED_OPERATION_REF.valueOf_.split("/")[-1]
                        port_operation_name = f"{port_name}_{operation_name}"
                        port_dataelement_name = port_operation_name
                    elif tag in {"DATA-SEND-COMPLETED-EVENT", "DATA-WRITE-COMPLETED-EVENT"}:
                        event_source_ref = event.EVENT_SOURCE_REF
                        event_source_dict = cls.__parse_event_source_ref(event_source_ref)
                        port_dataelement_name = (
                            event_source_dict["port_name"] + "_" + event_source_dict["data_element_name"]
                        )
                    elif tag == "INTERNAL-TRIGGER-OCCURRED-EVENT":
                        itp = event.EVENT_SOURCE_REF.valueOf_.split("/")[-1]
                        trigger_runnable_path = "/".join(event.EVENT_SOURCE_REF.valueOf_.split("/")[:-1])
                        trigger_runnable_obj = event.find(trigger_runnable_path)
                        trigger_runnable_symbol = utils.get_runnable_symbol(trigger_runnable_obj)
                        port_dataelement_name = trigger_runnable_symbol + "_" + itp
                    elif tag == "EXTERNAL-TRIGGER-OCCURRED-EVENT":
                        port = event.TRIGGER_IREF.CONTEXT_R_PORT_REF.valueOf_.split("/")[-1]
                        trigger = event.TRIGGER_IREF.TARGET_TRIGGER_REF.valueOf_.split("/")[-1]
                        port_dataelement_name = port + "_" + trigger
                    if runnable_symbol not in events_dict:
                        events_dict[runnable_symbol] = {}
                    events_dict[runnable_symbol][event_ref] = port_dataelement_name
                # TODO: other event
        return events_dict

    @classmethod
    def __parse_event_source_ref(cls, ar_event_source_ref):
        event_source = {"dest": "", "port_name": "", "data_element_name": ""}
        if (
            ar_event_source_ref and ar_event_source_ref.DEST and ar_event_source_ref.DEST == "VARIABLE-ACCESS"
        ):  # data send point
            event_source_ref_value = ar_event_source_ref.valueOf_
            ar_event_source = ar_event_source_ref.find(event_source_ref_value)  # ACCESSED-VARIABLE
            if ar_event_source and hasattr(ar_event_source, "ACCESSED_VARIABLE") and ar_event_source.ACCESSED_VARIABLE:
                accessed_variable = ar_event_source.ACCESSED_VARIABLE
                if hasattr(accessed_variable, "AUTOSAR_VARIABLE_IREF"):
                    autosar_variable_iref = accessed_variable.AUTOSAR_VARIABLE_IREF
                    port_prototype_ref = autosar_variable_iref.PORT_PROTOTYPE_REF
                    target_data_prototype_ref = autosar_variable_iref.TARGET_DATA_PROTOTYPE_REF

                    port_prototype_ref_value = port_prototype_ref.valueOf_
                    target_data_prototype_ref_value = target_data_prototype_ref.valueOf_

                    port_prototype = ar_event_source_ref.find(port_prototype_ref_value)
                    target_data_prototype = ar_event_source_ref.find(target_data_prototype_ref_value)

                    port_name = utils.get_short_name(port_prototype)
                    data_element_name = utils.get_short_name(target_data_prototype)

                    event_source["dest"] = "VARIABLE-ACCESS"
                    event_source["port_name"] = port_name
                    event_source["data_element_name"] = data_element_name
        return event_source

    @classmethod
    def __parse_runnables_task_and_event(cls):
        """
        Parse and get all runnables' task and event info

        Arg:
        task_mappings: task mapping info parsed by Task Mapping

        Return:
        a dictionary of all runnables' task and event info
        """
        runnable_tasks = {}
        runnable_events = {}
        port_events = {}
        for task_name, task in cls.task_mappings.items():
            for runnable in task["schedulable_entity_info_list"]:
                runnable_tasks[runnable["name"]] = task_name

                if runnable["event_type"] not in cls.RUNNABLE_EVENT_TYPE.values():
                    continue

                event_port = cls.asw_events.get(runnable["name"], {}).get(runnable["event_ref"])
                evt_info = {
                    "task_name": task_name,
                    "task_id": f"Os_Task_{task_name}_ID",
                    "event_mask": runnable["event_mask"],
                    "event_type": runnable["event_type"],
                    "event_key": f"{task_name}_{runnable['event_mask']}",
                }

                if runnable["name"] not in runnable_events:
                    runnable_events[runnable["name"]] = {}
                runnable_events[runnable["name"]][event_port] = evt_info

                if event_port not in port_events:
                    port_events[event_port] = {}
                port_events[event_port][runnable["name"]] = evt_info

        return runnable_tasks, runnable_events, port_events

    @classmethod
    def __parse_runnables_exclusive_areas(cls):
        """
        Parse and get all runnables' task and event info

        Arg:
        task_mappings: task mapping info parsed by Task Mapping

        Return:
        a dictionary of all runnables' task and event info
        """
        exclusive_areas = {}
        for task in cls.task_mappings.values():
            for runnable in task["schedulable_entity_info_list"]:
                exclusive_areas[runnable["name"]] = runnable["exclusive_areas"]
        return exclusive_areas

    @classmethod
    def __parse_sr_port_wait_events(cls, port):
        wait_events = []
        for runnable_symbol in port["runnable"]:
            if runnable_symbol not in cls.runnable_events:
                continue
            event = cls.runnable_events.get(runnable_symbol, {}).get(port["name"])
            if event:
                wait_events.append(
                    {
                        "task_name": event["task_name"],
                        "task_id": event["task_id"],
                        "event_mask": event["event_mask"],
                        "event_type": event["event_type"],
                        "event_key": event["event_key"],
                    }
                )
        return wait_events

    @classmethod
    def __parse_sr_port_set_events_by_connected_ports(cls, connected_ports, port_name=None):
        """
        Parse the specified S/R P-Port's setevent info

        Arg:
            connected_ports: the specified S/R P-Port's connected ports got by parse_pport_connected_ports
            task_mappings: task mapping info parsed by Task Mapping

        Return:
        a list of the specified pport's setevent info
        """
        set_events = []
        for connected_port in connected_ports["ports"]:
            if connected_port["access_type"] == "Receive" and connected_port["timeout"] > 0:
                set_events.append(
                    {
                        "task_id": f'Os_Task_{connected_port["task"]}_ID',
                        "event_mask": f'Rte_Ev_WaitPoint_{connected_port["task"]}',
                    }
                )
            else:
                runnable_symbol = connected_port["symbol"]
                if runnable_symbol not in cls.runnable_events:
                    continue
                event = cls.runnable_events.get(runnable_symbol, {}).get(connected_port["name"])
                if event:
                    set_events.append(
                        {"task_id": "Os_Task_" + event["task_name"] + "_ID", "event_mask": event["event_mask"]}
                    )

        # Add Pport set event
        if port_name is None:
            return set_events
        for events in cls.runnable_events.values():
            event = events.get(port_name)
            if event and event["event_type"] in {
                "DataSendCompletedEvent",
                "DataWriteCompletedEvent",
                "InternalTriggerOccurredEvent",
                "ExternalTriggerOccurredEvent",
            }:
                set_events.append(
                    {"task_id": "Os_Task_" + event["task_name"] + "_ID", "event_mask": event["event_mask"]}
                )
        return set_events

    @classmethod
    def __parse_cs_port_set_events_by_connected_ports(cls, connected_ports):
        set_events = []
        for connected_port in connected_ports["ports"]:
            runnable_symbol = connected_port["symbol"]
            if runnable_symbol not in cls.runnable_events:
                continue
            event = cls.runnable_events.get(runnable_symbol, {}).get(connected_port["name"])
            if event:
                set_events.append(
                    {"task_id": "Os_Task_" + event["task_name"] + "_ID", "event_mask": event["event_mask"]}
                )
        return set_events

    @classmethod
    def parse_sw_component_type_runnable(cls, sw_component_type, runnable_entity, swc_internal_behavior):
        args, return_type, _ = cls.parse_runnable_args(runnable_entity, sw_component_type, swc_internal_behavior)
        runnable_dict = {}
        runnable_dict["has_mode_disbaling"] = False
        runnable_dict["args"] = args
        runnable_dict["return_type"] = return_type
        runnable_dict["name"] = utils.get_runnable_symbol(runnable_entity)
        runnable_dict["component"] = utils.get_short_name(sw_component_type)
        runnable_dict["exclusive_areas"] = cls.exclusive_areas.get(runnable_dict["name"])
        period, trigger_event = cls.parse_period_trigger_event(runnable_entity, swc_internal_behavior)
        runnable_dict["period"] = period
        runnable_dict["trigger_event"] = trigger_event
        runnable_dict["nvblock_descriptor"] = None
        runnable_dict["storing_way"] = None
        runnable_dict["osapplication"] = (
            cls.component_osapplications[utils.get_short_name(sw_component_type)]
            if utils.get_short_name(sw_component_type) in cls.component_osapplications
            else None
        )
        activation_reasons = getattr(
            getattr(runnable_entity, "ACTIVATION_REASONS", object()), "EXECUTABLE_ENTITY_ACTIVATION_REASON", []
        )
        if len(activation_reasons) > 0:
            runnable_dict["args"].update(
                {
                    "activationVector": {
                        "name": "activationVector",
                        "type": f"Rte_ActivatingEvent_{utils.get_short_name(runnable_entity)}",
                        "direction": "IN",
                    }
                }
            )
        runnable_dict["internal_trigger"] = cls.parse_internal_trigger_points(
            utils.get_short_name(sw_component_type), runnable_entity, swc_internal_behavior
        )
        return runnable_dict

    @classmethod
    def parse_internal_trigger_points(cls, swc_type, runnable_entity, swc_internal_behavior):
        rv = []
        if not swc_internal_behavior.EVENTS or not swc_internal_behavior.EVENTS.INTERNAL_TRIGGER_OCCURRED_EVENT:
            return rv
        runnable_name = utils.get_short_name(runnable_entity)
        runnable_symbol = utils.get_runnable_symbol(runnable_entity)
        for event in swc_internal_behavior.EVENTS.INTERNAL_TRIGGER_OCCURRED_EVENT:
            runnable_path = utils.get_valueOf(event.START_ON_EVENT_REF)
            runnable_obj = swc_internal_behavior.find(runnable_path)
            triggered_runnable = utils.get_runnable_symbol(runnable_obj)
            itp_path = utils.get_valueOf(event.EVENT_SOURCE_REF)
            trigger_type = utils.get_valueOf(swc_internal_behavior.find(itp_path).SW_IMPL_POLICY)
            trigger_runnable_name, internal_trigger_point = itp_path.split("/")[-2:]
            runnable_trigger = runnable_symbol + "_" + internal_trigger_point
            if triggered_runnable not in cls.runnable_events:
                continue
            task_name = cls.runnable_events[triggered_runnable].get(runnable_trigger, {}).get("task_name", None)
            event_mask = cls.runnable_events[triggered_runnable].get(runnable_trigger, {}).get("event_mask", None)
            if trigger_runnable_name != runnable_name:
                continue
            rv.append(
                {
                    "trigger_runnable": runnable_symbol,
                    "trigger_point": internal_trigger_point,
                    "trigger_type": trigger_type,
                    "triggered_runnable": triggered_runnable,
                    "task_id": "Os_Task_" + task_name + "_ID" if task_name else None,
                    "event_mask": event_mask,
                    "swc_prototype": (
                        cls.sw_component_prototypes[swc_type][0]
                        if swc_type in cls.sw_component_prototypes
                        else swc_type
                    ),
                }
            )
        all_used_itps_path = cls.__get_swc_all_event_source_ref(swc_internal_behavior)
        all_itps_path = cls.__get_runnable_all_internal_trigger_point(runnable_entity)
        for itp_path in all_itps_path:
            if itp_path in all_used_itps_path:
                continue
            trigger_runnable_name, internal_trigger_point = itp_path.split("/")[-2:]
            trigger_type = utils.get_valueOf(swc_internal_behavior.find(itp_path).SW_IMPL_POLICY)
            rv.append(
                {
                    "trigger_runnable": runnable_symbol,
                    "trigger_point": internal_trigger_point,
                    "trigger_type": trigger_type,
                    "triggered_runnable": None,
                    "task_id": None,
                    "event_mask": None,
                    "swc_prototype": (
                        cls.sw_component_prototypes[swc_type][0]
                        if swc_type in cls.sw_component_prototypes
                        else swc_type
                    ),
                }
            )
        return rv

    @classmethod
    def __get_swc_all_event_source_ref(cls, swc_internal_behavior):
        # get all used internal point triggers in current swc
        rv = set()
        for event in swc_internal_behavior.EVENTS.INTERNAL_TRIGGER_OCCURRED_EVENT:
            itp_path = utils.get_valueOf(event.EVENT_SOURCE_REF)
            rv.add(itp_path)
        return rv

    @classmethod
    def __get_runnable_all_internal_trigger_point(cls, runnable_entity):
        # get all internal point triggers in current runnable
        rv = set()
        itps = getattr(
            getattr(runnable_entity, "INTERNAL_TRIGGERING_POINTS", object()), "INTERNAL_TRIGGERING_POINT", []
        )
        for itp in itps:
            rv.add(itp.get_path())
        return rv

    @classmethod
    def __parse_run_operation_map(cls):
        for operation_info in cls.port_operation_access.values():
            for start_on_event_ref, access_info in operation_info.items():
                cls.run_operation_map[start_on_event_ref] = access_info

    @classmethod
    def parse_runnable_args(cls, runnable_entity, sw_component_type, swc_internal_behavior):
        port_ref = None

        operation_path = None
        op_info = cls.run_operation_map.get(runnable_entity.get_path(), {})
        if op_info:
            operation_path = op_info["original_operation_ref"]

        # for swc_runnable_map in cls.operation_access.values():
        #     if "original_target_operation_ref" not in swc_runnable_map:
        #         continue
        #     if swc_name in swc_runnable_map["p_access_runnable"]:
        #         for run_port in swc_runnable_map["p_access_runnable"][swc_name]:
        #             if runnable_entity.get_path() in run_port:
        #                 operation_path = swc_runnable_map["original_target_operation_ref"]
        #                 break
        #         if operation_path:
        #             break
        is_main_function = True
        runnable_entity_ref = runnable_entity.get_path()
        if hasattr(swc_internal_behavior.EVENTS, "OPERATION_INVOKED_EVENT"):
            operation_invoked_events = swc_internal_behavior.EVENTS.OPERATION_INVOKED_EVENT
            for operation_invoked_event in operation_invoked_events:
                if utils.get_start_on_event_ref(operation_invoked_event) != runnable_entity_ref:
                    continue
                is_main_function = False
                opreation_ref = operation_invoked_event.OPERATION_IREF.TARGET_PROVIDED_OPERATION_REF.valueOf_
                if operation_path and "/".join(opreation_ref.split("/")[-2:]) == "/".join(
                    operation_path.split("/")[-2:]
                ):
                    if not runnable_entity.find(operation_path):
                        break
                    port_ref = operation_invoked_event.OPERATION_IREF.CONTEXT_P_PORT_REF.valueOf_
                    if port_ref and port_ref in cls.p_connections:
                        break
        # if runnable has triggered event but not valid interface found,should not generate runnable declaration
        if is_main_function:
            return {}, "void", {}
        if port_ref is None:
            return {}, "", {}
        return cls.__parse_operation_for_runnable(runnable_entity, operation_path, port_ref)

    @classmethod
    def parse_sw_component_type_runnables(cls, sw_component_type):
        runnables_dict = {}
        if not hasattr(sw_component_type, "INTERNAL_BEHAVIORS"):
            return runnables_dict
        swc_internal_behaviors = sw_component_type.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR
        for swc_internal_behavior in swc_internal_behaviors:
            if not swc_internal_behavior.RUNNABLES:
                return runnables_dict
            runnable_entitys = swc_internal_behavior.RUNNABLES.RUNNABLE_ENTITY
            for runnable_entity in runnable_entitys:
                runnable_dict = cls.parse_sw_component_type_runnable(
                    sw_component_type, runnable_entity, swc_internal_behavior
                )
                if runnable_dict["args"] is None:
                    continue
                runnables_dict.update({runnable_dict["name"]: runnable_dict})
        return runnables_dict

    @classmethod
    def parse_mode_switch_pport(cls, mode_switch_point, sw_component_type, ar_runnable):
        swc_name = utils.get_short_name(sw_component_type)
        runnable_symbol = utils.get_runnable_symbol(ar_runnable)
        mode_group_iref = mode_switch_point.MODE_GROUP_IREF
        context_p_port_ref = mode_group_iref.CONTEXT_P_PORT_REF.valueOf_
        context_p_port = sw_component_type.find(context_p_port_ref)
        target_mode_group_ref = mode_group_iref.TARGET_MODE_GROUP_REF.valueOf_
        target_mode_group = sw_component_type.find(target_mode_group_ref)
        if not target_mode_group or not context_p_port:
            return {}
        pport_name = utils.get_short_name(context_p_port)
        mode_group_prototype_name = utils.get_short_name(target_mode_group)
        combined_port_name = f"{pport_name}_{mode_group_prototype_name}"
        if target_mode_group_ref not in cls.operation_access:
            logger.debug(f"{target_mode_group_ref} do not exsist !")
            return {}
        if (
            swc_name not in cls.operation_access[target_mode_group_ref]["r_access_runnable"]
            and swc_name not in cls.operation_access[target_mode_group_ref]["p_access_runnable"]
        ):
            return {}
        data_element_p_access = cls.operation_access[target_mode_group_ref]["p_access_runnable"]
        data_element_r_access = cls.operation_access[target_mode_group_ref]["r_access_runnable"]
        if len(data_element_p_access) == 0:
            logger.debug(f"{target_mode_group_ref} do not accessed by any runnables !")
            return {}
        if len(data_element_r_access) == 0:
            # logger.debug(f"{target_mode_group_ref} do not used by any runnables !")
            pass
        # get mode group name
        ar_target_mode_group_ref = target_mode_group.TYPE_TREF.valueOf_
        ar_target_mode_group_name = utils.get_short_name(sw_component_type.find(ar_target_mode_group_ref))
        if not ar_target_mode_group_name:
            logger.debug(f"{ar_target_mode_group_ref} not defined !")
            return {}
        pport_osapplication = cls.__parse_sw_component_type_osapplication(swc_name)
        pport_core_id = cls.__parse_sw_component_type_core_id(swc_name)
        swc_mode_switch_event, connected_port_path_list = cls.__get_mode_switch_event_for_pport(
            data_element_p_access, data_element_r_access, swc_name, context_p_port_ref
        )
        # judge if cross partition
        inter_partition = False
        connected_osapplication = None
        for connected_swc_port in connected_port_path_list:
            connected_osapplication = (
                cls.component_osapplications[connected_swc_port[0]]
                if connected_swc_port[0] in cls.component_osapplications
                else None
            )
            if pport_osapplication and connected_osapplication and connected_osapplication != pport_osapplication:
                inter_partition = True
        # get init name

        init_mode_name = None
        if ar_target_mode_group_name not in cls.mode_groups:
            logger.debug(f"{ar_target_mode_group_name} can not find in mode_groups !")
            return {}
        init_mode_dict = cls.mode_groups[ar_target_mode_group_name]["initial_mode"]

        for name, value in init_mode_dict.items():
            init_mode_name = name

        # get queue length
        queue_length = "1"
        use_mode_switched_ack = False
        if context_p_port.PROVIDED_COM_SPECS:
            com_specs = context_p_port.PROVIDED_COM_SPECS.MODE_SWITCH_SENDER_COM_SPEC
            if com_specs and len(com_specs) >= 1:
                com_spec = com_specs[0]
                queue_length = com_spec.QUEUE_LENGTH.valueOf_ if com_spec.QUEUE_LENGTH else "1"
                # only support parser one mode group for each port interface
                if com_spec.MODE_SWITCHED_ACK:
                    use_mode_switched_ack = True

        # get event triggered by this mode machine, all events must mapped in one task.
        # this information getted by TaskMpping
        pport_dict = {
            "name": combined_port_name,
            "queue_length": int(queue_length),
            "mode_group_prototype": mode_group_prototype_name,
            "port_name": pport_name,
            "swc_name": swc_name,
            "on_transition_mode": (
                cls.mode_groups[ar_target_mode_group_name]["on_tansition_value"]
                if "on_tansition_value" in cls.mode_groups[ar_target_mode_group_name]
                else None
            ),
            "mode_group_len": cls.mode_groups[ar_target_mode_group_name]["mode_group_len"],
            "mode_group_category": cls.mode_groups[ar_target_mode_group_name]["category"],
            "swc_mode_switch_event": swc_mode_switch_event,
            "mode_switched_ack": use_mode_switched_ack,
            "type": "ModeSwitch",
            "connected_port_path_list": connected_port_path_list,
            "mode_group": ar_target_mode_group_name,
            "init_mode": init_mode_name,
            "task": cls.runnable_tasks.get(runnable_symbol) if cls.runnable_tasks else None,
            "osapplication": pport_osapplication,
            "inter_partition": inter_partition,
            "connected_osapplication": connected_osapplication,
            "port_interface_type": "mode",
            "port_path": context_p_port_ref,
            "mode_disabled_entity": {},
            "mode_disabled_flag": {},
            "core_id": pport_core_id,
        }
        return {combined_port_name: pport_dict}

    @classmethod
    def parse_external_trigger_pport(cls, external_triggering_point, type, ar_runnable):
        rv = {}
        trigger_iref = external_triggering_point.TRIGGER_IREF
        trigger_path = utils.get_target_trigger_ref(trigger_iref.P_TRIGGER_IN_ATOMIC_SWC_TYPE_INSTANCE_REF)
        trigger_name = trigger_path.split("/")[-1]
        trigger_type = utils.get_valueOf(external_triggering_point.find(trigger_path).SW_IMPL_POLICY)
        pport_path = utils.get_context_p_port_ref(trigger_iref.P_TRIGGER_IN_ATOMIC_SWC_TYPE_INSTANCE_REF)
        ar_port = external_triggering_point.find(pport_path)
        swc_type, pport_name = pport_path.split("/")[-2:]  # swc type
        swc_prototype = (
            cls.sw_component_prototypes[swc_type][0] if swc_type in cls.sw_component_prototypes else swc_type
        )  # swc prototype
        pport_var = pport_name + "_" + trigger_name
        runnable_symbol = utils.get_runnable_symbol(ar_runnable)

        pport_dict = {
            "sort_name": f"{swc_prototype}_{pport_var}",
            "name": pport_var,
            "port_prototype": pport_name,
            "data_element": trigger_name,
            "data_element_type": trigger_type,
            "type": type,
            "swc_prototype": swc_prototype,
            "symbol": [runnable_symbol],
            "task": [],  # DONOT use None!
            "connected_ports": None,
            "set_events": [],
            "osapplication": None,
            "core_id": None,
        }

        try:
            pport_dict["core_id"] = cls.__parse_sw_component_type_core_id(swc_type)
            pport_dict["osapplication"] = cls.__parse_sw_component_type_osapplication(swc_type)
            pport_dict["task"] = [cls.runnable_tasks[runnable_symbol]] if runnable_symbol in cls.runnable_tasks else []
        except Exception:
            # validation do the check
            pass

        # unconnected pport
        if pport_path in cls.p_connections:
            connected_ports = {}
            connected_ports = cls.__parse_sr_pport_connected_ports(ar_port, trigger_path)
            pport_dict["connected_ports"] = connected_ports
            if connected_ports:
                set_events = cls.__parse_sr_port_set_events_by_connected_ports(connected_ports, pport_var)
                pport_dict["set_events"] = cls.remove_duplicate_dicts(set_events)  # 去重
        rv.update({pport_var: pport_dict})
        return rv

    @classmethod
    def remove_duplicate_dicts(cls, list_of_dicts):
        """
        去除列表中重复的字典。
        """
        rv = set()
        return [d for d in list_of_dicts if not (tuple(d.items()) in rv or rv.add(tuple(d.items())))]

    @classmethod
    def parse_external_trigger_rport(cls, rport_prototype, type):
        rv = {}
        if not hasattr(rport_prototype, "REQUIRED_INTERFACE_TREF") or not rport_prototype.REQUIRED_INTERFACE_TREF:
            return rv
        port_interface_ref = utils.get_valueOf(rport_prototype.REQUIRED_INTERFACE_TREF)
        port_interface = rport_prototype.find(port_interface_ref)
        if not port_interface or not hasattr(port_interface, "TRIGGERS"):
            return rv
        rport_path = rport_prototype.get_path()
        swc_type, rport_name = rport_path.split("/")[-2:]
        swc_prototype = (
            cls.sw_component_prototypes[swc_type][0] if swc_type in cls.sw_component_prototypes else swc_type
        )  # swc prototype
        for trigger in port_interface.TRIGGERS.TRIGGER:
            trigger_path = trigger.get_path()
            trigger_name = utils.get_short_name(trigger)
            trigger_type = utils.get_valueOf(trigger.SW_IMPL_POLICY)
            rport_var = rport_name + "_" + trigger_name
            port_trigger_key = f"{rport_path}{trigger_path}"
            if port_trigger_key not in cls.port_data_element_access:
                # unaccess trigger element
                continue
            for runnable_path, _ in cls.port_data_element_access[port_trigger_key].items():
                ar_runnable = rport_prototype.find(runnable_path)
                runnable_symbol = utils.get_runnable_symbol(ar_runnable)

            rport_dict = {
                "sort_name": f"{swc_prototype}_{rport_var}",
                "name": rport_var,
                "port_prototype": rport_name,
                "data_element": trigger_name,
                "data_element_type": trigger_type,
                "type": type,
                "swc_prototype": swc_prototype,
                "symbol": [runnable_symbol],
                "task": [],  # DONOT use None!
                "connected_ports": None,
                "set_events": [],
                "osapplication": None,
                "core_id": None,
            }

            try:
                rport_dict["core_id"] = cls.__parse_sw_component_type_core_id(swc_type)
                rport_dict["osapplication"] = cls.__parse_sw_component_type_osapplication(swc_type)
                rport_dict["task"] = (
                    [cls.runnable_tasks[runnable_symbol]] if runnable_symbol in cls.runnable_tasks else []
                )
            except Exception:
                # validation do the check
                pass

            if rport_path in cls.r_connections:
                connected_ports = {}
                if rport_path in cls.r_connections:
                    connected_ports = cls.__parse_sr_rport_connected_ports(rport_prototype, trigger_path)
                rport_dict["connected_ports"] = connected_ports
            rv.update({rport_var: rport_dict})
        return rv

    @classmethod
    def parse_cal_prm_port(cls, port_prototype, sw_component_type):
        rv = {}
        param_req_com_spec_s = getattr(
            getattr(port_prototype, "REQUIRED_COM_SPECS", None), "PARAMETER_REQUIRE_COM_SPEC", None
        )
        if param_req_com_spec_s:
            for param_req_com_spec in param_req_com_spec_s:
                swc_type = utils.get_short_name(sw_component_type)
                swc_name = (
                    cls.sw_component_prototypes[swc_type][0] if swc_type in cls.sw_component_prototypes else swc_type
                )
                port_prototype_name = utils.get_short_name(port_prototype)
                prm_ref = utils.get_valueOf(param_req_com_spec.PARAMETER_REF)
                prm_data_name = prm_ref.split("/")[-1]
                data_element = sw_component_type.find(prm_ref)
                p_d_name = f"{port_prototype_name}_{prm_data_name}"
                prm_interface_ref = utils.get_valueOf(port_prototype.REQUIRED_INTERFACE_TREF)
                rport_dict = {
                    "sort_name": f"{swc_name}_{p_d_name}",
                    "name": p_d_name,
                    "port_prototype": port_prototype,
                    "data_element": prm_data_name,
                    "prm_ref": prm_ref,
                    "prm_interface_ref": prm_interface_ref,
                    "type": cls.cal_prm_rport_type,
                    "component": swc_type,
                    "swc_prototype": swc_name,
                    "arg": cls.__parse_cal_prm_const_arg(data_element, [], f"{swc_name}_{p_d_name}", True, True),
                    "cal_prm_const": "",
                    "connected": False,
                }
                rv.update({p_d_name: rport_dict})
        else:
            pass
        return rv

    @classmethod
    def parse_mode_switch_rport(cls, rport_prototype, sw_component_type):
        rport_dict = {}
        swc_name = utils.get_short_name(sw_component_type)
        port_name = utils.get_short_name(rport_prototype)
        port_path = rport_prototype.get_path()
        rport_osapplication = cls.__parse_sw_component_type_osapplication(swc_name)
        rport_core_id = cls.__parse_sw_component_type_core_id(swc_name)
        if not hasattr(rport_prototype, "REQUIRED_INTERFACE_TREF") or not rport_prototype.REQUIRED_INTERFACE_TREF:
            return {}
        port_interface_ref = rport_prototype.REQUIRED_INTERFACE_TREF.valueOf_
        port_interface = sw_component_type.find(port_interface_ref)
        if not port_interface or not hasattr(port_interface, "MODE_GROUP"):
            return {}
        mode_group_prototype = port_interface.MODE_GROUP
        mode_group_prototype_name = utils.get_short_name(mode_group_prototype)
        mode_group_prototype_path = mode_group_prototype.get_path()
        if mode_group_prototype_path not in cls.operation_access:
            return {}
        p_access_runnable = cls.operation_access[mode_group_prototype_path]["p_access_runnable"]
        r_access_runnable = cls.operation_access[mode_group_prototype_path]["r_access_runnable"]
        combined_port_name = f"{port_name}_{mode_group_prototype_name}"
        # get use_enhanced_mode_api
        use_enhanced_mode_api = False
        com_specs = (
            rport_prototype.REQUIRED_COM_SPECS.MODE_SWITCH_RECEIVER_COM_SPEC
            if hasattr(rport_prototype, "REQUIRED_COM_SPECS") and rport_prototype.REQUIRED_COM_SPECS
            else None
        )
        if com_specs and len(com_specs) >= 1:
            com_spec = com_specs[0]
            if com_spec.ENHANCED_MODE_API and com_spec.ENHANCED_MODE_API.valueOf_ == "true":
                use_enhanced_mode_api = True
        # get mode group
        mode_group_ref = mode_group_prototype.TYPE_TREF.valueOf_
        mode_group_name = utils.get_short_name(sw_component_type.find(mode_group_ref))
        if not mode_group_name:
            return {}
        if mode_group_name not in cls.mode_groups:
            return {}
        # get init mode
        init_mode_name = None
        init_mode_dict = cls.mode_groups[mode_group_name]["initial_mode"]
        for name, value in init_mode_dict.items():
            init_mode_name = name

        swc_mode_switch_event = cls.__get_mode_switch_event_for_rport(
            p_access_runnable, r_access_runnable, swc_name, port_path
        )
        # get connected port info
        connect_port_name = None
        connected_component_name = None
        connected_osapplication = None
        for swc, runnable_info_list in p_access_runnable.items():
            for runnable_info in runnable_info_list:
                if port_path in cls.r_connections and runnable_info["port_path"] == cls.r_port_connection[port_path]:
                    # connected
                    connected_component_name = swc
                    connect_port_ref = cls.r_port_connection[port_path]
                    connect_port_name = connect_port_ref.split("/")[-1]
                    connected_osapplication = (
                        cls.component_osapplications[connected_component_name]
                        if connected_component_name in cls.component_osapplications
                        else None
                    )

        rport_dict = {
            "mode_group": mode_group_name,
            "connect_port_name": connect_port_name,
            "connected_component_name": connected_component_name,
            "mode_group_prototype": mode_group_prototype_name,
            "port_name": port_name,
            "swc_name": swc_name,
            "use_enhanced_mode_api": use_enhanced_mode_api,
            "type": "ModeNotification",
            "init_mode": init_mode_name,
            "swc_mode_switch_event": swc_mode_switch_event,
            "osapplication": rport_osapplication,
            "connected_osapplication": connected_osapplication,
            "inter_partition": (
                True
                if (rport_osapplication and connected_osapplication and rport_osapplication != connected_osapplication)
                else False
            ),
            "port_interface_type": "mode",
            "mode_disabled_entity": {},
            "mode_disabled_flag": {},
            "core_id": rport_core_id,
        }

        if port_path not in cls.mode_r_port_path_to_asw_port_dict:
            cls.mode_r_port_path_to_asw_port_dict[port_path] = {}
        if mode_group_prototype_name not in cls.mode_r_port_path_to_asw_port_dict[port_path]:
            cls.mode_r_port_path_to_asw_port_dict[port_path][mode_group_prototype_name] = {}
        if combined_port_name not in cls.mode_r_port_path_to_asw_port_dict[port_path][mode_group_prototype_name]:
            cls.mode_r_port_path_to_asw_port_dict[port_path][mode_group_prototype_name][combined_port_name] = rport_dict

        return {combined_port_name: rport_dict}

    @classmethod
    def __get_mode_switch_event_for_rport(cls, p_access_runnable, r_access_runnable, swc_name, port_path):
        event_map = {"ON-EXIT": "exit_events", "ON-TRANSITION": "transition_events", "ON-ENTRY": "entry_events"}
        swc_mode_switch_event_dict = {}
        for runnable_info in r_access_runnable.get(swc_name, []):
            if runnable_info["port_path"] != port_path:
                continue
            if "swc_mode_switch_event" in runnable_info:
                for key, value in runnable_info["swc_mode_switch_event"].items():
                    if event_map[key] not in swc_mode_switch_event_dict:
                        swc_mode_switch_event_dict.update({event_map[key]: [value]})
                    else:
                        swc_mode_switch_event_dict[event_map[key]].extend(
                            runnable_info["swc_mode_switch_event"].values()
                        )
        return swc_mode_switch_event_dict

    @classmethod
    def __get_mode_switch_event_for_pport(
        cls, data_element_p_access, data_element_r_access, swc_name, context_p_port_ref
    ):
        event_map = {"ON-EXIT": "exit_events", "ON-TRANSITION": "transition_events", "ON-ENTRY": "entry_events"}
        swc_mode_switch_event_dict = {}
        connected_port_path_set = set()
        for p_runnable_info in data_element_p_access.get(swc_name):
            # 解析连接Port对应的事件
            if p_runnable_info["port_path"] != context_p_port_ref:
                continue
            for swc_name, runnable_infos in data_element_r_access.items():
                for runnable_info in runnable_infos:
                    if (
                        runnable_info["port_path"] in cls.r_port_connection
                        and context_p_port_ref == cls.r_port_connection[runnable_info["port_path"]]
                    ):
                        connected_port_path_set.add((swc_name, runnable_info["port_path"]))
                    if (
                        runnable_info["port_path"] in cls.r_port_connection
                        and context_p_port_ref == cls.r_port_connection[runnable_info["port_path"]]
                        and "swc_mode_switch_event" in runnable_info
                    ):
                        for key, value in runnable_info["swc_mode_switch_event"].items():
                            if event_map[key] not in swc_mode_switch_event_dict:
                                swc_mode_switch_event_dict.update({event_map[key]: [value]})
                            else:
                                swc_mode_switch_event_dict[event_map[key]].extend(
                                    runnable_info["swc_mode_switch_event"].values()
                                )
        return swc_mode_switch_event_dict, list(connected_port_path_set)

    @classmethod
    def __check_if_cross_core_or_partition_between_two_ports(
        cls, port_core_id, port_appl, compared_port_core_id, compared_port_appl
    ):
        lock = "NONE"
        if port_core_id != compared_port_core_id:
            lock = "SPINLOCK"
        elif port_appl != compared_port_appl:
            lock = "OSISR"
        return lock

    @classmethod
    def __check_if_cross_core_or_partition_by_peer_ports(cls, port_core_id, port_appl, connected_ports):
        lock = "NONE"
        for peer in connected_ports:
            lock = cls.__check_if_cross_core_or_partition_between_two_ports(
                port_core_id, port_appl, peer["core_id"], peer["osapplication"]
            )
            if lock == "SPINLOCK":
                break
        return lock

    @classmethod
    def __check_if_pport_cross_core_or_partition_by_connection(cls, pport_core_id, pport_appl, connection):
        lock = "NONE"
        lock = cls.__check_if_cross_core_or_partition_by_peer_ports(pport_core_id, pport_appl, connection["ports"])
        if lock != "NONE":
            return lock
        if connection["category"] == "N:1":
            # find other connected p-ports and check if cross-core or cross-partition
            rport_path = connection["ports"][0]["port_path"]
            for local_pport_path in cls.r_connections[rport_path]:
                local_pport_swc = local_pport_path.split("/")[-2]
                if local_pport_swc not in cls.component_core_id:
                    continue
                lock = cls.__check_if_cross_core_or_partition_between_two_ports(
                    pport_core_id,
                    pport_appl,
                    cls.component_core_id[local_pport_swc],
                    cls.component_osapplications[local_pport_swc],
                )
                if lock != "NONE":
                    break
        return lock

    @classmethod
    def __check_if_rport_cross_core_or_partition_by_all_connected_ports(cls, rport_core_id, rport_appl, connection):
        lock = "NONE"
        lock = cls.__check_if_cross_core_or_partition_by_peer_ports(rport_core_id, rport_appl, connection["ports"])
        if lock != "NONE":
            return lock
        if connection["category"] == "1:N":
            pport_path = connection["ports"][0]["port_path"]
            for local_rport_path in cls.p_connections[pport_path]:
                local_rport_swc = local_rport_path.split("/")[-2]
                if local_rport_swc not in cls.component_core_id:
                    continue
                lock = cls.__check_if_cross_core_or_partition_between_two_ports(
                    rport_core_id,
                    rport_appl,
                    cls.component_core_id[local_rport_swc],
                    cls.component_osapplications[local_rport_swc],
                )
                if lock != "NONE":
                    break
        return lock

    @classmethod
    def __pack_sr_queue_pport_queue_info(cls, pport, connection):
        queue = {}
        # send to one queue owned by the receiver
        if connection["category"] in ["1:1", "N:1"]:
            lock = cls.__check_if_pport_cross_core_or_partition_by_connection(
                pport["core_id"], pport["osapplication"], connection
            )
            rport = connection["ports"][0]
            queue.update(
                {
                    f'{rport["component"]}_{rport["port_prototype"]}_{rport["data_element"]}': {
                        "size": cls.port_prototypes[rport["port_path"]][rport["data_element_path"]]["queue_size"],
                        "ioc_type": lock,
                    }
                }
            )
        # send to multi queues (one queue owned by one receiver)
        else:
            for rport in connection["ports"]:
                lock = cls.__check_if_cross_core_or_partition_between_two_ports(
                    pport["core_id"], pport["osapplication"], rport["core_id"], rport["osapplication"]
                )
                queue.update(
                    {
                        f'{rport["component"]}_{rport["port_prototype"]}_{rport["data_element"]}': {
                            "size": cls.port_prototypes[rport["port_path"]][rport["data_element_path"]]["queue_size"],
                            "ioc_type": lock,
                        }
                    }
                )
        return queue

    @classmethod
    def __pack_sr_queue_rport_queue_info(cls, rport, connection):
        queue = {}
        lock = cls.__check_if_cross_core_or_partition_by_peer_ports(
            rport["core_id"], rport["osapplication"], connection["ports"]
        )
        # recive from one queue owned by the receiver
        queue.update(
            {
                f'{rport["component"]}_{rport["port_prototype"]}_{rport["data_element"]}': {
                    "size": cls.port_prototypes[rport["port_path"]][rport["data_element_path"]]["queue_size"],
                    "ioc_type": lock,
                }
            }
        )
        return queue

    @classmethod
    def __pack_cs_ioc_server_queue_info(cls, pport, connection):
        queue = {}
        lock = cls.__check_if_pport_cross_core_or_partition_by_connection(
            pport["core_id"], pport["osapplication"], connection
        )
        # receive from queue owned by the server
        if (
            pport["port_path"] not in cls.port_prototypes
            or pport["operation_path"] not in cls.port_prototypes[pport["port_path"]]
        ):
            queue_size = pport["client_num"] * 2
        else:
            queue_size = cls.port_prototypes[pport["port_path"]][pport["operation_path"]]["queue_size"]
            if queue_size < pport["client_num"] * 2:
                logger.warning(
                    f'The queue size of server port <{pport["port_path"]}> is less than twice the number of client port'
                )
                queue_size = pport["client_num"] * 2
        memmap_enq = cls.__update_cs_enqueue_memmap(pport, connection)
        memmap_deq = cls.__update_cs_dequeue_memmap(pport, connection)
        queue.update(
            {
                f'{pport["component"]}_{pport["name"]}': {
                    "name": f'{pport["component"]}_{pport["name"]}',
                    "size": queue_size,
                    "ioc_type": lock,
                    "memmap_enq": memmap_enq,
                    "memmap_deq": memmap_deq,
                }
            }
        )
        return queue

    @classmethod
    def __pack_cs_ioc_client_queue_info(cls, rport, connection):
        queue = {}
        lock = cls.__check_if_rport_cross_core_or_partition_by_all_connected_ports(
            rport["core_id"], rport["osapplication"], connection
        )
        # send to one queue (maybe shared with multi clients) owned by the server
        pport = connection["ports"][0]
        if (
            pport["port_path"] not in cls.port_prototypes
            or pport["operation_path"] not in cls.port_prototypes[pport["port_path"]]
        ):
            queue_size = rport["client_num"] * 2
        else:
            queue_size = cls.port_prototypes[pport["port_path"]][pport["operation_path"]]["queue_size"]
            if queue_size < rport["client_num"] * 2:
                logger.warning(
                    f'The queue size of server port <{pport["port_path"]}> is less than twice the number of client port'
                )
                queue_size = rport["client_num"] * 2
        queue.update(
            {
                f'{pport["component"]}_{pport["name"]}': {
                    "name": f'{pport["component"]}_{pport["name"]}',
                    "client_name": f"{rport['component']}_{rport['name']}",
                    "size": queue_size,
                    "ioc_type": lock,
                }
            }
        )
        return queue

    @classmethod
    def __pack_sr_connected_port_info(cls, port_path, runnable_symbol, runnable_path, access_info):
        connected_port_info = {}
        try:
            port_swc_type = port_path.split("/")[-2]
            port_swc = (
                cls.sw_component_prototypes[port_swc_type][0]
                if port_swc_type in cls.sw_component_prototypes
                else port_swc_type
            )
            port_prototype_name = port_path.split("/")[-1]
            data_element_path = access_info["original_data_element_path"]
            data_element_name = data_element_path.split("/")[-1]
            data_element_path_short = "/".join(data_element_path.split("/")[-2:])
            connected_port_info = {
                "name": f"{port_prototype_name}_{data_element_name}",
                "component": port_swc_type,
                "swc_prototype": port_swc,
                "port_path": port_path,
                "port_prototype": port_prototype_name,
                "data_element_path": data_element_path,
                "data_element": data_element_name,
                "runnable": runnable_path.split("/")[-1],
                "symbol": runnable_symbol,
                "access_type": access_info["access_type"],
                "init_value": None,
                "core_id": cls.component_core_id[port_swc_type] if port_swc_type in cls.component_core_id else None,
                "osapplication": (
                    cls.component_osapplications[port_swc_type]
                    if port_swc_type in cls.component_osapplications
                    else None
                ),
                "task": cls.runnable_tasks[runnable_symbol] if runnable_symbol in cls.runnable_tasks else None,
                "is_prport": access_info["is_prport"],
            }
            if connected_port_info["access_type"] == "Receive":
                connected_port_info["timeout"] = cls.port_data_element_access[f"{port_path}{data_element_path_short}"][
                    runnable_path
                ]["timeout"]
        except Exception:
            # validation do the check
            pass
        return connected_port_info

    @classmethod
    def get_if_data_element_is_queued(cls, data_element):
        is_queued = False
        if not hasattr(data_element, "SW_DATA_DEF_PROPS") or not data_element.SW_DATA_DEF_PROPS:
            return is_queued
        try:
            sw_impl_policy = getattr(
                data_element.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[
                    0
                ].SW_IMPL_POLICY,
                "valueOf_",
                None,
            )
            if sw_impl_policy == "QUEUED":
                is_queued = True
        except Exception as e:
            raise Exception(
                f"The SW_IMPL_POLICY <{sw_impl_policy}> of "
                f"S/R data element <{data_element.get_path()}> is not supported!"
            ) from e
        return is_queued

    @classmethod
    def __parse_sr_pport_connected_ports(cls, pport_obj, data_element_path_short):
        connected_ports = {"category": "", "ports": []}
        pport_path = pport_obj.get_path()
        if len(cls.p_connections[pport_path]) > 1:
            connected_ports["category"] = "1:N"
        else:
            connected_rport_path = cls.p_connections[pport_path][0]
            if len(cls.r_connections[connected_rport_path]) > 1:
                connected_ports["category"] = "N:1"
            else:
                connected_ports["category"] = "1:1"
        for connected_rport_path in cls.p_connections[pport_path]:
            rport_data_element_access_key = f"{connected_rport_path}{data_element_path_short}"
            # data element of connected rport is not accessed by any runnable in the peer swc
            if rport_data_element_access_key not in cls.port_data_element_access:
                continue
            # data element of connected rport is accessed by multi runnables in the peer swc
            for runnable_path, access_info in cls.port_data_element_access[rport_data_element_access_key].items():
                runnable_obj = pport_obj.find(runnable_path)
                runnable_symbol = utils.get_runnable_symbol(runnable_obj)
                port_info = cls.__pack_sr_connected_port_info(
                    connected_rport_path, runnable_symbol, runnable_path, access_info
                )
                if not port_info:
                    continue
                connected_ports["ports"].append(port_info)
        # process the connection degradation caused by connected ports without access point
        if len(connected_ports["ports"]) <= 0:
            connected_ports = None
        return connected_ports

    @classmethod
    def __parse_sr_rport_connected_ports(cls, rport_obj, data_element_path_short):
        connected_ports = {"category": "", "ports": []}
        rport_path = rport_obj.get_path()
        if len(cls.r_connections[rport_path]) > 1:
            connected_ports["category"] = "N:1"
        else:
            connected_pport_path = cls.r_connections[rport_path][0]
            if len(cls.p_connections[connected_pport_path]) > 1:
                connected_ports["category"] = "1:N"
            else:
                connected_ports["category"] = "1:1"
        for connected_pport_path in cls.r_connections[rport_path]:
            pport_data_element_access_key = f"{connected_pport_path}{data_element_path_short}"
            # data element of connected pport is not accessed by any runnable in the peer swc
            if pport_data_element_access_key not in cls.port_data_element_access:
                continue
            # data element of connected rport is accessed by multi runnables in the peer swc
            for runnable_path, access_info in cls.port_data_element_access[pport_data_element_access_key].items():
                runnable_obj = rport_obj.find(runnable_path)
                runnable_symbol = utils.get_runnable_symbol(runnable_obj)
                port_info = cls.__pack_sr_connected_port_info(
                    connected_pport_path, runnable_symbol, runnable_path, access_info
                )
                if not port_info:
                    continue
                connected_ports["ports"].append(port_info)
        # process the connection degradation caused by connected ports without access point
        if len(connected_ports["ports"]) <= 0:
            connected_ports = None
        return connected_ports

    @classmethod
    def parse_sr_pport_access_point(cls, access_point, type, runnable_obj, mapping_sets):
        data_element_path = utils.get_valueOf(
            access_point.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF.TARGET_DATA_PROTOTYPE_REF
        )
        data_element = access_point.find(data_element_path)
        if not data_element:
            return {}

        data_name = data_element_path.split("/")[-1]
        is_queued = cls.get_if_data_element_is_queued(data_element)
        pport_path = utils.get_valueOf(access_point.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF.PORT_PROTOTYPE_REF)
        pport_swc_type_name = pport_path.split("/")[-2]  # swc type
        pport_swc_name = (
            cls.sw_component_prototypes[pport_swc_type_name][0]
            if pport_swc_type_name in cls.sw_component_prototypes
            else pport_swc_type_name
        )  # swc prototype
        port_prototype_name = pport_path.split("/")[-1]
        port_var = port_prototype_name + "_" + data_name
        comspec_key = f"{pport_swc_type_name}_{port_var}"
        pport_name = port_var
        pport_key = port_var
        runnable_path = runnable_obj.get_path()
        runnable_name = utils.get_short_name(runnable_obj)
        runnable_symbol = utils.get_runnable_symbol(runnable_obj)

        ar_port = access_point.find(pport_path)
        is_prport = True if ar_port.get_tag() == "PR-PORT-PROTOTYPE" else False

        if type == "Explicit Sender" and is_queued:
            type = "Queued Sender"

        is_implicit = False
        if type == "Implicit Sender":
            pport_name = f"{runnable_name}_{port_var}"
            pport_key = pport_name
            is_implicit = True

        port_full_key = f"p_{pport_swc_type_name}_{pport_key}"

        pport_dict = {
            "sort_name": f"{pport_swc_name}_{pport_name}",
            "name": pport_name,
            "port_prototype": port_prototype_name,
            "data_element": data_element_path.split("/")[-1],
            "type": type,
            "component": pport_swc_type_name,
            "swc_prototype": pport_swc_name,
            "runnable": [runnable_name],
            "symbol": [runnable_symbol],
            "runnable_path": [runnable_path],
            "task": [],  # DONOT use None!
            "arg": cls.__parse_sr_accessed_variable(data_element, mapping_sets, comspec_key, True, not is_queued),
            "connected_ports": None,
            "set_events": [],
            "signal_category": "None",
            "osapplication": None,
            "core_id": None,
            "is_queued": is_queued,
            "is_implicit": is_implicit,
            "port_path": pport_path,
            "port_key": pport_key,
            "port_interface_type": "sr",
            "lock": "NONE",
            "data_name": data_name,
            "port_full_key": port_full_key,
            "data_element_path": data_element_path,
            "swc_port_var": f"{pport_swc_name}_{port_var}",
            "buff_category": None,
            "buff_memmap_category": MemmapCategory.OSA_PRIVATE,
            "enable_update": [],
            "is_p": True,
            "is_prport": is_prport,
            "has_prport": is_prport,
            "port_var": port_var,
            "constraints": {},
            "compu_methods": {},
            "data_mapping_m_to_n": "0",
        }

        try:
            pport_dict["core_id"] = cls.__parse_sw_component_type_core_id(pport_swc_type_name)
            pport_dict["osapplication"] = cls.__parse_sw_component_type_osapplication(pport_swc_type_name)
            pport_dict["task"] = [cls.runnable_tasks[runnable_symbol]] if runnable_symbol in cls.runnable_tasks else []
        except Exception:
            # validation do the check
            logger.error(
                f"Swc port info <{pport_dict['swc_port_var']}> not properly resolved, "
                f"check runnable task mappping: <{pport_dict['runnable_symbol']}>"
            )
            return {}
        if pport_path not in cls.sr_p_port_path_to_asw_port_dict:
            cls.sr_p_port_path_to_asw_port_dict[pport_path] = {}
        if data_name not in cls.sr_p_port_path_to_asw_port_dict[pport_path]:
            cls.sr_p_port_path_to_asw_port_dict[pport_path][data_name] = {}
        if pport_key not in cls.sr_p_port_path_to_asw_port_dict[pport_path][data_name]:
            cls.sr_p_port_path_to_asw_port_dict[pport_path][data_name][pport_key] = pport_dict

        if is_queued:
            pport_dict["queue"] = {}
            pport_dict["q_lock"] = "NONE"

        # unconnected pport
        if is_prport:
            if pport_path not in cls.p_connections and pport_path not in cls.r_connections:
                return pport_dict
        else:
            if pport_path not in cls.p_connections:
                return pport_dict

        return pport_dict

    @classmethod
    def parse_sr_rport_access_point(cls, access_point, type, runnable_obj, mapping_sets, dread=False, waitpoints=None):
        data_element_path = utils.get_valueOf(
            access_point.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF.TARGET_DATA_PROTOTYPE_REF
        )
        data_element_path_short = "/".join(data_element_path.split("/")[-2:])
        data_element = access_point.find(data_element_path)
        if not data_element:
            return {}
        data_name = data_element_path.split("/")[-1]
        is_queued = cls.get_if_data_element_is_queued(data_element)
        rport_path = utils.get_valueOf(access_point.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF.PORT_PROTOTYPE_REF)
        rport_swc_type_name = rport_path.split("/")[-2]  # swc type
        rport_swc_name = (
            cls.sw_component_prototypes[rport_swc_type_name][0]
            if rport_swc_type_name in cls.sw_component_prototypes
            else rport_swc_type_name
        )  # swc prototype
        port_prototype_name = rport_path.split("/")[-1]
        rport_name = port_prototype_name + "_" + data_name
        port_var = port_prototype_name + "_" + data_name
        comspec_key = f"{rport_swc_type_name}_{rport_name}"
        rport_key = rport_name
        runnable_ref = runnable_obj.get_path()
        runnable_name = utils.get_short_name(runnable_obj)
        runnable_symbol = utils.get_runnable_symbol(runnable_obj)

        ar_port = access_point.find(rport_path)
        is_prport = True if ar_port.get_tag() == "PR-PORT-PROTOTYPE" else False

        if type == "Explicit Receiver" and is_queued:
            type = "Queued Receiver"

        is_implicit = False
        if type == "Implicit Receiver":
            rport_name = f"{runnable_name}_{rport_name}"
            rport_key = rport_name
            is_implicit = True
        elif type == "Explicit Receiver":
            rport_key = f"DRead_{rport_key}" if dread else rport_key

        port_full_key = f"r_{rport_swc_type_name}_{rport_key}"

        rport_dict = {
            "sort_name": f"{rport_swc_name}_{rport_name}",
            "name": rport_name,
            "port_prototype": port_prototype_name,
            "data_element": data_element_path.split("/")[-1],
            "type": type,
            "component": rport_swc_type_name,
            "swc_prototype": rport_swc_name,
            "runnable": [runnable_name],
            "symbol": [runnable_symbol],
            "runnable_path": [runnable_ref],
            "task": [],  # DONOT use None!
            "arg": cls.__parse_sr_accessed_variable(data_element, mapping_sets, comspec_key, False, not is_queued),
            "connected_ports": None,
            "signal_category": "None",
            "osapplication": None,
            "core_id": None,
            "is_queued": is_queued,
            "is_dread": dread,
            "is_implicit": is_implicit,
            "port_path": rport_path,
            "port_key": rport_key,
            "port_interface_type": "sr",
            "lock": "NONE",
            "data_name": data_name,
            "port_full_key": port_full_key,
            "data_element_path": data_element_path,
            "swc_port_var": f"{rport_swc_name}_{port_prototype_name}_{data_name}",
            "buff_category": None,
            "buff_memmap_category": MemmapCategory.OSA_PRIVATE,
            "is_p": False,
            "is_prport": is_prport,
            "has_prport": is_prport,
            "required_com_specs": {},
            "port_var": port_var,
            "constraints": {},
            "compu_methods": {},
            "data_mapping_m_to_n": "0",
            "schedule_table": {},
        }
        if type == "Explicit Receiver":
            if data_element_path in cls.port_prototypes[rport_path]:
                rport_dict["enable_update"] = cls.port_prototypes[rport_path][data_element_path]["enable_update"]
            else:
                rport_dict["enable_update"] = False
        try:
            rport_dict["core_id"] = cls.__parse_sw_component_type_core_id(rport_swc_type_name)
            rport_dict["osapplication"] = cls.__parse_sw_component_type_osapplication(rport_swc_type_name)
            rport_dict["task"] = [cls.runnable_tasks[runnable_symbol]] if runnable_symbol in cls.runnable_tasks else []
        except Exception:
            # validation do the check
            logger.error(
                f"Swc port info <{rport_dict['swc_port_var']}> not properly resolved, "
                f"check runnable task mappping: <{rport_dict['runnable_symbol']}>"
            )
            return {}

        if rport_path not in cls.sr_r_port_path_to_asw_port_dict:
            cls.sr_r_port_path_to_asw_port_dict[rport_path] = {}
        if data_name not in cls.sr_r_port_path_to_asw_port_dict[rport_path]:
            cls.sr_r_port_path_to_asw_port_dict[rport_path][data_name] = {}
        if rport_key not in cls.sr_r_port_path_to_asw_port_dict[rport_path][data_name]:
            cls.sr_r_port_path_to_asw_port_dict[rport_path][data_name][rport_key] = rport_dict

        if type == "Explicit Receiver":
            rport_dict["read_by_value"] = dread
        elif type == "Queued Receiver":
            rport_dict["timeout"] = cls.port_data_element_access[f"{rport_path}{data_element_path_short}"][
                runnable_ref
            ]["timeout"]
            # rport_dict['queue_size'] = cls.port_prototypes[rport_path][data_element_path]['queue_size']
            os_counter = cls.os_counter.get(rport_dict["osapplication"], {})
            if os_counter and rport_dict["timeout"] > 0.0:
                rport_dict["schedule_table"]["name"] = f'Rte_St_{rport_dict["swc_port_var"]}'
                rport_dict["schedule_table"]["id"] = f'OS_SCHEDTABLE_{rport_dict["schedule_table"]["name"].upper()}_ID'
                rport_dict["schedule_table"]["task"] = rport_dict["task"][0]
                rport_dict["schedule_table"]["counter"] = os_counter
                rport_dict["schedule_table"]["timeout"] = rport_dict["timeout"]
                rport_dict["schedule_table"]["trigger_task"] = rport_dict["task"][0]
                rport_dict["schedule_table"]["trigger_event"] = f'Rte_Ev_Timeout_{rport_dict["task"][0]}'
                if rport_dict["schedule_table"]["id"] not in cls.rte_sch_tbl:
                    cls.rte_sch_tbl[rport_dict["schedule_table"]["id"]] = rport_dict["schedule_table"]
        if not is_queued:
            rport_dict["required_com_specs"] = cls.parse_sr_rport_required_com_specs(
                access_point.find(rport_path), data_element_path
            )
        else:
            rport_dict["queue"] = {}
            rport_dict["q_lock"] = "NONE"

        # unconnected port
        if is_prport:
            if rport_path not in cls.r_connections and rport_path not in cls.p_connections:
                return rport_dict
        else:
            if rport_path not in cls.r_connections:
                return rport_dict

        return rport_dict

    @classmethod
    def parse_sr_rport_required_com_specs(cls, rport_prototype, data_element_path):
        rv_dict = {"enable_update": "false", "handle_never_received": "false", "alive_timeout": "0"}
        if rport_prototype is None:
            return rv_dict
        required_com_specs = getattr(rport_prototype, "REQUIRED_COM_SPECS", None)
        if required_com_specs is None:
            return rv_dict
        nonqueued_receiver_com_spec_list = getattr(required_com_specs, "NONQUEUED_RECEIVER_COM_SPEC", [])
        for nonqueued_receiver_com_spec in nonqueued_receiver_com_spec_list:
            data_element_ref = getattr(nonqueued_receiver_com_spec, "DATA_ELEMENT_REF", None)
            data_element_ref_value = getattr(data_element_ref, "valueOf_", None)
            if data_element_ref_value != data_element_path:
                continue
            enable_update = getattr(nonqueued_receiver_com_spec, "ENABLE_UPDATE", None)
            rv_dict["enable_update"] = getattr(enable_update, "valueOf_", "false")
            handle_never_received = getattr(nonqueued_receiver_com_spec, "HANDLE_NEVER_RECEIVED", None)
            rv_dict["handle_never_received"] = getattr(handle_never_received, "valueOf_", "false")
            alive_timeout = getattr(nonqueued_receiver_com_spec, "ALIVE_TIMEOUT", None)
            rv_dict["alive_timeout"] = getattr(alive_timeout, "valueOf_", "0")
            break
        return rv_dict

    @classmethod
    def parse_sw_component_type_pports(cls, sw_component_type, info):
        pports_dict = {}
        if not sw_component_type.PORTS:
            return pports_dict
        for behavior in getattr(getattr(sw_component_type, "INTERNAL_BEHAVIORS", None), "SWC_INTERNAL_BEHAVIOR", []):
            mapping_sets = []
            if behavior.DATA_TYPE_MAPPING_REFS:
                for mapping_set in behavior.DATA_TYPE_MAPPING_REFS.DATA_TYPE_MAPPING_REF:
                    mapping_sets.append(utils.get_valueOf(mapping_set))
            if behavior.EVENTS and len(behavior.EVENTS.OPERATION_INVOKED_EVENT) > 0:
                # filter pport not be triggered
                for op_event in behavior.EVENTS.OPERATION_INVOKED_EVENT:
                    pport = cls.parse_cs_server_pport(op_event, sw_component_type)
                    if pport:
                        pports_dict.update({pport["port_key"]: pport})
                    cls.update_swc_info_from_port(pport, op_event, info, "CS")
            if behavior.RUNNABLES:
                for runnable_entity in behavior.RUNNABLES.RUNNABLE_ENTITY:
                    # runnable_ref = runnable_entity.get_path()
                    if runnable_entity.DATA_SEND_POINTS:
                        for access_point in runnable_entity.DATA_SEND_POINTS.VARIABLE_ACCESS:
                            pport = cls.parse_sr_pport_access_point(
                                access_point, "Explicit Sender", runnable_entity, mapping_sets
                            )
                            if not pport:
                                continue
                            cls.update_sr_cs_port_multi_runnable_access(pports_dict, pport)
                            cls.update_swc_info_from_port(pport, access_point, info, "SR")
                    if runnable_entity.DATA_WRITE_ACCESSS:
                        for access_point in runnable_entity.DATA_WRITE_ACCESSS.VARIABLE_ACCESS:
                            pport = cls.parse_sr_pport_access_point(
                                access_point, "Implicit Sender", runnable_entity, mapping_sets
                            )
                            if not pport:
                                continue
                            pports_dict.update({pport["port_key"]: pport})
                            cls.update_swc_info_from_port(pport, access_point, info, "SR")
                    if runnable_entity.MODE_SWITCH_POINTS:
                        for mode_switch_point in runnable_entity.MODE_SWITCH_POINTS.MODE_SWITCH_POINT:
                            pports_dict.update(
                                cls.parse_mode_switch_pport(mode_switch_point, sw_component_type, runnable_entity)
                            )
                    if runnable_entity.EXTERNAL_TRIGGERING_POINTS:
                        for (
                            external_triggering_point
                        ) in runnable_entity.EXTERNAL_TRIGGERING_POINTS.EXTERNAL_TRIGGERING_POINT:
                            pports_dict.update(
                                cls.parse_external_trigger_pport(
                                    external_triggering_point, "External Trigger", runnable_entity
                                )
                            )
        return dict(sorted(pports_dict.items()))

    @classmethod
    def parse_sw_component_type_rports(cls, sw_component_type, info):
        rports_dict = {}
        if not sw_component_type.PORTS:
            return rports_dict
        for behavior in getattr(getattr(sw_component_type, "INTERNAL_BEHAVIORS", None), "SWC_INTERNAL_BEHAVIOR", []):
            mapping_sets = []
            if behavior.DATA_TYPE_MAPPING_REFS:
                for mapping_set in behavior.DATA_TYPE_MAPPING_REFS.DATA_TYPE_MAPPING_REF:
                    mapping_sets.append(utils.get_valueOf(mapping_set))
            if behavior.RUNNABLES:
                for runnable_entity in behavior.RUNNABLES.RUNNABLE_ENTITY:
                    # runnable_ref = runnable_entity.get_path()
                    if runnable_entity.SERVER_CALL_POINTS:
                        for access_point in getattr(
                            runnable_entity.SERVER_CALL_POINTS, "SYNCHRONOUS_SERVER_CALL_POINT"
                        ):
                            rport = cls.parse_cs_client_rport(
                                access_point, runnable_entity, sw_component_type, type="Sync Client"
                            )
                            cls.update_sr_cs_port_multi_runnable_access(rports_dict, rport)
                            cls.update_swc_info_from_port(rport, access_point, info, "CS")
                        for access_point in getattr(
                            runnable_entity.SERVER_CALL_POINTS, "ASYNCHRONOUS_SERVER_CALL_POINT"
                        ):
                            rport = cls.parse_cs_client_rport(
                                access_point, runnable_entity, sw_component_type, type="Async Client"
                            )
                            cls.update_sr_cs_port_multi_runnable_access(rports_dict, rport)
                            cls.update_swc_info_from_port(rport, access_point, info, "CS")
                    if runnable_entity.DATA_RECEIVE_POINT_BY_ARGUMENTS:
                        for access_point in runnable_entity.DATA_RECEIVE_POINT_BY_ARGUMENTS.VARIABLE_ACCESS:
                            rport = cls.parse_sr_rport_access_point(
                                access_point,
                                "Explicit Receiver",
                                runnable_entity,
                                mapping_sets,
                                False,
                                runnable_entity.WAIT_POINTS,
                            )
                            if not rport:
                                continue
                            cls.update_sr_cs_port_multi_runnable_access(rports_dict, rport)
                            cls.update_swc_info_from_port(rport, access_point, info, "SR")
                    if runnable_entity.DATA_RECEIVE_POINT_BY_VALUES:
                        for access_point in runnable_entity.DATA_RECEIVE_POINT_BY_VALUES.VARIABLE_ACCESS:
                            rport = cls.parse_sr_rport_access_point(
                                access_point, "Explicit Receiver", runnable_entity, mapping_sets, True
                            )
                            if not rport:
                                continue
                            cls.update_sr_cs_port_multi_runnable_access(rports_dict, rport)
                            cls.update_swc_info_from_port(rport, access_point, info, "SR")
                    if runnable_entity.DATA_READ_ACCESSS:
                        for access_point in runnable_entity.DATA_READ_ACCESSS.VARIABLE_ACCESS:
                            rport = cls.parse_sr_rport_access_point(
                                access_point, "Implicit Receiver", runnable_entity, mapping_sets
                            )
                            if not rport:
                                continue
                            rports_dict.update({rport["port_key"]: rport})
                            cls.update_swc_info_from_port(rport, access_point, info, "SR")
        for rport_prototype in sw_component_type.PORTS.R_PORT_PROTOTYPE:
            rports_dict.update(cls.parse_external_trigger_rport(rport_prototype, "External Trigger"))
        for rport_prototype in sw_component_type.PORTS.R_PORT_PROTOTYPE:
            rports_dict.update(cls.parse_mode_switch_rport(rport_prototype, sw_component_type))
        for rport_prototype in sw_component_type.PORTS.R_PORT_PROTOTYPE:
            rports_dict.update(cls.parse_cal_prm_port(rport_prototype, sw_component_type))
        return dict(sorted(rports_dict.items()))

    @classmethod
    def update_sr_cs_port_multi_runnable_access(cls, port_dict, port):
        if not port or "port_key" not in port:
            return
        port_key = port["port_key"]
        if port_key not in port_dict:
            port_dict.update({port_key: port})
        else:
            # try:
            exist_port = port_dict[port_key]
            exist_port["runnable"] += port["runnable"]
            exist_port["symbol"] += port["symbol"]
            exist_port["runnable_path"] += port["runnable_path"]
            exist_port["task"] += port["task"]
            # except Exception as e:
            #     raise Exception(f'Task mapping of runnable <{port["runnable"]}> does NOT exist!') from e

    @classmethod
    def update_swc_info_from_port(cls, port, ar_class, info, port_type):
        if not port:
            return
        if not cls.constraints and not cls.compu_methods:
            return
        # update constraints and compu-methods of ADT & IDT
        if port_type == "SR":
            adt_path = port["arg"]["adt_path"]
            idt_path = port["arg"]["idt_path"]
            cls.update_constraint_compumethod_of_swc_info(port, ar_class, adt_path, info, "adt")
            cls.update_constraint_compumethod_of_swc_info(port, ar_class, idt_path, info, "idt")
        elif port_type == "CS":
            # for key, value in port.items():
            if "client" in port["type"].lower():
                operation_ref = utils.get_valueOf(ar_class.OPERATION_IREF.TARGET_REQUIRED_OPERATION_REF)
                operation = ar_class.find(operation_ref)
                args = operation.ARGUMENTS.ARGUMENT_DATA_PROTOTYPE if operation.ARGUMENTS else []
                if args:
                    for arg in args:
                        if arg.TYPE_TREF.DEST == "IMPLEMENTATION-DATA-TYPE":
                            adt_path = None
                            idt_path = utils.get_valueOf(arg.TYPE_TREF)
                        # elif arg.TYPE_TREF.DEST == 'APPLICATION-PRIMITIVE-DATA-TYPE':
                        #     # 目前不支持argument里面ref的是adt
                        #     adt_path = utils.get_valueOf(arg.TYPE_TREF)
                        #     idt_path = cls.__convert_adt_to_idt(adt_path, mapping_sets)
                        # cls.update_constraint_compumethod_of_swc_info(port, ar_class, adt_path, info, 'adt')
                        cls.update_constraint_compumethod_of_swc_info(port, ar_class, idt_path, info, "idt")
            else:
                operation_ref = utils.get_valueOf(ar_class.OPERATION_IREF.TARGET_PROVIDED_OPERATION_REF)
                operation = ar_class.find(operation_ref)
                args = operation.ARGUMENTS.ARGUMENT_DATA_PROTOTYPE if operation.ARGUMENTS else []
                if args:
                    for arg in args:
                        if arg.TYPE_TREF.DEST == "IMPLEMENTATION-DATA-TYPE":
                            adt_path = None
                            idt_path = utils.get_valueOf(arg.TYPE_TREF)
                        # elif arg.TYPE_TREF.DEST == 'APPLICATION-PRIMITIVE-DATA-TYPE':
                        #     # 目前不支持argument里面ref的是adt
                        #     adt_path = utils.get_valueOf(arg.TYPE_TREF)
                        #     idt_path = cls.__convert_adt_to_idt(adt_path, mapping_sets)
                        # cls.update_constraint_compumethod_of_swc_info(port, ar_class, adt_path, info, 'adt')
                        cls.update_constraint_compumethod_of_swc_info(port, ar_class, idt_path, info, "idt")

    @classmethod
    def update_constraint_compumethod_of_swc_info(cls, port, ar_class, data_type_path, info, data_type):
        if not data_type_path:
            return
        ar_dt = ar_class.find(data_type_path)
        constraint_path_list = []
        compumethod_path_list = []
        if not ar_dt:
            return
        category = utils.get_valueOf(ar_dt.CATEGORY)
        if category in ["VALUE", "TYPE_REFERENCE", "BOOLEAN"]:
            constraint_path_list, compumethod_path_list = cls.get_value_constraint_compumethod_path(ar_dt, data_type)
        elif category == "ARRAY":
            constraint_path_list, compumethod_path_list = cls.get_array_constraint_compumethod_path(ar_dt, data_type)
        elif category == "STRUCTURE":
            constraint_path_list, compumethod_path_list = cls.get_struct_constraint_compumethod_path(ar_dt, data_type)
        else:
            # TODO
            pass
        constraint_path_set = set(constraint_path_list)
        compumethod_path_set = set(compumethod_path_list)

        # constraint
        if data_type == "adt":
            for constraint_path in constraint_path_set:
                if constraint_path not in cls.constraints:
                    continue
                constr = {
                    data_type_path: {
                        "adt_name": utils.get_short_name(ar_dt),
                        "basetype": port["arg"]["datatype"].get("basetype", None),
                        "max": cls.constraints[constraint_path]["max"],
                        "min": cls.constraints[constraint_path]["min"],
                    }
                }
                if "constraints" in port:
                    port["constraints"].update(constr)
                if data_type_path not in info["constraints"]:
                    info["constraints"].update(constr)

        # compu method
        for compumethod_path in compumethod_path_set:
            if compumethod_path not in cls.compu_methods:
                continue
            compu_method = {
                data_type_path: {
                    "category": cls.compu_methods[compumethod_path]["category"],
                    "value": cls.compu_methods[compumethod_path]["value"],
                }
            }
            if "compu_methods" in port:
                port["compu_methods"].update(compu_method)
            if data_type_path not in info["compu_methods"][data_type]:
                info["compu_methods"][data_type].update(compu_method)

    @classmethod
    def get_struct_constraint_compumethod_path(cls, ar_dt, data_type):
        constraint_path_list = []
        compumethod_path_list = []
        constraint_path = None
        compumethod_path = None
        ref_idts = ar_dt.SUB_ELEMENTS.IMPLEMENTATION_DATA_TYPE_ELEMENT
        for ref_idt in ref_idts:
            if utils.get_valueOf(ref_idt.CATEGORY) == "VALUE":
                constraint_path, compumethod_path = cls.get_value_constraint_compumethod_path(ref_idt, data_type)
            elif utils.get_valueOf(ref_idt.CATEGORY) == "TYPE_REFERENCE":
                idt_ref = utils.get_valueOf(
                    ref_idt.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[
                        0
                    ].IMPLEMENTATION_DATA_TYPE_REF
                )
                idt_dt = ar_dt.find(idt_ref)
                if utils.get_valueOf(idt_dt.CATEGORY) in ["VALUE", "TYPE_REFERENCE"]:
                    constraint_path, compumethod_path = cls.get_value_constraint_compumethod_path(idt_dt, data_type)
                    if constraint_path:
                        constraint_path_list.extend(constraint_path)
                    if compumethod_path:
                        compumethod_path_list.extend(compumethod_path)
                elif utils.get_valueOf(idt_dt.CATEGORY) == "ARRAY":
                    constraint_path, compumethod_path = cls.get_array_constraint_compumethod_path(idt_dt, data_type)
                    if constraint_path:
                        constraint_path_list.extend(constraint_path)
                    if compumethod_path:
                        compumethod_path_list.extend(compumethod_path)
                elif utils.get_valueOf(idt_dt.CATEGORY) == "STRUCTURE":
                    constraint_path, compumethod_path = cls.get_struct_constraint_compumethod_path(idt_dt, data_type)
                    if constraint_path:
                        constraint_path_list.extend(constraint_path)
                    if compumethod_path:
                        compumethod_path_list.extend(compumethod_path)
        return constraint_path_list, compumethod_path_list

    @classmethod
    def get_array_constraint_compumethod_path(cls, ar_dt, data_type):
        constraint_path_list = []
        compumethod_path_list = []
        constraint_path = None
        compumethod_path = None
        if data_type == "idt":
            element_category = utils.get_valueOf(ar_dt.SUB_ELEMENTS.IMPLEMENTATION_DATA_TYPE_ELEMENT[0].CATEGORY)
        elif data_type == "adt":
            element_category = utils.get_valueOf(ar_dt.ELEMENT.CATEGORY)

        if element_category == "VALUE":
            if data_type == "idt":
                idt_ref = utils.get_valueOf(
                    ar_dt.SUB_ELEMENTS.IMPLEMENTATION_DATA_TYPE_ELEMENT[0]
                    .SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[0]
                    .BASE_TYPE_REF
                )
                idt_dt = ar_dt.find(idt_ref)
                constraint_path, compumethod_path = cls.get_value_constraint_compumethod_path(idt_dt, data_type)
            elif data_type == "adt":
                if ar_dt.ELEMENT.TYPE_TREF.DEST == "APPLICATION-PRIMITIVE-DATA-TYPE":
                    adt_ref = utils.get_valueOf(ar_dt.ELEMENT.parent_object_.ELEMENT.TYPE_TREF)
                    adt_dt = ar_dt.find(adt_ref)
                    constraint_path, compumethod_path = cls.get_value_constraint_compumethod_path(adt_dt, data_type)
        elif element_category == "TYPE_REFERENCE":
            idt_ref = utils.get_valueOf(
                ar_dt.SUB_ELEMENTS.IMPLEMENTATION_DATA_TYPE_ELEMENT[0]
                .SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[0]
                .IMPLEMENTATION_DATA_TYPE_REF
            )
            idt_dt = ar_dt.find(idt_ref)
            if utils.get_valueOf(idt_dt.CATEGORY) == "VALUE":
                constraint_path, compumethod_path = cls.get_value_constraint_compumethod_path(idt_dt, data_type)
            elif utils.get_valueOf(idt_dt.CATEGORY) == "STRUCTURE":
                constraint_path, compumethod_path = cls.get_struct_constraint_compumethod_path(idt_dt, data_type)
            elif utils.get_valueOf(idt_dt.CATEGORY) == "ARRAY":
                constraint_path, compumethod_path = cls.get_array_constraint_compumethod_path(idt_dt, data_type)
        else:
            # TODO
            pass
        if constraint_path:
            constraint_path_list.extend(constraint_path)
        if compumethod_path:
            compumethod_path_list.extend(compumethod_path)
        return constraint_path_list, compumethod_path_list

    @classmethod
    def get_value_constraint_compumethod_path(cls, ar_dt, data_type):
        constraint_path_list = []
        compumethod_path_list = []
        constraint_path = None
        compumethod_path = None
        if hasattr(ar_dt, "SW_DATA_DEF_PROPS"):
            conditional = ar_dt.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[0]
            if hasattr(conditional, "DATA_CONSTR_REF") and conditional.DATA_CONSTR_REF is not None:
                constraint_path = utils.get_valueOf(conditional.DATA_CONSTR_REF)
            if hasattr(conditional, "COMPU_METHOD_REF") and conditional.COMPU_METHOD_REF is not None:
                compumethod_path = utils.get_valueOf(conditional.COMPU_METHOD_REF)
            if constraint_path:
                constraint_path_list.append(constraint_path)
            if compumethod_path:
                compumethod_path_list.append(compumethod_path)
        return constraint_path_list, compumethod_path_list

    @classmethod
    def __parse_irv(cls, irv_dict, irv, swc_inst, is_implicit):
        name = utils.get_short_name(irv)
        if not irv.TYPE_TREF:
            return
        idt_path = utils.get_valueOf(irv.TYPE_TREF)
        if idt_path not in cls.datatype_path_to_idt_mapping:
            return
        datatype = cls.datatype_path_to_idt_mapping[idt_path]["idt"]
        init_value = cls.__get_variable_data_prototype_init_value(irv, datatype)
        irv_dict[irv.get_path()] = {
            "name": name,
            "is_implicit": is_implicit,
            "datatype": datatype,
            "buff": f"Rte_Irv_{swc_inst}_{name}",
            "init_value": init_value,
            "adt_path": None,
            "idt_path": idt_path,
            "w": [],
            "r": [],
            "m_to_n": "0",
        }

    @classmethod
    def __get_variable_data_prototype_init_value(cls, vdp, idt_info):
        ar_init_value = vdp.INIT_VALUE
        if not ar_init_value:
            init_value = None
        elif ar_init_value.CONSTANT_REFERENCE:
            init_value = cls.__parse_sr_init_value_by_const_reference(ar_init_value, idt_info)
        else:
            init_value = cls.__parse_sr_init_value_by_value_definition(ar_init_value, idt_info)
        return init_value

    @classmethod
    def __parse_irv_access_point(cls, access_point, access_type, swc_type, swc_inst, runnable_obj, irv_dict):
        data_element_path = utils.get_valueOf(access_point.ACCESSED_VARIABLE.LOCAL_VARIABLE_REF)
        data = irv_dict["data"].get(data_element_path, {})
        if not data:
            logger.error(f"Unknown IRV access: {data_element_path}")
            return
        runnable_symbol = utils.get_runnable_symbol(runnable_obj)
        run_var = f"{runnable_symbol}_{data['name']}"
        access_key = f"{access_type}_{run_var}"

        if access_key not in irv_dict[access_type]:
            curr_access = {
                "access_key": access_key,
                "run_var": run_var,
                "access_type": access_type,
                "swc_type": swc_type,
                "swc_inst": swc_inst,
                "m_to_n": "0",
                "lock": "NONE",
                "data": data,
                "runnable": [runnable_symbol],
                "task": [cls.runnable_tasks[runnable_symbol]] if runnable_symbol in cls.runnable_tasks else [],
                "osapplication": (
                    cls.component_osapplications[swc_type] if swc_type in cls.component_osapplications else None
                ),
            }
            if data["is_implicit"]:
                curr_access["buff_imp_copy"] = (
                    f"{data['buff']}_{curr_access['task'][0]}" if curr_access["task"] else None
                )

            if curr_access["task"] and curr_access["osapplication"]:
                irv_dict[access_type][access_key] = curr_access
                data[access_type].append(curr_access)
            else:
                logger.error(f"IRV access task / osa not found: {run_var} - {runnable_symbol} - {swc_type}")
        else:
            # nothing to update yet
            pass

    @classmethod
    def __update_irv_m_to_n(cls, irv_dict):
        unused_data_path = set()
        for data_path, data in irv_dict["data"].items():
            # sort
            if data["w"]:
                data["w"].sort(key=lambda x: x["access_key"])
            if data["r"]:
                data["r"].sort(key=lambda x: x["access_key"])

            # check m:n
            if data["w"] and data["r"]:
                len_w = len(data["w"])
                len_r = len(data["r"])
                m_to_n = "0"
                if len_w > 1 and len_r > 1:
                    m_to_n = "mn"
                elif len_w > 1:
                    m_to_n = "n1"
                elif len_r > 1:
                    m_to_n = "1n"
                else:
                    m_to_n = "11"
                for access in data["w"]:
                    access["m_to_n"] = m_to_n
                for access in data["r"]:
                    access["m_to_n"] = m_to_n
                data["m_to_n"] = m_to_n
            elif (not data["w"]) and (not data["r"]):
                unused_data_path.add(data_path)
        for path in unused_data_path:
            del irv_dict["data"][path]

    @classmethod
    def __update_irv_lock(cls, irv_dict):
        for _, data in irv_dict["data"].items():
            if data["m_to_n"] == "0":
                continue

            # opt data type
            if (
                data["datatype"]["native_category"] == "NUMERICAL"
                and data["datatype"]["basetype"] in cls.AUTOMIC_DATATYPES
            ):
                continue

            # opt exec in one task
            task = None
            has_multi_task = False
            for access in data["w"]:
                if task:
                    if task != access["task"][0]:
                        has_multi_task = True
                        break
                else:
                    task = access["task"][0]
            if not has_multi_task:
                continue
            for access in data["r"]:
                if task != access["task"][0]:
                    has_multi_task = True
                    break
            if not has_multi_task:
                continue

            # opt base on task schduling
            all_access = data["w"] + data["r"]
            if cls.is_ea_opt_enabled:
                access_to_task_info_dict, highest_access_task_priority = cls.__process_all_tasks(
                    all_access, "access_key"
                )
                for access in all_access:
                    curr_lock = "NONE"
                    for task_info in access_to_task_info_dict[access["access_key"]]:
                        if task_info[0] < highest_access_task_priority and task_info[1]:
                            curr_lock = "OSISR"
                            break
                    access["lock"] = curr_lock
            else:
                for access in all_access:
                    access["lock"] = "OSISR"

    @classmethod
    def __parse_swc_type_irv(cls, ar_swc_type):
        irv_dict = {"data": {}, "w": {}, "r": {}}
        swc_type = utils.get_short_name(ar_swc_type)
        swc_inst = cls.sw_component_prototypes[swc_type][0] if swc_type in cls.sw_component_prototypes else swc_type
        if not hasattr(ar_swc_type, "INTERNAL_BEHAVIORS"):
            return
        for behavior in ar_swc_type.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR:
            if hasattr(behavior, "EXPLICIT_INTER_RUNNABLE_VARIABLES") and behavior.EXPLICIT_INTER_RUNNABLE_VARIABLES:
                for exp_irv in behavior.EXPLICIT_INTER_RUNNABLE_VARIABLES.VARIABLE_DATA_PROTOTYPE:
                    cls.__parse_irv(irv_dict["data"], exp_irv, swc_inst, False)
            if hasattr(behavior, "IMPLICIT_INTER_RUNNABLE_VARIABLES") and behavior.IMPLICIT_INTER_RUNNABLE_VARIABLES:
                for imp_irv in behavior.IMPLICIT_INTER_RUNNABLE_VARIABLES.VARIABLE_DATA_PROTOTYPE:
                    cls.__parse_irv(irv_dict["data"], imp_irv, swc_inst, True)
        irv_dict["data"] = dict(sorted(irv_dict["data"].items()))

        for behavior in ar_swc_type.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR:
            if (not hasattr(behavior, "RUNNABLES")) or (not behavior.RUNNABLES):
                continue
            for runnable_entity in behavior.RUNNABLES.RUNNABLE_ENTITY:
                if runnable_entity.WRITTEN_LOCAL_VARIABLES:
                    for access in runnable_entity.WRITTEN_LOCAL_VARIABLES.VARIABLE_ACCESS:
                        cls.__parse_irv_access_point(access, "w", swc_type, swc_inst, runnable_entity, irv_dict)
                if runnable_entity.READ_LOCAL_VARIABLES:
                    for access in runnable_entity.READ_LOCAL_VARIABLES.VARIABLE_ACCESS:
                        cls.__parse_irv_access_point(access, "r", swc_type, swc_inst, runnable_entity, irv_dict)

        cls.__update_irv_m_to_n(irv_dict)
        cls.__update_irv_lock(irv_dict)
        irv_dict["w"] = dict(sorted(irv_dict["w"].items()))
        irv_dict["r"] = dict(sorted(irv_dict["r"].items()))
        return irv_dict

    @classmethod
    def __parse_pim_with_ar_type(cls, pim_dict, swc_type, swc_inst, pim):
        name = utils.get_short_name(pim)
        if name in pim_dict:
            return
        idt_path = utils.get_valueOf(pim.TYPE_TREF)
        datatype = cls.datatype_path_to_idt_mapping[idt_path]["idt"]
        pim_dict["name"] = {
            "name": name,
            "swc_type": swc_type,
            "swc_inst": swc_inst,
            "datatype": datatype,
            "buff": f"Rte_{swc_inst}_{name}",
            "buff_type": datatype["name"],
            "init_value": cls.__get_variable_data_prototype_init_value(pim, datatype),
        }

    @classmethod
    def __parse_pim(cls, pim_dict, type_def_dict, swc_type, swc_inst, pim):
        name = utils.get_short_name(pim)
        if name in pim_dict:
            return
        if (not pim.TYPE) or (not pim.TYPE_DEFINITION):
            return
        pim_type = utils.get_valueOf(pim.TYPE)
        pim_type_def = utils.get_valueOf(pim.TYPE_DEFINITION)
        curr_type_def_key = f"{pim_type_def} {pim_type}"

        curr_pim = {
            "name": name,
            "swc_type": swc_type,
            "swc_inst": swc_inst,
            "pim_type": pim_type,
            "pim_type_def": pim_type_def,
            "buff": f"Rte_{swc_inst}_{name}",
            "buff_type": f"Rte_PimType_{swc_type}_{pim_type}",
            "init_value": None,
        }
        pim_dict[name] = curr_pim
        if curr_type_def_key not in type_def_dict:
            type_def_dict[curr_type_def_key] = curr_pim

    @classmethod
    def __parse_swc_type_pim(cls, ar_swc_type):
        pim_dict = {"ar_typed": {}, "user_defined": {}, "type_def": {}}
        if not hasattr(ar_swc_type, "INTERNAL_BEHAVIORS"):
            return
        swc_type = utils.get_short_name(ar_swc_type)
        swc_inst = cls.sw_component_prototypes[swc_type][0] if swc_type in cls.sw_component_prototypes else swc_type
        for behavior in getattr(getattr(ar_swc_type, "INTERNAL_BEHAVIORS", None), "SWC_INTERNAL_BEHAVIOR", []):
            if hasattr(behavior, "AR_TYPED_PER_INSTANCE_MEMORYS") and behavior.AR_TYPED_PER_INSTANCE_MEMORYS:
                for pim in behavior.AR_TYPED_PER_INSTANCE_MEMORYS.VARIABLE_DATA_PROTOTYPE:
                    cls.__parse_pim_with_ar_type(pim_dict["ar_typed"], swc_type, swc_inst, pim)
            if hasattr(behavior, "PER_INSTANCE_MEMORYS") and behavior.PER_INSTANCE_MEMORYS:
                for pim in behavior.PER_INSTANCE_MEMORYS.PER_INSTANCE_MEMORY:
                    cls.__parse_pim(pim_dict["user_defined"], pim_dict["type_def"], swc_type, swc_inst, pim)
        pim_dict["ar_typed"] = dict(sorted(pim_dict["ar_typed"].items()))
        pim_dict["user_defined"] = dict(sorted(pim_dict["user_defined"].items()))
        pim_dict["type_def"] = dict(sorted(pim_dict["type_def"].items()))
        return pim_dict

    @classmethod
    def parse_sw_component_type(cls, sw_component_type):
        sw_component_type_dict = {}
        info_from_port = {"constraints": {}, "compu_methods": {"adt": {}, "idt": {}}}
        sw_component_type_dict["name"] = utils.get_short_name(sw_component_type)
        sw_component_type_dict["type"] = sw_component_type.get_tag()
        sw_component_type_dict["pports"] = cls.parse_sw_component_type_pports(sw_component_type, info_from_port)
        sw_component_type_dict["rports"] = cls.parse_sw_component_type_rports(sw_component_type, info_from_port)
        sw_component_type_dict["pim"] = cls.__parse_swc_type_pim(sw_component_type)
        sw_component_type_dict["irv"] = cls.__parse_swc_type_irv(sw_component_type)
        sw_component_type_dict["runnables"] = cls.parse_sw_component_type_runnables(sw_component_type)
        sw_component_type_dict["osapplication"] = cls.__parse_sw_component_type_osapplication(
            utils.get_short_name(sw_component_type)
        )
        sw_component_type_dict["core_id"] = cls.__parse_sw_component_type_core_id(
            utils.get_short_name(sw_component_type)
        )
        sw_component_type_dict["constraints"] = info_from_port["constraints"]
        sw_component_type_dict["compu_methods"] = info_from_port["compu_methods"]
        return sw_component_type_dict

    @classmethod
    def __parse_sw_component_type_osapplication(cls, swc_name):
        osa_tm = cls.component_osapplications.get(swc_name, None)
        osa_ep = list(cls.swc_osa_from_ep[swc_name])[0] if cls.swc_osa_from_ep.get(swc_name, set()) else None
        swc_osapplication = osa_tm if osa_tm is not None else osa_ep
        return swc_osapplication

    @classmethod
    def __parse_sw_component_type_core_id(cls, swc_name):
        core_id_tm = cls.component_core_id.get(swc_name, None)
        core_id_ep = (
            list(cls.swc_core_id_from_ep[swc_name])[0] if cls.swc_core_id_from_ep.get(swc_name, set()) else None
        )
        swc_core_id = core_id_tm if core_id_tm is not None else core_id_ep
        return swc_core_id

    @classmethod
    def parse_delegation_sw_connector(cls, composition_sw_component_type, com_signals=None):
        delegation_sw_connector_dict = {}
        if (
            not com_signals
            or not composition_sw_component_type.CONNECTORS
            or not composition_sw_component_type.CONNECTORS.DELEGATION_SW_CONNECTOR
        ):
            return delegation_sw_connector_dict
        delegation_sw_connectors = composition_sw_component_type.CONNECTORS.DELEGATION_SW_CONNECTOR
        for delegation_connector in delegation_sw_connectors:
            connection = {
                "signal_name": None,
                "signal_category": None,
                "signals": [],
                "swc": None,
                "port_interface_name": None,
                "port_name": None,
                "port_type": None,
            }
            # pass CS connection
            com_signal_name = delegation_connector.OUTER_PORT_REF.valueOf_.split("/")[-1]
            pport_ref = delegation_connector.INNER_PORT_IREF.P_PORT_IN_COMPOSITION_INSTANCE_REF
            rport_ref = delegation_connector.INNER_PORT_IREF.R_PORT_IN_COMPOSITION_INSTANCE_REF
            if pport_ref:
                com_signal_direction = "SEND"
                pport_swc_name = pport_ref.CONTEXT_COMPONENT_REF.valueOf_.split("/")[-1]
                pport_name = pport_ref.TARGET_P_PORT_REF.valueOf_.split("/")[-1]
                connection["swc"] = pport_swc_name
                pport = composition_sw_component_type.find(pport_ref.TARGET_P_PORT_REF.valueOf_)
                if pport:
                    pport_interface_name = pport.PROVIDED_INTERFACE_TREF.valueOf_.split("/")[-1]
                    connection["port_interface_name"] = pport_interface_name
                else:
                    continue
                connection["port_name"] = pport_name
                connection["port_type"] = "pport"
            elif rport_ref:
                com_signal_direction = "RECEIVE"
                rport_swc_name = rport_ref.CONTEXT_COMPONENT_REF.valueOf_.split("/")[-1]
                rport_name = rport_ref.TARGET_R_PORT_REF.valueOf_.split("/")[-1]
                connection["swc"] = rport_swc_name
                rport = composition_sw_component_type.find(rport_ref.TARGET_R_PORT_REF.valueOf_)
                if rport:
                    rport_interface_name = rport.REQUIRED_INTERFACE_TREF.valueOf_.split("/")[-1]
                    connection["port_interface_name"] = rport_interface_name
                else:
                    continue
                connection["port_name"] = rport_name
                connection["port_type"] = "rport"
            else:
                continue

            if com_signal_name in com_signals and com_signal_direction == com_signals[com_signal_name]["direction"]:
                pass
            else:
                for signal_name, signal_info in com_signals.items():
                    if (
                        signal_name.startswith(f"{com_signal_name}_o")
                        and com_signal_direction == signal_info["direction"]
                    ):
                        com_signal_name = signal_name
                        break
                else:
                    continue
            if com_signals[com_signal_name]["signal_category"] == "signal":
                connection["signal_category"] = "Signal"
            elif com_signals[com_signal_name]["signal_category"] == "signal_group":
                connection["signal_category"] = "SignalGroup"
                connection["signals"] = []
                for group_signal_name, group_signal_info in com_signals[com_signal_name]["signals"].items():
                    signalgroups_signal = {"signal_name": group_signal_name, "type": group_signal_info["datatype"]}
                    connection["signals"].append(signalgroups_signal)
            else:
                continue
            connection["signal_name"] = com_signal_name

            delegation_sw_connector_dict.update({utils.get_short_name(delegation_connector): connection})
        return delegation_sw_connector_dict

    @classmethod
    def __get_com_proxy_task(cls, rte_com_proxy_entity_name):
        if rte_com_proxy_entity_name in cls.runnable_tasks:
            proxy_task = cls.runnable_tasks[rte_com_proxy_entity_name]
            return [proxy_task] if proxy_task else []
        else:
            return []

    @classmethod
    def __update_sr_data_mapping_find_mapping(cls, port, data_mappings_info, is_p_port):
        if port.get("port_interface_type", None) != "sr":
            return False, [], {}
        if port["is_prport"]:
            return False, [], {}

        direction = "Tx" if is_p_port else "Rx"
        system_signal_isignals = data_mappings_info[1]
        port_datatype = port.get("arg", {}).get("datatype", {})
        system_signal_type = (
            "system_signal_group" if port_datatype["native_category"] == "STRUCTURE" else "system_signal"
        )

        curr_mappings = []
        curr_type_mappings = {}
        dm_key = f"{port['component']}/{port['port_prototype']}/{port['data_element']}"
        # signal
        system_singal_refs = data_mappings_info[0]["sr_signal_mappings"].get(dm_key, {})
        if system_singal_refs:
            for system_singal_ref in system_singal_refs["system_singal_refs"]:
                system_singal_name = system_singal_ref.split("/")[-1]
                signal_info = system_signal_isignals[direction][system_signal_type].get(system_singal_name, None)
                if signal_info is None:
                    continue
                curr_mappings.append(signal_info)
        # signal group
        system_singal_refs = data_mappings_info[0]["sr_signal_group_mappings"].get(dm_key, {})
        if system_singal_refs:
            for system_singal_ref in system_singal_refs["system_singal_refs"]:
                system_singal_name = system_singal_ref.split("/")[-1]
                signal_info = system_signal_isignals[direction][system_signal_type].get(system_singal_name, None)
                if signal_info is None:
                    continue
                full_name = signal_info["full_name"]
                curr_mappings.append(signal_info)
                curr_type_mappings.update({full_name: system_singal_refs["type_mappings"][system_singal_ref]})
                for type_mapping in curr_type_mappings[full_name]:
                    system_signal = type_mapping["system_signal"]
                    i_signal_name = signal_info["system_signal_to_i_signal"].get(system_signal)
                    type_mapping["i_signal"] = i_signal_name

        if curr_mappings:
            port["data_mapping_details"] = curr_mappings
            port["mapping_to_signals"] = [i_signal["full_name"] for i_signal in curr_mappings]
            port["mapping_to_signals"].sort()
            return True, curr_mappings, curr_type_mappings
        else:
            return False, [], {}

    @classmethod
    def __update_sr_data_mapping_update_port(
        cls, port, com_signals_dict, signal_ports, signal_dict, is_p_port, curr_mappings, curr_type_mappings
    ):
        compu_method = {}
        real_sig_type = {}
        port_datatype = port.get("arg", {}).get("datatype", {})
        signal_type = "SignalGroup" if port_datatype["native_category"] == "STRUCTURE" else "Signal"
        if signal_type == "Signal":
            for i_signal in curr_mappings:
                compu_method.update({i_signal["full_name"]: i_signal["compu_method"]})
                real_sig_type.update({i_signal["full_name"]: i_signal["real_sig_type"]})
        elif signal_type == "SignalGroup":
            for signal_groups in curr_mappings:
                compu_method.update({signal_groups["full_name"]: {}})
                real_sig_type.update({signal_groups["full_name"]: {}})
                for sig_name, sig_value in signal_groups["system_signal"].items():
                    compu_method[signal_groups["full_name"]].update({sig_name: sig_value["compu_method"]})
                    real_sig_type[signal_groups["full_name"]].update({sig_name: sig_value["real_sig_type"]})
        port["signal_category"] = signal_type
        port["type_mappings"] = curr_type_mappings

        if not is_p_port:
            port["Direction"] = "Rx"
            runnable_symbol = port["symbol"]
            event_list = cls.__parse_sr_port_wait_events({"name": port["port_var"], "runnable": runnable_symbol})
            port["trigger_event_list"] = event_list
            if len(event_list):
                port["trigger_event"] = "On_Data_Reception"
            else:
                port["trigger_event"] = "Periodic"
        else:
            port["trigger_event"] = "Periodic"
            port["Direction"] = "Tx"
        signal_ports.append(port)

        for signal_name in port["mapping_to_signals"]:
            dir_key = "tx" if port["Direction"] == "Tx" else "rx"
            if signal_name not in signal_dict[dir_key]:
                com_signal_info = cls.__get_com_signal_info(signal_name, port["Direction"], com_signals_dict)
                if not com_signal_info["osa"] or com_signal_info["osa"] not in cls.all_osa_set:
                    com_signal_info["osa"] = cls.all_osa[0]
                    logger.error(f"ComSignal osa not found: {signal_name}")

                _, proxy_name = cls.__get_proxy_name(com_signal_info["osa"], com_signal_info["signal_com_func_period"])
                signal_dict[dir_key][signal_name] = {
                    "name": signal_name,
                    "category": "com",
                    "signal_type": signal_type,
                    "conn_sr_port": [],
                    "direction": port["Direction"],
                    "data_received_event": [],
                    "enable_update": [],
                    "handle_never_received": [],
                    "alive_timeout": [],
                    "datatype": None,
                    "proxy_name": proxy_name,
                    "task": cls.__get_com_proxy_task(proxy_name),
                    "is_signal_group": (signal_type == "SignalGroup"),
                }
                signal_dict[dir_key][signal_name].update(com_signal_info)

                if signal_type == "Signal":
                    signal_dict[dir_key][signal_name].update({"compu_method": compu_method[signal_name]})
                    signal_dict[dir_key][signal_name].update({"real_sig_type": real_sig_type[signal_name]})
                elif signal_type == "SignalGroup":
                    signal_dict[dir_key][signal_name].update({"compu_method": compu_method})
                    signal_dict[dir_key][signal_name].update({"real_sig_type": real_sig_type})
            signal_dict[dir_key][signal_name]["conn_sr_port"].append(port)

    @classmethod
    def __update_sr_constr_and_compumethod_intra_ecu_each_port(cls, port, visited_ports):
        if not cls.__is_sr_nonq_port(port):
            return
        if port["m_to_n"] in {"0", "mn"}:
            return
        if port["port_full_key"] in visited_ports:
            return
        all_non_q_participant_ports = port["sr_port_group"]
        visited_ports.update(port["port_full_key"] for port in all_non_q_participant_ports)

        # TODO: update intra ecu constr and cm

    @classmethod
    def __update_sr_constr_and_compumethod_intra_ecu(cls, asw_dict):
        """
        update constraints and compu-methods of ADT & IDT
        """
        if not cls.constraints and not cls.compu_methods:
            return

        # port mapping
        visited_ports_intra_ecu = set()
        for _, swc_info in asw_dict.items():
            for _, port in swc_info["pports"].items():
                cls.__update_sr_constr_and_compumethod_intra_ecu_each_port(port, visited_ports_intra_ecu)
            for _, port in swc_info["rports"].items():
                cls.__update_sr_constr_and_compumethod_intra_ecu_each_port(port, visited_ports_intra_ecu)

    @classmethod
    def __update_sr_constr_and_compumethod_inter_ecu(cls, port_signal_group_list, is_tx):
        data_mapping_m_to_n = port_signal_group_list[0][0]["data_mapping_m_to_n"]
        if (is_tx and data_mapping_m_to_n != "n1") and (not is_tx and data_mapping_m_to_n != "1n"):
            return
        sig_osa = port_signal_group_list[1][0]["osa"]
        if sig_osa not in cls.sr_dm_glob_vars["macro"]["compu_method"]:
            cls.sr_dm_glob_vars["macro"]["compu_method"][sig_osa] = {}
        for port in port_signal_group_list[0]:
            if not port["compu_methods"]:
                continue
            cls.sr_dm_glob_vars["macro"]["compu_method"][sig_osa].update(port["compu_methods"])

    @classmethod
    def __update_sr_data_mapping(cls, asw_dict, data_mappings_info, task_mapping_info, com_cfg_dict, cfg_dict):
        dm_cfg = {
            "signals_and_signalgroups": [],
            "data_received_event_list": [],
            "port_event_id_and_task_id": [],
            "sr_required_com_specs_dict": {},
            "signal_dict": {
                "tx": {},
                "rx": {},
                "tx_proxy": {},
            },
            "glob_vars": {},
        }
        if not com_cfg_dict:
            cls.__update_sr_data_mapping_update_codegen_data(dm_cfg, cfg_dict)
            return

        cls.__update_sr_data_mapping_asw_port(asw_dict, data_mappings_info, task_mapping_info, com_cfg_dict, dm_cfg)
        cls.__update_sr_data_mapping_extra_info(dm_cfg["signal_dict"])
        cls.__update_sr_data_mapping_rte_macro_api_codegen_data(asw_dict)

        dm_cfg["sr_required_com_specs_dict"] = cls.__get_data_mapping_sr_rport_by_required_com_specs(cfg_dict)
        dm_cfg["glob_vars"] = cls.__sorted_sr_dm_glob_vars()
        cls.__update_sr_data_mapping_update_codegen_data(dm_cfg, cfg_dict)

    @classmethod
    def __dm_compu_method_phy_eq_raw(cls, port):
        if cls.signal_compu_method_enabled is False:
            return True
        for data_mapping_detail in port["data_mapping_details"]:
            if not data_mapping_detail.get("compu_method", {}).get("phy_eq_raw", False):
                return False
        return True

    @classmethod
    def __update_sr_data_mapping_rte_macro_api_codegen_data(cls, asw_dict):
        def __port_generate_rte_macro_api(port):
            if port["type"] not in ["Explicit Receiver", "Explicit Sender"]:
                return False
            if port.get("signal_category", "None") != "Signal":
                return False
            if port["m_to_n"] not in ["0", "mn"]:
                return False
            if (
                len(port["data_mapping_details"]) == 0
                or len(port["mapping_to_signals"]) == 0
                or port["data_mapping_m_to_n"] == "0"
            ):
                return False
            if port["data_mapping_has_inter_osa_same_core"] or port["data_mapping_has_inter_core"]:
                return False
            if not cls.__dm_compu_method_phy_eq_raw(port):
                return False
            if port["type"] == "Explicit Receiver":
                data_mapping_flag = port["data_mapping_flag"]
                if len(data_mapping_flag.get("is_updated", [])) > 0:
                    return False
                if len(data_mapping_flag.get("is_received", [])) > 0:
                    return False
                if len(data_mapping_flag.get("is_timeout", [])) > 0:
                    return False
                if len(port["trigger_event_list"]) > 0:
                    return False
                if port["data_mapping_m_to_n"] == "11" and cls.is_datamapping_opt_rx_1_1 is False:
                    return True
                elif port["data_mapping_m_to_n"] == "1n" and cls.is_datamapping_opt_rx_1_n is False:
                    return True
            return False

        if cls.rte_dlog_enabled:
            return
        for _, swc in asw_dict.items():
            for _, port in swc.get("rports", {}).items():
                port["dm_macro_api"] = __port_generate_rte_macro_api(port)

    @classmethod
    def __update_sr_data_mapping_asw_port(
        cls, asw_dict, data_mappings_info, task_mapping_info, com_cfg_dict, data_mapping_cfg
    ):
        if not data_mappings_info or not data_mappings_info[0] or not data_mappings_info[1]:
            return

        signal_ports = []
        signal_dict = {"tx": {}, "rx": {}, "tx_proxy": {}}
        com_signals_dict = com_cfg_dict.get("ComConfig", {}).get("ComSignals_totle", {})

        for _, swc_info in asw_dict.items():
            for _, pport in swc_info["pports"].items():
                ret, curr_mappings, curr_type_mappings = cls.__update_sr_data_mapping_find_mapping(
                    pport, data_mappings_info, True
                )
                if ret:
                    cls.__update_sr_data_mapping_update_port(
                        pport, com_signals_dict, signal_ports, signal_dict, True, curr_mappings, curr_type_mappings
                    )
            for _, rport in swc_info["rports"].items():
                ret, curr_mappings, curr_type_mappings = cls.__update_sr_data_mapping_find_mapping(
                    rport, data_mappings_info, False
                )
                if ret:
                    cls.__update_sr_data_mapping_update_port(
                        rport, com_signals_dict, signal_ports, signal_dict, False, curr_mappings, curr_type_mappings
                    )

        data_mapping_cfg["signal_dict"]["tx"] = dict(sorted(signal_dict["tx"].items()))
        data_mapping_cfg["signal_dict"]["rx"] = dict(sorted(signal_dict["rx"].items()))
        data_mapping_cfg.update(cls.get_data_receive_event(signal_ports, task_mapping_info))

    @classmethod
    def __get_com_signal_info(cls, signal_name, direction, com_signals_dict):
        DEAULT_TX_PERIOD = 5
        com_signal_name = f"{signal_name}_{direction}"
        rte_com_signal_info = {
            "is_signal_periodic": False,
            "signal_period": DEAULT_TX_PERIOD,
            "signal_com_func_period": None,
            "signal_com_func_name": None,
            "osa": None,
            "core_id": 0,
            "rte_init_state": "Rte_InitState",
        }
        if com_signal_name not in com_signals_dict:
            return rte_com_signal_info
        com_signal_info = com_signals_dict[com_signal_name]
        rte_com_signal_info["is_signal_periodic"] = com_signal_info.get("Rte_GetTxModeMode", "NONE") == "PERIODIC"
        rte_com_signal_info["signal_period"] = (
            com_signal_info["Rte_GetPeriodTime"] if "Rte_GetPeriodTime" in com_signal_info else DEAULT_TX_PERIOD
        )
        rte_com_signal_info["signal_com_func_period"] = (
            com_signal_info["Rte_GetMainFunctionTime"]
            if "Rte_GetMainFunctionTime" in com_signal_info
            else DEAULT_TX_PERIOD
        )
        rte_com_signal_info["signal_com_func_name"] = (
            com_signal_info["Rte_GetMainFunctionName"]
            if "Rte_GetMainFunctionName" in com_signal_info
            else DEAULT_TX_PERIOD
        )
        rte_com_signal_info["osa"] = com_signal_info.get("application", None)
        rte_com_signal_info["core_id"] = com_signal_info.get("CoreRef", 0)
        # add postfix if core-id is non zero
        rte_com_signal_info["rte_init_state"] = (
            f"Rte_InitState_{rte_com_signal_info['core_id']}" if rte_com_signal_info["core_id"] else "Rte_InitState"
        )
        return rte_com_signal_info

    @classmethod
    def get_data_receive_event(cls, signal_ports, task_mappings_info):
        data_mapping_cfg = {
            "signals_and_signalgroups": [],
            "data_received_event_list": [],
            "port_event_id_and_task_id": [],
        }
        data_mapping_cfg["data_received_event_list"] = cls.get_on_data_reception_trigger_runnable_data_mapping_ports(
            signal_ports, task_mappings_info
        )
        return data_mapping_cfg

    @classmethod
    def get_on_data_reception_trigger_runnable_data_mapping_ports(cls, signal_ports, task_mappings_info):
        data_received_event_dict = {}
        for signal_port in signal_ports:
            event_list = cls.__parse_sr_port_wait_events(
                {"name": signal_port.get("name", ""), "runnable": signal_port.get("symbol", "")}
            )
            if "On_Data_Reception" == signal_port.get("trigger_event", None):
                for signal_or_signalgroup_name in signal_port.get("mapping_to_signals", []):
                    if signal_port.get("signal_category", None) not in ["Signal", "SignalGroup"]:
                        continue
                    data_received_event = dict.fromkeys(["port_name", "port_alias_name", "event_type"])
                    data_received_event["port_name"] = signal_or_signalgroup_name
                    data_received_event["port_alias_name"] = signal_or_signalgroup_name
                    data_received_event["signal_or_signalgroup"] = signal_or_signalgroup_name
                    data_received_event["event_type"] = "DataReceivedEvent"
                    data_received_event["task_event_id"] = []
                    if data_received_event["port_name"] not in data_received_event_dict.keys():
                        data_received_event_dict[data_received_event["port_name"]] = data_received_event
                    for event in event_list:
                        port_event_id_and_task_id_dict = {"port_name": "", "task_id": "", "event_id": ""}
                        port_event_id_and_task_id_dict["task_id"] = event.get("task_id", "")
                        port_event_id_and_task_id_dict["event_id"] = event.get("event_mask", "")
                        if (
                            port_event_id_and_task_id_dict
                            in data_received_event_dict[data_received_event["port_name"]]["task_event_id"]
                        ):
                            continue
                        data_received_event_dict[data_received_event["port_name"]]["task_event_id"].append(
                            port_event_id_and_task_id_dict
                        )
        return list(data_received_event_dict.values())

    @classmethod
    def get_data_mapping_config_event_id_and_task_id(cls, runnable_name, task_mappings_info):
        port_event_id_and_task_id = []
        for key, value in task_mappings_info.items():
            for j in range(len(value["schedulable_entity_info_list"])):
                if runnable_name == value["schedulable_entity_info_list"][j]["name"]:
                    port_event_id_and_task_id_dict = {"port_name": "", "task_id": "", "event_id": ""}
                    port_event_id_and_task_id_dict["task_id"] = key
                    port_event_id_and_task_id_dict["event_id"] = value["schedulable_entity_info_list"][j]["event_mask"]
                    if port_event_id_and_task_id_dict in port_event_id_and_task_id:
                        continue
                    port_event_id_and_task_id.append(port_event_id_and_task_id_dict)
        return port_event_id_and_task_id

    @classmethod
    def get_signals_and_signalgroups(cls, signals):
        """
        Get the signal and SignalGroup for which Data Mapping has been done.
        Arg:
        signals : all signals.

        Return:
        Returns a list of signals and signalGroups.
        """

        signals_and_signalgroups_dict = {}

        for signal in signals:
            signals_and_signalgroups = {
                "signal_name": "",
                "softwareCompositionRef": "",
                "componentPrototypeRef": "",
                "portPrototypeRef": "",
                "is_group": "",
                "type": "",
                "runnable": "",
                "trigger_mode": "",
                "signals": [],
            }
            if "Signal" == signal["signal_category"]:
                signals_and_signalgroups["signal_name"] = signal["com_signal_name"]
                signals_and_signalgroups["type"] = signal["arg"]["datatype"]
            elif "SignalGroup" == signal["signal_category"]:
                signals_and_signalgroups["signal_name"] = signal["com_signal_name"]
                signals_and_signalgroups["signals"] = signal["signals"]
            else:
                continue
            signals_and_signalgroups["is_group"] = signal["signal_category"]
            signals_and_signalgroups["runnable"] = signal["runnable"]
            signals_and_signalgroups["trigger_mode"] = signal["trigger_event"]
            if signals_and_signalgroups["signal_name"] in signals_and_signalgroups_dict and (
                signals_and_signalgroups_dict[signals_and_signalgroups["signal_name"]]["trigger_mode"]
                == "On_Data_Reception"
            ):
                continue
            signals_and_signalgroups_dict[signals_and_signalgroups["signal_name"]] = signals_and_signalgroups
        return list(signals_and_signalgroups_dict.values())

    @classmethod
    def parse_data_mapping_signals(cls, signals, signals_and_signalgroups):
        """
        Processing signals from data mapping excel.

        Arg:
        signals: signals from EXCEL;
        signals_and_signalgroups: all signals and signalgroups that are mapped.

        Return:
        Returns all mapped ports and their mappings,
        and returns all ports that are set to On_data_reception.
        """

        ports = []
        data_received_event_dict = {}

        for signal in signals:
            signal_name = signal["com_signal_name"]
            # message_name = signal["Message"]
            direction = signal["Direction"]
            signal_category = signal["signal_category"]
            data_type = signal["arg"]["datatype"]
            signal_group_name = None
            timeout = None
            component_name = signal["component"]
            runnable_name = signal["runnable"]
            trigger_mode = signal["trigger_event"]
            port = {
                "port_name": signal_name,
                "direction": direction,
                "signal_category": signal_category,
                "data_type": data_type,
                "signal_group_name": signal_group_name,
                "timeout": timeout,
                "component_name": component_name,
                "runnable_name": runnable_name,
                "trigger_mode": trigger_mode,
                "port_access_mode": None,
            }

            port_name, category = cls.get_port_name(port, signals_and_signalgroups)
            cls.get_data_received_event_dict(port, trigger_mode, port_name, data_received_event_dict)
            ports.append(port)
        return list(data_received_event_dict.values())

    @classmethod
    def get_port_name(cls, port, signals_and_signalgroups):
        """
        Get all the ports. If it is a signal group,
        the signal group name will be used as the port name.

        Arg:
            port: port from EXCEL;
            signals_and_signalgroups: all signals and signalgroups that are mapped.

        Return:
            a dictionary of all ports.
        """
        for i in range(len(signals_and_signalgroups)):
            if signals_and_signalgroups[i]["signal_name"] == port["port_name"]:
                port_name = port["port_name"]
                category = "TYPE_REFERENCE"
                if "double64" == port["data_type"]:
                    category = "ARRAY"
                break
            else:
                for k in range(len(signals_and_signalgroups[i]["signals"])):
                    if signals_and_signalgroups[i]["signals"][k]["signal_name"] == port["port_name"]:
                        port_name = port["signal_group_name"]
                        category = "STRUCTURE"
                        break
        return port_name, category

    @classmethod
    def get_data_received_event_dict(cls, port, trigger_mode, port_name, data_received_event_dict):
        """
        Get the port of the data recevied event.

        Arg:
        trigger_mode: trigger mode;
        port_name: port name;

        """
        if "On_Data_Reception" == trigger_mode:
            data_received_event = dict.fromkeys(["port_name", "event_type"])
            data_received_event["port_name"] = port_name
            data_received_event["port_alias_name"] = port_name
            data_received_event["event_type"] = "DataReceivedEvent"
            data_received_event_dict[port_name] = data_received_event

    @classmethod
    def data_mapping_config_event_id_and_task_id(cls, data_mapping_config, task_mappings_info):
        """
        Get the port associated with the task_id and event_id.

        It is used to generate Cbk interfaces to provide COM module calls.
        As follows:
        [
        {
            "port_name": "***",
            "task_id": "Default_Appl_Task_Core0",
            "event_id": "Rte_Ev_Run_CAN_Outputs_CAN_Outputs_Runnable"
        }
        ]

        Arg:
        data_mapping_config : Configuration information for all data_mapping;
        task_mappings_info: Configuration information for all task_mapping.
        """

        port_event_id_and_task_id = []
        signals_and_signalgroups = data_mapping_config["signals_and_signalgroups"]
        for i in range(len(signals_and_signalgroups)):
            for key, value in task_mappings_info.items():
                for j in range(len(value["schedulable_entity_info_list"])):
                    if (
                        signals_and_signalgroups[i]["runnable"] == value["schedulable_entity_info_list"][j]["name"]
                        and "On_Data_Reception" == signals_and_signalgroups[i]["trigger_mode"]
                    ):
                        port_event_id_and_task_id_dict = {"port_name": "", "task_id": "", "event_id": ""}
                        port_event_id_and_task_id_dict["port_name"] = signals_and_signalgroups[i]["signal_name"]
                        port_event_id_and_task_id_dict["task_id"] = key
                        port_event_id_and_task_id_dict["event_id"] = value["schedulable_entity_info_list"][j][
                            "event_mask"
                        ]
                        port_event_id_and_task_id.append(port_event_id_and_task_id_dict)

        return port_event_id_and_task_id

    @classmethod
    def __pack_asw_auxiliary_data(cls, asw_autosar_dict, task_mappings, cfg_dict):
        """
        do NOT change the execution order
        """
        ar_asw = asw_autosar_dict.get("asw")
        ar_flat_extract = asw_autosar_dict.get("FlatExtract")
        if ar_asw is None:
            print("No found ASW arxml!")
            return False
        if ar_flat_extract is None:
            print("No found FlatExtract arxml!")
            return False
        cls.task_mappings = task_mappings
        cls.cfg_dict = cfg_dict

        cls.constraints = cls.__parse_all_data_constraints(ar_asw)
        cls.compu_methods = cls.__parse_all_compu_methods(ar_asw)
        cls.idts, cls.idts_dependency, cls.datatype_path_to_idt_mapping = cls.__parse_all_idts_and_dependency(ar_asw)
        cls.consts = cls.__get_all_constants(ar_asw)
        cls.datatype_mapping_sets, cls.adt_mappings = cls.__parse_datatype_mapping_sets(ar_asw)
        cls.mode_groups = cls.__parse_all_mode_dclr_groups(ar_asw)
        cls.sw_component_types = cls.__pack_all_sw_component_type(ar_asw)
        cls.sw_component_prototypes = cls.get_all_sw_component_prototypes(ar_asw)
        cls.asw_events = cls.__parse_asw_runnable_events_dict()
        cls.runnable_tasks, cls.runnable_events, cls.port_events = cls.__parse_runnables_task_and_event()
        cls.exclusive_areas = cls.__parse_runnables_exclusive_areas()
        cls.component_osapplications, cls.mapped_schedulable_entitys, cls.component_core_id = (
            cls.__pack_sw_component_type_osapplication()
        )
        cls.ecuc_partition_osa, cls.swc_osa_from_ep, cls.swc_core_id_from_ep, cls.swc_ecuc_partition = (
            cls.__pack_osa_info_from_ecuc_partition()
        )
        # DO NOT use these, use cls.p_connections and cls.r_connections instead
        # TODO: for M/S only, needs to fix
        cls.p_port_connection, cls.r_port_connection = cls.__pack_port_prototype_connection(ar_flat_extract)
        cls.p_connections, cls.r_connections = cls.__parse_assembly_connection(ar_flat_extract)
        (
            cls.port_data_element_access,
            cls.port_operation_access,
            cls.operation_access,
            cls.server_runnable_connections,
        ) = cls.__parse_dataelement_operation_modegroup_access()
        cls.__parse_run_operation_map()
        cls.port_prototypes = cls.__parse_all_port_prototypes()
        cls.pport_api_options = cls.__parse_all_pport_api_options()

        return bool(cls.all_osa)

    @classmethod
    def set_is_debug(cls, is_debug):
        cls.is_debug = is_debug

    @classmethod
    def __to_asw_codegen_dict(cls, asw_autosar_dict, data_mapping_info, task_mappings, com_cfg_dict, cfg_dict):
        rte_cfg = cfg_dict["rte"]
        os_cfg = rte_cfg.get("os_cfg", {})
        isolate_cfg = rte_cfg.get("isolate_cfg", {"module": {}, "iso_func": {}})

        cls.__init_global_vars_before_code_gen(rte_cfg, isolate_cfg, os_cfg)
        if not cls.__pack_asw_auxiliary_data(asw_autosar_dict, task_mappings, cfg_dict):
            return
        cls.__resolve_swc_data(cls.__rte_codegen_dict)

        # accessed runnable is unmapped (such as server runnable direct call)
        cls.__update_swc_due_to_unmapped_runnable(cls.__rte_codegen_dict)

        # sr
        cls.__find_sr_opposite_asw_ports(cls.__rte_codegen_dict)
        cls.__update_sr_m_to_n_status(cls.__rte_codegen_dict)
        cls.__update_sr_com_specs(cls.__rte_codegen_dict)
        cls.__update_sr_set_events(cls.__rte_codegen_dict)
        cls.__update_sr_func_safe_info(cls.__rte_codegen_dict, os_cfg)
        cls.__update_sr_lock_info(cls.__rte_codegen_dict)
        cls.__update_sr_queue_info(cls.__rte_codegen_dict)
        cls.__update_sr_port_init_value(cls.__rte_codegen_dict)
        cls.__update_sr_constr_and_compumethod_intra_ecu(cls.__rte_codegen_dict)
        cls.__update_sr_data_mapping(cls.__rte_codegen_dict, data_mapping_info, task_mappings, com_cfg_dict, cfg_dict)
        cls.__update_implicit_sr_copy_buffer_optimize_flag(cls.__rte_codegen_dict)
        cls.__build_sr_implicit_data_structure(cls.__rte_codegen_dict)

        # mode
        cls.__find_mode_opposite_asw_ports(cls.__rte_codegen_dict)
        cls.__update_mode_disabling_info(cls.__rte_codegen_dict, cls.__get_all_mode_disabling_info_dict(task_mappings))
        cls.__update_ms_memmap(cls.__rte_codegen_dict)
        # cs: TODO
        cls.__update_cs_memmap(cls.__rte_codegen_dict)
        # trigger: TODO

        cls.__update_cal_prm_port_info(cls.__rte_codegen_dict)

        # other update
        cls.__update_iso_function_header_file(cfg_dict)

        pass

    @classmethod
    def __update_ms_memmap(cls, asw_dict):
        # update the client queue memmap from server queue memmap
        for _, swc_info in asw_dict.items():
            for _, pport_info in swc_info["pports"].items():
                if pport_info["type"] != "ModeSwitch":
                    continue
                if not pport_info["conn_asw_ports"]:
                    continue
                memmap = cls.__update_ms_port_memmap(pport_info)
                pport_info.update({"memmap": memmap})

    @classmethod
    def __update_cs_memmap(cls, asw_dict):
        # update the client queue memmap from server queue memmap
        for _, swc_info in asw_dict.items():
            for _, rport_info in swc_info["rports"].items():
                if "Client" not in rport_info["type"]:
                    continue
                if not rport_info.get("queue", {}):
                    continue
                for swc_port, queue_info in rport_info["queue"].items():
                    pport = rport_info["connected_ports"]["ports"][0]
                    swc_name, port_name = pport["component"], pport["name"]
                    memmap_enq = asw_dict[swc_name]["pports"][port_name]["queue"][swc_port]["memmap_enq"]
                    memmap_deq = asw_dict[swc_name]["pports"][port_name]["queue"][swc_port]["memmap_deq"]
                    queue_info.update({"memmap_enq": memmap_enq})
                    queue_info.update({"memmap_deq": memmap_deq})

            for _, pport_info in swc_info["pports"].items():
                if "Server" not in pport_info["type"]:
                    continue
                if not pport_info["connected_ports"] or not pport_info["connected_ports"].get("ports", []):
                    continue
                for rport in pport_info["connected_ports"]["ports"]:
                    swc_name, port_name = rport["component"], rport["name"]
                    memmap = asw_dict[swc_name]["rports"][port_name]["memmap"]
                    rport.update({"memmap": memmap})

    @classmethod
    def __update_iso_function_header_file(cls, cfg_dict):
        cfg_dict["rte"]["iso_call_func_include_header_file"] = {}
        for osa, include_files in cls.iso_call_func_include_header_file.items():
            cfg_dict["rte"]["iso_call_func_include_header_file"][osa] = sorted(include_files)

    @classmethod
    def __resolve_swc_data(cls, asw_codegen_dict):
        if cls.sw_component_types is None:
            return
        cls.__pre_parse_swc_info()
        for ar_component_type in cls.sw_component_types:
            asw_codegen_dict[utils.get_short_name(ar_component_type)] = cls.parse_sw_component_type(ar_component_type)

    @classmethod
    def __build_sr_implicit_data_structure(cls, asw_dict):
        for _, swc_info in asw_dict.items():
            for _, pport in swc_info["pports"].items():
                cls.__build_sr_implicit_data_structure_each_group(pport)
            for _, rport in swc_info["rports"].items():
                cls.__build_sr_implicit_data_structure_each_group(rport)

    @classmethod
    def __build_sr_implicit_data_structure_each_group(cls, port):
        if "Implicit" not in port["type"]:
            return
        component = port["component"]
        task_index = 0
        visited_run_data_map = dict()
        while task_index < len(port["task"]):
            task_name = port["task"][task_index]
            runnable_name = port["runnable"][task_index]
            task_index += 1

            if port["imp_sr_copy_buf_opt"] is True:
                continue

            task_idt_name, task_sub_idt_name = cls.__build_sr_imp_data_task(task_name)
            swc_run_idt_name = cls.__build_sr_imp_data_swc_run(
                component, runnable_name, task_idt_name, task_sub_idt_name
            )
            cls.__build_sr_imp_data_de(port, visited_run_data_map, task_idt_name, task_sub_idt_name, swc_run_idt_name)

    @classmethod
    def __build_sr_imp_data_de(cls, port, visited_run_data_map, task_idt_name, task_sub_idt_name, swc_run_idt_name):
        data_ele_cfg_idt = port["arg"]["datatype"]
        data_ele_idt_name = data_ele_cfg_idt["name"]
        data_ele_idt_category = data_ele_cfg_idt["category"]
        data_ele_idt_align = data_ele_cfg_idt["typesize_byte_for_struct_align"]
        # data_ele_cfg_idt_typesize_align = data_ele_cfg_idt["typesize_byte_for_struct_align"]
        # data_ele_idt_name = data_ele_cfg_idt_name
        data_ele_member_name = f"Rte_{port['port_prototype']}_{port['data_element']}"
        data_ele_member = {
            "name": data_ele_member_name,
            "is_user_typed": False,
            "is_array": False,
            "datatype": data_ele_idt_name,
            "category": data_ele_idt_category,
            "typesize_byte_for_struct_align": data_ele_idt_align,
            "mem_dep": [],
            "mem_nature_order": 0,
        }

        cls.idts_dependency[task_idt_name].append(data_ele_idt_name)
        cls.idts_dependency[task_sub_idt_name].append(data_ele_idt_name)
        cls.idts_dependency[swc_run_idt_name].append(data_ele_idt_name)

        if swc_run_idt_name not in visited_run_data_map:
            visited_run_data_map[swc_run_idt_name] = set()
        if data_ele_member_name not in visited_run_data_map[swc_run_idt_name]:
            visited_run_data_map[swc_run_idt_name].add(data_ele_member_name)
            cls.idts[swc_run_idt_name]["members"].append(data_ele_member)
            cls.idts[swc_run_idt_name]["members"].sort(key=lambda x: x["typesize_byte_for_struct_align"], reverse=True)
            cls.idts[swc_run_idt_name]["mem_in_typesize_order_for_align"][4].append(data_ele_member)
            mem_indices = cls.idts[swc_run_idt_name]["mem_index_in_order"]
            mem_indices.append(mem_indices[-1] + 1 if mem_indices else 0)

    @classmethod
    def __build_sr_imp_data_swc_run(cls, component, runnable_name, task_idt_name, task_sub_idt_name):
        swc_run_idt_name = f"Rte_tsRB_{component}_{runnable_name}"
        if swc_run_idt_name not in cls.idts:
            swc_run_idt = {
                "name": swc_run_idt_name,
                "category": "STRUCTURE",
                "members": [],
                "typesize_byte_for_struct_align": 4,
                "mem_in_typesize_order_for_align": {8: [], 4: [], 2: [], 1: []},
                "mem_index_in_order": [],
                "native_category": "STRUCTURE",
                "constraint": {},
                "type_emitter": "RTE",
            }
            swc_run_member = {
                "name": f"Rte_{component}_{runnable_name}",
                "is_user_typed": False,
                "is_array": False,
                "datatype": swc_run_idt_name,
                "category": "STRUCTURE",
                "typesize_byte_for_struct_align": 4,
                "mem_dep": [],
                "mem_nature_order": 0,
            }
            cls.idts[swc_run_idt_name] = swc_run_idt
            cls.idts_dependency[swc_run_idt_name] = []
            cls.idts_dependency[task_idt_name].append(swc_run_idt_name)
            cls.idts_dependency[task_sub_idt_name].append(swc_run_idt_name)

            cls.idts[task_sub_idt_name]["members"].append(swc_run_member)
            cls.idts[task_sub_idt_name]["mem_in_typesize_order_for_align"][4].append(swc_run_member)
            mem_indices = cls.idts[task_sub_idt_name]["mem_index_in_order"]
            mem_indices.append(mem_indices[-1] + 1 if mem_indices else 0)
        return swc_run_idt_name

    @classmethod
    def __build_sr_imp_data_task(cls, task_name):
        task_idt_name = f"Rte_ts_{task_name}"
        task_sub_idt_name = f"Rte_tuRB_{task_name}"
        if task_idt_name not in cls.idts:
            task_sub_idt = {
                "name": task_sub_idt_name,
                "category": "STRUCTURE",
                "members": [],
                "typesize_byte_for_struct_align": 4,
                "mem_in_typesize_order_for_align": {8: [], 4: [], 2: [], 1: []},
                "mem_index_in_order": [],
                "native_category": "STRUCTURE",
                "constraint": {},
                "type_emitter": "RTE",
            }
            task_sub_member = {
                "name": "Rte_RB",
                "is_user_typed": False,
                "is_array": False,
                "datatype": task_sub_idt_name,
                "category": "STRUCTURE",
                "typesize_byte_for_struct_align": 4,
                "mem_dep": [],
                "mem_nature_order": 0,
            }
            cls.idts[task_sub_idt_name] = task_sub_idt
            cls.idts_dependency[task_sub_idt_name] = []
            task_idt = {
                "name": task_idt_name,
                "category": "STRUCTURE",
                "members": [task_sub_member],
                "typesize_byte_for_struct_align": 4,
                "mem_in_typesize_order_for_align": {8: [], 4: [task_sub_member], 2: [], 1: []},
                "mem_index_in_order": [0],
                "native_category": "STRUCTURE",
                "constraint": {},
                "type_emitter": "RTE",
            }
            cls.idts[task_idt_name] = task_idt
            cls.idts_dependency[task_idt_name] = [task_sub_idt_name]
        return task_idt_name, task_sub_idt_name

    @classmethod
    def __get_all_mode_disabling_info_dict(cls, task_mappings):
        """
        get all mode disabling info as a dict
        """
        mode_disabling_info = {}
        for _, mapping in task_mappings.items():
            for entity in mapping["schedulable_entity_info_list"]:
                if "mode_disabling_info" not in entity:
                    # only for dictionary input of test cases, not for real arxmls
                    continue
                for info in entity["mode_disabling_info"]:
                    key = info["key"]
                    if key not in mode_disabling_info:
                        mode_disabling_info[key] = []
                    mode_disabling_info[key].append(info)
        return mode_disabling_info

    @classmethod
    def to_idt_codegen_dict(cls, ar_asw, is_re_parsing=True):
        cls.constraints = cls.__parse_all_data_constraints(ar_asw)
        if is_re_parsing:
            cls.idts, cls.idts_dependency, _ = cls.__parse_all_idts_and_dependency(ar_asw)
        sorted_idts = {}
        sorted_idt_names = topological_sort(cls.idts_dependency)
        for idt_name in sorted_idt_names:
            if not idt_name:
                continue
            if idt_name in cls.NATIVE_DATATYPES:
                continue  # exclude basetype for codegen
            sorted_idts.update({idt_name: cls.idts[idt_name]})
        return sorted_idts

    @classmethod
    def get_idt_for_validation(cls, ar_asw):
        idts, _, _ = cls.__parse_all_idts_and_dependency(ar_asw)
        return idts

    @classmethod
    def parse_datatype_mapping_sets_for_validation(cls, asw_class):
        return cls.__parse_datatype_mapping_sets(asw_class)

    @classmethod
    def __update_sr_func_safe_info(cls, asw_dict, os_cfg):
        """
        all memory (including memmap) related logic should be updated here to meet functional safety requirements
        """
        asil_info = {}
        if os_cfg and "asil" in os_cfg:
            asil_info = os_cfg["asil"]
        visited_ports = set()
        for _, swc_info in asw_dict.items():
            for _, pport in swc_info["pports"].items():
                cls.__update_sr_func_safe_info_each_port_group(pport, visited_ports, asil_info, True)
            for _, rport in swc_info["rports"].items():
                cls.__update_sr_func_safe_info_each_port_group(rport, visited_ports, asil_info, False)

    @classmethod
    def __update_sr_queue_info_each_port(cls, asw_port):
        all_non_q_participant_ports = asw_port["sr_port_group"]

        if asw_port["m_to_n"] == "1n":
            p_port = {}
            for port in all_non_q_participant_ports:
                if port["is_p"]:
                    p_port = port
                    p_port["queue"] = {}
            for port in all_non_q_participant_ports:
                if port["is_p"]:
                    continue
                q_size = cls.port_prototypes[port["port_path"]][port["data_element_path"]]["queue_size"]
                if not q_size:
                    continue
                queue = {port["swc_port_var"]: {"size": q_size, "ioc_type": port["q_ioc_type"]}}
                port["queue"] = queue
                p_port["queue"].update(queue)
        else:
            q_size = 0
            r_port = {}
            for port in all_non_q_participant_ports:
                if not port["is_p"]:
                    q_size = cls.port_prototypes[port["port_path"]][port["data_element_path"]]["queue_size"]
                    r_port = port
                    break
            if not q_size:
                return
            queue = {r_port["swc_port_var"]: {"size": q_size, "ioc_type": r_port["q_ioc_type"]}}
            for port in all_non_q_participant_ports:
                port["queue"] = queue

    @classmethod
    def __update_sr_queue_info(cls, asw_dict):
        visited_ports = set()
        for _, swc_info in asw_dict.items():
            for _, pport in swc_info["pports"].items():
                if ("port_interface_type" not in pport) or pport["port_interface_type"] != "sr":
                    continue
                if not pport["is_queued"]:
                    continue
                if pport["has_prport"]:
                    continue
                if pport["m_to_n"] in {"mn", "0"}:
                    continue
                if pport["port_full_key"] in visited_ports:
                    continue
                visited_ports.update(port["port_full_key"] for port in pport["sr_port_group"])
                cls.__update_sr_queue_ioc_type(pport)
                cls.__update_sr_queue_lock(pport)
                cls.__update_sr_queue_info_each_port(pport)

            for _, rport in swc_info["rports"].items():
                if ("port_interface_type" not in rport) or rport["port_interface_type"] != "sr":
                    continue
                if not rport["is_queued"]:
                    continue
                if rport["has_prport"]:
                    continue
                if rport["m_to_n"] in {"mn", "0"}:
                    continue
                if rport["port_full_key"] in visited_ports:
                    continue
                visited_ports.update(port["port_full_key"] for port in rport["sr_port_group"])
                cls.__update_sr_queue_ioc_type(rport)
                cls.__update_sr_queue_lock(rport)
                cls.__update_sr_queue_info_each_port(rport)

    @classmethod
    def __update_sr_set_events_each_port(cls, asw_port, visited_ports):
        if ("port_interface_type" not in asw_port) or asw_port["port_interface_type"] != "sr":
            return
        if asw_port["port_full_key"] in visited_ports:
            return
        visited_ports.add(asw_port["port_full_key"])

        set_events = []
        for r_port in asw_port["conn_asw_ports"]:
            if r_port["is_queued"] and r_port["timeout"] > 0:
                for task in set(r_port["task"]):
                    set_events.append(
                        {
                            "task_id": f"Os_Task_{task}_ID",
                            "event_mask": f"Rte_Ev_WaitPoint_{task}",
                        }
                    )
            else:
                for runnable_symbol in set(r_port["symbol"]):
                    if runnable_symbol not in cls.runnable_events:
                        continue
                    event = cls.runnable_events.get(runnable_symbol, {}).get(r_port["port_var"])
                    if event:
                        set_events.append(
                            {"task_id": "Os_Task_" + event["task_name"] + "_ID", "event_mask": event["event_mask"]}
                        )

        # Add Pport set event
        for event in cls.port_events.get(asw_port["port_var"], {}).values():
            if event and event["event_type"] in {
                "DataSendCompletedEvent",
                "DataWriteCompletedEvent",
                "InternalTriggerOccurredEvent",
                "ExternalTriggerOccurredEvent",
            }:
                set_events.append(
                    {"task_id": "Os_Task_" + event["task_name"] + "_ID", "event_mask": event["event_mask"]}
                )

        asw_port["set_events"] = set_events

    @classmethod
    def __update_sr_set_events(cls, asw_dict):
        visited_ports = set()
        for _, swc_info in asw_dict.items():
            for _, pport in swc_info["pports"].items():
                cls.__update_sr_set_events_each_port(pport, visited_ports)

    @classmethod
    def __update_sr_lock_info(cls, asw_dict):
        visited_ports = set()
        for _, swc_info in asw_dict.items():
            for _, pport in swc_info["pports"].items():
                cls.__parse_sr_lock_nonqueue(pport, visited_ports)
            for _, rport in swc_info["rports"].items():
                cls.__parse_sr_lock_nonqueue(rport, visited_ports)

    @classmethod
    def __update_implicit_sr_copy_buffer_optimize_flag(cls, asw_dict):
        for _, swc_info in asw_dict.items():
            for _, port in swc_info["pports"].items():
                cls.__implicit_sr_copy_buffer_opt(port)
                cls.__update_implicit_sr_buf_intra_osa_opt_flag(port)
            for _, port in swc_info["rports"].items():
                cls.__implicit_sr_copy_buffer_opt(port)
                cls.__update_implicit_sr_buf_intra_osa_opt_flag(port)

    @classmethod
    def __implicit_sr_copy_buffer_opt(cls, port):
        port["imp_sr_copy_buf_opt"] = (
            port["type"] in ["Implicit Sender", "Implicit Receiver"]
            and cls.__sr_port_group_in_same_task(port)
            and port["lock"] == "NONE"
            and port["m_to_n"] not in {"0", "mn"}
            and (port["m_to_n"] != "n1" or port.get("single_rec_buff_for_n1", False) is True)
            and port["signal_category"] not in ["Signal", "SignalGroup"]
            and len(port.get("set_events", [])) == 0
        )

    @classmethod
    def __sr_port_group_in_same_task(cls, port):
        tasks = []
        for group_port in port.get("sr_port_group", []):
            tasks += group_port.get("task", [])
        return len(set(tasks)) == 1

    @classmethod
    def __update_implicit_sr_buf_intra_osa_opt_flag(cls, curr_port):
        if not curr_port["imp_sr_copy_buf_opt"]:
            curr_port["imp_sr_buf_opt_intra_osa"] = False
        else:
            curr_port_osa = curr_port["osapplication"]
            all_non_q_participant_ports = curr_port["sr_port_group"]
            curr_port["imp_sr_buf_opt_intra_osa"] = True
            for port in all_non_q_participant_ports:
                if port == curr_port:
                    continue
                elif port["osapplication"] != curr_port_osa:
                    curr_port["imp_sr_buf_opt_intra_osa"] = False
                    break

    @classmethod
    def __check_if_has_prport_in_connected_port_group(cls, port_group):
        has_prport = False
        for port in port_group:
            if port["is_prport"]:
                has_prport = True
                break
        return has_prport

    @classmethod
    def __get_data_mapping_sr_rport_by_required_com_specs(cls, cfg_dict):
        import importlib.util

        if importlib.util.find_spec("Bsw") is None:
            com_signal_default_values = {None, "None", "", " ", "0"}
        else:
            from Bsw.Com.plug_in.update_ecuc.com_ecuc_manager import SIGNAL_NOTIFICATION_DEFAULT_VALUE_LIST

            com_signal_default_values = set(SIGNAL_NOTIFICATION_DEFAULT_VALUE_LIST)

        """过滤required_com_specs非空的DataMapping rport"""
        sr_rport_required_com_specs_dict = {}
        for component_name, component in cfg_dict.get("rte", {}).get("asw_config", {}).items():
            osapplication = component.get("osapplication", None)
            if osapplication is None:
                continue
            if osapplication not in sr_rport_required_com_specs_dict.keys():
                sr_rport_required_com_specs_dict[osapplication] = {}
            if component_name not in sr_rport_required_com_specs_dict[osapplication].keys():
                sr_rport_required_com_specs_dict[osapplication][component_name] = {
                    "enable_update": [],
                    "handle_never_received": [],
                    "alive_timeout": [],
                }
            component_required_com_specs = sr_rport_required_com_specs_dict[osapplication][component_name]
            for port_name, rport in component.get("rports", {}).items():
                if rport.get("signal_category", None) != "Signal" or rport.get("type", None) != "Explicit Receiver":
                    continue
                required_com_specs = rport.get("required_com_specs", None)
                if required_com_specs is None:
                    continue
                if required_com_specs.get("enable_update", "false") == "true":
                    component_required_com_specs["enable_update"].append(rport)
                if required_com_specs.get("handle_never_received", "false") == "true":
                    component_required_com_specs["handle_never_received"].append(rport)
                if required_com_specs.get("alive_timeout", "0") not in com_signal_default_values:
                    component_required_com_specs["alive_timeout"].append(rport)
        return sr_rport_required_com_specs_dict

    @classmethod
    def __sorted_sr_dm_glob_vars(cls):
        def __sorted_sub_vars(root):
            if not root:
                return root
            for osa, info in root.items():
                root[osa] = dict(sorted(info.items()))
                for sub_key, sub_info in info.items():
                    info[sub_key] = dict(sorted(sub_info.items()))
            return dict(sorted(root.items()))

        cls.sr_dm_glob_vars["individual"]["buff"] = __sorted_sub_vars(cls.sr_dm_glob_vars["individual"]["buff"])
        cls.sr_dm_glob_vars["individual"]["buff_last"] = __sorted_sub_vars(
            cls.sr_dm_glob_vars["individual"]["buff_last"]
        )
        cls.sr_dm_glob_vars["individual"]["status"] = __sorted_sub_vars(cls.sr_dm_glob_vars["individual"]["status"])

        cls.sr_dm_glob_vars["complex"]["flag_is_proxy_sending"] = __sorted_sub_vars(
            cls.sr_dm_glob_vars["complex"]["flag_is_proxy_sending"]
        )
        cls.sr_dm_glob_vars["complex"]["flag_is_updated_tx"] = __sorted_sub_vars(
            cls.sr_dm_glob_vars["complex"]["flag_is_updated_tx"]
        )
        cls.sr_dm_glob_vars["complex"]["flag_is_updated_rx"] = __sorted_sub_vars(
            cls.sr_dm_glob_vars["complex"]["flag_is_updated_rx"]
        )
        cls.sr_dm_glob_vars["complex"]["flag_is_received"] = __sorted_sub_vars(
            cls.sr_dm_glob_vars["complex"]["flag_is_received"]
        )
        cls.sr_dm_glob_vars["complex"]["flag_is_timeout"] = __sorted_sub_vars(
            cls.sr_dm_glob_vars["complex"]["flag_is_timeout"]
        )

        return cls.sr_dm_glob_vars

    @classmethod
    def __update_sr_data_mapping_update_codegen_data(cls, dm_cfg, cfg_dict):
        cls.__last_data_mapping_info = {
            "signals_and_signalgroups": dm_cfg["signals_and_signalgroups"],
            "data_received_event_list": dm_cfg["data_received_event_list"],
            "port_event_id_and_task_id": dm_cfg["port_event_id_and_task_id"],
            "signal_dict": dm_cfg["signal_dict"],
            "sr_required_com_specs_dict": dm_cfg["sr_required_com_specs_dict"],
            "glob_vars": dm_cfg["glob_vars"],
        }
        cfg_dict["rte"]["data_mapping_config"] = cls.__last_data_mapping_info

    @classmethod
    def __update_sr_data_mapping_extra_info(cls, signal_dict):
        # update N:M info for SR data mapping
        port_id_set = set()
        signal_id_set = set()
        osa_set = set()
        core_id_set = set()
        visited_signal = set()
        invalid_signal = set()
        for signal_name, _ in signal_dict["tx"].items():
            if signal_name in visited_signal:
                continue
            port_id_set.clear()
            signal_id_set.clear()
            osa_set.clear()
            core_id_set.clear()
            # index 0: port - index 1: signal
            port_signal_group_list = [[], []]
            cls.__find_sr_data_mapping_each_group(
                signal_dict["tx"], signal_name, port_id_set, signal_id_set, port_signal_group_list, osa_set, core_id_set
            )
            visited_signal.update([sig["name"] for sig in port_signal_group_list[1]])
            if not cls.__update_sr_data_mapping_check_valid(
                port_signal_group_list, invalid_signal, osa_set, core_id_set
            ):
                continue

            cls.__update_sr_data_mapping_port_signal_group(port_signal_group_list)
            cls.__update_sr_data_mapping_core_info_each_group(port_signal_group_list, osa_set, core_id_set)
            cls.__update_sr_data_mapping_m_to_n_each_group(port_signal_group_list, True)
            cls.__update_sr_data_mapping_flag_each_group(port_signal_group_list, True)
            cls.__update_sr_data_mapping_datatype_each_group(port_signal_group_list)
            cls.__update_sr_data_mapping_lock_buff_info_each_group(port_signal_group_list, True)
            cls.__update_sr_data_mapping_tx_proxy(port_signal_group_list, signal_dict["tx_proxy"])
            cls.__update_sr_constr_and_compumethod_inter_ecu(port_signal_group_list, True)
        signal_dict["tx_proxy"] = dict(sorted(signal_dict["tx_proxy"].items()))
        for sig in invalid_signal:
            signal_dict["tx"].pop(sig, None)

        visited_signal.clear()
        invalid_signal.clear()
        for signal_name, _ in signal_dict["rx"].items():
            if signal_name in visited_signal:
                continue
            port_id_set.clear()
            signal_id_set.clear()
            osa_set.clear()
            core_id_set.clear()
            # index 0: port - index 1: signal
            port_signal_group_list = [[], []]
            cls.__find_sr_data_mapping_each_group(
                signal_dict["rx"], signal_name, port_id_set, signal_id_set, port_signal_group_list, osa_set, core_id_set
            )
            visited_signal.update([sig["name"] for sig in port_signal_group_list[1]])
            if not cls.__update_sr_data_mapping_check_valid(
                port_signal_group_list, invalid_signal, osa_set, core_id_set
            ):
                continue

            cls.__update_sr_data_mapping_port_signal_group(port_signal_group_list)
            cls.__update_sr_data_mapping_core_info_each_group(port_signal_group_list, osa_set, core_id_set)
            cls.__update_sr_data_mapping_m_to_n_each_group(port_signal_group_list, False)
            cls.__update_sr_data_mapping_rx_com_spec_each_group(port_signal_group_list)
            cls.__update_sr_data_mapping_flag_each_group(port_signal_group_list, False)
            cls.__update_sr_data_mapping_datatype_each_group(port_signal_group_list)
            cls.__update_sr_data_mapping_lock_buff_info_each_group(port_signal_group_list, False)
            cls.__update_sr_constr_and_compumethod_inter_ecu(port_signal_group_list, False)
        for sig in invalid_signal:
            signal_dict["rx"].pop(sig, None)

    @classmethod
    def __update_sr_data_mapping_check_valid(cls, port_signal_group_list, invalid_signal, osa_set, core_id_set):
        port_to_remove = []
        for port in port_signal_group_list[0]:
            if not port["osapplication"] or port["core_id"] is None:
                logger.error(f"Rte port config error: {port['swc_port_var']}!")
                port_to_remove.append(port)
        for port in port_to_remove:
            port_signal_group_list[0].remove(port)

        sig_to_remove = []
        for sig in port_signal_group_list[1]:
            if not sig["osa"] or sig["core_id"] is None:
                sig["data_mapping_m_to_n"] = "0"
                sig_to_remove.append(sig)
                invalid_signal.add(sig["name"])
                logger.error(f"Rte signal config error: {sig['name']}!")
        for sig in sig_to_remove:
            port_signal_group_list[1].remove(sig)

        if (not port_signal_group_list[0]) and (not port_signal_group_list[1]):
            return False
        elif (not port_signal_group_list[0]) or (not port_signal_group_list[1]):
            if port_signal_group_list[0]:
                msg = f"{[port['swc_port_var'] for port in port_signal_group_list[0]]}"
            else:
                msg = f"{[sig['name'] for sig in port_signal_group_list[1]]}"
            for sig in port_signal_group_list[1]:
                sig["data_mapping_m_to_n"] = "0"
                invalid_signal.add(sig["name"])
            logger.error(f"Rte datamapping config error: {msg}!")
            return False

        osa_set.discard(None)
        core_id_set.discard(None)

        return True

    @classmethod
    def __get_proxy_name(cls, osa, period):
        postfix = f"_{osa}_{period}ms"
        return postfix, f"Rte_ComSendSignalProxyPeriodic{postfix}"

    @classmethod
    def __update_sr_data_mapping_tx_proxy(cls, port_signal_group_list, tx_proxy):
        fst_sig = port_signal_group_list[1][0]
        if not (fst_sig["data_mapping_has_inter_core"] or fst_sig["data_mapping_has_inter_osa_same_core"]):
            for signal in port_signal_group_list[1]:
                signal["tx_proxy"] = None
        else:
            for signal in port_signal_group_list[1]:
                period = signal["signal_com_func_period"]
                proxy_name_postfix, proxy_name = cls.__get_proxy_name(signal["osa"], period)
                if proxy_name not in tx_proxy:
                    tx_proxy[proxy_name] = {
                        "period": period,
                        "name": proxy_name,
                        "osa": signal["osa"],
                        "postfix": proxy_name_postfix,
                        "signal": {},
                    }
                tx_proxy[proxy_name]["signal"][signal["name"]] = signal
                signal["tx_proxy"] = proxy_name

    @classmethod
    def __update_sr_data_mapping_port_signal_group(cls, port_signal_group_list):
        for port in port_signal_group_list[0]:
            port["sr_port_signal_group"] = port_signal_group_list
        for sig in port_signal_group_list[1]:
            sig["sr_port_signal_group"] = port_signal_group_list

    @classmethod
    def __update_sr_data_mapping_core_info_each_group(cls, port_signal_group_list, osa_set, core_id_set):
        has_inter_core = False
        has_inter_osa_same_core = False
        if len(core_id_set) > 1:
            has_inter_core = True
        elif len(osa_set) > 1:
            has_inter_osa_same_core = True

        for port in port_signal_group_list[0]:
            port["data_mapping_has_inter_core"] = has_inter_core
            port["data_mapping_has_inter_osa_same_core"] = has_inter_osa_same_core
        for signal in port_signal_group_list[1]:
            signal["data_mapping_has_inter_core"] = has_inter_core
            signal["data_mapping_has_inter_osa_same_core"] = has_inter_osa_same_core

    @classmethod
    def __add_to_sr_dm_glob_vars_individual(cls, var_category, var_info):
        root = cls.sr_dm_glob_vars["individual"][var_category]
        osa = var_info["osa"]
        if osa not in root:
            root[osa] = {}
        if var_info["memmap_category"] not in root[osa]:
            root[osa][var_info["memmap_category"]] = {}
        root[osa][var_info["memmap_category"]][var_info["name"]] = var_info

    @classmethod
    def __add_to_sr_dm_glob_vars_complex(cls, var_category, var_info):
        root = cls.sr_dm_glob_vars["complex"][var_category]
        osa = var_info["osa"]
        if osa not in root:
            root[osa] = {}
        parent_struct_name = var_info["parent_struct_name"]
        if parent_struct_name not in root[osa]:
            root[osa][parent_struct_name] = {}
        root[osa][parent_struct_name][var_info["name"]] = var_info

    @classmethod
    def __update_sr_data_mapping_lock_buff_info_each_group(cls, port_signal_group_list, is_tx):
        """
        TODO: func safety not considered, one shared buffer is used
        """
        for port in port_signal_group_list[0]:
            port["data_mapping_lock"] = "NONE"
            port["data_mapping_lock_id"] = None
            port["data_mapping_buff"] = {}
            port["is_com_tx_opt"] = False
            port["data_mapping_buff_last"] = {}
            port["data_mapping_flag_is_proxy_sending"] = {}
            port["data_mapping_status"] = None
        for signal in port_signal_group_list[1]:
            signal["data_mapping_lock"] = "NONE"
            signal["data_mapping_lock_id"] = None
            signal["data_mapping_buff"] = {}
            signal["is_com_tx_opt"] = False
            signal["data_mapping_buff_last"] = {}
            signal["data_mapping_flag_is_proxy_sending"] = {}
            signal["data_mapping_status"] = None
            signal["is_inter_core_extra_copy_skipped"] = False

        has_inter_core = port_signal_group_list[0][0]["data_mapping_has_inter_core"]
        has_inter_osa_same_core = port_signal_group_list[0][0]["data_mapping_has_inter_osa_same_core"]
        if has_inter_core:
            cls.__update_sr_data_mapping_buff_info_each_group_has_inter_osa(port_signal_group_list, is_tx)
            cls.__update_sr_data_mapping_lock_info_each_group_has_inter_core(port_signal_group_list)
            cls.__update_sr_data_mapping_is_inter_core_extra_copy_skipped(port_signal_group_list, is_tx)
        elif has_inter_osa_same_core:
            cls.__update_sr_data_mapping_buff_info_each_group_has_inter_osa(port_signal_group_list, is_tx)
            cls.__update_sr_data_mapping_lock_info_each_group_has_inter_osa_same_core(port_signal_group_list)
        else:
            cls.__update_sr_data_mapping_buff_info_each_group_intra_osa(port_signal_group_list, is_tx)
            cls.__update_sr_data_mapping_lock_info_each_group_intra_osa()

    @classmethod
    def __update_sr_data_mapping_is_inter_core_extra_copy_skipped(cls, port_signal_group_list, is_tx):
        """
        if more than one signal exist in the same data inter core exchange, (1:n / m:n)
        only the first extra copy is needed, the rests are skipped
        """
        if not is_tx:
            return
        if len(port_signal_group_list[1]) == 1:
            return
        visited_sig_osa = set()
        for signal in port_signal_group_list[1]:
            if signal["osa"] in visited_sig_osa:
                signal["is_inter_core_extra_copy_skipped"] = True
            else:
                visited_sig_osa.add(signal["osa"])

    @classmethod
    def __update_sr_data_mapping_buff_info_each_group_intra_osa(cls, port_signal_group_list, is_tx):
        first_signal = port_signal_group_list[1][0]
        datatype = first_signal["datatype"]
        init_value = first_signal["init_value"]
        m_to_n = first_signal["data_mapping_m_to_n"]
        if is_tx:
            cls.__update_sr_data_mapping_buff_info_each_group_intra_osa_tx(
                port_signal_group_list, first_signal, datatype, init_value
            )
        else:
            cls.__update_sr_data_mapping_buff_info_each_group_intra_osa_rx(
                port_signal_group_list, first_signal, datatype, init_value, m_to_n
            )

    @classmethod
    def __update_sr_data_mapping_buff_info_each_group_intra_osa_rx(
        cls, port_signal_group_list, first_signal, datatype, init_value, m_to_n
    ):
        if m_to_n == "11":
            port = port_signal_group_list[0][0]
            if cls.is_datamapping_opt_rx_1_1:
                signals_detail = port.get("data_mapping_details", [])
                if len(signals_detail) != 1:
                    return
                runnable_list = port.get("runnable", [])
                port_runnable_period_list = []
                for runnable in runnable_list:
                    port_runnable_period = (
                        cls.__rte_codegen_dict[port["swc_prototype"]]
                        .get("runnables", {})
                        .get(runnable, {})
                        .get("period", 0)
                    )
                    if port_runnable_period is None or port_runnable_period == 0:
                        continue
                    port_runnable_period_list.append(port_runnable_period)
                if len(port_runnable_period_list) > 0:
                    port_runnable_period = min(port_runnable_period_list)
                else:
                    port_runnable_period = 0
                signal_runnable_period = float(signals_detail[0].get("pdu_period", "0")) * 1000  # Convert to ms
                if (
                    signal_runnable_period > 0
                    and port_runnable_period > 0
                    and signal_runnable_period > port_runnable_period
                ):
                    buff = {
                        "name": f"Rte_{first_signal['name']}_{first_signal['direction']}",
                        "datatype": datatype,
                        "init_value": init_value,
                        "osa": first_signal["osa"],
                        "core_id": first_signal["core_id"],
                        "memmap_category": MemmapCategory.OSA_PRIVATE,
                        "init_category": None,
                    }
                    port["data_mapping_buff"] = buff
                    first_signal["data_mapping_buff"] = buff
                    cls.__add_to_sr_dm_glob_vars_individual("buff", buff)

                    if not port["is_implicit"]:
                        stat = {
                            "name": f"Rte_Status_{buff['name']}",
                            "osa": first_signal["osa"],
                            "core_id": first_signal["core_id"],
                            "memmap_category": MemmapCategory.OSA_PRIVATE,
                            "init_category": VariableInitCategory.ZERO_INIT,
                        }
                        cls.__add_to_sr_dm_glob_vars_individual("status", stat)
                        port["data_mapping_status"] = stat
                        first_signal["data_mapping_status"] = stat
        elif m_to_n == "1n" and (not cls.is_datamapping_opt_rx_1_n):
            # 1 signal -> n ports
            pass
        elif m_to_n == "n1":
            # n signals -> 1 port
            first_port = port_signal_group_list[0][0]
            buff = {
                "name": f"Rte_{first_port['swc_port_var']}_{first_signal['direction']}",
                "datatype": datatype,
                "init_value": init_value,
                "memmap_category": MemmapCategory.OSA_PRIVATE,
                "osa": first_port["osapplication"],
                "core_id": first_port["core_id"],
                "init_category": None,
            }
            cls.__add_to_sr_dm_glob_vars_individual("buff", buff)
            first_port["data_mapping_buff"] = buff
            for signal in port_signal_group_list[1]:
                signal["data_mapping_buff"] = buff

            if not first_port["is_implicit"]:
                stat = {
                    "name": f"Rte_Status_{buff['name']}",
                    "memmap_category": MemmapCategory.OSA_PRIVATE,
                    "osa": first_port["osapplication"],
                    "core_id": first_port["core_id"],
                    "init_category": VariableInitCategory.ZERO_INIT,
                }
                cls.__add_to_sr_dm_glob_vars_individual("status", stat)
                first_port["data_mapping_status"] = stat
                for signal in port_signal_group_list[1]:
                    signal["data_mapping_status"] = stat
        else:
            buff = {
                "name": f"Rte_{first_signal['name']}_{first_signal['direction']}",
                "datatype": datatype,
                "init_value": init_value,
                "memmap_category": MemmapCategory.OSA_PRIVATE,
                "osa": first_signal["osa"],
                "core_id": first_signal["core_id"],
                "init_category": None,
            }
            cls.__add_to_sr_dm_glob_vars_individual("buff", buff)
            first_signal["data_mapping_buff"] = buff
            if_need_stat = False
            stat = {
                "name": f"Rte_Status_{buff['name']}",
                "memmap_category": MemmapCategory.OSA_PRIVATE,
                "osa": first_signal["osa"],
                "core_id": first_signal["core_id"],
                "init_category": VariableInitCategory.ZERO_INIT,
            }
            for port in port_signal_group_list[0]:
                port["data_mapping_buff"] = buff
                if not port["is_implicit"]:
                    port["data_mapping_status"] = stat
                    if_need_stat = True
            if len(port_signal_group_list[1]) > 1:
                for signal in port_signal_group_list[1]:
                    signal["data_mapping_buff"] = buff

            if if_need_stat:
                cls.__add_to_sr_dm_glob_vars_individual("status", stat)
                for signal in port_signal_group_list[1]:
                    signal["data_mapping_status"] = stat

    @classmethod
    def __is_tx_signal_periodic(cls, port_signal_group_list):
        for signal in port_signal_group_list[1]:
            if not signal["is_signal_periodic"]:
                return False
        return True

    @classmethod
    def __update_sr_data_mapping_buff_info_each_group_intra_osa_tx(
        cls, port_signal_group_list, first_signal, datatype, init_value
    ):
        if cls.is_datamapping_opt_tx and cls.__is_tx_signal_periodic(port_signal_group_list):
            for port in port_signal_group_list[0]:
                # only used in port API, not in proxy
                osapplication = port["osapplication"]
                port["is_com_tx_opt"] = True
                buff_last = {
                    "name": f"Rte_{port['swc_port_var']}_{first_signal['direction']}_LastUpdated",
                    "memmap_category": MemmapCategory.OSA_PRIVATE,
                    "datatype": datatype,
                    "init_value": init_value,
                    "osa": osapplication,
                    "core_id": port["core_id"],
                    "init_category": VariableInitCategory.NO_INIT,
                }
                port["data_mapping_buff_last"] = buff_last
                cls.__add_to_sr_dm_glob_vars_individual("buff_last", buff_last)
                flag = {
                    "name": f"Rte_{port['swc_port_var']}_{first_signal['direction']}_IsSending",
                    "memmap_category": MemmapCategory.OSA_PRIVATE,
                    "parent_struct_name": f"Rte_IsProxySending_{osapplication}_{MemmapCategory.OSA_PRIVATE.value}",
                    "osa": osapplication,
                    "core_id": port["core_id"],
                    "init_category": VariableInitCategory.INIT,
                }
                port["data_mapping_flag_is_proxy_sending"] = flag
                cls.__add_to_sr_dm_glob_vars_complex("flag_is_proxy_sending", flag)

    @classmethod
    def __update_sr_data_mapping_buff_info_each_group_has_inter_osa(cls, port_signal_group_list, is_tx):
        first_signal = port_signal_group_list[1][0]
        datatype = first_signal["datatype"]
        init_value = first_signal["init_value"]
        m_to_n = first_signal["data_mapping_m_to_n"]
        if is_tx:
            cls.__update_sr_data_mapping_buff_info_each_group_has_inter_osa_tx(
                port_signal_group_list, first_signal, datatype, init_value, m_to_n
            )
        else:
            cls.__update_sr_data_mapping_buff_info_each_group_has_inter_osa_rx(
                port_signal_group_list, first_signal, datatype, init_value, m_to_n
            )

    @classmethod
    def __update_sr_data_mapping_buff_info_each_group_has_inter_osa_rx(
        cls, port_signal_group_list, first_signal, datatype, init_value, m_to_n
    ):
        if m_to_n == "n1":
            # n signal -> 1 port
            first_port = port_signal_group_list[0][0]
            buff = {
                "name": f"Rte_{first_port['swc_port_var']}_{first_signal['direction']}",
                "datatype": datatype,
                "init_value": init_value,
                "osa": first_port["osapplication"],
                "core_id": first_port["core_id"],
                "memmap_category": MemmapCategory.GLOBAL,
                "init_category": None,
            }
            cls.__add_to_sr_dm_glob_vars_individual("buff", buff)
            first_port["data_mapping_buff"] = buff
            for signal in port_signal_group_list[1]:
                signal["data_mapping_buff"] = buff

            if not first_port["is_implicit"]:
                stat = {
                    "name": f"Rte_Status_{buff['name']}",
                    "osa": first_port["osapplication"],
                    "core_id": first_port["core_id"],
                    "memmap_category": MemmapCategory.GLOBAL,
                    "init_category": VariableInitCategory.ZERO_INIT,
                }
                cls.__add_to_sr_dm_glob_vars_individual("status", stat)
                first_port["data_mapping_status"] = stat
                for signal in port_signal_group_list[1]:
                    signal["data_mapping_status"] = stat
        else:
            buff_memmap_category = cls.__get_memmap_category(port_signal_group_list[1], port_signal_group_list[0])
            buff = {
                "name": f"Rte_{first_signal['name']}_{first_signal['direction']}",
                "datatype": datatype,
                "init_value": init_value,
                "osa": first_signal["osa"],
                "core_id": first_signal["core_id"],
                "memmap_category": buff_memmap_category,
                "init_category": None,
            }
            cls.__add_to_sr_dm_glob_vars_individual("buff", buff)
            first_signal["data_mapping_buff"] = buff

            if_need_stat = False
            stat = {
                "name": f"Rte_Status_{buff['name']}",
                "osa": first_signal["osa"],
                "core_id": first_signal["core_id"],
                "memmap_category": buff_memmap_category,
                "init_category": VariableInitCategory.ZERO_INIT,
            }
            for port in port_signal_group_list[0]:
                port["data_mapping_buff"] = buff
                if not port["is_implicit"]:
                    port["data_mapping_status"] = stat
                    if_need_stat = True
            if len(port_signal_group_list[1]) > 1:
                for signal in port_signal_group_list[1]:
                    signal["data_mapping_buff"] = buff

            if if_need_stat:
                cls.__add_to_sr_dm_glob_vars_individual("status", stat)
                for signal in port_signal_group_list[1]:
                    signal["data_mapping_status"] = stat

    @classmethod
    def __update_sr_data_mapping_buff_info_each_group_has_inter_osa_tx(
        cls, port_signal_group_list, first_signal, datatype, init_value, m_to_n
    ):
        if m_to_n == "n1":
            # n port -> 1 signal
            cls.__update_sr_data_mapping_buff_info_each_group_has_inter_osa_tx_n1(
                port_signal_group_list, first_signal, datatype, init_value
            )
        elif m_to_n == "11":
            cls.__update_sr_data_mapping_buff_info_each_group_has_inter_osa_tx_11(
                port_signal_group_list, first_signal, datatype, init_value
            )
        else:
            cls.__update_sr_data_mapping_buff_info_each_group_has_inter_osa_tx_1n_mn(
                port_signal_group_list, first_signal, datatype, init_value
            )

    @classmethod
    def __update_sr_data_mapping_buff_info_each_group_has_inter_osa_tx_1n_mn(
        cls, port_signal_group_list, first_signal, datatype, init_value
    ):
        first_port = port_signal_group_list[0][0]
        buff = {
            "name": f"Rte_{first_port['swc_port_var']}_{first_signal['direction']}",
            "datatype": datatype,
            "init_value": init_value,
            "memmap_category": cls.__get_memmap_category(port_signal_group_list[0], port_signal_group_list[1]),
            "osa": first_port["osapplication"],
            "core_id": first_port["core_id"],
            "init_category": None,
        }
        cls.__add_to_sr_dm_glob_vars_individual("buff", buff)

        if_need_stat = False
        stat = {
            "name": f"Rte_Status_{buff['name']}",
            "osa": first_port["osapplication"],
            "core_id": first_port["core_id"],
            "memmap_category": MemmapCategory.GLOBAL,
            "init_category": VariableInitCategory.ZERO_INIT,
        }
        for port in port_signal_group_list[0]:
            port["data_mapping_buff"] = buff
            if not port["is_implicit"]:
                port["data_mapping_status"] = stat
                if_need_stat = True
        for signal in port_signal_group_list[1]:
            signal["data_mapping_buff"] = buff

        if if_need_stat:
            cls.__add_to_sr_dm_glob_vars_individual("status", stat)
            for signal in port_signal_group_list[1]:
                signal["data_mapping_status"] = stat

        if cls.is_datamapping_opt_tx and cls.__is_tx_signal_periodic(port_signal_group_list):
            buff_last_memmap_category = cls.__get_memmap_category(port_signal_group_list[0], port_signal_group_list[0])
            buff_last = {
                "name": f"Rte_{first_port['swc_port_var']}_{first_signal['direction']}_LastUpdated",
                "datatype": datatype,
                "init_value": init_value,
                "osa": first_port["osapplication"],
                "core_id": first_port["core_id"],
                "memmap_category": buff_last_memmap_category,
                "init_category": VariableInitCategory.NO_INIT,
            }
            cls.__add_to_sr_dm_glob_vars_individual("buff_last", buff_last)

            flag_memmap_category = buff_last_memmap_category
            flag_is_proxy_sending = {
                "name": f"Rte_{first_port['swc_port_var']}_{first_signal['direction']}_IsSending",
                "memmap_category": flag_memmap_category,
                "parent_struct_name": f"Rte_IsProxySending_{first_port['osapplication']}_{flag_memmap_category.value}",
                "osa": first_port["osapplication"],
                "core_id": first_port["core_id"],
                "init_category": VariableInitCategory.INIT,
            }
            cls.__add_to_sr_dm_glob_vars_complex("flag_is_proxy_sending", flag_is_proxy_sending)
            for port in port_signal_group_list[0]:
                port["is_com_tx_opt"] = True
                port["data_mapping_buff_last"] = buff_last
                port["data_mapping_flag_is_proxy_sending"] = flag_is_proxy_sending
            for signal in port_signal_group_list[1]:
                signal["is_com_tx_opt"] = True
                signal["data_mapping_buff_last"] = buff_last
                signal["data_mapping_flag_is_proxy_sending"] = flag_is_proxy_sending

    @classmethod
    def __update_sr_data_mapping_buff_info_each_group_has_inter_osa_tx_11(
        cls, port_signal_group_list, first_signal, datatype, init_value
    ):
        first_port = port_signal_group_list[0][0]

        buff = {
            "name": f"Rte_{first_port['swc_port_var']}_{first_signal['direction']}",
            "datatype": datatype,
            "init_value": init_value,
            "memmap_category": MemmapCategory.OSA_SHARED,
            "osa": first_port["osapplication"],
            "core_id": first_port["core_id"],
            "init_category": None,
        }
        cls.__add_to_sr_dm_glob_vars_individual("buff", buff)
        first_signal["data_mapping_buff"] = buff
        first_port["data_mapping_buff"] = buff

        if not first_port["is_implicit"]:
            stat = {
                "name": f"Rte_{first_signal['name']}_{first_signal['direction']}",
                "osa": first_signal["osa"],
                "core_id": first_signal["core_id"],
                "memmap_category": MemmapCategory.OSA_SHARED,
                "init_category": VariableInitCategory.ZERO_INIT,
            }
            first_port["data_mapping_status"] = stat
            first_signal["data_mapping_status"] = stat
            cls.__add_to_sr_dm_glob_vars_individual("status", stat)

        if cls.is_datamapping_opt_tx and cls.__is_tx_signal_periodic(port_signal_group_list):
            all_port_signals = port_signal_group_list[0] + port_signal_group_list[1]
            flag_memmap_category = cls.__get_memmap_category(all_port_signals, all_port_signals)
            flag_is_proxy_sending = {
                "name": f"Rte_{first_signal['name']}_{first_signal['direction']}_IsSending",
                "memmap_category": flag_memmap_category,
                "parent_struct_name": f"Rte_IsProxySending_{first_signal['osa']}_{flag_memmap_category.value}",
                "osa": first_signal["osa"],
                "core_id": first_signal["core_id"],
                "init_category": VariableInitCategory.INIT,
            }
            cls.__add_to_sr_dm_glob_vars_complex("flag_is_proxy_sending", flag_is_proxy_sending)
            first_signal["data_mapping_flag_is_proxy_sending"] = flag_is_proxy_sending
            buff_last = {
                "name": f"Rte_{first_port['name']}_{first_signal['direction']}_LastUpdated",
                "datatype": datatype,
                "init_value": init_value,
                "osa": first_port["osapplication"],
                "core_id": first_port["core_id"],
                "memmap_category": MemmapCategory.OSA_PRIVATE,
                "init_category": VariableInitCategory.NO_INIT,
            }
            cls.__add_to_sr_dm_glob_vars_individual("buff_last", buff_last)
            first_port["is_com_tx_opt"] = True
            first_port["data_mapping_buff_last"] = buff_last
            first_port["data_mapping_flag_is_proxy_sending"] = flag_is_proxy_sending
            first_signal["is_com_tx_opt"] = True
            first_signal["data_mapping_buff_last"] = buff_last
            first_signal["data_mapping_flag_is_proxy_sending"] = flag_is_proxy_sending

    @classmethod
    def __update_sr_data_mapping_buff_info_each_group_has_inter_osa_tx_n1(
        cls, port_signal_group_list, first_signal, datatype, init_value
    ):
        buff = {
            "name": f"Rte_{first_signal['name']}_{first_signal['direction']}",
            "datatype": datatype,
            "init_value": init_value,
            "osa": first_signal["osa"],
            "core_id": first_signal["core_id"],
            "memmap_category": MemmapCategory.GLOBAL,
            "init_category": None,
        }
        cls.__add_to_sr_dm_glob_vars_individual("buff", buff)
        first_signal["data_mapping_buff"] = buff

        if_need_stat = False
        stat = {
            "name": f"Rte_Status_{buff['name']}",
            "osa": first_signal["osa"],
            "core_id": first_signal["core_id"],
            "memmap_category": cls.__get_memmap_category(port_signal_group_list[1], port_signal_group_list[0]),
            "init_category": VariableInitCategory.ZERO_INIT,
        }
        for port in port_signal_group_list[0]:
            port["data_mapping_buff"] = buff
            if not port["is_implicit"]:
                port["data_mapping_status"] = stat
                if_need_stat = True
        if if_need_stat:
            cls.__add_to_sr_dm_glob_vars_individual("status", stat)
            first_signal["data_mapping_status"] = stat

        if cls.is_datamapping_opt_tx and cls.__is_tx_signal_periodic(port_signal_group_list):
            all_port_signals = port_signal_group_list[0] + port_signal_group_list[1]
            flag_memmap_category = cls.__get_memmap_category(all_port_signals, all_port_signals)
            flag_is_proxy_sending = {
                "name": f"Rte_{first_signal['name']}_{first_signal['direction']}_IsSending",
                "memmap_category": flag_memmap_category,
                "parent_struct_name": f"Rte_IsProxySending_{first_signal['osa']}_{flag_memmap_category.value}",
                "osa": first_signal["osa"],
                "core_id": first_signal["core_id"],
                "init_category": VariableInitCategory.INIT,
            }
            cls.__add_to_sr_dm_glob_vars_complex("flag_is_proxy_sending", flag_is_proxy_sending)
            first_signal["data_mapping_flag_is_proxy_sending"] = flag_is_proxy_sending
            buff_last_memmap_category = flag_memmap_category
            buff_last = {
                "name": f"Rte_{first_signal['name']}_{first_signal['direction']}_LastUpdated",
                "datatype": datatype,
                "init_value": init_value,
                "osa": first_signal["osa"],
                "core_id": first_signal["core_id"],
                "memmap_category": buff_last_memmap_category,
                "init_category": VariableInitCategory.NO_INIT,
            }
            cls.__add_to_sr_dm_glob_vars_individual("buff_last", buff_last)
            for port in port_signal_group_list[0]:
                port["is_com_tx_opt"] = True
                port["data_mapping_buff_last"] = buff_last
                port["data_mapping_flag_is_proxy_sending"] = flag_is_proxy_sending
            for signal in port_signal_group_list[1]:
                signal["is_com_tx_opt"] = True
                signal["data_mapping_buff_last"] = buff_last
                signal["data_mapping_flag_is_proxy_sending"] = flag_is_proxy_sending

    @classmethod
    def __update_sr_data_mapping_lock_info_each_group_intra_osa(cls):
        """
        nothing to do for right now
        """
        pass

    @classmethod
    def __update_sr_data_mapping_lock_info_each_group_has_inter_osa_same_core(cls, port_signal_group_list):
        # default: isr
        for port in port_signal_group_list[0]:
            port["data_mapping_lock"] = "OSISR"
        for signal in port_signal_group_list[1]:
            signal["data_mapping_lock"] = "OSISR"

        # check if all tasks are valid
        for signal in port_signal_group_list[1]:
            if not signal["task"]:
                return
        for port in port_signal_group_list[0]:
            if not port["task"]:
                return
            for task in port["task"]:
                if not task:
                    return

        # optimization based on same task execution
        has_multi_task = False
        single_task = None
        for entity in port_signal_group_list[0] + port_signal_group_list[1]:
            if len(set(entity["task"])) != 1:
                has_multi_task = True
                break
            curr_task = entity["task"][0]
            if single_task:
                if single_task != curr_task:
                    has_multi_task = True
                    break
            else:
                single_task = curr_task
        if not has_multi_task:
            for port in port_signal_group_list[0]:
                port["data_mapping_lock"] = "NONE"
            for signal in port_signal_group_list[1]:
                signal["data_mapping_lock"] = "NONE"
            return

        # os interrupt lock based on task scheduling
        if cls.is_ea_opt_enabled:
            port_to_task_info_dict, highest_port_task_priority = cls.__process_all_tasks(
                port_signal_group_list[0], "port_full_key"
            )
            proxy_to_task_info_dict, highest_proxy_task_priority = cls.__process_all_tasks(
                port_signal_group_list[1], "name"
            )
            highest_task_priority = max(highest_port_task_priority, highest_proxy_task_priority)
            for port in port_signal_group_list[0]:
                curr_port_lock = "NONE"
                for task_info in port_to_task_info_dict[port["port_full_key"]]:
                    if task_info[0] < highest_task_priority and task_info[1]:
                        curr_port_lock = "OSISR"
                        break
                port["data_mapping_lock"] = curr_port_lock
            for signal in port_signal_group_list[1]:
                curr_port_lock = "NONE"
                for task_info in proxy_to_task_info_dict[signal["name"]]:
                    if task_info[0] < highest_task_priority and task_info[1]:
                        curr_port_lock = "OSISR"
                        break
                signal["data_mapping_lock"] = curr_port_lock

    @classmethod
    def __update_sr_data_mapping_lock_info_each_group_has_inter_core(cls, port_signal_group_list):
        core_id_set = set()
        for port in port_signal_group_list[0]:
            core_id_set.add(port["core_id"])
            port["data_mapping_lock"] = "SPINLOCK"
        for signal in port_signal_group_list[1]:
            core_id_set.add(signal["core_id"])
            signal["data_mapping_lock"] = "SPINLOCK"
        has_more_than_two_cores = len(core_id_set) > 2

        is_rw = port_signal_group_list[0][0]["data_mapping_m_to_n"] in {"1n", "mn"}

        if has_more_than_two_cores:
            spinlock_id = ("OS_SPINLOCK_Rte_Com_Global_RW" if is_rw else "OS_SPINLOCK_Rte_Com_Global").upper()
            spinlock_cfg = {
                "lock_id": spinlock_id,
                "access_osa": cls.all_osa,
                "lock_metohd": "LOCK_CAT2_INTERRUPTS",
                "is_rw": is_rw,
            }
        else:
            sorted_core_id = sorted(core_id_set)
            spinlock_id = (
                f"OS_SPINLOCK_Rte_Com_Core_{sorted_core_id[0]}_{sorted_core_id[1]}_RW"
                if is_rw
                else f"OS_SPINLOCK_Rte_Com_Core_{sorted_core_id[0]}_{sorted_core_id[1]}"
            ).upper()
            access_osa = []
            for core_id in sorted_core_id:
                access_osa.extend(cls.core_osa_map[core_id])
            spinlock_cfg = {
                "lock_id": spinlock_id,
                "access_osa": access_osa,
                "lock_metohd": "LOCK_CAT2_INTERRUPTS",
                "is_rw": is_rw,
            }

        is_tx = port_signal_group_list[0][0]["is_p"]
        for port in port_signal_group_list[0]:
            port["data_mapping_lock_id"] = spinlock_id
            port["data_mapping_spinlock_cfg"] = spinlock_cfg
            if spinlock_cfg["is_rw"]:
                port["data_mapping_spinlock_api_postfix"] = "Write" if is_tx else "Read"
            else:
                port["data_mapping_spinlock_api_postfix"] = ""
        for signal in port_signal_group_list[1]:
            signal["data_mapping_lock_id"] = spinlock_id
            signal["data_mapping_spinlock_cfg"] = spinlock_cfg
            if spinlock_cfg["is_rw"]:
                signal["data_mapping_spinlock_api_postfix"] = "Read" if is_tx else "Write"
            else:
                signal["data_mapping_spinlock_api_postfix"] = ""

    @classmethod
    def __update_sr_data_mapping_datatype_each_group(cls, port_signal_group_list):
        fst_port = port_signal_group_list[0][0]
        for signal in port_signal_group_list[1]:
            signal["datatype"] = fst_port["arg"]["datatype"]
            signal["type_mappings"] = fst_port["type_mappings"]
            signal["init_value"] = fst_port["arg"]["init_value"]

    @classmethod
    def __update_sr_data_mapping_flag_each_group(cls, port_signal_group_list, is_tx):
        for port in port_signal_group_list[0]:
            port["data_mapping_flag"] = {}
        for signal in port_signal_group_list[1]:
            signal["data_mapping_flag"] = {}
        if is_tx:
            cls.__update_sr_data_mapping_flag_each_group_tx(port_signal_group_list)
        else:
            cls.__update_sr_data_mapping_flag_each_group_rx(port_signal_group_list)

    @classmethod
    def __update_sr_data_mapping_flag_each_group_rx(cls, port_signal_group_list):
        is_updated_flags = []
        is_received_flags = []
        is_timeout_flags = []
        for port in port_signal_group_list[0]:
            # flag isUpdated
            port_id_postfix = f"{port['swc_port_var']}_Rx"
            port_core_id = port["core_id"]
            port_osa = port["osapplication"]
            curr_mixed_port_signal_group_list = [port] + port_signal_group_list[1]
            if port["required_com_specs"]["enable_update"] == "true":
                flag_is_updated_memmap_category = cls.__get_memmap_category(
                    curr_mixed_port_signal_group_list, curr_mixed_port_signal_group_list
                )
                flag = {
                    "name": f"Rte_IsUpdated_{port_id_postfix}",
                    "core_id": port_core_id,
                    "osa": port_osa,
                    "memmap_category": flag_is_updated_memmap_category,
                    "parent_struct_name": f"Rte_IsUpdatedRx_{port_osa}_{flag_is_updated_memmap_category.value}",
                    "init_category": VariableInitCategory.ZERO_INIT,
                }
                port["data_mapping_flag"]["is_updated"] = flag
                is_updated_flags.append(port["data_mapping_flag"]["is_updated"])
                cls.__add_to_sr_dm_glob_vars_complex("flag_is_updated_rx", flag)
            else:
                port["data_mapping_flag"]["is_updated"] = {}

            # flag is data received
            if port["required_com_specs"]["handle_never_received"] == "true":
                flag_is_received_memmap_category = cls.__get_memmap_category(
                    curr_mixed_port_signal_group_list, curr_mixed_port_signal_group_list
                )
                flag = {
                    "name": f"Rte_IsReceived_{port_id_postfix}",
                    "core_id": port_core_id,
                    "osa": port_osa,
                    "memmap_category": flag_is_received_memmap_category,
                    "parent_struct_name": f"Rte_IsReceivedRx_{port_osa}_{flag_is_received_memmap_category.value}",
                    "init_category": VariableInitCategory.ZERO_INIT,
                }
                port["data_mapping_flag"]["is_received"] = flag
                is_received_flags.append(port["data_mapping_flag"]["is_received"])
                cls.__add_to_sr_dm_glob_vars_complex("flag_is_received", flag)
            else:
                port["data_mapping_flag"]["is_received"] = {}

            # flag is timeout
            if port["required_com_specs"]["alive_timeout"] not in {"0", "0.0"}:
                flag_is_timeout_memmap_category = cls.__get_memmap_category(
                    curr_mixed_port_signal_group_list, curr_mixed_port_signal_group_list
                )
                flag = {
                    "name": f"Rte_IsTimeout_{port_id_postfix}",
                    "core_id": port_core_id,
                    "osa": port_osa,
                    "memmap_category": flag_is_timeout_memmap_category,
                    "parent_struct_name": f"Rte_IsTimeoutRx_{port_osa}_{flag_is_timeout_memmap_category.value}",
                    "init_category": VariableInitCategory.ZERO_INIT,
                }
                port["data_mapping_flag"]["is_timeout"] = flag
                is_timeout_flags.append(port["data_mapping_flag"]["is_timeout"])
                cls.__add_to_sr_dm_glob_vars_complex("flag_is_timeout", flag)
            else:
                port["data_mapping_flag"]["is_timeout"] = {}

        for signal in port_signal_group_list[1]:
            signal["data_mapping_flag"]["is_updated"] = is_updated_flags
            signal["data_mapping_flag"]["is_received"] = is_received_flags
            signal["data_mapping_flag"]["is_timeout"] = is_timeout_flags

    @classmethod
    def __update_sr_data_mapping_flag_each_group_tx(cls, port_signal_group_list):
        fst_sig = port_signal_group_list[1][0]
        if not (fst_sig["data_mapping_has_inter_core"] or fst_sig["data_mapping_has_inter_osa_same_core"]):
            return

        is_updated_flags = []
        for signal in port_signal_group_list[1]:
            mixed_port_signal_group_list = port_signal_group_list[0] + [signal]
            curr_flag_memmap_category = cls.__get_memmap_category(
                mixed_port_signal_group_list, mixed_port_signal_group_list
            )
            flag = {
                "name": f"Rte_IsUpdated_{signal['name']}_{signal['direction']}",
                "core_id": signal["core_id"],
                "osa": signal["osa"],
                "memmap_category": curr_flag_memmap_category,
                "parent_struct_name": f"Rte_IsUpdatedTx_{signal['osa']}_{curr_flag_memmap_category.value}",
                "init_category": VariableInitCategory.ZERO_INIT,
            }
            signal["data_mapping_flag"]["is_updated"] = flag
            is_updated_flags.append(signal["data_mapping_flag"]["is_updated"])
            cls.__add_to_sr_dm_glob_vars_complex("flag_is_updated_tx", flag)
        for port in port_signal_group_list[0]:
            port["data_mapping_flag"]["is_updated"] = is_updated_flags

    @classmethod
    def __update_sr_data_mapping_rx_com_spec_each_group(cls, port_signal_group_list):
        event_list = []
        evt_set = set()
        enable_update_list = []
        handle_never_received_list = []
        alive_timeout_list = []
        for port in port_signal_group_list[0]:
            events = port["trigger_event_list"]
            for evt in events:
                if evt["event_type"] != "DataReceivedEvent":
                    continue
                if evt["event_key"] in evt_set:
                    continue
                evt_set.add(evt["event_key"])
                event_list.append(evt)
            enable_update = port.get("required_com_specs", {}).get("enable_update", "false")
            if enable_update == "true":
                enable_update_list.append(port)
            handle_never_received = port.get("required_com_specs", {}).get("handle_never_received", "false")
            if handle_never_received == "true":
                handle_never_received_list.append(port)
            alive_timeout = port.get("required_com_specs", {}).get("alive_timeout", "0")
            if alive_timeout not in {"0", "0.0"}:
                alive_timeout_list.append(port)
        for signal in port_signal_group_list[1]:
            signal["trigger_event"] = event_list
            signal["enable_update"] = enable_update_list
            signal["handle_never_received"] = handle_never_received_list
            signal["alive_timeout"] = alive_timeout_list

    @classmethod
    def __update_sr_data_mapping_m_to_n_each_group(cls, port_signal_group_list, is_tx):
        if len(port_signal_group_list[0]) > 1 and len(port_signal_group_list[1]) > 1:
            signals_names = ""
            for signal in port_signal_group_list[1]:
                signals_names += f" - {signal['name']}"
            logger.warning(f"DataMapping: M:N mapping for signals{signals_names}")
            m_to_n = "mn"
        elif len(port_signal_group_list[0]) > 1:
            m_to_n = "n1" if is_tx else "1n"
        elif len(port_signal_group_list[1]) > 1:
            m_to_n = "1n" if is_tx else "n1"
        else:
            m_to_n = "11"
        port_signal_group_list[0].sort(key=lambda x: x["port_full_key"])
        port_signal_group_list[1].sort(key=lambda x: x["name"])
        datatype = port_signal_group_list[0][0]["arg"]["datatype"]
        for port in port_signal_group_list[0]:
            port["data_mapping_m_to_n"] = m_to_n
            port["sr_signal_port_group"] = port_signal_group_list
        for signal in port_signal_group_list[1]:
            signal["data_mapping_m_to_n"] = m_to_n
            signal["sr_signal_port_group"] = port_signal_group_list
            signal["datatype"] = datatype

    @classmethod
    def __update_sr_m_to_n_status(cls, asw_dict):
        # update N:M info for SR
        port_group_id_set = set()
        m_to_n_status = [None]
        for _, swc_info in asw_dict.items():
            for _, pport in swc_info["pports"].items():
                m_to_n_status[0] = None
                port_group_id_set.clear()
                port_group_list = []
                cls.__update_sr_m_to_n_status_each_group(pport, port_group_list, port_group_id_set, True, m_to_n_status)
                if not m_to_n_status[0]:
                    continue
                has_prport = cls.__check_if_has_prport_in_connected_port_group(port_group_list)
                if m_to_n_status[0] == "mn" and not has_prport:
                    logger.error(f"M:N SR connection! {pport['swc_port_var']}")
                port_group_list.sort(key=lambda x: x["port_full_key"])
                for port in port_group_list:
                    port["m_to_n"] = m_to_n_status[0]
                    port["sr_port_group"] = port_group_list
                    port["has_prport"] = has_prport
            for _, rport in swc_info["rports"].items():
                m_to_n_status[0] = None
                port_group_id_set.clear()
                port_group_list = []
                cls.__update_sr_m_to_n_status_each_group(
                    rport, port_group_list, port_group_id_set, False, m_to_n_status
                )
                if not m_to_n_status[0]:
                    continue
                has_prport = cls.__check_if_has_prport_in_connected_port_group(port_group_list)
                if m_to_n_status[0] == "mn" and not has_prport:
                    logger.error(f"M:N SR connection! {rport['swc_port_var']}")
                port_group_list.sort(key=lambda x: x["port_full_key"])
                for port in port_group_list:
                    port["m_to_n"] = m_to_n_status[0]
                    port["sr_port_group"] = port_group_list
                    port["has_prport"] = has_prport

    @classmethod
    def __update_cal_prm_port_info(cls, asw_dict):
        param_ports = {}
        for _, swc_info in asw_dict.items():
            for rport_name, rport in swc_info["rports"].items():
                if rport["type"] != cls.cal_prm_rport_type:
                    continue
                if rport_name not in param_ports.keys():
                    param_ports[rport_name] = []
                param_ports[rport_name].append(rport)
        for _, ports in param_ports.items():
            port_groups = {}
            for rport in ports:
                prm_ref = rport["prm_ref"]
                if prm_ref not in port_groups.keys():
                    port_groups[prm_ref] = []
                port_groups[prm_ref].append(rport)
                rport["prm_port_group"] = port_groups[prm_ref]
            for _, group_ports in port_groups.items():
                if len(group_ports) == 0:
                    m_to_n = "0"
                    continue
                elif len(group_ports) == 1:
                    m_to_n = "11"
                else:
                    m_to_n = "1n"
                cal_prm_const = f"Rte_{group_ports[0]['sort_name']}"
                for port in group_ports:
                    port["m_to_n"] = m_to_n
                    port["cal_prm_const"] = cal_prm_const
                    port["connected"] = True

    @classmethod
    def __update_sr_func_safe_info_each_port_group(cls, curr_port, visited_ports, osa_asils, is_p_port):
        if not cls.__is_sr_nonq_port(curr_port):
            return
        if curr_port["m_to_n"] in {"0", "mn"}:
            return
        if curr_port["port_full_key"] in visited_ports:
            return
        all_non_q_participant_ports = curr_port["sr_port_group"]
        visited_ports.update(port["port_full_key"] for port in all_non_q_participant_ports)
        if curr_port["m_to_n"] == "n1":
            cls.__update_sr_func_safe_info_each_port_group_n1(
                curr_port, is_p_port, all_non_q_participant_ports, osa_asils
            )
        else:
            cls.__update_sr_func_safe_info_each_port_group_11_1n(curr_port, is_p_port, all_non_q_participant_ports)

    @classmethod
    def __update_sr_func_safe_info_each_port_group_11_1n(cls, curr_port, is_p_port, all_non_q_participant_ports):
        if is_p_port:
            p_port = curr_port
        else:
            p_port = curr_port["conn_asw_ports"][0]
        p_osa = p_port["osapplication"]
        p_core_id = p_port["core_id"]
        has_inter_core = False
        has_inter_osa_same_core = False
        for port in all_non_q_participant_ports:
            if port == p_port:
                continue
            if port["core_id"] != p_core_id:
                has_inter_core = True
                break
            elif port["osapplication"] != p_osa:
                has_inter_osa_same_core = True
        if has_inter_core:
            p_port["buff_category"] = "inter_core"
            for port in all_non_q_participant_ports:
                port["buff_memmap_category"] = MemmapCategory.OSA_SHARED
        elif has_inter_osa_same_core:
            p_port["buff_category"] = "inter_osa_same_core"
            for port in all_non_q_participant_ports:
                port["buff_memmap_category"] = MemmapCategory.OSA_SHARED
        else:
            p_port["buff_category"] = "intra_osa"
            for port in all_non_q_participant_ports:
                port["buff_memmap_category"] = MemmapCategory.OSA_PRIVATE

    @classmethod
    def __update_sr_func_safe_info_each_port_group_n1(
        cls, curr_port, is_p_port, all_non_q_participant_ports, osa_asils
    ):
        if is_p_port:
            r_port = curr_port["conn_asw_ports"][0]
        else:
            r_port = curr_port
        has_inter_core = False
        has_inter_osa_same_core = False
        curr_osa = curr_port["osapplication"]
        curr_core_id = curr_port["core_id"]
        for port in all_non_q_participant_ports:
            if port["core_id"] != curr_core_id:
                has_inter_core = True
            elif port["osapplication"] != curr_osa:
                has_inter_osa_same_core = True
        cls.__update_sr_func_safe_info_each_port_group_n1_sub(
            r_port, all_non_q_participant_ports, osa_asils, has_inter_core, has_inter_osa_same_core
        )

    @classmethod
    def __update_sr_func_safe_info_each_port_group_n1_sub(
        cls, r_port, all_non_q_participant_ports, osa_asils, has_inter_core, has_inter_osa_same_core
    ):
        if not (has_inter_core or has_inter_osa_same_core):
            for port in all_non_q_participant_ports:
                port["single_rec_buff_for_n1"] = True
                port["buff_memmap_category"] = MemmapCategory.OSA_PRIVATE
            r_port["buff_category"] = "intra_osa"
        else:
            r_port_asil = cls.__get_osa_asil(osa_asils, r_port["osapplication"])
            single_rec_buff_for_n1 = True
            if r_port_asil != "QM":
                for it_port in all_non_q_participant_ports:
                    if it_port == r_port:
                        continue
                    curr_asil = cls.__get_osa_asil(osa_asils, it_port["osapplication"])
                    if cls.__is_higher_asil_rating(r_port_asil, curr_asil):
                        single_rec_buff_for_n1 = False
                        break
            if single_rec_buff_for_n1:
                for port in all_non_q_participant_ports:
                    port["single_rec_buff_for_n1"] = True
                if has_inter_core:
                    r_port["buff_category"] = "inter_core"
                    for port in all_non_q_participant_ports:
                        port["buff_memmap_category"] = MemmapCategory.GLOBAL
                elif has_inter_osa_same_core:
                    r_port["buff_category"] = "inter_osa_same_core"
                    for port in all_non_q_participant_ports:
                        port["buff_memmap_category"] = MemmapCategory.GLOBAL
                else:
                    r_port["buff_category"] = "intra_osa"
                    for port in all_non_q_participant_ports:
                        port["buff_memmap_category"] = MemmapCategory.OSA_PRIVATE
            else:
                r_port_osa = r_port["osapplication"]
                r_port_core_id = r_port["core_id"]
                for port in all_non_q_participant_ports:
                    port["single_rec_buff_for_n1"] = False
                    if port == r_port:
                        port["buff_category"] = "intra_osa"
                        port["buff_memmap_category"] = MemmapCategory.OSA_PRIVATE
                        if has_inter_core:
                            port["counter_category"] = "inter_core"
                            port["counter_memmap_category"] = MemmapCategory.GLOBAL
                        elif has_inter_osa_same_core:
                            port["counter_category"] = "inter_osa_same_core"
                            port["counter_memmap_category"] = MemmapCategory.GLOBAL
                    else:
                        if port["core_id"] != r_port_core_id:
                            port["buff_category"] = "inter_core"
                            port["buff_memmap_category"] = MemmapCategory.OSA_SHARED
                            port["counter_category"] = "inter_core"
                            port["counter_memmap_category"] = MemmapCategory.GLOBAL
                        elif port["osapplication"] != r_port_osa:
                            port["buff_category"] = "inter_osa_same_core"
                            port["buff_memmap_category"] = MemmapCategory.OSA_SHARED
                            port["counter_category"] = "inter_osa_same_core"
                            port["counter_memmap_category"] = MemmapCategory.GLOBAL
                        else:
                            port["buff_category"] = "intra_osa"
                            port["buff_memmap_category"] = MemmapCategory.OSA_PRIVATE
                            port["counter_category"] = "intra_osa"
                            port["counter_memmap_category"] = MemmapCategory.OSA_PRIVATE

    @classmethod
    def __is_higher_asil_rating(cls, asil_1, asil_2):
        """
        check if asil_1 > asil_2
        """
        if asil_1 == "QM":
            return False
        elif asil_2 == "QM":
            return True
        else:
            return asil_1 > asil_2

    @classmethod
    def __get_osa_asil(cls, osa_asils, osa_name):
        if (not osa_name) or (osa_name not in osa_asils) or (not osa_asils[osa_name]):
            return "QM"
        return osa_asils[osa_name]

    @classmethod
    def __find_sr_data_mapping_each_group(
        cls, signal_dict, signal_name, port_id_set, signal_id_set, port_signal_group_list, osa_set, core_id_set
    ):
        if signal_name in signal_id_set:
            return
        signal_id_set.add(signal_name)
        curr_signal = signal_dict[signal_name]
        port_signal_group_list[1].append(curr_signal)
        osa_set.add(curr_signal["osa"])
        core_id_set.add(curr_signal["core_id"])
        for curr_port in curr_signal["conn_sr_port"]:
            if curr_port["port_full_key"] in port_id_set:
                continue
            port_id_set.add(curr_port["port_full_key"])
            port_signal_group_list[0].append(curr_port)
            osa_set.add(curr_port["osapplication"])
            core_id_set.add(curr_port["core_id"])

            if len(curr_port["mapping_to_signals"]) < 2:
                continue
            for op_signal_name in curr_port["mapping_to_signals"]:
                cls.__find_sr_data_mapping_each_group(
                    signal_dict,
                    op_signal_name,
                    port_id_set,
                    signal_id_set,
                    port_signal_group_list,
                    osa_set,
                    core_id_set,
                )

    @classmethod
    def __update_sr_m_to_n_status_each_group(
        cls, curr_port, port_group_list, port_group_id_set, is_p_port, m_to_n_status
    ):
        if ("port_interface_type" not in curr_port) or curr_port["port_interface_type"] != "sr":
            return False
        if "m_to_n" in curr_port:
            return
        if not curr_port["conn_asw_ports"]:
            curr_port["m_to_n"] = "0"
            return
        if curr_port["port_full_key"] in port_group_id_set:
            return
        port_group_id_set.add(curr_port["port_full_key"])
        port_group_list.append(curr_port)

        curr_has_multi_opposite_ports = False
        if len(curr_port["conn_asw_ports"]) > 1:
            # check for multiple opposite ports who are not the scenario of
            # multi access to the same data element within the same SWC
            opposite_ports_multi_access_set = set()
            for opposite_port in curr_port["conn_asw_ports"]:
                opposite_ports_multi_access_set.add(opposite_port["swc_port_var"])
                if len(opposite_ports_multi_access_set) > 1:
                    curr_has_multi_opposite_ports = True
                    break

        if not m_to_n_status[0]:
            if curr_has_multi_opposite_ports:
                m_to_n_status[0] = "1n" if is_p_port else "n1"
            else:
                m_to_n_status[0] = "11"
        elif m_to_n_status[0] == "11":
            if curr_has_multi_opposite_ports:
                m_to_n_status[0] = "1n" if is_p_port else "n1"
        elif m_to_n_status[0] == "1n":
            # R Port has multi P conns
            if curr_has_multi_opposite_ports and (not is_p_port):
                m_to_n_status[0] = "mn"
        elif m_to_n_status[0] == "n1":
            # P Port has multi R conns
            if curr_has_multi_opposite_ports and is_p_port:
                m_to_n_status[0] = "mn"

        # recursively get all connected ports:
        for opposite_port in curr_port["conn_asw_ports"]:
            cls.__update_sr_m_to_n_status_each_group(
                opposite_port, port_group_list, port_group_id_set, (not is_p_port), m_to_n_status
            )

    @classmethod
    def __update_mode_disabling_info(cls, asw_dict, mode_disabling_info):
        if not mode_disabling_info:
            return
        for _, swc_info in asw_dict.items():
            for _, port in swc_info["pports"].items():
                if ("port_interface_type" not in port) or port["port_interface_type"] != "mode":
                    continue
                if not port["conn_asw_ports"]:
                    continue
                for r_port in port["conn_asw_ports"]:
                    key = f"{r_port['swc_name']}_{r_port['port_name']}_{r_port['mode_group_prototype']}"
                    if key not in mode_disabling_info:
                        continue
                    for info in mode_disabling_info[key]:
                        rte_mode = f"RTE_MODE_{info['mdgp']}_{info['mode']}"
                        swc_run_key = info["swc_run"]
                        # add to r-port
                        if rte_mode not in r_port["mode_disabled_entity"]:
                            r_port["mode_disabled_entity"][rte_mode] = {}
                        r_port["mode_disabled_entity"][rte_mode][swc_run_key] = info
                        if swc_run_key not in r_port["mode_disabled_flag"]:
                            r_port["mode_disabled_flag"][swc_run_key] = {
                                "osa": info["osa"],
                                "disabled_mode": {info["mode"]},
                            }
                        else:
                            r_port["mode_disabled_flag"][swc_run_key]["disabled_mode"].add(info["mode"])
                        asw_dict[info["swc"]]["runnables"][info["runnable"]]["has_mode_disbaling"] = True

                        # add to p-port
                        if rte_mode not in port["mode_disabled_entity"]:
                            port["mode_disabled_entity"][rte_mode] = {}
                        port["mode_disabled_entity"][rte_mode][swc_run_key] = info
                        if swc_run_key not in port["mode_disabled_flag"]:
                            port["mode_disabled_flag"][swc_run_key] = {
                                "osa": info["osa"],
                                "disabled_mode": {info["mode"]},
                            }
                        else:
                            port["mode_disabled_flag"][swc_run_key]["disabled_mode"].add(info["mode"])
                    r_port["mode_disabled_entity"] = dict(sorted(r_port["mode_disabled_entity"].items()))
                    r_port["mode_disabled_flag"] = dict(sorted(r_port["mode_disabled_flag"].items()))
                    for _, infos in r_port["mode_disabled_entity"].items():
                        infos = dict(sorted(infos.items()))
                port["mode_disabled_entity"] = dict(sorted(port["mode_disabled_entity"].items()))
                port["mode_disabled_flag"] = dict(sorted(port["mode_disabled_flag"].items()))
                for _, infos in port["mode_disabled_entity"].items():
                    infos = dict(sorted(infos.items()))

    @classmethod
    def __find_mode_opposite_asw_ports(cls, asw_dict):
        for _, swc_info in asw_dict.items():
            for _, port in swc_info["pports"].items():
                if ("port_interface_type" not in port) or port["port_interface_type"] != "mode":
                    continue
                curr_path = port["port_path"]
                mgp = port["mode_group_prototype"]
                port["conn_asw_ports"] = []
                if curr_path not in cls.p_connections:
                    continue
                for opposite_path in cls.p_connections[curr_path]:
                    if opposite_path not in cls.mode_r_port_path_to_asw_port_dict:
                        continue
                    opposite_ports = cls.mode_r_port_path_to_asw_port_dict[opposite_path]
                    if mgp not in opposite_ports:
                        continue
                    opposite_asw_ports = opposite_ports[mgp]
                    port["conn_asw_ports"].extend(opposite_asw_ports.values())
                    for _, oppo_port in opposite_asw_ports.items():
                        oppo_port["conn_asw_ports"] = [port]
                port["conn_asw_ports"].sort(key=lambda x: (x["swc_name"], x["port_name"], x["mode_group_prototype"]))

    @classmethod
    def __update_sr_com_specs(cls, asw_dict):
        visited_ports = set()
        for _, swc_info in asw_dict.items():
            for _, pport in swc_info["pports"].items():
                cls.__update_sr_pport_info_by_connected_rport(pport, visited_ports)

    @classmethod
    def __find_sr_opposite_asw_ports(cls, asw_dict):
        for _, swc_info in asw_dict.items():
            for _, pport in swc_info["pports"].items():
                cls.__find_curr_sr_opposite_asw_ports(pport, cls.p_connections, cls.sr_r_port_path_to_asw_port_dict)
            for _, rport in swc_info["rports"].items():
                cls.__find_curr_sr_opposite_asw_ports(rport, cls.r_connections, cls.sr_p_port_path_to_asw_port_dict)

    @classmethod
    def __find_curr_sr_opposite_asw_ports(cls, curr_port, connections, port_path_to_asw_port_dict):
        if ("port_interface_type" not in curr_port) or curr_port["port_interface_type"] != "sr":
            return
        curr_path = curr_port["port_path"]
        data_name = curr_port["data_name"]
        curr_port["conn_asw_ports"] = []
        if curr_path not in connections:
            return
        for opposite_path in connections[curr_path]:
            if opposite_path not in port_path_to_asw_port_dict:
                continue
            opposite_access_ports = port_path_to_asw_port_dict[opposite_path]
            if data_name not in opposite_access_ports:
                continue
            curr_port["conn_asw_ports"].extend(opposite_access_ports[data_name].values())

    # @classmethod
    # def __update_sr_pport_info_by_connected_rport(cls, pport):
    #     if pport['type'] not in ['Explicit Sender', 'Implicit Sender']:
    #         return
    #     enable_update = []
    #     for conn_port in pport['conn_asw_ports']:
    #         # update enable_update flag
    #         if conn_port['type'] == 'Explicit Receiver' and conn_port['enable_update']:
    #             enable_update.append(f'Rte_RxUpdate_{conn_port["component"]}_{conn_port["name"]}')
    #         enable_update.sort(key=lambda x: (len(x), x.lower()))
    #         # TODO: update queue_size
    #     pport['enable_update'] = enable_update  # attr has the same name with rport

    @classmethod
    def __update_sr_pport_info_by_connected_rport(cls, asw_port, visited_ports):
        if ("port_interface_type" not in asw_port) or asw_port["port_interface_type"] != "sr":
            return
        if asw_port["m_to_n"] == "0":
            return

        if asw_port["port_full_key"] in visited_ports:
            return
        all_non_q_participant_ports = asw_port["sr_port_group"]
        visited_ports.update(port["port_full_key"] for port in all_non_q_participant_ports)

        if asw_port["type"] not in {"Explicit Sender", "Implicit Sender"}:
            return

        p_ports = []
        r_ports = []
        enable_update = []
        for port in all_non_q_participant_ports:
            if port["is_p"]:
                p_ports.append(port)
            else:
                r_ports.append(port)
                if port["type"] == "Explicit Receiver" and port["enable_update"]:
                    # update enable_update flag
                    enable_update.append(f'Rte_RxUpdate_{port["component"]}_{port["name"]}')
        enable_update.sort(key=lambda x: (len(x), x.lower()))
        for port in p_ports:
            port["enable_update"] = enable_update
        for port in r_ports:
            if port["type"] == "Explicit Receiver" and port["enable_update"]:
                access_ports = p_ports + [port]
                port["enable_update_memmap_category"] = cls.__get_memmap_category(access_ports, access_ports)

    @classmethod
    def __process_all_tasks(cls, all_entities, key_attribute):
        highest_task_priority = 0
        entity_to_task_info_dict = {}
        for entity in all_entities:
            curr_entity_tasks = []
            for task in entity["task"]:
                highest_task_priority = cls.__process_task_priority(highest_task_priority, curr_entity_tasks, task)
            entity_to_task_info_dict[entity[key_attribute]] = curr_entity_tasks
        return entity_to_task_info_dict, highest_task_priority

    @classmethod
    def __process_task_priority(cls, highest_task_priority, curr_port_tasks, task):
        task_info = cls.task_mappings.get(task, {})
        if not task_info:
            return 0
        curr_priority = int(task_info["task_priority"])
        curr_preemptive = task_info["task_schedule"] == "FULL"
        curr_port_tasks.append((curr_priority, curr_preemptive))
        if curr_priority > highest_task_priority:
            highest_task_priority = curr_priority
        return highest_task_priority

    @classmethod
    def __update_sr_queue_lock_1n(cls, all_non_q_participant_ports):
        p_port = {}
        for port in all_non_q_participant_ports:
            if port["is_p"]:
                p_port = port
                break
        p_port["q_lock"] = {}
        p_port["q_spinlock_cfg"] = {}
        p_core_id = p_port["core_id"]
        for port in all_non_q_participant_ports:
            if port["is_p"]:
                continue
            if port["core_id"] != p_core_id:
                spinlock_cfg = {
                    "lock_id": (f'OS_SPINLOCK_Rte_{port["swc_port_var"]}_ID').upper(),
                    "access_osa": [p_port["osapplication"], port["osapplication"]],
                    "lock_metohd": "LOCK_CAT2_INTERRUPTS",
                    "is_rw": False,
                }
                port["q_lock"] = "SPINLOCK"
                port["q_spinlock_cfg"] = spinlock_cfg
                p_port["q_lock"][port["swc_port_var"]] = "SPINLOCK"
                p_port["q_spinlock_cfg"][port["swc_port_var"]] = spinlock_cfg
            else:
                port["q_lock"] = "OSISR"
                p_port["q_lock"][port["swc_port_var"]] = "OSISR"

                # optimization based on same task execution
                if (
                    p_port["task"]
                    and len(set(p_port["task"])) == 1
                    and len(set(port["task"])) == 1
                    and p_port["task"][0] == port["task"][0]
                ):
                    port["q_lock"] = "NONE"
                    p_port["q_lock"][port["swc_port_var"]] = "NONE"
                    continue

                # os interrupt lock based on task scheduling
                if cls.is_ea_opt_enabled:
                    has_isr_lock = False
                    curr_q_ports = [p_port, port]
                    port_to_task_info_dict, highest_task_priority = cls.__process_all_tasks(
                        curr_q_ports, "port_full_key"
                    )
                    for curr_p in curr_q_ports:
                        for task_info in port_to_task_info_dict[curr_p["port_full_key"]]:
                            if task_info[0] < highest_task_priority and task_info[1]:
                                has_isr_lock = True
                                break
                        if has_isr_lock:
                            break
                    if not has_isr_lock:
                        port["q_lock"] = "NONE"
                        p_port["q_lock"][port["swc_port_var"]] = "NONE"

    @classmethod
    def __update_sr_queue_lock_11_n1(cls, asw_port, all_q_participant_ports):
        r_port = {}
        for port in all_q_participant_ports:
            if not port["is_p"]:
                r_port = port
                break

        # check if inter core
        curr_core_id = asw_port["core_id"]
        has_inter_core = False
        for port in all_q_participant_ports:
            if port == asw_port:
                continue
            if curr_core_id != port["core_id"]:
                has_inter_core = True
                break
        if has_inter_core:
            spinlock_cfg = {
                "lock_id": (f'OS_SPINLOCK_Rte_{r_port["swc_port_var"]}_ID').upper(),
                "access_osa": sorted(
                    list(set([p["osapplication"] for p in all_q_participant_ports if p["osapplication"]]))
                ),
                "lock_metohd": "LOCK_CAT2_INTERRUPTS",
                "is_rw": False,
            }
            for port in all_q_participant_ports:
                if port["is_p"]:
                    port["q_lock"] = {r_port["swc_port_var"]: "SPINLOCK"}
                    port["q_spinlock_cfg"] = {r_port["swc_port_var"]: spinlock_cfg}
                else:
                    port["q_lock"] = "SPINLOCK"
                    port["q_spinlock_cfg"] = spinlock_cfg
            return

        for port in all_q_participant_ports:
            for port in all_q_participant_ports:
                if port["is_p"]:
                    port["q_lock"] = {r_port["swc_port_var"]: "OSISR"}
                else:
                    port["q_lock"] = "OSISR"

        # optimization based on same task execution
        if asw_port["task"] and len(set(asw_port["task"])) == 1:
            curr_task = asw_port["task"][0]
            has_multi_task = False
            for port in all_q_participant_ports:
                if port == asw_port:
                    continue
                if len(set(port["task"])) != 1 or curr_task != port["task"][0]:
                    has_multi_task = True
                    break
            if not has_multi_task:
                for port in all_q_participant_ports:
                    if port["is_p"]:
                        port["q_lock"][r_port["swc_port_var"]] = "NONE"
                    else:
                        port["q_lock"] = "NONE"
                return

        # os interrupt lock based on task scheduling
        if cls.is_ea_opt_enabled:
            has_isr_lock = False
            port_to_task_info_dict, highest_task_priority = cls.__process_all_tasks(
                all_q_participant_ports, "port_full_key"
            )
            for port in all_q_participant_ports:
                for task_info in port_to_task_info_dict[port["port_full_key"]]:
                    if task_info[0] < highest_task_priority and task_info[1]:
                        has_isr_lock = True
                        break
                if has_isr_lock:
                    break
            if not has_isr_lock:
                for port in all_q_participant_ports:
                    if port["is_p"]:
                        port["q_lock"][r_port["swc_port_var"]] = "NONE"
                    else:
                        port["q_lock"] = "NONE"
                return

    @classmethod
    def __update_sr_queue_ioc_type(cls, asw_port):
        all_non_q_participant_ports = asw_port["sr_port_group"]

        if asw_port["m_to_n"] == "1n":
            p_port = {}
            for port in all_non_q_participant_ports:
                if port["is_p"]:
                    p_port = port
                    break
            p_port["q_ioc_type"] = {}
            p_core_id = p_port["core_id"]
            p_osa = p_port["osapplication"]
            for port in all_non_q_participant_ports:
                if port["is_p"]:
                    continue
                q_ioc_type = cls.__check_if_cross_core_or_partition_between_two_ports(
                    p_core_id, p_osa, port["core_id"], port["osapplication"]
                )
                port["q_ioc_type"] = q_ioc_type
                p_port["q_ioc_type"][port["swc_port_var"]] = q_ioc_type
        else:
            r_port = {}
            for port in all_non_q_participant_ports:
                if not port["is_p"]:
                    r_port = port
                    break
            r_core_id = r_port["core_id"]
            r_osa = r_port["osapplication"]
            q_ioc_type = "NONE"
            for port in all_non_q_participant_ports:
                if not port["is_p"]:
                    continue
                curr_ioc_type = cls.__check_if_cross_core_or_partition_between_two_ports(
                    r_core_id, r_osa, port["core_id"], port["osapplication"]
                )
                if curr_ioc_type == "SPINLOCK":
                    q_ioc_type = "SPINLOCK"
                    break
                elif curr_ioc_type == "OSISR":
                    q_ioc_type = "OSISR"
            for port in all_non_q_participant_ports:
                if port["is_p"]:
                    port["q_ioc_type"] = {r_port["swc_port_var"]: q_ioc_type}
            r_port["q_ioc_type"] = q_ioc_type

    @classmethod
    def __update_sr_queue_lock(cls, asw_port):
        all_q_participant_ports = asw_port["sr_port_group"]
        if asw_port["m_to_n"] == "1n":
            cls.__update_sr_queue_lock_1n(all_q_participant_ports)
        else:
            cls.__update_sr_queue_lock_11_n1(asw_port, all_q_participant_ports)

    @classmethod
    def __parse_sr_non_q_spinlock(cls, port, all_non_q_participant_ports):
        spinlock_cfg = {
            "lock_id": None,
            "access_osa": [],
            "lock_metohd": "LOCK_CAT2_INTERRUPTS",
            "is_rw": False,
        }
        if port["m_to_n"] in {"11", "1n", "mn"}:
            if port["is_p"]:
                p_port = port
            else:
                for curr_port in all_non_q_participant_ports:
                    if curr_port["is_p"]:
                        p_port = curr_port
                        break
            spinlock_cfg["lock_id"] = (f"OS_SPINLOCK_Rte_{p_port['swc_port_var']}_ID").upper()
            spinlock_cfg["access_osa"] = sorted(
                list(set([p["osapplication"] for p in all_non_q_participant_ports if p["osapplication"]]))
            )
            if port["m_to_n"] in {"1n", "mn"}:
                spinlock_cfg["is_rw"] = True
        elif port["m_to_n"] == "n1":
            if not port["is_p"]:
                r_port = port
            else:
                for curr_port in all_non_q_participant_ports:
                    if curr_port["is_p"]:
                        r_port = curr_port
                        break
            spinlock_cfg["lock_id"] = (f"OS_SPINLOCK_Rte_{r_port['swc_port_var']}_ID").upper()
            spinlock_cfg["access_osa"] = sorted(
                list(set([p["osapplication"] for p in all_non_q_participant_ports if p["osapplication"]]))
            )
        return spinlock_cfg

    @classmethod
    def __parse_sr_lock_nonqueue(cls, asw_port, visited_ports):
        if not cls.__is_sr_nonq_port(asw_port):
            return
        if asw_port["m_to_n"] == "0":
            return
        if not asw_port["has_prport"] and asw_port["m_to_n"] == "mn":
            return
        if asw_port["port_full_key"] in visited_ports:
            return
        all_non_q_participant_ports = asw_port["sr_port_group"]
        visited_ports.update(port["port_full_key"] for port in all_non_q_participant_ports)

        # check if inter osa
        curr_core_id = asw_port["core_id"]
        curr_osa = asw_port["osapplication"]
        has_inter_core = False
        has_inter_osa = False
        for port in all_non_q_participant_ports:
            if port == asw_port:
                continue
            if curr_core_id != port["core_id"]:
                has_inter_core = True
                break
            if curr_osa != port["osapplication"]:
                has_inter_osa = True

        intra_osa = True if not has_inter_core and not has_inter_osa else False
        for port in all_non_q_participant_ports:
            port["intra_osa"] = intra_osa

        # optimization based on datatype
        # exclud N:1 scen: as N:1 operations are NOT atomic
        datatype = asw_port["arg"]["datatype"]
        is_data_type_free_from_lock = (
            datatype["native_category"] == "NUMERICAL" and datatype["basetype"] in cls.AUTOMIC_DATATYPES
        )
        if (
            (asw_port["m_to_n"] != "n1" or (asw_port["m_to_n"] == "n1" and asw_port["single_rec_buff_for_n1"]))
            and is_data_type_free_from_lock
            and (("enable_update" not in asw_port) or (not asw_port["enable_update"]))
        ):
            for port in all_non_q_participant_ports:
                port["lock"] = "NONE"
            return

        if has_inter_core:
            spinlock_cfg = cls.__parse_sr_non_q_spinlock(port, all_non_q_participant_ports)
            for port in all_non_q_participant_ports:
                port["lock"] = "SPINLOCK"
                port["spinlock_cfg"] = spinlock_cfg
            return

        # optimization based on same task execution
        if asw_port["task"] and len(set(asw_port["task"])) == 1:
            curr_task = asw_port["task"][0]
            has_multi_task = False
            for port in all_non_q_participant_ports:
                if port == asw_port:
                    continue
                if len(set(port["task"])) != 1 or curr_task != port["task"][0]:
                    has_multi_task = True
                    break
            if not has_multi_task:
                for port in all_non_q_participant_ports:
                    port["lock"] = "NONE"
                return

        # os interrupt lock based on task scheduling
        if asw_port["m_to_n"] != "mn" and cls.is_ea_opt_enabled:
            port_to_task_info_dict, highest_task_priority = cls.__process_all_tasks(
                all_non_q_participant_ports, "port_full_key"
            )
            for port in all_non_q_participant_ports:
                curr_port_lock = "NONE"
                for task_info in port_to_task_info_dict[port["port_full_key"]]:
                    if task_info[0] < highest_task_priority and task_info[1]:
                        curr_port_lock = "OSISR"
                        break
                port["lock"] = curr_port_lock
            return
        else:
            for port in all_non_q_participant_ports:
                port["lock"] = "OSISR"
            return

    @classmethod
    def __is_sr_nonq_port(cls, asw_port) -> bool:
        if ("port_interface_type" not in asw_port) or asw_port["port_interface_type"] != "sr":
            return False
        if asw_port["is_queued"]:
            return False
        return True

    @classmethod
    def __update_sr_port_init_value(cls, asw_dict):
        visited = set()
        for swc in asw_dict.values():
            for p_port in swc["pports"].values():
                if p_port.get("port_interface_type", None) != "sr":
                    continue
                if p_port["port_full_key"] in visited:
                    continue
                if p_port["m_to_n"] == "0":
                    iv = cls.__default_init_value(p_port)
                    init_value_str, is_zero_init, is_bool = cls.get_sr_var_init_value(p_port["arg"]["datatype"], iv)
                    p_port["arg"]["init_value"] = iv
                    p_port["arg"]["init_value"]["init_value_str"] = init_value_str
                    p_port["arg"]["init_value"]["is_zero_init"] = is_zero_init
                    p_port["arg"]["init_value"]["is_bool"] = is_bool
                    p_port["arg"]["init_value"]["init_category"] = (
                        VariableInitCategory.ZERO_INIT if is_zero_init else VariableInitCategory.INIT
                    )
                    continue
                visited.update(port["port_full_key"] for port in p_port["sr_port_group"])

                r_port_has_init_value = False
                r_port_init_value = {}
                p_port_has_init_value = False
                p_port_init_value = {}
                iv_port = {}
                for port in p_port["sr_port_group"]:
                    if port["is_p"]:
                        if p_port_has_init_value:
                            continue
                        if not port["arg"]["init_value"]:
                            continue
                        p_port_has_init_value = True
                        p_port_init_value = port["arg"]["init_value"]
                        iv_port = port
                    else:
                        if r_port_has_init_value:
                            continue
                        if not port["arg"]["init_value"]:
                            continue
                        r_port_has_init_value = True
                        r_port_init_value = port["arg"]["init_value"]
                        iv_port = port

                if r_port_has_init_value:
                    init_value_str, is_zero_init, is_bool = cls.get_sr_var_init_value(
                        iv_port["arg"]["datatype"], r_port_init_value
                    )
                    for port in p_port["sr_port_group"]:
                        port["arg"]["init_value"] = r_port_init_value
                        port["arg"]["init_value"]["name"] = cls.__get_init_value_name(port)
                        port["arg"]["init_value"]["value"]["name"] = cls.__get_init_value_name(port)
                        port["arg"]["init_value"]["init_value_str"] = init_value_str
                        port["arg"]["init_value"]["is_zero_init"] = is_zero_init
                        port["arg"]["init_value"]["is_bool"] = is_bool
                        port["arg"]["init_value"]["init_category"] = (
                            VariableInitCategory.ZERO_INIT if is_zero_init else VariableInitCategory.INIT
                        )
                elif p_port_has_init_value:
                    init_value_str, is_zero_init, is_bool = cls.get_sr_var_init_value(
                        iv_port["arg"]["datatype"], p_port_init_value
                    )
                    for port in p_port["sr_port_group"]:
                        port["arg"]["init_value"] = p_port_init_value
                        port["arg"]["init_value"]["name"] = cls.__get_init_value_name(port)
                        port["arg"]["init_value"]["value"]["name"] = cls.__get_init_value_name(port)
                        port["arg"]["init_value"]["init_value_str"] = init_value_str
                        port["arg"]["init_value"]["is_zero_init"] = is_zero_init
                        port["arg"]["init_value"]["is_bool"] = is_bool
                        port["arg"]["init_value"]["init_category"] = (
                            VariableInitCategory.ZERO_INIT if is_zero_init else VariableInitCategory.INIT
                        )
                else:
                    iv = cls.__default_init_value(p_port)
                    init_value_str, is_zero_init, is_bool = cls.get_sr_var_init_value(p_port["arg"]["datatype"], iv)
                    for port in p_port["sr_port_group"]:
                        port["arg"]["init_value"] = iv
                        port["arg"]["init_value"]["init_value_str"] = init_value_str
                        port["arg"]["init_value"]["is_zero_init"] = is_zero_init
                        port["arg"]["init_value"]["is_bool"] = is_bool
                        port["arg"]["init_value"]["init_category"] = (
                            VariableInitCategory.ZERO_INIT if is_zero_init else VariableInitCategory.INIT
                        )

        for swc in asw_dict.values():
            for r_port in swc["rports"].values():
                if r_port.get("port_interface_type", None) != "sr":
                    continue
                if r_port["port_full_key"] in visited:
                    continue
                if (not r_port["arg"]["init_value"]) and r_port["m_to_n"] == "0":
                    iv = cls.__default_init_value(r_port)
                    init_value_str, is_zero_init, is_bool = cls.get_sr_var_init_value(r_port["arg"]["datatype"], iv)
                    r_port["arg"]["init_value"] = iv
                    r_port["arg"]["init_value"]["init_value_str"] = init_value_str
                    r_port["arg"]["init_value"]["is_zero_init"] = is_zero_init
                    r_port["arg"]["init_value"]["is_bool"] = is_bool
                    r_port["arg"]["init_value"]["init_category"] = (
                        VariableInitCategory.ZERO_INIT if is_zero_init else VariableInitCategory.INIT
                    )
                else:
                    init_value_str, is_zero_init, is_bool = cls.get_sr_var_init_value(
                        r_port["arg"]["datatype"], r_port["arg"]["init_value"]
                    )
                    r_port["arg"]["init_value"]["name"] = cls.__get_init_value_name(r_port)
                    r_port["arg"]["init_value"]["value"]["name"] = cls.__get_init_value_name(r_port)
                    r_port["arg"]["init_value"]["init_value_str"] = init_value_str
                    r_port["arg"]["init_value"]["is_zero_init"] = is_zero_init
                    r_port["arg"]["init_value"]["is_bool"] = is_bool
                    r_port["arg"]["init_value"]["init_category"] = (
                        VariableInitCategory.ZERO_INIT if is_zero_init else VariableInitCategory.INIT
                    )

    @classmethod
    def __default_init_value(cls, port):
        init_value = port["arg"]["init_value"]
        data_type = port["arg"]["datatype"]
        init_value.update({"category": data_type["native_category"]})
        init_value.update({"name": cls.__get_init_value_name(port)})
        init_value.update({"value": {}})
        arg_base_type = cls.get_arg_base_type(data_type["name"])
        value = cls.__parse_default_init_value(arg_base_type)
        init_value["value"].update({"datatype": data_type["name"]})
        init_value["value"].update({"name": data_type["name"]})
        init_value["value"].update({"value": value})
        return init_value

    @classmethod
    def __parse_default_init_value(cls, arg_base_type):
        if not arg_base_type:
            return 0
        if type(arg_base_type) is str:
            values = None
            values = cls.__default_numerical_init_value(arg_base_type)
        elif type(arg_base_type) is list:
            values = {}
            values = cls.__default_array_init_value(arg_base_type)
        elif type(arg_base_type) is dict:
            values = {}
            values = cls.__default_struct_init_value(arg_base_type)
        return values

    @classmethod
    def __default_numerical_init_value(cls, arg_base_type):
        value = cls.__data_type_convert("0", arg_base_type)
        return value

    @classmethod
    def __default_array_init_value(cls, arg_base_type):
        values = {}
        for ind, value_base_type in enumerate(arg_base_type):
            if type(value_base_type) is str:
                values.update({ind: cls.__default_numerical_init_value(value_base_type)})
            elif type(value_base_type) is list:
                values.update({ind: cls.__default_array_init_value(value_base_type)})
            elif type(value_base_type) is dict:
                values.update({ind: cls.__default_struct_init_value(value_base_type)})
        return values

    @classmethod
    def __default_struct_init_value(cls, arg_base_type):
        values = {}
        for key, value_base_type in arg_base_type.items():
            if type(value_base_type) is str:
                values.update({key: cls.__default_numerical_init_value(value_base_type)})
            elif type(value_base_type) is list:
                values.update({key: cls.__default_array_init_value(value_base_type)})
            elif type(value_base_type) is dict:
                values.update({key: cls.__default_struct_init_value(value_base_type)})
        return values

    @classmethod
    def __get_init_value_name(cls, port):
        init_value_name = None
        if port["arg"]["datatype"]["native_category"] in ["ARRAY", "STRUCTURE", "UNION"]:
            if port["is_p"]:
                # pport
                if port["conn_asw_ports"]:
                    if port["m_to_n"] in {"11", "1n"}:
                        # 用pport的名字
                        init_value_name = (
                            f"Rte_C_{port['arg']['datatype']['name']}_"
                            f"{port['component']}_{port['port_prototype']}_{port['data_element']}"
                        )
                    elif port["m_to_n"] == "n1":
                        init_value_name = (
                            f"Rte_C_{port['arg']['datatype']['name']}_"
                            f"{port['conn_asw_ports'][0]['component']}_{port['conn_asw_ports'][0]['name']}"
                        )
                    elif port["m_to_n"] == "mn":
                        fst_port = port["sr_port_group"][0]
                        init_value_name = f"Rte_C_{fst_port['arg']['datatype']['name']}_{fst_port['swc_port_var']}"
                    else:
                        pass
                else:
                    # 未连接时，用当前port的信息
                    init_value_name = (
                        f"Rte_C_{port['arg']['datatype']['name']}_"
                        f"{port['component']}_{port['port_prototype']}_{port['data_element']}"
                    )
            else:
                # rport
                if port["conn_asw_ports"]:
                    if port["m_to_n"] in {"11", "1n"}:
                        # 用pport的名字
                        init_value_name = (
                            f"Rte_C_{port['arg']['datatype']['name']}_"
                            f"{port['conn_asw_ports'][0]['component']}_{port['conn_asw_ports'][0]['name']}"
                        )
                    elif port["m_to_n"] == "n1":
                        init_value_name = (
                            f"Rte_C_{port['arg']['datatype']['name']}_"
                            f"{port['component']}_{port['port_prototype']}_{port['data_element']}"
                        )
                    elif port["m_to_n"] == "mn":
                        fst_port = port["sr_port_group"][0]
                        init_value_name = f"Rte_C_{fst_port['arg']['datatype']['name']}_{fst_port['swc_port_var']}"
                    else:
                        # TODO
                        pass
                else:
                    init_value_name = (
                        f"Rte_C_{port['arg']['datatype']['name']}_"
                        f"{port['component']}_{port['port_prototype']}_{port['data_element']}"
                    )
        else:
            # 不是array/struct/union，就直接用datatype名字
            init_value_name = port["arg"]["datatype"]["name"]
        return init_value_name

    @classmethod
    def get_basetype_size_byte(cls, basetype):
        return cls.NATIVE_DATATYPES_SIZE[basetype] if basetype in cls.NATIVE_DATATYPES_SIZE else 0

    @classmethod
    def __parse_idt_member_info(cls, ar_idt, index, is_parent_arr=False):
        member = {
            "name": utils.get_short_name(ar_idt),
            # user typed means "datatype" (RTE IDT) is defined
            "is_user_typed": False,
            "datatype": "",
            "category": None,
            "is_array": False,
            "typesize_byte_for_struct_align": 0,
            "mem_dep": None,
            "mem_nature_order": index,
        }
        member_category = ar_idt.CATEGORY.valueOf_
        if (
            member_category == "TYPE_REFERENCE"
            and ar_idt.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[
                0
            ].IMPLEMENTATION_DATA_TYPE_REF
        ):
            member_path = ar_idt.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[
                0
            ].IMPLEMENTATION_DATA_TYPE_REF.valueOf_
            member_ar_idt = ar_idt.find(member_path)
            if not member_ar_idt:
                raise Exception(f"Can not find {utils.get_short_name(member_ar_idt)} in arxml file")
            member["datatype"] = utils.get_short_name(member_ar_idt)
            member["category"] = utils.get_valueOf(member_ar_idt.CATEGORY)
            mem_idt, member["mem_dep"] = cls.parse_idt_and_dependency(member_ar_idt)
            member["typesize_byte_for_struct_align"] = mem_idt["typesize_byte_for_struct_align"]
            if "is_array" in mem_idt and mem_idt["is_array"]:
                member["is_array"] = mem_idt["is_array"]
                member["arr_basetype"] = mem_idt["arr_basetype"]
        elif (
            member_category == "VALUE"
            and ar_idt.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[0].BASE_TYPE_REF
        ):
            member_path = ar_idt.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[
                0
            ].BASE_TYPE_REF.valueOf_
            member_basetype = ar_idt.find(member_path)
            if not member_basetype:
                raise Exception(f"Can not find {utils.get_short_name(member_basetype)} in arxml file")
            member["category"] = member_category
            member["datatype"] = utils.get_short_name(member_basetype)
            member["typesize_byte_for_struct_align"] = cls.get_basetype_size_byte(member["datatype"])
        elif member_category == "ARRAY" and not is_parent_arr:
            if not ar_idt.SUB_ELEMENTS:
                raise Exception(f"Elememt of {utils.get_short_name(ar_idt)} does not exist!")
            ar_idt_sub_ele = ar_idt.SUB_ELEMENTS.IMPLEMENTATION_DATA_TYPE_ELEMENT[0]
            arr_sub_mem_idt = cls.__parse_idt_member_info(ar_idt_sub_ele, 0, True)
            member["category"] = member_category
            member["is_user_typed"] = True
            member["is_array"] = True
            # no RTE defined type
            member["basetype"] = arr_sub_mem_idt["datatype"]
            member["arr_basetype"] = (
                arr_sub_mem_idt["arr_basetype"]
                if ("is_array" in arr_sub_mem_idt and arr_sub_mem_idt["is_array"])
                else arr_sub_mem_idt["datatype"]
            )
            member["size"] = int(ar_idt_sub_ele.ARRAY_SIZE.valueOf_)
            member.update({"typesize_byte_for_struct_align": arr_sub_mem_idt["typesize_byte_for_struct_align"]})
            if arr_sub_mem_idt["mem_dep"]:
                member["mem_dep"] = arr_sub_mem_idt["mem_dep"]
        else:
            raise Exception(f"Can not parse IDT {utils.get_short_name(ar_idt)} yet!")
        return member

    @classmethod
    def parse_idt_category_value(cls, ar_idt):
        idt = {"name": utils.get_short_name(ar_idt), "category": "TYPE_REFERENCE", "native_category": "NUMERICAL"}
        idt_dependency = {utils.get_short_name(ar_idt): []}
        ref_basetype_path = utils.get_valueOf(
            ar_idt.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[0].BASE_TYPE_REF
        )
        ar_basetype = ar_idt.find(ref_basetype_path)
        if not ar_basetype:
            raise Exception(f"Can not find {ref_basetype_path} in arxml file")
        if ar_basetype.CATEGORY.valueOf_ != "FIXED_LENGTH":
            raise Exception(f"Datatype {utils.get_short_name(ar_basetype)} with nnfixed length is not yet supported!")
        basetype = (
            utils.get_short_name(ar_basetype)
            if utils.get_short_name(ar_basetype) in cls.NATIVE_DATATYPES
            else ar_basetype.NATIVE_DECLARATION.valueOf_
        )
        idt["typedef_type"] = basetype
        idt["basetype"] = basetype
        idt_dependency[utils.get_short_name(ar_idt)].append(idt["typedef_type"])
        idt.update({"typesize_byte_for_struct_align": cls.get_basetype_size_byte(basetype)})
        cls.datatype_path_to_idt_mapping.update({ar_idt.get_path(): {"idt": idt, "idt_dependency": idt_dependency}})
        return idt, idt_dependency

    @classmethod
    def parse_idt_category_type_reference(cls, ar_idt):
        idt = {"name": utils.get_short_name(ar_idt), "category": "TYPE_REFERENCE"}
        idt_dependency = {utils.get_short_name(ar_idt): []}
        ref_idt_name = ar_idt.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[
            0
        ].IMPLEMENTATION_DATA_TYPE_REF.valueOf_
        referenced_idt = ar_idt.find(ref_idt_name)
        if not referenced_idt:
            raise Exception(f"Can not find {ref_idt_name} in arxml file")
        last_ref_idt, _ = cls.parse_idt_and_dependency(referenced_idt)
        idt["typedef_type"] = utils.get_short_name(referenced_idt)
        idt_dependency[utils.get_short_name(ar_idt)].append(idt["typedef_type"])
        idt.update({"typesize_byte_for_struct_align": last_ref_idt["typesize_byte_for_struct_align"]})
        if last_ref_idt["category"] == "TYPE_REFERENCE":
            idt["native_category"] = "NUMERICAL"
            idt["basetype"] = last_ref_idt["typedef_type"]
        elif last_ref_idt["category"] == "ARRAY":
            idt["native_category"] = "ARRAY"
            idt["basetype"] = last_ref_idt["basetype"]
            idt["size"] = last_ref_idt["size"]
        elif last_ref_idt["category"] in ["STRUCTURE", "UNION"]:
            idt["native_category"] = last_ref_idt["category"]
            idt["members"] = last_ref_idt["members"]
        else:
            pass
        if "is_array" in last_ref_idt and last_ref_idt["is_array"]:
            idt["is_array"] = True
            idt["arr_basetype"] = last_ref_idt["arr_basetype"]
        return idt, idt_dependency

    @classmethod
    def parse_idt_category_data_reference(cls, ar_idt):
        idt = {
            "name": utils.get_short_name(ar_idt),
            "category": "DATA_REFERENCE",
            "typesize_byte_for_struct_align": 4,
            "native_category": "DATA_REFERENCE",
        }
        idt_dependency = {utils.get_short_name(ar_idt): []}
        sw_pointer_target_props = ar_idt.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[
            0
        ].SW_POINTER_TARGET_PROPS
        if not sw_pointer_target_props:
            raise Exception(f"Can not find {utils.get_short_name(ar_idt)} in arxml file")
        target_category = sw_pointer_target_props.TARGET_CATEGORY
        sw_data_def_props = sw_pointer_target_props.SW_DATA_DEF_PROPS
        sw_impl_policy = ""
        if sw_data_def_props.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[0].SW_IMPL_POLICY:
            sw_impl_policy = sw_data_def_props.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[
                0
            ].SW_IMPL_POLICY.valueOf_
        ref_idt = None
        if target_category.valueOf_ == "VALUE":
            ref_idt, _ = cls.parse_idt_category_value(sw_pointer_target_props)
        elif target_category.valueOf_ == "TYPE_REFERENCE":
            ref_idt, _ = cls.parse_idt_category_type_reference(sw_pointer_target_props)
        else:
            raise Exception(f"Can not parse {target_category.valueOf_} TARGET_CATEGORY of SW-POINTER-TARGET-PROPS")
        idt.update(
            {
                # NOTE: # the sw_pointer_target_props's name is None parsed by parse_idt_category_type_reference
                "typedef_type": ref_idt["typedef_type"],
                "sw_impl_policy": f"{sw_impl_policy.lower()} " if sw_impl_policy else "",
                "is_pointer": "True",
            }
        )
        idt_dependency[utils.get_short_name(ar_idt)].append(idt["typedef_type"])
        return idt, idt_dependency

    @classmethod
    def parse_idt_category_array(cls, ar_idt):
        idt = {
            "name": utils.get_short_name(ar_idt),
            "category": "ARRAY",
            "basetype": "",
            "arr_basetype": "",
            "is_array": True,
            "size": 0,
            "native_category": "ARRAY",
        }
        idt_dependency = {utils.get_short_name(ar_idt): []}
        if not ar_idt.SUB_ELEMENTS:
            raise Exception(f"Elememt of {utils.get_short_name(ar_idt)} does not exist!")
        member = ar_idt.SUB_ELEMENTS.IMPLEMENTATION_DATA_TYPE_ELEMENT[0]
        member_idt = cls.__parse_idt_member_info(member, 0)
        idt["basetype"] = member_idt["datatype"]
        idt["arr_basetype"] = (
            member_idt["arr_basetype"]
            if ("is_array" in member_idt and member_idt["is_array"])
            else member_idt["datatype"]
        )
        idt["size"] = int(member.ARRAY_SIZE.valueOf_)
        idt.update({"typesize_byte_for_struct_align": member_idt["typesize_byte_for_struct_align"]})
        idt_dependency[utils.get_short_name(ar_idt)].append(idt["basetype"])
        if member_idt["mem_dep"]:
            if member_idt["is_user_typed"]:
                idt_dependency[utils.get_short_name(ar_idt)].extend(member_idt["mem_dep"][member_idt["arr_basetype"]])
            else:
                idt_dependency[utils.get_short_name(ar_idt)].extend(member_idt["mem_dep"][member_idt["datatype"]])
        return idt, idt_dependency

    @classmethod
    def parse_idt_category_structure(cls, ar_idt):
        idt = {
            "name": utils.get_short_name(ar_idt),
            "category": "STRUCTURE",
            "members": [],
            "typesize_byte_for_struct_align": 4,
            "mem_in_typesize_order_for_align": {8: [], 4: [], 2: [], 1: []},
            "mem_index_in_order": [0] * len(ar_idt.SUB_ELEMENTS.IMPLEMENTATION_DATA_TYPE_ELEMENT),
            "native_category": "STRUCTURE",
        }
        idt_dependency = {utils.get_short_name(ar_idt): []}
        index = 0
        for ar_member in ar_idt.SUB_ELEMENTS.IMPLEMENTATION_DATA_TYPE_ELEMENT:
            member = cls.__parse_idt_member_info(ar_member, index)
            idt["members"].append(member)
            mem_datatype = member["datatype"]
            idt_dependency[utils.get_short_name(ar_idt)].append(mem_datatype)
            if member["mem_dep"]:
                if member["is_user_typed"]:
                    idt_dependency[utils.get_short_name(ar_idt)].extend(member["mem_dep"][member["arr_basetype"]])
                else:
                    idt_dependency[utils.get_short_name(ar_idt)].extend(member["mem_dep"][member["datatype"]])
            curr_mem_typesize_byte_for_struct_align = member["typesize_byte_for_struct_align"]
            idt["mem_in_typesize_order_for_align"][curr_mem_typesize_byte_for_struct_align].append(member)
            index += 1
        index = 0
        for mems in idt["mem_in_typesize_order_for_align"].values():
            for mem in mems:
                idt["mem_index_in_order"][mem["mem_nature_order"]] = index
                index += 1
        return idt, idt_dependency

    @classmethod
    def parse_idt_category_union(cls, ar_idt):
        idt = {
            "name": utils.get_short_name(ar_idt),
            "category": "UNION",
            "members": [],
            "typesize_byte_for_struct_align": 8,
            "native_category": "UNION",
        }
        idt_dependency = {utils.get_short_name(ar_idt): []}
        index = 0
        for ar_member in ar_idt.SUB_ELEMENTS.IMPLEMENTATION_DATA_TYPE_ELEMENT:
            member = cls.__parse_idt_member_info(ar_member, index)
            idt["members"].append(member)
            idt_dependency[utils.get_short_name(ar_idt)].append(member["datatype"])
            if member["mem_dep"]:
                if member["is_user_typed"]:
                    idt_dependency[utils.get_short_name(ar_idt)].extend(member["mem_dep"][member["arr_basetype"]])
                else:
                    idt_dependency[utils.get_short_name(ar_idt)].extend(member["mem_dep"][member["datatype"]])
            index += 1
        return idt, idt_dependency

    @classmethod
    def parse_mode_dclr_group(cls, ar_mode_dclr_group):
        ar_mode_dclr_group_dict = {}
        ar_mode_dclrs = {}
        mode_group_name = utils.get_short_name(ar_mode_dclr_group)
        if not ar_mode_dclr_group.CATEGORY or not ar_mode_dclr_group.CATEGORY.valueOf_:
            # logger.debug(
            #     f"Mode declarations : {utils.get_short_name(ar_mode_dclr_group)} "
            #     "does not have category, handled as ALPHABETIC_ORDER"
            # )
            pass
        category = (
            ar_mode_dclr_group.CATEGORY.valueOf_
            if ar_mode_dclr_group.CATEGORY and ar_mode_dclr_group.CATEGORY.valueOf_
            else "ALPHABETIC_ORDER"
        )
        initial_mode_ref = ar_mode_dclr_group.INITIAL_MODE_REF.valueOf_
        initial_mode_name = utils.get_short_name(ar_mode_dclr_group.find(initial_mode_ref))
        if not initial_mode_name:
            logger.debug(f"can not find initial mode in {ar_mode_dclr_group.get_path()} or wrong path!")
            return {}
        if not ar_mode_dclr_group.MODE_DECLARATIONS or not ar_mode_dclr_group.MODE_DECLARATIONS.MODE_DECLARATION:
            return ar_mode_dclr_group_dict
        for index, ar_mode_dclr in enumerate(ar_mode_dclr_group.MODE_DECLARATIONS.MODE_DECLARATION):
            if category == "EXPLICIT_ORDER":
                value = ar_mode_dclr.VALUE.valueOf_
                ar_mode_dclrs.update({utils.get_short_name(ar_mode_dclr): (index, value)})
            elif category == "ALPHABETIC_ORDER":
                ar_mode_dclrs.update({utils.get_short_name(ar_mode_dclr): (index, index)})
        if initial_mode_name not in ar_mode_dclrs:
            logger.debug(f"invalid initial_mode_name {initial_mode_name}")
            return {}
        initial_mode_value = ar_mode_dclrs[initial_mode_name][1]
        mode_group_len = len(ar_mode_dclr_group.MODE_DECLARATIONS.MODE_DECLARATION)
        if category == "EXPLICIT_ORDER" and not ar_mode_dclr_group.ON_TRANSITION_VALUE:
            # TODO validation
            raise Exception(
                f"The mode declaration group <{mode_group_name}> "
                "does not define the value of the OnTransitionValue attribute although "
                "its mode declarations explicitly specify a value violation of AUTOSAR [constr_1180] "
                "valid up to AR 4.1.3 respectively [constr_1298] valid in AR 4.1.3 or later"
            )
        on_transition_value = (
            mode_group_len if category == "ALPHABETIC_ORDER" else int(ar_mode_dclr_group.ON_TRANSITION_VALUE.valueOf_)
        )
        ar_mode_dclr_group_dict.update(
            {
                "name": mode_group_name,
                "mode_declarations": ar_mode_dclrs,
                "on_tansition_value": on_transition_value,
                "initial_mode": {initial_mode_name: initial_mode_value},
                "mode_group_len": mode_group_len,
                "category": category,
            }
        )
        return ar_mode_dclr_group_dict

    @classmethod
    def __parse_all_data_constraints(cls, ar_asw):
        constrs = {}
        ar_constrs = ar_asw.find_nodes("DATA-CONSTR")
        ar_constrs.sort(key=lambda x: x.get_path())
        for ar_constr in ar_constrs:
            constr_path = ar_constr.get_path()
            if ar_constr.DATA_CONSTR_RULES and ar_constr.DATA_CONSTR_RULES.DATA_CONSTR_RULE:
                if ar_constr.DATA_CONSTR_RULES.DATA_CONSTR_RULE[0].INTERNAL_CONSTRS:
                    # constra中至少需要包含internal_constras/phys_constras中的一种；
                    # 如果有internal_constras，生成代码就用internal_constras；
                    # 如果没有internal_constras，生成代码就用phys_constras
                    constrs.update(
                        {
                            constr_path: {
                                "min": utils.get_valueOf(
                                    ar_constr.DATA_CONSTR_RULES.DATA_CONSTR_RULE[0].INTERNAL_CONSTRS.LOWER_LIMIT
                                ),
                                "max": utils.get_valueOf(
                                    ar_constr.DATA_CONSTR_RULES.DATA_CONSTR_RULE[0].INTERNAL_CONSTRS.UPPER_LIMIT
                                ),
                            }
                        }
                    )
                elif ar_constr.DATA_CONSTR_RULES.DATA_CONSTR_RULE[0].PHYS_CONSTRS:
                    constrs.update(
                        {
                            constr_path: {
                                "min": utils.get_valueOf(
                                    ar_constr.DATA_CONSTR_RULES.DATA_CONSTR_RULE[0].PHYS_CONSTRS.LOWER_LIMIT
                                ),
                                "max": utils.get_valueOf(
                                    ar_constr.DATA_CONSTR_RULES.DATA_CONSTR_RULE[0].PHYS_CONSTRS.UPPER_LIMIT
                                ),
                            }
                        }
                    )
        return constrs

    @classmethod
    def __parse_all_texttable_compu_methods(cls, compu_methods_dict, compu_method_path, compu_method):
        compu_methods_dict.update({compu_method_path: {}})
        compu_methods_dict[compu_method_path].update({"category": "TEXTTABLE", "phy_eq_raw": True, "value": {}})
        for compu_scale in compu_method.COMPU_INTERNAL_TO_PHYS.COMPU_SCALES.COMPU_SCALE:
            lower_limit = utils.get_valueOf(compu_scale.LOWER_LIMIT)
            upper_limit = utils.get_valueOf(compu_scale.UPPER_LIMIT)
            # 标签包括Label/Constant/Symbol, 优先级递增，Label肯定会有，其他的不一定会有
            short_label = utils.get_valueOf(compu_scale.SHORT_LABEL) if compu_scale.SHORT_LABEL else None
            compu_methods_dict[compu_method_path].update({"short_label": short_label})
            constant = (
                utils.get_valueOf(compu_scale.COMPU_CONST.VT)
                if compu_scale.COMPU_CONST and compu_scale.COMPU_CONST.VT
                else None
            )
            compu_methods_dict[compu_method_path].update({"constant": constant})
            symbol = utils.get_valueOf(compu_scale.SYMBOL) if compu_scale.SYMBOL else None
            compu_methods_dict[compu_method_path].update({"symbol": symbol})
            if symbol:
                final_text = symbol
            elif constant:
                final_text = constant
            else:
                final_text = short_label
            if lower_limit and lower_limit == upper_limit:
                compu_methods_dict[compu_method_path]["value"].update({final_text: lower_limit})

    @classmethod
    def __parse_all_identical_compu_methods(cls, compu_methods_dict, compu_method_path, compu_method):
        compu_methods_dict.update({compu_method_path: {}})
        compu_methods_dict[compu_method_path].update(
            {
                "category": "IDENTICAL",
                "phy_eq_raw": True,
                "value": {"denominator": 1, "numerator_offset": 0, "numerator_coeff": 1},
            }
        )

    @classmethod
    def __parse_all_linear_compu_methods(cls, compu_methods_dict, compu_method_path, compu_method):
        compu_methods_dict.update({compu_method_path: {}})
        compu_methods_dict[compu_method_path].update(
            {
                "category": "LINEAR",
                "phy_eq_raw": False,
                "value": {"denominator": None, "numerator_offset": None, "numerator_coeff": None},
            }
        )
        if hasattr(compu_method, "COMPU_INTERNAL_TO_PHYS") and compu_method.COMPU_INTERNAL_TO_PHYS:
            compu_methods_dict[compu_method_path].update({"trans_type": "internal_to_phys"})
            denominator = compu_method.COMPU_INTERNAL_TO_PHYS.COMPU_SCALES.COMPU_SCALE[
                0
            ].COMPU_RATIONAL_COEFFS.COMPU_DENOMINATOR.V
            denom_value = utils.get_valueOf(denominator[0])
            numerator = compu_method.COMPU_INTERNAL_TO_PHYS.COMPU_SCALES.COMPU_SCALE[
                0
            ].COMPU_RATIONAL_COEFFS.COMPU_NUMERATOR.V
            offset = utils.get_valueOf(numerator[0])
            coeff = utils.get_valueOf(numerator[1])
            compu_methods_dict[compu_method_path]["value"]["denominator"] = denom_value
            compu_methods_dict[compu_method_path]["value"]["numerator_offset"] = offset
            compu_methods_dict[compu_method_path]["value"]["numerator_coeff"] = coeff
            compu_methods_dict[compu_method_path]["phy_eq_raw"] = denom_value == "1" and offset == "0" and coeff == "1"
        else:
            # TODO
            pass

    @classmethod
    def __parse_all_scale_linear_and_texttable_compu_methods(cls, compu_methods_dict, compu_method_path, compu_method):
        compu_methods_dict.update({compu_method_path: {}})
        compu_methods_dict[compu_method_path].update(
            {"category": utils.get_valueOf(compu_method.CATEGORY), "phy_eq_raw": False, "value": []}
        )
        if hasattr(compu_method, "COMPU_INTERNAL_TO_PHYS") and compu_method.COMPU_INTERNAL_TO_PHYS:
            compu_methods_dict[compu_method_path].update({"trans_type": "internal_to_phys"})
            for compu_scale in compu_method.COMPU_INTERNAL_TO_PHYS.COMPU_SCALES.COMPU_SCALE:
                lower_limit = utils.get_valueOf(compu_scale.LOWER_LIMIT)
                upper_limit = utils.get_valueOf(compu_scale.UPPER_LIMIT)
                denom_value = None
                offset = None
                coeff = None
                if compu_scale.COMPU_RATIONAL_COEFFS:
                    denom_value = utils.get_valueOf(compu_scale.COMPU_RATIONAL_COEFFS.COMPU_DENOMINATOR.V[0])
                    offset = utils.get_valueOf(compu_scale.COMPU_RATIONAL_COEFFS.COMPU_NUMERATOR.V[0])
                    coeff = utils.get_valueOf(compu_scale.COMPU_RATIONAL_COEFFS.COMPU_NUMERATOR.V[1])
                compu_methods_dict[compu_method_path]["phy_eq_raw"] = (
                    denom_value == "1" and offset == "0" and coeff == "1"
                )
                compu_methods_dict[compu_method_path]["value"].append(
                    {
                        "lower_limit": lower_limit,
                        "upper_limit": upper_limit,
                        "denominator": denom_value,
                        "numerator_offset": offset,
                        "numerator_coeff": coeff,
                    }
                )
        else:
            # TODO
            pass

    @classmethod
    def __parse_all_bitfield_texttable_compu_methods(cls, compu_methods_dict, compu_method_path, compu_method):
        compu_methods_dict.update({compu_method_path: {}})
        compu_methods_dict[compu_method_path].update(
            {"category": "BITFIELD_TEXTTABLE", "phy_eq_raw": True, "value": {}}
        )
        for compu_scale in compu_method.COMPU_INTERNAL_TO_PHYS.COMPU_SCALES.COMPU_SCALE:
            lower_limit = utils.get_valueOf(compu_scale.LOWER_LIMIT)
            upper_limit = utils.get_valueOf(compu_scale.UPPER_LIMIT)
            # 标签包括Label/Constant/Symbol, 优先级递增，Label肯定会有，其他的不一定会有
            short_label = utils.get_valueOf(compu_scale.SHORT_LABEL) if compu_scale.SHORT_LABEL else None
            compu_methods_dict[compu_method_path].update({"short_label": short_label})
            constant = (
                utils.get_valueOf(compu_scale.COMPU_CONST.VT)
                if compu_scale.COMPU_CONST and compu_scale.COMPU_CONST.VT
                else None
            )
            compu_methods_dict[compu_method_path].update({"constant": constant})
            symbol = utils.get_valueOf(compu_scale.SYMBOL) if compu_scale.SYMBOL else None
            compu_methods_dict[compu_method_path].update({"symbol": symbol})
            if symbol:
                final_text = symbol
            elif constant:
                final_text = constant
            else:
                final_text = short_label
            mask = symbol = utils.get_valueOf(compu_scale.MASK) if compu_scale.MASK else None
            if lower_limit and lower_limit == upper_limit:
                compu_methods_dict[compu_method_path]["value"].update({final_text: lower_limit})
                compu_methods_dict[compu_method_path]["value"].update({f"{short_label}_BflMask": mask})
                bit_len = bin(int(lower_limit))[2:].count("1")
                bfl_pos = bin(int(lower_limit))[2:][::-1].index("1") if bit_len == 1 else 0  # 多位为1时，置为0
                compu_methods_dict[compu_method_path]["value"].update({f"{short_label}_BflPn": bfl_pos})
                compu_methods_dict[compu_method_path]["value"].update({f"{short_label}_BflLn": bit_len})

    @classmethod
    def __parse_all_compu_methods(cls, ar_asw):
        compu_methods_dict = {}
        compu_methods = ar_asw.find_nodes("COMPU-METHOD")
        compu_methods.sort(key=lambda x: x.get_path())
        for compu_method in compu_methods:
            compu_method_path = compu_method.get_path()
            if utils.get_valueOf(compu_method.CATEGORY) == "IDENTICAL":
                cls.__parse_all_identical_compu_methods(compu_methods_dict, compu_method_path, compu_method)
            if compu_method.COMPU_INTERNAL_TO_PHYS and compu_method.COMPU_INTERNAL_TO_PHYS.COMPU_SCALES:
                if utils.get_valueOf(compu_method.CATEGORY) == "TEXTTABLE":
                    cls.__parse_all_texttable_compu_methods(compu_methods_dict, compu_method_path, compu_method)
                elif utils.get_valueOf(compu_method.CATEGORY) == "LINEAR":
                    cls.__parse_all_linear_compu_methods(compu_methods_dict, compu_method_path, compu_method)
                elif utils.get_valueOf(compu_method.CATEGORY) in ["SCALE_LINEAR", "SCALE_LINEAR_AND_TEXTTABLE"]:
                    cls.__parse_all_scale_linear_and_texttable_compu_methods(
                        compu_methods_dict, compu_method_path, compu_method
                    )
                elif utils.get_valueOf(compu_method.CATEGORY) == "BITFIELD_TEXTTABLE":
                    cls.__parse_all_bitfield_texttable_compu_methods(
                        compu_methods_dict, compu_method_path, compu_method
                    )
            elif compu_method.COMPU_PHYS_TO_INTERNAL and compu_method.COMPU_PHYS_TO_INTERNAL.COMPU_SCALES:
                # TODO
                pass
        return compu_methods_dict

    @classmethod
    def parse_idt_and_dependency(cls, ar_idt):
        ar_path = ar_idt.get_path()
        if ar_path in cls.datatype_path_to_idt_mapping:
            idt_ele = cls.datatype_path_to_idt_mapping[ar_path]
            return idt_ele["idt"], idt_ele["idt_dependency"]
        idt = {}
        idt_dependency = {}
        if ar_idt.CATEGORY.valueOf_ == "VALUE":
            idt, idt_dependency = cls.parse_idt_category_value(ar_idt)
        elif ar_idt.CATEGORY.valueOf_ == "TYPE_REFERENCE":
            idt, idt_dependency = cls.parse_idt_category_type_reference(ar_idt)
        elif ar_idt.CATEGORY.valueOf_ == "ARRAY":
            idt, idt_dependency = cls.parse_idt_category_array(ar_idt)
        elif ar_idt.CATEGORY.valueOf_ == "STRUCTURE":
            idt, idt_dependency = cls.parse_idt_category_structure(ar_idt)
        elif ar_idt.CATEGORY.valueOf_ == "DATA_REFERENCE":
            idt, idt_dependency = cls.parse_idt_category_data_reference(ar_idt)
        elif ar_idt.CATEGORY.valueOf_ == "UNION":
            idt, idt_dependency = cls.parse_idt_category_union(ar_idt)
        else:
            logger.debug(f"Can not parse IDT with category of {utils.get_valueOf(ar_idt.CATEGORY)} yet!")
            pass
        type_emitter = None
        if hasattr(ar_idt, "TYPE_EMITTER") and ar_idt.TYPE_EMITTER:
            type_emitter = ar_idt.TYPE_EMITTER.valueOf_
        idt.update({"type_emitter": type_emitter})

        constraint_path = None
        idt.update({"constraint": {}})
        if (
            ar_idt.SW_DATA_DEF_PROPS
            and ar_idt.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS
            and ar_idt.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL
            and ar_idt.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[0].DATA_CONSTR_REF
        ):
            constraint_path = utils.get_valueOf(
                ar_idt.SW_DATA_DEF_PROPS.SW_DATA_DEF_PROPS_VARIANTS.SW_DATA_DEF_PROPS_CONDITIONAL[0].DATA_CONSTR_REF
            )
        if constraint_path and cls.constraints and constraint_path in cls.constraints:
            idt["constraint"].update(
                {"max": cls.constraints[constraint_path]["max"], "min": cls.constraints[constraint_path]["min"]}
            )
        cls.datatype_path_to_idt_mapping[ar_path] = {"idt": idt, "idt_dependency": idt_dependency}
        return idt, idt_dependency

    @classmethod
    def __parse_all_idts_and_dependency(cls, ar_asw):
        idts = {}
        idts_dependency = {}
        path_to_idt_mapping = {}
        ar_idts = ar_asw.find_nodes("IMPLEMENTATION-DATA-TYPE")
        ar_idts.sort(key=lambda x: x.get_path())
        for ar_idt in ar_idts:
            idt_path = ar_idt.get_path()
            if idt_path in path_to_idt_mapping:
                continue
            idt, idt_dependency = cls.parse_idt_and_dependency(ar_idt)
            if not idt:
                continue
            path_to_idt_mapping[idt_path] = {"idt": idt, "idt_dependency": idt_dependency}
            idt_name = utils.get_short_name(ar_idt)
            type_emitter = idt.get("type_emitter", None)
            if (idt_name not in idts) or (not type_emitter) or (type_emitter == "RTE"):
                idts[idt_name] = idt
                idts_dependency.update(idt_dependency)
        return idts, idts_dependency, path_to_idt_mapping

    @classmethod
    def __parse_numerical_constant_value(cls, value_spec, datatype):
        base_type = cls.get_arg_base_type(datatype["name"])
        return cls.__numerical_data_type_convert(utils.get_value(value_spec), base_type)

    @classmethod
    def __parse_all_struct_value(cls, value_spec, datatype):
        value = {}
        value.update(
            {
                "name": f"Rte_C_{datatype['name']}",
                "type": "STRUCTURE",
                "value": cls.__parse_struct_value(value_spec, datatype),
            }
        )
        return value

    @classmethod
    def __get_all_value_spec_based_on_datatype(cls, value_spec):
        all_value_specs = []
        all_value_specs.extend(value_spec.FIELDS.NUMERICAL_VALUE_SPECIFICATION)
        all_value_specs.extend(value_spec.FIELDS.RECORD_VALUE_SPECIFICATION)
        all_value_specs.extend(value_spec.FIELDS.ARRAY_VALUE_SPECIFICATION)
        all_value_specs.sort(key=lambda x: x.index)
        return all_value_specs

    @classmethod
    def get_unique_keys(cls, original_key, input_dict):
        keys = list(input_dict.keys())
        new_key = original_key
        counter = 1
        while new_key in keys:
            new_key = f"{original_key}_{counter}"
            counter += 1
        return new_key

    @classmethod
    def __parse_struct_value(cls, value_spec, datatype):
        values = {}
        values = cls.__parse_struct_origin_value(value_spec)
        arg_base_type = cls.get_arg_base_type(datatype["name"])
        values = cls.__struct_data_type_convert(values, arg_base_type)
        return values

    @classmethod
    def __parse_struct_origin_value(cls, value_spec):
        all_value_specs = cls.__get_all_value_spec_based_on_datatype(value_spec)
        values = {}
        for index, value_spec in enumerate(all_value_specs):
            if value_spec.original_tagname_ == "NUMERICAL-VALUE-SPECIFICATION":
                if utils.get_label(value_spec) in values:
                    new_label = cls.get_unique_keys(utils.get_label(value_spec), values)
                    values[new_label] = utils.get_value(value_spec)
                else:
                    values[utils.get_label(value_spec)] = utils.get_value(value_spec)
            elif value_spec.original_tagname_ == "RECORD-VALUE-SPECIFICATION":
                if utils.get_label(value_spec) in values:
                    new_label = cls.get_unique_keys(utils.get_label(value_spec), values)
                    values[new_label] = cls.__parse_struct_origin_value(value_spec)
                else:
                    values[utils.get_label(value_spec)] = cls.__parse_struct_origin_value(value_spec)
            elif value_spec.original_tagname_ == "ARRAY-VALUE-SPECIFICATION":
                if utils.get_label(value_spec) in values:
                    new_label = cls.get_unique_keys(utils.get_label(value_spec), values)
                    values[new_label] = cls.__parse_array_origin_value(value_spec)
                else:
                    values[utils.get_label(value_spec)] = cls.__parse_array_origin_value(value_spec)
        return values

    @classmethod
    def __parse_all_application_value(cls, value_spec, datatype):
        value = {}

        if value_spec.SW_VALUE_CONT.SW_VALUES_PHYS.V:
            temp_value = cls.__numerical_data_type_convert(
                value_spec.SW_VALUE_CONT.SW_VALUES_PHYS.V[0].valueOf_, datatype
            )
        elif value_spec.SW_VALUE_CONT.SW_VALUES_PHYS.VT:
            temp_value = value_spec.SW_VALUE_CONT.SW_VALUES_PHYS.VT[0].valueOf_
        value.update({"name": f"Rte_C_{datatype['name']}", "type": "APPLICATION", "value": temp_value})
        return value

    @classmethod
    def __parse_all_numerical_value(cls, value_spec, datatype):
        value = {}
        value.update(
            {
                "name": f"Rte_C_{datatype['name']}",
                "type": "NUMERICAL",
                "value": cls.__numerical_data_type_convert(utils.get_value(value_spec), datatype),
            }
        )
        return value

    @classmethod
    def __numerical_data_type_convert(cls, value, datatype):
        if "basetype" in datatype:
            value = cls.__data_type_convert(value, datatype["basetype"])
        elif "datatype" in datatype:
            value = cls.__data_type_convert(value, datatype["datatype"])
        elif type(datatype) is dict and datatype.get("category", "") == "UNION":
            # the generated union datatype is based on the first data type
            mem_datatype = datatype["members"][0]["datatype"]
            value = cls.__data_type_convert(value, mem_datatype)
        elif type(datatype) is str:
            value = cls.__data_type_convert(value, datatype)
        else:
            # TODO
            print("add parser of __numerical_data_type_convert")
        return value

    @classmethod
    def __data_type_convert(cls, value, data_type):
        if "bool" in data_type.lower():
            value = "FALSE" if value in ["FALSE", "0", 0, "0.0", 0.0] else "TRUE"
        elif "uint64" in data_type.lower():
            value = str(value) + "ULL"
        elif "uint" in data_type.lower():
            value = str(value) + "U"
        elif "float64" in data_type.lower() or "double" in data_type.lower():
            value = str(float(value))
        elif "float" in data_type.lower():
            value = str(float(value)) + "F"
        elif "sint" in data_type.lower():
            pass
        return value

    @classmethod
    def __parse_all_array_value(cls, value_spec, datatype):
        value = {}
        value.update(
            {
                "name": f"Rte_C_{datatype['name']}",
                "type": "ARRAY",
                "value": cls.__parse_array_value(value_spec, datatype),
            }
        )
        return value

    @classmethod
    def __parse_array_origin_value(cls, value_spec):
        values = {}
        num_values = value_spec.ELEMENTS.NUMERICAL_VALUE_SPECIFICATION
        if num_values:
            for index, num_value in enumerate(num_values):
                values[index] = utils.get_value(num_value)
        struct_values = value_spec.ELEMENTS.RECORD_VALUE_SPECIFICATION
        if struct_values:
            for index, struct_value in enumerate(struct_values):
                values[index] = cls.__parse_struct_origin_value(struct_value)
        array_values = value_spec.ELEMENTS.ARRAY_VALUE_SPECIFICATION
        if array_values:
            for index, array_value in enumerate(array_values):
                values[index] = cls.__parse_array_origin_value(array_value)
        application_values = value_spec.ELEMENTS.APPLICATION_VALUE_SPECIFICATION
        if application_values:
            for index, application_value in enumerate(application_values):
                if utils.get_valueOf(application_value.CATEGORY) == "VALUE":
                    value = utils.get_valueOf(application_value.SW_VALUE_CONT.SW_VALUES_PHYS.V[0])
                    values[index] = value
                else:
                    logger.debug(
                        "Can not parse array value with category of "
                        f"{utils.get_valueOf(application_value.CATEGORY)} yet!"
                    )
        const_refs = value_spec.ELEMENTS.CONSTANT_REFERENCE
        if const_refs:
            for index, const_ref in enumerate(const_refs):
                value_spec = const_ref.find(utils.get_valueOf(const_ref.CONSTANT_REF)).VALUE_SPEC
                num_value = value_spec.NUMERICAL_VALUE_SPECIFICATION
                if num_value:
                    values[index] = utils.get_value(num_value)
                struct_value = value_spec.RECORD_VALUE_SPECIFICATION
                if struct_value:
                    values[index] = cls.__parse_struct_origin_value(struct_value)
                array_value = value_spec.ARRAY_VALUE_SPECIFICATION
                if array_value:
                    values[index] = cls.__parse_array_origin_value(array_value)
        return values

    @classmethod
    def __parse_array_value(cls, value_spec, datatype):
        values = cls.__parse_array_origin_value(value_spec)
        arg_base_type = cls.get_arg_base_type(datatype["name"])
        values = cls.__array_data_type_convert(values, arg_base_type)
        return values

    @classmethod
    def __array_data_type_convert(cls, values, arg_base_type):
        if values and arg_base_type:
            if len(values) != len(arg_base_type):
                logger.error(
                    "Length of array values does not match length of argument base type: "
                    f"{len(values)}!= {len(arg_base_type)}"
                )
            for ind, value in values.items():
                if ind < len(arg_base_type) and type(arg_base_type[ind]) is str:
                    values[ind] = cls.__numerical_data_type_convert(value, arg_base_type[ind])
                elif ind < len(arg_base_type) and type(arg_base_type[ind]) is list:
                    values[ind] = cls.__array_data_type_convert(value, arg_base_type[ind])
                elif ind < len(arg_base_type) and type(arg_base_type[ind]) is dict:
                    values[ind] = cls.__struct_data_type_convert(value, arg_base_type[ind])
                else:
                    continue
        return values

    @classmethod
    def __struct_data_type_convert(cls, values, arg_base_type):
        if values and arg_base_type:
            if list(values.keys()) == list(arg_base_type.keys()):
                # the keys of values are the same as the define
                for key, value in values.items():
                    if type(arg_base_type[key]) is str:
                        values[key] = cls.__numerical_data_type_convert(value, arg_base_type[key])
                    elif type(arg_base_type[key]) is list:
                        values[key] = cls.__array_data_type_convert(value, arg_base_type[key])
                    elif type(arg_base_type[key]) is dict:
                        values[key] = cls.__struct_data_type_convert(value, arg_base_type[key])
            else:
                # the keys of values are not the same as the define
                values_list = list(values.values())
                keys_list = list(values.keys())
                basetype_list = list(arg_base_type.values())
                for ind, value in enumerate(values_list):
                    if type(basetype_list[ind]) is str:
                        values[keys_list[ind]] = cls.__numerical_data_type_convert(value, basetype_list[ind])
                    elif type(basetype_list[ind]) is list:
                        values[keys_list[ind]] = cls.__array_data_type_convert(value, basetype_list[ind])
                    elif type(basetype_list[ind]) is dict:
                        values[keys_list[ind]] = cls.__struct_data_type_convert(value, basetype_list[ind])
        return values

    @classmethod
    def __get_all_constants(cls, ar_asw):
        consts = {}
        ar_consts = ar_asw.find_nodes("CONSTANT-SPECIFICATION")
        for ar_const in ar_consts:
            consts[utils.get_short_name(ar_const)] = {"ar_const": ar_const}
        return consts

    @classmethod
    def __parse_datatype_mapping_sets(cls, ar_asw):
        mapping_sets = {}
        adt_mappings = {}
        for mapping_set in ar_asw.find_nodes("DATA-TYPE-MAPPING-SET"):
            if mapping_set.DATA_TYPE_MAPS:
                mapping_set_path = mapping_set.get_path()
                mapping_sets[mapping_set_path] = {}
                for mapping in mapping_set.DATA_TYPE_MAPS.DATA_TYPE_MAP:
                    mapping_sets[mapping_set_path].update(
                        {
                            utils.get_valueOf(mapping.APPLICATION_DATA_TYPE_REF): utils.get_valueOf(
                                mapping.IMPLEMENTATION_DATA_TYPE_REF
                            )
                        }
                    )
                    adt_mappings.update(
                        {
                            utils.get_valueOf(mapping.APPLICATION_DATA_TYPE_REF): utils.get_valueOf(
                                mapping.IMPLEMENTATION_DATA_TYPE_REF
                            )
                        }
                    )
        return mapping_sets, adt_mappings

    @classmethod
    def __parse_all_mode_dclr_groups(cls, ar_asw):
        mode_dclr_groups_dict = {}
        ar_mode_dclr_groups = ar_asw.find_nodes("MODE-DECLARATION-GROUP")
        for ar_mode_dclr_group in ar_mode_dclr_groups:
            mode_dclr_group_name = utils.get_short_name(ar_mode_dclr_group)
            if mode_dclr_group_name in mode_dclr_groups_dict:
                continue
            mode_dclr_group_dict = cls.parse_mode_dclr_group(ar_mode_dclr_group)
            if mode_dclr_group_dict:
                mode_dclr_groups_dict.update({mode_dclr_group_name: mode_dclr_group_dict})
        return mode_dclr_groups_dict

    @classmethod
    def to_mode_group_codegen_dict(cls, ar_asw):
        idts = cls.__parse_all_mode_dclr_groups(ar_asw)
        return idts

    # TODO: for M/S only, needs to remove
    @staticmethod
    def __pack_port_prototype_connection(ar):
        p_port_connections = {}
        r_port_connections = {}
        ar_ecu_compositions = ar.find_nodes("COMPOSITION-SW-COMPONENT-TYPE")
        if len(ar_ecu_compositions) == 0:
            return p_port_connections, r_port_connections
        for ar_ecu_composition in ar_ecu_compositions:
            if not ar_ecu_composition.CONNECTORS:
                continue
            for assembly_connector in ar_ecu_composition.CONNECTORS.ASSEMBLY_SW_CONNECTOR:
                provider_iref = assembly_connector.PROVIDER_IREF
                requester_iref = assembly_connector.REQUESTER_IREF
                p_port_connections.update(
                    {provider_iref.TARGET_P_PORT_REF.valueOf_: requester_iref.TARGET_R_PORT_REF.valueOf_}
                )
                r_port_connections.update(
                    {requester_iref.TARGET_R_PORT_REF.valueOf_: provider_iref.TARGET_P_PORT_REF.valueOf_}
                )
        return p_port_connections, r_port_connections

    @classmethod
    def __parse_assembly_connection(cls, ar):
        # new connections dict, better data structures, better performance
        p_connections = {}
        r_connections = {}
        # get all pr-port
        pr_port_paths = set()
        for swc_type in cls.sw_component_types:
            if not swc_type.PORTS:
                continue
            pr_ports = swc_type.PORTS.PR_PORT_PROTOTYPE
            if pr_ports:
                pr_port_paths.update([x.get_path() for x in pr_ports])
        # for pr-ports, it is self connected
        for port_path in pr_port_paths:
            p_connections[port_path] = ([], set())
            p_connections[port_path][0].append(port_path)
            r_connections[port_path] = ([], set())
            r_connections[port_path][0].append(port_path)
        # parse all connections
        ar_ecu_compositions = ar.find_nodes("COMPOSITION-SW-COMPONENT-TYPE")
        if len(ar_ecu_compositions) == 0:
            for path, conn_info in p_connections.items():
                p_connections[path] = conn_info[0]
            for path, conn_info in r_connections.items():
                r_connections[path] = conn_info[0]
            return p_connections, r_connections
        for ar_ecu_composition in ar_ecu_compositions:
            if not ar_ecu_composition.CONNECTORS:
                continue
            for assembly_connector in ar_ecu_composition.CONNECTORS.ASSEMBLY_SW_CONNECTOR:
                p_path = assembly_connector.PROVIDER_IREF.TARGET_P_PORT_REF.valueOf_
                r_path = assembly_connector.REQUESTER_IREF.TARGET_R_PORT_REF.valueOf_
                cls.__parse_connection(p_path, r_path, p_connections)
                cls.__parse_connection(r_path, p_path, r_connections)
        for path, conn_info in p_connections.items():
            p_connections[path] = conn_info[0]
        for path, conn_info in r_connections.items():
            r_connections[path] = conn_info[0]
        return p_connections, r_connections

    @classmethod
    def __parse_connection(cls, path_a, path_b, connections_a):
        if path_a not in connections_a:
            connections_a[path_a] = ([], set())
        if path_b in connections_a[path_a][1]:
            return
        connections_a[path_a][0].append(path_b)
        connections_a[path_a][1].add(path_b)

    @classmethod
    def __pre_parse_swc_info(cls):
        for sw_component in cls.sw_component_types:
            if not hasattr(sw_component, "PORTS"):
                continue
            ports = sw_component.PORTS
            swc_name = sw_component.SHORT_NAME.valueOf_
            if hasattr(ports, "P_PORT_PROTOTYPE"):
                for port in ports.P_PORT_PROTOTYPE:
                    cls.__pre_parse_swc_info_p_port(swc_name, port)
            if hasattr(ports, "R_PORT_PROTOTYPE"):
                for port in ports.R_PORT_PROTOTYPE:
                    cls.__pre_parse_swc_info_r_port(swc_name, port)
            if hasattr(ports, "PR_PORT_PROTOTYPE"):
                for port in ports.PR_PORT_PROTOTYPE:
                    cls.__pre_parse_swc_info_pr_port(swc_name, port)
            for behavior in getattr(getattr(sw_component, "INTERNAL_BEHAVIORS", None), "SWC_INTERNAL_BEHAVIOR", []):
                if not behavior.RUNNABLES:
                    continue
                for runnable_entity in behavior.RUNNABLES.RUNNABLE_ENTITY:
                    run_path = runnable_entity.get_path()
                    if runnable_entity.ASYNCHRONOUS_SERVER_CALL_RESULT_POINTS:
                        cls.__pre_parse_swc_info_cs_result_points(runnable_entity, run_path)

    @classmethod
    def __pre_parse_swc_info_r_port_cal_prm(cls, swc_name, port):
        if not hasattr(port, "REQUIRED_COM_SPECS"):
            return
        r_specs = port.REQUIRED_COM_SPECS

        if hasattr(r_specs, "PARAMETER_REQUIRE_COM_SPEC"):
            for comspec in r_specs.PARAMETER_REQUIRE_COM_SPEC:
                if not comspec.PARAMETER_REF:
                    continue
                key = f"{swc_name}_{port.SHORT_NAME.valueOf_}_{comspec.PARAMETER_REF.valueOf_.split('/')[-1]}"
                if key not in cls.r_param_comspec_map:
                    cls.r_param_comspec_map[key] = comspec

    @classmethod
    def __pre_parse_swc_info_r_port_sr(cls, swc_name, port):
        if not hasattr(port, "REQUIRED_COM_SPECS"):
            return
        r_specs = port.REQUIRED_COM_SPECS

        if hasattr(r_specs, "NONQUEUED_RECEIVER_COM_SPEC"):
            for comspec in r_specs.NONQUEUED_RECEIVER_COM_SPEC:
                if not comspec.DATA_ELEMENT_REF:
                    continue
                key = f"{swc_name}_{port.SHORT_NAME.valueOf_}_{comspec.DATA_ELEMENT_REF.valueOf_.split('/')[-1]}"
                if key not in cls.r_access_comspec_map:
                    cls.r_access_comspec_map[key] = comspec
        if hasattr(r_specs, "NV_REQUIRE_COM_SPEC"):
            for comspec in r_specs.NV_REQUIRE_COM_SPEC:
                if not comspec.VARIABLE_REF:
                    continue
                key = f"{swc_name}_{port.SHORT_NAME.valueOf_}_{comspec.VARIABLE_REF.valueOf_.split('/')[-1]}"
                if key not in cls.r_access_comspec_map:
                    cls.r_access_comspec_map[key] = comspec

    @classmethod
    def __pre_parse_swc_info_p_port_sr(cls, swc_name, port):
        if not hasattr(port, "PROVIDED_COM_SPECS"):
            return
        p_specs = port.PROVIDED_COM_SPECS
        if hasattr(p_specs, "NONQUEUED_SENDER_COM_SPEC"):
            for comspec in p_specs.NONQUEUED_SENDER_COM_SPEC:
                if not comspec.DATA_ELEMENT_REF:
                    continue
                key = f"{swc_name}_{port.SHORT_NAME.valueOf_}_{comspec.DATA_ELEMENT_REF.valueOf_.split('/')[-1]}"
                if key not in cls.p_access_comspec_map:
                    cls.p_access_comspec_map[key] = comspec
        if hasattr(p_specs, "NV_PROVIDE_COM_SPEC"):
            for comspec in p_specs.NV_PROVIDE_COM_SPEC:
                if not comspec.VARIABLE_REF:
                    continue
                key = f"{swc_name}_{port.SHORT_NAME.valueOf_}_{comspec.VARIABLE_REF.valueOf_.split('/')[-1]}"
                if key not in cls.p_access_comspec_map:
                    cls.p_access_comspec_map[key] = comspec

    @classmethod
    def __pre_parse_swc_info_pr_port(cls, swc_name, port):
        if not hasattr(port, "PROVIDED_REQUIRED_INTERFACE_TREF"):
            return
        cls.__pre_parse_swc_info_p_port_sr(swc_name, port)
        cls.__pre_parse_swc_info_r_port_sr(swc_name, port)

    @classmethod
    def __pre_parse_swc_info_r_port(cls, swc_name, port):
        if not hasattr(port, "REQUIRED_INTERFACE_TREF"):
            return
        pref = port.REQUIRED_INTERFACE_TREF
        if not hasattr(pref, "DEST"):
            return
        dest = pref.DEST
        if dest == "SENDER-RECEIVER-INTERFACE":
            cls.__pre_parse_swc_info_r_port_sr(swc_name, port)
        elif dest == "PARAMETER-INTERFACE":
            cls.__pre_parse_swc_info_r_port_cal_prm(swc_name, port)
            pass

    @classmethod
    def __pre_parse_swc_info_p_port(cls, swc_name, port):
        if not hasattr(port, "PROVIDED_INTERFACE_TREF"):
            return
        pref = port.PROVIDED_INTERFACE_TREF
        if not hasattr(pref, "DEST"):
            return
        dest = pref.DEST
        if dest == "SENDER-RECEIVER-INTERFACE":
            cls.__pre_parse_swc_info_p_port_sr(swc_name, port)
        else:
            pass

    @classmethod
    def __pre_parse_swc_info_cs_result_points(cls, runnable_entity, run_path):
        for result_point in getattr(
            runnable_entity.ASYNCHRONOUS_SERVER_CALL_RESULT_POINTS, "ASYNCHRONOUS_SERVER_CALL_RESULT_POINT", []
        ):
            call_point_ref = getattr(result_point, "ASYNCHRONOUS_SERVER_CALL_POINT_REF", None)
            if not call_point_ref:
                continue
            call_point_path = call_point_ref.valueOf_
            if call_point_path not in cls.cs_ret_evt_trig_run:
                cls.cs_ret_evt_trig_run[call_point_path] = set()
            cls.cs_ret_evt_trig_run[call_point_path].add(run_path)

    @classmethod
    def __parse_cs_rport_result_runnable(cls, call_point, runnable_entity):
        call_run_path = runnable_entity.get_path()
        call_point_path = call_point.get_path()
        if call_point_path not in cls.cs_ret_evt_trig_run:
            return []

        result_runs_set = cls.cs_ret_evt_trig_run[call_point_path]
        if call_run_path in result_runs_set:
            result_runnable = [call_run_path]
        else:
            result_runnable = []
        for path in sorted(result_runs_set):
            if path == call_run_path:
                continue
            result_runnable.append(path)
        return result_runnable

    @classmethod
    def __parse_cs_rport_return_mode(cls, access):
        if access.get_tag() == "SYNCHRONOUS-SERVER-CALL-POINT":
            return "waiting"
        call_point_path = access.get_path()
        runnable_entity = access.get_path_parent()
        internal_behavior = runnable_entity.get_path_parent()
        sw_component = internal_behavior.get_path_parent()

        # If no ASYNCHRONOUS-SERVER-CALL-RESULT-POINT relates to this access point, it means the return mode is "none"
        none_flag = True
        for result_point in getattr(
            runnable_entity.ASYNCHRONOUS_SERVER_CALL_RESULT_POINTS, "ASYNCHRONOUS_SERVER_CALL_RESULT_POINT", []
        ):
            if access == runnable_entity.find(result_point.ASYNCHRONOUS_SERVER_CALL_POINT_REF.valueOf_):
                none_flag = False
                break
        if none_flag and call_point_path not in cls.cs_ret_evt_trig_run:
            return "none"

        # If no WAIT-POINT relates to this access point, it means the return mode is "polling"
        for wait_point in getattr(runnable_entity.WAIT_POINTS, "WAIT_POINT", []):
            if wait_point.TRIGGER_REF:
                # Try find [WAIT-POINT ->
                # ASYNCHRONOUS-SERVER-CALL-RETURNS-EVENT ->
                # ASYNCHRONOUS-SERVER-CALL-RESULT-POINT ->
                # ASYNCHRONOUS-SERVER-CALL-POINT]
                # relation chain
                trigger_ref_path = wait_point.TRIGGER_REF.valueOf_
                return_event = sw_component.find(trigger_ref_path)
                event_source_ref_path = return_event.EVENT_SOURCE_REF.valueOf_
                result_point = runnable_entity.find(event_source_ref_path)
                server_call_point_ref = result_point.ASYNCHRONOUS_SERVER_CALL_POINT_REF.valueOf_
                server_call_point = runnable_entity.find(server_call_point_ref)
                if server_call_point == access:
                    return "waiting"
            else:
                continue

        return "polling"

    @classmethod
    def get_sw_component_prototype(cls, ar_asw):
        sw_component_prototype_dict = {}
        if not ar_asw:
            return sw_component_prototype_dict
        compositions = ar_asw.find_nodes("COMPOSITION-SW-COMPONENT-TYPE")
        if not compositions:
            return sw_component_prototype_dict
        for composition in compositions:
            sw_component_prototypes = composition.COMPONENTS.SW_COMPONENT_PROTOTYPE
            if sw_component_prototypes:
                for sw_component_prototype in sw_component_prototypes:
                    short_name = utils.get_short_name(sw_component_prototype)
                    uuid = sw_component_prototype.UUID
                    type_tref = utils.get_type_tref(sw_component_prototype)
                    type_tref_dest = sw_component_prototype.TYPE_TREF.DEST
                    sw_component_prototype_dict.update({short_name: {}})
                    sw_component_prototype_dict[short_name].update({"short_name": short_name})
                    sw_component_prototype_dict[short_name].update({"uuid": uuid})
                    sw_component_prototype_dict[short_name].update({"type_tref": type_tref})
                    sw_component_prototype_dict[short_name].update({"type_tref_dest": type_tref_dest})
                    sw_component_prototype_dict[short_name].update(
                        {"CONTEXT-COMPONENT-REF": sw_component_prototype.get_path()}
                    )
        return sw_component_prototype_dict

    @classmethod
    def create_admin_data_object(cls, sdgs_list):
        admin_data_object = autosar44.ADMIN_DATA()
        sdgs_object = cls.create_sdgs_object(sdgs_list)
        admin_data_object.SDGS = sdgs_object
        return admin_data_object

    @classmethod
    def create_sdgs_object(cls, sd_list):
        sdgs_object = autosar44.SDGSType50()
        for key, value in sd_list.items():
            sdg_object = cls.create_sdg_object(key, value)
            sdgs_object.SDG.append(sdg_object)
        return sdgs_object

    @classmethod
    def create_sdg_object(cls, sdg_name, sd_list):
        sdg_object = autosar44.SDG()
        sdg_object.GID = sdg_name
        for sd_info in sd_list:
            sd = cls.create_sd_object(sd_info["GID"], sd_info["valueOf_"])
            sdg_object.SD.append(sd)
        return sdg_object

    @classmethod
    def create_sd_object(cls, sd_name, sd_value):
        sd_object = autosar44.SD()
        sd_object.GID = sd_name
        sd_object.valueOf_ = sd_value
        return sd_object

    @classmethod
    def get_all_ref_configuration_items_by_ref_target(cls, ecuc_autosar_dict, ref_target, new_ref_target=None):
        all_ref_configuration_items_by_ref_target_dict = {}
        for module_name, module_object in ecuc_autosar_dict.items():
            reference_object = module_object.find("/ActiveEcuC/" + module_name)
            if reference_object is None:
                continue
            containers = reference_object.CONTAINERS.parent_object_.CONTAINERS.ECUC_CONTAINER_VALUE
            for i in range(len(containers)):
                container = containers[i]
                if hasattr(container, "REFERENCE_VALUES") and container.REFERENCE_VALUES:
                    cls.traversal_ref_values(
                        container.REFERENCE_VALUES,
                        ref_target,
                        all_ref_configuration_items_by_ref_target_dict,
                        new_ref_target,
                    )
                cls.traversal_sub_container(
                    container, ref_target, all_ref_configuration_items_by_ref_target_dict, new_ref_target
                )

        return all_ref_configuration_items_by_ref_target_dict

    @classmethod
    def traversal_sub_container(
        cls, containers, ref_target, all_ref_configuration_items_by_ref_target_dict, new_ref_target=None
    ):

        sub_containers = containers.SUB_CONTAINERS
        if sub_containers:
            for i in range(len(sub_containers.ECUC_CONTAINER_VALUE)):
                sub_container = sub_containers.ECUC_CONTAINER_VALUE[i]
                if hasattr(sub_container, "REFERENCE_VALUES") and sub_container.REFERENCE_VALUES:
                    cls.traversal_ref_values(
                        sub_container.REFERENCE_VALUES,
                        ref_target,
                        all_ref_configuration_items_by_ref_target_dict,
                        new_ref_target,
                    )
                cls.traversal_sub_container(
                    sub_container, ref_target, all_ref_configuration_items_by_ref_target_dict, new_ref_target
                )

    @classmethod
    def traversal_ref_values(
        cls, ref_obj, ref_target, all_ref_configuration_items_by_ref_target_dict, new_ref_target=None
    ):
        if hasattr(ref_obj, "ECUC_INSTANCE_REFERENCE_VALUE") and ref_obj.ECUC_INSTANCE_REFERENCE_VALUE:
            for i in range(len(ref_obj.ECUC_INSTANCE_REFERENCE_VALUE)):
                if hasattr(ref_obj.ECUC_INSTANCE_REFERENCE_VALUE[i], "VALUE_IREF"):
                    ref_target_value = utils.get_value_iref(ref_obj.ECUC_INSTANCE_REFERENCE_VALUE[i])
                    if ref_target_value == ref_target:
                        emement = (
                            ref_obj.get_path()
                            + "/"
                            + ref_obj.ECUC_INSTANCE_REFERENCE_VALUE[i].DEFINITION_REF.valueOf_.split("/")[-1]
                        )
                        all_ref_configuration_items_by_ref_target_dict[emement] = ref_target_value
                        if new_ref_target:
                            utils.set_value_ref(ref_obj.ECUC_REFERENCE_VALUE[i], new_ref_target)
        if hasattr(ref_obj, "ECUC_REFERENCE_VALUE") and ref_obj.ECUC_REFERENCE_VALUE:
            for i in range(len(ref_obj.ECUC_REFERENCE_VALUE)):
                if hasattr(ref_obj.ECUC_REFERENCE_VALUE[i], "VALUE_REF"):
                    ref_target_value = utils.get_value_ref(ref_obj.ECUC_REFERENCE_VALUE[i])
                    if ref_target_value == ref_target:
                        emement = (
                            ref_obj.get_path()
                            + "/"
                            + ref_obj.ECUC_REFERENCE_VALUE[i].DEFINITION_REF.valueOf_.split("/")[-1]
                        )
                        all_ref_configuration_items_by_ref_target_dict[emement] = ref_target_value
                        if new_ref_target:
                            utils.set_value_ref(ref_obj.ECUC_REFERENCE_VALUE[i], new_ref_target)

    @classmethod
    def traversal_para_values_global_filter(cls, para_obj, all_element_items_list, filter_text=None):

        if hasattr(para_obj, "ECUC_ADD_INFO_PARAM_VALUE") and para_obj.ECUC_ADD_INFO_PARAM_VALUE:
            for i in range(len(para_obj.ECUC_ADD_INFO_PARAM_VALUE)):
                cls.get_para_element(para_obj.ECUC_ADD_INFO_PARAM_VALUE[i], all_element_items_list, filter_text)

        if hasattr(para_obj, "ECUC_NUMERICAL_PARAM_VALUE") and para_obj.ECUC_NUMERICAL_PARAM_VALUE:
            for i in range(len(para_obj.ECUC_NUMERICAL_PARAM_VALUE)):
                cls.get_para_element(para_obj.ECUC_NUMERICAL_PARAM_VALUE[i], all_element_items_list, filter_text)

        if hasattr(para_obj, "ECUC_TEXTUAL_PARAM_VALUE") and para_obj.ECUC_TEXTUAL_PARAM_VALUE:
            for i in range(len(para_obj.ECUC_TEXTUAL_PARAM_VALUE)):
                cls.get_para_element(para_obj.ECUC_TEXTUAL_PARAM_VALUE[i], all_element_items_list, filter_text)

    @classmethod
    def traversal_ref_values_global_filter(cls, ref_obj, all_element_items_list, filter_text=None):
        if hasattr(ref_obj, "ECUC_INSTANCE_REFERENCE_VALUE") and ref_obj.ECUC_INSTANCE_REFERENCE_VALUE:
            for i in range(len(ref_obj.ECUC_INSTANCE_REFERENCE_VALUE)):
                cls.get_ref_element(
                    ref_obj.ECUC_INSTANCE_REFERENCE_VALUE[i], all_element_items_list, "iref", filter_text
                )

        if hasattr(ref_obj, "ECUC_REFERENCE_VALUE") and ref_obj.ECUC_REFERENCE_VALUE:
            for i in range(len(ref_obj.ECUC_REFERENCE_VALUE)):
                cls.get_ref_element(ref_obj.ECUC_REFERENCE_VALUE[i], all_element_items_list, "ref", filter_text)

    @classmethod
    def traversal_sub_container_global_filter(cls, containers, all_element_items_list, filter_text):

        sub_containers = containers.SUB_CONTAINERS
        if sub_containers:
            for i in range(len(sub_containers.ECUC_CONTAINER_VALUE)):
                sub_container = sub_containers.ECUC_CONTAINER_VALUE[i]
                if hasattr(sub_container, "SHORT_NAME") and sub_container.SHORT_NAME:
                    cls.get_container_element(sub_container, all_element_items_list, filter_text)
                if hasattr(sub_container, "PARAMETER_VALUES") and sub_container.PARAMETER_VALUES:
                    cls.traversal_para_values_global_filter(
                        sub_container.PARAMETER_VALUES, all_element_items_list, filter_text
                    )
                if hasattr(sub_container, "REFERENCE_VALUES") and sub_container.REFERENCE_VALUES:
                    cls.traversal_ref_values_global_filter(
                        sub_container.REFERENCE_VALUES, all_element_items_list, filter_text
                    )
                cls.traversal_sub_container_global_filter(sub_container, all_element_items_list, filter_text)

    @classmethod
    def get_all_element_items_by_filter_value(cls, ecuc_autosar_dict, filter_value):
        all_element_items_by_filter_value_dict = {}
        for module_name, module_object in ecuc_autosar_dict.items():
            reference_object = module_object.find("/ActiveEcuC/" + module_name)
            containers = reference_object.CONTAINERS.parent_object_.CONTAINERS.ECUC_CONTAINER_VALUE
            for i in range(len(containers)):
                container = containers[i]
                if hasattr(container, "SHORT_NAME") and container.SHORT_NAME:
                    if filter_value in container.SHORT_NAME.valueOf_.lower():
                        logger.debug("short Name匹配")
                if hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES:
                    cls.traversal_para_values_global_filter(
                        container.PARAMETER_VALUES, filter_value, all_element_items_by_filter_value_dict
                    )
                if hasattr(container, "REFERENCE_VALUES") and container.REFERENCE_VALUES:
                    cls.traversal_ref_values_global_filter(
                        container.REFERENCE_VALUES, filter_value, all_element_items_by_filter_value_dict
                    )
                cls.traversal_sub_container_global_filter(
                    container, filter_value, all_element_items_by_filter_value_dict
                )

        return all_element_items_by_filter_value_dict

    @classmethod
    def get_all_element_items(cls, ecuc_autosar_dict, filter_text):
        all_element_items_list = []
        for module_name, module_object in ecuc_autosar_dict.items():
            reference_object = module_object.find("/ActiveEcuC/" + module_name)
            if hasattr(reference_object, "CONTAINERS"):
                containers = reference_object.CONTAINERS.parent_object_.CONTAINERS.ECUC_CONTAINER_VALUE
                for i in range(len(containers)):
                    container = containers[i]
                    if hasattr(container, "SHORT_NAME") and container.SHORT_NAME:
                        cls.get_container_element(container, all_element_items_list, filter_text)
                    if hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES:
                        cls.traversal_para_values_global_filter(
                            container.PARAMETER_VALUES, all_element_items_list, filter_text
                        )
                    if hasattr(container, "REFERENCE_VALUES") and container.REFERENCE_VALUES:
                        cls.traversal_ref_values_global_filter(
                            container.REFERENCE_VALUES, all_element_items_list, filter_text
                        )
                    cls.traversal_sub_container_global_filter(container, all_element_items_list, filter_text)

        return all_element_items_list

    @classmethod
    def get_element_items_by_module_name(cls, ecuc_autosar_dict, module_name):
        element_items_list = []
        reference_object = ecuc_autosar_dict[module_name].find("/ActiveEcuC/" + module_name)
        containers = reference_object.CONTAINERS.parent_object_.CONTAINERS.ECUC_CONTAINER_VALUE
        for i in range(len(containers)):
            container = containers[i]
            if hasattr(container, "SHORT_NAME") and container.SHORT_NAME:
                cls.get_container_element(container, element_items_list, None)
            if hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES:
                cls.traversal_para_values_global_filter(container.PARAMETER_VALUES, element_items_list)
            if hasattr(container, "REFERENCE_VALUES") and container.REFERENCE_VALUES:
                cls.traversal_ref_values_global_filter(container.REFERENCE_VALUES, element_items_list)
            cls.traversal_sub_container_with_short_name(container, element_items_list)

        return element_items_list

    @classmethod
    def traversal_sub_container_with_short_name(cls, containers, all_element_items_list):
        sub_containers = containers.SUB_CONTAINERS
        if sub_containers:
            for i in range(len(sub_containers.ECUC_CONTAINER_VALUE)):
                sub_container = sub_containers.ECUC_CONTAINER_VALUE[i]
                if hasattr(sub_container, "PARAMETER_VALUES") and sub_container.PARAMETER_VALUES:
                    cls.traversal_para_values_global_filter(sub_container.PARAMETER_VALUES, all_element_items_list)
                if hasattr(sub_container, "REFERENCE_VALUES") and sub_container.REFERENCE_VALUES:
                    cls.traversal_ref_values_global_filter(sub_container.REFERENCE_VALUES, all_element_items_list)
                cls.traversal_sub_container_global_filter(sub_container, all_element_items_list, None)

    @classmethod
    def get_container_element(cls, container_obj, all_element_items_list, filter_text=None):

        element_item_dict = {}
        element_item_dict["Element"] = container_obj.get_path()
        element_item_dict["Type"] = "Container"
        element_item_dict["Value"] = ""
        if filter_text is None:
            all_element_items_list.append(element_item_dict)
        elif (filter_text is not None) and filter_text in " ".join(
            str(value).lower() for value in element_item_dict.values() if value is not None
        ):
            all_element_items_list.append(element_item_dict)

    @classmethod
    def get_para_element(cls, para_obj, all_element_items_list, filter_text=None):

        element_item_dict = {}
        element_item_dict["Element"] = para_obj.get_path() + "/" + utils.get_definition_ref(para_obj).split("/")[-1]
        element_item_dict["Type"] = "Parameter"
        element_item_dict["Value"] = utils.get_value(para_obj)
        if filter_text is None:
            all_element_items_list.append(element_item_dict)
        elif (filter_text is not None) and filter_text in " ".join(
            str(value).lower() for value in element_item_dict.values() if value is not None
        ):
            all_element_items_list.append(element_item_dict)

    @classmethod
    def get_ref_element(cls, ref_obj, all_element_items_list, ref_type, filter_text=None):

        element_item_dict = {}
        element_item_dict["Element"] = ref_obj.get_path() + "/" + utils.get_definition_ref(ref_obj).split("/")[-1]
        element_item_dict["Type"] = "Parameter"
        if "ref" == ref_type:
            element_item_dict["Value"] = utils.get_value_ref(ref_obj)
        elif "iref" == ref_type:
            element_item_dict["Value"] = utils.get_value_iref(ref_obj)
        if filter_text is None:
            all_element_items_list.append(element_item_dict)
        elif (filter_text is not None) and filter_text in " ".join(
            str(value).lower() for value in element_item_dict.values() if value is not None
        ):
            all_element_items_list.append(element_item_dict)

    ####################################################################################################################
    # Parse autosar ecuc function
    @classmethod
    def set_autosar_ecuc_pararm_value(cls, ecuc_autosar_param_obj: object, ecuc_def_pararm_obj: object, value) -> bool:
        original_tagname_ = ecuc_def_pararm_obj.original_tagname_
        ecuc_textual_param_values = []
        if original_tagname_ == "ECUC-STRING-PARAM-DEF" or original_tagname_ == "ECUC-ENUMERATION-PARAM-DEF":
            if hasattr(ecuc_autosar_param_obj, "PARAMETER_VALUES") and hasattr(
                ecuc_autosar_param_obj.PARAMETER_VALUES, "ECUC_TEXTUAL_PARAM_VALUE"
            ):
                ecuc_textual_param_values = ecuc_autosar_param_obj.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE
        elif original_tagname_ == "ECUC-BOOLEAN-PARAM-DEF" or original_tagname_ == "ECUC-FLOAT-PARAM-DEF":
            if hasattr(ecuc_autosar_param_obj, "PARAMETER_VALUES") and hasattr(
                ecuc_autosar_param_obj.PARAMETER_VALUES, "ECUC_NUMERICAL_PARAM_VALUE"
            ):
                ecuc_textual_param_values = ecuc_autosar_param_obj.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE
        else:
            logger.error(f"unsupported type:utils.get_short_name(ecuc_autosar_param_obj), {original_tagname_}")
            return False

        flag = False
        for ecuc_textual_param_value in ecuc_textual_param_values:
            if utils.get_short_name(ecuc_def_pararm_obj) in ecuc_textual_param_value.DEFINITION_REF.valueOf_:
                utils.set_value(ecuc_textual_param_value, value)
                flag = True
                break

        if flag is False:
            logger.error(f"{utils.get_short_name(ecuc_def_pararm_obj)} set value fail: {original_tagname_}")
            return False

        return True

    @classmethod
    def get_all_element_items_components_pports_rports(cls, autosar_asw_class, filter_text):
        all_element_items_list = []
        element_item_dict = {}
        sw_components = []
        for comp_type in cls.SUPPORT_COMPONENT_TYPE:
            sw_components += autosar_asw_class.find_nodes(comp_type)

        for sw_component in sw_components:
            pports = []
            rports = []
            if sw_component.PORTS is not None:
                pports = sw_component.PORTS.P_PORT_PROTOTYPE
                rports = sw_component.PORTS.R_PORT_PROTOTYPE
            element_item_dict = {}
            element_item_dict["Element"] = sw_component.get_path()
            element_item_dict["Type"] = "component"
            element_item_dict["Value"] = ""
            if filter_text in " ".join(str(value).lower() for value in element_item_dict.values() if value is not None):
                all_element_items_list.append(element_item_dict)
            if len(pports):
                for pport in pports:
                    element_item_dict = {}
                    element_item_dict["Element"] = pport.get_path()
                    element_item_dict["Type"] = "pport"
                    element_item_dict["Value"] = ""
                    if filter_text in " ".join(
                        str(value).lower() for value in element_item_dict.values() if value is not None
                    ):
                        all_element_items_list.append(element_item_dict)

            if len(rports):
                for rport in rports:
                    element_item_dict = {}
                    element_item_dict["Element"] = rport.get_path()
                    element_item_dict["Type"] = "rport"
                    element_item_dict["Value"] = ""
                    if filter_text in " ".join(
                        str(value).lower() for value in element_item_dict.values() if value is not None
                    ):
                        all_element_items_list.append(element_item_dict)

        return all_element_items_list

    @classmethod
    def get_all_element_items_common(cls, autosar_asw_class, filter_text, element_tag):
        all_element_items_list = []
        element_item_dict = {}
        elements = autosar_asw_class.find_nodes(element_tag)

        for element in elements:
            element_item_dict = {}
            element_item_dict["Element"] = element.get_path()
            element_item_dict["Type"] = element_tag.lower().replace("-", "_")
            element_item_dict["Value"] = ""
            if filter_text in " ".join(str(value).lower() for value in element_item_dict.values() if value is not None):
                all_element_items_list.append(element_item_dict)
            pass

        return all_element_items_list

    @classmethod
    def get_all_element_items_from_asw(cls, autosar_asw_class, filter_text):
        element_items_list = []
        if autosar_asw_class is None:
            return element_items_list
        SUPPORT_TAG = [
            "DATA-CONSTR",
            "COMPU-METHOD",
            "IMPLEMENTATION-DATA-TYPE",
            "SENDER-RECEIVER-INTERFACE",
            "CLIENT-SERVER-INTERFACE",
            "SWC-INTERNAL-BEHAVIOR",
            "INIT-EVENT",
            "BACKGROUND-EVENT",
            "DATA-RECEIVED-EVENT",
            "OPERATION-INVOKED-EVENT",
            "SWC-MODE-SWITCH-EVENT",
            "MODE-SWITCHED-ACK-EVENT",
            "ASYNCHRONOUS-SERVER-CALL-RETURNS-EVENT",
            "TIMING-EVENT",
            "SWC-MODE-SWITCH-EVENT",
            "DATA-SEND-COMPLETED-EVENT",
            "DATA-WRITE-COMPLETED-EVENT",
            "RUNNABLES",
            "RUNNABLE-ENTITY",
            "VARIABLE-ACCESS",
        ]

        # 获取asw中所有的component、pport和rport
        rv = cls.get_all_element_items_components_pports_rports(autosar_asw_class, filter_text)
        for element_tag in SUPPORT_TAG:
            rv += cls.get_all_element_items_common(autosar_asw_class, filter_text, element_tag)
        element_items_list = list({tuple(sorted(d.items())): d for d in rv}.values())
        return element_items_list

    @classmethod
    def get_all_idts_and_dependency(cls, asw_autosar):
        return cls.__parse_all_idts_and_dependency(asw_autosar)

    @classmethod
    def get_all_compu_methods(cls, asw_autosar):
        return cls.__parse_all_compu_methods(asw_autosar)

    @classmethod
    def get_datatype_mapping_sets(cls, asw_autosar):
        return cls.__parse_datatype_mapping_sets(asw_autosar)

    @classmethod
    def get_bswmd_autosar_by_module_name(cls, module_name, module_obj):

        if hasattr(module_obj, "AR_PACKAGES"):
            ar_packages = getattr(module_obj, "AR_PACKAGES")
            bswmd_autosar = cls.traversal_ar_packages(module_name, ar_packages)
            return bswmd_autosar

    @classmethod
    def traversal_ar_packages(cls, module_name, ar_packages):
        if hasattr(ar_packages, "AR_PACKAGE") and getattr(ar_packages, "AR_PACKAGE") is not None:
            ar_package_list = getattr(ar_packages, "AR_PACKAGE")
            for ar_package in ar_package_list:
                if hasattr(ar_package, "ELEMENTS") and getattr(ar_package, "ELEMENTS") is not None:
                    element = getattr(ar_package, "ELEMENTS")
                    if hasattr(element, "ECUC_MODULE_DEF") and getattr(element, "ECUC_MODULE_DEF"):
                        ecuc_module_def_list = getattr(element, "ECUC_MODULE_DEF")
                        for ecuc_module_def in ecuc_module_def_list:
                            if utils.get_short_name(ecuc_module_def) == module_name:
                                return ecuc_module_def
                if hasattr(ar_package, "AR_PACKAGES") and getattr(ar_package, "AR_PACKAGES") is not None:
                    return cls.traversal_ar_packages(module_name, getattr(ar_package, "AR_PACKAGES"))

    @classmethod
    def __update_aux_server_runnable_connections(cls, connections, event_obj):
        pport_runnable_path = utils.get_valueOf(event_obj.START_ON_EVENT_REF)
        pport_path = utils.get_valueOf(event_obj.OPERATION_IREF.CONTEXT_P_PORT_REF)
        operation_path = utils.get_valueOf(event_obj.OPERATION_IREF.TARGET_PROVIDED_OPERATION_REF)
        interface_path = operation_path.rsplit("/", 1)[0]
        interface_obj = event_obj.find(interface_path)
        if not interface_obj or utils.get_is_service(interface_obj) != "false":
            return
        if pport_path not in cls.p_connections:
            # avoid flooding the screen
            # logger.warning(f'Server port <{pport_path}> is not connected!')
            return
        if pport_runnable_path not in connections:
            connections.update(
                {
                    pport_runnable_path: {
                        operation_path: {"pport_path": pport_path, "operation_path": operation_path, "rport_info": {}}
                    }
                }
            )
        if pport_runnable_path in connections and operation_path not in connections[pport_runnable_path]:
            connections[pport_runnable_path].update(
                {operation_path: {"pport_path": pport_path, "operation_path": operation_path, "rport_info": {}}}
            )
        for rport_path in cls.p_connections[pport_path]:
            rport_info = cls.get_cs_rport_runnable_info(rport_path, operation_path, event_obj)
            connections[pport_runnable_path][operation_path]["rport_info"].update(rport_info)

    @classmethod
    def get_cs_rport_runnable_info(cls, rport_path, pport_operation_path, event_obj):
        rport_info = {rport_path: {}}
        client_path = rport_path.rsplit("/", 1)[0]
        client_obj = event_obj.find(client_path)
        for behavior_obj in client_obj.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR:
            if behavior_obj.RUNNABLES:
                for runnable_obj in behavior_obj.RUNNABLES.RUNNABLE_ENTITY:
                    if runnable_obj.SERVER_CALL_POINTS:
                        for access_obj in (
                            runnable_obj.SERVER_CALL_POINTS.SYNCHRONOUS_SERVER_CALL_POINT
                            + runnable_obj.SERVER_CALL_POINTS.ASYNCHRONOUS_SERVER_CALL_POINT
                        ):
                            check_rport_path = utils.get_valueOf(access_obj.OPERATION_IREF.CONTEXT_R_PORT_REF)
                            check_operation_path = utils.get_valueOf(
                                access_obj.OPERATION_IREF.TARGET_REQUIRED_OPERATION_REF
                            )
                            check_operation_path_short = "/".join(check_operation_path.split("/")[-2:])
                            operation_path_short = "/".join(pport_operation_path.split("/")[-2:])
                            if check_rport_path == rport_path and check_operation_path_short == operation_path_short:
                                # use
                                if check_operation_path not in rport_info[rport_path]:
                                    rport_info[rport_path].update({check_operation_path: {"rport_runnable": []}})
                                rport_info[rport_path][check_operation_path]["rport_runnable"].append(
                                    runnable_obj.get_path()
                                )
        return rport_info

    @classmethod
    def __update_swc_due_to_unmapped_runnable(cls, asw_dict):
        # DONOT use osapplication to judge because it is parsed from swc not the accessed runnable
        for swc in asw_dict.values():
            for pport in swc["pports"].values():
                if "Sender" not in pport["type"] and "Receiver" not in pport["type"]:
                    continue
                if not pport["task"]:
                    pport["task"] += cls.__do_recursion_to_find_task_in_unmapped_runnable(pport, asw_dict)
            for rport in swc["rports"].values():
                if "Client" not in rport["type"]:
                    continue
                if not rport["task"]:
                    rport["task"] += cls.__do_recursion_to_find_task_in_unmapped_runnable(rport, asw_dict)
        for swc in asw_dict.values():
            for pport in swc["pports"].values():
                if "Server" not in pport["type"]:
                    continue
                if not pport["connected_ports"]:
                    continue
                for conn_rport in pport["connected_ports"]["ports"]:
                    if conn_rport["task"]:
                        continue
                    try:
                        conn_rport["task"] = asw_dict[conn_rport["component"]]["rports"][conn_rport["name"]]["task"]
                    except Exception:
                        pass

    @classmethod
    def __do_recursion_to_find_task_in_unmapped_runnable(cls, port, asw_dict):
        task = []
        for runnable_path in port["runnable_path"]:
            # the unmapped runnable can only be the server runnable of direct call,
            # otherwise, it would be intercepted by validation.
            if runnable_path not in cls.server_runnable_connections:
                logger.error(f"Runnable <{runnable_path}> is either not mapped or not a server runnable!")
                continue
            for p_operation_path, p_operation_info in cls.server_runnable_connections[runnable_path].items():
                operation_name = p_operation_path.split("/")[-1]
                for cs_rport_path in p_operation_info["rport_info"].keys():
                    client_name = cs_rport_path.split("/")[-2]
                    rport_name = f'{cs_rport_path.split("/")[-1]}_{operation_name}'
                    try:
                        cs_rport = asw_dict[client_name]["rports"][rport_name]
                        add_task = cs_rport["task"]
                        if not add_task:
                            add_task = cls.__do_recursion_to_find_task_in_unmapped_runnable(cs_rport, asw_dict)
                        task += cs_rport["task"]
                    except Exception:
                        pass
        # the runnable of connected rport may also have no task since
        # it is accessed by another server runnable of direct call,
        # in this case, do recursion.
        # TODO
        return task

    @classmethod
    def get_sr_var_init_value(cls, datatype, init_value, ind=""):
        # return value are init_value and is_zero
        category = datatype["native_category"]
        if category == "NUMERICAL":
            basetype = datatype["basetype"]
            if basetype[0] == "b":
                # boolean
                if (
                    init_value.get("value", {}).get("value", "FALSE") == "TRUE"
                    or init_value.get("value", {}).get("value", "FALSE") == "True"
                    or init_value.get("value", {}).get("value", "FALSE") == "1"
                ):
                    return "TRUE", False, True
                else:
                    return "FALSE", True, True
            elif basetype[0] == "u":
                # unsigned
                if init_value.get("value", {}).get("value", "0U") in ["0U", "0ULL"]:
                    return init_value.get("value", {}).get("value", "0U"), True, False
                else:
                    return init_value.get("value", {}).get("value", "0U"), False, False
            elif basetype[0] == "s":
                # signed
                if init_value.get("value", {}).get("value", "0") == "0":
                    return init_value.get("value", {}).get("value", "0"), True, False
                else:
                    return init_value.get("value", {}).get("value", "0"), False, False
            elif basetype[0] == "f":
                # - float
                if init_value.get("value", {}).get("value", "0.0F") in ["0.0", "0.0F"]:
                    return init_value.get("value", {}).get("value", "0.0F"), True, False
                else:
                    return init_value.get("value", {}).get("value", "0.0F"), False, False
        elif category in {"STRUCTURE", "ARRAY", "UNION"}:
            if cls.are_all_elements_zero(init_value.get("value", {}).get("value", {})):
                return (
                    "{\n    "
                    + ind
                    + cls.__get_complex_datatype_member(
                        init_value.get("value", {}).get("value", {}), is_union=(category == "UNION")
                    )
                    + ind
                    + "\n}",
                    True,
                    False,
                )
            else:
                return (
                    "{\n    "
                    + ind
                    + cls.__get_complex_datatype_member(
                        init_value.get("value", {}).get("value", {}), is_union=(category == "UNION")
                    )
                    + ind
                    + "\n}",
                    False,
                    False,
                )
        return "", False, False

    @classmethod
    def __get_complex_datatype_member(cls, obj, is_union=False) -> str:
        if isinstance(obj, dict):
            ret = ""
            if is_union:
                ret += "{"

            size = len(obj)
            for i, sub in enumerate(obj.values()):
                if not isinstance(sub, dict):
                    ret += str(sub)
                else:
                    ret += "{" + cls.__get_complex_datatype_member(sub) + "}"
                if i != (size - 1):
                    ret += ","

            if is_union:
                ret += "}"
        elif isinstance(obj, list):
            ret = ""
            if is_union:
                ret += "{"

            size = len(obj)
            for i, sub in enumerate(obj):
                if not isinstance(sub, list):
                    ret += str(sub)
                else:
                    ret += "{" + cls.__get_complex_datatype_member(sub) + "}"
                if i != (size - 1):
                    ret += ","

            if is_union:
                ret += "}"
        else:
            ret = obj
        return ret

    @classmethod
    def are_all_elements_zero(cls, item):
        # 如果是字典，则递归检查每个键对应的值
        if isinstance(item, dict):
            return all(cls.are_all_elements_zero(value) for value in item.values())
        # 如果是列表或元组，则递归检查每个元素
        elif isinstance(item, list) or isinstance(item, tuple):
            return all(cls.are_all_elements_zero(elem) for elem in item)
        # 基本数据类型：直接检查是否为0
        else:
            return str(item).lower() in ["0", "0u", "0ull", "0.0", "0.0f", "false"]
