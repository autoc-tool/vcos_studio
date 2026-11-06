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
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QWidget,
    QStyledItemDelegate,
    QLineEdit,
    QVBoxLayout,
    QTableWidget,
    QHeaderView,
    QTableWidgetItem,
)
from ui_adaptor.ui_interaction.ui_logger import logger


class AlarmOffsetDelegate(QStyledItemDelegate):

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        validator = QDoubleValidator(self)
        validator.setBottom(0)
        editor.setValidator(validator)
        return editor


class SecRuntimeSystemOsConfigurationAlarmOffsetWidget(QWidget):

    def __init__(self, main_window, show_data_dict, task_ref, callback) -> None:
        super().__init__()
        self.main_window = main_window
        self.show_data_dict = show_data_dict
        self.task_ref = task_ref
        self.callback = callback
        self.init_ui()

    def init_ui(self):
        alarm_offset_infos = self.get_alarm_offset_infos()
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.table = QTableWidget(self)
        self.table.setSortingEnabled(True)
        self.table.setRowCount(len(alarm_offset_infos))
        self.table.setColumnCount(2)
        self.table.setItemDelegateForColumn(1, AlarmOffsetDelegate())
        self.table.setHorizontalHeaderLabels(["Alarm Name", "Offset(ms)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        for i, alarm_name in enumerate(alarm_offset_infos):
            item = QTableWidgetItem(alarm_name)
            item.setFlags(item.flags() & ~Qt.ItemFlags(Qt.ItemFlag.ItemIsEditable))
            self.table.setItem(i, 0, item)
            self.table.setItem(i, 1, QTableWidgetItem(str(alarm_offset_infos[alarm_name])))
        self.table.itemChanged.connect(self.set_alarm_offset_infos)
        layout.addWidget(self.table)

    def set_alarm_offset_infos(self, item: QTableWidgetItem):
        alarm_name = self.table.item(item.row(), 0).text()
        mapping_refs = [v["ref"] for v in self.used_os_alarm_infos if v["alarm_ref"].endswith(alarm_name)]
        logger.debug(f"set_alarm_offset_infos alarm_name: {alarm_name}, mapping_refs: {mapping_refs}")
        res = self.callback("set_used_alarm_offset_by_mapping_ref", mapping_refs, item.text())
        logger.debug(f"set_alarm_offset_infos result: {res}")

    def get_alarm_offset_infos(self):
        task_ref = ""
        for v in self.show_data_dict.values():
            for vv in v:
                if vv["label_name"] == "ShortName":
                    task_ref = vv["ecuc_path"]
                    break
        logger.debug(f"get_alarm_offset_infos task_ref: {task_ref}")
        self.used_os_alarm_infos = self.callback("get_used_os_alarm_infos_by_task_ref", task_ref)
        logger.debug(f"get_alarm_offset_infos used_os_alarm_infos: {self.used_os_alarm_infos}")
        used_os_alarm_info_dict = {}
        for used_os_alarm_info in self.used_os_alarm_infos:
            alarm_name = used_os_alarm_info["alarm_ref"].split("/")[-1]
            offset = used_os_alarm_info["offset"]
            if alarm_name in used_os_alarm_info_dict and used_os_alarm_info_dict[alarm_name] != offset:
                used_os_alarm_info_dict[alarm_name] += f", {offset}"
            else:
                used_os_alarm_info_dict[alarm_name] = str(offset)
        logger.debug(f"get_alarm_offset_infos used_os_alarm_info_dict: {used_os_alarm_info_dict}")
        return used_os_alarm_info_dict
