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
from func_module.project_management.version_management.upgrade_common.common import VersionUpgradeCommon
import importlib
import os
from func_module.health_monitor.logger import logger
from basic_func_module.base_common.load_plug_in import LoadPlugIn
from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlParseHandler
from func_module.module_management.arxml_handler.ib_bswmd_process.ib_bswmd_process import IbBswmdProcess
from func_module.project_management.version_management.vcos_version import get_vcos_version_info
from func_module.generator import generator as vcos_gen
from func_module.health_monitor.perf_record import log_function_stats


class VersionUpgrate:

    def __init__(self, sys_info_class):
        self.sys_info_class = sys_info_class
        self.enabled_module_list = self.sys_info_class.enable_modules
        self.all_module_list = self.sys_info_class.all_modules
        self.current_version = None
        self.vcos_info = get_vcos_version_info()

    def is_upgrade_version(self, system_version, current_project_sys_version, plug_in_path):
        version = VersionUpgradeCommon()
        upgrade_project_system_version = ""
        upgrade_vcos_version = ""
        upgrade_list = {}
        vcos_version_for_comp = version.get_current_version(self.vcos_info.studio_version)
        project_vcos_version_for_comp = version.get_current_version(self.sys_info_class.version)
        self.system_version = version.get_current_version(system_version)
        self.current_project_version = version.get_current_version(current_project_sys_version)

        if None in (vcos_version_for_comp, project_vcos_version_for_comp):
            return upgrade_project_system_version, upgrade_vcos_version, upgrade_list

        if None in (self.system_version, self.current_project_version):
            return upgrade_project_system_version, upgrade_vcos_version, upgrade_list

        if version.compare_version(self.system_version, self.current_project_version, large_equal=False):
            upgrade_project_system_version = version.get_content_between_flags(system_version, "V", "-")

        if version.compare_version(vcos_version_for_comp, project_vcos_version_for_comp, large_equal=False):
            upgrade_vcos_version = version.get_content_between_flags(self.vcos_info.studio_version, "V", "-")

        upgrade_module_list = version.get_upgrade_module_list(self.enabled_module_list, plug_in_path)
        version_list = None
        for module in upgrade_module_list:
            version_list = version.get_module_version_list(
                module,
                self.system_version,
                vcos_version_for_comp,
                self.current_project_version,
                project_vcos_version_for_comp,
                plug_in_path,
            )
            if len(version_list) > 0:
                upgrade_list.update({module: version_list})
        return upgrade_project_system_version, upgrade_vcos_version, upgrade_list

    def upgrade_module_config(
        self, upgrade_list, bsw_ecuc_autosar_class, autosar_ib_class, mod_autosar_dict, sys_info_class
    ) -> bool:
        result = True
        for module, version_list in upgrade_list.items():
            if (
                module not in sys_info_class.enable_modules or module not in bsw_ecuc_autosar_class
            ) and module.lower() != "vcosproject":
                continue
            for version in version_list:
                try:
                    file_version = version.replace(".", "_")
                    if module.lower() in ["vcosproject", "rte"]:
                        upgrade_module_package = importlib.import_module(
                            f"func_module.project_management.version_management.{module.lower()}_upgrade."
                            f"{module.lower()}_upgrade_v{file_version}"
                        )
                        class_version = version.replace(".", "")
                        bsw_module_rule_class = getattr(upgrade_module_package, f"{module}UpgradeV{class_version}")
                        bsw_module_rule_obj = bsw_module_rule_class()
                        if module.lower() == "vcosproject":
                            result = bsw_module_rule_obj.upgrade_module(sys_info_class)
                        else:
                            result = bsw_module_rule_obj.upgrade_module(
                                bsw_ecuc_autosar_class, autosar_ib_class, mod_autosar_dict, sys_info_class
                            )

                    else:
                        class_version = version.replace(".", "")
                        upgrade_module_path = f"config_plug_in.version_upgrade.{module.lower()}_upgrade_v{file_version}"
                        upgrade_module_package = LoadPlugIn.load_module(module, upgrade_module_path)
                        bsw_module_rule_class = getattr(upgrade_module_package, f"{module}UpgradeV{class_version}")
                        bsw_module_rule_obj = bsw_module_rule_class()
                        result = bsw_module_rule_obj.upgrade_module(
                            bsw_ecuc_autosar_class, autosar_ib_class, mod_autosar_dict, sys_info_class
                        )

                    if result is False:
                        logger.warning(f"{module} upgrade failed.")
                        return False
                    else:
                        logger.info(f"{module} upgrade completed.")
                except Exception:
                    import traceback

                    traceback.print_exc()
                    logger.error(traceback.format_exc())
                    logger.error(f"{module} upgrade exception. Please check.")
                    assert traceback.format_exc()
                    return False
        return result

    def upgrade_project_config(self, sys_info_class):
        """update sys_cfg_info"""
        sys_info_class.version = self.vcos_info.studio_version
        # update path_cfg
        if hasattr(sys_info_class, "swc_template_path"):
            path_cfg = sys_info_class.swc_template_path
            if not path_cfg:
                path_config = (
                    sys_info_class.template_files_path if hasattr(sys_info_class, "template_files_path") else ""
                )
                if path_config:
                    sys_info_class.swc_template_path = path_config
                else:
                    sys_info_class.swc_template_path = os.path.abspath(
                        os.path.join(sys_info_class.application_path, "Apps", "Asw_Swc")
                    )

        if hasattr(sys_info_class, "bswcallout_path"):
            path_cfg = sys_info_class.bswcallout_path
            if not path_cfg:
                sys_info_class.bswcallout_path = os.path.abspath(
                    os.path.join(sys_info_class.application_path, "Apps", "BswUserCallout")
                )


class UpgradeCli:

    def __init__(self, vcos_version, system_version):
        self.vcos_version = vcos_version
        self.system_version = system_version
        self.version_module_list = {}
        self.version_upgrade = None
        pass

    def auto_cli_upgrade(self, sys_info_class, type=False) -> str:
        upgrade_info = ""
        self.version_upgrade = VersionUpgrate(sys_info_class)
        current_project_sys_version = sys_info_class.system_version
        if "Release " in current_project_sys_version:
            current_project_sys_version = current_project_sys_version.replace("Release ", "")
            current_project_sys_version = f"{current_project_sys_version}-DEV"
        upgrade_version, upgrade_vcos_version, self.version_module_list = self.version_upgrade.is_upgrade_version(
            self.system_version, current_project_sys_version, sys_info_class.plug_in_path
        )
        if not upgrade_version and not self.version_module_list and not upgrade_vcos_version:
            return None
        elif upgrade_version and not self.version_module_list:
            sys_info_class.system_version = self.system_version
            sys_info_class.version = self.vcos_version
            return None
        elif upgrade_version or upgrade_vcos_version:
            upgrade_info = f"Current system version:{upgrade_version}; Current studio version:{upgrade_vcos_version}\n"
        module_upgrade_info = ""
        for module, version in self.version_module_list.items():
            module_upgrade_info += f"{module}: {str(version)}\t\t\n"
        upgrade_info = (
            upgrade_info + f"Check that the current project needs to be upgraded as follows:\n {module_upgrade_info}"
        )

        return upgrade_info

    @log_function_stats(["VCOS工程管理", "工程升级"])
    def vcos_version_upgrade(self, data):
        bsw_ecuc_autosar_class = {}
        mod_autosar_dict = {}
        ib_autosar_class = {}
        sys_info_class = data.sys_info_class
        enabled_module_list = sys_info_class.enable_modules
        sys_info_class.version = self.vcos_version
        sys_info_class.system_version = self.system_version
        # 优化：避免重复加载耗时过长
        bsw_ecuc_autosar_class = data.autosar_bsw_class or ArxmlParseHandler.parse_autosar_ecuc_arxml(
            sys_info_class.config_base_path, enabled_module_list
        )
        mod_autosar_dict = data.autosar_bswmd_class or ArxmlParseHandler.parse_all_bswmd_arxml(
            sys_info_class.plug_in_bswmd_path, enabled_module_list, sys_info_class.target
        )
        result = self.version_upgrade.upgrade_module_config(
            self.version_module_list, bsw_ecuc_autosar_class, data.autosar_ib_class, mod_autosar_dict, sys_info_class
        )
        # ib_bswmd.arxml配置升级
        asw_autosar_class = data.autosar_asw_class or ArxmlParseHandler.parse_asw_arxml(sys_info_class.config_base_path)
        system_autosar_class = data.autosar_system_class or ArxmlParseHandler.parse_system_dir_arxml(
            sys_info_class.config_base_path
        )
        ib_autosar_class = data.autosar_ib_class or ArxmlParseHandler.parse_internal_behavior_arxml(
            sys_info_class.config_base_path, enabled_module_list, data.sys_target_dict
        )
        other_input_info = {
            "codegen_autosar_dict": vcos_gen.init_codegen_autosar_dict(data),
            "sys_info_class": data.sys_info_class,
            "sys_target_dict": data.sys_target_dict,
            "is_rte_parse_new_dict": True,
        }
        IbBswmdProcess.update_all_ib_bswmd(
            ib_autosar_class, bsw_ecuc_autosar_class, asw_autosar_class, system_autosar_class, other_input_info
        )
        return result, bsw_ecuc_autosar_class, mod_autosar_dict, ib_autosar_class


class VersionUpgradeProject:

    def __init__(self, cur_info_dict):
        self.cur_info_dict = cur_info_dict
        self.enabled_module_list = self.cur_info_dict["modules_info"]["enabled_module_list"]
        # self.all_module_list = self.cur_info_dict["modules_info"]["all_module_list"]
        self.current_version = cur_info_dict["version"]
        self.vcos_info = get_vcos_version_info()
        pass

    def is_upgrade_version(self, vcos_version, current_project_version, plug_in_path):
        version = VersionUpgradeCommon()
        upgrade_list = {}
        self.vcos_version = version.get_current_version(vcos_version)
        if self.vcos_version is None:
            return upgrade_list

        self.current_project_version = version.get_current_version(current_project_version)
        if self.current_project_version is None:
            return upgrade_list

        upgrade_module_list = version.get_upgrade_module_list(self.enabled_module_list, plug_in_path)
        version_list = None
        for module in upgrade_module_list:
            version_list = version.get_module_version_list(
                module, self.vcos_version, self.current_project_version, plug_in_path
            )
            if len(version_list) > 0:
                upgrade_list.update({module: version_list})
                logger.info(f"{module}: {version_list}")

        return upgrade_list

    @classmethod
    def upgrade_project_file(cls, update_version_list, sys_info_dict):
        result = True
        if not update_version_list:
            return result
        for version in update_version_list:
            try:
                upgrade_module_package = importlib.import_module(
                    f"func_module.project_management.version_management.vcosproject_upgrade."
                    f"vcosproject_upgrade_v{version}"
                )
                vcosproject_upgrade_class = getattr(upgrade_module_package, f"VCOSProjectUpgradeV{version}")
                vcosproject_upgrade_obj = vcosproject_upgrade_class()
                result = vcosproject_upgrade_obj.upgrade_module(sys_info_dict)
            except Exception:
                import traceback

                traceback.print_exc()
                logger.error(traceback.format_exc())
                assert traceback.format_exc()
                return False
        if result:
            sys_info_dict["version"] = cls.vcos_info.studio_version
        return result


class UpgradeCliProject:

    def __init__(self, vcos_version, cur_info_dict, plug_in_path):
        self.vcos_version = vcos_version
        self.version_module_list = {}
        self.version_upgrade = None
        self.cur_info_dict = cur_info_dict
        self.plug_in_path = plug_in_path
        pass

    def auto_cli_upgrade(self, type=False) -> str:
        self.version_upgrade = VersionUpgradeProject(self.cur_info_dict)
        current_project_version = self.cur_info_dict["version"]
        if "Release " in current_project_version:
            current_project_version = current_project_version.replace("Release ", "")
            current_project_version = f"{current_project_version}-DEV"
        self.version_module_list = self.version_upgrade.is_upgrade_version(
            self.vcos_version, current_project_version, self.plug_in_path
        )
        if not self.version_module_list:
            return None
        return self.version_module_list.get("VCOSProject", None)
