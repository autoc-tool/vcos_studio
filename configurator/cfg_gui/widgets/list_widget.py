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
from basic_func_module.autosar_utils import utils
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QLabel,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QSpacerItem,
    QSizePolicy,
)

VALID_REF_TARGET_PATH_MAP = {"BswMArgumentRef": "/ActiveEcuC/BswM/BswMConfig/BswMArbitration"}


class ArgReferenceWidget(QVBoxLayout):
    """
    Handle same DEFINITION-REF of ECUC-REFERENCE-VALUE.
    """

    def __init__(self, reference_param_list, definition_ref_name, ecuc_config):
        super().__init__()
        self.ecuc_config = ecuc_config
        self.reference_param_list = reference_param_list
        self.definition_ref_name = definition_ref_name
        self.ref_list: QListWidget = QListWidget()
        self.push_buttton_add = QPushButton()
        self.push_buttton_add.setIcon(QIcon(":/add.svg"))
        self.push_buttton_add.setToolTip("Add")
        self.push_buttton_remove = QPushButton()
        self.push_buttton_remove.setIcon(QIcon(":/not_ok.svg"))
        self.push_buttton_remove.setToolTip("Remove")
        self.init_ref_target_window()
        self.qhboxlayout = QHBoxLayout()
        self.qvboxlayout = QVBoxLayout()
        self.qhboxlayout.addLayout(self.qvboxlayout)

        self.setup_ui(reference_param_list, definition_ref_name)

    def init_ref_target_window(self):
        self.qdialog = QDialog()
        self.qdialog.setWindowTitle("Select Reference Tartget")
        self.qdialog.setWindowFlags(Qt.WindowType.WindowCloseButtonHint)
        self.qdialog.setFixedSize(561, 283)
        self.dialog_layout = QVBoxLayout(self.qdialog)
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.update_ref_target_in_table)
        self.init_ref_target_list(VALID_REF_TARGET_PATH_MAP, self.definition_ref_name)
        self.btn = QPushButton("ok")
        self.dialog_layout.addWidget(self.list_widget)
        self.dialog_layout.addWidget(self.btn)

    def init_ref_target_list(self, valid_ref_target_path_map: dict, input_definition: str):
        if input_definition not in valid_ref_target_path_map:
            return
        valid_ref_target = self.ecuc_config.find(valid_ref_target_path_map[input_definition])
        ref_target_path_list: list = []
        for container in valid_ref_target.SUB_CONTAINERS.ECUC_CONTAINER_VALUE:
            ref_target_path_list.append(
                (valid_ref_target_path_map[input_definition] + "/" + utils.get_short_name(container))
            )
        self.list_widget.addItems(ref_target_path_list)

    def show_qdialog(self):
        self.qdialog.exec()

    def update_ref_target_in_table(self, selected_item: QListWidgetItem):
        path_set = set()
        row_count = self.ref_list.count()
        for row_index in range(row_count):
            if self.ref_list.item(row_index) is not None:
                path_set.add(self.ref_list.item(row_index).text())
        if selected_item.text() not in path_set:
            self.ref_list.insertItem(row_count, selected_item.text())
        self.qdialog.close()

    def setup_ui(self, reference_param_list, definition_ref_name):
        short_name = definition_ref_name
        # Add reference parameter name
        self.addWidget(QLabel(short_name))
        self.addLayout(self.qhboxlayout)

        # Add add&remove button for ref target
        self.qvboxlayout.addWidget(self.push_buttton_add)
        self.qvboxlayout.addWidget(self.push_buttton_remove)
        self.qvboxlayout.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Fixed, QSizePolicy.Expanding))
        # add button handle add ref target in table
        self.push_buttton_add.clicked.connect(self.show_qdialog)

        self.ref_list.clear()
        for reference_param in reference_param_list:
            param_value = utils.get_value_ref(reference_param)
            self.ref_list.addItem(param_value)

        # Add Table
        self.qhboxlayout.addWidget(self.ref_list)
        self.ref_list.itemChanged.connect(self.on_item_changed)

    def on_item_changed(self, item):
        row_count = item.row()
        text = item.text()
        self.reference_param_list[row_count].VALUE_REF.valueOf_ = text
        # print(f"onTextChanged {text}")
        # return text
        return
