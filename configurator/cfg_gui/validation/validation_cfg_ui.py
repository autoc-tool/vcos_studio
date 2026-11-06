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
from cfg_gui.common.generate_and_validation_base_ui import GenerateAndValidationBaseUI


class ValidationCFGUI(GenerateAndValidationBaseUI):

    def __init__(self, main_windows, module_list: dict = None, enabled_module_list=None, call_back=None) -> None:
        super().__init__(module_list=module_list, name="Validation", slot_call_back=call_back)
        self.main_windows = main_windows
        self.validation_enabled_list = []
        self.callback = call_back
        self.generation_or_validation_enabled_list = enabled_module_list
        self.button_add()

    def set_callback(self, callback):
        self.callback = callback

    def close_cancel_button_slot(self):
        self.close()

    def change_project_settings_button_slot(self):
        self.add_enabled_module_list_to_treeview()
        self.validation_enabled_list = self.set_validation_status_to_project_file()

    def validation_generate_button_slot(self):
        self.close()
        self.change_project_settings_button_slot()

        cbk_param = {"is_rte_parse_new_dict": self.main_windows.is_rte_parse_new_dict()}
        cbk_param.update({"module_list": self.validation_enabled_list})
        self.callback("validate_modules", cbk_param, result_callback=self.ui_validate_cbk)

    def ui_validate_cbk(self, result):
        self.main_windows.validation_ui.validation_model.update_model_data()
        self.main_windows.rte_edit_ui.task_mapping_ui.update_model()
        self.main_windows.over_view_ui.update_bsw_modules_view_switch(["Os", "Rte"])
