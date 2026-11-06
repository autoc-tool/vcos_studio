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
import pickle
from PySide6 import QtCore, QtGui
from PySide6.QtCore import Qt
from typing import List, Iterable, Optional, Callable
from cfg_gui.rte_editor.mapping.mapping_model_config import MappingModelConfig


class MappingTreeItem:
    data_handler: Callable

    def __init__(self, data, parent=None):
        self.data = data
        self.parent: Optional["MappingTreeItem"] = parent
        self.children: List["MappingTreeItem"] = []
        self.child_map: dict[str, "MappingTreeItem"] = {}
        self.mime_type = "default"
        if parent:
            parent.append_child(self)

    def append_child(self, child: "MappingTreeItem"):
        child.parent = self
        self.children.append(child)
        self.child_map[child.text] = child

    def child(self, row: int):
        if row < len(self.children):
            return self.children[row]
        else:
            return None

    def child_text(self, text: str):
        return self.child_map.get(text, None)

    def insert_child(self, position: int, child: "MappingTreeItem"):
        self.children.insert(position, child)
        self.child_map[child.text] = child

    def row(self) -> int:
        if self.parent is not None:
            return self.parent.children.index(self)
        return 0

    def row_count(self) -> int:
        return len(self.children)

    def column_count(self) -> int:
        return 1

    def is_leaf(self) -> bool:
        return len(self.children) == 0

    @property
    def text(self) -> str:
        if self.data_handler is None or not callable(self.data_handler):
            return ""
        else:
            return self.data_handler("get_tree_item_text", data=self.data) or ""

    @property
    def icon(self) -> QtGui.QIcon:
        if self.data_handler is None or not callable(self.data_handler):
            return QtGui.QIcon()
        else:
            return self.data_handler("get_tree_item_icon", data=self.data) or QtGui.QIcon()

    @property
    def tooltip(self) -> str:
        if self.data_handler is None or not callable(self.data_handler):
            return ""
        else:
            return self.data_handler("get_tree_item_tooltip", data=self.data) or ""

    @property
    def flags(self) -> Qt.ItemFlags:
        if self.data_handler is None or not callable(self.data_handler):
            return Qt.ItemFlags(Qt.ItemFlag.NoItemFlags)
        else:
            return Qt.ItemFlags(self.data_handler("get_tree_item_flags", data=self.data) or Qt.ItemFlag.NoItemFlags)


class MappingTreeModel(QtCore.QAbstractItemModel):

    def __init__(self, config: MappingModelConfig, parent=None):
        # 初始化TreeModel
        super().__init__(parent)
        self.config = config
        self.init()

    def init(self):
        # 初始化TreeItem数据
        MappingTreeItem.data_handler = self.config.callback_handler
        self.root_item = self.config.callback_handler("get_tree_root_item")

    def reset_model(self):
        # 重置TreeModel
        self.beginResetModel()
        self.init()
        self.endResetModel()

    def is_changed(self):
        # 检查Tree item数据是否变化
        cur_root_item = self.config.callback_handler("get_tree_root_item")
        return id(cur_root_item) != id(self.root_item)

    def data(self, index: QtCore.QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        # 返回TreeModel中数据，是显示图标、数据、还是提示
        if not index.isValid():
            return None
        item = index.internalPointer()
        if item is None:
            return None
        # 显示节点图标
        if role == Qt.ItemDataRole.DecorationRole:
            return item.icon
        # 显示节点数据
        if role == Qt.ItemDataRole.DisplayRole:
            return str(item.text)
        # 显示节点提示
        elif role == Qt.ItemDataRole.ToolTipRole:
            return str(item.tooltip)
        else:
            return None

    def mimeData(self, indexes: Iterable[QtCore.QModelIndex]):
        # 返回打包拖放的数据
        mimedata = QtCore.QMimeData()
        item_id_list = []
        for index in indexes:
            if not index.isValid():
                continue
            item = index.internalPointer()
            if item is None:
                continue
            item_id_list.append(id(item))
        mimedata.setData(self.config.mime_types[item.mime_type], pickle.dumps((item_id_list)))
        mimedata.setText(self.config.mime_types[item.mime_type])
        return mimedata

    def mimeTypes(self):
        # 定义拖放数据类型
        return list(self.config.mime_types.values())

    def flags(self, index: QtCore.QModelIndex):
        # 返回TreeModel中数据对应属性，是否可被选中、是否可启用、是否支持拖拽
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        item = index.internalPointer()
        if item is None:
            return Qt.ItemFlag.NoItemFlags
        return item.flags

    def index(self, row: int, column=0, parent=QtCore.QModelIndex()):
        # 创建TreeModel中item的index
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()
        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        else:
            return QtCore.QModelIndex()

    def parent(self, index: QtCore.QModelIndex):
        # 创建TreeModel中item的parent index
        if not index.isValid():
            return QtCore.QModelIndex()
        child_item = index.internalPointer()
        parent_item = child_item.parent
        # 顶层节点, 直接返回空索引
        if parent_item == self.root_item:
            return QtCore.QModelIndex()
        # 为父节点建立索引
        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent=QtCore.QModelIndex()):
        # 返回parent index下有多少行
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()
        if parent_item:
            return parent_item.row_count()
        else:
            return 0

    def columnCount(self, parent=QtCore.QModelIndex()):
        # 返回parent index下有多少列
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()
        if parent_item:
            return parent_item.column_count()
        else:
            return 0

    def supportedDragActions(self):
        # 返回TreeModel是否支持Drag
        return self.config.supported_drag_actions

    def supportedDropActions(self):
        # 返回TreeModel是否支持Drop
        return self.config.supported_drop_actions
