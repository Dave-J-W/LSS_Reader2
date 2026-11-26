"""Screenshots of the ngui prototype window (F82; docs/gui/prototype.md), with an index.

    python tests/tools/ngui_screens.py [--out docs/gui/prototype/screens]

Makes the whole window at 1440 x 900 on each tab, the Frames tab's Line cuts
sub-tab, its Split view and its panes, a fit plot with the residuals panel,
the sketch dialogs (Retired controls, File > Export..., a Legacy... window,
Preferences), and one close-up per tab of its left column with every group
open; rewrites README.md beside them. No data are read (the window holds
only placeholders); runs offscreen from anywhere. Images are quantised to
256 colours as in tests/tools/gui_screens.py.
"""
import argparse
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('MPLBACKEND', 'Agg')
os.environ['LSS_READER_LOG_DIR'] = tempfile.mkdtemp(prefix='ngui_screens_logs_')
os.environ['LSS_READER_LOCK_AT_OPEN'] = '0'      # D1: no workbook lock beside the sample data (rule 7)
os.environ['LSS_READER_PREFS'] = os.path.join(tempfile.mkdtemp(prefix='ngui_screens_prefs_'), 'p.json')

ENTRIES = []


def save_png(img, out, name, shows):
    from PIL import Image
    from PyQt5 import QtGui
    if isinstance(img, QtGui.QPixmap):
        img = img.toImage()
    img = img.convertToFormat(QtGui.QImage.Format_RGBA8888)
    ptr = img.constBits()
    ptr.setsize(img.byteCount())
    pil = Image.frombuffer('RGBA', (img.width(), img.height()), bytes(ptr), 'raw', 'RGBA', img.bytesPerLine(), 1)
    pil = pil.convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pil.save(os.path.join(out, name), optimize=True)
    ENTRIES.append((name, shows, '%d × %d' % (pil.width, pil.height)))
    print('saved %s (%dx%d)' % (name, pil.width, pil.height), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'docs', 'gui', 'prototype', 'screens'))
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    from PyQt5.QtWidgets import QApplication, QWidget
    app = QApplication.instance() or QApplication(['ngui-screens'])
    from ngui import layout as L
    from ngui.window import NguiWindow

    def settle():
        for _ in range(3):
            app.processEvents()

    w = NguiWindow()
    w.show()
    settle()
    out = args.out

    for k, tab in enumerate(L.TABS):
        w.tabs.setCurrentIndex(k)
        settle()
        save_png(w.grab(), out, '%02d_%s.png' % (k + 1, tab['key']),
                 'Whole window on the %s tab (was: %s); folded groups closed, panes hidden' % (tab['title'], tab['was']))

    w.tabs.setCurrentIndex(1)
    w.framesSubTabs.setCurrentIndex(1)
    settle()
    save_png(w.grab(), out, '02b_frames_line_cuts.png', 'Frames: the Line cuts sub-tab (cut toolbar, cut plot with '
                                                         'its provenance strip and Save…, display options)')
    w.framesSubTabs.setCurrentIndex(0)
    w.framesSplitToggle.setChecked(True)
    settle()
    save_png(w.grab(), out, '02c_frames_split.png', 'Frames: Split on, Raw frames and Line cuts side by side')
    w.framesSplitToggle.setChecked(False)
    w.resize(1440, 900)
    for d in w.panes.values():
        d.show()
    w.panes['Errors'].raise_()
    from PyQt5.QtCore import Qt
    w.resizeDocks([w.panes['Errors']], [200], Qt.Vertical)
    settle()
    save_png(w.grab(), out, '02d_frames_with_panes.png', 'Frames with the panes shown (View menu): Messages, Script '
                                                          'and Errors tabbed under the tab area only; the selection '
                                                          'panel keeps the full height')
    for d in w.panes.values():
        d.hide()
    w.tabs.setCurrentIndex(3)
    w.controls_toggle = w.findChild(QWidget, 'ngui_refRefDataPlotwidget_residualsToggle')
    w.controls_toggle.setChecked(True)
    settle()
    save_png(w.grab(), out, '04b_reflectivity_residuals.png', 'Reflectivity with the residuals panel shown above '
                                                               'the fit plot (F74; hidden by default)')
    w.controls_toggle.setChecked(False)

    for key, name, shows in (('retired', '08_retired_controls.png', 'Help > Retired controls: what the layout drops, '
                                                                    'with the reasons'),
                             ('export', '09_file_export.png', 'File > Export…: the only route to exporting (D61)'),
                             ('legacy_reflectivity', '10_legacy_reflectivity.png',
                              'Reflectivity > Check frames…: the point-by-point path behind one button (question 13)'),
                             ('preferences', '11_preferences.png', 'File > Preferences…: what stays in the dialog')):
        if key == 'retired':
            d = w.show_retired()
        elif key == 'export':
            d = w.show_export()
        elif key == 'preferences':
            d = w.show_preferences()
        else:
            d = w.show_legacy('reflectivity')
        settle()
        save_png(d.grab(), out, name, shows)
        d.hide()

    w.expand_all(True)
    settle()
    for k, tab in enumerate(L.TABS):
        w.tabs.setCurrentIndex(k)
        settle()
        col = w.findChild(QWidget, 'ngui_%s_leftColumn' % tab['key'])
        h = max(col.sizeHint().height(), col.height())
        col.resize(col.width(), h)
        settle()
        save_png(col.grab(), out, '2%d_left_%s.png' % (k + 1, tab['key']),
                 'Close-up: the %s tab\'s left column, every group open' % tab['title'])
    w.expand_all(False)
    dock = w.findChild(QWidget, 'ngui_selectionPanel')
    save_png(dock.grab(), out, '20_left_selection_panel.png', 'Close-up: the selection panel (series, scans, frames '
                                                              'with the display mode, background frames folded)')

    with open(os.path.join(out, 'README.md'), 'w', encoding='utf-8') as f:
        f.write('# Screenshots of the ngui prototype\n\n'
                'Made by `python tests/tools/ngui_screens.py` (do not edit by hand). The window is a non-functional '
                'sketch of the proposed layout (`docs/gui/prototype.md`); hover a control in the real window to see '
                'where it lives today. Open it with File > Preferences > Layout > "ngui (new layout, prototype)".\n\n'
                '| File | Shows | Size |\n|---|---|---|\n')
        for name, shows, size in sorted(ENTRIES):
            f.write('| [`%s`](%s) | %s | %s |\n' % (name, name, shows, size))
    w.close()
    w.deleteLater()
    settle()
    return 0


if __name__ == '__main__':
    sys.exit(main())
