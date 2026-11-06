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
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QHBoxLayout, QCheckBox, QLabel, QToolButton, QMenu


class ArgQCheckBox(QHBoxLayout):

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
        self.user_defined = None
        self.linked_flag = False  # 是否是被联动的配置项
        self.init_layout()
        self.init_signal_connect_slot()
        self.ashes_and_locks()

    def ashes_and_locks(self):

        if self.is_lock is False:
            if self.annotation_status is False:
                self.box.setEnabled(False)
                self.set_user_defined_action.setEnabled(True)
                self.remove_user_defined_action.setEnabled(False)
                self.set_default_value_action.setEnabled(False)
            elif self.annotation_status is True:
                self.box.setEnabled(True)
                self.set_user_defined_action.setEnabled(False)
                self.remove_user_defined_action.setEnabled(True)
                self.set_default_value_action.setEnabled(self.set_default_value_status())
            else:
                self.box.setEnabled(True)
                self.set_user_defined_action.setEnabled(True)
                self.remove_user_defined_action.setEnabled(False)
                self.set_default_value_action.setEnabled(self.set_default_value_status())
        else:
            self.box.setEnabled(False)
            self.set_user_defined_action.setEnabled(False)
            self.remove_user_defined_action.setEnabled(False)
            self.set_default_value_action.setEnabled(False)

    def init_signal_connect_slot(self):
        self.box.stateChanged.connect(self.onStateChanged)
        self.set_default_value_action.triggered.connect(self.set_default_value_slot)
        self.set_user_defined_action.triggered.connect(self.set_user_defined_slot)
        self.remove_user_defined_action.triggered.connect(self.remove_user_defined_slot)

    def init_layout(self):
        self.box = QCheckBox()
        value = Qt.PartiallyChecked
        if isinstance(self.param_value, str):
            if self.param_value.lower() in ["false", "0"]:
                value = Qt.Unchecked
            elif self.param_value.lower() in ["true", "1"]:
                value = Qt.Checked
        self.box.setCheckState(value)
        self.box_and_icon = QHBoxLayout()
        self.box_and_icon.addWidget(self.box)
        if self.is_necessary:
            necessary_icon = QLabel("*")
        else:
            necessary_icon = QLabel("")
        necessary_icon.setFixedSize(10, 18)
        self.box_and_icon.addWidget(necessary_icon)
        self.old_data = self.show_data_dict["cfg_value"]  # 初始化旧状态

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

    def onStateChanged(self, text):
        value_table = {
            Qt.Checked: "true",
            Qt.Unchecked: "false",
        }
        self.box.setTristate(False)
        self.callback(
            "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
            value_table[self.box.checkState()],
            None,
            self.show_data_dict["mod_path"],
            self.show_data_dict["module"],
            self.show_data_dict["ecuc_path"],
            self.show_data_dict["tag"],
        )
        self.show_data_dict["cfg_value"] = value_table[self.box.checkState()]

        # 同步修改联动配置项
        self.callback(
            "bsw_editor_update_linked_cfg_item",
            self.show_data_dict["module"],
            self.show_data_dict["mod_path"],
            self.show_data_dict["ecuc_path"],
            value_table[self.box.checkState()],
            getattr(self, "updated_path_dict", {self.show_data_dict["ecuc_path"]: [self.show_data_dict["mod_path"]]}),
            self.basic_ui_handler,
            self.callback,
            self.main_window,
        )
        # 入栈
        self.callback(
            "bsw_editor_input_push_stack",
            self.old_data,
            value_table[self.box.checkState()],
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
        self.old_data = value_table[self.box.checkState()]

    def set_default_value_slot(self):
        if self.default_value:
            if self.default_value.lower() == "false":
                self.box.setCheckState(Qt.Unchecked)
            elif self.default_value.lower() == "true":
                self.box.setCheckState(Qt.Checked)

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
        self.box.setEnabled(True)
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
        self.box.setEnabled(False)
        self.set_default_value_action.setEnabled(False)

    def set_default_value_status(self):
        if self.is_lock is True:
            return False
        if self.default_value:
            return True
        return False
