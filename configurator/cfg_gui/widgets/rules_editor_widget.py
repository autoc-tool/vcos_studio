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
from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QFrame, QLineEdit, QCheckBox, QTextEdit, QPlainTextEdit
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtGui import QFont
from basic_func_module.autosar_utils.utils import get_short_name, get_value, get_valueOf
from func_module.health_monitor.logger import logger


class RulesEditorWidget(QWidget):

    def __init__(self, module_name=None, ecuc_cfg=None, click_item="", item_father=""):
        super().__init__()
        self.module_name = module_name
        self.ecuc_cfg = ecuc_cfg
        self.click_item = click_item
        self.item_class = self.get_click_item_class()
        self.triggered_relationships = self.get_all_tiggered_relationships()
        if self.click_item != "" and item_father == "Rules":
            self.set_rules_editor_widget()
        elif self.click_item != "" and item_father == "Expressions":
            self.set_expression_editor_widget()
        elif self.click_item != "" and item_father == "Actions":
            self.set_actions_editor_widget()
        elif self.click_item != "" and item_father == "Action Lists":
            self.set_action_lists_editor_widget()
        elif self.click_item != "" and item_father == "BSW Mode Request Ports":
            self.set_request_ports_editor_widget()
        else:
            self.clear_editor_widget()

    def set_read_only(self, layout):
        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, QLineEdit) or isinstance(widget, QTextEdit) or isinstance(widget, QPlainTextEdit):
                widget.setReadOnly(True)

    # ===========================清空界面===========================
    def clear_editor_widget(self):
        self.setStyleSheet("background:white")
        self.setWindowTitle(f"{self.module_name} Rules Editor")
        layout = QGridLayout()  # 整体布局
        font = QFont()
        font.setBold(True)

        line1 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        label = QLabel("Only Rules/Expressions/Actions/Action Lists/BSW Mode Request Ports supported yet!", font=font)
        line2 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        layout.addWidget(line1, 0, 0, 1, 4)
        layout.addWidget(label, 1, 0, 1, 4)
        layout.addWidget(line2, 2, 0, 1, 4)
        self.setLayout(layout)

    # =========================设置Rules界面=========================
    def set_rules_editor_widget(self):
        # self.resize(800, 600)
        self.setStyleSheet("background:white")
        self.setWindowTitle(f"{self.module_name} Rules Editor")
        layout = QGridLayout()  # 整体布局

        font = QFont()
        font.setBold(True)
        # part1，配置控件
        label1 = QLabel("Settings", font=font)
        line1 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        label2 = QLabel("Short Name:")
        short_name = QLineEdit()
        label3 = QLabel("Nested Execution Only:")
        excution_check_box = QCheckBox()
        label4 = QLabel("Rule Id:")
        rule_id = QLineEdit()
        label5 = QLabel("Rule Init State:")
        rule_init_state = QLineEdit()
        # part1，填充数据
        short_name.setText(get_short_name(self.item_class))
        excution_check_box.setChecked(self.get_excution_check_box_status())
        rule_id.setText(self.get_rule_id())
        rule_init_state.setText(self.get_rule_init_state())

        # part2
        label6 = QLabel("Excution", font=font)
        line2 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        label7 = QLabel(f"{self.module_name}_DEFERRED execution:")
        deferred_execution = QLineEdit()
        label8 = QLabel(f"{self.module_name}_IMMEDIATE execution:")
        immediate_execution = QLineEdit()
        # part2，填充数据
        index_deferred = 0
        index_immediate = 0
        category, content = self.get_execution_category_content()
        for index, value in enumerate(category):
            if "DEFERRED" in value:
                index_deferred = 1
                if deferred_execution.text() != "":
                    deferred_execution.setText(deferred_execution.text() + "; " + content[index])
                else:
                    deferred_execution.setText(content[index])
            elif "IMMEDIATE" in value:
                index_immediate = 1
                if immediate_execution.text() != "":
                    immediate_execution.setText(immediate_execution.text() + "; " + content[index])
                else:
                    immediate_execution.setText(content[index])
            else:
                # TODO
                pass

        # part3
        label9 = QLabel("Expression", font=font)
        line3 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        label10 = QLabel("Referenced Expression:")
        ref_expression = QLineEdit()
        ref_expression_text_edit = QTextEdit()
        # part3，填充数据
        ref_expression_value, true_action_list_value, false_action_list_value = self.get_ecuc_reference_value()
        ref_expression.setText(ref_expression_value)
        ref_expression_dict = {}
        ref_expression_dict.update(
            {ref_expression_value.split("/")[-1]: self.get_reference_expression_value(ref_expression_value)}
        )
        ref_expression_str = self.ref_expression_dict_trans_to_str(ref_expression_dict, 0)
        self.ref_expression_str_to_list(ref_expression_text_edit, ref_expression_str)

        # part4
        # 没有Actions True to True 的时候标题显示 No Actions when Expression evaluates to True
        # 有Actions True to True 且 trigger的时候标题显示
        # Actions when Expression evaluation result changes from (False to True)
        # 有Actions True to True 且 conditon的时候标题显示 Actions when Expression evaluation to True--暂时固定成这个
        label11 = QLabel("Actions when Expression evaluates to True", font=font)
        line4 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        label12 = QLabel("  True Action List:")
        true_action_list = QLineEdit()
        label13 = QLabel("  Action List Execution:")
        true_action_list_execution = QLineEdit()
        label14 = QLabel("  Action List Priority:")
        true_action_list_priority = QLineEdit()
        # part4，填充数据
        true_action_list.setText(true_action_list_value)
        true_action_list_execution_value = self.get_true_action_list_execution(true_action_list_value)
        true_action_list_execution.setText(true_action_list_execution_value)

        # part5
        label15 = QLabel("  Triggering Rules", font=font)
        line5 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        label16 = QLabel("  This action list is not triggered by any other rules.")

        # part6
        label17 = QLabel("  Actions", font=font)
        line6 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        true_actions_edit = QPlainTextEdit()
        # part6，填充数据
        true_actions_edit.setPlainText(self.get_true_actions_list())
        # TODO 点击不同的链接，实例化不同的控件出来

        # part 7
        # 没有Actions True to False的时候标题显示 No Actions when Expression evaluates to False
        # 有Actions True to False 且 trigger的时候标题显示
        # Actions when Expression evaluation result changes from (True to False)
        # 有Actions True to False 且 conditon的时候标题显示 Actions when Expression evaluation to False--暂时固定成这个
        label18 = (
            QLabel("No Actions when Expression evaluates to False", font=font)
            if false_action_list_value is None
            else QLabel("Actions when Expression evaluation to False", font=font)
        )
        label19 = QLabel("  False Action List:")
        false_action_list = QLineEdit()
        label20 = QLabel("  Action List Execution:")
        false_action_list_execution = QLineEdit()
        label21 = QLabel("  Action List Priority:")
        false_action_list_priority = QLineEdit()
        # part7，填充数据
        false_action_list.setText(false_action_list_value)
        false_action_list_execution_value = self.get_false_action_list_execution(false_action_list_value)
        false_action_list_execution.setText(false_action_list_execution_value)

        # Part 8
        label22 = QLabel("  Triggering Rules", font=font)
        line7 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        label23 = QLabel("  No action list referenced.")

        # Part 9
        label24 = QLabel("  Actions", font=font)
        line8 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        false_actions_edit = QPlainTextEdit()
        # part9，填充数据
        false_actions_edit.setPlainText(self.get_false_actions_list())

        # 配置界面
        layout.addWidget(label1, 0, 0, 1, 4)
        layout.addWidget(line1, 1, 0, 1, 4)
        layout.addWidget(label2, 2, 0, 1, 1)
        layout.addWidget(short_name, 2, 1, 1, 3)
        layout.addWidget(label3, 3, 0, 1, 1)
        layout.addWidget(excution_check_box, 3, 1, 1, 3)
        layout.addWidget(label4, 4, 0, 1, 1)
        layout.addWidget(rule_id, 4, 1, 1, 3)
        layout.addWidget(label5, 5, 0, 1, 1)
        layout.addWidget(rule_init_state, 5, 1, 1, 3)
        layout.addWidget(label6, 6, 0, 1, 4)
        layout.addWidget(line2, 7, 0, 1, 4)
        if index_deferred:
            layout.addWidget(label7, 8, 0, 1, 1)
            layout.addWidget(deferred_execution, 8, 1, 1, 3)
        if index_immediate:
            layout.addWidget(label8, 9, 0, 1, 1)
            layout.addWidget(immediate_execution, 9, 1, 1, 3)
        layout.addWidget(label9, 10, 0, 1, 4)
        layout.addWidget(line3, 11, 0, 1, 4)
        layout.addWidget(label10, 12, 0, 1, 1)
        layout.addWidget(ref_expression, 12, 1, 1, 3)
        layout.addWidget(ref_expression_text_edit, 13, 0, 1, 4)
        layout.addWidget(label11, 14, 0, 1, 4)
        layout.addWidget(line4, 15, 0, 1, 4)
        layout.addWidget(label12, 16, 0, 1, 1)
        layout.addWidget(true_action_list, 16, 1, 1, 3)
        layout.addWidget(label13, 17, 0, 1, 1)
        layout.addWidget(true_action_list_execution, 17, 1, 1, 3)
        layout.addWidget(label14, 18, 0, 1, 1)
        layout.addWidget(true_action_list_priority, 18, 1, 1, 3)
        layout.addWidget(label15, 19, 0, 1, 4)
        layout.addWidget(line5, 20, 0, 1, 4)
        layout.addWidget(label16, 21, 0, 1, 4)
        layout.addWidget(label17, 22, 0, 1, 4)
        layout.addWidget(line6, 23, 0, 1, 4)
        layout.addWidget(true_actions_edit, 24, 0, 1, 1)
        layout.addWidget(label18, 25, 0, 1, 4)
        layout.addWidget(label19, 26, 0, 1, 1)
        layout.addWidget(false_action_list, 26, 1, 1, 3)
        layout.addWidget(label20, 27, 0, 1, 1)
        layout.addWidget(false_action_list_execution, 27, 1, 1, 3)
        layout.addWidget(label21, 28, 0, 1, 1)
        layout.addWidget(false_action_list_priority, 28, 1, 1, 3)
        layout.addWidget(label22, 29, 0, 1, 4)
        layout.addWidget(line7, 30, 0, 1, 4)
        layout.addWidget(label23, 31, 0, 1, 4)
        layout.addWidget(label24, 32, 0, 1, 4)
        layout.addWidget(line8, 33, 0, 1, 4)
        layout.addWidget(false_actions_edit, 34, 0, 1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 3)
        self.set_read_only(layout)
        self.setLayout(layout)

    # 数据处理部分
    def get_click_item_class(self):
        arbitration_container_def = None
        for container_def in self.ecuc_cfg.CONTAINERS.ECUC_CONTAINER_VALUE:
            if get_short_name(container_def) == "BswMConfig":
                for ecuc_container_value in container_def.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                    if get_short_name(ecuc_container_value) == "BswMArbitration":
                        for arbitration_container_def in ecuc_container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                            if get_short_name(arbitration_container_def) == self.click_item:
                                return arbitration_container_def
                    if get_short_name(ecuc_container_value) == "BswMModeControl":
                        for arbitration_container_def in ecuc_container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                            if get_short_name(arbitration_container_def) == self.click_item:
                                return arbitration_container_def

    def get_all_tiggered_relationships(self):
        rv = {}
        for container_def in self.ecuc_cfg.CONTAINERS.ECUC_CONTAINER_VALUE:
            if get_short_name(container_def) == "BswMConfig":
                for ecuc_container_value in container_def.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                    if get_short_name(ecuc_container_value) == "BswMArbitration":
                        for arbitration_container_def in ecuc_container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                            if get_valueOf(arbitration_container_def.DEFINITION_REF).endswith("Rule"):
                                rv.update(
                                    {
                                        get_short_name(arbitration_container_def): {
                                            "ExpressionRef": self.get_expression_ref(arbitration_container_def),
                                            "FalseActionList": self.get_false_action_list(arbitration_container_def),
                                            "TrueActionList": self.get_true_action_list(arbitration_container_def),
                                        }
                                    }
                                )
        return rv

    def get_expression_ref(self, rule_container_value):
        rv = {}
        for item in rule_container_value.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
            if get_valueOf(item.DEFINITION_REF).endswith("RuleExpressionRef"):
                ref_path = get_valueOf(item.VALUE_REF)
                if ref_path:
                    rv.update(
                        {
                            ref_path.split("/")[-1]: {
                                "ref_path": ref_path,
                                "request_ports": self.get_request_ports_list(ref_path),
                            }
                        }
                    )
        return rv

    def get_expression_ref_not_cited_by_rules(self):
        rv = {}
        for container_def in self.ecuc_cfg.CONTAINERS.ECUC_CONTAINER_VALUE:
            if get_short_name(container_def) == "BswMConfig":
                for ecuc_container_value in container_def.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                    if get_short_name(ecuc_container_value) == "BswMArbitration":
                        for arbitration_container_def in ecuc_container_value.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                            if get_valueOf(arbitration_container_def.DEFINITION_REF).endswith("LogicalExpression"):
                                if self.click_item == get_short_name(arbitration_container_def):
                                    rv = arbitration_container_def.get_path()
        return rv

    def get_request_ports_list(self, ref_path):
        rv = []
        for item in self.ecuc_cfg.find(ref_path).REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
            port_ref_path = get_valueOf(item.VALUE_REF)
            for sub_item in self.ecuc_cfg.find(port_ref_path).REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
                rv.append(get_valueOf(sub_item.VALUE_REF).split("/")[-1])
        return rv

    def get_false_action_list(self, rule_container_value):
        rv = {}
        for item in rule_container_value.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
            if get_valueOf(item.DEFINITION_REF).endswith("RuleFalseActionList"):
                if not item.VALUE_REF:
                    continue
                ref_path = get_valueOf(item.VALUE_REF)
                if ref_path:
                    action_list_name = ref_path.split("/")[-1]
                    rv.update({action_list_name: self.get_false_actions(ref_path)})
        return rv

    def get_false_actions(self, ref_path):
        rv = {}
        for item in self.ecuc_cfg.find(ref_path).SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
            false_action = get_valueOf(item.REFERENCE_VALUES.ECUC_REFERENCE_VALUE[0].VALUE_REF).split("/")[-1]
            rv.update({false_action: ref_path})
        return rv

    def get_true_action_list(self, rule_container_value):
        rv = {}
        for item in rule_container_value.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
            if get_valueOf(item.DEFINITION_REF).endswith("RuleTrueActionList"):
                ref_path = get_valueOf(item.VALUE_REF)
                if ref_path:
                    action_list_name = ref_path.split("/")[-1]
                    rv.update({action_list_name: self.get_true_actions(ref_path)})
        return rv

    def get_true_actions(self, ref_path):
        rv = {}
        for item in self.ecuc_cfg.find(ref_path).SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
            true_action = get_valueOf(item.REFERENCE_VALUES.ECUC_REFERENCE_VALUE[0].VALUE_REF).split("/")[-1]
            rv.update({true_action: ref_path})
        return rv

    def get_excution_check_box_status(self):
        num_param_values = self.item_class.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE
        for num_param_value in num_param_values:
            if get_valueOf(num_param_value.DEFINITION_REF).endswith("NestedExecutionOnly"):
                excution_check_box_status = get_value(num_param_value)
                if excution_check_box_status.lower() == "false":
                    return False
                elif excution_check_box_status.lower() == "true":
                    return True
                else:
                    print("unsupported type!")
                    return False

    def get_rule_id(self):
        rule_id = None
        num_param_values = self.item_class.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE
        for num_param_value in num_param_values:
            if get_valueOf(num_param_value.DEFINITION_REF).endswith("RuleId"):
                rule_id = get_value(num_param_value)
                break
        return rule_id

    def get_rule_init_state(self):
        rule_init_state = None
        num_param_values = self.item_class.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE
        for num_param_value in num_param_values:
            if get_valueOf(num_param_value.DEFINITION_REF).endswith("RuleInitState"):
                rule_init_state = get_value(num_param_value)
                break
        return rule_init_state

    def get_ecuc_reference_value(self):
        ref_expression = None
        true_action_list = None
        false_action_list = None
        reference_values = self.item_class.REFERENCE_VALUES.ECUC_REFERENCE_VALUE
        for reference_value in reference_values:
            if not reference_value.VALUE_REF:
                continue
            if get_valueOf(reference_value.DEFINITION_REF).endswith("RuleExpressionRef"):
                ref_expression = get_valueOf(reference_value.VALUE_REF)
            if get_valueOf(reference_value.DEFINITION_REF).endswith("RuleTrueActionList"):
                true_action_list = get_valueOf(reference_value.VALUE_REF)
            if get_valueOf(reference_value.DEFINITION_REF).endswith("RuleFalseActionList"):
                false_action_list = get_valueOf(reference_value.VALUE_REF)
        return ref_expression, true_action_list, false_action_list

    def get_reference_expression_value(self, ref_expression_value):
        ref_expression_dict = {}
        expression_ref = self.item_class.find(ref_expression_value)
        logical_operator = get_value(expression_ref.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE[0])
        if "AND" in logical_operator:
            logical_operator = "&&"
        elif "OR" in logical_operator:
            logical_operator = "||"
        elif "EQUALS_NOT" in logical_operator:
            logical_operator = "!="
        elif "EQUALS" in logical_operator:
            logical_operator = "=="
        else:
            # TODO
            pass
        ref_expression_dict.update({"logical_operator": logical_operator})

        container_values = expression_ref.SUB_CONTAINERS.ECUC_CONTAINER_VALUE
        if container_values:
            # 不为空时，说明循环到底了
            conditon_value = get_value(
                container_values[0].SUB_CONTAINERS.ECUC_CONTAINER_VALUE[0].PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE[0]
            )
            ref_expression_dict.update({"conditon_value": conditon_value})
            value_ref = get_valueOf(expression_ref.REFERENCE_VALUES.ECUC_REFERENCE_VALUE[0].VALUE_REF).split("/")[-1]
            ref_expression_dict.update({"value_ref": value_ref})
        else:
            ref_values = expression_ref.REFERENCE_VALUES.ECUC_REFERENCE_VALUE
            if ref_values:
                for ref_value in ref_values:
                    choice_ref = get_valueOf(ref_value.VALUE_REF)
                    choice_ref_name = get_valueOf(ref_value.VALUE_REF).split("/")[-1]
                    ref_expression_dict.update({choice_ref_name: self.get_reference_expression_value(choice_ref)})
        return ref_expression_dict

    def ref_expression_dict_trans_to_str(self, ref_expression_dict, index):
        ref_expression_str_list = []
        blank_str = "    "
        direction_str = "-    "
        index += 1
        key_index = 0
        if list(ref_expression_dict.keys()) == ["logical_operator", "conditon_value", "value_ref"]:
            ref_expression_str_list.append(
                index * blank_str
                + ref_expression_dict["value_ref"]
                + ref_expression_dict["logical_operator"]
                + ref_expression_dict["conditon_value"]
            )
        else:
            for key, value in ref_expression_dict.items():
                if index == 1:
                    ref_expression_str_list.append(direction_str + (index - 1) * blank_str + key)
                if (
                    "logical_operator" in list(ref_expression_dict.keys())
                    and len(list(ref_expression_dict.keys())) <= 2
                ):
                    if key != "logical_operator":
                        ref_expression_str_list.append((index - 1) * blank_str + direction_str + key)
                elif (
                    "logical_operator" in list(ref_expression_dict.keys()) and len(list(ref_expression_dict.keys())) > 2
                ):
                    if key != "logical_operator":
                        key_index += 1
                        if key_index == 1:
                            ref_expression_str_list.append((index - 1) * blank_str + direction_str + key)
                        else:
                            ref_expression_str_list.append(
                                (index - 1) * blank_str + direction_str + ref_expression_dict["logical_operator"] + key
                            )
                if type(value) is dict:
                    ref_expression_str_list.append(self.ref_expression_dict_trans_to_str(value, index))
        return ref_expression_str_list

    def ref_expression_str_to_list(self, ref_expression_text_edit, ref_expression_str):
        for sub_str in ref_expression_str:
            if type(sub_str) is list:
                self.ref_expression_str_to_list(ref_expression_text_edit, sub_str)
            else:
                ref_expression_text_edit.append(sub_str)

    def get_true_action_list_execution(self, true_action_list_value):
        true_action_list_execution = None
        if true_action_list_value:
            textual_param_values = self.item_class.find(
                true_action_list_value
            ).PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE
            for textual_param_value in textual_param_values:
                if get_valueOf(textual_param_value.DEFINITION_REF).endswith("ActionListExecution"):
                    true_action_list_execution = get_value(textual_param_value)
                    break
        return true_action_list_execution

    def get_false_action_list_execution(self, false_action_list_value):
        false_action_list_execution = None
        if false_action_list_value:
            textual_param_values = self.item_class.find(
                false_action_list_value
            ).PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE
            for textual_param_value in textual_param_values:
                if get_valueOf(textual_param_value.DEFINITION_REF).endswith("ActionListExecution"):
                    false_action_list_execution = get_value(textual_param_value)
                    break
        return false_action_list_execution

    def get_true_actions_list(self):
        true_actions_list = []
        true_actions_list_text = None
        if self.triggered_relationships[self.click_item]["TrueActionList"]:
            for value in self.triggered_relationships[self.click_item]["TrueActionList"].values():
                if value:
                    for action_name in value.keys():
                        true_actions_list.append(action_name)
        true_actions_list_text = "\n".join(true_actions_list)
        return true_actions_list_text

    def get_false_actions_list(self):
        true_actions_list = []
        true_actions_list_text = None
        if self.triggered_relationships[self.click_item]["FalseActionList"]:
            for value in self.triggered_relationships[self.click_item]["FalseActionList"].values():
                for action_name in value.keys():
                    if value:
                        true_actions_list.append(action_name)
        true_actions_list_text = "\n".join(true_actions_list)
        return true_actions_list_text

    def get_execution_category_content(self):
        category = []
        content = []
        value_ref = None
        ref_values = self.item_class.REFERENCE_VALUES.ECUC_REFERENCE_VALUE
        for ref_value in ref_values:
            if get_valueOf(ref_value.DEFINITION_REF).endswith("RuleExpressionRef"):
                value_ref = get_valueOf(ref_value.VALUE_REF)
                break
        if value_ref:
            for item in self.item_class.find(value_ref).REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
                item_path = get_valueOf(item.VALUE_REF)
                content.append(item_path.split("/")[-1])
                if len(self.item_class.find(item_path).REFERENCE_VALUES.ECUC_REFERENCE_VALUE) == 1:
                    sub_item = self.item_class.find(get_valueOf(item.VALUE_REF)).REFERENCE_VALUES.ECUC_REFERENCE_VALUE[
                        0
                    ]
                    if (
                        len(
                            self.item_class.find(
                                get_valueOf(sub_item.VALUE_REF)
                            ).PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE
                        )
                        == 1
                    ):
                        sub_item2 = self.item_class.find(
                            get_valueOf(sub_item.VALUE_REF)
                        ).PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE[0]
                    else:
                        logger.warning("multi values3")
                    category.append(get_value(sub_item2))
                else:
                    logger.warning("multi values2")
        return category, content

    # =========================设置Expressions界面======================
    def set_expression_editor_widget(self):
        self.setStyleSheet("background:white")
        self.setWindowTitle(f"{self.module_name} Rules Editor")
        layout = QGridLayout()  # 整体布局
        font = QFont()
        font.setBold(True)

        # 设置控件
        label1 = QLabel("Name:")
        Name = QLineEdit()
        label2 = QLabel("Triggered Rules:", font=font)
        line1 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        label3 = QLabel("Rules triggered by this expression:")
        Triggered_rules = QLineEdit()
        label4 = QLabel("Expression:", font=font)
        line2 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        expression_text_edit = QTextEdit()
        # 填充数据
        Name.setText(get_short_name(self.item_class))
        triggered_rules_str, ref_expression_value = self.get_expression_triggerd_rules()
        if not ref_expression_value:
            # 没解析到，说明这个Expression没有被rules调用，需要单独进行解析
            ref_expression_value = self.get_expression_ref_not_cited_by_rules()
        Triggered_rules.setText(triggered_rules_str)
        ref_expression_dict = {}
        ref_expression_dict.update(
            {ref_expression_value.split("/")[-1]: self.get_reference_expression_value(ref_expression_value)}
        )
        ref_expression_str = self.ref_expression_dict_trans_to_str(ref_expression_dict, 0)
        self.ref_expression_str_to_list(expression_text_edit, ref_expression_str)

        # 配置界面
        layout.addWidget(label1, 0, 0, 1, 1)
        layout.addWidget(Name, 0, 1, 1, 3)
        layout.addWidget(label2, 1, 0, 1, 4)
        layout.addWidget(line1, 2, 0, 1, 4)
        layout.addWidget(label3, 3, 0, 1, 1)
        layout.addWidget(Triggered_rules, 3, 1, 1, 3)
        layout.addWidget(label4, 4, 0, 1, 4)
        layout.addWidget(line2, 5, 0, 1, 4)
        layout.addWidget(expression_text_edit, 6, 0, 1, 4)
        layout.setRowStretch(7, 10)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 3)
        self.set_read_only(layout)
        self.setLayout(layout)

    # 数据处理部分
    def get_expression_triggerd_rules(self):
        triggered_rules_list = []
        expression_ref = None
        for rule, value in self.triggered_relationships.items():
            if self.click_item in value["ExpressionRef"]:
                triggered_rules_list.append(rule)
                expression_ref = value["ExpressionRef"][self.click_item]["ref_path"]
        triggered_rules_str = "; ".join(triggered_rules_list)
        return triggered_rules_str, expression_ref

    # =========================设置Request ports界面======================
    def set_request_ports_editor_widget(self):
        self.setStyleSheet("background:white")
        self.setWindowTitle(f"{self.module_name} Rules Editor")
        layout = QGridLayout()  # 整体布局
        font = QFont()
        font.setBold(True)

        # 设置控件
        label1 = QLabel("Name:")
        Name = QLineEdit()
        label2 = QLabel("Type:")
        Type = QLineEdit()
        label3 = QLabel("Request Processing:")
        Request_processing = QLineEdit()
        label4 = QLabel("Arbitrate On Init:")
        arbitrate_check_box = QCheckBox()
        label5 = QLabel("Init Value:")
        Init_value = QLineEdit()
        label6 = QLabel("Source:", font=font)
        line1 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        # 有区别的部分1
        label7 = QLabel("Mode Requester Id:")
        mode_requester_id = QLineEdit()
        label8 = QLabel("Request Mode Max:")
        Request_mode_max = QLineEdit()
        label9 = QLabel("Generic Request Modes:", font=font)
        line2 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        expression_table_widget = QTableWidget()
        expression_table_widget.setRowCount(3)
        expression_table_widget.setColumnCount(4)
        expression_table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        expression_table_widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        expression_table_widget.setEditTriggers(QTableWidget.NoEditTriggers)  # 只读
        # 共同的部分
        label10 = QLabel("Trigger Rules:", font=font)
        line3 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        label11 = QLabel("Rules triggered by this port:")
        rules_triggered = QLineEdit()
        # 有区别的部分2
        label12 = QLabel("ComM Channel Ref:")
        label13 = QLabel("User Condition:")
        comm_channel_ref = QLineEdit()

        # 填充数据
        Name.setText(get_short_name(self.item_class))
        arbitrate_check_box.setChecked(self.get_arbitrate_check_box_status())
        Request_processing.setText(self.get_request_processing())
        Init_value.setText(self.get_init_value())
        user_condition, user_condition_value = self.get_user_condition()
        if user_condition:
            comm_channel_ref.setText(user_condition_value)
        else:
            comm_channel_ref.setText(self.get_comm_channel_ref())

        condition1 = self.get_condition()
        if condition1:
            requesterId, requestedModeMax = self.get_requester_id()
            mode_requester_id.setText(requesterId)
            Request_mode_max.setText(requestedModeMax)

        rules_triggered.setText(self.get_request_ports_triggerd_rules())

        # 填充标题
        expression_table_widget.setItem(0, 0, QTableWidgetItem(f"{self.module_name}GenericRequestModes"))
        expression_table_widget.setItem(0, 1, QTableWidgetItem("Generic Request Mode Value"))
        expression_table_widget.setItem(0, 2, QTableWidgetItem("Generic Request Port Value Ref"))

        # 配置界面
        layout.addWidget(label1, 0, 0, 1, 1)
        layout.addWidget(Name, 0, 1, 1, 3)
        layout.addWidget(label2, 1, 0, 1, 1)
        layout.addWidget(Type, 1, 1, 1, 3)
        layout.addWidget(label3, 2, 0, 1, 1)
        layout.addWidget(Request_processing, 2, 1, 1, 3)
        layout.addWidget(label4, 3, 0, 1, 2)
        layout.addWidget(arbitrate_check_box, 3, 1, 1, 3)
        layout.addWidget(label5, 4, 0, 1, 1)
        layout.addWidget(Init_value, 4, 1, 1, 3)
        layout.addWidget(label6, 5, 0, 1, 4)
        layout.addWidget(line1, 6, 0, 1, 4)
        if condition1:
            layout.addWidget(label7, 7, 0, 1, 1)
            layout.addWidget(mode_requester_id, 7, 1, 1, 3)
            layout.addWidget(label8, 8, 0, 1, 1)
            layout.addWidget(Request_mode_max, 8, 1, 1, 3)
            layout.addWidget(label9, 9, 0, 1, 4)
            layout.addWidget(line2, 10, 0, 1, 4)
            layout.addWidget(expression_table_widget, 11, 0, 1, 4)
            layout.addWidget(label10, 12, 0, 1, 4)
            layout.addWidget(line3, 13, 0, 1, 4)
            layout.addWidget(label11, 14, 0, 1, 1)
            layout.addWidget(rules_triggered, 14, 1, 1, 3)
            layout.setRowStretch(15, 10)
        else:
            if user_condition:
                layout.addWidget(label13, 7, 0, 1, 1)
            else:
                layout.addWidget(label12, 7, 0, 1, 1)
            layout.addWidget(comm_channel_ref, 7, 1, 1, 3)
            layout.addWidget(label10, 8, 0, 1, 4)
            layout.addWidget(line3, 9, 0, 1, 4)
            layout.addWidget(label11, 10, 0, 1, 1)
            layout.addWidget(rules_triggered, 10, 1, 1, 3)
            layout.setRowStretch(11, 10)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 3)
        self.set_read_only(layout)
        self.setLayout(layout)

    def get_arbitrate_check_box_status(self):
        rv = False
        if self.item_class.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
            rv = get_value(self.item_class.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE[0]).lower() == "true"
        return rv

    def get_request_processing(self):
        rv = None
        # if self.item_class.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
        #     if get_valueOf(self.item_class.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE[0].DEFINITION_REF).endswith(
        #             'RequestProcessing'):
        #         rv = get_value(self.item_class.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE[0])
        if self.item_class.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE:
            if get_valueOf(self.item_class.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE[0].DEFINITION_REF).endswith(
                "RequestProcessing"
            ):
                rv = get_value(self.item_class.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE[0])
        return rv

    def get_init_value(self):
        rv = None
        for item in self.item_class.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
            if get_short_name(item).endswith("InitValue"):
                rv = get_value(item.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE[0])
        return rv

    def get_comm_channel_ref(self):
        rv = None
        for item in self.item_class.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
            if get_short_name(item).endswith("RequestSource"):
                if item.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                    if item.SUB_CONTAINERS.ECUC_CONTAINER_VALUE[0].REFERENCE_VALUES:
                        if hasattr(item.SUB_CONTAINERS.ECUC_CONTAINER_VALUE[0].REFERENCE_VALUES, "VALUE_REF"):
                            rv = get_valueOf(item.SUB_CONTAINERS.ECUC_CONTAINER_VALUE[0].REFERENCE_VALUES.VALUE_REF)
        return rv

    def get_condition(self):
        rv = False
        for item in self.item_class.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
            if get_short_name(item).endswith("RequestSource"):
                for sub_item in item.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                    if get_short_name(sub_item).endswith("GenericRequest"):
                        rv = True
        return rv

    def get_user_condition(self):
        condition = False
        value = None
        for item in self.item_class.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
            if get_short_name(item).endswith("RequestSource"):
                for sub_item in item.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                    if get_short_name(sub_item).endswith("ConditionRequest"):
                        condition = True
                        value = get_value(sub_item.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE)
        return condition, value

    def get_requester_id(self):
        requesterId = None
        requestedModeMax = None
        for item in self.item_class.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
            if get_short_name(item).endswith("RequestSource"):
                for sub_item in item.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                    if get_short_name(sub_item).endswith("GenericRequest"):
                        for sub_item2 in sub_item.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                            if get_valueOf(sub_item2.DEFINITION_REF).endswith("RequesterId"):
                                requesterId = get_value(sub_item2)
                            elif get_valueOf(sub_item2.DEFINITION_REF).endswith("RequestedModeMax"):
                                requestedModeMax = get_value(sub_item2)
        return requesterId, requestedModeMax

    def get_request_ports_triggerd_rules(self):
        rv = None
        triggered_rules_list = []
        for rule, value in self.triggered_relationships.items():
            for _, sub_value in value["ExpressionRef"].items():
                if self.click_item in sub_value["request_ports"]:
                    triggered_rules_list.append(rule)
        rv = "; ".join(triggered_rules_list)
        return rv

    # =========================设置Actions界面======================
    def set_actions_editor_widget(self):
        self.setStyleSheet("background:white")
        self.setWindowTitle(f"{self.module_name} Rules Editor")
        layout = QGridLayout()  # 整体布局
        font = QFont()
        font.setBold(True)

        # 设置控件
        # 共同部分1
        label1 = QLabel("Name:")
        Name = QLineEdit()
        # 有区别部分1
        label2 = QLabel("Com Allowed:")
        com_allowed_check_box = QCheckBox()
        label3 = QLabel("ComM Allow Channel Ref:")
        Channel_ref = QLineEdit()
        # 有区别部分2--UserCallout
        label4 = QLabel("Callout Parameter List:")
        callout_parameter = QLineEdit()
        label5 = QLabel("Create Callout:")
        callout_check_box = QCheckBox()
        label6 = QLabel("User Callout Function:")
        callout_function = QLineEdit()
        label7 = QLabel("User Code:")
        user_code_text_edit = QTextEdit()
        label8 = QLabel("User Include File:")
        user_include_file = QLineEdit()
        # 有区别的部分3--TimerControl
        label9 = QLabel("Timer Actions:")
        timer_actions = QLineEdit()
        label10 = QLabel("Timer Ref:")
        timer_ref = QLineEdit()
        label11 = QLabel("Timer Value:")
        timer_value = QLineEdit()
        # 共同部分2
        label12 = QLabel("Triggering Rules:", font=font)
        line1 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        label13 = QLabel("Rules triggering this action:")
        rules_trigger = QLineEdit()

        # 填充数据
        Name.setText(get_short_name(self.item_class))
        actions_condition = self.get_actions_condition()
        if actions_condition == "TimerControl":
            timer_action_value, timer_value_value, timer_ref_value = self.get_timer_control_values()
            timer_actions.setText(timer_action_value)
            timer_value.setText(timer_value_value)
            timer_ref.setText(timer_ref_value)
        elif actions_condition == "UserCallout":
            # callout_parameter
            # callout_check_box
            callout_function.setText(self.get_actions_callout_function())
            # user_code_text_edit
            # user_include_file
        rules_trigger.setText(self.get_actions_rules_trigger())

        # 配置界面
        layout.addWidget(label1, 0, 0, 1, 1)
        layout.addWidget(Name, 0, 1, 1, 3)
        if actions_condition == "Others":
            layout.addWidget(label2, 1, 0, 1, 1)
            layout.addWidget(com_allowed_check_box, 1, 1, 1, 3)
            layout.addWidget(label3, 2, 0, 1, 1)
            layout.addWidget(Channel_ref, 2, 1, 1, 3)
            layout.addWidget(label12, 3, 0, 1, 4)
            layout.addWidget(line1, 4, 0, 1, 4)
            layout.addWidget(label13, 5, 0, 1, 1)
            layout.addWidget(rules_trigger, 5, 1, 1, 3)
            layout.setRowStretch(6, 10)
        elif actions_condition == "UserCallout":
            layout.addWidget(label4, 1, 0, 1, 1)
            layout.addWidget(callout_parameter, 1, 1, 1, 3)
            layout.addWidget(label5, 2, 0, 1, 1)
            layout.addWidget(callout_check_box, 2, 1, 1, 3)
            layout.addWidget(label6, 3, 0, 1, 1)
            layout.addWidget(callout_function, 3, 1, 1, 3)
            layout.addWidget(label7, 4, 0, 1, 1)
            layout.addWidget(user_code_text_edit, 4, 1, 1, 3)
            layout.addWidget(label8, 5, 0, 1, 1)
            layout.addWidget(user_include_file, 5, 1, 1, 3)
            layout.addWidget(label12, 6, 0, 1, 4)
            layout.addWidget(line1, 7, 0, 1, 4)
            layout.addWidget(label13, 8, 0, 1, 1)
            layout.addWidget(rules_trigger, 8, 1, 1, 3)
            layout.setRowStretch(9, 10)
        elif actions_condition == "TimerControl":
            layout.addWidget(label9, 1, 0, 1, 1)
            layout.addWidget(timer_actions, 1, 1, 1, 3)
            layout.addWidget(label10, 2, 0, 1, 1)
            layout.addWidget(timer_ref, 2, 1, 1, 3)
            layout.addWidget(label11, 3, 0, 1, 1)
            layout.addWidget(timer_value, 3, 1, 1, 3)
            layout.addWidget(label12, 6, 0, 1, 4)
            layout.addWidget(line1, 7, 0, 1, 4)
            layout.addWidget(label13, 8, 0, 1, 1)
            layout.addWidget(rules_trigger, 8, 1, 1, 3)
            layout.setRowStretch(9, 10)
        else:
            # TODO
            pass
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 3)
        self.set_read_only(layout)
        self.setLayout(layout)

    # 数据处理部分
    def get_com_allowed_check_box_status(self):
        rv = None
        return rv

    def get_actions_condition(self):
        rv = None
        for item in self.item_class.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
            for sub_item in item.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                if get_valueOf(sub_item.DEFINITION_REF).endswith("TimerControl"):
                    rv = "TimerControl"
                elif get_valueOf(sub_item.DEFINITION_REF).endswith("UserCallout"):
                    rv = "UserCallout"
                else:
                    rv = "Others"
        return rv

    def get_timer_control_values(self):
        timer_action = None
        timer_value = None
        timer_ref = None
        for item in self.item_class.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
            for sub_item in item.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
                timer_action = get_value(sub_item.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE[0])
                timer_value = get_value(sub_item.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE[0])
                timer_ref = get_valueOf(sub_item.REFERENCE_VALUES.ECUC_REFERENCE_VALUE[0].VALUE_REF)
        return timer_action, timer_value, timer_ref

    def get_actions_rules_trigger(self):
        rules_list = []
        rv = None
        for rule, value in self.triggered_relationships.items():
            if value["TrueActionList"]:
                for _, sub_value in value["TrueActionList"].items():
                    if self.click_item in sub_value:
                        rules_list.append(rule)
            if value["FalseActionList"]:
                for _, sub_value in value["FalseActionList"].items():
                    if self.click_item in sub_value:
                        rules_list.append(rule)
        rv = "; ".join(rules_list)
        return rv

    def get_actions_callout_function(self):
        rv = None
        function_list = []
        para_values = (
            self.item_class.SUB_CONTAINERS.ECUC_CONTAINER_VALUE[0]
            .SUB_CONTAINERS.ECUC_CONTAINER_VALUE[0]
            .PARAMETER_VALUES
        )
        for item in para_values.ECUC_TEXTUAL_PARAM_VALUE:
            if get_valueOf(item.DEFINITION_REF).endswith("UserCalloutFunction"):
                function_list.append(get_value(item))
        rv = "; ".join(function_list)
        return rv

    # =========================设置Action lists界面======================
    def set_action_lists_editor_widget(self):
        self.setStyleSheet("background:white")
        self.setWindowTitle(f"{self.module_name} Rules Editor")
        layout = QGridLayout()  # 整体布局
        font = QFont()
        font.setBold(True)

        # 设置控件
        label1 = QLabel("Short Name:")
        short_name = QLineEdit()
        label2 = QLabel("Action List Execution:")
        action_list_execution = QLineEdit()
        label3 = QLabel("Action List Priority:")
        action_list_priority = QLineEdit()
        label4 = QLabel("Triggering Rules:", font=font)
        line1 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        label5 = QLabel("This action list is triggered by:")
        action_list_triggered = QLineEdit()
        label6 = QLabel("Items:", font=font)
        line2 = QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken)
        items_text_edit = QTextEdit()
        # 填充数据
        short_name.setText(get_short_name(self.item_class))
        action_list_execution.setText(self.get_action_list_excution())
        # action_list_priority # TDDO，待补充
        action_list_triggered.setText(self.get_action_lists_rules_trigger())
        items_text_edit.setText(self.get_action_lists_items())

        # 配置界面
        layout.addWidget(label1, 0, 0, 1, 1)
        layout.addWidget(short_name, 0, 1, 1, 3)
        layout.addWidget(label2, 1, 0, 1, 1)
        layout.addWidget(action_list_execution, 1, 1, 1, 3)
        layout.addWidget(label3, 2, 0, 1, 1)
        layout.addWidget(action_list_priority, 2, 1, 1, 3)
        layout.addWidget(label4, 3, 0, 1, 4)
        layout.addWidget(line1, 4, 0, 1, 4)
        layout.addWidget(label5, 5, 0, 1, 1)
        layout.addWidget(action_list_triggered, 5, 1, 1, 3)
        layout.addWidget(label6, 6, 0, 1, 4)
        layout.addWidget(line2, 7, 0, 1, 4)
        layout.addWidget(items_text_edit, 8, 0, 1, 1)
        layout.setRowStretch(9, 10)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 3)
        self.set_read_only(layout)
        self.setLayout(layout)

    def get_action_list_excution(self):
        rv = ""
        rv = get_value(self.item_class.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE[0])
        return rv

    def get_action_lists_rules_trigger(self):
        rules_list = []
        rv = ""
        for rule, value in self.triggered_relationships.items():
            if value["TrueActionList"]:
                if self.click_item in value["TrueActionList"]:
                    rules_list.append(rule)
            if value["FalseActionList"]:
                if self.click_item in value["FalseActionList"]:
                    rules_list.append(rule)
        rv = "; ".join(rules_list)
        return rv

    def get_action_lists_items(self):
        rv = ""
        items_list = []
        for item in self.item_class.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
            items_list.append(get_short_name(item))
        rv = "\n".join(items_list)
        return rv
