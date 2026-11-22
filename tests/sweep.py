"""Drive every control of the main window in a given application state.

Used by test_gui_sweep.py to keep an inventory of the controls that raise.
The goal of the project is an empty inventory.
"""
import os
import time
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
        # an output folder of its own (2026-11-22): every reduction is saved into the workbook there,
        # and a folder shared by the hundreds of windows of one sweep test grew one workbook that each
        # new window had to open again (the sweep slowed down and its memory grew to gigabytes)
        import tempfile
        w.directory = tempfile.mkdtemp(prefix='lss-sweep-out-')
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


def fork_available():
    """True when controls run in forked copies of one state window.

    ``LSS_SWEEP_FORK=0`` turns it off (a fresh window is then built and put
    into the state for every control, as before 2026-11-22); there is no
    fork on Windows.
    """
    return hasattr(os, 'fork') and os.environ.get('LSS_SWEEP_FORK', '1') != '0'


def fingerprint(w):
    """What a control could see of the window and of its files.

    Every named control's value, the selected scans and images, the output
    folder (names and sizes) and the preferences file. Used to show that
    each forked copy starts exactly where a freshly built window starts.
    """
    import hashlib
    out = []
    for b in w.findChildren(QtWidgets.QAbstractButton):
        if b.objectName() and b.isCheckable():
            out.append(('check', b.objectName(), b.isChecked()))
    for c in w.findChildren(QtWidgets.QComboBox):
        if c.objectName():
            out.append(('combo', c.objectName(), c.currentIndex(), c.count()))
    for e in w.findChildren(QtWidgets.QLineEdit):
        if e.objectName() and not e.objectName().startswith('qt_'):
            out.append(('edit', e.objectName(), e.text()))
    for s in w.findChildren(QtWidgets.QAbstractSpinBox):
        if s.objectName():
            out.append(('spin', s.objectName(), s.text()))
    for name in ('scanListWidget', 'imageListWidget'):
        lw = getattr(w.ui, name)
        out.append((name, lw.count(), tuple(sorted(lw.row(i) for i in lw.selectedItems()))))
    d = getattr(w, 'directory', None)
    files = []
    if d and os.path.isdir(d):
        for root, _dirs, names in os.walk(d):
            for n in names:
                p = os.path.join(root, n)
                files.append((os.path.relpath(p, d), os.path.getsize(p)))
    out.append(('files', tuple(sorted(files))))
    from lss_core import preferences
    try:
        with open(preferences.path(), 'rb') as f:
            prefs = hashlib.sha256(f.read()).hexdigest()
    except OSError:
        prefs = None
    out.append(('prefs', prefs))
    return sorted(out, key=repr)


def _pool_threads():
    """Number of threads of Qt's thread pools in this process (Linux)."""
    n = 0
    try:
        for t in os.listdir('/proc/self/task'):
            with open('/proc/self/task/%s/comm' % t) as f:
                n += f.read().startswith('Thread (pooled)')
    except OSError:
        return 0
    return n


def _no_pool_threads(wait=40.0):
    """Wait until Qt's global thread pool has no threads left.

    Qt converts and scales large images on QThreadPool.globalInstance(). A
    forked child has none of its parent's threads, yet the pool would hand
    work to the idle ones it remembers and wait for it for ever. With an
    expiry time of 0 (set in run_state) its threads end as soon as they are
    idle (_ForkDriver sets it), so this only waits for those finishing.
    """
    import select
    end = time.monotonic() + wait
    while _pool_threads() and time.monotonic() < end:
        select.select([], [], [], 0.005)      # time.sleep is stubbed out by the recorder fixture


class _ForkDriver:
    """Builds the window in the state once; every control runs in a copy.

    The copy is a forked child process: it starts with the window exactly
    as it was after the state was set up (memory copied, nothing rebuilt),
    runs one control, reports, and exits, so no control sees anything left
    by another. Files are the only thing children share; the two a fresh
    window would read, its own output folder and the preferences file, are
    put back to what they were after the setup before each control.
    """

    TIMEOUT = float(os.environ.get('LSS_SWEEP_CHILD_TIMEOUT', '900'))

    def __init__(self, make_window, app, recorder, spec, state):
        self.make_window, self.app, self.recorder = make_window, app, recorder
        self.spec, self.setup = spec, STATES[state]
        self.w = None
        self.broken = None
        self.out_dir = self.pristine = None
        self.prefs = None
        self.frozen = False
        from PyQt5.QtCore import QThreadPool
        self.pool = QThreadPool.globalInstance()
        self.expiry = self.pool.expiryTimeout()
        self.pool.setExpiryTimeout(0)        # no idle Qt pool threads when forking (_no_pool_threads)

    def build(self):
        """The window in the state; True when it is ready for controls."""
        import gc
        import shutil
        import tempfile
        from lss_core import preferences
        rec = self.recorder
        self.w = self.make_window()
        made = self.w.directory
        rec.exceptions.clear()
        try:
            self.setup(self.w, self.app, self.spec)
        except Exception as exc:
            self.broken = '%s @ setup' % type(exc).__name__
            return False
        if rec.exceptions:
            self.broken = _first(rec)
            return False
        if self.w.directory != made and os.path.isdir(self.w.directory):
            self.out_dir = self.w.directory       # the state's own folder (state_spec_loaded)
            self.pristine = os.path.join(tempfile.mkdtemp(prefix='lss-sweep-pristine-'), 'out')
            shutil.copytree(self.out_dir, self.pristine)
        try:
            with open(preferences.path(), 'rb') as f:
                self.prefs = f.read()
        except OSError:
            self.prefs = None
        gc.collect()
        gc.freeze()          # the children's collections then leave these objects' pages alone
        self.frozen = True
        return True

    def _restore_files(self):
        import shutil
        from lss_core import preferences
        if self.out_dir:
            shutil.rmtree(self.out_dir, ignore_errors=True)
            shutil.copytree(self.pristine, self.out_dir)
        p = preferences.path()
        if self.prefs is None:
            if os.path.exists(p):
                os.remove(p)
        else:
            with open(p, 'wb') as f:
                f.write(self.prefs)

    def run(self, job):
        """``job(window)`` in a forked copy of the state window; its JSON result.

        A child that dies or hangs gives {'err': '... @ child'}, so a
        segmentation fault becomes an inventory entry instead of ending the run.
        """
        import json
        import select
        import signal
        import sys
        import warnings
        _no_pool_threads()
        sys.stdout.flush()
        sys.stderr.flush()
        r, wfd = os.pipe()
        with warnings.catch_warnings():
            # the other threads are BLAS worker pools, which re-create themselves
            # in a child (pthread_atfork); Qt's pool threads are gone (_no_pool_threads)
            warnings.simplefilter('ignore', DeprecationWarning)
            pid = os.fork()
        if pid == 0:                                   # the child
            code = 0
            try:
                os.close(r)
                self._restore_files()
                self.recorder.exceptions.clear()
                data = json.dumps(job(self.w)).encode()
                while data:
                    data = data[os.write(wfd, data):]
            except BaseException:
                traceback.print_exc()
                code = 3
            finally:
                try:
                    sys.stdout.flush()
                    sys.stderr.flush()
                finally:
                    os._exit(code)
        os.close(wfd)
        chunks = []
        deadline = time.monotonic() + self.TIMEOUT
        timed_out = False
        while True:
            left = deadline - time.monotonic()
            if left <= 0 or not select.select([r], [], [], left)[0]:
                timed_out = True
                os.kill(pid, signal.SIGKILL)
                break
            b = os.read(r, 65536)
            if not b:
                break
            chunks.append(b)
        os.close(r)
        _pid, status = os.waitpid(pid, 0)
        if timed_out:
            return {'err': 'Timeout @ child'}
        if not chunks:
            if os.WIFSIGNALED(status):
                return {'err': 'Signal%d @ child' % os.WTERMSIG(status)}
            return {'err': 'Exit%d @ child' % os.WEXITSTATUS(status)}
        return json.loads(b''.join(chunks))

    def close(self):
        import gc
        import shutil
        if self.frozen:
            gc.unfreeze()
            self.frozen = False
        if self.pristine:
            shutil.rmtree(os.path.dirname(self.pristine), ignore_errors=True)
            self.pristine = None
        if self.w is not None:
            dispose(self.w, self.app, self.recorder)
            self.w = None
        self.pool.setExpiryTimeout(self.expiry)


def _trigger(app, recorder, fn):
    """Run one control; return 'Type @ where' or None."""
    try:
        fn()
        app.processEvents()
    except Exception as exc:           # raised outside a slot
        return '%s @ direct' % type(exc).__name__
    if recorder.exceptions:
        return _first(recorder)
    return None


def run_state(make_window, app, recorder, spec, state, exercised=None):
    """Trigger every control once in ``state``; return {key: 'Type @ where'}.

    Every control gets a fresh window in that state. When a control opens a
    dialog, every control of that dialog is triggered too (one level deep),
    reopening the dialog each time; those keys read 'parent > child'.
    ``exercised``, if a list, receives every key triggered, in order.

    With fork (``fork_available``) the state window is built once and each
    control runs in a forked copy of it (2026-11-22: about ten times faster
    than building a window per control); otherwise a new window is built and
    put into the state for every control.
    """
    if not fork_available():
        return _run_state_rebuild(make_window, app, recorder, spec, state, exercised)
    failures = {}
    drv = _ForkDriver(make_window, app, recorder, spec, state)
    probe = make_window()
    keys = list(controls(probe))
    dispose(probe, app, recorder)
    del probe

    def first(w, key):
        fn = controls(w).get(key)
        if fn is None:
            return {'missing': True}
        t0 = time.perf_counter()
        err = _trigger(app, recorder, fn)
        _log_time(state, key, t0)
        if err:
            return {'err': err}
        dialogs = _visible_dialogs(w)
        return {'children': list(controls(dialogs[-1])) if dialogs else []}

    def second(w, key, ck):
        parent = controls(w).get(key)
        if parent is None or _trigger(app, recorder, parent):
            return {'stop': True}
        dialogs = _visible_dialogs(w)
        if not dialogs:
            return {'stop': True}
        child = controls(dialogs[-1]).get(ck)
        if child is None:
            return {'missing': True}
        recorder.exceptions.clear()
        t0 = time.perf_counter()
        err = _trigger(app, recorder, child)
        _log_time(state, '%s > %s' % (key, ck), t0)
        return {'err': err}

    try:
        if not drv.build():
            failures['<setup>'] = drv.broken
            return failures
        for key in keys:
            res = drv.run(lambda w: first(w, key))
            if res.get('missing'):
                continue
            if exercised is not None:
                exercised.append(key)
            if res.get('err'):
                failures[key] = res['err']
                continue
            for ck in res.get('children', []):
                res2 = drv.run(lambda w: second(w, key, ck))
                if res2.get('stop'):
                    break
                if res2.get('missing'):
                    continue
                if exercised is not None:
                    exercised.append('%s > %s' % (key, ck))
                if res2.get('err'):
                    failures['%s > %s' % (key, ck)] = res2['err']
    finally:
        drv.close()
    return failures


def _run_state_rebuild(make_window, app, recorder, spec, state, exercised=None):
    """run_state with a new window built for every control (no fork)."""
    drv = _Driver(make_window, app, recorder, spec, state)
    failures = {}
    probe = make_window()
    keys = list(controls(probe))
    dispose(probe, app, recorder)
    del probe
    for key in keys:
        if not drv.reset():
            failures['<setup>'] = drv.broken
            break
        fn = controls(drv.w).get(key)
        if fn is None:
            continue
        if exercised is not None:
            exercised.append(key)
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
            if exercised is not None:
                exercised.append('%s > %s' % (key, ck))
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
