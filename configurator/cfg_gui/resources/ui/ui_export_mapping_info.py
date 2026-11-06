# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'export_mapping_info.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QWidget)


class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(680, 230)
        Form.setMinimumSize(QSize(680, 230))
        Form.setMaximumSize(QSize(680, 230))
        icon = QIcon()
        icon.addFile(u":/vcos.png", QSize(), QIcon.Normal, QIcon.Off)
        Form.setWindowIcon(icon)
        Form.setStyleSheet(u"background-color: rgb(255, 255, 255);")
        self.label_8 = QLabel(Form)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setGeometry(QRect(13, 39, 641, 121))
        self.label_8.setStyleSheet(u"border-color: rgb(226, 226, 226);")
        self.label_8.setFrameShape(QFrame.Box)
        self.label_3 = QLabel(Form)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(20, 50, 261, 19))
        font = QFont()
        font.setFamilies([u"Microsoft YaHei UI"])
        font.setPointSize(10)
        self.label_3.setFont(font)
        self.lineEditProjectFilePath = QLineEdit(Form)
        self.lineEditProjectFilePath.setObjectName(u"lineEditProjectFilePath")
        self.lineEditProjectFilePath.setEnabled(True)
        self.lineEditProjectFilePath.setGeometry(QRect(164, 103, 391, 20))
        self.pushButtonBrowse = QPushButton(Form)
        self.pushButtonBrowse.setObjectName(u"pushButtonBrowse")
        self.pushButtonBrowse.setGeometry(QRect(565, 103, 75, 23))
        self.label_4 = QLabel(Form)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setGeometry(QRect(21, 103, 131, 17))
        font1 = QFont()
        font1.setFamilies([u"Microsoft YaHei UI"])
        self.label_4.setFont(font1)
        self.label_2 = QLabel(Form)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(0, 0, 680, 31))
        self.label_2.setStyleSheet(u"font: 12pt \"\u5fae\u8f6f\u96c5\u9ed1\";\n"
"background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 rgb(255, 255, 255), stop:0.3#f8fafc, stop: 1 #e4ebf3);\n"
"border-style: solid;\n"
"border-color: rgb(255, 255, 255);\n"
"border-width: 1px;")
        self.label_2.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)
        self.pushButtonOK = QPushButton(Form)
        self.pushButtonOK.setObjectName(u"pushButtonOK")
        self.pushButtonOK.setGeometry(QRect(550, 170, 101, 31))

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"VCOS Project", None))
        self.label_8.setText("")
        self.label_3.setText(QCoreApplication.translate("Form", u"Mapping Info Export", None))
        self.pushButtonBrowse.setText(QCoreApplication.translate("Form", u"Browse", None))
        self.label_4.setText(QCoreApplication.translate("Form", u"Target File:", None))
        self.label_2.setText(QCoreApplication.translate("Form", u"  Mapping Info Export", None))
        self.pushButtonOK.setText(QCoreApplication.translate("Form", u"OK", None))
    # retranslateUi

