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
import threading
from PySide6 import QtWidgets
from PySide6.QtGui import QCursor, QIcon, QRegularExpressionValidator
from PySide6.QtCore import Qt, QModelIndex, QRegularExpression
from PySide6.QtWidgets import QWidget, QTabWidget, QTreeWidgetItem, QTreeWidget, QHBoxLayout
from PySide6.QtWidgets import QHeaderView, QPushButton
from ui_adaptor.ui_interaction.ui_logger import logger
from basic_func_module.autosar_utils.autosar_utils import AutosarUtils
from cfg_gui.widgets.tree_view import ArgQTreeView, ArgQTreeModel
from cfg_gui.widgets.widget import ArgQWidget
from cfg_gui.widgets.container_outline import ContainerOutlineWidget
from cfg_gui.rte_editor.rte_edit_ui import RTE_TAB_IDX
from basic_func_module.autosar_utils.utils import get_definition_ref
from cfg_gui.trace.vfb_trace_function_ui import VfbTraceCfgUI
from cfg_gui.resources.ui.ui_bsw_cfg_base import Ui_Form

CUR_FILE_PATH = os.path.dirname(__file__)
BSW_TAB = 0
RTE_TAB = 1


class ModuleCfgView(QWidget, Ui_Form):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setupUi(self)


class OverViewUI:

    def __init__(self, main_window):
        self.main_window = main_window
        self.bswmd_autosar_dict = {}
        self.bsw_ecuc_autosar_dict = {}
        self.bsw_cfg_view_dict = {}
        self.bsw_overview_tab_set = set()
        self.lock = threading.Lock()
        self.cur_tab_name = None
        self.callback = lambda *args, **kwargs: args or kwargs
        self.load_validation_log_status = False
        self.rules_edit_button = None
        self.rules_editor_tree_view = None
        self.main_window.treeWidgetOverview.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.main_window.treeWidgetOverview.customContextMenuRequested.connect(self.show_menu)

    def set_callback(self, callback):
        self.callback = callback

    def show_bsw_tab_slot(self, index: QModelIndex):
        module_name = index.data()
        tab_name = module_name  # bsw,tab name和module name相同
        bsw_tab_widget: QTabWidget = self.main_window.bswTabWidget
        self.update_bsw_module_data(module_name, tab_name)
        if module_name not in self.bsw_cfg_view_dict:
            if not self.add_bsw_module_view({module_name}, tab_name):
                return
        else:
            self.update_bsw_module_view({module_name}, tab_name)
        module_cfg_view = self.bsw_cfg_view_dict[module_name]
        tab_index = bsw_tab_widget.indexOf(module_cfg_view)
        if tab_index == -1:
            bsw_tab_widget.addTab(module_cfg_view, module_name)
        tab_index = bsw_tab_widget.indexOf(module_cfg_view)
        bsw_tab_widget.setCurrentIndex(tab_index)

    def switch_bsw_tab_solt(self, index):
        previous_tab_name = self.cur_tab_name
        bsw_tab_widget: QTabWidget = self.main_window.bswTabWidget
        self.cur_tab_name = bsw_tab_widget.tabText(index)
        if previous_tab_name != "Overview":
            # 切换tab，更新当前模块的data和view，后台启线程完成
            self.update_bsw_module_data_and_view(previous_tab_name)
        if self.cur_tab_name != "Overview":
            self.refresh_bsw_view_focus()

    def close_bsw_tab_solt(self, index: int):
        if index == 0:
            return
        else:
            bsw_tab_widget: QTabWidget = self.main_window.bswTabWidget
            bsw_tab_widget.removeTab(index)

    def update_overview(self, args):
        """
        Update MainWindow OverView.
        args: Require len(args) == 2
              args[0]: bswmd autosar dict, {"All": <autosar44.autosar44...>}}.
              args[1]: bsw module ecuc autosar dict, {"Rte": <autosar44.autosar44...>, }.
        """
        assert len(args) == 2
        old_bsw_set = set(self.bsw_overview_tab_set)
        new_bsw_set = set(args[1])
        add_ecuc = new_bsw_set - old_bsw_set
        remove_ecuc = old_bsw_set - new_bsw_set
        self.bswmd_autosar_dict: dict = args[0]
        self.bsw_ecuc_autosar_dict: dict = args[1]
        self.overview_add_modules(add_ecuc)
        self.overview_remove_modules(remove_ecuc)

        if not self.load_validation_log_status:
            self.callback("validation_load_ignored_logs")
            self.callback(
                "validation_load_logs",
                result_callback=self.main_window.validation_ui.validation_model.update_model_data,
            )
            self.load_validation_log_status = True
        self.callback("parse_rte_codegen_dict")
        return True

    def overview_add_modules(self, module_name_list):
        for module_name in module_name_list:
            if module_name == "Rte":
                self.main_window.tabWidget.setTabEnabled(RTE_TAB, True)
            elif module_name == "Com":
                self.main_window.rteTabWidget.setTabEnabled(RTE_TAB_IDX["Data Mapping"], True)
            if module_name in self.bsw_overview_tab_set:
                continue
            module_item = QTreeWidgetItem(self.main_window.treeWidgetOverview, [module_name])  # type: ignore
            module_item.setIcon(0, QIcon(":/plugin.svg"))
            self.bsw_overview_tab_set.add(module_name)
        self.main_window.treeWidgetOverview.sortItems(0, Qt.SortOrder.AscendingOrder)  # type: ignore

    def overview_add_module(self, module_name):
        self.overview_add_modules([module_name])

    def overview_remove_modules(self, module_name_list):
        for module_name in module_name_list:
            if module_name == "Rte":
                self.main_window.tabWidget.setTabEnabled(RTE_TAB, False)
            elif module_name == "Com":
                self.main_window.rteTabWidget.setTabEnabled(RTE_TAB_IDX["Data Mapping"], False)
            if module_name not in self.bsw_overview_tab_set:
                continue
            self.bsw_overview_tab_set.remove(module_name)
            tree_widget_overview: QTreeWidget = self.main_window.treeWidgetOverview  # type: ignore
            items = tree_widget_overview.findItems(module_name, Qt.MatchFlag.MatchExactly)
            if len(items) == 1:
                item: QTreeWidgetItem = items[0]
                parent = item.parent()
                if parent is not None:
                    parent.removeChild(item)
                else:
                    tree_widget_overview.invisibleRootItem().removeChild(item)
                self.remove_bsw_cfg_view(module_name)
            else:
                pass
        self.main_window.treeWidgetOverview.sortItems(0, Qt.SortOrder.AscendingOrder)  # type: ignore

    def overview_remove_module(self, module_name):
        self.overview_remove_modules([module_name])

    def add_bsw_module_view(self, module_names_list, tab_name=None, is_secondary=False, secondary_menu_cfg_of_tab=None):

        if tab_name in self.bsw_cfg_view_dict:
            return False
        instance_bswmd_mapping_dict = {}
        bswmd_autosar_obj_dict = {}
        ecuc_cfg_obj_dict = {}
        for instance_name in module_names_list:
            ecuc_obj = self.bsw_ecuc_autosar_dict.get(instance_name)
            if ecuc_obj:
                ecuc_cfg_obj = ecuc_obj.find(f"/ActiveEcuC/{instance_name}")
                module_def_ref = get_definition_ref(ecuc_cfg_obj) or ""
                module_name = module_def_ref.split("/")[-1]
                module_def_obj = self.bswmd_autosar_dict.get(module_name)
                if not module_def_obj:
                    logger.error(f"{module_name} Configuration Parameter Definition not found!")
                    continue
                ecuc_cfg_obj_dict[instance_name] = ecuc_cfg_obj
                bswmd_autosar_obj_dict[module_name] = AutosarUtils.get_bswmd_autosar_by_module_name(
                    module_name, module_def_obj
                )
                instance_bswmd_mapping_dict[instance_name] = module_name
            else:
                logger.warning(f"{instance_name} module view init failed!")
                bswmd_autosar_obj_dict.pop(instance_name, None)
        if not bswmd_autosar_obj_dict or not ecuc_cfg_obj_dict:
            logger.error(f"{tab_name} module view init failed!")
            return False

        module_cfg_view = ModuleCfgView()
        module_cfg_view.splitter.setStretchFactor(1, 2)  # type: ignore
        tree_view = self.get_bsw_tree_view(
            module_cfg_view,
            instance_bswmd_mapping_dict,
            bswmd_autosar_obj_dict,
            ecuc_cfg_obj_dict,
            is_secondary,
            secondary_menu_cfg_of_tab,
        )
        tree_layout: QHBoxLayout = module_cfg_view.treeHorizontalLayout  # type: ignore
        tree_layout.addWidget(tree_view)
        if not is_secondary:
            self.rte_vfb_trace_button(module_name, tree_layout)
        self.bsw_cfg_view_dict[tab_name] = module_cfg_view
        logger.info(f"Add {tab_name} tab.")
        return True

    def rte_vfb_trace_button(self, module_name, tree_layout):
        if "Rte" == module_name:
            self.vfb_trace_button = QPushButton("VFB\nTrace")
            font_metrics = self.vfb_trace_button.fontMetrics()
            self.vfb_trace_button.setFixedSize(font_metrics.horizontalAdvance("Trace") + 10, font_metrics.height() + 30)
            tree_layout.addWidget(self.vfb_trace_button, alignment=Qt.AlignTop)
            self.vfb_trace_button.clicked.connect(self.__vfb_trace_function_slot)

    def __vfb_trace_function_slot(self):
        runnable_info_list = self.callback("get_all_runnnable_info")
        self.vfb_trace_cfg_window = VfbTraceCfgUI(
            runnable_info_list, self.callback, self.update_bsw_module_data_and_view
        )
        self.vfb_trace_cfg_window.show()

    def remove_bsw_cfg_view(self, module_name):
        if module_name not in self.bsw_cfg_view_dict:
            return
        module_cfg_view: QWidget = self.bsw_cfg_view_dict[module_name]
        module_cfg_view.deleteLater()
        self.bsw_cfg_view_dict.pop(module_name)

    def get_bsw_tree_view(
        self,
        parent,
        instance_bswmd_mapping_dict,
        bswmd_autosar_obj_dict,
        ecuc_cfg_obj_dict,
        is_secondary,
        secondary_menu_cfg_of_tab=None,
    ):
        self.secondary_menu_cfg_of_tab = secondary_menu_cfg_of_tab
        tree_view = ArgQTreeView(parent, self.main_window, is_secondary, secondary_menu_cfg_of_tab)
        tree_model = ArgQTreeModel(
            instance_bswmd_mapping_dict,
            bswmd_autosar_obj_dict,
            ecuc_cfg_obj_dict,
            parent,
            self,
            is_secondary,
            secondary_menu_cfg_of_tab,
        )
        tree_view.set_callback(self.callback)
        tree_model.set_callback(self.callback)
        tree_view.setModel(tree_model)
        tree_view.setDropIndicatorShown(True)
        tree_view.setDragDropOverwriteMode(False)
        tree_view.setDragDropMode(ArgQTreeView.DragDropMode.InternalMove)
        tree_view.setSelectionMode(ArgQTreeView.SelectionMode.ExtendedSelection)
        tree_view.setSelectionBehavior(ArgQTreeView.SelectionBehavior.SelectItems)
        tree_view.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tree_view.expandToDepth(0)

        def update_tree_scroll_area(tree_view: ArgQTreeView, index: QModelIndex):
            tree_view.resizeColumnToContents(index.column())

        tree_view.expanded.connect(lambda index: update_tree_scroll_area(tree_view, index))
        tree_view.collapsed.connect(lambda index: update_tree_scroll_area(tree_view, index))
        return tree_view

    def update_bsw_module_data(self, module_name, tab_name):
        self.lock.acquire()
        ecuc_autosar = self.bsw_ecuc_autosar_dict.get(module_name)
        if ecuc_autosar:
            self.callback("bsw_editor_update_bsw_module_data", [module_name])
        self.lock.release()

    def update_bsw_module_data_and_view(self, tab_name):
        if not tab_name:
            return
        module_names_list = [tab_name]
        self.lock.acquire()
        secondary_menu_cfg: dict = self.callback("get_secondary_menu_cfg")
        for secondary_menu_value in secondary_menu_cfg.values():
            if tab_name in secondary_menu_value:
                module_names_list = secondary_menu_value[tab_name]["tab_dependency_module_list"]
                break
        self.callback(
            "bsw_editor_update_bsw_module_data_and_view",
            module_names_list,
            result_callback=self.update_bsw_modules_view_switch,
        )
        self.lock.release()

    def update_bsw_modules_view(self, module_name_list):
        self.lock.acquire()
        for module_name in module_name_list:
            self.update_bsw_module_view([module_name], module_name)
        self.lock.release()

    def update_bsw_modules_view_switch(self, module_list):
        # 切换tab时，除了更新当前模块的view，还需要更新与该模块相关的二级菜单的view
        module_dependency_tab_list: dict = self.callback("get_module_dependency_tab_list")
        secondary_menu_cfg: dict = self.callback("get_secondary_menu_cfg")
        for module_name in module_list:
            self.update_bsw_module_view([module_name], module_name)
        tab_names_list = module_dependency_tab_list.get(module_name, [])
        dependency_secondary_menu_dict = {
            tab_name: secondary_menu_value[tab_name]
            for tab_name in tab_names_list
            for secondary_menu_value in secondary_menu_cfg.values()
            if tab_name in secondary_menu_value
        }
        for tab_name, secondary_menu_dict in dependency_secondary_menu_dict.items():
            self.update_bsw_module_view(
                secondary_menu_dict["tab_dependency_module_list"],
                tab_name,
                is_secondary=True,
                secondary_menu_cfg_of_tab=secondary_menu_dict,
            )

    def update_bsw_module_view(
        self, module_names_list, tab_name=None, is_secondary=False, secondary_menu_cfg_of_tab=None
    ):

        ecuc_cfg_obj_dict = {}

        if tab_name not in self.bsw_cfg_view_dict:
            return
        module_cfg_view: QWidget = self.bsw_cfg_view_dict[tab_name]
        tree_view: ArgQTreeView = module_cfg_view.findChild(ArgQTreeView)  # type: ignore
        tree_model: ArgQTreeModel = tree_view.model()  # type: ignore
        # ecuc_cfg = None
        for module_name in module_names_list:
            if module_name in self.bsw_ecuc_autosar_dict:
                module_autosar = self.bsw_ecuc_autosar_dict[module_name]
                ecuc_cfg_obj_dict[module_name] = module_autosar.find(f"/ActiveEcuC/{module_name}")
                # ecuc_cfg = module_autosar.find(f"/ActiveEcuC/{module_name}")
                if ecuc_cfg_obj_dict[module_name] is None:
                    logger.error(f"/ActiveEcuC/{module_name} is not found!")
                    return
        tree_model.update_model_data(
            ecuc_cfg_obj_dict, is_secondary=is_secondary, secondary_menu_cfg_of_tab=secondary_menu_cfg_of_tab
        )
        tree_view.expandToDepth(0)
        tree_view.viewport().update()
        widget: ArgQWidget = module_cfg_view.paramScrollArea.widget()  # type: ignore
        tab_path = ""
        if is_secondary is True and hasattr(widget, "selected_item_path"):
            tab_path = getattr(widget, "selected_item_path")
        elif isinstance(widget, ArgQWidget) and hasattr(widget, "show_data_dict") and len(widget.show_data_dict) > 0:
            tab_path = list(widget.show_data_dict)[0]
        elif isinstance(widget, ContainerOutlineWidget) and len(widget.model.container_show_data_list) > 0:
            cfg_value = list(widget.model.container_show_data_list[0].values())[0][0]["cfg_value"]
            ecuc_path = list(widget.model.container_show_data_list[0].values())[0][0]["ecuc_path"]
            mod_path = list(widget.model.container_show_data_list[0].values())[0][0]["mod_path"]
            tab_path = ecuc_path.replace(cfg_value, mod_path.split("/")[-1])
        if tab_path and "/" in tab_path:
            path_list = tab_path.split("/")[2:]
            index = self.main_window.basic_ui_handler.find_index_by_name_path(tree_model, path_list)
            tree_view.setCurrentIndex(index)

    def refresh_bsw_view_focus(self):
        if self.cur_tab_name == "Overview":  # type: ignore
            return
        autosar_tab_name = self.main_window.tabWidget.currentWidget().objectName()  # type: ignore
        if autosar_tab_name == "vcos_rte" or self.cur_tab_name not in self.bsw_cfg_view_dict:
            return
        module_cfg_view: QWidget = self.bsw_cfg_view_dict[self.cur_tab_name]
        tree_view: ArgQTreeView = module_cfg_view.findChild(ArgQTreeView)  # type: ignore
        if not tree_view:
            return
        tree_view.clicked.emit(tree_view.currentIndex())
        # container validation
        tree_view.container_validation()

    def refresh_bsw_view_tree(self, tab_name):
        if tab_name not in self.bsw_cfg_view_dict:
            return
        module_cfg_view: QWidget = self.bsw_cfg_view_dict[tab_name]
        tree_view: ArgQTreeView = module_cfg_view.findChild(ArgQTreeView)  # type: ignore
        tree_view.viewport().update()

    def show_menu(self):
        module_name = self.main_window.treeWidgetOverview.currentIndex().data()
        _, module_info_dict = self.callback("get_current_project_module_info")
        module_info = module_info_dict.get(module_name)
        if isinstance(module_info, dict):
            if module_info.get("multiple_instance", 0) <= 1:
                return
        self.menu = QtWidgets.QMenu(self.main_window)
        self.menu.addAction(QIcon(":/project_settings.svg"), "Change Module Name", self.show_change_module_name, "")
        self.menu.popup(QCursor.pos())

    def show_change_module_name(self):
        self.change_module_name_dialog = ChangeModuleNameDialog(
            self.change_module_name, self.main_window.treeWidgetOverview
        )
        self.change_module_name_dialog.open()

    def change_module_name(self, new_name):
        old_name = self.main_window.treeWidgetOverview.currentIndex().data()
        if old_name == new_name or new_name in self.bsw_overview_tab_set:
            logger.error("Same name as existing module!")
            return
        self.overview_remove_module(old_name)
        self.callback("apply_module_renaming", old_name, new_name, result_callback=self.overview_add_module)


class ChangeModuleNameDialog(QtWidgets.QDialog):
    re = QRegularExpression("[a-zA-Z0-9_]+$")

    def __init__(self, change_module_name_callback, parent) -> None:
        super().__init__(parent)
        self.setMinimumWidth(300)
        self.setWindowTitle("Change Module Name")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.change_module_name_callback = change_module_name_callback
        self.line_edit = QtWidgets.QLineEdit(self)
        self.line_edit.setPlaceholderText("<Please Input New Name>")
        validator = QRegularExpressionValidator(self.re, self)
        self.line_edit.setValidator(validator)
        self.push_button = QtWidgets.QPushButton("OK", self)
        qhboxlayout = QtWidgets.QHBoxLayout(self)
        qhboxlayout.addWidget(self.line_edit, 7)
        qhboxlayout.addWidget(self.push_button, 3)
        self.push_button.clicked.connect(self.apply_change_slot)

    def apply_change_slot(self):
        new_name = self.line_edit.text()
        if new_name:
            self.change_module_name_callback(new_name)
            self.close()
