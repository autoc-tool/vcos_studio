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
import re
from func_module.health_monitor.logger import logger
from basic_func_module.autosar_utils.autosar_utils import AutosarUtils
from basic_func_module.autosar_utils.utils import (
    get_min,
    get_max,
    get_max_length,
    get_min_length,
    get_lower_multiplicity,
    get_short_name,
    get_upper_multiplicity,
    get_upper_multiplicity_infinite,
    get_value,
    get_definition_ref,
    get_value_ref,
    get_value_iref,
    get_admin_data,
    get_default_value,
    get_destination_type,
    get_destination_ref,
    get_destination_refs,
    get_max_interval_type,
    get_min_interval_type,
    get_admin_data_all,
)
from enum import Enum
from func_module.validation.common.validation_def import ValidationResult
import hashlib

INTERVAL_CLOSED = "CLOSED"
CONTAINER_NAME_IDX = -2


class ValidationType(Enum):
    VALIDATE_NUMERICAL = 0
    VALIDATE_STRING = 1
    VALIDATE_STRING_REF = 2
    VALIDATE_ENUMERATION = 3
    VALIDATE_CONTAINER_NAME = 4


# 校验的基础数据项
class BasicValidationData:

    def __init__(self) -> None:
        self.param_name = None
        self.param_value = None
        self.data_type = None
        self.param_path = None
        self.module_name = None
        self.instance_name = None
        self.mod_path = None
        self.lower_multiplicity = None
        self.upper_multiplicity = None
        self.upper_multiplicity_infinite = None
        # 将 字符串长度 与 整数大小 合并为一个参数
        self.max_limit = None
        self.min_limit = None
        self.default_value = None
        self.min_closed = True
        self.max_closed = True


class ValidationUtil:

    @classmethod
    def get_validation_type(cls, param_def_obj):
        if not param_def_obj:
            return None
        # 获取校验数据的类型
        param_tag_name = param_def_obj.get_tag()
        return cls.get_validation_type_by_tag(param_tag_name)

    @classmethod
    def get_validation_type_by_tag(cls, param_tag_name):
        if param_tag_name in ("ECUC-INTEGER-PARAM-DEF", "ECUC-FLOAT-PARAM-DEF"):
            return ValidationType.VALIDATE_NUMERICAL
        elif param_tag_name in ("ECUC-STRING-PARAM-DEF", "ECUC-FUNCTION-NAME-DEF"):
            return ValidationType.VALIDATE_STRING
        elif param_tag_name in (
            "ECUC-REFERENCE-DEF",
            "ECUC-INSTANCE-REFERENCE-DEF",
            "ECUC-CHOICE-REFERENCE-DEF",
            "ECUC-SYMBOLIC-NAME-REFERENCE-DEF",
            "ECUC-FOREIGN-REFERENCE-DEF",
        ):
            return ValidationType.VALIDATE_STRING_REF
        elif param_tag_name in ("ECUC-ENUMERATION-PARAM-DEF"):
            return ValidationType.VALIDATE_ENUMERATION
        elif param_tag_name in ("SHORT-NAME", "ECUC-PARAM-CONF-CONTAINER-DEF", "ECUC-CHOICE-CONTAINER-DEF"):
            return ValidationType.VALIDATE_CONTAINER_NAME
        else:
            return None

    @classmethod
    def get_mod_name(cls, autosar_ecuc_dict, param_path):
        module_name, instance_name = "", ""
        CONTAINER_PATH_MIN_LEN = 2
        for inst_name, ecuc_obj in autosar_ecuc_dict.items():
            container_name = os.path.dirname(param_path)
            if not ecuc_obj.find(param_path):
                if len(container_name.split("/")) - 1 < CONTAINER_PATH_MIN_LEN or not ecuc_obj.find(container_name):
                    continue
            module_name = cls.get_module_name_by_module_ecuc_obj(ecuc_obj)
            instance_name = inst_name
            break

        return module_name, instance_name

    @classmethod
    def get_module_name_by_module_ecuc_obj(cls, module_ecuc_obj):
        def_ref = get_definition_ref(module_ecuc_obj.find_nodes("ECUC-MODULE-CONFIGURATION-VALUES")[-1]) or ""
        module_name = def_ref.split("/")[-1]
        return module_name

    @classmethod
    def get_param_value_obj(cls, module_ecuc_obj, param_path):
        # TODO: 后续优化方向：container进去后查找一遍然后全部校验
        if not module_ecuc_obj:
            return None
        # 通过param_path去查数据，查类型，查范围等
        param_name = param_path.split("/")[-1]
        container_path = os.path.dirname(param_path)
        container_obj = module_ecuc_obj.find(container_path)

        if param_name == "ShortName":
            return container_obj
        # 遍历所有参数值类型 获取指定的容器的参数对象
        for value_type in ("ECUC_NUMERICAL_PARAM_VALUE", "ECUC_TEXTUAL_PARAM_VALUE", "ECUC_ADD_INFO_PARAM_VALUE"):
            for node in getattr(getattr(container_obj, "PARAMETER_VALUES", None), value_type, []):
                if get_definition_ref(node).split("/")[-1] == param_name:
                    return node
        for ref_type in (
            "ECUC_REFERENCE_VALUE",
            "ECUC_INSTANCE_REFERENCE_VALUE",
            "ECUC_CHOICE_REFERENCE_VALUE",
            "ECUC_SYMBOLIC_NAME_REFERENCE_VALUE",
            "ECUC_FOREIGN_REFERENCE_VALUE",
        ):
            for node in getattr(getattr(container_obj, "REFERENCE_VALUES", None), ref_type, []):
                if get_definition_ref(node).split("/")[-1] == param_name:
                    return node
        return None

    @classmethod
    def get_data_type(cls, param_def_obj):
        # 获取校验数据的类型
        data_type = None
        if param_def_obj is None:
            return data_type
        mod_obj_dest_name = param_def_obj.get_tag()
        return cls.get_data_type_by_tag(mod_obj_dest_name)

    @classmethod
    def get_data_type_by_tag(cls, mod_obj_dest_name):
        data_type = None
        if mod_obj_dest_name == "ECUC-BOOLEAN-PARAM-DEF":
            data_type = "boolean"
        elif mod_obj_dest_name == "ECUC-INTEGER-PARAM-DEF":
            data_type = "integer"
        elif mod_obj_dest_name == "ECUC-FLOAT-PARAM-DEF":
            data_type = "float"
        elif mod_obj_dest_name in ("ECUC-STRING-PARAM-DEF", "ECUC-FUNCTION-NAME-DEF"):
            data_type = "string"
        elif mod_obj_dest_name in (
            "ECUC-REFERENCE-DEF",
            "ECUC-INSTANCE-REFERENCE-DEF",
            "ECUC-CHOICE-REFERENCE-DEF",
            "ECUC-SYMBOLIC-NAME-REFERENCE-DEF",
            "ECUC-FOREIGN-REFERENCE-DEF",
        ):
            data_type = "string_ref"
        elif mod_obj_dest_name in ("ECUC-ENUMERATION-PARAM-DEF"):
            data_type = "enumeration"
        elif mod_obj_dest_name in ("SHORT-NAME", "ECUC-PARAM-CONF-CONTAINER-DEF", "ECUC-CHOICE-CONTAINER-DEF"):
            data_type = "container name"
        else:
            pass
        return data_type

    @classmethod
    def set_range_limit(cls, validation_data: BasicValidationData, param_def_obj):
        if validation_data.data_type == "integer":
            validation_data.min_limit = int(get_min(param_def_obj)) if get_min(param_def_obj) else None
            validation_data.max_limit = int(get_max(param_def_obj)) if get_max(param_def_obj) else None
        elif validation_data.data_type == "float":
            validation_data.min_limit = float(get_min(param_def_obj)) if get_min(param_def_obj) else None
            validation_data.max_limit = float(get_max(param_def_obj)) if get_max(param_def_obj) else None
        elif validation_data.data_type == "string" and param_def_obj:
            validation_data.max_limit = int(get_max_length(param_def_obj)) if get_max_length(param_def_obj) else None
            validation_data.min_limit = int(get_min_length(param_def_obj)) if get_min_length(param_def_obj) else None
        elif validation_data.data_type == "container name" and param_def_obj:
            admin_data = get_admin_data_all(param_def_obj)
            if admin_data:
                min_limit = admin_data.get("VCOS:StringLength", {}).get("VCOS:MinLength", None)
                max_limit = admin_data.get("VCOS:StringLength", {}).get("VCOS:MaxLength", None)
                if isinstance(min_limit, str) and min_limit.isdecimal():
                    validation_data.min_limit = int(min_limit)
                if isinstance(max_limit, str) and max_limit.isdecimal():
                    validation_data.max_limit = int(max_limit)
        # set interval type -> closed or open
        validation_data.max_closed = get_max_interval_type(param_def_obj) == INTERVAL_CLOSED
        validation_data.min_closed = get_min_interval_type(param_def_obj) == INTERVAL_CLOSED

    @classmethod
    def set_multiplicity(cls, validation_data: BasicValidationData, param_def_obj):
        validation_data.lower_multiplicity = get_lower_multiplicity(param_def_obj)
        validation_data.upper_multiplicity = get_upper_multiplicity(param_def_obj)
        validation_data.upper_multiplicity_infinite = get_upper_multiplicity_infinite(param_def_obj)

    @classmethod
    def get_basic_validation_info_by_path(
        cls, autosar_bsw_class, autosar_mod_class, param_path, instance_name, mod_name
    ):
        if not autosar_mod_class:
            return None, None
        # 寻找param_path对应的参数对象
        param_value_obj = ValidationUtil.get_param_value_obj(autosar_bsw_class.get(instance_name), param_path)
        if not param_value_obj:
            logger.warning(f"{param_path} is not found!")
            return None, None

        definition_ref = get_definition_ref(param_value_obj)
        param_def_obj = autosar_mod_class[mod_name].find(definition_ref)
        if not param_def_obj:
            # logger.warning(f"{param_path} is not found!")
            return None, None

        basic_validation_data = BasicValidationData()
        basic_validation_data.param_name = param_path.split("/")[-1]
        basic_validation_data.param_path = param_path
        basic_validation_data.module_name = mod_name
        basic_validation_data.instance_name = instance_name
        basic_validation_data.mod_path = definition_ref

        # 获取被校验的类型
        validation_type = cls.get_validation_type(param_def_obj)
        # 获取被校验参数的类型
        basic_validation_data.data_type = cls.get_data_type(param_def_obj)
        # 获取校验参数的限制信息
        cls.set_range_limit(basic_validation_data, param_def_obj)
        cls.set_multiplicity(basic_validation_data, param_def_obj)

        # 获取校验参数的默认值
        basic_validation_data.default_value = (
            get_default_value(param_def_obj) if get_default_value(param_def_obj) else None
        )

        # 获取校验参数的 字符串
        if validation_type in (
            ValidationType.VALIDATE_NUMERICAL,
            ValidationType.VALIDATE_STRING,
            ValidationType.VALIDATE_ENUMERATION,
        ):
            basic_validation_data.param_value = get_value(param_value_obj)
        elif validation_type == ValidationType.VALIDATE_CONTAINER_NAME:
            basic_validation_data.param_value = basic_validation_data.param_path.split("/")[CONTAINER_NAME_IDX]

        return validation_type, basic_validation_data

    @classmethod
    def get_necessary_flag(cls, basic_validation_data: BasicValidationData) -> bool:
        return basic_validation_data.lower_multiplicity is not None and basic_validation_data.lower_multiplicity > 0

    @classmethod
    def text_is_null(cls, basic_validation_data: BasicValidationData) -> bool:
        return cls.text_is_null_by_text(basic_validation_data.param_value)

    @classmethod
    def text_is_null_by_text(cls, param_value) -> bool:
        return param_value in (None, "", "<empty>")

    @classmethod
    def get_necessary_hint_message(cls):
        return "This is a necessary configuration item, at least one configuration item is required!"

    @classmethod
    def get_basic_validation_info_by_value(cls, autosar_bsw_class, basic_validation_dict):
        if not basic_validation_dict:
            return None, None

        basic_validation_data = BasicValidationData()
        basic_validation_data.param_name = basic_validation_dict.get("param_name")
        basic_validation_data.param_path = basic_validation_dict.get("param_path")
        basic_validation_data.mod_path = basic_validation_dict.get("mod_path")
        basic_validation_data.lower_multiplicity = basic_validation_dict.get("lower_multiplicity")
        basic_validation_data.upper_multiplicity = basic_validation_dict.get("upper_multiplicity")
        basic_validation_data.upper_multiplicity_infinite = basic_validation_dict.get("upper_multiplicity_infinite")
        basic_validation_data.data_type = cls.get_data_type_by_tag(basic_validation_dict.get("tag"))

        if basic_validation_data.data_type == "integer":
            basic_validation_data.max_limit = (
                int(basic_validation_dict.get("max_value")) if basic_validation_dict.get("max_value") else None
            )
            basic_validation_data.min_limit = (
                int(basic_validation_dict.get("min_value")) if basic_validation_dict.get("min_value") else None
            )
        elif basic_validation_data.data_type == "float":
            basic_validation_data.max_limit = (
                float(basic_validation_dict.get("max_value")) if basic_validation_dict.get("max_value") else None
            )
            basic_validation_data.min_limit = (
                float(basic_validation_dict.get("min_value")) if basic_validation_dict.get("min_value") else None
            )
        elif basic_validation_data.data_type in ("string", "container name"):
            basic_validation_data.max_limit = (
                int(basic_validation_dict.get("max_length")) if basic_validation_dict.get("max_length") else None
            )
            basic_validation_data.min_limit = (
                int(basic_validation_dict.get("min_length")) if basic_validation_dict.get("min_length") else None
            )

        basic_validation_data.param_value = basic_validation_dict.get("check_text")
        basic_validation_data.default_value = basic_validation_dict.get("default_value")
        basic_validation_data.max_closed = (
            basic_validation_dict.get("max_interval_type", INTERVAL_CLOSED) == INTERVAL_CLOSED
        )
        basic_validation_data.min_closed = (
            basic_validation_dict.get("min_interval_type", INTERVAL_CLOSED) == INTERVAL_CLOSED
        )

        validation_type = cls.get_validation_type_by_tag(basic_validation_dict.get("tag"))
        basic_validation_data.module_name, basic_validation_data.instance_name = cls.get_mod_name(
            autosar_bsw_class, basic_validation_data.param_path
        )

        return validation_type, basic_validation_data

    @classmethod
    def __get_container_mod_dict(cls, module_mod_obj, container_mod_dict):
        if not module_mod_obj:
            return

        for container_type in ["ECUC_PARAM_CONF_CONTAINER_DEF", "ECUC_CHOICE_CONTAINER_DEF"]:
            for container_mod_obj in getattr(module_mod_obj, container_type, []):
                mod_path = container_mod_obj.get_path()
                container_mod_dict[mod_path] = {}
                container_mod_dict[mod_path]["def"] = container_mod_obj
                cls.__get_container_mod_dict(getattr(container_mod_obj, "SUB_CONTAINERS", None), container_mod_dict)

    @classmethod
    def get_container_mod_def(cls, autosar_mod_class, module_name):
        """
        get container definition detail through autosar_mod_class[module_name] -> {mod_path: definition_obj}
        """
        container_mod_dict = {}
        autosar_module_mod_obj = autosar_mod_class.get(module_name)
        if not autosar_module_mod_obj:
            return container_mod_dict
        autosar_module_mod_obj = autosar_module_mod_obj.find(f"/AUTOSAR/EcucDefs/{module_name}")

        if hasattr(autosar_module_mod_obj, "CONTAINERS"):
            cls.__get_container_mod_dict(autosar_module_mod_obj.CONTAINERS, container_mod_dict)
        elif hasattr(autosar_module_mod_obj, "SUB_CONTAINERS"):
            cls.__get_container_mod_dict(autosar_module_mod_obj.SUB_CONTAINERS, container_mod_dict)

        return container_mod_dict

    @classmethod
    def __get_container_validation_input_dict(cls, autosar_mod_class, autosar_bsw_class, module_name, instance_name):
        """
        construct container count validation input data in module validation
        """
        container_validation_dict = {}
        container_validation_dict["module_ecuc_obj"] = {}
        ecuc_obj = autosar_bsw_class.get(instance_name)
        if ecuc_obj:
            ecuc_obj = ecuc_obj.find(f"/ActiveEcuC/{instance_name}")
        container_validation_dict["module_ecuc_obj"][instance_name] = ecuc_obj
        container_def_dcit = cls.get_container_mod_def(autosar_mod_class, module_name)
        container_validation_dict["container_def_dcit"] = container_def_dcit

        return container_validation_dict

    @classmethod
    def validate_module(
        cls,
        autosar_asw_class,
        autosar_bsw_class,
        autosar_ib_class,
        autosar_mod_class,
        autosar_system_class,
        instance_name,
    ):
        element_data = {}
        validation_result_list = []

        # 获取单个模块下所有的参数信息，合并ref_value为list
        for element in AutosarUtils.get_element_items_by_module_name(autosar_bsw_class, instance_name):
            param_path = f"{element['Element']}/ShortName" if element["Type"] == "Container" else element["Element"]
            if param_path not in element_data:
                element_data.update({param_path: []})
            element_data[param_path].append(element["Value"])
        module_name = cls.get_module_name_by_module_ecuc_obj(autosar_bsw_class.get(instance_name))
        # validate param
        for param_path, param_value in element_data.items():
            validation_type, basic_validation_data = cls.get_basic_validation_info_by_path(
                autosar_bsw_class, autosar_mod_class, param_path, instance_name, module_name
            )
            if not validation_type:
                continue
            validation_result = None
            if validation_type == ValidationType.VALIDATE_NUMERICAL:
                validation_result = ValidationNumRange.validate(basic_validation_data)
                validation_result_list.append(validation_result)
                pass
            elif validation_type in (ValidationType.VALIDATE_STRING, ValidationType.VALIDATE_CONTAINER_NAME):
                validation_result = ValidationStringRange.validate(basic_validation_data)
                validation_result_list.append(validation_result)
                pass
            elif validation_type == ValidationType.VALIDATE_STRING_REF:
                multi_instance_result = ValidationMultiInstance.validate(basic_validation_data, param_value)
                validation_result_list.append(multi_instance_result)

                # reference有效性校验
                ref_valid_result = ValidationRef.validate(
                    autosar_asw_class,
                    autosar_bsw_class,
                    autosar_ib_class,
                    autosar_system_class,
                    autosar_mod_class,
                    basic_validation_data,
                    param_value,
                )
                validation_result_list.append(ref_valid_result)
            elif validation_type == ValidationType.VALIDATE_ENUMERATION:
                validation_result = ValidationEnumerate.validate(
                    autosar_bsw_class, autosar_mod_class, basic_validation_data
                )
                validation_result_list.append(validation_result)

        # validate container count
        # get all container mod info
        container_validation_dict = cls.__get_container_validation_input_dict(
            autosar_mod_class, autosar_bsw_class, module_name, instance_name
        )
        container_validation_ret = cls.validate_container(container_validation_dict, autosar_mod_class)
        validation_result_list.extend(container_validation_ret)

        return validation_result_list

    @classmethod
    def validate_param(
        cls,
        autosar_asw_class,
        autosar_bsw_class,
        autosar_ib_class,
        autosar_system_class,
        autosar_mod_class,
        basic_validation_dict,
    ):
        validation_result_list = []
        validation_type, basic_validation_data = cls.get_basic_validation_info_by_value(
            autosar_bsw_class, basic_validation_dict
        )
        if validation_type == ValidationType.VALIDATE_NUMERICAL:
            validation_result = ValidationNumRange.validate(basic_validation_data)
            validation_result_list.append(validation_result)
        elif validation_type in (ValidationType.VALIDATE_STRING, ValidationType.VALIDATE_CONTAINER_NAME):
            validation_result = ValidationStringRange.validate(basic_validation_data)
            validation_result_list.append(validation_result)
        elif validation_type == ValidationType.VALIDATE_STRING_REF:
            # 多实例校验，需要这个ref_list
            param_ref_list, is_valid = ValidationUtil.get_param_ref_list(
                autosar_bsw_class, basic_validation_data.param_path
            )
            multi_instance_result = ValidationMultiInstance.validate(basic_validation_data, param_ref_list, is_valid)
            validation_result_list.append(multi_instance_result)

            # reference有效性校验
            ref_valid_result = ValidationRef.validate(
                autosar_asw_class,
                autosar_bsw_class,
                autosar_ib_class,
                autosar_system_class,
                autosar_mod_class,
                basic_validation_data,
                param_ref_list,
                is_valid,
            )
            validation_result_list.append(ref_valid_result)
        elif validation_type == ValidationType.VALIDATE_ENUMERATION:
            validation_result = ValidationEnumerate.validate(
                autosar_bsw_class, autosar_mod_class, basic_validation_data
            )
            validation_result_list.append(validation_result)

        return validation_result_list

    @classmethod
    def __get_container_ecuc_dict(cls, ecuc_obj, container_ecuc_dict: dict, parent_mod_path: str):
        if not ecuc_obj:
            return

        parent_path = ecuc_obj.get_path()
        if parent_path not in container_ecuc_dict.keys():
            container_ecuc_dict[parent_path] = {}
            container_ecuc_dict[parent_path]["parent_mod_path"] = parent_mod_path
            container_ecuc_dict[parent_path]["child_item"] = {}
        for container_obj in getattr(ecuc_obj, "ECUC_CONTAINER_VALUE", []):
            mod_path = get_definition_ref(container_obj)
            if not mod_path:
                continue
            if mod_path not in container_ecuc_dict[parent_path]["child_item"].keys():
                container_ecuc_dict[parent_path]["child_item"][mod_path] = []

            container_ecuc_dict[parent_path]["child_item"][mod_path].append(
                {"ecuc_path": container_obj.get_path(), "container_ecuc_obj": container_obj}
            )
            cls.__get_container_ecuc_dict(
                getattr(container_obj, "SUB_CONTAINERS", None),
                container_ecuc_dict,
                get_definition_ref(container_obj),
            )

    @classmethod
    def get_module_container_ecuc_dict(cls, module_ecuc_dict: dict):
        container_ecuc_dict = {}
        instance_name, module_name = None, None
        # just one module
        for instance_name, module_ecuc_obj in module_ecuc_dict.items():
            parent_mod_path = get_definition_ref(module_ecuc_obj)
            module_name = cls.get_module_name_by_module_ecuc_obj(module_ecuc_obj)
            if hasattr(module_ecuc_obj, "CONTAINERS"):
                cls.__get_container_ecuc_dict(module_ecuc_obj.CONTAINERS, container_ecuc_dict, parent_mod_path)
            elif hasattr(module_ecuc_obj, "SUB_CONTAINERS"):
                cls.__get_container_ecuc_dict(module_ecuc_obj.SUB_CONTAINERS, container_ecuc_dict, parent_mod_path)
        return instance_name, module_name, container_ecuc_dict

    @classmethod
    def get_param_lock_info(cls, param_def) -> bool:
        admin_data_list = get_admin_data(param_def)
        is_locked = False
        if admin_data_list:
            for admin_data in admin_data_list:
                if admin_data.get("VCOS:CfgLock", False):
                    is_locked = True
        return is_locked

    @classmethod
    def get_container_def_info_dict(cls, container_def_obj_dict: dict):
        container_def_info_dict = {}
        for mod_path, item_dict in container_def_obj_dict.items():
            container_def_info = item_dict["def"]
            if container_def_info:
                upper_multiplicity = get_upper_multiplicity_infinite(container_def_info)
                if not upper_multiplicity:
                    upper_multiplicity = get_upper_multiplicity(container_def_info)
                container_def = {
                    "lower_multiplicity": get_lower_multiplicity(container_def_info),
                    "upper_multiplicity": upper_multiplicity,
                    "is_locked": cls.get_param_lock_info(container_def_info),
                }
                container_def_info_dict[mod_path] = container_def
        return container_def_info_dict

    @classmethod
    def is_parent_path(self, parent_path: str, child_path: str):
        parent_path_list = parent_path.split("/")
        child_len_list = child_path.split("/")
        if len(parent_path_list) + 1 != len(child_len_list):
            return False
        for node_idx in range(len(parent_path_list)):
            if parent_path_list[node_idx] != child_len_list[node_idx]:
                return False

        return True

    @classmethod
    def validate_container(cls, container_validation_dict, autosar_mod_class):
        validation_result_list = []
        module_ecuc_dict = container_validation_dict["module_ecuc_obj"]
        container_def_dict = container_validation_dict["container_def_dcit"]

        instance_name, module_name, container_ecuc_dict = cls.get_module_container_ecuc_dict(module_ecuc_dict)
        container_def_info_dict = cls.get_container_def_info_dict(container_def_dict)

        for parent_path, ecuc_node_info in container_ecuc_dict.items():
            parent_mod_path = ecuc_node_info.get("parent_mod_path", "")
            if not parent_mod_path:
                continue
            child_item_dict = ecuc_node_info.get("child_item", {})
            for mod_path, container_def in container_def_info_dict.items():
                # if the container cfg is locked, then skip it
                if container_def.get("is_locked"):
                    continue
                if cls.is_parent_path(parent_mod_path, mod_path):
                    child_item_list = child_item_dict.get(mod_path, [])
                    validation_data = cls.get_container_validation_data(
                        child_item_list, container_def, mod_path, instance_name, module_name
                    )
                    if not child_item_list:
                        container_name = mod_path.split("/")[-1]
                        validation_data.param_path = f"{parent_path}/{container_name}"
                    validation_result = ValidationContainerNum.validate(validation_data)
                    validation_result_list.append(validation_result)

        return validation_result_list

    @classmethod
    def get_param_ref_list(cls, autosar_bsw_class, param_path):
        para_ref_list = []
        if not autosar_bsw_class:
            return para_ref_list, False
        _, instance_name = cls.get_mod_name(autosar_bsw_class, param_path)
        param_name = param_path.split("/")[-1]
        container_path = os.path.dirname(param_path)
        if instance_name not in autosar_bsw_class:
            return para_ref_list, False
        container_obj = autosar_bsw_class[instance_name].find(container_path)
        for ref_type in (
            "ECUC_REFERENCE_VALUE",
            "ECUC_INSTANCE_REFERENCE_VALUE",
            "ECUC_CHOICE_REFERENCE_VALUE",
            "ECUC_SYMBOLIC_NAME_REFERENCE_VALUE",
            "ECUC_FOREIGN_REFERENCE_VALUE",
        ):
            for node in getattr(getattr(container_obj, "REFERENCE_VALUES", None), ref_type, []):
                if node is None:
                    continue
                if get_definition_ref(node).split("/")[-1] != param_name:
                    continue

                if getattr(node, "VALUE_REF", None) is not None:
                    para_ref_list.append(get_value_ref(node))
                elif getattr(node, "VALUE_IREF", None) is not None:
                    para_ref_list.append(get_value_iref(node))
        return para_ref_list, True

    @classmethod
    def reference_numer_is_valid(cls, basic_validation_data, ref_num) -> bool:
        # TODO: infinite修改后这里也需要相应地修改
        if basic_validation_data.upper_multiplicity_infinite:
            return (
                basic_validation_data.lower_multiplicity <= ref_num
                and ref_num <= basic_validation_data.upper_multiplicity_infinite
            )
        elif basic_validation_data.upper_multiplicity:
            return (
                basic_validation_data.lower_multiplicity <= ref_num
                and ref_num <= basic_validation_data.upper_multiplicity
            )
        else:
            return True

    @classmethod
    def get_enum_allowed_value(cls, autosar_bsw_class, autosar_mod_class, basic_validation_data) -> list:
        allowed_value_list = []
        if not autosar_mod_class:
            return allowed_value_list
        # get ecuc param obj
        module_name = basic_validation_data.module_name
        instance_name = basic_validation_data.instance_name
        param_path = basic_validation_data.param_path
        param_value_obj = ValidationUtil.get_param_value_obj(autosar_bsw_class.get(instance_name), param_path)
        if not param_value_obj or module_name not in autosar_mod_class:
            logger.warning(f"{param_path} enum allowed value is not found!")
            return allowed_value_list

        definition_ref = get_definition_ref(param_value_obj)
        param_def_obj = autosar_mod_class[module_name].find(definition_ref)

        # get allowed config value in bswmd
        allowed_obj_list = getattr(getattr(param_def_obj, "LITERALS", None), "ECUC_ENUMERATION_LITERAL_DEF", [])
        allowed_value_list = [get_short_name(obj) for obj in allowed_obj_list]

        return allowed_value_list

    @classmethod
    def get_container_validation_data(
        cls, container_ecuc_list, container_def_info_dict, mod_path, instance_name, module_name
    ) -> list:
        basic_validation_data = BasicValidationData()
        basic_validation_data.param_value = container_ecuc_list
        basic_validation_data.instance_name = instance_name
        basic_validation_data.module_name = module_name
        basic_validation_data.mod_path = mod_path
        basic_validation_data.lower_multiplicity = container_def_info_dict["lower_multiplicity"]
        basic_validation_data.upper_multiplicity = container_def_info_dict["upper_multiplicity"]

        return basic_validation_data

    @classmethod
    def is_basic_validation(cls, validation_mark: str) -> bool:
        VALIDATION_CODE_DIGIT_LEN = 6
        VALIDATION_CODE_TYPE_BIT = 1  # validation_mark[-5]: ==>  0: baisc_validation 1/2 -> semantic_validation
        if not validation_mark[-VALIDATION_CODE_DIGIT_LEN:].isdigit():
            logger.warning("input param validation_mark error!")
        validation_type_bit = validation_mark[VALIDATION_CODE_TYPE_BIT - VALIDATION_CODE_DIGIT_LEN]
        return validation_type_bit == 0

    # 使用hash自动修复字符串超长
    @staticmethod
    def update_string_length(param_value: str, max_length, hash_length=8) -> str:
        if param_value and len(param_value) > max_length:
            hash_obj = hashlib.sha1(param_value[(max_length - hash_length - 1) :].encode(encoding="utf-8"))
            hash_str = hash_obj.hexdigest()
            shorten_string = f"{param_value[:(max_length - hash_length - 1)]}_{hash_str[:hash_length]}"
        else:
            shorten_string = param_value
        return shorten_string


class ValidationRef:

    @classmethod
    def get_validation_mark(cls, module_name):
        return module_name.upper() + "000000"

    @classmethod
    def get_validation_summary(cls):
        return "Validation of reference is valid"

    @classmethod
    def get_hint_message(cls, ref_fail_list):
        error_info = "the param reference "
        for ref_value in ref_fail_list:
            error_info += ref_value
            error_info += " "
        error_info += " should exist"
        return error_info

    @classmethod
    def check_ref_type_is_compatible(cls, instance_name, module_name, param_def_ref, dest_ref_list) -> bool:
        # check reference type of param is valid for definition
        ref_type_found = False
        for ref_type in dest_ref_list:
            definition_ref_list, ref_type_list = param_def_ref.split("/"), ref_type.split("/")
            # handle with CanTrcv1145 and CanTrcv
            ref_type_compatible_list = [
                module_name.startswith(ref_type_node) for ref_type_node in ref_type_list if ref_type_node
            ]
            if ref_type and instance_name in definition_ref_list and True in ref_type_compatible_list:
                # prefix: AURIX2G/EcucDefs, AUTOSAR/EcucDefs
                ref_type_prefix_idx = ref_type_compatible_list.index(True) + 2
                def_ref_prefix_idx = definition_ref_list.index(instance_name) + 1
                if ref_type_prefix_idx < len(ref_type_list) and def_ref_prefix_idx < len(definition_ref_list):
                    if ref_type_list[ref_type_prefix_idx:] == definition_ref_list[def_ref_prefix_idx:]:
                        ref_type_found = True
                        break
                else:
                    ref_type_found = True
                    break
        return ref_type_found

    @classmethod
    def check_internal_ref(cls, ref_value, param_def_obj, autosar_bsw_class):
        # internal reference -> search in bsw dict
        ref_type, ref_types = get_destination_ref(param_def_obj), get_destination_refs(param_def_obj)
        ref_module_name, ref_instance_name = ValidationUtil.get_mod_name(autosar_bsw_class, ref_value)
        if not ref_module_name or not ref_instance_name:
            return False
        # CanTrcv1145 -> CanTrcv
        ref_module_name = ValidationUtil.get_module_name_by_module_ecuc_obj(autosar_bsw_class[ref_instance_name])
        if ref_instance_name in autosar_bsw_class.keys() and autosar_bsw_class[ref_instance_name]:
            ref_obj = autosar_bsw_class[ref_instance_name].find(ref_value)
            if not ref_obj:
                return False
            if ref_type:
                if not cls.check_ref_type_is_compatible(
                    ref_instance_name, ref_module_name, get_definition_ref(ref_obj), [ref_type]
                ):
                    return False
            elif ref_types:
                if not cls.check_ref_type_is_compatible(
                    ref_instance_name, ref_module_name, get_definition_ref(ref_obj), ref_types
                ):
                    return False
        else:
            return False
        return True

    @classmethod
    def check_external_ref(
        cls, ref_value, param_def_obj, autosar_bsw_class, autosar_asw_class, autosar_system_class, autosar_ib_class
    ):
        # external reference
        destination_type = get_destination_type(param_def_obj)
        search_obj_list = []

        if "I-SIGNAL-TO-I-PDU-MAPPING" == destination_type:
            # Accept mapping path itself; also allow parent I-SIGNAL-I-PDU for legacy refs.
            # Do not rewrite DEST to I-SIGNAL-I-PDU only (that falsely fails correct mapping paths).
            destination_type = ["I-SIGNAL-TO-I-PDU-MAPPING", "I-SIGNAL-I-PDU"]
            if "Communication" in autosar_system_class:
                search_obj_list.append(autosar_system_class["Communication"])
        elif destination_type in ["SW-ADDR-METHOD", "EXCLUSIVE-AREA", "BSW-MODULE-ENTRY"]:
            search_obj_list.extend(autosar_ib_class.values())
            search_obj_list.append(autosar_asw_class)
        elif "SW-COMPONENT-PROTOTYPE" == destination_type:
            if autosar_asw_class:
                search_obj_list.append(autosar_asw_class)
        elif "SW-COMPONENT-TYPE" == destination_type:
            destination_type = ["APPLICATION-SW-COMPONENT-TYPE", "SERVICE-SW-COMPONENT-TYPE"]
            if autosar_asw_class:
                search_obj_list.append(autosar_asw_class)
        elif destination_type in [
            "COMPU-METHOD",
            "MODE-DECLARATION",
            "DATA-TYPE-MAPPING-SET",
            "MODE-SWITCH-INTERFACE",
            "MODE-DECLARATION-GROUP",
            "VARIABLE-DATA-PROTOTYPE",
            "VARIABLE-ACCESS",
            "SWC-IMPLEMENTATION",
            "ARGUMENT-DATA-PROTOTYPE",
            "IMPLEMENTATION-DATA-TYPE",
        ]:
            if autosar_asw_class:
                search_obj_list.append(autosar_asw_class)
        elif "MODE-DECLARATION-GROUP-PROTOTYPE" == destination_type:
            destination_type = "MODE-GROUP"
            if autosar_asw_class:
                search_obj_list.append(autosar_asw_class)
        elif "RTE-EVENT" == destination_type:
            destination_type = [
                "ASYNCHRONOUS-SERVER-CALL-RETURNS-EVENT",
                "BACKGROUND-EVENT",
                "DATA-RECEIVE-ERROR-EVENT",
                "DATA-RECEIVED-EVENT",
                "DATA-SEND-COMPLETED-EVENT",
                "DATA-WRITE-COMPLETED-EVENT",
                "EXTERNAL-TRIGGER-OCCURRED-EVENT",
                "INIT-EVENT",
                "INTERNAL-TRIGGER-OCCURRED-EVENT",
                "MODE-SWITCHED-ACK-EVENT",
                "OPERATION-INVOKED-EVENT",
                "SWC-MODE-MANAGER-ERROR-EVENT",
                "SWC-MODE-SWITCH-EVENT",
                "TIMING-EVENT",
                "TRANSFORMER-HARD-ERROR-EVENT",
            ]
            if autosar_asw_class:
                search_obj_list.append(autosar_asw_class)
        elif "BSW-EVENT" == destination_type:
            destination_type = [
                "BSW-ASYNCHRONOUS-SERVER-CALL-RETURNS-EVENT",
                "BSW-BACKGROUND-EVENT",
                "BSW-DATA-RECEIVED-EVENT",
                "BSW-EXTERNAL-TRIGGER-OCCURRED-EVENT",
                "BSW-INTERNAL-TRIGGER-OCCURRED-EVENT",
                "BSW-MODE-MANAGER-ERROR-EVENT",
                "BSW-MODE-SWITCHED-ACK-EVENT",
                "BSW-MODE-SWITCH-EVENT",
                "BSW-OPERATION-INVOKED-EVENT",
                "BSW-TIMING-EVENT",
            ]
            search_obj_list.extend(autosar_ib_class.values())
        else:
            if autosar_asw_class:
                search_obj_list.append(autosar_asw_class)
            if "Communication" in autosar_system_class:
                search_obj_list.append(autosar_system_class["Communication"])
            if "FlatExtract" in autosar_system_class:
                search_obj_list.append(autosar_system_class["FlatExtract"])
            search_obj_list.extend(autosar_bsw_class.values())
            search_obj_list.extend(autosar_ib_class.values())

        # search configured value
        ref_is_compatiable = False
        for search_obj in search_obj_list:
            ref_value_obj = search_obj.find(ref_value)
            if not ref_value_obj:
                continue
            ref_type = ref_value_obj.get_tag()
            if isinstance(destination_type, list):
                ref_is_compatiable = bool(ref_type in destination_type)
            else:
                ref_is_compatiable = bool(ref_type == destination_type)
            break

        return ref_is_compatiable

    @classmethod
    def validate(
        cls,
        autosar_asw_class,
        autosar_bsw_class,
        autosar_ib_class,
        autosar_system_class,
        autosar_mod_class,
        basic_validation_data,
        ref_value_list,
        is_ref_value_valid=True,
    ):
        if not is_ref_value_valid:
            return None
        ref_fail_list = []
        param_path = basic_validation_data.param_path
        # 只要配置了引用参数(非空)就必须校验，以满足移除模块后引用被删除模块的报错提示
        for ref_value in ref_value_list:
            # 引用校验不包括空文本
            if ValidationUtil.text_is_null_by_text(ref_value):
                continue

            param_def_obj = autosar_mod_class[basic_validation_data.module_name].find(basic_validation_data.mod_path)
            if param_def_obj.get_tag() in [
                "ECUC-SYMBOLIC-NAME-REFERENCE-DEF",
                "ECUC-REFERENCE-DEF",
                "ECUC-CHOICE-REFERENCE-DEF",
            ]:
                # internal reference
                if not cls.check_internal_ref(ref_value, param_def_obj, autosar_bsw_class):
                    ref_fail_list.append(ref_value)
            elif param_def_obj.get_tag() in ["ECUC-FOREIGN-REFERENCE-DEF", "ECUC-INSTANCE-REFERENCE-DEF"]:
                # foreign reference
                if not cls.check_external_ref(
                    ref_value,
                    param_def_obj,
                    autosar_bsw_class,
                    autosar_asw_class,
                    autosar_system_class,
                    autosar_ib_class,
                ):
                    ref_fail_list.append(ref_value)
        validation_status = "pass" if not ref_fail_list else "fail"

        auto_solve_list = []
        manual_solve_list = []
        if (
            basic_validation_data.upper_multiplicity_infinite
            or basic_validation_data.upper_multiplicity - len(ref_fail_list) >= basic_validation_data.lower_multiplicity
        ):
            ref_name_list = [ref_value.split("/")[-1] for ref_value in ref_fail_list]

            auto_solve_list = [
                {
                    "solve_info": f"Delete reference {ref_name_list}",
                    "solve_type": "DeleteReference",
                    "parameter": basic_validation_data.mod_path,
                    "value": ref_fail_list,
                }
            ]
        else:
            manual_solve_list = ["Please select a valid reference in the pop-up window after clicking '[...]'"]

        return ValidationResult(
            cls.get_validation_mark(basic_validation_data.module_name),
            cls.get_validation_summary(),
            cls.get_hint_message(ref_fail_list),
            [param_path],
            validation_status,
            auto_solve_list,
            manual_solve_list,
        )


class ValidationMultiInstance:

    @classmethod
    def get_validation_mark(cls, module_name):
        return module_name.upper() + "001000"

    @classmethod
    def get_validation_summary(cls, is_check_none=False):
        return "Validation of multi instance" if not is_check_none else "Validation of empty configuration"

    @classmethod
    def get_hint_message(cls, basic_validation_data: BasicValidationData):
        error_info = "the number of configuration items is between "
        error_info += f"{basic_validation_data.lower_multiplicity} ~ {basic_validation_data.upper_multiplicity}"
        return error_info

    @classmethod
    def get_error_hint_message(cls, is_check_none=False):
        none_hint_message = "the gray background line is an empty configuration item, please check"
        error_info = "the param for validation is wrong" if not is_check_none else none_hint_message
        return error_info

    @classmethod
    def validate(cls, basic_validation_data: BasicValidationData, param_ref_list, is_ref_valid=True):
        validation_status = "fail"
        # 当输入数据不合法时，直接返回一个校验错误
        if not is_ref_valid:
            return ValidationResult(
                cls.get_validation_mark(basic_validation_data.module_name),
                cls.get_validation_summary(),
                cls.get_error_hint_message(),
                [basic_validation_data.param_path],
                "fail",
            )

        param_sub_ref_list = [x for x in param_ref_list if not ValidationUtil.text_is_null_by_text(x)]
        # 当同时存在None和有效值时是非法的
        if len(param_ref_list) > 1 and len(param_sub_ref_list) != len(param_ref_list):
            validation_mark = cls.get_validation_mark(basic_validation_data.module_name)
            return ValidationResult(
                validation_mark,
                cls.get_validation_summary(is_check_none=True),
                cls.get_error_hint_message(is_check_none=True),
                [basic_validation_data.param_path],
                validation_status,
            )

        validation_message = cls.get_hint_message(basic_validation_data)
        ref_num = len(param_sub_ref_list)
        # 引用个数合法，或者引用个数为0且是非必要项时，校验通过
        if ref_num > 0:
            if ValidationUtil.reference_numer_is_valid(basic_validation_data, ref_num):
                validation_status = "pass"
        elif ref_num == 0:
            if not ValidationUtil.get_necessary_flag(basic_validation_data):
                validation_status = "pass"
            else:
                validation_message = ValidationUtil.get_necessary_hint_message()

        return ValidationResult(
            cls.get_validation_mark(basic_validation_data.module_name),
            cls.get_validation_summary(),
            validation_message,
            [basic_validation_data.param_path],
            validation_status,
        )


class ValidationNumRange:

    @classmethod
    def get_validation_mark(cls, module_name):
        return module_name.upper() + "002000"

    @classmethod
    def get_validation_summary(cls):
        return "Validation of numerical range"

    @classmethod
    def get_hint_message(cls, basic_validation_data: BasicValidationData):
        error_info = f"the range of {basic_validation_data.data_type} is "
        error_info += "[" if basic_validation_data.min_closed else "("
        error_info += f"{basic_validation_data.min_limit}, {basic_validation_data.max_limit}"
        error_info += "]" if basic_validation_data.max_closed else ")"
        return error_info

    @classmethod
    def value_out_of_range_judge(cls, validation_data: BasicValidationData):
        out_of_range = False
        # NOTE: 原有逻辑就是这样，但line_edit控件的输入控制拒接负数
        regex_hex = r"^[+-]?0[xX][0-9a-fA-F]+"
        regex_oct = r"^[+-]?0[oO][0-7]+"
        regex_bin = r"^[+-]?0[bB][0-1]+"
        regex_dec = r"^[+-]?\d+"

        if validation_data.max_limit is None or validation_data.min_limit is None:
            return out_of_range
        param_value = None
        # 整形数据校验
        if validation_data.data_type == "integer":
            if re.fullmatch(regex_hex, validation_data.param_value):
                param_value = int(validation_data.param_value, base=16)
            elif re.fullmatch(regex_oct, validation_data.param_value):
                param_value = int(validation_data.param_value, base=8)
            elif re.fullmatch(regex_bin, validation_data.param_value):
                param_value = int(validation_data.param_value, base=2)
            elif re.fullmatch(regex_dec, validation_data.param_value):
                param_value = int(validation_data.param_value, base=10)
            else:
                param_value = validation_data.min_limit - 1
        # 浮点型数据校验
        elif validation_data.data_type == "float":
            param_value = float(validation_data.param_value)

        if param_value is not None:
            if validation_data.min_closed and validation_data.max_closed:
                out_of_range = param_value < validation_data.min_limit or param_value > validation_data.max_limit
            elif validation_data.min_closed:
                out_of_range = param_value < validation_data.min_limit or param_value >= validation_data.max_limit
            elif validation_data.max_closed:
                out_of_range = param_value <= validation_data.min_limit or param_value > validation_data.max_limit
            else:
                out_of_range = param_value <= validation_data.min_limit or param_value >= validation_data.max_limit

        return out_of_range

    @classmethod
    def validate(cls, basic_validation_data):
        validation_status = "fail"
        validation_message = cls.get_hint_message(basic_validation_data)
        # 字符串非空
        if not ValidationUtil.text_is_null(basic_validation_data):
            if not cls.value_out_of_range_judge(basic_validation_data):
                validation_status = "pass"
        else:
            # 字符串为空 且 是必要配置项，则校验失败
            if ValidationUtil.get_necessary_flag(basic_validation_data):
                validation_message = ValidationUtil.get_necessary_hint_message()
            else:
                validation_status = "pass"

        # 添加校验错误一键解决信息
        auto_solve_list = []
        manual_solve_list = []
        if validation_status == "fail":
            if basic_validation_data.default_value is not None:
                auto_solve_default_dict = {
                    "solve_info": (
                        f"Set {basic_validation_data.param_name} (value={basic_validation_data.param_value}) "
                        f"to default (value={basic_validation_data.default_value})"
                    ),
                    "solve_type": "SetValue",
                    "parameter": basic_validation_data.param_path,
                    "value": basic_validation_data.default_value,
                }
                auto_solve_list.append(auto_solve_default_dict)
            if basic_validation_data.min_limit is not None and basic_validation_data.min_closed:
                auto_solve_minimum_dict = {
                    "solve_info": (
                        f"Set {basic_validation_data.param_name} (value={basic_validation_data.param_value}) "
                        f"to minimum (value={basic_validation_data.min_limit})"
                    ),
                    "solve_type": "SetValue",
                    "parameter": basic_validation_data.param_path,
                    "value": str(basic_validation_data.min_limit),
                }
                auto_solve_list.append(auto_solve_minimum_dict)
            if basic_validation_data.max_limit is not None and basic_validation_data.max_closed:
                auto_solve_maximum_dict = {
                    "solve_info": (
                        f"Set {basic_validation_data.param_name} (value={basic_validation_data.param_value}) "
                        f"to maximum (value={basic_validation_data.max_limit})"
                    ),
                    "solve_type": "SetValue",
                    "parameter": basic_validation_data.param_path,
                    "value": str(basic_validation_data.max_limit),
                }
                auto_solve_list.append(auto_solve_maximum_dict)

        return ValidationResult(
            cls.get_validation_mark(basic_validation_data.module_name),
            cls.get_validation_summary(),
            validation_message,
            [basic_validation_data.param_path],
            validation_status,
            auto_solve_list,
            manual_solve_list,
        )


# 字符串长度，针对字符串长度超限这种情况，fail同样是两种
class ValidationStringRange:

    @classmethod
    def get_validation_mark(cls, module_name):
        return module_name.upper() + "003000"

    @classmethod
    def get_validation_summary(cls):
        return "Validation of string configuration item"

    @classmethod
    def get_hint_message(cls, basic_validation_data: BasicValidationData):
        error_info = f"the data length of {basic_validation_data.data_type} type should be between "
        error_info += f"{basic_validation_data.min_limit} ~ {basic_validation_data.max_limit}"
        return error_info

    @classmethod
    def string_out_of_range_judge(cls, basic_validation_data):
        outOfRangeIndex_name = False
        if (
            basic_validation_data.data_type in ("string", "container name")
            and basic_validation_data.max_limit is not None
            and basic_validation_data.min_limit is not None
        ):
            outOfRangeIndex_name = (
                len(basic_validation_data.param_value) > basic_validation_data.max_limit
                or len(basic_validation_data.param_value) < basic_validation_data.min_limit
            )
            return outOfRangeIndex_name

    @classmethod
    def validate(cls, basic_validation_data):
        validation_status = "fail"
        validation_message = cls.get_hint_message(basic_validation_data)
        # 字符串非空
        if not ValidationUtil.text_is_null(basic_validation_data):
            # 判定字符串长度是否符合要求
            if not cls.string_out_of_range_judge(basic_validation_data):
                validation_status = "pass"
        else:
            # 字符串为空 且 是必要配置项，则校验失败
            if ValidationUtil.get_necessary_flag(basic_validation_data):
                validation_message = ValidationUtil.get_necessary_hint_message()
            else:
                validation_status = "pass"

        auto_solve_list = []
        manual_solve_list = []
        if (
            not ValidationUtil.text_is_null(basic_validation_data)
            and basic_validation_data.max_limit is not None
            and len(basic_validation_data.param_value) > basic_validation_data.max_limit
        ):
            auto_solve_list = [
                {
                    "solve_info": f"Use UUID to shorten '{basic_validation_data.param_name}' length",
                    "solve_type": "SetValue",
                    "parameter": basic_validation_data.param_path,
                    "value": ValidationUtil.update_string_length(
                        basic_validation_data.param_value, basic_validation_data.max_limit
                    ),
                }
            ]
            manual_solve_list = [
                f"Shorten {basic_validation_data.param_name} length less then {basic_validation_data.max_limit}"
            ]

        return ValidationResult(
            cls.get_validation_mark(basic_validation_data.module_name),
            cls.get_validation_summary(),
            validation_message,
            [basic_validation_data.param_path],
            validation_status,
            auto_solve_list,
            manual_solve_list,
        )


# validate enumeration config items
class ValidationEnumerate:

    @classmethod
    def get_validation_mark(cls, module_name):
        return module_name.upper() + "004000"

    @classmethod
    def get_validation_summary(cls):
        return "Validation of enumeration items"

    @classmethod
    def get_hint_message(cls, basic_validation_data: BasicValidationData):
        return f"enumeration config item value: {basic_validation_data.param_value} is illegal"

    @classmethod
    def validate(cls, autosar_bsw_class, autosar_mod_class, basic_validation_data):
        validation_status = "fail"
        validation_message = cls.get_hint_message(basic_validation_data)

        # enum config item value is empty
        if ValidationUtil.text_is_null(basic_validation_data):
            # is necessary config item
            if ValidationUtil.get_necessary_flag(basic_validation_data):
                validation_message = ValidationUtil.get_necessary_hint_message()
            else:
                validation_status = "pass"
        else:
            # config value must in allowed value list
            allowed_config_values = ValidationUtil.get_enum_allowed_value(
                autosar_bsw_class, autosar_mod_class, basic_validation_data
            )
            if basic_validation_data.param_value in allowed_config_values:
                validation_status = "pass"

        return ValidationResult(
            cls.get_validation_mark(basic_validation_data.module_name),
            cls.get_validation_summary(),
            validation_message,
            [basic_validation_data.param_path],
            validation_status,
        )


# validate container count
class ValidationContainerNum:

    @classmethod
    def get_validation_mark(cls, module_name):
        return module_name.upper() + "001000"

    @classmethod
    def get_validation_summary(cls):
        return "Validation of multi instance of container"

    @classmethod
    def get_hint_message(cls, mode_path, lower_limit, upper_limit):
        return f"The number of containers for {mode_path} should be between {lower_limit} and {upper_limit}."

    @classmethod
    def get_param_path(cls, mode_path, module_name):
        index = mode_path.find("/" + module_name)
        result_path = mode_path[index:]
        return result_path

    @classmethod
    def validate(cls, basic_validation_data: BasicValidationData):
        validation_status = "pass"
        sub_container_num = len(basic_validation_data.param_value)

        if (
            sub_container_num < basic_validation_data.lower_multiplicity
            or sub_container_num > basic_validation_data.upper_multiplicity
        ):
            validation_status = "fail"

        container_list = basic_validation_data.param_value
        param_path_list = []
        for i in range(len(container_list)):
            param_path_list.append(container_list[i]["ecuc_path"])
        if not param_path_list:
            param_path_list.append(basic_validation_data.param_path)

        # param_path = cls.get_param_path(basic_validation_data.mod_path, basic_validation_data.module_name)
        param_path = basic_validation_data.mod_path
        validation_message = cls.get_hint_message(
            param_path, basic_validation_data.lower_multiplicity, basic_validation_data.upper_multiplicity
        )
        validation_mark = cls.get_validation_mark(basic_validation_data.module_name)

        auto_solve_list = []
        manual_solve_list = []
        if validation_status == "fail":
            if sub_container_num < basic_validation_data.lower_multiplicity:
                create_num = basic_validation_data.lower_multiplicity - len(basic_validation_data.param_value)
                auto_solve_list = [
                    {
                        "solve_info": f"Create {create_num} {param_path} container(s)",
                        "solve_type": "CreateContainer",
                        "parameter": basic_validation_data.mod_path,
                        "value": f"{create_num}",
                    }
                ]
                manual_solve_list = [f"Create {create_num} {param_path} container(s) manually"]
            else:
                delete_num = len(basic_validation_data.param_value) - basic_validation_data.upper_multiplicity
                manual_solve_list = [f"Delete {delete_num} {param_path} container(s) manually"]

        return ValidationResult(
            validation_mark,
            cls.get_validation_summary(),
            validation_message,
            param_path_list,
            validation_status,
            auto_solve_list,
            manual_solve_list,
        )
