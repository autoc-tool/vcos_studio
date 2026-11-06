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
from func_module.generator.rte.rte_parser import get_vfb_trace_functions
from ui_adaptor.data_management import get_autosar_bsw_class, get_autosar_bswmd_class
from func_module.health_monitor import perf_record
from func_module.module_management.bsw_editor.bsw_editor import BswEditor
from basic_func_module.base_logger import logger


class VfbTraceFunction:

    @perf_record.log_function_stats(["Trace", "trace数据打点", "VFB trace打点"])
    def cbk_clear_vfb_trace_functions(self, container_path, module_name, mod_path, tag):
        """
        clear configured trace function
        """
        try:
            bsw_ecuc_dict = get_autosar_bsw_class()
            bsw_mod_dict = get_autosar_bswmd_class()
            configured_value_list = get_vfb_trace_functions(bsw_ecuc_dict)
            for configured_value in configured_value_list:
                BswEditor.remove_param_item_and_write_to_ecuc_arxml(
                    bsw_ecuc_dict, bsw_mod_dict, configured_value, mod_path, module_name, container_path, tag, None
                )
        except Exception as e:
            logger.error(f"clear vfb trace function error: {e}")
