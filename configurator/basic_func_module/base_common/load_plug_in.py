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
from importlib import import_module
from basic_func_module.base_logger import logger
from basic_func_module.base_common.singleton import Singleton

ROOT_PACKAGE = "components"
DRIVERS_PACKAGE = "drivers"

class LoadPlugIn(Singleton):

    instance = None

    def __init__(self):
        self.__class__.instance = self
        self.plug_in_dict = {}
        self.module_name_map = {}
        self.module_loaded_cache = {}

    @classmethod
    def load_module(cls, module_name: str, module_path: str):
        assert cls.instance
        if module_name not in cls.instance.module_name_map:
            logger.debug(f"Load module failed, module_name: {module_name} is not exist.")
            return None
        module_prefix = cls.instance.module_name_map[module_name]
        module_path = f"{module_prefix}.{module_path}"
        if module_path in cls.instance.module_loaded_cache:
            return cls.instance.module_loaded_cache[module_path]
        try:
            module = import_module(module_path)
            cls.instance.module_loaded_cache[module_path] = module
            return module
        except Exception as e:
            logger.warning(f"Failed to load module {module_path}: {e}")
            logger.exception("Failed to load module.")

    @classmethod
    def append_sys_path(cls, plug_in_path, module_name=""):
        assert cls.instance
        plug_in_path = os.path.abspath(plug_in_path).replace("\\", "/")
        if module_name:
            root_package_str = f"/{ROOT_PACKAGE}/"
            drivers_package_str = f"/{DRIVERS_PACKAGE}/"
            if root_package_str in plug_in_path:
                prefix, module = plug_in_path.split(root_package_str)
                cls.instance.module_name_map[module_name] = f"{ROOT_PACKAGE}.{module.replace('/', '.')}"
            elif drivers_package_str in plug_in_path:
                prefix, module = plug_in_path.split(drivers_package_str)
                cls.instance.module_name_map[module_name] = f"{DRIVERS_PACKAGE}.{module.replace('/', '.')}"
            else:
                logger.ui_error(f"{module_name} System path {plug_in_path} error!")
                return
            plug_in_base_path = prefix
        else:
            plug_in_base_path = plug_in_path
        if not os.path.exists(plug_in_base_path):
            logger.ui_error(f"System path {plug_in_base_path} not exist!")
            return
        if plug_in_base_path not in sys.path:
            sys.path.append(plug_in_base_path)


LoadPlugIn()
