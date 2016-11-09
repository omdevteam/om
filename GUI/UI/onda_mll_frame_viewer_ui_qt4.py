# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'OndaMLLFrameViewer.ui'
#
# Created: Thu Nov  3 02:34:46 2016
#      by: PyQt4 UI code generator 4.10.4
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
        MainWindow.resize(1133, 818)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.imageView = ImageView(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.imageView.sizePolicy().hasHeightForWidth())
        self.imageView.setSizePolicy(sizePolicy)
        self.imageView.setBaseSize(QtCore.QSize(0, 0))
        self.imageView.setObjectName(_fromUtf8("imageView"))
        self.verticalLayout.addWidget(self.imageView)
        self.horizontalLayout0 = QtGui.QHBoxLayout()
        self.horizontalLayout0.setObjectName(_fromUtf8("horizontalLayout0"))
        self.backButton = QtGui.QPushButton(self.centralwidget)
        self.backButton.setObjectName(_fromUtf8("backButton"))
        self.horizontalLayout0.addWidget(self.backButton)
        self.forwardButton = QtGui.QPushButton(self.centralwidget)
        self.forwardButton.setObjectName(_fromUtf8("forwardButton"))
        self.horizontalLayout0.addWidget(self.forwardButton)
        self.playPauseButton = QtGui.QPushButton(self.centralwidget)
        self.playPauseButton.setObjectName(_fromUtf8("playPauseButton"))
        self.horizontalLayout0.addWidget(self.playPauseButton)
        self.verticalLayout.addLayout(self.horizontalLayout0)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "OnDA MLL Frame Viewer", None))
        self.backButton.setText(_translate("MainWindow", "Back", None))
        self.forwardButton.setText(_translate("MainWindow", "Forward", None))
        self.playPauseButton.setText(_translate("MainWindow", "Play/Pause", None))

from pyqtgraph import ImageView
