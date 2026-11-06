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
import json
import typing
from threading import Lock
from typing import Any, List, Union
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QSizePolicy, QAbstractScrollArea, QMessageBox


class ScheduleTableModel(QtCore.QAbstractTableModel):

    def __init__(self, parent: QtCore.QObject) -> None:
        super().__init__(parent)
        self.sch_tbl_cfg = {"task_groups": {}}
        self.init_model_data()

    def init_model_data(self, row=6, col=10):
        self.table_data: List[List[Union[str, int]]] = [[""] * row for _ in range(col)]
        self.table_data[0][0] = -1

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self.table_data[-1])

    def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self.table_data)

    def flags(self, index: QtCore.QModelIndex):
        row = index.row()
        col = index.column()
        if col == 0:
            return Qt.ItemFlag.ItemIsEnabled
        if col != 0 and row == 0:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable
        if col > 0 and row > 0:
            if col < len(self.table_data) and row < len(self.table_data[col]):
                if self.table_data[col][row] and not self.in_group(row, col):
                    return (
                        Qt.ItemFlag.ItemIsEnabled
                        | Qt.ItemFlag.ItemIsSelectable
                        | Qt.ItemFlag.ItemIsDragEnabled
                        | Qt.ItemFlag.ItemIsDropEnabled
                    )
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDropEnabled

        return super().flags(index)

    def data(self, index: QtCore.QModelIndex, role: int = ...):
        row = index.row()
        col = index.column()
        if role == Qt.ItemDataRole.TextAlignmentRole and row != 0 and col == 0:
            return Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter
        if role == Qt.ItemDataRole.BackgroundRole:
            if row > 0 and col > 0 and self.table_data[col][row]:
                if not self.in_group(row, col):
                    return None
                group = self.get_group(row, col)
                if group % 2 == 1:
                    return QColor(Qt.GlobalColor.lightGray)
                else:
                    return QColor(Qt.GlobalColor.gray)
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return None
        if row == col == 0:
            return "Task Offset"
        if row == 1 and col == 0:
            return "Task Name"
        if row >= 0 and col > 0:
            if col < len(self.table_data) and row < len(self.table_data[col]):
                return str(self.table_data[col][row])
            else:
                return None
        return None

    def setData(self, index: QtCore.QModelIndex, value: Any, role: int = ...) -> bool:
        if role != Qt.ItemDataRole.EditRole:
            return False
        row = index.row()
        col = index.column()
        if row == 0:
            if value == "":
                self.table_data[col][row] = ""
                return True
            if not self.is_int(value):
                return False
            value = int(value)
            if value < 0:
                return False
            for row_data in self.table_data:
                if row_data[row] == value:
                    return False
        self.table_data[col][row] = value
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.EditRole, Qt.ItemDataRole.DisplayRole])
        return True

    def insertRow(self, row: int, parent: QtCore.QModelIndex) -> bool:
        return self.insertRows(row, 1, parent)

    def insertRows(self, row: int, count: int, parent: QtCore.QModelIndex) -> bool:
        self.beginInsertRows(parent, row, row + count - 1)
        for v in self.table_data:
            v.insert(row, "")
        self.endInsertRows()
        return True

    def insertColumn(self, column: int, parent: QtCore.QModelIndex) -> bool:
        return self.insertColumns(column, 1, parent)

    def insertColumns(self, column: int, count: int, parent: QtCore.QModelIndex) -> bool:
        self.beginInsertColumns(parent, column, column + count - 1)
        self.table_data.insert(column, ["" for _ in range(len(self.table_data[-1]))])
        self.endInsertColumns()
        return True

    def removeRow(self, row: int, parent: QtCore.QModelIndex = ...) -> bool:
        return self.removeRows(row, 1, parent)

    def removeRows(self, row: int, count: int, parent: QtCore.QModelIndex = ...) -> bool:
        self.beginRemoveRows(parent, row, row + count - 1)
        for i in range(len(self.table_data) - 1, -1, -1):
            row_data = self.table_data[i]
            for j in range(row + count - 1, row - 1, -1):
                del row_data[j]
        self.endRemoveRows()
        return True

    def removeColumn(self, column: int, parent: QtCore.QModelIndex = ...) -> bool:
        return self.removeColumns(column, 1, parent)

    def removeColumns(self, column: int, count: int, parent: QtCore.QModelIndex = ...) -> bool:
        self.beginRemoveColumns(parent, column, column + count - 1)
        for i in range(column + count - 1, column - 1, -1):
            del self.table_data[i]
        self.endRemoveColumns()
        return True

    def supportedDragActions(self):
        return Qt.DropAction.MoveAction

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction

    def mimeTypes(self):
        return ["text/plain"]

    def mimeData(self, indexes: typing.List[QtCore.QModelIndex]) -> QtCore.QMimeData:
        mime_data = QtCore.QMimeData()
        if not indexes:
            return mime_data
        row = indexes[-1].row()
        col = indexes[-1].column()
        if self.in_group(col, row):
            return mime_data
        coord = {"row": row, "col": col}
        mime_data.setText(json.dumps(coord))
        return mime_data

    def dropMimeData(
        self, data: QtCore.QMimeData, action: Qt.DropAction, row: int, column: int, parent: QtCore.QModelIndex
    ) -> bool:
        if action != Qt.DropAction.MoveAction:
            return False
        coord = json.loads(data.text())
        col = coord["col"]
        row = coord["row"]
        if col < len(self.table_data) and row < len(self.table_data[col]):
            if parent.data():
                self.set_group(row, col, self.get_group(parent.row(), parent.column()))
            else:
                self.delete_group(row, col)
            value = self.table_data[col][row]
            self.table_data[col][row] = parent.data()
            self.setData(parent, value, Qt.ItemDataRole.EditRole)
            group = self.get_group(row, col)
            parent_row = parent.row() if group == -1 else group
            self.add_group(parent_row, parent_row + 1, parent.column())
            return True
        else:
            return False

    def update_model_data(self, task_offset_list, sch_tbl_cfg):
        self.sch_tbl_cfg.update(sch_tbl_cfg)
        if not task_offset_list:
            return False
        row = self.rowCount()
        max_row = max(max([len(v) for v in task_offset_list]), row)
        table_data = [v + [""] * (max_row - len(v)) for v in task_offset_list]
        if not sch_tbl_cfg.get("task_groups"):
            task_groups = {vv: v.index(vv) for v in task_offset_list for vv in v[1:] if vv}
        else:
            task_groups = sch_tbl_cfg["task_groups"]
            self.update_task_groups(task_offset_list, task_groups)
        self.beginResetModel()
        self.init_model_data(max_row)
        self.table_data[1 : len(table_data) + 1] = table_data
        self.sch_tbl_cfg["task_groups"] = task_groups
        self.endResetModel()
        return True

    def update_task_groups(self, task_offset_list, task_groups):
        task_first_list = {task_list[1]: task_list[1:] for task_list in task_offset_list}
        for task_name, task_list in task_first_list.items():
            if task_name not in task_groups:
                continue
            index = 1
            previous_group = -1
            for task_name in task_list:
                if task_name not in task_groups:
                    continue
                if previous_group == -1:
                    previous_group = task_groups[task_name]
                    task_groups[task_name] = index
                else:
                    if previous_group == task_groups[task_name]:
                        task_groups[task_name] = index
                    else:
                        index += 1
                        previous_group = task_groups[task_name]
                        task_groups[task_name] = index

    def sort_first_row(self):
        self.beginResetModel()
        self.table_data.sort(key=lambda x: (0, x[0]) if isinstance(x[0], int) else (1,))
        self.endResetModel()

    def get_used_task(self):
        return {
            task_name
            for task_names in self.table_data
            for task_name in task_names
            if task_name != ""
            if not isinstance(task_name, int)
        }

    def get_sch_tbl_ui_cfg(self):
        if not self.sch_tbl_cfg:
            return {}
        if not self.sch_tbl_cfg.get("name") or not self.sch_tbl_cfg.get("counter_ref"):
            return {}
        for row in self.table_data[1:]:
            if isinstance(row[0], int) and set(row[1:]) == {""}:
                QMessageBox(
                    QMessageBox.Icon.Warning, "Warning", "调度表有未配置的任务偏移，请检查!", parent=self.parent()
                ).show()
                return {}
        task_offset_table = {
            task_name: row[0]
            for row in self.table_data[1:]
            for task_name in row[1:]
            if isinstance(row[0], int)
            if task_name != ""
        }
        sch_tbl_ui_cfg = {
            "name": self.sch_tbl_cfg["name"],
            "task_offset_table": task_offset_table,
            "counter_ref": self.sch_tbl_cfg["counter_ref"],
        }
        return sch_tbl_ui_cfg

    def get_sch_tbl_ui_data(self):
        table_data = self.table_data[1:]
        return table_data, self.sch_tbl_cfg

    def is_int(self, str):
        try:
            int(str)
            return True
        except ValueError:
            return False

    def set_group(self, row, col, group, block_signal=False):
        if (
            col > 0
            and col < len(self.table_data)
            and row > 0
            and row < len(self.table_data[col])
            and self.table_data[col][row]
        ):
            self.sch_tbl_cfg["task_groups"][self.table_data[col][row]] = group
        if not block_signal:
            index = self.index(row, col)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.BackgroundRole])

    def get_group(self, row, col):
        if (
            col > 0
            and col < len(self.table_data)
            and row > 0
            and row < len(self.table_data[col])
            and self.table_data[col][row]
        ):
            task_groups = self.sch_tbl_cfg["task_groups"]
            return task_groups.get(self.table_data[col][row], -1)
        else:
            return -1

    def in_group(self, row, col):
        group = self.get_group(row, col)
        group_front = self.get_group(row - 1, col)
        group_back = self.get_group(row + 1, col)
        if group == group_front != -1 or group == group_back != -1:
            return True
        else:
            return False

    def refresh_group(self, row_start, value, block_signal=False):
        if not block_signal:
            self.beginResetModel()
        for col in range(1, self.columnCount()):
            for row in range(row_start, self.rowCount()):
                group = self.get_group(row, col)
                if group == -1:
                    continue
                self.set_group(row, col, group + value, True)
        if not block_signal:
            self.endResetModel()

    def add_group(self, row_start, row_end, col):
        group = 0
        for row in range(row_start - 1, 0, -1):
            if self.table_data[col][row]:
                group = self.get_group(row, col) + 1
                break
        self.beginResetModel()
        for row in range(row_start, self.rowCount()):
            if row < row_end:
                if group == 0:
                    self.set_group(row, col, group + 1, True)
                else:
                    self.set_group(row, col, group, True)
            else:
                group = self.get_group(row, col)
                group += row_start - row_end + 1
                self.set_group(row, col, group, True)
        self.endResetModel()

    def remove_group(self, row, col):
        count = -1
        group_base = self.get_group(row, col)
        self.beginResetModel()
        for row in range(group_base, self.rowCount()):
            group = self.get_group(row, col)
            if group == -1:
                continue
            if group == group_base:
                count += 1
            self.set_group(row, col, group + count, True)
        self.endResetModel()

    def delete_group(self, row, col):
        self.beginResetModel()
        self.sch_tbl_cfg["task_groups"].pop(self.table_data[col][row], None)
        for row in range(row + 1, self.rowCount()):
            group = self.get_group(row, col)
            if group == -1:
                continue
            self.set_group(row, col, group - 1, True)
        self.endResetModel()


class SelectReferenceTargetTableWidget(QtWidgets.QTableWidget):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["Task Name", "Mapping Info (Period, Offset)"])
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.setShowGrid(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Fixed)

    def set_data(self, data: typing.Dict[str, dict]):
        self.setRowCount(len(data))
        i = 0
        for task_name, task_mapping_info in data.items():
            runnable_periods = sorted(
                {
                    (
                        int(v["runnable_period"]),
                        float(v["runnable_offset"]),
                    )
                    for v in task_mapping_info
                },
                key=lambda x: (x[0], x[1]),
            )
            info = ", ".join([f"({p}, {o})" for p, o in runnable_periods])
            self.setItem(i, 0, QtWidgets.QTableWidgetItem(task_name))
            self.setItem(i, 1, QtWidgets.QTableWidgetItem(info))
            i += 1


class SelectReferenceTargetDialog(QtWidgets.QDialog):

    def __init__(self) -> None:
        super().__init__()
        self.table_widget = SelectReferenceTargetTableWidget(self)
        self.filter_text_edit = QtWidgets.QLineEdit(self)
        self.select_text = ""
        self.filter_text = ""
        self.init_ui()
        self.init_slot()

    def init_ui(self):
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle("Selectable Os Task Reference Target")
        self.setMinimumSize(800, 482)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint)
        self.table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.filter_text_edit.setPlaceholderText("<Filter>")
        qvboxlayout = QtWidgets.QVBoxLayout(self)
        qvboxlayout.addWidget(self.table_widget)
        qvboxlayout.addWidget(self.filter_text_edit)

    def init_slot(self):
        self.table_widget.doubleClicked.connect(self.select_target_slot)
        self.filter_text_edit.textChanged.connect(self.filter_text_changed_slot)

    def select_target_slot(self, index: QtCore.QModelIndex):
        self.select_text = index.siblingAtColumn(0).data()
        self.close()

    def update_table_widget(self, ref_target_dict: typing.Dict[str, dict]):
        self.select_text = ""
        self.ref_target_dict = ref_target_dict
        filter_ref_target_dict = {k: v for k, v in ref_target_dict.items() if self.filter_text in k.lower()}
        self.table_widget.set_data(filter_ref_target_dict)

    def filter_text_changed_slot(self, filter_text: str):
        self.filter_text = filter_text.lower()
        self.update_table_widget(self.ref_target_dict)


class ScheduleTableView(QtWidgets.QTableView):

    def __init__(self, callback, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.callback = callback
        self.add_remove_menu = None
        self.menu = None
        self.select_dialog = None
        self.init_ui()

    def init_ui(self):
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu_slot)
        self.setAutoFillBackground(True)
        self.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        self.setDragEnabled(True)
        self.setDragDropOverwriteMode(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSortingEnabled(False)
        self.setWordWrap(True)
        self.setCornerButtonEnabled(False)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Fixed)

    def show_context_menu_slot(self):
        menu = self.create_menu()
        row, col = self.get_current_coord()
        index = self.currentIndex()
        if row == 0 and col > 0:
            enabled_action = {"Insert 1 row down", "Insert 1 column left", "Insert 1 column right", "Delete column"}
            for action in self.retrieve_menu_actions(menu):
                if action.text() in enabled_action:
                    action.setEnabled(True)
                else:
                    action.setEnabled(False)
        elif row > 0 and col > 0:
            self.retrieve_menu_actions(menu)
            for action in self.retrieve_menu_actions(menu):
                if action.text() == "Add" and index.data():
                    action.setEnabled(False)
                else:
                    action.setEnabled(True)
        else:
            return

        menu.exec(QtGui.QCursor.pos())

    def retrieve_menu_actions(self, menu):
        actions = []
        for action in menu.actions():
            if action.menu():
                actions.extend(self.retrieve_menu_actions(action.menu()))
            else:
                actions.append(action)
        return actions

    def create_menu(self):
        if isinstance(self.menu, QtWidgets.QMenu):
            return self.menu
        menu = QtWidgets.QMenu(self)
        self.menu_set_style_sheet(menu)
        menu.addAction(QtGui.QIcon(":/add_s.svg"), "Add", self.add_task_slot)
        menu.addAction(QtGui.QIcon(":/not_ok.svg"), "Remove", self.remove_task)
        # menu.addAction(QtGui.QIcon(), "LockTasks", self.lock_tasks)
        # menu.addAction(QtGui.QIcon(), "UnlockTasks", self.unlock_tasks)
        menu.addSeparator()
        self.add_insert_delete_menu(menu)
        self.menu = menu
        return self.menu

    def add_insert_delete_menu(self, menu: QtWidgets.QMenu):
        insert_menu = menu.addMenu(QtGui.QIcon(":/insert.svg"), "Insert")
        insert_menu.addAction(QtGui.QIcon(), "Insert 1 row up", lambda: self.insert_row_or_col("up"))
        insert_menu.addAction(QtGui.QIcon(), "Insert 1 row down", lambda: self.insert_row_or_col("down"))
        insert_menu.addSeparator()
        insert_menu.addAction(QtGui.QIcon(), "Insert 1 column left", lambda: self.insert_row_or_col("left"))
        insert_menu.addAction(QtGui.QIcon(), "Insert 1 column right", lambda: self.insert_row_or_col("right"))
        delete_menu = menu.addMenu(QtGui.QIcon(":/delete.svg"), "Delete")
        delete_menu.addAction(QtGui.QIcon(), "Delete row", self.delete_row)
        delete_menu.addAction(QtGui.QIcon(), "Delete column", self.delete_column)

    def menu_set_style_sheet(self, menu: QtWidgets.QMenu):
        menu.setStyleSheet(
            "QMenu{border:1px solid lightgray;}"  # 设置整个菜单框的边界高亮厚度颜色
            "QMenu::item{padding:0px 10px 0px 5px;}"  # 以文字为标准，右边距文字40像素，左边同理
            "QMenu::item{height:20px;}"  # 显示菜单选项高度
            "QMenu::item{margin:1px 1px 1px 1px;}"  # 每个选项四边的边界厚度，上，右，下，左
            "QMenu::item:selected:enabled{background:lightskyblue;}"  # 选项选中颜色
        )

    def model(self) -> ScheduleTableModel:
        return super().model()

    def get_current_coord(self):
        index = self.currentIndex()
        return index.row(), index.column()

    def get_add_task_dict(self):
        task_dict = self.callback("get_schedule_table_task_dict")
        used_task_set: set = self.model().get_used_task()
        new_task_dict = {task_name: task_dict[task_name] for task_name in used_task_set.symmetric_difference(task_dict)}
        sorted_task_dict = dict(sorted(new_task_dict.items(), key=lambda x: (len(x[0]), x[0])))
        return sorted_task_dict

    def add_task_slot(self):
        index = self.currentIndex()
        row = index.row()
        col = index.column()
        if row <= 0 or col <= 0:
            return
        if self.model().in_group(row, col):
            QMessageBox(QMessageBox.Icon.Warning, "Warning", "不能编辑被锁定的任务!", parent=self).show()
            return
        task_dict = self.get_add_task_dict()
        self.select_dialog = self.select_dialog or SelectReferenceTargetDialog()
        self.select_dialog.update_table_widget(task_dict)
        self.select_dialog.move(
            self.window().frameGeometry().topLeft() + self.window().rect().center() - self.select_dialog.rect().center()
        )
        self.select_dialog.filter_text_edit.setFocus()
        self.select_dialog.exec()
        if self.select_dialog.select_text:
            self.model().setData(index, self.select_dialog.select_text, Qt.ItemDataRole.EditRole)
            self.model().add_group(row, row + 1, col)
            self.resizeColumnToContents(index.column())

    def remove_task(self):
        indexs = self.selectedIndexes()
        for index in indexs:
            row = index.row()
            col = index.column()
            if self.model().in_group(row, col):
                QMessageBox(QMessageBox.Icon.Warning, "Warning", "不能移除被锁定的任务，请先解锁!", parent=self).show()
                return
            self.model().setData(index, "", Qt.ItemDataRole.EditRole)
            self.model().remove_group(row, col)

    def lock_tasks(self):
        indexes = self.selectedIndexes()
        indexes_len = len(indexes)
        if indexes_len == 0:
            return
        data_count = len({index.data() for index in indexes if index.data()})
        col_count = len({index.column() for index in indexes})
        if indexes_len == 1 or data_count != indexes_len or col_count != 1:
            QMessageBox(QMessageBox.Icon.Warning, "Warning", "请选择一列中相邻的任务!", parent=self).show()
            return
        for index in indexes:
            row = index.row()
            col = index.column()
            if self.model().in_group(row, col):
                QMessageBox(QMessageBox.Icon.Warning, "Warning", "操作包含被锁定的任务，请先解锁!", parent=self).show()
                return
        col = indexes[0].column()
        row_start = min(index.row() for index in indexes)
        row_end = max(index.row() for index in indexes) + 1
        self.model().add_group(row_start, row_end, col)

    def unlock_tasks(self):
        row, col = self.get_current_coord()
        if not self.model().in_group(row, col):
            QMessageBox(QMessageBox.Icon.Warning, "Warning", "请选择一个被锁定的任务!", parent=self).show()
            return
        self.model().remove_group(row, col)

    def insert_row_or_col(self, direction):
        row, col = self.get_current_coord()
        if direction in ["up", "down"]:
            if direction == "down":
                row += 1
            for _col in range(1, self.model().columnCount()):
                group_0 = self.model().get_group(row - 1, _col)
                group_1 = self.model().get_group(row, _col)
                if group_0 == group_1 != -1:
                    QMessageBox(
                        QMessageBox.Icon.Warning, "Warning", "不能在被锁定的任务中插入一行，请先解锁!", parent=self
                    ).show()
                    return
            self.model().beginResetModel()
            self.model().refresh_group(row, 1, True)
            self.model().insertRow(row, self.currentIndex())
            self.model().endResetModel()
        elif direction in ["left", "right"]:
            if direction == "right":
                col += 1
            self.model().beginResetModel()
            self.model().insertColumn(col, self.currentIndex())
            self.model().endResetModel()

    def delete_row(self):
        row, col = self.get_current_coord()
        for _col in range(1, self.model().columnCount()):
            if self.model().in_group(row, _col):
                QMessageBox(QMessageBox.Icon.Warning, "Warning", "不能删除被锁定的任务，请先解锁!", parent=self).show()
                return
        self.model().beginResetModel()
        self.model().refresh_group(row, -1, True)
        self.model().removeRow(row, self.currentIndex())
        self.model().endResetModel()

    def delete_column(self):
        row, col = self.get_current_coord()
        for _row in range(1, self.model().rowCount()):
            if self.model().in_group(_row, col):
                QMessageBox(QMessageBox.Icon.Warning, "Warning", "不能删除被锁定的任务，请先解锁!", parent=self).show()
                return
        self.model().beginResetModel()
        self.model().removeColumn(col, self.currentIndex())
        self.model().endResetModel()


CURRENT_SCHEDULE_TABLE_WIDGET = None


class SecRuntimeSystemOsConfigurationScheduleTableWidget(QtWidgets.QWidget):

    def __init__(
        self,
        main_window,
        show_data_dict,
        selected_item_path,
        callback,
        parent: typing.Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        global CURRENT_SCHEDULE_TABLE_WIDGET
        CURRENT_SCHEDULE_TABLE_WIDGET = self
        self.auto_save = True
        self.lock = Lock()
        self.gen_cfg_button = QtWidgets.QPushButton()
        self.hbox_layout = QtWidgets.QHBoxLayout()
        self.hbox_layout_widget = QtWidgets.QWidget()
        self.sch_tbl_view = ScheduleTableView(callback, self)
        self.sch_tbl_model = ScheduleTableModel(self)
        self.splitter = QtWidgets.QSplitter(self)
        self.task_detail_info_table_widget = SelectReferenceTargetTableWidget()
        self.click_timer = QtCore.QTimer(self)
        self.main_window = main_window
        self.show_data_dict = show_data_dict
        self.selected_item_path = selected_item_path
        self.callback = callback
        self.init_ui()
        self.init_slot()

    def init_ui(self):
        self.callback("get_schedule_table_data", self.show_data_dict, result_callback=self.update_sch_tbl_model_data)
        self.click_timer.setSingleShot(True)
        self.sch_tbl_view.setModel(self.sch_tbl_model)
        self.gen_cfg_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.gen_cfg_button.setText("Generate Schedule Table Config")
        self.hbox_layout.setContentsMargins(0, 0, 0, 0)
        self.hbox_layout.addWidget(self.gen_cfg_button)
        self.hbox_layout.addStretch(0)
        self.hbox_layout_widget.setLayout(self.hbox_layout)
        self.grid_layout = QtWidgets.QGridLayout(self)
        self.grid_layout.addWidget(self.hbox_layout_widget, 0, 0)
        self.grid_layout.addWidget(self.splitter, 1, 0)
        self.splitter.addWidget(self.sch_tbl_view)
        self.splitter.addWidget(self.task_detail_info_table_widget)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.set_spans_slot()

    def init_slot(self):
        self.sch_tbl_model.modelReset.connect(self.set_spans_slot)
        self.sch_tbl_view.clicked.connect(self.handle_click_slot)
        self.sch_tbl_view.doubleClicked.connect(self.sort_first_row_slot)
        self.sch_tbl_view.doubleClicked.connect(self.sch_tbl_view.add_task_slot)
        self.gen_cfg_button.clicked.connect(self.generate_sch_tbl_cfg_slot)
        self.click_timer.timeout.connect(self.update_table_widget_slot)

    def update_sch_tbl_model_data(self, args):
        task_offset_list, sch_tbl_cfg = args
        self.sch_tbl_model.update_model_data(task_offset_list, sch_tbl_cfg)

    def handle_click_slot(self):
        if not self.click_timer.isActive():
            self.click_timer.start(250)

    def update_table_widget_slot(self):
        task_dict = self.callback("get_schedule_table_task_dict")
        task_names = {index.data() for index in self.sch_tbl_view.selectedIndexes()}
        if not task_names:
            return
        data = {k: v for k, v in task_dict.items() if k in task_names}
        self.task_detail_info_table_widget.set_data(data)

    def generate_sch_tbl_cfg_slot(self):
        sch_tbl_ui_cfg = self.sch_tbl_model.get_sch_tbl_ui_cfg()
        self.callback("generate_schedule_table_cfg", sch_tbl_ui_cfg)

    def set_spans_slot(self):
        row = self.sch_tbl_model.rowCount()
        if row <= 1:
            return
        self.sch_tbl_view.setSpan(1, 0, row - 1, 1)

    def sort_first_row_slot(self, index: QtCore.QModelIndex):
        self.click_timer.stop()
        row = index.row()
        col = index.column()
        if row == col == 0:
            self.sch_tbl_model.sort_first_row()

    def deleteLater(self) -> None:
        if self.auto_save:
            self.save_cfg()
        return super().deleteLater()

    def hideEvent(self, a0: QtGui.QHideEvent) -> None:
        if self.auto_save:
            self.save_cfg()
        return super().hideEvent(a0)

    def save_cfg(self):
        with self.lock:
            table_offset_list, sch_tbl_cfg = self.sch_tbl_model.get_sch_tbl_ui_data()
            self.callback("save_schedule_table_ui_data", table_offset_list, sch_tbl_cfg)
