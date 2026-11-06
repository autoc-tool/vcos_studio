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
from typing import Union, Tuple
from cmd_adaptor.func_logic_layer.load_save_project import LoadAndSaveProject
from cmd_adaptor.func_logic_layer.import_func.import_asw_handler import ImportAswHandler
from cmd_adaptor.func_logic_layer.mapping_func.task_mapping_cmd_func import TaskMappingCmdFunc
from cmd_adaptor.func_logic_layer.generate_func.generate_cmd_func import GenerateCmdFunc
from cmd_adaptor.func_logic_layer.validation_func.validate_cmd_func import ValidateCmdFunc
from cmd_adaptor.func_logic_layer.export_func.export_file_func import ExportFileFunc
from cmd_adaptor.func_logic_layer.bsw_func.os_cmd_func import OsCmdFunc
from cmd_adaptor.func_logic_layer.os_cfg_cmd_func import OsConfigureCmdFunc
from cmd_adaptor.func_logic_layer.mapping_func.data_mapping_cmd_func import DataMappingCmdFunc
from cmd_adaptor.func_logic_layer.mapping_func.port_mapping_cmd_func import PortMappingCmdFunc
from cmd_adaptor.func_logic_layer.mapping_func.service_mapping_cmd_func import ServiceMappingCmdFunc
from cmd_adaptor.func_logic_layer.mapping_func.schedule_table_mapping_cmd_func import ScheduleTableCmdFunc
from cmd_adaptor.cmd_interaction.cmd_logger import logger


class AutoCliApi:

    class Args:
        def __setattr__(self, name: str, value):
            self.__dict__[name] = value

        def __getattr__(self, name: str):
            return self.__dict__[name]

    @classmethod
    def load_project(cls, project_file_path) -> bool:
        """load the vcos project by project file path, include all kinds of arxml and logs.

        Args:
            project_file_path (str): the .vcosproject file path.

        Returns:
            bool: True(load sucessfully), False:(load failed).
        """
        if not os.path.exists(project_file_path) or ".vcosproject" not in project_file_path:
            logger.error(f"project file path {project_file_path} format error")
            return False
        return LoadAndSaveProject.load_project(project_file_path)

    @classmethod
    def save_project(cls) -> bool:
        """save the project into arxml and logs.

        Returns:
            bool: True(save sucessfully), False:(save failed).
        """
        return LoadAndSaveProject.save_project_all_info()

    @classmethod
    def import_asw(cls, asw_dir: str) -> bool:
        """import the asw files according to the directory path.

        Args:
            asw_dir (str): the directory which store the asw arxmls.

        Returns:
            bool: True(import sucessfully), False:(import failed).
        """
        if not os.path.exists(asw_dir):
            logger.error(f"asw dir {asw_dir} not exists")
            return False
        return ImportAswHandler.import_asw(asw_dir)

    @classmethod
    def import_cdd(cls, cdd_path_list: list) -> bool:
        """import the cdd file according to the file path.

        Args:
            cdd_path_list (list): the list of cdd path.

        Returns:
            bool: True(import sucessfully), False:(import failed).
        """
        try:
            for i in range(len(cdd_path_list)):
                file_path = os.path.abspath(cdd_path_list[i])
                cdd_path_list[i] = file_path
                if not os.path.exists(file_path):
                    logger.error(f"cdd file path {file_path} not exsit")
                    return False
            from cmd_adaptor.func_logic_layer.import_func.import_cdd_handler import ImportCddHandler

            ImportCddHandler.import_cdd(cdd_path_list)
        except Exception:
            logger.exception("Import dbc/ldf Failed")
            return False
        return True

    @classmethod
    def import_dbc_ldf(cls, file_path_list: list, ecu_instance, is_add_channel_name=False) -> bool:
        """import the dbc according to the list of dbc info.

        Args:
            file_path_list (list): the list of dbc or ldf file path.

            ecu_instance (str): ecu instance.

        Returns:
            bool: True(import sucessfully), False:(import failed)
        """
        try:
            for i in range(len(file_path_list)):
                file_path = os.path.abspath(file_path_list[i])
                file_path_list[i] = file_path
                if not os.path.exists(file_path):
                    logger.error(f"dbc or ldf file path {file_path} not exsit")
                    return False
            from cmd_adaptor.func_logic_layer.import_func.import_dbc_and_ldf_handler import ImportDbcLdfHandler

            ImportDbcLdfHandler.import_dbc_ldf(file_path_list, ecu_instance, is_add_channel_name=is_add_channel_name)
        except Exception:
            logger.exception("Import dbc/ldf Failed")
            return False
        return True

    @classmethod
    def import_mcal(cls, mcal_path: str, mcal_module_list: list) -> bool:
        """import the mcal file path according to the mcal path.

        Args:
            mcal_path (str): the mcal file path.
            mcal_module_list (list): the MCAL modules that need to be imported

        Returns:
            bool: True(import sucessfully), False:(import failed).
        """
        if not isinstance(mcal_path, str) or not os.path.isfile(mcal_path):
            logger.error("mcal path is invalid, please check mcal path what you config!")
            return False
        if not mcal_module_list or not isinstance(mcal_module_list, list):
            logger.error("mcal module list is invalid, please check mcal module list what you want import")
            return False
        try:
            from cmd_adaptor.func_logic_layer.import_func.import_mcal_handler import ImportMcalHandler

            ImportMcalHandler.import_mcal_arxml(mcal_path, mcal_module_list)
        except Exception:
            return False
        return True

    @classmethod
    def excute_task_mapping(cls, task_mapping_info_list: list) -> bool:
        """excute the task mapping by the list of task mapping info

        Args:
            task_mapping_info_list (list): the list of task_mapping_info
            (the dict of containing the below task mapping params).
                task_name (str): the task name which to be mapped.
                swc_name (str): the swc name which the runnable belongs to.
                runnable_name (str): the runnable or main function name.
                position (int): the target position of task, (-1:default to the last unused position,
                                > 0: the target position).
                event_name (str): If the runnable_name has multiple different runnables,
                                this parameter must be specified.

        Returns:
            bool: True(excute sucessfully), False:(excute failed)

        Note:
            only support Application Components
        """
        for task_mapping_info in task_mapping_info_list:
            task_name = task_mapping_info.get("task_name")
            swc_name = task_mapping_info.get("swc_name")
            runnable_name = task_mapping_info.get("runnable_name")
            position = task_mapping_info.get("position")
            event_name = task_mapping_info.get("event_name", "")
            result = TaskMappingCmdFunc.auto_task_mapping_by_param(
                task_name, swc_name, runnable_name, position, event_name
            )
            if not result:
                return False

        return True

    @classmethod
    def excute_task_mapping_by_file(cls, excel_file: str) -> bool:
        """excute the task mapping by the input excel file

        Args:
            excel_file (str): excel path

        Returns:
            bool: True(excute sucessfully), False:(excute failed)
        """
        if not os.path.exists(excel_file):
            logger.error(f"excel file {excel_file} not exists")
            return False
        return TaskMappingCmdFunc.auto_task_mapping_by_file(excel_file)

    @classmethod
    def excute_data_mapping(cls, data_mapping_info_list: list) -> bool:
        """excute the data mapping by the list of data mapping info

        Args:
            data_mapping_info_list (list): the list of data_mapping_info (the dict of containing
                                            the below data mapping params).

                component (str): the component string (format eg: SWC1,SWC2,SWC3).

                direction (str): the direction (Rx, Tx).

                prefix (str): optional param, the prefix word to filter.

                postfix (str): optional param, the postfix word to filter.

                ignore_match_whole_word (bool): optional param, ignore match the whole word or not.

                ignore_match_case (bool): optional param,  ignore match case or not.

                log_save (bool): optional param, save the log or not.
                match_compatibility (bool): optional param, match compatibility of data type size.
                file (str): optional param, excel file path, auto data mapping by excel file if set.

        Returns:
            bool: True(excute sucessfully), False:(excute failed)
        """
        for data_mapping_info in data_mapping_info_list:
            args = cls.Args()
            if not data_mapping_info.get("file", None):
                if "component" not in data_mapping_info:
                    logger.error("data_mapping_info should contain component")
                    return False
                if "direction" not in data_mapping_info:
                    logger.error("data_mapping_info should contain direction")
                    return False
                args.component = data_mapping_info.get("component")
                args.direction = data_mapping_info.get("direction")
                if not args.component or not args.direction:
                    logger.error("component and direction should not be empty")
                    return False
            args.component = data_mapping_info.get("component", [])
            args.direction = data_mapping_info.get("direction", None)
            args.prefix = data_mapping_info.get("prefix", "")
            args.postfix = data_mapping_info.get("postfix", "")
            args.ignore_match_whole_word = data_mapping_info.get("ignore_match_whole_word", False)
            args.ignore_match_case = data_mapping_info.get("ignore_match_case", False)
            args.allow_multi_signal = data_mapping_info.get("allow_multi_signal", False)
            args.log_save = data_mapping_info.get("log_save", False)
            args.match_compatibility = data_mapping_info.get("match_compatibility", False)
            args.File = data_mapping_info.get("file", None)
            DataMappingCmdFunc.auto_data_mapping(args)
        return True

    @classmethod
    def excute_data_mapping_all_logs_save(cls) -> bool:
        """Save DataMapping all logs to a excel file.
           Called after function excute_data_mapping().

        Returns:
            bool: True(excute sucessfully), False:(excute failed)
        """
        DataMappingCmdFunc.auto_data_mapping_all_logs_save()
        return True

    @classmethod
    def excute_port_mapping(cls, port_mapping_info_list: list) -> bool:
        """excute the port mapping by the list of port mapping info

        Args:
            port_mapping_info_list (list): the list of port_mapping_info(the dict of containing
                                            the below port mapping params).

                component (str): optional param, the component to excute.

                direction (str): optional param, the direction (Rx, Tx).

                prefix (str): optional param, the prefix word to filter.

                postfix (str): optional param, the postfix word to filter.

                allow_split (bool): optional param, whether allow split or not.

                allow_merge (bool): optional param, whether allow merge or not.

                ignore_match_case (bool): optional param, ignore match case or not.

                ignore_match_whole_word (bool): optional param, ignore match the whole word or not.

        Returns:
            bool: True(excute sucessfully), False:(excute failed)
        """
        for port_mapping_info in port_mapping_info_list:
            args = cls.Args()
            args.component = port_mapping_info.get("component", "")
            args.direction = port_mapping_info.get("direction", "Tx")
            args.prefix = port_mapping_info.get("prefix", "")
            args.postfix = port_mapping_info.get("postfix", "")
            args.allow_split = port_mapping_info.get("allow_split", False)
            args.allow_merge = port_mapping_info.get("allow_merge", False)
            args.ignore_match_whole_word = port_mapping_info.get("ignore_match_whole_word", False)
            args.ignore_match_case = port_mapping_info.get("ignore_match_case", False)
            args.Mapping = "AutoPortMapping"
            args.log_save = port_mapping_info.get("log_save", False)
            args.match_compatibility = port_mapping_info.get("match_compatibility", False)
            PortMappingCmdFunc.app_port_mapping(args)

        return True

    @classmethod
    def excute_service_mapping(cls, service_mapping_info_list: list) -> bool:
        """excute the service mapping by the list of service mapping info

        Args:
            service_mapping_info_list (list): the list of service_mapping_info(the dict of containing
                                            the below service mapping params).

                component (str): optional param, the component to excute.

                direction (str): optional param, the direction (Rx, Tx).

                prefix (str): optional param, the prefix word to filter.

                postfix (str): optional param, the postfix word to filter.

                allow_split (bool): optional param, whether allow split or not.

                allow_merge (bool): optional param, whether allow merge or not.

                ignore_match_case (bool): optional param, ignore match case or not.

                ignore_match_whole_word (bool): optional param, ignore match the whole word or not.

        Returns:
            bool: True(excute sucessfully), False:(excute failed)
        """

        for service_mapping_info in service_mapping_info_list:
            args = cls.Args()
            args.component = service_mapping_info.get("component", "")
            args.direction = service_mapping_info.get("direction", "Tx")
            args.prefix = service_mapping_info.get("prefix", "")
            args.postfix = service_mapping_info.get("postfix", "")
            args.allow_split = service_mapping_info.get("allow_split", False)
            args.allow_merge = service_mapping_info.get("allow_merge", False)
            args.ignore_match_whole_word = service_mapping_info.get("ignore_match_whole_word", False)
            args.ignore_match_case = service_mapping_info.get("ignore_match_case", False)
            args.Mapping = "AutoServiceMapping"
            args.log_save = service_mapping_info.get("log_save", False)
            args.match_compatibility = service_mapping_info.get("match_compatibility", False)
            ServiceMappingCmdFunc.service_port_mapping(args)

        return True

    @classmethod
    def excute_validation(cls, validation_module_list: list, validation_level: str) -> Union[bool, Tuple[dict, dict]]:
        """excute the validation by the list of module and validation level.

        Args:
            validation_module_list (list): the list of the module needed to be validated.

            validation_level (str): "no limit"(only ouput the important rules),
                                    "error"(output the important rules and error result),
                                    "warnning"(output the important rules、error and warning result).

        Returns:
            validation_dict: the validation result dict, key:module_name, value:True/False.
            validation_logs: Detailed error and warning validation items.
        """
        if validation_level and validation_level not in ["no limit", "error", "warnning"]:
            logger.error(f"validation_level {validation_level} value error")
            return False
        validation_dict, validation_logs = ValidateCmdFunc.validate_modules_with_result(
            validation_module_list, validation_level
        )
        return validation_dict, validation_logs

    @classmethod
    def excute_generation(
        cls, generation_module_list: list, is_debug: bool = False, forced_codegen: bool = True
    ) -> bool:
        """excute the generation by the list of module.

        Args:
            generation_module_list (list): the list of the module needed to be generated.

            is_debug (bool) : optional param, generate mode(debug or release), default value(release)

            forced_codegen (bool) : optional param, all-generate or add-generate mode, default value(all-generate mode)

        Returns:
            dict: the generation result dict, key:module_name, value:True/False.
        """
        result = GenerateCmdFunc.execute_auto_generate(generation_module_list, is_debug, forced_codegen)
        return result

    @classmethod
    def export_task_mapping(cls, file_path) -> bool:
        """export the task mapping result into one excel file.

        Returns:
            bool: True(excute sucessfully), False:(excute failed).
        """

        return ExportFileFunc.export_task_mapping_info_to_excel(file_path)

    @classmethod
    def add_spinlock(cls, spinlock_info: dict) -> bool:
        """add/update a spinlock by spinlock_info

        Args:
            spinlock_info (dict): the dict of containing the below spinlock params.

                spinlock_id (str): the unique name of a spinlock

                spinlock_method (str): the method should in (LOCK_ALL_INTERRUPTS/LOCK_CAT2_INTERRUPTS/LOCK_NOTHING)

                app_name_list (str): the param for OsSpinlockAccessingApplication,
                                    and the app name should be unique and the count should >= 2

        Returns:
            bool: True(excute sucessfully), False:(excute failed)
        """
        if "spinlock_id" not in spinlock_info:
            logger.error("spinlock_info should contain spinlock_id")
            return False
        if "spinlock_method" not in spinlock_info:
            logger.error("spinlock_info should contain spinlock_method")
            return False
        if "app_name_list" not in spinlock_info:
            logger.error("spinlock_info should contain app_name_list")
            return False
        return OsCmdFunc.add_spinlock(spinlock_info)

    @classmethod
    def remove_spinlock(cls, spinlock_id: str) -> bool:
        """remove a spinlock by spinlock_id

        Args:
            spinlock_id (str): the unique name of a spinlock

        Returns:
            bool: True(excute sucessfully), False:(excute failed)
        """
        if not spinlock_id:
            logger.error("spinlock_id is empty")
            return False
        return OsCmdFunc.remove_spinlock(spinlock_id)

    @classmethod
    def import_os_cfg(cls, file_name: str) -> bool:
        """在指定工程中导入OS自动配置
        Args:
            file_name(str): name of file to import
        Returns:
            bool: True(import sucessfully), False:(import failed)
        """
        if not os.path.exists(file_name):
            logger.error(f"os cfg file {file_name} not exists")
            return False
        return OsConfigureCmdFunc.import_os_cfg(file_name)

    @classmethod
    def export_os_cfg(cls, file_name: str) -> bool:
        """导出指定工程现有OS配置
        Args:
            file_name(str): name of file to export
        Returns:
            bool: True(export sucessfully), False:(export failed)
        """
        return OsConfigureCmdFunc.export_os_cfg(file_name)

    @classmethod
    def generate_all_schedule_table(cls):
        """
        生成所有的调度表配置
        Returns:
            bool: True(generate sucessfully), False:(generate failed)
        """
        res = ScheduleTableCmdFunc.generate_schedule_table_cfg()
        if not res:
            logger.error("generate schedule table cfg failed")
            return False
        task_mapping_instance = TaskMappingCmdFunc.get_task_mapping_instance()
        task_mapping_instance.update_schedule_table_info()
        logger.info("generate schedule table cfg success")
        return True
