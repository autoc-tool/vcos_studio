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
from func_module.module_management.arxml_handler.config_comparator import ConfigComparator
from func_module.health_monitor import perf_record


@perf_record.log_function_stats(["BSW Editor", "配置文件解析和导入", "Ecuc arxml文件对比合并框架", "对比Ecuc arxml"])
def compare_ecuc(old_config, new_config):
    comparator = ConfigComparator(old_config, new_config)
    comparator.config_comparator()
    return comparator


def all_diff_string(comparator: ConfigComparator):
    return comparator.all_diff_string()


@perf_record.log_function_stats(["BSW Editor", "配置文件解析和导入", "Ecuc arxml文件对比合并框架", "合并Ecuc Arxml"])
def merge_ecuc(comparator: ConfigComparator, disabled_change, progress_signal):
    progress_signal.emit("Merging ecuc")
    comparator.merge_ecuc(disabled_change)
