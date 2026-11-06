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
import platform
from PySide6.QtWidgets import QFileDialog, QDialog, QMessageBox
from PySide6.QtCore import Qt
from ui_adaptor.ui_interaction.ui_logger import logger
from cfg_gui.resources.ui.ui_new_project import Ui_Form

CUR_DIR = os.path.dirname(__file__)
CONFIGURATOR_PLUG_IN_PATH = "components/configs/configurator_plug_in"


class ProjectUIBase(QDialog, Ui_Form):
    """
    Project configuration class for supporting operations in new or setting interface
    """

    def __init__(self, result: dict, slot_call_back, mainwindow, type_name):
        super().__init__()
        self.type_name = type_name
        self.mainwindow = mainwindow
        self.target_compiler_list: dict = result
        self.slot_call_back = slot_call_back
        self.config_path = ""
        self.gendata_path = ""
        self.swc_template_path = ""
        self.bswcallout_path = ""
        self.user_plugin_output_path = ""
        self.application_path = ""
        self.ib_path = ""
        self.log_path = ""
        self.project_file_path = ""
        self.file_path = ""
        self.project_path = ""
        self.service_component_path = ""
        self.mcal_path = ""
        self.mcal_gendata_path = ""
        self.compiler_path = ""
        self.system_path = ""
        self.deafult_config_path = os.path.abspath(os.path.join(CUR_DIR, "../.."))
        self.studio_path = self.deafult_config_path
        self.setupUi(self)
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
            "compiler_path": self.lineEditCompilerPath,
            "mcal_path": self.lineEditMcalPath,
            "mcal_gendata_path": self.lineEditMcalGenDataPath,
            "system_path": self.lineEditSystemPath,
        }
        self.combo_box_list = {
            "target": self.comboBoxTarget,
            "compiler": self.comboBoxCompiler,
            "mcal_version": self.comboBoxMcalVersion,
        }

        self.pushButtonProject.clicked.connect(self.new_vcos_project_file_browse_slot)
        self.pushButtonConfig.clicked.connect(self.new_vcos_config_file_slot)
        self.pushButtonGenData.clicked.connect(self.new_vcos_codegen_path_slot)
        self.pushButtonTemplate.clicked.connect(self.new_vcos_template_files_slot)
        self.pushButtonBswCallout.clicked.connect(self.new_bswcallout_files_slot)
        self.pushButtonUserPluginOutputPath.clicked.connect(self.new_user_plugin_output_path_slot)
        self.pushButtonOK.clicked.connect(self.create_vcos_project_ok_slot)
        self.pushButtonApplication.clicked.connect(self.new_vcos_project_file_application_browse_slot)
        self.pushButtonServiceComponent.clicked.connect(self.new_vcos_project_file_service_component_slot)
        self.pushButtonIB.clicked.connect(self.new_vcos_project_file_ib_slot)
        self.pushButtonLog.clicked.connect(self.new_vcos_project_file_log_slot)
        self.pushButtonToolChain.clicked.connect(self.new_vcos_project_toolchain_slot)

        self.pushButtonMcalPath.clicked.connect(self.new_vcos_mcal_path_slot)
        self.pushButtonMcalGenDataPath.clicked.connect(self.new_vcos_mcal_gendata_path_slot)
        self.pushButtonSystemPath.clicked.connect(self.new_vcos_system_path_slot)

        self.set_line_edit_focus_policy()
        self.comboBoxTarget.clear()
        # self.lineEditSystemPath.textChanged.connect(self.system_path_text_changed_slot)
        self.comboBoxTarget.addItems([key for key, _ in self.target_compiler_list.items()])
        # 基于target更新compiler，json支持后再设计逻辑

        self.comboBoxTarget.currentIndexChanged.connect(self.compiler_update_with_target)
        self.comboBoxTarget.setEnabled(True)
        self.comboBoxCompiler.setEnabled(True)
        self.setWindowModality(Qt.ApplicationModal)
        if self.target_compiler_list != {}:
            self.update_compiler()

    def update_compiler(self):
        """Update compiler"""
        if not self.type_name == "NewProject":
            return
        default_cfg_path = self.deafult_config_path
        target_text = self.comboBoxTarget.currentText()
        if self.lineEditMcalPath.text() != "":
            self.mcal_path = os.path.abspath(os.path.join(default_cfg_path, "drivers"))
            self.lineEditMcalPath.setText(self.mcal_path)
        self.lineEditMcalPath.setCursorPosition(0)
        self.comboBoxCompiler.clear()
        self.comboBoxCompiler.addItems(self.target_compiler_list[target_text]["compiler"])

    # system path改变时调用
    def system_path_text_changed_slot(self, system_path):
        self.lineEditSystemPath.setText(system_path)
        self.lineEditSystemPath.setCursorPosition(0)
        if os.path.exists(system_path):
            self.system_path = system_path
            self.slot_call_back(
                "load_studio_plugin_config_file_action",
                system_path,
                self.type_name,
                result_callback=self.update_new_studio_target_info,
            )
        else:
            self.lineEditSystemPath.setText(self.system_path)
            self.system_path_incorrect_tips()

    def system_path_incorrect_tips(self):
        QMessageBox.critical(
            self,
            "Critical",
            "Configurator PlugIn Path is incorrect, please choose the correct {CONFIGURATOR_PLUG_IN_PATH} path.",
            QMessageBox.StandardButton.Ok,
            QMessageBox.StandardButton.Ok,
        )

    def update_new_studio_target_info(self, studio_support_target_list):
        self.target_compiler_list = studio_support_target_list
        self.update_target_combo_box(studio_support_target_list)
        self.update_compiler_combo_box(studio_support_target_list)
        self.update_mcal_combo_box(studio_support_target_list)
        self.update_mcal_version_combo_box(studio_support_target_list)

    def update_target_combo_box(self, studio_support_target_list):
        """update compiler with target change"""
        target_text = self.comboBoxTarget.currentText()
        self.comboBoxTarget.clear()
        self.comboBoxTarget.addItems([key for key, _ in studio_support_target_list.items()])
        if target_text in studio_support_target_list.keys():
            self.comboBoxTarget.setCurrentText(target_text)
        else:
            self.comboBoxTarget.setCurrentIndex(0)

    def update_compiler_combo_box(self, studio_support_target_list):
        """update compiler with target change"""
        current_target = self.comboBoxTarget.currentText()
        compiler_text = self.comboBoxCompiler.currentText()
        self.comboBoxCompiler.clear()
        self.comboBoxCompiler.addItems(studio_support_target_list[current_target]["compiler"])
        if compiler_text in studio_support_target_list[current_target]["compiler"]:
            self.comboBoxCompiler.setCurrentText(compiler_text)
        else:
            self.comboBoxCompiler.setCurrentIndex(0)

    def update_mcal_combo_box(self, studio_support_target_list):
        """update compiler with target change"""
        if self.type_name == "NewProject":
            self.update_mcal_related()

    def update_mcal_version_combo_box(self, studio_support_target_list):
        """update compiler with target change"""
        current_target = self.comboBoxTarget.currentText()
        mcal_version_text = self.comboBoxMcalVersion.currentText()
        self.comboBoxMcalVersion.clear()
        self.comboBoxMcalVersion.addItems(studio_support_target_list[current_target]["MCAL_VERSION"])
        if mcal_version_text in studio_support_target_list[current_target]["MCAL_VERSION"]:
            self.comboBoxMcalVersion.setCurrentText(mcal_version_text)
        else:
            self.comboBoxMcalVersion.setCurrentIndex(0)

    def update_compiler_info(self):
        """
        Update compilers after selecting a target
        """
        self.update_compiler()

    def set_line_edit_focus_policy(self):
        """
        Set LineEdit status as NoFocus
        """
        self.lineEditProjectFilePath.setFocusPolicy(Qt.NoFocus)
        for line_edit in self.line_edit_list.values():
            if line_edit == self.lineEditProjectName:
                continue
            line_edit.setFocusPolicy(Qt.NoFocus)

    def get_default_cfg_path(self, dir_name, cur_path):
        target_path = ""
        is_found = False
        if cur_path == os.path.abspath(os.path.join(cur_path, "..")):
            return ""
        if os.path.exists(os.path.join(cur_path, dir_name)):
            target_path = cur_path
            is_found = True
        if is_found is True:
            return target_path
        else:
            cur_path = os.path.abspath(os.path.join(cur_path, ".."))
            target_path = self.get_default_cfg_path(dir_name, cur_path)

        return target_path

    def set_line_edit_default(self):
        """
        Update configuration based on project name while creating a new project
        """
        if self.project_file_path == "":
            return

        config_path = os.path.dirname(self.project_file_path)
        default_cfg_path = self.deafult_config_path
        if self.lineEditConfigPath.text() == "":
            self.config_path = os.path.abspath(os.path.join(config_path, "config"))
            self.lineEditConfigPath.setText(self.config_path)
            self.lineEditConfigPath.setCursorPosition(0)
        if self.lineEditApplicationPath.text() == "":
            self.application_path = os.path.abspath(
                os.path.join(default_cfg_path, "examples", self.lineEditProjectName.text(), "apps")
            )
            self.lineEditApplicationPath.setText(self.application_path)
            self.lineEditApplicationPath.setCursorPosition(0)
        if self.lineEditBswIBPath.text() == "":
            self.ib_path = os.path.abspath(os.path.join(self.config_path, "internal_behavior"))
            self.lineEditBswIBPath.setText(self.ib_path)
            self.lineEditBswIBPath.setCursorPosition(0)
        if self.lineEditLogPath.text() == "":
            self.log_path = os.path.abspath(os.path.join(config_path, "log"))
            self.lineEditLogPath.setText(self.log_path)
            self.lineEditLogPath.setCursorPosition(0)
        if self.lineEditGenDataPath.text() == "":
            self.gendata_path = os.path.abspath(os.path.join(config_path, "gen_data"))
            self.lineEditGenDataPath.setText(self.gendata_path)
            self.lineEditGenDataPath.setCursorPosition(0)
        if self.lineEditTemplateFiles.text() == "":
            self.swc_template_path = os.path.abspath(os.path.join(self.application_path, "asw_swc"))
            self.lineEditTemplateFiles.setText(self.swc_template_path)
            self.lineEditTemplateFiles.setCursorPosition(0)
        if self.lineEditBswCalloutFiles.text() == "":
            self.bswcallout_path = os.path.abspath(os.path.join(self.application_path, "bsw_user_callout"))
            self.lineEditBswCalloutFiles.setText(self.bswcallout_path)
            self.lineEditBswCalloutFiles.setCursorPosition(0)
        if self.lineEditUserPluginOutputPath.text() == "":
            self.user_plugin_output_path = os.path.abspath(os.path.join(config_path, "gen_data"))
            self.lineEditGenDataPath.setText(self.user_plugin_output_path)
            self.lineEditGenDataPath.setCursorPosition(0)
        if self.lineEditServiceComponentPath.text() == "":
            self.service_component_path = os.path.abspath(os.path.join(self.config_path, "service_components"))
            self.lineEditServiceComponentPath.setText(self.service_component_path)
            self.lineEditServiceComponentPath.setCursorPosition(0)
        if self.lineEditCompilerPath.text() == "":
            update_compiler_path = ""
            system = platform.system()
            if system == "Linux":
                update_compiler_path = os.path.join(default_cfg_path, "tools/GnuArmToolchain/linux/gcc-arm")
            elif system == "Windows":
                update_compiler_path = os.path.join(default_cfg_path, "tools/GnuArmToolchain/windows")
            self.compiler_path = update_compiler_path
            self.lineEditCompilerPath.setText(self.compiler_path)
            self.lineEditCompilerPath.setCursorPosition(0)
        if self.lineEditMcalPath.text() == "":
            self.update_mcal_related()
        if self.lineEditSystemPath.text() == "":
            self.system_path = os.path.join(default_cfg_path, CONFIGURATOR_PLUG_IN_PATH)
            self.lineEditSystemPath.setText(self.system_path)
            self.lineEditSystemPath.setCursorPosition(0)
            self.system_path_text_changed_slot(self.system_path)
        else:
            self.system_path_text_changed_slot(self.lineEditSystemPath.text())

    def new_vcos_project_file_application_browse_slot(self):
        self.application_path = QFileDialog.getExistingDirectory(self, "config path", self.deafult_config_path)
        if not self.application_path:
            return
        else:
            self.application_path = os.path.abspath(
                os.path.join(os.path.dirname(self.application_path), self.application_path)
            )
        self.lineEditApplicationPath.setText(self.application_path)
        self.lineEditApplicationPath.setCursorPosition(0)

    def new_vcos_project_file_service_component_slot(self):
        self.service_component_path = QFileDialog.getExistingDirectory(self, "config path", self.deafult_config_path)
        if not self.service_component_path:
            return
        else:
            self.service_component_path = os.path.abspath(
                os.path.join(os.path.dirname(self.service_component_path), self.service_component_path)
            )
        self.lineEditServiceComponentPath.setText(self.service_component_path)
        self.lineEditServiceComponentPath.setCursorPosition(0)

    def new_vcos_project_file_ib_slot(self):
        self.ib_path = QFileDialog.getExistingDirectory(self, "config path", self.deafult_config_path)
        if not self.ib_path:
            return
        else:
            self.ib_path = os.path.abspath(os.path.join(os.path.dirname(self.ib_path), self.ib_path))
        self.lineEditBswIBPath.setText(self.ib_path)
        self.lineEditBswIBPath.setCursorPosition(0)

    def new_vcos_project_file_log_slot(self):
        self.log_path = QFileDialog.getExistingDirectory(self, "config path", self.deafult_config_path)
        if not self.log_path:
            return
        else:
            self.log_path = os.path.abspath(os.path.join(os.path.dirname(self.log_path), self.log_path))
        self.lineEditLogPath.setText(self.log_path)
        self.lineEditLogPath.setCursorPosition(0)

    def new_vcos_config_file_slot(self):
        self.config_path = QFileDialog.getExistingDirectory(self, "config path", self.deafult_config_path)
        if not self.config_path:
            return
        else:
            self.config_path = os.path.abspath(os.path.join(os.path.dirname(self.config_path), self.config_path))
        self.lineEditConfigPath.setText(self.config_path)
        self.lineEditConfigPath.setCursorPosition(0)

    def new_vcos_codegen_path_slot(self):
        self.gendata_path = QFileDialog.getExistingDirectory(self, "config path", self.deafult_config_path)
        if not self.gendata_path:
            return
        else:
            self.gendata_path = os.path.abspath(os.path.join(os.path.dirname(self.gendata_path), self.gendata_path))
        self.lineEditGenDataPath.setText(self.gendata_path)
        self.lineEditGenDataPath.setCursorPosition(0)

    def new_vcos_template_files_slot(self):
        self.swc_template_path = QFileDialog.getExistingDirectory(self, "config path", self.deafult_config_path)
        if not self.swc_template_path:
            return
        else:
            self.swc_template_path = os.path.abspath(
                os.path.join(os.path.dirname(self.swc_template_path), self.swc_template_path)
            )
        self.lineEditTemplateFiles.setText(self.swc_template_path)
        self.lineEditTemplateFiles.setCursorPosition(0)

    def new_bswcallout_files_slot(self):
        self.bswcallout_path = QFileDialog.getExistingDirectory(self, "config path", self.deafult_config_path)
        if not self.bswcallout_path:
            return
        else:
            self.bswcallout_path = os.path.abspath(
                os.path.join(os.path.dirname(self.bswcallout_path), self.bswcallout_path)
            )
        self.lineEditBswCalloutFiles.setText(self.bswcallout_path)
        self.lineEditBswCalloutFiles.setCursorPosition(0)

    def new_user_plugin_output_path_slot(self):
        self.user_plugin_output_path = QFileDialog.getExistingDirectory(self, "config path", self.deafult_config_path)
        if not self.user_plugin_output_path:
            return
        else:
            self.user_plugin_output_path = os.path.abspath(
                os.path.join(os.path.dirname(self.user_plugin_output_path), self.user_plugin_output_path)
            )
        self.lineEditUserPluginOutputPath.setText(self.user_plugin_output_path)
        self.lineEditUserPluginOutputPath.setCursorPosition(0)

    def new_vcos_project_toolchain_slot(self):

        self.compiler_path = QFileDialog.getExistingDirectory(self, "config path", self.deafult_config_path)
        if not self.compiler_path:
            return
        else:
            self.compiler_path = os.path.abspath(os.path.join(os.path.dirname(self.compiler_path), self.compiler_path))
        self.lineEditCompilerPath.setText(self.compiler_path)
        self.lineEditCompilerPath.setCursorPosition(0)

    def new_vcos_mcal_path_slot(self):
        self.mcal_path = QFileDialog.getExistingDirectory(self, "complexdriver path", self.deafult_config_path)
        if not self.mcal_path:
            return
        else:
            self.mcal_path = os.path.abspath(os.path.join(os.path.dirname(self.mcal_path), self.mcal_path))
        self.lineEditMcalPath.setText(self.mcal_path)
        self.lineEditMcalPath.setCursorPosition(0)

    def new_vcos_mcal_gendata_path_slot(self):
        self.mcal_gendata_path = QFileDialog.getExistingDirectory(self, "mcal gendata path", self.deafult_config_path)
        if not self.mcal_gendata_path:
            return
        else:
            self.mcal_gendata_path = os.path.abspath(
                os.path.join(os.path.dirname(self.mcal_gendata_path), self.mcal_gendata_path)
            )
        self.lineEditMcalGenDataPath.setText(self.mcal_gendata_path)
        self.lineEditMcalGenDataPath.setCursorPosition(0)

    def new_vcos_system_path_slot(self):
        system_path = QFileDialog.getExistingDirectory(self, "system path", self.deafult_config_path)
        if system_path:
            self.system_path_text_changed_slot(system_path)

    def create_vcos_project_ok_slot(self):
        """
        function triggerd by ok signal to update project configuration
        """
        if not os.path.exists(self.system_path):
            self.system_path_incorrect_tips()
            return
        # update system configuration as variable to return
        path_dict = self.update_sys_info_dict()
        if path_dict == {}:
            return

        # call mainwindow callback function to update project configuration
        self.slot_call_back("project_update", path_dict, self.type_name, result_callback=self.project_update_callback)
        self.update_mainwindow_state()
        self.mainwindow.recent_files_manager.add_recent_file(self.project_file_path)
        self.mainwindow._update_recent_file_actions()
        self.close()

    def project_update_callback(self, res):
        self.mainwindow.update_overview_ui(res)
        self.mainwindow.init_gui_secondary_menu()
        self.mainwindow.post_init_secondary_menu_signal_slot()
        self.mainwindow.user_module_menu.setEnabled(True)
        self.mainwindow.update_user_plugin_info()

    def update_mainwindow_state(self):
        self.mainwindow.centralwidget.setEnabled(True)
        self.mainwindow.menuCodeGen.setEnabled(True)
        self.mainwindow.actionToolsSetting.setEnabled(True)
        self.mainwindow.actionSave.setEnabled(True)
        self.mainwindow.actionSave_As.setEnabled(True)
        self.mainwindow.actionProject_Setting.setEnabled(True)
        self.mainwindow.actionOpen.setEnabled(True)
        self.mainwindow.actionNew.setEnabled(False)
        self.mainwindow.actionImport.setEnabled(True)
        self.mainwindow.actionExport.setEnabled(True)
        self.mainwindow.actionTaskAnalysis.setEnabled(True)
        self.mainwindow.studio_open_state = True

    def update_project_file(self, file_path):
        if file_path and not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as file:
                file.close()
        else:
            return

    def update_sys_info_dict(self):
        """
        UI界面修改工程配置后更新工程配置(适配界面与工程文件路径一致)，新建时创建工程文件
        """
        # 更新工程文件路径
        path_dict = {}
        if not self.project_file_path:
            return path_dict
        if not os.path.exists(os.path.dirname(self.project_file_path)):
            project_path = os.path.dirname(self.project_file_path)
            os.makedirs(project_path, exist_ok=True)
            self.update_project_file(self.project_file_path)
            # logger.debug(f"create {os.path.dirname(project_file_path)} success")
        # 根据UI界面中修改的工程配置，更新工程配置信息以及本地工程路径
        path_dict = self.project_configuration_update()
        return path_dict

    def project_configuration_update(self):
        """
        界面中获取控件信息返回dict更新工程配置
        """
        # 对象中获取UI界面
        path_dict = {}
        for LineEdit, item in self.line_edit_list.items():
            update_path = item.text()
            if update_path == "" and LineEdit == "mcal_path":
                self.update_mcal_related()
                logger.info("The configuration item of mcal_path has been filled in based on target")
            if (
                update_path != ""
                and not os.path.exists(update_path)
                and LineEdit != "project"
                and LineEdit != "project_path"
            ):
                os.makedirs(update_path)
            if LineEdit == "config_base_path":
                self.update_dirs_in_config(update_path)
            if LineEdit == "project_path":
                self.update_project_file(update_path)
                self.mainwindow.setWindowTitle(f"  {self.mainwindow.vcos_version}  {update_path}")
            path_dict.update({LineEdit: update_path})
        for QcomboBox, item in self.combo_box_list.items():
            update_para = item.currentText()
            path_dict.update({QcomboBox: update_para})
        path_dict.update({"studio_path": self.studio_path})
        if not os.path.exists(path_dict["system_path"]):
            logger.error_ui(f"{path_dict['system_path']} does not exist, Please modify the correct System Path!!!")
        path_dict.update({"mcal_version": self.comboBoxMcalVersion.currentText()})
        # 返回保存工程信息的字典
        return path_dict

    def get_project_file_path(self):
        return self.project_file_path

    def update_dirs_in_config(self, project_path):
        """update the directories in config"""
        dir_list: list = ["asw", "bsw", "system", "autosar", "internal_behavior", "service_components"]
        for dir in dir_list:
            new_path = os.path.join(os.path.abspath(project_path), dir)
            if os.path.exists(os.path.abspath(new_path)):
                continue
            os.mkdir(new_path)

    def compiler_update_with_target(self):
        """update compiler with target change"""
        target_text = self.comboBoxTarget.currentText()
        self.lineEditMcalPath.setCursorPosition(0)
        self.comboBoxCompiler.clear()
        if target_text not in self.target_compiler_list:
            return
        self.comboBoxCompiler.addItems(self.target_compiler_list[target_text]["compiler"])

        self.comboBoxMcalVersion.clear()
        if target_text not in self.target_compiler_list:
            return
        self.comboBoxMcalVersion.addItems(self.target_compiler_list[target_text]["MCAL_VERSION"])
        if self.type_name == "NewProject":
            self.update_mcal_related()

    def update_mcal_related(self):
        """update mcal-related info"""
        default_config_path = self.deafult_config_path
        target_map_to_dir = {
            "E3": "MCAL_E3XX",
            "RH": "MCAL_RH850",
            "TC": "MCAL_TC3XX",
            "J6": "MCAL_J6E",
        }
        target_text = self.comboBoxTarget.currentText()
        for target_abbr, target_dir in target_map_to_dir.items():
            if target_abbr in target_text:
                self.mcal_path = os.path.abspath(os.path.join(default_config_path, "drivers"))
                self.lineEditMcalPath.setText(self.mcal_path)
                self.lineEditMcalPath.setCursorPosition(0)
                break
