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


def _visible_dialogs(w):
    return [d for d in w.findChildren(QtWidgets.QDialog) if d.isVisible()]


def _close_dialogs(w):
    for d in QtWidgets.QApplication.topLevelWidgets():
        if isinstance(d, QtWidgets.QDialog) and d.isVisible():
            d.close()


def _first(recorder):
    t, v, tb = recorder.exceptions[0]
    return '%s @ %s' % (t.__name__, _where(tb))


class _Driver:
    """Keeps a window in a given state, rebuilding it when the state breaks."""

    def __init__(self, make_window, app, recorder, spec, state):
        self.make_window, self.app, self.recorder = make_window, app, recorder
        self.spec, self.setup = spec, STATES[state]
        self.w = make_window()
        self.broken = None

    def reset(self):
        """Re-apply the state; True when the window is ready for a control."""
        rec = self.recorder
        _close_dialogs(self.w)
        rec.exceptions.clear()
        try:
            self.setup(self.w, self.app, self.spec)
            ok = not rec.exceptions
        except Exception:
            ok = False
        if not ok:
            rec.exceptions.clear()
            self.w.close()
            self.w = self.make_window()
            try:
                self.setup(self.w, self.app, self.spec)
            except Exception as exc:
                self.broken = '%s @ setup' % type(exc).__name__
                return False
            if rec.exceptions:
                self.broken = _first(rec)
                return False
        rec.exceptions.clear()
        return True

    def trigger(self, fn):
        """Run one control; return 'Type @ where' or None."""
        try:
            fn()
            self.app.processEvents()
        except Exception as exc:           # raised outside a slot
            return '%s @ direct' % type(exc).__name__
        if self.recorder.exceptions:
            return _first(self.recorder)
        return None


def run_state(make_window, app, recorder, spec, state):
    """Trigger every control once in ``state``; return {key: 'Type @ where'}.

    The state is re-applied before each control. When a control opens a
    dialog, every control of that dialog is triggered too (one level deep),
    reopening the dialog each time; those keys read 'parent > child'.
    """
    drv = _Driver(make_window, app, recorder, spec, state)
    failures = {}
    for key in list(controls(drv.w)):
        if not drv.reset():
            failures['<setup>'] = drv.broken
            break
        fn = controls(drv.w).get(key)
        if fn is None:
            continue
        err = drv.trigger(fn)
        if err:
            failures[key] = err
            continue
        dialogs = _visible_dialogs(drv.w)
        if not dialogs:
            continue
        child_keys = list(controls(dialogs[-1]))
        for ck in child_keys:
            if not drv.reset():
                break
            parent = controls(drv.w).get(key)
            if parent is None or drv.trigger(parent):
                break
            dialogs = _visible_dialogs(drv.w)
            if not dialogs:
                break
            child = controls(dialogs[-1]).get(ck)
            if child is None:
                continue
            recorder.exceptions.clear()
            err = drv.trigger(child)
            if err:
                failures['%s > %s' % (key, ck)] = err
    _close_dialogs(drv.w)
    drv.w.close()
    return failures


def run_walk(make_window, app, recorder, spec, state, seed, steps):
    """Random sequence of ``steps`` controls starting from ``state``.

    Nothing is reset between steps. Returns the list of
    (step, key, 'Type @ where') for the steps that raised.
    """
    import random
    rng = random.Random(seed)
    w = make_window()
    recorder.exceptions.clear()
    STATES[state](w, app, spec)
    recorder.exceptions.clear()
    raised = []
    for step in range(steps):
        pool = dict(controls(w))
        for d in _visible_dialogs(w):
            pool.update(('dlg:' + k, f) for k, f in controls(d).items())
        # list selections are part of "whichever files are selected"
        for name in ('scanListWidget', 'imageListWidget'):
            lw = getattr(w.ui, name)
            if lw.count():
                pool['select:' + name] = (
                    lambda lw=lw: _select_rows(
                        lw, app, sorted(rng.sample(
                            range(lw.count()),
                            rng.randint(1, min(3, lw.count()))))))
        key = rng.choice(sorted(pool))
        recorder.exceptions.clear()
        try:
            pool[key]()
            app.processEvents()
        except Exception as exc:
            raised.append((step, key, '%s @ direct' % type(exc).__name__))
            continue
        if recorder.exceptions:
            raised.append((step, key, _first(recorder)))
    recorder.exceptions.clear()
    _close_dialogs(w)
    w.close()
    return raised
