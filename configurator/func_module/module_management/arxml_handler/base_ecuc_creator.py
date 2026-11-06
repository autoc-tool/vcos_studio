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
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.autosar_utils.autosar_utils import AutosarUtils
from basic_func_module.autosar_utils.utils import get_lower_multiplicity, get_short_name
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlParseHandler
from func_module.health_monitor.logger import logger
from func_module.module_management.base_config import BASE_CONFIG_PATH


def get_ecuc_param_conf_container_def(module_container_def):
    tag = module_container_def.get_tag()
    if tag == "ECUC-MODULE-DEF":
        return getattr(getattr(module_container_def, "CONTAINERS", None), "ECUC_PARAM_CONF_CONTAINER_DEF", [])
    elif tag == "ECUC-PARAM-CONF-CONTAINER-DEF":
        return getattr(getattr(module_container_def, "SUB_CONTAINERS", None), "ECUC_PARAM_CONF_CONTAINER_DEF", [])
    else:
        return []


def get_ecuc_choice_container_def(module_container_def):
    tag = module_container_def.get_tag()
    if tag == "ECUC-MODULE-DEF":
        return getattr(getattr(module_container_def, "CONTAINERS", None), "ECUC_CHOICE_CONTAINER_DEF", [])
    elif tag == "ECUC-PARAM-CONF-CONTAINER-DEF":
        return getattr(getattr(module_container_def, "SUB_CONTAINERS", None), "ECUC_CHOICE_CONTAINER_DEF", [])
    else:
        return []


def get_ecuc_string_param_def(container_def):
    return getattr(getattr(container_def, "PARAMETERS", None), "ECUC_STRING_PARAM_DEF", [])


def get_ecuc_multiline_string_param_def(container_def):
    return getattr(getattr(container_def, "PARAMETERS", None), "ECUC_MULTILINE_STRING_PARAM_DEF", [])


def get_ecuc_linker_symbol_def(container_def):
    return getattr(getattr(container_def, "PARAMETERS", None), "ECUC_LINKER_SYMBOL_DEF", [])


def get_ecuc_integer_param_def(container_def):
    return getattr(getattr(container_def, "PARAMETERS", None), "ECUC_INTEGER_PARAM_DEF", [])


def get_ecuc_function_name_def(container_def):
    return getattr(getattr(container_def, "PARAMETERS", None), "ECUC_FUNCTION_NAME_DEF", [])


def get_ecuc_float_param_def(container_def):
    return getattr(getattr(container_def, "PARAMETERS", None), "ECUC_FLOAT_PARAM_DEF", [])


def get_ecuc_enumeration_param_def(container_def):
    return getattr(getattr(container_def, "PARAMETERS", None), "ECUC_ENUMERATION_PARAM_DEF", [])


def get_ecuc_boolean_param_def(container_def):
    return getattr(getattr(container_def, "PARAMETERS", None), "ECUC_BOOLEAN_PARAM_DEF", [])


def get_ecuc_add_info_param_def(container_def):
    return getattr(getattr(container_def, "PARAMETERS", None), "ECUC_ADD_INFO_PARAM_DEF", [])


class BaseEcucCreator:

    def __init__(self) -> None:
        pass

    def infer_base_container(self, container_def, parent):
        least_num = get_lower_multiplicity(container_def)
        if least_num is not None:
            for n in range(least_num):
                default_name = get_short_name(container_def)
                if n > 0:
                    default_name = f"{default_name}_{n}"
                container_val = AutosarUtil.create_sub_container_value(default_name, container_def, parent)
                container_def_list = []
                container_def_list += get_ecuc_choice_container_def(container_def)
                container_def_list += get_ecuc_param_conf_container_def(container_def)
                for sub_container_def in container_def_list:
                    self.infer_base_container(sub_container_def, container_val)

    def infer_base_ecuc(self, module_name, instance_name, bswmd_obj, sys_info_obj, prefix=None):
        """
        Infer basic ecuc obj according to definition in bswmd

        Args:
            module_name: Name of module
            bswmd_obj: Definition of the module. Must be an object, not dict
        """

        if bswmd_obj is not None:
            module_def = AutosarUtils.get_bswmd_autosar_by_module_name(module_name, bswmd_obj)
            # module_def = bswmd_obj.AR_PACKAGES.AR_PACKAGE[0].AR_PACKAGES.AR_PACKAGE[0].ELEMENTS.ECUC_MODULE_DEF[0]
        else:
            logger.error(f"Cannot load bswmd of {module_name}")
            return
        ecuc_header = ArxmlParseHandler.parse_ecuc_header(BASE_CONFIG_PATH)
        ecuc_module_val = AutosarUtil.create_ecuc_module_configuration_values(
            instance_name, module_def, ecuc_header.find("/ActiveEcuC")
        )
        container_def_list = []
        container_def_list += get_ecuc_choice_container_def(module_def)
        container_def_list += get_ecuc_param_conf_container_def(module_def)
        for container_def in container_def_list:
            self.infer_base_container(container_def, ecuc_module_val)

        return AutosarUtil.update_autosar(ecuc_header)

    def infer_base_ecuc_initial(self, module_name, bswmd_obj, ecuc_header):
        """
        Infer basic ecuc obj according to definition in bswmd

        Args:
            module_name: Name of module
            bswmd_obj: Definition of the module. Must be an object, not dict
        """

        if bswmd_obj is not None:
            module_def = AutosarUtils.get_bswmd_autosar_by_module_name(module_name, bswmd_obj)
            # module_def = bswmd_obj.AR_PACKAGES.AR_PACKAGE[0].AR_PACKAGES.AR_PACKAGE[0].ELEMENTS.ECUC_MODULE_DEF[0]
        else:
            logger.error(f"Cannot load bswmd of {module_name}")
            return

        ecuc_module_val = AutosarUtil.create_ecuc_module_configuration_values(module_name, module_def, ecuc_header)
        container_def_list = []
        container_def_list += get_ecuc_choice_container_def(module_def)
        container_def_list += get_ecuc_param_conf_container_def(module_def)
        for container_def in container_def_list:
            self.infer_base_container(container_def, ecuc_module_val)
