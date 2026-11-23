from PyQt5 import uic, Qt#, QtGui, QtCore
import dataclasses
# from PyQt5.QtCore import *
# from PyQt5.QtGui import *
from PyQt5.QtGui import QIcon, QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import QFileDialog, QProgressDialog, QMessageBox
from PyQt5.Qt import *
from spec_routines import specread, is_spec_file
from mca_routines import mcaread
from mplwidget import MplWidget, errorbars, mesh
from matplotlib.widgets import MultiCursor
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib.gridspec as gridspec
from TwoDDetector import TwoDDetector
from scipy.optimize import leastsq
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d
from interp_compat import interp2d_linear   # scipy's interp2d was removed in SciPy 1.14
from scipy.interpolate import griddata
from sympy.solvers import solve 
from sympy import Symbol
import scipy as sy
import pylab as pl
import numpy as np
import time
import os
import glob
import sys
import matplotlib as mpl
from lmfit import minimize, Parameters, Parameter, report_fit, fit_report
from functools import partial
import traceback
import reader_log
from lss_core.resources import resource
from lss_core import stitching, reflectivity, fluorescence, normalise
from lss_core import cuts, mcafiles
from lss_core import gid as gidmod
from lss_core import pinhole
from lss_core import peaks
from lss_core import workbook as workbookmod
from lss_core import absorbers
from lss_core import preferences as prefs_store
from lss_core import trends as trendmod
from lss_core import burn as burnmod
from lss_core import series as seriesmod
from lss_core import live as livemod
from lss_core.absorbers import ABSFAC_10KEV
from lss_core.monitor import gain_factor, scan_rate
from lss_core.experiment import monitor_factor, absorber_setting
from lss_core.errors import ErrorModel, MonitorModel, MonitorTerms, script_kw, ELECTRONICS
#from TwoD_Integrate import integrate_2d


(Ui_MainWindow, QMainWindow) = uic.loadUiType(resource('mainwindow.ui'))

# per-frame lists built by updatePilImageList, one entry per row of the image list
FRAMELISTS=['pilAlpha', 'pilFileNames', 'pilFileQxs', 'pilFileQys', 'pilFileQzs', 'pilFrameNum', 'pilScanNum', 'pilTrueAlpha', 'pilX', 'pilY', 'pil_AbsNum', 'pil_Chi', 'pil_Dist', 'pil_Dth', 'pil_Gl2', 'pil_PDist', 'pil_Phi', 'pil_S1h', 'pil_S1v', 'pil_S4h', 'pil_S5h', 'pil_Sh', 'pil_Tth', 'pil_Wavelength']


def selectionDelayMs():
    """Delay before a change of the image-list selection is drawn
    ($LSS_READER_SELECTION_DELAY_MS, default 150; 0 draws at once)."""
    try:
        return max(0,int(os.environ.get('LSS_READER_SELECTION_DELAY_MS','150')))
    except ValueError:
        return 150


def runRemake(job):
    """In the worker thread (no Qt): remake one saved result from its recipe
    (lss_core.live) on a fresh Experiment of the SPEC file as it is now."""
    from lss_core.experiment import Experiment
    exp=Experiment(job['spec'])
    call,res,used,pts=livemod.remake(job['recipe'],job['scans'],exp,job['then'],job['now'])
    kind,items=livemod.item_for(call,res,used)
    return kind,items,livemod.with_scans(job['recipe'],used,pts),res


def scanRanges(values):
    """'6-9, 11' for scan numbers: consecutive runs written as ranges."""
    v=sorted(int(x) for x in values)
    out=[]
    k=0
    while k<len(v):
        j=k
        while j+1<len(v) and v[j+1]==v[j]+1:
            j+=1
        out.append(str(v[k]) if j==k else '%d-%d' % (v[k],v[j]))
        k=j+1
    return ', '.join(out)


def listText(values):
    """'1, 2, 3' for a sequence of numbers, whatever their type.

    str(list) of NumPy 2 scalars reads 'np.int64(1), np.int64(2)'; this is
    the one place where scan and frame lists are turned into text for
    titles, the command line and file headers.
    """
    return ', '.join(str(v.item() if hasattr(v, 'item') else v) for v in values)

class DoubleValidator(QDoubleValidator):
    def __init__(self, parent, bottom=0):
        QDoubleValidator.__init__(self, parent, bottom=bottom)
        self.bottom=bottom

    def validate(self, text, pos):
        try:
            if float(text)>= self.bottom:
                state = QDoubleValidator.Acceptable
            else:
                state = QDoubleValidator.Invalid
        except:
            state = QDoubleValidator.Invalid
        return state, text, pos


class IntValidator(QIntValidator):
    def __init__(self, parent, bottom=0):
        QIntValidator.__init__(self, parent, bottom=bottom)
        self.bottom=bottom

    def validate(self, text, pos):
        try:
            if float(text)>= self.bottom:
                state = QIntValidator.Acceptable
            else:
                state = QIntValidator.Invalid
        except:
            state = QIntValidator.Invalid
        return state, text, pos




class MainWindow (QMainWindow):
    """MainWindow inherits QMainWindow"""

    def __init__ (self, parent = None):
        QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.PlotWidget.setTabVisible(1, False)   # the Apex (CCD) tab: that detector is defunct
        self.pilatus=TwoDDetector('Pilatus')
        np.seterr(invalid='ignore',divide='ignore')
        self.mcaDirName='vortex'
        self.pilDirName='pilatus'
        self.beamline='APS-15IDC'
        self.specData={}
        self.specPar={}
        self.startLineNum=0
        self.endScanNum=0
        self.refData=[]
        self.refInfo=[]
        self.det=None   #set to 'Pilatus' once images are loaded
        self.refQzSelectedItems=[]
        self.reffnames=[]
        self.mcaIntData=[]
        self.refQc=float(self.ui.refQcLineEdit.text())
        self.ui.AbsFacLineEdit.setToolTip('Transmission factor per absorber unit. SPEC #A gives the absorber in these units '
                                          '(0: no absorbers). Default: 50 um of Al at 10 keV, exp(mu/rho rho t) = %s '
                                          '(lss_core/absorbers.py); it depends on the energy. "cal": the calibrated '
                                          'foils are in use (File > Preferences).' % ABSFAC_10KEV)
        self.ui.AbsFacLineEdit.setText(str(ABSFAC_10KEV))
        self.absfac=float(self.ui.AbsFacLineEdit.text())
        # the factor in use is the one the field shows, however it was set
        # (typed, or preset when a SPEC file with Pilatus images is opened)
        self.ui.AbsFacLineEdit.textChanged.connect(self.absFacChanged)
        self.reffiles=[]
        self.selectedBgFrameNums=[]
        self.selectedreffiles_rows=[]
        self.mcafitplotstatus = 0
        self.mcafiles=[]
        self.mcafnames=[]
        self.selectedMcaScanNums=[]
        self.nomMcaData={}            # normalised MCA frames of the last plot
        self.selectedmcafiles_rows=[]
        self.selectedScans=[]         # scan list items / numbers selected in the Scan list
        self.selectedScanNums=[]
        self.scanlines=[]
        self.scanCenter={}
        self.cutData={}               # filled by the Line/Area cut
        self.selectedPilFramesNums=[]
        self.pilScanNum=[]
        self.selectedplotfiles_rows=[]
        self.ui.PlotWidget.setCurrentIndex(0)
        self.directory=os.getcwd()
        self.pilGIDshow=0
        self.pilGISAXSshow=0
        self.pilmovieindex=0
        self.refpatchindex=0
        self.formfactor_r=0
        self.formfactor_rxy=0
        self.formfactor_rz=0
        self.mcafitstatus=0
        self.mcafitallstatus=0
        self.fitplotstatus = 0
        self.cutDirItems=['Q H Cut [Qz_min : Qz_max]', 'Q V Cut [Qxy_min : Qxy_max]', 'Pix H Cut [Pix_bottom : Pix_top]', 'Pix V Cut [Pix_left : Pix_right]']
        self.ui.pilCutDirComboBox.clear()
        self.ui.pilCutDirComboBox.addItems(self.cutDirItems)
        self.plotfiles=[]
        self.twodplotfiles=[]
        self.selected2dplotfiles_rows=[]   # rows selected in the 2D_Plot file list
        self.plot2dindex=None               # None until a 2d data file has been plotted
        self.halftab='      '
        self.xyzformat='x=%.3f,y=%.3f,z=%.2e'
        # mpl.rc('axes',color_cycle=['b','r','g','c','m','y','k'])
        self.ui.plotMoveUpPushButton.setIcon(QIcon(resource('arrow_up.png')))
        self.ui.plotMoveDownPushButton.setIcon(QIcon(resource('arrow_down.png')))
        self.prefs=prefs_store.load()           # before the signals: the fit controls read their options from it
        self.wrapReductionsForAutoSave()        # before the signals: every connection reaches the wrapped method
        self.init_signals()
        self.log=reader_log.get_logger()
        self.initMessagePane()
        self.initScriptPane()
        self.initErrorPane()
        self.initMonitorGainOption()
        self.initAbsFacFromEnergy()
        self.initPreferences()
        self.initToolsMenu()
        self.gidParams=gidmod.GIDParams()     # GID patch settings (worksheet, F61)
        self.gidJoinLog=[]
        self.gidLevels=[]
        self.gidWorksheet=None
        self.ui.gidComboBox.addItem('Worksheet')
        self.ui.gidComboBox.addItem('Save to workbook')
        self.initSpecPointLabels()
        self.specFileName=None
        #self.openSpecFile(fname='C:/Users/bu/Desktop/sample_data/sample')
        self.initValidator()
        self.nguiWindow=None
        if self.prefs.get('ngui',False):
            self.setNgui(True)


    def init_signals(self):
        # self.connect(self.ui.actionAbout, SIGNAL('triggered()'),self.showAbout)
        self.ui.actionAbout.triggered.connect(self.showAbout)
        # self.connect(self.ui.actionOpen_Spec_File, SIGNAL('triggered()'),self.openSpecFile)
        self.ui.actionOpen_Spec_File.triggered.connect(lambda x:self.openSpecFile(fname=None))
        # self.connect(self.ui.speUpSpeFilePushButton, SIGNAL('clicked()'),self.readSpecFile)
        self.ui.speUpSpeFilePushButton.clicked.connect(self.updateSpecFile)
        # self.connect(self.ui.actionAPS_15IDC, SIGNAL('triggered()'),self.selectAPS_15IDC)
        self.ui.actionAPS_15IDC.triggered.connect(self.selectAPS_15IDC)
        self.ui.actionAPS_9IDC.setVisible(False)   # 9-ID-C is not supported (owner, 2026-11-17)
        # self.connect(self.ui.actionG_l2, SIGNAL('triggered()'), self.calg_l2)
        self.ui.actionG_l2.triggered.connect(self.calg_l2)
        # self.connect(self.ui.actionG_l3, SIGNAL('triggered()'), self.calg_l3)
        self.ui.actionG_l3.triggered.connect(self.calg_l3)
        # self.connect(self.ui.actionAbs_ratio, SIGNAL('triggered()'), self.calabsrat)
        self.ui.actionAbs_ratio.triggered.connect(self.calabsrat)
        # self.connect(self.ui.scanListWidget, SIGNAL('itemSelectionChanged()'),self.scanListChanged)
        self.ui.scanListWidget.itemSelectionChanged.connect(self.scanListChanged)
       # self.connect(self.ui.scanListWidget, SIGNAL('itemClicked(QListWidgetItem*)'),self.scanListChanged)
       #  self.connect(self.ui.spLogXCheckBox, SIGNAL('stateChanged(int)'),self.updateSpecPlotData)
        self.ui.spLogXCheckBox.stateChanged.connect(self.updateSpecPlotData)
        # self.connect(self.ui.spLogYCheckBox, SIGNAL('stateChanged(int)'),self.updateSpecPlotData)
        self.ui.spLogYCheckBox.stateChanged.connect(self.updateSpecPlotData)
        # self.connect(self.ui.spGridCheckBox, SIGNAL('stateChanged(int)'),self.updateSpecPlotData)
        self.ui.spGridCheckBox.stateChanged.connect(self.updateSpecPlotData)
        # self.connect(self.ui.spLegendCheckBox, SIGNAL('stateChanged(int)'),self.updateSpecPlotData)
        self.ui.spLegendCheckBox.stateChanged.connect(self.updateSpecPlotData)
        # self.connect(self.ui.spNCheckBox, SIGNAL('stateChanged(int)'),self.updateSpecPlotData)
        self.ui.spNCheckBox.stateChanged.connect(self.updateSpecPlotData)
        # self.connect(self.ui.spLegendLocComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spLegendLocComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
        # self.connect(self.ui.spXComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spXComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
        # self.connect(self.ui.spYComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spYComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
        # self.connect(self.ui.spY2ComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spY2ComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
        # self.connect(self.ui.spNComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spNComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
     #    self.connect(self.ui.spExportPushButton, SIGNAL('clicked()'),self.specSaveData)
        self.ui.spExportPushButton.clicked.connect(self.specSaveData)
     #    self.connect(self.ui.scansLineEdit, SIGNAL('returnPressed()'),self.scanListInputChanged)
        self.ui.scansLineEdit.returnPressed.connect(self.scanListInputChanged)
     #    self.connect(self.ui.imageListWidget, SIGNAL('itemSelectionChanged()'),self.imageSelectedScanChanged)
        self.ui.imageListWidget.itemSelectionChanged.connect(self.imageSelectedScanChanged)
     #    self.connect(self.ui.mcaLogXCheckBox, SIGNAL('stateChanged(int)'),self.updateMcaPlotData)
        self.ui.mcaLogXCheckBox.stateChanged.connect(self.mcaPlotSettings)
     #    self.connect(self.ui.mcaLogYCheckBox, SIGNAL('stateChanged(int)'),self.updateMcaPlotData)
        self.ui.mcaLogYCheckBox.stateChanged.connect(self.mcaPlotSettings)
     #    self.connect(self.ui.mcaGridCheckBox, SIGNAL('stateChanged(int)'),self.updateMcaPlotData)
        self.ui.mcaGridCheckBox.stateChanged.connect(self.mcaPlotSettings)
     #    self.connect(self.ui.mcaLegendCheckBox, SIGNAL('stateChanged(int)'),self.updateMcaPlotData)
        self.ui.mcaLegendCheckBox.stateChanged.connect(self.mcaPlotSettings)
     #    self.connect(self.ui.mcaNormComboBox, SIGNAL('currentIndexChanged(int)'),self.updateMcaPlotData)
        self.ui.mcaNormComboBox.currentIndexChanged.connect(self.updateMcaPlotData)
     #    self.connect(self.ui.mcaLegendLocComboBox, SIGNAL('currentIndexChanged(int)'),self.updateMcaPlotData)
        self.ui.mcaLegendLocComboBox.currentIndexChanged.connect(self.mcaPlotSettings)
     #    self.connect(self.ui.mcaCalibCheckBox, SIGNAL('stateChanged(int)'),self.updateMcaPlotData)
        self.ui.mcaCalibCheckBox.stateChanged.connect(self.updateMcaPlotData)
     #    self.connect(self.ui.mcaCalibConLineEdit, SIGNAL('returnPressed()'),self.updateMcaPlotData)
        self.ui.mcaCalibConLineEdit.returnPressed.connect(self.updateMcaPlotData)
     #    self.connect(self.ui.mcaCalibLinLineEdit, SIGNAL('returnPressed()'),self.updateMcaPlotData)
        self.ui.mcaCalibLinLineEdit.returnPressed.connect(self.updateMcaPlotData)
     #    self.connect(self.ui.mcaCalibQuaLineEdit, SIGNAL('returnPressed()'),self.updateMcaPlotData)
        self.ui.mcaCalibQuaLineEdit.returnPressed.connect(self.updateMcaPlotData)
        self.ui.mcaRanLineEdit.returnPressed.connect(self.updateMCAPlotVline)
     #    self.connect(self.ui.gixSumCheckBox,SIGNAL('stateChanged(int)'),self.update2dPlots)
        self.ui.gixSumCheckBox.stateChanged.connect(self.update2dPlots)
        self.ui.gixSumCheckBox.setToolTip('Sum the selected frames (same Qz): counts and monitors summed, then '
                                          'normalised once, ΣN/ΣM (the pooled estimate; owner, 2026-11-23, F91). With '
                                          'unequal monitors it weights each frame by its monitor, over its absorber and '
                                          'gain factors. The legacy mean of the normalised frames is a Reduction option.')
     #   self.connect(self.ui.pilBPCiteSpinBox, SIGNAL('valueChanged(int)'), self.imageSelectedScanChanged)
        self.ui.pilBPCiteSpinBox.valueChanged.connect(self.imageSelectedScanChanged)
     #   self.connect(self.ui.pilBPCfacSpinBox, SIGNAL('valueChanged(int)'), self.imageSelectedScanChanged)
        self.ui.pilBPCfacSpinBox.valueChanged.connect(self.imageSelectedScanChanged)
     #    self.connect(self.ui.pilPinholeCheckBox,SIGNAL('stateChanged(int)'),self.update2dPlots)
        self.ui.pilPinholeCheckBox.stateChanged.connect(self.update2dPlots)
        self.ui.pilPinholeCheckBox.blockSignals(True)
        self.ui.pilPinholeCheckBox.setChecked(True)      # pinhole geometry is the default (owner, 2026-11-18)
        self.ui.pilPinholeCheckBox.blockSignals(False)
        self.ui.pilPinholeCheckBox.setToolTip('Pinhole geometry (the default): frames at Det_Th > 1 deg get their horizontal '
                                              'angle from the S4-detector distance (#B1 4th number), each column through the '
                                              'pinhole; the vertical angle always uses the sample-detector distance. Untick for '
                                              'the sample-detector distance everywhere.')
     #    self.connect(self.ui.pilLogIntCheckBox, SIGNAL('stateChanged(int)'),self.update2dPlots)
        self.ui.pilLogIntCheckBox.stateChanged.connect(self.update2dPlots)
     #    self.connect(self.ui.imageSelectAllCheckBox, SIGNAL('clicked()'),self.selectAllImages)
        self.ui.imageSelectAllCheckBox.clicked.connect(self.selectAllImages)
     #    self.connect(self.ui.imageListWidget, SIGNAL('clicked(QModelIndex)'),self.unSelectedAllImages)
        self.ui.imageListWidget.clicked.connect(self.unSelectedAllImages)
     #    self.connect(self.ui.pilSpecCheckBox,SIGNAL('stateChanged(int)'),self.update2dPlots)
        self.ui.pilSpecCheckBox.stateChanged.connect(self.update2dPlots)
     #    self.connect(self.ui.pilCMapComboBox, SIGNAL('currentIndexChanged(int)'), self.update2dPlots)
        self.ui.pilCMapComboBox.currentIndexChanged.connect(self.update2dPlots)
     #    self.connect(self.ui.pilMinLineEdit, SIGNAL('returnPressed()'),self.update2dPlots)
        self.ui.pilMinLineEdit.returnPressed.connect(self.update2dPlots)
     #    self.connect(self.ui.pilMaxLineEdit, SIGNAL('returnPressed()'),self.update2dPlots)
        self.ui.pilMaxLineEdit.returnPressed.connect(self.update2dPlots)
     #    self.connect(self.ui.pilAxesComboBox, SIGNAL('currentIndexChanged(int)'), self.update2dPlots)
        self.ui.pilAxesComboBox.currentIndexChanged.connect(self.update2dPlots)
     #    self.connect(self.ui.pilMinHorizontalSlider, SIGNAL('sliderReleased()'),self.updatePilMinSlider)
        self.ui.pilMinHorizontalSlider.sliderReleased.connect(self.updatePilMinSlider)
     #    self.connect(self.ui.pilMaxHorizontalSlider, SIGNAL('sliderReleased()'),sel.updatePilMaxSlider)
        self.ui.pilMaxHorizontalSlider.sliderReleased.connect(self.updatePilMaxSlider)
     #    self.connect(self.ui.pilRefPushButton,SIGNAL('clicked()'),self.refPlotWin)
        self.ui.pilRefPushButton.clicked.connect(self.refPlotWin)
     #    self.connect(self.ui.pilRefPatchPushButton,SIGNAL('clicked()'),self.pilRefPatchData)
        self.ui.pilRefPatchPushButton.clicked.connect(self.pilRefPatchData)
     #    self.connect(self.ui.refSlitLineEdit,SIGNAL('returnPressed()'),self.refQzListSelectionChanged)
        self.ui.refSlitLineEdit.returnPressed.connect(self.refQzListSelectionChanged)
     #    self.connect(self.ui.refBGOffLineEdit,SIGNAL('returnPressed()'),self.refQzListSelectionChanged)
        self.ui.refBGOffLineEdit.returnPressed.connect(self.refQzListSelectionChanged)
     #    self.connect(self.ui.refQzListWidget, SIGNAL('itemSelectionChanged()'),self.refQzListSelectionChanged)
        self.ui.refQzListWidget.itemSelectionChanged.connect(self.refQzListSelectionChanged)
     #    self.connect(self.ui.refBGDirComboBox,SIGNAL('currentIndexChanged(int)'),self.refQzListSelectionChanged)
        self.ui.refBGDirComboBox.currentIndexChanged.connect(self.refQzListSelectionChanged)
     #    self.connect(self.ui.refAnalyzePushButton,SIGNAL('clicked()'),self.refAnalyze)
        self.ui.refAnalyzePushButton.clicked.connect(self.refAnalyze)
     #    self.connect(self.ui.refBPCFacLineEdit, SIGNAL('returnPressed()'),self.refAnalyze)
        self.ui.refBPCFacLineEdit.returnPressed.connect(self.refAnalyzeFromField)
     #  #self.connect(self.ui.AbsFacLineEdit, SIGNAL('returnPressed()'),self.refDoBPC)
        #self.ui.AbsFacLineEdit.returnPressed.connect(self.refDoBPC)
     #    self.connect(self.ui.refAcceptPushButton, SIGNAL('clicked()'), self.updateRefDataList)
        self.ui.refAcceptPushButton.clicked.connect(self.updateRefDataList)
     #    self.connect(self.ui.refAnalyzeAllPushButton, SIGNAL('clicked()'),self.refAnalyzeAll)
        self.ui.refAnalyzeAllPushButton.clicked.connect(self.refAnalyzeAll)
     #    #self.connect(self.ui.refDataListWidget,SIGNAL('itemChanged(QListWidgetItem*)'), self.updateRefPlotData)
        self.ui.refDataListWidget.itemChanged.connect(self.updateRefPlotData)
     #    self.connect(self.ui.refQcLineEdit,SIGNAL('returnPressed()'),self.updateRefPlotData)
        self.ui.refQcLineEdit.returnPressed.connect(self.updateRefPlotData)
     #    self.connect(self.ui.refQoffLineEdit,SIGNAL('returnPressed()'),self.updateRefPlotData)
        self.ui.refQoffLineEdit.returnPressed.connect(self.updateRefPlotData)
     #    self.connect(self.ui.refRRFCheckBox,SIGNAL('stateChanged(int)'),self.updateRefPlotData)
        self.ui.refRRFCheckBox.stateChanged.connect(self.updateRefPlotData)
     #    self.connect(self.ui.refLogYCheckBox,SIGNAL('stateChanged(int)'),self.updateRefPlotData)
        self.ui.refLogYCheckBox.stateChanged.connect(self.updateRefPlotData)
     #    self.connect(self.ui.refQzSqrCheckBox,SIGNAL('stateChanged(int)'),self.updateRefPlotData)
        self.ui.refQzSqrCheckBox.stateChanged.connect(self.updateRefPlotData)
     #    self.connect(self.ui.refDelPushButton,SIGNAL('clicked()'),self.delRefDataList)
        self.ui.refDelPushButton.clicked.connect(self.delRefDataList)
     #    self.connect(self.ui.refSeaWinLineEdit, SIGNAL('returnPressed()'),self.refAnalyze)
        self.ui.refSeaWinLineEdit.returnPressed.connect(self.refAnalyzeFromField)
     #    self.connect(self.ui.refExportPushButton,SIGNAL('clicked()'), self.saveRefData)
        self.ui.refExportPushButton.clicked.connect(self.saveRefData)
     #    self.connect(self.ui.refAddFilePushButton, SIGNAL('clicked()'), self.addRefFiles)
        self.ui.refAddFilePushButton.clicked.connect(self.addRefFiles)
     #    self.connect(self.ui.refRemoveFilePushButton, SIGNAL('clicked()'), self.removeRefFiles)
        self.ui.refRemoveFilePushButton.clicked.connect(self.removeRefFiles)
     #    self.connect(self.ui.refRefFileListWidget, SIGNAL('itemSelectionChanged()'), self.updateSelectedRefFiles)
        self.ui.refRefFileListWidget.itemSelectionChanged.connect(self.updateSelectedRefFiles)
     #    self.connect(self.ui.refLegendCheckBox,SIGNAL('stateChanged(int)'), self.updateRefPlotData)
        self.ui.refLegendCheckBox.stateChanged.connect(self.updateRefPlotData)
     #    self.connect(self.ui.refLegendLocComboBox,SIGNAL('currentIndexChanged(int)'), self.updateRefPlotData)
        self.ui.refLegendLocComboBox.currentIndexChanged.connect(self.updateRefPlotData)
     #    #self.connect(self.ui.refCenCheckBox, SIGNAL('stateChanged(int)'),)
     #    self.connect(self.ui.refCenLineEdit, SIGNAL('returnPressed()'), self.refAnalyze)
        self.ui.refCenLineEdit.returnPressed.connect(self.refAnalyzeFromField)
     #    self.connect(self.ui.pilLineAreaPushButton, SIGNAL('clicked()'), self.updateCutData)
        self.ui.pilLineAreaPushButton.clicked.connect(self.lineAreaCut)
     #    self.connect(self.ui.pilIntRangeLineEdit, SIGNAL('returnPressed()'), self.updateCutData)
        self.ui.pilIntRangeLineEdit.returnPressed.connect(self.updateCutData)
     #    self.connect(self.ui.cutLogXCheckBox, SIGNAL('stateChanged(int)'),self.updateCutPlotData)
        self.ui.cutLogXCheckBox.stateChanged.connect(self.updateCutPlotData)
     #    self.connect(self.ui.cutLogYCheckBox, SIGNAL('stateChanged(int)'),self.updateCutPlotData)
        self.ui.cutLogYCheckBox.stateChanged.connect(self.updateCutPlotData)
     #    self.connect(self.ui.cutGridCheckBox, SIGNAL('stateChanged(int)'),self.updateCutPlotData)
        self.ui.cutGridCheckBox.stateChanged.connect(self.updateCutPlotData)
     #    self.connect(self.ui.cutLegendCheckBox, SIGNAL('stateChanged(int)'),self.updateCutPlotData)
        self.ui.cutLegendCheckBox.stateChanged.connect(self.updateCutPlotData)
        self.setupCutFit()
        self.setupSeriesBox()
        self.setupLive()
     #    self.connect(self.ui.cutLegendLocComboBox, SIGNAL('currentIndexChanged(int)'),self.updateCutPlotData)
        self.ui.cutLegendLocComboBox.currentIndexChanged.connect(self.updateCutPlotData)
     #    self.connect(self.ui.cutErrorbarCheckBox, SIGNAL('stateChanged(int)'),self.updateCutData)
        self.ui.cutErrorbarCheckBox.stateChanged.connect(self.updateCutData)
     #    self.connect(self.ui.cutExportPushButton, SIGNAL('clicked()'),self.saveCutData)
        self.ui.cutExportPushButton.clicked.connect(self.saveCutData)
     #    self.connect(self.ui.cutOffsetCheckBox, SIGNAL('stateChanged(int)'),self.updateCutData)
        self.ui.cutOffsetCheckBox.stateChanged.connect(self.updateCutData)
     #    self.connect(self.ui.cutOffsetLineEdit, SIGNAL('returnPressed()'),self.updateCutData)
        self.ui.cutOffsetLineEdit.returnPressed.connect(self.updateCutData)
     #    self.connect(self.ui.mcaExportPushButton, SIGNAL('clicked()'),self.saveMcaData)
        self.ui.mcaExportPushButton.clicked.connect(self.saveMcaData)
     #    self.connect(self.ui.mcaOffsetCheckBox, SIGNAL('stateChanged(int)'),self.updateMcaPlotData)
        self.ui.mcaOffsetCheckBox.stateChanged.connect(self.updateMcaPlotData)
     #    self.connect(self.ui.mcaOffsetLineEdit, SIGNAL('returnPressed()'),self.updateMcaPlotData)
        self.ui.mcaOffsetLineEdit.returnPressed.connect(self.updateMcaPlotData)
     #    self.connect(self.ui.mcaFitPushButton, SIGNAL('clicked()'), self.mcaPeakFit)
        self.ui.mcaFitPushButton.clicked.connect(self.mcaPeakFit)
     #    self.connect(self.ui.mcaFitAllPushButton, SIGNAL('clicked()'), self.mcaPeakFitAll)
        self.ui.mcaFitAllPushButton.clicked.connect(self.mcaPeakFitAll)
     # #   self.connect(self.ui.mcaSumPushButton, SIGNAL('clicked()'), self.mcaSum)
     #    self.connect(self.ui.mcaSumAllPushButton, SIGNAL('clicked()'), self.mcaSumAll)
        self.ui.mcaSumAllPushButton.clicked.connect(self.mcaSumAll)
     #    self.connect(self.ui.mcaAcceptPushButton, SIGNAL('clicked()'), self.mcaAcceptPeak)
        self.ui.mcaAcceptPushButton.clicked.connect(self.mcaAcceptPeak)
     # #   self.connect(self.ui.mcaFrameCheckBox, SIGNAL('stateChanged(int)'), self.updateMcaInt)
     # #   self.connect(self.ui.mcaQzCheckBox, SIGNAL('stateChanged(int)'), self.updateMcaInt)
     # #   self.connect(self.ui.mcaEnergyCheckBox, SIGNAL('stateChanged(int)'), self.updateMcaInt)
     #    self.connect(self.ui.mcaXAxisComboBox,SIGNAL('currentIndexChanged(int)'), self.updateMcaInt)
        self.ui.mcaXAxisComboBox.currentIndexChanged.connect(self.updateMcaInt)
     #    self.connect(self.ui.mcaDelPushButton, SIGNAL('clicked()'), self.mcaDelIntData)
        self.ui.mcaDelPushButton.clicked.connect(self.mcaDelIntData)
     #    self.connect(self.ui.mcaMergePushButton, SIGNAL('clicked()'), self.mcaIntMergeDia)
        self.ui.mcaMergePushButton.clicked.connect(self.mcaIntMergeDia)
     #    self.connect(self.ui.mcaExportIntPushButton, SIGNAL('clicked()'), self.mcaSaveIntData)
        self.ui.mcaExportIntPushButton.clicked.connect(self.mcaSaveIntData)
     #    self.connect(self.ui.mcaAddFilePushButton, SIGNAL('clicked()'),self.addMcaFiles)
        self.ui.mcaAddFilePushButton.clicked.connect(self.addMcaFiles)
     #    self.connect(self.ui.mcaRemoveFilePushButton, SIGNAL('clicked()'),self.removeMcaFiles)
        self.ui.mcaRemoveFilePushButton.clicked.connect(self.removeMcaFiles)
     #    self.connect(self.ui.mcaFileListWidget, SIGNAL('itemSelectionChanged()'),self.updateSelectedMcaFiles)
        self.ui.mcaFileListWidget.itemSelectionChanged.connect(self.updateSelectedMcaFiles)
     #    self.connect(self.ui.cutClearGraphPushButton, SIGNAL('clicked()'),self.clearCutGraph)
        self.ui.cutClearGraphPushButton.clicked.connect(self.clearCutGraph)
     #    self.connect(self.ui.backgroundPushButton, SIGNAL('clicked()'),self.addBGImagestoList)
        self.ui.backgroundPushButton.clicked.connect(self.addBGImagestoList)
     #    self.connect(self.ui.removePushButton, SIGNAL('clicked()'), self.removeBGImages)
        self.ui.removePushButton.clicked.connect(self.removeBGImages)
     #    self.connect(self.ui.backgroundListWidget, SIGNAL('itemSelectionChanged()'),self.bgSelectionChanged)
        self.ui.backgroundListWidget.itemSelectionChanged.connect(self.bgSelectionChanged)
     #    self.connect(self.ui.bgSelectAllCheckBox, SIGNAL('stateChanged(int)'),self.bgSelectAll)
        self.ui.bgSelectAllCheckBox.stateChanged.connect(self.bgSelectAll)
        self.ui.bgFacLineEdit.returnPressed.connect(self.imageSelectedScanChanged)   # re-read with the new factor, whichever detector
     #    self.connect(self.ui.scanListWidget, SIGNAL('doubleClicked(QModelIndex)'),self.displayScanInfo)
        self.ui.scanListWidget.doubleClicked.connect(self.displayScanInfo)
     #   # self.connect(self.ui.pilGIDPushButton, SIGNAL('clicked()'),self.pilGIDData)
     #   # self.connect(self.ui.pilGIDPatchPushButton, SIGNAL('clicked()'),self.pilGIDpatchData)
     #    self.connect(self.ui.gidComboBox, SIGNAL('activated(int)'),self.pilGID)
        self.ui.gidComboBox.activated.connect(self.pilGID)
     #    self.connect(self.ui.gisaxsComboBox, SIGNAL('activated(int)'),self.pilGISAXS)
        self.ui.gisaxsComboBox.activated.connect(self.pilGISAXS)
     #    self.connect(self.ui.pilMoviePushButton, SIGNAL('clicked()'),self.pilMovieShow)
        self.ui.pilMoviePushButton.clicked.connect(self.pilMovieShow)
     #    self.connect(self.ui.pilBurnPushButton, SIGNAL('clicked()'),self.pilBurnTest)
        self.ui.pilBurnPushButton.clicked.connect(self.pilBurnTest)
     #    self.connect(self.ui.pilGioxsPushButton,SIGNAL('clicked()'),self.gioxsDisplay)
        self.ui.pilGioxsPushButton.clicked.connect(self.gioxsDisplay)
     #    self.connect(self.ui.refNormFacCheckBox, SIGNAL('stateChanged(int)'),self.updateRefPlotData)
        self.ui.refNormFacCheckBox.stateChanged.connect(self.updateRefPlotData)
     #    self.connect(self.ui.pilAspectComboBox, SIGNAL('currentIndexChanged(int)'),self.update2dPlots)
        self.ui.pilAspectComboBox.currentIndexChanged.connect(self.update2dPlots)
     #    self.connect(self.ui.plotAddFilePushButton, SIGNAL('clicked()'),self.addPlotFile)
        self.ui.plotAddFilePushButton.clicked.connect(self.addPlotFile)
     #    self.connect(self.ui.plotRemoveFilePushButton, SIGNAL('clicked()'), self.removePlotFile)
        self.ui.plotRemoveFilePushButton.clicked.connect(self.removePlotFile)
     #    self.connect(self.ui.plotFileListWidget, SIGNAL('itemSelectionChanged()'),self.updateSelectedPlotFile)
        self.ui.plotFileListWidget.itemSelectionChanged.connect(self.updateSelectedPlotFile)
     #    self.connect(self.ui.plotLogXCheckBox, SIGNAL('stateChanged(int)'),self.updatePlotPlot)
        self.ui.plotLogXCheckBox.stateChanged.connect(self.updatePlotPlot)
     #    self.connect(self.ui.plotLogYCheckBox, SIGNAL('stateChanged(int)'),self.updatePlotPlot)
        self.ui.plotLogYCheckBox.stateChanged.connect(self.updatePlotPlot)
     #    self.connect(self.ui.plotGridCheckBox, SIGNAL('stateChanged(int)'),self.updatePlotPlot)
        self.ui.plotGridCheckBox.stateChanged.connect(self.updatePlotPlot)
     #    self.connect(self.ui.plotLegendCheckBox, SIGNAL('stateChanged(it)'),self.updatePlotPlot)
        self.ui.plotLegendCheckBox.stateChanged.connect(self.updatePlotPlot)
     #    self.connect(self.ui.plotLegendLocComboBox, SIGNAL('currentIndexChanged(int)'),self.updatePlotPlot)
        self.ui.plotLegendLocComboBox.currentIndexChanged.connect(self.updatePlotPlot)
     #    self.connect(self.ui.onedLabelSizeSpinBox,SIGNAL('valueChanged(int)'),self.updatePlotPlot)
        self.ui.onedLabelSizeSpinBox.valueChanged.connect(self.updatePlotPlot)
     #    self.connect(self.ui.onedTickSizeSpinBox,SIGNAL('valueChanged(int)'),self.updatePlotPlot)
        self.ui.onedTickSizeSpinBox.valueChanged.connect(self.updatePlotPlot)
     #    self.connect(self.ui.onedStyComboBox,SIGNAL('currentIndexChanged(int)'),self.updatePlotPlot)
        self.ui.onedStyComboBox.currentIndexChanged.connect(self.updatePlotPlot)
     #    self.connect(self.ui.plotRSPushButton, SIGNAL('clicked()'), self.setPlotScale)
        self.ui.plotRSPushButton.clicked.connect(self.setPlotScale)
     #    self.connect(self.ui.plotPFPushButton, SIGNAL('clicked()'), self.dataPeakFit)
        self.ui.plotPFPushButton.clicked.connect(self.dataPeakFit)
     #    self.connect(self.ui.plotMoveUpPushButton, SIGNAL('clicked()'), self.upPlotFile)
        self.ui.plotMoveUpPushButton.clicked.connect(self.upPlotFile)
     #    self.connect(self.ui.plotMoveDownPushButton, SIGNAL('clicked()'), self.downPlotFile)
        self.ui.plotMoveDownPushButton.clicked.connect(self.downPlotFile)
     #    self.connect(self.ui.graPushButton, SIGNAL('clicked()'),self.graPlotPlot)
        self.ui.graPushButton.clicked.connect(self.graPlotPlot)
     #    self.connect(self.ui.savegraPushButton, SIGNAL('clicked()'),self.saveGraPlotData)
        self.ui.savegraPushButton.clicked.connect(self.saveGraPlotData)
     #    self.connect(self.ui.twodPlotAddFilePushButton, SIGNAL('clicked()'),self.add2dPlotFile)
        self.ui.twodPlotAddFilePushButton.clicked.connect(self.add2dPlotFile)
     #    self.connect(self.ui.twodPlotRemoveFilePushButton, SIGNAL('clicked()'), self.remove2dPlotFile)
        self.ui.twodPlotRemoveFilePushButton.clicked.connect(self.remove2dPlotFile)
     #    self.connect(self.ui.twodPlotFileListWidget, SIGNAL('itemSelectionChanged()'),self.updateSelected2dPlotFile)
        self.ui.twodPlotFileListWidget.itemSelectionChanged.connect(self.updateSelected2dPlotFile)
     #    self.connect(self.ui.twodCMapComboBox, SIGNAL('currentIndexChanged(int)'), self.update2dPlotPlot)
        self.ui.twodCMapComboBox.currentIndexChanged.connect(self.update2dPlotPlot)
     #    self.connect(self.ui.twodLogIntCheckBox, SIGNAL('stateChanged(int)'),self.update2dPlotPlot)
        self.ui.twodLogIntCheckBox.stateChanged.connect(self.update2dPlotPlot)
     #    self.connect(self.ui.twodMinHorizontalSlider, SIGNAL('sliderReleased()'),self.update2dPlotPlot)
        self.ui.twodMinHorizontalSlider.sliderReleased.connect(self.update2dPlotPlot)
     #    self.connect(self.ui.twodMaxHorizontalSlider, SIGNAL('sliderReleased()'),self.update2dPlotPlot)
        self.ui.twodMaxHorizontalSlider.sliderReleased.connect(self.update2dPlotPlot)
     #    self.connect(self.ui.twodMinLineEdit, SIGNAL('returnPressed()'),self.update2dPlotPlot)
        self.ui.twodMinLineEdit.returnPressed.connect(self.update2dPlotPlot)
     #    self.connect(self.ui.twodMaxLineEdit, SIGNAL('returnPressed()'),self.update2dPlotPlot)
        self.ui.twodMaxLineEdit.returnPressed.connect(self.update2dPlotPlot)
     #    self.connect(self.ui.twodUpdatePlotPushButton, SIGNAL('clicked()'),self.update2dIntPolData)
        self.ui.twodUpdatePlotPushButton.clicked.connect(self.update2dIntPolData)
     #    self.connect(self.ui.twodIntPolComboBox, SIGNAL('currentIndexChanged(int)'),self.update2dPlotPlot)
        self.ui.twodIntPolComboBox.currentIndexChanged.connect(self.update2dPlotPlot)
     #    self.connect(self.ui.twodLabelSizeSpinBox,SIGNAL('valueChanged(int)'),self.update2dPlotPlot)
        self.ui.twodLabelSizeSpinBox.valueChanged.connect(self.update2dPlotPlot)
     #    self.connect(self.ui.twodTickSizeSpinBox,SIGNAL('valueChanged(int)'),self.update2dPlotPlot)
        self.ui.twodTickSizeSpinBox.valueChanged.connect(self.update2dPlotData)
     #    self.connect(self.ui.twodColBarCheckBox,SIGNAL('stateChanged(int)'),self.update2dPlotPlot)
        self.ui.twodColBarCheckBox.stateChanged.connect(self.update2dPlotPlot)
     #    self.connect(self.ui.twodMinHorizontalSlider, SIGNAL('sliderReleased()'), self.update2dMinSlider)
        self.ui.twodMinHorizontalSlider.sliderReleased.connect(self.update2dMinSlider)
     #    self.connect(self.ui.twodMaxHorizontalSlider, SIGNAL('sliderReleased()'), self.update2dMaxSlider)
        self.ui.twodMaxHorizontalSlider.sliderReleased.connect(self.update2dMaxSlider)
        self.ui.pilCutDirComboBox.currentIndexChanged.connect(self.updatePilCutRange)

    def initValidator(self):
        qdoublevalidator1 = DoubleValidator(self, bottom=1)
        qdoublevalidator0 = DoubleValidator(self, bottom=0)
        qintvaliator1 = IntValidator(self, bottom=1)
        self.ui.AbsFacLineEdit.setValidator(qdoublevalidator1)
        self.ui.bgFacLineEdit.setValidator(qdoublevalidator0)
        self.ui.pilSDDistLineEdit.setValidator(qdoublevalidator1)
       # self.ui.pilBPCfacLineEdit.setValidator(qintvaliator1)
        self.ui.pilMinLineEdit.setValidator(QDoubleValidator())
        self.ui.pilMaxLineEdit.setValidator(QDoubleValidator())
        self.ui.pilHSlitLineEdit.setValidator(qintvaliator1)
        self.ui.refBGOffLineEdit.setValidator(qdoublevalidator0)
        self.ui.refSeaWinLineEdit.setValidator(qdoublevalidator0)
        self.ui.refBPCFacLineEdit.setValidator(qintvaliator1)
        self.ui.refNormLineEdit.setValidator(qdoublevalidator0)
        self.ui.refQcLineEdit.setValidator(qdoublevalidator0)
        self.ui.refQoffLineEdit.setValidator(QDoubleValidator())
        self.ui.refQLineEdit.setValidator(qdoublevalidator0)
        self.ui.refRLineEdit.setValidator(QDoubleValidator())
        self.ui.refRErrLineEdit.setValidator(qdoublevalidator0)
        self.ui.cutOffsetLineEdit.setValidator(qdoublevalidator0)
        self.ui.mcaCalibConLineEdit.setValidator(QDoubleValidator())
        self.ui.mcaCalibLinLineEdit.setValidator(QDoubleValidator())
        self.ui.mcaCalibQuaLineEdit.setValidator(QDoubleValidator())
        self.ui.mcaOffsetLineEdit.setValidator(qdoublevalidator0)



    def selectAPS_15IDC(self):
        # 15-ID-C is the only beamline; the menu entry stays checked
        self.ui.statusBar.clearMessage()
        self.beamline='APS-15IDC'
        self.ui.actionAPS_15IDC.setChecked(True)
        self.ui.statusBar.showMessage('APS-15IDC Selected')
        
    def showAbout(self):
        cwd=os.path.dirname(resource('mainwindow.py'))
        files=['mainwindow.py','mainwindow.ui','LSS_Reader.py','mca_routines.py','mpl2dwidget.py','mplwidget.py','spec_routines.py','TwoDDetector.py','logo.png']
        fname=[cwd+'/'+fname for fname in files if os.path.exists(cwd+'/'+fname)]
        # a packaged build holds no .py files: date it by its .ui file and logo, or the executable
        updateTime=max([os.path.getmtime(fn) for fn in fname] or [os.path.getmtime(sys.executable)])
        self.messageBox('LSS-Reader\n Version: 1.1\nLast Update: '+time.strftime("%m/%d/%Y %I:%M:%S %p",time.localtime(updateTime))+'\nCopyright belongs to:\n\tWei Bu <weibu1977@gmail.com>\n\tMrinal K Bera <nayanbera@gmail.com>',title='About')
        
    def openSpecFile(self,fname=None):
        self.ui.statusBar.clearMessage()       
        self.ui.imagesLabel.setText('Detector:')
        if fname is None:
            fname=QFileDialog.getOpenFileName(caption='Open Spec File')[0]
        if fname=='':
            return
        if not is_spec_file(fname):
            # leave whatever is loaded untouched
            self.notify('"'+str(fname)+'" is not a SPEC file (it does not start with #F), or it cannot be read. Nothing was changed.')
            self.ui.statusBar.showMessage('Not a SPEC file')
            return
        self.specFileName=fname
        if self.specFileName!='':
            self.clearAll()
            self.directory=str(QFileInfo(self.specFileName).absolutePath())
            self.directory_old=self.directory
            logpath,fallback=reader_log.attach_spec_log(self.specFileName)
            if fallback and logpath is not None:
                self.notify('The folder of the SPEC file cannot be written to. The log for this file is kept at '+logpath,title='Log')
            elif logpath is None:
                self.notify('No log file could be opened for this SPEC file.',title='Log')
        else:
            try:
                self.directory=self.directory_old
            except:
                self.directory=os.getcwd()
        specData_old=self.specData
        specPar_old=self.specPar
        startLineNum_old=self.startLineNum
        # try:
        self.specData={}
        self.specPar={}
        self.startLineNum=0
        self.endScanNum=0
        self.readSpecFile()
        self.ui.specFileLabel.setText('SpecFile: '+str(self.specFileName.split('/')[-1]))
        self.scriptLine('exp = Experiment(%r)' % os.path.abspath(self.specFileName))
        # except:
        #     self.specData=specData_old
        #     self.specPar=specPar_old
        #     self.startLineNum=startLineNum_old
        #     print("Either you have just loaded the old file or there is something wrong with Specfile reading")

        
    def clearAll(self):
        self.forgetImageSelection()
        # self.disconnect(self.ui.scanListWidget, SIGNAL('itemSelectionChanged()'),self.scanListChanged)
        self.ui.scanListWidget.itemSelectionChanged.disconnect(self.scanListChanged)
        # self.disconnect(self.ui.imageListWidget, SIGNAL('itemSelectionChanged()'),self.imageSelectedScanChanged)
        self.ui.imageListWidget.itemSelectionChanged.disconnect(self.imageSelectedScanChanged)
        # self.disconnect(self.ui.refQzListWidget, SIGNAL('itemSelectionChanged()'),self.refQzListSelectionChanged)
        self.ui.refQzListWidget.itemSelectionChanged.disconnect(self.refQzListSelectionChanged)
        # self.disconnect(self.ui.spXComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spXComboBox.currentIndexChanged.disconnect(self.updateSpecPlotData)
        # self.disconnect(self.ui.spYComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spYComboBox.currentIndexChanged.disconnect(self.updateSpecPlotData)
        # self.disconnect(self.ui.spY2ComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spY2ComboBox.currentIndexChanged.disconnect(self.updateSpecPlotData)
        # self.disconnect(self.ui.spNComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spNComboBox.currentIndexChanged.disconnect(self.updateSpecPlotData)
        self.ui.imageListWidget.clear()
        self.ui.statusBar.clearMessage()
        self.ui.scanListWidget.clear()
        self.ui.specPlotMplWidget.canvas.ax.clear()
        self.ui.spXComboBox.clear()
        self.ui.spYComboBox.clear()
        self.ui.spY2ComboBox.clear()
        self.ui.spNComboBox.clear()
        self.ui.mcaPlotMplWidget.canvas.ax.clear()
        self.ui.mcaPlotMplWidget.canvas.draw()
        self.ui.refBadPixListWidget.clear()
        self.ui.cutPlotMplWidget.canvas.ax.clear()
        self.ui.cutPlotMplWidget.canvas.draw()
        self.ui.gixMplWidget.canvas.ax.clear()
        self.ui.gixMplWidget.canvas.draw()
        self.ui.refADDataPlotWidget.canvas.ax.clear()
        self.ui.refADDataPlotWidget.canvas.draw()
        self.ui.refQzListWidget.clear() 
        # self.connect(self.ui.scanListWidget, SIGNAL('itemSelectionChanged()'),self.scanListChanged)
        # self.connect(self.ui.imageListWidget, SIGNAL('itemSelectionChanged()'),self.imageSelectedScanChanged)
        # self.connect(self.ui.refQzListWidget, SIGNAL('itemSelectionChanged()'),self.refQzListSelectionChanged)
        # self.connect(self.ui.spXComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        # self.connect(self.ui.spYComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        # self.connect(self.ui.spY2ComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        # self.connect(self.ui.spNComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        # self.disconnect(self.ui.scanListWidget, SIGNAL('itemSelectionChanged()'),self.scanListChanged)
        self.ui.scanListWidget.itemSelectionChanged.connect(self.scanListChanged)
        # self.disconnect(self.ui.imageListWidget, SIGNAL('itemSelectionChanged()'),self.imageSelectedScanChanged)
        self.ui.imageListWidget.itemSelectionChanged.connect(self.imageSelectedScanChanged)
        # self.disconnect(self.ui.refQzListWidget, SIGNAL('itemSelectionChanged()'),self.refQzListSelectionChanged)
        self.ui.refQzListWidget.itemSelectionChanged.connect(self.refQzListSelectionChanged)
        # self.disconnect(self.ui.spXComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spXComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
        # self.disconnect(self.ui.spYComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spYComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
        # self.disconnect(self.ui.spY2ComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spY2ComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
        # self.disconnect(self.ui.spNComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spNComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
         
        
    def readSpecFile(self):
        '''
        Reading spec File
        '''
        if self.specFileName is not None:
            progress=QProgressDialog('Reading scans form SPEC File:','Abort',0,100)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle('Wait')
            progress.setAutoClose(True)
            progress.setAutoReset(True)
            progress.setMinimum(1)
            self.specRead=specread(self.specFileName,startLineNum=self.startLineNum, endScanNum=self.endScanNum, beamline=self.beamline,data=self.specData,par=self.specPar,progress=progress)
        else:
            self.messageBox('Warning: There is no SPEC loaded!')
            return
        self.clearAll()
        if self.startLineNum==0:
            inipil=0
        else:
            inipil=1
        self.startLineNum=self.specRead.endLineNum
        self.specData=self.specRead.Data
        self.specPar=self.specRead.Par
        self.endScanNum=self.specData['NumOfScans']
       # print self.endScanNum
        if self.specData['NumOfScans']==0:
            self.ui.statusBar.showMessage(self.specData['Message'])
        else:
            scannums=sorted(set(self.specData['ScanNums']))   # the scans that exist, whatever their numbering
            repeated=sorted(set(n for n in self.specData['ScanNums'] if self.specData['ScanNums'].count(n)>1))
            if len(repeated)>0:
                self.messageBox('Scan number(s) '+listText(repeated)+' appear more than once in this SPEC file. The last scan with each number is shown.')
            short=[n for n in scannums if isinstance(self.specPar.get(n),dict) and self.specPar[n].get('DroppedRows')]
            if short:   # spec_routines.complete_rows: one short line used to lose the whole scan
                self.notify('Scan(s) %s: a data line with a different number of values was left out (in a file '
                            'SPEC is still writing, usually the line being written).' % listText(short),
                            title='SPEC file',level='info')
            self.scanlines=[self.specData[i]['ScanLine'] for i in scannums]
            self.ui.scanListWidget.addItems(self.scanlines)
            if np.any([self.specPar[i]['Detector']=='Vortex' for i in scannums]):
                if QDir(self.directory+'/'+self.mcaDirName).exists()==True:
                    self.mcaDir=self.directory+'/'+self.mcaDirName
                else:
                    self.messageBox('The folder "'+self.mcaDirName+'" was not found beside the SPEC file; please choose the folder with the MCA files.')
                    self.mcaDir=QFileDialog.getExistingDirectory(caption='Open MCA Directory')
                    if self.mcaDir=='':
                        self.mcaDir=self.directory+'/'+self.mcaDirName
                        self.messageBox('No MCA folder chosen: spectra of the fluorescence scans cannot be shown.')
                self.mcafhead=str(self.mcaDir)+'/'+self.specFileName.split('/')[-1]+'_'
                self.mcaftail='_mca' 
                print("MCA data Found!!")
            if np.any([self.specPar[i]['Detector']=='Pilatus' for i in scannums]):
                if QDir(self.directory+'/'+self.pilDirName).exists()==True:
                    self.pilDir=self.directory+'/'+self.pilDirName
                else:
                    self.messageBox('The folder "'+self.pilDirName+'" was not found beside the SPEC file; please choose the folder with the Pilatus images.')
                    self.pilDir=QFileDialog.getExistingDirectory(caption='Open Pilatus Directory')
                    if self.pilDir=='':
                        self.pilDir=self.directory+'/'+self.pilDirName
                        self.messageBox('No Pilatus folder chosen: images of the Pilatus scans cannot be shown.')
                self.pilfhead=str(self.pilDir)+'/'+self.specFileName.split('/')[-1]+'_SCAN-'
                self.pilftail='.tif'
                print ("Pilatus Images Found!!")
                if inipil==0:
                    self.ui.refBGOffLineEdit.setText('0.5')   #preset the background    
                    self.ui.refSlitLineEdit.setText('21,11')  #preset the size of ROI
                    self.ui.refQcLineEdit.setText('0.0217') #preset the critical q
                    if not self.absFacEnergyCheckBox.isChecked():   # with "from E", the scans' energy sets it
                        self.ui.AbsFacLineEdit.setText(str(ABSFAC_10KEV)) # 50 um Al at 10 keV (was '1.42')
            self.updateSeries()             # after the folders are known: it counts the frames and spectra on disk
            self.checkStaleResults()
        self.ui.statusBar.showMessage('Done')
        self.scanCenter={}


    def forgetImageSelection(self):
        """The image list is about to be rebuilt: selections and results that
        refer to its rows are no longer valid. (The detector type and the
        reduced reflectivity are kept; they do not refer to list rows.)"""
        self.selectedPilFramesNums=[]
        self.selectedMcaScanNums=[]
        self.nomMcaData={}
        self.cutData={}
        self.pilData={}
        self.pilErrorData={}
        self.pilGIDshow=0
        self.pilGISAXSshow=0

    # ---- scan series in the scan list (F39, review R2; owner, 2026-11-21) ----

    SERIES_TINT={'reflectivity':(70,130,220),'gid':(60,170,90),'xfntr':(230,140,40),'energy':(150,90,200),
                 'burn':(220,70,70),'gisaxs':(40,170,170),'direct_beam':(120,120,120),'alignment':(150,150,150)}

    def setupSeriesBox(self):
        """A 'Series' list above the scan list: choosing a series selects its
        data scans as one action; each scan row says its series in a tooltip
        and carries a faint tint of its kind."""
        from PyQt5.QtWidgets import QComboBox
        box=QComboBox(self)
        box.setObjectName('seriesComboBox')
        box.setToolTip('Scan series: the scans one experiment macro took together, from the file\'s "#U Series" lines '
                       'or, in older files, guessed by the reader (reflectivity: L scans whose Qz ranges move up and '
                       'overlap; gid: consecutive "ascan dth" with images; xfntr: "#V" L scans; energy: escans; burn: '
                       '"ascan ih" without movement). Choosing one selects its data scans (alignment scans between '
                       'them are not selected). The label says how many scans it has of how many were planned '
                       '("?" when the file does not say) and whether it was complete, partial (a scan stopped early), '
                       'aborted or still being written; the item\'s tooltip says why. Scan rows are tinted by kind: '
                       'blue reflectivity, green GID, orange XFNTR, purple energy, red burn, grey alignment.')
        box.addItem('Series: choose to select its scans')
        box.setEnabled(False)
        lay=self.ui.scanListWidget.parentWidget().layout()
        idx=lay.indexOf(self.ui.scanListWidget)
        inner=None
        if idx<0:                                   # the list sits in a nested layout
            for k in range(lay.count()):
                it=lay.itemAt(k)
                if it.layout() is not None and it.layout().indexOf(self.ui.scanListWidget)>=0:
                    inner=it.layout()
                    break
        target=inner if inner is not None else lay
        from PyQt5.QtWidgets import QCheckBox, QHBoxLayout
        row=QHBoxLayout()
        row.addWidget(box,1)
        whole=QCheckBox('Whole series',self)
        whole.setObjectName('seriesWholeCheckBox')
        whole.setChecked(bool(self.prefs.get('select_whole_series',True)))
        whole.setToolTip('On (default): clicking a scan that belongs to a series selects all the data scans of that '
                         'series (Ctrl-click still removes one; alignment scans are selected alone). Off: scans are '
                         'selected one by one, as before. Typed scan numbers are never expanded.')
        whole.toggled.connect(lambda on:self.setPreference('select_whole_series',bool(on)))
        row.addWidget(whole)
        target.insertLayout(max(target.indexOf(self.ui.scanListWidget),0),row)
        self.seriesWholeCheckBox=whole
        self.scanSelectionBefore=set()
        self.seriesUserAction=False
        self.ui.scanListWidget.viewport().installEventFilter(self)
        self.ui.scanListWidget.installEventFilter(self)
        box.activated.connect(self.selectSeries)
        self.ui.scanListWidget.itemSelectionChanged.connect(self.syncSeriesBox)
        self.seriesComboBox=box
        self.seriesList=[]

    def updateSeries(self):
        """The series of the open file (lss_core.series.all_series) into the
        Series list and the scan rows' tooltips and tints."""
        from PyQt5.QtGui import QBrush, QColor
        box=getattr(self,'seriesComboBox',None)
        if box is None:
            return
        try:
            info=seriesmod.scan_info(self.specData,self.specPar)
            self.scanPoints=self.dataCounts({x.num:x.points for x in info})
            found=seriesmod.all_series(info,growing=self.liveOn())   # live: the last series may be in progress
        except Exception as e:                       # a nicety: the list works without it
            self.log.info('series not found: %s',e)
            found=[]
        self.seriesAll=found
        self.seriesList=[s for s in found if s.data_scans]
        box.blockSignals(True)
        box.clear()
        box.addItem('Series: choose to select its scans' if self.seriesList else 'Series: none found')
        where={}
        for k,s in enumerate(self.seriesList):
            box.addItem('%s: S# %s' % (s.label(),scanRanges(s.data_scans)))
            tip=['%s series %s%s' % (s.kind,s.id,' (guessed by the reader)' if s.inferred else '')]
            tip.append('scans %s%s' % (listText(s.data_scans),'' if s.n is None else ' of %d planned' % s.n))
            if s.aux:
                tip.append('other scans: '+', '.join('%d (%s)' % (n,r) for n,r in s.aux))
            tip.append('status: %s%s' % (s.status.replace('_',' '),' — '+s.why if s.why else ''))
            if s.macro:
                tip.append('macro: '+s.macro)
            box.setItemData(k+1,'\n'.join(tip),Qt.ToolTipRole)
            for i,n in sorted(s.scans.items()):
                where.setdefault(n,(s,'scan %d of %s' % (i,'?' if s.n is None else s.n),s.kind))
            for n,r in s.aux:
                where.setdefault(n,(s,r,'alignment' if r=='align' else s.kind))
        box.setCurrentIndex(0)
        box.setEnabled(bool(self.seriesList))
        box.blockSignals(False)
        for row,line in enumerate(self.scanlines):
            item=self.ui.scanListWidget.item(row)
            try:
                num=int(line.split()[1])
            except (IndexError,ValueError):
                continue
            if num in where:
                s,pos,kind=where[num]
                item.setToolTip('%s series %s: %s%s; %s' % (s.kind,s.id,pos,' (guessed)' if s.inferred else '',
                                                               s.status.replace('_',' ')))
                c=self.SERIES_TINT.get(kind)
                if c:
                    item.setBackground(QBrush(QColor(c[0],c[1],c[2],40)))
            else:
                item.setToolTip('Scan %d: not part of a series' % num)

    def eventFilter(self,obj,event):
        """A mouse press or key press in the scan list is the user's own
        selection: only then is it widened to whole series (expandToSeries)."""
        from PyQt5.QtCore import QEvent
        lw=getattr(self.ui,'scanListWidget',None) if hasattr(self,'ui') else None
        if lw is not None and obj in (lw,lw.viewport()) and event.type() in (QEvent.MouseButtonPress,
                                                                             QEvent.KeyPress):
            self.seriesUserAction=True
            QTimer.singleShot(0,self.endSeriesUserAction)
        return super().eventFilter(obj,event)

    def endSeriesUserAction(self):
        self.seriesUserAction=False
        try:
            self.scanSelectionBefore=set(self.selectedScanNumbersInList())
        except RuntimeError:
            pass

    def selectedScanNumbersInList(self):
        out=[]
        for it in self.ui.scanListWidget.selectedItems():
            try:
                out.append(int(str(it.text()).split()[1]))
            except (IndexError,ValueError):
                pass
        return out

    def expandToSeries(self):
        """With "Whole series" on, a scan the user has just added to the
        selection brings the other data scans of its series (one selection,
        signals blocked); scans removed stay removed."""
        now=set(self.selectedScanNumbersInList())
        before=getattr(self,'scanSelectionBefore',set())
        self.scanSelectionBefore=now
        box=getattr(self,'seriesWholeCheckBox',None)
        if box is None or not box.isChecked() or not getattr(self,'seriesUserAction',False):
            return
        added=now-before
        extra=set()
        for s in getattr(self,'seriesList',[]):
            members=set(s.data_scans)
            if added & members:
                extra|=members
        extra-=now
        if not extra:
            return
        lw=self.ui.scanListWidget
        lw.blockSignals(True)
        for n in sorted(extra):
            r=self.scanRow(n)
            if r is not None:
                lw.item(r).setSelected(True)
        lw.blockSignals(False)
        self.scanSelectionBefore=now|extra

    # ---- live updates (F1-F5, L1-L4; owner, 2026-11-22) ----

    def setupLive(self):
        """A "Live" box beside "Update Specfile": the SPEC file is watched and,
        when it grows, read again (L1); results saved from a series that
        changed are remade from their recipes and saved as new versions
        (L2); a selection that was a whole series follows it (L3); live mode
        ends when the followed series says it is complete (L4)."""
        from PyQt5.QtWidgets import QCheckBox
        box=QCheckBox('Live',self)
        box.setObjectName('liveCheckBox')
        box.setToolTip('Watch the data while they are being written: every %g s the reader checks the SPEC file, the '
                       'Pilatus folder and the latest fluorescence scan\'s MCA file, and on any new SPEC line, image or '
                       'spectrum reads what is new without resetting the window. Results saved in the workbook whose '
                       'series gained scans or points are remade from their recipe (the lss_core call stored with '
                       'them) and saved as a new version marked "live"; the old one is marked superseded. A selection '
                       'that was a whole series grows with it. Live mode stops by itself when the followed series '
                       'writes that it is complete (series lines from the macro); otherwise untick it. Results '
                       'without a recipe (SpecPlot curves, fitted MCA lines, GID cuts) are only marked out of date.'
                       % self.liveInterval())
        box.toggled.connect(self.liveToggled)
        btn=self.ui.speUpSpeFilePushButton
        lay=btn.parentWidget().layout()
        idx=lay.indexOf(btn)
        inner=None
        if idx<0:
            for k in range(lay.count()):
                it=lay.itemAt(k)
                if it.layout() is not None and it.layout().indexOf(btn)>=0:
                    inner=it.layout()
                    break
        target=inner if inner is not None else lay
        from PyQt5.QtWidgets import QHBoxLayout
        if hasattr(target,'insertLayout') and not isinstance(target,QHBoxLayout):
            row=QHBoxLayout()
            pos=target.indexOf(btn)
            target.removeWidget(btn)
            row.addWidget(btn,1)
            row.addWidget(box)
            target.insertLayout(max(pos,0),row)
        else:
            target.insertWidget(target.indexOf(btn)+1,box)
        self.liveCheckBox=box
        self.liveTimer=QTimer(self)
        self.liveTimer.timeout.connect(self.liveTick)
        self.liveStamp=None
        self.remakeJobs=[]
        self.remakePool=None
        self.remakeTimer=QTimer(self)
        self.remakeTimer.timeout.connect(self.collectRemakes)

    def liveInterval(self):
        try:
            return max(float(self.prefs.get('live_interval_s',5.0)),0.2)
        except (TypeError,ValueError):
            return 5.0

    def liveOn(self):
        box=getattr(self,'liveCheckBox',None)
        return bool(box is not None and box.isChecked())

    def liveToggled(self,on):
        if on:
            if not getattr(self,'specFileName',None):
                self.liveCheckBox.setChecked(False)
                self.messageBox('Open a SPEC file first.')
                return
            self.liveStamp=self.fileStamp()
            self.liveTimer.start(int(self.liveInterval()*1000))
            self.ui.statusBar.showMessage('Live: watching %s' % os.path.basename(self.specFileName),5000)
        else:
            self.liveTimer.stop()

    def fileStamp(self):
        """What live mode watches (owner, 2026-11-22: every new Pilatus image or
        Vortex spectrum, not only new SPEC lines): the SPEC file, the Pilatus
        folder (a new image changes it) and the MCA file of the last scan (it
        grows by one block per spectrum)."""
        try:
            st=os.stat(self.specFileName)
        except (OSError,TypeError):
            return None
        stamp=[st.st_size,st.st_mtime_ns]
        for d in (getattr(self,'pilDir',None),getattr(self,'mcaDir',None)):
            try:
                stamp.append(os.stat(d).st_mtime_ns if d else None)
            except OSError:
                stamp.append(None)
        nums=self.specData.get('ScanNums',[]) if isinstance(getattr(self,'specData',None),dict) else []
        par=getattr(self,'specPar',{}) or {}
        vortex=[n for n in nums if par.get(n,{}).get('Detector')=='Vortex']
        mca=self.mcaFilePath(vortex[-1]) if vortex else None          # the latest fluorescence scan's file
        try:
            stamp.append(os.stat(mca).st_size if mca else None)
        except OSError:
            stamp.append(None)
        return tuple(stamp)

    def mcaFilePath(self,scan):
        head=getattr(self,'mcafhead',None)
        return head+str(scan)+getattr(self,'mcaftail','_mca') if head else None

    def dataCounts(self,points):
        """{scan: frames or spectra on disk}: a Pilatus scan counts the images
        written (one listing of the folder), a fluorescence scan the spectra
        in its MCA file (re-read only when the file's size changed); neither
        more than the SPEC points, which carry each point's Qz and monitor
        (a spectrum-only scan, getandsave_mca, has no SPEC points: its
        spectra). Other scans: their SPEC points. Live mode and the stale
        check compare these, so a frame or spectrum written after its SPEC
        line still counts as new data."""
        import re
        out=dict(points)
        par=getattr(self,'specPar',{}) or {}
        pil={n for n in out if par.get(n,{}).get('Detector')=='Pilatus'}
        if pil and getattr(self,'pilDir',None):
            try:
                names=os.listdir(self.pilDir)
            except OSError:
                names=[]
            base=re.escape(os.path.basename(self.specFileName))
            pat=re.compile(r'^%s_SCAN-(\d+)_\d+\.' % base)
            have={}
            for nm in names:
                m=pat.match(nm)
                if m:
                    k=int(m.group(1))
                    have[k]=have.get(k,0)+1
            for n in pil:
                out[n]=min(out[n],have.get(n,0))
        cache=getattr(self,'mcaCountCache',None)
        if cache is None:
            cache=self.mcaCountCache={}
        for n in [n for n in out if par.get(n,{}).get('Detector')=='Vortex']:
            path=self.mcaFilePath(n)
            try:
                size=os.stat(path).st_size if path else None
            except OSError:
                size=None
            if size is None:
                out[n]=0 if out[n] else out[n]
                continue
            if cache.get(path,(None,))[0]!=size:
                cache[path]=(size,self.countSpectra(path))
            k=cache[path][1]
            out[n]=k if not out[n] else min(out[n],k)
        return out

    @staticmethod
    def countSpectra(path):
        """Spectra in an MCA file: one '#S' block each (a multi-element file
        holds one block per element and point: its distinct 'Point:' values)."""
        blocks,pointset=0,set()
        try:
            with open(path,errors='replace') as f:
                for line in f:
                    if line.startswith('#S'):
                        blocks+=1
                        for w in line.split():
                            if w.startswith('Point:'):
                                pointset.add(w)
        except OSError:
            return 0
        return len(pointset) if pointset else blocks

    def liveTick(self):
        """L1: the file grew: read it again, keep the selection (L3), stop at the end (L4)."""
        stamp=self.fileStamp()
        if stamp is None or stamp==self.liveStamp:
            return
        self.liveStamp=stamp
        self.liveUpdate()

    def updateSpecFile(self):
        """"Update Specfile": the scans the file gained, read without resetting
        the window (liveUpdate), the same as one step of live mode; a file not
        read yet is read in full."""
        if not getattr(self,'specFileName',None) or not self.specData.get('ScanNums'):
            self.readSpecFile()
            return
        self.liveUpdate()

    def liveRead(self):
        """Read what the SPEC file gained since the last read without
        resetting the window (owner, 2026-11-22: "updates shouldn't feel
        like a reset or clunky"): no clearing, no progress dialog; rows of
        new scans are added and the re-read last scan's row is updated in
        place, so the selection stays. Returns (new scans, scans that
        gained points)."""
        old_nums=set(self.specData.get('ScanNums',[]))
        old_pts=dict(getattr(self,'scanPoints',{}) or {})
        r=specread(self.specFileName,startLineNum=self.startLineNum,endScanNum=self.endScanNum,beamline=self.beamline,
                   data=self.specData,par=self.specPar,progress=None)
        self.specRead=r
        self.startLineNum=r.endLineNum
        self.specData,self.specPar=r.Data,r.Par
        self.endScanNum=self.specData['NumOfScans']
        scannums=sorted(set(self.specData.get('ScanNums',[])))
        lines=[self.specData[i]['ScanLine'] for i in scannums]
        lw=self.ui.scanListWidget
        lw.blockSignals(True)
        for row,line in enumerate(lines):
            if row<lw.count():
                if lw.item(row).text()!=line:
                    lw.item(row).setText(line)
            else:
                lw.addItem(line)
        lw.blockSignals(False)
        self.scanlines=lines
        new=[n for n in scannums if n not in old_nums]
        dets={self.specPar[n].get('Detector') for n in new}
        if ('Pilatus' in dets and not hasattr(self,'pilfhead')) or ('Vortex' in dets and not hasattr(self,'mcafhead')):
            # a detector this file had not used yet: its folder is looked up the usual way
            self.startLineNum,self.endScanNum=0,0
            self.specData,self.specPar={},{}
            self.readSpecFile()
            return new,[]
        self.updateSeries()
        grown=[n for n in scannums if n in old_pts and self.scanPoints.get(n,0)>old_pts[n]]
        self.checkStaleResults()
        return new,grown

    def liveUpdate(self):
        """One live update: read the new data (liveRead); when the scans being
        looked at changed or the followed series grew, redraw them while
        keeping the tab, the plot's axis choices and the frame selection;
        otherwise leave the window as it is (L1, L3, L4)."""
        before=sorted(int(n) for n in getattr(self,'selectedScanNums',[]))
        followed=next((s for s in getattr(self,'seriesAll',[]) if before and sorted(s.data_scans)==before),None)
        tab=self.ui.PlotWidget.currentIndex()
        combos=[(c,c.currentText()) for c in (self.ui.spXComboBox,self.ui.spYComboBox,self.ui.spY2ComboBox,
                                              self.ui.spNComboBox)]
        il=self.ui.imageListWidget
        frames=[it.text() for it in il.selectedItems()]
        all_frames=il.count()>0 and len(frames)==il.count()
        gid_shown=getattr(self,'pilGIDshow',0)==1 and getattr(self,'pilGIDData',None) is not None
        new,grown=self.liveRead()
        now=None
        if followed is not None:
            now=next((s for s in self.seriesAll if s.id==followed.id),None) or \
                next((s for s in self.seriesAll if followed.data_scans[0] in s.data_scans),None)
        want=sorted(now.data_scans) if now is not None else before
        touched=set(want)!=set(before) or bool(set(want)&(set(new)|set(grown)))
        if touched and want:
            lw=self.ui.scanListWidget
            lw.blockSignals(True)
            lw.clearSelection()
            for r in (self.scanRow(n) for n in want):
                if r is not None:
                    lw.item(r).setSelected(True)
            lw.blockSignals(False)
            self.seriesChosen=now
            self.scanSelectionBefore=set(want)
            self.scanListChanged()
            for c,text in combos:                       # the plot's axis choices, as they were
                k=c.findText(text)
                if text and k>=0 and c.currentText()!=text:
                    c.setCurrentIndex(k)
            self.ui.PlotWidget.setCurrentIndex(tab)
            if frames and il.count():
                counts=getattr(self,'scanPoints',{}) or {}
                rows_scan=list(getattr(self,'pilScanNum',[]))
                rows_frame=list(getattr(self,'pilFrameNum',[]))

                def written(k):            # the frame's image is on disk (a frame may be listed before it is)
                    if self.det!='Pilatus' or k>=len(rows_scan):
                        return True
                    return int(rows_frame[k])<counts.get(int(rows_scan[k]),10**9)
                il.blockSignals(True)
                for k in range(il.count()):
                    it=il.item(k)
                    it.setSelected((all_frames and written(k)) or (not all_frames and it.text() in frames))
                il.blockSignals(False)
                il.itemSelectionChanged.emit()
                self.flushPendingSelection()            # drawn now, so that the tab can be put back after it
            if gid_shown:                               # a GID map was on screen: it stays (a remake replaces it)
                self.pilGIDshow=1
                self.gidShowMap()
            self.ui.PlotWidget.setCurrentIndex(tab)
        if new or grown:
            self.ui.statusBar.showMessage('Live: %s%s' % ('new scans %s' % scanRanges(new) if new else '',
                ('%sscans %s grew' % ('; ' if new else '',scanRanges(grown))) if grown else ''),8000)
        # L4: a series with the macro's lines says when it is done (a guessed one cannot)
        if self.liveOn() and now is not None and not now.inferred and now.status in ('complete','aborted','partial'):
            self.liveCheckBox.setChecked(False)
            self.notify('Live updates stopped: series %s is %s.' % (now.id,now.status),title='Live',level='info')

    def remakeStale(self,wb,stale):
        """L2: results whose series changed are remade from their recipes on
        the series' scans now, with the user's point selection carried over
        (lss_core.live.carry_points), in a worker thread (owner,
        2026-11-22); collectRemakes saves them as new versions ('live') and
        marks the old rows superseded. One remake per recipe (a
        reflectivity's R and R/RF share one); a result already being remade
        is not queued again."""
        import concurrent.futures
        rows={r['id']:r for r in wb.results()}
        groups={}
        for rid in stale:
            r=rows.get(rid)
            if r is not None and rid not in self.remakesInFlight():
                groups.setdefault(r.get('recipe') or '',[]).append(r)
        left=[]
        for recipe,members in groups.items():
            if not recipe:
                left+=[(r['id'],'no recipe') for r in members]
                continue
            first=members[0]
            saved=[int(x) for x in str(first.get('series_scans') or first['scans']).split(',') if x.strip()]
            cur=next((s for s in self.seriesAll if s.id==first.get('series')),None) or \
                next((s for s in self.seriesAll if saved and saved[0] in s.data_scans),None)
            job=dict(recipe=recipe,spec=self.specFileName,scans=list(cur.data_scans if cur is not None else saved),
                     then=workbookmod.scan_points_of(first),now=dict(self.scanPoints),series=list(self.seriesAll),
                     members=[(r['id'],r.get('label'),stale[r['id']]) for r in members])
            if getattr(self,'remakePool',None) is None:
                self.remakePool=concurrent.futures.ThreadPoolExecutor(max_workers=1,thread_name_prefix='remake')
            self.remakeJobs.append((self.remakePool.submit(runRemake,job),job))
        if self.remakeJobs and not self.remakeTimer.isActive():
            self.remakeTimer.start(100)
        if left:
            self.notify('Live: out of date, not remade: %s' % '; '.join('%s (%s)' % l for l in left),
                        title='Live',level='info')

    def remakesInFlight(self):
        return {m[0] for _,job in getattr(self,'remakeJobs',[]) for m in job['members']}

    def collectRemakes(self):
        """In the window's thread: store the remakes that have finished."""
        done=[(f,job) for f,job in self.remakeJobs if f.done()]
        if not done:
            return
        self.remakeJobs=[(f,job) for f,job in self.remakeJobs if not f.done()]
        if not self.remakeJobs:
            self.remakeTimer.stop()
        made,left,shown=[],[],[]
        try:
            wb=self.openWorkbook()
            for f,job in done:
                try:
                    kind,items,new_recipe,res=f.result()
                except Exception as e:
                    left+=[(rid,str(e)) for rid,_,_ in job['members']]
                    continue
                for rid,label,why in job['members']:
                    it=next((i for i in items if i.get('label')==label),items[0] if len(items)==1 else None)
                    if it is None:
                        left.append((rid,'no matching part in the remade result'))
                        continue
                    it=dict(it,label=label or it.get('label',''))
                    it['series']=workbookmod.series_for(it.get('scans',[]),job['series'],job['now'])
                    nid=wb.add_result(kind,note='remade from %s: %s' % (rid,why),origin='live',recipe=new_recipe,**it)
                    wb.supersede(rid,nid)
                    made.append((rid,nid))
                    if getattr(self,'shownResults',{}).get(kind)==rid:
                        shown.append((kind,res,nid))
            if made:
                self.saveWorkbook(wb)
        except Exception as e:
            self.workbookCache=None
            self.notify('Live: could not store the remade results: %s' % e,title='Live')
            return
        for kind,res,nid in shown:            # the display showing the old result now shows the remade one
            try:
                self.showRemade(kind,res,nid)
            except Exception as e:
                self.log.info('remade %s not shown: %s',nid,e)
        if made or left:
            self.notify('Live: %s%s' % ('; '.join('%s remade as %s' % d for d in made),
                        ('; not remade: '+'; '.join('%s (%s)' % l for l in left)) if left else ''),
                        title='Live',level='info')

    def finishRemakes(self,timeout=120):
        """Wait for the remakes under way and store them (tests; closing)."""
        import concurrent.futures
        futures=[f for f,_ in getattr(self,'remakeJobs',[])]
        if futures:
            concurrent.futures.wait(futures,timeout=timeout)
        self.collectRemakes()

    def selectSeries(self,index):
        """Select the data scans of the chosen series as one action."""
        if index<=0 or index>len(self.seriesList):
            return
        s=self.seriesList[index-1]
        rows=[r for r in (self.scanRow(n) for n in s.data_scans) if r is not None]
        lw=self.ui.scanListWidget
        lw.blockSignals(True)
        lw.clearSelection()
        for r in rows:
            lw.item(r).setSelected(True)
        if rows:
            lw.scrollToItem(lw.item(rows[0]))
        lw.blockSignals(False)
        self.seriesChosen=s
        lw.itemSelectionChanged.emit()

    def syncSeriesBox(self):
        """Back to the placeholder when the selection is no longer the chosen series."""
        box=getattr(self,'seriesComboBox',None)
        s=getattr(self,'seriesChosen',None)
        if box is None or s is None:
            return
        chosen=sorted(int(str(it.text()).split()[1]) for it in self.ui.scanListWidget.selectedItems())
        if chosen!=sorted(s.data_scans):
            self.seriesChosen=None
            box.blockSignals(True)
            box.setCurrentIndex(0)
            box.blockSignals(False)

    def scanRow(self,scannum):
        """Row of scan number ``scannum`` in the scan list, or None.

        Scan numbers need not start at 1 or be consecutive (SPEC restarted,
        scans deleted), so the row is looked up, never computed as number-1.
        """
        for row,line in enumerate(self.scanlines):
            try:
                if int(line.split()[1])==int(scannum):
                    return row
            except (IndexError,ValueError):
                pass
        return None

    def scanListChanged(self):
        self.expandToSeries()
        self.forgetImageSelection()
        self.ui.statusBar.clearMessage()
        self.ui.imageSelectAllCheckBox.setCheckState(0)
        self.ui.imageListWidget.clear()
        # self.disconnect(self.ui.spXComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spXComboBox.currentIndexChanged.disconnect(self.updateSpecPlotData)
        # self.disconnect(self.ui.spYComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spYComboBox.currentIndexChanged.disconnect(self.updateSpecPlotData)
        # self.disconnect(self.ui.spY2ComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spY2ComboBox.currentIndexChanged.disconnect(self.updateSpecPlotData)
        # self.disconnect(self.ui.spNComboBox, SIGNAL('currentIndexChanged(int)'),self.updateSpecPlotData)
        self.ui.spNComboBox.currentIndexChanged.disconnect(self.updateSpecPlotData)
        self.selectedScans=self.ui.scanListWidget.selectedItems()
        #self.selectedScanNums=[self.ui.scanListWidget.row(items) for items in self.selectedScans]
        self.selectedScanNums=[int(str(items.text()).split()[1]) for items in self.selectedScans]
        self.ui.scansLineEdit.setText(listText(self.selectedScanNums))
        if self.checkSameScans()==False or self.selectedScanNums==[]:
            self.messageBox('Error:: The scans are not identical or some scans have no data!!')
            # self.disconnect(self.ui.scanListWidget, SIGNAL('itemSelectionChanged()'),self.scanListChanged)
            self.ui.scanListWidget.itemSelectionChanged.disconnect(self.scanListChanged)
            for item in self.selectedScans:
                item.setSelected(False)
            # self.connect(self.ui.scanListWidget, SIGNAL('itemSelectionChanged()'),self.scanListChanged)
            self.ui.scanListWidget.itemSelectionChanged.connect(self.scanListChanged)
            self.ui.specPlotMplWidget.canvas.ax.clear()
            self.ui.specPlotMplWidget.canvas.draw()
            self.ui.spXComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
            self.ui.spYComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
            self.ui.spY2ComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
            self.ui.spNComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
        else:
            self.ui.spXComboBox.clear()
            self.ui.spYComboBox.clear()
            self.ui.spY2ComboBox.clear()
            self.ui.spNComboBox.clear()
            try:
                self.ui.spXComboBox.addItems(self.specData[self.selectedScanNums[0]]['ScanVar'])
                self.ui.spYComboBox.addItems(self.specData[self.selectedScanNums[0]]['ScanVar'])
                self.ui.spY2ComboBox.addItems(['None'])
                self.ui.spY2ComboBox.addItems(self.specData[self.selectedScanNums[0]]['ScanVar'])
                self.ui.spNComboBox.addItems(self.specData[self.selectedScanNums[0]]['ScanVar'])
                if self.specData[self.selectedScanNums[0]]['ScanVar'][0]=='H':
                    self.ui.spXComboBox.setCurrentIndex(2)
                else:
                    self.ui.spXComboBox.setCurrentIndex(0)
                self.ui.spYComboBox.setCurrentIndex(len(self.specData[self.selectedScanNums[0]]['ScanVar'])-1)
                self.ui.spY2ComboBox.setCurrentIndex(0)
                cols=list(self.specData[self.selectedScanNums[0]]['ScanVar'])
                # normalised by Monc by default (owner, 2026-11-23: "all data is default normalized
                # by monc"); the column before the last only when the scan has no Monc (as before)
                self.ui.spNComboBox.setCurrentIndex(cols.index('Monc') if 'Monc' in cols else len(cols)-2)

            except:   #for getandsave_mca, which doesn't have any 'ScanVar'
                pass
            self.addTimeColumn()
            self.ui.spXComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
            self.ui.spYComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
            self.ui.spY2ComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
            self.ui.spNComboBox.currentIndexChanged.connect(self.updateSpecPlotData)
            self.absFacFromEnergy()
            if self.specPar[self.selectedScanNums[0]]['Detector']=='Vortex' and self.specData[self.selectedScanNums[0]]['ScanVar']=='Empty':
                # a fluorescence scan has no columns to plot; that is normal, not a warning
                self.ui.specPlotMplWidget.canvas.ax.clear()
                self.ui.specPlotMplWidget.canvas.draw()
            else:
                try:
                    self.updateSpecPlotData()
                except Exception:
                    self.log.exception('could not plot scan(s) %s',self.selectedScanNums)
                    self.messageBox('Warning:: The scan(s) are not regular Spec scan')
            if self.specPar[self.selectedScanNums[0]]['Detector']=='Vortex':
                self.updateMcaImageList()
                self.ui.imagesLabel.setText('Vortex:')
                self.ui.PlotWidget.setCurrentIndex(0)
            if self.specPar[self.selectedScanNums[0]]['Detector']=='Unsupported':
                self.messageBox('Bruker CCD images (.sfrm) are no longer supported by this reader.')
            if self.specPar[self.selectedScanNums[0]]['Detector']=='Pilatus':
                self.updatePilImageList()
                self.ui.PlotWidget.setCurrentIndex(0)
                self.ui.imagesLabel.setText('Pilatus:')
        self.ui.statusBar.showMessage('Done')
            
    def scanListInputChanged(self):
        if len(self.scanlines)==0:   # no scans listed: nothing to select
            self.messageBox('Please open a SPEC file first!')
            return
        # self.disconnect(self.ui.scanListWidget, SIGNAL('itemSelectionChanged()'),self.scanListChanged)
        self.ui.scanListWidget.itemSelectionChanged.disconnect(self.scanListChanged)
        try:
            self.selectedScans=self.ui.scanListWidget.selectedItems()
            self.selectedScanNums=[int(str(items.text()).split()[1]) for items in self.selectedScans]
            try:    # deselect the currently selected numbers
                for item in self.selectedScans:
                    item.setSelected(False)
                self.selectedScanNums=[]
            except:
                self.selectedScanNums=[]
            inputscannumbers = str(self.ui.scansLineEdit.text()).split(',')
            for item in inputscannumbers:
                scan=list(map(int, item.split('-')))
                if len(scan)>1:
                    self.selectedScanNums=self.selectedScanNums+list(range(scan[0],scan[1]+1))
                else:
                    self.selectedScanNums=self.selectedScanNums+scan
            #self.selectedScanNums=[item for item in self.selectedScanNums]
            # self.connect(self.ui.scanListWidget, SIGNAL('itemSelectionChanged()'),self.scanListChanged)
            snum=[int(item.split()[1]) for item in self.scanlines]
            for i in self.selectedScanNums:
                # self.ui.scanListWidget.setItemSelected(self.ui.scanListWidget.item(snum.index(i)),True)
                self.ui.scanListWidget.item(snum.index(i)).setSelected(True)
            self.ui.scanListWidget.setCurrentRow(snum.index(self.selectedScanNums[-1]))
            self.ui.scanListWidget.itemSelectionChanged.connect(self.scanListChanged)
            self.scanListChanged()
            self.ui.statusBar.showMessage('Done')
        except:
            lastnum=int(self.scanlines[-1].split()[1])
            self.messageBox('Please enter the scan number in the range of [1, '+str(lastnum)+']\n'+'and in the format such as "2-5,7".')
            self.ui.scanListWidget.itemSelectionChanged.connect(self.scanListChanged)
            return

        

    TIME_COLUMN='Time_s'
    TIME_START_COLUMN='Time_from_start_s'

    def scanTimes(self,i):
        """Start time of every point of scan ``i`` (s, lss_core.timing), or
        None; cached per SPEC file."""
        from lss_core import timing
        cache=getattr(self,'_scanTimes',{})
        key=(self.specFileName,i)
        if key not in cache:
            p=self.specPar.get(i,{})
            cols={k:v for k,v in self.specData.get(i,{}).items() if isinstance(v,np.ndarray)}
            t=timing.point_times(cols,p.get('Date'),timing.utc_offset(p.get('FileEpoch'),p.get('FileDate')),
                                 series_t0=p.get('SeriesT0'))
            cache[key]=t
            self._scanTimes=cache
        return cache[key]

    def addTimeColumn(self):
        """Offer time as an x axis in the SPEC plot (owner, 2026-11-19; D46):
        Time_s, the true timeline of the selected scans (seconds since the
        earliest selected point), and Time_from_start_s, each scan from its
        own first point (to compare scans as if they started together). From
        lss_core.timing: old files #D + Epoch steps (~1 s, overhead ignored),
        new files Tstart; dates removed: Epoch's own clock."""
        import time as _time
        times={}
        for i in self.selectedScanNums:
            t=self.scanTimes(i)
            length=len(next((v for v in self.specData[i].values() if isinstance(v,np.ndarray)),[]))
            if t.start is None or len(t.start)!=length or length==0:
                return
            times[i]=np.asarray(t.start,float)
        if not times:
            return
        origin=min(float(v[0]) for v in times.values())
        for i,v in times.items():
            self.specData[i][self.TIME_COLUMN]=v-origin
            self.specData[i][self.TIME_START_COLUMN]=v-v[0]
        notes=' '.join(self.scanTimes(self.selectedScanNums[0]).notes)
        clock='' if origin<1e8 else ' (%s UTC)' % _time.strftime('%Y-%m-%d %H:%M:%S',_time.gmtime(origin))
        for name,tip in ((self.TIME_COLUMN,'Seconds since the earliest selected point%s: the selected scans on '
                          'one true timeline. ' % clock),
                         (self.TIME_START_COLUMN,'Seconds since each scan\'s own first point: the scans compared '
                          'as if they had started together. ')):
            if self.ui.spXComboBox.findText(name)<0:
                self.ui.spXComboBox.addItem(name)
            self.ui.spXComboBox.setItemData(self.ui.spXComboBox.findText(name),tip+notes,Qt.ToolTipRole)

    def updateSpecPlotData(self):
        if (self.specFileName is None or len(self.selectedScanNums)==0
                or str(self.ui.spXComboBox.currentText())==''):   # nothing plotted yet: display options do nothing
            return
        self.ui.statusBar.clearMessage()
        self.ui.specPlotMplWidget.canvas.ax.clear()
        self.ui.PlotWidget.setCurrentIndex(0)
        self.specData['YCol']=str(self.ui.spYComboBox.currentText())
        self.specData['NCol']=str(self.ui.spNComboBox.currentText())
        title='File: '+self.specFileName+' S# '+listText(np.sort(self.selectedScanNums))
        if self.checkSameScans()==False:
            self.ui.statusBar.showMessage('Error:: The scans are not identical or some scans have no data!!')
        else:
            for i in self.selectedScanNums:
                tempx=self.specData[i][str(self.ui.spXComboBox.currentText())]
                tempy=self.specData[i][str(self.ui.spYComboBox.currentText())]
                if tempx is None or tempy is None:
                    break
                x=tempx
                y=tempy
                n=self.specData[i][str(self.ui.spNComboBox.currentText())]
                g=self.monitorGainFactor(i,self.ui.spNComboBox.currentText()) if self.ui.spNCheckBox.checkState()!=0 else 1.0
                if str(self.ui.spY2ComboBox.currentText())=='None':
                    self.label='S '+str(i)
                    self.specPlot(x,y,n,g)
                else: 
                    self.label='S '+str(i)+str(self.ui.spYComboBox.currentText())
                    self.specPlot(x,y,n,g)
                    y2=self.specData[i][str(self.ui.spY2ComboBox.currentText())]
                    self.label='S '+str(i)+str(self.ui.spY2ComboBox.currentText())
                    self.specPlot(x,y2,n,g)
                yerr=pl.sqrt(np.abs(y))
                if self.ui.spNCheckBox.checkState()!=0:
                    yerr=pl.sqrt(y/n**2+y**2/n**3)*g
                    y=y/n*g
            try:
                # the shape of the scan (lss_core.peaks.fit_scan, owner 2026-11-21; P9 fixed): a peak, an
                # edge (a half-cut: the edge width is the beam size) or a plateau, whichever the data support
                yerr_=np.asarray(yerr,float)
                # a sample-height scan against its own motor: good signal and FWHM > 20 µm or no fit (owner, 2026-11-23)
                last=self.specData[self.selectedScanNums[-1]]
                first=next((k for k,v in last.items() if isinstance(v,np.ndarray)),None)
                kw=peaks.height_scan_options() if (peaks.is_height_scan(last.get('ScanLine',''))
                                                   and str(self.ui.spXComboBox.currentText())==first) else {}
                res=peaks.fit_scan(x,y,yerr_ if np.all(yerr_>0) else None,**kw)
                self.specFit=res
                self.peakPos='%.4f'%x[np.argmax(y)]
                if not res.peaks:
                    raise ValueError(res.message)
                p=res.peaks[0]
                self.peakCenter='%.4f'%p.centre
                self.peakFWHM='%.4f'%p.fwhm
                if res.kind=='edge':
                    self.ui.specPlotMplWidget.canvas.ax.set_title(title+'\n'+'Peak= '+self.peakPos+', Edge= '+self.peakCenter+', Edge Width= '+self.peakFWHM)
                elif res.kind=='box':
                    self.ui.specPlotMplWidget.canvas.ax.set_title(title+'\n'+'Peak= '+self.peakPos+', Cen= '+self.peakCenter+', Width= '+self.peakFWHM+
                                                                  ', Edge widths= %.4f, %.4f' % (res.edges[0][1],res.edges[1][1]))
                else:
                    self.ui.specPlotMplWidget.canvas.ax.set_title(title+'\n'+'Peak= '+self.peakPos+', Cen= '+self.peakCenter+', FWHM= '+self.peakFWHM)
                xf=np.linspace(np.min(x),np.max(x),400)
                self.ui.specPlotMplWidget.canvas.ax.plot(xf,res.model(xf),'g--',label='Fit (%s)' % res.kind)
                self.scanCenter[self.selectedScanNums[-1]]=float(format(p.centre,'.3f'))
            except:
                self.peakPos='%.4f'%x[np.argmax(y)]
                self.peakCenter=self.peakPos
                self.peakFWHM='0'
        self.specPlotSettings()
        if not getattr(self,'specLogKept',''):          # keep the note about a log axis left linear
            self.ui.statusBar.showMessage('Done')
        
    def specSaveData(self):
        if len(self.selectedScanNums)==0 or str(self.ui.spXComboBox.currentText())=='':
            self.messageBox('Please select a scan with data to save first!')
            return
        self.saveFileName=QFileDialog.getSaveFileName(caption='Save SPEC scans', directory=self.directory)[0]
        if self.saveFileName=='':   # dialog cancelled
            return
        cols=[str(c.currentText()) for c in (self.ui.spXComboBox,self.ui.spYComboBox,self.ui.spNComboBox)]
        missing=[i for i in self.selectedScanNums if any(c not in self.specData[i] for c in cols)]
        if missing:   # e.g. the selection changed since the columns were listed
            self.messageBox('Scan(s) %s have no column %s; select scans with the same columns.' % (listText(missing),', '.join(c for c in cols if any(c not in self.specData[i] for i in missing))))
            return
        for i in self.selectedScanNums:
            x=self.specData[i][str(self.ui.spXComboBox.currentText())]
            y=self.specData[i][str(self.ui.spYComboBox.currentText())]
            n=self.specData[i][str(self.ui.spNComboBox.currentText())]
            g=self.monitorGainFactor(i,self.ui.spNComboBox.currentText()) if self.ui.spNCheckBox.checkState()!=0 else 1.0
            yerr=pl.sqrt(y)
            self.fname=self.saveFileName+'_'+str(i)+'_'+str(self.ui.spXComboBox.currentText())+'_'+str(self.ui.spYComboBox.currentText())+'.txt'
            if self.ui.spNCheckBox.checkState()!=0:
                yerr=pl.sqrt(y/n**2+y**2/n**3)*g
                y=y/n*g
                self.fname=self.saveFileName+'_'+str(i)+'_'+str(self.ui.spXComboBox.currentText())+'_'+str(self.ui.spYComboBox.currentText())+'_'+str(self.ui.spNComboBox.currentText())+'.txt'
            specscandata=[[x[j],y[j],yerr[j]] for j in range(len(x))]
            np.savetxt(self.fname,specscandata,fmt='%.4f\t%.4e\t%.4e')
            if str(self.ui.spY2ComboBox.currentText())!='None':
                y2=self.specData[i][str(self.ui.spY2ComboBox.currentText())]
                yerr2=pl.sqrt(y2)
                self.fname=self.saveFileName+'_'+str(i)+'_'+str(self.ui.spXComboBox.currentText())+'_'+str(self.ui.spY2ComboBox.currentText())+'.txt'
                if self.ui.spNCheckBox.checkState()!=0:
                    yerr2=pl.sqrt(y2/n**2+y2**2/n**3)*g
                    y2=y2/n*g
                    self.fname=self.saveFileName+'_'+str(i)+'_'+str(self.ui.spXComboBox.currentText())+'_'+str(self.ui.spY2ComboBox.currentText())+'_'+str(self.ui.spNComboBox.currentText())+'.txt'
                specscandata=[[x[j],y2[j],yerr2[j]] for j in range(len(x))]   # was yerr: the Y column's errors
                np.savetxt(self.fname,specscandata,fmt='%.4f\t%.4e\t%.4e')
            
            
    def specPlotSettings(self):
        self.spLogX=self.ui.spLogXCheckBox.checkState()
        self.spLogY=self.ui.spLogYCheckBox.checkState()
        self.spGrid=self.ui.spGridCheckBox.checkState()
        self.ui.specPlotMplWidget.canvas.ax.set_xscale('linear')
        self.ui.specPlotMplWidget.canvas.ax.set_yscale('linear')
        self.ui.specPlotMplWidget.canvas.ax.set_xlabel(str(self.ui.spXComboBox.currentText()))
        self.ui.specPlotMplWidget.canvas.ax.set_ylabel(str(self.ui.spYComboBox.currentText()))
        if str(self.ui.spY2ComboBox.currentText())=='None':
            self.ui.specPlotMplWidget.canvas.ax.set_ylabel(str(self.ui.spYComboBox.currentText()))
        else:
            self.ui.specPlotMplWidget.canvas.ax.set_ylabel(str(self.ui.spYComboBox.currentText())+' and '+str(self.ui.spY2ComboBox.currentText()))
        self.ui.specPlotMplWidget.canvas.ax.grid(visible=False)
        # a log axis needs a finite positive value to show: without one (all <= 0,
        # or inf after dividing by a zero monitor) matplotlib's log locator raised
        # while drawing (found by the sweep's random walk, 2026-11-23); such an
        # axis stays linear, with a note in the status bar
        ax=self.ui.specPlotMplWidget.canvas.ax

        def positive(get):
            for l in ax.lines:
                v=np.asarray(get(l),dtype=float)
                if np.any(np.isfinite(v)&(v>0)):
                    return True
            return False
        logx=self.spLogX!=0 and positive(lambda l: l.get_xdata())
        logy=self.spLogY!=0 and positive(lambda l: l.get_ydata())
        if logx:
            ax.set_xscale('log')
        if logy:
            ax.set_yscale('log')
        kept=[n for n,want,got in (('x',self.spLogX!=0,logx),('y',self.spLogY!=0,logy)) if want and not got]
        self.specLogKept=('Log %s: nothing positive to show, kept linear' % ' and '.join(kept)) if kept else ''
        if kept:
            self.ui.statusBar.showMessage(self.specLogKept,8000)
        if self.spGrid!=0:
            self.ui.specPlotMplWidget.canvas.ax.grid(visible=True,color='r',linestyle='--')
        # point labels where the point cannot be drawn (not finite, or <= 0 on a
        # log axis) are hidden: matplotlib clips such a position to a finite but
        # enormous pixel offset, and FreeType raised 'raster overflow' there
        for t in self.ui.specPlotMplWidget.canvas.ax.texts:
            px,py=(float(v) for v in t.get_position())
            t.set_visible(bool(np.isfinite(px) and np.isfinite(py)
                               and (not logx or px>0) and (not logy or py>0)))
        if self.ui.spLegendCheckBox.checkState()!=0:
            self.ui.specPlotMplWidget.canvas.ax.legend(loc=self.ui.spLegendLocComboBox.currentIndex()+1,frameon=False,scatterpoints=0,numpoints=1)
        self.ui.specPlotMplWidget.canvas.draw()
            
        
    def specPlot(self,x,y,n,g=1.0):
        yerr=pl.sqrt(y)
        if self.ui.spNCheckBox.checkState()!=0:
            yerr=pl.sqrt(y/n**2+y**2/n**3)*g
            y=y/n*g
        self.ui.specPlotMplWidget.canvas.ax.errorbar(x,y,yerr,label=self.label,fmt='o-')
        if not self.spPointLabelsCheckBox.isChecked():
            return
        for i in range(len(x)):
            self.ui.specPlotMplWidget.canvas.ax.text(x[i],y[i],str(i),color='r',fontsize=16)
        
    def specPeakFit(self,x,y,yerr):
        par=[x[np.argmax(y)],np.abs(x[-1]-x[0])/2.0,np.max(y),0.0,0.0,np.abs(x[0]-x[1]),0.0,1]
        p=leastsq(self.specPeakRes1,par,args=(x,y,yerr),maxfev=5000)
        if p[0][1]<np.abs(x[0]-x[1]):
            p=leastsq(self.specPeakRes2,par,args=(x,y,yerr),maxfev=5000)
        self.specFitPar=p[0]
        
    
    def specPeakRes1(self,par,x,y,yerr):
        if np.all(np.where(yerr>0,1,0))==True:
            return (y-self.specPeakFun1(par,x))/yerr
        else:
            return (y-self.specPeakFun1(par,x))
            
    def specPeakRes2(self,par,x,y,yerr):
        if np.all(np.where(yerr>0,1,0))==True:
            return (y-self.specPeakFun2(par,x))/yerr
        else:
            return (y-self.specPeakFun2(par,x))
            
        
    def specPeakFun1(self, par, x):
        par[1]=np.abs(par[1])
        par[5]=np.abs(par[5])
        par[7]=-1
        return par[2]*((1+np.tanh((x-par[0]+par[1]/2)/par[5]))/2+(np.tanh(-(x-par[0]-par[1]/2)/par[5])+1)/2)+par[3]+par[4]*(x-par[0])+par[6]*(x-par[0])**2
    
    def specPeakFun2(self, par, x):
        par[1]=np.abs(par[1])
        sig=par[1]/2.0/np.sqrt(2.0*np.log(2.0))
        par[7]=1
        return par[2]*np.exp(-(x-par[0])**2/2.0/sig**2)+par[3]+par[4]*x
        

        
    def checkSameScans(self):
        scanvar=[self.specData[i]['ScanVar'] for i in self.selectedScanNums]
        return all(x==scanvar[0] for  x in scanvar)
    
    def checkSameQzs(self,qzvalues):
        return all(np.abs(x-qzvalues[0])<0.0001 for x in qzvalues)
        
    def checkSameArrays(self,anyarray):
        return all(x==anyarray[0] for x in anyarray)
        
    def updateMcaImageList(self):
        # self.disconnect(self.ui.imageListWidget,SIGNAL('itemSelectionChanged()'),self.imageSelectedScanChanged)
        self.ui.imageListWidget.itemSelectionChanged.disconnect(self.imageSelectedScanChanged)
        self.ui.statusBar.clearMessage()
        self.ui.scanListWidget.blockSignals(True)
        for i in self.selectedScanNums:
            row=self.scanRow(i)
            if row is not None:
                self.ui.scanListWidget.item(row).setSelected(True)
        self.ui.scanListWidget.blockSignals(False)
        self.mcaFileNames=[self.mcafhead+str(i)+self.mcaftail for i in self.selectedScanNums]
        self.mcaData={}
        self.mcaPar={}
        self.mcaAbsorber={}     # absorber setting n of each spectrum's scan (None: unknown)
        self.mcaScanOf={}       # SPEC scan number of each spectrum
        start=0
        try:
            for i in range(len(self.mcaFileNames)):
                # parsed once per file version (lss_core.mcafiles): a selection change re-read every selected file
                data,par=mcafiles.read_mca(self.mcaFileNames[i],beamline=self.beamline)
                spar=self.specPar.get(self.selectedScanNums[i],{})
                n=spar.get('Absorber')
                abstext='' if n is None else '\tAbs=%g' % n + ('' if 'AbsorberFrom' not in spar else ' (#A of S%d)' % spar['AbsorberFrom'])
                spectra=fluorescence.combine_channels([(data[j],par[j]) for j in range(data['NumOfScans'])],
                                                      self.mcaChannels())
                for j,(dj,pj) in enumerate(spectra):
                    self.mcaData[start]=dj
                    self.mcaPar[start]=pj
                    self.mcaAbsorber[start]=n
                    self.mcaScanOf[start]=self.selectedScanNums[i]
                    chtext='\tch '+','.join(map(str,pj['Channels'])) if 'Channels' in pj else ''
                    self.ui.imageListWidget.addItem('S# '+str(self.selectedScanNums[i])+'\tmS# '+str(j+1)+'\tQz='+str(self.mcaPar[start]['Q'][2])+abstext+chtext)
                    start=start+1
        except:
            self.messageBox('MCA file(s) of selected scans do not exit!')
        self.noteMcaAbsorbers()
        # self.connect(self.ui.imageListWidget,SIGNAL('itemSelectionChanged()'),self.imageSelectedScanChanged)
        self.ui.imageListWidget.itemSelectionChanged.connect(self.imageSelectedScanChanged)
        
    def initMonitorGainOption(self):
        """Option (F52): divide by the Monc current, M x S/S_ref, instead of
        the counts M, using the SR570 sensitivity S recorded as '#M Monc
        Gain' (lss_core/monitor.py). One setting, shown beside the monitor
        choice in the MCA tab and in SpecPlot."""
        from PyQt5.QtWidgets import QCheckBox
        self.monitorGain=False
        self.monitorPhotons=False
        self.absorberUnknownNoted=set()     # (SPEC file, scan) with no readable #A, said once
        tip=('Also divide by the Monc gain: normalise by M x S / (5 uA/V, the usual gain) instead of M, with S the SR570 '
             'sensitivity from "#M Monc Gain" (last one above the scan if it has none). Puts scans taken at '
             'different gains on one scale. Only for the Monc monitor; unknown gains get no factor.')
        self.monitorGainBoxes=[]
        for after,layout in ((self.ui.mcaNormComboBox,self.ui.horizontalLayout_12),
                             (self.ui.spNComboBox,self.ui.horizontalLayout_10)):
            box=QCheckBox('/ gain')
            box.setObjectName(('mca' if after is self.ui.mcaNormComboBox else 'sp')+'GainCheckBox')
            box.setToolTip(tip)
            layout.insertWidget(layout.indexOf(after)+1,box)
            box.stateChanged.connect(self.setMonitorGain)
            self.monitorGainBoxes.append(box)
        self.mcaGainCheckBox,self.spGainCheckBox=self.monitorGainBoxes
        # F54: per incident photon (includes the gain), beside each gain box
        ptip=('Divide by the incident photons instead: N = (M - 50 Hz x t) x q(E) x S/(500 nA/V), the photons/s '
              'through the Monc chamber (xray_fluxor hand-off, route D; lss_core/flux.py). Includes "/ gain". '
              'q(E) from the scan energy (5-30 keV); dark 50 Hz, as SPEC does not record it (D41); gas at the '
              "table's 24.9 C and 98.99 kPa. Bounds +-3.6 % below 13 keV, wider above: a common scale, not in "
              'the error bars. Only for the Monc monitor; scans with an unknown gain or energy keep per-count values.')
        self.monitorPhotonBoxes=[]
        for gbox,layout in zip(self.monitorGainBoxes,(self.ui.horizontalLayout_12,self.ui.horizontalLayout_10)):
            box=QCheckBox('/ photon')
            box.setObjectName(gbox.objectName().replace('Gain','Photon'))
            box.setToolTip(ptip)
            layout.insertWidget(layout.indexOf(gbox)+1,box)
            box.stateChanged.connect(self.setMonitorPhotons)
            self.monitorPhotonBoxes.append(box)
        self.mcaPhotonCheckBox,self.spPhotonCheckBox=self.monitorPhotonBoxes

    def initSpecPointLabels(self):
        """Option (F55), on by default: the SPEC plot labels each point
        with its index in the scan (red numbers). Unticked, no labels."""
        from PyQt5.QtWidgets import QCheckBox
        box=QCheckBox('Point #')
        box.setObjectName('spPointLabelsCheckBox')
        box.setToolTip('Label each point of the SPEC plot with its index in the scan (0, 1, 2, ...)')
        box.setChecked(True)
        layout=self.ui.horizontalLayout_8
        layout.insertWidget(layout.indexOf(self.ui.spLegendCheckBox)+1,box)
        self.spPointLabelsCheckBox=box
        box.stateChanged.connect(self.updateSpecPlotData)

    def initAbsFacFromEnergy(self):
        """Option (F49), on by default: the Absorber factor field follows
        the energy of the selected scans (#W), 50 um Al per unit at 10 keV
        and below (lss_core/absorbers.py, NIST SRD 126). Unticked, the
        typed value is used, as before. Where the foil is not known (above
        10 keV; Cu at 30 keV) the field keeps its value and the Messages
        pane says so."""
        from PyQt5.QtWidgets import QCheckBox
        box=QCheckBox('from E')
        box.setObjectName('absFacEnergyCheckBox')
        box.setToolTip('Set the absorber factor from the energy of the selected scans (SPEC #W): the calibrated '
                       'foils at 9.70-10.30 keV (field shows "cal"; File > Preferences), elsewhere 50 um Al per '
                       'unit at <= 10.52 keV, exp(mu/rho rho t) with mu/rho from NIST SRD 126. Untick to type a '
                       'value. Energy scans use the energy in their header.')
        box.setChecked(True)
        layout=self.ui.horizontalLayout_26
        layout.insertWidget(layout.indexOf(self.ui.AbsFacLineEdit)+1,box)
        self.absFacEnergyCheckBox=box
        self.ui.AbsFacLineEdit.setReadOnly(True)
        self.absFacEnergyNoted=set()
        box.stateChanged.connect(self.setAbsFacFromEnergy)

    def setAbsFacFromEnergy(self,state=None):
        on=self.absFacEnergyCheckBox.isChecked()
        self.ui.AbsFacLineEdit.setReadOnly(on)
        if not on and isinstance(self.absfac,absorbers.Foils):   # a typed value replaces the foils
            self.ui.AbsFacLineEdit.setText(str(absorbers.factor_at(self.absfac.energy_kev)[0]))
        self.notify('Absorber factor: '+('from the energy of the selected scans' if on else 'typed value'),
                    title='Absorbers',level='info')
        if on:
            self.absFacFromEnergy()

    def absFacFromEnergy(self):
        """Set the Absorber factor field from the selected scans' energy,
        when the "from E" option is on. Returns the factor set, or None."""
        box=getattr(self,'absFacEnergyCheckBox',None)
        if box is None or not box.isChecked():
            return None
        known,unknown={},{}
        for i in getattr(self,'selectedScanNums',[]):
            wl=self.specPar.get(i,{}).get('Wavelength')
            e=absorbers.energy_kev(wl) if isinstance(wl,(int,float)) and wl>0 else None
            cal=absorbers.calibrated(e) if self.prefs['calibrated_foils'] else None
            a,why=(cal,'calibrated foils at %.2f keV' % cal.energy_kev) if cal is not None else absorbers.factor_at(e)
            (known.setdefault((a,why),[]) if a is not None else unknown.setdefault(why,[])).append(i)
        for why,scans in unknown.items():
            key=(self.specFileName,why)
            if key not in self.absFacEnergyNoted:
                self.absFacEnergyNoted.add(key)
                self.notify('Scan(s) %s: %s; the Absorber factor field keeps %s. Untick "from E" to type a '
                            'value.' % (listText(scans),why,self.ui.AbsFacLineEdit.text()),title='Absorbers')
        if not known:
            return None
        first=min(known,key=lambda k:known[k][0])     # the factor of the first selected scan
        if len(known)>1:
            self.notify('The selected scans are at energies with different absorber factors: '
                        +'; '.join('scan(s) %s: %s' % (listText(v),k[1] if isinstance(k[0],absorbers.Foils) else '%s, %s' % k)
                                   for k,v in sorted(known.items(),key=lambda kv:kv[1][0]))
                        +'. One is applied to all: %s. Reduce them separately.' % first[1],title='Absorbers')
        if isinstance(first[0],absorbers.Foils):
            if self.absfac!=first[0] or self.ui.AbsFacLineEdit.text()!='cal':
                self.ui.AbsFacLineEdit.setText('cal')
                self.absfac=first[0]
            self.ui.AbsFacLineEdit.setToolTip('cal: %s, measured (File > Preferences shows the foils). '
                                              'Untick "from E" to type a factor per unit instead.' % first[1])
        elif self.ui.AbsFacLineEdit.text()!=str(first[0]):
            self.ui.AbsFacLineEdit.setText(str(first[0]))
            self.notify('Absorber factor %s per unit: %s.' % first,title='Absorbers',level='info')
        return first[0]

    def absorberModel(self):
        """The absorber factor in use: the calibrated foils
        (lss_core.absorbers.Foils) or the number in the field."""
        if isinstance(self.absfac,absorbers.Foils):
            return self.absfac
        try:
            value=float(self.ui.AbsFacLineEdit.text())
        except ValueError:
            return self.absfac
        return value if value>0 else self.absfac

    def absorberText(self):
        a=self.absorberModel()
        return ('the calibrated foils (File > Preferences)' if isinstance(a,absorbers.Foils)
                else 'absfac^n with absfac %s (the Absorber factor field)' % a)

    # ---- Tools menu (lss_toolbox; docs/TOOLS.md) ----------------------------

    def initToolsMenu(self):
        """Tools menu: every demonstration and figure generator of the
        repository, run from its current code in its own process (the
        catalogue is lss_toolbox/catalog.py; the window is built when first
        asked for: self.toolsWindow)."""
        from lss_toolbox import menu as toolsmenu
        self.ui.menuTools=toolsmenu.install(self,spec_file=lambda:self.specFileName,
                                            open_spec=lambda path:self.openSpecFile(fname=path),
                                            notify=lambda text:self.notify(text,'Tools','info'))

    # ---- preferences (File > Preferences) ---------------------------------

    def initPreferences(self):
        from PyQt5.QtWidgets import QAction
        act=QAction('Preferences...',self)
        act.setObjectName('actionPreferences')
        act.setToolTip('Absorber foils and Ref Patch settings, kept between sessions')
        self.ui.menuFile.insertAction(self.ui.actionQuit,act)
        act.triggered.connect(self.showPreferences)
        self.ui.actionPreferences=act
        self.preferencesDialog=None

    def showPreferences(self):
        if self.preferencesDialog is None:
            self.preferencesDialog=self.buildPreferences()
        self.preferencesDialog.show()
        self.preferencesDialog.raise_()

    def buildPreferences(self):
        """Short labels; the explanations are in the tooltips."""
        from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox, QLabel,
                                     QTableWidget, QTableWidgetItem, QDoubleSpinBox, QPushButton, QAbstractItemView)
        from PyQt5.QtCore import Qt as QtC
        d=QDialog(self)
        d.setObjectName('preferencesDialog')
        d.setWindowTitle('Preferences')
        lay=QVBoxLayout(d)
        g=QGroupBox('Absorber foils',d)
        gl=QVBoxLayout(g)
        cal=QCheckBox('Calibrated foils',g)
        cal.setObjectName('prefCalibratedCheckBox')
        cal.setChecked(self.prefs['calibrated_foils'])
        cal.setToolTip('Use the measured foil thicknesses below instead of 50 um Al per unit, at %.2f-%.2f keV, '
                       'when "from E" is ticked. Measured: %s. Elsewhere, or unticked: 50 um Al per unit '
                       '(NIST SRD 126).' % (absorbers.CAL_RANGE_KEV+(absorbers.CAL_PROVENANCE,)))
        gl.addWidget(cal)
        t=QTableWidget(len(absorbers.CAL_FOILS_UM),4,g)
        t.setObjectName('prefFoilTable')
        t.setHorizontalHeaderLabels(['units','nominal um','calibrated um','+/- um'])
        t.setVerticalHeaderLabels(['foil %d' % k for k in range(len(absorbers.CAL_FOILS_UM))])
        tips=['Absorber units of this foil: SPEC #A is the sum of the foils in (binary)',
              '50 um of Al per unit (beamline)',
              'Al-equivalent thickness at 10 keV, fitted to measured joins. Hover a value for its fit error',
              'Run-to-run spread of the foil (leave one run out), used for the error of a ratio: these in '
              'quadrature for the foils that change, plus %.1f %% per step; x%.1f when the overlap is at '
              'Qz >= %.2f 1/A, where single steps scatter more (ABSORBER_RATIOS.md)'
              % (100*absorbers.CAL_STEP_SCATTER,absorbers.CAL_HIGH_QZ_SCALE,absorbers.CAL_HIGH_QZ)]
        for c,tip in enumerate(tips):
            t.horizontalHeaderItem(c).setToolTip(tip)
        for k,(tk,ek,rk) in enumerate(zip(absorbers.CAL_FOILS_UM,absorbers.CAL_FOILS_FIT_ERR_UM,absorbers.CAL_FOILS_RUN_UM)):
            for c,val in enumerate(('%d' % 2**k,'%g' % (absorbers.UNIT_THICKNESS_UM*2**k),'%.1f' % tk,'%.1f' % rk)):
                it=QTableWidgetItem(val)
                it.setFlags(it.flags() & ~QtC.ItemIsEditable)
                it.setTextAlignment(int(QtC.AlignRight | QtC.AlignVCenter))
                if c==2:
                    it.setToolTip('%.1f +/- %.1f um (fit); +/- %.1f um run to run' % (tk,ek,rk))
                t.setItem(k,c,it)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setToolTip(absorbers.CAL_PROVENANCE)
        t.resizeColumnsToContents()
        t.setMinimumHeight(t.verticalHeader().length()+t.horizontalHeader().height()+6)
        gl.addWidget(t)
        rng=QLabel('%.2f-%.2f keV' % absorbers.CAL_RANGE_KEV,g)
        rng.setObjectName('prefFoilRangeLabel')
        rng.setToolTip('Energies where the calibration is used, with the mu/rho of Al at the energy: no K edge of '
                       'the usual Al impurities lies in this range. Measured at 10 keV.')
        gl.addWidget(rng)
        lay.addWidget(g)
        g2=QGroupBox('Ref Patch',d)
        hl=QHBoxLayout(g2)
        auto=QCheckBox('Known ratio when fit error >',g2)
        auto.setObjectName('prefPatchAutoCheckBox')
        auto.setChecked(self.prefs['patch_auto_known_ratio'])
        auto.setToolTip('At a join, use the absorber ratio of the calibrated foils instead of the fitted patch '
                        'factor when the fit error is above this, the ratio is at least twice as precise '
                        '(its error is 3.2 times larger when the overlap is at Qz >= 0.25 1/A), '
                        'Monc/Monp shows no slit change across the join, and the two agree within 3 sigma. '
                        'The patch window shows the choice and can undo it.')
        spin=QDoubleSpinBox(g2)
        spin.setObjectName('prefPatchThresholdSpinBox')
        spin.setRange(0.1,100.0)
        spin.setSingleStep(0.5)
        spin.setDecimals(1)
        spin.setSuffix(' %')
        spin.setValue(self.prefs['patch_threshold_percent'])
        spin.setEnabled(auto.isChecked())
        spin.setToolTip('Relative error of the fitted patch factor above which the known ratio is used')
        hl.addWidget(auto)
        hl.addWidget(spin)
        meth=QComboBox(g2)
        meth.setObjectName('prefPatchMethodComboBox')
        meth.addItem('Joint fit','joint')
        meth.addItem('Legacy fit','legacy')
        meth.setCurrentIndex(max(0,meth.findData(self.refPatchMethod())))
        meth.setToolTip('How the scale factor at a join is fitted. Joint fit (default since 2026-11-22): one smooth '
                        'curve in ln(R/R_F) through both scans, the factor fitted with it, from the overlap and up to '
                        '2 points either side; where its chi-squared is poor (p < 0.3) the window shrinks and the '
                        'order rises until it fits, otherwise its error is inflated. Unbiased where the legacy fit '
                        'is not (+5.5 % on a thick film\'s fringes, P1) and with honest errors (the legacy ones are '
                        '1.1-4.8 times too small), measured on synthetic scans '
                        '(tests/tools/ref_patch_gauntlet.py). Legacy fit: scan b interpolated at the overlap points '
                        'and one ratio fitted, as before; it reproduces older files exactly.')
        hl.addWidget(meth)
        lay.addWidget(g2)
        g3=QGroupBox('Fluorescence detector',d)
        g3.setToolTip('Multi-element detector (7-element Xspress3): the elements summed into one spectrum per '
                      'point, for plotting and reduction. EXAFS sums all seven; XFNTR uses the central one. '
                      'Single-element files are not affected. The 7-element detector corrects its own dead time; '
                      'the 1-element one is corrected here by real/live time (#@CTIME).')
        h3=QHBoxLayout(g3)
        boxes=[]
        sel=self.mcaChannels()
        for k in range(1,8):
            b=QCheckBox(str(k),g3)
            b.setObjectName('prefMcaChannel%dCheckBox' % k)
            b.setChecked(not sel or k in sel)
            b.setToolTip('Element %d (#@CHANNEL %d in the MCA file)' % (k,k))
            h3.addWidget(b)
            boxes.append(b)
        allb=QPushButton('All',g3)
        allb.setObjectName('prefMcaAllPushButton')
        allb.setToolTip('Sum all elements (EXAFS)')
        h3.addWidget(allb)
        centreb=QPushButton('Centre',g3)
        centreb.setObjectName('prefMcaCentrePushButton')
        centreb.setToolTip('The central element only, element 1 (XFNTR; owner, 2026-11-19)')
        h3.addWidget(centreb)
        lay.addWidget(g3)

        def channels_changed(*_):
            chosen=[k for k,b in enumerate(boxes,1) if b.isChecked()]
            self.setPreference('mca_channels',[] if len(chosen) in (0,7) else chosen)

        def all_on():
            for b in boxes:
                b.blockSignals(True)
                b.setChecked(True)
                b.blockSignals(False)
            channels_changed()
        def centre_only():
            for k,b in enumerate(boxes,1):
                b.blockSignals(True)
                b.setChecked(k==1)
                b.blockSignals(False)
            channels_changed()
        for b in boxes:
            b.toggled.connect(channels_changed)
        allb.clicked.connect(all_on)
        centreb.clicked.connect(centre_only)
        d.prefMcaChannelBoxes=boxes
        g4=QGroupBox('Saving',d)
        g4.setToolTip('The Save buttons store results in this SPEC file\'s workbook (<SPEC file>_reader.xlsx in the output '
                      'folder: sheets Scans, Saved, Data, Fits, Trends, Maps, Settings). Export still writes the usual text files.')
        l4=QVBoxLayout(g4)
        asknote=QCheckBox('Ask for a note on every Save',g4)
        asknote.setObjectName('prefSaveNoteCheckBox')
        asknote.setChecked(bool(self.prefs.get('save_asks_note',True)))
        asknote.setToolTip('On (default): every Save asks for a short note, kept with that version in the workbook (Saved '
                           'sheet); Shift-click a Save button to save without asking. Off: never asks; Shift-click asks.')
        asknote.toggled.connect(lambda on:self.setPreference('save_asks_note',bool(on)))
        l4.addWidget(asknote)
        autos=QCheckBox('Save every reduction automatically',g4)
        autos.setObjectName('prefAutoSaveCheckBox')
        autos.setChecked(bool(self.prefs.get('auto_save',True)))
        autos.setToolTip('On (default; owner, 2026-11-22): whenever a reduction is carried through (reflectivity '
                         'patch, line cut or its fit, GID map or GID cut, MCA sum, line fit or merge, burn test) its '
                         'result is saved into the workbook without a question, marked "auto" in the Saved sheet\'s '
                         'origin column; an identical result is not stored twice. The Save buttons still save a '
                         'version with a note. Off: only the Save buttons save.')
        autos.toggled.connect(lambda on:self.setPreference('auto_save',bool(on)))
        l4.addWidget(autos)
        lay.addWidget(g4)
        d.prefSaveNoteCheckBox=asknote
        d.prefAutoSaveCheckBox=autos
        g5=QGroupBox('Layout',d)
        l5=QVBoxLayout(g5)
        ngui=QCheckBox('ngui (new layout, prototype)',g5)
        ngui.setObjectName('prefNguiCheckBox')
        ngui.setChecked(bool(self.prefs.get('ngui',False)))
        ngui.setToolTip('Opens a second window beside this one: a non-functional sketch of the proposed new layout '
                        '(tabs by workflow, the selection panel at full height, panes under the tabs). Its controls '
                        'are disabled placeholders whose tooltips say where each control is today; nothing in it '
                        'reads or reduces data, and this window is unchanged. Unticking closes it. Off by default '
                        '(F82; docs/gui/prototype.md).')
        ngui.toggled.connect(self.setNgui)
        l5.addWidget(ngui)
        lay.addWidget(g5)
        d.prefNguiCheckBox=ngui
        close=QPushButton('Close',d)
        close.setObjectName('prefClosePushButton')
        close.clicked.connect(d.close)
        lay.addWidget(close)
        cal.toggled.connect(lambda on:self.setPreference('calibrated_foils',bool(on)))
        auto.toggled.connect(lambda on:(spin.setEnabled(on),self.setPreference('patch_auto_known_ratio',bool(on))))
        spin.valueChanged.connect(lambda v:self.setPreference('patch_threshold_percent',float(v)))
        meth.currentIndexChanged.connect(lambda i:self.setPreference('ref_patch_method',str(meth.itemData(i))))
        d.prefCalibratedCheckBox,d.prefFoilTable,d.prefPatchAutoCheckBox,d.prefPatchThresholdSpinBox=cal,t,auto,spin
        d.prefPatchMethodComboBox=meth
        return d

    def setNgui(self,on):
        """Open (on) or close the ngui prototype window (F82), and keep the choice. The window is a child
        of this one (Qt.Window), so it closes and is disposed with it."""
        self.setPreference('ngui',bool(on))
        w=getattr(self,'nguiWindow',None)
        if on:
            if w is None:
                from ngui.window import open_window      # lazily: the prototype costs nothing when off
                self.nguiWindow=open_window(self)
            else:
                w.show()
                w.raise_()
        elif w is not None:
            w.close()
            w.deleteLater()
            self.nguiWindow=None

    def mcaChannels(self):
        """Elements of a multi-element fluorescence detector to sum (empty: all)."""
        ch=self.prefs.get('mca_channels',[])
        return [int(c) for c in ch if isinstance(c,int) and not isinstance(c,bool)]

    def setPreference(self,key,value):
        if self.prefs.get(key)==value:
            return
        self.prefs[key]=value
        err=prefs_store.save(self.prefs)
        if err and not getattr(self,'prefsSaveNoted',False):
            self.prefsSaveNoted=True
            self.notify('Preferences could not be saved (%s); they hold for this session.' % err,title='Preferences')
        if key=='calibrated_foils':
            if not value and isinstance(self.absfac,absorbers.Foils):
                self.ui.AbsFacLineEdit.setText(str(absorbers.factor_at(self.absfac.energy_kev)[0]))
            self.notify('Absorbers: '+('calibrated foils where they apply' if value else '50 um Al per unit'),
                        title='Absorbers',level='info')
            self.absFacFromEnergy()
        if key=='mca_channels':
            self.notify('Fluorescence detector: '+('all elements summed' if not value else
                        'element(s) %s' % ', '.join(map(str,value))),title='Fluorescence detector',level='info')
            scans=getattr(self,'selectedScanNums',None) or []
            if scans and self.specPar.get(scans[0],{}).get('Detector')=='Vortex' and getattr(self,'mcafhead',None):
                self.forgetImageSelection()
                self.ui.imageListWidget.blockSignals(True)
                self.ui.imageListWidget.clear()       # rebuilt with the new elements (the list builder appends)
                self.ui.imageListWidget.blockSignals(False)
                self.updateMcaImageList()

    def setMonitorGain(self,state=None):
        on=bool(self.sender().isChecked()) if self.sender() in self.monitorGainBoxes else bool(state)
        self.setMonitorMode(on,self.monitorPhotons and on)     # unticking the gain unticks "per photon"

    def setMonitorPhotons(self,state=None):
        on=bool(self.sender().isChecked()) if self.sender() in self.monitorPhotonBoxes else bool(state)
        self.setMonitorMode(self.monitorGain or on,on)         # per photon includes the gain

    def monitorMode(self):
        """'photons', 'gain' or False: the Monc normalisation in use."""
        return 'photons' if self.monitorPhotons else ('gain' if self.monitorGain else False)

    def setMonitorMode(self,gain,photons):
        for boxes,on in ((self.monitorGainBoxes,gain),(self.monitorPhotonBoxes,photons)):
            for box in boxes:
                box.blockSignals(True)
                box.setChecked(on)
                box.blockSignals(False)
        if (gain,photons)==(self.monitorGain,self.monitorPhotons):
            return
        self.monitorGain,self.monitorPhotons=gain,photons
        what=('per incident photon, N = (M - D t) q(E) S/(500 nA/V) (xray_fluxor route D)' if photons else
              'Monc current, M x S/(5 uA/V), S from "#M Monc Gain"' if gain else 'Monc counts M (gain not used)')
        self.notify('Monitor normalisation: '+what
                    +'. Spectra, SPEC plots and background-subtracted images on show are recomputed; cuts, GID and '
                    'frames at one Qz use it the next time they are computed. Ref Patch does not use it (it measures '
                    'the scale between scans).',title='Monitor',level='info')
        if self.selectedMcaScanNums is not None and len(self.selectedMcaScanNums)>0 and getattr(self,'mcaData',None):
            self.updateMcaPlotData()
        if self.det=='Pilatus' and len(self.ui.backgroundListWidget.selectedItems())>0:
            self.bgSelectionChanged()       # background and background-subtracted frames
        self.updateSpecPlotData()

    def monitorGainFactor(self,scannum,column,rate=None):
        """S_ref/S for scan ``scannum`` when the option is on and ``column``
        is Monc; 1 otherwise (and when the gain is unknown, said once).
        With "per photon" on, M/N per incident photon (F54); ``rate``: the
        monitor rate (Hz) for the dark term, else the scan's median
        Monc/Seconds."""
        if not self.monitorGain or str(column).lower()!='monc' or scannum is None:
            return 1.0
        spar=self.specPar.get(scannum,{})
        if self.monitorPhotons and spar.get('MoncGain') is not None:
            if rate is None:
                rate=scan_rate(self.specData.get(scannum,{}) if isinstance(self.specData,dict) else {})
            f,known=monitor_factor(spar,per_photon=True,rate_hz=rate)
            if not known:
                seen=getattr(self,'photonUnknownNoted',set())
                if (self.specFileName,scannum) not in seen:
                    seen.add((self.specFileName,scannum))
                    self.photonUnknownNoted=seen
                    wl=spar.get('Wavelength')
                    self.notify('Scan %d: photons per monitor count not known (%s); its values stay per monitor count.'
                                % (scannum,'energy %.3g keV outside 5-30 keV' % absorbers.energy_kev(wl)
                                   if isinstance(wl,(int,float)) and wl>0 else 'energy unknown'),
                                title='Monitor',level='warning')
                return 1.0
            return f
        if spar.get('MoncGain') is None:
            seen=getattr(self,'gainUnknownNoted',set())
            if (self.specFileName,scannum) not in seen:
                seen.add((self.specFileName,scannum))
                self.gainUnknownNoted=seen
                self.notify('Scan %d: Monc gain unknown (%s); no gain factor applied to it.'
                            % (scannum,'"#M Monc Gain %s"' % spar['MoncGainText'] if 'MoncGainText' in spar else 'no #M above it'),
                            title='Monitor',level='warning')
            return 1.0
        return gain_factor(spar['MoncGain'])

    def sumAllLegacy(self):
        """True when "Sum All" keeps the legacy mean of the normalised frames
        (the Reduction options page, F86; preference 'sum_all_legacy_average',
        off by default since 2026-11-23, F91)."""
        return bool(self.prefs.get('sum_all_legacy_average',False))

    def gisaxsRawCounts(self):
        """True when GISAXS keeps the raw counts it showed until 2026-11-23
        (preference 'gisaxs_raw_counts', for the Reduction options page, F86;
        off: GISAXS is per Monc like every other reduction)."""
        return bool(self.prefs.get('gisaxs_raw_counts',False))

    def pilFrameNormalised(self,i):
        """(value, error) of frame ``i`` per monitor (Monc), absorber and gain:
        what every reduction, the image display and GISAXS use (owner,
        2026-11-23: "all data is default normalized by monc, even gisaxs").
        Background-subtracted frames are normalised already (sumFiles);
        self.pilData keeps the frames as read, for the reductions that
        normalise them themselves (Ref Patch)."""
        if len(self.ui.backgroundListWidget.selectedItems())!=0:
            return self.pilData[i],self.pilErrorData[i]
        g=self.pilGains([self.pilScanNum[i]])
        return normalise.normalise_frame(self.pilData[i],self.pilErrorData[i],self.pilMonc[i],self.absfac,
                                         self.pil_AbsNum[i],model=self.errorModel,gain=1.0 if g is None else g[0])

    def pilSumNormalised(self,frames):
        """"Sum All" of the normalised frames: counts and monitors summed and
        normalised once, ΣN/ΣM (F91), or their mean ('sum_all_legacy_average')."""
        d,e=zip(*[self.pilFrameNormalised(i) for i in frames])
        if self.sumAllLegacy():
            return cuts.mean_frame(list(d),list(e))
        return cuts.sum_frames(list(d),list(e),[self.pilNormaliser(i) for i in frames])

    def gisaxsData(self,frames):
        """(value, error) GISAXS is made from: per Monc, ΣN/ΣM when several
        frames are summed; with 'gisaxs_raw_counts' the raw counts, and their
        mean when summed, as until 2026-11-23."""
        if self.gisaxsRawCounts():
            if len(frames)==1:
                return self.pilData[frames[0]],self.pilErrorData[frames[0]]
            d,e=self.pilData[frames[0]],self.pilErrorData[frames[0]]**2
            for i in frames[1:]:
                d,e=d+self.pilData[i],e+self.pilErrorData[i]**2
            return d/float(len(frames)),np.sqrt(e)/float(len(frames))
        if len(frames)==1:
            return self.pilFrameNormalised(frames[0])
        return self.pilSumNormalised(frames)

    def pilNormaliser(self,i):
        """Frame ``i``'s weight in "Sum All": its monitor over the absorber and
        gain factors it is normalised with (lss_core.cuts.frame_normaliser)."""
        g=self.pilGains([self.pilScanNum[i]])
        return cuts.frame_normaliser(self.pilMonc[i],self.absfac,self.pil_AbsNum[i],1.0 if g is None else g[0])

    def pilGains(self,scans):
        """Monitor-gain factors for Pilatus frames of ``scans`` (Pilatus
        frames are always normalised by Monc); None when the option is off,
        which keeps the legacy arithmetic."""
        if not self.monitorGain:
            return None
        return [self.monitorGainFactor(int(sc),'Monc') for sc in scans]

    def absFacChanged(self,text):
        try:
            value=float(text)
        except ValueError:
            return          # partly typed; the last valid value stays in use
        if value>0:
            self.absfac=value

    def noteMcaAbsorbers(self):
        """Say where the absorber setting of the listed MCA scans came from:
        getandsave_mca writes no #A, so it is the last #A above the scan
        (owner, 2026-11-17, F50), or unknown when there is none."""
        seen=getattr(self,'mcaAbsorberNoted',set())
        inferred,unknown={},[]
        for i in self.selectedScanNums:
            spar=self.specPar.get(i,{})
            if (self.specFileName,i) in seen or spar.get('Detector')!='Vortex':
                continue
            seen.add((self.specFileName,i))
            if spar.get('Absorber') is None:
                unknown.append(i)
            elif 'AbsorberFrom' in spar:
                inferred.setdefault((spar['Absorber'],spar['AbsorberFrom']),[]).append(i)
        self.mcaAbsorberNoted=seen
        if inferred:
            self.notify('MCA scans record no absorber setting; it is taken from the last #A above each scan '
                        '(absorbers do not change during a scan), and normalised spectra are multiplied by '
                        '%s: ' % self.absorberText()
                        +'; '.join('scan(s) %s: n = %g from the #A of scan %d' % (listText(v),k[0],k[1])
                                   for k,v in sorted(inferred.items(),key=lambda kv:kv[1][0]))+'.',
                        title='Absorbers',level='info')
        if unknown:
            self.notify('MCA scan(s) %s: no #A above them in the file, so the absorber setting is unknown; '
                        'no absorber factor is applied.' % listText(unknown),title='Absorbers',level='info')

    def mcaAbsorberFactor(self,i):
        """absfac**n for MCA spectrum ``i`` (1 when its setting is unknown)."""
        return fluorescence.absorber_factor(self.absfac,getattr(self,'mcaAbsorber',{}).get(i))

    def mcaSelectedScanChanged(self):
        self.ui.statusBar.clearMessage()
        self.selectedMcaScans=self.ui.imageListWidget.selectedItems()
        self.selectedMcaScanNums=[self.ui.imageListWidget.row(items) for items in self.selectedMcaScans]
        self.mcafitplotstatus=0
        try:
            self.ui.PlotWidget.setCurrentIndex(5)
            self.updateMcaPlotData()
        except:
            self.ui.statusBar.showMessage('Warning:: Some scans maybe missing!')
            
            
            
    def updateMcaPlotData(self):
        if len(self.selectedMcaScanNums)==0:
            pass
        elif (str(self.ui.mcaNormComboBox.currentText())!='None' and
              any(i in self.mcaData and str(self.ui.mcaNormComboBox.currentText()) not in self.mcaData[i]
                  for i in self.selectedMcaScanNums)):
            self.messageBox('The monitor '+str(self.ui.mcaNormComboBox.currentText())+' is not in the MCA data, please choose another one.')
        else:

            self.ui.statusBar.clearMessage()
            self.ui.mcaPlotMplWidget.canvas.ax.clear()
            self.nomMcaData={}
            fact=1.0

            if len(self.selectedMcaScanNums) > 10:
                self.progressDialog = QProgressDialog('Reading MCA Frames', 'Abort', 0, 100)
                self.progressDialog.setWindowModality(Qt.WindowModal)
                self.progressDialog.setWindowTitle('Wait')
                self.progressDialog.setAutoClose(True)
                self.progressDialog.setAutoReset(True)
                self.progressDialog.setMinimum(1)
                self.progressDialog.setMaximum(len(self.selectedMcaScanNums))
                self.progressDialog.show()

            self.mcaMax=0
            self.absfac=self.absorberModel()
            self.mcaAbsfacUsed=self.absfac
            self.mcaGainUsed=self.monitorMode() if str(self.ui.mcaNormComboBox.currentText())=='Monc' else False
            if str(self.ui.mcaNormComboBox.currentText())!='None':
                self.noteMixedAbsorbers([self.mcaAbsorber[i] for i in self.selectedMcaScanNums
                                         if getattr(self,'mcaAbsorber',{}).get(i) is not None],'The selected MCA spectra')

            for i in self.selectedMcaScanNums:
                y=pl.array(self.mcaData[i]['Vortex'],dtype='float')
                x=pl.arange(1,len(y)+1)
                if self.ui.mcaCalibCheckBox.checkState()!=0:
                    self.ui.mcaCalibConLineEdit.setText(str(self.mcaPar[i]['Calib'][0]))
                    self.ui.mcaCalibLinLineEdit.setText(str(self.mcaPar[i]['Calib'][1]))
                    self.ui.mcaCalibQuaLineEdit.setText(str(self.mcaPar[i]['Calib'][2]))
                con=float(self.ui.mcaCalibConLineEdit.text())
                lin=float(self.ui.mcaCalibLinLineEdit.text())
                qua=float(self.ui.mcaCalibQuaLineEdit.text())
                x=con+lin*x+qua*x**2
                if str(self.ui.mcaNormComboBox.currentText())!='None':
                    monitor=str(self.ui.mcaNormComboBox.currentText())
                    n=self.mcaData[i][monitor]
                    tc=self.mcaPar[i]['Time'][1]/self.mcaPar[i]['Time'][2]  #real count time correction
                    a=self.mcaAbsorberFactor(i)
                    try:
                        r=float(n)/float(self.mcaPar[i]['Time'][1])     # this spectrum's monitor rate
                    except (KeyError,IndexError,TypeError,ValueError,ZeroDivisionError):
                        r=None
                    g=self.monitorGainFactor(self.mcaScanOf.get(i),monitor,rate=r)
                    self.nomMcaData[i]=fluorescence.normalise_spectrum(self.mcaData[i]['Vortex'],self.mcaPar[i],n,(con,lin,qua),self.errorModel,a,g)
                    a=a*g      # both factors on the plotted spectrum
                else:
                    n=1
                    tc=1
                    a=1.0       # raw counts: no absorber factor
                    self.nomMcaData[i]=fluorescence.normalise_spectrum(self.mcaData[i]['Vortex'],self.mcaPar[i],None,(con,lin,qua))
                self.mcaLabel=str(i+1)+' Qz='+'%.4f'%self.mcaPar[i]['Q'][2]
                if self.ui.mcaOffsetCheckBox.checkState()!=0:
                    fact=fact*float(self.ui.mcaOffsetLineEdit.text())
                self.mcaPlot(x,y,n,tc,fact,a)
                if len(self.selectedMcaScanNums) > 10:
                    self.progressDialog.setLabelText('Reading MCA Frame #' + str(i))
                    self.updateProgress()
                    if self.progressDialog.wasCanceled() == True:
                        break
            if len(self.selectedMcaScanNums) > 10:
                self.progressDialog.hide()
            self.mcaPlotSettings()
            self.ui.statusBar.showMessage('Done')
        
    def mcaPlot(self,x,y,n,tc,fact,a=1.0):
        if str(self.ui.mcaNormComboBox.currentText())!='None' and self.errorModel.budget:
            u=self.errorModel.monitor.relative(n)
            yerr=pl.sqrt(y/n**2*tc**2+(y/n*tc)**2*u**2)
        elif str(self.ui.mcaNormComboBox.currentText())!='None':
            yerr=pl.sqrt(y+y**2/n)/n*tc
        else:
            yerr=pl.sqrt(y)
        y=y/n*tc
        if a!=1.0:      # absorber factor absfac**n
            y,yerr=y*a,yerr*a
        self.mcaMax=max(self.mcaMax,max(y+yerr))
        # one path for all the bars (mplwidget.errorbars): many spectra on a log axis were slow to draw (2026-11-23)
        errorbars(self.ui.mcaPlotMplWidget.canvas.ax,x,fact*y,fact*yerr,fmt='o-',label=self.mcaLabel)

        
    def updateMCAPlotVline(self):
        try:
            # left = float(str(self.ui.mcaRanLineEdit.text()).split(':')[0])
            # right = float(str(self.ui.mcaRanLineEdit.text()).split(':')[1])
            # self.leftLine.set_xdata([left, left])
            # self.rightLine.set_xdata([right, right])
            self.mcavlines.remove()
        except:
            pass
        self.mcaPlotSettings()

    def mcaPlotSettings(self):
        self.mcaLogX=self.ui.mcaLogXCheckBox.checkState()
        self.mcaLogY=self.ui.mcaLogYCheckBox.checkState()
        self.mcaGrid=self.ui.mcaGridCheckBox.checkState()
        self.ui.mcaPlotMplWidget.canvas.ax.set_xscale('linear')
        self.ui.mcaPlotMplWidget.canvas.ax.set_yscale('linear')
        self.ui.mcaPlotMplWidget.canvas.ax.set_xlabel('Energy')
        self.ui.mcaPlotMplWidget.canvas.ax.set_ylabel('Intensity')
        self.ui.mcaPlotMplWidget.canvas.ax.set_title('Fluorescence Spectrum')

        try:
            left = float(str(self.ui.mcaRanLineEdit.text()).split(':')[0])
            right = float(str(self.ui.mcaRanLineEdit.text()).split(':')[1])
            self.mcavlines=self.ui.mcaPlotMplWidget.canvas.ax.vlines(x=[left,right], ymin=0, ymax=self.mcaMax, color='k')
        except:
            pass



        self.ui.mcaPlotMplWidget.canvas.ax.grid(visible=False)
        mcalines=self.ui.mcaPlotMplWidget.canvas.ax.lines   # a log axis needs something positive to show
        if self.mcaLogX!=0 and any(np.any(np.asarray(l.get_xdata(),dtype=float)>0) for l in mcalines):
            self.ui.mcaPlotMplWidget.canvas.ax.set_xscale('log')
        if self.mcaLogY!=0 and any(np.any(np.asarray(l.get_ydata(),dtype=float)>0) for l in mcalines):
            self.ui.mcaPlotMplWidget.canvas.ax.set_yscale('log')
        if self.mcaGrid!=0:
            self.ui.mcaPlotMplWidget.canvas.ax.grid(visible=True,color='r',linestyle='--')
        if self.ui.mcaLegendCheckBox.checkState()!=0:
            self.ui.mcaPlotMplWidget.canvas.ax.legend(loc=self.ui.mcaLegendLocComboBox.currentIndex()+1,frameon=False,scatterpoints=0,numpoints=1)
        else:
            self.ui.mcaPlotMplWidget.canvas.ax.legend().set_visible(False)
        if self.mcafitplotstatus==1:
             fit=np.array(self.peakfitdata)
             xran=np.abs(fit[:,0][-1]-fit[:,0][0])
             yran=np.max(fit[:,1])-np.min(fit[:,1])
             self.ui.mcaPlotMplWidget.canvas.ax.plot(fit[:,0],fit[:,1],'r-',zorder=1)
             self.ui.mcaPlotMplWidget.canvas.ax.set_xlim(fit[:,0][0]-0.25*xran,fit[:,0][-1]+0.25*xran)
             self.ui.mcaPlotMplWidget.canvas.ax.set_ylim(np.min(fit[:,1])-0.2*yran,np.max(fit[:,1])+0.2*yran)
        self.ui.mcaPlotMplWidget.canvas.ax.autoscale(tight=True)
        self.ui.mcaPlotMplWidget.canvas.draw()
            
    def saveMcaData(self):
        self.saveMcaFileName=QFileDialog.getSaveFileName(caption='Save Mca data',directory=self.directory)[0]
        if self.saveMcaFileName=='':   # dialog cancelled: write nothing
            return
        for i in self.selectedMcaScanNums:
            self.fmcaName=self.saveMcaFileName+str(self.ui.imageListWidget.item(i).text().split('\t')[0])+'_'+str(self.ui.imageListWidget.item(i).text().split('\t')[1])+'_''%.4f'%self.mcaPar[i]['Q'][2]+'_mca.txt'
            np.savetxt(self.fmcaName,self.nomMcaData[i],fmt='%.4f\t%.4e\t%.4e')
            
    def mcaPeakFit(self):  #fit the mca spectrum
        self.mcafitstatus=1 #let self.peakfit know it's mca fit
        self.mcafitallstatus=0
        self.peakFit()
        
    def mcaPeakFitAll(self): #fit all selected spectrum
        self.mcafitallstatus=1
        self.peakFit()
 
    # def mcaSum(self):  # sum one selected spectrum with given range
    #     data=self.nomMcaData[self.selectedMcaScanNums[0]]
    #     ini=max(float(str(self.ui.mcaRanLineEdit.text()).split(':')[0]),data[0][0])
    #     fin=min(float(str(self.ui.mcaRanLineEdit.text()).split(':')[1]),data[-1][0])
    #     print ini, fin
    #     dataran=np.where((np.logical_and(data[0:]<=fin,data[0:]>=ini)))
    #     print dataran[0]
    #     newdata=data[dataran[0][0]:dataran[0][-1]+1]
    #     print newdata
    #     print np.sum(newdata[:,1]), np.sqrt(np.sum(newdata[:,2]**2))
    
    def mcaSumAll(self):  #sum all selected spectrum with given range
        try:
            gain=self.monitorMode() if str(self.ui.mcaNormComboBox.currentText())=='Monc' else False
            if self.selectedMcaScanNums is not None and len(self.selectedMcaScanNums)>0 and (
                    self.absorberModel()!=getattr(self,'mcaAbsfacUsed',None)
                    or gain!=getattr(self,'mcaGainUsed',False)):
                self.updateMcaPlotData()        # the absorber factor or the gain option changed since
        except ValueError:
            pass
        self.mcaIntData=[]
        self.ui.mcaDataListWidget.clear()
        try:
            for i in range(len(self.selectedMcaScanNums)):
                data=self.nomMcaData[self.selectedMcaScanNums[i]]
                u=None
                mon=str(self.ui.mcaNormComboBox.currentText())
                if self.errorModel.budget and mon!='None':
                    u=float(self.errorModel.monitor.relative(self.mcaData[self.selectedMcaScanNums[i]][mon]))
                inten,error,ini,fin=fluorescence.window_sum(data,float(str(self.ui.mcaRanLineEdit.text()).split(':')[0]),float(str(self.ui.mcaRanLineEdit.text()).split(':')[1]),u)
                frame=self.selectedMcaScanNums[i]+1
                qz=self.mcaPar[self.selectedMcaScanNums[i]]['Q'][2]
                try:
                    energy=self.mcaPar[self.selectedMcaScanNums[i]]['Energy']
                except:
                    energy=10.0
                #print newdata, inten, error
                self.mcaIntData.append([frame, qz, energy, inten, error])
                if self.ui.mcaXAxisComboBox.currentIndex()==0:
                    string=str(int(frame))+'\t'+'%.4e'%inten+'\t'+'%.4e'%error
                elif self.ui.mcaXAxisComboBox.currentIndex()==1:
                    string='%.4f'%qz+'\t'+'%.4e'%inten+'\t'+'%.4e'%error
                else:
                    string='%.4f'%energy+'\t'+'%.4e'%inten+'\t'+'%.4e'%error
                self.ui.mcaDataListWidget.addItem(string)
            self.updateMcaIntPlot()
            rng=str(self.ui.mcaRanLineEdit.text()).split(':')
            self.mcaSumScript=(sorted(int(n) for n in self.selectedScanNums),float(rng[0]),float(rng[1]),
                               len(self.selectedMcaScanNums)==self.ui.imageListWidget.count())
            self.mcaMerges=[]       # Merge actions since this Sum All, for the Script pane
            self.command='Flu Sum, scans=['+listText(np.sort(self.selectedScanNums))+'], energy range=['+str(ini)+':'+str(fin)+']'
            self.ui.commandLineEdit.setText(self.command)
        except:
            self.messageBox('Please input the proper sum range in the format of "min:max"!')
            self.ui.mcaRanLineEdit.setText('1:1000')
            return
    
    def mcaAcceptPeak(self,num=0): #accecpt the fitting result, save the data, and update the mca integral plot 
        self.mcaSumScript=None   # the intensities no longer come from one Sum All
        if num>=len(self.selectedMcaScanNums) or not hasattr(self,'fitpeakpara') or not hasattr(self,'fiterror'):
            self.messageBox('Please select an MCA frame and fit its peak first!')
            return
        frame=self.selectedMcaScanNums[num]+1
        qz=self.mcaPar[self.selectedMcaScanNums[num]]['Q'][2]
        try:
            energy=self.mcaPar[self.selectedMcaScanNums[num]]['Energy']
        except:
            energy=10
       # print self.fitpeakpara
        inten=self.fitpeakpara[0][1]*self.fitpeakpara[0][2]
        error=np.sqrt(self.fitpeakpara[0][1]**2*self.fiterror[2]**2+self.fitpeakpara[0][2]**2*self.fiterror[1]**2)
       # print frame, qc, energy, inten, error
        self.mcaIntData.append([frame, qz, energy, inten, error])
        if self.ui.mcaXAxisComboBox.currentIndex()==0:
            string=str(int(frame))+'\t'+'%.4e'%inten+'\t'+'%.4e'%error 
        elif self.ui.mcaXAxisComboBox.currentIndex()==1:
            string='%.4f'%qz+'\t'+'%.4e'%inten+'\t'+'%.4e'%error
        else:
            string='%.4f'%energy+'\t'+'%.4e'%inten+'\t'+'%.4e'%error
        self.ui.mcaDataListWidget.addItem(string)
        self.updateMcaIntPlot()
        
    def updateMcaIntPlot(self):
        self.ui.mcaIntPlotMplWidget.canvas.ax.clear()
        self.ui.mcaIntPlotMplWidget.canvas.ax.set_ylabel('Integral Intensity')
        try:
            data=np.array(self.mcaIntData)
            y=data[:,3]
            yerr=data[:,4]
            if self.ui.mcaXAxisComboBox.currentIndex()==0:
                x=data[:,0]
                self.ui.mcaIntPlotMplWidget.canvas.ax.set_xlabel('Frame')
            elif self.ui.mcaXAxisComboBox.currentIndex()==1:
                x=data[:,1]
                self.ui.mcaIntPlotMplWidget.canvas.ax.set_xlabel(r'$Q_z$'+' '+r'$[\AA^{-1}]$')
            else:
                x=data[:,2]
                self.ui.mcaIntPlotMplWidget.canvas.ax.set_xlabel('Energy (keV)')
            self.ui.mcaIntPlotMplWidget.canvas.ax.errorbar(x,y,yerr,fmt='o',label='#0')
        except:
            self.messageBox('no mca integral data to process.')
        if len(self.selectedmcafiles_rows)!=0: #plot the loaded mca int data
            for i in range(len(self.selectedmcafiles_rows)):
                data1=np.loadtxt(str(self.mcafiles[self.selectedmcafiles_rows[i]]),comments='#')
                self.ui.mcaIntPlotMplWidget.canvas.ax.errorbar(data1[:,0],data1[:,1],data1[:,2],fmt='o',label='#'+str(self.selectedmcafiles_rows[i]+1))
        self.ui.mcaIntPlotMplWidget.canvas.ax.legend(loc=2,frameon=False,scatterpoints=0,numpoints=1)
        self.ui.mcaIntPlotMplWidget.canvas.draw()
    
    def updateMcaInt(self):
        try:
            self.ui.mcaDataListWidget.clear()
            for i in range(len(self.mcaIntData)):
                if self.ui.mcaXAxisComboBox.currentIndex()==0:
                    string=str(self.mcaIntData[i][0])+'\t'+'%.4e'%self.mcaIntData[i][3]+'\t'+'%.4e'%self.mcaIntData[i][4] 
                elif self.ui.mcaXAxisComboBox.currentIndex()==1:
                    string='%.4f'%self.mcaIntData[i][1]+'\t'+'%.4e'%self.mcaIntData[i][3]+'\t'+'%.4e'%self.mcaIntData[i][4]
                else:
                    string='%.4f'%self.mcaIntData[i][2]+'\t'+'%.4e'%self.mcaIntData[i][3]+'\t'+'%.4e'%self.mcaIntData[i][4]
                self.ui.mcaDataListWidget.addItem(string)
            self.updateMcaIntPlot()
        except:
            self.messageBox('no mca integral data to process.')
                
    def mcaIntMergeDia(self):
        Dialog=QDialog(self)
        self.uimcamerge=uic.loadUi(resource('mcamerge.ui'), Dialog)
        self.uimcamerge.label.setText('Merge window')
        x=['frame','qz','energy'][self.ui.mcaXAxisComboBox.currentIndex()]
        rows=getattr(self,'mcaIntData',None)
        default=fluorescence.default_merge_window(rows,x) if rows is not None and len(rows) else 0.0
        self.uimcamerge.resLineEdit.setText('%.6g' % default)
        self.uimcamerge.resLineEdit.setToolTip(
            'Points closer than this on the x axis are merged, as one longer measurement: weights y/sigma^2, which '
            'for counting errors is total counts over total monitor. Default on the Qz axis: 0.1 x the Qz grid step '
            '(%s), so only repeats of one target Qz merge (owner\'s XFNTR rule); on the frame and energy axes 0. '
            'On the Qz axis the Qz jitter, %.0e 1/A, is added to the error bars: sigma(I)/I = |d ln I/dQz| x jitter, '
            'which matters only within a step or two of the edge. Choose scans of one run, wavelength, sample and '
            'signal shape: the reader does not check.' % ('%.4g 1/A' % (default/0.1) if x=='qz' and default else
                                                           'not known', fluorescence.QZ_JITTER))
        self.uimcamerge.show()
        # self.connect(self.uimcamerge.cancelPushButton, SIGNAL('clicked()'), self.mcaMergeDiaClose)
        self.uimcamerge.cancelPushButton.clicked.connect(self.mcaMergeDiaClose)
        # self.connect(self.uimcamerge.okPushButton, SIGNAL('clicked()'), self.mcaIntMerge)
        self.uimcamerge.okPushButton.clicked.connect(self.mcaIntMerge)
            
    def mcaMergeDiaClose(self):
        self.uimcamerge.close()
        
    
    def mcaIntMerge(self):
        try:
            resolution=float(self.uimcamerge.resLineEdit.text())
            x=['frame','qz','energy'][self.ui.mcaXAxisComboBox.currentIndex()]
            self.mcaIntData=fluorescence.merge_rows(self.mcaIntData,x,resolution)
            if getattr(self,'mcaSumScript',None):
                self.mcaMerges=getattr(self,'mcaMerges',[])+[(resolution,x)]
            self.uimcamerge.close()
            self.updateMcaInt()
        except Exception:
            self.messageBox('no mca integral data to process.')

    def mcaDelIntData(self):
        self.mcaSumScript=None   # the intensities no longer come from one Sum All
        items=self.ui.mcaDataListWidget.selectedItems()
        self.mcaIntData=list(self.mcaIntData)
        for item in items:
            self.mcaIntData.pop(self.ui.mcaDataListWidget.row(item))
            self.ui.mcaDataListWidget.takeItem(self.ui.mcaDataListWidget.row(item))
        self.updateMcaIntPlot()
        
    def mcaSaveIntData(self):
        try:
            self.saveFileName=QFileDialog.getSaveFileName(caption='Save Fluorescence Integral Data',directory=self.directory)[0]
            if self.saveFileName=='':   # dialog cancelled: write nothing
                return
            fid=open(self.saveFileName+'_flu.txt','w')
            try:
                fid.write('#'+str(self.command)+'\n')
            except:
                pass
            for i in range(len(self.mcaIntData)):
                if self.ui.mcaXAxisComboBox.currentIndex()==0:
                    fid.write(str(self.mcaIntData[i][0])+'\t'+str(self.mcaIntData[i][3])+'\t'+str(self.mcaIntData[i][4])+'\n')
                elif self.ui.mcaXAxisComboBox.currentIndex()==1:
                    fid.write(str(self.mcaIntData[i][1])+'\t'+str(self.mcaIntData[i][3])+'\t'+str(self.mcaIntData[i][4])+'\n')
                else:
                    fid.write(str(self.mcaIntData[i][2])+'\t'+str(self.mcaIntData[i][3])+'\t'+str(self.mcaIntData[i][4])+'\n')
            fid.close()
            self.scriptLine(self.fluorescenceScript(self.saveFileName))
        except:
            print ('no mca integral data to save.')
                
    def fluorescenceScript(self,name):
        """The lss_core call for the last fluorescence export, when there is one."""
        if not getattr(self,'mcaSumScript',None):
            return '# these intensities came from peak fits or were edited; not scriptable yet'
        scans,lo,hi,complete=self.mcaSumScript
        if not complete:
            return '# only some spectra were selected; not scriptable yet'
        kw=['window=(%r, %r)' % (lo,hi)]
        mon=str(self.ui.mcaNormComboBox.currentText())
        if mon!='Monc':
            kw.append('monitor=%r' % (None if mon=='None' else mon))
        if self.ui.mcaCalibCheckBox.checkState()==0:
            kw.append('calibration=(%r, %r, %r)' % (float(self.ui.mcaCalibConLineEdit.text()),float(self.ui.mcaCalibLinLineEdit.text()),float(self.ui.mcaCalibQuaLineEdit.text())))
        if script_kw(self.errorModel):
            kw.append(script_kw(self.errorModel))
        if mon!='None' and getattr(self,'mcaAbsfacUsed',ABSFAC_10KEV)!=ABSFAC_10KEV and any(
                self.mcaAbsorber.get(i) for i in self.selectedMcaScanNums):
            kw.append('absfac=%r' % self.mcaAbsfacUsed)
        if getattr(self,'mcaGainUsed',False):
            kw.append('per_photon=True' if self.mcaGainUsed=='photons' else 'monitor_gain=True')
        if self.mcaChannels() and any('Channels' in self.mcaPar[i] for i in self.selectedMcaScanNums):
            kw.append('channels=%r' % self.mcaChannels())
        x=['frame','qz','energy'][self.ui.mcaXAxisComboBox.currentIndex()]
        head='from lss_core import absorbers\n' if isinstance(getattr(self,'mcaAbsfacUsed',None),absorbers.Foils) else ''
        merges=''.join('flu.merge(%r, x=%r)\n' % m for m in getattr(self,'mcaMerges',[]))
        return head+'flu = exp.fluorescence(%r, %s)\n%sflu.save(%r, x=%r)' % (scans,', '.join(kw),merges,name,x)

    def addMcaFiles(self): #add mca files with integral intensity in the list
        f=QFileDialog.getOpenFileNames(caption='Select Multiple Files to import', directory=self.directory)[0]
        self.mcafiles=self.mcafiles+list(map(str, f))
        self.mcafnames=[]
        self.ui.mcaFileListWidget.clear()
        for i in range(len(self.mcafiles)):
            s=str(self.mcafiles[i])
            self.mcafnames.append(s[s.rfind('/')+1:])
            self.ui.mcaFileListWidget.addItem('#'+str(i+1)+'\t'+self.mcafnames[i])

    def removeMcaFiles(self):
        items=self.ui.mcaFileListWidget.selectedItems()
        for item in items:
            self.mcafnames.pop(self.ui.mcaFileListWidget.row(item))
            self.mcafiles.pop(self.ui.mcaFileListWidget.row(item))
        self.ui.mcaFileListWidget.clear()
        for i in range(len(self.mcafnames)):
            self.ui.mcaFileListWidget.addItem('#'+str(i+1)+'\t'+self.mcafnames[i])    
    
    def updateSelectedMcaFiles(self):
        selectedmcafiles=self.ui.mcaFileListWidget.selectedItems()
        self.selectedmcafiles_rows=[]
        for item in selectedmcafiles:
            self.selectedmcafiles_rows.append(self.ui.mcaFileListWidget.row(item))
        self.updateMcaIntPlot()

    def initMessagePane(self):
        """A dock at the bottom of the window that collects messages.

        Messages used to be modal dialogs that had to be clicked away. They
        are now appended here, written to the log, and the pane is raised;
        nothing blocks.
        """
        self.messages=[]   # (time string, title, text) of everything shown
        self.messageDock=QDockWidget('Messages',self)
        self.messageDock.setObjectName('messageDock')
        self.messageDock.setAllowedAreas(Qt.BottomDockWidgetArea|Qt.TopDockWidgetArea)
        self.messageView=QPlainTextEdit(self.messageDock)
        self.messageView.setObjectName('messageView')
        self.messageView.setReadOnly(True)
        self.messageView.setMaximumBlockCount(2000)
        self.messageView.setMinimumHeight(60)
        self.messageDock.setWidget(self.messageView)
        self.addDockWidget(Qt.BottomDockWidgetArea,self.messageDock)
        self.messageDock.hide()   # appears with the first message

    def initScriptPane(self):
        """A dock showing, for actions that have one, the Python that does the
        same thing with lss_core (docs/SCRIPTING.md), ready to copy (F48)."""
        self.scriptDock=QDockWidget('Script',self)
        self.scriptDock.setObjectName('scriptDock')
        self.scriptView=QPlainTextEdit(self.scriptDock)
        self.scriptView.setObjectName('scriptView')
        self.scriptView.setReadOnly(True)
        self.scriptView.setPlainText('from lss_core.experiment import Experiment\n')
        self.scriptDock.setWidget(self.scriptView)
        self.addDockWidget(Qt.BottomDockWidgetArea,self.scriptDock)
        self.tabifyDockWidget(self.messageDock,self.scriptDock)
        self.scriptDock.hide()   # View it from the dock area's context menu, or it appears with the first line

    def initErrorPane(self):
        """A dock with the error model (lss_core.errors). 'Legacy' gives the
        numbers the program always gave; 'Budget' applies the monitor's
        uncertainty once to each whole sum. The monitor model: a Gaussian of
        fixed relative sigma (default 0.04 %, owner 2026-11-17), a Student t,
        or the counting form f^2 + (dark/M)^2 + 1/(g M)."""
        self.errorModel=ErrorModel('legacy')
        self.pilatus.errors=self.errorModel
        self.errorDock=QDockWidget('Errors',self)
        self.errorDock.setObjectName('errorDock')
        w=QWidget(self.errorDock)
        form=QFormLayout(w)
        self.errorModeComboBox=QComboBox(w)
        self.errorModeComboBox.setObjectName('errorModeComboBox')
        self.errorModeComboBox.addItems(['Legacy','Budget'])
        self.errorModeComboBox.setToolTip('Legacy: per-pixel monitor term summed in quadrature (as before).\n'
                                          'Budget: the monitor term is applied once to each whole sum.')
        form.addRow('Error model',self.errorModeComboBox)
        self.monitorKindComboBox=QComboBox(w)
        self.monitorKindComboBox.setObjectName('monitorKindComboBox')
        self.monitorKindComboBox.addItems(['Gaussian','Student t','Counting'])
        self.monitorKindComboBox.setToolTip('Gaussian and Student t values describe the present Monc electronics '
                                            '('+ELECTRONICS+'); re-measure them if the electronics change.')
        form.addRow('Monitor model',self.monitorKindComboBox)
        m=self.errorModel.monitor
        self.errorFields={}
        self.errorFieldLabels={}
        for name,label,value,tip in (
                ('sigma','Monitor sigma (%)',100*m.sigma,'relative standard deviation of one Monc reading, in percent'),
                ('sigma_scan','Scan scatter (%)',100*m.sigma_scan,"the scan's own relative Monc scatter, in percent\n"
                                                                  '(0.039 when unknown)'),
                ('width','t width',m.width,'scale of the Student t = width x scan scatter\n'
                                           '(about 0.94; 0.86 to 1.01 across data sets)'),
                ('nu','t nu',m.nu,'degrees of freedom of the Student t (> 2; about 4)'),
                ('f','Floor f',m.f,'fractional monitor uncertainty that does not fall with counts'),
                ('sigma_dark','Dark sigma',m.sigma_dark,'scatter of the monitor dark counts in one frame (counts)'),
                ('g','Quanta per count g',m.g,'true quanta per recorded monitor count (1: Poisson on the counts)')):
            e=QLineEdit(repr(value),w)
            e.setObjectName('errorModel_'+name)
            e.setToolTip(tip)
            e.setValidator(QDoubleValidator(0.0,1e12,12,e))
            e.editingFinished.connect(self.setErrorModel)
            self.errorFields[name]=e
            lab=QLabel(label,w)
            self.errorFieldLabels[name]=lab
            form.addRow(lab,e)
        self.errorModelLabel=QLabel(w)
        self.errorModelLabel.setObjectName('errorModelLabel')
        self.errorModelLabel.setWordWrap(True)
        form.addRow(self.errorModelLabel)
        self.errorModeComboBox.currentIndexChanged.connect(self.setErrorModel)
        self.monitorKindComboBox.currentIndexChanged.connect(self.setErrorModel)
        self.errorDock.setWidget(w)
        self.addDockWidget(Qt.BottomDockWidgetArea,self.errorDock)
        self.tabifyDockWidget(self.messageDock,self.errorDock)
        self.errorDock.hide()
        view=self.ui.menuBar.addMenu('View')
        view.setObjectName('menuView')
        for dock in (self.messageDock,self.scriptDock,self.errorDock):
            view.addAction(dock.toggleViewAction())
        self.showErrorModel()

    def showErrorModel(self):
        """Enable the fields the chosen monitor model uses; describe the model."""
        kind=('gaussian','student_t','counting')[self.monitorKindComboBox.currentIndex()]
        used={'gaussian':('sigma',),'student_t':('sigma_scan','width','nu'),'counting':('f','sigma_dark','g')}[kind]
        for name,e in self.errorFields.items():
            e.setEnabled(name in used)
            self.errorFieldLabels[name].setEnabled(name in used)
        text=self.errorModel.describe()
        if not self.errorModel.budget:
            text+='. The monitor model below is used when Budget is chosen.'
        self.errorModelLabel.setText(text)

    def setErrorModel(self):
        """Read the Errors pane into self.errorModel; applies to what is
        computed from now on (what is on show is recomputed where cheap)."""
        defaults=MonitorModel()
        vals={}
        for name,e in self.errorFields.items():
            try:
                vals[name]=float(e.text())
            except ValueError:
                vals[name]=getattr(defaults,name)*(100 if name in ('sigma','sigma_scan') else 1)
                e.setText(repr(vals[name]))
        vals['sigma']=vals['sigma']/100.0
        vals['sigma_scan']=vals['sigma_scan']/100.0
        if vals['g']<=0:
            vals['g']=defaults.g
            self.errorFields['g'].setText(repr(defaults.g))
        if vals['nu']<=2:
            vals['nu']=defaults.nu
            self.errorFields['nu'].setText(repr(defaults.nu))
            self.notify('A Student t needs nu > 2 for a finite variance; nu was reset to %g.' % defaults.nu,
                        title='Errors',level='info')
        vals['kind']=('gaussian','student_t','counting')[self.monitorKindComboBox.currentIndex()]
        mode='budget' if self.errorModeComboBox.currentIndex()==1 else 'legacy'
        new=ErrorModel(mode,MonitorModel(**vals))
        if new==self.errorModel:
            self.showErrorModel()
            return
        self.errorModel=new
        self.pilatus.errors=new
        self.showErrorModel()
        self.notify('Error model: '+new.describe()+'. Spectra and background-subtracted images on show are '
                    'recomputed; other results apply it the next time they are computed.',
                    title='Errors',level='info')
        # what is on show was normalised under the old model: redo it
        if len(self.selectedMcaScanNums)>0 and getattr(self,'mcaData',None):
            self.updateMcaPlotData()
        if self.det=='Pilatus' and len(self.selectedPilFramesNums)>0 and len(self.ui.backgroundListWidget.selectedItems())>0:
            self.pilSelectedScanChanged()

    def noteMixedAbsorbers(self,absnums,what):
        """Frames taken at different absorber settings are being combined on
        the nominal factor absfac**n, which is not measured (Ref Patch measures
        the scale instead; owner, 2026-11-17). Monc is upstream of the
        absorbers (owner), so it does not see them. Say so, once per
        combination."""
        n=sorted(set(int(a) for a in absnums))
        if len(n)<2:
            return
        key=(what,tuple(n),repr(self.absfac))
        seen=self.__dict__.setdefault('_absorberNotes',set())
        if key in seen:
            return
        seen.add(key)
        if isinstance(self.absfac,absorbers.Foils):
            self.notify('%s combines frames taken at absorber settings %s (SPEC #A), scaled by the calibrated foils '
                        '(File > Preferences).' % (what,', '.join(map(str,n))),title='Absorbers',level='info')
            return
        self.notify('%s combines frames taken at absorber settings %s (SPEC #A), scaled by the nominal factor %g '
                    'per unit; Monc is upstream of the absorbers, so only this unmeasured factor puts them on one '
                    'scale.' % (what,', '.join(map(str,n)),self.absfac),title='Absorbers',level='info')

    def scriptLine(self,text):
        """Append Python to the Script pane and the log."""
        self.log.info('script: %s',text.replace('\n',' | '))
        try:
            self.scriptView.appendPlainText(text)
            self.scriptDock.show()
        except RuntimeError:
            pass

    def notify(self,text,title='Warning',level='warning'):
        """Tell the user something without stopping them, and log it."""
        text=str(text)
        stamp=time.strftime('%H:%M:%S')
        self.messages.append((stamp,title,text))
        getattr(self.log,level,self.log.warning)('%s: %s',title,text.replace('\n',' | '))
        try:
            self.messageView.appendPlainText(stamp+'  '+text.replace('\n','\n          '))
            self.messageDock.show()
        except RuntimeError:   # window already being destroyed
            pass

    def reportFailure(self,text):
        """Called by the process-wide exception handler (reader_log)."""
        self.notify(text,title='Error',level='info')   # the traceback is logged separately
        try:
            self.ui.statusBar.showMessage(text.split('. Details')[0])
        except RuntimeError:
            pass

    def sessionContext(self):
        """What was loaded and selected; added to every logged exception."""
        def short(name):
            value=getattr(self,name,None)
            if value is None:
                return None
            try:
                value=[int(v) for v in value]
            except (TypeError,ValueError):
                pass
            text=str(value)
            return text if len(text)<200 else text[:200]+'...'
        return {'SPEC file':self.specFileName,
                'beamline':getattr(self,'beamline',None),
                'detector':getattr(self,'det',None),
                'tab':self.ui.PlotWidget.tabText(self.ui.PlotWidget.currentIndex()),
                'selected scans':short('selectedScanNums'),
                'selected frames':short('selectedPilFramesNums'),
                'selected spectra':short('selectedMcaScanNums')}

    def messageBox(self,text,title='Warning'):
        if title=='About':   # the one message that is a deliberate dialog
            mesgbox=QMessageBox(self)
            mesgbox.setText(text)
            mesgbox.setWindowTitle(title)
            mesgbox.exec_()
            return
        self.notify(text,title)
    
    def updateProgress(self):
        self.progressDialog.setValue(self.progressDialog.value()+1)
        
    def selectAllImages(self):
        if self.ui.imageSelectAllCheckBox.checkState()!=0:
            # self.disconnect(self.ui.imageListWidget,SIGNAL('itemSelectionChanged()'),self.imageSelectedScanChanged)
            self.ui.imageListWidget.itemSelectionChanged.disconnect(self.imageSelectedScanChanged)
            for i in range(self.ui.imageListWidget.count()):
                self.ui.imageListWidget.item(i).setSelected(True)#setItemSelected(self.ui.imageListWidget.item(i),True)
            # self.connect(self.ui.imageListWidget,SIGNAL('itemSelectionChanged()'),self.imageSelectedScanChanged)
            self.ui.imageListWidget.itemSelectionChanged.connect(self.imageSelectedScanChanged)
            self.imageSelectedScanChanged()
        else:
            self.unSelectedAllImages()
                
    def unSelectedAllImages(self):
        if self.ui.imageSelectAllCheckBox.checkState()!=0 and self.specPar[self.selectedScanNums[0]]['Detector']=='Pilatus':
            # self.disconnect(self.ui.imageListWidget,SIGNAL('itemSelectionChanged()'),self.imageSelectedScanChanged)
            self.ui.imageListWidget.itemSelectionChanged.disconnect(self.imageSelectedScanChanged)
            for items in self.selectedPilFrames:
                items.setSelected(False)
            # self.connect(self.ui.imageListWidget,SIGNAL('itemSelectionChanged()'),self.imageSelectedScanChanged)
            self.ui.imageListWidget.itemSelectionChanged.connect(self.imageSelectedScanChanged)
            self.ui.imageSelectAllCheckBox.setCheckState(0)
        elif self.ui.imageSelectAllCheckBox.checkState()!=0 and self.specPar[self.selectedScanNums[0]]['Detector']=='Vortex':
            self.ui.imageSelectAllCheckBox.setCheckState(0)
        self.ui.gixSumCheckBox.setCheckState(0)


    def imageSelectedScanChanged(self):
        # Clicks in the image list arrive in quick succession when the user
        # drags, shift-clicks or scrolls with the keyboard. Each one used to
        # redraw every selected frame; now a change from the list waits a
        # moment and only the last one is drawn.
        delay=selectionDelayMs()
        if delay>0 and self.sender() is self.ui.imageListWidget:
            if not hasattr(self,'imageSelectionTimer'):
                self.imageSelectionTimer=QTimer(self)
                self.imageSelectionTimer.setSingleShot(True)
                self.imageSelectionTimer.timeout.connect(self.imageSelectionNow)
            self.imageSelectionTimer.start(delay)
            return
        self.imageSelectionNow()

    def flushPendingSelection(self):
        """Process a delayed image-list selection now (used by tests and
        before any action that reads the selection)."""
        timer=getattr(self,'imageSelectionTimer',None)
        if timer is not None and timer.isActive():
            timer.stop()
            self.imageSelectionNow()

    def imageSelectionNow(self):
        if len(self.selectedScanNums)==0:   # no scan selected: nothing to read
            return
        #self.ui.imageSelectAllCheckBox.setCheckState(0)
        self.pilGIDshow=0
        self.pilGISAXSshow=0
        self.ui.statusBar.showMessage('Plotting....Wait!!')
        if  self.specPar[self.selectedScanNums[0]]['Detector']=='Vortex':
            self.mcaSelectedScanChanged()
            self.ui.statusBar.showMessage('Done')
        elif self.specPar[self.selectedScanNums[0]]['Detector']=='Pilatus':
            self.det='Pilatus'
            self.pilSelectedScanChanged()
            self.ui.statusBar.showMessage('Done')
 
        
    def updatePilImageList(self):
        # self.disconnect(self.ui.imageListWidget,SIGNAL('itemSelectionChanged()'),self.imageSelectedScanChanged)
        self.ui.imageListWidget.itemSelectionChanged.disconnect(self.imageSelectedScanChanged)
        self.ui.statusBar.clearMessage()
        self.numFrames={}
        self.pilFileNames=[]
        self.pilFileQzs=[]
        self.pilMonc=np.array([])
        self.pilX=[]
        self.pilY=[]
        self.pil_Dist=[]
        self.pil_PDist=[]
        self.pilAlpha=[]
        self.pilTrueAlpha=[]
        self.pil_Sh=[]
        self.pil_Wavelength=[]
        self.pil_Tth=[]
        self.pil_Chi=[]
        self.pil_Gl2=[]
        self.pil_AbsNum=[]
        self.pil_Phi=[]
        self.pil_Dth=[]
        self.pilX_off=[]
        self.pilY_off=[]
        self.pilFileQxs=[]
        self.pilFileQys=[]
        self.pilScanNum=[]
        self.pilFrameNum=[]
        self.pil_S1v=[]
        self.pil_S1h=[]
        self.pil_S4h=[]
        self.pil_S5h=[]
        self.selectedScanNums.sort()
        for i in self.selectedScanNums:
            #self.ui.scanListWidget.setItemSelected(self.ui.scanListWidget.item(i),True)
            try:
                self.numFrames[i]=len(self.specData[i][self.specData[i]['ScanVar'][0]])  #get frame number for each scan
            except:
                #self.ui.imageListWidget.itemSelectionChanged.connect(self.imageSelectedScanChanged)
                self.messageBox('Warning: scan ' + str(i)+ ' has no data!')
                break
            try:
                scanmonc=self.specData[i]['Monc']
            except KeyError:
                scanmonc=self.specData[i]['monc']
            fname=self.pilfhead+str(i)+'_'
            # frame number -> image file, read from the file name, so that a
            # missing image cannot shift every later frame onto the wrong file
            files={}
            for path in glob.glob(str(fname+'*')):
                try:
                    files[int(path.split('_')[-1].split('.')[0])]=path
                except ValueError:
                    pass
            missing=[]
            for j in range(self.numFrames[i]):
                if j not in files:
                    missing.append(j)
                    continue
                filelist={j:files[j]}
                before={name:len(getattr(self,name)) for name in FRAMELISTS}
                rows=self.ui.imageListWidget.count()
                try:
                    self.pilFileNames.append(filelist[j])
                    fnum=filelist[j].split('_')[-1].split('.')[0].lstrip('0')
                    if fnum=='':
                        fnum='0'
                    absn=self.specPar[i].get('Absorber')
                    self.ui.imageListWidget.addItem('S# '+str(i)+'\tF# '+fnum+'\tQz='+'%.4f'%self.specData[i]['L'][j]+'\tQx='+'%.4f'%self.specData[i]['H'][j]+('\tAbs=?' if absn is None else '\tAbs=%d'%absn))
                    self.pilMonc=np.append(self.pilMonc, scanmonc[j])
                    self.pilScanNum.append(i)  
                    self.pilFrameNum.append(j)
                    self.pilFileQzs.append(self.specData[i]['L'][j])
                    self.pilFileQxs.append(self.specData[i]['H'][j])
                    self.pilFileQys.append(self.specData[i]['K'][j])
                    self.pilAlpha.append(np.arcsin(self.pilFileQzs[-1]*self.specPar[i]['Wavelength']/4.0/np.pi))
                    self.pilTrueAlpha.append(self.specPar[i]['In_Rot']*np.pi/180.0)
                    self.pilX.append(self.specPar[i]['DBPos'][1])
                    self.pil_Wavelength.append(self.specPar[i]['Wavelength'])
                    self.pilY.append(self.specPar[i]['DBPos'][0])
                    self.pil_Dist.append(self.specPar[i]['S2D_Dist'])
                    self.pil_PDist.append(self.specPar[i]['S7D_Dist'])
                    self.pil_Sh.append(self.specPar[i]['Sample_H'])
                    self.pil_S1v.append(self.specPar[i]['S1T']+self.specPar[i]['S1B'])   # top + bottom (was S1T + S1T, defect 10)
                    self.pil_S1h.append(self.specPar[i]['S1L']+self.specPar[i]['S1R'])
                    self.pil_S4h.append(self.specPar[i]['S4L']+self.specPar[i]['S4R'])
                    self.pil_S5h.append(self.specPar[i]['S5L']+self.specPar[i]['S5R'])
                    try:
                        self.pil_Dth.append(self.specData[i]['Det_Th'][j]*np.pi/180.0)
                    except:
                        self.pil_Dth.append(2.0*np.arcsin(np.sqrt(self.pilFileQxs[-1]**2+self.pilFileQys[-1]**2)*self.specPar[i]['Wavelength']/4.0/np.pi))
                    self.pil_Tth.append(self.specPar[i]['Two_Thet'])
                    self.pil_Chi.append(self.specPar[i]['Chi'])
                    self.pil_Gl2.append(self.specPar[i]['g_l2'])
                    self.pil_AbsNum.append(absorber_setting(self.specPar[i]))   # unknown: 0, no factor
                    self.pil_Phi.append(self.specPar[i]['Phi'])
                except Exception:
                    # a frame whose header values cannot be read is left out
                    # entirely, so every per-frame list stays aligned with the image list
                    for name,n in before.items():
                        del getattr(self,name)[n:]
                    self.pilMonc=self.pilMonc[:before['pilFileNames']]
                    while self.ui.imageListWidget.count()>rows:
                        self.ui.imageListWidget.takeItem(self.ui.imageListWidget.count()-1)
                    self.log.exception('scan %s frame %d could not be listed',i,j)
                    missing.append(j)
            if self.specPar[i].get('Absorber') is None and (self.specFileName,i) not in self.absorberUnknownNoted:
                self.absorberUnknownNoted.add((self.specFileName,i))
                self.notify('Scan %d: absorber setting unknown (%s); no absorber factor on its frames, the patch '
                            'scales them as usual.' % (i,'"#A %s"' % self.specPar[i]['AbsorberText']
                                                         if 'AbsorberText' in self.specPar[i] else 'no #A'),
                            title='Absorbers',level='warning')
            if len(missing)>0:
                self.messageBox('Scan '+str(i)+': '+str(len(missing))+' of '+str(self.numFrames[i])+' frames have no readable image ('+listText(missing[:10])+('...' if len(missing)>10 else '')+').')
#            except:
#                self.messageBox('Warning:: #S '+str(i+1)+' has been canceled or no data found.')
        self.pilData={}
        self.pilLogData={}
        self.pilErrorData={}
        self.pilGIOXSData={}
        self.pilGIOXSErrorData={}
        # self.connect(self.ui.imageListWidget,SIGNAL('itemSelectionChanged()'),self.imageSelectedScanChanged)
        self.ui.imageListWidget.itemSelectionChanged.connect(self.imageSelectedScanChanged)

    def pilSelectedScanChanged(self):
        self.pilmovieindex=0
        #        self.disconnect=(self.ui.gidComboBox, SIGNAL('currentIndexChanged(int)'), self.pilGID)
#        self.ui.gidComboBox.setCurrentIndex(0)
#        self.connect=(self.ui.gidComboBox, SIGNAL('currentIndexChanged(int)'), self.pilGID)
        bad_pix = int(self.ui.pilBPCiteSpinBox.value())
        bad_fac = int(self.ui.pilBPCfacSpinBox.value())
        self.ui.statusBar.clearMessage()
        self.selectedPilFrames=self.ui.imageListWidget.selectedItems()
        self.selectedPilFramesNums=np.sort([self.ui.imageListWidget.row(items) for items in self.selectedPilFrames])
        self.pilSelectedScanNum=[self.pilScanNum[i] for i in self.selectedPilFramesNums]
        self.pilSelectedQzs=[self.pilFileQzs[i] for i in self.selectedPilFramesNums]
        self.pilSelectedMonc=[self.pilMonc[i] for i in self.selectedPilFramesNums]
        self.pilSelectedX=[self.pilX[i] for i in self.selectedPilFramesNums]   #this is the direct beam x pixel
        self.pilSelectedY=[self.pilY[i] for i in self.selectedPilFramesNums]   # this is the direct beam y pixel
        self.pilSelected_Dist=[self.pil_Dist[i] for i in self.selectedPilFramesNums]   # this is the distance btw sample and Pilatus
        self.pilSelected_PDist=[self.pil_PDist[i] for i in self.selectedPilFramesNums] # this is the distance between the two slits before the detector. Useful only for pinhole kind of setup
        self.pilSelected_Sh=[-self.pil_Gl2[i]*np.tan(self.pilAlpha[i]) for i in self.selectedPilFramesNums]
        self.pilSelected_Alpha=[self.pilAlpha[i] for i in self.selectedPilFramesNums]
        self.pilSelected_TrueAlpha=[self.pilTrueAlpha[i] for i in self.selectedPilFramesNums]
        self.pilSelected_Wavelength=[self.pil_Wavelength[i] for i in self.selectedPilFramesNums]
        self.pilSelected_Dth=[self.pil_Dth[i] for i in self.selectedPilFramesNums]
        self.pilSelected_Tth=[self.pil_Tth[i] for i in self.selectedPilFramesNums]
        self.pilSelected_Chi=[self.pil_Chi[i] for i in self.selectedPilFramesNums]
        self.pilSelected_Gl2=[self.pil_Gl2[i] for i in self.selectedPilFramesNums]
        self.pilSelected_AbsNum=[self.pil_AbsNum[i] for i in self.selectedPilFramesNums]
        self.pilSelected_Phi=[self.pil_Phi[i] for i in self.selectedPilFramesNums]
        fac=float(self.ui.bgFacLineEdit.text())
        j=0
        self.progressDialog=QProgressDialog('Reading Pilatus Images','Abort',0,100)
        self.progressDialog.setWindowModality(Qt.WindowModal)
        self.progressDialog.setWindowTitle('Wait')
        self.progressDialog.setAutoClose(True)
        self.progressDialog.setAutoReset(True)
        self.progressDialog.setMinimum(1)
        self.progressDialog.setMaximum(len(self.selectedPilFramesNums))
        self.progressDialog.show()
        self.pilbadpixLoc = {}
        self.pilMonitorTerms = {}   # budget error model: monitor parts of background-subtracted frames
        for i in self.selectedPilFramesNums:
            if len(self.ui.backgroundListWidget.selectedItems())==0:
                self.pilatus.openFile(self.pilFileNames[i],bad_pix=bad_pix,bad_fac=bad_fac)
                self.pilData[i]=self.pilatus.imageData
                self.pilLogData[i]=np.log10(self.pilData[i]+1)
                self.pilErrorData[i]=self.pilatus.errorData
                self.xyzformat='x=%.3f,y=%.3f,z=%.2e'
                self.pilbadpixLoc[i] = self.pilatus.imbadPix
            else:
                self.pilatus.openFile(self.pilFileNames[i],bad_pix=bad_pix,bad_fac=bad_fac)
                self.pilData[i]=self.pilatus.imageData
                self.pilErrorData[i]=self.pilatus.errorData
                self.pilatus.sumFiles({i:self.pilData[i]},{i:self.pilErrorData[i]},absfac=self.absfac,absnum=[self.pilSelected_AbsNum[j]],mon=[self.pilSelectedMonc[j]],gain=self.pilGains([self.pilSelectedScanNum[j]])) # For the Normalization Calculation Only!!
                self.pilGIOXSData[i]=self.pilatus.imageData   #for GIOXS data, bg substraction has to be done in 1D format. So keep it without bg image substraction
                self.pilGIOXSErrorData[i]=self.pilatus.errorData
                if self.errorModel.budget:
                    terms=MonitorTerms()
                    terms.extend(self.pilatus.monitorTerms)
                    terms.extend(getattr(self,'bgMonitorTerms',MonitorTerms()),-fac)
                    self.pilMonitorTerms[i]=terms
                self.pilData[i]=self.pilatus.imageData-fac*self.bgData
                if self.ui.bgIgnoreNegCheckBox.checkState()!=0:
                    self.pilData[i]=np.where(self.pilData[i]<0,0,self.pilData[i])
                self.pilLogData[i]=np.log10(np.where(self.pilData[i]<=0,1e-10,self.pilData[i]))
                self.pilErrorData[i]=np.sqrt(self.pilatus.errorData**2+fac**2*self.bgError**2)
                j=j+1
                self.xyzformat='x=%.3f,y=%.3f,z=%.2e'
            self.progressDialog.setLabelText('Reading Pilatus Frame #'+str(i))     
            self.updateProgress()
            if self.progressDialog.wasCanceled()==True:
                break
        self.progressDialog.close()
        self.pilFrameNumsWithSameQz={}
        self.pilFrameAbsWithSameQz={} 
        for i in self.selectedPilFramesNums:
            if float(format(self.pilFileQzs[i],'.4f')) in self.pilFrameNumsWithSameQz:                
                self.pilFrameNumsWithSameQz[float(format(self.pilFileQzs[i],'.4f'))].append(i)
                self.pilFrameAbsWithSameQz[float(format(self.pilFileQzs[i],'.4f'))].append(self.pil_AbsNum[i])
            else:
                self.pilFrameNumsWithSameQz[float(format(self.pilFileQzs[i],'.4f'))]=[i]
                self.pilFrameAbsWithSameQz[float(format(self.pilFileQzs[i],'.4f'))]=[self.pil_AbsNum[i]]
        try:
            # the range of what is drawn: the first frame per Monc (owner, 2026-11-23); a range
            # below 1 is normal now, so only a frame without any positive value falls back to 1
            first=self.pilFrameNormalised(self.selectedPilFramesNums[0])[0]
            self.imageMax=np.max(first)
            if not self.imageMax>0:
                self.imageMax=1
            self.imageMin=np.min(first[np.nonzero(first)])
        except:
            self.imageMax=100
            self.imageMin=0
        self.ui.pilMaxLineEdit.setText(str(self.imageMax))
        self.ui.pilMinLineEdit.setText(str(self.imageMin))
        self.ui.pilMinHorizontalSlider.setRange(0, 100)
        self.ui.pilMaxHorizontalSlider.setRange(0, 100)
        self.ui.pilMinHorizontalSlider.setValue(0)
        self.ui.pilMaxHorizontalSlider.setValue(100)
#        try:
        self.ui.PlotWidget.setCurrentIndex(2)
        self.updatePilPlotData()
#        except:
#            self.messageBox('Warning:: Some scans maybe missing')
            
    def updatePilMaxSlider(self):
        self.ui.pilMaxLineEdit.setText(str(self.ui.pilMaxHorizontalSlider.value()*(self.imageMax-self.imageMin)/100.0))
        self.ui.pilMinHorizontalSlider.setMaximum(int(float(self.ui.pilMaxLineEdit.text())*100.0/(self.imageMax-self.imageMin)))
        self.updatePilPlotData()
        
    def updatePilMinSlider(self):
        self.ui.pilMinLineEdit.setText(str(self.ui.pilMinHorizontalSlider.value()*(self.imageMax-self.imageMin)/100.0))
        self.updatePilPlotData()
        
    def addBGImagestoList(self):
        if self.det is None or len(self.ui.imageListWidget.selectedItems())==0:
            self.messageBox('Please select the background images in the image list first!')
            return
        self.ui.backgroundListWidget.clear()
        for item in self.ui.imageListWidget.selectedItems():
            self.ui.backgroundListWidget.addItem(item.text())
        self.bgpilData={}
        self.bgpilErrorData={}
        self.bgMonc={}
        self.bgAbsNum={}
        self.bgScanNum={}
        self.bgWavelength={}
        self.bgDist={}
        self.bgAlpha={}
        self.bgTrueAlpha={}
        j=0
        if self.det=='Pilatus':
            for i in self.selectedPilFramesNums:
                self.bgpilData[j]=self.pilData[i]
                self.bgpilErrorData[j]=self.pilErrorData[i]
                self.bgMonc[j]=self.pilSelectedMonc[j]
                self.bgWavelength[j]=self.pilSelected_Wavelength[j]
                self.bgDist[j]=self.pilSelected_Dist[j]
                self.bgAlpha[j]=self.pilSelected_Alpha[j]
                self.bgTrueAlpha[j]=self.pilSelected_TrueAlpha[j]
                self.bgAbsNum[j]=self.pilSelected_AbsNum[j]
                self.bgScanNum[j]=self.pilSelectedScanNum[j]
                j=j+1
            
    def bgSelectAll(self):
        try:
            self.ui.backgroundListWidget.itemSelectionChanged.disconnect(self.bgSelectionChanged)
        except:
            pass
        #self.disconnect(self.ui.backgroundListWidget, SIGNAL('itemSelectionChanged()'),self.bgSelectionChanged)
        if self.ui.bgSelectAllCheckBox.checkState()!=0:
            for i in range(self.ui.backgroundListWidget.count()):
                self.ui.backgroundListWidget.item(i).setSelected(True)#.setItemSelected(self.ui.backgroundListWidget.item(i),True)
        else:
            for i in range(self.ui.backgroundListWidget.count()):
                self.ui.backgroundListWidget.item(i).setSelected(False)#setItemSelected(self.ui.backgroundListWidget.item(i),False)
        self.ui.backgroundListWidget.itemSelectionChanged.connect(self.bgSelectionChanged)
        self.bgSelectionChanged()
        
            
    def bgSelectionChanged(self):
        if self.det is None:   # no images loaded: nothing to select from
            return
        self.selectedBgFrameNums=[self.ui.backgroundListWidget.row(item) for item in self.ui.backgroundListWidget.selectedItems()]
        #print self.selectedBgFrameNums
        self.selectedBgData={}
        self.selectedBgError={}
        self.selectedBgAbsNum=[]
        self.selectedBgScanNum=[]
        self.selectedBgMonc=[]
        self.selectedBgWavelength=[]
        self.selectedBgDist=[]
        self.selectedBgAlpha=[]
        self.selectedBgTrueAlpha=[]
        
        if self.det=='Pilatus':
            for i in self.selectedBgFrameNums:
                self.selectedBgData[i]=self.bgpilData[i]
                self.selectedBgError[i]=self.bgpilErrorData[i]
                self.selectedBgMonc.append(self.bgMonc[i])
                self.selectedBgWavelength.append(self.bgWavelength[i])
                self.selectedBgDist.append(self.bgDist[i])
                self.selectedBgAlpha.append(self.bgAlpha[i])
                self.selectedBgTrueAlpha.append(self.bgTrueAlpha[i])
                self.selectedBgAbsNum.append(self.bgAbsNum[i])
                self.selectedBgScanNum.append(self.bgScanNum[i])
            if len(self.selectedBgFrameNums)>0:   # nothing selected: no background to form
                self.noteMixedAbsorbers(self.selectedBgAbsNum,'The background image')
                self.pilatus.sumFiles(self.selectedBgData,self.selectedBgError,absfac=self.absfac,absnum=self.selectedBgAbsNum,mon=self.selectedBgMonc,tag='bg',gain=self.pilGains(self.selectedBgScanNum))
                self.bgData=self.pilatus.imageData
                self.bgError=self.pilatus.errorData
                self.bgMonitorTerms=self.pilatus.monitorTerms
        if self.det=='Pilatus' and len(self.selectedPilFramesNums)>0:
            self.pilSelectedScanChanged()
#        if len(self.ui.backgroundListWidget.selectedItems())>0:
#            self.ui.gixSumCheckBox.setCheckState(2)
        
        
    def removeBGImages(self):
        # self.disconnect(self.ui.backgroundListWidget, SIGNAL('itemSelectionChanged()'),self.bgSelectionChanged)
        self.ui.backgroundListWidget.itemSelectionChanged.disconnect(self.bgSelectionChanged)
        for item in self.ui.backgroundListWidget.selectedItems():
            self.ui.backgroundListWidget.takeItem(self.ui.backgroundListWidget.row(item))  
        # self.connect(self.ui.backgroundListWidget, SIGNAL('itemSelectionChanged()'),self.bgSelectionChanged)
        self.ui.backgroundListWidget.itemSelectionChanged.connect(self.bgSelectionChanged)
        self.ui.bgSelectAllCheckBox.setCheckState(0)
        
    def update2dPlots(self):
        if getattr(self,'det',None) is None:   # no frames selected yet: nothing to redraw
            return
        if self.det=='Pilatus':
            self.updatePilPlotData()

            
    def typedPilGeometry(self):
        """(distance, x centre, y centre) per selected frame from the typed
        fields (SPEC box unticked), or None after one message when they do
        not read as numbers: an empty field raised ValueError (found by the
        sweep's random walk, 2026-11-23). The callers then use the SPEC
        values for that redraw; the fields are left as typed."""
        try:
            d=float(self.ui.pilSDDistLineEdit.text())
            t=self.ui.pilDBPosLineEdit.text().split(',')
            x,y=float(t[0]),float(t[-1])
        except (ValueError,IndexError):
            self.notify('Distance or direct-beam position is not a number: the SPEC values are used.')
            return None
        one=np.ones_like(self.selectedPilFramesNums)
        return d*one,x*one,y*one

    def updatePilPlotData(self):
        aspect=str(self.ui.pilAspectComboBox.currentText())
        if self.pilGIDshow==0 and self.pilGISAXSshow==0 and len(self.selectedPilFramesNums)!=0:
            if len(self.selectedPilFramesNums)>10 and self.ui.gixSumCheckBox.checkState()<1:
                #self.messageBox("The number of selected frames are more than 10. So plotting only first 10 images")
                N=10
            else:
                N=len(self.selectedPilFramesNums)    
            self.ui.pilMplWidget.canvas.fig.clf()
            cmap=str(self.ui.pilCMapComboBox.currentText())
            self.ui.pilMaxHorizontalSlider.setValue(int(float(self.ui.pilMaxLineEdit.text())*100/(self.imageMax-self.imageMin)))
            self.ui.pilMinHorizontalSlider.setValue(int(float(self.ui.pilMinLineEdit.text())*100/(self.imageMax-self.imageMin)))
            vmax=float(self.ui.pilMaxLineEdit.text())
            vmin=float(self.ui.pilMinLineEdit.text())
            pilXMin=np.ones_like(self.selectedPilFramesNums)-1
            pilYMin=np.ones_like(self.selectedPilFramesNums)-1
            pilXMax=float(self.pilatus.NCOLS)*np.ones_like(self.selectedPilFramesNums)-1   #[194,...,194]
            pilYMax=float(self.pilatus.NROWS)*np.ones_like(self.selectedPilFramesNums)-1
            xlabel='PixX'
            ylabel='PixY'
            self.wavelength=np.array(self.pilSelected_Wavelength)
            self.alpha=np.array(self.pilSelected_Alpha)
            self.truealpha=np.array(self.pilSelected_TrueAlpha)
            self.dth=np.array(self.pilSelected_Dth)
            if self.ui.pilSpecCheckBox.checkState()!=0: #if this CB is checked, use spec value
                if self.checkSameArrays(self.pilSelectedX)==False or self.checkSameArrays(self.pilSelectedY)==False or self.checkSameArrays(self.pilSelected_Dist)==False:
                    self.messageBox('Warning:: The selected frames have different Pilatus parameters; the parameters of the first frames are used here!!')
                try:
                    self.ui.pilSDDistLineEdit.setText(str(self.pilSelected_Dist[0]))
                    self.ui.pilDBPosLineEdit.setText(str(int(pilXMax[0])-self.pilSelectedX[0])+','+str(self.pilSelectedY[0]))
                   # if self.ui.pilPinholeCheckBox.checkState()!=0:
                   #     self.distance=np.array(self.pilSelected_PDist)
                   # else:
                   #     self.distance=np.array(self.pilSelected_Dist)
                    self.distance=np.array(self.pilSelected_Dist)
                    self.xcenter=np.array(pilXMax[0]-self.pilSelectedX) # image was flipped from left to right, i.e., x=194
                    self.ycenter=np.array(self.pilSelectedY)
                except:
                    pass
            else:   #if this CB is unchecked, use input value   
                typed=self.typedPilGeometry()
                if typed is not None:
                    self.distance,self.xcenter,self.ycenter=typed
                else:                                       # the SPEC values, as with the box ticked
                    self.distance=np.array(self.pilSelected_Dist)
                    self.xcenter=np.array(pilXMax[0]-self.pilSelectedX)
                    self.ycenter=np.array(self.pilSelectedY)
                #self.ui.pilSDDistLineEdit.setText(str(self.pilSelected_Dist[0]))
                #self.ui.pilDBPosLineEdit.setText(str(self.pilSelectedX[0])+','+str(self.pilSelectedY[0]))
                #if self.ui.pilPinholeCheckBox.checkState()!=0:
                #    self.distance=np.array(self.pilSelected_PDist)
                #else:
                #    self.distance=self.distance
                #self.xcenter=np.array(self.pilSelectedX)
                #self.ycenter=np.array(self.pilSelectedY).ones_like(self.selectedPilFramesNums)
            if str(self.ui.pilAxesComboBox.currentText())=='Angles':
                xlabel=r'$2\theta$'+' '+r'$[\deg]$'
                ylabel=r'$\beta$'+' '+r'$[\deg]$'
                pilYMin=((pilYMin-self.ycenter)*0.172/self.distance+np.arcsin(2*np.sin(self.alpha)-np.sin(self.truealpha)))*180/np.pi
                pilYMax=((pilYMax-self.ycenter)*0.172/self.distance+np.arcsin(2*np.sin(self.alpha)-np.sin(self.truealpha)))*180/np.pi
                if self.ui.pilPinholeCheckBox.checkState()!=0:   # pinhole frames (Det_Th > 1 deg, IDL): S4-detector distance
                    self.distance=np.where(np.degrees(self.dth)>1.0,np.array(self.pilSelected_PDist,dtype=float),self.distance)
                #else:
                #    self.distance=np.array(self.pilSelected_Dist)
                pilXMin=(self.dth+(pilXMin-self.xcenter)*0.172/self.distance)*180.0/np.pi
                pilXMax=(self.dth+(pilXMax-self.xcenter)*0.172/self.distance)*180.0/np.pi
                pilXCen=self.dth*180.0/np.pi
                
            elif str(self.ui.pilAxesComboBox.currentText())=='Q':
                xlabel=r'$Q_{xy}$'+' '+r'$[\AA^{-1}]$'
               # ylabel='Qz [1/Angs]'
                ylabel=r'$Q_z$'+' '+r'$[\AA^{-1}]$'
                pilYMin=2.0*np.pi*(np.sin((pilYMin-self.ycenter)*0.172/self.distance+np.arcsin(2*np.sin(self.alpha)-np.sin(self.truealpha)))+np.sin(self.truealpha))/self.wavelength
                pilYMax=2.0*np.pi*(np.sin((pilYMax-self.ycenter)*0.172/self.distance+np.arcsin(2*np.sin(self.alpha)-np.sin(self.truealpha)))+np.sin(self.truealpha))/self.wavelength
                if self.ui.pilPinholeCheckBox.checkState()!=0:   # pinhole frames (Det_Th > 1 deg, IDL): S4-detector distance
                    self.distance=np.where(np.degrees(self.dth)>1.0,np.array(self.pilSelected_PDist,dtype=float),self.distance)
                #else:
                #    self.distance=np.array(self.pilSelected_Dist)
                pilXMin=4.0*np.pi*np.sin((self.dth+(pilXMin-self.xcenter)*0.172/self.distance)/2.0)/self.wavelength
                pilXMax=4.0*np.pi*np.sin((self.dth+(pilXMax-self.xcenter)*0.172/self.distance)/2.0)/self.wavelength
                pilXCen=4.0*np.pi*np.sin(self.dth/2.0)/self.wavelength
                
            # what is drawn: every frame per monitor (Monc), absorber and gain, as every reduction
            # is (owner, 2026-11-23: "all data is default normalized by monc"); pilData stays as read
            disp={i:self.pilFrameNormalised(i)[0] for i in self.selectedPilFramesNums}
            dlog={i:np.log10(np.where(d<=0,1e-10,d)) for i,d in disp.items()}
            if self.pilmovieindex==1:
                for j,i in enumerate(self.selectedPilFramesNums):   # j: position in the selection, i: frame number
                    self.ui.pilMplWidget.canvas.fig.clf()
                    ax=self.ui.pilMplWidget.canvas.fig.add_subplot(1,1,1)
                    ax.set_xlabel(xlabel)
                    ax.set_ylabel(ylabel) 
                    ax.set_title('F #'+str(i),fontsize=16)
                    self.extent=[pilXMin[j],pilXMax[j],pilYMin[j],pilYMax[j]]
                    if self.ui.pilLogIntCheckBox.checkState()!=0:
                        p=ax.imshow(dlog[i],interpolation='bicubic',extent=self.extent,vmax=np.log10(vmax),vmin=np.log10(vmin),cmap=cmap,aspect=aspect,origin='lower')
                        self.Zdata=dlog[i] 
                    else:
                        p=ax.imshow(disp[i],interpolation='bicubic',extent=self.extent,vmax=vmax,vmin=vmin,cmap=cmap,aspect=aspect,origin='lower')
                        self.Zdata=disp[i]
                    ax.format_coord=self.format_pil_coord
                    ax.autoscale(False)
                    ax.plot([pilXCen[j],pilXCen[j]], [pilYMin[j],pilYMax[j]], 'w--', linewidth=2.0)
                    self.ui.pilMplWidget.canvas.fig.colorbar(p)
                    self.ui.pilMplWidget.canvas.fig.suptitle('File: '+self.specFileName+' S# '+listText(np.sort(self.selectedScanNums)))
                    self.ui.pilMplWidget.canvas.fig.tight_layout()
                    self.ui.pilMplWidget.canvas.fig.subplots_adjust(top=0.9)
                    self.ui.pilMplWidget.canvas.draw()
                    self.ui.pilMplWidget.canvas.flush_events()
                    time.sleep(0.5)
                    
            else:
                if self.ui.gixSumCheckBox.checkState()!=0:   #if "Sum All" is checked; merge the frames having the same qz
                    if self.checkSameQzs(self.pilSelectedQzs)==True: # check if qz are same in selected frames
                        # ΣN/ΣM of the frames per Monc (F91; the mean with 'sum_all_legacy_average')
                        self.sumData=self.pilSumNormalised(list(self.selectedPilFramesNums))[0]
                        self.logData=np.log10(np.where(self.sumData<=0,1e-10,self.sumData))
                        ax=self.ui.pilMplWidget.canvas.fig.add_subplot(1,1,1)
                        ax.set_xlabel(xlabel)
                        ax.set_ylabel(ylabel)
                        ax.set_title('Sum'+str(self.selectedPilFramesNums))
                        self.extent=[pilXMin[0],pilXMax[0],pilYMin[0],pilYMax[0]]
                        if self.ui.pilLogIntCheckBox.checkState()!=0:
                            p=ax.imshow(self.logData,interpolation='bicubic',extent=self.extent,vmax=np.log10(vmax),vmin=np.log10(vmin),cmap=cmap,aspect=aspect,origin='lower') 
                            self.Zdata=self.logData
                        else:
                            p=ax.imshow(self.sumData,interpolation='bicubic',extent=self.extent,vmax=vmax,vmin=vmin,cmap=cmap,aspect=aspect,origin='lower')
                            self.Zdata=self.sumData 
                        ax.format_coord=self.format_pil_coord
                        self.ui.pilMplWidget.canvas.fig.colorbar(p)
                    else:
                        self.messageBox('Error:: The selected frames have different qz values!!')
                else:
                    row=2
                    while N/row+pl.where(pl.mod(N,row)>0,1,0)>=row:  #setup subplot format for n of selected frames. 
                        row=row+1
                    row=row-1
                    col=int(N/row+pl.where(pl.mod(N,row)>0,1,0))
                    num=1
                    ax={}
                    for i in self.selectedPilFramesNums[:N]:
                        ax[i]=self.ui.pilMplWidget.canvas.fig.add_subplot(row,col,num)
                        ax[i].set_xlabel(xlabel,fontsize=16)
                        ax[i].set_ylabel(ylabel,fontsize=16)
                        ax[i].set_title('F #'+str(i),fontsize=16)
                        self.extent=[pilXMin[num-1],pilXMax[num-1],pilYMin[num-1],pilYMax[num-1]]
                        if self.ui.pilLogIntCheckBox.checkState()!=0:
                            p=ax[i].imshow(dlog[i],interpolation='bicubic',extent=self.extent,vmax=np.log10(vmax),vmin=np.log10(vmin),cmap=cmap,aspect=aspect,origin='lower')
                            self.Zdata=dlog[i] 
                        else:
                            p=ax[i].imshow(disp[i],interpolation='bicubic',extent=self.extent,vmax=vmax,vmin=vmin,cmap=cmap,aspect=aspect,origin='lower')
                            self.Zdata=disp[i]
                        ax[i].format_coord=self.format_pil_coord
                        self.ui.pilMplWidget.canvas.fig.colorbar(p,format="%.1e")
                        num=num+1
                self.ui.pilMplWidget.canvas.fig.suptitle('File: '+self.specFileName+' S# '+listText(np.sort(self.selectedScanNums)))
                self.ui.pilMplWidget.canvas.fig.tight_layout()
                self.ui.pilMplWidget.canvas.fig.subplots_adjust(top=0.9)
              # self.ui.pilMplWidget.canvas.fig.subplots_adjust(left=0)
              #  self.ui.pilMplWidget.canvas.fig.subplots_adjust(right=1)
                self.ui.pilMplWidget.canvas.draw()
        elif self.pilGIDshow!=0 and len(self.selectedPilFramesNums)!=0:            
            self.pilGIDPlot()
        elif self.pilGISAXSshow!=0 and len(self.selectedPilFramesNums)!=0:
            self.showPilGISAXS()
            
    def pilMovieShow(self):
        if self.det!='Pilatus' or len(self.selectedPilFramesNums)==0:
            self.messageBox('Please select Pilatus images first!')
            return
        #self.disconnect(self.ui.pilAxesComboBox, SIGNAL('currentIndexChanged(int)'), self.update2dPlots)
        self.ui.pilAxesComboBox.currentIndexChanged.disconnect(self.update2dPlots)
        self.ui.pilAxesComboBox.setCurrentIndex(2)
        #self.connect(self.ui.pilAxesComboBox, SIGNAL('currentIndexChanged(int)'), self.update2dPlots)
        self.ui.pilAxesComboBox.currentIndexChanged.connect(self.update2dPlots)
        self.pilmovieindex=1
        #self.disconnect(self.ui.pilPinholeCheckBox,SIGNAL('stateChanged(int)'),self.update2dPlots)
        self.ui.pilPinholeCheckBox.stateChanged.disconnect(self.update2dPlots)
        was=self.ui.pilPinholeCheckBox.checkState()
        self.ui.pilPinholeCheckBox.setCheckState(2)
        self.updatePilPlotData()
        self.pilmovieindex=0
        self.ui.pilPinholeCheckBox.setCheckState(was)      # as it was (it was always left unticked)
        #self.connect(self.ui.pilPinholeCheckBox,SIGNAL('stateChanged(int)'),self.update2dPlots)
        self.ui.pilPinholeCheckBox.stateChanged.connect(self.update2dPlots)
        
    def gioxsDisplay(self):
        if len(self.selectedBgFrameNums)==0 or len(self.selectedPilFramesNums)==0:
            self.messageBox('Warning: No GIOXS data or background selected!!')
        else:
            Dialog=QDialog(self)
            self.uipdgioxs=uic.loadUi(resource('pdgioxs.ui'), Dialog)
            self.uipdgioxs.frameLineEdit.setText(str(len(self.selectedPilFramesNums)))
            self.uipdgioxs.show()
            # self.connect(self.uipdgioxs.closePushButton, SIGNAL('clicked()'), self.pilGioxsClose)
            self.uipdgioxs.closePushButton.clicked.connect(self.pilGioxsClose)
            # self.connect(self.uipdgioxs.runPushButton, SIGNAL('clicked()'), self.pilGioxsRun)
            self.uipdgioxs.runPushButton.clicked.connect(self.pilGioxsRun)
            # self.connect(self.uipdgioxs.savePushButton, SIGNAL('clicked()'), self.pilGioxsSave)
            self.uipdgioxs.savePushButton.clicked.connect(self.pilGioxsSave)
            self.pilGioxsRun()
            
    def pilGioxsClose(self):
        self.uipdgioxs.close()
        
    def pilGioxsSave(self):
        self.saveFileName=QFileDialog.getSaveFileName(caption='Save gioxs data',directory=self.directory)[0]
        if self.saveFileName=='':   # dialog cancelled: write nothing
            return
        for i in range(len(self.gioxsdata)):
            fname=self.saveFileName+self.gioxsname[i]
            np.savetxt(fname,self.gioxsdata[i],fmt='%.4f\t%.4e\t%.4e')
        fname=self.saveFileName+'_bg_gio.txt'
        np.savetxt(fname,self.gioxsbgdata,fmt='%.4f\t%.4e\t%.4e')


        
    def pilGioxsRun(self):
        self.uipdgioxs.plotWidget.canvas.ax.clear()
        aveframe=int(self.uipdgioxs.frameLineEdit.text())
        if aveframe<1:
            aveframe=max(np.abs(aveframe),1)
            self.messageBox('Warning: Average frames should be a positive interger!\n'+str(aveframe)+' is used as ave frames in the calculation')
        avepoint=int(self.uipdgioxs.pointLineEdit.text())
        if avepoint<1:
            avepoint=max(np.abs(avepoint),1)
            self.messageBox('Warning: Average points should be a positive interger!\n'+str(avepoint)+' is used as ave points in the calculation')
        ini=self.xcenter[0]-4
        fin=self.xcenter[0]+4
        cen=[self.xcenter[0], self.ycenter[0]]
        loop=[divmod(len(self.selectedPilFramesNums),aveframe)[0],divmod(len(self.selectedPilFramesNums),aveframe)[1]]
        if loop[1]!=0:
            loop[0]=loop[0]+1
        self.gioxsdata={}
        self.gioxsname={}
        self.pilatus.plotHint(self.bgData,self.bgError,hroi=[ini,fin],cen=cen,ax_type='Q', wavelength=self.selectedBgWavelength[0],s2d_dist=self.selectedBgDist[0],alpha=self.selectedBgAlpha[0],truealpha=self.selectedBgTrueAlpha[0])
        self.gioxsbgdata=self.pilatus.hintData
        for i in range(loop[0]):
            data=self.pilGIOXSData[self.selectedPilFramesNums[aveframe*i]]
            errordata=self.pilGIOXSErrorData[self.selectedPilFramesNums[aveframe*i]]**2
            if i==loop[0]-1 and loop[1]!=0: # last average 
                for j in range(aveframe*i+1,aveframe*i+loop[1]):
                    data=data+self.pilGIOXSData[self.selectedPilFramesNums[j]]
                    errordata=errordata+self.pilGIOXSErrorData[self.selectedPilFramesNums[j]]**2
            else:
                for j in range(aveframe*i+1,aveframe*(i+1)):
                    data=data+self.pilGIOXSData[self.selectedPilFramesNums[j]]
                    errordata=errordata+self.pilGIOXSErrorData[self.selectedPilFramesNums[j]]**2
            if i==loop[0]-1 and loop[1]!=0: # last average 
                data=data/loop[1]
                errordata=np.sqrt(errordata)/loop[1]
                self.pilatus.plotHint(data,errordata,hroi=[ini,fin],cen=cen,ax_type='Q', wavelength=self.pilSelected_Wavelength[0],s2d_dist=self.pilSelected_Dist[0],alpha=self.pilSelected_Alpha[0],truealpha=self.pilSelected_TrueAlpha[0])
                datasum=self.pilatus.hintData
                datagioxs=self.pilGioxsSub(datagioxs,self.gioxsbgdata)
               # print datasum
                self.gioxsdata[i]=self.aveData(datagioxs,avepoint)
                self.gioxsname[i]='_frame'+str(self.selectedPilFramesNums[aveframe*i])+'-'+str(self.selectedPilFramesNums[aveframe*i+loop[1]-1])+'_gio.txt'
                self.uipdgioxs.plotWidget.canvas.ax.errorbar(self.gioxsdata[i][:,0],self.gioxsdata[i][:,1],self.gioxsdata[i][:,2],fmt='o-',label='F #'+str(self.selectedPilFramesNums[aveframe*i])+'-'+str(self.selectedPilFramesNums[aveframe*i+loop[1]-1]))
            else:
                data=data/aveframe
                errordata=np.sqrt(errordata)/aveframe
                self.pilatus.plotHint(data,errordata,hroi=[ini,fin],cen=cen,ax_type='Q', wavelength=self.pilSelected_Wavelength[0],s2d_dist=self.pilSelected_Dist[0],alpha=self.pilSelected_Alpha[0],truealpha=self.pilSelected_TrueAlpha[0])
                datasum=self.pilatus.hintData
                datagioxs=self.pilGioxsSub(datasum,self.gioxsbgdata)
               # print datasum
                self.gioxsdata[i]=self.aveData(datagioxs,avepoint)
                #print datasum[:,0]
                #print self.gioxsdata[i][:,0]
                self.gioxsname[i]='_frame'+str(self.selectedPilFramesNums[aveframe*i])+'-'+str(self.selectedPilFramesNums[aveframe*(i+1)-1])+'_gio.txt'
                self.uipdgioxs.plotWidget.canvas.ax.errorbar(self.gioxsdata[i][:,0],self.gioxsdata[i][:,1],self.gioxsdata[i][:,2],fmt='o-',label='F #'+str(self.selectedPilFramesNums[aveframe*i])+'-'+str(self.selectedPilFramesNums[aveframe*(i+1)-1]))
       # self.uipdgioxs.plotWidget.canvas.ax.clear()
       # self.uipdgioxs.plotWidget.canvas.ax.errorbar(bgdata[:,0],bgdata[:,1],bgdata[:,2],fmt='o-')
        self.uipdgioxs.plotWidget.canvas.ax.errorbar(self.gioxsbgdata[:,0],self.gioxsbgdata[:,1],self.gioxsbgdata[:,2],fmt='o-',label='background')
        self.uipdgioxs.plotWidget.canvas.ax.legend(frameon=False,scatterpoints=0,numpoints=1)
        self.uipdgioxs.plotWidget.canvas.ax.set_yscale('log')
        self.uipdgioxs.plotWidget.canvas.ax.set_xlabel(r'$Q_z$'+' '+r'$[\AA^{-1}]$')
        self.uipdgioxs.plotWidget.canvas.ax.set_ylabel('Intensity')
        self.uipdgioxs.plotWidget.canvas.ax.set_title('File: '+self.specFileName+' S# '+listText(np.sort(self.selectedScanNums))+'\nbg S# '+listText(np.unique(np.sort(self.selectedBgScanNum))))
        self.uipdgioxs.plotWidget.canvas.draw()
        self.command='GIOXS, singal scans=['+listText(np.sort(self.selectedScanNums))+'], bg scans=['+listText(np.unique(np.sort(self.selectedBgScanNum)))+'], ave_frames='+str(aveframe)+', ave_points='+str(avepoint)
        self.ui.commandLineEdit.setText(self.command)                
        
    def pilGioxsSub(self, data1, data2): #for Gioxs 1d data substration
        data1x=data1[:,0]
        data1y=data1[:,1]
        data1yerr=data1[:,2]
        data2x=data2[:,0]
        data2y=data2[:,1]
        data2yerr=data2[:,2]
        overlap1=np.where(np.logical_and(data1x<=data2x[-1],data1x>=data2x[0]))
        f=interp1d(data2x,data2y,kind='cubic')
        ferr=interp1d(data2x,data2yerr,kind='cubic')
        data3y=f(data1x[overlap1])
        data3yerr=ferr(data1x[overlap1])
        datanewx=data1x[overlap1]
        datanewy=data1y[overlap1]-data3y
        datanewyerr=np.sqrt(data1yerr[overlap1]**2+data3yerr**2)
        data=np.vstack((datanewx,datanewy,datanewyerr)).T
        #print data
        #print data1x
        #print data2x
        return data
    
    def aveData(self, data, avepoint):
        if avepoint==1:
            return data
        else:
            loop=[divmod(len(data),avepoint)[0],divmod(len(data),avepoint)[1]]
            newdata=np.array([0,0,0])
            for i in range(loop[0]):
                newdata=np.vstack((newdata,np.array([np.average(data[:,0][i*avepoint:(i+1)*avepoint]),np.average(data[:,1][i*avepoint:(i+1)*avepoint]),np.sqrt(np.sum(data[:,2][i*avepoint:(i+1)*avepoint]**2))/avepoint])))
            if loop[1]!=0:
                newdata=np.vstack((newdata,np.array([np.average(data[:,0][loop[0]*avepoint:loop[0]*avepoint+loop[1]]),np.average(data[:,1][loop[0]*avepoint:loop[0]*avepoint+loop[1]]),np.sqrt(np.sum(data[:,2][loop[0]*avepoint:loop[0]*avepoint+loop[1]]**2))/loop[1]])))
            return newdata[1:]
    
    def pilBurnTest(self):
        if self.det!='Pilatus' or len(self.selectedPilFramesNums)==0:
            self.messageBox('Please select the Pilatus images of a burn test scan first!')
            return
        self.pilSelectedQxs=[self.pilFileQxs[i] for i in self.selectedPilFramesNums]
        if  self.pilSelectedQxs.count(self.pilSelectedQxs[0])!=len(self.pilSelectedQxs) or self.pilSelectedQzs.count(self.pilSelectedQzs[0])!=len(self.pilSelectedQzs) or self.pilSelectedScanNum.count(self.pilSelectedScanNum[0])!=len(self.pilSelectedScanNum):
            self.messageBox('Warning: It is not a burn test scan or multiple scans are selected!')
        else:
            self.buildBurnDialog().show()
            self.burnTrends()

    def buildBurnDialog(self):
        """The burn-test dialog: the Trends tab (default) and the legacy plots."""
        Dialog=QDialog(self)
        self.uipdburn=uic.loadUi(resource('pdburn.ui'), Dialog)
        self.uipdburn.gidComboBox.activated.connect(self.pilGidBurn)      # legacy GID burn analysis
        self.uipdburn.refPushButton.clicked.connect(self.pilRefBurn)      # legacy REF burn analysis
        self.uipdburn.closePushButton.clicked.connect(self.pilBurnClose)
        self.setupBurnTrends()
        return self.uipdburn

    def pilBurnClose(self):
        self.uipdburn.close()

    # ---- burn tests: trends over time (owner, 2026-11-21; F22a 3-4, P30) ----

    def burnOptions(self):
        o=dict(models=list(trendmod.MODELS),estimator='template',time='clock',threshold=5.0,auto_peak=True,position_limit=False,
               errors='auto')
        o.update({k:v for k,v in (self.prefs.get('burn') or {}).items() if k in o})
        return o

    def setupBurnTrends(self):
        """The burn dialog's Trends tab (the default): every quantity over
        time with constant, linear, exponential and double-exponential fits
        compared by AICc; the legacy plot moves to its own tab."""
        from PyQt5.QtWidgets import (QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QComboBox,
                                     QDoubleSpinBox, QPushButton, QLabel)
        u=self.uipdburn
        o=self.burnOptions()
        tabs=QTabWidget(u)
        tabs.setObjectName('burnTabWidget')
        u.layout().replaceWidget(u.plotWidget,tabs)
        page=QWidget()
        lay=QVBoxLayout(page)
        row=QHBoxLayout()
        u.burnModelBoxes={}
        tips={'constant':'c: no change (the average)',
              'linear':'c + s·t: a steady drift',
              'exponential':'a·exp(k·t): a decay (k < 0) or growth with a time constant τ = −1/k',
              'double exponential':'a1·exp(k1·t) + a2·exp(k2·t): a fast and a slow change'}
        for m in trendmod.MODELS:
            b=QCheckBox({'double exponential':'double exp.'}.get(m,m),page)
            b.setObjectName('burn%sCheckBox' % ''.join(w.capitalize() for w in m.split()))
            b.setChecked(m in o['models'])
            b.setToolTip('Fit %s. %s. Models are compared by AICc (Akaike\'s criterion for small samples; QAICc '
                         'when the scatter exceeds the errors); the lowest wins, and a difference below 2 means '
                         'the data cannot tell them apart (Burnham & Anderson 2002).' % (m,tips[m]))
            b.toggled.connect(self.burnOptionsChanged)
            row.addWidget(b)
            u.burnModelBoxes[m]=b
            setattr(u,b.objectName(),b)
        est=QComboBox(page)
        est.setObjectName('burnEstimatorComboBox')
        est.addItems(burnmod.ESTIMATORS)
        est.setCurrentText(o['estimator'])
        est.setToolTip('GID: how each frame\'s peak is measured, in the peak window (constrained as the legacy test '
                       'needed). template (default): the mean of the frames, less the legacy straight background, is the '
                       'peak\'s shape; each frame is fitted as that shape scaled, shifted and stretched, i.e. measured '
                       'relative to the others. moments (legacy arithmetic): straight line through the window\'s first '
                       'and last three points removed, then sum, centroid, r.m.s. width; a steady shoulder under the '
                       'peak dilutes its shift (synthetic: 0.004 read as 0.0023). fit: one peak of the line-cut Fit '
                       'options\' shape (a Gaussian does not describe a pinhole frame\'s peak).')
        est.currentIndexChanged.connect(self.burnOptionsChanged)
        tim=QComboBox(page)
        tim.setObjectName('burnTimeComboBox')
        tim.addItems(['clock','exposure'])
        tim.setCurrentText(o['time'])
        tim.setToolTip('Time axis, from the start of the first frame\'s exposure, at the middle of each frame. '
                       'clock (default; owner: the shutter closes between exposures, wall time is better): measured '
                       'start times (Tstart, or Epoch steps in older files); a scan without them falls back to '
                       'exposure and says so. exposure: the counting time accumulated.')
        tim.currentIndexChanged.connect(self.burnOptionsChanged)
        err=QComboBox(page)
        err.setObjectName('burnErrorsComboBox')
        err.addItems(['auto','scatter','counting'])
        err.setCurrentText(o['errors'])
        err.setToolTip('What sets the size of the error bars in the trend fits. scatter: the frames\' errors only as '
                       'relative weights, scaled to the frames\' scatter about the most general model (a relative '
                       'change is what matters). counting: the errors as computed (QAICc when the scatter exceeds '
                       'them). auto (default): scatter for GID, counting for reflectivity.')
        err.currentIndexChanged.connect(self.burnOptionsChanged)
        thr=QDoubleSpinBox(page)
        thr.setObjectName('burnThresholdSpinBox')
        thr.setRange(0.5,50.0)
        thr.setDecimals(1)
        thr.setSuffix(' %')
        thr.setValue(float(o['threshold']))
        thr.setToolTip('The change that matters: the time until intensity or width changes by this fraction (the '
                       'position: by this fraction of the peak\'s FWHM). Given as a 95 % confident lower bound '
                       '(parameters drawn from the fit\'s covariance), from the best model that can change.')
        thr.valueChanged.connect(self.burnOptionsChanged)
        poslim=QCheckBox('Position in limit',page)
        poslim.setObjectName('burnPositionLimitCheckBox')
        poslim.setChecked(bool(o['position_limit']))
        poslim.setToolTip('GID: let the position\'s change (in % of the FWHM) set the limit too. Off (default): the '
                          'limit is the shortest 5 % time of intensity and width; whether a position change matters '
                          'is your judgment (owner, 2026-11-21), so it is shown but not counted.')
        poslim.toggled.connect(self.burnOptionsChanged)
        auto=QCheckBox('Auto peak',page)
        auto.setObjectName('burnAutoPeakCheckBox')
        auto.setChecked(bool(o['auto_peak']))
        auto.setToolTip('GID: the strongest peak of the mean of the frames, 3 FWHM either side, inside the lit '
                        'columns. Off: the Qxy range typed below.')
        auto.toggled.connect(self.burnOptionsChanged)
        run=QPushButton('Analyse',page)
        run.setObjectName('burnAnalysePushButton')
        run.setToolTip('Measure every selected frame and fit the trends again.')
        run.clicked.connect(self.burnTrends)
        save=QPushButton('Save',page)
        save.setObjectName('burnSavePushButton')
        save.setToolTip('Save the values over time and the trend table (every model: chi2/dof, AICc, weight, '
                        'parameters; the change time) into this SPEC file\'s workbook (Data and Trends sheets).')
        save.clicked.connect(self.saveBurnToWorkbook)
        for w in (QLabel('Estimator',page),est,QLabel('Errors',page),err,QLabel('Time',page),tim,QLabel('Change',page),
                  thr,poslim,auto,run,save):
            row.addWidget(w)
        row.addStretch(1)
        lay.addLayout(row)
        canvas=MplWidget(page)
        canvas.setObjectName('burnTrendPlotWidget')
        lay.addWidget(canvas)
        res=QLabel(page)
        res.setObjectName('burnResultLabel')
        res.setWordWrap(True)
        lay.addWidget(res)
        tabs.addTab(page,'Trends')
        tabs.addTab(u.plotWidget,'Legacy')
        tabs.setTabToolTip(1,'The program\'s original burn plots (REF button, GID list): raw counts against count time '
                             '× frame (P30), one quantity at a time, an exponential for the intensity only.')
        u.refPushButton.clicked.connect(lambda: tabs.setCurrentIndex(1))
        u.gidComboBox.activated.connect(lambda i: i and tabs.setCurrentIndex(1))
        u.burnTabWidget,u.burnEstimatorComboBox,u.burnTimeComboBox,u.burnErrorsComboBox=tabs,est,tim,err
        u.burnThresholdSpinBox,u.burnAutoPeakCheckBox,u.burnAnalysePushButton=thr,auto,run
        u.burnPositionLimitCheckBox=poslim
        u.burnSavePushButton,u.burnTrendPlotWidget,u.burnResultLabel=save,canvas,res
        self.burnResult=None

    def burnOptionsChanged(self,*args):
        u=self.uipdburn
        o=dict(models=[m for m,b in u.burnModelBoxes.items() if b.isChecked()],
               estimator=str(u.burnEstimatorComboBox.currentText()),time=str(u.burnTimeComboBox.currentText()),
               errors=str(u.burnErrorsComboBox.currentText()),
               threshold=float(u.burnThresholdSpinBox.value()),auto_peak=bool(u.burnAutoPeakCheckBox.isChecked()),
               position_limit=bool(u.burnPositionLimitCheckBox.isChecked()))
        self.setPreference('burn',o)
        self.burnTrends()

    def burnExperiment(self):
        """An lss_core Experiment of the open SPEC file (kept while the file
        is unchanged)."""
        from lss_core.experiment import Experiment
        key=(os.path.abspath(self.specFileName),os.path.getmtime(self.specFileName))
        if getattr(self,'_burnExperiment',(None,None))[0]!=key:
            self._burnExperiment=(key,Experiment(self.specFileName))
        return self._burnExperiment[1]

    def burnArguments(self):
        """(scan, keywords) for Experiment.burn from the selection and the window's settings."""
        u=self.uipdburn
        o=self.burnOptions()
        scan=int(self.pilScanNum[self.selectedPilFramesNums[0]])
        kw=dict(points=[int(self.pilFrameNum[i]) for i in self.selectedPilFramesNums],time=o['time'],
                models=tuple(o['models']),threshold=o['threshold']/100.0,estimator=o['estimator'])
        if o['position_limit']:
            kw['limit']=('intensity','fwhm','centre')
        if o['errors']!='auto':
            kw['trend_errors']={'counting':'given'}.get(o['errors'],o['errors'])
        if o['estimator']=='fit':
            kw['fit']=dataclasses.replace(self.peakFitOptions,n_peaks=1)
        if not o['auto_peak']:
            lo,hi=(float(v) for v in str(u.rangeLineEdit.text()).split(':'))
            kw['qxy_range']=(lo,hi)
        kw['slit']=tuple(int(v) for v in str(self.ui.refSlitLineEdit.text()).split(','))
        kw['bg_offset']=float(self.ui.refBGOffLineEdit.text())
        kw['direction']=str(self.ui.refBGDirComboBox.currentText())
        if self.ui.pilSpecCheckBox.checkState()==0:
            t=str(self.ui.pilDBPosLineEdit.text()).split(',')
            kw['db_pos']=(float(t[0]),float(t[-1]))
        if int(self.ui.pilBPCiteSpinBox.value())!=0:
            kw['bad_pixel_iterations']=int(self.ui.pilBPCiteSpinBox.value())
            kw['bad_pixel_factor']=int(self.ui.pilBPCfacSpinBox.value())
        return scan,kw

    def burnTrends(self):
        """Measure the selected burn frames and fit their trends (lss_core.burn)."""
        u=getattr(self,'uipdburn',None)
        if u is None or not hasattr(u,'burnResultLabel'):
            return
        if self.det!='Pilatus' or len(self.selectedPilFramesNums)==0 or not getattr(self,'specFileName',None):
            u.burnResultLabel.setText('Select the Pilatus frames of a burn scan first.')
            return
        try:
            scan,kw=self.burnArguments()
        except (ValueError,IndexError) as e:
            u.burnResultLabel.setText('Not analysed: the settings could not be read (%s).' % e)
            return
        if not kw['models']:
            u.burnResultLabel.setText('Tick at least one model.')
            return
        try:
            res=self.burnExperiment().burn(scan,errors=self.errorModel,**kw)
        except (ValueError,KeyError,OSError) as e:
            self.burnResult=None
            u.burnResultLabel.setText('Not analysed: %s' % e)
            u.burnResultLabel.setToolTip('')
            self.log.info('burn test of scan %d not analysed: %s',scan,e)
            return
        self.burnResult=res
        self.plotBurnTrends(res)
        u.Label.setText('Burn test for Scan #%d' % scan)
        u.burnResultLabel.setText(self.burnShortText(res))
        u.burnResultLabel.setToolTip(self.burnLongText(res))
        args=dict(kw)
        args.pop('models') if tuple(args.get('models',()))==trendmod.MODELS else None
        for k,v in (('time','clock'),('threshold',0.05),('estimator','template'),('slit',(21,11)),
                    ('bg_offset',0.5),('direction','H')):
            if args.get(k)==v:
                args.pop(k)
        if args.get('points')==[f.index for f in self.burnExperiment().frames([scan])]:
            args.pop('points')
        extra=script_kw(self.errorModel)
        head='from lss_core.peaks import FitOptions\n' if 'fit' in args else ''
        self.burnScript=head+'burn = exp.burn(%d%s%s)\nprint(burn.summary())' % (
            scan,''.join(', %s=%r' % (k,v) for k,v in args.items()),', '+extra if extra else '')

    def burnShortText(self,res):
        parts=[]
        for q,c in res.trends.items():
            if c.stable is None:
                parts.append('%s: best %s' % (burnmod.LABELS[q],c.best))
            else:
                parts.append('%s: %s' % (burnmod.LABELS[q],'stable' if c.stable else 'changing'))
        t,q=res.safe_time()
        if q:
            ch=res.trends[q].change
            parts.append('%.0f %% change in ≥ %.3g s (%s, %.0f %% confidence%s)' % (
                100*res.threshold,t,burnmod.LABELS[q].lower(),100*ch.confidence,', extrapolated' if ch.extrapolated else ''))
        elif res.trends:
            parts.append('no %.0f %% change within the horizon' % (100*res.threshold))
        return '; '.join(parts)

    def burnLongText(self,res):
        lines=[res.summary(),'']
        for q,c in res.trends.items():
            lines.append('%s (%s):' % (burnmod.LABELS[q],c.criterion))
            for f in c.ranked():
                lines.append('  %s  Δ %.1f  weight %.2f  %s' % (f.model,f.delta,f.weight,f.describe()))
        lines+=['']+res.notes
        if res.kind=='gid' and res.reference is not None:
            r=res.reference
            lines.append('peak window Qxy %.4f–%.4f; mean profile: centroid %.4f, FWHM %.4f; estimator %s'
                         % (res.window[0],res.window[1],r['centre'],r['fwhm'],r['estimator']))
        lines.append('A position change can also be the sample height drifting (pinhole geometry), not damage.'
                     if res.kind=='gid' else '')
        return '\n'.join(l for l in lines if l is not None)

    def plotBurnTrends(self,res):
        """Each quantity on its own panel, its right axis in percent, the
        summary to the right (owner, 2026-11-21; lss_core.burn.plot)."""
        canvas=self.uipdburn.burnTrendPlotWidget.canvas
        burnmod.plot(res,canvas.fig,'%s S# %d' % (os.path.basename(self.specFileName),res.scan))
        try:
            canvas.fig.subplots_adjust(left=0.1,right=0.97,top=0.9,bottom=0.09)
        except Exception:
            pass
        canvas.draw()

    def saveBurnToWorkbook(self):
        res=getattr(self,'burnResult',None)
        if res is None:
            self.saveNotice('Analyse a burn test first.')
            return
        cols,arr=res.data()
        o=self.burnOptions()
        ids=self.saveToWorkbook('burn test',auto=getattr(self,'autoSaving',False),items=[dict(scans=[res.scan],data=arr,columns=cols,
                                                  label=res.kind,settings=dict(o,window=res.window,notes=res.notes),
                                                  trends=list(res.trends.items()),time_axis=res.time,
                                                  recipe=getattr(self,'burnScript','') or '')])
        if ids and getattr(self,'burnScript',None) and not getattr(self,'autoSaving',False):
            self.scriptLine(self.burnScript)
        
    def expdecay(self, x, a,b):  #define exponential decay
        return a*np.exp(-x/b)
        
        
    def burnFramesGone(self):
        """The burn-test dialog stays open while the selection changes: True
        (and a message) when no frames are selected any more."""
        if self.det!='Pilatus' or len(self.selectedPilFramesNums)==0 or len(getattr(self,'pilSelected_Dth',[]))==0:
            self.messageBox('Please select the Pilatus images of a burn test scan first!')
            return True
        return False

    def pilRefBurn(self):
        if self.burnFramesGone():
            return
        if self.pilSelected_Dth[0] > 0.001:
            self.messageBox('Warning: It it not a REF burn test. Please use GID burn test button!')
        else:
            self.uipdburn.plotWidget.canvas.ax.clear()
            self.uipdburn.plotWidget.canvas.ax.set_xlabel('Time (sec.)')
            self.uipdburn.plotWidget.canvas.ax.set_ylabel('Intensity')
            ctime=float(self.scanlines[self.scanRow(self.selectedScanNums[0])].split(' ')[-1])  #get the counting time
            scan=self.scanlines[self.scanRow(self.selectedScanNums[0])].split(' ')[1] #get scan number
            self.uipdburn.Label.setText('Burn test for Scan #'+scan)
            slitx=int(self.ui.refSlitLineEdit.text().split(',')[0]) #get the size of ROI
            slity=int(self.ui.refSlitLineEdit.text().split(',')[1])
            self.slit=[slitx,slity]        
            self.dir=str(self.ui.refBGDirComboBox.currentText()) #get the background offset direction
            bg=float(self.ui.refBGOffLineEdit.text())  #get the background offset
            data=[]
            for i in self.selectedPilFramesNums:
                cenx=self.pilatus.NCOLS-self.pilX[i]-1 #image was flipped left to right
                ceny=self.pilY[i]
                cenx,ceny=self.pilatus.peakLocate(self.pilData[i],self.pilErrorData[i],cen=[cenx,ceny],mon=self.pilMonc[i])
                if self.dir=='H':
                    self.bg=bg*self.pil_Dist[i]*np.pi/180/0.172/slitx
                else:
                    self.bg=bg*self.pil_Dist[i]*np.pi/180/0.172/slity
                self.pilatus.sumROI(slit=self.slit,cen=[cenx,ceny],dir=self.dir,bg=self.bg)
                net,neterr=self.pilatus.netROI()
                data.append([ctime*i,net,neterr])
            data=np.array(data)
            x=data[:,0]
            y=data[:,1]
            yerr=data[:,2]
            try:
                pfit,pcov=curve_fit(self.expdecay,x,y,p0=[y[0],(x[-1]-x[0])/np.log(y[0]/y[-1])],sigma=yerr,maxfev=5000)
                tauerr=int(pcov[1][1]**0.5)
                tau=int(pfit[1])
                self.uipdburn.plotWidget.canvas.ax.errorbar(x,y,yerr,fmt='o-')
                self.uipdburn.plotWidget.canvas.ax.plot(x,self.expdecay(x,pfit[0],pfit[1]),'r--',label=r'$\tau$'+' = '+str(format(tau,'.1e'))+' ('+str(format(tauerr,'.1e'))+') sec.')
                self.uipdburn.plotWidget.canvas.ax.legend(loc=1,frameon=False,scatterpoints=0,numpoints=1)
                self.uipdburn.plotWidget.canvas.ax.set_xlim(x[0],x[-1])
                self.uipdburn.plotWidget.canvas.ax.set_title('File: '+self.specFileName+' S# '+listText(np.sort(self.selectedScanNums)))
                self.uipdburn.plotWidget.canvas.draw()
                self.command='REF Burn, scan='+str(self.selectedScanNums)
                self.ui.commandLineEdit.setText(self.command)
            except:
                self.messageBox('Warning: It seems there is not enough data points for burn test fitting (min: 3 points)!')
                return
            
    def pilGidBurn(self):
        if self.uipdburn.gidComboBox.currentIndex()==0:
            return
        elif self.burnFramesGone():
            return
        else:
            if self.pilSelected_Dth[0]==0:
                self.messageBox('Warning: It is not a GID burn test. Please click REF burn test button!')
            else:
                try:
                    ctime=float(self.scanlines[self.scanRow(self.selectedScanNums[0])].split(' ')[-1])  #get the counting time
                    scan=self.scanlines[self.scanRow(self.selectedScanNums[0])].split(' ')[1] #get scan number
                    self.uipdburn.Label.setText('Burn test for Scan #'+scan)
                    ini=float(self.uipdburn.rangeLineEdit.text().split(':')[0]) #get the  ini qz value from lineedit
                    fin=float(self.uipdburn.rangeLineEdit.text().split(':')[1]) #get the final qz value from lineedit
                    cen=self.pilatus.NCOLS-self.pilSelectedX[0]-1
                    ini=max(int((2.0*np.arcsin(ini*self.pilSelected_Wavelength[0]/4.0/np.pi)-self.pilSelected_Dth[0])*self.pilSelected_PDist[0]/0.172)+cen,0) # conver it to pixel and check with the boundary
                    fin=min(int((2.0*np.arcsin(fin*self.pilSelected_Wavelength[0]/4.0/np.pi)-self.pilSelected_Dth[0])*self.pilSelected_PDist[0]/0.172)+cen,self.pilatus.NCOLS-1)
                    row=np.arange(self.pilatus.NROWS)
                    col=np.arange(ini,fin+1)
                    col,row=np.meshgrid(col,row)
                    print(ini, fin)
                    data=[]
                    self.uipdburn.plotWidget.canvas.ax.clear()
                    self.uipdburn.plotWidget.canvas.ax.set_xlabel('Time (sec.)')
                    for i in self.selectedPilFramesNums:
                        self.pilatus.plotVint(self.pilData[i],self.pilErrorData[i],hroi=[ini,fin])
                        datai=self.pilatus.vintData
                        meanleft=np.mean(datai[0:3,1])  #pass a straight line bewteen first and last three points in the selected range, then subtracte it from the data, keep the errorbar unchange
                        meanright=np.mean(datai[-3:,1])
                        slope=(meanright-meanleft)/(datai[-2,0]-datai[1,0])
                        datai[:,1]=datai[:,1]-slope*(datai[:,0]-datai[1,0])-meanleft #subtracte the background
                        #datai[:,2]=np.sqrt(np.abs(datai[:,1]))   #need to recheck the error bar
                        if self.uipdburn.gidComboBox.currentText()=='Intensity':
                            if self.errorModel.budget:   # monitor term on the whole sum, u_M from the model
                                u=float(self.errorModel.monitor.relative(self.pilMonc[i]))
                                data.append([ctime*i,np.sum(datai[:,1])/self.pilMonc[i],np.sqrt((np.sum(datai[:,1])/self.pilMonc[i])**2*u**2+np.sum(datai[:,2]**2)/self.pilMonc[i]**2)])
                            else:
                                data.append([ctime*i,np.sum(datai[:,1])/self.pilMonc[i],np.sqrt(np.sum(datai[:,1])**2/self.pilMonc[i]**3+np.sum(datai[:,2]**2)/self.pilMonc[i]**2)])
                            self.uipdburn.plotWidget.canvas.ax.set_ylabel('Intensity')
                        elif self.uipdburn.gidComboBox.currentText()=='Location':
                            data.append([ctime*i,np.sum(datai[:,1]*datai[:,0])/np.sum(datai[:,1]),np.sqrt(np.sum(datai[:,0]**2*datai[:,2]**2)/np.sum(datai[:,1])**2+np.sum(datai[:,1]*datai[:,0])**2*np.sum(datai[:,2]**2)/np.sum(datai[:,1])**4)])
                        elif self.uipdburn.gidComboBox.currentText()=='Width':
                            location=np.sum(datai[:,1]*datai[:,0])/np.sum(datai[:,1])
                            datai[:,0]=(datai[:,0]-location)**2
                            data.append([ctime*i,np.sum(datai[:,1]*datai[:,0])/np.sum(datai[:,1]),np.sqrt(np.sum(datai[:,0]**2*datai[:,2]**2)/np.sum(datai[:,1])**2+np.sum(datai[:,1]*datai[:,0])**2*np.sum(datai[:,2]**2)/np.sum(datai[:,1])**4)])
                    data=np.array(data)
                    x=data[:,0]
                    y=data[:,1]
                    yerr=data[:,2]
                    print(y)
                    if self.uipdburn.gidComboBox.currentText()=='Location':
                        self.uipdburn.plotWidget.canvas.ax.set_ylabel('Relative Location '+r'$[\AA^{-1}]$')
                        y=4.0*np.pi*np.sin((self.pilSelected_Dth[0]+(data[:,1]-cen)*0.172/self.pilSelected_PDist[0])/2.0)/self.pilSelected_Wavelength[0]
                        yerr=4.0*np.pi*np.cos((self.pilSelected_Dth[0]+(data[:,1]-cen)*0.172/self.pilSelected_PDist[0])/2.0)/self.pilSelected_Wavelength[0]*data[:,2]*0.172/2/self.pilSelected_PDist[0]
                        y=y-y[0]
                    if self.uipdburn.gidComboBox.currentText()=='Width':
                        self.uipdburn.plotWidget.canvas.ax.set_ylabel('FWHM '+r'$[\AA^{-1}]$')
                        y=np.sqrt(y)
                        yerr=0.5/y*yerr
                        y=4.0*np.pi*np.sin((y*0.172/self.pilSelected_PDist[0])/2.0)/self.pilSelected_Wavelength[0]
                        yerr=4.0*np.pi*np.cos((data[:,1]*0.172/self.pilSelected_PDist[0])/2.0)/self.pilSelected_Wavelength[0]*data[:,2]*0.172/2/self.pilSelected_PDist[0]
                    self.uipdburn.plotWidget.canvas.ax.errorbar(x,y,yerr,fmt='o-')
                    if self.uipdburn.gidComboBox.currentText()=='Intensity':
                        self.uipdburn.plotWidget.canvas.ax.set_ylabel('Intensity')
                        pfit,pcov=curve_fit(self.expdecay,x,y,p0=[y[0],(x[-1]-x[0])/np.log(y[0]/y[-1])],sigma=yerr,maxfev=5000)
                        tauerr=int(pcov[1][1]**0.5)
                        tau=int(pfit[1])
                        self.uipdburn.plotWidget.canvas.ax.plot(x,self.expdecay(x,pfit[0],pfit[1]),'r--',label=r'$\tau$'+' = '+str(format(tau,'.1e'))+' ('+str(format(tauerr,'.1e'))+') sec.')
                        self.uipdburn.plotWidget.canvas.ax.legend(loc=1,frameon=False,scatterpoints=0,numpoints=1)
                    self.uipdburn.plotWidget.canvas.ax.set_xlim(x[0],x[-1])
                    self.uipdburn.plotWidget.canvas.ax.set_title('File: '+self.specFileName+' S# '+listText(np.sort(self.selectedScanNums)))
                    self.uipdburn.plotWidget.canvas.draw()
                    self.command='GID Burn, scan='+str(self.selectedScanNums)+', Qz range=['+str(self.uipdburn.rangeLineEdit.text())+'], mode='+str(self.uipdburn.gidComboBox.currentText())
                    self.ui.commandLineEdit.setText(self.command)
                except:
                    self.messageBox('Warning: It seems there is either not enough data points for burn test fitting (min: 3 points) or selected Qxy range is not correct!')
                    return
                 
    def pilGISAXS(self):
        if str(self.ui.gisaxsComboBox.currentText())=='Show GISAXS':
            self.showPilGISAXS()
        elif str(self.ui.gisaxsComboBox.currentText())=='Save GISAXS':
            self.savePilGISAXS()

    def showPilGISAXS(self):
        self.pilGISAXSshow=1
        self.pilGIDshow=0
        if len(self.selectedPilFramesNums)!=1 and self.ui.gixSumCheckBox.checkState()==0:
            self.messageBox('Warning: Please select only one frame or use summed frames')
        else:
            if self.ui.gixSumCheckBox.checkState() != 0:  # if "Sum All" is checked; merge the frames having the same qz
                # per Monc, ΣN/ΣM (owner, 2026-11-23; F91); the raw mean with 'gisaxs_raw_counts'
                self.sumData, self.sumErrData = self.gisaxsData(list(self.selectedPilFramesNums))
            if str(self.ui.pilAxesComboBox.currentText())!='Q':
                # self.disconnect(self.ui.pilAxesComboBox, SIGNAL('currentIndexChanged(int)'), self.update2dPlots)
                self.ui.pilAxesComboBox.currentIndexChanged.disconnect(self.update2dPlots)
                self.ui.pilAxesComboBox.setCurrentIndex(2)
                # self.connect(self.ui.pilAxesComboBox, SIGNAL('currentIndexChanged(int)'), self.update2dPlots)
                self.ui.pilAxesComboBox.currentIndexChanged.connect(self.update2dPlots)
            if self.ui.pilSpecCheckBox.checkState() != 0:  # if this CB is checked, use spec value
                if self.checkSameArrays(self.pilSelectedX) == False or self.checkSameArrays(self.pilSelectedY) == False or self.checkSameArrays(self.pilSelected_Dist) == False:
                    self.messageBox('Warning:: The selected frames have different Pilatus parameters; the parameters of the first frames are used here!!')
                try:
                    self.ui.pilSDDistLineEdit.setText(str(self.pilSelected_Dist[0]))
                    self.ui.pilDBPosLineEdit.setText(str(int(self.pilatus.NCOLS-self.pilSelectedX[0])) + ',' + str(self.pilSelectedY[0]))
                    self.distance = np.array(self.pilSelected_Dist)
                    self.xcenter = np.array(self.pilatus.NCOLS- self.pilSelectedX)  # image was flipped from left to right, i.e., x=194
                    self.ycenter = np.array(self.pilSelectedY)
                except:
                    pass
            else:  # if this CB is unchecked, use input value
                typed = self.typedPilGeometry()
                if typed is not None:
                    self.distance, self.xcenter, self.ycenter = typed
                else:                                       # the SPEC values, as with the box ticked
                    self.distance = np.array(self.pilSelected_Dist)
                    self.xcenter = np.array(self.pilatus.NCOLS - self.pilSelectedX)
                    self.ycenter = np.array(self.pilSelectedY)
            self.ui.pilMplWidget.canvas.fig.clf()
            cmap = str(self.ui.pilCMapComboBox.currentText())
            vmax = float(self.ui.pilMaxLineEdit.text())
            vmin = float(self.ui.pilMinLineEdit.text())
            pilX = np.arange(0, self.pilatus.NCOLS)
            pilY = np.arange(0, self.pilatus.NROWS)
            aspect = str(self.ui.pilAspectComboBox.currentText())
            xlabel = r'$Q_{xy}$' + ' ' + r'$[\AA^{-1}]$'
            ylabel = r'$Q_z$' + ' ' + r'$[\AA^{-1}]$'
            ax = self.ui.pilMplWidget.canvas.fig.add_subplot(1, 1, 1)
            ax.set_xlabel(xlabel, fontsize=16)
            ax.set_ylabel(ylabel, fontsize=16)
            pilY_deg = np.arctan(-(self.ycenter[0] - pilY) * 0.172 / self.distance[0]) + np.arcsin(2 * np.sin(self.alpha[0]) - np.sin(self.truealpha[0]))  # beta in rad
            if self.ui.pilPinholeCheckBox.checkState()!= 0:
                self.distance = np.array(self.pilSelected_PDist)  # distance between S4 & S5 for pinhole setup
            pilX_deg = self.dth[0] + np.arctan(-(self.xcenter[0] - pilX) * 0.172 / self.distance[0])  # dth in rad
            pilX_deg, pilY_deg = np.meshgrid(pilX_deg, pilY_deg)  # mesh x-y corrdinates
            self.pilXbin = 2.0 * np.pi / self.wavelength[0] * np.sqrt(np.cos(self.truealpha[0]) ** 2 + np.cos(pilY_deg) ** 2 - 2 * np.cos(self.truealpha[0]) * np.cos(pilY_deg) * np.cos(pilX_deg))
            self.pilYbin = 2.0 * np.pi / self.wavelength[0] * (np.sin(self.truealpha[0]) + np.sin(pilY_deg))
            # as many Qxy bins as columns, scaled by the whole image's Qxy span over the first
            # row's (last column - first). |Qxy| folds at the direct beam: with the beam centred
            # the two ends have the same Qxy (zero: OverflowError), right of the centre the last
            # the smaller (a negative count: ValueError). Now the size of that difference, and
            # the row's full span (max - min) when it is zero; unchanged left of the centre
            row = self.pilXbin[0]
            row_span = abs(row[-1] - row[0])
            if not (row_span > 0 and np.isfinite(row_span)):
                row_span = np.ptp(row)
            nqxy = len(row)
            if row_span > 0 and np.isfinite(row_span):
                nqxy = max(2, int(nqxy * (np.max(self.pilXbin) - np.min(self.pilXbin)) / row_span))
            qxyrange = np.linspace(np.min(self.pilXbin), np.max(self.pilXbin), nqxy)
            qxy, qz = np.meshgrid(qxyrange, self.pilYbin[:, 0])
            if len(self.selectedPilFramesNums)==1:
                 self.sumData, self.sumErrData = self.gisaxsData([self.selectedPilFramesNums[0]])   # per Monc (owner, 2026-11-23)
            self.pilDataBin = griddata((self.pilXbin.ravel(), self.pilYbin.ravel()), self.sumData.ravel(), (qxy, qz), method='linear', fill_value=1e-10)
            self.pilErrorDataBin = griddata((self.pilXbin.ravel(), self.pilYbin.ravel()), self.sumErrData.ravel(), (qxy, qz), method='linear', fill_value=1e-10)
            self.pilXbin=qxy
            self.pilYbin=qz
            self.extent=[self.pilXbin[0][0],self.pilXbin[0][-1],self.pilYbin[0][0],self.pilYbin[-1][0]]
            if self.ui.pilLogIntCheckBox.checkState() != 0:
                self.logData = np.log10(np.where(self.pilDataBin <= 0, 1e-10, self.pilDataBin))
                p = ax.imshow(self.logData, interpolation='bicubic', extent=self.extent, vmax=np.log10(vmax),vmin=np.log10(vmin), cmap=cmap, aspect=aspect, origin='lower')
                self.Zdata = self.logData
            else:
                p = ax.imshow(self.pilDataBin, interpolation='bicubic', extent=self.extent, vmax=vmax, vmin=vmin, cmap=cmap,aspect=aspect, origin='lower')
                self.Zdata = self.pilDataBin
            ax.set_aspect(aspect)
            ax.set_title("GISAXS")
            ax.format_coord=self.format_pil_coord
            self.ui.pilMplWidget.canvas.fig.colorbar(p)
            self.ui.pilMplWidget.canvas.fig.tight_layout()
            self.ui.pilMplWidget.canvas.fig.subplots_adjust(top=0.9)
            self.ui.pilMplWidget.canvas.draw()

    def savePilGISAXS(self):
        try:
            self.saveFileName = QFileDialog.getSaveFileName(caption='Save gioxs data', directory=self.directory)[0]
            if self.saveFileName=='':   # dialog cancelled: write nothing
                return
            data2d = []
            fname_2d = self.saveFileName + '_gisaxs.txt'
            for i in range(len(self.pilDataBin)):
                for j in range(len(self.pilDataBin[0])):
                    data2d.append([self.pilXbin[i][j], self.pilYbin[i][j], self.pilDataBin[i][j], self.pilErrorDataBin[i][j]])
            np.savetxt(fname_2d, np.array(data2d), fmt='%.4e\t%.4e\t%.4e\t%.4e')
        except:
            self.messageBox("Warning: No GISAXS data available!")

    def pilGID(self):
        if str(self.ui.gidComboBox.currentText())=='GID Patch': 
            self.pilGIDRelax=0
            self.pilGIDpatchData()
        elif str(self.ui.gidComboBox.currentText())=='GID Patch Relax':
            self.pilGIDRelax=1
            self.pilGIDpatchData()
        elif str(self.ui.gidComboBox.currentText())=='Save GID':
            self.saveGIDData()
        elif str(self.ui.gidComboBox.currentText())=='Form Factor':
            self.setGIDFormFactor()
        elif str(self.ui.gidComboBox.currentText())=='Worksheet':
            self.showGIDWorksheet()
        elif str(self.ui.gidComboBox.currentText())=='Save to workbook':
            self.saveGIDToWorkbook()
            
    def showGIDWorksheet(self):
        if self.gidWorksheet is None:
            self.gidWorksheet=self.buildGIDWorksheet()
        self.gidWorksheetResults()
        self.gidWorksheet.show()
        self.gidWorksheet.raise_()

    def buildGIDWorksheet(self):
        """GID patching worksheet (F61): the patch's settings, editable, and
        what each join did. Short labels; the explanations are in tooltips."""
        from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QCheckBox,
                                     QLabel, QSpinBox, QDoubleSpinBox, QComboBox, QPushButton, QTableWidget,
                                     QAbstractItemView)
        d=QDialog(self)
        d.setObjectName('gidWorksheetDialog')
        d.setWindowTitle('GID patching worksheet')
        lay=QVBoxLayout(d)
        g=QGroupBox('Settings',d)
        form=QFormLayout(g)
        gp=self.gidParams

        def spin(name,lo,hi,val,tip,dbl=False):
            w=(QDoubleSpinBox if dbl else QSpinBox)(g)
            w.setObjectName(name)
            w.setRange(lo,hi)
            if dbl:
                w.setDecimals(1)
            w.setValue(val)
            w.setToolTip(tip)
            return w
        cols=spin('gidColumnsSpinBox',1,195,int(float(self.ui.pilHSlitLineEdit.text() or 3)),
                  'Pixels summed across each frame, centred on the direct-beam column; the sum is one profile placed at '
                  'the frame\'s detector angle (the H slit field of the GID tab). More columns: more counts, coarser 2theta '
                  'resolution (the pinhole correction, F45, is to lift that limit).')
        rows=QHBoxLayout()
        rmin=spin('gidRowMinSpinBox',0,4000,gp.row_min,'First detector row used (beta range). Default 15.')
        rmax=spin('gidRowMaxSpinBox',0,4000,gp.row_max,'Last detector row used (beta range). Default 486.')
        rows.addWidget(rmin)
        rows.addWidget(rmax)
        qzd=spin('gidQzDecimalsSpinBox',1,6,gp.qz_decimals,'Frames are grouped into Qz levels by their Qz rounded to this many '
                 'decimals (at most three levels: low, middle, high; more go into high). Default 3.')
        dthd=spin('gidDthDecimalsSpinBox',1,6,gp.dth_decimals,'The detector angle (degrees) is rounded to this many decimals '
                  'before frames are ordered and joined. Default 3.')
        area=QCheckBox('Area correction',g)
        area.setObjectName('gidAreaCheckBox')
        area.setChecked(gp.area_correction)
        area.setToolTip('Divide by the fraction of the footprint seen through the detector slits at each detector angle '
                        '(S1, S4, S5 and the distances from the SPEC header).')
        hard=spin('gidHardSlitSpinBox',0,500,gp.hard_slit_offset_mm,'mm by which the sample-detector distance is shortened '
                  'in the area correction when hard slits are used. Default 32.', dbl=True)
        pol=QCheckBox('Polarisation',g)
        pol.setObjectName('gidPolCheckBox')
        pol.setChecked(gp.polarisation)
        pol.setToolTip('Divide by 1 - (sin 2theta cos beta)^2 (horizontally polarised beam).')
        kind=QComboBox(g)
        kind.setObjectName('gidVJoinKindComboBox')
        kind.addItems(['cubic','linear'])
        kind.setCurrentText(gp.vjoin_kind)
        kind.setToolTip('Interpolation of the beta-integrated profiles when two Qz levels are joined. Default cubic. '
                        'Horizontal joins use linear interpolation and average the two scans in the overlap.')
        dist=QLabel('sample-detector',g)
        dist.setObjectName('gidDistanceLabel')
        dist.setToolTip('Distance used to turn columns and rows into angles in the 3-column patch (pinhole off). '
                        'With the pinhole on, every pixel gets its own 2theta and beta through S4 (below).')
        absl=QLabel('not applied',g)
        absl.setObjectName('gidAbsorberLabel')
        absl.setToolTip('Frames are divided by their monitor but not multiplied by the absorber factor: GID scans are '
                        'expected at one absorber setting; joins absorb a difference between scans.')
        form.addRow('Columns per frame',cols)
        form.addRow('Rows',rows)
        form.addRow('Qz grouping, decimals',qzd)
        form.addRow('Angle rounding, decimals',dthd)
        form.addRow(area,hard)
        form.addRow(pol)
        form.addRow('Vertical join',kind)
        form.addRow('Distance for angles',dist)
        form.addRow('Absorber factor',absl)
        pin=QCheckBox('Pinhole: angle per column',g)
        pin.setObjectName('gidPinholeCheckBox')
        pin.setChecked(gp.pinhole)
        pin.setToolTip('Give every pixel its own 2theta and beta through the pinhole (S4), exactly as Mati Meron\'s '
                       'IMG_COO_CONV (beta depends on the column: each column sees another part of the footprint), and '
                       'use all columns the S5 slits and the footprint allow, binned in (2theta, beta) as counts over '
                       'normalisation (F45; lss_core/pinhole.py). Off: the patch above, columns summed at the frame '
                       'angle. The settings above that apply: rows, Qz grouping, area correction, polarisation.')
        pdist=spin('gidPinholeDistSpinBox',0,2000,gp.pinhole_distance_mm,'S4 (pinhole) to detector distance, mm. '
                   '0: the header value (#B1 4th number, 271 on NX). "Fit" estimates it from a peak\'s drift; the fit '
                   'depends on the columns used by several mm (column response), so the header value is the default.',dbl=True)
        resp=QComboBox(g)
        resp.setObjectName('gidResponseComboBox')
        resp.addItems(['fit','beam','physical','physical+fit','none'])
        resp.setCurrentText(gp.response)
        resp.setToolTip('Column response: "fit" estimates each column\'s relative sensitivity from the data (the '
                        'same 2theta is seen by many columns in different frames); "beam" estimates one profile '
                        'along the beam axis instead, shared by all frames: through S4 each column sees one point '
                        'of the lit strip, and that point moves with Det_Th, so a narrow (Gaussian) beam lights a '
                        'column differently from frame to frame, which one factor per column cannot follow; it '
                        'also gives the beam\'s position and width on the sample; "physical" computes it from the '
                        'geometry and the beam instead of fitting a factor per column: rays through each column\'s '
                        'pixel and the S4 opening to the footprint, lit by a Gaussian beam (its centre and vertical '
                        'FWHM fitted unless typed below, e.g. from a half-cut), clipped by S1; it includes the area '
                        'correction and keeps each level\'s absolute scale; "physical+fit" adds to it one factor per '
                        'column (mean 1) for what physics misses, keeping the physical scale; "none" takes it as flat. '
                        'Every kind fits each scan\'s scale with it, so a scale between scans is not absorbed (P42). '
                        'Default "fit": the frames of a level agree best with it on all the data measured '
                        '(2026-11-20; the consistency chi2 is shown with the levels).')
        bfw=spin('gidBeamFwhmSpinBox',0,5000,gp.beam_fwhm_um,'Response "physical": the beam\'s vertical FWHM in '
                 'micrometres, e.g. from a half-cut (sh) scan. 0: fitted to the data of each Qz level.',dbl=True)
        bcf=QCheckBox('fit',g)
        bcf.setObjectName('gidBeamCentreFitCheckBox')
        bcf.setChecked(gp.beam_centre_mm is None)
        bcf.setToolTip('Response "physical": fit the beam centre to the data of each Qz level (the sample height '
                       'drifts, so it can differ between levels). Untick to type it.')
        bce=spin('gidBeamCentreSpinBox',-200,200,0.0 if gp.beam_centre_mm is None else gp.beam_centre_mm,
                 'Response "physical": where the beam\'s centre meets the surface, mm along the beam from the sample '
                 'centre, positive downstream. A height offset dz moves it by dz / sin(alpha).',dbl=True)
        bhw=spin('gidBeamHFwhmSpinBox',0,20,gp.beam_h_fwhm_mm,'Response "physical": the beam\'s horizontal FWHM, mm '
                 '(about 1 mm: owner\'s estimate). A column\'s line of sight crosses the beam\'s width at 2theta, '
                 'which spreads the part of the footprint it sees and makes the footprint\'s ends ramps.',dbl=True)
        joins=QCheckBox('Apply join factors',g)
        joins.setObjectName('gidApplyJoinsCheckBox')
        joins.setChecked(gp.apply_joins)
        joins.setToolTip('On: the scans of a level and the Qz levels are scaled by the factors fitted in their '
                         'overlaps. Off: the factors are fitted and shown in the table (marked "not applied") but the '
                         'data stay as collected, normalised by the monitor and absorbers only, so any disagreement '
                         'stays visible. Pinhole geometry only.')
        foot=QComboBox(g)
        foot.setObjectName('gidFootprintComboBox')
        foot.addItems(['exact','IDL'])
        foot.setCurrentIndex(0 if gp.footprint=='exact' else 1)
        foot.setToolTip('Which columns of each frame see the lit strip of sample (the footprint) through the S4 '
                        'pinhole. "exact": traced ray by ray, only columns that see it through the whole S4 opening '
                        '(partly lit columns at the edges change with Det_Th, which a column response cannot follow); '
                        '"IDL": the window of the IDL code (PD_PIN_RANGE), the right width but centred on the '
                        'direct-beam column, which drops a few lit columns at the high-2theta edge (P39). '
                        'The S5 slits limit the columns too.')
        trans=QComboBox(g)
        trans.setObjectName('gidTransverseComboBox')
        trans.addItems(['common','all'])
        trans.setCurrentIndex(0 if gp.transverse=='intersection' else 1)
        trans.setToolTip('2theta range of a map joined from several Qz levels: "common", the range every level '
                         'covers (as IDL IMG_JOIN); "all", every level\'s range, empty where a level has no data. '
                         'The join factor always uses the common range only.')
        minf=spin('gidMinFramesSpinBox',1,50,gp.min_frames,'2theta bins seen by fewer frames than this are left out: '
                  'at the map edges a bin is seen only through the weakest columns of one or two frames.')
        arm=QCheckBox('Arm correction',g)
        arm.setObjectName('gidArmCheckBox')
        arm.setChecked(gp.arm_correction)
        arm.setToolTip('Vertical distance = sample-detector + g_l3 (1/cos beta0 - 1): the horizontal arm distance as '
                       'a path when the arm is raised (IDL). Pinhole mode only.')
        fit=QPushButton('Fit',g)
        fit.setObjectName('gidFitDistancePushButton')
        fit.setToolTip('Calibrate the S4-detector distance from single frames (owner, 2026-11-21): the strongest peak '
                       'of the first Qz level is fitted in every frame that holds it, without patching; a wrong distance '
                       'makes it drift with the column that sees it, so the distance where the frames agree best is '
                       'the calibrated one. Filled in above when reliable (enough frames, they agree, no drift left); '
                       'otherwise only shown, with the reason. lss_core.pinhole.calibrate_distance.')
        fitl=QLabel('',g)
        fitl.setObjectName('gidFitLabel')
        prow=QHBoxLayout()
        prow.addWidget(pdist)
        prow.addWidget(fit)
        prow.addWidget(fitl)
        form.addRow(pin)
        form.addRow('S4-detector (mm)',prow)
        form.addRow('Column response',resp)
        form.addRow('Footprint window',foot)
        brow=QHBoxLayout()
        for w_ in (QLabel('FWHM um',g),bfw,QLabel('centre mm',g),bce,bcf,QLabel('horizontal mm',g),bhw):
            brow.addWidget(w_)
        form.addRow('Beam (physical)',brow)
        form.addRow(joins)
        form.addRow('Frames per bin, at least',minf)
        form.addRow('2theta range across levels',trans)
        form.addRow(arm)
        lay.addWidget(g)
        levels=QLabel('',d)
        levels.setObjectName('gidLevelsLabel')
        levels.setToolTip('Qz levels of the last patch: scans, frames, detector-angle range (degrees)')
        lay.addWidget(levels)
        t=QTableWidget(0,7,d)
        t.setObjectName('gidJoinTable')
        t.setHorizontalHeaderLabels(['join','direction','from','to','points','factor','chi2/dof'])
        tips=['Which data were joined: scans of one Qz level side by side (horizontal), or Qz levels (vertical)',
              'horizontal: along 2theta (degrees); vertical: along beta (degrees)',
              'Start of the overlap used for the scale factor (degrees)','End of the overlap (degrees)',
              'Overlap points used in the fit','Scale factor applied to the second part, +/- its fitted error',
              'Scatter of the overlap ratios about the factor; near 1 when the error bars describe it']
        for c,tip in enumerate(tips):
            t.horizontalHeaderItem(c).setToolTip(tip)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        lay.addWidget(t)
        buttons=QHBoxLayout()
        live=QCheckBox('Update the map on every change',d)
        live.setObjectName('gidLiveCheckBox')
        live.setChecked(True)
        live.setToolTip('On: every change of a setting above patches the selected frames again (after a short pause), '
                        'so the effect of each method shows at once in the map and in the join table. Off: press '
                        'Patch.')
        timer=QTimer(d)
        timer.setSingleShot(True)
        timer.setInterval(400)
        timer.timeout.connect(self.gidWorksheetPatch)
        again=QPushButton('Patch',d)
        again.setObjectName('gidPatchPushButton')
        again.setToolTip('Patch the selected frames again with these settings')
        reset=QPushButton('Defaults',d)
        reset.setObjectName('gidDefaultsPushButton')
        reset.setToolTip('Back to the values the program always used')
        close=QPushButton('Close',d)
        close.setObjectName('gidClosePushButton')
        buttons.addWidget(live)
        for b in (again,reset,close):
            buttons.addWidget(b)
        lay.addLayout(buttons)

        ready=[False]                               # no live patch while the dialog is being built

        def apply(*_):
            self.ui.pilHSlitLineEdit.setText(str(cols.value()))
            self.gidParams=gidmod.GIDParams(columns=cols.value(),row_min=rmin.value(),row_max=rmax.value(),
                                            qz_decimals=qzd.value(),dth_decimals=dthd.value(),
                                            area_correction=area.isChecked(),hard_slit_offset_mm=hard.value(),
                                            polarisation=pol.isChecked(),vjoin_kind=kind.currentText(),
                                            pinhole=pin.isChecked(),pinhole_distance_mm=pdist.value(),
                                            response=resp.currentText(),arm_correction=arm.isChecked(),
                                            min_frames=minf.value(),footprint='exact' if foot.currentIndex()==0 else 'idl',
                                            beam_fwhm_um=bfw.value(),beam_h_fwhm_mm=bhw.value(),apply_joins=joins.isChecked(),
                                            beam_centre_mm=None if bcf.isChecked() else bce.value(),
                                            transverse='intersection' if trans.currentIndex()==0 else 'union')
            hard.setEnabled(area.isChecked())
            for w in (pdist,resp,arm,fit,minf,trans,foot,joins):
                w.setEnabled(pin.isChecked())
            physical=pin.isChecked() and resp.currentText().startswith('physical')
            for w in (bfw,bcf,bhw):
                w.setEnabled(physical)
            bce.setEnabled(physical and not bcf.isChecked())
            if ready[0] and live.isChecked() and getattr(self,'gidLevels',None) and \
                    len(getattr(self,'selectedPilFramesNums',[]))>0:
                timer.start()                       # patch again shortly (one patch for a burst of changes)
            cols.setEnabled(not pin.isChecked())

        def defaults():
            dflt=gidmod.GIDParams()
            for w,v in ((cols,dflt.columns),(rmin,dflt.row_min),(rmax,dflt.row_max),(qzd,dflt.qz_decimals),
                        (dthd,dflt.dth_decimals),(hard,dflt.hard_slit_offset_mm)):
                w.setValue(v)
            area.setChecked(dflt.area_correction)
            pol.setChecked(dflt.polarisation)
            kind.setCurrentText(dflt.vjoin_kind)
            pin.setChecked(dflt.pinhole)
            pdist.setValue(dflt.pinhole_distance_mm)
            resp.setCurrentText(dflt.response)
            arm.setChecked(dflt.arm_correction)
            minf.setValue(dflt.min_frames)
            trans.setCurrentIndex(0)
            foot.setCurrentIndex(0 if dflt.footprint=='exact' else 1)
            bfw.setValue(dflt.beam_fwhm_um)
            bhw.setValue(dflt.beam_h_fwhm_mm)
            bcf.setChecked(dflt.beam_centre_mm is None)
            bce.setValue(0.0)
            joins.setChecked(dflt.apply_joins)
            apply()

        def fitdist():
            r=self.gidFitPinholeDistance()
            if r:
                fitl.setText('%.1f +/- %.1f%s' % (r.distance_mm,r.error_mm,'' if r.reliable else ' (not used)'))
                fitl.setToolTip('Single frames: peak at 2theta %.3f deg in %d frames (rows %d-%d), frames agree chi2/dof '
                                '%.2f, drift %.4f deg/deg; at the header value (%.1f mm): chi2/dof %.2f, drift %.4f. %s'
                                % (r.peak_deg,r.frames,r.rows[0],r.rows[1],r.chi2_dof,r.drift,r.header_mm,
                                   r.chi2_dof_header,r.drift_header,
                                   'Filled in above.' if r.reliable else 'Not used: %s.' % r.why))
                if r.reliable:
                    pdist.setValue(round(r.distance_mm,1))
        for w in (cols,rmin,rmax,qzd,dthd,hard):
            w.valueChanged.connect(apply)
        area.toggled.connect(apply)
        pol.toggled.connect(apply)
        kind.currentIndexChanged.connect(apply)
        pdist.valueChanged.connect(apply)
        minf.valueChanged.connect(apply)
        trans.currentIndexChanged.connect(apply)
        pin.toggled.connect(apply)
        arm.toggled.connect(apply)
        resp.currentIndexChanged.connect(apply)
        foot.currentIndexChanged.connect(apply)
        for w_ in (bfw,bce,bhw):
            w_.valueChanged.connect(apply)
        bcf.toggled.connect(apply)
        joins.toggled.connect(apply)
        fit.clicked.connect(fitdist)
        apply()
        ready[0]=True
        again.clicked.connect(self.gidWorksheetPatch)
        reset.clicked.connect(defaults)
        close.clicked.connect(d.close)
        d.gidColumnsSpinBox,d.gidRowMinSpinBox,d.gidRowMaxSpinBox=cols,rmin,rmax
        d.gidQzDecimalsSpinBox,d.gidDthDecimalsSpinBox,d.gidAreaCheckBox=qzd,dthd,area
        d.gidHardSlitSpinBox,d.gidPolCheckBox,d.gidVJoinKindComboBox=hard,pol,kind
        d.gidLevelsLabel,d.gidJoinTable=levels,t
        d.gidPinholeCheckBox,d.gidPinholeDistSpinBox,d.gidResponseComboBox,d.gidArmCheckBox=pin,pdist,resp,arm
        d.gidFitDistancePushButton,d.gidFitLabel=fit,fitl
        d.gidTransverseComboBox,d.gidMinFramesSpinBox=trans,minf
        d.gidFootprintComboBox=foot
        d.gidBeamFwhmSpinBox,d.gidBeamCentreSpinBox,d.gidBeamCentreFitCheckBox=bfw,bce,bcf
        d.gidBeamHFwhmSpinBox,d.gidApplyJoinsCheckBox=bhw,joins
        d.gidLiveCheckBox,d.gidLiveTimer=live,timer
        return d

    def gidWorksheetPatch(self):
        if self.det!='Pilatus' or len(getattr(self,'selectedPilFramesNums',[]))==0:
            self.messageBox('Please select the Pilatus frames of the GID scans first.')
            return
        if self.gidParams.row_min>=self.gidParams.row_max:
            self.messageBox('The first row must be below the last row.')
            return
        self.pilGIDRelax=getattr(self,'pilGIDRelax',0)
        self.pilGIDpatchData()

    def gidWorksheetResults(self):
        """Fill the worksheet with the last patch's levels and joins."""
        from PyQt5.QtWidgets import QTableWidgetItem
        d=self.gidWorksheet
        if d is None:
            return
        text='; '.join('%s: S %s, %d frames, %.3f-%.3f' % (n,listText(k),f,lo,hi)
                       for n,k,f,lo,hi in self.gidLevels) or 'not patched yet'
        tip=''
        info=(getattr(self,'gidPinholeInfo',None) or [None])[0] if self.gidParams.pinhole else None
        if info and 'two_theta_resolution_deg' in info:
            text+='\n2theta resolution %.3f deg (%.1f columns)' % (info['two_theta_resolution_deg'],
                                                               info['two_theta_resolution_columns'])
            tip=('2theta resolution: the full width of the in-plane angles one column accepts through the S4 '
                 'opening (%.2f mm) and its own pixel, at the direct-beam column (lss_core.pinhole.'
                 'column_acceptance). The map\'s bins are %.4f deg wide, one column; the resolution, not the bin, '
                 'limits how sharp a peak can be.' % (info['s4_mm'],info['step_deg']))
            cons=[lv.get('consistency_chi2') for lv in (getattr(self,'gidPinholeInfo',None) or [])]
            if cons and all(c is not None for c in cons):
                text+='\nframes agree: chi2/dof %s' % ' / '.join('%.2f' % c for c in cons)
                tip+=(' Frames agree: for each Qz level, how well its frames match the map made from them once the '
                      'column response and scan factors are applied (Poisson chi2 per degree of freedom of the '
                      'rows-summed counts of each frame and column; 1 = counting noise only). Lower is better; '
                      'use it to compare responses (lss_core.pinhole.frame_consistency).')
            phys=info.get('physical')
            if phys:
                text+='; beam: centre %.1f mm, vertical FWHM %.0f um%s (response "physical", chi2/dof %.2f)' % (
                    phys['centre_mm'],phys['fwhm_um'],' (fitted)' if phys['fitted'] else '',phys['chi2_dof'])
                tip+=(' Physical response: the beam that best explains the data (or the one typed), with each column\'s '
                      'light from the geometry; x = 0 at the sample centre, positive downstream; along the beam the lit '
                      'strip is FWHM / sin(alpha) = %.1f mm long. Other levels: in the log.' % phys['fwhm_mm'])
            beam=info.get('beam')
            if beam and np.isfinite(beam['centre_mm']):
                text+='; beam on the sample: centre %.1f mm, FWHM %.1f mm (response "beam")' % (beam['centre_mm'],beam['fwhm_mm'])
                tip+=(' Beam: the response along the beam axis, x = 0 at the sample centre, positive downstream; '
                      'its centre and FWHM are where and how long the lit strip is.')
        d.gidLevelsLabel.setText(text)
        d.gidLevelsLabel.setToolTip(tip)
        t=d.gidJoinTable
        t.setRowCount(len(self.gidJoinLog))
        for r,j in enumerate(self.gidJoinLog):
            vals=[j['label'],j['kind'],'%.3f' % j['x_from'],'%.3f' % j['x_to'],'%d' % j['points'],
                  '%.4g +/- %.2g%s' % (j['factor'],j['error'],'' if j.get('applied',True) else ' (not applied)'),
                  '%.2f' % j['chi2']]
            for c,v in enumerate(vals):
                t.setItem(r,c,QTableWidgetItem(v))
        t.resizeColumnsToContents()

    def setGIDFormFactor(self):
        Dialog=QDialog(self)                
        self.uipdformfac=uic.loadUi(resource('pdformfac.ui'), Dialog)
        self.uipdformfac.show()
        # self.connect(self.uipdformfac.updatePushButton, SIGNAL('clicked()'),self.updateFormFactor)  #update gid plot with formfactor
        self.uipdformfac.updatePushButton.clicked.connect(self.updateFormFactor)
        # self.connect(self.uipdformfac.okPushButton, SIGNAL('clicked()'),self.presetFormFactor) #preset formfactor
        self.uipdformfac.okPushButton.clicked.connect(self.presetFormFactor)
        
    def readFormFactor(self):
        """(r, rxy, rz) from the form-factor dialog, or None after telling the
        user what is wrong. Zero means "not used"."""
        ui=self.uipdformfac
        sph=ui.sphCheckBox.checkState()!=0
        ell=ui.ellCheckBox.checkState()!=0
        if sph and ell:
            self.messageBox('Both "Sphere" and "Ellipsoid" are selected; please uncheck one of them.')
            return None
        try:
            if sph:
                r=float(ui.sphLineEdit.text())
                if not r>0:
                    raise ValueError
                return (r,0,0)
            if ell:
                rxy=float(ui.ellXYLineEdit.text())
                rz=float(ui.ellZLineEdit.text())
                if not (rxy>0 and rz>0):
                    raise ValueError
                return (0,rxy,rz)
        except ValueError:
            self.messageBox('The radius of the '+('sphere' if sph else 'ellipsoid')+' must be a positive number.')
            return None
        return (0,0,0)

    def presetFormFactor(self):
        radii=self.readFormFactor()
        if radii is None:
            return
        self.formfactor_r,self.formfactor_rxy,self.formfactor_rz=radii
        self.uipdformfac.close()

    def updateFormFactor(self):
        if getattr(self,'pilGIDData',None) is None or self.pilGIDshow==0:
            self.messageBox('There is no GID map yet; please do the GID patch first.')
            return
        radii=self.readFormFactor()
        if radii is None:
            return
        self.formfactor_r,self.formfactor_rxy,self.formfactor_rz=radii
        self.pilGIDPlot()

    def pilGIDpatchData(self):
        if self.pilGIDshow==0:
            # self.disconnect(self.ui.pilAxesComboBox, SIGNAL('currentIndexChanged(int)'), self.update2dPlots)
            self.ui.pilAxesComboBox.currentIndexChanged.disconnect(self.update2dPlots)
            if self.ui.pilAxesComboBox.currentIndex()==0:
                self.ui.pilAxesComboBox.setCurrentIndex(2)
            # self.connect(self.ui.pilAxesComboBox, SIGNAL('currentIndexChanged(int)'), self.update2dPlots)
            self.ui.pilAxesComboBox.currentIndexChanged.connect(self.update2dPlots)
        self.pilGIDshow=1
        self.pilGISAXSshow=0
        self.ui.pilMplWidget.canvas.fig.clf()
        gp=self.gidEffectiveParams()
        self.gidJoinLog=[]
        self.gidLevels=[]
        frames=self.gidFrames()
        try:
            if gp.pinhole:
                patch,self.gidLevels,self.gidPinholeInfo,self.gidJoinInfo=gidmod.pinhole_patch(frames,gp,log=self.gidJoinLog)
            else:
                self.pilxleft=self.xcenter-(gp.columns-1)/2      # also read by the GID line cuts
                self.pilxright=self.xcenter+(gp.columns-1)/2
                self.absfac=self.absorberModel()
                patch,self.gidLevels=gidmod.legacy_patch(frames,gp,self.pilatus,log=self.gidJoinLog,warn=self.messageBox)
        except gidmod.GIDError as e:
            self.messageBox(str(e))
            return
        self.pilPatchData=patch
        self.gidFinishMap()

    def gidEffectiveParams(self):
        """The worksheet's settings with the H slit field as the column count
        (the field can be typed without the worksheet)."""
        import dataclasses
        try:
            cols=float(self.ui.pilHSlitLineEdit.text())
        except ValueError:
            cols=self.gidParams.columns
        return dataclasses.replace(self.gidParams,columns=int(cols) if cols==int(cols) else cols)

    def gidFrames(self):
        """lss_core.gid.GIDFrame for each selected frame, in selection order."""
        out=[]
        for j,i in enumerate(self.selectedPilFramesNums):
            scan=self.pilScanNum[i]
            out.append(gidmod.GIDFrame(self.pilData[i],self.pilErrorData[i],self.pilMonc[i],self.pil_AbsNum[i],scan,
                                       self.pilFileQzs[i],self.pilAlpha[i],self.pilTrueAlpha[i],self.pil_Dth[i],
                                       self.pil_Wavelength[i],(self.xcenter[j],self.ycenter[j]),self.pil_Dist[i],
                                       self.pil_PDist[i],self.pil_Sh[i],
                                       (self.pil_S1h[i],self.pil_S1v[i],self.pil_S4h[i],self.pil_S5h[i]),
                                       self.specPar.get(scan,{})))
        return out

    def gidFinishMap(self):
        """Map arrays, colour limits and the plot from self.pilPatchData
        (the end of the GID patch, both geometries)."""
        self.pilGIDXAxs,self.pilGIDYAxs,self.pilGIDData,self.pilGIDDataErr=gidmod.map_arrays(self.pilPatchData)
        self.gidShowMap()

    def gidShowMap(self):
        """Colour limits, the plot and the worksheet's results for the map arrays."""
        self.imageMax=np.nanmax(self.pilGIDData)     # nan-aware: the pinhole 'all' range leaves cells empty
        self.imageMin=np.nanmin(self.pilGIDData[np.nonzero(np.nan_to_num(self.pilGIDData))])
        self.ui.pilMaxLineEdit.setText(str(self.imageMax)) #set the vmax/vmin in the lineedit and slider 
        self.ui.pilMinLineEdit.setText(str(self.imageMin))
        self.ui.pilMaxHorizontalSlider.setValue(int(float(self.ui.pilMaxLineEdit.text())*100/(self.imageMax-self.imageMin)))
        self.ui.pilMinHorizontalSlider.setValue(int(float(self.ui.pilMinLineEdit.text())*100/(self.imageMax-self.imageMin)))
        self.pilGIDPlot()   # go to plot function
        if self.gidWorksheet is not None and self.gidWorksheet.isVisible():
            self.gidWorksheetResults()

    def gidProducts(self,axes):
        """What is plotted and saved for the current map in ``axes``
        (lss_core.gid.products).

        The map regridded to Q is kept (G1, docs/gui/image_display.md;
        2026-11-23): regridding was 70-77 % of every redraw of the map, also
        when only the colour map, the scale or the limits changed. The key
        is the map's content (a hash of its four arrays, a few ms) with the
        angle, wavelength and Relax, so a patch, or a live remake that gives
        the same map in new arrays, is regridded only when the map changed.
        The kept arrays are read-only."""
        import hashlib
        args=(self.pilGIDXAxs,self.pilGIDYAxs,self.pilGIDData,self.pilGIDDataErr)
        relax=getattr(self,'pilGIDRelax',0)!=0
        if axes!='Q':
            return gidmod.products(*args,axes,self.truealpha[0],self.wavelength[0],relax=relax)
        h=hashlib.blake2b(digest_size=16)
        for a in args:
            a=np.ascontiguousarray(a)
            h.update(repr((a.shape,a.dtype.str)).encode())
            h.update(a.data)
        key=(h.hexdigest(),float(self.truealpha[0]),float(self.wavelength[0]),relax)
        kept=getattr(self,'gidProductsKept',None)
        if kept is not None and kept[0]==key:
            return kept[1]
        prod=gidmod.products(*args,axes,self.truealpha[0],self.wavelength[0],relax=relax)
        for v in list(prod.values())+list(prod['vc'].values()):
            if isinstance(v,np.ndarray):
                v.setflags(write=False)
        self.gidProductsKept=(key,prod)
        return prod

    def gidFitPinholeDistance(self):
        """S4 -> detector distance calibrated from single frames of the first
        Qz level (lss_core.pinhole.calibrate_distance); None on failure."""
        if self.det!='Pilatus' or len(getattr(self,'selectedPilFramesNums',[]))<6:
            self.messageBox('Select the frames of a GID scan (at least 6) first.')
            return None
        gp=dataclasses.replace(self.gidParams,pinhole_distance_mm=0.0)        # start from the header value
        try:
            level=gidmod.pinhole_frames(self.gidFrames(),gp)[0]
            return pinhole.calibrate_distance(level)
        except (ValueError,IndexError,KeyError) as e:
            self.messageBox('No distance calibration: %s.' % e)
            return None

    def calArea(self, areainfo, dth):
        """Footprint fraction (lss_core.gid.cal_area) with the H slit field."""
        return gidmod.cal_area(areainfo,dth,float(self.ui.pilHSlitLineEdit.text()),self.gidParams.hard_slit_offset_mm)

    def pilGIDPlot(self):
        self.ui.pilMplWidget.canvas.fig.clf()
        aspect=str(self.ui.pilAspectComboBox.currentText())
        vmax=float(self.ui.pilMaxLineEdit.text())
        vmin=float(self.ui.pilMinLineEdit.text())
        cmap=str(self.ui.pilCMapComboBox.currentText())
        #self.gidax=self.ui.pilMplWidget.canvas.fig.add_subplot(1,1,1)
        gs=gridspec.GridSpec(5,12)
        self.gidax=self.ui.pilMplWidget.canvas.fig.add_subplot(gs[0:3,3:7])  #for 2D data
        self.gidax_h=self.ui.pilMplWidget.canvas.fig.add_subplot(gs[3:5,3:7]) #for h-cut data
        self.gidax_v=self.ui.pilMplWidget.canvas.fig.add_subplot(gs[0:3,7:9])  #for v-cut data
        self.gidax_vc=self.ui.pilMplWidget.canvas.fig.add_subplot(gs[3:5,7:9])  #for vslide-cut data
        alpha=self.truealpha[0]  #get alpha
        k0=2*np.pi/self.wavelength[0] #get wavevector    
        
        if str(self.ui.pilAxesComboBox.currentText())=='Angles':   
            self.pilGIDxlabel=r'$2\theta$'+' '+r'$[\deg]$'
            self.pilGIDylabel=r'$\beta$'+' '+r'$[\deg]$'
            fint=interp1d(self.pilGIDXAxs[0], self.pilGIDData, kind='linear')   # interpolate the data along x-axis
            newpilGIDXAxis=np.linspace(self.pilGIDXAxs[0][0],self.pilGIDXAxs[0][-1],len(self.pilGIDXAxs[0])*10)
            inter_pilGIDData=fint(newpilGIDXAxis)
            self.Zdata=inter_pilGIDData
            self.extent=[self.pilGIDXAxs[0][0],self.pilGIDXAxs[0][-1],self.pilGIDYAxs[0][0],self.pilGIDYAxs[-1][-1]]
            if self.ui.pilLogIntCheckBox.checkState()!=0:
                self.gid_p=self.gidax.imshow(np.log10(inter_pilGIDData),interpolation='bicubic',extent=self.extent,vmax=np.log10(vmax),vmin=np.log10(vmin),cmap=cmap,aspect=aspect,origin='lower')            
            else:
                self.gid_p=self.gidax.imshow(inter_pilGIDData,interpolation='bicubic',extent=self.extent,vmax=vmax,vmin=vmin,cmap=cmap,aspect=aspect,origin='lower') 
           # self.ui.pilMplWidget.canvas.fig.colorbar(self.gid_p)
            #get the h-cut data and label
            prod=self.gidProducts('Angles')
            self.gid_h,self.gid_v,self.gid_vc=prod['h'],prod['v'],prod['vc']
            self.gidax_h.set_xlabel(r'$2\theta$'+' '+r'$[\deg]$')
            self.gidax_h.set_title('Integrated over '+r'$\beta$')
            #get the v-cut data
            self.gidax_v.set_ylabel(r'$\beta$'+' '+r'$[\deg]$')
            self.gidax_v.set_title('Integrated over '+r'$2\theta$')
            #get the v-slice-cut data
            self.gidax_vc.set_title(r'$\beta$'+'-binned')
            self.gidax_vc.set_xlabel(r'$2\theta$'+' '+r'$[\deg]$')
            
        
        if str(self.ui.pilAxesComboBox.currentText())=='Q':
            self.pilGIDxlabel=r'$Q_{xy}$'+' '+r'$[\AA^{-1}]$'
            self.pilGIDylabel=r'$Q_z$'+' '+r'$[\AA^{-1}]$'
            prod=self.gidProducts('Q')
            self.pilGIDXAxs_Q,self.pilGIDYAxs_Q,self.pilGIDData_Q,self.pilGIDDataErr_Q=prod['x'],prod['y'],prod['data'],prod['err']
            self.gid_h,self.gid_v,self.gid_vc=prod['h'],prod['v'],prod['vc']
            fint=interp1d(self.pilGIDXAxs_Q[0], self.pilGIDData_Q, kind='linear')   # interpolate the data along x-axis
            newpilGIDXAxis=np.linspace(self.pilGIDXAxs_Q[0][0],self.pilGIDXAxs_Q[0][-1],len(self.pilGIDXAxs_Q[0])*10)
            inter_pilGIDData_Q=fint(newpilGIDXAxis)
            self.Zdata=inter_pilGIDData_Q
            self.extent=[self.pilGIDXAxs_Q[0][0],self.pilGIDXAxs_Q[0][-1],self.pilGIDYAxs_Q[0][0],self.pilGIDYAxs_Q[-1][-1]]
            if self.ui.pilLogIntCheckBox.checkState()!=0:
                self.gid_p=self.gidax.imshow(np.log10(inter_pilGIDData_Q),interpolation='bicubic',extent=self.extent,vmax=np.log10(vmax),vmin=np.log10(vmin),cmap=cmap,aspect=aspect,origin='lower')            
            else:
                self.gid_p=self.gidax.imshow(inter_pilGIDData_Q,interpolation='bicubic',extent=self.extent,vmax=vmax,vmin=vmin,cmap=cmap,aspect=aspect,origin='lower')            
           
            if self.formfactor_r>0:  #for the sphere ff
                self.gidax.autoscale(False)
                qxymin=self.pilGIDXAxs_Q[0][np.where(self.pilGIDXAxs_Q[0]>0)[0][0]]
                qzmin=self.pilGIDYAxs_Q[:,0][np.where(self.pilGIDYAxs_Q[:,0]>0)[0][0]]
                qmin=np.sqrt(qxymin**2+qzmin**2)  # get min q in the 2d plot
                qmax=np.sqrt(self.pilGIDXAxs_Q[0][-1]**2+self.pilGIDYAxs_Q[-1][0]**2) # get max q in the 2d plot
                x=Symbol('x')
                anmin=solve((x-qmin*self.formfactor_r)*(x**2-8/3)-2,x)
                anmax=solve((x-qmax*self.formfactor_r)*(x**2-8/3)-2,x)                
                nmin=anmin[-1]/np.pi-0.5     #get min n based on radius and min q
                nmax=anmax[-1]/np.pi-0.5     #get min n based on radius and min q
               # print int(nmin+1), int(nmax+1),anmin,anmax
                if int(nmin)==int(nmax):
                    self.messageBox('Warning: not form factor minimun in the plot range.')
                for i in range(int(nmin+1),int(nmax+1)):                 # get n range
                    totq=((i+0.5)*np.pi-2/((i+0.5)**2*np.pi**2-8/3))/self.formfactor_r #get total q for n
                    plotqxy=np.linspace(self.pilGIDXAxs_Q[0][0],totq,100)   # get the x-axis for formfactor for ith order
                    plotqz=np.sqrt(totq**2-plotqxy**2)       # get the y-axis for formfactor for ith order
                    self.gidax.plot(plotqxy, plotqz, 'w-', linewidth=1.5)
            if self.formfactor_rxy>0 and self.formfactor_rz>0: #for ellipsoid ff
                self.gidax.autoscale(False)
                qxymin=self.pilGIDXAxs_Q[0][np.where(self.pilGIDXAxs_Q[0]>0)[0][0]]
                qzmin=self.pilGIDYAxs_Q[:,0][np.where(self.pilGIDYAxs_Q[:,0]>0)[0][0]]
                qmin=np.sqrt(qxymin**2*self.formfactor_rxy**2+qzmin**2*self.formfactor_rz**2) #get min q for ellipsoid
                qmax=np.sqrt(self.pilGIDXAxs_Q[0][-1]**2*self.formfactor_rxy**2+self.pilGIDYAxs_Q[-1][0]**2*self.formfactor_rz**2) #get max q for ellipsoid
                x=Symbol('x')
                anmin=solve((x-qmin)*(x**2-8/3)-2,x)
                anmax=solve((x-qmax)*(x**2-8/3)-2,x)                
                nmin=anmin[-1]/np.pi-0.5     #get min n based on radius and min q
                nmax=anmax[-1]/np.pi-0.5     #get min n based on radius and min q
                #print int(nmin+1),int(nmax+1),anmin,anmax
                if int(nmin)==int(nmax):
                    self.messageBox('Warning: not form factor minimun in the plot range.')
                for i in range(int(nmin+1),int(nmax+1)):                 # get n range
                    totq=(i+0.5)*np.pi-2/((i+0.5)**2*np.pi**2-8/3) #get total qr for n
                    plotqxy=np.linspace(self.pilGIDXAxs_Q[0][0],totq/self.formfactor_rxy,100)   # get the x-axis for formfactor for ith order
                    plotqz=np.nan_to_num(np.sqrt((totq**2-plotqxy**2*self.formfactor_rxy**2)/self.formfactor_rz**2))       # get the y-axis for formfactor for ith order
                    self.gidax.plot(plotqxy, plotqz, 'w-', linewidth=1.5)
             #get the h-cut data and label
            self.gidax_h.set_xlabel(r'$Q_{xy}$'+' '+r'$[\AA^{-1}]$')
            self.gidax_h.set_title('Integrated over '+r'$Q_z$')
            #get the v-cut data
            self.gidax_v.set_ylabel(r'$Q_z$'+' '+r'$[\AA^{-1}]$')
            self.gidax_v.set_title('Integrated over '+r'$Q_{xy}$')
            #get the v-slice-cut data
            self.gidax_vc.set_title(r'$Q_z$'+'-binned')
            self.gidax_vc.set_xlabel(r'$Q_{xy}$ '+r'$[\AA^{-1}]$')
        
        self.gidax.set_aspect(aspect)
        self.gidax.set_xlabel(self.pilGIDxlabel)
        self.gidax.set_ylabel(self.pilGIDylabel)
        self.gidax.set_title('Two-dimensional Data')
        self.gidax.format_coord=self.format_pil_coord
        vc_max=max(np.max(self.gid_vc[0][:,1]),np.max(self.gid_vc[1][:,1]),np.max(self.gid_vc[2][:,1]),np.max(self.gid_vc[3][:,1]))
        #self.gidax_v.errorbar(self.gid_v[:,1]/np.max(self.gid_v[:,1]),self.gid_v[:,0],xerr=self.gid_v[:,2]/np.max(self.gid_v[:,1]),fmt='b-')
        self.gidax_v.errorbar(self.gid_v[:,1],self.gid_v[:,0],xerr=self.gid_v[:,2],fmt='b-')
        #self.gidax_h.errorbar(self.gid_h[:,0],self.gid_h[:,1]/np.max(self.gid_h[:,1]),self.gid_h[:,2]/np.max(self.gid_h[:,1]),fmt='b-')
        self.gidax_h.errorbar(self.gid_h[:,0],self.gid_h[:,1],self.gid_h[:,2],fmt='b-')
        for i in range(4):
            #self.gidax_vc.errorbar(self.gid_vc[i][:,0], (self.gid_vc[i][:,1]+vc_max*i)/vc_max/4, self.gid_vc[i][:,2]/vc_max/4, fmt='b-')
            self.gidax_vc.errorbar(self.gid_vc[i][:,0], self.gid_vc[i][:,1]+vc_max*i, self.gid_vc[i][:,2], fmt='b-')
        for i in range(3):
            #self.gidax_vc.plot(self.gid_vc[i][:,0],(i+1)*0.25*np.ones_like(self.gid_vc[i]),'r--')
            self.gidax_vc.plot(self.gid_vc[i][:,0],(i+1)*vc_max*np.ones_like(self.gid_vc[i]),'r--')
        self.gidax_h.set_ylabel('Intensity (a.u.)')
        self.gidax_v.set_xlabel('Intensity (a.u.)')
        self.gidax_vc.set_ylabel('Intensity (a.u.)')
        self.gidax_v.yaxis.tick_right()
        self.gidax_v.yaxis.set_label_position("right")
        self.gidax_h.set_xlim(self.gid_h[:,0][0],self.gid_h[:,0][-1])
        self.gidax_vc.set_xlim(self.gid_h[:,0][0],self.gid_h[:,0][-1])
        self.gidax_v.set_ylim(self.gid_v[:,0][0],self.gid_v[:,0][-1])
        if self.ui.pilLogIntCheckBox.checkState()!=0:
            self.gidax_h.set_yscale('log')
            self.gidax_v.set_xscale('log')
        else:
            self.gidax_h.set_yscale('linear')
            self.gidax_v.set_xscale('linear')
        #    self.gidax_v.xaxis.set_ticks(np.linspace(0,1,3))
        #    self.gidax_h.yaxis.set_ticks(np.linspace(0,1,3))
        #self.gidax_vc.xaxis.set_ticks(np.linspace(float(format(self.gid_vc[0][:,0][0],'.2g')),float(format(self.gid_vc[0][:,0][-1],'.2g')),3))
        #self.gidax_v.locator_params(axis = 'x', nbins = 4)
        self.gidax_vc.locator_params(axis = 'x', nbins = 4)
        self.ui.pilMplWidget.canvas.fig.suptitle('File: '+self.specFileName+' S# '+listText(np.sort(self.selectedScanNums)))
        temp2d=make_axes_locatable(self.gidax)
        cax2d=temp2d.append_axes("right", size="5%",pad=0.05,)
        #cax2d = self.ui.pilMplWidget.canvas.fig.add_axes([0.565, 0.475, 0.008, 0.425]) 
        self.ui.pilMplWidget.canvas.fig.colorbar(self.gid_p,cax=cax2d,format="%.1e")
        
        self.ui.pilMplWidget.canvas.fig.tight_layout()
        self.ui.pilMplWidget.canvas.fig.subplots_adjust(top=0.9)
        self.ui.pilMplWidget.canvas.draw()
        self.command=str(self.ui.gidComboBox.currentText())+', scans=['+listText(np.sort(self.selectedScanNums))+'], sli=['+self.ui.pilHSlitLineEdit.text()+'], /'+self.ui.pilAxesComboBox.currentText()
        self.ui.commandLineEdit.setText(self.command)
        
    def saveGIDData(self):
        axes=str(self.ui.pilAxesComboBox.currentText())
        if axes not in ('Angles','Q') or getattr(self,'pilGIDData',None) is None:
            self.messageBox('Make a GID map first, with the axes in Angles or Q, then save it.')
            return
        self.saveFileName=str(QFileDialog.getSaveFileName(caption='Save gioxs data', directory=self.directory)[0])
        if self.saveFileName=='':   # dialog cancelled: write nothing
            return
        gidmod.save(self.saveFileName,self.gidProducts(axes))
        self.scriptLine(self.gidScript(self.saveFileName,axes))

    def gidScript(self,name,axes):
        """The lss_core call that reproduces the GID map just saved."""
        if len(self.ui.backgroundListWidget.selectedItems())>0:
            return '# this GID map is of background-subtracted frames; scripts cannot do that yet'
        scans=sorted(set(int(self.pilScanNum[i]) for i in self.selectedPilFramesNums))
        points={}
        for n in scans:
            chosen=[int(self.pilFrameNum[i]) for i in self.selectedPilFramesNums if self.pilScanNum[i]==n]
            listed=[int(self.pilFrameNum[i]) for i in range(len(self.pilScanNum)) if self.pilScanNum[i]==n]
            if chosen!=listed:
                points[n]=chosen
        kw=['axes=%r' % axes]
        gp=self.gidEffectiveParams()
        changed=gp.changed()
        head=''
        if changed:
            head='from lss_core.gid import GIDParams\n'
            kw.append('params=GIDParams(%s)' % ', '.join('%s=%r' % (k,getattr(gp,k)) for k in changed))
        if getattr(self,'pilGIDRelax',0):
            kw.append('relax=True')
        if points:
            kw.append('points=%r' % points)
        if script_kw(self.errorModel) and not gp.pinhole:
            kw.append(script_kw(self.errorModel))
        if self.ui.pilSpecCheckBox.checkState()==0:
            kw.append('db_pos=(%r, %r)' % (float(self.xcenter[0]),float(self.ycenter[0])))
        if int(self.ui.pilBPCiteSpinBox.value())!=0:
            kw.append('bad_pixel_iterations=%d, bad_pixel_factor=%d' % (int(self.ui.pilBPCiteSpinBox.value()),int(self.ui.pilBPCfacSpinBox.value())))
        return head+'gid = exp.gid(%r, %s)\ngid.save(%r)' % (scans,', '.join(kw),name)

    def imagehjoin(self, data1, data2):
        return gidmod.hjoin(data1,data2,getattr(self,'gidJoinLog',None),getattr(self,'gidJoinLabel',''),self.messageBox)

    def imagevjoin(self, data1, data2):
        return gidmod.vjoin(data1,data2,self.gidParams.vjoin_kind,getattr(self,'gidJoinLog',None),
                            getattr(self,'gidJoinLabel',''),self.messageBox)

    def sortedScans(self,data, mtype='dth'):  #reture the order of scans from low dth to higt dth, also works for sorting qz in the ref
        if len(data)<2:
            return list(data.keys())
        else:
            #print(data)
            x={}
            sorted_keys=[]
            for keys in data.keys():
                #print(len(data[keys]), data[keys])
                if mtype=='dth':
                    x[keys]=sorted([data[keys][0][0][0],data[keys][-1][0][0]]) #get dth range for each key, i.e., scan number
                else:
                    try:
                        x[keys]=sorted([data[keys][0][0],data[keys][-1][0]])  #get qz range for each key
                    except:
                        self.messageBox('Warning: Scan ' + str(keys) + ' does not have enough points for patching!')
                        return
            #print(x)
            sorted_x=sorted(x.items(), key=lambda t:t[1])  #sort the dth range
            for i in range(len(sorted_x)):
                sorted_keys.append(sorted_x[i][0]) #make an array for keys (scan number) based on the dth range
            return sorted_keys
        
    def polynomial(self,x,*p):    #define polynomial function
        return sum([p[i]*x**i for i in range(len(p))])
        
    def pilGIDData(self):
        #print 'I am missing'
        if self.pilGIDshow==0:
            # self.disconnect(self.ui.pilAxesComboBox, SIGNAL('currentIndexChanged(int)'), self.update2dPlots)
            self.ui.pilAxesComboBox.currentIndexChanged.connect(self.update2dPlots)
            self.ui.pilAxesComboBox.setCurrentIndex(1)
            # self.connect(self.ui.pilAxesComboBox, SIGNAL('currentIndexChanged(int)'), self.update2dPlots)
            self.ui.pilAxesComboBox.currentIndexChanged.connect(self.update2dPlots)
        self.pilGIDshow=1
        aspect=str(self.ui.pilAspectComboBox.currentText())
        vmax=float(self.ui.pilMaxLineEdit.text())
        vmin=float(self.ui.pilMinLineEdit.text())
        self.ui.pilMplWidget.canvas.fig.clf()
        self.pilxleft=self.xcenter-(float(self.ui.pilHSlitLineEdit.text())-1)/2
        self.pilxright=self.xcenter+(float(self.ui.pilHSlitLineEdit.text())-1)/2
        self.pilhintDatadic={}
        self.noteMixedAbsorbers([self.pil_AbsNum[i] for i in self.selectedPilFramesNums],'GID patching')
        cmap=str(self.ui.pilCMapComboBox.currentText())
        self.absfac=self.absorberModel()
        #sortedFrameNums=np.array(self.selectedPilFramesNums)[np.argsort(np.array(self.pil_Dth))]
        j=0   #for xcenter and ycenter, which are already defined in self.selectedPilFramesNums
        for i in self.selectedPilFramesNums:
            self.pilatus.plotHint({i:self.pilData[i]},{i:self.pilErrorData[i]},absfac=self.absfac,absnum=[self.pil_AbsNum[i]],cen=[self.pilX[i],self.pilY[i]], hroi=[self.pilxleft[j]-1, self.pilxright[j]-1], vroi=[5,486], ax_type='Angles', wavelength=[self.pil_Wavelength[i]],s2d_dist=[self.pil_Dist[i]], sh=[self.pil_Sh[i]],alpha=self.pilAlpha[i], truealpha=self.pilTrueAlpha[i], mon=[self.pilMonc[i]], gain=self.pilGains([self.pilScanNum[i]]))
            #ang=((self.pilatus.hintData[:,0]-self.ycenter[j])*0.172/self.distance[0]+np.arcsin(2.0*np.sin(self.pilAlpha[i])-np.sin(self.pilTrueAlpha[i])))*180/np.pi #convert pixle to beta
            #print self.pilatus.hintData[0][0]             
            j=j+1
            ckey=float(format(self.pil_Dth[i]*180/np.pi,'.2f'))
            if ckey in self.pilhintDatadic:
 #               self.pilhintDatadic[ckey].append(np.vstack((ang,self.pilatus.hintData[:,1],self.pilatus.hintData[:,2])).transpose())  #same dth but may be different starting qz 
                self.pilhintDatadic[ckey].append(np.vstack((self.pilatus.hintData[:,0],self.pilatus.hintData[:,1],self.pilatus.hintData[:,2])).transpose())
            else:
 #               self.pilhintDatadic[ckey]=[np.vstack((ang,self.pilatus.hintData[:,1],self.pilatus.hintData[:,2])).transpose()]
                self.pilhintDatadic[ckey]=[np.vstack((self.pilatus.hintData[:,0],self.pilatus.hintData[:,1],self.pilatus.hintData[:,2])).transpose()]
        lengths=np.array([len(self.pilhintDatadic[key]) for key in sorted(self.pilhintDatadic.keys())])
#        if np.any(lengths!=lengths[0]):
#            self.messageBox('Error:: Couldnot patch the frames perhaps some frames are missing for doing #the patch.')
#        else:
        self.pilhintData=[]
        self.pilhintErrorData=[]
        pilXAxis=[]
        for keys in sorted(self.pilhintDatadic.keys()):
            data=sorted(self.pilhintDatadic[keys],key=lambda x:x[0,0])  #each data for same qxy 
            pdata={}
            for i in range(len(data)): #creating dictonary of same starting qz's with averaging the same starting qz arrays
                c1keys=float(format(data[i][0,0],'.3f'))
                if c1keys in pdata: #same starting qz
                    pdata[c1keys]=(pdata[c1keys]+data[i])/2.0   #averaging 
                else: #different starting qz
                    pdata[c1keys]=data[i]
            keys1=sorted(pdata.keys())  #starting qz for different images with same qxy (i.e., dth)
            pdata2=pdata[keys1[0]]  # data of low starting qz for this dth 
            for i in range(1,len(keys1)):
                overlap1=np.where(pdata2[:,0]>=pdata[keys1[i]][0,0]) #create a list of pixles in lower qz data, which has larger qz than the first point of higher qz data 
                overlap2=np.where(pdata[keys1[i]][:,0]<=pdata2[-1,0]) #create a list of pixles in higher qz data, which has smaller qz than the last point of smaller qz data 
                f=interp1d(pdata[keys1[i]][overlap2,0][0],pdata[keys1[i]][overlap2,1][0]) #create the interpreation function based on the higher qz data in the overlap area
                fac=np.sum(pdata2[overlap1[0][:-1],1])/np.sum(f(pdata2[overlap1[0][:-1],0])) #calculate the scale factor
                pdata[keys1[i]][:,1]=fac*pdata[keys1[i]][:,1]
                pdata[keys1[i]][:,2]=fac*pdata[keys1[i]][:,2]
                pdata2=np.vstack((pdata2[:overlap1[0][0],:],pdata[keys1[i]]))
            self.pilhintData.append(list(pdata2[:,1]))  #sige intensity for pilhintData for this dth
            self.pilhintErrorData.append(list(pdata2[:,2]))  #sign errorbar of intensity for pilhintData for this dth
            pilXAxis.append(float(keys))  #sign x-axis for this dth
        pilYAxis=list(pdata2[:,0])  #sign y-axis for all dth
        self.pilhintData=np.array(self.pilhintData).transpose()
        self.pilhintErrorData=np.array(self.pilhintErrorData).transpose()
        self.pilXAxs, self.pilYAxs=np.meshgrid(pilXAxis,pilYAxis)
        self.pil_xlabel=r'$2\theta$'+' '+r'$[\deg]$'
        self.pil_ylabel=r'$\beta$'+' '+r'$[\deg]$'
        vmax=np.max(self.pilhintData)

#            if str(self.ui.pilAxesComboBox.currentText())=='Angles':
#                self.pilYAxs=((self.pilYAxs-self.ycenter[0])*0.172/self.distance[0]+self.alpha[0])*180/np.pi
#                self.pil_ylabel= 'Theta [Degrees]'
        if str(self.ui.pilAxesComboBox.currentText())=='Q':
            self.pilYAxs==2.0*np.pi*(np.sin(self.pilYAxs*np.pi/180.0)+np.sin(self.pilTrueAlpha[0]))/self.wavelength[0] #this coversion is approximation. 
            self.pilXAxs=4.0*np.pi*np.sin(self.pilXAxs*np.pi/2.0/180.0)/self.wavelength[0]  #this coversion is approximation.
            self.pil_xlabel=r'$Q_{xy}$'+' '+r'$[\AA^{-1}]$'
            self.pil_ylabel=r'$Q_z$'+' '+r'$[\AA^{-1}]$'
        self.gidax=self.ui.pilMplWidget.canvas.fig.add_subplot(1,1,1)
        if self.ui.pilLogIntCheckBox.checkState()!=0:
            # one mesh, not a polygon per cell (mplwidget.mesh): the log map was the slow one (2026-11-23)
            self.gid_p=mesh(self.gidax,self.pilXAxs, self.pilYAxs, np.log10(self.pilhintData),cmap=cmap,vmin=np.log10(vmin), vmax=np.log10(vmax))
        else:
            fint=interp1d(self.pilXAxs[0], self.pilhintData, kind='cubic')
            #print self.pilXAxs[0], self.pilhintData, len(self.pilhintData), len(self.pilhintData[0])
            newpilXAxis=np.linspace(self.pilXAxs[0][0],self.pilXAxs[0][-1],len(self.pilXAxs[0])*10)
            inter_pilhitData=fint(newpilXAxis)
            self.extent=[self.pilXAxs[0][0],self.pilXAxs[0][-1],self.pilYAxs[0][0],self.pilYAxs[-1][-1]]
            self.gid_p=self.gidax.imshow(inter_pilhitData,interpolation='bicubic',extent=self.extent,vmax=vmax,vmin=vmin,cmap=cmap,aspect=aspect,origin='lower')            
            #self.gid_p=self.gidax.pcolor(self.pilXAxs, self.pilYAxs, self.pilhintData,cmap=cmap,vmin=vmin, vmax=vmax)           
        #self.gidax.set_xlim((np.min(self.pilXAxs),np.max(self.pilXAxs)))
        #self.gidax.set_ylim((np.min(self.pilYAxs),np.max(self.pilYAxs)))
        self.gidax.set_aspect(aspect)
        self.gidax.set_xlabel(self.pil_xlabel)
        self.gidax.set_ylabel(self.pil_ylabel)
        self.ui.pilMplWidget.canvas.fig.colorbar(self.gid_p)
        self.ui.pilMplWidget.canvas.draw()
       
    

    def format_coord(self,x,y):  # cursor interactive 
        numrows, numcols = self.Zdata.shape
        col = int(np.abs((x-self.extent[0]))*numrows/np.abs((self.extent[1]-self.extent[0])))
        row = int(np.abs((y-self.extent[3]))*numcols/np.abs((self.extent[3]-self.extent[2])))
        if col>=0 and col<numcols and row>=0 and row<numrows:
            z = self.Zdata[row,col]
            return self.xyzformat%(x, y, z)
        else:
            return 'x=%.2f, y=%.2f'%(x, y)
    
    def format_pil_coord(self,x,y):  # cursor interactive 
        numrows, numcols = self.Zdata.shape
        col = int(np.abs((x-self.extent[0]))*numcols/np.abs((self.extent[1]-self.extent[0])))
        row = int(np.abs((y-self.extent[2]))*numrows/np.abs((self.extent[3]-self.extent[2])))
        if col>=0 and col<numcols and row>=0 and row<numrows:
            z = self.Zdata[row,col]
            return self.xyzformat%(x, y, z)
        else:
            return 'x=%.2f, y=%.2f'%(x, y)
    
    def format_coord_ref(self,x,y):
        numrows, numcols = self.refZdata.shape
        col = int(np.abs((x-self.extent[0]))*numrows/np.abs((self.extent[1]-self.extent[0])))
        row = int(np.abs((y-self.extent[3]))*numcols/np.abs((self.extent[3]-self.extent[2])))
        if col>=0 and col<numcols and row>=0 and row<numrows:
            z = self.refZdata[row,col]
            return 'x=%d,y=%d,z=%.1e'%(x, y, z)
        else:
            return 'x=%d, y=%d'%(x, y)
        
    def refPlotWin(self):
#        if self.ui.gixSumCheckBox.checkState()==0:
#            self.ui.gixSumCheckBox.setCheckState(2)
#            self.messageBox('Warning:: Multiple frames selected, summing over all the frames for Reflectivity!!')
        if self.det!='Pilatus' or len(getattr(self,'selectedPilFramesNums',[]))==0:
            self.messageBox('Please load a scan and select its images before opening the reflectivity analysis')
            return
        self.ui.PlotWidget.setCurrentIndex(3)
        self.ui.refCenCheckBox.setCheckState(0)
        self.ui.refComLineEdit.clear()
        if self.refpatchindex==1:
            self.ui.refDataListWidget.clear()
            self.ui.refNormRefListWidget.clear()
            self.refData=[]
        self.refpatchindex=0  #different index for pilatus patch model
        if self.det=='Pilatus':
            self.updateRefPilPlotData()
            
        
       
    def updateRefPilPlotData(self):
        self.ui.refADDataPlotWidget.canvas.fig.clf()
        dist=float(self.ui.pilSDDistLineEdit.text())
        cmap=str(self.ui.pilCMapComboBox.currentText())
        # self.disconnect(self.ui.refQzListWidget, SIGNAL('itemSelectionChanged()'),self.refQzListSelectionChanged)
        self.ui.refQzListWidget.itemSelectionChanged.disconnect(self.refQzListSelectionChanged)
        self.ui.refQzListWidget.clear()
        self.scanframe={}
        self.refSortedFrameNums={}
        if self.ui.pilMergeSameQzCheckBox.checkState()!=0:
            j=0
            for key in sorted(self.pilFrameNumsWithSameQz.keys()):
                self.scanframe[key]={}
                for item in self.pilFrameNumsWithSameQz[key]:
                    ekey=int(str(self.ui.imageListWidget.item(item).text()).split('\t')[0].split('#')[1])
                    if ekey in self.scanframe[key]:
                        self.scanframe[key][ekey].append(int(str(self.ui.imageListWidget.item(item).text()).split('\t')[1].split('#')[1]))
                    else:
                        self.scanframe[key][ekey]=[int(str(self.ui.imageListWidget.item(item).text()).split('\t')[1].split('#')[1])]
                if all(x==self.pilFrameAbsWithSameQz[key][0] for x in self.pilFrameAbsWithSameQz[key]):                   
                    self.ui.refQzListWidget.addItem('Qz= '+str(key)+'\t {S:F}= '+str(self.scanframe[key])+'\t Abs= '+str([self.pilFrameAbsWithSameQz[key][0]]))
                    self.refSortedFrameNums[j]=self.pilFrameNumsWithSameQz[key]
                    j=j+1
                else:
                    for i in range(len(self.pilFrameNumsWithSameQz[key])):
                        sftext=str(self.ui.imageListWidget.item(self.pilFrameNumsWithSameQz[key][i]).text()).split('\t')
                        self.ui.refQzListWidget.addItem('Qz= '+str(key)+'\t {S:F}= '+str({int(sftext[0].split('#')[1]):[int(sftext[1].split('#')[1])]})+'\t Abs= '+str([self.pilFrameAbsWithSameQz[key][i]]))
                        self.refSortedFrameNums[j]=[self.pilFrameNumsWithSameQz[key][i]]
                        j=j+1
        else:
            j=0
            for i in self.selectedPilFramesNums:
                sftext=str(self.ui.imageListWidget.item(i).text()).split('\t')
                self.ui.refQzListWidget.addItem('Qz= '+str(self.pilFileQzs[i])+'\t {S:F}= '+str({int(sftext[0].split('#')[1]):[int(sftext[1].split('#')[1])]})+'\t Abs='+str(self.pil_AbsNum[i]))
                self.refSortedFrameNums[j]=[i]
                j=j+1
        # self.connect(self.ui.refQzListWidget, SIGNAL('itemSelectionChanged()'),self.refQzListSelectionChanged)
        self.ui.refQzListWidget.itemSelectionChanged.connect(self.refQzListSelectionChanged)
        self.ui.refQzListWidget.item(0).setSelected(True)
        
    def refFramesGone(self,rows=None):
        """True (with one message) when frames behind the Qz list are no longer loaded.

        The list is built when Ref is pressed; changing the image selection afterwards
        leaves it pointing at frames that are not in memory (sweep walk, 2026-11-22:
        KeyError in refQzListSelectionChanged). ``rows``: list rows to check, the
        selected ones by default.
        """
        if getattr(self,'det',None)!='Pilatus':
            return False
        if rows is None:
            rows=[self.ui.refQzListWidget.row(it) for it in self.ui.refQzListWidget.selectedItems()]
        data=getattr(self,'pilData',None) or {}
        errors=getattr(self,'pilErrorData',None) or {}
        frames=getattr(self,'refSortedFrameNums',{})
        if all(i in data and i in errors for r in rows for i in frames.get(r,[])):
            return False
        self.messageBox('The Qz list is out of date: its frames are no longer selected. Select them and press Ref again.')
        return True

    def refQzListSelectionChanged(self):
        if len(self.ui.refQzListWidget.selectedItems())==0:
            return   #nothing selected in the Qz list, nothing to redraw
        if self.refFramesGone():
            return False
        self.ui.refADDataPlotWidget.canvas.fig.clf()
        cmap=str(self.ui.pilCMapComboBox.currentText())
        self.refQzSelectedItems=self.ui.refQzListWidget.selectedItems()        
        self.refQzSelected=float(str(self.refQzSelectedItems[0].text()).split()[1])
        self.absfac=self.absorberModel()       
        self.dir=str(self.ui.refBGDirComboBox.currentText())
        if self.det=='Pilatus': 
            slitx=int(self.ui.refSlitLineEdit.text().split(',')[0])
            slity=int(self.ui.refSlitLineEdit.text().split(',')[1])
            self.slit=[slitx,slity]
            self.bg=float(self.ui.refBGOffLineEdit.text())           
            self.selFrameNums=self.refSortedFrameNums[self.ui.refQzListWidget.row(self.refQzSelectedItems[0])]
            cenx=self.pilatus.NCOLS-self.pilX[self.selFrameNums[0]]-1 #image was flipped left to right
            ceny=self.pilY[self.selFrameNums[0]]
            self.mon=[self.pilMonc[i] for i in self.selFrameNums]
            self.absnum=[self.pil_AbsNum[i] for i in self.selFrameNums]
            self.noteMixedAbsorbers(self.absnum,'The frames at this Qz')
            self.vmax=float(self.ui.pilMaxLineEdit.text())
            self.vmin=float(self.ui.pilMinLineEdit.text())
            self.cen=[cenx,ceny]
            if self.ui.refCenCheckBox.checkState()==0:
                self.ui.refCenLineEdit.setText(str(self.cen[0])+','+str(self.cen[1]))
            else:
                self.cen=[int(self.ui.refCenLineEdit.text().split(',')[0]),int(self.ui.refCenLineEdit.text().split(',')[1])]  
            self.selData={}
            self.selErrorData={}
            if self.dir=='H':
                self.bg=self.bg*self.pil_Dist[self.selFrameNums[0]]*np.pi/180/0.172/slitx
            else:
                self.bg=self.bg*self.pil_Dist[self.selFrameNums[0]]*np.pi/180/0.172/slity         
            for i in self.selFrameNums:
                self.selData[i]=self.pilData[i]
                self.selErrorData[i]=self.pilErrorData[i]
            self.pilatus.setROI(self.selData,self.selErrorData,absfac=self.absfac,absnum=self.absnum,slit=self.slit,cen=self.cen,bg=self.bg,dir=self.dir,mon=self.mon,gain=self.pilGains([self.pilScanNum[i] for i in self.selFrameNums]))
            slit=[self.slit[1], self.slit[0]]
            cen=[self.cen[1], self.cen[0]]
            self.ax={}
            if self.dir=='H':
                self.refextent=[max(0,self.pilatus.bglcen-slit[1]), self.pilatus.bgrcen+slit[1]+1, cen[0]-slit[0], cen[0]+slit[0]+1]
                self.ax[1]=self.ui.refADDataPlotWidget.canvas.fig.add_subplot(2,1,1)
                self.vmax=np.max(self.pilatus.imageData[cen[0]-slit[0]:cen[0]+slit[0]+1, max(0,self.pilatus.bglcen-slit[1]):self.pilatus.bgrcen+slit[1]+1])
               # self.vmin=np.max(self.pilatus.imageData[cen[0]-slit[0]:cen[0]+slit[0]+1, max(0,self.pilatus.bglcen-slit[1]):self.pilatus.bgrcen+slit[1]+1])
                self.refZdata=self.pilatus.imageData
                p=self.ax[1].imshow(self.pilatus.imageROI[cen[0]-slit[0]:cen[0]+slit[0]+1, max(0,self.pilatus.bglcen-slit[1]):self.pilatus.bgrcen+slit[1]+1], origin='lower', aspect='auto', vmax=self.vmax, cmap=cmap, extent=self.refextent, interpolation='nearest')
                self.ax[1].set_ylabel('w/o Corr')
                self.ax[1].format_coord=self.format_coord_ref
            else:
                self.refextent=[cen[1]+slit[1]+1, cen[1]-slit[1], max(0,self.pilatus.bgucen-slit[0]), self.pilatus.bgdcen+slit[0]+1]
                self.ax[1]=self.ui.refADDataPlotWidget.canvas.fig.add_subplot(1,2,1)            
                # the region shown: the vertical background's centres (bglcen/bgrcen are the horizontal
                # one's, set only for 'H': AttributeError or a stale region; 2026-11-23)
                self.vmax=np.max(self.pilatus.imageData[max(0,self.pilatus.bgucen-slit[0]):self.pilatus.bgdcen+slit[0]+1,cen[1]-slit[1]:cen[1]+slit[1]+1])
                #self.vmin=np.max(self.pilatus.imageData[cen[0]-slit[0]:cen[0]+slit[0]+1, self.pilatus.bglcen-slit[1]:self.pilatus.bgrcen+slit[1]+1])
                self.refZdata=self.pilatus.imageData
                p=self.ax[1].imshow(self.pilatus.imageROI[max(0,self.pilatus.bgucen-slit[0]):self.pilatus.bgdcen+slit[0]+1,cen[1]-slit[1]:cen[1]+slit[1]+1], origin='lower', aspect='auto', vmax=self.vmax, cmap=cmap, extent=self.refextent, interpolation='nearest')
                self.ax[1].set_ylabel('w/o Corr')
                self.ax[1].format_coord=self.format_coord_ref
            self.ui.refADDataPlotWidget.canvas.fig.colorbar(p)
            self.ui.refADDataPlotWidget.canvas.draw()
         
        
        
    def refAnalyzeFromField(self):
        #Enter pressed in a parameter field: silent when no Qz is selected
        if len(self.ui.refQzListWidget.selectedItems())==0:
            return
        self.refAnalyze()

    def refAnalyze(self):
        if len(self.ui.refQzListWidget.selectedItems())==0:
            self.messageBox('Please select a Qz in the list first')
            return
        if self.refQzListSelectionChanged() is False:
            return False   #the frames of the list are gone; refFramesGone said so
        cmap=str(self.ui.gixCMapComboBox.currentText())
        if self.det=='Pilatus':
            self.ui.refBadPixListWidget.clear()
            fac=float(self.ui.refSeaWinLineEdit.text())
            self.cenfit=1
            #Peak searching is dummy it is not doing anything#
            if self.ui.refCenCheckBox.checkState()!=0:
                self.cen=[int(self.ui.refCenLineEdit.text().split(',')[0]),int(self.ui.refCenLineEdit.text().split(',')[1])]
            self.par=self.pilatus.peakFind(self.selData,self.selErrorData,slit=self.slit,cen=self.cen,absfac=self.absfac,absnum=self.absnum,fac=fac,mon=self.mon,cenfit=self.cenfit,gain=self.pilGains([self.pilScanNum[i] for i in self.selFrameNums]))
            self.cen=[int(np.floor(self.par[1])), int(np.floor(self.par[3]))]
            slit=[self.slit[1], self.slit[0]]
            cen=[self.cen[1], self.cen[0]]
            bfac=float(self.ui.refBPCFacLineEdit.text())
            sig,sigerr,lbg,lbgerr,rbg,rbgerr=self.pilatus.sumROI(slit=self.slit,cen=self.cen,dir=self.dir,bg=self.bg)
            net,neterr=self.pilatus.netROI()
            self.pilatus.setROI(self.pilatus.imageData,self.pilatus.errorData,slit=self.slit,cen=self.cen,absfac=self.absfac,absnum=self.absnum,bg=self.bg,dir=self.dir,mon=None)  
            if self.dir=='H':
                self.refextent=[max(0,self.pilatus.bglcen-slit[1]), self.pilatus.bgrcen+slit[1]+1, cen[0]-slit[0], cen[0]+slit[0]+1]
                self.ax[2]=self.ui.refADDataPlotWidget.canvas.fig.add_subplot(2,1,2)
                self.vmax=np.max(self.pilatus.imageData[cen[0]-slit[0]:cen[0]+slit[0]+1, max(0,self.pilatus.bglcen-slit[1]):self.pilatus.bgrcen+slit[1]+1])
               # self.vmin=np.max(self.pilatus.imageData[cen[0]-slit[0]:cen[0]+slit[0]+1, self.pilatus.bglcen-slit[1]:self.pilatus.bgrcen+slit[1]+1])
                self.refZdata=self.pilatus.imageData
                p=self.ax[2].imshow(self.pilatus.imageROI[cen[0]-slit[0]:cen[0]+slit[0]+1, max(0,self.pilatus.bglcen-slit[1]):self.pilatus.bgrcen+slit[1]+1], origin='lower', aspect='auto', vmax=self.vmax, cmap=cmap, extent=self.refextent, interpolation='nearest')
                self.ax[2].set_ylabel('w Corr')
                self.ax[2].format_coord=self.format_coord_ref
            else:
                self.refextent=[cen[1]+slit[1]+1, cen[1]-slit[1], max(0,self.pilatus.bgucen-slit[0]), self.pilatus.bgdcen+slit[0]+1]
                self.ax[2]=self.ui.refADDataPlotWidget.canvas.fig.add_subplot(1,2,2)            
                # the region shown: the vertical background's centres (bglcen/bgrcen are the horizontal
                # one's, set only for 'H': AttributeError or a stale region; 2026-11-23)
                self.vmax=np.max(self.pilatus.imageData[max(0,self.pilatus.bgucen-slit[0]):self.pilatus.bgdcen+slit[0]+1,cen[1]-slit[1]:cen[1]+slit[1]+1])
                #self.vmin=np.max(self.pilatus.imageData[cen[0]-slit[0]:cen[0]+slit[0]+1, self.pilatus.bglcen-slit[1]:self.pilatus.bgrcen+slit[1]+1])
                self.refZdata=self.pilatus.imageData
                p=self.ax[2].imshow(self.pilatus.imageROI[max(0,self.pilatus.bgucen-slit[0]):self.pilatus.bgdcen+slit[0]+1,cen[1]-slit[1]:cen[1]+slit[1]+1], origin='lower', aspect='auto', vmax=self.vmax, cmap=cmap, extent=self.refextent, interpolation='nearest')
                self.ax[2].set_ylabel('w Corr')
                self.ax[2].format_coord=self.format_coord_ref
        self.ui.refADDataPlotWidget.canvas.fig.colorbar(p)
        self.ui.refADDataPlotWidget.canvas.draw()
        self.fsig=net
        self.fsigerr=neterr
        self.fsigerrper=self.fsigerr/self.fsig*100.0
        self.ui.refQLineEdit.setText('%.4f'%float(str(self.refQzSelectedItems[0].text()).split()[1]))
        self.ui.refRLineEdit.setText('%.4e'%self.fsig)
        self.ui.refRErrLineEdit.setText('%.4e'%self.fsigerr)
        self.ui.refPerRErrLineEdit.setText('%.4f'%self.fsigerrper)
    
    def updateRefDataList(self):
        if self.refpatchindex==0 and (len(self.ui.refQzListWidget.selectedItems())==0 or getattr(self,'fsig',None) is None): #regular ref
            self.messageBox('Please select a Qz and analyze it first')
            return
        if self.refpatchindex==0: #regular ref
            comments=str(self.refQzSelectedItems[0].text()).split('\t')[1:]
            self.refData.append([float(str(self.refQzSelectedItems[0].text()).split()[1]),self.fsig,self.fsigerr])
            self.refInfo.append('#'+comments[0]+'\t'+comments[1]+'\t#Comments:'+str(self.ui.refComLineEdit.text()))
            self.ui.refDataListWidget.addItem('%.4f'%float(str(self.refQzSelectedItems[0].text()).split()[1])+'\t'+'%.4e'%self.fsig+'\t'+'%.4e'%self.fsigerr+'\t'+self.refInfo[-1])
        else:  #pilatus patch ref
            self.ui.refDataListWidget.clear()
            self.ui.refNormRefListWidget.clear()
            for i in range(len(self.refData)):
                self.ui.refDataListWidget.addItem('%.4f'%self.refData[i][0]+'\t'+'%.4e'%self.refData[i][1]+'\t'+'%.4e'%self.refData[i][2])
        self.updateRefPlotData()
        
    def refAnalyzeAll(self):
        if len(self.ui.refQzListWidget.selectedItems())==0:
            self.messageBox('Please select a Qz in the list first')
            return
        if self.refFramesGone(range(self.ui.refQzListWidget.count())):
            return
        self.refAnalyze()
        self.updateRefDataList()
        self.progressDialog=QProgressDialog('Analyzing Images for reflectivity calculations','Abort',1,self.ui.refQzListWidget.count())
        self.progressDialog.setWindowModality(Qt.WindowModal)
        self.progressDialog.setWindowTitle('Wait')
        self.progressDialog.setAutoClose(True)
        self.progressDialog.setAutoReset(True)
        self.progressDialog.setMinimum(1)
        self.progressDialog.setMaximum(self.ui.refQzListWidget.count())
        self.progressDialog.show()
        for i in range(1,self.ui.refQzListWidget.count()):
            # self.disconnect(self.ui.refQzListWidget, SIGNAL('itemSelectionChanged()'),self.refQzListSelectionChanged)
            self.ui.refQzListWidget.itemSelectionChanged.disconnect(self.refQzListSelectionChanged)
            self.ui.refQzListWidget.item(i-1).setSelected(False)
            # self.connect(self.ui.refQzListWidget, SIGNAL('itemSelectionChanged()'),self.refQzListSelectionChanged)
            self.ui.refQzListWidget.itemSelectionChanged.connect(self.refQzListSelectionChanged)
            self.ui.refQzListWidget.item(i).setSelected(True)
            self.refAnalyze()
            self.updateRefDataList()
            self.progressDialog.setLabelText('Reading Frames for Qz= '+str(self.refQzSelected))     
            self.updateProgress()
            if self.progressDialog.wasCanceled()==True:
                break
        self.progressDialog.hide()
            
            
        
    def delRefDataList(self):
        items=self.ui.refDataListWidget.selectedItems()
        for item in items:
            self.refData.pop(self.ui.refDataListWidget.row(item))
            if self.refpatchindex==0:
                self.refInfo.pop(self.ui.refDataListWidget.row(item))
            self.ui.refDataListWidget.takeItem(self.ui.refDataListWidget.row(item))
        self.updateRefPlotData()
        
    def fresnel(self,q,qc):
        return stitching.fresnel(q,qc)
        
    def pilRefPatchData(self):
        if self.det!='Pilatus' or len(getattr(self,'selectedPilFramesNums',[]))==0 or len(getattr(self,'selectedScanNums',[]))==0:
            self.messageBox('Please load a Pilatus scan and select its images before using Ref Patch')
            return
        self.refpatchindex=1
        self.refDrops={}       # join number -> list of drop actions, for the script console
        self.refFactors={}     # join number -> (factor, error) used instead of the fitted one
        self.refMethodUsed=self.refPatchMethod()   # one method for the whole patch (the script line says it)
        self.refKnownOverride={}   # join number -> the user's choice in the patch window
        self.refMerged=[]      # groups merged in the identical-scans dialog
        self.refDroppedScans=[]   # scans dropped in the identical-scans dialog
        self.refScanList=sorted(set(int(self.pilScanNum[i]) for i in self.selectedPilFramesNums))
        self.refPoints={}      # scans of which only some frames are selected
        for n in self.refScanList:
            chosen=[int(self.pilFrameNum[i]) for i in self.selectedPilFramesNums if self.pilScanNum[i]==n]
            listed=[int(self.pilFrameNum[i]) for i in range(len(self.pilScanNum)) if self.pilScanNum[i]==n]
            if chosen!=listed:
                self.refPoints[n]=chosen
        slitx=int(self.ui.refSlitLineEdit.text().split(',')[0]) #get the size of ROI
        slity=int(self.ui.refSlitLineEdit.text().split(',')[1])
        self.slit=[slitx,slity]        
        self.dir=str(self.ui.refBGDirComboBox.currentText()) #get the background offset direction
        bg=float(self.ui.refBGOffLineEdit.text())  #get the background offset
        self.command='Ref Patch, scans=['+listText(np.sort(self.selectedScanNums))+'], slits=['+listText(self.slit)+'], bg_angle='+str(bg)+', bg_direction='+str(self.dir)
        self.ui.commandLineEdit.setText(self.command)         #update the command lineedit
        self.scanqzframe={}  #build a dictionary for all scans with their qz ranges and data for sorting the scans.
        self.pilRefPeakCen=[]
        self.pilBadPixInf = []  # build a list for the detailed info for corrected bad pix in RF signal ROI, which is shown for users
        self.refErrorModel=self.errorModel   # recorded for the Script pane
        for i in self.selectedPilFramesNums:
            # one point per frame: the same code a script uses (lss_core.reflectivity)
            qkey=self.pilScanNum[i]
            first=qkey not in self.scanqzframe
            row,info=reflectivity.frame_row(self.pilatus,self.pilData[i],self.pilErrorData[i],
                self.pilMonc[i],(self.pilX[i],self.pilY[i]),self.pilFileQzs[i],[slitx,slity],bg,
                self.dir,self.pil_Dist[i],
                low_qz_slit=first or self.ui.pilLowQzCorCheckBox.checkState()!=0)   # as coded: always on the first frame (PHYSICS_ISSUES P18)
            (cenx,ceny),(scenx,sceny)=info['centre'],info['expected']
            self.slit,self.bg=info['slit'],info['bg']
            if np.abs(cenx-scenx)>2:
                self.pilRefPeakCen.append([qkey,self.pilFrameNum[i],'x', np.abs(cenx-scenx)])
            if np.abs(ceny-sceny)>2:
                self.pilRefPeakCen.append([qkey,self.pilFrameNum[i],'y', np.abs(ceny-sceny)])
            pilbadpixloc=[]   # corrected bad pixels inside the signal box, shown to the user
            badpix=self.pilbadpixLoc.get(i,[])   # not recorded when a background image is subtracted
            for j in range(len(badpix)):
                pilbadpixX=badpix[j][1]
                pilbadpixY=badpix[j][0]
                if cenx-(self.slit[0]+1)/2 < pilbadpixX < cenx+(self.slit[0]+1)/2 and ceny-(self.slit[1]+1)/2 < pilbadpixY < ceny+(self.slit[1]+1)/2:
                    pilbadpixloc.append([pilbadpixX, pilbadpixY])
            if len(pilbadpixloc)!=0:
                self.pilBadPixInf.append([qkey,self.pilFrameNum[i],pilbadpixloc])
            self.scanqzframe[qkey]=row if first else np.vstack((self.scanqzframe[qkey],row))
        try:
            self.pilrefsort=list(self.sortedScans(self.scanqzframe, mtype='qz'))
        except:
            return

        #print(self.scanqzframe)
        #print (self.pilrefsort)
        if len(self.pilRefPeakCen) != 0:
            self.pilRefPeakCenDis()  # display peak center offest (>2) for each frame
        if len(self.pilBadPixInf) != 0:
            self.pilBadPixInfDis()  # display bad pix correction in signal ROI for each frame
        if len(self.pilrefsort)==0:
            self.messageBox('Warning: no frame selected!!!')
        elif len(self.pilrefsort)==1:
            self.refData=list(np.atleast_2d(self.scanqzframe[self.pilrefsort[0]]))   #a single frame is a 1-D row
           #print self.refData
            self.ui.PlotWidget.setCurrentIndex(3)
            self.updateRefDataList()
        else:
            self.pilrefscanrag={}  #find the identical scans
            for key in self.scanqzframe:
                self.pilrefscanrag[key]=str(format(self.scanqzframe[key][0][0],'.3f'))+'_'+str(format(self.scanqzframe[key][-1][0],'.3f'))+'_'+str(len(self.scanqzframe[key]))
          #  print self.pilrefscanrag
            dd={}
            for key,value in self.pilrefscanrag.items():
                try:
                    dd[value].append(key)
                except:
                    dd[value]=[key]
          #  print dd
            self.pilrefsamescannum=[l for l in dd.values() if len(l)>1] #this is list with the identical scans numbers
          #  print self.pilrefsamescannum
            if len(self.pilrefsamescannum)!=0: #if identical scans found, give user choice to merge, patch, and drop scans. 
                self.messageBox('Identical scans were found! Please select your choices; regular patch is defult!')
                self.pilRefSameScan()
            else:
                self.pilRefPatch()
                
    def pilRefPeakCenDis(self):
        Dialog=QDialog(self)
        ui=uic.loadUi(resource('pilPeakCenDialog.ui'),Dialog)
        ui.show()
        line='Scan\tFrame\tAxis\t# of Pixels off\n'
        for i in range(len(self.pilRefPeakCen)):
            line=line+str(self.pilRefPeakCen[i][0])+'\t'+str(self.pilRefPeakCen[i][1])+'\t'+self.pilRefPeakCen[i][2]+'\t'+str(self.pilRefPeakCen[i][3])+'\n'
        ui.peakCenTextBrowser.append(line)
        
        Dialog.exec_()

    def pilBadPixInfDis(self):
        Dialog = QDialog(self)
        ui = uic.loadUi(resource('pilBadPixDialog.ui'), Dialog)
        ui.pushButton.setIcon(QIcon(resource('stop.png')))
        ui.pushButton.setIconSize(QSize(100, 100))
        ui.show()
        line = 'Scan\tFrame\tPixel(s)\n'
       # print self.pilBadPixInf
        for i in range(len(self.pilBadPixInf)):
            line = line + str(self.pilBadPixInf[i][0]) + '\t' + str(self.pilBadPixInf[i][1]) + '\t' + \
                   str(self.pilBadPixInf[i][2]) + '\n'
        ui.peakCenTextBrowser.append(line)

        Dialog.exec_()
                
    def pilRefPatch(self):            
        Dialog=QDialog(self)                
        self.uirefpatch=uic.loadUi(resource('refpatch.ui'), Dialog)
        self.uirefpatch.show()
        self.pilreforder=0
        # self.connect(self.uirefpatch.dropPushButton, SIGNAL('clicked()'),self.pilRefPatchDrop)  #drop the data
        self.uirefpatch.dropPushButton.clicked.connect(self.pilRefPatchDrop)
        # self.connect(self.uirefpatch.nextPushButton,SIGNAL('clicked()'),self.pilRefPatchNext) #go to the next overlap
        self.uirefpatch.nextPushButton.clicked.connect(self.pilRefPatchNext)
        from PyQt5.QtWidgets import QCheckBox, QLabel
        box=QCheckBox('Known ratio',Dialog)
        box.setObjectName('knownRatioCheckBox')
        lab=QLabel('',Dialog)
        lab.setObjectName('knownRatioLabel')
        lay=self.uirefpatch.horizontalLayout
        lay.insertWidget(lay.indexOf(self.uirefpatch.nextPushButton),lab)
        lay.insertWidget(lay.indexOf(self.uirefpatch.nextPushButton),box)
        self.uirefpatch.knownRatioCheckBox,self.uirefpatch.knownRatioLabel=box,lab
        box.toggled.connect(self.pilRefPatchKnownToggled)
        self.refScale={self.pilrefsort[0]:1.0}   # scale already applied to each scan's data
        # unscaled copies of the scans as the joins start (the joins scale them in place, trap T3):
        # the covariance export replays the patch from these
        self.refPatchInput={k:np.array(v,dtype=float) for k,v in self.scanqzframe.items()}
        self.refPatchOrder=list(self.pilrefsort)
        self.refInfoShown=None
        self.pilRefPatchPlot()

    def refMonitorChange(self,a,b):
        """Monc/Monp of scan b over scan a at their overlap (P29), or None."""
        try:
            da,db=self.specData[a],self.specData[b]
            return reflectivity.monitor_change(da['L'],da['Monc'],da['Monp'],db['L'],db['Monc'],db['Monp'])
        except (KeyError,TypeError,IndexError):
            return None

    def refPatchMethod(self):
        """How Ref Patch fits the factor at a join: 'joint' or 'legacy' (preference)."""
        m=self.prefs.get('ref_patch_method',reflectivity.DEFAULT_PATCH_METHOD)
        return m if m in reflectivity.PATCH_METHODS else reflectivity.DEFAULT_PATCH_METHOD

    def refActiveMethod(self):
        """The method of the patch in progress (set when it starts), else the preference."""
        return getattr(self,'refMethodUsed',None) or self.refPatchMethod()

    def refJoinInfo(self):
        """Fitted factor, known absorber ratio and the choice for the join on show."""
        j=self.pilreforder
        a,b=self.pilrefsort[j],self.pilrefsort[j+1]
        old=self.scanqzframe[a] if j==0 else self.pilrefdata
        note=''
        try:
            f,e,note=reflectivity.join_factor(old,self.scanqzframe[b],self.refActiveMethod())
            patch=(f,e)
        except Exception:
            patch=None
        known=None
        pa,pb=self.specPar.get(a,{}),self.specPar.get(b,{})
        wl=pb.get('Wavelength')
        if (self.prefs['calibrated_foils'] and isinstance(wl,(int,float)) and wl>0 and pa.get('Wavelength')==wl
                and isinstance(pa.get('Absorber'),(int,float)) and isinstance(pb.get('Absorber'),(int,float))):
            foils=absorbers.calibrated(absorbers.energy_kev(wl))
            if foils is not None:
                try:
                    qz=float(np.atleast_2d(self.scanqzframe[b])[0][0])   # where the overlap starts
                    r,rel=foils.step(pa['Absorber'],pb['Absorber'],qz=qz)
                    known=(self.refScale.get(a,1.0)*r,rel)
                except ValueError:
                    known=None
        mon=self.refMonitorChange(a,b)
        choice=None if patch is None else reflectivity.patch_choice(
            patch,known,mon,auto=self.prefs['patch_auto_known_ratio'],
            threshold=self.prefs['patch_threshold_percent']/100.0)
        return dict(join=j,a=a,b=b,patch=patch,known=known,monitor=mon,choice=choice,note=note)

    def refPreviewFactor(self):
        """The factor the join on show will use when it is fitted (None: the
        legacy preview's own, as before 2026-11-22)."""
        info=self.refInfoShown
        if self.refActiveMethod()=='legacy' or not info or info.get('patch') is None:
            return None
        return info['patch'][0]

    def refShowKnown(self):
        """Set the patch window's known-ratio box for the join on show;
        returns the factor to preview with (None: the fitted one)."""
        info=self.refJoinInfo()
        self.refInfoShown=info
        box,lab=self.uirefpatch.knownRatioCheckBox,self.uirefpatch.knownRatioLabel
        c=info['choice']
        use=False
        if c is None or info['known'] is None:
            box.setEnabled(False)
            lab.setText('')
            box.setToolTip('Known absorber ratio: '+(c['why'] if c else 'no fitted factor here')+'.')
        else:
            box.setEnabled(True)
            use=self.refKnownOverride.get(info['join'],c['use'])
            fit,kn=100*c['patch_rel'],100*c['known_rel']
            lab.setText(('fit +/-%.1f%%, foils +/-%.1f%%' % (fit,kn))+(' - try known ratio' if c['suggest'] and not use else ''))
            lab.setToolTip('Relative error of the fitted patch factor and of the ratio of the calibrated foils '
                           '(%.4g) for this join' % info['known'][0])
            box.setToolTip('Use the absorber ratio of the calibrated foils instead of the fitted factor. '
                           +('Chosen automatically (File > Preferences). ' if c['use'] else '')+c['why']+'.')
        box.blockSignals(True)
        box.setChecked(bool(use))
        box.blockSignals(False)
        return info['known'][0] if use else None

    def pilRefPatchKnownToggled(self,on):
        self.refKnownOverride[self.pilreforder]=bool(on)
        self.pilRefPatchPlot()
        
    def pilRefSameScan(self):
        Dialog=QDialog(self)
        self.uirefpatchsamescan=uic.loadUi(resource('refpatchsamescan.ui'), Dialog)
        self.uirefpatchsamescan.show()
        self.pilrefsamescanorder=0
        # self.connect(self.uirefpatchsamescan.dropPushButton, SIGNAL('clicked()'),self.pilRefSSDrop) #drop scans
        self.uirefpatchsamescan.dropPushButton.clicked.connect(self.pilRefSSDrop)
        # self.connect(self.uirefpatchsamescan.mergePushButton, SIGNAL('clicked()'),self.pilRefSSMerge) #merge scans
        self.uirefpatchsamescan.mergePushButton.clicked.connect(self.pilRefSSMerge)
        # self.connect(self.uirefpatchsamescan.nextPushButton, SIGNAL('clicked()'),self.pilRefSSNext) #go to the next overlap
        self.uirefpatchsamescan.nextPushButton.clicked.connect(self.pilRefSSNext)
        self.pilRefSameScanPlot()
    
    def pilRefSameScanPlot(self):  
        if self.pilrefsamescanorder==len(self.pilrefsamescannum):
            self.pilrefsort=list(self.sortedScans(self.scanqzframe, mtype='qz'))
            self.uirefpatchsamescan.close()
            if len(self.pilrefsort)==0:
                self.messageBox('All scans were dropped; there is no reflectivity to patch.')
            elif len(self.pilrefsort)==1:   # one scan left: nothing to patch, use it as it is
                self.refData=list(np.atleast_2d(self.scanqzframe[self.pilrefsort[0]]))
                self.ui.PlotWidget.setCurrentIndex(3)
                self.updateRefDataList()
            else:
                self.pilRefPatch()
        else:
            self.uirefpatchsamescan.Label.setText('Indentical Reflectivity Scans: '+listText(np.sort(self.pilrefsamescannum[self.pilrefsamescanorder])))
            if self.pilrefsamescanorder==len(self.pilrefsamescannum)-1:
                self.uirefpatchsamescan.nextPushButton.setText('Finish!') 
            self.uirefpatchsamescan.plotWidget.canvas.ax.clear()
            self.uirefpatchsamescan.plotWidget.canvas.ax.set_xlabel(r'$Q_z$'+' '+r'$[\AA^{-1}]$')
            self.uirefpatchsamescan.plotWidget.canvas.ax.set_ylabel('Reflectivity')
            for i in range(len(self.pilrefsamescannum[self.pilrefsamescanorder])):
                self.uirefpatchsamescan.plotWidget.canvas.ax.errorbar(self.scanqzframe[self.pilrefsamescannum[self.pilrefsamescanorder][i]][:,0],self.scanqzframe[self.pilrefsamescannum[self.pilrefsamescanorder][i]][:,1], self.scanqzframe[self.pilrefsamescannum[self.pilrefsamescanorder][i]][:,2], fmt='o-', label='#'+str(self.pilrefsamescannum[self.pilrefsamescanorder][i]))
            self.uirefpatchsamescan.plotWidget.canvas.ax.legend(frameon=False,scatterpoints=0,numpoints=1)
            self.uirefpatchsamescan.plotWidget.canvas.draw()

    def pilRefSSDrop(self):
        group=self.pilrefsamescannum[self.pilrefsamescanorder]
        try:
            dropnumbers=[int(t) for t in str(self.uirefpatchsamescan.dropLineEdit.text()).split(',')]
        except ValueError:
            self.messageBox('Please enter the scan numbers to drop, separated by commas, e.g. "12,14".')
            return
        unknown=[n for n in dropnumbers if n not in group]
        if unknown:
            self.messageBox('Scan(s) '+listText(unknown)+' are not in this group of identical scans ('+listText(group)+').')
            return
        for n in dropnumbers:
            self.scanqzframe.pop(n,None)
            group.remove(n)
            self.refDroppedScans.append(n)
        self.pilRefSameScanPlot()

    def pilRefSSMerge(self):
        if len(self.pilrefsamescannum[self.pilrefsamescanorder])<2:
            self.messageBox('There is nothing to merge: fewer than two scans are left in this group.')
            return
        datax=self.scanqzframe[self.pilrefsamescannum[self.pilrefsamescanorder][0]][:,0]
        datay=self.scanqzframe[self.pilrefsamescannum[self.pilrefsamescanorder][0]][:,1]
        datayerr=self.scanqzframe[self.pilrefsamescannum[self.pilrefsamescanorder][0]][:,2]**2
        for i in range(1,len(self.pilrefsamescannum[self.pilrefsamescanorder])):
            datay=datay+self.scanqzframe[self.pilrefsamescannum[self.pilrefsamescanorder][i]][:,1]
            datayerr=datayerr+self.scanqzframe[self.pilrefsamescannum[self.pilrefsamescanorder][i]][:,2]**2
            self.scanqzframe.pop(self.pilrefsamescannum[self.pilrefsamescanorder][i])
        datay=datay/len(self.pilrefsamescannum[self.pilrefsamescanorder])
        datayerr=np.sqrt(datayerr)/len(self.pilrefsamescannum[self.pilrefsamescanorder])
        data=np.vstack((datax,datay,datayerr)).T
        self.refMerged.append(list(self.pilrefsamescannum[self.pilrefsamescanorder]))
        self.scanqzframe[self.pilrefsamescannum[self.pilrefsamescanorder][0]]=data
        self.pilrefsamescannum[self.pilrefsamescanorder]=[self.pilrefsamescannum[self.pilrefsamescanorder][0]]
        #print data
        #print self.pilrefsamescannum
        #print self.scanqzframe
        self.pilRefSameScanPlot()
        
    def pilRefSSNext(self):
        self.pilrefsamescanorder=self.pilrefsamescanorder+1 
        self.pilRefSameScanPlot()
    
    def pilRefPatchPlot(self):
        if self.pilreforder==len(self.pilrefsort)-1:
            self.uirefpatch.close()
            self.refData=list(self.pilrefdata)
            self.ui.PlotWidget.setCurrentIndex(3)
          #  print self.pilrefdata
            self.updateRefDataList()
        elif self.pilreforder==0:
            if self.pilreforder==len(self.pilrefsort)-2:
                self.uirefpatch.nextPushButton.setText('Finish!')
            self.uirefpatch.Label.setText('Reflectivity Patch between Scans '+str(self.pilrefsort[self.pilreforder])+' and '+str(self.pilrefsort[self.pilreforder+1]))
            if self.scanqzframe[self.pilrefsort[self.pilreforder]][-1][0]<self.scanqzframe[self.pilrefsort[self.pilreforder+1]][0][0]:
                self.messageBox('Warning: no overlap qz between slected frames from scan '+str(self.pilrefsort[self.pilreforder])+' and '+str(self.pilrefsort[self.pilreforder+1])+'!!!')
                self.uirefpatch.close()
            else:
               #print self.scanqzframe[self.pilrefsort[self.pilreforder]],self.scanqzframe[self.pilrefsort[self.pilreforder+1]]
                try:
                    fac,xmin,xmax,ymin,ymax=self.oneDjoin(self.scanqzframe[self.pilrefsort[self.pilreforder]],self.scanqzframe[self.pilrefsort[self.pilreforder+1]],mtype='fac')
                except:
                    self.messageBox('Warning: Scan ' + str(self.pilrefsort[self.pilreforder]) + ' or ' + str(self.pilrefsort[self.pilreforder+1]) + ' does not have enough points for patching!')
                    self.uirefpatch.close()
                    return

                #print self.scanqzframe[self.pilrefsort[self.pilreforder]],self.scanqzframe[self.pilrefsort[self.pilreforder+1]]                
                kfac=self.refShowKnown()
                if kfac is None:
                    kfac=self.refPreviewFactor()
                if kfac is not None and fac:     # preview with the known ratio or the joint fit's factor
                    ymin,ymax=min(ymin,ymin*kfac/fac),max(ymax,ymax*kfac/fac)
                    fac=kfac
                self.uirefpatch.plotWidget.canvas.ax.clear()
                self.uirefpatch.plotWidget.canvas.ax.set_xlabel(r'$Q_z$'+' '+r'$[\AA^{-1}]$')
                self.uirefpatch.plotWidget.canvas.ax.set_ylabel('Reflectivity')
                self.uirefpatch.plotWidget.canvas.ax.errorbar(self.scanqzframe[self.pilrefsort[self.pilreforder]][:,0],self.scanqzframe[self.pilrefsort[self.pilreforder]][:,1],self.scanqzframe[self.pilrefsort[self.pilreforder]][:,2],fmt='o-',label='#'+str(self.pilrefsort[self.pilreforder]))
                self.uirefpatch.plotWidget.canvas.ax.errorbar(self.scanqzframe[self.pilrefsort[self.pilreforder+1]][:,0],self.scanqzframe[self.pilrefsort[self.pilreforder+1]][:,1]*fac,self.scanqzframe[self.pilrefsort[self.pilreforder+1]][:,2]*fac,fmt='o-',label='#'+str(self.pilrefsort[self.pilreforder+1]))
                for i in range(len(self.scanqzframe[self.pilrefsort[self.pilreforder]])):
                    if self.scanqzframe[self.pilrefsort[self.pilreforder]][i,0]>=xmin:
                        self.uirefpatch.plotWidget.canvas.ax.text(self.scanqzframe[self.pilrefsort[self.pilreforder]][i,0]+0.02*(xmax-xmin),self.scanqzframe[self.pilrefsort[self.pilreforder]][i,1]+0.02*(ymax-ymin),str(i-len(self.scanqzframe[self.pilrefsort[self.pilreforder]])),color='b',fontsize=16) 
                for i in range(len(self.scanqzframe[self.pilrefsort[self.pilreforder+1]])): 
                    if self.scanqzframe[self.pilrefsort[self.pilreforder+1]][i,0]<=xmax:
                        self.uirefpatch.plotWidget.canvas.ax.text(self.scanqzframe[self.pilrefsort[self.pilreforder+1]][i,0]-0.04*(xmax-xmin),self.scanqzframe[self.pilrefsort[self.pilreforder+1]][i,1]*fac-0.06*(ymax-ymin),str(i),color='r',fontsize=16)                
                self.uirefpatch.plotWidget.canvas.ax.legend(frameon=False,scatterpoints=0,numpoints=1)
                self.uirefpatch.plotWidget.canvas.ax.set_xlim(xmin,xmax)
                self.uirefpatch.plotWidget.canvas.ax.set_ylim(ymin,ymax)
              #  print xmin,xmax,ymin,ymax, fac
                self.uirefpatch.plotWidget.canvas.draw()
        else:
            if self.pilreforder==len(self.pilrefsort)-2:
                self.uirefpatch.nextPushButton.setText('Finish!')
            self.uirefpatch.Label.setText('Reflectivity Patch between Scans '+str(self.pilrefsort[self.pilreforder])+' and '+str(self.pilrefsort[self.pilreforder+1]))
            if self.scanqzframe[self.pilrefsort[self.pilreforder]][-1][0]<self.scanqzframe[self.pilrefsort[self.pilreforder+1]][0][0]:
                self.messageBox('Warning: no overlap qz between slected frames from scan '+str(self.pilrefsort[self.pilreforder])+' and '+str(self.pilrefsort[self.pilreforder+1])+'!!!')
            else:
                try:
                    fac,xmin,xmax,ymin,ymax=self.oneDjoin(self.pilrefdata,self.scanqzframe[self.pilrefsort[self.pilreforder+1]],mtype='fac')
                except:
                    self.messageBox('Warning: Scan ' + str(self.pilrefsort[self.pilreforder]) + ' or ' + str(self.pilrefsort[self.pilreforder+1]) + ' does not have enough points for patching!')
                    self.uirefpatch.close()
                    return
                kfac=self.refShowKnown()
                if kfac is None:
                    kfac=self.refPreviewFactor()
                if kfac is not None and fac:     # preview with the known ratio or the joint fit's factor
                    ymin,ymax=min(ymin,ymin*kfac/fac),max(ymax,ymax*kfac/fac)
                    fac=kfac
                self.uirefpatch.plotWidget.canvas.ax.clear()
                self.uirefpatch.plotWidget.canvas.ax.set_xlabel(r'$Q_z$'+' '+r'$[\AA^{-1}]$')
                self.uirefpatch.plotWidget.canvas.ax.set_ylabel('Reflectivity')
                self.uirefpatch.plotWidget.canvas.ax.errorbar(self.pilrefdata[:,0],self.pilrefdata[:,1],self.pilrefdata[:,2],fmt='o-',label='#'+str(self.pilrefsort[self.pilreforder]))
                self.uirefpatch.plotWidget.canvas.ax.errorbar(self.scanqzframe[self.pilrefsort[self.pilreforder+1]][:,0],self.scanqzframe[self.pilrefsort[self.pilreforder+1]][:,1]*fac,self.scanqzframe[self.pilrefsort[self.pilreforder+1]][:,2]*fac,fmt='o-',label='#'+str(self.pilrefsort[self.pilreforder+1]))
                for i in range(len(self.pilrefdata)):
                    if self.pilrefdata[i,0]>=xmin:
                        self.uirefpatch.plotWidget.canvas.ax.text(self.pilrefdata[i,0]+0.02*(xmax-xmin),self.pilrefdata[i,1]+0.02*(ymax-ymin),str(i-len(self.pilrefdata)),color='b',fontsize=16) 
                for i in range(len(self.scanqzframe[self.pilrefsort[self.pilreforder+1]])): 
                    if self.scanqzframe[self.pilrefsort[self.pilreforder+1]][i,0]<=xmax:
                        self.uirefpatch.plotWidget.canvas.ax.text(self.scanqzframe[self.pilrefsort[self.pilreforder+1]][i,0]-0.04*(xmax-xmin),self.scanqzframe[self.pilrefsort[self.pilreforder+1]][i,1]*fac-0.06*(ymax-ymin),str(i),color='r',fontsize=16)                
                self.uirefpatch.plotWidget.canvas.ax.legend(frameon=False,scatterpoints=0,numpoints=1)
                self.uirefpatch.plotWidget.canvas.ax.set_xlim(xmin,xmax)
                self.uirefpatch.plotWidget.canvas.ax.set_ylim(ymin,ymax)
            #    print xmin,xmax,ymin,ymax, fac
                self.uirefpatch.plotWidget.canvas.draw()
    
    def pilRefPatchDrop(self):
        try:
            dropnumbers=[int(t) for t in str(self.uirefpatch.dropLineEdit.text()).split(',')]
        except ValueError:
            self.messageBox('Please input the number of points which you like to drop in the format of "-1, 0 "!')
            return
        new=self.scanqzframe[self.pilrefsort[self.pilreforder+1]]
        old=self.scanqzframe[self.pilrefsort[0]] if self.pilreforder==0 else self.pilrefdata
        try:   # all or nothing: an index out of range drops nothing
            old2,new2=reflectivity.apply_drops(old,new,dropnumbers)
        except IndexError:
            self.messageBox('Point '+listText([d for d in dropnumbers if not -len(old)<=d<len(new)] or dropnumbers)+' does not exist; nothing was dropped.')
            return
        self.scanqzframe[self.pilrefsort[self.pilreforder+1]]=new2
        if self.pilreforder==0:
            self.scanqzframe[self.pilrefsort[0]]=old2
        else:
            self.pilrefdata=old2
        self.refDrops.setdefault(self.pilreforder,[]).append(dropnumbers)
        self.pilRefPatchPlot()

    def pilRefPatchNext(self):
        if self.pilreforder>=len(self.pilrefsort)-1:
            return
        old=self.scanqzframe[self.pilrefsort[0]] if self.pilreforder==0 else self.pilrefdata
        new=self.scanqzframe[self.pilrefsort[self.pilreforder+1]]
        if np.atleast_2d(old)[-1][0]<np.atleast_2d(new)[0][0]:   # hand-off trap T11
            self.messageBox('Scans '+str(self.pilrefsort[self.pilreforder])+' and '+str(self.pilrefsort[self.pilreforder+1])+' do not overlap in Qz; they cannot be patched. Select frames that overlap.')
            return
        info=self.refInfoShown
        if info is None or info['join']!=self.pilreforder or self.refActiveMethod()!='legacy':
            info=self.refJoinInfo()     # the joint fit: always on the data as they are now (drops)
        a,b=self.pilrefsort[self.pilreforder],self.pilrefsort[self.pilreforder+1]
        factor=None
        if info['known'] is not None and self.uirefpatch.knownRatioCheckBox.isChecked():
            k,rel=info['known']
            factor=(k,k*rel)
            self.refFactors[self.pilreforder]=factor
            fit=info['patch']
            self.notify('Scans %d and %d: known absorber ratio %.4g +/- %.1f%% used instead of the fitted %s.'
                        % (a,b,k,100*rel,'%.4g +/- %.1f%%' % (fit[0],100*abs(fit[1]/fit[0])) if fit else 'factor'),
                        title='Ref Patch',level='info')
        else:
            self.refFactors.pop(self.pilreforder,None)
            if self.refActiveMethod()!='legacy' and info['patch'] is not None:
                factor=info['patch']       # the joint fit's factor (the legacy one is fitted by join itself)
                if 'legacy fit used' in info.get('note',''):
                    self.notify('Scans %d and %d: %s.' % (a,b,info['note']),title='Ref Patch',level='warning')
        if factor is not None:
            self.pilrefdata=stitching.join(old,new,mtype='merge',factor=factor)
        elif self.pilreforder==0:
            self.pilrefdata=self.oneDjoin(self.scanqzframe[self.pilrefsort[self.pilreforder]],self.scanqzframe[self.pilrefsort[self.pilreforder+1]],mtype='merge')
        else:
            self.pilrefdata=self.oneDjoin(self.pilrefdata,self.scanqzframe[self.pilrefsort[self.pilreforder+1]],mtype='merge')
        used=factor[0] if factor is not None else (info['patch'][0] if info['patch'] else 1.0)
        self.refScale[b]=used     # fitted against the curve joined so far: already relative to the first scan
        self.pilreforder=self.pilreforder+1
        self.pilRefPatchPlot()
        
     
    def oneDjoin(self,data1, data2, mtype='fac'): #join two 1D data
        return stitching.join(data1,data2,mtype=mtype)

    def addRefFiles(self):
        f=QFileDialog.getOpenFileNames(caption='Select Multiple Files to import', directory=self.directory, filter='Ref Files (*_ref.txt;*.ref*;*_rrf.txt)')[0]
        self.reffiles=self.reffiles+list(map(str, f))
        self.reffnames=[]
        self.ui.refRefFileListWidget.clear()
        for i in range(len(self.reffiles)):
            s=str(self.reffiles[i])
            self.reffnames.append(s[s.rfind('/')+1:])
            self.ui.refRefFileListWidget.addItem('#'+str(i+1)+'\t'+self.reffnames[i])

    def removeRefFiles(self):
        items=self.ui.refRefFileListWidget.selectedItems()
        #print items
        for item in items:
            #print self.reffiles, item
            #print self.ui.refRefFileListWidget.row(item)
            self.reffnames.pop(self.ui.refRefFileListWidget.row(item))
            self.reffiles.pop(self.ui.refRefFileListWidget.row(item))
            #self.ui.refRefFileListWidget.takeItem(self.ui.refRefFileListWidget.row(item))
        self.ui.refRefFileListWidget.clear()
        for i in range(len(self.reffnames)):
            self.ui.refRefFileListWidget.addItem('#'+str(i+1)+'\t'+self.reffnames[i])
    
    def updateSelectedRefFiles(self):
        selectedreffiles=self.ui.refRefFileListWidget.selectedItems()
        self.selectedreffiles_rows=[]
        for item in selectedreffiles:
            self.selectedreffiles_rows.append(self.ui.refRefFileListWidget.row(item))
        self.updateRefPlotData()

        
    def updateRefPlotData(self):
        self.ui.refRefDataPlotwidget.canvas.ax.clear()
        self.ui.refNormRefListWidget.clear()
        self.ui.refRefDataPlotwidget.canvas.ax.set_xlabel(r'$Q_z$'+' '+r'$[\AA^{-1}]$')
        self.ui.refRefDataPlotwidget.canvas.ax.set_ylabel('Reflectivity')
        self.refQc=float(self.ui.refQcLineEdit.text())
        self.refQoff=float(self.ui.refQoffLineEdit.text())
        #print self.refpatchindex
        if len(self.refData)!=0:
            data=np.array(self.refData)
            if self.refpatchindex==0:
                self.refInfoNew=[self.refInfo[i] for i in np.argsort(data[:,0])]
                data=data[np.argsort(data[:,0])]
            if data[0,0]<self.refQc:
                norm=np.max(data[np.where(data[:,0]<self.refQc)][:,1]) #use the max intensity for the q below qc as the normalization factor. 
                
                #norm=data[0,1]
                #normerr=data[0,2]
                normerr=0
                data[:,1]=data[:,1]/norm
                data[:,2]=np.sqrt(data[:,2]**2/norm**2+normerr**2*data[:,1]**2/norm**2)
                perErr=data[:,2]*100.0/data[:,1]
                if self.refpatchindex==0:
                    self.ui.refNormRefListWidget.addItem('Q\tRef\tRef_Err\t%Err\t#S')
                    for i in range(len(data[:,0])):
                        self.ui.refNormRefListWidget.addItem('%.4f'%data[i,0]+'\t'+'%.4e'%data[i,1]+'\t'+'%.4e'%data[i,2]+'\t'+'%.4f'%perErr[i]+'\t'+self.refInfoNew[i])
                else:
                    self.ui.refNormRefListWidget.addItem('Q\tRef\tRef_Err\t%Err')
                    for i in range(len(data[:,0])):
                        self.ui.refNormRefListWidget.addItem('%.4f'%data[i,0]+'\t'+'%.4e'%data[i,1]+'\t'+'%.4e'%data[i,2]+'\t'+'%.4f'%perErr[i])
            if self.ui.refNormFacCheckBox.checkState()>0:
                norm=float(self.ui.refNormLineEdit.text())
                #normerr=np.sqrt(norm)
                data[:,1]=data[:,1]/norm
                data[:,2]=data[:,2]/norm                
                #data[:,2]=np.sqrt(data[:,2]**2/norm**2+normerr**2*data[:,1]**2/norm**4)
                perErr=data[:,2]*100.0/data[:,1]
                if self.refpatchindex==0:
                    self.ui.refNormRefListWidget.addItem('Q\tRef\tRef_Err\t%Err\t#S')
                    for i in range(len(data[:,0])):
                        self.ui.refNormRefListWidget.addItem('%.4f'%data[i,0]+'\t'+'%.4e'%data[i,1]+'\t'+'%.4e'%data[i,2]+'\t'+'%.4f'%perErr[i]+'\t'+self.refInfoNew[i])
                else:
                    self.ui.refNormRefListWidget.addItem('Q\tRef\tRef_Err\t%Err')
                    for i in range(len(data[:,0])):
                        self.ui.refNormRefListWidget.addItem('%.4f'%data[i,0]+'\t'+'%.4e'%data[i,1]+'\t'+'%.4e'%data[i,2]+'\t'+'%.4f'%perErr[i])        
            self.normRefData=data[np.argsort(data[:,0])]
            if self.ui.refRRFCheckBox.checkState()!=0:
                self.ui.refRefDataPlotwidget.canvas.ax.set_ylabel('R/RF')
                data[:,0]=data[:,0]+self.refQoff
                data[:,1]=data[:,1]/self.fresnel(data[:,0],self.refQc)
                data[:,2]=data[:,2]/self.fresnel(data[:,0],self.refQc)
                self.RrfData=data.copy()   # the Qz^2 option below must only change what is plotted
            if self.ui.refQzSqrCheckBox.checkState()!=0:
                self.ui.refRefDataPlotwidget.canvas.ax.set_xlabel('Qz^2')
                data[:,0]=data[:,0]**2
            if len(data[0])!=3:  #for pilatus single scan data with left and right background
                self.ui.refRefDataPlotwidget.canvas.ax.errorbar(data[:,0],data[:,3],data[:,4],fmt='o',label='s')                    
                self.ui.refRefDataPlotwidget.canvas.ax.errorbar(data[:,0],data[:,5],fmt='-',label='lb')
                self.ui.refRefDataPlotwidget.canvas.ax.errorbar(data[:,0],data[:,6],fmt='-',label='rb')
            else: 
                self.ui.refRefDataPlotwidget.canvas.ax.errorbar(data[:,0],data[:,1],data[:,2],fmt='o',label='#0')
        else:
            print ('no current ref data to plot')
     #plot selected ref files
        if  len(self.selectedreffiles_rows)!=0:
            for i in range(len(self.selectedreffiles_rows)):
                data1=np.loadtxt(str(self.reffiles[self.selectedreffiles_rows[i]]), comments='#')
                if self.ui.refRRFCheckBox.checkState()!=0:
                    self.ui.refRefDataPlotwidget.canvas.ax.set_ylabel('R/RF')
                    if str(self.reffiles[self.selectedreffiles_rows[i]]).split('_')[-1]!='rrf.txt':
                        data1[:,0]=data1[:,0]+self.refQoff
                        data1[:,1]=data1[:,1]/self.fresnel(data1[:,0],self.refQc)
                        data1[:,2]=data1[:,2]/self.fresnel(data1[:,0],self.refQc)
                if self.ui.refQzSqrCheckBox.checkState()!=0:
                    self.ui.refRefDataPlotwidget.canvas.ax.set_xlabel('Qz^2')
                    data1[:,0]=data1[:,0]**2
                self.ui.refRefDataPlotwidget.canvas.ax.errorbar(data1[:,0],data1[:,1],data1[:,2],fmt='o',label='#'+str(self.selectedreffiles_rows[i]+1))
        # done
        if self.ui.refLogYCheckBox.checkState()!=0:
            self.ui.refRefDataPlotwidget.canvas.ax.set_yscale('log')
        else:
            self.ui.refRefDataPlotwidget.canvas.ax.set_yscale('linear')
        if self.ui.refLegendCheckBox.checkState()!=0:
            self.ui.refRefDataPlotwidget.canvas.ax.legend(loc=self.ui.refLegendLocComboBox.currentIndex()+1,frameon=False,scatterpoints=0,numpoints=1)
        try:
            self.ui.refRefDataPlotwidget.canvas.ax.set_title('File: '+self.specFileName+' S# '+listText(np.sort(self.selectedScanNums)))
        except:
            pass
        self.ui.refRefDataPlotwidget.canvas.draw()
        self.saveTemData()
        
    def saveRefData(self):
        if self.det!='Pilatus' or len(self.refData)==0 or getattr(self,'normRefData',None) is None:
            self.messageBox('There is no reflectivity data to save yet')
            return
        self.saveFileName=QFileDialog.getSaveFileName(caption='Save Reflectivity',directory=self.directory)[0]
        if not self.saveFileName:
            return   #dialog cancelled
        if self.det=='Pilatus':
            reffile=self.saveFileName+'_ref.txt'
            rrffile=self.saveFileName+'_rrf.txt'
            np.savetxt(reffile,self.normRefData,fmt='%.4e\t%.4e\t%.4e')
            try:
                np.savetxt(rrffile,self.RrfData,fmt='%.4e\t%.4e\t%.4e')
            except:
                print ('No rrf data available!')
            if self.refCovarianceCheckBox.isChecked():
                self.saveRefCovariance(self.saveFileName)
            self.scriptLine(self.reflectivityScript(self.saveFileName))

    def setupRefCovarianceBox(self):
        """The Ref Patch export's "+ covariance" option, just after its Save button."""
        from PyQt5.QtWidgets import QCheckBox
        box=QCheckBox('+ covariance',self)
        box.setObjectName('refCovarianceCheckBox')
        box.setChecked(False)
        box.setToolTip('Off by default (the owner decides, TODO area B2). On: Export also writes <name>_ref.cov.json '
                       'and <name>_rrf.cov.json beside the text files, for XModFit or any fitter that can use a '
                       'covariance (format: docs/handoff/19, schema v1). The text files do not change. Each sidecar '
                       'holds, point for point, the counting-only error, which scan(s) each point came from, and the '
                       'covariance of the scans\' scale factors: a factor\'s error is shared by every point of its '
                       'scan and of every later scan, so the errors are correlated, and a fit that treats them as '
                       'independent is overconfident (synthetic film fits: parameter pull SDs up to 4 instead of 1). The factors '
                       'are those of the patch (joint or legacy, Preferences); their errors are recomputed from counting '
                       'errors, inflated when the overlap scatters. Only for a Ref Patch reduction; nothing is written if the patch cannot be '
                       'replayed exactly (a message says why).')
        exp=self.ui.refExportPushButton
        save=self.saveButtons.get('ref')
        anchor=save if save is not None else exp

        def find(layout):
            for k in range(layout.count()):
                it=layout.itemAt(k)
                if it.widget() is anchor:
                    return layout,k
                if it.layout() is not None:
                    r=find(it.layout())
                    if r:
                        return r
            return None
        top=anchor.parentWidget().layout() if anchor.parentWidget() is not None else None
        found=find(top) if top is not None else None
        if found:
            found[0].insertWidget(found[1]+1,box)
        self.refCovarianceCheckBox=box

    def saveRefCovariance(self,name):
        """Write <name>_ref.cov.json (and _rrf.cov.json) for the files just
        saved (lss_core.covariance_export): the patch is replayed from the
        unscaled scans with the method it was made with (refMethodUsed), the
        same drops and known factors, and nothing
        is written unless the replay equals the saved arrays (hand-off T10)."""
        from lss_core import covariance_export as ce
        title='Covariance'
        inp=getattr(self,'refPatchInput',None)
        if self.refpatchindex!=1 or inp is None or len(getattr(self,'refPatchOrder',[]))<2:
            self.notify('No covariance written: it exists only for a Ref Patch of two or more scans.',title=title)
            return
        try:
            method=getattr(self,'refMethodUsed',None) or reflectivity.DEFAULT_PATCH_METHOD
            chain=ce.tracked_chain(inp,self.refPatchOrder,self.refDrops,getattr(self,'refFactors',None),method)
            shown=np.asarray(self.refData,dtype=float)
            if shown.ndim!=2 or shown[:,:3].shape!=chain.data.shape or not np.array_equal(shown[:,:3],chain.data):
                self.notify('No covariance written: the patch on show is not the one the last Ref Patch made.',title=title)
                return
            nf=float(self.ui.refNormLineEdit.text()) if self.ui.refNormFacCheckBox.checkState()>0 else None
            rrf=self.ui.refRRFCheckBox.checkState()!=0
            ref,rrfcd=ce.finish(chain.covdata('legacy'),self.refQc,self.refQoff,nf,rrf)
            written=[]
            if np.array_equal(ref.array(),np.asarray(self.normRefData,dtype=float)[:,:3]):
                written.append(ce.write_sidecar(name+'_ref.cov.json',ref,name+'_ref.txt'))
            else:
                self.notify('No covariance written for %s_ref.txt: it does not match the reduction.' % name,title=title)
            if rrfcd is not None and getattr(self,'RrfData',None) is not None:
                if np.array_equal(rrfcd.array(),np.asarray(self.RrfData,dtype=float)[:,:3]):
                    written.append(ce.write_sidecar(name+'_rrf.cov.json',rrfcd,name+'_rrf.txt'))
                else:
                    self.notify('No covariance written for %s_rrf.txt: it does not match the reduction.' % name,title=title)
        except Exception as e:
            self.notify('No covariance written: %s' % e,title=title)
            return
        if written:
            self.notify('Covariance written: '+', '.join(os.path.basename(p) for p in written),title=title,level='info')
    
    def reflectivityScript(self,name):
        """The lss_core call that reproduces the last patched reflectivity."""
        if self.refpatchindex==0 or not hasattr(self,'refScanList'):
            return '# this reflectivity was made with "Analyze"; that path is not scriptable yet'
        scans=[n for n in self.refScanList if n not in self.refDroppedScans]
        kw=['slit=(%s)' % self.ui.refSlitLineEdit.text().strip(),
            'bg_offset=%r' % float(self.ui.refBGOffLineEdit.text()),
            'direction=%r' % str(self.ui.refBGDirComboBox.currentText()),
            'qc=%r' % float(self.ui.refQcLineEdit.text())]
        if float(self.ui.refQoffLineEdit.text())!=0:
            kw.append('qoff=%r' % float(self.ui.refQoffLineEdit.text()))
        if self.ui.refNormFacCheckBox.checkState()!=0:
            kw.append('norm_factor=%r' % float(self.ui.refNormLineEdit.text()))
        if self.ui.refRRFCheckBox.checkState()==0:
            kw.append('rrf=False')
        if self.refDrops:
            kw.append('drops=%r' % {k:v for k,v in sorted(self.refDrops.items())})
        if getattr(self,'refFactors',None):
            kw.append('factors=%r' % {k:(float(v[0]),float(v[1])) for k,v in sorted(self.refFactors.items())})
        if self.refMerged:
            kw.append('merge=%r' % self.refMerged)
        if self.ui.pilLowQzCorCheckBox.checkState()!=0:
            kw.append('low_qz_slit=True')
        if self.refPoints:
            kw.append('points=%r' % self.refPoints)
        if int(self.ui.pilBPCiteSpinBox.value())!=0:
            kw.append('bad_pixel_iterations=%d, bad_pixel_factor=%d' % (int(self.ui.pilBPCiteSpinBox.value()),int(self.ui.pilBPCfacSpinBox.value())))
        if script_kw(getattr(self,'refErrorModel',self.errorModel)):
            kw.append(script_kw(getattr(self,'refErrorModel',self.errorModel)))
        if getattr(self,'refMethodUsed',reflectivity.DEFAULT_PATCH_METHOD)!=reflectivity.DEFAULT_PATCH_METHOD:
            kw.append('method=%r' % self.refMethodUsed)
        lines=['ref = exp.reflectivity(%r, %s)' % (scans,', '.join(kw)),'ref.save(%r)' % name]
        if len(self.ui.backgroundListWidget.selectedItems())>0:
            lines.insert(0,'# note: background images were subtracted in the window; scripts cannot do that yet')
        return '\n'.join(lines)

    def saveTemData(self):
        fid=open(self.directory+'/temp_ref.txt','w')
        for i in range(len(self.refData)):
            if self.refpatchindex==0:
                fid.write(str(self.normRefData[i,0])+'\t'+str(self.normRefData[i,1])+'\t'+str(self.normRefData[i,2])+'\t'+self.refInfoNew[i]+'\n')
        fid.close()
    
    def clearCutGraph(self):
        self.ui.cutPlotMplWidget.canvas.ax.clear()
        self.ui.cutPlotMplWidget.canvas.draw()
        
    def lineAreaCut(self):   # the Line/Area cut buttons
        if self.det is None:
            self.messageBox('Please select scan images before making a cut!')
            return
        self.updateCutData()

    def updateCutData(self):
        if self.det=='Pilatus':
            try:
                if self.pilGIDshow==0 and self.pilGISAXSshow==0:
                    self.updatePilCutData()
                else:
                    if self.ui.pilCutDirComboBox.currentIndex()==0 or self.ui.pilCutDirComboBox.currentIndex()==1:
                        self.updatePilGIDCutData()
                    else:
                        self.messageBox('Please use one of Q cuts for GID data')
                        return
            except:
                self.messageBox('Please enter the appropriate integral type and range')
                self.updatePilCutRange()
                return


    def updatePilCutRange(self):
        if self.ui.pilCutDirComboBox.currentIndex()==0:
            self.ui.pilIntRangeLineEdit.setText('0:1')
        elif self.ui.pilCutDirComboBox.currentIndex()==1:
            self.ui.pilIntRangeLineEdit.setText('1:2')
        elif self.ui.pilCutDirComboBox.currentIndex()==2:
            self.ui.pilIntRangeLineEdit.setText('0:485')
        elif self.ui.pilCutDirComboBox.currentIndex() ==3:
            self.ui.pilIntRangeLineEdit.setText('0:194')

    def updatePilCutData(self):
        self.ui.cutPlotMplWidget.canvas.ax.clear()
        self.selCutPilData={}
        self.selCutPilErrorData={}
        self.cutData={}
        self.cutLabel={}
        try:
            ini=float(str(self.ui.pilIntRangeLineEdit.text()).split(':')[0])
            fin=float(str(self.ui.pilIntRangeLineEdit.text()).split(':')[1])
        except:
            self.messageBox('Please enter the range with the format "min:max"')
            self.updatePilCutRange()
            return
        budget=self.errorModel.budget
        self.selCutTerms={}   # budget error model: monitor parts, applied to each cut point's whole sum
        for i in self.selectedPilFramesNums:
            if len(self.ui.backgroundListWidget.selectedItems())==0:
                # frames are counts: normalise by monitor and absorber first, like
                # every other reduction (PHYSICS_ISSUES P23; owner, 2026-11-17)
                self.selCutPilData[i],self.selCutPilErrorData[i]=self.pilFrameNormalised(i)
                if budget:
                    self.selCutTerms[i]=normalise.frame_terms(('',i),self.selCutPilData[i],self.pilMonc[i],self.errorModel)
            else:   # background-subtracted frames are already normalised
                self.selCutPilData[i]=self.pilData[i]
                self.selCutPilErrorData[i]=self.pilErrorData[i]
                if budget:
                    self.selCutTerms[i]=getattr(self,'pilMonitorTerms',{}).get(i)
        if self.ui.gixSumCheckBox.checkState()!=0 and len(self.ui.backgroundListWidget.selectedItems())==0:
            self.noteMixedAbsorbers([self.pil_AbsNum[i] for i in self.selectedPilFramesNums],'The summed cut')
        legacy=self.sumAllLegacy()
        norms=[self.pilNormaliser(i) for i in self.selectedPilFramesNums]
        if budget and self.ui.gixSumCheckBox.checkState()!=0:
            self.selCutTerms[-1]=MonitorTerms()
            for i,wk in zip(self.selectedPilFramesNums,cuts.sum_weights(norms,legacy)):
                if self.selCutTerms.get(i) is not None:
                    self.selCutTerms[-1].extend(self.selCutTerms[i],wk)
        # the cut itself is lss_core.cuts.frame_cut, shared with Experiment.cut
        direction=self.ui.pilCutDirComboBox.currentIndex()
        axes=str(self.ui.pilAxesComboBox.currentText())
        if self.ui.gixSumCheckBox.checkState()!=0:
            frames=self.selectedPilFramesNums
            d,e=[self.selCutPilData[i] for i in frames],[self.selCutPilErrorData[i] for i in frames]
            # F91 (owner, 2026-11-23): counts and monitors summed, normalised once (ΣN/ΣM);
            # the legacy mean of the normalised frames when the Reduction options say so
            self.selCutPilData[-1],self.selCutPilErrorData[-1]=cuts.mean_frame(d,e) if legacy else cuts.sum_frames(d,e,norms)
            self.cutData[-1]=cuts.frame_cut(self.pilatus,self.selCutPilData[-1],self.selCutPilErrorData[-1],direction,ini,fin,
                                            self.cutGeometry(0),axes=axes,absfac=self.absfac,
                                            absnum=self.pilSelected_AbsNum[0],terms=self.selCutTerms.get(-1))
            self.cutLabel[-1]='summed cuts'
        else:
            for j,i in enumerate(self.selectedPilFramesNums):
                self.cutData[i]=cuts.frame_cut(self.pilatus,self.selCutPilData[i],self.selCutPilErrorData[i],direction,ini,fin,
                                               self.cutGeometry(j),axes=axes,absfac=self.absfac,
                                               absnum=self.pilSelected_AbsNum[j],terms=self.selCutTerms.get(i))
                self.cutLabel[i]=str(self.ui.imageListWidget.item(i).text().split('\t')[0])+' '+str(self.ui.imageListWidget.item(i).text().split('\t')[1])
        if self.ui.gixSumCheckBox.checkState()!=0:
            if self.ui.cutErrorbarCheckBox.checkState()!=0:
                self.ui.cutPlotMplWidget.canvas.ax.errorbar(self.cutData[-1][:,0],self.cutData[-1][:,1],self.cutData[-1][:,2],fmt='o-',label=self.cutLabel[-1])
            else:
                self.ui.cutPlotMplWidget.canvas.ax.plot(self.cutData[-1][:,0],self.cutData[-1][:,1],'o',label=self.cutLabel[-1])

        else:
            fact=1
            if self.ui.cutErrorbarCheckBox.checkState()!=0:
                for i in self.selectedPilFramesNums:
                    self.ui.cutPlotMplWidget.canvas.ax.errorbar(self.cutData[i][:,0],fact*self.cutData[i][:,1],fact*self.cutData[i][:,2],fmt='-',label=self.cutLabel[i])
                    if self.ui.cutOffsetCheckBox.checkState()!=0:
                        fact=fact*float(self.ui.cutOffsetLineEdit.text())
            else:
                for i in self.selectedPilFramesNums:
                    self.ui.cutPlotMplWidget.canvas.ax.plot(self.cutData[i][:,0],fact*self.cutData[i][:,1],'-',label=self.cutLabel[i])
                    if self.ui.cutOffsetCheckBox.checkState()!=0:
                        fact=fact*float(self.ui.cutOffsetLineEdit.text())
        self.updateCutPlotData()

    def cutGeometry(self,j):
        """Geometry of the j-th selected frame, as the image display set it."""
        return cuts.Geometry(self.wavelength[j],self.alpha[j],self.truealpha[j],self.dth[j],self.pilSelected_Sh[j],
                             self.distance[j],self.pilSelected_Dist[j],self.xcenter[j],self.ycenter[j])

    def cutScript(self,name):
        """The lss_core call that reproduces the cuts just exported."""
        if len(self.ui.backgroundListWidget.selectedItems())>0:
            return '# these cuts are of background-subtracted frames; scripts cannot do that yet'
        scans=sorted(set(int(self.pilScanNum[i]) for i in self.selectedPilFramesNums))
        points={}
        for n in scans:
            chosen=[int(self.pilFrameNum[i]) for i in self.selectedPilFramesNums if self.pilScanNum[i]==n]
            listed=[int(self.pilFrameNum[i]) for i in range(len(self.pilScanNum)) if self.pilScanNum[i]==n]
            if chosen!=listed:
                points[n]=chosen
        lo,hi=(float(t) for t in str(self.ui.pilIntRangeLineEdit.text()).split(':'))
        axes=str(self.ui.pilAxesComboBox.currentText())
        kw=['%r' % cuts.DIRECTIONS[self.ui.pilCutDirComboBox.currentIndex()],'(%r, %r)' % (lo,hi)]
        if axes!='Pixels':
            kw.append('axes=%r' % axes)
        if self.ui.gixSumCheckBox.checkState()!=0:
            kw.append('summed=True')
            if self.sumAllLegacy():
                kw.append("sum_mode='mean'")
        if points:
            kw.append('points=%r' % points)
        absfac=self.absorberModel()
        if any(self.pilSelected_AbsNum):
            kw.append('absfac=%r' % absfac)
        if script_kw(self.errorModel):
            kw.append(script_kw(self.errorModel))
        if self.monitorGain:
            kw.append('per_photon=True' if self.monitorPhotons else 'monitor_gain=True')
        if self.ui.pilSpecCheckBox.checkState()==0:
            kw.append('distance=%r' % float(self.ui.pilSDDistLineEdit.text()))
            kw.append('db_pos=(%r, %r)' % tuple(float(t) for t in (self.ui.pilDBPosLineEdit.text().split(',')[0],
                                                                     self.ui.pilDBPosLineEdit.text().split(',')[-1])))
        if self.ui.pilPinholeCheckBox.checkState()==0 and axes in ('Angles','Q'):
            kw.append('pinhole=False')
        if int(self.ui.pilBPCiteSpinBox.value())!=0:
            kw.append('bad_pixel_iterations=%d, bad_pixel_factor=%d' % (int(self.ui.pilBPCiteSpinBox.value()),int(self.ui.pilBPCfacSpinBox.value())))
        head='from lss_core import absorbers\n' if isinstance(absfac,absorbers.Foils) and any(self.pilSelected_AbsNum) else ''
        text=head+'cut = exp.cut(%r, %s)\n' % (scans,', '.join(kw))
        first=int(self.ui.imageListWidget.item(0).text().split('\t')[0].split()[-1])
        if self.ui.gixSumCheckBox.checkState()!=0 and first!=min(scans):   # the window names the file after the list's first scan
            text+='cut.summed_label = %r\n' % ('S# %d' % first)
        return text+'cut.save(%r)' % name

    def updatePilGIDCutData(self):
        self.ui.cutPlotMplWidget.canvas.ax.clear()
        try:
            start=float(self.ui.pilIntRangeLineEdit.text().split(':')[0])
            end=float(self.ui.pilIntRangeLineEdit.text().split(':')[1])
        except:
            self.messageBox('Please enter the range with the format "min:max"')
            self.updatePilCutRange()
            return
        # if str(self.ui.pilAxesComboBox.currentText())=='Angles':
        #     if str(self.ui.pilCutDirComboBox.currentText())=='H Cut':
        #         ini=np.where(self.pilGIDYAxs[:,0]>=start)[0][0]
        #         fin=np.where(self.pilGIDYAxs[:,0]<=end)[0][-1]
        #         xaxis=self.pilGIDXAxs[0,:]
        #         self.cutData=np.vstack((xaxis,np.sum(self.pilGIDData[ini:fin,:],axis=0),np.sqrt(np.sum(self.pilGIDDataErr[ini:fin,:]**2,axis=0)))).transpose()
        #     elif str(self.ui.pilCutDirComboBox.currentText())=='V Cut':
        #         ini=np.where(self.pilGIDXAxs[0,:]>=start)[0][0]
        #         fin=np.where(self.pilGIDXAxs[0,:]<=end)[0][-1]
        #         xaxis=self.pilGIDYAxs[:,0]
        #         self.cutData=np.vstack((xaxis,np.sum(self.pilGIDData[:,ini:fin],axis=1),np.sqrt(np.sum(self.pilGIDDataErr[:,ini:fin]**2,axis=1)))).transpose()
        # elif str(self.ui.pilAxesComboBox.currentText())=='Q':
        if self.pilGISAXSshow==0:
            if self.ui.pilCutDirComboBox.currentIndex()==0:
                ini=np.where(self.pilGIDYAxs_Q[:,0]>=start)[0][0]
                fin=np.where(self.pilGIDYAxs_Q[:,0]<=end)[0][-1]
                xaxis=self.pilGIDXAxs_Q[0,:]
                self.cutData=np.vstack((xaxis,np.sum(self.pilGIDData_Q[ini:fin,:],axis=0),np.sqrt(np.sum(self.pilGIDDataErr_Q[ini:fin,:]**2,axis=0)))).transpose()
            elif self.ui.pilCutDirComboBox.currentIndex()==1:
                ini=np.where(self.pilGIDXAxs_Q[0,:]>=start)[0][0]
                fin=np.where(self.pilGIDXAxs_Q[0,:]<=end)[0][-1]
                xaxis=self.pilGIDYAxs_Q[:,0]
                self.cutData=np.vstack((xaxis,np.sum(self.pilGIDData_Q[:,ini:fin],axis=1),np.sqrt(np.sum(self.pilGIDDataErr_Q[:,ini:fin]**2,axis=1)))).transpose()
        else:
            if self.ui.pilCutDirComboBox.currentIndex()==0:
                ini=np.where(self.pilYbin[:,0]>=start)[0][0]
                fin=np.where(self.pilYbin[:,0]<=end)[0][-1]
                xaxis=self.pilXbin[0,:]
                self.cutData=np.vstack((xaxis,np.sum(self.pilDataBin[ini:fin,:],axis=0),np.sqrt(np.sum(self.pilErrorDataBin[ini:fin,:]**2,axis=0)))).transpose()
            elif self.ui.pilCutDirComboBox.currentIndex()==1:
                ini=np.where(self.pilXbin[0,:]>=start)[0][0]
                fin=np.where(self.pilXbin[0,:]<=end)[0][-1]
                xaxis=self.pilYbin[:,0]
                self.cutData=np.vstack((xaxis,np.sum(self.pilDataBin[:,ini:fin],axis=1),np.sqrt(np.sum(self.pilErrorDataBin[:,ini:fin]**2,axis=1)))).transpose()
        if self.ui.cutErrorbarCheckBox.checkState()!=0:
            self.ui.cutPlotMplWidget.canvas.ax.errorbar(self.cutData[:,0],self.cutData[:,1],self.cutData[:,2],fmt='b-',label='GID Cut')
        else:
            self.ui.cutPlotMplWidget.canvas.ax.plot(self.cutData[:,0],self.cutData[:,1],'b-',label='GID Cut')
        self.updateCutPlotData()
    
    def setupCutFit(self):
        """"Fit peaks" and "Fit options..." beside the line-cut plot (owner,
        2026-11-21): every plotted cut fitted automatically (lss_core.peaks)."""
        self.peakFitOptions=peaks.options_from_dict(self.prefs.get('peak_fit'))     # kept between sessions
        self.mcaFitOptions=peaks.options_from_dict(self.prefs.get('mca_fit'),peaks.FitOptions(background='quadratic',n_peaks=1))
        self.cutFitResults=[]
        self.cutFitArtists=[]
        self.cutFitDialog=None
        self.mcaFitDialog=None
        self.mcaLineFits=None
        b=QPushButton('Fit peaks',self)
        b.setObjectName('cutFitPushButton')
        b.setToolTip('Find and fit the peaks of every plotted cut at once (lss_core.peaks): peaks standing out of a '
                     'running-median background by the chosen number of sigma, each fitted with its neighbours and a '
                     'polynomial background, weighted by the error bars. The fits are drawn dashed over the cuts and '
                     'listed in the Messages pane (centre, FWHM, area with errors, chi2/dof). "Fit options..." sets '
                     'the shape, background, number of peaks, range and sensitivity.')
        o=QPushButton('Fit options...',self)
        o.setObjectName('cutFitOptionsPushButton')
        o.setToolTip('Shape (Gaussian, Lorentzian, pseudo-Voigt), background (none to cubic), number of peaks '
                     '(0: automatic), range, given centres, sensitivity; save the results as a table.')
        self.ui.horizontalLayout_18.addWidget(b)
        self.ui.horizontalLayout_18.addWidget(o)
        b.clicked.connect(self.fitCuts)
        o.clicked.connect(self.showCutFitOptions)
        self.cutFitPushButton,self.cutFitOptionsPushButton=b,o
        # MCA: the lines of a series of spectra (lss_core.peaks.fit_series; F22a)
        fl=QPushButton('Fit lines',self)
        fl.setObjectName('mcaFitLinesPushButton')
        fl.setToolTip('Fit the fluorescence line(s) of all selected spectra (F22a, owner\'s rule): the sum of the spectra '
                      'is fitted within the range in the Sum All field for the lines\' positions and widths; then every '
                      'spectrum is fitted with those fixed, heights and background only (a Gaussian on a quadratic '
                      'background by default, for the Rayleigh spill-over). The intensity of the strongest line, as its '
                      'area over the channel width (the same units as Sum All, background removed), goes to the '
                      'integral plot and list like Sum All. "Fit options..." beside it sets the shape, background, lines.')
        fo=QPushButton('Fit options...',self)
        fo.setObjectName('mcaFitOptionsPushButton')
        fo.setToolTip('Shape, background, number of lines or their energies, sensitivity, for "Fit lines".')
        self.ui.horizontalLayout_37.addWidget(fl)
        self.ui.horizontalLayout_37.addWidget(fo)
        fl.clicked.connect(self.mcaFitLines)
        fo.clicked.connect(self.showMcaFitOptions)
        self.mcaFitLinesPushButton,self.mcaFitOptionsPushButton=fl,fo
        # one-click Save into the SPEC file's workbook beside every Export (owner, 2026-11-21)
        self.saveButtons={}
        for name,export,handler in (('spec',self.ui.spExportPushButton,self.saveSpecToWorkbook),
                                    ('ref',self.ui.refExportPushButton,self.saveRefToWorkbook),
                                    ('cut',self.ui.cutExportPushButton,self.saveCutsToWorkbook),
                                    ('mca',self.ui.mcaExportIntPushButton,self.saveMcaToWorkbook)):
            self.saveButtons[name]=self.addSaveButton(export,handler,name)
        self.setupRefCovarianceBox()

    def cutCurves(self):
        """The plotted cuts as (label, x, y, sigma, scale): scale is the
        offset factor they are drawn with."""
        cd=getattr(self,'cutData',None)
        if cd is None or (isinstance(cd,dict) and not cd):
            return []
        if isinstance(cd,dict):
            if -1 in cd:
                keys=[-1]
            else:
                keys=[i for i in getattr(self,'selectedPilFramesNums',[]) if i in cd]
            out,fact=[],1.0
            for i in keys:
                c=np.asarray(cd[i],float)
                out.append((self.cutLabel.get(i,str(i)),c[:,0],c[:,1],c[:,2],fact))
                if i!=-1 and self.ui.cutOffsetCheckBox.checkState()!=0:
                    try:
                        fact*=float(self.ui.cutOffsetLineEdit.text())
                    except ValueError:
                        pass
            return out
        c=np.asarray(cd,float)
        return [('GID cut',c[:,0],c[:,1],c[:,2],1.0)] if c.ndim==2 and c.shape[1]>=3 else []

    def fitCuts(self):
        """Fit every plotted cut (the "Fit peaks" button)."""
        curves=self.cutCurves()
        if not curves:
            self.messageBox('Make a line cut first: the fit works on the cuts in the plot.')
            return
        ax=self.ui.cutPlotMplWidget.canvas.ax
        for a in self.cutFitArtists:
            try:
                a.remove()
            except (ValueError,AttributeError):
                pass
        self.cutFitArtists=[]
        self.cutFitResults=[]
        opts=self.peakFitOptions
        for k,(label,x,y,s,scale) in enumerate(curves):
            groups=peaks.fit_all(x,y,s,opts)
            self.cutFitResults.append((label,groups))
            colour='C%d' % (k%10) if label!='GID cut' else 'k'
            for g in groups:
                if not g.peaks or not np.all(np.isfinite(g.window)):
                    continue
                xx=np.linspace(g.window[0],g.window[1],400)
                self.cutFitArtists+=ax.plot(xx,scale*g.model(xx),'--',color=colour,lw=1.2)
                for p in g.peaks:
                    self.cutFitArtists.append(ax.axvline(p.centre,color=colour,lw=0.6,ls=':'))
            good=[g for g in groups if g.ok]
            text='; '.join(g.summary() for g in groups) if groups else 'no fit'
            self.notify('Fit of %s: %s' % (label,text),title='Peak fit',level='info' if good else 'warning')
        self.ui.cutPlotMplWidget.canvas.draw()
        if self.cutFitDialog is not None:
            self.cutFitDialog.findChild(QLabel,'cutFitResultLabel').setText(self.cutFitSummary())
        if not any(l=='GID cut' for l,*_ in curves) and getattr(self,'specFileName',None):
            try:
                text=self.cutScript('fitted').rsplit('\n',1)[0]
                self.scriptLine('from lss_core import peaks\n'+text+'\nfits = cut.fit(peaks.%r)' % (opts,))
            except Exception:
                pass

    def cutFitSummary(self):
        lines=[]
        for label,groups in self.cutFitResults:
            for g in groups:
                if not g.ok:
                    lines.append('%s: %s' % (label,g.message))
                for k,p in enumerate(g.peaks):
                    lines.append('%s #%d: centre %.5g +/- %.2g, FWHM %.4g +/- %.2g, area %.4g +/- %.2g (chi2/dof %.2f)'
                                 % (label,k+1,p.centre,p.centre_err,p.fwhm,p.fwhm_err,p.area,p.area_err,g.chi2_dof))
        return '\n'.join(lines) or 'not fitted yet'

    def saveCutFits(self):
        if not self.cutFitResults:
            self.messageBox('Fit the cuts first.')
            return
        name=QFileDialog.getSaveFileName(self,'Save the peak fits',os.path.join(self.directory,'peak_fits.txt'),
                                         'Text (*.txt *.csv)')[0]
        if not name:
            return
        with open(name,'w') as f:
            f.write('# cut\tpeak\tcentre\tcentre_err\tfwhm\tfwhm_err\theight\theight_err\tarea\tarea_err\tchi2_dof\tshape\tbackground\n')
            for label,groups in self.cutFitResults:
                for g in groups:
                    for row in g.table():
                        f.write('%s\t%d\t%s\t%.4f\t%s\t%s\n' % (label,row[0],'\t'.join('%.8g' % v for v in row[1:]),g.chi2_dof,
                                                              g.options.shape,g.options.background))
        self.notify('Peak fits saved: %s' % name,title='Peak fit',level='info')

    def showCutFitOptions(self):
        if self.cutFitDialog is None:
            self.cutFitDialog=self.buildCutFitDialog()
        self.cutFitDialog.show()
        self.cutFitDialog.raise_()

    def buildCutFitDialog(self,which='cut'):
        """The options of "Fit peaks" (``which`` 'cut') or of the MCA's "Fit
        lines" ('mca'): lss_core.peaks.FitOptions, kept in the preferences."""
        attr,pref={'cut':('peakFitOptions','peak_fit'),'mca':('mcaFitOptions','mca_fit')}[which]
        d=QDialog(self)
        d.setWindowTitle('Peak fit options' if which=='cut' else 'Fluorescence line fit options')
        d.setObjectName('%sFitDialog' % which)
        lay=QVBoxLayout(d)
        form=QFormLayout()
        o=getattr(self,attr)
        shape=QComboBox(d); shape.setObjectName('cutFitShapeComboBox')
        shape.addItems(list(peaks.SHAPES)); shape.setCurrentText(o.shape)
        shape.setToolTip('Peak shape: Gaussian (instrument-limited peaks, most GID and fluorescence lines), Lorentzian '
                         '(lifetime or domain-size broadening), pseudo-Voigt (a fitted mix of the two, eta 0 = Gaussian).')
        bg=QComboBox(d); bg.setObjectName('cutFitBackgroundComboBox')
        bg.addItems(list(peaks.BACKGROUNDS)); bg.setCurrentText(o.background)
        bg.setToolTip('Background under the peaks, a polynomial over each fit window: linear for most cuts; quadratic or '
                      'cubic where a slope bends (e.g. the Rayleigh spillover under a fluorescence line).')
        npk=QSpinBox(d); npk.setObjectName('cutFitNumberSpinBox'); npk.setRange(0,20); npk.setValue(o.n_peaks)
        npk.setToolTip('Number of peaks to fit per cut; 0: every peak that stands out (up to the maximum below).')
        mpk=QSpinBox(d); mpk.setObjectName('cutFitMaxSpinBox'); mpk.setRange(1,20); mpk.setValue(o.max_peaks)
        mpk.setToolTip('With 0 above: at most this many peaks, the strongest first.')
        prom=QDoubleSpinBox(d); prom.setObjectName('cutFitProminenceSpinBox'); prom.setRange(1,100); prom.setDecimals(1)
        prom.setValue(o.min_prominence)
        prom.setToolTip('Sensitivity: a peak must stand this many sigma above the running-median background (its three '
                        'central points together) to be found. Lower finds weaker peaks and more noise.')
        win=QDoubleSpinBox(d); win.setObjectName('cutFitWindowSpinBox'); win.setRange(0,1e6); win.setDecimals(4)
        win.setValue(o.window)
        win.setToolTip('Half width of each peak\'s fit window, in the cut\'s x units; 0: three times the peak\'s '
                       'estimated FWHM (at least 6 points). Peaks whose windows overlap are fitted together.')
        fw=QDoubleSpinBox(d); fw.setObjectName('cutFitFwhmSpinBox'); fw.setRange(0,1e6); fw.setDecimals(4)
        fw.setValue(o.fwhm)
        fw.setToolTip('A fixed FWHM for every peak (e.g. the resolution); 0: fitted.')
        rng=QLineEdit(d); rng.setObjectName('cutFitRangeLineEdit')
        rng.setText('' if o.x_range is None else '%g:%g' % tuple(o.x_range))
        rng.setToolTip('x range to fit, "min:max" in the cut\'s x units; empty: the whole cut.')
        cen=QLineEdit(d); cen.setObjectName('cutFitCentresLineEdit')
        cen.setText(', '.join('%g' % c for c in o.centres))
        cen.setToolTip('Centres to start from, comma-separated (e.g. known lines); empty: found automatically.')
        fix=QCheckBox('fix the centres',d); fix.setObjectName('cutFitFixCheckBox'); fix.setChecked(o.fix_centres)
        fix.setToolTip('Keep the given centres fixed and fit only heights, widths and background.')
        for lab,w in (('Shape',shape),('Background',bg),('Peaks per cut (0 = automatic)',npk),('At most',mpk),
                      ('Sensitivity (sigma)',prom),('Window half width (0 = automatic)',win),('Fixed FWHM (0 = fitted)',fw),
                      ('x range (min:max)',rng),('Centres',cen)):
            form.addRow(lab,w)
        form.addRow(fix)
        lay.addLayout(form)
        res=QLabel(self.cutFitSummary() if which=='cut' else self.mcaFitSummary(),d)
        res.setObjectName('%sFitResultLabel' % which); res.setWordWrap(True)
        from PyQt5.QtCore import Qt as QtC
        res.setTextInteractionFlags(QtC.TextSelectableByMouse)
        res.setToolTip('The last fit of every cut; also in the Messages pane.')
        lay.addWidget(res)
        buttons=QHBoxLayout()
        go=QPushButton('Fit now',d); go.setObjectName('cutFitNowPushButton'); go.setToolTip('Fit the plotted cuts with these options')
        save=QPushButton('Save results...',d); save.setObjectName('cutFitSavePushButton')
        save.setToolTip('Write the last fits as a tab-separated table (cut, peak, centre, FWHM, height, area with errors, chi2/dof).')
        close=QPushButton('Close',d)
        for w in (go,save,close):
            buttons.addWidget(w)
        lay.addLayout(buttons)

        def apply(*_):
            try:
                xr=tuple(float(v) for v in rng.text().split(':')) if rng.text().strip() else None
                if xr is not None and len(xr)!=2:
                    raise ValueError
            except ValueError:
                xr=None
            try:
                cs=tuple(float(v) for v in cen.text().replace(';',',').split(',') if v.strip())
            except ValueError:
                cs=()
            new=peaks.FitOptions(shape=shape.currentText(),background=bg.currentText(),n_peaks=npk.value(),
                                 max_peaks=mpk.value(),min_prominence=prom.value(),window=win.value(),
                                 x_range=xr,centres=cs,fix_centres=fix.isChecked(),fwhm=fw.value())
            setattr(self,attr,new)
            self.setPreference(pref,peaks.options_to_dict(new))          # kept between sessions
        for w in (shape,bg):
            w.currentIndexChanged.connect(apply)
        for w in (npk,mpk,prom,win,fw):
            w.valueChanged.connect(apply)
        for w in (rng,cen):
            w.editingFinished.connect(apply)
        fix.toggled.connect(apply)
        go.clicked.connect(lambda: (apply(),self.fitCuts() if which=='cut' else self.mcaFitLines()))
        if which=='cut':
            save.clicked.connect(self.saveCutFits)
        else:
            save.setText('Save to workbook')
            save.setToolTip('Save the fluorescence intensities and the line fits into the workbook (as the Save button).')
            save.clicked.connect(self.saveMcaToWorkbook)
        close.clicked.connect(d.close)
        d.cutFitShapeComboBox,d.cutFitBackgroundComboBox,d.cutFitNumberSpinBox=shape,bg,npk
        d.cutFitRangeLineEdit,d.cutFitCentresLineEdit,d.cutFitNowPushButton=rng,cen,go
        return d

    def addSaveButton(self,beside,handler,name):
        """A Save button just after ``beside`` (an Export button) in its layout."""
        b=QPushButton('Save',self)
        b.setObjectName('%sSaveWorkbookPushButton' % name)
        b.setToolTip('Save what is shown into this SPEC file\'s workbook (<SPEC file>_reader.xlsx in the output folder): '
                     'the reduced data, any fits of it, the settings that made it, tied to its scans and labelled by '
                     'experiment type; each Save of the same scans is a new version. Each Save asks for an optional note '
                     '(Cancel: nothing saved); Shift-click saves without asking (Preferences > Saving turns the '
                     'question off). Export still writes the usual text files.')
        b.clicked.connect(handler)

        def find(layout):
            for k in range(layout.count()):
                it=layout.itemAt(k)
                if it.widget() is beside:
                    return layout,k
                if it.layout() is not None:
                    r=find(it.layout())
                    if r:
                        return r
            return None
        top=beside.parentWidget().layout() if beside.parentWidget() is not None else None
        found=find(top) if top is not None else None
        if found:
            found[0].insertWidget(found[1]+1,b)
        return b

    def workbookPath(self):
        return workbookmod.path_for(self.specFileName,self.directory)

    def saveToWorkbook(self,kind,items,auto=False):
        """Store ``items`` (dicts for lss_core.workbook.Workbook.add_result)
        in the workbook, with a note when asked for; returns the ids.
        ``auto``: saved because a reduction finished (owner, 2026-11-22): no
        note, no message when there is nothing, and a result identical to
        one already stored is not stored again."""
        if not getattr(self,'specFileName',None):
            if not auto:
                self.messageBox('Open a SPEC file first.')
            return []
        if not items:
            if not auto:
                self.messageBox('There is nothing to save here yet.')
            return []
        from PyQt5.QtWidgets import QInputDialog, QApplication
        from PyQt5.QtCore import Qt as QtC
        note=''
        if not auto:
            shift=bool(QApplication.keyboardModifiers() & QtC.ShiftModifier)
            if bool(self.prefs.get('save_asks_note',True)) != shift:   # owner 2026-11-21: ask every time, Shift skips
                note,ok=QInputDialog.getMultiLineText(self,'Note','A note for this saved version (optional):','')
                if not ok:
                    return []
        try:
            wb=self.openWorkbook()
            if auto:
                kept=[]
                for it in items:
                    same=wb.find_content(workbookmod.content_key(kind,**it))
                    if same is None:
                        kept.append(it)
                    elif self.isShownItem(kind,it):
                        self.shownResults[kind]=same      # on screen: the result already stored
                items=kept
                if not items:
                    return []
            wb.set_scans(workbookmod.scan_rows(self.specData,self.specPar))
            wb.set_settings('peak_fit',peaks.options_to_dict(self.peakFitOptions))
            wb.set_settings('mca_fit',peaks.options_to_dict(self.mcaFitOptions))
            wb.set_settings('reduction',self.reductionSettings())
            for it in items:
                if 'series' not in it:
                    it['series']=workbookmod.series_for(it.get('scans',[]),getattr(self,'seriesAll',[]),
                                                        getattr(self,'scanPoints',None))
            ids=[wb.add_result(kind,note=note,origin='auto' if auto else 'user',**it) for it in items]
            self.saveWorkbook(wb)
            for it,i in zip(items,ids):
                if self.isShownItem(kind,it):
                    self.shownResults[kind]=i
        except Exception as e:
            self.workbookCache=None             # what was added in memory but not written is dropped
            self.notify('Could not save to the workbook %s: %s' % (self.workbookPath(),e),title='Save')
            return []
        rows={r['id']:r for r in wb.results()}
        text='%s to %s: %s' % ('Saved automatically' if auto else 'Saved',os.path.basename(self.workbookPath()),
            '; '.join('%s %s, scans %s, %s v%d' % (i,rows[i]['kind'],rows[i]['scans'],rows[i]['label'] or '',
                                                   rows[i]['version']) for i in ids))
        if auto:                        # quiet: the status bar and the log, not the Messages pane
            self.ui.statusBar.showMessage(text,8000)
            self.log.info(text)
        else:
            self.notify(text,title='Save',level='info')
        return ids

    AUTO_SAVE_AFTER={'updateRefPlotData':'ref','updatePilCutData':'cut','updatePilGIDCutData':'cut','fitCuts':'cut',
                     'gidFinishMap':'gid','mcaSumAll':'mca','mcaFitLines':'mca','mcaIntMerge':'mca','burnTrends':'burn'}

    def wrapReductionsForAutoSave(self):
        """Each method that finishes a reduction (AUTO_SAVE_AFTER) is wrapped
        before the signals are connected, so that every way of reaching it
        schedules an automatic save; saves are made once the event loop is
        idle, one per kind however many of the methods ran."""
        import functools
        import inspect
        self.autoSavePending=[]
        self.shownResults={}          # workbook kind -> id of the saved result a display shows
        for name,which in self.AUTO_SAVE_AFTER.items():
            real=getattr(self,name)
            params=inspect.signature(real).parameters.values()
            nargs=None if any(p.kind==p.VAR_POSITIONAL for p in params) else \
                sum(1 for p in params if p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD))

            @functools.wraps(real)
            def wrapped(*a,_real=real,_which=which,_n=nargs,**k):
                # a signal may pass arguments the method does not take (clicked's "checked")
                out=_real(*(a if _n is None else a[:_n]),**k)
                self.scheduleAutoSave(_which)
                return out
            setattr(self,name,wrapped)

    def scheduleAutoSave(self,which):
        if not bool(self.prefs.get('auto_save',True)) or getattr(self,'suppressAutoSave',False):
            return
        if which not in self.autoSavePending:
            self.autoSavePending.append(which)
            if len(self.autoSavePending)==1:
                QTimer.singleShot(0,self.flushAutoSave)

    def flushAutoSave(self):
        pending,self.autoSavePending=self.autoSavePending,[]
        for which in pending:
            self.autoSave(which)

    def openWorkbook(self):
        """The workbook of the open SPEC file, kept in memory between saves
        (opening one costs about 0.6 s per GID map in it); read again when
        the file changed outside the reader (Excel) or is another file."""
        path=self.workbookPath()
        mtime=os.path.getmtime(path) if os.path.exists(path) else None
        cached=getattr(self,'workbookCache',None)
        if cached is not None and cached[0]==path and cached[1]==mtime and mtime is not None:
            return cached[2]
        wb=workbookmod.Workbook(path)
        self.workbookCache=(path,mtime,wb)
        return wb

    def saveWorkbook(self,wb):
        wb.save()
        self.workbookCache=(wb.path,os.path.getmtime(wb.path),wb)

    def isShownItem(self,kind,item):
        """Whether a saved item is what a display shows (a reflectivity's 'R',
        not its 'R/RF'; the other kinds have one item)."""
        return kind!='reflectivity' or item.get('label')=='R'

    def showRemade(self,kind,res,nid):
        """Put a remade result (lss_core objects from the worker) into the
        window and redraw the display that showed the old one (owner,
        2026-11-22); not saved again (it is stored already)."""
        self.suppressAutoSave=True
        try:
            if kind=='reflectivity' and getattr(self,'refpatchindex',0)!=0:
                self.refData=[list(r[:3]) for r in np.asarray(res.patched,float)]
                self.updateRefPlotData()
            elif kind=='fluorescence':
                self.mcaIntData=[list(r) for r in res.rows]
                self.updateMcaIntPlot()
            elif kind=='burn test' and getattr(self,'uipdburn',None) is not None and self.uipdburn.isVisible():
                self.burnResult=res
                self.plotBurnTrends(res)
                self.uipdburn.burnResultLabel.setText(self.burnShortText(res))
                self.uipdburn.burnResultLabel.setToolTip(self.burnLongText(res))
            elif kind=='gid map' and getattr(self,'pilGIDshow',0)==1:
                self.pilGIDXAxs,self.pilGIDYAxs,self.pilGIDData,self.pilGIDDataErr=res.x,res.y,res.data,res.err
                self.gidLevels=list(res.levels)
                if res.info:
                    self.gidPinholeInfo,self.gidJoinInfo=res.info.get('levels'),res.info.get('join')
                self.gidShowMap()
            else:
                return
            self.shownResults[kind]=nid
            self.ui.statusBar.showMessage('Live: the %s shown is now %s' % (kind,nid),8000)
        finally:
            self.suppressAutoSave=False

    def autoSave(self,which):
        """Save what a reduction has just made into the workbook (owner,
        2026-11-22: "make saving in the excel file automatic once a
        reduction/processing has been carried through"); Preferences >
        Saving turns it off. ``which``: 'ref', 'cut', 'mca', 'gid', 'burn'."""
        if not bool(self.prefs.get('auto_save',True)) or not getattr(self,'specFileName',None):
            return
        handler={'ref':self.saveRefToWorkbook,'cut':self.saveCutsToWorkbook,'mca':self.saveMcaToWorkbook,
                 'gid':self.saveGIDToWorkbook,'burn':self.saveBurnToWorkbook}[which]
        self.autoSaving=True
        try:
            handler()
        except Exception as e:                  # saving must never break the reduction it follows
            self.log.info('automatic save (%s) failed: %s',which,e)
        finally:
            self.autoSaving=False

    def saveNotice(self,text):
        """A save handler's "nothing to save" message: silent when saving automatically."""
        if not getattr(self,'autoSaving',False):
            self.messageBox(text)

    def checkStaleResults(self):
        """After the SPEC file is read or updated: saved results whose series
        has changed since (more scans, another status) are marked stale in
        the workbook, with a message. The step towards live updates (F1–F5)."""
        try:
            path=self.workbookPath()
        except Exception:
            return
        if not os.path.exists(path):
            return
        try:
            wb=self.openWorkbook()
            before={r['id']:r.get('stale') for r in wb.results()}
            stale=wb.mark_stale(getattr(self,'seriesAll',[]),getattr(self,'scanPoints',None))
            after={r['id']:r.get('stale') for r in wb.results()}
            if after!=before:
                self.saveWorkbook(wb)
        except Exception as e:
            self.workbookCache=None
            self.log.info('workbook %s not checked: %s',path,e)
            return
        new={k:v for k,v in stale.items() if before.get(k)!=v}
        if new and self.liveOn():
            self.remakeStale(wb,new)
        elif new:
            self.notify('%d saved result(s) in %s are out of date: %s' % (
                len(new),os.path.basename(path),'; '.join('%s: %s' % kv for kv in sorted(new.items()))),
                title='Workbook',level='info')

    def reductionSettings(self):
        """The settings that shape reduced data, for the workbook."""
        out={}
        try:
            out['absorber']=str(self.absorberModel())
        except Exception:
            pass
        out['monitor_gain']=bool(getattr(self,'monitorGain',False))
        out['per_photon']=bool(getattr(self,'monitorPhotons',False))
        out['error_model']=str(getattr(self.errorModel,'budget',False) and 'budget' or 'legacy')
        try:
            from dataclasses import asdict
            out['gid']=asdict(self.gidParams)
        except Exception:
            pass
        return out

    def recipe(self,builder):
        """The lss_core call that remakes a saved result (the Script pane's
        text with 'result' as the output name), or '' when there is none."""
        try:
            text=builder('result')
        except Exception:
            return ''
        return text if text and not text.lstrip().startswith('#') else ''

    def saveSpecToWorkbook(self):
        if len(self.selectedScanNums)==0 or str(self.ui.spXComboBox.currentText())=='':
            self.saveNotice('Please select a scan with data to save first!')
            return
        xc,yc,nc=(str(c.currentText()) for c in (self.ui.spXComboBox,self.ui.spYComboBox,self.ui.spNComboBox))
        norm=self.ui.spNCheckBox.checkState()!=0
        items=[]
        for i in self.selectedScanNums:
            d=self.specData[i]
            if xc not in d or yc not in d or (norm and nc not in d):
                continue
            x,y=np.asarray(d[xc],float),np.asarray(d[yc],float)
            yerr=np.sqrt(np.abs(y))
            cols=[xc,yc,'d'+yc]
            if norm:
                n=np.asarray(d[nc],float)
                g=self.monitorGainFactor(i,nc)
                yerr=np.sqrt(np.abs(y)/n**2+y**2/n**3)*g
                y=y/n*g
                cols=[xc,'%s/%s' % (yc,nc),'d(%s/%s)' % (yc,nc)]
            fits=[('%s vs %s' % (yc,xc),self.specFit)] if i==self.selectedScanNums[-1] and getattr(self,'specFit',None) is not None else []
            items.append(dict(scans=[i],data=np.column_stack([x,y,yerr]),columns=cols,label='%s vs %s%s' % (yc,xc,' / '+nc if norm else ''),
                              fits=fits,settings=dict(x=xc,y=yc,monitor=nc if norm else None)))
        self.saveToWorkbook('scan',items,auto=getattr(self,'autoSaving',False))

    def saveRefToWorkbook(self):
        if self.det!='Pilatus' or len(getattr(self,'refData',[]))==0 or getattr(self,'normRefData',None) is None:
            self.saveNotice('There is no reflectivity data to save yet')
            return
        scans=sorted(int(n) for n in self.selectedScanNums)
        d=np.asarray(self.normRefData,float)
        cols=['Qz','R','dR','dQz'][:d.shape[1]]
        items=[dict(scans=scans,data=d,columns=cols,label='R',settings=dict(command=str(getattr(self,'command',''))),
                    recipe=self.recipe(self.reflectivityScript))]
        rrf=getattr(self,'RrfData',None)
        if rrf is not None and len(rrf):
            r=np.asarray(rrf,float)
            items.append(dict(scans=scans,data=r,columns=['Qz','R/RF','d(R/RF)','dQz'][:r.shape[1]],label='R/RF'))
        self.saveToWorkbook('reflectivity',items,auto=getattr(self,'autoSaving',False))

    def saveCutsToWorkbook(self):
        curves=self.cutCurves()
        if not curves:
            self.saveNotice('Make a line cut first.')
            return
        cd=self.cutData
        keys=[-1] if isinstance(cd,dict) and -1 in cd else ([i for i in getattr(self,'selectedPilFramesNums',[]) if isinstance(cd,dict) and i in cd])
        fits={label:groups for label,groups in self.cutFitResults}
        direction=str(self.ui.pilCutDirComboBox.currentText())
        settings=dict(direction=direction,range=str(self.ui.pilIntRangeLineEdit.text()),axes=str(self.ui.pilAxesComboBox.currentText()))
        items=[]
        for k,(label,x,y,sg,scale) in enumerate(curves):
            if label=='GID cut':
                scans=sorted({int(n) for lv in getattr(self,'gidLevels',[]) for n in lv[1]})
                kind='gid cut'
            else:
                key=keys[k] if k<len(keys) else None
                frames=getattr(self,'selectedPilFramesNums',[]) if key==-1 else ([key] if key is not None else [])
                scans=sorted({int(self.pilScanNum[i]) for i in frames})
                kind='line cut'
            items.append(dict(scans=scans,data=np.column_stack([x,y,sg]),columns=[direction.split()[0]+' x','I','dI'],
                              label='%s, %s %s' % (label,direction,settings['range']),settings=settings,
                              fits=[(label,fits[label])] if label in fits else [],
                              recipe='' if label=='GID cut' else self.recipe(self.cutScript)))
        self.saveToWorkbook('gid cut' if curves[0][0]=='GID cut' else 'line cut',items,auto=getattr(self,'autoSaving',False))

    def saveMcaToWorkbook(self):
        rows=getattr(self,'mcaIntData',None)
        if not rows:
            self.saveNotice('Sum or fit the fluorescence first (Sum All or Fit lines).')
            return
        scans=sorted(int(n) for n in self.selectedScanNums)
        fits=[]
        if self.mcaLineFits is not None:
            ref,each,nums=self.mcaLineFits
            fits=[('sum of %d spectra' % len(each),ref)]+[('frame %d' % (n+1),r) for n,r in zip(nums,each)]
        items=[dict(scans=scans,data=np.asarray(rows,float),columns=['frame','Qz','energy','I','dI'],
                    label=str(getattr(self,'command','')),fits=fits,settings=dict(command=str(getattr(self,'command',''))),
                    recipe='' if fits else self.recipe(self.fluorescenceScript))]
        self.saveToWorkbook('fluorescence',items,auto=getattr(self,'autoSaving',False))

    def saveGIDToWorkbook(self):
        if getattr(self,'pilGIDData',None) is None or not getattr(self,'gidLevels',None):
            self.saveNotice('Patch a GID map first.')
            return
        scans=sorted({int(n) for lv in self.gidLevels for n in lv[1]})
        from dataclasses import asdict
        items=[dict(scans=scans,map_xyz=(self.pilGIDXAxs,self.pilGIDYAxs,self.pilGIDData,self.pilGIDDataErr),
                    label='2theta, beta (deg)',settings=asdict(self.gidParams),
                    recipe=self.recipe(lambda name:self.gidScript(name,'Q')))]
        self.saveToWorkbook('gid map',items,auto=getattr(self,'autoSaving',False))

    def mcaFitLines(self):
        """Fit the selected spectra's lines (lss_core.peaks.fit_series)."""
        nums=list(getattr(self,'selectedMcaScanNums',[]) or [])
        if not nums or not all(n in self.nomMcaData for n in nums):
            self.messageBox('Select and plot MCA spectra first.')
            return
        data=[np.asarray(self.nomMcaData[n],float) for n in nums]
        if any(len(d)!=len(data[0]) or not np.allclose(d[:,0],data[0][:,0]) for d in data):
            self.messageBox('The selected spectra have different energy axes; fit them in groups with the same axis.')
            return
        x=data[0][:,0]
        o=self.mcaFitOptions
        if o.x_range is None:
            try:
                lo,hi=(float(t) for t in str(self.ui.mcaRanLineEdit.text()).split(':'))
                o=dataclasses.replace(o,x_range=(lo,hi))
            except ValueError:
                pass
        ref,each=peaks.fit_series(x,[d[:,1] for d in data],[d[:,2] for d in data],o)
        if not each:
            self.notify('Fit lines: %s' % (ref.message or 'no line found'),title='Fit lines')
            return
        step=float(np.median(np.abs(np.diff(x))))
        self.mcaIntData=[]
        self.ui.mcaDataListWidget.clear()
        for n,r in zip(nums,each):
            p=r.peaks[0]
            inten,err=p.area/step,p.area_err/step
            frame=n+1
            qz=self.mcaPar[n]['Q'][2]
            energy=self.mcaPar[n].get('Energy',10.0) if isinstance(self.mcaPar[n],dict) else 10.0
            self.mcaIntData.append([frame,qz,energy,inten,err])
            xv=(frame,qz,energy)[min(self.ui.mcaXAxisComboBox.currentIndex(),2)]
            self.ui.mcaDataListWidget.addItem(('%d' % xv if self.ui.mcaXAxisComboBox.currentIndex()==0 else '%.4f' % xv)+
                                              '\t%.4e\t%.4e' % (inten,err))
        self.mcaSumScript=None
        self.mcaMerges=[]
        self.mcaLineFits=(ref,each,nums)
        self.updateMcaIntPlot()
        try:
            ax=self.ui.mcaPlotMplWidget.canvas.ax
            for r in each[:20]:
                xx=np.linspace(r.window[0],r.window[1],300)
                ax.plot(xx,r.model(xx),'k--',lw=0.8)
            self.ui.mcaPlotMplWidget.canvas.draw()
        except Exception:
            pass
        p=ref.peaks[0]
        self.command='Flu Fit lines, scans=[%s], line at %.4g (FWHM %.3g), %s on %s background' % (
            listText(np.sort(self.selectedScanNums)),p.centre,p.fwhm,o.shape,o.background)
        self.ui.commandLineEdit.setText(self.command)
        self.notify('Fit lines: sum of %d spectra: %s. Intensities of the line at %.4g (area / channel width) in the '
                    'integral plot.' % (len(each),ref.summary(),p.centre),title='Fit lines',level='info')
        if self.mcaFitDialog is not None:
            self.mcaFitDialog.findChild(QLabel,'mcaFitResultLabel').setText(self.mcaFitSummary())

    def mcaFitSummary(self):
        if self.mcaLineFits is None:
            return 'not fitted yet'
        ref,each,nums=self.mcaLineFits
        return 'Sum of %d spectra: %s' % (len(each),ref.summary())

    def showMcaFitOptions(self):
        if self.mcaFitDialog is None:
            self.mcaFitDialog=self.buildCutFitDialog('mca')
        self.mcaFitDialog.show()
        self.mcaFitDialog.raise_()

    def updateCutPlotData(self):
        if self.det!='Pilatus':   # no cut plotted: display options do nothing
            return
        self.ui.PlotWidget.setCurrentIndex(4) 
        self.cutLogX=self.ui.cutLogXCheckBox.checkState()
        self.cutLogY=self.ui.cutLogYCheckBox.checkState()
        self.cutGrid=self.ui.cutGridCheckBox.checkState()
        self.ui.cutPlotMplWidget.canvas.ax.set_xscale('linear')
        self.ui.cutPlotMplWidget.canvas.ax.set_yscale('linear')
        self.ui.cutPlotMplWidget.canvas.ax.set_ylabel('Intensity')
        self.ui.cutPlotMplWidget.canvas.ax.grid(visible=False)
        title='File: '+self.specFileName+' S# '+listText(np.sort(self.selectedScanNums))
        if self.det=='Pilatus':
            currentcutindex=self.ui.pilCutDirComboBox.currentIndex()
            cutrange=str(self.ui.pilIntRangeLineEdit.text())
        if currentcutindex==2:
            self.ui.cutPlotMplWidget.canvas.ax.set_title(title+'\n'+'H Cut     Vint Range['+cutrange+']', fontsize=16)
            self.ui.cutPlotMplWidget.canvas.ax.set_xlabel('Pixels', fontsize=16)
        elif currentcutindex==3:
            self.ui.cutPlotMplWidget.canvas.ax.set_title(title+'\n'+'V Cut     Hint Range['+cutrange+']', fontsize=16)
            self.ui.cutPlotMplWidget.canvas.ax.set_xlabel('Pixels', fontsize=16)
        elif currentcutindex==0:
            self.ui.cutPlotMplWidget.canvas.ax.set_title(title+'\n'+'Q H Cut     Qz Range['+cutrange+']', fontsize=16)
            self.ui.cutPlotMplWidget.canvas.ax.set_xlabel(r'$Q_{xy}$'+' '+r'$[\AA^{-1}]$', fontsize=16)
        else:
            self.ui.cutPlotMplWidget.canvas.ax.set_title(title+'\n'+'Q V Cut     Qxy Range['+cutrange+']', fontsize=16)
            self.ui.cutPlotMplWidget.canvas.ax.set_xlabel(r'$Q_z$'+' '+r'$[\AA^{-1}]$', fontsize=16)
        if self.cutLogX!=0:
            self.ui.cutPlotMplWidget.canvas.ax.set_xscale('log')
        if self.cutLogY!=0:
            self.ui.cutPlotMplWidget.canvas.ax.set_yscale('log')
        if self.cutGrid!=0:
            self.ui.cutPlotMplWidget.canvas.ax.grid(visible=True,color='r',linestyle='--')
        if self.ui.cutLegendCheckBox.checkState()!=0:
            self.ui.cutPlotMplWidget.canvas.ax.legend(loc=self.ui.cutLegendLocComboBox.currentIndex()+1,frameon=False,scatterpoints=0,numpoints=1)
        self.ui.cutPlotMplWidget.canvas.draw()
        
    def saveCutData(self):
        if self.det!='Pilatus' or len(self.cutData)==0:
            self.messageBox('There is no cut to save yet, please make a cut first!')
            return
        if isinstance(self.cutData,dict):   # per-frame or summed cuts: they must match the present selection
            summed=self.ui.gixSumCheckBox.checkState()!=0
            frames=self.selectedPilFramesNums
            if (summed and -1 not in self.cutData) or (not summed and any(i not in self.cutData for i in frames)) or (not summed and len(frames)==0):
                self.messageBox('The frame selection or the "Sum" option changed after the cut was made. Please make the cut again before saving.')
                return
        self.saveFileName=QFileDialog.getSaveFileName(caption='Save Cuts', directory=self.directory)[0]
        if self.saveFileName=='':   # dialog cancelled
            return
        if self.det=='Pilatus':
            if self.pilGIDshow==0 and self.pilGISAXSshow==0:
                if self.ui.gixSumCheckBox.checkState()!=0:
                    self.fname=self.saveFileName+str(self.ui.imageListWidget.item(0).text().split('\t')[0])+'_sumcut.txt'
                    np.savetxt(self.fname,self.cutData[-1],fmt='%.4f\t%.4e\t%.4e')
                else:
                    for i in self.selectedPilFramesNums:
                        self.fname=self.saveFileName+str(self.ui.imageListWidget.item(i).text().split('\t')[0])+'_'+str(self.ui.imageListWidget.item(i).text().split('\t')[1])+'_cut.txt'
                        np.savetxt(self.fname,self.cutData[i],fmt='%.4f\t%.4e\t%.4e')
                self.scriptLine(self.cutScript(self.saveFileName))
            else:
                self.fname=self.saveFileName
                np.savetxt(self.fname,self.cutData,fmt='%.4f\t%.4e\t%.4e')
        
            
            
    def displayScanInfo(self):
        Dialog=QDialog(self)
        ui=uic.loadUi(resource('scanInfoDialog.ui'),Dialog)
        ui.show()
        snumtit=''
        impsnumtit=''
        for i in self.selectedScanNums:
            try:
                for j in range(self.specRead.Data[i]['StartScanLineNum'],self.specRead.Data[i+1]['StartScanLineNum']):
                    snumtit=snumtit+self.specRead.SpecFileFull[j]
            except:
                for j in range(self.specRead.Data[i]['StartScanLineNum'],len(self.specRead.SpecFileFull)):
                    snumtit=snumtit+self.specRead.SpecFileFull[j]
            try:
                impsnumtit=impsnumtit+self.specData[i]['ScanLine']+'\n'
                impsnumtit=impsnumtit+'Detector:\t'+self.specPar[i]['Detector']+'\n\n'
                impsnumtit=impsnumtit+'Energy:\t'+str(format(12.39842/self.specPar[i]['Wavelength'],'.4f'))+' keV\n\n'
                impsnumtit=impsnumtit+'Wavelength:\t'+str(self.specPar[i]['Wavelength'])+' '+u'\u212b'+'\n\n'  
                impsnumtit=impsnumtit+'Absorber\t'+('unknown' if self.specPar[i].get('Absorber') is None else str(self.specPar[i]['Absorber']))+'\n\n'
                impsnumtit=impsnumtit+'SX\t'+str(self.specPar[i]['Sample_X'])+'\n\n'
                impsnumtit=impsnumtit+'Qx\tQy\tQz\n'
                impsnumtit=impsnumtit+str(self.specPar[i]['Q'][0])+'\t'+str(self.specPar[i]['Q'][1])+'\t'+str(self.specPar[i]['Q'][2])+'\n\n'
                impsnumtit=impsnumtit+'S1 [H, V]\tS4 [H, V]\tS5 [H]\n'
                impsnumtit=impsnumtit+'['+str(format(self.specPar[i]['S1L']+self.specPar[i]['S1R'],'.3f'))+', '+str(format(self.specPar[i]['S1T']+self.specPar[i]['S1B'],'.3f'))+']\t'+'['+str(format(self.specPar[i]['S4L']+self.specPar[i]['S4R'],'.1f'))+', '+str(format(self.specPar[i]['S4T']+self.specPar[i]['S4B'],'.1f'))+']\t'+'['+str(format(self.specPar[i]['S5L']+self.specPar[i]['S5R'],'.1f'))+']\n\n'
                impsnumtit=impsnumtit+'S2 [H, V]\tS3 [H, V]\tS7 [H, V]\n'
                impsnumtit=impsnumtit+'['+str(format(self.specPar[i]['S2L']+self.specPar[i]['S2R'],'.1f'))+', '+str(format(self.specPar[i]['S2T']+self.specPar[i]['S2B'],'.1f'))+']\t'+'['+str(format(self.specPar[i]['S3L']+self.specPar[i]['S3R'],'.1f'))+', '+str(format(self.specPar[i]['S3T']+self.specPar[i]['S3B'],'.1f'))+']\t'+'['+str(format(self.specPar[i]['S7L']+self.specPar[i]['S7R'],'.1f')+', '+str(format(self.specPar[i]['S7T']+self.specPar[i]['S7B'],'.1f')))+']\n\n'
                if self.specPar[i]['Detector']=='Pilatus':
                    impsnumtit=impsnumtit+'pd[x, y]:\t['+str(self.specPar[i]['DBPos'][0])+', '+str(self.specPar[i]['DBPos'][1])+']\n'
                impsnumtit=impsnumtit+'-----------------------------------------------\n'
            except:
                impsnumtit='No detailed info found in SPEC file!!!'
        ui.scanInfoTextBrowser.append(snumtit)
        ui.impInfoTextBrowser.append(impsnumtit)
        
        Dialog.exec_()  
        
            
        
    def g_lfunction(self,par,x,y):
        return y-par[0]+par[1]*np.sin(x*np.pi/180)
        
    def calg_l2(self):
        if not self.calScansReady():
            return
        Dialog=QDialog(self)
        self.uig_l2=uic.loadUi(resource('g_l2Dialog.ui'), Dialog)
        self.uig_l2.show()
        scannum=list(self.selectedScanNums)   # scan numbers already (the list's text), not row indices
       # self.g_l2alpha=[self.specPar[i]['In_Rot'] for i in self.selectedScanNums]
        self.g_l2alpha = [round(np.arctan(round(self.specPar[i]['Q'][2], 3) * self.specPar[i]['Wavelength'] / 4 / np.pi) * 180 / np.pi, 5) for i in self.selectedScanNums]
        self.g_l2center=[self.scanCenter[i] for i in self.selectedScanNums]
        self.g_l2=[self.specPar[i]['g_l2'] for i in self.selectedScanNums]
        self.uig_l2.g_l2ScanLineEdit.setText(str(scannum)[1:-1])
        self.uig_l2.g_l2CenterLineEdit.setText(str(self.g_l2center)[1:-1])
        # self.connect(self.uig_l2.g_l2CalPushButton,SIGNAL('clicked()'), self.g_l2plot)
        self.uig_l2.g_l2CalPushButton.clicked.connect(self.g_l2plot)
        Dialog.exec_()
        
    def g_l2plot(self):
        self.uig_l2.g_l2TextBrowser.clear()
        if len(self.g_l2alpha)<2:   # two unknowns (offset and length) need at least two scans
            self.messageBox('Please select at least two scans taken at different incident angles for this calibration.')
            return
        if self.uig_l2.g_l2centercheckBox.checkState()!=0:
            self.g_l2center=list(map(float, str(self.uig_l2.g_l2CenterLineEdit.text()).split(',')))
        par=[0,self.specPar[self.selectedScanNums[0]]['g_l2']]
        p=leastsq(self.g_lfunction,par,args=(np.array(self.g_l2alpha),np.array(self.g_l2center)),maxfev=5000)
        fp=p[0]
        self.uig_l2.g_l2plotWidget.canvas.ax.clear()
        self.uig_l2.g_l2plotWidget.canvas.ax.plot(self.g_l2alpha,self.g_l2center,'ro')
        self.uig_l2.g_l2plotWidget.canvas.ax.plot(np.array(self.g_l2alpha),fp[0]-fp[1]*np.sin(np.array(self.g_l2alpha)*np.pi/180),'-b',label=('g_l2= %.3f'%fp[1]))
        self.uig_l2.g_l2plotWidget.canvas.ax.set_xlabel('Alpha [Degrees]')
        self.uig_l2.g_l2plotWidget.canvas.ax.set_ylabel('Sh_Center [mm]')
        self.uig_l2.g_l2plotWidget.canvas.ax.legend(frameon=False,scatterpoints=0,numpoints=1)
        self.uig_l2.g_l2plotWidget.canvas.draw()
        self.uig_l2.g_l2TextBrowser.append(':Old Values:')
        self.uig_l2.g_l2TextBrowser.append('-----------------------------------------')
        self.uig_l2.g_l2TextBrowser.append('Scan \t Alpha \t Sh Nom \t Sh Cen \t N-C' )
        j=0
        for i in self.selectedScanNums:
            self.uig_l2.g_l2TextBrowser.append(str(i+1)+' \t %.5f '%self.g_l2alpha[j]+'\t %.4f'%(-np.sin(self.g_l2alpha[j]*np.pi/180)*self.g_l2[j])+'\t %.4f '%self.g_l2center[j]+'\t %.4f '%(-np.sin(self.g_l2alpha[j]*np.pi/180)*self.g_l2[j]-self.g_l2center[j]))
            j=j+1
        self.uig_l2.g_l2TextBrowser.append('\n')
        self.uig_l2.g_l2TextBrowser.append(':New Values:')
        self.uig_l2.g_l2TextBrowser.append('-----------------------------------------')
        self.uig_l2.g_l2TextBrowser.append('Scan \t Alpha \t Sh Nom \t Sh Cen \t N-C' )
        j=0
        for i in self.selectedScanNums:
            self.uig_l2.g_l2TextBrowser.append(str(i+1)+' \t %.5f '%self.g_l2alpha[j]+'\t %.4f'%(fp[0]-np.sin(self.g_l2alpha[j]*np.pi/180)*fp[1])+'\t %.4f '%self.g_l2center[j]+'\t %.4f '%(-np.sin(self.g_l2alpha[j]*np.pi/180)*fp[1]+fp[0]-self.g_l2center[j]))
            j=j+1
        self.uig_l2.g_l2TextBrowser.append('\n')
        self.uig_l2.g_l2TextBrowser.append('old g_l2\t= %.3f'%self.g_l2[0])
        self.uig_l2.g_l2TextBrowser.append('new g_l2\t= %.3f'%fp[1])
        self.uig_l2.g_l2TextBrowser.append('offset\t= %.3f'%fp[0])
        
    def calg_l3(self):
        if not self.calScansReady():
            return
        Dialog=QDialog(self)
        self.uig_l3=uic.loadUi(resource('g_l3Dialog.ui'), Dialog)
        self.uig_l3.show()
        scannum=list(self.selectedScanNums)   # scan numbers already (the list's text), not row indices
        #self.g_l3alpha=[self.specPar[i]['In_Rot'] for i in self.selectedScanNums]
        self.g_l3alpha = [round(np.arctan(round(self.specPar[i]['Q'][2], 3) * self.specPar[i]['Wavelength'] / 4 / np.pi) * 180 / np.pi, 5) for i in self.selectedScanNums]
        self.g_l3center=[self.scanCenter[i] for i in self.selectedScanNums]
        self.g_l3=[self.specPar[i]['g_l3'] for i in self.selectedScanNums]
        self.g_l2=[self.specPar[i]['g_l2'] for i in self.selectedScanNums]
        self.uig_l3.g_l3ScanLineEdit.setText(str(scannum)[1:-1])
        self.uig_l3.g_l3CenterLineEdit.setText(str(self.g_l3center)[1:-1])
        # self.connect(self.uig_l3.g_l3CalPushButton,SIGNAL('clicked()'), self.g_l3plot)
        self.uig_l3.g_l3CalPushButton.clicked.connect(self.g_l3plot)
        Dialog.exec_()
        
    def g_l3plot(self):
        self.uig_l3.g_l3TextBrowser.clear()
        if len(self.g_l3alpha)<2:   # two unknowns (offset and length) need at least two scans
            self.messageBox('Please select at least two scans taken at different incident angles for this calibration.')
            return
        if self.uig_l3.g_l3centercheckBox.checkState()!=0:
            self.g_l3center=list(map(float, str(self.uig_l3.g_l3CenterLineEdit.text()).split(',')))
        par=[0,self.specPar[self.selectedScanNums[0]]['g_l2']-self.specPar[self.selectedScanNums[0]]['g_l3']]
        p=leastsq(self.g_lfunction,par,args=(np.array(self.g_l3alpha),np.array(self.g_l3center)),maxfev=5000)
        fp=p[0]
        self.uig_l3.g_l3plotWidget.canvas.ax.clear()
        self.uig_l3.g_l3plotWidget.canvas.ax.plot(self.g_l3alpha,self.g_l3center,'ro')
        self.uig_l3.g_l3plotWidget.canvas.ax.plot(np.array(self.g_l3alpha),fp[0]-fp[1]*np.sin(np.array(self.g_l3alpha)*np.pi/180),'-b',label=('g_l2-g_l3= %.3f'%fp[1]))
        self.uig_l3.g_l3plotWidget.canvas.ax.set_xlabel('Alpha [Degrees]')
        self.uig_l3.g_l3plotWidget.canvas.ax.set_ylabel('Oh_Center [mm]')
        self.uig_l3.g_l3plotWidget.canvas.ax.legend(frameon=False,scatterpoints=0,numpoints=1)
        self.uig_l3.g_l3plotWidget.canvas.draw()
        self.uig_l3.g_l3TextBrowser.append(':Old Values:')
        self.uig_l3.g_l3TextBrowser.append('-----------------------------------------')
        self.uig_l3.g_l3TextBrowser.append('Scan \t Alpha \t Oh Nom \t Oh Cen \t N-C' )
        j=0
        for i in self.selectedScanNums:
            self.uig_l3.g_l3TextBrowser.append(str(i+1)+' \t %.5f '%self.g_l3alpha[j]+'\t %.4f'%(np.sin(self.g_l3alpha[j]*np.pi/180)*(self.g_l3[j]-self.g_l2[j]))+'\t %.4f '%self.g_l3center[j]+'\t %.4f '%(np.sin(self.g_l3alpha[j]*np.pi/180)*(self.g_l3[j]-self.g_l2[j])-self.g_l3center[j]))
            j=j+1
        self.uig_l3.g_l3TextBrowser.append('\n')
        self.uig_l3.g_l3TextBrowser.append(':New Values:')
        self.uig_l3.g_l3TextBrowser.append('-----------------------------------------')
        self.uig_l3.g_l3TextBrowser.append('Scan \t Alpha \t Oh Nom \t Oh Cen \t N-C' )
        j=0
        for i in self.selectedScanNums:
            self.uig_l3.g_l3TextBrowser.append(str(i+1)+' \t %.5f '%self.g_l3alpha[j]+'\t %.4f'%(fp[0]-np.sin(self.g_l3alpha[j]*np.pi/180)*fp[1])+'\t %.4f '%self.g_l3center[j]+'\t %.4f '%(-np.sin(self.g_l3alpha[j]*np.pi/180)*fp[1]+fp[0]-self.g_l3center[j]))
            j=j+1
        self.uig_l3.g_l3TextBrowser.append('\n')
        self.uig_l3.g_l3TextBrowser.append('old (g_l2-g_l3)\t= %.3f'%(self.g_l2[0]-self.g_l3[0]))
        self.uig_l3.g_l3TextBrowser.append('new (g_l2_g_l3)\t= %.3f'%fp[1])
        self.uig_l3.g_l3TextBrowser.append('offset\t\t= %.3f'%fp[0])
    
    def absratiofunction(self,par,x,y):
        return y-np.log(par[0])+x*np.log(par[1])+par[2]*par[0]/par[1]**x
        #return y-par[0]/np.power(par[1],x)
        
    def calScansReady(self):   # the g_l calibrations need plotted scans with a fitted centre
        if len(self.selectedScanNums)==0:
            self.messageBox('Please select the scans first!')
            return False
        if any(i not in self.scanCenter for i in self.selectedScanNums):
            self.messageBox('Please plot the selected scans first, the scan centers come from the peak fit!')
            return False
        return True

    def calabsrat(self):
        if len(self.selectedScanNums)==0:
            self.messageBox('Please select an absorber scan first!')
            return
        scannum=self.selectedScanNums[0]
        if self.specData[scannum]['ScanVar'][0]!='Absorber':
            self.messageBox('Error:: This scan is NOT an absorber scan!!')
        else:
            Dialog=QDialog(self)
            uiabs=uic.loadUi(resource('absratioDialog.ui'), Dialog)
            uiabs.show()
            x=self.specData[scannum]['Absorber']
            z=self.specData[scannum]['Monc']
            ave=sum(z)/float(len(z))
            y=np.log(self.specData[scannum][str(self.ui.spYComboBox.currentText())]/z*ave/self.specData[scannum]['Seconds'])
            par=[1.0e+10,1.5,1.0e-8]
            #par=[1.0e+10,1.6]
            p=leastsq(self.absratiofunction,par,args=(x,y),maxfev=5000)
            fp=p[0]
            #print fp, y
            uiabs.absRatplotWidget.canvas.ax.clear()
            uiabs.absRatplotWidget.canvas.ax.plot(x,np.exp(y),'ro')
            uiabs.absRatplotWidget.canvas.ax.plot(x,fp[0]/fp[1]**x*np.exp(-fp[2]*par[0]/fp[1]**x),'-b')
            uiabs.absRatplotWidget.canvas.ax.set_xlabel('Absorber Number')
            uiabs.absRatplotWidget.canvas.ax.set_ylabel('Intensity')
            uiabs.absRatplotWidget.canvas.ax.set_yscale('log')
            uiabs.absRatplotWidget.canvas.draw()
            uiabs.absRatScanLineEdit.setText(str(scannum+1))
            uiabs.absRatAbsLineEdit.setText(str(fp[1]))
            uiabs.absRatSouLineEdit.setText('%.3e'%fp[0])
            uiabs.absRatDeaLineEdit.setText('%.3e'%fp[2])
            Dialog.exec_()
        
    def updatePlotFile(self): #update plot files in the listwidget
        self.ui.plotFileListWidget.clear()
        for i in range(len(self.plotfiles)):
            try:  #for pc
                self.ui.plotFileListWidget.addItem('#'+str(i+1)+self.halftab+str(self.plotfiles[i].split('\\')[-2])+'\\'+str(self.plotfiles[i].split('\\')[-1]))
            except: #for mac and linux
                self.ui.plotFileListWidget.addItem('#'+str(i+1)+self.halftab+str(self.plotfiles[i].split('/')[-2])+'/'+str(self.plotfiles[i].split('/')[-1]))

    def addPlotFile(self): #add plot files into the listwidget and deselect all ref files in the listwidget
        f=QFileDialog.getOpenFileNames(caption='Select Multiple Files to import', directory=self.directory, filter='Files (*.*)')[0]
        self.plotfiles=self.plotfiles+list(map(str, f))
        self.updatePlotFile()
        
    def updateSelectedPlotFile(self): #update the selected ref files in the listwidget
        selectedplotfiles=self.ui.plotFileListWidget.selectedItems()
        self.fitplotstatus=0
        self.selectedplotfiles_rows=[]
        for item in selectedplotfiles:
            self.selectedplotfiles_rows.append(self.ui.plotFileListWidget.row(item))
        self.selectedplotfiles_rows.sort()
        self.plotscale=[[1,0,1,0] for i in range(len(self.selectedplotfiles_rows))]
        self.updatePlotPlot()
        
    def removePlotFile(self): #remove plot files in the listwidget and deselect all ref files in the listwidget
        items=self.ui.plotFileListWidget.selectedItems()
        items.reverse()
        for item in items:
            self.plotfiles.pop(self.ui.plotFileListWidget.row(item))
        self.ui.plotFileListWidget.clear()
        self.updatePlotFile()
                
        
    def upPlotFile(self):
        rows=self.selectedplotfiles_rows
        for i in rows:
            self.plotfiles.insert(max(0,i-1),self.plotfiles.pop(i))
        self.updatePlotFile()
        for i in rows:
            self.ui.plotFileListWidget.item(i-1).setSelected(True)#setItemSelected(self.ui.plotFileListWidget.item(i-1),True)
        
    def downPlotFile(self):
        rows=self.selectedplotfiles_rows
        rows.reverse()
        for i in self.selectedplotfiles_rows:
            self.plotfiles.insert(min(len(self.plotfiles),i+1),self.plotfiles.pop(i))   
        self.updatePlotFile()
        for i in rows:
            self.ui.plotFileListWidget.item(i+1).setSelected(True)#setItemSelected(self.ui.plotFileListWidget.item(i+1),True)
        
    def updatePlotPlot(self): #update the plot in the plot plotwidget
        self.ui.PlotMplWidget.canvas.ax.clear()
        labelsize=self.ui.onedLabelSizeSpinBox.value()
        ticksize=self.ui.onedTickSizeSpinBox.value()
        if self.ui.onedStyComboBox.currentIndex()==0:
            style='o'
        elif self.ui.onedStyComboBox.currentIndex()==1:
            style='-'
        elif self.ui.onedStyComboBox.currentIndex()==2:
            style='o-'
        if  len(self.selectedplotfiles_rows)!=0: #plot plot files
            for i in range(len(self.selectedplotfiles_rows)):
                try:
                    data1=np.loadtxt(str(self.plotfiles[self.selectedplotfiles_rows[i]]), comments='#')
                except:
                    QMessageBox.warning(self, 'File Error','The data file doesnot seems to have column data only. Please check',QMessageBox.Ok)
                    return
                data1=data1[np.argsort(data1[:,0])]
                try:  #for pc
                    datalabel=str(self.plotfiles[self.selectedplotfiles_rows[i]].split('\\')[-1])
                except: #for mac and linux
                    datalabel=str(self.plotfiles[self.selectedplotfiles_rows[i]].split('/')[-1])
                try:
                    self.ui.PlotMplWidget.canvas.ax.errorbar(data1[:,0]*self.plotscale[i][0]+self.plotscale[i][1],data1[:,1]*self.plotscale[i][2]+self.plotscale[i][3],data1[:,2]*self.plotscale[i][2],fmt=style,label='#'+str(self.selectedplotfiles_rows[i]+1)+' '+datalabel)
                except:
                    self.ui.PlotMplWidget.canvas.ax.plot(data1[:,0]*self.plotscale[i][0]+self.plotscale[i][1],data1[:,1]*self.plotscale[i][2]+self.plotscale[i][3],'-',label='#'+str(self.selectedplotfiles_rows[i]+1)+' '+datalabel)
        if self.fitplotstatus!=0:  #add fit result
            fitdata=np.array(self.peakfitdata)
            fitbgdata=np.array(self.peakbgfitdata)
            self.ui.PlotMplWidget.canvas.ax.plot(fitdata[:,0],fitdata[:,1],'r-')
            self.ui.PlotMplWidget.canvas.ax.plot(fitbgdata[:,0],fitbgdata[:,1],'g-')
        if self.ui.plotLogXCheckBox.checkState()!=0:
            self.ui.PlotMplWidget.canvas.ax.set_xscale('log')
        if self.ui.plotLogYCheckBox.checkState()!=0:
            self.ui.PlotMplWidget.canvas.ax.set_yscale('log')
        if self.ui.plotGridCheckBox.checkState()!=0:
            self.ui.PlotMplWidget.canvas.ax.grid(visible=True,color='r',linestyle='--')
        if self.ui.plotLegendCheckBox.checkState()!=0:
            self.ui.PlotMplWidget.canvas.ax.legend(loc=self.ui.plotLegendLocComboBox.currentIndex()+1,frameon=False,scatterpoints=0,numpoints=1)
        self.ui.PlotMplWidget.canvas.ax.set_xlabel('X', fontsize=labelsize)
        self.ui.PlotMplWidget.canvas.ax.set_ylabel('Y', fontsize=labelsize)
        self.ui.PlotMplWidget.canvas.ax.tick_params(labelsize=ticksize)
        self.ui.PlotMplWidget.canvas.draw()
        
    def graPlotPlot(self): #deriative data wiht x-axis having equal spacing
        self.ui.PlotMplWidget.canvas.ax.clear()
        labelsize=self.ui.onedLabelSizeSpinBox.value()
        ticksize=self.ui.onedTickSizeSpinBox.value()
        if self.ui.onedStyComboBox.currentIndex()==0:
            style='o'
        elif self.ui.onedStyComboBox.currentIndex()==1:
            style='-'
        elif self.ui.onedStyComboBox.currentIndex()==2:
            style='o-'
        if  len(self.selectedplotfiles_rows)!=0: #plot plot files
            for i in range(len(self.selectedplotfiles_rows)):
                data1=np.loadtxt(str(self.plotfiles[self.selectedplotfiles_rows[i]]), comments='#')
                data1=data1[np.argsort(data1[:,0])]
                x=np.linspace(data1[:,0][0],data1[:,0][-1],len(data1))
                fint=interp1d(data1[:,0], data1[:,1], kind='linear')
                y=fint(x)
                y=np.gradient(y)
                self.gradata=np.vstack((x,y)).T
                try:  #for pc
                    datalabel=str(self.plotfiles[self.selectedplotfiles_rows[i]].split('\\')[-1])
                except: #for mac and linux
                    datalabel=str(self.plotfiles[self.selectedplotfiles_rows[i]].split('/')[-1])
                self.ui.PlotMplWidget.canvas.ax.plot(self.gradata[:,0],self.gradata[:,1],style,label='#'+str(self.selectedplotfiles_rows[i]+1)+' '+datalabel)
        if self.ui.plotLogXCheckBox.checkState()!=0:
            self.ui.PlotMplWidget.canvas.ax.set_xscale('log')
        if self.ui.plotLogYCheckBox.checkState()!=0:
            self.ui.PlotMplWidget.canvas.ax.set_yscale('log')
        if self.ui.plotGridCheckBox.checkState()!=0:
            self.ui.PlotMplWidget.canvas.ax.grid(visible=True,color='r',linestyle='--')
        if self.ui.plotLegendCheckBox.checkState()!=0:
            self.ui.PlotMplWidget.canvas.ax.legend(loc=self.ui.plotLegendLocComboBox.currentIndex()+1,frameon=False,scatterpoints=0,numpoints=1)
        self.ui.PlotMplWidget.canvas.ax.set_xlabel('X', fontsize=labelsize)
        self.ui.PlotMplWidget.canvas.ax.set_ylabel('Y', fontsize=labelsize)
        self.ui.PlotMplWidget.canvas.ax.set_title('Derivative', fontsize=labelsize)
        self.ui.PlotMplWidget.canvas.ax.tick_params(labelsize=ticksize)
        self.ui.PlotMplWidget.canvas.draw()
        
    def saveGraPlotData(self): #save the derivative data
        try:
            self.saveFileName=str(QFileDialog.getSaveFileName(caption='Save Derivative Data',directory=self.directory)[0])
            if self.saveFileName=='':   # dialog cancelled: write nothing
                return
            fitfile=self.saveFileName+'_der.txt'
            np.savetxt(fitfile,self.gradata,fmt='%.4e\t%.4e')
        except:
            pass
    
    def setPlotScale(self): #set the scale of each data in the plot
        if len(self.selectedplotfiles_rows)==0:
            self.messageBox('Warning:: No files selected!')
        else:
            row=len(self.selectedplotfiles_rows)
            Dialog=QDialog(self)
            self.uiplotscale=uic.loadUi(resource('plotscale.ui'), Dialog)
            self.uiplotscale.scaleTW.setRowCount(row) #set the table size; 4 column is fixed
            self.uiplotscale.show()
            self.uiplotscale.scaleLabel.setText('Plot Scale Setup: X=X*Factor+Offset')
            self.uiplotscale.scaleTW.setHorizontalHeaderLabels(["X Factor","X Offset","Y Factor","Y Offset"]) #set the horizontal header
            vlabel=[]#QStringList() #set the vertical header
            for i in range(row):
                vlabel.append("#"+str(self.selectedplotfiles_rows[i]+1))
            self.uiplotscale.scaleTW.setVerticalHeaderLabels(vlabel)
            for i in range(row):  #set the initial values
                for j in range(4):
                    self.uiplotscale.scaleTW.setItem(i,j,QTableWidgetItem(str(self.plotscale[i][j])))
                    self.uiplotscale.scaleTW.item(i,j).setTextAlignment(Qt.AlignCenter)
            # self.connect(self.uiplotscale.scaleTW, SIGNAL('cellChanged(int,int)'), self.updatePlotScale) #update the ref scale and plot
            self.uiplotscale.scaleTW.cellChanged.connect(self.updatePlotScale)
            # self.connect(self.uiplotscale.closePB,SIGNAL('clicked()'), self.closePlotScale) #close the scale setup window
            self.uiplotscale.closePB.clicked.connect(self.closePlotScale)
            
    def updatePlotScale(self): #update the scale of each data in the plot
        row=len(self.selectedplotfiles_rows)
        self.plotscale=[[float(str(self.uiplotscale.scaleTW.item(i,j).text())) for j in range(4)] for i in range(row)]
        self.updatePlotPlot()
        
    def closePlotScale(self): #close the plot scale window'
        self.uiplotscale.close()
        
        
    def dataPeakFit(self): #fit the data in the "Plot" work window
        self.mcafitstatus=0
        self.peakFit()
        
    def peakFit(self): #fit the data with lor and gua functions and the polynomial background
        if self.mcafitstatus==0 and len(self.selectedplotfiles_rows)!=1 and self.mcafitallstatus==0:
            self.messageBox('Warning:: Please select only one file!!')
        elif self.mcafitstatus==1 and len(self.nomMcaData)!=1 and self.mcafitallstatus==0:
            self.messageBox('Warning:: Please select only one mca frame')
        else:
            Dialog=QDialog(self)
            self.uipeakfit=uic.loadUi(resource('peakfit.ui'), Dialog)
            self.uipeakfit.show()
            try:
                self.uipeakfit.rangeLineEdit.setText(str(self.peakfitranini)+':'+str(self.peakfitranfin))
            except:
                pass
            try:
                self.uipeakfit.numberOfPeakSpinBox.setValue(len(self.fitpeakpara))
                self.uipeakfit.bgSpinBox.setValue(len(self.fitbgpara)-1)
            except:
                pass
            peakrow=self.uipeakfit.numberOfPeakSpinBox.value()
            bgrow=self.uipeakfit.bgSpinBox.value()+1
            self.uipeakfit.peakTW.setRowCount(peakrow) #set the row for peak parameter; 3 colomn is fixed
            self.uipeakfit.bgTW.setRowCount(bgrow) #set the row for bg parameters
            self.uipeakfit.peakTW.setHorizontalHeaderLabels(["Location","Intensity","Width"])
            peakvlabel=[]#QStringList()
            bgvlabel=[]#QStringList()
            for i in range(peakrow):
                peakvlabel.append("#"+str(i+1))
            self.uipeakfit.peakTW.setVerticalHeaderLabels(peakvlabel)
            for i in range(bgrow):
                bgvlabel.append("C"+str(i))
            self.uipeakfit.bgTW.setVerticalHeaderLabels(bgvlabel)

            try:
                self.fitpeakpara = self.fitpeakpara
                self.fitbgpara = self.fitbgpara
            except:
                self.fitpeakpara = [[1, 1, 1] for i in range(peakrow)]
                self.fitbgpara = [0 for i in range(bgrow)]

            self.peakparadic={}
            self.peakbgparadic={}            
            for i in range(peakrow): # set values
                for j in range(3):
                    self.uipeakfit.peakTW.setItem(i,j,QTableWidgetItem(str(self.fitpeakpara[i][j])))
                    self.peakparadic[3*i+j]=[self.fitpeakpara[i][j],False,None,None]
            for i in range(bgrow): 
                self.uipeakfit.bgTW.setItem(i,0,QTableWidgetItem(str(self.fitbgpara[i])))
                self.peakbgparadic[i]=[self.fitbgpara[i],False,None,None]
            self.updatePeakParaName()
            # self.connect(self.uipeakfit.closePushButton, SIGNAL('clicked()'), self.closePeakFit) #close the peak fit window
            self.uipeakfit.closePushButton.clicked.connect(self.closePeakFit)
            # self.connect(self.uipeakfit.fitPushButton, SIGNAL('clicked()'), self.fitPeakFit) #fit the selected data
            self.uipeakfit.fitPushButton.clicked.connect(self.fitPeakFit)
            # self.connect(self.uipeakfit.numberOfPeakSpinBox, SIGNAL('valueChanged(int)'), self.modPeakPara) #change parameters with number of peaks
            self.uipeakfit.numberOfPeakSpinBox.valueChanged.connect(self.modPeakPara)
            # self.connect(self.uipeakfit.bgSpinBox, SIGNAL('valueChanged(int)'), self.modBGPara) #change parameters for the bg
            self.uipeakfit.bgSpinBox.valueChanged.connect(self.modBGPara)
            # self.connect(self.uipeakfit.exportFitPushButton,SIGNAL('clicked()'), self.savePeakFit) #save peak fit
            self.uipeakfit.exportFitPushButton.clicked.connect(self.savePeakFit)
            # self.connect(self.uipeakfit.exportParaPushButton,SIGNAL('clicked()'), self.savePeakPara) #save peak fit
            self.uipeakfit.exportParaPushButton.clicked.connect(self.savePeakPara)
            # self.connect(self.uipeakfit.peakTW,SIGNAL('cellDoubleClicked(int,int)'),partial(self.setupPeakPara,'peak')) #setup the peak para limits.
            self.uipeakfit.peakTW.cellDoubleClicked.connect(partial(self.setupPeakPara, 'peak'))
            # self.connect(self.uipeakfit.bgTW,SIGNAL('cellDoubleClicked(int,int)'),partial(self.setupPeakPara,'bg')) #setup the peak bg para limits.
            self.uipeakfit.bgTW.cellDoubleClicked.connect(partial(self.setupPeakPara,'bg'))
    
    def closePeakFit(self): # close the peak fit window
        self.uipeakfit.close()
        
    def updatePeakParaName(self): #update peak and bg para name
        self.peakparaname=[]
        self.peakbgparaname=[]
        for i in range(self.uipeakfit.peakTW.rowCount()):
            self.peakparaname=self.peakparaname+['Loc'+str(i+1),'Int'+str(i+1),'Wid'+str(i+1)]
        for i in range(self.uipeakfit.bgTW.rowCount()):
            self.peakbgparaname.append('C'+str(i))
            
    
    def modPeakPara(self): #modify peak parameter table
        diff=self.uipeakfit.peakTW.rowCount()-self.uipeakfit.numberOfPeakSpinBox.value()
        row=self.uipeakfit.peakTW.rowCount()
        if diff>0:
            for i in range(diff):
                self.uipeakfit.peakTW.removeRow(row-i-1)
                for j in range(3):
                    self.peakparadic.pop(3*(row-i-1)+j)
        else:
            for i in range(-diff):
                self.uipeakfit.peakTW.insertRow(row)
                for j in range(3):
                    self.uipeakfit.peakTW.setItem(row,j,QTableWidgetItem('1/1/1'.split('/')[j]))
                    self.peakparadic[3*row+j]=[1,False,None,None]
                row=row+1
        peakvlabel=[]
        for i in range(row-diff):
                peakvlabel.append("#"+str(i+1))
        self.uipeakfit.peakTW.setVerticalHeaderLabels(peakvlabel)
        self.updatePeakParaName()
        
        
    def modBGPara(self): #modify bg parameter table
        diff=self.uipeakfit.bgTW.rowCount()-self.uipeakfit.bgSpinBox.value()-1
        row=self.uipeakfit.bgTW.rowCount()
        if diff>0:
            for i in range(diff):
                self.uipeakfit.bgTW.removeRow(row-i-1)
                self.peakbgparadic.pop(row-i-1)
        else:
            for i in range(-diff):
                self.uipeakfit.bgTW.insertRow(row)
                self.uipeakfit.bgTW.setItem(row,0,QTableWidgetItem('0'))
                self.peakbgparadic[row]=[0,False,None,None]
                row=row+1
        bgvlabel=[]
        for i in range(row-diff):
                bgvlabel.append("C"+str(i))
        self.uipeakfit.bgTW.setVerticalHeaderLabels(bgvlabel)
        self.updatePeakParaName()
        
    def setupPeakPara(self, index):
        Dialog=QDialog(self)
        self.uipara=uic.loadUi(resource('peakpara.ui'), Dialog)
        if index=='peak':
            selrow=self.uipeakfit.peakTW.currentRow()
            selcol=self.uipeakfit.peakTW.currentColumn()
            self.paranum=selrow*3+selcol
            self.uipara.label.setText('Limits Setup of Parameter:'+self.peakparaname[self.paranum])
            if self.peakparadic[self.paranum][2]!=None: 
                self.uipara.minCB.setCheckState(2)
                self.uipara.minLE.setText(str(self.peakparadic[self.paranum][2]))
            if self.peakparadic[self.paranum][3]!=None: 
                self.uipara.maxCB.setCheckState(2)
                self.uipara.maxLE.setText(str(self.peakparadic[self.paranum][3]))
        else:
            self.paranum=self.uipeakfit.bgTW.currentRow()
            self.uipara.label.setText('Limits Setup of Parameter:'+self.peakbgparaname[self.paranum])
            if self.peakbgparadic[self.paranum][2]!=None: 
                self.uipara.minCB.setCheckState(2)
                self.uipara.minLE.setText(str(self.peakbgparadic[self.paranum][2]))
            if self.peakbgparadic[self.paranum][3]!=None: 
                self.uipara.maxCB.setCheckState(2)
                self.uipara.maxLE.setText(str(self.peakbgparadic[self.paranum][3]))
        self.uipara.show()
        # self.connect(self.uipara.cancelPB, SIGNAL('clicked()'), self.cancelPeakPara)
        self.uipara.cancelPB.clicked.connect(self.cancelPeakPara)
        # self.connect(self.uipara.okPB, SIGNAL('clicked()'), partial(self.takePeakPara,index))
        self.uipara.okPB.clicked.connect(partial(self.takePeakPara,index))
        
    def cancelPeakPara(self):
        self.uipara.close()
        
    def takePeakPara(self, index):
        if self.uipara.minCB.checkState()!=0 and self.uipara.maxCB.checkState()!=0 and float(self.uipara.minLE.text())>float(self.uipara.maxLE.text()):
            self.messageBox("Error:: Low constrain must be smaller than high constrain!!!")
        else:
            if index=='peak':
                if self.uipara.minCB.checkState()!=0:
                    self.peakparadic[self.paranum][2]=float(self.uipara.minLE.text())
                else:
                    self.peakparadic[self.paranum][2]=None
                if self.uipara.maxCB.checkState()!=0:
                    self.peakparadic[self.paranum][3]=float(self.uipara.maxLE.text())
                else:
                    self.peakparadic[self.paranum][3]=None
            else:
                if self.uipara.minCB.checkState()!=0:
                    self.peakbgparadic[self.paranum][2]=float(self.uipara.minLE.text())
                else:
                    self.peakbgparadic[self.paranum][2]=None
                if self.uipara.maxCB.checkState()!=0:
                    self.peakbgparadic[self.paranum][3]=float(self.uipara.maxLE.text())
                else:
                    self.peakbgparadic[self.paranum][3]=None
            self.uipara.close()
        
    def fitPeakFit(self):
        if (self.mcafitallstatus!=0 or self.mcafitstatus!=0) and (len(self.selectedMcaScanNums)==0 or any(i not in self.nomMcaData for i in self.selectedMcaScanNums)):
            self.messageBox('The MCA frames this fit was opened for are no longer selected. Please select them again.')
            return
        if self.mcafitallstatus==0 and self.mcafitstatus==0 and len(self.selectedplotfiles_rows)!=1:
            self.messageBox('Please select one file in the "Plot" tab to fit.')
            return
        if self.mcafitallstatus==0:
            if self.mcafitstatus==0:
                data=np.loadtxt(str(self.plotfiles[self.selectedplotfiles_rows[0]]), comments='#')
#                self.ui.PlotMplWidget.canvas.ax.clear()
#                self.ui.PlotMplWidget.canvas.ax.errorbar(data[:,0],data[:,1],data[:,2],fmt='o-')
            else:
                data=self.nomMcaData[self.selectedMcaScanNums[0]]
            self.fitPeak(data)
        else:  #for mca data fit all
           # print self.selectedMcaScanNums
           # print self.nomMcaData
            self.mcaIntData=[]
            self.ui.mcaDataListWidget.clear()
            for i in range(len(self.selectedMcaScanNums)):
                data=self.nomMcaData[self.selectedMcaScanNums[i]]
                self.mcafitstatus==1
                self.mcaLabelOne=str(i+1)
                success=self.fitPeak(data,num=i)
                if success:
                    self.mcaAcceptPeak(num=i)
            self.mcafitallstatus=0
            self.uipeakfit.close()
        
    
    def fitPeak(self,data, num=0): #fit the peak
        data=data[np.argsort(data[:,0])]
        try:
            ini=max(float(str(self.uipeakfit.rangeLineEdit.text()).split(':')[0]),data[0][0])
            fin=min(float(str(self.uipeakfit.rangeLineEdit.text()).split(':')[1]),data[-1][0])
        except:
            self.messageBox('Warning: Please input the fit range with the format "0:1"!')
            self.uipeakfit.rangeLineEdit.setText('0:1')
            return

        self.peakfitranini=float(str(self.uipeakfit.rangeLineEdit.text()).split(':')[0])
        self.peakfitranfin=float(str(self.uipeakfit.rangeLineEdit.text()).split(':')[1])
        data1=data[np.where(np.logical_and(data[:,0]>=ini,data[:,0]<=fin))]
        if len(data1)==0:
            self.messageBox('Warning: There is no data within the fit range!')
            return
        peaknumber=self.uipeakfit.numberOfPeakSpinBox.value()
        peaktype=str(self.uipeakfit.peakTypeComboBox.currentText())
        bgorder=self.uipeakfit.bgSpinBox.value()
        x=data1[:,0]
        y=data1[:,1]
        yerr=data1[:,2]
        try:
            yerr[yerr==0]=np.min(yerr[np.nonzero(yerr)]) #replace zero with minumun nonzero value
        except:
            yerr[yerr == 0]=1
            self.messageBox('All error bar values are zero, replacing them by 1')
        x0=np.linspace(x[0],x[-1],len(x)*10)
        self.fitpeakpara=[[float(str(self.uipeakfit.peakTW.item(i,j).text())) for j in range(3)] for i in range(peaknumber)]
        if peaknumber==1:
            inten=np.max(y)
            locat=np.sum(x*y)/np.sum(y)
            width=np.sqrt(np.sum(y*(x-locat)**2)/np.sum(y)/2)
            self.fitpeakpara=[[locat,inten,width]]
        self.fitbgpara=[float(str(self.uipeakfit.bgTW.item(i,0).text())) for i in range(bgorder+1)]
        if self.mcafitstatus!=0 or self.mcafitallstatus!=0:   # for fluorescence fitting 
            if peaktype=='Gaussian':        
                p=[[value for sublist in self.fitpeakpara for value in sublist],self.fitbgpara]
                flag=[0,peaknumber]
            else:
                p=[[value for sublist in self.fitpeakpara for value in sublist],self.fitbgpara]
                flag=[1,peaknumber]
            p0=[float(value) for sublist in p for value in sublist]
            pfit,pcov,info,errmsg,ier=leastsq(self.peakres,p0,args=(x,y,yerr,flag), full_output=1)

            if (ier>4 or pcov is None):
                self.messageBox("Could NOT fit Frame #"+str(num)+"!")
                return False
            #print(pcov)
            #print(info,errmsg,ier)
            residual=self.peakres(pfit,x,y,yerr,flag)
            self.chisquare=np.sum(residual**2)/(len(x)-len(p0))
            self.fiterror=[np.sqrt(self.chisquare*pcov[i,i]) for i in range(len(p0))]
            if flag[0]==0:
                self.peakfitdatay=sum(self.gaufun(x0,pfit[3*i:3*i+3]) for i in range(flag[1]))+self.polyfun(x0,pfit[3*flag[1]:])
            else:
                self.peakfitdatay=sum(self.lorfun(x0,pfit[3*i:3*i+3]) for i in range(flag[1]))+self.polyfun(x0,pfit[3*flag[1]:])
            self.peakfitdata=[[x0[i],self.peakfitdatay[i]] for i in range(len(x0))]
            #return True
        else: # regluar fitting 
            self.fitpeakpara=[value for sublist in self.fitpeakpara for value in sublist]
            for i in range(3*peaknumber):
                self.peakparadic[i][0]=self.fitpeakpara[i]
            for i in range(bgorder+1):
                self.peakbgparadic[i][0]=float(str(self.uipeakfit.bgTW.item(i,0).text()))
            index=self.uipeakfit.peakTW.selectionModel().selectedIndexes()  #get selected cell for peak
            bgindex=self.uipeakfit.bgTW.selectionModel().selectedIndexes() #get selected cell for bg 
            selrows=[self.uipeakfit.peakTW.row(self.uipeakfit.peakTW.itemFromIndex(index[i])) for i in range(len(index))] #get selected cells for peak and bg
            selcols=[self.uipeakfit.peakTW.column(self.uipeakfit.peakTW.itemFromIndex(index[i])) for i in range(len(index))]
            selbgrows=[self.uipeakfit.bgTW.row(self.uipeakfit.bgTW.itemFromIndex(bgindex[i])) for i in range(len(bgindex))]
            #print selrows, selcols, selbgrows
            selparas=[3*selrows[i]+selcols[i] for i in range(len(selrows))]
            for i in range(len(self.peakparadic)):  #set selected peak parameters to be varied
                if i in selparas:
                    self.peakparadic[i][1]=True
                else:
                    self.peakparadic[i][1]=False
            for i in range(len(self.peakbgparadic)):  #set selected bg paramenter to be varied
                if i in selbgrows:
                    self.peakbgparadic[i][1]=True
                else:
                    self.peakbgparadic[i][1]=False
                
            self.peakparameter=Parameters()  #set up the parameter for lmfit
            for i in range(len(self.peakparadic)):
                self.peakparameter.add(self.peakparaname[i], value=self.peakparadic[i][0],vary=self.peakparadic[i][1],min=self.peakparadic[i][2],max=self.peakparadic[i][3])
            for i in range(len(self.peakbgparadic)):
                self.peakparameter.add(self.peakbgparaname[i], value=self.peakbgparadic[i][0],vary=self.peakbgparadic[i][1],min=self.peakbgparadic[i][2],max=self.peakbgparadic[i][3])
            
            self.peakresult=minimize(self.peak2min, self.peakparameter, args=(x,y,yerr))
            print(fit_report(self.peakresult))

            peakfitres=[self.peakresult.params[self.peakparaname[i]].value for i in range(peaknumber*3)]
            bgfitres=[self.peakresult.params[self.peakbgparaname[i]].value for i in range(bgorder+1)]
            if peaktype=='Gaussian':
                self.peakfitdatay=sum(self.gaufun(x0,peakfitres[3*i:3*i+3]) for i in range(peaknumber))+self.polyfun(x0,bgfitres)
            else:
                self.peakfitdatay=sum(self.lorfun(x0,peakfitres[3*i:3*i+3]) for i in range(peaknumber))+self.polyfun(x0,bgfitres)
            self.peakbgfitdata=[[x0[i],self.polyfun(x0[i],bgfitres)] for i in range(len(x0))]
            self.peakfitdata=[[x0[i],self.peakfitdatay[i]] for i in range(len(x0))]
        if self.mcafitstatus==0 and self.mcafitallstatus==0:
            self.fitplotstatus=1
            self.updatePlotPlot()
#            self.ui.PlotMplWidget.canvas.ax.plot(x0,self.peakfitdatay,'r-')
#            self.ui.PlotMplWidget.canvas.draw()
        elif self.mcafitstatus!=0 and self.mcafitallstatus==0:
            self.mcafitplotstatus=1
            self.updateMcaPlotData()
        else:
            self.ui.mcaPlotMplWidget.canvas.ax.clear()
            errorbars(self.ui.mcaPlotMplWidget.canvas.ax,data[:,0],data[:,1],data[:,2],fmt='o-',label=self.mcaLabelOne)
            self.ui.mcaPlotMplWidget.canvas.ax.plot(x0,self.peakfitdatay,'r-')
            fit=np.array(self.peakfitdata)
            xran=np.abs(fit[:,0][-1]-fit[:,0][0])
            yran=np.max(fit[:,1])-np.min(fit[:,1])
            self.ui.mcaPlotMplWidget.canvas.ax.set_xlim(fit[:,0][0]-0.25*xran,fit[:,0][-1]+0.25*xran)
            self.ui.mcaPlotMplWidget.canvas.ax.set_ylim(np.min(fit[:,1])-0.2*yran,np.max(fit[:,1])+0.2*yran)
            self.ui.mcaPlotMplWidget.canvas.ax.set_xlabel('Energy')
            self.ui.mcaPlotMplWidget.canvas.ax.set_ylabel('Intensity')
            self.ui.mcaPlotMplWidget.canvas.ax.set_title('Fluorescence Spectrum')
            self.ui.mcaPlotMplWidget.canvas.ax.legend(loc=2,frameon=False,scatterpoints=0,numpoints=1)
            self.ui.mcaPlotMplWidget.canvas.draw()
            self.ui.mcaPlotMplWidget.canvas.flush_events()
            time.sleep(0.25)
        #self.fitpeakpara=[[pfit[3*i],pfit[3*i+1],abs(pfit[3*i+2])] for i in range(peaknumber)]
        #self.fitbgpara=[pfit[3*peaknumber+i] for i in range(bgorder+1)]
        if self.mcafitstatus!=0 or self.mcafitallstatus!=0:   # for fluorescence fitting 
            self.fitpeakpara=[[pfit[3*i],pfit[3*i+1],abs(pfit[3*i+2])] for i in range(peaknumber)]
            self.fitbgpara=[pfit[3*peaknumber+i] for i in range(bgorder+1)]
            for i in range(peaknumber): # set values
                for j in range(3):
                    self.uipeakfit.peakTW.setItem(i,j,QTableWidgetItem(str(float('%.4g' % self.fitpeakpara[i][j]))))
            for i in range(bgorder+1): 
                    self.uipeakfit.bgTW.setItem(i,0,QTableWidgetItem(str(float('%.4g' % self.fitbgpara[i]))))
            self.uipeakfit.chiLineEdit.setText(str(float('%.3f' % self.chisquare)))
            return True
        else:    # for regular fitting
            for i in range(peaknumber): # set values
                for j in range(3):
                    self.uipeakfit.peakTW.setItem(i,j,QTableWidgetItem(str(float('%.4g' % peakfitres[3*i+j]))))
            for i in range(bgorder+1): 
                    self.uipeakfit.bgTW.setItem(i,0,QTableWidgetItem(str(float('%.4g' % bgfitres[i]))))
            self.uipeakfit.chiLineEdit.setText(str(float('%.3f' % self.peakresult.redchi)))
    
    def gaufun(self,x,p):
        return abs(p[1])*np.exp(-(x-p[0])**2/2/p[2]**2)
        
    def lorfun(self,x,p):
        return abs(p[1])/(1+(x-p[0])**2/p[2]**2)

    def polyfun(self,x,p):
        if self.uipeakfit.invCheckBox.checkState()!=0:
            return sum([p[i]/x**i for i in range(len(p))])
        else:
            return sum([p[i]*x**i for i in range(len(p))])
        
    def peak2min(self, params, x, y, yerr):
        peakrow=self.uipeakfit.numberOfPeakSpinBox.value()
        peaktype=str(self.uipeakfit.peakTypeComboBox.currentText())
        bgrow=self.uipeakfit.bgSpinBox.value()
        peakpara=[params[self.peakparaname[i]].value for i in range(peakrow*3)]
        bgpara=[params[self.peakbgparaname[i]].value for i in range(bgrow+1)]
       # print peakpara, bgpara
        sum=self.polyfun(x,bgpara)        
        for i in range(peakrow):
            if peaktype=='Gaussian':
                sum=sum+self.gaufun(x,peakpara[3*i:3*i+3])
            else:
                sum=sum+self.lorfun(x,peakpara[3*i:3*i+3])
        return (y-sum)/yerr
        
    def peakres(self,p,x,y,yerr,flag): #define gauss and lorent  
        sum=self.polyfun(x,p[3*flag[1]:])        
        if flag[0]==0:
            for i in range(flag[1]):
                sum=sum+self.gaufun(x,p[3*i:3*i+3])
        else:
            for i in range(flag[1]):
                sum=sum+self.lorfun(x,p[3*i:3*i+3])
        return (y-sum)/yerr
    
    def savePeakFit(self): # save fit data
        if not hasattr(self,'peakfitdata'):
            self.messageBox('There is no fit to save yet; press "Fit" first.')
            return
        self.saveFileName=str(QFileDialog.getSaveFileName(caption='Save Fit Data',directory=self.directory)[0])
        if self.saveFileName=='':
            return
        fitfile=self.saveFileName+'_fit.txt'
       # print self.peakfitdata
        np.savetxt(fitfile,self.peakfitdata,fmt='%.4e\t%.4e')

    def savePeakPara(self): # save fit parameters
        if not hasattr(self,'peakresult'):
            # MCA fits use a different fitter that keeps no parameter report
            self.messageBox('Fit parameters can be saved after fitting a file in the "Plot" tab. For fluorescence fits use "Accept" and export the intensities.')
            return
        if len(self.selectedplotfiles_rows)==0:
            self.messageBox('Please select the fitted file in the "Plot" tab first.')
            return
        self.saveFileName=str(QFileDialog.getSaveFileName(caption='Save Fit Paremeters',directory=self.directory)[0])
        if self.saveFileName=='':
            return
        fid=open(self.saveFileName+'_par.txt','w')
        fid.write('Data File:\t'+os.path.basename(str(self.plotfiles[self.selectedplotfiles_rows[0]]))+'\n')
        fid.write('Peak Type:\t'+str(self.uipeakfit.peakTypeComboBox.currentText())+'\n')
        fid.write('# of Peaks:\t'+str(int(len(self.peakparaname)/3))+'\n')
        fid.write('BG Order:\t'+str(len(self.peakbgparaname)-1)+'\n')       
        fid.write('Chi_Square:\t'+str(float('%.4f' % self.peakresult.redchi))+'\n')
        fid.write('*********************\n')
        fid.write('\t\tValue\t\tVary\tStderr\t\tMin\tMax\n')
        for i in range(int(len(self.peakparaname)/3)):
            fid.write('Peak #'+str(i+1)+' pos:\t'+format(self.peakresult.params[self.peakparaname[i*3]].value, '.3e')+'\t'+str(self.peakparadic[i*3][1])+'\t'+format(self.peakresult.params[self.peakparaname[i*3]].stderr, '.3e')+'\t'+str(self.peakparadic[i*3][2])+'\t'+str(self.peakparadic[i*3][3])+'\n')
            fid.write('Peak #'+str(i+1)+' int:\t'+format(self.peakresult.params[self.peakparaname[i*3+1]].value, '.3e')+'\t'+str(self.peakparadic[i*3+1][1])+'\t'+format(self.peakresult.params[self.peakparaname[i*3+1]].stderr, '.3e')+'\t'+str(self.peakparadic[i*3+1][2])+'\t'+str(self.peakparadic[i*3+1][3])+'\n')
            fid.write('Peak #'+str(i+1)+' wid:\t'+format(self.peakresult.params[self.peakparaname[i*3+2]].value, '.3e')+'\t'+str(self.peakparadic[i*3+2][1])+'\t'+format(self.peakresult.params[self.peakparaname[i*3+2]].stderr, '.3e')+'\t'+str(self.peakparadic[i*3+2][2])+'\t'+str(self.peakparadic[i*3+2][3])+'\n')
        for i in range(len(self.fitbgpara)):
            fid.write('Background C'+str(i)+':\t'+format(self.peakresult.params[self.peakbgparaname[i]].value, '.3e')+'\t'+str(self.peakbgparadic[i][1])+'\t'+format(self.peakresult.params[self.peakbgparaname[i]].stderr, '.3e')+'\t'+str(self.peakbgparadic[i][2])+'\t'+str(self.peakbgparadic[i][3])+'\n')
        fid.close()
        
########################  for 2d plot######################

    def update2dPlotFile(self): #update 2dplot files in the listwidget
        self.ui.twodPlotFileListWidget.clear()
        for i in range(len(self.twodplotfiles)):
            try:  #for pc
                self.ui.twodPlotFileListWidget.addItem('#'+str(i+1)+self.halftab+str(self.twodplotfiles[i].split('\\')[-2])+'\\'+str(self.twodplotfiles[i].split('\\')[-1]))
            except: #for mac and linux
                self.ui.twodPlotFileListWidget.addItem('#'+str(i+1)+self.halftab+str(self.twodplotfiles[i].split('/')[-2])+'/'+str(self.twodplotfiles[i].split('/')[-1]))

    def add2dPlotFile(self): #add plot files into the listwidget and deselect all ref files in the listwidget
        f=QFileDialog.getOpenFileNames(caption='Select Multiple Files to import', directory=self.directory, filter='Files (*.*)')[0]
        self.twodplotfiles=self.twodplotfiles+list(map(str, f))
        self.update2dPlotFile()
        
    def updateSelected2dPlotFile(self): #update the selected data files in the listwidget
        selected2dplotfiles=self.ui.twodPlotFileListWidget.selectedItems()
        self.selected2dplotfiles_rows=[]
        for item in selected2dplotfiles:
            self.selected2dplotfiles_rows.append(self.ui.twodPlotFileListWidget.row(item))
        self.selected2dplotfiles_rows.sort()
        if len(self.selected2dplotfiles_rows)!=0:
            self.update2dPlotData()
        
    def remove2dPlotFile(self): #remove plot files in the listwidget and deselect all ref files in the listwidget
        items=self.ui.twodPlotFileListWidget.selectedItems()
        items.reverse()
        for item in items:
            self.twodplotfiles.pop(self.ui.twodPlotFileListWidget.row(item))
        self.ui.twodPlotFileListWidget.clear()
        self.update2dPlotFile()        
     
    def update2dPlotData(self):
        if len(self.selected2dplotfiles_rows)==0:   # no 2d file selected: nothing to redraw
            return
        data=np.loadtxt(str(self.twodplotfiles[self.selected2dplotfiles_rows[0]]), comments='#')
        x=np.unique(data[:,0])
        y=np.unique(data[:,1])
        if len(x)*len(y)!=len(data) or len(x)==1 or len(y)==1:
            self.messageBox('Warning:: The selected data file is not in 2d data format!')
        else:
            self.plot2dindex=0
            self.data2dint=np.reshape(data[:,2],(len(y),len(x)))
            self.extent=[x[0],x[-1],y[0],y[-1]]
            self.Zdata=self.data2dint
            self.data2dx, self.data2dy=np.meshgrid(x,y)
            self.imageMax=np.max(self.data2dint)
            self.imageMin=np.min(self.data2dint[np.where(self.data2dint>0)])
            self.ui.twodMaxLineEdit.setText(str(self.imageMax)) #set the vmax/vmin in the lineedit and slider 
            self.ui.twodMinLineEdit.setText(str(self.imageMin))
            self.ui.twodMaxHorizontalSlider.setValue(int(float(self.ui.twodMaxLineEdit.text())*100/(self.imageMax-self.imageMin)))
            self.ui.twodMinHorizontalSlider.setValue(int(float(self.ui.twodMinLineEdit.text())*100/(self.imageMax-self.imageMin)))
            self.update2dPlotPlot()
            
    def update2dMaxSlider(self):
        self.ui.twodMaxLineEdit.setText(str(self.ui.twodMaxHorizontalSlider.value()*(self.imageMax-self.imageMin)/100.0))
        self.ui.twodMinHorizontalSlider.setMaximum(int(float(self.ui.twodMaxLineEdit.text())*100.0/(self.imageMax-self.imageMin)))
       # print 'I ma here'
        self.update2dPlotPlot()
        
    def update2dMinSlider(self):
        self.ui.twodMinLineEdit.setText(str(self.ui.twodMinHorizontalSlider.value()*(self.imageMax-self.imageMin)/100.0))
        self.update2dPlotPlot()
        
    def update2dIntPolData(self):
        if len(self.selected2dplotfiles_rows)==0:
            self.messageBox('Please add and select a 2d data file first!')
        else:
            self.plot2dindex=1            
            pointden=self.ui.twodDenFacSpinBox.value()
            fint=interp1d(self.data2dx[0], self.data2dint, kind='linear')
            newdata2dx=np.linspace(self.data2dx[0][0],self.data2dx[0][-1],len(self.data2dx[0])*pointden)
            self.intpoldata2dint=fint(newdata2dx)
            self.Zdata = self.intpoldata2dint
           # print np.min(self.intpoldata2dint), np.min(self.data2dint)
            self.update2dPlotPlot()
    
    def update2dPlotPlot(self):
        if self.plot2dindex is None:   # nothing plotted yet: display options do nothing
            return
        self.ui.twodPlotMplWidget.canvas.fig.clf()
        cmap=str(self.ui.twodCMapComboBox.currentText())
        vmax=float(self.ui.twodMaxLineEdit.text())
        vmin=float(self.ui.twodMinLineEdit.text())
        labelsize=self.ui.twodLabelSizeSpinBox.value()
        ticksize=self.ui.twodTickSizeSpinBox.value()
        self.plot2dax=self.ui.twodPlotMplWidget.canvas.fig.add_subplot(1,1,1)
        self.plot2dax.set_xlabel(r'$Q_{xy}$'+' '+r'$[\AA^{-1}]$', fontsize=labelsize)
        self.plot2dax.set_ylabel(r'$Q_{z}$'+' '+r'$[\AA^{-1}]$', fontsize=labelsize)
        if self.plot2dindex==0:
            if self.ui.twodLogIntCheckBox.checkState()!=0:
                self.plot2d_p=mesh(self.plot2dax,self.data2dx, self.data2dy, np.log10(self.data2dint),cmap=cmap,vmin=np.log10(vmin), vmax=np.log10(vmax))
            else:
                self.plot2d_p=mesh(self.plot2dax,self.data2dx, self.data2dy, self.data2dint, cmap=cmap, vmin=vmin, vmax=vmax)
            self.plot2dax.set_xlim((np.min(self.data2dx),np.max(self.data2dx)))
            self.plot2dax.set_ylim((np.min(self.data2dy),np.max(self.data2dy)))
        else:
            interpol=str(self.ui.twodIntPolComboBox.currentText())
            if self.ui.twodLogIntCheckBox.checkState()!=0:
                self.plot2d_p=self.plot2dax.imshow(np.log10(self.intpoldata2dint),interpolation=interpol,extent=self.extent,cmap=cmap,vmin=np.log10(vmin), vmax=np.log10(vmax), aspect='auto', origin='lower')
            else:
                self.plot2d_p=self.plot2dax.imshow(self.intpoldata2dint,interpolation=interpol,extent=self.extent,cmap=cmap,vmin=vmin, vmax=vmax, aspect='auto', origin='lower')
        if self.ui.twodColBarCheckBox.checkState()!=0:
            cb=self.ui.twodPlotMplWidget.canvas.fig.colorbar(self.plot2d_p)
            cb.ax.tick_params(labelsize=ticksize)
        self.plot2dax.tick_params(labelsize=ticksize)
        self.plot2dax.format_coord=self.format_pil_coord
        self.ui.twodPlotMplWidget.canvas.draw()
    
    
    def questionDialog(self, question='Do you want to continue?'):
        reply=QMessageBox.question(self, 'Message',
            question, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        return reply
        
        