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
from PySide6 import QtGui
from PySide6.QtCore import QEvent, QPoint, QTimer, Qt
from PySide6.QtGui import QIcon, QPalette, QColor, QBrush
from func_module.health_monitor.logger import logger
from cfg_gui.widgets.line_edit import ArgQLineEdit
from cfg_gui.widgets.label import ArgQLabel
from cfg_gui.widgets.table_widget import ArgTableWidget
from cfg_gui.validation.validation_ui import ValidationErrorWindow
from PySide6.QtWidgets import QSizePolicy, QLabel, QAbstractItemView, QDialog, QWidget, QLineEdit, QTableWidgetItem
from PySide6.QtWidgets import QGridLayout, QListWidget, QListWidgetItem, QMenu, QPushButton, QVBoxLayout, QHBoxLayout
from PySide6.QtWidgets import QSpacerItem, QTableWidget, QMessageBox, QToolButton

LIST_WIDGET_MIN_ROW_COUNT = 5


class ArgQListWidgetItem(QListWidgetItem):

    def __init__(self, show_data_dict, callback=None):
        super().__init__()
        self.callback = callback
        self.show_data_dict = show_data_dict
        self.is_lock = self.show_data_dict["is_lock"]
        if self.show_data_dict["cfg_value"] is None:
            gray_color = QColor(220, 220, 220)  # 创建灰色对象
            brush = QBrush(gray_color)  # 使用灰色对象创建 QBrush
            self.setBackground(brush)
        self.setText(self.show_data_dict["cfg_value"])
        self.old_text = self.text()

    def set_user_defined(self):
        self.user_defined = self.callback(
            "bsw_editor_set_user_defined",
            self.show_data_dict["cfg_value"],
            self.show_data_dict["mod_path"],
            self.show_data_dict["module"],
            self.show_data_dict["ecuc_path"],
            self.show_data_dict["tag"],
        )
        self.user_defined = True

    def remove_user_defined(self):
        self.user_defined = self.callback(
            "bsw_editor_remove_user_defined",
            self.show_data_dict["cfg_value"],
            self.show_data_dict["mod_path"],
            self.show_data_dict["module"],
            self.show_data_dict["ecuc_path"],
            self.show_data_dict["tag"],
        )
        self.user_defined = False


class ArgQListWidget(QListWidget):

    def __init__(
        self, show_data_dict, basic_ui_handler, validation_ui, tool_btn, callback=None, over_view_ui=None
    ) -> None:
        super().__init__()
        self.callback = callback
        self.show_data_dict = show_data_dict
        self.basic_ui_handler = basic_ui_handler
        self.validation_ui = validation_ui
        self.over_view_ui = over_view_ui
        self.tool_btn = tool_btn
        self.show_data_dict = show_data_dict
        self.is_lock = show_data_dict["is_lock"]
        self.annotation_status = show_data_dict["annotation_status"]
        self.all_ref_configuration_items_by_ref_target_dict = {}
        self.show_element_usage = ArgTableWidget(self.basic_ui_handler)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setMinimumHeight(
            int(self.fontMetrics().height() * LIST_WIDGET_MIN_ROW_COUNT * 1.2 + 4 * self.frameWidth())
        )
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.right_click_item_slot)

    def init_signal_connect_slot(self):
        self.set_user_defined_action.triggered.connect(self.set_user_defined_slot)
        self.remove_user_defined_action.triggered.connect(self.remove_user_defined_slot)
        self.show_ref_in_basic_editor.triggered.connect(self.show_ref_in_basic_editor_slot)
        self.show_all_ref_configuration_items.triggered.connect(
            self.show_all_ref_configuration_items_by_ref_target_slot
        )

    def ashes_and_locks(self, item):

        if self.is_lock is False:
            if self.annotation_status is False:
                # item.setEnabled(False)
                self.set_user_defined_action.setEnabled(True)
                self.remove_user_defined_action.setEnabled(False)
            elif self.annotation_status is True:
                # item.setEnabled(True)
                self.set_user_defined_action.setEnabled(False)
                self.remove_user_defined_action.setEnabled(True)
            else:
                self.set_user_defined_action.setEnabled(True)
                self.remove_user_defined_action.setEnabled(False)
        else:
            # item.setEnabled(False)
            self.set_user_defined_action.setEnabled(False)
            self.remove_user_defined_action.setEnabled(False)

    def right_click_item_slot(self, pos: QPoint):
        selected_item_list = self.selectedItems()
        if len(selected_item_list) == 0:  # 没有选中item，直接返回，不展示menu
            return
        # Gather the status of user define
        for item in selected_item_list:
            item: ArgQListWidgetItem(self.show_data_dict)

        # Create the right click menu
        menu = QMenu(self)
        self.set_user_defined_action = menu.addAction("Set User Defined")
        self.remove_user_defined_action = menu.addAction("Remove User Defined")
        self.show_ref_in_basic_editor = menu.addAction("Show Referenced Item In Basic Editor (Tree)")
        self.show_all_ref_configuration_items = menu.addAction(
            "Show all ref configuration items that reference this ref target"
        )

        self.init_signal_connect_slot()
        self.ashes_and_locks(item)

        menu.popup(self.mapToGlobal(pos))

    def show_ref_in_basic_editor_slot(self):
        self.basic_ui_handler.ecuc_path_jumps_to_ui(self.selectedItems()[0].data(0))

    def set_user_defined_slot(self):
        selected_item_list = self.selectedItems()
        for item in selected_item_list:
            self.set_user_defined_action.setEnabled(False)
            self.remove_user_defined_action.setEnabled(True)
            self.set_enabled(item, True)
            item: ArgQListWidgetItem
            item.set_user_defined()

    def remove_user_defined_slot(self):
        selected_item_list = self.selectedItems()
        for item in selected_item_list:
            self.set_user_defined_action.setEnabled(True)
            self.remove_user_defined_action.setEnabled(False)
            self.set_enabled(item, False)
            item: ArgQListWidgetItem
            item.remove_user_defined()

    def add_item(self, show_data_dict, callback):
        item = ArgQListWidgetItem(show_data_dict, callback)
        self.set_enabled(item, not show_data_dict["is_lock"])
        self.addItem(item)

    def remove_item(self, basic_validation_handler=None, list_count=None, caller: str = ""):

        element_changed = False
        for item in self.selectedItems():
            item_index: int = self.row(item)
            self.takeItem(self.row(item))
            self.removeItemWidget(item)

            if item is not None:
                element_changed = True
                if list_count > 1:
                    # 如果当前列表中的数量大于1，直接删除实体
                    new_value = item.text()
                    if "" == new_value:
                        new_value = None
                    self.callback(
                        "bsw_editor_remove_param_item_and_write_to_ecuc_arxml",
                        new_value,
                        self.show_data_dict["mod_path"],
                        self.show_data_dict["module"],
                        self.show_data_dict["ecuc_path"],
                        self.show_data_dict["tag"],
                    )
                    # 入栈
                    if caller == "qstring":
                        self.callback(
                            "bsw_editor_qstring_push_stack",
                            item_index,
                            list_count,
                            new_value,
                            "remove",
                            self.show_data_dict,
                            self.callback,
                            self.over_view_ui,
                            self.basic_ui_handler,
                        )
                    elif caller == "qreference":
                        self.callback(
                            "bsw_editor_qreference_push_stack",
                            item_index,
                            list_count,
                            new_value,
                            "remove",
                            self.show_data_dict,
                            self.callback,
                            self.over_view_ui,
                            self.basic_ui_handler,
                        )
                    list_count -= 1
                elif 1 == list_count:
                    # 如果当前列表中数量为1，需要保留该实体，并将value值置为None
                    new_value = None
                    item_text = item.text()
                    self.callback(
                        "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                        new_value,
                        item.text(),
                        self.show_data_dict["mod_path"],
                        self.show_data_dict["module"],
                        self.show_data_dict["ecuc_path"],
                        self.show_data_dict["tag"],
                    )
                    self.show_data_dict["cfg_value"] = new_value
                    # 入栈
                    if caller == "qstring":
                        self.callback(
                            "bsw_editor_qstring_push_stack",
                            item_index,
                            list_count,
                            item_text,
                            "remove",
                            self.show_data_dict,
                            self.callback,
                            self.over_view_ui,
                            self.basic_ui_handler,
                        )
                    elif caller == "qreference":
                        self.callback(
                            "bsw_editor_qreference_push_stack",
                            item_index,
                            list_count,
                            item_text,
                            "remove",
                            self.show_data_dict,
                            self.callback,
                            self.over_view_ui,
                            self.basic_ui_handler,
                        )
                    # 删除最后一个item后,再创建一个灰色的空item
                    self.blockSignals(True)
                    gray_color = QColor(220, 220, 220)  # 创建灰色对象
                    brush = QBrush(gray_color)  # 使用灰色对象创建 QBrush
                    item.setBackground(brush)
                    item.setText(new_value)
                    item.old_text = new_value
                    self.addItem(item)
                    self.blockSignals(False)

        # Validation
        if basic_validation_handler is not None and element_changed:
            basic_validation_handler()
            self.validation_ui.validation_model.update_model_data()

    def remove_item_textual(self):
        # Never remove the last item
        if self.count() == 1:
            return None

        item: ArgQListWidgetItem = self.currentItem()
        if item is None:
            return None
        self.takeItem(self.row(item))
        self.removeItemWidget(item)
        return item.param_val

    def set_enabled(self, widget, is_enabled):

        if is_enabled:
            widget.setFlags(widget.flags() | Qt.ItemIsEditable)
            widget.setForeground(QColor(0, 0, 0))  # 设置文本颜色为黑色
        else:
            widget.setFlags(widget.flags() & ~Qt.ItemIsEditable)  # 禁用该项
            widget.setForeground(QColor(128, 128, 128))  # 设置文本颜色为浅灰色

    def show_all_ref_configuration_items_by_ref_target_slot(self):
        if self.selectedItems()[0].data(0) and "<empty>" != self.selectedItems()[0].data(0):
            self.all_ref_configuration_items_by_ref_target_dict = self.callback(
                "bsw_editor_all_ref_configuration_items_by_ref_target", self.selectedItems()[0].data(0)
            )
            self.show_element_usage.fill_reference_target_table_widget(
                "", self.all_ref_configuration_items_by_ref_target_dict
            )
            if self.show_element_usage.select_reference_target_dialog:
                self.show_element_usage.select_reference_target_dialog.show()


class ArgQStringWidget(QVBoxLayout):

    def __init__(self, show_data_dict, basic_ui_handler, validation_ui, tool_btn, callback=None, over_view_ui=None):
        super().__init__()
        self.show_data_dict = show_data_dict
        self.basic_ui_handler = basic_ui_handler
        self.validation_ui = validation_ui
        self.over_view_ui = over_view_ui
        self.tool_btn = tool_btn
        self.callback = callback
        self.is_lock = show_data_dict["is_lock"]
        self.annotation_status = show_data_dict["annotation_status"]
        self.string_list: ArgQListWidget = ArgQListWidget(
            show_data_dict,
            self.basic_ui_handler,
            self.validation_ui,
            self.tool_btn,
            callback=self.callback,
            over_view_ui=self.over_view_ui,
        )

        self.push_button_add = QPushButton()
        self.push_button_add.setIcon(QIcon(":/add.svg"))
        self.push_button_add.setToolTip("Add")
        self.push_button_remove = QPushButton()
        self.push_button_remove.setIcon(QIcon(":/not_ok.svg"))
        self.push_button_remove.setToolTip("Remove")
        if show_data_dict["is_necessary"] is True:
            self.necessary_icon = QLabel("*")
        else:
            self.necessary_icon = QLabel(" ")
        if self.is_lock is True:
            self.string_list.setEnabled(False)
            self.push_button_add.setEnabled(False)
            self.push_button_remove.setEnabled(False)
        self.init_layout()
        self.init_value()
        self.connect_slot()

    def init_layout(self):
        self.buttons_layout = QVBoxLayout()
        self.buttons_layout.addWidget(self.push_button_add)
        self.buttons_layout.addWidget(self.push_button_remove)
        self.buttons_layout.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Fixed, QSizePolicy.Expanding))
        self.button_and_list_layout = QHBoxLayout()
        self.button_and_list_layout.addLayout(self.buttons_layout)
        self.button_and_list_layout.addWidget(self.string_list)
        self.button_and_list_layout.addWidget(self.necessary_icon)
        self.addLayout(self.button_and_list_layout)

    def init_value(self):
        self.add_list_item(self.show_data_dict, self.callback)

    def connect_slot(self):
        self.push_button_add.clicked.connect(self.add_textual_slot)
        self.push_button_remove.clicked.connect(self.remove_textual_slot)
        self.string_list.itemDoubleClicked.connect(self.select_string_solt)
        self.string_list.itemChanged.connect(self.string_item_changed_slot)

    def select_string_solt(self, item):
        self.double_clicked_string = item
        if "" == self.double_clicked_string.text():
            self.show_data_dict["cfg_value"] = None
        else:
            self.show_data_dict["cfg_value"] = self.double_clicked_string.text()

    def add_textual_slot(self):
        # self.show_data_dict["cfg_value"] = "<empty>"
        self.callback(
            "bsw_editor_add_param_item_and_write_to_ecuc_arxml",
            "<empty>",
            self.show_data_dict["mod_path"],
            self.show_data_dict["module_name"],
            self.show_data_dict["ecuc_path"],
            self.show_data_dict["tag"],
            None,
            self.show_data_dict["module"],
        )
        # param_val = AutosarUtil.set_parameter(self.parent_node, self.string_param_def)
        self.show_data_dict["cfg_value"] = "<empty>"
        self.add_list_item(self.show_data_dict, self.callback)

        # 入栈
        self.callback(
            "bsw_editor_qstring_push_stack",
            self.string_list.count() - 1,
            self.string_list.count(),
            "<empty>",
            "add",
            self.show_data_dict,
            self.callback,
            self.over_view_ui,
            self.basic_ui_handler,
        )

    def add_list_item(self, show_data_dict, callback):
        # if show_data_dict["cfg_value"]:
        if hasattr(self.string_list, "add_item"):
            self.string_list.add_item(show_data_dict, callback)

    def remove_textual_slot(self):
        self.string_list.remove_item(self.basic_validation_handler, self.string_list.count(), "qstring")

    def string_item_changed_slot(self, item: ArgQListWidgetItem):
        if "" == item.text():
            new_value = None
            # 设置灰色背景色
            self.string_list.blockSignals(True)
            gray_color = QColor(220, 220, 220)
            brush = QBrush(gray_color)
            item.setBackground(brush)
            self.string_list.blockSignals(False)
        else:
            new_value = item.text()
        self.callback(
            "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
            new_value,
            self.show_data_dict["cfg_value"],
            self.show_data_dict["mod_path"],
            self.show_data_dict["module"],
            self.show_data_dict["ecuc_path"],
            self.show_data_dict["tag"],
        )
        self.show_data_dict["cfg_value"] = new_value

        # 入栈
        self.callback(
            "bsw_editor_qstring_push_stack",
            self.string_list.row(item),
            self.count(),
            [item.old_text, new_value],
            "change",
            self.show_data_dict,
            self.callback,
            self.over_view_ui,
            self.basic_ui_handler,
        )
        # 更新旧文本
        item.old_text = new_value

    def basic_validation_handler(self):
        cbk_param = {}
        cbk_param["param_name"] = self.show_data_dict["label_name"]
        cbk_param["check_text"] = self.show_data_dict["cfg_value"]
        cbk_param["param_path"] = self.show_data_dict["ecuc_path"] + "/" + self.show_data_dict["label_name"]
        cbk_param["tag"] = self.show_data_dict["tag"]
        cbk_param["lower_multiplicity"] = self.show_data_dict["lower_multiplicity"]
        cbk_param["upper_multiplicity"] = self.show_data_dict["upper_multiplicity"]
        cbk_param["upper_multiplicity_infinite"] = self.show_data_dict["upper_multiplicity_infinite"]
        cbk_param["is_necessary"] = self.show_data_dict["is_necessary"]
        cbk_param["max_value"] = self.show_data_dict["max_value"]
        cbk_param["min_value"] = self.show_data_dict["min_value"]
        cbk_param["max_length"] = self.show_data_dict["max_length"]
        cbk_param["min_length"] = self.show_data_dict["min_length"]
        cbk_param["mod_path"] = self.show_data_dict["mod_path"]

        ui_result_list = self.callback("validation_param", cbk_param)

        if len(ui_result_list) > 0:
            failed_result_list = []
            for validation_result in ui_result_list:
                if "fail" == validation_result.result:
                    ui_res_dict = {
                        "summary": validation_result.summary,
                        "message": validation_result.message,
                        "validation_mark": validation_result.validation_mark,
                        "path": validation_result.path,
                        "auto_solve_list": validation_result.auto_solve_list,
                        "manual_solve_list": validation_result.manual_solve_list,
                    }
                    failed_result_list.append(ui_res_dict)
            if failed_result_list:
                self.set_tool_btn_status(self.tool_btn, "Error", failed_result_list)
            else:
                self.set_tool_btn_status(self.tool_btn, "Pass")  # 拿到结果，首先将控件置为Pass

    def set_tool_btn_status(self, tool_btn, status_type, ui_result_list=[]):
        if tool_btn:
            tool_btn.set_error_down(status_type, ui_result_list, True)
            if "Error" == status_type or "Warning" == status_type or "Hint" == status_type:
                tool_btn.tool_btn_down.setEnabled(True)
            if "Pass" == status_type:
                if len(tool_btn.tool_btn_down.validation_result) == 0:
                    tool_btn.tool_btn_down.setEnabled(False)
                    tool_btn.tool_btn_down.setIcon(QIcon(""))


class ArgQReferenceWidget(QVBoxLayout):

    def __init__(
        self,
        show_data_dict,
        current_layout,
        current_index,
        basic_ui_handler,
        validation_ui,
        textBrowserDescription,
        table_widget_status,
        table_widget_definition,
        callback=None,
        main_window=None,
    ):
        super().__init__()
        self.current_layout = current_layout
        self.current_index = current_index
        self.show_data_dict = show_data_dict
        self.callback = callback
        self.basic_ui_handler = basic_ui_handler
        self.validation_ui = validation_ui
        self.main_window = main_window
        self.over_view_ui = self.main_window.over_view_ui
        self.textBrowserDescription = textBrowserDescription
        self.table_widget_status = table_widget_status
        self.table_widget_definition = table_widget_definition
        self.is_lock = show_data_dict["is_lock"]
        self.upper_multiplicity = show_data_dict["upper_multiplicity"]
        self.upper_multiplicity_infinite = show_data_dict["upper_multiplicity_infinite"]
        self.is_necessary = show_data_dict["is_necessary"]
        self.init_select_reference_target_dialog()
        self.references_target_dict = {"<None>": "<empty>"}
        self.ref_target_list_widget = QListWidget()
        self.ref_target_list_widget.itemDoubleClicked.connect(self.update_ref_target_in_table)
        self.select_reference_target_dialog = None

        # 创建指示控件
        self.tool_btn = ToolBtnWidget(self.main_window)
        self.basic_validation_handler()
        if self.upper_multiplicity_infinite:
            if self.upper_multiplicity_infinite:
                if self.upper_multiplicity:
                    self.upper_multiplicity = max(self.upper_multiplicity, self.upper_multiplicity_infinite)
                else:
                    self.upper_multiplicity = self.upper_multiplicity_infinite

        if 1 == self.upper_multiplicity:

            self.select_ref_target = QPushButton("[...]")
            self.select_ref_target.setFixedSize(30, 23)
            self.select_ref_target.setEnabled(not self.is_lock)
            self.reference_list = ArgQLineEdit(
                show_data_dict,
                self.basic_ui_handler,
                self.validation_ui,
                self.tool_btn,
                self.callback,
                select_ref_target=self.select_ref_target,
                main_window=self.main_window,
            )
            # ref的LineEdit不允许编辑
            self.set_enabled(self.reference_list.line_box, False)
            if hasattr(self.reference_list, "show_ref_in_basic_editor"):
                self.reference_list.show_ref_in_basic_editor.setVisible(True)
            if hasattr(self.reference_list, "show_all_ref_configuration_items"):
                self.reference_list.show_all_ref_configuration_items.setVisible(True)

        elif (
            (self.upper_multiplicity is not None and self.upper_multiplicity > 1)
            or (self.upper_multiplicity_infinite)
            or (self.upper_multiplicity is None)
        ):  # 支持Mod文件多实例配置为None的情况
            self.reference_list = ArgQListWidget(
                show_data_dict,
                self.basic_ui_handler,
                self.validation_ui,
                self.tool_btn,
                callback=self.callback,
                over_view_ui=self.over_view_ui,
            )
            self.reference_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.push_button_add = QPushButton()
            self.push_button_add.setIcon(QIcon(":/add.svg"))
            self.push_button_add.setToolTip("Add")
            self.push_button_remove = QPushButton()
            self.push_button_remove.setIcon(QIcon(":/not_ok.svg"))
            self.push_button_remove.setToolTip("Remove")
            self.path_dialog = QDialog()
            self.path_dialog.setWindowTitle("Select Reference Tartget")
            self.path_dialog.setWindowFlags(Qt.WindowType.WindowCloseButtonHint)
            self.path_dialog.setFixedSize(561, 283)
            self.dialog_layout = QVBoxLayout(self.path_dialog)
            if self.is_lock is True:
                self.reference_list.setEnabled(False)
                self.push_button_add.setEnabled(False)
                self.push_button_remove.setEnabled(False)

        if self.is_necessary:
            self.necessary_icon = QLabel("*")
        else:
            self.necessary_icon = QLabel("")

        if 1 == self.upper_multiplicity:
            self.init_layout_line_edit()
            self.connect_slot_line_edit()
        elif (
            (self.upper_multiplicity is not None and self.upper_multiplicity > 1)
            or (self.upper_multiplicity_infinite)
            or (self.upper_multiplicity is None)
        ):
            self.init_layout()
            self.init_value()
            self.connect_slot()

    def init_layout(self):
        self.buttons_layout = QVBoxLayout()
        self.buttons_layout.addWidget(self.push_button_add)
        self.buttons_layout.addWidget(self.push_button_remove)
        self.buttons_layout.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Fixed, QSizePolicy.Expanding))
        self.button_and_list_layout = QHBoxLayout()
        self.button_and_list_layout.addLayout(self.buttons_layout)
        self.button_and_list_layout.addLayout(self.tool_btn.tool_btn_v_layout)
        self.button_and_list_layout.addWidget(self.reference_list)
        self.button_and_list_layout.addWidget(self.necessary_icon)
        label = ArgQLabel(
            self.show_data_dict,
            self.textBrowserDescription,
            self.table_widget_status,
            self.table_widget_definition,
        )
        self.addWidget(label)
        self.addLayout(self.button_and_list_layout)

    def set_enabled(self, widget: QWidget, is_enabled):

        if hasattr(widget, "setReadOnly"):
            widget.setReadOnly(not is_enabled)
        palette = widget.palette()
        if is_enabled:
            black_color = QtGui.QColor(0, 0, 0)
            palette.setColor(QPalette.ColorRole.Text, black_color)
            widget.setPalette(palette)
            widget.setStyleSheet("background-color: rgb(255, 255, 255);")  # 设置背景颜色为白色
        else:
            black_color = QtGui.QColor(128, 128, 128)
            palette.setColor(QPalette.Text, black_color)  # 设置文本颜色为灰色
            widget.setPalette(palette)
            widget.setStyleSheet("background-color: rgb(240, 240, 240);")  # 设置背景颜色为浅灰色

    def init_layout_line_edit(self):
        self.button_and_list_layout = QGridLayout()
        if self.current_layout:
            label = ArgQLabel(
                self.show_data_dict,
                self.textBrowserDescription,
                self.table_widget_status,
                self.table_widget_definition,
            )
            self.current_layout.addWidget(label, self.current_index, 0)
            self.current_layout.addLayout(self.tool_btn.tool_btn_v_layout, self.current_index, 1)
            self.current_layout.addLayout(self.reference_list, self.current_index, 2)
            self.current_layout.addWidget(self.select_ref_target, self.current_index, 3)

        self.addLayout(self.button_and_list_layout)

    def init_value(self):
        self.add_list_item(self.show_data_dict, self.callback)

    def connect_slot(self):
        self.push_button_add.clicked.connect(self.add_reference_slot)
        self.push_button_remove.clicked.connect(self.remove_reference_slot)
        self.reference_list.itemChanged.connect(self.reference_item_changed_slot)
        self.reference_list.itemDoubleClicked.connect(self.select_reference_target_solt)

    def connect_slot_line_edit(self):
        self.select_ref_target.clicked.connect(self.add_reference_slot)

    def add_reference_slot(self):

        self.select_reference_target_solt(None)

    def update_ref_target_in_table(self):
        pass

    def add_list_item(self, show_data_dict, callback):
        # if show_data_dict["cfg_value"]:
        if hasattr(self.reference_list, "add_item"):
            self.reference_list.add_item(show_data_dict, callback)

    def remove_reference_slot(self):
        self.reference_list.remove_item(self.basic_validation_handler, self.reference_list.count(), "qreference")

    def reference_item_changed_slot(self, item: ArgQListWidgetItem):

        if "" == item.text():
            # 表示选择了<empty>，将value值改为None
            new_value = None
        else:
            # 修改为实际的值
            new_value = item.text()
            self.reference_list.blockSignals(True)
            transparent_color = QColor(0, 0, 0, 0)  # 创建透明颜色对象
            brush = QBrush(transparent_color)  # 使用透明颜色对象创建 QBrush
            item.setBackground(brush)
            self.reference_list.blockSignals(False)
            self.callback(
                "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                new_value,
                self.show_data_dict["cfg_value"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
        self.show_data_dict["cfg_value"] = new_value
        # Validation
        self.basic_validation_handler()
        self.validation_ui.validation_model.update_model_data()
        item_index: int = self.reference_list.row(item)
        # 入栈
        self.callback(
            "bsw_editor_qreference_push_stack",
            item_index,
            self.reference_list.count(),
            [item.old_text, item.text()],
            "change",
            self.show_data_dict,
            self.callback,
            self.over_view_ui,
            self.basic_ui_handler,
        )
        # 更新旧文本
        item.old_text = item.text()

    def init_select_reference_target_dialog(self):
        """
        init select reference target dialog
        """

        def _init_select_reference_target_dialog():
            self.select_reference_target_dialog = QDialog(parent=self.main_window)
            self.select_reference_target_dialog.setWindowTitle("Select Reference Target")
            self.select_reference_target_dialog.setMinimumSize(1150, 472)
            self.select_reference_target_dialog.setMaximumSize(1150, 472)

            self.select_reference_target_tablewidget = QTableWidget(self.select_reference_target_dialog)
            # 设置列数
            self.select_reference_target_tablewidget.setColumnCount(2)
            # 设置表格头
            self.select_reference_target_tablewidget.setHorizontalHeaderLabels(["Short Name", "Package Path"])
            self.select_reference_target_tablewidget.setColumnWidth(0, 400)
            self.select_reference_target_tablewidget.setColumnWidth(1, 680)
            # 将表格变为禁止编辑
            self.select_reference_target_tablewidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
            # 设置表格整行选中
            self.select_reference_target_tablewidget.setSelectionBehavior(QAbstractItemView.SelectRows)
            # 将行与列的高度设置为所显示的内容的宽度高度匹配
            # QTableWidget.resizeColumnsToContents(self.select_reference_target_tablewidget)
            # QTableWidget.resizeRowsToContents(self.select_reference_target_tablewidget)
            self.filter_text = QLineEdit()
            self.filter_text.setPlaceholderText("<Filter>")

            self.select_reference_target_pushbutton = QPushButton("Ok")
            qvboxlayout = QVBoxLayout(self.select_reference_target_dialog)
            qvboxlayout.addWidget(self.filter_text)
            qvboxlayout.addWidget(self.select_reference_target_tablewidget)
            qvboxlayout.addWidget(self.select_reference_target_pushbutton)

            if 1 == self.upper_multiplicity:
                self.select_reference_target_tablewidget.itemDoubleClicked.connect(
                    self.fill_selected_reference_target_line_edit
                )
                self.select_reference_target_pushbutton.clicked.connect(self.fill_selected_reference_target_line_edit)
                self.filter_text.textChanged.connect(self.handle_filter_text_changed_solt)
            elif (self.upper_multiplicity is not None and self.upper_multiplicity > 1) or (
                self.upper_multiplicity_infinite
            ):
                self.select_reference_target_tablewidget.itemDoubleClicked.connect(
                    self.fill_selected_reference_target_slot
                )
                self.select_reference_target_pushbutton.clicked.connect(self.fill_selected_reference_target_slot)
                self.filter_text.textChanged.connect(self.handle_filter_text_changed_solt)

        timer = QTimer(self)
        timer.timeout.connect(_init_select_reference_target_dialog)
        timer.setSingleShot(True)
        timer.start(1)

    def handle_filter_text_changed_solt(self, text):
        """
        不区分大小写
        """

        filter_text = text.lower()
        self.fill_reference_target_table_widget(filter_text)

    def fill_reference_target_table_widget(self, filter_text):
        """
        Populates the obtained reference target
        """
        row_count = 0
        for package_path, short_name in self.references_target_dict.items():
            matched = False
            if filter_text in package_path.lower() or filter_text in short_name.lower():
                matched = True
            if matched:
                row_count = row_count + 1
        # 设置行数
        self.select_reference_target_tablewidget.setRowCount(row_count)
        i = 0
        for package_path, short_name in self.references_target_dict.items():
            matched = False
            if filter_text in package_path.lower() or filter_text in short_name.lower():
                matched = True
            if matched:
                new_item_short_name = QTableWidgetItem(short_name)
                self.select_reference_target_tablewidget.setItem(i, 0, new_item_short_name)
                new_item_package_path = QTableWidgetItem(package_path)
                self.select_reference_target_tablewidget.setItem(i, 1, new_item_package_path)
                i = i + 1

    def select_reference_target_solt(self, item):
        """
        Slot function, Trigger get_reference_target_slot.
        Each bsw module obtains the reference target according to ref_name and
        saves it in self.references_target_dict.

        Arg:
            item : The selected item
        """
        if item:
            if item.flags() & Qt.ItemIsEditable:
                pass
            else:
                return

        if self.show_data_dict["tag"] in [
            "ECUC-SYMBOLIC-NAME-REFERENCE-DEF",
            "ECUC-REFERENCE-DEF",
            "ECUC-CHOICE-REFERENCE-DEF",
        ]:
            self.references_target_dict = self.callback(
                "bsw_editor_get_all_internal_ref_targets_from_ecuc_arxml",
                self.show_data_dict["mod_path"],
                self.show_data_dict["module_name"],
            )
        elif (
            "ECUC-FOREIGN-REFERENCE-DEF" == self.show_data_dict["tag"]
            or "ECUC-INSTANCE-REFERENCE-DEF" == self.show_data_dict["tag"]
        ):
            self.references_target_dict = self.callback(
                "bsw_editor_get_all_foreign_ref_targets_from_foreign_arxml",
                self.show_data_dict["mod_path"],
                self.show_data_dict["module_name"],
            )
        if item is not None:
            del self.references_target_dict["<None>"]
        # Filter referenced configurations
        self.callback(
            "filter_referenced_configurations",
            self.references_target_dict,
            self.show_data_dict["mod_path"],
            self.show_data_dict["module_name"],
            self.show_data_dict["ecuc_path"],
        )
        self.fill_reference_target_table_widget("")

        self.double_clicked_reference_target = item
        self.filter_text.clear()
        if self.select_reference_target_dialog:
            self.select_reference_target_dialog.show()

    def fill_selected_reference_target_line_edit(self):
        """
        Populates the selected reference targt into the UI and
        fires the slot function saved to arxml.
        """

        table_widget: QTableWidget = self.select_reference_target_tablewidget
        for list_item in table_widget.findItems("<empty>", Qt.MatchContains):
            reference_target = list_item.text()
            selected = list_item.isSelected()
            if selected:
                if 1 == self.upper_multiplicity:
                    self.reference_list.line_box.setText(reference_target)
                    self.reference_list.line_box.ecuc_path = self.show_data_dict["ecuc_path"]
                    self.reference_list.line_box.editingFinished.emit()
                    self.select_reference_target_dialog.close()
                elif self.upper_multiplicity > 1:
                    self.reference_list.setText(reference_target)
                    self.select_reference_target_dialog.close()
                break

        for list_item in table_widget.findItems("/", Qt.MatchContains):
            reference_target = list_item.text()
            selected = list_item.isSelected()
            if selected:
                if 1 == self.upper_multiplicity:
                    self.reference_list.line_box.setText(reference_target)
                    self.reference_list.line_box.editingFinished.emit()
                    self.select_reference_target_dialog.close()
                elif self.upper_multiplicity > 1:
                    self.reference_list.setText(reference_target)
                    self.select_reference_target_dialog.close()
                break

    def fill_selected_reference_target_slot(self):
        self.fill_selected_reference_target_handler("/")
        self.fill_selected_reference_target_handler("<empty>")

    def fill_selected_reference_target_handler(self, search_str):
        """
        Populates the selected reference targt into the UI and
        fires the slot function saved to arxml.
        """

        table_widget: QTableWidget = self.select_reference_target_tablewidget
        for list_item in table_widget.findItems(search_str, Qt.MatchContains):
            reference_target = list_item.text()
            selected = list_item.isSelected()
            if selected:
                if self.reference_list.count() >= self.upper_multiplicity:
                    self.msg_box = QMessageBox(
                        QMessageBox.Warning, "Warning", "当前配置项已达到最大允许值,不允许再添加新的配置项！"
                    )
                    self.msg_box.setModal(True)
                    self.msg_box.show()
                    return
                reference_target_items = self.reference_list.findItems(
                    reference_target, Qt.MatchExactly
                )  # Qt.MatchExactly:完全匹配
                if len(reference_target_items):
                    logger.warning("The selected ref target already exists: ", reference_target)
                    self.select_reference_target_dialog.close()
                    return
                if self.double_clicked_reference_target:
                    # 修改item走这条分支
                    # 手动改empty的情况后续要去掉,不用考虑
                    if "<empty>" == reference_target and self.reference_list.count() > 1:
                        self.select_reference_target_dialog.close()
                        return
                    if "<empty>" == reference_target:
                        # 弹窗中选中<empty>，value置为None
                        reference_target = None
                    if "" == self.double_clicked_reference_target.text():
                        self.show_data_dict["cfg_value"] = None
                    else:
                        self.show_data_dict["cfg_value"] = self.double_clicked_reference_target.text()
                    self.double_clicked_reference_target.setText(reference_target)
                else:
                    # 添加item走这条分支
                    empty_items = self.reference_list.findItems("<empty>", Qt.MatchFixedString | Qt.MatchCaseSensitive)
                    if len(empty_items):
                        # 触发item_changed
                        empty_items[0].setText(reference_target)  # Make sure there is one and only one empty
                    else:
                        # 添加empty无效直接return
                        if "<empty>" == reference_target:
                            logger.warning("Selecting <empty> means that the ref target is not added")
                            self.select_reference_target_dialog.close()
                            return
                        per_name = self.show_data_dict["cfg_value"]
                        self.show_data_dict["cfg_value"] = reference_target
                        self.reference_list.add_item(self.show_data_dict, self.callback)
                        if per_name is None or "" == per_name:
                            # 仅有1个空item时add item走这条分支
                            del_item = self.reference_list.item(0)
                            if "" == del_item.text():
                                self.reference_list.blockSignals(True)
                                transparent_color = QColor(0, 0, 0, 0)  # 创建透明颜色对象
                                brush = QBrush(transparent_color)  # 使用透明颜色对象创建 QBrush
                                del_item.setBackground(brush)
                                del_item = self.reference_list.takeItem(0)  # 删除第一个项
                                self.reference_list.insertItem(1, del_item)  # 将第一个项插入到索引为 1 的位置
                                self.reference_list.takeItem(1)
                                self.reference_list.blockSignals(False)
                            # show_data_dict中有obj，直接更新
                            self.callback(
                                "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                                reference_target,
                                per_name,
                                self.show_data_dict["mod_path"],
                                self.show_data_dict["module"],
                                self.show_data_dict["ecuc_path"],
                                self.show_data_dict["tag"],
                            )
                        else:
                            # 有item时add item走这条分支
                            self.callback(
                                "bsw_editor_add_param_item_and_write_to_ecuc_arxml",
                                reference_target,
                                self.show_data_dict["mod_path"],
                                self.show_data_dict["module_name"],
                                self.show_data_dict["ecuc_path"],
                                self.show_data_dict["tag"],
                                None,
                                self.show_data_dict["module"],
                            )
                        # Validation
                        self.basic_validation_handler()

                        # 入栈
                        self.callback(
                            "bsw_editor_qreference_push_stack",
                            self.reference_list.count() - 1,
                            self.reference_list.count(),
                            reference_target,
                            "add",
                            self.show_data_dict,
                            self.callback,
                            self.over_view_ui,
                            self.basic_ui_handler,
                        )

                self.select_reference_target_dialog.close()
                break

    def basic_validation_handler(self):
        cbk_param = {}
        cbk_param["param_name"] = self.show_data_dict["label_name"]
        cbk_param["check_text"] = self.show_data_dict["cfg_value"]
        cbk_param["param_path"] = self.show_data_dict["ecuc_path"] + "/" + self.show_data_dict["label_name"]
        cbk_param["tag"] = self.show_data_dict["tag"]
        cbk_param["lower_multiplicity"] = self.show_data_dict["lower_multiplicity"]
        cbk_param["upper_multiplicity"] = self.show_data_dict["upper_multiplicity"]
        cbk_param["upper_multiplicity_infinite"] = self.show_data_dict["upper_multiplicity_infinite"]
        cbk_param["is_necessary"] = self.show_data_dict["is_necessary"]
        cbk_param["max_value"] = self.show_data_dict["max_value"]
        cbk_param["min_value"] = self.show_data_dict["min_value"]
        cbk_param["max_length"] = self.show_data_dict["max_length"]
        cbk_param["min_length"] = self.show_data_dict["min_length"]
        cbk_param["mod_path"] = self.show_data_dict["mod_path"]

        ui_result_list = self.callback("validation_param", cbk_param)
        if len(ui_result_list) > 0:
            failed_result_list = []
            for validation_result in ui_result_list:
                if "fail" == validation_result.result:
                    ui_res_dict = {
                        "summary": validation_result.summary,
                        "message": validation_result.message,
                        "validation_mark": validation_result.validation_mark,
                        "path": validation_result.path,
                        "auto_solve_list": validation_result.auto_solve_list,
                        "manual_solve_list": validation_result.manual_solve_list,
                    }
                    failed_result_list.append(ui_res_dict)
            if failed_result_list:
                self.set_tool_btn_status(self.tool_btn, "Error", failed_result_list)
            else:
                self.set_tool_btn_status(self.tool_btn, "Pass")  # 拿到结果，首先将控件置为Pass

    def set_tool_btn_status(self, tool_btn, status_type, ui_result_list=[]):
        if tool_btn:
            tool_btn.set_error_down(status_type, ui_result_list, True)
            if "Error" == status_type or "Warning" == status_type or "Hint" == status_type:
                tool_btn.tool_btn_down.setEnabled(True)
            if "Pass" == status_type:
                if len(tool_btn.tool_btn_down.validation_result) == 0:
                    tool_btn.tool_btn_down.setEnabled(False)
                    tool_btn.tool_btn_down.setIcon(QIcon(""))


class ErrorToolBtnDown(QToolButton):
    def __init__(self, main_window, parent: None, validation_result: list = []) -> None:
        super(ErrorToolBtnDown, self).__init__(parent)
        self.validation_result = validation_result  # all validation result
        self.main_window = main_window
        self.param_validation_list = []  # just record param validation result

    def toolTip(self):
        """
        adapt to test case
        """
        all_validation_msg = ""
        for result in self.validation_result:
            all_validation_msg += result.get("message", " ")

        return all_validation_msg

    def __is_same_validation_result(self, result_1, result_2):
        return result_1.get("validation_mark") == result_2.get("validation_mark") and result_1.get(
            "path"
        ) == result_2.get("path")

    def remove_param_validation_list(self):
        tmp_result = []
        for result in self.validation_result:
            error_existed = False
            for in_result in self.param_validation_list:
                if self.__is_same_validation_result(in_result, result):
                    error_existed = True
                    break
            if not error_existed:
                tmp_result.append(result)
        self.validation_result = tmp_result

    def update_param_validation_result(self, param_validation_list):
        self.param_validation_list = param_validation_list

    def append_error_info(self, in_result_list: list):
        for in_result in in_result_list:
            error_existed = False
            for result in self.validation_result:
                if self.__is_same_validation_result(in_result, result):
                    error_existed = True
                    break
            if not error_existed:
                self.validation_result.append(in_result)

    def append_validation_result(self, validation_result_list: list):
        self.validation_result = validation_result_list

    def enterEvent(self, event):
        if self.validation_result is not None and len(self.validation_result) and self.isEnabled():
            if not getattr(self, "error_window", False) or (
                hasattr(self, "error_window") and not self.error_window.isVisible()
            ):
                self.error_window = ValidationErrorWindow(self.validation_result, self.main_window)
                self.error_window.window_hold_on()
                self.error_window.show()
                global_pos = self.mapToGlobal(event.pos())
                self.error_window.move(global_pos.x() + 5, global_pos.y() + 5)

    def leaveEvent(self, a0: QEvent) -> None:
        if (
            hasattr(self, "error_window")
            and self.error_window.isVisible()
            and not self.error_window.get_pin_window_on()
        ):
            self.error_window.window_hold_off()
        super().leaveEvent(a0)


class ToolBtnWidget(QWidget):

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.initUI()

    def initUI(self):

        # 创建指示控件(上)
        self.tool_btn_up = QToolButton(self)
        self.tool_btn_up.setIcon(QIcon("icon.png"))
        # self.tool_btn.setIconSize(self.tool_btn.size())
        self.tool_btn_up.setAutoRaise(True)
        self.tool_btn_up.setFixedSize(13, 13)  # 设置固定大小为13x13像素
        # self.tool_btn_up.hide()
        self.tool_btn_up.setEnabled(False)
        # 创建指示控件(下)
        self.tool_btn_down = ErrorToolBtnDown(self.main_window, self)
        self.tool_btn_down.setIcon(QIcon("icon.png"))
        # self.tool_btn.setIconSize(self.tool_btn.size())
        self.tool_btn_down.setAutoRaise(True)
        self.tool_btn_down.setFixedSize(13, 13)  # 设置固定大小为13x13像素
        # self.tool_btn_down.hide()
        self.tool_btn_down.setEnabled(False)
        self.tool_btn_v_layout = QVBoxLayout()
        self.tool_btn_v_layout.addWidget(self.tool_btn_up)
        self.tool_btn_v_layout.addWidget(self.tool_btn_down)

    def show_error_up(self, message):
        # 此函数被调用时，将显示一个包含错误消息的弹窗
        QMessageBox.critical(self, "Error", message)

    def show_error_down(self, message):
        # 此函数被调用时，将显示一个包含错误消息的弹窗
        QMessageBox.critical(self, "Error", message)

    def set_error_up(self):
        # 此函数被调用时，将显示一个错误符号
        # pixmap = QPixmap('red_x.png')
        # self.tool_btn_up.setIcon(QIcon(pixmap))
        self.tool_btn_up.show()

    def set_error_down(self, error_leve_type, ui_result_list=[], is_param_result=False):
        # 此函数被调用时，将显示一个错误符号
        # self.range_judge.setIcon(QIcon(":/not_ok.svg"))
        if "Error" == error_leve_type:
            self.tool_btn_down.setIcon(QIcon(":/unavailable.svg"))
        elif "Warning" == error_leve_type:
            self.tool_btn_down.setIcon(QIcon(":/validate.png"))
        elif "Hint" == error_leve_type:
            self.tool_btn_down.setIcon(QIcon(":/not_ok.svg"))
        if is_param_result:
            self.tool_btn_down.remove_param_validation_list()
            self.tool_btn_down.update_param_validation_result(ui_result_list)
            self.tool_btn_down.append_error_info(ui_result_list)
        else:
            self.update_error_info(ui_result_list)

    def update_error_info(self, in_result_list: list):
        self.tool_btn_down.validation_result = in_result_list
