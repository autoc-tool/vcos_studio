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
from PySide6 import QtWidgets
from PySide6.QtCore import Qt

DEFAULT_ALTERNATING_ROW_COLORS = False
DEFAULT_SORTING_ENABLED = False
DEFAULT_SELECTION_MODE = QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
DEFAULT_SELECTION_BEHAVIOR = QtWidgets.QAbstractItemView.SelectionBehavior.SelectItems
DEFAULT_SIZE_ADJUST_POLICY = QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents
DEFAULT_DRAG_ENABLED = False
DEFAULT_DRAG_DROP_OVERWRITE_MODE = False
DEFAULT_DRAG_DROP_MODE = QtWidgets.QAbstractItemView.DragDropMode.NoDragDrop
DEFAULT_DROP_ACTION = Qt.DropAction.IgnoreAction
DEFAULT_CONTEXT_MENU_POLICY = Qt.ContextMenuPolicy.NoContextMenu
DEFAULT_MENU_OPTIONS = {"attention": [":/attention_info.svg", True, lambda: None]}


class MappingViewConfig:

    def __init__(self) -> None:
        self.config_dict = {}
        self.config_dict["alternating_row_colors"] = DEFAULT_ALTERNATING_ROW_COLORS
        self.config_dict["sorting_enabled"] = DEFAULT_SORTING_ENABLED
        self.config_dict["selection_mode"] = DEFAULT_SELECTION_MODE
        self.config_dict["selection_behavior"] = DEFAULT_SELECTION_BEHAVIOR
        self.config_dict["size_adjust_policy"] = DEFAULT_SIZE_ADJUST_POLICY
        self.config_dict["drag_enabled"] = DEFAULT_DRAG_ENABLED
        self.config_dict["drag_drop_overwrite_mode"] = DEFAULT_DRAG_DROP_OVERWRITE_MODE
        self.config_dict["drag_drop_mode"] = DEFAULT_DRAG_DROP_MODE
        self.config_dict["drop_action"] = DEFAULT_DROP_ACTION
        self.config_dict["context_menu_policy"] = DEFAULT_CONTEXT_MENU_POLICY
        self.config_dict["menu_options"] = DEFAULT_MENU_OPTIONS.copy()

    @property
    def alternating_row_colors(self) -> bool:
        return self.config_dict.get("alternating_row_colors", DEFAULT_ALTERNATING_ROW_COLORS)

    @alternating_row_colors.setter
    def alternating_row_colors(self, value: bool):
        self.config_dict["alternating_row_colors"] = value

    @property
    def sorting_enabled(self) -> bool:
        return self.config_dict.get("sorting_enabled", DEFAULT_SORTING_ENABLED)

    @sorting_enabled.setter
    def sorting_enabled(self, value: bool):
        self.config_dict["sorting_enabled"] = value

    @property
    def selection_mode(self) -> QtWidgets.QAbstractItemView.SelectionMode:
        return self.config_dict.get("selection_mode", DEFAULT_SELECTION_MODE)

    @selection_mode.setter
    def selection_mode(self, value: QtWidgets.QAbstractItemView.SelectionMode):
        self.config_dict["selection_mode"] = value

    @property
    def selection_behavior(self) -> QtWidgets.QAbstractItemView.SelectionBehavior:
        return self.config_dict.get("selection_behavior", DEFAULT_SELECTION_BEHAVIOR)

    @selection_behavior.setter
    def selection_behavior(self, value: QtWidgets.QAbstractItemView.SelectionBehavior):
        self.config_dict["selection_behavior"] = value

    @property
    def size_adjust_policy(self) -> QtWidgets.QAbstractScrollArea.SizeAdjustPolicy:
        return self.config_dict.get("size_adjust_policy", DEFAULT_SIZE_ADJUST_POLICY)

    @size_adjust_policy.setter
    def size_adjust_policy(self, value: QtWidgets.QAbstractScrollArea.SizeAdjustPolicy):
        self.config_dict["size_adjust_policy"] = value

    @property
    def drag_enabled(self) -> bool:
        return self.config_dict.get("drag_enabled", DEFAULT_DRAG_ENABLED)

    @drag_enabled.setter
    def drag_enabled(self, value: bool):
        self.config_dict["drag_enabled"] = value

    @property
    def drag_drop_overwrite_mode(self) -> bool:
        return self.config_dict.get("drag_drop_overwrite_mode", DEFAULT_DRAG_DROP_OVERWRITE_MODE)

    @drag_drop_overwrite_mode.setter
    def drag_drop_overwrite_mode(self, value: bool):
        self.config_dict["drag_drop_overwrite_mode"] = value

    @property
    def drag_drop_mode(self) -> QtWidgets.QAbstractItemView.DragDropMode:
        return self.config_dict.get("drag_drop_mode", DEFAULT_DRAG_DROP_MODE)

    @drag_drop_mode.setter
    def drag_drop_mode(self, value: QtWidgets.QAbstractItemView.DragDropMode):
        self.config_dict["drag_drop_mode"] = value

    @property
    def drop_action(self) -> Qt.DropAction:
        return self.config_dict.get("drop_action", DEFAULT_DROP_ACTION)

    @drop_action.setter
    def drop_action(self, value: Qt.DropAction):
        self.config_dict["drop_action"] = value

    @property
    def context_menu_policy(self) -> Qt.ContextMenuPolicy:
        return self.config_dict.get("context_menu_policy", DEFAULT_CONTEXT_MENU_POLICY)

    @context_menu_policy.setter
    def context_menu_policy(self, value: Qt.ContextMenuPolicy):
        self.config_dict["context_menu_policy"] = value

    @property
    def menu_options(self) -> dict:
        return self.config_dict.get("menu_options", DEFAULT_MENU_OPTIONS.copy())

    @menu_options.setter
    def menu_options(self, value: dict):
        self.config_dict["context_menu_policy"] = Qt.ContextMenuPolicy.CustomContextMenu
        self.config_dict["menu_options"] = value
