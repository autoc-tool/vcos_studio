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
from cmd_adaptor.func_logic_layer.import_func.import_cdd_handler import ImportCddHandler
from cmd_adaptor.func_logic_layer.import_func.import_asw_handler import ImportAswHandler
from cmd_adaptor.func_logic_layer.import_func.import_dbc_and_ldf_handler import ImportDbcLdfHandler
from cmd_adaptor.func_logic_layer.import_func.import_mcal_handler import ImportMcalHandler


def execute_auto_import_asw(project_file_path, asw_dir_list):
    import_asw_handler = ImportAswHandler()
    import_asw_handler.load_project(project_file_path)

    return import_asw_handler


def execute_auto_import_cdd(project_file_path, cdd_path):
    import_cdd_handler = ImportCddHandler()

    return import_cdd_handler


def execute_auto_import_ldf_and_dbc(project_file_path, dbc_info):
    import_dbc_ldf_handler = ImportDbcLdfHandler()

    return import_dbc_ldf_handler


def execute_auto_import_mcal(project_file_path, mcal_path):

    import_mcal_handler = ImportMcalHandler()
    return import_mcal_handler
