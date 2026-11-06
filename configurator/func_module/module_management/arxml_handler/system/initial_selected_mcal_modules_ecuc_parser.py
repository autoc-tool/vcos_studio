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
from basic_func_module.autosar_utils.utils import (
    set_value_ref,
    set_value_iref,
    set_value,
    get_definition_ref,
    get_short_name,
)
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.autosar_utils.autosar_utils import AutosarUtils
from func_module.module_management.arxml_handler.base_ecuc_creator import BaseEcucCreator
from func_module.health_monitor.logger import logger
from collections import defaultdict

ECUC_PARAM_VALUE_LIST = [
    "ECUC-REFERENCE-DEF",
    "ECUC-CHOICE-REFERENCE-DEF",
    "ECUC-FOREIGN-REFERENCE-DEF",
    "ECUC-SYMBOLIC-NAME-REFERENCE-DEF",
    "ECUC-INTEGER-PARAM-DEF",
    "ECUC-BOOLEAN-PARAM-DEF",
    "ECUC-FLOAT-PARAM-DEF",
    "ECUC-ENUMERATION-PARAM-DEF",
    "ECUC-FUNCTION-NAME-DEF",
    "ECUC-STRING-PARAM-DEF",
    "ECUC-LINKER-SYMBOL-DEF",
    "ECUC-MULTILINE-STRING-PARAM-DEF",
]

ECUC_MODULE_VALUE_LIST = [
    # "ECUC-CONTAINER-VALUE",
    "ECUC-MODULE-CONFIGURATION-VALUES",
]

PERFIX_RENESAS = "Renesas"


class InitialSelectedMcalModulesEcucParser:

    def __init__(self, mod_autosar_dict, selected_mcal_modules_list, sys_info_class):
        self.mod_autosar_dict = mod_autosar_dict
        self.selected_mcal_modules_list = selected_mcal_modules_list
        self.sys_info_class = sys_info_class

    def set_selected_mcal_modules_list(self, selected_mcal_modules_list, sys_info_class):
        self.selected_mcal_modules_list = selected_mcal_modules_list
        self.sys_info_class = sys_info_class

    def traversal_mcal_module_obj(self, container_name, mcal_module_obj, base_ecuc_obj, mcal_module_name, prefix):

        param_ref_val_dict = None
        if not isinstance(mcal_module_obj, dict):
            return
        if isinstance(mcal_module_obj, dict):
            for key, value in mcal_module_obj.items():
                if key == "DefinitionRef":
                    container_cfg_path = value.replace(prefix, "InitialEcuC")
                    container_def_path = value
                    container_def = self.mod_autosar_dict[mcal_module_name].find(container_def_path)
                    if container_def is not None and container_def.get_tag() in ECUC_PARAM_VALUE_LIST:
                        logger.warning("No definition found, definition path: ", container_def_path)
                        continue
                    elif container_def is not None:  # 有定义，就创建container
                        # 删除base ecuc中创建的container
                        base_container = base_ecuc_obj.find(container_cfg_path)
                        if base_container is not None and "ECUC-CONTAINER-VALUE" == base_container.original_tagname_:
                            AutosarUtil.remove_container_value(
                                base_container.parent_object_.ECUC_CONTAINER_VALUE, base_container
                            )
                        container_cfg_path = self.replace_last_segment(container_cfg_path, container_name)
                        base_container = base_ecuc_obj.find(container_cfg_path)
                        if base_container is not None:
                            logger.debug("base container already existed")
                        else:
                            new_container = AutosarUtil.create_sub_container_value(
                                container_name, container_def, base_ecuc_obj
                            )
                            base_container = new_container

                        param_ref_val_dict = self.gather_param_ref_val(base_container, prefix)
                        self.fill_parameters(
                            param_ref_val_dict, mcal_module_obj, mcal_module_name, prefix, base_container
                        )

    def fill_parameters(self, param_ref_val_dict, mcal_module_obj, mcal_module_name, prefix, base_container):

        for key, value in mcal_module_obj.items():
            if key == "DefinitionRef":
                continue
            if not isinstance(mcal_module_obj[key], dict):
                continue
            definition_ref = mcal_module_obj[key]["DefinitionRef"]

            container_def_path = definition_ref
            container_def = self.mod_autosar_dict[mcal_module_name].find(container_def_path)
            # container_def = module_def.find(container_def_path)  # 查看有没有定义
            if container_def is None:
                logger.warning("No definition found, definition path: " + container_def_path)
                continue
            if container_def is not None and container_def.get_tag() in ECUC_PARAM_VALUE_LIST:
                if param_ref_val_dict is not None:
                    self.set_param_and_ref_value(param_ref_val_dict, key, value, mcal_module_name)  # 参数赋值
            elif container_def is not None:
                self.traversal_mcal_module_obj(key, value, base_container, mcal_module_name, prefix)

    def check_new_and_old_initial_ecuc(self, mcal_module_name, new_initial_autosar, old_initial_autosar, prefix):

        ecuc_obj = new_initial_autosar.find(f"/InitialEcuC/{mcal_module_name}")
        # 对应mcal其他模块的导入，直接删除new initial里的该模块，然后重新创建base ecuc，组成新的new initial，再去更新
        if ecuc_obj is not None:
            # 移除module value obj的同时还更新了ar_path和ar_tag，否则使用find将不符合预期
            AutosarUtil.remove_module_value(ecuc_obj.parent_object_.ECUC_MODULE_CONFIGURATION_VALUES, ecuc_obj)
        base_ecuc_creator = BaseEcucCreator()
        base_ecuc_creator.infer_base_ecuc_initial(
            mcal_module_name, self.mod_autosar_dict[mcal_module_name], new_initial_autosar.find(f"/InitialEcuC")
        )

        ecuc_obj = old_initial_autosar.find(f"/InitialEcuC/{mcal_module_name}")
        if ecuc_obj is None:
            # 如果ecuc加到old_initial_autosar中没有指定模块的对象，创建一个初始的加进来
            base_ecuc_creator.infer_base_ecuc_initial(
                mcal_module_name, self.mod_autosar_dict[mcal_module_name], old_initial_autosar.find(f"/InitialEcuC")
            )

        return new_initial_autosar

    def get_mcal_perfix(self, cfg_dict, mcal_module_name):
        module_obj_dict = cfg_dict["eb"]["arxml"]
        if mcal_module_name in module_obj_dict:
            pass  # 存在于字典结构中
        else:
            return
        mcal_module_obj = module_obj_dict[mcal_module_name]
        if not isinstance(mcal_module_obj, dict):
            return
        if isinstance(mcal_module_obj, dict):
            for key, value in mcal_module_obj.items():
                if key == "DefinitionRef":
                    return value.split("/")[1]

    def get_mod_perfix(self, module_name):
        perfix = ""
        if module_name in self.mod_autosar_dict:
            ar_package = getattr(getattr(self.mod_autosar_dict[module_name], "AR_PACKAGES", object()), "AR_PACKAGE", [])
            if len(ar_package) == 0:
                return False
            perfix = get_short_name(ar_package[0])

        return perfix

    def update_initial_selected_mcal_modules_ecuc_from_mcal_arxml(
        self, new_initial_autosar, cfg_dict, old_initial_autosar
    ):
        new_initial_autosar = AutosarUtil.update_autosar(old_initial_autosar)
        for mcal_module_name in self.selected_mcal_modules_list:
            mod_prefix = self.get_mod_perfix(mcal_module_name)
            mcal_prefix = self.get_mcal_perfix(cfg_dict, mcal_module_name)
            # 如果mod的前缀和mcal arxml中的前缀不同，表示工程使用的芯片和mcal arxml的不相同
            if mod_prefix != mcal_prefix:
                logger.error(
                    f"The current module({mcal_module_name}) mcal arxml does not match the project. Please select the correct mcal arxml file to import"
                )
                continue

            new_initial_autosar = self.check_new_and_old_initial_ecuc(
                mcal_module_name, new_initial_autosar, old_initial_autosar, mod_prefix
            )
            if new_initial_autosar is None:
                return None
            base_ecuc_obj = new_initial_autosar.find(f"/InitialEcuC/{mcal_module_name}")
            ar_packages = cfg_dict["eb"]["arxml"]
            if mcal_module_name in ar_packages:
                pass  # 存在于字典结构中
            else:
                return
            mcal_module_obj = ar_packages[mcal_module_name]
            # mcal_module_obj = cfg_dict['eb']['arxml']['ArPackages'][mcal_module_name][mcal_module_name]
            # 将mcal中的配置填充到new initial中
            prefix_module_definition_obj = (
                AutosarUtils.get_bswmd_autosar_by_module_name(mcal_module_name, self.mod_autosar_dict[mcal_module_name])
                .get_path()
                .split("/" + mcal_module_name)[0][1:]
            )
            self.traversal_mcal_module_obj(
                mcal_module_name, mcal_module_obj, base_ecuc_obj, mcal_module_name, prefix_module_definition_obj
            )

        return new_initial_autosar

    def replease_active_ecuc(self, value_ref):
        # 分割字符串
        parts = value_ref.split("/", 3)  # 只分割前3个斜杠前的部分

        # 检查是否有足够的部分进行替换（即字符串中至少有两个斜杠）
        if len(parts) >= 3:
            # 将第二个部分替换为'ActiveEcuc'
            parts[1] = "ActiveEcuC"

            new_str = "/".join(parts)
        else:
            new_str = value_ref  # 如果没有两个斜杠，则不修改

        return new_str

    def set_param_and_ref_value(self, param_ref_val_dict, key_3, value, mcal_module_name):

        if not isinstance(value, dict):
            return

        if "DefinitionRef" not in list(value.keys()):
            return

        if value["DefinitionRef"] in list(param_ref_val_dict.keys()):

            param_obj = param_ref_val_dict[value["DefinitionRef"]][0]
            tag = param_obj.get_tag()
            if tag == "ECUC-REFERENCE-VALUE":
                if value["ValueRef"] is None:
                    return
                if isinstance(value["ValueRef"], list):  # 如果是多个ref，第一个ref写入param_obj，其他的需要创建ref实体
                    value_ref_list = [value for value in value["ValueRef"] if value is not None]
                    self.cases_dealing_with_multiple_refs(value_ref_list, param_obj, mcal_module_name)
                else:
                    set_value_ref(param_obj, self.replease_active_ecuc(str(value["ValueRef"])))

            elif tag == "ECUC-INSTANCE-REFERENCE-VALUE":
                if value["ValueRef"] is None:
                    return
                if isinstance(value["ValueRef"], list):  # 如果是多个ref，第一个ref写入param_obj，其他的需要创建ref实体
                    value_ref_list = [value for value in value["ValueRef"] if value is not None]
                    self.cases_dealing_with_multiple_irefs(value_ref_list, param_obj, mcal_module_name)
                else:
                    set_value_iref(param_obj, self.replease_active_ecuc(str(value["ValueRef"])))
            elif tag in [
                "ECUC-NUMERICAL-PARAM-VALUE",
                "ECUC-TEXTUAL-PARAM-VALUE",
                "ECUC-ADD-INFO-PARAM-VALUE",
            ]:
                if value["Value"] is None:
                    return
                set_value(param_obj, str(value["Value"]))
        else:
            pass

    def cases_dealing_with_multiple_refs(self, value_list, param_obj, mcal_module_name):
        for i in range(len(value_list)):
            if 1 == i:
                set_value_ref(param_obj, self.replease_active_ecuc(str(value_list[i])))
            else:
                param_ref_obj = AutosarUtil.set_reference(
                    param_obj.get_parent(),
                    self.get_module_definition_obj(mcal_module_name, self.mod_autosar_dict).find(
                        param_obj.DEFINITION_REF.valueOf_
                    ),
                )
                set_value_ref(param_ref_obj, self.replease_active_ecuc(str(value_list[i])))

    def cases_dealing_with_multiple_irefs(self, value_list, param_obj, mcal_module_name):
        for i in range(len(value_list)):
            if 1 == i:
                set_value_iref(param_obj, str(value_list[i]))
            else:
                param_ref_obj = AutosarUtil.set_reference(
                    param_obj.get_parent(),
                    self.get_module_definition_obj(mcal_module_name, self.mod_autosar_dict).find(
                        param_obj.DEFINITION_REF.valueOf_
                    ),
                )
                set_value_iref(param_ref_obj, self.replease_active_ecuc(str(value_list[i])))

    def gather_param_ref_val(self, container_value, prefix):
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
        param_ref_val_dict = defaultdict(list)
        # Prevent modify original list
        param_val_list = []
        if hasattr(container_value, "PARAMETER_VALUES"):
            param_val_list += getattr(container_value.PARAMETER_VALUES, "ECUC_NUMERICAL_PARAM_VALUE", [])
            param_val_list += getattr(container_value.PARAMETER_VALUES, "ECUC_TEXTUAL_PARAM_VALUE", [])
            for param_val in param_val_list:
                def_path = get_definition_ref(param_val).replace("AUTOSAR", prefix)
                param_ref_val_dict[def_path].append(param_val)

        # Prevent modify original list
        ref_val_list = []
        if hasattr(container_value, "REFERENCE_VALUES"):
            ref_val_list += getattr(container_value.REFERENCE_VALUES, "ECUC_INSTANCE_REFERENCE_VALUE", [])
            ref_val_list += getattr(container_value.REFERENCE_VALUES, "ECUC_REFERENCE_VALUE", [])
            for ref_val in ref_val_list:
                def_path = get_definition_ref(ref_val).replace("AUTOSAR", prefix)
                param_ref_val_dict[def_path].append(ref_val)

        return param_ref_val_dict

    def get_module_definition_obj(self, module_name, bsw_mod_dict):
        module_definition_obj = None

        if module_name in bsw_mod_dict:
            # module_definition_obj = bsw_mod_dict[module_name].find(f"{perfix}/{module_name}")
            module_definition_obj = bsw_mod_dict[module_name]
        else:
            logger.error(f"{module_name} Configuration Parameter Definition not found!")

        return module_definition_obj

    def replace_last_segment(self, s, replacement):
        # 用'/'切分字符串
        segments = s.split("/")
        # 替换最后一个片段
        segments[-1] = replacement
        # 用'/'重新连接各个片段
        result = "/".join(segments)
        return result
