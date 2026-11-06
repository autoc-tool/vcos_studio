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
from PySide6.QtCore import QEvent
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QMenu, QHBoxLayout, QLabel, QToolButton, QComboBox


class ArgQComboBox(QHBoxLayout):

    def __init__(self, show_data_dict, basic_ui_handler, validation_ui, tool_btn, callback=None, main_window=None):
        super().__init__()
        self.callback = callback
        self.show_data_dict = show_data_dict
        self.basic_ui_handler = basic_ui_handler
        self.validation_ui = validation_ui
        self.main_window = main_window
        self.over_view_ui = self.main_window.over_view_ui
        self.tool_btn = tool_btn
        self.param_value = show_data_dict["cfg_value"]
        self.default_value = show_data_dict["default_value"]
        self.is_lock = show_data_dict["is_lock"]
        self.annotation_status = show_data_dict["annotation_status"]
        self.is_necessary = show_data_dict["is_necessary"]
        self.enum_item_list = show_data_dict["enum_item_list"]
        self.linked_flag = False  # 是否是被联动的配置项
        self.init_layout()
        self.init_signal_connect_slot()
        self.ashes_and_locks()
        self.basic_validation_handler()

    def init_signal_connect_slot(self):
        self.item_box.currentTextChanged.connect(self.on_text_changed_slot)
        self.set_default_value_action.triggered.connect(self.set_default_value_slot)
        self.set_user_defined_action.triggered.connect(self.set_user_defined_slot)
        self.remove_user_defined_action.triggered.connect(self.remove_user_defined_slot)
        pass

    def ashes_and_locks(self):

        if self.is_lock is False:
            if self.annotation_status is False:
                self.item_box.setEnabled(False)
                self.set_user_defined_action.setEnabled(True)
                self.remove_user_defined_action.setEnabled(False)
                self.set_default_value_action.setEnabled(False)
            elif self.annotation_status is True:
                self.item_box.setEnabled(True)
                self.set_user_defined_action.setEnabled(False)
                self.remove_user_defined_action.setEnabled(True)
                self.set_default_value_action.setEnabled(self.set_default_value_status())
            else:
                self.item_box.setEnabled(True)
                self.set_user_defined_action.setEnabled(True)
                self.remove_user_defined_action.setEnabled(False)
                self.set_default_value_action.setEnabled(self.set_default_value_status())
        else:
            self.item_box.setEnabled(False)
            self.set_user_defined_action.setEnabled(False)
            self.remove_user_defined_action.setEnabled(False)
            self.set_default_value_action.setEnabled(False)

    def set_tool_btn_status(self, tool_btn, status_type, ui_result_list=[]):
        if tool_btn:
            tool_btn.set_error_down(status_type, ui_result_list, True)
            if "Error" == status_type or "Warning" == status_type or "Hint" == status_type:
                tool_btn.tool_btn_down.setEnabled(True)
            if "Pass" == status_type:
                if len(tool_btn.tool_btn_down.validation_result) == 0:
                    tool_btn.tool_btn_down.setEnabled(False)
                    tool_btn.tool_btn_down.setIcon(QIcon(""))

    def init_layout(self):
        self.item_box = CustomComboBox()
        self.item_box.addItems(self.enum_item_list)
        self.box_and_icon = QHBoxLayout()
        self.box_and_icon.addWidget(self.item_box)
        if self.is_necessary:
            necessary_icon = QLabel("*")
            necessary_icon.setFixedSize(10, 18)
            self.box_and_icon.addWidget(necessary_icon)

        # add QToolButton
        triangleButton = QToolButton()
        triangleButton.setFixedSize(18, 18)
        triangleButton.setPopupMode(QToolButton.InstantPopup)
        triangleButton.setAutoRaise(True)
        menu = QMenu()
        # Create the click menu
        self.set_default_value_action = QAction("Set Default Value")
        self.set_user_defined_action = QAction("Set User Defined")
        self.remove_user_defined_action = QAction("Remove User Defined")

        menu.addAction(self.set_default_value_action)
        menu.addSeparator()
        menu.addAction(self.set_user_defined_action)
        menu.addSeparator()
        menu.addAction(self.remove_user_defined_action)
        triangleButton.setMenu(menu)
        self.box_and_icon.addWidget(triangleButton)
        self.box_and_icon.addStretch(15)
        self.addLayout(self.box_and_icon)
        self.item_box.setCurrentText(self.param_value)
        self.item_box.set_old_data()

    def on_text_changed_slot(self, text):
        self.callback(
            "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
            text,
            self.show_data_dict["cfg_value"],
            self.show_data_dict["mod_path"],
            self.show_data_dict["module"],
            self.show_data_dict["ecuc_path"],
            self.show_data_dict["tag"],
        )
        self.show_data_dict["cfg_value"] = text

        # 同步修改联动配置项
        self.callback(
            "bsw_editor_update_linked_cfg_item",
            self.show_data_dict["module"],
            self.show_data_dict["mod_path"],
            self.show_data_dict["ecuc_path"],
            self.item_box.currentText(),
            getattr(self, "updated_path_dict", {self.show_data_dict["ecuc_path"]: [self.show_data_dict["mod_path"]]}),
            self.basic_ui_handler,
            self.callback,
            self.main_window,
        )
        # 入栈
        self.callback(
            "bsw_editor_input_push_stack",
            self.item_box.old_data,
            self.item_box.currentText(),
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
        self.item_box.set_old_data()

        # Validation
        self.basic_validation_handler()
        self.validation_ui.validation_model.update_model_data()

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
        ui_result_list = self.callback("validation_param", cbk_param)
        # 拿到结果，首先将控件置为Pass
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

    def set_default_value_status(self):
        if self.is_lock is True:
            return False
        if self.default_value:
            return True
        return False

    def set_default_value_slot(self):
        if self.default_value:
            self.item_box.setCurrentText(self.default_value)
            self.item_box.set_old_data()

    def set_user_defined_slot(self):
        self.user_defined = self.callback(
            "bsw_editor_set_user_defined",
            None,
            self.show_data_dict["mod_path"],
            self.show_data_dict["module"],
            self.show_data_dict["ecuc_path"],
            self.show_data_dict["tag"],
        )
        self.set_user_defined_action.setEnabled(False)
        self.remove_user_defined_action.setEnabled(True)
        self.item_box.setEnabled(True)
        self.set_default_value_action.setEnabled(self.set_default_value_status())

    def remove_user_defined_slot(self):
        self.user_defined = self.callback(
            "bsw_editor_remove_user_defined",
            None,
            self.show_data_dict["mod_path"],
            self.show_data_dict["module"],
            self.show_data_dict["ecuc_path"],
            self.show_data_dict["tag"],
        )
        self.remove_user_defined_action.setEnabled(False)
        self.set_user_defined_action.setEnabled(True)
        self.item_box.setEnabled(False)
        self.set_default_value_action.setEnabled(False)


class CustomComboBox(QComboBox):
    """
    重新方法，禁止使用鼠标滚轮功能
    """

    def __init__(self):
        super().__init__()
        self.old_data = None

    def wheelEvent(self, e):
        if e.type() == QEvent.Wheel:
            e.ignore()

    def set_old_data(self):
        self.old_data = self.currentText()
