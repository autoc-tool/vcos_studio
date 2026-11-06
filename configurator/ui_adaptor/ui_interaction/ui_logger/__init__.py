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
import sys
import ansi2html
from queue import Queue
from os.path import basename, splitext
from loguru._recattrs import RecordFile
from func_module.health_monitor import logger as func_module_logger
from func_module.health_monitor.logger import Logger, DEFAULT_FORMAT
from PySide6 import QtCore, QtGui, QtWidgets

__all__ = ["logger", "UILogger"]

# log level, Option: TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL
LOGGER_LEVEL = "INFO"


class UpdatedSignals(QtCore.QObject):

    signal = QtCore.Signal()


class UILogger(Logger):
    """UI Logger"""

    def __init__(self):
        super().__init__()
        self.ui_object = None
        self.auto_fresh_falg = False
        self.html_messages = Queue()
        self.updated_signal = UpdatedSignals()
        self.conv = ansi2html.Ansi2HTMLConverter()

    def init_default_handler(self, log_path=""):
        super().init_default_handler(sink=None, log_path=log_path)  # type: ignore
        self.updated_signal.signal.connect(self.update_ui)
        self.ui_handler_id = self.add_handler(
            sink=self.handler, level=LOGGER_LEVEL, format=DEFAULT_FORMAT, colorize=True, filter=self.ui_log_filter
        )

    def registe_ui_obj(self, ui_obj):
        self.ui_object = ui_obj

    def handler(self, ansi_message: str):
        if self.ui_object is None:
            return
        ansi_message = ansi_message.rstrip()
        html_message = self.conv.convert(ansi_message)
        self.html_messages.put(html_message)
        self.updated_signal.signal.emit()

    def update_ui(self):
        if self.ui_object is None:
            return
        if not getattr(self.ui_object, "textBrowser", None):
            return
        text_browser: QtWidgets.QTextBrowser = self.ui_object.textBrowser  # type: ignore
        text_browser.setUpdatesEnabled(False)
        while not self.html_messages.empty():
            html_message = self.html_messages.get()
            text_browser.append(html_message)
        text_browser.setUpdatesEnabled(True)
        if self.auto_fresh_falg:
            text_browser.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def set_auto_fresh(self):
        self.auto_fresh_falg = True

    def cancle_auto_fresh(self):
        self.auto_fresh_falg = False

    def log_clear(self):
        if self.ui_object:
            text_browser: QtWidgets.QTextBrowser = self.ui_object.textBrowser
            if text_browser:
                text_browser.clear()

    def ui_log_filter(self, record):
        if record["extra"].get("ui_log"):
            self.update_record(record)
            return True
        else:
            return False


logger = UILogger()
func_module_logger.logger._core = logger._core
func_module_logger.logger._options = logger._options
func_module_logger.logger.ui_object = logger.ui_object
func_module_logger.base_logger.logger._core = logger._core
func_module_logger.base_logger.logger._options = logger._options
func_module_logger.base_logger.logger.ui_object = logger.ui_object
