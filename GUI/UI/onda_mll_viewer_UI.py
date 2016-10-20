# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'OndaMLLViewer.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1280, 800)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.imageViewLayout = QtWidgets.QHBoxLayout()
        self.imageViewLayout.setObjectName("imageViewLayout")
        self.verticalLayout.addLayout(self.imageViewLayout)
        self.buttonLayout = QtWidgets.QHBoxLayout()
        self.buttonLayout.setObjectName("buttonLayout")
        self.buttonLayout1 = QtWidgets.QHBoxLayout()
        self.buttonLayout1.setObjectName("buttonLayout1")
        self.stxmButton = QtWidgets.QPushButton(self.centralwidget)
        self.stxmButton.setCheckable(True)
        self.stxmButton.setAutoExclusive(True)
        self.stxmButton.setObjectName("stxmButton")
        self.stxmDpcButtonGroup = QtWidgets.QButtonGroup(MainWindow)
        self.stxmDpcButtonGroup.setObjectName("stxmDpcButtonGroup")
        self.stxmDpcButtonGroup.addButton(self.stxmButton)
        self.buttonLayout1.addWidget(self.stxmButton)
        self.dpcButton = QtWidgets.QPushButton(self.centralwidget)
        self.dpcButton.setCheckable(True)
        self.dpcButton.setAutoExclusive(True)
        self.dpcButton.setObjectName("dpcButton")
        self.stxmDpcButtonGroup.addButton(self.dpcButton)
        self.buttonLayout1.addWidget(self.dpcButton)
        self.buttonLayout.addLayout(self.buttonLayout1)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.buttonLayout.addItem(spacerItem)
        self.rescaleButton = QtWidgets.QPushButton(self.centralwidget)
        self.rescaleButton.setObjectName("rescaleButton")
        self.buttonLayout.addWidget(self.rescaleButton)
        self.delayLabel = QtWidgets.QLabel(self.centralwidget)
        self.delayLabel.setObjectName("delayLabel")
        self.buttonLayout.addWidget(self.delayLabel)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.buttonLayout.addItem(spacerItem1)
        self.buttonLayout2 = QtWidgets.QHBoxLayout()
        self.buttonLayout2.setObjectName("buttonLayout2")
        self.fsIntegrButton = QtWidgets.QPushButton(self.centralwidget)
        self.fsIntegrButton.setCheckable(True)
        self.fsIntegrButton.setAutoExclusive(True)
        self.fsIntegrButton.setObjectName("fsIntegrButton")
        self.fsSsButtonGroup = QtWidgets.QButtonGroup(MainWindow)
        self.fsSsButtonGroup.setObjectName("fsSsButtonGroup")
        self.fsSsButtonGroup.addButton(self.fsIntegrButton)
        self.buttonLayout2.addWidget(self.fsIntegrButton)
        self.ssIntegrButton = QtWidgets.QPushButton(self.centralwidget)
        self.ssIntegrButton.setCheckable(True)
        self.ssIntegrButton.setAutoExclusive(True)
        self.ssIntegrButton.setObjectName("ssIntegrButton")
        self.fsSsButtonGroup.addButton(self.ssIntegrButton)
        self.buttonLayout2.addWidget(self.ssIntegrButton)
        self.buttonLayout.addLayout(self.buttonLayout2)
        self.verticalLayout.addLayout(self.buttonLayout)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "OnDA MLL"))
        self.stxmButton.setText(_translate("MainWindow", "STXM"))
        self.dpcButton.setText(_translate("MainWindow", "DPC"))
        self.rescaleButton.setText(_translate("MainWindow", "Auto Rescale"))
        self.delayLabel.setText(_translate("MainWindow", "Estimated delay: -"))
        self.fsIntegrButton.setText(_translate("MainWindow", "FS Integr"))
        self.ssIntegrButton.setText(_translate("MainWindow", "SS Integr"))

