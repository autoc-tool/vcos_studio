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
import glob
import time
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.autosar_utils.autosar_ecuc import AutosarEcuc, ArxmlConflict
from basic_func_module.file_handler.file_io_handler import FileIOHandler
from basic_func_module.base_logger import logger
from basic_func_module import hash_utils
from func_module.module_management.arxml_handler.arxml_validate import asw_arxml_validation
from basic_func_module.autosar_utils.utils import get_definition_ref, get_short_name

CUR_FILE_PATH = os.path.dirname(__file__)


class ArxmlParseHandler:

    @classmethod
    def parse_base_bswmd_arxml(cls, config_path: str = None):
        """load VCOS_BASE_MOD_ECUConfigurationParameters.arxml

        Args:
            config_path (str, optional): Defaults to None.

        Returns:
            _type_: _description_
        """

        mod_ecuc_parameters_def = os.path.abspath(
            os.path.join(
                CUR_FILE_PATH,
                "..",
                "..",
                "project_management",
                "base_config",
                "bswmd",
                "comm_bswmd",
                "VCOS_BASE_MOD_ECUConfigurationParameters.arxml",
            )
        )
        if not os.path.isfile(mod_ecuc_parameters_def):
            logger.exception(f"{mod_ecuc_parameters_def} does not exist")
            return None

        result = FileIOHandler.parse_arxml_file(mod_ecuc_parameters_def)
        if result is None:
            logger.exception(f"parse {mod_ecuc_parameters_def} failed")
            return None

        return result

    @classmethod
    def parse_platform_types_arxml(cls, config_path: str):
        """load PlatformTypes_AR4.arxml

        Args:
            config_path (_type_): _description_
        """
        file_path = os.path.join(config_path, "autosar", "PlatformTypes_AR4.arxml")
        if not os.path.isfile(file_path):
            logger.exception(f"{file_path} does not exist")
            return None

        autosar_class = FileIOHandler.parse_arxml_file(file_path)
        if autosar_class is None:
            logger.exception(f"parse {file_path} failed")
            return None

        return autosar_class

    @classmethod
    def parse_asw_arxml(cls, config_path):
        """load Asw.arxml

        Args:
            config_path (_type_): _description_
        """
        asw_arxml = os.path.join(config_path, "system", "Asw.arxml")
        if not os.path.isfile(asw_arxml):
            logger.debug(f"{asw_arxml} does not exist")
            return None

        autosar_class = FileIOHandler.parse_arxml_file(asw_arxml)
        if autosar_class is None:
            logger.exception(f"parse {asw_arxml} failed")
            return None

        return autosar_class

    @classmethod
    def parse_service_components_arxml(cls, config_path):
        """parse service swc arxml

        Args:
            config_path (_type_): _description_

        Raises:
            Exception: _description_

        Returns:
            _type_: _description_
        """
        service_autosar_dict = None
        service_arxml_folder = os.path.join(config_path, "service_components")
        service_arxml_folder = os.path.abspath(service_arxml_folder)
        service_arxml_file_list = AutosarUtil.get_arxml_file_from_path(service_arxml_folder)
        asw_arxml_validation.validate_arxml_with_xsd(service_arxml_file_list)
        try:
            service_autosar_dict, component_arxml_path_dict_info = AutosarUtil.merge_service_component_from_arxml(
                service_arxml_folder
            )
        except Exception as e:
            raise Exception("merge asw and service component error") from e

        return service_autosar_dict, component_arxml_path_dict_info

    @classmethod
    def asw_arxml_merge(cls, asw_arxml_folder, config_path):
        """asw arxml merge

        Args:
            main_window (_type_): _description_
            asw_arxml_folder (_type_): _description_
            config_path (_type_): _description_

        Raises:
            Exception: _description_

        Returns:
            _type_: _description_
        """
        arxml_files = AutosarUtil.get_arxml_file_from_path(asw_arxml_folder)
        return cls.asw_arxml_merge_logic(arxml_files, config_path)

    @classmethod
    def asw_arxml_merge_logic(cls, arxml_files: list, config_path):
        asw_arxml_validation.validate_arxml_with_xsd(arxml_files)
        component_arxml_path_dict_info = {}
        asw_autosar_dict = {}
        try:
            platform_arxml_path = os.path.join(config_path, "autosar", "PlatformTypes_AR4.arxml")
            system_extract_path = os.path.join(config_path, "system", "SystemExtract.arxml.new")
            service_arxml_folder = os.path.join(config_path, "service_components")
            service_arxml_file_list = AutosarUtil.get_arxml_file_from_path(service_arxml_folder)
            arxml_files.append(platform_arxml_path)
            if os.path.exists(system_extract_path):
                arxml_files.append(system_extract_path)
            arxml_files.extend(service_arxml_file_list)
            with AutosarUtil.gc_guard():
                _, component_arxml_path_dict_info = AutosarUtil.merge_arxml(asw_autosar_dict, arxml_files)
        except Exception:
            logger.exception("asw_arxml_merge")

        return asw_autosar_dict, component_arxml_path_dict_info

    @classmethod
    def get_module_ecuc_hash(
        cls, cfg_info_dict_bsw: dict, cfg_info_dict_rte: dict, gendata_path: str
    ):  # DOTO: 代码生成
        """生成模块的ECUC和源代码的哈希值

        Args:
            ecuc_autosar_dict (dict): 针对每个模块的AUTOSAR数据字典
            gendata_path (str): 包含生成的C和H文件的目录路径

        Returns:
            dict: 返回每个模块名称及其对应的AUTOSAR哈希值和代码哈希值的字典
        """
        hash_result = {"ret": False, "bsw": {}}
        try:
            for module_name, autosar_dict in cfg_info_dict_bsw.items():
                # AUTOSAR字典转换并计算哈希
                autosar_dict_hash = hash_utils.Hasher.compute_hash(autosar_dict)

                # 为代码内容初始化一个字符串，用来储存和计算哈希
                code_content = ""
                found_files = False  # 标记是否找到文件

                # 计算模块对应的代码文件哈希值
                module_path = os.path.join(gendata_path, module_name)
                for root, _, files in os.walk(module_path):
                    for fname in files:
                        if fname.endswith((".c", ".h")):
                            with open(os.path.join(root, fname), "r", encoding="utf-8") as file:
                                code_content += file.read()  # 添加文件内容
                                found_files = True

                # 检查是否找到文件，如果没有找到，就使用默认哈希值
                if not found_files:
                    code_hash = "EMPTY_DIRECTORY_HASH"
                else:
                    code_hash = hash_utils.Hasher.compute_hash(code_content)

                # 组合结果
                if module_name == "Rte":
                    # 计算Asw, task mapping,data mapping, port mapping hash 并跟新Rte hash
                    rte_dict_hash = hash_utils.Hasher.compute_hash(cfg_info_dict_rte)
                    combined_hash_input = rte_dict_hash + autosar_dict_hash
                    autosar_dict_hash = hash_utils.Hasher.compute_hash(combined_hash_input)
                hash_result["bsw"][module_name] = {
                    "autosar_hash": autosar_dict_hash,
                    "code_hash": code_hash,
                }
        except Exception:
            logger.exception("get_module_ecuc_hash")
            return hash_result
        hash_result["ret"] = True
        return hash_result

    @classmethod
    def module_ecuc_class_to_dict(cls, ecuc_autosar_dict):  # DOTO: 代码生成
        """_summary_

        Args:
            cfg_info_dict (_type_): _description_
            ecuc_autosar_dict (_type_): _description_
        """
        bsw_ecuc_dict = {}
        for module_name, autosar_obj in ecuc_autosar_dict.items():
            module_name: str
            ecuc_dict = AutosarUtil.to_bsw_dict(autosar_obj)
            bsw_ecuc_dict.update({module_name.lower(): ecuc_dict})
        return bsw_ecuc_dict

    @classmethod
    def parse_base_autosar_ecuc_arxml(cls, plug_in_path, target_name, module_list: set) -> dict:
        """_summary_

        Args:
            config_path (_type_): _description_
        """
        autosar_class_dict = {}
        for module_name in module_list:
            if module_name not in plug_in_path.keys():
                logger.debug(f"{module_name} not in plug_in_path")
                continue
            file_path = os.path.join(
                plug_in_path[module_name],
                "config_plug_in/base_config/base_ecuc",
                target_name,
                f"{module_name}_ecuc.arxml",
            ).replace("\\", "/")
            if os.path.exists(file_path) is False:
                file_path = os.path.join(
                    plug_in_path[module_name],
                    "config_plug_in/base_config/base_ecuc/comm_ecuc",
                    f"{module_name}_ecuc.arxml",
                ).replace("\\", "/")
                if os.path.exists(file_path) is False:
                    logger.debug(f"{file_path} does not exist")
            autosar_class = FileIOHandler.parse_arxml_file(file_path)
            if autosar_class is None:
                logger.debug(f"{file_path} parse failed")
                continue
            autosar_class_dict.update({module_name: autosar_class})

        return autosar_class_dict

    @classmethod
    def module_ecuc_class_to_ecuc_dict(cls, ecuc_autosar_dict):  # DOTO: 代码生成
        """_summary_

        Args:
            cfg_info_dict (_type_): _description_
            ecuc_autosar_dict (_type_): _description_
        """
        ecuc_dict = AutosarUtil.to_bsw_dict(ecuc_autosar_dict)

        return ecuc_dict

    @classmethod
    def parse_autosar_ecuc_arxml(cls, config_path, module_list: set):
        """_summary_

        Args:
            config_path (_type_): _description_
        """

        autosar_class_dict = {}
        for module_name in module_list:
            dir_path = os.path.join(config_path, "bsw", module_name)
            suffix = "arxml"
            file_list = glob.glob(f"{dir_path}/**/*.{suffix}", recursive=True)
            if not file_list:
                logger.debug(f"{module_name} has no arxml")
                continue
            obj_dict = {}
            for file in file_list:
                try:
                    obj = FileIOHandler.parse_arxml_file(file)
                except Exception:
                    logger.debug(f"Cannot parse file {file}")
                else:
                    rel_path = os.path.relpath(file, dir_path)
                    obj_dict[rel_path] = obj

            bak_file = f"{module_name}_ecuc.bak"
            bak_obj = FileIOHandler.parse_arxml_file(os.path.join(dir_path, bak_file))
            autosar_class = None
            if not bak_obj:
                if len(obj_dict) > 1:
                    logger.warning(
                        f"{module_name} has many config files, but not find .bak! Container order will be random!"
                    )
                    try:
                        arxml_str = AutosarEcuc.merge_ecuc_arxml(bak_obj, obj_dict)
                    except ArxmlConflict as e:
                        for info in e.conflicts:
                            logger.error(info)
                        raise e
                    autosar_class = AutosarUtil.parse_arxml_string(arxml_str)
                else:
                    autosar_class = next(iter(obj_dict.values()))
            else:
                try:
                    arxml_str = AutosarEcuc.merge_ecuc_arxml(bak_obj, obj_dict)
                except ArxmlConflict as e:
                    for info in e.conflicts:
                        logger.error(info)
                    raise e
                autosar_class = AutosarUtil.parse_arxml_string(arxml_str)

            # Record default file
            dft_file = ""
            if len(obj_dict) == 1:
                dft_file = next(iter(obj_dict.keys()))
            else:
                for file, obj in obj_dict.items():
                    if AutosarEcuc.check_default_label_sdg(obj.find(f"/ActiveEcuC/{module_name}")):
                        dft_file = file
                        break

            if not dft_file:
                dft_file = f"{module_name}_ecuc.arxml"
                logger.warning(f"Find no default file for {module_name}, use {module_name}_ecuc.arxml as default file")

            AutosarEcuc.record_default_file(autosar_class.find(f"/ActiveEcuC/{module_name}"), dft_file)

            if autosar_class is None:
                logger.debug(f"{dir_path} parse failed")
                continue

            autosar_class_dict.update({module_name: autosar_class})

        return autosar_class_dict

    @classmethod
    def parse_internal_behavior_arxml(cls, config_path, module_list, sys_target_dict) -> dict:
        """_summary_

        Args:
            config_path (_type_): _description_
        """

        autosar_class_dict = {}
        if not isinstance(sys_target_dict, dict):
            logger.error("Parse internal behavior failed: sys_target_dict type error")
            return autosar_class_dict
        module_cfg = sys_target_dict.get("module_cfg", None)
        if module_cfg is None:
            logger.error("Parse internal behavior failed: module_cfg is None")
            return autosar_class_dict
        for module_name in module_list:
            ib_file_support = module_cfg.get(module_name, {}).get("internal_behavior", {}).get("support", None)
            if ib_file_support:
                file_path = os.path.join(config_path, "internal_behavior", f"{module_name}_ib_bswmd.arxml")
                autosar_class = FileIOHandler.parse_arxml_file(file_path)
                if autosar_class is None:
                    logger.error(f"{file_path} parse failed")
                    continue
                autosar_class_dict.update({module_name: autosar_class})
            elif ib_file_support is None:
                logger.info(f"{module_name} internal behavior support parameter parse failed")
        return autosar_class_dict

    @classmethod
    def parse_base_internal_behavior_arxml(cls, plug_in_ib_path, target_name, module_list, sys_target_dict) -> dict:
        """_summary_

        Args:
            config_path (_type_): _description_
        """

        autosar_class_dict = {}
        if not isinstance(sys_target_dict, dict):
            logger.error("Parse base internal behavior failed: sys_target_dict type error")
            return autosar_class_dict
        module_cfg = sys_target_dict.get("module_cfg", None)
        if module_cfg is None:
            logger.error("Parse base internal behavior failed: module_cfg is None")
            return autosar_class_dict
        for module_name in module_list:
            if module_name not in plug_in_ib_path.keys():
                logger.debug(f"{module_name} not in plug_in_ib_path")
                continue
            ib_file_support = module_cfg.get(module_name, {}).get("internal_behavior", {}).get("support", None)
            if ib_file_support:
                file_path = os.path.join(plug_in_ib_path[module_name], f"{module_name}_ib_bswmd.arxml")
                if os.path.exists(file_path) is False:
                    logger.ui_error(f"{module_name} not in plug_in_ib_path")
                    return None
                autosar_class = FileIOHandler.parse_arxml_file(file_path)
                if autosar_class is None:
                    logger.error(f"{file_path} parse failed")
                    continue
                autosar_class_dict.update({module_name: autosar_class})
            elif ib_file_support is None:
                logger.error(f"{module_name} internal behavior support parameter parse failed")
        return autosar_class_dict

    @classmethod
    def parse_mcal_arxml(cls, mcal_path) -> dict:
        """_summary_

        Args:
            config_path (_type_): _description_
        """
        if os.path.exists(mcal_path) is False:
            logger.exception(f"{mcal_path} does not exist")
            return None

        autosar_class = FileIOHandler.parse_arxml_file(mcal_path)
        if autosar_class is None:
            logger.exception(f"parse {mcal_path} failed")
            return None

        return autosar_class

    @classmethod
    def parse_eth_arxml(cls, eth_path) -> dict:
        """_summary_

        Args:
            config_path (_type_): _description_
        """
        if not os.path.isfile(eth_path):
            logger.debug(f"{eth_path} does not exist")
            return None

        autosar_class = FileIOHandler.parse_arxml_file(eth_path)
        if autosar_class is None:
            logger.exception(f"parse {eth_path} failed")
            return None

        return autosar_class

    @classmethod
    def parse_merged_asw_arxml(cls, merged_asw_path) -> dict:
        """_summary_

        Args:
            config_path (_type_): _description_
        """

        if os.path.exists(merged_asw_path) is False:
            logger.exception(f"{merged_asw_path} does not exist")
            return None

        autosar_class = FileIOHandler.parse_arxml_file(merged_asw_path)
        if autosar_class is None:
            logger.exception(f"parse {merged_asw_path} failed")
            return None
        return autosar_class

    @classmethod
    def parse_diagnostics_description_data_arxml(cls, config_path):
        """_summary_

        Args:
            config_path (_type_): _description_
        """
        file_path = os.path.join(config_path, "system", "DiagnosticsDescriptionData.arxml")
        if not os.path.isfile(file_path):
            logger.debug(f"{file_path} does not exist")
            return None

        autosar_class = FileIOHandler.parse_arxml_file(file_path)
        if autosar_class is None:
            logger.exception(f"parse {file_path} failed")
            return None

        return autosar_class

    @classmethod
    def parse_flatextract_arxml(cls, config_path):
        """_summary_

        Args:
            config_path (_type_): _description_
        """
        file_path = os.path.join(config_path, "system", "FlatExtract.arxml")
        if not os.path.isfile(file_path):
            logger.debug(f"{file_path} does not exist")
            return None

        autosar_class = FileIOHandler.parse_arxml_file(file_path)
        if autosar_class is None:
            logger.exception(f"parse {file_path} failed")
            return None

        return autosar_class

    @classmethod
    def parse_all_bswmd_arxml(cls, plug_in_bswmd_path, module_names, target_name):
        """_summary_

        Args:
            config_path (_type_): _description_
            module_names (_type_): _description_

        Returns:
            _type_: _description_
        """
        mod_autosar_dict = {}
        for module_name in module_names:
            if module_name not in plug_in_bswmd_path.keys():
                logger.debug(f"{module_name} is not found in {plug_in_bswmd_path}")
                continue
            mod_ecuc_path = os.path.abspath(
                os.path.join(plug_in_bswmd_path[module_name], f"{module_name}_bswmd.arxml")
            ).replace("\\", "/")
            if os.path.exists(mod_ecuc_path) is False:
                logger.ui_error(f"{mod_ecuc_path} is not found")
                return None
            mod_ecuc_class = FileIOHandler.parse_arxml_file(mod_ecuc_path)
            if mod_ecuc_class:
                mod_autosar_dict[module_name] = mod_ecuc_class
        return mod_autosar_dict

    @classmethod
    def parse_initial_arxml(cls, config_path):
        """_summary_

        Args:
            config_path (_type_): _description_
        """

        file_path = os.path.join(config_path, "system", "Initial.arxml")
        if not os.path.isfile(file_path):
            logger.debug(f"{file_path} does not exist")
            return None

        autosar_class = FileIOHandler.parse_arxml_file(file_path)
        if autosar_class is None:
            logger.exception(f"parse {file_path} failed")
            return None

        return autosar_class

    @classmethod
    def parse_communication_arxml(cls, config_path):
        """_summary_

        Args:
            config_path (_type_): _description_
        """
        file_path = os.path.join(config_path, "system", "Communication.arxml")
        if not os.path.isfile(file_path):
            logger.debug(f"{file_path} does not exist")
            return None

        autosar_class = FileIOHandler.parse_arxml_file(file_path)
        if autosar_class is None:
            logger.exception(f"parse {file_path} failed")
            return None

        return autosar_class

    @classmethod
    def parse_system_extract_arxml(cls, config_path):
        """_summary_

        Args:
            config_path (_type_): _description_
        """
        file_path = os.path.join(config_path, "system", "SystemExtract.arxml")
        if not os.path.isfile(file_path):
            logger.debug(f"{file_path} does not exist")
            return None

        autosar_class = FileIOHandler.parse_arxml_file(file_path)
        if autosar_class is None:
            logger.exception(f"parse {file_path} failed")
            return None

        return autosar_class

    @classmethod
    def parse_system_dir_arxml(cls, config_path):
        """_summary_

        Args:
            config_path (_type_): _description_
        """
        sys_dir_class_dict = {}
        sys_dir_class_dict.update({"Communication": ArxmlParseHandler.parse_communication_arxml(config_path)})
        sys_dir_class_dict.update(
            {"DiagnosticsDescriptionData": ArxmlParseHandler.parse_diagnostics_description_data_arxml(config_path)}
        )
        sys_dir_class_dict.update({"FlatExtract": ArxmlParseHandler.parse_flatextract_arxml(config_path)})
        sys_dir_class_dict.update({"Initial": ArxmlParseHandler.parse_initial_arxml(config_path)})
        sys_dir_class_dict.update({"SystemExtract": ArxmlParseHandler.parse_system_extract_arxml(config_path)})

        return sys_dir_class_dict

    @classmethod
    def parse_ecuc_header(cls, config_path):
        ecuc_header_path = os.path.join(config_path, "base_ecuc", "ecuc_header.arxml")
        return AutosarUtil.parse_arxml(ecuc_header_path)

    @classmethod
    def check_mod_files_exist(cls, plug_in_bswmd_path, module_list: set):
        """_summary_

        Args:
            config_path (_type_): _description_
        """

        for module_name in module_list:
            if module_name not in plug_in_bswmd_path.keys():
                logger.debug(f"{module_name} not in {plug_in_bswmd_path}")
                continue
            file_path = os.path.join(plug_in_bswmd_path[module_name], f"{module_name}_bswmd.arxml").replace("\\", "/")

            if os.path.exists(file_path) is False:
                logger.ui_error(f"{file_path} is not found")
                return False
            else:
                return True

    @classmethod
    def get_ecuc_module_preifx(cls, ecuc_module_obj) -> str:
        # get one ecuc module cfg prefix
        ecuc_module_cfg = ecuc_module_obj.find_nodes("ECUC-MODULE-CONFIGURATION-VALUES")
        if not ecuc_module_cfg:
            return ""
        return get_definition_ref(ecuc_module_cfg[0]).split("/")[1] if ecuc_module_cfg else ""

    @classmethod
    def get_mod_perfix(self, module_name, mod_autosar_dict):
        perfix = ""
        if module_name in mod_autosar_dict:
            ar_package = getattr(getattr(mod_autosar_dict[module_name], "AR_PACKAGES", object()), "AR_PACKAGE", [])
            if len(ar_package) == 0:
                return perfix
            perfix = get_short_name(ar_package[0])
        else:
            perfix = None

        return perfix


class ArxmlSaveHandler:

    @classmethod
    def save_platform_types_arxml(cls, autosar_class, config_path):
        """_summary_

        Args:
            config_path (_type_): _description_
        """
        file_path = os.path.join(config_path, "autosar", "PlatformTypes_AR4.arxml")
        result = FileIOHandler.save_arxml_file(autosar_class, file_path)
        if result is False:
            logger.exception(f"{file_path} does not exist")
            return None
        return autosar_class

    @classmethod
    def get_different_modules(cls, enable_modules, unchanged_modules):
        # 将 unchanged_modules 转换为小写集合
        lower_unchanged_modules = {module.lower() for module in unchanged_modules}

        # 找出在 enable_modules 中大小写一致但在 unchanged_modules 中不存在的元素
        difference = [module for module in enable_modules if module.lower() not in lower_unchanged_modules]
        return difference

    @classmethod
    def save_bsw_ecuc_arxml(cls, autosar_class_dict, config_path, module_list: set) -> dict:
        """_summary_

        Args:
            config_path (_type_): _description_
        """
        for module_name in module_list:
            dir_path = os.path.join(config_path, "bsw", module_name)
            module_class = autosar_class_dict.get(module_name, None)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            if not module_class:
                logger.error(f"save {module_name} ecuc arxml failed, {module_name} has no ecuc obj")
                continue

            # Remove files in dir_path
            arxml_file_list = glob.glob(f"{dir_path}/**/*.arxml", recursive=True)
            bak_file_list = glob.glob(f"{dir_path}/**/*.bak", recursive=True)
            file_list = arxml_file_list + bak_file_list
            for file in file_list:
                os.remove(file)

            module_obj = module_class.find(f"/ActiveEcuC/{module_name}")
            dft_file = AutosarEcuc.peek_default_file(module_obj)
            dft_file = dft_file or f"{module_name}_ecuc.arxml"
            files_dict = AutosarEcuc.split_ecuc_arxml(module_class, dft_file)
            # Save bak file
            if len(files_dict) > 1:
                bak_path = os.path.join(config_path, "bsw", module_name, f"{module_name}_ecuc.bak")
                FileIOHandler.save_arxml_file(module_class, bak_path)
                logger.debug(f"Detect split for {module_name}, save bak file.")

            for file, arxml_str in files_dict.items():
                arxml_obj = AutosarUtil.parse_arxml_string(arxml_str)
                module_obj = arxml_obj.find(f"/ActiveEcuC/{module_name}")
                # Clear default file record first
                if module_obj is None:
                    logger.error(f"File '{file}' of '{module_name}' has some errors")
                AutosarEcuc.pop_default_file(module_obj)
                # Set simply SDG tag for default file
                if file == dft_file:
                    AutosarEcuc.set_default_label_sdg(module_obj)
                file_path = os.path.join(config_path, "bsw", module_name, file)
                result = FileIOHandler.save_arxml_file(arxml_obj, os.path.join(dir_path, file))
                if result is False:
                    logger.error(f"save {file_path} failed")
                    continue
                else:
                    logger.info(f"save {file_path} succeeded")
        return autosar_class_dict

    @classmethod
    def save_all_bsw_ecuc_arxml(cls, merged_autosar_class: object, file_path: str):
        if merged_autosar_class:
            result = FileIOHandler.save_arxml_file(merged_autosar_class, file_path)
            if result is False:
                logger.exception(f"save {file_path} failed")
                return None

    @classmethod
    def save_all_swc_components_arxml(cls, class_asw_autosar, config_path):
        """_summary_

        Args:
            class_asw_autosar (_type_): _description_
            config_path (_type_): _description_
        """

        if class_asw_autosar:
            asw_arxml = os.path.abspath(os.path.join(config_path, "system", "Asw.arxml"))
            result = FileIOHandler.save_arxml_file(class_asw_autosar, asw_arxml)
            if result is False:
                logger.exception(f"save {asw_arxml} failed")
                return None

    @classmethod
    def save_internal_behavior_arxml(cls, internal_behavior_autosar_dict, config_path, module_list: set) -> set:
        """_summary_

        Args:
            config_path (_type_): _description_
        """
        result_set = set()
        module_list = module_list
        for module_name, module_autosar in internal_behavior_autosar_dict.items():
            if module_autosar is None:
                logger.debug(f"No {module_name} data")
                continue
            file_path = os.path.join(config_path, "internal_behavior", f"{module_name}_ib_bswmd.arxml")
            result = FileIOHandler.save_arxml_file(module_autosar, file_path)
            if result is False:
                result_set.add(module_name)
                logger.debug(f"save {file_path} failed")

        return result_set

    @classmethod
    def save_service_components_arxml(cls, autosar_class_dict, config_path, module_list: set) -> set:
        """_summary_

        Args:
            config_path (_type_): _description_
        """

        result_set = set()
        for module_name in module_list:
            file_path = os.path.join(config_path, module_name, f"{module_name}_swc.arxml")
            module_class = autosar_class_dict.get(module_name, None)
            result = FileIOHandler.save_arxml_file(module_class, file_path)
            if result is False:
                result_set.add(module_name)
                logger.debug(f"save {file_path} failed")
        return result_set

    @classmethod
    def save_asw_arxml(cls, autosar_class, config_path) -> dict:
        """_summary_

        Args:
            config_path (_type_): _description_
        """

        file_path = os.path.join(config_path, "system", "Asw.arxml")
        result = FileIOHandler.save_arxml_file(autosar_class, file_path)
        if result is False:
            logger.debug(f"save {file_path} failed")
        return result

    @classmethod
    def save_diagnostics_description_data_arxml(cls, autosar_class, config_path):
        """_summary_

        Args:
            config_path (_type_): _description_
        """

        file_path = os.path.join(config_path, "system", "DiagnosticsDescriptionData.arxml")
        result = FileIOHandler.save_arxml_file(autosar_class, file_path)
        if result is False:
            logger.debug(f"save {file_path} failed")
        return result

    @classmethod
    def save_flatextract_arxml(cls, autosar_class, config_path):
        """_summary_

        Args:
            config_path (_type_): _description_
        """

        file_path = os.path.join(config_path, "system", "FlatExtract.arxml")
        result = FileIOHandler.save_arxml_file(autosar_class, file_path)
        if result is False:
            logger.debug(f"save {file_path} failed")
        return result

    @classmethod
    def save_initial_arxml(cls, autosar_class, config_path):
        """_summary_

        Args:
            config_path (_type_): _description_
        """

        file_path = os.path.join(config_path, "system", "Initial.arxml")
        result = FileIOHandler.save_arxml_file(autosar_class, file_path)
        if result is False:
            logger.debug(f"save {file_path} failed")
        return result

    @classmethod
    def save_communication_arxml(cls, autosar_class, config_path):
        """_summary_

        Args:
            config_path (_type_): _description_
        """

        file_path = os.path.join(config_path, "system", "Communication.arxml")
        result = FileIOHandler.save_arxml_file(autosar_class, file_path)
        if result is False:
            logger.debug(f"save {file_path} failed")

        return autosar_class

    @classmethod
    def save_systemextract_arxml(cls, autosar_class, config_path):
        """_summary_

        Args:
            config_path (_type_): _description_
        """

        file_path = os.path.join(config_path, "system", "SystemExtract.arxml")
        result = FileIOHandler.save_arxml_file(autosar_class, file_path)
        if result is False:
            logger.debug(f"save {file_path} failed")

        return autosar_class

    @classmethod
    def save_system_dir_arxml(cls, system_autosar_dict, config_path) -> bool:
        """_summary_

        Args:
            config_path (_type_): _description_
        """
        if not os.path.exists(config_path):
            logger.debug(f"{config_path} is not a directory")
        system_path = os.path.join(config_path, "system")
        if not os.path.exists(system_path):
            os.makedirs(system_path)

        if system_autosar_dict.get("DiagnosticsDescriptionData", None) is None:
            logger.debug("DiagnosticsDescriptionData Class is None")
        else:
            result = ArxmlSaveHandler.save_diagnostics_description_data_arxml(
                system_autosar_dict["DiagnosticsDescriptionData"], config_path
            )
            if result is None:
                return False

        if system_autosar_dict.get("FlatExtract", None) is None:
            logger.debug("FlatExtract is None")
        else:
            result = ArxmlSaveHandler.save_flatextract_arxml(system_autosar_dict["FlatExtract"], config_path)
            if result is None:
                return False

        if system_autosar_dict.get("Communication", None) is None:
            logger.debug("Communication is None")
        else:
            result = ArxmlSaveHandler.save_communication_arxml(system_autosar_dict["Communication"], config_path)
            if result is None:
                return False

        if system_autosar_dict.get("SystemExtract", None) is None:
            logger.debug("SystemExtract is None")
        else:
            result = ArxmlSaveHandler.save_systemextract_arxml(system_autosar_dict["SystemExtract"], config_path)
            if result is None:
                return False

        if system_autosar_dict.get("Initial", None) is None:
            logger.debug("Initial is None")
            return False
        else:
            result = ArxmlSaveHandler.save_initial_arxml(system_autosar_dict["Initial"], config_path)
            if result is None:
                return False

        return True


class ArxmlIncrementalSaveHandler:

    @classmethod
    def get_class_hash(cls, module_class):
        bsw_ecuc_dict = ArxmlParseHandler.module_ecuc_class_to_ecuc_dict(module_class)
        autosar_dict_hash = hash_utils.Hasher.compute_hash(bsw_ecuc_dict)
        return autosar_dict_hash

    @classmethod
    def ecuc_class_to_xml(cls, ecuc_autosar_dict):
        ecuc_dict = AutosarUtil.class_to_xml(ecuc_autosar_dict)
        return ecuc_dict

    @classmethod
    def get_autosar_class_hash(
        cls, system_autosar_class, ecuc_autosar_class, ib_autosar_class, asw_autosar_class, sys_info_class
    ):
        start_time = time.time()

        _cfg_hash = cls.get_asw_autosar_class_hash(asw_autosar_class)
        _cfg_hash = cls.get_autosar_ecuc_class_hash(sys_info_class.enable_modules, ecuc_autosar_class)
        sys_info_class.cfg_hash["bsw"].update(_cfg_hash)

        _cfg_hash = cls.get_autosar_internal_behavior_class_hash(sys_info_class.enable_modules, ib_autosar_class)
        sys_info_class.cfg_hash["internal_behavior"].update(_cfg_hash)

        _cfg_hash = cls.get_autosar_system_class_hash(system_autosar_class["FlatExtract"])
        if _cfg_hash:
            sys_info_class.cfg_hash["system"].update({"flatextract": _cfg_hash})

        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"总代码执行时间: {execution_time:.4f} 秒")

    @classmethod
    def get_asw_autosar_class_hash(cls, autosar_class):
        if not autosar_class:
            return ""
        _cfg_hash = ArxmlIncrementalSaveHandler.get_arxml_config_hash(autosar_class)

        return _cfg_hash

    @classmethod
    def get_autosar_ecuc_class_hash(cls, module_list, autosar_class):
        _cfg_hash = {}
        for module_name in module_list:
            if not autosar_class.get(module_name, None):
                hash_value = ""
            else:
                hash_value = ArxmlIncrementalSaveHandler.get_class_hash(autosar_class[module_name])

            _cfg_hash.update({module_name: hash_value})
        return _cfg_hash

    @classmethod
    def get_autosar_internal_behavior_class_hash(cls, module_list, autosar_class):
        _cfg_hash = {}
        for module_name in module_list:
            if not autosar_class.get(module_name, None):
                hash_value = ""
            else:
                hash_value = ArxmlIncrementalSaveHandler.get_arxml_config_hash(autosar_class[module_name])
            _cfg_hash.update({module_name: hash_value})
        return _cfg_hash

    @classmethod
    def get_autosar_system_class_hash(cls, autosar_class):
        if not autosar_class:
            _cfg_hash = ""
        else:
            _cfg_hash = cls.get_arxml_config_hash(autosar_class)
        return _cfg_hash

    @classmethod
    def incremental_save_bsw_ecuc_arxml(cls, cfg_hash, module_list, autosar_class_dict, config_path):
        try:
            _cfg_hash = {}
            incremental_bsw_module_list = set()
            start_time = time.time()
            for module_name in module_list:
                module_class = autosar_class_dict.get(module_name, None)
                if not module_class:
                    continue
                hash_value = ArxmlIncrementalSaveHandler.get_bsw_config_hash(module_name, module_class)
                _cfg_hash.update({module_name: hash_value})
                if module_name in cfg_hash["bsw"].keys() and cfg_hash["bsw"][module_name] == hash_value:
                    continue
                incremental_bsw_module_list.add(module_name)

            if len(incremental_bsw_module_list) > 0:
                ArxmlSaveHandler.save_bsw_ecuc_arxml(autosar_class_dict, config_path, incremental_bsw_module_list)
            for module_name in incremental_bsw_module_list:
                cfg_hash["bsw"].update({module_name: _cfg_hash[module_name]})

            end_time = time.time()
            execution_time = end_time - start_time
            logger.info(f"save_bsw_ecuc_arxml代码执行时间: {execution_time:.4f} 秒")
        except Exception as e:
            logger.error(f"save_bsw_ecuc_arxml {e}")
            print(f"{e}")

    @classmethod
    def incremental_save_system_ecuc_arxml(cls, cfg_hash, autosar_class_dict, config_path):
        cls.incremental_save_system_FlatExtract_ecuc_arxml(cfg_hash, autosar_class_dict, config_path)

    @classmethod
    def incremental_save_system_FlatExtract_ecuc_arxml(cls, cfg_hash, autosar_class_dict, config_path):
        try:
            _cfg_hash = {}
            start_time = time.time()
            if not os.path.exists(config_path):
                logger.debug(f"{config_path} is not a directory")
            system_path = os.path.join(config_path, "system")
            if not os.path.exists(system_path):
                os.makedirs(system_path)

            if autosar_class_dict.get("FlatExtract", None) is None:
                logger.debug("FlatExtract is None")
            else:
                hash_value = cls.get_arxml_config_hash(autosar_class_dict["FlatExtract"])
                _cfg_hash.update({"FlatExtract": hash_value})
                if "FlatExtract" not in cfg_hash.keys() or (
                    "FlatExtract" in cfg_hash.keys() and cfg_hash["FlatExtract"] != hash_value
                ):
                    result = ArxmlSaveHandler.save_flatextract_arxml(autosar_class_dict["FlatExtract"], config_path)
                    if result is None:
                        return False
                    else:
                        cfg_hash.update({"FlatExtract": hash_value})
                        logger.info("FlatExtract saved successfully")

            end_time = time.time()
            execution_time = end_time - start_time
            logger.info(f"incremental_save_system_ecuc_arxml代码执行时间: {execution_time:.4f} 秒")
        except Exception as e:
            logger.error(f"incremental_save_system_ecuc_arxml failed {e}")

    @classmethod
    def incremental_internal_behavior_ecuc_arxml(cls, cfg_hash, autosar_class_dict, config_path, module_list: set):
        try:
            _cfg_hash = {}
            incremental_bsw_module_list = set()
            start_time = time.time()
            for module_name, module_autosar in autosar_class_dict.items():
                if not autosar_class_dict.get(module_name, None):
                    logger.debug(f"No {module_name} data")
                    continue
                hash_value = cls.get_arxml_config_hash(module_autosar)
                _cfg_hash.update({"internal_behavior": {module_name: hash_value}})
                if "internal_behavior" not in cfg_hash.keys() or (
                    "internal_behavior" in cfg_hash.keys()
                    and module_name in cfg_hash["internal_behavior"]
                    and cfg_hash["internal_behavior"][module_name] == hash_value
                ):
                    continue

            if len(incremental_bsw_module_list) > 0:
                ArxmlSaveHandler.save_internal_behavior_arxml(
                    autosar_class_dict, config_path, incremental_bsw_module_list
                )

            for module_name in incremental_bsw_module_list:
                cfg_hash.update({module_name: _cfg_hash[module_name]})

            end_time = time.time()
            execution_time = end_time - start_time
            logger.info(f"internal_behavior_ecuc_arxml代码执行时间: {execution_time:.4f} 秒")
        except Exception as e:
            logger.error(f"internal_behavior_ecuc_arxml代码执行时间 failed {e}")

    @classmethod
    def incremental_system_asw_ecuc_arxml(cls, cfg_hash, autosar_class_dict, config_path):

        try:
            _cfg_hash = {}
            start_time = time.time()

            hash_value = cls.get_arxml_config_hash(autosar_class_dict)
            _cfg_hash.update({"system_asw": hash_value})
            if "system_asw" not in cfg_hash.keys() or (
                "system_asw" in cfg_hash.keys() and cfg_hash["system_asw"] != hash_value
            ):
                result = ArxmlSaveHandler.save_all_swc_components_arxml(autosar_class_dict, config_path)
                if result is False:
                    logger.ui_debug("save system_asw failed")
                else:
                    cfg_hash.update({"system_asw": hash_value})
                    logger.ui_debug("save system_asw succeeded")

            end_time = time.time()
            execution_time = end_time - start_time
            logger.info(f"system_asw_ecuc_arxml代码执行时间: {execution_time:.4f} 秒")
        except Exception as e:
            logger.error(f"system_asw_ecuc_arxml代码执行时间 failed {e}")

    @classmethod
    def get_bsw_config_hash(cls, module_name, module_class):
        bsw_ecuc_dict = ArxmlParseHandler.module_ecuc_class_to_ecuc_dict(module_class)
        autosar_dict_hash = hash_utils.Hasher.compute_hash(bsw_ecuc_dict)
        return autosar_dict_hash

    @classmethod
    def get_arxml_config_hash(cls, module_class):
        bsw_ecuc_dict = cls.ecuc_class_to_xml(module_class)
        autosar_dict_hash = hash_utils.Hasher.compute_hash(bsw_ecuc_dict)
        return autosar_dict_hash
