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
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableView,
    QSpacerItem,
    QSizePolicy,
    QCheckBox,
    QLineEdit,
)
from cfg_gui.widgets.table_header_view import ArgQHeaderView
from typing import Any
from cfg_gui.widgets.container_outline import WidgetSortFilterProxyModel


class ContainerOutlineItem:

    def __init__(
        self,
        show_data_item,
        show_data_item_key,
        callback=None,
        show_data_row=None,
    ):

        self.callback = callback
        self.show_data_item_key = show_data_item_key
        self.show_data_row = show_data_row
        self.show_data_item = show_data_item

    def display_text(self):
        """
        Return dispaly text of this item
        """
        if self.show_data_item_key != "checked":
            return self.show_data_item["value"]
        else:
            return None


class TableModel(QAbstractTableModel):

    def __init__(self, show_data_list, editable_columns, callback=None, parent=None) -> None:
        super().__init__(parent)
        self.editable_columns = editable_columns if editable_columns is not None else []
        self.callback = callback
        self.head_data = []
        self.show_data_list = show_data_list
        self.row_count = self.get_row_count(self.show_data_list)
        self.column_count = self.get_column_count(self.show_data_list)
        self.get_head_data()
        self.table_items = self.init_table_item()

    def get_row_count(self, show_data_list):
        return len(show_data_list)

    def get_column_count(self, show_data_list):
        if self.row_count > 0:
            return len(show_data_list[0])
        else:
            return 0

    def get_head_data(self):
        if self.row_count > 0:
            for key in self.show_data_list[0]:
                self.head_data.append(key)

    def init_table_item(self):
        table_items = []
        for show_data_row in self.show_data_list:
            container_row = []

            for show_data_item_key, show_data_item in show_data_row.items():
                container_row.append(
                    ContainerOutlineItem(show_data_item, show_data_item_key, self.callback, show_data_row)
                )

            table_items.append(container_row)

        return table_items

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return self.row_count

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return self.column_count

    def data(self, index: QModelIndex, role: int = ...) -> Any:
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        # 返回第一列的复选框状态
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            return self.show_data_list[index.row()]["checked"]
        elif role == Qt.ItemDataRole.DisplayRole:
            target_item: ContainerOutlineItem = self.table_items[index.row()][index.column()]
            return target_item.display_text()

    def setData(self, index: QModelIndex, value: Any, role: int = ...) -> bool:
        # 设置第一列的复选框状态
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            self.show_data_list[index.row()]["checked"] = value
            self.dataChanged.emit(index, index)
            return True
        elif role == Qt.ItemDataRole.EditRole:
            row = index.row()
            column = index.column()
            if value:
                getattr(self.table_items[row][column], "show_data_item")["value"] = value
            self.dataChanged.emit(index, index, [role])
            return True
        else:
            return super().setData(index, value, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        flags |= Qt.ItemFlag.ItemIsSelectable
        if index.column() == 0:
            flags |= Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
        if index.column() in self.editable_columns:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        # 检查 row 和 column 是否在正确的范围内，然后调用基类的 index 方法
        if self.hasIndex(row, column, parent):
            return super(TableModel, self).index(row, column, parent)
        else:
            return QModelIndex()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        # def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> Any:
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignLeft

        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.head_data[section]
            if orientation == Qt.Orientation.Vertical:
                return None

        return super().headerData(section, orientation, role)

    def get_column_raw_data(self, column: int):
        # Get raw item data of specific row from table items
        return [row[column] for row in self.table_items]

    def update_check_state(self, state):
        # 更新内部数据前暂停数据更改通知
        self.beginResetModel()

        # 批量更新内部数据状态
        for row in range(self.rowCount()):
            self.show_data_list[row]["checked"] = state

        # 更新完成后恢复数据更改通知
        self.endResetModel()

    def update_row_check_state(self, row: int, checked_state):
        self.show_data_list[row]["checked"] = checked_state
        index = self.index(row, 0)  # 获取模型中行的索引
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])  # 发出数据改变信号


class ArgQCreateContainerDialog(QDialog):
    def __init__(
        self,
        create_container_dialog_show_data,
        fill_in_param_value_list_dict,
        callback,
        children_list=[],
        init_phase=None,
        key_column_index=1,
    ):
        super().__init__()
        self.create_container_dialog_show_data = create_container_dialog_show_data
        self.fill_in_param_value_list_dict = fill_in_param_value_list_dict
        self.callback = callback
        self.key_column_index = key_column_index
        self.init_phase = init_phase
        self.children_list = children_list
        self.dialog_title = "Create EcuMDriverInitltem"
        self.update_create_container_dialog_show_data_by_enable_module_list()
        self.update_create_container_dialog_show_data()

        self.setWindowTitle(self.dialog_title)
        self.setMinimumSize(500, 600)
        # 移除问号帮助按钮并添加最大化按钮
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint | Qt.WindowType.WindowMaximizeButtonHint
        )
        # 初始化数据和模型
        self.init_model()

        # 初始化表格视图
        self.init_table_view()

        # 设置控件布局
        self.setup_layouts()

    def init_model(self):

        editable_columns = [1]
        self.model = TableModel(self.create_container_dialog_show_data, editable_columns, callback=self.callback)
        self.sort_proxy_model = WidgetSortFilterProxyModel(self.init_phase)
        self.sort_proxy_model.setSourceModel(self.model)

    def init_table_view(self):
        self.tableView = QTableView()
        self.tableView.setModel(self.sort_proxy_model)
        self.horizontal_header_view = ArgQHeaderView(Qt.Orientation.Horizontal, self.tableView)
        self.tableView.setHorizontalHeader(self.horizontal_header_view)
        self.tableView.setSortingEnabled(True)
        self.horizontal_header_view.set_sort_indicator_clearable(True)

    def setup_layouts(self):
        # 上方全局复选框
        self.hide_used_checkbox = QCheckBox("Hide InitFunctions already used")
        self.hide_incompatible_checkbox = QCheckBox("Hide functions of incompatible init phases")
        # 默认选中复选框，并应用过滤条件
        self.hide_used_checkbox.setChecked(True)
        self.hide_incompatible_checkbox.setChecked(True)
        self.apply_filters()  # 应用默认的过滤条件
        self.hide_used_checkbox.stateChanged.connect(self.hide_used_checkbox_state_changed)
        self.hide_incompatible_checkbox.stateChanged.connect(self.hide_incompatible_checkbox_state_changed)
        # 左侧控制按钮
        self.select_all_push_button = QPushButton("Select All")
        self.deselect_all_push_button = QPushButton("Deselect All")
        self.select_all_push_button.clicked.connect(lambda: self.select_all())
        self.deselect_all_push_button.clicked.connect(lambda: self.deselect_all())

        # 底部按钮
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.clicked.connect(self.handle_ok_button_clicked_solt)
        self.cancel_button.clicked.connect(self.reject)

        # 整合布局
        top_layout = QVBoxLayout()
        top_layout.addWidget(self.hide_used_checkbox)
        top_layout.addWidget(self.hide_incompatible_checkbox)

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.select_all_push_button)
        left_layout.addWidget(self.deselect_all_push_button)
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        left_layout.addItem(spacer)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.ok_button)
        bottom_layout.addWidget(self.cancel_button)

        main_layout = QVBoxLayout(self)
        control_layout = QHBoxLayout()

        filter_text = QLineEdit()
        filter_text.setPlaceholderText("<Filter>")
        qvboxlayout = QVBoxLayout()
        qvboxlayout.addWidget(filter_text)
        qvboxlayout.addWidget(self.tableView)
        filter_text.textChanged.connect(self.handle_filter_text_changed_solt)

        control_layout.setContentsMargins(10, 10, 10, 10)
        control_layout.addLayout(left_layout)
        control_layout.addLayout(qvboxlayout)

        main_layout.addLayout(top_layout)
        main_layout.addLayout(control_layout)
        main_layout.addLayout(bottom_layout)
        self.setLayout(main_layout)

        # 调整表格列宽和行高以适应内容
        self.tableView.resizeColumnsToContents()
        self.tableView.resizeRowsToContents()

        # 更新dialog的尺寸以适应表格和其他控件
        self.adjustSize()

        # 设置对话框最小尺寸防止内容显示不全
        self.setMinimumSize(self.sizeHint())

        # 如果您的对话框包含额外的控件，则可能需要自定义计算大小
        additional_height = top_layout.sizeHint().height() + bottom_layout.sizeHint().height()
        additional_width = 20  # 您可能需要调整这个宽度
        self.resize(
            self.tableView.sizeHint().width() + additional_width, self.tableView.sizeHint().height() + additional_height
        )

    def apply_filters(self):
        if hasattr(self, "tableView"):
            filter_model = self.tableView.model()
            if isinstance(
                filter_model, WidgetSortFilterProxyModel
            ):  # WidgetSortFilterProxyModel 是您自定义的代理模型类
                # 设置过滤标志并应用过滤器
                filter_model.set_hide_if_used_checked(True)
                filter_model.set_hide_if_incompatible_checked(True)
                filter_model.init_phase = self.init_phase  # 确保代理模型可以访问
                filter_model.invalidateFilter()  # 重新应用过滤条件，更新视图

    def select_all(self):

        proxy_model = self.tableView.model()
        proxy_model.select_visible_rows(Qt.CheckState.Checked)

    def deselect_all(self):

        proxy_model = self.tableView.model()
        proxy_model.deselect_visible_rows()

    def handle_filter_text_changed_solt(self, text):
        """
        不区分大小写
        """
        self.sort_proxy_model.setFilterFixedString(text)
        self.sort_proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def handle_ok_button_clicked_solt(self):

        # 遍历模型中的所有行
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)  # 第一列是复选框，同时用作键
            if self.model.data(index, Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked:
                # 如果该行被选中，获取第一列的数据作为键
                # key_data = self.model.data(index, Qt.DisplayRole)
                key_data = self.model.data(self.model.index(row, self.key_column_index), Qt.ItemDataRole.DisplayRole)

                # 为其他列创建字典
                row_data_dict = {}
                for col in range(self.key_column_index, self.model.columnCount()):  # 从指定列开始
                    column_header = self.model.headerData(col, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
                    column_data = self.model.data(self.model.index(row, col), Qt.ItemDataRole.DisplayRole)
                    row_data_dict[column_header] = column_data

                # 使用第一列的数据作为键，将其他列的数据作为值
                self.fill_in_param_value_list_dict[key_data] = row_data_dict

        self.accept()  # 以正常状态关闭对话框

    def update_create_container_dialog_show_data_by_enable_module_list(self):
        enable_module_list = self.callback("get_enable_modules")
        self.create_container_dialog_show_data = [
            show_data
            for show_data in self.create_container_dialog_show_data
            if show_data.get("BswModule", {}).get("value") in enable_module_list
        ]

    def update_create_container_dialog_show_data(self):
        if self.init_phase is not None and self.children_list:
            children_set = set(self.children_list)

            for show_data in self.create_container_dialog_show_data:
                init_function = show_data["InitFunctions"]["value"]
                if init_function in children_set:
                    show_data["Already Used In"]["value"] = self.init_phase

    def hide_used_checkbox_state_changed(self, state):
        filter_model = self.tableView.model()
        filter_model.set_hide_if_used_checked(state == Qt.CheckState.Checked)
        filter_model.invalidateFilter()  # 允许复选框状态改变时更新过滤器

    def hide_incompatible_checkbox_state_changed(self, state):
        filter_model = self.tableView.model()
        filter_model.set_hide_if_incompatible_checked(state == Qt.CheckState.Checked)
        filter_model.invalidateFilter()  # 允许复选框状态改变时更新过滤器
