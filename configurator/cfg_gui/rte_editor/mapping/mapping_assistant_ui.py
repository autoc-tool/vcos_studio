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
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from cfg_gui.rte_editor.mapping.mapping_view_config import MappingViewConfig
from cfg_gui.rte_editor.mapping.mapping_model_config import MappingModelConfig
from cfg_gui.rte_editor.mapping.mapping_table_view import MappingTableView
from cfg_gui.rte_editor.mapping.mapping_table_model import MappingTableModel, MappingTableItem
from cfg_gui.rte_editor.mapping.mapping_table_header_view import MappingTableHeaderView
from cfg_gui.rte_editor.mapping.mapping_filter_proxy_model import MappingFilterProxyModel
from cfg_gui.rte_editor.mapping.mapping_assistant_ui_config import (
    MappingAssistantUIConfig,
    MappingAssistantUIType,
    MappingAssistantPushButtonType,
)


class MappingAssistantUI(QtWidgets.QWidget):

    def __init__(self, config: MappingAssistantUIConfig):
        super().__init__()
        # 初始化表格视图
        self.config = config
        self.table_model_config = MappingModelConfig()
        self.table_model_config.supported_check_state = self.config.supported_check_state
        self.table_model_config.supported_multiple_selection = self.config.supported_multiple_selection
        self.table_model = MappingTableModel(self.table_model_config)
        self.table_view_config = MappingViewConfig()
        self.table_view = MappingTableView(self.table_view_config)
        # self.table_delegate = MappingTableDelegate()
        self.table_proxy_model = MappingFilterProxyModel()
        self.table_header_view = MappingTableHeaderView(self.table_proxy_model)
        # 初始化Filter-Button-Table
        self.button_layout_v = QtWidgets.QVBoxLayout()
        self.select_all_button = QtWidgets.QPushButton(QtGui.QIcon(":/check_all.svg"), "")
        self.select_none_button = QtWidgets.QPushButton(QtGui.QIcon(":/cancel_all.svg"), "")
        self.filter_table_layout_v = QtWidgets.QVBoxLayout()
        self.clear_filter_button = QtWidgets.QPushButton("Clear All Filters")
        self.filter_text_line_edit = QtWidgets.QLineEdit()
        self.button_filter_table_layout_h = QtWidgets.QHBoxLayout()
        # 初始化Page切换按钮布局
        self.page_switch_layout_h = QtWidgets.QHBoxLayout()
        self.page_switch_push_button_dict = {}
        for button in self.config.current_page_push_buttons:
            self.page_switch_push_button_dict[button.name()] = QtWidgets.QPushButton(button.name(), self)
        # 初始化总体布局
        self.assistant_overall_layout_v = QtWidgets.QVBoxLayout(self)
        # 设置布局和信号连接
        self.setup_ui()
        self.setup_signal_handlers()

    def show(self):
        super().show()
        self.table_model.reset_model()
        self.table_view.resizeColumnsToContents()

    def setup_ui(self):
        """设置界面布局"""
        self.setWindowTitle(self.config.current_page_title)
        self.setMinimumSize(1200, 600)
        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        # 设置 TableView
        self.table_model_config.callback_handler = self.table_model_callback_handler
        self.table_proxy_model.setSourceModel(self.table_model)
        self.table_view.setHorizontalHeader(self.table_header_view)
        self.table_view.setModel(self.table_proxy_model)
        # self.table_view.setItemDelegate(self.table_delegate)
        # 设置按钮布局
        if self.config.supported_multiple_selection:
            self.button_layout_v.addWidget(self.select_all_button)
            self.button_layout_v.addWidget(self.select_none_button)
        self.button_layout_v.addStretch(1)
        # 设置Filter
        self.filter_text_line_edit.setPlaceholderText("<Filter>")
        self.filter_text_line_edit.setClearButtonEnabled(True)
        # 设置Filter-Button-Table布局
        self.filter_table_layout_v.addWidget(self.clear_filter_button)
        self.filter_table_layout_v.addWidget(self.filter_text_line_edit)
        self.filter_table_layout_v.addWidget(self.table_view)
        self.button_filter_table_layout_h.addLayout(self.button_layout_v)
        self.button_filter_table_layout_h.addLayout(self.filter_table_layout_v)
        # 设置Page切换按钮布局
        self.page_switch_layout_h.addStretch(1)
        for button, enabled in self.config.current_page_push_buttons.items():
            push_button = self.page_switch_push_button_dict[button.name()]
            push_button.setEnabled(enabled)
            self.page_switch_layout_h.addWidget(push_button)
        # 设置总体布局
        self.assistant_overall_layout_v.addLayout(self.button_filter_table_layout_h)
        self.assistant_overall_layout_v.addLayout(self.page_switch_layout_h)
        self.init_assistant_filter_ui()

    def init_assistant_filter_ui(self):
        if not self.config.has_filter_control:
            return
        #
        # Radio Button Group
        #
        self.radio_button_group = QtWidgets.QButtonGroup(self)
        self.radio_button_group.setExclusive(True)
        # Automatic Matching
        self.automatic_matching_radio_button = QtWidgets.QRadioButton(
            "Automatic Matching(Considers port names and port interface compatibility.)"
        )
        self.assistant_overall_layout_v.addWidget(self.automatic_matching_radio_button)
        self.automatic_matching_radio_button.setChecked(True)
        self.radio_button_group.addButton(self.automatic_matching_radio_button)
        # Manual Name Pattern
        self.manual_name_pattern_definition_radio_button = QtWidgets.QRadioButton("Manual Name Pattern Definition")
        self.assistant_overall_layout_v.addWidget(self.manual_name_pattern_definition_radio_button)
        self.manual_name_pattern_definition_radio_button.setChecked(False)
        self.radio_button_group.addButton(self.manual_name_pattern_definition_radio_button)
        #
        # Manual Name Pattern Definition Group Box
        #
        self.manual_name_pattern_definition_group_box = QtWidgets.QGroupBox()
        self.manual_name_pattern_definition_group_box.setEnabled(False)
        self.assistant_overall_layout_v.addWidget(self.manual_name_pattern_definition_group_box)
        pattern_definition_layout_v = QtWidgets.QVBoxLayout(self.manual_name_pattern_definition_group_box)
        # Pattern Context
        pattern_context_group_box = QtWidgets.QGroupBox("Pattern Context")
        pattern_definition_layout_v.addWidget(pattern_context_group_box)
        radio_button_layout = QtWidgets.QHBoxLayout(pattern_context_group_box)
        if MappingAssistantUIType.PORT_MAPPING_ASSISTANT == self.config.mapping_ui_type:
            self.pport_radio_button = QtWidgets.QRadioButton("Set P-Port pattern matching to R-Port")
            self.rport_radio_button = QtWidgets.QRadioButton("Set R-Port pattern matching to P-Port")
        else:
            self.pport_radio_button = QtWidgets.QRadioButton("Set P-Port pattern matching to Tx Signal")
            self.rport_radio_button = QtWidgets.QRadioButton("Set R-Port pattern matching to Rx Signal")
        self.pport_radio_button.setChecked(True)
        self.rport_radio_button.setChecked(False)
        # 同一个父窗口或布局中，单选按钮默认互斥
        radio_button_layout.addWidget(self.pport_radio_button)
        radio_button_layout.addWidget(self.rport_radio_button)
        # Port Prototype Name Pattern
        port_prototype_name_pattern_group_box = QtWidgets.QGroupBox("Port Prototype Name Pattern")
        pattern_definition_layout_v.addWidget(port_prototype_name_pattern_group_box)
        port_prototype_name_pattern_layout = QtWidgets.QHBoxLayout(port_prototype_name_pattern_group_box)
        self.prefix_label = QtWidgets.QLabel("Prefix ")
        self.prefix_line_edit = QtWidgets.QLineEdit()
        self.postfix_label = QtWidgets.QLabel("Postfix ")
        self.postfix_line_edit = QtWidgets.QLineEdit()
        prefix_layout = QtWidgets.QHBoxLayout()
        prefix_layout.addWidget(self.prefix_label)
        prefix_layout.addWidget(self.prefix_line_edit)
        postfix_layout = QtWidgets.QHBoxLayout()
        postfix_layout.addWidget(self.postfix_label)
        postfix_layout.addWidget(self.postfix_line_edit)
        port_prototype_name_pattern_layout.addLayout(prefix_layout)
        port_prototype_name_pattern_layout.addLayout(postfix_layout)
        # Connect Options
        connect_options_group_box = QtWidgets.QGroupBox("Connect Options")
        pattern_definition_layout_v.addWidget(connect_options_group_box)
        connect_options_layout_h = QtWidgets.QHBoxLayout(connect_options_group_box)
        self.allow_split_check_box = QtWidgets.QCheckBox("Allow split")
        self.match_case_check_box = QtWidgets.QCheckBox("Match case")
        self.allow_merge_check_box = QtWidgets.QCheckBox("Allow merge")
        self.match_whole_word_check_box = QtWidgets.QCheckBox("Match whole word")
        self.match_compatibility_check_box = QtWidgets.QCheckBox("Match Compatibility")
        if MappingAssistantUIType.DATA_MAPPING_ASSISTANT == self.config.mapping_ui_type:
            self.allow_split_check_box.setEnabled(False)
            self.allow_merge_check_box.setEnabled(False)
        connect_options_layout_h.addWidget(self.allow_split_check_box)
        connect_options_layout_h.addWidget(self.match_case_check_box)
        connect_options_layout_h.addWidget(self.allow_merge_check_box)
        connect_options_layout_h.addWidget(self.match_whole_word_check_box)
        connect_options_layout_h.addWidget(self.match_compatibility_check_box)

    def setup_signal_handlers(self):
        self.select_all_button.clicked.connect(self.select_all_clicked_slot)
        self.select_none_button.clicked.connect(self.select_none_clicked_slot)
        self.clear_filter_button.clicked.connect(self.clear_filter_clicked_slot)
        self.filter_text_line_edit.textChanged.connect(self.filter_text_changed_slot)
        self.table_model.modelReset.connect(self.table_layout_changed_slot)
        self.table_proxy_model.layoutChanged.connect(self.table_layout_changed_slot)
        self.table_view.doubleClicked.connect(self.table_double_clicked_slot)
        for button_name, button in self.page_switch_push_button_dict.items():
            if button_name == MappingAssistantPushButtonType.BACK.value:
                button.clicked.connect(self.back_clicked_slot)
            elif button_name == MappingAssistantPushButtonType.NEXT.value:
                button.clicked.connect(self.next_clicked_slot)
            elif button_name == MappingAssistantPushButtonType.FINISH.value:
                button.clicked.connect(self.finish_clicked_slot)
            elif button_name == MappingAssistantPushButtonType.CANCEL.value:
                button.clicked.connect(self.cancel_clicked_slot)
        if self.config.has_filter_control:
            self.radio_button_group.buttonClicked.connect(self.radio_button_changed_slot)

    def select_all_clicked_slot(self):
        for row in range(self.table_proxy_model.rowCount()):
            index = self.table_proxy_model.index(row, 0)
            self.table_proxy_model.setData(index, Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
        self.table_proxy_model.layoutChanged.emit()

    def select_none_clicked_slot(self):
        for row in range(self.table_proxy_model.rowCount()):
            index = self.table_proxy_model.index(row, 0)
            self.table_proxy_model.setData(index, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.table_proxy_model.layoutChanged.emit()

    def clear_filter_clicked_slot(self):
        self.table_proxy_model.clear_all_filter_patterns()
        self.table_header_view.clear_all_filter()
        self.filter_text_line_edit.clear()

    def filter_text_changed_slot(self, text: str):
        self.table_proxy_model.set_filter_pattern(text)

    def table_layout_changed_slot(self):
        row_count = self.table_proxy_model.rowCount()
        self.clear_filter_button.setText(f"Clear All Filters({row_count} items)")

    def switch_next_page(self):
        self.filter_table_layout_v.removeWidget(self.table_view)
        self.table_view.setParent(None)
        page_cache = {}
        page_cache["input_data"] = self.config.input_data
        page_cache["extra_data"] = self.config.table_data
        page_cache["table_view"] = self.table_view
        page_cache["table_model"] = self.table_model
        page_cache["table_proxy_model"] = self.table_proxy_model
        page_cache["table_header_view"] = self.table_header_view
        page_cache["filter_text"] = self.filter_text_line_edit.text()
        page_cache["selected_rows"] = self.get_selected_rows()
        self.config.push_page_cache(page_cache)
        self.config.input_data = None
        self.config.table_data = None
        self.table_model = MappingTableModel(self.table_model_config)
        self.table_proxy_model = MappingFilterProxyModel()
        self.table_header_view = MappingTableHeaderView(self.table_proxy_model)
        self.table_view = MappingTableView(self.table_view_config)
        self.filter_text_line_edit.clear()
        self.table_proxy_model.setSourceModel(self.table_model)
        self.table_view.setHorizontalHeader(self.table_header_view)
        self.table_view.setModel(self.table_proxy_model)
        self.filter_table_layout_v.addWidget(self.table_view)
        self.table_view.resizeColumnsToContents()
        self.table_model.modelReset.connect(self.table_layout_changed_slot)
        self.table_proxy_model.layoutChanged.connect(self.table_layout_changed_slot)
        self.table_view.doubleClicked.connect(self.table_double_clicked_slot)
        self.table_layout_changed_slot()

    def switch_previous_page(self):
        self.filter_table_layout_v.removeWidget(self.table_view)
        self.table_view.deleteLater()
        page_cache = self.config.pop_page_cache()
        self.config.input_data = page_cache["input_data"]
        self.config.table_data = page_cache["extra_data"]
        self.table_view = page_cache["table_view"]
        self.table_model = page_cache["table_model"]
        self.table_proxy_model = page_cache["table_proxy_model"]
        self.table_header_view = page_cache["table_header_view"]
        self.filter_table_layout_v.addWidget(self.table_view)
        self.filter_text_line_edit.setText(page_cache["filter_text"])
        self.table_layout_changed_slot()

    def back_clicked_slot(self):
        res = self.config.previous_page()
        if res:
            self.switch_previous_page()
            self.setWindowTitle(self.config.current_page_title)
            self.page_switch_push_button_dict[MappingAssistantPushButtonType.FINISH.value].setEnabled(False)
            self.page_switch_push_button_dict[MappingAssistantPushButtonType.NEXT.value].setEnabled(True)
            self.table_model_config.supported_check_state = True
        res = self.config.previous_page()
        if res:
            self.config.next_page()
        else:
            self.page_switch_push_button_dict[MappingAssistantPushButtonType.BACK.value].setEnabled(False)

    def next_clicked_slot(self):
        res = self.config.next_page()
        if res:
            self.switch_next_page()
            self.setWindowTitle(self.config.current_page_title)
            self.page_switch_push_button_dict[MappingAssistantPushButtonType.BACK.value].setEnabled(True)
        res = self.config.next_page()
        if res:
            self.config.previous_page()
        else:
            self.page_switch_push_button_dict[MappingAssistantPushButtonType.NEXT.value].setEnabled(False)
            self.page_switch_push_button_dict[MappingAssistantPushButtonType.FINISH.value].setEnabled(True)
            self.table_model_config.supported_check_state = False

    def finish_clicked_slot(self):
        row_data = self.get_selected_row_data()
        self.config.callback_handler("finish_clicked", data=row_data, config=self.config)
        self.close()

    def cancel_clicked_slot(self):
        self.close()

    def radio_button_changed_slot(self):
        self.manual_name_pattern_definition_group_box.setEnabled(
            self.manual_name_pattern_definition_radio_button.isChecked()
        )

    def table_double_clicked_slot(self, index: QtCore.QModelIndex):
        if not index.isValid():
            return
        header_label = self.table_model.headerData(index.column())
        mapping_ui_type = self.config.current_page_header_label_dialogs.get(header_label, None)
        if mapping_ui_type is None:
            return
        self.double_clicked_popup_config = MappingAssistantUIConfig(mapping_ui_type)
        self.double_clicked_popup_config.callback_handler = self.config.callback_handler
        self.double_clicked_popup_config.input_data = self.get_current_row_dict()
        self.double_clicked_popup_ui = MappingAssistantUI(self.double_clicked_popup_config)
        self.double_clicked_popup_ui.show()

    def get_current_row_dict(self):
        index = self.table_view.currentIndex()
        row = index.row()
        current_row = {row: [index.siblingAtColumn(col).data() for col in range(self.table_model.columnCount())]}
        return current_row

    def get_selected_rows(self):
        selected_rows = []
        for row, check_state in self.table_model.check_state_dict.items():
            if check_state != Qt.CheckState.Checked:
                continue
            index = self.table_model.index(row, 0)
            selected_rows.append([index.siblingAtColumn(col).data() for col in range(self.table_model.columnCount())])
        return selected_rows

    def get_selected_row_data(self):
        row_data = []
        for row, check_state in self.table_model.check_state_dict.items():
            if check_state != Qt.CheckState.Checked:
                continue
            index = self.table_model.index(row, 0)
            row_data.append(
                {
                    self.table_model.headerData(col): index.siblingAtColumn(col).data()
                    for col in range(self.table_model.columnCount())
                }
            )
        return row_data

    def get_mapping_filter_dict(self):
        filter_dict = {}
        filter_dict["automatic"] = self.automatic_matching_radio_button.isChecked()
        filter_dict["direction"] = "Tx" if self.pport_radio_button.isChecked() else "Rx"
        filter_dict["prefix"] = self.prefix_line_edit.text()
        filter_dict["postfix"] = self.postfix_line_edit.text()
        filter_dict["allow_split"] = self.allow_split_check_box.isChecked()
        filter_dict["match_case"] = self.match_case_check_box.isChecked()
        filter_dict["allow_merge"] = self.allow_merge_check_box.isChecked()
        filter_dict["match_whole_word"] = self.match_whole_word_check_box.isChecked()
        filter_dict["match_compatibility"] = self.match_compatibility_check_box.isChecked()
        return filter_dict

    def table_model_callback_handler(self, name, **kwargs):
        if name == "get_table_item_list":
            table_data_list = self.config.callback_handler("get_table_item_list", config=self.config)
            return [
                [
                    MappingTableItem({"data": data, "column": column}, self.table_model_callback_handler)
                    for column, data in enumerate(column_data)
                ]
                for column_data in table_data_list
            ]
        if name == "get_table_header_list":
            return self.config.current_page_header_labels
        if name == "get_table_item_text":
            text = self.config.callback_handler("get_table_item_text", config=self.config, **kwargs)
            return text or ""
        if name == "get_table_item_flags":
            return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
