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
from copy import deepcopy
from PySide6.QtWidgets import QFileDialog, QDialog, QMessageBox
from PySide6.QtCore import Qt
from cfg_gui.resources.ui.ui_save_as_project import Ui_Form

CUR_DIR = os.path.dirname(__file__)
VCOS_DIR = os.path.join(CUR_DIR, "..", "..", "..", "..")


class SaveAsProjectUI(QDialog, Ui_Form):
    """
    Save as project UI Class in a visible interface
    """

    def __init__(self, default_prj_path="", slot_call_back=None, mainwindow=None):
        super().__init__()
        self.default_prj_path = default_prj_path  # 另存工程的默认目录
        self.slot_call_back = slot_call_back
        self.main_window = mainwindow
        self.project = ""
        self.project_path = ""
        self.config_base_path = ""
        self.gendata_path = ""
        self.application_path = ""
        self.swc_template_path = ""
        self.bswcallout_path = ""
        self.user_plugin_output_path = ""
        self.service_component_path = ""
        self.internal_behavior_path = ""
        self.log_path = ""
        self.mcal_gendata_path = ""
        self.sys_info_class = None
        self.setupUi(self)
        self.setFocus()
        self.setWindowModality(Qt.ApplicationModal)
        self.line_edit_list = {
            "project": self.lineEditProjectName,
            "project_path": self.lineEditProjectFilePath,
            "config_base_path": self.lineEditConfigPath,
            "gendata_path": self.lineEditGenDataPath,
            "application_path": self.lineEditApplicationPath,
            "swc_template_path": self.lineEditTemplateFiles,
            "bswcallout_path": self.lineEditBswCalloutFiles,
            "user_plugin_output_path": self.lineEditUserPluginOutputPath,
            "service_component_path": self.lineEditServiceComponentPath,
            "internal_behavior_path": self.lineEditBswIBPath,
            "log_path": self.lineEditLogPath,
            "mcal_gendata_path": self.lineEditMcalGenDataPath,
        }
        self.init_config()
        self.init_signal()

    def init_config(self):
        """获取原始工程配置，后续用户指定更新"""
        sys_info_class = self.slot_call_back("get_sys_info")
        self.sys_info_class = deepcopy(sys_info_class)

    def init_signal(self):
        self.lineEditProjectName.editingFinished.connect(self.update_prj_info_slot)
        self.pushButtonProject.clicked.connect(self.save_as_vcos_project_file_browse_slot)
        self.pushButtonApplication.clicked.connect(lambda: self.vcos_browse_slot("application_path"))
        self.pushButtonGenData.clicked.connect(lambda: self.vcos_browse_slot("gendata_path"))
        self.pushButtonConfig.clicked.connect(lambda: self.vcos_browse_slot("config_base_path"))
        self.pushButtonTemplate.clicked.connect(lambda: self.vcos_browse_slot("swc_template_path"))
        self.pushButtonBswCallout.clicked.connect(lambda: self.vcos_browse_slot("bswcallout_path"))
        self.pushButtonUserPluginOutputPath.clicked.connect(lambda: self.vcos_browse_slot("user_plugin_output_path"))
        self.pushButtonServiceComponent.clicked.connect(lambda: self.vcos_browse_slot("service_component_path"))
        self.pushButtonIB.clicked.connect(lambda: self.vcos_browse_slot("internal_behavior_path"))
        self.pushButtonLog.clicked.connect(lambda: self.vcos_browse_slot("log_path"))
        self.pushButtonMcalGenData.clicked.connect(lambda: self.vcos_browse_slot("mcal_gendata_path"))
        self.pushButtonOK.clicked.connect(self.save_as_vcos_project_ok_slot)

    def update_prj_info_slot(self):
        for key, obj in self.line_edit_list.items():
            if key == "project":
                continue
            text = obj.text()
            if text == "":
                break
            if self.lineEditProjectName.text():
                obj.setText(text.replace(self.project, self.lineEditProjectName.text()))
        if self.lineEditProjectName.text():
            self.project = self.lineEditProjectName.text()
        else:
            self.lineEditProjectName.setText(self.project)

    def vcos_browse_slot(self, label):
        check: bool = self.check_project_name_info()
        if not check:
            return

        temp_path = QFileDialog.getExistingDirectory(self, "Configuration of path", VCOS_DIR)
        if not temp_path:
            return
        else:
            temp_path = os.path.abspath(temp_path)
            if hasattr(self, label):
                setattr(self, label, temp_path)
        self.line_edit_list[label].setText(temp_path)
        self.line_edit_list[label].setCursorPosition(0)

    def save_as_vcos_project_file_browse_slot(self):
        check: bool = self.check_project_name_info()
        if not check:
            return

        self.save_as_project_path = QFileDialog.getExistingDirectory(self, "文件另存为", self.default_prj_path)
        if not self.save_as_project_path:
            return
        self.project_path = os.path.abspath(
            os.path.join(
                self.save_as_project_path,
                self.lineEditProjectName.text(),
                "cfg_prj",
                f"{self.lineEditProjectName.text()}.vcosproject",
            )
        )
        self.lineEditProjectFilePath.setText(self.project_path)
        self.set_default_path()

    def save_as_vcos_project_ok_slot(self):
        """另存为界面配置完成后，另存为工程的配置全局变量保存，便于后续的文件拷贝等动作"""
        completed_or_not = self.check_config()
        if not completed_or_not:
            return
        self.update_config()
        # 更新另存为工程的配置信息
        self.slot_call_back("update_save_as_vcos_prj", self.sys_info_class)
        # 保存原工程信息 && 更新另存为工程（拷贝文件目录以及修改工程信息）
        self.slot_call_back("save_action", "", True, result_callback=self.save_as_vcos_project)
        self.close()

    def check_config(self):
        """检查另存为界面配置信息"""
        for key, obj in self.line_edit_list.items():
            text = obj.text()
            if text == "" and key != "mcal_gendata_path":
                return False
        return True

    def check_project_name_info(self):
        self.project = self.lineEditProjectName.text()
        if self.project == "":
            result = QMessageBox.information(self, "Notice", "Input Project Name firstly", QMessageBox.Ok)
            if result == QMessageBox.Ok or result == QMessageBox.close:
                return False
        else:
            return True

    def save_as_vcos_project(self):
        self.slot_call_back("save_as_vcos_project")

    def update_config(self):
        # 如果填写的信息为空，则点击OK返回
        # 待设计
        new_value = ""
        for key in self.line_edit_list.keys():
            if hasattr(self, key):
                new_value = getattr(self, key, "")
            if not new_value:
                continue
            setattr(self.sys_info_class, key, new_value)

    def set_default_path(self):
        if self.project_path == "":
            return
        config_path = os.path.dirname(self.project_path)

        for key, obj in self.line_edit_list.items():
            if key in ["project", "project_path"]:
                continue
            elif key == "config_base_path":
                self.config_base_path = os.path.abspath(os.path.join(config_path, "config"))
                obj.setText(self.config_base_path)
            elif key == "gendata_path":
                self.gendata_path = os.path.abspath(os.path.join(config_path, "gen_data"))
                obj.setText(self.gendata_path)
            elif key == "application_path":
                self.application_path = os.path.abspath(
                    os.path.join(config_path, "../../", self.line_edit_list["project"].text(), "apps")
                )
                obj.setText(self.application_path)
            elif key == "swc_template_path":
                self.swc_template_path = os.path.abspath(os.path.join(self.application_path, "asw_swc"))
                obj.setText(self.swc_template_path)
            elif key == "bswcallout_path":
                self.bswcallout_path = os.path.abspath(os.path.join(self.application_path, "bsw_user_callout"))
                obj.setText(self.bswcallout_path)
            elif key == "user_plugin_output_path":
                self.user_plugin_output_path = os.path.abspath(os.path.join(config_path, "gen_data"))
                obj.setText(self.user_plugin_output_path)
            elif key == "service_component_path":
                self.service_component_path = os.path.abspath(os.path.join(self.config_base_path, "service_components"))
                obj.setText(self.service_component_path)
            elif key == "internal_behavior_path":
                self.internal_behavior_path = os.path.abspath(os.path.join(self.config_base_path, "internal_behavior"))
                obj.setText(self.internal_behavior_path)
            elif key == "log_path":
                self.log_path = os.path.abspath(os.path.join(config_path, "log"))
                obj.setText(self.log_path)
            elif key == "mcal_gendata_path":
                origin_path = getattr(self.sys_info_class, key, "")
                if origin_path != "":
                    dir_list = origin_path.split("mcal_prj")
                    if len(dir_list) == 2:
                        self.mcal_gendata_path = os.path.abspath(
                            os.path.join(self.config_base_path, "..", "..", f"mcal_prj{dir_list[1]}")
                        )
                    else:
                        self.mcal_gendata_path = os.path.abspath(
                            os.path.join(self.config_base_path, "..", "..", "mcal_prj")
                        )
                else:
                    self.mcal_gendata_path = origin_path
                obj.setText(self.mcal_gendata_path)
            obj.setCursorPosition(0)

    def closeEvent(self, event):
        self.close()
