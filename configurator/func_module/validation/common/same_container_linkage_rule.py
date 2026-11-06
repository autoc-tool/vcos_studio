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


class SemanticSameContainerLinkageRule(BasicRule):
    """针对相同container下配置项联动的语义校验"""

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

                @lang.when_all((lang.m.condition == True) & (lang.m.judgement == True))
                def fact(c):
                    self.validation_result = True

    def check_validation_run(self):
        if not self.modules_are_exist([self.semantic_rule_data.module_name], self.validation_data.bsw_ecuc_dict):
            return False
        return True

    def check_compared_result(self, checked_data, compared_dict):
        """检查输入数据是否满足某种比较关系"""
        value = compared_dict["value"]
        if isinstance(checked_data, (int, float)):
            if isinstance(value, str):
                value = SemanticRuleUtil.str_to_num(value)
        else:
            checked_data = f"'{checked_data}'"
            value = f"'{value}'"

        value_operator = compared_dict["value_operator"]
        compared_state = True
        try:
            compared_state = eval(f"{checked_data} {value_operator} {value}")
        except Exception:
            detail = (
                f"validation json config error in 'mod_path', 'value_operator' or 'value' "
                f"of {self.semantic_rule_data.rule_name}."
            )
            raise Exception(detail)

        return compared_state

    def check_logical_result(self, logical_list):
        """检查输入数据是否满足某种逻辑关系"""
        if len(logical_list) == 0:
            return True

        logical_state = None
        for compared_state, logical_operator in logical_list:
            if logical_state is None:
                logical_state = compared_state
                continue
            logical_state = eval(f"{logical_state} {logical_operator} {compared_state}")

        return logical_state

    @timing_decorator
    def validation_run(self):
        result = True
        module_name = self.semantic_rule_data.module_name
        module_bsw_dict = self.validation_data.bsw_ecuc_dict[module_name]["ArPackages"]["ActiveEcuC"][module_name]
        rulesets = self.semantic_rule_data.rule_ruleset
        for ruleset_name, ruleset in rulesets.items():
            container_list = SemanticRuleUtil.find_validated_container(
                ruleset["base_path"], module_bsw_dict, f"/ActiveEcuC/{module_name}"
            )
            # 遍历container,在每个container中单独进行校验
            for container_path, container_obj in container_list:
                # 在该ruleset下,判断condition是否满足
                condition_list = ruleset.get("condition", [])
                condition_info, validated_path_list, condition_exist = [], [], True
                for condition in condition_list:
                    condition_data_list = SemanticRuleUtil.find_validated_parameter(
                        condition["mod_path"], container_obj, container_path
                    )
                    if not condition_data_list:
                        condition_exist = False
                        break
                    condition_info.append(
                        (
                            self.check_compared_result(condition_data_list[0]["param_value"], condition),
                            condition["logical_operator"],
                        )
                    )
                if not condition_exist:
                    continue
                condition_result = self.check_logical_result(condition_info)
                if condition_result is False:
                    continue
                validated_data = {"condition": True}

                # 若满足condition,则判断judgement是否满足
                judgement_list = ruleset["judgement"]
                judgement_info = []
                for judgement in judgement_list:
                    judgement_data_list = SemanticRuleUtil.find_validated_parameter(
                        judgement["mod_path"], container_obj, container_path
                    )
                    for judgement_data in judgement_data_list:
                        validated_path_list.append(judgement_data["param_path"])
                    judgement_info.append(
                        (
                            self.check_compared_result(judgement_data_list[0]["param_value"], judgement),
                            judgement["logical_operator"],
                        )
                    )
                judgement_result = self.check_logical_result(judgement_info)
                validated_data["judgement"] = judgement_result

                try:
                    self.validation_result = False
                    lang.assert_fact(self.semantic_rule_data.rule_name, validated_data)
                except Exception:
                    self.validation_result = False

                if self.validation_result:
                    self.vlog(
                        self.semantic_rule_data.rule_name,
                        self.semantic_rule_data.rule_summary,
                        self.semantic_rule_data.rule_message,
                        validated_path_list,
                        "pass",
                        [],
                        [],
                    )
                else:
                    self.semantic_rule_data.auto_solve_list = []
                    manual_solve = ""
                    for idx, judgement in enumerate(judgement_list):
                        value = judgement["value"]
                        value_operator = judgement["value_operator"]
                        parameter_path = validated_path_list[idx]
                        manual_solve += f"{parameter_path} {value_operator} '{value}' {judgement['logical_operator']} "
                        if value_operator == "==" or value_operator == ">=" or value_operator == "<=":
                            auto_solve_dict = {
                                "solve_info": f"Set the value '{value}' for {parameter_path}.",
                                "solve_type": "SetValue",
                                "parameter": parameter_path,
                                "value": value,
                            }
                            self.semantic_rule_data.auto_solve_list.append(auto_solve_dict)
                    self.semantic_rule_data.manual_solve_list.append(manual_solve)

                    self.vlog(
                        self.semantic_rule_data.rule_name,
                        self.semantic_rule_data.rule_summary,
                        self.semantic_rule_data.rule_message,
                        list(set(validated_path_list)),
                        "fail",
                        self.semantic_rule_data.auto_solve_list,
                        self.semantic_rule_data.manual_solve_list,
                    )

                if len(validated_data) > 0:
                    lang.retract_facts(self.semantic_rule_data.rule_name, validated_data)

        return result
