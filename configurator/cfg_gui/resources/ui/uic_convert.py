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
UI转换工具: 将.ui文件转换为Python代码
"""

import os
import re
import sys
import glob
import time
import argparse
import subprocess
import concurrent.futures


def check_pyside6_uic():
    """检查pyside6-uic命令是否存在，并获取版本"""
    try:
        result = subprocess.run(
            ["pyside6-uic", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True
        )
        version_match = re.search(r"(\d+\.\d+\.\d+)", result.stdout or result.stderr or "")
        version = version_match.group(1) if version_match else "未知"
        return True, version
    except FileNotFoundError:
        return False, None


def convert_ui_file(ui_file_info):
    """转换单个UI文件为Python代码"""
    ui_file, output_dir, verbose, prefix = ui_file_info

    # 获取文件名（不带扩展名）
    filename = os.path.splitext(os.path.basename(ui_file))[0]

    # 确定输出文件路径
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{prefix}{filename}.py")
    else:
        output_path = os.path.join(os.path.dirname(ui_file), f"{prefix}{filename}.py")

    if verbose:
        print(f"正在转换: {ui_file} -> {output_path}")

    start_time = time.time()

    # 执行转换命令
    try:
        _ = subprocess.run(
            ["pyside6-uic", ui_file, "-o", output_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )
        elapsed = time.time() - start_time

        # 验证输出文件存在
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            if verbose:
                print(f"✅ 转换成功 ({elapsed:.2f}s): {output_path}")
            return True, None
        else:
            if verbose:
                print("❌ 转换失败: 输出文件为空或不存在")
            return False, "输出文件为空或不存在"

    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        error_msg = e.stderr.strip() if e.stderr else str(e)
        if verbose:
            print(f"❌ 转换失败 ({elapsed:.2f}s): {error_msg}")
        return False, error_msg


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="将UI文件转换为Python代码")
    parser.add_argument("-r", "--recursive", action="store_true", help="递归处理子目录")
    parser.add_argument("-o", "--output", type=str, help="指定输出目录")
    parser.add_argument("-i", "--input", type=str, default=".", help="指定输入目录（默认为当前目录）")
    parser.add_argument("-q", "--quiet", action="store_true", help="安静模式，减少输出")
    parser.add_argument("-p", "--prefix", type=str, default="ui_", help='输出文件的前缀（默认为"ui_"）')
    parser.add_argument(
        "-j", "--jobs", type=int, default=os.cpu_count(), help=f"并行转换的任务数（默认为CPU核心数: {os.cpu_count()}）"
    )
    parser.add_argument("--dry-run", action="store_true", help="仅列出要转换的文件，不执行实际转换")
    parser.add_argument("-f", "--filter", type=str, help="使用正则表达式过滤UI文件名")

    args = parser.parse_args()

    # 检查pyside6-uic是否安装
    uic_exists, uic_version = check_pyside6_uic()
    if not uic_exists:
        print("错误: 找不到pyside6-uic命令。请确保PySide6已正确安装。")
        print("可以尝试运行: pip install pyside6")
        sys.exit(1)

    if not args.quiet:
        print(f"使用 pyside6-uic 版本: {uic_version}")

    # 确保输入目录存在
    input_dir = args.input
    if not os.path.isdir(input_dir):
        print(f"错误: 输入目录 '{input_dir}' 不存在")
        sys.exit(1)

    # 如果指定了输出目录，确保它存在
    output_dir = args.output
    if output_dir and not args.dry_run:
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            print(f"错误: 无法创建输出目录 '{output_dir}': {e}")
            sys.exit(1)

    # 查找UI文件
    if args.recursive:
        if not args.quiet:
            print(f"递归搜索目录 '{input_dir}' 中的UI文件...")
        ui_files = glob.glob(os.path.join(input_dir, "**/*.ui"), recursive=True)
    else:
        if not args.quiet:
            print(f"搜索目录 '{input_dir}' 中的UI文件...")
        ui_files = glob.glob(os.path.join(input_dir, "*.ui"))

    # 应用过滤器（如果指定）
    if args.filter:
        try:
            regex = re.compile(args.filter)
            ui_files = [f for f in ui_files if regex.search(os.path.basename(f))]
        except re.error as e:
            print(f"错误: 无效的正则表达式 '{args.filter}': {e}")
            sys.exit(1)

    if not ui_files:
        print("没有找到UI文件")
        sys.exit(0)

    if not args.quiet:
        print(f"找到 {len(ui_files)} 个UI文件")
        if args.dry_run:
            print("仅列出文件（干运行模式）:")
            for ui_file in ui_files:
                filename = os.path.splitext(os.path.basename(ui_file))[0]
                if output_dir:
                    output_path = os.path.join(output_dir, f"{args.prefix}{filename}.py")
                else:
                    output_path = os.path.join(os.path.dirname(ui_file), f"{args.prefix}{filename}.py")
                print(f"  {ui_file} -> {output_path}")
            sys.exit(0)
        print("----------------------------")

    # 准备转换参数
    conversion_params = [(ui_file, output_dir, not args.quiet, args.prefix) for ui_file in ui_files]

    # 转换UI文件（并行或串行）
    start_time = time.time()
    results = []

    if args.jobs > 1 and len(ui_files) > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
            futures = [executor.submit(convert_ui_file, params) for params in conversion_params]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
    else:
        for params in conversion_params:
            results.append(convert_ui_file(params))

    # 统计结果
    success = sum(1 for r, _ in results if r)
    failed = sum(1 for r, _ in results if not r)

    elapsed = time.time() - start_time

    if not args.quiet:
        print("----------------------------")
        print(f"转换完成! 耗时 {elapsed:.2f} 秒")
        print(f"总共: {len(ui_files)} 个文件")
        print(f"成功: {success} 个文件")
        print(f"失败: {failed} 个文件")

        if failed > 0:
            print("\n失败的文件:")
            for i, (status, error) in enumerate(results):
                if not status:
                    print(f"  {conversion_params[i][0]} - 错误: {error}")

    # 如果有失败，返回非零退出码
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
