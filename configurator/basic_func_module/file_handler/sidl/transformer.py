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
from typing import List, Union, Tuple, Dict
from lark import Transformer, Token, UnexpectedInput, v_args

DEFAULT_SYNTAX_VERSION = "sidl1"


class SidlTransformer(Transformer):

    def start(self, tree):
        sidl: Dict[str, Union[str, List]] = {
            "syntax": DEFAULT_SYNTAX_VERSION,
            "enum": [],
            "struct": [],
            "typedef": [],
            "service": [],
        }
        for key, value in tree:
            if key == "syntax":
                sidl[key] = value
            else:
                sidl[key].append(value)

        return sidl

    @v_args(inline=True)
    def identifier(self, token: Token):
        return ("name", token.value)

    def syntax_version(self, tree: List[Token]):
        if len(tree) > 0:
            return ("syntax", tree[0].value)
        else:
            return ("syntax", DEFAULT_SYNTAX_VERSION)

    def enum_def(self, tree):
        info_dict = dict(tree)
        return ("enum", info_dict)

    def enum_body(self, tree: List):
        return ("elements", tree)

    @v_args(inline=True)
    def enum_element(self, token: Token):
        return token.value

    def struct_def(self, tree):
        if "@compatible" in tree:
            info_list = tree[1:] + [("compatible", True)]
        else:
            info_list = tree + [("compatible", False)]

        return ("struct", dict(info_list))

    @v_args(inline=True)
    def COMPITABLE_FLAG(self, token: Token):
        return token.value

    def struct_body(self, tree: List):
        return ("items", tree)

    @v_args(inline=True)
    def struct_item(self, param_type: Union[Tuple, List[Tuple]], var_token: Union[Tuple, List[Tuple]]):
        if ("type", "array") in var_token:
            info_list: List = var_token + [param_type]
        elif ("type", "sequence") in param_type:
            info_list: List = param_type + [var_token]
        else:
            info_list: List = [("type", "single"), param_type, var_token]

        #  sort the tuples. "len" shoudle be the last
        info_list.sort(key=lambda x: (x[0] == "len", x[0]))
        return dict(info_list)

    @v_args(inline=True)
    def data_type(self, token: str):
        return ("data_type", token.value)

    @v_args(inline=True)
    def dynamic_array_type(self, tree):
        return [("type", "sequence"), tree]

    @v_args(inline=True)
    def var_token(self, tree: Union[List, Tuple]):
        if isinstance(tree, list):
            return tree
        elif isinstance(tree, tuple):
            return [tree]

    @v_args(inline=True)
    def c_array(self, name, length):
        return [("type", "array"), name, length]

    @v_args(inline=True)
    def array_len(self, token: Token):
        return ("len", int(token.value))

    def typedef_def(self, token: Token):
        info_dict = dict(token)
        return ("typedef", info_dict)

    @v_args(inline=True)
    def origin_type(self, param_type: Union[Tuple, List[Tuple]]):
        if ("type", "sequence") in param_type:
            info_list: List = param_type
        else:
            info_list: List = [("type", "single"), param_type]

        return ("origin_type", dict(info_list))

    @v_args(inline=True)
    def alias(self, token: Token):
        return ("alias", token.value)

    @v_args(inline=True)
    def service_def(self, name: Tuple, service_body: Dict):
        key, value = name
        info_dict = service_body
        info_dict[key] = value
        return ("service", info_dict)

    def service_body(self, token: List):
        service_body: Dict[str, Union[Dict, List]] = {"version": {}, "method": [], "field": [], "event": []}
        for key, value in token:
            if key == "version":
                service_body[key] = value
            else:
                service_body[key].append(value)

        return service_body

    @v_args(inline=True)
    def version_def(self, major_num: Token, minor_num: Token):
        return ("version", {"major": int(major_num.value), "minor": int(minor_num.value)})

    def method_def(self, token: Token):
        return ("method", dict(token))

    def param_list(self, token: List[Token]):
        return ("param_list", [param.value for param in token])

    @v_args(inline=True)
    def return_type(self, token: Token):
        return ("returns", token.value)

    @v_args(inline=True)
    def error_type(self, token: Token):
        return ("error", token.value)

    def field_def(self, tree: List):
        info_dict = dict(tree)
        # For simple filed, both get/set/notify are true
        if "field_body" not in info_dict:
            info_dict["field_body"] = {"get": True, "set": True, "notify": True}
        return ("field", info_dict)

    def field_body(self, tree: List):
        info_dict = dict(tree)
        # Field should has all of get/set/notify
        if "get" not in info_dict:
            raise UnexpectedInput('Need "get" for field')
        if "set" not in info_dict:
            raise UnexpectedInput('Need "set" for field')
        if "notify" not in info_dict:
            raise UnexpectedInput('Need "notify" for field')
        return ("field_body", info_dict)

    @v_args(inline=True)
    def get(self, token: bool):
        return ("get", token)

    @v_args(inline=True)
    def set(self, token: bool):
        return ("set", token)

    @v_args(inline=True)
    def notify(self, token: bool):
        return ("notify", token)

    @v_args(inline=True)
    def TRUE(self, _: Token):
        return True

    @v_args(inline=True)
    def FALSE(self, _: Token):
        return False

    def event_def(self, tree: List):
        return ("event", dict(tree))
