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
from typing import List
from basic_func_module.base_logger import logger
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.autosar_utils.autosar_utils import AutosarUtils
from basic_func_module.autosar_utils.utils import get_short_name, get_definition_ref
from basic_func_module.file_handler.excel_parser.import_dbc_or_ldf_excel_parser import ImportDBCOrLDFExcelParser
from basic_func_module.file_handler.excel_parser.import_canif_excel_parser import ImportCanIfExcelParser
from func_module.import_file.dbc_importer import DbcImporter
from func_module.import_file.ldf_importer import LdfImporter
from func_module.import_file.cdd_importer import CddImporter
from func_module.import_file.excel_importer import ExcelImporter
from func_module.import_file.sidl_sdepl_importer import SidlSdeplImporter
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlParseHandler
from func_module.project_management.sys_info_class import SysInfoClass
from func_module.module_management.arxml_handler.mcal_ecuc.import_ecuc_cfg import EcucCfgImport
from func_module.module_management.arxml_handler.system.system_arxmls_manager import SystemArxmlsManager
from func_module.health_monitor import perf_record
from ui_adaptor.data_management import data_management as data


class ImportFilesLogic:

    def __init__(self) -> None:
        self.dbc_importer = None
        self.ldf_importer = None
        self.cdd_importer = None

    def get_imported_excel(self):
        imported_excel_list = []
        imported_excel_list.extend(self.get_imported_com_excel())
        return imported_excel_list

    def get_imported_com_excel(self):
        sys_info_obj: SysInfoClass = data.sys_info_class
        imported_list = []
        for path in sys_info_obj.excel.values():
            imported_list.append(path)

        return imported_list

    def get_imported_diag_excel(self):
        imported_excel_lsit = []
        sys_info_obj: SysInfoClass = data.sys_info_class
        cdd_info = sys_info_obj.cdd
        for path in cdd_info.get("excel", {}).values():
            imported_excel_lsit.append(path)

        return imported_excel_lsit

    def get_dbc_ldf_content(self, file_path_list):
        file_info_dict = {}
        for file_path in file_path_list:
            file_name: str = os.path.basename(file_path)
            if file_name.endswith(".dbc") and file_path in self.dbc_importer.pre_import_dict:
                file_info_dict[file_path] = self.dbc_importer.get_file_content(file_path)
            elif file_name.endswith(".ldf") and file_path in self.ldf_importer.pre_import_dict:
                file_info_dict[file_path] = self.ldf_importer.get_file_content(file_path)
            else:
                logger.ui_error(f"Invalid file fromat of {file_path}. Support *.dbc *.ldf only")
        return file_info_dict

    def init_import_files_ui(self, progress_signal):
        progress_signal.emit("Initing import UI")
        imported_file_dict = {}
        self.dbc_importer = DbcImporter(
            data.sys_info_class,
            data.autosar_bsw_class,
            data.autosar_bswmd_class,
            data.autosar_ib_class,
            data.autosar_system_class,
            data.cfg_info_dict,
            data.sys_target_dict,
        )
        self.ldf_importer = LdfImporter(
            data.sys_info_class,
            data.autosar_bsw_class,
            data.autosar_bswmd_class,
            data.autosar_ib_class,
            data.autosar_system_class,
            data.cfg_info_dict,
            data.sys_target_dict,
        )
        self.cdd_importer = CddImporter(
            data.sys_info_class,
            data.autosar_bsw_class,
            data.autosar_bswmd_class,
            data.autosar_ib_class,
            data.cfg_info_dict,
            data.autosar_system_class,
            data.sys_target_dict,
        )
        imported_dbc = self.dbc_importer.get_pre_import_meta_info()
        imported_ldf = self.ldf_importer.get_pre_import_meta_info()
        imported_cdd = self.cdd_importer.get_pre_import_meta_info()
        imported_file_dict.update(imported_dbc)
        imported_file_dict.update(imported_ldf)
        imported_file_dict.update(imported_cdd)

        return imported_file_dict

    def import_dbc(self, file_list, progress_signal):
        imported_file_dict = {}
        progress_signal.emit("Parsing dbc files")
        pre_imported_dbc = self.dbc_importer.pre_import(file_list)
        pre_imported_ldf = self.ldf_importer.get_pre_import_meta_info()

        imported_file_dict.update(pre_imported_dbc)
        imported_file_dict.update(pre_imported_ldf)

        return imported_file_dict

    def import_files(self, file_list: dict, progress_signal):
        import_files_dict: dict = {}
        pre_imported_dbc: dict = {}
        pre_imported_ldf: dict = {}
        pre_imported_cdd: dict = {}
        progress_signal.emit("Parsing imported files")
        pre_imported_dbc = self.dbc_importer.pre_import(file_list["dbc"])
        pre_imported_ldf = self.ldf_importer.pre_import(file_list["ldf"])
        pre_imported_cdd = self.cdd_importer.pre_import(file_list["cdd"])
        import_files_dict.update(pre_imported_dbc)
        import_files_dict.update(pre_imported_ldf)
        import_files_dict.update(pre_imported_cdd)
        return import_files_dict

    def replace_files(self, file_info_dict: dict, progress_signal):
        progress_signal.emit("Parsing imported files")
        old_file_path = file_info_dict["old_file_path"]
        new_file_path = file_info_dict["new_file_path"]
        if file_info_dict["file_type"] == "dbc":
            meta_info_dict = self.dbc_importer.replace_pre_import(old_file_path, new_file_path)
        elif file_info_dict["file_type"] == "ldf":
            meta_info_dict = self.ldf_importer.replace_pre_import(old_file_path, new_file_path)
        elif file_info_dict["file_type"] == "cdd":
            meta_info_dict = self.cdd_importer.replace_pre_import(old_file_path, new_file_path)
        return meta_info_dict

    def node_selected_changed(self, file_path: str, selected_node):
        print(file_path, selected_node)
        if file_path.endswith(".dbc"):
            self.dbc_importer.set_selected_node(file_path, selected_node)
        if file_path.endswith(".ldf"):
            self.ldf_importer.set_selected_node(file_path, selected_node)

    def import_ldf(self, file_list, progress_signal):
        imported_file_dict = {}
        progress_signal.emit("Parsing ldf files")
        pre_imported_dbc = self.dbc_importer.get_pre_import_meta_info()
        pre_imported_ldf = self.ldf_importer.pre_import(file_list)

        imported_file_dict.update(pre_imported_dbc)
        imported_file_dict.update(pre_imported_ldf)

        return imported_file_dict

    def reload_mcal_arxml(self):
        if data.cfg_info_dict["eb"]:
            return
        file_path = data.sys_info_class.eb_arxml
        if os.path.isfile(file_path):
            mcal_arxml = ArxmlParseHandler.parse_mcal_arxml(file_path)
            if len(mcal_arxml.AR_PACKAGES.AR_PACKAGE) < 10:
                return
            mcal_arxml_dict = AutosarUtil.to_bsw_dict(mcal_arxml)
            data.cfg_info_dict["eb"] = {"arxml": mcal_arxml_dict}

    def reload_dbc(
        self,
    ):
        if data.cfg_info_dict["dbc"] is not None and len(data.cfg_info_dict["dbc"]):
            return None

        # 添加dbc/ldf信息到cfg_info_dict
        dbc_importer = DbcImporter(
            data.sys_info_class,
            data.autosar_bsw_class,
            data.autosar_bswmd_class,
            data.autosar_ib_class,
            data.autosar_system_class,
            data.cfg_info_dict,
            data.sys_target_dict,
        )
        dbc_importer.final_parse()
        ldf_importer = LdfImporter(
            data.sys_info_class,
            data.autosar_bsw_class,
            data.autosar_bswmd_class,
            data.autosar_ib_class,
            data.autosar_system_class,
            data.cfg_info_dict,
            data.sys_target_dict,
        )
        ldf_importer.final_parse()

    def check_before_apply(self, progress_signal):
        res = True
        error_message_list = []

        progress_signal.emit("Validating dbc file")
        error_log: dict[str, list] = self.dbc_importer.validate_all()
        for file_path, _ in error_log.items():
            res = False
            error_message_list.append(f"Invalid dbc! {os.path.basename(file_path)}")

        progress_signal.emit("Validating ldf file")
        error_log: dict[str, list] = self.ldf_importer.validate_all()
        for file_path, _ in error_log.items():
            res = False
            error_message_list.append(f"Invalid ldf! {os.path.basename(file_path)}")

        progress_signal.emit("Checking ldf channel name")
        check_res, path, channel_name = self.ldf_importer.check_channel_name()
        if not check_res:
            res = False
            error_message_list.append(f"Duplicate channel name {channel_name} of {path}")

        return res, error_message_list

    def parse_excel_files(self, excel_list):
        excel_importer = ExcelImporter()
        excel_contents: dict = excel_importer.parse_excel(excel_list)

        excel_files_path = {}
        if excel_contents:
            data.cfg_info_dict.pop("excel", None)
            data.cfg_info_dict.update({"excel": excel_contents})

        for excel_path in excel_list:
            excel_name = os.path.basename(excel_path)
            # Record excel which has been successfully parsed
            if excel_name in excel_contents:
                excel_files_path.update({excel_name: excel_path})
        sys_info_obj: SysInfoClass = data.sys_info_class
        sys_info_obj.excel = excel_files_path

    @perf_record.log_function_stats(["BSW Editor", "配置文件解析和导入", "确认导入文件"])
    def apply_import(self, excel_list, merge_signal_flag, is_add_channel_name, progress_signal):
        progress_signal.emit("Applying files import")

        # Parse excel first, for module updater need excel info when updating module config
        self.parse_excel_files(excel_list)

        # Apply file importing action
        self.dbc_importer.apply_import()
        self.ldf_importer.apply_import()
        self.cdd_importer.apply_import(merge_signal_flag)
        data.sys_info_class.is_add_channel_name = is_add_channel_name

        system_arxml_manager = SystemArxmlsManager(data.autosar_bswmd_class)
        system_arxml_manager.update_com_stack_arxml_from_dbc_ldf(
            data.cfg_info_dict,
            data.autosar_bsw_class,
            data.autosar_system_class,
            "dbc_or_ldf",
            is_add_channel_name=is_add_channel_name,
        )
        return data.autosar_bswmd_class, data.autosar_bsw_class

    def apply_cdd_signal(self):
        sys_info_obj: SysInfoClass = data.sys_info_class
        cdd: dict = sys_info_obj.cdd
        single_signal: bool = cdd.get("single_signal", False)
        return single_signal if single_signal else False

    def get_is_add_channel_name(self):
        sys_info_obj: SysInfoClass = data.sys_info_class
        return sys_info_obj.is_add_channel_name

    def apply_dbc_ldf_import(self, excel_list, progress_signal):
        progress_signal.emit("Applying dbc/ldf files import")
        self.parse_com_excel(excel_list)
        self.dbc_importer.apply_import()
        self.ldf_importer.apply_import()

        # TODO:fyf 3. 使用解析结果更新模块
        system_arxml_manager = SystemArxmlsManager(data.autosar_bswmd_class)
        system_arxml_manager.update_com_stack_arxml_from_dbc_ldf(
            data.cfg_info_dict, data.autosar_bsw_class, data.autosar_system_class, "dbc_or_ldf"
        )

        return data.autosar_bswmd_class, data.autosar_bsw_class

    def remove_files(self, file_list: "list[str]"):
        dbc_file_list = []
        ldf_file_list = []
        cdd_file_list = []
        excel_file_list = []
        for file_path in file_list:
            if file_path.endswith(".dbc"):
                dbc_file_list.append(file_path)
            if file_path.endswith(".ldf"):
                ldf_file_list.append(file_path)
            if file_path.endswith(".cdd"):
                cdd_file_list.append(file_path)
            if file_path.endswith(".xlsx"):
                excel_file_list.append(file_path)

        self.dbc_importer.de_pre_import(dbc_file_list)
        self.ldf_importer.de_pre_import(ldf_file_list)
        self.cdd_importer.de_pre_import(cdd_file_list)

        meta_info_dict = {}
        dbc_meta_info_dict = self.dbc_importer.get_pre_import_meta_info()
        ldf_meta_info_dict = self.ldf_importer.get_pre_import_meta_info()
        cdd_meta_info_dict = self.cdd_importer.get_pre_import_meta_info()

        meta_info_dict.update(dbc_meta_info_dict)
        meta_info_dict.update(ldf_meta_info_dict)
        meta_info_dict.update(cdd_meta_info_dict)

        return meta_info_dict

    def parse_com_excel(self, excel_file_list):
        import_dbc_or_ldf_excel_parser = ImportDBCOrLDFExcelParser()
        result = import_dbc_or_ldf_excel_parser.execute_import_excel_command(excel_file_list)
        excel_files_path = {}
        if result:
            excel_info_dict = data.cfg_info_dict.get("excel", None)
            if excel_info_dict:
                excel_info_dict.update(result)
            else:
                data.cfg_info_dict.update({"excel": result})

            for excel_path in excel_file_list:
                excel_name = os.path.basename(excel_path)
                excel_files_path.update({excel_name: excel_path})
        sys_info_obj: SysInfoClass = data.sys_info_class
        sys_info_obj.excel = excel_files_path

    def parse_diag_excel(self, diag_excel_list):
        import_cdd_excel_parser = ImportCDDExcelParser()
        result = import_cdd_excel_parser.execute_import_excel_command(diag_excel_list)
        if result:
            excel_info_dict = data.cfg_info_dict.get("excel", None)
            if excel_info_dict:
                excel_info_dict.update(result)
            else:
                data.cfg_info_dict.update({"excel": result})
        sys_info_obj: SysInfoClass = data.sys_info_class
        cdd_info: dict = sys_info_obj.cdd
        cdd_info.pop("excel", None)
        for excel in diag_excel_list:
            excel_name = os.path.basename(excel)
            cdd_info.update({"excel": {excel_name: excel}})
        sys_info_obj.cdd = cdd_info

    def parse_canif_excel(self, diag_excel_list):
        import_cdd_excel_parser = ImportCanIfExcelParser()
        result = import_cdd_excel_parser.execute_import_excel_command(diag_excel_list)
        excel_files_path = {}
        if result:
            excel_info_dict = data.cfg_info_dict.get("excel", None)
            if excel_info_dict:
                excel_info_dict.update(result)
            else:
                data.cfg_info_dict.update({"excel": result})

            for excel_path in diag_excel_list:
                excel_name = os.path.basename(excel_path)
                excel_files_path.update({excel_name: excel_path})

        sys_info_obj: SysInfoClass = data.sys_info_class
        cdd_info: dict = sys_info_obj.cdd
        excel = sys_info_obj.excel
        excel.update(excel_files_path)
        sys_info_obj.excel = excel
        sys_info_obj.cdd = cdd_info

    def deinit_import_dbc_ldf_ui(self):
        self.dbc_importer = None
        self.dbc_importer = None

    def init_import_cdd_ui(self):
        self.cdd_importer = CddImporter(
            data.sys_info_class,
            data.autosar_bsw_class,
            data.autosar_bswmd_class,
            data.autosar_ib_class,
            data.cfg_info_dict,
            data.autosar_system_class,
            data.sys_target_dict,
        )

        imported_cdd = self.cdd_importer.get_pre_import_meta_info()
        return imported_cdd

    def apply_cdd_import(self, file_list: List[str], merge_signal_flag, progress_signal):
        progress_signal.emit("Importing cdd files")
        cdd_list = []
        excel_list = []
        for file in file_list:
            if file.endswith(".cdd"):
                cdd_list.append(file)
            if file.endswith(".xlsx"):
                excel_list.append(file)

        # Parse excel info and record parse result
        import_cdd_excel_parser = ImportCDDExcelParser()
        result = import_cdd_excel_parser.execute_import_excel_command(excel_list)
        if result:
            data.cfg_info_dict.update({"excel": result})

        sys_info_obj: SysInfoClass = data.sys_info_class
        cdd_info: dict = sys_info_obj.cdd
        cdd_info.pop("excel", None)
        for excel in excel_list:
            excel_name = os.path.basename(excel)
            cdd_info.update({"excel": {excel_name: excel}})
        sys_info_obj.cdd = cdd_info

        # Parse cdd info
        self.cdd_importer.import_files(cdd_list, merge_signal_flag)

        return data.autosar_bswmd_class, data.autosar_bsw_class

    def judge_file_is_asw_arxml(self, file_obj: object) -> bool:
        """判断一个文件是否为 asw 文件"""
        SWC_DATA_TYPE_PORT_INTERFACE = [
            "DATA-TYPE-MAPPING-SET",
            "APPLICATION-PRIMITIVE-DATA-TYPE",
            "APPLICATION-ARRAY-DATA-TYPE",
            "DATA-TYPE-MAP",
            "APPLICATION-ARRAY-ELEMENT",
            "ARRAY-SIZE-HANDLING-ENUM",
            "APPLICATION-RECORD-DATA-TYPE",
            "CLIENT-SERVER-INTERFACE",
            "APPLICATION-RECORD-ELEMENT",
            "VARIABLE-DATA-PROTOTYPE",
            "PARAMETER-INTERFACE",
            "PARAMETER-DATA-PROTOTYPE",
            "SENDER-RECEIVER-INTERFACE",
            "MODE-SWITCH-INTERFACE",
            "NV-DATA-INTERFACE" "TRIGGER-INTERFACE-MAPPING",
            "PORT-INTERFACE-MAPPING-SET",
            "CLIENT-SERVER-INTERFACE-MAPPING",
        ]
        ILLEGAL_KEY_WORD = [
            "BSW-MODULE-DESCRIPTION",
            "SERVICE-SW-COMPONENT-TYPE",
            "ECUC-MODULE-CONFIGURATION-VALUES",
            "DATA-MAPPINGS",
            "I-SIGNAL-I-PDU",
        ]
        # 1. 存在 asw 的字段
        for asw_key_word in AutosarUtils.SUPPORT_APPL_COMPONENT_TYPE:
            if len(AutosarUtil.find_nodes(file_obj, asw_key_word, True)) > 0:
                return True
        # 2. 过滤 ib, service component, ecuc, flatExtract, communication arxml
        for illegal_key_word in ILLEGAL_KEY_WORD:
            if len(AutosarUtil.find_nodes(file_obj, illegal_key_word, True)) > 0:
                return False
        # 有 SWComponentTemplate::dataType 内或者 interface 的字段也认为是asw文件
        for key_word in SWC_DATA_TYPE_PORT_INTERFACE:
            if len(AutosarUtil.find_nodes(file_obj, key_word, True)) > 0:
                return True
        return False

    def judge_file_is_ecuc_arxml(self, file_obj: object):
        """判断一个文件是否为 ecuc arxml"""
        if len(AutosarUtil.find_nodes(file_obj, "ECUC-MODULE-CONFIGURATION-VALUES", True)) > 0:
            return bool(get_short_name(file_obj.AR_PACKAGES.AR_PACKAGE[0]) != "InitialEcuC")

        return False

    @perf_record.log_function_stats(["BSW Editor", "配置文件解析和导入", "ASW arxml导入"])
    def apply_asw_import(self, dir_path, progress_signal):
        print(dir_path)
        if len(dir_path) == 0:
            return
        arxml_files = AutosarUtil.get_arxml_file_from_path(dir_path)
        # 拦截非 asw arxml 文件，并提示
        illegal_files = []
        with AutosarUtil.gc_guard():
            for file_path in arxml_files:
                progress_signal.emit(f"validate {os.path.basename(file_path)} is legal to import...")
                if not self.judge_file_is_asw_arxml(AutosarUtil.parse_arxml(file_path)):
                    illegal_files.append(file_path)
                AutosarUtil.trigger_gc()
        for illegal_file_path in illegal_files:
            arxml_files.remove(illegal_file_path)

        if len(arxml_files) > 0:
            progress_signal.emit("Importing asw...")
        self.apply_asw_import_by_select_files(arxml_files)

        return illegal_files

    def apply_asw_import_by_select_files(self, file_list: list):
        if len(file_list) == 0:
            return
        sys_info_obj: SysInfoClass = data.sys_info_class
        sys_info_obj.swc = os.path.dirname(file_list[0])
        res, component_arxml_path_dict_info = ArxmlParseHandler.asw_arxml_merge_logic(
            file_list, sys_info_obj.config_base_path
        )
        if "asw" not in res:
            logger.warning("Cannot get asw info")
        else:
            data.autosar_asw_class = res["asw"]

        data.component_arxml_path_dict = {"asw_component": component_arxml_path_dict_info}

        SystemArxmlsManager.update_flatextract_arxml_from_arxml_slot(data.autosar_asw_class, data.autosar_system_class)

    def get_all_module_of_mcal_arxml(self, file_path):
        # 1. 解析mcal文件
        if file_path is None:
            logger.ui_warning("You did not select the mcal arxml file, please select.")
            return None
        parse_res = ArxmlParseHandler.parse_mcal_arxml(file_path)
        return self.get_mcal_list_prefix(parse_res, file_path)

    def get_mcal_list_prefix(self, parse_res, file_path):
        supported_mcal_module_list = []
        sys_info_obj: SysInfoClass = data.sys_info_class
        all_ecuc_objs = parse_res.find_nodes("ECUC-MODULE-CONFIGURATION-VALUES")

        mcal_arxml_dict = {}
        for module_obj in all_ecuc_objs:
            module_name = get_short_name(module_obj)
            mcal_arxml_dict[module_name] = AutosarUtil.to_ecuc_module_configuration_values_dict(module_obj)

        prefix = get_definition_ref(all_ecuc_objs[0]).split("/")[1]

        data.cfg_info_dict["eb"] = {"arxml": mcal_arxml_dict}
        # 2. 更新mcal的导入信息到sys_info_obj
        data.sys_info_class.eb_arxml = file_path
        all_modules_of_mcal_list = [get_short_name(ecuc_obj) for ecuc_obj in all_ecuc_objs]

        for module_name in all_modules_of_mcal_list:
            if ArxmlParseHandler.check_mod_files_exist(sys_info_obj.plug_in_bswmd_path, [module_name]):
                supported_mcal_module_list.append(module_name)

        return supported_mcal_module_list, prefix

    @perf_record.log_function_stats(["BSW Editor", "配置文件解析和导入", "Ecuc和ASW arxml文件", "Ecuc和ASW arxml导入"])
    def import_all_types_arxml(self, need_update_ecuc_dcit, asw_file_list: list = None, progress_signal=None):
        # 更新 ecuc
        prefix_diff_modules = {}
        if need_update_ecuc_dcit is not None and len(need_update_ecuc_dcit) > 0:
            progress_signal.emit("Updating ecuc module information...")
            prefix_diff_modules = EcucCfgImport.update_ecuc_autosar_dict(data, need_update_ecuc_dcit)

        # 最后更新 asw
        if asw_file_list is not None and len(asw_file_list) > 0:
            progress_signal.emit("Updating asw information...")
            self.apply_asw_import_by_select_files(asw_file_list)

        return data.autosar_bswmd_class, data.autosar_bsw_class, prefix_diff_modules

    @perf_record.log_function_stats(["BSW Editor", "配置文件解析和导入", "SOA配置文件导入"])
    def import_sidl_sdepl_dir(self, dir_path, progress_signal):
        progress_signal.emit("Importing sidl/sdepl from dir")
        importer = SidlSdeplImporter(
            data.sys_info_class,
            data.autosar_bsw_class,
            data.autosar_bswmd_class,
            data.autosar_ib_class,
            data.autosar_system_class,
            data.cfg_info_dict,
            data.sys_target_dict,
        )
        res = importer.import_files(dir_path)
        if res:
            logger.ui_info("Loading sidl/sdepl finished")

    def clear_initial_container(self, path_list: List[str]):
        for container_path in path_list:
            path_pieces = container_path.split("/")
            if len(path_pieces) > 2:
                module_name = path_pieces[2]

            module_inst = data.autosar_bsw_class.get(module_name, None)
            if not module_inst:
                return

            initial_path = container_path.replace("ActiveEcuC", "InitialEcuC")
            initial_obj = data.autosar_system_class["Initial"]
            ddd_obj = data.autosar_system_class["DiagnosticsDescriptionData"]
            initial_container = initial_obj.find(initial_path) or ddd_obj.find(initial_path)
            if not initial_container:
                logger.debug(f"Cannot find corresponding initial container of {container_path}")
                return

            if AutosarUtil.get_tag(initial_container) == "ECUC-MODULE-CONFIGURATION-VALUES":
                logger.debug("Do not support removing module directly")

            parent_obj = AutosarUtil.get_parent(initial_container)
            ecuc_container_list = parent_obj.ECUC_CONTAINER_VALUE
            AutosarUtil.remove_container_value(ecuc_container_list, initial_container)

    def restore_possibility(self, parent_container, child_def_path=""):
        """
        Compare initial with ecuc to check if the node has any sub containers that could be restored.

        Args:
            parent_container: The parent contaienr whose children will be checked
            child_def_path: Only check sub container of specific definition if the param is not empty,
                            otherwise check all sub containers

        Return:
            Whether sub containers are restorable;
            The restorable sub containers
        """
        container_path = parent_container.get_path()

        initial_path = container_path.replace("ActiveEcuC", "InitialEcuC")
        initial_obj = data.autosar_system_class["Initial"]
        ddd_obj = data.autosar_system_class["DiagnosticsDescriptionData"]
        initial_container = initial_obj.find(initial_path) or ddd_obj.find(initial_path)

        # If cannot find parent node in initial,
        # it means sub containers cannot be restored from derived recored
        if not initial_container:
            return False

        target_child_def = child_def_path.split("/")[-1] if child_def_path else ""

        def is_target_child(def_path):
            """
            Check if definition ref of sub container is our target
            """
            if target_child_def:
                def_name = def_path.split("/")[-1]
                return def_name == target_child_def
            else:
                return True

        initial_sub_node = getattr(initial_container, "CONTAINERS", None) or getattr(
            initial_container, "SUB_CONTAINERS", None
        )
        initial_sub_list = getattr(initial_sub_node, "ECUC_CONTAINER_VALUE", [])
        initial_target = {
            get_short_name(sub): sub for sub in initial_sub_list if is_target_child(get_definition_ref(sub))
        }
        ecuc_sub_node = getattr(parent_container, "CONTAINERS", None) or getattr(
            parent_container, "SUB_CONTAINERS", None
        )
        ecuc_sub_list = getattr(ecuc_sub_node, "ECUC_CONTAINER_VALUE", [])
        ecuc_target = {get_short_name(sub): sub for sub in ecuc_sub_list if is_target_child(get_definition_ref(sub))}

        restorable = {k: v for k, v in initial_target.items() if k not in ecuc_target}
        return restorable
