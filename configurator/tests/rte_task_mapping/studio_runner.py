# This Python file uses the following encoding: utf-8
"""Run Studio verify/save on a project in a fresh process and print a JSON summary as the last stdout line.

usage: studio_runner.py <project.vcosproject> <plain|refresh> <Module,Module,...> [save]

refresh: after load_project, replace every ECUC module in the live model with a plain re-parse of its ARXML,
i.e. without the EcucArxmlUpdater completion load_project applies. This is how a long-running client that
writes ECUC files itself and re-reads them into the Studio session sees the model.
"""
import json
import os
import sys
import traceback

CONFIGURATOR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, CONFIGURATOR_DIR)
sys.path.insert(0, os.path.join(CONFIGURATOR_DIR, "third_party"))
os.chdir(CONFIGURATOR_DIR)


def main():
    project, mode, modules = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
    do_save = len(sys.argv) > 4 and sys.argv[4] == "save"
    from cmd_api.auto_cli_api import AutoCliApi
    from cmd_adaptor.data_management import data_management as dm
    from func_module.module_management.arxml_handler.arxml_parse_save import ArxmlParseHandler

    summary = {"load": AutoCliApi.load_project(project), "verify": [], "crash": None, "save": None}
    if mode == "refresh":
        names = list(dm.autosar_bsw_class.keys())
        fresh = ArxmlParseHandler.parse_autosar_ecuc_arxml(dm.sys_info_class.config_base_path, names)
        for name in names:
            dm.autosar_bsw_class[name] = fresh[name]
    try:
        for _ in range(2):
            result, logs = AutoCliApi.excute_validation(modules, "error")
            errors = []
            for entry in logs.values():
                for code, rule in (entry.get("logs") or {}).items():
                    for info in rule.get("info", []):
                        if len(info) > 2 and info[2] != "pass":
                            errors.append({"code": code, "message": info[0], "paths": info[1], "solve": info[3:]})
            summary["verify"].append({"result": result, "errors": errors})
        if do_save:
            summary["save"] = AutoCliApi.save_project()
    except Exception as e:
        summary["crash"] = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
    print(json.dumps(summary, default=str))


if __name__ == "__main__":
    main()
