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

import openpyxl
import os
import re
import tkinter as tk
from tkinter import filedialog

class ReadXlsxInfo():
    """读取Excel接口信息的工具类"""
    def __init__(self):
        """初始化方法"""
        # 数据类型映射字典
        self.DATA_TYPE_MAPPING = {
            'boolean' :'boolean',
            'uint8'   :'uint8',
            'uint16'  :'uint16',
            'uint32'  :'uint32',
            'int8'    :'sint8',
            'int16'   :'sint16',
            'int32'   :'sint32',
            'sint8'   :'sint8',
            'sint16'  :'sint16',
            'sint32'  :'sint32',
            'single'  :'float32',
            'float'   :'float32',
            'sint32'  :'sint32',
            'float32'  :'float32',
            # 'float64' :'float64',
            'uint64': 'uint64'
        }
        # 必需的工作表
        self.REQUIRED_SHEETS = ['Runnable','AppDataTypeDef','Input','Output','CS']
        # 各工作表的必需列
        self.REQUIRED_COLUMNS = {
            'Runnable'  : ['周期ms'],
            'AppDataTypeDef' : ['AppDataType', 'StructName', 'MemberName', 'MemberDataType'],
            'Input' : ['SignalName', 'DataType', 'Dimension', 'InitValue','nvData','enableUpdate','Description'],
            'Output': ['SignalName', 'DataType', 'Dimension', 'InitValue','nvData','Description'],
            'CS'    : ['CorS', 'PortName', 'PortInerfaceName', 'Operation', 'Argument', '函数返回','isService','Description']  
        }
        self.INTERFACE_DIRECTION = {
            'Input' : 'receiver',
            'Output': 'sender',
            'CS'    : ['client','server']
        }
        self.swc_infos = {}
        self.only = []
        self._current_wb: Optional[openpyxl.Workbook] = None
    def find_xlsx_files(self,logger):
        """查找指定文件夹下的接口文件

        Args:
            logger: 日志记录器对象
        """
        root = tk.Tk()
        root.withdraw()
        filedir = filedialog.askdirectory()
        if not filedir:
            logger.info(f'未选择任何目录')
            return
        else:
            logger.info(f'选择的文件夹路径为：{filedir}')
        for foldername, _, filenames in os.walk(filedir):
            for filename in filenames:
                if filename.endswith('.xlsx') and filename.startswith('IF_List_') :
                    self._process_excel_file(foldername, filename, logger)

    def _process_excel_file(self,foldername,filename,logger):
        """处理单个Excel文件
        
        Args:
            foldername: 文件夹路径
            filename: 文件名
            logger: 日志记录器
        """
        match = re.search(r'IF_List_(.*).xlsx', filename)
        if not match:
            return
        swcname = match.group(1)
        filepath = os.path.join(foldername, filename)
        if swcname in self.swc_infos:
            error_msg = f'所选目录下存在多个相同的文件《{filename}》'
            logger.error(error_msg)
            raise ValueError(error_msg)  
        self.swc_infos[swcname] = {'path': filepath}

    def get_xlsx_info(self,logger):
        """获取Excel文件中的接口信息
        
        Args:
            logger: 日志记录器
        """
        for swcname,info in self.swc_infos.items(): 
            try:
                logger.info(f"{info['path']} IF文件信息获取开始.")
                self._current_wb = openpyxl.load_workbook(info['path'], data_only=True)
                filename = os.path.basename(info['path'])
                self.check_xlsx_info(filename,logger)
                self.only=[]
                info['info_sr'],info['info_cs'],info['info_appdatatypedef'] = [],[],[]

                for sheet in self.REQUIRED_SHEETS:
                    if sheet in ['Runnable']: 
                        info['task_cycle'] = self._get_task_cycle(swcname, filename, sheet, logger)
                    elif sheet in ['AppDataTypeDef']:
                        info['info_appdatatypedef'] =  self._get_appdatatypedef_info(swcname, filename, sheet,logger)
                    elif sheet in ['Input','Output']:
                        info['info_sr'].extend(
                            self._get_sr_interface_info(swcname, filename, sheet, logger)
                        )
                    elif sheet in ['CS']:
                        info['info_cs'].extend(
                            self._get_cs_interface_info(swcname, filename, sheet, logger)
                        )
                self._validate_only(filename, logger)
                logger.info(f"{info['path']} IF文件信息获取结束.")
            finally:
                if self._current_wb:
                    self._current_wb.close()

    def _validate_only(self,filename,logger):
        """检查Excel文件接口名 自定义名是否存在重名的情况
        
        Args:
            filename: 文件名
            logger: 日志记录器
        """
        # 检查是否存在重名情况
        only_names = list(set(self.only))
        if len(only_names) != len(self.only):
            duplicate_names = [name for name in only_names if self.only.count(name) > 1]
            error_msg = f"SR接口---excel名:《{filename}》 存在重名情况《{duplicate_names}》"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def check_xlsx_info(self,filename,logger):
        """检查Excel文件格式是否符合要求
        
        Args:
            filename: 文件名
            logger: 日志记录器
        """
        # 检查必需的工作表
        missing_sheets = [
            sheet for sheet in self.REQUIRED_SHEETS 
            if sheet not in self._current_wb.sheetnames
        ]
        if missing_sheets:
            error_msg = f'《{filename}》 文件缺少表单《{missing_sheets}》'
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 检查各工作表的必需列
        for sheet in self.REQUIRED_SHEETS:
            worksheet = self._current_wb[sheet]
            title_row = [cell.value for cell in worksheet[1]]
            
            missing_columns = [col for col in self.REQUIRED_COLUMNS[sheet] if col not in title_row]
            if missing_columns:
                error_msg = f'《{filename}》 文件,表单 《{sheet}》 中缺少必要的列 《{missing_columns}》'
                logger.error(error_msg)
                raise ValueError(error_msg)    

    def _get_task_cycle(self,swcname,filename,sheet,logger):
        """获取任务周期信息
        
        Args:
            swc_name: SWC名称
            filename: 文件名
            sheet: 工作表名
            logger: 日志记录器
            
        Returns:
            任务周期(ms)
        """
        worksheet = self._current_wb[sheet]
        title_row = [cell.value for cell in worksheet[1]]
        col_index = title_row.index('周期ms') + 1
        
        task_cycle = worksheet.cell(row=2, column=col_index).value
        
        if not str(task_cycle).isdigit():
            error_msg = f'文件 《{filename}》,表单 《{sheet}》 中Task周期包含非数字 《{task_cycle}》'
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        return int(task_cycle)

    def _get_sr_interface_info(self,swc_name,filename,sheet,logger) :
        """获取SR接口信息
        
        Args:
            swc_name: SWC名称
            filename: 文件名
            sheet: 工作表名
            logger: 日志记录器
            
        Returns:
            SR接口信息列表
        """
        worksheet      = self._current_wb[sheet]
        title_row      = [cell.value for cell in worksheet[1]]
        
        pp_name_col    = title_row.index('SignalName') + 1
        pi_name_col    = title_row.index('SignalName') + 1
        ie_name_col    = title_row.index('SignalName') + 1
        data_type_col  = title_row.index('DataType') + 1
        dimension_col  = title_row.index('Dimension') + 1
        init_value_col = title_row.index('InitValue') + 1
        nv_data_col    = title_row.index('nvData') + 1
        desc_col       = title_row.index('Description') + 1
        
        direction = self.INTERFACE_DIRECTION[sheet]
        enableupdate_col = title_row.index('enableUpdate') + 1 if direction == 'receiver'  else None
        
        interfaces = []
        
        for row in range(2, worksheet.max_row + 1):
            pp_name = worksheet.cell(row=row, column=pp_name_col).value
            pi_name = worksheet.cell(row=row, column=pi_name_col).value
            ie_name = worksheet.cell(row=row, column=ie_name_col).value
            
            if not pp_name or not str(pp_name).strip():
                continue
                
            try:
                data_type    = worksheet.cell(row=row, column=data_type_col).value
                dimension    = str(worksheet.cell(row=row, column=dimension_col).value)
                init_value   = str(worksheet.cell(row=row, column=init_value_col).value)
                desc         = str(worksheet.cell(row=row, column=desc_col).value) 
                nv_data      = str(worksheet.cell(row=row, column=nv_data_col).value) if worksheet.cell(row=row, column=nv_data_col).value else 'false'
                enableupdate = worksheet.cell(row=row, column=enableupdate_col).value if direction == 'receiver'  else 'false'
                enableupdate = str(enableupdate) if enableupdate  else 'false'
                
                
                validated_data = self._validate_sr_interface_data(
                    pp_name, pi_name, ie_name, data_type, dimension, init_value,nv_data,enableupdate,desc,
                    filename, sheet, row, swc_name, logger
                )
                '''-('filename','sheet','swcname','Cell_SR','Cell_PpName','Cell_PiName',
                'Cell_DataElement','DataType','Dimension','InitValue','nvData','enableUpdate','Description')-'''
                interfaces_info = (filename,sheet,swc_name,direction,validated_data[0],validated_data[1],validated_data[2],
                    validated_data[3],validated_data[4],validated_data[5],validated_data[6],validated_data[7],validated_data[8])       
                interfaces.append(interfaces_info)
            except Exception as e:
                logger.error(f"处理SR接口信息时出错: {str(e)}")
                raise
                
        return interfaces

    def _validate_sr_interface_data(self,pp_name,pi_name,ie_name,data_type,dimension,init_value,nv_data,enableupdate,desc,filename,sheet,row,swc_name,logger):
        """验证SR接口数据的有效性
        
        Args:
            pp_name: 端口信号名称
            pi_name: 接口信号名称
            ie_name: 接口元素名称
            data_type: 数据类型
            dimension: 维度
            init_value: 初始值
            filename: 文件名
            sheet: 工作表名
            row: 行号
            swc_name: swc名称
            logger: 日志记录器
            
        Returns:
            验证后的(pp_name, pi_name, ie_name, data_type, dimension, init_value)元组
        """
        # 检查空值或无效值
        if not all([pp_name, pi_name, ie_name, data_type, dimension, init_value]):
            error_msg = f"SR接口---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 关键值:《{pp_name}》缺少必要信息"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # 去除空格并检查
        pp_name       = pp_name.strip()
        pi_name       = pi_name.strip()
        ie_name       = ie_name.strip()
        data_type     = data_type.strip()
        dimension     = dimension.strip()
        init_value    = init_value.strip()
        nv_data       = nv_data.strip().lower()
        enableupdate  = enableupdate.strip().lower()
        desc          = desc.strip()
        if desc:
            desc = desc.replace("\n", " ")
        
        if any(val == '' or val == 'None' or ' ' in val 
               for val in [pp_name, pi_name, ie_name, data_type, dimension, init_value]):
            error_msg = f"SR接口---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 关键值:《{pp_name}》包含无效值"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # 检查数据类型是否在映射表中
        if data_type.lower() not in self.DATA_TYPE_MAPPING and not data_type.startswith('st_'):
            error_msg = f"SR接口---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 不支持的数据类型《{data_type}》"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # 转换维度和初始值
        try:
            dimension = int(dimension)
            # 处理结构体格式的初始值
            if init_value.startswith('{') and init_value.endswith('}'):
                parts = init_value[1:-1].split(',')
                if len(parts) == len(self.swc_infos[swc_name]['info_appdatatypedef'][data_type]['MemberDataType']):
                    init_value_dst = [float(part) if '.' in part else int(part) for part in parts]
                else:
                    error_msg  = f"SR接口---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 结构体类型初始值和成员个数不匹配"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            else:
                init_value = float(init_value) if '.' in init_value else int(init_value)
        except ValueError:
            error_msg  = f"SR接口---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 无法转换维度或初始值"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # 检查布尔类型的初始值
        if data_type.lower() == 'boolean' and init_value not in (0, 1):
            error_msg = f"SR接口---excel名:《{filename}》Sheet:《{sheet}》 《{pp_name}》boolean类型初始值不为0或1《{init_value}》"
            logger.error(error_msg)
            raise ValueError(error_msg)
        if data_type.startswith('st_'):
            for i in range(len(init_value_dst)):
                if self.swc_infos[swc_name]['info_appdatatypedef'][data_type]['MemberDataType'][i] == 'boolean' and init_value_dst[i] not in (0, 1):
                    error_msg = f"SR接口---excel名:《{filename}》Sheet:《{sheet}》 《{pp_name}》boolean类型初始值不为0或1《{init_value_dst}》"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
        # 检查nvData enableUpdate是否填写为true或false
        if nv_data  not in ['true','false'] or enableupdate not in ['true','false']:
            error_msg = f"SR接口---excel名:《{filename}》Sheet:《{sheet}》 《{pp_name}》的参数nvData enableUpdate《{nv_data}》 or 《{enableupdate}》 不是true或false"
            logger.error(error_msg)
            raise ValueError(error_msg)
        # 检查nvData enableUpdate是否都为true
        if nv_data in ['true'] and enableupdate in ['true']:
            error_msg = f"SR接口---excel名:《{filename}》Sheet:《{sheet}》 《{pp_name}》的参数nvData enableUpdate《{nv_data}》 and 《{enableupdate}》 都是true"
            logger.error(error_msg)
            raise ValueError(error_msg)
        nv_data = True if nv_data == 'true' else False
            
        self.only.append(pi_name)
        if data_type.startswith('st_'):
            return (pp_name,pi_name,ie_name, data_type, dimension, init_value_dst,nv_data,enableupdate,desc)
        else:  
            return (pp_name,pi_name,ie_name, self.DATA_TYPE_MAPPING[data_type.lower()], dimension, init_value,nv_data,enableupdate,desc)

    def _get_appdatatypedef_info(self,swc_name, filename, sheet,logger):
        """获取AppDataTypeDef信息
        
        Args:
            swc_name: SWC名称
            filename: 文件名
            sheet: 工作表名
            logger: 日志记录器
            
        Returns:
            AppDataTypeDef信息列表
        """
        worksheet          = self._current_wb[sheet]
        title_row          = [cell.value for cell in worksheet[1]]

        appdatatype_col    = title_row.index('AppDataType') + 1
        structname_col     = title_row.index('StructName') + 1
        membername_col     = title_row.index('MemberName') + 1
        memberdatatype_col = title_row.index('MemberDataType') + 1

        interfaces = {}
        
        for row in range(2, worksheet.max_row + 1):
            structname = worksheet.cell(row=row, column=structname_col).value
            
            if not structname or not str(structname).strip():
                continue
                
            try:
                appdatatype    = worksheet.cell(row=row, column=appdatatype_col).value
                membername     = worksheet.cell(row=row, column=membername_col).value
                memberdatatype = worksheet.cell(row=row, column=memberdatatype_col).value
                
                validated_data = self._validate_appdatatypedef_data(
                    appdatatype, structname,membername, memberdatatype, 
                    filename, sheet, row, swc_name, logger
                )
                '''-('AppDataType','StructName','MemberName' ,'MemberDataType',  )-'''
                interfaces_info = {}
                interfaces_info['SWCName']        = swc_name
                interfaces_info['AppDataType']    = validated_data['appdatatype']
                interfaces_info['StructName']     = validated_data['structname']
                interfaces_info['MemberName']     = validated_data['membername']
                interfaces_info['MemberDataType'] = validated_data['memberdatatype']
                interfaces[validated_data['structname']] = interfaces_info
            except Exception as e:
                logger.error(f"处理AppDataTypeDef信息时出错: {str(e)}")
                raise
                
        return interfaces
    def _validate_appdatatypedef_data(self,appdatatype,structname, membername, memberdatatype,filename,sheet,row,swc_name,logger):
        """验证AppDataTypeDef接口数据的有效性
        
        Args:
            appdatatype: 自定义数据类型
            structname: 结构体名
            membername: 成员名
            memberdatatype: 成员类型
            filename: 文件名
            sheet: 工作表名
            row: 行号
            swc_name: SWC名称
            logger: 日志记录器
            
        Returns:
            验证后的AppDataTypeDef数据字典
        """

        # 检查必要字段是否为空
        if not all([appdatatype, structname, membername, memberdatatype]):
            error_msg = f"AppDataTypeDef---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 缺少必要信息"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # 去除空格并检查
        appdatatype      = appdatatype.strip()
        structname       = structname.strip()
        membername       = membername.strip()
        memberdatatype   = memberdatatype.strip()
        
        if any(val == '' or val == 'None' 
               for val in [appdatatype, structname, membername, memberdatatype]):
            error_msg = f"AppDataTypeDef---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 包含无效值"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if any(' ' in val 
               for val in [appdatatype, structname]):
            error_msg = f"AppDataTypeDef---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 包含无效值"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # 去除空格并检查
        membername_list_src = membername[1:-1].split(',')
        membername_list_dst = [item.strip() for item in membername_list_src]
        if any(' ' in val 
               for val in membername_list_dst):
            error_msg = f"AppDataTypeDef---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 包含无效值"
            logger.error(error_msg)
            raise ValueError(error_msg)
        memberdatatype_list_src = memberdatatype[1:-1].split(',')
        memberdatatype_list_dst = [item.strip().lower() for item in memberdatatype_list_src]
        if any(' ' in val 
               for val in memberdatatype_list_dst):
            error_msg = f"AppDataTypeDef---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 包含无效值"
            logger.error(error_msg)
            raise ValueError(error_msg)
        if len(membername_list_dst) != len(memberdatatype_list_dst):
            error_msg = f"AppDataTypeDef---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 成员个数和成员类型个数不匹配"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 检查是membername否存在重名情况
        only_names = list(set(membername_list_dst))
        if len(only_names) != len(membername_list_dst):
            duplicate_names = [name for name in only_names if membername_list_dst.count(name) > 1]
            error_msg = f"AppDataTypeDef---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 存在重名情况《{duplicate_names}》"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 检查数据类型是否在映射表中
        if any(data_type not in self.DATA_TYPE_MAPPING for data_type in memberdatatype_list_dst):
            error_msg = f"AppDataTypeDef---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 《{memberdatatype_list_dst}》存在不支持的数据类型"
            logger.error(error_msg)
            raise ValueError(error_msg)
        else:
            memberdatatype_list_dstt = [self.DATA_TYPE_MAPPING[item] for item in memberdatatype_list_dst]

        # 检查结构体名是否符合规范
        if not structname.startswith('st_'):
            error_msg = f"AppDataTypeDef---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 《{structname}》名字不符合要求,没有使用《st_》开头"
            logger.error(error_msg)
            raise ValueError(error_msg)

        self.only.append(structname)      
        return {
            'appdatatype': appdatatype,
            'structname': structname,
            'membername': membername_list_dst,
            'memberdatatype': memberdatatype_list_dstt
        }

    def _get_cs_interface_info(self,swc_name,filename,sheet,logger):
        """获取CS接口信息
        
        Args:
            swc_name: SWC名称
            filename: 文件名
            sheet: 工作表名
            logger: 日志记录器
            
        Returns:
            CS接口信息列表
        """
        worksheet          = self._current_wb[sheet]
        title_row          = [cell.value for cell in worksheet[1]]
        
        cs_col             = title_row.index('CorS') + 1
        port_name_col      = title_row.index('PortName') + 1
        port_interface_col = title_row.index('PortInerfaceName') + 1
        operation_col      = title_row.index('Operation') + 1
        argument_col       = title_row.index('Argument') + 1
        fun_return_col     = title_row.index('函数返回') + 1
        isservice_col      = title_row.index('isService') + 1
        desc_col           = title_row.index('Description') + 1
        
        interfaces = []
        
        for row in range(2, worksheet.max_row + 1):
            port_name = worksheet.cell(row=row, column=port_name_col).value
            
            if not port_name or not str(port_name).strip():
                continue
                
            try:
                cs_direction   = worksheet.cell(row=row, column=cs_col).value
                port_interface = worksheet.cell(row=row, column=port_interface_col).value
                operation      = worksheet.cell(row=row, column=operation_col).value
                argument       = worksheet.cell(row=row, column=argument_col).value
                fun_return     = worksheet.cell(row=row, column=fun_return_col).value
                desc           = str(worksheet.cell(row=row, column=desc_col).value) 
                isservice      = str(worksheet.cell(row=row, column=isservice_col).value) if worksheet.cell(row=row, column=isservice_col).value else 'false'
                
                validated_data = self._validate_cs_interface_data(
                    cs_direction, port_name, port_interface, operation, 
                    argument, fun_return,isservice,desc, filename, sheet, row, logger
                )
                if len(validated_data['operation']) > 1:
                    error_msg = f"CS接口---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 暂时不支持多个Operation"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                '''-('SWCName','Direction','PortName'   ,'PortInerface','Operation'     ,'Argument'     ,'FunReturn','isService'  )-'''
                interfaces_info = {}
                interfaces_info['SWCName']      = swc_name
                interfaces_info['Direction']    = validated_data['direction']
                interfaces_info['PortName']     = validated_data['port_name']
                interfaces_info['PortInerface'] = validated_data['port_interface']
                interfaces_info['Operation']    = validated_data['operation']
                interfaces_info['Argument']     = validated_data['argument']
                interfaces_info['FunReturn']    = validated_data['fun_return']
                interfaces_info['isService']    = validated_data['isservice']
                interfaces_info['Description']  = validated_data['desc']
                interfaces.append(interfaces_info)
            except Exception as e:
                logger.error(f"处理CS接口信息时出错: {str(e)}")
                raise
                
        return interfaces

    def _validate_cs_interface_data(self,cs_direction,port_name,port_interface,operation,argument,fun_return,isservice,desc,filename,sheet,row,logger):
        """验证CS接口数据的有效性
        
        Args:
            cs_direction: 方向(client/server)
            port_name: 端口名
            port_interface: 端口接口名
            operation: 操作
            argument: 参数
            fun_return: 函数返回
            filename: 文件名
            sheet: 工作表名
            row: 行号
            logger: 日志记录器
            
        Returns:
            验证后的CS接口数据字典
        """
        # 检查方向是否有效
        if cs_direction.strip().lower() not in self.INTERFACE_DIRECTION[sheet]:
            error_msg = f"CS接口---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 无效的方向《{cs_direction}》"
            logger.error(error_msg)
            raise ValueError(error_msg)
        cs_direction = cs_direction.strip().lower()
        # 检查必要字段是否为空
        if not all([port_name, port_interface, operation, argument, fun_return]):
            error_msg = f"CS接口---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 缺少必要信息"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # 去除空格并检查
        port_name      = port_name.strip()
        port_interface = port_interface.strip()
        operation      = operation.strip()
        argument       = argument.strip()
        fun_return     = fun_return.strip()
        isservice      = isservice.strip().lower()
        desc           = desc.strip()
        if desc:
            desc = desc.replace("\n", " ")
        
        if any(val == '' or val == 'None' 
               for val in [port_name, port_interface, operation, argument, fun_return]):
            error_msg = f"CS接口---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 包含无效值"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if any(' ' in val 
               for val in [port_name, port_interface, operation]):
            error_msg = f"CS接口---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 包含无效值"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # 检查函数返回值
        if 'E_NOT_OK' not in fun_return:
            error_msg = f"CS接口---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行: 暂时不支持无函数返回"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 检查isService是否为true or false
        if isservice not in ['true','false']:
            error_msg = f"CS接口---excel名:《{filename}》Sheet:《{sheet}》 第《{row}》行,isService 不为true or false"
            logger.error(error_msg)
            raise ValueError(error_msg)
        isservice = True if isservice == 'true' else False

        self.only.append(port_interface)      
        return {
            'direction': cs_direction,
            'port_name': port_name,
            'port_interface': port_interface,
            'operation': operation.split('\n'),
            'argument': argument.split('\n'),
            'fun_return': fun_return,
            'isservice':isservice,
            'desc':desc
        }

    def xlsx_info_main(self,logger):
        """主入口方法
        
        Args:
            logger: 日志记录器
        """
        self.find_xlsx_files(logger)
        logger.info('Read 《IF_List_SWCName.xlsx》 File Start...')
        self.get_xlsx_info(logger)
        logger.info('Read 《IF_List_SWCName.xlsx》 File End!')
