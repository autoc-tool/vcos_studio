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
Exclusive Areas解析模块

提供validation前的EA更新

"""

import os
from func_module.health_monitor.logger import logger
from basic_func_module.autosar_utils.utils import (
    get_short_name,
    get_definition_ref,
    get_value,
    set_value,
    set_value_ref,
    get_value_ref,
)
from basic_func_module.autosar_utils.autosar_util import AutosarUtil

CUR_FILE_PATH = os.path.dirname(__file__)

RUNS_INSIDE = "RUNS-INSIDE"
CAN_ENTER = "CAN-ENTER"
EXCLUSIVE_AREA_TYPE = {
    RUNS_INSIDE: "RUNS-INSIDE-EXCLUSIVE-AREA-REF",
    CAN_ENTER: "CAN-ENTER-EXCLUSIVE-AREA-REF",
}

RTE_SW_COMPONENTINSTANCE_DEF_REF = "/AUTOSAR/EcucDefs/Rte/RteSwComponentInstance"
RTE_EVENT_TO_TASK_MAPPING = "/AUTOSAR/EcucDefs/Rte/RteSwComponentInstance/RteEventToTaskMapping"
RTE_EXCLUSIVE_AREA_IMPLEMENTATION = "/AUTOSAR/EcucDefs/Rte/RteSwComponentInstance/RteExclusiveAreaImplementation"
RTE_DEF_REF_DICT = {
    "RteSwComponentInstance": "/AUTOSAR/EcucDefs/Rte/RteSwComponentInstance",
    "RteEventToTaskMapping": RTE_EVENT_TO_TASK_MAPPING,
    "RteMappedToTaskRef": f"{RTE_EVENT_TO_TASK_MAPPING}/RteMappedToTaskRef",
    "RteEventRef": f"{RTE_EVENT_TO_TASK_MAPPING}/RteEventRef",
    "RteExclusiveAreaImplementation": RTE_EXCLUSIVE_AREA_IMPLEMENTATION,
    "RteExclusiveAreaImplMechanism": f"{RTE_EXCLUSIVE_AREA_IMPLEMENTATION}/RteExclusiveAreaImplMechanism",
    "RteExclusiveAreaRef": f"{RTE_EXCLUSIVE_AREA_IMPLEMENTATION}/RteExclusiveAreaRef",
    "RteExclusiveAreaOsResourceRef": f"{RTE_EXCLUSIVE_AREA_IMPLEMENTATION}/RteExclusiveAreaOsResourceRef",
}

RTE_BSW_EVENT_TO_TASK_MAPPING = "/AUTOSAR/EcucDefs/Rte/RteBswModuleInstance/RteBswEventToTaskMapping"
RTE_BSW_EXCLUSIVE_AREA_IMPL = "/AUTOSAR/EcucDefs/Rte/RteBswModuleInstance/RteBswExclusiveAreaImpl"
RTE_BSW_DEF_REF_DICT = {
    "RteBswModuleInstance": "/AUTOSAR/EcucDefs/Rte/RteBswModuleInstance",
    "RteBswEventToTaskMapping": RTE_BSW_EVENT_TO_TASK_MAPPING,
    "RteBswMappedToTaskRef": f"{RTE_BSW_EVENT_TO_TASK_MAPPING}/RteBswMappedToTaskRef",
    "RteBswEventRef": f"{RTE_BSW_EVENT_TO_TASK_MAPPING}/RteBswEventToTaskMapping/RteBswEventRef",
    "RteBswExclusiveAreaImpl": RTE_BSW_EXCLUSIVE_AREA_IMPL,
    "RteExclusiveAreaImplMechanism": f"{RTE_BSW_EXCLUSIVE_AREA_IMPL}/RteExclusiveAreaImplMechanism",
    "RteBswExclusiveAreaRef": f"{RTE_BSW_EXCLUSIVE_AREA_IMPL}/RteBswExclusiveAreaRef",
    "RteBswExclusiveAreaOsResourceRef": f"{RTE_BSW_EXCLUSIVE_AREA_IMPL}/RteBswExclusiveAreaOsResourceRef",
    "RteBswExclusiveAreaOsSpinlockRef": f"{RTE_BSW_EXCLUSIVE_AREA_IMPL}/RteBswExclusiveAreaOsSpinlockRef",
}


def exclusive_area_process(asw_obj, ecuc_autosar_dict):
    if asw_obj is None:
        return
    ea_objs = get_asw_exclusive_area_objs(asw_obj)
    ea_dict = parser_asw_exclusive_area_objs(ea_objs)
    if "Rte" in ecuc_autosar_dict and ecuc_autosar_dict.get("Rte", None) is not None:
        add_asw_exclusive_areas_to_rte(ea_dict, ecuc_autosar_dict["Rte"])


def get_asw_exclusive_area_objs(asw):
    exclusive_area = {
        RUNS_INSIDE: asw.find_nodes(EXCLUSIVE_AREA_TYPE[RUNS_INSIDE]),
        CAN_ENTER: asw.find_nodes(EXCLUSIVE_AREA_TYPE[CAN_ENTER]),
    }
    return exclusive_area


def get_rte_exclusive_area_objs(rte):
    exclusive_area = {
        RUNS_INSIDE: rte.find_nodes(EXCLUSIVE_AREA_TYPE[RUNS_INSIDE]),
        CAN_ENTER: rte.find_nodes(EXCLUSIVE_AREA_TYPE[CAN_ENTER]),
    }
    return exclusive_area


def parser_asw_exclusive_area_objs(ea_s: dict):
    exclusive_area_list = []
    for ea_type, ea_list in ea_s.items():
        if not isinstance(ea_list, list):
            continue
        for ea in ea_list:
            ea_info = dict.fromkeys(
                ["ea_name", "ea_valueof", "ea_type", "component_type", "internal_behavior", "runnable_entity"]
            )
            ea_value = ea.valueOf_ if ea.valueOf_ else None
            ea_value_split = ea_value.split("/") if isinstance(ea_value, str) else None
            ea_parent = ea.parent_object_ if ea.parent_object_ else None
            runnable_obj = ea_parent.parent_object_ if ea_parent and ea_parent.parent_object_ else None
            runnable_name = get_short_name(runnable_obj)
            runnable_path = runnable_obj.get_path()
            if ea_value_split and len(ea_value_split) > 4 and runnable_name:
                ea_info["ea_name"] = ea_value_split[-1]
                ea_info["ea_valueof"] = ea_value
                ea_info["ea_type"] = ea_type
                ea_info["component_type"] = ea_value_split[-3]
                ea_info["internal_behavior"] = ea_value_split[-2]
                ea_info["runnable_entity"] = runnable_name
                ea_info["runnable_path"] = runnable_path
                if ea_type == RUNS_INSIDE:
                    exclusive_area_list.append(ea_info)
                elif ea_type == CAN_ENTER:
                    exclusive_area_list.append(ea_info)
    return exclusive_area_list


def add_asw_exclusive_areas_to_rte(ea_dict, rte_ecuc):
    rte_sw_componentinstances = []
    rte = rte_ecuc.find("/ActiveEcuC/Rte")
    if not rte or not rte.CONTAINERS or not rte.CONTAINERS.ECUC_CONTAINER_VALUE:
        return
    rte_containers = rte.CONTAINERS.ECUC_CONTAINER_VALUE
    for container in rte_containers:
        if get_definition_ref(container) == RTE_SW_COMPONENTINSTANCE_DEF_REF:
            rte_sw_componentinstances.append(container)
    for rte_sw_componentinstance in rte_sw_componentinstances:
        rte_sw_componentinstance.find_nodes("ECUC-CONTAINER-VALUE")
    pass


def update_rte_instances_and_os_resource_spinlock(
    ecuc_mod, asw_autosar, autosar_bsw_class, internal_behavior_autosar_dict
):
    """
    rte bsw and swc instances, os resource spinlock update interface.
    """
    rte_autosar = autosar_bsw_class.get("Rte", None)
    if not ecuc_mod or not rte_autosar:
        return

    ecuc_rte = rte_autosar.find("/ActiveEcuC/Rte")
    os_autosar = autosar_bsw_class.get("Os", None)
    if os_autosar:
        ecuc_os = os_autosar.find("/ActiveEcuC/Os")
    else:
        ecuc_os = None

    for module_name, ib_autosar in internal_behavior_autosar_dict.items():
        RteBswInstancesManager.add_rte_bsw_module_instance_from_ib(
            ecuc_mod.get("Rte", None), rte_autosar, ib_autosar, module_name
        )

    _update_rte_bsw_eas(ecuc_mod.get("Rte", None), rte_autosar, internal_behavior_autosar_dict)

    rte_ea_resource_spinlock_infos = _get_rte_resource_spinlock_ea(asw_autosar, ecuc_rte)
    _update_os_resource_spinlock(ecuc_mod.get("Os", None), ecuc_os, rte_ea_resource_spinlock_infos)


def get_rte_bsw_instances_eas_and_ib_eas(ecuc_rte, internal_behavior_autosar_dict):
    """获取Rte RteBswInstances中已存在的eas和ib文件中的eas

    Args:
        ecuc_rte (_type_): _description_
        internal_behavior_autosar_dict (_type_): _description_
    """
    rte_bsw_eas_dict = {}
    ib_eas_dict = {}
    if ecuc_rte and ecuc_rte.CONTAINERS and ecuc_rte.CONTAINERS.ECUC_CONTAINER_VALUE:
        for container_value in ecuc_rte.CONTAINERS.ECUC_CONTAINER_VALUE:
            module_name = get_short_name(container_value)
            if get_definition_ref(container_value) == RTE_BSW_DEF_REF_DICT["RteBswModuleInstance"]:
                rte_bsw_eas_dict[module_name] = []
                rte_bsw_instance_exclusive_areas = _get_bsw_insatce_exclusive_areas(container_value)
                for exclusive_area_list in rte_bsw_instance_exclusive_areas.values():
                    rte_bsw_eas_dict[module_name] += exclusive_area_list

    for module_name, bsw_ib in internal_behavior_autosar_dict.items():
        if bsw_ib is None:
            continue
        ib_eas = bsw_ib.find_nodes("EXCLUSIVE-AREA")
        ib_eas_dict[module_name] = {}
        for ib_ea in ib_eas:
            ib_ea_name = get_short_name(ib_ea)
            rte_bsw_exclusive_area_ref = ib_ea.get_path()
            if ib_ea_name is not None:
                ib_eas_dict[module_name].update(
                    {ib_ea_name: {"name": ib_ea_name, "ea_rfe": rte_bsw_exclusive_area_ref}}
                )
    return rte_bsw_eas_dict, ib_eas_dict


def _update_rte_bsw_eas(ecuc_mod, rte_autosar, internal_behavior_autosar_dict):
    """
    Delete RteBswInstances EAs that do not exist in ib.arxml.
    Synchronize EAs in ib.arxml to RteBswInstances.
    """
    ecuc_rte = rte_autosar.find("/ActiveEcuC/Rte")
    if ecuc_rte is None:
        logger.warning("Rte module not found!")
        return

    rte_bsw_eas_dict, ib_eas_dict = get_rte_bsw_instances_eas_and_ib_eas(ecuc_rte, internal_behavior_autosar_dict)

    for module_name, rte_bsw_eas in rte_bsw_eas_dict.items():
        # Delete those EAs that do not exist in ib.arxml in RteBswInstances.
        if module_name not in ib_eas_dict.keys():
            ib_eas_dict[module_name] = {}
        for rte_bsw_ea in rte_bsw_eas:
            if rte_bsw_ea["eas_name"] not in ib_eas_dict[module_name].keys() and AutosarUtil.is_automatic(
                rte_bsw_ea["container"]
            ):
                parent_list = getattr(rte_bsw_ea["container"].get_parent(), "ECUC_CONTAINER_VALUE", [])
                if not isinstance(parent_list, list):
                    continue
                AutosarUtil.remove_container_value(parent_list, rte_bsw_ea["container"])
                # _remove_task_res_ref(os_autosar, os_resource_path)

    for module_name, ib_module_eas in ib_eas_dict.items():
        rte_bsw_instance_container = ecuc_rte.find(f"./{module_name}")
        if rte_bsw_instance_container is None:
            continue
        if module_name not in rte_bsw_eas_dict.keys():
            rte_bsw_eas_dict[module_name] = []
        for ib_ea_name, ib_ea_info in ib_module_eas.items():
            for rte_bsw_eas in rte_bsw_eas_dict[module_name]:
                if rte_bsw_eas["eas_name"] == ib_ea_name:
                    break
            else:
                ea_conf_def = ecuc_mod.find("/AUTOSAR/EcucDefs/Rte/RteBswModuleInstance/RteBswExclusiveAreaImpl")
                if ea_conf_def is None:
                    continue
                exclusive_area_ref = ib_ea_info["ea_rfe"]
                ea_container = rte_bsw_instance_container.find(f"./{ib_ea_name}")
                if ea_container is None:
                    ea_container = AutosarUtil.create_container_value(
                        ib_ea_name, ea_conf_def, rte_bsw_instance_container
                    )
                    AutosarUtil.add_annotation_value(ea_container, "IsAutomatic")
                    values = get_parameter_values(ea_container)
                    for value in values:
                        def_ref = get_definition_ref(value)
                        if def_ref.endswith("RteExclusiveAreaImplMechanism"):
                            set_value(value, "OS_INTERRUPT_BLOCKING")
                        elif def_ref.endswith("RteBswExclusiveAreaRef"):
                            set_value_ref(value, exclusive_area_ref)


def clear_automatic_os_resource_and_spinlock(ecuc_os):
    rte_ea_resource_spinlock = {
        "bsw": {"OS_RESOURCE": {}, "OS_SPINLOCK": {}},
        "swc": {"OS_RESOURCE": {}, "OS_SPINLOCK": {}},
    }
    if ecuc_os is None:
        return
    os_root_container = ecuc_os.find("/ActiveEcuC/Os")
    if os_root_container is None:
        return
    os_resource_spinlock = _get_os_resource_spinlock(os_root_container)
    delete_redundant_automatic_os_resource_spinlock(os_root_container, os_resource_spinlock, rte_ea_resource_spinlock)


def _update_os_resource_spinlock(ecuc_mod, ecuc_os, rte_ea_resource_spinlock_infos):
    """
    Remove unnecessary resources and spinlocks that are automatically added to the os.
    Add resources and spinlocks to os.
    """
    if ecuc_os is None or rte_ea_resource_spinlock_infos is None:
        return
    resource_spinlock_dict = {}
    resource_spinlock_dict.update(rte_ea_resource_spinlock_infos["swc"]["OS_RESOURCE"])
    resource_spinlock_dict.update(rte_ea_resource_spinlock_infos["bsw"]["OS_RESOURCE"])
    resource_spinlock_dict.update(rte_ea_resource_spinlock_infos["bsw"]["OS_SPINLOCK"])
    os_resource_spinlock = _get_os_resource_spinlock(ecuc_os)
    delete_redundant_automatic_os_resource_spinlock(ecuc_os, os_resource_spinlock, rte_ea_resource_spinlock_infos)
    for resource_path, swc_os_resource in resource_spinlock_dict.items():
        os_had_resource = ecuc_os.find(swc_os_resource["os_resource_or_spinlock_path"])
        if os_had_resource:
            continue
        _add_resource_to_os(ecuc_mod, ecuc_os, swc_os_resource)
        # _add_resource_ref_to_task(
        # ecuc_mod, ecuc_os, swc_os_resource["task"], swc_os_resource["os_resource_or_spinlock_path"], )
        # resource_accessing_application = _get_resource_accessing_application(ecuc_os, swc_os_resource["task"])

        # os_resource_value_dict = {
        #     "/AUTOSAR/EcucDefs/Os/OsResource/OsResourceProperty": {"Value": "STANDARD"},
        #     "/AUTOSAR/EcucDefs/Os/OsResource/OsResourceAccessingApplication":{"Value": resource_accessing_application}
        #     # "/AUTOSAR/EcucDefs/Os/OsResource/OsResourceLinkedResourceRef": None,
        # }
        # _create_resource_to_os(ecuc_mod, ecuc_os, swc_os_resource, os_resource_value_dict)


def _add_resource_to_os(ecuc_mod, os_autosar, os_resource_or_spinlock_dict):
    """
    add spinlock or resource to os.
    """
    task_ref_list = os_resource_or_spinlock_dict["task"]
    resource_ref = os_resource_or_spinlock_dict["os_resource_or_spinlock_path"]
    os_container = os_autosar.find("/ActiveEcuC/Os")
    os_container_mod_def = get_definition_ref(os_container)
    if os_resource_or_spinlock_dict["mechanism"] == "OS_RESOURCE":
        if len(task_ref_list):
            for task_ref in task_ref_list:
                task = os_autosar.find(task_ref)
                if not task or not task.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
                    continue
                find_ref = "/AUTOSAR/EcucDefs/Os/OsTask/OsTaskResourceRef"
                _add_ref_values_to_container(ecuc_mod, task, find_ref, [resource_ref])
                resource_accessing_application = _get_resource_accessing_application(os_autosar, task_ref_list)
            mod_def = ecuc_mod.find(os_container_mod_def + "/OsResource")
            res_short_name = os_resource_or_spinlock_dict["os_resource_or_spinlock_path"].split("/")[-1]
            res_container = AutosarUtil.create_sub_container_value(res_short_name, mod_def, os_container)
            AutosarUtil.add_annotation_value(res_container, "IsAutomatic")
            values = get_parameter_values(res_container)
            for value in values:
                def_ref = get_definition_ref(value)
                if def_ref.endswith("OsResourceProperty"):
                    set_value(value, "STANDARD")
                elif def_ref.endswith("OsResourceAccessingApplication") and len(resource_accessing_application):
                    set_value_ref(value, resource_accessing_application[0])
                    resource_accessing_application.pop(0)
            for accessing_app in resource_accessing_application:
                cur_conf_def = "/AUTOSAR/EcucDefs/Os/OsResource/OsResourceAccessingApplication"
                mod_conf_def = ecuc_mod.find(cur_conf_def)
                obj = AutosarUtil.set_reference(res_container.REFERENCE_VALUES, mod_conf_def)
                set_value_ref(obj, str(accessing_app))
        else:
            res_short_name = os_resource_or_spinlock_dict["os_resource_or_spinlock_path"].split("/")[-1]
            logger.warning(
                f"EAs synchronize to os resources ({res_short_name}) failure: runnable unmapping to any task."
            )
    elif os_resource_or_spinlock_dict["mechanism"] == "OS_SPINLOCK":
        if len(task_ref_list):
            # task = os_autosar.find(task_ref)
            # if not task or not task.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
            #     continue
            # # find_ref = "/AUTOSAR/EcucDefs/Os/OsTask/OsTaskResourceRef"
            # # _add_ref_values_to_container(ecuc_mod, task, find_ref, [resource_ref])
            resource_accessing_application = _get_resource_accessing_application(os_autosar, task_ref_list)
            mod_def = ecuc_mod.find(os_container_mod_def + "/OsSpinlock")
            spinlock_short_name = os_resource_or_spinlock_dict["os_resource_or_spinlock_path"].split("/")[-1]
            spinlock_container = AutosarUtil.create_sub_container_value(spinlock_short_name, mod_def, os_container)
            AutosarUtil.add_annotation_value(spinlock_container, "IsAutomatic")
            values = get_parameter_values(spinlock_container)
            for value in values:
                def_ref = get_definition_ref(value).split("/")[-1]
                if def_ref == ("OsSpinlockLockMethod"):
                    set_value(value, "LOCK_CAT2_INTERRUPTS")
                elif def_ref == ("OsSpinlockLockType"):
                    set_value(value, "STANDARD")
                elif def_ref == ("OsSpinlockAccessingApplication") and len(resource_accessing_application):
                    set_value_ref(value, resource_accessing_application[0])
                    resource_accessing_application.pop(0)
            for accessing_app in resource_accessing_application:
                cur_conf_def = "/AUTOSAR/EcucDefs/Os/OsSpinlock/OsSpinlockAccessingApplication"
                mod_conf_def = ecuc_mod.find(cur_conf_def)
                obj = AutosarUtil.set_reference(spinlock_container.REFERENCE_VALUES, mod_conf_def)
                set_value_ref(obj, str(accessing_app))
        else:
            spinlock_short_name = os_resource_or_spinlock_dict["os_resource_or_spinlock_path"].split("/")[-1]
            logger.warning(
                f"EAs synchronize to os spinlock ({spinlock_short_name}) failure: runnable unmapping to any task."
            )


def delete_redundant_automatic_os_resource_spinlock(ecuc_os, os_resource_spinlocks, rte_ea_resource_spinlock_infos):
    rte_resource = {}
    rte_spinlock = {}
    rte_resource.update(rte_ea_resource_spinlock_infos["bsw"]["OS_RESOURCE"])
    rte_resource.update(rte_ea_resource_spinlock_infos["swc"]["OS_RESOURCE"])
    rte_spinlock.update(rte_ea_resource_spinlock_infos["bsw"]["OS_SPINLOCK"])
    rte_spinlock.update(rte_ea_resource_spinlock_infos["swc"]["OS_SPINLOCK"])

    for os_resource_path in list(os_resource_spinlocks["OS_RESOURCE"].keys()):
        if os_resource_path not in rte_resource.keys():
            os_resource = os_resource_spinlocks["OS_RESOURCE"][os_resource_path]
            if AutosarUtil.is_automatic(os_resource):
                parent_list = getattr(os_resource.parent_object_, "ECUC_CONTAINER_VALUE", [])
                if not isinstance(parent_list, list):
                    continue
                AutosarUtil.remove_container_value(parent_list, os_resource)
                _remove_task_res_ref(ecuc_os, os_resource_path)

    for os_spinlock_path in list(os_resource_spinlocks["OS_SPINLOCK"].keys()):
        if os_spinlock_path not in rte_spinlock.keys():
            os_spinlock = os_resource_spinlocks["OS_SPINLOCK"][os_spinlock_path]
            if AutosarUtil.is_automatic(os_spinlock):
                parent_list = getattr(os_spinlock.parent_object_, "ECUC_CONTAINER_VALUE", [])
                if not isinstance(parent_list, list):
                    continue
                AutosarUtil.remove_container_value(parent_list, os_spinlock)


def _remove_task_res_ref(ecuc_os, os_resource_path):
    ecuc_os_container_list = ecuc_os.find_nodes("ECUC-CONTAINER-VALUE")
    for ecuc_os_container in ecuc_os_container_list:
        def_ref = get_definition_ref(ecuc_os_container)
        if def_ref.split("/")[-1] == "OsTask":
            _remove_reference_value(ecuc_os_container, "OsTaskResourceRef", os_resource_path)


def _remove_reference_value(container, find_ref_def, delete_ref_value):
    """
    删除容器中指定的reference值, 并删除多余的empty值
    """
    ref_container_dict = {}
    ref_container_empty_list = []
    if (
        container is None
        or container.REFERENCE_VALUES is None
        or container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE is None
    ):
        return
    for ref_val in container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
        def_ref = __get_definition_ref(ref_val, "")
        if def_ref.split("/")[-1] == find_ref_def:
            value_ref = get_value_ref(ref_val)
            if (value_ref == "<empty>") or (value_ref is None):
                ref_container_empty_list.append(ref_val)
            else:
                ref_container_dict[value_ref] = ref_val
    if delete_ref_value in ref_container_dict.keys():
        if len(ref_container_dict) > 1:
            AutosarUtil.remove_node_value(
                container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE, ref_container_dict[delete_ref_value]
            )
        else:
            set_value_ref(ref_container_dict[delete_ref_value], None)
        for ref_container_empty in ref_container_empty_list:
            AutosarUtil.remove_node_value(container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE, ref_container_empty)


def _get_rte_resource_spinlock_ea(asw_autosar, ecuc_rte):
    """
    Get the Resource and Spinlock in RTE
    """
    rte_ea_resource_spinlock_infos = {
        "bsw": {"OS_RESOURCE": {}, "OS_SPINLOCK": {}},
        "swc": {"OS_RESOURCE": {}, "OS_SPINLOCK": {}},
    }
    if not ecuc_rte or not ecuc_rte.CONTAINERS or not ecuc_rte.CONTAINERS.ECUC_CONTAINER_VALUE:
        return rte_ea_resource_spinlock_infos

    if asw_autosar is not None:
        asw_ea_objs = get_asw_exclusive_area_objs(asw_autosar)
        asw_ea_list = parser_asw_exclusive_area_objs(asw_ea_objs)
    else:
        asw_ea_list = []

    for container_value in ecuc_rte.CONTAINERS.ECUC_CONTAINER_VALUE:
        # def_ref = get_definition_ref(container_value)
        if get_definition_ref(container_value) == RTE_BSW_DEF_REF_DICT["RteBswModuleInstance"]:
            bsw_resource_or_spinlock_s = filter_bsw_resource_and_spinlock(container_value)
            if bsw_resource_or_spinlock_s is None or len(bsw_resource_or_spinlock_s) == 0:
                continue
            for res_spinlock_path, res_spinlock_value in bsw_resource_or_spinlock_s.items():
                if res_spinlock_value["mechanism"] == "OS_SPINLOCK":
                    rte_ea_resource_spinlock_infos["bsw"]["OS_SPINLOCK"].update({res_spinlock_path: res_spinlock_value})
                if res_spinlock_value["mechanism"] == "OS_RESOURCE":
                    rte_ea_resource_spinlock_infos["bsw"]["OS_RESOURCE"].update({res_spinlock_path: res_spinlock_value})
        if get_definition_ref(container_value) == RTE_DEF_REF_DICT["RteSwComponentInstance"]:
            rte_ea_resource_infos = filter_swc_resource(asw_autosar, container_value, asw_ea_list)
            if rte_ea_resource_infos is None or len(rte_ea_resource_infos) == 0:
                continue
            for res_path, res_value in rte_ea_resource_infos.items():
                if res_value["mechanism"] == "OS_RESOURCE":
                    rte_ea_resource_spinlock_infos["swc"]["OS_RESOURCE"].update({res_path: res_value})
    return rte_ea_resource_spinlock_infos


def _get_os_resource_spinlock(ecuc_os):
    os_resource_spinlock = {"OS_RESOURCE": {}, "OS_SPINLOCK": {}}
    if not hasattr(ecuc_os, "CONTAINERS"):
        return os_resource_spinlock
    for ecuc_container_value in ecuc_os.CONTAINERS.ECUC_CONTAINER_VALUE:
        def_ref = get_definition_ref(ecuc_container_value)
        if def_ref == "/AUTOSAR/EcucDefs/Os/OsResource":
            container_path = ecuc_container_value.get_path()
            if container_path:
                os_resource_spinlock["OS_RESOURCE"].update({container_path: ecuc_container_value})
        elif def_ref == "/AUTOSAR/EcucDefs/Os/OsSpinlock":
            container_path = ecuc_container_value.get_path()
            if container_path:
                os_resource_spinlock["OS_SPINLOCK"].update({container_path: ecuc_container_value})
    return os_resource_spinlock


def filter_bsw_resource_and_spinlock(container_value):
    rte_ea_resource_or_spinlock_infos = {}
    task_ref = None
    rte_ea_impl_mechanism = None
    ea_ref = None
    task_ref_list = []
    if not container_value.SUB_CONTAINERS or not container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
        return
    for swc_instance_child in container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
        sub_def_ref = get_definition_ref(swc_instance_child)
        if sub_def_ref == RTE_BSW_DEF_REF_DICT["RteBswEventToTaskMapping"]:
            task_ref = _get_first_value_from_def_ref(
                swc_instance_child, RTE_BSW_DEF_REF_DICT["RteBswMappedToTaskRef"], "ECUC_REFERENCE_VALUE"
            )
            if task_ref:
                if task_ref in task_ref_list:
                    continue
                task_ref_list.append(task_ref)
    for swc_instance_child in container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
        sub_def_ref = get_definition_ref(swc_instance_child)
        if sub_def_ref == RTE_BSW_DEF_REF_DICT["RteBswExclusiveAreaImpl"]:
            rte_ea_impl_mechanism = _get_first_value_from_def_ref(
                swc_instance_child, RTE_BSW_DEF_REF_DICT["RteExclusiveAreaImplMechanism"], "ECUC_TEXTUAL_PARAM_VALUE"
            )
            # if rte_ea_impl_mechanism not in ["OS_RESOURCE", "OS_SPINLOCK"]:
            #     continue
            ea_ref = _get_first_value_from_def_ref(
                swc_instance_child, RTE_BSW_DEF_REF_DICT["RteBswExclusiveAreaRef"], "ECUC_REFERENCE_VALUE"
            )
            if rte_ea_impl_mechanism and ea_ref:
                if len(ea_ref.split("/")) < 4:
                    continue
                ea_name = ea_ref.split("/")[-1]
                swc_or_bsw_name = ea_ref.split("/")[-3]
                if rte_ea_impl_mechanism == "OS_SPINLOCK":
                    find_def_ref = RTE_BSW_DEF_REF_DICT["RteBswExclusiveAreaOsResourceRef"]
                    _set_ref_value_to_container(swc_instance_child, find_def_ref, None)
                    os_resource_or_spinlock_def_ref = RTE_BSW_DEF_REF_DICT["RteBswExclusiveAreaOsSpinlockRef"]
                    resource_path = f"/ActiveEcuC/Os/Rte_Spinlock_{swc_or_bsw_name}_{ea_name}"
                elif rte_ea_impl_mechanism == "OS_RESOURCE":
                    find_def_ref = RTE_BSW_DEF_REF_DICT["RteBswExclusiveAreaOsSpinlockRef"]
                    _set_ref_value_to_container(swc_instance_child, find_def_ref, None)
                    os_resource_or_spinlock_def_ref = RTE_BSW_DEF_REF_DICT["RteBswExclusiveAreaOsResourceRef"]
                    resource_path = f"/ActiveEcuC/Os/Rte_Res_{swc_or_bsw_name}_{ea_name}"
                else:
                    find_def_ref = RTE_BSW_DEF_REF_DICT["RteBswExclusiveAreaOsResourceRef"]
                    _set_ref_value_to_container(swc_instance_child, find_def_ref, None)
                    find_def_ref = RTE_BSW_DEF_REF_DICT["RteBswExclusiveAreaOsSpinlockRef"]
                    _set_ref_value_to_container(swc_instance_child, find_def_ref, None)
                    continue
                rte_ea_resource_or_spinlock_infos[resource_path] = {
                    "ea_name": ea_name,
                    "os_resource_or_spinlock_path": resource_path,
                    "ea_ref": ea_ref,
                    "task": task_ref_list,
                    "mechanism": rte_ea_impl_mechanism,
                }
                _set_ref_value_to_container(swc_instance_child, os_resource_or_spinlock_def_ref, resource_path)
    return rte_ea_resource_or_spinlock_infos


def filter_swc_resource(asw_autosar, container_value, asw_ea_list):
    # name = name.replace("_EcuSwComposition", "")
    task_ref = None
    rte_ea_impl_mechanism = None
    ea_ref = None
    task_ref_list = []
    rte_ea_resource_infos = {}
    if not asw_autosar or not container_value.SUB_CONTAINERS or not container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
        return rte_ea_resource_infos
    for swc_instance_child in container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
        sub_def_ref = get_definition_ref(swc_instance_child)
        if sub_def_ref == RTE_DEF_REF_DICT["RteEventToTaskMapping"]:
            task_ref = _get_first_value_from_def_ref(
                swc_instance_child, RTE_DEF_REF_DICT["RteMappedToTaskRef"], "ECUC_REFERENCE_VALUE"
            )
            rte_event_ref = _get_first_value_from_def_ref(
                swc_instance_child, RTE_DEF_REF_DICT["RteEventRef"], "ECUC_REFERENCE_VALUE"
            )
            ib_event = asw_autosar.find(rte_event_ref)
            event_short_name = get_short_name(ib_event)
            runnable = ib_event.START_ON_EVENT_REF.valueOf_ if ib_event and ib_event.START_ON_EVENT_REF else ""
            # short_name = get_short_name(swc_instance_child)
            task_ref_list.append({"runnable": runnable, "evevt": event_short_name, "task_ref": task_ref})
            # task_ref_dict[get_short_name(swc_instance_child)] = task_ref
    for swc_instance_child in container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
        sub_def_ref = get_definition_ref(swc_instance_child)
        if sub_def_ref == RTE_DEF_REF_DICT["RteExclusiveAreaImplementation"]:
            rte_ea_impl_mechanism = _get_first_value_from_def_ref(
                swc_instance_child, RTE_DEF_REF_DICT["RteExclusiveAreaImplMechanism"], "ECUC_TEXTUAL_PARAM_VALUE"
            )
            if rte_ea_impl_mechanism != "OS_RESOURCE":
                find_def_ref = RTE_DEF_REF_DICT["RteExclusiveAreaOsResourceRef"]
                _set_ref_value_to_container(swc_instance_child, find_def_ref, None)
                continue
            ea_ref = _get_first_value_from_def_ref(
                swc_instance_child, RTE_DEF_REF_DICT["RteExclusiveAreaRef"], "ECUC_REFERENCE_VALUE"
            )
            for asw_ea in asw_ea_list:
                if ea_ref == asw_ea["ea_valueof"]:
                    runnable_path = asw_ea["runnable_path"]
                    break
            else:
                continue
            task_ref = []
            for task_info in task_ref_list:
                if runnable_path == task_info["runnable"]:
                    task_ref.append(task_info["task_ref"])
            #         break
            # else:
            #     continue
            # ib_event = asw_autosar.find(ea_ref)
            if rte_ea_impl_mechanism and ea_ref:
                if len(ea_ref.split("/")) < 4:
                    continue
                ea_name = ea_ref.split("/")[-1]
                swc_name = ea_ref.split("/")[-3]
                resource_path = f"/ActiveEcuC/Os/Rte_Res_{swc_name}_{ea_name}"
                rte_ea_resource_infos[resource_path] = {
                    "ea_name": ea_name,
                    "os_resource_or_spinlock_path": resource_path,
                    "ea_ref": ea_ref,
                    "task": task_ref,
                    "mechanism": rte_ea_impl_mechanism,
                }
                find_def_ref = RTE_DEF_REF_DICT["RteExclusiveAreaOsResourceRef"]
                _set_ref_value_to_container(swc_instance_child, find_def_ref, resource_path)
    return rte_ea_resource_infos


def _get_resource_accessing_application(os_autosar, task_ref_list):
    resource_accessing_application = []
    if not os_autosar.CONTAINERS or not os_autosar.CONTAINERS.ECUC_CONTAINER_VALUE:
        return resource_accessing_application
    for task_ref in task_ref_list:
        for container in os_autosar.CONTAINERS.ECUC_CONTAINER_VALUE:
            def_ref = get_definition_ref(container)
            if def_ref == "/AUTOSAR/EcucDefs/Os/OsApplication":
                ref_trg = "/AUTOSAR/EcucDefs/Os/OsApplication/OsAppTaskRef"
                os_app_task_ref_list = _get_values_from_def_ref(container, ref_trg, "ECUC_REFERENCE_VALUE")
                if task_ref in os_app_task_ref_list:
                    osa_path = container.get_path()
                    resource_accessing_application.append(osa_path)
    return resource_accessing_application


def _add_resource_ref_to_task(ecuc_mod, os_autosar, task_ref, resource_ref):
    task = os_autosar.find(task_ref)
    if not task or not task.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
        return

    find_ref = "/AUTOSAR/EcucDefs/Os/OsTask/OsTaskResourceRef"
    _add_ref_values_to_container(ecuc_mod, task, find_ref, [resource_ref])


def _get_first_value_from_def_ref(container, def_ref, val_type):
    if val_type == "ECUC_REFERENCE_VALUE":
        if not container.REFERENCE_VALUES or not container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
            return None
        for child in container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
            get_def_ref = get_definition_ref(child)
            if get_def_ref == def_ref:
                return get_value_ref(child)
    elif val_type == "ECUC_TEXTUAL_PARAM_VALUE":
        if not container.PARAMETER_VALUES or not container.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE:
            return None
        for child in container.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE:
            get_def_ref = get_definition_ref(child)
            if get_def_ref == def_ref:
                return get_value(child)
    return None


def _get_values_from_def_ref(container, def_ref, val_type):
    value_list = []
    if val_type == "ECUC_REFERENCE_VALUE":
        if not container.REFERENCE_VALUES or not container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
            return None
        for child in container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
            get_def_ref = get_definition_ref(child)
            if get_def_ref == def_ref:
                value_list.append(get_value_ref(child))
    elif val_type == "ECUC_TEXTUAL_PARAM_VALUE":
        if not container.PARAMETER_VALUES or not container.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE:
            return None
        for child in container.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE:
            get_def_ref = get_definition_ref(child)
            if get_def_ref == def_ref:
                value_list.append(get_value(child))
    return value_list


def _add_ref_values_to_container(ecuc_mod, container, def_ref, ref_list):
    value_dict = {}
    if not container.REFERENCE_VALUES or not container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
        return None
    for child in container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
        get_def_ref = get_definition_ref(child)
        if get_def_ref == def_ref:
            ref_val = get_value_ref(child)
            if ref_val is None:
                ref_val = "<empty>"
            value_dict[ref_val] = child
    for ref in ref_list:
        if ref in value_dict:
            continue
        if "<empty>" in value_dict:
            set_value_ref(value_dict["<empty>"], str(ref))
            value_dict.pop("<empty>")
        else:
            cur_conf_def = ecuc_mod.find(def_ref)
            obj = AutosarUtil.set_reference(container.REFERENCE_VALUES, cur_conf_def)
            set_value_ref(obj, str(ref))


def _set_ref_value_to_container(container, def_ref, value):
    if not container.REFERENCE_VALUES or not container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
        return None
    for child in container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
        get_def_ref = get_definition_ref(child)
        if get_def_ref == def_ref:
            ref_val = get_value_ref(child)
            if ref_val != value:
                set_value_ref(child, value)


def _creat_os_sub_container(ecuc_mod, parent_container, container_name, container_mod_name, value_dict):
    created_container = None
    parent_path = get_definition_ref(parent_container)

    if parent_path and container_name and container_mod_name and isinstance(value_dict, dict):
        cur_conf_def = ecuc_mod.find(parent_path + f"/{container_mod_name}")
        created_container = AutosarUtil.create_sub_container_value(container_name, cur_conf_def, parent_container)
        _set_container_value_by_def_ref(ecuc_mod, created_container, value_dict)
    return created_container


def _set_container_value_by_def_ref(ecuc_def, container_obj, value_dict):
    if not container_obj or not value_dict:
        return
    if container_obj.REFERENCE_VALUES and container_obj.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
        ref_num = len(container_obj.REFERENCE_VALUES.ECUC_REFERENCE_VALUE)
        for i in range(ref_num):
            para = container_obj.REFERENCE_VALUES.ECUC_REFERENCE_VALUE[i]
            def_ref = get_definition_ref(para)
            cur_conf_def = ecuc_def.find(def_ref)
            if def_ref not in value_dict.keys():
                continue
            if isinstance(value_dict[def_ref]["Value"], list):
                if len(value_dict[def_ref]["Value"]):
                    set_value_ref(para, str(value_dict[def_ref]["Value"][0]))
                    for index in range(len(value_dict[def_ref]["Value"]) - 1):
                        obj = AutosarUtil.set_reference(container_obj.REFERENCE_VALUES, cur_conf_def)
                        set_value_ref(obj, str(value_dict[def_ref]["Value"][index + 1]))
            else:
                set_value_ref(para, str(value_dict[def_ref]["Value"]))
    if container_obj.PARAMETER_VALUES and container_obj.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
        for para in container_obj.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
            def_ref = get_definition_ref(para)
            if def_ref in value_dict.keys():
                if value_dict[def_ref]["Value"] is not None:
                    set_value(para, str(value_dict[def_ref]["Value"]))
    if container_obj.PARAMETER_VALUES and container_obj.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE:
        for para in container_obj.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE:
            def_ref = get_definition_ref(para)
            if def_ref in value_dict.keys():
                set_value(para, str(value_dict[def_ref]["Value"]))


def get_bsw_ib_default_config(module_name, bsw_ib):
    rv = {"exclusive_areas": {}, "event_to_task_mapping_entitys": []}
    eas_dict = {
        "ALL_INTERRUPT_BLOCKING": [],
        "OS_INTERRUPT_BLOCKING": [],
        "OS_RESOURCE": [],
        "OS_SPINLOCK": [],
        "NONE": [],
        "RTE_PLUGIN": [],
    }
    mainfunction_objs = bsw_ib.find_nodes("BSW-SCHEDULABLE-ENTITY")
    event_to_task_mapping_entitys = [get_short_name(x) for x in mainfunction_objs]
    rv["event_to_task_mapping_entitys"] = sorted(list(set(event_to_task_mapping_entitys)))

    ea_objs = bsw_ib.find_nodes("EXCLUSIVE-AREA")
    ea_name_list = [get_short_name(x) for x in ea_objs]
    ea_name_list_sort = sorted(list(set(ea_name_list)))
    for ea_name in ea_name_list_sort:
        eas_dict["OS_INTERRUPT_BLOCKING"].append(
            {"module_name": module_name, "eas_name": ea_name, "imp_mechanism": "OS_INTERRUPT_BLOCKING"}
        )
    rv["exclusive_areas"] = eas_dict
    return rv


def rte_bsw_instances_codegen_parser(ecuc_autosar_dict, internal_behavior_autosar_dict):
    rv = {}
    rte_autosar = ecuc_autosar_dict.get("Rte", None)
    if rte_autosar is None:
        for module_name, bsw_ib in internal_behavior_autosar_dict.items():
            if module_name == "Os":  # Os不生成
                continue
            rv[module_name] = get_bsw_ib_default_config(module_name, bsw_ib)
    else:
        ecuc_rte = rte_autosar.find("/ActiveEcuC/Rte")

        if not ecuc_rte or not ecuc_rte.CONTAINERS or not ecuc_rte.CONTAINERS.ECUC_CONTAINER_VALUE:
            return rv

        for container_value in ecuc_rte.CONTAINERS.ECUC_CONTAINER_VALUE:
            module_name = get_short_name(container_value)
            if get_definition_ref(container_value) == RTE_BSW_DEF_REF_DICT["RteBswModuleInstance"]:
                exclusive_areas_dict = _get_bsw_insatce_exclusive_areas(container_value)
                event_to_task_mappings_list = _get_bsw_insatce_event_to_task_mappings(
                    container_value, internal_behavior_autosar_dict
                )
                if module_name not in rv.keys():
                    rv[module_name] = {}
                rv[module_name].update({"exclusive_areas": exclusive_areas_dict})
                rv[module_name].update({"event_to_task_mapping_entitys": event_to_task_mappings_list})
    return rv


def _get_bsw_insatce_exclusive_areas(container_value):
    module_name = get_short_name(container_value)
    eas_dict = {
        "ALL_INTERRUPT_BLOCKING": [],
        "OS_INTERRUPT_BLOCKING": [],
        "OS_RESOURCE": [],
        "OS_SPINLOCK": [],
        "NONE": [],
        "RTE_PLUGIN": [],
    }
    if not container_value.SUB_CONTAINERS or not container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
        return eas_dict
    for bsw_instance_child in container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
        sub_def_ref = __get_definition_ref(bsw_instance_child, "")
        if sub_def_ref.split("/")[-1] == "RteBswExclusiveAreaImpl":
            eas_container = bsw_instance_child
            eas_short_name = get_short_name(eas_container)
            parameter_values = get_parameter_values(eas_container)
            for parameter_value in parameter_values:
                def_ref = __get_definition_ref(parameter_value, "")
                if def_ref.split("/")[-1] == "RteExclusiveAreaImplMechanism":
                    imp_mechanism = get_value(parameter_value)
                    if imp_mechanism is None:
                        imp_mechanism = "NONE"
                elif def_ref.split("/")[-1] == "RteBswExclusiveAreaOsResourceRef":
                    resource_ref = get_value_ref(parameter_value)
                elif def_ref.split("/")[-1] == "RteBswExclusiveAreaOsSpinlockRef":
                    spinlock_ref = get_value_ref(parameter_value)
            if "imp_mechanism" in locals() and imp_mechanism in eas_dict.keys():
                eas_dict[imp_mechanism].append(
                    {
                        "module_name": module_name,
                        "eas_name": eas_short_name,
                        "imp_mechanism": imp_mechanism,
                        "container": eas_container,
                        # "resource_name": resource_ref.split("/")[-1] if isinstance(resource_ref),
                        # "spinlock_name": spinlock_ref.split("/")[-1],
                    }
                )
    return eas_dict


def _get_bsw_insatce_event_to_task_mappings(container_value, internal_behavior_autosar_dict):
    """根据IB中的mainfunction生成SchM_Module.h中的声明

    Args:
        container_value (_type_): _description_
        internal_behavior_autosar_dict (_type_): _description_

    Returns:
        _type_: _description_
    """
    module_name = get_short_name(container_value)
    module_ib = internal_behavior_autosar_dict.get(module_name, None)
    if module_ib is None:
        return []
    mainfunction_objs = module_ib.find_nodes("BSW-SCHEDULABLE-ENTITY")
    event_to_task_mapping_entitys = [get_short_name(x) for x in mainfunction_objs]
    return sorted(list(set(event_to_task_mapping_entitys)))
    # if not container_value.SUB_CONTAINERS or not container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
    #     return event_to_task_mapping_entitys
    # for bsw_instance_child in container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
    #     sub_def_ref = __get_definition_ref(bsw_instance_child, "")
    #     if sub_def_ref.split("/")[-1] == "RteBswEventToTaskMapping":
    #         event_to_task_mapping_container = bsw_instance_child
    #         event_to_task_mapping_short_name = get_short_name(event_to_task_mapping_container)
    #         ib_autosar = internal_behavior_autosar_dict.get(module_name)
    #         if ib_autosar is None:
    #             if event_to_task_mapping_short_name.endswith("TimingEvent0"):
    #                 bsw_schedulable_entity_name = event_to_task_mapping_short_name[:-(len("TimingEvent0"))]
    #             else:
    #                 bsw_schedulable_entity_name = event_to_task_mapping_short_name
    #             event_to_task_mapping_entitys.append(bsw_schedulable_entity_name)
    #             logger.info(f"Lack of {module_name}_ib_bswmd.arxml")
    #             return event_to_task_mapping_entitys
    #         bsw_timing_event_list = ib_autosar.find_nodes("BSW-TIMING-EVENT")
    #         for bsw_timing_event in bsw_timing_event_list:
    #             if get_short_name(bsw_timing_event) != event_to_task_mapping_short_name:
    #                 continue
    #             bsw_schedulable_entity_ref = getattr(bsw_timing_event.STARTS_ON_EVENT_REF, "valueOf_", "")
    #             if isinstance(bsw_schedulable_entity_ref, str) and len(bsw_schedulable_entity_ref.split("/")) > 1:
    #                 bsw_schedulable_entity_name = bsw_schedulable_entity_ref.split("/")[-1]
    #             else:
    #                 if event_to_task_mapping_short_name.endswith("TimingEvent0"):
    #                     bsw_schedulable_entity_name = event_to_task_mapping_short_name[:-(len("TimingEvent0"))]
    #                 else:
    #                     bsw_schedulable_entity_name = event_to_task_mapping_short_name
    #             event_to_task_mapping_entitys.append(bsw_schedulable_entity_name)


def __get_definition_ref(obj, default_value=None):
    if obj is None or obj.DEFINITION_REF is None or obj.DEFINITION_REF.valueOf_ is None:
        return default_value
    return obj.DEFINITION_REF.valueOf_


def get_parameter_values(container):
    values = []
    values += container.PARAMETER_VALUES.ECUC_ADD_INFO_PARAM_VALUE
    values += container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE
    values += container.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE
    values += container.REFERENCE_VALUES.ECUC_INSTANCE_REFERENCE_VALUE
    values += container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE
    return values


class RteBswInstancesManager:

    def __init__(self, main_window) -> None:
        self.main_window = main_window

    @classmethod
    def add_rte_bsw_module_instance_from_ib(cls, mod_autosar, rte_autosar, bsw_module_ib_autosar, module_name):
        # mod_autosar = self.main_window.mod_autosar_dict.get("All")
        # rte_autosar = self.main_window.ecuc_autosar_dict.get("Rte")
        bsw_module_autosar = bsw_module_ib_autosar
        # if "Rte" == module_name:
        #     return
        if bsw_module_autosar is None:
            logger.info(f"{module_name} internal behavior not found!")
            return
        if mod_autosar is None or rte_autosar is None:
            logger.info(f"'{module_name}' module not added to RteBswoduleInstance, because of rte module not found!")
            return

        rte = rte_autosar.find("/ActiveEcuC/Rte")
        rte_bsw_instance_container = rte.find(f"./{module_name}")
        if rte_bsw_instance_container is None:
            conf_def = mod_autosar.find("/AUTOSAR/EcucDefs/Rte/RteBswModuleInstance")
            rte_bsw_instance_container = AutosarUtil.create_container_value(module_name, conf_def, rte)
            AutosarUtil.add_annotation_value(rte_bsw_instance_container, "IsAutomatic")
        cls.update_rte_bsw_instance_eas(mod_autosar, rte_bsw_instance_container, bsw_module_autosar)

    @classmethod
    def update_rte_bsw_instance_eas(cls, mod_autosar, rte_bsw_instance_container, bsw_module_autosar):
        # mod_autosar = self.main_window.mod_autosar_dict.get("All")
        ib_eas = bsw_module_autosar.find_nodes("EXCLUSIVE-AREA")
        for ea_obj in sorted(ib_eas, key=lambda x: get_short_name(x)):
            exclusive_area_name = get_short_name(ea_obj)
            ea_container = rte_bsw_instance_container.find(f"./{exclusive_area_name}")
            if ea_container is None:
                ea_conf_def = mod_autosar.find("/AUTOSAR/EcucDefs/Rte/RteBswModuleInstance/RteBswExclusiveAreaImpl")
                exclusive_area_ref = ea_obj.get_path()
                ea_container = AutosarUtil.create_container_value(
                    exclusive_area_name, ea_conf_def, rte_bsw_instance_container
                )
                AutosarUtil.add_annotation_value(ea_container, "IsAutomatic")
                values = get_parameter_values(ea_container)
                for value in values:
                    def_ref = get_definition_ref(value)
                    if def_ref.endswith("RteExclusiveAreaImplMechanism"):
                        set_value(value, "OS_INTERRUPT_BLOCKING")
                    elif def_ref.endswith("RteBswExclusiveAreaRef"):
                        set_value_ref(value, exclusive_area_ref)
