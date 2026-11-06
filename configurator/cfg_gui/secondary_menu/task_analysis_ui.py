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
import os
from typing import Any, List, Optional, Dict
from PySide6.QtWidgets import (
    QTreeView,
    QVBoxLayout,
    QDialog,
    QPushButton,
    QHBoxLayout,
    QHeaderView,
    QFileDialog,
    QToolButton,
    QMenu,
    QTextBrowser,
)
from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex
from PySide6.QtGui import QCursor, QAction, QFont


class TATreeItem:
    """
    The data for Task Analysis UI

    Attrs:
        self.item_data: Data of each item.
            Example: {
                "Entity": "task_name",
                "cet_max": 12,
                "cet_avg": None,
                "type": task
            }
        self.parent_item: Parent node of the item
        self.children: Children node list of the item
        self.editable_attr: Name of editable attributes.
            Example: {"cet_max", "cet_avg"}
    """

    def __init__(self, data, parent=None) -> None:
        """
        Init the tree item

        Attrs:
            data: Dict describes attrs of the item
                Example: {"Entity": "task_name", "cet_max": 12, "cet_avg": None, "type": task}
            parent: Parent node in the tree of this item
        """
        self.item_data: Dict[str, Optional[str]] = data
        self.parent_item = parent
        self.children: List["TATreeItem"] = []
        self.editable_attr = set()

    def child(self, row) -> Optional["TATreeItem"]:
        if 0 <= row < len(self.children):
            return self.children[row]
        else:
            return None

    def parent(self):
        return self.parent_item

    def append_child(self, item: "TATreeItem"):
        self.children.append(item)

    def data(self, attr):
        return self.item_data.get(attr, None)

    def set_data(self, attr, value):
        if attr in self.item_data:
            self.item_data[attr] = value
            return True
        else:
            return False

    def set_editable(self, editable):
        self.editable_attr = editable

    def editable(self, name):
        return name in self.editable_attr

    def row(self):
        if self.parent_item:
            return self.parent_item.children.index(self)
        return 0

    def column_count(self):
        return len(self.item_data)

    def child_count(self):
        return len(self.children)


class TATreeModel(QAbstractItemModel):
    """
    Model of Task analysis ui in MVC arch.

    Attrs:
        self.headers: Headers of the multi column tree, mapping from column index to column name
            Example: {
                0: "Entity",
                1: "cet_max",
                2: "cet_avg",
                3: "type"
            }
        self.r_headers: Headers of the multi column tree, mapping from column name to column index.
            Should be consistent with 'self.headers'
            Example: {
                "Entity": 0,
                "cet_max": 1,
                "cet_avg": 2,
                "type": 3
            }
        self.root_item: The root of the tree
    """

    def __init__(self, headers, data, parent=None) -> None:
        """
        Init the tree model of Task analysis UI

        Attrs:
            headers: Headers of the multi column tree, mapping from column index to column name
                Example: {
                    0: "Entity",
                    1: "cet_max",
                    2: "cet_avg",
                    3: "type"
                }
            data: The dict describe the core/task/isr info
                Example: {
                    "Core0": {
                        "task_name": {
                            "attr": {
                                "cet_max": {
                                    "val": 21,
                                    "editable": True,
                                    "idx": 0
                                },
                                ...
                            }
                        },
                        "isr_name": ...
                    },
                    ...
                }
            parent: Parent widget
        """
        super().__init__(parent)
        self.headers = headers  # Headers mapping from col index to column name
        self.r_headers = {v: k for k, v in self.headers.items()}  # Headers mapping from column name to clo index
        self.root_item: TATreeItem = TATreeItem({})
        self.init_model(data)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return len(self.headers)

    def rowCount(self, parent: QModelIndex = ...) -> int:
        if parent.column() > 0:
            return 0
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()
        return parent_item.child_count()

    def index(self, row: int, column: int, parent: QModelIndex = ...) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item: TATreeItem = parent.internalPointer()

        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        else:
            return QModelIndex()

    def parent(self, index: QModelIndex):
        if not index.isValid():
            return QModelIndex()
        child_item = index.internalPointer()
        parent_item = child_item.parent()
        if parent_item == self.root_item or parent_item is None:
            return QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    def data(self, index: QModelIndex, role: int = ...) -> Any:
        if not index.isValid():
            return None

        item = index.internalPointer()
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return item.data(self.headers[index.column()])
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() != 0:
                return Qt.AlignmentFlag.AlignCenter
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if index.isValid():
            item = index.internalPointer()
            if role == Qt.ItemDataRole.EditRole:
                result = item.set_data(self.headers[index.column()], value)
                return result
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        if index.internalPointer().editable(self.headers[index.column()]):
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable
        else:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        return None

    def init_model(self, data):
        # Build tree
        for core, entity_d in data.items():
            core_item = TATreeItem({"Entity": core}, self.root_item)
            self.root_item.append_child(core_item)

            for entity, info in entity_d.items():
                entity_data = {"Entity": entity}
                editable = set()
                for attr, attr_info in info["attr"].items():
                    entity_data[attr] = attr_info["val"]
                    if attr_info.get("editable", False):
                        editable.add(attr)

                entity_item = TATreeItem(entity_data, core_item)
                entity_item.set_editable(editable)
                core_item.append_child(entity_item)


class TaskAnalysisUI(QDialog):

    def __init__(self, task_info, slot_call_back, parent=None) -> None:
        super().__init__()
        self.slot_call_back = slot_call_back
        self.setWindowTitle("Task Analysis")
        self.resize(800, 600)
        self.setWindowFlags(Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)
        self.init_layout()
        self.render_content(task_info)

    def init_layout(self):
        self.tree_view = QTreeView()

        self.tree_view.setSelectionMode(QTreeView.SelectionMode.ExtendedSelection)

        # Right click menu
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_menu)

        # Import button
        self.import_button = QPushButton("Import trace")
        self.import_button.clicked.connect(self.import_button_slot)

        # Export button
        self.export_button = QToolButton()
        self.export_button.setText("Export as cheddar")
        self.export_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        with_empty_cet = QAction("with empty cet", self)
        with_empty_cet.triggered.connect(self.export_all_core_with_empty_cet_slot)
        without_empty_cet = QAction("without empty cet", self)
        without_empty_cet.triggered.connect(self.export_without_empty_cet_slot)
        self.export_button.addAction(with_empty_cet)
        self.export_button.addAction(without_empty_cet)

        # Schedulability Button
        self.sche_analy_button = QPushButton()
        self.sche_analy_button.setText("Schedulability Analysis")
        self.sche_analy_button.clicked.connect(self.sche_analy_button_slot)

        # Text Browser
        self.text_browser = QTextBrowser(self)
        font = QFont("Consolas", 11)
        self.text_browser.setFont(font)

        # Layout
        self.button_layout = QVBoxLayout()
        self.button_layout.addWidget(self.import_button)
        self.button_layout.addWidget(self.export_button)
        self.button_layout.addWidget(self.sche_analy_button)
        self.func_layout = QHBoxLayout()
        self.func_layout.addWidget(self.tree_view)
        self.func_layout.addLayout(self.button_layout)
        self.setLayout(QVBoxLayout(self))
        self.layout().addLayout(self.func_layout)
        self.layout().addWidget(self.text_browser)

    def gather_columns(self, task_info: dict):
        # Gather columns according to attr in task info
        cols = {0: "Entity"}
        for _, entity_d in task_info.items():
            for _, entity_info in entity_d.items():
                for attr, attr_info in entity_info["attr"].items():
                    cols[attr_info["idx"] + 1] = attr

        return cols

    def render_content(self, task_info: dict):
        # Gather attrs and set columns
        attrs = self.gather_columns(task_info)

        # Init model
        model = TATreeModel(attrs, task_info)
        self.tree_view.setModel(model)
        self.tree_view.setColumnWidth(0, 300)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)

        self.tree_view.expandAll()

    def import_button_slot(self):
        """
        Slot function of the import button.
        Parse the selected trace file and fill result into UI
        """

        def fill_cet(item_info, item_table):

            # Iterate parsed task result and fill in ui
            for task_name, info in item_info.items():
                if task_name in item_table:
                    entity_idx: QModelIndex = item_table[task_name]
                    row = entity_idx.row()

                    cet_avg = info.get("cet_avg", None)  # Time unit is seconds
                    cet_max = info.get("cet_max", None)  # Time unit is seconds

                    cet_avg_col = tree_model.r_headers["cet_avg(ms)"]
                    cet_max_col = tree_model.r_headers["cet_max(ms)"]
                    cet_avg_idx = tree_model.index(row, cet_avg_col, entity_idx.parent())
                    cet_max_idx = tree_model.index(row, cet_max_col, entity_idx.parent())

                    tree_model.setData(cet_avg_idx, cet_avg * 1000)  # Convert time unit from 's' to 'ms'
                    tree_model.setData(cet_max_idx, cet_max * 1000)  # Convert time unit from 's' to 'ms'

        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_path, _ = file_dialog.getOpenFileName(
            self, "Import trace", "", "Trace File(*.log)", options=QFileDialog.Options()
        )

        if not file_path:
            return

        # Create mapping from task/isr name to index
        tree_model: TATreeModel = self.tree_view.model()
        root_index: QModelIndex = QModelIndex()

        # Gather index of task and isr
        task_table = {}
        irq_table = {}
        for core_row in range(tree_model.rowCount(root_index)):
            core_idx: QModelIndex = tree_model.index(core_row, 0, root_index)
            for entity_row in range(tree_model.rowCount(core_idx)):
                entity_idx: QModelIndex = tree_model.index(entity_row, 0, core_idx)
                type_col = tree_model.r_headers["type"]
                entity_type = tree_model.index(entity_row, type_col, core_idx).data(Qt.ItemDataRole.DisplayRole)

                if entity_type == "task":
                    task_table[entity_idx.data(Qt.ItemDataRole.DisplayRole)] = entity_idx
                elif entity_type == "isr":
                    irq_table[entity_idx.data(Qt.ItemDataRole.DisplayRole)] = entity_idx

        # Parse task info from trace file and fill into UI
        def fill_task_irq_cet(args):
            task_info = args[0]
            irq_info = args[1]

            fill_cet(task_info, task_table)
            fill_cet(irq_info, irq_table)

        self.slot_call_back("get_ftrace_task_irq_info", file_path, result_callback=fill_task_irq_cet)

    def sche_analy_button_slot(self):
        """
        Trigger Schedulability Analysis interface
        """
        # Gather all core index according to ui
        model: TATreeModel = self.tree_view.model()
        root_idx = QModelIndex()
        index_l = []
        for core_row in range(model.rowCount(root_idx)):
            core_idx: QModelIndex = model.index(core_row, 0, root_idx)
            index_l.append(core_idx)

        ui_info = self.gather_info_without_empty_cet(index_l)

        def refresh_text_browser(res):
            self.text_browser.setText(res)

        # Generate cheddar file with ui info
        self.slot_call_back("schedulability_analysis", ui_info, result_callback=refresh_text_browser)

    def export_all_core_with_empty_cet_slot(self):
        # Gather all core index according to ui
        model: TATreeModel = self.tree_view.model()
        root_idx = QModelIndex()
        index_l = []
        for core_row in range(model.rowCount(root_idx)):
            core_idx: QModelIndex = model.index(core_row, 0, root_idx)
            index_l.append(core_idx)

        ui_info = self.gather_info_with_empty_cet(index_l)

        self.export_selected_core(ui_info)

    def export_without_empty_cet_slot(self):
        # Gather all core index according to ui
        model: TATreeModel = self.tree_view.model()
        root_idx = QModelIndex()
        index_l = []
        for core_row in range(model.rowCount(root_idx)):
            core_idx: QModelIndex = model.index(core_row, 0, root_idx)
            index_l.append(core_idx)

        ui_info = self.gather_info_without_empty_cet(index_l)

        self.export_selected_core(ui_info)

    def export_selected_core(self, ui_info):
        """
        Export cheddar project file of selected cores
        """
        # Select dir which cheddar files save to
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.DirectoryOnly)
        proj_dir = os.path.dirname(self.slot_call_back("get_prj_path"))
        file_path, _ = file_dialog.getSaveFileName(self, "Export cheddar", proj_dir, "Cheddar file(*.xml)")

        # Generate cheddar file with ui info
        self.slot_call_back("gen_cheddar_with_cet", ui_info, file_path)

    def gather_info_with_empty_cet(self, core_idx_l: List[QModelIndex]):
        """
        Gather ui info of given core, includes entities whose cet is empty
        """
        model: TATreeModel = self.tree_view.model()
        ui_info = {}
        for core_idx in core_idx_l:
            entity_info = {}
            for entity_row in range(model.rowCount(core_idx)):
                entity_idx: QModelIndex = model.index(entity_row, 0, core_idx)
                attr_val = {}
                for attr_col in range(1, model.columnCount()):
                    attr_idx: QModelIndex = model.index(entity_row, attr_col, core_idx)
                    col_name = model.headerData(
                        attr_col, orientation=Qt.Orientation.Horizontal, role=Qt.ItemDataRole.DisplayRole
                    )
                    col_data = attr_idx.data()
                    attr_val[col_name] = col_data

                if attr_val:
                    entity_info[entity_idx.data()] = attr_val

            ui_info[core_idx.data()] = entity_info
        return ui_info

    def gather_info_without_empty_cet(self, core_idx_l: List[QModelIndex]):
        """
        Gather ui info of given core, excludes entities whose cet is empty
        """
        model: TATreeModel = self.tree_view.model()
        ui_info = {}
        for core_idx in core_idx_l:
            entity_info = {}
            for entity_row in range(model.rowCount(core_idx)):
                entity_idx: QModelIndex = model.index(entity_row, 0, core_idx)
                attr_val = {}
                for attr_col in range(1, model.columnCount()):
                    attr_idx: QModelIndex = model.index(entity_row, attr_col, core_idx)
                    col_name = model.headerData(
                        attr_col, orientation=Qt.Orientation.Horizontal, role=Qt.ItemDataRole.DisplayRole
                    )
                    col_data = attr_idx.data()
                    # If cet is empty, ignore the task
                    if (col_name == "cet_amx(ms)" or col_name == "cet_avg(ms)") and not col_data:
                        attr_val = {}
                        break
                    attr_val[col_name] = col_data

                if attr_val:
                    entity_info[entity_idx.data()] = attr_val

            ui_info[core_idx.data()] = entity_info

        return ui_info

    def export_core_with_empty_cet_slot(self):
        index_l = self.tree_view.selectedIndexes()
        index_l = [idx for idx in index_l if idx.column() == 0]  # Only keep 1st column index, which has name of core
        ui_info = self.gather_info_with_empty_cet(index_l)
        self.export_selected_core(ui_info)

    def export_core_without_empty_cet_slot(self):
        index_l = self.tree_view.selectedIndexes()
        index_l = [idx for idx in index_l if idx.column() == 0]  # Only keep 1st column index, which has name of core
        ui_info = self.gather_info_without_empty_cet(index_l)
        self.export_selected_core(ui_info)

    def show_menu(self):
        index_l = self.tree_view.selectedIndexes()
        index_l = [idx for idx in index_l if idx.column() == 0]  # Only keep 1st column index, which has name of core
        item_l: List[TATreeItem] = [idx.internalPointer() for idx in index_l]
        model: TATreeModel = self.tree_view.model()

        # Only core node has menu
        if any(item.parent() is not model.root_item for item in item_l):
            return

        self.tree_menu = QMenu()
        self.tree_menu.addAction("Export cheddar", self.export_core_with_empty_cet_slot)
        self.tree_menu.addAction("Export cheddar without empty cet", self.export_core_without_empty_cet_slot)
        self.tree_menu.popup(QCursor.pos())
