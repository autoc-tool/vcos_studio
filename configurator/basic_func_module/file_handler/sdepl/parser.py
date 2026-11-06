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
import yaml
from basic_func_module.base_logger import logger


def parse_sdepl_file(file_path: str):
    with open(file_path, "r") as f:
        try:
            info_dict = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            logger.exception(exc)
            raise exc

    return info_dict
