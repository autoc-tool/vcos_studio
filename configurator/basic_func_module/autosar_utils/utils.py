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
from functools import wraps
from autosar44 import autosar44


def check_attr(func):

    @wraps(func)
    def infunc(*args, **kwargs):
        attr = func.__name__.replace("get_", "", 1)
        if attr == func.__name__:
            attr = attr.replace("set_", "", 1)
        attr = attr.upper()
        if hasattr(args[0], attr):
            if getattr(args[0], attr):
                return func(*args, **kwargs)
            elif "set_" == func.__name__[:4]:
                return func(*args, **kwargs)
        # else:
        #     print(f"{args[0]} not have {attr}")
        return None

    return infunc


@check_attr
def get_short_name(obj):
    return obj.SHORT_NAME.valueOf_


@check_attr
def get_admin_data(obj):
    result = []
    if obj.ADMIN_DATA is not None:
        for sdg_value in obj.ADMIN_DATA.SDGS.SDG:
            for sd_value in sdg_value.SD:
                result.append({sd_value.GID: sd_value.valueOf_})
    else:
        result = None

    return result


def get_admin_data_all(obj):
    def parse_sdg(sdg_obj):
        # 初始化一个空字典来存储当前SDG的数据
        current_data = {}
        # 如果当前节点有子SDG，递归解析它们
        if hasattr(sdg_obj, "SDG"):
            for child_sdg in sdg_obj.SDG:
                current_data[child_sdg.GID] = parse_sdg(child_sdg)
        # 如果当前节点有SD，提取它们的信息
        if hasattr(sdg_obj, "SD"):
            for child_sd in sdg_obj.SD:
                # 注意：这里假设每个SDG下的SD的GID是唯一的
                current_data[child_sd.GID] = child_sd.valueOf_
        return current_data

    # 检查ADMIN_DATA和SDGS是否存在
    if (
        hasattr(obj, "ADMIN_DATA")
        and obj.ADMIN_DATA is not None
        and hasattr(obj.ADMIN_DATA, "SDGS")
        and obj.ADMIN_DATA.SDGS is not None
    ):
        result = {}  # 结果字典
        # 遍历每个顶层SDG
        for sdg in obj.ADMIN_DATA.SDGS.SDG:
            result[sdg.GID] = parse_sdg(sdg)
        return result
    else:
        return None


@check_attr
def get_annotations(obj):
    result = []
    if obj.ANNOTATIONS is not None:
        for i in range(len(obj.ANNOTATIONS.ANNOTATION)):
            result.append(obj.ANNOTATIONS.ANNOTATION[i].ANNOTATION_ORIGIN.valueOf_)
    else:
        result = None

    return result


@check_attr
def get_module_description_ref(obj):
    return obj.MODULE_DESCRIPTION_REF.valueOf_


@check_attr
def get_definition_ref(obj):
    return obj.DEFINITION_REF.valueOf_


def get_numerical_param_value(obj):
    value_string = get_value(obj)
    if value_string is None:
        return None
    if value_string.strip().lower() == "true":
        return True
    elif value_string.strip().lower() == "false":
        return False
    else:
        if "." in value_string or "E-" in value_string or "e-" in value_string:
            return float(value_string)
        elif value_string.startswith("0x"):
            return int(value_string, 16)
        elif value_string.startswith("0o"):
            return int(value_string, 8)
        elif value_string.startswith("0b"):
            return int(value_string, 2)
        elif "" == value_string or None is value_string:
            return ""
        else:
            return int(value_string)


@check_attr
def get_value_ref(obj):
    value_ref_obj = getattr(obj, "VALUE_REF", None)
    value_of = getattr(value_ref_obj, "valueOf_", None)
    return value_of


def get_lower_multiplicity(obj):
    return int(obj.LOWER_MULTIPLICITY.valueOf_) if obj.LOWER_MULTIPLICITY is not None else 0


@check_attr
def get_destination_type(obj):
    return obj.DESTINATION_TYPE.valueOf_


def get_upper_multiplicity(obj):

    return int(obj.UPPER_MULTIPLICITY.valueOf_) if obj.UPPER_MULTIPLICITY is not None else 1


def get_upper_multiplicity_infinite(obj):
    value_obj = getattr(obj, "UPPER_MULTIPLICITY_INFINITE", None)
    if value_obj is not None:
        if value_obj.valueOf_ in ("true", "1"):
            return 65536
        elif isinstance(value_obj.valueOf_, str) and value_obj.valueOf_.isdigit():
            return int(value_obj.valueOf_)
    return 0


def get_multiplicity(obj):
    return (get_lower_multiplicity(obj), get_upper_multiplicity(obj), get_upper_multiplicity_infinite(obj))


@check_attr
def get_origin(obj):
    if obj.ORIGIN:
        return obj.ORIGIN.valueOf_


@check_attr
def get_desc(obj):
    if obj.DESC:
        return "\n".join([desc_obj.valueOf_ for desc_obj in getattr(obj.DESC, "L_2", []) if desc_obj])


@check_attr
def get_introduction(obj):
    if obj.INTRODUCTION and obj.INTRODUCTION.P:
        return obj.INTRODUCTION.P[0].L_1[0].valueOf_


@check_attr
def get_max(obj):
    return obj.MAX.valueOf_


def get_max_interval_type(obj):
    return getattr(getattr(obj, "MAX", None), "INTERVAL_TYPE", "CLOSED")


def get_min_interval_type(obj):
    return getattr(getattr(obj, "MIN", None), "INTERVAL_TYPE", "CLOSED")


def get_max_length(obj):
    variants_tag = obj.original_tagname_.replace("-", "_") + "_VARIANTS"
    conditional_tag = obj.original_tagname_.replace("-", "_") + "_CONDITIONAL"
    variants_obj = getattr(obj, variants_tag, None)
    if variants_obj is None:
        return None
    conditional_obj_list = getattr(variants_obj, conditional_tag, None)
    if conditional_obj_list is None or len(conditional_obj_list) == 0:
        return None
    if getattr(conditional_obj_list[0], "MAX_LENGTH", None) is None:
        return None
    return conditional_obj_list[0].MAX_LENGTH.valueOf_


@check_attr
def get_min(obj):
    return obj.MIN.valueOf_


def get_min_length(obj):
    variants_tag = obj.original_tagname_.replace("-", "_") + "_VARIANTS"
    conditional_tag = obj.original_tagname_.replace("-", "_") + "_CONDITIONAL"
    variants_obj = getattr(obj, variants_tag, None)
    if variants_obj is None:
        return None
    conditional_obj_list = getattr(variants_obj, conditional_tag, None)
    if conditional_obj_list is None or len(conditional_obj_list) == 0:
        return None
    if getattr(conditional_obj_list[0], "MIN_LENGTH", None) is None:
        return None
    return conditional_obj_list[0].MIN_LENGTH.valueOf_


def get_range(obj):
    return (get_max(obj), get_min(obj))


@check_attr
def get_destination_refs(obj):
    ret = []
    for ref in obj.DESTINATION_REFS.DESTINATION_REF:
        ret.append(ref.valueOf_)
    return ret


@check_attr
def get_destination_ref(obj):
    return obj.DESTINATION_REF.valueOf_


@check_attr
def get_default_value(obj):
    if obj.DEFAULT_VALUE:
        return obj.DEFAULT_VALUE.valueOf_


def get_vcos_cfg_value(obj):
    cfg_value = None
    if admin_data := getattr(obj, "ADMIN_DATA", None):
        for sdg in admin_data.SDGS.SDG:
            for sd in sdg.SD:
                if sd.GID == "VCOS:CfgValue":
                    return sd.valueOf_

    return cfg_value


@check_attr
def get_value(obj):
    target_obj = getattr(obj, "VALUE", None)
    value_of = getattr(target_obj, "valueOf_", None)
    return value_of


def get_valueOf(obj):
    return obj.valueOf_


def get_label(obj):
    return obj.SHORT_LABEL.valueOf_


@check_attr
def get_target_ref(obj):
    target_obj = getattr(obj, "TARGET_REF", None)
    value_of = getattr(target_obj, "valueOf_", None)
    return value_of


@check_attr
def get_value_iref(obj):
    return get_target_ref(obj.VALUE_IREF)


@check_attr
def set_value(obj, value):
    if value is None:
        obj.VALUE = None
        return
    tag = obj.original_tagname_
    if obj.VALUE is None:
        if tag == "ECUC-TEXTUAL-PARAM-VALUE":
            obj.VALUE = autosar44.VERBATIM_STRING()
        elif tag == "ECUC-NUMERICAL-PARAM-VALUE":
            obj.VALUE = autosar44.NUMERICAL_VALUE_VARIATION_POINT()
            # # Constants for category:
            # CategoryNone = 0
            # CategoryText = 1
            # CategorySimple = 2
            # CategoryComplex = 3
            # # Constants for content_type:
            # TypeNone = 0
            # TypeText = 1
            # TypeString = 2
            # TypeInteger = 3
            # TypeFloat = 4
            # TypeDecimal = 5
            # TypeDouble = 6
            # TypeBoolean = 7
            # TypeBase64 = 8
            mixed_container = autosar44.MixedContainer(
                autosar44.MixedContainer.CategoryText, autosar44.MixedContainer.TypeNone, "", value
            )
            obj.VALUE.content_.append(mixed_container)
        elif tag == "ECUC-ADD-INFO-PARAM-VALUE":
            # TODO
            obj.VALUE = autosar44.VERBATIM_STRING()
        obj.VALUE.set_parent(obj)
    if tag == "ECUC-NUMERICAL-PARAM-VALUE":
        if len(obj.VALUE.content_) == 0:
            mixed_container = autosar44.MixedContainer(
                autosar44.MixedContainer.CategoryText, autosar44.MixedContainer.TypeNone, "", value
            )
            obj.VALUE.content_.append(mixed_container)
        obj.VALUE.content_[0].value = value
    obj.VALUE.valueOf_ = value


@check_attr
def set_value_ref(obj, value):
    if value is None:
        obj.VALUE_REF = None
        return
    tag = obj.original_tagname_
    if obj.VALUE_REF is None:
        if tag == "ECUC-REFERENCE-VALUE":
            obj.VALUE_REF = autosar44.VALUE_REFType2137()

    obj.VALUE_REF.valueOf_ = value


@check_attr
def set_value_iref(obj, value):
    if value is None:
        obj.VALUE_IREF = None
        return
    tag = obj.original_tagname_
    if obj.VALUE_IREF is None:
        if tag == "ECUC-INSTANCE-REFERENCE-VALUE":
            obj.VALUE_IREF = autosar44.ANY_INSTANCE_REF()
            obj.VALUE_IREF.TARGET_REF = autosar44.TARGET_REFType73()

    obj.VALUE_IREF.TARGET_REF.valueOf_ = value


@check_attr
def set_short_name(obj, value):
    if obj.SHORT_NAME is None:
        obj.SHORT_NAME = autosar44.IDENTIFIER()
        obj.SHORT_NAME.parent_object_ = obj
        obj.SHORT_NAME.original_tagname_ = "SHORT-NAME"
        obj.SHORT_NAME.set_parent(obj)
    obj.SHORT_NAME.valueOf_ = value


@check_attr
def set_vt(obj, value):
    if obj.VT is None:
        obj.VT = autosar44.VERBATIM_STRING()
        obj.VT.parent_object_ = obj
        obj.VT.original_tagname_ = "VT"
        obj.VT.set_parent(obj)
    obj.VT.valueOf_ = value


@check_attr
def set_lower_limit(obj, value, interval_type=None):
    if obj.LOWER_LIMIT is None:
        obj.LOWER_LIMIT = autosar44.LIMIT()
        mixed_container = autosar44.MixedContainer(
            autosar44.MixedContainer.CategoryText, autosar44.MixedContainer.TypeNone, "", value
        )
        obj.LOWER_LIMIT.content_.append(mixed_container)
        obj.LOWER_LIMIT.parent_object_ = obj
        obj.LOWER_LIMIT.original_tagname_ = "LOWER-LIMIT"
        obj.LOWER_LIMIT.set_parent(obj)
    obj.LOWER_LIMIT.valueOf_ = value

    if interval_type:
        obj.LOWER_LIMIT.INTERVAL_TYPE = str(interval_type)


@check_attr
def set_upper_limit(obj, value, interval_type=None):
    if obj.UPPER_LIMIT is None:
        obj.UPPER_LIMIT = autosar44.LIMIT()
        mixed_container = autosar44.MixedContainer(
            autosar44.MixedContainer.CategoryText, autosar44.MixedContainer.TypeNone, "", value
        )
        obj.UPPER_LIMIT.content_.append(mixed_container)
        obj.UPPER_LIMIT.parent_object_ = obj
        obj.UPPER_LIMIT.original_tagname_ = "UPPER-LIMIT"
        obj.UPPER_LIMIT.set_parent(obj)
    obj.UPPER_LIMIT.valueOf_ = value

    if interval_type:
        obj.UPPER_LIMIT.INTERVAL_TYPE = str(interval_type)


@check_attr
def set_category(obj, value):
    if obj.CATEGORY is None:
        obj.CATEGORY = autosar44.CATEGORY_STRING()
        obj.CATEGORY.parent_object_ = obj
        obj.CATEGORY.original_tagname_ = "CATEGORY"
        obj.CATEGORY.set_parent(obj)
    obj.CATEGORY.valueOf_ = value


@check_attr
def set_base_type_size(obj, value):
    if obj.BASE_TYPE_SIZE is None:
        obj.BASE_TYPE_SIZE = autosar44.POSITIVE_INTEGER()
        obj.BASE_TYPE_SIZE.parent_object_ = obj
        obj.BASE_TYPE_SIZE.original_tagname_ = "BASE-TYPE-SIZE"
        obj.BASE_TYPE_SIZE.set_parent(obj)
    obj.BASE_TYPE_SIZE.valueOf_ = str(value)


@check_attr
def set_base_type_encoding(obj, value):
    if obj.BASE_TYPE_ENCODING is None:
        obj.BASE_TYPE_ENCODING = autosar44.BASE_TYPE_ENCODING_STRING()
        obj.BASE_TYPE_ENCODING.parent_object_ = obj
        obj.BASE_TYPE_ENCODING.original_tagname_ = "BASE-TYPE-ENCODING"
        obj.BASE_TYPE_ENCODING.set_parent(obj)
    obj.BASE_TYPE_ENCODING.valueOf_ = value


@check_attr
def set_definition_ref(obj, dest, value):
    if obj.DEFINITION_REF is None:
        obj.DEFINITION_REF = autosar44.DEFINITION_REFType()
        obj.DEFINITION_REF.parent_object_ = obj
        obj.DEFINITION_REF.original_tagname_ = "DEFINITION-REF"
        obj.DEFINITION_REF.DEST = dest
    obj.DEFINITION_REF.valueOf_ = value


def get_definition_ref_dest(obj):
    if hasattr(obj, "DEFINITION_REF"):
        return obj.DEFINITION_REF.DEST
    else:
        return None


@check_attr
def get_is_service(obj):
    return obj.IS_SERVICE.valueOf_


@check_attr
def get_category(obj):
    return obj.CATEGORY.valueOf_


@check_attr
def get_unit_ref(obj):
    return obj.UNIT_REF.valueOf_


@check_attr
def get_factor_si_to_unit(obj):
    return obj.FACTOR_SI_TO_UNIT.valueOf_


@check_attr
def get_offset_si_to_unit(obj):
    return obj.OFFSET_SI_TO_UNIT.valueOf_


@check_attr
def get_base_type_size(obj):
    return obj.BASE_TYPE_SIZE.valueOf_


@check_attr
def get_base_type_encoding(obj):
    return obj.BASE_TYPE_ENCODING.valueOf_


@check_attr
def get_native_declaration(obj):
    return obj.NATIVE_DECLARATION.valueOf_


@check_attr
def get_lower_limit(obj):
    return obj.LOWER_LIMIT.valueOf_


@check_attr
def get_upper_limit(obj):
    return obj.UPPER_LIMIT.valueOf_


@check_attr
def get_type_tref(obj):
    return obj.TYPE_TREF.valueOf_


@check_attr
def get_array_size(obj):
    return obj.ARRAY_SIZE.valueOf_


@check_attr
def get_array_size_semantics(obj):
    return obj.ARRAY_SIZE_SEMANTICS.valueOf_


@check_attr
def get_direction(obj):
    return obj.DIRECTION.valueOf_


@check_attr
def get_server_argument_impl_policy(obj):
    return obj.SERVER_ARGUMENT_IMPL_POLICY.valueOf_


@check_attr
def get_period(obj):
    return obj.PERIOD.valueOf_


@check_attr
def get_symbol(obj):
    return obj.SYMBOL.valueOf_


@check_attr
def get_can_be_invoked_concurrently(obj):
    return obj.CAN_BE_INVOKED_CONCURRENTLY.valueOf_


@check_attr
def get_minimum_start_interval(obj):
    return obj.MINIMUM_START_INTERVAL.valueOf_


@check_attr
def get_timeout(obj):
    return obj.TIMEOUT.valueOf_


@check_attr
def get_context_r_port_ref(obj):
    return obj.CONTEXT_R_PORT_REF.valueOf_


def get_target_p_port_ref(obj):
    return obj.TARGET_P_PORT_REF.valueOf_


def get_target_r_port_ref(obj):
    return obj.TARGET_R_PORT_REF.valueOf_


def get_context_component_ref(obj):
    return obj.CONTEXT_COMPONENT_REF.valueOf_


@check_attr
def get_provided_interface_tref(obj):
    return obj.PROVIDED_INTERFACE_TREF.valueOf_


@check_attr
def get_init_value(obj):
    return obj.INIT_VALUE.NUMERICAL_VALUE_SPECIFICATION.VALUE.valueOf_


@check_attr
def get_uses_end_to_end_protection(obj):
    return obj.USES_END_TO_END_PROTECTION.valueOf_


@check_attr
def get_handle_out_of_range(obj):
    return obj.HANDLE_OUT_OF_RANGE.valueOf_


@check_attr
def get_required_interface_tref(obj):
    return obj.REQUIRED_INTERFACE_TREF.valueOf_


@check_attr
def get_handle_timeout_type(obj):
    return obj.HANDLE_TIMEOUT_TYPE.valueOf_


@check_attr
def get_handle_never_received(obj):
    return obj.HANDLE_NEVER_RECEIVED.valueOf_


@check_attr
def get_enable_update(obj):
    return obj.ENABLE_UPDATE.valueOf_


@check_attr
def get_alive_timeout(obj):
    return obj.ALIVE_TIMEOUT.valueOf_


@check_attr
def get_queue_length(obj):
    return obj.QUEUE_LENGTH.valueOf_


@check_attr
def get_operation_ref(obj):
    return obj.OPERATION_REF.valueOf_


@check_attr
def get_sw_calibration_access(obj):
    return obj.SW_CALIBRATION_ACCESS.valueOf_


@check_attr
def get_base_type_ref(obj):
    return obj.BASE_TYPE_REF.valueOf_


@check_attr
def get_data_constr_ref(obj):
    return obj.DATA_CONSTR_REF.valueOf_


@check_attr
def get_data_element_ref(obj):
    return obj.DATA_ELEMENT_REF.valueOf_


@check_attr
def get_start_on_event_ref(obj):
    return obj.START_ON_EVENT_REF.valueOf_


@check_attr
def get_starts_on_event_ref(obj):
    return obj.STARTS_ON_EVENT_REF.valueOf_


@check_attr
def get_implemented_entry_ref(obj):
    return obj.IMPLEMENTED_ENTRY_REF.valueOf_


@check_attr
def get_application_data_type_ref(obj):
    return obj.APPLICATION_DATA_TYPE_REF.valueOf_


@check_attr
def get_implementation_data_type_ref(obj):
    return obj.IMPLEMENTATION_DATA_TYPE_REF.valueOf_


@check_attr
def get_port_ref(obj):
    return obj.PORT_REF.valueOf_


@check_attr
def get_context_p_port_ref(obj):
    return obj.CONTEXT_P_PORT_REF.valueOf_


@check_attr
def get_target_trigger_ref(obj):
    return obj.TARGET_TRIGGER_REF.valueOf_


@check_attr
def get_outer_port_ref(obj):
    return obj.OUTER_PORT_REF.valueOf_


@check_attr
def get_activation_reason_representation_ref(obj):
    return obj.ACTIVATION_REASON_REPRESENTATION_REF.valueOf_


@check_attr
def get_bit_position(obj):
    return obj.BIT_POSITION.valueOf_


def convert_arxml_string_escape_characters(autosar):
    ls = []
    ls += autosar.find_nodes("L-1")
    ls += autosar.find_nodes("L-2")
    for lable in ls:
        if len(lable.content_) == 0:
            continue
        lable.content_[0].value = lable.valueOf_.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def get_runnable_symbol(runnable_obj):
    symbol = get_short_name(runnable_obj)
    if hasattr(runnable_obj, "SYMBOL") and runnable_obj.SYMBOL:
        symbol = get_symbol(runnable_obj)
    return symbol


def get_mod_autosar_version(mod_obj):
    autosar_version = ""
    doc_revision_list = mod_obj.find_nodes("DOC-REVISION")
    for doc_revision in doc_revision_list:
        path = doc_revision.get_path()
        if not path:
            continue
        revision_label = getattr(getattr(doc_revision, "REVISION_LABEL", ""), "valueOf_", "")
        issued_by = getattr(getattr(doc_revision, "ISSUED_BY", ""), "valueOf_", "")
        if issued_by == "AUTOSAR":
            autosar_version = revision_label.strip()
            break
    return autosar_version
