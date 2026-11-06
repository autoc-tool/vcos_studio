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
    QAbstractItemView,
    QFileDialog,
    QComboBox,
    QTableWidgetItem,
    QTableWidget,
    QDialog,
    QMessageBox,
    QMenu,
    QCheckBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QCursor
from cfg_gui.bsw_editor.overview_ui import OverViewUI
from cfg_gui.import_file.dbc_editor_ui import EditDBCDetailsUI
from cfg_gui.resources.ui.ui_import_dbc_and_ldf import Ui_Form
from ui_adaptor.ui_interaction.ui_logger import logger

LDF_RELATED_MODULE_LIST = ["EcuC", "Com", "PduR", "LinIf", "LinSM", "ComM", "Nm"]
DBC_RELATED_MODULE_LIST = ["CanNm", "Com", "PduR", "CanIf", "EcuC", "ComM", "Nm", "CanSM"]
CDD_RELATED_MODULE_LIST = ["Dcm", "Dem", "NvM"]


class ImportFilesUI(QDialog, Ui_Form):
    updata_dbc_and_ldf_data_signal = Signal(dict)

    def __init__(self, slot_call_back, overview_ui: OverViewUI, after_import, timer_func):
        super(ImportFilesUI, self).__init__()
        self.after_import = after_import
        self.slot_call_back = slot_call_back
        self.overview_ui = overview_ui
        self.timer_func = timer_func
        self.right_click_menu = None
        self.menu_action_edit = None
        self.menu_click_action = None
        self.ui_init()

    def register_slot_callback(self, callback):
        self.slot_call_back = callback

    def update_widget_then_show(self, info_dict: "dict[str, dict]"):
        self.update_table_widget(info_dict)
        self.show()

    def ui_init(self):
        self.setupUi(self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.pushButtonAddFiles.clicked.connect(self.open_vcos_project_files_slot)
        self.pushButtonRemove.clicked.connect(self.open_vcos_remove_files_slot)
        self.pushButtonApply.clicked.connect(self.open_vcos_pushbutton_apply_slot)
        self.pushButtonReplace.clicked.connect(self.open_vcos_replace_files_slot)
        self.tableWidget.setColumnWidth(0, 150)
        self.tableWidget.setColumnWidth(1, 150)
        self.tableWidget.setColumnWidth(2, 600)
        self.tableWidget.setRowCount(0)
        self.tableWidget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tableWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self.right_click_slot)
        self.tableWidget.itemSelectionChanged.connect(self.check_selection_for_replace_button)
        imported_excel_lsit = self.slot_call_back("get_imported_excel")
        DID_single_signal = (
            Qt.CheckState.Checked if self.slot_call_back("get_single_signal_state") else Qt.CheckState.Unchecked
        )
        self.merge_signal_checkBox.setCheckState(DID_single_signal)
        self.add_channel_name_checkBox.setCheckState(
            Qt.CheckState.Checked if self.slot_call_back("get_is_add_channel_name") else Qt.CheckState.Unchecked
        )
        self._update_excel_info(imported_excel_lsit)
        self.slot_call_back("init_import_files_ui", result_callback=self.update_widget_then_show)

    def check_selection_for_replace_button(self):
        selected_items = self.tableWidget.selectedItems()

        # 初始状态设置为不启用
        enabled = False

        if len(selected_items) == 0:
            self.pushButtonReplace.setEnabled(False)
            return

        selected_rows = {item.row() for item in selected_items}
        # 确认恰好一个文件被选中
        if len(selected_rows) == 1:
            row = next(iter(selected_rows))
            file_item = self.tableWidget.item(row, 2)
            if file_item and file_item.text().endswith((".dbc", ".ldf", ".cdd", ".xlsx")):
                enabled = True

        self.pushButtonReplace.setEnabled(enabled)

    def open_vcos_replace_files_slot(self):
        """
        Slot function for Remove File QPushButton.

        1. Support user to replace .dbc/.ldf/.cdd/.xlsx files.
        2. Update table widget according to selection.
        """
        selected_items = self.tableWidget.selectedItems()

        if len(selected_items) != 1:
            QMessageBox.warning(self, "Warning", "Please select exactly one file for replacement.")
            return

        row = selected_items[0].row()
        file_item = self.tableWidget.item(row, 2)

        if not file_item or not file_item.text().endswith((".dbc", ".ldf", ".cdd", ".xlsx")):
            QMessageBox.warning(self, "Warning", "Selection is not a valid file.")
            return

        file_info_dict: dict = {
            "file_type": "",  # 文件类型，可以是 "dbc"、"ldf" 等
            "old_file_path": "",  # 旧文件路径
            "new_file_path": "",  # 新文件路径
        }

        # 选择新文件
        file_dialog: QFileDialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        if file_item.text().endswith(".dbc"):
            new_file_path, _ = file_dialog.getOpenFileName(self, "Replace DBC File", "", "DBC Files(*.dbc)")
            file_info_dict["file_type"] = "dbc"
        elif file_item.text().endswith(".xlsx"):
            new_file_path, _ = file_dialog.getOpenFileName(self, "Replace Excel File", "", "Excel Files(*.xlsx)")
            file_info_dict["file_type"] = "xlsx"
        elif file_item.text().endswith(".ldf"):
            new_file_path, _ = file_dialog.getOpenFileName(self, "Replace LDF File", "", "LDF Files(*.ldf)")
            file_info_dict["file_type"] = "ldf"
        elif file_item.text().endswith(".cdd"):
            new_file_path, _ = file_dialog.getOpenFileName(self, "Replace CDD File", "", "CDD Files(*.cdd)")
            file_info_dict["file_type"] = "cdd"
        else:
            QMessageBox.warning(self, "Warning", "Selection is not a valid file.")
            return

        if len(new_file_path) == 0:
            return

        # 检查新增文件是否已经存在
        new_file_normalized_path = os.path.normpath(new_file_path)
        row_count = table_widget.rowCount()
        for i in range(row_count):
            existing_file_item = table_widget.item(i, 2)
            existing_file_path = os.path.normpath(existing_file_item.text())
            if existing_file_item and existing_file_path == new_file_normalized_path:
                QMessageBox.warning(self, "Warning", "The selected file is already in the list.")
                return

        logger.info(f"Replacing {file_item.text()} with {new_file_path}")

        # 如果是xlsx文件，直接替换
        if file_item.text().endswith(".xlsx"):
            file_path = os.path.abspath(new_file_path)
            meta_info = {"node_list": None, "node_selected": None, "path": file_path}
            self._replace_row(row, meta_info)
            return
        # 其他类型文件进行文件预解析,然后替换
        file_info_dict["old_file_path"] = os.path.normpath(file_item.text())
        file_info_dict["new_file_path"] = new_file_path
        self.slot_call_back(
            "parser_replace_files_get_original_data_action",
            file_info_dict,
            result_callback=lambda info_dict: self._replace_row(row, info_dict),
        )

    def right_click_slot(self, pos):
        self.selected_file_path_list = []
        table_widget: QTableWidget = self.tableWidget
        selected_items = table_widget.selectedItems()
        for selected_item in selected_items:
            selected_row = selected_item.row()
            self.selected_file_path_list.append(table_widget.item(selected_row, 2).text())
        self.right_click_menu = QMenu(self)
        self.menu_action_edit = self.right_click_menu.addAction("Edit")
        self.menu_click_action = self.right_click_menu.show()
        self.right_click_menu.move(QCursor.pos())
        self.menu_action_edit.triggered.connect(self.handle_edit_solt)

    def handle_edit_solt(self):
        file_info_dict = self.slot_call_back("get_dbc_ldf_content", self.selected_file_path_list)
        # 弹窗展示所有DBC的属性，并支持修改写回内存
        self.edit_DBC_details = EditDBCDetailsUI(file_info_dict)
        self.edit_DBC_details.details_dialog.show()

    def open_vcos_project_files_slot(self):
        """
        Slot function for Add Files QPushButton.

        1. Support user to select .dbc/.ldf/.cdd/.xlsx files.
        2. Update table widget according to selection.
        """
        # step1:Acquiring files
        file_dialog: QFileDialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        files_list, _ = file_dialog.getOpenFileNames(
            self, "VCOS Studio Import Files", "", filter=("*.dbc *.xlsx *.cdd")
        )  # 该方法不支持选择不同类型的文件
        if len(files_list) == 0:
            return
        # step2:Distinguishing file types to .dbc/.ldf/.cdd/.excel
        dbc_file_list: list = []
        ldf_file_list: list = []
        cdd_file_list: list = []
        excel_file_list: list = []
        file_list: dict = {"dbc": [], "ldf": [], "cdd": [], "excel": []}
        for file in files_list:
            file = os.path.abspath(file)
            excel_list = self._get_import_excel_data()
            if file.endswith(".dbc"):
                dbc_file_list.append(file)
            elif file.endswith(".ldf"):
                ldf_file_list.append(file)
            elif file.endswith(".cdd"):
                cdd_file_list.append(file)
            elif file.endswith(".xlsx"):
                excel_file_list.append(file)
                if file not in excel_list:
                    meta_info = {"node_list": None, "node_selected": None, "path": file}
                    self._append_row(file, meta_info)
            else:
                continue
        if (
            len(dbc_file_list) == 0
            and len(ldf_file_list) == 0
            and len(cdd_file_list) == 0
            and len(excel_file_list) == 0
        ):
            Text: str = "Please Reselect files endswith .dbc/.ldf/.cdd/.xlsx"
            message_box = QMessageBox(QMessageBox.Icon.Warning, "Notice", Text)
            message_box.exec()
        file_list["dbc"] = dbc_file_list
        file_list["ldf"] = ldf_file_list
        file_list["cdd"] = cdd_file_list
        file_list["excel"] = excel_file_list
        # step3:File processing according to file type
        # Process .dbc .ldf .cdd .xlsx(xlsx文件已经在选择时处理)
        self.slot_call_back(
            "parser_files_get_original_data_action", file_list, result_callback=self.update_table_widget
        )

    def clear_table_widget(self):
        table_widget: QTableWidget = self.tableWidget
        table_widget.setRowCount(0)

    def _update_excel_info(self, excel_list):
        for file in excel_list:
            meta_info = {"node_list": None, "node_selected": None, "path": file}
            self._append_row(file, meta_info)

    def update_table_widget(self, info_dict: "dict[str, dict]"):
        excel_list = self._get_import_excel_data()
        self.clear_table_widget()
        for file_name, file_info in info_dict.items():
            if file_info.get("validation_error_log", []):
                _, suffix = os.path.splitext(file_name)
                message_box = QMessageBox(QMessageBox.Icon.Critical, f"Invalid {suffix}", f"Won't import {file_name}")
                message_box.exec()
                continue
            self._append_row(file_name, file_info)

        self._update_excel_info(excel_list)

    def node_selected_changed(self):
        combo_box: QComboBox = self.sender()
        selected_node = combo_box.currentText()
        table_widget: QTableWidget = self.tableWidget
        row = table_widget.indexAt(combo_box.pos()).row()
        file_path = table_widget.item(row, 2).text()
        self.slot_call_back("node_selected_changed", file_path, selected_node)

    def _append_row(self, file_name, info_dict):
        table_widget: QTableWidget = self.tableWidget
        row_cnt = table_widget.rowCount()
        table_widget.insertRow(row_cnt)

        name_item = QTableWidgetItem(os.path.basename(file_name))
        table_widget.setItem(row_cnt, 0, name_item)

        path_item = QTableWidgetItem(info_dict["path"])
        table_widget.setItem(row_cnt, 2, path_item)
        table_widget.resizeColumnToContents(row_cnt)
        if (
            "node_list" in info_dict.keys()
            and "node_selected" in info_dict.keys()
            and info_dict["node_list"]
            and info_dict["node_selected"]
        ):
            combox_call_put = QComboBox()
            combox_call_put.addItems(info_dict["node_list"])
            combox_call_put.setCurrentText(info_dict["node_selected"])
            table_widget.setCellWidget(row_cnt, 1, combox_call_put)
            combox_call_put.currentIndexChanged.connect(self.node_selected_changed)
        else:
            place_holder_item = QTableWidgetItem("")
            place_holder_item.setFlags(place_holder_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table_widget.setItem(row_cnt, 1, place_holder_item)

    def _replace_row(self, row_idx, info_dict):
        table_widget: QTableWidget = self.tableWidget
        file_name = os.path.basename(info_dict["path"])

        if row_idx < 0 or row_idx >= table_widget.rowCount():
            logger.ui_error("Config file path does not exist")("Invalid row index. Cannot replace.")
            return

        if info_dict.get("validation_error_log", []):
            _, suffix = os.path.splitext(file_name)
            message_box = QMessageBox(QMessageBox.Icon.Critical, f"Invalid {suffix}", f"Won't import {file_name}")
            message_box.exec()
            return
        # 设置新的文件名
        name_item = QTableWidgetItem(file_name)
        table_widget.setItem(row_idx, 0, name_item)
        # 设置新的文件路径
        path_item = QTableWidgetItem(info_dict["path"])
        table_widget.setItem(row_idx, 2, path_item)
        table_widget.resizeColumnToContents(row_idx)
        # 根据给定的信息设置 ComboBox 或空白项
        if (
            "node_list" in info_dict.keys()
            and "node_selected" in info_dict.keys()
            and info_dict["node_list"]
            and info_dict["node_selected"]
        ):
            combox_call_put = QComboBox()
            combox_call_put.addItems(info_dict["node_list"])
            combox_call_put.setCurrentText(info_dict["node_selected"])
            table_widget.setCellWidget(row_idx, 1, combox_call_put)
            combox_call_put.currentIndexChanged.connect(self.node_selected_changed)
        else:
            # 如果下拉列表的条件不满足，放置一个非编辑的占位项
            place_holder_item = QTableWidgetItem("")
            place_holder_item.setFlags(place_holder_item.flags() & ~Qt.ItemIsEditable)
            table_widget.setItem(row_idx, 1, place_holder_item)

        # 调整列宽
        for column in range(table_widget.columnCount()):
            table_widget.resizeColumnToContents(column)

    def add_dbc_info_to_tablewidget(self, dbc_cfg_infos):
        dbc_list = {}
        for dbc_cfg_info in dbc_cfg_infos:
            dbc_list.update(
                {
                    dbc_cfg_info["dbc_name"]: {
                        "path": dbc_cfg_info["file"],
                        "node_selected": dbc_cfg_info["node_selected"],
                        "node_list": dbc_cfg_info["node_list"],
                    }
                }
            )
            self._add_a_row_data_to_table(dbc_cfg_info["file"], dbc_cfg_info["node_list"])

    def _add_a_row_data_to_table(self, file, node_list, node_selected_index=None):
        row_cnt = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row_cnt)
        comBox_call_put = QComboBox()
        comBox_call_put.addItems(node_list)
        if node_selected_index is not None:
            comBox_call_put.setCurrentIndex(node_selected_index)
        newItem = QTableWidgetItem(os.path.basename(file))
        self.tableWidget.setItem(row_cnt, 0, newItem)
        newItem = QTableWidgetItem(file)
        self.tableWidget.setItem(row_cnt, 2, newItem)
        self.tableWidget.resizeColumnToContents(row_cnt)
        self.tableWidget.setCellWidget(row_cnt, 1, comBox_call_put)

    def _get_import_table_data(self):
        rv = []
        row_count = self.tableWidget.rowCount()
        for row_num in range(row_count):
            file_name_item = self.tableWidget.item(row_num, 0)
            file_path_item = self.tableWidget.item(row_num, 2)
            node_cell_widget = self.tableWidget.cellWidget(row_num, 1)
            if not node_cell_widget or not file_name_item or not file_path_item:
                break
            file_name = file_name_item.text()
            file_path = file_path_item.text()
            node_selected = node_cell_widget.currentText()
            if file_name in [None, ""] or file_path in [None, ""]:
                continue
            rv.append({"file_name": file_name, "node_selected": node_selected, "file_path": file_path})
        return rv

    def _get_import_excel_data(self):
        rv = []
        table_widget: QTableWidget = self.tableWidget
        row_count = table_widget.rowCount()
        for row_num in range(row_count):
            file_name_item = table_widget.item(row_num, 0)
            file_path_item = table_widget.item(row_num, 2)
            file_name = file_name_item.text()
            file_path = file_path_item.text()
            if not file_path.endswith(".xlsx"):
                continue
            if file_name in [None, ""] or file_path in [None, ""]:
                continue
            rv.append(file_path)
        return rv

    def open_vcos_pushbutton_apply_slot(self):

        def _update_ui(args):
            logger.ui_info("Finish import attemption, try update overview")
            self.overview_ui.update_overview(args)
            # 导入dbc或ldf完成后，主动更新tree，用户无需关闭tab, CDD现在也在同一个文件里处理
            module_set = set(LDF_RELATED_MODULE_LIST + DBC_RELATED_MODULE_LIST + ["CanTp"] + CDD_RELATED_MODULE_LIST)
            self.after_import(module_set)
            self.close()

        def after_check(check_res_tuple):
            check_res = check_res_tuple[0]
            error_message_list = check_res_tuple[1]
            if not check_res:
                text = ""
                for msg in error_message_list:
                    text += f"{msg}\n"

                message_box = QMessageBox(QMessageBox.Icon.Critical, "Invalid channel name", text)
                message_box.exec()
                return

            excel_list = self._get_import_excel_data()
            merge_signal_checkBox: QCheckBox = self.merge_signal_checkBox
            add_channel_name_checkBox: QCheckBox = self.add_channel_name_checkBox
            merge_signal_flag = merge_signal_checkBox.isChecked()
            is_add_channel_name = add_channel_name_checkBox.isChecked()
            # 点击OK，需要将选中的所有dbc、ldf、cdd、excel传给UI Adaptor，解析并更新ecuc arxml
            self.slot_call_back(
                "apply_diag_com_import", excel_list, merge_signal_flag, is_add_channel_name, result_callback=_update_ui
            )

        # Check ldf channel name, stop apply if find invalid channel name
        self.slot_call_back("check_before_apply", result_callback=after_check)

    def open_vcos_remove_files_slot(self):
        table_widget: QTableWidget = self.tableWidget
        selected_items = table_widget.selectedItems()
        removed_files = []
        # Filter items, only remain one item for each row
        selected_row_dict = {}
        for item in selected_items:
            selected_row_dict[item.row()] = item
        selected_rows = list(selected_row_dict.keys())

        selected_rows.sort(reverse=True)
        for row in selected_rows:
            file_path = table_widget.item(row, 2).text()
            if file_path.endswith(".xlsx"):
                table_widget.removeRow(row)
            else:
                removed_files.append(file_path)

        self.slot_call_back("remove_imported_files", removed_files, result_callback=self.update_table_widget)

    def closeEvent(self, ev: QCloseEvent) -> None:
        self.slot_call_back("close_import_dbc_ldf_ui")
        self.timer_func()
