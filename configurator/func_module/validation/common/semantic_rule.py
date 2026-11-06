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
from func_module.validation.common.basic_rule import BasicRule
from func_module.validation.common.validation_def import ValidationData, ExceptionRuleLog
from func_module.validation.common.repeatability_rule import SemanticRepeatabilityRule
from func_module.validation.common.continuity_rule import SemanticContinuityRule
from func_module.validation.common.same_container_linkage_rule import SemanticSameContainerLinkageRule
from func_module.validation.common.diff_container_linkage_rule import DiffContainerLinkageRule


class SemanticRuleValidator(BasicRule):
    """单个模块的语义校验器"""

    def __init__(self, module_name, semantic_rules, validation_data: ValidationData):
        self.module_name = module_name
        self.semantic_rules = semantic_rules
        self.validation_data = validation_data
        self.logs = {}

    def validate(self):
        for semantic_rule_name, semantic_rule_data in self.semantic_rules.items():
            rule_obj = None
            if semantic_rule_data.rule_type == "repeatability_check":
                rule_obj = SemanticRepeatabilityRule(self.logs, semantic_rule_data, self.validation_data)
            elif semantic_rule_data.rule_type == "continuity_check":
                rule_obj = SemanticContinuityRule(self.logs, semantic_rule_data, self.validation_data)
            elif semantic_rule_data.rule_type == "same_container_linkage_check":
                rule_obj = SemanticSameContainerLinkageRule(self.logs, semantic_rule_data, self.validation_data)
            elif semantic_rule_data.rule_type == "diff_container_linkage_check":
                rule_obj = DiffContainerLinkageRule(self.logs, semantic_rule_data, self.validation_data)
            if rule_obj is None:
                message = f"The rule_type of {semantic_rule_name} is not supported now"
                ExceptionRuleLog.set_rule_exception_log(
                    self.logs, self.module_name, semantic_rule_data.rule_name[-6:], message
                )
                continue

            try:
                if rule_obj.check_validation_run():
                    rule_obj.validation_run()
            except Exception as e:
                ExceptionRuleLog.set_rule_exception_log(
                    self.logs, self.module_name, semantic_rule_data.rule_name[-6:], str(e)
                )

        return self.logs
