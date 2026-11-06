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
import os
import sys
from PyQt5 import uic
from cfg_gui.widgets.widget import ArgQWidget
from PyQt5 import QtWidgets, QtCore, QtGui
from cfg_gui.widgets.tree_view import ArgQTreeView, ArgQTreeModel
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import QWidget, QHBoxLayout

CUR_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.dirname(CUR_DIR)
CUR_FILE_PATH = os.path.dirname(__file__)
sys.path.append(ROOT_DIR)


class SecModeManagementBswManagementActionListWidget(ArgQWidget):
    ecu_config_path_dict = {}

    def __init__(self, main_window, show_data_dict, selected_item_path, callback):

        super().__init__(main_window, show_data_dict, selected_item_path, callback)
        self.main_window = main_window
        self.show_data_dict = show_data_dict
        self.selected_item_path = selected_item_path
        self.callback = callback

        self.post_setup_ui()

    def post_setup_ui(self):
        self.from_derived_data()  # ui显示的数据是推导出来的，需要callback从底层重新获取
        self.from_show_data_dict()  # ui的显示数据还是来自于show data dict，一般都来自于sub container

    def from_show_data_dict(self):
        normal_font = QtGui.QFont()
        normal_font.setPointSize(10)  # 设置字体大小

        # 构建显示字符串
        action_html = "<b style='color: blue;'>Items</b><br>———————————————————————————————————————————————————————————————————<br>"
        actions_body = "There are the following actions:<br>"
        action_none = "There are no actions in this action list."

        action_dict = {}
        action_of_action_list = self.show_data_dict['sub_containers']
        for action in action_of_action_list:
            for action_key, action_value in action.items():
                if len(action_value) and action_value[0]["label_name"] == "ShortName":
                    action_dict[action_value[0]["cfg_value"]] = action["/AUTOSAR/EcucDefs/BswM/BswMConfig/BswMModeControl/BswMActionList/BswMActionListItem/BswMActionListItemRef"][0]["cfg_value"]

        # 如果没有找到action，只添加 no_action
        if not action_dict:
            rules_html = f"{action_html}{action_none}"
        else:
            # 为每个规则构建链接
            rules_links = "".join([f" <a href='{path}' style='color: blue; text-decoration: none;'>{label}<br></a> " for label, path in action_dict.items()])
            rules_html = f"{action_html}{actions_body}{rules_links}"
        
        self.actions_message_label = QtWidgets.QLabel(rules_html)
        self.actions_message_label.setFont(normal_font)
        self.actions_message_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.actions_message_label.setTextFormat(QtCore.Qt.RichText)
        self.actions_message_label.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.actions_message_label.setOpenExternalLinks(False)
        self.actions_message_label.linkActivated.connect(self.link_clicked)

        self.layout.addWidget(self.actions_message_label, 4, 0, 1, -1)

        # module_cfg_view: QWidget = uic.loadUi(os.path.join(CUR_FILE_PATH, "..", "..", "resources", "ui", "bsw_cfg_base.ui"))  # type: ignore
        # module_cfg_view.splitter.setStretchFactor(1, 2)  # type: ignore
        # bswm_bswmd_autosar_obj_dict, bswm_ecuc_cfg_obj_dict = self.callback("sec_get_bswm_mod_and_ecuc_obj", self.selected_item_path_of_short_name)
        # secondary_menu_cfg_of_tab = self.main_window.secondary_menu_cfg["Mode Management"]["Bsw Management"]
        # tree_view = self.get_bsw_tree_view(module_cfg_view, "/AUTOSAR/EcucDefs", bswm_bswmd_autosar_obj_dict, bswm_ecuc_cfg_obj_dict, False, secondary_menu_cfg_of_tab)
        # tree_layout: QHBoxLayout = module_cfg_view.treeHorizontalLayout  # type: ignore
        # tree_layout.addWidget(tree_view)

        # self.layout.addWidget(module_cfg_view, 5, 0, 1, -1)

    def from_derived_data(self):
        # 对于此处
        # 查找哪个rule引用action list
        # 记录路径，以便跳转

        normal_font = QtGui.QFont()
        normal_font.setPointSize(10)  # 设置字体大小
        
        # 初始化触发规则字典用于存储规则标识符和路径
        triggering_rules_dict = {}

        for key, item_value in self.show_data_dict.items():
            # 确认条目值的第一个元素的mod_path是否符合条件
            if 0 == len(item_value):
                continue
            if item_value[0]["mod_path"] == "/AUTOSAR/EcucDefs/BswM/BswMConfig/BswMModeControl/BswMActionList":
                # 获取所有引用配置项
                self.selected_item_path_of_short_name = item_value[0]["ecuc_path"]
                final_ref_para = self.callback("bsw_editor_all_ref_configuration_items_by_ref_target", item_value[0]["ecuc_path"])
                for final_ref_para, _ in final_ref_para.items():
                    # 提取并存储触发规则标识符
                    # 以最终引用参数的倒数第二部分为键，倒数第二部分之前的路径为值
                    rule_identifier = final_ref_para.split("/")[-2]
                    rule_path = '/'.join(final_ref_para.split('/')[:-1])
                    triggering_rules_dict[rule_identifier] = rule_path  
        
        # 构建显示字符串
        rules_intro = "<b style='color: blue;'>Triggering Rules</b><br>———————————————————————————————————————————————————————————————————<br>"
        rules_body = "Rules triggering this action:"
        no_rules_msg = "This action list is not triggered by any rules."
        
        # 如果没有找到规则，只添加 no_rules_msg
        if not triggering_rules_dict:
            rules_html = f"{rules_intro}{no_rules_msg}"
        else:
            # 为每个规则构建链接
            rules_links = "".join([f" <a href='{path}' style='color: blue; text-decoration: none;'>{label}</a> " for label, path in triggering_rules_dict.items()])
            rules_html = f"{rules_intro}{rules_body}{rules_links}"

        self.triggering_rules_message_label = QtWidgets.QLabel(rules_html)
        self.triggering_rules_message_label.setFont(normal_font)
        self.triggering_rules_message_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.triggering_rules_message_label.setTextFormat(QtCore.Qt.RichText)
        self.triggering_rules_message_label.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.triggering_rules_message_label.setOpenExternalLinks(False)
        self.triggering_rules_message_label.linkActivated.connect(self.link_clicked)

        self.layout.addWidget(self.triggering_rules_message_label, 3, 0, 1, -1)

    def link_clicked(self, link):
        self.main_window.basic_ui_handler.ecuc_path_jumps_to_ui(link)

    def get_bsw_tree_view(self, parent, perfix, bswmd_autosar_obj_dict, ecuc_cfg_obj_dict, is_secondary, secondary_menu_cfg_of_tab=None):

        tree_view = ArgQTreeView(bswmd_autosar_obj_dict, parent, self.main_window)
        tree_model = ArgQTreeModel(perfix, bswmd_autosar_obj_dict, ecuc_cfg_obj_dict, parent, is_secondary=is_secondary)
        tree_view.set_callback(self.callback)
        tree_model.set_callback(self.callback)
        tree_view.setModel(tree_model)
        tree_view.setDropIndicatorShown(True)
        tree_view.setDragDropOverwriteMode(False)
        tree_view.setDragDropMode(ArgQTreeView.DragDropMode.InternalMove)
        tree_view.setSelectionMode(ArgQTreeView.SelectionMode.ExtendedSelection)
        tree_view.setSelectionBehavior(ArgQTreeView.SelectionBehavior.SelectItems)
        tree_view.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tree_view.expandToDepth(1)

        def update_tree_scroll_area(tree_view: ArgQTreeView, index: QModelIndex):
            tree_view.resizeColumnToContents(index.column())

        tree_view.expanded.connect(lambda index: update_tree_scroll_area(tree_view, index))
        tree_view.collapsed.connect(lambda index: update_tree_scroll_area(tree_view, index))
        return tree_view
