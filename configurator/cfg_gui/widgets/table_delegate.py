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
from cfg_gui.widgets.vcos_custom import VcosCustom
from ui_adaptor.ui_interaction.ui_logger import logger
from PySide6.QtCore import Qt, QModelIndex, QAbstractItemModel, QRect, QPoint
from PySide6.QtWidgets import (
    QWidget,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QCheckBox,
    QComboBox,
    QStyleOptionButton,
    QApplication,
    QLineEdit,
)


class ContainerOutlineDelegate(QStyledItemDelegate):

    def __init__(self, parent) -> None:
        super().__init__(parent)

    def get_check_box_rect(self, option):
        checkbox = QStyleOptionButton()
        rect = QApplication.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, checkbox)
        point = QPoint(
            option.rect.x() + option.rect.width() / 2 - rect.width() / 2,
            option.rect.y() + option.rect.height() / 2 - rect.height() / 2,
        )
        return QRect(point, rect.size())

    def paint(self, painter, option, index):
        str_to_state = {
            "true": QStyle.StateFlag.State_On,
            "false": QStyle.StateFlag.State_Off,
            "": QStyle.StateFlag.State_NoChange,
            None: QStyle.StateFlag.State_NoChange,
        }
        if index.data(Qt.ItemDataRole.EditRole) == VcosCustom.EditorWidget.CheckBoxEditor:
            # Draw checkbox
            super().paint(painter, option, index)
            checkbox_opt = QStyleOptionButton()
            try:
                checkbox_opt.state |= str_to_state[index.data(Qt.ItemDataRole.DisplayRole)]
            except KeyError:
                return
            checkbox_opt.state |= QStyle.StateFlag.State_Enabled
            checkbox_opt.rect = self.get_check_box_rect(option)
            QApplication.style().drawControl(QStyle.ControlElement.CE_CheckBox, checkbox_opt, painter)
        # elif index.data(Qt.ItemDataRole.EditRole) == VcosCustom.EditorWidget.ComboBoxEditor:
        #     # Always display special cell widget
        #     self.parent().openPersistentEditor(index)
        else:
            super().paint(painter, option, index)

    def initStyleOption(self, option: "QStyleOptionViewItem", index: QModelIndex) -> None:
        super().initStyleOption(option, index)
        if index.data(Qt.ItemDataRole.EditRole) == VcosCustom.EditorWidget.CheckBoxEditor:
            option.text = ""

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        """
        Override to create editor for special cells
        """
        if index.data(Qt.ItemDataRole.EditRole) == VcosCustom.EditorWidget.CheckBoxEditor:
            editor = QCheckBox(parent)
            if index.flags() & Qt.ItemFlag.ItemIsEditable:
                editor.setEnabled(True)
            else:
                editor.setEnabled(False)
            # editor.setCheckState(str_to_check_state[index.data(Qt.ItemDataRole.DisplayRole)])
            return editor
        if index.data(Qt.ItemDataRole.EditRole) == VcosCustom.EditorWidget.ComboBoxEditor:
            editor = QComboBox(parent)
            if index.flags() & Qt.ItemFlag.ItemIsEditable:
                editor.setEnabled(True)
            else:
                editor.setEnabled(False)
            # current_val = index.data(Qt.ItemDataRole.DisplayRole)
            item_tuple = index.data(VcosCustom.ItemDataRole.ComboBoxItemsRole)
            editor.addItems(item_tuple)
            # editor.setCurrentText(current_val)
            editor.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
            # self.sizeHintChanged.emit(index)
            return editor
        else:
            return super().createEditor(parent, option, index)

    # def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
    #     if index.data(Qt.ItemDataRole.EditRole) == VcosCustom.EditorWidget.ComboBoxEditor:
    #         pass
    #     return super().sizeHint(option, index)

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        """
        Set displaied data when editing
        """
        str_to_check_state = {
            "true": Qt.CheckState.Checked,
            "false": Qt.CheckState.Unchecked,
            "": Qt.CheckState.PartiallyChecked,
            None: Qt.CheckState.PartiallyChecked,
        }
        if index.data(Qt.ItemDataRole.EditRole) == VcosCustom.EditorWidget.CheckBoxEditor:
            editor: QCheckBox
            editor.setCheckState(str_to_check_state[index.data()])
        elif index.data(Qt.ItemDataRole.EditRole) == VcosCustom.EditorWidget.ComboBoxEditor:
            editor: QComboBox
            current_val = index.data(Qt.ItemDataRole.DisplayRole)
            editor.setCurrentText(current_val)
        else:
            if isinstance(editor, QLineEdit):
                editor.setText(index.data())

    def setModelData(self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex) -> None:
        value_table = {Qt.CheckState.Checked: "true", Qt.CheckState.Unchecked: "false"}
        if index.data(Qt.ItemDataRole.EditRole) == VcosCustom.EditorWidget.CheckBoxEditor:
            check_box_editor: QCheckBox = editor
            # Only update data with checked or unchecked state, omit partially check state
            if check_box_editor.checkState() in (Qt.CheckState.Checked, Qt.CheckState.Unchecked):
                new_value = value_table[check_box_editor.checkState()]
                model.setData(index, new_value, Qt.ItemDataRole.EditRole)
            else:
                logger.debug("Invalid state of checkbox for updating ecuc value obj!")
        elif index.data(Qt.ItemDataRole.EditRole) == VcosCustom.EditorWidget.ComboBoxEditor:
            combo_box_editor: QComboBox = editor
            new_value = combo_box_editor.currentText()
            model.setData(index, new_value, Qt.ItemDataRole.EditRole)
        else:
            if isinstance(editor, QLineEdit):
                new_value = editor.text()
                model.setData(index, new_value, Qt.ItemDataRole.EditRole)
            else:
                super().setModelData(editor, model, index)

    def updateEditorGeometry(self, editor: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """
        Move checkbox to center of the cell
        """
        if index.data(Qt.ItemDataRole.EditRole) == VcosCustom.EditorWidget.CheckBoxEditor:
            style = editor.style()
            checkBoxRect = style.subElementRect(QStyle.SE_CheckBoxIndicator, option)
            checkBoxRect.moveCenter(option.rect.center())
            editor.setGeometry(checkBoxRect)
        else:
            return super().updateEditorGeometry(editor, option, index)
