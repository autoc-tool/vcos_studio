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
"""
mcal模块动态代码生成模块.

"""
import os
import glob
import platform
from func_module.health_monitor.logger import logger
import subprocess

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PLATFORM = platform.system()


def generate(parser_module, mcal_module_codegen_cmd_line_dict: dict):
    """
    Generate MCAL module code and log the stdout to a log file.
    The log file will be located at the path specified after '-o' in cmd_args.
    """
    output_path = mcal_module_codegen_cmd_line_dict[parser_module]["paths"]["MCAL_GENDATA_PATH"]
    cmd_args = mcal_module_codegen_cmd_line_dict[parser_module]["cmd_args"]
    if cmd_args[0].endswith(".exe") and PLATFORM == "Linux":
        logger.warning("Linux do not support mcal code generate")
        return True
    cmd_line = " ".join(cmd_args)

    # 删除该mcal模块原来的动态代码文件
    delete_original_file(output_path, parser_module)

    # 确定 log 文件的完整路径
    log_file_path = os.path.join(output_path, f"{parser_module}.log")

    # 创建 log 文件目录，如果不存在的话
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    # 执行命令行并将 stdout 重定向到 log 文件
    with open(log_file_path, "w") as log_file:
        # 使用 subprocess.run 执行命令行，并将 stdout 和 stderr 都重定向到 log 文件
        result = subprocess.run(cmd_line, shell=True, stdout=log_file, stderr=log_file)

    # 读取日志文件的内容来记录或打印
    with open(log_file_path, "r") as log_file:
        log_contents = log_file.read()

    # 根据命令执行结果记录信息
    if result.returncode == 0:
        logger.info(log_contents)
    else:
        logger.error(log_contents)

    # 返回命令执行是否成功的布尔值
    return result.returncode == 0


def delete_original_file(output_path, parser_module):
    # 使用glob找出所有parser_module开头的文件
    pattern = f"{parser_module}_*"
    match_files = glob.glob(os.path.join(output_path, "**", pattern), recursive=True)

    # 循环删除这些文件
    for file_path in match_files:
        try:
            os.remove(file_path)
        except OSError as e:
            logger.info(f"Error: {file_path} : {e.strerror}")
    pass
