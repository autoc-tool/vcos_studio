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
Parse cdd file for generating Dcm and Dem configuration json file

"""
import os
import cantools
from basic_func_module.base_logger import logger


def gather_all_cdd_files(cdd_dir):
    """
    Gather all cdd files in give directory
    """
    cdd_file_list = []
    if not os.path.exists(cdd_dir):
        logger.logger.error(f"Path {cdd_dir} does not exist")

    for dirpath, _, filenames in os.walk(cdd_dir):
        for filename in filenames:
            if filename.split(".")[-1] == "cdd":
                cdd_file_list.append(os.path.join(dirpath, filename))

    return cdd_file_list


def import_config_from_cdd(cdd_file_list):
    """
    Parse all CDD files in the given list

    Args:
        cdd_file_list: cdd file list

    Returns:
        Return a dict object that contains all the information in the cdd file
    """
    # If cdd file not exist, report an error
    if len(cdd_file_list) == 0:
        logger.error("Cannot find cdd file!")
    # If find many cdd file, only load one of them
    cdd_file = cdd_file_list[0]
    if len(cdd_file_list) > 1:
        logger.info(f"Find more than one cdd file, load {os.path.split(cdd_file)[1]}")

    db_cdd = {}
    # Now we only have one cdd file
    if os.path.exists(cdd_file):
        logger.debug(f"Load {cdd_file}")
        try:
            db_cdd = cantools.database.load_file(cdd_file)
        except AssertionError as e:
            if "VersionError" in e.args[0]:
                logger.ui_error(e.args[0])
            raise e

    return db_cdd


def get_config_from_comm_matrix_file(sys_config: dict) -> dict:
    """
    Process all communication matrix files

    Args:

    Returns:
      Return a dict

    """

    # Parse cdd file only if Dem, Dcm or CanTp module is enabled
    if set(["Dem", "Dcm", "CanTp"]).intersection(set(sys_config["bsw_import_modules_list"])):
        return import_config_from_cdd(gather_all_cdd_files(os.path.join(sys_config["config_path"], "cdd")))
    else:
        return
