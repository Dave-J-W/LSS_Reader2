"""Drive every control of the main window in a given application state.

Used by test_gui_sweep.py to keep an inventory of the controls that raise.
The goal of the project is an empty inventory.
"""
import traceback

from PyQt5 import QtWidgets

SKIP_ACTION_WORDS = ('quit', 'exit', 'close')


# ---- application states -------------------------------------------------

def _select_rows(lw, app, rows):
    """Select ``rows`` (None = all) as one user action: one selection signal.

    Selecting items one by one would fire the handler once per item, and the
    image handler re-reads every selected frame each time.
    """
    lw.blockSignals(True)
    lw.clearSelection()
    for r in (range(lw.count()) if rows is None else rows):
        lw.item(r).setSelected(True)
    lw.blockSignals(False)
    lw.itemSelectionChanged.emit()
    app.processEvents()


def _select_scans(w, app, rows):
    _select_rows(w.ui.scanListWidget, app, rows)


def _select_images(w, app, rows=None):
    _select_rows(w.ui.imageListWidget, app, rows)


def state_empty(w, app, spec):
    pass


def state_spec_loaded(w, app, spec):
    if w.specFileName != spec:
        w.openSpecFile(fname=spec)
    w.ui.scanListWidget.clearSelection()
    app.processEvents()


def state_motor_scan(w, app, spec):
    state_spec_loaded(w, app, spec)
    _select_scans(w, app, [3])


def state_pilatus_scan_no_frames(w, app, spec):
    state_spec_loaded(w, app, spec)
    _select_scans(w, app, [0])


def state_pilatus_one_frame(w, app, spec):
    state_spec_loaded(w, app, spec)
    _select_scans(w, app, [0])
    _select_images(w, app, [0])


def state_pilatus_two_scans_all_frames(w, app, spec):
    state_spec_loaded(w, app, spec)
    _select_scans(w, app, [0, 1])
    _select_images(w, app)


def state_mca_frames(w, app, spec):
    state_spec_loaded(w, app, spec)
    _select_scans(w, app, [2])
    _select_images(w, app)


STATES = {f.__name__[6:]: f for f in (
    state_empty, state_spec_loaded, state_motor_scan,
    state_pilatus_scan_no_frames, state_pilatus_one_frame,
    state_pilatus_two_scans_all_frames, state_mca_frames)}


# ---- controls -----------------------------------------------------------

def controls(w):
    """(key, callable) for every named control of the main window, sorted."""
    out = {}
    for b in w.findChildren(QtWidgets.QAbstractButton):
        name = b.objectName()
        if not name or name.startswith('qt_'):
            continue
        if isinstance(b, (QtWidgets.QCheckBox, QtWidgets.QRadioButton)):
            out['toggle:' + name] = b.toggle
        elif isinstance(b, QtWidgets.QPushButton):
            out['click:' + name] = b.click
    for a in w.findChildren(QtWidgets.QAction):
        name = a.objectName()
        if not name or any(s in name.lower() or s in a.text().lower()
                           for s in SKIP_ACTION_WORDS):
            continue
        out['action:' + name] = a.trigger
    for c in w.findChildren(QtWidgets.QComboBox):
        name = c.objectName()
        if name and c.count():
            out['combo:' + name] = (
                lambda c=c: c.setCurrentIndex((c.currentIndex() + 1) % c.count()))
    for e in w.findChildren(QtWidgets.QLineEdit):
        name = e.objectName()
        if name and not name.startswith('qt_'):
            out['enter:' + name] = (
                lambda e=e: (e.returnPressed.emit(), e.editingFinished.emit()))
    for s in w.findChildren(QtWidgets.QAbstractSpinBox):
        name = s.objectName()
        if name:
            out['step:' + name] = s.stepUp
    return dict(sorted(out.items()))


def _where(tb):
    """'file:function' of the innermost frame inside this repository."""
    frames = [f for f in traceback.extract_tb(tb)
              if 'site-packages' not in f.filename]
    f = (frames or traceback.extract_tb(tb))[-1]
    return '%s:%s' % (f.filename.replace('\\', '/').split('/')[-1], f.name)


def run_state(make_window, app, recorder, spec, state):
    """Trigger every control once in ``state``; return {key: 'Type @ where'}.

    The state is re-applied before each control. A fresh window is built when
    re-applying it fails, so one broken control cannot hide the others.
    """
    setup = STATES[state]
    failures = {}
    w = make_window()
    keys = list(controls(w))
    for key in keys:
        recorder.exceptions.clear()
        try:
            setup(w, app, spec)
            ok = not recorder.exceptions
        except Exception:
            ok = False
        if not ok:
            recorder.exceptions.clear()
            w.close()
            w = make_window()
            try:
                setup(w, app, spec)
            except Exception as exc:       # the state itself is broken
                failures['<setup>'] = '%s @ setup' % type(exc).__name__
                break
            if recorder.exceptions:
                t, v, tb = recorder.exceptions[0]
                failures['<setup>'] = '%s @ %s' % (t.__name__, _where(tb))
                break
        recorder.exceptions.clear()
        fn = controls(w).get(key)
        if fn is None:
            continue
        try:
            fn()
            app.processEvents()
        except Exception as exc:           # raised outside a slot
            failures[key] = '%s @ direct' % type(exc).__name__
            continue
        if recorder.exceptions:
            t, v, tb = recorder.exceptions[0]
            failures[key] = '%s @ %s' % (t.__name__, _where(tb))
        for d in QtWidgets.QApplication.topLevelWidgets():
            if isinstance(d, QtWidgets.QDialog) and d.isVisible():
                d.close()
    w.close()
    return failures
