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
from basic_func_module.base_common.load_plug_in import LoadPlugIn
from cmd_adaptor.cmd_interaction.cmd_logger import logger
from cmd_adaptor.data_management import data_management
from cmd_adaptor.func_logic_layer.mapping_func.task_mapping_cmd_func import TaskMappingCmdFunc
from func_module.generator import generator as vcos_generator
from func_module.module_management.arxml_handler.ib_bswmd_process.ib_bswmd_process import IbBswmdProcess
from func_module.module_management.arxml_handler.rte_instances import rte_instances_manager
from func_module.health_monitor.perf_record import log_function_stats


class OsConfigureCmdFunc:
    def __init__(self) -> None:
        pass

    @classmethod
    def common_post_process(cls, is_update_instance=True):
        """根据RTE层推理BSW配置,摘自func_logic_layer的common_post_process()"""
        other_input_info = {
            "codegen_autosar_dict": vcos_generator.init_codegen_autosar_dict(data_management),
            "sys_info_class": data_management.sys_info_class,
            "sys_target_dict": data_management.sys_target_dict,
            "is_rte_parse_new_dict": True,
        }
        IbBswmdProcess.update_all_ib_bswmd(
            data_management.autosar_ib_class,
            data_management.autosar_bsw_class,
            data_management.autosar_asw_class,
            data_management.autosar_system_class,
            other_input_info,
        )
        rte_instances_manager.update_rte_instances_and_os_resource_spinlock(
            data_management.autosar_bswmd_class,
            data_management.autosar_asw_class,
            data_management.autosar_bsw_class,
            data_management.autosar_ib_class,
        )
        if is_update_instance:
            TaskMappingCmdFunc.update_task_mapping_instance()

    @classmethod
    @log_function_stats(["BSW Editor", "OS模块自动配置", "命令行配置导入"])
    def import_os_cfg(cls, file_name):
        """导入OS自动配置"""
        # 自动配置
        os_cfg_excel_parser = LoadPlugIn.load_module("Os", "config_plug_in.auto_config.os_cfg_excel_parser")
        OsCfgExcelImporter = getattr(os_cfg_excel_parser, "OsCfgExcelImporter")
        os_cfg_excel_importer = OsCfgExcelImporter(data_management)
        res = os_cfg_excel_importer.import_excel(file_name)
        if res is True:
            cls.common_post_process()
            logger.info("[CMD] Automatic configuration has been successfully completed.")
        else:
            logger.error("[CMD] Automatic configuration has been interrupted.")
        return res

    @classmethod
    @log_function_stats(["BSW Editor", "OS模块自动配置", "命令行配置导出"])
    def export_os_cfg(cls, file_name):
        """导出OS现有配置"""
        os_cfg_excel_parser = LoadPlugIn.load_module("Os", "config_plug_in.auto_config.os_cfg_excel_parser")
        OsCfgExcelExporter = getattr(os_cfg_excel_parser, "OsCfgExcelExporter")
        os_cfg_excel_exporter = OsCfgExcelExporter(data_management)
        res = os_cfg_excel_exporter.export_excel(file_name)
        if res is True:
            logger.info(f"[CMD] Configuration has been successfully exported to {file_name}.")
        else:
            logger.error("[CMD] Exporting configuration has been interrupted.")
        return res
