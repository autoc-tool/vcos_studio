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
from func_module.health_monitor.logger import logger
from func_module.module_management.module_management import ModuleManagement
from func_module.project_management.project_file_parser import ProjectFileParser
from func_module.health_monitor.perf_record import log_function_stats


class UserPluginManager:

    def __init__(self, sys_info_class, bsw_autosar_class, sys_target_dict, all_module_list):
        self.sys_info_class = sys_info_class
        self.sys_target_dict = sys_target_dict
        self.all_module_list = all_module_list
        self.bsw_autosar_class = bsw_autosar_class if bsw_autosar_class else None

    def _validate_plugin_configuration(self, root_directory):
        error_messages = {}
        # 1. 确定 JSON 文件的路径
        json_file_path = os.path.join(root_directory, "module_cfg.json")

        # 2. 检查 JSON 文件是否存在
        if not os.path.exists(json_file_path):
            error_messages["json_file"] = f"Error: JSON file not found: {json_file_path}"
            return error_messages

        # 3. 读取并解析模块配置 JSON 文件
        with open(json_file_path, "r") as json_file:
            config = json.load(json_file)

        # 4. 获取根目录名
        root_dir_name = os.path.basename(root_directory)

        # 检查是否存在重名模块
        paths_to_check = [root_dir_name]
        plugin_module_info = ModuleManagement.get_module_info_by_spec_path(set(paths_to_check))

        # 调用拦截函数
        intercepted_modules = self.already_supported_module(plugin_module_info.values())
        if intercepted_modules:
            error_messages["supported_modules"] = (
                f"Error: The following modules are already supported: {', '.join(intercepted_modules)}"
            )
            return error_messages

        # 5. 确保 JSON 字段名与根目录名相同
        if root_dir_name not in config:
            error_messages["missing_key"] = f"Error: The key '{root_dir_name}' is missing in the module_cfg.json"
            return error_messages

        module_config = config[root_dir_name]

        # 6. 检查 user_plugin 是否为 true
        if not module_config.get("user_plugin", False):
            error_messages["user_plugin"] = f"Error: 'user_plugin' must be True for '{root_dir_name}'"
            return error_messages

        # 7. 检查 support_generation 和检查 generator.py 中的接口
        if module_config.get("support_generation", False):
            generator_file = os.path.join(root_directory, "config_plug_in", "generator", "generator.py")

            if not os.path.exists(generator_file):
                error_messages["generator_file"] = f"Error: Generator file not found: {generator_file}"
                return error_messages

            # 直接检查 generator.py 文件中是否包含 generate_dynamic_code 字符串
            with open(generator_file, "r", encoding="utf-8") as file:
                file_content = file.read()
                if "generate_dynamic_code" not in file_content:
                    error_messages["missing_function"] = (
                        f"Error: The function 'generate_dynamic_code' is missing in {generator_file}"
                    )
                    return error_messages

        # 8. 检查必需的目录是否存在
        required_dirs = [
            os.path.join(root_directory, "config_plug_in", "base_config"),
            os.path.join(root_directory, "config_plug_in", "base_config", "bswmd"),
            # os.path.join(root_directory, 'config_plug_in', 'base_config', 'base_ecuc')
        ]

        for required_dir in required_dirs:
            if not os.path.exists(required_dir):
                error_messages["missing_directory"] = f"Error: Required directory not found: {required_dir}"
                return error_messages
        # TODO 其他校验
        logger.ui_info(f"Validation successful for plugin '{root_dir_name}'.")
        return {}  # 返回空字典表示没有错误

    @log_function_stats(["VCOS工程管理", "用户插件导入配置更新"])
    def handle_valid_plugin_sys_cfg(self, added_dirs):
        """处理有效的插件系统配置"""
        for added_dir in added_dirs:
            config_file = os.path.join(added_dir, "module_cfg.json")
            try:
                self._update_sys_info_class_module_cfg(config_file)
            except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
                logger.ui_error(f"Error handling directory {added_dir}: {e}")

    def _update_sys_info_class_module_cfg(self, plugin_cfg_path, encoding="utf-8"):
        """更新系统信息类模块配置"""
        try:
            with open(plugin_cfg_path, "r", encoding=encoding) as file:
                plugin_cfg_data = json.load(file)

            if "module_cfg" in self.sys_info_class.system_target_info:
                self.sys_info_class.system_target_info["module_cfg"].update(plugin_cfg_data)
                self.sys_target_dict["module_cfg"].update(plugin_cfg_data)
                logger.ui_info(f"Successfully import user plugin :{list(plugin_cfg_data.keys())}")
                self.update_vcos_project_datamanagement()
            else:
                raise KeyError("The key 'module_cfg' is not found in the system info.")
        except FileNotFoundError:
            logger.ui_error(f"Configuration file not found: {plugin_cfg_path}")
        except KeyError as e:
            logger.ui_error(e)
        except json.JSONDecodeError:
            logger.ui_error(f"Error decoding JSON from file: {plugin_cfg_path}")

    def _remove_plugin_sys_cfg(self, removed_dir):
        """移除插件系统配置"""
        config_file = os.path.join(removed_dir, "module_cfg.json")
        try:
            with open(config_file, "r", encoding="utf-8") as file:
                plugin_cfg_data = json.load(file)

            if "module_cfg" in self.sys_info_class.system_target_info:
                module_cfg = self.sys_info_class.system_target_info["module_cfg"]
                module_cfg_old = self.sys_target_dict["module_cfg"]
                removed_keys = []
                for key in plugin_cfg_data.keys():
                    if key in module_cfg:
                        del module_cfg[key]
                        removed_keys.append(key)
                    if key in module_cfg_old:
                        del module_cfg_old[key]
                logger.ui_info(f"Successfully removed user plugin: '{removed_keys}'")
                self.update_vcos_project_datamanagement()
            else:
                raise KeyError("The key 'module_cfg' is not found in the system info.")
        except FileNotFoundError:
            logger.ui_error(f"Configuration file not found in {removed_dir}.")
        except KeyError as e:
            logger.ui_error(e)

    def already_added_module_from_plugin(self, paths_to_remove):
        """检查已添加的模块"""
        to_intercept = []
        for path in paths_to_remove:
            if path in self.bsw_autosar_class:
                to_intercept.append(path)
        return to_intercept  # 返回需要拦截的路径列表

    def already_supported_module(self, paths_to_remove):
        """检查已支持的模块"""
        to_intercept = []
        for path in paths_to_remove:
            if path in self.sys_info_class.all_modules:
                to_intercept.append(path)
        return to_intercept  # 返回需要拦截的路径列表

    def update_vcos_project_datamanagement(self):
        """
        Instance class of SysInfoClass to save paras delivering from New Project UI
        """
        self.sys_info_class.all_modules = ProjectFileParser.get_all_module_list(self.sys_target_dict)
        self.all_module_list = self.sys_info_class.all_modules
        sys_info_class = self.sys_info_class
        sys_info_class.plug_in_path, sys_info_class.plug_in_bswmd_path, sys_info_class.plug_in_ib_path = (
            ProjectFileParser.get_plug_in_path(
                sys_info_class.system_path,
                sys_info_class.target,
                sys_info_class.system_target_info["target"][sys_info_class.target],
                sys_info_class.mcal_version,
                sys_info_class.import_plugin_path_list,
            )
        )
