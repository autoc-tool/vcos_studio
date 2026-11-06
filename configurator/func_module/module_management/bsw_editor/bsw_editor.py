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
import json
from copy import deepcopy
from collections import defaultdict
from func_module.health_monitor.logger import logger
from func_module.module_management.arxml_handler.ecuc_arxml_updater import EcucArxmlUpdater
from func_module.mapping.schedule_table_mapping import ScheduleTableManager
from func_module.module_management.container_rule.bsw_container_rule import RULE_DICT, base_rule_instance
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.autosar_utils.autosar_utils import AutosarUtils
from basic_func_module.file_handler.file_io_handler import FileIOHandler
from basic_func_module.autosar_utils.utils import (
    get_min,
    get_max,
    get_max_length,
    get_min_length,
    get_desc,
    get_origin,
    set_short_name,
    get_short_name,
    get_destination_ref,
    get_destination_refs,
    set_value_ref,
    get_admin_data,
    get_annotations,
    get_lower_multiplicity,
    get_destination_type,
    set_value,
    get_upper_multiplicity,
    get_upper_multiplicity_infinite,
    get_default_value,
    get_definition_ref,
    get_value,
    get_value_ref,
    set_value_iref,
    get_value_iref,
    get_admin_data_all,
    get_max_interval_type,
    get_min_interval_type,
)

CUR_FILE_PATH = os.path.dirname(__file__)

USER_DEFINED_FLAG = "UserDefined"
DEFAULT_FORMAT_FLAG = "DefaultFormat"
ECUC_NUMERICAL_PARAM_VALUE_LIST = ["ECUC-INTEGER-PARAM-DEF", "ECUC-BOOLEAN-PARAM-DEF", "ECUC-FLOAT-PARAM-DEF"]
ECUC_TEXTUAL_PARAM_VALUE_LIST = [
    "ECUC-ENUMERATION-PARAM-DEF",
    "ECUC-FUNCTION-NAME-DEF",
    "ECUC-STRING-PARAM-DEF",
    "ECUC-LINKER-SYMBOL-DEF",
    "ECUC-MULTILINE-STRING-PARAM-DEF",
]
ECUC_ADD_INFO_PARAM_VALUE_LIST = [
    "ECUC-ADD-INFO-PARAM-DEF",
]
ECUC_PARAM_VALUE_LIST = [
    "ECUC-INTEGER-PARAM-DEF",
    "ECUC-BOOLEAN-PARAM-DEF",
    "ECUC-FLOAT-PARAM-DEF",
    "ECUC-ENUMERATION-PARAM-DEF",
    "ECUC-FUNCTION-NAME-DEF",
    "ECUC-STRING-PARAM-DEF",
    "ECUC-LINKER-SYMBOL-DEF",
    "ECUC-MULTILINE-STRING-PARAM-DEF",
    "ECUC-ADD-INFO-PARAM-DEF",
]

ECUC_REFERENCE_VALUE_LIST = [
    "ECUC-REFERENCE-DEF",
    "ECUC-CHOICE-REFERENCE-DEF",
    "ECUC-FOREIGN-REFERENCE-DEF",
    "ECUC-SYMBOLIC-NAME-REFERENCE-DEF",
]
ECUC_IREFERENCE_VALUE_LIST = [
    "ECUC-INSTANCE-REFERENCE-DEF",
]
ECUC_REF_VALUE_LIST = [
    "ECUC-REFERENCE-DEF",
    "ECUC-CHOICE-REFERENCE-DEF",
    "ECUC-FOREIGN-REFERENCE-DEF",
    "ECUC-SYMBOLIC-NAME-REFERENCE-DEF",
    "ECUC-INSTANCE-REFERENCE-DEF",
]

PARAM_SUPPORED_BY_DERIVATION_RULE_OF_COM_1 = [
    "ComIPduCallout",
    "ComIPduTriggerTransmitCallout",
    "ComErrorNotification",
    "ComInvalidNotification",
    "ComNotification",
    "ComTimeoutNotification",
]

PARAM_SUPPORED_BY_DERIVATION_RULE_OF_CANSM_1 = [
    "BusOffBeginFunction",
    "BusOffEndFunction",
]

PARAM_SUPPORED_BY_DERIVATION_RULE_OF_DCM_1 = [
    "DcmDsdSidTabFnc",
    "DcmDsdSubServiceFnc",
    "DcmDspDataConditionCheckReadFnc",
    "DcmDspDataFreezeCurrentStateFnc",
    "DcmDspDataGetScalingInfoFnc",
    "DcmDspDataReadDataLengthFnc",
    "DcmDspDataReadFnc",
    "DcmDspDataResetToDefaultFnc",
    "DcmDspDataReturnControlToEcuFnc",
    "DcmDspDataShortTermAdjustmentFnc",
    "DcmDspDataWriteFnc",
    "DcmDspDataReadEcuSignal",
    "DcmDspPidDataReadFnc",
    "DcmDspRequestRoutineResultsConfirmationFnc",
    "DcmDspRequestRoutineResultsFnc",
    "DcmDspStartRoutineConfirmationFnc",
    "DcmDspStartRoutineFnc",
    "DcmDspStopRoutineConfirmationFnc",
    "DcmDspStopRoutineFnc",
    "DcmDspSecurityCompareKeyFnc",
    "DcmDspSecurityGetAttemptCounterFnc",
    "DcmDspSecurityGetSeedFnc",
    "DcmDspSecuritySetAttemptCounterFnc",
    "DcmDspVehInfoDataReadFnc",
    "DcmSwcModeRef",
]


class BswEditor:

    def __init__(self):
        self.swc_ports_list = []
        self.idt_dict = {}
        self.system_signal_dict = {}

    @classmethod
    def get_sorted_param_ref_definition(cls, instance_name, module_name, container_def_obj):
        param_definition_dict = {}
        param_definition_list = []
        if hasattr(container_def_obj, "PARAMETERS"):
            param_definition_list += getattr(container_def_obj.PARAMETERS, "ECUC_BOOLEAN_PARAM_DEF", [])
            param_definition_list += getattr(container_def_obj.PARAMETERS, "ECUC_ENUMERATION_PARAM_DEF", [])
            param_definition_list += getattr(container_def_obj.PARAMETERS, "ECUC_FLOAT_PARAM_DEF", [])
            param_definition_list += getattr(container_def_obj.PARAMETERS, "ECUC_FUNCTION_NAME_DEF", [])
            param_definition_list += getattr(container_def_obj.PARAMETERS, "ECUC_INTEGER_PARAM_DEF", [])
            param_definition_list += getattr(container_def_obj.PARAMETERS, "ECUC_STRING_PARAM_DEF", [])
        if hasattr(container_def_obj, "REFERENCES"):
            param_definition_list += getattr(container_def_obj.REFERENCES, "ECUC_CHOICE_REFERENCE_DEF", [])
            param_definition_list += getattr(container_def_obj.REFERENCES, "ECUC_FOREIGN_REFERENCE_DEF", [])
            param_definition_list += getattr(container_def_obj.REFERENCES, "ECUC_INSTANCE_REFERENCE_DEF", [])
            param_definition_list += getattr(container_def_obj.REFERENCES, "ECUC_REFERENCE_DEF", [])
            param_definition_list += getattr(container_def_obj.REFERENCES, "ECUC_SYMBOLIC_NAME_REFERENCE_DEF", [])

        def sort_key(v):
            upper = get_upper_multiplicity(v) or -1
            infinite = get_upper_multiplicity_infinite(v) or -1
            source_line = v.get_source_line()
            return infinite, upper, source_line

        param_definition_list.sort(key=sort_key)
        for param_definition in param_definition_list:
            definition_values = {}
            definition_values["module"] = instance_name
            definition_values["module_name"] = module_name
            definition_values["label_name"] = get_short_name(param_definition)
            definition_values["has_obj"] = None
            definition_values["cfg_value"] = None
            definition_values["num_format"] = None
            definition_values["annotations"] = None
            definition_values["ecuc_path"] = None
            definition_values["unit"] = None
            definition_values["desc"] = get_desc(param_definition)
            definition_values["max_value"] = get_max(param_definition)
            definition_values["min_value"] = get_min(param_definition)
            definition_values["max_length"] = get_max_length(param_definition)
            definition_values["min_length"] = get_min_length(param_definition)
            definition_values["max_interval_type"] = get_max_interval_type(param_definition)
            definition_values["min_interval_type"] = get_min_interval_type(param_definition)
            definition_values["default_value"] = get_default_value(param_definition)
            definition_values["origin"] = get_origin(param_definition)
            ret_value = cls.parse_admin_value(get_admin_data(param_definition))
            format_value = cls.parse_format_from_annotations(get_annotations(param_definition))
            definition_values["is_lock"] = not ret_value["is_enabled"]
            definition_values["annotation_status"] = None
            if (
                ret_value["cfg_value"] is not None
            ):  # 如果MOD中admin_data配置了cfg_value, 那么该配置项的值始终为该cfg_value，默认值也为一样
                definition_values["cfg_value"] = ret_value["cfg_value"]
                definition_values["default_value"] = ret_value["cfg_value"]
            if ret_value["unit"] is not None:
                definition_values["unit"] = ret_value["unit"]
            if format_value:
                definition_values["num_format"] = format_value.get(DEFAULT_FORMAT_FLAG, "dec")
            definition_values["tag"] = param_definition.get_tag()
            if "ECUC-ENUMERATION-PARAM-DEF" == definition_values["tag"]:
                item_list = [""]
                for liternal_def in param_definition.LITERALS.ECUC_ENUMERATION_LITERAL_DEF:
                    item_list.append(get_short_name(liternal_def))
                definition_values["enum_item_list"] = item_list
            definition_values["mod_path"] = param_definition.get_path()
            definition_values["upper_multiplicity"] = get_upper_multiplicity(param_definition)
            definition_values["lower_multiplicity"] = get_lower_multiplicity(param_definition)
            definition_values["upper_multiplicity_infinite"] = get_upper_multiplicity_infinite(param_definition)
            if definition_values["lower_multiplicity"] is None:
                definition_values["is_necessary"] = False
            else:
                if definition_values["lower_multiplicity"] > 0:
                    definition_values["is_necessary"] = True
                else:
                    definition_values["is_necessary"] = False
            param_definition_dict[param_definition.get_path()] = definition_values
        return param_definition_dict

    @classmethod
    def gather_param_ref_val(cls, container_cfg_obj):
        """
        Gather all parameter and refernce val obj from the container val obj

        Returns:
        A dict mapping definition ref path to val obj list
        example:
        {
            "/AUTOSAR/EcucDefs/Os/OsTask/OsMemoryMappingCodeLocationRef": ECUC_REFERENCE_VALUE obj,
            ...
        }
        """
        param_cfg_val_dict = defaultdict(list)
        # param_ref_val_dict = defaultdict(list)

        param_val_list = []
        param_val_list += getattr(container_cfg_obj.PARAMETER_VALUES, "ECUC_NUMERICAL_PARAM_VALUE", [])
        param_val_list += getattr(container_cfg_obj.PARAMETER_VALUES, "ECUC_TEXTUAL_PARAM_VALUE", [])
        for param_val in param_val_list:
            param_values = {}
            # if None == param_values["cfg_value"]:
            param_values["cfg_value"] = get_value(param_val)
            param_values["annotations"] = get_annotations(param_val)
            param_values["ecuc_path"] = param_val.get_path()
            def_path = get_definition_ref(param_val)
            param_cfg_val_dict[def_path].append(param_values)
            # param_cfg_val_dict[def_path] = param_values

        ref_val_list = []
        ref_val_list += getattr(container_cfg_obj.REFERENCE_VALUES, "ECUC_INSTANCE_REFERENCE_VALUE", [])
        ref_val_list += getattr(container_cfg_obj.REFERENCE_VALUES, "ECUC_REFERENCE_VALUE", [])
        for ref_val in ref_val_list:
            ref_values = {}
            if "ECUC-REFERENCE-VALUE" == ref_val.original_tagname_:
                ref_values["cfg_value"] = get_value_ref(ref_val)
            elif "ECUC-INSTANCE-REFERENCE-VALUE" == ref_val.original_tagname_:
                ref_values["cfg_value"] = get_value_iref(ref_val)
            ref_values["annotations"] = get_annotations(ref_val)
            ref_values["ecuc_path"] = ref_val.get_path()
            def_path = get_definition_ref(ref_val)
            param_cfg_val_dict[def_path].append(ref_values)
            # param_cfg_val_dict[def_path] = ref_values

        return param_cfg_val_dict

    @classmethod
    def get_module_definition_obj(cls, module_name, bsw_mod_dict):
        module_definition_obj = None
        if module_name in bsw_mod_dict:
            module_definition_obj = AutosarUtils.get_bswmd_autosar_by_module_name(
                module_name, bsw_mod_dict[module_name]
            )
        else:
            logger.error(f"{module_name} Configuration Parameter Definition not found!")

        return module_definition_obj

    @classmethod
    def get_container_definiton_obj(cls, module_name, container_cfg_obj, bsw_mod_dict):
        container_def_obj = None

        module_definition_obj = cls.get_module_definition_obj(module_name, bsw_mod_dict)
        container_def_path = get_definition_ref(container_cfg_obj)
        if module_definition_obj:
            container_def_obj = module_definition_obj.find(container_def_path)

        return container_def_obj

    @classmethod
    def get_show_data(cls, instance_name, module_name, container_cfg_obj, container_definition_obj):
        """
        module_name:需要获取配置的模块名
        container_cfg_obj:ecuc中container对象;
        container_definition_obj:bswmd中container对象
        """

        not_admin_cfg_value = False
        param_definition_dict = cls.get_sorted_param_ref_definition(
            instance_name, module_name, container_definition_obj
        )  # bswmd信息

        param_cfg_val_dict = cls.gather_param_ref_val(container_cfg_obj)  # ecuc container object

        show_data_dict = defaultdict(list)
        short_name_dict = {}
        short_name_dict["module"] = instance_name
        short_name_dict["module_name"] = module_name
        short_name_dict["label_name"] = "ShortName"
        short_name_dict["cfg_value"] = container_cfg_obj.get_path().split("/")[-1]
        short_name_dict["ecuc_path"] = container_cfg_obj.get_path()
        short_name_dict["tag"] = "SHORT-NAME"
        short_name_dict["num_format"] = None
        short_name_dict["unit"] = None
        short_name_dict["desc"] = get_desc(container_definition_obj)
        short_name_dict["max_value"] = None
        short_name_dict["min_value"] = None
        short_name_dict["max_length"] = None
        short_name_dict["min_length"] = None
        short_name_dict["origin"] = None
        short_name_dict["default_value"] = None
        short_name_dict["mod_path"] = container_definition_obj.get_path()
        short_name_dict["is_lock"] = False
        short_name_dict["annotation_status"] = None
        short_name_dict["is_necessary"] = False
        short_name_dict["lower_multiplicity"] = None
        short_name_dict["upper_multiplicity"] = None
        short_name_dict["upper_multiplicity_infinite"] = None
        short_name_dict["max_interval_type"] = None
        short_name_dict["min_interval_type"] = None

        # container length limit
        admin_data_dict = get_admin_data_all(container_definition_obj)
        if admin_data_dict:
            short_name_dict["min_length"] = admin_data_dict.get("VCOS:StringLength", {}).get("VCOS:MinLength", None)
            short_name_dict["max_length"] = admin_data_dict.get("VCOS:StringLength", {}).get("VCOS:MaxLength", None)
        invisible_flag = False
        # SHORT-NAME是否锁定(置灰)
        if (container_cfg_obj.ANNOTATIONS is not None) and (len(container_cfg_obj.ANNOTATIONS.ANNOTATION) != 0):
            for _ in container_cfg_obj.ANNOTATIONS.ANNOTATION:
                # 此处标记为is_locked仅表示SHORT-NAME不可修改
                if _.ANNOTATION_ORIGIN.valueOf_ == "is_locked":
                    short_name_dict["is_lock"] = True
                # 此处标记为InVisible表示整个container不可修改
                if _.ANNOTATION_ORIGIN.valueOf_ == "InVisible":
                    short_name_dict["is_lock"] = True
                    invisible_flag = True
        show_data_dict[short_name_dict["ecuc_path"]].append(short_name_dict)
        for key, value in param_definition_dict.items():
            # show_data_dict[key].append(value)
            if key in param_cfg_val_dict.keys():
                for i in range(len(param_cfg_val_dict[key])):
                    if param_definition_dict[key]["cfg_value"] is None:
                        not_admin_cfg_value = True
                        param_definition_dict[key]["cfg_value"] = param_cfg_val_dict[key][i]["cfg_value"]
                        if "ECUC-INTEGER-PARAM-DEF" == param_definition_dict[key]["tag"]:
                            ecuc_format_value = cls.get_format_info(param_cfg_val_dict[key][i])
                            if ecuc_format_value:
                                param_definition_dict[key]["num_format"] = ecuc_format_value
                            if param_definition_dict[key]["num_format"] is None:
                                param_definition_dict[key]["num_format"] = cls.get_num_format(
                                    param_definition_dict[key]["cfg_value"]
                                )
                    ret_value_annotation = cls.parse_annotations_value(param_cfg_val_dict[key][i]["annotations"])
                    param_definition_dict[key]["annotation_status"] = ret_value_annotation
                    # if param_definition_dict[key]["annotation_status"] is None:
                    #     param_definition_dict[key]["annotation_status"] = False
                    param_definition_dict[key]["annotations"] = param_cfg_val_dict[key][i]["annotations"]
                    param_definition_dict[key]["ecuc_path"] = param_cfg_val_dict[key][i]["ecuc_path"]
                    param_definition_dict[key]["has_obj"] = True
                    if "ECUC-FUNCTION-NAME-DEF" == param_definition_dict[key]["tag"]:
                        param_definition_dict[key]["default_value"] = cls.derivation_function_name_default_value(
                            param_definition_dict[key], param_cfg_val_dict[key], container_cfg_obj
                        )
                    # 若ecuc的ANNOTATIONS字段有"is_locked",则配置项置灰
                    if (param_cfg_val_dict[key][i]["annotations"] is not None) and (
                        "is_locked" in param_cfg_val_dict[key][i]["annotations"]
                    ):
                        param_definition_dict[key]["is_lock"] = True
                    # 若整个container都被锁定，则其配置项也应被锁定
                    if invisible_flag:
                        param_definition_dict[key]["is_lock"] = True
                    show_data_dict[key].append(deepcopy(param_definition_dict[key]))
                    if not_admin_cfg_value:
                        param_definition_dict[key]["cfg_value"] = None
                        not_admin_cfg_value = False
            else:
                param_definition_dict[key]["ecuc_path"] = container_cfg_obj.get_path()
                show_data_dict[key].append(
                    deepcopy(param_definition_dict[key])
                )  # ecuc中没有该配置项，界面也要有，值为空

        return show_data_dict

    @classmethod
    def derivation_function_name_default_value(cls, param_definition, param_cfg_val, container_cfg_obj):

        if param_definition["label_name"] in PARAM_SUPPORED_BY_DERIVATION_RULE_OF_COM_1:
            return cls.function_name_default_value_derivation_rule_of_com_1(param_definition, container_cfg_obj)

        if param_definition["label_name"] in PARAM_SUPPORED_BY_DERIVATION_RULE_OF_CANSM_1:
            return cls.function_name_default_value_derivation_rule_of_cansm_1(param_definition)

        if param_definition["label_name"] in PARAM_SUPPORED_BY_DERIVATION_RULE_OF_DCM_1:
            return cls.function_name_default_value_derivation_rule_of_dcm_1(param_definition, container_cfg_obj)

    @classmethod
    def function_name_default_value_derivation_rule_of_com_1(cls, param_definition, container_cfg_obj):
        # default_value = function_param_name + "_" + container_name
        return param_definition["label_name"] + "_" + container_cfg_obj.get_path().split("/")[-1]

    @classmethod
    def function_name_default_value_derivation_rule_of_cansm_1(cls, param_definition):
        # default_value = "Appl_CanSM" + param_definition["label_name"]（去除Function）
        return "Appl_CanSM" + "_" + param_definition["label_name"].split("Function")[0]

    @classmethod
    def function_name_default_value_derivation_rule_of_dcm_1(cls, param_definition, container_cfg_obj):
        # default_value = "Dcm_Call" + param_definition["label_name"]（去除Dcm）+ container_name
        return (
            "Appl_CanSM"
            + "_"
            + param_definition["label_name"].split("Dcm")[-1]
            + "_"
            + container_cfg_obj.get_path().split("/")[-1]
        )

    @classmethod
    def parse_admin_value(cls, admin_value):

        ret_value_dict = {"is_enabled": True, "cfg_value": None, "unit": None, "num_format": None}
        is_enabled = True
        if admin_value is not None:
            for i in range(len(admin_value)):
                if "VCOS:CfgLock" in admin_value[i].keys():
                    if "false" == admin_value[i]["VCOS:CfgLock"]:
                        is_enabled = True
                    elif "true" == admin_value[i]["VCOS:CfgLock"]:
                        is_enabled = False
                    ret_value_dict["is_enabled"] = is_enabled
                elif "VCOS:CfgValue" in admin_value[i].keys():
                    ret_value_dict["cfg_value"] = admin_value[i]["VCOS:CfgValue"]
                elif "VCOS:DefaultFormat" in admin_value[i].keys():
                    ret_value_dict["num_format"] = admin_value[i]["VCOS:DefaultFormat"]
                elif "VCOS:BaseUnit" in admin_value[i].keys():
                    ret_value_dict["unit"] = " [" + admin_value[i]["VCOS:BaseUnit"] + "]"
                elif "VCOS:Unit" in admin_value[i].keys():
                    ret_value_dict["unit"] = " [" + admin_value[i]["VCOS:Unit"] + "]"
                    break

        return ret_value_dict

    @classmethod
    def parse_annotations_value(cls, annotations_value):

        ret_value = None
        if annotations_value:
            if USER_DEFINED_FLAG in annotations_value:
                ret_value = True
            else:
                if "AutoDerived" in annotations_value:
                    ret_value = False

        return ret_value

    @classmethod
    def get_format_info(cls, param_cfg_val_dict):
        ret_value = None
        annotation_objs = param_cfg_val_dict.get("annotations", None)
        if annotation_objs is None:
            return ret_value
        for item in annotation_objs:
            item_list = item.split(":")
            if len(item_list) <= 1:
                continue
            if item_list[0] == "DefaultFormat":
                ret_value = item_list[1]
                break
        return ret_value

    @classmethod
    def parse_format_from_annotations(cls, annotations):

        def get_default_format(format_origin):
            cfg: list = format_origin.split(":")
            format_value: str = "dec"
            if len(cfg) > 1:
                format_value = "dec" if cfg[1] not in ["bin", "oct", "dec", "hex"] else cfg[1]
            return format_value

        if not annotations:
            return {}

        ret_value = {DEFAULT_FORMAT_FLAG: "dec"}
        for item in annotations:
            if DEFAULT_FORMAT_FLAG in item:
                ret_value.update({DEFAULT_FORMAT_FLAG: get_default_format(item)})
                break
        return ret_value

    @classmethod
    def get_num_format(cls, value_str):

        num_format = "dec"
        if value_str is not None:
            if value_str.startswith("0x"):
                num_format = "hex"
            elif value_str.startswith("0o"):
                num_format = "oct"
            elif value_str.startswith("0b"):
                num_format = "bin"
            else:
                num_format = "dec"

        return num_format

    @classmethod
    def get_all_internal_ref_targets(cls, mod_path, module_name, bsw_ecuc_dict, bsw_mod_dict):
        module_definition_obj = cls.get_module_definition_obj(module_name, bsw_mod_dict)
        cls.references_target_dict = {"<None>": "<empty>"}
        if module_definition_obj:
            cls.get_internal_reference_target(bsw_ecuc_dict, module_definition_obj.find(mod_path))
        return cls.references_target_dict

    @classmethod
    def get_all_foreign_ref_targets(
        cls,
        mod_path,
        module_name,
        bsw_mod_dict,
        bsw_ecuc_dict,
        autosar_asw_class,
        autosar_system_class,
        autosar_ib_class,
    ):

        module_definition_obj = cls.get_module_definition_obj(module_name, bsw_mod_dict)
        foreign_references_target_dict = {"<None>": "<empty>"}
        if module_definition_obj:
            foreign_references_target_dict = cls.get_foreign_reference_target(
                module_definition_obj.find(mod_path),
                bsw_ecuc_dict,
                autosar_asw_class,
                autosar_system_class,
                autosar_ib_class,
            )
        return foreign_references_target_dict

    @classmethod
    def get_foreign_reference_target(
        cls, reference_param_def, bsw_ecuc_dict, autosar_asw_class, autosar_system_class, autosar_ib_class
    ):

        search_object_list = []
        foreign_references_target_dict = {"<None>": "<empty>"}
        destination_type = get_destination_type(reference_param_def)

        if "I-SIGNAL-TO-I-PDU-MAPPING" == destination_type:
            search_object_list = []
            if "Communication" in autosar_system_class.keys():
                search_object_list.append(autosar_system_class["Communication"])
            search_destination_type = "I_SIGNAL_I_PDU"
            cls.get_foreign_reference_target_by_ref_type(
                search_object_list, search_destination_type, foreign_references_target_dict
            )
        elif "BSW-EVENT" == destination_type:
            search_internal_behavior_object_list = []
            for internal_behavior_name, internal_behavior_object in autosar_ib_class.items():
                search_internal_behavior_object_list.append(autosar_ib_class[internal_behavior_name])
            cls.get_foreign_reference_target_by_ref_type_bsw_event(
                search_internal_behavior_object_list, foreign_references_target_dict
            )
        elif (
            "SW-ADDR-METHOD" == destination_type
            or "EXCLUSIVE-AREA" == destination_type
            or "BSW-MODULE-ENTRY" == destination_type
        ):
            search_internal_behavior_object_list = []
            for internal_behavior_name, internal_behavior_object in autosar_ib_class.items():
                search_internal_behavior_object_list.append(autosar_ib_class[internal_behavior_name])
            search_internal_behavior_object_list.append(autosar_asw_class)
            cls.get_foreign_reference_target_by_ref_type_ib(
                search_internal_behavior_object_list, destination_type, foreign_references_target_dict
            )
        elif "SW-COMPONENT-PROTOTYPE" == destination_type:
            search_object_list = []
            if autosar_asw_class:
                search_object_list.append(autosar_asw_class)
            cls.get_foreign_reference_target_by_ref_type_ib(
                search_object_list, destination_type, foreign_references_target_dict
            )
        elif "SW-COMPONENT-TYPE" == destination_type:
            search_object_list = []
            if autosar_asw_class:
                search_object_list.append(autosar_asw_class)
            cls.get_foreign_reference_target_by_ref_type_ib(
                search_object_list, "APPLICATION-SW-COMPONENT-TYPE", foreign_references_target_dict
            )
            cls.get_foreign_reference_target_by_ref_type_ib(
                search_object_list, "SERVICE-SW-COMPONENT-TYPE", foreign_references_target_dict
            )
        elif (
            "COMPU-METHOD" == destination_type
            or "MODE-DECLARATION" == destination_type
            or "DATA-TYPE-MAPPING-SET" == destination_type
            or "MODE-SWITCH-INTERFACE" == destination_type
            or "MODE-DECLARATION-GROUP" == destination_type
        ):
            search_object_list = []
            if autosar_asw_class:
                search_object_list.append(autosar_asw_class)
            cls.get_foreign_reference_target_by_ref_type_ib(
                search_object_list, destination_type, foreign_references_target_dict
            )
        elif "VARIABLE-DATA-PROTOTYPE" == destination_type or "VARIABLE-ACCESS" == destination_type:
            search_object_list = []
            if autosar_asw_class:
                search_object_list.append(autosar_asw_class)
            cls.get_foreign_reference_target_by_ref_type_ib(
                search_object_list, destination_type, foreign_references_target_dict
            )
        elif (
            "SWC-IMPLEMENTATION" == destination_type
            or "ARGUMENT-DATA-PROTOTYPE" == destination_type
            or "IMPLEMENTATION-DATA-TYPE" == destination_type
        ):
            search_object_list = []
            if autosar_asw_class:
                search_object_list.append(autosar_asw_class)
            cls.get_foreign_reference_target_by_ref_type_ib(
                search_object_list, destination_type, foreign_references_target_dict
            )
        elif "MODE-DECLARATION-GROUP-PROTOTYPE" == destination_type:
            search_object_list = []
            if autosar_asw_class:
                search_object_list.append(autosar_asw_class)
                destination_type = "MODE-GROUP"
            cls.get_foreign_reference_target_by_ref_type_ib(
                search_object_list, destination_type, foreign_references_target_dict
            )
        elif "RTE-EVENT" == destination_type:
            cls.get_foreign_reference_target_by_ref_type_rte_event([autosar_asw_class], foreign_references_target_dict)
        else:
            search_object_list = []
            if autosar_asw_class:
                search_object_list.append(autosar_asw_class)
            if "Communication" in autosar_system_class.keys():
                search_object_list.append(autosar_system_class["Communication"])
            if "FlatExtract" in autosar_system_class.keys():
                search_object_list.append(autosar_system_class["FlatExtract"])
            for bsw_module_name, bsw_module_object in bsw_ecuc_dict.items():
                search_object_list.append(bsw_ecuc_dict[bsw_module_name])
            for internal_behavior_name, internal_behavior_object in autosar_ib_class.items():
                search_object_list.append(autosar_ib_class[internal_behavior_name])
            cls.get_foreign_reference_target_by_ref_type_ib(
                search_object_list, destination_type, foreign_references_target_dict
            )

        return foreign_references_target_dict

    @classmethod
    def get_foreign_reference_target_i_signal_to_i_pdu_mapping(cls, pdu_list, foreign_references_target_dict):

        for i in range(len(pdu_list)):
            if hasattr(pdu_list[i], "I_SIGNAL_TO_PDU_MAPPINGS"):
                i_signal_to_i_pdu_mappings = getattr(pdu_list[i], "I_SIGNAL_TO_PDU_MAPPINGS", None)
                for j in range(len(i_signal_to_i_pdu_mappings.I_SIGNAL_TO_I_PDU_MAPPING)):
                    signal_name = i_signal_to_i_pdu_mappings.I_SIGNAL_TO_I_PDU_MAPPING[j].SHORT_NAME.valueOf_
                    foreign_references_target_dict[
                        i_signal_to_i_pdu_mappings.I_SIGNAL_TO_I_PDU_MAPPING[j].get_path()
                    ] = signal_name

    @classmethod
    def get_foreign_reference_target_by_ref_type_ib(
        cls, all_to_be_found_object_list, destination_type, foreign_references_target_dict
    ):
        matched_object = []
        for k in range(len(all_to_be_found_object_list)):
            ar_packages_object = all_to_be_found_object_list[k]
            if ar_packages_object is not None:
                ib_exclusive_area = ar_packages_object.find_nodes(destination_type)
                if ib_exclusive_area:
                    matched_object.append(ib_exclusive_area)

        for i in range(len(matched_object)):
            for j in range(len(matched_object[i])):
                short_name = matched_object[i][j].SHORT_NAME.valueOf_
                foreign_references_target_dict[matched_object[i][j].get_path()] = short_name

    @classmethod
    def get_foreign_reference_target_by_ref_type_bsw_event(
        cls, search_internal_behavior_object_list, foreign_references_target_dict
    ):

        all_module_ib_bsw_event = []
        for k in range(len(search_internal_behavior_object_list)):
            ar_packages_object = search_internal_behavior_object_list[k]
            if ar_packages_object is not None:
                ib_bsw_event = ar_packages_object.find_nodes("EVENTS")
                if ib_bsw_event:
                    all_module_ib_bsw_event.append(ib_bsw_event)

        for i in range(len(all_module_ib_bsw_event)):
            if all_module_ib_bsw_event[i][0].BSW_ASYNCHRONOUS_SERVER_CALL_RETURNS_EVENT:
                for j in range(len(all_module_ib_bsw_event[i][0].BSW_ASYNCHRONOUS_SERVER_CALL_RETURNS_EVENT)):
                    short_name = (
                        all_module_ib_bsw_event[i][0].BSW_ASYNCHRONOUS_SERVER_CALL_RETURNS_EVENT[j].SHORT_NAME.valueOf_
                    )
                    foreign_references_target_dict[
                        all_module_ib_bsw_event[i][0].BSW_ASYNCHRONOUS_SERVER_CALL_RETURNS_EVENT[j].get_path()
                    ] = short_name
            if all_module_ib_bsw_event[i][0].BSW_BACKGROUND_EVENT:
                for j in range(len(all_module_ib_bsw_event[i][0].BSW_BACKGROUND_EVENT)):
                    short_name = all_module_ib_bsw_event[i][0].BSW_BACKGROUND_EVENT[j].SHORT_NAME.valueOf_
                    foreign_references_target_dict[all_module_ib_bsw_event[i][0].BSW_BACKGROUND_EVENT[j].get_path()] = (
                        short_name
                    )
            if all_module_ib_bsw_event[i][0].BSW_DATA_RECEIVED_EVENT:
                for j in range(len(all_module_ib_bsw_event[i][0].BSW_DATA_RECEIVED_EVENT)):
                    short_name = all_module_ib_bsw_event[i][0].BSW_DATA_RECEIVED_EVENT[j].SHORT_NAME.valueOf_
                    foreign_references_target_dict[
                        all_module_ib_bsw_event[i][0].BSW_DATA_RECEIVED_EVENT[j].get_path()
                    ] = short_name
            if all_module_ib_bsw_event[i][0].BSW_EXTERNAL_TRIGGER_OCCURRED_EVENT:
                for j in range(len(all_module_ib_bsw_event[i][0].BSW_EXTERNAL_TRIGGER_OCCURRED_EVENT)):
                    short_name = (
                        all_module_ib_bsw_event[i][0].BSW_EXTERNAL_TRIGGER_OCCURRED_EVENT[j].SHORT_NAME.valueOf_
                    )
                    foreign_references_target_dict[
                        all_module_ib_bsw_event[i][0].BSW_EXTERNAL_TRIGGER_OCCURRED_EVENT[j].get_path()
                    ] = short_name
            if all_module_ib_bsw_event[i][0].BSW_INTERNAL_TRIGGER_OCCURRED_EVENT:
                for j in range(len(all_module_ib_bsw_event[i][0].BSW_INTERNAL_TRIGGER_OCCURRED_EVENT)):
                    short_name = (
                        all_module_ib_bsw_event[i][0].BSW_INTERNAL_TRIGGER_OCCURRED_EVENT[j].SHORT_NAME.valueOf_
                    )
                    foreign_references_target_dict[
                        all_module_ib_bsw_event[i][0].BSW_INTERNAL_TRIGGER_OCCURRED_EVENT[j].get_path()
                    ] = short_name
            if all_module_ib_bsw_event[i][0].BSW_MODE_MANAGER_ERROR_EVENT:
                for j in range(len(all_module_ib_bsw_event[i][0].BSW_MODE_MANAGER_ERROR_EVENT)):
                    short_name = all_module_ib_bsw_event[i][0].BSW_MODE_MANAGER_ERROR_EVENT[j].SHORT_NAME.valueOf_
                    foreign_references_target_dict[
                        all_module_ib_bsw_event[i][0].BSW_MODE_MANAGER_ERROR_EVENT[j].get_path()
                    ] = short_name
            if all_module_ib_bsw_event[i][0].BSW_MODE_SWITCHED_ACK_EVENT:
                for j in range(len(all_module_ib_bsw_event[i][0].BSW_MODE_SWITCHED_ACK_EVENT)):
                    short_name = all_module_ib_bsw_event[i][0].BSW_MODE_SWITCHED_ACK_EVENT[j].SHORT_NAME.valueOf_
                    foreign_references_target_dict[
                        all_module_ib_bsw_event[i][0].BSW_MODE_SWITCHED_ACK_EVENT[j].get_path()
                    ] = short_name
            if all_module_ib_bsw_event[i][0].BSW_MODE_SWITCH_EVENT:
                for j in range(len(all_module_ib_bsw_event[i][0].BSW_MODE_SWITCH_EVENT)):
                    short_name = all_module_ib_bsw_event[i][0].BSW_MODE_SWITCH_EVENT[j].SHORT_NAME.valueOf_
                    foreign_references_target_dict[
                        all_module_ib_bsw_event[i][0].BSW_MODE_SWITCH_EVENT[j].get_path()
                    ] = short_name
            if all_module_ib_bsw_event[i][0].BSW_OPERATION_INVOKED_EVENT:
                for j in range(len(all_module_ib_bsw_event[i][0].BSW_OPERATION_INVOKED_EVENT)):
                    short_name = all_module_ib_bsw_event[i][0].BSW_OPERATION_INVOKED_EVENT[j].SHORT_NAME.valueOf_
                    foreign_references_target_dict[
                        all_module_ib_bsw_event[i][0].BSW_OPERATION_INVOKED_EVENT[j].get_path()
                    ] = short_name
            if all_module_ib_bsw_event[i][0].BSW_TIMING_EVENT:
                for j in range(len(all_module_ib_bsw_event[i][0].BSW_TIMING_EVENT)):
                    short_name = all_module_ib_bsw_event[i][0].BSW_TIMING_EVENT[j].SHORT_NAME.valueOf_
                    foreign_references_target_dict[all_module_ib_bsw_event[i][0].BSW_TIMING_EVENT[j].get_path()] = (
                        short_name
                    )

    @classmethod
    def get_foreign_reference_target_by_ref_type_rte_event(
        cls, search_internal_behavior_object_list, foreign_references_target_dict
    ):

        rte_event_type_list = [
            "ASYNCHRONOUS_SERVER_CALL_RETURNS_EVENT",
            "BACKGROUND_EVENT",
            "DATA_RECEIVE_ERROR_EVENT",
            "DATA_RECEIVED_EVENT",
            "DATA_SEND_COMPLETED_EVENT",
            "DATA_WRITE_COMPLETED_EVENT",
            "EXTERNAL_TRIGGER_OCCURRED_EVENT",
            "INIT_EVENT",
            "INTERNAL_TRIGGER_OCCURRED_EVENT",
            "MODE_SWITCHED_ACK_EVENT",
            "OPERATION_INVOKED_EVENT",
            "SWC_MODE_MANAGER_ERROR_EVENT",
            "SWC_MODE_SWITCH_EVENT",
            "TIMING_EVENT",
            "TRANSFORMER_HARD_ERROR_EVENT",
        ]

        all_module_ib_rte_event = []
        for ar_packages_object in search_internal_behavior_object_list:
            if ar_packages_object is None:
                continue
            ib_rte_event = ar_packages_object.find_nodes("EVENTS")
            if ib_rte_event:
                all_module_ib_rte_event.append(ib_rte_event)

        for ib_event_objs in all_module_ib_rte_event:
            for ib_event_obj in ib_event_objs:
                for rte_event_type in rte_event_type_list:
                    for target_event_obj in getattr(ib_event_obj, rte_event_type, []):
                        foreign_references_target_dict[target_event_obj.get_path()] = get_short_name(target_event_obj)

    @classmethod
    def get_foreign_reference_target_by_ref_type(
        cls, search_object_list, search_destination_type, foreign_references_target_dict
    ):

        for k in range(len(search_object_list)):
            ar_packages_object = search_object_list[k]
            cls.traversal_ar_packages(ar_packages_object, search_destination_type, foreign_references_target_dict)

    @classmethod
    def traversal_ar_packages(cls, ar_packages_object, destination_type, foreign_references_target_dict):

        if hasattr(ar_packages_object, "AR_PACKAGES"):
            if hasattr(ar_packages_object.AR_PACKAGES, "AR_PACKAGE"):
                for i in range(len(ar_packages_object.AR_PACKAGES.AR_PACKAGE)):
                    if hasattr(ar_packages_object.AR_PACKAGES.AR_PACKAGE[i], "ELEMENTS"):
                        object_to_be_matched = ar_packages_object.AR_PACKAGES.AR_PACKAGE[i].ELEMENTS
                        if object_to_be_matched:
                            cls.get_foreign_reference_target_elements(
                                destination_type, object_to_be_matched, foreign_references_target_dict
                            )
                    if hasattr(ar_packages_object.AR_PACKAGES.AR_PACKAGE[i], "AR_PACKAGES"):
                        cls.traversal_ar_packages(
                            ar_packages_object.AR_PACKAGES.AR_PACKAGE[i],
                            destination_type,
                            foreign_references_target_dict,
                        )

    @classmethod
    def get_foreign_reference_target_elements(
        cls, destination_type, object_to_be_matched_element, foreign_references_target_dict
    ):

        if hasattr(object_to_be_matched_element, destination_type):
            matched_object = getattr(object_to_be_matched_element, destination_type, None)
            if matched_object:
                if "I_SIGNAL_I_PDU" == destination_type:
                    cls.get_foreign_reference_target_i_signal_to_i_pdu_mapping(
                        matched_object, foreign_references_target_dict
                    )
                else:
                    for i in range(len(matched_object)):
                        short_name = matched_object[i].SHORT_NAME.valueOf_
                        foreign_references_target_dict[matched_object[i].get_path()] = short_name

    @classmethod
    def get_internal_reference_target(cls, bsw_ecuc_dict, reference_param_def):

        destination_refs_list = []
        destination_ref = get_destination_ref(reference_param_def)  # normal
        if destination_ref:
            destination_refs_list.append(destination_ref)
        destination_refs = get_destination_refs(reference_param_def)  # choise
        if destination_refs:
            for i in range(len(destination_refs)):
                destination_refs_list.append(destination_refs[i])
        instance_name_dict = {}
        for instance_name, ecuc_obj in bsw_ecuc_dict.items():
            def_ref = get_definition_ref(ecuc_obj.find_nodes("ECUC-MODULE-CONFIGURATION-VALUES")[-1]) or ""
            module_name = def_ref.split("/").pop()
            instance_name_dict.setdefault(module_name, []).append(instance_name)
        cls.references_target_dict = {"<None>": "<empty>"}
        for destination_ref in destination_refs_list:
            dest_module_name: str = destination_ref.split("/")[3]
            for module_name, instance_name_list in instance_name_dict.items():
                if not module_name.startswith(dest_module_name):
                    continue
                for instance_name in instance_name_list:
                    cls.get_reference_target_by_dest_ref(
                        bsw_ecuc_dict, destination_ref, dest_module_name, instance_name
                    )

    @classmethod
    def get_reference_target_by_dest_ref(cls, bsw_ecuc_dict, dest_ref, module_name, instance_name):
        """
        The CanIf module gets the reference target handler, which serves as the
        entry point for distinguishing all Refs configuration items in the CanIf module

        Arg:
            dest_ref : This is used as an identifier to distinguish Refs configuration items
            references_target_dict : Stores the obtained reference target
        """
        if instance_name not in bsw_ecuc_dict:
            return
        reference_object = bsw_ecuc_dict[instance_name].find(f"/ActiveEcuC/{instance_name}")
        module_def_ref = get_definition_ref(reference_object) or ""
        containers = [(0, v) for v in getattr(getattr(reference_object, "CONTAINERS", ""), "ECUC_CONTAINER_VALUE", [])]
        find_def_ref = dest_ref.split(f"/{module_name}/")[-1]
        find_def_ref_list = find_def_ref.split("/")
        module_def_name = module_def_ref.split("/")[-1]
        while containers:
            i, container = containers.pop()
            def_ref = get_definition_ref(container) or ""
            def_ref = def_ref.split(f"/{module_def_name}/")[-1]
            def_ref_list = def_ref.split("/")
            if def_ref_list == find_def_ref_list:
                short_name = get_short_name(container)
                cls.references_target_dict[container.get_path()] = short_name
            elif def_ref_list[i] == find_def_ref_list[i]:
                i += 1
                containers.extend(
                    ((i, v) for v in getattr(getattr(container, "SUB_CONTAINERS", ""), "ECUC_CONTAINER_VALUE", []))
                )

    @classmethod
    def set_new_value_to_ecuc_arxml(cls, bsw_ecuc_dict, new_value, per_value, mod_path, module, ecuc_path, tag, index):

        container_cfg_obj = bsw_ecuc_dict[module].find(ecuc_path)
        if tag in ECUC_REFERENCE_VALUE_LIST:
            for i, param_obj in enumerate(container_cfg_obj.REFERENCE_VALUES.ECUC_REFERENCE_VALUE):
                if mod_path == get_definition_ref(param_obj) and ((per_value == get_value_ref(param_obj))):
                    if (index is not None) and (i != index):
                        continue
                    set_value_ref(param_obj, new_value)
                    return
        elif tag in ECUC_NUMERICAL_PARAM_VALUE_LIST:
            for i, param_obj in enumerate(container_cfg_obj.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE):
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == "") or (per_value == get_value(param_obj))
                ):
                    if (index is not None) and (i != index):
                        continue
                    set_value(param_obj, new_value)
                    return
        elif tag in ECUC_TEXTUAL_PARAM_VALUE_LIST:
            for i, param_obj in enumerate(container_cfg_obj.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE):
                if mod_path == get_definition_ref(param_obj) and ((per_value == get_value(param_obj))):
                    if (index is not None) and (i != index):
                        continue
                    set_value(param_obj, new_value)
                    return
        elif tag in ECUC_IREFERENCE_VALUE_LIST:
            for i, param_obj in enumerate(container_cfg_obj.REFERENCE_VALUES.ECUC_INSTANCE_REFERENCE_VALUE):
                if mod_path == get_definition_ref(param_obj) and ((per_value == get_value_iref(param_obj))):
                    if (index is not None) and (i != index):
                        continue
                    set_value_iref(param_obj, new_value)
                    return
        elif tag in ("ECUC-PARAM-CONF-CONTAINER-DEF", "ECUC-CHOICE-CONTAINER-DEF"):
            set_short_name(container_cfg_obj, new_value)

    @classmethod
    def update_container_short_name_to_ecuc_arxml(
        cls, bsw_ecuc_dict, new_value, per_value, mod_path, module, ecuc_path, tag
    ):
        i = 1
        short_name = new_value
        while bsw_ecuc_dict[module].find(ecuc_path.split(per_value)[0] + short_name):
            short_name = f"{new_value}_{i}"
            i += 1
        container_cfg_obj = bsw_ecuc_dict[module].find(ecuc_path)
        set_short_name(container_cfg_obj, short_name)
        return short_name

    @classmethod
    def update_all_configuration_items_that_reference_this_ref_to_ecuc_arxml(
        cls, bsw_ecuc_dict, new_value, per_value, mod_path, module, ecuc_path, tag
    ):

        AutosarUtils.get_all_ref_configuration_items_by_ref_target(bsw_ecuc_dict, per_value, new_value)

    @classmethod
    def remove_param_item_and_write_to_ecuc_arxml(
        cls, bsw_ecuc_dict, bsw_mod_dict, per_value, mod_path, module_name, ecuc_path, tag, index
    ):
        container_cfg_obj = bsw_ecuc_dict[module_name].find(ecuc_path)

        if tag in ECUC_REFERENCE_VALUE_LIST:
            for param_obj in container_cfg_obj.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == get_value_ref(param_obj))
                ):
                    tag = param_obj.get_tag()
                    if index is not None:
                        del getattr(container_cfg_obj.REFERENCE_VALUES, tag.replace("-", "_"))[index]
                        return
                    getattr(container_cfg_obj.REFERENCE_VALUES, tag.replace("-", "_")).remove(param_obj)
                    return
        if tag in ECUC_IREFERENCE_VALUE_LIST:
            for param_obj in container_cfg_obj.REFERENCE_VALUES.ECUC_INSTANCE_REFERENCE_VALUE:
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == get_value_iref(param_obj))
                ):
                    tag = param_obj.get_tag()
                    if index is not None:
                        del getattr(container_cfg_obj.REFERENCE_VALUES, tag.replace("-", "_"))[index]
                        return
                    getattr(container_cfg_obj.REFERENCE_VALUES, tag.replace("-", "_")).remove(param_obj)
                    return
        elif tag in ECUC_NUMERICAL_PARAM_VALUE_LIST:
            for param_obj in container_cfg_obj.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == get_value(param_obj))
                ):
                    tag = param_obj.get_tag()
                    if index is not None:
                        del getattr(container_cfg_obj.PARAMETER_VALUES, tag.replace("-", "_"))[index]
                        return
                    getattr(container_cfg_obj.PARAMETER_VALUES, tag.replace("-", "_")).remove(param_obj)
                    return
        elif tag in ECUC_TEXTUAL_PARAM_VALUE_LIST:
            for param_obj in container_cfg_obj.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE:
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == get_value(param_obj))
                ):
                    tag = param_obj.get_tag()
                    if index is not None:
                        del getattr(container_cfg_obj.PARAMETER_VALUES, tag.replace("-", "_"))[index]
                        return
                    getattr(container_cfg_obj.PARAMETER_VALUES, tag.replace("-", "_")).remove(param_obj)
                    return

    @classmethod
    def add_param_item_and_write_to_ecuc_arxml(
        cls,
        bsw_ecuc_dict,
        bsw_mod_dict,
        new_value,
        mod_path,
        module_name,
        ecuc_path,
        tag,
        index=None,
        instance_name=None,
    ):
        instance_name = instance_name or module_name
        container_cfg_obj = bsw_ecuc_dict[instance_name].find(ecuc_path)

        if tag in ECUC_REFERENCE_VALUE_LIST:
            parent_param_obj = container_cfg_obj.REFERENCE_VALUES
            if parent_param_obj is None:
                AutosarUtil.add_reference_values(
                    cls.get_module_definition_obj(module_name, bsw_mod_dict).find(mod_path).get_parent().get_parent(),
                    container_cfg_obj,
                )
                parent_param_obj = container_cfg_obj.REFERENCE_VALUES
                cls.set_new_value_to_ecuc_arxml(bsw_ecuc_dict, new_value, None, mod_path, module_name, ecuc_path, tag)
                return
            param_ref_obj = AutosarUtil.set_reference(
                parent_param_obj, cls.get_module_definition_obj(module_name, bsw_mod_dict).find(mod_path)
            )

            # 撤销时index不是None,需要调整内存里item顺序
            if index is not None:
                cls.set_list_order(tag, mod_path, parent_param_obj, index)

            set_value_ref(param_ref_obj, new_value)
            return
        if tag in ECUC_IREFERENCE_VALUE_LIST:
            parent_param_obj = container_cfg_obj.REFERENCE_VALUES
            param_ref_obj = AutosarUtil.set_reference(
                parent_param_obj, cls.get_module_definition_obj(module_name, bsw_mod_dict).find(mod_path)
            )

            if index is not None:
                cls.set_list_order(tag, mod_path, parent_param_obj, index)

            set_value_iref(param_ref_obj, new_value)
            return
        elif tag in ECUC_PARAM_VALUE_LIST:
            parent_param_obj = container_cfg_obj.PARAMETER_VALUES
            param_ref_obj = AutosarUtil.set_parameter(
                parent_param_obj, cls.get_module_definition_obj(module_name, bsw_mod_dict).find(mod_path)
            )

            if index is not None:
                cls.set_list_order(tag, mod_path, parent_param_obj, index)

            set_value(param_ref_obj, new_value)
            return

    @classmethod
    def set_list_order(cls, tag, mod_path, parent_param_obj, index):
        """将内存里list控件的最后一个item设置到指定索引处"""

        ecuc_list = None
        if tag in ["ECUC-STRING-PARAM-DEF", "ECUC-FUNCTION-NAME-DEF"]:
            ecuc_list = parent_param_obj.ECUC_TEXTUAL_PARAM_VALUE
        elif tag in [
            "ECUC-REFERENCE-DEF",
            "ECUC-SYMBOLIC-NAME-REFERENCE-DEF",
            "ECUC-CHOICE-REFERENCE-DEF",
            "ECUC-FOREIGN-REFERENCE-DEF",
        ]:
            ecuc_list = parent_param_obj.ECUC_REFERENCE_VALUE
        elif tag in ["ECUC-INSTANCE-REFERENCE-DEF"]:
            ecuc_list = parent_param_obj.ECUC_INSTANCE_REFERENCE_VALUE
        else:
            print(f"ERROR: not adapted to this tag:{tag},check your code.")
            return

        item_list = []
        last_item = None
        for i, item in enumerate(ecuc_list):
            if get_definition_ref(item) == mod_path:
                item_list.append(item)
                last_item = item
                ecuc_list[i] = None
        del item_list[-1]
        item_list.insert(index, last_item)
        item_list_idx = 0
        for i, item in enumerate(ecuc_list):
            if item is None:
                ecuc_list[i] = item_list[item_list_idx]
                item_list_idx += 1
        if item_list_idx != len(item_list):
            print("ERROR: list content does not correspond")

    @classmethod
    def set_user_defined(cls, bsw_ecuc_dict, per_value, mod_path, module, ecuc_path, tag):

        container_cfg_obj = bsw_ecuc_dict[module].find(ecuc_path)
        if tag in ECUC_REFERENCE_VALUE_LIST:
            for param_obj in container_cfg_obj.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == get_value_ref(param_obj))
                ):
                    AutosarUtil.add_annotation_value(param_obj, USER_DEFINED_FLAG)
                    return True
        elif tag in ECUC_NUMERICAL_PARAM_VALUE_LIST:
            for param_obj in container_cfg_obj.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == get_value(param_obj))
                ):
                    AutosarUtil.add_annotation_value(param_obj, USER_DEFINED_FLAG)
                    return True
        elif tag in ECUC_TEXTUAL_PARAM_VALUE_LIST:
            for param_obj in container_cfg_obj.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE:
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == get_value(param_obj))
                ):
                    AutosarUtil.add_annotation_value(param_obj, USER_DEFINED_FLAG)
                    return True

    @classmethod
    def remove_user_defined(cls, bsw_ecuc_dict, per_value, mod_path, module, ecuc_path, tag):

        container_cfg_obj = bsw_ecuc_dict[module].find(ecuc_path)
        if tag in ECUC_REFERENCE_VALUE_LIST:
            for param_obj in container_cfg_obj.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == get_value_ref(param_obj))
                ):
                    AutosarUtil.remove_annotation_value(param_obj, USER_DEFINED_FLAG)
                    return False
        elif tag in ECUC_NUMERICAL_PARAM_VALUE_LIST:
            for param_obj in container_cfg_obj.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == get_value(param_obj))
                ):
                    AutosarUtil.remove_annotation_value(param_obj, USER_DEFINED_FLAG)
                    return False
        elif tag in ECUC_TEXTUAL_PARAM_VALUE_LIST:
            for param_obj in container_cfg_obj.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE:
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == get_value(param_obj))
                ):
                    AutosarUtil.remove_annotation_value(param_obj, USER_DEFINED_FLAG)
                    return False

    @classmethod
    def set_is_lock(cls, bsw_ecuc_dict, per_value, mod_path, module, ecuc_path, tag):
        IS_LOCK_FLAG = "is_locked"
        container_cfg_obj = bsw_ecuc_dict[module].find(ecuc_path)
        if tag in ECUC_REFERENCE_VALUE_LIST:
            for param_obj in container_cfg_obj.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == get_value_ref(param_obj))
                ):
                    AutosarUtil.add_annotation_value(param_obj, IS_LOCK_FLAG)
                    return True
        elif tag in ECUC_NUMERICAL_PARAM_VALUE_LIST:
            for param_obj in container_cfg_obj.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == get_value(param_obj))
                ):
                    AutosarUtil.add_annotation_value(param_obj, IS_LOCK_FLAG)
                    return True
        elif tag in ECUC_TEXTUAL_PARAM_VALUE_LIST:
            for param_obj in container_cfg_obj.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE:
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == get_value(param_obj))
                ):
                    AutosarUtil.add_annotation_value(param_obj, IS_LOCK_FLAG)
                    return True
        elif tag == "SHORT-NAME":
            param_obj = container_cfg_obj
            AutosarUtil.add_annotation_value(param_obj, IS_LOCK_FLAG)
            return True

    @classmethod
    def remove_is_lock(cls, bsw_ecuc_dict, per_value, mod_path, module, ecuc_path, tag):
        IS_LOCK_FLAG = "is_locked"
        container_cfg_obj = bsw_ecuc_dict[module].find(ecuc_path)
        if tag in ECUC_REFERENCE_VALUE_LIST:
            for param_obj in container_cfg_obj.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == get_value_ref(param_obj))
                ):
                    AutosarUtil.remove_annotation_value(param_obj, IS_LOCK_FLAG)
                    return False
        elif tag in ECUC_NUMERICAL_PARAM_VALUE_LIST:
            for param_obj in container_cfg_obj.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == get_value(param_obj))
                ):
                    AutosarUtil.remove_annotation_value(param_obj, IS_LOCK_FLAG)
                    return False
        elif tag in ECUC_TEXTUAL_PARAM_VALUE_LIST:
            for param_obj in container_cfg_obj.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE:
                if mod_path == get_definition_ref(param_obj) and (
                    (per_value is None) or (per_value == get_value(param_obj))
                ):
                    AutosarUtil.remove_annotation_value(param_obj, IS_LOCK_FLAG)
                    return False
        elif tag == "SHORT-NAME":
            param_obj = container_cfg_obj
            AutosarUtil.remove_annotation_value(param_obj, IS_LOCK_FLAG)
            return False

    @classmethod
    def set_integer_format(cls, bsw_ecuc_dict, module, mod_path, ecuc_path, cfg_value, tag, num_format):
        """set format info into annotation
        module:bsw模块
        mod_path:parameter所在的mode文件位置
        ecuc_path:参数在arxml中的position
        cfg_value:当前parameter的值
        tag:参数标签ECUC-INTEGER-PARAM-DEF
        num_format:参数的进制信息
        """
        container_cfg_obj = bsw_ecuc_dict[module].find(ecuc_path)
        origin_obj = f"DefaultFormat:{num_format}"

        if tag in ECUC_PARAM_VALUE_LIST:
            if tag == "ECUC-INTEGER-PARAM-DEF":
                for para_obj in container_cfg_obj.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                    if mod_path == get_definition_ref(para_obj):
                        AutosarUtil.set_annotation_value(para_obj, origin_obj)
                        set_value(para_obj, cfg_value)
                        return True

    @classmethod
    def get_all_ref_configuration_items_by_ref_target(cls, bsw_ecuc_dict, ref_target):

        return AutosarUtils.get_all_ref_configuration_items_by_ref_target(bsw_ecuc_dict, ref_target)

    @classmethod
    def bsw_editor_update_bsw_module_data(cls, bsw_ecuc_dict, bsw_mod_dict, instance_name):
        ecuc_autosar = bsw_ecuc_dict.get(instance_name)
        if not ecuc_autosar:
            return False
        bsw_ecuc_dict[instance_name] = AutosarUtil.update_autosar(ecuc_autosar)
        module_def_ref = get_definition_ref(ecuc_autosar.find(f"/ActiveEcuC/{instance_name}")) or ""
        module_name = module_def_ref = module_def_ref.split("/")[-1]
        if module_name not in bsw_mod_dict:
            logger.error(f"Cannot load {module_name} bswmd of {instance_name}")
            return
        ecuc_updater = EcucArxmlUpdater(bsw_mod_dict[module_name], bsw_ecuc_dict[instance_name])
        # 执行完update_autosar后，ref value如果没有配置值时，对象中的ValueRef为"",不符合预期，这里将其转换为None
        ecuc_updater.update_ecuc_with_default_value()

    @classmethod
    def bsw_editor_get_all_element_items(cls, bsw_ecuc_dict, filter_text):

        return AutosarUtils.get_all_element_items(bsw_ecuc_dict, filter_text)

    @classmethod
    def bsw_editor_get_all_element_items_from_asw(cls, autosar_asw_class, filter_text):

        return AutosarUtils.get_all_element_items_from_asw(autosar_asw_class, filter_text)

    @classmethod
    def bsw_editor_get_create_container_dialog_show_data(cls, show_data_type, original_data):

        if "init_function_settings" == show_data_type:
            create_container_dialog_show_data = cls.get_init_function_settings_doalog_show_data(original_data)

        return create_container_dialog_show_data

    @classmethod
    def get_init_function_settings_doalog_show_data(cls, original_data):

        init_function_settings_dialog_show_data_list = [
            {
                "checked": cls.create_value_dict("0"),
                "Already Used In": cls.create_value_dict(""),
                **{key: cls.create_value_dict(value) for key, value in init_function_details.items()},
            }
            for init_function, init_function_details in original_data.items()
        ]
        return init_function_settings_dialog_show_data_list

    @classmethod
    def create_value_dict(cls, value):
        """Helper function to create a dictionary with 'value' key."""
        return {"value": value}

    @classmethod
    def reset_initialization(cls, phase, bsw_ecuc_dict, bsw_mod_dict, init_function_settings):

        if phase == "all":
            cls.reset_initialization_zero(bsw_ecuc_dict, bsw_mod_dict, init_function_settings)
            cls.reset_initialization_one(bsw_ecuc_dict, bsw_mod_dict, init_function_settings)
            cls.reset_initialization_two(bsw_ecuc_dict, bsw_mod_dict, init_function_settings)
            cls.reset_initialization_three(bsw_ecuc_dict, bsw_mod_dict, init_function_settings)
        elif phase == "zero":
            cls.reset_initialization_zero(bsw_ecuc_dict, bsw_mod_dict, init_function_settings)
        elif phase == "one":
            cls.reset_initialization_one(bsw_ecuc_dict, bsw_mod_dict, init_function_settings)
        elif phase == "two":
            cls.reset_initialization_two(bsw_ecuc_dict, bsw_mod_dict, init_function_settings)
        elif phase == "three":
            cls.reset_initialization_three(bsw_ecuc_dict, bsw_mod_dict, init_function_settings)

    @classmethod
    def reset_initialization_zero(cls, bsw_ecuc_dict, bsw_mod_dict, init_function_settings):
        parent_ecuc_path = "/ActiveEcuC/EcuM/EcuMConfiguration/EcuMCommonConfiguration"
        parent_mod_path = "/AUTOSAR/EcucDefs/EcuM/EcuMConfiguration/EcuMCommonConfiguration"
        phase_value = {
            "container_group_name": "EcuMDriverInitListZero",
            "phase": "INIT_ZERO",
            "ecuc_path": f"{parent_ecuc_path}/EcuMDriverInitListZero",
            "parent_ecuc_path": parent_ecuc_path,
            "mod_path": f"{parent_mod_path}/EcuMDriverInitListZero/EcuMDriverInitItem",
            "parent_mod_path": f"{parent_mod_path}/EcuMDriverInitListZero",
        }
        cls.handle_phase_initialization(phase_value, bsw_ecuc_dict, bsw_mod_dict, init_function_settings)

    @classmethod
    def reset_initialization_one(cls, bsw_ecuc_dict, bsw_mod_dict, init_function_settings):
        parent_ecuc_path = "/ActiveEcuC/EcuM/EcuMConfiguration/EcuMCommonConfiguration"
        parent_mod_path = "/AUTOSAR/EcucDefs/EcuM/EcuMConfiguration/EcuMCommonConfiguration"
        phase_value = {
            "container_group_name": "EcuMDriverInitListOne",
            "phase": "INIT_ONE",
            "ecuc_path": f"{parent_ecuc_path}/EcuMDriverInitListOne",
            "parent_ecuc_path": parent_ecuc_path,
            "mod_path": f"{parent_mod_path}/EcuMDriverInitListOne/EcuMDriverInitItem",
            "parent_mod_path": f"{parent_mod_path}/EcuMDriverInitListOne",
        }
        cls.handle_phase_initialization(phase_value, bsw_ecuc_dict, bsw_mod_dict, init_function_settings)

    @classmethod
    def reset_initialization_two(cls, bsw_ecuc_dict, bsw_mod_dict, init_function_settings):
        parent_ecuc_path = "/ActiveEcuC/EcuM/EcuMConfiguration/EcuMFlexConfiguration"
        parent_mod_path = "/AUTOSAR/EcucDefs/EcuM/EcuMConfiguration/EcuMFlexConfiguration"
        phase_value = {
            "container_group_name": "EcuMDriverInitListTwo",
            "phase": "INIT_TWO",
            "ecuc_path": f"{parent_ecuc_path}/EcuMDriverInitListTwo",
            "parent_ecuc_path": parent_ecuc_path,
            "mod_path": f"{parent_mod_path}/EcuMDriverInitListBswM/EcuMDriverInitItem",
            "parent_mod_path": f"{parent_mod_path}/EcuMDriverInitListBswM",
        }
        cls.handle_phase_initialization(phase_value, bsw_ecuc_dict, bsw_mod_dict, init_function_settings)

    @classmethod
    def reset_initialization_three(cls, bsw_ecuc_dict, bsw_mod_dict, init_function_settings):
        parent_ecuc_path = "/ActiveEcuC/EcuM/EcuMConfiguration/EcuMFlexConfiguration"
        parent_mod_path = "/AUTOSAR/EcucDefs/EcuM/EcuMConfiguration/EcuMFlexConfiguration"
        phase_value = {
            "container_group_name": "EcuMDriverInitListThree",
            "phase": "INIT_THREE",
            "ecuc_path": f"{parent_ecuc_path}/EcuMDriverInitListThree",
            "parent_ecuc_path": parent_ecuc_path,
            "mod_path": f"{parent_mod_path}/EcuMDriverInitListBswM/EcuMDriverInitItem",
            "parent_mod_path": f"{parent_mod_path}/EcuMDriverInitListBswM",
        }
        cls.handle_phase_initialization(phase_value, bsw_ecuc_dict, bsw_mod_dict, init_function_settings)

    @classmethod
    def handle_phase_initialization(cls, phase_value, bsw_ecuc_dict, bsw_mod_dict, init_function_settings):
        phase_groups_obj = bsw_ecuc_dict["EcuM"].find(phase_value["ecuc_path"])
        conf_def = bsw_mod_dict["EcuM"].find(phase_value["mod_path"])
        parent_conf_def = bsw_mod_dict["EcuM"].find(phase_value["parent_mod_path"])
        parent = bsw_ecuc_dict["EcuM"].find(phase_value["parent_ecuc_path"])
        if phase_groups_obj is not None:
            # 遍历phase_groups_obj，移除存在于init_function_settings中的container，
            # 并重新根据init_function_settings的顺序创建container，从头开始插入
            cls.reset_initialization_assign_phase(
                phase_value["phase"], phase_groups_obj, init_function_settings, conf_def
            )
        else:
            phase_groups_obj = AutosarUtil.create_container_value(
                phase_value["container_group_name"], parent_conf_def, parent
            )
            # 再遍历phase_groups_obj，移除存在于init_function_settings中的container，
            # 并重新根据init_function_settings的顺序创建container，从头开始插入
            cls.reset_initialization_assign_phase(
                phase_value["phase"], phase_groups_obj, init_function_settings, conf_def
            )

    @classmethod
    def reset_initialization_assign_phase(cls, phase, phase_groups_obj, init_function_settings, conf_def):

        ecuc_container_value_list = phase_groups_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE

        # 创建一个新的列表，用于存储不需要删除的项
        new_ecuc_container_value_list = []

        for ecuc_container_value in ecuc_container_value_list:
            if (
                get_short_name(ecuc_container_value) not in init_function_settings
                or phase != init_function_settings[get_short_name(ecuc_container_value)]["Init Phase"]
            ):
                # 如果不满足删除条件，将其添加到新列表中
                new_ecuc_container_value_list.append(ecuc_container_value)

        phase_groups_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE.clear()
        # for container_name, fill_in_param_value in fill_in_param_value_list_dict.items():
        #     container_obj = self.create_container_value(container_name, sec_menu_name=sec_menu_name)
        #     self.fill_prameter_and_referance(container_obj, fill_in_param_value)
        AutosarUtil.update_autosar(phase_groups_obj)
        for module, module_function_setting in init_function_settings.items():
            if module_function_setting["Init Phase"] == phase:
                container_obj = AutosarUtil.create_container_value(
                    module, conf_def, phase_groups_obj, guess_name=module
                )
                cls.fill_prameter_and_referance(container_obj, module_function_setting)

        phase_groups_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE.extend(new_ecuc_container_value_list)

    @classmethod
    def fill_prameter_and_referance(cls, container_value, fill_value_dict, module_name=None, bsw_mod_dict={}):

        if hasattr(container_value.PARAMETER_VALUES, "ECUC_ADD_INFO_PARAM_VALUE"):
            for para in container_value.PARAMETER_VALUES.ECUC_ADD_INFO_PARAM_VALUE:
                def_ref = get_definition_ref(para)
                for definition in fill_value_dict.keys():
                    if definition in def_ref:
                        set_value(para, fill_value_dict[definition])

        if hasattr(container_value.PARAMETER_VALUES, "ECUC_NUMERICAL_PARAM_VALUE"):
            for para in container_value.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref = get_definition_ref(para)
                for definition in fill_value_dict.keys():
                    if definition in def_ref:
                        if fill_value_dict[definition] in [True, False]:
                            set_value(para, str(fill_value_dict[definition]).lower())
                        else:
                            set_value(para, fill_value_dict[definition])

        if hasattr(container_value.PARAMETER_VALUES, "ECUC_TEXTUAL_PARAM_VALUE"):
            for para in container_value.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE:
                def_ref = get_definition_ref(para)
                for definition in fill_value_dict.keys():
                    if definition in def_ref:
                        set_value(para, fill_value_dict[definition])

        if hasattr(container_value.REFERENCE_VALUES, "ECUC_REFERENCE_VALUE"):
            original_reference_values = list(container_value.REFERENCE_VALUES.ECUC_REFERENCE_VALUE)
            parent_param_obj = container_value.REFERENCE_VALUES

            for para in original_reference_values:
                def_ref = get_definition_ref(para)

                for definition in fill_value_dict.keys():
                    if definition in def_ref:
                        if isinstance(fill_value_dict[definition], list):
                            # 如果配置的value是list，表示有多条ref target，需要创建多个对象，再往里对象中填入ref target
                            set_value_ref(para, fill_value_dict[definition][0])  # 设置第一个值
                            # 从第二个值开始复制并设置，避免修改正在迭代的列表
                            for ref_target in fill_value_dict[definition][1:]:
                                if module_name is not None:
                                    param_ref_obj = AutosarUtil.set_reference(
                                        parent_param_obj,
                                        cls.get_module_definition_obj(module_name, bsw_mod_dict).find(definition),
                                    )
                                    set_value_ref(param_ref_obj, ref_target)
                        else:
                            set_value_ref(para, fill_value_dict[definition])

        if hasattr(container_value.REFERENCE_VALUES, "ECUC_INSTANCE_REFERENCE_VALUE"):
            for para in container_value.REFERENCE_VALUES.ECUC_INSTANCE_REFERENCE_VALUE:
                def_ref = get_definition_ref(para)
                for definition in fill_value_dict.keys():
                    if definition in def_ref:
                        set_value(para, fill_value_dict[definition])

        return container_value

    @classmethod
    def get_sec_bsw_management_configuration(
        cls, dialog_type, bsw_ecuc_dict, enable_module_list, system_path, use_get=True
    ):
        if "BswM" not in bsw_ecuc_dict:
            logger.info("Invalid or missing BswM in configuration")
            return

        bswm_common_data_obj = bsw_ecuc_dict["BswM"].find("/ActiveEcuC/BswM/BswMGeneral/BswMCommonData")

        if bswm_common_data_obj is None:  # 如果获取不到bswm common data obj，需要创建他，
            bswm_common_data_obj = cls.create_base_bswm_common_data_obj(bsw_ecuc_dict, system_path)
        if use_get is True:
            bswm_common_data_obj = cls.update_bswm_common_data_obj(
                bswm_common_data_obj, bsw_ecuc_dict, enable_module_list
            )

        ret_value = get_admin_data_all(bswm_common_data_obj)

        dialogue_mapping = {
            "CC": "VCOS2:Communication",
            "ESH": "VCOS2:ESH",
            "INIT": "VCOS2:INIT",
        }

        statemachine_key = dialogue_mapping.get(dialog_type)

        if (
            statemachine_key is None
            or "VCOS2:BswM" not in ret_value
            or "VCOS2:Statemachines" not in ret_value["VCOS2:BswM"]
            or statemachine_key not in ret_value["VCOS2:BswM"]["VCOS2:Statemachines"]
        ):
            logger.info(f"Invalid dialogue type or path: {dialog_type}")

        return ret_value["VCOS2:BswM"]["VCOS2:Statemachines"][statemachine_key]

    @classmethod
    def create_base_bswm_common_data_obj(cls, bsw_ecuc_dict, system_path):
        ecuconfig_file = os.path.join(system_path, "system_secondary", "bsw_management", "base_common_data.arxml")
        ecuc_autosar = AutosarUtil.parse_arxml(ecuconfig_file)  # 加载base bswm ecuc，里面存在base bswm_common_data
        base_bswm_common_data = ecuc_autosar.find("/ActiveEcuC/BswM/BswMGeneral/BswMCommonData")
        ecuc_bswm_general_obj = bsw_ecuc_dict["BswM"].find("/ActiveEcuC/BswM/BswMGeneral")
        ecuc_bswm_general_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE.append(base_bswm_common_data)
        bsw_ecuc_dict["BswM"] = AutosarUtil.update_autosar(bsw_ecuc_dict["BswM"])
        return bsw_ecuc_dict["BswM"].find("/ActiveEcuC/BswM/BswMGeneral/BswMCommonData")

    @classmethod
    def update_bswm_common_data_obj(cls, bswm_common_data_obj, bsw_ecuc_dict, enable_module_list):
        # 获取完成后，因为工程在不断的配置，还需要校验bswm_common_data_obj是否正确，如果不正确，需要更新它
        # 主要校验的有ESH和CC两部分
        # ESH
        #  Dem模块是否存在，决定Dem_Handing是否存在
        #  ComM里的通道需要更新到Support ComM下
        #  NvM模块是否存在，决定NvM Handling是否存在
        #  Rte模块是否存在，决定Rte Mode Sync是否存在
        #  EcuM模块是否存在，决定EcuM Mode Handling是否存在
        # CC
        #  更新channel，以及channel下的
        #    Nm Communication 与Nm模块和DCM模块相关
        #    tx group和rx pdu
        # init = bswm_common_data_obj.ADMIN_DATA.SDGS.SDG[0].SDG[0].SDG[0]
        esh = bswm_common_data_obj.ADMIN_DATA.SDGS.SDG[0].SDG[0].SDG[1]
        cc = bswm_common_data_obj.ADMIN_DATA.SDGS.SDG[0].SDG[0].SDG[2]

        cls.update_bswm_common_data_obj_esh(esh, bsw_ecuc_dict, enable_module_list)
        cls.update_bswm_common_data_obj_cc(cc, bsw_ecuc_dict, enable_module_list)
        bsw_ecuc_dict["BswM"] = AutosarUtil.update_autosar(bsw_ecuc_dict["BswM"])
        return bsw_ecuc_dict["BswM"].find("/ActiveEcuC/BswM/BswMGeneral/BswMCommonData")

    @classmethod
    def update_bswm_common_data_obj_cc(cls, cc_obj, bsw_ecuc_dict, enable_module_list):
        support_comm = "ComM" in enable_module_list
        support_channel_dict = {}
        support_pdu_group_list = []
        del_sdg_list = []
        existed_channel_list = []
        if support_comm is True:
            comm_config_set_obj = bsw_ecuc_dict["ComM"].find("/ActiveEcuC/ComM/ComMConfigSet")
            for config_set in comm_config_set_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                if "/AUTOSAR/EcucDefs/ComM/ComMConfigSet/ComMChannel" == get_definition_ref(config_set):
                    for v in getattr(getattr(config_set, "PARAMETER_VALUES", None), "ECUC_TEXTUAL_PARAM_VALUE", []):
                        if "/AUTOSAR/EcucDefs/ComM/ComMConfigSet/ComMChannel/ComMBusType" == get_definition_ref(v):
                            support_channel_dict[get_short_name(config_set)] = (get_value(v) or "").split("_")[-1]
            for sub_sdg_tmp in cc_obj.SDG:
                if sub_sdg_tmp.GID.split(":")[-1] not in support_channel_dict:
                    del_sdg_list.append(sub_sdg_tmp)
                else:
                    existed_channel_list.append(sub_sdg_tmp.GID.split(":")[-1])

            for del_sdg in del_sdg_list:
                cc_obj.SDG.remove(del_sdg)
            for existed_channel in existed_channel_list:
                support_channel_dict.pop(existed_channel)

            # /ActiveEcuC/Com/ComConfig/MyECU_oCAN_Rx_63a3e3ce
            for need_to_add_channel, bus_type in support_channel_dict.items():
                module_name = f"{bus_type[:1].upper()}{bus_type[1:].lower()}"
                sdg_label = "VCOS2:Feature:" + need_to_add_channel
                sub_sdg_obj = AutosarUtil.create_sdg_obj_common_data(
                    sdg_label,
                    {"VCOS2:Name": need_to_add_channel, "VCOS2:Value": "FALSE", "VCOS2:BswModule": module_name},
                )
                cc_obj.SDG.append(sub_sdg_obj)

            # 获取com中所有的pdu group
            support_com = "Com" in enable_module_list
            if support_com:
                com_config_obj = bsw_ecuc_dict["Com"].find("/ActiveEcuC/Com/ComConfig")
                for com_config in com_config_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                    if "/AUTOSAR/EcucDefs/Com/ComConfig/ComIPduGroup" == get_definition_ref(com_config):
                        support_pdu_group_list.append(get_short_name(com_config))

            for sub_sdg_tmp in cc_obj.SDG:
                supported_group_or_nm_list = []
                for group_or_nm_sdg in sub_sdg_tmp.SDG:
                    if group_or_nm_sdg.GID.split(":")[-1] in support_pdu_group_list:
                        supported_group_or_nm_list.append(group_or_nm_sdg.GID.split(":")[-1])

                if (
                    sub_sdg_tmp.GID.split(":")[-1] + "_Tx" not in supported_group_or_nm_list
                    and sub_sdg_tmp.GID.split(":")[-1] + "_Tx" in support_pdu_group_list
                ):
                    sdg_label = "VCOS2:Feature:Group:" + sub_sdg_tmp.GID.split(":")[-1] + "_Tx"
                    tx_sdg_obj = AutosarUtil.create_sdg_obj_common_data(
                        sdg_label,
                        {"VCOS2:Name": "Group:" + sub_sdg_tmp.GID.split(":")[-1] + "_Tx", "VCOS2:Value": "FALSE"},
                    )
                    sub_sdg_tmp.SDG.append(tx_sdg_obj)
                if (
                    sub_sdg_tmp.GID.split(":")[-1] + "_Rx" not in supported_group_or_nm_list
                    and sub_sdg_tmp.GID.split(":")[-1] + "_Rx" in support_pdu_group_list
                ):
                    sdg_label = "VCOS2:Feature:Group:" + sub_sdg_tmp.GID.split(":")[-1] + "_Rx"
                    rx_sdg_obj = AutosarUtil.create_sdg_obj_common_data(
                        sdg_label,
                        {"VCOS2:Name": "Group:" + sub_sdg_tmp.GID.split(":")[-1] + "_Rx", "VCOS2:Value": "FALSE"},
                    )
                    sub_sdg_tmp.SDG.append(rx_sdg_obj)

    @classmethod
    def update_bswm_common_data_obj_esh(cls, esh_obj, bsw_ecuc_dict, enable_module_list):
        del_sdg_list = []
        support_comm = True
        features_to_check = {
            "VCOS2:Feature:Dem_Handling": "Dem",
            "VCOS2:Feature:Support_ComM": "ComM",
            "VCOS2:Feature:NvM_Handling": "NvM",
            "VCOS2:Feature:Rte_Mode_Synchronization": "Rte",
            "VCOS2:Feature:EcuM_Mode_Handling": "EcuM",
        }

        support_comm = "ComM" in enable_module_list
        sdg_to_remove = []
        suppored_sdg_gid = []

        # Remove unneeded SDGs
        for sub_sdg in esh_obj.SDG[0].SDG:
            feature_module = features_to_check.get(sub_sdg.GID)
            if feature_module and feature_module not in enable_module_list:
                sdg_to_remove.append(sub_sdg)
            suppored_sdg_gid.append(sub_sdg.GID)
        for sdg in sdg_to_remove:
            esh_obj.SDG[0].SDG.remove(sdg)

        for sdg_label, _ in features_to_check.items():
            if sdg_label not in suppored_sdg_gid and features_to_check.get(sdg_label) in enable_module_list:
                sub_sdg_obj = AutosarUtil.create_sdg_obj_common_data(
                    sdg_label, {"VCOS2:Name": sdg_label.split(":")[-1], "VCOS2:Value": "FALSE"}
                )
                esh_obj.SDG[0].SDG.append(sub_sdg_obj)

        # 更新support comm
        support_channel_list = []
        del_sdg_list = []
        existed_channel_list = []

        if support_comm is True:
            comm_config_set_obj = bsw_ecuc_dict["ComM"].find("/ActiveEcuC/ComM/ComMConfigSet")
            for config_set in comm_config_set_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                if "/AUTOSAR/EcucDefs/ComM/ComMConfigSet/ComMChannel" == get_definition_ref(config_set):
                    support_channel_list.append(get_short_name(config_set))
            for sub_sdg in esh_obj.SDG[0].SDG:
                if sub_sdg.GID == "VCOS2:Feature:Support_ComM":
                    for sub_sdg_tmp in sub_sdg.SDG:
                        if sub_sdg_tmp.GID.split(":")[-1] not in support_channel_list:
                            del_sdg_list.append(sub_sdg_tmp)
                        else:
                            existed_channel_list.append(sub_sdg_tmp.GID.split(":")[-1])

                    for del_sdg in del_sdg_list:
                        sub_sdg.SDG.remove(del_sdg)
                    for existed_channel in existed_channel_list:
                        support_channel_list.remove(existed_channel)

                    for need_to_add_channel in support_channel_list:
                        sdg_label = "VCOS2:Feature:" + need_to_add_channel
                        sub_sdg_obj = AutosarUtil.create_sdg_obj_common_data(
                            sdg_label, {"VCOS2:Name": need_to_add_channel, "VCOS2:Value": "FALSE"}
                        )
                        sub_sdg.SDG.append(sub_sdg_obj)

    @classmethod
    def update_state_to_bswm_common_data(cls, item_state_cache, dialog_type, bsw_ecuc_dict):
        if "BswM" not in bsw_ecuc_dict:
            logger.info("Invalid or missing BswM in configuration")
            return

        bswm_common_data_obj = bsw_ecuc_dict["BswM"].find("/ActiveEcuC/BswM/BswMGeneral/BswMCommonData")
        if dialog_type == "ESH":
            dialog_type = "VCOS2:ESH"
        elif dialog_type == "INIT":
            dialog_type = "VCOS2:INIT"
        elif dialog_type == "CC":
            dialog_type = "VCOS2:Communication"
        for item_path, state in item_state_cache.items():
            cls.set_bswm_common_data_by_path(
                bswm_common_data_obj, "/VCOS2:BswM/VCOS2:Statemachines/" + dialog_type + item_path, state
            )  # 修改
            pass

    @classmethod
    def set_bswm_common_data_by_path(cls, obj, item_path, new_state):
        def set_state(sdg_obj, parts):
            if not parts:
                return False
            current_part = parts.pop(0)

            # 如果当前部分匹配SDG的GID，处理
            if hasattr(sdg_obj, "GID") and sdg_obj.GID == current_part:
                if not parts:  # 如果已经是路径的最后一部分则更新状态
                    # 如果包含SD，处理SD
                    if hasattr(sdg_obj, "SD"):
                        for child_sd in sdg_obj.SD:
                            if hasattr(child_sd, "GID") and child_sd.GID == "VCOS2:Value":
                                if hasattr(child_sd, "valueOf_"):  # 找到目标SD，更新状态
                                    child_sd.valueOf_ = new_state
                                    return True
                                else:
                                    logger.info(f"Target object at {item_path} does not match expected structure.")
                    else:
                        logger.info(
                            f"Target object at {item_path} does not have valueOf_ attribute "
                            "but it was expected to be an SD."
                        )
                # 如果路径还有剩余部分且当前层级包含SDG，递归处理SDG
                if hasattr(sdg_obj, "SDG"):
                    for child_sdg in sdg_obj.SDG:
                        if set_state(child_sdg, list(parts)):
                            return True

            return False

        # 检查 ADMIN_DATA 是否存在
        if hasattr(obj, "ADMIN_DATA") and hasattr(obj.ADMIN_DATA, "SDGS"):
            parts = item_path.strip("/").split("/")  # 分割路径为列表
            for sdg in obj.ADMIN_DATA.SDGS.SDG:
                if set_state(sdg, list(parts)):
                    return
        logger.info(f"Path not found or update failed: {item_path}")

    @classmethod
    def check_container_of_bswm_ecuc(
        cls, dialog_type, create_sub_container_rules, bsw_ecuc_dict, bsw_mod_dict, enable_module_list, system_path
    ):

        sec_bsw_management_configuration = cls.get_sec_bsw_management_configuration(
            dialog_type, bsw_ecuc_dict, enable_module_list, system_path, use_get=False
        )
        if sec_bsw_management_configuration is None:
            return
        # 1. 如果是INIT，检查Action和ActionList
        # 遍历sec_bsw_management_configuration，根据VCOS2:Value属性值的属性值check对应的container
        # 1. 如果是INIT，检查Action和ActionList(检查哪些定义在配置文件中)
        # 2. 如果是CC, ...
        # 3. 如果是ESH, ...
        ecuc_autosar = bsw_ecuc_dict.get("BswM")
        if dialog_type == "INIT":
            cls.sec_bsw_management_init_handler(
                dialog_type,
                ecuc_autosar,
                bsw_mod_dict,
                create_sub_container_rules[0][dialog_type],
                sec_bsw_management_configuration,
            )
        elif dialog_type == "CC":
            cls.sec_bsw_management_cc_handler(
                "Communication",
                ecuc_autosar,
                bsw_mod_dict,
                create_sub_container_rules[0][dialog_type],
                sec_bsw_management_configuration,
            )
        elif dialog_type == "ESH":
            cls.sec_bsw_management_esh_handler(
                dialog_type,
                ecuc_autosar,
                bsw_mod_dict,
                create_sub_container_rules[0][dialog_type],
                sec_bsw_management_configuration,
            )

    @classmethod
    def sec_bsw_management_init_handler(
        cls, dialog_type, bswm_ecuc_obj, bsw_mod_dict, create_sub_container_rules, sec_bsw_management_configuration
    ):
        cls.traverse_bsw_management_configuration_init_and_esh(
            dialog_type, bswm_ecuc_obj, bsw_mod_dict, create_sub_container_rules, sec_bsw_management_configuration
        )

    @classmethod
    def sec_bsw_management_cc_handler(
        cls, dialog_type, bswm_ecuc_obj, bsw_mod_dict, create_sub_container_rules, sec_bsw_management_configuration
    ):
        cls.traverse_bsw_management_configuration_cc_common(
            dialog_type, bswm_ecuc_obj, bsw_mod_dict, create_sub_container_rules, sec_bsw_management_configuration
        )
        cls.traverse_bsw_management_configuration_cc(
            dialog_type, bswm_ecuc_obj, bsw_mod_dict, create_sub_container_rules, sec_bsw_management_configuration
        )

    @classmethod
    def sec_bsw_management_esh_handler(
        cls, dialog_type, bswm_ecuc_obj, bsw_mod_dict, create_sub_container_rules, sec_bsw_management_configuration
    ):
        cls.traverse_bsw_management_configuration_init_and_esh(
            dialog_type, bswm_ecuc_obj, bsw_mod_dict, create_sub_container_rules, sec_bsw_management_configuration
        )

    @classmethod
    def traverse_bsw_management_configuration_cc_common(
        cls,
        dialog_type,
        bswm_ecuc_obj,
        bsw_mod_dict,
        create_sub_container_rules,
        data,
        features=None,
        channel_name=None,
    ):
        if features is None:
            features = {}

        for key_root, value_root in data.items():
            rx_or_tx_group = False
            channel_name = value_root["VCOS2:Name"]
            module_name = value_root["VCOS2:BswModule"]
            for key, value in value_root.items():
                if isinstance(value, dict) and value["VCOS2:Value"] == "TRUE":
                    rx_or_tx_group = True
            bsw_mode_dict = create_sub_container_rules.get("bsw_mode", {}).get(module_name, {})
            replace_dict = {"{channel_name}": channel_name, "{module_name}": module_name, **bsw_mode_dict}
            if rx_or_tx_group is False:
                real_rules = cls.replace_placeholders(create_sub_container_rules["group_common"], replace_dict)
                for container_cfg_rule in real_rules:
                    cls.is_false_and_check_container(bswm_ecuc_obj, bsw_mod_dict, container_cfg_rule)
            elif rx_or_tx_group is True:
                real_rules = cls.replace_placeholders(create_sub_container_rules["group_common"], replace_dict)
                for container_cfg_rule in real_rules:
                    cls.is_true_and_check_container(dialog_type, bswm_ecuc_obj, bsw_mod_dict, container_cfg_rule)

    @classmethod
    def traverse_bsw_management_configuration_cc(
        cls,
        dialog_type,
        bswm_ecuc_obj,
        bsw_mod_dict,
        create_sub_container_rules,
        data,
        features=None,
        channel_name=None,
    ):
        if features is None:
            features = {}
        for key, value in data.items():
            module_name = (
                data.get("VCOS2:BswModule", "") or value.get("VCOS2:BswModule", "") if isinstance(value, dict) else ""
            )
            channel_name = key.split(":")[-1]
            if channel_name.endswith("_Tx") or channel_name.endswith("_Rx"):
                channel_name = channel_name.rsplit("_", 1)[0]
            bsw_mode_dict = create_sub_container_rules.get("bsw_mode", {}).get(module_name, {})
            replace_dict = {
                "{channel_name}": channel_name,
                "{group_name}": key.split(":")[-1],
                "{module_name}": module_name,
                **bsw_mode_dict,
            }
            if "group" in key.lower() and "tx" in key.lower():
                real_rules = cls.replace_placeholders(create_sub_container_rules["group_tx"], replace_dict)
                for container_cfg_rule in real_rules:
                    if value["VCOS2:Value"] == "TRUE":
                        cls.is_true_and_check_container(dialog_type, bswm_ecuc_obj, bsw_mod_dict, container_cfg_rule)
                    elif value["VCOS2:Value"] == "FALSE":
                        cls.is_false_and_check_container(bswm_ecuc_obj, bsw_mod_dict, container_cfg_rule)
            elif "group" in key.lower() and "rx" in key.lower():
                real_rules = cls.replace_placeholders(create_sub_container_rules["group_rx"], replace_dict)
                for container_cfg_rule in real_rules:
                    if value["VCOS2:Value"] == "TRUE":
                        cls.is_true_and_check_container(dialog_type, bswm_ecuc_obj, bsw_mod_dict, container_cfg_rule)
                    elif value["VCOS2:Value"] == "FALSE":
                        cls.is_false_and_check_container(bswm_ecuc_obj, bsw_mod_dict, container_cfg_rule)
            elif "Nm Communication" == key:
                real_rules = cls.replace_placeholders(create_sub_container_rules["nm_communication"], replace_dict)
                for container_cfg_rule in real_rules:
                    if value["VCOS2:Value"] == "TRUE":
                        cls.is_true_and_check_container(dialog_type, bswm_ecuc_obj, bsw_mod_dict, container_cfg_rule)
                    elif value["VCOS2:Value"] == "FALSE":
                        cls.is_false_and_check_container(bswm_ecuc_obj, bsw_mod_dict, container_cfg_rule)

                # 递归遍历子字典中的内容
            if isinstance(value, dict):  # 检查value是否为字典
                features.update(
                    cls.traverse_bsw_management_configuration_cc(
                        dialog_type,
                        bswm_ecuc_obj,
                        bsw_mod_dict,
                        create_sub_container_rules,
                        value,
                        features,
                        channel_name=channel_name,
                    )
                )

        return features

    @classmethod
    def traverse_bsw_management_configuration_init_and_esh(
        cls, dialog_type, bswm_ecuc_obj, bsw_mod_dict, create_sub_container_rules, data, features=None
    ):
        if features is None:
            features = {}
        for key, value in data.items():
            if key in create_sub_container_rules:
                for container_cfg_rule in create_sub_container_rules[key]:
                    if value["VCOS2:Value"] == "TRUE":
                        cls.is_true_and_check_container(dialog_type, bswm_ecuc_obj, bsw_mod_dict, container_cfg_rule)
                    elif value["VCOS2:Value"] == "FALSE":
                        cls.is_false_and_check_container(bswm_ecuc_obj, bsw_mod_dict, container_cfg_rule)

                # 递归遍历子字典中的内容
            if isinstance(value, dict):  # 检查value是否为字典
                features.update(
                    cls.traverse_bsw_management_configuration_init_and_esh(
                        dialog_type, bswm_ecuc_obj, bsw_mod_dict, create_sub_container_rules, value, features
                    )
                )

        return features

    @classmethod
    def is_true_and_check_container(cls, dialog_type, bswm_ecuc_obj, bsw_mod_dict, container_cfg_rule):
        # 处理当前层级的container信息
        ecuc_path = container_cfg_rule.get("ecuc_path")
        mod_path = container_cfg_rule.get("mod_path")
        short_name = container_cfg_rule.get("short_name")
        parameter = container_cfg_rule.get("parameter")
        if not bswm_ecuc_obj.find(ecuc_path):
            # 如果container不存在，创建container，并填入参数
            # 如果container不存在，不检查参数是否正确（用户可能修改过），
            # 但还是会遍历sub container，container必须存在，但参数不会check
            parent_obj = bswm_ecuc_obj.find("/".join(ecuc_path.split("/")[:-1]))
            container_def = cls.get_module_definition_obj("BswM", bsw_mod_dict).find(mod_path)
            if container_def is None:
                return
            container_obj = AutosarUtil.create_container_value(short_name, container_def, parent_obj)
            cls.fill_prameter_and_referance(container_obj, parameter, module_name="BswM", bsw_mod_dict=bsw_mod_dict)
            admin_data_config = {"VCOS2:BswM": {"VCOS2:Statemachines": {"VCOS2:" + dialog_type: {"NAME": short_name}}}}
            AutosarUtil.add_admin_data_value(container_obj, admin_data_config)
            # 添加ADMIN-DATA
            rule = RULE_DICT.get("BswM", base_rule_instance)
            rule.container_create_trigger(container_obj, from_ui=False)

        # 如果存在sub_container，递归处理
        for sub_container in container_cfg_rule.get("sub_container", []):
            cls.is_true_and_check_container(dialog_type, bswm_ecuc_obj, bsw_mod_dict, sub_container)

    @classmethod
    def is_false_and_check_container(cls, bswm_ecuc_obj, bsw_mod_dict, container_cfg_rule):

        # 处理当前层级的container信息
        ecuc_path = container_cfg_rule.get("ecuc_path")
        short_name = container_cfg_rule.get("short_name")
        if bswm_ecuc_obj.find(ecuc_path):
            parent_obj = bswm_ecuc_obj.find("/".join(ecuc_path.split("/")[:-1]))
            if parent_obj and short_name not in ["INIT_AL_Initialize"]:
                if bswm_ecuc_obj.find(ecuc_path) in parent_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                    # parent_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE.remove(bswm_ecuc_obj.find(ecuc_path))
                    AutosarUtil.remove_container_value(
                        parent_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE, bswm_ecuc_obj.find(ecuc_path)
                    )
                    # AutosarUtil.update_autosar(bswm_ecuc_obj)
        # 如果存在sub_container，递归调用process_container
        for sub_container in container_cfg_rule.get("sub_container", []):
            cls.is_false_and_check_container(bswm_ecuc_obj, bsw_mod_dict, sub_container)

    @classmethod
    def replace_placeholders(cls, data, replace_dict):
        """
        递归替换字典中的占位符。

        :param data: 要处理的字典或列表
        :param replace_dict: 一个字典，包含占位符的原始文本和要替换的值
        """
        if isinstance(data, dict):
            return {
                cls.replace_placeholders(key, replace_dict): cls.replace_placeholders(value, replace_dict)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [cls.replace_placeholders(item, replace_dict) for item in data]
        elif isinstance(data, str):
            for placeholder, replacement in replace_dict.items():
                data = data.replace(placeholder, replacement)
            return data
        else:
            return data

    @classmethod
    def sec_get_init_functions_that_have_been_initialized_in_ecum(cls, module_name, bsw_ecuc_dict):
        initialized_function_list = []
        if module_name in bsw_ecuc_dict:
            ecum_obj = bsw_ecuc_dict[module_name]
            zero_obj = ecum_obj.find(
                "/ActiveEcuC/EcuM/EcuMConfiguration/EcuMCommonConfiguration/EcuMDriverInitListZero"
            )
            for initialize_obj in zero_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                initialized_function_list.append(get_short_name(initialize_obj) + " initialized in ecum(zero)")
            one_obj = ecum_obj.find("/ActiveEcuC/EcuM/EcuMConfiguration/EcuMCommonConfiguration/EcuMDriverInitListOne")
            for initialize_obj in one_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                initialized_function_list.append(get_short_name(initialize_obj) + " initialized in ecum(one)")
            two_obj = ecum_obj.find("/ActiveEcuC/EcuM/EcuMConfiguration/EcuMFlexConfiguration/EcuMDriverInitListTwo")
            if two_obj:
                for initialize_obj in two_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                    initialized_function_list.append(get_short_name(initialize_obj) + " initialized in ecum(two)")
            three_obj = ecum_obj.find(
                "/ActiveEcuC/EcuM/EcuMConfiguration/EcuMFlexConfiguration/EcuMDriverInitListThree"
            )
            if three_obj:
                for initialize_obj in three_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                    initialized_function_list.append(get_short_name(initialize_obj) + " initialized in ecum(three)")

        return initialized_function_list

    @classmethod
    def get_show_data_action(cls, instance_name, module_name, container_cfg_obj, container_definition_obj):
        # 构建根容器的显示数据
        show_data_dict = cls.get_show_data(instance_name, module_name, container_cfg_obj, container_definition_obj)
        # 获取根容器的子容器数据
        show_data_dict["sub_containers"] = cls.get_sub_container_obj(
            instance_name, module_name, container_cfg_obj, container_definition_obj
        )
        return show_data_dict

    @classmethod
    def get_sub_container_obj(cls, instance_name, module_name, container_cfg_obj, container_definition_obj):
        # 创建一个列表来保存所有子容器的数据
        sub_containers_list = []
        for sub_container_obj in container_cfg_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
            definition_ref = get_definition_ref(sub_container_obj)
            sub_container_definition = container_definition_obj.find(definition_ref)
            sub_show_data_dict = cls.get_show_data(
                instance_name, module_name, sub_container_obj, sub_container_definition
            )

            # 如果当前子容器还有它自己的子容器
            if len(sub_container_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE) > 0:
                # 递归获取子容器的子容器数据
                sub_show_data_dict["sub_containers"] = cls.get_sub_container_obj(
                    instance_name, module_name, sub_container_obj, sub_container_definition
                )

            # 由于definition_ref可能相同，不使用definition_ref作为关键字，直接将数据字典添加到列表中
            sub_containers_list.append(sub_show_data_dict)

        return sub_containers_list

    @classmethod
    def sec_get_bswm_mod_and_ecuc_obj(cls, selected_item_path, bsw_ecuc_dict, bsw_mod_dict):

        return {"BswM": AutosarUtils.get_bswmd_autosar_by_module_name("BswM", bsw_mod_dict["BswM"])}, {
            "BswM": bsw_ecuc_dict["BswM"].find(selected_item_path)
        }

    @classmethod
    def get_admin_data(cls, bswmd_obj):
        return get_admin_data(bswmd_obj)

    @classmethod
    def get_used_os_alarm_infos_by_task_ref(cls, bsw_ecuc_dict, task_ref: str):
        if "Rte" not in bsw_ecuc_dict:
            return []
        rte = bsw_ecuc_dict["Rte"].find("/ActiveEcuC/Rte")
        container_value_list = getattr(getattr(rte, "CONTAINERS", ""), "ECUC_CONTAINER_VALUE", [])
        instance_list = [
            v
            for v in container_value_list
            if isinstance(get_definition_ref(v), str)
            and get_definition_ref(v).split("/")[-1] in ["RteBswModuleInstance", "RteSwComponentInstance"]
        ]
        rte_used_alarm_info = defaultdict(list)
        for instance in instance_list:
            sub_container_value_list = getattr(getattr(instance, "SUB_CONTAINERS", ""), "ECUC_CONTAINER_VALUE", [])
            event_to_task_mapping_list = [
                v
                for v in sub_container_value_list
                if isinstance(get_definition_ref(v), str)
                and get_definition_ref(v).split("/")[-1] in ["RteEventToTaskMapping", "RteBswEventToTaskMapping"]
            ]
            for event_to_task_mapping in event_to_task_mapping_list:
                mapping_info = {}
                mapping_info["ref"] = event_to_task_mapping.get_path()
                parameter_value_list = getattr(
                    getattr(event_to_task_mapping, "PARAMETER_VALUES", ""), "ECUC_NUMERICAL_PARAM_VALUE", []
                )
                reference_value_list = getattr(
                    getattr(event_to_task_mapping, "REFERENCE_VALUES", ""), "ECUC_REFERENCE_VALUE", []
                )
                for value in parameter_value_list + reference_value_list:
                    def_ref = get_definition_ref(value) or ""
                    if def_ref.endswith("RteActivationOffset") or def_ref.endswith("RteBswActivationOffset"):
                        mapping_info["offset"] = get_value(value) or "0"
                    elif def_ref.endswith("RteMappedToTaskRef") or def_ref.endswith("RteBswMappedToTaskRef"):
                        mapping_info["task_ref"] = get_value_ref(value)
                    elif def_ref.endswith("RteUsedOsAlarmRef") or def_ref.endswith("RteBswUsedOsAlarmRef"):
                        mapping_info["alarm_ref"] = get_value_ref(value)
                if mapping_info["alarm_ref"]:
                    rte_used_alarm_info[mapping_info["task_ref"]].append(mapping_info)
        return rte_used_alarm_info.get(task_ref, [])

    @classmethod
    def set_used_alarm_offset_by_mapping_ref(cls, bsw_ecuc_dict, mapping_ref_list: list, offset: str):
        if "Rte" not in bsw_ecuc_dict:
            return False
        for mapping_ref in mapping_ref_list:
            event_to_task_mapping = bsw_ecuc_dict["Rte"].find(mapping_ref)
            parameter_value_list = getattr(
                getattr(event_to_task_mapping, "PARAMETER_VALUES", ""), "ECUC_NUMERICAL_PARAM_VALUE", []
            )
            for value in parameter_value_list:
                def_ref = get_definition_ref(value) or ""
                if def_ref.endswith("RteActivationOffset") or def_ref.endswith("RteBswActivationOffset"):
                    set_value(value, offset)
        return True

    @classmethod
    def get_offset_cfg_by_jitter_config(cls, bsw_ecuc_dict, alarm_jitter_cfg):
        offset_cfg = []
        for task_name, alarm_cfgs in alarm_jitter_cfg.items():
            if not isinstance(alarm_cfgs, dict):
                continue
            mapping_list = cls.get_used_os_alarm_infos_by_task_ref(bsw_ecuc_dict, f"/ActiveEcuC/Os/{task_name}")
            if not mapping_list:
                continue
            if alarm_cfgs.get("offset"):
                offset_cfg.append([mapping_list, alarm_cfgs["offset"]])
            else:
                alarm_list = alarm_cfgs.get("alarm_list", [])
                for alarm_cfg in alarm_list:
                    alarm_name = alarm_cfg.get("alarm_name")
                    alarm_offset = alarm_cfg.get("offset")
                    if not alarm_offset or not alarm_name:
                        continue
                    mapping_list = [mapping for mapping in mapping_list if alarm_name in mapping.get("alarm_ref", "")]
                    offset_cfg.append([mapping_list, alarm_offset])
        return offset_cfg

    @classmethod
    def set_used_alarm_offset_by_offset_cfg(cls, bsw_ecuc_dict, offset_cfg):
        for mapping_list, offset in offset_cfg:
            mapping_ref_list = [mapping.get("ref", "") for mapping in mapping_list]
            cls.set_used_alarm_offset_by_mapping_ref(bsw_ecuc_dict, mapping_ref_list, offset)

    @classmethod
    def set_used_alarm_offset_by_mapping_list(cls, bsw_ecuc_dict, mapping_list):
        for mapping in mapping_list:
            mapping_ref = mapping.get("ref", "")
            offset = mapping.get("offset", "0")
            cls.set_used_alarm_offset_by_mapping_ref(bsw_ecuc_dict, [mapping_ref], offset)

    @classmethod
    def get_core_task_dict(cls, asw_autosar, bsw_ecuc_dict, ib_bswmds):
        os_autosar = bsw_ecuc_dict.get("Os")
        rte_autosar = bsw_ecuc_dict.get("Rte")
        ecuc_autosar = bsw_ecuc_dict.get("EcuC")
        task_core_dict = {}
        try:
            task_list = ScheduleTableManager.get_ecuc_cfg(os_autosar, "/ActiveEcuC/Os", "OsTask", 0)
            app_list = ScheduleTableManager.get_ecuc_cfg(os_autosar, "/ActiveEcuC/Os", "OsApplication", 0)
            core_list = ScheduleTableManager.get_ecuc_cfg(
                ecuc_autosar, "/ActiveEcuC/EcuC/EcucHardware", "EcucCoreDefinition", 0
            )
            timing_eucu_cfgs = ScheduleTableManager.get_timing_ecuc_infos(
                os_autosar, rte_autosar, asw_autosar, ib_bswmds
            )
            core_dict = {
                f'/ActiveEcuC/EcuC/EcucHardware/{core_def["ShortName"]}': int(core_def.get("EcucCoreId", 0))
                for core_def in core_list
            }
            task_dict = {
                task["ShortName"]: task.get("OsTaskPriority", "0") for task in task_list if not task["SubContainers"]
            }
            task_core_dict = defaultdict(dict)
            for app in app_list:
                for task_ref in app.get("OsAppTaskRef", "").split(":"):
                    task_name = task_ref.split("/")[-1]
                    if task_name not in timing_eucu_cfgs:
                        continue
                    core_id = core_dict.get(app.get("OsApplicationCoreRef"), 0)
                    if task_name not in task_dict:
                        continue
                    cfg = {"priority": task_dict[task_name], "timing": timing_eucu_cfgs[task_name]}
                    task_core_dict[f"Core{core_id}"][task_name] = cfg
        except Exception:
            logger.exception("get task dict ERROR!")
        return task_core_dict

    @classmethod
    def load_jitter_opt_history(cls, base_cfg_path):
        history = FileIOHandler.load_json_file(os.path.join(base_cfg_path, "system/jitter_opt_history.json"))
        return history or []

    @classmethod
    def save_jitter_opt_history(cls, base_cfg_path, history):
        with open(os.path.join(base_cfg_path, "system/jitter_opt_history.json"), "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)

    @classmethod
    def get_all_ref_param_values(cls, container_obj, param_mod_path, param_name, result_dict: dict):
        # get all reference parameter values in one container
        if f"{get_definition_ref(container_obj)}/{param_name}" == param_mod_path:
            for ref_attr in ("ECUC_INSTANCE_REFERENCE_VALUE", "ECUC_REFERENCE_VALUE"):
                for ref_param in getattr(getattr(container_obj, "REFERENCE_VALUES", None), ref_attr, []):
                    if get_definition_ref(ref_param) != param_mod_path:
                        continue
                    ref_val = (
                        get_value_iref(ref_param)
                        if "ECUC_INSTANCE_REFERENCE_VALUE" == ref_attr
                        else get_value_ref(ref_param)
                    )
                    if ref_val:
                        param_path = ref_param.get_path()
                        result_dict.setdefault(param_path, [])
                        result_dict[param_path].append(ref_val)

        for container_type in ("CONTAINERS", "SUB_CONTAINERS"):
            peer_containers = getattr(container_obj, container_type, None)
            for peer_container in getattr(peer_containers, "ECUC_CONTAINER_VALUE", []):
                if f"{get_definition_ref(peer_container)}/" not in param_mod_path:
                    continue
                cls.get_all_ref_param_values(peer_container, param_mod_path, param_name, result_dict)
