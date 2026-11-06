# vcos_studio 代码仓库说明

## 1. 代码仓库简介

Configurator 是配套 VCOS 操作系统提供给汽车控制器软件开发工程师使用的一款组件配置工具，此工具提供 VCOS 的各组件模块、以及 Task Mapping、Data Mapping、Port Mapping、Service Mapping 等功能进行配置的 UI 界面，并根据用户配置生成 RTE 及各功能组件的动态代码，配合应用软件代码、功能组件代码及芯片驱动代码、复杂驱动共同编译生成控制器软件镜像。同时 Configurator 还提供命令行接口以及 Python API 接口实现VCOS功能组件自动化配置以及软件自动化版本集成

## 2. 代码目录

vcos_studio 源代码在 haloosspace/vcos/vcos_studio 目录下，目录结构如下图所示：

```plaintext
vcos_studio
└─ configurator                # 配置工具
    ├─ basic_func_module       # 基础功能模块，主要包括功能模块所使用的公用接口，如文件处理、autosar arxml解析编辑接口、日志接口等
    ├─ cfg_gui                 # 前台 GUI 界面的用户操作交互功能代码，包括 BSW 编辑、Rte 配置、导入导出、工程管理、二级菜单、搜索跳转、代码生成及校验等UI功能
    │  ├─ bsw_editor           # BSW 模块配置界面
    │  ├─ generator            # 代码生成界面
    │  ├─ rte_editor           # Rte二级菜单，包含Task Mapping，Data Mapping，Port Mapping和Service Mapping
    │  ├─ secondary_menu       # 二级菜单界面
    │  ├─ validation           # 校验界面
    │  └─ ...
    ├─ ui_adaptor              # 前台 GUI 适配层，对上提供接口供 GUI 用户交互模块调用，对下调用功能模块层的具体模块业务功能，并管理 GUI 交互数据
    ├─ cmd_api                 # 配置工具提供的 API 及命令行接口，包括供参考使用的演示代码
    │  ├─ api_demo             # 对外 API 使用演示
    │  ├─ cmd_demo             # 命令行接口演示
    │  ├─ auto_cli.py          # 命令行接口
    │  └─ auto_cli_api.py      # 对外API接口
    ├─ cmd_adaptor             # 前台命令行适配层，对上提供 API 及命令行接口，对下调用功能模块层的具体业务功能，管理交互数据
    ├─ func_module             # 功能模块层，对前台命令行模块及 UI 界面提供具体功能实现，包括文件导入、导出、代码生成、配置校验、模块管理、mapping、工程管理等
    │  ├─ import_file          # 导入文件模块
    │  ├─ export_file          # 导出文件模块
    │  ├─ validation           # 校验模块
    │  ├─ generator            # 代码生成模块
    │  ├─ mapping              # mapping 模块
    │  ├─ health_monitor       # 健康监控模块
    │  ├─ module_management    # 模块管理模块
    │  └─ project_management   # 工程管理模块
    ├─ third_party             # 依赖的第三方库
    ├─ configurator.bat        # Windows 环境下 configurator 工具启动脚本（启动时会显示控制台窗口）
    ├─ configurator.ps1        # Windows 环境下 configurator 工具启动脚本（无控制台版本）
    ├─ configurator.sh         # Linux 环境下 configurator 工具启动脚本
    ├─ init_env.py             # configurator 工具环境配置脚本
    └─ ...
```

## 3. 仓库使用入门

### 3.1. 环境配置

- 安装 Python3.8

  [安装教程](https://gitee.com/haloos/vcos/blob/master/quick_start/01_downloading.md)

- Windows 系统设置虚拟运行环境

  ```powershell
  python ./vcos_studio/configurator/init_env.py -a
  .venv/Scripts/Activate.ps1
  ```

- Linux 系统设置虚拟运行环境

  ```bash
  sudo apt update
  sudo apt install python3.8-venv libxcb-cursor0
  python ./vcos_studio/configurator/init_env.py -a
  chmod +x .venv/bin/activate
  source .venv/bin/activate
  ```

> 注意：如果下载遇到卡住不动的情况，可以考虑配置当地的pip镜像源

### 3.2. 启动工具

- Windows

  ```powershell
  vcos_studio/configurator/configurator.bat # 启动时会显示控制台窗口
  vcos_studio/configurator/configurator.ps1 # 启动时无控制台窗口，需要右键使用 PowerShell 运行
  ```

- Linux

  ```bash
  vcos_studio/configurator/configurator.sh
  ```

### 3.3. 使用工具

[工具使用手册](https://gitee.com/haloos/vcos/blob/master/user_manual/studio/configurator_tool_user_manual.md)
