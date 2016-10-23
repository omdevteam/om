# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'OndaMLLFrameViewer.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1133, 818)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.imageView = ImageView(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.imageView.sizePolicy().hasHeightForWidth())
        self.imageView.setSizePolicy(sizePolicy)
        self.imageView.setBaseSize(QtCore.QSize(0, 0))
        self.imageView.setObjectName("imageView")
        self.verticalLayout.addWidget(self.imageView)
        self.horizontalLayout0 = QtWidgets.QHBoxLayout()
        self.horizontalLayout0.setObjectName("horizontalLayout0")
        self.backButton = QtWidgets.QPushButton(self.centralwidget)
        self.backButton.setObjectName("backButton")
        self.horizontalLayout0.addWidget(self.backButton)
        self.forwardButton = QtWidgets.QPushButton(self.centralwidget)
        self.forwardButton.setObjectName("forwardButton")
        self.horizontalLayout0.addWidget(self.forwardButton)
        self.playPauseButton = QtWidgets.QPushButton(self.centralwidget)
        self.playPauseButton.setObjectName("playPauseButton")
        self.horizontalLayout0.addWidget(self.playPauseButton)
        self.verticalLayout.addLayout(self.horizontalLayout0)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "OnDA MLL Frame Viewer"))
        self.backButton.setText(_translate("MainWindow", "Back"))
        self.forwardButton.setText(_translate("MainWindow", "Forward"))
        self.playPauseButton.setText(_translate("MainWindow", "Play/Pause"))

from pyqtgraph import ImageView
