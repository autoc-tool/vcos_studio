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
from PySide6.QtWidgets import QFileDialog, QMessageBox
from cfg_gui.project_management.project_base_ui import ProjectUIBase, CONFIGURATOR_PLUG_IN_PATH

CUR_DIR = os.path.dirname(__file__)


class NewProjectUI(ProjectUIBase):
    """
    New project UI Class for creating a new project in a visible interface
    """

    def __init__(self, result, slot_call_back=None, mainwindow=None):
        super().__init__(result=result, slot_call_back=slot_call_back, mainwindow=mainwindow, type_name="NewProject")

    def new_vcos_project_file_browse_slot(self):
        project_name = self.lineEditProjectName.text()
        if not project_name:
            QMessageBox.information(
                self, "Notice", "Project Name missing,\n Please supplement firstly", QMessageBox.StandardButton.Ok
            )
            return

        self.project_path = QFileDialog.getExistingDirectory(self, "文件保存", self.deafult_config_path)
        if not self.project_path:
            return
        self.lineEditProjectName.setEnabled(False)
        if not self.lineEditProjectFilePath.text():
            self.project_file_path = os.path.abspath(
                os.path.join(self.project_path, project_name, "cfg_prj", f"{project_name}.vcosproject")
            )
        else:
            self.project_file_path = os.path.abspath(os.path.join(self.project_path, f"{project_name}.vcosproject"))
        self.lineEditProjectFilePath.setText(self.project_file_path)
        self.lineEditProjectFilePath.setCursorPosition(0)
        default_cfg_path = self.get_default_cfg_path(CONFIGURATOR_PLUG_IN_PATH, self.project_path)
        if default_cfg_path != "":
            self.deafult_config_path = default_cfg_path
        else:
            self.deafult_config_path = self.project_path
        self.set_line_edit_default()
