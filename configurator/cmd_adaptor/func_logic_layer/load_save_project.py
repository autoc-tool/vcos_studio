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
from cmd_adaptor.data_management import data_management
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlParseHandler, ArxmlSaveHandler
from func_module.project_management.project_file_parser import ProjectFileParser
from func_module.project_management.sys_info_class import SysInfoClass
from cmd_adaptor.cmd_interaction.cmd_logger import logger
from func_module.module_management.arxml_handler.ecuc_arxml_updater import EcucArxmlUpdater

CUR_PATH = os.path.dirname(__file__)


class LoadAndSaveProject:

    @classmethod
    def import_asw_load_project(cls, project_file_path) -> bool:
        """
        load arxml
        """
        # ProjectFileParser提供工程文件配置解析
        project_file_parser = ProjectFileParser()
        project_file_parser.load_file(project_file_path)
        """if return false """
        # 实例化SysInfoClass提供get、set方法
        sys_info_obj = SysInfoClass()
        # 从ProjectFileParser解析或者构造的配置设值sys_info_obj
        project_file_parser.init_sys_info(sys_info_obj)
        data_management.sys_info_class = sys_info_obj
        data_management.sys_target_dict = data_management.sys_info_class.system_target_info
        data_management.sys_info_class.all_modules = project_file_parser.get_all_module_list(
            data_management.sys_target_dict
        )
        data_management.all_module_list = data_management.sys_info_class.all_modules

        # 1. parse ecuc arxml
        # 2. parse ib arxml
        # 3. parse system arxml
        # 4. parse bswm arxml
        config_base_path = data_management.sys_info_class.config_base_path
        data_management.autosar_system_class = ArxmlParseHandler.parse_system_dir_arxml(config_base_path)
        if data_management.autosar_system_class is None:
            return False
        data_management.cfg_info_dict.update({"target": getattr(data_management.sys_info_class, "target")})

        return data_management.autosar_system_class, sys_info_obj

    @classmethod
    def import_dbc_ldf_load_project(cls, project_file_path) -> bool:
        """
        load arxml
        """
        # ProjectFileParser提供工程文件配置解析
        project_file_parser = ProjectFileParser()
        project_file_parser.load_file(project_file_path)
        """if return false """
        # 实例化SysInfoClass提供get、set方法
        sys_info_obj = SysInfoClass()
        # 从ProjectFileParser解析或者构造的配置设值sys_info_obj
        project_file_parser.init_sys_info(sys_info_obj)
        data_management.sys_info_class = sys_info_obj
        data_management.sys_target_dict = data_management.sys_info_class.system_target_info
        data_management.sys_info_class.all_modules = project_file_parser.get_all_module_list(
            data_management.sys_target_dict
        )
        data_management.all_module_list = data_management.sys_info_class.all_modules
        data_management.cfg_info_dict.update({"target": getattr(data_management.sys_info_class, "target")})
        # 1. parse ecuc arxml
        # 2. parse ib arxml
        # 3. parse system arxml
        # 4. parse bswm arxml
        config_base_path = data_management.sys_info_class.config_base_path
        enable_module_list = data_management.sys_info_class.enable_modules
        data_management.autosar_asw_class = ArxmlParseHandler.parse_asw_arxml(config_base_path)
        if data_management.autosar_asw_class is None:
            return False
        data_management.autosar_system_class = ArxmlParseHandler.parse_system_dir_arxml(config_base_path)
        if data_management.autosar_system_class is None:
            return False
        data_management.autosar_bswmd_class = ArxmlParseHandler.parse_all_bswmd_arxml(
            data_management.sys_info_class.plug_in_bswmd_path, enable_module_list, data_management.sys_info_class.target
        )
        if data_management.autosar_bswmd_class is None:
            return False
        data_management.autosar_bsw_class = ArxmlParseHandler.parse_autosar_ecuc_arxml(
            config_base_path, enable_module_list
        )
        if data_management.autosar_bsw_class is None:
            return False

    @classmethod
    def import_cdd_load_project(cls, project_file_path) -> bool:
        """
        load arxml
        """
        # ProjectFileParser提供工程文件配置解析
        project_file_parser = ProjectFileParser()
        project_file_parser.load_file(project_file_path)
        """if return false """
        # 实例化SysInfoClass提供get、set方法
        sys_info_obj = SysInfoClass()
        # 从ProjectFileParser解析或者构造的配置设值sys_info_obj
        project_file_parser.init_sys_info(sys_info_obj)
        data_management.sys_info_class = sys_info_obj
        data_management.sys_target_dict = data_management.sys_info_class.system_target_info
        data_management.sys_info_class.all_modules = project_file_parser.get_all_module_list(
            data_management.sys_target_dict
        )
        data_management.all_module_list = data_management.sys_info_class.all_modules
        # 1. parse ecuc arxml
        # 2. parse ib arxml
        # 3. parse system arxml
        # 4. parse bswm arxml
        config_base_path = data_management.sys_info_class.config_base_path
        enable_module_list = data_management.sys_info_class.enable_modules
        data_management.autosar_asw_class = ArxmlParseHandler.parse_asw_arxml(config_base_path)
        data_management.cfg_info_dict.update({"target": getattr(data_management.sys_info_class, "target")})
        if data_management.autosar_asw_class is None:
            return False
        data_management.autosar_system_class = ArxmlParseHandler.parse_system_dir_arxml(config_base_path)
        if data_management.autosar_system_class is None:
            return False
        data_management.autosar_bswmd_class = ArxmlParseHandler.parse_all_bswmd_arxml(
            data_management.sys_info_class.plug_in_bswmd_path, enable_module_list, data_management.sys_info_class.target
        )
        if data_management.autosar_bswmd_class is None:
            return False
        data_management.autosar_bsw_class = ArxmlParseHandler.parse_autosar_ecuc_arxml(
            config_base_path, enable_module_list
        )
        if data_management.autosar_bsw_class is None:
            return False
        data_management.autosar_ib_class = ArxmlParseHandler.parse_internal_behavior_arxml(
            config_base_path, enable_module_list, data_management.sys_target_dict
        )
        if data_management.autosar_ib_class is None:
            return False

        return [
            sys_info_obj,
            data_management.autosar_bsw_class,
            data_management.autosar_bswmd_class,
            data_management.autosar_ib_class,
            data_management.cfg_info_dict,
            data_management.autosar_system_class,
            data_management.sys_target_dict,
        ]

    @classmethod
    def import_mcal_load_project(cls, project_file_path) -> bool:
        """
        load arxml
        """
        # ProjectFileParser提供工程文件配置解析
        project_file_parser = ProjectFileParser()
        project_file_parser.load_file(project_file_path)
        """if return false """
        # 实例化SysInfoClass提供get、set方法
        sys_info_obj = SysInfoClass()
        # 从ProjectFileParser解析或者构造的配置设值sys_info_obj
        project_file_parser.init_sys_info(sys_info_obj)
        data_management.sys_info_class = sys_info_obj
        data_management.sys_target_dict = data_management.sys_info_class.system_target_info
        data_management.sys_info_class.all_modules = project_file_parser.get_all_module_list(
            data_management.sys_target_dict
        )
        data_management.all_module_list = data_management.sys_info_class.all_modules
        data_management.cfg_info_dict.update({"target": getattr(data_management.sys_info_class, "target")})
        # 1. parse ecuc arxml
        # 2. parse ib arxml
        # 3. parse system arxml
        # 4. parse bswm arxml
        config_base_path = data_management.sys_info_class.config_base_path
        enable_module_list = data_management.sys_info_class.enable_modules
        # data_management.autosar_asw_class = ArxmlParseHandler.parse_asw_arxml(config_base_path)
        # if data_management.autosar_asw_class is None:
        #     return False
        data_management.autosar_system_class = ArxmlParseHandler.parse_system_dir_arxml(config_base_path)
        if data_management.autosar_system_class is None:
            return False
        data_management.autosar_bswmd_class = ArxmlParseHandler.parse_all_bswmd_arxml(
            data_management.sys_info_class.plug_in_bswmd_path, enable_module_list, data_management.sys_info_class.target
        )
        if data_management.autosar_bswmd_class is None:
            return False
        data_management.autosar_bsw_class = ArxmlParseHandler.parse_autosar_ecuc_arxml(
            config_base_path, enable_module_list
        )
        if data_management.autosar_bsw_class is None:
            return False
        # data_management.autosar_ib_class = ArxmlParseHandler.parse_internal_behavior_arxml(
        #     config_base_path, enable_module_list, data_management.sys_target_dict)
        # if data_management.autosar_ib_class is None:
        #     return False

    @classmethod
    def task_mapping_load_project(cls, project_file_path) -> bool:
        """
        load arxml
        """
        # ProjectFileParser提供工程文件配置解析
        project_file_parser = ProjectFileParser()
        project_file_parser.load_file(project_file_path)
        """if return false """
        # 实例化SysInfoClass提供get、set方法
        sys_info_obj = SysInfoClass()
        # 从ProjectFileParser解析或者构造的配置设值sys_info_obj
        project_file_parser.init_sys_info(sys_info_obj)
        data_management.sys_info_class = sys_info_obj
        data_management.sys_target_dict = data_management.sys_info_class.system_target_info
        data_management.sys_info_class.all_modules = project_file_parser.get_all_module_list(
            data_management.sys_target_dict
        )
        data_management.all_module_list = data_management.sys_info_class.all_modules
        data_management.cfg_info_dict.update({"target": getattr(data_management.sys_info_class, "target")})
        # 1. parse ecuc arxml
        # 2. parse ib arxml
        # 3. parse system arxml
        # 4. parse bswm arxml
        config_base_path = data_management.sys_info_class.config_base_path
        enable_module_list = data_management.sys_info_class.enable_modules
        data_management.autosar_asw_class = ArxmlParseHandler.parse_asw_arxml(config_base_path)
        if data_management.autosar_asw_class is None:
            return False
        data_management.autosar_system_class = ArxmlParseHandler.parse_system_dir_arxml(config_base_path)
        if data_management.autosar_system_class is None:
            return False
        data_management.autosar_bswmd_class = ArxmlParseHandler.parse_all_bswmd_arxml(
            data_management.sys_info_class.plug_in_bswmd_path, enable_module_list, data_management.sys_info_class.target
        )
        if data_management.autosar_bswmd_class is None:
            return False
        data_management.autosar_bsw_class = ArxmlParseHandler.parse_autosar_ecuc_arxml(
            config_base_path, enable_module_list
        )
        if data_management.autosar_bsw_class is None:
            return False
        data_management.autosar_ib_class = ArxmlParseHandler.parse_internal_behavior_arxml(
            config_base_path, enable_module_list, data_management.sys_target_dict
        )
        if data_management.autosar_ib_class is None:
            return False

    @classmethod
    def data_mapping_load_project(cls, project_file_path) -> bool:
        """
        load arxml
        """
        # ProjectFileParser提供工程文件配置解析
        project_file_parser = ProjectFileParser()
        project_file_parser.load_file(project_file_path)
        """if return false """
        # 实例化SysInfoClass提供get、set方法
        sys_info_obj = SysInfoClass()
        # 从ProjectFileParser解析或者构造的配置设值sys_info_obj
        project_file_parser.init_sys_info(sys_info_obj)
        data_management.sys_info_class = sys_info_obj
        data_management.sys_target_dict = data_management.sys_info_class.system_target_info
        data_management.sys_info_class.all_modules = project_file_parser.get_all_module_list(
            data_management.sys_target_dict
        )
        data_management.all_module_list = data_management.sys_info_class.all_modules
        data_management.cfg_info_dict.update({"target": getattr(data_management.sys_info_class, "target")})
        # 1. parse ecuc arxml
        # 2. parse ib arxml
        # 3. parse system arxml
        # 4. parse bswm arxml
        config_base_path = data_management.sys_info_class.config_base_path
        data_management.autosar_asw_class = ArxmlParseHandler.parse_asw_arxml(config_base_path)
        if data_management.autosar_asw_class is None:
            return False
        data_management.autosar_system_class = ArxmlParseHandler.parse_system_dir_arxml(config_base_path)
        if data_management.autosar_system_class is None:
            return False
        data_management.autosar_bsw_class = ArxmlParseHandler.parse_autosar_ecuc_arxml(config_base_path, ["Com"])
        if data_management.autosar_bsw_class is None:
            return False

    @classmethod
    def service_mapping_load_project(cls, project_file_path) -> bool:
        """
        load arxml
        """
        # ProjectFileParser提供工程文件配置解析
        project_file_parser = ProjectFileParser()
        project_file_parser.load_file(project_file_path)
        """if return false """
        # 实例化SysInfoClass提供get、set方法
        sys_info_obj = SysInfoClass()
        # 从ProjectFileParser解析或者构造的配置设值sys_info_obj
        project_file_parser.init_sys_info(sys_info_obj)
        data_management.sys_info_class = sys_info_obj
        data_management.sys_target_dict = data_management.sys_info_class.system_target_info
        data_management.sys_info_class.all_modules = project_file_parser.get_all_module_list(
            data_management.sys_target_dict
        )
        data_management.all_module_list = data_management.sys_info_class.all_modules
        data_management.cfg_info_dict.update({"target": getattr(data_management.sys_info_class, "target")})
        # 1. parse ecuc arxml
        # 2. parse ib arxml
        # 3. parse system arxml
        # 4. parse bswm arxml
        config_base_path = data_management.sys_info_class.config_base_path
        enable_module_list = data_management.sys_info_class.enable_modules
        data_management.autosar_asw_class = ArxmlParseHandler.parse_asw_arxml(config_base_path)
        if data_management.autosar_asw_class is None:
            return False
        data_management.autosar_system_class = ArxmlParseHandler.parse_system_dir_arxml(config_base_path)
        if data_management.autosar_system_class is None:
            return False
        data_management.autosar_bswmd_class = ArxmlParseHandler.parse_all_bswmd_arxml(
            data_management.sys_info_class.plug_in_bswmd_path, enable_module_list, data_management.sys_info_class.target
        )
        if data_management.autosar_bswmd_class is None:
            return False
        data_management.autosar_bsw_class = ArxmlParseHandler.parse_autosar_ecuc_arxml(
            config_base_path, enable_module_list
        )
        if data_management.autosar_bsw_class is None:
            return False
        data_management.autosar_ib_class = ArxmlParseHandler.parse_internal_behavior_arxml(
            config_base_path, enable_module_list, data_management.sys_target_dict
        )
        if data_management.autosar_ib_class is None:
            return False

    @classmethod
    def port_mapping_load_project(cls, project_file_path) -> bool:
        """
        load arxml
        """
        # ProjectFileParser提供工程文件配置解析
        project_file_parser = ProjectFileParser()
        project_file_parser.load_file(project_file_path)
        """if return false """
        # 实例化SysInfoClass提供get、set方法
        sys_info_obj = SysInfoClass()
        # 从ProjectFileParser解析或者构造的配置设值sys_info_obj
        project_file_parser.init_sys_info(sys_info_obj)
        data_management.sys_info_class = sys_info_obj
        data_management.sys_target_dict = data_management.sys_info_class.system_target_info
        data_management.sys_info_class.all_modules = project_file_parser.get_all_module_list(
            data_management.sys_target_dict
        )
        data_management.all_module_list = data_management.sys_info_class.all_modules
        # 1. parse ecuc arxml
        # 2. parse ib arxml
        # 3. parse system arxml
        # 4. parse bswm arxml
        config_base_path = data_management.sys_info_class.config_base_path
        enable_module_list = data_management.sys_info_class.enable_modules
        data_management.autosar_asw_class = ArxmlParseHandler.parse_asw_arxml(config_base_path)
        data_management.cfg_info_dict.update({"target": getattr(data_management.sys_info_class, "target")})
        if data_management.autosar_asw_class is None:
            return False
        data_management.autosar_system_class = ArxmlParseHandler.parse_system_dir_arxml(config_base_path)
        if data_management.autosar_system_class is None:
            return False
        data_management.autosar_bswmd_class = ArxmlParseHandler.parse_all_bswmd_arxml(
            data_management.sys_info_class.plug_in_bswmd_path, enable_module_list, data_management.sys_info_class.target
        )
        if data_management.autosar_bswmd_class is None:
            return False
        data_management.autosar_bsw_class = ArxmlParseHandler.parse_autosar_ecuc_arxml(
            config_base_path, enable_module_list
        )
        if data_management.autosar_bsw_class is None:
            return False
        data_management.autosar_ib_class = ArxmlParseHandler.parse_internal_behavior_arxml(
            config_base_path, enable_module_list, data_management.sys_target_dict
        )
        if data_management.autosar_ib_class is None:
            return False
        pass

    @classmethod
    def load_project(cls, project_file_path) -> bool:
        """
        load arxml
        """
        # ProjectFileParser提供工程文件配置解析
        project_file_parser = ProjectFileParser()
        result = project_file_parser.load_file(project_file_path)
        if result is False:
            return False
        compatibility_info = project_file_parser.get_version_compatibility_info()
        ret = project_file_parser.process_compatibility_info(compatibility_info)
        if not ret:
            return False
        project_file_parser.cfg_pre_check()
        """if return false """
        # 实例化SysInfoClass提供get、set方法
        sys_info_obj = SysInfoClass()
        # 从ProjectFileParser解析或者构造的配置设值sys_info_obj
        result = project_file_parser.init_sys_info(sys_info_obj)
        if not result:
            return False
        data_management.sys_info_class = sys_info_obj
        data_management.sys_target_dict = data_management.sys_info_class.system_target_info
        data_management.sys_info_class.all_modules = project_file_parser.get_all_module_list(
            data_management.sys_target_dict
        )
        data_management.all_module_list = data_management.sys_info_class.all_modules
        data_management.cfg_info_dict.update({"target": getattr(data_management.sys_info_class, "target")})
        # 1. parse ecuc arxml
        # 2. parse ib arxml
        # 3. parse system arxml
        # 4. parse bswm arxml
        config_base_path = data_management.sys_info_class.config_base_path
        enable_module_list = data_management.sys_info_class.enable_modules
        data_management.autosar_asw_class = ArxmlParseHandler.parse_asw_arxml(config_base_path)
        if data_management.autosar_asw_class is None:
            logger.debug("parse asw.arxml failed")

        data_management.autosar_system_class = ArxmlParseHandler.parse_system_dir_arxml(config_base_path)
        if data_management.autosar_system_class is None:
            return False

        data_management.autosar_bswmd_class = ArxmlParseHandler.parse_all_bswmd_arxml(
            data_management.sys_info_class.plug_in_bswmd_path, enable_module_list, data_management.sys_info_class.target
        )
        if data_management.autosar_bswmd_class is None:
            return False

        data_management.autosar_bsw_class = ArxmlParseHandler.parse_autosar_ecuc_arxml(
            config_base_path, enable_module_list
        )

        if data_management.autosar_bsw_class is None:
            return False

        for instance_name, ecuc_obj in data_management.autosar_bsw_class.items():
            module_obj = ecuc_obj.find(f"/ActiveEcuC/{instance_name}")
            module_name = getattr(getattr(module_obj, "DEFINITION_REF", ""), "valueOf_", "").split("/")[-1]
            if module_name not in data_management.autosar_bswmd_class:
                res = ArxmlParseHandler.parse_all_bswmd_arxml(
                    data_management.sys_info_class.plug_in_bswmd_path,
                    [module_name],
                    data_management.sys_info_class.target,
                )
                data_management.autosar_bswmd_class.update(res)
            bswmd_obj = data_management.autosar_bswmd_class.get(module_name)
            if not bswmd_obj:
                continue
            ecuc_updater = EcucArxmlUpdater(bswmd_obj, ecuc_obj)
            ecuc_updater.update_ecuc_with_default_value()

        data_management.autosar_ib_class = ArxmlParseHandler.parse_internal_behavior_arxml(
            config_base_path, enable_module_list, data_management.sys_target_dict
        )
        if data_management.autosar_ib_class is None:
            return False
        if data_management.sys_info_class.target in data_management.sys_target_dict["validate"]["ignore_option"]:
            data_management.sys_target_dict["validate"]["ignore_option"] = data_management.sys_target_dict["validate"][
                "ignore_option"
            ][data_management.sys_info_class.target]
        data_management.sys_info_class.system_target_info.update(data_management.sys_target_dict)
        # load ignored logs
        from cmd_adaptor.func_logic_layer.validation_func.validate_cmd_func import ValidateCmdFunc

        ValidateCmdFunc.load_ignored_logs_from_file()
        return True

    @classmethod
    def save_project_all_info(cls) -> bool:
        project_path = data_management.sys_info_class.project_path
        # save project configuration
        project_file_parser = ProjectFileParser()
        project_file_parser.update_info_dict(data_management.sys_info_class)
        project_file_parser.save_file(project_path)
        # 1. save ecuc arxml
        # 2. save ib arxml
        # 3. save system arxml
        config_path = data_management.sys_info_class.config_base_path
        module_list = data_management.sys_info_class.enable_modules
        if data_management.sys_info_class.incremental_generation:
            module_list = ArxmlSaveHandler.get_different_modules(
                data_management.sys_info_class.enable_modules,
                data_management.sys_info_class.bsw_ecuc_hash["unchanged_modules"],
            )
            module_list = set(module_list)
        ArxmlSaveHandler.save_bsw_ecuc_arxml(data_management.autosar_bsw_class, config_path, module_list)
        ArxmlSaveHandler.save_internal_behavior_arxml(data_management.autosar_ib_class, config_path, module_list)
        ArxmlSaveHandler.save_system_dir_arxml(data_management.autosar_system_class, config_path)
        ArxmlSaveHandler.save_all_swc_components_arxml(data_management.autosar_asw_class, config_path)
        from cmd_adaptor.func_logic_layer.validation_func.validate_cmd_func import ValidateCmdFunc

        ValidateCmdFunc.save_ignored_logs_to_file()
        ValidateCmdFunc.save_validation_logs_to_file()
        return True

    @classmethod
    def import_asw_save_project(cls) -> bool:
        project_path = data_management.sys_info_class.project_path
        # save project configuration
        project_file_parser = ProjectFileParser()
        project_file_parser.update_info_dict(data_management.sys_info_class)
        project_file_parser.save_file(project_path)
        # 1. save ecuc arxml
        # 2. save ib arxml
        # 3. save system arxml
        config_path = data_management.sys_info_class.config_base_path

        ArxmlSaveHandler.save_system_dir_arxml(data_management.autosar_system_class, config_path)
        ArxmlSaveHandler.save_all_swc_components_arxml(data_management.autosar_asw_class, config_path)

    @classmethod
    def import_dbc_ldf_save_project(cls) -> bool:
        project_path = data_management.sys_info_class.project_path
        # save project configuration
        project_file_parser = ProjectFileParser()
        project_file_parser.update_info_dict(data_management.sys_info_class)
        project_file_parser.save_file(project_path)
        # 1. save ecuc arxml
        # 2. save ib arxml
        # 3. save system arxml
        config_path = data_management.sys_info_class.config_base_path
        module_list = data_management.sys_info_class.enable_modules
        ArxmlSaveHandler.save_bsw_ecuc_arxml(data_management.autosar_bsw_class, config_path, module_list)
        ArxmlSaveHandler.save_system_dir_arxml(data_management.autosar_system_class, config_path)

    @classmethod
    def import_cdd_save_project(cls) -> bool:
        return cls.save_project_all_info()

    @classmethod
    def import_mcal_save_project(cls) -> bool:
        return cls.save_project_all_info()

    @classmethod
    def task_mapping_save_project(cls) -> bool:
        return cls.save_project_all_info()

    @classmethod
    def data_mapping_save_project(cls) -> bool:
        project_path = data_management.sys_info_class.project_path
        # save project configuration
        project_file_parser = ProjectFileParser()
        project_file_parser.update_info_dict(data_management.sys_info_class)
        project_file_parser.save_file(project_path)
        # 1. save ecuc arxml
        # 2. save ib arxml
        # 3. save system arxml
        config_path = data_management.sys_info_class.config_base_path
        ArxmlSaveHandler.save_system_dir_arxml(data_management.autosar_system_class, config_path)
        return True

    @classmethod
    def service_mapping_save_project(cls) -> bool:
        project_path = data_management.sys_info_class.project_path
        # save project configuration
        project_file_parser = ProjectFileParser()
        project_file_parser.update_info_dict(data_management.sys_info_class)
        project_file_parser.save_file(project_path)
        # 1. save ecuc arxml
        # 2. save ib arxml
        # 3. save system arxml
        config_path = data_management.sys_info_class.config_base_path
        ArxmlSaveHandler.save_system_dir_arxml(data_management.autosar_system_class, config_path)
        return True

    @classmethod
    def port_mapping_save_project(cls) -> bool:
        project_path = data_management.sys_info_class.project_path
        # save project configuration
        project_file_parser = ProjectFileParser()
        project_file_parser.update_info_dict(data_management.sys_info_class)
        project_file_parser.save_file(project_path)

        config_path = data_management.sys_info_class.config_base_path
        ArxmlSaveHandler.save_system_dir_arxml(data_management.autosar_system_class, config_path)
        return True

    @classmethod
    def generate_save_project(cls) -> bool:
        return cls.save_project_all_info()

    @classmethod
    def validate_save_project(cls) -> bool:
        return cls.save_project_all_info()
