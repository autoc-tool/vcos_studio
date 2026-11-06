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
from func_module.health_monitor.logger import logger
from basic_func_module.base_common.load_plug_in import LoadPlugIn


class SetMethod:
    """联动行为的数据推理函数"""

    @classmethod
    def get_method(cls, module_name, method_name):
        common_set_method = getattr(CommonSetMethod, method_name, None)

        module_behavior = LoadPlugIn.load_module(module_name, "config_plug_in.linkage.linkage_behavior")

        # 模块的linkage_behavior.py不存在,在class CommonSetMethod中获取函数
        if module_behavior is None and common_set_method is None:
            logger.ui_error(f"'{method_name}' does not exist in Class CommonSetMethod.")
            return None
        if module_behavior is None:
            return common_set_method

        # 模块的linkage_behavior.py存在
        module_method_class = getattr(module_behavior, f"{module_name}SetMethod", None)
        if module_method_class is None:
            logger.ui_error(f"Class {module_name}SetMethod does not exist in {module_name}.linkage.linkage_behavior.")
            return None
        # 优先取模块特有的函数
        if getattr(module_method_class, method_name, None) is not None:
            return getattr(module_method_class, method_name, None)
        elif common_set_method is not None:
            return common_set_method
        else:
            logger.ui_error(f"{method_name} does not exist in Class CommonSetMethod or Class {module_name}SetMethod.")
            return None


class CommonSetMethod:
    """公共的数据推理函数"""

    @classmethod
    def equal(cls, data, input_show_data_dict, data_management, bsw_editor_ui_func=None, method_parameter=None):
        """与入口配置项数据相同"""
        return data, None

    @classmethod
    def unchanged(cls, data, input_show_data_dict, data_management, bsw_editor_ui_func=None, method_parameter=None):
        """被联动配置项数据不变"""
        return input_show_data_dict["cfg_value"], None

    @classmethod
    def set_old_data(cls, data, input_show_data_dict, data_management, bsw_editor_ui_func=None, method_parameter=None):
        """被联动配置项设置之前的旧值"""
        if hasattr(data_management, "old_data_dict") is False:
            return input_show_data_dict["cfg_value"], None
        if (input_show_data_dict["ecuc_path"] + input_show_data_dict["mod_path"]) in data_management.old_data_dict:
            return (
                data_management.old_data_dict[input_show_data_dict["ecuc_path"] + input_show_data_dict["mod_path"]],
                None,
            )
        return input_show_data_dict["cfg_value"], None

    @classmethod
    def clear_line(cls, data, input_show_data_dict, data_management, bsw_editor_ui_func=None, method_parameter=None):
        """清空被联动输入行数据"""
        return "", None

    @classmethod
    def str_zero(cls, data, input_show_data_dict, data_management, bsw_editor_ui_func=None, method_parameter=None):
        """返回字符0"""
        return "0", None

    @classmethod
    def str_one(cls, data, input_show_data_dict, data_management, bsw_editor_ui_func=None, method_parameter=None):
        """返回字符1"""
        return "1", None

    @classmethod
    def str_1024(cls, data, input_show_data_dict, data_management, bsw_editor_ui_func=None, method_parameter=None):
        """返回字符1024"""
        return "1024", None

    @classmethod
    def str_true(cls, data, input_show_data_dict, data_management, bsw_editor_ui_func=None, method_parameter=None):
        """返回字符true"""
        return "true", None

    @classmethod
    def str_false(cls, data, input_show_data_dict, data_management, bsw_editor_ui_func=None, method_parameter=None):
        """返回字符false"""
        return "false", None
