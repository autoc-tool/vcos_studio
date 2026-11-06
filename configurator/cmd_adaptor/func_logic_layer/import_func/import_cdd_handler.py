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
from cmd_adaptor.func_logic_layer.load_save_project import LoadAndSaveProject
from func_module.import_file.cdd_importer import CddImporter
from cmd_adaptor.cmd_interaction.cmd_logger import logger
from cmd_adaptor.data_management import data_management


class ImportCddHandler:

    def __init__(self) -> None:
        pass

    @classmethod
    def import_cdd(cls, cdd_path):

        cdd_importer = CddImporter(
            data_management.sys_info_class,
            data_management.autosar_bsw_class,
            data_management.autosar_bswmd_class,
            data_management.autosar_ib_class,
            data_management.cfg_info_dict,
            data_management.autosar_system_class,
            data_management.sys_target_dict,
        )
        cdd_importer.pre_import(cdd_path)
        cdd_importer.apply_import(True)
        pass

    def execute_auto_import_cdd(self, cdd_path, project_file_path):
        LoadAndSaveProject.load_project(project_file_path)
        self.import_cdd(cdd_path)
        logger.info("finish execute import cdd ...")
        LoadAndSaveProject.import_cdd_save_project()
