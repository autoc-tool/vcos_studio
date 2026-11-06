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
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt
from typing import Callable
from func_module.mapping.port_mapping_core import MT_Index
from ui_adaptor.ui_interaction.ui_logger import logger
from cfg_gui.rte_editor.mapping.mapping_view_config import MappingViewConfig
from cfg_gui.rte_editor.mapping.mapping_model_config import MappingModelConfig
from cfg_gui.rte_editor.mapping.mapping_tree_view import MappingTreeView
from cfg_gui.rte_editor.mapping.mapping_tree_model import MappingTreeModel, MappingTreeItem
from cfg_gui.rte_editor.mapping.mapping_table_view import MappingTableView
from cfg_gui.rte_editor.mapping.mapping_table_model import MappingTableModel, MappingTableItem
from cfg_gui.rte_editor.mapping.mapping_table_header_view import MappingTableHeaderView
from cfg_gui.rte_editor.mapping.mapping_filter_proxy_model import MappingFilterProxyModel
from cfg_gui.rte_editor.mapping.mapping_assistant_ui import MappingAssistantUI
from cfg_gui.rte_editor.mapping.mapping_assistant_ui_config import MappingAssistantUIConfig, MappingAssistantUIType


class ServiceMappingUI(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.callback = None
        self.init_callback_param_dict()
        # 初始化树形视图
        self.tree_model_config = MappingModelConfig()
        self.tree_model = MappingTreeModel(self.tree_model_config)
        self.tree_view_config = MappingViewConfig()
        self.tree_view_config.context_menu_policy = Qt.ContextMenuPolicy.CustomContextMenu
        self.tree_view = MappingTreeView(self.tree_view_config)
        # 初始化表格视图
        self.table_model_config = MappingModelConfig()
        self.table_model = MappingTableModel(self.table_model_config)
        self.table_view_config = MappingViewConfig()
        self.table_view_config.menu_options = {
            "Connect": [":/add.svg", self.connect_port_solt],
            "Disconnect": [":/not_ok.svg", self.disconnect_port_solt]
        }
        self.table_view = MappingTableView(self.table_view_config)
        self.table_proxy_model = MappingFilterProxyModel()
        self.table_header_view = MappingTableHeaderView(self.table_proxy_model)
        # 初始化布局控件
        self.vertical_layout = QtWidgets.QVBoxLayout(self)
        self.assistant_text_lable = QtWidgets.QLabel()
        assistant_link_text = "Component Connection Assistant"
        assistant_text_info = "create application connectors."
        self.assistant_text = f'Use the <a href="#" style="text-decoration:underline;color:blue;">{assistant_link_text}</a> {assistant_text_info}'
        self.button_layout_v = QtWidgets.QVBoxLayout()
        self.all_port_push_button = QtWidgets.QPushButton("All")
        self.p_port_push_button = QtWidgets.QPushButton("P")
        self.r_port_push_button = QtWidgets.QPushButton("R")
        self.pr_port_push_button = QtWidgets.QPushButton("PR")
        self.button_group = QtWidgets.QButtonGroup()
        self.filter_table_layout_v = QtWidgets.QVBoxLayout()
        self.clear_filter_button = QtWidgets.QPushButton("Clear All Filters")
        self.filter_text = QtWidgets.QLineEdit()
        self.splitter = QtWidgets.QSplitter(Qt.Orientation.Horizontal)
        self.button_filter_table_widget = QtWidgets.QWidget()
        self.button_filter_table_layout_h = QtWidgets.QHBoxLayout()
        # 设置布局和信号连接
        self.setup_ui()
        self.setup_signal_handlers()

    def init_callback_param_dict(self):
        self.callback_param_dict = {}
        # 右键callback参数字典
        self.callback_param_dict["row_items"] = {}
        self.callback_param_dict["swc_name"] = ""
        self.callback_param_dict["item_name"] = ""
        self.callback_param_dict["filter_name"] = ""
        # 助手callback参数字典
        self.callback_param_dict["filter"] = {}
        self.callback_param_dict["mapping_data"] = []
        self.callback_param_dict["selected_data"] = []
        # 助手二级Select Component Prototype弹窗callback参数字典
        self.callback_param_dict["row_items"] = {}  # Component Connection Confirm页面中双击所在行的数据
        self.callback_param_dict["confirmed_data_dict"] = {}  # Component Connection Confirm页面的表格数据
        self.callback_param_dict["component_row_items"] = {}  # 二级Select Component Prototype弹窗中选择的数据

    def setup_ui(self):
        """设置界面布局"""
        # 设置 TreeView
        self.tree_model_config.callback_handler = self.tree_model_callback_handler
        self.tree_view.setModel(self.tree_model)
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
        self.button_group.addButton(self.p_port_push_button)
        self.button_group.addButton(self.r_port_push_button)
        self.button_group.addButton(self.pr_port_push_button)
        # 设置All Port按钮
        self.all_port_push_button.setToolTip("Connector Prototype List All Ports View")
        self.all_port_push_button.setFixedSize(30, 30)
        self.all_port_push_button.setCheckable(True)
        self.all_port_push_button.setChecked(True)
        # 设置P Port按钮
        self.p_port_push_button.setToolTip("Connector Prototype List P-Port View")
        self.p_port_push_button.setFixedSize(30, 30)
        self.p_port_push_button.setCheckable(True)
        # 设置R Port按钮
        self.r_port_push_button.setToolTip("Connector Prototype List R-Port View")
        self.r_port_push_button.setFixedSize(30, 30)
        self.r_port_push_button.setCheckable(True)
        # 设置PR Port按钮
        self.pr_port_push_button.setToolTip("Connector Prototype List PR-Port View")
        self.pr_port_push_button.setFixedSize(30, 30)
        self.pr_port_push_button.setCheckable(True)
        # 设置按钮布局
        self.button_layout_v.addWidget(self.all_port_push_button)
        self.button_layout_v.addWidget(self.p_port_push_button)
        self.button_layout_v.addWidget(self.r_port_push_button)
        self.button_layout_v.addWidget(self.pr_port_push_button)
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
        # 设置Tree-Table布局
        self.splitter.addWidget(self.tree_view)
        self.splitter.addWidget(self.button_filter_table_widget)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        # 设置整体布局
        self.vertical_layout.addWidget(self.assistant_text_lable)
        self.vertical_layout.addWidget(self.splitter)
        self.vertical_layout.setStretch(0, 1)
        self.vertical_layout.setStretch(1, 999)

    def set_callback(self, callback: Callable):
        """设置UIAdaptor callback"""
        self.callback = callback

    def setup_signal_handlers(self):
        self.tree_view.clicked.connect(self.tree_view_clicked_slot)
        self.assistant_text_lable.linkActivated.connect(self.assistant_link_activated_slot)
        self.button_group.buttonClicked.connect(self.port_button_clicked_slot)
        self.clear_filter_button.clicked.connect(self.clear_filter_button_clicked_slot)
        self.filter_text.textChanged.connect(self.filter_text_changed_solt)
        self.table_model.modelReset.connect(self.table_layout_changed_slot)
        self.table_proxy_model.layoutChanged.connect(self.table_layout_changed_slot)

    def tree_view_clicked_slot(self, index: QtCore.QModelIndex):
        text = index.data()
        if text == "ECU_Composition":
            self.table_proxy_model.clear_filter_column_patterns(MT_Index.Component)
        else:
            self.table_proxy_model.set_filter_column_patterns(MT_Index.Component, {index.data()})

    def assistant_link_activated_slot(self, link: str):
        if not callable(self.callback):
            logger.error("ServiceMappingUI callback is not callable")
            return
        self.mapping_assistant_config = MappingAssistantUIConfig(MappingAssistantUIType.PORT_MAPPING_ASSISTANT)
        self.mapping_assistant_config.has_filter_control = True
        self.mapping_assistant_config.callback_handler = self.assistant_table_model_callback_handler
        self.mapping_assistant_ui = MappingAssistantUI(self.mapping_assistant_config)
        self.mapping_assistant_ui.show()

    def port_button_clicked_slot(self, button: QtWidgets.QPushButton):
        text = button.text()
        if text == self.all_port_push_button.text():
            patterns = {"P-Port", "R-Port", "PR-Port"}
        elif text == self.p_port_push_button.text():
            patterns = {"P-Port"}
        elif text == self.r_port_push_button.text():
            patterns = {"R-Port"}
        elif text == self.pr_port_push_button.text():
            patterns = {"PR-Port"}
        else:
            patterns = set()
        self.table_proxy_model.set_filter_column_patterns(MT_Index.Port_Direction, patterns)

    def clear_filter_button_clicked_slot(self):
        self.filter_text.clear()
        self.all_port_push_button.setChecked(True)
        self.tree_view.setCurrentIndex(self.tree_model.index(0))
        self.table_header_view.clear_all_filter()
        self.table_proxy_model.clear_all_filter_patterns()

    def filter_text_changed_solt(self, text: str):
        self.table_proxy_model.set_filter_pattern(text)

    def connect_port_solt(self):
        if not callable(self.callback):
            logger.error("ServiceMappingUI callback is not callable")
            return
        self.mapping_assistant_config = MappingAssistantUIConfig(MappingAssistantUIType.SELECT_PORT_PROTOTYPE)
        self.mapping_assistant_config.callback_handler = self.assistant_table_model_callback_handler
        self.mapping_assistant_config.input_data = self.get_current_row_dict()
        self.mapping_assistant_ui = MappingAssistantUI(self.mapping_assistant_config)
        self.mapping_assistant_ui.show()

    def disconnect_port_solt(self):
        if not callable(self.callback):
            logger.error("ServiceMappingUI callback is not callable")
            return
        self.init_callback_param_dict()
        self.callback_param_dict["row_items"] = self.get_current_row_dict()
        self.callback("service_mapping_rte_right_click_disconnect", self.callback_param_dict)
        self.table_model.reset_model()

    def table_layout_changed_slot(self):
        row_count = self.table_proxy_model.rowCount()
        self.clear_filter_button.setText(f"Clear All Filters({row_count} items)")

    def tree_model_callback_handler(self, name: str, **kwargs):
        if not callable(self.callback):
            logger.info("ServiceMappingUI callback is not callable")
            return
        if name == "get_tree_root_item":
            root_item = MappingTreeItem("root")
            ecu_composition_item = MappingTreeItem("ECU_Composition", root_item)
            all_component_name_list = self.callback("service_mapping_get_all_service_component_name_to_update",
                                                    "service_mapping") or []
            for component_name in all_component_name_list:
                ecu_composition_item.append_child(MappingTreeItem(component_name))
            return root_item
        if name == "get_tree_item_text":
            return kwargs["data"]
        if name == "get_tree_item_flags":
            return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

    def main_table_model_callback_handler(self, name: str, **kwargs):
        if not callable(self.callback):
            logger.info("ServiceMappingUI callback is not callable")
            return
        if name == "get_table_item_list":
            self.init_callback_param_dict()
            self.callback_param_dict["item_name"] = "PR"
            table_data_list = self.callback("service_mapping_get_main_table_data", self.callback_param_dict)
            return [[MappingTableItem(data[1], self.main_table_model_callback_handler)
                     for data in column_data]
                    for column_data in table_data_list]
        if name == "get_table_header_list":
            return MT_Index.get_header_list()
        if name == "get_table_item_text":
            return kwargs["data"]
        if name == "get_table_item_flags":
            return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

    def assistant_table_model_callback_handler(self, name: str, **kwargs):
        if not callable(self.callback):
            logger.info("ServiceMappingUI callback is not callable")
            return
        self.init_callback_param_dict()
        config: MappingAssistantUIConfig = kwargs["config"]

        if name == "get_table_item_list":
            if config.mapping_ui_type == MappingAssistantUIType.PORT_MAPPING_ASSISTANT:
                if config.current_page_title == "Select Component Prototypes":
                    return self.callback("service_mapping_rte_open_assistant", self.callback_param_dict)
                if config.current_page_title == "Select Port Prototypes":
                    page_cache = self.mapping_assistant_config.previous_page_cache()
                    self.callback_param_dict["selected_data"] = self.get_selected_data(page_cache)
                    return self.callback("service_mapping_first_level_next", self.callback_param_dict)
                if config.current_page_title == "Component Connection Confirm":
                    if config.table_data:
                        return config.table_data
                    page_cache = self.mapping_assistant_config.previous_page_cache()
                    self.callback_param_dict["selected_data"] = self.get_selected_data(page_cache)
                    self.callback_param_dict["filter"] = self.mapping_assistant_ui.get_mapping_filter_dict()
                    if self.callback_param_dict["filter"]["automatic"]:
                        self.callback_param_dict["filter"]["match_case"] = True
                        self.callback_param_dict["filter"]["match_whole_word"] = True
                    config.table_data = self.callback("service_mapping_second_level_next", self.callback_param_dict)
                    return config.table_data
            if config.mapping_ui_type == MappingAssistantUIType.SELECT_PORT_PROTOTYPE:
                self.callback_param_dict["row_items"] = config.input_data
                return self.callback("service_mapping_rte_right_click_connect", self.callback_param_dict)
            if config.mapping_ui_type == MappingAssistantUIType.ASSISTANT_SELECT_COMPONENT_PROTOTYPE:
                self.callback_param_dict["row_items"] = config.input_data
                return self.callback("service_mapping_third_level_double_click_component", self.callback_param_dict)
            if config.mapping_ui_type == MappingAssistantUIType.ASSISTANT_SELECT_PORT_PROTOTYPE:
                self.callback_param_dict["row_items"] = config.input_data
                return self.callback("service_mapping_third_level_double_click_port", self.callback_param_dict)

        elif name == "get_table_item_text":
            if config.mapping_ui_type & (MappingAssistantUIType.SELECT_PORT_PROTOTYPE |
                                         MappingAssistantUIType.PORT_MAPPING_ASSISTANT |
                                         MappingAssistantUIType.ASSISTANT_SELECT_PORT_PROTOTYPE |
                                         MappingAssistantUIType.ASSISTANT_SELECT_COMPONENT_PROTOTYPE):
                if config.current_page_title == "Component Connection Confirm":
                    return kwargs["data"]["data"]
                else:
                    return "" if kwargs["data"]["column"] == 0 else kwargs["data"]["data"]

        if name == "finish_clicked":
            if config.mapping_ui_type == MappingAssistantUIType.SELECT_PORT_PROTOTYPE:
                self.callback_param_dict["row_items"] = kwargs["data"]
                self.callback("service_mapping_first_level_finish", self.callback_param_dict)
                self.table_model.reset_model()
                return
            if config.mapping_ui_type == MappingAssistantUIType.PORT_MAPPING_ASSISTANT:
                self.callback_param_dict["mapping_data"] = config.table_data
                self.callback("service_mapping_third_level_finish", self.callback_param_dict)
                self.table_model.reset_model()
                return
            if config.mapping_ui_type == MappingAssistantUIType.ASSISTANT_SELECT_COMPONENT_PROTOTYPE:
                self.callback_param_dict["row_items"] = config.input_data
                self.callback_param_dict["confirmed_data_dict"] = self.mapping_assistant_ui.config.table_data
                self.callback_param_dict["component_row_items"] = kwargs["data"]
                self.callback("service_mapping_third_level_component_finish", self.callback_param_dict)
                self.mapping_assistant_ui.table_model.reset_model()
                return
            if config.mapping_ui_type == MappingAssistantUIType.ASSISTANT_SELECT_PORT_PROTOTYPE:
                self.callback_param_dict["row_items"] = config.input_data
                self.callback_param_dict["confirmed_data_dict"] = self.mapping_assistant_ui.config.table_data
                self.callback_param_dict["port_row_items"] = kwargs["data"]
                self.callback("service_mapping_third_level_port_finish", self.callback_param_dict)
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
        self.tree_model.reset_model()
        self.tree_view.restore_tree_expanded_status()
        self.table_model.reset_model()

    def update_tree(self):
        self.tree_model.reset_model()
        self.tree_view.restore_tree_expanded_status()
