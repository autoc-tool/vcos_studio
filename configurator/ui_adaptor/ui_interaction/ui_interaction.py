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
from cfg_gui.main_window import MainWindow
from ui_adaptor.ui_interaction.ui_logger import logger
from func_module.health_monitor import perf_logger
import os

CUR_PATH = os.path.dirname(os.path.abspath(__file__))


class UiInteraction:

    def __init__(self, app, project_path, call_back, save_timer_flag=False, status_queue=None, message=None):
        studio_path = os.path.join(CUR_PATH, "..", "..")
        logger.init_default_handler(log_path=studio_path)
        perf_logger.init_perf_handler(studio_path, "ui_perf_record.log")

        self.main_windows = MainWindow(app, call_back, status_queue, save_timer_flag=save_timer_flag)
        self.main_windows.print_coredump_info(message)
        self.main_windows.auto_open_project(project_path)
        logger.registe_ui_obj(self.main_windows)
