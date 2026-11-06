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
from autosar44 import autosar44
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from func_module.mapping.port_mapping_core import PortMappingCore
from basic_func_module.autosar_utils.utils import (
    get_short_name,
    get_context_component_ref,
    get_target_p_port_ref,
    get_target_r_port_ref,
)
from func_module.health_monitor.logger import logger


CUR_FILE_PATH = os.path.dirname(os.path.realpath(__file__))


class FlatExtractArxmlManager:

    @classmethod
    def update_flatextract_info_from_asw_arxml(cls, asw_autosar_dict, system_autosar_dict):
        autosar_flatextract = None
        if "FlatExtract" in system_autosar_dict:
            autosar_flatextract = system_autosar_dict["FlatExtract"]
        if not isinstance(autosar_flatextract, autosar44.AUTOSAR):
            logger.error("FlatExtract is not AUTOSAR object")
            return False

        # # 对flatextract.arxml中进行去重操作,只在出现重复connector后临时使用
        # self.del_all_repeat_assembly_sw_connectors(self.autosar_flatextract)
        # return

        # 方案1.
        # 1. 如果导入的ARXML中有连接关系，那么将FlatExtract中的连接关系全部删除，然后将导入的ARXML中的连接关系复制过去
        # 2. 如果导入的ARXML中没有连接关系，那么将FlatExtract中的连接关系全部删除
        # 当前方案弃用
        # if asw_connectors:
        #     # 如果导入的arxml中有连接信息，将FlatExtract.arxml中的application-port的连接信息删除，
        #     # 将导入的arxml中的application-port连接信息拷贝到FlatExtract中
        #     self.del_all_assembly_sw_connectors(self.autosar_flatextract)
        #     # 将导入的arxml中的所有连接信息保存到FlatExtract.arxml中
        #     self.add_all_assembly_sw_connectors(self.autosar_flatextract, asw_connectors, all_autosar)
        # else: # 如果导入的arxml中没有连接信息
        #     # 先根据port口，如果FlatExtract中的port口不在导入的arxml中，将连接关系删除
        #     self.get_connectors_to_be_delete(all_autosar, self.autosar_flatextract)
        #     # 然后将merged_autosar中的connector信息保存到FlatExtract中
        #     # self.add_assembly_sw_connectors(asw_autosar_dict, self.autosar_flatextract)

        # 方案2.
        # 1. 导入arxml不管其中有没有连接关系，先判断FlatExtract中的连接关系相关的SWC和PORT在导入的ARXML中是否存在
        # 如果存在，那么保留连接信息;如果不存在,那么将连接关系删除
        # 2. 将导入ARXML中的连接信息，经过去重后，复制到FlatExtract中
        # 采用此方案
        # 先判断连接信息是否存在于ARXML中，如果不存在的话，就先删除掉
        all_ports = {}
        flatextract_connectors = None
        asw_connectors = None
        if asw_autosar_dict:
            asw_connectors = asw_autosar_dict.find_nodes("ASSEMBLY-SW-CONNECTOR")
        if autosar_flatextract:
            flatextract_connectors = autosar_flatextract.find_nodes("ASSEMBLY-SW-CONNECTOR")
        all_app_ports = PortMappingCore.get_all_app_ports_dict(asw_autosar_dict).copy()
        all_service_ports = PortMappingCore.get_all_service_ports_dict(asw_autosar_dict).copy()
        all_ports["pports"] = {**all_app_ports["pports"], **all_service_ports["pports"]}
        all_ports["rports"] = {**all_app_ports["rports"], **all_service_ports["rports"]}
        if flatextract_connectors:
            _, short_name_list = cls.get_connectors_to_be_delete(all_ports, flatextract_connectors)
            cls.del_useless_connectors(short_name_list, autosar_flatextract)
        # 添加导入的ARXML中的连接信息
        cls.add_all_assembly_sw_connectors(autosar_flatextract, asw_connectors, all_ports)

        autosar_flatextract = AutosarUtil.update_autosar(autosar_flatextract)
        system_autosar_dict["FlatExtract"] = autosar_flatextract

    @classmethod
    def del_all_assembly_sw_connectors(cls, autosar_flatextract):
        """
        将Flatextract.arxml中所有的连接都删除
        """
        assembly_sw_connectors = autosar_flatextract.find_nodes("ASSEMBLY-SW-CONNECTOR")
        for assembly_sw_connector in assembly_sw_connectors:
            assembly_sw_connector.get_parent().ASSEMBLY_SW_CONNECTOR.remove(assembly_sw_connector)

    @classmethod
    def add_all_assembly_sw_connectors(cls, autosar_flatextract, asw_connectors, all_ports):
        connectors_dict = {}
        flatextract_assembly_sw_connector_names = []
        flatextract_connectors = autosar_flatextract.find_nodes("CONNECTORS")
        flatextract_assembly_sw_connectors = autosar_flatextract.find_nodes("ASSEMBLY-SW-CONNECTOR")
        for flatextract_assembly_sw_connector in flatextract_assembly_sw_connectors:
            # 根据connector name进行判重，而不是根据short name进行判重，
            # 避免short_name不一致，但是connector_name一致的情况下，导入asw.arxml后会存在多份连接
            flatextract_assembly_sw_connector_names.append(cls.get_connector_name(flatextract_assembly_sw_connector))
        if asw_connectors:
            connector_name_list, _ = cls.get_connectors_to_be_delete(all_ports, asw_connectors)
            # 对导入的asw.arxml中的connector通过dict进行去重
            for asw_assembly_sw_connector in asw_connectors:
                connector_name = cls.get_connector_name(asw_assembly_sw_connector)
                if connector_name in connector_name_list:
                    continue
                if connector_name in flatextract_assembly_sw_connector_names:
                    continue
                connectors_dict.update({connector_name: asw_assembly_sw_connector})
            flatextract_connectors[0].ASSEMBLY_SW_CONNECTOR.extend(connectors_dict.values())

    @classmethod
    def get_connector_name(cls, connector):
        pport_swc_name, pport_name = connector.PROVIDER_IREF.TARGET_P_PORT_REF.valueOf_.split("/")[-2:]
        rport_swc_name, rport_name = connector.REQUESTER_IREF.TARGET_R_PORT_REF.valueOf_.split("/")[-2:]
        connector_name = "_".join([pport_swc_name, pport_name, rport_swc_name, rport_name])
        return connector_name

    @classmethod
    def del_useless_connectors(cls, short_name_list, autosar_flatextract={}):
        for short_name in short_name_list:
            AutosarUtil.remove_assembly_sw_connector(autosar_flatextract, short_name)

    @classmethod
    def get_connectors_to_be_delete(cls, all_ports, connectors):
        # 此函数用于判断connector的port是否仍在导入的ARXML中
        connector_name_list = []
        short_name_list = []
        for assembly_sw_connector in connectors:
            index_pport = False
            index_rport = False
            if not assembly_sw_connector.SHORT_NAME:
                continue
            short_name = get_short_name(assembly_sw_connector)
            connector_name = cls.get_connector_name(assembly_sw_connector)
            pport_ref = assembly_sw_connector.PROVIDER_IREF.TARGET_P_PORT_REF.valueOf_
            pport_name = pport_ref.split("/")[-1]
            pport_swc_ref = assembly_sw_connector.PROVIDER_IREF.CONTEXT_COMPONENT_REF.valueOf_
            pport_component = pport_swc_ref.split("/")[-1]
            for pport_value in all_ports["pports"].values():
                for pport in pport_value.values():
                    if pport_name == pport["Name"] and pport_component == pport["Component"]:
                        index_pport = True
                        break

            rport_ref = assembly_sw_connector.REQUESTER_IREF.TARGET_R_PORT_REF.valueOf_
            rport_name = rport_ref.split("/")[-1]
            rport_swc_ref = assembly_sw_connector.REQUESTER_IREF.CONTEXT_COMPONENT_REF.valueOf_
            rport_component = rport_swc_ref.split("/")[-1]
            for rport_value in all_ports["rports"].values():
                for rport in rport_value.values():
                    if rport_name == rport["Name"] and rport_component == rport["Component"]:
                        index_rport = True
                        break

            if index_pport and index_rport:
                continue
            connector_name_list.append(connector_name)
            short_name_list.append(short_name)
        return connector_name_list, short_name_list

    @classmethod
    def get_all_data_mappings_from_flatextract(cls, autosar_flatextract):
        rv = {"sr_signal_mappings": [], "sr_signal_group_mappings": []}
        signal_mapping_list = autosar_flatextract.find_nodes("SENDER-RECEIVER-TO-SIGNAL-MAPPING")
        for signal_mapping in signal_mapping_list:
            mapping_info = cls.paser_sender_receiver_to_signal_mapping(signal_mapping)
            if mapping_info is None:
                continue
            rv["sr_signal_mappings"].append(mapping_info)
        signal_group_mapping_list = autosar_flatextract.find_nodes("SENDER-RECEIVER-TO-SIGNAL-GROUP-MAPPING")
        for signal_group_mapping in signal_group_mapping_list:
            mapping_info = cls.paser_sender_receiver_to_signal_group_mapping(signal_group_mapping)
            if mapping_info is None:
                continue
            rv["sr_signal_group_mappings"].append(mapping_info)
        return rv

    @classmethod
    def paser_sender_receiver_to_signal_mapping(cls, mapping_obj):
        system_signal_ref = _get_value_by_attrs(mapping_obj, ["SYSTEM_SIGNAL_REF", "valueOf_"])
        data_element_iref = _get_value_by_attrs(mapping_obj, ["DATA_ELEMENT_IREF"])
        context_component_ref = getattr(data_element_iref.CONTEXT_COMPONENT_REF[0], "valueOf_", None)
        context_composition_ref = _get_value_by_attrs(data_element_iref, ["CONTEXT_COMPOSITION_REF", "valueOf_"])
        context_port_ref = _get_value_by_attrs(data_element_iref, ["CONTEXT_PORT_REF", "valueOf_"])
        port_type = _get_value_by_attrs(data_element_iref, ["CONTEXT_PORT_REF", "DEST"])
        target_data_prototype_ref = _get_value_by_attrs(data_element_iref, ["TARGET_DATA_PROTOTYPE_REF", "valueOf_"])
        if not system_signal_ref or not context_port_ref or not target_data_prototype_ref:
            return None
        rv = {
            "system_signal_ref": system_signal_ref,
            "data_element_iref": {
                "context_component_ref": context_component_ref,
                "context_composition_ref": context_composition_ref,
                "context_port_ref": context_port_ref,
                "port_type": port_type,
                "target_data_prototype_ref": target_data_prototype_ref,
            },
        }
        return rv

    @classmethod
    def paser_sender_receiver_to_signal_group_mapping(cls, mapping_obj):
        system_signal_group_ref = _get_value_by_attrs(mapping_obj, ["SIGNAL_GROUP_REF", "valueOf_"])
        data_element_iref = _get_value_by_attrs(mapping_obj, ["DATA_ELEMENT_IREF"])
        context_component_ref = getattr(data_element_iref.CONTEXT_COMPONENT_REF[0], "valueOf_", None)
        context_composition_ref = _get_value_by_attrs(data_element_iref, ["CONTEXT_COMPOSITION_REF", "valueOf_"])
        context_port_ref = _get_value_by_attrs(data_element_iref, ["CONTEXT_PORT_REF", "valueOf_"])
        port_type = _get_value_by_attrs(data_element_iref, ["CONTEXT_PORT_REF", "DEST"])
        target_data_prototype_ref = _get_value_by_attrs(data_element_iref, ["TARGET_DATA_PROTOTYPE_REF", "valueOf_"])
        if not system_signal_group_ref or not context_port_ref or not target_data_prototype_ref:
            return None
        type_mapping_list = []
        for record_element_mapping in (
            _get_value_by_attrs(
                mapping_obj,
                [
                    "TYPE_MAPPING",
                    "SENDER_REC_RECORD_TYPE_MAPPING",
                    "RECORD_ELEMENT_MAPPINGS",
                    "SENDER_REC_RECORD_ELEMENT_MAPPING",
                ],
            )
            or []
        ):
            implementation_record_element_ref = _get_value_by_attrs(
                record_element_mapping, ["IMPLEMENTATION_RECORD_ELEMENT_REF", "valueOf_"]
            )
            system_signal_ref = _get_value_by_attrs(record_element_mapping, ["SYSTEM_SIGNAL_REF", "valueOf_"])
            type_mapping_list.append(
                {
                    "implementation_record_element_ref": implementation_record_element_ref,
                    "implementation_record_element": implementation_record_element_ref.split("/")[-1],
                    "system_signal_ref": system_signal_ref,
                    "system_signal": system_signal_ref.split("/")[-1],
                }
            )
        rv = {
            "data_element_iref": {
                "context_component_ref": context_component_ref,
                "context_composition_ref": context_composition_ref,
                "context_port_ref": context_port_ref,
                "port_type": port_type,
                "target_data_prototype_ref": target_data_prototype_ref,
            },
            "signal_group_ref": system_signal_group_ref,
            "type_mapping": type_mapping_list,
        }
        return rv

    @classmethod
    def get_assembly_and_delegation_sw_connector(cls, flatextract_dict):
        sw_connector_dict = {}
        compositions = flatextract_dict.find_nodes("COMPOSITION-SW-COMPONENT-TYPE")
        if compositions:
            # ASSEMBLY_SW_CONNECTOR
            if hasattr(compositions[0].CONNECTORS, "ASSEMBLY_SW_CONNECTOR"):
                assembly_sw_connectors = compositions[0].CONNECTORS.ASSEMBLY_SW_CONNECTOR
                if assembly_sw_connectors:
                    for assembly_sw_connector in assembly_sw_connectors:
                        short_name = get_short_name(assembly_sw_connector)
                        uuid = assembly_sw_connector.UUID
                        conn_dict = {}
                        conn_dict.update({"uuid": uuid})
                        conn_dict.update({"short_name": short_name})
                        conn_dict.update({"type": "ASSEMBLY_SW_CONNECTOR"})
                        conn_dict.update({"provider_iref": {}})
                        # PROVIDER-IREF
                        context_component_ref = get_context_component_ref(assembly_sw_connector.PROVIDER_IREF)
                        context_component_dest = assembly_sw_connector.PROVIDER_IREF.CONTEXT_COMPONENT_REF.DEST
                        target_pport_ref = get_target_p_port_ref(assembly_sw_connector.PROVIDER_IREF)
                        target_pport_dest = assembly_sw_connector.PROVIDER_IREF.TARGET_P_PORT_REF.DEST
                        conn_dict["provider_iref"].update({"context_component_ref": context_component_ref})
                        conn_dict["provider_iref"].update({"context_component_dest": context_component_dest})
                        conn_dict["provider_iref"].update({"target_pport_ref": target_pport_ref})
                        conn_dict["provider_iref"].update({"target_pport_dest": target_pport_dest})
                        # REQUESTER-IREF
                        conn_dict.update({"requester_iref": {}})
                        context_component_ref = get_context_component_ref(assembly_sw_connector.REQUESTER_IREF)
                        context_component_dest = assembly_sw_connector.REQUESTER_IREF.CONTEXT_COMPONENT_REF.DEST
                        target_rport_ref = get_target_r_port_ref(assembly_sw_connector.REQUESTER_IREF)
                        target_rport_dest = assembly_sw_connector.REQUESTER_IREF.TARGET_R_PORT_REF.DEST
                        conn_dict["requester_iref"].update({"context_component_ref": context_component_ref})
                        conn_dict["requester_iref"].update({"context_component_dest": context_component_dest})
                        conn_dict["requester_iref"].update({"target_rport_ref": target_rport_ref})
                        conn_dict["requester_iref"].update({"target_rport_dest": target_rport_dest})
                        conn_key = (
                            f"{conn_dict['provider_iref']['context_component_ref'].split('/')[-1]}_"
                            f"{conn_dict['provider_iref']['target_pport_ref'].split('/')[-1]}_"
                            f"{conn_dict['requester_iref']['context_component_ref'].split('/')[-1]}_"
                            f"{conn_dict['requester_iref']['target_rport_ref'].split('/')[-1]}"
                        )
                        sw_connector_dict[conn_key] = conn_dict
        return sw_connector_dict


def _get_value_by_attrs(obj, attrs_list, _default=None):
    find_value = obj
    if find_value is None or attrs_list is None or len(attrs_list) == 0:
        return _default
    for attr in attrs_list:
        find_value = getattr(find_value, attr, _default)
        if find_value is None or find_value == _default:
            return find_value
    return find_value
