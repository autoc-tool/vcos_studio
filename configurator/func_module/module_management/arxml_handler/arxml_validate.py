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
from basic_func_module.file_validation.arxml_validator import ArxmlFileValidator
from func_module.module_management.base_config import BASE_CONFIG_PATH

SCHEMA_XSD_FILE = os.path.abspath(os.path.join(BASE_CONFIG_PATH, "autosar_cfg/AUTOSAR_00046.xsd"))

arxml_file_validator = ArxmlFileValidator()
arxml_file_validator.set_arxml_schema(SCHEMA_XSD_FILE)


class AswArxmlValidation:
    time_stat = {}

    @classmethod
    def validate_arxml_with_xsd(cls, file_list):
        total_result = True
        for arxml_file in file_list:
            # start_time = time.time()
            is_valid_xml_file = True
            try:
                arxml_file_validator.clear_log()
                result = arxml_file_validator.validate(arxml_file)
                is_valid_xml_file = result
                if not result:
                    logs = arxml_file_validator.log_list
                    for log in logs:
                        logger.error(f"error ARXML File: {log.file_name}")
                        logger.error(f"error Line: {log.line}")
                        logger.error(f"error Message: {log.message}")
            except Exception:
                is_valid_xml_file = False
                logger.exception("validate_arxml_with_xsd")
            if not is_valid_xml_file:
                logger.error(f"{arxml_file} : Validation FAILEd")
                total_result = False
                # end_time = time.time()
                # cls.time_stat.update({arxml_file:end_time-start_time})
            else:
                # end_time = time.time()
                # cls.time_stat.update({arxml_file:end_time-start_time})
                pass
        # with open('clstime_stat.json', 'w') as f:
        #     json.dump(cls.time_stat, f)
        return total_result


asw_arxml_validation = AswArxmlValidation()
