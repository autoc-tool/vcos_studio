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
import inspect
from typing import Callable


def is_dbc_semantic_rule(object):
    return inspect.isfunction(object) and object.__name__.startswith("dbc_semantic_rule")


def dbc_semantic_rule_demo(db_dbc, error_log: Callable) -> bool:
    # Semantic check scentences here
    validation_pass = True
    ...
    # If cannot pass the semantic check, raise exception
    if not validation_pass:
        message = "Error message of the validation"
        error_log(message)

    return validation_pass


def dbc_semantic_rule_001(db_dbc, error_log: Callable) -> bool:
    validation_pass = True

    attr_def = db_dbc.dbc.attribute_definitions
    if badurate := attr_def.get("Baudrate", None):
        if default_val := getattr(badurate, "default_value", None):
            maximum = getattr(badurate, "maximum", default_val + 1)
            minimum = getattr(badurate, "minimum", default_val - 1)
            if default_val > maximum:
                validation_pass = False
                error_log("Invalid Baudrate! Bigger than maximum")
            if default_val < minimum:
                validation_pass = False
                error_log("Invalid Baudrate! Smaller than minimum")

    return validation_pass
