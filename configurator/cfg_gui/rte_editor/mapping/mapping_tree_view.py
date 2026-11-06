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
from typing import Optional
from PySide6 import QtCore, QtGui, QtWidgets
from cfg_gui.rte_editor.mapping.mapping_tree_model import MappingTreeModel
from cfg_gui.rte_editor.mapping.mapping_view_config import MappingViewConfig


class MappingTreeView(QtWidgets.QTreeView):

    def __init__(self, config: MappingViewConfig, parent=None):
        super().__init__(parent)
        self._expanded_status_dict = {}
        self.config = config
        self.setup_ui()
        self.setup_signal_handlers()

    @property
    def expanded_status_dict(self) -> dict:
        return self._expanded_status_dict

    @expanded_status_dict.setter
    def expanded_status_dict(self, value: dict):
        self._expanded_status_dict.clear()
        self._expanded_status_dict.update(value)

    def setup_ui(self):
        """根据配置初始化UI的行为和外观"""
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
        self.setHeaderHidden(True)

    def setup_signal_handlers(self):
        """设置信号处理函数"""
        self.expanded.connect(self.record_tree_expand_status)
        self.expanded.connect(self.resize_tree_column_area)
        self.collapsed.connect(self.resize_tree_column_area)
        self.customContextMenuRequested.connect(self.create_right_click_menu)

    def setModel(self, model: MappingTreeModel):
        """设置TreeView的model"""
        super().setModel(model)
        self._model = model

    def model(self) -> Optional[MappingTreeModel]:
        """获取TreeView的model"""
        return self._model if hasattr(self, "_model") else None

    def update_model(self):
        """更新TreeView的model"""
        model = self.model()
        if model is not None:
            model.reset_model()

    def create_right_click_menu(self, pos: QtCore.QPoint):
        """创建右键菜单"""
        if getattr(self, "tree_menu", None) is None:
            self.tree_menu = QtWidgets.QMenu(self)
        else:
            self.tree_menu.clear()
        for menu_name, menu_cfg in self.config.menu_options.items():
            action = QtGui.QAction(menu_name)
            icon, is_enabled, func = menu_cfg
            if icon:
                action.setIcon(QtGui.QIcon(icon))
            if func:
                action.triggered.connect(func)
            action.setEnabled(is_enabled)
            self.tree_menu.addAction(action)
        self.tree_menu.popup(self.mapToGlobal(pos))

    def record_tree_expand_status(self, index: QtCore.QModelIndex):
        """记录TreeView的展开状态"""
        model = self.model()
        if model is None:
            return
        tree_key = self.get_index_tree_key(index)
        self.expanded_status_dict[tree_key] = self.isExpanded(index)

    def get_index_tree_key(self, index: QtCore.QModelIndex):
        """获取当前索引的树形结构的键值"""
        tree_key_list = []
        while index.parent().isValid():
            text = index.parent().data()
            tree_key_list.append(text)
            index = index.parent()
        tree_key_list.reverse()
        tree_key = ".".join(tree_key_list)
        return tree_key

    def restore_tree_expanded_status(self, expanded_status_dict=None, parent=QtCore.QModelIndex()):
        """
        根据展开的字典恢复树形控件的展开状态
        :param expanded_status_dict: 展开的字典，格式为{tree_key: bool}，
        其中tree_key为节点的路径，bool值为True表示展开，False表示收缩。
        :param parent: 父节点索引，默认值为根节点
        """
        model = self.model()
        if model is None:
            return
        expanded_status_dict = expanded_status_dict or self.expanded_status_dict.copy()
        if not expanded_status_dict:
            self.blockSignals(True)
            self.expandToDepth(0)
            self.resizeColumnToContents(0)
            self.blockSignals(False)
            return
        for row in range(model.rowCount(parent)):
            tree_key = self.get_index_tree_key(parent)
            index = model.index(row, 0, parent)
            if tree_key in expanded_status_dict and expanded_status_dict[tree_key]:
                self.blockSignals(True)
                self.expand(index)
                self.blockSignals(False)
                del expanded_status_dict[tree_key]
            else:
                self.blockSignals(True)
                self.collapse(index)
                self.blockSignals(False)
            if model.hasChildren(index):
                self.restore_tree_expanded_status(expanded_status_dict, index)
        if parent == QtCore.QModelIndex():
            self.expanded_status_dict = {
                key: True for key in self.expanded_status_dict if key not in expanded_status_dict
            }

    def resize_tree_column_area(self, index: QtCore.QModelIndex):
        """调整树形视图的列宽以适应内容"""
        self.resizeColumnToContents(index.column())
