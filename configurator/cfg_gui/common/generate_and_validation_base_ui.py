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
from PySide6.QtWidgets import QHeaderView, QWidget, QTreeView, QHBoxLayout, QVBoxLayout, QPushButton, QAbstractItemView
from PySide6.QtGui import QStandardItem, QStandardItemModel, QIcon
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox
from ui_adaptor.ui_interaction.ui_logger import logger
from typing import Callable

TopList = [
    "Base Serivces",
    "Communication",
    "Complex Driver",
    "Diagnostics",
    "I/O",
    "Measurement & Calibration",
    "Memory",
    "Mode Management",
    "Safety",
    "Timing",
]


class GenerateAndValidationBaseUI(QWidget):
    """Support Generation and Validation UI"""

    def __init__(self, module_list: dict = {}, name: str = "", slot_call_back=None):
        super().__init__()
        self.codegen_or_validation_module_list = module_list
        self.generation_or_validation_enabled_list = []
        self.slot_call_back: Callable = slot_call_back
        self.setWindowTitle(name)
        self.setWindowIcon(QIcon(":/Home.svg"))
        self.resize(600, 800)
        self.setWindowModality(Qt.ApplicationModal)
        self.treeview = QTreeView(self)
        self.model_table = QStandardItemModel(0, 4, self.treeview)
        self.model_table.setHorizontalHeaderLabels(["Generation Step", "Calculation", "Validation", ""])
        self.treeview.setModel(self.model_table)
        self.treeview.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.treeview.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.rootItem = self.model_table.invisibleRootItem()
        self.child_node = QStandardItem("VCOS Configurator Code Generation")
        self.child_node.setData("VCOS Configurator Code Generation")
        self.child_node.setCheckable(True)
        self.child_node.setData(Qt.Unchecked, Qt.CheckStateRole)
        self.rootItem.appendRow(self.child_node)
        self.module_list = []
        self.module_dict = {}

        self.close_cancel_button = QPushButton("Close", self)
        self.change_project_settings_button = QPushButton("Change Project Settings", self)
        self.change_project_settings_button.setEnabled(False)
        self.validation_generate_button = QPushButton(name, self)

        self.close_cancel_button.clicked.connect(self.close_cancel_button_slot)
        self.change_project_settings_button.clicked.connect(self.change_project_settings_button_slot)
        self.validation_generate_button.clicked.connect(self.validation_generate_button_slot)
        self.model_table.itemChanged.connect(self.on_check_box_changed)

        self.hlayout1 = QHBoxLayout()
        self.hlayout1.addStretch(2)
        qlayout = QVBoxLayout()
        qlayout.addWidget(self.treeview)
        qlayout.addLayout(self.hlayout1)

        self.setLayout(qlayout)
        self.set_module_init()
        self.treeview_parent_init(TopList)

    def combobox_add(self, item: QVBoxLayout = None):
        if item:
            self.hlayout1.addLayout(item)
            self.hlayout1.addStretch(16)
            self.button_add()

    def button_add(self):
        self.hlayout1.addWidget(self.change_project_settings_button)
        self.hlayout1.addWidget(self.validation_generate_button)
        self.validation_generate_button.setToolTip(f"Click Here to {self.windowTitle()}")
        self.hlayout1.addWidget(self.close_cancel_button)
        self.close_cancel_button.setToolTip("Click Here to Close")

    def set_module_init(self):
        self.VCOS_CONFIGURATOR_MODULE_RELATED_LIST: dict = {}
        self.VCOS_CONFIGURATOR_MODE_GENERATION_LIST: dict = {}
        for module, value in self.codegen_or_validation_module_list.items():
            self.VCOS_CONFIGURATOR_MODULE_RELATED_LIST.update({module: value["dependency_list"]})
            self.VCOS_CONFIGURATOR_MODE_GENERATION_LIST.update({module: value["group"]})
            self.module_list.append(module)

    def update_ui_module_list(self, module_list: dict, enabled_generate_module_list=[]):
        temp_list = []
        self.module_dict = module_list
        for module, value in module_list.items():
            if module in self.module_list:
                continue
            else:
                value["module_name"]
                self.VCOS_CONFIGURATOR_MODULE_RELATED_LIST.update({module: value["dependency_list"]})
                self.VCOS_CONFIGURATOR_MODE_GENERATION_LIST.update({module: value["group"]})
                self.module_list.append(module)
        for module in self.module_list:
            if module not in module_list:
                self.VCOS_CONFIGURATOR_MODULE_RELATED_LIST.pop(module)
                self.VCOS_CONFIGURATOR_MODE_GENERATION_LIST.pop(module)
            else:
                temp_list.append(module)
        self.module_list = sorted(temp_list)
        self.generation_or_validation_enabled_list = enabled_generate_module_list
        self.update_treeview()

    def get_check_module_list(self, module_list, generation_enabled_list):
        module_list_to_check = []
        for module in module_list:
            if module in generation_enabled_list:
                module_list_to_check.append(module)
            else:
                continue
        return module_list_to_check

    def close_cancel_button_slot(self):
        pass

    def change_project_settings_button_slot(self):
        pass

    def validation_generate_button_slot(self):
        pass

    def treeview_parent_init(self, module_list):
        for module_name in module_list:
            newItem = QStandardItem(module_name)
            newItem.setCheckable(True)
            newItem.setData(Qt.Unchecked, Qt.CheckStateRole)
            self.child_node.appendRow(newItem)

    def set_module_check_state(self):
        module_check_list = self.get_check_module_list(self.module_list, self.generation_or_validation_enabled_list)
        for name in TopList:
            items = self.model_table.findItems(name, Qt.MatchContains | Qt.MatchRecursive)
            if items[0].rowCount() < 1:
                continue
            for module_name in module_check_list:
                for i in range(items[0].rowCount()):
                    child_item = items[0].child(i)
                    if child_item.text() == module_name:
                        child_item.setCheckState(Qt.Checked)

    def update_treeview(self):
        self.add_enabled_module_list_to_treeview()
        self.set_module_check_state()
        self.treeview.expandAll()

    def add_enabled_module_list_to_treeview(self):
        self.add_module_in_ui(self.module_list)
        self.remove_module_in_ui(self.child_node, self.module_list)

    def add_module_in_ui(self, module_list):
        keys = []
        for module_name in module_list:
            for key, value in self.VCOS_CONFIGURATOR_MODE_GENERATION_LIST.items():
                if module_name == key:
                    keys = value
                    break
            if len(keys) < 1:
                continue
            if self.model_table.findItems(module_name, Qt.MatchExactly | Qt.MatchRecursive):
                continue
            for key_item in keys:
                item = self.model_table.findItems(key_item, Qt.MatchExactly | Qt.MatchRecursive)
                child_node2 = QStandardItem(module_name)
                child_node2.setCheckable(True)
                child_node2.setData(Qt.Unchecked, Qt.CheckStateRole)
                child_node2.setData(module_name)
                item[0].appendRow(child_node2)

    def remove_module_in_ui(self, root_node: QStandardItem, module_list):
        """删除模块在UI界面同步删除:连续、单、间隔、跨group均支持"""
        node_count = root_node.rowCount()
        bias = int(0)  # 记录childnode偏差
        if node_count == 0:
            return
        for row in range(node_count):
            update_row = row + bias
            node_item: QStandardItem = root_node.child(update_row)
            if not isinstance(node_item, QStandardItem):
                continue
            item_text = node_item.text()
            self.remove_module_in_ui(node_item, module_list)
            if item_text not in TopList and item_text not in module_list:
                root_node.removeRow(update_row)
                bias -= 1

    def on_check_box_changed(self, item: QStandardItem):
        if item.text() == "VCOS Configurator Code Generation":
            if item.checkState() == Qt.Unchecked:
                for i in range(item.rowCount()):
                    child_item = item.child(i)
                    child_item.setData(Qt.Unchecked, Qt.CheckStateRole)
                    self.set_child_item_check_status(child_item, Qt.Unchecked)
            elif item.checkState() == Qt.Checked:
                for i in range(item.rowCount()):
                    child_item = item.child(i)
                    child_item.setData(Qt.Checked, Qt.CheckStateRole)
                    self.set_child_item_check_status(child_item, Qt.Checked)

        if item.text() in TopList:
            if item.checkState() == Qt.Unchecked:
                self.set_child_item_check_status(item, Qt.Unchecked)
            elif item.checkState() == Qt.Checked:
                # 打印第一个根项的所有子项
                self.set_child_item_check_status(item, Qt.Checked)

        if item.text() in self.module_list:
            if item.checkState() == Qt.Unchecked:
                # 取消一个模块的同时，取消其关联模块的勾选
                self.set_child_item_check_status(item, Qt.Unchecked)
            elif item.checkState() == Qt.Checked:
                ret, mcal_module_cmd_line_tool_path = self.slot_call_back(
                    "check_mcal_module_codegen_cmd_line_tool_exist", item.text()
                )
                # 1. 如果不是mcal模块,返回True
                # 2. 如果是mcal模块,但代码命令行生成工具不存在,返回False
                # 3. 如果是mcal模块,且代码命令行生成工具存在,返回命令行工具的绝对路径
                if ret is False:
                    # 这里只需要关心返回值为False的情况，
                    # 需要弹窗提醒用户当前没有该类型芯片mcal模块代码的命令行生成工具，需要安装，并去除勾选
                    item.model().blockSignals(True)
                    message = (
                        "{module_name} codegen cmd line tools({mcal_module_cmd_line_tool_path}) "
                        "is not exist, please confirm"
                    ).format(module_name=item.text(), mcal_module_cmd_line_tool_path=mcal_module_cmd_line_tool_path)
                    self.show_message_box(message)
                    logger.error(message)
                    item.setCheckState(Qt.Unchecked)  # 去除勾选
                    item.model().blockSignals(False)
                    return
                # item.model().blockSignals(False)
                self.set_child_item_check_status(item, Qt.Checked)

    def show_message_box(self, message):
        # 创建QMessageBox实例
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setWindowTitle("Error")
        msgBox.setText(message)
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.setDefaultButton(QMessageBox.Ok)
        msgBox.exec()

    def set_validation_status_to_project_file(self):
        validation_enabled_list = []
        for name in TopList:
            items = self.model_table.findItems(name, Qt.MatchContains | Qt.MatchRecursive)
            if items[0].rowCount() < 1:
                continue
            for i in range(items[0].rowCount()):
                child_item = items[0].child(i)
                if child_item.checkState() == Qt.Checked:
                    validation_enabled_list.append(child_item.text())
        validation_enabled_list.sort()
        validation_enabled_list = {k: self.module_dict[k] for k in validation_enabled_list if k in self.module_dict}
        return validation_enabled_list

    def set_child_item_check_status(self, item: QStandardItem, status):
        if item is None:
            return
        if item.rowCount() < 1:
            self.set_child_item_check_status_related_module(item, status)
        else:
            for i in range(item.rowCount()):
                child_item = item.child(i)
                child_item.setData(status, Qt.CheckStateRole)
                self.set_child_item_check_status_related_module(child_item, status)

    def set_child_item_check_status_related_module(self, item: QStandardItem, status):
        target_module = item.text()
        all_items = self.model_table.findItems(target_module, Qt.MatchExactly | Qt.MatchRecursive)
        related_modules = []
        # 当前模块的重复勾选
        for item in all_items:
            item.setData(status, Qt.CheckStateRole)
        # 关联模块的勾选
        if status == Qt.Checked:
            if target_module in self.VCOS_CONFIGURATOR_MODULE_RELATED_LIST.keys():
                related_modules = self.VCOS_CONFIGURATOR_MODULE_RELATED_LIST[target_module]

            if related_modules != []:
                for module in related_modules:
                    all_items = self.model_table.findItems(module, Qt.MatchExactly | Qt.MatchRecursive)
                    for item in all_items:
                        item.setData(status, Qt.CheckStateRole)
        else:
            for key, list in self.VCOS_CONFIGURATOR_MODULE_RELATED_LIST.items():
                if target_module in list:
                    items = self.model_table.findItems(key, Qt.MatchExactly | Qt.MatchRecursive)
                    if len(items) == 0:
                        continue
                    items[0].setData(status, Qt.CheckStateRole)
