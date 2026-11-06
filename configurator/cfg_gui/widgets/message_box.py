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
from PySide6.QtWidgets import QMessageBox


class ArgQMessageBox:

    def __init__(self, mainwindow=None, defaultValue=None, IsEnabled=None):
        msg = QMessageBox(mainwindow)
        msg.setInformativeText("This is additional information")
        msg.setWindowTitle("new/open vcos project")
        msg.setDetailedText("The details are as follows:")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg.buttonClicked.connect(self.msgbtn)
        msg.show()

    def msgbtn(i):
        print("Button pressed is:", i.text())
