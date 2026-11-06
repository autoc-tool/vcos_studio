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
from copy import deepcopy

CUR_FILE_PATH = os.path.dirname(os.path.realpath(__file__))


class VersionUpgradeCommon:

    def __init__(self):
        pass

    def get_current_version(self, project_version):
        version_split = []
        prj_version_spy = project_version.upper()
        if "-DEV" in prj_version_spy or "-RELEASE" in prj_version_spy or "-HOUR" in prj_version_spy:
            # 情况一：解析工具和工程版本
            current_version = self.get_content_between_flags(project_version, "V", "-")
        else:
            # 情况二：解析升级脚本文件的版本
            current_version = self.get_content_between_flags(project_version, "_v", ".py").replace("_", ".")
        if current_version:
            version_split = current_version.split(".")
        version = version_split[-1]
        for item in [" RC", "RC", "-"]:
            if item in version:
                v = version.split(item)
                version_split.pop(-1)
                version_split += v
                break
        if "RC" in project_version:
            version_split = ["RC"] + version_split
        else:
            version_split = [" "] + version_split
        return version_split

    def func_update_version(self, vcos_list, prj_list):
        # '-'划分如RC后的字段
        vcos_version = vcos_list[-1].split("-")
        prj_version = prj_list[-1].split("-")
        len_vcos = len(vcos_version)
        len_prj = len(prj_version)
        # 通过补0方式完善版本信息
        len_max = max(len_vcos, len_prj)
        vcos_version += ["0" for i in range(len_max - len_vcos)]
        prj_version += ["0" for i in range(len_max - len_prj)]

        vcos_list.pop(-1)
        vcos_list += vcos_version
        prj_list.pop(-1)
        prj_list += prj_version

    def compare_version(self, vcos_version, prj_version, large_equal=True):
        """
        large_equal == True: Larger Than and Equal (para1>=para2) -> return True
        large_equal == False: Larger (para1>para2) -> return True
        """
        levels = 0
        vcos = deepcopy(vcos_version[1:])
        prj = deepcopy(prj_version[1:])
        levels = max(len(vcos), len(prj))
        basic_levels = min(len(vcos), len(prj))

        if levels == basic_levels and ("RC" in vcos_version or "RC" in prj_version):
            # 支持处理RC后面带'-'字符
            self.func_update_version(vcos, prj)
            # 更新子版本长度
            levels = len(vcos)
            basic_levels = levels

        for level in range(basic_levels):
            sub_vcos_version = int(vcos[level])  # 带RC长度版本号长度相等
            sub_prj_version = int(prj[level])
            if sub_vcos_version > sub_prj_version:
                return True
            elif sub_vcos_version < sub_prj_version:
                return False
            else:
                continue

        if levels != basic_levels:
            if vcos_version[0] == "RC" or prj_version[0] == "RC":  # 带RC长度不等
                return len(vcos_version) < len(prj_version)
            else:  # 不带RC长度不等，带-
                return len(vcos_version) > len(prj_version)

        if large_equal:
            return True
        else:
            return False

    def get_upgrade_module_list(self, enabled_module_list, plug_in_path):
        directories = set()
        for k, v in plug_in_path.items():
            for name in os.listdir(v):
                if name.endswith("_upgrade"):
                    directories.add(k.lower())
        #
        upgrade_dir = os.path.abspath(os.path.join(CUR_FILE_PATH, ".."))
        for name in os.listdir(upgrade_dir):
            if name.endswith("_upgrade"):
                directories.add(name.split("_upgrade")[0])

        upgrade_module_list = [module_list for module_list in enabled_module_list if module_list.lower() in directories]
        upgrade_module_list.append("VCOSProject")
        return upgrade_module_list

    def get_module_version_list(
        self,
        module_name,
        system_version,
        studio_version,
        current_project_system_version,
        current_project_version,
        plug_in_path,
    ):

        def version_upgrade_check(module_version):
            """compare version"""
            result = False
            result = self.compare_version(system_version, module_version)
            result = result and self.compare_version(module_version, current_project_system_version, False)
            return result

        def project_version_upgrade_check(module_version):
            """compare version"""
            result = False
            result = self.compare_version(studio_version, module_version)
            result = result and self.compare_version(module_version, current_project_version, False)
            return result

        files = []
        module_version = set()
        if module_name.lower() in ["vcosproject", "rte"]:
            upgrade_dir = os.path.abspath(os.path.join(CUR_FILE_PATH, ".."))
            upgrade_module_dir = os.path.abspath(os.path.join(upgrade_dir, f"{module_name.lower()}_upgrade"))
        else:
            upgrade_module_dir = os.path.abspath(os.path.join(plug_in_path[module_name], "version_upgrade"))

        if not os.path.exists(upgrade_module_dir):
            return []
        files = os.listdir(upgrade_module_dir)
        upgrade_files = [file for file in files if file.endswith(".py") or file.endswith(".pyc")]
        if module_name.lower() in ["vcosproject", "rte"]:
            for file in upgrade_files:
                version_module = self.get_current_version(file)
                if project_version_upgrade_check(version_module):
                    module_file_version = self.get_content_between_flags(file, "_v", ".py").replace("_", ".")
                    module_version.add(module_file_version)
        else:
            for file in upgrade_files:
                version_module = self.get_current_version(file)
                if version_upgrade_check(version_module):
                    module_file_version = self.get_content_between_flags(file, "_v", ".py").replace("_", ".")
                    module_version.add(module_file_version)
        module_version = sorted(module_version)
        return module_version

    def get_content_between_flags(self, input_string, start_flag, end_flag):
        start_index = input_string.find(start_flag)
        end_index = input_string.rfind(end_flag)  # find last index of specific char

        if start_index != -1 and end_index != -1:
            content = input_string[start_index + len(start_flag) : end_index]
            return content.strip()
        else:
            return None
