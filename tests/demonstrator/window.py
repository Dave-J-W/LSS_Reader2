"""The demonstrator's little window (PyQt5 + matplotlib): a mode switch
(reflectivity patching / burn line cuts), selectors for the truth and the
settings, checkboxes for the plotted items and the methods, and the space
bar for a new noise replicate (refit and redraw).

Explanations are in tooltips (AGENTS.md rule 9). Launch with ``python
tests/tools/patch_demo.py``.
"""
from PyQt5 import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from . import burnmode as bm
from . import draw, refl

COUNTS = (0.02, 0.1, 1.0, 10.0, 100.0)
MONITORS = (1e5, 1e6, 1e7, 1e8)


def _combo(items, current=None, tip=''):
    c = QtWidgets.QComboBox()
    for key, label in items:
        c.addItem(label, key)
    if current is not None:
        c.setCurrentIndex([k for k, _ in items].index(current))
    c.setToolTip(tip)
    return c


def _check(label, on, tip):
    b = QtWidgets.QCheckBox(label)
    b.setChecked(on)
    b.setToolTip(tip)
    b.setFocusPolicy(QtCore.Qt.NoFocus)        # the space bar is for new replicates, not for toggling
    return b


def open_demo(parent=None, mode='refl', seed=0, refl_config=None, burn_config=None):
    """Create and show the demonstrator window: ``parent`` a QWidget or
    None; ``refl_config``/``burn_config`` the starting settings (None: the
    defaults); returns the window. It deletes itself when closed. The
    reader's Tools menu starts it as its own process (``patch_demo.py``),
    because the window takes the space bar application-wide."""
    w = DemoWindow(mode=mode, seed=seed, refl_config=refl_config, burn_config=burn_config, parent=parent)
    w.resize(1500, 950)
    w.show()
    return w


class DemoWindow(QtWidgets.QMainWindow):
    """Mode 'refl' or 'burn'; ``parent`` may be the reader's main window. ``seed``: the replicate shown; the space bar
    (or the button) draws the next one. ``self.rep``/``self.results`` hold
    what is drawn (tests read them)."""

    def __init__(self, mode='refl', seed=0, refl_config=None, burn_config=None, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Fit demonstrator (synthetic data)')
        self.seed = int(seed)
        self.refl_config = refl_config or refl.Config()
        self.burn_config = burn_config or bm.Config()
        self.rep = self.results = self.clean_results = None
        self._key = None
        self.fig = Figure(figsize=(11, 7.5))
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        panel = self._controls(mode)
        right = QtWidgets.QWidget()
        rl = QtWidgets.QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(NavigationToolbar2QT(self.canvas, right))
        rl.addWidget(self.canvas)
        split = QtWidgets.QSplitter()
        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(panel)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(270)
        split.addWidget(scroll)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        self.setCentralWidget(split)
        QtWidgets.QApplication.instance().installEventFilter(self)
        self.refresh()

    # ---- controls ------------------------------------------------------------
    def _controls(self, mode):
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        self.mode = _combo([('refl', 'Reflectivity patching'), ('burn', 'Burn line cuts')], mode,
                           'Reflectivity patching: overlapping scans of a known curve joined by every method.\n'
                           'Burn line cuts: GID frames of one spot over time, each estimator of lss_core.burn.')
        lay.addWidget(self.mode)
        top = QtWidgets.QHBoxLayout()
        self.seed_label = QtWidgets.QLabel()
        self.seed_label.setToolTip('The replicate shown: one draw of counting noise. The same seed gives the same data.')
        self.next_button = QtWidgets.QPushButton('New replicate (space)')
        self.next_button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.next_button.setToolTip('Draw new counting noise (seed + 1) and refit everything. Shortcut: space bar.')
        top.addWidget(self.seed_label)
        top.addWidget(self.next_button)
        lay.addLayout(top)
        self.stack = QtWidgets.QStackedWidget()
        self.stack.addWidget(self._refl_page())
        self.stack.addWidget(self._burn_page())
        lay.addWidget(self.stack)
        self.notes = QtWidgets.QPlainTextEdit()
        self.notes.setReadOnly(True)
        self.notes.setMaximumHeight(130)
        self.notes.setToolTip('What the methods reported: failures, guard steps, whether the prior was used.')
        lay.addWidget(self.notes)
        lay.addStretch(1)
        self.mode.currentIndexChanged.connect(self.refresh)
        self.next_button.clicked.connect(self.new_replicate)
        return w

    def _refl_page(self):
        w = QtWidgets.QWidget()
        f = QtWidgets.QFormLayout(w)
        c = self.refl_config
        self.truth = _combo([(k, refl.TRUTH_LABELS[k]) for k in refl.TRUTHS], c.truth,
                            'The true interface (tests/synthetic/xrr.py): bare water, a DPPC monolayer, or a uniform '
                            'film (0.383 e/Å³) on water whose two interfaces make Kiessig fringes of period 2π/d.')
        self.thickness = QtWidgets.QDoubleSpinBox()
        self.thickness.setRange(10.0, 400.0)
        self.thickness.setSingleStep(10.0)
        self.thickness.setValue(c.thickness)
        self.thickness.setSuffix(' Å')
        self.thickness.setToolTip('Film thickness d (film only): fringe period 2π/d.')
        self.plan = _combo([(k, refl.PLAN_LABELS[k]) for k in refl.PLANS], c.plan,
                           'How the curve is cut into scans (tests/synthetic/xrr_scans.py): NX school grids 6–9; four '
                           'scans sharing 4 points; the same with the shared points moved by half a step (none '
                           'coincide); NX-like ranges with every overlap staggered; and, as an aside, a staggered overlap '
                           'across the critical edge (P1; the owner does not patch there: the counts are plenty '
                           'until they fall 100×).')
        self.counts = _combo([(v, '×%g' % v) for v in COUNTS], c.counts if c.counts in COUNTS else 1.0,
                             'Beam and monitors scaled together: ×1 is the NX school rate (about 4e5 counts/s at '
                             'each scan\'s first point). The absorbers chosen do not change; errors scale as 1/√counts.')
        self.monc = _combo([(k, refl.MONITOR_LABELS[k]) for k in refl.MONITORS], c.monitor,
                           'How Monc is drawn. Owner (2026-11-22): "monc doesn\'t have poisson noise, it\'s more like '
                           'a strict 0.05% uncertainty" (tests/synthetic/xrr_scans.REAL_MONITOR, the default). '
                           'Poisson: Monc as counts (the generator\'s older model).')
        self.foil = _check('foils off calibration', c.foil_error,
                           'Each replicate draws the true foil steps from the prior\'s covariance (the prior is right '
                           'on average, with the error it claims). Off: the prior is exact.')
        self.view = _combo([('rrf', 'R / R_F'), ('r', 'R')], 'rrf',
                           'R_F: the reader\'s Fresnel curve (sharp water, no absorption, Qc 0.0217 Å⁻¹).')
        self.join = QtWidgets.QSpinBox()
        self.join.setRange(1, 6)
        self.join.setToolTip('Which join the close-up shows (1: the first pair of scans).')
        for lab, wid in (('Truth', self.truth), ('Film', self.thickness), ('Scans', self.plan),
                         ('Counts', self.counts), ('Monitor', self.monc), ('', self.foil), ('View', self.view),
                         ('Join', self.join)):
            f.addRow(lab, wid)
        box = QtWidgets.QGroupBox('Methods')
        bl = QtWidgets.QVBoxLayout(box)
        self.method_boxes = {}
        for name, spec in refl.METHODS.items():
            b = _check(spec['label'], name in refl.DEFAULT_METHODS, _METHOD_TIPS.get(name, name))
            self.method_boxes[name] = b
            bl.addWidget(b)
        f.addRow(box)
        box = QtWidgets.QGroupBox('Plotted items')
        bl = QtWidgets.QVBoxLayout(box)
        self.refl_items = {}
        for key, label, tip in draw.REFL_ITEMS:
            b = _check(label, key in draw.REFL_DEFAULT, tip)
            self.refl_items[key] = b
            bl.addWidget(b)
        f.addRow(box)
        for wid in (self.truth, self.plan, self.counts, self.monc):
            wid.currentIndexChanged.connect(self.refresh)
        self.thickness.valueChanged.connect(self.refresh)
        self.foil.toggled.connect(self.refresh)
        self.view.currentIndexChanged.connect(self.redraw)
        self.join.valueChanged.connect(self.redraw)
        for b in list(self.method_boxes.values()) + list(self.refl_items.values()):
            b.toggled.connect(self.redraw)
        return w

    def _burn_page(self):
        w = QtWidgets.QWidget()
        f = QtWidgets.QFormLayout(w)
        c = self.burn_config
        self.change = _combo([(k, bm.CHANGE_LABELS[k]) for k in bm.CHANGES], c.change,
                             'What happens to the spot over the test (tests/synthetic/burn_profiles.py). The '
                             'broadening at constant area on the shoulder is the P44 case.')
        self.amount = QtWidgets.QDoubleSpinBox()
        self.amount.setDecimals(4)
        self.amount.setRange(0.0, 2.0)
        self.amount.setSingleStep(0.05)
        self.amount.setValue(c.amount_used)
        self.amount.setToolTip('Size of the change at the end of the test: relative for fade, broaden, shoulder and '
                               'floor; Å⁻¹ for a shift (default 0.004).')
        self.monitor = _combo([(v, '%.0e' % v) for v in MONITORS], c.monitor,
                              'Monitor counts per frame: sets the counting noise (1e7: about 2e5 counts at the top '
                              'of the peak).')
        self.frame = QtWidgets.QSpinBox()
        self.frame.setRange(0, c.n - 1)
        self.frame.setValue(c.n - 1)
        self.frame.setToolTip('Which frame\'s line cut is shown (its time is marked on the trends).')
        for lab, wid in (('Change', self.change), ('Amount', self.amount), ('Monitor', self.monitor),
                         ('Frame', self.frame)):
            f.addRow(lab, wid)
        box = QtWidgets.QGroupBox('Estimators')
        bl = QtWidgets.QVBoxLayout(box)
        self.estimator_boxes = {}
        for name in bm.ESTIMATORS:
            b = _check(name, True, _ESTIMATOR_TIPS[name])
            self.estimator_boxes[name] = b
            bl.addWidget(b)
        f.addRow(box)
        box = QtWidgets.QGroupBox('Plotted items')
        bl = QtWidgets.QVBoxLayout(box)
        self.burn_items = {}
        for key, label, tip in draw.BURN_ITEMS:
            b = _check(label, key in draw.BURN_DEFAULT, tip)
            self.burn_items[key] = b
            bl.addWidget(b)
        f.addRow(box)
        self.change.currentIndexChanged.connect(self._change_changed)
        self.amount.valueChanged.connect(self.refresh)
        self.monitor.currentIndexChanged.connect(self.refresh)
        self.frame.valueChanged.connect(self.redraw)
        for b in list(self.estimator_boxes.values()) + list(self.burn_items.values()):
            b.toggled.connect(self.redraw)
        return w

    def _change_changed(self):
        self.amount.blockSignals(True)
        self.amount.setValue(bm.DEFAULT_AMOUNTS[self.change.currentData()])
        self.amount.blockSignals(False)
        self.refresh()

    # ---- state ---------------------------------------------------------------
    def current_mode(self):
        return self.mode.currentData()

    def eventFilter(self, obj, ev):
        if (ev.type() == QtCore.QEvent.KeyPress and ev.key() == QtCore.Qt.Key_Space and not ev.isAutoRepeat()
                and isinstance(obj, QtWidgets.QWidget) and obj.window() is self):
            self.new_replicate()
            return True
        return False

    def closeEvent(self, ev):
        QtWidgets.QApplication.instance().removeEventFilter(self)
        super().closeEvent(ev)

    def new_replicate(self):
        self.seed += 1
        self.refresh()

    def _configs(self):
        rc = refl.Config(truth=self.truth.currentData(), plan=self.plan.currentData(),
                         counts=float(self.counts.currentData()), thickness=float(self.thickness.value()),
                         foil_error=self.foil.isChecked(), monitor=self.monc.currentData())
        bc = bm.Config(change=self.change.currentData(), amount=float(self.amount.value()),
                       monitor=float(self.monitor.currentData()))
        return rc, bc

    def refresh(self):
        """Recompute the replicate (if its configuration or seed changed) and redraw."""
        mode = self.current_mode()
        self.stack.setCurrentIndex(0 if mode == 'refl' else 1)
        self.seed_label.setText('seed %d' % self.seed)
        rc, bc = self._configs()
        key = (mode, self.seed, repr(rc) if mode == 'refl' else repr(bc))
        if key != self._key:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            try:
                if mode == 'refl':
                    self.refl_config = rc
                    self.rep = refl.replicate(rc, self.seed)
                    self.results = refl.run_all(self.rep)
                    self.clean_results = refl.run_all(refl.denoised(self.rep))
                    self.join.setMaximum(max(len(self.rep.scans) - 1, 1))
                else:
                    self.burn_config = bc
                    self.rep = bm.replicate(bc, self.seed)
                    self.results = bm.run_all(self.rep)
                    self.clean_results = None
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()
            self._key = key
        self.redraw()

    def redraw(self):
        if self.rep is None:
            return
        mode = self.current_mode()
        if (mode == 'refl') != isinstance(self.rep, refl.Replicate):
            return self.refresh()
        notes = []
        if mode == 'refl':
            show = {k for k, b in self.refl_items.items() if b.isChecked()}
            methods = [n for n, b in self.method_boxes.items() if b.isChecked()]
            draw.refl_figure(self.fig, self.rep, self.results, show, methods, self.view.currentData(),
                             self.join.value(), self.clean_results)
            for n in methods:
                r = self.results[n]
                if r.error:
                    notes.append('%s: %s' % (n, r.error))
                notes += ['%s: %s' % (n, x) for x in r.notes]
        else:
            show = {k for k, b in self.burn_items.items() if b.isChecked()}
            est = [n for n, b in self.estimator_boxes.items() if b.isChecked()]
            draw.burn_figure(self.fig, self.rep, self.results, show, est, self.frame.value())
            for n in est:
                r = self.results[n]
                if r.error:
                    notes.append('%s: %s' % (n, r.error))
                notes += ['%s: %s' % (n, x) for x in r.notes]
                for q, c in (r.trends or {}).items():
                    notes.append('%s %s: best %s, %s' % (n, q, c.best, 'stable' if c.stable else 'changing'))
        self.notes.setPlainText('\n'.join(notes) or 'no notes')
        self.canvas.draw_idle()


_METHOD_TIPS = {
    'legacy': 'The reader\'s chain (lss_core.reflectivity.patch, method=\'legacy\'): scan b interpolated by a cubic '
              'spline in linear intensity at the merged data\'s overlap points (P1), its own error, no inheritance (P4).',
    'reader': 'The reader\'s chain with its default factor since 2026-11-22 (reflectivity.join_factor, method=\'joint\'): '
              'the joint fit against the merged data; the overlap still averaged and the error folded in as before.',
    'interp': 'patching.interp_factor: the spline ratio against the previous scan, counting errors, inflate-only, '
              'Σ carried along the chain.',
    'interp_log': 'patching.interp_factor(log=True): the spline in ln y (10× less P1 bias).',
    'coincident': 'patching.coincident_factor: ratios at Qz measured in both scans only (fails on staggered grids).',
    'joint': 'patching.joint_factor with its defaults: one polynomial in ln(R/R_F) through both scans, 2 points '
             'either side (N_EXT); the guard ladder (largest window first, the order rising to what the points '
             'carry) keeps the first fit with χ² p ≥ 0.3, else the most adequate with its error inflated.',
    'joint_e4': 'The default joint fit with 4 points either side (the default before 2026-11-22), with the ladder.',
    'joint_raw': 'The default joint fit in ln R instead of ln(R/R_F).',
    'joint_log': 'The default joint fit by weighted least squares in ln y (closed form; biased at low counts).',
    'joint_prior': 'patching.chain(prior=known_steps(...)): the default joint fit combined with the calibrated foil '
                   'ratios (correlated), where Monc/Monp shows no slit change and |z| ≤ 3.',
    'fixed_o2_e0': 'One joint fit, order 2, overlap only, no guard.',
    'fixed_o2_e4': 'One joint fit, order 2, 4 points either side, no guard (biased near fringes and at high Qz).',
    'fixed_o4_e2': 'One joint fit, order 4, 2 points either side, no guard.',
    'fixed_o4_e4': 'One joint fit, order 4, 4 points either side, no guard (the old default window without the guard).',
    'global': 'patching.global_fit: all factors in one least-squares fit in ln y (order 4, 4 either side per join, '
              'no guard, one χ² inflation for all).',
}
_ESTIMATOR_TIPS = {
    'template': 'burn.measure_gid default: each frame fitted as A × the mean frame\'s shape, shifted and stretched, '
                'on a straight background.',
    'moments': 'The legacy burn test\'s arithmetic: straight baseline through 3 points at each end of the window, '
               'then sum, centroid and 2.355 × r.m.s. width. Its curve here is only the Gaussian of those numbers.',
    'fit': 'lss_core.peaks.fit: one Gaussian on a straight background in the window.',
}
