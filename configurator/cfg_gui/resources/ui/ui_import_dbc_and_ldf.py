# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'import_dbc_and_ldf.ui'
##
## Created by: Qt User Interface Compiler version 6.6.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QHBoxLayout,
    QHeaderView, QLabel, QPushButton, QSizePolicy,
    QSpacerItem, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)


class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(984, 516)
        Form.setMinimumSize(QSize(984, 516))
        Form.setMaximumSize(QSize(984, 516))
        icon = QIcon()
        icon.addFile(u":/Home.svg", QSize(), QIcon.Normal, QIcon.Off)
        Form.setWindowIcon(icon)
        self.verticalLayout_2 = QVBoxLayout(Form)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label = QLabel(Form)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setFamilies([u"Microsoft YaHei UI"])
        font.setPointSize(14)
        font.setBold(False)
        self.label.setFont(font)

        self.verticalLayout_2.addWidget(self.label)

        self.label_2 = QLabel(Form)
        self.label_2.setObjectName(u"label_2")
        font1 = QFont()
        font1.setFamilies([u"Microsoft YaHei UI"])
        font1.setPointSize(9)
        font1.setBold(False)
        self.label_2.setFont(font1)

        self.verticalLayout_2.addWidget(self.label_2)

        self.line = QFrame(Form)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.verticalLayout_2.addWidget(self.line)

        self.label_3 = QLabel(Form)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font1)

        self.verticalLayout_2.addWidget(self.label_3)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.tableWidget = QTableWidget(Form)
        if (self.tableWidget.columnCount() < 3):
            self.tableWidget.setColumnCount(3)
        icon1 = QIcon()
        icon1.addFile(u":/import.svg", QSize(), QIcon.Normal, QIcon.Off)
        __qtablewidgetitem = QTableWidgetItem()
        __qtablewidgetitem.setIcon(icon1);
        self.tableWidget.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        if (self.tableWidget.rowCount() < 7):
            self.tableWidget.setRowCount(7)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tableWidget.setVerticalHeaderItem(0, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.tableWidget.setVerticalHeaderItem(1, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.tableWidget.setVerticalHeaderItem(2, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.tableWidget.setVerticalHeaderItem(3, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.tableWidget.setVerticalHeaderItem(4, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.tableWidget.setVerticalHeaderItem(5, __qtablewidgetitem8)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.tableWidget.setVerticalHeaderItem(6, __qtablewidgetitem9)
        self.tableWidget.setObjectName(u"tableWidget")
        self.tableWidget.setFrameShape(QFrame.NoFrame)
        self.tableWidget.horizontalHeader().setVisible(True)
        self.tableWidget.horizontalHeader().setCascadingSectionResizes(False)
        self.tableWidget.horizontalHeader().setHighlightSections(True)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.verticalHeader().setHighlightSections(True)

        self.horizontalLayout.addWidget(self.tableWidget)

        self.frame = QFrame(Form)
        self.frame.setObjectName(u"frame")
        self.frame.setMinimumSize(QSize(10, 0))
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)

        self.horizontalLayout.addWidget(self.frame)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(-1, 30, -1, -1)
        self.pushButtonAddFiles = QPushButton(Form)
        self.pushButtonAddFiles.setObjectName(u"pushButtonAddFiles")
        icon2 = QIcon()
        icon2.addFile(u":/add.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.pushButtonAddFiles.setIcon(icon2)
        self.pushButtonAddFiles.setAutoDefault(True)
        self.pushButtonAddFiles.setFlat(True)

        self.verticalLayout.addWidget(self.pushButtonAddFiles)

        self.pushButtonReplace = QPushButton(Form)
        self.pushButtonReplace.setObjectName(u"pushButtonReplace")
        icon3 = QIcon()
        icon3.addFile(u":/reset.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.pushButtonReplace.setIcon(icon3)
        self.pushButtonReplace.setAutoDefault(True)
        self.pushButtonReplace.setFlat(True)

        self.verticalLayout.addWidget(self.pushButtonReplace)

        self.pushButtonRemove = QPushButton(Form)
        self.pushButtonRemove.setObjectName(u"pushButtonRemove")
        self.pushButtonRemove.setStyleSheet(u"QPushButton {background-color:rgba(0,0,0,0);}\n"
"QPushButton:hover {	background-color:#e3f3fd;}")
        icon4 = QIcon()
        icon4.addFile(u":/not_ok.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.pushButtonRemove.setIcon(icon4)
        self.pushButtonRemove.setCheckable(False)
        self.pushButtonRemove.setAutoDefault(True)
        self.pushButtonRemove.setFlat(True)

        self.verticalLayout.addWidget(self.pushButtonRemove)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_2)

        self.pushButtonApply = QPushButton(Form)
        self.pushButtonApply.setObjectName(u"pushButtonApply")

        self.verticalLayout.addWidget(self.pushButtonApply)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.horizontalLayout.addLayout(self.verticalLayout)

        self.frame_2 = QFrame(Form)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setMinimumSize(QSize(20, 0))
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)

        self.horizontalLayout.addWidget(self.frame_2)


        self.verticalLayout_2.addLayout(self.horizontalLayout)

        self.merge_signal_checkBox = QCheckBox(Form)
        self.merge_signal_checkBox.setObjectName(u"merge_signal_checkBox")
        self.merge_signal_checkBox.setEnabled(True)

        self.verticalLayout_2.addWidget(self.merge_signal_checkBox)

        self.add_channel_name_checkBox = QCheckBox(Form)
        self.add_channel_name_checkBox.setObjectName(u"add_channel_name_checkBox")
        self.add_channel_name_checkBox.setEnabled(True)

        self.verticalLayout_2.addWidget(self.add_channel_name_checkBox)


        self.retranslateUi(Form)

        self.pushButtonAddFiles.setDefault(True)
        self.pushButtonReplace.setDefault(False)
        self.pushButtonRemove.setDefault(True)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Import Files", None))
        self.label.setText(QCoreApplication.translate("Form", u"Import content selection", None))
        self.label_2.setText(QCoreApplication.translate("Form", u"Select the CanDb primitives and LinDF and CDD to import", None))
        self.label_3.setText(QCoreApplication.translate("Form", u"Select the CanDB node that corresponds to this Ecu.(Used to determine frame direction)", None))
        ___qtablewidgetitem = self.tableWidget.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("Form", u"Filename", None));
        ___qtablewidgetitem1 = self.tableWidget.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("Form", u"ECU Instance", None));
        ___qtablewidgetitem2 = self.tableWidget.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("Form", u"Path", None));
        self.pushButtonAddFiles.setText(QCoreApplication.translate("Form", u"Add Files", None))
        self.pushButtonReplace.setText(QCoreApplication.translate("Form", u"Replace", None))
        self.pushButtonRemove.setText(QCoreApplication.translate("Form", u" Remove", None))
        self.pushButtonApply.setText(QCoreApplication.translate("Form", u"OK", None))
        self.merge_signal_checkBox.setText(QCoreApplication.translate("Form", u"Import DIDs and RIDs as single signal for DCM (backward compatibility)", None))
        self.add_channel_name_checkBox.setText(QCoreApplication.translate("Form", u"Import DBC/LDF files with added channel name to the SystemSignals", None))
    # retranslateUi

