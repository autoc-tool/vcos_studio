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
from typing import Union
from cfg_gui.rte_editor.mapping.mapping_table_model import MappingTableModel
from cfg_gui.rte_editor.mapping.mapping_view_config import MappingViewConfig
from cfg_gui.rte_editor.mapping.mapping_filter_proxy_model import MappingFilterProxyModel
from cfg_gui.rte_editor.mapping.mapping_table_header_view import MappingTableHeaderView


class MappingTableView(QtWidgets.QTableView):

    def __init__(self, config: MappingViewConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_ui()

    def setup_ui(self):
        self.setAlternatingRowColors(self.config.alternating_row_colors)
        self.setSortingEnabled(self.config.sorting_enabled)
        self.setSelectionMode(self.config.selection_mode)
        self.setSelectionBehavior(self.config.selection_behavior)
        self.setSizeAdjustPolicy(self.config.size_adjust_policy)
        self.setContextMenuPolicy(self.config.context_menu_policy)
        self.setDragEnabled(self.config.drag_enabled)
        self.setDragDropMode(self.config.drag_drop_mode)
        self.setDragDropOverwriteMode(self.config.drag_drop_overwrite_mode)
        self.setDefaultDropAction(self.config.drop_action)
        self.setCornerButtonEnabled(False)
        self.setAlternatingRowColors(True)
        if self.config.context_menu_policy == QtCore.Qt.ContextMenuPolicy.CustomContextMenu:
            self.customContextMenuRequested.connect(self.create_right_click_menu)

    def setHorizontalHeader(self, header: MappingTableHeaderView):
        scroll_bar = self.horizontalScrollBar()
        if scroll_bar:
            scroll_bar.valueChanged.connect(header.update_filter_buttons_position)
        return super().setHorizontalHeader(header)

    def setModel(self, model: Union[MappingTableModel, MappingFilterProxyModel, None]):
        """设置TableView的model"""
        super().setModel(model)
        if model is not None:
            model.dataChanged.connect(self.resize_table_column_area)
        self._model = model

    def model(self) -> Union[MappingTableModel, MappingFilterProxyModel, None]:
        """获取TableView的model"""
        return self._model if hasattr(self, "_model") else None

    def update_model(self):
        """更新TableView的model"""
        model = self.model()
        if isinstance(model, MappingFilterProxyModel):
            model = model.sourceModel()
        if isinstance(model, MappingTableModel):
            model.reset_model()

    def create_right_click_menu(self, pos: QtCore.QPoint):
        """创建右键菜单"""
        if getattr(self, "table_menu", None) is None:
            self.table_menu = QtWidgets.QMenu(self)
        else:
            self.table_menu.clear()
        for menu_name, menu_cfg in self.config.menu_options.items():
            action = QtGui.QAction(menu_name, self.table_menu)
            icon, func = menu_cfg
            if icon:
                action.setIcon(QtGui.QIcon(icon))
            if func:
                action.triggered.connect(func)
            self.table_menu.addAction(action)
        self.table_menu.popup(self.mapToGlobal(pos))

    def resize_table_column_area(self, index: QtCore.QModelIndex):
        """调整表格视图的列宽以适应内容"""
        self.resizeColumnToContents(index.column())
