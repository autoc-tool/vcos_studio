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
from PySide6 import QtWidgets, QtCore, QtGui
from cfg_gui.widgets.sec_widgets.sec_bsw_management_dialog import SecBswManagementDialog


class SecModeManagementBswManagementModuleInitializationWidget(QtWidgets.QWidget):
    def __init__(self, main_window, show_data_dict, selected_item_path, callback) -> None:
        super().__init__()
        self.main_window = main_window
        self.show_data_dict = show_data_dict
        self.selected_item_path = selected_item_path
        self.callback = callback
        self.dialog_title = "Configure Module Initialization"
        self.dialog_type = "INIT"
        self.create_sub_container_rules = None

        # 设置垂直布局
        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # 创建字体对象
        normal_font = QtGui.QFont()
        normal_font.setPointSize(10)  # 设置字体大小

        # 创建包含普通文本和多个链接的整体标签
        self.message_label = QtWidgets.QLabel(
            "<a href='INIT' style='color: blue; text-decoration: none;'>Configure Module Initialization</a> "
        )

        self.message_label.setFont(normal_font)  # 设置字体
        self.message_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.message_label.setTextFormat(QtCore.Qt.TextFormat.RichText)  # 开启富文本格式
        self.message_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)  # 可交互文本
        self.message_label.setOpenExternalLinks(False)  # 禁止打开外部链接
        self.message_label.linkActivated.connect(self.link_clicked)  # 连接槽函数

        # 向布局中添加标签
        layout.addWidget(self.message_label)

    def link_clicked(self, link):
        self.callback(
            "get_sec_bsw_management_configuration", link, result_callback=self.update_sec_bsw_management_dialog
        )

    def update_sec_bsw_management_dialog(self, module_list):

        self.sec_bsw_management_dialog = SecBswManagementDialog(
            self.dialog_title,
            self.dialog_type,
            self.create_sub_container_rules,
            self.main_window,
            module_list,
            self.callback,
        )

        self.sec_bsw_management_dialog.show()
