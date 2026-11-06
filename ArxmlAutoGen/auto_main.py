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
from ScriptLib.create_arxml_utility import CreateArxmlUtility
from ScriptLib.get_excel_info import  ReadXlsxInfo
from ScriptLib.creat_arxml_info import ArxmlGenerator

PROJECT_NAME = 'Demo'
LOG_DIR = 'log'
log_file = os.path.join(f'{LOG_DIR}',f'ARXML-log-{PROJECT_NAME}.log')
LOG_DIVIDER = '-' * 37
def main():
    utility = CreateArxmlUtility()
    utility.mkdir(LOG_DIR)
    logger = utility.getLogger(log_file)
    try:
        logger.info(f'生成项目：{PROJECT_NAME}')
        logger.info(f'{LOG_DIVIDER}start{LOG_DIVIDER}')
        # 1. Read and process Excel data
        excel_reader = ReadXlsxInfo()
        excel_reader.xlsx_info_main(logger)
        # 2. Generate ARXML files
        arxml_maker = ArxmlGenerator()
        arxml_maker.generate_arxml_files(excel_reader.swc_infos,logger)
        logger.info(f'{LOG_DIVIDER}stop{LOG_DIVIDER}')
    except Exception as e:
        logger.error(f"Exception occurred:{e}")
        raise  

if __name__ == '__main__':
    main()