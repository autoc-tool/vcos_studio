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
from func_module.validation.validator import Validator, ValidationData
from cmd_adaptor.data_management import get_autosar_asw_class
from cmd_adaptor.data_management import get_autosar_bsw_class
from cmd_adaptor.data_management import get_autosar_system_class
from cmd_adaptor.data_management import get_autosar_ib_class
from cmd_adaptor.data_management import get_autosar_bswmd_class
from cmd_adaptor.data_management import get_sys_info_class
from cmd_adaptor.data_management import get_sys_target_dict
from cmd_adaptor.func_logic_layer.load_save_project import LoadAndSaveProject
from func_module.project_management.studio_cfg_handler import StudioCfgHandler
from func_module.module_management.arxml_handler.ib_bswmd_process.ib_bswmd_process import IbBswmdProcess
from func_module.module_management.arxml_handler.rte_instances.rte_instances_manager import (
    update_rte_instances_and_os_resource_spinlock,
)
from cmd_adaptor.func_logic_layer.mapping_func.task_mapping_cmd_func import TaskMappingCmdFunc
from cmd_adaptor.data_management import data_management as data
from time import time
from cmd_adaptor.cmd_interaction.cmd_logger import logger
from func_module.health_monitor.perf_record import log_function_stats
from func_module.generator import generator as vcos_gen
from func_module.mapping.task_mapping_core import TaskMappingInstance


class ValidateCmdFunc:

    validation_instance = None

    @classmethod
    def update_instance(cls):
        validation_data = ValidationData(
            get_autosar_asw_class(),
            get_autosar_bsw_class(),
            get_autosar_ib_class(),
            get_autosar_system_class(),
            get_autosar_bswmd_class(),
            get_sys_info_class(),
        )
        module_list = getattr(get_sys_info_class(), "all_modules", [])
        cls.validation_instance = Validator(validation_data, module_list)

    @classmethod
    def execute_auto_validation(cls, project_path, module_list) -> bool:
        LoadAndSaveProject.load_project(project_path)

        if not getattr(cls, "validation_instance", None):
            cls.update_instance()

        cls.load_ignored_logs_from_file()

        module_list = cls.get_validation_input_dict(module_list)

        cls.validate_modules(module_list)

        logger.info("start saving arxml ...")
        LoadAndSaveProject.validate_save_project()
        logger.info("finish saving arxml ...")
        return True

    @classmethod
    @log_function_stats(["Studio性能统计", "Validation校验耗时"])
    def validate_modules(cls, module_list):
        logger.info("start executing auto validation ...")
        start_time = time()

        is_update_instance, _ = TaskMappingInstance.check_task_mapping_config(data.autosar_bsw_class)
        cls.common_post_process(is_update_instance)

        validation_logs = cls.validation_instance.validate_module(module_list)

        total_time = "%.2f" % (time() - start_time)
        logger.info(f"finish executing auto validation in {total_time} seconds ...")
        return validation_logs

    @classmethod
    @log_function_stats(["校验", "命令行模块校验"])
    def validate_modules_with_result(cls, module_list, validation_level=None):
        """
        校验指定模块(代码生成的前置操作调用， 与ui保持一致)
        return:
            count_log_dict: 校验错误中 error 和 warning 的个数信息
            validation_result: key 为模块名, value 表示是否没有错误校验项, True 表示没有
        """
        cls.update_instance()
        if validation_level:
            setattr(data.sys_info_class, "generation_limit", validation_level)

        cls.load_ignored_logs_from_file()

        is_update_instance, _ = TaskMappingInstance.check_task_mapping_config(data.autosar_bsw_class)
        cls.common_post_process(is_update_instance)

        validation_modules = cls.get_validation_input_dict(module_list)

        # 校验得到完整校验项
        validation_logs = cls.validation_instance.validate_module(validation_modules)
        cls.remove_ignored_logs(list(validation_modules.keys()), validation_logs, cls.validation_instance.ignored_logs)

        _, validation_res_info = cls.validation_instance.parse_validation_result_info(
            validation_modules, validation_logs, cls.validation_instance.ignored_logs
        )

        validation_result = cls.show_validation_result(validation_res_info)

        return validation_result, validation_logs

    @classmethod
    def get_validate_module_list(cls, module_list, enable_modules):
        validate_module_set = [x.replace(" ", "") for x in module_list]
        validate_module_dict = {
            instance_name: module_info
            for instance_name, module_info in enable_modules.items()
            if instance_name in validate_module_set
        }
        return validate_module_dict

    @classmethod
    def common_post_process(cls, is_update_instance=True):
        other_input_info = {
            "codegen_autosar_dict": vcos_gen.init_codegen_autosar_dict(data),
            "sys_info_class": data.sys_info_class,
            "sys_target_dict": data.sys_target_dict,
            "is_rte_parse_new_dict": True,
        }
        IbBswmdProcess.update_all_ib_bswmd(
            data.autosar_ib_class,
            data.autosar_bsw_class,
            data.autosar_asw_class,
            data.autosar_system_class,
            other_input_info,
        )
        update_rte_instances_and_os_resource_spinlock(
            data.autosar_bswmd_class, data.autosar_asw_class, data.autosar_bsw_class, data.autosar_ib_class
        )
        if is_update_instance:
            TaskMappingCmdFunc.update_task_mapping_instance()

    @classmethod
    def load_ignored_logs_from_file(cls):
        if cls.validation_instance is None:
            cls.update_instance()
        sys_info_class = get_sys_info_class()
        if not sys_info_class or not hasattr(sys_info_class, "config_base_path"):
            return
        ignored_logs_path = os.path.join(sys_info_class.config_base_path, "system", "ignored_logs.log")
        cls.validation_instance.load_ignored_logs(ignored_logs_path)

    @classmethod
    def show_validation_result(cls, validation_res_info: dict):
        validation_result = {}
        limit_level = getattr(data.sys_info_class, "generation_limit", "Error")
        error_level = 0
        if limit_level in ["Error", "error"]:
            error_level = 0
        elif limit_level in ["Warnning", "warnning"]:
            error_level = 1
        elif limit_level == "no limit":
            error_level = -1

        for module_name, validation_info_list in validation_res_info.items():
            validation_result[module_name] = True
            for validation_info in validation_info_list:
                mark = validation_info["mark"]
                log_type = int(mark[-6])
                if log_type <= error_level:
                    element = validation_info["element"]
                    validation_result[module_name] = False
                    logger.error(
                        f"Validation Error:{mark} {validation_info['summary']}: (1){element[1][0]}. (2){element[0]}."
                    )
                    logger.info(f"element: {element}")
        return validation_result

    @classmethod
    def get_validation_input_dict(cls, module_list):
        validate_module_dict, _ = Validator.get_validation_configuration(data)
        if module_list:
            validate_module_dict = cls.get_validate_module_list(module_list, validate_module_dict)

        module_cfg = get_sys_target_dict().get("module_cfg", {})
        validate_module_dict = cls.validation_instance.get_validation_support_modules(validate_module_dict, module_cfg)
        get_sys_info_class().validate_modules = StudioCfgHandler.get_module_list(validate_module_dict)

        return validate_module_dict

    @classmethod
    def remove_ignored_logs(cls, module_list, validation_logs, ignored_logs):
        for module, module_validation in validation_logs.items():
            if (module not in module_list) or (module not in ignored_logs.keys()):
                continue
            if ("logs" not in module_validation.keys()) or ("logs" not in ignored_logs[module].keys()):
                continue
            for mark in ignored_logs[module]["logs"].keys():
                if mark not in module_validation["logs"].keys():
                    continue
                if "info" not in ignored_logs[module]["logs"][mark].keys():
                    continue
                for ignored_element in ignored_logs[module]["logs"][mark]["info"]:
                    for idx in range(len(module_validation["logs"][mark]["info"])):
                        if (
                            ignored_element[0] == module_validation["logs"][mark]["info"][idx][0]
                            and ignored_element[1] == module_validation["logs"][mark]["info"][idx][1]
                            and ignored_element[2] == module_validation["logs"][mark]["info"][idx][2]
                        ):
                            del module_validation["logs"][mark]["info"][idx]
                            break

    @classmethod
    def save_ignored_logs_to_file(cls):
        if cls.validation_instance is None:
            cls.update_instance()
        sys_info_class = get_sys_info_class()
        config_base_path = getattr(sys_info_class, "config_base_path")
        if not config_base_path:
            return
        ignored_logs_path = os.path.join(config_base_path, "system", "ignored_logs.log")
        cls.validation_instance.save_ignored_logs(ignored_logs_path)

    @classmethod
    def save_validation_logs_to_file(cls):
        if cls.validation_instance is None:
            cls.update_instance()

        sys_info_class = get_sys_info_class()
        config_base_path = getattr(sys_info_class, "config_base_path")
        if not config_base_path:
            return
        validation_log_path = os.path.join(config_base_path, "system", "validation_logs.log")
        cls.validation_instance.save_validation_logs(validation_log_path)
