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
from time import time, strftime, localtime
from func_module.mapping.port_mapping_core import PortMappingCore
from func_module.module_management.arxml_handler.system.flatextract_arxml_manager import FlatExtractArxmlManager
from func_module.health_monitor.perf_record import log_function_stats
from cmd_adaptor.data_management import data_management
from cmd_adaptor.func_logic_layer.load_save_project import LoadAndSaveProject
from cmd_adaptor.cmd_interaction.cmd_logger import logger
from basic_func_module.autosar_utils.autosar_utils import AutosarUtils


class PortMappingCmdFunc:

    @classmethod
    @log_function_stats(["Studio性能统计", "auto port mapping脚本执行耗时"])
    def app_port_mapping(cls, args):
        logger.info("start executing auto application port mapping ...")
        total_time = cls.map_port(args, data_management.autosar_asw_class, data_management.autosar_system_class)
        logger.info(f"finish executing auto application port mapping in {total_time} seconds ...")

    @classmethod
    @log_function_stats(["RTE", "PortMapping", "命令行自动PortMapping"])
    def execute_auto_app_port_mapping_command(cls, args) -> bool:
        LoadAndSaveProject.port_mapping_load_project(args.Project)
        cls.app_port_mapping(args)
        logger.info("start saving arxml ...")
        LoadAndSaveProject.port_mapping_save_project()
        logger.info("finish saving arxml ...")
        return True

    @classmethod
    def map_port(cls, args, asw_autosar_dict, system_autosar_dict):
        start_time = time()

        filter = PortMappingCore.cmd_filter_trans(args)
        all_app_ports = PortMappingCore.get_all_app_ports_dict(asw_autosar_dict, "not_service")
        mappings_result, logs = PortMappingCore.map_port(
            all_app_ports["pports"],
            all_app_ports["rports"],
            FlatExtractArxmlManager.get_assembly_and_delegation_sw_connector(system_autosar_dict["FlatExtract"]),
            filter,
        )
        cls.print_log_to_console(logs)
        PortMappingCore.save_port_mapping_list(list(mappings_result.values()), all_app_ports, system_autosar_dict)
        if getattr(args, "log_save", False):
            all_swc_prototypes = AutosarUtils.get_all_sw_component_prototypes(asw_autosar_dict)
            PortMappingCore.get_all_connected_and_unconnected_ports_list(
                system_autosar_dict["FlatExtract"], all_app_ports, logs, all_swc_prototypes
            )
            logger.info(" --- start saving mapping logs to excel ...")
            formatted_time = strftime("%Y%m%d-%H%M%S", localtime(start_time))
            file_path = os.path.abspath(
                f"{data_management.sys_info_class.log_path}/AutoPortMapping_Log_{formatted_time}.xlsx"
            )
            PortMappingCore.log_to_excel(file_path, logs)
            logger.info(" --- finish saving mapping logs to excel ...")
        total_time = "%.2f" % (time() - start_time)
        return total_time

    @classmethod
    def print_log_to_console(cls, logs):
        print("")
        if not (logs[0] or logs[1] or logs[2] or logs[3]):
            print(" --- no new ports are mapped ...")
        else:
            CATEGORY = ["1-1", "1-N", "N-1", "M-N"]
            log_cat_index = 0
            for curr_logs in logs:
                if log_cat_index > CATEGORY.index("M-N"):
                    # 防止Connected_Ports和UnConnected_Ports打印刷屏
                    break
                curr_log_cat = CATEGORY[log_cat_index]
                for log_entry in curr_logs:
                    print(f" --- {curr_log_cat}: {log_entry[0]} {log_entry[1]} <---> {log_entry[3]} {log_entry[4]}")
                log_cat_index += 1
        print("")
