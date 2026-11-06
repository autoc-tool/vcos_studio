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
import os
import sys
from collections import defaultdict
from basic_func_module.autosar_utils.utils import get_definition_ref, get_value_ref, get_value, get_short_name
from ui_adaptor.data_management import data_management as data
from func_module.export_file.cheddar_generator import CheddarGenerator
from ui_adaptor.ui_interaction.ui_logger import logger


class TaskAnalysisLogic:

    def __init__(self) -> None:
        pass

    @classmethod
    def task_analysis_ui_info(cls):
        os_cfg = data.autosar_bsw_class.get("Os", None)
        ecuc_cfg = data.autosar_bsw_class.get("EcuC", None)

        # No Os module yet, return nothing
        if not os_cfg or not ecuc_cfg:
            return {}
        # No Os config yet, return nothing
        if not (os_cfg_vals := os_cfg.find("/ActiveEcuC/Os")):
            return {}

        # Gather all applications
        os_container_l = getattr(getattr(os_cfg_vals, "CONTAINERS", None), "ECUC_CONTAINER_VALUE", [])
        os_app_l = [c for c in os_container_l if get_definition_ref(c).split("/")[-1] == "OsApplication"]

        # Read refed core of applications
        app_core_path_map = {
            app: get_value_ref(ref)
            for app in os_app_l
            for ref in getattr(getattr(app, "REFERENCE_VALUES", None), "ECUC_REFERENCE_VALUE", [])
            if get_definition_ref(ref).split("/")[-1] == "OsApplicationCoreRef"
        }

        # Build mapping from core id to applications
        core_app_map = defaultdict(list)
        for app_obj, core_path in app_core_path_map.items():
            core_obj = ecuc_cfg.find(core_path)
            # Find core id of core obj
            core_id = None
            for param in getattr(getattr(core_obj, "PARAMETER_VALUES", None), "ECUC_NUMERICAL_PARAM_VALUE", []):
                if get_definition_ref(param).split("/")[-1] == "EcucCoreId":
                    core_id = get_value(param)
                    break
            assert core_id, f"Find no core id of {get_short_name(core_obj)}"
            core_app_map[f"Core{core_id}"].append(app_obj)

        # Build mapping from core id to tasks and isrs
        result = defaultdict(dict)
        for core_id, apps in core_app_map.items():
            task_res = {}
            isr_res = {}
            for app in apps:
                # Gather tasks refed by application
                for ref in getattr(getattr(app, "REFERENCE_VALUES", None), "ECUC_REFERENCE_VALUE", []):
                    if get_definition_ref(ref).split("/")[-1] == "OsAppTaskRef" and (task_path := get_value_ref(ref)):
                        task_name = task_path.split("/")[-1]
                        # Omit idle task
                        if "idle" in task_name.lower():
                            continue

                        task_res[task_name] = {
                            "attr": {
                                "cet_max(ms)": {
                                    "val": None,  # attribute val
                                    "editable": True,  # attribute editable?
                                    "idx": 0,  # attribute col index
                                },
                                "cet_avg(ms)": {"val": None, "editable": True, "idx": 1},
                                "type": {"val": "task", "editable": False, "idx": 2},
                            }
                        }
                    elif get_definition_ref(ref).split("/")[-1] == "OsAppIsrRef" and (isr_path := get_value_ref(ref)):
                        isr_name = isr_path.split("/")[-1]
                        isr_res[isr_name] = {
                            "attr": {
                                "cet_max(ms)": {
                                    "val": None,  # attribute val
                                    "editable": True,  # attribute editable?
                                    "idx": 0,  # attribute col index
                                },
                                "cet_avg(ms)": {"val": None, "editable": True, "idx": 1},
                                "type": {"val": "isr", "editable": False, "idx": 2},
                            }
                        }
            result[core_id].update(task_res)
            result[core_id].update(isr_res)

        return result

    @classmethod
    def gen_cheddar_with_cet(cls, cet_info, target_dir, progress_signal=None):
        progress_signal and progress_signal.emit("Generating cheddar project file")

        generator = CheddarGenerator()
        generator.clear_id_count()
        generator.build_model(cet_info, data.autosar_bsw_class, data.autosar_ib_class, data.autosar_asw_class)
        generator.gen_cheddar(target_dir)

    @classmethod
    def schedulability_analysis(cls, cet_info, progress_signal=None):
        progress_signal and progress_signal.emit("Generating cheddar project file")

        generator = CheddarGenerator()
        generator.clear_id_count()
        generator.build_model(cet_info, data.autosar_bsw_class, data.autosar_ib_class, data.autosar_asw_class)

        from basic_func_module.base_common.load_plug_in import LoadPlugIn

        jitter = LoadPlugIn.load_module("Os", "config_plug_in.schedual_analysis.schedulability_analysis")
        SchedulabilityAnalysis = getattr(jitter, "SchedulabilityAnalysis")
        analyser = SchedulabilityAnalysis()
        analyser.set_model(generator)
        res = analyser.analysis()

        return res

    @classmethod
    def get_ftrace_task_irq_info(cls, file_path, progress_signal=None):
        cur_file_path = os.path.dirname(os.path.realpath(__file__))
        vcos_trace_path = os.path.abspath(os.path.join(cur_file_path, "..", "..", "..", "halo_trace"))
        halo_trace_path = os.path.abspath(
            os.path.join(cur_file_path, "..", "..", "..", "..", "..", "tools", "halo_trace")
        )
        if os.path.exists(vcos_trace_path):
            sys.path.append(vcos_trace_path)
        elif os.path.exists(halo_trace_path):
            sys.path.append(halo_trace_path)
        from ftrace_manager import FtraceParser

        progress_signal and progress_signal.emit("Parsing task info from ftrace")
        res, task_info = FtraceParser.get_ftrace_task_info(file_path, {})
        if not res:
            logger.ui_error(f"Cannot parse task info from {file_path}")
            logger.error(f"Cannot parse task info from {file_path}")

        progress_signal and progress_signal.emit("Parsing irq info from ftrace")
        res, irq_info = FtraceParser.get_ftrace_irq_info(file_path, {})
        if not res:
            logger.ui_error(f"Cannot parse isr info from {file_path}")
            logger.error(f"Cannot parse isr info from {file_path}")
        return task_info, irq_info
