"""The Compare tab (F80, F105): the reflectivities saved in the open SPEC
file's workbook, overlaid, with their ratios to the first one ticked.

Owner, 2026-11-23: compare reduced data "from different sample areas or
just as time goes by, to check stability"; a tab used only for comparing,
fed by the workbook, "provided the new data auto-update". The window calls
``show_entries`` whenever the workbook changed (a new reduction saved,
automatically or with Save; a live remake), and a newly saved curve is
ticked when "Follow new" is on.

The list holds every saved R curve (the R/RF ones with the box ticked):
its id, version and scans, with the series, time, sx and note in the
tooltip. Order: series, time saved or sx. The plot is log R against Qz;
with "Ratio to the first", a panel below shows each ticked curve over the
first ticked one (lss_core.compare.ratio).
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                             QSplitter, QVBoxLayout, QWidget)

from lss_core import compare
from mplwidget import MplWidget

RID_ROLE = Qt.UserRole + 20


class CompareTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('compareTab')
        self.entries = []
        self.known = set()            # ids listed before: a new one is ticked when Follow new is on
        v = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel('Order by', self))
        self.orderComboBox = QComboBox(self)
        self.orderComboBox.setObjectName('compareOrderComboBox')
        for name in compare.ORDERS:
            self.orderComboBox.addItem({'series': 'series', 'time': 'time saved', 'sx': 'sx'}[name], name)
        self.orderComboBox.setToolTip('The order of the list and of the colours: by series (then first scan and '
                                      'version), by the time the curve was saved, or by the sample position sx of '
                                      'its first scan (F80: "different sample areas or just as time goes by")')
        top.addWidget(self.orderComboBox)
        self.ratioCheckBox = QCheckBox('Ratio to the first', self)
        self.ratioCheckBox.setObjectName('compareRatioCheckBox')
        self.ratioCheckBox.setChecked(True)
        self.ratioCheckBox.setToolTip('A panel below: each ticked curve divided by the first ticked one, on the '
                                      'first one\'s Qz inside the range both cover (the other interpolated in log '
                                      'R against log Qz); errors add in quadrature, neighbouring points are correlated by the '
                                      'interpolation (lss_core.compare.ratio)')
        top.addWidget(self.ratioCheckBox)
        self.rrfCheckBox = QCheckBox('R/R_F', self)
        self.rrfCheckBox.setObjectName('compareRrfCheckBox')
        self.rrfCheckBox.setToolTip('List the saved R/R_F curves instead of R')
        top.addWidget(self.rrfCheckBox)
        self.followCheckBox = QCheckBox('Follow new', self)
        self.followCheckBox.setObjectName('compareFollowCheckBox')
        self.followCheckBox.setChecked(True)
        self.followCheckBox.setToolTip('Tick each newly saved curve as it arrives (a reduction saved by itself or '
                                       'with Save, a live remake): the comparison updates itself (owner, Q-REF-5)')
        top.addWidget(self.followCheckBox)
        self.infoLabel = QLabel('', self)
        self.infoLabel.setObjectName('compareInfoLabel')
        top.addWidget(self.infoLabel, 1)
        v.addLayout(top)
        split = QSplitter(Qt.Horizontal, self)
        self.listWidget = QListWidget(split)
        self.listWidget.setObjectName('compareListWidget')
        self.listWidget.setToolTip('The reflectivities saved in this SPEC file\'s workbook. Tick the ones to '
                                   'compare; hover for the series, time, sx and note')
        self.plotWidget = MplWidget(split)
        self.plotWidget.setObjectName('comparePlotWidget')
        split.addWidget(self.listWidget)
        split.addWidget(self.plotWidget)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 3)
        self.listWidget.setMinimumWidth(230)          # 'R0012 v3  S# 6–9  (out of date)' fits
        split.setSizes([300, 1000])
        v.addWidget(split, 1)
        self.listWidget.itemChanged.connect(lambda *_: self.draw())
        self.orderComboBox.currentIndexChanged.connect(lambda *_: self.relist())
        self.ratioCheckBox.toggled.connect(lambda *_: self.draw())
        self.rrfChanged = None           # the window re-reads the workbook when R/R_F is toggled
        self.rrfCheckBox.toggled.connect(lambda *_: self.rrfChanged() if self.rrfChanged else None)
        self.axes = []

    def label(self):
        return 'R/RF' if self.rrfCheckBox.isChecked() else 'R'

    def show_entries(self, items, message=''):
        """The saved curves to list; keeps the ticks, and ticks new ones when
        Follow new is on (or the first curve when none is ticked yet)."""
        ticked = self.ticked_ids()
        new = [e.rid for e in items if e.rid not in self.known]
        if self.followCheckBox.isChecked():
            ticked |= set(new)
        if not ticked and items:
            ticked = {items[-1].rid}
        self.known |= {e.rid for e in items}
        self.entries = list(items)
        self._ticks = ticked
        self.relist()
        self.infoLabel.setText(message or ('%d saved curve%s' % (len(items), 's' if len(items) != 1 else '')))

    def tick(self, rid):
        """Tick saved curve ``rid`` (the timeline's reduced lane opens it here)."""
        for i in range(self.listWidget.count()):
            it = self.listWidget.item(i)
            if it.data(RID_ROLE) == rid:
                it.setCheckState(Qt.Checked)
                self.listWidget.scrollToItem(it)
                return True
        return False

    def ticked_ids(self):
        out = set()
        for i in range(self.listWidget.count()):
            it = self.listWidget.item(i)
            if it.checkState() == Qt.Checked:
                out.add(it.data(RID_ROLE))
        return out

    def relist(self):
        ticked = self.ticked_ids() if self.listWidget.count() else getattr(self, '_ticks', set())
        ticked |= getattr(self, '_ticks', set())
        self._ticks = set()
        by = self.orderComboBox.currentData() or 'series'
        self.listWidget.blockSignals(True)
        self.listWidget.clear()
        for e in compare.order(self.entries, by):
            it = QListWidgetItem(e.title())
            it.setData(RID_ROLE, e.rid)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if e.rid in ticked else Qt.Unchecked)
            it.setToolTip('Saved %s, %s%s; series %s; sx %s mm%s' % (
                e.saved, e.origin or 'user', ', out of date (its scans have grown since)' if e.stale else '',
                e.series or 'none', '%g' % e.sx if e.sx is not None else 'not known',
                '\nNote: ' + e.note if e.note else ''))
            self.listWidget.addItem(it)
        self.listWidget.blockSignals(False)
        self.draw()

    def shown(self):
        """The ticked entries, in list order."""
        by_id = {e.rid: e for e in self.entries}
        out = []
        for i in range(self.listWidget.count()):
            it = self.listWidget.item(i)
            if it.checkState() == Qt.Checked and it.data(RID_ROLE) in by_id:
                out.append(by_id[it.data(RID_ROLE)])
        return out

    def draw(self):
        fig = self.plotWidget.canvas.fig
        fig.clf()
        shown = [e for e in self.shown() if e.data is not None and e.data.ndim == 2 and len(e.data)]
        ratio = self.ratioCheckBox.isChecked() and len(shown) > 1
        if ratio:
            gs = fig.add_gridspec(2, 1, height_ratios=[3, 1.3], hspace=0.08)
            ax = fig.add_subplot(gs[0])
            rax = fig.add_subplot(gs[1], sharex=ax)
        else:
            ax, rax = fig.add_subplot(111), None
        self.axes = [ax] + ([rax] if rax is not None else [])
        self.plotWidget.canvas.ax = ax
        for k, e in enumerate(shown):
            d = e.data
            err = d[:, 2] if d.shape[1] > 2 else None
            ax.errorbar(d[:, 0], d[:, 1], err, fmt='o-', ms=3, lw=0.8, color='C%d' % (k % 10), label=e.title())
        if shown:
            ax.set_yscale('log')
            ax.legend(fontsize='small', frameon=False)
        ax.set_ylabel(self.label())
        if rax is not None:
            ref = shown[0]
            for k, e in enumerate(shown[1:], start=1):
                q, r, s = compare.ratio(ref.data, e.data)
                if len(q):
                    rax.errorbar(q, r, s, fmt='o-', ms=3, lw=0.8, color='C%d' % (k % 10))
            rax.axhline(1.0, color='0.5', lw=0.8)
            rax.set_ylabel('ratio to %s' % ref.rid, fontsize='small')
            rax.set_xlabel('Qz (1/Å)')
            ax.tick_params(labelbottom=False)
        else:
            ax.set_xlabel('Qz (1/Å)')
        if not shown:
            ax.text(0.5, 0.5, 'Tick saved curves to compare them' if self.entries else
                    'No reflectivity saved in this workbook yet', ha='center', va='center',
                    transform=ax.transAxes, color='0.4')
        self.plotWidget.canvas.draw()
