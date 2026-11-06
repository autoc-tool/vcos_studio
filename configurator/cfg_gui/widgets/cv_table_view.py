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
from typing import Optional
from PySide6.QtCore import Qt, QAbstractItemModel, QItemSelectionModel
from PySide6.QtGui import QKeySequence, QAction, QShortcut
from PySide6.QtWidgets import QApplication, QTableView, QWidget, QMenu
from func_module.health_monitor.logger import logger

COLUMN_0 = 0  # 第0列


class CvTableView(QTableView):

    def __init__(self, parent: Optional[QWidget] = None, model=None, callback=None) -> None:
        super().__init__(parent)
        self.callback = callback
        QShortcut(QKeySequence(Qt.Modifier.CTRL + Qt.Key.Key_C), self, self.copy_slot)
        QShortcut(QKeySequence(Qt.Modifier.CTRL + Qt.Key.Key_V), self, self.paste_slot)

    def setModel(self, model: QAbstractItemModel) -> None:
        super().setModel(model)
        self.selectionModel().selectionChanged.connect(self.selection_changed_slot)

    def selection_changed_slot(self):
        """
        Deselct cells in different columns.
        Limit multi selection to one column
        """
        selected_indexs = self.selectedIndexes()
        if selected_indexs:
            col = selected_indexs[0].column()
            for idx in selected_indexs:
                if idx.column() != col:
                    self.selectionModel().select(idx, QItemSelectionModel.SelectionFlag.Deselect)

    def copy_slot(self):
        selected_indexs = self.selectedIndexes()
        if selected_indexs:
            index = selected_indexs[0]
            logger.info(f"Copy '{index.data()}' from row: {index.row()}, column: {index.column()}")
            clipboard = QApplication.clipboard()
            clipboard.setText(index.data())

    def paste_slot(self):
        selected_indexs = self.selectedIndexes()
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        for idx in selected_indexs:
            if idx.flags() & Qt.ItemFlag.ItemIsEditable:
                self.model().setData(idx, text, Qt.ItemDataRole.EditRole)
                logger.debug(f"Paste {text} to cell ({idx.row()}, {idx.column()})")
            else:
                logger.debug(f"Cell ({idx.row()}, {idx.column()}) is not editable")

    def contextMenuEvent(self, event):

        self.selected_indexes = self.selectionModel().selectedIndexes()
        self.selected_indexes = [index for index in self.selected_indexes if index.isValid()]

        # # self.right_clicked_index = self.indexAt(event.pos())  # 获取右键菜单所在的点击位置索引
        # self.selected_table_item = self.get_selected_table_item()  # 获取单元格背后的细节
        # self.show_data_dict = self.selected_table_item._container_val_obj[0]

        menu = QMenu(self)

        # Create the click menu
        self.edit_action = QAction("Edit")
        self.set_default_value_action = QAction("Set Default Value")
        self.set_default_value_action.setEnabled(self.set_default_value_status())
        self.set_user_defined_action = QAction("Set User Defined")
        self.remove_user_defined_action = QAction("Remove User Defined")
        self.show_ref_in_basic_editor = QAction("Show Referenced Item In Basic Editor (Tree)")
        self.show_ref_in_basic_editor.setVisible(False)
        self.show_all_ref_configuration_items = menu.addAction(
            "Show all ref configuration items that reference this ref target"
        )
        self.show_all_ref_configuration_items.setVisible(False)

        menu.addAction(self.edit_action)
        menu.addSeparator()
        menu.addAction(self.set_default_value_action)
        menu.addSeparator()
        menu.addAction(self.set_user_defined_action)
        menu.addSeparator()
        menu.addAction(self.remove_user_defined_action)
        menu.addSeparator()
        menu.addAction(self.show_ref_in_basic_editor)
        menu.addSeparator()
        menu.addAction(self.show_all_ref_configuration_items)

        if self.ashes_and_locks() is False:  # outline界面没有可选的item，不展示menu
            return
        self.init_signal_connect_slot()
        # 显示菜单
        menu.exec_(event.globalPos())

    def ashes_and_locks(self):
        if 0 == len(self.selected_indexes):  # outline界面没有可选的item，直接返回
            return False
        # 首先获取第一个被选中item的is_lock和annotation_status
        final_is_lock = self.get_selected_table_item(self.selected_indexes[0])._container_val_obj[0]["is_lock"]
        final_annotation_status = self.get_selected_table_item(self.selected_indexes[0])._container_val_obj[0][
            "annotation_status"
        ]

        for index in self.selected_indexes:
            selected_table_item = self.get_selected_table_item(index)
            show_data_dict = selected_table_item._container_val_obj[0]
            # for循环，与所有被选中item的is_lock和annotation_status比较，但凡有不相同的，
            # final_is_lock直接置True（所有右键menu置灰）
            if final_is_lock != show_data_dict["is_lock"]:
                final_is_lock = True
                break
            if final_annotation_status != show_data_dict["annotation_status"]:
                final_is_lock = True
                break

        if final_is_lock is False:
            if final_annotation_status is False:
                self.edit_action.setEnabled(False)
                self.set_user_defined_action.setEnabled(True)
                self.remove_user_defined_action.setEnabled(False)
                self.set_default_value_action.setEnabled(False)
            elif final_annotation_status is True:
                self.edit_action.setEnabled(True)
                self.set_user_defined_action.setEnabled(False)
                self.remove_user_defined_action.setEnabled(True)
                self.set_default_value_action.setEnabled(self.set_default_value_status())
            else:
                self.edit_action.setEnabled(False)
                self.set_user_defined_action.setEnabled(True)
                self.remove_user_defined_action.setEnabled(False)
                self.set_default_value_action.setEnabled(self.set_default_value_status())
        else:
            self.edit_action.setEnabled(False)
            self.set_user_defined_action.setEnabled(False)
            self.remove_user_defined_action.setEnabled(False)
            self.show_ref_in_basic_editor.setEnabled(False)
            self.show_all_ref_configuration_items.setEnabled(False)
            self.set_default_value_action.setEnabled(False)

    def set_default_value_status(self):

        for index in self.selected_indexes:
            selected_table_item = self.get_selected_table_item(index)
            show_data_dict = selected_table_item._container_val_obj[0]
            if show_data_dict["is_lock"] is True:
                return False
            if show_data_dict["default_value"] is None:
                return False
        return True

    def get_selected_table_item(self, index):

        short_name = self.model().data(self.model().index(index.row(), COLUMN_0))  # 从第0列获取short name

        table_items = self.parent().model.table_items
        for item_index in range(len(table_items)):
            if short_name in next(iter(table_items[item_index][0].container_item)):
                return self.parent().model.table_items[item_index][index.column()]

    def init_signal_connect_slot(self):

        self.set_default_value_action.triggered.connect(lambda: self.set_default_value_slot())
        self.set_user_defined_action.triggered.connect(lambda: self.set_user_defined_slot())
        self.remove_user_defined_action.triggered.connect(lambda: self.remove_user_defined_slot())
        self.show_ref_in_basic_editor.triggered.connect(lambda: self.show_ref_in_basic_editor_slot())
        self.show_all_ref_configuration_items.triggered.connect(
            self.show_all_ref_configuration_items_by_ref_target_slot
        )

    def set_default_value_slot(self):
        for index in self.selected_indexes:
            selected_table_item = self.get_selected_table_item(index)
            show_data_dict = selected_table_item._container_val_obj[0]
            self.model().setData(index, show_data_dict["default_value"])

    def set_user_defined_slot(self):

        for index in self.selected_indexes:
            selected_table_item = self.get_selected_table_item(index)
            show_data_dict = selected_table_item._container_val_obj[0]
            # self.model().setData(index, show_data_dict["default_value"])
            show_data_dict["annotation_status"] = True
            self.user_defined = self.callback(
                "bsw_editor_set_user_defined",
                None,
                show_data_dict["mod_path"],
                show_data_dict["module"],
                show_data_dict["ecuc_path"],
                show_data_dict["tag"],
            )
            self.set_user_defined_action.setEnabled(False)
            self.remove_user_defined_action.setEnabled(True)
            #
            # self.set_enabled(self.line_box, True)
            self.set_default_value_action.setEnabled(self.set_default_value_status())

    def remove_user_defined_slot(self):
        for index in self.selected_indexes:
            selected_table_item = self.get_selected_table_item(index)
            show_data_dict = selected_table_item._container_val_obj[0]
            show_data_dict["annotation_status"] = False
            self.user_defined = self.callback(
                "bsw_editor_remove_user_defined",
                None,
                show_data_dict["mod_path"],
                show_data_dict["module"],
                show_data_dict["ecuc_path"],
                show_data_dict["tag"],
            )
            self.remove_user_defined_action.setEnabled(False)
            self.set_user_defined_action.setEnabled(True)
            # self.set_enabled(self.line_box, False)
            self.set_default_value_action.setEnabled(False)

    def show_ref_in_basic_editor_slot(self):
        self.basic_ui_handler.ecuc_path_jumps_to_ui(self.line_box.text())

    def show_all_ref_configuration_items_by_ref_target_slot(self):

        if self.line_box.text() and "<empty>" != self.line_box.text():
            all_ref_configuration_items_by_ref_target_dict = self.callback(
                "bsw_editor_all_ref_configuration_items_by_ref_target", self.line_box.text()
            )
            self.show_element_usage.fill_reference_target_table_widget(
                "", all_ref_configuration_items_by_ref_target_dict
            )
            if self.show_element_usage.select_reference_target_dialog:
                self.show_element_usage.select_reference_target_dialog.exec()
