"""The sample timeline tab (F83, phase 1c): a view of lss_core.timeline.

Owner, 2026-11-24: a tab in the main window (docs/gui/questions.md). The
design is docs/gui/timeline/research.md section 5: lanes on one time axis
(the file's local clock), each with its label at the left:

- Events: "set sh 0: new sample?" as a red line through every lane;
  re-referencing (µm), aborts, macro files loaded, SPEC session restarts;
  gaps without scans shaded across every lane.
- sx: the sample's x position from each scan's #P, as steps.
- Sample height: each sh scan with its FWHM and p (F78), grey when the
  scan holds no reflected beam.
- Scans: bars from start to end, coloured by kind; aborted scans paler.

The wheel zooms the time axis only (about the cursor); drag pans;
double-click or "Fit all" shows everything. A click on a scan bar or an sh
scan selects that scan in the scan list. Tooltips everywhere (rule 9).
Drawn with QGraphicsScene (research §5: no new dependency; 3,000 bars draw
in milliseconds). Time is the scene's x in seconds from the first scan;
items that must not stretch (labels, markers) ignore the view's transform.
"""
import time

from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QTransform
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem, QGraphicsPathItem, QGraphicsRectItem,
                             QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView, QHBoxLayout, QLabel, QMenu,
                             QPushButton, QVBoxLayout, QWidget)

AXIS_H = 22                                   # px at the top for the time axis
LANES = (('events', 'Events', 46), ('sx', 'sx (mm)', 46), ('height', 'Sample height', 64), ('scans', 'Scans', 34),
         ('reduced', 'Reduced', 48), ('env', 'Environment', 56), ('notes', 'Notes', 34))
THUMB_W, THUMB_H = 64, 34                     # px: a sample-height scan's thumbnail
KIND_COLOURS = {'reflectivity': '#1f77b4', 'gid': '#2ca02c', 'height': '#9467bd', 'burn': '#d62728',
                'xfntr': '#ff7f0e', 'gisaxs': '#17becf', 'energy': '#bcbd22', 'other': '#8c8c8c'}
EVENT_COLOURS = {'set-zero': '#d00000', 'reset': '#e08000', 'abort': '#555555', 'macro': '#9a9a9a',
                 'session': '#000000'}
TICK_STEPS = (1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 10800, 21600, 43200, 86400)


def lane_top(key):
    y = AXIS_H
    for k, _label, h in LANES:
        if k == key:
            return y, h
        y += h
    raise KeyError(key)


def total_height():
    return AXIS_H + sum(h for _k, _l, h in LANES)


def tick_step(span_s, target=8):
    """A clock-friendly tick spacing (s) giving about ``target`` ticks over ``span_s``."""
    for s in TICK_STEPS:
        if span_s / s <= target:
            return s
    return TICK_STEPS[-1] * max(1, int(span_s / TICK_STEPS[-1] / target))


class HeightThumb(QGraphicsItem):
    """A sample-height scan drawn small: the data (grey) and its
    super-Gaussian fit (purple), at a fixed size in pixels (it ignores the
    zoom); framed purple when fitted, grey when there was no beam."""

    def __init__(self, x, y, model=None, ok=True):
        super().__init__()
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.points, self.fit = self._map(x, y, model)
        self.ok = ok

    @staticmethod
    def _map(x, y, model):
        import numpy as np
        if x is None or y is None or len(x) < 2:
            return [], []
        x, y = np.asarray(x, float), np.asarray(y, float)
        good = np.isfinite(x) & np.isfinite(y)
        x, y = x[good], y[good]
        if len(x) < 2 or np.ptp(x) == 0:
            return [], []
        xf = np.linspace(x.min(), x.max(), 60)
        yf = model(xf) if model is not None else None
        allv = np.r_[y, yf] if yf is not None else y
        lo, hi = float(np.min(allv)), float(np.max(allv))
        span = hi - lo if hi > lo else 1.0

        def pts(xx, yy):
            return [((xi - x.min()) / np.ptp(x) * (THUMB_W - 6) + 3, THUMB_H - 3 - (yi - lo) / span * (THUMB_H - 6))
                    for xi, yi in zip(xx, yy)]
        return pts(x, y), (pts(xf, yf) if yf is not None else [])

    def boundingRect(self):
        return QRectF(0, 0, THUMB_W, THUMB_H)

    def paint(self, painter, option, widget=None):
        from PyQt5.QtCore import QPointF
        painter.setBrush(QBrush(QColor('white')))
        painter.setPen(QPen(QColor(KIND_COLOURS['height'] if self.ok else '#bdbdbd'), 1.2))
        painter.drawRect(self.boundingRect())
        if self.points:
            painter.setPen(QPen(QColor('#555555'), 1.0))
            painter.drawPolyline(*[QPointF(px, py) for px, py in self.points])
        if self.fit:
            painter.setPen(QPen(QColor(KIND_COLOURS['height']), 1.4))
            painter.drawPolyline(*[QPointF(px, py) for px, py in self.fit])


class ResultThumb(HeightThumb):
    """A saved result's thumbnail on the reduced lane (phase 1d): its first
    two columns (log R against Qz for a reflectivity; I against Qz for
    fluorescence, whose first columns are frame and Qz; none for a GID map,
    a 2D map), framed in its kind's colour; amber and dashed when out of
    date; a dashed grey box saying why for a placeholder."""

    def __init__(self, item):
        import numpy as np
        d = item.data
        x = y = None
        if item.kind == 'gid map':
            d = None                       # a map, not a curve: the framed box only (2026-11-26)
        if d is not None and getattr(d, 'ndim', 0) == 2 and d.shape[0] > 1 and d.shape[1] > 1:
            x, y = d[:, 0], d[:, 1]
            if item.kind == 'fluorescence' and d.shape[1] >= 4:
                x, y = d[:, 1], d[:, 3]    # Qz and I (columns frame, Qz, E, I, dI[, I_xeray, dI_xeray])
            if item.kind == 'reflectivity':
                with np.errstate(divide='ignore', invalid='ignore'):
                    y = np.where(y > 0, np.log10(np.where(y > 0, y, 1.0)), np.nan)
        super().__init__(x, y, None, True)
        self.item = item

    def paint(self, painter, option, widget=None):
        from PyQt5.QtCore import QPointF
        it = self.item
        kind = {'gid map': 'gid', 'gid cut': 'gid', 'burn test': 'burn', 'fluorescence': 'xfntr'}.get(it.kind, it.kind)
        colour = KIND_COLOURS.get(kind, KIND_COLOURS['other'])
        if it.placeholder:
            painter.setBrush(QBrush(QColor('#f4f4f4')))
            painter.setPen(QPen(QColor('#9a9a9a'), 1.0, Qt.DashLine))
            painter.drawRect(self.boundingRect())
            painter.setPen(QPen(QColor('#666666')))
            f = QFont()
            f.setPointSize(7)
            painter.setFont(f)
            painter.drawText(self.boundingRect(), Qt.AlignCenter | Qt.TextWordWrap, it.placeholder)
            return
        painter.setBrush(QBrush(QColor('white')))
        painter.setPen(QPen(QColor('#e08000' if it.stale else colour), 1.4, Qt.DashLine if it.stale else Qt.SolidLine))
        painter.drawRect(self.boundingRect())
        if self.points:
            painter.setPen(QPen(QColor(colour), 1.0))
            painter.drawPolyline(*[QPointF(px, py) for px, py in self.points])


class TimelineView(QGraphicsView):
    """The lanes. ``scanClicked(n)`` when a scan bar or an sh scan is clicked."""
    scanClicked = pyqtSignal(int)
    resultClicked = pyqtSignal(str)                 # a saved result's id (the reduced lane)
    answerGiven = pyqtSignal(float, int, str)       # a set-zero's time, the scan before it, the answer
    noteWanted = pyqtSignal(float)                  # the time a note is to be added at

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('timelineView')
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setMinimumHeight(total_height() + 24)
        self.setMaximumHeight(total_height() + 40)           # the lanes, a scroll bar, no empty canvas
        self.timeline = None
        self.t0 = 0.0
        self.span = 1.0
        self.offset = 0.0
        self.items = {'scans': {}, 'heights': {}, 'events': [], 'steps': [], 'gaps': [], 'notes': [], 'set_zero': []}
        self.notes = []
        self.answer_of = lambda event: ''
        self.dose = None                 # F107: a lss_core.timeline.DoseTrack, drawn over the sx line
        self.reduced = []                # phase 1d: lss_core.timeline.Reduced items, the reduced lane
        self.env = None                  # phase 2: a lss_core.timeline.ColumnTrack, the environment lane
        self._sx_y = None

    # ---- building

    def set_timeline(self, tl, notes=()):
        from lss_core import timeline as timelinemod
        sc = self.scene()
        sc.clear()
        self.items = {'scans': {}, 'heights': {}, 'events': [], 'steps': [], 'gaps': [], 'notes': [], 'set_zero': [],
                      'dose': [], 'reduced': [], 'env': []}
        self.timeline = tl
        self.notes = list(notes)
        self.answer_of = timelinemod.answers(self.notes)
        t0, t1 = tl.range()
        if t0 is None:
            self.t0, self.span = 0.0, 1.0
            return
        times = [e.t for e in tl.events if e.t == e.t]           # events after the last scan too (macro loads)
        t0, t1 = min([t0] + times), max([t1] + times)
        self.t0, self.span = t0, max(t1 - t0, 1.0)
        self.offset = tl.utc_offset
        h = total_height()
        sc.setSceneRect(QRectF(-0.02 * self.span, 0, 1.04 * self.span, h))
        for key, _label, lh in LANES[1:]:                       # lane separators
            y, _ = lane_top(key)
            line = sc.addLine(-1e9, y, 1e9, y, self._pen('#e0e0e0'))
            line.setZValue(-10)
        self._gaps(tl)
        self._scans(tl)
        self._reduced()
        self._env()
        self._heights(tl)
        self._steps(tl)
        if self.dose is not None:
            self._dose(tl)
        self._events(tl)
        self._notes()
        self.fit_all()

    @staticmethod
    def _pen(colour, width=1.0, style=Qt.SolidLine):
        p = QPen(QColor(colour), width, style)
        p.setCosmetic(True)                                     # the same width at every zoom
        return p

    def _x(self, t):
        return t - self.t0

    def _label(self, text, x, y, colour='#333333', tip='', size=8, bold=False):
        item = QGraphicsSimpleTextItem(text)
        f = QFont()
        f.setPointSize(size)
        f.setBold(bold)
        item.setFont(f)
        item.setBrush(QBrush(QColor(colour)))
        item.setPos(x, y)
        item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        if tip:
            item.setToolTip(tip)
        self.scene().addItem(item)
        return item

    def _marker(self, x, y, r, colour, tip, data=None, outline=None):
        item = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
        item.setPos(x, y)
        item.setBrush(QBrush(QColor(colour)))
        item.setPen(self._pen(outline or colour))
        item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        item.setToolTip(tip)
        if data is not None:
            item.setData(0, data)
            item.setCursor(Qt.PointingHandCursor)
        self.scene().addItem(item)
        return item

    def _gaps(self, tl):
        for e in tl.of_kind('gap'):
            r = self.scene().addRect(QRectF(self._x(e.t), AXIS_H, e.duration or 0.0, total_height() - AXIS_H),
                                     QPen(Qt.NoPen), QBrush(QColor(0, 0, 0, 18), Qt.BDiagPattern))
            r.setZValue(-5)
            r.setToolTip('%s (after scan %d): the chamber opened, the hutch entered or the session paused; a gap '
                         'alone does not mean a new sample' % (e.text, e.after_scan))
            self.items['gaps'].append(r)

    def _scans(self, tl):
        y, h = lane_top('scans')
        for s in tl.spans:
            c = QColor(KIND_COLOURS.get(s.kind, KIND_COLOURS['other']))
            if s.aborted:
                c.setAlpha(90)
            r = QGraphicsRectItem(self._x(s.t0), y + 6, max(s.t1 - s.t0, 1.0), h - 12)
            r.setBrush(QBrush(c))
            r.setPen(self._pen(c.darker(130).name()))
            r.setToolTip('S# %d  %s\n%d points, %s%s, %s to %s (local clock). Click: select the scan.'
                         % (s.scan, s.command, s.points, s.kind, ', aborted' if s.aborted else '',
                            self.clock(s.t0, True), self.clock(s.t1, True)))
            r.setData(0, ('scan', s.scan))
            r.setCursor(Qt.PointingHandCursor)
            self.scene().addItem(r)
            self.items['scans'][s.scan] = r

    def _heights(self, tl):
        y, h = lane_top('height')
        for hs in tl.heights:
            f = hs.fit
            x = self._x(hs.t)
            if f.ok:
                tip = ('S# %d, sample-height scan (sx %s mm): %s. Grey: Pilatus/Monc; purple: the super-Gaussian. '
                       'A usable scan is wide (about 65 µm or more) and flatter than a Gaussian, p > 2 (owner, F78); '
                       'no verdict is drawn: the thresholds are the owner\'s to give. Click: open the scan with its fit.'
                       % (hs.scan, hs.sx, f.summary('µm', 1000.0)))
                text = '%.0f µm · p %.1f' % (f.fwhm * 1000.0, f.p)
            else:
                tip = 'S# %d, sample-height scan: %s. Click: open the scan.' % (hs.scan, f.message)
                text = 'no beam'
            item = HeightThumb(hs.x, hs.y, f.model if f.ok else None, f.ok)
            item.setPos(x, y + 4)
            item.setToolTip(tip)
            item.setData(0, ('scan', hs.scan))
            item.setCursor(Qt.PointingHandCursor)
            self.scene().addItem(item)
            self._label(text, x, y + 4 + THUMB_H + 2, colour='#333333' if f.ok else '#8c8c8c', tip=tip, size=7)
            self.items['heights'][hs.scan] = item

    def _steps(self, tl, motor='Sample_X'):
        y, h = lane_top('sx')
        track = tl.positions.get(motor, [])
        self._sx_y = None
        if not track:
            self._label('no sx in this file', 4, y + 14, colour='#8c8c8c')
            return
        lo, hi = min(v for _n, _t, v in track), max(v for _n, _t, v in track)
        scale = (h - 18) / (hi - lo) if hi > lo else 0.0

        def ypos(v):
            return y + h - 8 - (v - lo) * scale if scale else y + h / 2.0
        self._sx_y = ypos
        path = QPainterPath()
        path.moveTo(self._x(track[0][1]), ypos(track[0][2]))
        for (_na, _ta, va), (_nb, tb, vb) in zip(track, track[1:]):
            path.lineTo(self._x(tb), ypos(va))
            path.lineTo(self._x(tb), ypos(vb))
        path.lineTo(self._x(max(s.t1 for s in tl.spans)), ypos(track[-1][2]))
        item = QGraphicsPathItem(path)
        item.setPen(self._pen('#444444', 1.5))
        item.setToolTip('sx (Sample_X) at the start of each scan, from its #P line, %g to %g mm: a move between '
                        'scans is dated only to the interval between them (research §3)' % (lo, hi))
        self.scene().addItem(item)
        self.items['sx_path'] = item
        self._label('%g' % track[0][2], self._x(track[0][1]), ypos(track[0][2]) - 14, colour='#666666')
        for st in tl.steps:
            tip = ('sx %g → %g mm before S# %d, between %s and %s (local clock); a large sx move calls for a new '
                   'sample-height scan (owner, F78)' % (st.old, st.new, st.scan, self.clock(st.t_before, True),
                                                       self.clock(st.t_after, True)))
            self.items['steps'].append(self._label('%g' % st.new, self._x(st.t_after), ypos(st.new) - 14, tip=tip))

    def set_reduced(self, items):
        """The reduced lane's items (lss_core.timeline.reduced_items), redrawn."""
        self.reduced = list(items or [])
        if self.timeline is not None:
            keep = self.transform(), self.horizontalScrollBar().value()
            self.set_timeline(self.timeline, self.notes)
            self.setTransform(keep[0])
            self.horizontalScrollBar().setValue(keep[1])

    def _reduced(self):
        """Each saved result as a thumbnail at its scans' start, a bar under it
        to their end; placeholders for series not reduced (research §4)."""
        y, h = lane_top('reduced')
        if not self.reduced:
            self._label('nothing saved yet', 4, y + 14, colour='#8c8c8c')
            return
        for it in self.reduced:
            scans = ', '.join(str(n) for n in it.scans)
            if it.placeholder:
                tip = ('%s series %s (S# %s): %s. Click: select its first scan.'
                       % (it.kind, it.series, scans, it.placeholder))
                data = ('scan', it.scans[0])
            else:
                tip = ('%s %s v%d (%s), S# %s, saved %s%s%s%s. Click: open it%s.'
                       % (it.rid, it.kind, it.version, it.label or '-', scans, it.saved,
                          ', automatically' if it.origin == 'auto' else '',
                          '; out of date: its scans have grown since' if it.stale else '',
                          '\nNote: ' + it.note if it.note else '',
                          ' on the Compare tab' if it.kind == 'reflectivity' else ' (its scans are selected)'))
                data = ('result', it.rid)
            bar = QGraphicsRectItem(self._x(it.t0), y + h - 6, max(self._x(it.t1) - self._x(it.t0), 1e-9), 3)
            bar.setBrush(QBrush(QColor('#bdbdbd')))
            bar.setPen(QPen(Qt.NoPen))
            bar.setToolTip(tip)
            self.scene().addItem(bar)
            thumb = ResultThumb(it)
            thumb.setPos(self._x(it.t0), y + 4)
            thumb.setToolTip(tip)
            thumb.setData(0, data)
            thumb.setCursor(Qt.PointingHandCursor)
            self.scene().addItem(thumb)
            self.items['reduced'].append(thumb)

    def set_env(self, track):
        """The environment lane's column (lss_core.timeline.column_track), or None."""
        self.env = track
        if self.timeline is not None:
            keep = self.transform(), self.horizontalScrollBar().value()
            self.set_timeline(self.timeline, self.notes)
            self.setTransform(keep[0])
            self.horizontalScrollBar().setValue(keep[1])

    def _env(self):
        """The chosen column as a strip chart, one line per scan (no line drawn
        across the time between scans), scaled to the lane."""
        import numpy as np
        y, h = lane_top('env')
        tr = self.env
        if tr is None:
            self._label('choose a column above (F75: tensiometer, barrier, O₂ when the macros write them)', 4,
                        y + 18, colour='#8c8c8c')
            return
        good = np.isfinite(tr.y) & np.isfinite(tr.t)
        if not good.any():
            self._label('%s: no values with a time' % tr.name, 4, y + 18, colour='#8c8c8c')
            return
        lo, hi = float(np.min(tr.y[good])), float(np.max(tr.y[good]))
        scale = (h - 14) / (hi - lo) if hi > lo else 0.0
        unit = ' %s' % tr.unit if tr.unit else ''
        tip = ('%s%s, %.4g to %.4g, at the middle of each point\'s count, from the SPEC columns (%d points); '
               'one line per scan' % (tr.name, unit, lo, hi, int(good.sum()))) + (
               '\n' + '; '.join(tr.notes) if tr.notes else '')
        for n in np.unique(tr.scans[good]):
            sel = good & (tr.scans == n)
            ts, vs = tr.t[sel], tr.y[sel]
            path = QPainterPath()
            for k, (t, v) in enumerate(zip(ts, vs)):
                py = y + h - 7 - (v - lo) * scale if scale else y + h / 2.0
                (path.moveTo if k == 0 else path.lineTo)(self._x(float(t)), py)
            item = QGraphicsPathItem(path)
            item.setPen(self._pen('#00838f', 1.4))
            item.setToolTip('S# %d · %s' % (int(n), tip))
            self.scene().addItem(item)
            self.items['env'].append(item)
        self._label('%s%s  %.4g – %.4g' % (tr.name, unit, lo, hi), 4, y + 1, colour='#00838f', tip=tip, size=7)

    def set_dose(self, track):
        """Colour the sx line by the dose each spot has received (F107), or
        not (None)."""
        self.dose = track
        if self.timeline is not None:
            keep = self.transform(), self.horizontalScrollBar().value()
            self.set_timeline(self.timeline, self.notes)
            self.setTransform(keep[0])
            self.horizontalScrollBar().setValue(keep[1])

    def _dose(self, tl):
        """Each scan's span over the sx line, coloured by its spot's dose so far
        as a fraction of the burn test's dose to a 5 % change
        (lss_core.timeline.dose_colour: teal 0, yellow 50 %, red 100 %, dark red
        200 % and above; grey without a scale)."""
        from lss_core import timeline as timelinemod
        if self._sx_y is None or not self.dose.rows:
            return
        tr = self.dose
        for r in tr.rows:
            y = self._sx_y(r.sx)
            line = QGraphicsLineItem(self._x(r.t0), y, self._x(r.t1), y)
            line.setPen(self._pen(QColor(*timelinemod.dose_colour(r.fraction)), 5.0))
            line.setZValue(2)
            sc = tr.scales.get(r.burn) if r.burn is not None else None
            line.setToolTip('S# %d at sx %g mm (spot %d): %.3g %s during the scan, %.3g at this spot so far%s'
                            % (r.scan, r.sx, r.spot + 1, r.dose, tr.unit, r.cumulative,
                               ('\n= %s%.0f %% of %s%s' % ('≤ ' if sc.lower_bound else '', 100 * r.fraction,
                                                          sc.describe(tr.unit),
                                                          '' if r.own else ' (the nearest burn in time: this sample '
                                                                           'has none of its own)'))
                               if sc is not None and r.fraction is not None else '\nno burn test to scale it by'))
            line.setData(0, r.scan)
            self.scene().addItem(line)
            self.items['dose'].append(line)

    def _events(self, tl):
        y, h = lane_top('events')
        for e in tl.events:
            if e.kind == 'gap':
                continue
            x = self._x(e.t)
            colour = EVENT_COLOURS.get(e.kind, '#555555')
            local = self.clock(e.t, True)
            if e.kind == 'set-zero':
                answer = self.answer_of(e)
                if answer == 'same sample':
                    colour = '#8c8c8c'
                style = Qt.DashLine if not answer else Qt.SolidLine
                line = self.scene().addLine(x, AXIS_H, x, total_height(), self._pen(colour, 1.6, style))
                line.setZValue(5)
                tip = ('%s: %s reset from %g to 0 at %s (after scan %d). "set sh 0" is almost always a new sample, '
                       'occasionally the same one after conditions changed (owner, F83). %s Right-click to answer; '
                       'the answer is kept in the workbook as a note.' %
                       (e.text, e.motor, e.old, local, e.after_scan,
                        ('Answered: %s.' % answer) if answer else 'Not answered yet: a guess to confirm.'))
                line.setToolTip(tip)
                line.setData(0, ('set-zero', len(self.items['set_zero'])))
                lab = self._label(answer or 'new sample?', x + 0, y + 2, colour=colour, tip=tip, bold=True)
                lab.setData(0, ('set-zero', len(self.items['set_zero'])))
                self.items['set_zero'].append((e, line, lab))
                self.items['events'].append(line)
            elif e.kind == 'reset':
                tip = ('%s at %s (after scan %d): re-referenced by %+.1f µm' %
                       (e.text, local, e.after_scan, 1000.0 * (e.shift or 0.0)))
                self.items['events'].append(self._marker(x, y + 26, 3.5, colour, tip))
                self._label('%+.1f µm' % (1000.0 * (e.shift or 0.0)), x, y + 30, colour=colour, tip=tip, size=7)
            elif e.kind == 'abort':
                tip = '%s at %s (scan %d)' % (e.text, local, e.after_scan)
                self.items['events'].append(self._label('×', x, y + 16, colour=colour, tip=tip, size=10, bold=True))
            elif e.kind == 'session':
                line = self.scene().addLine(x, AXIS_H, x, total_height(), self._pen(colour, 1.0, Qt.DotLine))
                line.setToolTip('%s before scan %d' % (e.text, e.after_scan + 1))
                self.items['events'].append(line)
            else:                                                  # a macro file loaded
                tip = '%s at %s (%s)' % (e.text, local, 'file header' if e.after_scan == 0 else
                                          'after scan %d' % e.after_scan)
                self.items['events'].append(self._marker(x, y + 40, 2.0, colour, tip))

    def _notes(self):
        y, h = lane_top('notes')
        for n in self.notes:
            if n.event:
                continue                                           # an answer: shown on its event
            x = self._x(n.t0)
            tip = '%s\n%s\n(note %s v%d in the workbook, at %s)' % (n.label, n.text, n.rid, n.version,
                                                                     self.clock(n.t0, True))
            if n.t1 is not None and n.t1 > n.t0:
                r = self.scene().addRect(QRectF(x, y + 4, n.t1 - n.t0, h - 8), QPen(Qt.NoPen),
                                         QBrush(QColor(255, 230, 120, 120)))
                r.setToolTip(tip)
            box = self._label(n.label[:40], x, y + 8, colour='#5a4500', tip=tip)
            box.setData(0, ('note', n.rid))
            self.items['notes'].append(box)

    def contextMenuEvent(self, ev):
        """Right-click: answer a "new sample?", or add a note at that time."""
        item = self.itemAt(ev.pos())
        data = item.data(0) if item is not None else None
        t = self.t0 + self.mapToScene(ev.pos()).x()
        menu = QMenu(self)
        if isinstance(data, tuple) and data[:1] == ('set-zero',):
            e = self.items['set_zero'][data[1]][0]
            for answer in ('new sample', 'same sample'):
                act = menu.addAction('A new sample' if answer == 'new sample' else 'The same sample')
                act.triggered.connect(lambda _=False, a=answer, e=e: self.answerGiven.emit(float(e.t), int(e.after_scan), a))
            menu.addSeparator()
        act = menu.addAction('Add a note here…')
        act.triggered.connect(lambda _=False, t=t: self.noteWanted.emit(float(t)))
        self.contextMenu = menu
        menu.exec_(ev.globalPos())

    # ---- viewing

    def clock(self, t, seconds=False):
        """The file's local clock at Unix time t."""
        return time.strftime('%H:%M:%S' if seconds else '%H:%M', time.gmtime(t + self.offset))

    def fit_all(self):
        w = max(self.viewport().width(), 100)
        self.setTransform(QTransform.fromScale(w / (1.04 * self.span), 1.0))
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().minimum())
        self.centerOn(self.span / 2.0, total_height() / 2.0)
        self.viewport().update()

    def zoom(self, factor):
        m = self.transform().m11()
        factor = max(min(factor, 2000.0 / m), 1e-4 / m)             # 1 px per 2 ms down to 1 px per 3 h
        self.scale(factor, 1.0)
        self.viewport().update()

    def wheelEvent(self, ev):
        steps = ev.angleDelta().y() / 120.0
        if steps:
            self.zoom(1.25 ** steps)
        ev.accept()

    def mouseDoubleClickEvent(self, ev):
        self.fit_all()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            item = self.itemAt(ev.pos())
            data = item.data(0) if item is not None else None
            if isinstance(data, tuple) and data[:1] == ('scan',):
                self.scanClicked.emit(int(data[1]))
                ev.accept()
                return
            if isinstance(data, tuple) and data[:1] == ('result',):
                self.resultClicked.emit(str(data[1]))
                ev.accept()
                return
        super().mousePressEvent(ev)

    def resizeEvent(self, ev):
        refit = self.timeline is not None and abs(self.visible_span() - 1.04 * self.span) < 1e-6 * self.span + 1
        super().resizeEvent(ev)
        if refit:
            self.fit_all()

    def visible_span(self):
        m = self.transform().m11()
        return self.viewport().width() / m if m else 0.0

    def drawForeground(self, painter, rect):
        """The time axis, on the local clock, at the top of the viewport."""
        if self.timeline is None or self.timeline.range()[0] is None:
            return
        painter.save()
        painter.resetTransform()
        vw = self.viewport().width()
        left, right = self.mapToScene(0, 0).x(), self.mapToScene(vw, 0).x()
        painter.fillRect(0, 0, vw, AXIS_H - 4, QColor(250, 250, 250))
        step = tick_step(max(right - left, 1.0))
        first = self.t0 + left
        local0 = first + self.offset
        t = (int(local0 // step) + 1) * step - self.offset
        painter.setPen(QColor('#555555'))
        f = painter.font()
        f.setPointSize(8)
        painter.setFont(f)
        while t < self.t0 + right:
            x = self.mapFromScene(t - self.t0, 0).x()
            painter.drawLine(x, AXIS_H - 8, x, AXIS_H - 4)
            painter.drawText(x + 2, AXIS_H - 9, self.clock(t, step < 60))
            t += step
        painter.restore()


class TimelineTab(QWidget):
    """The tab: a toolbar line (Fit all, what is shown), the lane labels and the view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('timelineTab')
        v = QVBoxLayout(self)
        top = QHBoxLayout()
        self.fitButton = QPushButton('Fit all', self)
        self.fitButton.setObjectName('timelineFitPushButton')
        self.fitButton.setToolTip('Show the whole file. The wheel zooms the time axis about the cursor, a drag pans, '
                                  'a double-click fits too.')
        self.infoLabel = QLabel('', self)
        self.infoLabel.setObjectName('timelineInfoLabel')
        self.doseCheckBox = QCheckBox('Dose', self)
        self.doseCheckBox.setObjectName('timelineDoseCheckBox')
        self.doseCheckBox.setToolTip(
            'Colour the sx line by the dose each spot has received, as a fraction of the dose at which the burn '
            'test changes by 5 % (F107): teal none, yellow half, red the burn\'s dose, dark red twice it. The '
            'burn is the sample\'s own (between the same two "new sample?" guesses) or else the nearest in time. '
            'Assumptions: one beam for the file (then its size cancels), positions within half the beam\'s width '
            'are one spot, every scan counts in full. Analysing the burns takes a few seconds')
        self.envComboBox = QComboBox(self)
        self.envComboBox.setObjectName('timelineEnvComboBox')
        self.envComboBox.setToolTip(
            'The column drawn on the Environment lane, over every scan that has it, at the middle of each point\'s '
            'count. The tensiometer, barrier and O₂ readings will be columns once the macros write them (F75; '
            'units: mN/m, cm², %); names that look like them are listed first. Any other column works too, e.g. '
            'Monc to see the beam over the session')
        top.addWidget(self.fitButton)
        top.addWidget(self.doseCheckBox)
        top.addWidget(self.envComboBox)
        top.addWidget(self.infoLabel, 1)
        v.addLayout(top)
        body = QHBoxLayout()
        labels = QVBoxLayout()
        labels.setSpacing(0)
        labels.addSpacing(AXIS_H)
        for key, text, h in LANES:
            lab = QLabel(text, self)
            lab.setFixedHeight(h)
            lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lab.setStyleSheet('color: #444; padding-right: 4px;')
            labels.addWidget(lab)
        labels.addStretch(1)
        body.addLayout(labels)
        self.view = TimelineView(self)
        body.addWidget(self.view, 1)
        v.addLayout(body)
        v.addStretch(1)
        self.fitButton.clicked.connect(self.view.fit_all)

    def show_timeline(self, tl, name='', notes=()):
        self.view.set_timeline(tl, notes)
        t0, t1 = tl.range()
        if t0 is None:
            self.infoLabel.setText('No scan of this file has a time.')
            self.infoLabel.setToolTip('\n'.join(tl.notes))
            return
        n_new = len(tl.of_kind('set-zero'))
        text = '%s: %d scans, %s to %s%s' % (name, len(tl.spans), self.view.clock(t0), self.view.clock(t1),
                                             ', %d "set sh 0" (new sample?)' % n_new if n_new else '')
        self.infoLabel.setText(text)
        self.infoLabel.setToolTip('Read from the SPEC file (lss_core.timeline): scan spans from #D and Epoch '
                                  '(or Tstart/Tend), events from the dated #C lines, sx from #P, sample-height '
                                  'scans with their super-Gaussian fits (F78). Times on the file\'s local clock.'
                                  + ('\nNotes: ' + '; '.join(tl.notes) if tl.notes else ''))

    def show_message(self, text):
        self.view.scene().clear()
        self.view.timeline = None
        self.infoLabel.setText(text)
        self.infoLabel.setToolTip('')
