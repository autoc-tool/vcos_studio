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
ib_bswm对象公共方法
"""

from basic_func_module.autosar_utils.utils import get_short_name, set_short_name
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from autosar44 import autosar44
from func_module.health_monitor.logger import logger


def create_bsw_exclusive_area(ib_autosar, module_name, ea_shortname):
    """
    描述: 此接口用于创建EXCLUSIVE-AREA并添加至ib对象
    """
    """
    入参：
    ib_autosar: bsw模块的ib arxml的autosar对象
    module_name: 指定的bsw模块
    ea_shortname: 需要创建的EXCLUSIVE-AREA的short-name
    """
    ea_containers = ib_autosar.find_nodes("EXCLUSIVE-AREA")
    for ea_container in ea_containers:
        find_short_name = get_short_name(ea_container)
        if find_short_name == ea_shortname:
            logger.warning(f"{module_name} ExclusiveArea {ea_shortname} already exist!")
            return ea_container

    exclusive_areas_containers = ib_autosar.find_nodes("EXCLUSIVE-AREAS")
    exclusive_areas_num = len(exclusive_areas_containers)
    if exclusive_areas_num != 1:
        logger.error(f"{module_name} ExclusiveAreasContainer number {exclusive_areas_num} error!")
        return

    parent_container = exclusive_areas_containers[0]
    container_value = autosar44.EXCLUSIVE_AREA()
    container_value.set_tag("EXCLUSIVE-AREA")
    container_value.set_parent(parent_container)
    set_short_name(container_value, ea_shortname)
    parent_container.EXCLUSIVE_AREA.append(container_value)
    return container_value


def create_bsw_module_entry_ref_conditional(ib_autosar, module_name, bsw_module_entry_ref, prefix="/AUTOSAR"):
    """
    描述: 此接口用于检查模块对应的ib文件中的ref对象并创建添加至ib对象
    """
    """
    入参：
    ib_autosar: bsw模块的ib arxml的autosar对象
    module_name: 指定的bsw模块
    bsw_module_entry_ref: 需要创建的BSW_MODULE_ENTRY_REF_CONDITIONAL的BSW-MODULE-ENTRY-REF的VALUE
    """
    """
    方法: dfs-自上而下查找 至下而上更新创建(find根据short-name查找container,
    getattr获取container下的node, 遍历node下指定tag的成员变量获取寻找的配置)
    """
    parent_path = f"{prefix}/{module_name}_ib_bswmd/BswModuleDescriptions/{module_name}"
    bsw_module_entry_ref = f"{prefix}/{module_name}_ib_bswmd/BswModuleDescriptions/{bsw_module_entry_ref}"
    if ib_autosar is None:
        return
    find_container = ib_autosar.find(parent_path)
    if find_container is None:
        return
    parent_container = getattr(find_container, "PROVIDED_ENTRYS", None)
    if parent_container is None:
        return
    if not isinstance(parent_container.BSW_MODULE_ENTRY_REF_CONDITIONAL, list):
        return

    for entry_ref_conditional in parent_container.BSW_MODULE_ENTRY_REF_CONDITIONAL:
        entry_ref = getattr(entry_ref_conditional, "BSW_MODULE_ENTRY_REF", None)
        if getattr(entry_ref, "valueOf_", "").split("/")[-1] == bsw_module_entry_ref.split("/")[-1]:
            return entry_ref_conditional

    container_value = autosar44.BSW_MODULE_ENTRY_REF_CONDITIONAL()
    container_value.set_tag("BSW-MODULE-ENTRY-REF-CONDITIONAL")
    container_value.set_parent(parent_container)

    bsw_module_entry_ref_container = autosar44.BSW_MODULE_ENTRY_REFType450()
    bsw_module_entry_ref_container.set_tag("BSW-MODULE-ENTRY-REF")
    bsw_module_entry_ref_container.set_parent(container_value)
    bsw_module_entry_ref_container.DEST = "BSW-MODULE-ENTRY"
    bsw_module_entry_ref_container.valueOf_ = bsw_module_entry_ref
    container_value.BSW_MODULE_ENTRY_REF = bsw_module_entry_ref_container

    parent_container.BSW_MODULE_ENTRY_REF_CONDITIONAL.append(container_value)
    return container_value


def create_bsw_schedulable_entity(ib_autosar, module_name, short_name, implemented_entry_ref=None, prefix="/AUTOSAR"):
    """
    描述: 此接口用于检查模块对应的ib文件中BSW-SCHEDULABLE-ENTITY类型对象并创建添加至ib对象
    """
    """
    入参：
    ib_autosar: bsw模块的ib arxml的autosar对象
    module_name: bsw模块
    short_name: tag==BSW-SCHEDULABLE-ENTITY的container对象的short_name
    implemented_entry_ref: tag==BSW-SCHEDULABLE-ENTITY的container对象的IMPLEMENTED-ENTRY-REF的属性值
    """
    parent_path = f"{prefix}/{module_name}_ib_bswmd/BswModuleDescriptions/{module_name}/{module_name}Behavior"
    if implemented_entry_ref is None:
        implemented_entry_ref = f"{prefix}/{module_name}_ib_bswmd/BswModuleDescriptions/{short_name}"
    else:
        implemented_entry_ref = f"{prefix}/{module_name}_ib_bswmd/BswModuleDescriptions/{implemented_entry_ref}"
    if ib_autosar is None:
        return
    find_container = ib_autosar.find(parent_path)
    entitys_container = getattr(find_container, "ENTITYS", None)
    if entitys_container is None:
        return
    container_value = autosar44.BSW_SCHEDULABLE_ENTITY()
    container_value.set_tag("BSW-SCHEDULABLE-ENTITY")
    container_value.set_parent(entitys_container)

    implemented_entry_ref_container = autosar44.IMPLEMENTED_ENTRY_REFType()
    implemented_entry_ref_container.set_tag("IMPLEMENTED-ENTRY-REF")
    implemented_entry_ref_container.DEST = "BSW-MODULE-ENTRY"
    implemented_entry_ref_container.set_parent(container_value)
    implemented_entry_ref_container.valueOf_ = implemented_entry_ref
    container_value.IMPLEMENTED_ENTRY_REF = implemented_entry_ref_container
    set_short_name(container_value, short_name)
    entitys_container.BSW_SCHEDULABLE_ENTITY.append(container_value)
    return container_value


def create_bsw_timing_event(ib_autosar, module_name, short_name, starts_on_event_ref, period_s, prefix="/AUTOSAR"):
    """
    描述: 此接口用于检查模块对应的ib文件中BSW-TIMING-EVENT类型对象并创建添加至ib对象
    """
    """
    入参：
    ib_autosar: bsw模块的ib arxml的autosar对象
    module_name: bsw模块
    short_name: tag==BSW-TIMING-EVENT的container对象的short_name
    starts_on_event_ref: tag==BSW-TIMING-EVENT的container对象的STARTS-ON-EVENT-REF的属性值
    period_s: tag==BSW-TIMING-EVENT的container对象的运行实体调用周期属性值
    """
    parent_path = f"{prefix}/{module_name}_ib_bswmd/BswModuleDescriptions/{module_name}/{module_name}Behavior"
    if starts_on_event_ref is None:
        starts_on_event_ref = f"{parent_path}/{short_name}"
    else:
        starts_on_event_ref = f"{parent_path}/{starts_on_event_ref}"
    if ib_autosar is None:
        return
    find_container = ib_autosar.find(parent_path)
    events_container = getattr(find_container, "EVENTS", None)
    if events_container is None:
        return
    container_value = autosar44.BSW_TIMING_EVENT()
    container_value.set_tag("BSW-TIMING-EVENT")
    container_value.set_parent(events_container)

    starts_on_event_ref_container = autosar44.STARTS_ON_EVENT_REFType510()
    starts_on_event_ref_container.set_tag("STARTS-ON-EVENT-REF")
    starts_on_event_ref_container.DEST = "BSW-SCHEDULABLE-ENTITY"
    starts_on_event_ref_container.set_parent(container_value)
    starts_on_event_ref_container.valueOf_ = starts_on_event_ref
    container_value.STARTS_ON_EVENT_REF = starts_on_event_ref_container

    period_node = autosar44.TIME_VALUE()
    period_node.valueOf_ = str(period_s)
    period_node.set_parent(container_value)
    container_value.PERIOD = period_node

    set_short_name(container_value, short_name)
    events_container.BSW_TIMING_EVENT.append(container_value)
    return container_value


def create_bsw_module_entry(
    ib_autosar, module_name, short_name, call_type="SCHEDULED", execution_context="TASK", prefix="/AUTOSAR"
):
    """
    描述: 此接口用于检查模块对应的ib文件中的BSW_MODULE_ENTRY对象并创建添加至ib对象
    """
    """
    入参：
    ib_autosar: bsw模块的ib arxml的autosar对象
    module_name: bsw模块
    short_name: tag==BSW_MODULE_ENTRY的container对象的short_name
    call_type: tag==BSW_MODULE_ENTRY的container对象的调用类型call-type属性值
    execution_context: tag==BSW_MODULE_ENTRY的container对象的执行上下文execution-context属性值
    """
    parent_path = f"{prefix}/{module_name}_ib_bswmd/BswModuleDescriptions"
    if ib_autosar is None:
        return
    find_container = ib_autosar.find(parent_path)
    parent_container = getattr(find_container, "ELEMENTS", None)
    if parent_container is None:
        return
    container_value = autosar44.BSW_MODULE_ENTRY()
    container_value.set_tag("BSW-MODULE-ENTRY")
    container_value.set_parent(parent_container)

    call_type_container = autosar44.BSW_CALL_TYPE()
    call_type_container.set_tag("CALL-TYPE")
    call_type_container.set_parent(container_value)
    call_type_container.valueOf_ = call_type
    container_value.CALL_TYPE = call_type_container

    execution_context_container = autosar44.BSW_EXECUTION_CONTEXT()
    execution_context_container.set_tag("EXECUTION-CONTEXT")
    execution_context_container.set_parent(container_value)
    execution_context_container.valueOf_ = execution_context
    container_value.EXECUTION_CONTEXT = execution_context_container

    set_short_name(container_value, short_name)
    parent_container.BSW_MODULE_ENTRY.append(container_value)
    return container_value


def delete_ib_container(rte_ib, tag, delete_short_name):
    """
    用于有short name的容器
    """
    find_list = rte_ib.find_nodes(tag)
    for find_container in find_list:
        short_name = get_short_name(find_container)
        if short_name != delete_short_name:
            continue
        parent = AutosarUtil.get_parent(find_container)
        if parent is None:
            continue
        remove_list = getattr(parent, tag.replace("-", "_"), None)
        if not isinstance(remove_list, list):
            continue
        AutosarUtil.remove_container_value(remove_list, find_container)


def delete_ib_container_with_prefix(rte_ib, tag, delete_short_name_prefix):
    """
    用于有short name的容器
    """
    find_list = rte_ib.find_nodes(tag)
    for find_container in find_list:
        short_name = get_short_name(find_container)
        if not (short_name and short_name.startswith(delete_short_name_prefix)):
            continue
        parent = AutosarUtil.get_parent(find_container)
        if parent is None:
            continue
        remove_list = getattr(parent, tag.replace("-", "_"), None)
        if not isinstance(remove_list, list):
            continue
        AutosarUtil.remove_container_value(remove_list, find_container)


def delete_ib_node(rte_ib, node_tag, delete_ref_name):
    """
    描述: 此接口用于删除指定标签tag的配置项，以下支持了tag==BSW-MODULE-ENTRY-REF-CONDITIONAL，可补充其它tag，
    比如BSW-SCHEDULABLE-ENTITY
    """
    """
    入参：
    rte_ib: bsw模块的ib arxml的autosar对象
    node_tag: 指定类型的配置项tag标签，比如BSW-MODULE-ENTRY-REF-CONDITIONAL
    delete_ref_name: 需要删除配置的VALUE
    """
    if node_tag == "BSW-MODULE-ENTRY-REF-CONDITIONAL":
        find_list = rte_ib.find_nodes(node_tag)
        for find_node in find_list:
            ref_node = getattr(find_node, "BSW_MODULE_ENTRY_REF", None)
            ref_value = getattr(ref_node, "valueOf_", None)
            if not isinstance(ref_value, str):
                continue
            if ref_value.split("/")[-1] != delete_ref_name:
                continue
            parent = AutosarUtil.get_parent(find_node)
            if parent is None:
                continue
            remove_list = getattr(parent, "BSW_MODULE_ENTRY_REF_CONDITIONAL", None)
            if not isinstance(remove_list, list):
                continue
            AutosarUtil.remove_node_value(remove_list, find_node)


def delete_ib_node_with_prefix(rte_ib, node_tag, delete_ref_name_prefix):
    """
    描述: 此接口用于删除指定标签tag的配置项，以下支持了tag==BSW-MODULE-ENTRY-REF-CONDITIONAL，可补充其它tag，
    比如BSW-SCHEDULABLE-ENTITY
    """
    """
    入参：
    rte_ib: bsw模块的ib arxml的autosar对象
    node_tag: 指定类型的配置项tag标签，比如BSW-MODULE-ENTRY-REF-CONDITIONAL
    delete_ref_name: 需要删除配置的VALUE
    """
    if node_tag == "BSW-MODULE-ENTRY-REF-CONDITIONAL":
        find_list = rte_ib.find_nodes(node_tag)
        for find_node in find_list:
            ref_node = getattr(find_node, "BSW_MODULE_ENTRY_REF", None)
            ref_value = getattr(ref_node, "valueOf_", None)
            if not isinstance(ref_value, str):
                continue
            if not ref_value.split("/")[-1].startswith(delete_ref_name_prefix):
                continue
            parent = AutosarUtil.get_parent(find_node)
            if parent is None:
                continue
            remove_list = getattr(parent, "BSW_MODULE_ENTRY_REF_CONDITIONAL", None)
            if not isinstance(remove_list, list):
                continue
            AutosarUtil.remove_node_value(remove_list, find_node)


def get_parameter_values(container):
    values = []
    if container is None:
        return values
    values += getattr(getattr(container, "PARAMETER_VALUES", None), "ECUC_ADD_INFO_PARAM_VALUE", [])
    values += getattr(getattr(container, "PARAMETER_VALUES", None), "ECUC_NUMERICAL_PARAM_VALUE", [])
    values += getattr(getattr(container, "PARAMETER_VALUES", None), "ECUC_TEXTUAL_PARAM_VALUE", [])
    return values
