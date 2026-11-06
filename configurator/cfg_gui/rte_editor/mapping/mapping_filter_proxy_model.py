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
from PySide6 import QtCore
from PySide6.QtCore import Qt
from typing import Set


class MappingFilterProxyModel(QtCore.QSortFilterProxyModel):

    def __init__(self):
        """初始化model"""
        super().__init__()
        self.filter_pattern = ""
        self.filter_column_patterns = {}

    def filterAcceptsRow(self, source_row: int, source_parent=QtCore.QModelIndex()):
        """筛选将呈现的行数据"""
        source_model = self.sourceModel()
        if source_model is None:
            return True
        filter_res = False
        if self.filter_pattern != "":
            for column in range(source_model.columnCount()):
                value = source_model.index(source_row, column, source_parent).data()
                if value and self.filter_pattern in value.lower():
                    filter_res = True
                    break
        else:
            filter_res = True
        filter_column_res = True
        for column, patterns in self.filter_column_patterns.items():
            value = source_model.index(source_row, column, source_parent).data(Qt.ItemDataRole.CheckStateRole)
            if column == 0 and value is not None:
                if value == Qt.CheckState.Checked:
                    value = "True"
                else:
                    value = "False"
            else:
                value = source_model.index(source_row, column, source_parent).data()
            filter_column_res &= value in patterns
        return filter_res and filter_column_res

    def invalidateFilter(self):
        super().invalidateFilter()
        self.layoutChanged.emit()

    def set_filter_pattern(self, text: str):
        """设置表格或列表的过滤模式"""
        self.filter_pattern = text.lower()
        self.invalidateFilter()

    def set_filter_column_patterns(self, column: int, patterns: Set[str]):
        """设置表格模型的过滤列模式"""
        self.filter_column_patterns[column] = patterns
        self.invalidateFilter()

    def clear_filter_column_patterns(self, column: int):
        """清除表格模型的过滤模式"""
        if column in self.filter_column_patterns:
            del self.filter_column_patterns[column]
        self.invalidateFilter()

    def clear_all_filter_patterns(self):
        """清除所有过滤模式"""
        self.filter_pattern = ""
        self.filter_column_patterns = {}
        self.invalidateFilter()
