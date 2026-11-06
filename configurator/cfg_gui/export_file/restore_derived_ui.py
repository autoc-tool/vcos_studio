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
from PySide6.QtWidgets import (
    QDialog,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableView,
    QFrame,
    QLineEdit,
    QHeaderView,
)
from PySide6.QtGui import QFont, QIcon, QGuiApplication, QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, QSize, QSortFilterProxyModel
from basic_func_module.autosar_utils.utils import get_definition_ref

FONT_SIZE = 10
BUTTON_LENGTH = 20
WIDGET_SIZE_FACTOR = 0.4


def button_set_attr(button: QPushButton):
    button.resize(QSize(BUTTON_LENGTH, BUTTON_LENGTH))
    button.setIconSize(button.size())
    button.setStyleSheet(
        """
            QPushButton {background-color: transparent; border: none; color: white;}
            QPushButton:hover {background-color: rgba(180, 180, 255, 0.4);}
            QPushButton:pressed { background-color: rgba(100, 100, 155, 0.4);}
        """
    )


class RestoreDerivedUI(QDialog):

    def __init__(self, slot_call_back, parent=None) -> None:
        super().__init__(parent)
        self.ok_callback: callable = None
        self.slot_call_back: callable = slot_call_back
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint)
        self.init_ui_layout()
        self.init_signal_connect_slot()

    def init_ui_layout(self):
        # 顶端标题与提示信息区域
        title_label = QLabel("Available sub containers")
        title_label.setFont(QFont("Microsoft YaHei", 15))
        self.hint_message_label = QLabel(
            "The sub containers listed below have previously been deleted and can be restored."
        )
        self.hint_message_label.setFont(QFont(title_label.font().family(), FONT_SIZE))
        top_layout = QVBoxLayout()
        top_layout.addWidget(title_label)
        top_layout.addWidget(self.hint_message_label)
        top_layout.setSpacing(10)
        top_layout.setContentsMargins(7, 0, 0, 0)

        # 中间控件区域布局
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("<Filter>")
        self.select_all_button = QPushButton(QIcon(":/check_all.svg"), "", self)
        self.cancel_all_button = QPushButton(QIcon(":cancel_all.svg"), "", self)
        button_set_attr(self.select_all_button)
        button_set_attr(self.cancel_all_button)
        select_button_layout = QVBoxLayout()
        select_button_layout.addWidget(self.select_all_button)
        select_button_layout.addWidget(self.cancel_all_button)
        select_button_layout.addStretch(1)
        select_button_layout.setSpacing(10)
        self.table_view = QTableView(self)
        center_layout = QHBoxLayout()
        center_layout.addLayout(select_button_layout)
        center_layout.addWidget(self.table_view)
        center_layout.setContentsMargins(0, 0, 0, 2)
        center_layout.setSpacing(2)

        # 底部按钮设置
        self.ok_button = QPushButton("OK")
        self.button_cancel = QPushButton("Cancel")
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.ok_button)
        bottom_layout.addWidget(self.button_cancel)
        bottom_layout.setContentsMargins(0, 0, 10, 0)

        # 整体控件布局
        widget_layout = QVBoxLayout(self)
        widget_layout.addLayout(top_layout)
        widget_layout.addWidget(self.get_ui_seperate_line())
        widget_layout.addWidget(self.filter_edit)
        widget_layout.addLayout(center_layout)
        widget_layout.addWidget(self.get_ui_seperate_line())
        widget_layout.addLayout(bottom_layout)
        widget_layout.setContentsMargins(5, 0, 5, 10)
        self.setWindowIcon(QIcon(":/Home.svg"))
        screen_geometry = QGuiApplication.primaryScreen().geometry()
        self.resize(screen_geometry.width() * WIDGET_SIZE_FACTOR, screen_geometry.height() * WIDGET_SIZE_FACTOR)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle("Select sub containers to restore")

    def init_signal_connect_slot(self):
        self.filter_edit.textChanged.connect(self.filter_text_changed_slot)

        self.select_all_button.clicked.connect(lambda: self.update_module_selected_state_slot(Qt.CheckState.Checked))
        self.cancel_all_button.clicked.connect(lambda: self.update_module_selected_state_slot(Qt.CheckState.Unchecked))
        self.ok_button.clicked.connect(self.ok_button_slot)
        self.button_cancel.clicked.connect(self.close)

    def update_module_selected_state_slot(self, state: Qt.CheckState):
        for row in range(self.proxy_model.rowCount()):
            proxy_idx = self.proxy_model.index(row, 0)
            source_idx = self.proxy_model.mapToSource(proxy_idx)
            item = self.table_model.itemFromIndex(source_idx)
            item.setCheckState(state)

    def get_ui_seperate_line(self, direction=QFrame.Shape.HLine) -> QFrame:
        horizon_line = QFrame(self)
        horizon_line.setFrameShape(direction)
        horizon_line.setFrameShadow(QFrame.Shadow.Sunken)
        return horizon_line

    def filter_text_changed_slot(self, text):
        self.proxy_model.setFilterRegularExpression(text)

    def ok_button_slot(self):
        # Gather all selected items on the ui shown now
        selected_container = {}
        for row in range(self.proxy_model.rowCount()):
            idx = self.proxy_model.index(row, 0)
            check_state = idx.data(Qt.ItemDataRole.CheckStateRole)
            if check_state == Qt.CheckState.Checked:
                container_name = idx.data(Qt.ItemDataRole.DisplayRole)
                selected_container[container_name] = self.data[container_name]

        if selected_container and self.ok_callback:
            self.ok_callback(selected_container)

        self.close()

    def build_model(self, restorable: dict):
        self.data = restorable
        self.table_model = QStandardItemModel(0, 2, self)
        self.table_model.setHorizontalHeaderLabels(["Name", "Definition"])

        for name, obj in restorable.items():
            name_item = QStandardItem(name)
            name_item.setCheckable(True)

            definition_item = QStandardItem(get_definition_ref(obj))
            self.table_model.appendRow([name_item, definition_item])

        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)

        h_header = self.table_view.horizontalHeader()
        h_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_view.verticalHeader().setHidden(True)
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSortingEnabled(True)
