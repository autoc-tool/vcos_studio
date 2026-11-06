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
from basic_func_module.file_handler.excel_parser.import_excel_base import ImportExcelBase
from basic_func_module.base_logger import logger
from openpyxl.reader.excel import load_workbook


class ImportDBCOrLDFExcelParser(ImportExcelBase):

    def execute_import_excel_command(self, excel_path_dict):
        dict = {}
        if not excel_path_dict:
            return None
        for excel_path in excel_path_dict:
            excel_name = os.path.basename(excel_path)
            if excel_name == "PduRCfg.xlsx":
                result = self.parse_excel_file(excel_path)
                if result is None:
                    logger.ui_error(f"{excel_path} load PduRCfg.xlsx failed, result is None!")
                    return None
                list = self.get_valid_bus_name(excel_path)
                if self.pdur_excel_validate(result, list) is False:
                    logger.ui_error(f"{excel_path} PduRCfg.xlsx Validation Failed!")
                    return None
                dict.update({excel_name: result})
            else:  # 'ComCfg.xlsx'
                result = self.parse_excel_file(excel_path)
                if result is None or result["excel_dict"] is None:
                    logger.ui_error(f"{excel_path} load ComCfg.xlsx failed, result is None!")
                    return None
                if self.excel_validate(result["excel_dict"]) is False:
                    logger.ui_error(f"{excel_path} ComCfg.xlsx Validation Failed!")
                    return None
                dict.update({excel_name: result["result_dict"]})
        return dict

    def update_dcm_cfg_from_cdd(self):
        pass

    def parse_excel_file(self, file_path):
        excel_name = os.path.basename(file_path)
        if excel_name == "PduRCfg.xlsx":
            pdur_excel_dict = {}
            workbook = load_workbook(file_path)
            sheet = workbook["Sheet1"]
            # 固定excel文件为5列
            if sheet.max_column != 5:
                return
            project_name = self.get_cell_value(sheet, 1, 2)
            self_diag_req = self.get_cell_value(sheet, 2, 2)
            self_diag_rsp = self.get_cell_value(sheet, 3, 2)
            if self_diag_req is None:
                self_diag_req = "0xFFF"
            if self_diag_rsp is None:
                self_diag_rsp = "0xFFF"
            func_bus = self.get_cell_value(sheet, 4, 2)
            self_info = {
                "project_name": project_name,
                "self_diag_req": int(self_diag_req, 16),
                "self_diag_rsp": int(self_diag_rsp, 16),
                "func_bus": func_bus,
            }
            pdur_excel_dict.update({2: self_info})
            for row in range(6, sheet.max_row + 1):
                dest_list = []
                row_value_list = self.get_row_value(sheet, row)
                if row_value_list[0] == "#":
                    continue
                name_temp = row_value_list[0]
                SrcBus_temp = row_value_list[1]
                SrcId_temp = row_value_list[2]
                DstBus_temp = row_value_list[3]
                DstId_temp = row_value_list[4]
                if name_temp is None:
                    name_temp = "INVALID"
                if SrcId_temp is None:
                    SrcId_temp = "0xFFF"
                if DstId_temp is None:
                    DstId_temp = "0xFFF"
                dict = {
                    "Name": row_value_list[0],
                    "SrcBus": SrcBus_temp,
                    "SrcId": int(SrcId_temp, 16),
                    "DstBus": DstBus_temp,
                    "DstId": int(DstId_temp, 16),
                }
                pdur_excel_dict.update({row: dict})
            return pdur_excel_dict
        else:
            pdur_excel_dict = {"excel_dict": {}, "result_dict": {}}
            workbook = load_workbook(file_path)
            sheet = workbook["Sheet1"]
            # 固定excel文件为4列
            if sheet.max_column != 4:
                return
            project_name = self.get_cell_value(sheet, 2, 1)
            for row in range(3, sheet.max_row + 1):
                dest_list = []
                row_value_list = self.get_row_value(sheet, row)
                dict = {
                    "Name": row_value_list[0],
                    "Type": row_value_list[1],
                    "Source": row_value_list[2],
                    "Target": row_value_list[3],
                }
                pdur_excel_dict["excel_dict"].update({row: dict})
                for dest in row_value_list[3].split(","):
                    # RX / TX 怎么确认？
                    dest_list.append(self.get_pdu_name(dict["Name"], project_name, dest) + "_TX")
                # if dict["Source"] not in dict["Target"]:
                #     dest_list.append(self.get_pdu_name(dict["Name"], project_name, dict["Source"]) + "_TX")
                src_name = self.get_pdu_name(dict["Name"], project_name, dict["Source"]) + "_RX"
                pdur_excel_dict["result_dict"].update({src_name: dest_list})

            return pdur_excel_dict

    def get_pdu_name(self, message_name, project_name, can_lin_name) -> str:
        if can_lin_name in ["BDCAN2", "BLECAN"]:
            can_lin_name += "_Ctrl"
        return message_name + "_o" + project_name + "_" + can_lin_name

    def excel_validate(self, dict: dict) -> bool:
        validate_result = True
        for key, value in dict.items():
            validate = True
            if value["Type"] != "PDU Gateway" and value["Type"] != "Signal Gateway":
                validate = False
            if "CAN" not in value["Source"] and "LIN" not in value["Source"]:
                validate = False
            target_list = value["Target"].split(",")
            for target in target_list:
                if "CAN" not in target and "LIN" not in target:
                    validate = False
            if validate is False:
                validate_result = False
                logger.info(f"{key, value} is invalid info!")
        return validate_result

    def pdur_excel_validate(self, dict: dict, buslist) -> bool:
        validate_result = True
        if 2 not in dict.keys():
            logger.error("PduRCfg.xlsx Header Information error!")
        if dict[2]["self_diag_req"] == 0xFFF:
            logger.error("PduRCfg.xlsx Header Information Self_Diag_Req Id is Empty!")
            validate_result = False
        if dict[2]["self_diag_rsp"] == 0xFFF:
            logger.error("PduRCfg.xlsx Header Information Self_Diag_Req Id is Empty!")
            validate_result = False
        if dict[2]["func_bus"] is None:
            logger.error("PduRCfg.xlsx Header Information Func_Req_Bus error!")
            validate_result = False
        elif dict[2]["func_bus"] not in buslist:
            logger.error("PduRCfg.xlsx Header Information Func_Req_Bus not Exist!")
            validate_result = False
        for key, Value in dict.items():
            if key == 2:
                continue
            if Value["SrcBus"] is None:
                logger.error(f" PduRCfg.xlsx row {key} SrcBus Info is Empty!")
                validate_result = False
            elif Value["SrcBus"] not in buslist:
                logger.error(f" PduRCfg.xlsx row {key} SrcBus Info error!")
                validate_result = False
            if Value["DstBus"] is None:
                logger.error(f" PduRCfg.xlsx row {key} DstBus Info is Empty!")
                validate_result = False
            elif Value["DstBus"] not in buslist:
                logger.error(f" PduRCfg.xlsx row {key} DstBus Info error!")
                validate_result = False
            if Value["SrcId"] == 0xFFF:
                logger.error(f" PduRCfg.xlsx row {key} SrcId Info is Empty!")
                validate_result = False
            elif Value["SrcId"] > 0x7FF:
                logger.error(f" PduRCfg.xlsx row {key} SrcId Info error!")
                validate_result = False
            if Value["DstId"] == 0xFFF:
                logger.error(f" PduRCfg.xlsx row {key} DstId Info is Empty!")
                validate_result = False
            elif Value["DstId"] > 0x7FF:
                logger.error(f" PduRCfg.xlsx row {key} DstId Info error!")
                validate_result = False
        return validate_result

    def get_valid_bus_name(self, file_path):
        Valid_list = []
        workbook = load_workbook(file_path)
        sheet = workbook["Sheet2"]
        for row in range(1, sheet.max_row + 1):
            Bus = self.get_cell_value(sheet, row, 1)
            Valid_list.append(Bus)
        return Valid_list
