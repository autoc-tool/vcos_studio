
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
import re
from lark import Lark
from basic_func_module.base_logger import logger
from basic_func_module.file_handler.sidl.transformer import SidlTransformer, DEFAULT_SYNTAX_VERSION


def parse_sidl_file(file_path: str):
    version_pattern = r"syntax:\s*\"(?P<syntax_version>\w+)\";"
    with open(file_path, "r", encoding="utf-8") as f:
        sidl_file = f.read()

        # Check the syntax version
        match = re.search(version_pattern, sidl_file)
        # If match no "syntax" field in sidl, use default syntax version
        syntax_version = DEFAULT_SYNTAX_VERSION
        if match:
            syntax_version = match.groupdict()["syntax_version"]
        else:
            logger.debug("Select default syntax version")
        logger.debug(f"Use sidl syntax version: {syntax_version}")

        # Load grammer file and create parser
        grammer_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'grammars', f"{syntax_version}.lark"))
        grammar = ""
        try:
            with open(grammer_path, "r") as gf:
                grammar = gf.read()
        except FileNotFoundError as e:
            logger.exception(f"Unsupported sidl version {syntax_version}")
            raise e
        parser = Lark(grammar, parser='lalr')

        tree = parser.parse(sidl_file)
        res = SidlTransformer().transform(tree)
        return res
