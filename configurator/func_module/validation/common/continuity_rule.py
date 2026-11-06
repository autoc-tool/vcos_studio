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
from durable import lang
from func_module.validation.common.basic_rule import BasicRule, timing_decorator
from func_module.validation.common.validation_def import SemanticRuleData, ValidationData
from func_module.validation.common.semantic_rule_util import SemanticRuleUtil


class SemanticContinuityRule(BasicRule):
    """针对连续性的语义校验"""

    def __init__(self, logs, semantic_rule_data: SemanticRuleData, validation_data: ValidationData) -> None:
        super().__init__()
        self.logs = logs
        self.semantic_rule_data = semantic_rule_data
        self.validation_data = validation_data
        self.validation_result = False
        self.durable_init()

    def durable_init(self):
        try:
            lang.get_host().get_ruleset(self.semantic_rule_data.rule_name)
        except Exception:
            with lang.ruleset(self.semantic_rule_data.rule_name):

                @lang.when_all(+lang.m.status)
                def event(c):
                    pass

                @lang.when_all(lang.m.param_value == lang.m.item_idx)
                def fact(c):
                    self.validation_result = True

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
        for container_path, container_obj in container_list:
            validated_data_list = SemanticRuleUtil.find_validated_parameter(mod_path, container_obj, container_path)
            # support non sorted sequences
            if not self.semantic_rule_data.rule_ruleset.get("disable_sort", False):
                validated_data_list = sorted(
                    validated_data_list, key=lambda x: x["param_value"] if x["param_value"] else 0
                )

            # 2)开始校验
            for idx, validated_data in enumerate(validated_data_list):
                validated_data["item_idx"] = idx
                try:
                    self.validation_result = False
                    lang.assert_fact(self.semantic_rule_data.rule_name, validated_data)
                except Exception:
                    self.validation_result = False

                validation_status = "pass" if self.validation_result else "fail"
                self.vlog(
                    self.semantic_rule_data.rule_name,
                    self.semantic_rule_data.rule_summary,
                    self.semantic_rule_data.rule_message,
                    [validated_data["param_path"]],
                    validation_status,
                    self.semantic_rule_data.auto_solve_list,
                    self.semantic_rule_data.manual_solve_list,
                )

            # 3)清空ruleset中的所有fact，为下一次校验做准备
            if len(validated_data_list) > 0:
                lang.retract_facts(self.semantic_rule_data.rule_name, validated_data_list)
