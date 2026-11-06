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
import sys
import os
import argparse

CUR_FILE_PATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(CUR_FILE_PATH, ".."))
sys.path.append(os.path.join(CUR_FILE_PATH, "..", "third_party"))

if __name__ == "__main__":
    from cmd_adaptor.cmd_interaction.cmd_logger import logger
    from cmd_adaptor.cmd_interaction.cmd_interaction import CmdInteraction
    from func_module.health_monitor import perf_logger

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p", "--Project", required=True, type=str, default="FBCM_Sample", help="-P demo_project.vcosproject"
    )
    subparsers = parser.add_subparsers(
        title="sub-commands", dest="subcommand", description="valid subcommands", help="additional help"
    )
    parser_import = subparsers.add_parser("Import")
    parser_import.add_argument("--cdd", type=str, nargs="?", metavar="", default=None, help="cdd file path")
    parser_import.add_argument("--dbc_ldf", type=str, nargs="?", metavar="", default=None, help="dbc file path")
    parser_import.add_argument("--acn", action="store_true", default=False, help="if add channel name to signal")
    parser_import.add_argument("--node", type=str, nargs="?", metavar="", default=None, help="node file path")
    parser_import.add_argument("--asw", type=str, nargs="?", metavar="", default=None, help="asw file path")
    parser_import.add_argument("--mcal", type=str, nargs="?", metavar="", default=None, help="mcal file path")
    parser_import.add_argument(
        "--module", type=str, default=None, nargs="*", help="Need to import mcal module --module Can,Fee"
    )
    parser_mapping = subparsers.add_parser("AutoMapping")
    parser_mapping.add_argument(
        "-m",
        "--Mapping",
        type=str,
        default="TaskMapping",
        help="mapping type:AutoTaskMappingByFile/AutoPortMapping/AutoServiceMapping/AudtoDataMapping",
    )
    parser_mapping.add_argument("-f", "--File", type=str, default=None, help="mapping type:Excel")
    parser_mapping.add_argument("-t", "--TaskName", type=str, default=None, help="task name")
    parser_mapping.add_argument("-s", "--SwcName", type=str, default=None, help="swc name")
    parser_mapping.add_argument("-n", "--RunnableName", type=str, default=None, help="runnable name")
    parser_mapping.add_argument("-i", "--PositionInTask", type=int, default=-1, help="position in task")
    parser_mapping.add_argument("-e", "--EventName", type=str, default="", help="runnbale bind event name")

    # ################## port/service/data mapping using command ###################
    parser_mapping.add_argument("-c", "--component", type=str, default=None, help="Component prototype name")
    parser_mapping.add_argument("-d", "--direction", type=str, default=None, help="Tx/Rx")
    parser_mapping.add_argument(
        "-pr", "--prefix", type=str, default=None, help="Port prototype前缀字符串。可为空，代表无前缀"
    )
    parser_mapping.add_argument(
        "-po", "--postfix", type=str, default=None, help="Port prototype后缀字符串。可为空，代表无后缀"
    )
    parser_mapping.add_argument(
        "-sp",
        "--allow_split",
        action="store_true",
        default=False,
        help="allow split 允许1:N连接。为空，代表不允许1:N连接；不为空，代表允许1:N连接",
    )
    parser_mapping.add_argument(
        "-me",
        "--allow_merge",
        action="store_true",
        default=False,
        help="allow merge 允许N:1连接。为空，代表不允许N:1；不为空，代表允许N:1",
    )
    parser_mapping.add_argument(
        "-ms",
        "--allow_multi_signal",
        action="store_true",
        default=False,
        help="allow multi-signal 允许1个Port自动连接多个Signal。为空，代表不允许；不为空，代表允许",
    )
    parser_mapping.add_argument(
        "-ic",
        "--ignore_match_case",
        action="store_true",
        default=False,
        help="Ignore Match case忽略大小写匹配。为空，代表大小写匹配；不为空，代表不大小写匹配",
    )
    parser_mapping.add_argument(
        "-iw",
        "--ignore_match_whole_word",
        action="store_true",
        default=False,
        help="Ignore match whole word忽略全词匹配。为空，代表全词匹配；不为空，代表不全词匹配",
    )
    parser_mapping.add_argument(
        "-lg",
        "--log_save",
        action="store_true",
        default=False,
        help="log save 保存log。为空，代表不保存；不为空，代表保存",
    )
    parser_mapping.add_argument(
        "-compat",
        "--match_compatibility",
        action="store_true",
        default=False,
        help="Match compatibility 数据类型长度兼容自动连接。为空，代表不自动连接；不为空，代表兼容类型自动连接",
    )
    parser_mapping.add_argument("--cmd", type=str, default=None, help="Port prototype后缀字符串。可为空，代表无后缀")

    parser_validate = subparsers.add_parser("Validate")
    parser_validate.add_argument(
        "--module", type=str, default=str, nargs="*", help="Port prototype后缀字符串。可为空，代表无后缀"
    )

    parser_generate = subparsers.add_parser("Generate")
    parser_generate.add_argument(
        "--module", type=str, default=None, nargs="*", help="Generate module code: --module Os,Rte"
    )
    parser_generate.add_argument(
        "--debug", action="store_const", const=True, default=False, help="Generate code for debugging"
    )
    parser_generate.add_argument(
        "--force", action="store_const", const=True, default=False, help="No incremental generation"
    )
    parser_generate.add_argument(
        "--sim", action="store_const", const=True, default=False, help="Simulator Mode"
    )
    parser_swc_generate = subparsers.add_parser("Swc_Generate")
    parser_swc_generate.add_argument(
        "--swcs", type=str, default=None, nargs="*", help="Generate swc template: --module CanInput, CanOutput"
    )

    parser_upgrade = subparsers.add_parser("Upgrade")
    args = parser.parse_args()

    studio_path = os.path.join(CUR_FILE_PATH, "..")
    logger.init_default_handler(log_path=studio_path)
    perf_logger.init_perf_handler(studio_path, "cmd_perf_record.log")

    cmd_interaction = CmdInteraction(args, sys.argv)

    if args.subcommand == "Import":
        result = cmd_interaction.execute_auto_import_command(args)
    elif args.subcommand == "AutoMapping":
        result = cmd_interaction.execute_auto_mapping_command(args)
    elif args.subcommand == "Validate":
        result = cmd_interaction.execute_validation_command(args.Project, args.module)
    elif args.subcommand == "Generate":
        result = cmd_interaction.execute_generate_command(args.Project, args.module, args.debug, args.force, args.sim)
    elif args.subcommand == "Swc_Generate":
        result = cmd_interaction.execute_swc_generate_command(args.Project, args.swcs)
    elif args.subcommand == "Upgrade":
        result = cmd_interaction.execute_upgrade_command(args.Project)

    if result is True:
        logger.info("AutoCli successfully")
    else:
        logger.error("AutoCli failed")

    if not result:
        sys.exit(-1)
