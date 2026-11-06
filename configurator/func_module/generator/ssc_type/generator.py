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
Service component ARXML 生成入口.
调用各个模块的Port parser结果, 然后传给各个模块generator ARXML文件
"""
import os
import shutil
import inspect
from jinja2 import UndefinedError
from basic_func_module.base_common.load_plug_in import LoadPlugIn
from func_module.health_monitor.logger import logger
from func_module.health_monitor.perf_record import log_function_stats

module_list = ["ComM", "Dcm", "WdgM", "Dem", "Det", "EcuM", "NvM", "StbM", "Csm", "BswM"]

module_derive_dict = {}


def get_bsw_port_dict(enabled_module_list: list, module_ecuc_cfg):
    for module in module_list:
        if module not in enabled_module_list or module not in module_ecuc_cfg:
            module_derive_dict.pop(module.lower(), None)
            continue
        try:
            port_parser = LoadPlugIn.load_module(module, "config_plug_in.ssc_type.port_parser")
            port_derive_dict = port_parser.get_config_dict(module_ecuc_cfg)
            module_derive_dict[module.lower()] = port_derive_dict
        except ModuleNotFoundError:
            logger.warning(f"{module} does not support service swc")
        except Exception as e:
            logger.exception(f"{module} port parser failed! : {e}")


@log_function_stats(["代码生成", "Service SWC生成"])
def generate_bsw_port_arxml(config_path, enabled_module_list: list, module_ecuc_cfg, progress_signal=None):
    get_bsw_port_dict(enabled_module_list, module_ecuc_cfg)
    service_swc_arxml_folder = os.path.abspath(os.path.join(config_path, "service_components"))
    if not os.path.exists(service_swc_arxml_folder):
        os.makedirs(service_swc_arxml_folder)
    service_swc_arxml_file_list = os.listdir(service_swc_arxml_folder)
    for file_name in service_swc_arxml_file_list:
        file_path = os.path.join(service_swc_arxml_folder, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
    try:
        for module in module_list:
            service_swc_arxml_path = os.path.abspath(
                os.path.join(config_path, "service_components", f"{module}_swc.arxml")
            )
            if module.lower() not in module_derive_dict:
                continue
            try:
                if progress_signal:
                    progress_signal.emit(f"Generating {module}_swc.arxml")
                module_pkg = LoadPlugIn.load_module(module, "config_plug_in.ssc_type.generator")
                if os.path.exists(service_swc_arxml_path):
                    os.remove(service_swc_arxml_path)
                module_pkg.generate_arxml(config_path, module_derive_dict[module.lower()])
            except ModuleNotFoundError:
                logger.warning(f"{module} does not support service swc")
            except UndefinedError as e:
                # find the error location in the template
                error_info = None
                frame_info_list = inspect.trace()
                frame_info_list.reverse()
                for frame_info in frame_info_list:
                    if frame_info.function == "top-level template code":
                        error_info = frame_info
                        break
                filename = os.path.basename(error_info.filename)
                error_line = error_info.lineno
                error_code = error_info.code_context[0].strip()
                logger.error(f"UndefinedError: {filename}:{error_line} {error_code} {e}")
            except Exception:
                raise RuntimeError(module)
    except RuntimeError:
        logger.ui_error(f"{module} generate service arxml failed!")
