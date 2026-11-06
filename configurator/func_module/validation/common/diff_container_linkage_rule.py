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
import copy
from func_module.health_monitor.logger import logger
from func_module.validation.common.basic_rule import BasicRule, timing_decorator
from func_module.validation.common.validation_def import SemanticRuleData, ValidationData
from func_module.validation.common.semantic_rule_util import SemanticRuleUtil


class DiffContainerLinkageRule(BasicRule):

    def __init__(self, logs, semantic_rule_data: SemanticRuleData, validation_data: ValidationData) -> None:
        super().__init__()
        self.logs = logs
        self.semantic_rule_data = semantic_rule_data
        self.validation_data = validation_data

    def check_validation_run(self):
        if not self.modules_are_exist([self.semantic_rule_data.module_name], self.validation_data.bsw_ecuc_dict):
            return False
        return True

    def execute_judge_expression(self, condition_judgement, params_info_dict) -> bool:
        # if condition is empty, indicates that no condition is required -> return true
        if not condition_judgement:
            return True

        judge_expression = condition_judgement["judge_expression"]
        for path_idx, mod_path in enumerate(condition_judgement["mod_path"]):
            try:
                replaced_str = SemanticRuleUtil.param_value_2_expression_str(params_info_dict[mod_path]["param_value"])
                judge_expression = judge_expression.replace(f"%{path_idx}", replaced_str)
            except Exception as e:
                raise Exception(f"Failed to replace variable in judge expression: {e}")

        judge_result = eval(judge_expression)

        return judge_result

    def parse_mod_path_list_val(self, path_list):
        validate_data_dict = {}
        for mod_path in path_list:
            module_name = SemanticRuleUtil.get_module_name_from_mod_path(mod_path)
            module_ecuc_dict = self.validation_data.bsw_ecuc_dict[module_name]["ArPackages"]["ActiveEcuC"][module_name]
            validate_data_list = SemanticRuleUtil.find_validated_parameter(
                mod_path, module_ecuc_dict, f"/ActiveEcuC/{module_name}"
            )
            mod_parent_path = SemanticRuleUtil.get_parent_path(mod_path)
            validate_data_dict.setdefault(mod_parent_path, {})

            for validate_data in validate_data_list:
                ecuc_container_name = SemanticRuleUtil.get_parent_path(validate_data["param_path"])
                validate_data_dict[mod_parent_path].setdefault(ecuc_container_name, {})
                validate_data_dict[mod_parent_path][ecuc_container_name][mod_path] = validate_data

        return validate_data_dict

    def get_param_path_list(self, param_info):
        path_list = []
        for _, ecuc_info in param_info.items():
            path_list.append(ecuc_info["param_path"])
        return path_list

    def handle_auto_solve_by_set_value(self, auto_solve_list: list, judge_path_list: list):
        # handle auto solve info
        curr_auto_solve_list = copy.deepcopy(auto_solve_list)
        for auto_solve in curr_auto_solve_list:
            param_name = auto_solve.get("parameter", "").split("/")[-1]
            param_path_list = [path for path in judge_path_list if path.split("/")[-1] == param_name]
            if len(param_path_list) != 1:
                logger.error("auto solve parameter configure error")
                auto_solve["error"] = True
            else:
                auto_solve["parameter"] = param_path_list[0]
        final_auto_solve = [auto_solve for auto_solve in curr_auto_solve_list if not auto_solve.get("error")]
        return final_auto_solve

    @timing_decorator
    def validation_run(self):
        for ruleset in self.semantic_rule_data.rule_ruleset.values():
            rule_condition, rule_judgement = ruleset.get("condition", {}), ruleset.get("judgement")
            condition_dict = self.parse_mod_path_list_val(rule_condition.get("mod_path", []))
            judgement_dict = self.parse_mod_path_list_val(rule_judgement.get("mod_path", []))
            if condition_dict:
                if not condition_dict:
                    continue
                elif len(condition_dict) == 1:
                    cond_mod_parent_path = list(condition_dict.keys())[0]
                    for _, cond_param_info in condition_dict[cond_mod_parent_path].items():
                        if not self.execute_judge_expression(rule_condition, cond_param_info):
                            continue
                        cond_path_list = self.get_param_path_list(cond_param_info)
                        self.run_judgement_logic(
                            rule_judgement, ruleset.get("auto_solve_list", []), judgement_dict, cond_path_list
                        )
                else:
                    logger.ui_error(
                        "At present, it's not supported to have more than 2 container parameters in the condition."
                    )
                    continue
            # condition is not confiured -> just check judgement info
            else:
                self.run_judgement_logic(rule_judgement, ruleset.get("auto_solve_list", []), judgement_dict, [])

    def run_judgement_logic(self, rule_judgement, auto_solve_list, judgement_dict, cond_path_list):
        if len(judgement_dict) == 1:
            self.run_judgement_in_one_container(rule_judgement, auto_solve_list, judgement_dict, cond_path_list)
        elif len(judgement_dict) == 2:
            self.run_judgement_in_two_container(rule_judgement, auto_solve_list, judgement_dict, cond_path_list)
        else:
            logger.ui_error(f"judgement configuration error!: {self.semantic_rule_data.rule_name}")

    def run_judgement_in_one_container(self, rule_judgement, auto_solve_list, judgement_dict, cond_path_list):
        # run judgement
        judge_mod_parent_path = list(judgement_dict.keys())[0]
        for _, judge_param_info in judgement_dict[judge_mod_parent_path].items():
            judge_result = self.execute_judge_expression(rule_judgement, judge_param_info)
            # save all relevant parameter path
            judge_path_list = []
            judge_path_list.extend(cond_path_list)
            judge_path_list.extend(self.get_param_path_list(judge_param_info))
            if judge_result:
                self.vlog(
                    self.semantic_rule_data.rule_name,
                    self.semantic_rule_data.rule_summary,
                    self.semantic_rule_data.rule_message,
                    judge_path_list,
                    "pass",
                )
            else:
                final_auto_solve = self.handle_auto_solve_by_set_value(auto_solve_list, judge_path_list)
                self.vlog(
                    self.semantic_rule_data.rule_name,
                    self.semantic_rule_data.rule_summary,
                    self.semantic_rule_data.rule_message,
                    judge_path_list,
                    "fail",
                    final_auto_solve,
                )

    def run_judgement_in_two_container(self, rule_judgement, auto_solve_list, judgement_dict, cond_path_list):
        mod_parent_path_1, mod_parent_path_2 = judgement_dict.keys()
        for _, judge_param_info_1 in judgement_dict[mod_parent_path_1].items():
            for _, judge_param_info_2 in judgement_dict[mod_parent_path_2].items():
                judge_param_info = copy.deepcopy(judge_param_info_1)
                judge_param_info.update(judge_param_info_2)
                judge_result = self.execute_judge_expression(rule_judgement, judge_param_info)

                # save all relevant parameter path
                judge_path_list = []
                judge_path_list.extend(cond_path_list)
                judge_path_list.extend(self.get_param_path_list(judge_param_info))
                if judge_result:
                    self.vlog(
                        self.semantic_rule_data.rule_name,
                        self.semantic_rule_data.rule_summary,
                        self.semantic_rule_data.rule_message,
                        judge_path_list,
                        "pass",
                    )
                else:
                    final_auto_solve = self.handle_auto_solve_by_set_value(auto_solve_list, judge_path_list)
                    self.vlog(
                        self.semantic_rule_data.rule_name,
                        self.semantic_rule_data.rule_summary,
                        self.semantic_rule_data.rule_message,
                        judge_path_list,
                        "fail",
                        [],
                        final_auto_solve,
                    )
