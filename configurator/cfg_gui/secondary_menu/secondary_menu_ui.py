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
import threading
from PySide6.QtWidgets import QTabWidget
from cfg_gui.bsw_editor.overview_ui import OverViewUI

BSW_TAB = 0
RTE_TAB = 1


class SecondaryMenu:
    """Mode Management UI Class"""

    def __init__(self, main_window):
        self.main_window = main_window
        self.overview_obj: OverViewUI = self.main_window.over_view_ui
        self.tabs_view_dict = self.main_window.over_view_ui.bsw_cfg_view_dict  # record all tab items here
        self.lock = threading.Lock()

    def set_callback(self, callback):
        self.callback = callback

    def show_tab(self, tab_name, secondary_menu_cfg_of_tab):
        """here to show tab of module which is in group of mode management"""

        tab_widget_to_show: QTabWidget = self.main_window.bswTabWidget
        self.main_window.tabWidget.setCurrentIndex(BSW_TAB)
        if tab_name not in self.tabs_view_dict:
            # tab has not displayed yet
            if not self.overview_obj.add_bsw_module_view(
                secondary_menu_cfg_of_tab["tab_dependency_module_list"],
                tab_name=tab_name,
                is_secondary=True,
                secondary_menu_cfg_of_tab=secondary_menu_cfg_of_tab,
            ):
                return
        else:
            self.overview_obj.update_bsw_module_view(
                secondary_menu_cfg_of_tab["tab_dependency_module_list"],
                tab_name=tab_name,
                is_secondary=True,
                secondary_menu_cfg_of_tab=secondary_menu_cfg_of_tab,
            )
        tab_view = self.tabs_view_dict[tab_name]

        tab_idx = tab_widget_to_show.indexOf(tab_view)
        if tab_idx == -1:
            tab_widget_to_show.addTab(tab_view, tab_name)
        tab_idx = tab_widget_to_show.indexOf(tab_view)
        tab_widget_to_show.setCurrentIndex(tab_idx)

    def close_secondary_menu_tabs(self):
        """clear Tabs of bsw"""
        self.callback("clear_schedule_table_ui_cache")
        self.callback("clear_jitter_opt_history", True)
        tab_count = self.main_window.bswTabWidget.count()
        for idx in range(tab_count - 1, -1, -1):
            tab_name = self.main_window.bswTabWidget.tabText(idx)
            if tab_name == "Overview":
                continue
            self.main_window.bswTabWidget.tabCloseRequested.emit(idx)
