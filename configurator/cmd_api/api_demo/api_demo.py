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

CUR_FILE_PATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(CUR_FILE_PATH, "..", ".."))
sys.path.append(os.path.abspath(os.path.join(CUR_FILE_PATH, "..", "..", "third_party")))

from cmd_api.auto_cli_api import AutoCliApi
from func_module.health_monitor.perf_record import log_function_stats, record_function_stats
from cmd_adaptor.cmd_interaction.cmd_logger import logger

PROJECT_PATH = os.path.abspath(os.path.join(CUR_FILE_PATH, "../../../../examples/tc397_demo/cfg_prj"))
PROJECT_FILE_PATH = os.path.join(PROJECT_PATH, "tc397_demo.vcosproject")

LOG_APTH = os.path.join(CUR_FILE_PATH)


@log_function_stats(["Studio性能统计", "一键集成耗时"])
def execute_auto_cli_api_demo_command():
    logger.init_default_handler(log_path=LOG_APTH)
    logger.info(f"load {PROJECT_FILE_PATH}")
    start_time = time.time()
    result = AutoCliApi.load_project(PROJECT_FILE_PATH)
    end_time = time.time()
    if result is False:
        logger.info("load project failed")
    else:
        runtime = end_time - start_time
        logger.info(f"load project succeeded: {runtime:.2f} seconds.")
    asw_path = os.path.join(PROJECT_PATH, "config", "asw")
    start_time = time.time()
    result = AutoCliApi.import_asw(asw_path)
    end_time = time.time()
    if result is False:
        logger.info("excute import asw failed")
    else:
        runtime = end_time - start_time
        logger.info(f"excute import asw succeeded: {runtime:.2f} seconds.")

    start_time = time.time()
    result = AutoCliApi.excute_validation(["Os", "Rte"], "warnning")
    end_time = time.time()
    runtime = end_time - start_time
    logger.info(f"excute validation: {runtime}")

    start_time = time.time()
    result = AutoCliApi.excute_generation(["Os", "Rte"], False, True)
    end_time = time.time()
    runtime = end_time - start_time
    logger.info(f"excute generation c code succeeded: {runtime:.2f} seconds.")

    start_time = time.time()
    result = AutoCliApi.save_project()
    end_time = time.time()
    if result is False:
        logger.info("save project failed")
    else:
        runtime = end_time - start_time
        logger.info(f"excute save project succeeded: {runtime:.2f} seconds.")


if __name__ == "__main__":
    execute_auto_cli_api_demo_command()
    record_function_stats()
