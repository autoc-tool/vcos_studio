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
from typing import Callable
from PySide6 import QtWidgets, QtGui
from PySide6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QFileDialog,
    QPushButton,
    QMessageBox,
    QTreeWidget,
    QTableWidget,
    QWidget,
    QToolBox,
    QSpacerItem,
    QSizePolicy,
)
from PySide6.QtCore import QSize, QTimer
from cfg_gui.resources.images import images_rc  # noqa: F401
from cfg_gui.resources.ui.ui_mainwindow import Ui_mainWindow
from cfg_gui.common.basic_ui_handler import BasicUIHandler
from cfg_gui.project_management.new_project_ui import NewProjectUI
from cfg_gui.project_management.save_as_project_ui import SaveAsProjectUI
from cfg_gui.project_management.project_information_ui import ProjectConfigUI
from cfg_gui.project_management.plugin_manager_dialog_ui import PluginManagerDialog
from cfg_gui.project_management.module_manage_ui import ModuleManageUi
from cfg_gui.project_management.main_general_ui import ConfigratorGeneral
from cfg_gui.export_file.export_ecuc_arxml_ui import ExportEcucArxmlUi
from cfg_gui.import_file.import_arxml_ui import HintInfoListDialog, ImportArxmlUi
from cfg_gui.import_file.import_asw_arxml_ui import ImportASWARXMLUI
from cfg_gui.import_file.import_files_ui import ImportFilesUI
from cfg_gui.bsw_editor.overview_ui import OverViewUI
from cfg_gui.rte_editor.rte_edit_ui import RteEditUI
from cfg_gui.validation.validation_ui import ValidationUI
from cfg_gui.validation.validation_cfg_ui import ValidationCFGUI
from cfg_gui.generator.generate_cfg_ui import BSWGeneratorWidget
from cfg_gui.generator.swc_generator_ui import SWCGeneratorWidget
from cfg_gui.secondary_menu.task_analysis_ui import TaskAnalysisUI
from cfg_gui.secondary_menu.secondary_menu_ui import SecondaryMenu
from cfg_gui.secondary_menu.jitter_optimization_ui import JitterOptimizationUI
from cfg_gui.search_jump.find_ui import FindTableViewWidget
from cfg_gui.widgets.log_widget import LogWidget
from func_module.project_management.recent_files_manager import RecentFilesManager
from ui_adaptor.ui_interaction.ui_logger import logger
from ui_adaptor.data_management import (
    get_module_stack_dict,
    get_sys_info_class,
    get_autosar_bsw_class,
    get_sys_target_dict,
    get_all_module_list,
)

CUR_FILE_PATH = os.path.dirname(__file__)

DEFAULT_SAVE_CYCLE = "60"


class MainWindow(QtWidgets.QMainWindow, Ui_mainWindow):

    def __init__(self, app: QApplication, call_back, status_queue=None, save_timer_flag=False, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.slot_call_back = lambda *args, **kwargs: args or kwargs
        self.app = app
        self.status_queue = status_queue
        self.status = {"status": "init", "studio_version": "", "project_info": {"path": ""}}
        self.input_configurator_project_file_path = None
        self.autosar_tab_name = "VCOS BSW"
        self.studio_version = ""
        self.save_timer = None
        self.save_cycle = DEFAULT_SAVE_CYCLE
        self.save_timer_flag = save_timer_flag
        self._pre_init()
        self._post_init(call_back)
        self.get_periodic_save_time()
        self.init_windows_title()
        self.init_project_save_timer()

    def print_coredump_info(self, message):
        if message is None or message["status"] == "init":
            pass
        elif message.get("subprocess_status", None).get("info", None).get("data", None):
            logger.ui_error(
                f"""Studio异常重启:\n
                错误信息: {message["subprocess_status"]["info"]["data"]}\n
                操作记录: {message["subprocess_status"]["info"]["stack_info"]}"""
            )
        else:
            logger.ui_error("""Studio异常重启""")
        pass

    def get_periodic_save_time(self):
        tools_setting = self.slot_call_back("get_periodic_save_time_action")
        if tools_setting is None:
            self.save_cycle = DEFAULT_SAVE_CYCLE
            self.periodic_save_setting = True
            return
        self.save_cycle = tools_setting.get("save_cycle", DEFAULT_SAVE_CYCLE)
        self.periodic_save_setting = tools_setting.get("periodic_save_setting", True)

    def init_windows_title(self):
        self.studio_version = self.slot_call_back("get_studio_version_action")
        self.setWindowTitle(f"VCOS Studio({self.studio_version})")
        self.status["studio_version"] = self.studio_version
        self.send_status_to_daemon(self.status)

    def _pre_init(self):
        self.import_files_ui = None
        self.bsw_generate_ui = None
        self.swc_generate_ui = None
        self.validation_cfg_ui = None
        self.project_setting = None
        self.new_project_ui = None
        self.import_arxml_ui = None
        self.export_ecuc_arxml_ui = None
        self.save_as_vcos_project_ui = None
        self.general = None
        self.project_check_qmessagebox = None
        # 初始化界面为 VCOS VBSW
        self.studio_open_state = False
        self.project_file_path = ""
        self.vcos_version = ""
        self.user_module_menu = None
        self.show()

    def _post_init(self, call_back):
        self._init_gui()
        self._register_slot_callback(call_back)
        self._init_finish()
        self._post_init_gui()
        self._post_init_signal_slot()
        self._init_action_manager()
        self._init_user_module_plugin_manager()

    def _init_action_manager(self):
        self.dynamic_actions = []
        self.menu_file = self.menuBar().findChild(QtWidgets.QMenu, "menuFile")
        self.recent_files_menu = QtWidgets.QMenu("Open Recent")
        self.menu_file.insertMenu(self.actionSave, self.recent_files_menu)
        self.recent_files_manager = RecentFilesManager()
        self._update_recent_file_actions()

    def _init_user_module_plugin_manager(self):
        if self.user_module_menu is None:
            self.user_module_menu = self.menuBar().addMenu("User_Module_Plugin")
            self.manage_plugins_action = QtGui.QAction("Manage Plugins", self.user_module_menu)
            self.plugin_manager_dialog = PluginManagerDialog(self, self.slot_call_back)
            self.manage_plugins_action.triggered.connect(lambda: self._manage_plugins(self.plugin_manager_dialog))
            self.user_module_menu.addAction(self.manage_plugins_action)
            self.user_module_menu.setEnabled(False)

    def _manage_plugins(self, dialog):
        dialog.pre_init_ui()
        dialog.open()

    def _update_recent_file_actions(self):
        """更新最近文件的菜单项"""
        self.recent_files_menu.clear()  # 清空当前的动态菜单项

        # 获取最近文件并添加菜单项
        recent_files = self.recent_files_manager.get_recent_files()
        for recent_file in recent_files:
            file_path = recent_file.get_file_path()
            self._add_dynamic_action(
                file_path,
                self.select_open_vcos_project_config_file_slot,
                self.recent_files_menu,  # 仅添加到最近文件的子菜单
                args=file_path,
            )

    def _add_dynamic_action(self, action_name, slot_name, menu, args=None):
        # 创建新 QAction
        new_action = QtGui.QAction(action_name, self)
        new_action.triggered.connect(lambda: slot_name(args))
        # 将 QAction 添加到菜单
        menu.addAction(new_action)

    def _post_init_gui(self):
        self.init_gui_secondary_menu()

    def _post_init_signal_slot(self):
        self.post_init_secondary_menu_signal_slot()

    def _init_gui(self):
        self.rte_edit_ui = RteEditUI(self)
        self.over_view_ui = OverViewUI(self)
        self.basic_ui_handler = BasicUIHandler(self)
        self.validation_ui = ValidationUI(self)
        self.find_table_view = FindTableViewWidget(self)
        self.secondary_menu = SecondaryMenu(self)
        self.log_widget = LogWidget(self)

        self.centralwidget.setEnabled(False)
        self.menuCodeGen.setEnabled(False)
        self.actionToolsSetting.setEnabled(False)
        self.actionSave.setEnabled(False)
        self.actionSave_As.setEnabled(False)
        self.actionProject_Setting.setEnabled(False)
        self.actionTaskAnalysis.setEnabled(False)
        self.actionJitterOpt.setEnabled(False)
        self.actionImport.setEnabled(False)
        self.actionExport.setEnabled(False)
        self.action_import_os_cfg.setEnabled(False)
        self.action_export_os_cfg.setEnabled(False)
        self.menuOs_Configuration.setEnabled(False)
        self.tabWidget.setCurrentIndex(0)  # type: ignore
        self.tabWidget_2.setCurrentIndex(0)
        self.rte_tab_prev_index = 0
        self.init_properties_tab_widget()
        self.init_signal_slot()
        self.rte_edit_ui.task_mapping_ui.set_update_overview(self.over_view_ui.update_bsw_module_data_and_view)

    def post_init_secondary_menu_signal_slot(self):
        """Secondary menu objects' signals and slots"""
        for group_name, value in self.secondary_menu_cfg.items():
            for button_name, value_detail in value.items():
                button_var_name = f"sec_{button_name.replace(' ', '_')}_button".lower()
                button = getattr(self, button_var_name)
                if button_var_name == "sec_ecu_management_button":
                    button.setEnabled(False)
                button.clicked.connect(
                    lambda group=group_name, button=button_name: self.secondary_menu_slot(group, button)
                )

    def init_signal_slot(self):
        self.actionSave.setShortcut("CTRL+SHIFT+S")
        self.actionOpen.setShortcut("CTRL+SHIFT+P")
        self.actionGenerator.setShortcut("CTRL+SHIFT+G")
        self.actionValidation.setShortcut("CTRL+SHIFT+V")
        self.actionSWC_Generator.setShortcut("CTRL+SHIFT+M")
        self.treeWidgetOverview.doubleClicked.connect(self.over_view_ui.show_bsw_tab_slot)
        self.tabWidget.currentChanged.connect(self.bsw_rte_switch_tab_solt)
        self.bswTabWidget.tabCloseRequested.connect(self.over_view_ui.close_bsw_tab_solt)
        self.bswTabWidget.currentChanged.connect(self.over_view_ui.switch_bsw_tab_solt)

        self.import_files_button.clicked.connect(self.import_files_solt)
        self.import_arxml_button.clicked.connect(self.import_arxml_solt)
        self.export_arxml_button.clicked.connect(self.export_ecuc_arxml_slot)
        self.import_asw_arxml_button.clicked.connect(self.import_asw_arxml_slot)
        self.actionGenerator.triggered.connect(self.generate_vcos_c_code_slot)
        self.actionValidation.triggered.connect(self.get_validation_config_slot)
        self.actionSWC_Generator.triggered.connect(self.swc_generator_vcos_c_code_slot)
        self.actionTaskAnalysis.triggered.connect(self.task_analysis_slot)
        self.actionJitterOpt.triggered.connect(self.jitter_auto_optimization_slot)

        self.actionOpen.triggered.connect(self.select_open_vcos_project_config_file_slot)
        self.actionUpdate.triggered.connect(self.update_vcos_service_arxml_slot)
        self.actionSave.triggered.connect(self.save_vcos_project_config_file_slot)
        self.actionSave_As.triggered.connect(self.save_as_vcos_project_slot)
        self.actionNew.triggered.connect(self.new_vcos_project_config_file_slot)
        self.actionImport.triggered.connect(self.import_arxml_solt)
        self.actionExport.triggered.connect(self.export_ecuc_arxml_slot)
        self.actionProject_Setting.triggered.connect(self.update_project_settings)
        self.pushButtonAdd.clicked.connect(self.add_modules_ui_slot)
        self.pushButtonRemove.clicked.connect(self.remove_module_slot)  # type: ignore
        self.rteTabWidget.currentChanged.connect(self.rte_tab_widget_switch_slot)
        self.actionUndo.triggered.connect(self.undo_slot)
        self.actionRedo.triggered.connect(self.redo_slot)
        self.action_import_os_cfg.triggered.connect(self.import_os_cfg_slot)
        self.action_export_os_cfg.triggered.connect(self.export_os_cfg_slot)
        self.actionToolsSetting.triggered.connect(self.on_general_clicked_slot)

    def on_general_clicked_slot(self):
        if self.general is None or not self.general.isVisible():
            self.general = ConfigratorGeneral(
                self.slot_call_back, self.save_cycle, self.periodic_save_setting, self.update_project_save_timer
            )
            self.general.show()
        else:
            self.general.raise_()
            self.general.activateWindow()
        pass

    def check_secondary_module_enabled(self, module):
        result = True
        result = self.slot_call_back("get_secondary_module_enabled_state", module)
        if result is False:
            self.message_reply = QMessageBox.information(
                self, "Notice", f"Please add {module} module.", QMessageBox.StandardButton.Ok
            )
        return result

    def secondary_menu_slot(self, group_name: str, tab_name: str):
        """slot function for secondary menu of ecum module"""

        secondary_menu_cfg_of_tab = self.secondary_menu_cfg[group_name][tab_name]
        for module_name in secondary_menu_cfg_of_tab["tab_dependency_module_list"]:
            result = self.check_secondary_module_enabled(module_name)
            if result is False:
                return
        self.secondary_menu.show_tab(tab_name, secondary_menu_cfg_of_tab)

    def undo_slot(self):
        module_name = self.bswTabWidget.tabText(self.bswTabWidget.currentIndex())
        self.slot_call_back("bsw_editor_undo_slot", module_name)

    def redo_slot(self):
        module_name = self.bswTabWidget.tabText(self.bswTabWidget.currentIndex())
        self.slot_call_back("bsw_editor_redo_slot", module_name)

    def init_gui_secondary_menu(self):
        self.secondary_menu_cfg = self.slot_call_back("get_secondary_menu_cfg")
        if hasattr(self, "toolBox"):
            for _ in range(self.secondary_menu_widget.layout().count()):
                self.secondary_menu_widget.layout().takeAt(0)
        self.toolBox = QToolBox()
        self.secondary_menu_widget.layout().addWidget(self.toolBox)
        self.toolBox.setMinimumSize(QSize(200, 200))
        self.toolBox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolBox.setStyleSheet(
            """
        QToolBox::tab {
            font-weight: bold;
        }
        """
        )

        for group_name, value in self.secondary_menu_cfg.items():
            widget_var_name = f"sec_{group_name.replace(' ', '_')}_widget".lower()
            group_widget = QWidget()
            setattr(self, widget_var_name, group_widget)
            group_layout = QVBoxLayout()
            group_widget.setLayout(group_layout)
            self.toolBox.addItem(group_widget, group_name.capitalize())

            for button_name, value_detail in value.items():
                button_var_name = f"sec_{button_name.replace(' ', '_')}_button".lower()
                button = QPushButton(button_name)
                setattr(self, button_var_name, button)
                group_layout.addWidget(button)
            spacer = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
            group_layout.addItem(spacer)
        spacer = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.secondary_menu_widget.layout().addItem(spacer)

    def init_properties_tab_widget(self):

        layout_tab_status = QVBoxLayout(self.tabStatus)
        self.table_widget_status = QTableWidget()
        layout_tab_status.addWidget(self.table_widget_status)
        layout_tab_definition = QVBoxLayout(self.tabDefinition)
        self.table_widget_definition = QTableWidget()
        layout_tab_definition.addWidget(self.table_widget_definition)

    def update_mainwindow_action_state(self):
        self.centralwidget.setEnabled(True)
        self.menuCodeGen.setEnabled(True)
        self.actionToolsSetting.setEnabled(True)
        self.actionSave.setEnabled(True)
        self.actionSave_As.setEnabled(True)
        self.actionProject_Setting.setEnabled(True)
        self.actionTaskAnalysis.setEnabled(True)
        self.actionJitterOpt.setEnabled(True)
        self.actionOpen.setEnabled(True)
        self.actionNew.setEnabled(False)
        self.actionImport.setEnabled(True)
        self.actionExport.setEnabled(True)
        self.menuOs_Configuration.setEnabled(True)
        self.action_import_os_cfg.setEnabled(True)
        self.action_export_os_cfg.setEnabled(True)
        self.user_module_menu.setEnabled(True)

    def _init_finish(self):
        self.slot_call_back("get_vcos_version", result_callback=self.update_version)

    def update_version(self, version):
        self.vcos_version = version

    def send_status_to_daemon(self, status):
        if not self.status_queue:
            return
        logger.debug(f"Sending status {status}")
        self.status_queue.put(status)

    def bsw_rte_switch_tab_solt(self, index):
        """Rte Edit shows TaskMapping by default."""
        if self.tabWidget.tabText(index) == "VCOS RTE":
            prev_rte_tab_name = None
            is_rte_parse_new_dict = self.is_rte_parse_new_dict()
            self.rteTabWidget.setCurrentIndex(0)
            # for group_name, value in self.secondary_menu_cfg.items():
            #     for button_name, value_detail in value.items():
            #         button_var_name = f"sec_{button_name.replace(' ', '_')}_button".lower()
            #         button = getattr(self, button_var_name)
            #         button.setEnabled(False)
        elif self.tabWidget.tabText(index) == "VCOS BSW":
            prev_rte_tab_name = self.rteTabWidget.tabText(self.rte_tab_prev_index)
            self.rte_tab_prev_index = 0
            is_rte_parse_new_dict = False
            for group_name, value in self.secondary_menu_cfg.items():
                for button_name, value_detail in value.items():
                    button_var_name = f"sec_{button_name.replace(' ', '_')}_button".lower()
                    if button_var_name in ["sec_ecu_management_button"]:
                        continue
                    button = getattr(self, button_var_name)
                    button.setEnabled(True)
        previous_tab_name = self.autosar_tab_name
        self.autosar_tab_name = self.tabWidget.tabText(index)
        self.slot_call_back(
            "vcos_bsw_rte_switch_tab_solt",
            previous_tab_name,
            prev_rte_tab_name,
            is_rte_parse_new_dict,
            result_callback=self.update_mapping_show,
        )

    def rte_tab_widget_switch_slot(self, index):
        next_tab_name = self.rteTabWidget.tabText(index)
        prev_tab_name = self.rteTabWidget.tabText(self.rte_tab_prev_index)
        self.rte_tab_prev_index = index

        self.slot_call_back(
            "rte_tab_widget_currentChanged_action",
            next_tab_name,
            prev_tab_name,
            result_callback=self.update_mapping_show,
        )

    def update_mapping_data_status(self, mapping_data_info):
        if "is_prev_mapping_data_updated" not in mapping_data_info:
            return
        prev_mapping = mapping_data_info["prev_mapping"]
        if prev_mapping == "task":
            self.rte_edit_ui.is_task_mapping_data_updated = mapping_data_info["is_prev_mapping_data_updated"]
        elif prev_mapping == "data":
            self.rte_edit_ui.is_data_mapping_data_updated = mapping_data_info["is_prev_mapping_data_updated"]
        elif prev_mapping == "serv":
            self.rte_edit_ui.is_service_mapping_data_updated = mapping_data_info["is_prev_mapping_data_updated"]
        elif prev_mapping == "port":
            self.rte_edit_ui.is_port_mapping_data_updated = mapping_data_info["is_prev_mapping_data_updated"]

    def update_mapping_show(self, mapping_data_info):
        self.update_mapping_data_status(mapping_data_info)
        for mapping_name, value in mapping_data_info.items():
            if mapping_name == "Task Mapping":
                self.rte_edit_ui.task_mapping_ui.update_task_mapping_ui({"all"}, value)
            elif mapping_name == "Data Mapping":
                self.rte_edit_ui.data_mapping_ui.update()
            elif mapping_name == "Service Mapping":
                self.rte_edit_ui.service_mapping_ui.update()
            elif mapping_name == "Port Mapping":
                self.rte_edit_ui.port_mapping_ui.update()

    def remove_module_slot(self):
        self.remove_message_box = QMessageBox.question(
            self,
            "Confirm module removal",
            "Are you sure that you want to remove the following modules ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        selected_module_list = []
        self.treeWidgetOverview: QTreeWidget
        for item in self.treeWidgetOverview.selectedItems():
            selected_module_list.append(item.text(0))
        if self.remove_message_box == QMessageBox.Yes:
            # 检查依赖关系，提示用户依赖关系信息
            dependency_dict = self.slot_call_back("get_dependency_modules", selected_module_list)
            if self.show_module_dependency_message(dependency_dict) == QMessageBox.StandardButton.Yes:
                for dependent_module_list in dependency_dict.values():
                    for depent_module in dependent_module_list:
                        selected_module_list.append(depent_module)

            self.slot_call_back(
                "remove_modules", selected_module_list, result_callback=self.over_view_ui.update_overview
            )

    def show_module_dependency_message(self, dependency_dict: dict):
        message_box_reply = None
        if dependency_dict:
            dependent_info = "The module you choose to delete has the following dependencies: \n"
            for module_name, dependency_modules in dependency_dict.items():
                dependent_info += f"\t{module_name} is dependent on {dependency_modules}\n"
            dependent_info += "Click ok to delete the dependency on the selected module, otherwise click no."
            message_box_reply = QMessageBox.information(
                self,
                "Exist module dependency",
                dependent_info,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

        return message_box_reply

    def show_vcos_project_information_slot(self):
        self.slot_call_back(
            "project_setting_action",
            "",
            result_callback=self.create_proj_setting,
        )

    def _register_slot_callback(self, callback: Callable):
        self.slot_call_back = callback
        self.rte_edit_ui.port_mapping_ui.set_callback(callback)
        self.rte_edit_ui.service_mapping_ui.set_callback(callback)
        self.rte_edit_ui.data_mapping_ui.set_callback(callback)
        self.rte_edit_ui.task_mapping_ui.set_callback(callback)
        self.over_view_ui.set_callback(callback)
        self.validation_ui.set_callback(callback)
        self.find_table_view.set_callback(callback)
        self.secondary_menu.set_callback(callback)

    def after_import_asw(self, illegal_files: list = []):
        if len(illegal_files):
            for file_path in illegal_files:
                logger.warning(f"{file_path} is illegal to import!")
            self.hint_info_dialog = HintInfoListDialog(
                "The fllowing files are illegal to import, please check it.", illegal_files, self
            )
        # TODO: ALL: 导入asw后需要进行的操作请写在此处
        self.slot_call_back("update_flatextract_data_mapping_after_import")
        self.rte_edit_ui.task_mapping_ui.update_task_mapping_ui({"all"})
        self.rte_edit_ui.port_mapping_ui.update_tree()
        self.slot_call_back("update_port_mapping_table_after_import_asw")
        self.rte_edit_ui.service_mapping_ui.update_tree()
        self.slot_call_back("update_service_mapping_table_after_import_asw")

    def after_import_dbc_ldf(self, module_set):
        self.slot_call_back("update_flatextract_data_mapping_after_import")
        self.slot_call_back(
            "bsw_editor_update_bsw_modules", module_set, result_callback=self.over_view_ui.update_bsw_modules_view
        )

    def update_overview_ui(self, args):
        if self.input_configurator_project_file_path is None:
            self.over_view_ui.update_overview(args)

    def import_asw_arxml_slot(self):
        import_asw_arxml_ui = ImportASWARXMLUI()
        asw_arxml_folder = import_asw_arxml_ui.open_the_input_files_assistant_asw()
        if len(asw_arxml_folder) == 0:
            return
        self.slot_call_back(
            "parser_asw_arxml_and_update_arxml_action", asw_arxml_folder, result_callback=self.after_import_asw
        )

    def import_files_solt(self):
        self.stop_project_save_timer()
        self.import_files_ui = ImportFilesUI(
            self.slot_call_back, self.over_view_ui, self.after_import_dbc_ldf, self.start_project_save_timer
        )

    def import_arxml_solt(self):
        """导入asw, bsw, mcal arxml 文件"""
        self.stop_project_save_timer()
        self.import_arxml_ui = ImportArxmlUi(
            self.slot_call_back, self.over_view_ui, self.after_import_asw, self.start_project_save_timer
        )
        self.import_arxml_ui.show()

    def export_ecuc_arxml_slot(self):
        """这里处理导出mcal与bsw模块arxml动作"""
        _, added_module_list = self.slot_call_back("get_current_project_module_info")
        self.export_ecuc_arxml_ui = ExportEcucArxmlUi(added_module_list, self.slot_call_back)
        self.export_ecuc_arxml_ui.show()

    def import_os_cfg_slot(self):
        """导入OS配置的excel文件"""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_name, _ = file_dialog.getOpenFileName(self, "Import Os Configuration", "", filter=("*.xlsx"))
        if not file_name:
            return
        self.slot_call_back("import_os_cfg", file_name, self, self.over_view_ui)

    def export_os_cfg_slot(self):
        """导出OS配置的excel文件"""
        file_name, _ = QFileDialog.getSaveFileName(self, "Export Os Configuration", "", filter=("*.xlsx"))
        if not file_name:
            return
        self.slot_call_back("export_os_cfg", file_name)

    def new_vcos_project_config_file_slot(self):
        """
        信号触发的槽函数调用函数逻辑层获取工程配置
        """
        if not self.new_project_ui:
            self.new_project_ui = NewProjectUI({}, self.slot_call_back, self)
        self.new_project_ui.show()

    def select_open_vcos_project_config_file_slot(self, project_path=None):
        """
        打开工程文件
        """

        def choose_default_project(arg):
            self.choose_project(project_path)

        if self.studio_open_state:
            self.stop_project_save_timer()
            reply = QMessageBox.question(
                self,
                "Reopen",
                "Saving project before close?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if reply == QMessageBox.Yes:
                self.slot_call_back("validation_save_logs")
                self.slot_call_back("validation_save_ignored_logs")
                self.slot_call_back("save_action", "", True, result_callback=choose_default_project)

            if reply == QMessageBox.No:
                self.choose_project(project_path)
            else:
                return None
        else:
            self.choose_project(project_path)

    def choose_project(self, project_path=None):
        input_project_file_path = project_path
        if not project_path:
            input_project_file_path, _ = QFileDialog.getOpenFileName(
                self, "vcos", "../../", "vcosproject Files (*.vcosproject)"
            )
        if not input_project_file_path:
            return
        if not os.path.exists(input_project_file_path):
            QMessageBox.critical(
                self,
                "Path Error",
                f"The path does not exist: {input_project_file_path}.\nPlease check if the path is correct.",
                QMessageBox.Ok,
            )
            self._update_recent_file_actions()
            return
        if self.studio_open_state:
            self.slot_call_back("delete_file_lock_action")
        reult = self.slot_call_back("add_file_lock_action", input_project_file_path)
        if reult is False:
            self.file_lock_notify(input_project_file_path)
            return
        if self.studio_open_state:
            logger.log_clear()
            self.tabWidget.setCurrentIndex(0)
            self.tabWidget_2.setCurrentIndex(0)
            self.bswTabWidget.setCurrentIndex(0)
            self.secondary_menu.close_secondary_menu_tabs()
            self.over_view_ui.overview_remove_modules(set(self.over_view_ui.bsw_overview_tab_set))
            self.validation_ui.validation_model.clear_model_data()

        self.open_project_slot(input_project_file_path)
        self.status["project_info"]["path"] = input_project_file_path
        self.status["status"] = "open"
        self.send_status_to_daemon(self.status)
        self.start_project_save_timer()

    def auto_open_project(self, project_file_path):
        if project_file_path == "":
            return
        if os.path.exists(project_file_path) is False:
            logger.warning(f"{project_file_path} is not existed.")
            return
        if project_file_path.split(".")[-1] != "vcosproject":
            logger.warning(f"{project_file_path} must be vcosproject.")
            return

        if self.studio_open_state:
            self.slot_call_back("delete_file_lock_action")
        reult = self.slot_call_back("add_file_lock_action", project_file_path)
        if reult is False:
            self.file_lock_notify(project_file_path)
            return
        if self.studio_open_state:
            logger.log_clear()
            self.tabWidget.setCurrentIndex(0)
            self.tabWidget_2.setCurrentIndex(0)
            self.bswTabWidget.setCurrentIndex(0)
            self.over_view_ui.update_overview([{}, {}])
            self.validation_ui.validation_model.clear_model_data()
        self.open_project_slot(project_file_path)
        self.status["project_info"]["path"] = project_file_path
        self.status["status"] = "open"
        self.send_status_to_daemon(self.status)
        self.start_project_save_timer()

    def open_project_slot(self, project_file_path):
        cfg_check, upgrade_check, compatibility_info = self.slot_call_back("open_project", project_file_path)
        if compatibility_info is None:
            logger.debug(f"{cfg_check} {upgrade_check} {compatibility_info}")
            self.project_check_qmessagebox = QMessageBox.critical(
                self,
                "critical",
                "Please check whether the project file is correct, \nFor more information, "
                "see: components/configs/configurator_plug_in/components_plug_in_cfg.json",
                QMessageBox.Ok,
            )
            return
        self.upgrade_result = upgrade_check
        exc: bool = self.cfg_check_func(cfg_check)
        if not exc:
            return
        if self.upgrade_result:
            # not latest version yet
            logger.info("VCOS supports to upgrade")
            self.slot_call_back(
                "load_project_config_action", project_file_path, result_callback=self.open_project_call_back
            )
        else:
            # already latest version
            logger.info("No Bsw modules need to be upgraded in current version")
            self.slot_call_back(
                "load_project_config_action", project_file_path, result_callback=self.load_project_config_callback
            )
        self.update_mainwindow_action_state()
        self.studio_open_state = True
        self.recent_files_manager.add_recent_file(project_file_path)
        self._update_recent_file_actions()
        self.project_file_path = project_file_path
        self.setWindowTitle(f"VCOS Studio({self.studio_version})  {self.project_file_path}")

    def update_user_plugin_info(self):
        self.plugin_manager_dialog.update_user_plugin_sysinfo(
            sys_info_class=get_sys_info_class(),
            bsw_autosar_class=get_autosar_bsw_class(),
            sys_target_dict=get_sys_target_dict(),
            all_module_list=get_all_module_list(),
        )

    def load_project_config_callback(self, result):
        self.init_gui_secondary_menu()
        self.post_init_secondary_menu_signal_slot()
        self.over_view_ui.update_overview(result)
        self.update_user_plugin_info()

    def open_project_call_back(self, result):
        """version upgrade"""
        message = QMessageBox.information(
            self, "studio upgrade", self.upgrade_result, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if message == QMessageBox.Yes:
            logger.info("Execution of upgrade is in progress")
            self.slot_call_back(
                "studio_version_upgrade_action",
                self.project_file_path,
                result_callback=self.load_project_config_callback,
            )
        else:
            self.prompt_compatibility(result)

    def prompt_compatibility(self, result):
        """提示兼容性问题，返回升级界面"""
        info = QMessageBox.information(
            self,
            "Information",
            "In order to avoid problems of compatibility,\n\tplease complete upgrade firstly.",
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Ok,
        )
        if info == QMessageBox.Ok:
            self.slot_call_back(
                "studio_version_upgrade_action",
                self.project_file_path,
                result_callback=self.over_view_ui.update_overview,
            )
        else:
            logger.info("Vcos Studio does not support loading projects without being upgraded.")
            self.mainwindow_action_without_upgrade()

    def mainwindow_action_without_upgrade(self):
        """process logic of mainwindow without upgrade"""
        self.studio_open_state = False
        # centralwidget setenabled
        self.centralwidget.setEnabled(False)
        # actions bellow menuFile setenabled
        self.actionOpen.setEnabled(True)
        self.actionSave.setEnabled(False)
        self.actionSave_As.setEnabled(False)
        self.actionImport.setEnabled(False)
        self.actionExport.setEnabled(False)
        self.action_import_os_cfg.setEnabled(False)
        self.action_export_os_cfg.setEnabled(False)
        # menuCodeGen setenabled
        self.menuCodeGen.setEnabled(False)
        self.actionToolsSetting.setEnabled(False)
        # menuProject setenabled
        self.actionProject_Setting.setEnabled(False)
        self.actionTaskAnalysis.setEnabled(False)
        logger.log_clear()
        self.over_view_ui.update_overview([{}, {}])
        self.slot_call_back("delete_file_lock_action")

    def cfg_check_func(self, cfg_check):
        """check configurations missing or not"""
        if cfg_check == {}:
            return True
        info: str = "No following directories exist, please create before reopening!\n\n"
        num: int = 1
        for key, value in cfg_check.items():
            info = info + f"{num}. {key}" + ":\n" + f"{value}" + "\n"
            num += 1
        cfg_check = QMessageBox.critical(self, "Notice", info, QMessageBox.Ok)
        return False

    def file_lock_notify(self, project_file_path):
        result = QMessageBox.warning(
            None,
            "Title",
            "1. If the Studio has been opened, please close it before executing.              \n"
            + "2. If the Studio is not opened, please delete the vcos_studio.lock~ file!        ",
            QMessageBox.Yes,
        )
        if result == QMessageBox.Yes or result == QMessageBox.close:
            return

    def save_vcos_project_config_file_slot(self, closed=False, code_gen=False):
        """
        保存工程文件按钮槽函数
        """
        self.slot_call_back("validation_save_logs")
        self.slot_call_back("validation_save_ignored_logs")
        self.slot_call_back(
            "save_action",
            " ",
            True,
            result_callback=lambda: self.over_view_ui.update_bsw_modules_view_switch(["Os", "Rte"]),
        )

    def save_as_vcos_project_slot(self):
        """另存为槽函数"""
        # step1：更新工程文件配置
        if self.project_file_path == "":
            # 新建工程需要从全局变量中获取工程文件路径信息
            self.project_file_path = self.slot_call_back("get_prj_path")
            # 获取另存工程的默认目录
        defalut_prj_path = os.path.normpath(os.path.join(self.project_file_path, "..", "..", ".."))
        self.save_as_vcos_project_ui = SaveAsProjectUI(defalut_prj_path, self.slot_call_back, self)
        self.save_as_vcos_project_ui.show()

    def generate_vcos_c_code_slot(self):
        """目前generate直接调用generate_c_code接口生成所有代码，后面需要在界面触发回调执行生成动作"""
        """支持获取UI界面信息并显示"""
        self.slot_call_back("get_generate_configuration", result_callback=self.update_bsw_generate_ui)

    def update_bsw_generate_ui(self, module_list):
        """更新Generate界面显示"""
        support_generate_module_dict = dict(module_list[0])
        enabled_generate_module_list = list(module_list[1])
        generation_limit = str(module_list[2])
        if not self.bsw_generate_ui:
            self.bsw_generate_ui = BSWGeneratorWidget(
                self, {}, enabled_generate_module_list, generation_limit, self.slot_call_back
            )
        # add module新增新的模块后需要更新codegen或者validaton列表显示
        self.bsw_generate_ui.update_ui_module_list(support_generate_module_dict, enabled_generate_module_list)
        self.bsw_generate_ui.show()

    def swc_generator_vcos_c_code_slot(self):
        self.slot_call_back("get_vcos_swc_name_list_action", result_callback=self.update_swc_generate_ui)

    def update_swc_generate_ui(self, swc_list):
        if swc_list == []:
            self.swc_generate_ui = SWCGeneratorWidget(swc_list, self.slot_call_back, False)
        else:
            self.swc_generate_ui = SWCGeneratorWidget(swc_list, self.slot_call_back)
        self.swc_generate_ui.show()

    def get_validation_config_slot(self):
        self.slot_call_back("get_validation_configuration", result_callback=self.update_bsw_validation_ui)

    def update_bsw_validation_ui(self, module_list):
        """更新validation配置界面显示"""
        support_validate_module_list = dict(module_list[0])
        enabled_validate_module_list = list(module_list[1])
        if not self.validation_cfg_ui:
            self.validation_cfg_ui = ValidationCFGUI(
                self, support_validate_module_list, enabled_validate_module_list, self.slot_call_back
            )
        # add module新增新的模块后需要更新codegen或者validaton列表显示
        self.validation_cfg_ui.update_ui_module_list(support_validate_module_list, enabled_validate_module_list)
        self.validation_cfg_ui.show()
        pass

    def update_vcos_service_arxml_slot(self):
        self.slot_call_back("update_action", result_callback=self._update_mapping_ui_tree)

    def _update_mapping_ui_tree(self, return_tag: dict):
        if self.rte_edit_ui and self.rte_edit_ui.service_mapping_ui:
            self.rte_edit_ui.service_mapping_ui.update()
        if self.rte_edit_ui and self.rte_edit_ui.port_mapping_ui:
            self.rte_edit_ui.port_mapping_ui.update()
        if self.rte_edit_ui and self.rte_edit_ui.task_mapping_ui:
            self.rte_edit_ui.task_mapping_ui.update_task_mapping_ui(return_tag)

    def update_project_settings(self):
        self.slot_call_back(
            "project_setting_action",
            result_callback=self.create_proj_setting,
        )

    def create_proj_setting(self, result):
        """
        工程配置Instance Object
        """
        if not self.project_setting:
            self.project_setting = ProjectConfigUI(result, self.slot_call_back, self)
        else:
            self.project_setting.sys_info_dict = result["project_setting_action"]
            self.project_setting.show_init()
        self.project_setting.show()

    def update_project(self, result):
        """
        界面返回更新配置Update Config
        """
        call_back = list(result.keys())[0]
        call_back_config = result[call_back]
        self.slot_call_back(call_back, call_back_config)
        pass

    def add_modules_ui_slot(self):
        (
            all_module_list,
            added_module_dict,
            level_module_dict,
        ) = self.slot_call_back("add_modules_ui")
        self.module_manage_ui = ModuleManageUi(
            all_module_list, added_module_dict, level_module_dict, self.over_view_ui, self.slot_call_back, self
        )
        self.module_manage_ui.open()

    def closeEvent(self, event):
        if self.studio_open_state is False:
            self.status["status"] = "close"
            self.send_status_to_daemon(self.status)
            self.app.quit()
            return
        self.stop_project_save_timer()
        self.reply = QMessageBox.question(
            self,
            "Close",
            "Do you want to save the project?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        self.stop_project_save_timer()
        if self.reply == QMessageBox.Yes:
            event.accept()
            self.slot_call_back("validation_save_logs")
            self.slot_call_back("validation_save_ignored_logs")
            self.slot_call_back("save_action", " ", True, result_callback=self.close_studio)
        elif self.reply == QMessageBox.No:
            event.accept()
            self.close_studio()
        elif self.reply == QMessageBox.Cancel:
            event.ignore()
            self.start_project_save_timer()

    def close_studio(self):
        self.slot_call_back("delete_file_lock_action")
        self.slot_call_back("project_close_handle_action", result_callback=self.quit_studio)

    def quit_studio(self):
        self.status["status"] = "close"
        self.send_status_to_daemon(self.status)
        self.app.quit()

    def task_analysis_slot(self):
        self.slot_call_back("task_analysis_ui", result_callback=self.show_task_analysis_ui)

    def show_task_analysis_ui(self, task_ui_info):
        self.task_analysis_ui = TaskAnalysisUI(task_ui_info, self.slot_call_back, self)
        self.task_analysis_ui.show()

    def __is_bsw_module_updated(self, mod, op_stack) -> bool:
        return mod in op_stack and (not op_stack[mod].isClean())

    def __reset_dependency(self, dependent_bsw_module, op_stack):
        self.rte_edit_ui.is_task_mapping_data_updated = False
        self.rte_edit_ui.is_data_mapping_data_updated = False
        self.rte_edit_ui.is_port_mapping_data_updated = False
        self.rte_edit_ui.is_service_mapping_data_updated = False
        for mod in dependent_bsw_module:
            if mod not in op_stack:
                continue
            op_stack[mod].setClean()

    def is_rte_parse_new_dict(self):
        # 判断依赖的几个flag是否有更新
        RTE_DEP_BSW_MODULE = ["Rte", "Os", "EcuC", "Com"]
        op_stack = get_module_stack_dict()
        if not isinstance(op_stack, dict):
            return True

        if (
            self.rte_edit_ui.is_task_mapping_data_updated
            or self.rte_edit_ui.is_data_mapping_data_updated
            or self.rte_edit_ui.is_port_mapping_data_updated
            or self.rte_edit_ui.is_service_mapping_data_updated
        ):
            self.__reset_dependency(RTE_DEP_BSW_MODULE, op_stack)
            return True

        is_updated = False
        for mod in RTE_DEP_BSW_MODULE:
            if self.__is_bsw_module_updated(mod, op_stack):
                is_updated = True
                break
        # reset flag
        self.__reset_dependency(RTE_DEP_BSW_MODULE, op_stack)
        return is_updated

    def start_project_save_timer(self):
        if self.save_timer_flag is False:
            return

        if self.periodic_save_setting is True:
            self.save_timer.start(int(self.save_cycle) * 1000)

    def stop_project_save_timer(self):
        if self.save_timer_flag is False:
            return
        if self.save_timer:
            self.save_timer.stop()

    def init_project_save_timer(self):
        if self.save_timer_flag is False:
            return
        self.save_timer = QTimer(self)
        self.save_timer.timeout.connect(self.periodic_save_configuration_action)

    def periodic_save_configuration_action(self):
        self.slot_call_back("periodic_save_configuration_action")

    def update_project_save_timer(self, save_cycle, periodic_save_setting):
        self.save_cycle = save_cycle
        self.periodic_save_setting = periodic_save_setting
        self.stop_project_save_timer()
        self.start_project_save_timer()

    def jitter_auto_optimization_slot(self):
        self.jitter_opt_dialog = JitterOptimizationUI(self.slot_call_back, self)
        self.jitter_opt_dialog.open()
