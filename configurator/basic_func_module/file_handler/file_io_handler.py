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
import json
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.base_logger import logger

CUR_FILE_PATH = os.path.dirname(__file__)


class FileIOHandler:

    @classmethod
    def path_conversion(cls, file_path: str):
        new_file_path = file_path.replace("\\", "/")
        return new_file_path

    @classmethod
    def parse_arxml_file(cls, arxml_file_path: str):
        """load arxml file

        Args:
            arxml_file_path (dict, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """
        arxml_file_path = FileIOHandler.path_conversion(arxml_file_path)
        if not os.path.isfile(arxml_file_path):
            return None

        result = AutosarUtil.parse_arxml(arxml_file_path)

        return result

    @classmethod
    def save_arxml_file(cls, autosar_class, arxml_file_path: str) -> bool:
        """_summary_

        Args:
            autosar_class (_type_): _description_
            arxml_file_path (str): _description_

        Returns:
            _type_: _description_
        """
        result = True
        arxml_file_path = FileIOHandler.path_conversion(arxml_file_path)

        if autosar_class is None:
            logger.error(f"{autosar_class} is None, {arxml_file_path}")
            return False
        try:
            AutosarUtil.save_arxml(autosar_class, arxml_file_path)
        except Exception as e:
            logger.exception(f"save file {arxml_file_path} failed: {e}")
            result = False

        return result

    @classmethod
    def load_json_file(cls, json_file_path: str):
        json_file_path = FileIOHandler.path_conversion(json_file_path)
        if not os.path.isfile(json_file_path):
            return None
        with open(json_file_path) as f:
            data = json.load(f)
        f.close()

        return data

    @classmethod
    def save_json_file(cls, json_file_path: str, json_data) -> bool:
        json_file_path = FileIOHandler.path_conversion(json_file_path)
        if not os.path.isfile(json_file_path):
            return False

        if json_data is None:
            return False

        with open(json_file_path, "w") as f:
            json.dump(json_data, f)
        f.close()

        return True
