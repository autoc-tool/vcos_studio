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
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout
from cfg_gui.widgets.combo_box import ArgQComboBox
from cfg_gui.widgets.check_box import ArgQCheckBox
from cfg_gui.widgets.line_edit import ArgQLineEdit
from cfg_gui.widgets.label import ArgQLabel
from cfg_gui.widgets.list_view import ArgQStringWidget, ArgQReferenceWidget, ToolBtnWidget


class ArgQWidget(QWidget):
    ecu_config_path_dict = {}

    def __init__(self, main_window, show_data_dict, selected_item_path, callback):
        super().__init__()
        self.main_window = main_window
        self.show_data_dict = show_data_dict
        self.reference_container_dict = {}
        self.string_container_dict = {}
        self.grid_layout = QGridLayout()
        self.grid_layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.grid_layout)
        self.location_index = 0
        self.callback = callback
        self.selected_item_path = selected_item_path
        self.setup_ui(self.show_data_dict)

    def create_boolean_param_widget(self, show_data_dict):

        label = ArgQLabel(
            show_data_dict,
            self.main_window.textBrowserDescription,
            self.main_window.table_widget_status,
            self.main_window.table_widget_definition,
        )
        tool_btn = ToolBtnWidget(self.main_window)
        check_box = ArgQCheckBox(
            show_data_dict,
            self.main_window.basic_ui_handler,
            self.main_window.validation_ui,
            tool_btn,
            self.callback,
            main_window=self.main_window,
        )

        return label, tool_btn, check_box

    def create_param_widget(self, show_data_dict, show_data_dicts):

        label = ArgQLabel(
            show_data_dict,
            self.main_window.textBrowserDescription,
            self.main_window.table_widget_status,
            self.main_window.table_widget_definition,
        )
        tool_btn = ToolBtnWidget(self.main_window)
        line_edit = ArgQLineEdit(
            show_data_dict,
            self.main_window.basic_ui_handler,
            self.main_window.validation_ui,
            tool_btn,
            self.callback,
            show_data_dicts,
            main_window=self.main_window,
        )
        return label, tool_btn, line_edit

    def create_enumeration_param_widget(self, show_data_dict):

        label = ArgQLabel(
            show_data_dict,
            self.main_window.textBrowserDescription,
            self.main_window.table_widget_status,
            self.main_window.table_widget_definition,
        )
        tool_btn = ToolBtnWidget(self.main_window)
        combo_box = ArgQComboBox(
            show_data_dict,
            self.main_window.basic_ui_handler,
            self.main_window.validation_ui,
            tool_btn,
            self.callback,
            self.main_window,
        )

        return label, tool_btn, combo_box

    def create_string_param_widget(self, show_data_dict):
        label = ArgQLabel(
            show_data_dict,
            self.main_window.textBrowserDescription,
            self.main_window.table_widget_status,
            self.main_window.table_widget_definition,
        )
        tool_btn = ToolBtnWidget(self.main_window)
        if (show_data_dict["upper_multiplicity_infinite"]) or (
            (show_data_dict["upper_multiplicity"] is not None) and (show_data_dict["upper_multiplicity"] > 1)
        ):
            def_name = show_data_dict["label_name"]
            if def_name in self.string_container_dict.keys():
                string_list_widget: ArgQStringWidget = self.string_container_dict[def_name]
                string_list_widget.add_list_item(show_data_dict, self.callback)
                return label, tool_btn, string_list_widget
            else:
                string_list_widget = ArgQStringWidget(
                    show_data_dict,
                    self.main_window.basic_ui_handler,
                    self.main_window.validation_ui,
                    tool_btn,
                    self.callback,
                    over_view_ui=self.main_window.over_view_ui,
                )
                self.string_container_dict[def_name] = string_list_widget
                return label, tool_btn, string_list_widget
        else:
            lineedit = ArgQLineEdit(
                show_data_dict,
                self.main_window.basic_ui_handler,
                self.main_window.validation_ui,
                tool_btn,
                self.callback,
                main_window=self.main_window,
            )
            return label, tool_btn, lineedit

    def create_symbolic_name_reference_widget(self, show_data_dict, layout, index):

        def_name = show_data_dict["label_name"]

        if def_name in self.reference_container_dict.keys():
            refernce_list_widget: ArgQReferenceWidget = self.reference_container_dict[def_name]
            refernce_list_widget.add_list_item(show_data_dict, self.callback)
            label = ArgQLabel(
                show_data_dict,
                self.main_window.textBrowserDescription,
                self.main_window.table_widget_status,
                self.main_window.table_widget_definition,
            )
            return label, refernce_list_widget
        else:
            widget = ArgQReferenceWidget(
                show_data_dict,
                layout,
                index,
                self.main_window.basic_ui_handler,
                self.main_window.validation_ui,
                self.main_window.textBrowserDescription,
                self.main_window.table_widget_status,
                self.main_window.table_widget_definition,
                self.callback,
                main_window=self.main_window,
            )
            self.reference_container_dict[def_name] = widget
            label = ArgQLabel(
                show_data_dict,
                self.main_window.textBrowserDescription,
                self.main_window.table_widget_status,
                self.main_window.table_widget_definition,
            )
            return label, widget

    def setup_ui(self, show_data_dict):
        """
        遍历show_data_dict, 初始化bsw ui界面
        """

        for key, show_data in show_data_dict.items():
            if 0 == len(show_data):
                continue
            param_tag = show_data[0]["tag"]
            if param_tag in ["ECUC-BOOLEAN-PARAM-DEF"]:
                row_num = self.grid_layout.rowCount()
                label, tool_btn, check_box = self.create_boolean_param_widget(show_data[0])
                self.grid_layout.addWidget(label, row_num, 0)
                self.grid_layout.addLayout(tool_btn.tool_btn_v_layout, row_num, 1)
                self.grid_layout.addLayout(check_box, row_num, 2, 1, 2)
            elif param_tag in [
                "ECUC-INTEGER-PARAM-DEF",
                "SHORT-NAME",
                "ECUC-FLOAT-PARAM-DEF",
                # "ECUC-FUNCTION-NAME-DEF", # function类型的配置项也可能有多实例的情况
            ]:
                row_num = self.grid_layout.rowCount()
                label, tool_btn, line_edit = self.create_param_widget(show_data[0], show_data_dict)
                self.grid_layout.addWidget(label, row_num, 0)
                self.grid_layout.addLayout(tool_btn.tool_btn_v_layout, row_num, 1)
                self.grid_layout.addLayout(line_edit, row_num, 2)
            elif param_tag in ["ECUC-ENUMERATION-PARAM-DEF"]:
                row_num = self.grid_layout.rowCount()
                label, tool_btn, combo_box = self.create_enumeration_param_widget(show_data[0])
                self.grid_layout.addWidget(label, row_num, 0)
                self.grid_layout.addLayout(tool_btn.tool_btn_v_layout, row_num, 1)
                self.grid_layout.addLayout(combo_box, row_num, 2)
            elif param_tag in [
                "ECUC-STRING-PARAM-DEF",
                "ECUC-FUNCTION-NAME-DEF",
            ]:  # function类型的配置项也可能有多实例的情况
                row_num = self.grid_layout.rowCount()
                for string_val_obj in show_data:
                    label, tool_btn, param_widget = self.create_string_param_widget(string_val_obj)
                self.grid_layout.addWidget(label, row_num, 0)
                self.grid_layout.addLayout(tool_btn.tool_btn_v_layout, row_num, 1)
                if param_widget.inherits("ArgQStringWidget"):
                    self.grid_layout.addLayout(param_widget, row_num + 1, 0, 3, 3)
                else:
                    self.grid_layout.addLayout(param_widget, row_num, 2)
            elif param_tag in [
                "ECUC-REFERENCE-DEF",
                "ECUC-INSTANCE-REFERENCE-DEF",
                "ECUC-SYMBOLIC-NAME-REFERENCE-DEF",
                "ECUC-CHOICE-REFERENCE-DEF",
                "ECUC-FOREIGN-REFERENCE-DEF",
            ]:
                row_num = self.grid_layout.rowCount()
                for ref_val_obj in show_data:
                    _, ref_widget = self.create_symbolic_name_reference_widget(ref_val_obj, self.grid_layout, row_num)
                self.grid_layout.addLayout(ref_widget, row_num, 0, 3, 3)

        self.main_window.validation_ui.validation_model.update_model_data()
