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
import re
import os
from abc import ABCMeta, abstractmethod


class ImportExcelBase(metaclass=ABCMeta):

    @abstractmethod
    def parse_excel_file(self, file_path) -> dict:
        pass

    @abstractmethod
    def excel_validate(self, dict: dict) -> bool:
        pass

    @abstractmethod
    def execute_import_excel_command(self) -> bool:
        pass

    def is_contain_chinese(self, path: str) -> bool:
        if re.search("[\u4e00-\u9fa5]", path) is not None:
            return True
        else:
            return False

    def get_execute_export_excel_path(self, config_path, excel_name_list=None):
        if config_path == "":
            return False
        excel_path_list = set()
        for excel_name in excel_name_list or []:
            excel_name_path = os.path.join(config_path, excel_name)
            if os.path.exists(excel_name_path):
                excel_name_path = os.path.join(config_path, f"{excel_name}.bak")
            excel_path_list.add(excel_name_path)

        return excel_path_list

    # 获取sheet表单里row行的数据
    def get_row_value(self, sheet, row) -> list:
        row_list = []
        for column in range(1, sheet.max_column + 1):
            value = sheet.cell(row, column).value
            row_list.append(value)
        return row_list

    # 获取sheet表单里column列的数据
    def get_column_value(self, sheet, column):
        column_list = []
        for row in range(1, sheet.max_row + 1):
            value = sheet.cell(row, column).value
            column_list.append(value)
        return column_list

    # 获取单元格里的数据
    def get_cell_value(self, sheet, raw, column):
        value = sheet.cell(raw, column).value
        return value
