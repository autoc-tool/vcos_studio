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
import time
import os
import argparse
import shutil
from multiprocessing import Process, Queue, freeze_support

CUR_FILE_PATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(CUR_FILE_PATH, "third_party"))

CLOSE_NUM_DEFAULT = 4

COREDUMP_LOG_PATH = os.path.join(CUR_FILE_PATH, "coredump.json")

CONFIGURATOR_DEAFULT_STATUS = {
    "status": "",
    "studio_version": "",
    "project_info": {"path": ""},
    "info": {"time": "", "data": ""},
}


def recursive_copy(source, destination):
    # Ensure the source directory exists
    try:
        if not os.path.exists(source):
            return

        # Walk through the source directory
        for dirpath, dirnames, filenames in os.walk(source):
            # Construct the corresponding destination path
            rel_path = os.path.relpath(dirpath, source)
            dest_dir = os.path.join(destination, rel_path)

            # If destination directories do not exist, create them
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)

            # Copy each file, overwriting if it already exists
            for filename in filenames:
                src_file = os.path.join(dirpath, filename)
                dest_file = os.path.join(dest_dir, filename)
                shutil.copy2(src_file, dest_file)  # copy2 to preserve metadata

    except Exception as e:
        raise e


class DeamonProcess:

    def __init__(self) -> None:
        self.deamon_status = {
            "name": "Configurator",
            "launch_num": 0,
            "queue": None,
            "status": "init",  # 1. running 2, ended 3，exception 4, init
            "subprocess_status": CONFIGURATOR_DEAFULT_STATUS.copy(),
            "process_id": None,
            "coredump_info": "",
        }

    def init(self, process_info):
        process_info["name"] = "Configurator"
        process_info["queue"] = None
        process_info["status"] = "init"  # 1. running 2, ended 3，exception 4, init
        process_info["subprocess_status"]["status"] = "init"
        process_info["process_id"] = None
        process_info["coredump_info"] = ""

    def configurator_monitor_process(self, launch_debug, project_path, type=False):
        while True:
            deamon_status = self.deamon_status
            if deamon_status["queue"] and deamon_status["queue"].qsize() > 0:
                status = deamon_status["queue"].get()
                deamon_status["subprocess_status"].update(status)

            # The child process is active
            if deamon_status["process_id"] and deamon_status["process_id"].is_alive():
                if deamon_status["subprocess_status"]["status"] == "close":
                    # Closing: configurator process is alive and status is close
                    deamon_status["status"] = "ended"
                    continue

                # Child process is active and exception
                if (
                    deamon_status["subprocess_status"]["status"] == "coredump"
                    and deamon_status["subprocess_status"]["info"] != deamon_status["coredump_info"]
                ):
                    deamon_status["subprocess_status"].update({"exitcode": deamon_status["process_id"].exitcode})
                    deamon_status["subprocess_status"].update({"name": deamon_status["process_id"].name})
                    deamon_status["subprocess_status"].update({"pid": deamon_status["process_id"].pid})
                    deamon_status["coredump_info"] = deamon_status["subprocess_status"]["info"]
                    self.exception_handle(deamon_status, "CRITICAL")
                    if type is True:
                        return
            else:
                # The child process has exited
                if deamon_status["status"] == "ended" or deamon_status["subprocess_status"]["status"] == "close":
                    # The child process has exited and closed normally
                    sys.exit(0)
                elif deamon_status["status"] == "init":
                    # The child process is in the initialization state
                    print(f"{deamon_status['name']} is running")
                    result = self.create_configrator_thread(deamon_status, launch_debug, project_path)
                    if result is False:
                        deamon_status["status"] = "exception"
                    else:
                        deamon_status["status"] = "running"
                else:
                    # The child process has exited and closed abnormally
                    self.exception_handle(deamon_status, "")
                    if type is True:
                        return
                    if deamon_status["launch_num"] >= CLOSE_NUM_DEFAULT:
                        deamon_status["status"] = "ended"
                    else:
                        self.init(deamon_status)
                        project_path = (
                            deamon_status.get("subprocess_status", "").get("project_info", "").get("path", "")
                        )
                        result = self.create_configrator_thread(deamon_status, launch_debug, project_path)
                        if result is False:
                            deamon_status["status"] = "exception"
                        else:
                            deamon_status["status"] = "running"
            if deamon_status["status"] in ["running", "ended"]:
                time.sleep(1)

    def create_configrator_thread(self, process_info, launch_debug, project_path):
        process_info["launch_num"] += 1
        process_info["queue"] = Queue()
        if process_info["queue"] is None:
            return False
        from ui_adaptor.launch_configurator import LaunchConfigurator

        launch_configurator = LaunchConfigurator(process_info["queue"])
        process_info["process_id"] = Process(
            target=launch_configurator.launch_configurator,
            args=(launch_debug, project_path, process_info["queue"], process_info),
            name="Configurator",
        )
        if process_info["process_id"] is None:
            return False
        process_info["process_id"].start()

        return True

    def exception_handle(self, process_info, type):
        # Abnormal scenarios: 1. Studio can catch the exception, 2. The studio process crashes directly
        # 1. Abnormal information is reported to the cloud
        # 2. Handle abnormal project
        if (
            process_info["subprocess_status"].get("studio_version", None)
            and "release" in process_info["subprocess_status"]["studio_version"].lower()
        ):
            self.coredump_project_handle(process_info["subprocess_status"], type, process_info["launch_num"])

    def coredump_project_handle(self, subprocess_status, type, launch_num):
        # 1. If the Studio does catch the exception or the Studio is in the initialization state
        if "CRITICAL" == type:
            return False
        try:
            # 2. Remove file locks
            vcos_studio_lock_path = os.path.join(
                os.path.dirname(subprocess_status["project_info"]["path"]), "vcos_studio.lock~"
            )
            if os.path.exists(vcos_studio_lock_path):
                os.remove(vcos_studio_lock_path)

            dst_config_bak = os.path.join(
                os.path.dirname(subprocess_status["project_info"]["path"]), "..", "Cfg_Prj_bak"
            )
            src_config = os.path.join(os.path.dirname(subprocess_status["project_info"]["path"]))
            tmp_dest_config = os.path.join(os.path.dirname(subprocess_status["project_info"]["path"]), "config")
            # 3. If the Studio restart times exceed the limit, it will exit directly
            if launch_num == CLOSE_NUM_DEFAULT:
                if os.path.exists(dst_config_bak):
                    recursive_copy(dst_config_bak, src_config)
                    shutil.rmtree(dst_config_bak)
                exit(0)

            message = (
                f'是否重新打开Studio并恢复工程?, 操作记录:\n{subprocess_status["info"]["stack_info"]}'
                if subprocess_status["info"].get("stack_info", None)
                else "是否重新打开Studio并恢复工程?"
            )
            print(f"""操作记录:\n{message} """)
            tmp_config_path = os.path.join(os.path.dirname(subprocess_status["project_info"]["path"]), ".config")
            if not os.path.exists(tmp_config_path):
                return True

            # 4. 1. Back up the Project to Cfg_Prj_bak.
            #    2. Copy the .config directory to the Project
            recursive_copy(src_config, dst_config_bak)
            recursive_copy(tmp_config_path, tmp_dest_config)
            shutil.rmtree(tmp_config_path)
            return True
        except Exception as e:
            raise e

    def get_user_name(self):
        username = os.environ.get("USERNAME")  # Windows
        if not username:
            username = os.environ.get("USER")  # Unix/Linux
        return username


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true", default=False, help="Start the debug function")
    parser.add_argument("-p", "--project_path", type=str, default="", help="Path of the project file")
    args = parser.parse_args()
    if args.debug:
        from ui_adaptor.launch_configurator import LaunchConfigurator

        launch_configurator = LaunchConfigurator()
        launch_configurator.launch_configurator(args.debug, args.project_path)
    else:
        deamon_process = DeamonProcess()
        deamon_process.configurator_monitor_process(args.debug, args.project_path)


if __name__ == "__main__":
    freeze_support()
    main()
