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
from cmd_adaptor.cmd_interaction.cmd_logger import logger
from cmd_adaptor.func_logic_layer.mapping_func.task_mapping_cmd_func import TaskMappingCmdFunc
from cmd_adaptor.func_logic_layer.import_func.import_asw_handler import ImportAswHandler
from cmd_adaptor.func_logic_layer.import_func.import_mcal_handler import ImportMcalHandler
from cmd_adaptor.func_logic_layer.generate_func.generate_cmd_func import GenerateCmdFunc
from cmd_adaptor.func_logic_layer.validation_func.validate_cmd_func import ValidateCmdFunc
from cmd_adaptor.func_logic_layer.upgrade_func.upgrade_cmd_func import UpgradeCmdFunc
from basic_func_module.file_validation.arxml_validator import ArxmlFileValidator
from func_module.module_management.base_config import BASE_CONFIG_PATH

SCHEMA_XSD_FILE = os.path.join(BASE_CONFIG_PATH, "autosar_cfg/AUTOSAR_00046.xsd")


class CmdInteraction:

    def __init__(self, args, argv):
        self.args = args
        self.argv = argv
        self.project_file_path = {}
        self.init_object()

    def init_object(self):
        self.arxml_file_validator = ArxmlFileValidator()
        self.arxml_file_validator.set_arxml_schema(SCHEMA_XSD_FILE)
        pass

    #####################################################################################################
    # Auto Import commands
    ####
    def execute_auto_import_command(self, args):
        # project_file_pat = args.Project
        if hasattr(args, "Project") and args.Project:
            project_file_path = args.Project
        else:
            logger.error("No project file path specified")

        if hasattr(args, "asw") and args.asw:
            asw_dir_list = args.asw
            self.execute_auto_import_asw_command(project_file_path, asw_dir_list)
            pass
        if hasattr(args, "dbc_ldf") and args.node:
            is_add_channel_name = False
            if hasattr(args, "acn"):
                is_add_channel_name = args.acn
            if args.dbc_ldf:
                file_list = args.dbc_ldf.split()
            else:
                file_list = []
            self.execute_auto_import_dbc_ldf_command(project_file_path, file_list, args.node, is_add_channel_name)
        if hasattr(args, "cdd") and args.cdd:
            cdd_path = args.cdd
            self.execute_auto_import_cdd_command([cdd_path], project_file_path)
        if hasattr(args, "mcal") and args.mcal:
            if (
                args.module
            ):  # 支持【--module Can,Fee】， 【--module Can，Fee】， 【--module Can ,Fee】， 【--module】 【】
                need_to_import_mcal_module_list = [s.strip() for s in args.module[0].split(",")]
            else:
                need_to_import_mcal_module_list = None
            mcal_arxml_path = args.mcal
            self.execute_auto_import_mcal_command(project_file_path, mcal_arxml_path, need_to_import_mcal_module_list)
        return True

    def execute_auto_import_dbc_ldf_command(self, project_file_path, file_list, node, is_add_channel_name):
        from cmd_adaptor.func_logic_layer.import_func.import_dbc_and_ldf_handler import ImportDbcLdfHandler

        import_dbc_ldf_func = ImportDbcLdfHandler()
        import_dbc_ldf_func.execute_auto_import_dbc_ldf(
            project_file_path, file_list, node, is_add_channel_name=is_add_channel_name
        )

    def execute_auto_import_asw_command(self, project_file_path, asw_dir_list):
        import_asw_handler = ImportAswHandler()
        import_asw_handler.execute_auto_import_asw(project_file_path, asw_dir_list)

    def execute_auto_import_cdd_command(self, cdd_path, project_file_path):
        from cmd_adaptor.func_logic_layer.import_func.import_cdd_handler import ImportCddHandler

        import_asw_handler = ImportCddHandler()
        import_asw_handler.execute_auto_import_cdd(cdd_path, project_file_path)

    def execute_auto_import_mcal_command(self, project_file_path, mcal_arxml_file_path, selected_mcal_module_list=None):
        import_asw_handler = ImportMcalHandler()
        import_asw_handler.execute_auto_import_mcal_arxml(
            project_file_path, mcal_arxml_file_path, selected_mcal_module_list
        )

    def execute_auto_mapping_command(self, args) -> bool:
        result = False
        if args.Project and args.Mapping == "AutoTaskMappingByFile" and args.File:
            result = self.execute_auto_task_mapping_by_file_command(args.Project, args.File)
            return result
        elif args.Project and args.Mapping == "AutoTaskMappingByParam":
            result = self.execute_auto_task_mapping_by_param_command(
                args.Project, args.TaskName, args.SwcName, args.RunnableName, args.PositionInTask, args.EventName
            )
            return result
        elif args.Project and args.Mapping == "AutoPortMapping":
            result = self.execute_auto_app_port_mapping_command(args)
            return True
        elif args.Project and args.Mapping == "AutoServiceMapping":
            result = self.execute_auto_service_port_mapping_command(args)
            return True
        elif args.Project and args.Mapping == "AutoDataMapping" and (args.component or args.File):
            result = self.execute_auto_data_mapping_command(args)
            return True
        else:
            logger.error("Command error!")
            return False

    def execute_auto_task_mapping_by_param_command(
        self, project_path, task_name, swc_name, runnable_name, position_in_task, runnable_event_name
    ) -> bool:
        result = TaskMappingCmdFunc.execute_auto_task_mapping_by_param(
            project_path, task_name, swc_name, runnable_name, position_in_task, runnable_event_name
        )
        return result

    def execute_auto_app_port_mapping_command(self, args) -> bool:
        from cmd_adaptor.func_logic_layer.mapping_func.port_mapping_cmd_func import PortMappingCmdFunc

        result = PortMappingCmdFunc.execute_auto_app_port_mapping_command(args)
        return result

    def execute_auto_task_mapping_by_file_command(self, project_path, excel_path) -> bool:
        result = TaskMappingCmdFunc.execute_auto_task_mapping_by_file(project_path, excel_path)
        return result

    def execute_auto_service_port_mapping_command(self, args) -> bool:
        from cmd_adaptor.func_logic_layer.mapping_func.service_mapping_cmd_func import ServiceMappingCmdFunc

        result = ServiceMappingCmdFunc.execute_auto_service_port_mapping_command(args)
        return result

    def execute_auto_data_mapping_command(self, args) -> bool:
        from cmd_adaptor.func_logic_layer.mapping_func.data_mapping_cmd_func import DataMappingCmdFunc

        result = DataMappingCmdFunc.execute_auto_data_mapping_command(args)
        return result

    def execute_validation_command(self, project_path, module_list=[]) -> bool:
        result = False
        if project_path:
            module_list = self.handle_cmd_input_modules(module_list)
            result = ValidateCmdFunc.execute_auto_validation(project_path, module_list)
        return result

    def execute_generate_command(
        self, project_path, module_list, is_debug: bool = False, forced_codegen: bool = True, sim_mode: bool = False
    ) -> bool:
        result = False

        if project_path:
            module_list = self.handle_cmd_input_modules(module_list)
            result = GenerateCmdFunc.execute_auto_generate_c_code(project_path, module_list, is_debug, forced_codegen, sim_mode)

        if not result:
            logger.debug(f"generate c code failed {result}")
        else:
            logger.debug(f"generate c code success {result}")
        return result

    def execute_swc_generate_command(self, project_path, selected_swcs) -> bool:
        result = False
        if project_path:
            result = GenerateCmdFunc.execute_auto_generate_swc_template(project_path, selected_swcs)
        return result

    def execute_upgrade_command(self, project_path) -> bool:
        result = False

        if not os.path.exists(os.path.abspath(project_path)):
            logger.error(f"{project_path} not exist")
            return False

        logger.info(f"upgrade {project_path} project")

        result = UpgradeCmdFunc.execute_auto_upgrade_command(project_path)

        return result

    @classmethod
    def handle_cmd_input_modules(cls, module_list):
        handled_module_list = []
        if not module_list:
            return handled_module_list
        if isinstance(module_list, str):
            if "," in module_list:
                handled_module_list = module_list.split(",")
            elif " " in module_list:
                handled_module_list = module_list.split(" ")
            else:
                handled_module_list = [module_list]
        elif isinstance(module_list, list) and ("," in module_list[0] or " " in module_list[0]):
            module_list = module_list[0]
            if "," in module_list:
                handled_module_list = module_list.split(",")
            elif " " in module_list:
                handled_module_list = module_list.split(" ")
            else:
                handled_module_list = [module_list]
        elif isinstance(module_list, list):
            handled_module_list = module_list

        handled_module_list = [x.replace(" ", "") for x in handled_module_list]
        return handled_module_list
