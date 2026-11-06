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
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QTreeView,
    QDialog,
    QVBoxLayout,
    QScrollArea,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QBoxLayout,
    QWidget,
    QGridLayout,
    QComboBox,
)
from PySide6.QtCore import QRegularExpression as QRegExp
from PySide6.QtGui import QRegularExpressionValidator as QRegExpValidator
from basic_func_module.file_handler.dbc.definition import MessageDBC, SignalDBC

NO_NEED_TO_SHOW_MESSAGE = [
    "has_signal_groups",
    "header_id",
    "is_fd",
    "senders",
    "signal_groups",
    "signals",
    "is_container",
    "is_extended_frame",
    "is_fd",
]
NO_NEED_TO_SHOW_SIGNAL = [
    "choices",
    "invalid",
    "is_float",
    "is_multiplexer",
    "is_signed",
    "multiplexer_ids",
    "multiplexer_signal",
    "receivers",
    "spn",
    "unit",
]
NEED_TO_SHOW_USE_COMBOBOX = ["header_byte_order", "protocol", "byte_order"]
# message所有属性
MESSAGE_ATTR = [
    "GenMsgStartDelayTime",
    "GenMsgSendType",
    "GenMsgDelayTime",
    "GenMsgCycleTime",
    "VFrameFormat",
    "CANFD_BRS",
    "DiagConnection",
    "DiagRequest",
    "DiagResponse",
    "DiagState",
    "DiagUUDTResponse",
    "GenMsgCycleTimeFast",
    "GenMsgILSupport",
    "GenMsgNrOfRepetition",
    "NmAsrMessage",
]
# signal所有属性
SIGNAL_ATTR = [
    "GenSigStartValue",
    "GenSigSendType",
    "GenSigCycleTime",
    "GenSigCycleTimeActive",
    "GenSigInactiveValue",
    "GenSigRrmark",
    "GenSigTimeoutTime",
    "SystemSignalLongSymbol",
]
# signal字符串类型的属性
SIGNAL_ATTR_STR = ["GenSigRrmark", "SystemSignalLongSymbol"]
# message通用属性，int类型
MESSAGE_GENERAL_ATTR_INT = ["frame_id", "length"]
# signal通用属性，int类型
SIGNAL_GENERAL_ATTR_INT = ["initial", "start", "length"]
# signal通用属性，float类型
SIGNAL_GENERAL_ATTR_FLOAT = ["maximum", "minimum", "offset", "scale"]
# DBC全局属性，str类型
DBC_ATTR_STR = ["ProtocolType", "NmType", "Manufacturer", "DBName", "BusType"]
DBC_DICT_DEPTH = 1
MESSAGE_DICT_DEPTH = 4
SIGNAL_DICT_DEPTH = 5


class EditDBCDetailsUI:

    def __init__(self, pre_import_dict) -> None:
        self.pre_import_dict = pre_import_dict
        self.details_dialog = None
        self.dbc_details_widget = None
        self.current_position = 0
        self.search_results = []
        self.dbc_details_dict = {}
        for key, value in self.pre_import_dict.items():
            if value["parse_result"] is not None:
                if "dbc_name" in value["parse_result"].keys():
                    # if hasattr(value["parse_result"], "dbc_name"):
                    self.dbc_details_dict[value["parse_result"]["dbc_name"]] = value["parse_result"]["details"]
        self.init_dialog()
        self.details_dialog.show()
        # self.details_dialog.activateWindow()
        # self.details_dialog.raise_()

    def init_dialog(self):
        """
        init select reference target dialog
        """
        # def _init_mapping_dialog():
        self.details_dialog = QDialog()
        self.details_dialog.setWindowTitle("DBC Details")
        self.details_dialog.setMinimumSize(1150, 472)
        self.details_dialog.setMaximumSize(1150, 472)
        self.details_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        # self.details_dialog.setWindowFlags(Qt.WindowType.WindowCloseButtonHint)
        # self.details_dialog.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["DBCs"])

        # Convert dictionary to model
        self.dict_to_model(self.model, self.dbc_details_dict)

        # 创建搜索框和按钮
        self.filter_edit = QLineEdit()
        self.prev_button = QPushButton("<")
        self.next_button = QPushButton(">")

        # 创建用于显示搜索结果数量和位置的标签
        self.status_label = QLabel()

        # 创建水平布局，并将控件添加到布局中
        filter_layout = QBoxLayout(QBoxLayout.LeftToRight)
        filter_layout.addWidget(self.filter_edit)
        filter_layout.addWidget(self.status_label)
        filter_layout.addWidget(self.prev_button)
        filter_layout.addWidget(self.next_button)

        self.tree_view = QTreeView(self.details_dialog)
        self.tree_view.setModel(self.model)
        self.tree_view.setAlternatingRowColors(True)

        self.apply_button = QPushButton("OK")
        self.apply_button.clicked.connect(self.accept)
        tree_layout = QHBoxLayout()
        tree_layout.addWidget(self.tree_view)
        self.dbc_details_scroll_area = QScrollArea()
        self.dbc_details_scroll_area.setWidgetResizable(True)
        tree_layout.addWidget(self.dbc_details_scroll_area)

        layout = QVBoxLayout(self.details_dialog)
        layout.addLayout(filter_layout)
        layout.addLayout(tree_layout)
        layout.addWidget(self.apply_button)
        # 连接按钮的点击事件到对应的槽函数
        self.prev_button.clicked.connect(self.go_to_previous_result)
        self.next_button.clicked.connect(self.go_to_next_result)

        # 连接搜索框的文本更改事件到对应的槽函数
        self.filter_edit.textChanged.connect(self.search_text_changed)

        # 连接treeview的clicked信号到槽函数
        self.tree_view.clicked.connect(self.tree_view_clicked)

    def tree_view_clicked(self, index: QModelIndex):
        # 通过index的data方法获取点击的项的数据
        item_data = index.data()

        sub_tree_structure = self.find_element(self.pre_import_dict, item_data)
        # try:
        self.dbc_details_widget = DBCDetialsArgQWidget(sub_tree_structure, self.pre_import_dict)
        # except Exception:
        #     # logger.exception("show param widget occurred exception!")
        #     return
        if self.dbc_details_scroll_area.widget() is not None:
            self.dbc_details_scroll_area.widget().deleteLater()
        self.dbc_details_scroll_area.setWidget(self.dbc_details_widget)

    def find_element(self, dictionary, target_key):
        rv = {}
        if "dbc" == target_key.split(".")[-1]:
            for key, value in dictionary.items():
                if target_key in key:
                    rv[key] = value["parse_result"]["attributes"]["network"]["default_value"]
                    return rv
        for key, value in dictionary.items():
            if key == target_key:
                rv[key] = copy.deepcopy(value)
            elif isinstance(value, dict):
                nested_result = self.find_element(value, target_key)
                if nested_result:
                    rv[key] = nested_result
            elif isinstance(value, MessageDBC):
                for attr in vars(value):
                    if "signals" == attr:
                        nested_result = self.find_element(getattr(value, attr), target_key)
                        if nested_result:
                            rv[key] = nested_result

        return rv

    def search_text_changed(self):
        # 获取搜索关键字
        total_results = 0
        keyword = self.filter_edit.text()

        # 在此处执行搜索逻辑，并得到搜索结果数量和当前位置
        self.search_results = []
        if keyword:
            total_results = self.search_in_tree(
                self.model, self.model.invisibleRootItem(), keyword, self.search_results
            )
        self.current_position = 0 if total_results > 0 else -1
        # self.next_button.setFocus()
        # 更新标签的文本，显示搜索结果数量和当前位置
        self.status_label.setText(f"{self.current_position+1} of {total_results}")

    def search_in_tree(self, model, parent_item, search_keyword, search_results):
        total_results = 0

        for row in range(model.rowCount(parent_item.index())):
            index = model.index(row, 0, parent_item.index())
            node_text = index.data()

            if search_keyword in node_text:
                # 标记找到的节点
                search_results.append(index)
                total_results += 1

            # 继续递归搜索子节点
            total_results += self.search_in_tree(model, model.itemFromIndex(index), search_keyword, search_results)

        return total_results

    def go_to_previous_result(self):
        if self.current_position > 0:
            self.current_position -= 1

        if 0 <= self.current_position < len(self.search_results):
            index = self.search_results[self.current_position]
            self.tree_view.setCurrentIndex(index)
            self.status_label.setText(f"{self.current_position+1} of {len(self.search_results)}")
            self.tree_view.clicked.emit(index)
        # else:
        #     self.status_label.clear()

    def go_to_next_result(self):
        if self.current_position <= len(self.search_results) - 1:
            self.current_position += 1

        if self.current_position < len(self.search_results):
            index = self.search_results[self.current_position]
            self.tree_view.setCurrentIndex(index)
            self.status_label.setText(f"{self.current_position+1} of {len(self.search_results)}")
            self.tree_view.clicked.emit(index)
        # else:
        #     self.status_label.clear()

    def accept(self):
        self.details_dialog.close()

    def dict_to_model_attr(self, item, d):
        if isinstance(d, dict):
            for k, v in d.items():
                child_key_item = QStandardItem(k)
                child_value_item = QStandardItem()
                child_value_item.setData(str(v.value), Qt.EditRole)
                item.appendRow([child_key_item])

    def dict_to_model(self, item, d):
        if isinstance(d, dict):
            for k, v in d.items():
                child_key_item = QStandardItem(k)
                if isinstance(v, dict) or isinstance(v, MessageDBC):
                    item.appendRow([child_key_item])
                    self.dict_to_model(child_key_item, v)
                elif isinstance(v, SignalDBC):
                    item.appendRow([child_key_item])
        elif isinstance(d, MessageDBC):
            for attr in vars(d):
                if "signals" == attr:
                    self.dict_to_model(item, getattr(d, attr))
        else:
            item.setText(str(d))

    def model_to_dict(self, item):
        result = {}
        for row in range(item.rowCount()):
            key_item = item.child(row, 0)
            value_item = item.child(row, 1)

            if key_item.hasChildren():
                result[key_item.text()] = self.model_to_dict(key_item)
            else:
                result[key_item.text()] = value_item.text()

        return result


class DBCDetialsArgQWidget(QWidget):
    ecu_config_path_dict = {}

    def __init__(self, show_data_dict, pre_import_dict):

        super().__init__()
        self.layout: QGridLayout = QGridLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)
        self.show_data_dict = show_data_dict
        self.pre_import_dict = pre_import_dict
        self.show_value, self.show_key = self.get_bottom_value(self.show_data_dict)

        self.setup_ui(self.show_value)

    def get_bottom_value(self, dictionary):
        key_list = []

        while isinstance(dictionary, dict) and len(dictionary) == 1:
            key, value = next(iter(dictionary.items()))
            key_list.append(key)
            dictionary = value

        return dictionary, key_list

    def combobox_add_item(self, attr, widget):

        if attr in ["header_byte_order", "byte_order"]:
            widget.addItem("big_endian")
            widget.addItem("litter_endian")
        elif "protocol" == attr:
            widget.addItem("StandardCAN")
            widget.addItem("StandardCAN_FD")
            widget.addItem("ExtendedCAN")
            widget.addItem("ExtendedCAN_FD")
            widget.addItem("EXTENDED_NO_FD_CAN")
            widget.addItem("STANDARD_NO_FD_CAN")

    # QComboBox控件的槽函数
    def combo_box_changed_solt(self, text):

        self.modify_per_import_dict(self.sender().property("label"), text)

    def try_convert_to_int(self, value, default=0, base=10):
        try:
            return int(value, base)
        except ValueError:
            return default

    def try_convert_to_float(self, value, default=0.0):
        try:
            return float(value)
        except ValueError:
            return default

    def modify_per_import_dict(self, attribute_name, new_value):
        is_message_or_signal_attr = False
        depth = len(self.show_key)

        if MESSAGE_DICT_DEPTH == depth:  # 修改message属性
            obj = self.pre_import_dict[self.show_key[0]][self.show_key[1]][self.show_key[2]][self.show_key[3]]
        elif SIGNAL_DICT_DEPTH == depth:  # 修改signal属性
            obj = self.pre_import_dict[self.show_key[0]][self.show_key[1]][self.show_key[2]][self.show_key[3]].signals[
                self.show_key[4]
            ]

        if attribute_name in MESSAGE_ATTR:
            is_message_or_signal_attr = True
            obj = obj.message_attributes[attribute_name]
        elif attribute_name in SIGNAL_ATTR:
            is_message_or_signal_attr = True
            obj = obj.signal_attributes[attribute_name]

        if is_message_or_signal_attr:
            if attribute_name in SIGNAL_ATTR_STR:
                setattr(obj, "value", str(new_value))
            else:
                setattr(obj, "value", self.try_convert_to_int(new_value))
        else:
            if attribute_name == "frame_id":
                setattr(obj, attribute_name, self.try_convert_to_int(new_value, base=16))
            elif attribute_name in MESSAGE_GENERAL_ATTR_INT + SIGNAL_GENERAL_ATTR_INT:
                setattr(obj, attribute_name, self.try_convert_to_int(new_value))
            elif attribute_name in SIGNAL_GENERAL_ATTR_FLOAT:
                setattr(obj, attribute_name, self.try_convert_to_float(new_value))
            else:  # str类型
                setattr(obj, attribute_name, str(new_value))

    # QLineEdit控件的槽函数
    def line_edit_changed_solt(self, text):

        self.modify_per_import_dict(self.sender().property("label"), text)

    def line_edit_changed_global_solt(self, text):
        attribute_name = self.sender().property("label")
        obj = self.pre_import_dict[self.show_key[0]]["parse_result"]["attributes"]["network"]["default_value"][
            attribute_name
        ]
        if attribute_name in DBC_ATTR_STR:
            obj.value = str(text)
        else:
            obj.value = int(text)

    def on_input_rejected_slot(self):

        pass

    def global_attr_of_dbc_ui(self, show_data_dict):

        for attr_key, attr_value in show_data_dict.items():
            label = QLabel(attr_value.name)
            widget = QLineEdit(str(attr_value.value))
            # QLineEdit控件添加槽函数
            widget.textEdited.connect(self.line_edit_changed_global_solt)
            widget.setProperty("label", label.text())
            row_num = self.layout.rowCount()
            self.layout.addWidget(label, row_num, 0)
            self.layout.addWidget(widget, row_num, 1, 1, 2)

    def add_widget_to_layout(self, label, widget):
        row_num = self.layout.rowCount()
        self.layout.addWidget(label, row_num, 0)
        self.layout.addWidget(widget, row_num, 1, 1, 2)

    def create_line_edit(self, attr, value, read_only=False, validator_reg=None):
        widget = QLineEdit(str(value))
        if read_only:
            widget.setReadOnly(True)
        if validator_reg:
            reg_val = QRegExpValidator(QRegExp(validator_reg))
            widget.setValidator(reg_val)
        widget.inputRejected.connect(self.on_input_rejected_slot)
        widget.textEdited.connect(self.line_edit_changed_solt)
        return widget

    def message_and_signal_attr_of_dbc_ui(self, show_data_dict):
        # 遍历show_data_dict
        for attr, value in vars(show_data_dict).items():
            # 根据属性是否需要使用QComboBox来创建相应的控件
            if attr in NEED_TO_SHOW_USE_COMBOBOX:
                label = QLabel(attr)
                widget = QComboBox()
                widget.setProperty("label", attr)
                # 添加选项
                self.combobox_add_item(attr, widget)
                widget.setCurrentText(getattr(show_data_dict, attr))
                # QComboBox控件添加槽函数
                widget.currentTextChanged.connect(self.combo_box_changed_solt)
                self.add_widget_to_layout(label, widget)
            elif attr in ["message_attributes", "signal_attributes"]:
                for attr_key, attr_value in value.items():
                    label = QLabel(attr_value.name)
                    widget = self.create_line_edit(
                        attr_key,
                        attr_value.value,
                        False,
                        "-?[0-9]+" if attr_key in SIGNAL_ATTR + MESSAGE_ATTR else None,
                    )
                    widget.setProperty("label", attr_value.name)
                    self.add_widget_to_layout(label, widget)
            elif attr in NO_NEED_TO_SHOW_MESSAGE + NO_NEED_TO_SHOW_SIGNAL:
                continue  # 不显示的属性跳过
            else:
                label = QLabel(attr)
                validator_reg = None
                if "frame_id" == attr:  # 十六进制显示
                    validator_reg = "0[xX][0-9a-fA-F]+|-0[xX][0-9a-fA-F]"
                    value = hex(value)
                elif attr in MESSAGE_GENERAL_ATTR_INT + SIGNAL_GENERAL_ATTR_INT:  # int
                    validator_reg = "-?[0-9]+|[0-9]"
                elif attr in SIGNAL_GENERAL_ATTR_FLOAT:  # float
                    validator_reg = "[+-]?\d+(\.\d+)?"
                widget = self.create_line_edit(attr, value, "name" in attr, validator_reg)
                widget.setProperty("label", attr)
                self.add_widget_to_layout(label, widget)

    def setup_ui(self, show_data_dict):

        if DBC_DICT_DEPTH == len(self.show_key):
            self.global_attr_of_dbc_ui(show_data_dict)
        else:
            self.message_and_signal_attr_of_dbc_ui(show_data_dict)
