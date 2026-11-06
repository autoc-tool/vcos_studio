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

CUR_FILE_PATH = os.path.dirname(__file__)


class PathConverter_Adaptor:

    @classmethod
    def to_forward_slash(cls, path: str):
        return path.replace("\\", "/")

    @classmethod
    def to_rel(cls, path, base_path):
        """
        Convert to relative path
        """
        path = cls.to_forward_slash(path)
        base_path = cls.to_forward_slash(base_path)
        is_same_disk_dir: bool = cls.is_same_disk(path, base_path)  # 跨磁盘处理
        if os.path.isabs(path) and is_same_disk_dir:
            return cls.to_forward_slash(os.path.relpath(path, start=os.path.dirname(base_path)))
        else:
            return path

    @classmethod
    def is_same_disk(cls, path, base_path):
        """
        跨磁盘处理
        入参：目标路径+工程base路径
        """
        path_dir, _ = os.path.splitdrive(path)
        base_dir, _ = os.path.splitdrive(base_path)
        return path_dir == base_dir

    @classmethod
    def is_drive_existed(cls, path):
        """
        盘符检查：检查当前路径的盘符是否存在
        入参：文件或目录路径
        """
        ret = True
        temp_path = path
        drive = os.path.splitdrive(temp_path)[0]
        ret = False if not os.path.exists(drive) else True
        return ret, drive

    @classmethod
    def to_abs(cls, path, base_path):
        """
        Convert to absolute path
        """
        path = cls.to_forward_slash(path)
        base_path = cls.to_forward_slash(base_path)
        # abspath process
        if not os.path.isabs(path):
            path = os.path.abspath(os.path.join(os.path.dirname(base_path), path))
        else:
            path = os.path.abspath(path)
        return path
