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
from PySide6.QtWidgets import QFileDialog
from cfg_gui.project_management.project_base_ui import ProjectUIBase

CUR_DIR = os.path.dirname(__file__)


class ProjectConfigUI(ProjectUIBase):
    """
    Project Setting UI Class for modifying project configuration in a visible interface
    """

    def __init__(self, sys_info_dict: dict = None, slot_call_back=None, mainwindow=None):
        super().__init__(
            result=sys_info_dict["target_compiler_list"],
            slot_call_back=slot_call_back,
            mainwindow=mainwindow,
            type_name="ProjectConfig",
        )
        self.sys_info_dict = sys_info_dict["project_setting_action"]
        self.show_init()

    def show_init(self):
        self.Description_Label.setText("Project Setting")
        self.lineEditProjectName.setEnabled(False)
        self.lineEditProjectName.setText(self.sys_info_dict["project"])
        self.lineEditProjectName.setCursorPosition(0)
        self.pushButtonProject.setEnabled(False)
        self.lineEditProjectFilePath.setText(self.sys_info_dict["project_path"])
        self.lineEditProjectFilePath.setCursorPosition(0)
        self.lineEditConfigPath.setText(self.sys_info_dict["config_base_path"])
        self.lineEditConfigPath.setCursorPosition(0)
        self.lineEditApplicationPath.setText(self.sys_info_dict["application_path"])
        self.lineEditApplicationPath.setCursorPosition(0)
        self.lineEditBswIBPath.setText(self.sys_info_dict["internal_behavior_path"])
        self.lineEditBswIBPath.setCursorPosition(0)
        self.lineEditLogPath.setText(self.sys_info_dict["log_path"])
        self.lineEditLogPath.setCursorPosition(0)
        self.lineEditGenDataPath.setText(self.sys_info_dict["gendata_path"])
        self.lineEditGenDataPath.setCursorPosition(0)
        self.lineEditTemplateFiles.setText(self.sys_info_dict["swc_template_path"])
        self.lineEditTemplateFiles.setCursorPosition(0)
        self.lineEditBswCalloutFiles.setText(self.sys_info_dict["bswcallout_path"])
        self.lineEditBswCalloutFiles.setCursorPosition(0)
        self.lineEditUserPluginOutputPath.setText(self.sys_info_dict["user_plugin_output_path"])
        self.lineEditUserPluginOutputPath.setCursorPosition(0)
        self.lineEditServiceComponentPath.setText(self.sys_info_dict["service_component_path"])
        self.lineEditServiceComponentPath.setCursorPosition(0)
        self.lineEditCompilerPath.setText(self.sys_info_dict["compiler_path"])
        self.comboBoxMcalVersion.clear()
        self.comboBoxMcalVersion.addItems(self.target_compiler_list[self.sys_info_dict["target"]]["MCAL_VERSION"])
        self.comboBoxMcalVersion.setCurrentText(self.sys_info_dict["mcal_version"])
        self.lineEditMcalPath.setText(self.sys_info_dict["mcal_path"])
        self.lineEditMcalPath.setCursorPosition(0)
        self.lineEditMcalGenDataPath.setText(self.sys_info_dict["mcal_gendata_path"])
        self.lineEditMcalGenDataPath.setCursorPosition(0)
        self.lineEditSystemPath.setText(self.sys_info_dict["system_path"])
        self.system_path = self.sys_info_dict["system_path"]
        self.lineEditSystemPath.setCursorPosition(0)
        self.comboBoxTarget.setCurrentText(self.sys_info_dict["target"])
        self.compiler_update_with_target()
        self.comboBoxCompiler.setCurrentText(self.sys_info_dict["compiler"])
        self.lineEditCompilerPath.setCursorPosition(0)
        self.comboBoxTarget.setEnabled(False)
        self.project_file_path = os.path.join(self.sys_info_dict["project_path"])

    def new_vcos_project_file_browse_slot(self):
        self.project_path = QFileDialog.getExistingDirectory(self, "文件保存", self.deafult_config_path)
        if not self.project_path:
            return
        self.project_file_path = os.path.abspath(
            os.path.join(
                self.project_path, self.lineEditProjectName.text(), f"{self.lineEditProjectName.text()}.vcosproject"
            )
        )
        self.lineEditProjectFilePath.setText(self.project_file_path)
        self.lineEditProjectFilePath.setCursorPosition(0)
