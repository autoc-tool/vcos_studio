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
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget, QProgressBar, QVBoxLayout
from threading import RLock


class ProgressDialog(QWidget):

    _instance = None
    _initialized = False
    lock = RLock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self.setWindowIcon(QIcon(":/Home.svg"))
        self.setWindowIconText("处理中...")
        self.setWindowTitle("处理中...")
        self.setMinimumSize(450, 60)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowMinimizeButtonHint)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #ccc;
                height: 10px;
                padding: 0px;
                text-align: center;
                background-color: #f2f2f2;
            }
        """
        )
        self.label = QLabel()
        self.label.setWordWrap(True)
        hbox = QHBoxLayout()
        hbox.addWidget(self.label)
        vbox = QVBoxLayout()
        vbox.addWidget(self.progress_bar)
        vbox.addLayout(hbox)
        self.setLayout(vbox)

    def setLabelText(self, text: str):
        self.label.setText(text)

    def show(self):
        self.lock.acquire()
        return super().show()

    @Slot()
    def hide(self):
        self.lock.release()
        self.label.clear()
        return super().hide()
