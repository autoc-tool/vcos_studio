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
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt
from cfg_gui.widgets.vcos_custom import VcosCustom
from ui_adaptor.ui_interaction.ui_logger import logger


class MappingTableDelegate(QtWidgets.QStyledItemDelegate):
    STR_TO_CHECK_STATE = {
        "true": Qt.CheckState.Checked,
        "false": Qt.CheckState.Unchecked,
    }

    def createEditor(
        self, parent: QtWidgets.QWidget, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex
    ):
        """
        Override to create editor for special cells
        """
        if index.data(Qt.ItemDataRole.EditRole) == VcosCustom.EditorWidget.CheckBoxEditor:
            editor = QtWidgets.QCheckBox(parent)
            if index.flags() & Qt.ItemFlag.ItemIsEditable != 0:
                editor.setEnabled(True)
            else:
                editor.setEnabled(False)
            return editor
        else:
            return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index: QtCore.QModelIndex):
        """
        Set displaied data when editing
        """
        if isinstance(editor, QtWidgets.QCheckBox):
            editor.setCheckState(self.STR_TO_CHECK_STATE.get(index.data(), Qt.CheckState.Unchecked))
        else:
            super().setEditorData(editor, index)

    def setModelData(
        self, editor: QtWidgets.QWidget, model: QtCore.QAbstractItemModel, index: QtCore.QModelIndex
    ) -> None:
        value_table = {Qt.CheckState.Checked: "true", Qt.CheckState.Unchecked: "false"}
        if isinstance(editor, QtWidgets.QCheckBox):
            # Only update data with checked or unchecked state, omit partially check state
            if editor.checkState() in (Qt.CheckState.Checked, Qt.CheckState.Unchecked):
                new_value = value_table[editor.checkState()]
                model.setData(index, new_value, Qt.ItemDataRole.EditRole)
            else:
                logger.debug("Invalid state of checkbox for updating ecuc value obj!")
        else:
            super().setModelData(editor, model, index)

    def updateEditorGeometry(
        self, editor: QtWidgets.QWidget, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex
    ) -> None:
        """
        Move checkbox to center of the cell
        """
        if index.data(Qt.ItemDataRole.EditRole) == VcosCustom.EditorWidget.CheckBoxEditor:
            style = editor.style()
            checkBoxRect = style.subElementRect(QtWidgets.QStyle.SubElement.SE_CheckBoxIndicator, option)
            checkBoxRect.moveCenter(option.rect.center())
            editor.setGeometry(checkBoxRect)
        else:
            return super().updateEditorGeometry(editor, option, index)
