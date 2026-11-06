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
from PySide6.QtWidgets import (
    QMessageBox,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QDialogButtonBox,
    QFileDialog,
    QDialog,
    QListView,
    QTreeView,
    QAbstractItemView,
)
from func_module.module_management.module_management import ModuleManagement
from func_module.module_management.user_plugin_manager.user_plugin_manager import UserPluginManager


class PluginManagerDialog(QDialog):

    def __init__(self, parent=None, slot_call_back=None):
        super(PluginManagerDialog, self).__init__(parent)
        self.setWindowTitle("Plugin Manager")
        self.resize(500, 400)
        self.slot_call_back = slot_call_back

    def update_user_plugin_sysinfo(self, sys_info_class, bsw_autosar_class, sys_target_dict, all_module_list):
        self.user_plugin_manager = UserPluginManager(
            sys_info_class, bsw_autosar_class, sys_target_dict, all_module_list
        )
        self.plugin_dirs = getattr(sys_info_class, "import_plugin_path_list", []) if sys_info_class else []
        self.user_plugin_manager.handle_valid_plugin_sys_cfg(self.plugin_dirs)

    def pre_init_ui(self):
        if self.layout() is not None:
            return  # 如果已有布局，则直接返回
        # 列表视图显示插件目录
        main_layout = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.addItems(self.plugin_dirs)
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        main_layout.addWidget(self.list_widget)

        # 按钮布局
        button_layout = QHBoxLayout()

        self.add_button = QPushButton("Add Plugin Directory")
        self.add_button.clicked.connect(self.add_plugins)
        button_layout.addWidget(self.add_button)

        self.remove_button = QPushButton("Remove Selected Directory")
        self.remove_button.clicked.connect(self.remove_selected)
        button_layout.addWidget(self.remove_button)

        main_layout.addLayout(button_layout)

        # 对话框按钮（OK 和 Cancel）
        self.dialog_buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.dialog_buttons.accepted.connect(self.handle_accept)
        self.dialog_buttons.rejected.connect(self.reject)
        main_layout.addWidget(self.dialog_buttons)

        self.setLayout(main_layout)

    def add_plugins(self):
        """使用 QFileDialog 选择多个目录"""
        dialog = QFileDialog(self)
        dialog.setWindowTitle("Select Plugin Directories")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)

        for view in dialog.findChildren(QListView) + dialog.findChildren(QTreeView):
            view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        if dialog.exec_():
            selected_dirs = dialog.selectedFiles()
            added_dirs = []
            duplicate_dirs = []
            invalid_dirs = []

            for dir_path in selected_dirs:
                if os.path.isdir(dir_path):
                    if dir_path not in self.plugin_dirs:
                        validation_errors = self.user_plugin_manager._validate_plugin_configuration(dir_path)
                        if not validation_errors:
                            added_dirs.append(dir_path)
                        else:
                            invalid_dirs.append((dir_path, validation_errors))  # 存储路径及对应的错误信息
                    else:
                        duplicate_dirs.append(dir_path)
                else:
                    invalid_dirs.append((dir_path, {"error": "Not a valid directory"}))

            # 组合有效和无效目录信息
            valid_dirs_str = "\n".join(added_dirs)
            invalid_messages = "\n".join([f"{path}: {errors}" for path, errors in invalid_dirs])

            if added_dirs and invalid_dirs:
                summary_message = (
                    f"Valid directories added:\n{valid_dirs_str}\n\nInvalid directories:\n{invalid_messages}"
                )
                QMessageBox.warning(self, "Warning", summary_message)
            elif added_dirs:
                summary_message = f"The following directories are valid:\n{valid_dirs_str}"
                QMessageBox.information(self, "Success", summary_message)
            elif invalid_dirs:
                error_messages = "\n".join([f"{path}: {errors}" for path, errors in invalid_dirs])
                summary_message = f"The following directories are invalid:\n{error_messages}"
                QMessageBox.critical(self, "Error", summary_message)

            # 向用户确认是否添加有效的目录
            if added_dirs:
                reply = QMessageBox.question(
                    self,
                    "Confirm Addition",
                    f"Do you want to proceed with adding the following valid directories?\n{valid_dirs_str}",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )

                if reply == QMessageBox.Yes:
                    for dir_path in added_dirs:
                        self.plugin_dirs.append(dir_path)
                        self.list_widget.addItem(dir_path)
                    self.user_plugin_manager.handle_valid_plugin_sys_cfg(added_dirs)

    def remove_selected(self):
        """移除选中的目录并确认"""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "No items selected for removal.")
            return

        # 获取待删除的路径列表
        paths_to_remove = [item.text() for item in selected_items]
        plugin_module_info = ModuleManagement.get_module_info_by_spec_path(set(paths_to_remove))
        # 调用拦截函数
        intercepted_modules = self.user_plugin_manager.already_added_module_from_plugin(plugin_module_info.values())
        if intercepted_modules:
            existing_modules = "\n".join(intercepted_modules)
            QMessageBox.critical(
                self,
                "Error",
                f"Some modules are protected and cannot be removed.\n\n"
                f"Intercepted modules:\n{existing_modules}\n\n"
                "Please remove the modules first.",
            )
            return

        # 弹出确认对话框
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            "Are you sure you want to remove the selected directories?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            for item in selected_items:
                dir_path = item.text()
                if dir_path in self.plugin_dirs:
                    self.plugin_dirs.remove(dir_path)
                self.list_widget.takeItem(self.list_widget.row(item))  # 从列表中移除
            for dir in list(plugin_module_info.keys()):
                self.user_plugin_manager._remove_plugin_sys_cfg(dir)

    def handle_accept(self):
        """在点击 OK 时处理插件目录更新"""
        super(PluginManagerDialog, self).accept()
        self.slot_call_back("update_plugin_dir_list", self.plugin_dirs)
        self.user_plugin_manager.update_vcos_project_datamanagement()

    def _show_import_results(self, added_dirs, duplicate_dirs, invalid_dirs):
        """展示导入结果"""
        feedback = ""
        if added_dirs:
            feedback += "Successfully imported plugin directories:\n" + "\n".join(added_dirs) + "\n"
        if duplicate_dirs:
            feedback += (
                "The following plugin directories already exist and were skipped:\n" + "\n".join(duplicate_dirs) + "\n"
            )
        if invalid_dirs:
            feedback += "The following selected paths are not valid directories:\n" + "\n".join(invalid_dirs) + "\n"

        if feedback:
            QMessageBox.information(self, "Import Results", feedback)

    def get_plugin_dirs(self):
        """返回当前的插件目录列表"""
        return self.plugin_dirs
