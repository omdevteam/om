# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'OndaCrystallographyGUI.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1200, 800)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout0 = QtWidgets.QVBoxLayout()
        self.verticalLayout0.setObjectName("verticalLayout0")
        self.splitter0 = QtWidgets.QSplitter(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.splitter0.sizePolicy().hasHeightForWidth())
        self.splitter0.setSizePolicy(sizePolicy)
        self.splitter0.setOrientation(QtCore.Qt.Horizontal)
        self.splitter0.setObjectName("splitter0")
        self.imageView = ImageView(self.splitter0)
        self.imageView.setObjectName("imageView")
        self.splitter1 = QtWidgets.QSplitter(self.splitter0)
        self.splitter1.setOrientation(QtCore.Qt.Vertical)
        self.splitter1.setObjectName("splitter1")
        self.hitRatePlotWidget = PlotWidget(self.splitter1)
        self.hitRatePlotWidget.setObjectName("hitRatePlotWidget")
        self.saturationPlotViewer = PlotWidget(self.splitter1)
        self.saturationPlotViewer.setObjectName("saturationPlotViewer")
        self.verticalLayout0.addWidget(self.splitter0)
        self.horizontalLayout0 = QtWidgets.QHBoxLayout()
        self.horizontalLayout0.setObjectName("horizontalLayout0")
        self.resetPeaksButton = QtWidgets.QPushButton(self.centralwidget)
        self.resetPeaksButton.setObjectName("resetPeaksButton")
        self.horizontalLayout0.addWidget(self.resetPeaksButton)
        self.resetPlotsButton = QtWidgets.QPushButton(self.centralwidget)
        self.resetPlotsButton.setObjectName("resetPlotsButton")
        self.horizontalLayout0.addWidget(self.resetPlotsButton)
        self.delayLabel = QtWidgets.QLabel(self.centralwidget)
        self.delayLabel.setObjectName("delayLabel")
        self.horizontalLayout0.addWidget(self.delayLabel)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout0.addItem(spacerItem)
        self.resolutionRingsCheckBox = QtWidgets.QCheckBox(self.centralwidget)
        self.resolutionRingsCheckBox.setObjectName("resolutionRingsCheckBox")
        self.horizontalLayout0.addWidget(self.resolutionRingsCheckBox)
        self.resolutionRingsLineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.resolutionRingsLineEdit.setObjectName("resolutionRingsLineEdit")
        self.horizontalLayout0.addWidget(self.resolutionRingsLineEdit)
        self.accumulatedPeaksCheckBox = QtWidgets.QCheckBox(self.centralwidget)
        self.accumulatedPeaksCheckBox.setObjectName("accumulatedPeaksCheckBox")
        self.horizontalLayout0.addWidget(self.accumulatedPeaksCheckBox)
        self.verticalLayout0.addLayout(self.horizontalLayout0)
        self.gridLayout.addLayout(self.verticalLayout0, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "OnDA Crystallography"))
        self.resetPeaksButton.setText(_translate("MainWindow", "Reset Peaks"))
        self.resetPlotsButton.setText(_translate("MainWindow", "Reset Plots"))
        self.delayLabel.setText(_translate("MainWindow", "Estimated Delay: -"))
        self.resolutionRingsCheckBox.setText(_translate("MainWindow", "Resolution Rings"))
        self.accumulatedPeaksCheckBox.setText(_translate("MainWindow", "Show Accumulated Peaks"))

from pyqtgraph import ImageView, PlotWidget
