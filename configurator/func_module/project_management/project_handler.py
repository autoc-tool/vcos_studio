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
import sys
import shutil
from func_module.health_monitor.logger import logger

CURRENT_PATH = os.path.dirname(__file__)
STUDIO_PATH = os.path.join(CURRENT_PATH, "..", "..")


def backup_file(file_path):
    backup_path = file_path + ".bak"
    shutil.copy2(file_path, backup_path)
    return backup_path


def reduce_file(bak_file_path):
    file_path = bak_file_path.split(".")[-2]
    shutil.copy2(bak_file_path, file_path)
    return file_path


def create_kconfig_config_file(kconfig_file_path):
    directory = os.path.dirname(kconfig_file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(kconfig_file_path, "w") as file:
        file.write("")


class ProjectHandler:

    def remove_module_in_saving_project(self, remove_module_list, config_path):
        for module_name in remove_module_list:
            self.delete_ib_arxml(module_name, config_path)
            self.delete_ecuc_arxml(module_name, config_path)
            self.delete_service_swc_arxml(module_name, config_path)

    def delete_ib_arxml(self, module_name, config_path):
        arxml_path = os.path.join(config_path, "internal_behavior", f"{module_name}_ib_bswmd.arxml")
        if not os.path.exists(arxml_path):
            return
        os.remove(arxml_path)

    def delete_ecuc_arxml(self, module_name, config_path):
        arxml_path = os.path.join(config_path, "bsw", module_name, f"{module_name}_ecuc.arxml")
        if not os.path.exists(arxml_path):
            return
        os.remove(arxml_path)

    def delete_service_swc_arxml(self, module_name, config_path):
        arxml_path = os.path.join(config_path, "service_components", f"{module_name}_swc.arxml")
        if not os.path.exists(arxml_path):
            return
        os.remove(arxml_path)

    def get_remove_module_list(self, new_module_list, old_module_list):
        remove_module_list = set(filter(lambda old_module: old_module not in new_module_list, old_module_list))

        return remove_module_list

    @classmethod
    def get_platform_type(cls):
        os_type = ""
        if sys.platform.startswith("win"):
            os_type = "windows"
        elif sys.platform.startswith("linux"):
            os_type = "linux"
        else:
            logger.exception("get system type failed")
        return os_type

    @classmethod
    def copy_dir(cls, source_dir, destination_dir):
        # 遍历源目录下的所有文件
        if not os.path.exists(source_dir):
            return False

        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)

        for root, dirs, files in os.walk(source_dir):
            for file in files:
                source_file = os.path.join(root, file)
                destination_file = os.path.join(destination_dir, file)
                # 拷贝文件
                result = shutil.copy2(source_file, destination_file)
                if result is None:
                    return False

        return True

    @classmethod
    def update_bsw_module_cfg_path(cls, sys_info_class):
        config_path = sys_info_class.config_base_path
        enabled_module_list = list(sys_info_class.enable_modules)
        bsw_cfg: dict = {}
        """update bsw_module_cfg configuration"""
        for module in enabled_module_list:
            module_arxml_path: str = os.path.abspath(os.path.join(config_path, "bsw", module, f"{module}_ecuc.arxml"))
            if not os.path.exists(module_arxml_path):
                continue
            bsw_cfg.update({module: module_arxml_path})
        sys_info_class.bsw_cfg = bsw_cfg

    @classmethod
    def copy_cur_dir(cls, source_dir, destination_dir):
        if not os.path.exists(source_dir):
            return False

        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)

        files = os.listdir(source_dir)
        for file in files:
            file_path = os.path.join(source_dir, file)
            if os.path.isfile(file_path):
                shutil.copy(file_path, destination_dir)

    @classmethod
    def amend_project_name(cls, project_name, path):
        with open(path, "r") as file:
            # 读取文件的全部内容
            content = file.read()

        new_string = content.replace("<project_name>", f"{project_name}")

        # 打开文件用于写入
        with open(path, "w") as file:
            # 写入一些文本到文件
            file.write(new_string)

        if not os.path.exists(path):
            return False

        return True

    @classmethod
    def copy_file(cls, source_file, destination_file):
        if not os.path.isfile(source_file):
            logger.exception(f"copy {source_file} failed")
            return False

        result = shutil.copy(source_file, destination_file)
        if result is None:
            return False

        return True
