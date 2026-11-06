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
appl模板内过滤器定义模块.

定义jinja2模板中所使用的过滤器函数.

用法示例:
{{"#define {}_{}"|format_align("PI", "VALUE", length=10)}} 3.14

输出: "PI_VALUE  3.14"
"""

from jinja2 import pass_context


class Filter:
    """
    Class containing all filters. Add new static functions here
    to be included in the jinja2 context
    """

    @staticmethod
    @pass_context
    def define_once_include(context, content, filename):
        """
        Gen header file protection code
        """
        _ = context
        return "#ifndef {name}\n#define {name}{content}#endif /* {name} */".format(
            name=filename.replace(".", "_").upper(), content=content
        )

    @staticmethod
    @pass_context
    def define_extern_c_include(context, content):
        """
        Gen extern "C" code
        """
        _ = context
        return f'#ifdef __cplusplus\n\
            extern "C"\n\
            {{\n\
            #endif /* __cplusplus */\n\
            {content}\
            #ifdef __cplusplus\n\
            }} /* extern "C" */\n\
            #endif /* __cplusplus */'

    @staticmethod
    def format_align(content, *args, length=0):
        return f"{f'{content.format(*args)}':<{length}}"
