# Load and dump a diagnostics database in CDD format.
import logging
import re
import string
from typing import Dict, List, Tuple
from copy import deepcopy

from xml.etree import ElementTree
from functools import reduce

from .service_inst_parser import parse_service_inst
from .service_inst_parser import parse_parameter_datas as _parse_parameter_datas
from .service_inst_parser import infer_data_type_str as _infer_data_type_str
from .service_inst_parser import load_data_element as _load_data_element
from .service_inst_parser import load_struct_data_element as _load_struct_data_element

from ..did import Did
from ..pid import Pid
from ..vehi_id import Vehi_id
from ..snap_shot import SnapShot
from ..extended_data import ExtendedData
from ..state_group import State, StateGroup
from ..routine import Routine, RoutineService
from ..datatype import DataType
from ..dtc import Dtc, ObdDtc
from ..event import Event
from ..uds_service import UdsService, UdsSubService
from ..internal_database import InternalDatabase
from ...errors import ParseError

LOGGER = logging.getLogger(__name__)

HAS_SUB_SERVICE = {
    int("0x01", 16): False,
    int("0x02", 16): False,
    int("0x03", 16): False,
    int("0x04", 16): False,
    int("0x06", 16): False,
    int("0x07", 16): False,
    int("0x08", 16): False,
    int("0x09", 16): False,
    int("0x0A", 16): False,
    int("0x10", 16): True,
    int("0x11", 16): True,
    int("0x14", 16): False,
    int("0x19", 16): True,
    int("0x22", 16): False,
    int("0x23", 16): False,
    int("0x24", 16): False,
    int("0x27", 16): True,
    int("0x28", 16): True,
    int("0x2A", 16): False,
    int("0x2C", 16): True,
    int("0x2E", 16): False,
    int("0x2F", 16): False,
    int("0x31", 16): True,
    int("0x34", 16): False,
    int("0x35", 16): False,
    int("0x36", 16): False,
    int("0x37", 16): False,
    int("0x38", 16): False,
    int("0x3D", 16): False,
    int("0x3E", 16): True,
    int("0x83", 16): True,
    int("0x84", 16): False,
    int("0x85", 16): True,
    int("0x86", 16): True,
    int("0x87", 16): True,
}


def _load_def_atts(ecu_doc: ElementTree.Element):
    def_atts_field = ecu_doc.find("DEFATTS")
    all_def_atts = {}
    for field in def_atts_field:
        tag_name = field.tag
        def_objects = {child.get("id"): child for child in field if "id" in child.attrib}
        all_def_atts[tag_name] = def_objects
    return all_def_atts


def _load_choices(data_type):
    choices = {}

    for choice in data_type.findall('TEXTMAP'):
        start = int(choice.attrib['s'].strip('()'))
        end = int(choice.attrib['e'].strip('()'))

        if start == end:
            choices[start] = choice.find('TEXT/TUV[1]').text

    if not choices:
        choices = None

    return choices


def _load_interface_param(ecu_doc):
    # Parse attrcat info
    attrcat_list = ecu_doc.findall("ATTRCATS/ATTRCAT")
    attrcat_table = {attrcat.attrib["id"]: attrcat for attrcat in attrcat_list}
    overwritten_table = {item.attrib["attrref"]: item.attrib["v"] for item in ecu_doc.findall("ECU/UNS")}

    interface_param_dict = {}
    ecu_atts_elemet = ecu_doc.find("DEFATTS/ECUATTS")

    interface_pos = 0
    for defatt in ecu_atts_elemet:
        attrcat_ref = defatt.attrib["attrcatref"]
        attrcat_obj = attrcat_table.get(attrcat_ref, None)
        attrcat_qual = attrcat_obj.find("QUAL").text if attrcat_obj else ""

        # If the interface still not parsed, add the interface into dict
        if attrcat_qual == "COM.INTERFACES" and attrcat_qual not in interface_param_dict:
            interface_name = defatt.find("QUAL").text
            interface_param_dict.update({interface_name: {"v": defatt.attrib["v"], "pos": interface_pos}})
            interface_pos += 1

        # Parse parameters of interfaces
        if attrcat_qual in ("COM.INIT", "COM.COM", "COM.TIMING", "COM.AUTOSAR"):
            qualifier = defatt.find("QUAL").text
            attr_id = defatt.attrib["id"]
            param_value = defatt.attrib.get("v",
                                            None) if attr_id not in overwritten_table else overwritten_table[attr_id]
            split_res = qualifier.split(".", 1)
            if len(split_res) <= 1:
                continue
            interface_name, param_name = qualifier.split(".", 1)
            # Update the param of the interface
            interface_param_dict[interface_name].update({param_name: param_value})

    return interface_param_dict


def _load_data_types(ecu_doc: ElementTree.Element):
    """Load all data types found in given ECU doc element.

    """

    data_type_dict = {}

    for data_type in ecu_doc.find("DATATYPES"):
        # Default values.
        byte_order = 'big_endian'
        unit = None
        factor = 1
        offset = 0
        bit_length = None
        encoding = None
        category = None
        minimum = None
        maximum = None

        # Name and id.
        type_name = data_type.find('NAME/TUV[1]').text
        type_id = data_type.attrib['id']
        tag = data_type.tag

        # Load from C-type element.
        ctype = data_type.find('CVALUETYPE')
        bit_length = ctype.attrib.get("bl", None)
        bit_length and int(bit_length)
        for key, value in ctype.attrib.items():
            if key == 'bl':
                bit_length = int(value)
            elif key == 'enc':
                encoding = value
            elif key == 'qty':
                category = value
            elif key == 'minsz':
                minimum = int(value)
            elif key == 'maxsz':
                maximum = int(value)
            else:
                LOGGER.debug("Ignoring unsupported attribute '%s'.", key)

        if ctype.attrib['bo'] == '21':
            byte_order = 'big_endian'
        elif ctype.attrib['bo'] == '12':
            byte_order = 'little_endian'
        else:
            raise ParseError("Unknown byte order code: %s" % ctype.attrib['bo'])

        # Load from P-type element.
        ptype_unit = data_type.find('PVALUETYPE/UNIT')

        if ptype_unit is not None:
            unit = ptype_unit.text

        # Choices, scale and offset.
        choices = _load_choices(data_type)

        # Slope and offset.
        comp = data_type.find('COMP')

        if comp is not None:
            factor = float(comp.attrib['f'])
            offset = float(comp.attrib['o'])

        data_type_obj = DataType(type_name, type_id, bit_length, encoding, minimum, maximum, choices, byte_order, unit,
                                 factor, offset, category, tag)
        data_type_str = _infer_data_type_str(data_type_obj)
        data_type_obj.set_data_type_str(data_type_str)
        data_type_dict[type_id] = data_type_obj

    return data_type_dict


def _load_did_element_from_diag_inst(diag_inst, data_types, state_groups, did_dict, id_to_dcl_srv_tmpl,
                                     protocol_service_dict):
    """Load given diag instance element as DID and return a did object.
    """

    # Parse access of this did
    read_access = {"access": False, "executability": None}
    write_access = {"access": False, "executability": None}
    control_access = {"access": False, "executability": None}
    set_access = {"access": False, "executability": None}
    freeze_access = {"access": False, "executability": None}
    reset_access = {"access": False, "executability": None}
    supported_service_info_dict = {
        "Read": read_access,
        "Write": write_access,
        "ReturnControl": control_access,
        "ResetDefault": reset_access,
        "ShortTermAdjustment": set_access,
        "Freeze": freeze_access
    }
    service_element_list = diag_inst.findall("SERVICE")
    for service_element in service_element_list:
        service_name = None
        dcl_srv_tmpl = id_to_dcl_srv_tmpl[service_element.attrib["tmplref"]]
        protocol_service = protocol_service_dict[dcl_srv_tmpl.attrib["tmplref"]]
        req = protocol_service.find("REQ")
        const_comp_list = req.findall("CONSTCOMP")
        try:
            sid = const_comp_list[0].attrib["v"]
            # 22 "Read" service
            if sid == "34":
                service_name = "Read"
            # 2e "Write" service
            elif sid == "46":
                service_name = "Write"
            # 2f "IO control" service
            elif sid == "47":
                ssid = const_comp_list[1].attrib["v"]
                # "Return Control" subservice
                if ssid == "0":
                    service_name = "ReturnControl"
                # "Reset Default" subservice
                elif ssid == "1":
                    service_name = "ResetDefault"
                # "Freeze" subservice
                elif ssid == "2":
                    service_name = "Freeze"
                # "Short term adjust" subservice
                elif ssid == "3":
                    service_name = "ShortTermAdjustment"
                else:
                    raise Exception(f"Invalid ssid {ssid} for 2F service!")
            else:
                did_name = diag_inst.find("QUAL").text
                raise Exception(f"Invalid sid {sid} for {did_name}!")

            supported_service_info_dict[service_name]["access"] = True
            executability = parse_service_element_execute_permission(service_element, state_groups)
            supported_service_info_dict[service_name]["executability"] = executability
        except Exception:
            pass

    # Parse signal datas of this did
    ref_id = diag_inst.attrib["id"]
    identifier = int(diag_inst.find("STATICVALUE").attrib["v"])
    name = diag_inst.find("QUAL").text
    used = True
    if diag_inst.attrib.get("act", "-1") == "0":
        used = False

    offset = 0
    data_list = []
    # The first SIMPLECOMPCONT tag has data info of the did
    simple_compcont = select_did_simple_compcont(diag_inst)
    data_obj_element_list = []
    # Iterate all child tag of the simple compcont to gather all datas
    for data_obj_element in simple_compcont:
        data_obj_element_list.append(data_obj_element)

    data = None
    for data_obj in data_obj_element_list:
        # If the data obj references from did, simply return the did
        if data_obj.tag == "DIDDATAREF":
            if identifier in did_dict:
                did_dict[identifier].used = used
                did_dict[identifier].service_info = supported_service_info_dict
                return did_dict[identifier]
            else:
                # For uncreated did inst, create one
                did_obj_filter = filter(lambda x: x.ref_id == data_obj.attrib.get("didRef", "-1"), did_dict.values())
                similar_did_obj = list(did_obj_filter)[0]
                did_dict[identifier] = Did(identifier=identifier,
                                           name=name,
                                           length=similar_did_obj.length,
                                           datas=deepcopy(similar_did_obj.datas),
                                           ref_id=ref_id,
                                           used=used,
                                           service_info=supported_service_info_dict)
                return did_dict[identifier]
        # Parse different kinds of data obj
        if data_obj.tag in ("DATAOBJ", "GAPDATAOBJ"):
            data = _load_data_element(data_obj, offset, data_types)
        elif data_obj.tag == "STRUCT":
            data = _load_struct_data_element(data_obj, offset, data_types)

        if data:
            data_list.append(data)
            offset += data.length

    length = (offset + 7) // 8

    return Did(identifier=identifier,
               name=name,
               length=length,
               datas=data_list,
               ref_id=ref_id,
               used=used,
               service_info=supported_service_info_dict)


def select_did_simple_compcont(diag_inst):
    simple_compocont_list = diag_inst.findall("SIMPLECOMPCONT")
    for simple_compocont in simple_compocont_list:
        if simple_compocont.find("DIDDATAREF") is not None:
            return simple_compocont
    LOGGER.warning("Cannot find did ref, use the first simple compocont as did data")
    return simple_compocont_list[0]


def _load_did_element_from_dids_tag(did, data_types):
    """Load given did tag element as DID and return a did object.
    """

    ref_id = did.attrib["id"]
    identifier = int(did.attrib["n"])
    name = did.find("QUAL").text
    offset = 0
    datas = []
    structure_element = did.find("STRUCTURE")
    data_objs = []
    for child in structure_element:
        data_objs.append(child)

    for data_obj in data_objs:
        if data_obj.tag in ("DATAOBJ", "GAPDATAOBJ"):
            data = _load_data_element(data_obj, offset, data_types)
        elif data_obj.tag == "STRUCT":
            data = _load_struct_data_element(data_obj, offset, data_types)
        else:
            LOGGER.error(f"Unsupported data tag: {data.tag}")

        if data:
            datas.append(data)
            offset += data.length

    length = (offset + 7) // 8

    return Did(identifier=identifier, name=name, length=length, datas=datas, ref_id=ref_id, used=False)


def _load_did_data_refs(ecu_doc: ElementTree.Element) -> Dict[str, ElementTree.Element]:
    """Load DID data references from given ECU doc element.

    """
    dids = ecu_doc.find('DIDS')

    if dids is None:
        return {}
    else:
        return {did.attrib['id']: did for did in dids.findall('DID')}


def _load_dcl_tmpls(ecu_doc: ElementTree.Element) -> Dict[str, ElementTree.Element]:
    """
    Load all dcltmpls
    """
    dcl_tmpl_list = ecu_doc.findall("DCLTMPLS/DCLTMPL")

    return {dcl_tmpl.attrib["id"]: dcl_tmpl for dcl_tmpl in dcl_tmpl_list}


def _reason_executable_state(may_be_execute, not_exec_in_state_groups, state_groups):
    # Init all states executablity to false
    state_executablity = 0
    state_group_bound_list = []
    for state_group in state_groups:
        # Get all states' number of the state group
        state_number_list = list(map(lambda x: x.number, state_group.state_list))
        # Get the minimum and maximum state number of this state group
        state_group_bound_list.append((min(state_number_list), max(state_number_list)))
    # Set correspond bit to 1, e.g.["1", "3", "5"] with 6 states to 101010
    may_be_execute_iter = map(lambda x: (1 << State.count - int(x)), may_be_execute)
    state_executablity = bin(reduce(lambda x, y: x + y, may_be_execute_iter, 0))[2:]
    state_executablity = state_executablity.zfill(State.count)
    for state_group_num, bound_tuple in enumerate(state_group_bound_list):
        lower_bound = bound_tuple[0]
        upper_bound = bound_tuple[1]
        # Get state group bits
        state_str = state_executablity[lower_bound - 1:upper_bound]
        # If list no executable state and the state group can execute
        if int(state_str) == 0 and str(state_group_num + 1) not in not_exec_in_state_groups:
            # Set all bits of this state group str to 1
            state_str = bin(2**len(state_str) - 1)[2:]
            state_executablity = state_executablity[:lower_bound - 1] + state_str + state_executablity[upper_bound:]

    return state_executablity


def parse_service_element_execute_permission(service_element, state_groups):
    # Parse mayBeExec attrib from service tag.
    # If the attrib doesnot exist, defaultly treat the state avaibility as False
    may_be_execute = service_element.attrib["mayBeExec"] if "mayBeExec" in service_element.attrib else ""
    may_be_execute = list(filter(None, may_be_execute[1:-1].split(",")))
    # Parse notExecInStateGroups attrib from service tag.
    # If the attrib doesnot exist, defaultly treat all state groups as executable
    not_exec_in_state_groups = service_element.attrib[
        "notExecInStateGroups"] if "notExecInStateGroups" in service_element.attrib else ""
    not_exec_in_state_groups = list(filter(None, not_exec_in_state_groups[1:-1].split(",")))
    state_executability = _reason_executable_state(may_be_execute, not_exec_in_state_groups, state_groups)
    return state_executability


def _load_protocol_services(ecu_doc: ElementTree.Element):
    protocol_services_table = {
        protocol_service.attrib["id"]: protocol_service
        for protocol_service in ecu_doc.findall("PROTOCOLSERVICES/PROTOCOLSERVICE")
    }

    return protocol_services_table


def _update_services(service_table: Dict, service_id, service_name, subservice_id, subservice_name, execute_permission):
    service: UdsService = service_table.get(service_id, None)

    # If the uds service already existed and parse new subservice from cdd
    if service is not None:
        # If parse new subservice from cdd
        if subservice_id is not None:
            subservice: UdsSubService = service.subservices.get(subservice_id, None)
            # If subservice already existed, update its execute permission
            if subservice is not None:
                subservice.update_execute_permission(execute_permission)
            # else add the new subservice
            else:
                service.add_sub_service(subservice_name, subservice_id, execute_permission)
        # else simply update execute permission of the service
        else:
            service.update_execute_permission(execute_permission)
    # If the uds service still not be recorded
    elif service is None:
        # Create new service
        new_service = UdsService(service_name, service_id, execute_permission, HAS_SUB_SERVICE[int(service_id)])
        service_table.update({service_id: new_service})
        # If also parse subservice from cdd
        if subservice_id is not None:
            new_service.add_sub_service(subservice_name, subservice_id, execute_permission)


def _load_shproxy(xml_node: ElementTree.Element):
    shproxy_table = {shproxy.attrib["id"]: shproxy for shproxy in xml_node.findall("SHPROXY")}

    return shproxy_table


def _load_uds_services(ecu_doc: ElementTree.Element, dcl_tmpls: Dict, protocol_services, state_groups):
    services_table = {}
    var = ecu_doc.find("ECU/VAR")
    # Gather all diag inst
    diag_class_list = var.findall("DIAGCLASS")
    diag_inst_list = var.findall("DIAGINST")
    diag_inst_of_class_list_iter = map(lambda diag_class: diag_class.findall("DIAGINST"), diag_class_list)
    diag_inst_list += reduce(lambda x, y: x + y, diag_inst_of_class_list_iter)

    # Iterate all diag inst in this diag class
    for diag_inst in diag_inst_list:
        # Skip all services of the inactivated diag inst
        if diag_inst.attrib.get("act", "1") == "0":
            continue
        # Get tmplref of this diag inst
        dcl_tmpl = dcl_tmpls[diag_inst.attrib["tmplref"]]
        # Construct dcl srv tmpl looktable of this dcl tmpl
        dcl_srv_tmpl_table = {
            dcl_srv_tmpl.attrib["id"]: dcl_srv_tmpl for dcl_srv_tmpl in dcl_tmpl.findall("DCLSRVTMPL")
        }
        # Iterate all SERVICE tag under this diag inst
        for service_element in diag_inst.findall("SERVICE"):
            dcl_srv_tmpl = dcl_srv_tmpl_table[service_element.attrib["tmplref"]]
            # Find the service prototype
            protocol_service = protocol_services[dcl_srv_tmpl.attrib["tmplref"]]
            service_name = protocol_service.find("NAME/TUV").text.split(" ")[1]
            service_req = protocol_service.find("REQ")
            const_comp = service_req.findall("CONSTCOMP")
            service_id = const_comp[0].attrib["v"]
            # If this service has sub service and protocol service has more than one CONSTCOMP tag
            # the value of second CONSTCOMP should be sub service id
            sub_service_sid = None
            sub_service_name = None
            if len(const_comp) > 1 and HAS_SUB_SERVICE[int(service_id)]:
                sub_service_sid = const_comp[1].attrib["v"]
                sub_service_name = dcl_srv_tmpl.find("QUAL").text
            # else the value of STATICVALUE tag in diag inst should be ssid
            elif diag_inst.find("STATICVALUE") is not None and HAS_SUB_SERVICE[int(service_id)]:
                sub_service_sid = diag_inst.find("STATICVALUE").attrib["v"]
                sub_service_name = diag_inst.find("QUAL").text
            execute_permission = parse_service_element_execute_permission(service_element, state_groups)

            # Update the service table with new info
            _update_services(services_table, service_id, service_name, sub_service_sid, sub_service_name,
                             execute_permission)

    return list(services_table.values())


def _update_security_level_info(ecu_doc: ElementTree.Element, dcl_tmpls: Dict, protocol_services, state_groups,
                                data_types):
    """
    Check which security level used according to DIAGINST
    """
    var = ecu_doc.find("ECU/VAR")
    diag_class_list = _find_spec_diag_class(var, dcl_tmpls, "sec", "class")
    security_group = list(filter(lambda state_group: state_group.spec == "security", state_groups))[0]
    locked_state = list(filter(lambda state: state.name == "Locked", security_group.state_list))[0]
    number_to_state_dict = {str(state.number): state for state in security_group.state_list}

    key_state_binding = {}
    service_info_binding = {}
    for diag_class in diag_class_list:
        dcl_tmpl = dcl_tmpls[diag_class.attrib["tmplref"]]
        dcl_srv_tmpl_table = {
            dcl_srv_tmpl.attrib["id"]: dcl_srv_tmpl for dcl_srv_tmpl in dcl_tmpl.findall("DCLSRVTMPL")
        }
        for diag_inst in diag_class.findall("DIAGINST"):
            for service in diag_inst.findall("SERVICE"):
                dcl_srv_tmpl = dcl_srv_tmpl_table[service.attrib["tmplref"]]
                protocol_service = protocol_services[dcl_srv_tmpl.attrib["tmplref"]]
                req = protocol_service.find("REQ")
                service_id = req.find("CONSTCOMP").attrib["v"]
                if service_id != "39":
                    continue
                else:
                    subservice_id = diag_inst.find("STATICVALUE").attrib["v"]
                    if subservice_id in ("2", "10"):
                        trans = service.attrib.get("trans", "()")[1:-1]
                        if trans is not None:
                            trans = trans.split(",")
                            # Get odd index element as start state
                            start_state_list = trans[::2]
                            # Get even index element as end state
                            end_state_list = trans[1::2]
                            # Build a start-end state dict
                            state_trans_dict = dict(zip(start_state_list, end_state_list))
                            if str(locked_state.number) in state_trans_dict:
                                end_state_num = state_trans_dict[str(locked_state.number)]
                                end_state = number_to_state_dict[end_state_num]
                                end_state.set_used(True and not diag_inst.attrib.get("act", "1") == "0")
                                key_state_binding[subservice_id] = end_state
                    service_info_binding.update(
                        {subservice_id: parse_service_inst(dcl_tmpl, protocol_service, diag_inst, data_types)})
    for ssid, state in key_state_binding.items():
        setattr(state, "send_key_service_info", service_info_binding[ssid])
        setattr(state, "request_seed_service_info", service_info_binding[str(int(ssid) - 1)])


def _update_session_level_used_info(ecu_doc: ElementTree.Element, dcl_tmpls: Dict, protocol_services, state_groups):
    """
    Check which session level used according to DIAGINST
    """
    ssid_to_session_table = {"1": "Default", "2": "Programming", "3": "Extended"}
    var = ecu_doc.find("ECU/VAR")
    diag_class_list = _find_spec_diag_class(var, dcl_tmpls, "ses", "class")
    session_group = list(filter(lambda state_group: state_group.spec == "session", state_groups))[0]
    name_to_state_dict = {state.name: state for state in session_group.state_list}

    for diag_class in diag_class_list:
        dcl_tmpl = dcl_tmpls[diag_class.attrib["tmplref"]]
        dcl_srv_tmpl_table = {
            dcl_srv_tmpl.attrib["id"]: dcl_srv_tmpl for dcl_srv_tmpl in dcl_tmpl.findall("DCLSRVTMPL")
        }
        for diag_inst in diag_class.findall("DIAGINST"):
            # Find session diag inst according to service
            for service in diag_inst.findall("SERVICE"):
                dcl_srv_tmpl = dcl_srv_tmpl_table[service.attrib["tmplref"]]
                protocol_service = protocol_services[dcl_srv_tmpl.attrib["tmplref"]]
                req = protocol_service.find("REQ")
                service_id = req.find("CONSTCOMP").attrib["v"]
                if service_id != "16":
                    continue
                else:
                    ssid = diag_inst.find("STATICVALUE").attrib["v"]
                    act = diag_inst.attrib.get("act", "1") == "0"
                    name_to_state_dict[ssid_to_session_table[ssid]].set_used(not act)


def _load_state_groups(ecu_doc: ElementTree.Element):
    state_group_list = []
    state_group_elements = ecu_doc.findall("STATEGROUPS/STATEGROUP")
    # Number of the state according to the order in cdd text file
    number = 1
    for state_group in state_group_elements:
        state_elements = state_group.findall("STATE")
        state_list = []
        for state in state_elements:
            state_list.append(State(state.find("QUAL").text, number))
            # Increase the number
            number += 1

        spec = state_group.attrib["spec"] if "spec" in state_group.attrib else "none"
        state_group_list.append(StateGroup(state_group.find("QUAL").text, state_list, spec))

    State.count = number - 1
    return state_group_list


def _load_record_tmpls(ecu_doc: ElementTree.Element, spec_name):
    record_tmpl_dict = {}
    for record_tmpl in ecu_doc.findall("RECORDTMPLS/RECORDTMPL"):
        record_item_tmpl_list = record_tmpl.findall("TRRECORDITEMTMPL")
        record_item_tmpl_list += record_tmpl.findall("UNSRECORDITEMTMPL")
        record_item_tmpl_list += record_tmpl.findall("ENUMRECORDITEMTMPL")
        itemtmpl_ele_dict = {
            record_item_tmpl.attrib["id"]: record_item_tmpl for record_item_tmpl in record_item_tmpl_list
        }
        record_tmpl_dict.update({record_tmpl.attrib["spec"]: itemtmpl_ele_dict})

    return record_tmpl_dict


def _find_spec_diag_class(var: ElementTree.Element, dcl_tmpls: Dict, cls_str: str, diag_type="class"):
    """
    Find the specific diag class or instance list
    """
    target_table = {"class": "DIAGCLASS", "instance": "DIAGINST"}

    class_list = []
    for diag_class in var.findall(target_table[diag_type]):
        # Find the fault memory diag instance
        dcl_tmpl = dcl_tmpls[diag_class.attrib["tmplref"]]
        if dcl_tmpl.attrib["cls"] == cls_str:
            class_list.append(diag_class)

    return class_list


def _parse_record_item_info(idref_to_record_item_dict: Dict, record_item_tmpl: ElementTree.Element):
    # Find the record item of the tmpl to get its value
    item_qual = record_item_tmpl.find("QUAL").text.lower()
    item_content = None
    record_item: ElementTree.Element = idref_to_record_item_dict.get(record_item_tmpl.attrib["id"], None)

    # If the record tmpl has no record item, try use default value of tmpl
    if record_item is None:
        value = record_item_tmpl.attrib.get("v", None)
    elif record_item_tmpl.tag == "TRRECORDITEMTMPL":
        item_content = record_item.find("TEXT/TUV").text
    elif record_item_tmpl.tag == "ENUMRECORDITEMTMPL":
        value = record_item.attrib.get("v", None)
        etag_dict = {etag.attrib["v"]: etag.find("TUV").text for etag in record_item_tmpl.findall("ETAG")}
        item_content = etag_dict.get(value, None)
    elif record_item_tmpl.tag == "UNSRECORDITEMTMPL":
        item_content = record_item.attrib.get("v", None)

    return {item_qual: item_content}


def _parse_attr_value(value_obj: ElementTree.Element, def_atts_obj: ElementTree.Element):
    item_qual = def_atts_obj.findtext("QUAL")

    default_value = def_atts_obj.get("v", None)
    if not value_obj:
        value = default_value
    else:
        value = value_obj.get("v", None)

    if def_atts_obj.tag == "ENUMDEF":
        etag_dict = {etag.attrib["v"]: etag.findtext("TUV") for etag in def_atts_obj.findall("ETAG")}
        item_content = etag_dict.get(value, None)
    elif def_atts_obj.tag == "STRDEF":
        item_content = value
    elif def_atts_obj.tag == "CSTRDEF":
        item_content = value
    elif def_atts_obj.tag == "UNSDEF":
        item_content = value
    else:
        item_content = None

    return {item_qual: item_content}


def _load_enable_condition(dtc: Dtc, condition_set, condition_group_list):
    enable_condition_str = dtc.record_info_dict["enable_conditions"]
    condition_list = enable_condition_str.split("&&")
    remove_chars = string.punctuation.replace("_", "")
    condition_list = [re.sub(f"[{remove_chars}]", "", condition) for condition in condition_list]
    condition_set.update(condition_list)
    if condition_list not in condition_group_list:
        condition_group_list.append(condition_list)
    dtc.set_enable_condition_group(condition_group_list.index(condition_list))


def _load_dtcs(ecu_doc: ElementTree.Element, var: ElementTree.Element, dcl_tmpls: Dict, record_tmpls: Dict,
               def_atts: Dict[str, ElementTree.Element]):
    dtcs = []
    dtc_elements = None
    # Get dtc elements from fault memory diag instance
    diag_inst = _find_spec_diag_class(var, dcl_tmpls, "ftm", "instance")[0]
    record_data_obj = diag_inst.find("SIMPLECOMPCONT/RECORDDATAOBJ")
    item_tmpls = record_tmpls[record_data_obj.attrib["rtSpec"]]
    dtc_elements = diag_inst.find("SIMPLECOMPCONT/RECORDDATAOBJ/RECORDDT")

    record_dt_elements = {record.attrib["id"]: record for record in ecu_doc.findall("RECORDDTPOOL/RECORDDT/RECORD")}

    # Iterate elements to gather dtc info
    enable_condition_set = set()
    enable_condition_group_list = []
    for child in dtc_elements:
        if child.tag in ("NAME", "QUAL", "CVALUETYPE", "PVALUETYPE"):
            continue
        elif child.tag == "RECORD":
            dtc = child
        elif child.tag == "RECORDREF":
            dtc = record_dt_elements[child.attrib["idref"]]
        else:
            LOGGER.error(f"Unsupport type of RECORDDT {child.tag}!")
            continue

        name = dtc.find("TEXT/TUV").text
        value = int(dtc.attrib["v"])

        # Parse all info of the DTC from record items
        idref_to_record_item_dict = {}
        attrref_to_atts = {}
        for item in dtc:
            if idref := item.get("idref"):
                idref_to_record_item_dict[idref] = item
            elif attrref := item.get("attrref"):
                attrref_to_atts[attrref] = item
            else:
                continue

        record_info_dict = {}
        for record_item_tmpl in item_tmpls.values():
            record_info_dict.update(_parse_record_item_info(idref_to_record_item_dict, record_item_tmpl))

        attr_info_dict = {}
        for ref_id, def_obj in def_atts.items():
            inst_obj = attrref_to_atts.get(ref_id, None)
            attr_info_dict.update(_parse_attr_value(inst_obj, def_obj))

        dtc = Dtc(name, value, record_info_dict, attr_info_dict=attr_info_dict)

        try:
            _load_enable_condition(dtc, enable_condition_set, enable_condition_group_list)
        except Exception as e:
            print(e)

        dtcs.append(dtc)

    return dtcs, enable_condition_set, enable_condition_group_list


def _load_obd_dtcs(ecu_doc: ElementTree.Element, var: ElementTree.Element, dcl_tmpls: Dict, record_tmpls: Dict,
                   protocol_service_dict, def_atts):
    obd_dtcs = []
    dtc_elements = None
    # Get dtc elements from fault memory diag instance
    try:
        dcl_tmpl = next(target_dcl_tmp_iter(list(dcl_tmpls.values()), protocol_service_dict, ("0x03",)))
    except StopIteration:
        return obd_dtcs
    dcl_tmpl_id = dcl_tmpl.attrib["id"]
    try:
        diag_inst = next(filter(lambda t: t.attrib["tmplref"] == dcl_tmpl_id, var.findall("DIAGINST")))
    except StopIteration:
        return obd_dtcs
    record_data_obj = diag_inst.find("SIMPLECOMPCONT/RECORDDATAOBJ")
    if not record_data_obj:
        return obd_dtcs
    item_tmpls = record_tmpls[record_data_obj.attrib["rtSpec"]]
    dtc_elements = diag_inst.find("SIMPLECOMPCONT/RECORDDATAOBJ/RECORDDT")

    record_dict = {}
    for recorddt in ecu_doc.findall("RECORDDTPOOL/RECORDDT"):
        for record in recorddt.findall("RECORD"):
            record_dict.update({record.attrib["id"]: record})

    # Iterate elements to gather dtc info
    for child in dtc_elements:
        if child.tag in ("NAME", "QUAL", "CVALUETYPE", "PVALUETYPE"):
            continue
        elif child.tag == "RECORD":
            obd_dtc = child
        elif child.tag == "RECORDREF":
            obd_dtc = record_dict[child.attrib["idref"]]
        else:
            LOGGER.error(f"Unsupport type of RECORDDT {child.tag}!")
            continue

        name = obd_dtc.find("TEXT/TUV").text
        value = int(obd_dtc.attrib["v"])

        # Parse all info of the DTC from record items
        idref_to_record_item_dict = {}
        attrref_to_atts = {}
        for item in obd_dtc:
            if idref := item.get("idref"):
                idref_to_record_item_dict[idref] = item
            elif attrref := item.get("attrref"):
                attrref_to_atts[attrref] = item
            else:
                continue

        record_info_dict = {}
        for record_item_tmpl in item_tmpls.values():
            record_info_dict.update(_parse_record_item_info(idref_to_record_item_dict, record_item_tmpl))

        attr_info_dict = {}
        for ref_id, def_obj in def_atts.items():
            inst_obj = attrref_to_atts.get(ref_id, None)
            attr_info_dict.update(_parse_attr_value(inst_obj, def_obj))

        obd_dtc = ObdDtc(name, value, record_info_dict, attr_info_dict=attr_info_dict)
        obd_dtcs.append(obd_dtc)

    return obd_dtcs


def _find_protocol_service_by_id(protocol_service_table: Dict, sid_str: str, ssid_str: str = None):
    sid = int(sid_str, 16)
    ssid = int(ssid_str, 16)

    for protocol_service in protocol_service_table.values():
        constcomp_list = protocol_service.findall("REQ/CONSTCOMP")
        protocol_sid = int(constcomp_list[0].attrib["v"])
        # If find the service with given sid and still need to find ssid
        if protocol_sid == sid and ssid:
            protocol_service_ssid = int(constcomp_list[1].attrib["v"])
            if protocol_service_ssid == ssid:
                return protocol_service
        # If only need find service without ssid
        elif not ssid:
            return protocol_service

    # Cannot find sid
    return None


def _load_fault_memory_under_ecu(fault_memory_element: ElementTree.Element, did_dict: Dict):
    """
    Load snapshot info from FAULTMEMORY tag under ECU tag
    """
    snapshots_list = []
    any_common_snapshot_data = fault_memory_element.findall("COMMONSNAPSHOTDATAPOOL/ANYCOMMONSNAPSHOTDATA")
    # If cannot find snapshot under ecu, return empty list
    if len(any_common_snapshot_data) > 0:
        any_common_snapshot_data = any_common_snapshot_data[0]
    else:
        return snapshots_list

    dids = []
    for did_info in any_common_snapshot_data.find("STRUCTURE"):
        if did_info.tag == "DIDREF":
            data_obj = did_info.find("DATAOBJ")
            identifier = int(data_obj.attrib["v"])
            if did_dict.get(identifier, None):
                dids.append(did_dict[identifier])

    if dids:
        snapshots_list.append(SnapShot(name="default", dids=dids))
    return snapshots_list


def _load_snapshot_under_diag_inst(fault_memory_element: ElementTree.Element, did_dict: Dict):
    """
    Load snapshot info from FAULTMEMORY tag under DIAGINST tag
    """
    snapshots_list = []
    ref_id_did_dict = {did.ref_id: did for did in did_dict.values()}
    default_snapshot_data = fault_memory_element.findall("SNAPSHOT/DEFAULTSNAPSHOTDATA")
    # If cannot find snapshot under ecu, return empty list
    if len(default_snapshot_data) > 0:
        default_snapshot_data = default_snapshot_data[0]
    else:
        return snapshots_list

    dids = []
    for did_info in default_snapshot_data:
        if did_info.tag == "SNAPSHOTDATADIDREF":
            dids.append(ref_id_did_dict[did_info.attrib["didRef"]])
    if dids:
        snapshots_list.append(SnapShot(name="default", dids=dids))

    return snapshots_list


def _load_snapshots(ecu_doc: ElementTree.Element, dcl_tmpls: Dict, dids, protocol_service_table: Dict, data_types):
    snapshots_list = []

    # If it has FAULTMEMORY tag under ECU tag, try load snapshot info from FAULTMEMORY tag under ECU tag
    falult_memory_element = ecu_doc.find("ECU/FAULTMEMORY")
    if falult_memory_element:
        snapshots_list = _load_fault_memory_under_ecu(falult_memory_element, dids)
        # If sucessfully parse snapshot under standard tag, just return the result
        if snapshots_list:
            return snapshots_list

    # Try parse snapshot info stored as datatype from diag inst
    var = ecu_doc.find("ECU/VAR")
    # Find "Fault Memory" diag instance
    diag_inst = _find_spec_diag_class(var, dcl_tmpls, "ftm", "instance")[0]

    # If it has FAULTMEMORY tag under DIAGINST tag, try load snapshot info from the FAULTMEMORY tag
    falult_memory_element = diag_inst.find("FAULTMEMORY")
    if falult_memory_element:
        snapshots_list = _load_snapshot_under_diag_inst(falult_memory_element, dids)
        # If sucessfully parse snapshot under standard tag, just return the result
        if snapshots_list:
            return snapshots_list

    # Find 19 04 service
    service_19_04 = _find_protocol_service_by_id(protocol_service_table, "0x19", "0x4")
    # Load shproxy table of this diag instance
    fault_memory_dcl_tmpl = dcl_tmpls[diag_inst.attrib["tmplref"]]
    shproxy_table = _load_shproxy(fault_memory_dcl_tmpl)

    # Find shrpoxy for the snapshot record data
    snapshot_shproxy = None
    if (muxcomp_obj := service_19_04.find("POS/EOSITERCOMP/MUXCOMP")) is not None:
        mux_comp_id = muxcomp_obj.attrib["id"]
    else:
        LOGGER.debug("Find no snapshot!")
        return snapshots_list
    for shproxy in shproxy_table.values():
        for proxycomp_ref in shproxy.findall("PROXYCOMPREF"):
            if proxycomp_ref.attrib["idref"] == mux_comp_id:
                snapshot_shproxy = shproxy

    # Find MUXCOMPCONT of snapshot record data
    snapshot_record_data = None
    if snapshot_shproxy:
        for muxcompcont in diag_inst.findall("MUXCOMPCONT"):
            if muxcompcont.attrib["shproxyref"] == snapshot_shproxy.attrib["id"]:
                snapshot_record_data = muxcompcont
                break
    else:
        LOGGER.error("Cannot find SHPROXY for snapshot record data!")

    # Parse data in MUXCOMPCONT
    if snapshot_record_data:
        dids = []
        for struct_child in list(snapshot_record_data.find("MUXDT/STRUCTURE"))[2:]:
            if struct_child.tag == "DATAOBJ":
                dataobj = struct_child
                data_type_element = list(
                    filter(lambda item: item.attrib["id"] == dataobj.attrib["dtref"],
                           ecu_doc.findall('DATATYPES/MUXDT')))[0]

                offset = 0
                datas = []
                identifier = None
                did_name = None
                for child in data_type_element.find("STRUCTURE"):
                    # The element without "v" is classified to data
                    if "v" not in child.attrib:
                        if child.tag in ("DATAOBJ", "GAPDATAOBJ") and "v" not in child.attrib:
                            data = _load_data_element(child, offset, data_types)
                        elif child.tag == "STRUCT" and "v" not in child.attrib:
                            data = _load_struct_data_element(child, offset, data_types)
                        else:
                            LOGGER.error(f"Unsupported data tag: {data.tag}")

                        if data:
                            datas.append(data)
                            offset += data.length
                    # The element with "v" is classified to did
                    else:
                        if identifier:
                            length = (offset + 7) // 8
                            did = Did(identifier=identifier,
                                      name=did_name,
                                      length=length,
                                      datas=datas,
                                      ref_id=None,
                                      used=False)
                            dids.append(did)

                        # Prepare for next DID
                        offset = 0
                        identifier = int(child.attrib["v"])
                        did_name = child.find("QUAL").text
                        datas = []

                # Create the last did
                length = (offset + 7) // 8
                did = Did(identifier=identifier, name=did_name, length=length, datas=datas, ref_id=None, used=False)
                dids.append(did)

        snapshots_list.append(SnapShot(name="default", dids=dids))
        return snapshots_list
    else:
        LOGGER.error("Cannot find MUXCOMPCONT for snapshot record data!")
        return snapshots_list


def _load_extended_datas(ecu_doc: ElementTree.Element, dcl_tmpls: Dict, data_types):
    var = ecu_doc.find("ECU/VAR")
    diag_inst = _find_spec_diag_class(var, dcl_tmpls, "ftm", "instance")[0]
    extended_data_under_diag_inst = diag_inst.find("FAULTMEMORY/EXTENDEDDATA")
    if extended_data_under_diag_inst is not None:
        extended_data = extended_data_under_diag_inst
    else:
        extended_data = ecu_doc.find("ECU/FAULTMEMORY")
    extended_data_records = extended_data.findall("EXTENDEDDATARECORDS/EXTENDEDDATARECORD")

    extended_data_list = []
    for extended_data in extended_data_records:
        data_obj_element_list = extended_data.findall("STRUCTURE/DATAOBJ")
        data_obj_element_list += extended_data.findall("STRUCTURE/STRUCT")

        # Gather all data elements of this extenede data
        data_list = []
        offset = 0
        for data_obj in data_obj_element_list:
            if data_obj.tag in ("DATAOBJ", "GAPDATAOBJ"):
                data = _load_data_element(data_obj, offset, data_types)
            elif data_obj.tag == "STRUCT":
                data = _load_struct_data_element(data_obj, offset, data_types)

            if data:
                data_list.append(data)
                offset += data.length

        length = (offset + 7) // 8

        extended_data_list.append(
            ExtendedData(name=extended_data.find("QUAL").text,
                         datas=data_list,
                         length=length,
                         update=extended_data.attrib["updated"] if "updated" in extended_data.attrib else "0",
                         trigger=extended_data.attrib["trigger"] if "trigger" in extended_data.attrib else "testFailed",
                         record_num=extended_data.attrib["rn"]))

    return extended_data_list


def _load_operation_cycles(var: ElementTree.Element, dcl_tmpls: Dict):
    diag_inst = _find_spec_diag_class(var, dcl_tmpls, "ftm", "instance")[0]
    operation_cycle_list = diag_inst.findall("EVENTDATA/OPERATIONCYCLES/OPERATIONCYCLE")
    oc_info_dict = {}
    for oc in operation_cycle_list:
        info_dict = {"name": oc.findtext("QUAL"), "autostart": oc.get("autostart"), "type": oc.get("type")}
        oc_info_dict[oc.get("id")] = info_dict
    return oc_info_dict


def _load_debounce_algorithms(var: ElementTree.Element, dcl_tmpls: Dict):
    diag_inst = _find_spec_diag_class(var, dcl_tmpls, "ftm", "instance")[0]
    debounce_algorithm_list = diag_inst.findall("EVENTDATA/DEBOUNCEALGORITHMS/TIMEBASEDALGORITHM")
    debounce_algorithm_list += diag_inst.findall("EVENTDATA/DEBOUNCEALGORITHMS/COUNTERBASEDALGORITHM")
    return {debounce_algorithm.attrib["id"]: debounce_algorithm for debounce_algorithm in debounce_algorithm_list}


def _load_indicator(var: ElementTree.Element, dcl_tmpls: Dict):
    diag_inst = _find_spec_diag_class(var, dcl_tmpls, "ftm", "instance")[0]
    indicator_field_list = diag_inst.findall("EVENTDATA/INDICATORS/INDICATOR")
    indicator_info_dict = {}
    for idct in indicator_field_list:
        info_dict = {"name": idct.findtext("QUAL"), "type": idct.get("type")}
        indicator_info_dict[idct.get("id")] = info_dict
    return indicator_info_dict


def _load_events(ecu_doc: ElementTree.Element, dcl_tmpls: Dict, operation_cycle: Dict[str, Dict],
                 debounce_algorithum: Dict, dtc_list: List[Dtc], indicator: Dict[str, Dict]):
    var = ecu_doc.findall("ECU")[0].find("VAR")
    diag_inst: ElementTree.Element = _find_spec_diag_class(var, dcl_tmpls, "ftm", "instance")[0]

    # Construct condition group info dict
    condition_group_dict = {}
    condition_group_field_dict = {cg.get("id"): cg for cg in diag_inst.findall("EVENTDATA/CONDITIONS/CONDITIONGROUP")}
    condition_field_dict = {c.get("id"): c for c in diag_inst.findall("EVENTDATA/CONDITIONS/CONDITION")}
    # CONDITIONGROUP field
    for cg_field in condition_group_field_dict.values():
        condition_list = []
        for condition_ref_field in cg_field.findall("CONDITIONREF"):
            ref_id = condition_ref_field.get("idref")
            condition_field = condition_field_dict[ref_id]
            info_dict = {"name": condition_field.findtext("QUAL"), "init_type": condition_field.get("initType")}
            condition_list.append(info_dict)
        condition_group_dict[cg_field.get("id")] = condition_list
    # CONDITION field
    for c_id, c_field in condition_field_dict.items():
        info_dict = {"name": c_field.findtext("QUAL"), "init_type": c_field.get("initType")}
        condition_group_dict[c_id] = [info_dict]

    record_field_table = {record.attrib["id"]: record for record in ecu_doc.findall("RECORDDTPOOL/RECORDDT/RECORD")}
    record_field_table.update(
        {record.attrib["id"]: record for record in diag_inst.findall("SIMPLECOMPCONT/RECORDDATAOBJ/RECORDDT/RECORD")})
    dtc_table = {dtc.value: dtc for dtc in dtc_list}

    events = []
    for event_field in diag_inst.findall("EVENTDATA/EVENTS/EVENT"):
        event = Event(event_field.findtext("QUAL"))
        event.clear_allowed = event_field.get("clearAllowed")
        event.kind = event_field.get("kind")
        event.failure_cycle = event_field.get("failureCycle")
        event.ff_prestorage = event_field.get("ffPrestorage")
        event.ff_prestorage_in_memory = event_field.get("ffPrestoredNvm")
        event.clear_behavior = event_field.get("clearBehavior")
        event.rec_same_op_cycle = event_field.get("recSameOpCycle")
        event.operation_cycle = operation_cycle.get(event_field.get("operationCycleRef"), None)
        if cg_field_id := event_field.get("eConditionRef"):
            event.condition = condition_group_dict[cg_field_id]
        if cg_field_id := event_field.get("sConditionRef"):
            event.storage_condition = condition_group_dict[cg_field_id]
        if "algorithmRef" in event_field.attrib:
            # Gather debounce algorithum info. "da" stands for "debounce algorithum"
            da_info_dcit = {}
            da_field: ElementTree.Element = debounce_algorithum[event_field.attrib["algorithmRef"]]
            if da_field.tag == "COUNTERBASEDALGORITHM":
                da_info_dcit["type"] = "counter_based"
                da_info_dcit["behavior"] = da_field.get("behavior")
                da_info_dcit["counter_storage"] = da_field.get("counterStorage")
                da_info_dcit["inc_step"] = da_field.get("incStep")
                da_info_dcit["dec_step"] = da_field.get("decStep")
                da_info_dcit["j_down_allowed"] = da_field.get("jDownAllowed")
                da_info_dcit["j_down"] = da_field.get("jDown")
                da_info_dcit["j_up_allowed"] = da_field.get("jUpAllowed")
                da_info_dcit["j_up"] = da_field.get("jUp")
                da_info_dcit["passed_threshold"] = da_field.get("passedThreshold")
                da_info_dcit["failed_threshold"] = da_field.get("failedThreshold")
                da_info_dcit["fdc_threshold"] = da_field.get("fdcThreshold")
            elif da_field.tag == "TIMEBASEDALGORITHM":
                da_info_dcit["type"] = "time_based"
                da_info_dcit["behavior"] = da_field.get("behavior")
                da_info_dcit["passed_threshold"] = da_field.get("passedThreshold")
                da_info_dcit["failed_threshold"] = da_field.get("failedThreshold")
                da_info_dcit["fdc_threshold"] = da_field.get("fdcThreshold")
            else:
                print(f"Unsupported debounce algorithm {da_field.tag}")
            event.algorithm = da_info_dcit
        if "recordRef" in event_field.attrib:
            record_field = record_field_table.get(event_field.get("recordRef"))
            value = record_field.get("v")
            dtc = dtc_table.get(int(value), None)
            event.dtc = dtc

        if indicator_connector_field := event_field.find("INDICATORCONNECTOR"):
            ic_info = {
                "behivor": indicator_connector_field.get("behavior"),
                "healing_cycle_counter": indicator_connector_field("healingCycleCounter"),
                "operation_cycle": operation_cycle.get(event_field.get("operationCycleRef"), None),
                "indicator": indicator.get(event_field.get("indicatorRef"), None)
            }
            event.indicator_connector = ic_info
        events.append(event)

    return events


def _parse_parameters(diag_inst, dcl_tmpls, data_types):
    parameter_list = []

    # Find the corresponding dcl tmpl of the diag class
    dcl_tmpl = dcl_tmpls[diag_inst.attrib["tmplref"]]
    # Build lookup table of shproxy
    id_to_shproxy = {shproxy.attrib["id"]: shproxy for shproxy in dcl_tmpl.findall("SHPROXY")}

    for simpl_comp_cont in diag_inst.findall("SIMPLECOMPCONT"):
        # Temporaryly ignore specdataobj
        if simpl_comp_cont.find("SPECDATAOBJ"):
            continue
        simple_procy_comp_id = [
            ref.attrib["idref"] for ref in id_to_shproxy[simpl_comp_cont.attrib["shproxyref"]].findall("PROXYCOMPREF")
        ]

        parameter_dict = {
            "name": id_to_shproxy[simpl_comp_cont.attrib["shproxyref"]].find("QUAL").text,
            "datas": _parse_parameter_datas(simpl_comp_cont, data_types),
            "simple_proxy_comp_id": simple_procy_comp_id
        }
        parameter_list.append(parameter_dict)

    return parameter_list


def _bind_parameter_with_service(parameter_list, service, id_to_dcl_srv_tmpl, id_to_protocol_service):
    """
    Find parameters of the service according to "SIMPLEPROXYCOMP" tag
    """
    bind_parameter_dict = {"req_param": None, "pos_param": None}

    # Find the protocol service which service derived from
    dcl_srv_tmpl = id_to_dcl_srv_tmpl[service.attrib["tmplref"]]
    protocol_service = id_to_protocol_service[dcl_srv_tmpl.attrib["tmplref"]]
    # Get simple proxy comp id of request
    req_simple_proxy_comp = protocol_service.find("REQ/SIMPLEPROXYCOMP")
    req_simple_proxy_comp_id = req_simple_proxy_comp.attrib["id"] if req_simple_proxy_comp else []
    # Get simple proxy comp id of positive respond
    pos_simple_proxy_comp = protocol_service.find("POS/SIMPLEPROXYCOMP")
    pos_simple_proxy_comp_id = pos_simple_proxy_comp.attrib["id"] if pos_simple_proxy_comp else []
    # Iterate all patameters
    for parameter in parameter_list:
        # If the paramter's simple proxy comp id is the request or positive respond,
        # it implies the parameter is used by the service
        if req_simple_proxy_comp_id in parameter["simple_proxy_comp_id"]:
            bind_parameter_dict["req_param"] = {
                key: value for key, value in parameter.items() if key in ["name", "datas"]
            }
        elif pos_simple_proxy_comp_id in parameter["simple_proxy_comp_id"]:
            bind_parameter_dict["pos_param"] = {
                key: value for key, value in parameter.items() if key in ["name", "datas"]
            }

    return bind_parameter_dict


def _load_routines(ecu_doc: ElementTree.Element, dcl_tmpls: Dict, data_types, state_groups):
    var = ecu_doc.findall("ECU")[0].find("VAR")
    routine_list = []
    diag_class_list = _find_spec_diag_class(var, dcl_tmpls, "rtn")
    diag_class = None
    if diag_class_list:
        diag_class = diag_class_list[0]
    else:
        diag_class = list(
            filter(lambda diag_class: "Routine" in diag_class.find("QUAL").text,
                   _find_spec_diag_class(var, dcl_tmpls, "ctl")))[0]
    # Find the corresponding dcl tmpl of the diag class
    dcl_tmpl = dcl_tmpls[diag_class.attrib["tmplref"]]
    # Build lookup table of dcl service tmpls
    id_to_dcl_srv_tmpl = {srv_tmpl.attrib["id"]: srv_tmpl for srv_tmpl in dcl_tmpl.findall("DCLSRVTMPL")}
    # Build lookup table of shproxy
    id_to_protocol_service = {
        protocol_service.attrib["id"]: protocol_service
        for protocol_service in ecu_doc.findall("PROTOCOLSERVICES/PROTOCOLSERVICE")
    }

    for diag_inst in diag_class.findall("DIAGINST"):
        name = diag_inst.find("QUAL").text
        identifier = diag_inst.find("STATICVALUE").attrib["v"]
        # Parse all parameters of the diag instance
        diag_inst_parameter_list = _parse_parameters(diag_inst, dcl_tmpls, data_types)
        # Parse all service of the routine
        service_list = []
        for service in diag_inst.findall("SERVICE"):
            service_name = service.find("SHORTCUTQUAL").text
            dcl_srv_tmpl = id_to_dcl_srv_tmpl[service.attrib["tmplref"]]
            protocol_service = id_to_protocol_service[dcl_srv_tmpl.attrib["tmplref"]]
            req_const_comp = protocol_service.findall("REQ/CONSTCOMP")
            service_id = None
            subservice_id = None
            # Find sid and ssid for this service
            try:
                service_id = req_const_comp[0].attrib["v"]
                subservice_id = req_const_comp[1].attrib["v"]
            except Exception:
                LOGGER.error(f"Cannot find sid and ssid for routine {name}!")
            service_parameter_dict = _bind_parameter_with_service(parameter_list=diag_inst_parameter_list,
                                                                  service=service,
                                                                  id_to_dcl_srv_tmpl=id_to_dcl_srv_tmpl,
                                                                  id_to_protocol_service=id_to_protocol_service)
            service_execute_permission = parse_service_element_execute_permission(service, state_groups)
            service_list.append(
                RoutineService(name=service_name,
                               sid=service_id,
                               ssid=subservice_id,
                               parameter_dict=service_parameter_dict,
                               execute_permission=service_execute_permission))
        new_routine = Routine(name=name, identifier=identifier, service_list=service_list)
        new_routine.set_used(not diag_inst.attrib.get("act", "1") == "0")
        routine_list.append(new_routine)

    return routine_list


def _load_dids(ecu_doc: ElementTree.Element, dcl_tmpls: Dict, data_types: Dict, did_data_lib, state_groups,
               protocol_service_dict):
    """
    Load all dids
    """
    dids = {}
    var = ecu_doc.find("ECU/VAR")

    # In some situation, there is a DIDS tag in cdd file
    # If there is DIDS tag, iterate its all elements to gather dids
    for did in did_data_lib.values():
        did = _load_did_element_from_dids_tag(did, data_types)
        dids.update({did.identifier: did})

    # Hard code the diag classes where dids are
    diag_classes_abbre = ["idn", "act", "std", "ctl", "vcd"]
    # Iterate all diag classes to find all dids
    for diag_class in var.findall("DIAGCLASS"):
        tmpl = dcl_tmpls[diag_class.attrib["tmplref"]]
        # Check if the diag calsses in hardcode list
        if tmpl.attrib["cls"] not in diag_classes_abbre or tmpl.find("SHSTATIC").attrib["spec"] != "id":
            continue
        # Iterate diag instances of this diag class to find dids
        for diag_inst in diag_class.findall("DIAGINST"):
            # Find the corresponding dcl tmpl of the diag class
            dcl_tmpl = dcl_tmpls[diag_inst.attrib["tmplref"]]
            # Build lookup table of dcl service tmpls
            id_to_dcl_srv_tmpl = {srv_tmpl.attrib["id"]: srv_tmpl for srv_tmpl in dcl_tmpl.findall("DCLSRVTMPL")}
            did = _load_did_element_from_diag_inst(diag_inst, data_types, state_groups, dids, id_to_dcl_srv_tmpl,
                                                   protocol_service_dict)
            # If this did already in dids, replace it with last parse result
            dids.update({did.identifier: did})

    return dids


def target_dcl_tmp_iter(dcl_tmpl_list: List[ElementTree.Element], protocol_service_dict: Dict[str, ElementTree.Element],
                        target_sid: Tuple[str]):
    try:
        int_target_sid = tuple(int(sid, 16) for sid in target_sid)
    except ValueError as e:
        raise ValueError(f"{e}. Invalid sid input!") from e

    for dcl_tmpl in dcl_tmpl_list:
        for dcl_srv_tmpl in dcl_tmpl.findall("DCLSRVTMPL"):
            ref_id: str = dcl_srv_tmpl.attrib["tmplref"]
            protocol_service = protocol_service_dict[ref_id]
            sid = protocol_service.find("REQ/CONSTCOMP").attrib["v"]
            if int(sid) in int_target_sid:
                yield dcl_tmpl


def _load_pids(ecu_doc: ElementTree.Element, dcl_tmpls: Dict, data_types: Dict, protocol_service_dict):

    def load_pid_from_diag_cls(diag_cls, dcl_tmpl):
        pid_dict = {}
        id_to_dcl_srv_tmpl = {srv_tmpl.attrib["id"]: srv_tmpl for srv_tmpl in dcl_tmpl.findall("DCLSRVTMPL")}
        id_to_shproxy = {shproxy.attrib["id"]: shproxy for shproxy in dcl_tmpl.findall("SHPROXY")}
        shproxy_to_proxycomp = {}  # Record mapping from shproxy_id to proxycomp_id referenced by this shproxy
        for shproxy_id, shproxy_obj in id_to_shproxy.items():
            proxycompref_id = map(lambda proxycompref: proxycompref.attrib["idref"],
                                  shproxy_obj.findall("PROXYCOMPREF"))
            shproxy_to_proxycomp[shproxy_id] = list(proxycompref_id)
        for diag_inst in diag_cls.findall("DIAGINST"):
            name = diag_inst.find("QUAL").text
            identifier = diag_inst.find("STATICVALUE").attrib["v"]
            used = not (diag_inst.attrib.get("act", "-1") == "0")
            service_info = {}
            for service_ele in diag_inst.findall("SERVICE"):
                dcl_srv_tmpl = id_to_dcl_srv_tmpl[service_ele.attrib["tmplref"]]
                protocol_service = protocol_service_dict[dcl_srv_tmpl.attrib["tmplref"]]
                req = protocol_service.find("REQ")
                const_comp_list = req.findall("CONSTCOMP")
                sid = const_comp_list[0].attrib["v"]
                if sid in ("1", "2"):
                    pos = protocol_service.find("POS")
                    simpleproxycomp = pos.find("SIMPLEPROXYCOMP")
                    simpleproxycomp_id = simpleproxycomp.attrib["id"]
                    # shproxy format is ({shproxy_id}, {set of simpleproxycomp_id})
                    shproxy = next(filter(lambda item: simpleproxycomp_id in item[1], shproxy_to_proxycomp.items()))
                    simplecompcont = next(
                        filter(lambda ele: ele.attrib["shproxyref"] == shproxy[0], diag_inst.findall("SIMPLECOMPCONT")))
                    data_list = _parse_parameter_datas(simplecompcont, data_types)

                    service_info[sid] = {
                        "param_name": id_to_shproxy[shproxy[0]].findtext("NAME/TUV"),
                        "data_list": data_list
                    }
                else:
                    LOGGER.warning(f"PID {identifier}: Only support 0x01/0x02 service now")

            pid = Pid(name=name, identifier=identifier, service_info=service_info, used=used)
            pid_dict.update({pid.identifier: pid})

        return pid_dict

    dcl_tmpl_iter = target_dcl_tmp_iter(list(dcl_tmpls.values()), protocol_service_dict, ("0x01", "0x02"))
    var = ecu_doc.find("ECU/VAR")
    pids = {}
    for dcl_tmpl in dcl_tmpl_iter:
        dcl_tmpl_id = dcl_tmpl.attrib["id"]
        diag_cls_iter = filter(lambda t: t.attrib["tmplref"] == dcl_tmpl_id, var.findall("DIAGCLASS"))
        for diag_cls in diag_cls_iter:
            pid_dict = load_pid_from_diag_cls(diag_cls, dcl_tmpl)
            pids.update(pid_dict)

    return pids


def _load_vehi_id(ecu_doc: ElementTree.Element, dcl_tmpls: Dict, data_types: Dict, protocol_service_dict):

    def load_vehi_id_from_diag_cls(diag_cls, dcl_tmpl):
        vehi_id_dict = {}
        id_to_dcl_srv_tmpl = {srv_tmpl.attrib["id"]: srv_tmpl for srv_tmpl in dcl_tmpl.findall("DCLSRVTMPL")}
        id_to_shproxy = {shproxy.attrib["id"]: shproxy for shproxy in dcl_tmpl.findall("SHPROXY")}
        shproxy_to_proxycomp = {}  # Record mapping from shproxy_id to proxycomp_id referenced by this shproxy
        for shproxy_id, shproxy_obj in id_to_shproxy.items():
            proxycompref_id = map(lambda proxycompref: proxycompref.attrib["idref"],
                                  shproxy_obj.findall("PROXYCOMPREF"))
            shproxy_to_proxycomp[shproxy_id] = list(proxycompref_id)
        for diag_inst in diag_cls.findall("DIAGINST"):
            name = diag_inst.find("QUAL").text
            used = not (diag_inst.attrib.get("act", "-1") == "0")
            identifier = diag_inst.find("STATICVALUE").attrib["v"]
            service_info = {}
            for service_ele in diag_inst.findall("SERVICE"):
                dcl_srv_tmpl = id_to_dcl_srv_tmpl[service_ele.attrib["tmplref"]]
                protocol_service = protocol_service_dict[dcl_srv_tmpl.attrib["tmplref"]]
                req = protocol_service.find("REQ")
                const_comp_list = req.findall("CONSTCOMP")
                sid = const_comp_list[0].attrib["v"]
                if sid in ("9"):
                    pos = protocol_service.find("POS")
                    simpleproxycomp = pos.find("SIMPLEPROXYCOMP")
                    simpleproxycomp_id = simpleproxycomp.attrib["id"]
                    # shproxy format is ({shproxy_id}, {set of simpleproxycomp_id})
                    shproxy = next(filter(lambda item: simpleproxycomp_id in item[1], shproxy_to_proxycomp.items()))
                    simplecompcont = next(
                        filter(lambda ele: ele.attrib["shproxyref"] == shproxy[0], diag_inst.findall("SIMPLECOMPCONT")))
                    data_list = _parse_parameter_datas(simplecompcont, data_types)

                    service_info[sid] = {"data_list": data_list}
                else:
                    LOGGER.warning(f"Vehi Id {identifier}: Only support 0x09 service now")

            vehi_id = Vehi_id(name=name, identifier=identifier, service_info=service_info, used=used)
            vehi_id_dict.update({vehi_id.identifier: vehi_id})

        return vehi_id_dict

    dcl_tmpl_iter = target_dcl_tmp_iter(list(dcl_tmpls.values()), protocol_service_dict, ("0x09",))
    var = ecu_doc.find("ECU/VAR")
    vehi_ids = {}
    for dcl_tmpl in dcl_tmpl_iter:
        dcl_tmpl_id = dcl_tmpl.attrib["id"]
        diag_cls_iter = filter(lambda t: t.attrib["tmplref"] == dcl_tmpl_id, var.findall("DIAGCLASS"))
        for diag_cls in diag_cls_iter:
            vehi_id_dict = load_vehi_id_from_diag_cls(diag_cls, dcl_tmpl)
            vehi_ids.update(vehi_id_dict)

    return vehi_ids


def load_string(string):
    """Parse given CDD format string.

    """

    root = ElementTree.fromstring(string)
    version = root.attrib.get("dtdvers", "")
    assert version.startswith("13"), f"VersionError: Unsupported version '{version}', please convert to CANdela 13"
    ecu_doc = root.find("ECUDOC")
    assert ecu_doc, "Missing key element 'ECUDOC'"
    assert ecu_doc.find("ECU"), "Missing key element 'ECU'"
    def_atts = _load_def_atts(ecu_doc)
    interface_param = _load_interface_param(ecu_doc)
    data_types = _load_data_types(ecu_doc)
    did_data_lib = _load_did_data_refs(ecu_doc)
    dcl_tmpls = _load_dcl_tmpls(ecu_doc)
    record_tmpls = _load_record_tmpls(ecu_doc, "faultMemory")
    states_groups = _load_state_groups(ecu_doc)
    protocol_services = _load_protocol_services(ecu_doc)
    _update_session_level_used_info(ecu_doc, dcl_tmpls, protocol_services, states_groups)
    _update_security_level_info(ecu_doc, dcl_tmpls, protocol_services, states_groups, data_types)
    uds_services = _load_uds_services(ecu_doc, dcl_tmpls, protocol_services, states_groups)
    var = ecu_doc.findall("ECU")[0].find("VAR")
    dtcs, enable_conditions, enable_condition_groups = _load_dtcs(ecu_doc, var, dcl_tmpls, record_tmpls,
                                                                  def_atts.get("RECORDATTS", {}))
    obd_dtcs = _load_obd_dtcs(ecu_doc, var, dcl_tmpls, record_tmpls, protocol_services, def_atts.get("RECORDATTS", {}))
    operation_cycle = _load_operation_cycles(var, dcl_tmpls)
    debounces_algorithm = _load_debounce_algorithms(var, dcl_tmpls)
    indicator = _load_indicator(var, dcl_tmpls)
    events = _load_events(ecu_doc, dcl_tmpls, operation_cycle, debounces_algorithm, dtcs, indicator)
    routines = _load_routines(ecu_doc, dcl_tmpls, data_types, states_groups)

    dids = _load_dids(ecu_doc, dcl_tmpls, data_types, did_data_lib, states_groups, protocol_services)
    pids = _load_pids(ecu_doc, dcl_tmpls, data_types, protocol_services)
    vehi_ids = _load_vehi_id(ecu_doc, dcl_tmpls, data_types, protocol_services)

    snapshots = _load_snapshots(ecu_doc, dcl_tmpls, dids, protocol_services, data_types)
    # snapshots = []
    extended_datas = _load_extended_datas(ecu_doc, dcl_tmpls, data_types)
    # extended_datas = []

    return InternalDatabase(dids=list(dids.values()),
                            pids=pids,
                            vehi_ids=vehi_ids,
                            dtcs=dtcs,
                            obd_dtcs=obd_dtcs,
                            enable_conditions=enable_conditions,
                            enable_condition_groups=enable_condition_groups,
                            events=events,
                            snapshots=snapshots,
                            extended_datas=extended_datas,
                            uds_services=uds_services,
                            state_groups=states_groups,
                            routines=routines,
                            interface_param=interface_param)
