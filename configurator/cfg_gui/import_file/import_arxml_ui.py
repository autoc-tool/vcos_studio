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
import copy
from enum import Enum
from typing import Callable
from PySide6.QtWidgets import (
    QWidget,
    QTableWidget,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QFileDialog,
    QAbstractItemView,
    QTableWidgetItem,
    QFrame,
    QLabel,
    QDialog,
    QListWidget,
    QStackedWidget,
    QComboBox,
    QMessageBox,
)
from PySide6.QtGui import QGuiApplication, QIcon, QFont
from PySide6.QtCore import Qt, QSize
from cfg_gui.import_file.merge_ecuc_ui import MergeEcucUi
from func_module.module_management.arxml_handler import config_comparator

HINT_SIZE_FACTOR = 0.3
WIDGET_SIZE_FACTOR = 0.4
BUTTON_LENGTH = 20
PIXMAP_SIZE = 25
FONT_SIZE = 10


class IMPORT_FILES_TYPE(Enum):
    NO_FILE = 0
    ONLY_ASW = 1
    HAS_ECUC = 2


class HintInfoListDialog(QDialog):

    def __init__(self, hint_str: str, info_list: list, parent=None):
        super().__init__(parent)
        self.hint_str = hint_str
        self.info_list = info_list
        self.init_ui()
        self.show()

    def init_ui(self):
        hint_icon = QLabel()
        hint_icon.setPixmap(QIcon(":/attention_info.svg").pixmap(PIXMAP_SIZE, PIXMAP_SIZE))
        hint_icon.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hint_label = QLabel(self.hint_str)
        hint_label.setFont(QFont("Microsoft YaHei", FONT_SIZE))
        hint_layout = QHBoxLayout()
        hint_layout.addWidget(hint_icon)
        hint_layout.addWidget(hint_label)
        hint_layout.addStretch(1)

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.close)
        button_layout.addStretch(1)
        button_layout.addWidget(self.ok_button)

        info_list_widget = QListWidget()
        info_list_widget.addItems(self.info_list)

        window_layout = QVBoxLayout()
        window_layout.addLayout(hint_layout)
        window_layout.addWidget(info_list_widget)
        window_layout.addLayout(button_layout)
        self.setLayout(window_layout)
        screen_geometry = QGuiApplication.primaryScreen().geometry()
        self.resize(screen_geometry.width() * HINT_SIZE_FACTOR, screen_geometry.height() * HINT_SIZE_FACTOR)
        self.setWindowTitle("VCOS Studio")
        self.setWindowIcon(QIcon(":/Home.svg"))
        self.setModal(True)
        # 取消窗口标题栏的问号按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)


def button_set_attr(button: QPushButton):
    button.resize(QSize(BUTTON_LENGTH, BUTTON_LENGTH))
    button.setIconSize(button.size())
    button.setStyleSheet(
        """
            QPushButton {background-color: transparent; border: none; color: white;}
            QPushButton:hover {background-color: rgba(180, 180, 255, 0.4);}
            QPushButton:pressed { background-color: rgba(100, 100, 155, 0.4);}
        """
    )


class ImportArxmlUi(QWidget):

    def __init__(
        self, call_back_dict=None, over_view_ui=None, after_asw_import: callable = None, timer_func=None, parent=None
    ):
        super().__init__(parent)
        self.call_back: Callable = call_back_dict
        self.over_view_ui = over_view_ui
        self.after_asw_import = after_asw_import

        # 记录当前已经选择的文件信息
        self.selected_file_path_set = set()
        # 记录当前已解析成模块信息的文件集合
        self.parsed_module_files_set = set()
        # 导入的arxml数据 也表示合法的文件的数据
        self.arxml_data_obj_dict = {}
        # 存储所有ecuc文件的模块数据 key: file_path, value: [(module_name, module_obj)]
        self.parsed_module_dict = {}
        # 存储所有 ecuc 模块的对比对象
        self.ecuc_comparator_dict = {}
        self.selected_module_num = 0
        self.merge_ecuc_ui = None
        self.timer_func = timer_func
        self.init_UI_layout()
        self.init_signal_connect_slot()

    def init_first_page(self):
        # 第一个导入文件的界面
        # 中间左侧的按钮区域
        self.stack_widget = QStackedWidget(self)
        # 第一个页面的整体部分
        import_arxml_widget = QWidget()
        self.button_add_file = QPushButton(QIcon(":/add.svg"), "", self)
        self.button_remove_file = QPushButton(QIcon(":/not_ok.svg"), "", self)
        button_set_attr(self.button_add_file)
        button_set_attr(self.button_remove_file)
        manage_file_button_layout = QVBoxLayout()
        manage_file_button_layout.addWidget(self.button_add_file)
        manage_file_button_layout.addWidget(self.button_remove_file)
        manage_file_button_layout.addStretch(1)
        manage_file_button_layout.setSpacing(10)
        # 中间文件路径控件区域
        self.manage_files_tablewidget = QTableWidget(self)
        center_inner_layout_1 = QHBoxLayout(import_arxml_widget)
        center_inner_layout_1.addLayout(manage_file_button_layout)
        center_inner_layout_1.addWidget(self.manage_files_tablewidget)
        center_inner_layout_1.setContentsMargins(2, 0, 5, 2)
        center_inner_layout_1.setSpacing(2)
        self.stack_widget.addWidget(import_arxml_widget)

        self.set_table_widget_attr(self.manage_files_tablewidget, ["Arxml File Path"])

    def init_second_page(self):
        # 第二个界面，冲突显示界面
        import_mode_select_widget = QWidget()
        self.select_all_button = QPushButton(QIcon(":/check_all.svg"), "", self)
        self.cancel_all_button = QPushButton(QIcon(":cancel_all.svg"), "", self)
        button_set_attr(self.select_all_button)
        button_set_attr(self.cancel_all_button)
        select_button_layout = QVBoxLayout()
        select_button_layout.addWidget(self.select_all_button)
        select_button_layout.addWidget(self.cancel_all_button)
        select_button_layout.addStretch(1)
        select_button_layout.setSpacing(10)
        # 中间控件区域布局
        self.all_module_table_widget = QTableWidget(self)
        center_layout = QHBoxLayout(import_mode_select_widget)
        center_layout.addLayout(select_button_layout)
        center_layout.addWidget(self.all_module_table_widget)
        center_layout.setContentsMargins(2, 0, 5, 2)
        center_layout.setSpacing(2)
        self.stack_widget.addWidget(import_mode_select_widget)

        self.init_import_mode_select_table_widget()

    def init_UI_layout(self):
        # 顶端标题与提示信息区域
        title_label = QLabel("Import Files")
        title_label.setFont(QFont("Microsoft YaHei", 15))
        self.hint_message_label = QLabel("Please select at least one arxml file to import.")
        self.hint_message_label.setFont(QFont(title_label.font().family(), FONT_SIZE))
        top_layout = QVBoxLayout()
        top_layout.addWidget(title_label)
        top_layout.addWidget(self.hint_message_label)
        top_layout.setSpacing(10)
        top_layout.setContentsMargins(7, 0, 0, 0)

        self.init_first_page()
        self.init_second_page()

        # 底部按钮设置
        self.next_button = QPushButton("next")
        self.back_button = QPushButton("back")
        self.back_button.setDisabled(True)
        self.finish_button = QPushButton("finish")
        self.finish_button.setDisabled(True)
        self.button_cancel = QPushButton("cancel")
        self.next_button.setDisabled(True)
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.back_button)
        bottom_layout.addWidget(self.next_button)
        bottom_layout.addWidget(self.finish_button)
        bottom_layout.addWidget(self.button_cancel)
        bottom_layout.setContentsMargins(0, 0, 10, 0)

        # 整体控件布局
        widget_layout = QVBoxLayout(self)
        widget_layout.addLayout(top_layout)
        widget_layout.addWidget(self.get_ui_seperate_line())
        widget_layout.addWidget(self.stack_widget)
        widget_layout.addWidget(self.get_ui_seperate_line())
        widget_layout.addLayout(bottom_layout)
        widget_layout.setContentsMargins(0, 0, 0, 10)
        self.setWindowIcon(QIcon(":/Home.svg"))
        screen_geometry = QGuiApplication.primaryScreen().geometry()
        self.resize(screen_geometry.width() * WIDGET_SIZE_FACTOR, screen_geometry.height() * WIDGET_SIZE_FACTOR)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle("Select Arxml Files To Import")

    def set_table_widget_attr(self, table_widget: QTableWidget, table_widget_header: list):
        table_widget.setColumnCount(len(table_widget_header))
        table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table_widget.setHorizontalHeaderLabels(table_widget_header)
        table_widget.setSelectionBehavior(QAbstractItemView.SelectItems)
        table_widget.verticalHeader().setHidden(True)

    def init_signal_connect_slot(self):
        self.button_add_file.clicked.connect(self.add_import_button_slot)
        self.button_remove_file.clicked.connect(self.remove_arxml_files_slot)
        self.button_cancel.clicked.connect(self.closeEvent)
        self.back_button.clicked.connect(self.back_page_slot)
        self.next_button.clicked.connect(self.next_page_slot)
        self.select_all_button.clicked.connect(lambda: self.update_module_selected_state(Qt.CheckState.Checked))
        self.cancel_all_button.clicked.connect(lambda: self.update_module_selected_state(Qt.CheckState.Unchecked))
        self.finish_button.clicked.connect(self.finish_button_clicked_slot)
        self.all_module_table_widget.cellChanged.connect(self.module_table_cell_state_changed)

    def get_ui_seperate_line(self, direction=QFrame.HLine) -> QFrame:
        horizon_line = QFrame(self)
        horizon_line.setFrameShape(direction)
        horizon_line.setFrameShadow(QFrame.Sunken)
        return horizon_line

    def show_illegal_files_window(self, legal_arxml_dict: dict):
        # legal_arxml_dict --> key: file_path, value: dict { key: "arxml_obj", key: "file_type" }
        # file_type: "asw", "ecuc"
        illegal_file_list = []
        imported_file_path = copy.deepcopy(self.curr_imported_file_path)
        for file_path in imported_file_path:
            if legal_arxml_dict is None or file_path not in legal_arxml_dict.keys():
                self.curr_imported_file_path.remove(file_path)
                illegal_file_list.append(file_path)
            else:
                self.selected_file_path_set.add(file_path)
                self.arxml_data_obj_dict.update({file_path: legal_arxml_dict[file_path]})

        if len(illegal_file_list) > 0:
            # 弹窗显示不合法文件
            self.illegal_hint_ui = HintInfoListDialog(
                "The following files are illegal to import, please check it.", illegal_file_list, self
            )
        self.insert_file_path_to_table()

    def get_import_files_type(self):
        asw_file_num, ecuc_file_num = 0, 0
        for obj_and_type in self.arxml_data_obj_dict.values():
            if obj_and_type["file_type"] == "asw":
                asw_file_num += 1
            elif obj_and_type["file_type"] == "ecuc":
                ecuc_file_num += 1

        if ecuc_file_num > 0:
            return IMPORT_FILES_TYPE.HAS_ECUC
        else:
            return IMPORT_FILES_TYPE.ONLY_ASW if asw_file_num > 0 else IMPORT_FILES_TYPE.NO_FILE

    def update_hint_info_button_state(self, first_page=True):
        import_files_type = self.get_import_files_type()

        def _set_common_button_state():
            if first_page is True:
                self.back_button.setDisabled(True)
                self.finish_button.setDisabled(True)
            else:
                self.next_button.setDisabled(True)
                self.back_button.setEnabled(True)

        if import_files_type == IMPORT_FILES_TYPE.NO_FILE:
            self.next_button.setDisabled(True)
            self.finish_button.setDisabled(True)
            self.hint_message_label.setText("Please select at least one arxml file to import.")
        elif import_files_type == IMPORT_FILES_TYPE.ONLY_ASW:
            self.next_button.setDisabled(True)
            self.finish_button.setEnabled(True)
            self.hint_message_label.setText("After clicking the finish button, import the data to the project.")
        elif import_files_type == IMPORT_FILES_TYPE.HAS_ECUC:
            _set_common_button_state()
            if first_page is True:
                self.next_button.setEnabled(True)
                self.hint_message_label.setText(
                    "After clicking the next button, you can select the import " "mode and module you need."
                )
            else:
                if self.selected_module_num > 0:
                    self.finish_button.setEnabled(True)
                    self.hint_message_label.setText("After clicking the finish button, import the data to the project.")
                else:
                    self.finish_button.setDisabled(True)
                    self.hint_message_label.setText("Please select at least one ecuc module to import.")

    def back_page_slot(self):
        self.stack_widget.setCurrentIndex(0)
        # 切完页面使能next按钮
        self.next_button.setEnabled(True)
        self.back_button.setDisabled(True)
        self.update_hint_info_button_state(first_page=True)

    def next_page_slot(self):
        self.stack_widget.setCurrentIndex(1)
        # 切完页面使能back按钮
        self.back_button.setEnabled(True)
        self.next_button.setDisabled(True)
        self.update_import_mode_select_table_widget()

    def filt_illegal_files(self):
        # 过滤 重复导入
        self.curr_imported_file_path = [
            file_path for file_path in self.curr_imported_file_path if file_path not in self.selected_file_path_set
        ]
        # 过滤不合法文件
        self.call_back(
            "validate_ecuc_and_asw_arxml", self.curr_imported_file_path, result_callback=self.show_illegal_files_window
        )

    def insert_file_path_to_table(self):
        # 插入数据的行下标
        curr_row_index = self.manage_files_tablewidget.rowCount()
        self.manage_files_tablewidget.setRowCount(
            self.manage_files_tablewidget.rowCount() + len(self.curr_imported_file_path)
        )
        for file_path in self.curr_imported_file_path:
            self.manage_files_tablewidget.setItem(curr_row_index, 0, QTableWidgetItem(file_path))
            curr_row_index += 1
        self.manage_files_tablewidget.resizeColumnsToContents()

        self.update_hint_info_button_state(first_page=True)

    def add_import_button_slot(self):
        self.curr_imported_file_path, _ = QFileDialog.getOpenFileNames(
            self, "Select the arxml file to import", filter="Ecuc or Asw arxml (*.arxml)"
        )
        if len(self.curr_imported_file_path) > 0:
            # 先过滤相同文件，然后过滤非法文件，完成校验操作自动调用插数据函数
            self.filt_illegal_files()
            # update module type info
            self.module_type_dict = self.call_back("get_module_type")

    def remove_module_table_widget_lines(self, file_path):
        FILE_PATH_LINE = 2
        row_count = self.all_module_table_widget.rowCount()
        row_index = 0
        while row_index < row_count:
            if row_index >= self.all_module_table_widget.rowCount():
                break
            if self.all_module_table_widget.item(row_index, FILE_PATH_LINE).text() == file_path:
                self.all_module_table_widget.removeRow(row_index)
            else:
                row_index += 1

    def remove_arxml_files_slot(self):

        def remove_file_path_line(selected_item, selected_row):
            self.selected_file_path_set.remove(selected_item.text())
            # 清除取消导入文件的记录信息， 也即清除合法文件的信息
            self.arxml_data_obj_dict.pop(selected_item.text())
            # 取消文件导入时，需要清除模块解析集合
            if selected_item.text() in self.parsed_module_files_set:
                # 清除第二页的模块 导入模式 文件路径 行的信息
                self.remove_module_table_widget_lines(selected_item.text())
                self.parsed_module_files_set.remove(selected_item.text())
                self.parsed_module_dict.pop(selected_item.text())
            self.manage_files_tablewidget.removeRow(selected_row)
            self.update_hint_info_button_state(first_page=True)

        # 多选清除导入文件
        selected_item_list = self.manage_files_tablewidget.selectedItems()
        # 防止一次点击，会删除所有行的异常
        if len(selected_item_list) > 1:
            for selected_item in selected_item_list:
                remove_file_path_line(selected_item, selected_item.row())

        # 一直点击 x 不断清除文件
        selected_row = self.manage_files_tablewidget.currentRow()
        selected_item = self.manage_files_tablewidget.item(selected_row, 0)
        if selected_item is None:
            return
        remove_file_path_line(selected_item, selected_row)

    def init_import_mode_select_table_widget(self):
        # 设置初始属性
        header = ["Ecuc Module", "Import Mode", "Source File Path"]
        self.set_table_widget_attr(self.all_module_table_widget, header)
        self.all_module_table_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.all_module_table_widget.setColumnCount(3)

    def update_module_selected_state(self, state: Qt.CheckState):
        for row_index in range(self.all_module_table_widget.rowCount()):
            self.all_module_table_widget.item(row_index, 0).setCheckState(state)
            self.update_hint_info_button_state(first_page=False)

    def module_table_cell_state_changed(self, row_index, col_index):
        if self.all_module_table_widget.item(row_index, col_index).checkState() == Qt.CheckState.Unchecked:
            self.selected_module_num -= 1
        else:
            self.selected_module_num += 1
        self.update_hint_info_button_state(False)

    def insert_module_file_to_table_widget(self, file_path, mode_and_modules: list):
        # 屏蔽信号，初始状态非选中与设置单元对象，selected_module_num 不需要减一
        self.all_module_table_widget.blockSignals(True)
        table_start_index = self.all_module_table_widget.rowCount()
        self.all_module_table_widget.setRowCount(self.all_module_table_widget.rowCount() + len(mode_and_modules))

        for module_index in range(len(mode_and_modules)):
            row_index = table_start_index + module_index
            for col_index in range(self.all_module_table_widget.columnCount()):
                if col_index == 0:
                    table_widget_item = QTableWidgetItem(mode_and_modules[module_index][1])
                    # import mode 默认仅有 replace 的情况下不勾选
                    if mode_and_modules[module_index][0] == ["replace"]:
                        table_widget_item.setCheckState(Qt.CheckState.Unchecked)
                    else:
                        table_widget_item.setCheckState(Qt.CheckState.Checked)
                        self.selected_module_num += 1
                    self.all_module_table_widget.setItem(row_index, col_index, table_widget_item)
                elif col_index == 1:
                    if len(mode_and_modules[module_index][0]) > 1:
                        table_widget_item = QComboBox()
                        table_widget_item.addItems(mode_and_modules[module_index][0])
                        self.all_module_table_widget.setCellWidget(row_index, col_index, table_widget_item)
                    elif len(mode_and_modules[module_index][0]) == 1:
                        self.all_module_table_widget.setItem(
                            row_index, col_index, QTableWidgetItem(mode_and_modules[module_index][0][0])
                        )
                else:
                    self.all_module_table_widget.setItem(row_index, col_index, QTableWidgetItem(file_path))

        self.all_module_table_widget.resizeColumnsToContents()
        self.all_module_table_widget.blockSignals(False)

    def get_import_mode_and_module_info(self, file_path: str, bsw_module_info: dict):
        curr_file_module_table_dict = {}
        module_import_mode = []
        for module_name, module_data_obj in bsw_module_info.items():
            # 当前工程没有该模块 -> add
            _, added_module_list = self.call_back("get_current_project_module_info")
            if module_name not in added_module_list:
                import_mode = ["add"]
            else:
                if self.arxml_data_obj_dict[file_path]["file_type"] == "ecuc":
                    comparator: config_comparator = self.call_back(
                        "judge_ecuc_config_has_difference", module_name, module_data_obj
                    )
                    # 有区别: merge replace, 没区别: reaplce # TODO: MCAL模块暂时不支持冲突解决
                    if not self.module_type_dict.get(module_name, {}).get("is_mcal") and comparator.has_diff():
                        if file_path not in self.ecuc_comparator_dict.keys():
                            self.ecuc_comparator_dict.update({file_path: {}})
                        if module_name not in self.ecuc_comparator_dict[file_path].keys():
                            self.ecuc_comparator_dict[file_path].update({module_name: comparator})
                        import_mode = ["merge", "replace"]
                    else:
                        import_mode = ["replace"]
                else:
                    import_mode = ["replace"]
            module_import_mode.append((import_mode, module_name))
        curr_file_module_table_dict.update({file_path: module_import_mode})
        return curr_file_module_table_dict

    def update_import_mode_select_table_widget(self):

        def __update_table_widget(all_ecuc_obj_dict: dict):
            for file_path, bsw_module_info in all_ecuc_obj_dict.items():
                if file_path not in self.parsed_module_files_set:
                    curr_file_module_table_dict = self.get_import_mode_and_module_info(file_path, bsw_module_info)
                    self.insert_module_file_to_table_widget(file_path, curr_file_module_table_dict[file_path])
                    self.parsed_module_files_set.add(file_path)
            self.all_module_table_widget.sortItems(0, Qt.AscendingOrder)
            self.update_hint_info_button_state(first_page=False)

        ecuc_obj_dict = {}
        for file_path, arxml_info in self.arxml_data_obj_dict.items():
            # 判断当前ecuc文件是否已经在已解析的哈希表中，防止二次解析
            if file_path not in self.parsed_module_files_set and arxml_info["file_type"] == "ecuc":
                ecuc_obj_dict.update({file_path: arxml_info["arxml_obj"]})
        if len(ecuc_obj_dict) > 0:
            self.call_back(
                "parse_files_ecuc_to_module_dict",
                ecuc_obj_dict,
                self.parsed_module_dict,
                result_callback=__update_table_widget,
            )
        else:
            self.update_hint_info_button_state(first_page=False)

    def get_selected_module_list(self) -> list:
        selected_ecuc_module_dict = {}
        for row_index in range(self.all_module_table_widget.rowCount()):
            if self.all_module_table_widget.item(row_index, 0).checkState() == Qt.CheckState.Checked:
                if self.all_module_table_widget.cellWidget(row_index, 1) is not None:
                    import_mode = self.all_module_table_widget.cellWidget(row_index, 1).currentText()
                else:
                    import_mode = self.all_module_table_widget.item(row_index, 1).text()
                file_path = self.all_module_table_widget.item(row_index, 2).text()
                module_name = self.all_module_table_widget.item(row_index, 0).text()
                if file_path not in selected_ecuc_module_dict.keys():
                    selected_ecuc_module_dict.update({file_path: []})
                selected_ecuc_module_dict[file_path].append(
                    {
                        "module_name": module_name,
                        "import_mode": import_mode,
                        "module_obj": self.parsed_module_dict[file_path][module_name],
                    }
                )
        return selected_ecuc_module_dict

    def get_need_import_ecuc_dict(self, bsw_module_dict: dict):
        merge_module_list, new_import_ecuc_dict = [], {}
        self.import_ecuc_module_list = []
        for file_name, all_seleted_module_info in bsw_module_dict.items():
            for curr_module in all_seleted_module_info:
                module_name = curr_module["module_name"]
                if curr_module["import_mode"] == "merge":
                    merge_module_list.append((file_name, module_name))
                else:
                    if file_name not in new_import_ecuc_dict:
                        new_import_ecuc_dict[file_name] = {}
                    new_import_ecuc_dict[file_name][module_name] = {"ecuc_module_obj": curr_module["module_obj"]}
                    self.import_ecuc_module_list.append(module_name)
        return merge_module_list, new_import_ecuc_dict

    def get_need_import_asw_list(self):
        asw_file_list = []
        for file_path, obj_and_type in self.arxml_data_obj_dict.items():
            if obj_and_type["file_type"] == "asw":
                asw_file_list.append(file_path)

        return asw_file_list

    def _re_import_diff_prefix_module(self, prefix_diff_modules):
        """
        前缀不一致的ecuc模块需要重新导入
        :param prefix_diff_modules: dict, 前缀不一致的ecuc模块字典
        :return: None
        """
        if not prefix_diff_modules:
            return
        module_list = []
        for modules_in_one_file in prefix_diff_modules.values():
            module_list.extend(list(modules_in_one_file.keys()))

        box_reply = QMessageBox.question(
            self,
            "Mcal module prefix incompatible",
            (
                f"The prefix of {module_list} is inconsistent with the prefix of BSWMD in the project.\n"
                "Do you want to continue importing? Continuing to import may result in errors."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if QMessageBox.Yes == box_reply:
            for ecuc_module_dict in prefix_diff_modules.values():
                for module_info in ecuc_module_dict.values():
                    module_info["force_import"] = True
            # re import modules with different prefixes
            self.call_back(
                "import_all_types_arxml", prefix_diff_modules, [], result_callback=self._update_module_overview
            )

    def _update_module_overview(self, args):
        autosar_bswmd_dict, autosar_bsw_dict, prefix_diff_module = args[0], args[1], args[2]

        if self.import_ecuc_module_list is not None:
            self.over_view_ui.update_overview([autosar_bswmd_dict, autosar_bsw_dict])
            if "Can" in self.import_ecuc_module_list:
                self.import_ecuc_module_list.append("CanIf")
            # 导入mcal完成后，主动更新tree，用户无需关闭tab
            for module in self.import_ecuc_module_list:
                self.over_view_ui.update_bsw_module_data_and_view(module)

        # 刷新asw数据后，需要刷新其他 ui 的数据
        if self.asw_file_list is not None and len(self.asw_file_list) > 0:
            self.after_asw_import()
        # 开启冲突解决 UI
        if not self.merge_module_list:
            self._re_import_diff_prefix_module(prefix_diff_module)
            self.close()
            return
        self.pull_clash_resolution_ui()
        for module in autosar_bsw_dict:
            self.over_view_ui.update_bsw_module_data_and_view(module)

        self.call_back("save_system_arxml_arxml_action", result_callback=self.timer_func)
        self._re_import_diff_prefix_module(prefix_diff_module)

    def pull_clash_resolution_ui(self):
        for path_name, module_name in self.merge_module_list:
            self.merge_ecuc_ui = MergeEcucUi(self.ecuc_comparator_dict[path_name][module_name], self.call_back)
        self.close()

    def finish_button_clicked_slot(self):
        # 处理 ecuc 文件导入
        selected_ecuc_module_dict = self.get_selected_module_list()
        # bsw 文件处理，获取需要进行冲突解决与直接导入的bsw模块信息
        self.merge_module_list, new_import_bsw_dict = self.get_need_import_ecuc_dict(selected_ecuc_module_dict)
        # 获取需要导入的 asw 文件列表
        self.asw_file_list = self.get_need_import_asw_list()
        # 没有需要冲突解决的模块直接刷新数据更新ui
        self.call_back(
            "import_all_types_arxml",
            new_import_bsw_dict,
            self.asw_file_list,
            result_callback=self._update_module_overview,
        )

    def closeEvent(self, event=None):
        self.timer_func()
        self.close()
