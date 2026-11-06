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
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QLayout
from cfg_gui.widgets.widget import ArgQWidget
from cfg_gui.widgets.check_box import ArgQCheckBox
from cfg_gui.widgets.combo_box import ArgQComboBox
from cfg_gui.widgets.line_edit import ArgQLineEdit
from cfg_gui.widgets.tree_view import ArgQTreeView, ArgQTreeModel
from func_module.health_monitor.logger import logger
from func_module.module_management.linkage.linkage_func import SetMethod

MODUEL_NAME_INDEX = 1


class BasicUIHandler:

    def __init__(self, mainwindow, parent=None):
        self.mainwindow = mainwindow

    def ecuc_path_jumps_to_ui(self, path):
        if path is None:
            return

        index_list = list(filter(lambda x: x.strip() != "", path.split("/")))
        if "ActiveEcuC" not in index_list:
            return

        autosar_tab_name = self.mainwindow.tabWidget.currentWidget().objectName()
        if autosar_tab_name == "vcos_rte":
            self.mainwindow.tabWidget.setCurrentWidget(self.mainwindow.vcos_bsw)
        bsw_module_name = index_list[MODUEL_NAME_INDEX]
        tab_name = index_list[MODUEL_NAME_INDEX]
        bsw_tab_widget = self.mainwindow.bswTabWidget
        if tab_name not in self.mainwindow.over_view_ui.bsw_cfg_view_dict:
            if not self.mainwindow.over_view_ui.add_bsw_module_view({bsw_module_name}, tab_name):
                return
        module_cfg_view = self.mainwindow.over_view_ui.bsw_cfg_view_dict[tab_name]
        tab_index = bsw_tab_widget.indexOf(module_cfg_view)
        if tab_index == -1:
            bsw_tab_widget.addTab(module_cfg_view, tab_name)
        tab_index = bsw_tab_widget.indexOf(module_cfg_view)
        bsw_tab_widget.setCurrentIndex(tab_index)
        tree_view: ArgQTreeView = module_cfg_view.findChild(ArgQTreeView)
        tree_model: ArgQTreeModel = tree_view.model()
        cur_index = self.find_index_by_name_path(tree_model, index_list[1:])
        tree_view.setCurrentIndex(QModelIndex())
        tree_view.clicked.emit(QModelIndex())
        tree_view.setCurrentIndex(cur_index)
        tree_view.clicked.emit(tree_view.currentIndex())

    @classmethod
    def find_index_by_name_path(cls, model: ArgQTreeModel, name_path: list, parent=QModelIndex()):
        if len(name_path) == 0:
            return parent
        for row in range(model.rowCount(parent)):
            index = model.index(row, 0, parent)
            name = index.data()
            path = index.internalPointer().get_path()
            if path == "#" and (name == name_path[0] or name[:-3] == name_path[0]):
                child = cls.find_index_by_name_path(model, name_path, index)
                if child.isValid():
                    return child
                else:
                    return index
            if name == name_path[0]:
                child = cls.find_index_by_name_path(model, name_path[1:], index)
                if child.isValid():
                    return child
                else:
                    return index
            if path != "#":
                continue
            if model.hasChildren(index):
                child = cls.find_index_by_name_path(model, name_path, index)
                if child.isValid():
                    return child
        return QModelIndex()

    @classmethod
    def linked_cfg_item_set_value(
        cls, item_widget, data, module_name, linked_show_data_dict, callback, is_locked, updated_path_dict
    ):
        """
        根据set_value对UI对象进行修改
        item_widget:配置项的控件对象
        data:被联动配置项要设置的数据值
        module_name:入口配置项模块
        linked_show_data_dict:被联动配置项的show_data_dict
        callback:中间件回调机制
        is_locked:被联动配置项是否锁定(置灰)
        updated_path_dict:联动链上的配置项路径
        """
        item_widget.linked_flag = True  # 表示控件是被联动的,避免彼此无限联动
        item_widget.undo_module_name = module_name  # 撤销入栈的模块=入口配置项模块
        item_widget.updated_path_dict = updated_path_dict
        item_widget.blockSignals(True)

        admin_lock: bool = False
        admin_data = callback("bsw_editor_get_admin_data", module_name, linked_show_data_dict["mod_path"])
        if admin_data is not None:
            for _ in admin_data:
                if ("VCOS:CfgLock" in _) and (_["VCOS:CfgLock"] == "true"):
                    admin_lock = True

        # 修改is_lock(置灰)
        if (is_locked is not None) and (linked_show_data_dict["is_lock"] != is_locked) and (admin_lock is False):
            item_widget.modify_lock_flag = True  # 是否修改is_lock
            item_widget.is_lock = item_widget.show_data_dict["is_lock"] = is_locked
            item_widget.ashes_and_locks()
            if item_widget.is_lock is True:
                callback(
                    "bsw_editor_set_is_lock",
                    None,
                    linked_show_data_dict["mod_path"],
                    linked_show_data_dict["module"],
                    linked_show_data_dict["ecuc_path"],
                    linked_show_data_dict["tag"],
                )
            else:
                callback(
                    "bsw_editor_remove_is_lock",
                    None,
                    linked_show_data_dict["mod_path"],
                    linked_show_data_dict["module"],
                    linked_show_data_dict["ecuc_path"],
                    linked_show_data_dict["tag"],
                )

        # 修改数值
        if item_widget.show_data_dict["cfg_value"] != data:
            if isinstance(item_widget, ArgQCheckBox):
                value_table = {
                    "true": Qt.Checked,
                    "false": Qt.Unchecked,
                }
                item_widget.box.blockSignals(True)
                if data in value_table:
                    item_widget.box.setCheckState(value_table[data])
                    item_widget.onStateChanged(None)
                else:
                    item_widget.box.setCheckState(item_widget.box.checkState())
                    logger.error(
                        f"ERROR: {linked_show_data_dict['mod_path']} "
                        f'can not be set "{data}",it must be "true" or "false".'
                    )
                item_widget.box.blockSignals(False)
            elif isinstance(item_widget, ArgQLineEdit):
                item_widget.line_box.blockSignals(True)
                item_widget.line_box.setText(data)
                if data == "":
                    item_widget.on_input_empty_slot()
                else:
                    item_widget.editing_finished_slot()
                item_widget.line_box.blockSignals(False)
            elif isinstance(item_widget, ArgQComboBox):
                item_widget.item_box.blockSignals(True)
                if item_widget.item_box.findText(data) >= 0:
                    item_widget.item_box.setCurrentText(data)
                    item_widget.on_text_changed_slot(data)
                else:
                    item_widget.on_text_changed_slot(item_widget.item_box.currentText())
                    logger.error(f"ERROR: {linked_show_data_dict['mod_path']} can not be set \"{data}\".")
                item_widget.item_box.blockSignals(False)

        item_widget.blockSignals(False)
        item_widget.linked_flag = False
        del item_widget.updated_path_dict
        item_widget.modify_lock_flag = False

    @classmethod
    def update_linked_cfg_item(cls, instance_info_list, updated_path_dict, callback, main_window):
        """
        实例化配置项UI对象,根据set_method对配置项进行修改
        instance_info_list:需要修改的配置项信息列表
        updated_path_dict:联动链上的配置项路径
        callback:中间件回调机制
        main_window:主窗口
        """
        overview_ui = main_window.over_view_ui

        for item in instance_info_list:
            linked_show_data, linked_mod_path, data, module_name, is_locked = (
                item[0],
                item[1],
                item[2],
                item[3],
                item[4],
            )
            linked_show_data_dict = linked_show_data[linked_mod_path][0]
            linked_container_ecuc_path = linked_show_data_dict["ecuc_path"]
            ecuc_path_list = list(filter(lambda x: x.strip() != "", linked_container_ecuc_path.split("/")))
            # 1.配置项对象已存在,直接修改对象
            if ecuc_path_list[1] in overview_ui.bsw_cfg_view_dict:
                module_cfg_view = overview_ui.bsw_cfg_view_dict[ecuc_path_list[1]]
                tree_view: ArgQTreeView = module_cfg_view.findChild(ArgQTreeView)
                all_layouts = list(
                    filter(
                        lambda item: (hasattr(item, "show_data_dict"))
                        and (item.show_data_dict["ecuc_path"] == linked_container_ecuc_path)
                        and (item.show_data_dict["mod_path"] == linked_mod_path),
                        tree_view.param_scroll_area.widget().findChildren(QLayout),
                    )
                )
                if len(all_layouts) != 0:
                    item_widget = all_layouts[0]
                    cls.linked_cfg_item_set_value(
                        item_widget, data, module_name, linked_show_data_dict, callback, is_locked, updated_path_dict
                    )
                    logger.info(f"{linked_container_ecuc_path}/{linked_mod_path.split('/')[-1]} is set '{str(data)}'.")
                    continue
            # 2.配置项对象不存在,先实例化再修改
            param_widget = ArgQWidget(main_window, linked_show_data, "/", callback)
            all_layouts = param_widget.findChildren(QLayout)
            for item_widget in all_layouts:
                if (
                    hasattr(item_widget, "show_data_dict")
                    and ("mod_path" in item_widget.show_data_dict)
                    and (item_widget.show_data_dict["mod_path"] == linked_mod_path)
                ):
                    cls.linked_cfg_item_set_value(
                        item_widget, data, module_name, linked_show_data_dict, callback, is_locked, updated_path_dict
                    )
                    break
            param_widget.deleteLater()

            # 打印输出联动配置的情况
            logger.info(f"{linked_container_ecuc_path}/{linked_mod_path.split('/')[-1]} is set '{str(data)}'.")

    @classmethod
    def update_linked_arxml_item(cls, module_name, arxml_info_list, data_management):
        """
        创建/删除整个container
        arxml_info_list:被联动的arxml配置项信息列表
        """
        for _ in arxml_info_list:
            container_ecuc_path, linked_mod_path, set_method_name = _[0], _[1], _[2]

            set_method_func = SetMethod.get_method(module_name, set_method_name)
            if set_method_func is None:
                continue
            set_method_func(container_ecuc_path, linked_mod_path, data_management)
