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
from func_module.import_file.excel_parser import ExcelParser
from func_module.health_monitor.perf_record import log_function_stats
from func_module.mapping.task_mapping_core import TaskMappingInstance
from cmd_adaptor.data_management import get_autosar_asw_class
from cmd_adaptor.data_management import get_autosar_bsw_class
from cmd_adaptor.data_management import get_autosar_system_class
from cmd_adaptor.data_management import get_autosar_ib_class
from cmd_adaptor.data_management import get_autosar_bswmd_class
from cmd_adaptor.func_logic_layer.load_save_project import LoadAndSaveProject
from cmd_adaptor.cmd_interaction.cmd_logger import logger


class TaskMappingCmdFunc:
    log_list = []
    CATEGORY_LIST = ["Application Components", "Service Components", "Schedulable Entities"]

    @classmethod
    def execute_auto_task_mapping_by_param(
        cls, project_path, task_name, swc_name, runnable_name, position: int = -1, event_name: str = ""
    ) -> bool:
        """excute the task mapping by the input excel file

        Args:
            task_name (str): the task name which to be mapped.
            swc_name (str): the swc name which the runnable belongs to.
            runnable_name (str): the runnable or main function name.
            position (int): the target position of task,
                            (-1:default to the last unused position, > 0: the target position).
            event_name (str): If the runnable_name has multiple different runnables, this parameter must be specified.

        Returns:
            bool: True(excute sucessfully), False:(excute failed)
        """
        logger.info(f"start load project: {project_path} ...")
        LoadAndSaveProject.load_project(project_path)
        logger.info("start auto task mapping by param ...")

        mapping_ret = cls.auto_task_mapping_by_param(task_name, swc_name, runnable_name, position, event_name)

        logger.info("start saving arxml ...")
        LoadAndSaveProject.task_mapping_save_project()
        logger.info("finish saving arxml ...")
        return mapping_ret

    @classmethod
    def execute_auto_task_mapping_by_file(cls, project_path, excel_path) -> bool:
        logger.info(f"start load project: {project_path} ...")
        LoadAndSaveProject.load_project(project_path)

        cls.auto_task_mapping_by_file(excel_path)

        logger.info("start saving arxml ...")
        LoadAndSaveProject.task_mapping_save_project()
        logger.info("finish saving arxml ...")
        return True

    @classmethod
    @log_function_stats(["RTE", "TaskMapping", "命令行自动TaskMapping", "依照excel文件进行taskmapping操作"])
    def auto_task_mapping_by_file(cls, excel_path) -> bool:
        logger.info(f"start parse excel file to item list: {excel_path} ...")
        ExcelParser.excel_2_taskmapping_item_list(excel_path)
        logger.info("start auto task mapping by item list ...")
        return TaskMappingCmdFunc.auto_task_mapping_by_item_list(ExcelParser.taskmapping_item_list)

    @classmethod
    def update_task_mapping_instance(cls):
        return TaskMappingInstance.update_task_mapping_instance(
            get_autosar_asw_class(),
            get_autosar_bsw_class(),
            get_autosar_system_class(),
            get_autosar_ib_class(),
            get_autosar_bswmd_class(),
        )

    @classmethod
    def get_task_mapping_instance(cls):
        task_mapping_instance = TaskMappingInstance.get_task_mapping_instance()
        if not task_mapping_instance:
            task_mapping_instance = cls.update_task_mapping_instance()
        return task_mapping_instance

    @classmethod
    def log_all(cls, log_level: str, log_str: str):
        if log_level == "error":
            logger.error(log_str)
        elif log_level == "info":
            logger.info(log_str)
        elif log_level == "warning":
            logger.warning(log_str)

        cls.log_list.append(log_str)

        pass

    @classmethod
    def get_runnable_item(cls, target_swc_name, runnable_name, root_item, event_name: str = ""):
        target_runnable = None
        is_swc_find = False
        log_list = []

        candidate_runnable_list = []
        is_application_category = False

        for category_name in cls.CATEGORY_LIST:
            swc_components = root_item.child_map.get(category_name)
            if not swc_components:
                continue

            for curr_swc_name, swc_instance in swc_components.child_map.items():
                if curr_swc_name != target_swc_name:
                    continue
                for runnable_item in swc_instance.child_items:
                    if runnable_name != runnable_item.data["RunnableName"]:
                        continue
                    candidate_runnable_list.append(runnable_item)
                    if "Application Components" == category_name:
                        is_application_category = True

        # 多个重名 runnbale 必须通过 event_name 来确定
        if len(candidate_runnable_list) == 1:
            is_swc_find, target_runnable = True, candidate_runnable_list[0]
        elif len(candidate_runnable_list) > 1:
            if is_application_category:
                is_swc_find, target_runnable = True, candidate_runnable_list[0]
            elif not event_name:
                cls.log_all(
                    "error",
                    f"the runnable_name:{runnable_name} has multiple different runnables, "
                    "event_name must be specified!",
                )
            else:
                for runnable in candidate_runnable_list:
                    if getattr(runnable, "data", []).get("Name", "") == event_name:
                        is_swc_find, target_runnable = True, runnable
                        break

        return is_swc_find, target_runnable, log_list

    @classmethod
    def get_runnable_item_by_runnable(cls, runnable_name, root_item):
        target_runnable = None

        for category_name in cls.CATEGORY_LIST:
            swc_components = root_item.child_map.get(category_name)
            if not swc_components:
                continue

            for swc_name, swc_instance in swc_components.child_map.items():
                for runnable_item in swc_instance.child_items:
                    # 通过mapped状态来实现Service Components和Schedulable Entities中重名runnable的过滤
                    if runnable_item.mapped:
                        continue
                    if runnable_name != runnable_item.data["RunnableName"]:
                        continue
                    if not target_runnable:
                        target_runnable = runnable_item
                        break
                if target_runnable:
                    break

            if target_runnable:
                break

        return target_runnable

    @classmethod
    def clear_mapping_info_of_task(cls, task_name):
        task_mapping_instance = cls.get_task_mapping_instance()

        col_count = task_mapping_instance.get_col_count()
        col = task_mapping_instance.get_col_by_task_name(task_name)
        if col is None:
            logger.error(f"clear the mapped runnable on {task_name} failed")
            return False

        for row in range(task_mapping_instance.get_row_count()):
            # 每一次unmap都可能造成table变化，所以要及时加上校验判断
            if row not in range(task_mapping_instance.get_row_count()):
                continue
            i = col + row * col_count
            table_item = task_mapping_instance.get_item(i)
            if not table_item or not table_item.item_data:
                continue

            item_data = table_item.item_data
            task_mapping_instance.unmap_runnable(item_data)

        logger.info(f"clear the mapped runnables on {task_name} successfully")
        return True

    @classmethod
    @log_function_stats(["RTE", "TaskMapping", "命令行自动TaskMapping", "对参数组进行taskmapping操作"])
    def auto_task_mapping_by_param(cls, task_name, swc_name, runnable_name, position: int = -1, event_name: str = ""):
        if (not task_name) or (not swc_name) or (not runnable_name) or (position < -1):
            cls.log_all(
                "error",
                f"task_name:{task_name}, swc_name:{swc_name}, runnable_name:{runnable_name}, "
                f"position:{position} param error",
            )
            return False

        task_mapping_instance = cls.get_task_mapping_instance()
        # 1）首先要从tree中找到具体的runnable
        is_swc_find, runnable_item, _ = cls.get_runnable_item(
            swc_name, runnable_name, task_mapping_instance.root_item, event_name
        )
        if not is_swc_find:
            cls.log_all("error", f"find swc_name:{swc_name} failed!")
            return False

        if not runnable_item:
            cls.log_all("error", f"find runnable_item {swc_name}.{runnable_name} failed!")
            return False

        target_col = task_mapping_instance.get_col_by_task_name(task_name)
        if target_col is None:
            cls.log_all("error", f"find task_name {task_name} failed!")
            return False

        # 2) 判断目标位置是否已经map上runnable
        col_count = task_mapping_instance.get_col_count()
        row_count = task_mapping_instance.get_row_count()
        if position >= row_count:
            cls.log_all(
                "error", f"runnable_name({runnable_name}) position({position}) exceeds table row count({row_count})!"
            )
            cls.log_all("error", "Please use -1 to indicate the last unused position in the table.")
            return False

        is_position_mapped = False
        if position >= 0:
            position_index = target_col + position * col_count
            position_item_data = task_mapping_instance.get_item_data(position_index)
            if position_item_data and position_item_data.mapped:
                is_position_mapped = True

        # 3) 如果position选择最大值则需要查找到位置，若position上已经映射有runnable则需要腾位置
        max_unused_position = -1
        if position == -1 or is_position_mapped:
            low_range = max(position - 1, -1)
            for row in range(task_mapping_instance.get_row_count() - 1, low_range, -1):
                if row not in range(task_mapping_instance.get_row_count()):
                    continue
                i = target_col + row * col_count
                table_item = task_mapping_instance.item_list[i]
                if not table_item or not table_item.item_data:
                    continue
                item_data = table_item.item_data
                if item_data.id not in task_mapping_instance.item_map:
                    continue

                if position == -1:
                    max_unused_position = row + 1
                    break
                else:
                    task_mapping_instance.unmap_runnable(item_data)
                    task_mapping_instance.map_runnable(item_data, task_name, row + 1)

        correct_position = position
        if position == -1:
            correct_position = max(max_unused_position, 0)

        # 4) 最后统一进行unmap+map处理
        item_data = runnable_item.item_data
        task_mapping_instance.unmap_runnable(item_data)
        task_mapping_instance.map_runnable(item_data, task_name, correct_position)

        # 5）根据当前最新结果执行一遍推理更新
        task_mapping_instance.post_update_os_ecuc()
        cls.log_all(
            "info", f"create a taskmapping: {swc_name}.{runnable_name} -> {task_name}:{correct_position} succeed!"
        )
        return True

    @classmethod
    def auto_task_mapping_by_item_list(cls, taskmapping_item_list: list):
        ret = True
        cls.log_list = []
        task_mapping_instance = cls.get_task_mapping_instance()
        # 1) 对所有runnable进行unmap操作
        table_size = len(task_mapping_instance.item_list)
        for i in range(table_size - 1, -1, -1):
            if i not in range(len(task_mapping_instance.item_list)):
                continue

            table_item = task_mapping_instance.get_item(i)
            if not table_item or not table_item.item_data:
                continue

            item_data = table_item.item_data
            task_mapping_instance.unmap_runnable(item_data)

        # 2）开始进行map操作
        for taskmapping_item in taskmapping_item_list:
            task_name = taskmapping_item.task_name
            runnable_name = taskmapping_item.runnable_name
            position = taskmapping_item.position
            if not task_name or not runnable_name or not isinstance(position, int):
                cls.log_all(
                    "error", f"task_name:{task_name}, runnable_name:{runnable_name}, position:{position} param error"
                )
                ret = False
                continue
            if position < 0:
                cls.log_all("error", f"position:{position} range error")
                ret = False
                continue
            col = task_mapping_instance.get_col_by_task_name(task_name)
            if col is None:
                cls.log_all("error", f"find task_name:{task_name} failed")
                ret = False
                continue

            runnable_item = cls.get_runnable_item_by_runnable(runnable_name, task_mapping_instance.root_item)
            if not runnable_item:
                cls.log_all("error", f"find runnable_name:{runnable_name} failed")
                ret = False
                continue

            item_data = runnable_item.item_data
            bind_item_list = task_mapping_instance.get_bind_item_list(item_data)
            for j, bind_item in enumerate(bind_item_list):
                category = None
                if not bind_item.data["IsServiceComponent"] and not bind_item.data["IsMainFunction"]:
                    category = "Application Components"
                    pass
                elif bind_item.data["IsServiceComponent"] and bind_item.data["IsMainFunction"]:
                    category = "Service Components"
                    pass
                elif not bind_item.data["IsServiceComponent"] and bind_item.data["IsMainFunction"]:
                    category = "Schedulable Entities"
                    pass
                swc_name = bind_item.data["Component"]
                task_mapping_instance.map_runnable(bind_item, task_name, position)
                cls.log_all(
                    "info",
                    f"create a taskmapping: {category}.{swc_name}.{runnable_name} -> {task_name}:{position} succeed!",
                )

        return ret

    @classmethod
    def get_runnable_data(cls):
        task_mapping_instance = cls.get_task_mapping_instance()
        return task_mapping_instance.runnable_data
