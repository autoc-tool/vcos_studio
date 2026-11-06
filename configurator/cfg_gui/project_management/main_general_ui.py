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
import os
from PySide6.QtWidgets import QDialog
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QMessageBox
from cfg_gui.resources.ui.ui_general import Ui_Form

CUR_FILE_PATH = os.path.dirname(__file__)


class ConfigratorGeneral(QDialog, Ui_Form):

    def __init__(self, slot_call_back, save_cycle, periodic_save_setting, call_back, parent=None):
        super().__init__()
        self.slot_call_back = slot_call_back
        self.call_back = call_back
        self.save_cycle = save_cycle
        self.periodic_save_setting = periodic_save_setting
        self.init()
        self.configure_general_uic.pushButtonOk.clicked.connect(self.general_ok_slot)
        self.configure_general_uic.checkBox.stateChanged.connect(self.checkbox_state_changed)

    def init(self):
        self.setupUi(self)
        self.configure_general_uic: QDialog = self
        self.configure_general_uic.lineEditPeriodicSave.setValidator(QIntValidator(60, 9999, self))
        self.configure_general_uic.lineEditPeriodicSave.setText(f"{self.save_cycle}")
        self.configure_general_uic.checkBox.setChecked(self.periodic_save_setting)
        self.checkbox_state_changed()

    def general_ok_slot(self):
        self.save_cycle = self.configure_general_uic.lineEditPeriodicSave.text()
        self.periodic_save_setting = True if self.configure_general_uic.checkBox.isChecked() else False
        self.set_periodic_save_time(self.save_cycle, self.periodic_save_setting)

    def checkbox_state_changed(self):
        if self.configure_general_uic.checkBox.isChecked() is True:
            self.configure_general_uic.lineEditPeriodicSave.setEnabled(True)
        else:
            self.configure_general_uic.lineEditPeriodicSave.setEnabled(False)

    def set_periodic_save_time(self, save_cycle, periodic_save_setting):
        if int(save_cycle) < 60:
            QMessageBox.information(self, "Notice", "Periodic Save必须大于60s", QMessageBox.StandardButton.Ok)
            return
        self.slot_call_back(
            "set_periodic_save_time_action",
            {"save_cycle": int(save_cycle), "periodic_save_setting": periodic_save_setting},
        )
        self.call_back(save_cycle, periodic_save_setting)
        self.close()
