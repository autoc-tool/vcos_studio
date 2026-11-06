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
from PySide6.QtWidgets import QLineEdit, QLabel, QHeaderView
from typing import Any, Optional
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableView, QMenu, QMessageBox
from PySide6.QtCore import QObject, Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtCore import Signal


class WidgetSortFilterProxyModel(QSortFilterProxyModel):
    total_matches_changed = Signal(int)
    progress_changed = Signal(int)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.filter_text = ""
        self.total_matches = 0
        self.max_display_items = 1000  # 设置最大显示项数为1000

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:

        if self.filter_text:
            matched = False
            index0 = self.sourceModel().index(source_row, 0, source_parent)
            # 获取要过滤的数据
            data0 = self.sourceModel().data(index0, Qt.ItemDataRole.DisplayRole)
            # 检查是否与过滤文本匹配
            if self.filter_text.lower() in str(data0).lower():
                matched = True
            if not matched:
                index2 = self.sourceModel().index(source_row, 2, source_parent)
                # 获取要过滤的数据
                data2 = self.sourceModel().data(index2, Qt.ItemDataRole.DisplayRole)
                # 检查是否与过滤文本匹配
                if self.filter_text.lower() in str(data2).lower():
                    matched = True

            if matched:
                self.total_matches += 1
                if self.total_matches > self.max_display_items:
                    self.total_matches_changed.emit(self.total_matches)
                    return False
                self.total_matches_changed.emit(self.total_matches)
                return True
        self.total_matches_changed.emit(self.total_matches)
        return False

    def set_filter_text(self, text):

        self.filter_text = text
        # self.invalidateFilter()


class FindTableViewModel(QAbstractTableModel):

    def __init__(self, find_tab_view, parent=None) -> None:
        super().__init__(parent)
        self.header = ["Element", "Type", "Value"]
        self.table_items = []
        self.find_tab_view = find_tab_view

    def update_model(self, all_element_items):

        self.find_tab_view.update_total_matches_label(len(all_element_items))
        self.beginResetModel()
        self.table_items = all_element_items
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self.table_items)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        column_count = 3
        return column_count

    def data(self, index: QModelIndex, role: int = ...) -> Any:
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignLeft

        item_data = self.table_items[index.row()].get(self.header[index.column()], "")
        if role == Qt.ItemDataRole.DisplayRole:
            if isinstance(item_data, str):
                return item_data
            else:
                return ""
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignLeft

        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.header[section]
            if orientation == Qt.Orientation.Vertical:
                return None

        return super().headerData(section, orientation, role)


class FindTableViewWidget(QWidget):

    def __init__(self, mainwindow) -> None:
        super().__init__()
        self.callback = None
        self.sort_proxy_model = None
        self.basic_ui_handler = mainwindow.basic_ui_handler
        self.global_filter_text: QLineEdit = mainwindow.lineEdit
        mainwindow.tabFind.layout().addWidget(self)

        self.total_matches_label = QLabel()
        self.model = FindTableViewModel(self)
        self.show_element_tableview = QTableView(self)
        self.sort_proxy_model = WidgetSortFilterProxyModel()
        self.sort_proxy_model.setSourceModel(self.model)

        self.init_table()
        self.init_layout()
        self.init_slot()

    def set_callback(self, callback):
        self.callback = callback

    def init_slot(self):
        self.show_element_tableview.doubleClicked.connect(self.show_ref_in_basic_editor_slot)
        self.show_element_tableview.customContextMenuRequested.connect(self.tableview_menu)
        self.global_filter_text.returnPressed.connect(self.handle_global_filter_text_changed_slot)
        self.sort_proxy_model.total_matches_changed.connect(self.update_total_matches_label)

    def init_table(self):
        self.global_filter_text.setPlaceholderText("<Filter>")

        self.sort_proxy_model.setSourceModel(self.model)

        self.show_element_tableview.setModel(self.sort_proxy_model)
        self.show_element_tableview.setSelectionBehavior(QTableView.SelectRows)
        self.show_element_tableview.setSelectionMode(QTableView.SingleSelection)
        self.show_element_tableview.verticalHeader().setVisible(False)
        self.show_element_tableview.setAlternatingRowColors(True)
        self.show_element_tableview.setSortingEnabled(True)
        self.show_element_tableview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        # 自定义右键菜单
        self.show_element_tableview.setContextMenuPolicy(Qt.CustomContextMenu)

    def init_layout(self):
        layout = QVBoxLayout(self)
        layout.addWidget(self.global_filter_text)
        layout.addWidget(self.total_matches_label)
        layout.addWidget(self.show_element_tableview)

    def tableview_menu(self, pos):
        # 获取选中的行索引
        index = self.show_element_tableview.indexAt(pos)
        # 创建右键菜单
        self.menu = QMenu(self.show_element_tableview)
        # 创建选项并连接到槽函数
        open_file_action = QAction("VSCode打开", self)
        open_file_action.triggered.connect(lambda: self.tableview_menu_slot(index, "vscode"))
        self.menu.addAction(open_file_action)
        # 显示右键菜单
        self.menu.popup(self.show_element_tableview.viewport().mapToGlobal(pos))

    def tableview_menu_slot(self, index: QModelIndex, editor_type: str = "vscode"):
        # 获取选中行的Element和Type数据
        source_index = self.sort_proxy_model.mapToSource(index)
        element_string = self.model.data(self.model.index(source_index.row(), 0), role=Qt.ItemDataRole.DisplayRole)
        type_string = self.model.data(self.model.index(source_index.row(), 1), role=Qt.ItemDataRole.DisplayRole)

        res = self.callback("open_arxml_file", element_string, type_string, editor_type)
        self.message_box = None
        if res != 0:
            self.message_box = QMessageBox()
            self.message_box.setWindowTitle("Warning")
            self.message_box.setText(str(res))
            self.message_box.setIcon(QMessageBox.Warning)
            self.message_box.show()

    def handle_global_filter_text_changed_slot(self):
        filter_text_lower = self.global_filter_text.text().lower()
        self.sort_proxy_model.total_matches = 0  # 重置总匹配数
        self.sort_proxy_model.set_filter_text(filter_text_lower)
        self.callback("get_all_element_items", filter_text_lower, result_callback=self.model.update_model)

    def show_ref_in_basic_editor_slot(self, index):
        source_index = self.sort_proxy_model.mapToSource(index)
        row = source_index.row()
        item_data = self.model.table_items[row]
        self.basic_ui_handler.ecuc_path_jumps_to_ui(item_data["Element"])

    def update_total_matches_label(self, total_matches):
        if total_matches <= 1000:
            self.total_matches_label.setText(f"{total_matches} items found")
        else:
            self.total_matches_label.setText(f"{total_matches} items found, 1000 displayed")
