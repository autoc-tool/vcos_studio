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
from basic_func_module.base_common.singleton import Singleton
from func_module.health_monitor.logger import logger

CUR_FILE_PATH = os.path.dirname(__file__)
FILE_LOCK_NAME = "vcos_studio.lock~"


class ProjectFileLock(Singleton):
    """
    文件锁
    """

    def __init__(self):
        self.file_lock_path = ""
        self.lock_status = False

    def add_file_lock(self, project_file_path):
        self.file_lock_path = os.path.join(os.path.dirname(project_file_path), FILE_LOCK_NAME)
        if os.path.exists(self.file_lock_path):
            self.lock_status = False
            return False
        else:
            with open(self.file_lock_path, "w") as f:
                f.close()
            self.lock_status = True
            return True

    def delete_file_lock(self):
        if self.lock_status is True:
            if os.path.exists(self.file_lock_path):
                try:
                    os.remove(self.file_lock_path)
                except OSError:
                    logger.exception(f"delete {self.file_lock_path} fail")
            self.lock_status = False
