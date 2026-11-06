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
from typing import Any, Optional
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QSpacerItem, QSizePolicy
from PySide6.QtCore import QAbstractItemModel, QObject, Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QBrush, QColor
from cfg_gui.widgets.vcos_custom import VcosCustom
from cfg_gui.widgets.table_header_view import ArgQHeaderView
from cfg_gui.widgets.cv_table_view import CvTableView
from cfg_gui.widgets.table_delegate import ContainerOutlineDelegate


def try_to_num(string):
    if string is None:
        return ""
    try:
        i = int(string)
        return i
    except ValueError:
        try:
            f = float(string)
            return f
        except ValueError:
            return string


class ContainerOutlineItem:
    # container name and some parameters and references are combo display role
    combo_tag = "ECUC-ENUMERATION-PARAM-DEF"
    # container name and some parameters and references are check display role
    check_tag = "ECUC-BOOLEAN-PARAM-DEF"
    # container name and some parameters and references are text display role
    display_tag = (
        "SHORT-NAME",
        "ECUC-PARAM-CONF-CONTAINER-DEF",
        "ECUC-INTEGER-PARAM-DEF",
        "ECUC-FLOAT-PARAM-DEF",
        "ECUC-FUNCTION-NAME-DEF",
        "ECUC-STRING-PARAM-DEF",
        "ECUC-REFERENCE-DEF",
        "ECUC-INSTANCE-REFERENCE-DEF",
        "ECUC-CHOICE-REFERENCE-DEF",
        "ECUC-SYMBOLIC-NAME-REFERENCE-DEF",
    )
    # references cannot be edited
    not_editable_tag = ("ECUC-REFERENCE-DEF", "ECUC-INSTANCE-REFERENCE-DEF", "ECUC-SYMBOLIC-NAME-REFERENCE-DEF")

    def __init__(
        self,
        container_val_obj,
        basic_ui_handler,
        update_overview,
        validation_ui,
        callback=None,
        container_item=None,
        over_view_ui=None,
    ):

        self.basic_ui_handler = basic_ui_handler
        self.update_overview = update_overview
        self.validation_ui = validation_ui
        self.callback = callback
        self.container_item = container_item
        self._container_val_obj = container_val_obj
        self.over_view_ui = over_view_ui

    def is_param_ref(self):
        if "SHORT-NAME" == self._container_val_obj[0]["tag"]:
            return False
        else:
            return True

    def display_text(self):
        """
        Return dispaly text of this item
        """

        if self.is_general_display():
            str_list = []
            for obj in self._container_val_obj:
                str_list.append(obj["cfg_value"])
            return ",".join([s.split("/")[-1] for s in str_list if s is not None])
        elif self.is_check():
            return self._container_val_obj[0]["cfg_value"]
        elif self.is_combo():
            return self._container_val_obj[0]["cfg_value"]
        else:
            return None

    def get_combo_list(self):
        item_list = []
        if self._container_val_obj[0]["tag"] in self.combo_tag:
            for liternal_def in self._container_val_obj[0]["enum_item_list"]:
                item_list.append(liternal_def)
        return item_list

    def is_general_display(self):
        if self._container_val_obj[0]["tag"] in self.display_tag:
            return True
        else:
            return False

    def is_check(self):
        if self._container_val_obj[0]["tag"] in self.check_tag:
            return True
        else:
            return False

    def is_combo(self):
        if self._container_val_obj[0]["tag"] in self.combo_tag:
            return True
        else:
            return False

    def is_editable(self):
        """
        Check if the item is editable according to rules:

        1. Whether def_obj has "CfgLock" admin data
        2. Whether data_obj has "AutoDerived" annotation
        3. Whether container has "IsAutomatic" annotation
        4. Whether def_obj is reference
        """
        if self._container_val_obj[0]["tag"] in self.not_editable_tag:
            return False

        return self.get_can_be_edit()

    def get_can_be_edit(self):

        is_editable = True
        if self._container_val_obj[0]["is_lock"] is False:
            if self._container_val_obj[0]["annotation_status"] is False:
                is_editable = False
            elif self._container_val_obj[0]["annotation_status"] is True:
                is_editable = True
            else:
                pass
        else:
            is_editable = False

        return is_editable

    def update_short_name(self, new_value, show_data_dict):

        if len(new_value) == 0:  # Short Name长度不允许为0
            # self.line_box.setText(self.pre_name)
            return
        old_value = show_data_dict["cfg_value"]  # 修改前的值
        final_short_name, bsw_ecuc_dict = self.callback(
            "update_container_short_name_to_ecuc_arxml",
            new_value,
            show_data_dict["cfg_value"],
            show_data_dict["mod_path"],
            show_data_dict["module"],
            show_data_dict["ecuc_path"],
            show_data_dict["tag"],
        )
        # if final_short_name != new_value:
        #     self.line_box.blockSignals(True)
        #     self.line_box.setText(final_short_name)
        #     self.line_box.blockSignals(False)
        # over_view_args = [bsw_mod_dict, bsw_ecuc_dict]
        # self.update_overview(over_view_args)
        self.callback(
            "bsw_editor_update_all_configuration_items_that_reference_this_ref",
            final_short_name,
            show_data_dict["cfg_value"],
            show_data_dict["mod_path"],
            show_data_dict["module"],
            show_data_dict["ecuc_path"],
            show_data_dict["tag"],
        )
        new_ecuc_path = show_data_dict["ecuc_path"].split(show_data_dict["cfg_value"])[0] + final_short_name
        self.update_show_data_dicts_ecuc_path(new_ecuc_path)
        show_data_dict["cfg_value"] = final_short_name
        # 入栈
        self.callback(
            "bsw_editor_container_outline_push_stack",
            "short_name",
            [old_value, new_value],
            self,
            show_data_dict,
            self.callback,
            self.over_view_ui,
            self.basic_ui_handler,
        )

    def update_show_data_dicts_ecuc_path(self, new_ecuc_path):

        for key, show_data in self.container_item.items():
            show_data[0]["ecuc_path"] = new_ecuc_path

    def update_param_or_ref_value(self, new_value, show_data_dict):
        if show_data_dict["has_obj"] is True:
            # show_data_dict中有obj，直接更新
            self.callback(
                "bsw_editor_editing_finished_and_write_to_ecuc_arxml",
                new_value,
                show_data_dict["cfg_value"],
                show_data_dict["mod_path"],
                show_data_dict["module"],
                show_data_dict["ecuc_path"],
                show_data_dict["tag"],
            )
        else:
            # show_data_dict中没有obj，需要创建对象
            self.callback(
                "bsw_editor_add_param_item_and_write_to_ecuc_arxml",
                new_value,
                show_data_dict["mod_path"],
                show_data_dict["module"],
                show_data_dict["ecuc_path"],
                show_data_dict["tag"],
            )
        old_value = show_data_dict["cfg_value"]  # 修改前的值
        show_data_dict["cfg_value"] = new_value

        # Validation
        self.basic_validation_handler(show_data_dict)
        self.validation_ui.validation_model.update_model_data()
        # 入栈
        self.callback(
            "bsw_editor_container_outline_push_stack",
            "param",
            [old_value, new_value],
            self,
            show_data_dict,
            self.callback,
            self.over_view_ui,
            self.basic_ui_handler,
        )

    def basic_validation_handler(self, show_data_dict):
        cbk_param = {}
        cbk_param["param_name"] = show_data_dict["label_name"]
        cbk_param["check_text"] = show_data_dict["cfg_value"]
        cbk_param["param_path"] = show_data_dict["ecuc_path"] + "/" + show_data_dict["label_name"]
        cbk_param["tag"] = show_data_dict["tag"]
        cbk_param["lower_multiplicity"] = show_data_dict["lower_multiplicity"]
        cbk_param["upper_multiplicity"] = show_data_dict["upper_multiplicity"]
        cbk_param["upper_multiplicity_infinite"] = show_data_dict["upper_multiplicity_infinite"]
        cbk_param["is_necessary"] = show_data_dict["is_necessary"]
        cbk_param["max_value"] = show_data_dict["max_value"]
        cbk_param["min_value"] = show_data_dict["min_value"]
        cbk_param["max_length"] = show_data_dict["max_length"]
        cbk_param["min_length"] = show_data_dict["min_length"]
        self.callback("validation_param", cbk_param)

    def modify_value(self, new_value):

        if new_value == self._container_val_obj[0]["cfg_value"]:
            # 如果new value与old value相同，直接退出
            return
        if "SHORT-NAME" == self._container_val_obj[0]["tag"]:
            self.update_short_name(new_value, self._container_val_obj[0])
            return
        # elif len(self._data_obj_list) > 1:
        #     logger.warning(f"Unsupported multi instance param/ref value obj: {get_short_name(self._def_obj)}")
        else:
            self.update_param_or_ref_value(new_value, self._container_val_obj[0])


class WidgetSortFilterProxyModel(QSortFilterProxyModel):

    def __init__(self, init_phase=None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # 初始化状态变量
        self.init_phase = init_phase
        self.hide_if_used_checked = False
        self.hide_if_incompatible_checked = False

        # List storing which rows are selected
        self.row_selection_list = []

    def setSourceModel(self, sourceModel: QAbstractItemModel) -> None:
        # At the beginning, select all rows
        self.row_selection_list = [Qt.CheckState.Checked] * sourceModel.rowCount()
        return super().setSourceModel(sourceModel)

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        if not left.isValid() or not right.isValid():
            return False

        left_value = left.data(Qt.ItemDataRole.DisplayRole)
        right_value = right.data(Qt.ItemDataRole.DisplayRole)
        if not isinstance(l_num := try_to_num(left_value), str) and not isinstance(
            r_num := try_to_num(right_value), str
        ):
            return l_num < r_num
        else:
            return super().lessThan(left, right)

    def update_rows(self, row_selection_list):
        """
        Update row selection and refresh table UI
        """
        self.row_selection_list = row_selection_list
        self.invalidateFilter()

    def set_hide_if_used_checked(self, checked):
        self.hide_if_used_checked = checked
        self.invalidateFilter()

    def set_hide_if_incompatible_checked(self, checked):
        self.hide_if_incompatible_checked = checked
        self.invalidateFilter()

    def select_visible_rows(self, checked_state):
        # 只遍历由当前过滤器显示的行
        source_model = self.sourceModel()
        if not source_model:
            return

        # 获取代理模型的行数并更新行选中状态
        for row in range(self.rowCount()):
            # mapToSource 将代理模型坐标映射到源模型坐标
            source_index = self.mapToSource(self.index(row, 0))
            if source_index.isValid():
                source_row = source_index.row()
                source_model.update_row_check_state(source_row, checked_state)

    def deselect_visible_rows(self):
        # 只遍历由当前过滤器显示的行
        source_model = self.sourceModel()
        if not source_model:
            return

        # 获取代理模型的行数并更新行选中状态
        for row in range(self.rowCount()):
            source_index = self.mapToSource(self.index(row, 0))  # 代理模型坐标映射到源模型坐标
            if source_index.isValid():
                source_row = source_index.row()
                source_model.update_row_check_state(source_row, Qt.Unchecked)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        source_model = self.sourceModel()
        if self.row_selection_list and self.row_selection_list[source_row] != Qt.CheckState.Checked:
            return False
        # 如果启用了“Hide If Used”过滤
        if self.hide_if_used_checked:
            already_used_in_col_index = self.get_column_index("Already Used In", source_model)
            if already_used_in_col_index >= 0:
                value = source_model.index(source_row, already_used_in_col_index, source_parent).data()
                if value:  # 如果该列有值，则不显示该行
                    return False

        # 如果启用了“Hide If Incompatible”过滤
        if self.hide_if_incompatible_checked:
            init_phase_col_index = self.get_column_index("Init Phase", source_model)
            if init_phase_col_index >= 0:
                value = source_model.index(source_row, init_phase_col_index, source_parent).data()
                if value != self.init_phase:  # 如果该列的值不匹配初始化阶段，则不显示该行
                    return False

        # 如果启用了文本过滤
        filter_text = self.filterRegularExpression().pattern().strip().lower()
        if filter_text:
            # 遍历所有列来检查是否匹配过滤文本
            for column in range(source_model.columnCount()):
                index = source_model.index(source_row, column, source_parent)
                row_value = str(source_model.data(index, Qt.DisplayRole)).lower()
                if filter_text in row_value:
                    return True  # 文本匹配则显示该行
            return False  # 没有匹配的文本则不显示该行

        # 如果没有启用任何过滤操作，则显示该行
        return True

    # 获取指定列名的列索引
    def get_column_index(self, column_name, source_model):
        for column_index in range(source_model.columnCount()):
            if source_model.headerData(column_index, Qt.Horizontal, Qt.DisplayRole) == column_name:
                return column_index
        return -1


class ContainerOutlineModel(QAbstractTableModel):

    def __init__(
        self,
        container_show_data_list,
        basic_ui_handler,
        update_overview,
        validation_ui,
        callback=None,
        parent=None,
        over_view_ui=None,
    ) -> None:
        super().__init__(parent)
        self.callback = callback
        self.basic_ui_handler = basic_ui_handler
        self.update_overview = update_overview
        self.validation_ui = validation_ui
        self.over_view_ui = over_view_ui
        self.head_data = []
        self.container_show_data_list = container_show_data_list
        self.row_count = self.get_row_count(self.container_show_data_list)
        self.column_count = self.get_column_count(self.container_show_data_list)
        self.get_head_data()
        self.table_items = self.init_table_item()

    def get_row_count(self, container_show_data_list):
        return len(container_show_data_list)

    def get_column_count(self, container_show_data_list):
        if self.row_count > 0:
            return len(container_show_data_list[0])
        else:
            return 0

    def get_head_data(self):
        if self.row_count > 0:
            for key, param_item in self.container_show_data_list[0].items():
                self.head_data.append(param_item[0]["label_name"])

    def init_table_item(self):
        table_items = []
        for container_item in self.container_show_data_list:
            container_row = []

            for param_label_name, param_item in container_item.items():
                container_row.append(
                    ContainerOutlineItem(
                        param_item,
                        self.basic_ui_handler,
                        self.update_overview,
                        self.validation_ui,
                        self.callback,
                        container_item,
                        over_view_ui=self.over_view_ui,
                    )
                )

            table_items.append(container_row)

        return table_items

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return self.row_count

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return self.column_count

    def data(self, index: QModelIndex, role: int = ...) -> Any:
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        target_item: ContainerOutlineItem = self.table_items[index.row()][index.column()]

        if role == VcosCustom.ItemDataRole.ComboBoxItemsRole:
            if target_item.is_combo():
                return target_item.get_combo_list()
            else:
                return []

        if role == Qt.ItemDataRole.DisplayRole:
            return target_item.display_text()

        if role == Qt.ItemDataRole.EditRole:
            if target_item.is_check():
                return VcosCustom.EditorWidget.CheckBoxEditor
            elif target_item.is_combo():
                return VcosCustom.EditorWidget.ComboBoxEditor
            else:
                return None
        if role == Qt.ItemDataRole.ForegroundRole:
            if not target_item.is_editable():
                return QBrush(QColor(160, 160, 160))

    def is_valid_value(self, index, value):
        """
        Check if the value is valid to be set according to:

        1. CheckBox cell only accepts "true" or "false"
        2. ComboBox cell only accepts its items
        """
        if index.data(Qt.ItemDataRole.EditRole) == VcosCustom.EditorWidget.CheckBoxEditor:
            return value in ("true", "false")
        elif index.data(Qt.ItemDataRole.EditRole) == VcosCustom.EditorWidget.ComboBoxEditor:
            valid_val_list = index.data(VcosCustom.ItemDataRole.ComboBoxItemsRole)
            return value in valid_val_list
        else:
            return True

    def setData(self, index: QModelIndex, value: Any, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole and self.is_valid_value(index, value):
            target_item: ContainerOutlineItem = self.table_items[index.row()][index.column()]
            target_item.modify_value(value)
            self.dataChanged.emit(index, index)
            return True
        else:
            return super().setData(index, value, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        flags = super().flags(index)
        flags |= Qt.ItemFlag.ItemIsSelectable
        target_item: ContainerOutlineItem = self.table_items[index.row()][index.column()]

        if target_item.is_editable():
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def index(self, row: int, column: int, parent: QModelIndex = ...) -> QModelIndex:
        return super().index(row, column, parent)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> Any:
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignLeft

        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.head_data[section]
            if orientation == Qt.Orientation.Vertical:
                return None

        return super().headerData(section, orientation, role)

    def get_column_raw_data(self, column: int):
        # Get raw item data of specific row from table items
        return [row[column] for row in self.table_items]


class ContainerOutlineWidget(QWidget):

    def __init__(self, main_window, container_show_data_dict, callback=None) -> None:
        super().__init__()
        self.main_window = main_window
        self.basic_ui_handler = self.main_window.basic_ui_handler
        self.update_overview = self.main_window.over_view_ui.update_overview
        self.validation_ui = self.main_window.validation_ui
        self.callback = callback
        self.model = ContainerOutlineModel(
            container_show_data_dict,
            self.basic_ui_handler,
            self.update_overview,
            self.validation_ui,
            self.callback,
            over_view_ui=self.main_window.over_view_ui,
        )
        self.sort_proxy_model = WidgetSortFilterProxyModel()
        self.table_view = CvTableView(self, self.model, self.callback)
        self.delegate = ContainerOutlineDelegate(self.table_view)
        self.horizontal_header_view = ArgQHeaderView(Qt.Orientation.Horizontal, self.table_view)
        self.init_table()
        self.general_layout = QHBoxLayout()
        self.init_layout()

    def init_table(self):
        self.sort_proxy_model.setSourceModel(self.model)
        self.table_view.setModel(self.sort_proxy_model)
        self.table_view.setItemDelegate(self.delegate)
        self.table_view.setHorizontalHeader(self.horizontal_header_view)
        self.table_view.setSortingEnabled(True)
        self.horizontal_header_view.set_sort_indicator_clearable(True)

    def init_layout(self):
        # Button region layout
        button_layout = QVBoxLayout()
        add_button = QPushButton("Add")
        dup_button = QPushButton("Dup")
        del_button = QPushButton("Del")
        add_button.setEnabled(False)
        dup_button.setEnabled(False)
        del_button.setEnabled(False)
        button_layout.addWidget(add_button)
        button_layout.addWidget(dup_button)
        button_layout.addWidget(del_button)
        button_layout.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Fixed, QSizePolicy.Expanding))

        # General layout
        self.general_layout.addLayout(button_layout)
        self.general_layout.addWidget(self.table_view)
        self.setLayout(self.general_layout)
