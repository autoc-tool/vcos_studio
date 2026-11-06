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
from func_module.health_monitor.logger import logger
from basic_func_module.base_common.load_plug_in import LoadPlugIn

class ExcelImporter:
    def __init__(self) -> None:
        pass

    def parse_excel(self, excel_list):

        res_dict = {}
        for file in excel_list:
            name, _ = os.path.splitext(os.path.basename(file))
            if not name.endswith("Cfg"):
                logger.ui_error(f"Invalid name of {name}. Must be *Cfg.xlsx. Skip this file")
                continue
            module_name: str = name[:-3]
            pkg_path = f"config_plug_in.excel_parser.{module_name.lower()}_excel_parser"
            module_obj = LoadPlugIn.load_module(module_name, pkg_path)
            parser_cls = getattr(module_obj, f"{module_name}ExcelParser")
            parse_res = parser_cls().execute_import_excel_command(excel_list)

            if parse_res:
                res_dict.update(parse_res)

        return res_dict
