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
from basic_func_module import base_logger
from basic_func_module.base_logger import BaseLogger, DEFAULT_FORMAT

__all__ = ["logger", "Logger"]

# log level, Option: TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL
LOGGER_LEVEL = "INFO"
LOGGER_PATH = ""


class Logger(BaseLogger):
    """Func Module Logger"""

    def init_default_handler(
        self,
        sink=sys.stderr,
        log_path=LOGGER_PATH,
    ):
        if sink:
            self.add_handler(sink, level=LOGGER_LEVEL, format=DEFAULT_FORMAT, colorize=True)
        log_file_path = os.path.join(log_path, "vcos_{time:YYYY_MM_DD}.log")
        self.add_handler(log_file_path, level="DEBUG", format=DEFAULT_FORMAT)


PERF_DEFAULT_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> " "[<level>{level}</level>] " "<level>{message}</level>"
)


class PerfLogger(BaseLogger):
    """Func Module Logger"""

    def init_perf_handler(self, perf_log_path, log_name):
        perf_log_path = os.path.join(perf_log_path, log_name)
        self.add_handler(perf_log_path, format=PERF_DEFAULT_FORMAT)


logger = Logger()
base_logger.logger._core = logger._core
base_logger.logger._options = logger._options

perf_logger = PerfLogger()
