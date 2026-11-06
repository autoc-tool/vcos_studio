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

CUR_FILE_PATH = os.path.dirname(__file__)
FILE_LOCK_NAME = "vcos_studio.lock~"


class ProjectFileLock:
    """
    文件锁
    """

    def __init__(self):
        self.file_lock_path = ""
        self.lock_status = False

    def create_file_lock(self, project_file_path):
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
                    print(f"delete {self.file_lock_path} fail")
            self.lock_status = False


class VcosProjectFileHandler:
    """
    导入工程时,update工程配置并赋予默认值(工程配置文件中不包含的配置)
    """

    def __init__(self):
        self.sys_cfg_dict = {}
        self.project_file_path = ""
        pass

    def set_sys_cfg_dict(self, sys_cfg_dict):
        self.sys_cfg_dict = sys_cfg_dict

    def check_project_file_version(self, sys_cfg_dict):
        if (
            "rte_cfg" in sys_cfg_dict["path"]["config_file_path"]
            and sys_cfg_dict["path"]["config_file_path"]["rte_cfg"] != ""
        ):
            return None
        else:
            return "cur version"

    def load_project_config_file(self, project_file_path):
        self.project_file_path = os.path.abspath(project_file_path)
        if self.project_file_path is None and os.path.exists(self.project_file_path) is False:
            return None

        with open(self.project_file_path, "r", encoding="utf-8") as f:
            sys_info_dict = json.load(f)
        self.sys_info_dict.update(sys_info_dict)
        self.project_file_path_converter()
        self.main_window.enabled_module_list = set(sorted(self.sys_info_dict["modules_info"]["enabled_module_list"]))
        self.enabled_module_list = set(sorted(self.sys_info_dict["modules_info"]["enabled_module_list"]))
        self.codegen_module_list = sorted(self.sys_info_dict["modules_info"]["codegen_module_list"])
        self.all_module_list = sorted(self.sys_info_dict["modules_info"]["all_module_list"])

    def sys_cfg_dict_converter(self, sys_cfg_dict, project_file_path, is_version=True):
        self.sys_cfg_dict = sys_cfg_dict

        if not self.sys_cfg_dict["path"].get("project_path"):
            self.sys_cfg_dict["path"].update({"project_path": os.path.join(os.path.abspath(project_file_path))})

        if not self.sys_cfg_dict["path"].get("swc_template_path"):
            self.sys_cfg_dict["path"].update(
                {"swc_template_path": os.path.join(self.sys_cfg_dict["gendata_path"], "appl", "source")}
            )

        if not self.sys_cfg_dict["path"].get("application_path"):
            self.sys_cfg_dict["path"].update(
                {"application_path": os.path.join(self.sys_cfg_dict["config_path"], "..", "Apps")}
            )

        if not self.sys_cfg_dict["path"].get("internal_behavior_path"):
            self.sys_cfg_dict["path"].update(
                {"internal_behavior_path": os.path.join(self.sys_cfg_dict["config_path"], "internal_behavior")}
            )

        if not self.sys_cfg_dict["path"].get("log_path"):
            self.sys_cfg_dict["path"].update({"log_path": os.path.join(self.sys_cfg_dict["config_path"], "..", "Log")})

        if not self.sys_cfg_dict["path"].get("service_component_path"):
            self.sys_cfg_dict["path"].update(
                {"service_component_path": os.path.join(self.sys_cfg_dict["config_path"], "service_components")}
            )

        if not self.sys_cfg_dict["path"].get("compiler_path"):
            self.sys_cfg_dict["path"].update(
                {
                    "compiler_path": os.path.abspath(
                        os.path.join(CUR_FILE_PATH, "../../../..", "Tools", "GNUArmToolchain", "linux", "gcc-arm")
                    )
                }
            )

        return self.sys_cfg_dict


class ProjectFileHandler(ProjectFileLock, VcosProjectFileHandler):
    """
    处理文件锁与默认工程配置(default config)
    """

    def __init__(self, main_window=None, sys_info_dict=None):
        super().__init__()
        self.main_window = main_window
        self.set_sys_cfg_dict(sys_info_dict)
        pass
