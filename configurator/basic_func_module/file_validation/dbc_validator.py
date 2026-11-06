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
import inspect
import chardet
import cantools
from basic_func_module.file_validation import dbc_semantic_rules
from basic_func_module.file_validation.file_validator import FileValidator


class DbcValidator(FileValidator):

    def validate(self, file_path):

        def error_log(text: str):
            self._append_log(file_path, "ERROR", -1, text)

        if not os.path.exists(file_path):
            self._append_log(file_path, "ERROR", -1, "File not exist")
            return False

        res = True
        # Syntax validation
        try:
            encoding_message = ""
            with open(file_path, "rb") as f:
                encoding_message = chardet.detect(f.read())
            db_dbc = cantools.database.load_file(file_path, encoding=encoding_message["encoding"])
            # Empty file also cannot pass
            if not db_dbc:
                res = False
                self._append_log(file_path, "ERROR", -1, "Empty file")
        except Exception as e:
            res = False
            self._append_log(file_path, "ERROR", -1, str(e))
        else:
            # Semantic validation
            rules_dict = {
                member[0]: member[1]
                for member in inspect.getmembers(dbc_semantic_rules, dbc_semantic_rules.is_dbc_semantic_rule)
            }
            for func in rules_dict.values():
                res = res and func(db_dbc, error_log)

        return res


if __name__ == "__main__":
    DBC_FILE = ""
    va = DbcValidator()
    res = va.validate(DBC_FILE)
    ...
