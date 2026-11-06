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
import re
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QTreeView, QMainWindow, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QToolButton
from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex, QTimer, QSize
from PySide6.QtGui import QGuiApplication, QIcon, QFont
from basic_func_module.base_logger import logger
from func_module.health_monitor.perf_record import log_function_stats
from func_module.validation.common.validation_def import ValidationLogAttrIdx as attrIdx

PIXMAP_SIZE = 15
TITLE_FONT_SIZE = 11
BODY_FONT_SIZE = 9
VALIDATION_LEVEL_BIT = -6
WIDGET_SIZE_HEIGHT_FACTOR = 0.35
WIDGET_SIZE_WIDTH_FACTOR = 0.2


class OneClickSolveHandler:

    @classmethod
    def one_click_auto_solve_logic(cls, over_view_ui, call_back, auto_solve_dict, param_path, update_ui=True):
        if not auto_solve_dict or not auto_solve_dict.get("solve_type", ""):
            return
        solve_type = auto_solve_dict.get("solve_type", "")

        if solve_type == "CreateContainer":
            cls.__create_container(over_view_ui, call_back, auto_solve_dict, param_path, update_ui)
        elif solve_type == "SetValue":
            cls.__set_param_value(over_view_ui, call_back, auto_solve_dict, param_path, update_ui)
        elif solve_type == "Repopulate_value":
            cls.__repopulate_params_value(over_view_ui, call_back, auto_solve_dict, param_path, update_ui)
        elif solve_type == "DeleteReference":
            cls.__delete_reference(over_view_ui, call_back, auto_solve_dict, param_path, update_ui)
        elif solve_type == "UnmapRunnable":
            cls.__unmap_runnable(over_view_ui, call_back, auto_solve_dict, param_path, update_ui)
        elif solve_type == "MapRunnable":
            cls.__map_runnable(over_view_ui, call_back, auto_solve_dict, param_path, update_ui)
        else:
            logger.ui_warning("one click solution error!")
            return

    @classmethod
    def __create_container(cls, over_view_ui, call_back, auto_solve_dict, param_path, update_ui):
        param_mod_path = auto_solve_dict.get("parameter", "")
        solve_value = auto_solve_dict.get("value", 0)
        create_ret = call_back("create_container_by_one_click_solution", param_path, param_mod_path, solve_value)
        if create_ret and update_ui:
            over_view_ui.update_bsw_module_data_and_view(create_ret)
            over_view_ui.refresh_bsw_view_focus()

    @classmethod
    def __set_param_value(cls, over_view_ui, call_back, auto_solve_dict, param_path, update_ui):
        param_path = auto_solve_dict.get("parameter", "")
        solve_value = auto_solve_dict.get("value", "")
        if isinstance(solve_value, bool):
            solve_value = "true" if solve_value else "false"
        else:
            solve_value = str(solve_value)
        module_name = None
        if isinstance(param_path, list):
            for path in param_path:
                module_name = call_back("update_arxml_value_by_one_click_solution", path, solve_value)
        else:
            module_name = call_back("update_arxml_value_by_one_click_solution", param_path, solve_value)
        if module_name and update_ui:
            cls.update_curr_container_ui_page(over_view_ui, module_name)

    @classmethod
    def __repopulate_params_value(cls, over_view_ui, call_back, auto_solve_dict, param_path, update_ui):
        mod_path = auto_solve_dict.get("parameter", "")
        try:
            begin_value = int(auto_solve_dict.get("value"))
        except BaseException:
            begin_value = 0

        set_value_dict = call_back("set_repopulate_value_by_one_click_solution", param_path, mod_path, begin_value)

        module_name = ""
        for param_path, solve_value in set_value_dict.items():
            module_name = call_back("update_arxml_value_by_one_click_solution", param_path, solve_value)
            if not module_name:
                logger.ui_error(f"update param value({param_path}) in repopulate value")
        # update overview shows
        if module_name and update_ui:
            over_view_ui.update_bsw_module_data_and_view(module_name)
            cls.update_curr_container_ui_page(over_view_ui, module_name)

    @classmethod
    def __delete_reference(cls, over_view_ui, call_back, auto_solve_dict, param_path, update_ui):
        mod_path = auto_solve_dict.get("parameter", [])
        delete_ref_list = auto_solve_dict.get("value", [])
        module_name = call_back("delete_reference_by_one_click_solution", mod_path, param_path, delete_ref_list)
        # update overview shows
        if module_name and update_ui:
            cls.update_curr_container_ui_page(over_view_ui, module_name)

    @classmethod
    def __unmap_runnable(cls, over_view_ui, call_back, auto_solve_dict, param_path, update_ui):
        task_name, runnable_name = auto_solve_dict.get("parameter"), auto_solve_dict.get("value")
        position_index, _, _ = call_back("get_runnable_pos_index", task_name, runnable_name)
        if not position_index:
            logger.ui_warning(f"auto unmap: Can't find runnable: {runnable_name} in task: {task_name}")
            return

        call_back("task_mapping_table_unmap", {"unmap_index_list": [position_index]})
        if update_ui:
            cls.update_rte_task_mapping_ui(over_view_ui)

    @classmethod
    def __map_runnable(cls, over_view_ui, call_back, auto_solve_dict, param_path, update_ui):
        """NOTE: mapping from tree is not supported yet"""
        origin_task = auto_solve_dict.get("parameter", {}).get("origin_task")
        dest_task = auto_solve_dict.get("parameter", {}).get("dest_task")
        runnable_name = auto_solve_dict.get("parameter", {}).get("runnable_name")
        position = auto_solve_dict.get("value")
        if not origin_task or not dest_task:
            logger.ui_warning("auto map: Invalid task names")
            return

        # Organize task mapping function args
        _, origin_row, origin_col = call_back("get_runnable_pos_index", origin_task, runnable_name)
        if origin_row is None or origin_col is None:
            # runnable has already been remapped manually
            return
        if origin_task == dest_task:
            dest_col = origin_col
            # mapping position was not changed
            if origin_row == position:
                return
        else:
            dest_col = call_back("get_task_col_in_table", dest_task)

        task_mapping_ui = over_view_ui.main_window.rte_edit_ui.task_mapping_ui
        mimedata = cls.get_task_mapping_table_mimedata(task_mapping_ui, origin_row, origin_col)

        if position is None or dest_col is None:
            logger.ui_warning("auto map: Invalid position or destination column")
            return
        if not mimedata:
            logger.ui_warning("auto map: Failed to get mime data")
            return

        cbk_param = {
            "remap_item_data_list": task_mapping_ui.table_view_model.get_item_data_list(mimedata),
            "target_row": position,
            "target_col": dest_col,
        }

        call_back("task_mapping_remap_data", cbk_param)

        if update_ui:
            cls.update_rte_task_mapping_ui(over_view_ui)

    @classmethod
    def update_curr_container_ui_page(cls, over_view_ui, module_name):
        module_cfg_view = over_view_ui.bsw_cfg_view_dict.get(module_name, None)
        if not module_name or not module_cfg_view:
            return
        from cfg_gui.widgets.tree_view import ArgQTreeView

        tree_view: ArgQTreeView = module_cfg_view.findChild(ArgQTreeView)
        tree_view_curr_idx = tree_view.currentIndex()
        if tree_view_curr_idx.isValid():
            tree_view.show_param_widget(tree_view_curr_idx)

    @classmethod
    def update_rte_task_mapping_ui(cls, over_view_ui):
        """update rte task mapping ui if rte tab was selected"""
        from cfg_gui.bsw_editor.overview_ui import RTE_TAB

        if over_view_ui.main_window.tabWidget.currentIndex() == RTE_TAB:
            task_mapping_ui = over_view_ui.main_window.rte_edit_ui.task_mapping_ui
            if task_mapping_ui:
                task_mapping_ui.update_model()

    @classmethod
    def get_task_mapping_table_mimedata(cls, task_mapping_ui, row_idx, col_idx):
        table_model = task_mapping_ui.table_view_model
        if not table_model:
            return None
        index = table_model.index(row_idx, col_idx)
        table_mime_data = table_model.mimeData([index])
        return table_mime_data


class ValidationUI:

    def __init__(self, main_window):
        self.main_window = main_window
        self.callback = None
        self.validation_view: ValidationView = None
        self.validation_model: ValidationModel = None
        self.setup_ui()

    def setup_ui(self):
        self.validation_view = ValidationView(self.main_window)
        self.validation_model = ValidationModel(self)

        self.validation_view.doubleClicked.connect(self.on_double_clicked)
        self.validation_view.warning_button.clicked.connect(self.validation_model.setup_warning_model_data)
        self.validation_view.error_button.clicked.connect(self.validation_model.setup_error_model_data)
        self.validation_view.all_button.clicked.connect(self.validation_model.setup_all_model_data)
        self.validation_view.ignored_button.clicked.connect(self.validation_model.setup_ignored_model_data)
        self.validation_view.auto_fix_button.clicked.connect(lambda: self.auto_fix_all_validaiton_errors())

        self.validation_view.setModel(self.validation_model)

    def set_callback(self, callback):
        self.callback = callback
        self.validation_view.call_back = callback
        self.validation_model.callback = callback

    def on_double_clicked(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        item = index.internalPointer()
        if not item.has_auto_solve_info():
            self.main_window.basic_ui_handler.ecuc_path_jumps_to_ui(item.text)
        else:
            auto_solve_dict = item.get_auto_solve_info()
            self.one_click_auto_solve_slot(
                self.main_window.over_view_ui, self.callback, auto_solve_dict, item.param_path
            )

    @classmethod
    def one_click_auto_solve_slot(cls, over_view_ui, call_back, auto_solve_dict: dict, param_path):
        OneClickSolveHandler.one_click_auto_solve_logic(over_view_ui, call_back, auto_solve_dict, param_path)

    @log_function_stats(["校验", "校验错误一键解决", "一键解决所有校验错误"])
    def auto_fix_all_validaiton_errors(self):
        root_item: validationItem = self.validation_model.root_item
        for error_parent_item in root_item.children:
            self.validation_view.solve_all_error(error_parent_item)

        logger.ui_info(
            "Auto fix all solvable validation errors, please validate modules to get the latest validaiton information"
        )


class ValidationView(QTreeView):

    def __init__(self, mainwindow: QMainWindow) -> None:
        super().__init__()
        self.setStyleSheet("QListView { border: none; }")
        self.mainwindow = mainwindow
        self.call_back = None
        self.validation_layout: QVBoxLayout = mainwindow.tabValidation.layout()
        self.warning_button = QtWidgets.QPushButton("Warning")
        self.warning_button.setIcon(QIcon(":/validate.png"))
        # self.warning_button.setIconSize(QtCore.QSize(25,25))
        self.error_button = QtWidgets.QPushButton("Error")
        self.error_button.setIcon(QIcon(":/validate_off.png"))
        # self.error_button.setIconSize(QtCore.QSize(25,25))
        self.all_button = QtWidgets.QPushButton("All")
        self.all_button.setIcon(QIcon(":/validateAll.png"))
        # self.all_button.setIconSize(QtCore.QSize(25,25))
        self.ignored_button = QtWidgets.QPushButton("Ignored")
        self.ignored_button.setIcon(QIcon(":/attention_info.svg"))
        self.auto_fix_button = QtWidgets.QPushButton(QIcon(":/auto_fix.svg"), "AutoFix")

        self.hboxlayout = QtWidgets.QHBoxLayout()
        self.hboxlayout.addWidget(self.warning_button)
        self.hboxlayout.addWidget(self.error_button)
        self.hboxlayout.addWidget(self.all_button)
        self.hboxlayout.addWidget(self.ignored_button)
        self.hboxlayout.addWidget(self.auto_fix_button)

        self.hboxlayout.addStretch(3)
        self.validation_layout.addLayout(self.hboxlayout)
        self.validation_layout.addWidget(self)
        self.tree_ignore_menu = None
        self.tree_restore_menu = None

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)  # 打开右键菜单
        self.customContextMenuRequested.connect(self.show_tree_context_menu_slot)

    def create_menu(self, menu, button_name):
        menu.setStyleSheet(
            "QMenu{background:lightgray;}"
            "QMenu{border:1px solid lightgray;}"
            "QMenu::item{padding:0px 10px 0px 5px;}"
            "QMenu::item{height:20px;}"
            "QMenu::item{color:black;}"
            "QMenu::item{background:lightgray;}"
            "QMenu::item{margin:1px 1px 1px 1px;}"
            "QMenu::item:selected:enabled{background:lightskyblue;}"
        )
        if "Ignore" in button_name:
            action = menu.addAction(QtGui.QIcon(":/not_ok.svg"), button_name)
        elif "Restore" in button_name:
            action = menu.addAction(QtGui.QIcon(":/add.svg"), button_name)
        elif "Solve" in button_name:
            action = menu.addAction(QtGui.QIcon(":/validation.svg"), button_name)
        return action

    def _create_lambda(self, over_view_ui, call_back, solve_info_dict, param_path):
        return lambda: ValidationUI.one_click_auto_solve_slot(over_view_ui, call_back, solve_info_dict, param_path)

    def create_solve_menu(self, peer_item):
        menu = QtWidgets.QMenu("solve", self)
        peer_node_list = peer_item.parent.children
        # just search current valdiation item solve data
        had_solve_info = False
        for node in peer_node_list:
            if node.has_auto_solve_info():
                solve_info_dict = node.get_auto_solve_info()
                text = solve_info_dict.get("solve_info")
                action = menu.addAction(QtGui.QIcon(":/validation.svg"), text)
                action.triggered.connect(
                    self._create_lambda(self.mainwindow.over_view_ui, self.call_back, solve_info_dict, node.param_path)
                )
                menu.addAction(action)
                had_solve_info = True
            else:
                if had_solve_info:
                    break
        return menu

    def solve_all_error(self, parent_item):
        child_node_list = parent_item.children
        prev_is_auto_solve, current_is_auto_solve = False, False
        node_info_list = []
        for node_item in child_node_list:
            current_is_auto_solve = node_item.has_auto_solve_info()
            if not prev_is_auto_solve and current_is_auto_solve:
                node_info_list.append(
                    {"solve_info": node_item.get_auto_solve_info(), "param_path": node_item.param_path}
                )
            prev_is_auto_solve = current_is_auto_solve
        for index, item_dict in enumerate(node_info_list):
            update_ui = True if index == len(node_info_list) - 1 else False
            try:
                OneClickSolveHandler.one_click_auto_solve_logic(
                    self.mainwindow.over_view_ui,
                    self.call_back,
                    item_dict.get("solve_info"),
                    item_dict.get("param_path"),
                    update_ui,
                )
            except Exception as e:
                logger.error(f"exception during solving all errors, extra information: {e}")

    def show_tree_context_menu_slot(self, pos: QtCore.QPoint) -> None:
        index = self.indexAt(pos)
        if not index.isValid():
            return

        item = index.internalPointer()
        if item.module == "":
            return

        menu = QtWidgets.QMenu(self)
        if self.model().cur_validation_type != "Ignored":
            if not index.parent().isValid():
                action = self.create_menu(menu, "Ignore All")
                action.triggered.connect(lambda: self.model().update_ignored_dict(item, True, True))
                action = self.create_menu(menu, "Solve All")
                action.triggered.connect(lambda: self.solve_all_error(item))
                self.tree_ignore_menu = menu
                self.tree_ignore_menu.popup(QtGui.QCursor.pos())
            else:
                action = self.create_menu(menu, "Ignore")
                action.triggered.connect(lambda: self.model().update_ignored_dict(item, True, False, self, item.row()))
                solve_menu = self.create_solve_menu(item)
                menu.addMenu(solve_menu)
                self.tree_ignore_menu = menu
                self.tree_ignore_menu.popup(QtGui.QCursor.pos())
        else:
            if not index.parent().isValid():
                action = self.create_menu(menu, "Restore All")
                action.triggered.connect(lambda: self.model().update_ignored_dict(item, False, True))
                self.tree_restore_menu = menu
                self.tree_restore_menu.popup(QtGui.QCursor.pos())
            else:
                action = self.create_menu(menu, "Restore")
                action.triggered.connect(lambda: self.model().update_ignored_dict(item, False, False, self, item.row()))
                self.tree_restore_menu = menu
                self.tree_restore_menu.popup(QtGui.QCursor.pos())


class validationItem:

    def __init__(
        self, module="", text="", code="", icon="", parent=None, auto_solve_dict={}, manual_solve_list=[], param_path=""
    ):
        self.parent = parent
        self.module = module
        self.text = text
        self.code = code
        self.icon = icon
        self.children = []
        self._auto_solve_dict = auto_solve_dict
        self._manual_solve_list = manual_solve_list
        self.param_path = param_path

    def append_child(self, child: "validationItem"):
        self.children.append(child)

    def child_count(self) -> int:
        return len(self.children)

    def row(self) -> int:
        if isinstance(self.parent, validationItem):
            return self.parent.children.index(self)
        else:
            return -1

    def has_auto_solve_info(self) -> bool:
        return bool(self._auto_solve_dict)

    def get_auto_solve_info(self):
        return self._auto_solve_dict

    def get_manual_solve_list(self):
        return self._manual_solve_list


class ValidationModel(QAbstractItemModel):

    def __init__(self, validation_ui: ValidationUI):
        super().__init__()
        self.validation_ui = validation_ui
        self.callback = self.validation_ui.callback
        self.headers = ["ID", "Message"]
        self.root_item = validationItem(module="root")
        # 一级引用数据
        self.validation_logs = {}
        # 二级加工后数据
        self.validation_dict = {}
        self.ignored_dict = {}
        # 当前显示的数据
        self.cur_validation_dict = {}
        # 显示的校验结果类型
        self.cur_validation_type = "All"

    def init_data(self, validation_logs):
        self.validation_logs = validation_logs

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.headers[section]

    def data(self, index: QtCore.QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        col = index.column()
        item: validationItem = index.internalPointer()
        if role == Qt.ItemDataRole.DecorationRole:
            if item.icon != "" and col == 0:
                return QIcon(item.icon)
        elif role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return item.module
            else:
                return item.text
        elif role == Qt.ItemDataRole.ToolTipRole:
            if item.code != "":
                return item.code
        return None

    def index(self, row: int, column: int, parent: QtCore.QModelIndex = ...) -> QtCore.QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()
        item = parent_item.children[row]
        if item:
            return self.createIndex(row, column, item)
        else:
            return QtCore.QModelIndex()

    def flags(self, index: QtCore.QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        if not index.isValid():
            return QtCore.QModelIndex()
        item: validationItem = index.internalPointer()
        if item == self.root_item:
            return QtCore.QModelIndex()
        if item.parent:
            parent_item: validationItem = item.parent
            return self.createIndex(parent_item.row(), index.column(), parent_item)
        return QtCore.QModelIndex()

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        if not parent.isValid():
            item = self.root_item
        else:
            item = parent.internalPointer()
        return item.child_count()

    def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self.headers)

    # validation_dict是否改变直接影响界面的显示,它只包含报警信息
    def setup_model_data(self, validation_dict):
        if self.cur_validation_dict == validation_dict:
            return
        self.cur_validation_dict = validation_dict

        self.beginResetModel()
        # 1）清空所有model数据
        self.root_item.children = []
        flag = False
        parent = self.root_item
        # 2) 根据传入的参数重建model
        for module, validation_list in validation_dict.items():
            for mark, validation_info in validation_list.items():
                for data in validation_info:
                    if flag is False:
                        child = validationItem(
                            data["module"],
                            data["text"],
                            data["code"],
                            data["icon"],
                            parent,
                            data.get("auto_solve_dict", {}),
                            data.get("manual_solve_list", []),
                            data.get("path", ""),
                        )
                        if parent:
                            parent.append_child(child)
                        parent = child
                        flag = True
                        continue
                    child = validationItem(
                        data["module"],
                        data["text"],
                        data["code"],
                        data["icon"],
                        parent,
                        data.get("auto_solve_dict", {}),
                        data.get("manual_solve_list", []),
                        data.get("path", ""),
                    )
                    parent.append_child(child)
                flag = False
                if parent.parent is not None:
                    parent = parent.parent
        self.endResetModel()

    # error_level:错误级别，0-错误，1-警告，2-提示
    def get_error_level_data(self, error_level):
        validation_dict = {}
        for module, validation_list in self.validation_dict.items():
            validation_dict_module = {}
            for mark, validation_info in validation_list.items():
                if int(mark[-6]) == error_level:
                    validation_dict_module[mark] = validation_info
            if validation_dict_module:
                validation_dict[module] = validation_dict_module
        return validation_dict

    def setup_warning_model_data(self):
        warning_model_data = self.get_error_level_data(1)
        self.setup_model_data(warning_model_data)
        self.cur_validation_type = "Warning"

    def setup_error_model_data(self):
        error_model_data = self.get_error_level_data(0)
        self.setup_model_data(error_model_data)
        self.cur_validation_type = "Error"

    def setup_all_model_data(self):
        self.setup_model_data(self.validation_dict)
        self.cur_validation_type = "All"

    def setup_ignored_model_data(self):
        self.setup_model_data(self.ignored_dict)
        self.cur_validation_type = "Ignored"

    def set_icon(self, mark):
        icon_list = [":/validate_off.png", ":/validate.png", ":/validate_on.png"]
        return icon_list[int(mark[-6])]

    def logs_to_dict(self, logs_obj: dict) -> dict:
        """func层使用的logs格式字典转为ui层使用的dict格式字典"""
        dict_obj: dict = {}
        for module, module_validation in logs_obj.items():
            if "logs" not in module_validation.keys():
                continue
            dict_obj[module]: dict = {}
            for mark, block_validation in module_validation["logs"].items():
                if "summary" not in block_validation.keys():
                    continue
                if ("info" not in block_validation.keys()) or (len(block_validation["info"]) == 0):
                    continue
                icon_path = ":/validate_off.png" if mark[-6] == "0" else ":/validate.png"
                dict_obj[module][mark]: list = [
                    {
                        "module": mark,
                        "summary": True,
                        "text": block_validation["summary"] + f" ({len(block_validation['info'])})",
                        "code": "",
                        "icon": icon_path,
                    }
                ]
                for item in block_validation["info"]:
                    if item[2] == "pass":
                        continue
                    auto_solve_list = item[attrIdx.auto_solve] if attrIdx.auto_solve < len(item) else []
                    manual_solve_list = item[attrIdx.manual_solve] if attrIdx.manual_solve < len(item) else []
                    dict_obj[module][mark].append(
                        {
                            "module": mark,
                            "summary": False,
                            "text": item[0],
                            "code": "",
                            "icon": icon_path,
                            "auto_solve_list": auto_solve_list,
                            "manual_solve_list": manual_solve_list,
                        }
                    )
                    # 逐条添加自动解决方法
                    for auto_solve_info in auto_solve_list:
                        if not auto_solve_info:
                            continue
                        info_basic = {"module": "", "summary": False, "text": "", "code": "", "icon": ""}
                        info_basic["text"] = auto_solve_info.get("solve_info", "")
                        info_basic["auto_solve_dict"] = auto_solve_info
                        if auto_solve_info:
                            info_basic["path"] = item[1][0]  # just save the first
                        dict_obj[module][mark].append(info_basic)
                    # 逐条添加path
                    for path in item[1]:
                        dict_obj[module][mark].append(
                            {"module": "", "summary": False, "text": path, "code": "", "icon": ""}
                        )

        return dict_obj

    def clear_model_data(self):
        self.validation_logs = {}
        self.cached_logs = {}
        ignored_logs = {}
        self.ignored_dict = self.logs_to_dict(ignored_logs)
        self.update_validation_dict(self.validation_logs, ignored_logs)
        self.refresh_model()

    def update_validation_dict(self, validation_logs, ignored_logs):
        displayed_validation_logs = self.remove_validation_in_ignored(validation_logs, ignored_logs)
        self.validation_dict = self.logs_to_dict(displayed_validation_logs)

    def check_validation_item_exist(self, item, item_list):
        """检查是否存在指定的校验项"""
        item[1] = sorted(item[1])
        for _ in item_list:
            if item[1] == sorted(_[1]):
                return True
        return False

    def remove_validation_in_ignored(self, validation_logs, ignored_logs):
        """全量校验结果和忽略结果作差集"""
        displayed_validation_logs: dict = {}
        for module_name in validation_logs:
            displayed_validation_logs[module_name] = {"time": validation_logs[module_name]["time"], "logs": {}}
            module_displayed_logs = displayed_validation_logs[module_name]["logs"]
            module_validation_logs = validation_logs[module_name].get("logs", {})
            if module_name not in ignored_logs:
                for mark in module_validation_logs:
                    module_displayed_logs[mark] = {
                        "time": module_validation_logs[mark]["time"],
                        "summary": module_validation_logs[mark]["summary"],
                        "info": [],
                    }
                    module_displayed_logs[mark]["info"] = [
                        item for item in module_validation_logs[mark]["info"] if item[2] != "pass"
                    ]
            else:
                module_ignored_logs = ignored_logs[module_name].get("logs", {})
                for mark in module_validation_logs:
                    module_displayed_logs[mark] = {
                        "time": module_validation_logs[mark]["time"],
                        "summary": module_validation_logs[mark]["summary"],
                        "info": [],
                    }
                    validation_info_list = module_validation_logs[mark]["info"]
                    module_displayed_logs[mark]["info"] = [item for item in validation_info_list if item[2] != "pass"]
                    if mark in module_ignored_logs:
                        ignored_info_list = module_ignored_logs[mark]["info"]
                        module_displayed_logs[mark]["info"] = [
                            item
                            for item in module_displayed_logs[mark]["info"]
                            if self.check_validation_item_exist(item, ignored_info_list) is False
                        ]
            displayed_validation_logs[module_name]["logs"] = module_displayed_logs

        return displayed_validation_logs

    def update_model_data(self, args=None):
        # 1）获取最新数据
        self.validation_logs = self.callback("validation_get_logs")
        self.cached_logs = self.callback("validation_get_cached_logs")
        ignored_logs = self.callback("validation_get_ignored_logs")
        self.ignored_dict = self.logs_to_dict(ignored_logs)
        self.update_validation_dict(self.validation_logs, ignored_logs)
        # 2）刷新model和UI显示
        self.refresh_model()

    @log_function_stats(["校验", "忽略或恢复错误校验项"])
    def update_ignored_dict(
        self, input_item, is_ignore: bool, is_all: bool, tree_view=None, input_item_row=None
    ) -> None:
        src_dict: dict = self.validation_dict if is_ignore is True else self.ignored_dict
        rule_name: str = input_item.module
        # 模块名
        module_name: str = ""
        module_name_lower: str = rule_name[0:-6].lower()
        for v in src_dict.keys():
            if module_name_lower == v.lower():
                module_name = v
                break
        # summary
        summary_text: str = src_dict[module_name][rule_name][0]["text"]
        summary_text = re.match(r"^(.*)(\(\d+\))$", summary_text).group(1).strip()

        # 1.修改func层ignored_logs
        if is_all is False:
            input_item_parent = input_item.parent
            idx: int = input_item_row + 1
            manual_solve_list = input_item_parent.children[idx - 1].get_manual_solve_list()
            auto_solve_list: list = []
            path_list: list = []
            while (idx < len(input_item_parent.children)) and (input_item_parent.children[idx].module == ""):
                if input_item_parent.children[idx].has_auto_solve_info() is True:
                    auto_solve_list.append(input_item_parent.children[idx].get_auto_solve_info())
                else:
                    path_list.append(input_item_parent.children[idx].text)
                idx += 1
            self.callback(
                "validation_update_ignored_logs",
                module_name,
                rule_name,
                summary_text,
                input_item.text,
                path_list,
                auto_solve_list,
                manual_solve_list,
                is_ignore,
            )
        else:
            idx: int = 0
            while idx < len(input_item.children):
                if input_item.children[idx].module != "":
                    item_text = input_item.children[idx].text
                    manual_solve_list = input_item.children[idx].get_manual_solve_list()
                    auto_solve_list: list = []
                    path_list: list = []
                    idx += 1
                    while (idx < len(input_item.children)) and (input_item.children[idx].module == ""):
                        if input_item.children[idx].has_auto_solve_info() is True:
                            auto_solve_list.append(input_item.children[idx].get_auto_solve_info())
                        else:
                            path_list.append(input_item.children[idx].text)
                        idx += 1
                    self.callback(
                        "validation_update_ignored_logs",
                        module_name,
                        rule_name,
                        summary_text,
                        item_text,
                        path_list,
                        auto_solve_list,
                        manual_solve_list,
                        is_ignore,
                    )
                else:
                    idx += 1

        # 2.修改ui层validation_dict并刷新UI显示
        self.update_model_data()
        src_dict: dict = self.validation_dict if is_ignore is True else self.ignored_dict
        src_dict.setdefault(module_name, {})
        src_dict[module_name].setdefault(input_item.module, [])
        if (tree_view is not None) and (src_dict[module_name][input_item.module] != []):
            model = tree_view.model()
            for row in range(model.rowCount(QModelIndex())):
                idx = model.index(row, 0, QModelIndex())
                if model.data(idx) == input_item.module:
                    tree_view.expand(self.index(row, 0, QModelIndex()))
                    break

    def refresh_model(self) -> None:
        """刷新view显示的model数据"""
        if self.cur_validation_type == "Warning":
            self.setup_warning_model_data()
        elif self.cur_validation_type == "Error":
            self.setup_error_model_data()
        elif self.cur_validation_type == "All":
            self.setup_all_model_data()
        elif self.cur_validation_type == "Ignored":
            self.setup_ignored_model_data()


class ClickableLabel(QLabel):

    def __init__(
        self, propose_full_text=None, related_item=None, is_propose: bool = None, clicked_function=None, parent=None
    ):
        super(ClickableLabel, self).__init__(parent)
        self._propose_full_text = propose_full_text
        self._related_item = related_item
        self._is_propose = is_propose
        self._clicked_function = clicked_function

        self.__init_ui()

    def __init_ui(self):
        if self._is_propose:
            show_text = f"{self._propose_full_text}"
        else:
            show_text = self._related_item.split("/")[-1]
        tab_space = "&nbsp;" * 4
        self.setText(f'{tab_space}<a href="#" style="color: blue; text-decoration: underline;">{show_text}</a>')
        self.setFont(QFont("Microsoft YaHei", BODY_FONT_SIZE))

        self.linkActivated.connect(self._clicked_function)


class ValidationErrorWindow(QToolButton):

    def __init__(self, validation_result_list: list, main_window) -> None:
        super().__init__()
        self.validation_result_list = validation_result_list
        self.validation_result_idx = 0
        self.proposed_layout = None
        self.related_item_layout = None
        self.main_window = main_window
        self.call_back = main_window.slot_call_back
        self.error_idx = 0  # represent validation error index
        self.__init_ui()
        self.set_timer_event()

    def can_show(self) -> bool:
        if not self.isVisible():
            return False
        return self.validation_result_list is not None and len(self.validation_result_list) > 0

    def __init_ui(self):
        if not self.validation_result_list:
            return

        # switch error show
        self.switch_error_layout = None
        self.back_btn = QPushButton("<")
        self.back_btn.setFixedWidth(40)
        self.next_btn = QPushButton(">")
        self.next_btn.setFixedWidth(40)
        self.switch_error_layout = QHBoxLayout()
        self.page_idx_label = QLabel(f"1/{len(self.validation_result_list)} items")
        self.page_idx_label.setFont(QFont("Microsoft YaHei", TITLE_FONT_SIZE))
        self.switch_error_layout.addWidget(self.page_idx_label)
        self.switch_error_layout.addStretch(2)
        # pin button
        self.pin_button = QPushButton(QIcon(":/pin.svg"), "")
        self.pin_button.resize(QSize(18, 18))
        self.pin_button.setCheckable(True)
        self.pin_button.setStyleSheet("QPushButton {background-color: transparent; border: none; color: white;}")
        self.pin_button.setIconSize(self.pin_button.size())

        self.switch_error_layout.addWidget(self.pin_button)
        self.switch_error_layout.addWidget(self.back_btn)
        self.switch_error_layout.addWidget(self.next_btn)
        self.back_btn.setDisabled(len(self.validation_result_list) <= 1)
        self.next_btn.setDisabled(len(self.validation_result_list) <= 1)
        self.set_slot_function()

        # error title
        first_validation_result = self.validation_result_list[0]
        self.title_icon = QLabel()
        self.title_icon.setPixmap(self.get_validation_icon(first_validation_result).pixmap(PIXMAP_SIZE, PIXMAP_SIZE))
        summary = first_validation_result.get("summary", "")
        self.title_label = QLabel(f"{summary}")
        self.title_label.setFont(QFont("Microsoft YaHei", TITLE_FONT_SIZE))
        self.title_label.setWordWrap(True)
        title_layout = QHBoxLayout()
        title_layout.addWidget(self.title_icon)
        title_layout.addWidget(self.title_label)
        title_layout.setStretch(0, 1)
        title_layout.setStretch(1, 20)

        # validation mark and hint message
        validation_mark = first_validation_result.get("validation_mark", "")
        self.validation_mark_label = QLabel(f"ID = {validation_mark}")
        self.validation_mark_label.setFont(QFont("Microsoft YaHei", TITLE_FONT_SIZE))

        message = first_validation_result.get("message", "")
        self.hint_message_label = QLabel(f"    {message}")
        self.hint_message_label.setFont(QFont("Microsoft YaHei", BODY_FONT_SIZE))
        self.hint_message_label.setWordWrap(True)

        # proposed solution info area
        self.proposed_layout = self.get_proposed_solution_layout(first_validation_result)
        # related item ecuc path area
        self.related_item_layout = self.get_related_item_layout(first_validation_result)

        self.main_layout = QVBoxLayout(self)
        if self.switch_error_layout:
            self.main_layout.addLayout(self.switch_error_layout)
        self.main_layout.addLayout(title_layout)
        self.main_layout.addWidget(self.validation_mark_label)
        self.main_layout.addWidget(self.hint_message_label)
        if self.proposed_layout:
            self.main_layout.addLayout(self.proposed_layout)
        if self.related_item_layout:
            self.main_layout.addLayout(self.related_item_layout)

        self.main_layout.addStretch(1)
        # no window title
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAutoRaise(True)
        screen_geometry = QGuiApplication.primaryScreen().geometry()
        self.setMinimumSize(
            int(screen_geometry.width() * WIDGET_SIZE_WIDTH_FACTOR),
            int(screen_geometry.height() * WIDGET_SIZE_HEIGHT_FACTOR),
        )

        self.setStyleSheet(
            """
            QToolButton { background-color: rgb(245, 245, 245); border: 1px solid #5f5f5f; border-radius: 4px; }
            QToolButton:hover { background-color: rgb(245, 245, 245); border: 1px solid #5f5f5f; }
            QToolButton:pressed { background-color: rgb(245, 245, 245); border: 1px solid #5f5f5f; }
        """
        )

        self.oldPos = self.pos()

    def set_slot_function(self):
        self.next_btn.clicked.connect(lambda: self.refresh_window_slot(is_next=True))
        self.back_btn.clicked.connect(lambda: self.refresh_window_slot(is_next=False))
        self.pin_button.toggled.connect(self.pin_button_toggled_slot)

    def refresh_window_slot(self, is_next: bool):
        if is_next:
            self.error_idx = (self.error_idx + 1) % len(self.validation_result_list)
        else:
            self.error_idx = (len(self.validation_result_list) - 1) if self.error_idx == 0 else self.error_idx - 1
        self.page_idx_label.setText(f"{self.error_idx + 1}/{len(self.validation_result_list)} items")
        self.refresh_window_info(self.validation_result_list[self.error_idx])

    def _create_lambda(self, auto_solve_dict, param_path):
        return lambda: OneClickSolveHandler.one_click_auto_solve_logic(
            self.main_window.over_view_ui, self.call_back, auto_solve_dict, param_path
        )

    def add_solution_widget(self, propose_layout, solve_list, param_path, is_auto=True):
        for solve_info in solve_list:
            if not solve_info:
                continue
            if is_auto:
                propose_text = "[auto solve]：" + solve_info.get("solve_info", "")
                propose_label = ClickableLabel(
                    propose_text, is_propose=True, clicked_function=self._create_lambda(solve_info, param_path)
                )
            else:
                propose_label = QLabel()
                propose_label.setText(f"    [manual solve]：{solve_info}")
            propose_label.setWordWrap(True)
            propose_layout.addWidget(propose_label)

    def get_proposed_solution_layout(self, validation_result):
        propose_layout = QVBoxLayout()
        propose_title_label = QLabel("Proposed Solution")
        propose_title_label.setFont(QFont("Microsoft YaHei", TITLE_FONT_SIZE))
        propose_layout.addWidget(propose_title_label)

        auto_solve_list = validation_result.get("auto_solve_list", [])
        manual_solve_list = validation_result.get("manual_solve_list", [])
        param_path = validation_result.get("path", [""])[0]
        self.add_solution_widget(propose_layout, auto_solve_list, param_path, is_auto=True)
        self.add_solution_widget(propose_layout, manual_solve_list, param_path, is_auto=False)

        return propose_layout if propose_layout.count() > 1 else None

    def get_related_item_layout(self, validation_result):

        def __create_lambda(basic_ui_handler, item_str: str):
            return lambda: basic_ui_handler.ecuc_path_jumps_to_ui(item_str)

        relate_item_layout = None
        for item_str in validation_result.get("path", []):
            if not relate_item_layout:
                relate_item_layout = QVBoxLayout()
                propose_title_label = QLabel("Related Item")
                propose_title_label.setFont(QFont("Microsoft YaHei", TITLE_FONT_SIZE))
                relate_item_layout.addWidget(propose_title_label)
            relate_item_label = ClickableLabel(
                related_item=item_str,
                is_propose=False,
                clicked_function=__create_lambda(self.main_window.basic_ui_handler, item_str),
            )
            relate_item_layout.addWidget(relate_item_label)
        return relate_item_layout

    def refresh_window_info(self, validation_result):

        def __remove_child_layout_widget(layout):
            for i in reversed(range(layout.count())):
                widget = layout.itemAt(i).widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    layout.removeItem(layout.itemAt(i))
            self.main_layout.removeItem(layout)

        self.title_icon.setPixmap(self.get_validation_icon(validation_result).pixmap(PIXMAP_SIZE, PIXMAP_SIZE))
        summary = validation_result.get("summary", "")
        self.title_label.setText(f"{summary}")
        validation_mark = validation_result.get("validation_mark", "")
        self.validation_mark_label.setText(f"ID = {validation_mark}")
        message = validation_result.get("message", "")
        self.hint_message_label.setText(f"    {message}")

        # remove stretch
        stretch_index = self.main_layout.count() - 1
        item = self.main_layout.itemAt(stretch_index)
        if item.spacerItem() is not None:
            self.main_layout.setStretch(stretch_index, 0)
            self.main_layout.removeItem(item)

        if self.proposed_layout:
            __remove_child_layout_widget(self.proposed_layout)
        if self.related_item_layout:
            __remove_child_layout_widget(self.related_item_layout)

        # proposed solution info area
        self.proposed_layout = self.get_proposed_solution_layout(validation_result)
        # related item ecuc path area
        self.related_item_layout = self.get_related_item_layout(validation_result)
        if self.proposed_layout:
            self.main_layout.addLayout(self.proposed_layout)
        if self.related_item_layout:
            self.main_layout.addLayout(self.related_item_layout)

        self.main_layout.addStretch(1)
        self.update()

    def get_validation_icon(self, validation_result):
        try:
            validation_level_code = validation_result.get("validation_mark", "")
            validation_level_code = validation_level_code[VALIDATION_LEVEL_BIT : (VALIDATION_LEVEL_BIT + 1)]
        except BaseException:
            validation_level_code = 0
        if validation_level_code == "0":
            return QIcon(":/unavailable.svg")
        elif validation_level_code == "1":
            return QIcon(":/validate.png")
        else:
            return QIcon(":/attention_info.svg")

    def pin_button_toggled_slot(self, checked):
        if checked:
            self.enter_timer.stop()
            self.leave_timer.stop()
            self.pin_button.setStyleSheet(
                """
                QPushButton {background-color: rgb(200, 200, 200); border: none; color: white;}"""
            )
        else:
            self.pin_button.setStyleSheet("QPushButton {background-color: transparent; border: none; color: white;}")

    def get_pin_window_on(self) -> bool:
        return self.pin_button.isChecked()

    def set_timer_event(self):
        self.enter_timer = QTimer(self)
        self.enter_timer.setInterval(3000)
        self.enter_timer.timeout.connect(self.close)
        self.enter_timer.start()

        self.leave_timer = QTimer(self)
        self.leave_timer.setInterval(500)
        self.leave_timer.timeout.connect(self.close)

    def enterEvent(self, event):
        self.enter_timer.stop()
        self.leave_timer.stop()

    def leaveEvent(self, event):
        if not self.get_pin_window_on():
            self.leave_timer.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(
                self.x() + (event.globalPos().x() - self.oldPos.x()),
                self.y() + (event.globalPos().y() - self.oldPos.y()),
            )
            self.oldPos = event.globalPos()
            event.accept()

    def window_hold_on(self):
        self.enter_timer.stop()
        self.leave_timer.stop()

    def window_hold_off(self):
        self.leave_timer.start()
