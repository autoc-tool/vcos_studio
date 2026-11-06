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
from PySide6.QtWidgets import QDialog, QTreeWidget, QPushButton, QHBoxLayout, QVBoxLayout, QTreeWidgetItem
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, Signal


class ModuleLevelUi(QDialog):
    level_signal = Signal(list)

    def __init__(self, module_level_list: dict, select_level_func, parent=None):
        super().__init__(parent)
        self.setWindowIcon(QIcon(":/Home.svg"))
        self.select_level_module_list = []
        self.select_item_list = []
        self.setWindowTitle("Select Level Module")
        self.setMinimumSize(384, 472)
        self.setMaximumSize(384, 472)
        self.add_module_listwidget = QTreeWidget(self)
        self.add_module_listwidget.header().hide()
        self.apply_pushbutton = QPushButton("Ok")
        self.module_level_list = module_level_list
        qhboxlayout = QHBoxLayout()
        qhboxlayout.addStretch(0)
        qhboxlayout.addWidget(self.apply_pushbutton)
        qhboxlayout.addStretch(0)

        qvboxlayout = QVBoxLayout(self)
        qvboxlayout.addWidget(self.add_module_listwidget)

        qvboxlayout.addLayout(qhboxlayout)
        for module_name, value in module_level_list.items():
            list_item = QTreeWidgetItem(self.add_module_listwidget)
            list_item.setText(0, module_name)
            list_item.setCheckState(0, Qt.Unchecked)
            for key_name in value:
                # 添加一个子项到顶级项目
                child_item = QTreeWidgetItem(list_item)
                child_item.setText(0, key_name)
        self.add_module_listwidget.itemChanged.connect(self.on_item_changed)
        self.level_signal.connect(select_level_func)
        self.apply_pushbutton.clicked.connect(self.apply_change_slot)

    def apply_change_slot(self):
        for item in self.select_item_list:
            for i in range(item[0].childCount()):
                child = item[0].child(i)
                name = child.text(item[1])
                self.select_level_module_list.append(name)
        self.level_signal.emit(self.select_level_module_list)
        self.close()

    def on_item_changed(self, item, column):
        if item.checkState(column) != Qt.Checked:
            self.select_item_list.pop([item, column])
        else:
            self.select_item_list.append([item, column])
