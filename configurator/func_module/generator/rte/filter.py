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
rte对象解析模块,用于兼容模式

解析输入的josn object, 然后生成模板需要的参数对象.
"""
from decimal import Decimal


def get_task_mappings_dict_form_task_mapping_info(task_mapping_info: dict) -> dict:
    """
    Get the task and schedulable entity required by the task mapping,
    Used for Rte_OsApplication.c/h template generation task entity.

    Arg:
      config_dict : All config dictionary

    Return:
      Returns a dictionary of schedulable entity mapping to the task
      task_mappings: {
        "task_name": {
          "core_id": "0",
          "schedulable_entity": {
            "schedulable_entity_name": {
              "name": "schedulable_entity_name",
              "period": "period(int)" ,
              "position_in_task": "position(int)",
              "os_event": {
                "event_name": {
                  "event_name": "event_name",
                  "event_type": "event_type"
                }
              }
            }
          },
          "alarm": {
            "alarm_name": {
              "alarm_action_type": "OsAlarmSetEvent" or "OsAlarmActivateTask",
              "alarm_action": "event_name" or "task_name",
            }
          },
          "event": {
            "schedulable_entity_name": {
              "event_type": "event_type",
              "period": "period(int)"
            }
          },
        },
        ...
      }
    """
    task_mappings = {}
    for task_name, task_info in task_mapping_info.items():
        if task_name not in task_mappings:
            task_mapping = dict.fromkeys(
                ["core_id", "task_type", "task_schedule", "task_priority", "schedulable_entity", "alarm", "event"]
            )
            task_mapping["task_name"] = task_name
            task_mapping["core_id"] = task_info["core_id"]
            task_mapping["application"] = task_info["application"]
            task_mapping["task_type"] = task_info["task_type"]
            task_mapping["task_schedule"] = task_info["task_schedule"]
            task_mapping["task_priority"] = task_info["task_priority"]
            task_mapping["task_autostart"] = task_info["task_autostart"]
            task_mapping["os_counter"] = task_info["os_counter"]
            task_mapping["schedulable_entity"] = {}
            task_mapping["alarm"] = {}
            task_mapping["event"] = {}
            task_mapping["is_bsw"] = False
            task_mapping["has_unique_sch_tbl"] = task_info.get("has_unique_sch_tbl", False)
            task_mapping["schedule_table_list"] = task_info.get("schedule_table_list", [])
            task_mappings[task_name] = task_mapping
        task_mapping = task_mappings[task_name]
        alarm_info_list = task_info["alarm_info_list"]
        schedulable_entity_info_list = task_info["schedulable_entity_info_list"]
        for i in range(len(schedulable_entity_info_list)):
            schedulable_entity_info = schedulable_entity_info_list[i]
            alarm_info = alarm_info_list[i]
            task_mapping_add_schedulable_entity(task_mapping, schedulable_entity_info)
            task_mapping_add_event(task_mapping, schedulable_entity_info)
            task_mapping_add_alarm(task_mapping, schedulable_entity_info, alarm_info)
    return task_mappings


def task_mapping_add_schedulable_entity(task_mapping: dict, schedulable_entity_info: dict):
    """
    Add task binding schedulable entity information to task_mapping.

    Arg:
      task_mapping: one of task_mappings.
      schedulable_entity_info: task binding schedulable entity information.
    """
    name = schedulable_entity_info["name"]
    is_bsw = schedulable_entity_info["is_bsw"]
    task_mapping["is_bsw"] = is_bsw or task_mapping["is_bsw"]
    if name not in task_mapping["schedulable_entity"]:
        schedulable_entity = dict.fromkeys(["name", "period", "position_in_task", "os_event"])
        schedulable_entity["name"] = name
        schedulable_entity["is_bsw"] = schedulable_entity_info["is_bsw"]
        schedulable_entity["component"] = schedulable_entity_info["component"]
        schedulable_entity["period"] = schedulable_entity_info["period"]
        schedulable_entity["position_in_task"] = schedulable_entity_info["position_in_task"]
        schedulable_entity["exclusive_areas"] = schedulable_entity_info["exclusive_areas"]
        schedulable_entity["os_event"] = {}
        task_mapping["schedulable_entity"][name] = schedulable_entity
    elif is_bsw:
        schedulable_entity = task_mapping["schedulable_entity"][name]
        schedulable_entity["is_bsw"] = is_bsw
        schedulable_entity["component"] = schedulable_entity_info["component"]
        schedulable_entity["exclusive_areas"] = schedulable_entity_info["exclusive_areas"]

    task_mapping["schedulable_entity"][name]["mode_disabling_info"] = schedulable_entity_info["mode_disabling_info"]
    event_mask = schedulable_entity_info["event_mask"]
    event_type = schedulable_entity_info["event_type"]
    os_event_value = {"event_mask": event_mask, "event_type": event_type}
    os_event = {}
    if event_mask:
        os_event.update({event_mask: os_event_value})
    else:
        os_event.update({event_type: os_event_value})
    task_mapping["schedulable_entity"][name]["os_event"].update(os_event)

    activation_reason = schedulable_entity_info.get("activation_reason")
    if activation_reason:
        os_event_value["activation_reason_name"] = activation_reason["name"]
        os_event_value["activation_bit_position"] = activation_reason["bit_position"]
        schedulable_entity = task_mapping["schedulable_entity"][name]
        if "activation_reason" not in schedulable_entity:
            schedulable_entity["activation_reason"] = []
        schedulable_entity["activation_reason"].append(activation_reason)


def task_mapping_add_event(task_mapping: dict, schedulable_entity_info: dict):
    """
    Add task binding event information to task_mapping.

    Arg:
      task_mapping: one of task_mappings.
      schedulable_entity_info: task binding schedulable entity information.
    """
    event_mask = schedulable_entity_info["event_mask"]
    event_type = schedulable_entity_info["event_type"]
    offset = schedulable_entity_info["offset"]
    period = schedulable_entity_info["period"]
    if event_mask:
        task_mapping["event"].update(
            {event_mask: {"event_type": event_type, "alarm_time": offset, "cycle_time": period}}
        )


def task_mapping_add_alarm(task_mapping: dict, schedulable_entity_info: dict, used_os_alarm_info: dict):
    """
    Add task binding alarm information to task_mapping.

    Arg:
      task_mapping: one of task_mappings.
      schedulable_entity_info: task binding schedulable entity information.
      used_os_alarm_info: task binding alarm information.
    """
    if used_os_alarm_info is None:
        return
    event_mask = schedulable_entity_info["event_mask"]
    event_type = schedulable_entity_info["event_type"]
    task_type = task_mapping["task_type"]
    alarm_time, cycle_time = None, None
    if event_mask is None and event_type == "TimingEvent" and task_type in {"AUTO", "BASIC"}:
        alarm_time = schedulable_entity_info["offset"]
        cycle_time = schedulable_entity_info["period"]
    alarm_info = dict.fromkeys(["alarm_name", "alarm_action_type", "alarm_action", "alarm_time", "cycle_time"])
    alarm_info["alarm_name"] = used_os_alarm_info["alarm_name"]
    alarm_info["alarm_action"] = used_os_alarm_info["alarm_action"]
    alarm_info["alarm_action_type"] = used_os_alarm_info["alarm_action_type"]
    alarm_info["alarm_time"] = alarm_time
    alarm_info["cycle_time"] = cycle_time
    alarm_info["is_bsw"] = schedulable_entity_info["is_bsw"]
    alarm_name = alarm_info["alarm_name"]
    if alarm_name in task_mapping["alarm"]:
        alarm_info["is_bsw"] |= task_mapping["alarm"][alarm_name]["is_bsw"]
    else:
        task_mapping["alarm"][alarm_name] = alarm_info


def get_core_to_appl_dict(task_mappings: dict):
    appl_set = set()
    core_to_appl = {}
    for task in task_mappings.values():
        core_id = str(task["core_id"])
        application = task["application"]
        if core_id not in core_to_appl:
            core_to_appl[core_id] = set()
        core_to_appl[core_id].add(application)
        appl_set.add(application)
    return sorted(appl_set), dict(map(lambda item: (item[0], sorted(item[1])), core_to_appl.items()))


def get_appl_to_task_dict(task_mappings: dict) -> dict:
    appl_to_task_dict = {}
    for task_name, task in task_mappings.items():
        application = task["application"]
        if application not in appl_to_task_dict:
            appl_to_task_dict[application] = {}
        appl_to_task_dict[application][task_name] = task
    return appl_to_task_dict


def get_core_to_task_dict(task_mappings: dict) -> dict:
    """
    Get the relationship of task mapping to the core,
    Used for Rte.c template generation life cycle api.

    Arg:
      task_mappings: a dictionary of task mapping to task

    Return:
      Returns a dictionary of task mapping to the task
      {
        "0": [
          {
            "name": "Default_BSW_Async_Task_Core0",
            "is_bsw_task": true
          },
          {
            "name": "Default_Appl_Task_Core0",
            "is_bsw_task": false
          },
        ],
      }
    """
    core_to_task_dict = {}
    for task_name, task in task_mappings.items():
        if task["task_autostart"] == "TRUE":
            continue
        core_id = str(task["core_id"])
        if core_id not in core_to_task_dict:
            core_to_task_dict[core_id] = []
        task_dict = {}
        task_dict["name"] = task_name
        task_dict["is_basic"] = bool(task["task_type"] == "BASIC")
        task_dict["is_bsw_task"] = task["is_bsw"]
        task_dict["is_schedule_table_task"] = False
        if task["schedule_table_list"]:
            task_dict["is_schedule_table_task"] = True
            task_dict["has_unique_sch_tbl"] = task.get("has_unique_sch_tbl", True)

        core_to_task_dict[core_id].append(task_dict)
    return core_to_task_dict


def get_core_to_alarm_dict(task_mappings) -> dict:
    """
    Get the relationship of alarm mapping to the core,
    Used for Rte.c template generation life cycle api.

    Arg:
      task_mappings: a dictionary of task mapping to task

    Return:
      Returns a dictionary of alarm mapping to the core
      {
        "0": [
          {
            "name": "Rte_Al_XXX",
            "is_bsw_alarm": true,
            "alarm_time": 20,
            "cycle_time": "10"
          },
        ],
      }
    """

    core_to_alarm_dict = {}
    for task_dict in task_mappings.values():
        core_id = str(task_dict["core_id"])
        if len(task_dict["alarm"]) == 0:
            continue
        alarm_info_list = get_task_alarm_info_list(task_dict)
        if len(alarm_info_list) == 0:
            continue
        if core_id not in core_to_alarm_dict:
            core_to_alarm_dict[core_id] = []
        counter_info = task_dict["os_counter"]
        for alarm_info in alarm_info_list:
            alarm_dict = dict.fromkeys(["name", "is_bsw_alarm", "alarm_time", "cycle_time"])
            alarm_dict["name"] = alarm_info["alarm_name"]
            alarm_dict["is_bsw_alarm"] = alarm_info["is_bsw"]
            # NOTE:从这里转换最合适，因为core_to_alarm_dict就是给生成alarm用的，其他的不受影响
            alarm_dict["alarm_time"] = get_counter_tick(counter_info, alarm_info["alarm_time"])
            alarm_dict["cycle_time"] = get_counter_tick(counter_info, alarm_info["cycle_time"])
            core_to_alarm_dict[core_id].append(alarm_dict)
    return core_to_alarm_dict


def get_task_to_st_dict(task_mappings) -> dict:
    """
    Get the relationship of schedule table list and the task,
    Used for Rte.c template generation life cycle api.

    Arg:
      task_mappings: a dictionary of task mapping to task

    Return:
      Returns a dictionary of schedule table list to the task name
      {
        "Os_Task_Name": [
          {
            "name": "InitScheduleTable",
            "duration": 3,
            "repeat": False,
            "step_dict": {},
            "expiry_point_dict": {},
            "code_gen": True
          },
          {
            "name": "MainScheduleTable",
            "duration": 10,
            "repeat": True,
            "step_dict": {},
            "expiry_point_dict": {},
            "code_gen": True
          },
        ],
      }
    """

    task_to_st_dict = {}
    for task_name, mapping_info in task_mappings.items():
        schedule_table_list = mapping_info["schedule_table_list"]
        task_to_st_dict.update({task_name: schedule_table_list})
    return task_to_st_dict


def get_counter_tick(counter_info, time_value):
    seconds_per_tick = counter_info["OsSecondsPerTick"]
    miliseconds_per_tick = Decimal(str(seconds_per_tick)) * 1000
    tick_count = round(Decimal(str(time_value)) / miliseconds_per_tick)
    if tick_count == 0:
        tick_count = 1

    return tick_count


def get_task_alarm_info_list(task_dict: dict) -> list:
    """
    Get the alarm information of the task binding.

    Arg:
      task_dict: a dictionary containing alarm information of task binding.
      {
        "schedulable_entity_name": {
          "name": "schedulable_entity_name",
          "period": "period(int)" ,
          "position_in_task": "position(int)",
          "os_event": {
            "event_name": {
              "event_name": "event_name",
              "event_type": "event_type"
            }
          }
        },
        "alarm": {
          "alarm_name": {
            "alarm_action_type": "set_event" or "activate_task",
            "alarm_action": "event_name" or "task_name",
          }
        },
        "event": {
          "schedulable_entity_name": {
            "event_type": "event_type",
            "period": "period(int)"
          }
        }
      }

    Return:
      Returns a list of alarm information.
      [
        {"alarm_name": "Rte_Al_TE_XXX", "cycle_time": "10"},
        ...
      ]
    """
    alarm_info_lsit = []
    if len(task_dict["alarm"]) == 0:
        return alarm_info_lsit
    for alarm_name, alarm_dict in task_dict["alarm"].items():
        alarm_info = dict.fromkeys(["alarm_name", "cycle_time"])
        alarm_info["alarm_name"] = alarm_name
        alarm_info["is_bsw"] = alarm_dict["is_bsw"]
        action_type = alarm_dict["alarm_action_type"]
        action = alarm_dict["alarm_action"]
        if action_type == "activate_task":
            alarm_info["alarm_time"] = alarm_dict["alarm_time"]
            alarm_info["cycle_time"] = alarm_dict["cycle_time"]
        elif action_type == "set_event":
            alarm_info["alarm_time"] = task_dict["event"][action]["alarm_time"]
            alarm_info["cycle_time"] = task_dict["event"][action]["cycle_time"]
        alarm_info_lsit.append(alarm_info)
    return alarm_info_lsit


def get_activation_reasons(task_mappings: dict):
    activation_reasons = []
    for task_dict in task_mappings.values():
        for schedulable_entity in task_dict["schedulable_entity"].values():
            if "activation_reason" not in schedulable_entity:
                continue
            activation_reason = {}
            activation_reason_list = sorted(schedulable_entity["activation_reason"], key=lambda x: x["bit_position"])
            activation_reason["schedulable_entity_name"] = schedulable_entity["name"]
            activation_reason["value"] = activation_reason_list
            if len(activation_reason) > 0:
                activation_reasons.append(activation_reason)
    activation_reasons.sort(key=lambda x: (len(x["schedulable_entity_name"]), x["schedulable_entity_name"]))
    return activation_reasons


def get_template_input_parameter_dict_from_parsed_data(config_dict: dict) -> dict:
    """
    Get input parameter for template generated code for VCOS Design(Excel).

    Arg:
        config_dict : All config dictionary

    Return:
        Returns a dictionary of template input parameter
    """

    # get the task and schedulable entity required by the task mapping in the Rte_OsApplication.c/h template
    task_mappings_info = {}
    if "task_mappings_info" in config_dict:
        task_mappings_info = config_dict["task_mappings_info"]

    task_mappings = get_task_mappings_dict_form_task_mapping_info(task_mappings_info)
    # get the task and runnable required by the task mapping in the Rte.c/h template
    appl_list, core_to_appl_dict = get_core_to_appl_dict(task_mappings)
    core_to_task_dict = get_core_to_task_dict(task_mappings)
    appl_to_task_dict = get_appl_to_task_dict(task_mappings)
    # get the alarm required by the life cycle in the Rte.c template
    core_to_alarm_dict = get_core_to_alarm_dict(task_mappings)
    # Rte_Type.h template
    activation_reasons = get_activation_reasons(task_mappings)
    # get the schedule table list info about task for Rte.c template
    task_to_st_dict = get_task_to_st_dict(task_mappings)

    # Get the signal and SignalGroup for which Data Mapping has been done.
    # Missing data_mapping_config means no mappings yet (AutoC/partial projects).
    _dm = config_dict.get("data_mapping_config") or {}
    signals_and_signalgroups = _dm.get("signals_and_signalgroups", {})

    # Get the port of the data recevied event
    data_received_event = _dm.get("data_received_event_list", [])

    # Get the port associated with the task_id and event_id.
    port_event_id_and_task_id = _dm.get("port_event_id_and_task_id", {})

    data_mapping_sr_rport_required_com_specs = _dm.get("sr_required_com_specs_dict", {})

    RteGeneration_info = {}
    if "RteGeneration" in config_dict:
        RteGeneration_info = config_dict["RteGeneration"]

    input_dict = {
        "core_id_list": sorted(core_to_task_dict),
        "core_to_appl_dict": core_to_appl_dict,
        "core_to_task_dict": core_to_task_dict,
        "appl_to_task_dict": appl_to_task_dict,
        "core_to_alarm_dict": core_to_alarm_dict,
        "task_to_st_dict": task_to_st_dict,
        "appl_list": appl_list,
        "task_mappings": task_mappings,
        "impl_datatype_dict": config_dict["implementation_datatypes"],
        "iso_call_func_include_header_file": config_dict["iso_call_func_include_header_file"],
        "asw_cfg": config_dict["asw_config"],
        "mode_declaration_group": config_dict["mode_declaration_group"],
        "swc_list": [],
        "signals_and_signalgroups": signals_and_signalgroups,
        "data_received_event": data_received_event,
        "port_event_id_and_task_id": port_event_id_and_task_id,
        "bsw_instances": config_dict["bsw_instances"],
        "sr_required_com_specs_dict": data_mapping_sr_rport_required_com_specs,
        "sr_dm_glob_vars": _dm.get("glob_vars", {}),
        "RteGeneration": RteGeneration_info,
        "appl_dict": config_dict["appl_dict"],
        "os_counter": config_dict["os_counter"],
        "signal_dict": _dm.get("signal_dict", {}),
        "cal_prm": _get_calibration_parameter_codegen_dict(config_dict["asw_config"]),
    }
    if len(activation_reasons) > 0:
        input_dict["activation_reasons"] = activation_reasons
    return input_dict


def _get_calibration_parameter_codegen_dict(asw_cfg, swc=None):
    def port_sort(port):
        type_idx = {"NUMERICAL": 0, "ARRAY": 1, "STRUCTURE": 2}
        return type_idx.get(port["arg"]["datatype"]["native_category"], 3)

    consts = {}
    rports_connected = {}
    rports_unconnected = {}
    for swc_name, swc_info in asw_cfg.items():
        if swc is not None and swc_name != swc:
            continue
        for rport in swc_info["rports"].values():
            if rport["type"] != "CAL_PRM_RPORT":
                continue
            if not rport["connected"]:
                rports_unconnected.setdefault(swc_name, []).append(rport)
                continue
            rports_connected.setdefault(swc_name, []).append(rport)
            const_name = rport["cal_prm_const"]
            if const_name not in consts.keys():
                consts.update({const_name: rport})
            if rport["arg"]["init_value"] and not consts[const_name]["arg"]["init_value"]:
                consts.update({const_name: rport})  # 多个rport时用有初值的替换无初值的
    # 按照swc_prototype和port的数据类型排序
    consts_sorted = dict(sorted(consts.items(), key=lambda x: (x[1]["swc_prototype"], port_sort(x[1]))))
    # 按照port的数据类型排序
    rports_connected_sorted = {k: sorted(v, key=port_sort) for k, v in rports_connected.items()}
    return {"consts": consts_sorted, "prm_rports_connected": rports_connected_sorted}
