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
Resources转换工具: 将.qrc文件转换为Python代码
"""

import os
import re
import subprocess


def check_pyside6_uic():
    """检查pyside6-rcc命令是否存在，并获取版本"""
    try:
        result = subprocess.run(
            ["pyside6-rcc", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True
        )
        version_match = re.search(r"(\d+\.\d+\.\d+)", result.stdout or result.stderr or "")
        version = version_match.group(1) if version_match else "未知"
        return True, version
    except FileNotFoundError:
        return False, None


def convert_ui_file():
    """转换单个.qrc文件为Python代码"""
    check_pyside6_uic()
    # 获取文件名（不带扩展名）

    # 执行转换命令
    try:
        _ = subprocess.run(
            ["pyside6-rcc", "images.qrc", "-o", "images_rc.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )

        # 验证输出文件存在
        if os.path.exists("images_rc.py") and os.path.getsize("images_rc.py") > 0:
            print("✅ 转换成功: images_rc.py")
        else:
            print("❌ 转换失败: 输出文件为空或不存在")

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        print(f"❌ 转换失败 : {error_msg}")
        return False, error_msg


def main():
    convert_ui_file()


if __name__ == "__main__":
    main()
