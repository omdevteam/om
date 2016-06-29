# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ParameterTweakerUI.ui'
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
        MainWindow.resize(1133, 818)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.splitter = QtGui.QSplitter(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.splitter.sizePolicy().hasHeightForWidth())
        self.splitter.setSizePolicy(sizePolicy)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName(_fromUtf8("splitter"))
        self.layoutWidget = QtGui.QWidget(self.splitter)
        self.layoutWidget.setObjectName(_fromUtf8("layoutWidget"))
        self.verticalLayout0 = QtGui.QVBoxLayout(self.layoutWidget)
        self.verticalLayout0.setObjectName(_fromUtf8("verticalLayout0"))
        self.imageView = ImageView(self.layoutWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.imageView.sizePolicy().hasHeightForWidth())
        self.imageView.setSizePolicy(sizePolicy)
        self.imageView.setBaseSize(QtCore.QSize(0, 0))
        self.imageView.setObjectName(_fromUtf8("imageView"))
        self.verticalLayout0.addWidget(self.imageView)
        self.horizontalLayout0 = QtGui.QHBoxLayout()
        self.horizontalLayout0.setObjectName(_fromUtf8("horizontalLayout0"))
        self.backButton = QtGui.QPushButton(self.layoutWidget)
        self.backButton.setObjectName(_fromUtf8("backButton"))
        self.horizontalLayout0.addWidget(self.backButton)
        self.forwardButton = QtGui.QPushButton(self.layoutWidget)
        self.forwardButton.setObjectName(_fromUtf8("forwardButton"))
        self.horizontalLayout0.addWidget(self.forwardButton)
        self.randomButton = QtGui.QPushButton(self.layoutWidget)
        self.randomButton.setObjectName(_fromUtf8("randomButton"))
        self.horizontalLayout0.addWidget(self.randomButton)
        self.showHidePeaksCheckBox = QtGui.QCheckBox(self.layoutWidget)
        self.showHidePeaksCheckBox.setChecked(True)
        self.showHidePeaksCheckBox.setObjectName(_fromUtf8("showHidePeaksCheckBox"))
        self.horizontalLayout0.addWidget(self.showHidePeaksCheckBox)
        self.verticalLayout0.addLayout(self.horizontalLayout0)
        self.verticalLayoutWidget = QtGui.QWidget(self.splitter)
        self.verticalLayoutWidget.setObjectName(_fromUtf8("verticalLayoutWidget"))
        self.verticalLayout1 = QtGui.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout1.setSizeConstraint(QtGui.QLayout.SetDefaultConstraint)
        self.verticalLayout1.setObjectName(_fromUtf8("verticalLayout1"))
        spacerItem = QtGui.QSpacerItem(20, 732, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout1.addItem(spacerItem)
        self.hitLabel = QtGui.QLabel(self.verticalLayoutWidget)
        self.hitLabel.setObjectName(_fromUtf8("hitLabel"))
        self.verticalLayout1.addWidget(self.hitLabel)
        self.resolutionRingsCheckBox = QtGui.QCheckBox(self.verticalLayoutWidget)
        self.resolutionRingsCheckBox.setChecked(True)
        self.resolutionRingsCheckBox.setObjectName(_fromUtf8("resolutionRingsCheckBox"))
        self.verticalLayout1.addWidget(self.resolutionRingsCheckBox)
        self.horizontalLayout1 = QtGui.QHBoxLayout()
        self.horizontalLayout1.setObjectName(_fromUtf8("horizontalLayout1"))
        self.lastClickedPositionLabel = QtGui.QLabel(self.verticalLayoutWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lastClickedPositionLabel.sizePolicy().hasHeightForWidth())
        self.lastClickedPositionLabel.setSizePolicy(sizePolicy)
        self.lastClickedPositionLabel.setObjectName(_fromUtf8("lastClickedPositionLabel"))
        self.horizontalLayout1.addWidget(self.lastClickedPositionLabel)
        self.lastClickedPixelValueLabel = QtGui.QLabel(self.verticalLayoutWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lastClickedPixelValueLabel.sizePolicy().hasHeightForWidth())
        self.lastClickedPixelValueLabel.setSizePolicy(sizePolicy)
        self.lastClickedPixelValueLabel.setObjectName(_fromUtf8("lastClickedPixelValueLabel"))
        self.horizontalLayout1.addWidget(self.lastClickedPixelValueLabel)
        self.verticalLayout1.addLayout(self.horizontalLayout1)
        self.gridLayout.addWidget(self.splitter, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow", None))
        self.backButton.setText(_translate("MainWindow", "Back", None))
        self.forwardButton.setText(_translate("MainWindow", "Forward", None))
        self.randomButton.setText(_translate("MainWindow", "Random", None))
        self.showHidePeaksCheckBox.setText(_translate("MainWindow", "Show/Hide Peaks", None))
        self.hitLabel.setText(_translate("MainWindow", "Hit: - (- peaks)", None))
        self.resolutionRingsCheckBox.setText(_translate("MainWindow", "Min and max resolution rings", None))
        self.lastClickedPositionLabel.setText(_translate("MainWindow", "Last clicked position: - ", None))
        self.lastClickedPixelValueLabel.setText(_translate("MainWindow", "Pixel value: - ", None))

from pyqtgraph import ImageView
