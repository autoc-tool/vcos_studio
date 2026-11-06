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
from itertools import chain
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QListWidget,
    QVBoxLayout,
    QLabel,
    QListWidgetItem,
    QPushButton,
    QHBoxLayout,
    QCheckBox,
)
from func_module.module_management.arxml_handler.config_comparator import ConfigComparator


class MergeEcucUi(QDialog):

    def __init__(self, comparator: ConfigComparator, slot_callback: callable = None) -> None:
        super(MergeEcucUi, self).__init__()
        self.comparator = comparator
        self.init_ui()
        self.slot_callback = slot_callback
        diff_strings = self.comparator.all_diff_string()
        self.fill_list(diff_strings)
        self.exec()

    def init_ui(self):
        self.setWindowIcon(QIcon(":/Home.svg"))
        self.setWindowTitle("Handle diff")
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.init_layout()

    def init_layout(self):
        v_layout = QVBoxLayout()
        self.setLayout(v_layout)
        self.added_container_list = QListWidget(self)
        v_layout.addWidget(QLabel("Added container"))
        v_layout.addWidget(self.added_container_list)
        self.added_param_ref_list = QListWidget(self)
        v_layout.addWidget(QLabel("Added param/ref"))
        v_layout.addWidget(self.added_param_ref_list)
        self.deleted_container_list = QListWidget(self)
        v_layout.addWidget(QLabel("Deleted container"))
        v_layout.addWidget(self.deleted_container_list)
        self.deleted_param_ref_list = QListWidget(self)
        v_layout.addWidget(QLabel("Deleted param/ref"))
        v_layout.addWidget(self.deleted_param_ref_list)
        self.modified_config_list = QListWidget(self)
        v_layout.addWidget(QLabel("Modified param/ref"))
        v_layout.addWidget(self.modified_config_list)
        h_layout = QHBoxLayout()
        self.sel_all_check_box = QCheckBox("Select all")
        self.sel_all_check_box.setCheckState(Qt.CheckState.Checked)
        self.sel_all_check_box.stateChanged.connect(self.sel_all_changed_slot)
        h_layout.addWidget(self.sel_all_check_box)
        self.apply_button = QPushButton("Apply", self)
        self.apply_button.clicked.connect(self.apply_button_clicked_slot)
        h_layout.addWidget(self.apply_button)
        v_layout.addLayout(h_layout)

    def fill_list(self, diff_strings):
        for diff in diff_strings["added_container"]:
            item = QListWidgetItem(diff)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.added_container_list.addItem(item)

        for diff in chain(diff_strings["added_param"], diff_strings["added_ref"]):
            item = QListWidgetItem(diff)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.added_param_ref_list.addItem(item)

        for diff in diff_strings["deleted_container"]:
            item = QListWidgetItem(diff)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.deleted_container_list.addItem(item)

        for diff in chain(diff_strings["deleted_param"], diff_strings["deleted_ref"]):
            item = QListWidgetItem(diff)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.deleted_param_ref_list.addItem(item)

        for diff in diff_strings["modified_config"]:
            item = QListWidgetItem(diff)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.modified_config_list.addItem(item)

    def keyPressEvent(self, a0: QKeyEvent) -> None:
        if a0.key() == Qt.Key.Key_Escape:
            pass  # ignore esc
        else:
            return super().keyPressEvent(a0)

    def apply_button_clicked_slot(self):
        disabled_change = {
            "added_container": [],
            "added_param_ref": [],
            "deleted_container": [],
            "deleted_param_ref": [],
            "modified_config": [],
        }
        for idx in range(self.added_container_list.count()):
            item = self.added_container_list.item(idx)
            if item.checkState() == Qt.CheckState.Unchecked:
                disabled_change["added_container"].append(item.text())
        for idx in range(self.added_param_ref_list.count()):
            item = self.added_param_ref_list.item(idx)
            if item.checkState() == Qt.CheckState.Unchecked:
                disabled_change["added_param_ref"].append(item.text())
        for idx in range(self.deleted_container_list.count()):
            item = self.deleted_container_list.item(idx)
            if item.checkState() == Qt.CheckState.Unchecked:
                disabled_change["deleted_container"].append(item.text())
        for idx in range(self.deleted_param_ref_list.count()):
            item = self.deleted_param_ref_list.item(idx)
            if item.checkState() == Qt.CheckState.Unchecked:
                disabled_change["deleted_param_ref"].append(item.text())
        for idx in range(self.modified_config_list.count()):
            item = self.modified_config_list.item(idx)
            if item.checkState() == Qt.CheckState.Unchecked:
                disabled_change["modified_config"].append(item.text())

        if callable(self.slot_callback):
            self.slot_callback("merge_ecuc", self.comparator, disabled_change, finished_callback=self.close)
        else:
            self.comparator.merge_ecuc(disabled_change)
            self.close()

    def set_all_item_selector(self, state: Qt.CheckState):
        for idx in range(self.added_container_list.count()):
            item = self.added_container_list.item(idx)
            item.setCheckState(state)
        for idx in range(self.added_param_ref_list.count()):
            item = self.added_param_ref_list.item(idx)
            item.setCheckState(state)
        for idx in range(self.deleted_container_list.count()):
            item = self.deleted_container_list.item(idx)
            item.setCheckState(state)
        for idx in range(self.deleted_param_ref_list.count()):
            item = self.deleted_param_ref_list.item(idx)
            item.setCheckState(state)
        for idx in range(self.modified_config_list.count()):
            item = self.modified_config_list.item(idx)
            item.setCheckState(state)

    def sel_all_changed_slot(self):
        self.sel_all_check_box: QCheckBox
        if self.sel_all_check_box.checkState() == Qt.CheckState.Checked:
            self.set_all_item_selector(Qt.CheckState.Checked)
        else:
            self.set_all_item_selector(Qt.CheckState.Unchecked)
        pass
