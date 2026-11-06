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

import subprocess
import shutil
import os
from typing import List, Dict, Optional

def get_package_location(package_name) :
    """获取Python包的安装位置
    
    Args:
        package_name: 要查找的包名
        
    Returns:
        包的安装路径
        
    Raises:
        ValueError: 如果包未安装或查找失败
    """
    try:
        result = subprocess.run(
            ['pip', 'show', package_name],
            text=True,
            capture_output=True,
            check=True
        )
        
        if not result.stdout:
            raise ValueError(f"未找到包: {package_name}")
            
        for line in result.stdout.splitlines():
            if line.startswith('Location:'):
                return line.split('Location:')[1].strip()
                
        raise ValueError(f"无法从pip show结果中解析Location: {package_name}")
        
    except subprocess.CalledProcessError as e:
        raise ValueError(f"执行pip命令失败: {e.stderr}") from e

def copy_files(file_mapping):
    """复制文件到目标位置
    
    Args:
        file_mapping: 源文件路径到目标路径的映射
        
    Raises:
        FileNotFoundError: 如果源文件不存在
        OSError: 如果复制过程中出错
    """
    for src, dst in file_mapping.items():
        try:
            if not os.path.exists(src):
                raise FileNotFoundError(f"源文件不存在: {src}")
            shutil.copy2(src, dst)
            print(f"成功复制: {src} -> {dst}")   
        except (OSError, shutil.Error) as e:
            print(f"复制文件失败: {src} -> {dst}")
            raise

def main():
    try:
        # 配置要复制的文件
        package_name = "autosar"
        files_to_copy = {
            "port.py": os.path.join("autosar", "port.py"),
            "component_writer.py": os.path.join("autosar", "writer", "component_writer.py"),
            "portinterface_writer.py": os.path.join("autosar", "writer", "portinterface_writer.py")
        }
        
        # 获取包位置
        package_location = get_package_location(package_name)
        print(f"找到包位置: {package_location}")
        
        # 构建完整路径映射
        full_mapping = {
            src: os.path.join(package_location, dst)
            for src, dst in files_to_copy.items()
        }
        # 执行复制
        copy_files(full_mapping)
        
    except Exception as e:
        print(f"程序执行失败: {str(e)}")
        raise

if __name__ == "__main__":
    main()
