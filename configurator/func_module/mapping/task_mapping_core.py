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
from collections import defaultdict
import threading
from func_module.health_monitor.logger import logger
from typing import List
from basic_func_module.base_common.load_plug_in import LoadPlugIn
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.autosar_utils.autosar_utils import AutosarUtils
from func_module.generator.rte.rte_parser import get_rte_codegen_dict
from basic_func_module.autosar_utils.utils import get_short_name, set_short_name
from func_module.mapping.task_mapping_helper import (
    TaskMappingTableItem,
    TaskMappingTreeItem,
    TaskMappingItemData,
    AswManager,
    RteManager,
    IbManager,
    BasicTaskScheduleTableManager,
    PortManager,
)


class TaskMappingInstance:
    task_mapping_instance = None
    task_mapping_data = None

    @classmethod
    def update_task_mapping_instance(
        cls, autosar_asw_class, autosar_bsw_class, autosar_system_class, autosar_ib_class, autosar_mod_class
    ):
        if not cls.task_mapping_data:
            cls.task_mapping_data = TaskMappingData()

        cls.task_mapping_data.autosar_asw_class = autosar_asw_class
        cls.task_mapping_data.autosar_bsw_class = autosar_bsw_class
        cls.task_mapping_data.autosar_system_class = autosar_system_class
        cls.task_mapping_data.autosar_ib_class = autosar_ib_class
        cls.task_mapping_data.autosar_mod_class = autosar_mod_class
        if not cls.task_mapping_instance:
            cls.task_mapping_instance = TaskMapping(cls.task_mapping_data)
        else:
            cls.task_mapping_instance.update_task_mapping(cls.task_mapping_data)

        return cls.task_mapping_instance

    @classmethod
    def get_task_mapping_instance(cls):
        return cls.task_mapping_instance

    @classmethod
    def check_task_mapping_config(cls, autosar_bsw_class):
        # 检查是否满足 update task mapping 的条件
        RELY_MODULE_LIST = ["EcuC", "Os", "Rte"]
        check_result = False
        los_str = ""
        for rely_module in RELY_MODULE_LIST:
            if not autosar_bsw_class.get(rely_module):
                los_str = f"Not found {rely_module} module!"
                break
            module_cfg = f"/ActiveEcuC/{rely_module}"
            if not autosar_bsw_class[rely_module].find(module_cfg):
                los_str = f"{autosar_bsw_class[rely_module].gds_elementtree_node_.base}: {module_cfg} not found!"
                break
        if los_str == "":
            check_result = True

        return check_result, los_str


class TaskMappingData:

    def __init__(self):
        self.autosar_asw_class = {}
        self.autosar_bsw_class = {}
        self.autosar_ib_class = {}
        self.autosar_system_class = {}
        self.autosar_mod_class = {}
        pass


class TaskMapping:
    lock = threading.RLock()

    def __init__(self, task_mapping_data: TaskMappingData):
        self.update_task_mapping(task_mapping_data)

    def update_task_mapping(self, task_mapping_data: TaskMappingData, init_flags="all", update_cfg=True):
        with self.lock:
            self.pre_init(task_mapping_data, init_flags, update_cfg)
            if not self.check_config():
                return
            self.init()

        self.post_update_os_ecuc()

    def pre_init(self, task_mapping_data, init_flags, update_cfg):
        self.task_mapping_data = task_mapping_data

        self.init_flags = init_flags
        self.update_cfg = update_cfg

        self.runnable_data = {"Application Components": {}, "Service Components": {}, "Schedulable Entities": {}}
        # NOTE:root_item具有管理item_data的作用
        self.root_item = TaskMappingTreeItem("root")

        self.table_headers = []
        self.item_list: List[TaskMappingTableItem] = []

        self.main_function_dict = defaultdict(list)
        self.swc_runnable_dict = defaultdict(list)

        # key:item_data.id,value:table_index
        self.item_map = {}
        # key:row, value:bit_mask
        self.bit_map = {}
        self.component_appls = {}
        self.os_event_count_dict = {}
        self.os_alarm_count_dict = {}
        self.port_alarm_ref_manager = {}
        self.port_event_ref_manager = {}
        self.is_row_count_changed = False
        # 记录task上timing event的状态
        self.task_timing_event_dict = {}

    @property
    def autosar_asw_class(self):
        return self.task_mapping_data.autosar_asw_class

    @property
    def autosar_bsw_class(self):
        return self.task_mapping_data.autosar_bsw_class

    @property
    def autosar_ib_class(self):
        return self.task_mapping_data.autosar_ib_class

    @property
    def autosar_system_class(self):
        return self.task_mapping_data.autosar_system_class

    @property
    def autosar_mod_class(self):
        return self.task_mapping_data.autosar_mod_class

    def check_config(self):
        os_autosar = self.autosar_bsw_class.get("Os")
        if os_autosar is None:
            logger.warning("Not found Os Module!")
            return False
        os_cfg = os_autosar.find("/ActiveEcuC/Os")
        if os_cfg is None:
            logger.warning(f"{os_autosar.gds_elementtree_node_.base}: /ActiveEcuC/Os not found!")
            return False
        ecuc_autosar = self.autosar_bsw_class.get("EcuC")
        if ecuc_autosar is None:
            logger.warning("Not found EcuC Module!")
            return False
        rte_autosar = self.autosar_bsw_class.get("Rte")
        if rte_autosar is None:
            logger.warning("Not found Rte module!")
            return False
        rte_cfg = rte_autosar.find("/ActiveEcuC/Rte")
        if rte_cfg is None:
            logger.warning(f"{rte_autosar.gds_elementtree_node_.base}: /ActiveEcuC/Rte not found!")
            return False
        return True

    def init(self):
        self.root_item = TaskMappingTreeItem("root")
        if isinstance(self.init_flags, str):
            self.init_flags = {self.init_flags}
        if "all" in self.init_flags:
            self.init_flags = {"application", "service", "schedulable"}

        if "application" in self.init_flags:
            application_component_data_dict, application_component_types = AswManager.get_application_components_data(
                self.autosar_asw_class
            )
            self.runnable_data.update({"Application Components": application_component_data_dict})
            RteManager.update_rte_sw_component_exclusive_area(
                application_component_types, self.autosar_mod_class["Rte"], self.autosar_bsw_class["Rte"]
            )

        if "service" in self.init_flags or "schedulable" in self.init_flags:
            service_component_data_dict, service_component_types = AswManager.get_service_components_data(
                self.autosar_asw_class
            )
            self.runnable_data.update({"Service Components": service_component_data_dict})
            RteManager.update_rte_sw_component_exclusive_area(
                service_component_types, self.autosar_mod_class["Rte"], self.autosar_bsw_class["Rte"]
            )

            schedulable_entities_data_dict, bsw_module_descriptions = IbManager.get_schedulable_entities_data(
                self.autosar_ib_class
            )

            self.runnable_data.update({"Schedulable Entities": schedulable_entities_data_dict})
            RteManager.update_rte_bsw_module_exclusive_area(
                bsw_module_descriptions, self.autosar_mod_class["Rte"], self.autosar_bsw_class["Rte"]
            )

        self.bind_related_events()
        self.init_tree_data()
        self.init_table_data()
        self.update_tree_data()

    def bind_related_events(self):
        service_components = self.runnable_data.get("Service Components", {})
        for swc_item in service_components.values():
            for event_info in swc_item.values():
                swc_name = event_info["Component"]
                runnable_name = event_info["RunnableName"]
                if event_info["IsMainFunction"]:
                    self.main_function_dict[runnable_name].append(event_info)
                else:
                    runnable_name = f"{swc_name}_{runnable_name}"
                    self.swc_runnable_dict[runnable_name].append(event_info)

        application_components = self.runnable_data.get("Application Components", {})
        for swc_item in application_components.values():
            for event_info in swc_item.values():
                if event_info["IsMainFunction"]:
                    continue
                swc_name = event_info["Component"]
                runnable_name = event_info["RunnableName"]
                runnable_name = f"{swc_name}_{runnable_name}"
                self.swc_runnable_dict[runnable_name].append(event_info)

        main_function_order = {}
        schedule_entities = self.runnable_data.get("Schedulable Entities", {})
        for swc_item in schedule_entities.values():
            for event_info in swc_item.values():
                if not event_info["IsMainFunction"]:
                    continue
                main_function_name = event_info["RunnableName"]
                period = event_info["Period"]
                module_name = event_info["Component"]

                i = main_function_order.get(main_function_name, 0)
                event_list = self.main_function_dict.get(main_function_name, [])
                if len(event_list) > i:
                    main_function_order[main_function_name] = i + 1
                    if str(event_list[i]["Period"]) != str(period):
                        log_str = (
                            f"{module_name} Module MainFunction and {module_name} "
                            "Service Component MainFunction Period inconsistency! "
                            "Please click the update button in CodeGen menu."
                        )
                        # TODO 转换为校验规则
                        logger.ui_error(log_str)
                    event_info["BindEvent"].append(event_list[i])
                    event_list[i]["BindEvent"].append(event_info)

    def init_tree_data(self):
        # 构建以root_item为根节点的树
        for key, val in self.runnable_data.items():
            primary = TaskMappingTreeItem(key, self.root_item)
            self.root_item.append_child(primary)
            for swc_name, runnables in val.items():
                swc_item = TaskMappingTreeItem(swc_name, primary)
                primary.append_child(swc_item)
                for runnable in runnables.values():
                    # runnable = event_info
                    # 1) 构建最终runnable节点
                    runnable_item = TaskMappingTreeItem(runnable, swc_item)
                    swc_item.append_child(runnable_item)

        # 多事件触发的runnable共用一个uuid
        for event_list in self.swc_runnable_dict.values():
            if len(event_list) == 0:
                continue
            if not event_list[0]["Parent"]:
                continue
            uuid = event_list[0]["Parent"].id
            for event in event_list:
                event["Parent"].id = uuid

        # service与schedule entity绑定event共用一个uuid
        for event_list in self.main_function_dict.values():
            for event in event_list:
                if not event["Parent"]:
                    continue
                uuid = event["Parent"].id
                for bind_event in event["BindEvent"]:
                    bind_event["Parent"].id = uuid

    def init_table_data(self):
        rte_autosar = self.autosar_bsw_class["Rte"]
        os_autosar = self.autosar_bsw_class["Os"]
        ecuc_autosar = self.autosar_bsw_class["EcuC"]
        os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
        OsManager = getattr(os_process, "OsManager")
        OsManager.update_os_ref(os_autosar)
        self.table_headers = OsManager.get_sorted_tasks(os_autosar, ecuc_autosar)
        rte_swc_instances, rte_bsw_module_instances = RteManager.get_rte_task_mapping_info(rte_autosar)
        task_mapping_dict = {}
        swc_max_position = self.update_swc_task_mapping_dict(self.root_item, rte_swc_instances, task_mapping_dict)
        bsw_max_position = self.update_bsw_module_task_mapping_dict(
            self.root_item, rte_bsw_module_instances, task_mapping_dict
        )
        max_position = max(swc_max_position, bsw_max_position)
        if max_position == -1:
            row_count = 1
        else:
            row_count = max_position + 2

        col_count = len(self.table_headers)
        for i in range(row_count * col_count):
            row = int(i / col_count)
            col = i - row * col_count
            task_name = self.table_headers[col]["OsTaskName"]
            item_data = None
            if task_name in task_mapping_dict and row in task_mapping_dict[task_name]:
                item_data = task_mapping_dict[task_name][row]
            table_item = TaskMappingTableItem(item_data)
            self.item_list.append(table_item)
            if isinstance(item_data, TaskMappingItemData):
                bind_item_list = self.get_bind_item_list(item_data)
                table_item.bind_item_list = bind_item_list
                for bind_item in bind_item_list:
                    self.map_runnable(bind_item, task_name, row, False)
        pass

    def post_update_os_ecuc(self):
        with self.lock:
            os_autosar = self.autosar_bsw_class["Os"]
            ecuc_autosar = self.autosar_bsw_class["EcuC"]
            mod_autosar = self.autosar_mod_class

            if not self.check_config():
                logger.warning("post update os ecuc check failed!")
                return

            # 1 get rte codegen dict
            asw_dict = {"asw": self.autosar_asw_class, "FlatExtract": self.autosar_system_class["FlatExtract"]}
            cfg_dict = {"asw": "", "rte": {}, "bsw": {}, "dbc": [], "ldf": [], "cdd": {}, "eb": {}}
            rte_codegen_dict, _ = get_rte_codegen_dict(
                asw_dict,
                self.autosar_bsw_class,
                self.autosar_system_class,
                self.autosar_ib_class,
                cfg_dict,
                parse_new_dict=False,
            )

            # 2 update os arxml based on rte codegen dict
            # these configsed are used SOLOLY within RTE
            self.update_spinlock_and_ioc_infos(os_autosar, mod_autosar["Os"], rte_codegen_dict)
            self.update_rte_schedule_table_info(os_autosar, mod_autosar["Os"], rte_codegen_dict)

            os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
            OsManager = getattr(os_process, "OsManager")
            task_dict = OsManager.get_os_task_dict(os_autosar, ecuc_autosar)

            self.update_os_by_sr_queue_waitpoint(rte_codegen_dict, task_dict)
            self.update_cs_infos(rte_codegen_dict, task_dict)

            self.remove_unused_infos()

            self.update_schedule_table_info()

    def get_task_info_by_col(self, col):
        if (col is None) or (col < 0) or (col > len(self.table_headers)):
            return None
        return self.table_headers[col]

    def get_col_by_task_name(self, task_name):
        if not task_name:
            return None

        col = None
        for i in range(len(self.table_headers)):
            if self.table_headers[i]["OsTaskName"] == task_name:
                col = i
                break
        return col

    def get_task_info_by_name(self, task_name):
        col = self.get_col_by_task_name(task_name)
        return self.get_task_info_by_col(col)

    def get_col_count(self):
        return len(self.table_headers)

    def get_row_count_status(self):
        return self.is_row_count_changed

    def reset_row_count_status(self):
        self.is_row_count_changed = False

    def get_row_count(self):
        col_count = self.get_col_count()
        if col_count == 0:
            return 0
        else:
            return int(len(self.item_list) / col_count)

    def get_os_info(self, task_info, event_info):
        os_event_name = None
        os_alarm_name = None
        if event_info["IsMainFunction"]:
            os_event_name, os_alarm_name = RteManager.get_bsw_os_info(task_info, event_info)
        else:
            os_event_name, os_alarm_name = RteManager.get_swc_os_info(task_info, event_info)

        return os_event_name, os_alarm_name

    def get_modeswitch_info(self, task_info, event_info):
        os_ms_event_name = None
        if event_info["TriggerEvent"] != "SwcModeSwitchEvent":
            return os_ms_event_name

        os_ms_event_name = f"Rte_Ev_MS_{task_info['OsTaskName']}"
        return os_ms_event_name

    def get_cs_info(self, port, t_info):
        task_name = t_info["OsTaskName"]
        timeout = int(port["timeout"])
        timeout_alarm_name = None
        timeout_event_name = None
        wait_point_event_name = None

        if timeout > 0:
            if port.get("return_mode") == "polling":
                client_name = port["name"]
                timeout_alarm_name = f"Rte_Al_Timeout_{port['component']}_{client_name}"
                timeout_event_name = f"Rte_Ev_Timeout_{port['component']}_{client_name}"
            else:
                timeout_alarm_name = f"Rte_Al_Timeout_{task_name}"
                timeout_event_name = f"Rte_Ev_Timeout_{task_name}"

        if port.get("return_mode") != "polling":
            wait_point_event_name = f"Rte_Ev_WaitPoint_{task_name}"

        return timeout_alarm_name, timeout_event_name, wait_point_event_name

    def remove_event_info(self, os_autosar, os_event_name, task_info, category="Normal"):
        if not os_event_name:
            return

        if os_event_name not in self.os_event_count_dict:
            return

        os_event_count = self.os_event_count_dict[os_event_name].get(category, 0)
        if os_event_count > 0:
            self.os_event_count_dict[os_event_name].update({category: os_event_count - 1})

        if sum(self.os_event_count_dict[os_event_name].values()) == 0:
            os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
            OsManager = getattr(os_process, "OsManager")
            OsManager.remove_os_event_info(os_autosar, os_event_name)
            OsManager.remove_task_event_ref(os_autosar, os_event_name, task_info)
            self.os_event_count_dict.pop(os_event_name)

    def add_event_info(self, os_autosar, mod_autosar, os_event_name, task_info, category="Normal"):
        if not os_event_name:
            return

        if os_event_name not in self.os_event_count_dict:
            os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
            OsManager = getattr(os_process, "OsManager")
            OsManager.add_os_event_info(os_autosar, mod_autosar, os_event_name, task_info)
            OsManager.add_task_event_ref(os_autosar, mod_autosar, os_event_name, task_info)
            self.os_event_count_dict.update({os_event_name: {}})

        os_event_count = self.os_event_count_dict[os_event_name].get(category, 0)
        self.os_event_count_dict[os_event_name].update({category: os_event_count + 1})

    def remove_alarm_info(self, os_autosar, os_alarm_name, os_appl_name, category="Normal"):
        if not os_alarm_name:
            return

        if os_alarm_name not in self.os_alarm_count_dict:
            return

        os_alarm_count = self.os_alarm_count_dict[os_alarm_name].get(category, 0)
        if os_alarm_count > 0:
            self.os_alarm_count_dict[os_alarm_name].update({category: os_alarm_count - 1})

        if sum(self.os_alarm_count_dict[os_alarm_name].values()) == 0:
            os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
            OsManager = getattr(os_process, "OsManager")
            OsManager.remove_os_alarm_info(os_autosar, os_alarm_name)
            OsManager.remove_appl_alarm_ref(os_autosar, os_alarm_name, os_appl_name)
            self.os_alarm_count_dict.pop(os_alarm_name)

    def add_alarm_info(self, os_autosar, mod_autosar, os_alarm_name, os_event_name, task_info, category="Normal"):
        # NOTE:这里允许os_event_name为空
        if not os_alarm_name:
            return

        if os_alarm_name not in self.os_alarm_count_dict:
            os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
            OsManager = getattr(os_process, "OsManager")
            OsManager.add_os_alarm_info(os_autosar, mod_autosar, os_alarm_name, os_event_name, task_info)
            OsManager.add_appl_alarm_ref(os_autosar, mod_autosar, os_alarm_name, task_info["OsApplName"])
            self.os_alarm_count_dict.update({os_alarm_name: {}})

        os_alarm_count = self.os_alarm_count_dict[os_alarm_name].get(category, 0)
        self.os_alarm_count_dict[os_alarm_name].update({category: os_alarm_count + 1})

    def unmap_runnable(self, item_data: TaskMappingItemData):
        rte_autosar = self.autosar_bsw_class.get("Rte")
        os_autosar = self.autosar_bsw_class.get("Os")

        if not item_data:
            return False

        # 如果已经是unmap状态，可以直接忽略
        if not item_data.mapped:
            return True

        i = self.get_item_index(item_data.id)
        if i is None:
            logger.error("the item_data is not in the map")
            return False

        col_count = self.get_col_count()
        cur_col = i % col_count

        task_info = self.get_task_info_by_col(cur_col)
        if not task_info:
            logger.error("get task info by col failed")
            return False

        bind_item_list = self.get_bind_item_list(item_data)
        for bind_item in bind_item_list:
            event_info = bind_item.data

            RteManager.remove_rte_instance(rte_autosar, event_info)
            os_event_name, os_alarm_name = self.get_os_info(task_info, event_info)
            self.remove_alarm_info(os_autosar, os_alarm_name, task_info["OsApplName"])
            self.remove_event_info(os_autosar, os_event_name, task_info)

            os_ms_event_name = self.get_modeswitch_info(task_info, event_info)
            self.remove_event_info(os_autosar, os_ms_event_name, task_info)

            bind_item.mapped = False
        self.remove_item_map(item_data.id)
        return True

    def map_runnable(self, item_data: TaskMappingItemData, task_name, row, is_update_row=True):
        rte_autosar = self.autosar_bsw_class.get("Rte")
        os_autosar = self.autosar_bsw_class.get("Os")
        mod_autosar = self.autosar_mod_class

        if not item_data or not task_name:
            return False

        # 如果已经是map状态，可以直接忽略
        if item_data.mapped:
            return True

        col = self.get_col_by_task_name(task_name)
        if col is None:
            return False

        task_info = self.get_task_info_by_name(task_name)
        if not task_info:
            logger.error("get task info by col failed")
            return False
        bind_item_list = self.get_bind_item_list(item_data)
        for bind_item in bind_item_list:
            event_info = bind_item.data
            RteManager.add_rte_instance(rte_autosar, mod_autosar["Rte"], row, task_info, event_info)
            os_event_name, os_alarm_name = self.get_os_info(task_info, event_info)
            # self.add_alarm_info(os_autosar, mod_autosar["Os"], os_alarm_name, os_event_name, task_info)
            self.add_event_info(os_autosar, mod_autosar["Os"], os_event_name, task_info)

            os_ms_event_name = self.get_modeswitch_info(task_info, event_info)
            self.add_event_info(os_autosar, mod_autosar["Os"], os_ms_event_name, task_info)

            bind_item.mapped = True
        self.add_item_map(item_data, row, col, is_update_row)

        return True

    def get_bind_item_list(self, item_data: TaskMappingItemData):
        bind_item_list = []
        if item_data is None:
            return bind_item_list

        if item_data["IsMainFunction"]:
            bind_item_list.append(item_data)
            for bind_event_info in item_data["BindEvent"]:
                bind_item_data: TaskMappingItemData = bind_event_info["Parent"]
                if not bind_item_data:
                    continue
                bind_item_list.append(bind_item_data)
        else:
            runnable_name = item_data["RunnableName"]
            component_name = item_data["Component"]
            runnable_name = f"{component_name}_{runnable_name}"
            for event_info in self.swc_runnable_dict.get(runnable_name, []):
                bind_item_data: TaskMappingItemData = event_info["Parent"]
                if not bind_item_data:
                    continue
                bind_item_list.append(bind_item_data)
        return bind_item_list

    def update_swc_task_mapping_dict(self, root_item, rte_swc_instances, task_mapping_dict):
        rte_autosar = self.autosar_bsw_class.get("Rte")
        os_autosar = self.autosar_bsw_class.get("Os")
        max_position = -1
        for k, swc_instance in rte_swc_instances.items():
            if swc_instance is None:
                continue
            swc_name = k.replace("_EcuSwComposition", "")
            application_components = root_item.child_map["Application Components"]
            swc = application_components.child_map.get(swc_name)
            if swc is None:
                swc = root_item.child_map["Service Components"].child_map.get(swc_name)
                if self.update_cfg and swc is None:
                    swc_container = rte_autosar.find(f"/ActiveEcuC/Rte/{k}")
                    container_parent = swc_container.get_parent()
                    AutosarUtil.remove_container_value(container_parent.ECUC_CONTAINER_VALUE, swc_container)
                    continue
            for event_name, mapping in swc_instance.items():
                tree_item: TaskMappingTreeItem = swc.child_map.get(event_name)
                task = os_autosar.find(mapping["RteMappedToTaskRef"])
                task_name = get_short_name(task)
                if self.update_cfg and (tree_item is None or task_name is None):
                    # Remove Event Mapping
                    event_container = rte_autosar.find(f"/ActiveEcuC/Rte/{k}/{event_name}")
                    container_parent = event_container.get_parent()
                    AutosarUtil.remove_container_value(container_parent.ECUC_CONTAINER_VALUE, event_container)
                    continue
                if task_name not in task_mapping_dict:
                    task_mapping_dict[task_name] = {}
                event = tree_item.item_data
                if event["Name"] != event["OldName"]:
                    # 更新event名称
                    event_container = rte_autosar.find(f"/ActiveEcuC/Rte/{k}/{event_name}")
                    set_short_name(event_container, event["Name"])
                position = int(mapping["RtePositionInTask"])
                max_position = max(max_position, position)
                if position in task_mapping_dict[task_name]:
                    runnable_1 = task_mapping_dict[task_name][position]["RunnableName"]
                    component_1 = task_mapping_dict[task_name][position]["Component"]
                    runnable_2 = event["RunnableName"]
                    component_2 = event["Component"]
                    if runnable_1 != runnable_2:
                        log_str = (
                            f"Both the runnable: {runnable_1} of swc: {component_1} and the runnable: "
                            f"{runnable_2} of swc: {component_2} are mapped to position {position} of {task_name}! "
                            f"Please Remapping the runnable: {runnable_2} of swc: {component_2}!"
                        )
                        # TODO 转换为校验规则
                        logger.ui_error(log_str)
                else:
                    task_mapping_dict[task_name][position] = event
        return max_position

    def update_bsw_module_task_mapping_dict(self, root_item, rte_bsw_module_instances, task_mapping_dict):
        rte_autosar = self.autosar_bsw_class.get("Rte")
        os_autosar = self.autosar_bsw_class.get("Os")
        max_position = -1
        for bsw_module_name, bsw_module_instance in rte_bsw_module_instances.items():
            if bsw_module_instance is None:
                continue
            schedulable_entity = root_item.child_map["Schedulable Entities"]
            bsw_module = schedulable_entity.child_map.get(bsw_module_name)
            if bsw_module is None:
                # Remove BSW Info
                bsw_module_container = rte_autosar.find(f"/ActiveEcuC/Rte/{bsw_module_name}")
                if bsw_module_container is not None:
                    container_parent = bsw_module_container.get_parent()
                    AutosarUtil.remove_container_value(container_parent.ECUC_CONTAINER_VALUE, bsw_module_container)
                continue

            for event_name, mapping in bsw_module_instance.items():
                tree_item: TaskMappingTreeItem = bsw_module.child_map.get(event_name)
                task = os_autosar.find(mapping["RteBswMappedToTaskRef"])
                task_name = get_short_name(task)
                if self.update_cfg and (tree_item is None or task_name is None):
                    # Remove Event Mapping
                    event_container = rte_autosar.find(f"/ActiveEcuC/Rte/{bsw_module_name}/{event_name}")
                    container_parent = event_container.get_parent()
                    AutosarUtil.remove_container_value(container_parent.ECUC_CONTAINER_VALUE, event_container)
                    continue
                if task_name not in task_mapping_dict:
                    task_mapping_dict[task_name] = {}
                event = tree_item.item_data
                position = int(mapping["RteBswPositionInTask"])
                max_position = max(max_position, position)
                if position in task_mapping_dict[task_name]:
                    if task_mapping_dict[task_name][position]["RunnableName"] != event["RunnableName"]:
                        log_str = f"/ActiveEcuC/Rte/{bsw_module_name}/{event_name} {task_name}:{position}  value error!"
                        # TODO 转换为校验规则
                        logger.error(log_str)
                    elif not event["IsServiceComponent"] and event["IsMainFunction"]:
                        task_mapping_dict[task_name][position] = event
                else:
                    task_mapping_dict[task_name][position] = event
        return max_position

    def get_item_list(self):
        return self.item_list

    def get_item(self, i) -> TaskMappingTableItem:
        return self.item_list[i]

    def get_item_data(self, i) -> TaskMappingItemData:
        return self.item_list[i].item_data

    def set_item_data(self, i, item_data):
        item: TaskMappingTableItem = self.item_list[i]
        item.item_data = item_data
        item.bind_item_list = self.get_bind_item_list(item_data)

    def get_item_index(self, id):
        return self.item_map.get(id)

    def add_item_map(self, item_data: TaskMappingItemData, row, col, is_update_row=True):
        col_count = self.get_col_count()
        i = col + row * col_count
        self.item_map[item_data.id] = i
        if row not in self.bit_map:
            self.bit_map[row] = 0
        # NOTE:将1左移col位，然后取或
        self.bit_map[row] |= 1 << col

        if is_update_row:
            self.update_row_count()
            self.set_item_data(i, item_data)

    def remove_item_map(self, id):
        if id not in self.item_map:
            return
        col_count = self.get_col_count()
        i = self.item_map[id]
        self.item_map.pop(id)
        row = int(i / col_count)
        col = i - row * col_count
        self.bit_map[row] &= ~(1 << col)
        self.set_item_data(i, None)
        self.update_row_count()

    def update_row_count(self):
        row_count = self.get_row_count()
        col_count = self.get_col_count()

        max_position = -1
        for row in self.bit_map.keys():
            if not self.bit_map[row]:
                continue
            max_position = max(max_position, row)

        if max_position == -1:
            new_row_count = 1
        else:
            new_row_count = max_position + 2

        if new_row_count == row_count:
            pass
        elif new_row_count > row_count:
            self.is_row_count_changed = True
            self.item_list.extend([TaskMappingTableItem(None) for _ in range((new_row_count - row_count) * col_count)])
        else:
            self.is_row_count_changed = True
            self.item_list = self.item_list[: new_row_count * col_count]

    def update_tree_data(self):
        category_list = ["Application Components", "Service Components", "Schedulable Entities"]

        for category_name in category_list:
            swc_components = self.root_item.child_map.get(category_name)
            if not swc_components:
                continue

            for swc_name, swc_instance in swc_components.child_map.items():
                swc_instance.mapped = True
                for runnable_item in swc_instance.child_items:
                    swc_instance.mapped = swc_instance.mapped and runnable_item.mapped

        pass

    def update_port_infos_by_taskmapping(self, event_info, task_info, port_infos, asw):
        if event_info["IsMainFunction"]:
            return

        event_ref = event_info["EventRef"]
        event = asw.find(event_ref)
        if not event:
            logger.error(f"Error EventRef: {event_ref}")
            return

        event_tag = event.get_tag()
        if event_tag not in AutosarUtils.EVENT_TYPE:
            logger.error(f"Unsupported Event: {event_tag}")
            return

        start_on_event_ref = event.START_ON_EVENT_REF.valueOf_
        ports = port_infos.get(start_on_event_ref, {})
        for port_info in ports.values():
            if port_info is None:
                continue
            for port in port_info.values():
                # 只有task mapping时才会新增以下参数，ioc默认为False
                port["ioc"] = False
                port["task"] = task_info
                port["task_name"] = task_info["OsTaskName"]
                port["appl_name"] = task_info["OsApplName"]

                appl_name = self.component_appls.get(port["component"])
                if appl_name is None:
                    self.component_appls[port["component"]] = task_info["OsApplName"]
                if appl_name and appl_name != task_info["OsApplName"]:
                    log_str = (
                        f"Runnable <{port['runnable_ref'].split('/').pop()}> "
                        f"cannot map to <{task_info['OsTaskName']}> task, "
                        f"because different runnables of SWC <{port['component']}> "
                        "cannot be mapped to different partitions!"
                    )
                    # TODO 转换为校验规则
                    logger.ui_error(log_str)

    def check_if_prport_in_same_osapplication(self, ports):
        for port in ports:
            error = False
            if "port_interface_type" not in port or port["port_interface_type"] != "sr":
                continue
            # Task mapping has not been done
            if "appl_name" not in port:
                continue
            # exclude PRPort which has only P or R access point
            if not port["is_prport"] or port["m_to_n"] == "0":
                continue
            connected_port = {}
            for group_port in port["sr_port_group"]:
                if "appl_name" not in group_port:
                    continue
                if group_port["appl_name"] != port["appl_name"]:
                    error = True
                    connected_port = group_port
                    break
            if error:
                prport_name = port["port_ref"].split("/")[-1]
                prport_swc = port["component"]
                connected_port_swc = connected_port["component"]
                logger.error(
                    f"PR-Port <{prport_name}> of Swc <{prport_swc}> is connected to Swc <{connected_port_swc}> "
                    f"which is on another Os Application!"
                )
                continue

    def register_port_alarm_ref(self, alarm_name, port):
        if alarm_name not in self.port_alarm_ref_manager:
            self.port_alarm_ref_manager.update({alarm_name: {}})
        self.port_alarm_ref_manager[alarm_name].update({f'{port["component"]}_{port["port_key"]}': {}})

    def deregister_port_alarm_ref(self, alarm_name, port):
        if alarm_name not in self.port_alarm_ref_manager:
            return
        self.port_alarm_ref_manager[alarm_name].pop(f'{port["component"]}_{port["port_key"]}', None)

    def register_port_event_ref(self, event_name, port):
        if event_name not in self.port_event_ref_manager:
            self.port_event_ref_manager.update({event_name: {}})
        self.port_event_ref_manager[event_name].update({f'{port["component"]}_{port["port_key"]}': {}})

    def deregister_port_event_ref(self, event_name, port):
        if event_name not in self.port_event_ref_manager:
            return
        self.port_event_ref_manager[event_name].pop(f'{port["component"]}_{port["port_key"]}', None)

    def check_if_port_alarm_ref_exist(self, alarm_name):
        exist = False
        if alarm_name in self.port_alarm_ref_manager and self.port_alarm_ref_manager[alarm_name]:
            exist = True
        return exist

    def check_if_port_event_ref_exist(self, event_name):
        exist = False
        if event_name in self.port_event_ref_manager and self.port_event_ref_manager[event_name]:
            exist = True
        return exist

    def update_os_by_sr_queue_waitpoint(self, rte_codegen_dict, task_dict):
        os_autosar = self.autosar_bsw_class.get("Os")
        mod_autosar = self.autosar_mod_class.get("Os")
        for swc in rte_codegen_dict.values():
            for r_port in swc["rports"].values():
                if r_port["type"] != "Queued Receiver":
                    continue
                if not r_port["conn_asw_ports"]:
                    continue
                if "task" not in r_port or not r_port["task"]:
                    continue
                task_name = r_port["task"][0]
                task_info = task_dict.get(task_name, {})
                if not task_info:
                    continue
                timeout_alarm_name = f"Rte_Al_Timeout_{task_name}"
                timeout_event_name = f"Rte_Ev_Timeout_{task_name}"
                wait_point_event_name = f"Rte_Ev_WaitPoint_{task_name}"
                if r_port["timeout"] > 0:
                    self.register_port_alarm_ref(timeout_alarm_name, r_port)
                    self.register_port_event_ref(timeout_event_name, r_port)
                    self.register_port_event_ref(wait_point_event_name, r_port)
                    # self.add_alarm_info(
                    #     os_autosar, mod_autosar, timeout_alarm_name, timeout_event_name, task_info, "SR"
                    # )
                    self.add_event_info(os_autosar, mod_autosar, timeout_event_name, task_info, "SR")
                    self.add_event_info(os_autosar, mod_autosar, wait_point_event_name, task_info, "SR")
                else:
                    # the timeout in arxml has been changed, which should not happen under normal use.
                    self.deregister_port_alarm_ref(timeout_alarm_name, r_port)
                    self.deregister_port_event_ref(timeout_event_name, r_port)
                    self.deregister_port_event_ref(wait_point_event_name, r_port)
                    if not self.check_if_port_alarm_ref_exist(timeout_alarm_name):
                        self.remove_alarm_info(os_autosar, timeout_alarm_name, task_info["OsApplName"], "CS")
                    if not self.check_if_port_event_ref_exist(timeout_event_name):
                        self.remove_event_info(os_autosar, timeout_event_name, task_info, "CS")
                    if not self.check_if_port_event_ref_exist(wait_point_event_name):
                        self.remove_event_info(os_autosar, wait_point_event_name, task_info, "CS")

    def update_cs_infos(self, rte_codegen_dict, task_dict):
        for swc in rte_codegen_dict.values():
            for r_port in swc["rports"].values():
                if r_port["type"] not in ["Sync Client", "Async Client"]:
                    continue
                if "task" not in r_port:
                    continue
                connected_ports = r_port["connected_ports"]
                if not connected_ports:
                    continue
                if connected_ports["category"] not in ["1:1", "1:N"]:
                    continue
                p_port = connected_ports["ports"][0]
                self.update_cs_info(r_port, p_port, task_dict)

    def update_cs_info(self, r_port, p_port, task_dict):
        os_autosar = self.autosar_bsw_class.get("Os")
        mod_autosar = self.autosar_mod_class.get("Os")

        is_pass, task_infos = self.check_cs_port_config(r_port, task_dict)
        if not is_pass:
            return

        for t_info in task_infos:
            timeout_alarm_name, timeout_event_name, wait_point_event_name = self.get_cs_info(r_port, t_info)
            if r_port["ioc"] or "core_id" not in r_port:
                self.register_port_alarm_ref(timeout_alarm_name, r_port)
                self.register_port_event_ref(timeout_event_name, r_port)
                self.register_port_event_ref(wait_point_event_name, r_port)
                # self.add_alarm_info(os_autosar, mod_autosar, timeout_alarm_name, timeout_event_name, t_info, "CS")
                self.add_event_info(os_autosar, mod_autosar, timeout_event_name, t_info, "CS")
                self.add_event_info(os_autosar, mod_autosar, wait_point_event_name, t_info, "CS")
            else:
                if "task" not in p_port:
                    return
                self.deregister_port_alarm_ref(timeout_alarm_name, r_port)
                self.deregister_port_event_ref(timeout_event_name, r_port)
                self.deregister_port_event_ref(wait_point_event_name, r_port)
                if not self.check_if_port_alarm_ref_exist(timeout_alarm_name):
                    self.remove_alarm_info(os_autosar, timeout_alarm_name, r_port["osapplication"], "CS")
                if not self.check_if_port_event_ref_exist(timeout_event_name):
                    self.remove_event_info(os_autosar, timeout_event_name, t_info, "CS")
                if not self.check_if_port_event_ref_exist(wait_point_event_name):
                    self.remove_event_info(os_autosar, wait_point_event_name, t_info, "CS")

    def check_cs_port_config(self, r_port, task_dict):
        timeout = int(r_port["timeout"])
        if not r_port["task"]:
            return False, []
        task_infos = []
        visited = set()
        for i, task_name in enumerate(r_port["task"]):
            if not task_name or task_name in visited:
                continue
            visited.add(task_name)
            t_info = task_dict.get(task_name, {})
            if not t_info:
                continue
            task_type = t_info["OsTaskType"]
            if task_type == "BASIC" and timeout > 0:
                client_name = r_port["name"]
                log_str = (
                    f"Basic task <{task_name}> can't map runnable <{r_port['runnable'][i]}> "
                    f"containing timeout client <{client_name}>!"
                )
                # TODO 转换为校验规则
                logger.ui_error(log_str)
                return False, []
            task_infos.append(t_info)
        return True, task_infos

    def remove_unused_infos(self):
        os_autosar = self.autosar_bsw_class.get("Os")
        ecuc_autosar = self.autosar_bsw_class.get("EcuC")
        os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
        OsManager = getattr(os_process, "OsManager")

        os_alarm_set, os_event_set = OsManager.get_os_alarm_event_set(os_autosar)

        appl_name_list = OsManager.get_os_appl_list(os_autosar)
        for os_alarm_name in os_alarm_set:
            if os_alarm_name in self.os_alarm_count_dict.keys():
                continue
            OsManager.remove_os_alarm_info(os_autosar, os_alarm_name)
            # 对所有的os appl进行引用查找，命中则删除
            for os_appl_name in appl_name_list:
                OsManager.remove_appl_alarm_ref(os_autosar, os_alarm_name, os_appl_name)

        os_tasks = OsManager.get_os_task_dict(os_autosar, ecuc_autosar)
        for os_event_name in os_event_set:
            if os_event_name in self.os_event_count_dict.keys():
                continue
            OsManager.remove_os_event_info(os_autosar, os_event_name)
            # 对所有的os task进行引用查找，命中则删除
            for task_info in os_tasks.values():
                OsManager.remove_task_event_ref(os_autosar, os_event_name, task_info)

    def update_schedule_table_info(self):
        os_autosar = self.autosar_bsw_class.get("Os")
        rte_autosar = self.autosar_bsw_class.get("Rte")
        mod_autosar = self.autosar_mod_class.get("Os")
        os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
        OsManager = getattr(os_process, "OsManager")

        task_name_set = self.get_sch_tbl_used_task_name_set(os_autosar)
        self.remove_sch_tbl_used_alarm_info(os_autosar, rte_autosar, task_name_set)
        for task_info in self.table_headers:
            if task_info["OsTaskType"] != "BASIC" or "CoreId" not in task_info:
                continue
            task_name = task_info["OsTaskName"]
            if task_name in task_name_set:
                continue
            app_name = task_info["OsApplName"]
            event_list = self.get_event_list_on_task(task_info)
            mapping_validation, cur_timing_offset_dict = BasicTaskScheduleTableManager.get_timing_offset_dict(
                rte_autosar, event_list, task_name
            )
            if not mapping_validation:
                # 如果basic task上配置的event类型不合法，则不进行任何操作
                continue
            timing_offset_dict = self.task_timing_event_dict.get(task_name, None)
            if timing_offset_dict == cur_timing_offset_dict:
                continue
            self.task_timing_event_dict.update({task_name: cur_timing_offset_dict})
            # 1) 清除alarm信息
            for event_info in event_list:
                os_event_name, os_alarm_name = self.get_os_info(task_info, event_info)
                self.remove_alarm_info(os_autosar, os_alarm_name, task_info["OsApplName"])
                RteManager.set_rte_param_value(rte_autosar, event_info, "UsedOsAlarmRef", None)
                pass

            # 2）清除schedule table信息
            init_schedule_table_name = BasicTaskScheduleTableManager.get_os_init_schedule_table_name(task_name)
            OsManager.remove_os_schedule_table(os_autosar, init_schedule_table_name)
            OsManager.remove_appl_schedule_table_ref(os_autosar, init_schedule_table_name, app_name)
            main_schedule_table_name = BasicTaskScheduleTableManager.get_os_main_schedule_table_name(task_name)
            OsManager.remove_os_schedule_table(os_autosar, main_schedule_table_name)
            OsManager.remove_appl_schedule_table_ref(os_autosar, main_schedule_table_name, app_name)

            # 3) 根据schedule table配置去生成推理
            init_schedule_table_cfg, main_schedule_table_cfg = BasicTaskScheduleTableManager.get_schedule_table_cfg(
                cur_timing_offset_dict, task_name
            )
            if init_schedule_table_cfg or main_schedule_table_cfg:
                OsManager.add_os_schedule_table(os_autosar, mod_autosar, init_schedule_table_cfg, task_info)
                if init_schedule_table_cfg:
                    OsManager.add_appl_schedule_table_ref(os_autosar, mod_autosar, init_schedule_table_name, app_name)
                OsManager.add_os_schedule_table(os_autosar, mod_autosar, main_schedule_table_cfg, task_info)
                if main_schedule_table_cfg:
                    OsManager.add_appl_schedule_table_ref(os_autosar, mod_autosar, main_schedule_table_name, app_name)
                pass
            else:
                for event_info in event_list:
                    os_event_name, os_alarm_name = self.get_os_info(task_info, event_info)
                    if not os_alarm_name:
                        continue
                    # self.add_alarm_info(os_autosar, mod_autosar, os_alarm_name, os_event_name, task_info)
                    # RteManager.set_rte_param_value(
                    #     rte_autosar, event_info, "UsedOsAlarmRef", f"/ActiveEcuC/Os/{os_alarm_name}"
                    # )
                pass
            pass
        pass

    def remove_sch_tbl_used_alarm_info(self, os_autosar, rte_autosar, task_name_set):
        for task_info in self.table_headers:
            task_name = task_info["OsTaskName"]
            if task_name not in task_name_set:
                continue
            event_list = self.get_event_list_on_task(task_info)
            for event_info in event_list:
                _, os_alarm_name = self.get_os_info(task_info, event_info)
                self.remove_alarm_info(os_autosar, os_alarm_name, task_info["OsApplName"])
                RteManager.set_rte_param_value(rte_autosar, event_info, "UsedOsAlarmRef", None)

    def get_sch_tbl_used_task_name_set(self, os_autosar):
        os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
        OsManager = getattr(os_process, "OsManager")
        sch_tbl_cfg = OsManager.get_os_sch_tbl_cfgs(os_autosar)
        task_name_set = {
            exp_point.get("task_name", "").split("/")[-1]
            for v in sch_tbl_cfg.values()
            for exp_points in v.get("expiry_points", {}).values()
            for exp_point in exp_points
            if exp_point.get("task_name")
            if not v.get("is_automatic")
        }
        return task_name_set

    def get_event_list_on_task(self, task_info):
        # 获取mapping到basic task上的event列表
        event_list = []
        task_name = task_info["OsTaskName"]
        col = self.get_col_by_task_name(task_name)
        col_count = self.get_col_count()
        for row in range(self.get_row_count()):
            index = col + row * col_count
            item_data = self.get_item_data(index)
            if not item_data:
                continue
            bind_item_list = self.get_bind_item_list(item_data)
            event_list += bind_item_list

        return event_list

    def remove_schedule_table_info(self):
        os_autosar = self.autosar_bsw_class.get("Os")
        os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
        OsManager = getattr(os_process, "OsManager")
        for task_info in self.table_headers:
            if task_info["OsTaskType"] != "BASIC":
                continue
            task_name = task_info["OsTaskName"]
            app_name = task_info["OsApplName"]
            init_schedule_table_name = BasicTaskScheduleTableManager.get_os_init_schedule_table_name(task_name)
            OsManager.remove_os_schedule_table(os_autosar, init_schedule_table_name)
            OsManager.remove_appl_schedule_table_ref(os_autosar, init_schedule_table_name, app_name)
            main_schedule_table_name = BasicTaskScheduleTableManager.get_os_main_schedule_table_name(task_name)
            OsManager.remove_os_schedule_table(os_autosar, main_schedule_table_name)
            OsManager.remove_appl_schedule_table_ref(os_autosar, main_schedule_table_name, app_name)

    def deinit(self):
        self.pre_init(self.task_mapping_data, init_flags="all", update_cfg=True)
        os_autosar = self.autosar_bsw_class.get("Os")
        if os_autosar is None:
            return
        self.remove_unused_infos()
        self.remove_schedule_table_info()
        os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
        OsManager = getattr(os_process, "OsManager")
        OsManager.remove_all_ioc_info(os_autosar)
        OsManager.remove_all_spinlock_info(os_autosar)

    def get_mapped_runnable_position_info(self) -> dict:
        # key: position_idx,  val: {row: row_idx, col: col_idx}
        runnable_position_info_dict = {}
        col_count = self.get_col_count()
        for _, item_list_idx in self.item_map.items():
            row_idx = item_list_idx // col_count
            col_idx = item_list_idx % col_count
            runnable_position_info_dict[item_list_idx] = {"row": row_idx, "col": col_idx}

        return runnable_position_info_dict

    def get_runnable_data(self):
        return self.runnable_data

    def get_all_spinlocks(self, rte_codegen_dict):
        spinlock_cfgs = {}
        for swc in rte_codegen_dict.values():
            for p_port in swc["pports"].values():
                if p_port["type"] in {"Explicit Sender", "Implicit Sender"}:
                    PortManager.get_all_spinlocks_sr_nonq_p_port(p_port, spinlock_cfgs)
                elif p_port["type"] == "Server":
                    PortManager.get_all_spinlocks_cs(p_port, spinlock_cfgs)
            for r_port in swc["rports"].values():
                if r_port["type"] in {"Explicit Receiver", "Implicit Receiver"}:
                    PortManager.get_all_spinlocks_sr_nonq_r_port(r_port, spinlock_cfgs)
                elif r_port["type"] == "Queued Receiver":
                    PortManager.get_all_spinlocks_sr_queue(r_port, spinlock_cfgs)
        return spinlock_cfgs

    def update_spinlock_and_ioc_infos(self, os_autosar, mod_autosar, rte_codegen_dict):
        os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
        OsManager = getattr(os_process, "OsManager")
        OsManager.remove_all_ioc_info(os_autosar)

        all_spinlocks = self.get_all_spinlocks(rte_codegen_dict)
        for spinlock_id, appl_name_list in sorted(all_spinlocks.items()):
            OsManager.remove_spinlock_info(os_autosar, spinlock_id)
        for spinlock_id, appl_name_list in sorted(all_spinlocks.items()):
            OsManager.add_spinlock_info(os_autosar, mod_autosar, spinlock_id, appl_name_list)


    def get_all_rte_schedule_table_cfg(self, rte_codegen_dict):
        all_rte_schedule_table_cfg = []
        for swc in rte_codegen_dict.values():
            for r_port in swc["rports"].values():
                if not r_port.get("schedule_table", {}):
                    continue
                sch_tbl_info = PortManager.get_rte_schedule_table_info(r_port)
                if not sch_tbl_info:
                    continue
                all_rte_schedule_table_cfg.append(sch_tbl_info)

        return sorted(all_rte_schedule_table_cfg, key=lambda x: x["name"])


    def update_rte_schedule_table_info(self, os_autosar, mod_autosar, rte_codegen_dict):
        os_process = LoadPlugIn.load_module("Rte", "config_plug_in.bsw_process.os_process")
        OsManager = getattr(os_process, "OsManager")

        OsManager.remove_all_rte_schedule_table_info(os_autosar)
        OsManager.add_all_rte_schedule_table_info(os_autosar, mod_autosar, self.get_all_rte_schedule_table_cfg(rte_codegen_dict))
