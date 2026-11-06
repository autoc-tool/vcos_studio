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
from copy import deepcopy
from typing import Dict
from basic_func_module.file_handler.sidl.sidl_datapool import (
    SidlDataPool,
    DataTypeNotFoundError,
    DataTypeConflictError,
    ServiceConflictError,
)
from basic_func_module.file_handler.sdepl.parser import parse_sdepl_file
from func_module.project_management.sys_info_class import SysInfoClass
from func_module.health_monitor.logger import logger


class SidlSdeplImporter:

    def __init__(
        self,
        sys_info_obj: SysInfoClass,
        ecuc_obj_dict,
        bswmd_obj_dict,
        ib_obj_dict,
        system_autosar_dict,
        cfg_info_dict,
        sys_target_dict,
    ) -> None:
        self.sys_info_obj = sys_info_obj
        self.ecuc_obj_dict = ecuc_obj_dict
        self.bswmd_obj_dict = bswmd_obj_dict
        self.ib_obj_dict = ib_obj_dict
        self.cfg_info_dict: dict = cfg_info_dict
        self.system_autosar_dict = system_autosar_dict
        self.sys_target_dict = sys_target_dict

    def collect_files(self, folder_path):
        sidl_files = []
        sdepl_files = []
        for file in os.listdir(folder_path):
            suffix: str = os.path.splitext(file)[1]
            abs_path = os.path.join(folder_path, file)
            if suffix.lower() == ".sidl":
                sidl_files.append(abs_path)
            elif suffix.lower() == ".sdepl":
                sdepl_files.append(abs_path)

        assert sidl_files and sdepl_files, "Miss sidl file or sdepl file! Must import them at the same time!"

        return sidl_files, sdepl_files

    def merge_service_methods(self, sidl_info, sdepl_info):
        # Check if methods are same in sidl and sdepl
        sidl_part = {m["name"]: m for m in sidl_info}
        sdepl_part_set = {m["name"] for m in sdepl_info}
        assert set(sidl_part.keys()) == sdepl_part_set, "Methods in sidl and sdepl are diff!"

        # Merge method info
        res = []
        for sdepl_method in sdepl_info:
            method_name = sdepl_method["name"]
            sidl_method = sidl_part[method_name]
            merged_info: Dict = deepcopy(sdepl_method)
            merged_info.update(sidl_method)
            res.append(merged_info)

        return res

    def merge_service_events(self, sidl_info, sdepl_info):
        # Check if events are same in sidl and sdepl
        sidl_part = {m["name"]: m for m in sidl_info}
        sdepl_part_set = {m["name"] for m in sdepl_info}
        assert set(sidl_part.keys()) == sdepl_part_set, "Events in sidl and sdepl are diff!"

        # Merge event info
        res = []
        for sdepl_event in sdepl_info:
            event_name = sdepl_event["name"]
            sidl_event = sidl_part[event_name]
            merged_info: Dict = deepcopy(sdepl_event)
            merged_info.update(sidl_event)
            res.append(merged_info)

        return res

    def merge_service_fields(self, sidl_info, sdepl_info):
        # Check if fields are same in sidl and sdepl
        sidl_part = {m["name"]: m for m in sidl_info}
        sdepl_part_set = {m["name"] for m in sdepl_info}
        assert set(sidl_part.keys()) == sdepl_part_set, "Fields in sidl and sdepl are diff!"

        # Merge field info
        res = []
        for sdepl_field in sdepl_info:
            field_name = sdepl_field["name"]
            sidl_field = sidl_part[field_name]
            merged_info: Dict = deepcopy(sdepl_field)
            merged_info.update(sidl_field)
            res.append(merged_info)

        return res

    def merge_sidl_sdepl_info(self, sidl_dict, sdepl_dict):
        """
        Merge service info in sidl and sdepl.
        If service cannot be found in sdepl, the service info will be ignored, and vice versa.
        """

        # Collect all services exist in sidl dict
        sidl_service_dict = {s["name"]: s for s in sidl_dict["service"]}

        # Merge service info sdepl dict
        merge_res = deepcopy(sidl_dict)
        merge_res["service"] = []
        for sdepl_service in sdepl_dict["service"]:
            service_name = sdepl_service["name"]
            # For service both exist in sidl and sdepl, executing merging operation
            if service_name in sidl_service_dict:
                merge_service_res = deepcopy(sdepl_service)
                binding_type = merge_service_res["binding_type"]
                select = binding_type["select"]

                sidl_service = sidl_service_dict[service_name]

                # Merge methods info of the service
                sidl_method = sidl_service["method"]
                sdepl_method = binding_type[select]["methods"]
                try:
                    merge_method_res = self.merge_service_methods(sidl_method, sdepl_method)
                    binding_type[select]["methods"] = merge_method_res
                except AssertionError as e:
                    raise AssertionError(f"{service_name}: {str(e)}")

                # Merge events info of the service
                sidl_event = sidl_service["event"]
                sdepl_event = binding_type[select]["events"]
                try:
                    merge_event_res = self.merge_service_events(sidl_event, sdepl_event)
                    binding_type[select]["events"] = merge_event_res
                except AssertionError as e:
                    raise AssertionError(f"{service_name}: {str(e)}")

                # Merge events info of the service
                sidl_field = sidl_service["field"]
                sdepl_field = binding_type[select]["fields"]
                try:
                    merge_field_res = self.merge_service_fields(sidl_field, sdepl_field)
                    binding_type[select]["fields"] = merge_field_res
                except AssertionError as e:
                    raise AssertionError(f"{service_name}: {str(e)}")

                # Append merged service info as final result
                merge_res["service"].append(merge_service_res)

        return merge_res

    def import_files(self, folder_path):
        print(f"sidl_sdepl_dir: {folder_path}")
        # Collect all sidl and sdepl files in the folder
        try:
            sidl_files, sdepl_files = self.collect_files(folder_path)
        except AssertionError as e:
            logger.ui_error(str(e))
            return False

        # parse sidl files
        try:
            sidl_pool = SidlDataPool(sidl_files)
        except DataTypeNotFoundError as e:
            logger.ui_error(str(e))
            return False
        except DataTypeConflictError as e:
            logger.ui_error(str(e))
            return False
        except ServiceConflictError as e:
            logger.ui_error(str(e))
            return False
        sidl_dict = sidl_pool.sidl_dict

        # parse sdepl file
        try:
            sdepl_dict = parse_sdepl_file(sdepl_files[0])
        except Exception as e:
            logger.ui_error(str(e))
            return False

        # Merge sidl info and sdepl info
        try:
            merge_res = self.merge_sidl_sdepl_info(sidl_dict, sdepl_dict)
        except AssertionError as e:
            logger.ui_error(str(e))
            return False

        self.cfg_info_dict["sidl_sdepl"] = merge_res
        return True
