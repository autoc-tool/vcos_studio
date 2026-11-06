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
import os
from typing import Callable
from PySide6.QtWidgets import (
    QDialog,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QLabel,
    QFrame,
    QAbstractItemView,
)
from PySide6.QtGui import QIcon, QFont
from PySide6.QtCore import Qt, QSize
from cfg_gui.import_file.import_arxml_ui import button_set_attr


class ExportEcucArxmlUi(QDialog):
    TABLE_WIDGET_COLUMN = 4

    def __init__(self, all_module_list: list, call_back_dict, parent=None):
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)
        self.call_back: Callable = call_back_dict
        self.all_module_list = sorted(all_module_list)
        self.selected_module_num = 0
        self.init_ui_layout()
        self.init_widget_check_widgets()
        self.init_signal_connect_slot()

    def init_ui_layout(self):
        # 顶端标题与提示信息区域
        title_label = QLabel("Export Module Configuration")
        title_label.setFont(QFont("Microsoft YaHei", 15))
        self.hint_message_label = QLabel()
        self.hint_message_label.setFont(QFont("Microsoft YaHei", 10))
        top_layout = QVBoxLayout()
        top_layout.addWidget(title_label)
        top_layout.addWidget(self.hint_message_label)
        top_layout.setSpacing(5)
        top_layout.setContentsMargins(7, 0, 0, 0)

        # 中间左侧按钮布局
        self.select_all_button = QPushButton(QIcon(":/check_all.svg"), "", self)
        self.cancel_all_button = QPushButton(QIcon(":cancel_all.svg"), "", self)
        button_set_attr(self.select_all_button)
        button_set_attr(self.cancel_all_button)
        select_button_layout = QVBoxLayout()
        select_button_layout.addWidget(self.select_all_button)
        select_button_layout.addWidget(self.cancel_all_button)
        select_button_layout.addStretch(1)
        select_button_layout.setSpacing(10)
        # 中间控件区域布局
        self.all_module_table_widget = QTableWidget(self)
        center_layout = QHBoxLayout()
        center_layout.addLayout(select_button_layout)
        center_layout.addWidget(self.all_module_table_widget)
        center_layout.setContentsMargins(2, 0, 5, 2)
        center_layout.setSpacing(2)

        # 底部按钮布局
        self.next_button = QPushButton("next")
        self.cancel_button = QPushButton("cancel")
        self.selected_num_label = QLabel()
        self.selected_num_label.setFont(QFont("Microsoft YaHei", 9))
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.selected_num_label)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.next_button)
        bottom_layout.addWidget(self.cancel_button)
        bottom_layout.setContentsMargins(10, 0, 10, 0)

        # 窗口整体布局
        widget_layout = QVBoxLayout(self)
        widget_layout.addLayout(top_layout)
        widget_layout.addWidget(self.get_ui_seperate_line())
        widget_layout.addLayout(center_layout)
        widget_layout.addWidget(self.get_ui_seperate_line())
        widget_layout.addLayout(bottom_layout)
        widget_layout.setContentsMargins(0, 0, 0, 10)

        self.setWindowIcon(QIcon(":/Home.svg"))
        self.setFixedSize(QSize(600, 420))
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle("Export Module Ecuc Arxml")

    def get_ui_seperate_line(self, direction=QFrame.HLine) -> QFrame:
        horizon_line = QFrame(self)
        horizon_line.setFrameShape(direction)
        horizon_line.setFrameShadow(QFrame.Sunken)
        return horizon_line

    def init_signal_connect_slot(self):
        self.cancel_button.clicked.connect(self.close)
        self.next_button.clicked.connect(self.apply_button_clicked_slot)
        self.cancel_all_button.clicked.connect(lambda: self.change_all_selected_state(Qt.CheckState.Unchecked))
        self.select_all_button.clicked.connect(lambda: self.change_all_selected_state(Qt.CheckState.Checked))
        self.all_module_table_widget.cellChanged.connect(self.table_cell_state_changed)

    def init_widget_check_widgets(self):
        # 默认设置为 3 列
        self.all_module_table_widget.setColumnCount(self.TABLE_WIDGET_COLUMN)
        if len(self.all_module_list) % self.TABLE_WIDGET_COLUMN == 0:
            row_count = len(self.all_module_list) // self.TABLE_WIDGET_COLUMN
        else:
            row_count = len(self.all_module_list) // self.TABLE_WIDGET_COLUMN + 1
        self.all_module_table_widget.setRowCount(row_count)
        self.all_module_table_widget.verticalHeader().setHidden(True)
        self.all_module_table_widget.horizontalHeader().setHidden(True)
        self.all_module_table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.all_module_table_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.all_module_table_widget.setFocusPolicy(Qt.NoFocus)

        for i in range(self.all_module_table_widget.columnCount()):
            # TODO: 获取准确的宽度
            column_width = self.width() // self.all_module_table_widget.columnCount() - 4 * self.TABLE_WIDGET_COLUMN
            self.all_module_table_widget.setColumnWidth(i, column_width)
        self.all_module_table_widget.setShowGrid(False)

        for i in range(len(self.all_module_list)):
            table_widget_item = QTableWidgetItem(self.all_module_list[i])
            table_widget_item.setCheckState(Qt.CheckState.Unchecked)
            self.all_module_table_widget.setItem(
                i // self.TABLE_WIDGET_COLUMN, i % self.TABLE_WIDGET_COLUMN, table_widget_item
            )
        self.update_hint_message_and_button_state()

    def get_cell_pos(self, index) -> tuple:
        return (index // self.TABLE_WIDGET_COLUMN, index % self.TABLE_WIDGET_COLUMN)

    def get_selected_module_list(self) -> list:
        selected_module = []
        for i in range(len(self.all_module_list)):
            item = self.all_module_table_widget.item(*self.get_cell_pos(i))
            if item.checkState() == Qt.CheckState.Checked:
                selected_module.append(item.text())
        return selected_module

    def change_all_selected_state(self, state: Qt.CheckState):
        for i in range(len(self.all_module_list)):
            self.all_module_table_widget.item(*self.get_cell_pos(i)).setCheckState(state)

    def update_hint_message_and_button_state(self):
        if self.selected_module_num == 0:
            self.hint_message_label.setText("Please select at least one module to export.")
            self.next_button.setDisabled(True)
        else:
            self.hint_message_label.setText("After clicking the next button, select a path to store in the arxml file.")
            self.next_button.setEnabled(True)
        self.selected_num_label.setText(
            f"selected {self.selected_module_num}/" f"{len(self.all_module_list)} module configuration."
        )

    def table_cell_state_changed(self, row_index, col_index):
        if self.all_module_table_widget.item(row_index, col_index).checkState() == Qt.CheckState.Unchecked:
            self.selected_module_num -= 1
        else:
            self.selected_module_num += 1
        self.update_hint_message_and_button_state()

    def apply_button_clicked_slot(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Saving Selected Ecuc module arxml", filter="Ecuc arxml (*.arxml)"
        )
        if len(file_path) == 0:
            return
        file_name = os.path.basename(file_path)
        if not file_path.endswith(".arxml"):
            file_path = f"{os.path.dirname(file_path)}/{file_name}.arxml"
        # 保存所选模块的 arxml 数据到文件中
        self.call_back("export_action", self.get_selected_module_list(), file_path)
        self.close()
