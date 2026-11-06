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
from func_module.validation.validator import Validator, ValidationData
from ui_adaptor.data_management import get_autosar_asw_class
from ui_adaptor.data_management import get_autosar_bsw_class
from ui_adaptor.data_management import get_autosar_system_class
from ui_adaptor.data_management import get_autosar_ib_class
from ui_adaptor.data_management import get_autosar_bswmd_class
from ui_adaptor.data_management import get_sys_info_class, get_sys_target_dict
import os
from func_module.health_monitor import perf_record
from basic_func_module.autosar_utils.utils import get_value, get_definition_ref, get_short_name
from func_module.validation.basic_validation.basic_validation import ValidationUtil
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from func_module.module_management.bsw_editor.bsw_editor import BswEditor
from basic_func_module.base_logger import logger
from func_module.validation.common.validation_def import ValidationLogAttrIdx as attrIdx


class ValidationFunc:

    def __init__(self):
        self.update_instance()
        return

    def update_instance(self):
        validation_data = ValidationData(
            get_autosar_asw_class(),
            get_autosar_bsw_class(),
            get_autosar_ib_class(),
            get_autosar_system_class(),
            get_autosar_bswmd_class(),
            get_sys_info_class(),
        )
        sys_info_class = get_sys_info_class()
        module_list = None
        if hasattr(sys_info_class, "all_modules"):
            module_list = sys_info_class.all_modules
        self.validation_instance = Validator(validation_data, module_list)

    def update_validation_data(self):
        self.validation_instance.autosar_asw_class = get_autosar_asw_class()
        self.validation_instance.autosar_bsw_class = get_autosar_bsw_class()
        self.validation_instance.autosar_ib_class = get_autosar_ib_class()
        self.validation_instance.autosar_system_class = get_autosar_system_class()
        self.validation_instance.autosar_mod_class = get_autosar_bswmd_class()

        sys_info_class = get_sys_info_class()
        module_list = sys_info_class.all_modules
        self.validation_instance.module_list = module_list
        self.validation_instance.sys_info_class = sys_info_class

    def cbk_get_validation_logs(self):
        if self.validation_instance is None:
            self.update_instance()
        return self.validation_instance.validation_logs

    def cbk_get_module_failed_validation_logs(self, module_list=[]):

        def __get_module_validation_fail_logs(module_name, validation_logs, failed_logs):
            logs_dict = validation_logs.get("logs", {})
            if module_name not in failed_logs.keys():
                failed_logs[module_name] = {}
            for validation_mark, validation_ret_info_dict in logs_dict.items():
                if validation_mark not in failed_logs[module_name].keys():
                    failed_logs[module_name][validation_mark] = {
                        "summary": validation_ret_info_dict.get("summary", ""),
                        "info": [],
                    }
                validation_ret_info_list = validation_ret_info_dict.get("info", [])
                for validation_info in validation_ret_info_list:
                    if len(validation_info) > attrIdx.result and validation_info[attrIdx.result] == "fail":
                        failed_logs[module_name][validation_mark]["info"].append(validation_info)

        failed_logs = {}
        if self.validation_instance is None:
            self.update_instance()
        if not module_list:
            for module_name, validation_logs in self.validation_instance.validation_logs.items():
                __get_module_validation_fail_logs(module_name, validation_logs, failed_logs)
        else:
            for module_name in module_list:
                validation_logs = self.validation_instance.validation_logs.get(module_name, {})
                __get_module_validation_fail_logs(module_name, validation_logs, failed_logs)
        return failed_logs

    def cbk_get_container_validation_fail_logs(self, container_path: str, module_name: str):
        failed_logs = {}
        logs_dict = self.validation_instance.validation_logs.get(module_name, {}).get("logs", {})
        for validation_mark, validation_ret_info_dict in logs_dict.items():
            if validation_mark not in failed_logs.keys():
                failed_logs[validation_mark] = {"summary": validation_ret_info_dict.get("summary", ""), "info": []}

            validation_ret_info_list = validation_ret_info_dict.get("info", [])
            for validation_info in validation_ret_info_list:
                if len(validation_info) > attrIdx.result and validation_info[attrIdx.result] == "fail":
                    for param_path in validation_info[attrIdx.path]:
                        if container_path in param_path:
                            failed_logs[validation_mark]["info"].append(validation_info)
                            break
        return failed_logs

    def cbk_validation_fail_logs_to_ui_dict(self, container_path, validation_logs: dict):
        validation_error_dict = {}
        for validation_mark, validation_info_dict in validation_logs.items():
            validation_info_list = validation_info_dict.get("info")
            if not validation_info_dict or not validation_info_list:
                continue
            for validation_info in validation_info_list:
                validation_message = validation_info[attrIdx.message]
                for path in validation_info[attrIdx.path]:
                    # just update in currrent container error
                    if container_path not in path:
                        continue
                    if path not in validation_error_dict.keys():
                        validation_error_dict[path] = []
                    validation_error_dict[path].append(
                        {
                            "validation_mark": validation_mark,
                            "summary": validation_info_dict.get("summary", ""),
                            "message": validation_message,
                            "path": validation_info[attrIdx.path],
                            "auto_solve_list": (
                                validation_info[attrIdx.auto_solve] if attrIdx.auto_solve < len(validation_info) else []
                            ),
                            "manual_solve_list": (
                                validation_info[attrIdx.manual_solve]
                                if attrIdx.manual_solve < len(validation_info)
                                else []
                            ),
                        }
                    )
        return validation_error_dict

    def cbk_get_cached_logs(self):
        if self.validation_instance is None:
            self.update_instance()
        return self.validation_instance.log_list

    def cbk_save_validation_logs_to_file(self):
        if self.validation_instance is None:
            self.update_instance()

        sys_info_class = get_sys_info_class()
        config_base_path = sys_info_class.config_base_path
        validation_log_path = os.path.join(config_base_path, "system/validation_logs.log")
        self.validation_instance.save_validation_logs(validation_log_path)
        return

    def cbk_load_validation_logs_from_file(self):
        if self.validation_instance is None:
            self.update_instance()

        sys_info_class = get_sys_info_class()
        if not sys_info_class or not hasattr(sys_info_class, "config_base_path"):
            return
        config_base_path = sys_info_class.config_base_path
        validation_log_path = os.path.join(config_base_path, "system/validation_logs.log")
        self.validation_instance.load_validation_logs(validation_log_path)
        return

    def cbk_get_ignored_logs(self):
        """获取func层ignored_logs"""
        if self.validation_instance is None:
            self.update_instance()
        return self.validation_instance.ignored_logs

    @perf_record.log_function_stats(["校验", "更新忽略日志"])
    def cbk_update_ignored_logs(
        self,
        module_name: str,
        rule_name: str,
        summary_text: str,
        item_text: str,
        path_list: list,
        auto_solve_list: list,
        manual_solve_list: list,
        is_ignore: bool,
    ):
        """更新func层ignored_logs"""
        if self.validation_instance is None:
            self.update_instance()
        self.validation_instance.update_ignored_logs(
            module_name, rule_name, summary_text, item_text, path_list, auto_solve_list, manual_solve_list, is_ignore
        )

    def cbk_save_ignored_logs_to_file(self):
        """保存func层ignored_logs"""
        if self.validation_instance is None:
            self.update_instance()
        sys_info_class = get_sys_info_class()
        if not sys_info_class or not hasattr(sys_info_class, "config_base_path"):
            return
        config_base_path = sys_info_class.config_base_path
        ignored_logs_path = os.path.join(config_base_path, "system/ignored_logs.log")
        self.validation_instance.save_ignored_logs(ignored_logs_path)
        return

    def cbk_load_ignored_logs_from_file(self):
        """加载func层ignored_logs"""
        if self.validation_instance is None:
            self.update_instance()
        sys_info_class = get_sys_info_class()
        if not sys_info_class or not hasattr(sys_info_class, "config_base_path"):
            return
        config_base_path = sys_info_class.config_base_path
        ignored_logs_path = os.path.join(config_base_path, "system/ignored_logs.log")
        self.validation_instance.load_ignored_logs(ignored_logs_path)
        return

    def validate_module(self, module_list):
        if self.validation_instance is None:
            self.update_instance()
        self.update_validation_data()
        return self.validation_instance.validate_module(module_list)

    @perf_record.log_function_stats(["校验", "模块校验"])
    def validate_module_with_result(self, module_list):
        if self.validation_instance is None:
            self.update_instance()
        self.update_validation_data()

        # filter unsupported modules
        module_cfg = get_sys_target_dict().get("module_cfg", {})
        module_list = self.validation_instance.get_validation_support_modules(module_list, module_cfg)

        validation_logs = self.validation_instance.validate_module(module_list)
        ignored_logs = self.validation_instance.ignored_logs

        count_log_dict, validation_result = self.validation_instance.parse_validation_result_info(
            module_list, validation_logs, ignored_logs
        )

        validation_result = {k: not bool(v) for k, v in validation_result.items()}
        return count_log_dict, validation_result

    def cbk_validate_param(self, param):
        if self.validation_instance is None:
            self.update_instance()
        self.update_validation_data()
        result_list = self.validation_instance.validate_param(param)

        return result_list

    @perf_record.log_function_stats(["校验", "container校验"])
    def cbk_validate_container(self, param):
        if self.validation_instance is None:
            self.update_instance()
        self.update_validation_data()
        result_list = self.validation_instance.validate_container(param)
        validation_ui_result_list = []

        for result in result_list:
            validation_ui_result = {}
            validation_ui_result.update({"message": result.message})
            validation_ui_result.update({"result": result.result})
            validation_ui_result_list.append(validation_ui_result)

        return validation_ui_result_list

    def update_validation_log_pass(self, param):
        # 将contaier对应的param path，都置为pass
        if self.validation_instance is None:
            self.update_instance()
        path_list = param["path_list"]
        for param_path in path_list:
            self.validation_instance.update_validation_log_pass(param_path)

        return

    def cbk_validation_update_modify_container_name(self, pre_name: str, ecue_path: str):
        if self.validation_instance is None:
            self.update_instance()
        self.validation_instance.update_validation_logs_container_name(pre_name, ecue_path)

    @perf_record.log_function_stats(["校验", "校验错误一键解决", "更新参数值"])
    def cbk_update_arxml_value_by_one_click_solution(self, ecuc_path, new_value):
        if self.validation_instance is None:
            self.update_instance()
        try:
            autosar_ecuc_obj = self.validation_instance.autosar_bsw_class
            module_name, instance_name = ValidationUtil.get_mod_name(autosar_ecuc_obj, ecuc_path)
            param_obj = ValidationUtil.get_param_value_obj(autosar_ecuc_obj.get(instance_name), ecuc_path)
            if not param_obj:
                return None
            mod_path = get_definition_ref(param_obj)
            param_def_obj = self.validation_instance.autosar_mod_class[module_name].find(mod_path)
            old_value = get_short_name(param_obj) if ecuc_path.split("/")[-1] == "ShortName" else get_value(param_obj)
            if old_value != new_value:
                tag = param_def_obj.get_tag()
                container_path = "/".join(ecuc_path.split("/")[:-1])
                BswEditor.set_new_value_to_ecuc_arxml(
                    autosar_ecuc_obj, new_value, old_value, mod_path, instance_name, container_path, tag, None
                )
        except Exception as e:
            logger.ui_error(f"one-click solution error in set arxml value!: {e}")
            return None
        return module_name

    @perf_record.log_function_stats(["校验", "校验错误一键解决", "创建container"])
    def cbk_create_container_by_one_click_solution(self, param_ecuc_path: str, mod_path: str, create_num):
        if self.validation_instance is None:
            self.update_instance()
        try:
            autosar_ecuc_obj = self.validation_instance.autosar_bsw_class
            autosat_mod_obj = self.validation_instance.autosar_mod_class
            module_name, instance_name = ValidationUtil.get_mod_name(autosar_ecuc_obj, param_ecuc_path)
            module_bsw_obj = autosar_ecuc_obj.get(instance_name)
            module_mod_obj = autosat_mod_obj.get(module_name)
            if not module_bsw_obj or not module_mod_obj:
                return None
            for idx in range(int(create_num)):
                create_ret = AutosarUtil.create_container_by_path(
                    module_bsw_obj, module_mod_obj, param_ecuc_path, mod_path
                )
        except Exception as e:
            logger.ui_error(f"one-click solution error in create container: {e}")
            return None
        return module_name if create_ret else None

    @perf_record.log_function_stats(["校验", "校验错误一键解决", "参数值重排序回填"])
    def cbk_set_repopulate_value_by_one_click_solution(self, param_ecuc_path: str, mod_path: str, start_idx=0):
        if self.validation_instance is None:
            self.update_instance()

        set_value_dict = {}
        autosar_ecuc_obj = self.validation_instance.autosar_bsw_class

        try:
            module_name, instance_name = ValidationUtil.get_mod_name(autosar_ecuc_obj, param_ecuc_path)
            bsw_moudle_obj = autosar_ecuc_obj.get(instance_name)
            parent_container_ecuc_path = os.path.dirname(param_ecuc_path)
            parent_container_obj = bsw_moudle_obj.find(parent_container_ecuc_path)
            parent_container_mod_path = get_definition_ref(parent_container_obj)

            curr_ecuc_path, curr_mod_path = f"{parent_container_ecuc_path}", f"{parent_container_mod_path}"
            module_root_path = f"/ActiveEcuC/{instance_name}"
            while True:
                if curr_ecuc_path == module_root_path:
                    break
                if curr_mod_path == mod_path:
                    break
                curr_ecuc_path = os.path.dirname(curr_ecuc_path)
                curr_ecuc_obj = bsw_moudle_obj.find(curr_ecuc_path)
                curr_mod_path = get_definition_ref(curr_ecuc_obj)

            container_path_list = AutosarUtil.get_container_path_by_mod_path(
                bsw_moudle_obj, curr_ecuc_path, parent_container_mod_path
            )
        except Exception as e:
            logger.ui_error(f"one-click solution error in repopulate parameter value: {e}")
            return set_value_dict

        param_name = param_ecuc_path.split("/")[-1]
        for container_path in container_path_list:
            set_value_dict[f"{container_path}/{param_name}"] = f"{start_idx}"
            start_idx += 1
        return set_value_dict

    @perf_record.log_function_stats(["校验", "校验错误一键解决", "删除无效引用"])
    def cbk_delete_reference_by_one_click_solution(self, mod_path: str, param_path: str, delete_ref_list: list):
        if self.validation_instance is None:
            self.update_instance()
        try:
            autosar_ecuc_obj = self.validation_instance.autosar_bsw_class
            autosat_mod_obj = self.validation_instance.autosar_mod_class
            module_name, instance_name = ValidationUtil.get_mod_name(autosar_ecuc_obj, param_path)
            container_path = os.path.dirname(param_path)
            tag = autosat_mod_obj[module_name].find(mod_path).get_tag()
            for ref_value in delete_ref_list:
                BswEditor.remove_param_item_and_write_to_ecuc_arxml(
                    autosar_ecuc_obj, autosat_mod_obj, ref_value, mod_path, instance_name, container_path, tag, None
                )
        except Exception as e:
            logger.ui_error(f"one-click solution error in delete reference: {e}")
            return None
        return instance_name
