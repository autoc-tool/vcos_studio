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
import inspect
from func_module.health_monitor.logger import logger
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.autosar_utils.utils import (
    get_admin_data,
    get_definition_ref,
    set_value,
    set_value_ref,
    set_value_iref,
    get_value,
    get_value_ref,
    get_value_iref,
    get_default_value,
    get_short_name,
)


def get_ref(obj):
    tag = obj.get_tag()
    if tag == "ECUC-REFERENCE-VALUE":
        return get_value_ref(obj)
    elif tag == "ECUC-INSTANCE-REFERENCE-VALUE":
        return get_value_iref(obj)
    else:
        logger.debug(f"{__file__}:{inspect.currentframe().f_lineno}    Unsupported value obj tag {tag}")


def set_ref(obj, val):
    tag = obj.get_tag()
    if tag == "ECUC-REFERENCE-VALUE":
        return set_value_ref(obj, val)
    elif tag == "ECUC-INSTANCE-REFERENCE-VALUE":
        return set_value_iref(obj, val)
    else:
        logger.debug(f"{__file__}:{inspect.currentframe().f_lineno}    Unsupported value obj tag {tag}")


def check_container_reference(container_def_obj, cfg_lock_obj_dict: dict):
    references_obj = getattr(container_def_obj, "REFERENCES", None)
    ref_def_list = []
    ref_def_list += getattr(references_obj, "ECUC_CHOICE_REFERENCE_DEF", [])
    ref_def_list += getattr(references_obj, "ECUC_FOREIGN_REFERENCE_DEF", [])
    ref_def_list += getattr(references_obj, "ECUC_INSTANCE_REFERENCE_DEF", [])
    ref_def_list += getattr(references_obj, "ECUC_REFERENCE_DEF", [])
    ref_def_list += getattr(references_obj, "ECUC_SYMBOLIC_NAME_REFERENCE_DEF", [])

    for ref_def in ref_def_list:
        admin_data = get_admin_data(ref_def)
        if admin_data is not None and {"VCOS:CfgLock": "true"} in admin_data:
            cfg_lock_obj_dict["refs"].append(ref_def)


def check_container_parameter(container_def_obj, cfg_lock_obj_dict: dict):
    parameters_obj = getattr(container_def_obj, "PARAMETERS", None)
    param_def_list = []
    param_def_list += getattr(parameters_obj, "ECUC_ADD_INFO_PARAM_DEF", [])
    param_def_list += getattr(parameters_obj, "ECUC_BOOLEAN_PARAM_DEF", [])
    param_def_list += getattr(parameters_obj, "ECUC_ENUMERATION_PARAM_DEF", [])
    param_def_list += getattr(parameters_obj, "ECUC_FLOAT_PARAM_DEF", [])
    param_def_list += getattr(parameters_obj, "ECUC_FUNCTION_NAME_DEF", [])
    param_def_list += getattr(parameters_obj, "ECUC_INTEGER_PARAM_DEF", [])
    param_def_list += getattr(parameters_obj, "ECUC_LINKER_SYMBOL_DEF", [])
    param_def_list += getattr(parameters_obj, "ECUC_MULTILINE_STRING_PARAM_DEF", [])
    param_def_list += getattr(parameters_obj, "ECUC_STRING_PARAM_DEF", [])

    for param_def in param_def_list:
        admin_data = get_admin_data(param_def)
        if admin_data is not None and {"VCOS:CfgLock": "true"} in admin_data:
            cfg_lock_obj_dict["params"].append(param_def)


def check_param_conf_container(container_def_obj, cfg_lock_obj_dict: dict):
    if container_def_obj is None:
        return

    admin_data = get_admin_data(container_def_obj)
    if admin_data is not None and {"VCOS:CfgLock": "true"} in admin_data:
        cfg_lock_obj_dict["containers"].append(container_def_obj)

    check_container_parameter(container_def_obj, cfg_lock_obj_dict)
    check_container_reference(container_def_obj, cfg_lock_obj_dict)

    sub_containers_obj = getattr(container_def_obj, "SUB_CONTAINERS", None)
    param_container_def_list = []
    param_container_def_list += getattr(sub_containers_obj, "ECUC_PARAM_CONF_CONTAINER_DEF", [])
    for sub_container_def_obj in param_container_def_list:
        check_param_conf_container(sub_container_def_obj, cfg_lock_obj_dict)

    choice_container_def_list = []
    choice_container_def_list += getattr(sub_containers_obj, "ECUC_CHOICE_CONTAINER_DEF", [])
    for sub_container_def_obj in choice_container_def_list:
        check_choice_container(sub_container_def_obj, cfg_lock_obj_dict)


def check_choice_container(container_def_obj, cfg_lock_obj_dict):
    admin_data = get_admin_data(container_def_obj)
    if admin_data is not None and {"VCOS:CfgLock": "true"} in admin_data:
        cfg_lock_obj_dict["containers"].append(container_def_obj)

    choices_obj = getattr(container_def_obj, "CHOICES", None)
    param_container_def_list = []
    param_container_def_list += getattr(choices_obj, "ECUC_PARAM_CONF_CONTAINER_DEF", [])
    for container_def in param_container_def_list:
        check_param_conf_container(container_def, cfg_lock_obj_dict)


def gather_cfg_locks(bswmd_obj):
    elements_obj = getattr(bswmd_obj.find("/AUTOSAR/EcucDefs"), "ELEMENTS", None)
    ecuc_module_def_obj = getattr(elements_obj, "ECUC_MODULE_DEF", [None])[0]

    cfg_lock_obj_dict = {"containers": [], "params": [], "refs": []}

    if ecuc_module_def_obj:
        containers_obj = getattr(ecuc_module_def_obj, "CONTAINERS", None)

        # Iterate all sub containers, collect CfgLock
        param_conf_container_def_list = []
        param_conf_container_def_list += getattr(containers_obj, "ECUC_PARAM_CONF_CONTAINER_DEF", [])
        for sub_container_def_obj in param_conf_container_def_list:
            check_param_conf_container(sub_container_def_obj, cfg_lock_obj_dict)

        choice_container_def_list = []
        choice_container_def_list += getattr(containers_obj, "ECUC_CHOICE_CONTAINER_DEF", [])
        for sub_container_def_obj in choice_container_def_list:
            check_choice_container(sub_container_def_obj, cfg_lock_obj_dict)

    return cfg_lock_obj_dict


class EcucArxmlUpdater:

    def __init__(self, bswmd_obj, ecuc_obj) -> None:
        self.bswmd_obj = bswmd_obj
        self.ecuc_obj = ecuc_obj

    def get_param_def_list(self, container_def):
        param_def_list = []
        param_def_list += getattr(getattr(container_def, "PARAMETERS", None), "ECUC_ADD_INFO_PARAM_DEF", [])
        param_def_list += getattr(getattr(container_def, "PARAMETERS", None), "ECUC_BOOLEAN_PARAM_DEF", [])
        param_def_list += getattr(getattr(container_def, "PARAMETERS", None), "ECUC_ENUMERATION_PARAM_DEF", [])
        param_def_list += getattr(getattr(container_def, "PARAMETERS", None), "ECUC_FLOAT_PARAM_DEF", [])
        param_def_list += getattr(getattr(container_def, "PARAMETERS", None), "ECUC_FUNCTION_NAME_DEF", [])
        param_def_list += getattr(getattr(container_def, "PARAMETERS", None), "ECUC_INTEGER_PARAM_DEF", [])
        param_def_list += getattr(getattr(container_def, "PARAMETERS", None), "ECUC_LINKER_SYMBOL_DEF", [])
        param_def_list += getattr(getattr(container_def, "PARAMETERS", None), "ECUC_MULTILINE_STRING_PARAM_DEF", [])
        param_def_list += getattr(getattr(container_def, "PARAMETERS", None), "ECUC_STRING_PARAM_DEF", [])

        return param_def_list

    def get_param_val_list(self, container_obj):
        parameter_vals_obj = getattr(container_obj, "PARAMETER_VALUES", None)
        param_val_list = []
        param_val_list += getattr(parameter_vals_obj, "ECUC_ADD_INFO_PARAM_VALUE", [])
        param_val_list += getattr(parameter_vals_obj, "ECUC_NUMERICAL_PARAM_VALUE", [])
        param_val_list += getattr(parameter_vals_obj, "ECUC_TEXTUAL_PARAM_VALUE", [])
        return param_val_list

    def check_param_instance(self, container_obj, container_def):
        param_def_list = self.get_param_def_list(container_def)
        # If container has parameter definition, but not PARAMETER_VALUES obj, create one
        if param_def_list and not container_obj.PARAMETER_VALUES:
            container_obj.PARAMETER_VALUES = AutosarUtil.create_parameter_values([], container_obj)

        param_val_list = self.get_param_val_list(container_obj)

        existed_instance = set(get_definition_ref(param_val).split("/")[-1] for param_val in param_val_list)
        for param_def in param_def_list:
            if get_short_name(param_def) not in existed_instance:
                if param_vals := getattr(container_obj, "PARAMETER_VALUES", None):
                    AutosarUtil.set_parameter(param_vals, param_def)

    def update_parameter(self, container_obj, container_def):
        # 1. Check and add param instance
        self.check_param_instance(container_obj, container_def)

        # 2. Update param values with defaul values
        param_val_list = self.get_param_val_list(container_obj)
        self.update_default_param(param_val_list)

    def update_default_param(self, param_val_list):
        for param_val in param_val_list:
            # 1. If definition has "CfgLock", set to the default value
            def_ref_path = get_definition_ref(param_val)
            def_obj = self.bswmd_obj.find(def_ref_path)
            admin_data = get_admin_data(def_obj)
            if admin_data is not None and {"VCOS:CfgLock": "true"} in admin_data:
                # If admin data has CfgValue, set to this value
                if len(cfg_value_list := list(filter(lambda ele: "VCOS:CfgValue" in ele, admin_data))) > 0:
                    val = cfg_value_list[0]["VCOS:CfgValue"]
                    set_value(param_val, val)
                    continue
                # If no CfgValue but default value
                elif (val := get_default_value(def_obj)) is not None:
                    set_value(param_val, val)
                    continue
                else:
                    continue

            # 2. If value is None, fill with default value
            if get_value(param_val) is None:
                if (val := get_default_value(def_obj)) is not None:
                    set_value(param_val, val)
                    continue

    def get_ref_val_list(self, container_obj):
        ref_vals_obj = getattr(container_obj, "REFERENCE_VALUES", None)
        ref_val_list = []
        ref_val_list += getattr(ref_vals_obj, "ECUC_INSTANCE_REFERENCE_VALUE", [])
        ref_val_list += getattr(ref_vals_obj, "ECUC_REFERENCE_VALUE", [])
        return ref_val_list

    def get_ref_def_list(self, container_def):
        ref_def_list = []
        ref_def_list += getattr(getattr(container_def, "REFERENCES", None), "ECUC_CHOICE_REFERENCE_DEF", [])
        ref_def_list += getattr(getattr(container_def, "REFERENCES", None), "ECUC_FOREIGN_REFERENCE_DEF", [])
        ref_def_list += getattr(getattr(container_def, "REFERENCES", None), "ECUC_INSTANCE_REFERENCE_DEF", [])
        ref_def_list += getattr(getattr(container_def, "REFERENCES", None), "ECUC_REFERENCE_DEF", [])
        ref_def_list += getattr(getattr(container_def, "REFERENCES", None), "ECUC_SYMBOLIC_NAME_REFERENCE_DEF", [])
        # ref_def_list += getattr(getattr(container_def, "REFERENCES", None), "ECUC_URI_REFERENCE_DEF", [])x``
        return ref_def_list

    def check_ref_instance(self, container_obj, container_def):
        ref_def_list = self.get_ref_def_list(container_def)
        # If container has reference definition, but not REFERENCE_VALUES obj, create one
        if ref_def_list and not container_obj.REFERENCE_VALUES:
            container_obj.REFERENCE_VALUES = AutosarUtil.create_reference_values([], container_obj)

        ref_val_list = self.get_ref_val_list(container_obj)

        existed_instance = set(get_definition_ref(ref_val).split("/")[-1] for ref_val in ref_val_list)
        for ref_def in ref_def_list:
            if get_short_name(ref_def) not in existed_instance:
                if ref_vals := getattr(container_obj, "REFERENCE_VALUES", None):
                    AutosarUtil.set_reference(ref_vals, ref_def)

    def update_reference(self, container_obj, container_def):
        # 1. Check and add ref instance
        self.check_ref_instance(container_obj, container_def)

        # 2. Update ref values with defaul values
        ref_val_list = self.get_ref_val_list(container_obj)
        self.update_default_ref(ref_val_list)

    def update_default_ref(self, ref_val_list):
        for ref_val in ref_val_list:
            # 1. If definition has "CfgLock", set to the default value
            def_ref_path = get_definition_ref(ref_val)
            def_obj = self.bswmd_obj.find(def_ref_path)
            admin_data = get_admin_data(def_obj)

            if admin_data is not None and {"VCOS:CfgLock": "true"} in admin_data:
                # If admin data has CfgValue, set to this value
                if len(cfg_value_list := list(filter(lambda ele: "VCOS:CfgValue" in ele, admin_data))) > 0:
                    val = cfg_value_list[0]["VCOS:CfgValue"]
                    set_ref(ref_val, val)
                    continue
                # If no CfgValue but default value
                elif (val := get_default_value(def_obj)) is not None:
                    set_ref(ref_val, val)
                    continue
                else:
                    continue

            # 2. 如果ref value是"<empty>"或"",将Value设置为None
            if get_ref(ref_val) in ["<empty>", ""]:
                set_ref(ref_val, None)

            # 3. If value is None, fill with default value
            if get_ref(ref_val) is None:
                if (val := get_default_value(def_obj)) is not None:
                    set_ref(ref_val, val)
                    continue

    def update_container(self, container_obj):
        if container_obj is None:
            return

        container_def_path = get_definition_ref(container_obj)
        container_def = self.bswmd_obj.find(container_def_path)

        self.update_parameter(container_obj, container_def)
        self.update_reference(container_obj, container_def)

        sub_containers_obj = getattr(container_obj, "SUB_CONTAINERS", None)
        container_val_list = []
        container_val_list += getattr(sub_containers_obj, "ECUC_CONTAINER_VALUE", [])
        for container_obj in container_val_list:
            self.update_container(container_obj)

    def update_ecuc_with_default_value(self):
        """
        Update ecuc.arxml according to CfgValue and default value of given bswmd.arxml
        """
        elements_obj = getattr(self.ecuc_obj.find("/ActiveEcuC"), "ELEMENTS", None)
        module_cfg_val_obj_list = getattr(elements_obj, "ECUC_MODULE_CONFIGURATION_VALUES", [None])
        module_cfg_val_obj = None
        if len(module_cfg_val_obj_list) > 0:
            module_cfg_val_obj = module_cfg_val_obj_list[0]
        # module_name = get_short_name(module_cfg_val_obj)

        containers_obj = getattr(module_cfg_val_obj, "CONTAINERS", None)
        container_val_list = []
        container_val_list += getattr(containers_obj, "ECUC_CONTAINER_VALUE", [])
        for container_obj in container_val_list:
            self.update_container(container_obj)
        pass
