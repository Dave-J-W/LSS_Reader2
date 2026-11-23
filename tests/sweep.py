"""Drive every control of the main window in a given application state.

Used by test_gui_sweep.py to keep an inventory of the controls that raise.
The goal of the project is an empty inventory.
"""
import os
import time
import traceback

from PyQt5 import QtWidgets

# 'actiontool_': the Tools menu's per-item actions (lss_toolbox) all open the
# same window at another page, and the pages are tested on their own
# (test_toolbox_gui.py); 'All tools…' (actionToolsWindow) stays in the sweep.
SKIP_ACTION_WORDS = ('quit', 'exit', 'close', 'actiontool_')


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
        parent = w.directory if os.path.isdir(w.directory or '') else None   # the test's tmp_path
        if parent and 'sample_data' in os.path.abspath(parent).split(os.sep):
            parent = None                                  # never write beside the sample data (AGENTS.md rule 7)
        w.openSpecFile(fname=spec)
        # an output folder of its own (2026-11-22): every reduction is saved into the workbook there,
        # and a folder shared by the hundreds of windows of one sweep test grew one workbook that each
        # new window had to open again (the sweep slowed down and its memory grew to gigabytes).
        # Inside the test's tmp_path (2026-11-23), so that pytest removes it with the test's folder;
        # before, hundreds of them stayed in the system's temporary folder after every sweep.
        import tempfile
        w.directory = tempfile.mkdtemp(prefix='lss-sweep-out-', dir=parent)
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


def _budget(w, app):
    w.errorModeComboBox.setCurrentIndex(1)     # the Errors pane: budget model
    w.setErrorModel()
    app.processEvents()


def state_pilatus_two_scans_budget(w, app, spec):
    state_spec_loaded(w, app, spec)
    _budget(w, app)
    _select_scans(w, app, [0, 1])
    _select_images(w, app)


def state_mca_frames_budget(w, app, spec):
    state_spec_loaded(w, app, spec)
    _budget(w, app)
    _select_scans(w, app, [2])
    _select_images(w, app)


STATES = {f.__name__[6:]: f for f in (
    state_empty, state_spec_loaded, state_motor_scan,
    state_pilatus_scan_no_frames, state_pilatus_one_frame,
    state_pilatus_two_scans_all_frames, state_mca_frames,
    state_pilatus_two_scans_budget, state_mca_frames_budget)}


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
            if b.menu() is not None:
                # a button with a popup menu (the ngui prototype's provenance
                # strip): click() runs the menu's own event loop, which nothing
                # closes offscreen, so the walk hung (found 2026-11-23). The key
                # stays (a no-op), so that random walks draw what they drew
                # before; the menu's actions are QActions, triggered as such
                out['click:' + name] = lambda: None
                continue
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


def dispose(w, app, recorder=None):
    """Close a window and really free it.

    Hundreds of windows are created in a sweep. Each holds images and
    several matplotlib canvases, and stays alive while anything refers to
    it: recorded dialogs, tracebacks of recorded exceptions, Qt's deferred
    deletion queue, reference cycles.
    """
    import gc
    from PyQt5 import QtCore
    _close_dialogs(w)
    if recorder is not None:
        recorder.dialogs.clear()
        recorder.exceptions.clear()
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    app.processEvents()
    del w
    gc.collect()


class _Driver:
    """Gives every control a fresh window in the requested state.

    Reusing one window would let settings changed by one control (a checked
    box, the selected beamline) leak into the result for the next.
    """

    def __init__(self, make_window, app, recorder, spec, state):
        self.make_window, self.app, self.recorder = make_window, app, recorder
        self.spec, self.setup = spec, STATES[state]
        self.w = None
        self.broken = None

    def close(self):
        if self.w is not None:
            dispose(self.w, self.app, self.recorder)
            self.w = None

    def reset(self):
        """New window in the state; True when it is ready for a control."""
        rec = self.recorder
        self.close()
        self.w = self.make_window()
        rec.exceptions.clear()
        try:
            self.setup(self.w, self.app, self.spec)
        except Exception as exc:
            self.broken = '%s @ setup' % type(exc).__name__
            return False
        if rec.exceptions:
            self.broken = _first(rec)
            return False
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


def _log_time(state, key, t0):
    """Append 'state<TAB>key<TAB>seconds' to $LSS_SWEEP_TIMES, if set.

    A diagnostic for a slow sweep: sort the file by its last column.
    """
    path = os.environ.get('LSS_SWEEP_TIMES')
    if path:
        name = getattr(state, '__name__', str(state))
        with open(path, 'a') as f:
            f.write('%s\t%s\t%.3f\n' % (name, key, time.perf_counter() - t0))


def control_keys(make_window, app, recorder, part=None):
    """The window's control keys (a fresh window's ``controls``), or only
    part ``i`` of ``n`` (every n-th from the i-th) when ``part`` = (i, n)."""
    probe = make_window()
    keys = list(controls(probe))
    dispose(probe, app, recorder)
    return keys if part is None else keys[part[0]::part[1]]


def run_state(make_window, app, recorder, spec, state, part=None):
    """Trigger every control once in ``state``; return {key: 'Type @ where'}.

    Every control gets a fresh window in that state. When a control opens a
    dialog, every control of that dialog is triggered too (one level deep),
    reopening the dialog each time; those keys read 'parent > child'.
    ``part`` = (i, n): only the controls ``control_keys`` gives for that
    part, and their dialogs' (the sweep's tests share a state this way).
    """
    drv = _Driver(make_window, app, recorder, spec, state)
    failures = {}
    keys = control_keys(make_window, app, recorder, part)
    for key in keys:
        if not drv.reset():
            failures['<setup>'] = drv.broken
            break
        fn = controls(drv.w).get(key)
        if fn is None:
            continue
        t0 = time.perf_counter()
        err = drv.trigger(fn)
        _log_time(state, key, t0)
        del fn
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
            t0 = time.perf_counter()
            err = drv.trigger(child)
            _log_time(state, '%s > %s' % (key, ck), t0)
            if err:
                failures['%s > %s' % (key, ck)] = err
    drv.close()
    return failures


def run_walk(make_window, app, recorder, spec, state, seed, steps):
    """Random sequence of ``steps`` controls starting from ``state``.

    Nothing is reset between steps. Returns the list of
    (step, key, 'Type @ where', end of traceback) for the steps that raised.
    """
    import random
    rng = random.Random(seed)
    w = make_window()
    recorder.exceptions.clear()
    STATES[state](w, app, spec)
    recorder.exceptions.clear()
    raised = []
    for step in range(steps):
        # the Tools menu's actions (lss_toolbox) open a separate window and are
        # covered by the per-state sweep and test_toolbox_gui.py; leaving them
        # out keeps each seed's walk what it was before the menu (2026-11-23)
        pool = {k: f for k, f in controls(w).items() if not k.startswith('action:actionTool')}
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
            raised.append((step, key, '%s @ direct' % type(exc).__name__, ''))
            continue
        if recorder.exceptions:
            t, v, tb = recorder.exceptions[0]
            raised.append((step, key, _first(recorder),
                           ''.join(traceback.format_exception(t, v, tb)[-4:])))
    dispose(w, app, recorder)
    return raised


# ---- walks inside dialogs ---------------------------------------------------

TEXT_BANK = ('', '0', '1', '-1', '0,-1', '-1,0', '2,3', '99', '-99', 'abc',
             '1:2', '0:0.2', '1.40:1.52', '5', '-0.5', '0.5', '1e9', ',', '0,0')


def dialog_controls(dialog, rng):
    """Every control of an open dialog as {key: callable}; line edits get a
    text from TEXT_BANK and Enter, combo boxes a random entry."""
    out = {}
    for b in dialog.findChildren(QtWidgets.QAbstractButton):
        name = b.objectName()
        if not name or name.startswith('qt_') or not b.isEnabled():
            continue
        if isinstance(b, (QtWidgets.QCheckBox, QtWidgets.QRadioButton)):
            out['toggle:' + name] = b.toggle
        else:
            out['click:' + name] = b.click
    for c in dialog.findChildren(QtWidgets.QComboBox):
        if c.objectName() and c.count():
            def pick(c=c):
                i = rng.randrange(c.count())
                c.setCurrentIndex(i)
                c.activated.emit(i)
            out['combo:' + c.objectName()] = pick
    for e in dialog.findChildren(QtWidgets.QLineEdit):
        if e.objectName() and not e.objectName().startswith('qt_') and not e.isReadOnly():
            def type_(e=e):
                e.setText(rng.choice(TEXT_BANK))
                e.returnPressed.emit()
                e.editingFinished.emit()
            out['type:' + e.objectName()] = type_
    for bb in dialog.findChildren(QtWidgets.QDialogButtonBox):
        for b in bb.buttons():
            out['box:' + b.text()] = b.click
    return out


def run_dialog_walk(w, app, recorder, open_dialog, seed, steps, reopen=True):
    """Open a dialog with ``open_dialog()`` and apply ``steps`` random actions
    to whatever dialogs are open (including dialogs opened by dialogs).
    When all dialogs have closed, ``open_dialog`` is called again if
    ``reopen``. Returns [(step, key, 'Type @ where', traceback tail)]."""
    import random
    rng = random.Random(seed)
    raised = []

    def record(step, key):
        if recorder.exceptions:
            t, v, tb = recorder.exceptions[0]
            raised.append((step, key, _first(recorder),
                           ''.join(traceback.format_exception(t, v, tb)[-4:])))
            recorder.exceptions.clear()

    recorder.exceptions.clear()
    open_dialog()
    app.processEvents()
    record(-1, 'open')
    for step in range(steps):
        dialogs = [d for d in QtWidgets.QApplication.topLevelWidgets()
                   if isinstance(d, QtWidgets.QDialog) and d.isVisible()]
        pool = {}
        for d in dialogs:
            pool.update(('%s/%s' % (d.objectName() or 'dialog', k), f)
                        for k, f in dialog_controls(d, rng).items())
        if not pool:
            if not reopen:
                break
            open_dialog()
            app.processEvents()
            record(step, 'reopen')
            continue
        key = rng.choice(sorted(pool))
        try:
            pool[key]()
            app.processEvents()
        except Exception as exc:
            raised.append((step, key, '%s @ direct' % type(exc).__name__, ''))
            continue
        record(step, key)
    _close_dialogs(w)
    return raised
