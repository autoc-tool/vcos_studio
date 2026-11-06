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
"""
rte代码生成模块.

解析输入的josn object, 然后生成rte代码.
"""
from basic_func_module.autosar_utils.utils import get_mod_autosar_version

from func_module.health_monitor.logger import logger
from func_module.generator.bsw import generator as bsw_generator
from func_module.generator.rte import generator as rte_generator
from func_module.generator.appl import generator as appl_generator
from func_module.generator.sim import generator as sim_generator
from func_module.generator.cmake import generator as cmake_generator
from func_module.generator.common.user_code_extract import UserCodeExtract
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlParseHandler

from func_module.generator import parser as codegen_parser
from func_module.generator.common.common import ErrorCode
from func_module.health_monitor import perf_record
import os

CUR_PATH = os.path.dirname(os.path.abspath(__file__))


def init_codegen_autosar_dict(data_management, is_for_swc=False) -> dict:
    if is_for_swc:
        return {
            "asw_autosar_dict": {
                "FlatExtract": data_management.autosar_system_class["FlatExtract"],
                "asw": data_management.autosar_asw_class,
            },
            "ecuc_autosar_dict": data_management.autosar_bsw_class,
            "system_autosar_dict": data_management.autosar_system_class,
            "internal_behavior_autosar_dict": data_management.autosar_ib_class,
            "bswmd_autosar_dict": data_management.autosar_bswmd_class,
        }
    else:
        return {
            "asw_autosar_dict": {
                "FlatExtract": data_management.autosar_system_class["FlatExtract"],
                "asw": data_management.autosar_asw_class,
            },
            "ecuc_autosar_dict": data_management.autosar_bsw_class,
            "system_autosar_dict": data_management.autosar_system_class,
            "internal_behavior_autosar_dict": data_management.autosar_ib_class,
            "sys_target_dict": data_management.sys_target_dict,
            "bswmd_autosar_dict": data_management.autosar_bswmd_class,
        }


def parse_config_dict(
    sys_info_class, codegen_autosar_dict, enable_bsw_instance=True, other_info={"rte_parse_new_dict": True}
) -> dict:
    sys_info_dict = get_sys_info_dict(sys_info_class, codegen_autosar_dict=codegen_autosar_dict)
    codegen_module_list = sys_info_dict.get("modules_info", {}).get("codegen_module_list", [])
    enabled_module_list = sys_info_dict.get("modules_info", {}).get("enabled_module_list", [])

    cfg_info_dict = {"asw": "", "rte": {}, "bsw": {}, "dbc": [], "ldf": [], "cdd": {}, "eb": {}}
    asw_autosar_dict = codegen_autosar_dict["asw_autosar_dict"]
    system_autosar_dict = codegen_autosar_dict["system_autosar_dict"]
    internal_behavior_autosar_dict = codegen_autosar_dict["internal_behavior_autosar_dict"]
    ecuc_autosar_dict = codegen_autosar_dict["ecuc_autosar_dict"]
    module_cfg = codegen_autosar_dict.get("sys_target_dict", {}).get("module_cfg", {})
    bswmd_autosar_dict = codegen_autosar_dict["bswmd_autosar_dict"]

    ret = codegen_parser.get_config_dict(
        codegen_module_list,
        cfg_info_dict,
        asw_autosar_dict,
        ecuc_autosar_dict,
        system_autosar_dict,
        internal_behavior_autosar_dict,
        module_cfg,
        enabled_module_list,
        enable_bsw_instance,
        bswmd_autosar_dict,
        other_info=other_info,
    )
    cfg_info_dict["parser_ret"] = ret
    return cfg_info_dict


@perf_record.log_function_stats(["代码生成", "模块C代码生成"])
def generate_c_code(
    sys_info_class,
    codegen_autosar_dict,
    progress_signal=None,
    result_signal=None,
    other_info={"rte_parse_new_dict": True},
) -> bool:
    rte_result_dict = {"Rte": {"result": False}}
    darwin_result_dict = {"Darwin": {"result": True}}
    sys_info_dict = get_sys_info_dict(sys_info_class, codegen_autosar_dict=codegen_autosar_dict)
    codegen_module_list = sys_info_dict.get("modules_info", {}).get("codegen_module_list", [])
    ecuc_autosar_dict = codegen_autosar_dict["ecuc_autosar_dict"]
    module_cfg = codegen_autosar_dict.get("sys_target_dict", {}).get("module_cfg", {})
    mcal_module_codegen_cmd_line_dict = codegen_autosar_dict.get("sys_target_dict", {}).get(
        "mcal_module_codegen_cmd_line_dict", {}
    )
    enable_bsw_instance = True
    logger.info(f"Start the code generator of the {sys_info_dict['project']}!")
    logger.info(f"Generation list : {codegen_module_list}")

    cfg_info_dict = parse_config_dict(
        sys_info_class, codegen_autosar_dict, enable_bsw_instance=enable_bsw_instance, other_info=other_info
    )
    parser_ret = cfg_info_dict["parser_ret"]

    bsw_ecuc_dict = bsw_ecuc_class_to_bsw_ecuc_dict(ecuc_autosar_dict)
    cfg_info_dict["bsw"] = bsw_ecuc_dict

    bsw_ecuc_hash_result = ArxmlParseHandler.get_module_ecuc_hash(
        cfg_info_dict["bsw"], cfg_info_dict["rte"], sys_info_dict.get("gendata_path", "")
    )
    unchanged_modules = []
    if bsw_ecuc_hash_result["ret"]:
        unchanged_modules = update_ecuc_hash_and_codegen_list(
            sys_info_class.bsw_ecuc_hash,
            codegen_module_list,
            bsw_ecuc_hash_result,
            sys_info_class.incremental_generation,
        )

    logger.ui_info(f"Generation list : {codegen_module_list}")
    if sys_info_class.incremental_generation and "Rte" not in codegen_module_list:
        parser_ret = ErrorCode.NO_CODEGEN if parser_ret == ErrorCode.RTE_CODEGEN else parser_ret
    if parser_ret != ErrorCode.NO_CODEGEN and parser_ret:
        progress_signal.emit("Generating Rte/Schm c/h code ...")
        user_code = {}  # 生成rte代码时，不获取模版文件中的user_code
        rte_result_dict = generate_rte_c_code(sys_info_dict, cfg_info_dict, user_code, parser_ret, ecuc_autosar_dict)

    progress_signal.emit("Generating Bsw c code ...")
    for module_name, bswmd_obj in codegen_autosar_dict.get("bswmd_autosar_dict", {}).items():
        module_cfg.get(module_name, {})["autosar_version"] = get_mod_autosar_version(bswmd_obj)
    bsw_result_dict = generate_bsw_c_code(
        sys_info_dict, cfg_info_dict, ecuc_autosar_dict, module_cfg, mcal_module_codegen_cmd_line_dict, progress_signal
    )

    sim_result_dict = generate_sim_c_code(
        sys_info_dict, cfg_info_dict, ecuc_autosar_dict, module_cfg, progress_signal
    )

    cmake_result_dict = cmake_generator.generate_project_cmake(sys_info_dict)

    codegen_result = report_codegen_result(
        cmake_result_dict, rte_result_dict, darwin_result_dict, bsw_result_dict, codegen_module_list
    )
    logger.ui_info(f"Finish the code generator of the {sys_info_dict['project']}")
    if codegen_result:
        cfg_info_dict["bsw"] = bsw_ecuc_class_to_bsw_ecuc_dict(ecuc_autosar_dict)
        bsw_ecuc_hash_result = ArxmlParseHandler.get_module_ecuc_hash(
            cfg_info_dict["bsw"], cfg_info_dict["rte"], sys_info_dict.get("gendata_path", "")
        )
        # bsw_ecuc_hash_result.update({"unchanged_modules": unchanged_modules})
        update_codegen_hash(sys_info_class.bsw_ecuc_hash, bsw_ecuc_hash_result, codegen_module_list, unchanged_modules)
        # sys_info_class.bsw_ecuc_hash.clear()
        # sys_info_class.bsw_ecuc_hash.update(bsw_ecuc_hash_result)
    return codegen_result


def get_sys_info_dict(sys_info_class, codegen_autosar_dict=None):
    sys_info_dict = {
        "project": sys_info_class.project,
        "version": sys_info_class.version,
        "compiler": sys_info_class.compiler,
        "target": sys_info_class.target,
        "project_path": sys_info_class.project_path,
        "mode": sys_info_class.mode,
        "incremental_generation": sys_info_class.incremental_generation,
        "sim_mode": sys_info_class.sim_mode,
        "modules_info": {
            "all_module_list": sorted(list(sys_info_class.all_modules)),
            "enabled_module_list": sorted(list(sys_info_class.enable_modules)),
            "codegen_module_dict": sys_info_class.codegen_module_dict,
            "codegen_module_list": sorted(list(sys_info_class.codegen_modules)),
            "kfg_module_enabled_list": sys_info_class.kfg_module_enabled_list,
            "kfg_module_all_list": sys_info_class.kfg_module_all_list,
            "vcos_mtnce_macro_list": {},
            "vcos_os_macro_list": {},
            "bsw_ecuc_hash": sys_info_class.bsw_ecuc_hash,
        },
        "config_path": sys_info_class.config_base_path,
        "gendata_path": sys_info_class.gendata_path,
        "path": {
            "config_base_path": sys_info_class.config_base_path,
            "swc_template_path": sys_info_class.swc_template_path,
            "bswcallout_path": sys_info_class.bswcallout_path,
            "user_plugin_output_path": (
                sys_info_class.user_plugin_output_path
                if sys_info_class.user_plugin_output_path
                else sys_info_class.gendata_path
            ),
            "studio_path": sys_info_class.studio_path,
            "application_path": sys_info_class.application_path,
            "internal_behavior_path": sys_info_class.internal_behavior_path,
            "log_path": sys_info_class.log_path,
            "service_component_path": sys_info_class.service_component_path,
            "compiler_path": sys_info_class.compiler_path,
            "project_path": sys_info_class.project_path,
            "mcal_path": sys_info_class.mcal_path,
            "mcal_gendata_path": sys_info_class.mcal_gendata_path,
            "system_path": sys_info_class.system_path,
            "import_plugin_path_list": sys_info_class.import_plugin_path_list,
        },
        "studio_path": sys_info_class.studio_path,
        "plug_in_path": sys_info_class.plug_in_path,
        "mcal_version": sys_info_class.mcal_version,
        "sys_target_dict": sys_info_class.system_target_info,
    }

    # 追加mcal模块列表和普通bsw模块列表
    if codegen_autosar_dict is not None:
        mcal_cfg_dict = codegen_autosar_dict.get("sys_target_dict", {}).get("module_cfg", {})
        mcal_module_list = [mod_name for mod_name, cfg in mcal_cfg_dict.items() if cfg.get("is_mcal") is True]
        common_bsw_module_list = [mod_name for mod_name, cfg in mcal_cfg_dict.items() if cfg.get("is_mcal") is not True]

        modules_info = sys_info_dict.setdefault("modules_info", {})  # 保证modules_info存在
        modules_info["mcal_module_list"] = mcal_module_list
        modules_info["common_bsw_module_list"] = common_bsw_module_list
        sys_info_dict["sys_target_dict"] = codegen_autosar_dict.get("sys_target_dict", {})

    return sys_info_dict


def generate_swc_template(sys_info_class, codegen_autosar_dict, swc_app_list, result_signal=None):
    appl_codegen_result = False
    try:
        sys_info_dict = get_sys_info_dict(sys_info_class, codegen_autosar_dict=codegen_autosar_dict)
        enable_bsw_instance = True
        codegen_module_list = sys_info_dict.get("modules_info", {}).get("codegen_module_list", [])
        enabled_module_list = sys_info_dict.get("modules_info", {}).get("enabled_module_list", [])
        asw_autosar_dict = codegen_autosar_dict["asw_autosar_dict"]
        cfg_info_dict = {"asw": "", "rte": {}, "bsw": {}, "dbc": [], "ldf": [], "cdd": {}, "eb": {}}
        if "Rte" not in codegen_module_list:
            codegen_module_list.append("Rte")
        if not codegen_parser.get_config_dict(
            codegen_module_list,
            cfg_info_dict,
            asw_autosar_dict,
            codegen_autosar_dict["ecuc_autosar_dict"],
            codegen_autosar_dict["system_autosar_dict"],
            codegen_autosar_dict["internal_behavior_autosar_dict"],
            {},
            enabled_module_list,
            enable_bsw_instance,
            codegen_autosar_dict["bswmd_autosar_dict"],
        ):
            return appl_codegen_result
        user_code = UserCodeExtract.get_user_code(sys_info_dict, asw_autosar_dict, swc_app_list)
        appl_codegen_result = appl_generator.generate(
            sys_info_dict, cfg_info_dict, asw_autosar_dict, user_code, swc_app_list
        )
    except Exception:
        logger.exception("generate_swc_template")
    return appl_codegen_result


def get_swc_list_for_template_gereration(asw_autosar_dict):
    return codegen_parser.get_swc_list(asw_autosar_dict)


def report_codegen_result(cmake_result_dict, rte_result_dict, darwin_result_dict, bsw_result_dict, codegen_module_list):
    codegen_result = True
    result_dict = {}

    if cmake_result_dict:
        result_dict.update(cmake_result_dict)

    if rte_result_dict:
        result_dict.update(rte_result_dict)

    if darwin_result_dict:
        result_dict.update(darwin_result_dict)

    if bsw_result_dict:
        result_dict.update(bsw_result_dict["bsw"])

    for module, result in result_dict.items():
        if module not in codegen_module_list and module not in ["MemMap", "vcosMtnce"]:
            continue
        if module in ["MemMap"] and "Rte" not in codegen_module_list:
            continue
        if result["result"] is None:
            logger.ui_warning(f"{module} module generate_dynamic_code do not have return value")
        if result["result"] is False:
            codegen_result = False
            logger.ui_error(f"{module} module generate c code failed")
        if result["result"] is True:
            logger.ui_info(f"{module} module generate c code successful")

    return codegen_result


def bsw_ecuc_class_to_bsw_ecuc_dict(ecuc_autosar_dict):
    bsw_ecuc_dict = ArxmlParseHandler.module_ecuc_class_to_dict(ecuc_autosar_dict)

    return bsw_ecuc_dict


def generate_bsw_c_code(
    sys_info_dict, cfg_info_dict, ecuc_autosar_dict, module_cfg, mcal_module_codegen_cmd_line_dict, progress_signal
):
    bsw_result_dict = bsw_generator.generate(
        sys_info_dict, cfg_info_dict, ecuc_autosar_dict, module_cfg, mcal_module_codegen_cmd_line_dict, progress_signal
    )
    return bsw_result_dict

def generate_sim_c_code(
    sys_info_dict, cfg_info_dict, ecuc_autosar_dict, module_cfg, progress_signal
):
    sim_result_dict = sim_generator.generate(
        sys_info_dict, cfg_info_dict, ecuc_autosar_dict, module_cfg, progress_signal
    )
    return sim_result_dict

def generate_rte_c_code(sys_info_dict, cfg_info_dict, user_code, parser_ret, ecuc_autosar_dict=None):
    rte_result_dict = rte_generator.generate(sys_info_dict, cfg_info_dict, user_code, parser_ret, ecuc_autosar_dict)
    return rte_result_dict


def find_no_change_bsw_modules(original_bsw_ecuc_hash, new_bsw_ecuc_hash):
    unchanged_modules = []
    if "bsw" not in original_bsw_ecuc_hash:
        return []
    for module_name, hashes in original_bsw_ecuc_hash["bsw"].items():
        # 检查模块是否也在新的字典中
        if not isinstance(hashes, dict):
            return unchanged_modules
        if module_name in new_bsw_ecuc_hash["bsw"]:
            # 获取新字典中相同名称的模块哈希值
            new_hashes = new_bsw_ecuc_hash["bsw"][module_name]

            # 检查autosar_hash和code_hash是否都没有变化
            if hashes["autosar_hash"] == new_hashes["autosar_hash"] and hashes["code_hash"] == new_hashes["code_hash"]:
                # 如果都没有变化，将模块名添加到结果列表中
                unchanged_modules.append(module_name)
    return unchanged_modules


def update_ecuc_hash_and_codegen_list(
    original_bsw_ecuc_hash, codegen_module_list, new_bsw_ecuc_hash, incremental_generation=True
):
    no_change_bsw_modules = []
    if incremental_generation:
        # 查找未更改的BSW模块，并将模块名转换为小写
        no_change_bsw_modules = find_no_change_bsw_modules(original_bsw_ecuc_hash, new_bsw_ecuc_hash)
        no_change_bsw_modules = [module.lower() for module in no_change_bsw_modules]

        # 将codegen_module_list中的模块名转换为小写
        codegen_module_list_lower = [module.lower() for module in codegen_module_list]

        # 执行集合操作
        setA = set(codegen_module_list_lower)
        setB = set(no_change_bsw_modules)
        intersection_set = setA.intersection(setB)

        # 日志记录
        logger.ui_info(
            f"The following {list(intersection_set)} modules have not been modified, "
            "and the code will not be regenerated."
        )

        # 更新原始codegen_module_list，保留顺序但剔除未更改的模块
        codegen_module_list[:] = sorted([module for module in codegen_module_list if module.lower() not in setB])
    return no_change_bsw_modules
    # original_bsw_ecuc_hash.clear()
    # original_bsw_ecuc_hash.update(new_bsw_ecuc_hash)


def update_codegen_hash(sys_info_class_bsw_ecuc_hash, bsw_ecuc_hash_result, codegen_module_list, unchanged_modules):
    """
    更新sys_info_class_bsw_ecuc_hash的内容，只有在codegen_module_list的模块才会被更新
    :param sys_info_class_bsw_ecuc_hash: 当前的bsw_ecuc_hash（字典形式）
    :param bsw_ecuc_hash_result: 新的bsw_ecuc_hash结果（字典形式）
    :param codegen_module_list: 需要更新的模块列表
    """
    if "ret" in sys_info_class_bsw_ecuc_hash:
        del sys_info_class_bsw_ecuc_hash["ret"]
    if "bsw" not in sys_info_class_bsw_ecuc_hash:
        sys_info_class_bsw_ecuc_hash.clear()
        sys_info_class_bsw_ecuc_hash.update({"bsw": {}})
    sys_info_class_bsw_ecuc_hash.update({"unchanged_modules": unchanged_modules})
    for module in codegen_module_list:
        if module.lower() in bsw_ecuc_hash_result["bsw"]:
            if module.lower() in sys_info_class_bsw_ecuc_hash["bsw"]:
                sys_info_class_bsw_ecuc_hash["bsw"][module.lower()].update(bsw_ecuc_hash_result["bsw"][module.lower()])
            else:
                sys_info_class_bsw_ecuc_hash["bsw"].update(
                    {module.lower(): bsw_ecuc_hash_result["bsw"][module.lower()]}
                )
