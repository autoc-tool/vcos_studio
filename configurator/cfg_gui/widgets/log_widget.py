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
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QTextBrowser, QMenu


class LogWidget(QTextBrowser):

    def __init__(self, main_window):
        super().__init__(main_window.tabLog)
        main_window.textBrowser = self
        main_window.tabLog.layout().addWidget(self)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_menu)

    def show_menu(self, pos):
        self.contextMenu = self.createStandardContextMenu() or QMenu(self)
        action = QAction("Clear", self.contextMenu)
        action.triggered.connect(self.clear)
        self.contextMenu.insertAction(self.contextMenu.actions()[0], action)
        self.contextMenu.exec(self.mapToGlobal(pos))
