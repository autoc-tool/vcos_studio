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
from func_module.generator.bsw import parser as bsw_parser
from func_module.generator.rte import rte_parser as rte_parser
from func_module.generator.common.common import check_and_warn_missing_dependencies, ErrorCode
from func_module.module_management.arxml_handler.rte_instances.rte_instances_manager import (
    rte_bsw_instances_codegen_parser,
)


def get_config_dict(
    codegen_module_list: dict,
    cfg_info_dict: dict,
    asw_autosar_dict: dict,
    ecuc_autosar_dict: dict,
    system_autosar_dict: dict,
    internal_behavior_autosar_dict: dict,
    module_cfg: dict,
    enabled_module_list,
    enable_bsw_instance: bool,
    bswmd_autosar_dict=None,
    other_info={"rte_parse_new_dict": True},
):
    # memmap
    parser_ret = False
    config_dict = bsw_parser.get_config_dict({}, cfg_info_dict)
    for key, value in config_dict.items():
        cfg_info_dict["bsw"][key] = value
    bsw_instances = {}
    if "Rte" not in enabled_module_list and not enable_bsw_instance:
        # 无Rte且不使能bsw instance
        parser_ret = ErrorCode.NO_CODEGEN
    elif "Rte" not in enabled_module_list and enable_bsw_instance:
        try:
            bsw_instances = rte_bsw_instances_codegen_parser(ecuc_autosar_dict, internal_behavior_autosar_dict)
            cfg_info_dict.setdefault("rte", {}).setdefault("bsw_instances", {}).update(bsw_instances)
            parser_ret = ErrorCode.SCHM_CODEGEN
        except Exception as e:
            logger.exception(f"Bsw instances parser failed! {type(e)}")
            parser_ret = False
    else:
        check_and_warn_missing_dependencies(module_cfg, "Rte", enabled_module_list)
        try:
            rte_parser.get_config_dict(
                asw_autosar_dict,
                ecuc_autosar_dict,
                cfg_info_dict,
                system_autosar_dict,
                internal_behavior_autosar_dict,
                bswmd_autosar_dict,
                parse_new_dict=other_info["rte_parse_new_dict"],
            )
            bsw_instances = cfg_info_dict.get("rte", {}).get("bsw_instances", {})
            parser_ret = ErrorCode.RTE_CODEGEN if "Rte" in codegen_module_list else ErrorCode.NO_CODEGEN
        except Exception as e:
            logger.exception(f"Rte parser failed! {type(e)}")
            parser_ret = False
    for bsw_module_name, bsw_instance in bsw_instances.items():
        bsw_instance["is_mcal"] = module_cfg.get(bsw_module_name, {}).get("is_mcal", False)
        bsw_instance["symbol"] = module_cfg.get(bsw_module_name, {}).get("symbol", "")
        bsw_instance["support_ib_gen"] = (
            module_cfg.get(bsw_module_name, {}).get("internal_behavior", {}).get("support_generation", False)
        )
    return parser_ret


def get_swc_list(asw_autosar_dict):
    return rte_parser.get_parsered_swc_list(asw_autosar_dict)
