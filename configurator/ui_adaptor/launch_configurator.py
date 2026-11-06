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
import sys
import time
import datetime
import traceback
from PySide6 import QtCore, QtGui, QtWidgets
from ui_adaptor.ui_adaptor import UIAdaptor
from ui_adaptor.ui_interaction.ui_logger import logger
from ui_adaptor.data_management import data_management

CUR_FILE_PATH = os.path.dirname(os.path.realpath(__file__))
messages = ["Loading now", "Please wait", "Almost there", "Finishing up"]
configurator_stdout_file = "configurator_stdout.log"


class LaunchConfigurator:

    def __init__(self, status_queue=None):
        self.status_queue = status_queue
        self.configurator_status = {"info": ""}
        pass

    def get_index_data(self, module_stack, index):
        data_dict = {"ecuc_path": "", "mod_path": "", "value": None}
        index_command = module_stack.command(index)
        if index_command is None:
            return None
        data_dict["mod_path"] = index_command.show_data_dict["mod_path"]
        data_dict["ecuc_path"] = index_command.show_data_dict["ecuc_path"]
        data_dict["value"] = index_command.show_data_dict["cfg_value"]
        return data_dict

    def get_qundocommand_data(self):
        undo_stack_info = {}
        if (
            data_management
            and hasattr(data_management, "all_module_stack_dict")
            and data_management.all_module_stack_dict
        ):
            for key, value in data_management.all_module_stack_dict.items():

                module_index = data_management.all_module_stack_dict[key].index()
                if module_index > 0 and key not in undo_stack_info:
                    undo_stack_info.update({key: []})

                if module_index <= 2:
                    for index in range(module_index - 1, -1, -1):
                        reulst = self.get_index_data(data_management.all_module_stack_dict[key], index)
                        undo_stack_info[key].append(reulst)
                else:
                    for index in range(module_index - 1, module_index - 3, -1):
                        reulst = self.get_index_data(data_management.all_module_stack_dict[key], index)
                        undo_stack_info[key].append(reulst)

        return undo_stack_info

    def send_coredump_to_daemon(self, traceback_string):
        undo_stack_info = self.get_qundocommand_data()
        exception_info = {"time": "", "data": ""}
        current_datetime = datetime.datetime.now()
        formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
        exception_info.update({"time": formatted_datetime})
        exception_info.update({"data": traceback_string})
        exception_info.update({"stack_info": undo_stack_info})
        self.configurator_status.update({"status": "coredump"})
        self.configurator_status["info"] = exception_info
        logger.error(traceback_string)
        if self.status_queue:
            self.status_queue.put(self.configurator_status)
        QtWidgets.QMessageBox.critical(None, "An exception was raised", "{}".format(traceback_string))

    def handleException(self, exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            return sys.__excepthook__(exc_type, exc_value, exc_traceback)
        traceback_string = str("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        self.send_coredump_to_daemon(traceback_string)

    def launch_configurator(self, launch_debug, project_path, status_queue=None, message=None):
        fopen = open(configurator_stdout_file, "w")
        sys.stdout = fopen
        sys.stdin = fopen
        sys.stderr = fopen
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        # 启动Application
        app = QtWidgets.QApplication([])
        app.setFont(QtGui.QFont("Microsoft YaHei", 9))
        app.setStyle(QtWidgets.QStyleFactory.create("windowsvista"))
        # 展示加载进度
        splash = MySplashScreen()
        # 显示启动界面
        splash.show()
        # 处理主进程事件
        QtCore.QCoreApplication.processEvents()
        splash.load_data()
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("6666")
        try:
            UIAdaptor(
                app,
                is_debug=launch_debug,
                project_path=project_path,
                status_queue=status_queue,
                save_timer_flag=False,
                message=message,
            )
            sys.excepthook = self.handleException
        except Exception:
            error_info = f"{traceback.format_exc()}"
            self.send_coredump_to_daemon(f"Exception: {error_info}")
        sys.exit(app.exec())


class MySplashScreen(QtWidgets.QSplashScreen):
    """展示工程加载进度"""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QtGui.QIcon(":/Home.svg"))
        self.setWindowTitle("Vcos Studio Loading")
        self.setStyleSheet("font-size: 10pt; font-weight: bold")
        self.resize(300, 60)

    def closeEvent(self, event):
        """close event"""
        super().closeEvent(event)

    def load_data(self):
        """展示加载百分比"""
        max_length = 20
        for load in range(1, 100):
            start_time = time.perf_counter()
            while (time.perf_counter() - start_time) < (10 / 1000):
                pass
            message_index = int(load / 25)
            message = messages[message_index]
            message = message.ljust(max_length, ".")
            self.showMessage(f"{message}  {load}%", QtCore.Qt.AlignCenter | QtCore.Qt.AlignCenter, QtCore.Qt.black)
            # 允许主进程处理事件
            QtCore.QCoreApplication.processEvents()
        self.close()
