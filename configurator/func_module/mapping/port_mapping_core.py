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
import copy
import hashlib
from typing import List
from enum import IntEnum
from openpyxl import Workbook
from basic_func_module.autosar_utils.utils import get_short_name, get_valueOf
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.autosar_utils.autosar_utils import AutosarUtils
from func_module.health_monitor.logger import logger


class PortMappingCore:

    # TODO: rmv "row_item" in this file using a new abstract list of port info coming from Adapter class
    @classmethod
    def get_all_app_ports_dict(cls, asw_autosar_dict, category="all"):
        # 1. category == "all" is include service and not service
        # 2. category == "is_service" include service
        # 3. category == "not_service" include not service
        all_port_dict = {}
        all_port_dict["pports"] = {}
        all_port_dict["rports"] = {}
        auxiliary_data = cls.__pack_asw_auxiliary_data_for_compatibility(asw_autosar_dict)
        pports_dict = cls.__get_all_app_pports_prports_list(asw_autosar_dict, category, auxiliary_data)
        all_port_dict["pports"] = pports_dict
        rports_dict = cls.__get_all_app_rports_prports_list(asw_autosar_dict, category, auxiliary_data)
        all_port_dict["rports"] = rports_dict
        return all_port_dict

    @classmethod
    def get_all_service_ports_dict(cls, asw_autosar_dict):
        all_port_dict = {}
        all_port_dict["pports"] = {}
        all_port_dict["rports"] = {}
        auxiliary_data = cls.__pack_asw_auxiliary_data_for_compatibility(asw_autosar_dict)
        pports_dict = cls.__get_all_service_pports_prports_list(asw_autosar_dict, auxiliary_data)
        all_port_dict["pports"] = pports_dict
        rports_dict = cls.__get_all_service_rports_prports_list(asw_autosar_dict, auxiliary_data)
        all_port_dict["rports"] = rports_dict
        return all_port_dict

    @classmethod
    def get_target_port_info(cls, all_ports, selected_data):
        port_info = {}
        if not selected_data:
            return port_info
        # data length 4: second level table
        # data length 7: third level table
        first_data = next(iter(selected_data))
        swc_index = ST_Index.Component if len(first_data) == 4 else TT_Index.Component
        port_index = ST_Index.Port if len(first_data) == 4 else TT_Index.Port
        for data in selected_data:
            swc_name = data[swc_index]
            port_name = data[port_index]
            swc_port = f"{swc_name}_{port_name}"
            if (
                "pports" in all_ports
                and port_name in all_ports["pports"]
                and swc_port in all_ports["pports"][port_name]
            ):
                port_info[swc_port] = all_ports["pports"][port_name][swc_port]
            elif (
                "rports" in all_ports
                and port_name in all_ports["rports"]
                and swc_port in all_ports["rports"][port_name]
            ):
                port_info[swc_port] = all_ports["rports"][port_name][swc_port]
        return port_info

    @classmethod
    def get_port_to_connect_dict(cls, all_app_swc_port_dict, port_src_info, port_direction):
        port_display_dict = {}
        if port_direction == "R-Port":
            port_display_dict = cls.__get_pport_display_dict(all_app_swc_port_dict, port_src_info)
        elif port_direction == "P-Port":
            port_display_dict = cls.__get_rport_display_dict(all_app_swc_port_dict, port_src_info)
        elif port_direction == "PR-Port":
            pport_display_dict = cls.__get_pport_display_dict(all_app_swc_port_dict, port_src_info)
            rport_display_dict = cls.__get_rport_display_dict(all_app_swc_port_dict, port_src_info)
            port_display_dict = {**pport_display_dict, **rport_display_dict}
        else:
            # TODO
            pass
        return port_display_dict

    @classmethod
    def get_filtering_args(cls, component_port_set=set(), direction_src=None):
        return _MappingFilterArgument(component_port_set=component_port_set, direction=direction_src)

    @classmethod
    def update_data_after_port_mapping(cls, new_port_mappings_list: List, flat_extract_autosar_class):
        AutosarUtil.save_assembly_sw_connector(flat_extract_autosar_class, new_port_mappings_list)

    @classmethod
    def __get_all_service_pports_prports_list(cls, service_autosar_class, auxiliary_data):
        pport_list = {}
        if not service_autosar_class:
            return pport_list
        sw_component_types = []
        for comp_type in AutosarUtils.SUPPORT_SERVICE_COMPONENT_TYPE:
            sw_component_types += service_autosar_class.find_nodes(comp_type)
        for sw_component_type in sw_component_types:
            cls.parse_sw_component_type(
                pport_list, service_autosar_class, sw_component_type, "all", auxiliary_data, "P"
            )
        return pport_list

    @classmethod
    def __get_all_service_rports_prports_list(cls, service_autosar_class, auxiliary_data):
        rport_list = {}
        if not service_autosar_class:
            return rport_list
        sw_component_types = []
        for comp_type in AutosarUtils.SUPPORT_SERVICE_COMPONENT_TYPE:
            sw_component_types += service_autosar_class.find_nodes(comp_type)
        for sw_component_type in sw_component_types:
            cls.parse_sw_component_type(
                rport_list, service_autosar_class, sw_component_type, "all", auxiliary_data, "R"
            )
        return rport_list

    @staticmethod
    def __get_all_api_options(componenttype):
        port_api_options_list = []
        port_api_options = componenttype.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR[0].PORT_API_OPTIONS.PORT_API_OPTION
        for port_api_option in port_api_options:
            port_ref = port_api_option.PORT_REF.valueOf_
            port_api_options_list.append(port_ref)
        return port_api_options_list

    @classmethod
    def __get_pport_display_dict(cls, all_app_swc_port_dict, port_src_info=None):
        pports_display_dict = {}
        pports = all_app_swc_port_dict.get("pports", {})
        for pport_value in pports.values():
            for pport in pport_value.values():
                if cls.__get_connected_status(pport, port_src_info):
                    continue
                if cls.__is_same_component(pport, port_src_info):
                    continue
                component_port = pport["Component"] + "_" + pport["Name"]
                pports_display_dict.update({component_port: {}})
                placeholder = " "
                Compatibility = cls.__get_compatibility(pport, port_src_info)  # TODO
                Component_Prototype = pport["Component"]
                Port_Prototype = pport["Name"]
                Port_Interface = pport["Interface"].split("/")[-1]
                Port_Interface_Mapping = "-"
                Port_Interface_Mapping_Set = "-"
                pports_display_dict[component_port] = [
                    placeholder,
                    Compatibility,
                    Component_Prototype,
                    Port_Prototype,
                    Port_Interface,
                    Port_Interface_Mapping,
                    Port_Interface_Mapping_Set,
                ]
        return pports_display_dict

    @classmethod
    def __get_rport_display_dict(cls, all_app_swc_port_dict, port_src_info=None):
        rports_display_dict = {}
        rports = all_app_swc_port_dict["rports"]
        for rport_value in rports.values():
            for rport in rport_value.values():
                if cls.__get_connected_status(rport, port_src_info):
                    continue
                if cls.__is_same_component(rport, port_src_info):
                    continue
                component_port = rport["Component"] + "_" + rport["Name"]
                rports_display_dict.update({component_port: {}})
                placeholder = " "
                Compatibility = cls.__get_compatibility(rport, port_src_info)  # TODO
                Component_Prototype = rport["Component"]
                Port_Prototype = rport["Name"]
                Port_Interface = rport["Interface"].split("/")[-1]
                Port_Interface_Mapping = "-"
                Port_Interface_Mapping_Set = "-"
                rports_display_dict[component_port] = [
                    placeholder,
                    Compatibility,
                    Component_Prototype,
                    Port_Prototype,
                    Port_Interface,
                    Port_Interface_Mapping,
                    Port_Interface_Mapping_Set,
                ]
        return rports_display_dict

    @classmethod
    def __get_connected_status(cls, port, port_src_info):
        row_item = list(port_src_info.values())[0]
        if (
            row_item[MT_Index.Conn_Component] == port["Component"]
            and row_item[MT_Index.Conn_Port] == port["Name"]
            and row_item[MT_Index.Conn_Port_Interface] == port["Interface"].split("/")[-1]
        ):
            return True
        return False

    @classmethod
    def __get_compatibility(cls, port, port_src_info):
        score = 0
        for _, row_item in port_src_info.items():
            if row_item[MT_Index.Port_Interface] == port["Interface"].split("/")[-1]:
                # rule1: Port Interface相同 +500
                score += 500
                # Port Interface相同时，继续判断Port名是否相同
                if row_item[MT_Index.Port] == port["Name"]:
                    # rule2: Port相同 +500
                    score += 500
                elif row_item[MT_Index.Port].lower() == port["Name"].lower():
                    # rule3: rule3: Port不考虑字母大小写 -100
                    score -= 100
                elif (
                    row_item[MT_Index.Port].lower() in port["Name"].lower()
                    or port["Name"].lower() in row_item[MT_Index.Port].lower()
                ):
                    # rule4: Port不考虑全词匹配 -100
                    score -= 100
                else:
                    # TODO
                    pass
            else:
                break
                # TODO
                # 待添加区分Port Interface是否兼容
        score = 0 if score < 0 else score
        return str(score)

    @classmethod
    def __get_all_app_pports_prports_list(cls, asw_autosar_class=None, category="all", auxiliary_data={}):
        pport_list = {}
        if not asw_autosar_class:
            return pport_list
        sw_component_types = []
        for comp_type in AutosarUtils.SUPPORT_APPL_COMPONENT_TYPE:
            sw_component_types += asw_autosar_class.find_nodes(comp_type)
        for sw_component_type in sw_component_types:
            cls.parse_sw_component_type(pport_list, asw_autosar_class, sw_component_type, category, auxiliary_data, "P")
        return pport_list

    @classmethod
    def __pack_asw_auxiliary_data_for_compatibility(cls, asw_autosar_class):
        auxiliary_data = {}
        AutosarUtils.get_idts_for_compatibility(asw_autosar_class)
        AutosarUtils.parse_datatype_mapping_sets_for_compatibility(asw_autosar_class)
        AutosarUtils.get_all_constraints_for_compatibility(asw_autosar_class)
        all_swc_prototypes = AutosarUtils.get_all_sw_component_prototypes(asw_autosar_class)
        all_port_arg_in_runnable = cls.get_all_port_arg_in_runnable(asw_autosar_class, all_swc_prototypes)
        auxiliary_data.update(
            {
                "asw_class": asw_autosar_class,
                "all_port_arg_in_runnable": all_port_arg_in_runnable,
                "all_swc_prototypes": all_swc_prototypes,
            }
        )
        return auxiliary_data

    @classmethod
    def get_all_port_arg_in_runnable(cls, asw_autosar_class, all_swc_prototypes):
        rv = {}
        sw_component_types = []
        for comp_type in AutosarUtils.SUPPORT_COMPONENT_TYPE:
            sw_component_types += asw_autosar_class.find_nodes(comp_type)
        for sw_component_type in sw_component_types:
            swc_name = get_short_name(sw_component_type)
            base_swc_name = get_short_name(sw_component_type)
            swc_name = all_swc_prototypes[base_swc_name][0] if base_swc_name in all_swc_prototypes else base_swc_name
            rv.update({swc_name: {"pports": {}, "rports": {}}})
            rv[swc_name]["pports"] = cls.get_all_pport_arg_in_runnable(sw_component_type)
            rv[swc_name]["rports"] = cls.get_all_rport_arg_in_runnable(sw_component_type)
        return rv

    @classmethod
    def get_all_pport_arg_in_runnable(cls, sw_component_type):
        """
        判断pport中的arg是否关联runnable
        """
        rv = {}
        if not sw_component_type.PORTS:
            return rv
        if not hasattr(sw_component_type, "INTERNAL_BEHAVIORS"):
            return rv
        for behavior in sw_component_type.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR:
            if behavior.EVENTS and len(behavior.EVENTS.OPERATION_INVOKED_EVENT) > 0:
                for op_event in behavior.EVENTS.OPERATION_INVOKED_EVENT:
                    data_ref = get_valueOf(op_event.OPERATION_IREF.TARGET_PROVIDED_OPERATION_REF)
                    port_ref = get_valueOf(op_event.OPERATION_IREF.CONTEXT_P_PORT_REF)
                    if port_ref not in rv:
                        rv[port_ref] = []
                    rv[port_ref].append(data_ref)
            if behavior.RUNNABLES:
                for runnable_entity in behavior.RUNNABLES.RUNNABLE_ENTITY:
                    if runnable_entity.DATA_SEND_POINTS:
                        for access_point in runnable_entity.DATA_SEND_POINTS.VARIABLE_ACCESS:
                            data_ref = get_valueOf(
                                access_point.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF.TARGET_DATA_PROTOTYPE_REF
                            )
                            port_ref = get_valueOf(
                                access_point.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF.PORT_PROTOTYPE_REF
                            )
                            if port_ref not in rv:
                                rv[port_ref] = []
                            rv[port_ref].append(data_ref)
                    if runnable_entity.DATA_WRITE_ACCESSS:
                        for access_point in runnable_entity.DATA_WRITE_ACCESSS.VARIABLE_ACCESS:
                            data_ref = get_valueOf(
                                access_point.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF.TARGET_DATA_PROTOTYPE_REF
                            )
                            port_ref = get_valueOf(
                                access_point.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF.PORT_PROTOTYPE_REF
                            )
                            if port_ref not in rv:
                                rv[port_ref] = []
                            rv[port_ref].append(data_ref)
        return rv

    @classmethod
    def get_all_rport_arg_in_runnable(cls, sw_component_type):
        """
        判断rport中的arg是否关联runnable
        """
        rv = {}
        if not sw_component_type.PORTS:
            return rv
        if not hasattr(sw_component_type, "INTERNAL_BEHAVIORS"):
            return rv
        for behavior in sw_component_type.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR:
            if behavior.RUNNABLES:
                for runnable_entity in behavior.RUNNABLES.RUNNABLE_ENTITY:
                    if runnable_entity.SERVER_CALL_POINTS:
                        for access_point in runnable_entity.SERVER_CALL_POINTS.SYNCHRONOUS_SERVER_CALL_POINT:
                            data_ref = get_valueOf(access_point.OPERATION_IREF.TARGET_REQUIRED_OPERATION_REF)
                            port_ref = get_valueOf(access_point.OPERATION_IREF.CONTEXT_R_PORT_REF)
                            if port_ref not in rv:
                                rv[port_ref] = []
                            rv[port_ref].append(data_ref)
                        for access_point in runnable_entity.SERVER_CALL_POINTS.ASYNCHRONOUS_SERVER_CALL_POINT:
                            data_ref = get_valueOf(access_point.OPERATION_IREF.TARGET_REQUIRED_OPERATION_REF)
                            port_ref = get_valueOf(access_point.OPERATION_IREF.CONTEXT_R_PORT_REF)
                            if port_ref not in rv:
                                rv[port_ref] = []
                            rv[port_ref].append(data_ref)
                    if runnable_entity.DATA_RECEIVE_POINT_BY_ARGUMENTS:
                        for access_point in runnable_entity.DATA_RECEIVE_POINT_BY_ARGUMENTS.VARIABLE_ACCESS:
                            data_ref = get_valueOf(
                                access_point.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF.TARGET_DATA_PROTOTYPE_REF
                            )
                            port_ref = get_valueOf(
                                access_point.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF.PORT_PROTOTYPE_REF
                            )
                            if port_ref not in rv:
                                rv[port_ref] = []
                            rv[port_ref].append(data_ref)
                    if runnable_entity.DATA_RECEIVE_POINT_BY_VALUES:
                        for access_point in runnable_entity.DATA_RECEIVE_POINT_BY_VALUES.VARIABLE_ACCESS:
                            data_ref = get_valueOf(
                                access_point.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF.TARGET_DATA_PROTOTYPE_REF
                            )
                            port_ref = get_valueOf(
                                access_point.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF.PORT_PROTOTYPE_REF
                            )
                            if port_ref not in rv:
                                rv[port_ref] = []
                            rv[port_ref].append(data_ref)
                    if runnable_entity.DATA_READ_ACCESSS:
                        for access_point in runnable_entity.DATA_READ_ACCESSS.VARIABLE_ACCESS:
                            data_ref = get_valueOf(
                                access_point.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF.TARGET_DATA_PROTOTYPE_REF
                            )
                            port_ref = get_valueOf(
                                access_point.ACCESSED_VARIABLE.AUTOSAR_VARIABLE_IREF.PORT_PROTOTYPE_REF
                            )
                            if port_ref not in rv:
                                rv[port_ref] = []
                            rv[port_ref].append(data_ref)
        return rv

    @classmethod
    def parse_sw_component_type(
        cls, port_list, asw_autosar_class, sw_component_type, category, auxiliary_data, direction
    ):
        mapping_sets = []
        sw_component_prototye = AutosarUtils.get_sw_component_prototype(asw_autosar_class)
        ports_obj = sw_component_type.PORTS
        if ports_obj:
            if direction == "P":
                pport_prototype_list = []
                pport_prototype_list += ports_obj.P_PORT_PROTOTYPE
                pport_prototype_list += ports_obj.PR_PORT_PROTOTYPE
                if pport_prototype_list:
                    if hasattr(sw_component_type, "INTERNAL_BEHAVIORS"):
                        for behavior in sw_component_type.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR:
                            if behavior.DATA_TYPE_MAPPING_REFS:
                                for mapping_set in behavior.DATA_TYPE_MAPPING_REFS.DATA_TYPE_MAPPING_REF:
                                    mapping_sets.append(mapping_set.valueOf_)
                    for pport_prototype in pport_prototype_list:
                        if (
                            pport_prototype.PROVIDED_COM_SPECS and pport_prototype.PROVIDED_COM_SPECS.SERVER_COM_SPEC
                        ) or (not pport_prototype.PROVIDED_COM_SPECS):
                            # SERVER
                            cls.parse_all_pports(
                                port_list,
                                pport_prototype,
                                sw_component_type,
                                sw_component_prototye,
                                category,
                                mapping_sets,
                                auxiliary_data,
                            )
                        elif pport_prototype.PROVIDED_COM_SPECS and (
                            pport_prototype.PROVIDED_COM_SPECS.NONQUEUED_SENDER_COM_SPEC
                            or pport_prototype.PROVIDED_COM_SPECS.QUEUED_SENDER_COM_SPEC
                        ):
                            # SENDER
                            cls.parse_all_pports(
                                port_list,
                                pport_prototype,
                                sw_component_type,
                                sw_component_prototye,
                                category,
                                mapping_sets,
                                auxiliary_data,
                            )
                        elif (
                            pport_prototype.PROVIDED_COM_SPECS
                            and pport_prototype.PROVIDED_COM_SPECS.MODE_SWITCH_SENDER_COM_SPEC
                        ):
                            # MODE SWITCH
                            cls.parse_all_pports(
                                port_list,
                                pport_prototype,
                                sw_component_type,
                                sw_component_prototye,
                                category,
                                mapping_sets,
                                auxiliary_data,
                            )
                        elif (
                            pport_prototype.PROVIDED_COM_SPECS
                            and pport_prototype.PROVIDED_COM_SPECS.NV_PROVIDE_COM_SPEC
                        ):
                            # NV DATA
                            cls.parse_all_pports(
                                port_list,
                                pport_prototype,
                                sw_component_type,
                                sw_component_prototye,
                                category,
                                mapping_sets,
                                auxiliary_data,
                            )
                        elif (
                            pport_prototype.PROVIDED_COM_SPECS
                            and pport_prototype.PROVIDED_COM_SPECS.PARAMETER_PROVIDE_COM_SPEC
                        ):
                            # parameter
                            cls.parse_all_pports(
                                port_list,
                                pport_prototype,
                                sw_component_type,
                                sw_component_prototye,
                                category,
                                mapping_sets,
                                auxiliary_data,
                            )
            else:
                rport_prototype_list = []
                rport_prototype_list += ports_obj.R_PORT_PROTOTYPE
                rport_prototype_list += ports_obj.PR_PORT_PROTOTYPE
                if rport_prototype_list:
                    if hasattr(sw_component_type, "INTERNAL_BEHAVIORS"):
                        for behavior in sw_component_type.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR:
                            if behavior.DATA_TYPE_MAPPING_REFS:
                                for mapping_set in behavior.DATA_TYPE_MAPPING_REFS.DATA_TYPE_MAPPING_REF:
                                    mapping_sets.append(mapping_set.valueOf_)
                    for rport_prototype in rport_prototype_list:
                        if (
                            rport_prototype.REQUIRED_COM_SPECS and rport_prototype.REQUIRED_COM_SPECS.CLIENT_COM_SPEC
                        ) or (not rport_prototype.REQUIRED_COM_SPECS):
                            # CLIENT
                            cls.parse_all_rports(
                                port_list,
                                rport_prototype,
                                sw_component_type,
                                sw_component_prototye,
                                category,
                                mapping_sets,
                                auxiliary_data,
                            )
                        elif rport_prototype.REQUIRED_COM_SPECS and (
                            rport_prototype.REQUIRED_COM_SPECS.NONQUEUED_RECEIVER_COM_SPEC
                            or rport_prototype.REQUIRED_COM_SPECS.QUEUED_RECEIVER_COM_SPEC
                        ):
                            # RECEIVER
                            cls.parse_all_rports(
                                port_list,
                                rport_prototype,
                                sw_component_type,
                                sw_component_prototye,
                                category,
                                mapping_sets,
                                auxiliary_data,
                            )
                        elif (
                            rport_prototype.REQUIRED_COM_SPECS
                            and rport_prototype.REQUIRED_COM_SPECS.MODE_SWITCH_RECEIVER_COM_SPEC
                        ):
                            # MODE SWITCH
                            cls.parse_all_rports(
                                port_list,
                                rport_prototype,
                                sw_component_type,
                                sw_component_prototye,
                                category,
                                mapping_sets,
                                auxiliary_data,
                            )
                        elif (
                            rport_prototype.REQUIRED_COM_SPECS
                            and rport_prototype.REQUIRED_COM_SPECS.NV_REQUIRE_COM_SPEC
                        ):
                            # NV DATA
                            cls.parse_all_rports(
                                port_list,
                                rport_prototype,
                                sw_component_type,
                                sw_component_prototye,
                                category,
                                mapping_sets,
                                auxiliary_data,
                            )
                        elif (
                            rport_prototype.REQUIRED_COM_SPECS
                            and rport_prototype.REQUIRED_COM_SPECS.PARAMETER_REQUIRE_COM_SPEC
                        ):
                            # parameter
                            cls.parse_all_rports(
                                port_list,
                                rport_prototype,
                                sw_component_type,
                                sw_component_prototye,
                                category,
                                mapping_sets,
                                auxiliary_data,
                            )

    @classmethod
    def parse_all_pports(
        cls,
        pport_list,
        pport_prototype,
        sw_component_type,
        sw_component_prototye,
        category,
        mapping_sets,
        auxiliary_data,
    ):
        port_name = get_short_name(pport_prototype)
        port_path = pport_prototype.get_path()
        base_swc_name = get_short_name(sw_component_type)
        # 暂时不支持多实例，取第0个
        swc_name = (
            auxiliary_data["all_swc_prototypes"][base_swc_name][0]
            if base_swc_name in auxiliary_data["all_swc_prototypes"]
            else base_swc_name
        )

        port = {
            "Tag": "pr" if "PR-PORT" in pport_prototype.original_tagname_ else "p",
            "Name": port_name,
            "Component": swc_name,
            "Interface": None,
            "Interface_type": None,
            "Port Interface Mapping": None,
            "Port Interface Mapping Set": None,
            "CONTEXT-COMPONENT-REF": None,
            "TARGET-P-PORT-REF": None,
            "id_port_map": swc_name + "_" + port_name,
            "Is_service": None,
        }

        if port["Tag"] == "pr":
            if pport_prototype.PROVIDED_REQUIRED_INTERFACE_TREF:
                port["Interface"] = pport_prototype.PROVIDED_REQUIRED_INTERFACE_TREF.valueOf_
        else:
            if pport_prototype.PROVIDED_INTERFACE_TREF:
                port["Interface"] = pport_prototype.PROVIDED_INTERFACE_TREF.valueOf_

        if not port["Interface"]:
            logger.error(f"the interface of {swc_name}/{port_name} has no interface!")
        else:
            if pport_prototype.find(port["Interface"]):
                port["Interface_type"] = pport_prototype.find(port["Interface"]).original_tagname_
                port["Is_service"] = (
                    pport_prototype.find(port["Interface"]).IS_SERVICE.valueOf_
                    if pport_prototype.find(port["Interface"]).IS_SERVICE
                    else "false"
                )
            else:
                logger.error(f'interface path:{port["Interface"]} can not be found!')

        if (
            sw_component_type.original_tagname_ not in AutosarUtils.SUPPORT_APPL_COMPONENT_TYPE
            and swc_name not in sw_component_prototye
        ):
            # service component
            port_api_options = cls.__get_all_api_options(sw_component_type)
            for port_api_option in port_api_options:
                if port_name != port_api_option.split("/")[-1]:
                    continue
                port["CONTEXT-COMPONENT-REF"] = port_api_option.replace(("/" + port_name), "")
                port["TARGET-P-PORT-REF"] = port_api_option
        else:
            # application component
            if swc_name in sw_component_prototye:
                port["CONTEXT-COMPONENT-REF"] = sw_component_prototye[swc_name]["CONTEXT-COMPONENT-REF"]
                port["TARGET-P-PORT-REF"] = (
                    sw_component_prototye[swc_name]["type_tref"] + "/" + get_short_name(pport_prototype)
                )
            else:
                port["CONTEXT-COMPONENT-REF"] = sw_component_type.get_path()
                port["TARGET-P-PORT-REF"] = pport_prototype.get_path()

        if port["Interface_type"] == "CLIENT-SERVER-INTERFACE":
            port.update({"args": {}})
            if pport_prototype.PROVIDED_COM_SPECS:
                for server_com_spec in pport_prototype.PROVIDED_COM_SPECS.SERVER_COM_SPEC:
                    if not server_com_spec.OPERATION_REF:
                        continue
                    operation_path = server_com_spec.OPERATION_REF.valueOf_
                    operation_name = operation_path.split("/")[-1]
                    args = copy.deepcopy(
                        AutosarUtils.parse_operation_for_compatibility(pport_prototype, operation_path)
                    )
                    port["args"].update({operation_name: args})
                    if args:
                        for arg, value in port["args"][operation_name].items():
                            port["args"][operation_name][arg].update(
                                {"de_basetype": AutosarUtils.get_arg_base_type(value["type"])}
                            )
                            port["args"][operation_name][arg].update(
                                {
                                    "map_runnable": operation_path
                                    in auxiliary_data["all_port_arg_in_runnable"][swc_name]["pports"].get(port_path, [])
                                }
                            )
            else:
                for operation in pport_prototype.find(port["Interface"]).OPERATIONS.CLIENT_SERVER_OPERATION:
                    operation_path = operation.get_path()
                    operation_name = get_short_name(operation)
                    args = copy.deepcopy(
                        AutosarUtils.parse_operation_for_compatibility(pport_prototype, operation_path)
                    )
                    port["args"].update({operation_name: args})
                    if args:
                        for arg, value in port["args"][operation_name].items():
                            port["args"][operation_name][arg].update(
                                {"de_basetype": AutosarUtils.get_arg_base_type(value["type"])}
                            )
                            port["args"][operation_name][arg].update(
                                {
                                    "map_runnable": operation_path
                                    in auxiliary_data["all_port_arg_in_runnable"][swc_name]["pports"].get(port_path, [])
                                }
                            )
        elif port["Interface_type"] == "SENDER-RECEIVER-INTERFACE":
            port.update({"args": {}})
            for sender_com_spec in pport_prototype.PROVIDED_COM_SPECS.NONQUEUED_SENDER_COM_SPEC:
                if not sender_com_spec.DATA_ELEMENT_REF:
                    continue
                data_element_path = sender_com_spec.DATA_ELEMENT_REF.valueOf_
                data_element = pport_prototype.find(data_element_path)
                element_name = data_element_path.split("/")[-1]
                args = copy.deepcopy(
                    AutosarUtils.parse_de_for_compatibility(data_element, pport_prototype, mapping_sets, auxiliary_data)
                )
                port["args"].update({element_name: args})
                if args:
                    port["args"][element_name]["datatype"].update(
                        {"de_basetype": AutosarUtils.get_arg_base_type(args["datatype"]["name"])}
                    )
                    port["args"][element_name]["datatype"].update(
                        {
                            "map_runnable": data_element_path
                            in auxiliary_data["all_port_arg_in_runnable"][swc_name]["pports"].get(port_path, [])
                        }
                    )
            for sender_com_spec in pport_prototype.PROVIDED_COM_SPECS.QUEUED_SENDER_COM_SPEC:
                if not sender_com_spec.DATA_ELEMENT_REF:
                    continue
                data_element_path = sender_com_spec.DATA_ELEMENT_REF.valueOf_
                data_element = pport_prototype.find(data_element_path)
                element_name = data_element_path.split("/")[-1]
                args = copy.deepcopy(
                    AutosarUtils.parse_de_for_compatibility(data_element, pport_prototype, mapping_sets, auxiliary_data)
                )
                port["args"].update({element_name: args})
                if args:
                    port["args"][element_name]["datatype"].update(
                        {"de_basetype": AutosarUtils.get_arg_base_type(args["datatype"]["name"])}
                    )
                    port["args"][element_name]["datatype"].update(
                        {
                            "map_runnable": data_element_path
                            in auxiliary_data["all_port_arg_in_runnable"][swc_name]["pports"].get(port_path, [])
                        }
                    )
        elif port["Interface_type"] == "MODE-SWITCH-INTERFACE":
            pass
        elif port["Interface_type"] == "NV-DATA-INTERFACE":
            port.update({"args": {}})
            for sender_com_spec in pport_prototype.PROVIDED_COM_SPECS.NV_PROVIDE_COM_SPEC:
                if not sender_com_spec.VARIABLE_REF:
                    continue
                data_element_path = sender_com_spec.VARIABLE_REF.valueOf_
                data_element = pport_prototype.find(data_element_path)
                element_name = data_element_path.split("/")[-1]
                args = copy.deepcopy(
                    AutosarUtils.parse_de_for_compatibility(data_element, pport_prototype, mapping_sets, auxiliary_data)
                )
                port["args"].update({element_name: args})
                if args:
                    port["args"][element_name]["datatype"].update(
                        {"de_basetype": AutosarUtils.get_arg_base_type(args["datatype"]["name"])}
                    )
                    port["args"][element_name]["datatype"].update(
                        {
                            "map_runnable": data_element_path
                            in auxiliary_data["all_port_arg_in_runnable"][swc_name]["pports"].get(port_path, [])
                        }
                    )

        if category == "all":
            if port_name not in pport_list:
                pport_list[port_name] = {}
            pport_list[port_name].update({swc_name + "_" + port_name: port})
        elif category == "is_service":
            if port["Is_service"] and port["Is_service"].lower() == "true":
                if port_name not in pport_list:
                    pport_list[port_name] = {}
                pport_list[port_name].update({swc_name + "_" + port_name: port})
        elif category == "not_service":
            if port["Is_service"] and port["Is_service"].lower() == "false":
                if port_name not in pport_list:
                    pport_list[port_name] = {}
                pport_list[port_name].update({swc_name + "_" + port_name: port})

    @classmethod
    def __get_all_app_rports_prports_list(cls, asw_autosar_class=None, category="all", auxiliary_data={}):
        rport_list = {}
        if not asw_autosar_class:
            return rport_list
        sw_component_types = []
        for comp_type in AutosarUtils.SUPPORT_APPL_COMPONENT_TYPE:
            sw_component_types += asw_autosar_class.find_nodes(comp_type)
        for sw_component_type in sw_component_types:
            cls.parse_sw_component_type(rport_list, asw_autosar_class, sw_component_type, category, auxiliary_data, "R")
        return rport_list

    @classmethod
    def parse_all_rports(
        cls,
        rport_list,
        rport_prototype,
        sw_component_type,
        sw_component_prototye,
        category,
        mapping_sets,
        auxiliary_data,
    ):
        port_name = get_short_name(rport_prototype)
        port_path = rport_prototype.get_path()
        base_swc_name = get_short_name(sw_component_type)
        # 暂时不支持多实例，取第0个
        swc_name = (
            auxiliary_data["all_swc_prototypes"][base_swc_name][0]
            if base_swc_name in auxiliary_data["all_swc_prototypes"]
            else base_swc_name
        )

        port = {
            "Tag": "pr" if "PR-PORT" in rport_prototype.original_tagname_ else "r",
            "Name": port_name,
            "Component": swc_name,
            "Interface": None,
            "Interface_type": None,
            "Port Interface Mapping": None,
            "Port Interface Mapping Set": None,
            "CONTEXT-COMPONENT-REF": None,
            "TARGET-R-PORT-REF": None,
            "id_port_map": swc_name + "_" + port_name,
            "Is_service": None,
        }
        if port["Tag"] == "pr":
            if rport_prototype.PROVIDED_REQUIRED_INTERFACE_TREF:
                port["Interface"] = rport_prototype.PROVIDED_REQUIRED_INTERFACE_TREF.valueOf_
        else:
            if rport_prototype.REQUIRED_INTERFACE_TREF:
                port["Interface"] = rport_prototype.REQUIRED_INTERFACE_TREF.valueOf_

        if not port["Interface"]:
            logger.error(f"the interface of {swc_name}/{port_name} has no interface!")
        else:
            if rport_prototype.find(port["Interface"]):
                port["Interface_type"] = rport_prototype.find(port["Interface"]).original_tagname_
                port["Is_service"] = (
                    rport_prototype.find(port["Interface"]).IS_SERVICE.valueOf_
                    if rport_prototype.find(port["Interface"]).IS_SERVICE
                    else "false"
                )
            else:
                logger.error(f'interface path:{port["Interface"]} can not be found!')

        if (
            sw_component_type.original_tagname_ not in AutosarUtils.SUPPORT_APPL_COMPONENT_TYPE
            and swc_name not in sw_component_prototye
        ):
            # service component
            port_api_options = cls.__get_all_api_options(sw_component_type)
            for port_api_option in port_api_options:
                if port_name != port_api_option.split("/")[-1]:
                    continue
                port["CONTEXT-COMPONENT-REF"] = port_api_option.replace(("/" + port_name), "")
                port["TARGET-R-PORT-REF"] = port_api_option
        else:
            # application component
            if swc_name in sw_component_prototye:
                port["CONTEXT-COMPONENT-REF"] = sw_component_prototye[swc_name]["CONTEXT-COMPONENT-REF"]
                port["TARGET-R-PORT-REF"] = (
                    sw_component_prototye[swc_name]["type_tref"] + "/" + get_short_name(rport_prototype)
                )
            else:
                port["CONTEXT-COMPONENT-REF"] = sw_component_type.get_path()
                port["TARGET-R-PORT-REF"] = rport_prototype.get_path()

        if port["Interface_type"] == "CLIENT-SERVER-INTERFACE":
            port.update({"args": {}})
            if rport_prototype.REQUIRED_COM_SPECS:
                for server_com_spec in rport_prototype.REQUIRED_COM_SPECS.CLIENT_COM_SPEC:
                    if not server_com_spec.OPERATION_REF:
                        continue
                    operation_path = server_com_spec.OPERATION_REF.valueOf_
                    operation_name = operation_path.split("/")[-1]
                    args = copy.deepcopy(
                        AutosarUtils.parse_operation_for_compatibility(rport_prototype, operation_path)
                    )
                    port["args"].update({operation_name: args})
                    if args:
                        for arg, value in port["args"][operation_name].items():
                            port["args"][operation_name][arg].update(
                                {"de_basetype": AutosarUtils.get_arg_base_type(value["type"])}
                            )
                            port["args"][operation_name][arg].update(
                                {
                                    "map_runnable": operation_path
                                    in auxiliary_data["all_port_arg_in_runnable"][swc_name]["rports"].get(port_path, [])
                                }
                            )
            else:
                for operation in rport_prototype.find(port["Interface"]).OPERATIONS.CLIENT_SERVER_OPERATION:
                    operation_path = operation.get_path()
                    operation_name = get_short_name(operation)
                    args = copy.deepcopy(
                        AutosarUtils.parse_operation_for_compatibility(rport_prototype, operation_path)
                    )
                    port["args"].update({operation_name: args})
                    if args:
                        for arg, value in port["args"][operation_name].items():
                            port["args"][operation_name][arg].update(
                                {"de_basetype": AutosarUtils.get_arg_base_type(value["type"])}
                            )
                            port["args"][operation_name][arg].update(
                                {
                                    "map_runnable": operation_path
                                    in auxiliary_data["all_port_arg_in_runnable"][swc_name]["rports"].get(port_path, [])
                                }
                            )

        elif port["Interface_type"] == "SENDER-RECEIVER-INTERFACE":
            port.update({"args": {}})
            for sender_com_spec in rport_prototype.REQUIRED_COM_SPECS.NONQUEUED_RECEIVER_COM_SPEC:
                if not sender_com_spec.DATA_ELEMENT_REF:
                    continue
                data_element_path = sender_com_spec.DATA_ELEMENT_REF.valueOf_
                data_element = rport_prototype.find(data_element_path)
                element_name = data_element_path.split("/")[-1]
                args = copy.deepcopy(
                    AutosarUtils.parse_de_for_compatibility(data_element, rport_prototype, mapping_sets, auxiliary_data)
                )
                port["args"].update({element_name: args})
                if args:
                    port["args"][element_name]["datatype"].update(
                        {"de_basetype": AutosarUtils.get_arg_base_type(args["datatype"]["name"])}
                    )
                    port["args"][element_name]["datatype"].update(
                        {
                            "map_runnable": data_element_path
                            in auxiliary_data["all_port_arg_in_runnable"][swc_name]["rports"].get(port_path, [])
                        }
                    )
            for sender_com_spec in rport_prototype.REQUIRED_COM_SPECS.QUEUED_RECEIVER_COM_SPEC:
                if not sender_com_spec.DATA_ELEMENT_REF:
                    continue
                data_element_path = sender_com_spec.DATA_ELEMENT_REF.valueOf_
                data_element = rport_prototype.find(data_element_path)
                element_name = data_element_path.split("/")[-1]
                args = copy.deepcopy(
                    AutosarUtils.parse_de_for_compatibility(data_element, rport_prototype, mapping_sets, auxiliary_data)
                )
                port["args"].update({element_name: args})
                if args:
                    port["args"][element_name]["datatype"].update(
                        {"de_basetype": AutosarUtils.get_arg_base_type(args["datatype"]["name"])}
                    )
                    port["args"][element_name]["datatype"].update(
                        {
                            "map_runnable": data_element_path
                            in auxiliary_data["all_port_arg_in_runnable"][swc_name]["rports"].get(port_path, [])
                        }
                    )
        elif port["Interface_type"] == "MODE-SWITCH-INTERFACE":
            pass
        elif port["Interface_type"] == "NV-DATA-INTERFACE":
            port.update({"args": {}})
            for sender_com_spec in rport_prototype.REQUIRED_COM_SPECS.NV_REQUIRE_COM_SPEC:
                if not sender_com_spec.VARIABLE_REF:
                    continue
                data_element_path = sender_com_spec.VARIABLE_REF.valueOf_
                data_element = rport_prototype.find(data_element_path)
                element_name = data_element_path.split("/")[-1]
                args = copy.deepcopy(
                    AutosarUtils.parse_de_for_compatibility(data_element, rport_prototype, mapping_sets, auxiliary_data)
                )
                port["args"].update({element_name: args})
                if args:
                    port["args"][element_name]["datatype"].update(
                        {"de_basetype": AutosarUtils.get_arg_base_type(args["datatype"]["name"])}
                    )
                    port["args"][element_name]["datatype"].update(
                        {
                            "map_runnable": data_element_path
                            in auxiliary_data["all_port_arg_in_runnable"][swc_name]["rports"].get(port_path, [])
                        }
                    )

        if category == "all":
            if port_name not in rport_list:
                rport_list[port_name] = {}
            rport_list[port_name].update({swc_name + "_" + port_name: port})
        elif category == "is_service":
            if port["Is_service"] and port["Is_service"].lower() == "true":
                if port_name not in rport_list:
                    rport_list[port_name] = {}
                rport_list[port_name].update({swc_name + "_" + port_name: port})
        elif category == "not_service":
            if port["Is_service"] and port["Is_service"].lower() == "false":
                if port_name not in rport_list:
                    rport_list[port_name] = {}
                rport_list[port_name].update({swc_name + "_" + port_name: port})

    @classmethod
    def map_port(cls, p_ports, r_ports, mapped_ports, filter):
        pre_process_ports, key_relation_for_match_whole_word = cls.__pre_process_ports(p_ports, r_ports, filter)
        selected_port_info, is_valid = cls.__get_selected_port_info(filter, p_ports, r_ports)
        if not is_valid:
            return {}, [[], [], [], []]

        mapping_result = {}
        if selected_port_info:
            valid_selected_port_info = {}
            for port_id, port_info in selected_port_info.items():
                if "p" in port_info["Tag"]:
                    target_port_key = cls.__get_processed_port_key(
                        filter, port_info["Name"], filter["direction"] == "Tx"
                    )
                    if target_port_key not in pre_process_ports[0]:
                        continue
                    valid_selected_port_info[port_id] = port_info
                    cls.__find_opposite_ports(
                        mapping_result,
                        {target_port_key: {port_id: pre_process_ports[0][target_port_key][port_id]}},
                        pre_process_ports[1],
                        key_relation_for_match_whole_word[0],
                        filter["allow_merge"],
                        filter["allow_split"],
                        filter["match_compatibility"],
                        True,
                        mapped_ports,
                    )
                if "r" in port_info["Tag"]:
                    target_port_key = cls.__get_processed_port_key(
                        filter, port_info["Name"], filter["direction"] == "Rx"
                    )
                    if target_port_key not in pre_process_ports[1]:
                        continue
                    valid_selected_port_info[port_id] = port_info
                    cls.__find_opposite_ports(
                        mapping_result,
                        {target_port_key: {port_id: pre_process_ports[1][target_port_key][port_id]}},
                        pre_process_ports[0],
                        key_relation_for_match_whole_word[1],
                        filter["allow_split"],
                        filter["allow_merge"],
                        filter["match_compatibility"],
                        False,
                        mapped_ports,
                    )
            return cls.__post_process_mapping_result(mapping_result, p_ports, r_ports, True, valid_selected_port_info)
        else:
            cls.__find_opposite_ports(
                mapping_result,
                pre_process_ports[0],
                pre_process_ports[1],
                key_relation_for_match_whole_word[0],
                filter["allow_merge"],
                filter["allow_split"],
                filter["match_compatibility"],
                True,
                mapped_ports,
            )
            return cls.__post_process_mapping_result(mapping_result, p_ports, r_ports, False)

    @classmethod
    def __get_selected_port_info(cls, filter, p_ports, r_ports):
        if "selected_port_info" in filter and filter["selected_port_info"]:
            return filter["selected_port_info"], True
        elif filter["component"]:
            target_swcs = set(filter["component"].split(" "))
            selected_port_info = {}
            for _, ports in p_ports.items():
                for port_id, port_info in ports.items():
                    if port_info["Component"] in target_swcs:
                        selected_port_info[port_id] = port_info
            for _, ports in r_ports.items():
                for port_id, port_info in ports.items():
                    if port_info["Component"] in target_swcs:
                        selected_port_info[port_id] = port_info
            return selected_port_info, bool(selected_port_info)
        else:
            return {}, True

    @classmethod
    def __post_process_mapping_result(cls, mapping_result, p_ports, r_ports, has_selected_input, selected_port_info={}):
        # 1:1 / 1:N / N:1 / M:N
        logs = [[], [], [], []]
        mapping_result_for_ui = {}
        valid_mapping_result = {}
        for port_id, result in mapping_result.items():
            if result["tx_valid_mn_conn"] or result["rx_valid_mn_conn"]:
                if not result["tx_valid_mn_conn"]:
                    result["tx_mapped_ports"].clear()
                if not result["rx_valid_mn_conn"]:
                    result["rx_mapped_ports"].clear()
                valid_mapping_result[port_id] = result
        if has_selected_input:
            for port_id, port_info in selected_port_info.items():
                cls.__update_mapping_result_for_ui(
                    port_id,
                    port_info,
                    valid_mapping_result,
                    mapping_result_for_ui,
                    logs,
                    selected_port_info=selected_port_info,
                )
        else:
            visited_port_id = set()
            for _, ports in p_ports.items():
                for port_id, port_info in ports.items():
                    cls.__update_mapping_result_for_ui(
                        port_id,
                        port_info,
                        valid_mapping_result,
                        mapping_result_for_ui,
                        logs,
                        visited_port_id=visited_port_id,
                    )
            for _, ports in r_ports.items():
                for port_id, port_info in ports.items():
                    cls.__update_mapping_result_for_ui(
                        port_id,
                        port_info,
                        valid_mapping_result,
                        mapping_result_for_ui,
                        logs,
                        visited_port_id=visited_port_id,
                    )
        return mapping_result_for_ui, logs

    @classmethod
    def __update_mapping_result_for_ui(
        cls, port_id, port, mapping_result, mapping_result_for_ui, logs, selected_port_info=None, visited_port_id=None
    ):
        if port_id in mapping_result:
            port_info = mapping_result[port_id]
            curr_mapping_result_for_ui = {}
            if visited_port_id is None:
                local_visited_port_id = set()
                num_tx, num_rx = cls.__get_connected_port_group(
                    local_visited_port_id,
                    mapping_result,
                    port_id,
                    port_info,
                    curr_mapping_result_for_ui,
                    selected_port_info,
                )
            else:
                num_tx, num_rx = cls.__get_connected_port_group(
                    visited_port_id, mapping_result, port_id, port_info, curr_mapping_result_for_ui, selected_port_info
                )
            mapping_result_for_ui.update(curr_mapping_result_for_ui)
            cls.__update_logs(num_tx, num_rx, curr_mapping_result_for_ui, logs)
        else:
            mapping_result_for_ui[port_id] = [
                port["Component"],
                port["Name"],
                port["Interface"].split("/")[-1],
                "<Select component prototype...>",
                "<Select port prototype...>",
                "",
                "",
            ]

    @classmethod
    def __update_logs(cls, num_tx, num_rx, curr_mapping_result, logs):
        if num_tx == 0 or num_rx == 0:
            return
        if num_tx == 1 and num_rx == 1:
            log_category = 0
        elif num_tx > 1 and num_rx > 1:
            log_category = 3
        elif num_tx > 1:
            log_category = 2
        else:
            log_category = 1
        mapped_port_id_groups = set()
        for _, entry in curr_mapping_result.items():
            if entry[3].startswith("<"):
                continue
            # valid mapping
            # dedup reversed log
            port_id = f"{entry[0]}_{entry[1]}_{entry[3]}_{entry[4]}"
            if port_id in mapped_port_id_groups:
                continue
            mapped_port_id_groups.add(port_id)
            logs[log_category].append(entry)

    @classmethod
    def __get_connected_port_group(
        cls, visited_port_id, mapping_result, port_id_a, port_info_a, mapping_result_for_ui, selected_port_info
    ):
        if port_id_a in visited_port_id:
            return 0, 0
        else:
            visited_port_id.add(port_id_a)
        num_tx = 0
        num_rx = 0
        port_a = port_info_a["port"]
        if port_info_a["tx_valid_mn_conn"] and port_info_a["tx_mapped_ports"]:
            num_tx += 1
            for port_b in port_info_a["tx_mapped_ports"]:
                port_id_b = port_b["id_port_map"]
                if selected_port_info:
                    ret_num_tx, ret_num_rx = 0, 0
                else:
                    ret_num_tx, ret_num_rx = cls.__get_connected_port_group(
                        visited_port_id,
                        mapping_result,
                        port_id_b,
                        mapping_result[port_id_b],
                        mapping_result_for_ui,
                        selected_port_info,
                    )
                mapping_key = f"{port_a['id_port_map']}_{port_b['id_port_map']}"
                if mapping_key not in mapping_result_for_ui:
                    mapping_result_for_ui[mapping_key] = cls.__get_mapping_result_for_ui_display(
                        port_a, port_id_a, port_b, True, selected_port_info
                    )
                num_tx += ret_num_tx
                num_rx += ret_num_rx
        if port_info_a["rx_valid_mn_conn"] and port_info_a["rx_mapped_ports"]:
            num_rx += 1
            for port_b in port_info_a["rx_mapped_ports"]:
                port_id_b = port_b["id_port_map"]
                if selected_port_info:
                    ret_num_tx, ret_num_rx = 0, 0
                else:
                    ret_num_tx, ret_num_rx = cls.__get_connected_port_group(
                        visited_port_id,
                        mapping_result,
                        port_id_b,
                        mapping_result[port_id_b],
                        mapping_result_for_ui,
                        selected_port_info,
                    )
                mapping_key = f"{port_a['id_port_map']}_{port_b['id_port_map']}"
                if mapping_key not in mapping_result_for_ui:
                    mapping_result_for_ui[mapping_key] = cls.__get_mapping_result_for_ui_display(
                        port_a, port_id_a, port_b, False, selected_port_info
                    )
                num_tx += ret_num_tx
                num_rx += ret_num_rx
        if not port_info_a["tx_mapped_ports"] and not port_info_a["rx_mapped_ports"]:
            mapping_result_for_ui[port_id_a] = [
                port_a["Component"],
                port_a["Name"],
                port_a["Interface"].split("/")[-1],
                "<Select component prototype...>",
                "<Select port prototype...>",
                "",
                "",
            ]
        return num_tx, num_rx

    @classmethod
    def __get_mapping_result_for_ui_display(cls, port_a, port_id_a, port_b, is_tx, selected_port_info):
        if selected_port_info:
            if port_id_a in selected_port_info:
                return [
                    port_a["Component"],
                    port_a["Name"],
                    port_a["Interface"].split("/")[-1],
                    port_b["Component"],
                    port_b["Name"],
                    port_b["Interface"].split("/")[-1],
                    "",
                ]
            else:
                return [
                    port_b["Component"],
                    port_b["Name"],
                    port_b["Interface"].split("/")[-1],
                    port_a["Component"],
                    port_a["Name"],
                    port_a["Interface"].split("/")[-1],
                    "",
                ]
        else:
            if is_tx:
                return [
                    port_a["Component"],
                    port_a["Name"],
                    port_a["Interface"].split("/")[-1],
                    port_b["Component"],
                    port_b["Name"],
                    port_b["Interface"].split("/")[-1],
                    "",
                ]
            else:
                return [
                    port_b["Component"],
                    port_b["Name"],
                    port_b["Interface"].split("/")[-1],
                    port_a["Component"],
                    port_a["Name"],
                    port_a["Interface"].split("/")[-1],
                    "",
                ]

    @classmethod
    def __find_opposite_ports(
        cls,
        mapping_result,
        groups_a,
        groups_b,
        key_relation_a,
        is_multi_allowed_a,
        is_multi_allowed_b,
        match_compat,
        is_tx,
        mapped_ports,
    ):
        visited_port_id = set()
        for port_key, ports_a in groups_a.items():
            for port_id_a, port_a in ports_a.items():
                if port_id_a not in mapping_result:
                    mapping_result[port_id_a] = {
                        "port": port_a,
                        "tx_mapped_ports": [],
                        "rx_mapped_ports": [],
                        "tx_valid_mn_conn": True,
                        "rx_valid_mn_conn": True,
                    }
                validity_key_a = "tx_valid_mn_conn" if is_tx else "rx_valid_mn_conn"
                validity_key_b = "rx_valid_mn_conn" if is_tx else "tx_valid_mn_conn"
                if not mapping_result[port_id_a][validity_key_a]:
                    continue
                direct_key_a = "tx_mapped_ports" if is_tx else "rx_mapped_ports"
                direct_key_b = "rx_mapped_ports" if is_tx else "tx_mapped_ports"

                if port_id_a in visited_port_id:
                    continue
                else:
                    visited_port_id.add(port_id_a)

                opposite_ports = groups_b.get(port_key, {})
                if port_key in key_relation_a:
                    for extra_key in key_relation_a[port_key]:
                        opposite_ports.update(groups_b.get(extra_key, {}))

                if not opposite_ports:
                    continue

                compatible_opposite_ports = []
                for port_b in opposite_ports.values():
                    port_id_b = port_b["id_port_map"]
                    if (
                        (port_a["Component"] == port_b["Component"])
                        or cls.__is_port_already_mapped(port_a, port_b, mapped_ports, is_tx)
                        or cls.__is_port_already_in_mapping_result(mapping_result, port_a, port_id_b, direct_key_b)
                        or (not cls.__is_compatible(port_a, port_b, match_compat))
                    ):
                        continue
                    if port_id_b in mapping_result and (not mapping_result[port_id_b][validity_key_b]):
                        mapping_result[port_id_a][validity_key_a] = False
                        break
                    if (
                        not is_multi_allowed_a
                        and port_id_b in mapping_result
                        and mapping_result[port_id_b][direct_key_b]
                    ):
                        cls.__invalidate_mapped_port(mapping_result, port_b, not is_tx)
                        break
                    compatible_opposite_ports.append(port_b)
                if (not mapping_result[port_id_a][validity_key_a]) or (not compatible_opposite_ports):
                    continue
                if (not is_multi_allowed_b) and len(compatible_opposite_ports) > 1:
                    mapping_result[port_id_a][validity_key_a] = False
                    for port_b in compatible_opposite_ports:
                        cls.__invalidate_mapped_port(mapping_result, port_b, not is_tx)
                    continue

                for port_b in compatible_opposite_ports:
                    mapping_result[port_id_a][direct_key_a].append(port_b)
                    port_id_b = port_b["id_port_map"]
                    if port_id_b not in mapping_result:
                        mapping_result[port_id_b] = {
                            "port": port_b,
                            "tx_mapped_ports": [],
                            "rx_mapped_ports": [],
                            "tx_valid_mn_conn": True,
                            "rx_valid_mn_conn": True,
                        }
                    mapping_result[port_id_b][direct_key_b].append(port_a)
        return mapping_result

    @classmethod
    def __invalidate_mapped_port(cls, mapping_result, port_a, is_tx):
        port_id_a = port_a["id_port_map"]
        validity_key_a = "tx_valid_mn_conn" if is_tx else "rx_valid_mn_conn"
        if port_id_a not in mapping_result or (not mapping_result[port_id_a][validity_key_a]):
            mapping_result[port_id_a] = {
                "port": port_a,
                "tx_mapped_ports": [],
                "rx_mapped_ports": [],
                "tx_valid_mn_conn": False if is_tx else True,
                "rx_valid_mn_conn": True if is_tx else False,
            }
            return
        direct_key_a = "tx_mapped_ports" if is_tx else "rx_mapped_ports"
        mapping_result[port_id_a][validity_key_a] = False
        for port_b in mapping_result[port_id_a][direct_key_a]:
            cls.__invalidate_mapped_port(mapping_result, port_b, not is_tx)
        mapping_result[port_id_a][direct_key_a].clear()

    @classmethod
    def __pre_process_ports(cls, p_ports, r_ports, filter):
        rv = [{}, {}]
        key_groups = [{}, {}]
        key_relation_for_match_whole_word = [{}, {}]

        # automatic: no filter
        if filter["automatic"]:
            rv[0] = p_ports
            rv[1] = r_ports
            return rv, key_relation_for_match_whole_word

        # manual: filter
        for port_key, p_port in p_ports.items():
            for port in p_port.values():
                cls.__pre_process_each_port(rv[0], key_groups[0], filter, port_key, port, (filter["direction"] == "Tx"))
        for port_key, r_port in r_ports.items():
            for port in r_port.values():
                cls.__pre_process_each_port(rv[1], key_groups[1], filter, port_key, port, (filter["direction"] == "Rx"))

        if not filter["match_whole_word"]:
            p_max_len = max(key_groups[0].keys()) if key_groups[0] else 0
            p_groups = [{} if x not in key_groups[0] else key_groups[0][x] for x in range(p_max_len + 1)]
            r_max_len = max(key_groups[1].keys()) if key_groups[1] else 0
            r_groups = [{} if x not in key_groups[1] else key_groups[1][x] for x in range(r_max_len + 1)]
            if filter["direction"] == "Tx":
                cls.__pre_process_key_groups(
                    key_relation_for_match_whole_word[0],
                    key_relation_for_match_whole_word[1],
                    p_groups,
                    r_groups,
                    r_max_len,
                )
            else:
                cls.__pre_process_key_groups(
                    key_relation_for_match_whole_word[1],
                    key_relation_for_match_whole_word[0],
                    r_groups,
                    p_groups,
                    p_max_len,
                )
        return rv, key_relation_for_match_whole_word

    @classmethod
    def __pre_process_key_groups(cls, key_relation_a, key_relation_b, key_groups_a, key_groups_b, max_len_b):
        key_len_a = -1
        for groups_a in key_groups_a:
            key_len_a += 1
            if not groups_a:
                continue
            for key_len_b in range(key_len_a + 1, max_len_b + 1):
                groups_b = key_groups_b[key_len_b]
                if not groups_b:
                    continue
                for key_a in groups_a:
                    for key_b in groups_b:
                        if key_a not in key_b:
                            continue
                        if key_a not in key_relation_a:
                            key_relation_a[key_a] = set()
                        if key_b not in key_relation_b:
                            key_relation_b[key_b] = set()
                        key_relation_a[key_a].add(key_b)
                        key_relation_b[key_b].add(key_a)

    @classmethod
    def __pre_process_each_port(cls, port_info, key_groups, filter, port_key, port, is_matching_direction):
        new_key = cls.__get_processed_port_key(filter, port_key, is_matching_direction)
        if new_key not in port_info:
            port_info[new_key] = {}
        port_info[new_key][port["id_port_map"]] = port
        if not filter["match_whole_word"]:
            key_len = len(new_key)
            if key_len not in key_groups:
                key_groups[key_len] = set()
            key_groups[key_len].add(new_key)

    @classmethod
    def __get_processed_port_key(cls, filter, port_key, is_matching_direction):
        new_key = port_key if filter["match_case"] else port_key.lower()
        if not is_matching_direction:
            return new_key
        if filter["match_case"]:
            prefix = filter["prefix"]
            postfix = filter["postfix"]
        else:
            prefix = filter["prefix"].lower()
            postfix = filter["postfix"].lower()
        if prefix and new_key.startswith(prefix):
            new_key = new_key[len(prefix) : len(new_key)]
        if postfix and new_key.endswith(postfix):
            new_key = new_key[0 : (len(new_key) - len(postfix))]
        return new_key

    @classmethod
    def __is_compatible(cls, port_a, port_b, match_compat=False):
        """
        # 判断是否两个port是否兼容
        Args:
            port_a (dict):
            port_b (dict):

        Returns:
            rv: is compatible or not
        """
        rv = Compatibility.not_match
        if cls.__is_same_component(port_a, port_b) or (not cls.__is_interface_compatible(port_a, port_b)):
            return rv
        rv = cls.__is_data_element_compatible(port_a, port_b, match_compat)
        return rv

    @classmethod
    def is_interface_compatible_for_validataion(cls, port_a, port_b):
        return cls.__is_interface_compatible(port_a, port_b)

    @classmethod
    def is_data_element_compatible_for_validataion(cls, port_a, port_b, match_compat):
        return cls.__is_data_element_compatible(port_a, port_b, match_compat)

    @classmethod
    def __is_data_element_compatible(cls, port_a, port_b, match_compat):
        """
        用于判断相连接的port的data_element/arg是否兼容
        Args:
            port_a (dict):
            port_b (dict):
            match_compat (bool):

        Returns:
            rv: is data element compatible or not
        """
        rv = Compatibility.not_match
        if port_a["Interface_type"] == "CLIENT-SERVER-INTERFACE":
            temp_rv = max(Compatibility, key=lambda x: x.value)
            index = 0
            for de, value in port_a["args"].items():
                if not value:
                    # 只有operation，里面没有arguments
                    if value == port_b["args"].get(de, {}):
                        compatibility = Compatibility.full_match
                        if compatibility < temp_rv:
                            temp_rv = compatibility
                        index += 1
                    else:
                        compatibility = Compatibility.not_match
                        if compatibility < temp_rv:
                            temp_rv = compatibility
                        index += 1
                else:
                    for inner_de, inner_value in value.items():
                        map_runnble_a = inner_value.get("map_runnable", None)
                        map_runnble_b = port_b["args"].get(de, {}).get(inner_de, {}).get("map_runnable", None)
                        if not map_runnble_a or not map_runnble_b:
                            continue
                        if inner_value["category"] != "UNION":
                            de_basetype_a = inner_value.get("de_basetype", None)
                            de_constr_a = inner_value.get("constraint", None)
                            de_basetype_b = port_b["args"].get(de, {}).get(inner_de, {}).get("de_basetype", None)
                            de_constr_b = port_b["args"].get(de, {}).get(inner_de, {}).get("constraint", None)
                            if not de_basetype_b and not de_basetype_a:
                                index += 1
                                continue
                            if not de_basetype_b or not de_basetype_a:
                                return rv
                            compatibility = cls.__is_data_element_same_or_compatible(
                                port_a, port_b, de_basetype_a, de_basetype_b, de_constr_a, de_constr_b, de, match_compat
                            )
                        else:
                            compatibility = Compatibility.full_match
                        temp_rv = min(compatibility, temp_rv)
                        index += 1
            if index > 0:
                rv = temp_rv
        elif port_a["Interface_type"] in ["SENDER-RECEIVER-INTERFACE", "NV-DATA-INTERFACE"]:
            temp_rv = max(Compatibility, key=lambda x: x.value)
            index = 0
            for de, value in port_a["args"].items():
                map_runnble_a = value.get("datatype", {}).get("map_runnable", None)
                map_runnble_b = port_b["args"].get(de, {}).get("datatype", {}).get("map_runnable", None)
                if not map_runnble_a or not map_runnble_b:
                    continue
                if ("category" in value and value["category"] != "UNION") or (
                    "category" not in value and value["datatype"]["category"] != "UNION"
                ):
                    de_basetype_a = value.get("datatype", {}).get("de_basetype", None)
                    de_constr_a = value.get("datatype", {}).get("constraint", None)
                    de_basetype_b = port_b["args"].get(de, {}).get("datatype", {}).get("de_basetype", None)
                    de_constr_b = port_b["args"].get(de, {}).get("datatype", {}).get("constraint", None)
                    if not de_basetype_b and not de_basetype_a:
                        index += 1
                        continue
                    if not de_basetype_b or not de_basetype_a:
                        return rv
                    compatibility = cls.__is_data_element_same_or_compatible(
                        port_a, port_b, de_basetype_a, de_basetype_b, de_constr_a, de_constr_b, de, match_compat
                    )
                else:
                    compatibility = Compatibility.full_match
                temp_rv = min(compatibility, temp_rv)
                index += 1
            if index > 0:
                rv = temp_rv
        elif port_a["Interface_type"] == "MODE-SWITCH-INTERFACE":
            return Compatibility.full_match
        elif port_a["Interface_type"] == "PARAMETER-INTERFACE":
            return Compatibility.full_match
        else:
            return Compatibility.full_match
        return rv

    @classmethod
    def __is_data_element_same_or_compatible(
        cls, port_a, port_b, de_basetype_a, de_basetype_b, de_constr_a, de_constr_b, op_de, match_compat
    ):
        """判断data element是完全一致,还是兼容的
        Args:
            port_a (dict)
            port_b (dict)
            de_basetype_a (str/list/dict)
            de_basetype_b (str/list/dict)
            op_de (str)
            match_compat (bool)
            auxiliary_data(dict)
        Returns:
            rv(enum):
        """
        rv = Compatibility.not_match
        if type(de_basetype_a) is not type(de_basetype_b):
            # 类型不一致，如de_basetype_a是str，de_basetype_b是dict肯定不同
            a_component, a_port, b_component, b_port = (
                port_a["Component"],
                port_a["Name"],
                port_b["Component"],
                port_b["Name"],
            )
            logger.warning(
                f"base type of {a_component}_{a_port}_{op_de} and {b_component}_{b_port}_{op_de} is not the same!"
            )
            return False
        if type(de_basetype_a) is str:
            # 简单类型
            rv = cls.__is_data_element_str_same_or_compatible(
                de_basetype_a, de_basetype_b, match_compat, port_a, port_b, op_de, de_constr_a, de_constr_b
            )
        elif type(de_basetype_a) is list:
            # 数组
            rv = cls.__is_data_element_array_same_or_compatible(
                de_basetype_a, de_basetype_b, match_compat, port_a, port_b, op_de, de_constr_a, de_constr_b
            )
        elif type(de_basetype_a) is dict:
            # 结构体
            rv = cls.__is_data_element_struct_same_or_compatible(
                de_basetype_a, de_basetype_b, match_compat, port_a, port_b, op_de, de_constr_a, de_constr_b
            )
        return rv

    @classmethod
    def __is_data_element_str_same_or_compatible(
        cls, de_basetype_a, de_basetype_b, match_compat, port_a, port_b, op_de, constr_a, constr_b
    ):
        """
        判断data element类型是字符串时,是否一致或兼容
        """
        rv = Compatibility.not_match
        if match_compat:
            max_constr_a, min_constr_a = constr_a.get("max", 0), constr_a.get("min", 0)
            max_constr_b, min_constr_b = constr_b.get("max", 0), constr_b.get("min", 0)
            if de_basetype_a.endswith("_least"):
                de_basetype_a = de_basetype_a[0 : (len(de_basetype_a) - len("_least"))]
            if de_basetype_b.endswith("_least"):
                de_basetype_b = de_basetype_b[0 : (len(de_basetype_b) - len("_least"))]
            digits_a = (
                int("".join([char for char in de_basetype_a if char.isdigit()])) if de_basetype_a != "boolean" else 1
            )
            letters_a = "".join([char for char in de_basetype_a if char.isalpha()])
            digits_b = (
                int("".join([char for char in de_basetype_b if char.isdigit()])) if de_basetype_b != "boolean" else 1
            )
            letters_b = "".join([char for char in de_basetype_b if char.isalpha()])
            a_component, a_port, b_component, b_port = (
                port_a["Component"],
                port_a["Name"],
                port_b["Component"],
                port_b["Name"],
            )
            if letters_a != letters_b:
                logger.warning(
                    f"type of {a_component}_{a_port}_{op_de} and "
                    f"{b_component}_{b_port}_{op_de} base_type is not compatible!"
                )
                return Compatibility.not_match
            if port_a["Tag"] == "p":
                if digits_a > digits_b:
                    logger.warning(
                        f"size of {a_component}_{a_port}_{op_de} and "
                        f"{b_component}_{b_port}_{op_de} base_type is not compatible!"
                    )
                    return Compatibility.not_match
                elif max_constr_a > max_constr_b or min_constr_a < min_constr_b:
                    logger.warning(
                        f"constraints of {a_component}_{a_port}_{op_de} and "
                        f"{b_component}_{b_port}_{op_de} base_type is not compatible!"
                    )
                    return Compatibility.not_match
                elif digits_a == digits_b and max_constr_a == max_constr_b and min_constr_a == min_constr_b:
                    return Compatibility.full_match
                else:
                    return Compatibility.partial_match
            elif port_a["Tag"] == "r":
                if digits_a < digits_b:
                    logger.warning(
                        f"size of {a_component}_{a_port}_{op_de} and "
                        f"{b_component}_{b_port}_{op_de} base_type is not compatible!"
                    )
                    return Compatibility.not_match
                elif max_constr_a < max_constr_b or min_constr_a > min_constr_b:
                    logger.warning(
                        f"constraints of {a_component}_{a_port}_{op_de} and "
                        f"{b_component}_{b_port}_{op_de} base_type is not compatible!"
                    )
                    return Compatibility.not_match
                elif digits_a == digits_b and max_constr_a == max_constr_b and min_constr_a == min_constr_b:
                    return Compatibility.full_match
                else:
                    return Compatibility.partial_match
            else:
                if port_b["Tag"] == "p":
                    if digits_a < digits_b:
                        logger.warning(
                            f"size of {a_component}_{a_port}_{op_de} and "
                            f"{b_component}_{b_port}_{op_de} base_type is not compatible!"
                        )
                        return Compatibility.not_match
                    elif max_constr_a < max_constr_b or min_constr_a > min_constr_b:
                        logger.warning(
                            f"constraints of {a_component}_{a_port}_{op_de} and "
                            f"{b_component}_{b_port}_{op_de} base_type is not compatible!"
                        )
                        return Compatibility.not_match
                    elif digits_a == digits_b and max_constr_a == max_constr_b and min_constr_a == min_constr_b:
                        return Compatibility.full_match
                    else:
                        return Compatibility.partial_match
                elif port_b["Tag"] == "r":
                    if digits_a > digits_b:
                        logger.warning(
                            f"size of {a_component}_{a_port}_{op_de} and "
                            f"{b_component}_{b_port}_{op_de} base_type is not compatible!"
                        )
                        return Compatibility.not_match
                    elif max_constr_a > max_constr_b or min_constr_a < min_constr_b:
                        logger.warning(
                            f"constraints of {a_component}_{a_port}_{op_de} and "
                            f"{b_component}_{b_port}_{op_de} base_type is not compatible!"
                        )
                        return Compatibility.not_match
                    elif digits_a == digits_b and max_constr_a == max_constr_b and min_constr_a == min_constr_b:
                        return Compatibility.full_match
                    else:
                        return Compatibility.partial_match
                else:
                    if digits_a != digits_b:
                        logger.warning(
                            f"size of {a_component}_{a_port}_{op_de} and "
                            f"{b_component}_{b_port}_{op_de} base_type is not the same!"
                        )
                        return Compatibility.not_match
                    elif max_constr_a != max_constr_b or min_constr_a != min_constr_b:
                        logger.warning(
                            f"constraints of {a_component}_{a_port}_{op_de} and "
                            f"{b_component}_{b_port}_{op_de} base_type is not the same!"
                        )
                        return Compatibility.not_match
                    else:
                        return Compatibility.full_match
        else:
            if de_basetype_a == de_basetype_b and constr_a == constr_b:
                rv = Compatibility.full_match
        return rv

    @classmethod
    def __is_data_element_array_same_or_compatible(
        cls, de_basetype_a, de_basetype_b, match_compat, port_a, port_b, op_de, de_constr_a, de_constr_b
    ):
        """
        判断data element类型是数组时,是否一致或兼容
        """
        rv = Compatibility.full_match
        if len(de_basetype_a) == len(de_basetype_b) == 0:
            # 数组为空时，不比对
            return rv
        # 数组类型只需对比一个元素就行
        if len(de_basetype_a) != len(de_basetype_b):
            # 数组长度不一致
            return Compatibility.not_match

        try:
            element_a, element_b = de_basetype_a[0], de_basetype_b[0]
            element_a_constr, element_b_constr = de_constr_a[0], de_constr_b[0]
        except IndexError:
            return Compatibility.not_match

        if type(element_a) is not type(element_b):
            # 类型不一致
            rv = Compatibility.not_match
        if type(element_a) is str:
            # member是简单类型
            temp_rv = cls.__is_data_element_str_same_or_compatible(
                element_a, element_b, match_compat, port_a, port_b, op_de, element_a_constr, element_b_constr
            )
            if temp_rv == Compatibility.partial_match or temp_rv == Compatibility.not_match:
                rv = temp_rv
            if not rv:
                return rv
        elif type(element_a) is list:
            # member是数组
            temp_rv = cls.__is_data_element_array_same_or_compatible(
                element_a, element_b, match_compat, port_a, port_b, op_de, element_a_constr, element_b_constr
            )
            if temp_rv == Compatibility.partial_match or temp_rv == Compatibility.not_match:
                rv = temp_rv
            if not rv:
                return rv
        elif type(element_a) is dict:
            temp_rv = cls.__is_data_element_struct_same_or_compatible(
                element_a, element_b, match_compat, port_a, port_b, op_de, element_a_constr, element_b_constr
            )
            if temp_rv == Compatibility.partial_match or temp_rv == Compatibility.not_match:
                rv = temp_rv
            if not rv:
                return rv
        return rv

    @classmethod
    def __is_data_element_struct_same_or_compatible(
        cls, de_basetype_a, de_basetype_b, match_compat, port_a, port_b, op_de, de_constr_a, de_constr_b
    ):
        """
        判断data element类型是结构体时,是否一致或兼容
        """
        rv = Compatibility.full_match
        de_basetype_a_list = list(de_basetype_a.values())
        de_basetype_b_list = list(de_basetype_b.values())
        if (not de_basetype_a_list) or (not de_basetype_b_list):
            if not de_basetype_a_list == de_basetype_b_list:
                return Compatibility.not_match
        if len(de_basetype_a_list) != len(de_basetype_b_list):
            return Compatibility.not_match
        for key, member_a in de_basetype_a.items():
            try:
                member_b = de_basetype_b[key]
            except KeyError:
                return Compatibility.not_match
            if type(member_a) is not type(member_b):
                # 类型不一致
                return Compatibility.not_match
            member_constr_a, member_constr_b = de_constr_a.get(key, None), de_constr_b.get(key, None)
            if type(member_a) is str:
                # member是简单类型
                temp_rv = cls.__is_data_element_str_same_or_compatible(
                    member_a, member_b, match_compat, port_a, port_b, op_de, member_constr_a, member_constr_b
                )
                if temp_rv == Compatibility.partial_match or temp_rv == Compatibility.not_match:
                    rv = temp_rv
                if not rv:
                    return rv
            elif type(member_a) is list:
                # member是数组
                temp_rv = cls.__is_data_element_array_same_or_compatible(
                    member_a, member_b, match_compat, port_a, port_b, op_de, member_constr_a, member_constr_b
                )
                if temp_rv == Compatibility.partial_match or temp_rv == Compatibility.not_match:
                    rv = temp_rv
                if not rv:
                    return rv
            elif type(member_a) is dict:
                # member是结构体
                temp_rv = cls.__is_data_element_struct_same_or_compatible(
                    member_a, member_b, match_compat, port_a, port_b, op_de, member_constr_a, member_constr_b
                )
                if temp_rv == Compatibility.partial_match or temp_rv == Compatibility.not_match:
                    rv = temp_rv
                if not rv:
                    return rv
        return rv

    @classmethod
    def __is_same_component(cls, port_a, port_b):
        # 判断是否两个port处于同一个模块
        rv = False
        if "Component" not in port_b:
            # 界面上右键connect的情况，是一个索引为行号的字典
            rv = True if port_a["Component"] == list(port_b.values())[0][MT_Index.Component] else False
        else:
            rv = True if port_a["Component"] == port_b["Component"] else False
        return rv

    @classmethod
    def __is_interface_compatible(cls, port_a, port_b):
        # 判断interface是否兼容，此处不添加兼容性条件，所有情况都需符合此条件
        rv = True
        # SR-SR/SR-NV
        if port_a["Interface_type"] in ["SENDER-RECEIVER-INTERFACE", "NV-DATA-INTERFACE"]:
            rv = port_b["Interface_type"] in ["NV-DATA-INTERFACE", "SENDER-RECEIVER-INTERFACE"]
            if not rv:
                return rv
        # CS-CS
        if (
            port_a["Interface_type"] == "CLIENT-SERVER-INTERFACE"
            or port_b["Interface_type"] == "CLIENT-SERVER-INTERFACE"
        ):
            rv = port_a["Interface_type"] == port_b["Interface_type"]
            if not rv:
                return rv
        # MS-MS
        if port_b["Interface_type"] == "MODE-SWITCH-INTERFACE" or port_a["Interface_type"] == "MODE-SWITCH-INTERFACE":
            rv = port_a["Interface_type"] == port_b["Interface_type"]
            if not rv:
                return rv
        # Service-Service
        if port_a["Is_service"] or port_b["Is_service"]:
            rv = port_a["Is_service"] == port_b["Is_service"]
            if not rv:
                return rv
        # Trigger & parameter interface 目前还没有解析，后续用到再添加
        # TODO
        return rv

    @classmethod
    def __is_port_already_mapped(cls, port_a, port_b, mapped_ports, is_tx):
        if port_a["Tag"] == "pr" and port_b["Tag"] == "pr":
            return (
                f"{port_a['id_port_map']}_{port_b['id_port_map']}" in mapped_ports
                or f"{port_b['id_port_map']}_{port_a['id_port_map']}" in mapped_ports
            )
        elif is_tx:
            return f"{port_a['id_port_map']}_{port_b['id_port_map']}" in mapped_ports
        else:
            return f"{port_b['id_port_map']}_{port_a['id_port_map']}" in mapped_ports

    @classmethod
    def __is_port_already_in_mapping_result(cls, mapping_result, port_a, port_id_b, direct_key_b):
        return (
            port_id_b in mapping_result
            and mapping_result[port_id_b][direct_key_b]
            and mapping_result[port_id_b][direct_key_b][0] == port_a
        )

    @classmethod
    def get_the_direction_of_selected_prport(cls, mapping_list, all_ports_dict):
        # mapping_direction = None
        connector_name = ""
        port_to_map = {}
        port_be_map = {}
        port_to, component_to, component_port, port_be, component_be, conn_component_port = mapping_list[0:6]
        # port_to
        if port_to in all_ports_dict["pports"] and component_port in all_ports_dict["pports"][port_to]:
            port_to_map = all_ports_dict["pports"][port_to][component_port]
        elif port_to in all_ports_dict["rports"] and component_port in all_ports_dict["rports"][port_to]:
            port_to_map = all_ports_dict["rports"][port_to][component_port]
        # port_be
        if port_be in all_ports_dict["pports"] and conn_component_port in all_ports_dict["pports"][port_be]:
            port_be_map = all_ports_dict["pports"][port_be][conn_component_port]
        elif port_be in all_ports_dict["rports"] and conn_component_port in all_ports_dict["rports"][port_be]:
            port_be_map = all_ports_dict["rports"][port_be][conn_component_port]

        if port_to_map:
            if port_to_map["Tag"] == "pr":
                if port_be_map["Tag"] == "pr":
                    if component_to < component_be:
                        connector_name = "_".join([component_to, port_to, component_be, port_be])
                        # mapping_direction = 'F'  # 正向
                    else:
                        connector_name = "_".join([component_be, port_be, component_to, port_to])
                        # mapping_direction = 'R'  # 反向
                else:
                    if port_be_map["Tag"] == "p":
                        connector_name = "_".join([component_be, port_be, component_to, port_to])
                        # mapping_direction = 'R'  # 反向
                    else:
                        connector_name = "_".join([component_to, port_to, component_be, port_be])
                        # mapping_direction = 'F'  # 正向
            else:
                if port_to_map["Tag"] == "p":
                    connector_name = "_".join([component_to, port_to, component_be, port_be])
                    # mapping_direction = 'F'  # 正向
                else:
                    connector_name = "_".join([component_be, port_be, component_to, port_to])
        return connector_name, port_to_map, port_be_map

    @classmethod
    def save_port_mapping_list(cls, mapping_data, all_ports_dict, autosar_system_class):
        row_data = []
        if not mapping_data:
            return row_data

        all_mapping_info = []
        assembly_conn_set = set(
            get_short_name(conn)
            for conn in autosar_system_class["FlatExtract"]
            .find("/COM/VCOS2/CFG/WORKFLOW/SYSDESC/SYNC/COMPOSITIONTYPE")
            .CONNECTORS.ASSEMBLY_SW_CONNECTOR
        )
        for data in mapping_data:
            mapping_list = []
            port_be = data[TT_Index.Conn_Port]
            component_be = data[TT_Index.Conn_Component]
            conn_component_port = component_be + "_" + port_be
            if component_be == "<Select component prototype...>" or port_be == "<Select port prototype...>":
                continue
            add_port_connect_to_save = {}
            port_to_map = {}
            port_to = data[TT_Index.Port]
            component_to = data[TT_Index.Component]
            component_port = component_to + "_" + port_to
            mapping_list = [port_to, component_to, component_port, port_be, component_be, conn_component_port]
            # connector_name是完整的p_swc+p_port+r_swc+r_port, short_name是截断之后的名字(如果len(connector_name)>128)
            connector_name, port_to_map, _ = cls.get_the_direction_of_selected_prport(mapping_list, all_ports_dict)
            short_name = (
                cls.update_short_name_length(connector_name)
                if connector_name and len(connector_name) > 128
                else connector_name
            )
            # 如果是新增的连接，保存到FlatExtract中
            if short_name not in assembly_conn_set:
                # 格式转换
                value = [""] * len(MT_Index)
                value[MT_Index.Port] = port_to
                value[MT_Index.Completed] = "√"
                value[MT_Index.Component] = component_to
                value[MT_Index.Port_Interface] = data[TT_Index.Port_Interface]
                value[MT_Index.Conn_Component] = data[TT_Index.Conn_Component]
                value[MT_Index.Conn_Port] = data[TT_Index.Conn_Port]
                value[MT_Index.Conn_Port_Interface] = data[TT_Index.Conn_Port_Interface]
                if port_to_map["Tag"] == "pr":
                    value[MT_Index.Port_Direction] = "PR-Port"
                elif port_to_map["Tag"] == "p":
                    value[MT_Index.Port_Direction] = "P-Port"
                else:
                    value[MT_Index.Port_Direction] = "R-Port"
                add_port_connect_to_save[connector_name] = value
                mapping_info = cls.get_port_mapping_info(add_port_connect_to_save, all_ports_dict)
                all_mapping_info.append(mapping_info)
                row_data.append(value)
                # 添加以后就把名字add进去，避免重复生成
                assembly_conn_set.add(short_name)
        if all_mapping_info:
            AutosarUtil.save_assembly_sw_connector(autosar_system_class["FlatExtract"], all_mapping_info)
        return row_data

    @classmethod
    def get_port_mapping_info(cls, add_port_connect, all_ports_dict):
        mapping_info = {}
        for connector_name, value in add_port_connect.items():
            short_name = (
                cls.update_short_name_length(connector_name)
                if connector_name and len(connector_name) > 128
                else connector_name
            )
            mapping_info[connector_name] = {}
            mapping_info[connector_name].update({"uuid": 123456})
            mapping_info[connector_name].update({"short_name": short_name})
            mapping_info[connector_name].update({"type": "ASSEMBLY_SW_CONNECTOR"})
            mapping_info[connector_name].update({"provider_iref": {}})
            mapping_info[connector_name].update({"requester_iref": {}})
            port_a = value[MT_Index.Port]
            swc_port_a = f"{value[MT_Index.Component]}_{port_a}"
            port_b = value[MT_Index.Conn_Port]
            swc_port_b = f"{value[MT_Index.Conn_Component]}_{port_b}"
            if value[MT_Index.Port_Direction] == "P-Port":
                cls.__get_port_service_mapping_info(
                    mapping_info, all_ports_dict, connector_name, port_a, swc_port_a, port_b, swc_port_b
                )
            elif value[MT_Index.Port_Direction] == "R-Port":
                cls.__get_port_service_mapping_info(
                    mapping_info, all_ports_dict, connector_name, port_b, swc_port_b, port_a, swc_port_a
                )
            else:
                # PR-Port
                if connector_name.startswith(swc_port_a):
                    cls.__get_port_service_mapping_info(
                        mapping_info, all_ports_dict, connector_name, port_a, swc_port_a, port_b, swc_port_b
                    )
                elif connector_name.startswith(swc_port_b):
                    cls.__get_port_service_mapping_info(
                        mapping_info, all_ports_dict, connector_name, port_b, swc_port_b, port_a, swc_port_a
                    )
        return mapping_info

    @classmethod
    def __get_port_service_mapping_info(
        cls, mapping_info, all_swc_port_dict, connector_name, port_p, swc_port_p, port_r, swc_port_r
    ):
        pport = all_swc_port_dict["pports"].get(port_p, {}).get(swc_port_p, {})
        if pport:
            mapping_info[connector_name]["provider_iref"].update(
                {"context_component_ref": pport["CONTEXT-COMPONENT-REF"]}
            )
            mapping_info[connector_name]["provider_iref"].update({"context_component_dest": "SW-COMPONENT-PROTOTYPE"})
            mapping_info[connector_name]["provider_iref"].update({"target_pport_ref": pport["TARGET-P-PORT-REF"]})
            mapping_info[connector_name]["provider_iref"].update(
                {"target_pport_dest": "PR-PORT-PROTOTYPE" if pport["Tag"] == "pr" else "P-PORT-PROTOTYPE"}
            )

        rport = all_swc_port_dict["rports"].get(port_r, {}).get(swc_port_r, {})
        if rport:
            mapping_info[connector_name]["requester_iref"].update(
                {"context_component_ref": rport["CONTEXT-COMPONENT-REF"]}
            )
            mapping_info[connector_name]["requester_iref"].update({"context_component_dest": "SW-COMPONENT-PROTOTYPE"})
            mapping_info[connector_name]["requester_iref"].update({"target_rport_ref": rport["TARGET-R-PORT-REF"]})
            mapping_info[connector_name]["requester_iref"].update(
                {"target_rport_dest": "PR-PORT-PROTOTYPE" if rport["Tag"] == "pr" else "R-PORT-PROTOTYPE"}
            )

    @classmethod
    def cmd_filter_trans(cls, args={}):
        rv = {
            "selected_port_info": {},
            "automatic": None,
            "component": args.component,
            "direction": args.direction.lower() if args.direction else None,
            "prefix": args.prefix,
            "postfix": args.postfix,
            "allow_split": args.allow_split,
            "allow_merge": args.allow_merge,
            "match_case": not bool(args.ignore_match_case),
            "match_whole_word": not bool(args.ignore_match_whole_word),
            "mapping_mode": args.Mapping,
            "match_compatibility": args.match_compatibility,
        }
        return rv

    @classmethod
    def log_to_excel(cls, file_path, logs):

        def write_sheet(sheet_obj, log_list):
            row = 3  # 去除数据格式后，log数据从第三行开始，跟title直接空一行，方便用户进行查看
            for log in log_list:
                cls.__write_row_data(sheet_obj, row, log)
                row += 1
            cls.__set_column_widths(sheet_obj)

        workbook = Workbook()
        sheet = workbook.active
        workbook.remove(sheet)  # type: ignore

        HEADER = [
            "ComponentPrototype",
            "PortPrototype",
            "PortInterface",
            "Connected ComponentPrototype",
            "Connected PortPrototype",
            "Connected PortInterface",
        ]
        HEADER_UNCON = ["ComponentPrototype", "PortPrototype", "PortInterface", "comment"]
        SHEET_NAME = ["1-1", "1-N", "N-1", "M-N", "Connected_Ports", "UnConnected_Ports"]
        sheet_num = 0
        for curr_logs in logs:
            sheet = workbook.create_sheet(title=SHEET_NAME[sheet_num])
            if sheet_num == SHEET_NAME.index("UnConnected_Ports"):
                cls.__write_row_data(sheet, 1, HEADER_UNCON)
            else:
                cls.__write_row_data(sheet, 1, HEADER)
            write_sheet(sheet, curr_logs)
            sheet_num += 1

        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        workbook.save(file_path)
        return file_path

    @classmethod
    def __write_row_data(cls, sheet, row_num, row_data):
        col = 0
        for value in row_data:
            sheet.cell(row=row_num, column=col + 1, value=value)
            col += 1

    @classmethod
    def __set_column_widths(cls, sheet):
        for column in sheet.columns:
            max_length = 0
            column_name = column[0].column_letter
            for cell in column:
                if cell.coordinate in sheet.merged_cells:
                    continue
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            adjusted_width = (max_length + 2) * 1.2
            sheet.column_dimensions[column_name].width = adjusted_width

    @classmethod
    def get_swc_all_ports_list(cls, all_app_swc_port_dict):
        ports = []
        port_direction = {}
        ports_in_component = {}
        for _, pport_list in all_app_swc_port_dict["pports"].items():
            for _, pport in pport_list.items():
                port_list = [""] * len(MT_Index)
                port_list[MT_Index.Port] = pport["Name"]  # Port Prototype
                port_list[MT_Index.Component] = pport["Component"]  # Component Prototype
                port_list[MT_Index.Port_Interface] = pport["Interface"].split("/")[-1]  # Port Interface
                port_list[MT_Index.Port_Direction] = "PR-Port" if pport["Tag"] == "pr" else "P-Port"
                if port_list not in ports:
                    ports.append(port_list)
                    port_direction.update(
                        {
                            port_list[MT_Index.Component]
                            + "_"
                            + port_list[MT_Index.Port]: port_list[MT_Index.Port_Direction]
                        }
                    )
                if port_list[MT_Index.Component] not in ports_in_component:
                    ports_in_component.update({port_list[MT_Index.Component]: []})
                    ports_in_component[port_list[MT_Index.Component]].append(pport)
                else:
                    ports_in_component[port_list[MT_Index.Component]].append(pport)
        for _, rport_list in all_app_swc_port_dict["rports"].items():
            for _, rport in rport_list.items():
                port_list = [""] * len(MT_Index)
                port_list[MT_Index.Port] = rport["Name"]  # Port Prototype
                port_list[MT_Index.Component] = rport["Component"]  # Component Prototype
                port_list[MT_Index.Port_Interface] = rport["Interface"].split("/")[-1]  # Port Interface
                port_list[MT_Index.Port_Direction] = "PR-Port" if rport["Tag"] == "pr" else "R-Port"
                if port_list not in ports:
                    ports.append(port_list)
                    port_direction.update(
                        {
                            port_list[MT_Index.Component]
                            + "_"
                            + port_list[MT_Index.Port]: port_list[MT_Index.Port_Direction]
                        }
                    )
                if port_list[MT_Index.Component] not in ports_in_component:
                    ports_in_component.update({port_list[MT_Index.Component]: []})
                    ports_in_component[port_list[MT_Index.Component]].append(rport)
                else:
                    ports_in_component[port_list[MT_Index.Component]].append(rport)
        return ports, port_direction, ports_in_component

    @classmethod
    def get_port_mapping_port_connections_from_flatextract(cls, ar_asw, asw_autosar_dict):
        assembly_connectors = {}
        port_connections = {}
        pport_interface_name, pport_direction, rport_interface_name, rport_direction = None, None, None, None
        ar_ecu_compositions = ar_asw.find_nodes("COMPOSITION-SW-COMPONENT-TYPE")
        for ar_ecu_composition in ar_ecu_compositions:
            if not ar_ecu_composition or not ar_ecu_composition.CONNECTORS:
                return assembly_connectors
            for assembly_connector in ar_ecu_composition.CONNECTORS.ASSEMBLY_SW_CONNECTOR:
                connection = {}
                # PPort
                pport_swc_name = assembly_connector.PROVIDER_IREF.CONTEXT_COMPONENT_REF.valueOf_.split("/")[-1]
                pport = asw_autosar_dict.find(assembly_connector.PROVIDER_IREF.TARGET_P_PORT_REF.valueOf_)
                if pport is None:
                    continue
                pport_name = get_short_name(pport)
                if hasattr(pport, "PROVIDED_INTERFACE_TREF"):
                    pport_interface_name = pport.PROVIDED_INTERFACE_TREF.valueOf_.split("/")[-1]
                elif hasattr(pport, "PROVIDED_REQUIRED_INTERFACE_TREF"):
                    pport_interface_name = pport.PROVIDED_REQUIRED_INTERFACE_TREF.valueOf_.split("/")[-1]
                connection.update({"pport_swc_name": pport_swc_name})
                connection.update({"pport_name": pport_name})
                connection.update({"pport_interface_name": pport_interface_name})
                if "PR-PORT" in pport.original_tagname_:
                    pport_direction = "PR-Port"
                elif "P-PORT" in pport.original_tagname_:
                    pport_direction = "P-Port"
                else:
                    pass
                connection.update({"pport_direction": pport_direction})
                # RPort
                rport_swc_name = assembly_connector.REQUESTER_IREF.CONTEXT_COMPONENT_REF.valueOf_.split("/")[-1]
                rport = asw_autosar_dict.find(assembly_connector.REQUESTER_IREF.TARGET_R_PORT_REF.valueOf_)
                if not rport:
                    continue
                rport_name = get_short_name(rport)
                if hasattr(rport, "REQUIRED_INTERFACE_TREF"):
                    rport_interface_name = rport.REQUIRED_INTERFACE_TREF.valueOf_.split("/")[-1]
                elif hasattr(rport, "PROVIDED_REQUIRED_INTERFACE_TREF"):
                    rport_interface_name = rport.PROVIDED_REQUIRED_INTERFACE_TREF.valueOf_.split("/")[-1]
                connection.update({"rport_swc_name": rport_swc_name})
                connection.update({"rport_name": rport_name})
                connection.update({"rport_interface_name": rport_interface_name})
                if "PR-PORT" in rport.original_tagname_:
                    rport_direction = "PR-Port"
                elif "R-PORT" in rport.original_tagname_:
                    rport_direction = "R-Port"
                else:
                    pass
                connection.update({"rport_direction": rport_direction})
                connection.update({"short_name": get_short_name(assembly_connector)})
                connector_name = "_".join([pport_swc_name, pport_name, rport_swc_name, rport_name])
                assembly_connectors.update({connector_name: connection})
                r_swc_port = rport_swc_name + "_" + rport_name
                p_swc_port = pport_swc_name + "_" + pport_name
                if p_swc_port not in port_connections:
                    port_connections.update({p_swc_port: []})
                if r_swc_port not in port_connections[p_swc_port]:
                    port_connections[p_swc_port].append(r_swc_port)
                if r_swc_port not in port_connections:
                    port_connections.update({r_swc_port: []})
                if p_swc_port not in port_connections[r_swc_port]:
                    port_connections[r_swc_port].append(p_swc_port)
        return assembly_connectors, port_connections

    @classmethod
    def get_all_component_name_to_update(cls, all_ports_dict, category):
        """
        port_mapping界面获取所有包含non-service port的swc list
        service_mapping界面获取所有包含service port的swc list
        """
        child_item_list = []
        if not all_ports_dict:
            return child_item_list
        for port in all_ports_dict["pports"].values():
            for value in port.values():
                if "port_mapping" in category:
                    if value["Is_service"] == "false" and value["Component"] not in child_item_list:
                        child_item_list.append(value["Component"])
                elif "service_mapping" in category:
                    if value["Is_service"] == "true" and value["Component"] not in child_item_list:
                        child_item_list.append(value["Component"])
        for port in all_ports_dict["rports"].values():
            for value in port.values():
                if "port_mapping" in category:
                    if value["Is_service"] == "false" and value["Component"] not in child_item_list:
                        child_item_list.append(value["Component"])
                elif "service_mapping" in category:
                    if value["Is_service"] == "true" and value["Component"] not in child_item_list:
                        child_item_list.append(value["Component"])
        child_item_list.sort(reverse=False)
        return child_item_list

    @classmethod
    def update_all_ports_with_connector(
        cls,
        selected_data,
        row_data,
        all_ports_dict,
        all_ports_direction,
        autosar_system_class,
        autosar_asw_class,
        all_ports_list,
    ):
        """
        根据连接信息或者新增的连接跟新主界面port列表
        """
        port_connect_to_save = {}
        if selected_data or row_data:
            if selected_data and row_data:
                # 如果是有选择的数据,代表右键添加新增加的连接
                for value in selected_data:
                    if row_data[MT_Index.Port_Direction] == "P-Port":
                        component_port = value["Component Prototype"] + "_" + value["Port Prototype"]
                        port_connect_to_save = cls.update_all_ports_list(
                            row_data[MT_Index.Component],
                            row_data[MT_Index.Port],
                            row_data[MT_Index.Port_Interface],
                            "P-Port",
                            value["Component Prototype"],
                            value["Port Prototype"],
                            value["Port Interface"],
                            all_ports_direction[component_port],
                            all_ports_list,
                            port_connect_to_save,
                        )
                    elif row_data[MT_Index.Port_Direction] == "R-Port":
                        component_port = value["Component Prototype"] + "_" + value["Port Prototype"]
                        port_connect_to_save = cls.update_all_ports_list(
                            value["Component Prototype"],
                            value["Port Prototype"],
                            value["Port Interface"],
                            all_ports_direction[component_port],
                            row_data[MT_Index.Component],
                            row_data[MT_Index.Port],
                            row_data[MT_Index.Port_Interface],
                            "R-Port",
                            all_ports_list,
                            port_connect_to_save,
                        )
                    elif row_data[MT_Index.Port_Direction] == "PR-Port":
                        component_port = row_data[MT_Index.Component] + "_" + row_data[MT_Index.Port]
                        conn_component_port = value["Component Prototype"] + "_" + value["Port Prototype"]
                        mapping_list = [
                            row_data[MT_Index.Port],
                            row_data[MT_Index.Component],
                            component_port,
                            value["Port Prototype"],
                            value["Component Prototype"],
                            conn_component_port,
                        ]
                        connector_name, _, _ = cls.get_the_direction_of_selected_prport(mapping_list, all_ports_dict)
                        if connector_name.startswith(component_port):
                            port_connect_to_save = cls.update_all_ports_list(
                                row_data[MT_Index.Component],
                                row_data[MT_Index.Port],
                                row_data[MT_Index.Port_Interface],
                                "PR-Port",
                                value["Component Prototype"],
                                value["Port Prototype"],
                                value["Port Interface"],
                                all_ports_direction[conn_component_port],
                                all_ports_list,
                                port_connect_to_save,
                            )
                        elif connector_name.startswith(conn_component_port):
                            port_connect_to_save = cls.update_all_ports_list(
                                value["Component Prototype"],
                                value["Port Prototype"],
                                value["Port Interface"],
                                all_ports_direction[conn_component_port],
                                row_data[MT_Index.Component],
                                row_data[MT_Index.Port],
                                row_data[MT_Index.Port_Interface],
                                "PR-Port",
                                all_ports_list,
                                port_connect_to_save,
                            )
                return port_connect_to_save
            if row_data and not selected_data:
                # 如果是只有row_data,代表是通过UI助手添加的连接
                for value in row_data:
                    if value[MT_Index.Port_Direction] == "P-Port":
                        component_port = value[MT_Index.Conn_Component] + "_" + value[MT_Index.Conn_Port]
                        port_connect_to_save = cls.update_all_ports_list(
                            value[MT_Index.Component],
                            value[MT_Index.Port],
                            value[MT_Index.Port_Interface],
                            "P-Port",
                            value[MT_Index.Conn_Component],
                            value[MT_Index.Conn_Port],
                            value[MT_Index.Conn_Port_Interface],
                            all_ports_direction[component_port],
                            all_ports_list,
                            port_connect_to_save,
                        )
                    elif value[MT_Index.Port_Direction] == "R-Port":
                        component_port = value[MT_Index.Conn_Component] + "_" + value[MT_Index.Conn_Port]
                        port_connect_to_save = cls.update_all_ports_list(
                            value[MT_Index.Conn_Component],
                            value[MT_Index.Conn_Port],
                            value[MT_Index.Conn_Port_Interface],
                            all_ports_direction[component_port],
                            value[MT_Index.Component],
                            value[MT_Index.Port],
                            value[MT_Index.Port_Interface],
                            "R-Port",
                            all_ports_list,
                            port_connect_to_save,
                        )
                    elif value[MT_Index.Port_Direction] == "PR-Port":
                        mapping_list = []
                        component_port = value[MT_Index.Component] + "_" + value[MT_Index.Port]
                        conn_component_port = value[MT_Index.Conn_Component] + "_" + value[MT_Index.Conn_Port]
                        mapping_list = [
                            value[MT_Index.Port],
                            value[MT_Index.Component],
                            component_port,
                            value[MT_Index.Conn_Port],
                            value[MT_Index.Conn_Component],
                            conn_component_port,
                        ]
                        connector_name, _, _ = cls.get_the_direction_of_selected_prport(mapping_list, all_ports_dict)
                        if connector_name.startswith(component_port):
                            port_connect_to_save = cls.update_all_ports_list(
                                value[MT_Index.Component],
                                value[MT_Index.Port],
                                value[MT_Index.Port_Interface],
                                "PR-Port",
                                value[MT_Index.Conn_Component],
                                value[MT_Index.Conn_Port],
                                value[MT_Index.Conn_Port_Interface],
                                all_ports_direction[conn_component_port],
                                all_ports_list,
                                port_connect_to_save,
                            )
                        elif connector_name.startswith(conn_component_port):
                            port_connect_to_save = cls.update_all_ports_list(
                                value[MT_Index.Conn_Component],
                                value[MT_Index.Conn_Port],
                                value[MT_Index.Conn_Port_Interface],
                                all_ports_direction[conn_component_port],
                                value[MT_Index.Component],
                                value[MT_Index.Port],
                                value[MT_Index.Port_Interface],
                                "PR-Port",
                                all_ports_list,
                                port_connect_to_save,
                            )
                return port_connect_to_save
        else:
            # 代表从FlatExtract中获取连接信息,再根据connetors信息更新ports
            if "FlatExtract" not in autosar_system_class:
                return [], []
            assembly_connectors, port_connections = cls.get_port_mapping_port_connections_from_flatextract(
                autosar_system_class["FlatExtract"], autosar_asw_class
            )
            # 根据connector信息得到连接好的信息
            for _, connector in assembly_connectors.items():
                if connector["pport_name"] not in all_ports_dict["pports"]:
                    # pport不在当前ports列表中，说明不是同一类的port，直接跳过
                    continue
                cls.update_all_ports_list(
                    connector["pport_swc_name"],
                    connector["pport_name"],
                    connector["pport_interface_name"],
                    connector["pport_direction"],
                    connector["rport_swc_name"],
                    connector["rport_name"],
                    connector["rport_interface_name"],
                    connector["rport_direction"],
                    all_ports_list,
                    {},
                )
            return assembly_connectors, port_connections

    @classmethod
    def update_all_ports_list(
        cls,
        p_swc,
        pport,
        p_interface,
        p_direct,
        r_swc,
        rport,
        r_interface,
        r_direct,
        all_ports_list=[],
        port_connect_to_save={},
    ):
        """
        根据连接关系来更新port列表,并获得要保存的port信息
        """
        # p-port方向的连接
        mapped_pport_list = [""] * len(MT_Index)
        mapped_pport_list[MT_Index.Port] = pport  # type: ignore
        mapped_pport_list[MT_Index.Completed] = "√"  # type: ignore
        mapped_pport_list[MT_Index.Component] = p_swc
        mapped_pport_list[MT_Index.Port_Interface] = p_interface
        mapped_pport_list[MT_Index.Conn_Component] = r_swc
        mapped_pport_list[MT_Index.Conn_Port] = rport
        mapped_pport_list[MT_Index.Conn_Port_Interface] = r_interface
        mapped_pport_list[MT_Index.Port_Direction] = p_direct
        # p-port方向的未连接
        unmapped_pport_list = [""] * len(MT_Index)
        unmapped_pport_list[MT_Index.Port] = pport
        unmapped_pport_list[MT_Index.Completed] = ""
        unmapped_pport_list[MT_Index.Component] = p_swc
        unmapped_pport_list[MT_Index.Port_Interface] = p_interface
        unmapped_pport_list[MT_Index.Port_Direction] = p_direct
        connector_name = "_".join(
            [
                mapped_pport_list[MT_Index.Component],
                mapped_pport_list[MT_Index.Port],
                mapped_pport_list[MT_Index.Conn_Component],
                mapped_pport_list[MT_Index.Conn_Port],
            ]
        )
        if mapped_pport_list not in all_ports_list and port_connect_to_save is not None:
            port_connect_to_save[connector_name] = mapped_pport_list

        if unmapped_pport_list in all_ports_list:
            all_ports_list[all_ports_list.index(unmapped_pport_list)] = mapped_pport_list
        elif mapped_pport_list not in all_ports_list:
            all_ports_list.append(mapped_pport_list)

        # r-port方向的连接
        mapped_rport_list = [""] * len(MT_Index)
        mapped_rport_list[MT_Index.Port] = rport
        mapped_rport_list[MT_Index.Completed] = "√"
        mapped_rport_list[MT_Index.Component] = r_swc
        mapped_rport_list[MT_Index.Port_Interface] = r_interface
        mapped_rport_list[MT_Index.Conn_Component] = p_swc
        mapped_rport_list[MT_Index.Conn_Port] = pport  # type: ignore
        mapped_rport_list[MT_Index.Conn_Port_Interface] = p_interface  # type: ignore
        mapped_rport_list[MT_Index.Port_Direction] = r_direct
        # r-port方向的未连接
        unmapped_rport_list = [""] * len(MT_Index)
        unmapped_rport_list[MT_Index.Port] = rport  # type: ignore
        unmapped_rport_list[MT_Index.Completed] = ""  # type: ignore
        unmapped_rport_list[MT_Index.Component] = r_swc
        unmapped_rport_list[MT_Index.Port_Interface] = r_interface
        unmapped_rport_list[MT_Index.Port_Direction] = r_direct
        if unmapped_rport_list in all_ports_list:
            all_ports_list[all_ports_list.index(unmapped_rport_list)] = mapped_rport_list
        elif mapped_rport_list not in all_ports_list:
            all_ports_list.append(mapped_rport_list)
        return port_connect_to_save

    @classmethod
    def get_main_table_data(cls, param_dict, all_ports_list):
        if not all_ports_list:
            return []
        main_table_data = []
        main_table_data_add_index = []
        selected_swc_name = param_dict["swc_name"]
        selected_direction = param_dict["item_name"]
        selected_filter = param_dict["filter_name"]

        if selected_swc_name == "" or selected_swc_name is None:
            for port in all_ports_list:
                if selected_direction == "PR":
                    if any(selected_filter.lower() in word.lower() for word in port):
                        main_table_data.append(port)
                elif selected_direction == "P":
                    if ("P-Port" in port or "PR-Port" in port) and any(
                        selected_filter.lower() in word.lower() for word in port
                    ):
                        main_table_data.append(port)
                elif selected_direction == "R":
                    if ("R-Port" in port or "PR-Port" in port) and any(
                        selected_filter.lower() in word.lower() for word in port
                    ):
                        main_table_data.append(port)
        else:
            for port in all_ports_list:
                if selected_direction == "PR":
                    if (
                        any(selected_filter.lower() in word.lower() for word in port)
                        and selected_swc_name == port[MT_Index.Component]
                    ):
                        main_table_data.append(port)
                elif selected_direction == "P":
                    if (
                        ("P-Port" in port or "PR-Port" in port)
                        and any(selected_filter.lower() in word.lower() for word in port)
                        and selected_swc_name == port[MT_Index.Component]
                    ):
                        main_table_data.append(port)
                elif selected_direction == "R":
                    if (
                        ("R-Port" in port or "PR-Port" in port)
                        and any(selected_filter.lower() in word.lower() for word in port)
                        and selected_swc_name == port[MT_Index.Component]
                    ):
                        main_table_data.append(port)
        if not main_table_data:
            return []
        main_table_data.sort(key=lambda x: (x[MT_Index.Component], x[MT_Index.Port]))
        for port_connection in main_table_data:
            curr_row_data = []
            main_table_data_add_index.append(curr_row_data)
            for col, item in enumerate(port_connection):
                curr_row_data.append((col, item))
        return main_table_data_add_index

    @classmethod
    def manual_remove_port_mapping(
        cls,
        selected_data_dict,
        autosar_system_class,
        all_ports_dict,
        all_ports_direction,
        all_ports_list,
        assembly_connectors,
        port_connections,
    ):
        # 删除某个连接
        connector_name = None
        remove_port_connect = {}
        if "FlatExtract" not in autosar_system_class or len(selected_data_dict) == 0:
            return
        for row_value in selected_data_dict.values():
            if (
                row_value[MT_Index.Conn_Component : MT_Index.Port_Interface_Mapping] == [""] * 3
                and row_value[MT_Index.Completed] == ""
            ):
                # 未连接port,直接跳过,不做处理
                continue
            if row_value[MT_Index.Port_Direction] == "P-Port":
                connector_name = "_".join(
                    [
                        row_value[MT_Index.Component],
                        row_value[MT_Index.Port],
                        row_value[MT_Index.Conn_Component],
                        row_value[MT_Index.Conn_Port],
                    ]
                )
            elif row_value[MT_Index.Port_Direction] == "R-Port":
                connector_name = "_".join(
                    [
                        row_value[MT_Index.Conn_Component],
                        row_value[MT_Index.Conn_Port],
                        row_value[MT_Index.Component],
                        row_value[MT_Index.Port],
                    ]
                )
            elif row_value[MT_Index.Port_Direction] == "PR-Port":
                component_port = row_value[MT_Index.Component] + "_" + row_value[MT_Index.Port]
                conn_component_port = row_value[MT_Index.Conn_Component] + "_" + row_value[MT_Index.Conn_Port]
                mapping_list = [
                    row_value[MT_Index.Port],
                    row_value[MT_Index.Component],
                    component_port,
                    row_value[MT_Index.Conn_Port],
                    row_value[MT_Index.Conn_Component],
                    conn_component_port,
                ]
                connector_name, _, _ = cls.get_the_direction_of_selected_prport(mapping_list, all_ports_dict)
            cls.__remove_ports_with_connector(row_value, all_ports_direction, all_ports_list)
            remove_port_connect.update({connector_name: row_value})
            mapping_info = cls.get_port_mapping_info(remove_port_connect, all_ports_dict)
            short_name = assembly_connectors[connector_name]["short_name"]
            AutosarUtil.remove_assembly_sw_connector(autosar_system_class["FlatExtract"], short_name)
            cls.update_port_connection(
                connector_name,
                mapping_info[connector_name],
                all_ports_dict,
                all_ports_direction,
                assembly_connectors,
                port_connections,
                "del",
            )

    @classmethod
    def __remove_ports_with_connector(cls, selected_data, all_ports_direction, all_ports_list):
        if selected_data:
            # 选中行未连接状态
            selected_data_uncon = selected_data.copy()
            selected_data_uncon[MT_Index.Completed] = selected_data_uncon[MT_Index.Conn_Component] = (
                selected_data_uncon[MT_Index.Conn_Port]
            ) = selected_data_uncon[MT_Index.Conn_Port_Interface] = ""
            # 反向连接行连接时的状态
            rev_selected_data = selected_data.copy()
            rev_selected_data[MT_Index.Port] = selected_data[MT_Index.Conn_Port]
            rev_selected_data[MT_Index.Component] = selected_data[MT_Index.Conn_Component]
            rev_selected_data[MT_Index.Port_Interface] = selected_data[MT_Index.Conn_Port_Interface]
            rev_selected_data[MT_Index.Conn_Component] = selected_data[MT_Index.Component]
            rev_selected_data[MT_Index.Conn_Port] = selected_data[MT_Index.Port]
            rev_selected_data[MT_Index.Conn_Port_Interface] = selected_data[MT_Index.Port_Interface]
            component_port = selected_data[MT_Index.Conn_Component] + "_" + selected_data[MT_Index.Conn_Port]
            rev_selected_data[MT_Index.Port_Direction] = all_ports_direction[component_port]
            # 反向连接行未连接时的状态
            rev_selected_data_uncon = rev_selected_data.copy()
            rev_selected_data_uncon[MT_Index.Completed] = rev_selected_data_uncon[MT_Index.Conn_Component] = (
                rev_selected_data_uncon[MT_Index.Conn_Port]
            ) = rev_selected_data_uncon[MT_Index.Conn_Port_Interface] = ""

            if selected_data_uncon in all_ports_list:
                all_ports_list.pop(all_ports_list.index(selected_data_uncon))
            all_ports_list[all_ports_list.index(selected_data)] = selected_data_uncon
            for port in all_ports_list:
                if all(element in port for element in selected_data_uncon) and selected_data_uncon != port:
                    all_ports_list.pop(all_ports_list.index(selected_data_uncon))
                    break
            if rev_selected_data_uncon in all_ports_list:
                all_ports_list.pop(all_ports_list.index(rev_selected_data_uncon))
            all_ports_list[all_ports_list.index(rev_selected_data)] = rev_selected_data_uncon
            for port in all_ports_list:
                if all(element in port for element in rev_selected_data_uncon) and rev_selected_data_uncon != port:
                    all_ports_list.pop(all_ports_list.index(rev_selected_data_uncon))
                    break

    @classmethod
    def update_port_connection(
        cls, connector_name, info, all_ports_dict, all_ports_direction, assembly_connectors, port_connections, mode
    ):
        """
        更新预处理之后的连接信息
        """
        p_swc = info["provider_iref"]["context_component_ref"].split("/")[-1]
        p_port = info["provider_iref"]["target_pport_ref"].split("/")[-1]
        p_swc_port = p_swc + "_" + p_port
        p_interf = all_ports_dict["pports"][p_port][p_swc_port]["Interface"].split("/")[-1]
        p_direct = all_ports_direction[p_swc_port]
        r_swc = info["requester_iref"]["context_component_ref"].split("/")[-1]
        r_port = info["requester_iref"]["target_rport_ref"].split("/")[-1]
        r_swc_port = r_swc + "_" + r_port
        r_interf = all_ports_dict["rports"][r_port][r_swc_port]["Interface"].split("/")[-1]
        r_direct = all_ports_direction[r_swc_port]
        if mode == "add":
            short_name = (
                cls.update_short_name_length(connector_name)
                if connector_name and len(connector_name) > 128
                else connector_name
            )
            assembly_connectors.update(
                {
                    connector_name: {
                        "pport_swc_name": p_swc,
                        "pport_name": p_port,
                        "pport_interface_name": p_interf,
                        "pport_direction": p_direct,
                        "rport_swc_name": r_swc,
                        "rport_name": r_port,
                        "rport_interface_name": r_interf,
                        "rport_direction": r_direct,
                        "short_name": short_name,
                    }
                }
            )

            if p_swc_port in port_connections:
                port_connections[p_swc_port].append(r_swc_port)
            else:
                port_connections.update({p_swc_port: [r_swc_port]})
            if r_swc_port in port_connections:
                port_connections[r_swc_port].append(p_swc_port)
            else:
                port_connections.update({r_swc_port: [p_swc_port]})
        elif mode == "del":
            if connector_name in assembly_connectors:
                del assembly_connectors[connector_name]

            if p_swc_port in port_connections:
                port_connections[p_swc_port].remove(r_swc_port)

            if r_swc_port in port_connections:
                port_connections[r_swc_port].remove(p_swc_port)

    @classmethod
    def get_all_connected_and_unconnected_ports_list(cls, flatextract_class, all_ports_dict, logs, all_swc_prototypes):
        """
        获取所有已连接、未连接的ports,添加到log中,方便用户查看
        Args:
            flatextract_class (class)
            all_ports_dict (dict)
            logs (list)
        """
        connected_ports_set = set()
        connected_ports_list = []
        unconnected_ports_set = set()
        unconnected_ports_list = []
        connected_ports = cls.get_assembly_connected_ports_from_flat(
            flatextract_class, all_ports_dict, all_swc_prototypes
        )
        delegation_connected_ports = cls.get_delegation_connected_ports_from_flat(flatextract_class, all_swc_prototypes)
        for _, value in all_ports_dict["pports"].items():
            for swc_port, port in value.items():
                if len(connected_ports.get(swc_port, [])) == 0:
                    port_list = [port["Component"], port["Name"], port["Interface"].split("/")[-1]]
                    if swc_port in delegation_connected_ports:
                        port_list.append("Have Delegation Connector!")
                    if swc_port not in unconnected_ports_set:
                        unconnected_ports_set.add(swc_port)
                        unconnected_ports_list.append(port_list)
                else:
                    for connected_port in connected_ports.get(swc_port, []):
                        port_list = [port["Component"], port["Name"], port["Interface"].split("/")[-1]]
                        port_list.extend(connected_port)
                        if swc_port not in connected_ports_set:
                            connected_ports_set.add(swc_port)
                            connected_ports_list.append(port_list)
        for value in all_ports_dict["rports"].values():
            for swc_port, port in value.items():
                if len(connected_ports.get(swc_port, [])) == 0:
                    port_list = [port["Component"], port["Name"], port["Interface"].split("/")[-1]]
                    if swc_port in delegation_connected_ports:
                        port_list.append("Have Delegation Connector!")
                    if swc_port not in unconnected_ports_set:
                        unconnected_ports_set.add(swc_port)
                        unconnected_ports_list.append(port_list)
                else:
                    for connected_port in connected_ports.get(swc_port, []):
                        port_list = [port["Component"], port["Name"], port["Interface"].split("/")[-1]]
                        port_list.extend(connected_port)
                        if swc_port not in connected_ports_set:
                            connected_ports_set.add(swc_port)
                            connected_ports_list.append(port_list)
        connected_ports_list.sort(key=lambda x: (x[TT_Index.Component], x[TT_Index.Port]))
        unconnected_ports_list.sort(key=lambda x: (x[TT_Index.Component], x[TT_Index.Port]))
        logs.append(connected_ports_list)
        logs.append(unconnected_ports_list)

    @classmethod
    def get_assembly_connected_ports_from_flat(cls, flatextract_class, all_ports_dict, all_swc_prototypes):
        """
        根据Flatextract.arxml获取所有已连接的port mapping信息
        Args:
            flatextract_class (class)

        Returns: dict
        """
        connected_ports = {}
        for ar_ecu_composition in flatextract_class.find_nodes("COMPOSITION-SW-COMPONENT-TYPE"):
            if not ar_ecu_composition or not ar_ecu_composition.CONNECTORS:
                return connected_ports
            for assembly_connector in ar_ecu_composition.CONNECTORS.ASSEMBLY_SW_CONNECTOR:
                # PPort
                p_swc_base, p_port = assembly_connector.PROVIDER_IREF.TARGET_P_PORT_REF.valueOf_.split("/")[-2:]
                p_swc = all_swc_prototypes[p_swc_base][0] if p_swc_base in all_swc_prototypes else p_swc_base
                p_swc_port = p_swc + "_" + p_port
                p_interf = (
                    all_ports_dict["pports"][p_port][p_swc_port]["Interface"].split("/")[-1]
                    if p_port in all_ports_dict["pports"]
                    else None
                )
                # RPort
                r_swc_base, r_port = assembly_connector.REQUESTER_IREF.TARGET_R_PORT_REF.valueOf_.split("/")[-2:]
                r_swc = all_swc_prototypes[r_swc_base][0] if r_swc_base in all_swc_prototypes else r_swc_base
                r_swc_port = r_swc + "_" + r_port
                r_interf = (
                    all_ports_dict["rports"][r_port][r_swc_port]["Interface"].split("/")[-1]
                    if r_port in all_ports_dict["rports"]
                    else None
                )

                if p_interf and r_interf:
                    if p_swc_port not in connected_ports:
                        connected_ports.update({p_swc_port: []})
                    if [r_swc, r_port, r_interf] not in connected_ports[p_swc_port]:
                        connected_ports[p_swc_port].append([r_swc, r_port, r_interf])
                    if r_swc_port not in connected_ports:
                        connected_ports.update({r_swc_port: []})
                    if [p_swc, p_port, p_interf] not in connected_ports[r_swc_port]:
                        connected_ports[r_swc_port].append([p_swc, p_port, p_interf])
        return connected_ports

    @classmethod
    def get_delegation_connected_ports_from_flat(cls, flatextract_class, all_swc_prototypes):
        """
        根据Flatextract.arxml获取所有已连接的port信息
        Args:
            flatextract_class (class)

        Returns: connected_ports(set)
        """
        connected_ports_set = set()
        for ar_ecu_composition in flatextract_class.find_nodes("COMPOSITION-SW-COMPONENT-TYPE"):
            if not ar_ecu_composition or not ar_ecu_composition.CONNECTORS:
                return connected_ports_set
            for delegation_connector in ar_ecu_composition.CONNECTORS.DELEGATION_SW_CONNECTOR:
                p_swc_port, r_swc_port = None, None
                if delegation_connector.INNER_PORT_IREF.R_PORT_IN_COMPOSITION_INSTANCE_REF:
                    r_swc_base, r_port = (
                        delegation_connector.INNER_PORT_IREF.R_PORT_IN_COMPOSITION_INSTANCE_REF.TARGET_R_PORT_REF.valueOf_.split(
                            "/"
                        )[
                            -2:
                        ]
                    )
                    r_swc = all_swc_prototypes[r_swc_base][0] if r_swc_base in all_swc_prototypes else r_swc_base
                    r_swc_port = r_swc + "_" + r_port
                elif delegation_connector.INNER_PORT_IREF.P_PORT_IN_COMPOSITION_INSTANCE_REF:
                    p_swc_base, p_port = (
                        delegation_connector.INNER_PORT_IREF.P_PORT_IN_COMPOSITION_INSTANCE_REF.TARGET_P_PORT_REF.valueOf_.split(
                            "/"
                        )[
                            -2:
                        ]
                    )
                    p_swc = all_swc_prototypes[p_swc_base][0] if p_swc_base in all_swc_prototypes else p_swc_base
                    p_swc_port = p_swc + "_" + p_port
                if p_swc_port:
                    connected_ports_set.add(p_swc_port)
                if r_swc_port:
                    connected_ports_set.add(r_swc_port)
        return connected_ports_set

    @classmethod
    def update_short_name_length(cls, short_name) -> str:
        if short_name and len(short_name) > 128:
            hash_obj = hashlib.sha1(short_name[120:].encode(encoding="utf-8"))
            hash_str = hash_obj.hexdigest()
            short_name = short_name[:120] + hash_str[:8]
        return short_name


class MT_Index(IntEnum):
    # port mapping---main title list
    # head_titles = ["Port Prototype", "Completed", "Component Prototype", "Port Interface",
    # "Connected Component Prototype", "Connected Port Prototype", "Connected Port Interface",
    # "Port inteface Mapping", "Mapped Syetem Signal", "Origin Context", "Origin Ports",
    # "Local Cluster RIPS Reference", "Corss Cluster RIPS Reference", "Flat Instance Descriptor", "Port Direction"]
    Port = 0  # Port_Prototype
    Completed = 1  #
    Component = 2
    Port_Interface = 3
    Conn_Component = 4
    Conn_Port = 5
    Conn_Port_Interface = 6
    Port_Interface_Mapping = 7
    Mapped_System_Signal = 8
    Origin_Context = 9
    Origin_Ports = 10
    Local_Cluster_RIPS_Reference = 11
    Cross_Cluster_RIPS_Reference = 12
    Flat_Instance_Descriptor = 13
    Port_Direction = 14

    @classmethod
    def get_header_list(cls):
        return [
            "Port Prototype",
            "Completed",
            "Component Prototype",
            "Port Interface",
            "Connected Component Prototype",
            "Connected Port Prototype",
            "Connected Port Interface",
            "Port inteface Mapping",
            "Mapped Syetem Signal",
            "Origin Context",
            "Origin Ports",
            "Local Cluster RIPS Reference",
            "Corss Cluster RIPS Reference",
            "Flat Instance Descriptor",
            "Port Direction",
        ]


class FT_Index(IntEnum):
    # port mapping---first popups title list

    # head_titles = ["Selected", "Component Prototype", "Component type"]
    Selected = 0
    Component = 1
    Component_Type = 2


class ST_Index(IntEnum):
    # port mapping---second popups title list

    # head_titles = ["Selected", "Component Prototype", "Port Prototype", "Already Connected"]
    Selected = 0
    Component = 1
    Port = 2
    Connected = 3


class TT_Index(IntEnum):
    # port mapping---third popups title list

    # head_titles = ["Component Prototype", "Port Prototype", "Port Interface", "Connected Component Prototype",
    # "Connected Port Prototype", "Connected Port Interface", "Port inteface Mapping"]
    Component = 0
    Port = 1
    Port_Interface = 2
    Conn_Component = 3
    Conn_Port = 4
    Conn_Port_Interface = 5
    Port_Interface_Mapping = 6
    Port_Direction = 7


class CON_Index(IntEnum):
    # port mapping---right connected popups title list
    # head_titles = ["Selected", "Compatibility", "Component Prototype", "Port Prototype", "Port Interface",
    # "Port Interface Mapping", "Port Interface Mapping Set"]
    Selected = 0
    Compatibility = 1
    Component = 2
    Port = 3
    Port_Interface = 4
    Port_Interface_Mapping = 5
    Port_Interface_Mapping_Set = 6


class _MappingFilterArgument:

    def __init__(self, component=None, component_port_set=set(), direction=None, prefix=None, postfix=None):
        self.Component = component
        self.component_port_set = component_port_set
        self.Direction = direction
        self.Prefix = prefix
        self.Postfix = postfix


class Compatibility(IntEnum):
    # port mapping---right connected popups title list
    # head_titles = ["Selected", "Compatibility", "Component Prototype", "Port Prototype", "Port Interface",
    # "Port Interface Mapping", "Port Interface Mapping Set"]
    not_match = 0
    partial_match = 1
    full_match = 2
