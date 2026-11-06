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
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QIcon, QStandardItem, QStandardItemModel
from ui_adaptor.ui_interaction.ui_logger import logger


class SWCGeneratorWidget(QWidget):

    def __init__(self, swc_list, cbk, status=True):
        super().__init__()
        self.setWindowIcon(QIcon(":/Home.svg"))
        self.callback = cbk
        self.swc_app_list = swc_list
        self.setWindowTitle("SWC Generator")
        self.resize(600, 800)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.treeview = QTreeView()
        self.model_table = QStandardItemModel(0, 4)
        headers: list = ["Application SWC Generation Step", "Calculation", "Validation", ""]
        self.model_table.setHorizontalHeaderLabels(headers)
        self.header = self.treeview.header()
        self.header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.treeview.setModel(self.model_table)
        self.treeview.setHeader(self.header)
        self.treeview.expanded.connect(lambda index: self.update_tree_scroll_area(index))
        self.treeview.collapsed.connect(lambda index: self.update_tree_scroll_area(index))
        self.treeview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.rootItem = self.model_table.invisibleRootItem()
        self.child_node = QStandardItem("VCOS Configurator SWC Code Generation")
        self.child_node.setData(self.child_node.text(), Qt.ItemDataRole.DisplayRole)
        self.child_node.setCheckable(True)
        self.child_node.setData(Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
        self.rootItem.appendRow(self.child_node)

        self.generate_swc_file_path = QLineEdit("Generate")
        self.swc_generate_save_button = QPushButton("Generate")
        self.swc_generate_save_button.setEnabled(status)

        self.swc_generate_save_button.clicked.connect(self.swc_generate_save_button_slot)
        self.model_table.itemChanged.connect(self.on_check_box_changed)

        hlayout1 = QHBoxLayout()
        hlayout1.addStretch(2)
        hlayout1.addWidget(self.swc_generate_save_button)
        qlayout = QVBoxLayout()
        qlayout.addWidget(self.treeview)
        qlayout.addLayout(hlayout1)
        self.setLayout(qlayout)

        self.treeview_parent_init(self.swc_app_list)

    def update_tree_scroll_area(self, index: QModelIndex):
        self.treeview.resizeColumnToContents(index.column())

    def close_cancel_button_slot(self):
        self.close()
        return

    def swc_generate_save_button_slot(self):
        swc_list = self.save_and_update_swc_app()
        self.callback("swc_generator_action", swc_list, result_callback=self.finish_code_gen)

    def finish_code_gen(self, result):
        if result:
            logger.ui_info("The generation of the SWCs succeeded!")
        else:
            logger.ui_info("The generation of the SWCs failed!")
        self.close()

    # Update the list of application swcs' for generation
    def save_and_update_swc_app(self):
        if self.child_node is None or self.child_node.rowCount() < 1:
            logger.warning("No child item exists")
            return

        for i in range(self.child_node.rowCount()):
            child_item = self.child_node.child(i)
            swc_object = child_item.text()
            if child_item.checkState() == Qt.CheckState.Checked:
                if swc_object not in self.swc_app_list:
                    self.swc_app_list.append(swc_object)
                else:
                    continue
            elif child_item.checkState() == Qt.CheckState.Unchecked:
                if swc_object in self.swc_app_list:
                    idx = self.swc_app_list.index(swc_object)
                    del self.swc_app_list[idx]
                else:
                    continue
        return self.swc_app_list

    def sort_func(self, element):
        return (element.lower(), len(element))

    def treeview_parent_init(self, swc_list):
        swc_list = sorted(swc_list, key=self.sort_func)
        for swc in swc_list:
            if self.has_item_with_text(swc):
                continue
            newItem = QStandardItem(swc)
            newItem.setCheckable(True)
            newItem.setData(Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
            self.child_node.appendRow(newItem)
        self.treeview.expandAll()

    def has_item_with_text(self, text):
        for row in range(self.child_node.rowCount()):
            child_item = self.child_node.child(row)
            if child_item.text() == text:
                return True
        return False

    def on_check_box_changed(self, item: QStandardItem):
        if item.text() == "VCOS Configurator SWC Code Generation":
            if item.checkState() == Qt.CheckState.Unchecked:
                for i in range(item.rowCount()):
                    child_item = item.child(i)
                    child_item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
                    self.set_child_item_check_status(child_item, Qt.CheckState.Unchecked)
            elif item.checkState() == Qt.CheckState.Checked:
                for i in range(item.rowCount()):
                    child_item = item.child(i)
                    child_item.setData(Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
                    self.set_child_item_check_status(child_item, Qt.CheckState.Checked)

        if item.text() in self.swc_app_list:
            if item.checkState() == Qt.CheckState.Unchecked:
                self.set_child_item_check_status(item, Qt.CheckState.Unchecked)
            elif item.checkState() == Qt.CheckState.Checked:
                self.set_child_item_check_status(item, Qt.CheckState.Checked)

    def set_child_item_check_status(self, item: QStandardItem, status):
        if item is None or item.rowCount() < 1:
            return
        for i in range(item.rowCount()):
            child_item = item.child(i)
            child_item.setData(status, Qt.ItemDataRole.CheckStateRole)
        self.treeview.expandAll()
