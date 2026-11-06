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
import gc
import os
import pickle
import ctypes
from pathlib import Path
from collections import defaultdict
from typing import Iterable, List
from PySide6 import QtGui
from PySide6.QtCore import Qt, QMimeData, QModelIndex, QAbstractItemModel
from PySide6.QtGui import QCursor, QIcon, QAction
from PySide6.QtWidgets import (
    QWidget,
    QMenu,
    QTreeView,
    QMessageBox,
    QApplication,
    QScrollArea,
    QFileDialog,
    QLayout,
    QStyle,
)
from basic_func_module.autosar_utils import utils
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.autosar_utils.autosar_ecuc import AutosarEcuc
from cfg_gui.widgets.widget import ArgQWidget
from cfg_gui.widgets.container_outline import ContainerOutlineWidget
from cfg_gui.widgets.table_widget import ArgTableWidget
from cfg_gui.export_file.restore_derived_ui import RestoreDerivedUI
from ui_adaptor.ui_interaction.ui_logger import logger
from func_module.module_management.container_rule.bsw_container_rule import RULE_DICT, base_rule_instance
import importlib
from weakref import ReferenceType
from cfg_gui.validation.validation_ui import ValidationErrorWindow


class ArgQTreeItem:

    def __init__(
        self,
        data,
        icon=":/container.svg",
        path="",
        alias=None,
        widget_type=None,
        is_secondary_custom_node=False,
        is_recursion=True,
    ):
        self._icon = icon  # 节点对应图标
        self._origin_icon = icon  # 原始图标，应对校验错误的图标显示
        self._data = data  # 节点对应数据
        self._parent = None  # 父节点
        self._children = []  # 子节点集合
        self._row = -1  # 此item位于父节点第几个
        self._path = path  # 节点对应路径
        self._alias = alias  # 节点别名，用于二级菜单
        self._widget_type = widget_type  # 点击该节点时使用的控件
        self._is_recursion = is_recursion
        self._is_secondary_custom_node = is_secondary_custom_node
        self._validation_result_list = []

    @property
    def _data(self):
        return self.__data() if isinstance(self.__data, ReferenceType) else self.__data

    @_data.setter
    def _data(self, data):
        self.__data = data if (not data or isinstance(data, str)) else ReferenceType(data)

    def append_child(self, child):
        self.add_child(child)
        self._children.append(child)

    def insert_child(self, child, index=0):
        self.add_child(child)
        self._children.insert(index, child)
        for i, child in enumerate(self._children):
            child.set_row(i)

    def add_child(self, child: "ArgQTreeItem"):
        child._parent = self
        parent_path = self.get_path()
        if parent_path == "#":
            parent_path = self.get_parent().get_path()
        if child._path == "":
            data = child.get_alias() or child.get_data()
            if data is not None:
                if isinstance(data, str):
                    child._path = "/".join([parent_path, data])
                else:
                    child._path = "/".join([parent_path, utils.get_short_name(data)])
        child._row = len(self._children)

    def get_icon(self):
        return self._icon

    def recovery_icon(self):
        self._icon = self._origin_icon

    def set_icon(self, icon):
        self._icon = icon

    def get_data(self):
        return self._data

    def get_children(self) -> List["ArgQTreeItem"]:
        return self._children

    def get_child(self, row) -> "ArgQTreeItem":
        if row >= 0 and row < len(self._children):
            return self._children[row]
        else:
            return None

    def get_path(self):
        return self._path

    def get_parent(self) -> "ArgQTreeItem":
        return self._parent

    def get_row(self):
        return self._row

    def set_row(self, row):
        self._row = row

    def child_count(self):
        return len(self._children)

    def column_count(self):
        return 2

    def get_alias(self):
        return self._alias

    def get_widget_type(self):
        return self._widget_type

    def get_is_recursion(self):
        return self._is_recursion

    def get_is_secondary_custom_node(self):
        return self._is_secondary_custom_node

    def update_validation_result(self, validation_result_list):
        self._validation_result_list = validation_result_list

    def get_validation_result(self):
        return self._validation_result_list


class ArgQTreeModel(QAbstractItemModel):

    def __init__(
        self,
        instance_bswmd_mapping_dict: dict,
        bswmd_autosar_obj_dict: dict,
        ecuc_cfg_obj_dict: dict,
        parent=None,
        overview_ui=None,
        is_secondary=False,
        secondary_menu_cfg_of_tab=None,
    ):
        super().__init__(parent)
        self.instance_bswmd_mapping_dict = instance_bswmd_mapping_dict
        self.bswmd_autosar_obj_dict = bswmd_autosar_obj_dict
        self.ecuc_cfg_obj_dict = ecuc_cfg_obj_dict
        self.group_item_dict = defaultdict(dict)
        self.child_item_dict = {}
        self.defs_dict = {}
        self.defs_set = {}
        self.root_item = ArgQTreeItem("root", path="/ActiveEcuC")  # 最顶层根节点
        self.is_secondary = is_secondary
        self.secondary_menu_cfg_of_tab = secondary_menu_cfg_of_tab
        self.ecuc_def_prefix_dict = self.get_module_def_prefix(bswmd_autosar_obj_dict)
        self.ecuc_def_prefix = list(self.ecuc_def_prefix_dict.values())[-1] or ""
        if self.is_secondary is True:
            self.init_model_data_secondary()
        else:
            self.init_model_data()
        self.callback = None
        self.overview_ui = overview_ui

    def set_callback(self, callback):
        self.callback = callback

    # 显示index的节点数据
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        item: ArgQTreeItem = index.internalPointer()
        # 显示节点图标
        if item.get_icon() and role == Qt.ItemDataRole.DecorationRole and index.column() == 0:
            return QIcon(item.get_icon())
        # 显示节点数据
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.ToolTipRole:
            if index.column() == 0:
                short_name = item.get_alias()
                if short_name is None:
                    data = item.get_data()
                    short_name = utils.get_short_name(data)
                    if item.get_path() == "#":
                        return f"{short_name}(s)"
                return short_name
            if index.column() == 1 and not self.is_secondary:
                data = item.get_data()
                if item.get_path() == "#" or self.root_item == item.get_parent():
                    return None
                path_marks = AutosarEcuc.get_path_marks(data)
                if path_marks:
                    return ", ".join(path_marks)
                else:
                    return f"No mark, default in {self.get_default_file_path()}"

        return None

    # 指示index的节点的启用和允许选择标志的组合
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        item: ArgQTreeItem = index.internalPointer()
        if AutosarUtil.is_visible(item._data):
            if item.get_path() == "#":
                return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            else:
                return (
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsDragEnabled
                    | Qt.ItemFlag.ItemIsDropEnabled
                )
        else:
            return Qt.ItemFlag.NoItemFlags

    # 在parent节点下, 第row行, 第column列位置上创建索引
    def index(self, row: int, column: int, parent: QModelIndex = ...) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()
        child_item = parent_item.get_child(row)
        if child_item:
            return self.createIndex(row, column, child_item)  # 展开树形, 为子节点建立索引
        else:
            return QModelIndex()

    def parent(self, child=None):
        if child is None:
            # 返回parent
            return super().parent()
        if not child.isValid():
            return QModelIndex()
        child_item = child.internalPointer()
        parent_item = child_item.get_parent()
        # 顶层节点, 直接返回空索引
        if parent_item == self.root_item:
            return QModelIndex()
        # 为父节点建立索引
        return self.createIndex(parent_item.get_row(), 0, parent_item)

    def append_item(self, data, parent: QModelIndex, sec_menu_name=None) -> bool:

        self.beginInsertRows(parent, self.rowCount(parent), self.rowCount(parent))
        parent_item: ArgQTreeItem = parent.internalPointer()
        item = ArgQTreeItem(data)
        item.set_row(len(parent_item._children))
        row = self.container_create_trigger(item, sec_menu_name)
        if isinstance(row, int) and row >= 0:
            parent_item.insert_child(item, row)
        else:
            parent_item.append_child(item)
        module_item = self.root_item.get_child(0)
        path = item.get_path()
        item_relpath = path.replace(module_item.get_path(), "")
        n = item_relpath.count("/") + 1
        containers = getattr(data, "SUB_CONTAINERS", getattr(data, "CONTAINERS", None))
        self.add_containers(item, containers, n)
        self.endInsertRows()
        return True

    def moveRow(
        self, sourceParent: QModelIndex, sourceRow: int, destinationParent: QModelIndex, destinationRow: int
    ) -> bool:
        return self.moveRows(sourceParent, sourceRow, 1, destinationParent, destinationRow)

    def moveRows(
        self, sourceParent: QModelIndex, sourceRow: int, count: int, destinationParent: QModelIndex, destinationRow: int
    ) -> bool:
        if sourceParent != destinationParent:
            return False
        if sourceRow <= destinationRow < sourceRow + count:
            return False
        parent_item: ArgQTreeItem = sourceParent.internalPointer()
        children = parent_item.get_children()
        self.layoutAboutToBeChanged.emit()
        moved_items = self.move_rows(sourceRow, count, destinationRow, children)
        values = self.get_ecuc_values(children)
        children_index_dict = self.get_children_index_in_values(children, values)
        self.container_move_trigger(moved_items)
        self.layoutChanged.emit()
        self.sort_children_index(values, children_index_dict)
        return True

    def sort_children_index(self, values, children_index_dict: dict):
        children_index_list = list(children_index_dict)
        for i, index in enumerate(sorted(children_index_list)):
            values[index] = children_index_dict[children_index_list[i]]

    def get_children_index_in_values(self, children, values):
        children_index_dict = {}
        for i, child in enumerate(children):
            child.set_row(i)
            data = child.get_data()
            if data not in values:
                continue
            index = values.index(data)
            children_index_dict[index] = data
        return children_index_dict

    def get_ecuc_values(self, children):
        values = []
        for child in children:
            if child.get_path() == "#":
                continue
            data = child.get_data()
            parent = data.get_parent()
            values = getattr(parent, "ECUC_CONTAINER_VALUE", [])
            break
        return values

    def move_rows(self, source_row, count, destination_row, children: list):
        source_first = source_row
        source_last = source_row + count
        if source_row <= destination_row < source_last:
            return []
        moved_items = children[source_first:source_last]
        # 从原始列表中删除要移动的子项
        del children[source_first:source_last]
        # 根据目标位置的不同，选择将子项插入到前面或后面
        if destination_row > source_last:
            # 插入到目标位置后面
            destination_row -= count
            children[destination_row + 1 : destination_row + 1] = moved_items
        else:
            # 插入到目标位置前面
            children[destination_row:destination_row] = moved_items
        return moved_items

    def removeRows(self, row: int, count: int, parent: QModelIndex) -> bool:

        if row < 0 or count < 1 or row + count > self.rowCount(parent):
            return False

        self.beginRemoveRows(parent, row, row + count - 1)
        parent_item: ArgQTreeItem = parent.internalPointer()
        children = parent_item.get_children()
        item_list = []
        for i in reversed(range(row, row + count)):
            item = parent_item.get_child(i)
            if item.get_path() == "#":
                continue
            prefix = item.get_path()
            keys_to_remove = [k for k in self.child_item_dict if k.startswith(prefix)]
            for k in keys_to_remove:
                self.child_item_dict.pop(k, None)
                self.group_item_dict.pop(k, None)
            item_list.append(item)
            data = item.get_data()
            parent_data = data.get_parent()
            parent_data.ECUC_CONTAINER_VALUE.remove(data)
            path = data.get_path()
            root_id = id(data.get_root())
            AutosarUtil.ar_paths.get(path, {}).pop(root_id, None)
            children.pop(i)
        self.container_delete_trigger(item_list)
        for i in range(row, len(children)):
            children[i].set_row(i)
        self.endRemoveRows()
        return True

    # 获取索引parent下有多少行
    def rowCount(self, parent: QModelIndex = ...) -> int:
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()
        return parent_item.child_count()  # 返回父节点下子节点数目

    # 返回索引parent下有多少列
    def columnCount(self, parent: QModelIndex = ...) -> int:
        return self.root_item.column_count()

    def mimeData(self, indexes: Iterable[QModelIndex]) -> QMimeData:
        mimedata = QMimeData()
        indexes = list(indexes)
        if len(indexes) == 0:
            return mimedata
        index = indexes[-1]
        item: ArgQTreeItem = index.internalPointer()
        parent = item.get_parent()
        row = item.get_row()
        mimedata.setData("items", pickle.dumps({"parent": id(parent), "row": row}))
        return mimedata

    def mimeTypes(self) -> List[str]:
        return ["items"]

    def dropMimeData(
        self, mimedata: QMimeData, action: Qt.DropAction, row: int, column: int, parent: QModelIndex
    ) -> bool:
        if action != Qt.DropAction.MoveAction:
            return False
        if "items" not in mimedata.formats():
            return False
        data = pickle.loads(mimedata.data("items").data())
        data_parent: ArgQTreeItem = ctypes.cast(data["parent"], ctypes.py_object).value
        parent_item = parent.internalPointer()
        if parent_item and data_parent == parent_item.get_parent():
            row = data["row"]
            cur_row = parent.row()
            parent = parent.parent()
            # 在同一个父容器下,从row挪到cur_row
            res = self.moveRow(parent, row, parent, cur_row)
            return res
        else:
            msg_box = QMessageBox(QMessageBox.Icon.Warning, "Warning", "不允许拖动到该位置！")
            msg_box.exec()
            return False

    def supportedDragActions(self):
        return Qt.DropAction.MoveAction

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction

    def update_defs_dict_for_secondary(self, mod_path, is_recursion=True):
        if is_recursion:
            self.defs_dict = {k: v for k, v in self.defs_dict.items() if mod_path in k}
        else:
            self.defs_dict = {k: v for k, v in self.defs_dict.items() if k == mod_path}

    def find_obj_by_mod_path(self, containers, mod_path, obj, def_perfix=""):
        if not mod_path:
            return
        if containers is None:
            return
        for container_value in containers.ECUC_CONTAINER_VALUE:
            definition_ref = utils.get_definition_ref(container_value)
            definition_ref = definition_ref
            if definition_ref == mod_path:
                obj.append(container_value)
                return

            self.find_obj_by_mod_path(container_value.SUB_CONTAINERS, mod_path, obj)

    def create_tree(self, node, parent_item: ArgQTreeItem, depth=0, icon=":/container.svg"):
        item_name = node.get("item_name")
        module_name = node.get("module_name")
        is_container_groups = node.get("is_container_groups", False)
        widget_type = node.get("widget_type")
        is_recursion = node.get("is_recursion", True)
        filter_condition = node.get("filter_condition")
        child_widget_type = node.get("child_widget_type")
        if module_name not in self.ecuc_cfg_obj_dict:
            return
        containers = self.ecuc_cfg_obj_dict[module_name].CONTAINERS
        if node.get("mod_path"):
            # 根据 mod_path，转换为ecuc path，获得ecuc_obj
            obj = []
            def_perfix = self.ecuc_def_prefix_dict.get(module_name, "")
            self.find_obj_by_mod_path(containers, node.get("mod_path"), obj, def_perfix)
            # 特殊处理 mod_path 非空的情况，可能会创建新的对象或使用已找到的对象
            if obj:
                if is_container_groups:
                    self.parse_param_conf_container_def(self.bswmd_autosar_obj_dict[module_name].CONTAINERS, 1)
                    self.update_defs_dict_for_secondary(node.get("mod_path"), is_recursion)
                    parent_obj = obj[0].get_parent().get_parent()
                    tag = parent_obj.get_tag()
                    if tag in ["ECUC-MODULE-DEF", "ECUC-MODULE-CONFIGURATION-VALUES"]:
                        self.add_containers(
                            parent_item,
                            parent_obj.CONTAINERS,
                            depth,
                            child_widget_type=child_widget_type,
                            filter_condition=filter_condition,
                        )
                    else:
                        self.add_containers(
                            parent_item,
                            parent_obj.SUB_CONTAINERS,
                            depth,
                            child_widget_type=child_widget_type,
                            filter_condition=filter_condition,
                        )
                else:
                    module_item = ArgQTreeItem(
                        obj[0], icon=icon, alias=item_name, widget_type=widget_type, is_secondary_custom_node=True
                    )
                    parent_item.append_child(module_item)
            else:
                self.parse_param_conf_container_def(self.bswmd_autosar_obj_dict[module_name].CONTAINERS, 1)
                self.update_defs_dict_for_secondary(node.get("mod_path"), is_recursion)
                module_item = ArgQTreeItem(
                    self.defs_dict[node.get("mod_path")]["def"],
                    icon=icon,
                    path="#",
                    alias=item_name,
                    widget_type=widget_type,
                    is_secondary_custom_node=True,
                )
                parent_item.append_child(module_item)
        else:
            module_item = ArgQTreeItem(
                containers.get_parent(),
                icon=icon,
                alias=item_name,
                widget_type=widget_type,
                is_secondary_custom_node=True,
            )
            parent_item.append_child(module_item)

        # 递归处理子节点，如果存在
        if "sub_container" in node:
            for child in node["sub_container"]:
                # 继续递归构建树
                self.create_tree(child, parent_item=module_item, depth=depth + 1)

    # 构建模型数据
    def init_model_data_secondary(self):
        root_item = self.secondary_menu_cfg_of_tab["tree"]
        self.create_tree(root_item, parent_item=self.root_item, icon=":/plugin.svg")

    def update_model_data_secondary(self, ecuc_cfg):
        self.root_item = ArgQTreeItem("root", path="/ActiveEcuC")
        self.ecuc_cfg_obj_dict = ecuc_cfg
        self.group_item_dict.clear()
        self.child_item_dict.clear()
        self.beginResetModel()
        self.init_model_data_secondary()
        self.endResetModel()

    # 构建模型数据
    def init_model_data(self):
        for instance_name, module_ecuc_obj in self.ecuc_cfg_obj_dict.items():
            module_item = ArgQTreeItem(module_ecuc_obj, ":/plugin.svg")
            self.root_item.append_child(module_item)
            module_name = self.instance_bswmd_mapping_dict[instance_name]
            self.parse_param_conf_container_def(self.bswmd_autosar_obj_dict[module_name].CONTAINERS, 1)
            if hasattr(module_ecuc_obj, "CONTAINERS"):
                self.add_containers(module_item, module_ecuc_obj.CONTAINERS, 1)
            elif hasattr(module_ecuc_obj, "SUB_CONTAINERS"):
                self.add_containers(module_item, module_ecuc_obj.SUB_CONTAINERS, 1)

    def update_model_data(self, ecuc_cfg, is_secondary=False, secondary_menu_cfg_of_tab=None):
        self.root_item = ArgQTreeItem("root", path="/ActiveEcuC")
        self.ecuc_cfg_obj_dict = ecuc_cfg
        self.group_item_dict.clear()
        self.child_item_dict.clear()
        self.beginResetModel()
        if is_secondary is True:
            self.init_model_data_secondary()
        else:
            self.init_model_data()
        self.endResetModel()

    def parse_param_conf_container_def(self, containers, n):
        if containers is None:
            return
        container_defs = []
        if hasattr(containers, "ECUC_PARAM_CONF_CONTAINER_DEF"):
            container_defs += containers.ECUC_PARAM_CONF_CONTAINER_DEF
        else:
            container_defs += containers.parent_object_.ECUC_PARAM_CONF_CONTAINER_DEF
        if containers.get_tag() in ["CONTAINERS", "SUB-CONTAINERS"]:
            container_defs += containers.ECUC_CHOICE_CONTAINER_DEF
        for container_def in container_defs:
            self.update_defs_dict(container_def, n)
            tag = container_def.get_tag()
            if tag == "ECUC-PARAM-CONF-CONTAINER-DEF":
                self.parse_param_conf_container_def(container_def.SUB_CONTAINERS, n + 1)
            elif tag == "ECUC-CHOICE-CONTAINER-DEF":
                self.parse_param_conf_container_def(container_def.CHOICES, n + 1)
            else:
                logger.warning(f"Unsupported tag: {tag}")

    def update_defs_dict(self, node, n):
        definition_ref = node.get_path()
        if definition_ref not in self.defs_dict:
            lower, upper, upper_infinite = utils.get_multiplicity(node)
            item_dict = {}
            if upper_infinite or (upper and upper > 1):
                item_dict["is_group"] = True
                if n not in self.defs_set:
                    self.defs_set[n] = set()
                self.defs_set[n].add(node.get_path())
            else:
                item_dict["is_group"] = False
            item_dict["def"] = node
            self.defs_dict[definition_ref] = item_dict

    def add_containers(self, parent_item: ArgQTreeItem, containers, n, child_widget_type=None, filter_condition=None):
        if containers is None or parent_item.get_path() is None:
            return
        if parent_item.get_is_recursion():
            self.add_container_groups(parent_item, n)
        for container_value in containers.ECUC_CONTAINER_VALUE:
            definition_ref = utils.get_definition_ref(container_value)
            definition_ref = definition_ref
            item_child = ArgQTreeItem(container_value, ":/container.svg", widget_type=child_widget_type)
            if definition_ref not in self.defs_dict:
                continue
            def_ref_dict = self.defs_dict[definition_ref]
            if filter_condition is not None:
                is_match = self.filter_container_by_filter_condition(filter_condition, container_value)
                if is_match is False:
                    continue
            parent_item_path = parent_item.get_path()
            if def_ref_dict["is_group"] and definition_ref in self.group_item_dict.get(parent_item_path, {}):
                self.group_item_dict[parent_item_path][definition_ref].append_child(item_child)
            else:
                parent_item.append_child(item_child)
                item_child_path = item_child.get_path()
                item = self.child_item_dict.get(item_child_path)
                if item is None:
                    self.child_item_dict[item_child_path] = item_child
                else:
                    # Unreachable branch
                    module = self.root_item.get_child(0).get_data()
                    name = utils.get_short_name(module)
                    logger.error(
                        f"{name}_ecuc.arxml has multiple duplicate paths: {item.get_path()}, "
                        "Please manually delete, Keep the first one!"
                    )
            self.add_containers(item_child, container_value.SUB_CONTAINERS, n + 1)

    def gather_param_ref_val(self, container_cfg_obj):
        """
        Gather all parameter and refernce val obj from the container val obj

        Returns:
        A dict mapping definition ref path to val obj list
        example:
        {
            "/AUTOSAR/EcucDefs/Os/OsTask/OsMemoryMappingCodeLocationRef": ECUC_REFERENCE_VALUE obj,
            ...
        }
        """
        param_cfg_val_dict = defaultdict(list)
        # param_ref_val_dict = defaultdict(list)

        param_val_list = []
        param_val_list += getattr(container_cfg_obj.PARAMETER_VALUES, "ECUC_NUMERICAL_PARAM_VALUE", [])
        param_val_list += getattr(container_cfg_obj.PARAMETER_VALUES, "ECUC_TEXTUAL_PARAM_VALUE", [])
        for param_val in param_val_list:
            param_values = {}
            # if None == param_values["cfg_value"]:
            param_values["cfg_value"] = utils.get_value(param_val)
            param_values["annotations"] = utils.get_annotations(param_val)
            param_values["ecuc_path"] = param_val.get_path()
            def_path = utils.get_definition_ref(param_val)
            param_cfg_val_dict[def_path].append(param_values)
            # param_cfg_val_dict[def_path] = param_values

        ref_val_list = []
        ref_val_list += getattr(container_cfg_obj.REFERENCE_VALUES, "ECUC_INSTANCE_REFERENCE_VALUE", [])
        ref_val_list += getattr(container_cfg_obj.REFERENCE_VALUES, "ECUC_REFERENCE_VALUE", [])
        for ref_val in ref_val_list:
            ref_values = {}
            if "ECUC-REFERENCE-VALUE" == ref_val.original_tagname_:
                ref_values["cfg_value"] = utils.get_value_ref(ref_val)
            elif "ECUC-INSTANCE-REFERENCE-VALUE" == ref_val.original_tagname_:
                ref_values["cfg_value"] = utils.get_value_iref(ref_val)
            ref_values["annotations"] = utils.get_annotations(ref_val)
            ref_values["ecuc_path"] = ref_val.get_path()
            def_path = utils.get_definition_ref(ref_val)
            param_cfg_val_dict[def_path].append(ref_values)
            # param_cfg_val_dict[def_path] = ref_values

        return param_cfg_val_dict

    def filter_container_by_filter_condition(self, filter_condition_list, container_value):
        is_match = True  # 假设容器默认符合条件，直到找到不符合的条件
        param_cfg_val_dict = self.gather_param_ref_val(container_value)

        for condition in filter_condition_list:
            if not self.evaluate_condition(condition, container_value, param_cfg_val_dict):
                is_match = False
                break

        return is_match

    def evaluate_condition(self, condition, container_value, param_cfg_val_dict):
        # 检查配置项条件
        by_configuration_item = condition.get("by_configuration_item")
        if by_configuration_item and not self.is_match_by_configuration_item(by_configuration_item, param_cfg_val_dict):
            return False

        # 检查该container是否为自动推导出来的
        by_is_automatic = condition.get("by_is_automatic")
        is_automatic = AutosarUtil.is_automatic(container_value)
        if by_is_automatic is not None:
            if by_is_automatic != is_automatic:
                return False

        # 检查子容器存在或不存在条件
        by_sub_container_exist_or_not = condition.get("by_sub_container_exist_or_not")
        if by_sub_container_exist_or_not and not self.is_match_by_sub_container_exist_or_not(
            by_sub_container_exist_or_not, container_value
        ):
            return False

        # 检查该container的admin data
        by_admin_data = condition.get("by_admin_data")
        if by_admin_data and not self.is_match_by_admin_data(by_admin_data, container_value):
            return False

        return True

    def is_match_by_configuration_item(self, by_configuration_item_list, param_cfg_val_dict):
        for configuration_item in by_configuration_item_list:
            for config_key, config_value in configuration_item.items():
                actual_value_list = param_cfg_val_dict.get(config_key)
                if config_value == "*":
                    if not actual_value_list:
                        return False
                else:
                    if not any(actual_value["cfg_value"] == config_value for actual_value in actual_value_list):
                        return False
        return True

    def is_match_by_sub_container_exist_or_not(self, by_sub_container_exist_or_not_list, container_value):
        for sub_container_rule in by_sub_container_exist_or_not_list:
            for sub_container_path, exist_or_not in sub_container_rule.items():
                sub_container_exist = self.check_sub_container_exist(sub_container_path, container_value)
                # 如果规则是"not exist"但我们发现了子容器，或者规则是"exist"但我们没发现子容器，
                # 那么过滤条件就不满足。
                if (exist_or_not == "not exist" and sub_container_exist) or (
                    exist_or_not == "exist" and not sub_container_exist
                ):
                    return False
        return True

    def check_sub_container_exist(self, configuration_key, container_value):
        # 检查 SUB_CONTAINERS 属性是否存在
        sub_containers_attr = getattr(container_value, "SUB_CONTAINERS", None)
        if sub_containers_attr is None:
            return False

        # 检查 ECUC_CONTAINER_VALUE 属性是否存在
        ecuc_container_value = getattr(sub_containers_attr, "ECUC_CONTAINER_VALUE", None)
        if ecuc_container_value is None:
            return False

        # 验证 configuration_key 是否匹配任一子容器的定义引用
        for sub_container in ecuc_container_value:
            definition_ref = utils.get_definition_ref(sub_container)
            if configuration_key == definition_ref:
                return True  # 找到匹配的子容器，存在

        return False  # 未找到匹配项，不存在

    def is_match_by_admin_data(self, by_admin_data, container_value):
        keys_list = []
        admin_value = utils.get_admin_data_all(container_value)
        self.extract_keys(admin_value, keys_list)  # 整理出admin_value中所有的key

        for admin_data_item in by_admin_data:
            if admin_data_item in keys_list:
                return True

        return False  # 未找到匹配项，不存在

    def extract_keys(self, d, keys_list):
        if d is None:
            return
        for key, value in d.items():
            keys_list.append(key)
            if isinstance(value, dict):
                self.extract_keys(value, keys_list)

    def add_container_groups(self, parent_item: ArgQTreeItem, n):
        if parent_item is None:
            return
        if n not in self.defs_set:
            return
        parent_item_path = parent_item.get_path()
        if parent_item_path == "#":
            return
        parent_def_ref = utils.get_definition_ref(parent_item.get_data()) + "/"
        for def_group_ref in sorted(self.defs_set[n]):
            if def_group_ref not in self.defs_dict or not def_group_ref.startswith(parent_def_ref):
                continue
            item_group = ArgQTreeItem(self.defs_dict[def_group_ref]["def"], ":/containers.svg", path="#")
            parent_item.append_child(item_group)
            self.group_item_dict[parent_item_path][def_group_ref] = item_group

    def update_other_args(self, other_args: dict, sec_menu_name):

        if sec_menu_name == "Initialization":
            init_function_settings = self.callback("get_init_function_settings")
            other_args["init_function_settings"] = init_function_settings

    def container_create_trigger(self, item, sec_menu_name):
        other_args = {}
        self.update_other_args(other_args, sec_menu_name)
        module = (
            item.get_data().get_path().split("/")[2]
        )  # item的path获取模块名，path为ecuc arxml的路径，格式统一（/ActiveEcuc/模块名/../..）
        rule = RULE_DICT.get(module, base_rule_instance)
        index = rule.container_create_trigger(item, other_args=other_args)

        return index

    def container_delete_trigger(self, item_list):
        # list中的item都是同一类的container，且至少有一个container，
        # 取第一个元素的path获取模块名，path为ecuc arxml的路径，格式统一（/ActiveEcuc/模块名/../..）
        if len(item_list):
            module = item_list[0].get_path().split("/")[2]
            rule = RULE_DICT.get(module, base_rule_instance)
            rule.container_delete_trigger(item_list)

    def container_move_trigger(self, item_list):
        # list中的item都是同一类的container，且至少有一个container，
        # 取第一个元素的path获取模块名，path为ecuc arxml的路径，格式统一（/ActiveEcuc/模块名/../..）
        if len(item_list):
            module = item_list[0].get_path().split("/")[2]
            rule = RULE_DICT.get(module, base_rule_instance)
            rule.container_move_trigger(item_list)

    def get_module_def_prefix(self, bswmd_autosar_obj_dict):
        module_def_prefix_dict = {}
        for module_name, obj in bswmd_autosar_obj_dict.items():
            for ecuc_module_def_obj in obj.find_nodes("ECUC-MODULE-DEF"):
                def_prefix: str = ecuc_module_def_obj.get_path()
                if def_prefix.endswith(module_name):
                    module_def_prefix_dict[module_name] = def_prefix.replace(f"/{module_name}", "")
                    break
        return module_def_prefix_dict

    def get_conf_def_obj(self, def_ref):
        conf_def_obj = None
        for bswmd_obj in self.bswmd_autosar_obj_dict.values():
            conf_def_obj = bswmd_obj.find(def_ref)
            if conf_def_obj:
                break
        return conf_def_obj

    def get_default_file_path(self):
        """
        Get the default file path mark.
        Note: Cannot be used in secondary menu
        """
        module_obj = next(iter(self.ecuc_cfg_obj_dict.values()))
        dft_path = AutosarEcuc.peek_default_file(module_obj)
        return dft_path


class ArgQTreeView(QTreeView):

    def __init__(self, parent=None, main_window=None, is_secondary=False, secondary_menu_cfg_of_tab=None) -> None:
        super().__init__(parent)
        self.main_ui = parent
        self.main_window = main_window
        self.param_scroll_area: QScrollArea = self.main_ui.paramScrollArea
        self.param_scroll_area.setWidgetResizable(True)
        self.setHeaderHidden(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_menu)
        self.callback = lambda *args, **kwargs: None
        self.is_secondary = is_secondary
        self.secondary_menu_cfg_of_tab = secondary_menu_cfg_of_tab
        self._last_index = QModelIndex()  # save the latest index
        self.setMouseTracking(True)

    def set_callback(self, callback):
        self.callback = callback

    def currentChanged(self, current: QModelIndex, previous: QModelIndex) -> None:
        if current.isValid():
            self.show_param_widget(current)

        return super().currentChanged(current, previous)

    def dropEvent(self, e: QtGui.QDropEvent) -> None:
        if e.dropAction() == Qt.DropAction.MoveAction:
            self.setCurrentIndex(QModelIndex())
        return super().dropEvent(e)

    def use_container_outline(self, item):
        container_show_data_dict = []
        # sub_container_list = item.get_children()
        for sub_container in item.get_children():
            container_path_of_ecuc_arxml = sub_container.get_data().get_path()
            show_data_dict = self.callback(
                "bsw_editor_get_the_show_data_of_the_container", container_path_of_ecuc_arxml
            )
            if show_data_dict is not None:
                container_show_data_dict.append(show_data_dict)
        self.param_widget = ContainerOutlineWidget(self.main_window, container_show_data_dict, self.callback)

    def use_arg_qwidget(self, item, item_path):
        try:
            container_path_of_ecuc_arxml = item.get_data().get_path()
            show_data_dict = self.callback(
                "bsw_editor_get_the_show_data_of_the_container", container_path_of_ecuc_arxml
            )
            if show_data_dict is None:
                show_data_dict = {}
            self.param_widget = ArgQWidget(self.main_window, show_data_dict, item_path, self.callback)
        except Exception:
            self.param_widget = QWidget()
            logger.exception("show param widget occurred exception!")
            return
        pass

    def container_use_custom_widget(self, widget_type, item):

        try:
            # 1. 获取item对象的数据
            # 2. 根据控件类型，导入控件Class
            # 3. 实例化Class
            data = item.get_data()
            show_data_dict = {}

            if data and data.get_tag() != "ECUC-MODULE-CONFIGURATION-VALUES":
                container_path_of_ecuc_arxml = data.get_path()
                if container_path_of_ecuc_arxml:
                    if widget_type == "sec_runtime_system_os_configuration_schedule_table_widget":
                        show_data_dict = (
                            self.callback("bsw_editor_get_the_show_data_of_the_container", container_path_of_ecuc_arxml)
                            or {}
                        )
                    else:
                        show_data_dict = (
                            self.callback(
                                "sec_bsw_editor_get_the_show_data_of_the_container", container_path_of_ecuc_arxml
                            )
                            or {}
                        )

            class_name = "".join(word.title() for word in widget_type.split("_"))
            module = importlib.import_module(f"cfg_gui.widgets.sec_widgets.{widget_type}")
            custom_widget_class = getattr(module, class_name)
            self.param_widget = custom_widget_class(self.main_window, show_data_dict, item.get_path(), self.callback)
            if hasattr(self.param_widget, "create_sub_container_rules"):
                self.param_widget.create_sub_container_rules = self.secondary_menu_cfg_of_tab["right_click_rules"][
                    "create_sub_container_rules"
                ]
        except KeyError:
            logger.error(f"Error: {widget_type} class not found.")
            self.param_widget = QWidget()
        except ImportError as e:
            logger.error(f"Error: Module {widget_type} could not be imported. {e}")
            self.param_widget = QWidget()

    def show_param_widget(self, current: QModelIndex):
        item: ArgQTreeItem = current.internalPointer()
        path = item.get_path()

        widget_type = item.get_widget_type()
        container_flag = False

        if current.parent().data() is None:
            self.param_widget = QWidget()
        elif path == "#":  # 处理标记为“container groups”的节点
            if widget_type is None:  # 没有指定控件类型，默认使用ContainerOutlineItem
                self.use_container_outline(item)
            else:
                self.param_widget = QWidget()
        else:  # 没有特殊指定，表示是container
            if widget_type is None:  # 没有指定控件类型，默认使用ArgQWidget
                self.use_arg_qwidget(item, path)
                container_flag = True
            else:
                self.container_use_custom_widget(widget_type, item)

        self.param_scroll_area.takeWidget()
        self.param_scroll_area.setWidget(self.param_widget)

        if container_flag:
            self.update_validation_error_display(path)

    def get_param_widget_ecuc_path_list(self, container_path):
        ecuc_path_list = []
        for _, show_data_list in self.param_widget.show_data_dict.items():
            for show_data in show_data_list:
                label_name = show_data.get("label_name", "")
                ecuc_path = ""
                if label_name == "ShortName":
                    ecuc_path = show_data.get("ecuc_path")
                elif label_name != "":
                    ecuc_path = f"{container_path}/{label_name}"
                ecuc_path_list.append(ecuc_path)
        return ecuc_path_list

    def get_param_widget(self, param_path, container_path):
        param_widget = None
        for item in self.param_scroll_area.widget().findChildren(QLayout):
            if hasattr(item, "show_data_dict"):
                eucu_path = container_path + "/" + item.show_data_dict.get("label_name", "")
                if eucu_path == param_path:
                    param_widget = item
                    break
        return param_widget

    def update_validation_error_display(self, container_path):
        try:
            if not hasattr(self.param_widget, "show_data_dict"):
                return
            module_name = next(iter(self.model().ecuc_cfg_obj_dict.keys()))
            failed_logs = self.callback("get_container_validation_fail_logs", container_path, module_name)
            path_to_validation_logs = self.callback("validation_fail_logs_to_ui_dict", container_path, failed_logs)
            ecuc_path_list = self.get_param_widget_ecuc_path_list(container_path)
            for param_path, validation_info_list in path_to_validation_logs.items():
                if param_path in ecuc_path_list:
                    param_widget = self.get_param_widget(param_path, container_path)
                    tool_btn = getattr(param_widget, "tool_btn", None)
                    tool_btn_down = getattr(tool_btn, "tool_btn_down", None)
                    if tool_btn_down and validation_info_list:
                        tool_btn.set_error_down("Error", validation_info_list)
                        tool_btn_down.setEnabled(True)
        except Exception as e:
            logger.error(f"update validation error display error: {format(e)}")

    def fill_prameter_and_referance(self, container_value, fill_value_dict):
        parameter_values = []
        parameter_values += getattr(container_value.PARAMETER_VALUES, "ECUC_ADD_INFO_PARAM_VALUE", [])
        parameter_values += getattr(container_value.PARAMETER_VALUES, "ECUC_NUMERICAL_PARAM_VALUE", [])
        parameter_values += getattr(container_value.PARAMETER_VALUES, "ECUC_TEXTUAL_PARAM_VALUE", [])
        for para in parameter_values:
            def_ref = utils.get_definition_ref(para)
            for definition in fill_value_dict.keys():
                if definition in def_ref:
                    utils.set_value(para, fill_value_dict[definition])

        for para in getattr(container_value.REFERENCE_VALUES, "ECUC_REFERENCE_VALUE", []):
            def_ref = utils.get_definition_ref(para)
            for definition in fill_value_dict.keys():
                if definition in def_ref:
                    utils.set_value_ref(para, fill_value_dict[definition])

        for para in getattr(container_value.REFERENCE_VALUES, "ECUC_INSTANCE_REFERENCE_VALUE", []):
            def_ref = utils.get_definition_ref(para)
            for definition in fill_value_dict.keys():
                if definition in def_ref:
                    utils.set_value_iref(para, fill_value_dict[definition])

        return container_value

    def get_init_phase(self, item):
        init_phase = None
        parent_ecuc_path = item.get_parent().get_data().get_path()

        if "EcuMDriverInitListZero" in parent_ecuc_path:
            init_phase = "INIT_ZERO"
        elif "EcuMDriverInitListOne" in parent_ecuc_path:
            init_phase = "INIT_ONE"
        elif "EcuMDriverRestartList" in parent_ecuc_path:
            pass
        elif "EcuMDriverInitListTwo" in parent_ecuc_path:
            init_phase = "INIT_TWO"
        elif "EcuMDriverInitListThree" in parent_ecuc_path:
            init_phase = "INIT_THREE"

        return init_phase

    def get_init_functions_that_have_been_added(self, item):
        children_list = []
        item_children = item.get_children()

        for child in item_children:
            children_list.append(child.get_data().get_path().split("/")[-1])

        return children_list

    def pre_create_container_value(self, container_name=None, def_ref=None):
        fill_in_param_value_list_dict = {}
        item_mod_paths = []
        item = self.get_current_tree_item()
        if item is None:
            return
        if self.secondary_menu_cfg_of_tab:
            sec_menu_name = self.secondary_menu_cfg_of_tab.get("sec_menu_name")
            create_sub_container_rules = self.secondary_menu_cfg_of_tab.get("right_click_rules", {}).get(
                "create_sub_container_rules"
            )
            item_mod_paths = [rule["item_mod_path"] for rule in create_sub_container_rules]
        else:
            sec_menu_name = None
            create_sub_container_rules = None

        if fill_in_param_value_list_dict:
            for container_name, fill_in_param_value in fill_in_param_value_list_dict.items():
                container_obj = self.create_container_value(container_name, sec_menu_name=sec_menu_name)
                self.fill_prameter_and_referance(container_obj, fill_in_param_value)
        elif (
            def_ref in item_mod_paths
            and 0 == len(fill_in_param_value_list_dict)
            and create_sub_container_rules is not None
        ):  # 用户没有在弹窗中做选择
            pass
        else:
            self.create_container_value(container_name)

        # container validation
        self.container_validation()

    def create_container_value(self, container_name=None, sec_menu_name=None):

        item = self.get_current_tree_item()
        if item is None:
            return

        data = item.get_data()
        path = item.get_path()
        parent_item = item.get_parent()
        parent_data = parent_item.get_data()
        i = 1
        base_name = container_name
        if not self.can_create_container(container_name, item):
            return
        children = item.get_children()
        # create sub containers
        if path == "#":
            conf_def = data
            data = parent_data
            if data is None:
                data = parent_item._children[0]._children[0]._data.parent_object_
        else:
            def_ref = utils.get_definition_ref(data)
            def_ref = def_ref + f"/{base_name}"
            model: ArgQTreeModel = self.model()
            conf_def = model.get_conf_def_obj(def_ref)

        guess_name = base_name
        child_name_set = set()
        for child in children:
            child_name = utils.get_short_name(child.get_data())
            child_name_set.add(child_name)
        while guess_name in child_name_set:
            guess_name = f"{base_name}_{i}"
            i += 1

        child_data = AutosarUtil.create_container_value(base_name, conf_def, data, guess_name)

        # Set to default file
        model: ArgQTreeModel = self.model()
        dft_path = model.get_default_file_path()
        AutosarEcuc.mark_path(child_data, dft_path)

        index = self.currentIndex()
        model.append_item(child_data, index, sec_menu_name=sec_menu_name)

        # container validation
        self.container_validation()

        return child_data

    def can_create_container(self, container_name, item, create_num=1):
        data = item.get_data()
        path = item.get_path()
        tag = data.get_tag()
        upper = 65535
        children_num = create_num
        if path == "#":
            upper = utils.get_upper_multiplicity(data) or upper
            upper_infinite = utils.get_upper_multiplicity_infinite(data)
            if upper_infinite:
                upper = max(upper, upper_infinite)
            children_num += item.child_count()
        else:
            model: ArgQTreeModel = self.model()
            def_ref = utils.get_definition_ref(data)
            def_ref = def_ref + f"/{container_name}"
            def_data = model.get_conf_def_obj(def_ref)
            if tag == "ECUC-MODULE-CONFIGURATION-VALUES":
                upper = utils.get_upper_multiplicity(def_data) or upper
                upper_infinite = utils.get_upper_multiplicity_infinite(def_data)
                if upper_infinite:
                    upper = max(upper, upper_infinite)
                children_num = create_num
                container_values = getattr(getattr(data, "CONTAINERS", None), "ECUC_CONTAINER_VALUE", [])
                for container_value in container_values:
                    value_def_ref = utils.get_definition_ref(container_value)
                    if value_def_ref == def_ref:
                        children_num += 1
            elif tag == "ECUC-CONTAINER-VALUE":
                upper = utils.get_upper_multiplicity(def_data) or upper
                upper_infinite = utils.get_upper_multiplicity_infinite(def_data)
                if upper_infinite:
                    upper = max(upper, upper_infinite)
                children_num = create_num
                container_values = getattr(getattr(data, "SUB_CONTAINERS", None), "ECUC_CONTAINER_VALUE", [])
                for container_value in container_values:
                    value_def_ref = utils.get_definition_ref(container_value)
                    if value_def_ref == def_ref:
                        children_num += 1
        ret = True
        if children_num > upper:
            msg_box = QMessageBox(
                QMessageBox.Icon.Warning, "Warning", "当前配置项已达到最大允许值,不允许再添加新的配置项！"
            )
            msg_box.exec()
            ret = False
        return ret

    def create_sub_container_value(self, base_name):
        self.create_container_value(base_name)

    def create_sub_container_choice(self, choice):
        item = self.get_current_tree_item()
        if item is None:
            return
        parent_container = item.get_data()
        model: ArgQTreeModel = self.model()
        parent_def_ref = utils.get_definition_ref(parent_container)
        choice_def_ref = parent_def_ref + f"/{choice}"
        choice_conf_def = model.get_conf_def_obj(choice_def_ref)
        if item.child_count() > 0:
            child_item = item.get_child(0)
            child_data = child_item.get_data()
            child_def_ref = utils.get_definition_ref(child_data)
            if child_def_ref == choice_def_ref:
                return
            model: ArgQTreeModel = self.model()
            index = self.currentIndex().child(0, 0)
            model.removeRow(index.row(), index.parent())
        child_data = AutosarUtil.create_sub_container_choice(choice, choice_conf_def, parent_container)
        model: ArgQTreeModel = self.model()
        index = self.currentIndex()
        model.append_item(child_data, index)

        # container validation
        self.container_validation()

    def duplicate_container_value(self):
        item = self.get_current_tree_item()
        if item is None:
            return
        data = item.get_data()
        def_ref = utils.get_definition_ref(data)
        container_name = ""
        if def_ref is None:
            return
        container_name = def_ref.split("/")[-1]
        parent_item = item.get_parent()
        if not self.can_create_container(container_name, parent_item):
            return
        data_parent = data.get_parent()
        if data_parent is None:
            return
        data_str = AutosarUtil.get_arxml_string(data, is_root=False)
        ret, child_data = AutosarUtil.append_container_value_with_string(data_parent, data_str)
        if not ret:
            return
        AutosarUtil.remove_annotation_value(child_data, "IsAutomatic")
        model: ArgQTreeModel = self.model()
        index = self.currentIndex()
        model.append_item(child_data, index.parent())

        # container validation
        self.container_validation()

    def delete_container_value(self):
        path_list = []
        item = self.get_current_tree_item()
        if item is None:
            return
        model: ArgQTreeModel = self.model()
        index = self.currentIndex()
        indexs = self.selectedIndexes()
        if index not in indexs:
            return
        index_dict = defaultdict(list)
        for index in indexs:
            index_dict[index.parent()].append(index.row())
            item: ArgQTreeItem = index.internalPointer()
            data = item.get_data()
            path = data.get_path()
            path_list.append(path)
        # 清除当前item的报错信息
        cbk_param = {}
        cbk_param["path_list"] = path_list
        self.callback("validation_remove_container", cbk_param)
        self.set_index_before_delete(model, index.parent(), index_dict)
        for index in reversed(index_dict.keys()):
            rows = index_dict[index]
            for row in sorted(rows, reverse=True):
                model.removeRow(row, index)
        # container validation
        self.container_validation()
        gc.collect()

    def set_index_before_delete(self, model: ArgQTreeModel, parent_index, index_dict: dict):
        # Set currentIndex before container deletion to avoid unnecessary signal triggered validation
        first_rows = index_dict[next(iter(index_dict))]
        front_row, succeed_row = min(first_rows) - 1, max(first_rows) + 1
        if front_row >= 0:
            self.setCurrentIndex(model.index(front_row, 0, parent_index))
        elif succeed_row < model.rowCount(parent_index):
            self.setCurrentIndex(model.index(succeed_row, 0, parent_index))
        else:
            self.setCurrentIndex(parent_index)

    def show_all_ref_configuration_items_by_ref_target_slot(self, data):
        # print(self.path)
        path = data.get_path()

        self.all_ref_configuration_items_by_ref_target_dict = self.callback(
            "bsw_editor_all_ref_configuration_items_by_ref_target", path
        )
        self.show_element_usage = getattr(self, "show_element_usage", ArgTableWidget(self.main_window.basic_ui_handler))
        self.show_element_usage.fill_reference_target_table_widget(
            "", self.all_ref_configuration_items_by_ref_target_dict
        )
        if self.show_element_usage.select_reference_target_dialog:
            self.show_element_usage.select_reference_target_dialog.show()

    def find_all_element_items_by_current_short_name_slot(self, data):
        self.main_window.tabWidget_2.setCurrentIndex(3)
        self.main_window.lineEdit.setText(utils.get_short_name(data))
        self.main_window.lineEdit.returnPressed.emit()

    def copy_container_value(self):
        data_list = []
        indexs = self.selectedIndexes()
        for index in indexs:
            item: ArgQTreeItem = index.internalPointer()
            if item.get_path() == "#":
                for item_child in item.get_children():
                    data_list.append(item_child.get_data())
            else:
                data_list.append(item.get_data())
        arxml_str = AutosarUtil.export_ecuc_arxml(data_list)
        QApplication.clipboard().clear()
        QApplication.clipboard().setText(arxml_str)

    def paste_container_value_arxml(self):
        arxml_str = QApplication.clipboard().text()
        model: ArgQTreeModel = self.model()
        try:
            arxml_obj = AutosarUtil.parse_arxml_string(arxml_str)
            paths = AutosarUtil.get_exported_arxml_paths(arxml_obj)
            if len(paths) == 0:
                return
        except Exception:
            logger.debug(f"Paste:\n {arxml_str}")
            return
        item = self.get_current_tree_item()
        new_container_nodes = []
        parent_index_dict = {}
        parent_index_path_dict = defaultdict(dict)
        try:
            item_path = item.get_path()
            parent_node = None
            parent_node_path = ""
            container_node = arxml_obj.find(paths[0])
            container_def_ref = utils.get_definition_ref(container_node)
            data_path = item.get_data().get_path()
            if item_path != "#" and data_path.count("/") == paths[0].count("/"):
                # 在同一级容器上粘贴
                item = item.get_parent()
            elif item_path == "#" and data_path.count("/") == container_def_ref.count("/") + 1:
                # 在下一级容器组上粘贴
                item = item.get_parent().get_parent()
            item_path = item.get_path()
            if item_path == "#":
                # 在容器组上粘贴
                parent_node = item.get_parent().get_data()
                parent_node_path = parent_node.get_path()
            else:
                # 在父容器上粘贴
                parent_node = item.get_data()
                parent_node_path = parent_node.get_path()
            containers = getattr(parent_node, "SUB_CONTAINERS", getattr(parent_node, "CONTAINERS", None))
            if containers is None:
                raise Exception(f"{parent_node} does not have CONTAINERS or SUB_CONTAINERS")
            defs_dict = self.model().defs_dict
            from cfg_gui.common.basic_ui_handler import BasicUIHandler

            for path in paths:
                container_node = arxml_obj.find(path)
                container_def_ref = utils.get_definition_ref(container_node)
                container_def_name = container_def_ref.split("/")[-1]
                parent_item_path = item_path
                if parent_item_path == "#":
                    parent_item_path = f"{parent_node_path}/{container_def_name}(s)"
                elif defs_dict.get(container_def_ref)["is_group"]:
                    parent_item_path = f"{parent_node_path}/{container_def_ref.split('/')[-1]}(s)"
                if parent_item_path in parent_index_path_dict:
                    parent_index_path_dict[parent_item_path]["num"] += 1
                    parent_index_dict[path] = parent_index_path_dict[parent_item_path]["index"]
                    continue
                parent_index = BasicUIHandler.find_index_by_name_path(model, parent_item_path.split("/")[2:])
                parent_index_path_dict[parent_item_path]["num"] = 1
                parent_index_path_dict[parent_item_path]["index"] = parent_index
                parent_index_path_dict[parent_item_path]["def_name"] = container_def_name
                parent_index_dict[path] = parent_index
            for parent_item_path in parent_index_path_dict.keys():
                parent_index = parent_index_path_dict[parent_item_path]["index"]
                parent_item = parent_index.internalPointer()
                create_num = parent_index_path_dict[parent_item_path]["num"]
                container_def_name = parent_index_path_dict[parent_item_path]["def_name"]
                if not self.can_create_container(container_def_name, parent_item, create_num):
                    return
            new_container_nodes = AutosarUtil.append_container_values_with_object(containers, arxml_obj)
        except Exception:
            return
        for i in range(len(new_container_nodes)):
            new_container_node = new_container_nodes[i]
            if new_container_node is None:
                continue
            parent_index = parent_index_dict[paths[i]]
            model.append_item(new_container_node, parent_index)

    def custom_menu_handler(self, menu_name):
        self.callback("_".join(menu_name.split()).lower())

    def can_paste_container_value_arxml(self):
        item = self.get_current_tree_item()
        path = item.get_path()
        data = item.get_data()
        try:
            if path == "#":
                def_ref = data.get_parent().get_path()
            else:
                def_ref = utils.get_definition_ref(data)
                def_ref = def_ref
            arxml_str = QApplication.clipboard().text()
            is_valid = AutosarUtil.validate_exported_arxml(arxml_str, def_ref)
            if not is_valid:
                return False
            arxml_obj = AutosarUtil.parse_arxml_string(arxml_str, False, False)
            if arxml_obj is None:
                return False
        except Exception:
            return False
        return True

    def show_menu(self):
        menu_options = self.init_menu_cfg()
        if menu_options is not None:
            self.create_menu(menu_options)

    def init_menu_cfg(self):
        item = self.get_current_tree_item()
        if item is None:
            return
        path = item.get_path()
        data = item.get_data()
        if data is None:  # 二级菜单自定义节点，没有对应的ecuc value
            # 在这里扩展二级菜单自定义节点右键功能
            return
        is_enabled = not (len(self.selectedIndexes()) > 1)
        menu_options = {}
        if path == "#":
            is_container_group = True
            def_ref = data.get_path()
            short_name = utils.get_short_name(data)
            option_name = f"Create {short_name} Container"
            menu_options[option_name] = [
                ":/overlay_plus.png",
                (lambda v, v_def: lambda: self.pre_create_container_value(v, v_def))(short_name, def_ref),
                None,
                is_enabled and self.is_enabled(data),
            ]
            menu_options["Move to..."] = [None, self.move_to_new_file, None, True]
        else:
            is_container_group = False
            def_ref = utils.get_definition_ref(data)
            dest = utils.get_definition_ref_dest(data)
            model: ArgQTreeModel = self.model()
            def_ref = utils.get_definition_ref(data)
            def_data = model.get_conf_def_obj(def_ref)
            def_dest = def_data.get_tag()
            if dest != def_dest:
                logger.error(
                    f'<DEFINITION-REF DEST="{dest}">{def_ref}</DEFINITION-REF> is incorrect, '
                    f"according to AUTOSAR_MOD_ECUConfigurationParameters.arxml DEST should be {def_dest}"
                )
            elif dest == "ECUC-MODULE-DEF" and def_data.CONTAINERS:
                self.init_container_menu_options(menu_options, def_data.CONTAINERS, is_enabled)
            elif dest == "ECUC-PARAM-CONF-CONTAINER-DEF" and def_data.SUB_CONTAINERS:
                self.init_container_menu_options(menu_options, def_data.SUB_CONTAINERS, is_enabled)
            elif dest == "ECUC-CHOICE-CONTAINER-DEF" and def_data.CHOICES:
                self.init_choice_menu_options(menu_options, def_data.CHOICES, is_enabled)
            if item.get_parent().get_data() != "root":
                menu_options["Duplicate..."] = [None, self.duplicate_container_value, None, is_enabled]
                menu_options["Delete"] = [":/not_ok.svg", self.delete_container_value, "Delete", True]
                menu_options["Element Usage"] = [
                    "",
                    (lambda v: lambda: self.show_all_ref_configuration_items_by_ref_target_slot(v))(data),
                    None,
                    is_enabled,
                ]
                menu_options["Find"] = [
                    "",
                    (lambda v: lambda: self.find_all_element_items_by_current_short_name_slot(v))(data),
                    None,
                    is_enabled,
                ]
                menu_options["Move to..."] = [None, self.move_to_new_file, None, True]
        menu_options["Copy"] = {}
        menu_options["Copy"]["Copy ARXML"] = [":/copy.svg", self.copy_container_value, None, True]
        menu_options["Paste ARXML"] = [
            ":/paste.svg",
            self.paste_container_value_arxml,
            None,
            is_enabled and self.can_paste_container_value_arxml(),
        ]
        self.update_menu_options_by_custom_right_click_menu_rules(menu_options, def_ref, is_container_group)
        return menu_options

    def update_menu_options_by_custom_right_click_menu_rules(self, menu_options, def_ref, is_container_group):
        if self.secondary_menu_cfg_of_tab is None:
            return

        right_click_rules = self.secondary_menu_cfg_of_tab.get("right_click_rules", {})
        custom_right_click_menu_rules = right_click_rules.get("custom_right_click_menu_rules")

        # 如果 custom_right_click_menu_rules 为空，或者 def_ref 不在 dictionary 中, 返回
        if not custom_right_click_menu_rules or def_ref not in custom_right_click_menu_rules:
            return

        custom_menu_dict = custom_right_click_menu_rules[def_ref]
        self.disable_common_menu_options(menu_options, custom_menu_dict, is_container_group)
        self.add_custom_menus(menu_options, custom_menu_dict, is_container_group)

    def disable_common_menu_options(self, menu_options, custom_menu_dict, is_container_group):

        disable_common_menu_list = custom_menu_dict.get("disable_common_menu_list")
        if is_container_group is True:
            disable_common_menu_list = disable_common_menu_list["container_group"]
        else:
            disable_common_menu_list = disable_common_menu_list["container"]
        if disable_common_menu_list is None:
            return

        for disable_common_menu in disable_common_menu_list:
            if disable_common_menu == "All":
                menu_options.clear()
                return  # 如果是 "All", 清空 menu_options
            # 删除单个禁用的菜单项
            menu_options.pop(disable_common_menu, None)

    def add_custom_menus(self, menu_options, custom_menu_dict, is_container_group):
        custom_menu_list = custom_menu_dict.get("custom_menu_list")
        if is_container_group is True:
            custom_menu_list = custom_menu_list["container_group"]
        else:
            custom_menu_list = custom_menu_list["container"]
        if custom_menu_list is None:
            return

        for custom_menu in custom_menu_list:
            menu_options[custom_menu] = [None, (lambda v: lambda: self.custom_menu_handler(v))(custom_menu), None, True]

    def init_choice_menu_options(self, menu_options, choices, is_enabled):
        sub_option = "Choices..."
        menu_options[sub_option] = {}
        for param_conf_container in choices.ECUC_PARAM_CONF_CONTAINER_DEF:
            short_name = utils.get_short_name(param_conf_container)

            menu_options[sub_option][short_name] = [
                None,
                (lambda v: lambda: self.create_sub_container_choice(v))(short_name),
                None,
                is_enabled and self.is_enabled(param_conf_container),
            ]
        if len(menu_options[sub_option]) == 0:
            menu_options.pop(sub_option)

    def parse_admin_value_tree_view(self, admin_value):

        ret_value_dict = {"is_enable": True, "cfg_value": None, "unit": None}
        is_enable = None
        if admin_value is not None:
            for i in range(len(admin_value)):
                if "VCOS:CfgLock" in admin_value[i].keys():
                    if "false" == admin_value[i]["VCOS:CfgLock"]:
                        is_enable = True
                    elif "true" == admin_value[i]["VCOS:CfgLock"]:
                        is_enable = False
                    ret_value_dict["is_enable"] = is_enable
                elif "VCOS:CfgValue" in admin_value[i].keys():
                    ret_value_dict["cfg_value"] = admin_value[i]["VCOS:CfgValue"]
                elif "VCOS:BaseUnit" in admin_value[i].keys():
                    ret_value_dict["unit"] = " [" + admin_value[i]["VCOS:BaseUnit"] + "]"
                elif "VCOS:Unit" in admin_value[i].keys():
                    ret_value_dict["unit"] = " [" + admin_value[i]["VCOS:Unit"] + "]"
                    break

        return ret_value_dict

    def is_enabled(self, data):
        admin_value = utils.get_admin_data(data)
        ret_value = self.parse_admin_value_tree_view(admin_value)
        return ret_value["is_enable"]

    def init_container_menu_options(self, menu_options, containers, is_enabled):
        sub_option = "Create Sub Container"
        menu_options[sub_option] = {}
        for choice_container in containers.ECUC_CHOICE_CONTAINER_DEF:
            short_name = utils.get_short_name(choice_container)
            lower, upper, upper_infinite = utils.get_multiplicity(choice_container)
            if upper_infinite or (upper and upper > 1):
                continue
            menu_options[sub_option][short_name] = [
                None,
                (lambda v: lambda: self.create_sub_container_value(v))(short_name),
                None,
                is_enabled and self.is_enabled(choice_container),
            ]
        for param_conf_container in containers.ECUC_PARAM_CONF_CONTAINER_DEF:
            short_name = utils.get_short_name(param_conf_container)
            lower, upper, upper_infinite = utils.get_multiplicity(param_conf_container)
            if upper_infinite or (upper and upper > 1):
                continue
            menu_options[sub_option][short_name] = [
                None,
                (lambda v: lambda: self.create_sub_container_value(v))(short_name),
                None,
                is_enabled and self.is_enabled(param_conf_container),
            ]
        if len(menu_options[sub_option]) == 0:
            menu_options.pop(sub_option)

    def get_current_tree_item(self):
        index = self.currentIndex()
        item: ArgQTreeItem = index.internalPointer()
        return item

    def close_tree_menu(self):
        for action in self.actions():
            self.removeAction(action)
        self.tree_menu.close()

    def create_menu(self, menu_options):
        self.tree_menu = QMenu(self)
        for menu_name, menu_cfg in menu_options.items():
            if isinstance(menu_cfg, dict):
                sub_menu: QMenu = self.tree_menu.addMenu(menu_name)
                for sub_menu_name, sub_menu_cfg in menu_cfg.items():
                    self.set_menu(sub_menu, sub_menu_name, sub_menu_cfg)
            else:
                self.set_menu(self.tree_menu, menu_name, menu_cfg)
        self.tree_menu.popup(QCursor.pos())
        self.tree_menu.aboutToHide.connect(self.close_tree_menu)

    def set_menu(self, menu: QMenu, name, menu_cfg):
        icon, func, shortcut, is_enabled = menu_cfg
        action: QAction = menu.addAction(name)
        if icon:
            action.setIcon(QIcon(icon))
        if shortcut:
            self.addAction(action)
            action.setShortcut(shortcut)
            action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            action.triggered.connect(self.close_tree_menu)
        if func:
            action.triggered.connect(func)
        action.setEnabled(is_enabled)

    def move_to_new_file(self):
        # Select new file path
        prj_file_path = self.main_window.slot_call_back("get_prj_path")
        module_name = next(iter(self.model().ecuc_cfg_obj_dict.keys()))
        module_dir = os.path.join(os.path.dirname(prj_file_path), "config", "bsw", module_name)
        options = QFileDialog.Options()

        file_name, _ = QFileDialog.getSaveFileName(self, "Move to...", module_dir, "", options=options)

        # Validate file path
        if not file_name:
            return
        if os.path.splitext(file_name)[1] != ".arxml":
            QMessageBox.critical(
                self,
                "Error",
                f"{os.path.basename(file_name)} is invalid, file suffix must be 'arxml'",
                QMessageBox.StandardButton.Ok,
            )
            logger.error(f"{os.path.basename(file_name)} is invalid, file suffix must be 'arxml'")
            return
        try:
            Path(file_name).relative_to(module_dir)
        except ValueError:
            QMessageBox.critical(
                self, "Error", f"File path must be descendant of {module_dir}", QMessageBox.StandardButton.Ok
            )
            logger.error(f"File path must be descendant of {module_dir}")
            return
        rel_path = os.path.relpath(file_name, module_dir)

        # Count selected containers
        container_set = set()
        indexs = self.selectedIndexes()
        for index in indexs:
            item: ArgQTreeItem = index.internalPointer()
            if item.get_path() == "#":
                for item_child in item.get_children():
                    container_set.add(item_child.get_data())
            else:
                container_set.add(item.get_data())

        # Mark selected containers
        for container in container_set:
            path_marks = AutosarEcuc.get_path_marks(container)
            reply = QMessageBox.StandardButton.Ok
            if len(path_marks) > 1:
                container_name = utils.get_short_name(container)
                w_info = f"All descendants containers of {container_name} will be moved to {rel_path}, are you sure?"
                reply = QMessageBox.warning(
                    self,
                    "Warning",
                    w_info,
                    QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
            if reply == QMessageBox.StandardButton.Ok:
                AutosarEcuc.mark_path(container, rel_path)
                logger.debug(f"Move {container.get_path()} to new file {rel_path}")
            else:
                logger.debug(f"Cancel moving {container.get_path()} to new file {rel_path}")

    def recovery_all_icon(self, param_item: ArgQTreeItem):
        if not param_item:
            return
        for child_item in param_item.get_children():
            if child_item:
                child_item.recovery_icon()
                child_item.update_validation_result([])
                self.recovery_all_icon(child_item)

    def container_validation(self):
        cbk_param = {}
        model: ArgQTreeModel = self.model()
        cbk_param["module_ecuc_obj"] = model.ecuc_cfg_obj_dict
        cbk_param["container_def_dcit"] = model.defs_dict
        self.callback("validation_container", cbk_param)
        self.update_validation_error_hint()
        self.main_window.validation_ui.validation_model.update_model_data()

    def update_validation_error_hint(self):
        tree_model: ArgQTreeModel = self.model()
        module_name = next(iter(tree_model.ecuc_cfg_obj_dict.keys()))
        failed_validation_logs = self.callback("validation_get_module_fail_logs", [module_name])
        failed_validation_logs = failed_validation_logs.get(module_name, {})
        if not failed_validation_logs:
            return
        # get failed logs
        # 1. recover all icon
        root_item = tree_model.root_item
        self.recovery_all_icon(root_item)

        valdation_error_dict = {}
        for validation_mark, validation_info_dict in failed_validation_logs.items():
            summary = validation_info_dict.get("summary", "")
            validation_info_list = validation_info_dict.get("info", [])
            for validation_info in validation_info_list:
                for ecuc_path in validation_info[1]:
                    if ecuc_path not in valdation_error_dict.keys():
                        valdation_error_dict[ecuc_path] = []
                    valdation_error_dict[ecuc_path].append(
                        {
                            "validation_mark": validation_mark,
                            "summary": summary,
                            "message": validation_info[0],
                            "path": validation_info[1],
                            "auto_solve_list": [] if len(validation_info) < 4 else validation_info[3],
                            "manual_solve_list": [] if len(validation_info) < 5 else validation_info[4],
                        }
                    )

        from cfg_gui.common.basic_ui_handler import BasicUIHandler

        for ecuc_path, validation_error_list in valdation_error_dict.items():
            path_list = ecuc_path.split("/")[2:]
            model_index = BasicUIHandler.find_index_by_name_path(tree_model, path_list)
            tree_item = model_index.internalPointer()
            if tree_item and (ecuc_path == tree_item.get_path() or tree_item.get_path() == "#"):
                tree_item.set_icon(":/unavailable.svg")
                tree_item.update_validation_result(validation_error_list)

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.pos())
        icon_width = int(self.style().pixelMetric(QStyle.PM_SmallIconSize) * 1.1)
        tree_item_rect = self.visualRect(index)
        if index.isValid() and index.column() == 0 and index != self._last_index:
            if tree_item_rect.left() <= event.pos().x() <= tree_item_rect.left() + icon_width:
                self._last_index = index
                tree_item = index.internalPointer()
                valdiation_result = tree_item.get_validation_result()
                if valdiation_result:
                    self.validation_error_window = ValidationErrorWindow(valdiation_result, self.main_window)
                    self.validation_error_window.show()
                    global_pos = self.viewport().mapToGlobal(event.pos())
                    self.validation_error_window.move(global_pos.x() + 5, global_pos.y() + 5)
            else:
                self._last_index = QModelIndex()
        super().mouseMoveEvent(event)

    def restore_derived_sub_containers(self, restorable):
        self.restore_ui = RestoreDerivedUI(self.callback)
        self.restore_ui.build_model(restorable)
        self.restore_ui.ok_callback = self.restore_and_update_tree
        self.restore_ui.show()

    def restore_and_update_tree(self, restore_selection: dict):
        item = self.get_current_tree_item()
        item_path = item.get_path()

        if item_path == "#":
            # Restore at container group
            parent_node = item.get_parent().get_data()
        else:
            parent_node = item.get_data()

        from cfg_gui.common.basic_ui_handler import BasicUIHandler

        parent_node_path = parent_node.get_path()
        defs_dict = self.model().defs_dict
        item_path_to_index = {}
        for _, obj in restore_selection.items():
            container_def_ref = utils.get_definition_ref(obj)
            container_def_name = container_def_ref.split("/")[-1]
            parent_item_path = item_path
            # Get target tree node path
            if parent_item_path == "#":
                parent_item_path = f"{parent_node_path}/{container_def_name}(s)"
            elif defs_dict.get(container_def_ref)["is_group"]:
                parent_item_path = f"{parent_node_path}/{container_def_ref.split('/')[-1]}(s)"

            # Get index of parent node in tree
            if item_path_to_index.get(parent_item_path, None):
                parent_index = item_path_to_index[parent_item_path]
            else:
                parent_index = BasicUIHandler.find_index_by_name_path(self.model(), parent_item_path.split("/")[2:])
                item_path_to_index[parent_item_path] = parent_index

            # Restore contaienr into arxml obj
            parent_xml_node = getattr(parent_node, "SUB_CONTAINERS", None) or getattr(parent_node, "CONTAINERS", None)
            data_str = AutosarUtil.get_arxml_string(obj, is_root=False)
            ret, child_data = AutosarUtil.append_container_value_with_string(parent_xml_node, data_str)
            if not ret:
                return

            # Restore item into tree
            model: "ArgQTreeModel" = self.model()
            model.append_item(child_data, parent_index)
