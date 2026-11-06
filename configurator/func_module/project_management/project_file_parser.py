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
import shutil
from basic_func_module.base_common.load_plug_in import LoadPlugIn
from func_module.health_monitor.logger import logger
from basic_func_module.path_handler.path_converter import PathConverter_Adaptor
from func_module.project_management.sys_info_class import SysInfoClass
from func_module.project_management.version_management.vcos_version import get_vcos_version_info
from func_module.health_monitor.perf_record import log_function_stats
from func_module.module_management.base_config import BASE_CONFIG_PATH

CURRENT_PATH = os.path.dirname(__file__)
STUDIO_PATH = os.path.join(CURRENT_PATH, "..", "..")
DEFAULT_PROJECT_INFO = {
    "project": "",
    "version": "",
    "system_version": "",
    "compiler": "",
    "target": "",
    "mode": "release",
    "generation_limit": "Error",
    "modules_info": {"enabled_module_list": [], "codegen_module_list": []},
    "config_path": "",
    "gendata_path": "",
    "is_add_channel_name": False,
    "path": {
        "project_path": "",
        "swc_template_path": "",
        "bswcallout_path": "",
        "user_plugin_output_path": "",
        "config_base_path": "",
        "config_file_path": {
            "ldf": {"num": 0, "list": {}},
            "dbc": {"num": 0, "list": {}},
            "cdd": {"num": 0, "single_signal": True, "list": {}},
            "swc": "",
            "eb_arxml": "",
        },
        "studio_path": STUDIO_PATH,
        "application_path": "",
        "internal_behavior_path": "",
        "log_path": "",
        "service_component_path": "",
        "compiler_path": "",
        "mcal_path": "",
        "mcal_gendata_path": "",
        "system_path": "",
        "MCAL_VERSION": "",
        "import_plugin_path_list": [],
    },
}


class SingletonMeta(type):
    instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.instances:
            cls.instances[cls] = super().__call__(*args, **kwargs)
        return cls.instances[cls]


class ProjectFileParser(metaclass=SingletonMeta):

    def __init__(self) -> None:
        self.info_dict = {}

    def parse_json_cfg(self, path):
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            try:
                json_info = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"{type(e).__name__} - {str(e)}")
                return {}
        return json_info

    @classmethod
    def get_all_module_list(cls, studio_system_cfg_dict):
        all_module_list = set()
        for key, value in studio_system_cfg_dict["module_cfg"].items():
            if value.get("support_ui", False) is False:
                continue
            else:
                all_module_list.add(key)

        return all_module_list

    def project_abs_and_rel_path_converter(self, sys_info_dict, project_path):
        """
        递归方法优化config_path等工程配置的路径转化
        """
        func = PathConverter_Adaptor.to_rel

        for key, value in sys_info_dict.items():
            if len(key) < 4:
                continue
            filter_str: str = key[-4:]
            if filter_str.lower() != "path":
                continue
            if isinstance(value, str):
                if not os.path.exists(value):
                    logger.info(f"path of { {key} } not existed")  # 添加log提示
                sys_info_dict[key] = func(value, project_path)
            else:
                self.project_abs_and_rel_path_converter(value, project_path)

    def config_file_abs_and_rel_path_converter(self, sys_info_dict, project_path):
        """
        循环遍历优化dbc/ldf/cdd/arxml等配置文件的路径转化
        """
        abs_to_rel_func = PathConverter_Adaptor.to_rel

        config_dict = sys_info_dict["path"]["config_file_path"]
        config_dict_swc = ["swc", "eb_arxml"]
        config_dict_dbc_ldf_cdd = ["dbc", "ldf", "cdd"]
        for key, value in config_dict.items():
            config_name = key.lower()
            # 转换["path"]["config_file_path"]路径下swc、eb_arxml的路径
            if config_name in config_dict_swc:
                config_dict[key] = abs_to_rel_func(config_dict[key], project_path)
            # 转换["path"]["config_file_path"]路径下dbc,ldf,cdd的路径
            elif config_name in config_dict_dbc_ldf_cdd:
                for module, value in config_dict[config_name]["list"].items():
                    config_dict[config_name]["list"][module]["path"] = abs_to_rel_func(value["path"], project_path)
            else:
                continue

    def import_plugin_abs_and_rel_path_converter(self, sys_info_dict, project_path):
        abs_to_rel_func = PathConverter_Adaptor.to_rel
        import_plugin_path_list = sys_info_dict["path"]["import_plugin_path_list"]
        sys_info_dict["path"]["import_plugin_path_list"] = [
            abs_to_rel_func(path, project_path) for path in import_plugin_path_list
        ]

    def excel_input_abs_and_rel_path_converter(self, sys_info_dict, project_path):
        """
        遍历方法优化dbc、ldf、cdd等excel导入的路径转化
        """
        func = PathConverter_Adaptor.to_rel

        cdd_excel_path = sys_info_dict["path"]["config_file_path"]["cdd"].get("excel", {})
        for module_name, value in cdd_excel_path.items():
            if os.path.exists(value):
                sys_info_dict["path"]["config_file_path"]["cdd"]["excel"][module_name] = func(value, project_path)

        dbc_ldf_excel_path = sys_info_dict["path"]["config_file_path"].get("excel", {})
        for module_name, value in dbc_ldf_excel_path.items():
            if os.path.exists(value):
                sys_info_dict["path"]["config_file_path"]["excel"][module_name] = func(value, project_path)

        eb_arxml_path = sys_info_dict["path"]["config_file_path"]["eb_arxml"]
        if len(eb_arxml_path):
            if os.path.exists(eb_arxml_path):
                sys_info_dict["path"]["config_file_path"]["eb_arxml"] = func(eb_arxml_path, project_path)

    def to_abs_paths(self, sys_info_dict, project_file_path):
        """
        读取工程文件时将文件路径以及工程路径转换为绝对路径(window,Linux均适用)
        """
        sys_info_dict["path"].update({"project_path": os.path.abspath(project_file_path)})

        dir_func = PathConverter_Adaptor.to_abs
        file_func = PathConverter_Adaptor.to_abs
        # 转换单层路径
        multi_level_path = ["path", "modules_info"]
        for key, path in sys_info_dict.items():
            if key in multi_level_path:
                continue
            filter_str: str = key[-4:]
            if filter_str.lower() != "path":
                continue
            # if os.path.exists(sys_info_dict[key]):
            sys_info_dict[key] = dir_func(path, project_file_path)
        # 转换多层路径path
        for key, path in sys_info_dict["path"].items():
            if not isinstance(path, str):
                continue
            if ".vcosproject" in path or path == "":
                continue
            sys_info_dict["path"][key] = dir_func(path, project_file_path)
        # path:config_file_path:dbc
        for key, value in sys_info_dict["path"]["config_file_path"]["dbc"]["list"].items():
            path = file_func(value["path"], project_file_path)
            if path:
                sys_info_dict["path"]["config_file_path"]["dbc"]["list"][key]["path"] = path
        # path:config_file_path:ldf
        for key, value in sys_info_dict["path"]["config_file_path"]["ldf"]["list"].items():
            path = file_func(value["path"], project_file_path)
            if path:
                sys_info_dict["path"]["config_file_path"]["ldf"]["list"][key]["path"] = path
        # path:config_file_path:cdd
        for key, value in sys_info_dict["path"]["config_file_path"]["cdd"]["list"].items():
            path = file_func(value["path"], project_file_path)
            if path:
                sys_info_dict["path"]["config_file_path"]["cdd"]["list"][key]["path"] = path
        # path:import_plugin_path_list
        if "import_plugin_path_list" in sys_info_dict["path"]:
            sys_info_dict["path"]["import_plugin_path_list"] = [
                file_func(path, project_file_path) for path in sys_info_dict["path"]["import_plugin_path_list"]
            ]
        # path:config_file_path:eb_arxml
        eb_arxml_path = sys_info_dict["path"]["config_file_path"]["eb_arxml"]
        path = file_func(eb_arxml_path, project_file_path)
        if path:
            sys_info_dict["path"]["config_file_path"]["eb_arxml"] = path
        #  excel获取dbc\ldf\cdd配置的路径转换
        cdd_excel_path = sys_info_dict["path"]["config_file_path"]["cdd"].get("excel", {})
        excel_path = sys_info_dict["path"]["config_file_path"]["dbc"].get("excel", {})
        ldf_excel_path = sys_info_dict["path"]["config_file_path"]["ldf"].get("excel", {})
        for key, value in cdd_excel_path.items():
            path = file_func(value, project_file_path)
            if path:
                sys_info_dict["path"]["config_file_path"]["cdd"]["excel"][key] = path
        for key, value in ldf_excel_path.items():
            path = file_func(value, project_file_path)
            if path:
                sys_info_dict["path"]["config_file_path"]["ldf"]["excel"][key] = path
        for key, value in excel_path.items():
            path = file_func(value, project_file_path)
            if path:
                sys_info_dict["path"]["config_file_path"]["dbc"]["excel"][key] = path

        if path_dict := sys_info_dict["path"]["config_file_path"].get("excel", None):
            for key, value in path_dict.items():
                sys_info_dict["path"]["config_file_path"]["excel"][key] = file_func(value, project_file_path)
        sys_info_dict["path"]["studio_path"] = os.path.abspath(STUDIO_PATH)

    def to_rel_paths(self, sys_info_dict, project_path):
        """
        保存工程配置时将文件路径以及工程路径转换为相对路径(window,Linux均适用)
        """
        sys_info_dict["path"].update({"studio_path": os.path.abspath(STUDIO_PATH)})

        self.project_abs_and_rel_path_converter(sys_info_dict, project_path)
        self.config_file_abs_and_rel_path_converter(sys_info_dict, project_path)
        self.excel_input_abs_and_rel_path_converter(sys_info_dict, project_path)
        self.import_plugin_abs_and_rel_path_converter(sys_info_dict, project_path)

    @log_function_stats(["VCOS工程管理", "加载工程文件"])
    def load_file(self, file_path):
        # File not exists
        if not os.path.exists(file_path):
            logger.error(f"{file_path} not exist!")
            return False

        with open(file_path, "r", encoding="utf-8") as f:
            try:
                json_info = json.load(f)
                self.info_dict = json_info
                self.import_plugin_path = []
            except json.JSONDecodeError as e:
                logger.error(f"{type(e).__name__} - {str(e)}")
                return False
            self.to_abs_paths(self.info_dict, file_path)
        if not os.path.exists(self.info_dict["path"]["system_path"]):
            logger.error(f"System path {self.info_dict['path']['system_path']} not exist!")
            return False
        # 初始化
        self.vcos_info = get_vcos_version_info(
            system_path=self.info_dict["path"]["system_path"],
            project_version=self.info_dict["version"],
            project_system_version=self.info_dict.get("system_version", self.info_dict["version"]),
        )
        return True

    def get_version_compatibility_info(self):
        system_version = self.vcos_info.system_version
        project_version = self.vcos_info.project_version
        project_system_version = self.vcos_info.project_system_version
        compatible_system_versions = self.vcos_info.compatible_project_system_versions
        compatible_project_versions = self.vcos_info.get_compatible_project_versions()
        compatibility_info = self.vcos_info.version_check(
            system_version,
            project_system_version,
            project_version,
            compatible_system_versions,
            compatible_project_versions,
        )
        return compatibility_info

    def process_compatibility_info(self, info):
        return self.vcos_info.process_result(info)

    def cfg_pre_check(self):
        """Configuration pre-processing"""
        block_path_list: list = ["config_base_path"]
        not_block_path_list: list = ["compiler_path", "mcal_path", "mcal_gendata_path"]
        not_block_to_create_list: list = [
            "log_path",
            "gendata_path",
            "swc_template_path",
            "bswcallout_path",
            "internal_behavior_path",
            "service_component_path",
        ]
        block_check_dict: dict = {}

        drive_func = PathConverter_Adaptor.is_drive_existed

        # remind user of drive not existed warning
        def func_get_drive(path):
            ret, drive = drive_func(path)
            if ret is False:
                logger.warning(
                    f"{ {drive} } doesn't exist in your system,please select another path for { {item} } "
                    "in Project->Project Setting or update file of .vcosproject to reopen."
                )
            return ret

        # get configuration path
        def func_get_path(item):
            path = ""
            if self.info_dict.get(item):
                path = self.info_dict[item]
            else:
                path = self.info_dict["path"].get(item, "")
            return path

        # judge whether dir exists or not and process
        for item in block_path_list:
            path = func_get_path(item)
            if path and not os.path.exists(path) and func_get_drive(path):
                logger.error(f"necessary path {item}:{path} not exists")
                block_check_dict.update({item: path})

        for item in not_block_path_list:
            path = func_get_path(item)
            if path and not os.path.exists(path) and func_get_drive(path):
                logger.warning(f"{path} not exists, please do configuration in project_setting firstly")

        for item in not_block_to_create_list:
            path = func_get_path(item)
            if path and not os.path.exists(path) and func_get_drive(path):
                logger.info(f"{path} has been created which is not exists")
                os.makedirs(path)

        return block_check_dict

    def save_file(self, file_path):
        # Check type of info_dict
        if not isinstance(self.info_dict, dict):
            logger.error("Invalid info_dict! Must be dict!")
            return False

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                self.to_rel_paths(self.info_dict, file_path)
                if "project_path" in self.info_dict["path"]:
                    self.info_dict["path"].pop("project_path")
                json.dump(self.info_dict, f, indent=4)
        except TypeError as e:
            logger.error(f"{type(e).__name__} - {str(e)}")
            return False

        return True

    def create_copy_dir(self, data):
        """创建工程目录并完成拷贝"""
        original_sys_class: dict = data.sys_info_class
        latest_sys_class: dict = data.save_as_sys_info_class
        filter_out_list: list = ["mcal_path", "compiler_path", "system_path", "studio_path"]
        filtered_items: list = [
            item
            for item in dir(latest_sys_class)
            if not callable(getattr(latest_sys_class, item)) and not (item.startswith("_"))
        ]
        for key in filtered_items:
            item_type = key.split("_")[-1]
            dest_path = getattr(latest_sys_class, key, None)
            if not isinstance(dest_path, str) or item_type.lower() != "path":  # 非路径不处理
                continue
            if key in filter_out_list:  # 公共路径不处理
                continue
            if os.path.isdir(dest_path) or not os.path.splitext(dest_path)[1]:  # 处理目录
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)
                source_dir_path = getattr(original_sys_class, key, "")
                if os.path.exists(source_dir_path):
                    shutil.copytree(source_dir_path, dest_path)

            else:  # 处理文件
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                source_file_path = getattr(original_sys_class, key, "")
                if os.path.exists(source_file_path):
                    shutil.copy(source_file_path, dest_path)

    def modify_vcos_project(self, data):
        """适配vcos工程文件的工程信息"""
        post_name = data.save_as_sys_info_class.project
        pre_name = data.sys_info_class.project

        cfg_list = ["dbc", "ldf", "cdd"]
        for item in cfg_list:
            dbc_info: dict = getattr(data.save_as_sys_info_class, item)
            obj_list = dbc_info.get("list", {})
            for key, obj in obj_list.items():
                temp_path = obj.get("path", "")
                temp_path = temp_path.replace(pre_name, post_name)
                obj.update({"path": temp_path})
                obj_list[key] = obj
            setattr(data.save_as_sys_info_class, item, dbc_info)

        eb_arxml: str = getattr(data.save_as_sys_info_class, "eb_arxml", "")
        setattr(data.save_as_sys_info_class, "eb_arxml", eb_arxml.replace(pre_name, post_name))
        communication: str = getattr(data.save_as_sys_info_class, "communication", "")
        setattr(data.save_as_sys_info_class, "communication", communication.replace(pre_name, post_name))

    def modify_project(self, data):
        """修改另存工程相关文件的工程信息"""

        def func_modify(file_target):
            with open(file_target, "r") as f:
                content = f.read()
            content = content.replace(pre_name, post_name)
            with open(file_target, "w") as f:
                f.write(content)

        post_name = data.save_as_sys_info_class.project
        pre_name = data.sys_info_class.project
        application_path = data.save_as_sys_info_class.application_path
        gendata_path = data.save_as_sys_info_class.gendata_path
        studio_path = data.save_as_sys_info_class.studio_path
        system_path = data.save_as_sys_info_class.system_path
        root_path = os.path.abspath(os.path.join(system_path, ".."))
        file_list = {
            "makefile_generated.mk": gendata_path,
            "makefile_config.mk": application_path,
        }
        for file, dir_path in file_list.items():
            file_target = os.path.abspath(os.path.join(dir_path, file))
            if not os.path.exists(file_target):
                continue
            func_modify(file_target)
        # 适配makefile_config.mk中的环境变量
        config_file_path = os.path.abspath(os.path.join(application_path, "makefile_config.mk"))
        if not os.path.exists(config_file_path):
            logger.info("action of modification is not necessary.")
            return
        target_str: list = ["STUDIO_PATH", "BUILD_TOOL_PATH", "GENDATA_PATH", "PROJECT_ROOT_PATH", "OUTPUT_PATH"]
        for target in target_str:
            new_value = ""
            if target == "STUDIO_PATH":
                new_value = os.path.relpath(studio_path, application_path)
            elif target == "BUILD_TOOL_PATH":
                build_path = os.path.join(root_path, "Build")
                new_value = os.path.relpath(build_path, application_path)
            elif target == "GENDATA_PATH":
                new_value = os.path.relpath(gendata_path, application_path)
            elif target == "PROJECT_ROOT_PATH":
                new_value = os.path.relpath(root_path, application_path)
            elif target == "OUTPUT_PATH":
                output_path = os.path.join(root_path, "Output")
                new_value = os.path.relpath(output_path, application_path)
            new_value = new_value.replace("\\", "/")
            new_value = target + " := " + new_value
            self.replace_line_in_file(config_file_path, target, new_value)

    def replace_line_in_file(self, filename, target_string, new_value):
        with open(filename, "r") as file:
            lines = file.readlines()

        replaced = False
        for i, line in enumerate(lines):
            if target_string in line:
                lines[i] = new_value + "\n"
                replaced = True
                break

        if replaced:
            with open(filename, "w") as file:
                file.writelines(lines)

    def init_empty_project(self, system_path=""):
        vcos_info = get_vcos_version_info(system_path=system_path)
        DEFAULT_PROJECT_INFO["system_version"] = vcos_info.system_version
        DEFAULT_PROJECT_INFO["version"] = vcos_info.studio_version
        self.info_dict = DEFAULT_PROJECT_INFO.copy()
        if system_path:
            self.info_dict["path"]["system_path"] = system_path
        return True

    def init_sys_info(self, obj: SysInfoClass, system_path=None) -> bool:
        obj.is_add_channel_name = self.info_dict.get("is_add_channel_name", False)
        obj.project = self.info_dict["project"]
        obj.version = self.info_dict["version"]
        obj.system_version = self.info_dict.get("system_version", "")
        obj.import_plugin_path_list = self.info_dict["path"].get("import_plugin_path_list", [])
        obj.compiler = self.info_dict["compiler"]
        obj.target = self.info_dict.get("target", "")
        obj.all_modules = set(self.info_dict["modules_info"].get("all_module_list", []))
        obj.enable_modules = set(self.info_dict["modules_info"]["enabled_module_list"])
        obj.validate_modules = set(self.info_dict["modules_info"].get("validation_module_list", []))
        obj.codegen_modules = set(self.info_dict["modules_info"]["codegen_module_list"])
        obj.codegen_swcs = set(self.info_dict["modules_info"].get("codegen_swc_list", []))
        obj.config_base_path = self.info_dict["path"]["config_base_path"]
        obj.gendata_path = self.info_dict["gendata_path"]
        obj.swc_template_path = self.info_dict["path"].get("swc_template_path", "")
        obj.bswcallout_path = self.info_dict["path"].get("bswcallout_path", "")
        obj.user_plugin_output_path = self.info_dict["path"].get(
            "user_plugin_output_path", self.info_dict["gendata_path"]
        )
        obj.project_path = self.info_dict["path"]["project_path"]
        obj.ldf = self.info_dict["path"]["config_file_path"]["ldf"]
        obj.dbc = self.info_dict["path"]["config_file_path"]["dbc"]
        obj.cdd = self.info_dict["path"]["config_file_path"]["cdd"]
        obj.excel = self.info_dict["path"]["config_file_path"].get("excel", {})
        obj.swc = self.info_dict["path"]["config_file_path"]["swc"]
        obj.eb_arxml = self.info_dict["path"]["config_file_path"]["eb_arxml"]
        obj.bsw_cfg = self.info_dict["path"]["config_file_path"].get("bsw_cfg", {})
        obj.communication = (
            os.path.join(obj.config_base_path, "system", "Communication.arxml") if obj.config_base_path else ""
        )
        obj.flatextract = (
            os.path.join(obj.config_base_path, "system", "FlatExtract.arxml") if obj.config_base_path else ""
        )
        obj.flatmap = obj.config_base_path
        obj.systemextract = obj.config_base_path
        obj.diagnostics_description_data = (
            os.path.join(obj.config_base_path, "system", "DiagnosticsDescriptionData.arxml")
            if obj.config_base_path
            else ""
        )
        obj.initial = os.path.join(obj.config_base_path, "system", "Initial.arxml") if obj.config_base_path else ""
        obj.studio_path = self.info_dict["path"]["studio_path"]
        obj.application_path = self.info_dict["path"]["application_path"]
        obj.internal_behavior_path = self.info_dict["path"]["internal_behavior_path"]
        obj.log_path = self.info_dict["path"]["log_path"]
        obj.service_component_path = self.info_dict["path"]["service_component_path"]
        obj.compiler_path = self.info_dict["path"]["compiler_path"]
        obj.mode = self.info_dict.get("mode", "")
        obj.mcal_path = self.info_dict["path"]["mcal_path"]
        obj.mcal_gendata_path = self.info_dict["path"]["mcal_gendata_path"]
        obj.bsw_ecuc_hash = self.info_dict["modules_info"].get("bsw_ecuc_hash", {})
        obj.incremental_generation = self.info_dict.get("incremental_generation", False)
        obj.system_path = self.info_dict["path"]["system_path"]
        obj.generation_limit = self.info_dict.get("generation_limit", "Error")
        obj.mcal_version = self.info_dict.get("MCAL_VERSION", "")
        if system_path is None:
            result = self.update_target_info(obj)
            if result is False:
                return False
        else:
            reslut = self.new_create_project_get_target_dict(system_path)
            obj.system_target_info.update(reslut)
        return True

    def update_target_info(self, obj: SysInfoClass):
        if not obj.system_path or not os.path.exists(obj.system_path):
            logger.ui_error(f"{obj.system_path} does not exist")
            return False

        if not obj.target:
            logger.ui_error(f"{obj.target} does not exist")
            return False

        obj.system_target_info.update({"module_cfg": {}})
        reslut = self.parse_studio_plug_in_cfg_json(obj.system_path)
        obj.system_target_info.update(reslut)
        if obj.target not in obj.system_target_info["target"].keys():
            logger.ui_error(f"{obj.target} does not exist")
            return False
        self.parse_linkage_cfg_json(obj)
        self.parse_plaform_cfg_json(obj)
        if not obj.mcal_version:
            self.update_mcal_version(obj)
        if obj.mcal_version not in obj.system_target_info["target"][obj.target]["MCAL_VERSION"]:
            logger.ui_error(
                f"{obj.mcal_version} does not exist, "
                f"please check {os.path.join(obj.system_path, 'components_plug_in_cfg.json')}"
            )
            return False
        obj.plug_in_path, obj.plug_in_bswmd_path, obj.plug_in_ib_path = self.get_plug_in_path(
            obj.system_path,
            obj.target,
            obj.system_target_info["target"][obj.target],
            obj.mcal_version,
            obj.import_plugin_path_list,
        )
        if not obj.system_version:
            vcos_info = get_vcos_version_info()
            obj.system_version = vcos_info.project_version
        return True

    def new_create_project_get_target_dict(self, system_path):
        system_target_info = {"module_cfg": {}}
        if system_path and os.path.exists(system_path):
            system_target_info = self.parse_studio_plug_in_cfg_json(system_path)
        return system_target_info

    def update_mcal_version(self, obj: SysInfoClass):
        if "target" not in obj.system_target_info or obj.target not in obj.system_target_info["target"]:
            return

        if (
            "MCAL_VERSION" not in obj.system_target_info["target"][obj.target]
            or len(obj.system_target_info["target"][obj.target]["MCAL_VERSION"]) < 1
        ):
            logger.ui_error(f"Unknown {obj.target} MCAL_VERSION")

        if not obj.mcal_version:
            obj.mcal_version = obj.system_target_info["target"][obj.target]["MCAL_VERSION"][0]

    def update_info_dict(self, obj: SysInfoClass):
        self.info_dict["is_add_channel_name"] = obj.is_add_channel_name
        self.info_dict["project"] = obj.project
        self.info_dict["version"] = obj.version
        self.info_dict["system_version"] = obj.system_version
        self.info_dict["compiler"] = obj.compiler
        self.info_dict["target"] = obj.target
        self.info_dict["mode"] = obj.mode
        self.info_dict["generation_limit"] = obj.generation_limit

        self.info_dict["modules_info"] = {}
        self.info_dict["modules_info"]["enabled_module_list"] = sorted(list(obj.enable_modules))
        self.info_dict["modules_info"]["codegen_module_list"] = sorted(list(obj.codegen_modules))
        self.info_dict["modules_info"]["validation_module_list"] = sorted(list(obj.validate_modules))
        self.info_dict["modules_info"]["codegen_swc_list"] = sorted(list(obj.codegen_swcs))
        self.info_dict["modules_info"]["bsw_ecuc_hash"] = dict(sorted(obj.bsw_ecuc_hash.items(), key=lambda x: (x[0])))

        self.info_dict["gendata_path"] = obj.gendata_path
        self.info_dict["path"] = {}
        self.info_dict["path"]["project_path"] = obj.project_path
        self.info_dict["path"]["config_base_path"] = obj.config_base_path
        self.info_dict["path"]["swc_template_path"] = obj.swc_template_path
        self.info_dict["path"]["bswcallout_path"] = obj.bswcallout_path
        self.info_dict["path"]["import_plugin_path_list"] = obj.import_plugin_path_list
        self.info_dict["path"]["user_plugin_output_path"] = obj.user_plugin_output_path

        self.info_dict["path"]["config_file_path"] = {}
        self.info_dict["path"]["config_file_path"]["ldf"] = obj.ldf
        self.info_dict["path"]["config_file_path"]["dbc"] = obj.dbc
        self.info_dict["path"]["config_file_path"]["cdd"] = obj.cdd
        self.info_dict["path"]["config_file_path"]["swc"] = obj.swc
        self.info_dict["path"]["config_file_path"]["eb_arxml"] = obj.eb_arxml
        if obj.excel:
            self.info_dict["path"]["config_file_path"]["excel"] = obj.excel
        self.info_dict["path"]["studio_path"] = obj.studio_path
        self.info_dict["path"]["application_path"] = obj.application_path
        self.info_dict["path"]["internal_behavior_path"] = obj.internal_behavior_path
        self.info_dict["path"]["log_path"] = obj.log_path
        self.info_dict["path"]["service_component_path"] = obj.service_component_path
        self.info_dict["path"]["compiler_path"] = obj.compiler_path
        self.info_dict["path"]["mcal_path"] = obj.mcal_path
        self.info_dict["path"]["mcal_gendata_path"] = obj.mcal_gendata_path
        self.info_dict["path"]["system_path"] = obj.system_path
        self.info_dict["MCAL_VERSION"] = obj.mcal_version

    @classmethod
    def get_plug_in_path(cls, system_path, target, target_info, mcal_version, import_plugin_path_list):
        plug_in_paths = {}
        plug_in_bswmd_path = {}
        plug_in_ib_path = {}
        studio_common_arxml_path = os.path.abspath(os.path.join(BASE_CONFIG_PATH, "common"))

        for each_path in import_plugin_path_list:
            for dirpath, dirnames, filenames in os.walk(each_path):
                for dirname in dirnames:
                    if dirname == "config_plug_in":
                        module_name = os.path.basename(dirpath)
                        plug_in_path = os.path.join(dirpath, dirname).replace("\\", "/")
                        plug_in_paths[module_name] = plug_in_path

                    if dirname == "bswmd":
                        module_name = os.path.basename(os.path.dirname(os.path.dirname(dirpath)))
                        plug_in_path = os.path.join(dirpath, dirname, target).replace("\\", "/")
                        if not os.path.exists(plug_in_path):
                            plug_in_path = os.path.join(dirpath, dirname, "comm_bswmd").replace("\\", "/")
                            if not os.path.exists(plug_in_path):
                                logger.warning(f"Could not find bswmd for {module_name}")
                                continue
                        plug_in_bswmd_path[module_name] = plug_in_path

                    if dirname == "internal_behavior":
                        module_name = os.path.basename(os.path.dirname(os.path.dirname(dirpath)))
                        plug_in_path = os.path.join(dirpath, dirname, target).replace("\\", "/")
                        if not os.path.exists(plug_in_path):
                            plug_in_path = os.path.join(dirpath, dirname, "comm_ib").replace("\\", "/")
                            if not os.path.exists(plug_in_path):
                                logger.warning(f"Could not find internal_behavior for {module_name}")
                                continue
                        plug_in_ib_path[module_name] = plug_in_path

        with open(os.path.join(system_path, "components_plug_in_cfg.json"), "r") as f:
            components_plug_in_cfg = json.loads(f.read())
            module_cfg = components_plug_in_cfg["module_cfg"]
            for module_name, module_info in module_cfg.items():
                if not module_info.get("plug_in_path"):
                    logger.warning(f"Could not find plug_in_path for {module_name}")
                    continue
                plug_in_path = os.path.join(system_path, module_info["plug_in_path"])
                plug_in_paths[module_name] = os.path.abspath(plug_in_path).replace("\\", "/")
                LoadPlugIn.append_sys_path(plug_in_path, module_name)

                bswmd_base_path = os.path.join(plug_in_path, "config_plug_in/base_config/bswmd")
                bswmd_path = os.path.join(bswmd_base_path, target)
                if not os.path.exists(bswmd_path):
                    bswmd_path = os.path.join(bswmd_base_path, "comm_bswmd")
                    if not os.path.exists(bswmd_path):
                        logger.warning(f"Could not find bswmd for {module_name}")
                        continue
                plug_in_bswmd_path[module_name] = os.path.abspath(bswmd_path).replace("\\", "/")

                ib_base_path = os.path.join(plug_in_path, "config_plug_in/base_config/internal_behavior")
                ib_path = os.path.join(ib_base_path, target)
                if not os.path.exists(ib_path):
                    ib_path = os.path.join(ib_base_path, "comm_ib")
                    if not os.path.exists(ib_path):
                        logger.debug(f"Could not find internal_behavior path for {module_name}")
                        continue
                plug_in_ib_path[module_name] = os.path.abspath(ib_path).replace("\\", "/")

        mcal_path = os.path.abspath(
            os.path.join(system_path, "platform_cfg", target_info["DERIVATIVE_GROUP"], target, mcal_version, "bswmd")
        )
        if not os.path.exists(mcal_path):
            return plug_in_paths, plug_in_bswmd_path, plug_in_ib_path

        for dirpath, dirnames, filenames in os.walk(mcal_path):
            for file_name in filenames:
                if file_name.split("_bswmd.arxml")[0] not in plug_in_bswmd_path:
                    plug_in_bswmd_path.update({file_name.split("_bswmd.arxml")[0]: mcal_path})
        mcal_path = os.path.abspath(os.path.join(studio_common_arxml_path, "bswmd"))
        if os.path.exists(mcal_path):
            for dirpath, dirnames, filenames in os.walk(mcal_path):
                for file_name in filenames:
                    if file_name.split("_bswmd.arxml")[0] not in plug_in_bswmd_path:
                        plug_in_bswmd_path.update({file_name.split("_bswmd.arxml")[0]: mcal_path})

        mcal_path = os.path.abspath(
            os.path.join(
                system_path, "platform_cfg", target_info["DERIVATIVE_GROUP"], target, mcal_version, "internal_behavior"
            )
        )
        if os.path.exists(mcal_path):
            for dirpath, dirnames, filenames in os.walk(mcal_path):
                for file_name in filenames:
                    if file_name.split("_ib_bswmd.arxml")[0] not in plug_in_ib_path:
                        plug_in_ib_path.update({file_name.split("_ib_bswmd.arxml")[0]: mcal_path})

        mcal_path = os.path.abspath(os.path.join(studio_common_arxml_path, "internal_behavior"))
        if not os.path.exists(mcal_path):
            return plug_in_paths, plug_in_bswmd_path, plug_in_ib_path
        for dirpath, dirnames, filenames in os.walk(mcal_path):
            for file_name in filenames:
                if file_name.split("_ib_bswmd.arxml")[0] not in plug_in_ib_path:
                    plug_in_ib_path.update({file_name.split("_ib_bswmd.arxml")[0]: mcal_path})
        return plug_in_paths, plug_in_bswmd_path, plug_in_ib_path

    def parse_studio_plug_in_cfg_json(self, system_path):
        system_cfg_json = {}
        if not os.path.exists(system_path):
            logger.ui_error(f"{system_path} not found")
            return system_cfg_json
        studio_sys_cfg_path = os.path.abspath(os.path.join(system_path, "components_plug_in_cfg.json"))
        if not os.path.exists(studio_sys_cfg_path):
            logger.ui_error(f"{studio_sys_cfg_path} not found")
            return system_cfg_json
        system_cfg_json = self.parse_json_cfg(studio_sys_cfg_path)

        return system_cfg_json

    def parse_plaform_cfg_json(self, obj: SysInfoClass):
        if not (
            "target" in obj.system_target_info
            and obj.target in obj.system_target_info["target"]
            and "DERIVATIVE_GROUP" in obj.system_target_info["target"][obj.target]
        ):
            logger.ui_error(f"system_cfg.json {obj.target} is failed")
            return False

        system_sys_cfg_path = os.path.abspath(
            os.path.join(
                obj.system_path,
                "platform_cfg",
                obj.system_target_info["target"][obj.target]["DERIVATIVE_GROUP"],
                obj.target,
                "platform_cfg.json",
            )
        )

        if not os.path.exists(system_sys_cfg_path):
            logger.ui_error(f"{system_sys_cfg_path} not found")
            return False
        system_sys_cfg_dict = self.parse_json_cfg(system_sys_cfg_path)
        if "module_cfg" not in obj.system_target_info:
            obj.system_target_info.update({"module_cfg": {}})
        obj.system_target_info["module_cfg"].update(system_sys_cfg_dict["module_cfg"])

        if "cmd_line_rules" not in obj.system_target_info:
            obj.system_target_info.update({"cmd_line_rules": {}})
        obj.system_target_info["cmd_line_rules"] = system_sys_cfg_dict["cmd_line_rules"]

        return True

    def parse_linkage_cfg_json(self, obj: SysInfoClass):
        """加载BSW配置项联动行为json文件"""
        if not os.path.exists(obj.system_path):
            logger.ui_error(f"{obj.system_path} not found")
        linkage_cfg_path = os.path.abspath(os.path.join(obj.system_path, "linkage_cfg.json"))
        if not os.path.exists(linkage_cfg_path):
            logger.ui_error(f"{linkage_cfg_path} not found")
        obj.linkage_cfg_dict.update(self.parse_json_cfg(linkage_cfg_path))
