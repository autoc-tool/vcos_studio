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
import json
import hashlib

__all__ = ["Hasher"]


class Hasher:

    @staticmethod
    def compute_hash(input):
        """
        计算给定输入（字典或字符串）的SHA-256哈希值。

        如果输入是字典，该函数会先将字典的键进行排序，然后将其转化为字符串。
        如果输入是字符串，该函数会直接对其进行哈希计算。

        参数:
        input -- 输入，可以是字符串或字典。字典的键必须是可排序的（即，必须是可哈希的）。

        返回:
        一个代表输入哈希值的字符串，长度为64个字符。

        异常:
        TypeError -- 如果输入既不是字符串也不是字典，则会抛出TypeError。
        """
        if isinstance(input, dict):
            input_str = json.dumps(input, sort_keys=False)
        elif isinstance(input, str):
            input_str = input
        else:
            raise TypeError("输入类型必须是字典或字符串")

        input_bytes = input_str.encode("utf-8")
        return hashlib.sha256(input_bytes).hexdigest()
