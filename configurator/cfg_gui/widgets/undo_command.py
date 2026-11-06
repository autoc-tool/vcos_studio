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
import logging
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QUndoCommand
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.autosar_utils.utils import get_definition_ref
from cfg_gui.common.basic_ui_handler import BasicUIHandler
from cfg_gui.widgets.tree_view import ArgQTreeView, ArgQTreeModel
from cfg_gui.widgets.tree_view import ArgQTreeItem


class Write(QUndoCommand):

    def __init__(self, student, value):
        super().__init__()
        self.student = student
        self.item = value

    def redo(self) -> None:
        self.student.append(self.item)

    def undo(self):
        self.student.pop()


class BSWInputUndoCommand(QUndoCommand):
    """适配ArgQLineEdit,ArgQCheckBox,ArgQComboBox"""

    def __init__(
        self,
        old_data,
        new_data,
        show_data_dict,
        callback,
        overview_ui,
        basic_ui_handler,
        instance_type,
        linked_flag: bool = False,
        modify_lock_flag: bool = False,
        is_lock: bool = False,
    ):
        super().__init__()
        self.old_data = old_data  # 旧数据
        self.new_data = new_data  # 新数据
        self.show_data_dict = show_data_dict  # 保存内存和控件的路径信息
        self.callback = callback  # 中间件回调机制
        self.overview_ui = overview_ui  # overview界面
        self.instance_type = instance_type  # 控件类型,用type()获得
        self.linked_flag = linked_flag  # 是否被联动
        self.basic_ui_handler = basic_ui_handler  # 中间件container UI处理机制
        self.modify_lock_flag = modify_lock_flag  # 撤销时是否修改is_lock
        self.is_lock = is_lock  # 入栈时的锁定状态
        self.redo_flag = False  # 入栈时会运行1次redo(),此时直接return,第一次不运行

    def modify_display(self):
        # 跳转到撤销的container页面
        ecuc_path_list = list(filter(lambda x: x.strip() != "", self.show_data_dict["ecuc_path"].split("/")))
        module_cfg_view = (
            self.overview_ui.bsw_cfg_view_dict[ecuc_path_list[1]]
            if ecuc_path_list[1] in self.overview_ui.bsw_cfg_view_dict.keys()
            else None
        )
        if module_cfg_view is None:
            return
        tree_view: ArgQTreeView = module_cfg_view.findChild(ArgQTreeView)
        tree_model: ArgQTreeModel = tree_view.model()

        cur_index = self.basic_ui_handler.find_index_by_name_path(tree_model, ecuc_path_list[1:])
        tree_view.setCurrentIndex(QModelIndex())
        tree_view.clicked.emit(QModelIndex())
        tree_view.setCurrentIndex(cur_index)
        tree_view.clicked.emit(tree_view.currentIndex())

    def modify_lock(self, mode: str):
        """修改ecuc的is_lock"""
        if self.modify_lock_flag is False:
            return

        if mode == "undo":
            if self.is_lock is False:
                self.callback(
                    "bsw_editor_set_is_lock",
                    None,
                    self.show_data_dict["mod_path"],
                    self.show_data_dict["module"],
                    self.show_data_dict["ecuc_path"],
                    self.show_data_dict["tag"],
                )
            else:
                self.callback(
                    "bsw_editor_remove_is_lock",
                    None,
                    self.show_data_dict["mod_path"],
                    self.show_data_dict["module"],
                    self.show_data_dict["ecuc_path"],
                    self.show_data_dict["tag"],
                )
        else:
            if self.is_lock is False:
                self.callback(
                    "bsw_editor_remove_is_lock",
                    None,
                    self.show_data_dict["mod_path"],
                    self.show_data_dict["module"],
                    self.show_data_dict["ecuc_path"],
                    self.show_data_dict["tag"],
                )
            else:
                self.callback(
                    "bsw_editor_set_is_lock",
                    None,
                    self.show_data_dict["mod_path"],
                    self.show_data_dict["module"],
                    self.show_data_dict["ecuc_path"],
                    self.show_data_dict["tag"],
                )

    def undo(self):
        # 修改ecuc
        if "SHORT-NAME" == self.show_data_dict["tag"]:
            final_short_name, bsw_ecuc_dict = self.callback(
                "update_container_short_name_to_ecuc_arxml",
                self.old_data,
                self.show_data_dict["cfg_value"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            self.overview_ui.refresh_bsw_view_tree(self.show_data_dict["module"])
            self.callback(
                "bsw_editor_update_all_configuration_items_that_reference_this_ref",
                final_short_name,
                self.show_data_dict["cfg_value"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            # 修改ecuc_path
            new_ecuc_path = (
                self.show_data_dict["ecuc_path"].split("/" + self.show_data_dict["cfg_value"])[0]
                + "/"
                + final_short_name
            )
            self.show_data_dict["ecuc_path"] = new_ecuc_path  # 需要手动更新ecuc_path
            self.show_data_dict["cfg_value"] = final_short_name
        else:
            self.callback(
                "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                self.old_data,
                self.show_data_dict["cfg_value"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            self.show_data_dict["cfg_value"] = self.old_data

        self.modify_lock("undo")

        # 修改控件显示值
        self.modify_display()

    def redo(self):
        # 入栈时会运行1次redo(),此时直接return,第一次不运行
        if self.redo_flag is False:
            self.redo_flag = True
            return

        # 修改ecuc
        if "SHORT-NAME" == self.show_data_dict["tag"]:
            final_short_name, bsw_ecuc_dict = self.callback(
                "update_container_short_name_to_ecuc_arxml",
                self.new_data,
                self.show_data_dict["cfg_value"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            self.overview_ui.refresh_bsw_view_tree(self.show_data_dict["module"])
            self.callback(
                "bsw_editor_update_all_configuration_items_that_reference_this_ref",
                final_short_name,
                self.show_data_dict["cfg_value"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            # 修改ecuc_path
            new_ecuc_path = (
                self.show_data_dict["ecuc_path"].split("/" + self.show_data_dict["cfg_value"])[0]
                + "/"
                + final_short_name
            )
            self.show_data_dict["ecuc_path"] = new_ecuc_path  # 需要手动更新ecuc_path
            self.show_data_dict["cfg_value"] = final_short_name
        else:
            self.callback(
                "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                self.new_data,
                self.show_data_dict["cfg_value"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            self.show_data_dict["cfg_value"] = self.new_data

        self.modify_lock("redo")

        # 修改控件显示值
        self.modify_display()


class BSWQStringCommand(QUndoCommand):
    """
    适配ArgQStringWidget
    operation:
        remove、change、add
    """

    def __init__(
        self,
        item_index: int,
        list_count: int,
        item_text: str,
        operation: str,
        show_data_dict,
        callback,
        overview_ui,
        basic_ui_handler,
        linked_flag: bool = False,
    ):
        super().__init__()
        self.item_index = item_index  # 修改时item的索引
        self.list_count = list_count  # 修改时item的总个数
        self.item_text = item_text  # item文本
        self.operation = operation  # 原始修改方式,包括remove、add和change
        self.show_data_dict = show_data_dict  # 保存内存和控件的路径信息
        self.callback = callback  # 中间件回调机制
        self.overview_ui = overview_ui  # overview界面
        self.basic_ui_handler = basic_ui_handler  # 中间件container UI处理机制
        self.linked_flag = linked_flag
        self.redo_flag = False  # 入栈时会运行1次redo(),此时直接return,第一次不运行

    def modify_display(self):
        # 跳转到撤销的container页面
        ecuc_path_list = list(filter(lambda x: x.strip() != "", self.show_data_dict["ecuc_path"].split("/")))
        module_cfg_view = (
            self.overview_ui.bsw_cfg_view_dict[ecuc_path_list[1]]
            if ecuc_path_list[1] in self.overview_ui.bsw_cfg_view_dict.keys()
            else None
        )
        if module_cfg_view is None:
            return
        tree_view: ArgQTreeView = module_cfg_view.findChild(ArgQTreeView)
        tree_model: ArgQTreeModel = tree_view.model()

        cur_index = self.basic_ui_handler.find_index_by_name_path(tree_model, ecuc_path_list[1:])
        tree_view.setCurrentIndex(QModelIndex())
        tree_view.clicked.emit(QModelIndex())
        tree_view.setCurrentIndex(cur_index)
        tree_view.clicked.emit(tree_view.currentIndex())

    def undo_ecuc(self):
        # 1.ArgQStringWidget remove item的撤销
        if self.operation == "remove":
            # 1.1.有多个item时,remove item的撤销是add item
            if self.list_count > 1:
                # 添加ecuc,内部修改item顺序
                self.callback(
                    "bsw_editor_add_param_item_and_write_to_ecuc_arxml",
                    self.item_text,
                    self.show_data_dict["mod_path"],
                    self.show_data_dict["module"],
                    self.show_data_dict["ecuc_path"],
                    self.show_data_dict["tag"],
                    self.item_index,  # ecuc内部修改item顺序
                )
                self.show_data_dict["cfg_value"] = self.item_text
            # 1.2.仅有1个item时,remove item的撤销是修改item文本,改背景色
            elif self.list_count == 1:
                # 修改ecuc
                self.callback(
                    "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                    self.item_text,
                    None,
                    self.show_data_dict["mod_path"],
                    self.show_data_dict["module"],
                    self.show_data_dict["ecuc_path"],
                    self.show_data_dict["tag"],
                    self.item_index,
                )
                self.show_data_dict["cfg_value"] = self.item_text
        # 2.ArgQStringWidget add item的撤销是移除<empty>的item
        elif self.operation == "add":
            # 移除ecuc,add后的item数必定大于1
            self.callback(
                "bsw_editor_remove_param_item_and_write_to_ecuc_arxml",
                self.item_text,
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
                self.item_index,  # ecuc内部修改item顺序
            )
        # 3.ArgQStringWidget item changed的撤销是改变成旧文本
        elif self.operation == "change":
            # 修改ecuc
            self.callback(
                "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                self.item_text[0],
                self.item_text[1],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
                self.item_index,
            )
            self.show_data_dict["cfg_value"] = self.item_text[0]
        else:
            logging.info(f"Not support operation '{self.operation}'")

    def undo(self):
        # 修改ecuc
        self.undo_ecuc()

        # 修改控件显示值
        self.modify_display()

    def redo_ecuc(self):
        # 1.ArgQStringWidget remove item的反撤销
        if self.operation == "remove":
            # 1.1.有多个item时,remove item的反撤销是remove item
            if self.list_count > 1:
                # 移除ecuc
                self.callback(
                    "bsw_editor_remove_param_item_and_write_to_ecuc_arxml",
                    self.item_text,
                    self.show_data_dict["mod_path"],
                    self.show_data_dict["module"],
                    self.show_data_dict["ecuc_path"],
                    self.show_data_dict["tag"],
                    self.item_index,
                )
            # 1.2.仅有1个item时,remove item的反撤销是将item改为空,改背景色
            elif self.list_count == 1:
                # 修改ecuc为None
                self.callback(
                    "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                    None,
                    self.item_text,
                    self.show_data_dict["mod_path"],
                    self.show_data_dict["module"],
                    self.show_data_dict["ecuc_path"],
                    self.show_data_dict["tag"],
                    self.item_index,
                )
                self.show_data_dict["cfg_value"] = None
        # 2.ArgQStringWidget add item的反撤销是添加<empty>的item
        elif self.operation == "add":
            # 添加ecuc,内部修改item顺序
            self.callback(
                "bsw_editor_add_param_item_and_write_to_ecuc_arxml",
                self.item_text,
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
                self.item_index,
            )
            self.show_data_dict["cfg_value"] = self.item_text
        # 3.ArgQStringWidget item changed的反撤销是改变成新文本
        elif self.operation == "change":
            # 修改ecuc
            self.callback(
                "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                self.item_text[1],
                self.item_text[0],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
                self.item_index,
            )
            self.show_data_dict["cfg_value"] = self.item_text[1]
        else:
            logging.info(f"Not support operation '{self.operation}'")

    def redo(self):
        # 入栈时会运行1次redo(),此时直接return,第一次不运行
        if self.redo_flag is False:
            self.redo_flag = True
            return

        # 修改ecuc
        self.redo_ecuc()

        # 修改控件显示值
        self.modify_display()


class BSWQReferenceUndoCommand(QUndoCommand):
    """
    适配ArgQReferenceWidget
    operation:
        remove、change、add
    """

    def __init__(
        self,
        item_index: int,
        list_count: int,
        item_text: str,
        operation: str,
        show_data_dict,
        callback,
        overview_ui,
        basic_ui_handler,
        linked_flag: bool = False,
    ):
        super().__init__()
        self.item_index = item_index  # 修改时item的索引
        self.list_count = list_count  # 修改时item的总个数
        self.item_text = item_text  # item文本
        self.operation = operation  # 原始修改方式,包括remove、add和changed
        self.show_data_dict = show_data_dict  # 保存内存和控件的路径信息
        self.callback = callback  # 中间件回调机制
        self.overview_ui = overview_ui  # overview界面
        self.basic_ui_handler = basic_ui_handler  # 中间件container UI处理机制
        self.linked_flag = linked_flag
        self.redo_flag = False  # 入栈时会运行1次redo(),此时直接return,第一次不运行

    def modify_display(self):
        # 跳转到撤销的container页面
        ecuc_path_list = list(filter(lambda x: x.strip() != "", self.show_data_dict["ecuc_path"].split("/")))
        module_cfg_view = (
            self.overview_ui.bsw_cfg_view_dict[ecuc_path_list[1]]
            if ecuc_path_list[1] in self.overview_ui.bsw_cfg_view_dict.keys()
            else None
        )
        if module_cfg_view is None:
            return
        tree_view: ArgQTreeView = module_cfg_view.findChild(ArgQTreeView)
        tree_model: ArgQTreeModel = tree_view.model()

        cur_index = self.basic_ui_handler.find_index_by_name_path(tree_model, ecuc_path_list[1:])
        tree_view.setCurrentIndex(QModelIndex())
        tree_view.clicked.emit(QModelIndex())
        tree_view.setCurrentIndex(cur_index)
        tree_view.clicked.emit(tree_view.currentIndex())

    def undo_ecuc(self):
        # 1.ArgQReferenceWidget remove item的撤销
        if self.operation == "remove":
            # 1.1.有多个item时,remove item的撤销是add item
            if self.list_count > 1:
                # 添加ecuc,内部修改item顺序
                self.callback(
                    "bsw_editor_add_param_item_and_write_to_ecuc_arxml",
                    self.item_text,
                    self.show_data_dict["mod_path"],
                    self.show_data_dict["module"],
                    self.show_data_dict["ecuc_path"],
                    self.show_data_dict["tag"],
                    self.item_index,
                )
                self.show_data_dict["cfg_value"] = self.item_text
            # 1.2.仅有1个item时,remove item的撤销是修改item文本,改背景色
            elif self.list_count == 1:
                # 修改ecuc
                self.callback(
                    "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                    self.item_text,
                    None,
                    self.show_data_dict["mod_path"],
                    self.show_data_dict["module"],
                    self.show_data_dict["ecuc_path"],
                    self.show_data_dict["tag"],
                )
                self.show_data_dict["cfg_value"] = self.item_text
        # 2.ArgQReferenceWidget add item的撤销
        elif self.operation == "add":
            # 2.1.有多个item时,add item的撤销是remove item
            if self.list_count > 1:
                # 移除ecuc
                self.callback(
                    "bsw_editor_remove_param_item_and_write_to_ecuc_arxml",
                    self.item_text,
                    self.show_data_dict["mod_path"],
                    self.show_data_dict["module"],
                    self.show_data_dict["ecuc_path"],
                    self.show_data_dict["tag"],
                )
            # 2.2.仅有1个item时,add item的撤销是修改item文本,改背景色
            elif self.list_count == 1:
                # 修改ecuc
                self.callback(
                    "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                    None,
                    self.item_text,
                    self.show_data_dict["mod_path"],
                    self.show_data_dict["module"],
                    self.show_data_dict["ecuc_path"],
                    self.show_data_dict["tag"],
                )
                self.show_data_dict["cfg_value"] = None
        # 3.ArgQReferenceWidget item changed的撤销是改变成旧文本
        elif self.operation == "change":
            # 修改ecuc
            self.callback(
                "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                self.item_text[0],
                self.item_text[1],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            self.show_data_dict["cfg_value"] = self.item_text[0]
        else:
            logging.info(f"Not support operation '{self.operation}'")

    def undo(self):
        # 修改ecuc
        self.undo_ecuc()

        # 修改控件显示值
        self.modify_display()

    def redo_ecuc(self):
        # 1.ArgQReferenceWidget remove item的反撤销
        if self.operation == "remove":
            # 1.1.有多个item时,remove item的反撤销是remove item
            if self.list_count > 1:
                # 移除ecuc
                self.callback(
                    "bsw_editor_remove_param_item_and_write_to_ecuc_arxml",
                    self.item_text,
                    self.show_data_dict["mod_path"],
                    self.show_data_dict["module"],
                    self.show_data_dict["ecuc_path"],
                    self.show_data_dict["tag"],
                )
            # 1.2.仅有1个item时,remove item的反撤销是将item改为空,改背景色
            elif self.list_count == 1:
                # 修改ecuc
                self.callback(
                    "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                    None,
                    self.item_text,
                    self.show_data_dict["mod_path"],
                    self.show_data_dict["module"],
                    self.show_data_dict["ecuc_path"],
                    self.show_data_dict["tag"],
                )
                self.show_data_dict["cfg_value"] = None
        # 2.ArgQReferenceWidget add item的反撤销
        elif self.operation == "add":
            # 2.1.有多个item时,add item的反撤销是add item
            if self.list_count > 1:
                # 添加ecuc,内部修改item顺序
                self.callback(
                    "bsw_editor_add_param_item_and_write_to_ecuc_arxml",
                    self.item_text,
                    self.show_data_dict["mod_path"],
                    self.show_data_dict["module"],
                    self.show_data_dict["ecuc_path"],
                    self.show_data_dict["tag"],
                    self.item_index,
                )
                self.show_data_dict["cfg_value"] = self.item_text
            # 2.2.仅有1个item时,add item的反撤销是修改item文本,改背景色
            elif self.list_count == 1:
                # 修改ecuc
                self.callback(
                    "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                    self.item_text,
                    None,
                    self.show_data_dict["mod_path"],
                    self.show_data_dict["module"],
                    self.show_data_dict["ecuc_path"],
                    self.show_data_dict["tag"],
                )
                self.show_data_dict["cfg_value"] = self.item_text
        # 3.ArgQReferenceWidget item changed的反撤销是改变成新文本
        elif self.operation == "change":
            # 修改ecuc
            self.callback(
                "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                self.item_text[1],
                self.item_text[0],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            self.show_data_dict["cfg_value"] = self.item_text[1]
        else:
            logging.info(f"Not support operation '{self.operation}'")

    def redo(self):
        # 入栈时会运行1次redo(),此时直接return,第一次不运行
        if self.redo_flag is False:
            self.redo_flag = True
            return

        # 修改ecuc
        self.redo_ecuc()

        # 修改控件显示值
        self.modify_display()


class BSWOutlineUndoCommand(QUndoCommand):
    """
    适配ContainerOutlineWidget的操作撤销
    """

    def __init__(
        self,
        operation,
        data,
        instance,
        show_data_dict,
        callback,
        overview_ui,
        basic_ui_handler,
        linked_flag: bool = False,
    ):
        super().__init__()
        self.operation = operation
        self.data = data
        self.instance = instance
        self.show_data_dict = show_data_dict
        self.callback = callback
        self.overview_ui = overview_ui
        self.basic_ui_handler = basic_ui_handler
        self.linked_flag = linked_flag
        self.redo_flag = False  # 修改控件会运行1次redo(),此时直接return,第一次不运行

    def modify_display(self):
        ecuc_path_list = list(filter(lambda x: x.strip() != "", self.show_data_dict["ecuc_path"].split("/")))
        module_cfg_view = (
            self.overview_ui.bsw_cfg_view_dict[ecuc_path_list[1]]
            if ecuc_path_list[1] in self.overview_ui.bsw_cfg_view_dict.keys()
            else None
        )
        if module_cfg_view is None:
            return
        tree_view: ArgQTreeView = module_cfg_view.findChild(ArgQTreeView)
        tree_model: ArgQTreeModel = tree_view.model()

        # group container路径
        if self.operation == "short_name":
            ecuc_path_list[-1] = self.show_data_dict["mod_path"].split("/")[-1] + "(s)"
        elif self.operation == "param":
            ecuc_path_list[-1] = self.show_data_dict["mod_path"].split("/")[-2] + "(s)"

        # 用跳转刷新UI
        cur_index = self.basic_ui_handler.find_index_by_name_path(tree_model, ecuc_path_list[1:])
        tree_view.setCurrentIndex(QModelIndex())
        tree_view.clicked.emit(QModelIndex())
        tree_view.setCurrentIndex(cur_index)
        tree_view.clicked.emit(tree_view.currentIndex())

    def undo_ecuc(self):
        # 修改ecuc
        if self.operation == "short_name":
            final_short_name, bsw_ecuc_dict = self.callback(
                "update_container_short_name_to_ecuc_arxml",
                self.data[0],
                self.show_data_dict["cfg_value"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            self.callback(
                "bsw_editor_update_all_configuration_items_that_reference_this_ref",
                final_short_name,
                self.show_data_dict["cfg_value"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            new_ecuc_path = (
                self.show_data_dict["ecuc_path"].split(self.show_data_dict["cfg_value"])[0] + final_short_name
            )
            # 是否需要确认更新出对象才能调用？
            self.instance.update_show_data_dicts_ecuc_path(new_ecuc_path)
            self.show_data_dict["cfg_value"] = final_short_name
        elif self.operation == "param":
            # show_data_dict中有obj，直接更新
            self.callback(
                "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                self.data[0],
                self.data[1],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            self.show_data_dict["cfg_value"] = self.data[0]
        else:
            logging.info(f"Not support operation '{self.operation}'")

    def undo(self):
        # 修改ecuc
        self.undo_ecuc()

        # 修改显示
        self.modify_display()

    def redo_ecuc(self):
        # 修改ecuc
        if self.operation == "short_name":
            final_short_name, bsw_ecuc_dict = self.callback(
                "update_container_short_name_to_ecuc_arxml",
                self.data[1],
                self.show_data_dict["cfg_value"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            self.callback(
                "bsw_editor_update_all_configuration_items_that_reference_this_ref",
                final_short_name,
                self.show_data_dict["cfg_value"],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            new_ecuc_path = (
                self.show_data_dict["ecuc_path"].split(self.show_data_dict["cfg_value"])[0] + final_short_name
            )
            # 是否需要确认更新出对象才能调用？
            self.instance.update_show_data_dicts_ecuc_path(new_ecuc_path)
            self.show_data_dict["cfg_value"] = final_short_name
        elif self.operation == "param":
            # show_data_dict中有obj，直接更新
            self.callback(
                "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                self.data[1],
                self.data[0],
                self.show_data_dict["mod_path"],
                self.show_data_dict["module"],
                self.show_data_dict["ecuc_path"],
                self.show_data_dict["tag"],
            )
            self.show_data_dict["cfg_value"] = self.data[1]
        else:
            logging.info(f"Not support operation '{self.operation}'")

    def redo(self):
        # 入栈时会运行1次redo(),此时直接return,第一次不运行
        if self.redo_flag is False:
            self.redo_flag = True
            return

        # 修改ecuc
        self.redo_ecuc()

        # 修改显示
        self.modify_display()


class BSWContainerUndoCommand(QUndoCommand):
    """
    适配container的操作撤销
    operation:
        move、create
    """

    def __init__(
        self, module_name: str, item_data, item_path, item_row, operation: str, callback, overview_ui, main_window
    ):
        super().__init__()
        self.module_name = module_name  # 所属于的子模块名称
        self.item_data = item_data  # item的相关数据
        self.item_path = item_path  # item的UI路径
        self.item_row = item_row  # item的相关行号
        self.operation = operation  # 原始修改方式
        self.callback = callback  # 中间件回调机制
        self.overview_ui = overview_ui  # overview界面
        self.main_window = main_window  # 主窗口界面
        self.redo_flag = False  # 修改控件会运行1次redo(),此时直接return,第一次不运行

    def undo(self):
        # 获得model对象
        module_cfg_view: QWidget = self.overview_ui.bsw_cfg_view_dict[self.module_name]
        tree_view: ArgQTreeView = module_cfg_view.findChild(ArgQTreeView)
        tree_model: ArgQTreeModel = tree_view.model()

        # 1.拖动的撤销是相反地拖动item
        if self.operation == "move":
            # 获取index,然后与拖动相反地换行
            row = self.item_row[0]
            cur_row = self.item_row[1]
            # item_path是被拖动item的父item的UI路径
            parent_item_path = self.item_path
            parent_index: QModelIndex = BasicUIHandler.find_index_by_name_path(
                tree_model, parent_item_path.split("/")[2:]
            )
            tree_model.moveRow(parent_index, cur_row, parent_index, row)
        # 2.创建的撤销是移除item
        elif self.operation == "create":
            child_item_path = self.item_path[1]
            # 清除当前item的报错信息
            cbk_param = {}
            cbk_param["path_list"] = [child_item_path]
            self.callback(
                "validation_remove_container",
                cbk_param,
                result_callback=self.main_window.validation_ui.validation_model.update_model_data,
            )
            # 移除item
            child_item_index: QModelIndex = BasicUIHandler.find_index_by_name_path(
                tree_model, child_item_path.split("/")[2:]
            )
            tree_model.removeRow(child_item_index.row(), child_item_index.parent())
        else:
            logging.info(f"Not support operation '{self.operation}'")

    def redo(self):
        # 入栈时会运行1次redo(),此时直接return,第一次不运行
        if self.redo_flag is False:
            self.redo_flag = True
            return

        # 获得model对象
        module_cfg_view: QWidget = self.overview_ui.bsw_cfg_view_dict[self.module_name]
        tree_view: ArgQTreeView = module_cfg_view.findChild(ArgQTreeView)
        tree_model: ArgQTreeModel = tree_view.model()

        # 1.拖动的反撤销是相同地拖动item
        if self.operation == "move":
            row = self.item_row[0]
            cur_row = self.item_row[1]
            parent_item_path = self.item_path
            parent_index: QModelIndex = BasicUIHandler.find_index_by_name_path(
                tree_model, parent_item_path.split("/")[2:]
            )
            tree_model.moveRow(parent_index, row, parent_index, cur_row)
        # 2.创建的反撤销是创建item
        elif self.operation == "create":
            # 获取item
            item_path = self.item_path[0]
            item_index: QModelIndex = BasicUIHandler.find_index_by_name_path(tree_model, item_path.split("/")[2:])
            item: ArgQTreeItem = item_index.internalPointer()

            # 获取创建item所需的数据
            base_name = self.item_data[0]
            guess_name = self.item_data[1]

            # 2.1.对应在group容器下创建item的情况
            if len(self.item_data) == 2:
                conf_def = item.get_data()
                data = item.get_parent().get_data()
            # 2.2.对应在非group容器下创建item的情况
            else:
                data = item.get_data()
                def_ref = get_definition_ref(data)
                def_ref = def_ref + f"/{base_name}"
                ecuc_def = self.item_data[2]
                conf_def = ecuc_def.find(def_ref)

            # 创建item
            child_data = AutosarUtil.create_container_value(base_name, conf_def, data, guess_name)
            tree_model.append_item(child_data, item_index)
        else:
            logging.info(f"Not support operation '{self.operation}'")
