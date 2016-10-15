# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'OnDAMLLViewer.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(985, 946)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.imageViewLayout = QtGui.QHBoxLayout()
        self.imageViewLayout.setObjectName(_fromUtf8("imageViewLayout"))
        self.verticalLayout.addLayout(self.imageViewLayout)
        self.buttonLayout = QtGui.QHBoxLayout()
        self.buttonLayout.setObjectName(_fromUtf8("buttonLayout"))
        self.buttonLayout1 = QtGui.QHBoxLayout()
        self.buttonLayout1.setObjectName(_fromUtf8("buttonLayout1"))
        self.stxmButton = QtGui.QPushButton(self.centralwidget)
        self.stxmButton.setCheckable(True)
        self.stxmButton.setAutoExclusive(True)
        self.stxmButton.setObjectName(_fromUtf8("stxmButton"))
        self.stxmDpcButtonGroup = QtGui.QButtonGroup(MainWindow)
        self.stxmDpcButtonGroup.setObjectName(_fromUtf8("stxmDpcButtonGroup"))
        self.stxmDpcButtonGroup.addButton(self.stxmButton)
        self.buttonLayout1.addWidget(self.stxmButton)
        self.dpcButton = QtGui.QPushButton(self.centralwidget)
        self.dpcButton.setCheckable(True)
        self.dpcButton.setAutoExclusive(True)
        self.dpcButton.setObjectName(_fromUtf8("dpcButton"))
        self.stxmDpcButtonGroup.addButton(self.dpcButton)
        self.buttonLayout1.addWidget(self.dpcButton)
        self.buttonLayout.addLayout(self.buttonLayout1)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.buttonLayout.addItem(spacerItem)
        self.delayLabel = QtGui.QLabel(self.centralwidget)
        self.delayLabel.setObjectName(_fromUtf8("delayLabel"))
        self.buttonLayout.addWidget(self.delayLabel)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.buttonLayout.addItem(spacerItem1)
        self.buttonLayout2 = QtGui.QHBoxLayout()
        self.buttonLayout2.setObjectName(_fromUtf8("buttonLayout2"))
        self.fsIntegrButton = QtGui.QPushButton(self.centralwidget)
        self.fsIntegrButton.setCheckable(True)
        self.fsIntegrButton.setAutoExclusive(True)
        self.fsIntegrButton.setObjectName(_fromUtf8("fsIntegrButton"))
        self.fsSsButtonGroup = QtGui.QButtonGroup(MainWindow)
        self.fsSsButtonGroup.setObjectName(_fromUtf8("fsSsButtonGroup"))
        self.fsSsButtonGroup.addButton(self.fsIntegrButton)
        self.buttonLayout2.addWidget(self.fsIntegrButton)
        self.ssIntegrButton = QtGui.QPushButton(self.centralwidget)
        self.ssIntegrButton.setCheckable(True)
        self.ssIntegrButton.setAutoExclusive(True)
        self.ssIntegrButton.setObjectName(_fromUtf8("ssIntegrButton"))
        self.fsSsButtonGroup.addButton(self.ssIntegrButton)
        self.buttonLayout2.addWidget(self.ssIntegrButton)
        self.buttonLayout.addLayout(self.buttonLayout2)
        self.verticalLayout.addLayout(self.buttonLayout)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "OnDA MLL", None))
        self.stxmButton.setText(_translate("MainWindow", "STXM", None))
        self.dpcButton.setText(_translate("MainWindow", "DPC", None))
        self.delayLabel.setText(_translate("MainWindow", "Estimated delay: -", None))
        self.fsIntegrButton.setText(_translate("MainWindow", "FS Integr", None))
        self.ssIntegrButton.setText(_translate("MainWindow", "SS Integr", None))

