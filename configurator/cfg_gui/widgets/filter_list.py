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
from typing import Optional, Any
from PySide6.QtCore import Qt, QObject, QModelIndex, QAbstractListModel, QSortFilterProxyModel, QAbstractItemModel


class UniqueRowProxyModel(QSortFilterProxyModel):

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.unique_data = set()
        self.filter_text = ""

    def set_filter_text(self, text):
        # Update filter text and rerender filter list
        self.filter_text = text
        self.unique_data.clear()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """
        Filter row data who will be rendered

        1. Item data only occurs once
        2. Only item data containing filter text should be shown
        """
        source_model: QAbstractItemModel = self.sourceModel()
        index = source_model.index(source_row, self.filterKeyColumn(), source_parent)
        data = source_model.data(index, role=Qt.ItemDataRole.DisplayRole)

        if data in self.unique_data:
            return False
        elif self.filter_text.lower() in data.lower():
            self.unique_data.add(data)
            return True
        else:
            return False

    def setData(self, index: QModelIndex, value: Any, role: int = ...) -> bool:
        res = super().setData(index, value, role)
        # Notify view data has been changed
        self.dataChanged.emit(index, index)
        return res

    def check_all(self):
        """
        Check all items
        """
        for i in range(self.rowCount()):
            index = self.index(i, self.filterKeyColumn())
            self.setData(index, Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)

    def uncheck_all(self):
        """
        Uncheck all items
        """
        for i in range(self.sourceModel().rowCount()):
            index = self.index(i, self.filterKeyColumn())
            self.setData(index, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)


class FilterListModel(QAbstractListModel):

    def __init__(self, item_list, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.item_list = item_list
        self.check_state_list = [Qt.CheckState.Checked] * len(self.item_list)

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self.item_list)

    def data(self, index: QModelIndex, role: int = ...) -> Any:
        target_item = self.item_list[index.row()]

        if role == Qt.ItemDataRole.CheckStateRole:
            return self.check_state_list[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            display_text = target_item.display_text()
            if display_text in (None, ""):
                display_text = "empty"
            return display_text

    def setData(self, index: QModelIndex, value: Any, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.CheckStateRole:
            self.check_state_list[index.row()] = value
            return True
        else:
            super().setData(index, value, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        flags = super().flags(index)
        flags = flags | Qt.ItemFlag.ItemIsUserCheckable
        return flags

    def set_item_checked(self, item_value, checked):
        # 遍历所有数据项查找匹配的值
        for row in range(self.rowCount()):
            # 如果项的值匹配 item_value，则更新勾选状态
            if self.data(self.index(row, 0), Qt.DisplayRole) == item_value:
                # 更新内部勾选状态存储
                self.check_state_list[row] = Qt.Checked if checked else Qt.Unchecked
                # 发出数据改变信号。实参决定了哪些视图部分需要更新。
                self.dataChanged.emit(self.index(row, 0), self.index(row, 0), [Qt.CheckStateRole])

                # 只更新第一个匹配的项, 如果你想匹配所有项，请注释掉下面这行
                break

    def set_all_checked(self, checked):
        # 更新所有行的勾选状态
        for row in range(self.rowCount()):
            self.check_state_list[row] = Qt.Checked if checked else Qt.Unchecked
        # 发出数据改变信号，通知视图更新所有行
        top_left_index = self.index(0, 0)
        bottom_right_index = self.index(self.rowCount() - 1, 0)
        self.dataChanged.emit(top_left_index, bottom_right_index, [Qt.CheckStateRole])
