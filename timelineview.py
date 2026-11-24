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
from PyQt5.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem, QGraphicsPathItem, QGraphicsRectItem,
                             QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView, QHBoxLayout, QLabel,
                             QPushButton, QVBoxLayout, QWidget)

AXIS_H = 22                                   # px at the top for the time axis
LANES = (('events', 'Events', 46), ('sx', 'sx (mm)', 46), ('height', 'Sample height', 54), ('scans', 'Scans', 34))
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


class TimelineView(QGraphicsView):
    """The lanes. ``scanClicked(n)`` when a scan bar or an sh scan is clicked."""
    scanClicked = pyqtSignal(int)

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
        self.items = {'scans': {}, 'heights': {}, 'events': [], 'steps': [], 'gaps': []}

    # ---- building

    def set_timeline(self, tl):
        sc = self.scene()
        sc.clear()
        self.items = {'scans': {}, 'heights': {}, 'events': [], 'steps': [], 'gaps': []}
        self.timeline = tl
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
        self._heights(tl)
        self._steps(tl)
        self._events(tl)
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
                tip = ('S# %d, sample-height scan (sx %s mm): %s. A usable scan is wide (about 65 µm or more) and '
                       'flatter than a Gaussian, p > 2 (owner, F78); no verdict is drawn: the thresholds are the '
                       'owner\'s to give. Click: open the scan with its fit.'
                       % (hs.scan, hs.sx, f.summary('µm', 1000.0)))
                item = self._marker(x, y + 14, 5, KIND_COLOURS['height'], tip, ('scan', hs.scan))
                self._label('%.0f µm' % (f.fwhm * 1000.0), x, y + 22, tip=tip)
                self._label('p %.1f' % f.p, x, y + 34, colour='#666666', tip=tip)
            else:
                tip = 'S# %d, sample-height scan: %s. Click: open the scan.' % (hs.scan, f.message)
                item = self._marker(x, y + 14, 5, '#bdbdbd', tip, ('scan', hs.scan), outline='#8c8c8c')
                self._label('no beam', x, y + 22, colour='#8c8c8c', tip=tip)
            self.items['heights'][hs.scan] = item

    def _steps(self, tl, motor='Sample_X'):
        y, h = lane_top('sx')
        track = tl.positions.get(motor, [])
        if not track:
            self._label('no sx in this file', 4, y + 14, colour='#8c8c8c')
            return
        lo, hi = min(v for _n, _t, v in track), max(v for _n, _t, v in track)
        scale = (h - 18) / (hi - lo) if hi > lo else 0.0

        def ypos(v):
            return y + h - 8 - (v - lo) * scale if scale else y + h / 2.0
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

    def _events(self, tl):
        y, h = lane_top('events')
        for e in tl.events:
            if e.kind == 'gap':
                continue
            x = self._x(e.t)
            colour = EVENT_COLOURS.get(e.kind, '#555555')
            local = self.clock(e.t, True)
            if e.kind == 'set-zero':
                line = self.scene().addLine(x, AXIS_H, x, total_height(), self._pen(colour, 1.6, Qt.DashLine))
                line.setZValue(5)
                tip = ('%s: %s reset from %g to 0 at %s (after scan %d). "set sh 0" is almost always a new sample, '
                       'occasionally the same one after conditions changed (owner, F83): a guess to confirm' %
                       (e.text, e.motor, e.old, local, e.after_scan))
                line.setToolTip(tip)
                self._label('new sample?', x + 0, y + 2, colour=colour, tip=tip, bold=True)
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
        top.addWidget(self.fitButton)
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

    def show_timeline(self, tl, name=''):
        self.view.set_timeline(tl)
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
