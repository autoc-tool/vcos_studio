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
import time

from func_module.health_monitor import perf_logger as health_monitor_logger
from func_module.project_management.version_management.vcos_version import VCOS_VERSION

CUR_FILE_PATH = os.path.dirname(__file__)
STUDIO_PATH = os.path.join(CUR_FILE_PATH, "..", "..")
UI_LOG_NAME = "ui_perf_record.log"
CMD_LOG_NAME = "cmd_perf_record.log"
POSTURL1 = ""
POSTURL2 = ""
POST_TIMEOUT = 30


def check_version() -> bool:
    """检查版本号是否为正式版本"""
    if "-" not in VCOS_VERSION:
        return False
    suffix = VCOS_VERSION.split("-")[-1]
    return suffix == "RELEASE"


record_flag: bool = check_version()


# 定义字典用来存储每个函数的运行信息
function_stats = {}


# 定义装饰器函数，用来记录函数的运行时间和运行频率
def log_function_stats(function_module_list=[]):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            run_time = end_time - start_time
            run_time = float(f"{run_time:.6f}")
            # 更新函数运行信息
            if func.__name__ not in function_stats:
                function_module = ""
                for i in range(len(function_module_list)):
                    if function_module_list[i] == "":
                        break
                    function_module += f"{function_module_list[i]}"
                    if i < (len(function_module_list) - 1):
                        function_module += "|"
                function_stats[func.__name__] = {
                    "run_count": 1,
                    "last_run_time": run_time,
                    "total_run_time": run_time,
                    "avg_run_time": run_time,
                    "max_run_time": run_time,
                    "min_run_time": run_time,
                    "module": function_module,
                }
            else:
                function_info = function_stats[func.__name__]
                function_info["run_count"] += 1
                function_info["last_run_time"] = run_time
                function_info["total_run_time"] += run_time
                function_info["avg_run_time"] = function_info["total_run_time"] / function_info["run_count"]
                function_info["max_run_time"] = max(function_info["max_run_time"], run_time)
                function_info["min_run_time"] = min(function_info["min_run_time"], run_time)

            # 记录运行时间到日志文件
            function_info = function_stats[func.__name__]
            health_monitor_logger.info(
                f"Function:{func.__name__}, run_count:{function_info['run_count']}, \
last_run_time:{function_info['last_run_time']:.6f}, total_run_time:{function_info['total_run_time']:.6f}, \
avg_run_time:{function_info['avg_run_time']:.6f}, max_run_time:{function_info['max_run_time']:.6f}, \
min_run_time:{function_info['min_run_time']:.6f}, module: {function_info['module']}"
            )

            return result

        return wrapper

    return decorator


def record_validation_result(validation_logs: dict):
    failed_logs = {}
    from func_module.validation.validator import Validator

    for module_name, module_logs in validation_logs.items():
        Validator.get_module_validation_fail_logs(module_name, module_logs, failed_logs)
    for module_name, module_faled_logs in failed_logs.items():
        failed_info, error_cnt = {}, 0
        for validation_mark, info_dict in module_faled_logs.items():
            failed_count = len(info_dict.get("info", []))
            if failed_count:
                failed_info[validation_mark] = failed_count
                error_cnt += failed_count
        logger_str = f"module validation: {module_name}, error count: {error_cnt}, " + ", ".join(
            f"{mark}: {count}" for mark, count in failed_info.items()
        )
        health_monitor_logger.info(logger_str)


# 在程序退出前将函数运行信息写入日志文件
def record_function_stats():
    for func_name, stats in function_stats.items():
        run_count = stats["run_count"]
        total_run_time = stats["total_run_time"]
        avg_run_time = total_run_time / run_count
        max_run_time = stats["max_run_time"]
        min_run_time = stats["min_run_time"]
        health_monitor_logger.info(f"Function {func_name} was called {run_count} times.")
        health_monitor_logger.info(f"Function {func_name} average run time: {avg_run_time} seconds.")
        health_monitor_logger.info(f"Function {func_name} max run time: {max_run_time} seconds.")
        health_monitor_logger.info(f"Function {func_name} min run time: {min_run_time} seconds.")
