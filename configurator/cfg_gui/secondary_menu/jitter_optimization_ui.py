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
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidgetItem,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QTableWidget,
    QDialog,
    QCheckBox,
    QGridLayout,
)
from cfg_gui.widgets.tree_view import ArgQTreeView
from ui_adaptor.ui_interaction.ui_logger import logger


class JitterOptimizationUI(QDialog):

    def __init__(self, callback, parent):
        super().__init__(parent)
        self.mainwindow = parent
        self.callback = callback
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        self.setWindowTitle("One Click Optimization")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        # 创建控件
        self.optimizationButton = QPushButton("Optimization")
        self.optimizationButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.rollbackButton = QPushButton("Rollback History")
        self.rollbackButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.clearButton = QPushButton("Clear History")
        self.clearButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.jitterCheckBox = QCheckBox("Jitter")
        self.jitterCheckBox.setChecked(True)
        self.jitterCheckBox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.traceCheckBox = QCheckBox("Trace")
        self.traceCheckBox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.historyTable = QTableWidget()
        self.historyTable.setColumnCount(1)
        self.historyTable.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.historyTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.historyTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.historyTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.historyTable.setHorizontalHeaderLabels(["History"])
        self.historyTable.setContentsMargins(0, 0, 0, 0)  # 设置表格的边距为0
        # 设置列
        header = self.historyTable.horizontalHeader()
        header.setFixedHeight(25)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # 主布局
        mainLayout = QGridLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)  # 设置主布局的边距为0
        mainLayout.setSpacing(0)  # 设置主布局的控件间距为0
        # 按钮布局
        mainLayout.addWidget(self.jitterCheckBox, 1, 0, 1, 1)
        mainLayout.addWidget(self.traceCheckBox, 2, 0, 1, 1)
        mainLayout.addWidget(self.optimizationButton, 1, 1, 1, 1)
        mainLayout.addWidget(self.rollbackButton, 1, 3, 1, 1)
        mainLayout.addWidget(self.clearButton, 1, 5, 1, 1)
        mainLayout.addWidget(self.historyTable, 2, 1, 5, 5)
        self.setLayout(mainLayout)
        # 连接信号和槽
        self.optimizationButton.clicked.connect(self.onOptClicked)
        self.rollbackButton.clicked.connect(self.onRollbackClicked)
        self.clearButton.clicked.connect(self.onClearClicked)
        self.initTable()
        self.initDialog()

    def initTable(self):
        history_time = self.callback("get_jitter_opt_history_time")
        for time in history_time:
            self.appendTableItem(time)

    def onOptClicked(self):

        def result_callback(currentTime):
            self.appendTableItem(currentTime)
            self.updateModule()

        jitter = self.jitterCheckBox.isChecked()
        trace = self.traceCheckBox.isChecked()
        opt = {"jitter": jitter, "trace": trace}
        self.callback("generate_schedule_table_cfg_by_jitter", opt, result_callback=result_callback)

    def appendTableItem(self, currentTime):
        if not currentTime:
            return
        self.historyTable.insertRow(0)
        self.historyTable.setItem(0, 0, QTableWidgetItem(currentTime))

    def updateModule(self):
        try:
            if "OS Configuration" in self.mainwindow.over_view_ui.bsw_cfg_view_dict:
                module_cfg_view = self.mainwindow.over_view_ui.bsw_cfg_view_dict["OS Configuration"]
                tree_view: ArgQTreeView = module_cfg_view.findChild(ArgQTreeView)
                if hasattr(tree_view, "param_widget") and hasattr(tree_view.param_widget, "sch_tbl_model"):
                    tree_view.param_widget.auto_save = False
                    tree_view.show_param_widget(tree_view.currentIndex())
                    tree_view.param_widget.auto_save = True
        except BaseException:
            logger.exception("Update module error")

    def initDialog(self):
        self.dialog = QDialog(self)
        self.dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.dialogLabel = QLabel()
        self.dialogOkButton = QPushButton("Yes")
        self.dialogOkButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.dialogCancelButton = QPushButton("Cancel")
        self.dialogCancelButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.dialogCancelButton.clicked.connect(self.dialog.close)
        mainLayout = QVBoxLayout()
        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.dialogOkButton)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self.dialogCancelButton)
        mainLayout.addWidget(self.dialogLabel)
        mainLayout.addLayout(buttonLayout)
        self.dialog.setLayout(mainLayout)
        self.clickedConnect = None

    def openDialog(self, label, ok_slot=None):
        self.dialogLabel.setText(label)
        if self.clickedConnect:
            self.dialogOkButton.clicked.disconnect(self.clickedConnect)
        if ok_slot:
            self.clickedConnect = self.dialogOkButton.clicked.connect(ok_slot)
        else:
            self.clickedConnect = self.dialogOkButton.clicked.connect(self.dialog.close)
        self.dialog.open()

    def onRollbackClicked(self):
        if not self.historyTable.currentItem():
            self.openDialog("请选择一个历史配置?")
            return

        def rollback_to_current_config():
            model = self.historyTable.model()
            self.historyTable.setUpdatesEnabled(False)
            currentTime = self.historyTable.currentItem().text()
            for _ in range(self.historyTable.currentRow() + 1):
                model.removeRow(0)
            self.historyTable.setUpdatesEnabled(True)
            self.callback("rollback_jitter_opt_history", currentTime)
            self.dialog.close()
            self.updateModule()

        self.openDialog("是否回退到选择的历史配置?", rollback_to_current_config)

    def onClearClicked(self):

        def clear_history():
            self.historyTable.setRowCount(0)
            self.callback("clear_jitter_opt_history")
            self.dialog.close()

        self.openDialog("是否删除所有历史配置?", clear_history)
