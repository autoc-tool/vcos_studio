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
from PySide6 import QtWidgets
from PySide6.QtWidgets import QFileDialog
import os

CUR_FILE_PATH = os.path.dirname(__file__)


class ImportASWARXMLUI(QtWidgets.QWidget):

    def __init__(self):
        super(ImportASWARXMLUI, self).__init__()

    def open_the_input_files_assistant_asw(self):

        vcos_dir_path = os.path.abspath(os.path.join(CUR_FILE_PATH, "..", "..", ".."))
        absolute_file_path_asw_arxml_folder = QFileDialog.getExistingDirectory(self, "Import ASW ARXML", vcos_dir_path)

        return absolute_file_path_asw_arxml_folder
