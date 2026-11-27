"""The plot options of a tab (F112, F113, F114).

The owner, 2026-11-26: "Add a plot preferences button that applies to the
plots on that tab that has useful options, like font size, minor/major
ticks, grid on/off"; 2026-11-27: "begin the comprehensive solution for plot
customization" (the "one merged, saved window").

A window opened by "Plot options..." at the right of the tab bar. It shows
the options of the tab on show and follows the tabs as they change; every
change applies at once and is kept, per tab, between sessions and through
the tab's redraws (the canvases apply them at every draw,
``mplwidget.apply_plot_options``). Three pages:

- Text and ticks: font size, tick numbers, major and minor ticks, tick
  direction, ticks on all sides, grid, index numbers;
- Legend and lines: the legend (shown or hidden, its place, its frame), the
  curves' line width and marker size, titles;
- This plot: one plot of the tab at a time: its title and axis labels
  renamed (the rename applies whenever the reader draws that text), fixed
  ranges, and each curve's colour, line, width, marker and size, kept by
  the curve's name or by its position.

'As drawn' (every default) leaves a plot as the reader draws it."""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QMenu, QPushButton, QSpinBox, QTabWidget, QToolButton,
                             QVBoxLayout, QWidget)

import mplwidget
from mplwidget import AS_DRAWN

ROWS = [   # (key, label, object name, page, tooltip)
    ('font', 'Font size', 'plotOptFontSpinBox', 0,
     'The size (pt) of the tick labels, axis labels and legends of this tab\'s plots; titles 1.2 x. "auto": the '
     'reader\'s size, at least that of the tab labels (F111)'),
    ('ticknum', 'Tick numbers', 'plotOptTickNumComboBox', 0,
     'The numbers on linear axes: plain (0.00025), or scientific with one power of ten for the axis '
     '(2.5 with x10^-4 at its end). Log axes keep theirs'),
    ('major', 'Major ticks', 'plotOptMajorComboBox', 0,
     'About how many labelled ticks on each linear axis (fewer leave room for large labels); log axes keep '
     'theirs. "as drawn": matplotlib\'s choice'),
    ('minor', 'Minor ticks', 'plotOptMinorComboBox', 0,
     'Unlabelled ticks between the major ones. "as drawn": as the reader draws them (log axes have them, linear '
     'axes not)'),
    ('direction', 'Tick direction', 'plotOptDirectionComboBox', 0,
     'Ticks pointing out of the plot, into it, or across the axis line'),
    ('mirror', 'Ticks on all sides', 'plotOptMirrorComboBox', 0,
     'Ticks on the top and right edges too, as in many journals\' figures'),
    ('grid', 'Grid', 'plotOptGridComboBox', 0,
     'Grid lines at the major ticks, or at the major and minor ticks (minor ticks are then shown). This '
     'overrides a tab\'s own Grid box while it is not "as drawn"'),
    ('index', 'Index numbers', 'plotOptIndexCheckBox', 0,
     'The points\' index numbers (F113; the SpecPlot\'s Point # labels). Where they would overlap, the later ones '
     'are hidden; zoom in and they come back once they fit. Unticked: none on this tab\'s plots'),
    ('legend', 'Legend', 'plotOptLegendComboBox', 1,
     'Show or hide the legend of each plot. "shown" makes one where the reader draws none (when the curves have '
     'names). This overrides a tab\'s own Legend box while it is not "as drawn"'),
    ('legend_loc', 'Legend place', 'plotOptLegendLocComboBox', 1,
     'Where a shown legend goes; "best": where it hides the fewest points'),
    ('legend_frame', 'Legend frame', 'plotOptLegendFrameComboBox', 1,
     'A box around the legend, or none'),
    ('linewidth', 'Line width', 'plotOptLineWidthSpinBox', 1,
     'The width (pt) of every curve\'s line and error bars on this tab; a curve\'s own width (This plot) wins. '
     '"as drawn": the reader\'s'),
    ('markersize', 'Marker size', 'plotOptMarkerSizeSpinBox', 1,
     'The size (pt) of every curve\'s markers on this tab; a curve\'s own size (This plot) wins'),
    ('titles', 'Titles', 'plotOptTitlesComboBox', 1,
     'Hide the plots\' titles (the file name and fitted numbers above a SpecPlot, for example) to give the data '
     'more room'),
]

TAB_KEYS = [r[0] for r in ROWS]


def _text(v):
    if v == AS_DRAWN:
        return v
    return 'about %d' % v if isinstance(v, int) else str(v)


def _combo(parent, items):
    """A combo box of (shown, value) pairs."""
    w = QComboBox(parent)
    for shown, value in items:
        w.addItem(shown, value)
    return w


def _set_combo(w, value):
    i = w.findData(value)
    w.setCurrentIndex(i if i >= 0 else 0)


def _num(text):
    try:
        return float(str(text).strip())
    except ValueError:
        return None


class PlotOptionsDialog(QDialog):
    """Non-modal. From the window: ``options_for(key)`` and ``set_options(key,
    opts)``; ``plots_for(key)``: the tab's plots as (plot id, name, axes);
    ``copy_to_all(opts)``: the tab-wide options to every tab.
    ``target(key, label, base_pt)`` shows a tab's options."""

    def __init__(self, parent, options_for, set_options, plots_for=None, copy_to_all=None):
        super().__init__(parent)
        self.setObjectName('plotOptionsDialog')
        self.setWindowModality(Qt.NonModal)
        self.options_for, self.set_options = options_for, set_options
        self.plots_for, self.copy_to_all = plots_for, copy_to_all
        self.key = None
        self.label = ''
        self._loading = False
        self._plots = {}
        v = QVBoxLayout(self)
        self.tabLabel = QLabel('')
        self.tabLabel.setObjectName('plotOptTabLabel')
        self.tabLabel.setToolTip('The options apply to the plots of this tab; each tab keeps its own, between '
                                 'sessions and through its redraws. They follow the tab on show')
        v.addWidget(self.tabLabel)
        self.pages = QTabWidget(self)
        self.pages.setObjectName('plotOptPagesTabWidget')
        v.addWidget(self.pages)
        forms = []
        for title in ('Text and ticks', 'Legend and lines'):
            page = QWidget()
            form = QFormLayout(page)
            self.pages.addTab(page, title)
            forms.append(form)
        self.fields = {}
        for key, label, name, page, tip in ROWS:
            if key == 'index':
                w = QCheckBox(self)
                w.setChecked(True)
                w.stateChanged.connect(self._changed)
            elif key == 'font':
                w = QSpinBox(self)
                w.setRange(0, 40)
                w.setSuffix(' pt')
                w.setSpecialValueText('auto')
                w.valueChanged.connect(self._changed)
            elif key in ('linewidth', 'markersize'):
                w = QDoubleSpinBox(self)
                w.setRange(0.0, 20.0)
                w.setSingleStep(0.5)
                w.setDecimals(1)
                w.setSuffix(' pt')
                w.setSpecialValueText(AS_DRAWN)
                w.valueChanged.connect(self._changed)
            else:
                w = _combo(self, [(_text(c), c) for c in mplwidget.PLOT_OPTION_CHOICES[key]])
                w.currentIndexChanged.connect(self._changed)
            w.setObjectName(name)
            w.setToolTip(tip)
            lab = QLabel(label)
            lab.setToolTip(tip)
            forms[page].addRow(lab, w)
            self.fields[key] = w
        self._build_plot_page()
        row = QHBoxLayout()
        self.allTabsButton = QPushButton('Copy to all tabs', self)
        self.allTabsButton.setObjectName('plotOptAllTabsPushButton')
        self.allTabsButton.setToolTip('Give every tab with plots this tab\'s Text and ticks and Legend and lines '
                                      'options; each tab keeps its own plots\' labels, ranges and curves')
        self.allTabsButton.clicked.connect(self.copy_all)
        self.resetButton = QPushButton('As drawn', self)
        self.resetButton.setObjectName('plotOptResetPushButton')
        self.resetButton.setToolTip('Every option of this tab, its plots\' labels, ranges and curves included, back '
                                    'to "as drawn": the plots as the reader draws them')
        self.resetButton.clicked.connect(self.reset)
        self.closeButton = QPushButton('Close', self)
        self.closeButton.setObjectName('plotOptClosePushButton')
        self.closeButton.setToolTip('Close this window; the options stay as set')
        self.closeButton.clicked.connect(self.close)
        row.addWidget(self.allTabsButton)
        row.addWidget(self.resetButton)
        row.addStretch(1)
        row.addWidget(self.closeButton)
        v.addLayout(row)

    # ---- the page of one plot ----

    def _build_plot_page(self):
        page = QWidget()
        self.pages.addTab(page, 'This plot')
        v = QVBoxLayout(page)
        top = QHBoxLayout()
        self.plotCombo = QComboBox(page)
        self.plotCombo.setObjectName('plotOptPlotComboBox')
        self.plotCombo.setToolTip('The plot of this tab these settings are for (a tab can hold two: the MCA spectrum '
                                  'and its integrals, for example)')
        self.plotCombo.currentIndexChanged.connect(self._load_plot)
        top.addWidget(QLabel('Plot'))
        top.addWidget(self.plotCombo, 1)
        v.addLayout(top)
        g = QGroupBox('Labels and ranges', page)
        f = QFormLayout(g)
        self.labelEdits = {}
        for key, label, name in (('title', 'Title', 'plotOptTitleLineEdit'), ('x', 'X label', 'plotOptXLabelLineEdit'),
                                 ('y', 'Y label', 'plotOptYLabelLineEdit')):
            e = QLineEdit(g)
            e.setObjectName(name)
            e.setToolTip('Type a new text for this %s; empty: the reader\'s, shown greyed. The new text is used whenever '
                         'the reader draws the same text here again (a different column keeps its own name)'
                         % label.lower())
            e.editingFinished.connect(self._plot_changed)
            f.addRow(label, e)
            self.labelEdits[key] = e
        self.rangeFields = {}
        for axis, name in (('x', 'X'), ('y', 'Y')):
            box = QCheckBox('fixed', g)
            box.setObjectName('plotOpt%sFixedCheckBox' % name)
            box.setToolTip('Keep the %s axis between these two values whenever the reader redraws this plot (zoom '
                           'and pan still work in between). Unticked: as drawn' % name.lower())
            lo, hi = QLineEdit(g), QLineEdit(g)
            lo.setObjectName('plotOpt%sMinLineEdit' % name)
            hi.setObjectName('plotOpt%sMaxLineEdit' % name)
            for e, which in ((lo, 'lower'), (hi, 'upper')):
                e.setValidator(QDoubleValidator(e))
                e.setToolTip('The %s end of the fixed %s range' % (which, name.lower()))
                e.editingFinished.connect(self._plot_changed)
            box.stateChanged.connect(self._plot_changed)
            row = QHBoxLayout()
            row.addWidget(box)
            row.addWidget(lo)
            row.addWidget(QLabel('to'))
            row.addWidget(hi)
            f.addRow('%s range' % name, row)
            self.rangeFields[axis] = (box, lo, hi)
        self.viewButton = QPushButton('Use the current view', g)
        self.viewButton.setObjectName('plotOptViewPushButton')
        self.viewButton.setToolTip('Fix both ranges to what the plot shows now (after a zoom, for example)')
        self.viewButton.clicked.connect(self.use_view)
        f.addRow('', self.viewButton)
        v.addWidget(g)
        c = QGroupBox('Curves', page)
        cv = QHBoxLayout(c)
        self.curveList = QListWidget(c)
        self.curveList.setObjectName('plotOptCurveListWidget')
        self.curveList.setToolTip('The curves of this plot as drawn now, in drawing order; choose one to style it')
        self.curveList.currentRowChanged.connect(self._load_curve)
        cv.addWidget(self.curveList, 1)
        cf = QFormLayout()
        self.curveMatch = _combo(c, [('by its name', 'name'), ('by its position', 'position')])
        self.curveMatch.setObjectName('plotOptCurveMatchComboBox')
        self.curveMatch.setToolTip('Keep the style for the curve of this name (a fit, a scan, whatever else is '
                                   'shown), or for the curve at this place in the drawing order (the first, the '
                                   'second...), whatever its name')
        self.curveFields = {
            'color': _combo(c, mplwidget.CURVE_COLOURS),
            'linestyle': _combo(c, mplwidget.CURVE_LINES),
            'linewidth': QDoubleSpinBox(c),
            'marker': _combo(c, mplwidget.CURVE_MARKERS),
            'markersize': QDoubleSpinBox(c),
        }
        names = {'color': ('Colour', 'plotOptCurveColorComboBox', 'The curve\'s colour, its markers\' and error bars\''),
                 'linestyle': ('Line', 'plotOptCurveStyleComboBox', 'Solid, dashed, dotted, dash-dot, or no line'),
                 'linewidth': ('Width', 'plotOptCurveWidthSpinBox', 'The line\'s width (pt)'),
                 'marker': ('Marker', 'plotOptCurveMarkerComboBox', 'The markers at the points, or none'),
                 'markersize': ('Size', 'plotOptCurveSizeSpinBox', 'The markers\' size (pt)')}
        cf.addRow('Keep', self.curveMatch)
        self.curveMatch.currentIndexChanged.connect(self._curve_changed)
        for k, w in self.curveFields.items():
            label, name, tip = names[k]
            if isinstance(w, QDoubleSpinBox):
                w.setRange(0.0, 20.0)
                w.setSingleStep(0.5)
                w.setDecimals(1)
                w.setSuffix(' pt')
                w.setSpecialValueText(AS_DRAWN)
                w.valueChanged.connect(self._curve_changed)
            else:
                w.currentIndexChanged.connect(self._curve_changed)
            w.setObjectName(name)
            w.setToolTip(tip + '; "as drawn": the reader\'s')
            cf.addRow(label, w)
        self.curveResetButton = QPushButton('Curve as drawn', c)
        self.curveResetButton.setObjectName('plotOptCurveResetPushButton')
        self.curveResetButton.setToolTip('This curve\'s style back to the reader\'s')
        self.curveResetButton.clicked.connect(self.reset_curve)
        cf.addRow('', self.curveResetButton)
        cv.addLayout(cf)
        v.addWidget(c)
        bottom = QHBoxLayout()
        self.plotResetButton = QPushButton('Plot as drawn', page)
        self.plotResetButton.setObjectName('plotOptPlotResetPushButton')
        self.plotResetButton.setToolTip('This plot\'s labels, ranges and curve styles back to the reader\'s')
        self.plotResetButton.clicked.connect(self.reset_plot)
        self.axesButton = QToolButton(page)
        self.axesButton.setObjectName('plotOptAxesToolButton')
        self.axesButton.setText('One-off editor...')
        self.axesButton.setPopupMode(QToolButton.InstantPopup)
        self.axesButton.setToolTip(
            'matplotlib\'s editor of one plot (what was the toolbar\'s "Customize" icon): anything it offers, for '
            'the plot as drawn now. One-off: gone when the tab redraws the plot, and not saved; the settings of '
            'this window stay')
        self.axesMenu = QMenu(self.axesButton)
        self.axesMenu.aboutToShow.connect(self._fill_axes_menu)
        self.axesButton.setMenu(self.axesMenu)
        bottom.addWidget(self.plotResetButton)
        bottom.addStretch(1)
        bottom.addWidget(self.axesButton)
        v.addLayout(bottom)

    def plots(self):
        """The tab's plots as (plot id, name, axes) (none without a ``plots_for``)."""
        return list(self.plots_for(self.key)) if (self.plots_for and self.key is not None) else []

    def current_plot(self):
        i = self.plotCombo.currentIndex()
        plots = self.plots()
        return plots[i] if 0 <= i < len(plots) else None

    def _entry(self, pid, create=False):
        if pid not in self._plots and create:
            self._plots[pid] = {'labels': {}, 'xlim': None, 'ylim': None, 'curves': []}
        return self._plots.get(pid)

    def _fill_plots(self):
        keep = self.plotCombo.currentData()
        self.plotCombo.blockSignals(True)
        self.plotCombo.clear()
        for pid, name, _ax in self.plots():
            self.plotCombo.addItem(name, pid)
        i = self.plotCombo.findData(keep)
        self.plotCombo.setCurrentIndex(i if i >= 0 else (0 if self.plotCombo.count() else -1))
        self.plotCombo.blockSignals(False)
        self._load_plot()

    def _load_plot(self, *_a):
        cur = self.current_plot()
        was, self._loading = self._loading, True
        try:
            enabled = cur is not None
            for w in list(self.labelEdits.values()) + [x for t in self.rangeFields.values() for x in t] + \
                    [self.viewButton, self.curveList, self.plotResetButton]:
                w.setEnabled(enabled)
            self.curveList.clear()
            if cur is None:
                for e in self.labelEdits.values():
                    e.setText('')
                    e.setPlaceholderText('(no plot drawn on this tab)')
                self._load_curve()
                return
            pid, _name, ax = cur
            entry = self._entry(pid) or {}
            names = entry.get('labels') or {}
            for key, t in (('title', ax.title), ('x', ax.xaxis.label), ('y', ax.yaxis.label)):
                drawn = mplwidget.drawn_text(t)
                e = self.labelEdits[key]
                e.setPlaceholderText(drawn or '(none)')
                e.setText(names.get(drawn, ''))
                e.setProperty('drawn', drawn)
            for axis, (box, lo, hi) in self.rangeFields.items():
                lim = entry.get(axis + 'lim')
                box.setChecked(bool(lim))
                view = ax.get_xlim() if axis == 'x' else ax.get_ylim()
                vals = lim or view
                lo.setText('%.6g' % vals[0])
                hi.setText('%.6g' % vals[1])
            for pos, (_line, name) in enumerate(mplwidget.data_curves(ax), 1):
                self.curveList.addItem('%d: %s' % (pos, name or '(no name)'))
            if self.curveList.count():
                self.curveList.setCurrentRow(0)
            self._load_curve()
        finally:
            self._loading = was

    def _curve_at(self):
        cur = self.current_plot()
        row = self.curveList.currentRow()
        if cur is None or row < 0:
            return None
        curves = mplwidget.data_curves(cur[2])
        return (cur[0], row + 1, curves[row][1]) if row < len(curves) else None

    def _load_curve(self, *_a):
        at = self._curve_at()
        was, self._loading = self._loading, True
        try:
            for w in list(self.curveFields.values()) + [self.curveMatch, self.curveResetButton]:
                w.setEnabled(at is not None)
            rule = None
            if at is not None:
                pid, pos, name = at
                rules = (self._entry(pid) or {}).get('curves') or []
                rule = mplwidget._rule_for(rules, pos, name)
                _set_combo(self.curveMatch, rule.get('match') if rule else ('name' if name else 'position'))
                self.curveMatch.model().item(0).setEnabled(bool(name))      # no name: by position only
            rule = rule or {}
            for k, w in self.curveFields.items():
                if isinstance(w, QDoubleSpinBox):
                    v = rule.get(k, 0)
                    w.setValue(float(v) if v not in (None, AS_DRAWN) else 0.0)
                else:
                    _set_combo(w, rule.get(k, AS_DRAWN))
        finally:
            self._loading = was

    def _curve_changed(self, *_a):
        if self._loading:
            return
        at = self._curve_at()
        if at is None:
            return
        pid, pos, name = at
        match = self.curveMatch.currentData()
        key = name if (match == 'name' and name) else pos
        if match == 'name' and not name:
            match = 'position'
        rule = {'match': match, 'key': key}
        for k, w in self.curveFields.items():
            rule[k] = w.value() if isinstance(w, QDoubleSpinBox) else w.currentData()
        entry = self._entry(pid, create=True)
        rules = [r for r in entry.get('curves') or []
                 if not ((r.get('match') == 'name' and r.get('key') == name)
                         or (r.get('match') == 'position' and int(r.get('key', 0) or 0) == pos))]
        if mplwidget.curve_rule_set(rule):
            rules.append(rule)
        entry['curves'] = rules
        self._commit()

    def _plot_changed(self, *_a):
        if self._loading:
            return
        cur = self.current_plot()
        if cur is None:
            return
        entry = self._entry(cur[0], create=True)
        names = dict(entry.get('labels') or {})
        for e in self.labelEdits.values():
            drawn = e.property('drawn') or ''
            text = e.text().strip()
            if text and text != drawn:
                names[drawn] = text
            else:
                names.pop(drawn, None)
        entry['labels'] = names
        for axis, (box, lo, hi) in self.rangeFields.items():
            a, b = _num(lo.text()), _num(hi.text())
            entry[axis + 'lim'] = [a, b] if (box.isChecked() and a is not None and b is not None and a != b) else None
        self._commit()

    def use_view(self):
        cur = self.current_plot()
        if cur is None:
            return
        ax = cur[2]
        was, self._loading = self._loading, True
        try:
            for axis, (box, lo, hi) in self.rangeFields.items():
                a, b = ax.get_xlim() if axis == 'x' else ax.get_ylim()
                lo.setText('%.6g' % a)
                hi.setText('%.6g' % b)
                box.setChecked(True)
        finally:
            self._loading = was
        self._plot_changed()

    def reset_curve(self):
        at = self._curve_at()
        if at is None:
            return
        pid, pos, name = at
        entry = self._entry(pid, create=True)
        entry['curves'] = [r for r in entry.get('curves') or []
                           if not ((r.get('match') == 'name' and r.get('key') == name)
                                   or (r.get('match') == 'position' and int(r.get('key', 0) or 0) == pos))]
        self._commit()
        self._load_curve()

    def reset_plot(self):
        cur = self.current_plot()
        if cur is None:
            return
        self._plots.pop(cur[0], None)
        self._commit()
        self._load_plot()

    # ---- the matplotlib editor, one-off ----

    def _fill_axes_menu(self):
        self.axesMenu.clear()
        plots = self.plots()
        if not plots:
            a = self.axesMenu.addAction('(no plot drawn on this tab)')
            a.setEnabled(False)
        for _pid, name, ax in plots:
            self.axesMenu.addAction(name, lambda a=ax: self.edit_axes(a))

    def edit_axes(self, ax):
        """Open matplotlib's figure options for ``ax`` (non-modal, one-off)."""
        from matplotlib.backends.qt_editor import figureoptions
        figureoptions.figure_edit(ax, self)
        return getattr(self, '_fedit_dialog', None)

    # ---- the tab ----

    def target(self, key, label, base_pt=None):
        """Show the options of tab ``key`` (named ``label``)."""
        self.key, self.label = key, label
        if base_pt is not None:
            self.base_pt = base_pt
        base_pt = getattr(self, 'base_pt', None)
        self.setWindowTitle('Plot options: %s' % label)
        self.tabLabel.setText('Plots of the %s tab' % label)
        opts = dict(mplwidget.PLOT_OPTION_DEFAULTS, **(self.options_for(key) or {}))
        import copy
        self._plots = copy.deepcopy(opts.get('plots') or {})
        self._loading = True
        try:
            font = self.fields['font']
            font.setSpecialValueText('auto (%.3g pt)' % base_pt if base_pt else 'auto')
            font.setValue(int(opts['font'] or 0))
            for k, w in self.fields.items():
                if k == 'index':
                    w.setChecked(bool(opts[k]))
                elif isinstance(w, QDoubleSpinBox):
                    w.setValue(float(opts[k] or 0))
                elif k != 'font':
                    _set_combo(w, opts[k])
        finally:
            self._loading = False
        self._fill_plots()

    def tab_values(self):
        out = {'font': int(self.fields['font'].value())}
        for k, w in self.fields.items():
            if k == 'index':
                out[k] = bool(w.isChecked())
            elif isinstance(w, QDoubleSpinBox):
                out[k] = float(w.value())
            elif k != 'font':
                out[k] = w.currentData()
        return out

    def values(self):
        out = self.tab_values()
        out['plots'] = {pid: p for pid, p in self._plots.items() if mplwidget.plot_entry_set(p)}
        return out

    def _commit(self):
        if self.key is not None:
            self.set_options(self.key, self.values())

    def _changed(self, *_a):
        if not self._loading and self.key is not None:
            self._commit()

    def copy_all(self):
        if self.copy_to_all is not None:
            self.copy_to_all(self.tab_values())

    def reset(self):
        if self.key is None:
            return
        self._plots = {}
        self.set_options(self.key, dict(mplwidget.PLOT_OPTION_DEFAULTS))
        self.target(self.key, self.label)
