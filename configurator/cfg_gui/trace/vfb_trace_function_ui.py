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
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget,
    QStackedWidget,
    QPushButton,
    QVBoxLayout,
    QTableWidget,
    QHBoxLayout,
    QLabel,
    QAbstractItemView,
    QTableWidgetItem,
    QFrame,
    QLineEdit,
    QCheckBox,
)
from PySide6.QtGui import QGuiApplication, QIcon, QFont, QColor

WIDGET_SIZE_FACTOR = 0.5
TITLE_FONT_SIZE = 14
BODY_FONT_SIZE = 9
SELECT_TASK_MAPPING_PAGE_IDX = 0
SELECT_TRACE_FUNCITON_PAGE_IDX = 1
TRIGGER_ENTITY_COL_IDX = 0
TRIGGER_ENTIRY_OWNER_COL_IDX = 1
MAPE_STATE_COL_IDX = 2
TRIGGER_CONDITION_COL_IDX = 5
PARAM_MOD_PATH = "/AUTOSAR/EcucDefs/Rte/RteGeneration/RteVfbTraceFunction"
CONTAINER_ECUC_PATH = "/ActiveEcuC/Rte/RteGeneration"
MODULE_NAME = "Rte"
PARAM_TAG = "ECUC-FUNCTION-NAME-DEF"

BUTTON_LENGTH = 20


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


class VfbTraceCfgUI(QWidget):

    def __init__(self, runnable_info_list, call_back, update_data_and_view) -> None:
        super().__init__()
        self.runnable_info_list = runnable_info_list
        self.hook_info_list = []
        self.call_back = call_back
        self.update_data_and_view = update_data_and_view
        self.__init_UI_layout()
        self.__init_slot_func()

    def __init_top_ui(self):
        # set top info area ui
        self.title_label = QLabel("")
        self.title_label.setFont(QFont("Microsoft YaHei", TITLE_FONT_SIZE))
        self.hint_message_label = QLabel("")
        self.hint_message_label.setWordWrap(True)
        self.hint_message_label.setFont(QFont(self.title_label.font().family(), BODY_FONT_SIZE))
        self.top_layout = QVBoxLayout()
        self.top_layout.addWidget(self.title_label)
        self.top_layout.addWidget(self.hint_message_label)
        self.top_layout.setSpacing(10)
        self.top_layout.setContentsMargins(7, 0, 0, 0)

    def __init_first_page(self):
        self.stack_widget = QStackedWidget()
        select_task_mapping_widget = QWidget()

        self.mapped_filter_box = QCheckBox()
        self.mapped_filter_box.setCheckState(Qt.Unchecked)
        mapped_filter_label = QLabel("Show only task mappings mapped to task")
        mapped_filter_label.setFont(QFont("Microsoft YaHei", BODY_FONT_SIZE))
        self.filter_line_edit = QLineEdit()
        self.filter_line_edit.setPlaceholderText("triggered entity name filter")
        self.filter_line_edit.setMinimumWidth(300)
        filter_cond_layout = QHBoxLayout()
        filter_cond_layout.addWidget(self.mapped_filter_box)
        filter_cond_layout.addWidget(mapped_filter_label)
        filter_cond_layout.addStretch(1)
        filter_cond_layout.addWidget(self.filter_line_edit)
        filter_cond_layout.setContentsMargins(10, 0, 0, 0)

        self.mappings_select_all_button = QPushButton(QIcon(":/check_all.svg"), "", self)
        self.mappings_cancel_all_button = QPushButton(QIcon(":cancel_all.svg"), "", self)
        button_set_attr(self.mappings_select_all_button)
        button_set_attr(self.mappings_cancel_all_button)
        select_button_layout = QVBoxLayout()
        select_button_layout.addWidget(self.mappings_select_all_button)
        select_button_layout.addWidget(self.mappings_cancel_all_button)
        select_button_layout.addStretch(1)
        select_button_layout.setSpacing(10)

        # central runnable table widget layout
        self.triggered_entity_table_widget = QTableWidget(self)
        center_layout = QHBoxLayout()
        center_layout.addLayout(select_button_layout)
        center_layout.addWidget(self.triggered_entity_table_widget)
        center_layout.setContentsMargins(2, 0, 5, 0)
        center_layout.setSpacing(2)

        page_layout = QVBoxLayout(select_task_mapping_widget)
        page_layout.addLayout(filter_cond_layout)
        page_layout.addLayout(center_layout)

        self.stack_widget.addWidget(select_task_mapping_widget)

        # init attr of trigger entity table widget
        header = ["Triggered Entity", "Owner", "Mapped Task", "Position", "Trigger Category", "Trigger Condition"]
        self.__table_widget_common_set(self.triggered_entity_table_widget, header)
        col_init_width = [250, 150, 200, 80, 150, 120]
        for col_idx in range(len(col_init_width)):
            self.triggered_entity_table_widget.setColumnWidth(col_idx, col_init_width[col_idx])

        self.insert_runnable_data_to_widget()

    def __init_second_page(self):
        select_trace_func_widget = QWidget()
        self.trace_select_all_button = QPushButton(QIcon(":/check_all.svg"), "", self)
        self.trace_cancel_all_button = QPushButton(QIcon(":cancel_all.svg"), "", self)
        button_set_attr(self.trace_select_all_button)
        button_set_attr(self.trace_cancel_all_button)
        select_button_layout = QVBoxLayout()
        select_button_layout.addWidget(self.trace_select_all_button)
        select_button_layout.addWidget(self.trace_cancel_all_button)
        select_button_layout.addStretch(1)
        select_button_layout.setSpacing(10)
        select_button_layout.setContentsMargins(0, 0, 0, 0)

        # central trace function table widget layout
        self.trace_func_table_widget = QTableWidget(self)
        center_layout = QHBoxLayout(select_trace_func_widget)
        center_layout.addLayout(select_button_layout)
        center_layout.addWidget(self.trace_func_table_widget)
        center_layout.setContentsMargins(2, 0, 5, 2)
        center_layout.setSpacing(2)
        self.stack_widget.addWidget(select_trace_func_widget)

        # init attr of trigger entity table widget
        header = ["Trace Functions"]
        self.__table_widget_common_set(self.trace_func_table_widget, header)
        self.trace_func_table_widget.setColumnWidth(0, 400)

    def __table_widget_common_set(self, table_widget, header: list):
        table_widget.setColumnCount(len(header))
        table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table_widget.setHorizontalHeaderLabels(header)
        table_widget.setSelectionBehavior(QAbstractItemView.SelectItems)
        table_widget.verticalHeader().setHidden(True)
        table_widget.setSelectionMode(QAbstractItemView.NoSelection)
        table_widget.setColumnCount(len(header))

    def __init_bottom_ui(self):
        # btn of bottom setting
        self.next_button = QPushButton("next")
        self.back_button = QPushButton("back")
        self.back_button.setDisabled(True)
        self.finish_button = QPushButton("finish")
        self.finish_button.setDisabled(True)
        self.button_cancel = QPushButton("cancel")
        self.next_button.setDisabled(True)
        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.addStretch(1)
        self.bottom_layout.addWidget(self.back_button)
        self.bottom_layout.addWidget(self.next_button)
        self.bottom_layout.addWidget(self.finish_button)
        self.bottom_layout.addWidget(self.button_cancel)
        self.bottom_layout.setContentsMargins(0, 0, 10, 0)

    def __init_overall_layout(self):
        # set overall ui layout
        widget_layout = QVBoxLayout(self)
        widget_layout.addLayout(self.top_layout)
        widget_layout.addWidget(self.__get_ui_seperate_line())
        widget_layout.addWidget(self.stack_widget)
        widget_layout.addWidget(self.__get_ui_seperate_line())
        widget_layout.addLayout(self.bottom_layout)
        widget_layout.setContentsMargins(0, 0, 0, 10)
        self.setWindowIcon(QIcon(":/Home.svg"))
        screen_geometry = QGuiApplication.primaryScreen().geometry()
        self.resize(
            int(screen_geometry.width() * WIDGET_SIZE_FACTOR), int(screen_geometry.height() * WIDGET_SIZE_FACTOR)
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle("Import VFB Trace Function")

    def __get_ui_seperate_line(self, direction=QFrame.HLine) -> QFrame:
        horizon_line = QFrame(self)
        horizon_line.setFrameShape(direction)
        horizon_line.setFrameShadow(QFrame.Sunken)
        return horizon_line

    def __init_UI_layout(self):
        self.__init_top_ui()
        self.__init_bottom_ui()
        self.__init_first_page()
        self.__init_second_page()
        self.__init_overall_layout()
        self.update_hint_info_button_state(self.stack_widget.currentIndex())

    def __init_slot_func(self):
        self.button_cancel.clicked.connect(self.close)
        self.back_button.clicked.connect(self.back_page_slot)
        self.next_button.clicked.connect(self.next_page_slot)
        self.filter_line_edit.textChanged.connect(self.trigger_entity_filter_slot)
        self.mappings_select_all_button.clicked.connect(
            lambda: self.all_select_reverse_select_slot(self.triggered_entity_table_widget, Qt.Checked)
        )
        self.mappings_cancel_all_button.clicked.connect(
            lambda: self.all_select_reverse_select_slot(self.triggered_entity_table_widget, Qt.Unchecked)
        )
        self.trace_select_all_button.clicked.connect(
            lambda: self.all_select_reverse_select_slot(self.trace_func_table_widget, Qt.Checked)
        )
        self.trace_cancel_all_button.clicked.connect(
            lambda: self.all_select_reverse_select_slot(self.trace_func_table_widget, Qt.Unchecked)
        )

        self.triggered_entity_table_widget.cellChanged.connect(self.table_widget_cell_state_changed)
        self.trace_func_table_widget.cellChanged.connect(self.table_widget_cell_state_changed)

        self.mapped_filter_box.stateChanged.connect(self.filter_mapped_task_mappings)
        self.finish_button.clicked.connect(self.finish_button_slot)

    def back_page_slot(self):
        self.stack_widget.setCurrentIndex(self.stack_widget.currentIndex() - 1)

        checked_num = 0
        self.back_button.setDisabled(True)
        self.finish_button.setDisabled(True)
        checked_num = self.__get_checked_num_in_table_widget(self.triggered_entity_table_widget, TRIGGER_ENTITY_COL_IDX)
        self.next_button.setEnabled(True) if checked_num > 0 else self.next_button.setDisabled(True)

        self.update_hint_info_button_state(self.stack_widget.currentIndex(), checked_num)

    def __get_checked_num_in_table_widget(self, table_widget: QTableWidget, col_idx=TRIGGER_ENTITY_COL_IDX):
        checked_num = 0
        for row_idx in range(table_widget.rowCount()):
            table_widget_item = table_widget.item(row_idx, col_idx)
            if table_widget_item and table_widget_item.checkState() == Qt.Checked:
                checked_num += 1
        return checked_num

    def next_page_slot(self):
        self.stack_widget.setCurrentIndex(self.stack_widget.currentIndex() + 1)
        checked_num = 0
        self.show_trace_function_table_info()

        checked_num = self.__get_checked_num_in_table_widget(self.trace_func_table_widget, TRIGGER_ENTITY_COL_IDX)
        self.finish_button.setEnabled(True)
        self.next_button.setDisabled(True)
        self.back_button.setEnabled(True)

        self.update_hint_info_button_state(self.stack_widget.currentIndex(), checked_num)

    def update_hint_info_button_state(self, page_idx, checked_num=0):
        if page_idx == SELECT_TASK_MAPPING_PAGE_IDX:
            self.title_label.setText("Select Task Mappings")
            if checked_num == 0:
                self.hint_message_label.setText("Please select at least one task mapping.")
            else:
                self.hint_message_label.setText(
                    "Select the task mappings to filter for start/return hooks for those on the next page."
                )
        elif page_idx == SELECT_TRACE_FUNCITON_PAGE_IDX:
            self.title_label.setText("Confirmation")
            if checked_num == 0:
                label_text = "Please select at least one trace function, "
                label_text += "or click finish button to clear configured trace functions."
                self.hint_message_label.setText(label_text)
            else:
                confirm_text = "The trace function were filtered for Start/Return Hooks of the task mappings."
                self.hint_message_label.setText(f"{confirm_text} select which of them should be imported.")

    def insert_runnable_data_to_widget(self):

        def is_configured_runnable(configured_runnable_info_list, curr_line_info) -> bool:
            for configured_runnable_info in configured_runnable_info_list.keys():
                if not configured_runnable_info:
                    continue
                if configured_runnable_info == curr_line_info.trigger_entity:
                    return True
            return False

        # get configured trace functions
        configured_trigger_info = self.call_back("get_configured_vfb_trace_info")

        checked_num = 0
        self.triggered_entity_table_widget.setRowCount(len(self.runnable_info_list))
        for runnable_idx in range(len(self.runnable_info_list)):
            trigger_entity_item = QTableWidgetItem(self.runnable_info_list[runnable_idx].trigger_entity)

            self.triggered_entity_table_widget.setItem(runnable_idx, TRIGGER_ENTITY_COL_IDX, trigger_entity_item)
            self.triggered_entity_table_widget.setItem(
                runnable_idx,
                TRIGGER_ENTIRY_OWNER_COL_IDX,
                QTableWidgetItem(self.runnable_info_list[runnable_idx].owner),
            )
            self.triggered_entity_table_widget.setItem(
                runnable_idx, 2, QTableWidgetItem(self.runnable_info_list[runnable_idx].mapped_task)
            )
            self.triggered_entity_table_widget.setItem(
                runnable_idx, 3, QTableWidgetItem(self.runnable_info_list[runnable_idx].position)
            )
            self.triggered_entity_table_widget.setItem(
                runnable_idx, 4, QTableWidgetItem(self.runnable_info_list[runnable_idx].trigger_category)
            )
            self.triggered_entity_table_widget.setItem(
                runnable_idx,
                TRIGGER_CONDITION_COL_IDX,
                QTableWidgetItem(self.runnable_info_list[runnable_idx].trigger_condition),
            )

            # check configured trace functions
            if is_configured_runnable(configured_trigger_info, self.runnable_info_list[runnable_idx]):
                trigger_entity_item.setCheckState(Qt.Checked)
                self.next_button.setEnabled(True)
                checked_num += 1
            else:
                trigger_entity_item.setCheckState(Qt.Unchecked)

        self.update_hint_info_button_state(self.stack_widget.currentIndex(), checked_num)

        self.triggered_entity_table_widget.sortItems(2, Qt.AscendingOrder)
        self.triggered_entity_table_widget.sortItems(0, Qt.AscendingOrder)

    def __runnable_is_mapped(self, row_idx):
        cell_item = self.triggered_entity_table_widget.item(row_idx, MAPE_STATE_COL_IDX)
        return cell_item.text() != ""

    def filter_mapped_task_mappings(self, state):
        if state == Qt.Checked:
            # hide unmapped runnables line
            for row_idx in range(self.triggered_entity_table_widget.rowCount()):
                cell_item = self.triggered_entity_table_widget.item(row_idx, MAPE_STATE_COL_IDX)
                if not cell_item or not self.__runnable_is_mapped(row_idx):
                    self.triggered_entity_table_widget.hideRow(row_idx)
                    self.triggered_entity_table_widget.item(row_idx, TRIGGER_ENTITY_COL_IDX).setCheckState(Qt.Unchecked)
                    checked_num = self.__get_checked_num_in_table_widget(
                        self.triggered_entity_table_widget, TRIGGER_ENTITY_COL_IDX
                    )
                    self.next_button.setEnabled(True) if checked_num > 0 else self.next_button.setDisabled(True)
                    self.update_hint_info_button_state(self.stack_widget.currentIndex(), checked_num)
            self.triggered_entity_table_widget.sortItems(2, Qt.AscendingOrder)
            self.triggered_entity_table_widget.sortItems(0, Qt.AscendingOrder)
        elif state == Qt.Unchecked:
            # recovery the original table
            for row_idx in range(self.triggered_entity_table_widget.rowCount()):
                if self.triggered_entity_table_widget.isRowHidden(row_idx):
                    self.triggered_entity_table_widget.setRowHidden(row_idx, False)

    def all_select_reverse_select_slot(self, table_widget: QTableWidget, check_state, check_col_idx=0):
        for row_idx in range(table_widget.rowCount()):
            if not table_widget.isRowHidden(row_idx):
                table_widget.item(row_idx, check_col_idx).setCheckState(check_state)

    def __check_state_link(self, row_idx, col_idx, check_state):
        table_widget_item = self.trace_func_table_widget.item(row_idx, col_idx)
        if table_widget_item:
            trigger_entity_name = table_widget_item.text()
            if trigger_entity_name.endswith("_Return"):
                common_prefix = trigger_entity_name[0 : -len("Return")]
            elif trigger_entity_name.endswith("_Start"):
                common_prefix = trigger_entity_name[0 : -len("Start")]
            else:
                return
            for row_index in range(self.trace_func_table_widget.rowCount()):
                table_widget_item = self.trace_func_table_widget.item(row_index, TRIGGER_ENTITY_COL_IDX)
                if table_widget_item and table_widget_item.text().startswith(common_prefix):
                    table_widget_item.setCheckState(check_state)

    def table_widget_cell_state_changed(self, row_idx, col_idx):
        current_page_idx = self.stack_widget.currentIndex()
        check_num = 0
        if current_page_idx == SELECT_TASK_MAPPING_PAGE_IDX:
            check_num = self.__get_checked_num_in_table_widget(self.triggered_entity_table_widget)
            if check_num == 0:
                self.next_button.setDisabled(True)
            else:
                self.next_button.setEnabled(True)
        elif current_page_idx == SELECT_TRACE_FUNCITON_PAGE_IDX:
            # check state link
            self.__check_state_link(row_idx, col_idx, self.trace_func_table_widget.item(row_idx, col_idx).checkState())
            check_num = self.__get_checked_num_in_table_widget(self.trace_func_table_widget)
            self.finish_button.setEnabled(True)
        self.update_hint_info_button_state(current_page_idx, check_num)

    def get_trace_function_name(self, trigger_entity: str, owner: str, for_table_display=True):
        common_prefix = ""
        module_name = owner.split(" ")[-1]
        if owner.startswith("Component"):
            common_prefix = f"Rte_Runnable_{module_name}"
        elif owner.startswith("Service Component"):
            common_prefix = f"Rte_Runnable_{module_name}"
        elif owner.startswith("Module"):
            common_prefix = f"SchM_Schedulable_{module_name}"
        else:
            return ["", ""]

        hook_start, hook_return = f"{common_prefix}_{trigger_entity}_Start", f"{common_prefix}_{trigger_entity}_Return"

        return [hook_start, hook_return]

    def show_trace_function_table_info(self):
        # save checked trace function info
        self.__update_selected_trigger_entity_list()

        trace_functions = []
        # show no duplicate trace functions
        function_name_set = set()
        for hook_info in self.hook_info_list:
            hooks = self.get_trace_function_name(hook_info["runnable_name"], hook_info["owner"])
            if hooks != ["", ""]:
                for hook in hooks:
                    if hook not in function_name_set:
                        trace_functions.append(hook)
                        function_name_set.add(hook)

        self.trace_func_table_widget.setRowCount(len(trace_functions))

        for row_idx in range(self.trace_func_table_widget.rowCount()):
            table_widget_item = QTableWidgetItem(trace_functions[row_idx])
            self.trace_func_table_widget.setItem(row_idx, 0, table_widget_item)
            table_widget_item.setCheckState(Qt.Checked)

    def __update_selected_trigger_entity_list(self) -> list:
        self.hook_info_list = []
        table_widget = self.triggered_entity_table_widget
        for row_idx in range(table_widget.rowCount()):
            trigger_table_item = table_widget.item(row_idx, TRIGGER_ENTITY_COL_IDX)
            if trigger_table_item and trigger_table_item.checkState() == Qt.Checked:
                hooks = self.get_trace_function_name(
                    trigger_table_item.text(), table_widget.item(row_idx, TRIGGER_ENTIRY_OWNER_COL_IDX).text()
                )
                hooks = [hook for hook in hooks if hook != ""]
                self.hook_info_list.append(
                    {
                        "runnable_name": trigger_table_item.text(),
                        "owner": table_widget.item(row_idx, TRIGGER_ENTIRY_OWNER_COL_IDX).text(),
                        "hooks": hooks,
                    }
                )

    def trigger_entity_filter_slot(self):
        key_word = self.filter_line_edit.text().lower()

        self.triggered_entity_table_widget.blockSignals(True)
        for row_idx in range(self.triggered_entity_table_widget.rowCount()):
            if self.mapped_filter_box.checkState() == Qt.Checked and not self.__runnable_is_mapped(row_idx):
                continue

            table_widget_item = self.triggered_entity_table_widget.item(row_idx, TRIGGER_ENTITY_COL_IDX)
            if table_widget_item and key_word != "" and key_word in table_widget_item.text().lower():
                self.triggered_entity_table_widget.setRowHidden(row_idx, False)
                self.triggered_entity_table_widget.scrollToItem(table_widget_item)
                table_widget_item.setBackground(QColor("yellow"))
            else:
                self.triggered_entity_table_widget.setRowHidden(row_idx, (key_word != ""))
                table_widget_item.setBackground(QColor("white"))

        self.triggered_entity_table_widget.blockSignals(False)

    def __wirte_trace_function_to_arxml(self, trace_function_list):
        # remove all configured items in arxml data
        self.call_back("clear_vfb_trace_functions", CONTAINER_ECUC_PATH, MODULE_NAME, PARAM_MOD_PATH, PARAM_TAG)
        # write back all functions
        for function_name in trace_function_list:
            self.call_back(
                "bsw_editor_add_param_item_and_write_to_ecuc_arxml",
                function_name,
                PARAM_MOD_PATH,
                MODULE_NAME,
                CONTAINER_ECUC_PATH,
                PARAM_TAG,
                None,
                MODULE_NAME,
            )

    def finish_button_slot(self):
        """
        1. fill back to rte vfb trace funtion lines
        2. add script function in main window menu
        3. script funtion in background -> generate rtm code
        """
        trace_function_list = []
        for row_idx in range(self.trace_func_table_widget.rowCount()):
            table_widget_item = self.trace_func_table_widget.item(row_idx, TRIGGER_ENTITY_COL_IDX)
            if table_widget_item.checkState() == Qt.Checked:
                trace_function_list.append(table_widget_item.text())
        self.__wirte_trace_function_to_arxml(trace_function_list)

        # update RteVfbTraceFunction ui value
        self.update_data_and_view(MODULE_NAME)

        self.close()
