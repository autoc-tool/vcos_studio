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
from ui_adaptor.data_management import data_management
from func_module.export_file.export_file import ExportFile

CUR_FILE_PATH = os.path.dirname(os.path.realpath(__file__))


class ExportFileFunc:

    def __init__(self):

        pass

    def export_mapping_info_to_excel(self, info_table, mapping_type, file_path):

        ExportFile.mapping_info_export_to_excel(info_table, mapping_type, file_path, data_management)
