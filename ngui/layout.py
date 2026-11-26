"""The new layout as data (docs/gui/prototype.md).

Every control of today's window (each id of docs/gui/inventory/*.yaml) has
exactly one home here, or is in RETIRED with a reason;
tests/test_ngui.py checks it. Moving a control is editing one line.

Vocabulary
----------
C(id, label, kind, items, note)
    a control of today's window, placed here. ``label`` and ``kind`` are
    what the new layout shows (None: the inventory's); ``note`` says what
    changed and goes into the tooltip.
NEW(name, label, kind, note)
    a control the design adds (no inventory id): a requested feature (F..)
    or the visible half of a change (e.g. the GID combo split into buttons).
ROW(...)
    several controls on one line.
CAPTION(text)
    a small heading inside a group.
G(title, role, items, replaces, fold, note)
    a titled group ("card"). ``role`` is the template slot: Input, Reduce,
    Display, or the tab's own kind (Fit, Tools, ROI, Patch, ...).
    ``replaces`` lists containers of today (tabs, dialogs, menus) whose
    function this group takes over; they count as placed.
PLOT(id or None, caption, sketch, ...)
    a plot placeholder (a painted sketch, no matplotlib). ``residuals``: a
    residuals-panel toggle above it (F74); ``provenance``: the strip under it.
SPECIAL(kind, ...)
    the elements drawn by window.py: the frame viewer, the line-cut panel,
    the burn verdict card, the joins list, tabbed small panels.

Template order in every tab: Input, Reduce, Display, with the tab's own
groups between them (Fit, Tools, ROI, Patch, Result, Compare, ...). There is
no Output group (D61, owner 2026-11-23): results are saved into the workbook
automatically, and each result plot has one "Save…" button beside its
provenance strip (today's Save button: a version with a note); exporting is
File > Export… only (EXPORT below).
"""

# ---------------------------------------------------------------- vocabulary


def C(cid, label=None, kind=None, items=None, note=''):
    return {'id': cid, 'label': label, 'kind': kind, 'items': items, 'note': note}


def NEW(name, label, kind, note='', items=None):
    return {'new': name, 'label': label, 'kind': kind, 'items': items, 'note': note}


def ROW(*items):
    return {'row': list(items)}


def CAPTION(text):
    return {'caption': text}


def G(title, role, items, replaces=(), fold=False, note=''):
    return {'title': title, 'role': role, 'items': list(items), 'replaces': list(replaces), 'fold': fold,
            'note': note}


def PLOT(cid, caption, sketch, residuals=False, provenance=None, note='', name=None, stretch=1, note_button=None):
    return {'plot': cid, 'caption': caption, 'sketch': sketch, 'residuals': residuals, 'provenance': provenance,
            'note': note, 'name': name, 'stretch': stretch, 'note_button': note_button}


def SAVE(cid):
    """Today's workbook Save button: the one "Save…" button of a result area (owner 2026-11-23)."""
    return C(cid, 'Save…', kind='button', note=SAVE_TIP)


SAVE_TIP = ('Saves this result as a version, with your note. Results are also saved automatically (D56); if '
            'this result is the one just saved automatically, the note goes on that version instead of a copy. '
            'Change the parameters and Save… again for a new version')


def SPECIAL(kind, **kw):
    kw['special'] = kind
    return kw


# A provenance strip (principle 4). The values are an example of the format.
PROV_REF = 'S# 6–9 · joint fit · budget errors · / Monc · saved R0007 v2'

WORKFLOW_COLOURS = {          # chips in the tab titles; always beside text (never colour alone)
    'scans': '#7a869a',
    'frames': '#3a8fb7',
    'burn': '#e07b39',
    'reflectivity': '#2f6fdf',
    'gid': '#3c9d5d',
    'fluorescence': '#8e5cc4',
    'files': '#9a9a9a',
}

# The primary action of a group, drawn in the accent colour (principle 12).
PRIMARY = {'pilRefPatchPushButton', 'burnAnalysePushButton', 'gidPatchPushButton', 'mcaSumAllPushButton',
           'cutFitPushButton', 'pdgioxs.runPushButton', 'scans_fit', 'export_write'}

# ---------------------------------------------------------------- selection dock (left, full height)

DOCK = [
    G('SPEC file', 'Input', [
        C('specFileLabel', 'SPEC file: <name>'),
        ROW(C('speUpSpeFilePushButton', 'Update'),
            C('liveCheckBox', 'Live', note='Also shown in the state bar')),
    ]),
    G('Series', 'Input', [
        C('seriesComboBox', 'Series', items=['Series: choose to select its scans', 'reflectivity: S# 6–9',
                                             'GID: S# 22–31', 'burn: S# 40']),
        C('seriesWholeCheckBox', 'Whole series and all its frames',
          note='One action selects the series and every frame (prototype.md, Reflectivity > Input)'),
    ]),
    G('Scans', 'Input', [
        C('scansLineEdit', 'Scans', note='Typed as ranges, e.g. 6 – 9, 12'),
        C('scanListWidget', ''),
    ]),
    G('Frames', 'Input', [
        C('imagesLabel', 'Detector: Pilatus 100K'),
        C('gixSumCheckBox', 'Show', kind='combo', items=['Movie', 'Sampled (4)', 'First n', 'Sum'],
          note='"Sum All" becomes the Sum mode of one mode selector; Movie is the default for more than one '
               'frame, never more than 6 tiles (F69)'),
        C('imageSelectAllCheckBox', 'All frames'),
        C('imageListWidget', ''),
    ]),
    G('Background frames', 'Input', [
        ROW(C('backgroundPushButton', 'Use selected', note='Adds the selected frames as background frames'),
            C('removePushButton', 'Remove')),
        C('bgSelectAllCheckBox', 'All'),
        C('backgroundListWidget', ''),
    ], fold=True, note='Folds away when empty; the factor and Ignore −ve moved to Frames > Reduce'),
]

# ---------------------------------------------------------------- tabs

SCANS = {
    'key': 'scans', 'title': 'Scans', 'chip': 'align',
    'was': 'SpecPlot tab, Calculations menu',
    'replaces': ['specPlotTab'],
    'left': [
        G('Input', 'Input', [
            CAPTION('The scans selected in the panel, overlaid'),
            C('scanInfoDialog.impInfoTextBrowser', 'Scan summary', kind='list',
              note='The important lines of the scan header, shown inline'),
            C('scanInfoDialog.scanInfoTextBrowser', 'Full header…', kind='button',
              note='Opens the whole scan header'),
        ], replaces=['scanInfoDialog']),
        G('Reduce', 'Reduce', [
            ROW(C('spNCheckBox', 'Normalise by'), C('spNComboBox', '', items=['Monc', 'Monb', 'None'])),
            ROW(C('spGainCheckBox'), C('spPhotonCheckBox')),
        ]),
        G('Display', 'Display', [
            C('spXComboBox', 'X', items=['sh', 'Det_Th', 'Qz']),
            C('spYComboBox', 'Y', items=['Monc', 'Pilatus ROI', 'Monb']),
            C('spY2ComboBox', 'Y2 (right axis)', items=['None']),
            ROW(C('spLogXCheckBox', 'Log x'), C('spLogYCheckBox', 'Log y'), C('spGridCheckBox')),
            ROW(C('spLegendCheckBox'), C('spLegendLocComboBox', '')),
            C('spPointLabelsCheckBox', 'Point numbers'),
        ]),
        G('Fit', 'Fit', [
            NEW('scans_fitShape', 'Shape', 'combo', 'The scan\'s shape: peak, edge or plateau (F78)',
                items=['Peak', 'Edge', 'Plateau']),
            ROW(NEW('scans_fit', 'Fit', 'button', 'Fits the chosen shape to every scan shown'),
                NEW('scans_heightCheck', 'Sample height check', 'button',
                    'FWHM against 65 µm, flatness as a super-Gaussian exponent, earlier sh scans of the sample '
                    '(F78; owner 2026-11-23)')),
            NEW('scans_halfCut', 'Half-cut beam size: —', 'label', 'From a half-cut scan (F43)'),
        ], note='New: the fit of a motor scan and the sample height check'),
        G('Tools', 'Tools', [
            ROW(C('g_l2Dialog.g_l2centercheckBox', 'centres'),
                C('g_l2Dialog.g_l2CalPushButton', 'g_l2', note='Calculation of the Calculations menu, inline')),
            ROW(C('g_l3Dialog.g_l3centercheckBox', 'centres'),
                C('g_l3Dialog.g_l3CalPushButton', 'g_l3', note='Calculation of the Calculations menu, inline')),
            C('actionAbs_ratio', 'Absorber ratio', kind='button',
              note='Was a menu action; its result can be offered to the absorber field (Reflectivity > Patch)'),
        ], replaces=['menuCalculations', 'actionG_l2', 'actionG_l3', 'g_l2Dialog', 'g_l3Dialog', 'absratioDialog'],
           note='The Calculations menu, moved next to the scans it reads'),
    ],
    'right': [
        [PLOT('specPlotMplWidget', 'Counts vs motor (several scans overlaid)', 'peak', residuals=True,
              provenance='S# 12–14 · / Monc · fit: Gaussian · saved S0011 v1',
              note_button=SAVE('specSaveWorkbookPushButton'))],
    ],
}

FRAMES = {
    'key': 'frames', 'title': 'Frames', 'chip': 'img',
    'was': 'Pilatus tab (image area), Line/Area Cuts tab, GISAXS and GIOXS',
    'replaces': ['pilatusTab', 'cutAreaTab'],
    'left': [
        G('Reduce', 'Reduce', [
            ROW(C('pilBPCiteSpinBox', 'Bad pixels: passes'), C('pilBPCfacSpinBox', '×')),
            C('pilSpecCheckBox', 'Direct beam and distance from SPEC',
              note='Today the box\'s text is the label of the next field'),
            C('pilDBPosLineEdit', 'Direct beam x, y (px)'),
            C('pilSDDistLineEdit', 'Sample–detector (mm)'),
            C('pilPinholeCheckBox', 'Pinhole geometry', note='Moved from the display options: it is geometry'),
            C('bgFacLineEdit', 'Background frames ×'),
            C('bgIgnoreNegCheckBox', 'Ignore negative pixels after subtraction'),
        ]),
        G('Display', 'Display', [
            C('pilAxesComboBox', 'Axes'),
            C('pilLogIntCheckBox', 'Scale', kind='combo', items=['log', 'linear', 'asinh'],
              note='Log Int becomes a scale choice with asinh (C3)'),
            C('pilCMapComboBox', 'Colour map', items=['viridis', 'magma', 'gray', 'jet']),
            C('pilAspectComboBox', 'Aspect'),
            ROW(C('pilMinHorizontalSlider', 'Low %'), C('pilMinLineEdit', '')),
            ROW(C('pilMaxHorizontalSlider', 'High %'), C('pilMaxLineEdit', '')),
            ROW(C('pilHomePushButton', 'Home', note='The remembered zoom (F88)'),
                C('pilFitAllPushButton', 'Fit all', note='The whole frame (F88)'),
                C('pilAutoScalePushButton', 'Auto scale', note='Automatic limits again (F88)')),
            CAPTION('Zoom, map, scale and limits stay put while frames play (F70)'),
        ]),
        G('Views', 'Views', [
            CAPTION('GIOXS: background-subtracted profiles'),
            ROW(C('pdgioxs.frameLineEdit', 'Average frames'), C('pdgioxs.pointLineEdit', 'points')),
            C('pdgioxs.runPushButton', 'Run GIOXS'),
        ], replaces=['pdgioxs'], note='The GIOXS dialog, inline; the views are switched above the image'),
        G('Peak fit (cuts)', 'Fit', [
            C('cutFitShapeComboBox', 'Shape', items=['gaussian', 'lorentzian', 'pseudo-voigt'],
              note='The same options serve Fluorescence > Fit lines'),
            C('cutFitBackgroundComboBox', 'Background', items=['none', 'constant', 'linear', 'quadratic', 'cubic']),
            ROW(C('cutFitNumberSpinBox', 'Peaks (0 = auto)'), C('cutFitMaxSpinBox', 'at most')),
            C('cutFitProminenceSpinBox', 'Sensitivity (σ)'),
            C('cutFitWindowSpinBox', 'Window half-width (0 = auto)'),
            C('cutFitFwhmSpinBox', 'Fixed FWHM (0 = fitted)'),
            C('cutFitRangeLineEdit', 'x range (a – b)'),
            ROW(C('cutFitCentresLineEdit', 'Centres'), C('cutFitFixCheckBox', 'fixed')),
            ROW(C('mcaFitDetectorWidthCheckBox', 'width from detector'), C('mcaFitNoiseSpinBox', 'noise (keV)')),
            C('mcaFitEscapeCheckBox', 'strip Si escapes', note='Fluorescence only: F90 P2, P3 (options, not defaults)'),
            C('cutFitPushButton', 'Fit peaks'),
            C('cutFitResultLabel', 'χ²/dof —, 2 peaks'),
        ], replaces=['cutFitDialog', 'cutFitOptionsPushButton'], fold=True,
           note='The Peak fit options dialog, inline and folded'),
    ],
    'right': [
        [SPECIAL('frame_viewer',
                 views=[('Frames', None), ('GISAXS', C('gisaxsComboBox', 'GISAXS', kind='button',
                                                       note='The GISAXS combo becomes a view switch; "Export GISAXS" '
                                                            'is File > Export…')),
                        ('GIOXS', C('pilGioxsPushButton', 'GIOXS', kind='button',
                                    note='Switches to the GIOXS view; its settings are in Views'))],
                 image=PLOT('pilMplWidget', 'Frame (log scale, zoom kept)', 'frame',
                            note='Zoom, map and scale stay put while frames play (F70). Reflectivity frames open on '
                                 'log scale, zoomed to the ROI and both background zones with a margin of diffuse '
                                 'scattering, much smaller than the full frame (owner 2026-11-23)'),
                 gioxs=PLOT('pdgioxs.plotWidget', 'GIOXS profiles', 'curves'),
                 gisaxs=PLOT(None, 'GISAXS: Qz vs Qy', 'gisaxs', name='frames_gisaxsPlot'),
                 movie=C('pilMoviePushButton', 'Movie', note='Plays the selection as a movie, also 2 frames (F69)'),
                 movie_bar={'view': C('pilViewComboBox', '', items=['Movie', 'Tiles: 4', 'Tiles: 6']),
                            'back': C('pilMovieBackPushButton', '◀'),
                            'play': C('pilMoviePlayPushButton', '▶', note='Play/pause (space; F69, Q7)'),
                            'next': C('pilMovieForwardPushButton', '▶|'),
                            'slider': C('pilMovieSlider', ''),
                            'counter': C('pilMovieCounterLabel', '14 / 41'),
                            'speed': C('pilMovieSpeedComboBox', '', items=['2 fps', '0.5 fps', '1 fps', '5 fps',
                                                                         '10 fps']),
                            'loop': C('pilMovieLoopCheckBox', 'loop'),
                            'meta': C('pilMovieInfoLabel', 'S# 11 · pt 13 · 2θ 18.40° · t 412 s · abs 2 · '
                                                           'Monc 1.2e+05')},
                 split=NEW('frames_split', 'Split', 'toggle', 'Shows Raw frames and Line cuts together, side by '
                           'side or stacked (owner 2026-11-23)'),
                 # the "Line cuts" sub-tab; its band is drawn on the raw image
                 cuts=SPECIAL('cut_panel',
                 toolbar=[C('pilCutDirComboBox', 'Cut'), C('cutAxisComboBox', 'x: as image'),
                          C('pilIntRangeLineEdit', 'Range (a – b)'),
                          C('pilLineAreaPushButton', 'Cut', note='Draws the cut; the band can also be dragged on '
                                                                 'the image (F68)')],
                 plot=PLOT('cutPlotMplWidget', 'Line cut', 'cut'),
                 options=[C('cutLogXCheckBox', 'Log x'), C('cutLogYCheckBox', 'Log y'), C('cutGridCheckBox'),
                          C('cutErrorbarCheckBox', 'Error bars'), C('cutLegendCheckBox'),
                          C('cutLegendLocComboBox', ''),
                          C('cutOffsetCheckBox', 'Offset ×'), C('cutOffsetLineEdit', ''),
                          C('cutClearGraphPushButton', 'Clear')],
                 provenance='S# 22 · Q H cut, Qz 0.05–0.10 · / Monc · 2 peaks · saved C0005 v1',
                 note_button=SAVE('cutSaveWorkbookPushButton')),
                 stretch=1)],
    ],
}

BURN = {
    'key': 'burn', 'title': 'Burn', 'chip': 'burn',
    'was': 'Burn test dialog (Pilatus tab button)',
    'replaces': ['pdburn', 'burnTabWidget', 'pilBurnPushButton'],
    'left': [
        G('Input', 'Input', [
            CAPTION('Burn scans from the panel, several at once'),
            NEW('burn_showRoi', 'Show the ROI on the frames', 'checkbox', 'Q-BURN-5'),
            C('pdburn.rangeLineEdit', 'GID peak Qxy (a – b)', note='Single peak only'),
            ROW(C('burnAutoPeakCheckBox', 'Find peak'), C('burnPositionLimitCheckBox', 'Keep in range')),
            ROW(C('burnRowsAutoCheckBox', 'Rows from frame'), C('burnRowsLineEdit', 'Rows (first:last)')),
        ]),
        G('Reduce', 'Reduce', [
            CAPTION('Models compared'),
            ROW(C('burnConstantCheckBox'), C('burnLinearCheckBox')),
            ROW(C('burnExponentialCheckBox'), C('burnDoubleExponentialCheckBox')),
            C('burnTimeComboBox', 'Time axis', items=['clock', 'exposure']),
            ROW(C('burnAxisComboBox', 'Axis', items=['time', 'dose']),
                C('burnDoseUnitComboBox', 'Dose in', items=['photons', 'Monc counts'])),
            ROW(C('burnBeamWidthLineEdit', 'Beam width (mm)'), C('burnBeamHeightLineEdit', 'height (mm)')),
            C('burnFastModeCheckBox', 'Fast mode (shutter open)'),
            C('burnScanComboBox', 'Burn on show', note='Several burns at once (F98, built 2026-11-25)'),
            C('burnEstimatorComboBox', 'Estimator', items=['template', 'moments', 'fit']),
            C('burnErrorsComboBox', 'Errors', items=['auto', 'scatter', 'counting']),
            C('burnThresholdSpinBox', 'Change that matters (%)'),
            C('burnAnalysePushButton', 'Analyse'),
        ]),
        G('Dose or time', 'Dose or time', [
            CAPTION('Two or more burns at different absorbers (F76)'),
            ROW(C('burnVerdictQuantityComboBox', 'Compare'), C('burnStripSpinBox', 'Strip scatter ρ (%)')),
            C('burnVerdictLabel', 'Dose: β = 0.97 [0.88, 1.06]', kind='label'),
        ]),
        G('Display', 'Display', [
            NEW('burn_trendPanels', 'Panels: intensity, position, width', 'checkbox', 'One panel per trend'),
            NEW('burn_envPanels', 'Environment: barrier, tensiometer, O₂', 'checkbox', 'F75'),
        ]),
    ],
    'legacy': [
        G('Legacy burn plots', 'Legacy', [
            C('pdburn.refPushButton', 'REF plot'),
            C('pdburn.gidComboBox', 'GID: intensity, location or width'),
            C('pdburn.plotWidget', 'Legacy plot', kind='plot'),
        ]),
    ],
    'right': [
        [SPECIAL('verdict', label=C('burnResultLabel', '')), ],
        [PLOT('burnTrendPlotWidget', 'ROI intensity vs time, with the fitted models', 'trend', residuals=True,
              provenance='S# 40 · 41 frames · exposure time · scatter errors · saved B0003 v1', stretch=3,
              note_button=SAVE('burnSavePushButton'))],
        [PLOT('burnVerdictPlotWidget', 'Each burn against time and against the dose (F76, F98)', 'trend')],
        [PLOT(None, 'Barrier, surface pressure, oxygen vs time (F75)', 'env', name='burn_envPlot')],
    ],
}

REFLECTIVITY = {
    'key': 'reflectivity', 'title': 'Reflectivity', 'chip': 'ref',
    'was': 'Reflectivity tab, Ref Patch and its settings (Pilatus tab, Preferences)',
    'replaces': ['refTab', 'refpatch', 'refpatchsamescan', 'pilPeakCenDialog', 'pilBadPixDialog'],
    'left': [
        G('Input', 'Input', [
            CAPTION('The series in the panel: all its scans and frames'),
            C('pilMergeSameQzCheckBox', 'Group frames at the same Qz'),
        ]),
        G('ROI', 'ROI', [
            C('refSlitLineEdit', 'ROI size H, V (px)'),
            ROW(C('refBGOffLineEdit', 'Bkg offset (°)'), C('refBGDirComboBox', '')),
            ROW(C('refCenCheckBox', 'Centre H, V (px)'), C('refCenLineEdit', '')),
            C('pilLowQzCorCheckBox', 'Low-Qz slit correction'),
        ]),
        G('Patch', 'Patch', [
            C('prefPatchMethodComboBox', 'Method', items=['Joint fit', 'Legacy fit'],
              note='Was in Preferences; shown where it acts'),
            ROW(C('prefPatchAutoCheckBox', 'Foil ratio if fit error >'), C('prefPatchThresholdSpinBox', '')),
            ROW(C('AbsFacLineEdit', 'Absorber ratio'), C('absFacEnergyCheckBox', 'from E'),),
            CAPTION('Identical scans'),
            ROW(C('refpatchsamescan.mergePushButton', 'Sum', kind='radio',
                  note='Summed by counts and monitors (F81)'),
                C('refpatchsamescan.dropPushButton', 'Drop', kind='radio'),
                NEW('ref_samePatch', 'Patch', 'radio', 'Patched like any other pair')),
            C('refpatchsamescan.dropLineEdit', 'Drop scan #'),
            C('pilRefPatchPushButton', 'Patch'),
        ]),
        G('Result', 'Result', [
            ROW(C('refQcLineEdit', 'Qc (1/Å)'), C('refQcSubphaseToolButton', 'Subphase ▾')),
            ROW(C('refQoffLineEdit', 'Qoff (1/Å)'), C('refQoffProposePushButton', 'Propose')),
            ROW(C('refNormFacCheckBox', 'Divide by'), C('refNormLineEdit', '')),
        ]),
        G('Display', 'Display', [
            ROW(C('refRRFCheckBox', 'R / R_F'), C('refLogYCheckBox', 'Log R'), C('refQzSqrCheckBox', 'x = Qz²')),
            ROW(C('refLegendCheckBox'), C('refLegendLocComboBox', '')),
        ]),
        G('Compare', 'Compare', [
            NEW('ref_savedBy', 'Saved, by', 'combo', 'Saved reflectivities of the workbook (F80)',
                items=['series', 'time', 'sx']),
            NEW('ref_savedList', '', 'list', 'Saved reflectivities to overlay (F80)'),
            ROW(C('refAddFilePushButton', 'Add files'), C('refRemoveFilePushButton', 'Remove')),
            C('refRefFileListWidget', ''),
        ], fold=True),
    ],
    'legacy_label': 'Check frames…',
    'legacy': [
        G('Check frames, point by point (until question 13 is answered)', 'Legacy', [
            C('pilRefPushButton', 'List frames by Qz', note='Was the Pilatus tab\'s "Reflectivity" button'),
            C('refQzListWidget', ''),
            C('refSeaWinLineEdit', 'Search window (× slit)'),
            ROW(C('refAnalyzePushButton'), C('refAcceptPushButton'), C('refAnalyzeAllPushButton')),
            ROW(C('refQLineEdit', 'Qz'), C('refRLineEdit', 'R')),
            ROW(C('refRErrLineEdit', 'σR'), C('refPerRErrLineEdit', 'σR (%)')),
            C('refComLineEdit', 'Comment'),
        ]),
    ],
    'right': [
        [PLOT('refRefDataPlotwidget', 'R / R_F vs Qz', 'ref', residuals=True,
              provenance=C('refProvenanceLabel', PROV_REF, kind='label'), stretch=3,
              note_button=SAVE('refSaveWorkbookPushButton'))],
        [SPECIAL('tabs', name='ref_roiTabs', pages=[
            ('ROI close-up', [PLOT('refADDataPlotWidget', 'ROI movie (log)', 'roi',
                  note='Opens on log scale, zoomed to a box holding the ROI and both background zones with a margin of '
                       'diffuse scattering around them: a healthy zoom, not too close (owner 2026-11-23; F71)'),
                  C('refRoiLogCheckBox', 'Log'),
                  C('refRoiCuesLabel', 'off centre 30 % · clipped 2 %', kind='label',
                    note='The checks of the boxes (Q-IMG-7), the reasons in the tooltip')]),
            ('Checks', [NEW('ref_centreChecks', 'Beam centre off', 'list',
                            'Frames whose beam centre is more than 2 px off; in the main window since 2026-11-24 a '
                            'message and open squares on the curve (F95)'),
                        C('refBadPixListWidget', 'Bad pixels in the ROI', kind='list',
                          note='Per Qz, with crosses on the curve (F95; was a modal window during Ref Patch)')]),
         ]),
         SPECIAL('joins', title=C('refpatch.Label', 'Joins', kind='label'),
                 controls=[C('refpatch.knownRatioCheckBox', 'Known ratio'),
                           C('refpatch.knownRatioLabel', 'fit ±0.4 %, foils ±1.5 %'),
                           C('refpatch.dropLineEdit', 'Drop points'), C('refpatch.dropPushButton', 'Drop'),
                           C('refpatch.restoreAllPushButton', 'Restore all',
                             note='Clears the mask of these scans and starts again (F92, built 2026-11-25)'),
                           C('refpatch.backPushButton', '◂ Back',
                             note='Undoes the last drop or accepted join (F96, built in the main window 2026-11-24)'),
                           C('refpatch.nextPushButton', 'Next doubtful ▸',
                             note='Steps to the next doubtful join; all joins are listed together'),
                           C('refpatch.cancelPushButton', 'Cancel',
                             note='Stops the patch and says so; the result on show is unchanged (F96)')],
                 table=C('refpatch.joinTableWidget', 'Joins', kind='table',
                         note='Accepted joins and the one on show, kept with the result (F96, the main window\'s patch '
                              'window since 2026-11-24); here every join at once'),
                 pages=[('Join', PLOT('refpatch.plotWidget', 'Join close-up', 'join')),
                        ('Identical scans', PLOT('refpatchsamescan.plotWidget', 'Identical scans', 'join'))]),
         SPECIAL('tabs', name='ref_pointsTabs', title=C('reflectivityDataLabel', 'Points', kind='label'),
                 tabwidget=C('refDataTabWidget', kind='tab'),
                 pages=[('R', [C('refDataListWidget', '')]),
                        ('R normalised', [C('refNormRefListWidget', '')])],
                 footer=[C('refDelPushButton', 'Remove points')]),
         ],
    ],
}

GID = {
    'key': 'gid', 'title': 'GID', 'chip': 'gid',
    'was': 'GID combo (Pilatus tab), GID patching worksheet, form factor dialog',
    'replaces': ['gidWorksheetDialog', 'pdformfac'],
    'left': [
        G('Input', 'Input', [
            CAPTION('The GID series in the panel; background frames below it'),
            C('gidLevelsLabel', 'Levels: 3 (β 0–0.5°, 0.5–1°, 1–1.5°)'),
        ]),
        G('Map', 'Reduce', [
            C('gidColumnsSpinBox', 'Columns per frame', note='Was mirrored by the Pilatus tab\'s HSlits field'),
            ROW(C('gidRowMinSpinBox', 'Rows'), C('gidRowMaxSpinBox', '–')),
            ROW(C('gidQzDecimalsSpinBox', 'Decimals: Qz'), C('gidDthDecimalsSpinBox', '2θ')),
            C('gidMinFramesSpinBox', 'Min frames per level'),
        ]),
        G('Geometry', 'Reduce', [
            ROW(C('gidAreaCheckBox', 'Area'), C('gidPolCheckBox', 'Polarisation'), C('gidArmCheckBox', 'Arm')),
            C('gidHardSlitSpinBox', 'Hard slit (mm)'),
            C('gidPinholeCheckBox', 'Pinhole: angle per column'),
            ROW(C('gidPinholeDistSpinBox', 'S4–detector (mm)'), C('gidFitDistancePushButton', 'Fit')),
            C('gidFitLabel', 'fitted: —'),
            C('gidDistanceLabel', 'Sample–detector: 650 mm'),
            C('gidAbsorberLabel', 'Absorber: not applied'),
        ]),
        G('Response', 'Reduce', [
            C('gidResponseComboBox', 'Response', items=['fit', 'beam', 'physical', 'physical+fit', 'none']),
            C('gidBeamFwhmSpinBox', 'Beam FWHM (µm)'),
            ROW(C('gidBeamCentreSpinBox', 'Centre (mm)'), C('gidBeamCentreFitCheckBox', 'fit')),
            C('gidBeamHFwhmSpinBox', 'Horizontal FWHM (mm)'),
            C('gidFootprintComboBox', 'Footprint', items=['exact', 'IDL']),
            C('gidTransverseComboBox', '2θ range', items=['common', 'all']),
        ], fold=True),
        G('Joins', 'Reduce', [
            C('gidVJoinKindComboBox', 'Vertical join', items=['cubic', 'linear']),
            C('gidApplyJoinsCheckBox', 'Apply join factors'),
            C('gidLiveCheckBox', 'Re-patch on every change', note='Was "Update the map on every change"; not '
                                                                   'the same thing as the panel\'s Live'),
            ROW(C('gidDefaultsPushButton', 'Defaults'), C('gidPatchPushButton', 'Patch')),
        ]),
        G('Display', 'Display', [
            NEW('gid_cmap', 'Colour map', 'combo', 'The map\'s own colour settings (Q-IMG-15)',
                items=['viridis', 'magma', 'jet']),
            ROW(NEW('gid_scale', 'Scale', 'combo', '', items=['log', 'linear', 'asinh']),
                NEW('gid_limits', 'Limits', 'lineedit', 'Typed as a – b')),
        ]),
        G('Tools', 'Tools', [
            CAPTION('Form factor'),
            ROW(C('pdformfac.sphCheckBox', 'Sphere'), C('pdformfac.sphLineEdit', 'r (Å)')),
            ROW(C('pdformfac.ellCheckBox', 'Ellipsoid'), C('pdformfac.ellXYLineEdit', 'r_xy (Å)')),
            C('pdformfac.ellZLineEdit', 'r_z (Å)'),
            ROW(C('pdformfac.updatePushButton', 'Draw form factor'),
                NEW('gid_patchRelax', 'Patch relax', 'button', 'Was an item of the GID combo'),
                C('gidWorksheetPushButton', 'Worksheet…', kind='button')),
        ], fold=True),
    ],
    'right': [
        [PLOT(None, 'GID map: Qz vs Qxy (its own view)', 'map', name='gid_mapPlot',
              provenance='S# 22–31 · pinhole patch · 3 levels · joins applied · / Monc · saved G0002 v1', stretch=2,
              note_button=C('gidComboBox', 'Save…', kind='button',
                            note=SAVE_TIP + '. The GID combo (a menu of actions) becomes buttons: Patch (Joins), '
                                 'Patch relax and Form factor (Tools), Export GID (File > Export…), and its "Save to '
                                 'workbook" item, this Save… button')),
         SPECIAL('column', items=[PLOT(None, 'Qxy cut', 'cut', name='gid_qxyCut'),
                                  PLOT(None, 'Qz cut (Bragg rod)', 'rod', name='gid_qzCut')])],
        [C('gidJoinTable', 'Joins between levels and columns', kind='table')],
    ],
}

FLUORESCENCE = {
    'key': 'fluorescence', 'title': 'Fluorescence', 'chip': 'xfntr',
    'was': 'MCA tab, the element choice in Preferences, the Merge window',
    'replaces': ['mcaTab', 'mcaFitDialog', 'mcamerge'],
    'left': [
        G('Input', 'Input', [
            CAPTION('Spectra selected in the panel; detector elements'),
            ROW(*[C('prefMcaChannel%dCheckBox' % k, str(k)) for k in range(1, 8)]),
            ROW(C('prefMcaAllPushButton', 'All (EXAFS)'), C('prefMcaCentrePushButton', 'Centre (XFNTR)')),
        ], note='The element choice was in Preferences (D49)'),
        G('Reduce', 'Reduce', [
            ROW(C('mcaCalibCheckBox', 'E ='), C('mcaCalibConLineEdit', ''), C('mcaCalibLinLineEdit', '· ch +'),
                C('mcaCalibQuaLineEdit', '· ch²')),
            ROW(C('mcaNormComboBox', 'Normalise by'),),
            ROW(C('mcaGainCheckBox'), C('mcaPhotonCheckBox')),
            C('mcaRanLineEdit', 'Window (keV, a – b)'),
            ROW(C('mcaSumAllPushButton', 'Sum window'), C('mcaFitLinesPushButton', 'Fit lines')),
            C('mcaFitOptionsPushButton', 'Line fit options…', note='The same options as Frames > Peak fit'),
        ]),
        G('Display', 'Display', [
            C('mcaXAxisComboBox', 'Integral against', items=['Qz', 'Frame', 'Energy']),
            ROW(C('mcaLogXCheckBox', 'Log x'), C('mcaLogYCheckBox', 'Log y'), C('mcaGridCheckBox')),
            ROW(C('mcaLegendCheckBox'), C('mcaLegendLocComboBox', '')),
            ROW(C('mcaOffsetCheckBox', 'Offset ×'), C('mcaOffsetLineEdit', '')),
        ]),
        G('Merge', 'Merge', [
            C('mcamerge.resLineEdit', 'Qz resolution (1/Å)', note='Was asked in a Merge window'),
            ROW(C('mcaMergePushButton', 'Merge'), C('mcaDelPushButton', 'Delete rows')),
        ]),
        G('EXAFS', 'EXAFS', [
            NEW('fluo_exafs', 'Energy scans: waiting on question 6', 'label', 'A stub until question 6 is answered'),
        ]),
        G('Compare', 'Compare', [
            ROW(C('mcaAddFilePushButton', 'Add files'), C('mcaRemoveFilePushButton', 'Remove')),
            C('mcaFileListWidget', ''),
        ], fold=True),
    ],
    'legacy': [
        G('Legacy fits (until question 13 is answered)', 'Legacy', [
            ROW(C('mcaFitPushButton'), C('mcaFitAllPushButton'), C('mcaAcceptPushButton')),
            CAPTION('Peak Fit Panel (also opened by Files > Legacy…)'),
            ROW(C('peakfit.peakTypeComboBox', 'Peak type'), C('peakfit.numberOfPeakSpinBox', 'Peaks')),
            ROW(C('peakfit.bgSpinBox', 'Background order'), C('peakfit.invCheckBox', 'Inv.')),
            C('peakfit.rangeLineEdit', 'Fit range (a – b)'),
            C('peakfit.peakTW', 'Peak parameters'),
            C('peakfit.bgTW', 'Background parameters'),
            C('peakfit.chiLineEdit', 'χ²'),
            ROW(C('peakfit.fitPushButton'), C('peakfit.closePushButton')),
            CAPTION('Limits of a parameter'),
            ROW(C('peakpara.minCB', 'Min'), C('peakpara.maxCB', 'Max'), C('peakpara.okPB', 'OK'),
                C('peakpara.cancelPB', 'Cancel')),
        ], replaces=['peakfit', 'peakpara']),
    ],
    'right': [
        [PLOT('mcaPlotMplWidget', 'Spectra: counts vs energy (keV), window shaded', 'spectrum', residuals=True,
              stretch=3)],
        [PLOT('mcaIntPlotMplWidget', 'Integral vs Qz', 'xfntr', stretch=2,
              provenance='S# 50–58 · element 1 · window 4.9–5.1 keV · / Monc · merged · saved F0004 v1',
              note_button=SAVE('mcaSaveWorkbookPushButton')),
         C('mcaDataListWidget', 'Integral rows: x, I, σ')],
    ],
}

FILES = {
    'key': 'files', 'title': 'Files', 'chip': 'files',
    'was': 'Plot and 2D_Plot tabs, Plot Scale Setup',
    'replaces': ['tab_3', 'tab_4', 'plotscale'],
    'left': [
        G('Input', 'Input', [
            ROW(C('plotAddFilePushButton', 'Add'), C('plotRemoveFilePushButton', 'Remove'),
                C('plotMoveUpPushButton', '▲'), C('plotMoveDownPushButton', '▼')),
            C('plotFileListWidget', '', note='One list for 1-D and 2-D files; a 2-D file is drawn in the map'),
        ]),
        G('1-D plot', 'Display', [
            C('onedStyComboBox', 'Style'),
            ROW(C('plotLogXCheckBox', 'Log x'), C('plotLogYCheckBox', 'Log y'), C('plotGridCheckBox')),
            ROW(C('plotLegendCheckBox'), C('plotLegendLocComboBox', '')),
            ROW(C('onedLabelSizeSpinBox', 'Labels'), C('onedTickSizeSpinBox', 'Ticks')),
            C('plotRSPushButton', 'Scale and offset ▾', note='Opens the table below instead of a window'),
            C('plotscale.scaleTW', ''),
        ]),
        G('2-D map', 'Display', [
            ROW(C('twodCMapComboBox', 'Colour map', items=['viridis', 'magma', 'gray', 'jet']),
                C('twodLogIntCheckBox', 'Log')),
            C('twodColBarCheckBox', 'Colour bar'),
            ROW(C('twodMinHorizontalSlider', 'Low %'), C('twodMinLineEdit', '')),
            ROW(C('twodMaxHorizontalSlider', 'High %'), C('twodMaxLineEdit', '')),
            ROW(C('twodLabelSizeSpinBox', 'Labels'), C('twodTickSizeSpinBox', 'Ticks')),
            ROW(C('twodDenFacSpinBox', 'Point density'), C('twodIntPolComboBox', '')),
            C('twodUpdatePlotPushButton', 'Redraw'),
        ], fold=True),
        G('Tools', 'Tools', [
            C('graPushButton', 'Gradient'),
        ]),
    ],
    'legacy': [
        G('Legacy peak fit (until question 13 is answered)', 'Legacy', [
            C('plotPFPushButton', 'Peak fit…', note='Opens the Peak Fit Panel shown in Fluorescence > Legacy…'),
        ]),
    ],
    'right': [
        [PLOT('PlotMplWidget', '1-D: y vs x of the files', 'curves')],
        [PLOT('twodPlotMplWidget', '2-D map of a file', 'map')],
    ],
}

TABS = [SCANS, FRAMES, BURN, REFLECTIVITY, GID, FLUORESCENCE, FILES]

# ---------------------------------------------------------------- window-level elements

# The tab widget of today, replaced by the new tabs.
WINDOW_REPLACES = ['PlotWidget']

MENUS = [
    {'title': 'File', 'replaces': ['menuFile'], 'items': [
        C('actionOpen_Spec_File', 'Open SPEC file…'),
        NEW('file_export', 'Export…', 'action', 'Writes text or HDF5 files from a saved result (D61): the only '
            'route to exporting in ngui; no Export buttons in the tabs'),
        C('actionPreferences', 'Preferences…', note='In the prototype: the settings that stay in the dialog'),
        C('actionGiveUpWriteAccess', "Give up the workbook's write access",
          note="D1, the owner's revised Q5: one click, and the next reader of the SPEC file takes the workbook"),
        C('actionAskWriteAccess', "Ask for the workbook's write access",
          note='Also on the yellow read-only light: takes it when free, else asks the holder (Release / Keep)'),
        C('actionQuit', 'Quit'),
    ]},
    {'title': 'View', 'replaces': ['menuView'], 'items': [
        C('messageDock_toggleViewAction', 'Messages'),
        C('scriptDock_toggleViewAction', 'Script'),
        C('errorDock_toggleViewAction', 'Errors'),
        C('plotOptionsToolButton', 'Plot options…',
          note='F112: the options of the tab on show (font, ticks, grid); in ngui per tab as in the reader'),
        C('actionFitResiduals', 'Residuals above fits',
          note='One switch for every fit plot: the panels drawn here as the Residuals toggle above each fit plot (F74)'),
    ]},
    {'title': 'Tools', 'replaces': ['menuTools'], 'items': [
        C('actionToolsWindow', 'All tools…', note='The Tools collection (F84, lss_toolbox): every demonstration and '
          'figure generator, one submenu per area, generated from lss_toolbox/catalog.py as in the reader today'),
    ]},
    {'title': 'Help', 'replaces': ['menuHelp'], 'items': [
        C('actionDocumentation', 'Documentation'),
        C('actionAbout', 'About'),
        NEW('help_retired', 'Retired controls…', 'action', 'The controls this layout drops, with the reasons'),
    ]},
]

# Panes under the tab area only, hidden by default, never raising themselves (D59).
PANES = [
    {'title': 'Messages', 'replaces': ['messageDock'], 'items': [C('messageView', '', kind='pane')]},
    {'title': 'Script', 'replaces': ['scriptDock'], 'items': [C('scriptView', '', kind='pane')]},
    {'title': 'Errors', 'replaces': ['errorDock'], 'items': [
        ROW(C('errorModeComboBox', 'Error model', items=['Budget', 'Legacy']),
            C('monitorKindComboBox', 'Monitor', items=['Gaussian', 'Student t', 'Counting'])),
        ROW(C('errorModel_sigma', 'Monitor σ (%)'), C('errorModel_sigma_scan', 'Scan scatter (%)'),
            C('errorModel_width', 't width'), C('errorModel_nu', 't ν')),
        ROW(C('errorModel_f', 'Floor f'), C('errorModel_sigma_dark', 'Dark σ'), C('errorModel_g', 'Quanta per count g')),
        C('errorModelLabel', 'budget: Poisson counts, monitor noise, scan scatter, floor'),
    ]},
]

# The status bar: messages at the left, the state bar at the right (principle 5; question 12 is open).
STATUS = [
    C('statusBar', '', kind='pane'),
    C('progressDialog', '', kind='progress', note='Progress in the status bar, with Abort, instead of a window'),
    # the main window's state badges (F85, built there 2026-11-23); STATUS[2:] are drawn as badges
    C('errorsBadgeLabel', 'legacy errors', kind='badge'),
    C('normBadgeLabel', '/ Monc', kind='badge'),
    C('patchBadgeLabel', 'joint patch', kind='badge'),
    C('readOnlyLightLabel', 'read-only', kind='badge'),
]

STATE_BAR = [
    ('Live off', 'Watching the SPEC file for new scans (the panel\'s Live box).'),
]

# Settings that keep their dialog for now (prototype.md: "Preferences keep their dialog for now").
PREFERENCES = [
    G('Absorber foils', '', [
        C('prefCalibratedCheckBox', 'Calibrated foils'),
        C('prefFoilTable', 'Foil thicknesses'),
        C('prefFoilRangeLabel', '9.70–10.30 keV'),
    ]),
    # kept (orchestrator, 2026-11-23): the owner asked for automatic saving and a Save… with a note (D61),
    # not for removing the off switch or the note question; retiring them waits on the owner
    G('Saving', '', [
        C('prefAutoSaveCheckBox', 'Save results automatically', note='On by default (D56); off for quick looks'),
        C('prefSaveNoteCheckBox', 'Save… asks for a note', note='Shift-click skips the question'),
    ]),
    G('Plot options (per tab, F112)', '', [
        C('plotOptTabLabel', 'Plots of the … tab'),
        C('plotOptFontSpinBox', 'Font size'),
        C('plotOptMajorComboBox', 'Major ticks'),
        C('plotOptMinorComboBox', 'Minor ticks'),
        C('plotOptDirectionComboBox', 'Tick direction'),
        C('plotOptMirrorComboBox', 'Ticks on all sides'),
        C('plotOptGridComboBox', 'Grid'),
        C('plotOptIndexCheckBox', 'Index numbers', note='F113: crowded ones hidden, back on zoom'),
        C('plotOptAxesToolButton', 'Axes and curves…', note='matplotlib\'s one-off editor of one plot (was the toolbar\'s Customize icon)'),
        C('plotOptResetPushButton', 'As drawn'),
        C('plotOptClosePushButton', 'Close'),
    ]),
    G('Window', '', [
        C('prefNguiCheckBox', 'ngui (new layout, prototype)', note='This window; unticking closes it'),
        C('prefBadgesComboBox', 'State badges', items=['on', 'when not default', 'off']),
        # Reduction options (F86, built in the main window 2026-11-23)
        C('prefSumAllLegacyCheckBox', 'Sum All: legacy average'),
        C('prefRepeatsLegacyCheckBox', 'Ref Patch repeats: average (legacy)'),
        C('prefGisaxsRawCheckBox', 'GISAXS: raw counts (legacy)'),
        C('prefMcaFitLegacyCheckBox', 'Fluorescence fit: legacy dialog'),
        C('prefMcaFitDataWeightsCheckBox', 'Fit lines: data weights (legacy)', note='F90: P1 (Poisson) the default since 2026-11-24'),
        C('prefBurnLegacyCheckBox', 'Burn: Legacy tab'),
        C('prefClosePushButton', 'Close'),
    ]),
]
PREFERENCES_REPLACES = ['preferencesDialog']

# File > Export… (D61, owner 2026-11-23): exporting is a less-used option called from the File menu. A modest
# dialog: choose a result saved in the workbook, the format, and what to write. Every Export button of today
# becomes one entry of "Contents" (offered according to the kind of the chosen result).
EXPORT = [
    G('Result', '', [
        NEW('export_result', 'Saved result', 'combo', 'Every result the workbook holds, newest first',
            items=['R0007 v2 · reflectivity S# 6–9', 'G0002 v1 · GID map S# 22–31', 'B0003 v1 · burn S# 40',
                   'F0004 v1 · XFNTR S# 50–58', 'C0005 v1 · line cut S# 22', 'S0011 v1 · scans S# 12–14']),
    ]),
    G('Format', '', [
        NEW('export_format', 'Format', 'combo', 'Text files as today (xmodfit contract) or HDF5',
            items=['Text (as today)', 'HDF5', 'CSV']),
        C('refCovarianceCheckBox', '+ covariance', note='Reflectivity: the covariance matrix of the points too'),
    ]),
    G('Contents', '', [
        C('refExportPushButton', 'Reflectivity (_ref.txt, _rrf.txt)', kind='radio'),
        C('spExportPushButton', 'Scan columns', kind='radio'),
        C('cutExportPushButton', 'Line cuts', kind='radio'),
        C('cutFitSavePushButton', 'Peak fit results', kind='radio'),
        C('mcaExportPushButton', 'Spectra', kind='radio'),
        C('mcaExportIntPushButton', 'Fluorescence integral (_flu.txt)', kind='radio'),
        NEW('export_gid', 'GID map (Export GID)', 'radio', 'Was the "Export GID" item of the GID combo (Save GID until 2026-11-25)'),
        NEW('export_gisaxs', 'GISAXS', 'radio', 'Was the "Export GISAXS" item of the GISAXS combo (Save GISAXS until 2026-11-25)'),
        C('pdgioxs.savePushButton', 'GIOXS profiles', kind='radio'),
        C('savegraPushButton', 'Gradient (Files)', kind='radio'),
        ROW(C('peakfit.exportFitPushButton', 'Legacy fit: curve', kind='radio'),
            C('peakfit.exportParaPushButton', 'parameters', kind='radio')),
    ]),
    G('', 'Dialog', [
        ROW(NEW('export_write', 'Write files…', 'button', 'Asks for the file name, then writes'),
            NEW('export_close', 'Close', 'button', '')),
    ]),
]

# ---------------------------------------------------------------- retired

Q14 = 'dead today; retired pending owner question 14'
INLINE = 'nothing to close: the window\'s contents are now inline'
RETIRED = {
    'burnDoseSummaryLabel': 'The Burn tab\'s verdict card in this layout; the main window shows it in the burn dock (F109)',
    'burnDock': 'The Burn tab in this layout; the main window docks the burn window (F95 B10)',
    'worksheetDock': 'GID > Worksheet group in this layout; the main window docks the worksheet (F95 B10)',
    'cutfitDock': 'The fit options are inline groups in this layout; the main window docks them (F95 B10)',
    'mcafitDock': 'The fit options are inline groups in this layout; the main window docks them (F95 B10)',
    'burnExportPushButton': 'File > Export… (Burn test) in this layout; the main window puts it beside Save (F95 B9)',
    'mcaSpectraSaveWorkbookPushButton': 'One Save… per result in this layout (D61); the main window has it beside Export Spectrum (F95 B9)',
    'plotSaveWorkbookPushButton': 'One Save… per result in this layout (D61); the main window has it on the Plot tab (F95 B9)',
    # the Apex tab (Bruker Apex CCD, hidden at start)
    'apexTab': 'Apex tab, hidden since the CCD left: ' + Q14,
    **{cid: 'Apex tab, unconnected or a copy of a Pilatus control: ' + Q14 for cid in (
        'gixSpecCheckBox', 'gixDBPosLineEdit', 'gixSDDistLineEdit', 'gixCcd_OffLineEdit', 'gixBPCfacLineEdit',
        'gixAxesComboBox', 'gixCMapComboBox', 'gixMplWidget', 'gixLogIntCheckBox', 'gixMinHorizontalSlider',
        'gixMinLineEdit', 'gixMaxHorizontalSlider', 'gixMaxLineEdit', 'gixMergeSameQzCheckBox',
        'gixRefPushButton', 'gixCutDirComboBox', 'gixIntRangeLineEdit', 'gixLineAreaPushButton')},
    # the Beamlines menu
    'menuBeamlines': 'One beamline is supported: ' + Q14,
    'actionAPS_15IDC': 'The only beamline; nothing to choose: ' + Q14,
    'actionAPS_9IDC': '9-ID-C is not supported, owner 2026-11-17; hidden: ' + Q14,
    # unconnected pieces
    'commandLineEdit': 'The Command line is not connected to anything: ' + Q14,
    'peakfit2': 'Dialog never shown: ' + Q14,
    'peakfitpara': 'Dialog never shown: ' + Q14,
    'refBPCFacLineEdit': 'Defunct: read and never used (inventory); bad pixels are set in Frames > Reduce',
    'compareTab': 'Built in the main window first (F80, F105, 2026-11-24); ngui is to show the same view, comparetab.CompareTab',
    'compareListWidget': 'Part of the main window\'s Compare tab (F105)',
    'comparePlotWidget': 'Part of the main window\'s Compare tab (F105)',
    'compareOrderComboBox': 'Part of the main window\'s Compare tab (F105)',
    'compareRatioCheckBox': 'Part of the main window\'s Compare tab (F105)',
    'compareRrfCheckBox': 'Part of the main window\'s Compare tab (F105)',
    'compareFollowCheckBox': 'Part of the main window\'s Compare tab (F105)',
    'compareInfoLabel': 'Part of the main window\'s Compare tab (F105)',
    'timelineTab': 'Built in the main window first (owner, 2026-11-24); ngui is to show the same view, timelineview.TimelineView',
    'timelineView': 'The main window\'s Timeline tab (F83); ngui is to reuse it',
    'timelineFitPushButton': 'Part of the main window\'s Timeline tab (F83)',
    'timelineDoseCheckBox': 'Part of the main window\'s Timeline tab (F107)',
    'timelineEnvComboBox': 'Part of the main window\'s Timeline tab (phase 2, F75)',
    'timelineInfoLabel': 'Part of the main window\'s Timeline tab (F83)',
    'pilRoiPanel': 'One ROI close-up in this layout (Reflectivity > ROI close-up); the main window also has it beside the frame',
    'pilRoiLogCheckBox': 'One ROI close-up in this layout: its Log box is Reflectivity > ROI close-up > Log',
    'pilRoiCuesLabel': 'One ROI close-up in this layout: its checks are under Reflectivity > ROI close-up',
    'pilPeakCenDialog.peakCenTextBrowser': 'Removed 2026-11-24 (F95, Q-UI-B6): a message and marks instead of a modal box',
    'pilBadPixDialog.peakCenTextBrowser': 'Removed 2026-11-24 (F95, Q-UI-B6): the Bad Pixels list (Checks) instead of a modal box',
    # dialog chrome made unnecessary by inline groups
    'pdburn.closePushButton': 'Burn test dialog, now the Burn tab: ' + INLINE,
    'gidClosePushButton': 'GID worksheet, now GID tab groups: ' + INLINE,
    'pdformfac.okPushButton': 'Form factor, now GID > Tools: ' + INLINE,
    'pdgioxs.closePushButton': 'GIOXS, now Frames > Views: ' + INLINE,
    'mcamerge.okPushButton': 'Merge window; the Merge button acts at once: ' + INLINE,
    'mcamerge.cancelPushButton': 'Merge window; the Merge button acts at once: ' + INLINE,
    'plotscale.closePB': 'Plot Scale Setup, now Files > 1-D plot: ' + INLINE,
    'refpatchsamescan.nextPushButton': 'One choice (Sum, Drop, Patch) applies to every identical pair; no stepping',
    # duplicates merged
    'cutFitNowPushButton': 'Duplicate of "Fit peaks" once the fit options are inline (Frames > Peak fit)',
    'pilHSlitLineEdit': 'Duplicate of the GID worksheet\'s Columns (GID > Map), which it mirrored',
    'twodPlotAddFilePushButton': 'Merged into the one file list (Files > Input)',
    'twodPlotRemoveFilePushButton': 'Merged into the one file list (Files > Input)',
    'twodPlotFileListWidget': 'Merged into the one file list (Files > Input)',
}

# ---------------------------------------------------------------- walking the table


def _walk_items(items, where):
    for it in items:
        if 'row' in it:
            yield from _walk_items(it['row'], where)
        elif 'id' in it:
            yield it['id'], where, it
        elif 'special' in it:
            yield from _walk_special(it, where)
        elif 'plot' in it:
            if it['plot']:
                yield it['plot'], where, it
            if it.get('note_button'):
                yield from _walk_items([it['note_button']], where)
            if isinstance(it.get('provenance'), dict):      # the main window's line under the plot (F96)
                yield from _walk_items([it['provenance']], where)


def _walk_special(sp, where):
    kind = sp['special']
    w = '%s > %s' % (where, kind)
    for key in ('label', 'title', 'image', 'gioxs', 'gisaxs', 'movie', 'plot', 'tabwidget', 'cuts', 'note_button',
                'table'):
        v = sp.get(key)
        if isinstance(v, dict):
            yield from _walk_items([v], w)
    for key in ('toolbar', 'options', 'controls', 'items', 'footer'):
        yield from _walk_items(sp.get(key) or [], w)
    if isinstance(sp.get('movie_bar'), dict):
        yield from _walk_items(list(sp['movie_bar'].values()), w)
    for _name, v in sp.get('views') or []:
        if v:
            yield from _walk_items([v], w)
    for name, v in sp.get('pages') or []:
        yield from _walk_items(v if isinstance(v, list) else [v], '%s > %s' % (w, name))


def placements():
    """(inventory id, where in the new layout) for every placed id, including
    the containers listed in ``replaces``. An id appearing twice is an error
    (tests/test_ngui.py)."""
    out = []

    def add(cid, where):
        out.append((cid, where))

    for g in DOCK:
        for cid, w, _ in _walk_items(g['items'], 'Panel > ' + g['title']):
            add(cid, w)
        for cid in g['replaces']:
            add(cid, 'Panel > %s (replaces)' % g['title'])
    for tab in TABS:
        t = tab['title']
        for cid in tab['replaces']:
            add(cid, '%s (tab replaces)' % t)
        for section in ('left', 'legacy'):
            for g in tab.get(section, []):
                where = '%s > %s%s' % (t, 'Legacy… > ' if section == 'legacy' else '', g['title'])
                for cid, w, _ in _walk_items(g['items'], where):
                    add(cid, w)
                for cid in g['replaces']:
                    add(cid, where + ' (replaces)')
        for row in tab['right']:
            for cid, w, _ in _walk_items(row, '%s > plots' % t):
                add(cid, w)
    for cid in WINDOW_REPLACES:
        add(cid, 'Window > tabs (replaces)')
    for m in MENUS:
        for cid, w, _ in _walk_items(m['items'], 'Menu > ' + m['title']):
            add(cid, w)
        for cid in m['replaces']:
            add(cid, 'Menu > %s (replaces)' % m['title'])
    for p in PANES:
        for cid, w, _ in _walk_items(p['items'], 'Pane > ' + p['title']):
            add(cid, w)
        for cid in p['replaces']:
            add(cid, 'Pane > %s (replaces)' % p['title'])
    for cid, w, _ in _walk_items(STATUS, 'Status bar'):
        add(cid, w)
    for g in PREFERENCES:
        for cid, w, _ in _walk_items(g['items'], 'Preferences > ' + g['title']):
            add(cid, w)
    for cid in PREFERENCES_REPLACES:
        add(cid, 'Preferences (replaces)')
    for g in EXPORT:
        for cid, w, _ in _walk_items(g['items'], 'File > Export… > ' + (g['title'] or 'buttons')):
            add(cid, w)
    return out


def placed_items():
    """{inventory id: the C(...) dict} for every placed control drawn as a widget or action."""
    out = {}
    groups = [g for g in DOCK] + [g for tab in TABS for s in ('left', 'legacy') for g in tab.get(s, [])]
    groups += [{'items': m['items']} for m in MENUS] + [{'items': p['items']} for p in PANES]
    groups += [{'items': STATUS}] + PREFERENCES + EXPORT
    for g in groups:
        for cid, _w, it in _walk_items(g['items'], ''):
            out[cid] = it
    for tab in TABS:
        for row in tab['right']:
            for cid, _w, it in _walk_items(row, ''):
                out[cid] = it
    return out
