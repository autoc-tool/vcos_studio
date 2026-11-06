#!/usr/bin/env python3
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
import sys
import venv
import argparse
import platform
import subprocess
import pkg_resources

CUR_PATH = os.path.abspath(os.path.dirname(__file__))
VENV_PATH = os.path.abspath(os.path.join(CUR_PATH, "../../"))
REQ_PATH = os.path.abspath(os.path.join(CUR_PATH, "requirements.txt"))


def init_env():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--auto", action="store_true", default=False, help="Auto install packages")
    args = parser.parse_args()
    # 检查是否在虚拟环境中运行
    if os.environ.get("VIRTUAL_ENV") is None:
        print("非虚拟环境中运行: 创建虚拟环境并安装依赖...")
        venv_dir = os.path.join(VENV_PATH, ".venv")
        print(f"创建虚拟环境到: {venv_dir}")
        venv.create(venv_dir, clear=True, with_pip=True)
        return install_packages(venv_dir)

    elif args.auto:
        req_comparison = compare_requirements()
        missing_deps = req_comparison["missing_required"]
        if missing_deps and args.auto:
            venv_dir = os.environ.get("VIRTUAL_ENV")
            return install_packages(venv_dir)
        if missing_deps:
            print(f"\n警告: 发现 {len(missing_deps)} 个缺失的必要依赖: {', '.join(missing_deps)}")
        version_mismatches = [pkg for pkg, info in req_comparison["packages"].items() if info["status"] == "版本不符"]
        if version_mismatches:
            print(f"\n警告: 发现 {len(version_mismatches)} 个版本不匹配的包: {', '.join(version_mismatches)}")
        print("\n")


def install_packages(venv_dir):
    # 确定pip和python可执行文件的路径
    if sys.platform == "win32":
        pip_path = os.path.join(venv_dir, "Scripts", "pip.exe")
        python_path = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        pip_path = os.path.join(venv_dir, "bin", "pip")
        python_path = os.path.join(venv_dir, "bin", "python")
    # 检查requirements.txt文件是否存在
    req_file = REQ_PATH
    if os.path.exists(req_file):
        print(f"更新pip: {pip_path}")
        process = subprocess.Popen(
            [python_path, "-m", "pip", "install", "--upgrade", "pip"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in iter(process.stdout.readline, ""):
            print(line.strip())
        process.wait()
        print(f"安装依赖包: {req_file}")
        process = subprocess.Popen(
            [pip_path, "install", "-r", req_file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in iter(process.stdout.readline, ""):
            print(line.strip())
        process.wait()
        if process.returncode == 0:
            print("三方包安装成功")
        else:
            print(f"三方包安装失败，返回值：{process.returncode}")
        return process.returncode
    else:
        print(f"警告:三方包安装失败， {req_file} 文件未找到")
        return -1


def parse_requirements(filename):
    """解析requirements.txt文件，返回包名、版本要求和环境标记的字典"""
    requirements = {}
    if not os.path.exists(filename):
        return requirements

    with open(filename, "r") as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):
                # 处理行继续符号
                if line.endswith("\\"):
                    line = line[:-1].strip()

                # 忽略注释
                if "#" in line:
                    line = line.split("#")[0].strip()

                # 忽略选项（如-e, -r, -f等）
                if line.startswith("-"):
                    continue

                # 分离包规范和环境标记
                parts = line.split(";", 1)
                package_spec = parts[0].strip()
                env_marker = parts[1].strip() if len(parts) > 1 else None

                # 解析包名和版本规范
                match = re.match(r"^([a-zA-Z0-9_\-\.]+)(.*)$", package_spec)
                if match:
                    package = match.group(1).lower()
                    version_spec = match.group(2).strip()
                    requirements[package] = {"version_spec": version_spec, "env_marker": env_marker}

    return requirements


def get_installed_packages():
    """获取已安装的包和版本的字典"""
    installed = {}
    for package in pkg_resources.working_set:
        installed[package.key] = package.version
    return installed


def should_install_for_platform(env_marker):
    """检查给定环境标记是否适用于当前平台"""
    if not env_marker:
        return True

    # 创建一个简化的环境评估函数
    platform_vars = {
        "sys_platform": sys.platform,
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "os_name": os.name,
    }

    # 简单的环境标记解析（不完整，但足以处理常见情况）
    for var, value in platform_vars.items():
        if f"{var} == " in env_marker:
            expected_value = env_marker.split(f"{var} == ")[1].strip().strip("'\"")
            if expected_value != value:
                return False
        elif f"{var} != " in env_marker:
            expected_value = env_marker.split(f"{var} != ")[1].strip().strip("'\"")
            if expected_value == value:
                return False

    return True


def compare_requirements():
    """
    比较已安装的包与requirements.txt中的要求，考虑平台环境标记
    返回:
        字典包含比较结果:
        {
            'packages': {
                'package_name': {
                    'installed_version': '版本号或None如果未安装',
                    'required_version': '版本规范',
                    'env_marker': '环境标记或None',
                    'status': '状态（符合要求/版本不符/缺失/非必需）',
                    'is_for_this_platform': True/False
                },
                ...
            },
            'extra_packages': {
                'package_name': '版本号',
                ...
            },
            'missing_required': ['package_name1', 'package_name2', ...],
            'platform': 'current_platform_name'
        }
    """
    req_file = REQ_PATH
    result = {"packages": {}, "extra_packages": {}, "missing_required": [], "platform": sys.platform}

    if not os.path.exists(req_file):
        print(f"警告: {req_file} 文件未找到")
        return result

    required = parse_requirements(req_file)
    installed = get_installed_packages()

    print("\n=== 依赖对比 ===")
    print(f"{'包名':<20} {'已安装':<15} {'要求':<30} {'状态':<15}")
    print("-" * 80)

    for package, specs in required.items():
        version_spec = specs["version_spec"]
        env_marker = specs["env_marker"]

        # 检查此依赖是否适用于当前平台
        is_for_this_platform = should_install_for_platform(env_marker)
        env_info = f"{version_spec}; {env_marker}" if env_marker else version_spec

        package_info = {
            "required_version": version_spec,
            "env_marker": env_marker,
            "is_for_this_platform": is_for_this_platform,
        }

        if package in installed:
            installed_version = installed[package]
            package_info["installed_version"] = installed_version

            # 如果不是当前平台需要的包，标记为"非必需"
            if not is_for_this_platform:
                status = "非必需"
            # 尝试验证版本是否符合要求
            elif version_spec:
                try:
                    req = pkg_resources.Requirement.parse(f"{package}{version_spec}")
                    if installed_version in req:
                        status = "符合要求"
                    else:
                        status = "版本不符"
                except Exception:
                    status = "无法验证"
            else:
                status = "已安装"

            package_info["status"] = status

            print(f"{package:<20} {installed_version:<15} {env_info:<30} {status:<15}")
        else:
            package_info["installed_version"] = None

            if is_for_this_platform:
                status = "缺失"
                result["missing_required"].append(package)
            else:
                status = "非必需"

            package_info["status"] = status

            print(f"{package:<20} {'未安装':<15} {env_info:<30} {status:<15}")

        result["packages"][package] = package_info

    # 检查额外安装的包
    extra_packages = set(installed.keys()) - set(required.keys())
    if extra_packages:
        print("\n=== 额外安装的包 ===")

    for package in sorted(extra_packages):
        # 跳过一些标准库和setuptools相关包
        if package not in ("pip", "setuptools", "wheel", "pkg-resources"):
            result["extra_packages"][package] = installed[package]
            print(f"{package:<20} {installed[package]:<15}")
    return result


if __name__ == "__main__":
    sys.exit(init_env())
