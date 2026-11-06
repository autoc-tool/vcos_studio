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
import json
import os
from datetime import datetime
from collections import deque
from func_module.health_monitor.logger import logger
from func_module.health_monitor.perf_record import log_function_stats

CUR_PATH = os.path.dirname(__file__)
JSON_FILE_PATH = os.path.abspath(os.path.join(CUR_PATH, "studio_cfg", "recent_files.json"))
MAX_RECENT = 5


class FileInfo:
    """用于封装文件相关信息的类"""

    def __init__(self, name, path, last_opened):
        self.name = name
        self.path = path
        self.last_opened = last_opened

    def get_file_name(self):
        """获取文件名"""
        return self.name

    def get_file_path(self):
        """获取文件路径"""
        return self.path

    def get_last_opened(self):
        """获取最后打开时间"""
        return self.last_opened

    def update_last_opened(self):
        self.last_opened = datetime.now().isoformat()


class RecentFilesManager:

    def __init__(self, filepath=JSON_FILE_PATH, max_recent=MAX_RECENT):
        self.filepath = filepath
        self.max_recent = max_recent

        # 检查文件是否存在，不存在则创建一个
        if not os.path.exists(self.filepath):
            self.create_empty_file()

        self.recent_files = deque(self.load_recent_files())

    def create_empty_file(self):
        # 提取目录路径
        directory = os.path.dirname(self.filepath)

        # 创建目录（如果不存在的话）
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory)
                # logger.error(f"目录创建成功: {directory}")
            except OSError as e:
                logger.error(f"错误：无法创建目录 - {directory}. 错误信息: {e}")
                return

        # 创建或写入 recent_files.json 文件
        try:
            with open(self.filepath, "w") as f:
                json.dump({"recentFiles": []}, f, indent=4)
                # logger.error(f"文件创建成功: {self.filepath}")
        except IOError as e:
            logger.error(f"错误：无法创建文件 - {self.filepath}. 错误信息: {e}")

    def load_recent_files(self):
        """加载最近打开的文件列表。"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                    return [
                        FileInfo(file_info["name"], file_info["path"], file_info["lastOpened"])
                        for file_info in data.get("recentFiles", [])
                    ]
            except (IOError, json.JSONDecodeError) as e:
                logger.error(f"错误：无法加载文件 - {self.filepath}. 错误信息: {e}")
                return []
        return []

    def save_recent_files(self):
        """保存最近打开的文件列表。"""
        try:
            file_info_list = [
                {
                    "name": file_info.get_file_name(),
                    "path": file_info.get_file_path(),
                    "lastOpened": file_info.get_last_opened(),
                }
                for file_info in self.recent_files
            ]
            with open(self.filepath, "w") as f:
                json.dump({"recentFiles": file_info_list}, f, indent=4)
        except IOError as e:
            logger.error(f"错误：无法保存文件 - {self.filepath}. 错误信息: {e}")

    @log_function_stats(["VCOS工程管理", "新增最近打开工程文件"])
    def add_recent_file(self, file_path):
        """添加最近打开的文件，将路径转换为绝对路径。"""
        if not os.path.exists(file_path):
            logger.error(f"错误：文件不存在 - {file_path}")
            return  # 停止执行

        absolute_path = os.path.abspath(file_path)
        file_info = None

        # 检查文件是否已经存在
        for info in self.recent_files:
            if info.path == absolute_path:
                file_info = info
                break

        if file_info:
            # 如果已存在，只更新打开时间
            file_info.update_last_opened()
            # 将已存在的文件移动到最近的位置
            self.recent_files.remove(file_info)  # 从当前的位置移除
            self.recent_files.appendleft(file_info)  # 重新插入到最前
        else:
            # 新增文件信息
            file_info = FileInfo(
                name=os.path.basename(absolute_path), path=absolute_path, last_opened=datetime.now().isoformat()
            )
            self.recent_files.appendleft(file_info)  # 添加到队列的左侧

        # 限制数量
        if len(self.recent_files) > self.max_recent:
            self.recent_files.pop()  # 移除最旧的文件

        # 保存
        self.save_recent_files()

    def get_recent_files(self):
        """获取最近打开的文件列表，移除不存在的文件并去重，保留时间最新的。"""
        latest_files = {}

        for file_info in list(self.recent_files):  # 使用列表防止在迭代过程中修改队列
            # 只保留存在的文件
            if os.path.exists(file_info.path):
                # 如果文件路径尚未记录，或当前文件信息时间更新，则更新
                if (
                    file_info.path not in latest_files
                    or file_info.get_last_opened() > latest_files[file_info.path].get_last_opened()
                ):
                    latest_files[file_info.path] = file_info

        # 更新队列为最新的 FileInfo 实例
        self.recent_files = deque(latest_files.values())
        return list(self.recent_files)

    def get_file_info(self, file_name):
        """根据文件名返回文件的完整信息。"""
        for file_info in self.recent_files:
            if file_info.get_file_name() == file_name:
                return file_info
        return None

    def clear_recent_files(self):
        """清空最近打开的文件列表。"""
        self.recent_files.clear()
        self.save_recent_files()


# 使用示例
if __name__ == "__main__":
    recent_files_manager = RecentFilesManager(filepath=JSON_FILE_PATH)

    mypath = "D:\\workspace\\vcos_repo_all\\Projects\\TC397_Demo\\Cfg_Prj\\TC397_Demo.vcosproject"
    recent_files_manager.add_recent_file(mypath)

    # 确认最近打开的文件
    recent_files = recent_files_manager.get_recent_files()
    for file in recent_files:
        print(f"{file.get_file_name()} - {file.get_file_path()} - {file.get_last_opened()}")

    # 获取某个文件的信息
    file_name = os.path.basename(mypath)
    file_info = recent_files_manager.get_file_info(file_name)
    if file_info:
        print("文件信息:", file_info.get_file_path(), file_info.get_last_opened())

    # 用户删除文件
    os.remove(mypath)  # 模拟用户删除文件

    # 重新获取最近打开的文件列表
    print("最近打开的文件:", recent_files_manager.get_recent_files())
