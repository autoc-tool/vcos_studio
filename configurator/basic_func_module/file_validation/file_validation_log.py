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
class FileValidationLog:

    def __init__(self, file_name: str, level: str, line: str, message: str) -> None:
        self.__file_name: str = file_name
        self.__level = level
        self.__line = line
        self.__message = message

    @property
    def file_name(self):
        return self.__file_name

    @property
    def level(self):
        return self.__level

    @property
    def line(self):
        return self.__line

    @property
    def message(self):
        return self.__message
