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
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QLabel, QTableWidgetItem, QTableWidget


class ArgQLabel(QLabel):
    clicked = Signal()

    def __init__(
        self, show_data_dict, textBrowserDescription, table_widget_status, table_widget_definition, callback=None
    ):
        super().__init__()
        self.show_data_dict = show_data_dict
        self.textBrowserDescription = textBrowserDescription
        self.table_widget_status = table_widget_status
        self.table_widget_definition = table_widget_definition
        # 如果存在"unit"，label需要添加单位
        if show_data_dict["unit"] is not None:
            self.short_name = show_data_dict["label_name"] + show_data_dict["unit"]
        else:
            self.short_name = show_data_dict["label_name"]
        self.setText(self.short_name)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.clicked.connect(self.label_clicked_slot)

    def mousePressEvent(self, event):
        self.clicked.emit()  # 发送clicked信号
        super().mousePressEvent(event)

    def label_clicked_slot(self):

        self.show_description_message(self.show_data_dict)
        self.show_definition_message(self.show_data_dict)
        self.show_status_message(self.show_data_dict)

    def show_description_message(self, show_data_dict):
        self.textBrowserDescription.setText(show_data_dict["desc"])

    def show_definition_message(self, show_data_dict):

        show_message = {}
        show_message["Tpye"] = show_data_dict["tag"]
        if show_data_dict["lower_multiplicity"]:
            show_message["Multiplicity"] = (
                str(show_data_dict["lower_multiplicity"]) + ":" + str(show_data_dict["upper_multiplicity"])
            )
        elif show_data_dict["upper_multiplicity_infinite"]:
            show_message["Multiplicity"] = str(show_data_dict["lower_multiplicity"]) + ":" + "n"
        if show_data_dict["mod_path"] is not None:
            show_message["DefinitionRef"] = show_data_dict["mod_path"]
        if show_data_dict["unit"] is not None:
            show_message["Base Unit"] = str(show_data_dict["unit"])
        else:
            show_message["Base Unit"] = "-"
        if show_data_dict["min_value"] is not None and show_data_dict["max_value"] is not None:
            show_message["Range"] = (
                "[" + str(show_data_dict["min_value"]) + ";" + str(show_data_dict["max_value"]) + "]"
            )
        show_message["Origin"] = show_data_dict["origin"]
        self.show_message_handler(show_message, self.table_widget_definition)

    def show_status_message(self, show_data_dict):

        show_message = {}
        if show_data_dict["cfg_value"] is not None:
            show_message["Current Value"] = show_data_dict["cfg_value"]
        else:
            show_message["Current Value"] = "-"
        if show_data_dict["default_value"] is not None:
            show_message["Default Value"] = show_data_dict["default_value"]
        else:
            show_message["Default Value"] = "-"

        self.show_message_handler(show_message, self.table_widget_status)

    def show_message_handler(self, show_message, table_widget):

        table_widget.setColumnCount(2)
        table_widget.setRowCount(len(show_message))
        table_widget.setStyleSheet("QTableView { border: none; }")
        table_widget.verticalHeader().setVisible(False)  # 隐藏垂直表头
        table_widget.horizontalHeader().setVisible(False)  # 隐藏水平表头
        table_widget.setColumnWidth(1, 800)
        table_widget.setEditTriggers(QTableWidget.NoEditTriggers)

        row = 0
        col = 0
        for key, value in show_message.items():
            item_key = QTableWidgetItem(str(key))
            item_value = QTableWidgetItem(str(value))
            table_widget.setItem(row, col, item_key)
            table_widget.setItem(row, col + 1, item_value)
            row += 1
            if row == len(show_message):
                break
        table_widget.show()
