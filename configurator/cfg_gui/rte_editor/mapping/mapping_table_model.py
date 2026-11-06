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
import ctypes
import pickle
from PySide6 import QtCore, QtGui
from PySide6.QtCore import Qt
from typing import Any, Iterable, Callable
from cfg_gui.rte_editor.mapping.mapping_model_config import MappingModelConfig


class MappingTableItem:

    def __init__(self, data, data_handler: Callable):
        self.data_handler = data_handler
        self.data = data
        self.mime_type = "default"

    @property
    def text(self) -> str:
        if self.data_handler is None or not callable(self.data_handler):
            return ""
        else:
            return self.data_handler("get_table_item_text", data=self.data)

    @property
    def icon(self) -> QtGui.QIcon:
        if self.data_handler is None or not callable(self.data_handler):
            return QtGui.QIcon()
        else:
            return self.data_handler("get_table_item_icon", data=self.data)

    @property
    def tooltip(self) -> str:
        if self.data_handler is None or not callable(self.data_handler):
            return ""
        else:
            return self.data_handler("get_table_item_tooltip", data=self.data)

    @property
    def flags(self) -> Qt.ItemFlags:
        if self.data_handler is None or not callable(self.data_handler):
            return Qt.ItemFlags(Qt.ItemFlag.NoItemFlags)
        else:
            return Qt.ItemFlags(self.data_handler("get_table_item_flags", data=self.data) or Qt.ItemFlag.NoItemFlags)


class MappingTableModel(QtCore.QAbstractItemModel):

    def __init__(self, config: MappingModelConfig):
        # 初始化TableModel
        super().__init__()
        self.config = config
        self.init()

    def init(self):
        # 初始化TableModel的item数据
        self.check_state_dict = {}
        self.item_list = self.config.callback_handler("get_table_item_list") or [[]]
        if self.item_list != [[]]:
            self.table_header_list = self.config.callback_handler("get_table_header_list") or []
        else:
            self.table_header_list = []
        self.column_count = len(self.table_header_list)

    def reset_model(self):
        """重置TableModel"""
        self.beginResetModel()
        self.init()
        self.endResetModel()

    def data(self, index: QtCore.QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        """返回TableModel中数据的显示内容"""
        if not index.isValid():
            return None
        item = index.internalPointer()
        if item is None:
            return None
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return self.config.alignment_flag
        elif role == Qt.ItemDataRole.DisplayRole:
            return item.text
        elif role == Qt.ItemDataRole.ToolTipRole:
            return item.tooltip
        elif role == Qt.ItemDataRole.CheckStateRole:
            if self.config.supported_check_state and index.column() == 0:
                return self.check_state_dict.get(index.row(), Qt.CheckState.Unchecked)
        # elif role == Qt.ItemDataRole.EditRole:
        #     if index.column() in self.config.check_state_column:
        #         return VcosCustom.EditorWidget.CheckBoxEditor
        return None

    def setData(self, index: QtCore.QModelIndex, value: Any, role: int):
        if role == Qt.ItemDataRole.CheckStateRole:
            if value == Qt.CheckState.Checked.value and not self.config.supported_multiple_selection:
                for row, check_state in self.check_state_dict.items():
                    if check_state != Qt.CheckState.Checked:
                        continue
                    self.check_state_dict[row] = Qt.CheckState.Unchecked
                    other_index = self.index(row, 0)
                    self.dataChanged.emit(other_index, other_index, [Qt.ItemDataRole.CheckStateRole])
            self.check_state_dict[index.row()] = Qt.CheckState(value)
            return True
        else:
            return super().setData(index, value, role)

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

    def dropMimeData(
        self, mimedata: QtCore.QMimeData, action: Qt.DropAction, row: int, column: int, parent: QtCore.QModelIndex
    ):
        # 接受打包拖放的数据
        if not parent.isValid():
            return False
        if action != Qt.DropAction.MoveAction:
            return False
        target_row = parent.row()
        target_col = parent.column()
        # 用于反序列化出所需的python对象
        if not mimedata.hasText():
            return False
        obj_ids = pickle.loads(mimedata.data(mimedata.text()).data())
        # 需要用list, 这样才能保证有序
        item_data_list = []
        for obj_id in obj_ids:
            item_data = ctypes.cast(obj_id, ctypes.py_object).value
            item_data_list.append(item_data)
        self.config.callback_handler("drop_mime_data", item_data_list, target_row, target_col)
        return True

    def headerData(self, section: int, orientation=Qt.Orientation.Horizontal, role=Qt.ItemDataRole.DisplayRole):
        # 返回TableModel的header数据
        if section < 0:
            return None
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if section >= len(self.table_header_list):
                return None
            return str(self.table_header_list[section])
        if orientation == Qt.Orientation.Vertical:
            return str(section)

    def flags(self, index: QtCore.QModelIndex):
        # 返回TableModel中数据对应属性，是否可被选中、是否可启用、是否支持拖拽
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        item = index.internalPointer()
        if item is None:
            return Qt.ItemFlag.NoItemFlags
        return item.flags

    def index(self, row: int, column: int, parent=QtCore.QModelIndex()):
        # 创建TableModel中item的index
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        if parent.isValid():
            return QtCore.QModelIndex()
        if row >= len(self.item_list):
            return QtCore.QModelIndex()
        if column >= len(self.item_list[row]):
            return QtCore.QModelIndex()
        try:
            item = self.item_list[row][column]
        except BaseException:
            return QtCore.QModelIndex()
        if item:
            return self.createIndex(row, column, item)
        else:
            return QtCore.QModelIndex()

    def parent(self, index: QtCore.QModelIndex):
        """重写parent方法, 返回表格模型的父索引, 因为所有单元格都是顶级节点, 所以使用无效节点作为父节点"""
        return QtCore.QModelIndex()

    def rowCount(self, parent=QtCore.QModelIndex()):
        """重写rowCount函数, 返回表格模型的行数"""
        if self.column_count == 0:
            return 0
        row = len(self.item_list)
        return row

    def columnCount(self, parent=QtCore.QModelIndex()):
        """重写columnCount函数, 返回表格模型的列数"""
        return self.column_count

    def supportedDragActions(self):
        # 返回TableModel是否支持Drag
        return self.config.supported_drag_actions

    def supportedDropActions(self):
        # 返回TableModel是否支持Drop
        return self.config.supported_drop_actions
