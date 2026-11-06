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
from collections import defaultdict
from typing import List
from PySide6 import QtGui
from PySide6.QtCore import Qt, QModelIndex, QAbstractItemModel
from PySide6.QtWidgets import (
    QTreeView,
    QHeaderView,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
)


class ArgQTreeItem:

    def __init__(self, item_name, item_value, path="", alias=None):
        self._data = item_value  # 节点对应数据
        self._parent = None  # 父节点
        self._children = []  # 子节点集合
        self._row = -1  # 此item位于父节点第几个
        self._path = path  # 节点对应路径
        self._item_name = item_name
        self._alias = alias  # 节点别名

    def append_child(self, child, index=None):
        child._parent = self
        child._row = len(self._children)
        if index is not None:
            self._children.insert(index, child)
        else:
            self._children.append(child)

    def get_data(self):
        return self._data

    def get_children(self) -> List["ArgQTreeItem"]:
        return self._children

    def get_child(self, row) -> "ArgQTreeItem":
        if row >= 0 and row < len(self._children):
            return self._children[row]
        else:
            return None

    def get_path(self):
        return self._path

    def get_parent(self) -> "ArgQTreeItem":
        return self._parent

    def get_row(self):
        return self._row

    def set_row(self, row):
        self._row = row

    def child_count(self):
        return len(self._children)

    def column_count(self):
        return 1

    def get_alias(self):
        return self._alias

    def get_item_name(self):
        return self._item_name


class ArgQTreeModel(QAbstractItemModel):

    def __init__(self, support_cfg_module_init_list: dict, call_back):
        super().__init__()
        self.support_cfg_module_init_list = support_cfg_module_init_list
        self.callback = call_back
        self.parent_item_dict = defaultdict(dict)
        self.child_item_dict = {}
        self.defs_dict = {}
        self.defs_set = {}
        self.root_item = ArgQTreeItem("root", "", path="/")  # 最顶层根节点
        self.item_state_cache = {}
        self.init_model_data()

    def set_callback(self, callback):
        self.callback = callback

    # 显示index的节点数据
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        item: ArgQTreeItem = index.internalPointer()
        short_name = item.get_alias()
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:  # 复选框在第一列
            # 根据VCOS2:Value的值设置复选框状态
            if short_name is None:
                return (
                    Qt.CheckState.Checked
                    if item.get_data().get("VCOS2:Value", "FALSE").upper() == "TRUE"
                    else Qt.CheckState.Unchecked
                )
            else:
                return Qt.CheckState.PartiallyChecked
        # 显示节点数据
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.ToolTipRole:
            if short_name is None:
                short_name = item.get_item_name()
            return short_name
        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False

        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            item = index.internalPointer()
            new_state = "TRUE" if value == Qt.CheckState.Checked else "FALSE"
            item.get_data()["VCOS2:Value"] = new_state
            self.item_state_cache[item.get_path()] = new_state
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])

            # 更新父节点的状态，并且发出 dataChanged 信号
            self._update_parent_check_state(index, new_state)
            # 更新所有子节点的状态，并且发出 dataChanged 信号
            self._update_children_check_state(index, new_state)

            return True

        return False

    def _update_parent_check_state(self, child_index: QModelIndex, new_state: str):
        # 获取子项的内部对象
        child_item = child_index.internalPointer()
        # 检索父项
        parent_item = child_item.get_parent()

        while parent_item:
            all_checked = True
            some_checked = False
            if parent_item.get_path() == "/":
                break
            # 检查父节点所有子节点的状态
            for child in parent_item.get_children():
                state = child.get_data().get("VCOS2:Value", "none").lower()
                if state == "false":
                    all_checked = False
                else:
                    some_checked = True

            if new_state.lower() == "false" and not some_checked:
                # 如果新状态是去勾选，且没有其他子节点处于勾选状态，则将父节点取消勾选
                parent_item.get_data()["VCOS2:Value"] = "FALSE"
            elif all_checked:
                # 如果所有子节点都被勾选，则将父节点勾选
                parent_item.get_data()["VCOS2:Value"] = "TRUE"

            # 更新父节点状态信息到缓存
            self.item_state_cache[parent_item.get_path()] = parent_item.get_data()["VCOS2:Value"]

            # 获取父项的索引
            parent_row = parent_item.get_row()
            parent_parent_item = parent_item.get_parent()
            if parent_parent_item:
                parent_index = self.createIndex(parent_row, 0, parent_item)
            else:
                parent_index = QModelIndex()

            # 使用获取到的 parent_index 发出 dataChanged 信号
            self.dataChanged.emit(parent_index, parent_index, [Qt.ItemDataRole.CheckStateRole])

            # 继续向上遍历祖先节点
            child_item = parent_item
            parent_item = parent_item.get_parent()

    def _update_children_check_state(self, parent_index: QModelIndex, new_state: str):
        # 获取父项
        parent_item = parent_index.internalPointer()

        # 对每个子项进行更新，只有当状态不是PartiallyChecked
        for row in range(parent_item.child_count()):
            child_index = self.index(row, 0, parent_index)
            child_item = child_index.internalPointer()

            # 获取当前子项的检查状态
            current_state = self.data(child_index, Qt.CheckStateRole)

            if current_state != Qt.CheckState.PartiallyChecked:
                # 更新和 发出信号
                child_item.get_data()["VCOS2:Value"] = new_state
                self.item_state_cache[child_item.get_path()] = new_state
                self.dataChanged.emit(child_index, child_index, [Qt.CheckStateRole])

            # 递归更新下一层的子节点，如果子节点不是PartiallyChecked
            if child_item.child_count() > 0:
                self._update_children_check_state(child_index, new_state)

    def apply_cached_changes(self, dialog_type):
        # 1. 更新BswMComminData
        self.callback("sec_bsw_editor_update_state_to_bswm_common_data", self.item_state_cache, dialog_type)
        self.item_state_cache.clear()

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        return super().flags(index) | Qt.ItemFlag.ItemIsUserCheckable

    # 在parent节点下, 第row行, 第column列位置上创建索引
    def index(self, row: int, column: int, parent: QModelIndex = ...) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()
        child_item = parent_item.get_child(row)
        if child_item:
            return self.createIndex(row, column, child_item)  # 展开树形, 为子节点建立索引
        else:
            return QModelIndex()

    def itemFromIndex(self, index: QModelIndex) -> "ArgQTreeItem":
        """
        返回给定索引关联的项。
        """
        if index.isValid():
            return index.internalPointer()
        return None

    def parent(self, child=None):
        if child is None:
            # 返回parent
            return super().parent()
        if not child.isValid():
            return QModelIndex()
        child_item = child.internalPointer()
        parent_item = child_item.get_parent()
        # 顶层节点, 直接返回空索引
        if parent_item == self.root_item:
            return QModelIndex()
        # 为父节点建立索引
        return self.createIndex(parent_item.get_row(), 0, parent_item)

    # 获取索引parent下有多少行
    def rowCount(self, parent: QModelIndex = ...) -> int:
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()
        return parent_item.child_count()  # 返回父节点下子节点数目

    # 返回索引parent下有多少列
    def columnCount(self, parent: QModelIndex = ...) -> int:
        return self.root_item.column_count()

    def init_model_data(self):
        self.enable_modules_list = self.callback("get_enable_modules")
        self.initialized_function_list = self.callback("sec_get_init_functions_that_have_been_initialized_in_ecum")
        # 从根节点开始遍历admin_data字典并添加符合条件的到树中
        if self.support_cfg_module_init_list:
            self.add_items(self.root_item, self.support_cfg_module_init_list, "/")

    def add_items(self, parent_item, current_dict, parent_path):
        item_state_cache = {}
        # parent_path = parent_item.get_path()
        # 遍历当前字典中的所有键值对
        for key, value in current_dict.items():
            # 如果值是字典并且键开头不是'VCOS2:Feature'，进行递归查找子节点中的'VCOS2:Feature'
            if isinstance(value, dict) and not key.startswith("VCOS2:Feature"):
                # 继续递归遍历子字典
                child_path = f"{parent_path}{key}/"
                self.add_items(parent_item, value, child_path)
            elif key.startswith("VCOS2:Feature"):
                # 获取'VCOS2:Value'的值，用于判断是否添加到树中
                item_value = value.get("VCOS2:Value", "none").lower()
                # 如果'VCOS2:Value'是"true"或"false"，则创建一个新的树节点项
                if item_value in ["true", "false"]:
                    # 创建新的ArgQTreeItem节点实例
                    child_path = f"{parent_path}{key}/"
                    module_name = value.get("VCOS2:BswModule", "none")
                    if module_name != "none" and module_name not in self.enable_modules_list:
                        continue
                    alias = None
                    if module_name != "none":
                        for initialized_function in self.initialized_function_list:
                            if key.split(":")[-1] == initialized_function.split(" ")[0]:
                                alias = initialized_function
                                item_state_cache = {}
                                item_state_cache[child_path] = "FALSE"
                                self.callback(
                                    "sec_bsw_editor_update_state_to_bswm_common_data", item_state_cache, "INIT"
                                )
                                break
                    child_item = ArgQTreeItem(key.split(":")[-1], value, path=parent_path + key, alias=alias)
                    parent_item.append_child(child_item)  # 添加到父节点下
                    # 继续递归遍历此项字典中的子项

                    self.add_items(child_item, value, child_path)


class ArgQTreeView(QTreeView):

    def __init__(self, bswmd_autosar_obj_dict=None) -> None:
        super().__init__()
        self.bswmd_autosar_obj_dict = bswmd_autosar_obj_dict
        self.setHeaderHidden(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.callback = lambda *args, **kwargs: None

    def set_callback(self, callback):
        self.callback = callback

    def dropEvent(self, e: QtGui.QDropEvent) -> None:
        if e.dropAction() == Qt.DropAction.MoveAction:
            self.setCurrentIndex(QModelIndex())
        return super().dropEvent(e)

    def get_current_tree_item(self):
        index = self.currentIndex()
        item: ArgQTreeItem = index.internalPointer()
        return item


class SecBswManagementDialog(QDialog):

    def __init__(
        self,
        dialog_title,
        dialog_type,
        create_sub_container_rules,
        main_window,
        support_cfg_module_init_list: dict,
        call_back,
    ) -> None:
        super().__init__(main_window)
        self.dialog_title = dialog_title
        self.dialog_type = dialog_type
        self.create_sub_container_rules = create_sub_container_rules
        self.main_window = main_window
        self.support_cfg_module_init_list = support_cfg_module_init_list
        self.callback = call_back

        self.setWindowTitle(self.dialog_title)
        self.setMinimumSize(500, 600)
        # 移除问号帮助按钮并添加最大化按钮
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint | Qt.WindowType.WindowMaximizeButtonHint
        )

        self.tree_model = ArgQTreeModel(support_cfg_module_init_list, call_back=self.callback)
        self.tree_view = ArgQTreeView()
        self.tree_view.set_callback(self.callback)
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setDropIndicatorShown(True)
        self.tree_view.setDragDropOverwriteMode(False)
        self.tree_view.setDragDropMode(ArgQTreeView.DragDropMode.InternalMove)
        self.tree_view.setSelectionMode(ArgQTreeView.SelectionMode.ExtendedSelection)
        self.tree_view.setSelectionBehavior(ArgQTreeView.SelectionBehavior.SelectItems)
        self.tree_view.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tree_view.expandToDepth(1)
        # self.tree_model.dataChanged.connect(self.onDataChanged)
        # 创建主垂直布局
        main_layout = QVBoxLayout()

        # 添加树视图到主布局
        main_layout.addWidget(self.tree_view)

        # 创建按钮的水平布局
        buttons_layout = QHBoxLayout()

        # 添加一个弹性空间来推动按钮到布局的右侧
        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        buttons_layout.addItem(spacer)

        # 创建并添加按钮
        self.finish_button = QPushButton("Finish")
        self.cancel_button = QPushButton("Cancel")
        buttons_layout.addWidget(self.finish_button)
        buttons_layout.addWidget(self.cancel_button)

        # 连接按钮信号到槽函数
        self.finish_button.clicked.connect(self.on_finish_clicked)
        self.cancel_button.clicked.connect(self.on_cancel_clicked)

        # 将按钮布局添加到主布局
        main_layout.addLayout(buttons_layout)

        # 设置对话框的主布局
        self.setLayout(main_layout)

    def on_finish_clicked(self):
        # 点击 Finish 按钮时，应用所有缓存的更改
        self.tree_model.apply_cached_changes(self.dialog_type)
        # 2. 根据更新后的BswMComminData，check当前bswm_ecuc.arxml中container的情况，
        #    如果为True，则bswm_ecuc.arxml中需要存在相应的container（如果不存在则创建）
        #    如果为False，则bswm_ecuc.arxml中应该不存在相应的container（如果存在则删除）
        #    这样处理，处理逻辑应该是最简单的，check的内容不多，无需考虑性能问题
        self.callback(
            "sec_bsw_editor_check_container_of_bswm_ecuc",
            self.dialog_type,
            self.create_sub_container_rules,
            result_callback=self.main_window.over_view_ui.update_bsw_modules_view_switch,
        )

        # 触发任何需要的回调，更新后台数据
        self.applyChangesToBackend()

        self.accept()

    def applyChangesToBackend(self):
        # 收集当前模型中所有节点的状态，调用callback更新后端
        # 你可以在这里遍历模型的所有项，然后对每一项调用callback
        # 根据你的需求来实现
        pass

    def on_cancel_clicked(self):
        # 点击 Cancel 按钮执行
        self.callback(
            "sec_bsw_editor_check_container_of_bswm_ecuc",
            self.dialog_type,
            self.create_sub_container_rules,
            result_callback=self.main_window.over_view_ui.update_bsw_modules_view_switch,
        )
        self.reject()
