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
from PySide6.QtWidgets import QMessageBox, QComboBox, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox
from cfg_gui.common.generate_and_validation_base_ui import GenerateAndValidationBaseUI
from ui_adaptor.ui_interaction.ui_logger import logger


class BSWGeneratorWidget(GenerateAndValidationBaseUI):
    """Support Generation UI"""

    def __init__(
        self,
        main_windows,
        module_list: dict = None,
        enabled_model_list: list = None,
        generation_limit: str = "Error",
        slot_call_back=None,
    ) -> None:
        super().__init__(module_list=module_list, name="Generate", slot_call_back=slot_call_back)
        self.slot_call_back = slot_call_back
        self.generation_or_validation_enabled_list = enabled_model_list
        self.generation_limit = generation_limit
        self.main_windows = main_windows

        self.Vitem = QVBoxLayout()

        self.Incremental_generation_checkbox_label = QLabel("Incremental generation")
        self.Incremental_generation_checkbox = QCheckBox(self)
        self.Incremental_generation_checkbox.setChecked(False)
        self.Incremental_generation_checkbox.setGeometry(0, 0, 151, 25)
        self.Hitem0 = QHBoxLayout()
        self.Hitem0.addWidget(self.Incremental_generation_checkbox_label)
        self.Hitem0.addStretch(2)
        self.Hitem0.addWidget(self.Incremental_generation_checkbox)

        self.simulator_checkbox_label = QLabel("Simulator Mode")
        self.simulator_checkbox = QCheckBox(self)
        self.simulator_checkbox.setChecked(False)
        self.simulator_checkbox.setGeometry(0, 0, 151, 25)
        self.Hitem_Sim = QHBoxLayout()
        self.Hitem_Sim.addWidget(self.simulator_checkbox_label)
        self.Hitem_Sim.addStretch(2)
        self.Hitem_Sim.addWidget(self.simulator_checkbox)

        self.mode_label = QLabel("Select Limit: ")
        self.checkbox = QComboBox(self)
        self.checkbox.setGeometry(0, 0, 151, 25)
        self.checkbox.addItems(["Error", "Warning"])
        self.checkbox.setCurrentText(self.generation_limit)
        self.Hitem1 = QHBoxLayout()
        self.Hitem1.addWidget(self.mode_label)
        self.Hitem1.addStretch(2)
        self.Hitem1.addWidget(self.checkbox)

        self.limit_label = QLabel("Select Mode:")
        self.mode_checkbox = QComboBox(self)
        self.mode_checkbox.setGeometry(0, 0, 151, 25)
        self.mode_checkbox.addItems(["release", "debug"])
        self.Hitem2 = QHBoxLayout()
        self.Hitem2.addWidget(self.limit_label)
        self.Hitem2.addStretch(2)
        self.Hitem2.addWidget(self.mode_checkbox)

        self.Vitem.addLayout(self.Hitem0)
        self.Vitem.addLayout(self.Hitem_Sim)
        self.Vitem.addLayout(self.Hitem1)
        self.Vitem.addLayout(self.Hitem2)

        self.combobox_add(item=self.Vitem)

    def closeEvent(self, event):
        self.close_cancel_button_slot()

    def close_cancel_button_slot(self):
        # 更新模式信息
        self.slot_call_back(
            "update_mode_info",
            {
                "mode_info": self.mode_checkbox.currentText(),
                "incremental_generation_info": self.Incremental_generation_checkbox.isChecked(),
                "generation_limit": self.checkbox.currentText(),
                "sim_mode": self.simulator_checkbox.isChecked(),
            },
        )
        self.close()

    def validation_generate_button_slot(self):
        """generate信号触发的槽函数"""
        self.codegen_module_list: dict = self.set_validation_status_to_project_file()
        generation_module_param: dict = {}
        generation_module_param.update({"module_list": self.codegen_module_list})
        """Generate前先预处理, 然后Validation, 最后根据validation结果决定generate是否真正生成代码"""
        self.slot_call_back("generate_modules", generation_module_param, result_callback=self.generate_code)
        self.close_cancel_button_slot()

    def ui_codegen_cbk(self, result):
        self.main_windows.validation_ui.validation_model.update_model_data()
        self.main_windows.rte_edit_ui.task_mapping_ui.update_model()
        self.slot_call_back("validation_save_logs")
        self.slot_call_back("validation_save_ignored_logs")
        if not result:
            logger.ui_error("generate c code failed")
            self.slot_call_back(
                "save_action",
                " ",
                self.main_windows.is_rte_parse_new_dict(),
                result_callback=lambda: self.main_windows.over_view_ui.update_bsw_modules_view_switch(["Os", "Rte"]),
            )
            return False
        else:
            self.slot_call_back(
                "codegen_save_action",
                " ",
                self.main_windows.is_rte_parse_new_dict(),
                result_callback=lambda: self.main_windows.over_view_ui.update_bsw_modules_view_switch(["Os", "Rte"]),
            )
            return True

    def generate_code(self, param):
        """基于校验汇总结果判定Generation"""
        checkitem: str = self.checkbox.currentText()
        count_log_dict, validation_result = param[0], param[1]
        error_count = count_log_dict["Error"]
        warning_count = count_log_dict["Warning"]

        Text: str = "Errors Exist!\n\tPlease Check Validation"
        self.msg_box = QMessageBox(QMessageBox.Icon.Warning, "Notice", Text)
        if checkitem == "Warning":
            if error_count > 0 or warning_count > 0:
                for module, result in validation_result.items():
                    if result is False:
                        logger.ui_warning(
                            f"Module {module} has validation errors, you can view them in Validation page."
                        )
                logger.ui_warning(f"Validation: {error_count} Errors and {warning_count} Warnings")
                self.close()
                self.msg_box.show()
                self.ui_codegen_cbk(False)
                return
        elif checkitem == "Error":
            if error_count > 0:
                for module, result in validation_result.items():
                    if result is False:
                        logger.ui_warning(
                            f"Module {module} has validation errors, you can view them in Validation page."
                        )
                logger.ui_warning(f"Validation: {error_count} Errors and {warning_count} Warnings")
                self.close()
                self.msg_box.show()
                self.ui_codegen_cbk(False)
                return
        self.slot_call_back(
            "generator_action",
            self.codegen_module_list,
            {"rte_parse_new_dict": True},
            result_callback=self.ui_codegen_cbk,
        )

    def check_kconfig_enable(self, modules_info):
        if (
            not modules_info.get("kfg_module_enabled_list", None)
            and not modules_info.get("kfg_module_all_list", None)
            or len(modules_info.get("kfg_module_enabled_list", None)) < 1
            or len(modules_info.get("kfg_module_all_list", None)) < 1
        ):
            QMessageBox.question(
                None,
                "kconfig error",
                "请先关闭Studio，执行kconfig命令，然后重新打开工程。",
                QMessageBox.Yes,
                QMessageBox.Yes,
            )
            return False
        else:
            return True
