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
from PySide6 import QtGui
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QRegularExpression as QRegExp
from PySide6.QtGui import QPalette, QRegularExpressionValidator as QRegExpValidator, QDoubleValidator
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QToolButton
from PySide6.QtWidgets import QMessageBox, QMenu, QLabel
from cfg_gui.widgets.table_widget import ArgTableWidget
import re

ECUC_REF_VALUE_LIST = [
    "ECUC-REFERENCE-DEF",
    "ECUC-CHOICE-REFERENCE-DEF",
    "ECUC-FOREIGN-REFERENCE-DEF",
    "ECUC-SYMBOLIC-NAME-REFERENCE-DEF",
    "ECUC-INSTANCE-REFERENCE-DEF",
]


class ArgQLineEdit(QHBoxLayout):

    def __init__(
        self,
        show_data_dict,
        basic_ui_handler,
        validation_ui,
        tool_btn,
        callback=None,
        show_data_dicts=None,
        select_ref_target=None,
        main_window=None,
    ):
        super().__init__()
        self.show_data_dict = show_data_dict
        self.show_data_dicts = show_data_dicts
        self.basic_ui_handler = basic_ui_handler
        self.validation_ui = validation_ui
        self.tool_btn = tool_btn
        self.callback = callback
        self.select_ref_target = select_ref_target
        self.main_window = main_window
        self.over_view_ui = self.main_window.over_view_ui
        self.param_value = show_data_dict["cfg_value"]
        self.default_value = show_data_dict["default_value"]
        self.num_format = show_data_dict["num_format"]
        self.is_lock = show_data_dict["is_lock"]
        self.annotation_status = show_data_dict["annotation_status"]
        self.is_necessary = show_data_dict["is_necessary"]
        self.pre_name = None
        self.linked_flag = False  # 是否是被联动的配置项
        self.get_pre_cfg_to_display()
        self.init_layout()
        self.init_numerical_check()
        self.init_signal_connect_slot()
        self.ashes_and_locks()

    def get_pre_cfg_to_display(self):
        """获取parameter的上次配置进制改动并恢复界面显示"""
        # pre_cfg表示获取到的上次保存的模块container下的配置项的信息
        pre_cfg = self.callback("get_module_container_pre_cfg")
        cur_data = self.show_data_dict
        key_list = [cur_data["module"], cur_data["ecuc_path"], cur_data["label_name"]]

        def judge_cfg_existed(pre_cfg, key_list=None):
            for key in key_list:
                if not isinstance(pre_cfg, dict):
                    return False, None
                if key in pre_cfg:
                    pre_cfg = pre_cfg[key]
                else:
                    return False, None
            return True, pre_cfg

        is_found, format_value = judge_cfg_existed(pre_cfg, key_list)
        if is_found:
            self.num_format = format_value

    def ashes_and_locks(self):

        if self.is_lock is False:
            if self.annotation_status is False:
                self.set_enabled(self.line_box, False)
                if self.select_ref_target is not None:
                    self.select_ref_target.setEnabled(False)
                self.set_user_defined_action.setEnabled(True)
                self.remove_user_defined_action.setEnabled(False)
                self.set_default_value_action.setEnabled(False)
            elif self.annotation_status is True:
                self.set_enabled(self.line_box, True)
                if self.select_ref_target is not None:
                    self.select_ref_target.setEnabled(True)
                self.set_user_defined_action.setEnabled(False)
                self.remove_user_defined_action.setEnabled(True)
                self.set_default_value_action.setEnabled(self.set_default_value_status())
            else:
                self.set_enabled(self.line_box, True)
                if self.select_ref_target is not None:
                    self.select_ref_target.setEnabled(True)
                self.set_user_defined_action.setEnabled(True)
                self.remove_user_defined_action.setEnabled(False)
                self.set_default_value_action.setEnabled(self.set_default_value_status())
        else:
            self.set_enabled(self.line_box, not self.is_lock)
            if self.select_ref_target is not None:
                self.select_ref_target.setEnabled(False)
            self.set_user_defined_action.setEnabled(False)
            self.remove_user_defined_action.setEnabled(False)
            self.show_ref_in_basic_editor.setEnabled(False)
            self.show_all_ref_configuration_items.setEnabled(False)
            self.set_default_value_action.setEnabled(False)

    def init_signal_connect_slot(self):
        self.line_box.textChanged.connect(lambda _: self.on_input_empty_slot())
        self.line_box.editingFinished.connect(self.editing_finished_slot)
        self.line_box.inputRejected.connect(self.on_input_rejected_slot)
        self.set_default_value_action.triggered.connect(self.set_default_value_slot)
        self.set_user_defined_action.triggered.connect(self.set_user_defined_slot)
        self.remove_user_defined_action.triggered.connect(self.remove_user_defined_slot)
        self.show_ref_in_basic_editor.triggered.connect(self.show_ref_in_basic_editor_slot)
        self.show_all_ref_configuration_items.triggered.connect(
            self.show_all_ref_configuration_items_by_ref_target_slot
        )

    def set_type_validator(self, num_format, line_box):
        if "ECUC-INTEGER-PARAM-DEF" == self.show_data_dict["tag"]:
            reg = QRegExp("")
            if "hex" == num_format:
                reg = QRegExp("0[xX][0-9a-fA-F]+|-0[xX][0-9a-fA-F]")
            elif "dec" == num_format:
                reg = QRegExp("-?[0-9]+|[0-9]")
            elif "bin" == num_format:
                reg = QRegExp("0[b][0-1]+|-0[b][0-1]")
            elif "oct" == num_format:
                reg = QRegExp("0[o][0-7]+|-0[o][0-7]")
            else:  # 对于没有初值的int类型配置项，统一允许输入0-9
                reg = QRegExp("-?[0-9]+|[0-9]")
            reg_val = QRegExpValidator(self)
            reg_val.setRegularExpression(reg)
            line_box.setValidator(reg_val)
        elif (
            "ECUC-STRING-PARAM-DEF" == self.show_data_dict["tag"]
            or "ECUC-FUNCTION-PARAM-DEF" == self.show_data_dict["tag"]
        ):
            reg = QRegExp(r"[a-zA-Z0-9_.,\(\)\-\>\&\*\[\]\s\=\;\!]+$")
            reg_val = QRegExpValidator(self)
            reg_val.setRegularExpression(reg)
            line_box.setValidator(reg_val)
        elif "ECUC-FLOAT-PARAM-DEF" == self.show_data_dict["tag"]:
            doubleValidator = QDoubleValidator(self)
            line_box.setValidator(doubleValidator)
        else:
            # TODO
            pass

    def init_numerical_check(self):

        base = ""
        if self.param_value:
            self.line_box.setText(str(self.param_value))
            if self.num_format is not None:
                # 保存当前value的format格式，下次切回刷新时基于全局变量更新显示
                base = self.num_format
        if base:
            if base == "dec":
                self.line_box.set_decimal()
            elif base == "bin":
                self.line_box.set_binary()
            elif base == "oct":
                self.line_box.set_octal()
            elif base == "hex":
                self.line_box.set_hexadecimal()
        self.pre_name = self.line_box.text()

        self.set_type_validator(self.num_format, self.line_box)
        # Validation
        self.basic_validation_handler()
        self.line_box.setCursorPosition(0)
        self.validation_ui.validation_model.update_model_data()

    def init_layout(self):
        self.line_box = CustomLineEdit(num_format=self.num_format, show_data_dict=self.show_data_dict)
        self.set_enabled(self.line_box, not self.is_lock)
        self.line_button_layout = QHBoxLayout()
        triangle_button = QToolButton()
        triangle_button.setFixedSize(18, 18)
        triangle_button.setPopupMode(QToolButton.InstantPopup)
        triangle_button.setAutoRaise(True)
        menu = QMenu(triangle_button)
        # Create the click menu
        self.set_default_value_action = QAction("Set Default Value", self)
        self.set_default_value_action.setEnabled(self.set_default_value_status())
        self.set_user_defined_action = QAction("Set User Defined", self)
        self.remove_user_defined_action = QAction("Remove User Defined", self)
        self.show_ref_in_basic_editor = QAction("Show Referenced Item In Basic Editor (Tree)", self)
        self.show_ref_in_basic_editor.setVisible(False)
        self.show_all_ref_configuration_items = QAction(
            "Show all ref configuration items that reference this ref target", self
        )
        self.show_all_ref_configuration_items.setVisible(False)

        menu.addAction(self.set_default_value_action)
        menu.addSeparator()
        menu.addAction(self.set_user_defined_action)
        menu.addSeparator()
        menu.addAction(self.remove_user_defined_action)
        menu.addSeparator()
        menu.addAction(self.show_ref_in_basic_editor)
        menu.addSeparator()
        menu.addAction(self.show_all_ref_configuration_items)

        triangle_button.setMenu(menu)

        self.line_button_layout.addWidget(self.line_box)
        necessary_icon = QLabel(" ")
        if self.is_necessary:
            necessary_icon = QLabel("*")
        self.line_button_layout.addWidget(necessary_icon)
        self.line_button_layout.addWidget(triangle_button)
        self.addLayout(self.line_button_layout)

        # range judge
        self.range_judge = QAction(self)
        self.line_box.addAction(self.range_judge, CustomLineEdit.TrailingPosition)
        self.show_element_usage = ArgTableWidget(self.basic_ui_handler)

    def set_enabled(self, widget: QLineEdit, is_enabled):

        if self.select_ref_target is not None:
            self.select_ref_target.setEnabled(is_enabled)
        if self.show_data_dict["tag"] in ECUC_REF_VALUE_LIST:
            return
        widget.setReadOnly(not is_enabled)
        palette = widget.palette()
        if is_enabled:
            black_color = QtGui.QColor(0, 0, 0)
            palette.setColor(QPalette.ColorRole.Text, black_color)
            white_color = QtGui.QColor(255, 255, 255)
            palette.setColor(QPalette.ColorRole.Window, white_color)
            widget.setPalette(palette)
        else:
            gray_color = QtGui.QColor(128, 128, 128)
            palette.setColor(QPalette.ColorRole.Text, gray_color)
            bcream_color = QtGui.QColor(240, 240, 240)
            palette.setColor(QPalette.ColorRole.Window, bcream_color)
            widget.setPalette(palette)

    def on_input_empty_slot(self):
        if "SHORT-NAME" == self.show_data_dict["tag"]:
            if (
                self.line_box.text().strip() == "" or self.line_box.text() != self.line_box.text().rstrip()
            ):  # Short Name首尾不允许出现空白字符
                return

        # 由于输入为空时不会触发editingFinished，所以当输入为空时需要调用此函数来进行判断
        if "" == self.line_box.text():
            if "SHORT-NAME" == self.show_data_dict["tag"]:  # 不允许ShortName为""的情况,直接返回
                return
            self.callback(
                "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                "",
                self.show_data_dict["cfg_value"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            self.show_data_dict["cfg_value"] = self.line_box.text()
            # 同步修改联动配置项
            self.callback(
                "bsw_editor_update_linked_cfg_item",
                self.show_data_dict["module"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["ecuc_path"],
                self.line_box.text(),
                getattr(
                    self, "updated_path_dict", {self.show_data_dict["ecuc_path"]: [self.show_data_dict["mod_path"]]}
                ),
                self.basic_ui_handler,
                self.callback,
                self.main_window,
            )
            # 若更新数据则入栈
            if self.line_box.old_data != self.line_box.text():
                self.callback(
                    "bsw_editor_input_push_stack",
                    self.line_box.old_data,
                    self.line_box.text(),
                    getattr(self, "undo_module_name", self.show_data_dict["module"]),
                    self.show_data_dict,
                    self.callback,
                    self.over_view_ui,
                    self.basic_ui_handler,
                    type(self),
                    self.linked_flag,
                    getattr(self, "modify_lock_flag", False),
                    self.is_lock,
                )
                # 更新旧数据
                self.line_box.old_data = self.line_box.text()

                # Validation
                self.basic_validation_handler()
                self.validation_ui.validation_model.update_model_data()
        else:
            # 将修改的Interger类型配置项的进制等信息写回
            if "ECUC-INTEGER-PARAM-DEF" == self.show_data_dict["tag"] and self.show_data_dict["num_format"] is not None:
                self.show_data_dict["num_format"] = self.line_box.num_format
                self.callback(
                    "update_module_container_pre_cfg", self.show_data_dict, result_callback=self.write_back_format_info
                )
            # Validation
            self.basic_validation_handler()
            self.validation_ui.validation_model.update_model_data()

    def write_back_format_info(self, show_data_dict):
        self.callback(
            "bsw_editor_set_integer_format",
            show_data_dict["module"],
            show_data_dict["mod_path"],
            show_data_dict["ecuc_path"],
            self.line_box.text(),
            show_data_dict["tag"],
            show_data_dict["num_format"],
        )

    def show_ref_in_basic_editor_slot(self):
        self.basic_ui_handler.ecuc_path_jumps_to_ui(self.line_box.text())

    def editing_finished_slot(self):

        # If the widget has parent tree element, it means the widget shows the name of container
        new_value = self.line_box.text()
        if "ECUC-INTEGER-PARAM-DEF" == self.show_data_dict["tag"]:  # 所有int类型的配置项，值都保存为十进制
            new_value_number = self.line_box.every_format_to_int(new_value)
            new_value = str(new_value_number) if new_value_number is not None else ""
        if new_value == self.show_data_dict["cfg_value"]:
            return
        if new_value == "<empty>":
            # 弹窗中选择"<empty>"，保留实体，将value值置为None
            self.callback(
                "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                None,
                self.show_data_dict["cfg_value"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            self.line_box.setText("")
            self.show_data_dict["cfg_value"] = None
            self.basic_validation_handler()  # LineEdit中删除ref配置项后，也要执行Validation
            self.validation_ui.validation_model.update_model_data()
            return
        if "SHORT-NAME" == self.show_data_dict["tag"]:
            if (
                self.line_box.text().strip() == "" or self.line_box.text() != self.line_box.text().rstrip()
            ):  # Short Name首尾不允许出现空白字符
                return
            if len(new_value) == 0:  # Short Name长度不允许为0
                # self.line_box.setText(self.pre_name)
                return
            final_short_name, bsw_ecuc_dict = self.callback(
                "update_container_short_name_to_ecuc_arxml",
                new_value,
                self.show_data_dict["cfg_value"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            self.over_view_ui.refresh_bsw_view_tree(self.show_data_dict["module"])
            if final_short_name != new_value:
                self.line_box.blockSignals(True)
                self.line_box.setText(final_short_name)
                self.line_box.blockSignals(False)
            self.callback(
                "bsw_editor_update_all_configuration_items_that_reference_this_ref",
                final_short_name,
                self.show_data_dict["cfg_value"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            # 覆盖路径中有多个self.show_data_dict["cfg_value"]的情况，例如下面的路径有多个"EcucPartition"
            # /ActiveEcuC/EcuC/EcucPartitionCollection/EcucPartition
            pattern = re.compile(
                re.escape(self.show_data_dict["cfg_value"])
                + r"(?!.*"
                + re.escape(self.show_data_dict["cfg_value"])
                + ")"
            )
            new_ecuc_path = pattern.sub(final_short_name, self.show_data_dict["ecuc_path"])
            self.update_show_data_dicts_ecuc_path(new_ecuc_path)
            # 更新container旧名称
            self.pre_name = self.show_data_dict["cfg_value"]
            self.show_data_dict["cfg_value"] = final_short_name

            # 去除修改前的名字对应的错误日志
            self.update_modified_container_validaition_info(final_short_name, new_ecuc_path)
            # 同步修改联动配置项
            self.callback(
                "bsw_editor_update_linked_cfg_item",
                self.show_data_dict["module"],
                self.show_data_dict["mod_path"] + "/ShortName",  # ShortName配置项的ecuc路径要特殊处理
                self.show_data_dict["ecuc_path"],
                self.line_box.text(),
                getattr(
                    self, "updated_path_dict", {self.show_data_dict["ecuc_path"]: [self.show_data_dict["mod_path"]]}
                ),
                self.basic_ui_handler,
                self.callback,
                self.main_window,
            )
            # 若更新数据则入栈
            if self.line_box.old_data != self.line_box.text():
                self.callback(
                    "bsw_editor_input_push_stack",
                    self.line_box.old_data,
                    self.line_box.text(),
                    getattr(self, "undo_module_name", self.show_data_dict["module"]),
                    self.show_data_dict,
                    self.callback,
                    self.over_view_ui,
                    self.basic_ui_handler,
                    type(self),
                    self.linked_flag,
                    getattr(self, "modify_lock_flag", False),
                    self.is_lock,
                )
                # 更新旧数据
                self.line_box.old_data = self.line_box.text()
                self.basic_validation_handler()
                self.validation_ui.validation_model.update_model_data()
            return

        if self.show_data_dict["has_obj"] is True:
            # show_data_dict中有obj，直接更新
            self.callback(
                "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                new_value,
                self.show_data_dict["cfg_value"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
        else:
            # show_data_dict中没有obj，需要创建对象
            self.callback(
                "bsw_editor_add_param_item_and_write_to_ecuc_arxml",
                new_value,
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
        # 更新container旧名称
        self.pre_name = self.show_data_dict["cfg_value"]
        self.show_data_dict["cfg_value"] = new_value
        # 同步修改联动配置项
        self.callback(
            "bsw_editor_update_linked_cfg_item",
            self.show_data_dict["module"],
            self.show_data_dict["mod_path"],
            self.show_data_dict["ecuc_path"],
            self.line_box.text(),
            getattr(self, "updated_path_dict", {self.show_data_dict["ecuc_path"]: [self.show_data_dict["mod_path"]]}),
            self.basic_ui_handler,
            self.callback,
            self.main_window,
        )

        # 若更新数据则入栈
        if self.line_box.old_data != self.line_box.text():
            self.callback(
                "bsw_editor_input_push_stack",
                self.line_box.old_data,
                self.line_box.text(),
                getattr(self, "undo_module_name", self.show_data_dict["module"]),
                self.show_data_dict,
                self.callback,
                self.over_view_ui,
                self.basic_ui_handler,
                type(self),
                self.linked_flag,
                getattr(self, "modify_lock_flag", False),
                self.is_lock,
            )
            # 更新旧数据
            self.line_box.old_data = self.line_box.text()
            # Validation
            self.basic_validation_handler()
            self.validation_ui.validation_model.update_model_data()

    def update_show_data_dicts_ecuc_path(self, new_ecuc_path):

        for key, show_data in self.show_data_dicts.items():
            show_data[0]["ecuc_path"] = new_ecuc_path

    def basic_validation_handler(self):
        cbk_param = {}
        cbk_param["param_name"] = self.show_data_dict["label_name"]
        cbk_param["check_text"] = self.show_data_dict["cfg_value"]
        cbk_param["param_path"] = self.show_data_dict["ecuc_path"] + "/" + self.show_data_dict["label_name"]
        cbk_param["tag"] = self.show_data_dict["tag"]
        cbk_param["lower_multiplicity"] = self.show_data_dict["lower_multiplicity"]
        cbk_param["upper_multiplicity"] = self.show_data_dict["upper_multiplicity"]
        cbk_param["upper_multiplicity_infinite"] = self.show_data_dict["upper_multiplicity_infinite"]
        cbk_param["is_necessary"] = self.show_data_dict["is_necessary"]
        cbk_param["max_value"] = self.show_data_dict["max_value"]
        cbk_param["min_value"] = self.show_data_dict["min_value"]
        cbk_param["max_length"] = self.show_data_dict["max_length"]
        cbk_param["min_length"] = self.show_data_dict["min_length"]
        cbk_param["mod_path"] = self.show_data_dict["mod_path"]
        cbk_param["default_value"] = self.show_data_dict["default_value"]
        cbk_param["max_interval_type"] = self.show_data_dict["max_interval_type"]
        cbk_param["min_interval_type"] = self.show_data_dict["min_interval_type"]
        ui_result_list = self.callback("validation_param", cbk_param)
        if len(ui_result_list) > 0:
            failed_result_list = []
            for validation_result in ui_result_list:
                if "fail" == validation_result.result:
                    ui_res_dict = {
                        "summary": validation_result.summary,
                        "message": validation_result.message,
                        "validation_mark": validation_result.validation_mark,
                        "path": validation_result.path,
                        "auto_solve_list": validation_result.auto_solve_list,
                        "manual_solve_list": validation_result.manual_solve_list,
                    }
                    failed_result_list.append(ui_res_dict)
            if failed_result_list:
                self.set_tool_btn_status(self.tool_btn, "Error", failed_result_list)
            else:
                self.set_tool_btn_status(self.tool_btn, "Pass")  # 拿到结果，首先将控件置为Pass

    def on_input_rejected_slot(self):

        pass

    def set_default_value_slot(self):
        if self.default_value:
            self.line_box.setText(self.default_value)
            self.line_box.editingFinished.emit()

    def set_user_defined_slot(self):
        self.user_defined = self.callback(
            "bsw_editor_set_user_defined",
            self.show_data_dict["cfg_value"],
            self.show_data_dict["mod_path"],
            self.show_data_dict["module"],
            self.show_data_dict["ecuc_path"],
            self.show_data_dict["tag"],
        )
        self.set_user_defined_action.setEnabled(False)
        self.remove_user_defined_action.setEnabled(True)
        self.set_enabled(self.line_box, True)
        self.set_default_value_action.setEnabled(self.set_default_value_status())

    def remove_user_defined_slot(self):
        self.user_defined = self.callback(
            "bsw_editor_remove_user_defined",
            self.show_data_dict["cfg_value"],
            self.show_data_dict["mod_path"],
            self.show_data_dict["module"],
            self.show_data_dict["ecuc_path"],
            self.show_data_dict["tag"],
        )
        self.remove_user_defined_action.setEnabled(False)
        self.set_user_defined_action.setEnabled(True)
        self.set_enabled(self.line_box, False)
        self.set_default_value_action.setEnabled(False)

    def show_all_ref_configuration_items_by_ref_target_slot(self):

        if self.line_box.text() and "<empty>" != self.line_box.text():
            all_ref_configuration_items_by_ref_target_dict = self.callback(
                "bsw_editor_all_ref_configuration_items_by_ref_target", self.line_box.text()
            )
            self.show_element_usage.fill_reference_target_table_widget(
                "", all_ref_configuration_items_by_ref_target_dict
            )
            if self.show_element_usage.select_reference_target_dialog:
                self.show_element_usage.select_reference_target_dialog.exec()

    def set_default_value_status(self):
        if self.is_lock is True:
            return False
        if self.default_value:
            return True
        return False

    def set_tool_btn_status(self, tool_btn, status_type, ui_result_list=[]):
        if tool_btn:
            tool_btn.set_error_down(status_type, ui_result_list, True)
            if "Error" == status_type or "Warning" == status_type or "Hint" == status_type:
                tool_btn.tool_btn_down.setEnabled(True)
            if "Pass" == status_type:
                if len(tool_btn.tool_btn_down.validation_result) == 0:
                    tool_btn.tool_btn_down.setEnabled(False)
                    tool_btn.tool_btn_down.setIcon(QIcon(""))

    def update_modified_container_validaition_info(self, final_short_name, new_ecuc_path):
        if final_short_name != self.pre_name:
            # 刷新 validation ui 显示最新校验信息
            self.callback(
                "validation_update_modify_container_name",
                self.pre_name,
                new_ecuc_path,
                result_callback=self.validation_ui.validation_model.update_model_data,
            )


class CustomLineEdit(QLineEdit):

    def __init__(self, parent=None, num_format=None, show_data_dict=None):
        super().__init__(parent)
        self.num_format = num_format
        self.show_data_dict = show_data_dict
        if self.num_format:
            self.init_ui()
            self.set_menu_and_button_status()
        self.old_data: str = self.show_data_dict["cfg_value"]
        self.prev_value = ""  # 用于存储上一个文本值

    def init_ui(self):
        self.button = QPushButton(self.num_format, self)
        self.button.adjustSize()
        self.button.setMenu(self.create_menu())
        self.button.setStyleSheet(
            "QPushButton {"
            "    color: gray;"
            "}"
            "QPushButton:hover {"
            # "    background-color: black;"
            "    color: black;"
            "}"
        )
        self.button.move(self.width() - self.button.width(), 0)
        self.button.clicked.connect(self.show_message)

        self.button.clicked.connect(self.show_message)

    def create_menu(self):
        menu = QMenu(self)
        self.binary = menu.addAction("Binary", self.set_binary)
        menu.addSeparator()
        self.octal = menu.addAction("Octal", self.set_octal)
        menu.addSeparator()
        self.decimal = menu.addAction("Decimal", self.set_decimal)
        menu.addSeparator()
        self.hexadecimal = menu.addAction("Hexadecimal", self.set_hexadecimal)
        return menu

    def set_binary(self):
        self.num_format = "bin"
        self.set_type_validator(self.num_format)
        self.set_menu_and_button_status()
        text_value = self.every_format_to_int(self.text())
        self.setText(bin(text_value) if text_value is not None else "")

    def set_octal(self):
        self.num_format = "oct"
        self.set_type_validator(self.num_format)
        self.set_menu_and_button_status()
        text_value = self.every_format_to_int(self.text())
        self.setText(oct(text_value) if text_value is not None else "")

    def set_decimal(self):
        self.num_format = "dec"
        self.set_type_validator(self.num_format)
        self.set_menu_and_button_status()
        text_value = self.every_format_to_int(self.text())
        self.setText(str(text_value) if text_value is not None else "")

    def set_hexadecimal(self):
        self.num_format = "hex"
        self.set_type_validator(self.num_format)
        self.set_menu_and_button_status()
        text_value = self.every_format_to_int(self.text())
        self.setText(hex(text_value) if text_value is not None else "")

    def every_format_to_int(self, text):

        num_int = None
        if text:
            if text.startswith("0x") or text.startswith("0X"):
                num_int = int(text, 16)
            elif text.startswith("0o"):
                num_int = int(text, 8)
            elif text.startswith("0b"):
                num_int = int(text, 2)
            else:
                num_int = int(text)

        return num_int

    def set_type_validator(self, num_format):
        if "hex" == num_format:
            reg = QRegExp("0[xX][0-9a-fA-F]+|-0[xX][0-9a-fA-F]")
        elif "dec" == num_format:
            reg = QRegExp("-?[0-9]+|[0-9]")
        elif "bin" == num_format:
            reg = QRegExp("0[b][0-1]+|-0[b][0-1]")
        elif "oct" == num_format:
            reg = QRegExp("0[o][0-7]+|-0[o][0-7]")
        reg_val = QRegExpValidator(self)
        reg_val.setRegularExpression(reg)
        self.setValidator(reg_val)

    def set_menu_and_button_status(self):
        self.button.setText(self.num_format)
        if "bin" == self.num_format:
            self.binary.setEnabled(False)
            self.octal.setEnabled(True)
            self.decimal.setEnabled(True)
            self.hexadecimal.setEnabled(True)
        elif "oct" == self.num_format:
            self.binary.setEnabled(True)
            self.octal.setEnabled(False)
            self.decimal.setEnabled(True)
            self.hexadecimal.setEnabled(True)
        elif "dec" == self.num_format:
            self.binary.setEnabled(True)
            self.octal.setEnabled(True)
            self.decimal.setEnabled(False)
            self.hexadecimal.setEnabled(True)
        elif "hex" == self.num_format:
            self.binary.setEnabled(True)
            self.octal.setEnabled(True)
            self.decimal.setEnabled(True)
            self.hexadecimal.setEnabled(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 重新计算按钮位置
        if self.num_format:
            self.button.move(self.width() - self.button.width(), 0)

    def show_message(self):
        QMessageBox.information(self, "Message", "You clicked the button!")
