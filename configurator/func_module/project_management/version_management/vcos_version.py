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
import json
from enum import IntEnum, auto
from func_module.health_monitor.logger import logger

CUR_PATH = os.path.dirname(__file__)
JSON_FILE_PATH = os.path.join(CUR_PATH, "compatibility.json")


class VersionErrorCode(IntEnum):
    ERROR_CODE_COMPATIBLE = 0
    ERROR_CODE_SYSTEM_INCOMPATIBLE = auto()
    ERROR_CODE_PROJECT_INCOMPATIBLE = auto()
    ERROR_CODE_VCOS_TOO_LOW = auto()
    ERROR_CODE_PROJECT_TOO_LOW = auto()


class VcosVersionManager:

    def __init__(self, json_file=JSON_FILE_PATH, system_path="", project_version="", project_system_version=""):
        self.json_file = json_file
        with open(self.json_file, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.system_path = system_path
        self.project_version = project_version
        self.project_system_version = project_system_version
        self.studio_version = self.get_vcos_studio_version()
        self.get_system_version()

    def get_compatible_project_versions(self, component="Studio", max_versions=5):
        """
        获取指定软件组件兼容的项目版本列表，最多返回 max_versions 个版本.

        Args:
            component (str, optional): 组件名称. 默认为 "Studio".
            max_versions (int, optional): 最大返回版本数量. 默认为 3.

        Returns:
            list: 兼容的项目版本列表.
        """
        try:
            compatible_versions = self.data["components"][component]["compatibleProjectVersions"]
            compatible_versions.sort(reverse=True)
            return compatible_versions
        except KeyError:
            return []

    def get_vcos_studio_version(self, component="Studio"):
        with open(self.json_file, "r", encoding="utf-8") as f:
            data = json.load(f)  # 读取 JSON 文件内容
        current_version = data["components"][component]["version"]
        return current_version

    def set_vcos_studio_version(self, version, component="Studio"):
        self.data["components"][component]["version"] = version
        self.studio_version = version
        self.update_compatible_project_versions([version])
        self._save_changes()

    def _save_changes(self):
        """保存修改到 JSON 文件"""
        with open(self.json_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

    def update_compatible_project_versions(self, new_versions, max_version_nums=9):
        # 1. 添加新版本，并去重
        new_versions_list = []
        for new_version in new_versions:
            new_versions_list.extend([_replace_after_second_dot(v) for v in [new_version]])
        compatible_project_versions = self.get_compatible_project_versions(max_versions=max_version_nums)
        compatible_project_versions = list(set(compatible_project_versions + new_versions_list))

        # 2. 如果版本数量超过max_version_nums，则删除最小的版本
        compatible_project_versions = sorted(compatible_project_versions, reverse=True)
        compatible_project_versions = compatible_project_versions[:max_version_nums]
        self.data["components"]["Studio"]["compatibleProjectVersions"] = compatible_project_versions
        self._save_changes()

    def set_system_path(self, path: str):
        self.system_path = path

    def get_system_path(self):
        return self.system_path

    def _get_system_version_info(self):
        system_version_info = None
        from basic_func_module.base_common.load_plug_in import LoadPlugIn

        LoadPlugIn.append_sys_path(self.system_path)
        try:
            from components_version import ComponentsVersionInfo

            system_version_info = ComponentsVersionInfo()
        except ModuleNotFoundError as e:
            raise ImportError(
                f"Failed to import module 'system_version'. Make sure it exists in {self.system_path}"
            ) from e
        except AttributeError as e:
            raise ImportError("'system_version' module does not have 'SystemVersionInfo' attribute.") from e
        return system_version_info

    def get_system_version(self):
        system_version_info = self._get_system_version_info()
        system_version = system_version_info.get_current_version()
        compatible_project_system_versions = system_version_info.get_compatible_project_system_versions()
        self.system_version = system_version
        self.compatible_project_system_versions = compatible_project_system_versions
        return self.system_version

    def set_system_version(self, version):
        system_version_info = self._get_system_version_info()
        self.system_version = version
        system_version_info.update_current_version(version)

    def version_check(
        self,
        system_version,
        project_system_version,
        project_version,
        compatible_system_versions,
        compatible_project_versions,
    ):
        # Extract main versions from all relevant variables
        # main_system_version = _replace_after_second_dot(system_version)
        main_project_version = _replace_after_second_dot(project_version)
        main_project_system_version = _replace_after_second_dot(project_system_version)
        main_compatible_system_versions = [_replace_after_second_dot(v) for v in compatible_system_versions]
        main_compatible_project_versions = [_replace_after_second_dot(v) for v in compatible_project_versions]

        # Result dictionary
        result = {
            "compatibility_info": "",
            "error_code": VersionErrorCode.ERROR_CODE_COMPATIBLE,  # Default to 0, meaning compatible
        }

        # Validate project version compatibility
        if self.compare_versions(project_system_version, system_version) == 1:
            result["compatibility_info"] = (
                f"Project system version {project_system_version} "
                f"is larger than current system_version:{system_version}."
            )
            result["error_code"] = VersionErrorCode.ERROR_CODE_PROJECT_INCOMPATIBLE
            return result

        # Validate project version compatibility
        if main_project_version not in main_compatible_project_versions:
            result["compatibility_info"] = (
                f"Project studio version {project_version} "
                f"is not in compatible project versions {compatible_project_versions}."
            )
            result["error_code"] = VersionErrorCode.ERROR_CODE_PROJECT_INCOMPATIBLE
            return result

        # Validate project system version compatibility
        if main_project_system_version not in main_compatible_system_versions:
            result["compatibility_info"] = (
                f"Project system version {main_project_system_version} "
                f"is not in compatible project system versions {compatible_system_versions}."
            )
            result["error_code"] = VersionErrorCode.ERROR_CODE_PROJECT_INCOMPATIBLE
            return result

        # If all checks pass, versions are compatible
        result["compatibility_info"] = "All versions are compatible."
        result["error_code"] = VersionErrorCode.ERROR_CODE_COMPATIBLE
        return result

    def process_result(self, result):
        # Process the result based on error_code
        error_code = result["error_code"]
        message = result["compatibility_info"]
        ret = False
        if error_code in [
            VersionErrorCode.ERROR_CODE_SYSTEM_INCOMPATIBLE,
            VersionErrorCode.ERROR_CODE_PROJECT_INCOMPATIBLE,
            VersionErrorCode.ERROR_CODE_VCOS_TOO_LOW,
        ]:
            logger.error(f"ERROR: {message}")
            ret = False
        elif error_code == VersionErrorCode.ERROR_CODE_PROJECT_TOO_LOW:
            logger.warning(f"WARNING: {message}")
            ret = True
        elif error_code == VersionErrorCode.ERROR_CODE_COMPATIBLE:
            logger.info(f"INFO: {message}")
            ret = True
        return ret

    def version_key(self, version):
        # 去掉前缀 'V' 并提取右边第一个'-'之前的字符串
        main_part = version.lstrip("V").split("-")[0]

        # 检查是否包含 'RC'
        if "RC" in main_part:
            # 如果包含，取 'RC' 之前的部分
            main_part = main_part.split("RC")[0]

        # 使用 '.' 分割并转为整数
        parts = main_part.split(".")

        # 将每一部分转换为整数，返回包含整数和'0'的部分（如果有的话）
        return [int(part) if part.isdigit() else 0 for part in parts]

    def compare_versions(self, version_a, version_b):
        # 取得可比较的版本部分
        key_a = self.version_key(version_a)
        key_b = self.version_key(version_b)

        # 逐步比较
        for a, b in zip(key_a, key_b):
            if a > b:
                return 1
            elif a < b:
                return -1

        # 比较长度，如果一个版本更长，那它是更新的
        if len(key_a) > len(key_b):
            return 1
        elif len(key_a) < len(key_b):
            return -1

        return 0  # 相等


def _replace_after_second_dot(input_str):
    try:
        # 找到第一个点号的位置
        first_dot_index = input_str.find(".")
        if first_dot_index == -1:
            logger.error("输入的字符串不是有效的版本号，应该符合 x.x.x 格式")

        # 找到第二个点号的位置
        second_dot_index = input_str.find(".", first_dot_index + 1)
        if second_dot_index == -1:
            logger.error("输入的字符串不是有效的版本号，应该符合 x.x.x")

        # 构造新的字符串
        new_str = input_str[: second_dot_index + 1] + "x"
        return new_str

    except ValueError as e:
        logger.exception(f"错误: {e}")

    return None


vcos_info = None


def get_vcos_version_info(system_path="", project_version="", project_system_version=""):
    """Get the singleton instance of VcosVersionManager, or replace it if parameters are provided."""
    global vcos_info

    # 如果 vcos_info 是 None，或者传入了参数，则初始化或重新实例化
    if vcos_info is None or any([system_path != "", project_version, project_system_version]):
        vcos_info = VcosVersionManager(
            system_path=system_path, project_version=project_version, project_system_version=project_system_version
        )

    return vcos_info


class StudioVersionInfo:

    def __init__(self, json_file=JSON_FILE_PATH):
        self.json_file = json_file
        with open(self.json_file, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def get_studio_version(self, component="Studio"):
        current_version = self.data["components"][component]["version"]
        return current_version


studio_version = StudioVersionInfo()
VCOS_VERSION = studio_version.get_studio_version()

if __name__ == "__main__":
    new_version = "V1.3.0-DEV"
    vcos_info = get_vcos_version_info()
    vcos_info.set_system_version(new_version)
    vcos_info.set_vcos_studio_version(new_version)
