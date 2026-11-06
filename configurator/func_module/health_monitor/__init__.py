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
from func_module.health_monitor import logger as func_module_logger
from func_module.health_monitor.logger import PerfLogger

__all__ = ["PerfLogger"]

# log level, Option: TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL
perf_logger = PerfLogger()

func_module_logger.perf_logger._core = perf_logger._core
func_module_logger.perf_logger._options = perf_logger._options
func_module_logger.base_logger.perf_logger._core = perf_logger._core
func_module_logger.base_logger.perf_logger._options = perf_logger._options
