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
from PySide6 import QtWidgets
from cfg_gui.resources.ui.ui_export_mapping_info import Ui_Form

CUR_FILE_PATH = os.path.dirname(__file__)


class ExportMappingInfo(QtWidgets.QDialog, Ui_Form):

    def __init__(self, main_window, mapping_type):
        super(ExportMappingInfo, self).__init__()
        self.callback = main_window.slot_call_back
        self.mapping_type = mapping_type
        self.main_window = main_window
        self.task_mapping_ui = self.main_window.rte_edit_ui.task_mapping_ui
        self.data_mapping_ui = self.main_window.rte_edit_ui.data_mapping_ui
        self.file_path = ""

        self.setupUi(self)
        self.export_mapping_info = self
        self.export_mapping_info.pushButtonOK.clicked.connect(self.export_ok_slot)
        self.export_mapping_info.pushButtonBrowse.clicked.connect(self.target_file_browse_slot)

    def target_file_browse_slot(self):
        self.file_path, filetype = QtWidgets.QFileDialog.getSaveFileName(
            self, "文件保存", os.path.join(CUR_FILE_PATH, "../"), "xlsx Files (*.xlsx)"
        )
        if not self.file_path:
            return
        self.export_mapping_info.lineEditProjectFilePath.setText(self.file_path)

    def export_ok_slot(self):

        info_table = None
        if self.file_path is None:
            return
        if "port_mapping" == self.mapping_type:
            pass
        elif "data_mapping" == self.mapping_type:
            info_table = self.data_mapping_ui.table_model
        elif "service_mapping" == self.mapping_type:
            pass
        elif "task_mapping" == self.mapping_type:
            info_table = self.task_mapping_ui.table_view_model
        elif "export_os_info" == self.mapping_type:
            info_table = self.task_mapping_ui.table_view_model
        if info_table:
            self.callback("export_mapping_info_to_excel", info_table, self.mapping_type, self.file_path)

        self.close()
