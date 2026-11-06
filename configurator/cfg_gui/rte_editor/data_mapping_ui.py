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
from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from typing import Callable
from ui_adaptor.func_logic_layer.data_mapping_func import DMEditor_MainUI_Idx
from ui_adaptor.ui_interaction.ui_logger import logger
from cfg_gui.rte_editor.mapping.mapping_view_config import MappingViewConfig
from cfg_gui.rte_editor.mapping.mapping_model_config import MappingModelConfig
from cfg_gui.rte_editor.mapping.mapping_table_view import MappingTableView
from cfg_gui.rte_editor.mapping.mapping_table_model import MappingTableModel, MappingTableItem
from cfg_gui.rte_editor.mapping.mapping_table_header_view import MappingTableHeaderView
from cfg_gui.rte_editor.mapping.mapping_filter_proxy_model import MappingFilterProxyModel
from cfg_gui.rte_editor.mapping.mapping_assistant_ui import MappingAssistantUI
from cfg_gui.rte_editor.mapping.mapping_assistant_ui_config import MappingAssistantUIConfig, MappingAssistantUIType


class DataMappingUI(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.callback = None
        self.init_callback_param_dict()
        # 初始化表格视图
        self.table_model_config = MappingModelConfig()
        self.table_model = MappingTableModel(self.table_model_config)
        self.table_view_config = MappingViewConfig()
        self.table_view_config.menu_options = {
            "Map Communication Elements": [":/add.svg", self.connect_port_solt],
            "Remove Data Mapping": [":/not_ok.svg", self.disconnect_port_solt],
        }
        self.table_view = MappingTableView(self.table_view_config)
        self.table_proxy_model = MappingFilterProxyModel()
        self.table_header_view = MappingTableHeaderView(self.table_proxy_model)
        # 初始化布局控件
        self.vertical_layout = QtWidgets.QVBoxLayout(self)
        self.assistant_text_lable = QtWidgets.QLabel()
        assistant_link_text = "Component Connection Assistant"
        assistant_text_info = "create application connectors."
        self.assistant_text = (
            f'Use the <a href="#" style="text-decoration:underline;color:blue;">{assistant_link_text}'
            f"</a> {assistant_text_info}"
        )
        self.button_layout_v = QtWidgets.QVBoxLayout()
        self.all_port_push_button = QtWidgets.QPushButton("All")
        self.tx_port_push_button = QtWidgets.QPushButton("Tx")
        self.rx_port_push_button = QtWidgets.QPushButton("Rx")
        self.button_group = QtWidgets.QButtonGroup()
        self.filter_table_layout_v = QtWidgets.QVBoxLayout()
        self.clear_filter_button = QtWidgets.QPushButton("Clear All Filters")
        self.filter_text = QtWidgets.QLineEdit()
        self.button_filter_table_widget = QtWidgets.QWidget()
        self.button_filter_table_layout_h = QtWidgets.QHBoxLayout()
        # 设置布局和信号连接
        self.setup_ui()
        self.setup_signal_handlers()

    def init_callback_param_dict(self):
        self.callback_param_dict = {}
        self.callback_param_dict["filter"] = {}
        self.callback_param_dict["row_items"] = {}
        self.callback_param_dict["selected_data"] = []

    def setup_ui(self):
        """设置界面布局"""
        # 设置 TableView
        self.table_model_config.callback_handler = self.main_table_model_callback_handler
        self.table_proxy_model.setSourceModel(self.table_model)
        self.table_view.setHorizontalHeader(self.table_header_view)
        self.table_view.setModel(self.table_proxy_model)
        # 设置助手文本
        self.assistant_text_lable.setText(self.assistant_text)
        # 添加按钮到组中并设置他们互斥
        self.button_group.setExclusive(True)
        self.button_group.addButton(self.all_port_push_button)
        self.button_group.addButton(self.tx_port_push_button)
        self.button_group.addButton(self.rx_port_push_button)
        # 设置All Port按钮
        self.all_port_push_button.setToolTip("Connector Prototype List All Ports View")
        self.all_port_push_button.setFixedSize(30, 30)
        self.all_port_push_button.setCheckable(True)
        self.all_port_push_button.setChecked(True)
        # 设置P Port按钮
        self.tx_port_push_button.setToolTip("Connector Prototype List P-Port View")
        self.tx_port_push_button.setFixedSize(30, 30)
        self.tx_port_push_button.setCheckable(True)
        # 设置R Port按钮
        self.rx_port_push_button.setToolTip("Connector Prototype List R-Port View")
        self.rx_port_push_button.setFixedSize(30, 30)
        self.rx_port_push_button.setCheckable(True)
        # 设置按钮布局
        self.button_layout_v.addWidget(self.all_port_push_button)
        self.button_layout_v.addWidget(self.tx_port_push_button)
        self.button_layout_v.addWidget(self.rx_port_push_button)
        self.button_layout_v.addStretch(1)
        # 设置Filter文本
        self.filter_text.setPlaceholderText("<Filter>")
        # 设置Filter-Button-Table布局
        self.filter_table_layout_v.addWidget(self.clear_filter_button)
        self.filter_table_layout_v.addWidget(self.filter_text)
        self.filter_table_layout_v.addWidget(self.table_view)
        self.button_filter_table_layout_h.addLayout(self.button_layout_v)
        self.button_filter_table_layout_h.addLayout(self.filter_table_layout_v)
        self.button_filter_table_widget.setLayout(self.button_filter_table_layout_h)
        # 设置整体布局
        self.vertical_layout.addWidget(self.assistant_text_lable)
        self.vertical_layout.addWidget(self.button_filter_table_widget)
        self.vertical_layout.setStretch(0, 1)
        self.vertical_layout.setStretch(1, 999)

    def set_callback(self, callback: Callable):
        """设置UIAdaptor callback"""
        self.callback = callback

    def setup_signal_handlers(self):
        self.assistant_text_lable.linkActivated.connect(self.assistant_link_activated_slot)
        self.button_group.buttonClicked.connect(self.port_button_clicked_slot)
        self.clear_filter_button.clicked.connect(self.clear_filter_button_clicked_slot)
        self.filter_text.textChanged.connect(self.filter_text_changed_solt)
        self.table_model.modelReset.connect(self.table_layout_changed_slot)
        self.table_proxy_model.layoutChanged.connect(self.table_layout_changed_slot)

    def assistant_link_activated_slot(self, link: str):
        if not callable(self.callback):
            logger.error("DataMappingUI callback is not callable")
            return
        self.mapping_assistant_config = MappingAssistantUIConfig(MappingAssistantUIType.DATA_MAPPING_ASSISTANT)
        self.mapping_assistant_config.has_filter_control = True
        self.mapping_assistant_config.callback_handler = self.assistant_table_model_callback_handler
        self.mapping_assistant_ui = MappingAssistantUI(self.mapping_assistant_config)
        self.mapping_assistant_ui.show()

    def port_button_clicked_slot(self, button: QtWidgets.QPushButton):
        text = button.text()
        if text == self.all_port_push_button.text():
            patterns = {"Tx", "Rx"}
        elif text == self.tx_port_push_button.text():
            patterns = {"Tx"}
        elif text == self.rx_port_push_button.text():
            patterns = {"Rx"}
        else:
            patterns = set()
        self.table_proxy_model.set_filter_column_patterns(DMEditor_MainUI_Idx.direction.value[0], patterns)

    def clear_filter_button_clicked_slot(self):
        self.filter_text.clear()
        self.all_port_push_button.setChecked(True)
        self.table_header_view.clear_all_filter()
        self.table_proxy_model.clear_all_filter_patterns()

    def filter_text_changed_solt(self, text: str):
        self.table_proxy_model.set_filter_pattern(text)

    def connect_port_solt(self):
        if not callable(self.callback):
            logger.error("DataMappingUI callback is not callable")
            return
        self.mapping_assistant_config = MappingAssistantUIConfig(MappingAssistantUIType.SELECT_SYSTEM_SIGNAL)
        self.mapping_assistant_config.callback_handler = self.assistant_table_model_callback_handler
        self.mapping_assistant_config.input_data = self.get_current_row_dict()
        self.mapping_assistant_ui = MappingAssistantUI(self.mapping_assistant_config)
        self.mapping_assistant_ui.show()

    def disconnect_port_solt(self):
        if not callable(self.callback):
            logger.error("DataMappingUI callback is not callable")
            return
        self.init_callback_param_dict()
        self.callback_param_dict["row_items"] = self.get_current_row_dict()
        self.callback("data_mapping_editor_main_ui_right_click_remove_mapping", self.callback_param_dict)
        self.table_model.reset_model()

    def table_layout_changed_slot(self):
        row_count = self.table_proxy_model.rowCount()
        self.clear_filter_button.setText(f"Clear All Filters({row_count} items)")

    def main_table_model_callback_handler(self, name: str, **kwargs):
        if not callable(self.callback):
            logger.info("DataMappingUI callback is not callable")
            return
        if name == "get_table_item_list":
            table_data_list = self.callback("data_mapping_get_main_table_data")
            return [
                [MappingTableItem(data, self.main_table_model_callback_handler) for data in column_data]
                for column_data in table_data_list
            ]
        if name == "get_table_header_list":
            return DMEditor_MainUI_Idx.get_header_list()
        if name == "get_table_item_text":
            return kwargs["data"]
        if name == "get_table_item_flags":
            return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

    def assistant_table_model_callback_handler(self, name: str, **kwargs):
        if not callable(self.callback):
            logger.info("DataMappingUI callback is not callable")
            return
        self.init_callback_param_dict()
        config: MappingAssistantUIConfig = kwargs["config"]

        if name == "get_table_item_list":
            if config.mapping_ui_type == MappingAssistantUIType.DATA_MAPPING_ASSISTANT:
                if config.current_page_title == "Select Port Prototypes":
                    return self.callback("data_mapping_assistant_main_ui_data_open_assistant")
                if config.current_page_title == "Data Mapping Confirm":
                    if config.input_data:
                        return config.input_data
                    page_cache = self.mapping_assistant_config.previous_page_cache()
                    self.callback_param_dict["selected_data"] = self.get_selected_data(page_cache)
                    self.callback_param_dict["filter"] = self.mapping_assistant_ui.get_mapping_filter_dict()
                    if self.callback_param_dict["filter"]["automatic"]:
                        self.callback_param_dict["filter"] = {}
                    else:
                        self.callback_param_dict["filter"]["case_sensitive"] = self.callback_param_dict["filter"][
                            "match_case"
                        ]
                        self.callback_param_dict["filter"]["whole_word"] = self.callback_param_dict["filter"][
                            "match_whole_word"
                        ]
                    config.input_data = self.callback(
                        "data_mapping_assistant_map_ui_data_after_selecting_port", self.callback_param_dict
                    )
                    return config.input_data
            if config.mapping_ui_type == MappingAssistantUIType.SELECT_SYSTEM_SIGNAL:
                self.callback_param_dict["row_items"] = config.input_data
                config.table_data = config.table_data or self.callback(
                    "data_mapping_rte_right_click_connect", self.callback_param_dict
                )
                return config.table_data
            if config.mapping_ui_type == MappingAssistantUIType.SELECT_REFERENCE_TARGET:
                self.callback_param_dict["row_items"] = config.input_data
                return self.callback("data_mapping_editor_signal_ui_data_from_editor_map_ui", self.callback_param_dict)
            if config.mapping_ui_type == MappingAssistantUIType.ASSISTANT_SELECT_REFERENCE_TARGET:
                self.callback_param_dict["row_items"] = config.input_data
                return self.callback("data_mapping_assistant_signal_ui_data", self.callback_param_dict)

        elif name == "get_table_item_text":
            if config.mapping_ui_type & (
                MappingAssistantUIType.SELECT_SYSTEM_SIGNAL
                | MappingAssistantUIType.SELECT_REFERENCE_TARGET
                | MappingAssistantUIType.ASSISTANT_SELECT_REFERENCE_TARGET
            ):
                return kwargs["data"]["data"]
            if config.mapping_ui_type == MappingAssistantUIType.DATA_MAPPING_ASSISTANT:
                if config.current_page_title == "Select Port Prototypes":
                    return "" if kwargs["data"]["column"] == 0 else kwargs["data"]["data"]
                if config.current_page_title == "Data Mapping Confirm":
                    return kwargs["data"]["data"]

        if name == "finish_clicked":
            if config.mapping_ui_type == MappingAssistantUIType.SELECT_SYSTEM_SIGNAL:
                self.callback_param_dict["row_items"] = {i: v for i, v in enumerate(config.table_data)}
                self.callback("data_mapping_first_level_finish", self.callback_param_dict)
                self.table_model.reset_model()
                return
            if config.mapping_ui_type == MappingAssistantUIType.SELECT_REFERENCE_TARGET:
                self.callback_param_dict["row_items"] = {
                    i: [vv for vv in v.values()] for i, v in enumerate(kwargs["data"])
                }
                config.table_data = self.callback(
                    "data_mapping_editor_map_ui_data_from_editor_signal_ui", self.callback_param_dict
                )
                self.mapping_assistant_ui.table_model.reset_model()
                return
            if config.mapping_ui_type == MappingAssistantUIType.DATA_MAPPING_ASSISTANT:
                self.callback_param_dict["row_items"] = {i: v for i, v in enumerate(config.input_data)}
                self.callback("data_mapping_editor_main_ui_data_after_assistant_mapping", self.callback_param_dict)
                self.table_model.reset_model()
                return
            if config.mapping_ui_type == MappingAssistantUIType.ASSISTANT_SELECT_REFERENCE_TARGET:
                self.callback_param_dict["row_items"] = {
                    i: [vv for vv in v.values()] for i, v in enumerate(kwargs["data"])
                }
                self.mapping_assistant_ui.input_data = self.callback(
                    "data_mapping_assistant_map_ui_data_after_selecting_signal", self.callback_param_dict
                )
                self.mapping_assistant_ui.table_model.reset_model()
                return

    def get_current_row_dict(self):
        index = self.table_view.currentIndex()
        if not index.isValid():
            logger.warning("No valid port selected")
            return {}
        row = index.row()
        current_row_dict = {
            row: [index.siblingAtColumn(column).data() for column in range(self.table_proxy_model.columnCount())]
        }
        return current_row_dict

    def get_selected_data(self, page_cache):
        selected_data = []
        selected_rows = page_cache["selected_rows"]
        for row_data in selected_rows:
            row_data[0] = True
            selected_data.append(row_data)
        return selected_data

    def update(self):
        self.table_model.reset_model()
