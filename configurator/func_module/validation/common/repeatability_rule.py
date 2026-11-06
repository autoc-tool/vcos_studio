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
from func_module.validation.common.basic_rule import BasicRule, timing_decorator
from func_module.validation.common.validation_def import SemanticRuleData, ValidationData
from func_module.validation.common.semantic_rule_util import SemanticRuleUtil


class SemanticRepeatabilityRule(BasicRule):
    """针对重复性的语义校验"""

    def __init__(self, logs, semantic_rule_data: SemanticRuleData, validation_data: ValidationData) -> None:
        super().__init__()
        self.logs = logs
        self.semantic_rule_data = semantic_rule_data
        self.validation_data = validation_data
        self.validation_result = False

    def check_validation_run(self):
        if not self.modules_are_exist([self.semantic_rule_data.module_name], self.validation_data.bsw_ecuc_dict):
            return False
        return True

    @timing_decorator
    def validation_run(self):
        # 1)准备校验数据
        module_name = self.semantic_rule_data.module_name
        module_bsw_dict = self.validation_data.bsw_ecuc_dict[module_name]["ArPackages"]["ActiveEcuC"][module_name]
        mod_path = self.semantic_rule_data.rule_ruleset["mod_path"]
        base_path = self.semantic_rule_data.rule_ruleset["base_path"]
        container_list = SemanticRuleUtil.find_validated_container(
            base_path, module_bsw_dict, f"/ActiveEcuC/{module_name}"
        )

        if SemanticRuleUtil.is_multi_instance_param(module_name, mod_path, self.validation_data.autosar_mod_class):
            self.multi_value_repeatability_validation(mod_path, container_list)
        else:
            self.single_value_repeatability_validation(mod_path, container_list)

    def single_value_repeatability_validation(self, mod_path, container_list):
        for container_path, container_obj in container_list:
            validated_data_list = SemanticRuleUtil.find_validated_parameter(mod_path, container_obj, container_path)
            validated_data_list = sorted(validated_data_list, key=lambda x: x["param_value"] if x["param_value"] else 0)

            idx = 0
            while idx < len(validated_data_list):
                self.validation_result = False
                validated_data = validated_data_list[idx]
                if idx == len(validated_data_list) - 1 or validated_data["param_value"] in ("", None, "<empty>"):
                    self.validation_result = True
                elif validated_data["param_value"] != validated_data_list[idx + 1]["param_value"]:
                    self.validation_result = True
                else:
                    self.validation_result = False

                repeated_path_list = [validated_data["param_path"]]
                idx += 1
                if not self.validation_result:
                    while (
                        idx < len(validated_data_list)
                        and validated_data_list[idx]["param_value"] == validated_data["param_value"]
                    ):
                        repeated_path_list.append(validated_data_list[idx]["param_path"])
                        idx += 1
                validation_status = "pass" if self.validation_result else "fail"
                self.vlog(
                    self.semantic_rule_data.rule_name,
                    self.semantic_rule_data.rule_summary,
                    self.semantic_rule_data.rule_message,
                    repeated_path_list,
                    validation_status,
                    self.semantic_rule_data.auto_solve_list,
                    self.semantic_rule_data.manual_solve_list,
                )

    def multi_value_repeatability_validation(self, mod_path, container_list):
        for container_path, container_obj in container_list:
            param_ref_cfg_dict = {}
            validated_data_list = SemanticRuleUtil.find_validated_parameter(mod_path, container_obj, container_path)
            for param_info_dict in validated_data_list:
                if isinstance(param_info_dict["param_value"], list):
                    for param_value in param_info_dict["param_value"]:
                        if param_value not in param_ref_cfg_dict:
                            param_ref_cfg_dict[param_value] = []
                        param_ref_cfg_dict[param_value].append(param_info_dict["param_path"])
                elif isinstance(param_info_dict["param_value"], str):
                    if param_info_dict["param_value"] not in param_ref_cfg_dict:
                        param_ref_cfg_dict[param_info_dict["param_value"]] = []
                    param_ref_cfg_dict[param_info_dict["param_value"]].append(param_info_dict["param_path"])

            for ref_string, param_path_list in param_ref_cfg_dict.items():
                validation_status = "fail" if len(param_path_list) > 1 else "pass"

                self.vlog(
                    self.semantic_rule_data.rule_name,
                    self.semantic_rule_data.rule_summary,
                    self.semantic_rule_data.rule_message,
                    param_path_list,
                    validation_status,
                    self.semantic_rule_data.auto_solve_list,
                    self.semantic_rule_data.manual_solve_list,
                )
