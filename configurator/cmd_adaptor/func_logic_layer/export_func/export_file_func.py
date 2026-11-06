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
from func_module.export_file.export_file import ExportFile
from func_module.export_file.export_file import TASK_MAPPING
from cmd_adaptor.func_logic_layer.mapping_func.task_mapping_cmd_func import TaskMappingCmdFunc
from cmd_adaptor.cmd_interaction.cmd_logger import logger
from cmd_adaptor.data_management import data_management


class ExportFileFunc:

    @classmethod
    def export_task_mapping_info_to_excel(cls, file_path):
        # 1）获取文件的目录路径
        directory = os.path.dirname(file_path)
        # 2）判断目录路径是否存在，如果不存在则创建目录
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info("The directory does not exist and has been created:" + directory)

        task_mapping_instance = TaskMappingCmdFunc.get_task_mapping_instance()
        ExportFile.mapping_info_export_to_excel(
            task_mapping_instance, TASK_MAPPING, file_path, data_management, is_start_file=False
        )
        return True
