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
模拟器驱动代码生成模块
"""
import os
import shutil

from basic_func_module.base_common.load_plug_in import LoadPlugIn
from func_module.health_monitor.logger import logger

SIM_CODEGEN_MODULES = {"Can"}

def generate(
    sys_config: dict,
    config_dict: dict,
    ecuc_autosar_dict: dict,
    module_cfg: dict,
    progress_signal
):
    """
    Generate sim drivers code
    """
    sim_name = "Sim"
    if sys_config.get("sim_mode", False) is not True:
        sim_gendata_dir = os.path.join(sys_config["gendata_path"], "Sim")
        if os.path.exists(sim_gendata_dir):
            shutil.rmtree(sim_gendata_dir)
            logger.ui_info(f"Remove {sim_gendata_dir} successfully!")
        return {}

    if sim_name not in sys_config["plug_in_path"].keys():
        logger.warning(f"{sim_name} does not support c code generation")
        return {}

    module_pkg = LoadPlugIn.load_module(sim_name, "config_plug_in.generator.generator")
    if module_pkg is None:
        logger.exception(f"{sim_name} does not support c code generation")
        return {}

    generate_c_code = getattr(module_pkg, "generate_c_code")
    ret = generate_c_code(sys_config, config_dict, ecuc_autosar_dict, module_cfg, progress_signal)
    return ret


