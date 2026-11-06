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
from typing import List, Any, Iterable
import threading
import ctypes
import pickle
from func_module.mapping.task_mapping_helper import TaskMappingItemData, TaskMappingTreeItem
from cfg_gui.rte_editor.mapping.mapping_view_config import MappingViewConfig
from cfg_gui.rte_editor.mapping.mapping_tree_view import MappingTreeView
from cfg_gui.rte_editor.mapping.mapping_table_view import MappingTableView
from cfg_gui.rte_editor.mapping.mapping_table_header_view import MappingTableHeaderView
from cfg_gui.rte_editor.mapping.mapping_filter_proxy_model import MappingFilterProxyModel


class TaskMappingUI(QtWidgets.QWidget):

    def __init__(self, parent=None, cbk=None):
        super().__init__(parent)
        self.callback = cbk
        self.category = "task_mapping_"

        self.tree_view_model = None
        self.table_view_model = None
        self.tree_view = None
        self.table_view = None
        self.tree_menu = None
        self.table_menu = None
        self.setup_ui()
        self.init()

    def setup_ui(self):
        self.horizontal_layout = QtWidgets.QHBoxLayout(self)
        self.tree_view_config = MappingViewConfig()
        self.tree_view_config.size_adjust_policy = QtWidgets.QAbstractScrollArea.AdjustToContents
        self.tree_view_config.drag_enabled = True
        self.tree_view_config.drag_drop_mode = QtWidgets.QAbstractItemView.DragOnly
        self.tree_view_config.drag_drop_overwrite_mode = False
        self.tree_view_config.drop_action = QtCore.Qt.DropAction.IgnoreAction
        self.tree_view = MappingTreeView(self.tree_view_config, self)
        self.table_proxy_model = MappingFilterProxyModel()
        self.table_header_view = MappingTableHeaderView(self.table_proxy_model)
        self.table_view_config = MappingViewConfig()
        self.table_view_config.size_adjust_policy = QtWidgets.QAbstractScrollArea.AdjustToContents
        self.table_view_config.drag_enabled = True
        self.table_view_config.drag_drop_overwrite_mode = True
        self.table_view_config.drag_drop_mode = QtWidgets.QAbstractItemView.DragDrop
        self.table_view_config.alternating_row_colors = True
        self.table_view = MappingTableView(self.table_view_config, self)
        self.table_view.setHorizontalHeader(self.table_header_view)
        self.filter_table_layout_v = QtWidgets.QVBoxLayout()
        self.clear_filter_button = QtWidgets.QPushButton("Clear All Filters")
        self.clear_filter_button.clicked.connect(self.clear_filter_button_clicked_slot)
        self.filter_text = QtWidgets.QLineEdit()
        self.filter_text.setPlaceholderText("<Filter>")
        self.filter_text.textChanged.connect(self.filter_text_changed_solt)
        self.splitter = QtWidgets.QSplitter(Qt.Orientation.Horizontal)
        self.filter_table_layout_v.addWidget(self.clear_filter_button)
        self.filter_table_layout_v.addWidget(self.filter_text)
        self.filter_table_layout_v.addWidget(self.table_view)
        self.button_filter_table_widget = QtWidgets.QWidget()
        self.button_filter_table_widget.setLayout(self.filter_table_layout_v)
        self.splitter.addWidget(self.tree_view)
        self.splitter.addWidget(self.button_filter_table_widget)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        self.horizontal_layout.addWidget(self.splitter)

    def init(self):
        self.init_tree_view()
        self.init_table_view()

    def init_tree_view(self):
        tree_view: QtWidgets.QTreeView = self.tree_view
        tree_view.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)

        tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)  # 打开右键菜单的策略
        tree_view.customContextMenuRequested.connect(self.show_tree_context_menu_slot)  # 绑定事件

        def update_tree_scroll_area_slot(tree_view: QtWidgets.QTreeView, index: QtCore.QModelIndex):
            tree_view.resizeColumnToContents(index.column())

        tree_view.expanded.connect(lambda index: update_tree_scroll_area_slot(tree_view, index))
        tree_view.collapsed.connect(lambda index: update_tree_scroll_area_slot(tree_view, index))

        tree_view.doubleClicked.connect(self.select_table_item_slot)
        tree_view.expandToDepth(0)

    def init_table_view(self):
        table_view: QtWidgets.QTableView = self.table_view

        table_view.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)

        btn: QtWidgets.QAbstractButton = table_view.findChild(QtWidgets.QAbstractButton)
        btn.setStyleSheet("QTableCornerButton::section{font:9pt 'Microsoft YaHei UI';}")
        btn.setEnabled(False)
        btn.setText("Position")
        btn.setToolTip("Position")
        btn.installEventFilter(self)
        font = QtGui.QFont("Microsoft YaHei UI", 9)
        font_metrics = QtGui.QFontMetrics(font)
        text_width = font_metrics.horizontalAdvance("Position")
        horizontal_padding = 20
        min_width = text_width + horizontal_padding
        table_view.verticalHeader().setMinimumWidth(min_width)
        table_view.verticalHeader().setSectionsClickable(False)
        table_view.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Fixed)
        table_view.verticalHeader().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        table_view.horizontalHeader().setSectionsClickable(False)
        table_view.horizontalHeader().setStyleSheet("QHeaderView::section{background:lightgray;}")
        table_view.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table_view.customContextMenuRequested.connect(self.show_table_context_menu_slot)

    def set_callback(self, cbk):
        self.callback = cbk

    def set_update_overview(self, cbk):
        self.update_overview = cbk

    def _post_update_os_ecuc(self):
        self.callback("task_mapping_post_update_os_ecuc")

    def update_task_mapping_ui(self, init_flags, is_update_overview=False):
        self.init_flags = init_flags
        self.is_update_overview = is_update_overview
        self.callback("task_mapping_update_ui_all", result_callback=self._update_and_set_model)

    def _update_and_set_model(self, param):
        if not self.tree_view_model:
            self.tree_view_model = TaskMappingTreeModel(self, self.init_flags)

        if self.tree_view.model() != self.tree_view_model:
            if self.tree_view_model.check_data():
                self.tree_view.setModel(self.tree_view_model)
        else:
            self.tree_view_model.init_flags = self.init_flags
            self.tree_view_model.initTreeData()

        if not self.table_view_model:
            self.table_view_model = TaskMappingTableModel(self, True)
            self.table_proxy_model.setSourceModel(self.table_view_model)

        if self.table_view.model() != self.table_proxy_model:
            if self.table_view_model.check_data():
                self.table_view.setModel(self.table_proxy_model)
        else:
            self.table_view_model.initTableData()

        self.tree_view.expandToDepth(0)

        if self.is_update_overview:
            self.update_overview("Os")
            self.update_overview("Rte")

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent):
        if event.type() != QtCore.QEvent.Type.Paint or not isinstance(obj, QtWidgets.QAbstractButton):
            return False
        # Paint by hand (borrowed from QTableCornerButton)
        opt = QtWidgets.QStyleOptionHeader()
        opt.initFrom(obj)
        styleState = QtWidgets.QStyle.StateFlag.State_None
        if obj.isEnabled():
            styleState |= QtWidgets.QStyle.StateFlag.State_Enabled
        if obj.isActiveWindow():
            styleState |= QtWidgets.QStyle.StateFlag.State_Active
        if obj.isDown():
            styleState |= QtWidgets.QStyle.StateFlag.State_Sunken
        opt.state = styleState
        # This line is the only difference to QTableCornerButton
        opt.text = obj.text()
        opt.position = QtWidgets.QStyleOptionHeader.SectionPosition.OnlyOneSection
        painter = QtWidgets.QStylePainter(obj)
        painter.drawControl(QtWidgets.QStyle.ControlElement.CE_Header, opt)
        return True

    def show_table_context_menu_slot(self, pos: QtCore.QPoint):
        if self.table_menu is None:
            menu, action = self.create_menu()
            action.triggered.connect(lambda: self.table_action_unmap_slot())
            self.table_menu = menu
        self.table_menu.popup(QtGui.QCursor.pos())

    def create_menu(self):
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:lightgray;}"  # 选项背景颜色
            "QMenu{border:1px solid lightgray;}"  # 设置整个菜单框的边界高亮厚度颜色
            "QMenu::item{padding:0px 10px 0px 5px;}"  # 以文字为标准，右边距文字40像素，左边同理
            "QMenu::item{height:20px;}"  # 显示菜单选项高度
            "QMenu::item{color:black;}"  # 选项文字颜色
            "QMenu::item{background:lightgray;}"  # 选项背景
            "QMenu::item{margin:1px 1px 1px 1px;}"  # 每个选项四边的边界厚度，上，右，下，左
            "QMenu::item:selected:enabled{background:lightskyblue;}"  # 选项选中颜色
        )
        action = menu.addAction(QtGui.QIcon(":/not_ok.svg"), "Unmap")
        return menu, action

    def get_tree_parent_name(self, parent=QtCore.QModelIndex()):
        parent_item = parent.internalPointer()
        parent_name = "root"
        if parent_item:
            parent_name = parent_item.data

        return parent_name

    def get_tree_expand_dict(self, parent=QtCore.QModelIndex()):
        expanded_item_dict = {}
        for row in range(self.tree_view_model.rowCount(parent)):
            parent_name = self.get_tree_parent_name(parent)
            # 使用index函数来获取索引
            index = self.tree_view_model.index(row, 0, parent)
            # 使用view来获取索引项的折叠/展开状态
            if self.tree_view.isExpanded(index):
                if parent_name not in expanded_item_dict:
                    expanded_item_dict.update({parent_name: set()})
                expanded_item_dict[parent_name].add(row)

            # 如果还有子级别，递归进行
            if self.tree_view_model.hasChildren(index):
                expanded_item_dict.update(self.get_tree_expand_dict(index))
        return expanded_item_dict

    def restore_tree_expand_dict(self, expanded_item_dict, parent=QtCore.QModelIndex()):
        for row in range(self.tree_view_model.rowCount(parent)):
            parent_name = self.get_tree_parent_name(parent)
            # 使用index函数来获取索引
            index = self.tree_view_model.index(row, 0, parent)
            if parent_name in expanded_item_dict and row in expanded_item_dict[parent_name]:
                self.tree_view.expand(index)

            # 如果还有子级别，递归进行
            if self.tree_view_model.hasChildren(index):
                self.restore_tree_expand_dict(expanded_item_dict, index)
        return

    def table_action_unmap_slot(self):
        if not self.table_view.selectionModel():
            return
        index_list = []
        indexs = self.table_view.selectionModel().selectedIndexes()
        for index in indexs:
            i = self.table_view_model.columnCount() * index.row() + index.column()
            index_list.append(i)

        cbk_param = {}
        cbk_param.update({"unmap_index_list": index_list})
        self.callback("task_mapping_table_unmap", cbk_param)
        # NOTE:validation或者generation操作之后，只update_view不能及时更新页面
        self.update_model()

    def select_table_item_slot(self, index: QtCore.QModelIndex):
        model: TaskMappingTableModel = self.table_view_model
        item: TaskMappingTreeItem = index.internalPointer()
        if not item:
            return
        cbk_param = {}
        cbk_param.update({"select_item_id": item.id})
        i = self.callback("task_mapping_get_item_index", cbk_param)
        if i is None:
            return
        col_count = model.columnCount()
        cur_row = int(i / col_count)
        cur_col = i % col_count
        cur_index = self.table_proxy_model.index(cur_row, cur_col)

        self.table_view.setFocus()
        self.table_view.scrollTo(cur_index, QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter)
        self.table_view.selectionModel().select(cur_index, QtCore.QItemSelectionModel.SelectionFlag.SelectCurrent)

    def show_tree_context_menu_slot(self, pos: QtCore.QPoint):
        if self.tree_menu is None:
            menu, action = self.create_menu()
            action.triggered.connect(lambda: self.tree_action_unmap_slot())
            self.tree_menu = menu
        self.tree_menu.popup(QtGui.QCursor.pos())

    def tree_action_unmap_slot(self):
        if not self.tree_view.selectionModel():
            return
        item_id_list = []
        indexs = self.tree_view.selectionModel().selectedIndexes()
        for index in indexs:
            tree_item: TaskMappingTreeItem = index.internalPointer()
            if tree_item.id not in item_id_list:
                item_id_list.append(tree_item.id)

        cbk_param = {}
        cbk_param.update({"unmap_item_id_list": item_id_list})
        self.callback("task_mapping_tree_unmap", cbk_param)
        # NOTE:validation或者generation操作之后，只update_view不能及时更新页面
        self.update_model()

    def update_model(self):
        if not self.table_view_model or not self.tree_view_model:
            return
        self.table_view_model.initTableData()
        if self.tree_view_model.check_data_changed():
            expanded_item_dict = self.get_tree_expand_dict()
            self.tree_view_model.initTreeData()
            self.restore_tree_expand_dict(expanded_item_dict)
        self.tree_view.viewport().update()
        self.table_view.viewport().update()

    def filter_text_changed_solt(self, text: str):
        self.table_proxy_model.set_filter_pattern(text)

    def clear_filter_button_clicked_slot(self):
        self.filter_text.clear()
        self.table_header_view.clear_all_filter()
        self.table_proxy_model.clear_all_filter_patterns()


class TaskMappingTreeModel(QtCore.QAbstractItemModel):

    def __init__(self, task_mapping_ui: TaskMappingUI, init_flags):
        super().__init__()
        self.task_mapping_ui = task_mapping_ui
        self.init_flags = init_flags
        self.callback = self.task_mapping_ui.callback
        self.init()
        pass

    def check_data(self):
        self.root_item = self.callback("task_mapping_get_root_item")
        if self.root_item is None:
            return False

        return True

    def init(self):
        # 清空数据
        self.root_item = None
        # 获取新的数据
        self.root_item = self.callback("task_mapping_get_root_item")
        pass

    def check_data_changed(self):
        cur_root_item = self.callback("task_mapping_get_root_item")
        return id(cur_root_item) != id(self.root_item)

    # 获取index位置上的data
    def data(self, index: QtCore.QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        item: TaskMappingTreeItem = index.internalPointer()
        # 添加图标
        category_list = ["Application Components", "Service Components", "Schedulable Entities"]
        if role == Qt.ItemDataRole.DecorationRole:
            if not item.mapped and isinstance(item.data, dict) and len(item.child_items) == 0:
                return QtGui.QIcon(":/unavailable.svg")
            if not item.mapped and isinstance(item.data, str) and item.data not in category_list:
                return QtGui.QIcon(":/unavailable.svg")
        # 显示节点数据值
        if role == Qt.ItemDataRole.DisplayRole:
            if isinstance(item.data, str):
                return item.data
            if isinstance(item.data, dict):
                return item.data["RunnableName"]
        elif role == Qt.ItemDataRole.ToolTipRole:
            if isinstance(item.data, dict):
                return (
                    f"TriggerCategory: {item.data['TriggerCategory']}\n"
                    f"TriggerCondition: {item.data['TriggerCondition']}"
                )
        return None

    # 用于拖放数据时存储
    def mimeData(self, indexes: Iterable[QtCore.QModelIndex]) -> QtCore.QMimeData:
        mimedata = QtCore.QMimeData()
        datas = []
        for index in indexes:
            item: TaskMappingTreeItem = index.internalPointer()
            if item.data is None:
                continue
            datas.append(id(item.item_data))
        mimedata.setData("id", pickle.dumps((datas)))
        return mimedata

    def mimeTypes(self) -> List[str]:
        return ["id"]

    # 获取index位置对象属性和状态
    def flags(self, index: QtCore.QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        item: TaskMappingTreeItem = index.internalPointer()
        if item and isinstance(item.data, dict) and len(item.child_items) == 0:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled
        else:
            return Qt.ItemFlag.ItemIsEnabled

    # 获取表头数据
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.root_item.data(section)
        return None

    # 在parent节点下, 第row行, 第column列位置上创建索引
    def index(self, row: int, column: int, parent: QtCore.QModelIndex = ...) -> QtCore.QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        if not parent.isValid():
            parentItem = self.root_item
        else:
            parentItem = parent.internalPointer()
        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)  # 展开树形, 为子节点建立索引
        else:
            return QtCore.QModelIndex()

    # 创建index的父索引
    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        if not index.isValid():
            return QtCore.QModelIndex()
        childItem = index.internalPointer()
        parentItem = childItem.parent()
        # 顶层节点, 直接返回空索引
        if parentItem == self.root_item:
            return QtCore.QModelIndex()
        # 为父节点建立索引
        return self.createIndex(parentItem.row(), 0, parentItem)

    # 获取索引parent下有多少行
    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        if not parent.isValid():
            parentItem = self.root_item
        else:
            parentItem = parent.internalPointer()
        if parentItem:
            return parentItem.childCount()  # 返回父节点下子节点数目
        else:
            return 0

    # 返回索引parent下有多少列
    def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return self.root_item.columnCount() if self.root_item else 0

    def supportedDragActions(self) -> Qt.DropActions:
        return Qt.DropAction.MoveAction

    def supportedDropActions(self) -> Qt.DropActions:
        return Qt.DropAction.MoveAction

    def initTreeData(self):
        self.beginResetModel()
        self.init()
        self.endResetModel()


class TaskMappingTableModel(QtCore.QAbstractTableModel):
    lock = threading.RLock()

    def __init__(self, task_mapping_ui: TaskMappingUI, update_cfg=False) -> None:
        super().__init__()
        self.task_mapping_ui = task_mapping_ui
        self.update_cfg = update_cfg
        self.callback = self.task_mapping_ui.callback
        self.init()
        pass

    def check_data(self):
        self.item_list = self.callback("task_mapping_get_item_list")
        if not self.item_list:
            return False

        return True

    def init(self):
        # 清空数据
        self.item_list = []
        self.table_headers = []

        # 获取新的数据
        self.item_list = self.callback("task_mapping_get_item_list")
        self.table_headers = self.callback("task_mapping_get_table_headers")
        self.col_count = len(self.table_headers)
        pass

    def flags(self, index: QtCore.QModelIndex) -> int:
        if index.data():
            return (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
                | Qt.ItemFlag.ItemIsDropEnabled
            )
        else:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsDropEnabled

    def rowCount(self, parent=QtCore.QModelIndex()) -> int:
        """
        重写rowCount函数, 返回表格模型的行数
        """
        if self.col_count == 0:
            return 0
        row = int(len(self.item_list) / self.col_count)
        return row

    def columnCount(self, parent=QtCore.QModelIndex()) -> int:
        """
        重写columnCount函数, 返回表格模型的列数
        """
        return self.col_count

    def index(self, row: int, column: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        """
        重写index函数, 为每个单元格创建一个唯一的索引
        """
        i = row * column + column
        item = None
        if i >= len(self.item_list):
            return self.createIndex(row, column, item)
        try:
            item = self.item_list[i]
        except BaseException:
            pass
        return self.createIndex(row, column, item)

    def data(self, index: QtCore.QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """
        重写data函数, 返回视图上显示的数据, 该函数会被视图多次调用
        """
        # 获取单元格数据在self._item_list中的下标位置
        i = index.row() * self.col_count + index.column()

        # 设置单元格中数据的对其方式
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter

        # 根据角色返回单元格的数据
        if i >= len(self.item_list):
            return ""
        item = None
        bind_item_list = []
        try:
            item = self.item_list[i].data
            bind_item_list = self.item_list[i].bind_item_list
        except BaseException:
            pass
        if role == Qt.ItemDataRole.DisplayRole:
            if item:
                return item["RunnableName"]
        elif role == Qt.ItemDataRole.ToolTipRole:
            tip_str = " "
            for bind_item in bind_item_list:
                if bind_item["IsServiceComponent"]:
                    module = "Service Component"
                elif bind_item["IsMainFunction"]:
                    module = "Module"
                else:
                    module = "Component"
                tip_str += (
                    f"TriggerCategory: {bind_item['TriggerCategory']}, "
                    f"TriggerCondition: {bind_item['TriggerCondition']}, "
                    f"Owner: {module} {bind_item['Component']}\n"
                )
            return tip_str[:-1]

        # 其余角色使用无效数据
        return None

    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        """
        重写parent方法, 返回表格模型的父索引, 因为所有单元格都是顶级节点, 所以使用无效节点作为父节点
        """
        return QtCore.QModelIndex()

    def supportedDragActions(self) -> int:
        return Qt.DropAction.MoveAction

    def supportedDropActions(self) -> int:
        return Qt.DropAction.MoveAction

    def mimeData(self, indexes) -> QtCore.QMimeData:
        mimedata = QtCore.QMimeData()
        datas = []
        for index in indexes:
            i = index.row() * self.col_count + index.column()
            item_data = self.item_list[i].item_data
            datas.append(id(item_data))
        mimedata.setData("id", pickle.dumps((datas)))
        return mimedata

    def mimeTypes(self) -> List[str]:
        return ["id"]

    def get_item_data_list(self, mimedata):
        # 用于反序列化出所需的python对象
        obj_ids = pickle.loads(mimedata.data("id").data())
        # 需要用list, 这样才能保证有序
        item_data_list = []
        for obj_id in obj_ids:
            item_data: TaskMappingItemData = ctypes.cast(obj_id, ctypes.py_object).value
            item_data_list.append(item_data)
        return item_data_list

    # 1）拖动分两种：一种是从左侧界面拖动到右侧界面，一种是单独右侧界面上的操作
    def dropMimeData(
        self, mimedata: QtCore.QMimeData, action: Qt.DropAction, row: int, column: int, parent: QtCore.QModelIndex
    ) -> bool:
        target_row = parent.row()
        target_col = parent.column()
        i = target_row * self.col_count + target_col
        if i < 0:
            return False
        if action != Qt.DropAction.MoveAction:
            return False

        cbk_param = {}
        cbk_param.update({"remap_item_data_list": self.get_item_data_list(mimedata)})
        cbk_param.update({"target_row": target_row})
        cbk_param.update({"target_col": target_col})

        self.callback("task_mapping_remap_data", cbk_param)
        self.task_mapping_ui.update_model()

        return True

    def get_owner_info(self, table_cell_bind_item):
        if table_cell_bind_item["IsServiceComponent"]:
            module = "Service Component"
        elif table_cell_bind_item["IsMainFunction"]:
            module = "Module"
        else:
            module = "Component"

        return f"{module} {table_cell_bind_item['Component']}"

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if section >= len(self.table_headers):
                return None
            return (
                f"{self.table_headers[section]['OsApplName']}\n"
                f"{self.table_headers[section]['OsTaskName']}\n"
                f"Priority {self.table_headers[section]['OsTaskPriority']}"
            )
        if orientation == Qt.Orientation.Vertical:
            return int(section)

    def initTableData(self):
        self.beginResetModel()
        self.init()
        self.endResetModel()
