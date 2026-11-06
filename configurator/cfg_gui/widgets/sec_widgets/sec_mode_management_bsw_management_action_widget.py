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
from cfg_gui.widgets.widget import ArgQWidget
from PyQt5 import QtWidgets, QtCore, QtGui


class SecModeManagementBswManagementActionWidget(ArgQWidget):

    def __init__(self, main_window, show_data_dict, selected_item_path, callback):

        super().__init__(main_window, show_data_dict, selected_item_path, callback)
        self.main_window = main_window
        self.show_data_dict = show_data_dict
        self.selected_item_path = selected_item_path
        self.callback = callback
        self.post_setup_ui()

    def post_setup_ui(self):

        self.from_show_data_dict()  # ui的显示数据还是来自于show data dict，一般都来自于sub container
        self.from_derived_data()  # ui显示的数据是推导出来的，需要callback从底层重新获取

    def from_show_data_dict(self):

        show_data = self.show_data_dict["sub_containers"][0]["sub_containers"][0]
        if show_data:
            first_key = next(iter(show_data))
            del show_data[first_key]
        self.setup_ui(show_data)

    def from_derived_data(self):
        # 对于此处
        # 查找哪个action list引用了这个action
        # 查找哪个rule引用action list
        # 记录路径，以便跳转

        normal_font = QtGui.QFont()
        normal_font.setPointSize(10)  # 设置字体大小
        
        # 初始化触发规则字典用于存储规则标识符和路径
        triggering_rules_dict = {}

        for key, item_value in self.show_data_dict.items():
            # 确认条目值的第一个元素的mod_path是否符合条件
            if item_value[0]["mod_path"] == "/AUTOSAR/EcucDefs/BswM/BswMConfig/BswMModeControl/BswMAction":
                # 获取所有引用配置项
                ref_configuration_items = self.callback("bsw_editor_all_ref_configuration_items_by_ref_target", item_value[0]["ecuc_path"])
                for ref_para, _ in ref_configuration_items.items():
                    # 去除最后两个元素来获取result_str
                    result_str = '/'.join(ref_para.split('/')[:-2])
                    if result_str not in triggering_rules_dict:
                        final_ref_items = self.callback("bsw_editor_all_ref_configuration_items_by_ref_target", result_str)
                        for final_ref_para, _ in final_ref_items.items():
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

        self.message_label = QtWidgets.QLabel(rules_html)
        self.message_label.setFont(normal_font)
        self.message_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.message_label.setTextFormat(QtCore.Qt.RichText)
        self.message_label.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.message_label.setOpenExternalLinks(False)
        self.message_label.linkActivated.connect(self.link_clicked)
        
        self.layout.addWidget(self.message_label, self.layout.rowCount(), 0, 1, -1)

    def link_clicked(self, link):
        self.main_window.basic_ui_handler.ecuc_path_jumps_to_ui(link)