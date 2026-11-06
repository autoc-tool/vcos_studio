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
rte模板内函数定义模块.

定义jinja2模板中所使用的函数.

用法示例:
{{get_core_id_list()}}
"""

from jinja2 import pass_context

from basic_func_module.autosar_utils.utils import get_definition_ref, get_value
from func_module.generator.common.common import FunctionBase
from basic_func_module.autosar_utils.autosar_utils import AutosarUtils, MemmapCategory, VariableInitCategory


EVENT_TYPE = {
    "TimingEvent",
    "DataReceivedEvent",
    "BackgroundEvent",
    "OperationInvokedEvent",
    "SwcModeSwitchEvent",
    "ModeSwitchedAckEvent",
    "DataSendCompletedEvent",
    "DataWriteCompletedEvent",
    "AsynchronousServerCallReturnsEvent",
    "InternalTriggerOccurredEvent",
    "ExternalTriggerOccurredEvent",
}

"""显式SR接口代码实现形式类型"""
_UNCONNECT = 1
_FUNC = 2
_MACRO = 3


class Function(FunctionBase):
    """
    Class containing all functions. Add new static functions here
    to be included in the jinja2 context
    """

    @staticmethod
    @pass_context
    def get_appl_name_list(context):
        appl_name_list = context["appl_list"]
        appl_name_list.sort(key=lambda x: (len(x), x.lower()))
        return appl_name_list

    @staticmethod
    @pass_context
    def get_enable_module_list(context):
        return context["sys_cfg"].get("modules_info", {}).get("enabled_module_list", [])

    @staticmethod
    @pass_context
    def has_ack_flag_datatype(context, appl_list):
        for appl in appl_list:
            pport_list = Function.get_appl_task_mode_switch_port_list(context, appl)
            if len(pport_list) > 0:
                return True
        return False

    @staticmethod
    @pass_context
    def is_basic_task(context, task_name):
        task_info = context["task_mappings"][task_name]
        if task_info["task_type"] == "BASIC":
            return True
        return False

    @staticmethod
    @pass_context
    def get_cur_all_task_list(context):
        task_list = list(filter(lambda x: x["task_autostart"] != "TRUE", context["task_mappings"].values()))
        task_list = list(map(lambda x: x["task_name"], task_list))
        task_list.sort(key=lambda x: (len(x), x.lower()))
        return task_list

    @staticmethod
    def _filter_task_info(task_info):
        ret_task_info = {}
        ret_task_info["task_name"] = task_info["task_name"]
        ret_task_info["task_priority"] = task_info["task_priority"]
        ret_task_info["task_schedule"] = task_info["task_schedule"]
        return ret_task_info

    @staticmethod
    @pass_context
    def get_cur_appl_basic_task_without_st_list(context):
        # without schedule table
        task_list = list(
            filter(
                lambda x: x["task_autostart"] != "TRUE"
                and x["task_type"] == "BASIC"
                and len(x["schedule_table_list"]) == 0,
                context["task_mappings"].values(),
            )
        )
        task_list_without_st_list = list(
            filter(
                lambda x: x["task_autostart"] != "TRUE"
                and x["task_type"] == "BASIC"
                and len(x["schedule_table_list"]) > 0,
                context["task_mappings"].values(),
            )
        )
        if task_list_without_st_list:
            task_set = Function._get_task_set_with_same_period(task_list_without_st_list)
            task_list.extend(filter(lambda x: x["task_name"] in task_set, context["task_mappings"].values()))
        task_list = list(map(Function._filter_task_info, task_list))
        task_list.sort(key=lambda x: (len(x["task_name"]), x["task_name"].lower()))
        return task_list

    @staticmethod
    @pass_context
    def get_cur_appl_basic_task_with_st_list(context):
        # with schedule table
        task_list = list(
            filter(
                lambda x: x["task_autostart"] != "TRUE"
                and x["task_type"] == "BASIC"
                and len(x["schedule_table_list"]) > 0,
                context["task_mappings"].values(),
            )
        )
        task_set = Function._get_task_set_with_same_period(task_list)
        if task_set:
            task_list = list(filter(lambda x: x["task_name"] not in task_set, task_list))
        task_list = list(map(Function._filter_task_info, task_list))
        task_list.sort(key=lambda x: (len(x["task_name"]), x["task_name"].lower()))
        return task_list

    @staticmethod
    def _get_task_set_with_same_period(task_list):
        exp_point_list = [
            (sch_tbl["duration"], exp_point)
            for task in task_list
            for sch_tbl in task["schedule_table_list"]
            for exp_points in sch_tbl["expiry_point_dict"].values()
            for exp_point in exp_points
            if sch_tbl.get("repeat") or sch_tbl.get("repeating")
        ]
        excluded_task_set = set()
        task_period_offset = {}
        for duration, exp in exp_point_list:
            if isinstance(exp, int):
                continue
            if exp[0] > duration:
                excluded_task_set.add(exp[1]["task_name"])
            task_period_offset.setdefault(exp[1]["task_name"], set()).add(exp[1]["runnable_period"])
        task_set = set(dict(filter(lambda x: len(x[1]) == 1, task_period_offset.items())))
        task_set.difference_update(excluded_task_set)
        return task_set

    @staticmethod
    @pass_context
    def get_cur_appl_extended_task_list(context):
        task_list = list(
            filter(
                lambda x: x["task_autostart"] != "TRUE" and x["task_type"] == "EXTENDED",
                context["task_mappings"].values(),
            )
        )
        task_list = list(map(Function._filter_task_info, task_list))
        task_list.sort(key=lambda x: (len(x["task_name"]), x["task_name"].lower()))
        return task_list

    @staticmethod
    @pass_context
    def get_event_masks_with_type_conversion(context, event_list):
        length = len(event_list)
        if length == 0:
            return ""
        elif length == 1:
            return "(EventMaskType) " + str(event_list[0]).upper()
        else:
            ret_str = ""
            index = 0
            for evt in event_list:
                ret_str = ret_str + "((EventMaskType) " + str(evt).upper() + ")"
                if index < length - 1:
                    ret_str = ret_str + " | "
                index = index + 1
            return ret_str

    @staticmethod
    @pass_context
    def get_module_header_file_list(context):
        header_file_set = set()
        bsw_instances = context.get("bsw_instances", {})
        for task_mapping in context["task_mappings"].values():
            schedulable_entities = task_mapping["schedulable_entity"]
            for schedulable_entity in schedulable_entities.values():
                if not schedulable_entity.get("is_bsw", False) or schedulable_entity["component"] == "Rte":
                    continue
                component = schedulable_entity["component"]
                symbol = bsw_instances.get(component, {}).get("symbol") or component
                header_file_set.add(symbol)
        header_file_list = sorted(header_file_set, key=lambda x: (len(x), x.lower()))
        return header_file_list

    @staticmethod
    @pass_context
    def get_all_wait_event_mask_list(context, task_name):
        wait_event_mask_set = set()
        runnable_dict = context["task_mappings"][task_name]["schedulable_entity"]
        for runnable in runnable_dict.values():
            for event in runnable["os_event"]:
                if event in {"InitEvent", "BackgroundEvent"}:
                    continue
                wait_event_mask_set.add(event)
        wait_event_mask_list = list(wait_event_mask_set)
        if wait_event_mask_set is not None:
            wait_event_mask_list.sort(key=lambda x: (len(x), x.lower()))
        return wait_event_mask_list

    @staticmethod
    @pass_context
    def only_background_event(context, task_name):
        runnable_dict = context["task_mappings"][task_name]["schedulable_entity"]
        if len(runnable_dict) == 0:
            return False
        for runnable in runnable_dict.values():
            for event in runnable["os_event"]:
                if event != "BackgroundEvent":
                    return False
        return True

    @staticmethod
    @pass_context
    def __has_has_mode_disabling_in_asw_dict(context, runnable):
        run_name = runnable["name"]
        return (
            run_name in context["runnables_dict"]
            and "has_mode_disbaling" in context["runnables_dict"][run_name]
            and context["runnables_dict"][run_name]["has_mode_disbaling"]
        )

    @staticmethod
    @pass_context
    def get_runnable_groups(context, task_name):
        runnable_groups, supported_event_list = [], EVENT_TYPE
        runnables = list(context["task_mappings"][task_name]["schedulable_entity"].values())
        runnables.sort(key=lambda runnable: runnable["position_in_task"])
        runnable_dict, prev_mask = {}, None
        for runnable in runnables:
            cur_mask = Function._get_cur_mask(supported_event_list, runnable)
            has_mode_disabling = (
                "mode_disabling_info" in runnable
                and bool(runnable["mode_disabling_info"])
                and Function.__has_has_mode_disabling_in_asw_dict(context, runnable)
            )
            if cur_mask is None:
                continue
            if prev_mask is None:
                runnable_dict = {
                    "mask": cur_mask,
                    "entity": [runnable["name"]],
                    "has_mode_disabling": has_mode_disabling,
                }
                if not has_mode_disabling:
                    prev_mask = cur_mask
                else:
                    prev_mask = None
                    runnable_dict["disabling_flag"] = (
                        f"Rte_Flag_ModeDisableTrigger_{runnable['mode_disabling_info'][0]['osa']}."
                        f"Rte_Flag_ModeDisableTrigger_{runnable['component']}_{runnable['name']}"
                    )
                    runnable_groups.append(runnable_dict)
            elif has_mode_disabling:
                runnable_groups.append(runnable_dict)
                runnable_groups.append(
                    {
                        "mask": cur_mask,
                        "entity": [runnable["name"]],
                        "has_mode_disabling": has_mode_disabling,
                        "disabling_flag": f"Rte_Flag_ModeDisableTrigger_{runnable['mode_disabling_info'][0]['osa']}."
                        f"Rte_Flag_ModeDisableTrigger_{runnable['component']}_{runnable['name']}",
                    }
                )
                prev_mask = None
            elif prev_mask == cur_mask:
                runnable_dict["entity"].append(runnable["name"])
            else:
                runnable_groups.append(runnable_dict)
                runnable_dict = {
                    "mask": cur_mask,
                    "entity": [runnable["name"]],
                    "has_mode_disabling": has_mode_disabling,
                    "disabling_flag": None,
                }
                prev_mask = cur_mask
        if runnable_dict and prev_mask:
            runnable_groups.append(runnable_dict)
        return runnable_groups

    @staticmethod
    def _get_cur_mask(supported_event_list, runnable):
        os_event_list = list(runnable["os_event"].keys())
        if len(os_event_list) == 1 and runnable["os_event"][os_event_list[0]]["event_type"] in supported_event_list:
            if "BackgroundEvent" == os_event_list[0]:
                cur_mask = "BackgroundEvent"
            else:
                cur_mask = f"(EventMaskType){os_event_list[0].upper()}"
        else:
            mask_list = []
            for event in os_event_list:
                if runnable["os_event"][event]["event_type"] not in supported_event_list:
                    continue
                mask_list.append(event.upper())
            if len(mask_list) == 0:
                return None
            mask_list.sort(key=lambda x: (len(x), x.lower()))
            cur_mask = "((EventMaskType)" + " | (EventMaskType)".join(mask_list) + ")"
        return cur_mask

    @staticmethod
    @pass_context
    def get_init_event_runnable_list(context, task_name):
        runnable_list = []
        runnables = list(context["task_mappings"][task_name]["schedulable_entity"].values())
        runnables.sort(key=lambda runnable: runnable["position_in_task"])
        for runnable in runnables:
            for event_info in runnable["os_event"].values():
                if event_info["event_type"] == "InitEvent":
                    runnable_list.append(runnable["name"])
        return runnable_list

    @staticmethod
    @pass_context
    def get_timing_event_runnable_list(context, task_name, period):
        runnable_list = []
        runnables = list(context["task_mappings"][task_name]["schedulable_entity"].values())
        runnables.sort(key=lambda runnable: runnable["position_in_task"])
        for runnable in runnables:
            for event_info in runnable["os_event"].values():
                if event_info["event_type"] == "TimingEvent" and runnable["period"] == period:
                    runnable_list.append(runnable["name"])
        return runnable_list

    @staticmethod
    @pass_context
    def is_init_schedule_table(context, task_name):
        result = False
        for schedule_table in context["task_to_st_dict"][task_name]:
            if schedule_table["name"].startswith("Init"):
                result = True
                break
        return result

    @staticmethod
    @pass_context
    def get_schedule_table_name(context, task_name):
        init_sch_tbl_name, main_sch_tbl_name = "", ""
        for schedule_table in context["task_to_st_dict"][task_name]:
            if schedule_table.get("repeat") or schedule_table.get("repeating"):
                main_sch_tbl_name = schedule_table["name"].upper()
            else:
                init_sch_tbl_name = schedule_table["name"].upper()
        return init_sch_tbl_name, main_sch_tbl_name

    @staticmethod
    @pass_context
    def get_schedule_table_step_info(context, task_name):
        step_info = {"step_list": [], "step_cycle_start": 0}
        step_list = []
        init_step_list = []
        main_step_list = []
        step_cycle_start = 0
        for schedule_table in context["task_mappings"][task_name]["schedule_table_list"]:
            if not schedule_table["code_gen"]:
                continue

            if schedule_table["name"].startswith("Init"):
                init_step_list.extend(schedule_table["step_dict"].values())
                step_cycle_start = len(init_step_list)
            else:
                main_step_list.extend(schedule_table["step_dict"].values())
        step_list = init_step_list + main_step_list
        step_info.update({"step_list": step_list})
        step_info.update({"step_cycle_start": step_cycle_start})

        return step_info

    @staticmethod
    @pass_context
    def get_server_runnable_list(context, server_swc_name):
        swc = context["server_swc"][server_swc_name]
        runnable_list = []
        for runnable in swc["runnable_list"]:
            args_list, return_value, server_runnable = [], None, {}
            server_runnable["name"] = runnable["runnable_entity_name"]
            if runnable["event_type"] == "TimingEvent":
                args_list.append("void")
                return_value = "void"
            elif runnable["event_type"] == "OperationInvokedEvent":
                return_value = "Std_ReturnType"
                for arg in runnable["args"]:
                    if arg["direction"] == "IN":
                        args_list.append(f"{arg['type']} {arg['name']}")
                    elif arg["direction"] == "OUT" or arg["direction"] == "INOUT":
                        args_list.append(f"{arg['type']} *{arg['name']}")
            server_runnable["args_list"] = args_list
            server_runnable["return_value"] = return_value
            runnable_list.append(server_runnable)
        return runnable_list

    @staticmethod
    @pass_context
    def get_ordered_datatype_dict(context):
        return context["datatypes"]

    @staticmethod
    @pass_context
    def get_idt_constraint_list(context):
        constr_list = []
        for idt in context["datatypes"].values():
            if not idt["constraint"]:
                continue
            constr = idt["constraint"]
            if idt["basetype"][0] == "u":
                constr_list.append(
                    {
                        "idt_name": idt["name"],
                        "max_shown": f'{int(float(constr["max"]))}U',
                        "min_shown": f'{int(float(constr["min"]))}U',
                    }
                )
            elif idt["basetype"][0] == "f":
                constr_list.append(
                    {"idt_name": idt["name"], "max_shown": f'{constr["max"]}F', "min_shown": f'{constr["min"]}F'}
                )
            # TODO
        constr_list.sort(key=lambda x: ("args" in x.keys(), x["idt_name"].lower()))
        return constr_list

    @staticmethod
    @pass_context
    def get_swc_adt_constraint_list(context):
        constr_list = []
        if "constraints" not in context["swc"]:
            return constr_list
        for constr in context["swc"]["constraints"].values():
            if constr["basetype"][0] == "u":
                constr_list.append(
                    {
                        "adt_name": constr["adt_name"],
                        "max_shown": f'{int(float(constr["max"]))}U',
                        "min_shown": f'{int(float(constr["min"]))}U',
                    }
                )
            elif constr["basetype"][0] == "f":
                constr_list.append(
                    {"adt_name": constr["adt_name"], "max_shown": f'{constr["max"]}F', "min_shown": f'{constr["min"]}F'}
                )
            elif constr["basetype"][0] == "s":
                constr_list.append(
                    {
                        "adt_name": constr["adt_name"],
                        "max_shown": f'{int(float(constr["max"]))}',
                        "min_shown": f'{int(float(constr["min"]))}',
                    }
                )
            else:
                # TODO
                pass
        constr_list.sort(key=lambda x: ("args" in x.keys(), x["adt_name"].lower()))
        return constr_list

    @staticmethod
    @pass_context
    def get_com_signal_compu_method_list(context, osa):
        cm_list = []
        cm_set = set()
        for _, cm in context.get("sr_dm_glob_vars", {}).get("macro", {}).get("compu_method", {}).get(osa, {}).items():
            if cm["category"] not in {"TEXTTABLE", "BITFIELD_TEXTTABLE"}:
                continue
            for key, value in cm["value"].items():
                if key in cm_set:
                    continue
                cm_set.add(key)
                cm_list.append({key: value})
        return cm_list

    @staticmethod
    @pass_context
    def get_swc_adt_compu_method_list(context):
        compu_method_list = []
        service_module_list = [
            "ComM_swc",
            "Dcm_swc",
            "WdgM_swc",
            "Dem_swc",
            "Det_swc",
            "EcuM_swc",
            "NvM_swc",
            "StbM_swc",
            "Csm_swc",
            "BswM_swc",
        ]
        if "compu_methods" not in context["swc"] or context["swc"]["compu_methods"]["adt"] == {}:
            return compu_method_list
        for adt_path, compu_method in context["swc"]["compu_methods"]["adt"].items():
            if any(element in adt_path for element in service_module_list):
                continue  # exclude for service swc
            if compu_method["category"] == "TEXTTABLE":
                for key, value in compu_method["value"].items():
                    compu_method_list.append({key: value})
            elif compu_method["category"] == "BITFIELD_TEXTTABLE":
                for key, value in compu_method["value"].items():
                    if key.endswith("_BflMask") or key.endswith("_BflPn") or key.endswith("_BflLn"):
                        continue
                    compu_method_list.append({key: value})
        # compu_method_list.sort(key=lambda x: (list(x.keys())[0].lower()))
        return compu_method_list

    @staticmethod
    @pass_context
    def get_swc_idt_compu_method_list(context):
        compu_method_list = []
        key_set = set()
        # BswM_swc/StbM_swc是用户自定义的，可以生成
        service_module_list = [
            "ComM_swc",
            "Dcm_swc",
            "WdgM_swc",
            "Dem_swc",
            "Det_swc",
            "EcuM_swc",
            "NvM_swc",
            "Csm_swc",
        ]
        if "compu_methods" not in context["swc"] or context["swc"]["compu_methods"]["idt"] == {}:
            return compu_method_list
        for adt_path, compu_method in context["swc"]["compu_methods"]["idt"].items():
            if any(element in adt_path for element in service_module_list):
                continue  # exclude for service swc
            if compu_method["category"] == "TEXTTABLE":
                for key, value in compu_method["value"].items():
                    if key in key_set:
                        continue
                    compu_method_list.append({key: value})
                    key_set.add(key)
            elif compu_method["category"] == "BITFIELD_TEXTTABLE":
                for key, value in compu_method["value"].items():
                    if key in key_set:
                        continue
                    compu_method_list.append({key: value})
                    key_set.add(key)
        # compu_method_list.sort(key=lambda x: (list(x.keys())[0].lower()))
        return compu_method_list

    @staticmethod
    def _get_variable_of_prprot_connection(port):
        variable = None
        if port["is_prport"] and port["m_to_n"] == "0":
            variable = f'Rte_{port["sort_name"]}'
        else:
            variable_set = set()
            for _port in port["sr_port_group"]:
                if not _port["is_prport"]:
                    continue
                variable_set.add(_port["sort_name"])
            variable = f"Rte_{sorted(list(variable_set))[0]}"
        return variable

    @staticmethod
    def _pack_sr_explicit_pport_with_prport(pport):
        pport_dict = {}
        struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(pport)
        buff_struct_type = struct_type
        buff_struct_name = struct_name
        pport_dict.update(
            {
                "sort_name": pport["sort_name"],
                "name": pport["name"],
                "type": pport["type"],
                "datatype": pport["arg"]["datatype"]["name"],
                "variable": Function._get_variable_of_prprot_connection(pport),
                # NOTE, only works in the scenario of all ports connected with PR-Port in the same os application
                "var_osa": pport["osapplication"],
                "core_id": pport["core_id"],
                "arg": pport["arg"],
                "buff_memmap_category": pport["buff_memmap_category"],
                "lock": pport.get("lock", "NONE"),
                "set_events": pport.get("set_events", []),
                "has_prport": pport["has_prport"],
                "enable_update": pport["enable_update"],
                "signal_category": pport.get("signal_category", "None"),
                "runnable": pport["symbol"],
                "m_to_n": pport["m_to_n"],
                "intra_osa": pport.get("intra_osa", False),
                "buff_struct_type": buff_struct_type,
                "buff_struct_name": buff_struct_name,
            }
        )
        return pport_dict

    @staticmethod
    def _pack_sr_explicit_rport_with_prport(rport):
        rport_dict = {}
        struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(rport)
        buff_struct_type = struct_type
        buff_struct_name = struct_name
        rport_dict.update(
            {
                "sort_name": rport["sort_name"],
                "name": rport["name"],
                "type": rport["type"],
                "datatype": rport["arg"]["datatype"]["name"],
                "variable": Function._get_variable_of_prprot_connection(rport),
                "read_by_value": rport["read_by_value"],
                # NOTE, only works in the scenario of all ports connected with PR-Port in the same os application
                "var_osa": rport["osapplication"],
                "core_id": rport["core_id"],
                "arg": rport["arg"],
                "buff_memmap_category": rport["buff_memmap_category"],
                "lock": rport.get("lock", "NONE"),
                "has_prport": rport["has_prport"],
                "enable_update": rport["enable_update"],
                "signal_category": rport.get("signal_category", "None"),
                "runnable": rport["symbol"],
                "m_to_n": rport["m_to_n"],
                "intra_osa": rport.get("intra_osa", False),
                "buff_struct_type": buff_struct_type,
                "buff_struct_name": buff_struct_name,
            }
        )
        return rport_dict

    @staticmethod
    def _pack_sr_explicit_pport_without_prport(pport):
        variable = ""
        single_rec_buff_for_n1 = None
        buff_category = None
        counter_category = None
        local_counter = None
        global_counter = None
        buff_struct_type = None
        buff_struct_name = None
        sender_buff_struct_type = []
        sender_buff_struct_name = []
        if pport["m_to_n"] == "n1":
            # N:1
            rport = pport["conn_asw_ports"][0]
            single_rec_buff_for_n1 = pport["single_rec_buff_for_n1"]
            if single_rec_buff_for_n1:
                variable = "Rte_" + rport["swc_port_var"]
                struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(rport)
                buff_struct_type = struct_type
                buff_struct_name = struct_name
            else:
                variable = "Rte_" + pport["swc_port_var"]
                buff_category = pport["buff_category"]
                local_counter = "Rte_Counter_Sr_Local_" + pport["swc_port_var"]
                global_counter = "Rte_Counter_Sr_Global_" + rport["swc_port_var"]
                counter_category = pport["counter_category"]
                struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(pport)
                sender_buff_struct_type.append(struct_type)
                sender_buff_struct_name.append(struct_name)
        else:
            # 1:1 / 1:N
            variable = "Rte_" + pport["swc_port_var"]
            buff_category = pport["buff_category"]
            struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(pport)
            buff_struct_type = struct_type
            buff_struct_name = struct_name

        port_dict = {
            "sort_name": pport["sort_name"],
            "name": pport["name"],
            "type": pport["type"],
            "arg": pport["arg"],
            "datatype": pport["arg"]["datatype"]["name"],
            "variable": variable,
            "local_counter": local_counter,
            "global_counter": global_counter,
            "set_events": pport["set_events"],
            "lock": pport["lock"],
            "var_osa": pport["osapplication"],
            "m_to_n": pport["m_to_n"],
            "single_rec_buff_for_n1": single_rec_buff_for_n1,
            "buff_category": buff_category,
            "buff_memmap_category": pport["buff_memmap_category"],
            "core_id": pport["core_id"],
            "counter_category": counter_category,
            "has_prport": pport["has_prport"],
            "enable_update": pport["enable_update"],
            "signal_category": pport["signal_category"],
            "runnable": pport["symbol"],
            "intra_osa": pport.get("intra_osa", False),
            "dm_macro_api": pport.get("dm_macro_api", False),
            "mapping_to_signals": pport.get("mapping_to_signals", []),
            "buff_struct_type": buff_struct_type,
            "buff_struct_name": buff_struct_name,
            "sender_buff_struct_type": sender_buff_struct_type,
            "sender_buff_struct_name": sender_buff_struct_name,
        }
        return port_dict

    @staticmethod
    def _pack_sr_explicit_rport_without_prport(rport):
        single_rec_buff_for_n1 = None
        buff_category = None
        counter_category = None
        global_counter = None
        all_sender_buffer = []
        all_sender_counter = []
        variable = None
        buff_struct_type = None
        buff_struct_name = None
        sender_buff_struct_type = []
        sender_buff_struct_name = []
        if rport["m_to_n"] in {"0", "mn"}:
            # datamapping
            var_osa = rport["osapplication"]
            port_for_data_type = rport
        elif rport["m_to_n"] == "n1":
            # N:1
            variable = "Rte_" + rport["swc_port_var"]
            single_rec_buff_for_n1 = rport["single_rec_buff_for_n1"]
            buff_category = rport["buff_category"]
            struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(rport)
            buff_struct_type = struct_type
            buff_struct_name = struct_name
            if not single_rec_buff_for_n1:
                counter_category = rport["counter_category"]
                global_counter = "Rte_Counter_Sr_Global_" + rport["swc_port_var"]
                for pport in rport["conn_asw_ports"]:
                    all_sender_buffer.append(("Rte_" + pport["swc_port_var"], pport["osapplication"]))
                    all_sender_counter.append(("Rte_Counter_Sr_Local_" + pport["swc_port_var"], pport["osapplication"]))
                    struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(pport)
                    sender_buff_struct_type.append(struct_type)
                    sender_buff_struct_name.append(struct_name)
            var_osa = rport["osapplication"]
            port_for_data_type = rport
        else:
            # 1:1 / 1:N
            pport = rport["conn_asw_ports"][0]
            variable = "Rte_" + pport["swc_port_var"]
            var_osa = pport["osapplication"]
            port_for_data_type = pport
            struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(pport)
            buff_struct_type = struct_type
            buff_struct_name = struct_name
        rport_dict = {
            "sort_name": rport["sort_name"],
            "name": rport["name"],
            "type": rport["type"],
            "arg": rport["arg"],
            "datatype": port_for_data_type["arg"]["datatype"]["name"],
            "variable": variable,
            "global_counter": global_counter,
            "all_sender_buffer": all_sender_buffer,
            "all_sender_counter": all_sender_counter,
            "read_by_value": rport["read_by_value"],
            "lock": rport["lock"],
            "var_osa": var_osa,
            "m_to_n": rport["m_to_n"],
            "buff_category": buff_category,
            "buff_memmap_category": rport["buff_memmap_category"],
            "single_rec_buff_for_n1": single_rec_buff_for_n1,
            "core_id": rport["core_id"],
            "counter_category": counter_category,
            "has_prport": rport["has_prport"],
            "enable_update": rport["enable_update"],
            "signal_category": rport["signal_category"],
            "runnable": rport["symbol"],
            "intra_osa": rport.get("intra_osa", False),
            "dm_macro_api": rport.get("dm_macro_api", False),
            "mapping_to_signals": rport.get("mapping_to_signals", []),
            "buff_struct_type": buff_struct_type,
            "buff_struct_name": buff_struct_name,
            "sender_buff_struct_type": sender_buff_struct_type,
            "sender_buff_struct_name": sender_buff_struct_name,
        }
        return rport_dict

    @staticmethod
    def _get_swc_sr_explicit_connected_pport_list(swc):
        pport_list = []
        for pport in swc["pports"].values():
            if pport["type"] != "Explicit Sender":
                continue
            if pport["has_prport"]:
                pport_list.append(Function._pack_sr_explicit_pport_with_prport(pport))
            else:
                if Function.get_sr_explicit_rte_interface_code_format(pport) == _UNCONNECT:
                    continue
                pport_list.append(Function._pack_sr_explicit_pport_without_prport(pport))
        return pport_list

    @staticmethod
    def _get_swc_sr_explicit_connected_rport_list(swc):
        rport_list = []
        for rport in swc["rports"].values():
            if rport["type"] != "Explicit Receiver":
                continue
            if rport["has_prport"]:
                rport_list.append(Function._pack_sr_explicit_rport_with_prport(rport))
            else:
                if Function.get_sr_explicit_rte_interface_code_format(rport) == _UNCONNECT:
                    continue
                rport_list.append(Function._pack_sr_explicit_rport_without_prport(rport))
        return rport_list

    @staticmethod
    def _get_swc_sr_explicit_unconnected_rport_list(swc):
        rport_list = []
        for rport in swc["rports"].values():
            if rport["type"] != "Explicit Receiver":
                continue
            if Function.get_sr_explicit_rte_interface_code_format(rport) == _UNCONNECT:
                rport_list.append(
                    {
                        "sort_name": rport["sort_name"],
                        "name": rport["name"],
                        "type": rport["type"],
                        "read_by_value": rport["read_by_value"],
                        "arg": {"datatype": rport["arg"]["datatype"], "init_value": rport["arg"]["init_value"]},
                        "runnable": rport["symbol"],
                    }
                )
        return rport_list

    @staticmethod
    @pass_context
    def not_port_accessed_runnable(port, runnable=None):
        # runnable not in the port accessed runnable list
        rv = False
        if "symbol" in port:
            if runnable and runnable not in port["symbol"]:
                rv = True
            else:
                rv = False
        elif "runnable" in port:
            if runnable and runnable not in port["runnable"]:
                rv = True
            else:
                rv = False
        return rv

    @staticmethod
    @pass_context
    def get_swc_sr_explicit_unconnected_render_pport_list(context, runnable=None):
        port_list = []
        for pport in context["swc"]["pports"].values():
            if Function.not_port_accessed_runnable(pport, runnable):
                continue
            if pport["type"] != "Explicit Sender":
                continue
            if Function.get_sr_explicit_rte_interface_code_format(pport) == _UNCONNECT:
                port_list.append(
                    {
                        "sort_name": pport["sort_name"],
                        "name": pport["name"],
                        "runnable": pport["symbol"],
                        "datatype": pport["arg"]["datatype"],
                    }
                )
        port_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return port_list

    @staticmethod
    @pass_context
    def get_swc_sr_explicit_unconnected_render_rport_list(context, runnable=None):
        rport_list = []
        rport_list_origin = Function._get_swc_sr_explicit_unconnected_rport_list(context["swc"])
        if runnable:
            for rport in rport_list_origin:
                if Function.not_port_accessed_runnable(rport, runnable):
                    continue
                rport_list.append(rport)
        else:
            rport_list = rport_list_origin
        rport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rport_list

    @staticmethod
    @pass_context
    def get_swc_sr_explicit_macro_render_pport_list(context, runnable=None):
        pport_list = []
        for pport in Function._get_swc_sr_explicit_connected_pport_list(context["swc"]):
            if Function.not_port_accessed_runnable(pport, runnable):
                continue
            if Function.get_sr_explicit_rte_interface_code_format(pport) == _MACRO:
                pport_list.append(pport)
        pport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return pport_list

    @staticmethod
    @pass_context
    def _update_struct_datatype_and_name_of_boolean_buff(port):
        struct_type = None
        struct_name = None
        appl_name = port["var_osa"] if "var_osa" in port else port["osapplication"]
        if (port.get("buff_category", None) == "intra_osa" or port.get("intra_osa", False)) and port["arg"][
            "init_value"
        ]["is_bool"]:
            # 当前只优化同分区内的buffer
            if port["arg"]["init_value"]["is_zero_init"]:
                struct_type = f"Rte_Private_{appl_name}_ZeroBool_VarType"
                struct_name = f"Rte_Private_{appl_name}_ZeroBool_Vars"
            else:
                struct_type = f"Rte_Private_{appl_name}_NonZeroBool_VarType"
                struct_name = f"Rte_Private_{appl_name}_NonZeroBool_Vars"
        return struct_type, struct_name

    @staticmethod
    @pass_context
    def get_swc_sr_explicit_macro_render_rport_list(context, runnable=None):
        rport_list = []
        for rport in Function._get_swc_sr_explicit_connected_rport_list(context["swc"]):
            if Function.not_port_accessed_runnable(rport, runnable):
                continue
            if Function.get_sr_explicit_rte_interface_code_format(rport) == _MACRO:
                rport_list.append(rport)
        rport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rport_list

    @staticmethod
    @pass_context
    def get_swc_sr_explicit_variable_dict_by_appl(context):

        def __get_memmap_infix(port):
            init_infix = port["arg"]["init_value"]["init_category"].value
            if port["buff_memmap_category"] == MemmapCategory.OSA_PRIVATE:
                return f"{port['var_osa']}_PRIVATE_{init_infix}"
            elif port["buff_memmap_category"] == MemmapCategory.OSA_SHARED:
                return f"{port['var_osa']}_SEMISHARED_{init_infix}"
            elif port["buff_memmap_category"] == MemmapCategory.CORE_SHARED:
                return f"CORE{port['core_id']}_SEMISHARED_{init_infix}"
            elif port["buff_memmap_category"] == MemmapCategory.GLOBAL:
                return f"MULTI_APP_{init_infix}"
            else:
                return None

        variable_dict = {}
        sort_variable_dict = {}
        for port in Function.get_swc_sr_explicit_macro_render_pport_list(
            context
        ) + Function.get_swc_sr_explicit_macro_render_rport_list(context):
            # exclude multi-access of one portprototy in one swc
            if port.get("dm_macro_api", False) is True:
                continue  # datamapping macro api do not need to be generated variable
            memmap_infix = __get_memmap_infix(port)
            if memmap_infix not in variable_dict:
                variable_dict[memmap_infix] = {}
            variable_dict[memmap_infix][port["variable"]] = {
                "datatype": port["arg"]["datatype"]["name"],
                "var_osa": port["var_osa"],
                "variable": port["variable"],
                "arg": port["arg"],
                "memmap_infix": memmap_infix,
                "is_zero_init": port["arg"]["init_value"]["is_zero_init"],
                "buff_struct_type": port.get("buff_struct_type", None),
                "buff_struct_name": port.get("buff_struct_name", None),
            }
        for memmap_infix, vars in variable_dict.items():
            sort_variable_dict[memmap_infix] = dict(sorted(vars.items()))
        return dict(sorted(sort_variable_dict.items()))

    @staticmethod
    @pass_context
    def rte_swc_need_include_com(context):
        for port in Function.get_swc_sr_explicit_macro_render_pport_list(
            context
        ) + Function.get_swc_sr_explicit_macro_render_rport_list(context):
            if port.get("dm_macro_api", False) is True:
                return True
        return False

    @staticmethod
    @pass_context
    def get_nv_explicit_api_pport_list_from_all_swc(context):
        # used for core0.c
        nv_pport_list = []
        for swc_dict in context["asw_cfg"].values():
            for port in swc_dict["pports"].values():
                if port["type"] == "Explicit Nv Sender" and port["nv_block_data_mapping"]["dirty_flag"] == "False":
                    nv_pport_list.append(port)
        return nv_pport_list

    @staticmethod
    @pass_context
    def get_nv_explicit_api_pport_list(context):
        nv_pport_list = []
        swc_dict = context["swc"]
        for port in swc_dict["pports"].values():
            if port["type"] == "Explicit Nv Sender":
                nv_pport_list.append(port)
        return nv_pport_list

    @staticmethod
    @pass_context
    def get_nv_explicit_api_pport_list_with_dirtflag_from_swc_list(context):
        nv_pport_list = []
        for swc_dict in context["asw_cfg"].values():
            if swc_dict["type"] == "NvBlockComponent":
                continue
            for port in swc_dict["pports"].values():
                if port["type"] == "Explicit Nv Sender" and port["nv_block_data_mapping"]["dirty_flag"]:
                    nv_pport_list.append(port)
        return nv_pport_list

    @staticmethod
    @pass_context
    def _get_appl_sr_unqueued_variable_dict(context, appl_name=None):
        """未使用接口"""
        visited = set()
        variables = []
        ports = []
        for swc in context["asw_cfg"].values():
            if appl_name is not None and swc["osapplication"] == appl_name:
                ports += Function._get_swc_sr_explicit_connected_pport_list(swc)
                ports += Function._get_swc_sr_explicit_connected_rport_list(swc)
                ports += Function._get_swc_sr_implicit_all_pport_list(swc)
                ports += Function._get_swc_sr_implicit_all_rport_list(swc)
            elif appl_name is None:
                ports += Function._get_swc_sr_explicit_connected_pport_list(swc)
                ports += Function._get_swc_sr_explicit_connected_rport_list(swc)
                ports += Function._get_swc_sr_implicit_all_pport_list(swc)
                ports += Function._get_swc_sr_implicit_all_rport_list(swc)
        for port in ports:
            if port["variable"] == "":
                if port["global_counter"] in visited:
                    continue
                else:
                    visited.add(port["global_counter"])
            elif port["variable"] in visited:
                continue
            else:
                visited.add(port["variable"])
            variables.append(port)
        return variables

    @staticmethod
    @pass_context
    def get_appl_sr_unqueued_counters_definition(context, appl_name):
        visited_counters = set()
        counters = {
            "local": {"intra_osa": [], "inter_osa_same_core": [], "inter_core": []},
            "global": {"inter_osa_same_core": [], "inter_core": []},
        }
        pports = []
        rports = []
        for swc in context["asw_cfg"].values():
            if swc["osapplication"] == appl_name:
                pports += Function._get_swc_sr_explicit_connected_pport_list(swc)
                pports += Function._get_swc_sr_implicit_all_pport_list(swc)
                rports += Function._get_swc_sr_explicit_connected_rport_list(swc)
                rports += Function._get_swc_sr_implicit_all_rport_list(swc)
        if not (pports or rports):
            return counters
        for port in pports:
            if port["has_prport"]:
                continue
            if port["m_to_n"] != "n1" or port["single_rec_buff_for_n1"]:
                continue
            l_cnt = port["local_counter"]
            if l_cnt in visited_counters:
                continue
            else:
                visited_counters.add(l_cnt)
            counters["local"][port["counter_category"]].append(l_cnt)
        for port in rports:
            if port["has_prport"]:
                continue
            if port["m_to_n"] != "n1" or port["single_rec_buff_for_n1"]:
                continue
            g_cnt = port["global_counter"]
            if g_cnt in visited_counters:
                continue
            else:
                visited_counters.add(g_cnt)
            counters["global"][port["counter_category"]].append(g_cnt)
        counters["local"]["intra_osa"].sort()
        counters["local"]["inter_osa_same_core"].sort()
        counters["local"]["inter_core"].sort()
        counters["global"]["inter_osa_same_core"].sort()
        counters["global"]["inter_core"].sort()
        return counters

    @staticmethod
    @pass_context
    def get_appl_sr_unqueued_counters_extern(context, appl_name=None):
        visited_counters = set()
        local_counters = {}
        global_counters = []
        rports = []
        pports = []
        for swc in context["asw_cfg"].values():
            if appl_name:
                if swc["osapplication"] == appl_name:
                    rports += Function._get_swc_sr_explicit_connected_rport_list(swc)
                    rports += Function._get_swc_sr_implicit_all_rport_list(swc)
                    pports += Function._get_swc_sr_explicit_connected_pport_list(swc)
                    pports += Function._get_swc_sr_implicit_all_pport_list(swc)
            else:
                rports += Function._get_swc_sr_explicit_connected_rport_list(swc)
                rports += Function._get_swc_sr_implicit_all_rport_list(swc)
                pports += Function._get_swc_sr_explicit_connected_pport_list(swc)
                pports += Function._get_swc_sr_implicit_all_pport_list(swc)
        for port in rports:
            if port["has_prport"]:
                continue
            # TODO: exclude rport which is the same application as connected pport
            if port["m_to_n"] != "n1" or port["single_rec_buff_for_n1"]:
                continue
            if port["all_sender_counter"][0][0] in visited_counters:
                continue
            else:
                for counter, osa in port["all_sender_counter"]:
                    visited_counters.add(counter)
                    if osa not in local_counters:
                        local_counters[osa] = []
                    local_counters[osa].append(counter)
        for port in pports:
            if port["has_prport"]:
                continue
            if port["m_to_n"] != "n1" or port["single_rec_buff_for_n1"]:
                continue
            if port["global_counter"] in visited_counters:
                continue
            else:
                visited_counters.add(port["global_counter"])
                global_counters.append(port["global_counter"])

        for _, cnts in local_counters.items():
            cnts.sort()
        global_counters.sort()
        return global_counters, dict(sorted(local_counters.items()))

    @staticmethod
    def __get_sr_nonqueue_pport_defined_variable_by_swc(swc, filter=None):
        """
        currently:
            most variables are defined by P-Port
            ONLY for N:1 scenario, there may exist variables defined by R-Port
        """
        variables = {}
        for pport in Function._get_swc_sr_explicit_connected_pport_list(
            swc
        ) + Function._get_swc_sr_implicit_all_pport_list(swc):
            if pport["has_prport"]:
                if not filter or filter == MemmapCategory.OSA_PRIVATE:
                    pass
                else:
                    continue
            else:
                if pport["m_to_n"] in {"0", "mn"}:
                    continue
                if pport["m_to_n"] == "n1" and pport["single_rec_buff_for_n1"]:
                    continue
                if not filter and pport["buff_category"]:
                    pass
                elif filter != pport["buff_memmap_category"]:
                    continue
            # exclude multi-access in one swc, for example Write+IWrite
            variables.update({pport["variable"]: pport})
        return variables

    @staticmethod
    def __get_sr_nonqueue_rport_defined_variable_by_swc(swc, filter=None):
        """
        currently:
            ONLY for N:1 scenario, there may exist variables defined by R-Port
        """
        variables = {}
        for rport in Function._get_swc_sr_explicit_connected_rport_list(
            swc
        ) + Function._get_swc_sr_implicit_all_rport_list(swc):
            if rport["has_prport"]:
                if not filter or filter == MemmapCategory.OSA_PRIVATE:
                    pass
                else:
                    continue
            else:
                if rport["m_to_n"] != "n1":
                    continue
                if not filter and rport["buff_category"]:
                    pass
                elif filter != rport["buff_memmap_category"]:
                    continue
            # exclude multi-access in one swc, for example Read+IRead
            variables.update({rport["variable"]: rport})
        return variables

    @staticmethod
    @pass_context
    def get_sr_nonqueue_intra_osa_variable_dict_by_appl(context, appl_name=None, filter="all"):
        variable_dict = {}
        sort_variable_dict = {}
        variable_dict_is_bool = {}
        sort_variable_dict_is_bool = {}
        variable_dict_not_bool = {}
        sort_variable_dict_not_bool = {}
        for swc in context["asw_cfg"].values():
            variables = {}
            if appl_name:
                if swc["osapplication"] != appl_name:
                    continue
                variables.update(
                    Function.__get_sr_nonqueue_pport_defined_variable_by_swc(swc, MemmapCategory.OSA_PRIVATE)
                )
                variables.update(
                    Function.__get_sr_nonqueue_rport_defined_variable_by_swc(swc, MemmapCategory.OSA_PRIVATE)
                )
            else:
                variables.update(
                    Function.__get_sr_nonqueue_pport_defined_variable_by_swc(swc, MemmapCategory.OSA_PRIVATE)
                )
                variables.update(
                    Function.__get_sr_nonqueue_rport_defined_variable_by_swc(swc, MemmapCategory.OSA_PRIVATE)
                )
            if variables:
                if swc["osapplication"] not in variable_dict:
                    variable_dict.update({swc["osapplication"]: {}})
                variable_dict[swc["osapplication"]].update(variables)
                if swc["osapplication"] not in variable_dict_is_bool:
                    variable_dict_is_bool.update({swc["osapplication"]: {}})
                if swc["osapplication"] not in variable_dict_not_bool:
                    variable_dict_not_bool.update({swc["osapplication"]: {}})
                for variable in variables.values():
                    if variable["arg"]["init_value"]["is_bool"]:
                        variable_dict_is_bool[swc["osapplication"]].update({variable["variable"]: variable})
                    else:
                        variable_dict_not_bool[swc["osapplication"]].update({variable["variable"]: variable})
        if filter == "nonbool":
            for _appl, appl_variables in variable_dict_not_bool.items():
                sort_variable_dict_not_bool[_appl] = dict(sorted(appl_variables.items()))
            return dict(sorted(sort_variable_dict_not_bool.items()))
        elif filter == "bool":
            for _appl, appl_variables in variable_dict_is_bool.items():
                sort_variable_dict_is_bool[_appl] = dict(sorted(appl_variables.items()))
            return dict(sorted(sort_variable_dict_is_bool.items()))
        else:
            # filter == 'all'
            for _appl, appl_variables in variable_dict.items():
                sort_variable_dict[_appl] = dict(sorted(appl_variables.items()))
            return dict(sorted(sort_variable_dict.items()))

    @staticmethod
    @pass_context
    def get_sr_nonqueue_osa_share_variable_dict_by_appl(context, appl_name=None):
        variable_dict = {}
        sort_variable_dict = {}
        for swc in context["asw_cfg"].values():
            variables = {}
            if appl_name:
                if swc["osapplication"] != appl_name:
                    continue
                variables.update(
                    Function.__get_sr_nonqueue_pport_defined_variable_by_swc(swc, MemmapCategory.OSA_SHARED)
                )
                variables.update(
                    Function.__get_sr_nonqueue_rport_defined_variable_by_swc(swc, MemmapCategory.OSA_SHARED)
                )
            else:
                variables.update(
                    Function.__get_sr_nonqueue_pport_defined_variable_by_swc(swc, MemmapCategory.OSA_SHARED)
                )
                variables.update(
                    Function.__get_sr_nonqueue_rport_defined_variable_by_swc(swc, MemmapCategory.OSA_SHARED)
                )
            if variables:
                if swc["osapplication"] not in variable_dict:
                    variable_dict.update({swc["osapplication"]: {}})
                variable_dict[swc["osapplication"]].update(variables)
        for _appl, appl_variables in variable_dict.items():
            sort_variable_dict[_appl] = dict(sorted(appl_variables.items()))
        return dict(sorted(sort_variable_dict.items()))

    @staticmethod
    @pass_context
    def get_sr_nonqueue_core_share_variable_dict_by_appl(context, appl_name=None):
        variable_dict = {}
        sort_variable_dict = {}
        for swc in context["asw_cfg"].values():
            variables = {}
            if appl_name:
                if swc["osapplication"] != appl_name:
                    continue
                variables.update(
                    Function.__get_sr_nonqueue_pport_defined_variable_by_swc(swc, MemmapCategory.CORE_SHARED)
                )
                variables.update(
                    Function.__get_sr_nonqueue_rport_defined_variable_by_swc(swc, MemmapCategory.CORE_SHARED)
                )
            else:
                variables.update(
                    Function.__get_sr_nonqueue_pport_defined_variable_by_swc(swc, MemmapCategory.CORE_SHARED)
                )
                variables.update(
                    Function.__get_sr_nonqueue_rport_defined_variable_by_swc(swc, MemmapCategory.CORE_SHARED)
                )
            if variables:
                if swc["osapplication"] not in variable_dict:
                    variable_dict.update({swc["osapplication"]: {}})
                variable_dict[swc["osapplication"]].update(variables)
        for _appl, appl_variables in variable_dict.items():
            sort_variable_dict[_appl] = dict(sorted(appl_variables.items()))
        return dict(sorted(sort_variable_dict.items()))

    @staticmethod
    @pass_context
    def get_sr_nonqueue_global_variable_dict_by_appl(context, appl_name=None):
        variable_dict = {}
        sort_variable_dict = {}
        for swc in context["asw_cfg"].values():
            variables = {}
            variables_global = {}
            if appl_name:
                if swc["osapplication"] != appl_name:
                    continue
                variables.update(Function.__get_sr_nonqueue_pport_defined_variable_by_swc(swc, MemmapCategory.GLOBAL))
                variables_global.update(
                    Function.__get_sr_nonqueue_rport_defined_variable_by_swc(swc, MemmapCategory.GLOBAL)
                )
            else:
                variables.update(Function.__get_sr_nonqueue_pport_defined_variable_by_swc(swc, MemmapCategory.GLOBAL))
                variables_global.update(
                    Function.__get_sr_nonqueue_rport_defined_variable_by_swc(swc, MemmapCategory.GLOBAL)
                )
            if variables:
                if swc["osapplication"] not in variable_dict:
                    variable_dict.update({swc["osapplication"]: {}})
                variable_dict[swc["osapplication"]].update(variables)
            if variables_global:
                if "GLOBAL-VARS" not in variable_dict:
                    variable_dict.update({"GLOBAL-VARS": {}})
                variable_dict["GLOBAL-VARS"].update(variables_global)
        for _appl, appl_variables in variable_dict.items():
            sort_variable_dict[_appl] = dict(sorted(appl_variables.items()))
        return dict(sorted(sort_variable_dict.items()))

    @staticmethod
    @pass_context
    def get_sr_nonqueue_variable_dict_by_appl(context, appl_name):
        variable_dict = {}
        for swc in context["asw_cfg"].values():
            if swc["osapplication"] == appl_name:
                variable_dict.update(Function.__get_sr_nonqueue_pport_defined_variable_by_swc(swc))
                variable_dict.update(Function.__get_sr_nonqueue_rport_defined_variable_by_swc(swc))
        # variables.sort(key=lambda x: ('args' in x.keys(), x['variable'].lower()))
        for _, variable in variable_dict.items():
            datatype = variable.get("arg", {}).get("datatype", {})
            init_value = variable.get("arg", {}).get("init_value", {})
            variable["init_zero"] = Function._is_init_value_zero(datatype, init_value)
        return dict(sorted(variable_dict.items()))

    @staticmethod
    def _is_init_value_zero(datatype, init_value):
        is_zero = False
        if datatype and init_value:
            init_value_tuple = AutosarUtils.get_sr_var_init_value(datatype, init_value)
            if init_value_tuple is not None and len(init_value_tuple) == 3:
                is_zero = init_value_tuple[1] is True
        return is_zero

    @staticmethod
    @pass_context
    def get_swc_sr_nonqueue_intra_osa_update_flag_rport_list(context):
        rport_list = []
        for rport in context["swc"]["rports"].values():
            if rport["type"] != "Explicit Receiver" or rport["signal_category"] != "None":
                continue
            if not rport["enable_update"] or rport["m_to_n"] in ["0", "mn"] or not rport["intra_osa"]:
                continue
            rport_list.append(rport)
        rport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rport_list

    @staticmethod
    @pass_context
    def get_swc_sr_nonqueue_enable_update_rport_list(context, runnable=None):
        rport_list = []
        for rport in context["swc"]["rports"].values():
            if Function.not_port_accessed_runnable(rport, runnable):
                continue
            if rport["type"] != "Explicit Receiver" or rport["signal_category"] != "None":
                continue
            if not rport["enable_update"]:
                continue
            rport_list.append(rport)
        rport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rport_list

    @staticmethod
    @pass_context
    def _get_sr_nonqueue_specified_update_flag_dict_by_appl(context, mm_filter=None, appl_name=None):
        flag_dict = {}
        for swc in context["asw_cfg"].values():
            flags = []
            if appl_name and appl_name != swc["osapplication"]:
                continue
            for rport in swc["rports"].values():
                if rport["type"] != "Explicit Receiver":
                    continue
                if not rport["enable_update"]:
                    continue
                if not rport["has_prport"] and rport["m_to_n"] in ["0", "mn"]:
                    continue
                if not mm_filter:
                    pass
                elif mm_filter != rport["enable_update_memmap_category"]:
                    continue
                elif mm_filter == "inter_osa" and rport["intra_osa"]:
                    continue
                flags.append({"flag_name": f'Rte_RxUpdate_{rport["component"]}_{rport["name"]}'})
            if flags:
                if swc["osapplication"] not in flag_dict:
                    flag_dict.update({swc["osapplication"]: []})
                flag_dict[swc["osapplication"]].extend(flags)
            for appl_flags in flag_dict.values():
                appl_flags.sort(key=lambda x: (x["args"] if "args" in x.keys() else "", x["flag_name"]))
        return dict(sorted(flag_dict.items()))

    @staticmethod
    @pass_context
    def get_all_sr_nonqueue_intra_osa_update_flag_dict_by_appl(context, appl_name=None):
        return Function._get_sr_nonqueue_specified_update_flag_dict_by_appl(
            context, mm_filter=MemmapCategory.OSA_PRIVATE, appl_name=appl_name
        )

    @staticmethod
    @pass_context
    def get_all_sr_nonqueue_inter_osa_update_flag_dict_by_appl(context, appl_name=None):
        return Function._get_sr_nonqueue_specified_update_flag_dict_by_appl(
            context, mm_filter=MemmapCategory.CORE_SHARED, appl_name=appl_name
        )

    @staticmethod
    @pass_context
    def get_all_sr_nonqueue_inter_core_update_flag_dict_by_appl(context, appl_name=None):
        return Function._get_sr_nonqueue_specified_update_flag_dict_by_appl(
            context, mm_filter=MemmapCategory.GLOBAL, appl_name=appl_name
        )

    @staticmethod
    @pass_context
    def get_all_sr_nonqueue_update_flag_dict_by_appl(context, appl_name=None):
        return Function._get_sr_nonqueue_specified_update_flag_dict_by_appl(
            context, mm_filter=None, appl_name=appl_name
        )

    @staticmethod
    @pass_context
    def get_appl_sr_unqueued_structure_variable_list(context, appl_name=None):
        """未使用接口"""
        variable_list = []
        for port in Function._get_appl_sr_unqueued_variable_dict(context, appl_name):
            if port["arg"]["datatype"]["native_category"] != "STRUCTURE":
                continue
            variable_list.append(port)
        variable_list.sort(
            key=lambda x: (
                "args" in x.keys(),
                x["variable"].lower(),
                (x["global_counter"] if "global_counter" in x else ""),
            )
        )
        return variable_list

    @staticmethod
    @pass_context
    def get_initial_buffer_list(context, buffers):
        data_type_set = set()
        buffer_list = []
        for buffer in buffers:
            if buffer["datatype"] not in data_type_set:
                data_type_set.add(buffer["datatype"])
                buffer_list.append(buffer)
        return buffer_list

    @staticmethod
    @pass_context
    def get_appl_sr_unqueued_array_variable_list(context, appl_name=None):
        """未使用接口"""
        variable_list = []
        for port in Function._get_appl_sr_unqueued_variable_dict(context, appl_name):
            if port["arg"]["datatype"]["native_category"] != "ARRAY":
                continue
            variable_list.append(port)
        variable_list.sort(
            key=lambda x: (
                "args" in x.keys(),
                x["variable"].lower(),
                (x["global_counter"] if "global_counter" in x else ""),
            )
        )
        return variable_list

    @staticmethod
    @pass_context
    def get_all_sr_init_value_const_list(context):
        all_ports = []
        const = {}
        consts = []
        consts_dict = {}
        for swc in context["asw_cfg"].values():
            all_ports += Function._get_swc_sr_explicit_connected_rport_list(swc)
            all_ports += Function._get_swc_sr_explicit_unconnected_rport_list(swc)
            all_ports += Function._get_swc_sr_implicit_all_rport_list(swc)
        for port in all_ports:
            datatype = port.get("arg", {}).get("datatype", {})
            init_value = port.get("arg", {}).get("init_value", {})
            if not init_value:
                continue
            # the const of numerical is not generated or used, use numerical value directly
            if datatype["native_category"] not in ["UNION", "STRUCTURE", "ARRAY"]:
                continue
            if port.get("signal_category", "None") != "None":
                continue  # datamapping macro api do not need to be generated variable
            if port.get("m_to_n", "0") != "0" and Function._is_init_value_zero(datatype, init_value):
                # zero init will not generate for save flash if port has connection
                continue

            const = {
                "datatype": datatype["name"],
                "name": init_value["name"],
                "value": init_value["value"]["value"],
                "idt_dict": datatype,
                "is_union": datatype["native_category"] == "UNION",
            }
            # 通过字典来去重
            consts_dict.update({const["name"]: const})
            consts = list(consts_dict.values())
        consts.sort(key=lambda x: x["name"].lower())
        return consts

    @staticmethod
    @pass_context
    def get_appl_sr_implicit_copy_buffer_list(context, appl_name):
        buffer_list = []
        ports = []
        for swc in context["asw_cfg"].values():
            if swc["osapplication"] == appl_name:
                ports += Function._get_swc_sr_implicit_all_pport_list(swc)
                ports += Function._get_swc_sr_implicit_all_rport_list(swc)
        for port in ports:
            if port["imp_sr_copy_buf_opt"]:
                continue
            if port["task"] not in buffer_list:
                buffer_list.append(port["task"])
        buffer_list.sort(key=lambda x: (len(x), x.lower()))
        return buffer_list

    @staticmethod
    @pass_context
    def get_sr_nonqueue_intra_osa_without_boolean_variable_dict_by_appl(context, appl_name):
        # 取sr_nonqueue_intra_osa中的非bool变量
        rv = {}
        rv = Function.get_sr_nonqueue_intra_osa_variable_dict_by_appl(context, appl_name, filter="nonbool")
        return rv

    @staticmethod
    @pass_context
    def get_boolean_variables_init_value_list(context, appl_name, nonzero_boolean_vars):
        # 将组成结构体的所有bool变量的非0/FALSE初始值组成字符串
        rv = ""
        init_value_list = []
        for var in nonzero_boolean_vars[appl_name].values():
            init_value_list.append(var["arg"]["init_value"]["value"]["value"])
            # init_value_list.append('.' + var['variable'] + ' = 1U')
        if init_value_list:
            rv = "{" + ", ".join(init_value_list) + "}"
        else:
            rv = {0}
        return rv

    @staticmethod
    @pass_context
    def get_sr_nonqueue_intra_osa_boolean_variable_dict_by_appl(context, appl_name, filter="all"):
        # 取appl下所有SWC中的sr_nonqueue_intra_osa bool变量，将其转成位字段，节省RAM空间
        variable_dict = {}
        sort_variable_dict = {}
        temp_variable_dict = Function.get_sr_nonqueue_intra_osa_variable_dict_by_appl(context, appl_name, filter="bool")
        if temp_variable_dict:
            if filter == "nonzero":
                for name, value in temp_variable_dict.get(appl_name, {}).items():
                    if value["arg"]["init_value"]["is_zero_init"]:
                        continue
                    if appl_name not in variable_dict:
                        variable_dict.update({appl_name: {}})
                    variable_dict[appl_name].update({name: value})
            elif filter == "zero":
                for name, value in temp_variable_dict.get(appl_name, {}).items():
                    if not value["arg"]["init_value"]["is_zero_init"]:
                        continue
                    if appl_name not in variable_dict:
                        variable_dict.update({appl_name: {}})
                    variable_dict[appl_name].update({name: value})
            else:
                # filter == "all"
                variable_dict = temp_variable_dict
        for appl, appl_variables in variable_dict.items():
            sort_variable_dict[appl] = dict(sorted(appl_variables.items()))
        return sort_variable_dict

    @staticmethod
    @pass_context
    def get_swc_sr_implicit_macro_render_pport_list(context, runnable=None):
        pport_list = []
        for pport in Function._get_swc_sr_implicit_all_pport_list(context["swc"]):
            if Function.not_port_accessed_runnable(pport, runnable):
                continue
            pport_list.append(pport)
        pport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return pport_list

    @staticmethod
    @pass_context
    def get_swc_sr_implicit_macro_render_rport_list(context, runnable=None):
        rport_list = []
        rport_list_origin = Function._get_swc_sr_implicit_all_rport_list(context["swc"])
        if runnable:
            for rport in rport_list_origin:
                if Function.not_port_accessed_runnable(rport, runnable):
                    continue
                rport_list.append(rport)
        else:
            rport_list = rport_list_origin
        rport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rport_list

    @staticmethod
    @pass_context
    def get_swc_sr_implicit_copy_buffer_list(context):
        buffer_set = set()
        port_list = Function._get_swc_sr_implicit_all_pport_list(context["swc"])
        port_list += Function._get_swc_sr_implicit_all_rport_list(context["swc"])
        for port in port_list:
            if port["imp_sr_copy_buf_opt"]:
                continue
            if port["task"]:
                buffer_set.add(port["task"])
        buffer_list = sorted(buffer_set, key=lambda x: (len(x), x.lower()))
        return buffer_list

    @staticmethod
    @pass_context
    def get_nv_ram_block_data_type_swc_list(context):
        nv_ram_block_data_type_list = []
        for swc in context["asw_cfg"].values():
            if "type" in swc and swc["type"] == "NvBlockComponent":
                for descriptor_dict in swc["nvblock_descriptors"].values():
                    if descriptor_dict["ram_block"]:
                        nv_ram_block_data_type_list.append(descriptor_dict["ram_block"])
        return nv_ram_block_data_type_list

    @staticmethod
    @pass_context
    def get_nv_descriptor_with_dirtflag_from_swc_list(context):
        descriptor_dict = {}
        for swc in context["asw_cfg"].values():
            if "type" in swc and swc["type"] == "NvBlockComponent":
                for descriptor_cfg in swc["nvblock_descriptors"].values():
                    if descriptor_cfg["dirty_flag"]:
                        if "osapplication" not in swc:
                            appl_name = ""
                        else:
                            appl_name = swc["osapplication"]
                        if appl_name not in descriptor_dict:
                            descriptor_dict[appl_name] = []
                        descriptor_dict[appl_name].append(descriptor_cfg)
        return descriptor_dict

    @staticmethod
    def _get_swc_sr_implicit_all_pport_list(swc):
        pport_list = []
        for pport in swc["pports"].values():
            if pport["type"] != "Implicit Sender":
                continue
            variable = ""
            single_rec_buff_for_n1 = None
            buff_category = None
            buff_memmap_category = None
            counter_category = None
            local_counter = None
            global_counter = None
            buff_struct_type = None
            buff_struct_name = None
            sender_buff_struct_type = []
            sender_buff_struct_name = []
            if pport["m_to_n"] not in {"0", "mn"}:
                if pport["m_to_n"] == "n1":
                    rport = pport["conn_asw_ports"][0]
                    single_rec_buff_for_n1 = pport["single_rec_buff_for_n1"]
                    if single_rec_buff_for_n1:
                        variable = "Rte_" + rport["swc_port_var"]
                        struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(rport)
                        buff_struct_type = struct_type
                        buff_struct_name = struct_name
                    else:
                        variable = "Rte_" + pport["swc_port_var"]
                        buff_category = pport["buff_category"]
                        buff_memmap_category = pport["buff_memmap_category"]
                        counter_category = pport["counter_category"]
                        local_counter = "Rte_Counter_Sr_Local_" + pport["swc_port_var"]
                        global_counter = "Rte_Counter_Sr_Global_" + rport["swc_port_var"]
                        struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(pport)
                        sender_buff_struct_type.append(struct_type)
                        sender_buff_struct_name.append(struct_name)
                else:
                    variable = "Rte_" + pport["swc_port_var"]
                    buff_category = pport["buff_category"]
                    buff_memmap_category = pport["buff_memmap_category"]
                    struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(pport)
                    buff_struct_type = struct_type
                    buff_struct_name = struct_name
            else:
                variable = "Rte_" + pport["swc_port_var"]
            arg = {
                "datatype": pport["arg"]["datatype"],
                "typesize_byte_for_struct_align": pport["arg"]["datatype"]["typesize_byte_for_struct_align"],
                "init_value": pport["arg"]["init_value"],
            }
            pport_list.append(
                {
                    "sort_name": pport["sort_name"],
                    "name": pport["name"],
                    "type": pport["type"],
                    "component": pport["component"],
                    "port_prototype": pport["port_prototype"],
                    "data_element": pport["data_element"],
                    "task": pport["task"][0],
                    "runnable": pport["runnable"][0],
                    "datatype": pport["arg"]["datatype"]["name"],
                    "typesize_byte_for_struct_align": pport["arg"]["datatype"]["typesize_byte_for_struct_align"],
                    "variable": variable,
                    "local_counter": local_counter,
                    "global_counter": global_counter,
                    "arg": arg,
                    "lock": pport["lock"],
                    "set_events": pport["set_events"],
                    "var_osa": swc["osapplication"],
                    "m_to_n": pport["m_to_n"],
                    "single_rec_buff_for_n1": single_rec_buff_for_n1,
                    "buff_category": buff_category,
                    "buff_memmap_category": buff_memmap_category,
                    "core_id": pport["core_id"],
                    "counter_category": counter_category,
                    "has_prport": pport["has_prport"],
                    "signal_category": pport["signal_category"],
                    "imp_sr_copy_buf_opt": pport["imp_sr_copy_buf_opt"],
                    "imp_sr_buf_opt_intra_osa": pport["imp_sr_buf_opt_intra_osa"],
                    "buff_struct_type": buff_struct_type,
                    "buff_struct_name": buff_struct_name,
                    "sender_buff_struct_type": sender_buff_struct_type,
                    "sender_buff_struct_name": sender_buff_struct_name,
                }
            )
        return pport_list

    @staticmethod
    def _get_swc_sr_implicit_all_rport_list(swc):
        rport_list = []
        for rport in swc["rports"].values():
            if rport["type"] != "Implicit Receiver":
                continue
            single_rec_buff_for_n1 = None
            buff_category = None
            buff_memmap_category = None
            counter_category = None
            global_counter = None
            all_sender_buffer = []
            all_sender_counter = []
            buff_struct_type = None
            buff_struct_name = None
            sender_buff_struct_type = []
            sender_buff_struct_name = []
            if rport["m_to_n"] not in {"0", "mn"}:
                if rport["m_to_n"] == "n1":
                    # N:1
                    variable = "Rte_" + rport["swc_port_var"]
                    var_osa = swc["osapplication"]
                    port_for_data_type = rport
                    single_rec_buff_for_n1 = rport["single_rec_buff_for_n1"]
                    buff_category = rport["buff_category"]
                    buff_memmap_category = rport["buff_memmap_category"]
                    struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(rport)
                    buff_struct_type = struct_type
                    buff_struct_name = struct_name
                    if not single_rec_buff_for_n1:
                        counter_category = rport["counter_category"]
                        global_counter = "Rte_Counter_Sr_Global_" + rport["swc_port_var"]
                        for pport in rport["conn_asw_ports"]:
                            all_sender_buffer.append(("Rte_" + pport["swc_port_var"], pport["osapplication"]))
                            all_sender_counter.append(
                                ("Rte_Counter_Sr_Local_" + pport["swc_port_var"], pport["osapplication"])
                            )
                            struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(pport)
                            sender_buff_struct_type.append(struct_type)
                            sender_buff_struct_name.append(struct_name)
                else:
                    # 1:1 / 1:N
                    connected_pport = rport["conn_asw_ports"][0]
                    variable = "Rte_" + connected_pport["swc_port_var"]
                    var_osa = connected_pport["osapplication"]
                    port_for_data_type = connected_pport
                    struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(
                        connected_pport
                    )
                    buff_struct_type = struct_type
                    buff_struct_name = struct_name
            else:
                variable = "Rte_" + rport["swc_port_var"]
                var_osa = swc["osapplication"]
                port_for_data_type = rport
            arg = {
                "datatype": port_for_data_type["arg"]["datatype"],
                "typesize_byte_for_struct_align": rport["arg"]["datatype"]["typesize_byte_for_struct_align"],
                "init_value": rport["arg"]["init_value"],
            }
            rport_list.append(
                {
                    "sort_name": rport["sort_name"],
                    "name": rport["name"],
                    "type": rport["type"],
                    "component": rport["component"],
                    "port_prototype": rport["port_prototype"],
                    "data_element": rport["data_element"],
                    "task": rport["task"][0],
                    "runnable": rport["runnable"][0],
                    "datatype": port_for_data_type["arg"]["datatype"]["name"],
                    "typesize_byte_for_struct_align": rport["arg"]["datatype"]["typesize_byte_for_struct_align"],
                    "variable": variable,
                    "global_counter": global_counter,
                    "all_sender_buffer": all_sender_buffer,
                    "all_sender_counter": all_sender_counter,
                    "arg": arg,
                    "lock": rport["lock"],
                    "var_osa": var_osa,
                    "m_to_n": rport["m_to_n"],
                    "single_rec_buff_for_n1": single_rec_buff_for_n1,
                    "buff_category": buff_category,
                    "buff_memmap_category": buff_memmap_category,
                    "core_id": rport["core_id"],
                    "counter_category": counter_category,
                    "has_prport": rport["has_prport"],
                    "signal_category": rport["signal_category"],
                    "imp_sr_copy_buf_opt": rport["imp_sr_copy_buf_opt"],
                    "imp_sr_buf_opt_intra_osa": rport["imp_sr_buf_opt_intra_osa"],
                    "buff_struct_type": buff_struct_type,
                    "buff_struct_name": buff_struct_name,
                    "sender_buff_struct_type": sender_buff_struct_type,
                    "sender_buff_struct_name": sender_buff_struct_name,
                }
            )
        return rport_list

    @staticmethod
    @pass_context
    def get_swc_sr_explicit_api_pport_list(context, runnable=None):
        pport_list = []
        for pport in context["swc"]["pports"].values():
            if Function.not_port_accessed_runnable(pport, runnable):
                continue
            if pport["type"] != "Explicit Sender":
                continue
            if Function.get_sr_explicit_rte_interface_code_format(pport) == _FUNC:
                pport_list.append(pport)
        pport_list.sort(key=lambda x: ("arg" in x.keys(), x["name"].lower()))
        return pport_list

    @staticmethod
    @pass_context
    def get_swc_sr_explicit_api_rport_list(context, runnable=None):
        rport_list = []
        for rport in context["swc"]["rports"].values():
            if Function.not_port_accessed_runnable(rport, runnable):
                continue
            if rport["type"] != "Explicit Receiver":
                continue
            if Function.get_sr_explicit_rte_interface_code_format(rport) == _FUNC:
                rport_list.append(rport)
        rport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rport_list

    @staticmethod
    @pass_context
    def get_swc_sr_queue_unconnected_pport_list(context):
        pport_list = [
            i for i in context["swc"]["pports"].values() if i["type"] == "Queued Sender" and not i["conn_asw_ports"]
        ]
        pport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return pport_list

    @staticmethod
    @pass_context
    def get_swc_sr_queue_unconnected_rport_list(context):
        rport_list = [
            i for i in context["swc"]["rports"].values() if i["type"] == "Queued Receiver" and not i["conn_asw_ports"]
        ]
        rport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rport_list

    @staticmethod
    @pass_context
    def get_swc_sr_queue_api_pport_list(context, runnable=None):
        pport_list = []
        for pport in context["swc"]["pports"].values():
            if Function.not_port_accessed_runnable(pport, runnable):
                continue
            if pport["type"] == "Queued Sender" and pport["conn_asw_ports"]:
                pport_list.append(pport)
        pport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return pport_list

    @staticmethod
    @pass_context
    def get_swc_sr_queue_api_rport_list(context, runnable=None):
        rport_list = []
        for rport in context["swc"]["rports"].values():
            if Function.not_port_accessed_runnable(rport, runnable):
                continue
            if rport["type"] == "Queued Receiver" and rport["conn_asw_ports"]:
                rport_list.append(rport)
        rport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rport_list

    @staticmethod
    @pass_context
    def get_all_sr_queue_pport_list(context):
        pport_list = [
            i
            for swc in context["asw_cfg"].values()
            for i in swc["pports"].values()
            if i["type"] == "Queued Sender" and i["conn_asw_ports"]
        ]
        pport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return pport_list

    @staticmethod
    @pass_context
    def get_appl_sr_queue_pport_list(context, appl_name):
        pport_list = [
            i
            for swc in context["asw_cfg"].values()
            if swc["osapplication"] == appl_name
            for i in swc["pports"].values()
            if i["type"] == "Queued Sender" and i["conn_asw_ports"]
        ]
        pport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return pport_list

    @staticmethod
    @pass_context
    def get_all_sr_queue_rport_list(context):
        rport_list = [
            i
            for swc in context["asw_cfg"].values()
            for i in swc["rports"].values()
            if i["type"] == "Queued Receiver" and i["conn_asw_ports"]
        ]
        rport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rport_list

    @staticmethod
    @pass_context
    def get_appl_sr_queue_non_ioc_rport_list(context, appl_name):
        rport_list = [
            i
            for swc in context["asw_cfg"].values()
            if swc["osapplication"] == appl_name
            for i in swc["rports"].values()
            if i["type"] == "Queued Receiver"
            and i["conn_asw_ports"]
            and list(i["queue"].values())[0]["ioc_type"] == "NONE"
        ]
        rport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rport_list

    @staticmethod
    @pass_context
    def get_appl_sr_queue_ioc_rport_list(context, appl_name):
        rport_list = [
            i
            for swc in context["asw_cfg"].values()
            if swc["osapplication"] == appl_name
            for i in swc["rports"].values()
            if i["type"] == "Queued Receiver"
            and i["conn_asw_ports"]
            and list(i["queue"].values())[0]["ioc_type"] != "NONE"
        ]
        rport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rport_list

    @staticmethod
    @pass_context
    def get_all_sr_queue_non_ioc_dequeue_dict_by_appl(context, appl_name=None):
        queue_dict = {}
        for swc in context["asw_cfg"].values():
            if appl_name and appl_name != swc["osapplication"]:
                continue
            queues = []
            for rport in swc["rports"].values():
                if rport["type"] != "Queued Receiver" or not rport["conn_asw_ports"]:
                    continue
                queue_name = list(rport["queue"].keys())[0]
                queue = list(rport["queue"].values())[0]
                if queue["ioc_type"] != "NONE":
                    continue
                queues.append(
                    {
                        "name": queue_name,
                        "size": queue["size"],
                        "datatype": rport["arg"]["datatype"],
                        "overflow_name": f"Rte_{queue_name}",
                        "sort_name": rport["sort_name"],
                    }
                )
            if queues:
                if swc["osapplication"] not in queue_dict:
                    queue_dict.update({swc["osapplication"]: []})
                queue_dict[swc["osapplication"]].extend(queues)
            for appl_queues in queue_dict.values():
                appl_queues.sort(key=lambda x: (x["args"] if "args" in x.keys() else "", x["sort_name"]))
        return dict(sorted(queue_dict.items()))

    @staticmethod
    @pass_context
    def _get_sr_queue_ioc_specified_enqueue_dict_by_appl(context, filter, appl_name=None):
        queue_dict = {}
        for swc in context["asw_cfg"].values():
            if appl_name and appl_name != swc["osapplication"]:
                continue
            queues_inter_osa_same_core = []
            queues_inter_core = []

            for pport in swc["pports"].values():
                if pport["type"] != "Queued Sender" or not pport["conn_asw_ports"]:
                    continue
                if filter == "all":
                    pass
                elif filter == "N:1" and pport["m_to_n"] != "n1":
                    continue
                elif filter == "1:1/1:N" and pport["m_to_n"] == "n1":
                    continue
                for queue_name, queue in pport["queue"].items():
                    if queue["ioc_type"] == "NONE":
                        continue
                    curr_info = {
                        "name": queue_name,
                        "port": pport["port_prototype"],
                        "component": pport["component"],
                        "size": queue["size"],
                        "datatype": pport["arg"]["datatype"],
                        "ioc_type": queue["ioc_type"],
                        "sort_name": pport["sort_name"],
                    }
                    if queue["ioc_type"] == "SPINLOCK":
                        queues_inter_core.append(curr_info)
                    elif queue["ioc_type"] == "OSISR":
                        queues_inter_osa_same_core.append(curr_info)

            if queues_inter_core or queues_inter_osa_same_core:
                if swc["osapplication"] not in queue_dict:
                    queue_dict[swc["osapplication"]] = {
                        "inter_osa_same_core": [],
                        "inter_core": [],
                        "core_id": swc["core_id"],
                    }
                queue_dict[swc["osapplication"]]["inter_osa_same_core"].extend(queues_inter_osa_same_core)
                queue_dict[swc["osapplication"]]["inter_core"].extend(queues_inter_core)
            for appl_queues in queue_dict.values():
                appl_queues["inter_osa_same_core"].sort(
                    key=lambda x: (x["args"] if "args" in x.keys() else "", x["sort_name"])
                )
                appl_queues["inter_core"].sort(key=lambda x: (x["args"] if "args" in x.keys() else "", x["sort_name"]))
        return dict(sorted(queue_dict.items()))

    @staticmethod
    @pass_context
    def get_all_sr_queue_ioc_enqueue_dict_by_appl(context, appl_name=None):
        info = Function._get_sr_queue_ioc_specified_enqueue_dict_by_appl(context, "all", appl_name)
        combined_info = {}
        for osa, queues in info.items():
            combined_info[osa] = []
            combined_info[osa].extend(queues["inter_osa_same_core"])
            combined_info[osa].extend(queues["inter_core"])
        return combined_info

    @staticmethod
    @pass_context
    def get_all_sr_queue_ioc_1to1_1toN_enqueue_dict_by_appl(context, appl_name=None):
        return Function._get_sr_queue_ioc_specified_enqueue_dict_by_appl(context, "1:1/1:N", appl_name)

    @staticmethod
    @pass_context
    def _get_sr_queue_ioc_specified_dequeue_dict_by_appl(context, filter, appl_name=None):
        queue_dict = {}
        for swc in context["asw_cfg"].values():
            if appl_name and appl_name != swc["osapplication"]:
                continue
            queues_inter_osa_same_core = []
            queues_inter_core = []

            for rport in swc["rports"].values():
                if rport["type"] != "Queued Receiver" or not rport["conn_asw_ports"]:
                    continue
                if filter == "all":
                    pass
                elif filter == "N:1" and rport["m_to_n"] != "n1":
                    continue
                elif filter == "1:1/1:N" and rport["m_to_n"] == "n1":
                    continue
                queue_name = list(rport["queue"].keys())[0]
                queue = list(rport["queue"].values())[0]
                if queue["ioc_type"] == "NONE":
                    continue
                curr_info = {
                    "name": queue_name,
                    "component": rport["component"],
                    "size": queue["size"],
                    "datatype": rport["arg"]["datatype"],
                    "ioc_type": queue["ioc_type"],
                    "sort_name": rport["sort_name"],
                }
                if queue["ioc_type"] == "SPINLOCK":
                    queues_inter_core.append(curr_info)
                elif queue["ioc_type"] == "OSISR":
                    queues_inter_osa_same_core.append(curr_info)

            if queues_inter_core or queues_inter_osa_same_core:
                if swc["osapplication"] not in queue_dict:
                    queue_dict[swc["osapplication"]] = {
                        "inter_osa_same_core": [],
                        "inter_core": [],
                        "core_id": swc["core_id"],
                    }
                queue_dict[swc["osapplication"]]["inter_osa_same_core"].extend(queues_inter_osa_same_core)
                queue_dict[swc["osapplication"]]["inter_core"].extend(queues_inter_core)
            for appl_queues in queue_dict.values():
                appl_queues["inter_osa_same_core"].sort(
                    key=lambda x: (x["args"] if "args" in x.keys() else "", x["sort_name"])
                )
                appl_queues["inter_core"].sort(key=lambda x: (x["args"] if "args" in x.keys() else "", x["sort_name"]))
        return dict(sorted(queue_dict.items()))

    @staticmethod
    @pass_context
    def get_all_sr_queue_ioc_Nto1_dequeue_dict_by_appl(context, appl_name=None):
        return Function._get_sr_queue_ioc_specified_dequeue_dict_by_appl(context, "N:1", appl_name)

    @staticmethod
    @pass_context
    def get_all_sr_queue_ioc_1to1_1toN_dequeue_dict_by_appl(context, appl_name=None):
        return Function._get_sr_queue_ioc_specified_dequeue_dict_by_appl(context, "1:1/1:N", appl_name)

    @staticmethod
    @pass_context
    def get_all_sr_queue_ioc_dequeue_dict_by_appl(context, appl_name=None, is_result_combined=False):
        info = Function._get_sr_queue_ioc_specified_dequeue_dict_by_appl(context, "all", appl_name)
        if is_result_combined:
            combined_info = {}
            for osa, queues in info.items():
                combined_info[osa] = []
                combined_info[osa].extend(queues["inter_osa_same_core"])
                combined_info[osa].extend(queues["inter_core"])
            return combined_info
        else:
            return info

    @staticmethod
    @pass_context
    def get_dlog_sr_explicit_api_value_pport_list(context):
        pports = []
        for swc in context["asw_cfg"].values():
            for port in swc["pports"].values():
                if port["type"] != "Explicit Sender":
                    continue
                if port["arg"]["datatype"]["category"] != "TYPE_REFERENCE":
                    continue
                pports.append(port)
        pports.sort(key=lambda x: (x["component"], x["name"]))
        return pports

    @staticmethod
    @pass_context
    def get_dlog_sr_explicit_api_pointer_pport_list(context):
        pports = []
        for swc_dict in context["asw_cfg"].values():
            for port in swc_dict["pports"].values():
                if port["type"] != "Explicit Sender":
                    continue
                if port["arg"]["datatype"]["category"] == "TYPE_REFERENCE":
                    continue
                pports.append(port)
        pports.sort(key=lambda x: (x["component"], x["name"]))
        return pports

    @staticmethod
    @pass_context
    def get_dlog_sr_explicit_api_rport_list(context):
        rport_list = []
        for swc_dict in context["asw_cfg"].values():
            for rport in swc_dict["rports"].values():
                if rport["type"] != "Explicit Receiver" or (
                    rport["m_to_n"] in {"0", "mn"}
                    and (
                        rport["signal_category"] not in {"Signal", "SignalGroup"} or rport["data_mapping_m_to_n"] == "0"
                    )
                ):
                    continue
                if (
                    rport["signal_category"] != "None"
                    or rport["arg"]["datatype"]["category"] != "TYPE_REFERENCE"
                    or rport["lock"] != "NONE"
                ):
                    rport_list.append(rport)
        rport_list.sort(key=lambda x: (x["component"], x["name"]))
        return rport_list

    @staticmethod
    @pass_context
    def get_all_runnables_dict(context):
        runnables = {}
        for swc in context["asw_cfg"].values():
            runnables.update(swc["runnables"])
        return runnables

    @staticmethod
    @pass_context
    def get_all_implicit_sr_data_dict(context):
        port_dict = {}
        for task in context["task_mappings"].values():
            for runnable_symbol in task["schedulable_entity"].keys():
                port_dict[runnable_symbol] = {"pport_data": [], "rport_data": [], "set_events": []}
        for swc in context["asw_cfg"].values():
            Function._set_implicit_pport(port_dict, swc)
            Function._set_implicit_rport(port_dict, swc)
        for port in port_dict.values():
            event_set = set(map(lambda x: x["task_id"] + "&" + x["event_mask"] if x else "&", port["set_events"]))
            set_events = list(
                map(lambda x: {"task_id": x.split("&")[0].upper(), "event_mask": x.split("&")[1].upper()}, event_set)
            )
            set_events.sort(key=lambda x: ("task_id" in x, x["task_id"] + x["event_mask"]))
            port["set_events"] = set_events
        return port_dict

    @staticmethod
    def _set_implicit_pport(port_dict, swc):
        for pport in swc["pports"].values():
            if pport["type"] != "Implicit Sender":
                continue
            if pport["m_to_n"] == "mn":
                continue
            # either port mapping or data mapping or both
            if pport["m_to_n"] == "0" and (
                pport["signal_category"] not in {"Signal", "SignalGroup"} or pport["data_mapping_m_to_n"] == "0"
            ):
                continue

            if pport["imp_sr_copy_buf_opt"]:
                continue

            pport_data = dict(pport)
            if pport["m_to_n"] != "0":
                # intra ecu
                variable_name = None
                local_counter = None
                global_counter = None
                lock_id = None
                buff_struct_type = None
                buff_struct_name = None
                sender_buff_struct_type = []
                sender_buff_struct_name = []
                # the ioc_id has the same name as variable_name
                if pport["m_to_n"] in {"11", "1n"}:
                    variable_name = "Rte_" + pport["swc_port_var"]
                    lock_id = variable_name
                    struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(pport)
                    buff_struct_type = struct_type
                    buff_struct_name = struct_name
                else:
                    rport = pport["conn_asw_ports"][0]
                    lock_id = "Rte_" + rport["swc_port_var"]
                    if pport["single_rec_buff_for_n1"]:
                        variable_name = "Rte_" + rport["swc_port_var"]
                        struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(rport)
                        buff_struct_type = struct_type
                        buff_struct_name = struct_name
                    else:
                        variable_name = "Rte_" + pport["swc_port_var"]
                        local_counter = "Rte_Counter_Sr_Local_" + pport["swc_port_var"]
                        global_counter = "Rte_Counter_Sr_Global_" + rport["swc_port_var"]
                        struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(pport)
                        sender_buff_struct_type.append(struct_type)
                        sender_buff_struct_name.append(struct_name)
                pport_data.update(
                    {
                        "lock": pport["lock"],
                        "component": pport["component"],
                        "data_type": pport["arg"]["datatype"],
                        "data_category": pport["arg"]["datatype"]["native_category"],
                        "variable_name": variable_name,
                        "lock_id": lock_id,
                        "spinlock_api_postfix": "Write" if pport.get("spinlock_cfg", {}).get("is_rw", False) else "",
                        "local_counter": local_counter,
                        "global_counter": global_counter,
                        "signal_category": pport["signal_category"],
                        "message_name": pport["message_name"] if "message_name" in pport else None,
                        "network": pport["network"] if "network" in pport else None,
                        "buff_struct_type": buff_struct_type,
                        "buff_struct_name": buff_struct_name,
                        "sender_buff_struct_type": sender_buff_struct_type,
                        "sender_buff_struct_name": sender_buff_struct_name,
                    }
                )

            pport_data["runnable_name"] = pport["runnable"][0]
            runnable_symbol = pport["symbol"][0]
            if runnable_symbol not in port_dict:
                continue
            port_dict[runnable_symbol]["pport_data"].append(pport_data)
            if "set_events" in pport:
                port_dict[runnable_symbol]["set_events"].extend(pport["set_events"])

    @staticmethod
    def _set_implicit_rport(port_dict, swc):
        for rport in swc["rports"].values():
            if rport["type"] != "Implicit Receiver":
                continue
            if rport["m_to_n"] == "mn":
                continue
            # either port mapping or data mapping or both
            if rport["m_to_n"] == "0" and (
                rport["signal_category"] not in {"Signal", "SignalGroup"} or rport["data_mapping_m_to_n"] == "0"
            ):
                continue

            if rport["imp_sr_copy_buf_opt"]:
                continue

            rport_data = dict(rport)
            if rport["m_to_n"] != "0":
                # intra ecu
                # the ioc_id has the same name as variable_name
                variable_name = None
                all_sender_buffer = []
                all_sender_counter = []
                global_counter = None
                buff_struct_type = None
                buff_struct_name = None
                sender_buff_struct_type = []
                sender_buff_struct_name = []
                if rport["m_to_n"] in {"11", "1n"}:
                    pport = rport["conn_asw_ports"][0]
                    variable_name = "Rte_" + pport["swc_port_var"]
                    lock_id = variable_name
                    struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(pport)
                    buff_struct_type = struct_type
                    buff_struct_name = struct_name
                else:
                    variable_name = "Rte_" + rport["swc_port_var"]
                    lock_id = variable_name
                    struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(rport)
                    buff_struct_type = struct_type
                    buff_struct_name = struct_name
                    if not rport["single_rec_buff_for_n1"]:
                        global_counter = "Rte_Counter_Sr_Global_" + rport["swc_port_var"]
                        for pport in rport["conn_asw_ports"]:
                            all_sender_buffer.append(("Rte_" + pport["swc_port_var"], pport["osapplication"]))
                            all_sender_counter.append(
                                ("Rte_Counter_Sr_Local_" + pport["swc_port_var"], pport["osapplication"])
                            )
                            struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(pport)
                            sender_buff_struct_type = struct_type
                            sender_buff_struct_name = struct_name
                rport_data.update(
                    {
                        "lock": rport["lock"],
                        "port_dataelement": rport["port_prototype"] + "_" + rport["data_element"],
                        "component": rport["component"],
                        "data_type": rport["arg"]["datatype"],
                        "data_category": rport["arg"]["datatype"]["native_category"],
                        "variable_name": variable_name,
                        "lock_id": lock_id,
                        "spinlock_api_postfix": "Read" if rport.get("spinlock_cfg", {}).get("is_rw", False) else "",
                        "all_sender_buffer": all_sender_buffer,
                        "all_sender_counter": all_sender_counter,
                        "global_counter": global_counter,
                        "signal_category": rport["signal_category"],
                        "message_name": rport["message_name"] if "message_name" in rport else None,
                        "network": rport["network"] if "network" in rport else None,
                        "buff_struct_type": buff_struct_type,
                        "buff_struct_name": buff_struct_name,
                        "sender_buff_struct_type": sender_buff_struct_type,
                        "sender_buff_struct_name": sender_buff_struct_name,
                    }
                )

            rport_data["runnable_name"] = rport["runnable"][0]
            runnable_symbol = rport["symbol"][0]
            if runnable_symbol not in port_dict:
                continue
            port_dict[runnable_symbol]["rport_data"].append(rport_data)

    @staticmethod
    @pass_context
    def get_cross_core_cs_data_dict(context):
        port_dict = {}
        for swc in context["asw_cfg"].values():
            Function._set_cs_pport(port_dict, swc)
            Function._set_cs_rport(port_dict, swc)
        return port_dict

    @staticmethod
    @pass_context
    def get_cross_core_cs_data_dict_values(context):
        values = list(Function.get_cross_core_cs_data_dict(context).values())
        values.sort(key=lambda x: (x["component"], x["port_name"]))
        return values

    @staticmethod
    def has_waiting_event(rports):
        for rp in rports:
            if rp["return_mode"] in {"waiting", "sync"} and len(rp["no_dup_task"]) == 1:
                return True
        return False

    @staticmethod
    def _peer_return_mode(rports):
        has_polling = any(p["return_mode"] == "polling" for p in rports)
        has_waiting = any(p["return_mode"] == "waiting" for p in rports)
        if has_polling and has_waiting:
            return "mixed"
        elif has_polling:
            return "polling"
        elif has_waiting:
            return "waiting"
        else:
            return "none"

    @staticmethod
    def _set_cs_pport(port_dict, swc):
        for pport in swc["pports"].values():
            if pport["type"] != "Server" or pport["ioc"] is False:
                continue
            if pport["connected_ports"]["category"] in ["1:1", "1:N"]:
                args = list(pport["operation"]["args"].values())
                shared_data = "clientData"
                args = list(
                    map(
                        lambda x: (
                            f"{shared_data}->" + x["name"]
                            if (
                                (x["direction"] in ["OUT", "INOUT"])
                                or (
                                    x["direction"] == "IN"
                                    and "category" in x
                                    and (
                                        x["category"] == "ARRAY"
                                        or x["category"] == "STRUCTURE"
                                        or x["category"] == "UNION"
                                    )
                                )
                            )
                            else f"*({shared_data}->" + x["name"] + ")"
                        ),
                        args,
                    )
                )
                pport_data = {
                    "port_name": pport["name"],
                    "component": pport["component"],
                    "return_trigger_flag": any(
                        rp["return_trigger_event"]["ret_trigger_flag"] for rp in pport["connected_ports"]["ports"]
                    ),
                    "peer_return_mode": Function._peer_return_mode(pport["connected_ports"]["ports"]),
                    "has_waiting_event": Function.has_waiting_event(pport["connected_ports"]["ports"]),
                    "client_num": len(pport["connected_ports"]["ports"]),
                    "args": args,
                    "return_type": pport["operation"]["return_type"],
                    "port_def_args": pport["port_def_args"],
                    "queue": list(pport["queue"].values())[0],
                }
                # the runnable attr of C/S pport is symbol
                port_dict[pport["runnable"]] = pport_data

    @staticmethod
    def _set_cs_rport(port_dict, swc):
        for rport in swc["rports"].values():
            if rport["type"] not in ["Sync Client", "Async Client"] or rport["ioc"] is False:
                continue
            if rport["connected_ports"]["category"] in ["1:1", "1:N"]:
                args = list(rport["operation"]["args"].values())
                shared_data = "clientData"
                args = list(
                    map(
                        lambda x: (
                            f"&({shared_data}->" + x["name"] + ")"
                            if x["direction"] in ["OUT", "INOUT"]
                            else f"{shared_data}->" + x["name"]
                        ),
                        args,
                    )
                )
                pport = rport["connected_ports"]["ports"][0]
                pport_data = {
                    "port_name": pport["name"],
                    "component": pport["component"],
                    "client_num": rport["client_num"],
                    "args": args,
                    "return_type": rport["operation"]["return_type"],
                    "queue": list(rport["queue"].values())[0],
                }
                port_dict[f"{rport['component']}_{rport['name']}"] = pport_data

    @staticmethod
    @pass_context
    def get_can_enter_exclusive_areas(context, runnables):
        exclusive_area_infos = {}
        for runnable in runnables:
            if "exclusive_areas" not in runnable or not runnable["exclusive_areas"]:
                continue
            for exclusive_area in runnable["exclusive_areas"]:
                if exclusive_area["access_mode"] != "CAN_ENTER":
                    continue
                exclusive_area_info = {}
                exclusive_area_info["name"] = exclusive_area["name"]
                exclusive_area_info["input_param"] = ""
                if exclusive_area["implementation"] == "ALL_INTERRUPT_BLOCKING":
                    exclusive_area_info["suspend"] = "SuspendAllInterrupts"
                    exclusive_area_info["resume"] = "ResumeAllInterrupts"
                elif exclusive_area["implementation"] == "OS_INTERRUPT_BLOCKING":
                    exclusive_area_info["suspend"] = "SuspendOSInterrupts"
                    exclusive_area_info["resume"] = "ResumeOSInterrupts"
                elif exclusive_area["implementation"] == "OS_RESOURCE":
                    exclusive_area_info["suspend"] = "GetResource"
                    exclusive_area_info["resume"] = "ReleaseResource"
                    exclusive_area_info["input_param"] = (
                        "(ResourceType)Rte_Res_" + exclusive_area["swc_or_module_name"] + "_" + exclusive_area["name"]
                    )
                elif exclusive_area["implementation"] == "NONE":
                    exclusive_area_info["ea_empty_imp"] = True
                else:
                    continue
                exclusive_area_infos[exclusive_area["name"]] = exclusive_area_info
        exclusive_area_info_list = sorted(
            list(exclusive_area_infos.values()), key=lambda x: (len(x["name"]), x["name"].lower())
        )
        return exclusive_area_info_list

    # 获取R端需要的PPort,用于Task
    @staticmethod
    @pass_context
    def get_appl_task_mode_switch_port_list(context, appl_name, task_name=None, with_pport="no"):
        mode_switch_pports = []
        port_name_set = set()
        all_ms_pport_dict = {}
        for swc in context["appls_asw_cfg"].values():
            for pport in swc["pports"].values():
                if pport["type"] == "ModeSwitch" and pport["swc_mode_switch_event"]:
                    pport_name = pport.get("port_name", None)
                    swc_name = pport.get("swc_name", None)
                    if not pport_name or not swc_name:
                        continue
                    all_ms_pport_dict.update({(swc_name, pport_name): pport})
        for swc in context["asw_cfg"].values():
            for rport in swc["rports"].values():
                if rport["type"] == "ModeNotification" and rport["swc_mode_switch_event"]:
                    connected_pport_name = rport.get("connect_port_name", None)
                    connected_component_name = rport.get("connected_component_name", None)
                    if not connected_pport_name or not connected_component_name:
                        continue
                    pport = all_ms_pport_dict.get((connected_component_name, connected_pport_name), None)
                    if not pport:
                        continue
                    for event_catgory, mode_switch_events in rport["swc_mode_switch_event"].items():
                        for mode_switch_event in mode_switch_events:
                            if (
                                task_name
                                and mode_switch_event["task"] == task_name
                                and mode_switch_event["osapplication"] == appl_name
                            ):
                                if (connected_component_name, connected_pport_name) not in port_name_set:
                                    mode_switch_pports.append(pport)
                                    port_name_set.add((connected_component_name, connected_pport_name))
                            if task_name is None and mode_switch_event["osapplication"] == appl_name:
                                if (connected_component_name, connected_pport_name) not in port_name_set:
                                    mode_switch_pports.append(pport)
                                    port_name_set.add((connected_component_name, connected_pport_name))
        if with_pport == "yes":
            for (c_name, p_name), pport in all_ms_pport_dict.items():
                if pport["osapplication"] == appl_name and (c_name, p_name) not in port_name_set:
                    mode_switch_pports.append(pport)
                    port_name_set.add((c_name, p_name))
        Function.__get_and_set_max_memmap_in_osa(mode_switch_pports, "mem_ack_flags")
        for pport in mode_switch_pports:
            infix = Function.__update_ms_memmap_infix(pport["memmap"], appl_name, pport["core_id"])
            pport.update({"infix": infix})
        mode_switch_pports.sort(key=lambda x: x["port_name"])
        return mode_switch_pports

    @staticmethod
    @pass_context
    def __get_and_set_max_memmap_in_osa(ports, mem_filter):
        # ack flags memmap should consider memmmap of all ports
        if ports:
            max_ack_flags = max(port["memmap"][mem_filter] for port in ports)
            for port in ports:
                port["memmap"][mem_filter] = max_ack_flags

    @staticmethod
    @pass_context
    def get_all_mode_switch_event_mask_list(context, appl_name, task_name, mode_switch_pport):
        mode_switch_event_list = []
        mode_switch_event_mask_list = []
        for event_catgory, mode_switch_events in mode_switch_pport["swc_mode_switch_event"].items():
            for mode_switch_event in mode_switch_events:
                if mode_switch_event["task"] == task_name and mode_switch_event["osapplication"] == appl_name:
                    mode_switch_event_list.append(mode_switch_event)

        defalt_event_mask = f"Rte_Ev_MS_{task_name}".upper()
        if len(mode_switch_event_list):
            mode_switch_event_mask_list.append(defalt_event_mask)
        for mode_switch_event in mode_switch_event_list:
            swc_name = mode_switch_event["swc_name"]
            runnable_name = mode_switch_event["runnable_name"]
            event_mask_name = f"Rte_Ev_Run_{swc_name}_{runnable_name}".upper()
            mode_switch_event_mask_list.append(event_mask_name)
        mode_switch_event_mask_list.sort()
        return mode_switch_event_mask_list

    @staticmethod
    @pass_context
    def get_mode_switch_event_triggered_task(context, mode_switch_pport):
        task_name = None
        for event_catgory, mode_switch_events in mode_switch_pport["swc_mode_switch_event"].items():
            for mode_switch_event in mode_switch_events:
                if mode_switch_event["task"] and mode_switch_event["osapplication"]:
                    task_name = mode_switch_event["task"]
                    break
        return task_name

    @staticmethod
    @pass_context
    def get_all_mode_disabled_pports(context, osa=None):
        ret = []
        for swc_dict in context["asw_cfg"].values():
            if osa and (swc_dict["osapplication"] != osa):
                continue
            for pport in swc_dict["pports"].values():
                if ("port_interface_type" not in pport) or pport["port_interface_type"] != "mode":
                    continue
                if not pport["mode_disabled_entity"]:
                    continue
                ret.append(pport)
        Function.__get_and_set_max_memmap_in_osa(ret, "mem_mode_dis_trig")
        for pport in ret:
            infix = Function.__update_ms_memmap_infix(pport["memmap"], osa, pport["core_id"])
            pport.update({"infix": infix})
        ret.sort(key=lambda x: (x["swc_name"], x["port_name"], x["mode_group_prototype"]))
        return ret

    @staticmethod
    @pass_context
    def get_runs_inside_exclusive_areas(context, runnable_name, task_name):
        task = context["task_mappings"][task_name]
        runnable = task["schedulable_entity"][runnable_name]
        if "exclusive_areas" not in runnable or not runnable["exclusive_areas"]:
            return []
        exclusive_area_infos = {}
        for exclusive_area in runnable["exclusive_areas"]:
            if exclusive_area["access_mode"] != "RUNS_INSIDE":
                continue
            exclusive_area_info = {}
            exclusive_area_info["name"] = exclusive_area["name"]
            exclusive_area_info["input_param"] = ""
            if exclusive_area["implementation"] == "ALL_INTERRUPT_BLOCKING":
                exclusive_area_info["suspend"] = "SuspendAllInterrupts"
                exclusive_area_info["resume"] = "ResumeAllInterrupts"
            elif exclusive_area["implementation"] == "OS_INTERRUPT_BLOCKING":
                exclusive_area_info["suspend"] = "SuspendOSInterrupts"
                exclusive_area_info["resume"] = "ResumeOSInterrupts"
            elif exclusive_area["implementation"] == "OS_RESOURCE":
                exclusive_area_info["suspend"] = "(void)GetResource"
                exclusive_area_info["resume"] = "(void)ReleaseResource"
                exclusive_area_info["input_param"] = (
                    "(ResourceType)Rte_Res_" + exclusive_area["swc_or_module_name"] + "_" + exclusive_area["name"]
                )
            else:
                continue
            exclusive_area_infos[exclusive_area["implementation"]] = exclusive_area_info
        exclusive_area_info_list = sorted(
            list(exclusive_area_infos.values()), key=lambda x: (len(x["name"]), x["name"].lower())
        )
        return exclusive_area_info_list

    @staticmethod
    @pass_context
    def get_mode_switch_port_unconnected_in_swc(context):
        # Used for Rte_SWC.h generation
        mode_switch_rports = []
        mode_switch_pports = []
        for pport in context["swc"]["pports"].values():
            if pport["type"] == "ModeSwitch" and not pport["connected_port_path_list"]:
                mode_switch_pports.append(pport)
        for rport in context["swc"]["rports"].values():
            if rport["type"] == "ModeNotification" and not rport["connect_port_name"]:
                mode_switch_rports.append(rport)
        if len(mode_switch_pports) > 0:
            mode_switch_pports.sort(
                key=lambda x: (x["swc_name"].lower(), x["port_name"].lower(), x["mode_group_prototype"].lower())
            )
        if len(mode_switch_rports) > 0:
            mode_switch_rports.sort(
                key=lambda x: (x["swc_name"].lower(), x["port_name"].lower(), x["mode_group_prototype"].lower())
            )
        return mode_switch_rports, mode_switch_pports

    @staticmethod
    @pass_context
    def get_mode_switch_port_connected_in_swc(context):
        # Used for Rte_SWC.h generation
        mode_switch_rports = []
        mode_switch_pports = []
        for pport in context["swc"]["pports"].values():
            if pport["type"] == "ModeSwitch" and pport["connected_port_path_list"]:
                mode_switch_pports.append(pport)
        for rport in context["swc"]["rports"].values():
            if rport["type"] == "ModeNotification" and rport["connect_port_name"]:
                mode_switch_rports.append(rport)
        if len(mode_switch_pports) > 0:
            mode_switch_pports.sort(
                key=lambda x: (x["swc_name"].lower(), x["port_name"].lower(), x["mode_group_prototype"].lower())
            )
        if len(mode_switch_rports) > 0:
            mode_switch_rports.sort(
                key=lambda x: (x["swc_name"].lower(), x["port_name"].lower(), x["mode_group_prototype"].lower())
            )
        return mode_switch_rports, mode_switch_pports

    @staticmethod
    @pass_context
    def get_all_mode_switch_port_connected_in_swc(context):
        # Used for Rte_SWC.h generation
        mode_switch_rports = []
        mode_switch_pports = []
        for swc in context["asw_cfg"].values():
            for pport in swc["pports"].values():
                if pport["type"] == "ModeSwitch" and pport["connected_port_path_list"]:
                    mode_switch_pports.append(pport)
            for rport in swc["rports"].values():
                if rport["type"] == "ModeNotification" and rport["connect_port_name"]:
                    mode_switch_rports.append(rport)
        mode_switch_pports.sort(key=lambda x: (x["swc_name"], x["port_name"], x["mode_group_prototype"]))
        mode_switch_rports.sort(key=lambda x: (x["swc_name"], x["port_name"], x["mode_group_prototype"]))
        return mode_switch_rports, mode_switch_pports

    @staticmethod
    @pass_context
    def get_mode_group_list_in_swc(context):
        # Used for Rte_SWC_Type.h generation
        all_mode_group = context["mode_declaration_group"]
        mode_group_set = set()
        mode_group_list = []
        for pport in context["swc"]["pports"].values():
            if pport["type"] == "ModeSwitch" and pport["mode_group"] in all_mode_group:
                if pport["mode_group"] not in mode_group_set:
                    mode_group_set.add(pport["mode_group"])
                    mode_group_list.append(all_mode_group[pport["mode_group"]])
        for rport in context["swc"]["rports"].values():
            if rport["type"] == "ModeNotification" and rport["mode_group"] in all_mode_group:
                if rport["mode_group"] not in mode_group_set:
                    mode_group_set.add(rport["mode_group"])
                    mode_group_list.append(all_mode_group[rport["mode_group"]])
        return mode_group_list

    @staticmethod
    @pass_context
    def get_mode_switch_port_in_swc(context):
        # Used for Rte_SWC.h generation
        mode_switch_rports = []
        mode_switch_pports = []
        for pport in context["swc"]["pports"].values():
            if pport["type"] == "ModeSwitch":
                mode_switch_pports.append(pport)
        for rport in context["swc"]["rports"].values():
            if rport["type"] == "ModeNotification":
                mode_switch_rports.append(rport)
        return mode_switch_rports, mode_switch_pports

    @staticmethod
    @pass_context
    def get_client_server_port_in_swc(context, runnable=None):
        # Used for Rte_SWC.h generation
        client_server_rports = []
        client_server_pports = []
        for port in context["swc"]["pports"].values():
            if Function.not_port_accessed_runnable(port, runnable):
                continue
            if port["type"] == "Server" and not port["ioc"]:
                client_server_pports.append(port)
        for port in context["swc"]["rports"].values():
            if Function.not_port_accessed_runnable(port, runnable):
                continue
            if port["type"] == "Sync Client" and not port["ioc"]:
                client_server_rports.append(port)
        client_server_rports.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        client_server_pports.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return client_server_rports, client_server_pports

    @staticmethod
    @pass_context
    def get_used_port_interface_list_for_swc(context):
        # Used for Rte_SWC.h generation
        client_server_rports = []
        client_server_pports = []
        for port in context["swc"]["pports"].values():
            if port["type"] == "Server":
                client_server_pports.append(port)
        for port in context["swc"]["rports"].values():
            if port["type"] in ["Sync Client", "Async Client"]:
                client_server_rports.append(port)
        client_server_rports.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        client_server_pports.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        used_port_interface_dict = {}
        for port in client_server_rports + client_server_pports:
            if "port_interface_info" not in port:
                # for parser testccase
                continue
            port_info = port["port_interface_info"]
            if not port_info:
                continue
            for name, error_info in port_info.items():
                if name not in used_port_interface_dict:
                    used_port_interface_dict[name] = error_info
                else:
                    used_port_interface_dict[name].update(error_info)
        return {k: used_port_interface_dict[k] for k in sorted(used_port_interface_dict)}

    @staticmethod
    @pass_context
    def get_client_server_port_in_swc_no_dup(context):
        # Used for Rte_SWC.h generation
        client_server_rports = []
        opration_symbol_set = set()
        for port in context["swc"]["rports"].values():
            if port["type"] == "Sync Client":
                if port["ioc"]:
                    continue
                if port["connected_ports"] is None or len(port["connected_ports"]["ports"]) < 1:
                    continue
                connected_port = port["connected_ports"]["ports"][0]
                if connected_port["symbol"] in opration_symbol_set:
                    continue
                opration_symbol_set.add(connected_port["symbol"])
                client_server_rports.append(port)
        return client_server_rports

    @staticmethod
    @pass_context
    def get_swc_sync_cs_multicore_rports(context, runnable=None):
        rports = []
        for rport in context["swc"]["rports"].values():
            if Function.not_port_accessed_runnable(rport, runnable):
                continue
            if rport["type"] not in ["Sync Client"] or not rport["ioc"]:
                continue
            rports.append(rport)
        rports.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rports

    @staticmethod
    @pass_context
    def get_all_sync_cs_multicore_rports(context):
        rports = []
        for swc in context["asw_cfg"].values():
            for port in swc["rports"].values():
                if port["type"] not in ["Sync Client"] or not port["ioc"]:
                    continue
                rports.append(port)
        rports.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rports

    @staticmethod
    @pass_context
    def get_swc_async_cs_multicore_rports(context, runnable=None):
        rports = []
        for rport in context["swc"]["rports"].values():
            if Function.not_port_accessed_runnable(rport, runnable):
                continue
            if rport["type"] not in ["Async Client"] or not rport["ioc"]:
                continue
            rports.append(rport)
        rports.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rports

    @staticmethod
    @pass_context
    def get_all_async_cs_multicore_rports(context):
        rports = []
        for swc in context["asw_cfg"].values():
            for port in swc["rports"].values():
                if port["type"] not in ["Async Client"] or not port["ioc"]:
                    continue
                rports.append(port)
        rports.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rports

    @staticmethod
    @pass_context
    def get_appl_cs_unconnected_rports(context, appl_name):
        rports = []
        for swc in context["asw_cfg"].values():
            if swc["osapplication"] != appl_name:
                continue
            for rport in swc["rports"].values():
                if (
                    rport["type"] in ["Sync Client", "Async Client"]
                    and not rport["ioc"]
                    and rport["connected_ports"] is None
                ):
                    rports.append(rport)
        rports.sort(key=lambda x: ("args" in x.keys(), len(x["sort_name"]), x["name"].lower()))
        return rports

    @staticmethod
    @pass_context
    def get_all_cs_multicore_rports(context):
        rports = []
        for swc in context["asw_cfg"].values():
            if not swc["osapplication"]:
                continue
            for rport in swc["rports"].values():
                if rport["type"] not in ["Sync Client", "Async Client"] or not rport["ioc"]:
                    continue
                rports.append(rport)
        rports.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rports

    @staticmethod
    @pass_context
    def get_appl_cs_multicore_rports(context, appl_name):
        rports = []
        for rport in Function.get_all_cs_multicore_rports(context):
            if rport["osapplication"] != appl_name:
                continue
            infix = Function.__update_cs_ms_memmap_infix(rport["memmap"], rport["osapplication"], rport["core_id"])
            rport.update({"infix": infix})
            rports.append(rport)
        rports.sort(key=lambda x: ("args" in x.keys(), x["name"].lower(), x["client_id"]))
        return rports

    @staticmethod
    @pass_context
    def __update_cs_ms_memmap_infix(memmap, osa, core_id, rep=[], rep_osa=None):
        rv = {}
        for var, value in memmap.items():
            if rep and var in rep and rep_osa:
                if value == MemmapCategory.OSA_PRIVATE:
                    rv.update({var: f"{rep_osa}_PRIVATE"})
                elif value == MemmapCategory.OSA_SHARED:
                    rv.update({var: f"{rep_osa}_SEMISHARED"})
                elif value == MemmapCategory.CORE_SHARED:
                    rv.update({var: f"MULTI_APP"})
                elif value == MemmapCategory.GLOBAL:
                    rv.update({var: "MULTI_APP"})
                else:
                    rv.update({var: None})
            else:
                if value == MemmapCategory.OSA_PRIVATE:
                    rv.update({var: f"{osa}_PRIVATE"})
                elif value == MemmapCategory.OSA_SHARED:
                    rv.update({var: f"{osa}_SEMISHARED"})
                elif value == MemmapCategory.CORE_SHARED:
                    rv.update({var: f"MULTI_APP"})
                elif value == MemmapCategory.GLOBAL:
                    rv.update({var: "MULTI_APP"})
                else:
                    rv.update({var: None})
        return rv

    @staticmethod
    @pass_context
    def __update_ms_memmap_infix(memmap, osa, core_id, rep=[], rep_osa=None):
        rv = {}
        for var, value in memmap.items():
            if rep and var in rep and rep_osa:
                if value == MemmapCategory.OSA_PRIVATE:
                    rv.update({var: f"{rep_osa}_PRIVATE"})
                elif value == MemmapCategory.OSA_SHARED:
                    rv.update({var: f"{rep_osa}_SEMISHARED"})
                elif value in [MemmapCategory.GLOBAL, MemmapCategory.CORE_SHARED]:
                    rv.update({var: "MULTI_APP"})
                else:
                    rv.update({var: None})
            else:
                if value == MemmapCategory.OSA_PRIVATE:
                    rv.update({var: f"{osa}_PRIVATE"})
                elif value == MemmapCategory.OSA_SHARED:
                    rv.update({var: f"{osa}_SEMISHARED"})
                elif value in [MemmapCategory.GLOBAL, MemmapCategory.CORE_SHARED]:
                    rv.update({var: "MULTI_APP"})
                else:
                    rv.update({var: None})
        return rv

    @staticmethod
    @pass_context
    def get_appl_sync_cs_multicore_without_timeout_rports(context, appl_name):
        rports = []
        for rport in Function.get_appl_cs_multicore_rports(context, appl_name):
            if rport["type"] != "Sync Client" or rport["timeout"] > 0:
                continue
            rport["no_dup_tasks"] = list(set(rport["task"]))
            rport["no_dup_tasks"].sort()
            rports.append(rport)
        rports.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rports

    @staticmethod
    @pass_context
    def get_appl_sync_cs_multicore_timeout_rports(context, appl_name):
        rports = []
        for rport in Function.get_appl_cs_multicore_rports(context, appl_name):
            if rport["type"] != "Sync Client" or rport["timeout"] <= 0:
                continue
            rports.append(rport)
        for rport in rports:
            # one cs rport may be accessed by multi runnables and so it may have multi alamrs,
            # but the alarms' timeouts must be the same (except for zero)
            rport["no_dup_tasks"] = list(set(rport["task"]))
            rport["no_dup_tasks"].sort()

        rports.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rports

    @staticmethod
    @pass_context
    def get_appl_async_cs_multicore_rports(context, appl_name):
        rports = []
        for swc in context["asw_cfg"].values():
            if swc["osapplication"] != appl_name:
                continue
            for rport in swc["rports"].values():
                if rport["type"] not in ["Async Client"] or not rport["ioc"]:
                    continue
                rports.append(rport)
        rports.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rports

    @staticmethod
    @pass_context
    def get_appl_async_cs_multicore_without_timeout_rports(context, appl_name):
        rports = []
        for rport in Function.get_appl_cs_multicore_rports(context, appl_name):
            if rport["type"] != "Async Client" or rport["timeout"] > 0:
                continue
            rports.append(rport)
        rports.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rports

    @staticmethod
    @pass_context
    def get_appl_async_cs_multicore_timeout_rports(context, appl_name):
        rports = []
        for rport in Function.get_appl_async_cs_multicore_rports(context, appl_name):
            if rport["timeout"] <= 0:
                continue
            rports.append(rport)
        rports.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rports

    @staticmethod
    @pass_context
    def get_seconds_per_tick(context, appl_name):
        return float(context.get("os_counter", {}).get(appl_name, {}).get("OsSecondsPerTick", 0.0))

    @staticmethod
    @pass_context
    def _get_cs_ioc_specified_enqueue_dict_by_appl(context, filter, appl_name=None):
        queue_dict = {}
        for swc in context["asw_cfg"].values():
            if appl_name and appl_name != swc["osapplication"]:
                continue
            queues_intra_osa = []
            queues_inter_osa_same_core = []
            queues_inter_core = []

            for client in swc["rports"].values():
                if (
                    client["type"] not in ["Sync Client", "Async Client"]
                    or not client["connected_ports"]
                    or not client["ioc"]
                ):
                    continue
                if filter == "all":
                    pass
                elif filter == "1:1" and client["connected_ports"]["category"] != "1:1":
                    continue
                elif filter == "1:N" and client["connected_ports"]["category"] != "1:N":
                    continue
                queue_name = list(client["queue"].keys())[0]
                queue = list(client["queue"].values())[0]
                infix = Function.__update_cs_ms_memmap_infix(
                    queue["memmap_enq"], client["osapplication"], client["core_id"]
                )
                curr_info = {
                    "name": queue_name,
                    "client_name": queue["client_name"],
                    "component": client["component"],
                    "size": queue["size"],
                    "ioc_type": queue["ioc_type"],
                    "sort_name": client["sort_name"],
                    "infix": infix,
                }
                if queue["ioc_type"] == "SPINLOCK":
                    queues_inter_core.append(curr_info)
                elif queue["ioc_type"] == "OSISR":
                    queues_inter_osa_same_core.append(curr_info)
                else:
                    queues_intra_osa.append(curr_info)

            if queues_intra_osa or queues_inter_osa_same_core or queues_inter_core:
                if swc["osapplication"] not in queue_dict:
                    queue_dict[swc["osapplication"]] = {
                        "intra_osa": [],
                        "inter_osa_same_core": [],
                        "inter_core": [],
                        "core_id": swc["core_id"],
                    }
                queue_dict[swc["osapplication"]]["intra_osa"].extend(queues_intra_osa)
                queue_dict[swc["osapplication"]]["inter_osa_same_core"].extend(queues_inter_osa_same_core)
                queue_dict[swc["osapplication"]]["inter_core"].extend(queues_inter_core)
            for appl_queues in queue_dict.values():
                appl_queues["intra_osa"].sort(key=lambda x: (x["args"] if "args" in x.keys() else "", x["sort_name"]))
                appl_queues["inter_osa_same_core"].sort(
                    key=lambda x: (x["args"] if "args" in x.keys() else "", x["sort_name"])
                )
                appl_queues["inter_core"].sort(key=lambda x: (x["args"] if "args" in x.keys() else "", x["sort_name"]))
        return dict(sorted(queue_dict.items()))

    @staticmethod
    @pass_context
    def _get_cs_ioc_specified_dequeue_dict_by_appl(context, filter, appl_name=None):
        queue_dict = {}
        for swc in context["asw_cfg"].values():
            if appl_name and appl_name != swc["osapplication"]:
                continue
            queues_intra_osa = []
            queues_inter_osa_same_core = []
            queues_inter_core = []

            if not swc["osapplication"]:  # TODO: should not go here
                continue
            for server in swc["pports"].values():
                if server["type"] != "Server" or not server["connected_ports"] or not server["ioc"]:
                    continue
                if filter == "all":
                    pass
                elif filter == "1:1" and server["connected_ports"]["category"] != "1:1":
                    continue
                elif filter == "1:N" and server["connected_ports"]["category"] != "1:N":
                    continue
                queue_name = list(server["queue"].keys())[0]
                queue = list(server["queue"].values())[0]
                infix = Function.__update_cs_ms_memmap_infix(
                    queue["memmap_deq"], server["osapplication"], server["core_id"]
                )
                curr_info = {
                    "name": queue_name,
                    "component": server["component"],
                    "size": queue["size"],
                    "ioc_type": queue["ioc_type"],
                    "sort_name": server["sort_name"],
                    "infix": infix,
                }
                if queue["ioc_type"] == "SPINLOCK":
                    queues_inter_core.append(curr_info)
                elif queue["ioc_type"] == "OSISR":
                    queues_inter_osa_same_core.append(curr_info)
                else:
                    queues_intra_osa.append(curr_info)

            if queues_intra_osa or queues_inter_osa_same_core or queues_inter_core:
                if swc["osapplication"] not in queue_dict:
                    queue_dict[swc["osapplication"]] = {
                        "intra_osa": [],
                        "inter_osa_same_core": [],
                        "inter_core": [],
                        "core_id": swc["core_id"],
                    }
                queue_dict[swc["osapplication"]]["intra_osa"].extend(queues_intra_osa)
                queue_dict[swc["osapplication"]]["inter_osa_same_core"].extend(queues_inter_osa_same_core)
                queue_dict[swc["osapplication"]]["inter_core"].extend(queues_inter_core)
            for appl_queues in queue_dict.values():
                appl_queues["intra_osa"].sort(key=lambda x: (x["args"] if "args" in x.keys() else "", x["sort_name"]))
                appl_queues["inter_osa_same_core"].sort(
                    key=lambda x: (x["args"] if "args" in x.keys() else "", x["sort_name"])
                )
                appl_queues["inter_core"].sort(key=lambda x: (x["args"] if "args" in x.keys() else "", x["sort_name"]))
        return dict(sorted(queue_dict.items()))

    @staticmethod
    @pass_context
    def get_all_cs_ioc_1to1_enqueue_dict_by_appl(context, appl_name=None, is_result_combined=False):
        info = Function._get_cs_ioc_specified_enqueue_dict_by_appl(context, "1:1", appl_name)
        if is_result_combined:
            combined_info = {}
            for osa, queues in info.items():
                combined_info[osa] = []
                combined_info[osa].extend(queues["intra_osa"])
                combined_info[osa].extend(queues["inter_osa_same_core"])
                combined_info[osa].extend(queues["inter_core"])
            return combined_info
        else:
            return info

    @staticmethod
    @pass_context
    def get_all_cs_ioc_enqueue_dict_by_appl(context, appl_name=None, is_result_combined=False):
        info = Function._get_cs_ioc_specified_enqueue_dict_by_appl(context, "all", appl_name)
        if is_result_combined:
            combined_info = {}
            for osa, queues in info.items():
                combined_info[osa] = []
                combined_info[osa].extend(queues["intra_osa"])
                combined_info[osa].extend(queues["inter_osa_same_core"])
                combined_info[osa].extend(queues["inter_core"])
            return combined_info
        else:
            return info

    @staticmethod
    @pass_context
    def get_all_cs_ioc_1toN_dequeue_dict_by_appl(context, appl_name=None):
        return Function._get_cs_ioc_specified_dequeue_dict_by_appl(context, "1:N", appl_name)

    @staticmethod
    @pass_context
    def get_all_cs_ioc_1toN_enqueue_dict_by_appl(
        context, appl_name=None, var_filter=None, mem_filter=None, is_result_combined=False
    ):
        info = Function._get_cs_ioc_specified_enqueue_dict_by_appl(context, "1:N", appl_name)
        ret = {}
        if var_filter and mem_filter:
            for osa, queues in info.items():
                core_id = queues["core_id"]
                if osa not in ret:
                    ret[osa] = {"intra_osa": [], "inter_osa_same_core": [], "inter_core": []}
                for queue in queues["intra_osa"]:
                    if mem_filter == "PRIVATE" and queue["infix"][var_filter] == f"{osa}_PRIVATE":
                        ret[osa]["intra_osa"].append(queue)
                    elif mem_filter == "SHARED_OSA" and queue["infix"][var_filter] == f"{osa}_SEMISHARED":
                        ret[osa]["intra_osa"].append(queue)
                    elif mem_filter == "SHARED_CORE" and queue["infix"][var_filter] == f"MULTI_APP":
                        ret[osa]["intra_osa"].append(queue)
                    elif mem_filter == "GLOBAL" and queue["infix"][var_filter] == "MULTI_APP":
                        ret[osa]["intra_osa"].append(queue)
                for queue in queues["inter_osa_same_core"]:
                    if mem_filter == "PRIVATE" and queue["infix"][var_filter] == f"{osa}_PRIVATE":
                        ret[osa]["inter_osa_same_core"].append(queue)
                    elif mem_filter == "SHARED_OSA" and queue["infix"][var_filter] == f"{osa}_SEMISHARED":
                        ret[osa]["inter_osa_same_core"].append(queue)
                    elif mem_filter == "SHARED_CORE" and queue["infix"][var_filter] == f"MULTI_APP":
                        ret[osa]["inter_osa_same_core"].append(queue)
                    elif mem_filter == "GLOBAL" and queue["infix"][var_filter] == "MULTI_APP":
                        ret[osa]["inter_osa_same_core"].append(queue)
                for queue in queues["inter_core"]:
                    if mem_filter == "PRIVATE" and queue["infix"][var_filter] == f"{osa}_PRIVATE":
                        ret[osa]["inter_core"].append(queue)
                    elif mem_filter == "SHARED_OSA" and queue["infix"][var_filter] == f"{osa}_SEMISHARED":
                        ret[osa]["inter_core"].append(queue)
                    elif mem_filter == "SHARED_CORE" and queue["infix"][var_filter] == f"MULTI_APP":
                        ret[osa]["inter_core"].append(queue)
                    elif mem_filter == "GLOBAL" and queue["infix"][var_filter] == "MULTI_APP":
                        ret[osa]["inter_core"].append(queue)
        if is_result_combined:
            combined_ret = {}
            queue_name_set = set()
            osa_class_list = ["intra_osa", "inter_osa_same_core", "inter_core"]
            for osa, queues in ret.items():
                combined_ret[osa] = []
                for osa_class in osa_class_list:
                    for queue in queues[osa_class]:
                        if queue["name"] in queue_name_set:
                            continue
                        combined_ret[osa].append(queue)
                        queue_name_set.add(queue["name"])
            return combined_ret
        else:
            return ret

    @staticmethod
    @pass_context
    def get_all_shared_osa_cs_ioc_1toN_enqueue_dict_by_appl(
        context, appl_name=None, filter=None, is_result_combined=False
    ):
        info = Function._get_cs_ioc_specified_enqueue_dict_by_appl(context, "1:N", appl_name)
        ret = {}
        if filter:
            for osa, queues in info.items():
                for queue in queues["intra_osa"]:
                    if queue["infix"][f"mem_q_{filter}"] != f"SHARED_{osa}_VAR":
                        continue
                    ret[osa]["intra_osa"].append(queue)
                for queue in queues["inter_osa_same_core"]:
                    if queue["infix"][f"mem_q_{filter}"] != f"SHARED_{osa}_VAR":
                        continue
                    ret[osa]["inter_osa_same_core"].append(queue)
                for queue in queues["inter_core"]:
                    if queue["infix"][f"mem_q_{filter}"] != f"SHARED_{osa}_VAR":
                        continue
                    ret[osa]["inter_core"].append(queue)
        if is_result_combined:
            combined_ret = {}
            for osa, queues in ret.items():
                combined_ret[osa] = []
                combined_ret[osa].extend(queues["intra_osa"])
                combined_ret[osa].extend(queues["inter_osa_same_core"])
                combined_ret[osa].extend(queues["inter_core"])
            return combined_ret
        else:
            return ret

    @staticmethod
    @pass_context
    def get_all_shared_core_cs_ioc_1toN_enqueue_dict_by_appl(
        context, appl_name=None, filter=None, is_result_combined=False
    ):
        info = Function._get_cs_ioc_specified_enqueue_dict_by_appl(context, "1:N", appl_name)
        ret = {}
        if filter:
            for osa, queues in info.items():
                for queue in queues["intra_osa"]:
                    if queue["infix"][f"mem_q_{filter}"] != f"SHARED_{osa}_VAR":
                        continue
                    ret[osa]["intra_osa"].append(queue)
                for queue in queues["inter_osa_same_core"]:
                    if queue["infix"][f"mem_q_{filter}"] != f"SHARED_{osa}_VAR":
                        continue
                    ret[osa]["inter_osa_same_core"].append(queue)
                for queue in queues["inter_core"]:
                    if queue["infix"][f"mem_q_{filter}"] != f"SHARED_{osa}_VAR":
                        continue
                    ret[osa]["inter_core"].append(queue)
        if is_result_combined:
            combined_ret = {}
            for osa, queues in ret.items():
                combined_ret[osa] = []
                combined_ret[osa].extend(queues["intra_osa"])
                combined_ret[osa].extend(queues["inter_osa_same_core"])
                combined_ret[osa].extend(queues["inter_core"])
            return combined_ret
        else:
            return ret

    @staticmethod
    @pass_context
    def get_all_cs_ioc_1to1_dequeue_dict_by_appl(context, appl_name=None):
        return Function._get_cs_ioc_specified_dequeue_dict_by_appl(context, "1:1", appl_name)

    @staticmethod
    @pass_context
    def get_all_cs_ioc_dequeue_dict_by_appl(context, appl_name=None, is_result_combined=False):
        info = Function._get_cs_ioc_specified_dequeue_dict_by_appl(context, "all", appl_name)
        if is_result_combined:
            combined_info = {}
            for osa, queues in info.items():
                combined_info[osa] = []
                combined_info[osa].extend(queues["intra_osa"])
                combined_info[osa].extend(queues["inter_osa_same_core"])
                combined_info[osa].extend(queues["inter_core"])
            return combined_info
        else:
            return info

    @staticmethod
    def __sort_cs_pports(cs_pports):
        cs_pports.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        for port in cs_pports:
            if port["connected_ports"] and "ports" in port["connected_ports"]:
                rports = port["connected_ports"]["ports"]
                for rport in rports:
                    rport["no_dup_task"] = list(set(rport["task"]))
                    rport["no_dup_task"].sort()
                if len(rports) > 1:
                    rports.sort(key=lambda x: (x["client_id"]))

    @staticmethod
    @pass_context
    def get_all_cs_multicore_pports(context):
        pports = []
        for swc in context["asw_cfg"].values():
            if not swc["osapplication"]:
                continue
            for pport in swc["pports"].values():
                if pport["type"] not in ["Server"] or not pport["ioc"]:
                    continue
                pports.append(pport)
        Function.__sort_cs_pports(pports)
        return pports

    @staticmethod
    @pass_context
    def get_all_cs_non_direct_rports_extern(context):
        data = {}
        for pport in Function.get_all_cs_multicore_pports(context):
            for rport in pport["connected_ports"]["ports"]:
                osa = rport["osapplication"]
                if osa not in data:
                    data[osa] = []
                data[osa].append((rport, pport))
        return data

    @staticmethod
    @pass_context
    def get_all_cs_non_direct_pports_extern(context):
        data = {}
        for pport in Function.get_all_cs_multicore_pports(context):
            osa = pport["osapplication"]
            if osa not in data:
                data[osa] = []
            for rport in pport["connected_ports"]["ports"]:
                data[osa].append((pport, rport))
        return data

    @staticmethod
    @pass_context
    def get_all_cs_non_direct_inout_arg_extern(context):
        data = []
        for pport in Function.get_all_cs_multicore_pports(context):
            for arg in pport["operation"]["args"].values():
                if arg["direction"] == "INOUT":
                    for rport in pport["connected_ports"]["ports"]:
                        infix = Function.__update_cs_ms_memmap_infix(
                            rport["memmap"], rport["osapplication"], rport["core_id"]
                        )
                        rport.update({"infix": infix})
                        data.append([arg, pport, rport])
        return data

    @staticmethod
    @pass_context
    def get_appl_cs_multicore_pports(context, app_name):
        pports = []
        for swc in context["asw_cfg"].values():
            if swc["osapplication"] != app_name:
                continue
            for pport in swc["pports"].values():
                if pport["type"] not in ["Server"] or not pport["ioc"]:
                    continue
                pport.update({"infix": {}})
                for rport in pport["connected_ports"]["ports"]:
                    infix = Function.__update_cs_ms_memmap_infix(
                        rport["memmap"], pport["osapplication"], pport["core_id"]
                    )
                    rport.update({"infix": infix})
                pports.append(pport)
        Function.__sort_cs_pports(pports)
        return pports

    @staticmethod
    def get_appl_cs_in_args(operation_args):
        args = []
        for arg in operation_args.values():
            if arg["direction"] not in ["IN", "INOUT"]:
                continue
            args.append(arg)
        return args

    @staticmethod
    def get_appl_cs_out_args(operation_args):
        args = []
        for arg in operation_args.values():
            if arg["direction"] not in ["OUT", "INOUT"]:
                continue
            args.append(arg)
        return args

    @staticmethod
    @pass_context
    def get_base_type_impl_type_map(context):
        base_type_impl_type_map = {}
        client_server_rports = []
        for swc in context["asw_cfg"].values():
            for port in swc["rports"].values():
                if port["type"] == "Client":
                    client_server_rports.append(port)
            runnables = swc["runnables"]
            for runnable in runnables.values():
                if "args" not in runnable:
                    continue
                for arg in runnable["args"]:
                    if "type_def_in_c" in arg and arg["type_def_in_c"]:
                        base_type_impl_type_map[arg["type"]] = arg["type_def_in_c"]
        for client_server_rport in client_server_rports:
            port_def_args = client_server_rport["port_def_args"]
            if port_def_args and port_def_args["type_def_in_c"]:
                base_type_impl_type_map[port_def_args["data_type"]] = port_def_args["type_def_in_c"]
            for operation_symbol_pair in client_server_rport["operation_symbol_pair_list"]:
                for typedef_in_c in operation_symbol_pair["type_def_in_c_list"]:
                    if typedef_in_c["type_def_in_c"]:
                        base_type_impl_type_map[typedef_in_c["type"]] = typedef_in_c["type_def_in_c"]
        return base_type_impl_type_map

    @staticmethod
    @pass_context
    def get_mode_switch_pports_appl_all_swc(context, appl_name):
        mode_switch_pports = []
        for swc in context["asw_cfg"].values():
            for pport in swc["pports"].values():
                if (
                    pport["type"] == "ModeSwitch"
                    and pport["swc_mode_switch_event"]
                    and appl_name == pport["osapplication"]
                ):
                    mode_switch_pports.append(pport)
        return mode_switch_pports

    @staticmethod
    @pass_context
    def get_mode_switch_event_pport_all_swc_all_appl(context, appl_list):
        mode_switch_pports = []
        for appl_name in appl_list:
            mode_switch_pports.extend(Function.get_mode_switch_event_pport_all_swc_same_appl(context, appl_name))
        return mode_switch_pports

    @staticmethod
    @pass_context
    def has_ioc_replacment(context, appl_list):
        return len(Function.get_mode_switch_event_pport_all_swc_all_appl(context, appl_list)) > 0

    @staticmethod
    @pass_context
    def get_mode_switch_event_pport_all_swc_same_appl(context, appl_name):
        mode_switch_pports = []
        for swc in context["asw_cfg"].values():
            for pport in swc["pports"].values():
                if pport["type"] == "ModeSwitch" and pport["swc_mode_switch_event"]:
                    if appl_name == pport["osapplication"]:
                        mode_switch_pports.append(pport)
        for pport in mode_switch_pports:
            infix = Function.__update_ms_memmap_infix(
                pport["memmap"],
                pport["osapplication"],
                pport["core_id"],
                ["mem_head"],
                pport["connected_osapplication"],
            )

            pport.update({"infix": infix})
        if len(mode_switch_pports) > 0:
            mode_switch_pports.sort(
                key=lambda x: (x["swc_name"].lower(), x["port_name"].lower(), x["mode_group_prototype"].lower())
            )
        return mode_switch_pports

    @staticmethod
    @pass_context
    def get_mode_switch_pports_with_transition_event(context):
        mode_switch_pports = []
        for swc in context["appls_asw_cfg"].values():
            for pport in swc["pports"].values():
                if (
                    pport["type"] == "ModeSwitch"
                    and pport["swc_mode_switch_event"]
                    and pport["swc_mode_switch_event"].get("transition_events")
                ):
                    mode_switch_pports.append(pport)
        if len(mode_switch_pports) > 0:
            mode_switch_pports.sort(
                key=lambda x: (x["swc_name"].lower(), x["port_name"].lower(), x["mode_group_prototype"].lower())
            )
        return mode_switch_pports

    @staticmethod
    @pass_context
    def get_transition_event_ev_mask_list_for_same_mode(context, transition_events):
        events_ev_mask_list_for_mode = {}
        # {(pre_mode_name, next_mode_name) : ["evmask1", "evmask2"]}
        for transition_event in transition_events:
            pre_mode = transition_event["previous_mode"]["name"]
            next_mode = transition_event["next_mode"]["name"]
            runnable_name = transition_event["runnable_name"]
            swc_name = transition_event["swc_name"]
            ev_mask_name = f"Rte_Ev_Run_{swc_name}_{runnable_name}".upper()
            if (pre_mode, next_mode) not in events_ev_mask_list_for_mode:
                events_ev_mask_list_for_mode.update({(pre_mode, next_mode): [ev_mask_name]})
                continue
            events_ev_mask_list_for_mode[(pre_mode, next_mode)].append(ev_mask_name)
        sorted_dict = dict(sorted(events_ev_mask_list_for_mode.items(), key=lambda x: (x[0][0], x[0][1])))
        return sorted_dict

    @staticmethod
    @pass_context
    def get_transition_events_for_same_mode(context, transition_events):
        events_set_for_tansition = set()
        new_transition_events = []
        for transition_event in transition_events:
            pre_mode = transition_event["previous_mode"]["value"]
            next_mode = transition_event["next_mode"]["value"]
            if (pre_mode, next_mode) not in events_set_for_tansition:
                new_transition_events.append(transition_event)
                events_set_for_tansition.add((pre_mode, next_mode))
        new_transition_events.sort(key=lambda x: (x["previous_mode"]["name"]))
        return new_transition_events

    @staticmethod
    @pass_context
    def get_entry_events_ev_mask_list_for_same_mode(context, entry_events):
        entry_events_ev_mask_list_for_mode = {}
        # {mode1 : ["evmask1", "evmask2"]}
        for entry_event in entry_events:
            mode = entry_event["mode"]["value"]
            swc_name = entry_event["swc_name"]
            runnable_name = entry_event["runnable_name"]
            ev_mask_name = f"Rte_Ev_Run_{swc_name}_{runnable_name}".upper()
            if mode not in entry_events_ev_mask_list_for_mode:
                entry_events_ev_mask_list_for_mode.update({mode: [ev_mask_name]})
                continue
            entry_events_ev_mask_list_for_mode[mode].append(ev_mask_name)
        sorted_dict = dict(sorted(entry_events_ev_mask_list_for_mode.items(), key=lambda x: x[0][0]))
        return sorted_dict

    @staticmethod
    @pass_context
    def get_exit_events_ev_mask_list_for_same_mode(context, exit_events):
        exit_events_ev_mask_list_for_mode = {}
        # {mode1 : ["evmask1", "evmask2"]}
        for exit_event in exit_events:
            exit_mode = exit_event["mode"]["value"]
            swc_name = exit_event["swc_name"]
            runnable_name = exit_event["runnable_name"]
            ev_mask_name = f"Rte_Ev_Run_{swc_name}_{runnable_name}".upper()
            if exit_mode not in exit_events_ev_mask_list_for_mode:
                exit_events_ev_mask_list_for_mode.update({exit_mode: [ev_mask_name]})
                continue
            exit_events_ev_mask_list_for_mode[exit_mode].append(ev_mask_name)
        sorted_dict = dict(sorted(exit_events_ev_mask_list_for_mode.items(), key=lambda x: x[0][0]))
        return sorted_dict

    @staticmethod
    @pass_context
    def is_matched_transition_map(context, transition_events, pre_mode, next_mode):
        for transition_event in transition_events:
            if (
                transition_event["previous_mode"]["value"][0] == pre_mode
                and transition_event["next_mode"]["value"][0] == next_mode
            ):
                return True, transition_event["previous_mode"]["name"], transition_event["next_mode"]["name"]
        return False, "", ""

    # Used for Core0.c mode switch api generation
    @staticmethod
    @pass_context
    def get_mode_switch_port_in_swc_list(context, appl_name):
        mode_switch_rports = []
        mode_switch_pports = []
        for swc in context["appls_asw_cfg"].values():
            for pport in swc["pports"].values():
                if (
                    pport["type"] == "ModeSwitch"
                    and pport["connected_port_path_list"]
                    and appl_name == pport["osapplication"]
                ):
                    mode_switch_pports.append(pport)
            for rport in swc["rports"].values():
                if (
                    rport["type"] == "ModeNotification"
                    and rport["connect_port_name"]
                    and appl_name == rport["osapplication"]
                ):
                    mode_switch_rports.append(rport)
        if len(mode_switch_rports) > 0:
            mode_switch_rports.sort(
                key=lambda x: (x["swc_name"].lower(), x["port_name"].lower(), x["mode_group_prototype"].lower())
            )
        if len(mode_switch_pports) > 0:
            mode_switch_pports.sort(
                key=lambda x: (x["swc_name"].lower(), x["port_name"].lower(), x["mode_group_prototype"].lower())
            )
            # implementation specific
            for pport in mode_switch_pports:
                pport["if_use_internal_index_current_mode"] = False
                pport["if_use_current_mode"] = False
                if not pport["swc_mode_switch_event"]:
                    continue
                if pport["mode_disabled_entity"]:
                    pport["if_use_current_mode"] = True
                exit_events = pport["swc_mode_switch_event"].get("exit_events", [])
                transition_events = pport["swc_mode_switch_event"].get("transition_events", [])
                if not (exit_events or transition_events):
                    continue
                pport["if_use_current_mode"] = True
                if pport["mode_group_category"] == "EXPLICIT_ORDER":
                    pport["if_use_internal_index_current_mode"] = True
        return mode_switch_rports, mode_switch_pports

    # Used for Core0.c mode switch api generation
    @staticmethod
    @pass_context
    def get_mode_switch_port_in_swc_list_for_modeuser(context, appl_name):
        mode_switch_pports = []
        for swc in context["appls_asw_cfg"].values():
            for pport in swc["pports"].values():
                if (
                    pport["type"] == "ModeSwitch"
                    and pport["connected_port_path_list"]
                    and appl_name == pport["connected_osapplication"]
                ):
                    mode_switch_pports.append(pport)
        for pport in mode_switch_pports:
            infix = Function.__update_cs_ms_memmap_infix(pport["memmap"], appl_name, pport["core_id"])
            pport.update({"infix": infix})
        if len(mode_switch_pports) > 0:
            mode_switch_pports.sort(
                key=lambda x: (x["swc_name"].lower(), x["port_name"].lower(), x["mode_group_prototype"].lower())
            )
        return mode_switch_pports

    @staticmethod
    @pass_context
    def get_mode_switch_port_in_swc_list_all_appls(context):
        mode_switch_rports = []
        mode_switch_pports = []
        for swc in context["appls_asw_cfg"].values():
            for pport in swc["pports"].values():
                if pport["type"] == "ModeSwitch" and pport["connected_port_path_list"] and pport["osapplication"]:
                    mode_switch_pports.append(pport)
            for rport in swc["rports"].values():
                if rport["type"] == "ModeNotification" and rport["connect_port_name"]:
                    mode_switch_rports.append(rport)
        for pport in mode_switch_pports:
            infix = Function.__update_ms_memmap_infix(
                pport["memmap"], pport["connected_osapplication"], pport["core_id"]
            )
            pport.update({"infix": infix})
        if len(mode_switch_pports) > 0:
            mode_switch_pports.sort(
                key=lambda x: (x["swc_name"].lower(), x["port_name"].lower(), x["mode_group_prototype"].lower())
            )
        if len(mode_switch_rports) > 0:
            mode_switch_rports.sort(
                key=lambda x: (x["swc_name"].lower(), x["port_name"].lower(), x["mode_group_prototype"].lower())
            )
        return mode_switch_rports, mode_switch_pports

    @staticmethod
    @pass_context
    def get_mode_switch_pport_use_explicit_order_in_swc_list(context):
        explicit_order_dict = {}
        all_mode_group = context["mode_declaration_group"]
        for swc in context["asw_cfg"].values():
            for pport in swc["pports"].values():
                if (
                    pport["type"] == "ModeSwitch"
                    and pport["connected_port_path_list"]
                    and pport["mode_group_category"] == "EXPLICIT_ORDER"
                ):
                    swc_name = pport["swc_name"]
                    mode_group = pport["mode_group"]
                    if (swc_name, mode_group) not in explicit_order_dict:
                        explicit_order_dict.update({(swc_name, mode_group): all_mode_group[mode_group]})
                    # more than one ports uesed same port interface, count only once
        return explicit_order_dict

    @staticmethod
    @pass_context
    def get_mode_switch_port_unconnected_in_swc_list(context):
        mode_switch_rports = []
        mode_switch_pports = []
        for swc in context["asw_cfg"].values():
            for pport in swc["pports"].values():
                if pport["type"] == "ModeSwitch" and not pport["connected_port_path_list"]:
                    mode_switch_pports.append(pport)
            for rport in swc["rports"].values():
                if rport["type"] == "ModeNotification" and not rport["connect_port_name"]:
                    mode_switch_rports.append(rport)
        if len(mode_switch_pports) > 0:
            mode_switch_pports.sort(
                key=lambda x: (x["swc_name"].lower(), x["port_name"].lower(), x["mode_group_prototype"].lower())
            )
        if len(mode_switch_rports) > 0:
            mode_switch_rports.sort(
                key=lambda x: (x["swc_name"].lower(), x["port_name"].lower(), x["mode_group_prototype"].lower())
            )
        return mode_switch_rports, mode_switch_pports

    @staticmethod
    @pass_context
    # Used for Core0.c switch_ack api generation
    def get_mode_switch_ack_port_in_asw_cfg(context):
        mode_switch_ack_pports = []
        for swc in context["asw_cfg"].values():
            for port in swc["pports"].values():
                if port["type"] == "ModeSwitch" and port["mode_switched_ack"]:
                    mode_switch_ack_pports.append(port)
        mode_switch_ack_pports.sort(key=lambda x: (x["swc_name"], x["port_name"], x["mode_group_prototype"]))
        return mode_switch_ack_pports

    @staticmethod
    @pass_context
    def get_runnable_entity_list(context):
        runnable_list = []
        for runnable in context["swc"]["runnables"].values():
            runnable_list.append(runnable)
        if runnable_list != []:
            runnable_list.sort(key=lambda x: ("args" in x.keys(), x["name"].lower()))
        return runnable_list

    @staticmethod
    @pass_context
    def get_swc_name(context):
        return context["swc"]["name"]

    @staticmethod
    @pass_context
    def get_swc_type(context):
        return context["swc"]["type"]

    @staticmethod
    @pass_context
    def get_iso_call_func_include_header_file(context):
        return context["iso_call_func_include_header_file"]

    @staticmethod
    @pass_context
    def get_gen_file_swc_type(context):
        return AutosarUtils.GEN_FILE_APPL_COMPONENT_TYPE

    @staticmethod
    @pass_context
    def get_appl_swc_name_list(context):
        swc_name_set = set()
        all_mode_group = context["mode_declaration_group"]
        for swc in context["asw_cfg"].values():
            if swc["type"] not in AutosarUtils.GEN_FILE_COMPONENT_TYPE:
                continue
            swc_name_set.add(swc["name"])
        for swc in context["appls_asw_cfg"].values():
            use_mode_swc = False
            for pport in swc["pports"].values():
                if (
                    pport["type"] == "ModeSwitch"
                    and pport["connected_port_path_list"]
                    and pport["mode_group"] in all_mode_group
                ):
                    swc_name_set.add(swc["name"])
                    use_mode_swc = True
                    break
            if use_mode_swc:
                continue
            for rport in swc["rports"].values():
                if (
                    rport["type"] == "ModeNotification"
                    and rport["connected_component_name"]
                    and rport["mode_group"] in all_mode_group
                ):
                    swc_name_set.add(swc["name"])
                    use_mode_swc = True
                    break
            if use_mode_swc:
                continue
        swc_name_list = list(swc_name_set)
        swc_name_list.sort(key=lambda x: (len(x), x.lower()))
        return swc_name_list

    @staticmethod
    @pass_context
    def get_appl_not_signal_api_hasprport_pport_list(context):
        pport_list = []
        for swc in context["asw_cfg"].values():
            for pport in swc["pports"].values():
                if pport["type"] != "Explicit Sender" or pport["signal_category"] != "None" or not pport["has_prport"]:
                    continue
                if Function.get_sr_explicit_rte_interface_code_format(pport) == _FUNC:
                    pport["buffer_name"] = Function._get_variable_of_prprot_connection(pport)
                    pport_list.append(pport)
        pport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return pport_list

    @staticmethod
    @pass_context
    def get_appl_not_signal_api_hasprport_rport_list(context):
        rport_list = []
        for swc in context["asw_cfg"].values():
            for rport in swc["rports"].values():
                if (
                    rport["type"] != "Explicit Receiver"
                    or rport["signal_category"] != "None"
                    or not rport["has_prport"]
                ):
                    continue
                if Function.get_sr_explicit_rte_interface_code_format(rport) == _FUNC:
                    rport["buffer_name"] = Function._get_variable_of_prprot_connection(rport)
                    rport_list.append(rport)
        rport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rport_list

    @staticmethod
    @pass_context
    def get_rte_write_func_pports_with_no_prport(context):
        pport_list = []
        for swc in context["asw_cfg"].values():
            for pport in swc["pports"].values():
                if not pport["type"] == "Explicit Sender":
                    continue
                if pport["has_prport"]:
                    continue

                is_func_impl = False
                # inter ECU & intra ECU
                if Function.get_sr_explicit_rte_interface_code_format(pport) != _FUNC:
                    # macro implementations
                    continue
                is_func_impl = True
                buff_struct_type = None
                buff_struct_name = None
                sender_buff_struct_type = []
                sender_buff_struct_name = []
                # ioc_id has the same name as buffer_name
                if pport["m_to_n"] == "n1":
                    rport = pport["conn_asw_ports"][0]
                    pport["lock_id"] = "Rte_" + rport["swc_port_var"]
                    if pport["single_rec_buff_for_n1"]:
                        buffer_name = "Rte_" + rport["swc_port_var"]
                        struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(rport)
                        buff_struct_type = struct_type
                        buff_struct_name = struct_name
                    else:
                        buffer_name = "Rte_" + pport["swc_port_var"]
                        pport["local_counter"] = "Rte_Counter_Sr_Local_" + pport["swc_port_var"]
                        pport["global_counter"] = "Rte_Counter_Sr_Global_" + rport["swc_port_var"]
                        struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(pport)
                        sender_buff_struct_type.append(struct_type)
                        sender_buff_struct_name.append(struct_name)
                else:
                    buffer_name = "Rte_" + pport["swc_port_var"]
                    pport["lock_id"] = buffer_name
                    struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(pport)
                    buff_struct_type = struct_type
                    buff_struct_name = struct_name
                pport["spinlock_api_postfix"] = "Write" if pport.get("spinlock_cfg", {}).get("is_rw", False) else ""
                pport["buffer_name"] = buffer_name
                pport["buff_struct_type"] = buff_struct_type
                pport["buff_struct_name"] = buff_struct_name
                pport["sender_buff_struct_type"] = (sender_buff_struct_type,)
                pport["sender_buff_struct_name"] = sender_buff_struct_name
                if is_func_impl:
                    for signal in pport.get("data_mapping_details", []):
                        Function.signal_compu_method_trans(signal, False)
                    Function.update_cm_dt_to_type_mappings(pport)
                    pport_list.append(pport)
        pport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return pport_list

    @staticmethod
    def update_cm_dt_to_type_mappings(port_sig):
        if port_sig.get("signal_type", "") in ["system_signal_group", "SignalGroup"]:
            for sig_group_name, sig_values_tm in port_sig.get("type_mappings", {}).items():
                for sig_value_tm in sig_values_tm:
                    sig_value_tm.update(
                        {"compu_method": port_sig["compu_method"][sig_group_name][sig_value_tm["system_signal"]]}
                    )
                    sig_value_tm.update(
                        {"real_sig_type": port_sig["real_sig_type"][sig_group_name][sig_value_tm["system_signal"]]}
                    )
                    data_type = next(
                        (
                            mem["datatype"]
                            for mem in port_sig["datatype"]["members"]
                            if mem["name"] == sig_value_tm["system_signal"]
                        ),
                        None,
                    )
                    sig_value_tm.update({"datatype": data_type})
        if port_sig.get("signal_category", "") in ["system_signal_group", "SignalGroup"]:
            for sig_group_name, sig_values_tm in port_sig.get("type_mappings", {}).items():
                for sig_group_dm in port_sig.get("data_mapping_details", []):
                    if sig_group_dm["full_name"] != sig_group_name:
                        continue
                    for sig_value_tm in sig_values_tm:
                        sig_value_tm.update(
                            {
                                "compu_method": sig_group_dm["system_signal"][sig_value_tm["system_signal"]][
                                    "compu_method"
                                ]
                            }
                        )
                        sig_value_tm.update(
                            {
                                "real_sig_type": sig_group_dm["system_signal"][sig_value_tm["system_signal"]][
                                    "real_sig_type"
                                ]
                            }
                        )
                        data_type = next(
                            (
                                mem["datatype"]
                                for mem in port_sig["arg"]["datatype"]["members"]
                                if mem["name"] == sig_value_tm["system_signal"]
                            ),
                            None,
                        )
                        sig_value_tm.update({"datatype": data_type})

    @staticmethod
    @pass_context
    def get_appl_signal_api_rport_list(context):
        rport_list = []
        for swc in context["asw_cfg"].values():
            for rport in swc["rports"].values():
                if (
                    rport["type"] == "Explicit Receiver"
                    and rport["signal_category"] in {"Signal", "SignalGroup"}
                    and rport["data_mapping_m_to_n"] != "0"
                ):
                    if Function.get_sr_explicit_rte_interface_code_format(rport) == _MACRO:
                        continue
                    for signal in rport["data_mapping_details"]:
                        Function.signal_compu_method_trans(signal, False)
                    Function.update_cm_dt_to_type_mappings(rport)
                    rport_list.append(rport)
        rport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rport_list

    @staticmethod
    @pass_context
    def get_appl_not_signal_api_rport_list(context):
        rport_list = []
        for swc in context["asw_cfg"].values():
            for rport in swc["rports"].values():
                if rport["type"] != "Explicit Receiver":
                    continue
                if Function.get_sr_explicit_rte_interface_code_format(rport) != _FUNC:
                    continue  # pass macro implementation
                if rport["signal_category"] == "None":
                    if rport["has_prport"]:
                        continue
                    if rport["m_to_n"] in {"0", "mn"}:
                        continue
                    buff_struct_type = None
                    buff_struct_name = None
                    sender_buff_struct_type = []
                    sender_buff_struct_name = []
                    # the ioc_id has the same name as buffer_name
                    if rport["m_to_n"] == "n1":
                        buffer_name = "Rte_" + rport["swc_port_var"]
                        rport["lock_id"] = "Rte_" + rport["swc_port_var"]
                        struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(rport)
                        buff_struct_type = struct_type
                        buff_struct_name = struct_name
                        if not rport["single_rec_buff_for_n1"]:
                            rport["all_sender_buffer"] = []
                            rport["all_sender_counter"] = []
                            rport["all_sender_struct"] = []
                            rport["global_counter"] = "Rte_Counter_Sr_Global_" + rport["swc_port_var"]
                            for pport in rport["conn_asw_ports"]:
                                rport["all_sender_buffer"].append(
                                    ("Rte_" + pport["swc_port_var"], pport["osapplication"])
                                )
                                rport["all_sender_counter"].append(
                                    ("Rte_Counter_Sr_Local_" + pport["swc_port_var"], pport["osapplication"])
                                )
                                struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(
                                    pport
                                )
                                sender_buff_struct_type.append(struct_type)
                                sender_buff_struct_name.append(struct_name)
                    else:
                        pport = rport["conn_asw_ports"][0]
                        buffer_name = "Rte_" + pport["swc_port_var"]
                        rport["lock_id"] = buffer_name
                        struct_type, struct_name = Function._update_struct_datatype_and_name_of_boolean_buff(pport)
                        buff_struct_type = struct_type
                        buff_struct_name = struct_name
                    rport["spinlock_api_postfix"] = "Read" if rport.get("spinlock_cfg", {}).get("is_rw", False) else ""
                    rport["buffer_name"] = buffer_name
                    rport["buff_struct_type"] = buff_struct_type
                    rport["buff_struct_name"] = buff_struct_name
                    rport["sender_buff_struct_type"] = sender_buff_struct_type
                    rport["sender_buff_struct_name"] = sender_buff_struct_name
                    rport_list.append(rport)
        rport_list.sort(key=lambda x: ("args" in x.keys(), x["sort_name"].lower()))
        return rport_list

    @staticmethod
    def get_input_args_str_list(arg_list):
        args_str_list = []
        for arg in arg_list:
            arg_str = arg["type"]
            if arg["direction"] not in ["IN", "INOUT"]:
                continue
            # TODO: use native_category instead of category
            if arg["category"] in ["ARRAY", "STRUCTURE", "UNION"]:
                arg_str += "* "
            else:
                arg_str += " "
            arg_str += arg["name"]
            args_str_list.append(arg_str)
        return args_str_list

    @staticmethod
    def get_output_args_str_list(arg_list):
        args_str_list = []
        for arg in arg_list:
            arg_str = arg["type"]
            # if "category" in arg and arg["category"] == "ARRAY" and arg["direction"] == "OUT":
            #     arg_str += " "
            if arg["direction"] not in ["INOUT", "OUT"]:
                continue
            arg_str += "* "
            arg_str += arg["name"]
            args_str_list.append(arg_str)
        return args_str_list

    @staticmethod
    def get_args_str_list(arg_list):
        args_str_list = []
        for arg in arg_list:
            arg_str = arg["type"]
            # TODO: use native_category instead of category
            if arg["direction"] == "IN" and arg.get("category", "") in ["STRUCTURE", "UNION"]:
                arg_str += "* "
            elif arg["direction"] == "IN" and arg.get("category", "") == "ARRAY":
                arg_str = arg["base_type"]
                arg_str += "* "
            elif arg["direction"] in ["OUT", "INOUT"] and arg.get("category", "") == "ARRAY":
                arg_str = arg["base_type"]
                arg_str += "* "
            elif arg["direction"] in ["OUT", "INOUT"]:
                arg_str += "* "
            else:
                arg_str += " "
            arg_str += arg["name"]
            args_str_list.append(arg_str)
        return args_str_list

    def get_args_str_name_list(arg_list):
        args_str_name_list = []
        for arg in arg_list:
            args_str_name_list.append(arg["name"])
        return args_str_name_list

    @staticmethod
    def get_port_def_arg_str_list(arg_list):
        port_def_arg_str_list = []
        for arg in arg_list:
            arg_str = "(" + arg["type"] + ")" + str(arg["value"])
            port_def_arg_str_list.append(arg_str)
        return port_def_arg_str_list

    @staticmethod
    def get_arg_name_list(arg_list):
        return [element["name"] for element in arg_list]

    @staticmethod
    def _get_swc_per_instance_memory_list(swc):
        pim_list = []
        pim_list = list(swc["pims"].values()) if "pims" in swc else []
        return pim_list

    @staticmethod
    @pass_context
    def get_swc_per_instance_memory_list(context):
        pim_list = []
        pim_list = Function._get_swc_per_instance_memory_list(context["swc"])
        pim_list.sort(key=lambda x: ("args" in x.keys(), x["name"].lower()))
        return pim_list

    @staticmethod
    @pass_context
    def get_per_instacne_memory_variable_list(context):
        variable_list = []
        for swc in context["asw_cfg"].values():
            variable_list += Function._get_swc_per_instance_memory_list(swc)
        variable_list.sort(key=lambda x: ("args" in x.keys(), x["name"].lower()))
        return variable_list

    @staticmethod
    @pass_context
    def get_nvblock_component_dirtyflag_runnables(context):
        runnable_list = []
        for swc in context["asw_cfg"].values():
            if swc["type"] != "NvBlockComponent":
                continue
            for runnable_name, runnable in swc["runnables"].items():
                descriptor = swc["nvblock_descriptors"][runnable["nvblock_descriptor"]]
                if descriptor["dirty_flag"] is not True:
                    continue
                runnable_list.append(
                    {
                        "name": runnable_name,
                        "storing_way": runnable["storing_way"],
                        "nv_descriptor": {
                            "name": descriptor["name"],
                            "component": descriptor["swc_name"],
                            "block_id": descriptor["block_id"],
                            "ram_datatype": descriptor["ram_block"]["name"],
                        },
                    }
                )
        runnable_list.sort(key=lambda x: ("args" in x.keys(), x["name"].lower()))
        return runnable_list

    @staticmethod
    @pass_context
    def get_nvblcok_component_callbacks(context):
        callback_list = []
        for swc in context["asw_cfg"].values():
            if swc["type"] != "NvBlockComponent":
                continue
            for descriptor in swc["nvblock_descriptors"].values():
                if descriptor["dirty_flag"] is not True:
                    continue
                callback_list.append(
                    {
                        "component": descriptor["swc_name"],
                        "nv_descriptor": descriptor["name"],
                        "ram_datatype": descriptor["ram_block"]["name"],
                    }
                )
        callback_list.sort(key=lambda x: ("args" in x.keys(), x["nv_descriptor"].lower()))
        return callback_list

    @staticmethod
    @pass_context
    def get_bsw_configin(context):
        return context["bsw_cfgin"]

    @staticmethod
    @pass_context
    def check_can_enable_in_kconfig(context):
        kconfig_in = context["sys_cfg"]
        if "modules" in kconfig_in:
            if (
                "VCOS_MODULE_CONFIG_MCAL_CAN" in kconfig_in["modules"].keys()
                and kconfig_in["modules"]["VCOS_MODULE_CONFIG_MCAL_CAN"] == "y"
            ):
                return True
            else:
                return False
        return True

    @staticmethod
    @pass_context
    def check_lin_enable_in_kconfig(context):
        kconfig_in = context["sys_cfg"]
        if "modules" in kconfig_in:
            if (
                "VCOS_MODULE_CONFIG_MCAL_LIN" in kconfig_in["modules"].keys()
                and kconfig_in["modules"]["VCOS_MODULE_CONFIG_MCAL_LIN"] == "y"
            ):
                return True
            else:
                return False
        return True

    @staticmethod
    @pass_context
    def check_nvm_enable_in_kconfig(context):
        kconfig_in = context["sys_cfg"]
        if "modules" in kconfig_in:
            if (
                "VCOS_MODULE_CONFIG_MCAL_LIN" in kconfig_in["modules"].keys()
                and kconfig_in["modules"]["VCOS_MODULE_CONFIG_MCAL_LIN"] == "y"
            ):
                return True
            else:
                return False
        return True

    @staticmethod
    @pass_context
    def judge_unconnected_cs_rport(context, client_server_rport):
        if client_server_rport["connected_ports"] is None:
            return True
        else:
            return False

    @staticmethod
    @pass_context
    def get_cs_operation_arg_list(client_server_rport):
        arg_num = len(client_server_rport["operation"]["args"])
        arg_list = []
        if arg_num >= 1:
            for i in range(1, arg_num):
                arg_index = "arg" + i
                arg_list.append(arg_index)
        return arg_list

    @staticmethod
    @pass_context
    def get_bsw_instance_name(context):
        return context["bsw_instances"].get("symbol") or context["bsw_instances"]["module_name"]

    @staticmethod
    @pass_context
    def get_bsw_instance_event_to_task_mapping_entitys(context):
        if "event_to_task_mapping_entitys" in context["bsw_instances"]:
            return context["bsw_instances"]["event_to_task_mapping_entitys"]
        else:
            []

    @staticmethod
    @pass_context
    def get_bsw_instance_exclusive_areas(context):
        exclusive_area_infos = {}
        exclusive_areas_dict = context["bsw_instances"].get("exclusive_areas")
        symbol = context["bsw_instances"].get("symbol", "")
        prefix = symbol + "_" if symbol != "" else ""
        if exclusive_areas_dict is None:
            return []
        for exclusive_areas in exclusive_areas_dict.values():
            for exclusive_area in exclusive_areas:
                exclusive_area_codegen_dict = {}
                exclusive_area_codegen_dict["imp_mechanism"] = exclusive_area["imp_mechanism"]
                exclusive_area_codegen_dict["name"] = prefix + exclusive_area["eas_name"]
                exclusive_area_codegen_dict["input_param"] = ""
                if exclusive_area["imp_mechanism"] == "ALL_INTERRUPT_BLOCKING":
                    exclusive_area_codegen_dict["suspend"] = "SuspendAllInterrupts"
                    exclusive_area_codegen_dict["resume"] = "ResumeAllInterrupts"
                elif exclusive_area["imp_mechanism"] == "OS_INTERRUPT_BLOCKING":
                    exclusive_area_codegen_dict["suspend"] = "SuspendOSInterrupts"
                    exclusive_area_codegen_dict["resume"] = "ResumeOSInterrupts"
                elif exclusive_area["imp_mechanism"] == "OS_RESOURCE":
                    exclusive_area_codegen_dict["suspend"] = "GetResource"
                    exclusive_area_codegen_dict["resume"] = "ReleaseResource"
                    exclusive_area_codegen_dict["input_param"] = (
                        "(ResourceType)RTE_RES_"
                        + exclusive_area["module_name"].upper()
                        + "_"
                        + exclusive_area["eas_name"].upper()
                    )
                elif exclusive_area["imp_mechanism"] == "OS_SPINLOCK":
                    exclusive_area_codegen_dict["suspend"] = "GetSpinlock"
                    exclusive_area_codegen_dict["resume"] = "ReleaseSpinlock"
                    exclusive_area_codegen_dict["input_param"] = (
                        "(SpinlockIdType)RTE_SPINLOCK_"
                        + exclusive_area["module_name"].upper()
                        + "_"
                        + exclusive_area["eas_name"].upper()
                    )
                elif exclusive_area["imp_mechanism"] == "NONE":
                    pass
                else:
                    continue
                exclusive_area_infos[exclusive_area["eas_name"]] = exclusive_area_codegen_dict
        exclusive_area_info_list = sorted(
            exclusive_area_infos.values(), key=lambda x: (len(x["name"]), x["name"].lower())
        )
        return exclusive_area_info_list

    @staticmethod
    @pass_context
    def get_appl_core_id(context, appl_name):
        core_id = "0"
        core_to_appl = context.get("core_to_appl_dict", {})
        for id, appl_list in core_to_appl.items():
            if appl_name in appl_list:
                core_id = id
                break
        return core_id

    @staticmethod
    @pass_context
    def get_appl_is_privileged(context, appl_name):
        is_privileged = context["appl_info"].get("OsIsPrivileged", False)
        return is_privileged

    @staticmethod
    @pass_context
    def get_rte_generation_isr_simplified(context):
        isr_simplified = context["RteGeneration_dict"].get("RteIsrSimplification", False)
        return isr_simplified

    @staticmethod
    @pass_context
    def get_rte_data_mapping_optimize_period_Pport_flag(context):
        RteGeneration_cfg = context.get("RteGeneration_dict", {})
        OptimizationPeriodPport_flag = RteGeneration_cfg.get("DataMappingGenerationOptimizationPport", False)
        return OptimizationPeriodPport_flag

    @staticmethod
    @pass_context
    def get_rte_com_cbk_dict(context):
        com_cbk_dict_same_core = {}
        com_cbk_dict_inter_core = {}
        rx_signal_dict = context.get("signal_dict", {}).get("rx", {})
        for signal_name, signal in rx_signal_dict.items():
            Function.signal_compu_method_trans(signal, True)
            Function.update_cm_dt_to_type_mappings(signal)
            if signal["data_mapping_has_inter_core"]:
                com_cbk_dict_inter_core[signal_name] = signal
            else:
                if (
                    (not signal["data_mapping_buff"])
                    and (not signal["trigger_event"])
                    and (not signal["enable_update"])
                    and (not signal["handle_never_received"])
                    and (not signal["alive_timeout"])
                ):
                    continue
                com_cbk_dict_same_core[signal_name] = signal
        return com_cbk_dict_same_core, com_cbk_dict_inter_core

    @staticmethod
    @pass_context
    def need_include_com_h(context):
        com_cbk_dict_same_core, com_cbk_dict_inter_core = Function.get_rte_com_cbk_dict(context)
        if com_cbk_dict_same_core or com_cbk_dict_inter_core:
            return True
        data_dict_inter_parition_same_core, data_dict_inter_core, _, _ = Function.get_rte_com_tx_proxy_data_dict(
            context
        )
        if data_dict_inter_parition_same_core or data_dict_inter_core:
            return True
        return False

    @staticmethod
    @pass_context
    def get_all_osa(context):
        return sorted(context.get("osapplication_asw_cfg", {}).keys(), key=lambda x: (len(x), x.lower()))

    @staticmethod
    def get_sr_var_init_value(datatype, init_value, ind=""):
        return AutosarUtils.get_sr_var_init_value(datatype, init_value, ind)

    @staticmethod
    def __get_sr_dm_memmap_infix(var_info):
        init_infix = var_info["init_category"].value

        if var_info["memmap_category"] == MemmapCategory.OSA_PRIVATE:
            return f"{var_info['osa']}_PRIVATE_{init_infix}"
        elif var_info["memmap_category"] == MemmapCategory.OSA_SHARED:
            return f"{var_info['osa']}_SEMISHARED_{init_infix}"
        elif var_info["memmap_category"] == MemmapCategory.CORE_SHARED:
            return f"MULTI_APP_{init_infix}"
        elif var_info["memmap_category"] == MemmapCategory.GLOBAL:
            return f"MULTI_APP_{init_infix}"
        else:
            return None

    @staticmethod
    @pass_context
    def get_sr_dm_buff(context, osa=None):
        ret = {}
        if osa:
            for _, buffs in (
                context.get("sr_dm_glob_vars", {}).get("individual", {}).get("buff", {}).get(osa, {}).items()
            ):
                for _, buff_info in buffs.items():
                    init_value_str, is_zero_init, is_bool = AutosarUtils.get_sr_var_init_value(
                        buff_info["datatype"], buff_info["init_value"]
                    )
                    buff_info["init_category"] = (
                        VariableInitCategory.ZERO_INIT if is_zero_init else VariableInitCategory.INIT
                    )
                    buff_info["init_value_all_zero"] = is_zero_init
                    buff_info["init_value_str"] = init_value_str
                    infix = Function.__get_sr_dm_memmap_infix(buff_info)
                    if not infix:
                        continue
                    if infix not in ret:
                        ret[infix] = []
                    ret[infix].append(buff_info)
        else:
            for _, osa_info in context.get("sr_dm_glob_vars", {}).get("individual", {}).get("buff", {}).items():
                for _, buffs in osa_info.items():
                    for _, buff_info in buffs.items():
                        init_value_str, is_zero_init, is_bool = AutosarUtils.get_sr_var_init_value(
                            buff_info["datatype"], buff_info["init_value"]
                        )
                        buff_info["init_category"] = (
                            VariableInitCategory.ZERO_INIT if is_zero_init else VariableInitCategory.INIT
                        )
                        buff_info["init_value_all_zero"] = is_zero_init
                        buff_info["init_value_str"] = init_value_str
                        infix = Function.__get_sr_dm_memmap_infix(buff_info)
                        if not infix:
                            continue
                        if infix not in ret:
                            ret[infix] = []
                        ret[infix].append(buff_info)
        return ret

    @staticmethod
    @pass_context
    def get_sr_dm_buff_last(context, osa=None):
        ret = {}
        if osa:
            for _, buffs in (
                context.get("sr_dm_glob_vars", {}).get("individual", {}).get("buff_last", {}).get(osa, {}).items()
            ):
                for _, buff_info in buffs.items():
                    infix = Function.__get_sr_dm_memmap_infix(buff_info)
                    if not infix:
                        continue
                    if infix not in ret:
                        ret[infix] = []
                    ret[infix].append(buff_info)
        else:
            for _, osa_info in context.get("sr_dm_glob_vars", {}).get("individual", {}).get("buff_last", {}).items():
                for _, buffs in osa_info.items():
                    for _, buff_info in buffs.items():
                        infix = Function.__get_sr_dm_memmap_infix(buff_info)
                        if not infix:
                            continue
                        if infix not in ret:
                            ret[infix] = []
                        ret[infix].append(buff_info)
        return ret

    @staticmethod
    @pass_context
    def get_sr_dm_buff_status(context, osa=None):
        ret = {}
        if osa:
            for _, buffs in (
                context.get("sr_dm_glob_vars", {}).get("individual", {}).get("status", {}).get(osa, {}).items()
            ):
                for _, buff_info in buffs.items():
                    infix = Function.__get_sr_dm_memmap_infix(buff_info)
                    if not infix:
                        continue
                    if infix not in ret:
                        ret[infix] = []
                    ret[infix].append(buff_info)
        else:
            for _, osa_info in context.get("sr_dm_glob_vars", {}).get("individual", {}).get("status", {}).items():
                for _, buffs in osa_info.items():
                    for _, buff_info in buffs.items():
                        infix = Function.__get_sr_dm_memmap_infix(buff_info)
                        if not infix:
                            continue
                        if infix not in ret:
                            ret[infix] = []
                        ret[infix].append(buff_info)
        return ret

    @staticmethod
    def __get_sr_dm_flag_osa(ret, parent_struct_name, buffs):
        if parent_struct_name not in ret:
            ret[parent_struct_name] = [None, [], None]
        for _, buff_info in buffs.items():
            if not ret[parent_struct_name][0]:
                ret[parent_struct_name][0] = Function.__get_sr_dm_memmap_infix(buff_info)
                if not ret[parent_struct_name][0]:
                    continue
            ret[parent_struct_name][1].append(buff_info)

    @staticmethod
    @pass_context
    def get_sr_dm_flag_is_proxy_sending(context, osa=None):
        ret = {}
        if osa:
            for parent_struct_name, buffs in (
                context.get("sr_dm_glob_vars", {})
                .get("complex", {})
                .get("flag_is_proxy_sending", {})
                .get(osa, {})
                .items()
            ):
                Function.__get_sr_dm_flag_osa(ret, parent_struct_name, buffs)
        else:
            for _, osa_info in (
                context.get("sr_dm_glob_vars", {}).get("complex", {}).get("flag_is_proxy_sending", {}).items()
            ):
                for parent_struct_name, buffs in osa_info.items():
                    Function.__get_sr_dm_flag_osa(ret, parent_struct_name, buffs)
        for flag_info in ret.values():
            if not flag_info[1]:
                continue
            init_str = " = {\n    1U"
            for i in range(1, len(flag_info[1])):
                if i % 20 == 0:
                    init_str += ",\n    1U"
                else:
                    init_str += ", 1U"
            flag_info[2] = init_str + "\n}"
        return ret

    @staticmethod
    @pass_context
    def get_sr_dm_flag_is_updated_tx(context, osa=None):
        ret = {}
        if osa:
            for parent_struct_name, buffs in (
                context.get("sr_dm_glob_vars", {}).get("complex", {}).get("flag_is_updated_tx", {}).get(osa, {}).items()
            ):
                Function.__get_sr_dm_flag_osa(ret, parent_struct_name, buffs)
        else:
            for _, osa_info in (
                context.get("sr_dm_glob_vars", {}).get("complex", {}).get("flag_is_updated_tx", {}).items()
            ):
                for parent_struct_name, buffs in osa_info.items():
                    Function.__get_sr_dm_flag_osa(ret, parent_struct_name, buffs)
        return ret

    @staticmethod
    @pass_context
    def get_sr_dm_flag_is_updated_rx(context, osa=None):
        ret = {}
        if osa:
            for parent_struct_name, buffs in (
                context.get("sr_dm_glob_vars", {}).get("complex", {}).get("flag_is_updated_rx", {}).get(osa, {}).items()
            ):
                Function.__get_sr_dm_flag_osa(ret, parent_struct_name, buffs)
        else:
            for _, osa_info in (
                context.get("sr_dm_glob_vars", {}).get("complex", {}).get("flag_is_updated_rx", {}).items()
            ):
                for parent_struct_name, buffs in osa_info.items():
                    Function.__get_sr_dm_flag_osa(ret, parent_struct_name, buffs)
        return ret

    @staticmethod
    @pass_context
    def get_sr_dm_flag_is_received(context, osa=None):
        ret = {}
        if osa:
            for parent_struct_name, buffs in (
                context.get("sr_dm_glob_vars", {}).get("complex", {}).get("flag_is_received", {}).get(osa, {}).items()
            ):
                Function.__get_sr_dm_flag_osa(ret, parent_struct_name, buffs)
        else:
            for _, osa_info in (
                context.get("sr_dm_glob_vars", {}).get("complex", {}).get("flag_is_received", {}).items()
            ):
                for parent_struct_name, buffs in osa_info.items():
                    Function.__get_sr_dm_flag_osa(ret, parent_struct_name, buffs)
        return ret

    @staticmethod
    @pass_context
    def get_sr_dm_flag_is_timeout(context, osa=None):
        ret = {}
        if osa:
            for parent_struct_name, buffs in (
                context.get("sr_dm_glob_vars", {}).get("complex", {}).get("flag_is_timeout", {}).get(osa, {}).items()
            ):
                Function.__get_sr_dm_flag_osa(ret, parent_struct_name, buffs)
        else:
            for _, osa_info in context.get("sr_dm_glob_vars", {}).get("complex", {}).get("flag_is_timeout", {}).items():
                for parent_struct_name, buffs in osa_info.items():
                    Function.__get_sr_dm_flag_osa(ret, parent_struct_name, buffs)
        return ret

    @staticmethod
    @pass_context
    def get_rte_com_tx_proxy_list(context, osa=None):
        ret = []
        for proxy_name, proxy_info in context.get("signal_dict", {}).get("tx_proxy", {}).items():
            if osa and osa != proxy_info["osa"]:
                continue
            ret.append(proxy_name)
        return ret

    @staticmethod
    def linear_compu_method_trans(signal, dir=None, is_from_signal=False):
        if is_from_signal:
            if signal["trans_type"] == "internal_to_phys":
                if dir == "Tx":
                    # 转成HEX值，通过CAN发送出去
                    denom = signal["value"]["denominator"]
                    offset = signal["value"]["numerator_offset"]
                    coeff = signal["value"]["numerator_coeff"]
                    denom_final = "1"  # 除数全部转成1，不用在代码生成时生成denom
                    coeff_final = f"{str(float(denom)/float(coeff))}F"
                    offset_final = f"{str(-float(offset)/float(coeff))}F"
                    signal["value"].update(
                        {"denom_final": denom_final, "coeff_final": coeff_final, "offset_final": offset_final}
                    )
                else:
                    # 接收CAN上的HEX值后，将HEX值转换成phys值
                    denom = signal["value"]["denominator"]
                    offset = signal["value"]["numerator_offset"]
                    coeff = signal["value"]["numerator_coeff"]
                    denom_final = "1"  # 除数全部转成1，不用在代码生成时生成denom
                    coeff_final = f"{str(float(coeff)/float(denom))}F"
                    offset_final = f"{str(float(offset)/float(denom))}F"
                    signal["value"].update(
                        {"denom_final": denom_final, "coeff_final": coeff_final, "offset_final": offset_final}
                    )
            else:
                # TODO, phys_to_internal待开发
                pass
        else:
            if signal["compu_method"]["trans_type"] == "internal_to_phys":
                if signal["direction"] == "Tx":
                    # 转成HEX值，通过CAN发送出去
                    denom = signal["compu_method"]["value"]["denominator"]
                    offset = signal["compu_method"]["value"]["numerator_offset"]
                    coeff = signal["compu_method"]["value"]["numerator_coeff"]
                    denom_final = "1"  # 除数全部转成1，不用在代码生成时生成denom
                    coeff_final = f"{str(float(denom)/float(coeff))}F"
                    offset_final = f"{str(-float(offset)/float(coeff))}F"
                    signal["compu_method"]["value"].update(
                        {"denom_final": denom_final, "coeff_final": coeff_final, "offset_final": offset_final}
                    )
                elif signal["direction"] == "Rx":
                    # 接收CAN上的HEX值后，将HEX值转换成phys值
                    denom = signal["compu_method"]["value"]["denominator"]
                    offset = signal["compu_method"]["value"]["numerator_offset"]
                    coeff = signal["compu_method"]["value"]["numerator_coeff"]
                    denom_final = "1"  # 除数全部转成1，不用在代码生成时生成denom
                    coeff_final = f"{str(float(coeff)/float(denom))}F"
                    offset_final = f"{str(float(offset)/float(denom))}F"
                    signal["compu_method"]["value"].update(
                        {"denom_final": denom_final, "coeff_final": coeff_final, "offset_final": offset_final}
                    )
            else:
                # TODO, phys_to_internal待开发
                pass

    @staticmethod
    def scale_linear_and_texttable_compu_method_trans(signal, dir=None, is_from_signal=False):
        if is_from_signal:
            if signal["trans_type"] == "internal_to_phys":
                if dir == "Tx":
                    # 转成HEX值，通过CAN发送出去
                    for value in signal["value"]:
                        denom = value["denominator"]
                        offset = value["numerator_offset"]
                        coeff = value["numerator_coeff"]
                        if denom and offset and coeff:
                            denom_final = "1"  # 除数全部转成1，不用在代码生成时生成denom
                            coeff_final = f"{str(float(denom)/float(coeff))}F"
                            offset_final = f"{str(-float(offset)/float(coeff))}F"
                            value.update(
                                {"denom_final": denom_final, "coeff_final": coeff_final, "offset_final": offset_final}
                            )
                else:
                    # 接收CAN上的HEX值后，将HEX值转换成phys值
                    for value in signal["value"]:
                        denom = value["denominator"]
                        offset = value["numerator_offset"]
                        coeff = value["numerator_coeff"]
                        if denom and offset and coeff:
                            denom_final = "1"  # 除数全部转成1，不用在代码生成时生成denom
                            coeff_final = f"{str(float(coeff)/float(denom))}F"
                            offset_final = f"{str(float(offset)/float(denom))}F"
                            value.update(
                                {"denom_final": denom_final, "coeff_final": coeff_final, "offset_final": offset_final}
                            )
            else:
                # TODO, phys_to_internal待开发
                pass
        else:
            if signal["compu_method"]["trans_type"] == "internal_to_phys":
                if signal["direction"] == "Tx":
                    # 转成HEX值，通过CAN发送出去
                    for value in signal["compu_method"]["value"]:
                        denom = value["denominator"]
                        offset = value["numerator_offset"]
                        coeff = value["numerator_coeff"]
                        if denom and offset and coeff:
                            denom_final = "1"  # 除数全部转成1，不用在代码生成时生成denom
                            coeff_final = f"{str(float(denom)/float(coeff))}F"
                            offset_final = f"{str(-float(offset)/float(coeff))}F"
                            value.update(
                                {"denom_final": denom_final, "coeff_final": coeff_final, "offset_final": offset_final}
                            )
                elif signal["direction"] == "Rx":
                    # 接收CAN上的HEX值后，将HEX值转换成phys值
                    for value in signal["compu_method"]["value"]:
                        denom = value["denominator"]
                        offset = value["numerator_offset"]
                        coeff = value["numerator_coeff"]
                        if denom and offset and coeff:
                            denom_final = "1"  # 除数全部转成1，不用在代码生成时生成denom
                            coeff_final = f"{str(float(coeff)/float(denom))}F"
                            offset_final = f"{str(float(offset)/float(denom))}F"
                            value.update(
                                {"denom_final": denom_final, "coeff_final": coeff_final, "offset_final": offset_final}
                            )
            else:
                # TODO, phys_to_internal待开发
                pass

    @staticmethod
    def signal_compu_method_trans(signal, is_from_signal):
        if is_from_signal:
            if signal["signal_type"] == "Signal":
                compu_method = signal.get("compu_method", {})
                if compu_method:
                    # 当前只支持linear和scale_linear_and_texttable公式转换，其他的公式待支持
                    if compu_method["category"] == "LINEAR":
                        Function.linear_compu_method_trans(compu_method, signal["direction"], True)
                    if compu_method["category"] in ["SCALE_LINEAR", "SCALE_LINEAR_AND_TEXTTABLE"]:
                        Function.scale_linear_and_texttable_compu_method_trans(compu_method, signal["direction"], True)
                    else:
                        # TODO, 其他类型公式待开发
                        pass
            elif signal["signal_type"] == "SignalGroup":
                for sig_group_name, sig_values in signal["compu_method"].items():
                    # 当前只支持linear和scale_linear_and_texttable公式转换，其他的公式待支持
                    for sig_name, sig_value in sig_values.items():
                        if not sig_value:
                            continue
                        if sig_value["category"] == "LINEAR":
                            Function.linear_compu_method_trans(sig_value, signal["direction"], True)
                        if sig_value["category"] in ["SCALE_LINEAR", "SCALE_LINEAR_AND_TEXTTABLE"]:
                            Function.scale_linear_and_texttable_compu_method_trans(sig_value, signal["direction"], True)
                        else:
                            # TODO, 其他类型公式待开发
                            pass
            else:
                # TODO
                pass
        else:
            if signal["signal_type"] == "system_signal":
                if signal.get("compu_method", {}):
                    # 当前只支持linear和scale_linear_and_texttable公式转换，其他的公式待支持
                    if signal["compu_method"]["category"] == "LINEAR":
                        Function.linear_compu_method_trans(signal)
                    if signal["compu_method"]["category"] in ["SCALE_LINEAR", "SCALE_LINEAR_AND_TEXTTABLE"]:
                        Function.scale_linear_and_texttable_compu_method_trans(signal)
                    else:
                        # TODO, 其他类型公式待开发
                        pass
            elif signal["signal_type"] == "system_signal_group":
                for sig_name, sig_value in signal["system_signal"].items():
                    # 当前只支持linear和scale_linear_and_texttable公式转换，其他的公式待支持
                    if not sig_value or not sig_value.get("compu_method", {}):
                        continue
                    if sig_value["compu_method"]["category"] == "LINEAR":
                        Function.linear_compu_method_trans(sig_value)
                    if sig_value["compu_method"]["category"] in ["SCALE_LINEAR", "SCALE_LINEAR_AND_TEXTTABLE"]:
                        Function.scale_linear_and_texttable_compu_method_trans(sig_value)
                    else:
                        # TODO, 其他类型公式待开发
                        pass
            else:
                # TODO
                pass

    @staticmethod
    @pass_context
    def get_gen_compu_method_flag(context):
        gen_cm = context["RteGeneration_dict"].get("RteSystemSignalCompuMethodEna", False)
        return gen_cm

    @staticmethod
    @pass_context
    def get_rte_com_tx_proxy_data_dict(context, proxy_name=None):
        data_dict_inter_parition_same_core = {}
        data_dict_inter_core = {}
        local_data_dict_inter_core = {}
        is_updated_tx_parent_struct = set()

        for name, proxy in context.get("signal_dict", {}).get("tx_proxy", {}).items():
            if proxy_name and proxy_name != name:
                continue
            for signal_name, signal in proxy["signal"].items():
                Function.signal_compu_method_trans(signal, True)
                Function.update_cm_dt_to_type_mappings(signal)
                if signal["data_mapping_has_inter_osa_same_core"]:
                    data_dict_inter_parition_same_core[signal_name] = signal
                elif signal["data_mapping_has_inter_core"]:
                    data_dict_inter_core[signal_name] = signal
                    data_mapping_lock_id = signal["data_mapping_lock_id"]
                    if data_mapping_lock_id not in local_data_dict_inter_core:
                        local_data_dict_inter_core[data_mapping_lock_id] = {}
                    local_data_dict_inter_core[data_mapping_lock_id][signal_name] = signal
                    if signal["data_mapping_flag"]["is_updated"]:
                        is_updated_tx_parent_struct.add(signal["data_mapping_flag"]["is_updated"]["parent_struct_name"])
        return (
            data_dict_inter_parition_same_core,
            data_dict_inter_core,
            local_data_dict_inter_core,
            sorted(is_updated_tx_parent_struct),
        )

    @staticmethod
    @pass_context
    def get_swc_data_mapping_rx_is_updated_port(context):
        ret = []
        for port in context["swc"]["rports"].values():
            if ("data_mapping_flag" not in port) or (not port["data_mapping_flag"]):
                continue
            if ("is_updated" not in port["data_mapping_flag"]) or (not port["data_mapping_flag"]["is_updated"]):
                continue
            ret.append(port)
        ret.sort(key=lambda x: (x["swc_port_var"].lower()))
        return ret

    @staticmethod
    @pass_context
    def get_component_osapplication_name(context):
        return context.get("swc", {}).get("osapplication", "")

    @staticmethod
    def remove_duplicates_port_variables(port_list):
        dic = {port["variable"]: port for port in port_list}
        lst = list(dic.values())
        return sorted(lst, key=lambda x: x["variable"])

    @staticmethod
    @pass_context
    def get_activation_reasons(context):
        activation_reasons = context.get("activation_reasons", [])
        return activation_reasons

    @staticmethod
    def get_activation_vector(activation_reason):
        value = activation_reason["value"][-1]
        bit_position = int(value["bit_position"])
        type_str = Function.get_activation_vector_type_from_bit_position(bit_position)
        activation_vector = {}
        activation_vector["type"] = type_str
        activation_vector["name"] = activation_reason["schedulable_entity_name"]
        return activation_vector

    @staticmethod
    def get_activation_vector_type_from_bit_position(bit_position):
        type_str = "uint32"
        if bit_position < 8:
            type_str = "uint8"
        elif bit_position < 16:
            type_str = "uint16"
        elif bit_position < 32:
            type_str = "uint32"
        return type_str

    @staticmethod
    def get_activation_reason_defines(activation_reason):
        activation_reason_defines = []
        for value in activation_reason["value"]:
            activation_reason_define = {}
            activation_reason_define["name"] = f"{activation_reason['schedulable_entity_name']}_{value['name']}"
            activation_reason_define["value"] = 1 << int(value["bit_position"])
            activation_reason_defines.append(activation_reason_define)
        return activation_reason_defines

    @staticmethod
    @pass_context
    def get_runnable_activation_reasons(context, runnable_name, task_name):
        activation_reasons = []
        runnable = context["task_mappings"][task_name]["schedulable_entity"][runnable_name]
        for os_event in runnable["os_event"].values():
            if os_event["event_type"] not in EVENT_TYPE or "activation_reason_name" not in os_event:
                continue
            activation_reason = {}
            activation_reason["mask"] = os_event["event_mask"].upper()
            activation_reason["name"] = os_event["activation_reason_name"]
            activation_reasons.append(activation_reason)
        activation_reasons.sort(key=lambda x: x["name"])
        return activation_reasons

    @staticmethod
    @pass_context
    def get_runnable_args(context, runnable_name, task_name):
        runnable = context["task_mappings"][task_name]["schedulable_entity"][runnable_name]
        for os_event in runnable["os_event"].values():
            if "activation_reason_name" in os_event:
                return f"(Rte_ActivatingEvent_{runnable_name})activationVector"
        return ""

    @staticmethod
    @pass_context
    def get_task_activation_vector_type(context, task_name):
        runnables = context["task_mappings"][task_name]["schedulable_entity"]
        max_bit_position = -1
        for runnable in runnables.values():
            for os_event in runnable["os_event"].values():
                if "activation_bit_position" not in os_event:
                    continue
                max_bit_position = max(max_bit_position, int(os_event["activation_bit_position"]))
        if max_bit_position == -1:
            return ""
        type_str = Function.get_activation_vector_type_from_bit_position(max_bit_position)
        return type_str

    @staticmethod
    @pass_context
    def is_rte_dlog_enabled(context):
        return (
            "RteGeneration_dict" in context
            and "RteDevErrorDetect" in context["RteGeneration_dict"]
            and context["RteGeneration_dict"]["RteDevErrorDetect"]
        )

    @staticmethod
    @pass_context
    def rte_swc_header_need_include_os_header(context):
        runnables = Function.get_runnable_entity_list(context)
        eas = Function.get_can_enter_exclusive_areas(context, runnables)
        return len(eas) > 0

    @staticmethod
    @pass_context
    def get_user_code_list(context):
        usercode_list = context["swc"]["usercode"]
        return usercode_list

    @staticmethod
    @pass_context
    def all_complex_data_init_values_zero(context, item):
        is_all_zeros = False
        is_all_zeros = AutosarUtils.are_all_elements_zero(item)
        return is_all_zeros

    @staticmethod
    @pass_context
    def get_alive_check_point_func_param(context, task_name, event_name):
        """
        WdgM_CheckpointReached(first_param, first_param);
        first_param: {task_name}_Alive, second_param: max_cycle_event_name_CP
        """
        return (f"WdgMConf_WdgMSupervisedEntity_{task_name}_Alive", f"WdgMConf_WdgMCheckpoint_{event_name}_CP")

    @staticmethod
    @pass_context
    def get_activate_se_name(context, task_name):
        max_period_ev_name = Function.get_max_period_event_in_period_task(context, task_name)
        if max_period_ev_name:
            return Function.get_alive_check_point_func_param(context, task_name, "")[0]
        return ""

    @staticmethod
    @pass_context
    def get_max_period_event_in_period_task(context, task_name):
        """
        get max period event name in periodic task.
        if task does not have periodic event, then skip it
        """
        alive_container_path = f"/ActiveEcuC/WdgM/WdgMGeneral/{task_name}_Alive"
        if not context["ecuc_config"]:
            return ""
        wdgm_config = context["ecuc_config"].get("WdgM", None)
        if not wdgm_config:
            return ""
        alive_container = wdgm_config.find(alive_container_path)

        if not alive_container:
            return ""

        for event_name in context["task_mappings"][task_name]["event"].keys():
            cp_container_path = f"{alive_container_path}/{event_name}_CP"
            cp_container = context["ecuc_config"]["WdgM"].find(cp_container_path)
            if cp_container:
                return event_name
        return ""

    @staticmethod
    @pass_context
    def wdgm_configured_in_isolate(context) -> bool:
        wdgm_configured = False
        if not context["ecuc_config"] or not context["ecuc_config"].get("Isolate", None):
            return wdgm_configured
        isolate_config = context["ecuc_config"]["Isolate"]
        ecuc_path = "/ActiveEcuC/Isolate/WdgM"
        mod_path = "/Isolate/Module"
        container_obj = isolate_config.find(ecuc_path)
        if container_obj and get_definition_ref(container_obj).endswith(mod_path):
            wdgm_configured = True

        return wdgm_configured

    @staticmethod
    @pass_context
    def rte_configured_in_isolate(context) -> bool:
        rte_configured = False
        if not context["ecuc_config"] or not context["ecuc_config"].get("Isolate", None):
            return rte_configured
        isolate_config = context["ecuc_config"]["Isolate"]
        ecuc_path = "/ActiveEcuC/Isolate/Rte"
        mod_path = "/Isolate/Module"
        container_obj = isolate_config.find(ecuc_path)
        if container_obj and get_definition_ref(container_obj).endswith(mod_path):
            rte_configured = True

        return rte_configured

    @staticmethod
    @pass_context
    def task_alive_configured_in_curr_appl(context):
        task_list = Function.get_cur_appl_extended_task_list(context)
        for task in task_list:
            if Function.get_max_period_event_in_period_task(context, task.get("task_name", "")) != "":
                return True
        return False

    @staticmethod
    @pass_context
    def get_all_pim_user_typedefs(context):
        typedefs = []
        if not context["asw_cfg"]:
            return typedefs
        for swc in context["asw_cfg"].values():
            type_def_pims = swc["pim"]["type_def"] if swc["pim"] else {}
            if not type_def_pims:
                continue
            for pim in type_def_pims.values():
                typedefs.append(f"typedef {pim['pim_type_def']} Rte_PimType_{pim['swc_type']}_{pim['pim_type']};")
        typedefs.sort()
        return typedefs

    @staticmethod
    @pass_context
    def get_swc_pim_user_typedefs(context):
        typedefs = []
        if not context["swc"]:
            return typedefs
        type_def_pims = context["swc"]["pim"]["type_def"] if context["swc"]["pim"] else {}
        if not type_def_pims:
            return typedefs
        for pim in type_def_pims.values():
            typedefs.append(f"typedef {pim['buff_type']} {pim['pim_type']};")
        typedefs.sort()
        return typedefs

    @staticmethod
    @pass_context
    def get_swc_pim_var_and_api(context):
        vars = []
        vars_no_init_value = []
        apis = []
        if not context["swc"]:
            return vars, apis
        user_defined_pims = context["swc"]["pim"]["user_defined"] if context["swc"]["pim"] else {}
        if user_defined_pims:
            for pim in user_defined_pims.values():
                apis.append(pim)
                vars_no_init_value.append(pim)
        ar_typed_pims = context["swc"]["pim"]["ar_typed"] if context["swc"]["pim"] else {}
        if ar_typed_pims:
            for pim in ar_typed_pims.values():
                apis.append(pim)
                if pim["init_value"]:
                    vars.append(pim)
                else:
                    vars_no_init_value.append(pim)
        vars.sort(key=lambda x: x["buff"])
        vars_no_init_value.sort(key=lambda x: x["buff"])
        apis.sort(key=lambda x: x["buff"])
        return vars, vars_no_init_value, apis

    @staticmethod
    @pass_context
    def get_osa_pim_var(context, osa):
        vars = []
        vars_no_init_value = []
        for swc in context["asw_cfg"].values():
            if swc["osapplication"] != osa:
                continue
            user_defined_pims = swc["pim"]["user_defined"]
            if user_defined_pims:
                for pim in user_defined_pims.values():
                    vars_no_init_value.append(pim)
            ar_typed_pims = swc["pim"]["ar_typed"]
            if ar_typed_pims:
                for pim in ar_typed_pims.values():
                    if pim["init_value"]:
                        vars.append(pim)
                    else:
                        vars_no_init_value.append(pim)
        vars.sort(key=lambda x: x["buff"])
        vars_no_init_value.sort(key=lambda x: x["buff"])
        return vars, vars_no_init_value

    @staticmethod
    def __is_irv_api_func(access):
        return (not access["data"]["is_implicit"]) and (access["m_to_n"] != "0") and (access["lock"] != "NONE")

    @staticmethod
    def __get_irv_api(irvs, apis, access_type, is_implicit, is_func, runnable=None):
        if not irvs:
            return
        for irv_data in irvs.values():
            if is_implicit != irv_data["is_implicit"]:
                continue
            for access in irv_data[access_type]:
                if runnable and runnable != access["runnable"][0]:
                    continue
                # implicit (all macro) or explicit (partly macro)
                if is_func == Function.__is_irv_api_func(access):
                    apis.append(access)

    @staticmethod
    def __get_osa_irv_api(context, osa, access_type, is_implicit, is_func):
        apis = []
        for swc in context["asw_cfg"].values():
            if swc["osapplication"] != osa:
                continue
            Function.__get_irv_api(swc["irv"]["data"], apis, access_type, is_implicit, is_func)
        return apis

    @staticmethod
    def __get_swc_irv_api(context, runnable, access_type, is_implicit, is_func):
        apis = []
        if not context["swc"] or not context["swc"]["irv"]:
            return apis
        Function.__get_irv_api(
            context["swc"]["irv"]["data"], apis, access_type, is_implicit, is_func, runnable=runnable
        )
        return apis

    @staticmethod
    @pass_context
    def get_osa_irv_exp_write_api_func(context, osa):
        return Function.__get_osa_irv_api(context, osa, "w", False, True)

    @staticmethod
    @pass_context
    def get_osa_irv_exp_read_api_func(context, osa):
        return Function.__get_osa_irv_api(context, osa, "r", False, True)

    @staticmethod
    @pass_context
    def get_osa_irv_imp_write_api_macro(context, osa):
        return Function.__get_osa_irv_api(context, osa, "w", True, False)

    @staticmethod
    @pass_context
    def get_osa_irv_imp_read_api_macro(context, osa):
        return Function.__get_osa_irv_api(context, osa, "r", True, False)

    @staticmethod
    @pass_context
    def get_swc_irv_exp_write_api_func(context, runnable=None):
        return Function.__get_swc_irv_api(context, runnable, "w", False, True)

    @staticmethod
    @pass_context
    def get_swc_irv_exp_write_api_macro(context, runnable=None):
        return Function.__get_swc_irv_api(context, runnable, "w", False, False)

    @staticmethod
    @pass_context
    def get_swc_irv_exp_read_api_func(context, runnable=None):
        return Function.__get_swc_irv_api(context, runnable, "r", False, True)

    @staticmethod
    @pass_context
    def get_swc_irv_exp_read_api_macro(context, runnable=None):
        return Function.__get_swc_irv_api(context, runnable, "r", False, False)

    @staticmethod
    @pass_context
    def get_swc_irv_imp_write_api_macro(context, runnable=None):
        return Function.__get_swc_irv_api(context, runnable, "w", True, False)

    @staticmethod
    @pass_context
    def get_swc_irv_imp_read_api_macro(context, runnable=None):
        return Function.__get_swc_irv_api(context, runnable, "r", True, False)

    @staticmethod
    def __is_irv_var_def(data):
        # unconn write does NOT need def
        return data["m_to_n"] != "0" or data["r"]

    @staticmethod
    def __get_irv_var(swc, vars, vars_no_init_value):
        for irv_data in swc["irv"]["data"].values():
            if not Function.__is_irv_var_def(irv_data):
                continue
            if irv_data["init_value"]:
                vars.append(irv_data)
            else:
                vars_no_init_value.append(irv_data)

    @staticmethod
    @pass_context
    def get_osa_irv_var(context, osa):
        vars = []
        vars_no_init_value = []
        for swc in context["asw_cfg"].values():
            if swc["osapplication"] != osa:
                continue
            Function.__get_irv_var(swc, vars, vars_no_init_value)
        return vars, vars_no_init_value

    @staticmethod
    @pass_context
    def get_swc_irv_var_exp(context):
        vars = []
        vars_no_init_value = []
        if not context["swc"] or not context["swc"]["irv"]:
            return vars, vars_no_init_value
        for irv_data in context["swc"]["irv"]["data"].values():
            if irv_data["is_implicit"]:
                continue
            if not Function.__is_irv_var_def(irv_data):
                continue
            if irv_data["init_value"]:
                vars.append(irv_data)
            else:
                vars_no_init_value.append(irv_data)
        return vars, vars_no_init_value

    @staticmethod
    def __get_irv_var_imp_copy(swc, imp_var_copy):
        if not swc["irv"]:
            return
        for irv_data in swc["irv"]["data"].values():
            if irv_data["is_implicit"]:
                if irv_data["m_to_n"] != "0":
                    for access in irv_data["w"]:
                        imp_var_copy.append(access)
                for access in irv_data["r"]:
                    imp_var_copy.append(access)

    @staticmethod
    @pass_context
    def get_osa_irv_var_imp_copy(context, osa):
        imp_var_copy = []
        for swc in context["asw_cfg"].values():
            if swc["osapplication"] != osa:
                continue
            Function.__get_irv_var_imp_copy(swc, imp_var_copy)
        return imp_var_copy

    @staticmethod
    @pass_context
    def get_swc_irv_var_imp_copy(context):
        imp_var_copy = []
        if not context["swc"]:
            return imp_var_copy
        Function.__get_irv_var_imp_copy(context["swc"], imp_var_copy)
        return imp_var_copy

    @staticmethod
    @pass_context
    def get_osa_implicit_irv_access(context, osa):
        irv_write_dict = {}
        irv_read_dict = {}
        for access in Function.get_osa_irv_imp_write_api_macro(context, osa):
            if access["m_to_n"] == "0":
                continue
            task = access["task"][0]
            if task not in irv_write_dict:
                irv_write_dict[task] = {}
            run = access["runnable"][0]
            if run not in irv_write_dict[task]:
                irv_write_dict[task][run] = []
            irv_write_dict[task][run].append(access)
        for access in Function.get_osa_irv_imp_read_api_macro(context, osa):
            task = access["task"][0]
            if task not in irv_read_dict:
                irv_read_dict[task] = {}
            run = access["runnable"][0]
            if run not in irv_read_dict[task]:
                irv_read_dict[task][run] = []
            irv_read_dict[task][run].append(access)
        return irv_write_dict, irv_read_dict

    @pass_context
    def get_all_vfb_hook_name_list(context) -> list:
        vfb_hook_name_list = []
        vfb_hooks_info = context.get("vfb_trace_hooks_info", None)
        if not vfb_hooks_info:
            return vfb_hook_name_list

        for hook_dict in vfb_hooks_info.values():
            if not hook_dict:
                continue
            hook_list = hook_dict.get("hook_list", [])
            if not hook_list:
                continue
            vfb_hook_name_list.extend(hook_list)

        return vfb_hook_name_list

    @pass_context
    def get_vfb_trace_start_stop_function_call(context):
        """
        get trace_start/trace_stop function call
        """
        vfb_func_call = []
        vfb_hooks_dict = context.get("vfb_trace_hooks_info", {})
        for _, hook_info in vfb_hooks_dict.items():
            measurement_id_str = hook_info.get("measurement_id", "")
            hook_name_list = hook_info.get("hook_list", [])
            if not measurement_id_str:
                continue
            for hook_name in hook_name_list:
                if hook_name and hook_name.endswith("_Start"):
                    vfb_func_call.append([hook_name, f"Runnable_Trace_Start({measurement_id_str});"])
                elif hook_name and hook_name.endswith("_Return"):
                    vfb_func_call.append([hook_name, f"Runnable_Trace_Stop({measurement_id_str});"])

        return vfb_func_call

    @pass_context
    def get_vfb_runnable_hook_name(context, in_runnable_name: str):
        hooks_start_str, hooks_end_str = "", ""
        vfb_hooks_info = context.get("vfb_trace_hooks_info", None)
        if not vfb_hooks_info:
            return "", ""

        for hook_runnable_name, hook_name_dict in vfb_hooks_info.items():
            if hook_runnable_name == in_runnable_name:
                for hooks_name in hook_name_dict.get("hook_list", []):
                    if hooks_name and hooks_name.endswith("_Start"):
                        hooks_start_str = hooks_name
                    elif hooks_name and hooks_name.endswith("_Return"):
                        hooks_end_str = hooks_name

        return hooks_start_str, hooks_end_str

    @pass_context
    def is_vfb_trace_enabled(context) -> bool:
        ecuc_obj = context.get("ecuc_config", None)
        module_name = "Rte"
        if not ecuc_obj or module_name not in ecuc_obj.keys():
            return False
        rte_vfb_container_path = "/ActiveEcuC/Rte/RteGeneration"
        param_name = "RteVfbTraceEnabled"

        rte_vfb_container_obj = ecuc_obj[module_name].find(rte_vfb_container_path)
        if not rte_vfb_container_obj:
            return False
        for param_obj in getattr(getattr(rte_vfb_container_obj, "PARAMETER_VALUES"), "ECUC_NUMERICAL_PARAM_VALUE", []):
            definition_ref = get_definition_ref(param_obj)
            if definition_ref and definition_ref.split("/")[-1] == param_name:
                enable_value = get_value(param_obj)
                return enable_value == "true"
        return False

    @staticmethod
    def get_imp_sr_var_name(port):
        if port["imp_sr_copy_buf_opt"]:
            return port["variable"]
        else:
            return (
                f'Rte_{port["task"]}.Rte_RB.Rte_{port["component"]}_{port["runnable"]}.'
                f'Rte_{port["port_prototype"]}_{port["data_element"]}'
            )

    @staticmethod
    def get_swc_sr_implicit_intra_osa_opt_ports(ports):
        port_list = []
        for port in ports:
            if port["imp_sr_copy_buf_opt"] and port["imp_sr_buf_opt_intra_osa"]:
                port_list.append(port)
        return port_list

    @staticmethod
    @pass_context
    def get_swc_standard_internal_trigger_api(context, runnable=None):
        # internal trigger api in swc.c
        internal_trigger = {}
        if "asw_cfg" in context:
            # for Rte_OsApplication.c.jinja2
            for swc in context["asw_cfg"].values():
                Function.get_internal_trigger(swc, internal_trigger, "STANDARD", runnable)
        elif "swc" in context:
            # for rte_swc.c.jinja2/rte_swc.h.jinja
            Function.get_internal_trigger(context["swc"], internal_trigger, "STANDARD", runnable)
        return internal_trigger

    @staticmethod
    @pass_context
    def get_swc_standard_internal_triggered_api(context, runnable=None):
        # internal triggered api in swc.c
        internal_triggered = set()
        internal_trigger = Function.get_swc_standard_internal_trigger_api(context)
        for _, value in internal_trigger.items():
            for sub_value in value:
                triggerd_runnable = sub_value["triggered_runnable"]
                if runnable != triggerd_runnable:
                    continue
                internal_triggered.add(f"{sub_value['trigger_runnable']}/{sub_value['trigger_point']}")
        return internal_triggered

    @staticmethod
    @pass_context
    def get_standard_internal_trigger_api(context):
        internal_trigger = {}
        if "asw_cfg" in context:
            # for Rte_OsApplication.c.jinja2
            for swc in context["asw_cfg"].values():
                Function.get_internal_trigger(swc, internal_trigger, "STANDARD")
        elif "swc" in context:
            # for rte_swc.c.jinja2/rte_swc.h.jinja
            Function.get_internal_trigger(context["swc"], internal_trigger, "STANDARD")
        return internal_trigger

    @staticmethod
    @pass_context
    def get_internal_trigger(swc, trigger, type, runnable=None):
        for key, value in swc["runnables"].items():
            if runnable and key != runnable:
                continue
            if not value.get("internal_trigger", []):
                continue
            triggered_runnable_list = set()
            for it in value["internal_trigger"]:
                if it["trigger_type"] != type:
                    continue
                swc_runnable_trigger = "/".join([it["swc_prototype"], it["trigger_runnable"], it["trigger_point"]])
                if swc_runnable_trigger not in trigger:
                    trigger.update({swc_runnable_trigger: []})
                if it["triggered_runnable"] in triggered_runnable_list:
                    # 针对多个相同的trigger触发同一个runnable的情况
                    continue
                trigger[swc_runnable_trigger].append(it)
                triggered_runnable_list.add(it["triggered_runnable"])

    @staticmethod
    @pass_context
    def get_swc_external_trigger_api(context, runnable):
        # external trigger api in swc.c
        external_trigger = []
        if "asw_cfg" in context:
            # for Rte_OsApplication.c.jinja2
            for swc in context["asw_cfg"].values():
                Function.get_external_trigger(swc, external_trigger, "trigger", runnable)
        elif "swc" in context:
            # for rte_swc.c.jinja2/rte_swc.h.jinja
            Function.get_external_trigger(context["swc"], external_trigger, "trigger", runnable)
        return external_trigger

    @staticmethod
    @pass_context
    def get_swc_external_triggered_api(context, runnable):
        # external triggered api in swc.c
        external_triggered = []
        external_trigger = []
        if "asw_cfg" in context:
            # for Rte_OsApplication.c.jinja2
            for swc in context["asw_cfg"].values():
                Function.get_external_trigger(swc, external_trigger, "triggered", runnable)
        elif "swc" in context:
            # for rte_swc.c.jinja2/rte_swc.h.jinja
            Function.get_external_trigger(context["swc"], external_trigger, "triggered", runnable)
        for et in external_trigger:
            external_triggered.append({"port_prototype": et["port_prototype"], "data_element": et["data_element"]})
        return external_triggered

    @staticmethod
    @pass_context
    def get_external_trigger_api(context):
        external_trigger = []
        if "asw_cfg" in context:
            # for Rte_OsApplication.c.jinja2
            for swc in context["asw_cfg"].values():
                Function.get_external_trigger(swc, external_trigger, "trigger")
        elif "swc" in context:
            # for rte_swc.c.jinja2/rte_swc.h.jinja
            Function.get_external_trigger(context["swc"], external_trigger, "trigger")
        return external_trigger

    @staticmethod
    @pass_context
    def get_external_trigger(swc, trigger, dir, runnable=None):
        ports = "pports" if dir == "trigger" else "rports"
        for _, value in swc[ports].items():
            if value["type"] != "External Trigger":
                continue
            if runnable and runnable not in value["symbol"]:
                continue
            trigger.append(value)

    @staticmethod
    def get_sr_explicit_rte_interface_code_format(port):
        if not port["has_prport"] and port["m_to_n"] in {"0", "mn"} and port["signal_category"] == "None":
            return _UNCONNECT
        else:
            if port["signal_category"] != "None":
                if port.get("dm_macro_api", False) is True:
                    return _MACRO
                return _FUNC
            # if port["arg"]["datatype"]["native_category"] != ["NUMERICAL", "ARRAY", "STRUCTURE"]:
            #     return _FUNC
            if port.get("set_events", []) != []:
                return _FUNC
            if port["lock"] != "NONE":
                return _FUNC
            if port["enable_update"]:
                return _FUNC
            if not port["has_prport"] and port["m_to_n"] == "n1" and port["intra_osa"] is not True:
                return _FUNC
        return _MACRO

    @staticmethod
    def get_sr_merged_events_with_same_task(port):
        merged_events = {}
        multievent_tasks = set()
        for event in port["set_events"]:
            task_id = event["task_id"]
            event_mask = event["event_mask"].upper()
            if task_id not in merged_events.keys():
                merged_events[task_id] = {"task_id": task_id, "event_mask": event_mask}
                continue
            merged_events[task_id]["event_mask"] += f"|{event_mask}"
            multievent_tasks.add(task_id)

        for multievent_task in multievent_tasks:
            merged_events[multievent_task]["event_mask"] = f'({merged_events[multievent_task]["event_mask"]})'
        return list(merged_events.values())

    @staticmethod
    @pass_context
    def get_os_task_accessing_application(context):
        memmap = {}
        core_id_list = context["core_id_list"]
        task_mappings = context["task_mappings"]
        for core_id in core_id_list:
            memmap[core_id] = None
            for task_name, info in task_mappings.items():
                if info["core_id"] != core_id:
                    continue
                if "EcuM_MainFunction" in info["schedulable_entity"]:
                    appl_name = info["application"]
                    memmap[core_id] = f"SHARED_{appl_name}"
                    break
        return memmap

    @staticmethod
    def get_sr_write_data_arg(datatype, type="sr"):
        if datatype["native_category"] == "NUMERICAL":
            if type == "sr":
                data_arg = datatype["name"] + " data"
            else:
                data_arg = "const " + datatype["name"] + " data"
        elif datatype["native_category"] == "ARRAY":
            data_arg = "const " + datatype["arr_basetype"] + " *data"
        else:
            data_arg = "const " + datatype["name"] + " *data"
        return data_arg

    @staticmethod
    def get_sr_read_data_arg(datatype, type="sr"):
        if datatype["native_category"] == "NUMERICAL":
            if type == "sr":
                data_arg = datatype["name"] + " *data"
            else:
                data_arg = "void"
        elif datatype["native_category"] == "ARRAY":
            data_arg = datatype["arr_basetype"] + " *data"
        else:
            data_arg = datatype["name"] + " *data"
        return data_arg

    @staticmethod
    def get_sr_iread_prefix_arg(datatype, type="sr"):
        if datatype["native_category"] == "NUMERICAL":
            data_arg = datatype["name"] + " "
        elif datatype["native_category"] == "ARRAY":
            if type == "sr":
                data_arg = datatype["arr_basetype"] + " *"
            else:
                data_arg = "const " + datatype["arr_basetype"] + " *"
        else:
            if type == "sr":
                data_arg = datatype["name"] + " *"
            else:
                data_arg = "const " + datatype["name"] + " *"
        return data_arg

    @staticmethod
    @pass_context
    def get_cal_prm_consts(context):
        return context["cal_prm"].get("consts", {})

    @staticmethod
    @pass_context
    def get_cal_prm_rports_connected(context, swc):
        return context["cal_prm"].get("prm_rports_connected", {}).get(swc, [])
