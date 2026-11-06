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

CUR_FILE_PATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(CUR_FILE_PATH, "..", "..", ".."))
sys.path.append(os.path.join(CUR_FILE_PATH, "..", "..", "..", "cmd_adaptor"))
sys.path.append(os.path.abspath(os.path.join(CUR_FILE_PATH, "..", "..", "..", "third_party")))

from cmd_adaptor.func_logic_layer.mapping_func.task_mapping_cmd_func import TaskMappingCmdFunc
from cmd_adaptor.func_logic_layer.load_save_project import LoadAndSaveProject

PROJECT_FILE_PATH = os.path.abspath(os.path.join(CUR_FILE_PATH, "projects/demo/demo.vcosproject"))
EXCEL_FILE = os.path.abspath(os.path.join(CUR_FILE_PATH, "projects/demo/Config/import/taskmapping_cfg.xlsx"))

if __name__ == "__main__":
    LoadAndSaveProject.load_project(PROJECT_FILE_PATH)
    TaskMappingCmdFunc.auto_task_mapping_by_file(EXCEL_FILE)
    LoadAndSaveProject.task_mapping_save_project()
