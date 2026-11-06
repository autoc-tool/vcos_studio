# arxml生成说明  

## 1. 功能简介  

根据接口表所填的信息生成arxml文件。
功能描述与约束：  

- 支持SR接口。端口、接口、元素同名，不支持一个接口多个元素。支持一维数组，数组初始值需要相同。不支持隐式。不支持双向。
- 支持CS接口。不支持一个接口多个操作。参数方向不支持双向。
- 一个SWC只能包含一个runnable。只支持周期事件触发。默认会生成初始化runnable。  
- 支持基本的数据类型，支持自建的结构体数据类型，结构体不支持嵌套，都是单元素数据。

## 2. 文件目录介绍

> ``` text
> ArxmlFileGnrt
> ├── README.md                   # 仓库的readme，用于介绍该代码仓库(即本文)
> ├── auto_main.py                # arxml生成执行脚本
> ├── Modify                      # 二次修改脚本文件夹
> │   ├── component_writer.py     # ENABLE-UPDATE适配修改  
> │   ├── port.py                 # ENABLE-UPDATE适配修改
> │   ├── portinterface_writer.py # NV接口描述适配层
> │   └── copy_file.py            # 二次修改脚本的自动copy
> ├── ScriptLib                   # arxml生成子功能脚本文件夹
> │   ├── get_excel_info.py       # 获取接口表中的信息
> │   ├── creat_arxml_info.py     # 据获取的接口表信息生成arxml文件 
> │   └── create_arxml_utility.py # 辅助功能，log，dir
> └── IF_Path                     # 表格模板文件夹
> ```

## 3. 工具使用说明

### 3.1 外部工具依赖

- **GitHub项目名称**：autosar
- **GitHub链接**：<https://github.com/cogu/autosar/tree/v0.4.1>
- **版本**：v0.4.1
- **描述**：A set of python modules for working with AUTOSAR XML files
- **许可协议**：MIT License
- **安装**：在解压后文件目录输入 python setup.py install 安装即可
- 二次修改脚本文件替换  
  按照第三方autosar支持包后，把修改的三个文件替换到安装目录的对应位置；  
  /autosar/port.py  
  /autosar/writer/portinterface_writer.py  
  /autosar/writer/component_writer.py  
  [对于windows操作系统，也可以运行Modify文件夹下的copy_file.py进行自动覆盖]

### 3.2 使用说明

- 运行auto_main.py文件。选择接口表所在的目录，运行完成后，在接口表同目录下生成对应的arxml文件。

### 3.3 模板说明

a. 文件命名《IF_List_XXX.xlsx》。使用功能组名替换文件中的 XXX 。arxml中的runnable名字的来源。 周期：XXX_step 初始化：XXX_initialize  
b. 文件必须包含4个表单  
《Runnable》信息：  

|周期ms|
|------|
|10    |  

Event 触发周期，单位ms，数值是整数  

《Input》 P-Port接口信息：  

|SignalName|Min|Max|DataType|Unit|Description|Dimension|InitValue|nvData|enableUpdate|
|----------|---|---|--------|----|-----------|---------|---------|------|------------|  
|in1       |0  |1  |boolean |flg |r port1    |1        |0        |true  |true        |  
|in2       |0  |1  |boolean |flg |r port2    |1        |0        |true  |true        |

SignalName   ：信号接口名，名字在接口表中唯一。pp pi pe都使用该信号。必填。
Min          ：信号最小值。选填。
Max          ：信号最大值。选填。  
DataType     ：信号数据类型。必填。只能是基本数据类型：boolean、uint8、uint16、uint32、int8、int16、int32、sint8、sint16、sint32、single、float、float32、uint64  
或者是《AppDataTypeDef》 表单中自定义的结构体类型  
Unit         ：信号单位。选填。
Description  ：信号描述。选填。  
Dimension    ：信号维度。必填。  
InitValue    ：信号初始值。必填。  
nvData       ：信号NV标识。选填。只有为true时，才认为是nv接口。  
enableUpdate ：信号enableUpdate标识。选填。只有为true时，才认为有需求。  

《Output》 P-Port接口信息：  

|SignalName|Min|Max|DataType|Unit|Description|Dimension|InitValue|nvData|
|----------|---|---|--------|----|-----------|---------|---------|------|
|out1      |0  |1  |boolean |flg |p port1    |1        |0        |true  |  
|out2      |0  |1  |boolean |flg |p port2    |1        |0        |true  |  

SignalName   ：信号接口名，名字在接口表中唯一。pp pi pe都使用该信号。必填。
Min          ：信号最小值。选填。
Max          ：信号最大值。选填。  
DataType     ：信号数据类型。必填。只能是基本数据类型：boolean、uint8、uint16、uint32、int8、int16、int32、sint8、sint16、sint32、single、float、float32、uint64  
或者是《AppDataTypeDef》 表单中自定义的结构体类型  
Unit         ：信号单位。选填。
Description  ：信号描述。选填。  
Dimension    ：信号维度。必填。  
InitValue    ：信号初始值。必填。  
nvData       ：信号NV标识。选填。只有为true时，才认为是nv接口。  
  
《CS》 cs接口信息：  

|CorS      |PortName    |PortInerfaceName|Operation|Argument                  |函数返回          |isService|Description|
|----------|------------|----------------|---------|--------------------------|-----------------|---------|-----------|
|Client    |Pp_GetErrSts|Pi_GetErrSts    |GetErrSts|uint32 Id /\*IN\*/        |error E_NOT_OK  1|FALSE    |client     |
|          |            |                |         |uint8 ErrSts[32] /\*OUT\*/|                 |         |           |
|Server    |Pp_SetErrSts|Pi_SetErrSts    |SetErrSts|uint32 Id /\*IN\*/        |error E_NOT_OK  1|TRUE     |server     |
|          |            |                |         |uint8 ErrSts[32] /\*OUT\*/|                 |         |           |  
  
CorS             ：接口类型。必填。只能是Client Server
PortName         ：端口名称。必填。
PortInerfaceName ：接口名称。必填。
Operation        ：操作名称。必填。只支持一个 Operation Prototypes  
Argument         ：参数信息。必填。支持多Argument，之间换行，单个Argument中间空格，非数组格式：Data Type、Name、/*Direction*/，数组格式：Data Type、Name[Size]、/*Direction*/，
Data Type只支持基本数据类型，其他参数默认为：Calibration Access: NotAccessible、ImplPolicy:useArgumentType
函数返回          ：函数返回。必填。  Application Errors, Code:1、Error:E_NOT_OK
isService        ：service参数。必填。是否是 Service Ports，只能是true false  
Description      ：描述。选填。  

《AppDataTypeDef》 结构体类型定义：  

|AppDataType|StructName|MemberName   |MemberDataType  |
|-----------|----------|-------------|----------------|
|struct     |st_color1 |{red,blue}   |{single,boolean}|
|struct     |st_color2 |{white,black}|{boolean,uint8} |  

AppDataType      ：自定义数据类型。必填。目前只支持结构体，只能填写struct
StructName       ：结构体名称。必填。
MemberName       ：结构体成员名称。必填。 格式必须{,}。使用"{}"包括,使用","间隔  
MemberDataType   ：结构体成员类型。必填。 格式必须{,}。使用"{}"包括,使用","间隔。类型顺序需要和成员名称一致。
