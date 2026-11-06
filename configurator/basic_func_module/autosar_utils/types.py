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
from autosar44 import autosar44

PARAMETERS_CLASS = {
    "ECUC-ADD-INFO-PARAM-VALUE": autosar44.ECUC_ADD_INFO_PARAM_VALUE,
    "ECUC-NUMERICAL-PARAM-VALUE": autosar44.ECUC_NUMERICAL_PARAM_VALUE,
    "ECUC-TEXTUAL-PARAM-VALUE": autosar44.ECUC_TEXTUAL_PARAM_VALUE,
}

PARAMETERS_TYPE = {
    "ECUC-ADD-INFO-PARAM-DEF": "ECUC-ADD-INFO-PARAM-VALUE",
    "ECUC-BOOLEAN-PARAM-DEF": "ECUC-NUMERICAL-PARAM-VALUE",
    "ECUC-ENUMERATION-PARAM-DEF": "ECUC-TEXTUAL-PARAM-VALUE",
    "ECUC-FLOAT-PARAM-DEF": "ECUC-NUMERICAL-PARAM-VALUE",
    "ECUC-FUNCTION-NAME-DEF": "ECUC-TEXTUAL-PARAM-VALUE",
    "ECUC-INTEGER-PARAM-DEF": "ECUC-NUMERICAL-PARAM-VALUE",
    "ECUC-LINKER-SYMBOL-DEF": "ECUC-TEXTUAL-PARAM-VALUE",
    "ECUC-MULTILINE-STRING-PARAM-DEF": "ECUC-TEXTUAL-PARAM-VALUE",
    "ECUC-STRING-PARAM-DEF": "ECUC-TEXTUAL-PARAM-VALUE",
}


REFERENCES_CLASS = {
    "ECUC-REFERENCE-VALUE": autosar44.ECUC_REFERENCE_VALUE,
    "ECUC-INSTANCE-REFERENCE-VALUE": autosar44.ECUC_INSTANCE_REFERENCE_VALUE,
}

REFERENCES_TYPE = {
    "ECUC-CHOICE-REFERENCE-DEF": "ECUC-REFERENCE-VALUE",
    "ECUC-FOREIGN-REFERENCE-DEF": "ECUC-REFERENCE-VALUE",
    "ECUC-INSTANCE-REFERENCE-DEF": "ECUC-INSTANCE-REFERENCE-VALUE",
    "ECUC-REFERENCE-DEF": "ECUC-REFERENCE-VALUE",
    "ECUC-SYMBOLIC-NAME-REFERENCE-DEF": "ECUC-REFERENCE-VALUE",
}
