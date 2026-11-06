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
通信矩阵(LDF)对象解析模块.

"""
import os
import inspect
import chardet
from typing import Dict
from ldfparser.parser import parse_ldf
from basic_func_module.base_logger import logger
from basic_func_module.file_handler.ldf.definition import AttributeLDF, MessageLDF, ProductIdLDF, SignalLDF


def get_message_node_name_and_direction(message, frame, nodes):
    """
    get message node_name and direction

    Args:
        message:  message
        frame: frame
        nodes: node

    Returns:
        Return a json object
    """

    if message.message_alias_name == "MasterReq":
        message.node_name = "LIN_MASTER_RESPONSE"
        message.direction = "LIN_MASTER_RESPONSE"
    elif message.message_alias_name == "SlaveResp":
        message.node_name = "LIN_SLAVE_RESPONSE"
        message.direction = "LIN_SLAVE_RESPONSE"
    else:
        message.node_name = frame.publisher.name
        message.direction = nodes[frame.publisher.name]


def get_db_dict(network, db):
    """
    Iterate over the db_dict to convert data to JSON object

    Args:
        db:  Dict obtained from the communication matrix file

    Returns:
        Return a json object

    """
    message_by_name_object_json: Dict[str, MessageLDF] = {}
    # get master and slave information
    nodes = {}
    nodes.update({db.get_master().name: "LIN_MASTER_RESPONSE"})
    for slave in list(db.get_slaves()):
        nodes.update({slave.name: "LIN_SLAVE_RESPONSE"})

    # get frame information
    frames = []
    frames.extend(list(db.get_unconditional_frames()))
    frames.extend(list(db.get_diagnostic_frames()))

    # get schedule_table information
    schedule_tables = {}
    number_of_schedule_tables = len(list(db.get_schedule_tables())) + 1
    is_exist_diag_table = 0
    for schedule_table in list(db.get_schedule_tables()):
        for schedule in schedule_table.schedule:
            if hasattr(schedule, "frame"):  # For normal frames
                schedule_tables.update({schedule.frame.name: schedule.delay})
            else:  # For diag frames
                for schedule in range(len(schedule_table.schedule)):
                    is_exist_diag_table = 1
                    schedule_name = ["MasterReq", "SlaveResp"]
                    schedule_tables.update({schedule_name[schedule]: schedule_table.schedule[schedule].delay})
    if is_exist_diag_table == 1:
        number_of_schedule_tables += 1
    else:
        number_of_schedule_tables += 2

    for frame in frames:
        signal_name_dict: Dict[str, SignalLDF] = {}
        for i in range(len(frame.signal_map)):
            signal_object = SignalLDF(
                signal_alias_name=frame.signal_map[i][1].name,
                signal_name=frame.signal_map[i][1].name + "_o" + frame.name + "_o" + network,
                initial=frame.signal_map[i][1].init_value,
                length=frame.signal_map[i][1].width,
                start=frame.signal_map[i][0],
            )
            signal_name_dict[signal_object.signal_name] = signal_object
        if hasattr(frame.publisher, "product_id"):
            product_id = ProductIdLDF(
                function_id=frame.publisher.product_id.function_id,
                supplier_id=frame.publisher.product_id.supplier_id,
                variant=frame.publisher.product_id.variant,
            )
        else:
            product_id = None
        if hasattr(frame.publisher, "configured_nad"):
            attributes = AttributeLDF(
                configured_nad=hex(frame.publisher.configured_nad),
                initial_nad=hex(frame.publisher.initial_nad),
                lin_protocol=frame.publisher.lin_protocol,
                n_as_timeout=str(int(frame.publisher.n_as_timeout / db.master.timebase)),
                n_cr_timeout=str(int(frame.publisher.n_cr_timeout / db.master.timebase)),
                p2_min=str(int(frame.publisher.p2_min / db.master.timebase)),
                st_min=str(int(frame.publisher.st_min / db.master.timebase)),
                product_id=product_id,
            )
        else:
            attributes = AttributeLDF(
                jitter=db.master.jitter,
                timebase=db.master.timebase,
            )

        if frame.name in schedule_tables:
            delay_time_from_schedule_table = schedule_tables[frame.name]
        else:
            delay_time_from_schedule_table = -1  # if the frame is not in the schedule table,delay = 0

        message = MessageLDF(
            message_alias_name=frame.name,
            bus_name=network,
            message_name=frame.name + "_o" + network,
            frame_id=frame.frame_id,
            length=frame.length,
            node_name=None,
            direction=None,
            delay_time=delay_time_from_schedule_table,
            attributes=attributes,
            signals=signal_name_dict,
        )
        get_message_node_name_and_direction(message, frame, nodes)
        message_by_name_object_json[message.message_name] = message

    return message_by_name_object_json, number_of_schedule_tables


def schedule_tables_to_dict(db_ldf):
    sche_table_dict = {}
    for sche_table in db_ldf.get_schedule_tables():
        table_name = sche_table.name
        table_item_list = []
        for table_entry in sche_table.schedule:
            if hasattr(table_entry, "frame"):
                table_item_list.append({"name": table_entry.frame.name, "delay": table_entry.delay})
            else:
                table_item_list.append({"name": table_entry.__class__.__name__, "delay": table_entry.delay})
        sche_table_dict[table_name] = table_item_list

    return sche_table_dict


def get_lin_master_name(db_ldf):
    return db_ldf.get_master().name


def get_lin_slaves_name(db_ldf):
    name_list = []
    slaves = db_ldf.get_slaves()
    for slave_obj in slaves:
        name_list.append(slave_obj.name)
    return name_list


def parse_ldf_file(ldf_file, num_of_ldf):
    """
    Parse ldf file with ldfparser
    """
    if os.path.exists(ldf_file):
        logger.debug(f"Load {ldf_file}")
        try:
            ldf_details_by_ldf_name_dict = {"ldf_name": "", "number_of_schedule_tables": "", "details": ""}
            file = open(ldf_file, "rb")
            encoding_message = chardet.detect(file.read())
            db_ldf = parse_ldf(path=ldf_file, encoding=encoding_message["encoding"])
            network = ""
            if db_ldf.channel:
                network = db_ldf.channel
            else:
                network = f"LIN{num_of_ldf:02}"
                logger.debug(f"Cannot parse channel name in {ldf_file}, set it to {network}")
            message_by_name_object_json, table_num = get_db_dict(
                network, db_ldf
            )  # convert the resulting dict into a json object
            ldf_details_by_ldf_name_dict["ldf_name"] = ldf_file.split("/")[-1]
            ldf_details_by_ldf_name_dict["channel_name"] = network
            ldf_details_by_ldf_name_dict["number_of_schedule_tables"] = table_num
            ldf_details_by_ldf_name_dict["details"] = message_by_name_object_json
            ldf_details_by_ldf_name_dict["schedule_tables"] = schedule_tables_to_dict(db_ldf)
            ldf_details_by_ldf_name_dict["master_name"] = get_lin_master_name(db_ldf)
            ldf_details_by_ldf_name_dict["slaves_name"] = get_lin_slaves_name(db_ldf)
            return ldf_details_by_ldf_name_dict
        except NotImplementedError as e:
            frame_info = inspect.trace()[-1]
            filename = os.path.basename(frame_info.filename)
            error_line = frame_info.lineno
            error_code = frame_info.code_context[0].strip()
            logger.error(f"NotImplementedError: {filename}:{error_line} {error_code} {e}")
    else:
        logger.error(f"File {ldf_file} does not exist")


def gather_all_ldf_files(ldf_dir):
    """
    Gather all ldf files in given directory
    """
    if not os.path.exists(ldf_dir):
        logger.error(f"Path {ldf_dir} does not exist")
        return

    ldf_file_list = []
    for dirpath, _, filenames in os.walk(ldf_dir):
        for filename in filenames:
            if filename.split(".")[-1] == "ldf":
                ldf_file_list.append(os.path.join(dirpath, filename))

    return ldf_file_list


def import_config_from_ldf(ldf_file_list):
    """
    Parse all LDF files in the given list

    Args:
        ldf_file_list: ldf file list

    Returns:
        Return a dict object that contains all the information in the ldf file
    """

    ldfs_details_by_ldf_name_list = []
    num_of_ldf = 0

    for ldf_file in ldf_file_list:
        ldfs_details_by_ldf_name_list.append(parse_ldf_file(ldf_file, num_of_ldf))
        num_of_ldf += 1

    return ldfs_details_by_ldf_name_list


def get_config_from_comm_matrix_file(sys_config: dict) -> dict:
    """
    Process all communication matrix files

    Args:

    Returns:
        Return a dict

    """
    ldf_file_list = gather_all_ldf_files(os.path.join(sys_config["config_path"], "ldf"))
    return import_config_from_ldf(ldf_file_list)
