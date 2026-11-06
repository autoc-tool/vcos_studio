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
"""
appl对象解析模块.

解析输入的配置文件, 然后生成config.json.
"""

import os
from openpyxl import load_workbook

CUR_FILE_PATH = os.path.dirname(__file__)


def parse_arg_datatype_data_mapping(port, port_name, category, signals_and_signalgroups):
    """
    Parse and get arg's datatype dict

    Arg:
      port: port from EXCEL
      port_name: port name
      category: datatype's category
      signals_and_signalgroups: all signals and signalgroups that are mapped

    Return:
      a dictionary of datatype's name, category and basetype
    """

    datatype = {"name": port_name, "category": ""}
    if category == "STRUCTURE":
        datatype["category"] = "STRUCTURE"
        datatype["members"] = []
        for i in range(len(signals_and_signalgroups)):
            if port_name == signals_and_signalgroups[i]["signal_name"]:
                for j in range(len(signals_and_signalgroups[i]["signals"])):
                    datatype["members"].append({
                        "name": signals_and_signalgroups[i]["signals"][j]["signal_name"],
                        "basetype": signals_and_signalgroups[i]["signals"][j]["type"],
                        "size": 8
                    })
    elif category == "TYPE_REFERENCE":
        datatype["category"] = "TYPE_REFERENCE"
        datatype["basetype"] = port["data_type"]
        datatype["size"] = 8
    else:
        datatype["category"] = "ARRAY"
        datatype["basetype"] = "uint8"
        datatype["size"] = 8

    return datatype


def parse_data_mapping_sheet_from_excel(xlsx_file):
    """
    Parse DataMapping Sheet in Data_Mapping.xlsx

    Arg:
      xlsx_file: the Excel file to be parsed

    Return:
      a dictionary of all ports
    """
    signals = {}
    wb = load_workbook(xlsx_file)
    for ws in wb.worksheets:
        if ws.title != "DataMapping":
            continue
        for i, row in enumerate(ws.rows):
            port = {}
            if i == 0:
                continue  # pass the title row
            signal_name = row[0].value
            if signal_name is None:
                break  # pass the blank row
            for cell in row:
                port[ws.cell(1, cell.column).value] = cell.value
            signals[signal_name] = port

    return signals


def get_port_name(port, signals_and_signalgroups):
    """
    Get all the ports. If it is a signal group,
    the signal group name will be used as the port name.

    Arg:
      port: port from EXCEL;
      signals_and_signalgroups: all signals and signalgroups that are mapped.

    Return:
      a dictionary of all ports.
    """
    for i in range(len(signals_and_signalgroups)):
        if signals_and_signalgroups[i]["signal_name"] == port["port_name"]:
            port_name = port["port_name"]
            category = "TYPE_REFERENCE"
            if "double64" == port["data_type"]:
                category = "ARRAY"
            break
        else:
            for k in range(len(signals_and_signalgroups[i]["signals"])):
                if signals_and_signalgroups[i]["signals"][k]["signal_name"] == port["port_name"]:
                    port_name = port["signal_group_name"]
                    category = "STRUCTURE"
                    break

    return port_name, category


def get_set_timeout_signals_dict(port, port_name, timeout_signals_dict):
    """
    Get all the ports. If it is a signal group,
    the signal group name will be used as the port name.

    Arg:
      port: port from EXCEL;
      timeout_signals_dict: all timeout signals.

    """

    if port["timeout"]:
        timeout_signals = dict.fromkeys(["port_name", "timeout", "port_alias_name", "function"])
        timeout_signals["port_name"] = port_name
        timeout_signals["timeout"] = port["timeout"]
        timeout_signals["port_alias_name"] = port_name + "_o" + port["message_name"] + "_o" + port["network"]
        timeout_signals["function"] = "ComTimeoutNotification" + "_" + port_name + "_o" + port[
            "message_name"] + "_o" + port["network"] + "_" + port["direction"]
        timeout_signals_dict[port_name] = timeout_signals


def get_signals_and_signalgroups(signals):
    """
    Get the signal and SignalGroup for which Data Mapping has been done.

    As follows:
    [
      {
        "signal_name": "***",
        "softwareCompositionRef": "***",
        "componentPrototypeRef": "***",
          "portPrototypeRef": "***",
        "is_group": "NO"
        "type": "",
        "runnable": "",
        "trigger_mode": "",
      },
      ...
      {
        "signal_name": "***",
        "softwareCompositionRef": "***",
        "componentPrototypeRef": "***",
        "portPrototypeRef": "***",
        "is_group": "YES",
        "type": "",
        "runnable": "",
        "trigger_mode": "",
        "signals":
        [
          {
            "signal_name": "***",
            "recordElementRef": "***",
          },
          {
            "signal_name": "***",
            "recordElementRef": "***",
          }
        ]
      }
    ]

    Arg:
      signals : all signals.

    Return:
      Returns a list of signals and signalGroups.
    """

    signals_and_signalgroups_dict = {}
    signals_tmp = signals

    for signal in signals.values():
        signals_and_signalgroups = {
            "signal_name": "",
            "softwareCompositionRef": "",
            "componentPrototypeRef": "",
            "portPrototypeRef": "",
            "is_group": "",
            "type": "",
            "runnable": "",
            "trigger_mode": "",
            "signals": []
        }
        if "None" != signal["CreatePortFromSignal"]:
            signals_and_signalgroups["is_group"] = signal["SignalCategory"]
            signals_and_signalgroups["message_name"] = signal["Message"]
            signals_and_signalgroups["network"] = signal["Network"]
            signals_and_signalgroups["runnable"] = signal["MappingPortToSWC"].split(",")[1]
            signals_and_signalgroups["trigger_mode"] = signal["MappingPortToSWC"].split(",")[2]
            if "Signal" == signal["SignalCategory"]:
                signals_and_signalgroups["signal_name"] = signal["NetworkSignal"]
                signals_and_signalgroups["type"] = signal["DataType"]
            elif "SignalGroup" == signal["SignalCategory"]:
                signals_and_signalgroups["signal_name"] = signal["SignalGroupName"]
                for signal_tmp in signals_tmp.values():
                    signalgroups_signal = {"signal_name": "", "recordElementRef": "", "type": ""}
                    if signal["SignalGroupName"] == signal_tmp["SignalGroupName"]:
                        signalgroups_signal["signal_name"] = signal_tmp["NetworkSignal"]
                        signalgroups_signal["type"] = signal_tmp["DataType"]
                        signals_and_signalgroups["signals"].append(signalgroups_signal)
            signals_and_signalgroups_dict[signals_and_signalgroups["signal_name"]] = signals_and_signalgroups

    return list(signals_and_signalgroups_dict.values())


def parse_data_mapping_signals(signals, signals_and_signalgroups):
    """
    Processing signals from data mapping excel.

    Arg:
      signals: signals from EXCEL;
      signals_and_signalgroups: all signals and signalgroups that are mapped.

    Return:
      Returns all mapped ports and their mappings,
      and returns all ports that are set to On_data_reception.
    """

    timeout_signals_dict = {}

    for signal in signals.values():
        signal_name = signal["NetworkSignal"]
        message_name = signal["Message"]
        network = signal["Network"]
        direction = signal["Direction"]
        signal_category = signal["SignalCategory"]
        data_type = signal["DataType"]
        signal_group_name = signal["SignalGroupName"]
        timeout = signal["Timeout"]

        port = {
            "port_name": signal_name,
            "message_name": message_name,
            "network": network,
            "direction": direction,
            "signal_category": signal_category,
            "data_type": data_type,
            "signal_group_name": signal_group_name,
            "timeout": timeout,
        }
        get_set_timeout_signals_dict(port, signal_name, timeout_signals_dict)

    return list(timeout_signals_dict.values())


def get_data_mapping_config_from_excel(xlsx_file):
    """
    Get data_mapping from Excel file(Data_Mapping.xlsx).

    Arg:
      xlsx_file: the Excel file to be parsed.

    Return:
      a dictionary of data_mapping_cfg.
    """

    signals = parse_data_mapping_sheet_from_excel(xlsx_file)
    signals_and_signalgroups = get_signals_and_signalgroups(signals)
    timeout_signals_dict = parse_data_mapping_signals(signals, signals_and_signalgroups)

    data_mapping_cfg = {
        "timeout_signals_dict": timeout_signals_dict,
    }

    return data_mapping_cfg


def get_config_dict(sys_config, cfg_dict: dict) -> dict:
    """
    get config dict from parsered Excel file.
    """
    config_dict = dict.fromkeys(["data_mapping_config"])
    data_mapping_config_file = os.path.join(sys_config["config_path"], "Rte/Data_Mapping.xlsx")

    data_mapping_config = get_data_mapping_config_from_excel(data_mapping_config_file)

    config_dict["data_mapping_config"] = data_mapping_config

    return config_dict
