from typing import Dict
from xml.etree.ElementTree import Element
from ..datatype import DataType
from ..data import SimpleData, StructData
from ...utils import cdd_offset_to_dbc_start_bit


def infer_data_type_str(data_type):
    byte_bit_map = {1: "8", 2: "16", 3: "8", 4: "32"}
    tag = data_type.tag
    encoding = data_type.encoding
    bit_length = data_type.bit_length
    minsz = data_type.minimum
    maxsz = data_type.maximum

    data_type_str = ""
    # Infer the sign of data type
    if encoding in ("uns", "bcd", "asc"):
        data_type_str += "UINT"
    elif encoding == "sgn":
        data_type_str += "SINT"
    elif encoding in ("flt", "dbl"):
        return "UINT8_N"
    else:
        print(f"Warning: Unsupported coding {encoding} of {data_type.name}")
    # Infer the length of element of data type
    element_byte_length = (bit_length + 7) // 8
    # For data whose length <= 4 byte, infer its data type str according to its length
    if element_byte_length in byte_bit_map:
        data_type_str += byte_bit_map[element_byte_length]
    # For data whose length > 4. simply consider as UINT8 element
    else:
        data_type_str += "8"

    if tag in ("IDENT", "TEXTTBL"):
        if minsz != maxsz:
            data_type_str = "UINT8_DYN"
        elif maxsz > 1 or element_byte_length == 3:
            data_type_str += "_N"
    elif tag in ("COMPTBL", "LINCOMP", "FORMULADT"):
        if element_byte_length == 3 or element_byte_length > 4:
            data_type_str += "_N"
    elif tag in ("STRUCTDT", "MUXDT"):
        if maxsz > 1:
            data_type_str += "_N"
    elif tag == "STATICITERRDT":
        raise Exception(f"Unsupported data type tag {tag}!")
    elif tag == "GAP":
        data_type_str = "UINT8"
    else:
        raise Exception(f"Unsupported data type tag {tag}!")

    return data_type_str


def load_data_element(data, offset, data_types):
    """Load given signal element and return a signal object.

    """

    if data.tag == "GAPDATAOBJ":
        data_type = DataType(name=data.find("NAME/TUV").text,
                             id_="-1",
                             bit_length=int(data.attrib["bl"]),
                             encoding="uns",
                             minimum=1,
                             maximum=1,
                             choices=None,
                             byte_order="big_endian",
                             unit=None,
                             factor=0,
                             offset=0,
                             category="atom",
                             tag="GAP")
        data_type_str = infer_data_type_str(data_type)
        data_type.set_data_type_str(data_type_str)
    else:
        data_type = data_types[data.attrib["dtref"]]

    # Map CDD/c-style field offset to the DBC/can.Signal.start bit numbering
    # convention for compatability with can.Signal objects and the shared codec
    # infrastructure.
    dbc_start_bitnum = cdd_offset_to_dbc_start_bit(offset, data_type.bit_length, data_type.byte_order)
    if data_type.category == "atom":
        data_length = data_type.bit_length
    elif data_type.category == "field":
        data_length = data_type.bit_length * data_type.maximum
    return SimpleData(name=data.find("QUAL").text,
                      start=dbc_start_bitnum,
                      length=data_length,
                      byte_order=data_type.byte_order,
                      scale=data_type.factor,
                      offset=data_type.offset,
                      minimum=data_type.minimum,
                      maximum=data_type.maximum,
                      unit=data_type.unit,
                      choices=data_type.choices,
                      data_type=data_type)


def load_struct_data_element(struct_element, offset, data_types):
    data_list = []

    # The first SIMPLECOMPCONT tag has data info of the did
    data_element_list = []
    # Iterate all child tag of the simple compcont to gather all datas
    for child in struct_element:
        if child.tag in ("DATAOBJ", "GAPDATAOBJ"):
            data_element_list.append(child)
    data_type = data_types[struct_element.attrib["dtref"]]

    length = data_type.bit_length
    for data_element in data_element_list:
        data = load_data_element(data_element, offset, data_types)

        if data:
            data_list.append(data)
            offset += data.length

    return StructData(name=struct_element.find("QUAL").text, data_list=data_list, length=length, data_type=data_type)


def parse_parameter_datas(simpl_comp_cont, data_types):
    """
    Parse data elements of a simpl comp cont
    """
    data_list = []
    offset = 0
    for data_obj_element in simpl_comp_cont:
        if data_obj_element.tag in ("DATAOBJ", "GAPDATAOBJ"):
            data = load_data_element(data_obj_element, offset, data_types)
        elif data_obj_element.tag == "STRUCT":
            data = load_struct_data_element(data_obj_element, offset, data_types)

        data_list.append(data)

    return data_list


def find_sh_proxy(dcl_tmpl: Element, proxy_comp_ref_id: str):
    for sh_proxy in dcl_tmpl.findall("SHPROXY"):
        for proxy_comp_ref in sh_proxy.findall("PROXYCOMPREF"):
            if proxy_comp_ref_id == proxy_comp_ref.get("idref"):
                return sh_proxy


def find_simple_comp_cont(diag_inst: Element, sh_proxy_ref_id: str):
    for simple_comp_cont in diag_inst.findall("SIMPLECOMPCONT"):
        if sh_proxy_ref_id == simple_comp_cont.get("shproxyref"):
            return simple_comp_cont


def parse_static_comp(static_comp: Element, diag_inst: Element = None):
    comp_dict = {}

    comp_dict["spec"] = static_comp.get("spec", "")
    static_value = diag_inst.find("STATICVALUE")
    comp_dict["value"] = static_value.get("v", "")
    return comp_dict


def parse_simple_proxy_comp(simple_proxy_comp: Element, dcl_tmpl: Element, diag_inst: Element,
                            data_types: Dict[str, DataType]):
    comp_dict = {}

    comp_dict["dest"] = simple_proxy_comp.get("dest", "")
    sh_proxy = find_sh_proxy(dcl_tmpl, simple_proxy_comp.get("id"))
    simple_comp_cont = find_simple_comp_cont(diag_inst, sh_proxy.get("id"))
    comp_dict["data"] = parse_parameter_datas(simple_comp_cont, data_types)

    return comp_dict


def parse_req(protocol_service: Element, diag_inst: Element, dcl_tmpl: Element, data_types: Dict[str, DataType]):
    req_dict = {}
    req_dict["comp_list"] = []

    req_ele = protocol_service.find("REQ")
    for child in req_ele:
        if child.tag == "NAME":
            continue
        elif child.tag == "QUAL":
            req_dict["qual"] = child.text
        elif child.tag == "CONSTCOMP":
            comp_dict = {}
            comp_dict["spec"] = child.get("spec", "")
            comp_dict["value"] = child.get("v", "")
            req_dict["comp_list"].append(comp_dict)
        elif child.tag == "STATICCOMP":
            req_dict["comp_list"].append(parse_static_comp(child, diag_inst))
        elif child.tag == "SIMPLEPROXYCOMP":
            req_dict["comp_list"].append(parse_simple_proxy_comp(child, dcl_tmpl, diag_inst, data_types))
        else:
            print(f"Warning: Unsupported tag {child.tag}")

    return req_dict


def parse_pos(protocol_service: Element, diag_inst: Element, dcl_tmpl: Element, data_types: Dict[str, DataType]):
    pos_dict = {}
    pos_dict["comp_list"] = []

    pos_ele = protocol_service.find("POS")
    for child in pos_ele:
        if child.tag == "NAME":
            continue
        elif child.tag == "QUAL":
            pos_dict["qual"] = child.text
        elif child.tag == "CONSTCOMP":
            comp_dict = {}
            comp_dict["spec"] = child.get("spec", "")
            comp_dict["value"] = child.get("v", "")
            pos_dict["comp_list"].append(comp_dict)
        elif child.tag == "STATICCOMP":
            pos_dict["comp_list"].append(parse_static_comp(child, diag_inst))
        elif child.tag == "SIMPLEPROXYCOMP":
            pos_dict["comp_list"].append(parse_simple_proxy_comp(child, dcl_tmpl, diag_inst, data_types))
        else:
            print(f"Unsupported tag {child.tag}")

    return pos_dict


def parse_service_inst(dcl_tmpl: Element, protocol_service: Element, diag_inst: Element, data_types: Dict[str,
                                                                                                          DataType]):
    """
    return:
    {
        "req": {
            "qual": ...,
            "comp_list": [
                {
                    "spec": ...,
                    "value": ...
                },
                ...
                {
                    "dest": ...,
                    "data": ...
                }
            ]
        },
        "pos": {
            "qual": ...,
            "comp_list": [
                {
                    "spec": ...,
                    "value": ...
                },
                ...
                {
                    "dest": ...,
                    "data": ...
                }
            ]
        },
    }
    """

    service_dict = {
        "name": protocol_service.find("NAME/TUV").text,
        "qual": protocol_service.find("QUAL").text,
        "req": parse_req(protocol_service, diag_inst, dcl_tmpl, data_types),
        "pos": parse_pos(protocol_service, diag_inst, dcl_tmpl, data_types)
    }

    return service_dict
