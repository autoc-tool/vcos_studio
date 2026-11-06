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
import time
import json
from func_module.health_monitor.logger import logger
from basic_func_module.base_common.load_plug_in import LoadPlugIn
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from func_module.module_management.module_management import ModuleManagement
from func_module.validation.common.validation_def import ValidationData, ValidationLog, ValidationResult
from func_module.validation.common.semantic_rule import SemanticRuleValidator
from func_module.validation.basic_validation.basic_validation import ValidationUtil
from func_module.validation.common.semantic_rule_util import SemanticRuleUtil
from func_module.project_management.studio_cfg_handler import StudioCfgHandler
from func_module.health_monitor import perf_record
from func_module.validation.common.validation_def import ValidationLogAttrIdx as attrIdx


class Validator:

    def __init__(self, validation_data: ValidationData, module_list) -> None:
        self.validation_logs = {}
        self.validation_data = validation_data
        self.module_list = module_list
        # key:validation_mark+ path, value:list index
        self.validation_logs_dict = {}
        self.ignored_logs: dict = {}
        # the log list for test case
        self.log_list = []

    @property
    def autosar_asw_class(self):
        return self.validation_data.autosar_asw_class

    @autosar_asw_class.setter
    def autosar_asw_class(self, v):
        self.validation_data.autosar_asw_class = v

    @property
    def autosar_bsw_class(self):
        return self.validation_data.autosar_bsw_class

    @autosar_bsw_class.setter
    def autosar_bsw_class(self, v):
        self.validation_data.autosar_bsw_class = v

    @property
    def autosar_ib_class(self):
        return self.validation_data.autosar_ib_class

    @autosar_ib_class.setter
    def autosar_ib_class(self, v):
        self.validation_data.autosar_ib_class = v

    @property
    def autosar_system_class(self):
        return self.validation_data.autosar_system_class

    @autosar_system_class.setter
    def autosar_system_class(self, v):
        self.validation_data.autosar_system_class = v

    @property
    def autosar_mod_class(self):
        return self.validation_data.autosar_mod_class

    @autosar_mod_class.setter
    def autosar_mod_class(self, v):
        self.validation_data.autosar_mod_class = v

    @property
    def sys_info_class(self):
        return self.validation_data.sys_info_class

    @sys_info_class.setter
    def sys_info_class(self, v):
        self.validation_data.sys_info_class = v

    @property
    def bsw_ecuc_dict(self):
        return self.validation_data.bsw_ecuc_dict

    def uninit_durable(self):
        from durable import lang

        if lang._main_host is None:
            return
        lang._main_host._d_timer.cancel()
        lang._main_host._t_timer.cancel()
        del lang._main_host
        lang._main_host = None

    def log_with_cache(self, log_level: str, log_str: str, is_ui_log=False):
        if log_level == "error":
            logger.error(log_str) if not is_ui_log else logger.ui_error(log_str)
        elif log_level == "info":
            logger.info(log_str) if not is_ui_log else logger.ui_info(log_str)
        elif log_level == "warning":
            logger.warning(log_str) if not is_ui_log else logger.ui_warning(log_str)

        self.log_list.append(log_str)

        pass

    def validate_module_with_semantic_rule(
        self, validation_module_list: dict, validation_data: ValidationData, validation_logs
    ):
        import copy

        validation_rule_module_list = copy.deepcopy(validation_module_list)
        if "vcosMtnce" in validation_rule_module_list:
            validation_rule_module_list.pop("vcosMtnce")

        bsw_ecuc_dict = {}
        for instance_name in validation_data.autosar_bsw_class.keys():
            bsw_ecuc_dict.update(
                {instance_name: AutosarUtil.to_bsw_dict(validation_data.autosar_bsw_class[instance_name])}
            )
        validation_data.bsw_ecuc_dict = bsw_ecuc_dict

        module_name_list = []
        for instance_name in validation_rule_module_list:
            module_name_list.append(validation_rule_module_list[instance_name]["module_name"])
        # update project plug_in_path
        SemanticRuleUtil.update_plug_in_path(validation_data.sys_info_class.plug_in_path)
        semantic_rules_dict = SemanticRuleUtil.load_semantic_rule(module_name_list)
        for instance_name, v in validation_rule_module_list.items():
            validate_time = 0
            module_name = v["module_name"]
            if module_name not in semantic_rules_dict:
                continue
            try:
                logger.info(f"start validate with semantic rule ==> module: {instance_name}.")
                semantic_rule_validator = SemanticRuleValidator(
                    module_name, semantic_rules_dict[module_name], validation_data
                )
                start_time = time.time()
                semantic_rule_validator.validate()
                validate_time = time.time() - start_time
            except Exception as e:
                logger.warning(f"{type(e)} {format(e)} does not support config validation.")
                pass
            if hasattr(semantic_rule_validator, "logs"):
                if instance_name not in validation_logs.keys():
                    validation_logs.update({instance_name: {"time": 0, "logs": {}}})
                validation_logs[instance_name]["time"] += validate_time
                validation_logs[instance_name]["logs"].update(semantic_rule_validator.logs)

        for instance_name, v in validation_rule_module_list.items():
            bsw_module_rule_obj = None
            validate_time = 0
            try:
                module_name = v["module_name"]
                rule_import_path = f"config_plug_in.validation.rules.{module_name}_rule"
                plugin_module_info = ModuleManagement.get_module_path_info_by_spec_path(
                    set(self.sys_info_class.import_plugin_path_list)
                )
                if self.sys_info_class.system_target_info["module_cfg"][module_name].get("user_plugin", None):
                    LoadPlugIn.append_sys_path(plugin_module_info[module_name], module_name)
                bsw_module_rule_package = LoadPlugIn.load_module(module_name, rule_import_path)
                # 未配置有效的模块 py校验规则，可能没有配置，可能配置错误
                if not bsw_module_rule_package:
                    logger.ui_warning(f"{instance_name} has no valid python validation rules configured.")
                    continue
                bsw_module_rule_obj = getattr(bsw_module_rule_package, f"{module_name}Rule")()
                start_time = time.time()
                bsw_module_rule_obj.validate(validation_data)
                validate_time = time.time() - start_time
                logger.ui_info(f"{instance_name} module validate successful")
            except Exception as e:
                logger.ui_error(f"{instance_name} module validate failed, error: {e}")
                logger.exception(f"{instance_name} module validation error!")

            if bsw_module_rule_obj and hasattr(bsw_module_rule_obj, "logs"):
                if instance_name not in validation_logs.keys():
                    validation_logs.update({instance_name: {"time": 0, "logs": {}}})
                validation_logs[instance_name]["time"] += validate_time
                validation_logs[instance_name]["logs"].update(bsw_module_rule_obj.logs)

    def validate_module_with_basic_rule(self, validation_module_list, validation_data: ValidationData, validation_logs):
        import copy

        validation_basic_module_list = copy.deepcopy(validation_module_list)

        # NOTE:是否需要对validation_basic_module_list做预处理？
        for module_name in validation_basic_module_list:
            logger.info(f"start validate with basic rule ==> module: {module_name}.")
            validation_result_list = ValidationUtil.validate_module(
                validation_data.autosar_asw_class,
                validation_data.autosar_bsw_class,
                validation_data.autosar_ib_class,
                validation_data.autosar_mod_class,
                validation_data.autosar_system_class,
                module_name,
            )
            for validation_result in validation_result_list:
                if module_name not in validation_logs.keys():
                    validation_logs.update({module_name: {"time": 0, "logs": {}}})
                self.merge_validation_result_to_logs(validation_result, validation_logs)
                pass

        pass

    def validate_module(self, validation_module_list):
        self.validation_logs.clear()
        self.validation_logs_dict.clear()
        self.log_list = []

        self.validate_module_with_basic_rule(validation_module_list, self.validation_data, self.validation_logs)
        self.validate_module_with_semantic_rule(validation_module_list, self.validation_data, self.validation_logs)
        self.uninit_durable()
        self.log_with_cache("info", "finish validation!", is_ui_log=True)
        # record validaiton errors
        perf_record.record_validation_result(self.validation_logs)

        return self.validation_logs

    def validate_param(self, basic_validation_dict):
        validation_result_list = ValidationUtil.validate_param(
            self.autosar_asw_class,
            self.autosar_bsw_class,
            self.autosar_ib_class,
            self.autosar_system_class,
            self.autosar_mod_class,
            basic_validation_dict,
        )
        for validation_result in validation_result_list:
            self.merge_validation_result_to_logs(validation_result, self.validation_logs)
            pass

        return validation_result_list

    def validate_container(self, basic_validation_dict):
        validation_result_list = ValidationUtil.validate_container(basic_validation_dict, self.autosar_mod_class)
        for validation_result in validation_result_list:
            self.merge_validation_result_to_logs(validation_result, self.validation_logs)

        return validation_result_list

    def update_validation_log_pass(self, param_path):
        module_name = None
        if len(param_path.split("/")) > 2:
            module_name = param_path.split("/")[2]

        if not module_name:
            return
        if module_name not in self.validation_logs.keys():
            return

        module_log_dict = self.validation_logs[module_name]
        # 因为路径未删除，故不需要更新validation_logs_dict
        for value in module_log_dict["logs"].values():
            for value_info in value["info"]:
                for param_path in value_info[1]:
                    if param_path in param_path:
                        value_info[2] = "pass"
        return

    def update_validation_logs_container_name(self, pre_short_name: str, container_path: str):
        module_name = None
        if len(container_path.split("/")) > 2:
            module_name = container_path.split("/")[2]

        if not module_name:
            return
        if module_name not in self.validation_logs.keys():
            return
        # pre_ecuc_dirname: '/ActiveEcuC/Os/'
        pre_ecuc_dirname = os.path.dirname(container_path)
        # pre_ecuc_path:'/ActiveEcuC/Os/Os_ISR_ZCAN_TX/'
        pre_ecuc_path = f"{pre_ecuc_dirname}/{pre_short_name}/"
        # pre_container_path -> deal with container validation error
        pre_container_path = f"{pre_ecuc_dirname}/{pre_short_name}"

        module_log_dict = self.validation_logs[module_name]
        # container_path: '/ActiveEcuC/Os/Os_ISR_ZCAN_TX_1/'
        for validation_mark, value in module_log_dict["logs"].items():
            for value_info in value["info"]:
                # 更新validation_logs_dict
                combined_key = ValidationLog.get_combined_key(validation_mark, value_info[1])
                index = 0
                if combined_key in self.validation_logs_dict:
                    index = self.validation_logs_dict[combined_key]
                    self.validation_logs_dict.pop(combined_key)

                for i in range(len(value_info[1])):
                    param_path = value_info[1][i]
                    if not param_path.startswith(pre_ecuc_path) and pre_container_path != param_path:
                        continue
                    # 更新validation_logs
                    if pre_container_path == param_path:
                        validation_path = value_info[1][i].replace(pre_container_path, f"{container_path}")
                    else:
                        validation_path = value_info[1][i].replace(pre_ecuc_path, f"{container_path}/")
                    value_info[1][i] = validation_path

                combined_key = ValidationLog.get_combined_key(validation_mark, value_info[1])
                self.validation_logs_dict.update({combined_key: index})

    def filter_pass_logs(self) -> dict:
        failed_log = {}
        try:
            for module_name, logs_dict in self.validation_logs.items():
                if module_name not in failed_log.keys():
                    failed_log[module_name] = {"time": logs_dict.get("time", 0), "logs": {}}
                for validation_mark, validation_info_dict in logs_dict.get("logs").items():
                    for validation_info in validation_info_dict["info"]:
                        if validation_info[attrIdx.result] != "fail":
                            continue
                        if validation_mark not in failed_log[module_name]["logs"].keys():
                            failed_log[module_name]["logs"][validation_mark] = {
                                "time": validation_info_dict.get("time", 0),
                                "summary": validation_info_dict.get("summary", ""),
                                "info": [],
                            }
                        failed_log[module_name]["logs"][validation_mark]["info"].append(validation_info)
                if not failed_log[module_name]["logs"]:
                    failed_log.pop(module_name)
        except Exception as e:
            logger.warning(f"filter pass log exception: {type(e)} {format(e)}!")
        return failed_log

    def save_validation_logs(self, validation_log_file_path):
        try:
            file = open(validation_log_file_path, "w")
            failed_log = self.filter_pass_logs()
            js = json.dumps(failed_log, indent=4, separators=(",", ": "))
            validation_log_file_path = validation_log_file_path.replace("\\", "/")
            logger.ui_info(f"Save validation log to {validation_log_file_path}")
            file.write(js)
            file.close()
        except Exception as e:
            logger.warning(f"exception info: {type(e)} {format(e)}!")

    def load_validation_logs(self, validation_log_file_path):
        if not os.path.exists(validation_log_file_path):
            logger.warning(f"file {validation_log_file_path} not exist !")
            return
        try:
            with open(validation_log_file_path, "r", encoding="utf-8") as f:
                validation_logs = json.load(f)
                # 注意这里只能用update，不能用=赋值，否则会产生id变化
                self.validation_logs.update(validation_logs)
                self.validation_logs_dict = {}
                # 同步更新validation_logs_dict
                for module, value in self.validation_logs.items():
                    for validation_mark, value in value["logs"].items():
                        for index, value_info in enumerate(value["info"]):
                            combined_key = ValidationLog.get_combined_key(validation_mark, value_info[1])
                            self.validation_logs_dict.update({combined_key: index})

        except Exception as e:
            logger.warning(f"exception info: {type(e)} {format(e)}!")
            pass

    def save_ignored_logs(self, ignored_logs_path):
        try:
            file = open(ignored_logs_path, "w")
            js = json.dumps(self.ignored_logs, indent=4, separators=(",", ": "))
            ignored_logs_path = ignored_logs_path.replace("\\", "/")
            logger.ui_info(f"Save ignored log to {ignored_logs_path}")
            file.write(js)
            file.close()
        except Exception as e:
            logger.warning(f"exception info: {type(e)} {format(e)}!")

    def load_ignored_logs(self, ignored_logs_path):
        if not os.path.exists(ignored_logs_path):
            logger.warning(f"file {ignored_logs_path} not exist !")
            return
        try:
            with open(ignored_logs_path, "r", encoding="utf-8") as f:
                ignored_logs = json.load(f)
                # 注意这里只能用update，不能用=赋值，否则会产生id变化
                self.ignored_logs.update(ignored_logs)
        except Exception as e:
            logger.warning(f"exception info: {type(e)} {format(e)}!")
            pass

    def update_ignored_logs(
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
        """修改rule_name的单个校验项"""
        ignored_logs = self.ignored_logs
        # 1.ignored_logs添加校验项
        if is_ignore is True:
            if module_name not in ignored_logs.keys():
                ignored_logs[module_name]: dict = {"time": 0, "logs": {}}
            if rule_name not in ignored_logs[module_name]["logs"].keys():
                ignored_logs[module_name]["logs"][rule_name]: dict = {"time": 0, "summary": summary_text, "info": []}
            ignored_logs[module_name]["logs"][rule_name]["info"].append(
                [item_text, path_list, "fail", auto_solve_list, manual_solve_list]
            )
        # 2.ignored_logs删除校验项
        else:
            if (module_name not in ignored_logs.keys()) or ("logs" not in ignored_logs[module_name].keys()):
                return
            if (rule_name not in ignored_logs[module_name]["logs"].keys()) or (
                "info" not in ignored_logs[module_name]["logs"][rule_name].keys()
            ):
                return
            # 2.1.删除rule_name的单个校验项
            info_list = ignored_logs[module_name]["logs"][rule_name]["info"]
            for i in range(len(info_list)):
                # 兼容老版本的logs格式
                if (info_list[i][0].strip() == item_text.strip()) and (sorted(path_list) == sorted(info_list[i][1])):
                    del info_list[i]
                    break
            # 2.2.如果rule_name下没有校验项则清空
            if len(ignored_logs[module_name]["logs"][rule_name]["info"]) == 0:
                del ignored_logs[module_name]["logs"][rule_name]

    def get_module_name(self, validation_mark):
        upper_module_name = validation_mark[:-6]
        for module_name in self.module_list:
            if upper_module_name == module_name.upper():
                return module_name
        return None

    def merge_validation_result_to_logs(self, validation_result: ValidationResult, validation_logs):
        if not validation_result:
            return
        validation_mark = validation_result.validation_mark
        module_name = self.get_module_name(validation_mark)
        if not module_name:
            return

        if module_name not in validation_logs.keys():
            validation_logs.update({module_name: {"time": 0, "logs": {}}})
        # basic validation just one path
        combined_key = ValidationLog.get_combined_key(validation_mark, validation_result.path)
        if validation_mark not in validation_logs[module_name]["logs"]:
            validation_info = {"time": 0, "summary": "", "info": []}
            validation_logs[module_name]["logs"][validation_mark] = validation_info
            validation_logs[module_name]["logs"][validation_mark]["summary"] = validation_result.summary
            validation_logs[module_name]["logs"][validation_mark]["info"].append(
                [
                    validation_result.message,
                    validation_result.path,
                    validation_result.result,
                    validation_result.auto_solve_list,
                    validation_result.manual_solve_list,
                ]
            )
            self.validation_logs_dict.update({combined_key: 0})
        else:
            if combined_key in self.validation_logs_dict:
                index = self.validation_logs_dict[combined_key]
                if index >= len(validation_logs[module_name]["logs"][validation_mark]["info"]):
                    return
                info_item = validation_logs[module_name]["logs"][validation_mark]["info"][index]
                info_item[0] = validation_result.message
                info_item[2] = validation_result.result
                info_item.extend([None] * (attrIdx.attr_cnt - len(info_item)))
                info_item[3] = validation_result.auto_solve_list
                info_item[4] = validation_result.manual_solve_list
            else:
                info_len = len(validation_logs[module_name]["logs"][validation_mark]["info"])
                validation_logs[module_name]["logs"][validation_mark]["info"].append(
                    [
                        validation_result.message,
                        validation_result.path,
                        validation_result.result,
                        validation_result.auto_solve_list,
                        validation_result.manual_solve_list,
                    ]
                )
                self.validation_logs_dict.update({combined_key: info_len})

    @classmethod
    def get_validation_configuration(cls, data):
        enable_module_dict = {
            name: getattr(getattr(v, "DEFINITION_REF", ""), "valueOf_", "").split("/")[-1]
            for name, obj in data.autosar_bsw_class.items()
            for v in obj.find_nodes("ECUC-MODULE-CONFIGURATION-VALUES")
        }
        validation_module_list: dict = StudioCfgHandler.get_gen_or_validation_module_list(
            enable_module_dict, data.sys_target_dict, "support_validation"
        )
        enabled_validation_module_list: list = data.sys_info_class.validate_modules
        if not validation_module_list:
            logger.error("No validation module list got!")
        return validation_module_list, enabled_validation_module_list

    @classmethod
    def parse_validation_result_info(cls, module_list, validation_logs, ignored_logs):
        count_log_dict = {"Error": 0, "Warning": 0}  # 0:Error 1:Warning
        validation_result: dict = {}
        for module, module_validation in validation_logs.items():
            if module not in module_list:
                continue
            if "logs" not in module_validation.keys():
                continue
            validation_result[module] = []
            for mark, block_validation in module_validation["logs"].items():
                log_type = int(mark[-6])
                if "info" not in block_validation.keys():
                    continue
                for element in block_validation["info"]:
                    if "fail" not in element:
                        continue
                    # 不统计被忽略的错误校验结果
                    ignore_flag: bool = False
                    try:
                        for item in ignored_logs[module]["logs"][mark]["info"]:
                            if sorted(item[1]) == sorted(element[1]):
                                ignore_flag = True
                                break
                    except Exception:
                        pass
                    if ignore_flag is True:
                        continue
                    validation_result[module].append(
                        {"mark": mark, "summary": block_validation["summary"], "element": element}
                    )
                    if log_type == 0:
                        count_log_dict["Error"] += 1
                    elif log_type == 1:
                        count_log_dict["Warning"] += 1

        return count_log_dict, validation_result

    @classmethod
    def get_validation_support_modules(cls, module_list, module_cfg):
        """filter out unsupport modules"""
        support_modules = {}
        for instance_name, module_info in module_list.items():
            module_name = module_info.get("module_name")
            if module_cfg.get(module_name, {}).get("support_validation"):
                support_modules[instance_name] = module_info
        return support_modules

    @staticmethod
    def get_module_validation_fail_logs(module_name, validation_logs, failed_logs):
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
