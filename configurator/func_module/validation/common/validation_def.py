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
def check_args(func):

    def wrapper(self, validation_mark, summary, message, path, result, auto_solve_list=[], manual_solve_list=[]):
        if not validation_mark[-6:].isdigit():
            print("*************************************************************")
            print(f"{validation_mark}  {summary}  {message}  {path}  {result}")
            print(f"{validation_mark} does not conform to the specification")
            return

        if result not in ["fail", "pass"]:
            print("*************************************************************")
            print(f"{validation_mark}  {summary}  {message}  {path}  {result} fail")
            print(f"{result} does not conform to the specification")
            return

        return func(self, validation_mark, summary, message, path, result, auto_solve_list, manual_solve_list)

    return wrapper


class ValidationData:

    def __init__(
        self,
        autosar_asw_class,
        autosar_bsw_class,
        autosar_ib_class,
        autosar_system_class,
        autosar_mod_class,
        sys_info_class,
    ):
        self.autosar_asw_class = autosar_asw_class
        self.autosar_bsw_class = autosar_bsw_class
        self.autosar_ib_class = autosar_ib_class
        self.autosar_system_class = autosar_system_class
        self.autosar_mod_class = autosar_mod_class
        self.sys_info_class = sys_info_class
        self.bsw_ecuc_dict = {}
        pass


class ValidationLogAttrIdx:
    # Index of all attributes of validation_info in the validation_logs
    message = 0
    path = 1
    result = 2
    auto_solve = 3
    manual_solve = 4
    attr_cnt = 5


class ValidationResult:

    def __init__(self, validation_mark, summary, message, path, result, auto_solve_list=[], manual_solve_list=[]):
        self.validation_mark = validation_mark
        self.summary = summary
        self.message = message
        self.path = path
        self.result = result
        # self.proposal_solution = proposal_solution
        self.auto_solve_list = auto_solve_list
        self.manual_solve_list = manual_solve_list


class ValidationLog:

    def __init__(self):
        self.validation_logs_dict = {}
        pass

    @staticmethod
    def get_combined_key(validation_mark, param_path_list: list):
        return f"{validation_mark}_{'_'.join(param_path_list)}"

    @check_args
    def vlog(self, validation_mark, summary, message, path_list, result, auto_solve_list=[], manual_solve_list=[]):
        if not isinstance(path_list, list):
            path_list = [path_list]
        if validation_mark not in self.logs:
            vdalidation_info = {"time": 0, "summary": "", "info": []}
            self.logs[validation_mark] = vdalidation_info
            self.logs[validation_mark]["summary"] = summary
            self.logs[validation_mark]["info"].append([message, path_list, result, auto_solve_list, manual_solve_list])
            combined_key = self.get_combined_key(validation_mark, path_list)
            self.validation_logs_dict.update({combined_key: 0})
        else:
            # 保证一个校验码下，相同参数路径的结果只有一个（pass/fail）
            # 注意这里虽然只是局部最优，但是整个框架保证了各校验实例只有一份，所以可以保证全局唯一性
            info_len = len(self.logs[validation_mark]["info"])
            self.logs[validation_mark]["info"].append([message, path_list, result, auto_solve_list, manual_solve_list])
            combined_key = self.get_combined_key(validation_mark, path_list)
            if combined_key in self.validation_logs_dict:
                index = self.validation_logs_dict[combined_key]
                info_item = self.logs[validation_mark]["info"][index]
                info_item[0] = message
                info_item[2] = result
                info_item[3] = auto_solve_list
                info_item[4] = manual_solve_list
            else:
                self.validation_logs_dict.update({combined_key: info_len})


class SemanticRuleData:
    """对应语义校验规则配置文件中的单条规则"""

    def __init__(
        self,
        module_name,
        rule_name,
        rule_type,
        rule_ruleset,
        rule_summary,
        rule_message,
        auto_solve_list,
        manual_solve_list,
    ):
        self.module_name = module_name
        self.rule_name = rule_name
        self.rule_type = rule_type
        self.rule_ruleset = rule_ruleset
        self.rule_summary = rule_summary
        self.rule_message = rule_message
        self.auto_solve_list = auto_solve_list
        self.manual_solve_list = manual_solve_list


class ExceptionRuleLog:

    @staticmethod
    def set_rule_exception_log(logs: dict, module_name: str, validation_code: str, message: str):
        validation_mark = f"{module_name.upper()}{validation_code}"
        validation_message = (
            f"exception in {validation_mark}.py; exception detail: {message};"
            "please contact the person responsible for this validation rule for a fix."
        )
        path = [f"/ActiveEcuC/{module_name}/{validation_mark}"]

        if validation_mark not in logs:
            logs[validation_mark] = {"time": 0, "summary": "", "info": []}
            logs[validation_mark]["summary"] = "validation rule exception"
        logs[validation_mark]["info"].append([validation_message, path, "fail", [], []])


# {
#   "Rte": {
#     "time": 2.864006757736206,
#     "logs": {
#       "RTE000001": {
#         "time": 2.864006757736206,
#         "summary": "摘要",
#         "info": [
#           [
#             "错误信息",
#             "错误索引路径1",2,3
#             "pass"
#           ],
#           [
#             "错误信息",
#             "错误索引路径2",
#             "fail"
#           ]
#         ]
#       }
#     }
#   }
# }
