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
from typing import Optional
from PySide6.QtCore import Qt, QObject, QPoint, QEvent
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QHeaderView,
    QToolButton,
    QPushButton,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListView,
    QMenu,
    QWidgetAction,
    QSpacerItem,
    QSizePolicy,
    QLineEdit,
)
from cfg_gui.widgets.filter_list import FilterListModel, UniqueRowProxyModel


class HeaderSortClearableAdapter(QObject):
    """
    Filter table header's event, enable canceling sort at third click
    """

    def __init__(self, header_view: QHeaderView, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        # self.header_view = view.horizontalHeader()
        self.header_view = header_view
        self.header_view.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.header_view.setSortIndicatorShown(False)
        # self.header_view.viewport().installEventFilter(self)

        self.mouse_pressed_pos = QPoint()
        self.mouse_is_moving = False

    def mouse_press_event_filter(self, mouse_event: QMouseEvent):
        if mouse_event.button() != Qt.MouseButton.LeftButton:
            return False
        else:
            self.mouse_pressed_pos = mouse_event.pos()
            return False

    def mouse_move_event_filter(self, mouse_event: QMouseEvent):
        if (
            mouse_event.buttons() & Qt.MouseButton.LeftButton
            and (self.mouse_pressed_pos - mouse_event.pos()).manhattanLength() > QApplication.startDragDistance()
        ):
            self.mouse_is_moving = True

        return False

    def mouse_release_event_filter(self, mouse_event: QMouseEvent):
        """
        Deal with mouse release event for tri-state sort
        """
        if mouse_event.button() != Qt.MouseButton.LeftButton:
            return False

        # Ignore the mouse release event after moving mouse
        if self.mouse_is_moving:
            self.mouse_is_moving = False
            return False

        index_at_cursor = self.header_view.logicalIndexAt(mouse_event.pos())
        if index_at_cursor == -1:
            pass
        # For first click, sorting in ascending order
        elif self.header_view.sortIndicatorSection() != index_at_cursor:
            self.header_view.setSortIndicator(index_at_cursor, Qt.SortOrder.AscendingOrder)
            self.header_view.setSortIndicatorShown(True)
        # For second click, sorting in descending order
        elif self.header_view.sortIndicatorOrder() == Qt.SortOrder.AscendingOrder:
            self.header_view.setSortIndicator(index_at_cursor, Qt.SortOrder.DescendingOrder)
        # For third click, cancel sorting
        else:
            self.header_view.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
            self.header_view.setSortIndicatorShown(False)

        self.header_view.sectionClicked.emit(index_at_cursor)
        return True

    def eventFilter(self, a0: QObject, a1: QEvent) -> bool:
        event = a1

        if event.type() == QEvent.Type.MouseButtonPress:
            return self.mouse_press_event_filter(event)
        elif event.type() == QEvent.Type.MouseMove:
            return self.mouse_move_event_filter(event)
        elif event.type() == QEvent.Type.MouseButtonRelease:
            return self.mouse_release_event_filter(event)

        return False


class HeaderToolButton(QToolButton):
    """
    Tool button of table header
    """

    def __init__(self, parent, logicalIndex) -> None:
        super().__init__(parent)
        self.logical_index = logicalIndex
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setAutoRaise(True)
        self.proxy_model = None
        self.filter_text_editor = QLineEdit()
        self.filter_text_editor.textChanged.connect(self.filter_text_changed_slot)
        self.pop_up_menu = self.create_filter_widget()
        self.setMenu(self.pop_up_menu)

    def create_filter_widget(self):
        filter_menu = QMenu(self)
        action = QWidgetAction(self)
        widget = QWidget(filter_menu)
        self.init_filter_widget_layout(widget)
        action.setDefaultWidget(widget)
        filter_menu.addAction(action)
        return filter_menu

    def init_filter_widget_layout(self, widget: QWidget):
        button_layout = QVBoxLayout()
        select_all_button = QPushButton("Select All")
        select_all_button.clicked.connect(self.select_all_clicked_slot)
        select_none_button = QPushButton("Select None")
        select_none_button.clicked.connect(self.select_none_clicked_slot)
        button_layout.addWidget(select_all_button)
        button_layout.addWidget(select_none_button)
        button_layout.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding))

        filter_layout = QHBoxLayout()
        item_list_view = QListView()
        item_list_model = FilterListModel(self.parent().model().sourceModel().get_column_raw_data(self.logical_index))
        self.proxy_model = UniqueRowProxyModel()
        self.proxy_model.setSourceModel(item_list_model)
        item_list_view.setModel(self.proxy_model)
        filter_layout.addLayout(button_layout)
        filter_layout.addWidget(item_list_view)

        clear_filter_button = QPushButton("Clear Filter")
        clear_filter_button.clicked.connect(self.clear_fliter_button_clicked_slot)
        self.filter_text_editor.setPlaceholderText("<Filter>")
        apply_button = QPushButton("Apply and close")
        apply_button.clicked.connect(self.apply_button_clicked_slot)
        general_layout = QVBoxLayout()
        general_layout.addWidget(clear_filter_button)
        general_layout.addWidget(self.filter_text_editor)
        general_layout.addLayout(filter_layout)
        general_layout.addWidget(apply_button)
        widget.setLayout(general_layout)

    def select_all_clicked_slot(self):
        self.proxy_model.check_all()

    def select_none_clicked_slot(self):
        self.proxy_model.uncheck_all()

    def filter_text_changed_slot(self):
        text = self.filter_text_editor.text()
        self.proxy_model.set_filter_text(text)

    def clear_fliter_button_clicked_slot(self):
        self.filter_text_editor.setText("")

    def apply_button_clicked_slot(self):
        # Gather
        filter_checked_set = set()
        filter_unchecked_set = set()
        for row in range(self.proxy_model.rowCount()):
            index = self.proxy_model.index(row, 0)
            if index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked:
                filter_checked_set.add(index.data(Qt.ItemDataRole.DisplayRole))
            elif index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Unchecked:
                filter_unchecked_set.add(index.data(Qt.ItemDataRole.DisplayRole))

        check_state_list = self.proxy_model.sourceModel().check_state_list
        source_model = self.proxy_model.sourceModel()
        for idx, _ in enumerate(check_state_list):
            index = source_model.index(idx, 0)
            if index.data(Qt.ItemDataRole.DisplayRole) in filter_checked_set:
                check_state_list[idx] = Qt.CheckState.Checked
            elif index.data(Qt.ItemDataRole.DisplayRole) in filter_unchecked_set:
                check_state_list[idx] = Qt.CheckState.Unchecked

        self.parent().model().update_rows(check_state_list)
        self.menu().close()


class ArgQHeaderView(QHeaderView):
    filter_button_width = 11
    filter_button_height = 11

    def __init__(self, orientation: Qt.Orientation, parent) -> None:
        super().__init__(orientation, parent)
        self.filter_button_dict = {}  # Store the filter button of each header section
        self.setSectionsClickable(True)
        self.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.setStyleSheet(
            'QHeaderView::section{font-family:"Microsoft YaHei";'
            "font-size:9pt;color:black;background-color:rgb(230, 230, 230);font-weight:400}"
        )

    def set_sort_indicator_clearable(self, clearable: bool):
        """
        Set if the sort can be cleared.
        Must be called after enable related table view sorting
        """
        if not self.isSortIndicatorShown():
            return

        if clearable:
            self.header_adapter = HeaderSortClearableAdapter(self)
            self.viewport().installEventFilter(self.header_adapter)
        else:
            if self.header_adapter:
                self.viewport().removeEventFilter(self.header_adapter)

    def paintSection(self, painter, rect, logicalIndex: int) -> None:
        """
        Calculate and paint tool button. Put button at bottom right of the header section
        """
        super().paintSection(painter, rect, logicalIndex)
        filter_button = None
        try:
            filter_button = self.filter_button_dict[logicalIndex]
        except KeyError:  # If filter button of this section not existed, create one
            filter_button = HeaderToolButton(self, logicalIndex)
            self.filter_button_dict[logicalIndex] = filter_button

        # Hide tool button of other header section
        for button in self.filter_button_dict.values():
            button: HeaderToolButton
            if button is not filter_button and rect.intersects(button.rect()):
                button.hide()

        # Calculate the coordinate of filter button
        x = rect.right() - self.filter_button_width
        y = rect.bottom() - self.filter_button_height
        filter_button.setGeometry(x, y, self.filter_button_width, self.filter_button_height)
        filter_button.show()
