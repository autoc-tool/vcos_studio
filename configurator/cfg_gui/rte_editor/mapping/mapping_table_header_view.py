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
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from typing import Any
from cfg_gui.rte_editor.mapping.mapping_filter_proxy_model import MappingFilterProxyModel


class MappingTableHeaderView(QtWidgets.QHeaderView):
    page_switch = 0

    def __init__(self, table_proxy_model: MappingFilterProxyModel, parent=None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.table_proxy_model = table_proxy_model
        self.table_proxy_model.modelReset.connect(self.connect_to_source_model_singal)
        self.filter_button_dict: dict[int, TableHeaderToolButton] = {}
        self.setSectionsClickable(True)
        self.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.sectionResized.connect(self.update_filter_buttons_position)
        self.geometriesChanged.connect(self.update_filter_buttons_position)

    def connect_to_source_model_singal(self):
        source_model = self.table_proxy_model.sourceModel()
        if source_model is not None:
            self.create_filter_button()
            source_model.modelReset.connect(self.create_filter_button)

    def clear_all_filter(self):
        for logical_index in range(self.table_proxy_model.columnCount()):
            if logical_index in self.filter_button_dict:
                self.filter_button_dict[logical_index].clear_filter()

    def create_filter_button(self):
        """Create a filter button for each column"""
        for logical_index in range(self.table_proxy_model.columnCount()):
            if logical_index in self.filter_button_dict:
                continue
            self.filter_button_dict[logical_index] = TableHeaderToolButton(self.table_proxy_model, logical_index, self)

    def update_filter_buttons_position(self):
        offset = self.offset()
        rect = self.viewport().rect()
        for index, filter_button in self.filter_button_dict.items():
            right = self.sectionPosition(index) + self.sectionSize(index) - offset
            if right > rect.left() and right < rect.right():
                x = right - filter_button.width()
                y = rect.bottom() - filter_button.height()
                filter_button.move(x, y)
                filter_button.show()
            else:
                filter_button.hide()


class TableHeaderToolButton(QtWidgets.QToolButton):

    def __init__(self, table_proxy_model: MappingFilterProxyModel, logical_index: int, parent=None):
        super().__init__(parent)
        self.table_proxy_model = table_proxy_model
        self.logical_index = logical_index
        self.create_filter_widget()
        self.setFixedSize(12, 12)
        self.setArrowType(QtCore.Qt.ArrowType.DownArrow)
        self.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setAutoRaise(True)
        self.setMenu(self.popup_menu)

    def create_filter_widget(self):
        self.popup_menu = QtWidgets.QMenu(self)
        self.popup_menu_action = QtWidgets.QWidgetAction(self.popup_menu)
        self.popup_menu_action_widget = QtWidgets.QWidget(self)
        self.popup_menu_action.setDefaultWidget(self.popup_menu_action_widget)
        self.popup_menu.addAction(self.popup_menu_action)
        self.popup_menu.aboutToShow.connect(self.init_filter_widget_layout)

    def init_filter_widget_layout(self):
        widget = self.popup_menu_action_widget
        if widget.layout() is not None:
            self.item_list_model.reset_model()
            return
        button_layout = QtWidgets.QVBoxLayout()
        self.select_all_button = QtWidgets.QPushButton(QtGui.QIcon(":/check_all.svg"), "")
        self.select_none_button = QtWidgets.QPushButton(QtGui.QIcon(":/cancel_all.svg"), "")
        self.select_all_button.clicked.connect(self.select_all_clicked_slot)
        self.select_none_button.clicked.connect(self.select_none_clicked_slot)
        button_layout.addWidget(self.select_all_button)
        button_layout.addWidget(self.select_none_button)
        button_layout.addSpacerItem(
            QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Expanding)
        )
        filter_layout = QtWidgets.QHBoxLayout()
        self.item_list_view = QtWidgets.QListView()
        self.item_list_model = ToolButtonListModel(self.table_proxy_model, self.logical_index)
        self.proxy_model = MappingFilterProxyModel()
        self.proxy_model.setSourceModel(self.item_list_model)
        self.item_list_view.setModel(self.proxy_model)
        filter_layout.addLayout(button_layout)
        filter_layout.addWidget(self.item_list_view)

        self.filter_text_editor = QtWidgets.QLineEdit()
        self.filter_text_editor.textChanged.connect(self.filter_text_changed_slot)
        self.filter_text_editor.setPlaceholderText("<Filter>")
        self.filter_text_editor.setClearButtonEnabled(True)
        self.apply_button = QtWidgets.QPushButton("Apply and close")
        self.apply_button.clicked.connect(self.apply_button_clicked_slot)
        general_layout = QtWidgets.QVBoxLayout()
        general_layout.addWidget(self.filter_text_editor)
        general_layout.addLayout(filter_layout)
        general_layout.addWidget(self.apply_button)
        widget.setLayout(general_layout)

    def clear_filter(self):
        if self.popup_menu_action_widget.layout() is not None:
            self.item_list_model.check_state_dict.clear()

    def select_all_clicked_slot(self):
        for row in range(self.proxy_model.rowCount()):
            index = self.proxy_model.index(row, 0)
            self.proxy_model.setData(index, Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
        self.proxy_model.layoutChanged.emit()

    def select_none_clicked_slot(self):
        for row in range(self.proxy_model.rowCount()):
            index = self.proxy_model.index(row, 0)
            self.proxy_model.setData(index, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.proxy_model.layoutChanged.emit()

    def filter_text_changed_slot(self):
        text = self.filter_text_editor.text()
        self.proxy_model.set_filter_pattern(text)

    def apply_button_clicked_slot(self):
        filter_checked_set = set()
        for row in range(self.item_list_model.rowCount()):
            index = self.item_list_model.index(row, 0)
            check_state = index.data(Qt.ItemDataRole.CheckStateRole)
            if check_state == Qt.CheckState.Checked:
                filter_checked_set.add(index.data(Qt.ItemDataRole.DisplayRole))
        self.table_proxy_model.set_filter_column_patterns(self.logical_index, filter_checked_set)
        self.popup_menu.close()


class ToolButtonListModel(QtCore.QAbstractListModel):

    def __init__(self, table_proxy_model: MappingFilterProxyModel, logical_index: int, parent=None) -> None:
        super().__init__(parent)
        self.table_proxy_model = table_proxy_model
        self.logical_index = logical_index
        self.item_list = []
        self.check_state_dict = {}
        self.init()

    def init(self):
        source_model = self.table_proxy_model.sourceModel()
        if not source_model:
            return
        data = source_model.index(0, self.logical_index).data(Qt.ItemDataRole.CheckStateRole)
        if self.logical_index == 0 and data is not None:
            self.item_list = ["True", "False"]
        else:
            self.item_list = sorted(
                {source_model.index(row, self.logical_index).data() for row in range(source_model.rowCount())},
                key=lambda x: (x is not None, x),
            )

    def reset_model(self):
        self.beginResetModel()
        self.init()
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.item_list)

    def columnCount(self, parent=None):
        return 1

    def data(self, index: QtCore.QModelIndex, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.CheckStateRole:
            return self.check_state_dict.get(index.row(), Qt.CheckState.Checked)
        if role == Qt.ItemDataRole.DisplayRole:
            target_item = self.item_list[index.row()]
            return target_item

    def setData(self, index: QtCore.QModelIndex, value: Any, role: int):
        if role == Qt.ItemDataRole.CheckStateRole:
            self.check_state_dict[index.row()] = Qt.CheckState(value)
            return True
        else:
            return super().setData(index, value, role)

    def flags(self, index: QtCore.QModelIndex):
        return super().flags(index) | Qt.ItemFlag.ItemIsUserCheckable
