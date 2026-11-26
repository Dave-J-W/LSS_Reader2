"""The plot options of a tab (F112; owner, 2026-11-26: "Add a plot
preferences button that applies to the plots on that tab that has useful
options, like font size, minor/major ticks, grid on/off").

A small window, opened by the "Plot options" button at the right of the
tab bar. It shows the options of the tab on show and follows the tabs as
they change. Every change applies at once and is kept between sessions.
'As drawn' (the default of every option) leaves the plots as the reader
draws them; the choice is applied by the canvases themselves at every
draw (``mplwidget.apply_plot_options``), so a redrawn plot keeps it."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QMenu, QPushButton,
                             QSpinBox, QToolButton, QVBoxLayout)

import mplwidget

ROWS = [   # (key, label, object name, tooltip)
    ('font', 'Font size', 'plotOptFontSpinBox',
     'The size (pt) of the tick labels, axis labels and legends of this tab\'s plots; titles 1.2 x. "auto": the '
     'reader\'s size, at least that of the tab labels (F111)'),
    ('major', 'Major ticks', 'plotOptMajorComboBox',
     'About how many labelled ticks on each linear axis (fewer leave room for large labels); log axes keep '
     'theirs. "as drawn": matplotlib\'s choice'),
    ('minor', 'Minor ticks', 'plotOptMinorComboBox',
     'Unlabelled ticks between the major ones. "as drawn": as the reader draws them (log axes have them, linear '
     'axes not)'),
    ('direction', 'Tick direction', 'plotOptDirectionComboBox',
     'Ticks pointing out of the plot, into it, or across the axis line'),
    ('mirror', 'Ticks on all sides', 'plotOptMirrorComboBox',
     'Ticks on the top and right edges too, as in many journals\' figures'),
    ('grid', 'Grid', 'plotOptGridComboBox',
     'Grid lines at the major ticks, or at the major and minor ticks (minor ticks are then shown). This '
     'overrides a tab\'s own Grid box while it is not "as drawn"'),
    ('index', 'Index numbers', 'plotOptIndexCheckBox',
     'The points\' index numbers (F113; the SpecPlot\'s Point # labels). Where they would overlap, the later ones '
     'are hidden; zoom in and they come back once they fit. Unticked: none on this tab\'s plots'),
]


def _text(v):
    if v == mplwidget.AS_DRAWN:
        return v
    return 'about %d' % v if isinstance(v, int) else str(v)


class PlotOptionsDialog(QDialog):
    """Non-modal; ``options_for(key)`` and ``set_options(key, opts)`` come
    from the window; ``target(key, label, base_pt)`` shows a tab's options.
    ``plots_for(key)``: the tab's plots as (name, axes), for "Axes and
    curves...", matplotlib's own editor of one plot (owner, 2026-11-26: its
    toolbar icon is dropped on the tabs and reached from here instead)."""

    def __init__(self, parent, options_for, set_options, plots_for=None):
        super().__init__(parent)
        self.setObjectName('plotOptionsDialog')
        self.setWindowModality(Qt.NonModal)
        self.options_for, self.set_options, self.plots_for = options_for, set_options, plots_for
        self.key = None
        self._loading = False
        v = QVBoxLayout(self)
        self.tabLabel = QLabel('')
        self.tabLabel.setObjectName('plotOptTabLabel')
        self.tabLabel.setToolTip('The options apply to the plots of this tab; each tab keeps its own, between '
                                 'sessions. They follow the tab on show')
        v.addWidget(self.tabLabel)
        form = QFormLayout()
        self.fields = {}
        for key, label, name, tip in ROWS:
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
            else:
                w = QComboBox(self)
                for c in mplwidget.PLOT_OPTION_CHOICES[key]:
                    w.addItem(_text(c), c)
                w.currentIndexChanged.connect(self._changed)
            w.setObjectName(name)
            w.setToolTip(tip)
            lab = QLabel(label)
            lab.setToolTip(tip)
            form.addRow(lab, w)
            self.fields[key] = w
        v.addLayout(form)
        axes = QHBoxLayout()
        self.axesButton = QToolButton(self)
        self.axesButton.setObjectName('plotOptAxesToolButton')
        self.axesButton.setText('Axes and curves...')
        self.axesButton.setPopupMode(QToolButton.InstantPopup)
        self.axesButton.setToolTip(
            'matplotlib\'s editor of one plot of this tab: its title, axis limits, labels and scales, and each '
            'curve\'s line, marker and colour. One-off: kept until the tab redraws that plot (a new selection, an '
            'option above), and not saved. For settings that stay, use the options above. (It was the toolbar\'s '
            '"Customize" icon.)')
        self.axesMenu = QMenu(self.axesButton)
        self.axesMenu.aboutToShow.connect(self._fill_axes_menu)
        self.axesButton.setMenu(self.axesMenu)
        axes.addWidget(self.axesButton)
        axes.addStretch(1)
        v.addLayout(axes)
        row = QHBoxLayout()
        self.resetButton = QPushButton('As drawn', self)
        self.resetButton.setObjectName('plotOptResetPushButton')
        self.resetButton.setToolTip('Every option of this tab back to "as drawn": the plots as the reader draws them')
        self.resetButton.clicked.connect(self.reset)
        self.closeButton = QPushButton('Close', self)
        self.closeButton.setObjectName('plotOptClosePushButton')
        self.closeButton.setToolTip('Close this window; the options stay as set')
        self.closeButton.clicked.connect(self.close)
        row.addWidget(self.resetButton)
        row.addStretch(1)
        row.addWidget(self.closeButton)
        v.addLayout(row)

    def target(self, key, label, base_pt=None):
        """Show the options of tab ``key`` (named ``label``)."""
        self.key, self.label = key, label
        if base_pt is not None:
            self.base_pt = base_pt
        base_pt = getattr(self, 'base_pt', None)
        self.setWindowTitle('Plot options: %s' % label)
        self.tabLabel.setText('Plots of the %s tab' % label)
        opts = dict(mplwidget.PLOT_OPTION_DEFAULTS, **(self.options_for(key) or {}))
        self._loading = True
        try:
            font = self.fields['font']
            font.setSpecialValueText('auto (%.3g pt)' % base_pt if base_pt else 'auto')
            font.setValue(int(opts['font'] or 0))
            for k, w in self.fields.items():
                if k == 'index':
                    w.setChecked(bool(opts[k]))
                elif k != 'font':
                    i = w.findData(opts[k])
                    w.setCurrentIndex(i if i >= 0 else 0)
        finally:
            self._loading = False

    def plots(self):
        """The tab's plots as (name, axes) (none without a ``plots_for``)."""
        return list(self.plots_for(self.key)) if (self.plots_for and self.key is not None) else []

    def _fill_axes_menu(self):
        self.axesMenu.clear()
        plots = self.plots()
        if not plots:
            a = self.axesMenu.addAction('(no plot drawn on this tab)')
            a.setEnabled(False)
        for name, ax in plots:
            self.axesMenu.addAction(name, lambda a=ax: self.edit_axes(a))

    def edit_axes(self, ax):
        """Open matplotlib's figure options for ``ax`` (non-modal)."""
        from matplotlib.backends.qt_editor import figureoptions
        figureoptions.figure_edit(ax, self)
        return getattr(self, '_fedit_dialog', None)

    def values(self):
        out = {'font': int(self.fields['font'].value())}
        for k, w in self.fields.items():
            if k == 'index':
                out[k] = bool(w.isChecked())
            elif k != 'font':
                out[k] = w.currentData()
        return out

    def _changed(self, *_a):
        if not self._loading and self.key is not None:
            self.set_options(self.key, self.values())

    def reset(self):
        if self.key is None:
            return
        self.set_options(self.key, dict(mplwidget.PLOT_OPTION_DEFAULTS))
        self.target(self.key, self.label)
