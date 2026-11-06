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
from PySide6.QtWidgets import (
    QTableWidget,
    QDialog,
    QAbstractItemView,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QTableWidgetItem,
)
from PySide6.QtCore import Qt


class ArgTableWidget(QTableWidget):

    def __init__(self, basic_ui_handler):
        super().__init__()
        # self.ecuc_config = ecuc_config
        # self.reference_param_list = reference_param_list
        # self.definition_ref_name = definition_ref_name
        self.basic_ui_handler = basic_ui_handler
        self.select_reference_target_dialog = None
        self.select_reference_target_tablewidget = None
        self.all_ref_configuration_items_by_ref_target_dict = None
        self.init_select_reference_target_dialog()

    def init_select_reference_target_dialog(self):
        """
        init select reference target dialog
        """

        self.select_reference_target_dialog = QDialog()
        self.select_reference_target_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.select_reference_target_dialog.setWindowTitle("All Reference Configuration Items")
        self.select_reference_target_dialog.setMinimumSize(1150, 472)
        self.select_reference_target_dialog.setMaximumSize(1150, 472)
        self.select_reference_target_dialog.setWindowFlags(Qt.WindowType.WindowCloseButtonHint)

        self.select_reference_target_tablewidget = QTableWidget(self.select_reference_target_dialog)
        # 设置列数
        self.select_reference_target_tablewidget.setColumnCount(2)
        # 设置表格头
        # self.select_reference_target_tablewidget.setHorizontalHeaderLabels(["Element", "Type", "Value"])
        self.select_reference_target_tablewidget.setHorizontalHeaderLabels(
            ["Reference Configuration Item", "Ref Target"]
        )
        # 将表格变为禁止编辑
        self.select_reference_target_tablewidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # 设置表格整行选中
        self.select_reference_target_tablewidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        # 将行与列的高度设置为所显示的内容的宽度高度匹配
        # QTableWidget.resizeColumnsToContents(self.mapping_tablewidget)
        # QTableWidget.resizeRowsToContents(self.mapping_tablewidget)
        self.select_reference_target_tablewidget.setAlternatingRowColors(True)
        self.select_reference_target_tablewidget.horizontalHeader().setStyleSheet(
            'QHeaderView::section{font-family:"Microsoft YaHei";'
            "font-size:9pt;color:black;background-color:rgb(230, 230, 230);font-weight:400}"
        )
        self.select_reference_target_tablewidget.verticalHeader().setStyleSheet(
            'QHeaderView::section{font-family:"Microsoft YaHei";'
            "font-size:9pt;color:black;background-color:rgb(230, 230, 230);font-weight:400}"
        )
        self.select_reference_target_tablewidget.setShowGrid(True)
        self.select_reference_target_tablewidget.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.select_reference_target_tablewidget.horizontalHeader().font().setBold(True)
        self.select_reference_target_tablewidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.select_reference_target_tablewidget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.select_reference_target_tablewidget.verticalHeader().setSectionsClickable(False)
        self.select_reference_target_tablewidget.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.select_reference_target_tablewidget.horizontalHeader().setSectionsClickable(False)
        self.select_reference_target_tablewidget.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.select_reference_target_tablewidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.filter_text = QLineEdit()
        self.filter_text.setPlaceholderText("<Filter>")

        self.select_reference_target_pushbutton = QPushButton("Ok")
        qvboxlayout = QVBoxLayout(self.select_reference_target_dialog)
        qvboxlayout.addWidget(self.filter_text)
        qvboxlayout.addWidget(self.select_reference_target_tablewidget)
        qvboxlayout.addWidget(self.select_reference_target_pushbutton)
        self.select_reference_target_tablewidget.itemDoubleClicked.connect(self.show_ref_in_basic_editor_slot)
        # self.select_reference_target_pushbutton.clicked.connect(self.fill_selected_reference_target_line_edit)
        self.filter_text.textChanged.connect(self.handle_filter_text_changed_solt)

    def fill_reference_target_table_widget(self, filter_text, all_ref_configuration_items_by_ref_target_dict):
        """
        Populates the obtained reference target
        """
        self.all_ref_configuration_items_by_ref_target_dict = all_ref_configuration_items_by_ref_target_dict
        row_count = 0
        for package_path, short_name in all_ref_configuration_items_by_ref_target_dict.items():
            matched = False
            if filter_text in package_path.lower() or filter_text in short_name.lower():
                matched = True
            if matched:
                row_count = row_count + 1
        # 设置行数
        self.select_reference_target_tablewidget.setRowCount(row_count)
        i = 0
        for package_path, short_name in all_ref_configuration_items_by_ref_target_dict.items():
            matched = False
            if filter_text in package_path.lower() or filter_text in short_name.lower():
                matched = True
            if matched:
                new_item_short_name = QTableWidgetItem(short_name)
                self.select_reference_target_tablewidget.setItem(i, 1, new_item_short_name)
                new_item_package_path = QTableWidgetItem(package_path)
                self.select_reference_target_tablewidget.setItem(i, 0, new_item_package_path)
                i = i + 1

    def handle_filter_text_changed_solt(self, text):
        """
        不区分大小写
        """

        filter_text = text.lower()
        self.fill_reference_target_table_widget(filter_text, self.all_ref_configuration_items_by_ref_target_dict)

    def show_ref_in_basic_editor_slot(self):

        table_widget: QTableWidget = self.select_reference_target_tablewidget

        for list_item in table_widget.findItems("/", Qt.MatchContains):
            reference_target = list_item.text()
            selected = list_item.isSelected()
            if selected:
                self.basic_ui_handler.ecuc_path_jumps_to_ui(reference_target)
                break
        self.select_reference_target_dialog.close()
