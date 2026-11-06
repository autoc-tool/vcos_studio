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
from cmd_adaptor.data_management import data_management
from cmd_adaptor.cmd_interaction.cmd_logger import logger
from func_module.project_management.version_management.upgrade import UpgradeCli
from func_module.project_management.version_management.vcos_version import get_vcos_version_info
from func_module.project_management.sys_info_class import SysInfoClass
from func_module.project_management.project_file_parser import ProjectFileParser
from cmd_adaptor.func_logic_layer.load_save_project import LoadAndSaveProject


class UpgradeCmdFunc:

    @classmethod
    def init_obj(cls):
        """Initialize objs for supportting to upgrade modules"""
        cls.project_file_parser = ProjectFileParser()
        cls.sys_info_obj = SysInfoClass()

    @classmethod
    def parse_and_load_prj(cls, prj_path):
        """Parse project file for checking whether upgrade or not"""
        cls.init_obj()
        result = LoadAndSaveProject.load_project(prj_path)
        return result

    @classmethod
    def update_prj(cls, prj_path):
        """Save project file for updating parameters in project file"""
        cls.project_file_parser.update_info_dict(data_management.sys_info_class)
        cls.project_file_parser.save_file(prj_path)

    @classmethod
    def execute_auto_upgrade_command(cls, prj_path):
        """function for upgrade action with command"""
        ret = False

        logger.info("start parsing and loading vcos project ...")
        ret = cls.parse_and_load_prj(prj_path)
        if ret is False:
            logger.error("Failed to load project file, please check project file")
            return False

        logger.info("start checking whether upgrade or not ...")
        vcos_info = get_vcos_version_info()
        upgrade_obj = UpgradeCli(vcos_info.studio_version, vcos_info.system_version)
        result = upgrade_obj.auto_cli_upgrade(data_management.sys_info_class, type=True)

        # with modules to upgrade
        if result:
            logger.info("start executing upgrade action ...")
            ret, bsw_ecuc_autosar_dict, mode_autosar_dict, ib_autosar_dict = upgrade_obj.vcos_version_upgrade(
                data_management
            )
            if ret is True:
                data_management.autosar_bsw_class = bsw_ecuc_autosar_dict
                data_management.autosar_bswmd_class = mode_autosar_dict
                data_management.autosar_ib_class = ib_autosar_dict

                logger.info("start saving arxml ...")
                ret = LoadAndSaveProject.generate_save_project()
                logger.info("finish saving arxml ...")
                return True
            else:
                # with errors while executing update
                ret = False
                modules: str = "[ "
                for module, _ in upgrade_obj.version_module_list.items():
                    modules += str(module) + " "
                modules += "]"
                logger.warning(f"Upgrade is not completed, please check module list: {modules}")
                return False

        # no modules to upgrade
        else:
            cls.update_prj(prj_path)
            logger.info("No module need to upgrade, action of upgrade completed")
            ret = True

        return ret
