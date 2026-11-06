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

import autosar
import os
import re

class ArxmlGenerator():
    """生成arxml文件"""
    def __init__(self):
        """初始化方法"""
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
        'uint64'  :'uint64',}
        self.SR_DATA_INDEX = ['filename','sheet','swcname','Cell_SR','Cell_PpName','Cell_PiName','Cell_DataElement','DataType','Dimension','InitValue','nvData','enableUpdate','Description']
        self._reset_instance_variables()
    
    def generate_arxml_files(self, swc_infos, logger):
        """Main method to generate ARXML files for all SWCs.
        
        Args:
            swc_infos: Dictionary containing SWC information
            logger: Logger instance for logging messages
        """
        logger.info('Starting ARXML generation...')
        
        try:
            for swc_name, swc_info in swc_infos.items():
                self._process_single_swc(swc_name, swc_info, logger)
                
        except Exception as e:
            logger.error(f"Error during ARXML generation: {str(e)}")
            raise
            
        logger.info('ARXML generation completed successfully!')

    def _process_single_swc(self, swc_name, swc_info, logger):
        """Process a single SWC to generate its ARXML file."""
        logger.info(f"Generating ARXML for {swc_name}...")
        
        try:
            self._reset_instance_variables()
            self._initialize_swc_data(swc_name, swc_info, logger)
            
            # Create ARXML structure
            self._create_workspace_and_packages()
            self._create_base_data_types()
            self._create_array_data_types()
            self._create_array_data_constants()
            self._create_sr_port_interfaces()
            self._create_cs_port_interfaces(logger)
            self._create_components(logger)
            
            # Save the ARXML file
            self.ws.saveXML(self.arxml_file_path)
            logger.info(f"Successfully generated {swc_name}.arxml")
            
        except Exception as e:
            logger.error(f"Error processing SWC {swc_name}: {str(e)}")
            raise

    def _reset_instance_variables(self):
        """Reset instance variables for each new SWC processing."""
        self.arxml_file_path = None
        self.package_name = None
        self.swc_name = None
        self.task_cycle = None
        self.sr_port_data = None
        self.cs_port_data = None
        self.appdatatype_data = None 
        self.ws = None   

    def _initialize_swc_data(self, swc_name, swc_info, logger):
        """Initialize SWC-specific data and check file paths."""
        self.arxml_file_path = self._get_arxml_file_path(swc_name, swc_info['path'])
        self._cleanup_existing_file(logger)
        self.package_name = f'Package_{swc_name}'
        self.swc_name = swc_name
        self.task_cycle = swc_info['task_cycle']
        self.sr_port_data = swc_info['info_sr']
        self.cs_port_data = swc_info['info_cs']
        self.appdatatype_data = swc_info['info_appdatatypedef']
        self.ws = autosar.workspace(version='4.3.0')

    def _get_arxml_file_path(self, swc_name, swc_path):
        """Generate the ARXML file path for the given SWC."""
        return os.path.join(os.path.dirname(swc_path), f"{swc_name}.arxml")

    def _cleanup_existing_file(self, logger):
        """Remove existing ARXML file if it exists."""
        if os.path.exists(self.arxml_file_path):
            try:
                os.remove(self.arxml_file_path)
            except OSError as e:
                error_msg = f"Failed to remove existing file {self.arxml_file_path}: {str(e)}"
                logger.error(error_msg)
                raise OSError(error_msg)
    
    def _create_workspace_and_packages(self): 
        """Create the workspace and required packages."""
        package_all = self.ws.createPackage(self.package_name)
        # Data type packages
        data_types = package_all.createSubPackage('DataTypes',role='DataType')
        data_types.createSubPackage('CompuMethods',role='CompuMethod')
        data_types.createSubPackage('DataConstrs',role='DataConstraint')
        data_types.createSubPackage('Units',role='Unit')
        data_types.createSubPackage('BaseTypes')
        data_types.createSubPackage('ImplementationTypes')
        # Other packages
        package_all.createSubPackage('PortInterfaces',role='PortInterface')
        package_all.createSubPackage('ComponentTypes',role='ComponentType')
        package_all.createSubPackage('Constants', role='Constant')

    def _create_base_data_types(self):
        """Create base data types and implementation types."""
        base_types = self.ws.find(f'/{self.package_name}/DataTypes/BaseTypes')
        
        # Define base types
        type_definitions = [
            ('boolean', 8, 'BOOLEAN', 'boolean'),
            ('float32', 32, 'IEEE754', 'float32'),
            ('sint8', 8, '2C', 'sint8'),
            ('sint16', 16, '2C', 'sint16'),
            ('sint32', 32, '2C', 'sint32'),
            ('uint8', 8, None, 'uint8'),
            ('uint16', 16, None, 'uint16'),
            ('uint32', 32, None, 'uint32'),
            ('uint64', 64, None, 'uint64')
        ]
        
        for name, size, encoding, native_decl in type_definitions:
            if encoding:
                base_types.createSwBaseType(name, size, encoding=encoding, nativeDeclaration=native_decl)
            else:
                base_types.createSwBaseType(name, size, nativeDeclaration=native_decl)
        
        # Create implementation types
        self._create_implementation_types()

    def _create_implementation_types(self):
        """Create implementation data types."""
        impl_types = self.ws.find(f'/{self.package_name}/DataTypes/ImplementationTypes')
        base_type_ref = f'/{self.package_name}/DataTypes/BaseTypes/'
        
        type_ranges = {
            'boolean': (0, 1),
            'sint8': (-128, 127),
            'sint16': (-32768, 32767),
            'sint32': (-2147483648, 2147483647),
            'uint8': (0, 255),
            'uint16': (0, 65535),
            'uint32': (0, 4294967295),
            'uint64': (0, 18446744073709551615)
        }
        
        for type_name in type_ranges:
            lower, upper = type_ranges[type_name]
            impl_types.createImplementationDataType(
                type_name,
                lowerLimit=lower,
                upperLimit=upper,
                baseTypeRef=f'{base_type_ref}{type_name}',
                typeEmitter='Platform_Type'
            )
        
        # Float types have no limits
        impl_types.createImplementationDataType(
            'float32',
            baseTypeRef=f'{base_type_ref}float32',
            typeEmitter='Platform_Type'
        )

        # 结构体数据类型定义
        for key,value in self.appdatatype_data.items():
            struct_type_name = value['StructName']
            struct_member = []
            for i in range(len(value['MemberName'])):
                struct_member.append((value['MemberName'][i],f"/{self.package_name}/DataTypes/ImplementationTypes/{value['MemberDataType'][i]}"))
            impl_types.createImplementationRecordDataType(struct_type_name,struct_member)

    def _create_array_data_types(self):
        """Create array data types for SR port data."""
        # f'/{self.package_name}/DataTypes/ImplementationTypes'
        impl_types = self.ws.find(f'/{self.package_name}/DataTypes/ImplementationTypes')
        created_types = set()
        
        for data_info in self.sr_port_data:
            data_type = data_info[self.SR_DATA_INDEX.index('DataType')]
            dimension = data_info[self.SR_DATA_INDEX.index('Dimension')]
            
            if dimension > 1:  # Only create for arrays
                array_type_name = f"{data_type}_array_{dimension}"
                if array_type_name not in created_types:
                    impl_types.createImplementationArrayDataType(
                        array_type_name,
                        arraySize=dimension,
                        implementationTypeRef=f'/{self.package_name}/DataTypes/ImplementationTypes/{data_type}',
                        typeEmitter='Platform_Type'
                    )
                    created_types.add(array_type_name)

    def _create_array_data_constants(self):
        """Create constants for array data."""
        constants = self.ws.find(f'/{self.package_name}/Constants')
        created_constants = set()
        
        for data_info in self.sr_port_data:
            port_name  = data_info[self.SR_DATA_INDEX.index('Cell_PpName')]
            data_type  = data_info[self.SR_DATA_INDEX.index('DataType')]
            dimension  = data_info[self.SR_DATA_INDEX.index('Dimension')]
            init_value = data_info[self.SR_DATA_INDEX.index('InitValue')]
            if not data_type.startswith(f'st_'):
                if dimension > 1:  # Only create for arrays
                    const_name = f"{port_name}{data_type}_Const_{dimension}_{init_value}"
                    if const_name not in created_constants:
                        init_values = [init_value] * dimension
                        constants.createConstant(
                            const_name,
                            typeRef=f'/{self.package_name}/DataTypes/ImplementationTypes/{data_type}_array_{dimension}',
                            initValue=init_values
                        )
                        created_constants.add(const_name)
            else:#处理结构体常量for key,value in self.appdatatype_data.items():
                const_name = f"{port_name}{data_type}_Const_{dimension}"
                if dimension > 1:  # Only create for arrays
                    list_dict = []
                    for i in range(dimension):
                        list_dict.append(dict(zip(self.appdatatype_data[data_type]['MemberName'],init_value)))
                    constants.createConstant(const_name,f'/{self.package_name}/DataTypes/ImplementationTypes/{data_type}_array_{dimension}',list_dict)
                else:
                    member_dict = dict(zip(self.appdatatype_data[data_type]['MemberName'],init_value))
                    constants.createConstant(const_name,f"/{self.package_name}/DataTypes/ImplementationTypes/{data_type}",member_dict)
             
    def _create_sr_port_interfaces(self):
        """Create sender-receiver port interfaces."""
        package = self.ws.find(f'/{self.package_name}/PortInterfaces')
        created_interfaces = set()
        
        for data_info in self.sr_port_data:
            pi_name      = data_info[self.SR_DATA_INDEX.index('Cell_PiName')]
            data_element = data_info[self.SR_DATA_INDEX.index('Cell_DataElement')]
            data_type    = data_info[self.SR_DATA_INDEX.index('DataType')]
            dimension    = data_info[self.SR_DATA_INDEX.index('Dimension')]
            nvdata       = data_info[self.SR_DATA_INDEX.index('nvData')]
            description  = data_info[self.SR_DATA_INDEX.index('Description')]
            if pi_name not in created_interfaces:
                type_ref = (
                    f"{data_type}_array_{dimension}" if dimension > 1 
                    else data_type
                )
                if nvdata == True:
                    pi = package.createNvDataInterface(
                        pi_name,
                        nvDatas = autosar.element.DataElement(
                            data_element,
                            f'/{self.package_name}/DataTypes/ImplementationTypes/{type_ref}'
                        )
                    )
                    if description and description != 'None':
                        pi.__setattr__('desc',description)
                else:
                    pi = package.createSenderReceiverInterface(
                        pi_name,
                        autosar.element.DataElement(
                            data_element,
                            f'/{self.package_name}/DataTypes/ImplementationTypes/{type_ref}'
                        )
                    )
                    if description and description != 'None':
                        pi.__setattr__('desc',description)
                created_interfaces.add(pi_name)

    def _create_cs_port_interfaces(self, logger):
        """Create client-server port interfaces with error handling."""
        impl_types = self.ws.find(f'/{self.package_name}/DataTypes/ImplementationTypes')
        package = self.ws.find(f'/{self.package_name}/PortInterfaces')
        created_interfaces = set()
        created_array_types = set()
        
        for cs_info in self.cs_port_data:
            interface_name = cs_info['PortInerface']
            operation      = cs_info['Operation']
            isservice      = cs_info['isService']
            description    = cs_info['Description']
            
            if interface_name not in created_interfaces:
                # Create the interface with error definition
                port_interface = package.createClientServerInterface(
                    interface_name,
                    operations=[operation[0]],
                    errors=autosar.ApplicationError("E_NOT_OK", 1),
                    isService=isservice
                )
                port_interface[operation[0]].possibleErrors = "E_NOT_OK"
                if description and description != 'None':
                    port_interface.__setattr__('desc',description)
                created_interfaces.add(interface_name)
                
                # Process arguments
                for arg in cs_info['Argument']:
                    self._process_cs_argument(arg, port_interface, operation, cs_info, created_array_types, logger)

    def _process_cs_argument(self, arg, port_interface, operation, cs_info, created_array_types, logger):
        """Process a single CS interface argument."""
        try:
            arg_parts = arg.replace('/*', ' /*').split()
            if len(arg_parts) < 3:
                raise ValueError(f"Invalid argument format: {arg}")  
            arg_type = arg_parts[0].strip()
            arg_name = arg_parts[1].strip()
            direction = arg_parts[2].strip().lower()
            
            # Get mapped data type
            data_type = self.DATA_TYPE_MAPPING.get(arg_type)
            if not data_type:
                raise ValueError(f"Unsupported data type: {arg_type}")
            
            # Handle array types
            array_match = re.match(r'.*\[(\d+)\].*', arg_name)
            if array_match:
                array_size = array_match.group(1)
                base_name = re.match(r'(.*)\[\d+\]', arg_name).group(1)
                array_type_name = f"{data_type}_array_{array_size}_CS"
                
                if array_type_name not in created_array_types:
                    impl_types = self.ws.find(f'/{self.package_name}/DataTypes/ImplementationTypes')
                    impl_types.createImplementationArrayDataType(
                        array_type_name,
                        arraySize=array_size,
                        implementationTypeRef=f'/{self.package_name}/DataTypes/ImplementationTypes/{data_type}',
                        typeEmitter='Platform_Type'
                    )
                    created_array_types.add(array_type_name)
                
                type_ref = array_type_name
                arg_name = base_name
            else:
                type_ref = data_type
            # Create argument based on direction
            full_type_ref = f'/{self.package_name}/DataTypes/ImplementationTypes/{type_ref}'
            
            if 'in' in direction:
                port_interface[operation[0]].createInArgument(arg_name, full_type_ref)
            elif 'out' in direction:
                port_interface[operation[0]].createOutArgument(arg_name, full_type_ref)
            else:
                raise ValueError(f"Invalid direction '{direction}' for argument {arg_name}")
                
        except Exception as e:
            error_msg = f"Error processing argument '{arg}' for interface {cs_info['PortInerface']}: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _create_components(self, logger):
        """Create components with runnables and events."""

        package = self.ws.find(f'/{self.package_name}/ComponentTypes')
        component = package.createApplicationSoftwareComponent(self.swc_name)
        
        # Process SR ports
        port_access = self._create_sr_ports(component, logger)
    
        # Process CS ports
        self._create_cs_ports(component, logger, port_access)

        # Create main runnables
        self._create_main_runnables(component, port_access)

    def _create_sr_ports(self, component, logger):
        """Create sender-receiver ports and return port access list."""
        port_access = []
        created_ports = set()
        
        for data_info in self.sr_port_data:
            port_name = data_info[self.SR_DATA_INDEX.index('Cell_PpName')]
            if port_name in created_ports:
                continue
                
            direction      = data_info[self.SR_DATA_INDEX.index('Cell_SR')]
            interface_name = data_info[self.SR_DATA_INDEX.index('Cell_PiName')]
            data_type      = data_info[self.SR_DATA_INDEX.index('DataType')]
            dimension      = data_info[self.SR_DATA_INDEX.index('Dimension')]
            init_value     = data_info[self.SR_DATA_INDEX.index('InitValue')]
            isUpdate       = data_info[self.SR_DATA_INDEX.index('enableUpdate')]
            nvdata         = data_info[self.SR_DATA_INDEX.index('nvData')]
            
            try:
                if dimension > 1:  # Array type
                    if  data_type.startswith(f'st_'):
                        const_name = f"{port_name}{data_type}_Const_{dimension}"
                    else:
                        const_name = f"{port_name}{data_type}_Const_{dimension}_{init_value}"
                    if direction == "sender":
                        if nvdata == True:
                            component.createProvidePort(port_name, interface_name, ramBlockInitValueRef=const_name,romBlockInitValueRef=const_name)
                        else:
                            component.createProvidePort(port_name, interface_name, initValueRef=const_name)
                    else:
                        if nvdata == True:
                            component.createRequirePort(port_name, interface_name, initValueRef=const_name)
                        else:
                            component.createRequirePort(port_name, interface_name, initValueRef=const_name,enableUpdate=isUpdate)
                else:  # Scalar type
                    if  data_type.startswith(f'st_'):
                        const_name = f"{port_name}{data_type}_Const_{dimension}"
                    if direction == "sender":
                        if nvdata == True:
                            if  data_type.startswith(f'st_'):
                                component.createProvidePort(port_name, interface_name, ramBlockInitValueRef=const_name,romBlockInitValueRef=const_name)
                            else:
                                component.createProvidePort(port_name, interface_name, ramBlockInitValue=init_value,romBlockInitValue=init_value)
                        else:
                            if  data_type.startswith(f'st_'):
                                component.createProvidePort(port_name, interface_name, initValueRef=const_name)
                            else:
                                component.createProvidePort(port_name, interface_name, initValue=init_value)
                    else:
                        if nvdata == True:
                            if  data_type.startswith(f'st_'):
                                component.createRequirePort(port_name, interface_name, initValueRef=const_name)
                            else:
                                component.createRequirePort(port_name, interface_name, initValue=init_value)
                        else:
                            if  data_type.startswith(f'st_'):
                                component.createRequirePort(port_name, interface_name, initValueRef=const_name,enableUpdate=isUpdate)
                            else:
                                component.createRequirePort(port_name, interface_name, initValue=init_value,enableUpdate=isUpdate)
                if  nvdata == True:
                    port_access.append(f"{port_name}/{interface_name}")
                else:       
                    port_access.append(port_name)
                created_ports.add(port_name)
                
            except Exception as e:
                logger.error(f"Error creating SR port {port_name}: {str(e)}")
                raise
                
        return port_access

    def _create_main_runnables(self, component, port_access):
        """Create main runnables and events for the component."""
        component.behavior.createRunnable(f"{self.swc_name}_step", portAccess=port_access)
        component.behavior.createTimerEvent(
            f"{self.swc_name}_step",
            self.task_cycle,
            name='Event_Runnable_Step'
        )
        component.behavior.createRunnable(f"{self.swc_name}_initialize")
        component.behavior.createInitEvent(
            f"{self.swc_name}_initialize",
            name='Event_Runnable_Init'
        )

    def _create_cs_ports(self, component, logger, port_access):
        """Create client-server ports and associated runnables."""
        created_ports = set()
        
        for cs_info in self.cs_port_data:
            port_name = cs_info['PortName']
            if port_name in created_ports:
                continue
                
            direction = cs_info['Direction']
            interface_name = cs_info['PortInerface']
            operation = cs_info['Operation']
            
            try:
                if direction == 'client':
                    component.createRequirePort(port_name, interface_name)
                    port_access.append(f"{port_name}/{operation[0]}")
                elif direction == 'server':
                    component.createProvidePort(port_name, interface_name)
                    runnable_name = f"{self.swc_name}_{port_name}_Step"
                    component.behavior.createRunnable(runnable_name)
                    component.behavior.createOperationInvokedEvent(
                        runnableName=runnable_name,
                        operationRef=f"{port_name}/{operation[0]}"
                    )
                else:
                    raise ValueError(f"Invalid direction '{direction}' for port {port_name}")
                    
                created_ports.add(port_name)
                
            except Exception as e:
                logger.error(f"Error creating CS port {port_name}: {str(e)}")
                raise