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
import re
from func_module.health_monitor.logger import logger
from basic_func_module.autosar_utils.autosar_utils import AutosarUtils


class UserCodeExtract:
    # temp list, append other keys if required
    mem_key_list = ["const_mem", "calib_mem", "pri_ini_mem", "pri_no_ini_mem"]
    mem_patterns = {key: "" for key in mem_key_list}
    mem_patterns["const_mem"] = (
        r'#define (\w+)_START_SEC_CONST_UNSPECIFIED\n#include "\1_MemMap.h"\n(.*?)\n'
        r'#define \1_STOP_SEC_CONST_UNSPECIFIED\n#include "\1_MemMap.h"'
    )
    mem_patterns["calib_mem"] = (
        r'#define (\w+)_START_SEC_CALIB_CONST_UNSPECIFIED\n#include "\1_MemMap.h"\n(.*?)\n'
        r'#define \1_STOP_SEC_CALIB_CONST_UNSPECIFIED\n#include "\1_MemMap.h"'
    )
    mem_patterns["pri_ini_mem"] = (
        r'#define (\w+)_START_SEC_PRIVATE_(\w+)_VAR_INIT_UNSPECIFIED\n#include "\1_MemMap.h"\n(.*?)\n'
        r'#define \1_STOP_SEC_PRIVATE_\2_VAR_INIT_UNSPECIFIED\n#include "\1_MemMap.h"'
    )
    mem_patterns["pri_no_ini_mem"] = (
        r'#define (\w+)_START_SEC_PRIVATE_(\w+)_VAR_NO_INIT_UNSPECIFIED\n#include "\1_MemMap.h"\n(.*?)\n'
        r'#define \1_STOP_SEC_PRIVATE_\2_VAR_NO_INIT_UNSPECIFIED\n#include "\1_MemMap.h"'
    )
    user_code_pattern = (
        r"/\*+USER CODE STARTS!\*+\*+THIS COMMENT WILL BE SAVED!"
        r"\*+\*/\n(.*?)\n/\*+USER CODE ENDS!\*+\*+THIS COMMENT WILL BE SAVED!\*+\*/"
    )

    def __init__(self):
        pass

    @classmethod
    def user_code(cls, folder_path, swc_runnable, swc_app_list):
        user_code_dict = {}
        files = os.listdir(folder_path)
        for file in files:
            if file.endswith(".c"):
                swc_name = file.replace(".c", "")
                if swc_name not in swc_runnable or swc_name not in swc_app_list:
                    continue
                file_path = os.path.join(folder_path, file)  # 各个文件的路径
                with open(file_path, encoding="utf-8") as f:
                    # 格式问题检测，有问题直接跳过主功能代码
                    text = f.read()  # 整个文件读成一个字符串
                    left_bracket_count = text.count("{")
                    right_bracket_count = text.count("}")
                    if left_bracket_count != right_bracket_count:
                        logger.warning(f"The number of left bracket and right bracket in {file} is not the same!!!")
                        continue
                    user_code_start_string = (
                        "/******************USER CODE STARTS!************THIS COMMENT WILL BE SAVED!***************/"
                    )
                    user_code_end_string = (
                        "/******************USER CODE ENDS!**************THIS COMMENT WILL BE SAVED!***************/"
                    )
                    uc_start_count = text.count(user_code_start_string)
                    uc_end_count = text.count(user_code_end_string)
                    if uc_start_count != uc_end_count:
                        logger.warning(
                            f"The number of user_code_start_string and user_code_end_string in {file} is not the same!!!"  # noqa E501
                        )
                        continue
                    removed_code_start_string = (
                        "/************REMOVED USER CODE AREA STARTS!*********THIS COMMENT WILL BE SAVED!***********/"
                    )
                    removed_code_end_string = (
                        "/*************REMOVED USER CODE AREA ENDS!**********THIS COMMENT WILL BE SAVED!***********/"
                    )
                    comments_list = [
                        user_code_start_string,
                        user_code_end_string,
                        removed_code_start_string,
                        removed_code_end_string,
                    ]
                    if not all(comment in text for comment in comments_list):
                        logger.warning(f"The comments in {file} does not meet requirements!!!")
                        continue

                    # 主功能代码区
                    user_code_dict[swc_name] = {}
                    mem_comm = cls.get_all_memmap_comments(text)
                    for key in cls.mem_key_list:
                        user_code_dict[swc_name][key] = mem_comm[key]
                    user_code_dict[swc_name]["head_usercode"] = []
                    user_code_dict[swc_name]["tail_usercode"] = []
                    user_code_dict[swc_name]["unmatched_runnable"] = []
                    func_stack = []  # 初始化函数名栈
                    func_index_stack = []  # 初始化函数名位置索引栈
                    index_bracket = 0
                    index_head = 0
                    index_tail = 0
                    file_lines = text.split("\n")  # 按行读取
                    for index_line, line in enumerate(file_lines):
                        func_name = cls.extract_function_names(line)
                        if func_name:
                            func_stack.append(func_name)  # 把当前函数入栈
                            func_index_stack.append(index_line)
                        if "{" in line and 'extern "C"' not in line:
                            index_bracket += line.count("{")
                        if "}" in line:
                            index_bracket -= line.count("}")
                        if removed_code_start_string in line:
                            continue
                        if "* Runnable entity prototypes" in line or f"#define {swc_name}_STOP_SEC_CODE" in line:
                            # The previous one is for compatibility with older versions
                            index_tail += 1
                        if user_code_start_string in line:
                            if index_bracket == 0 and index_head == 0:
                                for index in range(index_line + 1, len(file_lines)):
                                    if user_code_end_string not in file_lines[index]:
                                        user_code_dict[swc_name]["head_usercode"].append(file_lines[index])
                                    else:
                                        index_head += 1
                                        break
                            elif index_bracket == 0 and index_tail > 0:
                                for index in range(index_line + 1, len(file_lines)):
                                    if user_code_end_string not in file_lines[index]:
                                        user_code_dict[swc_name]["tail_usercode"].append(file_lines[index])
                                    else:
                                        break
                            else:
                                if index_bracket != 0:
                                    func_name = func_stack[-1] if func_stack else None
                                    if func_name in swc_runnable[swc_name]:
                                        user_code_dict[swc_name].update({func_name: []})
                                        for index in range(index_line + 1, len(file_lines)):
                                            if user_code_end_string not in file_lines[index]:
                                                user_code_dict[swc_name][func_name].append(file_lines[index])
                                            else:
                                                break
                                    else:
                                        index_bracket_unmatched_runnable = 0
                                        for index in range(func_index_stack[-1], len(file_lines)):
                                            if "{" in file_lines[index]:
                                                index_bracket_unmatched_runnable += 1
                                            if "}" in file_lines[index]:
                                                index_bracket_unmatched_runnable -= 1
                                            if index == func_index_stack[-1] or index_bracket_unmatched_runnable != 0:
                                                user_code_dict[swc_name]["unmatched_runnable"].append(file_lines[index])
                                            else:
                                                user_code_dict[swc_name]["unmatched_runnable"].append(file_lines[index])
                                                break
        return user_code_dict

    @classmethod
    def get_all_memmap_comments(cls, text):
        mem_comm = {key: [] for key in cls.mem_key_list}
        for key in cls.mem_key_list:
            match = re.search(cls.mem_patterns[key], text, re.DOTALL)
            if not match:
                continue
            match_inner = re.search(cls.user_code_pattern, match.group(match.lastindex), re.DOTALL)
            if not match_inner:
                continue
            mem_comm[key].extend(match_inner.group(match_inner.lastindex).split("\n"))
        return mem_comm

    @classmethod
    def bsw_callout_user_code(cls, folder_path):
        bsw_user_code_dict = {}
        bsw_file_list = (
            "sysm_init_user_callout",
            "hook_user_callout",
            "isolate_user_callout",
            "wdgm_status_callout",
            "nvm_user_callout",
            "det_user_callout",
            "csm_user_callout",
            "ethif_eth_callout",
        )
        for root, dirs, files in os.walk(folder_path):
            if files == []:
                return bsw_user_code_dict
            for file in files:
                if not file.endswith(".c"):
                    continue
                if file.endswith(".c") and file.rstrip(".c") in bsw_file_list:
                    swc_name = file.replace(".c", "")
                    bsw_user_code_dict[swc_name] = {}
                    bsw_user_code_dict[swc_name]["head_usercode"] = []
                    bsw_user_code_dict[swc_name]["tail_usercode"] = []
                    file_path = os.path.join(folder_path, file)  # 各个文件的路径
                    with open(file_path, encoding="utf-8") as f:
                        # 格式问题检测，有问题直接跳过主功能代码
                        text = f.read()  # 整个文件读成一个字符串
                        left_bracket_count = text.count("{")
                        right_bracket_count = text.count("}")
                        if left_bracket_count != right_bracket_count:
                            logger.warning(f"The number of left bracket and right bracket in {file} is not the same!!!")
                            continue
                        user_code_start_string = "/******************USER CODE STARTS!************THIS COMMENT WILL BE SAVED!***************/"  # noqa E501
                        user_code_end_string = "/******************USER CODE ENDS!**************THIS COMMENT WILL BE SAVED!***************/"  # noqa E501
                        uc_start_count = text.count(user_code_start_string)
                        uc_end_count = text.count(user_code_end_string)
                        if uc_start_count != uc_end_count:
                            logger.warning(
                                f"The number of user_code_start_string and user_code_end_string in {file} is not the same!!!"  # noqa E501
                            )
                            continue
                        comments_list = [user_code_start_string, user_code_end_string]
                        if not all(comment in text for comment in comments_list):
                            logger.warning(f"The comments in {file} does not meet requirements!!!")
                            continue

                        # 主功能代码区
                        bsw_user_code_dict[swc_name] = {}
                        bsw_user_code_dict[swc_name]["head_usercode"] = []
                        bsw_user_code_dict[swc_name]["tail_usercode"] = []
                        bsw_user_code_dict[swc_name]["unmatched_runnable"] = []
                        func_stack = []  # 初始化函数名栈
                        index_bracket = 0
                        index_head_tail = 0
                        file_lines = text.split("\n")  # 按行读取
                        for index_line, line in enumerate(file_lines):
                            func_name = cls.extract_function_names(line)
                            if func_name:
                                func_stack.append(func_name)  # 把当前函数入栈
                            if "{" in line and 'extern "C"' not in line:
                                index_bracket += line.count("{")
                            if "}" in line:
                                index_bracket -= line.count("}")
                            if user_code_start_string in line:
                                if index_bracket == 0 and index_head_tail == 0:
                                    for index in range(index_line + 1, len(file_lines)):
                                        if user_code_end_string not in file_lines[index]:
                                            bsw_user_code_dict[swc_name]["head_usercode"].append(file_lines[index])
                                        else:
                                            break
                                    index_head_tail += 1
                                elif index_bracket == 0 and index_head_tail == 1:
                                    for index in range(index_line + 1, len(file_lines)):
                                        if user_code_end_string not in file_lines[index]:
                                            bsw_user_code_dict[swc_name]["tail_usercode"].append(file_lines[index])
                                        else:
                                            break
                                else:
                                    if index_bracket != 0:
                                        func_name = func_stack[-1] if func_stack else None
                                        bsw_user_code_dict[swc_name].update({func_name: []})
                                        for index in range(index_line + 1, len(file_lines)):
                                            if user_code_end_string not in file_lines[index]:
                                                bsw_user_code_dict[swc_name][func_name].append(file_lines[index])
                                            else:
                                                break
        return bsw_user_code_dict

    @classmethod
    def extract_function_names(cls, line):
        key_list = ["if"]  # else if会被误认为函数，去除
        # 正则表达式匹配可能的函数名
        func_name_pattern = re.compile(r"\b(^(?!#).+)\b([\w,\(\)\s*]+[\s*])?\b(\w+)\s*\([^)]*\)\s*(?=\{?$)")
        comment_pattern = r"/\*.*?\*/"
        cleaned_string = re.sub(comment_pattern, "", line, flags=re.DOTALL).strip()
        match = func_name_pattern.search(cleaned_string)
        if match:
            return match.group(3) if match.group(3).lower() not in key_list else None
        return None

    @classmethod
    def parse_swc_runnable(cls, asw_autosar_merged, swc_app_list):
        # 解析arxml中的swc及对应的runnable信息，用于user_code保存
        swc_runnable_dict = {}
        sw_component_types = []
        if asw_autosar_merged != {}:
            for swc_type in AutosarUtils.SUPPORT_COMPONENT_TYPE:
                sw_component_types += asw_autosar_merged.find_nodes(swc_type)
            for sw_component_type in sw_component_types:
                swc_name = sw_component_type.SHORT_NAME.valueOf_
                if swc_name not in swc_app_list:
                    continue
                if sw_component_type.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR:
                    sw_ib = sw_component_type.INTERNAL_BEHAVIORS.SWC_INTERNAL_BEHAVIOR[0]
                else:
                    sw_ib = None
                runnable_names = []
                if not sw_ib or not sw_ib.RUNNABLES:
                    continue
                for runnable_entity in sw_ib.RUNNABLES.RUNNABLE_ENTITY:
                    if runnable_entity.SYMBOL is None:
                        runnable_names.append(runnable_entity.SHORT_NAME.valueOf_)
                    else:
                        runnable_names.append(runnable_entity.SYMBOL.valueOf_)
                swc_runnable_dict[swc_name] = runnable_names
        return swc_runnable_dict

    @classmethod
    def get_user_code(cls, sys_info_dict, asw_autosar_dict, swc_app_list):
        user_code = {}
        # user_code["bsw_callout"] = {}
        swc_output_dir = sys_info_dict["path"]["swc_template_path"]
        if os.path.exists(swc_output_dir) is False:
            os.makedirs(swc_output_dir)
        if os.path.exists(swc_output_dir) is False:
            logger.error(f"{swc_output_dir} Not Exist!")
        if "asw" in asw_autosar_dict and asw_autosar_dict["asw"] is not None:
            swc_runnable = UserCodeExtract.parse_swc_runnable(asw_autosar_dict["asw"], swc_app_list)
            user_code = UserCodeExtract.user_code(swc_output_dir, swc_runnable, swc_app_list)
            # user_code["bsw_callout"] = UserCodeExtract.bsw_callout_user_code(bsw_callout_output_dir)
        return user_code
