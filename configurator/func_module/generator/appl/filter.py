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
"""
appl对象解析模块,用于兼容模式

解析输入的josn object, 然后生成模板需要的参数对象.
"""


def get_template_input_parameter_dict(config_dict: dict) -> dict:
    """
    Get input parameter for template generated code.

    Arg:
      config_dict : All config dictionary

    Return:
      Returns a dictionary of template input parameter
    """

    input_dict = {}

    return input_dict


def get_template_input_parameter_dict_from_parsed_data(config_dict: dict) -> dict:
    """
    Get input parameter for template generated code for VCOS Design(Excel).

    Arg:
        config_dict : All config dictionary

    Return:
        Returns a dictionary of template input parameter
    """

    # Get the signal with the timeout set
    timeout_signals_dict = (config_dict.get("data_mapping_config") or {}).get("timeout_signals_dict", {})

    input_dict = {
      "timeout_signals_dict": timeout_signals_dict,
    }
    return input_dict
