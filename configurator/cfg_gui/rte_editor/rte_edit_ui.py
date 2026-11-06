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
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout
from cfg_gui.rte_editor.task_mapping_ui import TaskMappingUI
from cfg_gui.rte_editor.port_mapping_ui import PortMappingUI
from cfg_gui.rte_editor.data_mapping_ui import DataMappingUI
from cfg_gui.rte_editor.service_mapping_ui import ServiceMappingUI
from cfg_gui.export_file.export_mapping_info_ui import ExportMappingInfo

CUR_FILE_PATH = os.path.dirname(__file__)
RTE_TAB_IDX: dict = {
    "Task Mapping": 0,
    "Port Mapping": 1,
    "Data Mapping": 2,
    "Service Mapping": 3,
}


class RteEditUI:

    def __init__(self, main_window):
        self.main_window = main_window
        self.export_mapping_info = None
        self.init_mapping()
        self.setup_ui()

    def init_mapping(self):
        self.task_mapping_ui = TaskMappingUI()
        self.data_mapping_ui = DataMappingUI()
        self.port_mapping_ui = PortMappingUI()
        self.service_mapping_ui = ServiceMappingUI()

        self.is_task_mapping_data_updated = False
        self.is_data_mapping_data_updated = False
        self.is_port_mapping_data_updated = False
        self.is_service_mapping_data_updated = False

    def setup_ui(self):
        self.os_export_button = QPushButton("Export Os Info")
        self.os_export_button.setFixedSize(110, 25)
        self.task_mapping_export_button = QPushButton("Export")
        self.task_mapping_export_button.setFixedSize(80, 25)
        task_mapping_q_hbox_layout = QHBoxLayout()
        task_mapping_q_hbox_layout.addWidget(self.main_window.label_16)
        task_mapping_q_hbox_layout.addStretch()
        task_mapping_q_hbox_layout.addWidget(self.os_export_button)
        task_mapping_q_hbox_layout.addWidget(self.task_mapping_export_button)
        taskMappingLayout: QVBoxLayout = self.main_window.taskMappingLayout
        taskMappingLayout.addLayout(task_mapping_q_hbox_layout)
        taskMappingLayout.addWidget(self.task_mapping_ui)

        self.data_mapping_export_button = QPushButton("Export")
        self.data_mapping_export_button.setFixedSize(80, 25)
        data_mapping_q_hbox_layout = QHBoxLayout()
        data_mapping_q_hbox_layout.addWidget(self.main_window.label_18)
        data_mapping_q_hbox_layout.addStretch()
        data_mapping_q_hbox_layout.addWidget(self.data_mapping_export_button)
        dataMappingLayout: QVBoxLayout = self.main_window.dataMappingLayout
        dataMappingLayout.addLayout(data_mapping_q_hbox_layout)
        dataMappingLayout.addWidget(self.data_mapping_ui)

        self.port_mapping_export_button = QPushButton("Export")
        self.port_mapping_export_button.setFixedSize(80, 25)
        port_mapping_q_hbox_layout = QHBoxLayout()
        port_mapping_q_hbox_layout.addWidget(self.main_window.label_15)
        port_mapping_q_hbox_layout.addStretch()
        port_mapping_q_hbox_layout.addWidget(self.port_mapping_export_button)
        portMappingLayout: QVBoxLayout = self.main_window.portMappingLayout
        portMappingLayout.addLayout(port_mapping_q_hbox_layout)
        portMappingLayout.addWidget(self.port_mapping_ui)

        self.service_mapping_export_button = QPushButton("Export")
        self.service_mapping_export_button.setFixedSize(80, 25)
        service_mapping_q_hbox_layout = QHBoxLayout()
        service_mapping_q_hbox_layout.addWidget(self.main_window.label_12)
        service_mapping_q_hbox_layout.addStretch()
        service_mapping_q_hbox_layout.addWidget(self.service_mapping_export_button)
        serviceMappingLayout: QVBoxLayout = self.main_window.serviceMappingLayout
        serviceMappingLayout.addLayout(service_mapping_q_hbox_layout)
        serviceMappingLayout.addWidget(self.service_mapping_ui)

        self.os_export_button.clicked.connect(self.export_button_clicked_solt("export_os_info"))
        self.task_mapping_export_button.clicked.connect(self.export_button_clicked_solt("task_mapping"))
        self.data_mapping_export_button.clicked.connect(self.export_button_clicked_solt("data_mapping"))
        self.port_mapping_export_button.clicked.connect(self.export_button_clicked_solt("port_mapping"))
        self.service_mapping_export_button.clicked.connect(self.export_button_clicked_solt("service_mapping"))

    def export_button_clicked_solt(self, mapping_type):

        def warpper():
            self.export_mapping_info = ExportMappingInfo(self.main_window, mapping_type)
            self.export_mapping_info.show()

        return warpper
