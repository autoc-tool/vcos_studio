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

from func_module.mapping.task_mapping_core import TaskMappingInstance, TaskMappingTableItem
from func_module.mapping.task_mapping_info import RunnableInfo
from ui_adaptor.data_management import get_autosar_asw_class
from ui_adaptor.data_management import get_autosar_bsw_class
from ui_adaptor.data_management import get_autosar_system_class
from ui_adaptor.data_management import get_autosar_ib_class
from ui_adaptor.data_management import get_autosar_bswmd_class
from func_module.health_monitor import perf_record


class TaskMappingFunc:

    def __init__(self):
        self.update_instance()
        self.first_enter_vfb = True
        self.mapping_data = []

    def __get_mapping_data_info(self):
        return [
            x.item_data.data.get("RunnableName", "") if hasattr(x.item_data, "data") else ""
            for x in self.task_mapping_instance.get_item_list()
        ]

    def init_mapping_data_status(self):
        if not self.task_mapping_instance or not self.task_mapping_instance.get_item_list():
            self.update_instance()
        self.mapping_data = self.__get_mapping_data_info()

    def is_mapping_data_updated(self) -> bool:
        latest_mapping_data = self.__get_mapping_data_info()
        if len(latest_mapping_data) != len(self.mapping_data):
            return True
        for x, y in zip(latest_mapping_data, self.mapping_data):
            if x != y:
                return True
        return False

    def update_instance(self):
        self.task_mapping_instance = TaskMappingInstance.update_task_mapping_instance(
            get_autosar_asw_class(),
            get_autosar_bsw_class(),
            get_autosar_system_class(),
            get_autosar_ib_class(),
            get_autosar_bswmd_class(),
        )

    def cbk_post_update_os_ecuc(self):
        self.task_mapping_instance.post_update_os_ecuc()

    def cbk_update_ui_all(self):
        self.update_instance()

    @perf_record.log_function_stats(["RTE", "TaskMapping", "树形unmap操作"])
    def cbk_unmap_tree_items(self, param_dict):
        item_id_list = param_dict["unmap_item_id_list"]
        for item_id in item_id_list:
            if item_id not in self.task_mapping_instance.item_map:
                continue
            item_index = self.task_mapping_instance.item_map[item_id]
            table_item: TaskMappingTableItem = self.task_mapping_instance.item_list[item_index]
            item_data = table_item.item_data
            self.task_mapping_instance.unmap_runnable(item_data)

        is_row_count_changed = self.task_mapping_instance.get_row_count_status()
        self.task_mapping_instance.reset_row_count_status()
        self.task_mapping_instance.update_tree_data()
        return is_row_count_changed

    @perf_record.log_function_stats(["RTE", "TaskMapping", "表格unmap操作"])
    def cbk_unmap_table_items(self, param_dict):
        index_list = param_dict["unmap_index_list"]
        for item_index in index_list:
            table_item: TaskMappingTableItem = self.task_mapping_instance.item_list[item_index]
            item_data = table_item.item_data
            self.task_mapping_instance.unmap_runnable(item_data)
        is_row_count_changed = self.task_mapping_instance.get_row_count_status()
        self.task_mapping_instance.reset_row_count_status()
        self.task_mapping_instance.update_tree_data()
        return is_row_count_changed

    def cbk_get_item_index_by_id(self, param_dict):
        select_item_id = param_dict["select_item_id"]
        return self.task_mapping_instance.item_map.get(select_item_id)

    def cbk_get_root_item(self):
        return self.task_mapping_instance.root_item

    def cbk_get_item_list(self):
        return self.task_mapping_instance.item_list

    def cbk_get_table_headers(self):
        return self.task_mapping_instance.table_headers

    @perf_record.log_function_stats(["RTE", "TaskMapping", "拖曳进行remap操作"])
    def cbk_remap_data(self, param_dict):
        remap_item_data_list = param_dict["remap_item_data_list"]
        target_row = param_dict["target_row"]
        target_col = param_dict["target_col"]

        row_count = self.task_mapping_instance.get_row_count()
        col_count = self.task_mapping_instance.get_col_count()
        task_name = self.task_mapping_instance.table_headers[target_col]["OsTaskName"]

        # 1）数据预处理，保证id唯一性
        item_id_list = []
        item_data_list = []
        for item_data in remap_item_data_list:
            if item_data.id not in item_id_list:
                item_id_list.append(item_data.id)
                item_data_list.append(item_data)

        move_count = len(item_id_list)
        if target_row >= (row_count - 1):
            move_count = 0

        # 2）计算出[target_row,row_count)上所有mapped的runnable需要下移的位置
        if move_count > 0:
            for row in range(target_row, row_count):
                i = target_col + row * col_count
                item: TaskMappingTableItem = self.task_mapping_instance.item_list[i]
                if item.item_data:
                    break
                move_count -= 1
                if move_count <= 0:
                    break

        # 3）如果空位不够，则包括target的所有位置统一腾位置
        if move_count > 0:
            low_range = max(target_row - 1, -1)
            for row in range(row_count - 1, low_range, -1):
                if row not in range(row_count):
                    continue
                i = target_col + row * col_count
                table_item: TaskMappingTableItem = self.task_mapping_instance.item_list[i]
                item_data = table_item.item_data
                if not item_data:
                    continue
                self.task_mapping_instance.unmap_runnable(item_data)
                self.task_mapping_instance.map_runnable(item_data, task_name, row + move_count)

        # 4）最后对拖动的item进行unmap+map操作
        for i, item_data in enumerate(item_data_list):
            self.task_mapping_instance.unmap_runnable(item_data)
            self.task_mapping_instance.map_runnable(item_data, task_name, target_row + i)

        is_row_count_changed = self.task_mapping_instance.get_row_count_status()
        self.task_mapping_instance.reset_row_count_status()
        self.task_mapping_instance.update_tree_data()
        return is_row_count_changed

    def cbk_get_all_runnable_info(self) -> list:

        def __get_owner_name(is_service_component: bool, is_main_function: bool, component_name: str):
            if is_service_component:
                module = "Service Component"
            elif is_main_function:
                module = "Module"
            else:
                module = "Component"
            return f"{module} {component_name}"

        # make sure that the data has been updated when entering for the first time
        if self.first_enter_vfb:
            self.update_instance()
            self.first_enter_vfb = False
        runnable_position_info_dict = self.task_mapping_instance.get_mapped_runnable_position_info()

        runnale_detail_list = []
        # get all mapped runnable info
        task_mapping_item_list = self.task_mapping_instance.item_list
        for item_idx in range(len(task_mapping_item_list)):
            bind_item_list = getattr(task_mapping_item_list[item_idx], "bind_item_list", [])
            if not bind_item_list:
                continue
            for bind_item in bind_item_list:
                curr_runnable_info = RunnableInfo()
                runnale_detail_list.append(curr_runnable_info)
                curr_runnable_info.trigger_entity = bind_item["RunnableName"]
                curr_runnable_info.owner = __get_owner_name(
                    bind_item["IsServiceComponent"], bind_item["IsMainFunction"], bind_item["Component"]
                )
                curr_runnable_info.trigger_condition = bind_item["TriggerCondition"]
                curr_runnable_info.trigger_category = bind_item["TriggerCategory"]
                # task_info
                position = runnable_position_info_dict.get(item_idx, None)
                if not position:
                    continue
                task_info = self.task_mapping_instance.get_task_info_by_col(int(position["col"]))
                curr_runnable_info.mapped_task = task_info.get("OsTaskName", "")
                row_idx = position["row"]
                curr_runnable_info.position = f"{row_idx}"

        # get all unmapped runnable info
        for _, runnable_type_kind_dict in self.task_mapping_instance.runnable_data.items():
            for _, swc_or_module_info_dict in runnable_type_kind_dict.items():
                for _, runnable_info_dict in swc_or_module_info_dict.items():
                    if not runnable_info_dict["Parent"] or runnable_info_dict["Parent"].mapped:
                        continue
                    curr_runnable_info = RunnableInfo()
                    runnable_name = runnable_info_dict.get("RunnableName", "")
                    curr_runnable_info.trigger_entity = runnable_name
                    curr_runnable_info.owner = __get_owner_name(
                        runnable_info_dict["IsServiceComponent"],
                        runnable_info_dict["IsMainFunction"],
                        runnable_info_dict["Component"],
                    )
                    curr_runnable_info.trigger_condition = runnable_info_dict.get("TriggerCondition", "")
                    curr_runnable_info.trigger_category = runnable_info_dict.get("TriggerCategory", "")
                    runnale_detail_list.append(curr_runnable_info)

        return runnale_detail_list

    def get_runnable_data(self):
        return self.task_mapping_instance.runnable_data

    def get_task_col_in_table(self, task_name):
        col_idx = None
        col_count = self.task_mapping_instance.get_col_count()
        table_header = self.task_mapping_instance.table_headers
        for idx in range(col_count):
            if table_header[idx]["OsTaskName"] == task_name:
                col_idx = idx
                break
        return col_idx

    def cbk_get_runnable_pos_index(self, task_name, runnable_name):
        pos_idx, task_row_idx, task_col_idx = None, None, None
        if not task_name or not runnable_name:
            return pos_idx, task_row_idx, task_col_idx
        row_count = self.task_mapping_instance.get_row_count()
        col_count = self.task_mapping_instance.get_col_count()
        task_mapping_item_list = self.task_mapping_instance.item_list
        task_col_idx = self.get_task_col_in_table(task_name)
        if task_col_idx is None:
            return pos_idx, task_row_idx, task_col_idx

        for row_idx in range(row_count):
            runnable_idx = row_idx * col_count + task_col_idx
            runnable_data = getattr(task_mapping_item_list[runnable_idx], "data", {})
            if runnable_data and runnable_data.get("RunnableName", None) == runnable_name:
                pos_idx = runnable_idx
                task_row_idx = row_idx
                break

        return pos_idx, task_row_idx, task_col_idx
