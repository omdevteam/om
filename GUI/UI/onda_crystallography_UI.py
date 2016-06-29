# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'OndaCrystallographyGUI.ui'
#
# Created: Tue Dec 15 21:57:42 2015
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

class Ui_mainWindow(object):
    def setupUi(self, mainWindow):
        mainWindow.setObjectName(_fromUtf8("mainWindow"))
        mainWindow.resize(1200, 800)
        self.centralwidget = QtGui.QWidget(mainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.verticalLayout0 = QtGui.QVBoxLayout()
        self.verticalLayout0.setObjectName(_fromUtf8("verticalLayout0"))
        self.splitter0 = QtGui.QSplitter(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.splitter0.sizePolicy().hasHeightForWidth())
        self.splitter0.setSizePolicy(sizePolicy)
        self.splitter0.setOrientation(QtCore.Qt.Horizontal)
        self.splitter0.setObjectName(_fromUtf8("splitter0"))
        self.imageView = ImageView(self.splitter0)
        self.imageView.setObjectName(_fromUtf8("imageView"))
        self.splitter1 = QtGui.QSplitter(self.splitter0)
        self.splitter1.setOrientation(QtCore.Qt.Vertical)
        self.splitter1.setObjectName(_fromUtf8("splitter1"))
        self.hitRatePlotWidget = PlotWidget(self.splitter1)
        self.hitRatePlotWidget.setObjectName(_fromUtf8("hitRatePlotWidget"))
        self.saturationPlotViewer = PlotWidget(self.splitter1)
        self.saturationPlotViewer.setObjectName(_fromUtf8("saturationPlotViewer"))
        self.verticalLayout0.addWidget(self.splitter0)
        self.horizontalLayout0 = QtGui.QHBoxLayout()
        self.horizontalLayout0.setObjectName(_fromUtf8("horizontalLayout0"))
        self.resetPeaksButton = QtGui.QPushButton(self.centralwidget)
        self.resetPeaksButton.setObjectName(_fromUtf8("resetPeaksButton"))
        self.horizontalLayout0.addWidget(self.resetPeaksButton)
        self.resetPlotsButton = QtGui.QPushButton(self.centralwidget)
        self.resetPlotsButton.setObjectName(_fromUtf8("resetPlotsButton"))
        self.horizontalLayout0.addWidget(self.resetPlotsButton)
        self.delayLabel = QtGui.QLabel(self.centralwidget)
        self.delayLabel.setObjectName(_fromUtf8("delayLabel"))
        self.horizontalLayout0.addWidget(self.delayLabel)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout0.addItem(spacerItem)
        self.resolutionRingsCheckBox = QtGui.QCheckBox(self.centralwidget)
        self.resolutionRingsCheckBox.setObjectName(_fromUtf8("resolutionRingsCheckBox"))
        self.horizontalLayout0.addWidget(self.resolutionRingsCheckBox)
        self.resolutionRingsLineEdit = QtGui.QLineEdit(self.centralwidget)
        self.resolutionRingsLineEdit.setObjectName(_fromUtf8("resolutionRingsLineEdit"))
        self.horizontalLayout0.addWidget(self.resolutionRingsLineEdit)
        self.accumulatedPeaksCheckBox = QtGui.QCheckBox(self.centralwidget)
        self.accumulatedPeaksCheckBox.setObjectName(_fromUtf8("accumulatedPeaksCheckBox"))
        self.horizontalLayout0.addWidget(self.accumulatedPeaksCheckBox)
        self.verticalLayout0.addLayout(self.horizontalLayout0)
        self.gridLayout.addLayout(self.verticalLayout0, 0, 0, 1, 1)
        mainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtGui.QStatusBar(mainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        mainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(mainWindow)
        QtCore.QMetaObject.connectSlotsByName(mainWindow)

    def retranslateUi(self, mainWindow):
        mainWindow.setWindowTitle(_translate("mainWindow", "OnDA Crystallography", None))
        self.resetPeaksButton.setText(_translate("mainWindow", "Reset Peaks", None))
        self.resetPlotsButton.setText(_translate("mainWindow", "Reset Plots", None))
        self.delayLabel.setText(_translate("mainWindow", "Estimated Delay: -", None))
        self.resolutionRingsCheckBox.setText(_translate("mainWindow", "Resolution Rings", None))
        self.accumulatedPeaksCheckBox.setText(_translate("mainWindow", "Show Accumulated Peaks", None))

from pyqtgraph import ImageView, PlotWidget
