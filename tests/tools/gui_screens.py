"""Screenshots of every area of the reader's window and of its dialogs, with an
index, for the GUI overhaul (docs/gui/README.md; owner, 2026-11-22: "screenshots
of every GUI area" to remind the owner what each part looks like).

    python tests/tools/gui_screens.py [--out docs/gui/screens] [--skip-slow]

Makes ``NN_<area>_<state>.png`` files (NN gives the reading order: 00 overview,
01 empty window, 1x left panel and SpecPlot, 2x Pilatus, 3x Reflectivity,
4x GID, 5x burn tests, 6x cuts, 7x MCA and XFNTR, 8x Plot and 2D_Plot, 9x
dialogs, menus and panes) and rewrites the table of ``README.md`` beside them.
The "Observations" section of that README is written by hand and is kept when
the tool reruns.

Data: the public NX school set (sample_data/NX_school) and synthetic data from
tests/synth.py (MCA spectra, a burn series, an absorber scan), written into a
temporary folder. Nothing is written into sample_data/ (AGENTS.md rule 7): the
output folder of every window is a temporary folder. Run from anywhere; needs no
display (Qt offscreen). Takes a few minutes (the GID patch and Ref Patch of the
real data dominate).

Whole-window shots are at Qt scale 1. The window cannot be narrower than about
2266 px (its minimum size), so that is the width of the shots.

Messages the window raises (MainWindow.notify) and exceptions in slots
(sys.excepthook) are collected, not shown or raised, and are listed at the end
with the action that caused them: an exception there is a bug worth reporting.
"""
import argparse
import glob
import os
import re
import sys
import tempfile
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


_TMP_COUNT = {}


def fixed_tmp(prefix):
    """A fresh empty folder whose name is the same on every run
    (<tmp>/lss_screens/<prefix><n>, n counting the calls with that prefix):
    paths appear in plot titles, legends and the status bar, and random
    names made unchanged screenshots differ on every rerun (2026-11-23)."""
    import shutil
    n = _TMP_COUNT[prefix] = _TMP_COUNT.get(prefix, 0) + 1
    path = os.path.join(tempfile.gettempdir(), 'lss_screens', '%s%d' % (prefix, n))
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path)
    return path

os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('MPLBACKEND', 'Agg')
os.environ['LSS_READER_LOG_DIR'] = fixed_tmp('lss_screens_logs_')
os.environ['LSS_READER_PREFS'] = os.path.join(fixed_tmp('lss_screens_prefs_'), 'p.json')
os.environ['LSS_READER_SELECTION_DELAY_MS'] = '0'
os.environ['LSS_READER_DISK_CACHE'] = fixed_tmp('lss_screens_cache_')

NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
WIN_W, WIN_H = 2300, 1400

# ---- bookkeeping --------------------------------------------------------

OUT = None
ENTRIES = []          # (file, shows, state)
PROBLEMS = []         # (action, kind, text)
ACTION = ['start']
T0 = time.time()


def log(msg):
    print('[%5.0fs] %s' % (time.time() - T0, msg), flush=True)


def save_png(img, name, shows, state):
    """``img``: a QImage/QPixmap or a PIL image."""
    from PIL import Image
    path = os.path.join(OUT, name)
    if not isinstance(img, Image.Image):
        img = qimage_to_pil(img)
    # 256 colours without dithering: the labels stay sharp, the colour maps
    # band a little, and the folder is about 6 MB instead of 13.5 MB, which
    # matters because the screenshots are regenerated (and committed) often.
    img = img.convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                                      dither=Image.Dither.NONE)
    img.save(path, optimize=True)
    ENTRIES.append((name, shows, state))
    log('saved %s (%dx%d)' % (name, img.width, img.height))


def qimage_to_pil(img):
    from PIL import Image
    from PyQt5 import QtCore, QtGui
    if isinstance(img, QtGui.QPixmap):
        img = img.toImage()
    img = img.convertToFormat(QtGui.QImage.Format_RGBA8888)
    ptr = img.constBits()
    ptr.setsize(img.byteCount())
    pil = Image.frombuffer('RGBA', (img.width(), img.height()), bytes(ptr), 'raw', 'RGBA', img.bytesPerLine(), 1)
    return pil.convert('RGB')


def step(name):
    """Decorator: run a capture step; a failure is recorded and the tool carries on."""
    def deco(f):
        def run(*a, **k):
            ACTION[0] = name
            try:
                return f(*a, **k)
            except Exception as e:      # the tool must finish; the failure is reported
                PROBLEMS.append((name, 'tool step failed', '%s: %s' % (type(e).__name__, e)))
                log('STEP FAILED %s: %s' % (name, e))
                traceback.print_exc()
        return run
    return deco


# ---- Qt helpers ---------------------------------------------------------

def settle(app, n=3):
    for _ in range(n):
        app.processEvents()


def grab_window(w, app):
    settle(app)
    return qimage_to_pil(w.grab())


def wait(app, seconds=0.3):
    """Let pending timers fire (deferred redraws: a colour bar, a slider) before
    a picture is taken; three processEvents alone left the GISAXS shot
    different from run to run (the Tools audit, 2026-11-25). Not for every
    shot: a frame movie's timer would advance its frame."""
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def getw(w, name):
    """A control of the window: on the generated ``ui`` or on the window itself."""
    return getattr(w.ui, name, None) or getattr(w, name)


def rect_in(win, widget):
    """(x0, y0, x1, y1) of ``widget`` in the coordinates of ``win``."""
    from PyQt5.QtCore import QPoint
    p = widget.mapTo(win, QPoint(0, 0))
    return (p.x(), p.y(), p.x() + widget.width(), p.y() + widget.height())


def crop(img, rect, pad=4):
    x0, y0, x1, y1 = rect
    return img.crop((max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad)))


def union(*rects):
    return (min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects))


def new_window(app, spec=None, directory=None):
    import mainwindow
    mainwindow.MainWindow.messageStamp = lambda self: '12:00:00'     # the same pictures from run to run (audit)
    w = mainwindow.MainWindow()
    timer = getattr(w, 'pilMovieTimer', None)
    if timer is not None:                     # the movie plays but stays on its frame: a shot does not depend on timing
        timer.timeout.disconnect(w.pilMovieTick)
    w.resize(WIN_W, WIN_H)
    w.show()
    if spec:
        w.openSpecFile(fname=spec)
        w.directory = directory or fixed_tmp('lss_screens_out_')   # rule 7
    settle(app)
    return w


def free(w, app):
    import sweep
    sweep.dispose(w, app, None)


def select_scans(w, app, rows):
    import sweep
    sweep._select_scans(w, app, rows)


def select_frames(w, app, rows=None):
    import sweep
    sweep._select_images(w, app, rows)


def tab(w, app, text):
    tw = w.ui.PlotWidget
    for i in range(tw.count()):
        if tw.tabText(i) == text:
            tw.setCurrentIndex(i)
    settle(app)


def combo_do(w, app, combo, text):
    i = combo.findText(text)
    assert i >= 0, text
    combo.setCurrentIndex(i)
    combo.activated.emit(i)
    settle(app)


def visible_tops(app):
    from PyQt5 import QtWidgets
    return [t for t in app.topLevelWidgets() if t.isVisible()]


class Dialogs:
    """Captures dialogs: modal ones (exec_) when they are executed, the rest
    by name on request."""

    def __init__(self, app, w_getter):
        self.app = app
        self.n = 0
        self.pending = None     # (name, shows, state) given by the step

    def grab_widget(self, d, name, shows, state):
        settle(self.app)
        save_png(d.grab(), name, shows, state)


def install_patches(app):
    from PyQt5 import QtWidgets
    import mainwindow
    ctx = {'name': None, 'shows': '', 'state': '', 'captured': []}

    def dialog_exec(self, *a, **k):
        settle(app)
        if ctx['name'] and not isinstance(self, QtWidgets.QFileDialog):
            idx = len(ctx['captured'])
            name = ctx['name'] if idx == 0 else ctx['name'].replace('.png', '%s.png' % chr(ord('a') + idx))
            save_png(self.grab(), name, ctx['shows'], ctx['state'])
            ctx['captured'].append(self)
        self.close()
        return 0

    def box_exec(self, *a, **k):
        PROBLEMS.append((ACTION[0], 'message box', self.text()))
        return QtWidgets.QMessageBox.Ok

    def static_box(*a, **k):
        PROBLEMS.append((ACTION[0], 'message box', ' | '.join(str(x) for x in a[1:3])))
        return QtWidgets.QMessageBox.No

    real_notify = mainwindow.MainWindow.notify

    def notify(self, text, title='Warning', level='warning'):
        PROBLEMS.append((ACTION[0], 'message' if title != 'Error' else 'failure', str(text).replace('\n', ' | ')))
        return real_notify(self, text, title, level)

    mainwindow.MainWindow.notify = notify
    QtWidgets.QDialog.exec_ = dialog_exec
    QtWidgets.QDialog.exec = dialog_exec
    QtWidgets.QMessageBox.exec_ = box_exec
    QtWidgets.QMessageBox.exec = box_exec
    for n in ('question', 'information', 'warning', 'critical', 'about'):
        setattr(QtWidgets.QMessageBox, n, staticmethod(static_box))
    files = {'open': [], 'many': []}
    ctx['files'] = files
    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (files['open'][0] if files['open'] else '', ''))
    QtWidgets.QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: (list(files['many']), ''))
    QtWidgets.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ('', ''))
    QtWidgets.QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: '')
    QtWidgets.QInputDialog.getMultiLineText = staticmethod(lambda *a, **k: ('', True))
    QtWidgets.QInputDialog.getText = staticmethod(lambda *a, **k: ('', False))
    sys.excepthook = lambda t, v, tb: PROBLEMS.append(
        (ACTION[0], 'EXCEPTION', '%s: %s  @ %s' % (t.__name__, v, _where(tb))))
    time.sleep = lambda s: None
    return ctx


def _where(tb):
    frames = [f for f in traceback.extract_tb(tb) if 'site-packages' not in f.filename]
    f = (frames or traceback.extract_tb(tb))[-1]
    return '%s:%s:%s' % (os.path.basename(f.filename), f.lineno, f.name)


def arm(ctx, name, shows, state):
    ctx['name'], ctx['shows'], ctx['state'], ctx['captured'] = name, shows, state, []


def disarm(ctx):
    ctx['name'] = None


def grab_toplevels(app, before, prefix, shows, state, ctx=None, skip=()):
    """Save every top-level widget that became visible since ``before``.
    Progress windows are left out: a finished 'Reading Scan #1, 100%' window
    from an earlier step sometimes appears late and was caught instead of
    the window wanted (2026-11-23; TODO area I)."""
    from PyQt5.QtWidgets import QProgressDialog
    settle(app)
    new = [t for t in visible_tops(app) if t not in before and t not in skip and not isinstance(t, QProgressDialog)]
    k = 0
    for t in new:
        name = prefix if k == 0 else prefix.replace('.png', '%s.png' % chr(ord('a') + k))
        save_png(t.grab(), name, shows if k == 0 else shows + ' (another window opened by the same action)', state)
        k += 1
    return new


# ---- the overview -------------------------------------------------------

def annotated_overview(w, app, img, name, shows, state):
    from PIL import ImageDraw, ImageFont
    d = ImageDraw.Draw(img, 'RGBA')
    try:
        font = ImageFont.load_default(size=22)
    except TypeError:
        font = ImageFont.load_default()
    ui = w.ui
    areas = []

    def add(label, rect, colour):
        areas.append((label, rect, colour))

    add('menu bar', rect_in(w, ui.menuBar), (200, 0, 0))
    left = union(*[rect_in(w, x) for x in (ui.scanListWidget, getw(w, 'seriesComboBox'), ui.imageListWidget,
                                            ui.backgroundListWidget, getw(w, 'removePushButton'), getw(w, 'speUpSpeFilePushButton'))])
    add('left panel: series, scan list, frame list, background list', left, (0, 110, 0))
    add('scan list', rect_in(w, ui.scanListWidget), (0, 150, 0))
    add('series chooser', rect_in(w, getw(w, 'seriesComboBox')), (0, 150, 0))
    add('frame (detector) list', rect_in(w, ui.imageListWidget), (0, 150, 0))
    add('background list', rect_in(w, ui.backgroundListWidget), (0, 150, 0))
    add('tab bar (7 tabs)', rect_in(w, ui.PlotWidget.tabBar()), (0, 0, 200))
    cur = ui.PlotWidget.currentWidget()
    add('tab page: controls and plot', rect_in(w, cur), (150, 0, 150))
    add('status bar', rect_in(w, ui.statusBar), (90, 90, 90))
    for dock, label in ((w.messageDock, 'Messages pane'), (w.scriptDock, 'Script pane'), (w.errorDock, 'Errors pane')):
        if dock.isVisible():
            add('bottom dock area (tabs: Messages / Script / Errors)', rect_in(w, dock), (0, 130, 130))
            break
    # numbered badges on the window; the key is in a margin added at the right
    # (labels written over the window would hide the controls they name)
    from PIL import Image
    margin = 780
    canvas = Image.new('RGB', (img.width + margin, img.height), (255, 255, 255))
    canvas.paste(img, (0, 0))
    d = ImageDraw.Draw(canvas, 'RGBA')
    d.text((img.width + 20, 14), 'Key', fill=(0, 0, 0, 255), font=font)
    for k, (label, (x0, y0, x1, y1), c) in enumerate(areas, start=1):
        d.rectangle((x0, y0, x1 - 1, y1 - 1), outline=c + (255,), width=3)
        r = 15
        cx, cy = min(x1 - r - 2, max(x0 + r + 2, x0 + r + 2 + 40 * (k % 3))) if k not in (1, 9) else x0 + r + 2, y0 + r + 2
        if k == 1:
            cx, cy = x1 - r - 2, y0 + r
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c + (255,))
        d.text((cx, cy), str(k), fill=(255, 255, 255, 255), font=font, anchor='mm')
        ky = 60 + 44 * (k - 1)
        d.ellipse((img.width + 20, ky - r, img.width + 20 + 2 * r, ky + r), fill=c + (255,))
        d.text((img.width + 20 + r, ky), str(k), fill=(255, 255, 255, 255), font=font, anchor='mm')
        d.text((img.width + 64, ky), label, fill=(0, 0, 0, 255), font=font, anchor='lm')
    img = canvas
    save_png(img, name, shows, state)


# ---- the steps ----------------------------------------------------------

def _series_row(w, text):
    c = getw(w, 'seriesComboBox')
    for i in range(c.count()):
        if text in c.itemText(i):
            return i
    return -1


def run_nx(app, ctx, skip_slow):
    import numpy as np
    from PyQt5.QtCore import QPoint
    tmp = fixed_tmp('lss_screens_files_')

    # --- empty window
    @step('empty window')
    def empty():
        w = new_window(app)
        img = grab_window(w, app)
        save_png(img, '01_window_empty.png', 'Whole window, nothing opened', 'No SPEC file; SpecPlot tab (first tab) shown')
        tw = w.ui.PlotWidget
        for t in ('Pilatus', 'Reflectivity', 'Line/Area Cuts', 'MCA', 'Plot', '2D_Plot'):
            tab(w, app, t)
            sl = {'Pilatus': '20_pilatus_empty', 'Reflectivity': '30_reflectivity_empty',
                  'Line/Area Cuts': '60_cuts_empty', 'MCA': '70_mca_empty', 'Plot': '80_plot_empty',
                  '2D_Plot': '82_2dplot_empty'}[t]
            save_png(crop(grab_window(w, app), rect_in(w, w.ui.PlotWidget)), sl + '.png',
                     'The %s tab (page and its controls) with nothing loaded' % t,
                     'No SPEC file; crop of the tab widget')
        free(w, app)
    empty()

    w = new_window(app, NX)
    log('NX opened: %d scans' % w.ui.scanListWidget.count())

    # --- overview and left panel
    @step('overview')
    def overview():
        select_scans(w, app, [3])
        tab(w, app, 'SpecPlot')
        w.scriptDock.show()
        w.messageDock.show()
        w.scriptDock.raise_()
        settle(app)
        img = grab_window(w, app)
        annotated_overview(w, app, img.copy(), '00_overview_annotated.png',
                           'Whole window with the main areas outlined and named (the "where is what" map)',
                           'NX school 20260923 opened; scan 4 (a2scan sh/oh) selected; SpecPlot tab; Script pane raised in the bottom dock')
        save_png(img, '00b_overview_plain.png', 'The same window, unannotated',
                 'NX school 20260923 opened; scan 4 selected; SpecPlot tab; bottom dock open (Script tab)')
        w.scriptDock.hide()
        w.messageDock.hide()
    overview()

    @step('left panel')
    def left_panel():
        sr = _series_row(w, 'reflectivity 4/?')
        getw(w, 'seriesComboBox').setCurrentIndex(sr)
        getw(w, 'seriesComboBox').activated.emit(sr)
        settle(app)
        img = grab_window(w, app)
        r = union(*[rect_in(w, x) for x in (w.ui.scanListWidget, getw(w, 'seriesComboBox'), w.ui.imageListWidget,
                                             w.ui.backgroundListWidget, getw(w, 'removePushButton'), getw(w, 'speUpSpeFilePushButton'))])
        save_png(crop(img, r, 12), '10_leftpanel_series_chosen.png',
                 'Left panel: series chooser, scan list, frame list, background list, buttons',
                 'NX opened; series "reflectivity 4/?: S# 6-9" chosen in the series chooser (its scans become the selection)')
        # the series dropdown, open
        getw(w, 'seriesComboBox').showPopup()
        settle(app)
        v = getw(w, 'seriesComboBox').view()
        if v.isVisible():
            save_png(v.window().grab(), '10b_leftpanel_series_dropdown.png', 'The series chooser list opened',
                     'NX opened; the five series entries')
        getw(w, 'seriesComboBox').hidePopup()
        settle(app)
    left_panel()

    @step('specplot')
    def specplot():
        select_scans(w, app, [3])
        tab(w, app, 'SpecPlot')
        img = grab_window(w, app)
        save_png(img, '11_specplot_motor_scan.png', 'SpecPlot tab, whole window',
                 'Scan 4 (a2scan sh/oh, 20 points) selected; default axes')
        save_png(crop(img, rect_in(w, w.ui.PlotWidget)), '12_specplot_tab_crop.png', 'SpecPlot tab page: controls and plot',
                 'Scan 4 selected')
        select_scans(w, app, [3, 4])
        save_png(crop(grab_window(w, app), rect_in(w, w.ui.PlotWidget)), '13_specplot_two_scans.png',
                 'SpecPlot with two scans selected (legend, N-scan controls)', 'Scans 4 and 5 selected')
        select_scans(w, app, [0])
        save_png(crop(grab_window(w, app), rect_in(w, w.ui.PlotWidget)), '13b_specplot_beam_off_scan.png',
                 'SpecPlot of scan 1 (a motor scan with the beam off)', 'Scan 1 selected')
    specplot()

    @step('timeline')
    def timeline_tab():
        tab(w, app, 'Timeline')
        save_png(crop(grab_window(w, app), rect_in(w, w.ui.PlotWidget)), '14_timeline_tab.png',
                 'Timeline tab (F83): events, sx, sample-height scans and scans on one time axis',
                 'NX school file opened; Timeline tab shown (fitted to the whole file)')
        w.timelineTab.doseCheckBox.setChecked(True)            # F107: the burns 14 and 15 are analysed
        save_png(crop(grab_window(w, app), rect_in(w, w.ui.PlotWidget)), '14b_timeline_dose.png',
                 'Timeline with Dose on (F107): the sx line coloured by each spot\'s dose as a fraction of the '
                 'burn test\'s dose to a 5 % change',
                 'NX school file; Dose ticked (beam 1 mm wide, its height from the sample-height scans)')
        w.timelineTab.doseCheckBox.setChecked(False)
    timeline_tab()

    # --- Pilatus
    @step('pilatus')
    def pilatus():
        select_scans(w, app, [10])
        tab(w, app, 'Pilatus')
        save_png(grab_window(w, app), '20_pilatus_scan_selected_no_frames.png',
                 'Pilatus tab, whole window: a scan with images selected, no frame selected yet',
                 'Scan 11 (ascan dth, 40 frames) selected, no frame selected')
        select_frames(w, app, [0])
        img = grab_window(w, app)
        save_png(img, '21_pilatus_one_frame.png', 'Pilatus tab, whole window, one frame', 'Scan 11, frame 1 selected')
        save_png(crop(img, rect_in(w, w.ui.PlotWidget)), '21b_pilatus_tab_controls.png',
                 'Pilatus tab page (controls above, image below)', 'Scan 11, frame 1')
        select_frames(w, app, [0, 10, 20])
        save_png(grab_window(w, app), '22_pilatus_three_frames.png', 'Pilatus tab with three frames selected (a movie since 2026-11-24, F69)',
                 'Scan 11, frames 1, 11, 21 selected')
        t = time.time()
        select_frames(w, app, None)
        dt = time.time() - t
        save_png(grab_window(w, app), '23_pilatus_all_frames_of_a_scan.png',
                 'Pilatus tab with ALL frames of a long scan selected: the movie (F69; before 2026-11-24, 10 small tiles)',
                 'Scan 11: all 40 frames selected (drawing took %.1f s offscreen)' % dt)
        select_scans(w, app, [5, 6, 7, 8])
        select_frames(w, app, None)
        save_png(grab_window(w, app), '23b_pilatus_all_frames_reflectivity_series.png',
                 'Pilatus tab with all frames of the four reflectivity scans selected',
                 'Scans 6-9: all %d frames selected' % w.ui.imageListWidget.count())
        select_scans(w, app, [3])
        w.ui.pilCMapComboBox.setCurrentIndex(0)
    pilatus()

    # --- Reflectivity: Ref Patch
    @step('ref patch')
    def refpatch():
        select_scans(w, app, [5, 6, 7, 8])
        select_frames(w, app, None)
        tab(w, app, 'Pilatus')
        before = visible_tops(app)
        arm(ctx, '31_refpatch_dialog_first_join.png', 'Ref Patch window (opened by Pilatus > Ref Patch), first join',
            'Scans 6-9 all frames; Ref Patch clicked')
        w.ui.pilRefPatchPushButton.click()
        settle(app)
        disarm(ctx)
        grab_toplevels(app, before, '31_refpatch_dialog_first_join.png',
                       'Ref Patch window (opened by Pilatus > Ref Patch), first join',
                       'Scans 6-9 all frames; Ref Patch clicked', skip=[w])
        save_png(grab_window(w, app), '31b_refpatch_main_window_behind.png',
                 'Main window while the Ref Patch window is open', 'Scans 6-9; Ref Patch open at first join')
        for i in range(3):
            w.uirefpatch.nextPushButton.click()
            settle(app)
            if i == 0:
                save_png(w.uirefpatch.grab(), '31c_refpatch_dialog_second_join.png',
                         'Ref Patch window at the second join', 'Scans 6-9; first join accepted')
        settle(app)
        tab(w, app, 'Reflectivity')
        save_png(grab_window(w, app), '32_reflectivity_after_patch.png',
                 'Reflectivity tab after Ref Patch (finished on the patched curve)',
                 'Scans 6-9 patched, all three joins accepted; sub-tab: %s' % w.ui.refDataTabWidget.tabText(w.ui.refDataTabWidget.currentIndex()))
        for i in range(w.ui.refDataTabWidget.count()):
            w.ui.refDataTabWidget.setCurrentIndex(i)
            settle(app)
            t = w.ui.refDataTabWidget.tabText(i)
            img = grab_window(w, app)
            save_png(crop(img, rect_in(w, w.ui.PlotWidget)), '33_reflectivity_%s_subtab.png' % t.lower().replace(' ', '_'),
                     'Reflectivity tab, "%s" sub-tab (page and controls)' % t, 'Scans 6-9 patched')
        w.ui.refDataTabWidget.setCurrentIndex(1)
        # export data used by the Plot tab later
        try:
            np.savetxt(os.path.join(tmp, 'nx_6-9_ref.txt'), w.normRefData)
            ctx['plot_files'] = [os.path.join(tmp, 'nx_6-9_ref.txt')]
        except Exception:
            pass
    if not skip_slow:
        refpatch()

    @step('compare')
    def compare_tab():
        app.processEvents()                      # the patch is saved by itself once the event loop is idle
        tab(w, app, 'Compare')
        save_png(crop(grab_window(w, app), rect_in(w, w.ui.PlotWidget)), '34_compare_tab.png',
                 'Compare tab (F80, F105): the reflectivities saved in the workbook, overlaid',
                 'Scans 6-9 patched and saved automatically; Compare tab shown')
    if not skip_slow:
        compare_tab()

    # --- GID
    @step('gid patch')
    def gid():
        select_scans(w, app, [10, 11])
        select_frames(w, app, None)
        tab(w, app, 'Pilatus')
        save_png(crop(grab_window(w, app), rect_in(w, w.ui.PlotWidget)), '40_gid_controls_before_patch.png',
                 'Pilatus tab with scans 11-12 selected: the GID drop-down (GID, GID Patch, ..., Worksheet) and neighbours',
                 'Scans 11-12 all frames selected')
        # the gid combo popup
        w.ui.gidComboBox.showPopup()
        settle(app)
        v = w.ui.gidComboBox.view()
        if v.isVisible():
            save_png(v.window().grab(), '40b_gid_dropdown.png', 'The GID drop-down opened', 'Pilatus tab, scans 11-12')
        w.ui.gidComboBox.hidePopup()
        before = visible_tops(app)
        w.gidPatchPushButton.click(); settle(app)
        settle(app)
        img = grab_window(w, app)
        save_png(img, '41_gid_patch_pinhole.png', 'Whole window after GID Patch of scans 11-12 (pinhole mode, the default)',
                 'Scans 11-12 all frames; GID drop-down > GID Patch; tab now: %s' % w.ui.PlotWidget.tabText(w.ui.PlotWidget.currentIndex()))
        grab_toplevels(app, before, '41b_gid_patch_other_windows.png', 'Window opened by GID Patch', 'Scans 11-12', skip=[w])
        # which tab shows the map
        for t in ('Pilatus', '2D_Plot', 'Plot', 'Line/Area Cuts'):
            tab(w, app, t)
        tab(w, app, 'Pilatus')
        before = visible_tops(app)
        w.gidWorksheetPushButton.click(); settle(app)
        settle(app)
        grab_toplevels(app, before, '42_gid_worksheet_window.png', 'GID worksheet window (GID drop-down > Worksheet)',
                       'After GID Patch of scans 11-12', skip=[w])
        ws = getattr(w, 'gidWorksheet', None)
        if ws is not None and ws.isVisible():
            ws.close()
        before = visible_tops(app)
        arm(ctx, '43_gid_form_factor_dialog.png', 'Form Factor window (GID drop-down > Form Factor)', 'After GID Patch of scans 11-12')
        combo_do(w, app, w.ui.gidComboBox, 'Form Factor')
        disarm(ctx)
        grab_toplevels(app, before, '43_gid_form_factor_dialog.png', 'Form Factor window (GID drop-down > Form Factor)',
                       'After GID Patch of scans 11-12', skip=[w])
        for t in list(visible_tops(app)):
            if t is not w:
                t.close()
        settle(app)
    if not skip_slow:
        gid()

    # --- line / area cuts (on the GID map)
    @step('cuts')
    def cuts():
        tab(w, app, 'Pilatus')
        w.ui.pilCutDirComboBox.setCurrentIndex(0)
        w.ui.pilIntRangeLineEdit.setText('0.0:0.2')
        w.ui.pilLineAreaPushButton.click()
        settle(app)
        tab(w, app, 'Line/Area Cuts')
        img = grab_window(w, app)
        save_png(img, '60_cuts_gid_qz_cut.png', 'Line/Area Cuts tab with a cut of the patched GID map (Qz 0.0:0.2 vs Qxy)',
                 'GID patch of scans 11-12; Pilatus tab: Q H Cut 0.0:0.2, Line/Area Cuts clicked')
        w.cutFitPushButton.click()
        settle(app)
        save_png(crop(grab_window(w, app), rect_in(w, w.ui.PlotWidget)), '61_cuts_after_peak_fit.png',
                 'Line/Area Cuts after Fit peaks', 'Same cut; Fit peaks clicked')
        before = visible_tops(app)
        w.cutFitOptionsPushButton.click()
        settle(app)
        grab_toplevels(app, before, '62_cuts_fit_options_dialog.png', 'Fit options... dialog of the cut fits', 'Cut plotted and fitted', skip=[w])
        if getattr(w, 'cutFitDialog', None) is not None:
            w.cutFitDialog.close()
        tab(w, app, 'Pilatus')
        w.ui.pilCutDirComboBox.setCurrentIndex(1)
        w.ui.pilIntRangeLineEdit.setText('1.25:1.35')
        w.ui.pilLineAreaPushButton.click()
        settle(app)
        tab(w, app, 'Line/Area Cuts')
        save_png(crop(grab_window(w, app), rect_in(w, w.ui.PlotWidget)), '63_cuts_gid_qxy_rod.png',
                 'Line/Area Cuts with a second cut added (Qxy 1.25:1.35 vs Qz, the Bragg rod)', 'Same map; second cut added to the plot')
    if not skip_slow:
        cuts()

    # --- GISAXS dialog
    @step('gisaxs')
    def gisaxs():
        select_scans(w, app, [11])                  # scan 12 frame 1 as the background
        select_frames(w, app, [0])
        tab(w, app, 'Pilatus')
        w.ui.backgroundPushButton.click()
        settle(app)
        bl = w.ui.backgroundListWidget
        if bl.count():
            bl.item(0).setSelected(True)
            bl.itemSelectionChanged.emit()
        select_scans(w, app, [10])
        select_frames(w, app, [0])
        before = visible_tops(app)
        arm(ctx, '90_dialog_gioxs.png', 'GIOXS window (Pilatus > GIOXS)', 'Scan 11 frame 1 as data, scan 12 frame 1 as background')
        w.ui.pilGioxsPushButton.click()
        settle(app)
        disarm(ctx)
        grab_toplevels(app, before, '90_dialog_gioxs.png', 'GIOXS window (Pilatus > GIOXS)', 'Scan 11 frame 1 as data, scan 12 frame 1 as background', skip=[w])
        for t in list(visible_tops(app)):
            if t is not w:
                t.close()
        combo_do(w, app, w.ui.gisaxsComboBox, 'Show GISAXS')
        wait(app)                                # its colour bar and slider are drawn by timers
        save_png(grab_window(w, app), '91_gisaxs_show.png', 'Whole window after GISAXS drop-down > Show GISAXS',
                 'Scan 11 frame 1 with a background; tab: %s' % w.ui.PlotWidget.tabText(w.ui.PlotWidget.currentIndex()))
    gisaxs()

    # --- burn tests
    @step('gid burn')
    def burn():
        tab(w, app, 'Pilatus')
        select_scans(w, app, [14])
        select_frames(w, app, None)
        before = visible_tops(app)
        w.ui.pilBurnPushButton.click()
        settle(app, 6)
        d = w.uipdburn
        save_png(d.grab(), '50_burn_gid_trends_view.png', 'Burn-test window, Trends tab, GID burn (scan 15)',
                 'Scan 15 (20 frames at one position) selected; Pilatus > Burn Test')
        save_png(grab_window(w, app), '50b_burn_main_window_behind.png', 'Main window behind the burn-test window',
                 'Scan 15, burn window open')
        d.refPushButton.click()
        settle(app)
        save_png(d.grab(), '51_burn_legacy_ref_view.png', 'Burn-test window, legacy plot tab after its Reflectivity button',
                 'Scan 15; the legacy REF burn analysis button clicked (on GID data)')
        try:
            combo_do(w, app, d.gidComboBox, d.gidComboBox.itemText(1))
        except Exception:
            pass
        d.burnTabWidget.setCurrentIndex(1)
        settle(app)
        save_png(d.grab(), '52_burn_legacy_gid_view.png', 'Burn-test window, legacy tab after the GID combo',
                 'Scan 15; legacy GID burn analysis chosen: %s' % d.gidComboBox.currentText())
        d.burnTabWidget.setCurrentIndex(0)
        settle(app)
        d.close()
        settle(app)
    if not skip_slow:
        burn()
    return w


def run_dialogs_on(w, app, ctx):
    """Dialogs and panes that need the NX window (still open)."""
    from PyQt5.QtCore import QPoint, Qt

    @step('scan info')
    def scaninfo():
        select_scans(w, app, [10])
        arm(ctx, '92_dialog_scan_info.png', 'Scan info window (double-click a scan in the scan list)', 'Scan 11 selected')
        w.displayScanInfo()
        disarm(ctx)
    scaninfo()

    @step('g_l2 g_l3 abs_ratio')
    def calcs():
        # an absorber scan is needed for the ratio; none in NX. Open the other two and the ratio's refusal.
        # The g_l dialogs need a fitted centre for every selected scan, and SpecPlot fits the last one
        # selected: plot the sample-height scans 5 and 13 one by one, then select both (scan 4 is flat:
        # since the fit rules of 2026-11-23 a flat scan is not fitted, so it has no centre).
        tab(w, app, 'SpecPlot')
        for row in (4, 12):
            select_scans(w, app, [row])
        select_scans(w, app, [4, 12])
        arm(ctx, '93_dialog_g_l2.png', 'Calculations > G_l2 window', 'Scans 5 and 13 (sample height) fitted on SpecPlot')
        w.ui.actionG_l2.trigger()
        disarm(ctx)
        arm(ctx, '94_dialog_g_l3.png', 'Calculations > G_l3 window', 'Scans 5 and 13 (sample height) fitted on SpecPlot')
        w.ui.actionG_l3.trigger()
        disarm(ctx)
        settle(app)
    calcs()

    @step('preferences')
    def prefs():
        before = visible_tops(app)
        w.ui.actionPreferences.trigger()
        settle(app)
        grab_toplevels(app, before, '95_dialog_preferences.png', 'File > Preferences window', 'Defaults', skip=[w])
        if w.preferencesDialog is not None:
            w.preferencesDialog.close()
    prefs()

    @step('panes')
    def panes():
        w.messageView.clear()
        w.notify('Example message (as the reader shows messages instead of dialogs)')
        w.notify('A second line:\nwith a continuation line')
        w.messageDock.show()
        w.messageDock.raise_()
        settle(app)
        img = grab_window(w, app)
        save_png(crop(img, rect_in(w, w.messageDock), 8), '96_pane_messages.png', 'Messages pane (bottom dock)',
                 'Two example messages posted (not from a real action)')
        w.scriptDock.show()
        w.scriptDock.raise_()
        select_scans(w, app, [3])
        settle(app)
        save_png(crop(grab_window(w, app), rect_in(w, w.scriptDock), 8), '97_pane_script.png', 'Script pane (bottom dock)',
                 'After the reductions run in this session (the script records them)')
        # Errors pane in budget mode
        w.errorDock.show()
        w.errorDock.raise_()
        settle(app)
        save_png(crop(grab_window(w, app), rect_in(w, w.errorDock), 8), '98_pane_errors_legacy.png',
                 'Errors pane (bottom dock), Legacy error model', 'Defaults')
        w.errorModeComboBox.setCurrentIndex(1)
        w.setErrorModel()
        settle(app)
        save_png(crop(grab_window(w, app), rect_in(w, w.errorDock), 8), '98b_pane_errors_budget.png',
                 'Errors pane (bottom dock), Budget error model (extra monitor controls appear)', 'Errors combo set to Budget')
        w.errorModeComboBox.setCurrentIndex(0)
        w.setErrorModel()
        w.errorDock.hide()
        w.scriptDock.hide()
        w.messageDock.hide()
    panes()

    @step('menus')
    def menus():
        bar = w.ui.menuBar
        lines = []
        shown = 0
        for act in bar.actions():
            m = act.menu()
            if m is None:
                continue
            geo = bar.actionGeometry(act)
            pos = bar.mapToGlobal(QPoint(geo.left(), geo.bottom()))
            m.popup(pos)
            settle(app)
            title = m.title().replace('&', '') or act.text()
            entries = [a.text().replace('&', '') for a in m.actions() if a.text() or a.isSeparator()]
            lines.append((title, entries))
            pm = m.grab()
            if pm.width() > 10 and pm.height() > 10:
                save_png(pm, '99_menu_%s.png' % title.lower(), 'Menu bar > %s menu' % title, 'Menu popped up offscreen')
                shown += 1
            m.hide()
            settle(app)
        MENUS.extend(lines)
    menus()


MENUS = []


# ---- synthetic data: MCA / XFNTR ----------------------------------------

def run_xfntr(app, ctx):
    import synth
    tmp = fixed_tmp('lss_screens_xf_')
    spec, truth = synth.make_xfntr_dataset(os.path.join(tmp, 'xf'))
    w = new_window(app, spec)

    @step('mca')
    def mca():
        select_scans(w, app, None)
        select_frames(w, app, [4])
        tab(w, app, 'MCA')
        save_png(grab_window(w, app), '70_mca_one_spectrum.png', 'MCA tab, whole window, one spectrum',
                 'Synthetic XFNTR data (9 getandsave_mca scans, Qz 0.012-0.036); frame 5 selected')
        select_frames(w, app, None)
        img = grab_window(w, app)
        save_png(crop(img, rect_in(w, w.ui.PlotWidget)), '71_mca_all_spectra.png', 'MCA tab with all spectra selected',
                 'Synthetic XFNTR; all 9 spectra selected')
        w.ui.mcaRanLineEdit.setText('5.6:7.2')
        w.ui.mcaSumAllPushButton.click()
        settle(app)
        save_png(grab_window(w, app), '72_mca_sum_all_integral.png', 'MCA tab after Sum All over the fluorescence window (integral vs Qz)',
                 'Synthetic XFNTR; window 5.6:7.2 keV; Sum All; whole window')
        w.ui.mcaXAxisComboBox.setCurrentIndex(1)
        settle(app)
        save_png(crop(grab_window(w, app), rect_in(w, w.ui.PlotWidget)), '72b_mca_integral_vs_qz.png', 'MCA tab, integral vs Qz',
                 'As before; x axis set to Qz')
        select_frames(w, app, [4])
        before = visible_tops(app)
        arm(ctx, '73_mca_peak_fit_dialog.png', 'MCA > Fit peak-fit window', 'Synthetic XFNTR; frame 5; Fit clicked')
        w.ui.mcaFitPushButton.click()
        settle(app)
        disarm(ctx)
        d = grab_toplevels(app, before, '73_mca_peak_fit_dialog.png', 'MCA > Fit window (peak fit of one spectrum)',
                           'Synthetic XFNTR; frame 5; Fit clicked', skip=[w])
        try:
            pf = w.uipeakfit
            pf.rangeLineEdit.setText('5.6:7.2')
            for j, v in enumerate((6.3, 1e-2, 0.1)):
                pf.peakTW.item(0, j).setText(str(v))
            settle(app)
            pf.fitPushButton.click()
            settle(app)
            save_png(pf.grab(), '74_mca_peak_fit_dialog_fitted.png', 'MCA peak-fit window after Fit', 'Range 5.6:7.2, guess 6.3 keV')
            pf.close()
        except Exception as e:
            PROBLEMS.append(('mca peak fit', 'tool step failed', str(e)))
        settle(app)
        select_frames(w, app, None)
        before = visible_tops(app)
        w.mcaFitLinesPushButton.click()
        settle(app, 6)
        save_png(grab_window(w, app), '75_mca_fit_lines_result.png', 'MCA tab after Fit lines (fluorescence result)',
                 'Synthetic XFNTR; all spectra; Fit lines clicked')
        grab_toplevels(app, before, '75b_mca_fit_lines_other_window.png', 'Window opened by Fit lines', 'Synthetic XFNTR', skip=[w])
        before = visible_tops(app)
        w.mcaFitOptionsPushButton.click()
        settle(app)
        grab_toplevels(app, before, '76_mca_fit_options_dialog.png', 'MCA Fit options... dialog', 'Synthetic XFNTR', skip=[w])
        if getattr(w, 'mcaFitDialog', None) is not None:
            w.mcaFitDialog.close()
        arm(ctx, '77_mca_merge_dialog.png', 'MCA > Merge dialog (merge window)', 'Synthetic XFNTR; after Sum All')
        w.ui.mcaMergePushButton.click()
        disarm(ctx)
        before = visible_tops(app)
        try:
            if w.uimcamerge.isVisible():
                save_png(w.uimcamerge.grab(), '77_mca_merge_dialog.png', 'MCA > Merge dialog (merge window)', 'Synthetic XFNTR; after Sum All')
                w.uimcamerge.close()
        except Exception:
            pass
    mca()
    free(w, app)

    # absorber ratio dialog needs a scan of the 'Absorber' variable; use the absorber patch dataset if it has one
    @step('absorber ratio')
    def absr():
        w2 = new_window(app, synth.make_absorber_patch_dataset(os.path.join(tmp, 'abs')))
        sc = w2.ui.scanListWidget
        found = None
        for i in range(sc.count()):
            select_scans(w2, app, [i])
            if w2.specData[w2.selectedScanNums[0]]['ScanVar'][0] == 'Absorber':
                found = i
        if found is not None:
            tab(w2, app, 'SpecPlot')
            arm(ctx, '93b_dialog_absorber_ratio.png', 'Calculations > Abs ratio window', 'Synthetic absorber scan')
            w2.ui.actionAbs_ratio.trigger()
            disarm(ctx)
        else:
            PROBLEMS.append(('absorber ratio', 'not captured', 'no scan with an Absorber scan variable in the synthetic data'))
        free(w2, app)
    absr()


def run_burn_ref(app, ctx):
    import synth
    tmp = fixed_tmp('lss_screens_burn_')

    @step('reflectivity burn')
    def b():
        spec = synth.make_burn_dataset(os.path.join(tmp, 'burn'))
        w = new_window(app, spec)
        select_scans(w, app, [0])
        select_frames(w, app, None)
        tab(w, app, 'Pilatus')
        save_png(grab_window(w, app), '53_burn_ref_series_selected.png', 'Pilatus tab, a synthetic burn series (21 frames, one spot) selected',
                 'Synthetic burn dataset (reflected intensity decaying, tau 400 s); all frames')
        w.ui.pilBurnPushButton.click()
        settle(app, 6)
        d = w.uipdburn
        save_png(d.grab(), '54_burn_ref_trends_view.png', 'Burn-test window, Trends tab, reflectivity burn (synthetic)',
                 'Synthetic burn dataset; Pilatus > Burn Test')
        d.refPushButton.click()
        settle(app)
        save_png(d.grab(), '55_burn_ref_legacy_view.png', 'Burn-test window, legacy tab after the Reflectivity button (synthetic)',
                 'Synthetic burn dataset; legacy REF burn analysis')
        d.close()
        free(w, app)
    b()


def run_plot_tabs(app, ctx, plot_files):
    import numpy as np
    import synth
    tmp = fixed_tmp('lss_screens_plot_')
    w = new_window(app, NX)

    @step('plot tab')
    def p():
        files = list(plot_files)
        # a few synthetic files: a decaying curve and a peak with errors
        x = np.linspace(0, 1, 60)
        f2 = os.path.join(tmp, 'peak_example.txt')
        np.savetxt(f2, np.column_stack([x, 100 * np.exp(-((x - .5) / .08) ** 2) + 5, np.sqrt(100 * np.exp(-((x - .5) / .08) ** 2) + 5)]))
        files.append(f2)
        ctx['files']['many'][:] = files
        tab(w, app, 'Plot')
        w.ui.plotAddFilePushButton.click()
        settle(app)
        lw = w.ui.plotFileListWidget
        for i in range(lw.count()):
            lw.item(i).setSelected(True)
        lw.itemSelectionChanged.emit()
        settle(app)
        save_png(grab_window(w, app), '80b_plot_two_files.png', 'Plot tab, whole window, two files from disk plotted',
                 'Files: a patched NX reflectivity export (if available) and a synthetic peak (Qz, I, error)')
        lw.blockSignals(True)
        lw.clearSelection()
        lw.item(lw.count() - 1).setSelected(True)
        lw.blockSignals(False)
        lw.itemSelectionChanged.emit()
        settle(app)
        before = visible_tops(app)
        arm(ctx, '81_plot_peak_fit_window.png', 'Plot > Peak Fit window', 'Plot tab with the synthetic peak file selected')
        w.ui.plotPFPushButton.click()
        settle(app)
        disarm(ctx)
        grab_toplevels(app, before, '81_plot_peak_fit_window.png', 'Plot > Peak Fit window', 'Plot tab; files plotted', skip=[w])
        try:
            pf = w.uipeakfit
            pf.fitPushButton.click()
            settle(app)
            save_png(pf.grab(), '81b_plot_peak_fit_window_fitted.png', 'Plot > Peak Fit window after Fit', 'Default start values')
            pf.close()
        except Exception as e:
            PROBLEMS.append(('plot peak fit', 'tool step failed', str(e)))
        w.ui.graPushButton.click()
        settle(app)
        save_png(crop(grab_window(w, app), rect_in(w, w.ui.PlotWidget)), '81c_plot_gradient.png', 'Plot tab after Gradient', 'As above; Gradient clicked')
        before = visible_tops(app)
        arm(ctx, '81d_plot_scale_window.png', 'Plot scale window', 'Plot tab')
        try:
            w.setPlotScale()
        except Exception:
            for n in dir(w):
                pass
        disarm(ctx)
        grab_toplevels(app, before, '81d_plot_scale_window.png', 'Plot scale window', 'Plot tab', skip=[w])
        for t in list(visible_tops(app)):
            if t is not w:
                t.close()
        # 2D plot: a 3-column x y z file
        xx, yy = np.meshgrid(np.linspace(0, 1, 30), np.linspace(0, 1, 30))
        zz = np.exp(-(((xx - .4) / .15) ** 2 + ((yy - .6) / .1) ** 2))
        f3 = os.path.join(tmp, 'map_example.txt')
        np.savetxt(f3, np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()]))
        ctx['files']['many'][:] = [f3]
        tab(w, app, '2D_Plot')
        w.ui.twodPlotAddFilePushButton.click()
        settle(app)
        lw = w.ui.twodPlotFileListWidget
        for i in range(lw.count()):
            lw.item(i).setSelected(True)
        lw.itemSelectionChanged.emit()
        settle(app)
        save_png(grab_window(w, app), '83_2dplot_map_file.png', '2D_Plot tab, whole window, a synthetic x y z map plotted',
                 'Synthetic 30x30 Gaussian map file added with Add Files')
    p()
    free(w, app)


def write_readme(out, wall):
    path = os.path.join(out, 'README.md')
    keep = ''
    committed = os.path.join(ROOT, 'docs', 'gui', 'screens', 'README.md')
    for src in (path, committed):        # a run into a new folder (the Tools audit) keeps the committed section
        if os.path.exists(src):
            m = re.search(r'^## Observations.*', open(src, encoding='utf-8').read(), re.S | re.M)
            if m:
                keep = m.group(0)
                break
    total = sum(os.path.getsize(f) for f in glob.glob(os.path.join(out, '*.png')))
    lines = ['# Screenshots of the reader window (GUI overhaul, phase 1a)', '',
             'Made by `python tests/tools/gui_screens.py` (offscreen Qt, scale 1; the window cannot be narrower than about',
             '2266 px, so whole-window shots are 2300 px wide). Data: the public NX school set (`sample_data/NX_school/2026sep/20260923`)',
             'and synthetic data from `tests/synth.py` for MCA / fluorescence, the reflectivity burn and the absorber scan',
             '(NX has no MCA data). Regenerate the whole folder with the command above; the table is rewritten, the',
             'Observations section is by hand and is kept.', '',
             '%d images, %.1f MB, last run took %.0f s.' % (len(ENTRIES), total / 1e6, wall), '',
             '| File | What it shows | Data and state |', '|---|---|---|']
    for f, s, st in sorted(ENTRIES):
        lines.append('| `%s` | %s | %s |' % (f, s.replace('|', '/'), st.replace('|', '/')))
    lines += ['', '### Menus (item lists, from the actions of each menu)', '']
    for t, es in MENUS:
        lines.append('- **%s**: %s' % (t, ', '.join(e if e else '-' for e in es) or '(empty)'))
    lines.append('')
    lines.append(keep or '## Observations\n\n(to be written)\n')
    open(path, 'w', encoding='utf-8').write('\n'.join(lines))


def main():
    global OUT
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=os.path.join(ROOT, 'docs', 'gui', 'screens'))
    ap.add_argument('--skip-slow', action='store_true', help='skip Ref Patch, GID patch, cuts and burn on the real data')
    a = ap.parse_args()
    OUT = os.path.abspath(a.out)
    os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, '*.png')):
        os.remove(f)
    from PyQt5 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(['lss-screens'])
    app.setCursorFlashTime(0)                    # no blinking text cursor: the same pictures from run to run
    ctx = install_patches(app)
    ctx['plot_files'] = []
    w = run_nx(app, ctx, a.skip_slow)
    run_dialogs_on(w, app, ctx)
    free(w, app)
    run_xfntr(app, ctx)
    run_burn_ref(app, ctx)
    run_plot_tabs(app, ctx, ctx.get('plot_files', []))
    wall = time.time() - T0
    write_readme(OUT, wall)
    print('\n==== messages, exceptions and tool problems (action: kind: text) ====')
    for act, kind, text in PROBLEMS:
        print('%s: %s: %s' % (act, kind, text[:300]))
    print('==== %d images, %.1f MB, %.0f s ====' % (len(ENTRIES),
          sum(os.path.getsize(f) for f in glob.glob(os.path.join(OUT, '*.png'))) / 1e6, wall))


if __name__ == '__main__':
    main()
