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
from basic_func_module.base_common.load_plug_in import LoadPlugIn
from basic_func_module.file_handler.cdd import parser
from basic_func_module.path_handler.path_converter import PathConverter_Adaptor
from func_module.import_file.module_enabler import FileType, enable_modules
from func_module.module_management.module_management import ModuleManagement
from func_module.project_management.sys_info_class import SysInfoClass
from func_module.health_monitor.logger import logger
from func_module.module_management.base_config import BASE_CONFIG_PATH

BASE_ARXML_PATH = os.path.join(BASE_CONFIG_PATH, "base_arxml")
CDD_RELATED_MODULE_LIST = ["Dcm", "Dem", "NvM"]


class CddImporter:
    def __init__(
        self,
        sys_info_obj: SysInfoClass,
        ecuc_obj_dict,
        bswmd_obj_dict,
        ib_obj_dict,
        cfg_info_dict,
        system_autosar_dict,
        sys_target_dict,
    ) -> None:
        self.sys_info_obj = sys_info_obj
        self.ecuc_obj_dict = ecuc_obj_dict
        self.bswmd_obj_dict = bswmd_obj_dict
        self.ib_obj_dict = ib_obj_dict
        self.cfg_info_dict: dict = cfg_info_dict
        self.system_autosar_dict = system_autosar_dict
        self.sys_target_dict = sys_target_dict
        self.pre_import_dict = {}
        self.block_list = []
        for _, file_info in self.sys_info_obj.cdd["list"].items():
            file_path = file_info["path"]
            self.pre_import_dict[file_path] = {"meta_info": file_info, "parse_result": None}

    def get_pre_import_meta_info(self):
        meta_info_dict = {}
        for file_path, file_info in self.pre_import_dict.items():
            file_name = os.path.basename(file_path)
            meta_info_dict[file_name] = file_info["meta_info"]

        return meta_info_dict

    def pre_import(self, file_list):
        meta_info_dict: dict = self.get_pre_import_meta_info()
        for file_path in file_list:
            # Only allow import one cdd file, so clear pre_import_dict each time
            meta_info_dict.clear()
            self.pre_import_dict.clear()
            file_base_name = os.path.basename(file_path)
            meta_info = {"path": file_path, "node_selected": None, "node_list": None}
            meta_info_dict[file_base_name] = meta_info
            self.pre_import_dict[file_path] = {"meta_info": meta_info, "parse_result": None}
        return meta_info_dict

    def replace_pre_import(self, old_file_path, new_file_path):
        new_file_path = PathConverter_Adaptor.to_abs(new_file_path, self.sys_info_obj.project_path)
        meta_info = {"path": new_file_path, "node_selected": None, "node_list": None}
        # 更新字典
        updated_pre_import_info_dict = {}
        for file_path, file_info in self.pre_import_dict.items():
            if file_path == old_file_path:
                updated_pre_import_info_dict[new_file_path] = {"meta_info": meta_info, "parse_result": None}
            else:
                updated_pre_import_info_dict[file_path] = file_info

        self.pre_import_dict = updated_pre_import_info_dict
        return meta_info

    def de_pre_import(self, file_list):
        for file_path in file_list:
            self.pre_import_dict.pop(file_path)

    def update_dcm_cfg_from_cdd(self, merge_signal_flag):
        """
        Update dcm cfg from cdd file

        1. Update dcm cfg according with dcm cfg updater

        Args:
            db_cdd_dict: cdd parsing result
        """
        db_cdd_dict = self.cfg_info_dict["cdd"]
        if self.cfg_info_dict.get("excel"):
            all_excel_dict = self.cfg_info_dict["excel"]
        else:
            all_excel_dict = None
        dcm_cfg_converter = LoadPlugIn.load_module("Dcm", "config_plug_in.cfg_converter.dcm_cfg_converter")
        DcmCfgConverterWithCdd = getattr(dcm_cfg_converter, "DcmCfgConverterWithCdd")
        dcm_cfg_updater = DcmCfgConverterWithCdd(
            base_arxml_path=BASE_ARXML_PATH,
            merge_signal_flag=merge_signal_flag,
            db_cdd_dict=db_cdd_dict,
            all_excel_dict=all_excel_dict,
            mod_autosar_dict=self.bswmd_obj_dict,
            ecuc_autosar_dict=self.ecuc_obj_dict,
            system_autosar_dict=self.system_autosar_dict,
        )
        dcm_cfg_updater.update_from_cdd()

    def update_dem_cfg_from_cdd(self):
        """
        Update dem cfg from cdd file

        1. Update dem cfg according with dem cfg converter

        Args:
            db_cdd_dict: cdd parsing result
        """
        db_cdd_dict = self.cfg_info_dict["cdd"]
        if self.cfg_info_dict.get("excel"):
            all_excel_dict = self.cfg_info_dict["excel"]
        else:
            all_excel_dict = None

        dem_cfg_converter = LoadPlugIn.load_module("Dem", "config_plug_in.cfg_converter.dem_cfg_converter")
        DemCfgConverterWithCdd = getattr(dem_cfg_converter, "DemCfgConverterWithCdd")
        dem_cfg_converter = DemCfgConverterWithCdd(
            base_arxml_path=BASE_ARXML_PATH,
            db_cdd_dict=db_cdd_dict,
            all_excel_dict=all_excel_dict,
            mod_autosar_dict=self.bswmd_obj_dict,
            ecuc_autosar_dict=self.ecuc_obj_dict,
            system_autosar_dict=self.system_autosar_dict,
        )
        self.block_list = dem_cfg_converter.update_from_cdd()

    def update_nvm_cfg_from_cdd(self):
        """
        Update nvm cfg from cdd file

        1. Update nvm cfg according with nvm cfg converter

        Args:
            db_cdd_dict: cdd parsing result
        """
        db_cdd_dict = self.cfg_info_dict["cdd"]
        nvm_cfg_converter = LoadPlugIn.load_module("NvM", "config_plug_in.cfg_converter.nvm_cfg_converter")
        NvmCfgConverterwithCdd = getattr(nvm_cfg_converter, "NvmCfgConverterwithCdd")
        nvm_cfg_converter = NvmCfgConverterwithCdd(
            base_arxml_path=BASE_ARXML_PATH,
            db_cdd_dict=db_cdd_dict,
            mod_autosar_dict=self.bswmd_obj_dict,
            ecuc_autosar_dict=self.ecuc_obj_dict,
            system_autosar_dict=self.system_autosar_dict,
            block_list=self.block_list,
        )
        nvm_cfg_converter.update_from_cdd()

    def _update_modules(self, merge_signal_flag):
        if self.cfg_info_dict["cdd"]:
            self.update_dcm_cfg_from_cdd(merge_signal_flag)
            self.update_dem_cfg_from_cdd()
            self.update_nvm_cfg_from_cdd()

    def apply_import(self, merge_signal_flag):
        db_cdd_dict = {}
        for file_path in self.pre_import_dict:
            file_name = os.path.basename(file_path)
            db_cdd_dict.update({file_name: parser.import_config_from_cdd([file_path])})

        self.cfg_info_dict["cdd"] = {}
        self.cfg_info_dict["cdd"].update(db_cdd_dict)
        # 2. 如果确实导入了dbc文件，添加受cdd影响的模块
        if self.pre_import_dict:
            module_manage = ModuleManagement(
                self.sys_info_obj, self.ecuc_obj_dict, self.bswmd_obj_dict, self.ib_obj_dict
            )
            enable_modules(FileType.CDD, self.pre_import_dict, self.sys_target_dict, module_manage)
            # for module in CDD_RELATED_MODULE_LIST:
            #     module_manage.append_module(module)
        # 3. 根据cdd文件信息更新对应模块
        self._update_modules(merge_signal_flag)
        # 4. 将导入cdd的信息保存至sys_info_obj
        cdd_info_in_sys = self.sys_info_obj.cdd
        cdd_info_in_sys["list"] = {}
        for file_path in self.pre_import_dict.keys():
            file_name = os.path.basename(file_path)
            if file_name not in cdd_info_in_sys["list"]:
                cdd_info_in_sys["list"][file_name] = {"path": file_path}

        cdd_info_in_sys["num"] = len(cdd_info_in_sys["list"])
        cdd_info_in_sys.update({"single_signal": merge_signal_flag})
        self.sys_info_obj.cdd = cdd_info_in_sys
        logger.ui_info(f"Finish import {list(self.pre_import_dict.keys())}")

    def import_files(self, file_list, merge_signal_flag):
        # 1. 解析cdd文件信息，并保存至cfg_info_dict
        db_cdd_dict = {}
        for file_path in file_list:
            file_name = os.path.basename(file_path)
            db_cdd_dict.update({file_name: parser.import_config_from_cdd([file_path])})

        self.cfg_info_dict["cdd"] = {}
        self.cfg_info_dict["cdd"].update(db_cdd_dict)
        # 2. 添加受cdd影响的模块
        module_manage = ModuleManagement(self.sys_info_obj, self.ecuc_obj_dict, self.bswmd_obj_dict, self.ib_obj_dict)
        for module in CDD_RELATED_MODULE_LIST:
            module_manage.append_module(module)
        # 3. 根据cdd文件信息更新对应模块
        self._update_modules(merge_signal_flag, file_list)
        # 4. 将导入cdd的信息保存至sys_info_obj
        cdd_info_in_sys = self.sys_info_obj.cdd
        cdd_info_in_sys["list"] = {}
        for file_path in file_list:
            file_name = os.path.basename(file_path)
            if file_name not in cdd_info_in_sys["list"]:
                cdd_info_in_sys["list"][file_name] = {"path": file_path}

        cdd_info_in_sys["num"] = len(cdd_info_in_sys["list"])
        self.sys_info_obj.cdd = cdd_info_in_sys
