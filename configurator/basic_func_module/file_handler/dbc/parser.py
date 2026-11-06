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
通信矩阵(DBC)对象解析模块.

"""
import os
import inspect
import chardet
import cantools
from typing import Dict
from basic_func_module.base_logger import logger
from basic_func_module.file_handler.dbc.definition import MessageDBC, SignalDBC, SignalGroupsDBC


def get_db_dict(db):
    """
    Iterate over the db_dict to convert data to JSON object

    Args:
        db:  Dict obtained from the communication matrix file

    Returns:
        Return a json object

    """

    message_by_name_object_json: Dict[str, MessageDBC] = {}
    for i in range(len(db.messages)):
        signal_name_dict: Dict[str, SignalDBC] = {}
        for j in range(len(db.messages[i].signals)):
            signal = SignalDBC(
                signal_alias_name=db.messages[i].signals[j].name,
                signal_name=db.messages[i].signals[j].name
                + "_o"
                + db.messages[i].name
                + "_o"
                + db.messages[i].bus_name,
                initial=db.messages[i].signals[j].initial,
                start=db.messages[i].signals[j].start,
                is_signed=db.messages[i].signals[j].is_signed,
                length=db.messages[i].signals[j].length,
                maximum=db.messages[i].signals[j].maximum,
                minimum=db.messages[i].signals[j].minimum,
                is_float=db.messages[i].signals[j].is_float,
                offset=db.messages[i].signals[j].offset,
                scale=db.messages[i].signals[j].scale,
                is_multiplexer=db.messages[i].signals[j].is_multiplexer,
                multiplexer_ids=db.messages[i].signals[j].multiplexer_ids,
                multiplexer_signal=db.messages[i].signals[j].multiplexer_signal,
                invalid=db.messages[i].signals[j].invalid,
                spn=db.messages[i].signals[j].spn,
                unit=db.messages[i].signals[j].unit,
                byte_order=db.messages[i].signals[j].byte_order,
                choices=db.messages[i].signals[j].choices,
                signal_attributes=db.messages[i].signals[j].dbc.attributes,
                receivers=db.messages[i].signals[j].receivers,
            )
            signal_name_dict[signal.signal_name] = signal
        signal_groups_dict: Dict[str, SignalGroupsDBC] = {}
        has_signal_groups = 0
        if 0 != len(db.messages[i].signal_groups):
            has_signal_groups = 1
            for k in range(len(db.messages[i].signal_groups)):
                signal_groups = SignalGroupsDBC(
                    signal_group_name=db.messages[i].signal_groups[k].name,
                    repetitions=db.messages[i].signal_groups[k].repetitions,
                    group_signals_name=db.messages[i].signal_groups[k].signal_names,
                )
                signal_groups_dict[signal_groups.signal_group_name] = signal_groups
        message = MessageDBC(
            message_alias_name=db.messages[i].name,
            bus_name=db.messages[i].bus_name,
            message_name=db.messages[i].name + "_o" + db.messages[i].bus_name,
            frame_id=db.messages[i].frame_id,
            header_byte_order=db.messages[i].header_byte_order,
            header_id=db.messages[i].header_id,
            is_container=db.messages[i].is_container,
            is_extended_frame=db.messages[i].is_extended_frame,
            is_fd=db.messages[i].is_fd,
            length=db.messages[i].length,
            protocol=db.messages[i].protocol,
            send_type=db.messages[i].send_type,
            senders=db.messages[i].senders,
            has_signal_groups=has_signal_groups,
            signal_groups=signal_groups_dict,
            message_attributes=db.messages[i].dbc.attributes,
            signals=signal_name_dict,
        )
        message_by_name_object_json[message.message_name] = message

    message_by_name_object_json_tmp = sorted(message_by_name_object_json.items())
    message_by_name_object_json_sorted: Dict[str, MessageDBC] = {}
    for i in range(len(message_by_name_object_json_tmp)):
        message_by_name_object_json_sorted[message_by_name_object_json_tmp[i][0]] = message_by_name_object_json_tmp[i][
            1
        ]

    return message_by_name_object_json_sorted


def parse_dbc_file(dbc_file):
    """
    Parse dbc file with cantools
    """
    if os.path.exists(dbc_file):
        logger.debug(f"Load {dbc_file}")
        try:
            dbc_details_by_dbc_name_dict = {"dbc_name": "", "details": ""}
            file = open(dbc_file, "rb")
            encoding_message = chardet.detect(file.read())
            db_dbc = cantools.database.load_file(dbc_file, encoding=encoding_message["encoding"])
            message_by_name_object_json = get_db_dict(db_dbc)  # convert the resulting dict into a json object
            dbc_attributes_value_dict = get_db_attributes_value(db_dbc)
            dbc_details_by_dbc_name_dict["dbc_name"] = os.path.basename(dbc_file)
            dbc_details_by_dbc_name_dict["details"] = {
                key: value for key, value in message_by_name_object_json.items() if len(value.senders)
            }
            dbc_details_by_dbc_name_dict["attributes"] = dbc_attributes_value_dict
            dbc_details_by_dbc_name_dict["node_list"] = [
                node for node in dbc_attributes_value_dict["node"]["define_value"].keys()
            ]
            dbc_details_by_dbc_name_dict["node_list"].sort()
            for msg_name, msg_value in (
                dbc_details_by_dbc_name_dict["details"].copy().items()
            ):  # messages and signals attributes default value set
                for attr_name, attr_value in dbc_details_by_dbc_name_dict["attributes"]["message"][
                    "default_value"
                ].items():
                    if attr_name not in msg_value.message_attributes.keys():
                        dbc_details_by_dbc_name_dict["details"][msg_name].message_attributes[attr_name] = attr_value
                for sig_name, sig_val in msg_value.signals.items():
                    for attr_name, attr_value in dbc_details_by_dbc_name_dict["attributes"]["signal"][
                        "default_value"
                    ].items():
                        if attr_name not in sig_val.signal_attributes.keys():
                            dbc_details_by_dbc_name_dict["details"][msg_name].signals[sig_name].signal_attributes[
                                attr_name
                            ] = attr_value
            return dbc_details_by_dbc_name_dict
        except NotImplementedError as e:
            frame_info = inspect.trace()[-1]
            filename = os.path.basename(frame_info.filename)
            error_line = frame_info.lineno
            error_code = frame_info.code_context[0].strip()
            logger.error(f"NotImplementedError: {filename}:{error_line} {error_code} {e}")
    else:
        logger.error(f"File {dbc_file} does not exist")


def get_db_attributes_value(db):
    attributes_value_dict = {
        "network": {"default_value": {}, "define_value": {}},
        "node": {"default_value": {}, "define_value": {}},
        "message": {"default_value": {}},
        "signal": {"default_value": {}},
    }
    for attr_name, value in db.dbc.attribute_definitions.items():  # process attributes default value
        attr = {attr_name: Attributes(attr_name, value, None)}
        if value.type_name == "ENUM":
            if value.default_value in value.choices:
                idx = value.choices.index(value.default_value)
                attr[attr_name].value = idx
        else:
            attr[attr_name].value = value.default_value
        if value.kind is None:
            attributes_value_dict["network"]["default_value"].update(attr)
        elif value.kind == "BU_":
            attributes_value_dict["node"]["default_value"].update(attr)
        elif value.kind == "BO_":
            attributes_value_dict["message"]["default_value"].update(attr)
        elif value.kind == "SG_":
            attributes_value_dict["signal"]["default_value"].update(attr)
    for attr_name, value in db.dbc.attributes.items():  # process network attributes define value
        attributes_value_dict["network"]["define_value"].update({attr_name: value.value})
    for node in db.nodes:  # process nodes attributes define value
        node_attr = {node.name: {}}
        for attr_name, value in node.dbc.attributes.items():
            node_attr[node.name].update({attr_name: value.value})
        attributes_value_dict["node"]["define_value"].update(node_attr)
    return attributes_value_dict


def gather_all_dbc_files(dbc_dir):
    """
    Gather all dbc files in given directory
    """
    if not os.path.exists(dbc_dir):
        logger.error(f"Path {dbc_dir} does not exist")
        return

    dbc_file_list = []
    for dirpath, _, filenames in os.walk(dbc_dir):
        for filename in filenames:
            if filename.split(".")[-1] == "dbc":
                dbc_file_list.append(os.path.join(dirpath, filename))

    return dbc_file_list


def import_config_from_dbc(dbc_file_list):
    """
    Parse all DBC files in given dbc file list

    Args:
      dbc_file: dbc file path list

    Returns:
      Return a dict object that contains all the information in the dbc file
    """

    dbcs_details_by_dbc_name_list = []

    for dbc_file in dbc_file_list:
        dbcs_details_by_dbc_name_list.append(parse_dbc_file(dbc_file))

    return dbcs_details_by_dbc_name_list


def get_config_from_comm_matrix_file(sys_config: dict) -> dict:
    """
    Process all communication matrix files

    Args:

    Returns:
      Return a dict

    """
    dbc_file_list = gather_all_dbc_files(os.path.join(sys_config["config_path"], "dbc"))
    return import_config_from_dbc(dbc_file_list)


class Attributes:

    def __init__(self, name, definition, value):
        self.name = name
        self.definition = definition
        self.value = value
