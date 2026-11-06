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
rte对象解析模块.

解析输入的配置文件, 然后生成config.json.
"""
from typing import Optional
from decimal import Decimal

from basic_func_module.base_common.load_plug_in import LoadPlugIn
from basic_func_module.autosar_utils import utils
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.autosar_utils.autosar_utils import AutosarUtils
from func_module.health_monitor.logger import logger
from func_module.module_management.arxml_handler.rte_instances.rte_instances_manager import (
    rte_bsw_instances_codegen_parser,
)
from func_module.mapping.data_mapping import DataMapping
from func_module.mapping.task_mapping_helper import BasicTaskScheduleTableManager
from func_module.mapping.schedule_table_mapping import ScheduleTableManager


def get_rte_codegen_dict(
    asw_autosar_dict: dict,
    ecuc_autosar_dict: dict,
    system_autosar_dict: dict,
    internal_behavior_autosar_dict: dict,
    cfg_dict: dict,
    parse_new_dict=True,
):
    if not parse_new_dict and AutosarUtils.get_last_rte_codegen_dict():
        return (
            AutosarUtils.get_rte_codegen_dict(asw_autosar_dict, {}, {}, {}, cfg_dict, parse_new_dict=parse_new_dict),
            AutosarUtils.get_last_task_mapping_info(),
        )

    # init vars
    if "Rte" not in ecuc_autosar_dict or "Os" not in ecuc_autosar_dict:
        return {}, {}

    cfg_dict.setdefault(
        "rte",
        {
            "bsw_instances": {},
            "os_cfg": {},
        },
    )

    # prepare depencies: ecuc info / mapping info / com module config
    __parse_and_update_ecuc_cfg(ecuc_autosar_dict, internal_behavior_autosar_dict, cfg_dict)
    task_mappings_info = get_task_mappings_info(
        asw_autosar_dict.get("asw", None), internal_behavior_autosar_dict, ecuc_autosar_dict
    )
    data_mapping_info = DataMapping.data_mapping_info_to_codegen(
        asw_autosar_dict.get("asw", None), system_autosar_dict, ecuc_autosar_dict.get("Com", None)
    )
    com_cfg_dict = __get_com_cfg_dict(ecuc_autosar_dict, task_mappings_info)
    # get rte codegen dict
    code_gen_dict = AutosarUtils.get_rte_codegen_dict(
        asw_autosar_dict, data_mapping_info, task_mappings_info, com_cfg_dict, cfg_dict, parse_new_dict=parse_new_dict
    )

    return code_gen_dict, task_mappings_info


def get_config_dict(
    asw_autosar_dict,
    ecuc_autosar_dict,
    cfg_dict: dict,
    system_autosar_dict: dict,
    internal_behavior_autosar_dict: dict,
    bswmd_autosar_dict,
    parse_new_dict=True,
):
    """
    主要是获取+构建cfg_dict中的rte部分
    asw_autosar_dict: 解析包括Asw等arxml得到的autosar类型的dict
    ecuc_autosar_dict:  解析包括Os和Rte等arxml得到的autosar类型的dict
    sys_cfg:主要包含Config路径,GenData路径和工程名称等工程信息
    cfg_dict:包含asw,rte,bsw,dbc,ldf,cdd和eb等各类信息
    system_autosar_dict:解析/config/system目录下arxml文件所获取的autosar类型的dict
    internal_behavior_autosar_dict:解析/config/internal_behavior目录下arxml文件所获取的autosar类型的dict
    """
    if "Rte" not in ecuc_autosar_dict or "Os" not in ecuc_autosar_dict:
        return

    code_gen_dict, task_mappings_info = get_rte_codegen_dict(
        asw_autosar_dict,
        ecuc_autosar_dict,
        system_autosar_dict,
        internal_behavior_autosar_dict,
        cfg_dict,
        parse_new_dict=parse_new_dict,
    )

    # update back to cfg_dict / update arxml
    __update_cfg_dict(
        asw_autosar_dict, ecuc_autosar_dict, cfg_dict, internal_behavior_autosar_dict, code_gen_dict, task_mappings_info
    )
    __update_com_ecuc_notifications(cfg_dict, ecuc_autosar_dict)


def __update_cfg_dict(
    asw_autosar_dict, ecuc_autosar_dict, cfg_dict, internal_behavior_autosar_dict, code_gen_dict, task_mappings_info
):
    if "asw" in asw_autosar_dict and asw_autosar_dict["asw"] is not None:
        cfg_dict["rte"]["implementation_datatypes"] = AutosarUtils.to_idt_codegen_dict(
            asw_autosar_dict["asw"], is_re_parsing=False
        )
        cfg_dict["rte"]["mode_declaration_group"] = AutosarUtils.to_mode_group_codegen_dict(asw_autosar_dict["asw"])
    else:
        cfg_dict["rte"]["implementation_datatypes"] = {}
        cfg_dict["rte"]["mode_declaration_group"] = {}

    cfg_dict["rte"]["os_counter"] = AutosarUtils.get_os_counter()
    cfg_dict["rte"]["appl_dict"] = cfg_dict["rte"]["os_cfg"]["OsApplications"]
    cfg_dict["rte"]["alarm_dict"] = cfg_dict["rte"]["os_cfg"]["os_alarms"]
    cfg_dict["rte"]["asw_config"] = code_gen_dict
    __update_task_mapping_info(task_mappings_info, code_gen_dict)
    cfg_dict["rte"]["task_mappings_info"] = task_mappings_info
    __update_vfb_trace(
        asw_autosar_dict, ecuc_autosar_dict, cfg_dict, internal_behavior_autosar_dict, task_mappings_info
    )


def __update_vfb_trace(asw_autosar_dict, ecuc_autosar_dict, cfg_dict, ib_autosar_dict, task_mappings_info):
    from func_module.mapping.task_mapping_helper import get_run_data

    run_data = get_run_data(asw_autosar_dict.get("asw", None), ib_autosar_dict)
    cfg_dict["rte"]["vfb_trace_hooks_info"] = get_vfb_trace_info(ecuc_autosar_dict, run_data, task_mappings_info)


def __get_com_cfg_dict(ecuc_autosar_dict, task_mappings_info):
    try:
        filter = LoadPlugIn.load_module("Com", "config_plug_in.generator.filter")
        get_dynamic_code_template_input_parameter_dict = getattr(
            filter, "get_dynamic_code_template_input_parameter_dict"
        )
        com_cfg_dict = (
            get_dynamic_code_template_input_parameter_dict(
                {
                    "bsw": {
                        "com": AutosarUtil.to_bsw_dict(ecuc_autosar_dict["Com"]),
                        "ecuc": AutosarUtil.to_bsw_dict(ecuc_autosar_dict["EcuC"]),
                    },
                    "rte": {"task_mappings_info": task_mappings_info},
                }
            )
            if ("Com" in ecuc_autosar_dict and "EcuC" in ecuc_autosar_dict)
            else {}
        )
    except Exception:
        com_cfg_dict = {}
        logger.exception(
            "===== Com module parsing error! Please try to upgrade Com module to the latest version! ====="
        )
    return com_cfg_dict


def __parse_and_update_ecuc_cfg(ecuc_autosar_dict, ib_autosar_dict, cfg_dict):
    if "bsw_instances" not in cfg_dict["rte"]:
        cfg_dict["rte"]["bsw_instances"] = {}
    if "os_cfg" not in cfg_dict["rte"]:
        cfg_dict["rte"]["os_cfg"] = {}

    cfg_dict["rte"]["bsw_instances"].update(rte_bsw_instances_codegen_parser(ecuc_autosar_dict, ib_autosar_dict))
    os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
    OsManager = getattr(os_process, "OsManager")
    os_autosar = ecuc_autosar_dict.get("Os", None)
    ecuc_autosar = ecuc_autosar_dict.get("EcuC", None)
    cfg_dict["rte"]["os_cfg"] = OsManager.parse_os_autosar(os_autosar, ecuc_autosar)
    cfg_dict["rte"]["isolate_cfg"] = __parse_isolate_autosar(ecuc_autosar_dict)
    __parse_rte_generation(ecuc_autosar_dict, cfg_dict["rte"])


def __parse_rte_generation(ecuc_autosar_dict, rte_cfg):
    rte_generation_dict = {
        "RteEaOptimization": False,
        "DataMappingGenerationOptimization1To1Rport": False,
        "DataMappingGenerationOptimizationNTo1Rport": False,
        "DataMappingGenerationOptimizationPport": False,
    }
    rte_cfg["RteGeneration"] = rte_generation_dict
    rte_autosar = ecuc_autosar_dict["Rte"]
    if not rte_autosar:
        return
    ecuc_rte = rte_autosar.find("/ActiveEcuC/Rte")
    if not ecuc_rte or not ecuc_rte.CONTAINERS or not ecuc_rte.CONTAINERS.ECUC_CONTAINER_VALUE:
        return
    for container_value in ecuc_rte.CONTAINERS.ECUC_CONTAINER_VALUE:
        if utils.get_definition_ref(container_value) == "/AUTOSAR/EcucDefs/Rte/RteGeneration":
            parameter_values = []
            parameter_values += container_value.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE
            parameter_values += container_value.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE
            for parameter_value in parameter_values:
                def_ref = utils.get_definition_ref(parameter_value)
                if def_ref.endswith("RteEaOptimization"):
                    rte_generation_dict["RteEaOptimization"] = utils.get_value(parameter_value) == "true"
                elif def_ref.endswith("DataMappingGenerationOptimization1To1Rport"):
                    rte_generation_dict["DataMappingGenerationOptimization1To1Rport"] = (
                        utils.get_value(parameter_value) == "true"
                    )
                elif def_ref.endswith("DataMappingGenerationOptimizationNTo1Rport"):
                    rte_generation_dict["DataMappingGenerationOptimizationNTo1Rport"] = (
                        utils.get_value(parameter_value) == "true"
                    )
                elif def_ref.endswith("DataMappingGenerationOptimizationPport"):
                    rte_generation_dict["DataMappingGenerationOptimizationPport"] = (
                        utils.get_value(parameter_value) == "true"
                    )
                elif def_ref.endswith("RteDevErrorDetect"):
                    rte_generation_dict["RteDevErrorDetect"] = utils.get_value(parameter_value) == "true"
                elif def_ref.endswith("RteIsrSimplification"):
                    rte_generation_dict["RteIsrSimplification"] = utils.get_value(parameter_value) == "true"
                elif def_ref.endswith("RteSystemSignalCompuMethodEna"):
                    rte_generation_dict["RteSystemSignalCompuMethodEna"] = utils.get_value(parameter_value) == "true"
            break


def get_parsered_swc_list(asw_autosar_dict):
    ar_asw = asw_autosar_dict.get("asw")
    return AutosarUtils.get_all_appl_component_short_names(ar_asw)


def __update_com_ecuc_notifications(cfg_dict, ecuc_autosar_dict):
    """com signal的Timeout和notification更新接口"""
    com_ecuc = ecuc_autosar_dict.get("Com", None)
    if com_ecuc is None or "rte" not in cfg_dict.keys():
        return
    com_ecuc_manager = LoadPlugIn.load_module("Com", "config_plug_in.update_ecuc.com_ecuc_manager")
    ComEcucManager = getattr(com_ecuc_manager, "ComEcucManager")
    SIGNAL_NOTIFICATION_DEFAULT_VALUE_LIST = getattr(com_ecuc_manager, "SIGNAL_NOTIFICATION_DEFAULT_VALUE_LIST")
    com_signal_default_values = set(SIGNAL_NOTIFICATION_DEFAULT_VALUE_LIST)
    com_ecuc_notifications = ComEcucManager.get_com_ecuc_notifications(com_ecuc)

    need_notifications_by_required_com_specs = (
        get_data_mapping_need_notifications_signals_by_sr_rport_required_com_specs(cfg_dict, com_signal_default_values)
    )
    _update_com_ecuc_signal_notifications(
        cfg_dict, com_ecuc, com_ecuc_notifications, need_notifications_by_required_com_specs, com_signal_default_values
    )
    _update_com_ecuc_signal_timeout(
        cfg_dict, com_ecuc, com_ecuc_notifications, need_notifications_by_required_com_specs, com_signal_default_values
    )
    _update_com_ecuc_signal_timeout_notifications(
        cfg_dict, com_ecuc, com_ecuc_notifications, need_notifications_by_required_com_specs, com_signal_default_values
    )


def _update_com_ecuc_signal_notifications(
    cfg_dict, com_ecuc, com_ecuc_notifications, need_notifications_by_required_com_specs, com_signal_default_values
):
    cross_partition_rx_signal_list = get_cross_partition_rx_signal_list(cfg_dict)
    rport_to_multiple_signals_list = get_rport_mapping_to_multiple_signals_list(cfg_dict)
    data_rx_event_list = cfg_dict.get("rte", {}).get("data_mapping_config", {}).get("data_received_event_list", [])
    data_rx_event_signal_list = [data_rx_event.get("port_name", "") for data_rx_event in data_rx_event_list]

    Optimization1To1Rport_signal_list, OptimizationNTo1Rport_signal_list = get_rport_Optimization_signals_list(cfg_dict)
    need_notification_rx_singals = set(
        cross_partition_rx_signal_list
        + data_rx_event_signal_list
        + rport_to_multiple_signals_list
        + Optimization1To1Rport_signal_list
        + OptimizationNTo1Rport_signal_list
        + need_notifications_by_required_com_specs.get("ComNotification", [])
    )
    com_notification_dict = com_ecuc_notifications.get("ComNotification", {})
    com_ecuc_manager = LoadPlugIn.load_module("Com", "config_plug_in.update_ecuc.com_ecuc_manager")
    ComEcucManager = getattr(com_ecuc_manager, "ComEcucManager")

    if len(need_notification_rx_singals) > 0:
        ComEcucManager.update_com_usercbk_headerfile(com_ecuc, "Rte_Cbk.h", "add")
    else:
        ComEcucManager.update_com_usercbk_headerfile(com_ecuc, "Rte_Cbk.h", "del")
    for need_notification_rx_singal in need_notification_rx_singals:
        # 更新ComNotification
        com_signal_name = f"{need_notification_rx_singal}_Rx"
        if com_signal_name in com_notification_dict:
            notification_containr = com_notification_dict[com_signal_name].get("notification_containr", None)
            notification_value = com_notification_dict[com_signal_name].get("notification_value", None)
            if notification_containr is None:
                continue
            _set_auto_derived_container_value(
                notification_containr,
                notification_value,
                com_signal_default_values,
                f"Rte_COMCbk_{need_notification_rx_singal}_Rx",
            )
            com_notification_dict.pop(com_signal_name, None)
        else:
            find_signal_container = com_ecuc.find(f"/ActiveEcuC/Com/ComConfig/{com_signal_name}")
            if find_signal_container is None:
                logger.warning(f"signal:{com_signal_name} not found!")
                continue
            _find_signal_value_container_and_set_value(
                find_signal_container, "ComNotification", f"Rte_COMCbk_{need_notification_rx_singal}_Rx"
            )
    for com_notification in com_notification_dict.values():
        # 清除不需要的ComNotification
        notification_containr = com_notification.get("notification_containr", None)
        _clear_auto_derived_container_value(notification_containr, "")


def _update_com_ecuc_signal_timeout_notifications(
    cfg_dict, com_ecuc, com_ecuc_notifications, need_notifications_by_required_com_specs, com_signal_default_values
):
    com_notification_dict = com_ecuc_notifications.get("ComTimeoutNotification", {})
    need_notification_rx_singals = set(need_notifications_by_required_com_specs.get("ComTimeoutNotification", []))
    for need_notification_rx_singal in need_notification_rx_singals:
        # 更新ComNotification
        com_signal_name = f"{need_notification_rx_singal}_Rx"
        if com_signal_name in com_notification_dict:
            notification_containr = com_notification_dict[com_signal_name].get("notification_containr", None)
            notification_value = com_notification_dict[com_signal_name].get("notification_value", None)
            if notification_containr is None:
                continue
            _set_auto_derived_container_value(
                notification_containr,
                notification_value,
                com_signal_default_values,
                f"Rte_COMCbkRxTOut_{need_notification_rx_singal}_Rx",
            )
            com_notification_dict.pop(com_signal_name, None)
        else:
            find_signal_container = com_ecuc.find(f"/ActiveEcuC/Com/ComConfig/{com_signal_name}")
            if find_signal_container is None:
                logger.warning(f"signal:{com_signal_name} not found!")
                continue
            _find_signal_value_container_and_set_value(
                find_signal_container, "ComTimeoutNotification", f"Rte_COMCbkRxTOut_{need_notification_rx_singal}_Rx"
            )
    for com_notification in com_notification_dict.values():
        # 清除不需要的ComNotification
        notification_containr = com_notification.get("notification_containr", None)
        _clear_auto_derived_container_value(notification_containr, "")


def _update_com_ecuc_signal_timeout(
    cfg_dict, com_ecuc, com_ecuc_notifications, need_notifications_by_required_com_specs, com_signal_default_values
):
    com_notification_dict = com_ecuc_notifications.get("ComTimeout", {})
    need_notification_rx_singals = need_notifications_by_required_com_specs.get("ComTimeout", {})
    for need_notification_rx_singal_dict in need_notification_rx_singals:
        # 更新ComNotification
        need_notification_rx_singal = need_notification_rx_singal_dict.get("signal", "")
        timeout_value = need_notification_rx_singal_dict.get("timeout", "0")
        com_signal_name = f"{need_notification_rx_singal}_Rx"
        if com_signal_name in com_notification_dict:
            notification_containr = com_notification_dict[com_signal_name].get("notification_containr", None)
            notification_value = com_notification_dict[com_signal_name].get("notification_value", None)
            if notification_containr is None:
                continue
            _set_auto_derived_container_value(
                notification_containr, notification_value, com_signal_default_values, timeout_value
            )
            com_notification_dict.pop(com_signal_name)
        else:
            find_signal_container = com_ecuc.find(f"/ActiveEcuC/Com/ComConfig/{com_signal_name}")
            if find_signal_container is None:
                logger.warning(f"signal:{com_signal_name} not found!")
                continue
            _find_signal_value_container_and_set_value(find_signal_container, "ComTimeout", timeout_value)
    for com_notification in com_notification_dict.values():
        # 清除不需要的ComNotification
        notification_containr = com_notification.get("notification_containr", None)
        _clear_auto_derived_container_value(notification_containr, "0")


def _set_auto_derived_container_value(value_containr, notification_value, com_signal_default_values, set_val=""):
    container_path = value_containr.get_path()
    def_ref = utils.get_definition_ref(value_containr).split("/")[-1]
    val_path = f"{container_path}/{def_ref}"
    if AutosarUtil.is_auto_derived(value_containr):
        if not AutosarUtil.is_user_defined(value_containr):
            utils.set_value(value_containr, set_val)
        else:
            logger.ui_warning(f"{val_path}: {set_val} update failed, because of user defined!")
    else:
        if not AutosarUtil.is_user_defined(value_containr):
            if notification_value in com_signal_default_values:
                utils.set_value(value_containr, set_val)
                AutosarUtil.add_annotation_value(value_containr, "AutoDerived")
            else:
                logger.ui_warning(f"{val_path}: {set_val} update failed, because of user defined!")


def _clear_auto_derived_container_value(value_containr, set_val=""):
    if value_containr is None:
        return
    if AutosarUtil.is_auto_derived(value_containr):
        AutosarUtil.remove_annotation_value(value_containr, "AutoDerived")
        if not AutosarUtil.is_user_defined(value_containr):
            utils.set_value(value_containr, set_val)


def _find_signal_value_container_and_set_value(container, definition, set_val):
    container_path = container.get_path()
    for textual_param in (
        container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE + container.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE
    ):
        if str(utils.get_definition_ref(textual_param)).split("/")[-1] != definition:
            continue
        val_path = f"{container_path}/{definition}"
        if AutosarUtil.is_user_defined(textual_param):
            logger.ui_warning(f"{val_path}: {set_val} update failed, because of user defined!")
            continue
        utils.set_value(textual_param, set_val)
        if not AutosarUtil.is_auto_derived(textual_param):
            AutosarUtil.add_annotation_value(textual_param, "AutoDerived")
        break


def get_data_mapping_need_notifications_signals_by_sr_rport_required_com_specs(cfg_dict, com_signal_default_values):
    """根据sr rport的required_com_specs配置推到出要生成notification、timeout和timeout notification的信号"""
    com_ecuc_notifications = {"ComNotification": [], "ComTimeout": [], "ComTimeoutNotification": []}
    for component in cfg_dict.get("rte", {}).get("asw_config", {}).values():
        for rport in component.get("rports", {}).values():
            if (
                rport.get("signal_category", None) not in ["Signal", "SignalGroup"]
                or rport.get("type", None) != "Explicit Receiver"
            ):
                continue
            required_com_specs = rport.get("required_com_specs", None)
            if required_com_specs is None:
                continue
            if (
                required_com_specs.get("enable_update", "false") == "true"
                or required_com_specs.get("handle_never_received", "false") == "true"
            ):
                com_ecuc_notifications["ComNotification"] += rport.get("mapping_to_signals", [])
            timeout = required_com_specs.get("alive_timeout", "0")
            if timeout not in com_signal_default_values:  # 有timeout时需要同时生成以下Notification
                com_ecuc_notifications["ComTimeout"] += list(
                    {"signal": signal, "timeout": timeout} for signal in rport.get("mapping_to_signals", [])
                )
                com_ecuc_notifications["ComTimeoutNotification"] += rport.get("mapping_to_signals", [])
                com_ecuc_notifications["ComNotification"] += rport.get("mapping_to_signals", [])
    return com_ecuc_notifications


def get_cross_partition_rx_signal_list(cfg_dict):
    cross_partition_rx_signal_list = []
    for swc_name, swc_info in cfg_dict.get("rte", {}).get("asw_config", {}).items():
        for rport_name, rport_info in swc_info.get("rports", {}).items():
            if rport_info.get("signal_category", None) in ["Signal", "SignalGroup"]:
                if rport_info.get("data_mapping_has_inter_osa_same_core", False) or rport_info.get(
                    "data_mapping_has_inter_core", False
                ):
                    cross_partition_rx_signal_list += rport_info.get("mapping_to_signals", [])
    return cross_partition_rx_signal_list


def get_rport_mapping_to_multiple_signals_list(cfg_dict):
    """得到多个接收signal mapping到同一个rport的list"""
    rv = []
    for component in cfg_dict.get("rte", {}).get("asw_config", {}).values():
        for rport in component.get("rports", {}).values():
            if (
                rport.get("signal_category", None) not in ["Signal", "SignalGroup"]
                or rport.get("type", None) != "Explicit Receiver"
            ):
                continue
            if len(rport["mapping_to_signals"]) > 1:
                rv += rport.get("mapping_to_signals", [])
    return rv


def _RPortIsNeedOptimization(port):
    return bool(port.get("data_mapping_buff", {}))


def get_rport_Optimization_signals_list(cfg_dict):
    Optimization1To1Rport_signal_list = []
    OptimizationNTo1Rport_signal_list = []
    OptimizationRport_signals = {}
    try:
        Optimization1To1Rport_flag = cfg_dict["rte"]["RteGeneration"]["DataMappingGenerationOptimization1To1Rport"]
        OptimizationNTo1Rport_flag = cfg_dict["rte"]["RteGeneration"]["DataMappingGenerationOptimizationNTo1Rport"]
    except Exception:
        Optimization1To1Rport_flag = False
        OptimizationNTo1Rport_flag = False
    if Optimization1To1Rport_flag or OptimizationNTo1Rport_flag:
        for swc_name, swc_info in cfg_dict.get("rte", {}).get("asw_config", {}).items():
            for rport_name, rport_info in swc_info.get("rports", {}).items():
                if rport_info.get("signal_category", None) == "Signal":
                    if not (
                        rport_info.get("data_mapping_has_inter_osa_same_core", False)
                        or rport_info.get("data_mapping_has_inter_core", False)
                    ):
                        signals = rport_info.get("mapping_to_signals", [])
                        if len(signals) == 1:
                            for signal in signals:
                                if signal in OptimizationRport_signals.keys():
                                    OptimizationRport_signals[signal].append(rport_info)
                                else:
                                    OptimizationRport_signals[signal] = [rport_info]
                    else:
                        signals = rport_info.get("mapping_to_signals", [])
                        for signal in signals:
                            if signal in OptimizationRport_signals.keys():
                                OptimizationRport_signals[signal].append("")
    for signal in OptimizationRport_signals.keys():
        if len(OptimizationRport_signals[signal]) == 1:
            if Optimization1To1Rport_flag and _RPortIsNeedOptimization(OptimizationRport_signals[signal][0]):
                Optimization1To1Rport_signal_list.append(signal)
        elif len(OptimizationRport_signals[signal]) > 1:
            if OptimizationNTo1Rport_flag:
                OptimizationNTo1Rport_signal_list.append(signal)
    return Optimization1To1Rport_signal_list, OptimizationNTo1Rport_signal_list


EVENT_TYPE = {
    "INIT-EVENT": "InitEvent",
    "TIMING-EVENT": "TimingEvent",
    "BSW-TIMING-EVENT": "TimingEvent",
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


def get_task_mappings_info(asw_autosar, ib_autosar_dict, ecuc_autosar_dict: dict) -> dict:
    rte_autosar = ecuc_autosar_dict.get("Rte", None)
    os_autosar = ecuc_autosar_dict.get("Os", None)
    ecuc_autosar = ecuc_autosar_dict.get("EcuC", None)
    if asw_autosar is None:
        logger.warning("Please import ASW.arxml!")
    if os_autosar is None:
        logger.error("Not Found Os module!")
        return {}

    os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
    OsManager = getattr(os_process, "OsManager")
    os_cfg = OsManager.parse_os_autosar(os_autosar, ecuc_autosar)
    rte_cfg = parse_rte_autosar(rte_autosar, asw_autosar, ib_autosar_dict, os_cfg)

    task_mappings_info = {}
    task_application_info = get_task_application_info(os_cfg)
    for _, config in rte_cfg.items():
        for mapping_config in config["task_mapping"].values():
            task_name = mapping_config["MappedToTask"]
            task_info = get_task_info(os_cfg, task_application_info, task_name)
            if not task_info:
                return task_mappings_info
            alarm_info = get_task_binding_alarm_info(os_cfg, mapping_config)
            schedulable_entity_info = get_task_binding_schedulable_entity_info(config["exclusive_area"], mapping_config)
            schedulable_entity_info["is_bsw"] = config["is_bsw"]
            if task_name not in task_mappings_info:
                task_mapping = dict.fromkeys(
                    [
                        "core_id",
                        "task_type",
                        "task_schedule",
                        "task_priority",
                        "schedulable_entity_info_list",
                        "alarm_info_list",
                    ]
                )
                task_mapping.update(task_info)
                task_mapping["schedulable_entity_info_list"] = []
                task_mapping["alarm_info_list"] = []
                task_mappings_info[task_name] = task_mapping
            task_mapping = task_mappings_info[task_name]
            task_mapping["schedulable_entity_info_list"].append(schedulable_entity_info)
            task_mapping["alarm_info_list"].append(alarm_info)
    # The placeholder ensures that the application file can be generated
    add_auto_start_task(task_mappings_info, os_cfg)
    task_names = update_task_mapping_sch_tbl_list(
        task_mappings_info, asw_autosar, os_autosar, rte_autosar, ib_autosar_dict
    )
    add_schedule_table_for_basic_task(task_mappings_info, task_names)
    return task_mappings_info


def parse_rte_autosar(rte_autosar, asw_autosar, bsw_autosar, os_cfg):
    rte_cfg = {}
    rte = rte_autosar.find("/ActiveEcuC/Rte")
    for container_value in rte.CONTAINERS.ECUC_CONTAINER_VALUE:
        name = utils.get_short_name(container_value)
        def_ref = utils.get_definition_ref(container_value)
        if def_ref.endswith("RteBswModuleInstance"):
            rte_cfg[name] = get_rte_cfg(container_value, bsw_autosar, "RteBsw", os_cfg)
        elif def_ref.endswith("RteSwComponentInstance"):
            rte_cfg[name] = get_rte_cfg(container_value, asw_autosar, "Rte", os_cfg)
    return rte_cfg


def __parse_isolate_autosar(module_config):
    isolate_cfg = {"module": {}, "iso_func": {}}
    isolate_autosar = module_config.get("Isolate", None)
    if not isolate_autosar:
        return isolate_cfg

    for container in isolate_autosar.find("/ActiveEcuC/Isolate").CONTAINERS.ECUC_CONTAINER_VALUE:
        mod_name = utils.get_short_name(container)
        def_ref = utils.get_definition_ref(container)
        if not def_ref.endswith("Module"):
            continue
        if not container.SUB_CONTAINERS:
            continue
        if not container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
            continue

        osa_name = None
        for ref in container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
            if utils.get_definition_ref(ref).endswith("OsApplicationRef"):
                try:
                    osa_name = (utils.get_value_ref(ref) or "").split("/")[-1]
                except Exception:
                    pass
                break
        if not osa_name:
            continue

        isolate_cfg["module"][mod_name] = []
        for sub_container in container.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
            iso_func = {
                "name": utils.get_short_name(sub_container),
                "module": mod_name,
                "osa": osa_name,
                "header_file_name": f"{mod_name}_{osa_name}_PPCFunction.h",
            }
            if iso_func["name"] in isolate_cfg["iso_func"]:
                continue
            isolate_cfg["module"][mod_name].append(iso_func)
            isolate_cfg["iso_func"][iso_func["name"]] = iso_func

    return isolate_cfg


def __update_task_mapping_info(task_mappings_info, asw_config):
    for task_name, mapping_info in task_mappings_info.items():
        if "cs_alarm_info_list" not in mapping_info:
            mapping_info["cs_alarm_info_list"] = []
            mapping_info["cs_event_info_list"] = []
        removed_schedulable_entity_infos = []
        removed_alarm_info_list = []
        service_runnable_infos = {}
        for name, component in asw_config.items():
            if name not in service_runnable_infos:
                service_runnable_infos[name] = {}
            for pport in component["pports"].values():
                if pport["type"] == "Server":
                    if not pport["connected_ports"]:
                        continue
                    service_runnable_infos[name][pport["runnable"]] = pport

        for i, schedulable_entity_info in enumerate(mapping_info["schedulable_entity_info_list"]):
            if schedulable_entity_info["event_type"] == "OperationInvokedEvent":
                name = schedulable_entity_info["name"]
                component = schedulable_entity_info["component"]
                # 检查service名称是否存在asw中service port一致
                if name not in service_runnable_infos[component]:
                    removed_schedulable_entity_infos.append(schedulable_entity_info)
                    removed_alarm_info_list.append(i)
                    logger.warning(f"service runnable name:{name} is different from service port name")
                    continue
                pport_names = service_runnable_infos[component][name]
                pport_name = pport_names["name"]
                pport = asw_config[component]["pports"][pport_name]
                connected_ports = pport.get("connected_ports", {})
                if not connected_ports:
                    continue
                if connected_ports["category"] == "1:1":
                    rport = connected_ports["ports"][0]
                    rport = asw_config[rport["component"]]["rports"][rport["name"]]
                    # Direct call不需要映射代码生成，故移除
                    if not rport["ioc"]:
                        removed_schedulable_entity_infos.append(schedulable_entity_info)
                        removed_alarm_info_list.append(i)
                        continue
                    if not rport["task"]:
                        continue
                    timeout = int(rport["timeout"])
                    for task_name in set(rport["task"]):
                        if "cs_event_info_list" not in task_mappings_info[task_name]:
                            task_mappings_info[task_name]["cs_event_info_list"] = []
                        if timeout > 0:
                            alarm_info = {}
                            alarm_info["task_name"] = task_name
                            alarm_info["alarm_action_type"] = "set_event"
                            alarm_info["alarm_name"] = f"Rte_Al_Timeout_{task_name}"
                            alarm_info["alarm_action"] = f"Rte_Ev_Timeout_{task_name}"
                            mapping_info["cs_alarm_info_list"].append(alarm_info)
                            task_mappings_info[task_name]["cs_event_info_list"].append(f"Rte_Ev_Timeout_{task_name}")
                    task_mappings_info[task_name]["cs_event_info_list"].append(f"Rte_Ev_WaitPoint_{task_name}")
                elif connected_ports["category"] == "1:N":
                    # Direct call不需要映射代码生成，故移除
                    if not pport["ioc"]:
                        removed_schedulable_entity_infos.append(schedulable_entity_info)
                        removed_alarm_info_list.append(i)
                        continue

        removed_alarm_info_list.reverse()
        for i, schedulable_entity_info in enumerate(removed_schedulable_entity_infos):
            mapping_info["schedulable_entity_info_list"].remove(schedulable_entity_info)
            mapping_info["alarm_info_list"].pop(removed_alarm_info_list[i])


def get_rte_cfg(container_value, autosar, perfix, os_cfg):
    if container_value.SUB_CONTAINERS is None:
        return None
    rte_cfg = {}
    rte_cfg["task_mapping"] = {}
    rte_cfg["exclusive_area"] = {}
    if perfix == "Rte":
        rte_cfg["is_bsw"] = False
        exclusive_area_tag = "RteExclusiveAreaImplementation"
    else:
        rte_cfg["is_bsw"] = True
        exclusive_area_tag = "RteBswExclusiveAreaImpl"
    for container_value in container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
        def_name = utils.get_definition_ref(container_value)
        values = []
        values += container_value.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE
        values += container_value.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE
        values += container_value.REFERENCE_VALUES.ECUC_REFERENCE_VALUE
        if def_name.endswith(f"{perfix}EventToTaskMapping"):
            mapping_name = utils.get_short_name(container_value)
            mapping_cfg = {}
            mapping_cfg["ActivationOffset"] = 0
            mapping_cfg["Event"] = {}
            mapping_cfg["Event"]["EventType"] = None
            for value in values:
                value_type = utils.get_definition_ref(value)
                if value_type.endswith(f"{perfix}ActivationOffset"):
                    offset = utils.get_value(value)
                    if not offset:
                        offset = 0
                    mapping_cfg["ActivationOffset"] = offset
                elif value_type.endswith(f"{perfix}PositionInTask"):
                    mapping_cfg["PositionInTask"] = int(utils.get_value(value) or 0)
                elif value_type.endswith(f"{perfix}EventRef"):
                    ref = utils.get_value_ref(value) or ""
                    module = ref.split("/")[-3]
                    event = None
                    if rte_cfg["is_bsw"] and module in autosar:
                        event = autosar[module].find(ref)
                    elif not rte_cfg["is_bsw"] and autosar:
                        event = autosar.find(ref)
                    if event is None:
                        logger.error(f"EventRef: {ref} is wrong!")
                        continue
                    event_cfg = mapping_cfg["Event"]
                    event_cfg["EventRef"] = ref
                    event_cfg["EventType"] = EVENT_TYPE.get(event.get_tag())
                    if event_cfg["EventType"] is None:
                        logger.warning(f"Event {event.get_tag()} not supported!")
                        continue
                    activation_reason = None
                    activation_reason_ref = utils.get_activation_reason_representation_ref(event)
                    if activation_reason_ref:
                        _activation_reason = event.find(activation_reason_ref)
                        activation_reason = {}
                        activation_reason["Name"] = utils.get_symbol(_activation_reason) or utils.get_short_name(
                            _activation_reason
                        )
                        activation_reason["BitPosition"] = utils.get_bit_position(_activation_reason)
                        event_cfg["ActivationReason"] = activation_reason
                    if event_cfg["EventType"] == "SwcModeSwitchEvent":
                        event_cfg["TriggerCategory"] = event.ACTIVATION.valueOf_
                        mode_iref = event.MODE_IREFS.MODE_IREF[0]
                        port = ".".join(mode_iref.CONTEXT_PORT_REF.valueOf_.split("/")[-2:])
                        group = mode_iref.CONTEXT_MODE_DECLARATION_GROUP_PROTOTYPE_REF.valueOf_.split("/").pop()
                        event_cfg["TriggerCondition"] = f"{port}.{group}"
                    period = event.PERIOD.valueOf_ if hasattr(event, "PERIOD") and event.PERIOD else None
                    if event_cfg["EventType"] == "TimingEvent" and period in (None, 0):
                        logger.error(f"{ref} period error!")
                    event_cfg["Period"] = str(Decimal(str(period)) * 1000) if period else None
                    event_cfg["ExclusiveArea"] = []
                    if rte_cfg["is_bsw"]:
                        starts_on_event_ref = utils.get_starts_on_event_ref(event)
                        schedulable_entity = event.find(starts_on_event_ref)
                        implemented_entry_ref = utils.get_implemented_entry_ref(schedulable_entity)
                        module_entry = event.find(implemented_entry_ref)
                        event_cfg["Component"] = starts_on_event_ref.split("/")[-3]
                        event_cfg["RunnableName"] = utils.get_short_name(module_entry)
                    else:
                        start_on_event_ref = event.START_ON_EVENT_REF.valueOf_
                        runnable = event.find(start_on_event_ref)
                        event_cfg["Component"] = start_on_event_ref.split("/")[-3]
                        event_cfg["RunnableName"] = (
                            runnable.SYMBOL.valueOf_ if runnable.SYMBOL else utils.get_short_name(runnable)
                        )
                        ea_refs = event_cfg["ExclusiveArea"]
                        if runnable.CAN_ENTER_EXCLUSIVE_AREA_REFS:
                            for ea_ref in runnable.CAN_ENTER_EXCLUSIVE_AREA_REFS.CAN_ENTER_EXCLUSIVE_AREA_REF:
                                ea_name = ea_ref.valueOf_.split("/").pop()
                                ea_ref_value = ea_ref.valueOf_
                                ea_ref = {}
                                ea_ref["Name"] = ea_name
                                ea_ref["AccessMode"] = "CAN_ENTER"
                                ea_ref["SwcOrModuleName"] = (
                                    ea_ref_value.split("/")[-3]
                                    if ea_ref_value and len(ea_ref_value.split("/")) > 3
                                    else ""
                                )
                                ea_refs.append(ea_ref)
                        if runnable.RUNS_INSIDE_EXCLUSIVE_AREA_REFS:
                            for ea_ref in runnable.RUNS_INSIDE_EXCLUSIVE_AREA_REFS.RUNS_INSIDE_EXCLUSIVE_AREA_REF:
                                ea_name = ea_ref.valueOf_.split("/").pop()
                                ea_ref_value = ea_ref.valueOf_
                                ea_ref = {}
                                ea_ref["Name"] = ea_name
                                ea_ref["AccessMode"] = "RUNS_INSIDE"
                                ea_ref["SwcOrModuleName"] = (
                                    ea_ref_value.split("/")[-3]
                                    if ea_ref_value and len(ea_ref_value.split("/")) > 3
                                    else ""
                                )
                                ea_refs.append(ea_ref)
                    event_cfg["mode_disabling_info"] = __parse_mode_disabling_info(event, event_cfg["RunnableName"])
                elif value_type.endswith(f"{perfix}MappedToTaskRef"):
                    mapping_cfg["MappedToTask"] = (utils.get_value_ref(value) or "").split("/").pop()
                    mapping_cfg["osa"] = os_cfg["OsTasks"].get(mapping_cfg["MappedToTask"], {}).get("osa")
                elif value_type.endswith(f"{perfix}UsedOsAlarmRef"):
                    used_os_alarm = utils.get_value_ref(value)
                    if used_os_alarm:
                        mapping_cfg["UsedOsAlarm"] = used_os_alarm.split("/").pop()
                    else:
                        mapping_cfg["UsedOsAlarm"] = None
                elif value_type.endswith(f"{perfix}UsedOsEventRef"):
                    used_os_event = utils.get_value_ref(value)
                    if used_os_event:
                        mapping_cfg["UsedOsEvent"] = used_os_event.split("/").pop()
                    else:
                        mapping_cfg["UsedOsEvent"] = None
            if "Period" not in mapping_cfg["Event"]:
                continue
            if "mode_disabling_info" in mapping_cfg["Event"] and mapping_cfg["Event"]["mode_disabling_info"]:
                for info in mapping_cfg["Event"]["mode_disabling_info"]:
                    info["osa"] = mapping_cfg["osa"]
            rte_cfg["task_mapping"][mapping_name] = mapping_cfg
        elif def_name.endswith(exclusive_area_tag):
            exclusive_area_name = utils.get_short_name(container_value)
            exclusive_area_cfg = {}
            for value in values:
                value_type = utils.get_definition_ref(value)
                if value_type.endswith("RteExclusiveAreaImplMechanism"):
                    exclusive_area_cfg["ExclusiveAreaImplMechanism"] = utils.get_value(value)
                elif value_type.endswith("ExclusiveAreaRef"):
                    exclusive_area_cfg["ExclusiveAreaRef"] = utils.get_value_ref(value)
            rte_cfg["exclusive_area"][exclusive_area_name] = exclusive_area_cfg
    return rte_cfg


def __parse_mode_disabling_info(event, run_name):
    mode_disabling_info = []
    if not hasattr(event, "DISABLED_MODE_IREFS"):
        return mode_disabling_info
    refs = event.DISABLED_MODE_IREFS
    if refs and refs.DISABLED_MODE_IREF:
        for ref in refs.DISABLED_MODE_IREF:
            rport_path = ref.CONTEXT_PORT_REF.valueOf_
            if not rport_path:
                continue
            mdgp_path = ref.CONTEXT_MODE_DECLARATION_GROUP_PROTOTYPE_REF.valueOf_
            if not mdgp_path:
                continue
            target_mode_path = ref.TARGET_MODE_DECLARATION_REF.valueOf_
            if not target_mode_path:
                continue
            info = {}
            info["rport_path"] = rport_path
            rport_path_split = rport_path.split("/")
            info["rport"] = rport_path_split[-1]
            info["swc"] = rport_path_split[-2]
            info["event"] = utils.get_short_name(event)
            info["runnable"] = run_name
            info["mdgp_path"] = mdgp_path
            info["mdgp"] = mdgp_path.split("/")[-1]
            info["mode_path"] = target_mode_path
            info["mode"] = target_mode_path.split("/")[-1]
            info["swc_run"] = f"{info['swc']}_{run_name}"
            info["key"] = f"{info['swc']}_{info['rport']}_{info['mdgp']}"
            mode_disabling_info.append(info)
    return mode_disabling_info


def add_auto_start_task(task_mappings_info, os_config):
    for appl_name, appl_cfg in os_config["OsApplications"].items():
        core_id = appl_cfg.get("CoreId", "0")
        task_name = f"{appl_name}PlaceholderInitTask"
        task_mappings_info[task_name] = {
            "core_id": core_id,
            "task_type": "BASIC",
            "task_schedule": "FULL",
            "task_priority": "0",
            "application": appl_name,
            "task_autostart": "TRUE",
            "schedulable_entity_info_list": [],
            "alarm_info_list": [],
            "os_counter": {},
        }


def add_schedule_table_for_basic_task(task_mappings_info, task_set):
    for task_name, mapping_cfg in task_mappings_info.items():
        if "schedule_table_list" not in mapping_cfg:
            mapping_cfg["schedule_table_list"] = []
        if task_name in task_set:
            continue
        if mapping_cfg["task_type"] != "BASIC":
            continue
        if not mapping_cfg["schedulable_entity_info_list"]:
            continue

        timing_offset_dict = {}
        for schedulable_entity_info in mapping_cfg["schedulable_entity_info_list"]:
            if schedulable_entity_info["event_type"] != "TimingEvent":
                continue
            timing_offset_dict.update({schedulable_entity_info["period"]: schedulable_entity_info["original_offset"]})

        init_schedule_table_cfg, main_schedule_table_cfg = BasicTaskScheduleTableManager.get_schedule_table_cfg(
            timing_offset_dict, task_name
        )
        if init_schedule_table_cfg:
            mapping_cfg["schedule_table_list"].append(init_schedule_table_cfg)

        if main_schedule_table_cfg:
            mapping_cfg["schedule_table_list"].append(main_schedule_table_cfg)

        if mapping_cfg["schedule_table_list"]:
            mapping_cfg["has_unique_sch_tbl"] = True


def get_task_application_info(os_config: dict) -> dict:
    task_appl_info = {}
    for appl_name, appl_cfg in os_config["OsApplications"].items():
        core_id = appl_cfg["CoreId"]
        counter_info = appl_cfg["OsAppCounter"]
        for task_name in appl_cfg["OsAppTaskRef"]:
            task_appl_info[task_name] = {"appl_name": appl_name, "core_id": core_id, "os_counter": counter_info}
    return task_appl_info


def get_task_info(os_config, task_application_info, task_name: str) -> dict:
    """
    Get task information in Workspace through task reference.

    Arg:
      os_config:  Configuration parsed from Os ecuc.
      task_name: Name of mapped task.

    Return:
      Returns a dictionary of task information.
      {
        "core_id": 0,
        "task_type": "AUTO" or "BASIC" or "EXTENDED",
        "task_schedule": "FULL",
        "task_priority": 0
      }
    """
    task_info_dict = dict.fromkeys(
        ["application", "core_id", "task_type", "task_schedule", "task_priority", "task_autostart", "os_counter"]
    )
    task_info = os_config["OsTasks"].get(task_name)
    if task_info is None:
        logger.ui_error(f"OsTask <{task_name}> is not configured!")
        return {}
    if task_name not in task_application_info:
        logger.ui_warning(f"Task <{task_name}> is not mapped to any application!")
        return {}
    task_info_dict["core_id"] = task_application_info[task_name]["core_id"]
    task_info_dict["task_type"] = task_info["OsTaskType"]
    task_info_dict["task_schedule"] = task_info["OsTaskSchedule"]
    task_info_dict["task_priority"] = task_info["OsTaskPriority"]
    task_info_dict["task_autostart"] = task_info["OsTaskAutostart"]
    task_info_dict["application"] = task_application_info[task_name]["appl_name"]
    task_info_dict["os_counter"] = task_application_info[task_name]["os_counter"]

    return task_info_dict


def get_task_binding_alarm_info(os_config: dict, mapping_config: dict) -> Optional[dict]:
    """
    Get task binding schedulable entity information..

    Arg:

    Return:
      Returns a dictionary of task binding alarm information.
      alarm_info: {
        "task_name": "<TaskName>",
        "alarm_name": "Rte_Al_TE_<SwcName>_<RunnableName>",
        "alarm_action_type": "set_event" or "activate_task",
        "alarm_action": "Rte_Ev_Run_<SwcName>_<RunnableName>" or "Rte_Ev_Cyclic<sequence>_<TaskName>_0_<period>ms",
    }
    """
    if mapping_config["Event"]["EventType"] != "TimingEvent":
        return None
    alarm_info = dict.fromkeys(["task_name", "alarm_name", "alarm_action_type", "alarm_action"])
    task_name = mapping_config["MappedToTask"]
    alarm_info["task_name"] = task_name
    task = os_config["OsTasks"].get(task_name)
    if task["OsTaskType"] == "BASIC":
        alarm_info["alarm_action_type"] = "activate_task"
    elif task["OsTaskType"] == "EXTENDED":
        alarm_info["alarm_action_type"] = "set_event"
    alarm_info["alarm_name"] = mapping_config["UsedOsAlarm"]
    alarm_info["alarm_action"] = mapping_config["UsedOsEvent"]
    if not alarm_info["alarm_name"]:
        return None
    else:
        return alarm_info


def get_task_binding_schedulable_entity_info(exclusive_area_dict, mapping_config: dict) -> dict:
    """
    Get task binding schedulable entity information.

    Arg:

    Return:
      Returns a dictionary of schedulable entity information.
      schedulable_entity_info: {
        "name": "schedulable_entity_name",
        "offset": "20",
        "period": "10",
        "position_in_task": 1,
        "event_mask": "event_mask_str",
        "event_type": "event_type_str",
        "exclusive_areas": [{
          "name": "ExclusiveArea",
          "implementation": "OS_INTERRUPT_BLOCKING",
          "access_mode": "CAN_ENTER"
        }]
      }
    """
    schedulable_entity_info = dict.fromkeys(["name", "period", "position_in_task", "event_mask", "event_type"])
    task_name = mapping_config["MappedToTask"]
    if "RunnableName" in mapping_config["Event"]:
        schedulable_entity_info["name"] = mapping_config["Event"]["RunnableName"]
    elif "RunnableName" not in mapping_config["Event"]:
        logger.error(f"{mapping_config} is failed")

    if "Component" in mapping_config["Event"]:
        schedulable_entity_info["component"] = mapping_config["Event"]["Component"]
    elif "Component" not in mapping_config["Event"]:
        logger.error(f"{mapping_config} is failed")

    schedulable_entity_info["task_name"] = task_name
    schedulable_entity_info["position_in_task"] = mapping_config["PositionInTask"]

    eas = []
    if "ExclusiveArea" in mapping_config["Event"]:
        eas = mapping_config["Event"]["ExclusiveArea"]
    elif "ExclusiveArea" not in mapping_config["Event"]:
        logger.error(f"{mapping_config} is failed")

    exclusive_areas = []

    if len(eas) != 0:
        for ea in eas:
            exclusive_area = {}
            exclusive_area["name"] = ea["Name"]
            exclusive_area["implementation"] = exclusive_area_dict[ea["Name"]]["ExclusiveAreaImplMechanism"]
            exclusive_area["access_mode"] = ea["AccessMode"]
            exclusive_area["swc_or_module_name"] = ea["SwcOrModuleName"]
            exclusive_areas.append(exclusive_area)
    offset = float(mapping_config["ActivationOffset"])
    if mapping_config["Event"]["Period"] is None:
        period = None
        offset = None
    else:
        period = Decimal(mapping_config["Event"]["Period"])
        mapping_config["UsedOsEvent"]
        # NOTE:OS组的对offset为零时的要求
        if offset == 0:
            offset = min(20, period)
        elif offset > period:
            logger.warning(f"The offset value {offset} should not be greater than period value {period}")
    activation_reason = mapping_config["Event"].get("ActivationReason")
    if activation_reason:
        schedulable_entity_info["activation_reason"] = {}
        schedulable_entity_info["activation_reason"]["name"] = activation_reason["Name"]
        schedulable_entity_info["activation_reason"]["bit_position"] = activation_reason["BitPosition"]
    schedulable_entity_info["exclusive_areas"] = exclusive_areas
    schedulable_entity_info["offset"] = offset
    schedulable_entity_info["period"] = period
    schedulable_entity_info["original_offset"] = float(mapping_config["ActivationOffset"])
    schedulable_entity_info["event_ref"] = mapping_config["Event"]["EventRef"]
    schedulable_entity_info["event_type"] = mapping_config["Event"]["EventType"]
    schedulable_entity_info["event_mask"] = mapping_config["UsedOsEvent"]
    schedulable_entity_info["mode_disabling_info"] = (
        mapping_config["Event"]["mode_disabling_info"] if "mode_disabling_info" in mapping_config["Event"] else []
    )
    return schedulable_entity_info


def update_task_mapping_sch_tbl_list(
    task_mappings_info, asw_autosar, os_autosar, rte_autosar, internal_behavior_autosar_dict
):
    os_sch_tbl_cfgs = ScheduleTableManager.re_reasoning_all(
        os_autosar, rte_autosar, asw_autosar, internal_behavior_autosar_dict
    )
    sch_tbl_ui_cfg_list = ScheduleTableManager.convert_os_sch_tbl_cfg_to_ui(os_sch_tbl_cfgs)
    sch_tbl_cfgs = ScheduleTableManager.reasoning_all(
        sch_tbl_ui_cfg_list, os_autosar, rte_autosar, asw_autosar, internal_behavior_autosar_dict
    )
    os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
    OsManager = getattr(os_process, "OsManager")
    for sch_tbl_cfg in sch_tbl_cfgs:
        init_sch_tbl_cfg = sch_tbl_cfg["init"]
        main_sch_tbl_cfg = sch_tbl_cfg["main"]
        if "counter_ref" not in main_sch_tbl_cfg:
            continue
        counter_info = OsManager.get_counter_info(os_autosar, main_sch_tbl_cfg["counter_ref"])
        task_names = set()
        task_names.update(ScheduleTableManager.get_sch_tbl_task_name_set(init_sch_tbl_cfg))
        task_names.update(ScheduleTableManager.get_sch_tbl_task_name_set(main_sch_tbl_cfg))
        os_seconds_per_tick = counter_info.get("OsSecondsPerTick")
        if not os_seconds_per_tick:
            continue
        ScheduleTableManager.convert_sch_tbl_tick_to_milliseconds(init_sch_tbl_cfg, os_seconds_per_tick)
        ScheduleTableManager.convert_sch_tbl_tick_to_milliseconds(main_sch_tbl_cfg, os_seconds_per_tick)
        mapping_cfg = {}
        for task_name in sorted(task_names):
            mapping_cfg = task_mappings_info[task_name]
            schedule_table_list = [get_task_sch_tbl_cfg(main_sch_tbl_cfg, task_name)]
            if "counter_ref" in init_sch_tbl_cfg:
                schedule_table_list.append(get_task_sch_tbl_cfg(init_sch_tbl_cfg, task_name))
            mapping_cfg["has_unique_sch_tbl"] = False
            mapping_cfg["schedule_table_list"] = schedule_table_list
        mapping_cfg["has_unique_sch_tbl"] = True
    all_task_names = {task_name for cfg in sch_tbl_ui_cfg_list for task_name in cfg["task_offset_table"]}
    return all_task_names


def get_task_sch_tbl_cfg(sch_tbl_cfg, task_name):
    sch_tbl_cfg_copy = sch_tbl_cfg.copy()
    step_dict = {}
    for i, step_infos in sch_tbl_cfg_copy["step_dict"].items():
        task_step_info = [period for period, step_info in step_infos.items() if step_info["task_name"] == task_name]
        step_dict[i] = task_step_info
    sch_tbl_cfg_copy["step_dict"] = step_dict
    return sch_tbl_cfg_copy


def get_vfb_trace_functions(ecuc_autosar_dict) -> list:
    """
    get configured vfbTraceFunction values
    """
    config_value_list = []
    if not ecuc_autosar_dict:
        return config_value_list
    autosar_module_ecuc_obj = ecuc_autosar_dict.get("Rte", None)
    if not autosar_module_ecuc_obj:
        return config_value_list
    container_obj = autosar_module_ecuc_obj.find("/ActiveEcuC/Rte/RteGeneration")
    for param_value_obj in getattr(getattr(container_obj, "PARAMETER_VALUES"), "ECUC_TEXTUAL_PARAM_VALUE", []):
        if utils.get_definition_ref(param_value_obj) == "/AUTOSAR/EcucDefs/Rte/RteGeneration/RteVfbTraceFunction":
            value = utils.get_value(param_value_obj)
            config_value_list.append(value)
    return config_value_list


def get_all_vfb_trace_function_postfix(runnable_data):
    trace_function_postfix_set = {}
    for _, runnable_type_kind_dict in runnable_data.items():
        for _, swc_or_module_info_dict in runnable_type_kind_dict.items():
            for _, runnable_info_dict in swc_or_module_info_dict.items():
                component = runnable_info_dict.get("Component", "")
                runnable_name = runnable_info_dict.get("RunnableName", "")
                postfix = f"{component}_{runnable_name}"
                trace_function_postfix_set[postfix] = runnable_name

    return trace_function_postfix_set


def filter_duplicate_and_get_measurement_id(runnable_name_dict: dict):
    # filter duplicate hooks
    for runnable_name, hook_dict in runnable_name_dict.items():
        start_list, end_list = [], []
        hook_list = hook_dict.get("hook_list", [])
        if len(hook_list) <= 1:
            continue
        for hook_name in hook_list:
            if hook_name and hook_name.endswith("_Start"):
                start_list.append(hook_name)
            elif hook_name and hook_name.endswith("_Return"):
                end_list.append(hook_name)
        start_list = sorted(start_list)
        end_list = sorted(end_list)
        hook_dict["hook_list"] = []
        if start_list:
            hook_dict["hook_list"].append(start_list[0])
        if end_list:
            hook_dict["hook_list"].append(end_list[0])

        for hook_name in hook_dict["hook_list"]:
            if hook_name.endswith("_Return"):
                hook_prefix = hook_name[0 : -len("_Return")]
            else:
                hook_prefix = hook_name[0 : -len("_Start")]
            hook_dict["measurement_id"] = f"RtmConf_RtmMeasurementPoint_{hook_prefix}"
            break


def parse_task_info(runnable_name_dict: dict, task_mappings_info):
    if not task_mappings_info or not runnable_name_dict or not isinstance(task_mappings_info, dict):
        return
    for task_name, info_dict in task_mappings_info.items():
        core_id = info_dict.get("core_id", "")
        for schedulable_entity_info in info_dict.get("schedulable_entity_info_list", []):
            runnable_name = schedulable_entity_info.get("name", "")
            if runnable_name not in runnable_name_dict.keys():
                continue
            period = schedulable_entity_info.get("period", "")
            runnable_name_dict[runnable_name]["task_info"].append(
                {"core_id": core_id, "mapped_task": task_name, "period": period if period is not None else ""}
            )


def get_vfb_trace_info(ecuc_autosar_dict, all_runnable_info_dict, task_mappings_info=None):
    configured_value_list = get_vfb_trace_functions(ecuc_autosar_dict)
    component_info_dict = {}
    if configured_value_list:
        component_info_dict = get_all_vfb_trace_function_postfix(all_runnable_info_dict)
    runnable_name_dict = {}

    HOOK_NAME_MIN_LENGTH = 5
    # get runnable name Rte_Runnable_{module_name}_{runnable_name}_start/return
    for configured_value in configured_value_list:
        if not configured_value or not isinstance(configured_value, str):
            continue
        name_list = configured_value.split("_")
        if len(name_list) < HOOK_NAME_MIN_LENGTH:
            continue
        postfix = "_".join(name_list[2:-1])
        if postfix not in component_info_dict.keys():
            continue
        runnable_name = component_info_dict[postfix]
        if runnable_name not in runnable_name_dict.keys():
            runnable_name_dict[runnable_name] = {"hook_list": [], "task_info": []}
        runnable_name_dict[runnable_name]["hook_list"].append(configured_value)

    filter_duplicate_and_get_measurement_id(runnable_name_dict)
    parse_task_info(runnable_name_dict, task_mappings_info)

    return runnable_name_dict
