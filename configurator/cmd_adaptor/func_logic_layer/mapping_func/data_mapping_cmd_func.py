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
from time import time, strftime, localtime
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from func_module.mapping.data_mapping import DataMapping
from cmd_adaptor.data_management import data_management
from cmd_adaptor.func_logic_layer.load_save_project import LoadAndSaveProject
from cmd_adaptor.cmd_interaction.cmd_logger import logger
from openpyxl import load_workbook

CUR_FILE_PATH = os.path.dirname(os.path.realpath(__file__))


class DataMappingCmdFunc:

    log_export_table_header_list = [
        "Index",
        "Compatibility",
        "AutoMapping",
        "Component",
        "PortPrototype",
        "DataElement",
        "Signal",
        "PDU",
    ]
    no_mapping_port_table_header_list = ["Index", "Component", "PortPrototype", "DataElement"]
    auto_data_mapping_results = {"mapping_infos": {}, "port_num": 0, "signal_num": 0, "mapped_num": 0}
    common_brief_information = [
        [],
        ["Compatibility兼容性说明:"],
        ["", "Full: 名字全词匹配且数据类型一致"],
        ["", "Partial: 名字部分匹配且数据类型一致"],
        [
            "",
            "Full & Data Type Length Compatible: "
            "名字全词匹配且数据类型不一致,但长度兼容(DataElement长度不小于Signal的长度)",
        ],
        [
            "",
            "Partial & Data Type Length Compatible: "
            "名字部分匹配且数据类型不一致,但长度兼容(DataElement长度不小于Signal的长度)",
        ],
        ["Sheet简介:"],
        [
            'Sheet "Port匹配到1个Signal":',
            'Port匹配到1个Signal, "AutoMapping"为"True"表示已自动连接, "Index"为在每个Component中的编号',
        ],
        [
            'Sheet "Port匹配到多个Signal":',
            'Port匹配到多个Signal, "AutoMapping"为"True"表示已自动连接, '
            '"Index"为在每个Component中的编号, 同一个Port_DataElement编号相同',
        ],
        [
            'Sheet "Port匹配到1个Signal但数据长度不兼容":',
            "Port匹配到1个Signal, 但Signal的数据长度大于Port的数据类型长度,不连接",
        ],
        [
            'Sheet "Port未匹配到Signal":',
            'Port根据名字未匹配到对应的Signal, "Index"为在每个Component中的编号',
        ],  # noqa: E126
    ]

    @classmethod
    def auto_data_mapping(cls, args):
        logger.info("")
        logger.info("------Start executing auto data mapping ...")
        logger.info(
            f"Auto Data Mapping Command: components: {args.component}, "
            + f"direction: {args.direction}, "
            + f"prefix: {args.prefix}, postfix:{args.postfix}, "
            + f'ic: {getattr(args, "case_sensitive", False)}, '
            + f'iw: {getattr(args, "ignore_match_whole_word", False)}, '
            + f'ms: {getattr(args, "allow_multi_signal", False)}, '
            + f'log: {getattr(args, "log_save", False)}, '
            + f'comp: {getattr(args, "match_compatibility", False)}, '
            + f'file: {getattr(args, "File", "None")}'
        )
        start_time = time()
        formatted_time = strftime("%Y%m%d-%H%M%S", localtime(start_time))
        filter_conditions = {
            "components": args.component.split() if args.component else [],
            "direction": args.direction,
            "prefix": args.prefix if args.prefix is not None else "",
            "postfix": args.postfix if args.postfix is not None else "",
            "whole_word": not getattr(args, "ignore_match_whole_word", False),
            "case_sensitive": not getattr(args, "ignore_match_case", False),
            "allow_multi_signal": getattr(args, "allow_multi_signal", False),
            "log_save": getattr(args, "log_save", False),
            "match_compatibility": getattr(args, "match_compatibility", False),
            "file": getattr(args, "File", None),
        }
        if filter_conditions["file"] is not None:
            cls.auto_data_mapping_by_file_cmd(filter_conditions)
        else:
            cls.auto_data_mapping_by_params(filter_conditions, formatted_time)
        total_time = "%.3f" % (time() - start_time)
        logger.info(
            f"Finish executing AutoDataMapping in {total_time} seconds (include the time of log saving, if enabled)."
        )

    @classmethod
    def auto_data_mapping_by_params(cls, filter_conditions, formatted_time):
        datamapping_infos = DataMapping.get_datamapping_infos(
            data_management.autosar_asw_class,
            data_management.autosar_bsw_class,
            data_management.autosar_system_class,
            filter_conditions,
        )
        all_swc_ports = datamapping_infos[DataMapping.INFOS_INDEX.SWC_PORTS]
        system_signals_dict = datamapping_infos[DataMapping.INFOS_INDEX.SYSTEM_SIGNALS]
        swc_ports_to_mapping = DataMapping.port_to_mapping_filter(
            filter_conditions, list(all_swc_ports["all_port_data_s"].values())
        )
        system_signals_pre_processing = DataMapping._system_signals_pre_processing(
            system_signals_dict, filter_conditions
        )

        new_data_mappings_ports_dict = DataMapping.get_new_data_mappings_dict(
            swc_ports_to_mapping, system_signals_pre_processing, filter_conditions
        )
        sr_port_list = (
            new_data_mappings_ports_dict["1to1_full"]
            + new_data_mappings_ports_dict["1to1_partial"]
            + new_data_mappings_ports_dict["1toN"]
            + new_data_mappings_ports_dict["1to1_full_datalength_compatible"]
            + new_data_mappings_ports_dict["1to1_partial_datalength_compatible"]
        )
        sr_to_signal_mapping_dicts = DataMapping.get_sr_to_signal_mapping_dicts(sr_port_list)
        DataMapping.add_new_data_mappings_to_arxml(data_management.autosar_system_class, sr_to_signal_mapping_dicts)
        signals_num = (
            len(system_signals_dict["Tx"]["system_signal"])
            + len(system_signals_dict["Tx"]["system_signal_group"])
            + len(system_signals_dict["Rx"]["system_signal"])
            + len(system_signals_dict["Rx"]["system_signal_group"])
        )
        summary_info = [
            ["Port数量:", len(swc_ports_to_mapping)],
            ["Signal数量:", signals_num],
            ["自动连接数量:", len(sr_to_signal_mapping_dicts)],
        ]
        mapping_infos_dict = cls.auto_data_mapping_log_process(
            new_data_mappings_ports_dict, formatted_time, summary_info, filter_conditions
        )
        cls.auto_data_mapping_info_collection(
            mapping_infos_dict, len(swc_ports_to_mapping), signals_num, len(sr_to_signal_mapping_dicts)
        )

    @classmethod
    def auto_data_mapping_by_file_cmd(cls, filter_conditions):
        file_mapping_info = DataMapping.auto_data_mapping_by_file(
            data_management.autosar_asw_class,
            data_management.autosar_bsw_class,
            data_management.autosar_system_class,
            filter_conditions["file"],
        )
        cls.auto_data_mapping_by_file_log_save(file_mapping_info, filter_conditions["file"])

    @classmethod
    def auto_data_mapping_by_file_log_save(cls, file_mapping_info, src_file_path):
        all_mapping_success = True
        if not file_mapping_info:
            return
        dest_file = f"{src_file_path}.mapping_result.xlsx"
        workbook = load_workbook(filename=src_file_path)
        sheet = workbook[workbook.sheetnames[0]]
        max_column = sheet.max_column
        find_pdu_column_index = max_column + 1
        result_column_index = max_column + 2
        reason_column_index = max_column + 3
        sheet.cell(row=1, column=find_pdu_column_index, value="find_pdu")
        sheet.cell(row=1, column=result_column_index, value="result")
        sheet.cell(row=1, column=reason_column_index, value="reason")
        for idx in range(len(file_mapping_info)):
            mapping_result = file_mapping_info[idx].get("mapping_result", {"result": "N/A", "reason": ""})
            all_mapping_success = False if mapping_result["result"] is False else all_mapping_success
            # row比idx大2，因为idx从0开始，Excel从1开始且表头占1行
            sheet.cell(
                row=idx + 2, column=find_pdu_column_index, value=",".join(file_mapping_info[idx].get("find_pdu", []))
            )
            sheet.cell(row=idx + 2, column=result_column_index, value=mapping_result["result"])
            sheet.cell(row=idx + 2, column=reason_column_index, value=mapping_result["reason"])
        # 保存为新的Excel文件
        workbook.save(dest_file)
        if all_mapping_success is True:
            logger.info(f"All ports data mapping successfully! Log file: {dest_file}")
        else:
            logger.error(f"Some Ports data mapping unsuccessfully! Log file: {dest_file}")

    @classmethod
    def auto_data_mapping_log_process(cls, ports, formatted_time, summary_info, filter_conditions):
        save_log = filter_conditions.get("log_save", False)
        log_info_dict = cls.auto_data_mapping_log_print(ports)
        if save_log is True:
            components = "-".join(str(x) for x in filter_conditions["components"])
            file_path = os.path.abspath(
                f"{data_management.sys_info_class.log_path}/AutoDataMapping_Log_{components}_{formatted_time}.xlsx"
            )
            log_save_start_time = time()
            cls.auto_data_mapping_log_save(log_info_dict, file_path, summary_info + cls.common_brief_information)
            log_save_total_time = "%.3f" % (time() - log_save_start_time)
            logger.info(f"Save data mapping log file: {file_path} in {log_save_total_time} seconds ...")
        return log_info_dict

    @classmethod
    def auto_data_mapping_info_collection(cls, mapping_infos_dict, port_num, signal_num, new_mapped_num):
        cls.auto_data_mapping_results["port_num"] += port_num
        cls.auto_data_mapping_results["mapped_num"] += new_mapped_num
        cls.auto_data_mapping_results["signal_num"] = signal_num

        for connection_type, mapping_list in mapping_infos_dict.items():
            if connection_type not in cls.auto_data_mapping_results["mapping_infos"].keys():
                cls.auto_data_mapping_results["mapping_infos"][connection_type] = mapping_list
            else:
                cls.auto_data_mapping_results["mapping_infos"][connection_type].extend(mapping_list)

    @classmethod
    def auto_data_mapping_all_logs_save(cls):
        summary_info = [
            ["Port数量:", cls.auto_data_mapping_results["port_num"]],
            ["Signal数量:", cls.auto_data_mapping_results["signal_num"]],
            ["自动连接数量:", cls.auto_data_mapping_results["mapped_num"]],
        ]

        log_save_start_time = time()
        formatted_time = strftime("%Y%m%d-%H%M%S", localtime(log_save_start_time))
        file_path = os.path.abspath(
            f"{data_management.sys_info_class.log_path}/AutoDataMapping_Log_All_{formatted_time}.xlsx"
        )
        cls.auto_data_mapping_log_save(
            cls.auto_data_mapping_results["mapping_infos"], file_path, summary_info + cls.common_brief_information
        )
        log_save_total_time = "%.3f" % (time() - log_save_start_time)
        logger.info(f"Save data mapping log file: {file_path} in {log_save_total_time} seconds ...")

    @classmethod
    def auto_data_mapping_log_print(cls, ports):

        def to_log_dict(idx, signal_idx):
            rv = dict.fromkeys(cls.log_export_table_header_list)
            rv["Index"] = idx
            rv["Compatibility"] = port["signals_recommend"][signal_idx]["compatibility"].value[1]
            rv["AutoMapping"] = str(port["signals_recommend"][signal_idx]["auto_mapping"])
            rv["Component"] = port["Component"]
            rv["PortPrototype"] = port["Name"]
            rv["DataElement"] = port["DATA-ELEMENT-REF"]["name"]
            rv["Signal"] = ""
            rv["PDU"] = port["signals_recommend"][signal_idx]["signal"]["pdu"]

            if port["allowable_signal_type"] == "system_signal_group":
                type_mappings_str = "\n"
                for _, mapping in port["signals_recommend"][signal_idx]["signal"]["type_mappings_brief"].items():
                    type_mappings_str += (
                        f'{mapping["group_name"]}.{mapping["system_signal"]}->'
                        f'{mapping["port_name"]}.{mapping["implementation_record_element"]};\n'
                    )
                rv["Signal"] = type_mappings_str
            else:
                rv["Signal"] = port["signals_recommend"][signal_idx]["signal"]["system_signal"]
            return rv

        def to_no_mapping_log_dict(idx):
            rv = dict.fromkeys(cls.no_mapping_port_table_header_list)
            rv["Index"] = idx
            rv["Component"] = port["Component"]
            rv["PortPrototype"] = port["Name"]
            rv["DataElement"] = port["DATA-ELEMENT-REF"]["name"]
            return rv

        def dict_to_log_str(mapping_info):
            log_str = ""
            for key, value in mapping_info.items():
                item_str = f"{key}: {value}, "
                log_str += item_str
            if log_str.endswith(", "):
                log_str = log_str[:-2]
            return log_str

        one_to_one_auto_connect_log = []
        one_to_n_auto_match_log = []
        no_mapping_port_log = []
        datalength_imcompatible_1to1 = []

        port_to_signal_1to1 = (
            ports["1to1_full"]
            + ports["1to1_partial"]
            + ports["1to1_full_datalength_compatible"]
            + ports["1to1_partial_datalength_compatible"]
        )
        for idx, port in enumerate(port_to_signal_1to1):
            one_to_one_auto_connect_log.append(to_log_dict(idx + 1, 0))

        for idx, port in enumerate(ports["1toN"]):
            for sig_idx in range(len(port["signals_recommend"])):
                one_to_n_auto_match_log.append(to_log_dict(idx + 1, sig_idx))

        for idx, port in enumerate(ports["1to1_datalength_imcompatible"]):
            datalength_imcompatible_1to1.append(to_log_dict(idx + 1, 0))
        for idx, port in enumerate(ports["no_mapping"]):
            no_mapping_port_log.append(to_no_mapping_log_dict(idx + 1))

        for log_dict in one_to_one_auto_connect_log:
            print(dict_to_log_str(log_dict))

        if len(one_to_n_auto_match_log):
            print("\n## The following ports have multiple signal matches##")
        for log_dict in one_to_n_auto_match_log:
            print("Warning(1:N), " + dict_to_log_str(log_dict))
        if len(datalength_imcompatible_1to1):
            print(
                "\n## The following ports have one signal name matches. "
                + " But data type length imcompatible(signal > port data)! ##"
            )
            for log_dict in datalength_imcompatible_1to1:
                print(dict_to_log_str(log_dict))
        return {
            "one_to_one_auto_connect": one_to_one_auto_connect_log,
            "one_to_n_auto_match": one_to_n_auto_match_log,
            "one_to_one_datalength_imcompatible": datalength_imcompatible_1to1,
            "no_mapping_port": no_mapping_port_log,
        }

    @classmethod
    def auto_data_mapping_log_save(cls, log_info_dict, file_path, summary_info):

        def write_sheet(sheet_obj, log_list):
            for num, log_info in enumerate(log_list):
                if isinstance(log_info, dict):
                    cls.write_row_data(sheet_obj, num + table_header_row + 1, list(log_info.values()))
                else:
                    cls.write_row_data(sheet_obj, num + table_header_row + 1, log_info)
            cls.set_column_widths(sheet_obj)

        workbook = Workbook()
        sheet = workbook.active
        workbook.remove(sheet)
        table_header_row = 1

        sheet = workbook.create_sheet(title="Summary Info")
        write_sheet(sheet, summary_info)
        # port:Signal 1:1自动连接信息保存
        sheet = workbook.create_sheet(title="Port匹配到1个Signal")
        cls.write_row_data(sheet, table_header_row, cls.log_export_table_header_list, True)
        write_sheet(sheet, log_info_dict["one_to_one_auto_connect"])

        # port匹配到多个Signal，未自动连接的信息
        sheet = workbook.create_sheet(title="Port匹配到多个Signal")
        cls.write_row_data(sheet, table_header_row, cls.log_export_table_header_list, True)
        write_sheet(sheet, log_info_dict["one_to_n_auto_match"])

        sheet = workbook.create_sheet(title="Port匹配到1个Signal但数据长度不兼容")
        cls.write_row_data(sheet, table_header_row, cls.log_export_table_header_list, True)
        write_sheet(sheet, log_info_dict["one_to_one_datalength_imcompatible"])
        # port未匹配到Signal
        sheet = workbook.create_sheet(title="Port未匹配到Signal")
        cls.write_row_data(sheet, table_header_row, cls.no_mapping_port_table_header_list, True)
        write_sheet(sheet, log_info_dict["no_mapping_port"])

        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        workbook.save(file_path)
        return file_path
        # os.startfile(f"{CUR_FILE_PATH}/auto_data_mapping_{formatted_time}.xlsx")

    @classmethod
    def write_row_data(cls, sheet, row_num, row_data, is_bold=False):
        header_font = Font(bold=is_bold)
        header_alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        header_row = []

        for value in row_data:
            cell = sheet.cell(row=row_num, column=len(header_row) + 1, value=value)
            cell.font = header_font
            cell.alignment = header_alignment
            header_row.append(cell)

    @classmethod
    def set_column_widths(cls, sheet):
        for column in sheet.columns:
            max_length = 0
            column_name = column[0].column_letter
            for cell in column:
                if cell.coordinate in sheet.merged_cells:
                    continue
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            adjusted_width = (max_length + 2) * 1.2
            sheet.column_dimensions[column_name].width = adjusted_width

    @classmethod
    def execute_auto_data_mapping_command(cls, args):
        LoadAndSaveProject.data_mapping_load_project(args.Project)
        cls.auto_data_mapping(args)
        logger.info("start saving arxml ...")
        LoadAndSaveProject.data_mapping_save_project()
        logger.info("finish saving arxml ...")
