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
from lxml import etree
from basic_func_module.base_logger import logger
from basic_func_module.file_validation.file_validator import FileValidator


class ArxmlFileValidator(FileValidator):

    def __init__(self) -> None:
        super().__init__()

    def set_arxml_schema(self, schema_path):
        if not os.path.exists(schema_path):
            logger.error(f"Cannot find schema file: {schema_path}")
            raise FileNotFoundError(f"Cannot find schema file: {schema_path}")
        self.arxml_schema = etree.XMLSchema(file=schema_path)
        self.__schema_name = os.path.basename(schema_path)

    def validate(self, file_path):
        if not os.path.exists(file_path):
            logger.error(f"Target file not exit {file_path}")
            raise FileNotFoundError(f"No such file or directory: '{file_path}'")
        try:
            parsed_arxml = etree.parse(file_path)
            root = parsed_arxml.getroot()
            schemaLocation = root.attrib.get(r"{http://www.w3.org/2001/XMLSchema-instance}schemaLocation", "").split(
                " "
            )[-1]
            if schemaLocation != self.__schema_name:
                logger.warning(f"{file_path}:schema {schemaLocation} version mismatch {self.__schema_name}")
        except Exception:
            logger.warning("parsed arxml failed!")
            raise
        self.arxml_schema._clear_error_log()
        result = self.arxml_schema.validate(parsed_arxml)
        if not result:
            for log in self.arxml_schema.error_log:
                self._append_log(file_path, log.level_name, log.line, log.message)
        return result
