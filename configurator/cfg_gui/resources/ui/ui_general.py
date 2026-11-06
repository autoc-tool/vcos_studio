# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'general.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QWidget)


class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(800, 600)
        Form.setMinimumSize(QSize(800, 600))
        Form.setMaximumSize(QSize(800, 600))
        icon = QIcon()
        icon.addFile(u":/Home.svg", QSize(), QIcon.Normal, QIcon.Off)
        Form.setWindowIcon(icon)
        Form.setStyleSheet(u"background-color: rgb(255, 255, 255);")
        self.label_3 = QLabel(Form)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(10, 40, 261, 16))
        font = QFont()
        font.setFamilies([u"\u5fae\u8f6f\u96c5\u9ed1"])
        font.setPointSize(12)
        font.setBold(False)
        font.setItalic(False)
        self.label_3.setFont(font)
        self.label_3.setStyleSheet(u"font: 12pt \"\u5fae\u8f6f\u96c5\u9ed1\";\n"
"color: rgb(85, 85, 255);")
        self.Description_Label = QLabel(Form)
        self.Description_Label.setObjectName(u"Description_Label")
        self.Description_Label.setGeometry(QRect(0, 0, 701, 31))
        self.Description_Label.setStyleSheet(u"font: 12pt \"\u5fae\u8f6f\u96c5\u9ed1\";\n"
"background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 rgb(255, 255, 255), stop:0.3#f8fafc, stop: 1 #e4ebf3);\n"
"border-style: solid;\n"
"border-color: rgb(255, 255, 255);\n"
"border-width: 1px;")
        self.Description_Label.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)
        self.lineEditPeriodicSave = QLineEdit(Form)
        self.lineEditPeriodicSave.setObjectName(u"lineEditPeriodicSave")
        self.lineEditPeriodicSave.setEnabled(True)
        self.lineEditPeriodicSave.setGeometry(QRect(160, 118, 71, 20))
        self.label_5 = QLabel(Form)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setGeometry(QRect(20, 120, 131, 17))
        font1 = QFont()
        font1.setFamilies([u"Microsoft YaHei UI"])
        self.label_5.setFont(font1)
        self.line = QFrame(Form)
        self.line.setObjectName(u"line")
        self.line.setGeometry(QRect(3, 60, 701, 16))
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)
        self.pushButtonOk = QPushButton(Form)
        self.pushButtonOk.setObjectName(u"pushButtonOk")
        self.pushButtonOk.setGeometry(QRect(660, 540, 89, 25))
        self.label_6 = QLabel(Form)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setGeometry(QRect(20, 90, 131, 17))
        self.label_6.setFont(font1)
        self.checkBox = QCheckBox(Form)
        self.checkBox.setObjectName(u"checkBox")
        self.checkBox.setGeometry(QRect(160, 93, 71, 16))
        self.checkBox.setChecked(True)

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"VCOS General", None))
        self.label_3.setText(QCoreApplication.translate("Form", u"General", None))
        self.Description_Label.setText(QCoreApplication.translate("Form", u"General", None))
        self.label_5.setText(QCoreApplication.translate("Form", u"Periodic Save(s):", None))
        self.pushButtonOk.setText(QCoreApplication.translate("Form", u"OK", None))
        self.label_6.setText(QCoreApplication.translate("Form", u"Periodic Save Setting:", None))
        self.checkBox.setText("")
    # retranslateUi

