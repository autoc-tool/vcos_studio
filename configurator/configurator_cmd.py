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
import shutil
import sys
import os
import argparse
import json


IS_FROZEN = getattr(sys, "frozen", False)
APP_DIR = os.path.dirname(sys.executable) if IS_FROZEN else os.path.dirname(os.path.abspath(__file__))
BUNDLE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
CFG_PLUG_IN_BASE = ["components", "configs", "configurator_plug_in"]
CURR_DIR = BUNDLE_DIR if IS_FROZEN else os.path.dirname(os.path.abspath(__file__))
CFG_PRJ = os.path.join(CURR_DIR, "cmd_api", "cmd_demo", "mini_project", "cfg_prj")
BSW_PATH = os.path.join(CFG_PRJ, "config", "bsw")
MINI_PRJ_PATH = os.path.join(CFG_PRJ, "mini_project.vcosproject")
LOG_PATH = os.path.join(APP_DIR, "configurator_cmd_{time:YYYY_MM_DD}.log")
CONFIGURATOR_PATH = CURR_DIR
CFG_PLUG_IN_PATH = os.path.abspath(
    os.path.join(CURR_DIR, *CFG_PLUG_IN_BASE) if IS_FROZEN else os.path.join(CURR_DIR, "..", "..", *CFG_PLUG_IN_BASE)
)


sys.path.insert(0, os.path.join(CURR_DIR, "third_party"))
sys.pycache_prefix = os.path.join(APP_DIR, "pycache")
os.makedirs(sys.pycache_prefix, exist_ok=True)

from cmd_adaptor.cmd_interaction.cmd_interaction import CmdInteraction
from cmd_adaptor.func_logic_layer.validation_func.validate_cmd_func import ValidateCmdFunc
from cmd_adaptor.cmd_interaction.cmd_logger import logger
from basic_func_module.base_logger import DEFAULT_FORMAT


VALIDATION_LOG_FORMAT = "[<level>{level}</level>] " "<level>{message}</level>"

CMD_ARGS = {
    "Validate": {
        "--module": {
            "type": str,
            "nargs": "+",
            "required": True,
            "help": "Specify the modules to be validated and their corresponding ARXML absolute paths, \n\
such as: --module Os d:/Os_ecuc.arxml Rte d:/Rte_ecuc.arxml.",
        },
        "--target": {
            "type": str,
            "required": True,
            "help": "Specify the target chip platform, \nsuch as --target=AURIX2G_TC397.",
        },
    },
    "Generate": {
        "--module": {
            "nargs": "+",
            "required": True,
            "help": "Specify the modules to be generated and their corresponding ARXML absolute paths, \n\
such as: --module Os d:/Os_ecuc.arxml Rte d:/Rte_ecuc.arxml.",
        },
        "--target": {
            "type": str,
            "required": True,
            "help": "Specify the target chip platform for the configuration, \nsuch as --target=AURIX2G_TC397.",
        },
        "--gen_dir": {
            "type": str,
            "required": True,
            "help": "Specify the absolute path to the folder where the code should be generated, \n\
such as: --gen_dir=d:/code_gen.",
        },
        "--compiler": {
            "type": str,
            "required": True,
            "help": "Specify the compiler for the configuration, such as --compiler=gcc.",
        },
        "--debug": {
            "action": "store_const",
            "const": True,
            "default": False,
            "help": "Generate code for debugging using --debug.",
        },
        "--force": {
            "action": "store_const",
            "const": True,
            "default": False,
            "help": "Disable incremental generation using --force.",
        },
    },
}


class ConfiguratorCmd:

    def __init__(self):
        self.log_handle_ids = []
        self.setup_logger()
        self.args = self.parse_input_args()

    @staticmethod
    def parse_input_args():
        """
        Parse the commands entered at the user terminal.
        """
        logger.info("Parsing terminal commands entered by user.")
        arg_parser = argparse.ArgumentParser()
        subparsers = arg_parser.add_subparsers(
            title="sub-commands", dest="subcommand", description="valid subcommands", help="additional help"
        )
        for cmd_name, cmd_arg_dict in CMD_ARGS.items():
            sub_parser = subparsers.add_parser(cmd_name)
            for arg_name, arg_params in cmd_arg_dict.items():
                sub_parser.add_argument(arg_name, **arg_params)

        args = arg_parser.parse_args()
        logger.info("Parsing the terminal command entered by the user is completed.")

        if not args.subcommand:
            arg_parser.print_help()

        return args

    def execute_command(self):
        """Execute commands from the user terminal.
        Args:
            args (Namespace): Commands parsed from the terminal input.
        """
        if not self.args.subcommand:
            return

        if not self.replace_config_data():
            return

        if not self._check_module_dependency():
            return

        cmd_interaction = CmdInteraction(self.args, sys.argv)

        if self.args.subcommand == "Validate":
            result = cmd_interaction.execute_validation_command(MINI_PRJ_PATH, self.args.module)
            if failed_logs := ValidateCmdFunc.validation_instance.filter_pass_logs():
                self.format_validation_logs(failed_logs)
        elif self.args.subcommand == "Generate":
            result = cmd_interaction.execute_generate_command(
                MINI_PRJ_PATH, self.args.module, self.args.debug, self.args.force
            )
            if result is False and (failed_logs := ValidateCmdFunc.validation_instance.filter_pass_logs()):
                self.format_validation_logs(failed_logs)
            else:
                logger.info(f"All codes have been generated into path {self.args.gen_dir}")
        else:
            logger.warning("No valid subcommand was entered, please check the command entered in the terminal.")

        logger.info("Command execution completed.")

    def replace_config_data(self):
        """
        Replace the ARXML, platform, version information, and other configuration settings.
        """
        try:
            if ret := self._replace_bsw_arxml_config():
                logger.info("Replace bsw arxml successfully.")
            else:
                logger.error("Replace bsw arxml failed.")
                return ret

            if ret := self._replace_project_config():
                logger.info("Replace project config successfully.")
            else:
                logger.error("Replace project config failed.")
                return ret
        except Exception as e:
            import traceback

            logger.error(f"Replace config data failed: {e}, {traceback.format_exc()}")
            return False

        return True

    def _replace_project_config(self):
        """
        Replace the project file configurations, such as target, mcal path, system version, studio version
        return: bool
        """
        with open(MINI_PRJ_PATH, "r", encoding="utf-8") as f:
            prj_cfg = json.load(f)
            if not os.path.exists(CFG_PLUG_IN_PATH):
                logger.error(f"system path <{CFG_PLUG_IN_PATH}> not existed.")
                return False

            prj_cfg["path"]["studio_path"] = os.path.relpath(CONFIGURATOR_PATH, CFG_PRJ).replace("\\", "/")
            prj_cfg["path"]["system_path"] = os.path.relpath(CFG_PLUG_IN_PATH, CFG_PRJ).replace("\\", "/")

            # 替换 configurator 和 system 的版本信息
            system_ver, configurator_ver = "V0.1.0-DEV", "V0.1.0-DEV"
            sys_compat_path = os.path.join(CFG_PLUG_IN_PATH, "compatibility.json")
            if not os.path.exists(sys_compat_path):
                logger.error("system compatibility.json not found, please check.")
                return False

            with open(sys_compat_path, "r") as f_stream:
                sys_compat_path = json.loads(f_stream.read())
                system_ver = sys_compat_path["components"]["version"]

            cfg_compat_path = os.path.join(
                CONFIGURATOR_PATH, "func_module", "project_management", "version_management", "compatibility.json"
            )
            if not os.path.exists(cfg_compat_path):
                logger.error("configurator compatibility.json not found, please check.")
                return False

            with open(cfg_compat_path, "r") as f_stream:
                cfg_compat_cfg = json.loads(f_stream.read())
                configurator_ver = cfg_compat_cfg["components"]["Studio"]["version"]

            prj_cfg["system_version"] = system_ver
            prj_cfg["version"] = configurator_ver

            if hasattr(self.args, "gen_dir"):
                gen_dir_abs = os.path.abspath(self.args.gen_dir)
                os.makedirs(gen_dir_abs, exist_ok=True)
                prj_cfg["gendata_path"] = gen_dir_abs

            # 添加未使能的模块
            curr_enable_module = prj_cfg["modules_info"]["enabled_module_list"]
            prj_cfg["modules_info"]["enabled_module_list"] = [
                *curr_enable_module,
                *[module_name for module_name in self.args.module if module_name not in curr_enable_module],
            ]

            # 替换芯片平台信息
            components_plug_in_path = os.path.join(CFG_PLUG_IN_PATH, "components_plug_in_cfg.json")
            if not os.path.exists(components_plug_in_path):
                logger.error("components_plug_in_cfg.json not found, please check.")
                return False

            self.components_cfg = None

            with open(components_plug_in_path, "r") as f_stream:
                self.components_cfg = json.loads(f_stream.read())
                self.target = getattr(self.args, "target", "")
                if self.target not in self.components_cfg["target"]:
                    logger.error(f"{self.target} not in {list(self.components_cfg['target'].keys())}, please check.")
                    return False
                mcal_ver = self.components_cfg["target"][self.target]["MCAL_VERSION"][0]
                self.derive_group = self.components_cfg["target"][self.target]["DERIVATIVE_GROUP"]

                prj_cfg["MCAL_VERSION"] = mcal_ver
                prj_cfg["target"] = self.target

                # 替换编译器信息
                if hasattr(self.args, "compiler"):
                    compiler_list = self.components_cfg["target"][self.target]["compiler"]
                    if self.args.compiler not in compiler_list:
                        logger.error(f"{self.args.compiler} not in {compiler_list}, please check.")
                        return False
                    prj_cfg["compiler"] = self.args.compiler

            with open(MINI_PRJ_PATH, "w", encoding="utf-8") as f:
                json.dump(prj_cfg, f, indent=4)

        return True

    def _replace_bsw_arxml_config(self):
        """
        Replace the input module’s ARXML configuration.
        """
        if hasattr(self.args, "module"):
            if len(self.args.module) == 0 or len(self.args.module) % 2 != 0:
                logger.error("module config error, please check the command in terminal.")
                return False

            module_cfg = {}
            for i in range(0, len(self.args.module), 2):
                module_cfg[self.args.module[i]] = self.args.module[i + 1]
            self.args.module = list(module_cfg.keys())
        else:
            return False

        # 覆盖用户指定的 arxml
        for module_name, src_arxml_path in module_cfg.items():
            if os.path.exists(src_arxml_path):
                dest_path = os.path.abspath(f"{BSW_PATH}/{module_name}/{module_name}_ecuc.arxml")
                dst_dir = os.path.dirname(dest_path)

                if not os.path.exists(dst_dir):
                    os.makedirs(dst_dir, exist_ok=True)

                shutil.copy2(src_arxml_path, dest_path)
            else:
                print(f"{src_arxml_path} not exist.")
                return False

        return True

    def _check_module_dependency(self):
        """
        Verify that the dependencies among the input modules meet the requirements.
        """

        def __get_dependency(curr_module: str, all_module: list, plat_cfg: dict, component_cfg: dict):
            # 获取所有依赖的模块
            dependency_list = plat_cfg["module_cfg"].get(curr_module, {}).get("dependency_list", [])

            if not dependency_list:
                dependency_list = component_cfg["module_cfg"].get(curr_module, {}).get("dependency_list", [])

            for module_name in dependency_list:
                if module_name not in all_module:
                    all_module.append(module_name)

        plat_cfg_path = os.path.join(
            CFG_PLUG_IN_PATH, "platform_cfg", self.derive_group, self.target, "platform_cfg.json"
        )
        if not os.path.exists(plat_cfg_path):
            logger.error(f"platform_cfg.json <{plat_cfg_path}> not found.")
            return False

        plat_cfg = None
        with open(plat_cfg_path, "r") as f_stream:
            plat_cfg = json.loads(f_stream.read())

        all_module_list = [*self.args.module]

        # 获取所有依赖的模块
        for module_name in all_module_list:
            __get_dependency(module_name, all_module_list, plat_cfg, self.components_cfg)

        left_modules = [module_name for module_name in all_module_list if module_name not in self.args.module]
        if left_modules:
            logger.error(f"Module dependencies are not met, please add the following module arxml: {left_modules}")
            return False
        else:
            return True

    def format_validation_logs(self, validation_logs):
        """
        Format and output the validation logs.
        """
        self.setup_logger(True)
        logger_level = {"0": logger.error, "1": logger.warning, "2": logger.info, "3": logger.debug}
        logger.info(f"{'-' * 60} validation logs {'-' * 60}")

        for module_info in validation_logs.values():
            for mark, validtion_dict in module_info.get("logs", {}).items():
                summary = validtion_dict["summary"]
                for validtion_info in validtion_dict["info"]:
                    detail, path = validtion_info[0], " ".join(validtion_info[1])
                    format_str = f"{mark:<20} {summary:<20} \n {' ' * 27} {path:<20} \n {' ' * 27} {detail}"
                    logger_level[mark[-6]](format_str)

    def setup_logger(self, print_log=False):
        """
        Handle standard printing and validation log output.
        """
        if not self.log_handle_ids:
            std_err_id = logger.add_handler(sys.stderr, format=DEFAULT_FORMAT, colorize=True)
            file_id = logger.add_handler(LOG_PATH, format=DEFAULT_FORMAT, colorize=False)
            self.log_handle_ids = [std_err_id, file_id]

        if print_log:
            for handle_id in self.log_handle_ids:
                logger.remove(handle_id)
            logger.add_handler(sys.stderr, format=VALIDATION_LOG_FORMAT, colorize=True)
            logger.add_handler(LOG_PATH, format=VALIDATION_LOG_FORMAT, colorize=False)


if __name__ == "__main__":
    cmd = ConfiguratorCmd()
    cmd.execute_command()
