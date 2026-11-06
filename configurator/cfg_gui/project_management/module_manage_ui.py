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
from cfg_gui.bsw_editor.overview_ui import OverViewUI
from typing import Callable
from PySide6.QtWidgets import (
    QDialog,
    QTableWidget,
    QCheckBox,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QTableWidgetItem,
    QLineEdit,
)
from PySide6.QtGui import QIcon, QValidator, QRegularExpressionValidator, QWheelEvent
from ui_adaptor.ui_interaction.ui_logger import logger
from PySide6.QtGui import QCloseEvent
from PySide6.QtCore import Qt, QRegularExpression
from cfg_gui.project_management.module_level_ui import ModuleLevelUi


class NumericLineEdit(QLineEdit):
    re = QRegularExpression("[1-9]")

    def __init__(self) -> None:
        super().__init__()
        self._validator = QRegularExpressionValidator(self.re, self)
        self.setValidator(self._validator)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self.hasFocus():
            return super().wheelEvent(event)
        current_value = int(self.placeholderText())
        if event.angleDelta().y() > 0:
            self.setText(str(current_value + 1))
        else:
            self.setText(str(current_value - 1))
        state, _, _ = self._validator.validate(self.placeholderText(), 0)
        if state != QValidator.State.Acceptable:
            self.setText(str(current_value))
        event.accept()


class ModuleManageUi(QDialog):

    def __init__(
        self,
        all_module_list: list,
        added_module_dict: dict,
        level_module_list: dict,
        overview_ui,
        call_back_dict,
        parent=None,
    ):
        super().__init__(parent)
        self.init_ui()
        self.all_module_list = all_module_list
        self.added_module_dict = added_module_dict
        self.overview_ui: OverViewUI = overview_ui
        self.slot_call_back: Callable = call_back_dict
        self.level_module_list = level_module_list
        self.select_module_dict = {}
        self.module_num_dict = {}
        self.added_module_set = {v["module_name"] for v in added_module_dict.values() if v["multiple_instance"] == 1}
        self.update_table_widget(self.all_module_list)
        self.init_slot()

    def init_slot(self):
        # Connect slot after setting list check state, to avoid influenced by slot
        self.add_module_tablewidget.itemChanged.connect(self.on_item_changed)
        self.select_all.stateChanged.connect(self.checkbox_state_changed)
        # self.module_level_pushbutton.clicked.connect(self.module_level_pushbutton_slot)
        self.apply_pushbutton.clicked.connect(self.apply_change_slot)
        self.filter_text_edit.textChanged.connect(self.filter_text_changed_slot)

    def init_ui(self):
        self.setWindowIcon(QIcon(":/Home.svg"))
        self.setWindowTitle("Add Module")
        self.setMinimumSize(384, 472)
        self.setMaximumSize(384, 472)
        self.filter_text_edit = QLineEdit(self)
        self.filter_text_edit.setPlaceholderText("<Filter>")
        self.add_module_tablewidget = QTableWidget(self)
        self.add_module_tablewidget.setColumnCount(2)
        self.add_module_tablewidget.verticalHeader().hide()
        self.add_module_tablewidget.horizontalHeader().hide()
        self.select_all = QCheckBox("Select All")
        self.apply_pushbutton = QPushButton("Ok")
        # self.module_level_pushbutton = QPushButton("Select Level")
        qhboxlayout = QHBoxLayout()
        qhboxlayout.addStretch(0)
        qhboxlayout.addWidget(self.select_all)
        qhboxlayout.addStretch(1)
        qhboxlayout.addWidget(self.apply_pushbutton)
        # qhboxlayout.addStretch(1)
        # qhboxlayout.addWidget(self.module_level_pushbutton)
        qhboxlayout.addStretch(0)
        qvboxlayout = QVBoxLayout(self)
        qvboxlayout.addWidget(self.add_module_tablewidget)
        qvboxlayout.addWidget(self.filter_text_edit)
        qvboxlayout.addLayout(qhboxlayout)

    def update_table_widget(self, all_module_list):
        self.add_module_tablewidget.clear()
        self.add_module_tablewidget.setRowCount(len(all_module_list))
        for row, module_name in enumerate(all_module_list):
            table_item = QTableWidgetItem(module_name)
            table_item.setIcon(QIcon(":/plugin.svg"))
            line_edit = NumericLineEdit()
            flags = table_item.flags() ^ Qt.ItemFlag.ItemIsEditable
            if module_name in self.added_module_set:
                flags ^= Qt.ItemFlag.ItemIsEnabled
                check_state = Qt.CheckState.Checked
                is_enabled = False
            else:
                flags |= Qt.ItemFlag.ItemIsEnabled
                check_state = Qt.CheckState.Unchecked
                is_enabled = True
            if module_name in self.select_module_dict:
                check_state = Qt.CheckState.Checked
            table_item.setFlags(flags)
            table_item.setCheckState(check_state)
            line_edit.setEnabled(is_enabled)
            line_edit.setPlaceholderText(self.module_num_dict.get(module_name, "1"))
            line_edit.textChanged.connect(lambda text, row=row: self.on_line_edit_changed(row, text))
            self.add_module_tablewidget.setItem(row, 0, table_item)
            self.add_module_tablewidget.setCellWidget(row, 1, line_edit)
        self.add_module_tablewidget.resizeColumnsToContents()

    def filter_text_changed_slot(self, filter_text: str):
        all_module_list = [name for name in self.all_module_list if filter_text.lower() in name.lower()]
        self.update_table_widget(all_module_list)

    def on_item_changed(self, item: QTableWidgetItem):
        if item.checkState() == Qt.CheckState.Checked:
            self.select_module_dict[item.text()] = None
            dependence_list = self.slot_call_back("get_module_dependence", item.text())
            for module in dependence_list:
                self.select_module_dict[module] = None
                sub_item = self.add_module_tablewidget.findItems(module, Qt.MatchFlag.MatchExactly)
                if len(sub_item) == 0:
                    continue
                self.set_checked(sub_item[0])
        else:
            self.select_module_dict.pop(item.text(), None)
            dependence_by_list = self.slot_call_back("get_module_dependence_by", item.text())
            for module in dependence_by_list:
                self.select_module_dict.pop(module, None)
                sub_item = self.add_module_tablewidget.findItems(module, Qt.MatchFlag.MatchExactly)
                if len(sub_item) == 0:
                    continue
                self.set_checked(sub_item[0], Qt.CheckState.Unchecked)

    def on_line_edit_changed(self, row: int, text: str):
        item = self.add_module_tablewidget.item(row, 0)
        self.module_num_dict[item.text()] = text
        lien_edit: QLineEdit = self.add_module_tablewidget.cellWidget(row, 1)
        lien_edit.blockSignals(True)
        lien_edit.clear()
        lien_edit.blockSignals(False)
        lien_edit.setPlaceholderText(text)

    def closeEvent(self, event: QCloseEvent):
        self.slot_call_back("close_modules_ui")

    def apply_change_slot(self):
        selected_module = []
        for module_name in self.select_module_dict.keys():
            num = int(self.module_num_dict.get(module_name, "1"))
            selected_module.extend([module_name] * num)

        def _update_module_overview(args):
            logger.info("Finish module change attemption, try update overview")
            self.overview_ui.update_overview(args)
            self.close()

        self.slot_call_back("apply_modules_change", selected_module, result_callback=_update_module_overview)

    def checkbox_state_changed(self, state):
        for row in range(self.add_module_tablewidget.rowCount()):
            item = self.add_module_tablewidget.item(row, 0)
            self.set_checked(item, state)

    def module_level_pushbutton_slot(self):
        self.hide()
        self.module_level_ui = ModuleLevelUi(self.level_module_list, self.apply_level_module, self.parent())
        self.module_level_ui.open()
        self.module_level_ui.finished.connect(self.show)

    def apply_level_module(self, list):
        for name in list:
            sub_item = self.add_module_tablewidget.findItems(name, Qt.MatchFlag.MatchExactly)
            if len(sub_item) == 0:
                continue
            self.set_checked(sub_item[0])

    def set_checked(self, item: QTableWidgetItem, checked=Qt.CheckState.Checked):
        if item.flags() & Qt.ItemFlag.ItemIsEnabled == Qt.ItemFlag.ItemIsEnabled:
            item.setCheckState(Qt.CheckState(checked))
