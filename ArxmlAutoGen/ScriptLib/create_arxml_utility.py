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

import logging
import os

class CreateArxmlUtility:
    """Utility class for ARXML file creation operations."""
    @staticmethod
    def mkdir(dir):
        if not os.path.exists(dir):
            os.makedirs(dir)

    @staticmethod
    def getLogger(logfile):
        logger = logging.getLogger()        
        hdlr = logging.FileHandler(logfile, 'w+')
        console = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
        hdlr.setFormatter(formatter)
        console.setFormatter(formatter)
        logger.addHandler(hdlr)
        logger.addHandler(console)
        logger.setLevel(logging.DEBUG)
        return logger