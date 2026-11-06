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
from basic_func_module.base_logger import logger
from basic_func_module.path_handler.path_converter import PathConverter_Adaptor
from basic_func_module.file_handler.ldf import parser
from basic_func_module.file_validation.file_validation_log import FileValidationLog
from basic_func_module.file_validation.ldf_validator import LdfValidator
from func_module.import_file.module_enabler import FileType, enable_modules
from func_module.project_management.sys_info_class import SysInfoClass
from func_module.module_management.module_management import ModuleManagement


class LdfImporter:

    def __init__(
        self,
        sys_info_obj: SysInfoClass,
        ecuc_obj_dict,
        bswmd_obj_dict,
        ib_obj_dict,
        system_obj_dict,
        cfg_info_dict,
        sys_target_dict,
    ) -> None:
        self.sys_info_obj = sys_info_obj
        self.ecuc_obj_dict = ecuc_obj_dict
        self.bswmd_obj_dict = bswmd_obj_dict
        self.ib_obj_dict = ib_obj_dict
        self.system_obj_dict = system_obj_dict
        self.cfg_info_dict = cfg_info_dict
        self.sys_target_dict = sys_target_dict
        self.pre_import_dict = {}
        for _, file_info in self.sys_info_obj.ldf["list"].items():
            file_path = file_info["path"]
            if os.path.exists(file_path):
                self.pre_import_dict[file_path] = {"meta_info": file_info, "parse_result": None}
            else:
                logger.warning(f"{file_path} not exists, omit the file record")
                logger.ui_warning(f"{file_path} not exists, omit the file record")

    def get_pre_import_meta_info(self):
        meta_info_dict = {}
        for file_path, file_info in self.pre_import_dict.items():
            file_name = os.path.basename(file_path)
            meta_info_dict[file_name] = file_info["meta_info"]

        return meta_info_dict

    def validate_ldf(self, file_path):
        ldf_validator = LdfValidator()
        ldf_validator.clear_log()
        res = ldf_validator.validate(file_path)
        if not res:
            return False, ldf_validator.log_list
        else:
            return True, []

    def pre_import(self, file_list):
        meta_info_dict = self.get_pre_import_meta_info()
        num_of_ldf = len(
            [meta_info for meta_info in meta_info_dict.values() if "validation_error_log" not in meta_info]
        )
        for file_path in file_list:
            res, log_list = self.validate_ldf(file_path)
            log_list: list[FileValidationLog]
            if not res:
                file_base_name = os.path.basename(file_path)
                meta_info = {"path": file_path, "validation_error_log": log_list}
                for log in log_list:
                    logger.ui_error(f"Invalid ldf file: {file_path};\n line: {log.line};\n message: {log.message}")
            else:
                ldf_info = parser.parse_ldf_file(file_path, num_of_ldf)
                num_of_ldf += 1
                file_path = PathConverter_Adaptor.to_abs(file_path, self.sys_info_obj.project_path)

                # 构造导入文件元信息
                file_base_name = os.path.basename(ldf_info["ldf_name"])
                node_set = {
                    message.node_name for message in list(ldf_info["details"].values()) if len(message.node_name)
                }
                node_list = list(node_set)
                meta_info = {"path": file_path, "node_selected": node_list[0], "node_list": node_list}
                self.pre_import_dict[file_path] = {"meta_info": meta_info, "parse_result": ldf_info}
            meta_info_dict[file_base_name] = meta_info

        return meta_info_dict

    def replace_pre_import(self, old_file_path, new_file_path):
        old_file_name = os.path.basename(old_file_path)
        meta_info_dict = self.get_pre_import_meta_info()
        for index, (filename, meta_info) in enumerate(meta_info_dict.items()):
            if filename == old_file_name:
                num_of_ldf = index
                break
        # 解析新增dbc文件
        res, log_list = self.validate_ldf(new_file_path)
        log_list: list[FileValidationLog]
        if not res:
            meta_info = {"path": new_file_path, "validation_error_log": log_list}
            for log in log_list:
                logger.ui_error(f"Invalid ldf file: {new_file_path};\n line: {log.line};\n message: {log.message}")
        else:
            ldf_info = parser.parse_ldf_file(new_file_path, num_of_ldf)
            new_file_path = PathConverter_Adaptor.to_abs(new_file_path, self.sys_info_obj.project_path)
            # 构造导入文件元信息
            node_set = {message.node_name for message in list(ldf_info["details"].values()) if len(message.node_name)}
            node_list = list(node_set)
            meta_info = {"path": new_file_path, "node_selected": node_list[0], "node_list": node_list}
            # 更新字典
            updated_pre_import_info_dict = {}
            for file_path, file_info in self.pre_import_dict.items():
                if file_path == old_file_path:
                    updated_pre_import_info_dict[new_file_path] = {"meta_info": meta_info, "parse_result": ldf_info}
                else:
                    updated_pre_import_info_dict[file_path] = file_info

            self.pre_import_dict = updated_pre_import_info_dict
        return meta_info

    def de_pre_import(self, file_list):
        for file_path in file_list:
            self.pre_import_dict.pop(file_path)

    def set_selected_node(self, file_path, selected_node):
        file_path = os.path.abspath(file_path)
        if file_path in self.pre_import_dict:
            self.pre_import_dict[file_path]["meta_info"]["node_selected"] = selected_node
        else:
            logger.error(f"Cannot find {file_path} in pre imported fils")

    def check_channel_name(self):
        self.final_parse()

        channel_name_set = set()
        for file_path, file_info in self.pre_import_dict.items():
            channel_name = file_info["parse_result"]["channel_name"]
            if channel_name in channel_name_set:
                return False, file_path, channel_name
            channel_name_set.add(channel_name)

        return True, "", ""

    def final_parse(self):
        num_of_ldf = 0
        for file_path, file_info in self.pre_import_dict.items():
            parse_result = parser.parse_ldf_file(file_path, num_of_ldf)
            self.pre_import_dict[file_path]["parse_result"] = parse_result
            num_of_ldf += 1

        ldf_info_dict = []
        for file_path, file_info in self.pre_import_dict.items():
            file_info["parse_result"]["file"] = file_path
            file_info["parse_result"]["node_selected"] = file_info["meta_info"]["node_selected"]
            ldf_info_dict.append(file_info["parse_result"])
        self.cfg_info_dict["ldf"] = ldf_info_dict

    def get_file_content(self, file_path):
        self.final_parse()
        file_info = self.pre_import_dict[file_path]
        # If the file not parsed yet, parse it
        if file_info["parse_result"] is None:
            parse_result = parser.parse_ldf_file(file_path)
            file_info["parse_result"] = parse_result

        return file_info

    def validate_all(self):
        error_log = {}
        for file_path in self.pre_import_dict.keys():
            res, log_list = self.validate_ldf(file_path)
            if not res:
                error_log[file_path] = log_list
                for log in log_list:
                    logger.ui_error(f"Invalid ldf file: {file_path};\n line: {log.line};\n message: {log.message}")

        return error_log

    def apply_import(self):
        # 1. 解析pre_import列表中未解析的文件,并添加进cfg_info_dict
        self.final_parse()
        # 2. 如果确实导入了ldf文件, 添加ldf相关模块
        if self.pre_import_dict:
            module_manage = ModuleManagement(
                self.sys_info_obj, self.ecuc_obj_dict, self.bswmd_obj_dict, self.ib_obj_dict
            )
            enable_modules(FileType.LDF, self.pre_import_dict, self.sys_target_dict, module_manage)

        # 4. 将导入文件信息写入sys_info_obj
        ldf_info_in_sys: dict = self.sys_info_obj.ldf
        ldf_info_in_sys["list"] = {}
        for file_path, file_info in self.pre_import_dict.items():
            file_name = os.path.basename(file_path)
            if file_name not in ldf_info_in_sys["list"]:
                node_list = file_info["meta_info"]["node_list"]
                ldf_info_in_sys["list"][file_name] = {
                    "path": file_path,
                    "node_selected": file_info["meta_info"]["node_selected"],
                    "node_list": node_list,
                }
        ldf_info_in_sys["num"] = len(ldf_info_in_sys["list"])
        self.sys_info_obj.ldf = ldf_info_in_sys

        logger.ui_info(f"Finish import {list(self.pre_import_dict.keys())}")
