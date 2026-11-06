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
from func_module.health_monitor.logger import logger
import time
import os
import shutil
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlIncrementalSaveHandler
import threading


class MyThread(threading.Thread):

    def __init__(
        self, lock, autosar_asw_class, autosar_bsw_class, autosar_system_class, autosar_ib_class, sys_info_class
    ):
        super().__init__()
        self.lock = lock
        self.autosar_asw_class = autosar_asw_class
        self.autosar_bsw_class = autosar_bsw_class
        self.autosar_system_class = autosar_system_class
        self.autosar_ib_class = autosar_ib_class
        self.sys_info_class = sys_info_class
        self.tmp_path = None

    def run(self):

        logger.info(f"Running {self.tmp_path}")

        logger.info("获取到锁，开始工作...")
        try:
            self.tmp_path = os.path.abspath(
                os.path.join(os.path.dirname(self.sys_info_class.config_base_path), ".config")
            )
            ArxmlIncrementalSaveHandler.incremental_save_bsw_ecuc_arxml(
                self.sys_info_class.cfg_hash, self.sys_info_class.enable_modules, self.autosar_bsw_class, self.tmp_path
            )
            ArxmlIncrementalSaveHandler.incremental_save_system_ecuc_arxml(
                self.sys_info_class.cfg_hash, self.autosar_system_class, self.tmp_path
            )
            ArxmlIncrementalSaveHandler.incremental_internal_behavior_ecuc_arxml(
                self.sys_info_class.cfg_hash, self.autosar_ib_class, self.tmp_path, self.sys_info_class.enable_modules
            )
            ArxmlIncrementalSaveHandler.incremental_system_asw_ecuc_arxml(
                self.sys_info_class.cfg_hash, self.autosar_asw_class, self.tmp_path
            )
        except Exception as e:
            logger.error(f"Error occurred while saving ARXML: {str(e)}")


class ProjectSaveHandlerFunc:

    def __init__(self, lock):
        self.flag = False
        self.lock = lock
        self.threading_status = False
        pass

    def create_thread(
        self, lock, autosar_asw_class, autosar_bsw_class, autosar_system_class, autosar_ib_class, sys_info_class
    ):
        start_time = time.time()
        threads = MyThread(
            lock,
            self.autosar_asw_class,
            self.autosar_bsw_class,
            self.autosar_system_class,
            self.autosar_ib_class,
            self.sys_info_class,
        )
        threads.start()
        threads.join()
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"all 代码执行时间: {execution_time:.4f} 秒")

    def periodic_save_configuration(
        self, lock, autosar_asw_class, autosar_bsw_class, autosar_system_class, autosar_ib_class, sys_info_class
    ):
        try:
            if self.lock.acquire(blocking=True):
                self.autosar_asw_class = autosar_asw_class
                self.autosar_bsw_class = autosar_bsw_class
                self.autosar_system_class = autosar_system_class
                self.autosar_ib_class = autosar_ib_class
                self.sys_info_class = sys_info_class
                if self.flag is True:
                    return
                self.flag = True
                self.tmp_path = os.path.abspath(
                    os.path.join(os.path.dirname(self.sys_info_class.config_base_path), ".config")
                )
                logger.debug("periodic_save_configuration thread started")
                self.create_thread(
                    self.lock,
                    self.autosar_asw_class,
                    self.autosar_bsw_class,
                    self.autosar_system_class,
                    self.autosar_ib_class,
                    self.sys_info_class,
                )
                logger.debug("periodic_save_configuration thread end")
                self.flag = False
        except Exception as e:
            logger.error(f"Error occurred while saving ARXML: {str(e)}")
        finally:
            self.lock.release()

    def save_config_from_tmp_to_config(
        self, lock, autosar_asw_class, autosar_bsw_class, autosar_system_class, autosar_ib_class, sys_info_class
    ):
        try:
            if self.lock.acquire(blocking=True):
                self.autosar_asw_class = autosar_asw_class
                self.autosar_bsw_class = autosar_bsw_class
                self.autosar_system_class = autosar_system_class
                self.autosar_ib_class = autosar_ib_class
                self.sys_info_class = sys_info_class
                self.tmp_path = os.path.abspath(
                    os.path.join(os.path.dirname(self.sys_info_class.config_base_path), ".config")
                )
                logger.debug("save_config_from_tmp_to_config thread started")
                self.create_thread(
                    self.lock,
                    self.autosar_asw_class,
                    self.autosar_bsw_class,
                    self.autosar_system_class,
                    self.autosar_ib_class,
                    self.sys_info_class,
                )
                self.copy_arxml_to_config(self.tmp_path)
                logger.debug("save_config_from_tmp_to_config thread end")
        except Exception as e:
            logger.error(f"Error occurred while saving ARXML: {str(e)}")
        finally:
            self.lock.release()

    def copy_arxml_to_config(self, tmp_path):

        for root, dirs, files in os.walk(tmp_path):
            for file in files:
                # Check for '.txt' extension
                if file.endswith(".arxml"):
                    file_path = os.path.join(root, file)
                    dest_path = os.path.join(root, file).replace(".config", "config")
                    if not os.path.exists(os.path.dirname(dest_path)):
                        os.makedirs(os.path.dirname(dest_path))

                    try:
                        shutil.copy(file_path, dest_path)
                        logger.debug(f"Removed {file_path}")
                    except OSError as e:
                        logger.debug(f"{file_path}, {dest_path} Error: {e} - {file_path}")
                        continue

        try:
            shutil.rmtree(tmp_path)
            logger.debug(f"Removed {file_path}")
        except OSError as e:
            logger.debug(f"Error: {e.strerror} - {file_path}")

    def check_thread_status(self):
        try:
            if self.lock.acquire(blocking=True):
                self.delete_config_dir()
                return True
        except Exception as e:
            logger.error(f"Error occurred while saving ARXML: {str(e)}")
        finally:
            self.lock.release()
        return False

    def delete_config_dir(self):
        if hasattr(self, "tmp_path") and os.path.exists(self.tmp_path) and os.path.isdir(self.tmp_path):
            try:
                # end try
                shutil.rmtree(self.tmp_path)
            except Exception as e:
                raise e
        pass
