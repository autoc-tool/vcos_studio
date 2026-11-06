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
from basic_func_module.base_logger import logger
from ui_adaptor.data_management import data_management
from ui_adaptor.func_logic_layer.task_mapping_func import TaskMappingFunc
from func_module.generator import generator as vcos_generator
from func_module.module_management.arxml_handler.ib_bswmd_process.ib_bswmd_process import IbBswmdProcess
from func_module.module_management.arxml_handler.rte_instances import rte_instances_manager
from func_module.health_monitor.perf_record import log_function_stats


class OsConfigureUIFunc:
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
            TaskMappingFunc().update_instance()

    @classmethod
    @log_function_stats(["BSW Editor", "OS模块自动配置", "配置导入"])
    def import_os_cfg(cls, file_name, main_window, over_view_ui, progress_signal):
        """导入OS自动配置"""
        progress_signal.emit("Importing Os configuration and automatically configuring")
        # 自动配置
        os_cfg_excel_parser = LoadPlugIn.load_module("Os", "config_plug_in.auto_config.os_cfg_excel_parser")
        OsCfgExcelImporter = getattr(os_cfg_excel_parser, "OsCfgExcelImporter")
        os_cfg_excel_importer = OsCfgExcelImporter(data_management)
        res = os_cfg_excel_importer.import_excel(file_name)
        if res is True:
            cls.common_post_process()
            logger.ui_info("[UI] Automatic configuration has been successfully completed.")
            # 刷新UI
            if over_view_ui.cur_tab_name in ["EcuC", "Os", "OS Configuration"]:
                bsw_tab_widget = main_window.bswTabWidget
                bsw_tab_widget.currentChanged.emit(bsw_tab_widget.currentIndex())
        else:
            logger.ui_error("[UI] Automatic configuration has been interrupted.")
        return res

    @classmethod
    @log_function_stats(["BSW Editor", "OS模块自动配置", "配置导出"])
    def export_os_cfg(cls, file_name, progress_signal):
        """导出OS现有配置"""
        progress_signal.emit("Exporting Os configuration")
        os_cfg_excel_parser = LoadPlugIn.load_module("Os", "config_plug_in.auto_config.os_cfg_excel_parser")
        OsCfgExcelExporter = getattr(os_cfg_excel_parser, "OsCfgExcelExporter")
        os_cfg_excel_exporter = OsCfgExcelExporter(data_management)
        res = os_cfg_excel_exporter.export_excel(file_name)
        if res is True:
            logger.ui_info(f"[UI] Configuration has been successfully exported to {file_name}.")
        else:
            logger.ui_error("[UI] Exporting configuration has been interrupted.")
        return res
