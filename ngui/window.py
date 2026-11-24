"""NguiWindow: the prototype of the new layout, built from layout.py.

Every control of today's window appears as a disabled placeholder of the
right kind, with a tooltip saying where it was, what it does and that the
prototype does nothing (AGENTS.md rule 9). Plots are painted sketches. A few
elements work so that the sketch can be explored: the View menu (panes),
folding groups, the residuals toggles, the Split toggle of the frame viewer,
the Legacy… buttons, File > Export…, File > Preferences… and Help > Retired
controls. No data are read and nothing from lss_core is imported.
"""
import math

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient, QFont
from PyQt5.QtWidgets import (QAction, QCheckBox, QComboBox, QDialog, QDockWidget, QDoubleSpinBox, QFrame,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QMainWindow, QMenu,
                             QPlainTextEdit, QProgressBar, QPushButton, QRadioButton, QScrollArea, QSizePolicy,
                             QSlider, QSplitter, QTableWidget, QTableWidgetItem, QTabWidget, QToolButton,
                             QVBoxLayout, QWidget)

from . import layout as L
from . import theme
from .inventory_text import COMBO_ITEMS, INVENTORY

TITLE = 'LSS Reader — ngui (prototype)'
SIZE = (1440, 900)
LEFT_W = 336        # the left column of groups in every tab
DOCK_W = 250        # the selection panel

NOT_FUNCTIONAL = 'Prototype: not functional.'

# a few rows so that lists read as what they will hold (invented, not data)
SAMPLES = {
    'scanListWidget': ['S# 6  rdef  Qz 0.01–0.05  (reflectivity)', 'S# 7  rdef  Qz 0.05–0.15', 'S# 8  rdef  Qz 0.15–0.35',
                       'S# 9  rdef  Qz 0.35–0.60', 'S# 12  ascan sh', 'S# 22  GID level 1', 'S# 40  burn (41 frames)'],
    'imageListWidget': ['S# 6 pt 0  Qz 0.010  abs 0', 'S# 6 pt 1  Qz 0.012  abs 0', 'S# 6 pt 2  Qz 0.014  abs 0',
                        'S# 7 pt 0  Qz 0.050  abs 2', 'S# 7 pt 1  Qz 0.055  abs 2', '…'],
    'backgroundListWidget': [],
    'refRefFileListWidget': ['#1  2026-09-23 water_ref.txt'],
    'ngui_ref_savedList': ['R0007 v2  S# 6–9  10:42', 'R0005 v1  S# 1–4  09:15'],
    'refDataListWidget': ['Qz        R          σR', '0.0100  9.98e-01  1.2e-02', '0.0120  1.00e+00  1.1e-02', '…'],
    'refNormRefListWidget': ['Qz        R/R0      σ        %', '0.0100  1.00e+00  1.2e-02  1.2', '…'],
    'refQzListWidget': ['Qz= 0.0100 {6:0} Abs= 0', 'Qz= 0.0120 {6:1} Abs= 0', '…'],
    'mcaDataListWidget': ['Qz       I          σ', '0.010  1.21e+03  3.5e+01', '0.012  1.25e+03  3.5e+01', '…'],
    'mcaFileListWidget': [],
    'plotFileListWidget': ['#1  run3/water_ref.txt', '#2  run3/lipid_ref.txt', '#3  run3/gid_map.txt'],
    'scanInfoDialog.impInfoTextBrowser': ['#S 12 ascan sh -0.2 0.2 40 1', 'Energy 10.0 keV · abs 0',
                                          'sh 0.0000 · Det_Th 0.00'],
    'pilPeakCenDialog.peakCenTextBrowser': ['S# 8 pt 3: centre 2 px off the ROI centre'],
    'pilBadPixDialog.peakCenTextBrowser': ['S# 9 pt 10: 1 hot pixel in the ROI (corrected)'],
}
TABLE_HEADERS = {
    'gidJoinTable': ['join', 'direction', 'from', 'to', 'points', 'factor', 'χ²/dof'],
    'prefFoilTable': ['units', 'nominal µm', 'calibrated µm', '± µm'],
    'plotscale.scaleTW': ['x ×', 'x +', 'y ×', 'y +'],
    'peakfit.peakTW': ['peak', 'centre', 'width', 'height'],
    'peakfit.bgTW': ['order', 'value'],
}


def _oname(key):
    return 'ngui_' + str(key).replace('.', '_')


def tooltip(item, functional=None):
    """The placeholder's tooltip: was, does, the change, and that it does nothing."""
    end = functional or NOT_FUNCTIONAL
    note = item.get('note') or ''
    if 'id' in item and item['id'] in INVENTORY:
        kind, label, where, does = INVENTORY[item['id']]
        text = 'Was: %s (%s). Does: %s.' % (where, label or item['id'], does.rstrip('.'))
        if note:
            text += ' Here: %s.' % note.rstrip('.')
        return '%s %s' % (text, end)
    return 'New in ngui%s. %s' % ((': ' + note.rstrip('.')) if note else '', end)


def _kind(item):
    if item.get('kind'):
        return item['kind']
    if 'id' in item and item['id'] in INVENTORY:
        return INVENTORY[item['id']][0]
    return 'label'


def _label(item):
    if item.get('label') is not None:
        return item['label']
    if 'id' in item and item['id'] in INVENTORY:
        return INVENTORY[item['id']][1]
    return ''


def _key(item):
    return item['id'] if 'id' in item else item.get('new') or item.get('name') or 'x'


# ---------------------------------------------------------------- painted plot sketches

class PlotSketch(QWidget):
    """A cheap drawing standing for a plot: a frame, a caption and a curve or image of the right shape."""

    def __init__(self, caption, sketch, parent=None):
        super().__init__(parent)
        self.caption = caption
        self.sketch = sketch
        self.band = sketch == 'frame'
        self.setMinimumSize(120, 70)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def sizeHint(self):
        return QSize(400, 220)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(1, 1, -2, -2)
        dark = self.sketch in ('frame', 'map', 'gisaxs', 'roi')
        p.setPen(QPen(QColor(theme.BORDER)))
        p.setBrush(QColor('#ffffff'))
        p.drawRect(r)
        top = 20
        area = r.adjusted(34, top, -10, -18)
        if area.width() < 20 or area.height() < 20:
            p.end()
            return
        if dark:
            self._image(p, area)
        else:
            self._axes(p, area)
            self._curve(p, area)
        p.setPen(QColor(theme.MUTED))
        f = QFont(self.font())
        f.setPointSizeF(8.5)
        p.setFont(f)
        p.drawText(r.adjusted(8, 3, -6, 0), Qt.AlignLeft | Qt.AlignTop, self.caption)
        p.end()

    def _axes(self, p, a):
        p.setPen(QPen(QColor('#9aa1ad'), 1))
        p.drawLine(a.bottomLeft(), a.bottomRight())
        p.drawLine(a.bottomLeft(), a.topLeft())
        p.setPen(QPen(QColor('#eceef2'), 1, Qt.DotLine))
        for k in range(1, 4):
            y = a.top() + k * a.height() / 4
            p.drawLine(int(a.left()) + 1, int(y), a.right(), int(y))

    def _pts(self, a, f, n=80, x0=0.0, x1=1.0):
        out = []
        for k in range(n + 1):
            x = x0 + (x1 - x0) * k / n
            y = max(0.0, min(1.0, f(x)))
            out.append((a.left() + (x - x0) / (x1 - x0) * a.width(), a.bottom() - y * a.height()))
        return out

    def _line(self, p, pts, colour, width=1.6, style=Qt.SolidLine):
        p.setPen(QPen(QColor(colour), width, style))
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            p.drawLine(int(x0), int(y0), int(x1), int(y1))

    def _dots(self, p, pts, colour, step=3, r=2):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(colour))
        for x, y in pts[::step]:
            p.drawEllipse(int(x) - r, int(y) - r, 2 * r, 2 * r)

    def _curve(self, p, a):
        s = self.sketch
        acc = theme.ACCENT
        if s == 'ref':
            f = lambda x: 0.95 if x < 0.12 else 0.95 - 0.75 * (x - 0.12) ** 0.6 + 0.03 * math.sin(28 * x) * x
            self._dots(p, self._pts(a, f, 90), acc, 2)
            self._line(p, self._pts(a, f, 90), '#e07b39', 1.2)
        elif s == 'peak':
            for k, c in enumerate((acc, '#3c9d5d', '#e07b39')):
                f = lambda x, k=k: 0.05 + (0.85 - 0.15 * k) * math.exp(-((x - 0.5 - 0.03 * k) / 0.11) ** 2)
                self._dots(p, self._pts(a, f, 60), c, 2, 2)
            self._line(p, self._pts(a, lambda x: 0.05 + 0.85 * math.exp(-((x - 0.5) / 0.11) ** 2)), '#333', 1)
        elif s == 'trend':
            import random
            rnd = random.Random(4)
            pts = self._pts(a, lambda x: 0.6 + 0.04 * rnd.uniform(-1, 1) - 0.02 * x, 40)
            self._dots(p, pts, acc, 1, 2)
            self._line(p, self._pts(a, lambda x: 0.6 - 0.02 * x, 2), '#e07b39', 1.4)
            self._line(p, self._pts(a, lambda x: 0.6 * math.exp(-0.08 * x), 30), '#8e5cc4', 1.2, Qt.DashLine)
        elif s == 'env':
            self._line(p, self._pts(a, lambda x: 0.7 + 0.05 * math.sin(6 * x)), '#3c9d5d', 1.4)
            self._line(p, self._pts(a, lambda x: 0.35 + 0.02 * math.cos(9 * x)), '#8e5cc4', 1.4)
            self._line(p, self._pts(a, lambda x: 0.15 + 0.1 * x), '#e07b39', 1.4)
        elif s == 'spectrum':
            f = lambda x: (0.05 + 0.8 * math.exp(-((x - 0.42) / 0.02) ** 2) + 0.35 * math.exp(-((x - 0.47) / 0.02) ** 2)
                           + 0.5 * math.exp(-((x - 0.8) / 0.03) ** 2) + 0.1 * math.exp(-x * 3))
            p.fillRect(int(a.left() + 0.38 * a.width()), a.top(), int(0.08 * a.width()), a.height(), QColor('#dfe9fb'))
            self._line(p, self._pts(a, f, 200), acc, 1.3)
        elif s == 'xfntr':
            f = lambda x: 0.1 + 0.75 / (1 + math.exp(-(x - 0.25) * 30)) - 0.25 * x
            self._dots(p, self._pts(a, f, 40), '#8e5cc4', 1, 2)
        elif s in ('cut', 'rod'):
            if s == 'cut':
                f = lambda x: 0.08 + 0.7 * math.exp(-((x - 0.35) / 0.04) ** 2) + 0.3 * math.exp(-((x - 0.7) / 0.05) ** 2)
            else:
                f = lambda x: 0.1 + 0.7 * math.exp(-((x - 0.3) / 0.25) ** 2)
            self._dots(p, self._pts(a, f, 80), acc, 2, 2)
            self._line(p, self._pts(a, f, 120), '#e07b39', 1.2)
        elif s == 'join':
            f = lambda x: 0.85 - 0.6 * x
            self._dots(p, self._pts(a, f, 20, 0, 0.6), acc, 1, 3)
            self._dots(p, self._pts(a, lambda x: f(x) + 0.01, 20, 0.4, 1.0), '#e07b39', 1, 3)
            self._line(p, self._pts(a, f, 2), '#333', 1)
        else:  # curves
            for k, c in enumerate((acc, '#3c9d5d', '#e07b39')):
                self._line(p, self._pts(a, lambda x, k=k: 0.2 + 0.15 * k + 0.25 * math.sin(4 * x + k)), c)

    def _image(self, p, a):
        g = QLinearGradient(a.topLeft(), a.bottomRight())
        g.setColorAt(0, QColor('#2d0f4d'))
        g.setColorAt(1, QColor('#1d1240'))
        p.fillRect(a, QBrush(g))
        s = self.sketch
        cx, cy = a.left() + a.width() * 0.5, a.top() + a.height() * 0.55
        if s == 'roi':
            # zoomed to the ROI and both background zones with a margin: diffuse scattering visible around them
            for rad, col in ((0.46, '#31336b'), (0.34, '#3b528b'), (0.22, '#2c728e'), (0.12, '#21918c'),
                             (0.06, '#5ec962'), (0.025, '#fde725')):
                rx, ry = rad * a.width(), rad * a.height() * 0.55
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(col))
                p.drawEllipse(int(cx - rx), int(cy - ry), int(2 * rx), int(2 * ry))
            w, h = a.width() * 0.16, a.height() * 0.22
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor('#ffffff'), 1.5))
            p.drawRect(int(cx - w / 2), int(cy - h / 2), int(w), int(h))
            p.setPen(QPen(QColor('#ffb000'), 1, Qt.DashLine))
            for sx in (-1, 1):
                p.drawRect(int(cx - w / 2 + sx * w * 1.25), int(cy - h / 2), int(w), int(h))
            p.setPen(QColor('#d8d8f0'))
            p.drawText(int(a.left()) + 4, int(a.bottom()) - 4, 'ROI + bkg zones + margin')
            return
        if s == 'frame':
            for rad, col in ((0.30, '#3b528b'), (0.18, '#21918c'), (0.09, '#5ec962'), (0.04, '#fde725')):
                rr = rad * min(a.width(), a.height())
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(col))
                p.drawEllipse(int(cx - rr * 1.4), int(cy - rr), int(2.8 * rr), int(2 * rr))
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor('#ffffff'), 1.5))
            w, h = a.width() * 0.16, a.height() * 0.2
            p.drawRect(int(cx - w / 2), int(cy - h / 2), int(w), int(h))
            p.setPen(QPen(QColor('#ffb000'), 1, Qt.DashLine))
            p.drawRect(int(cx - w / 2 + w * 1.4), int(cy - h / 2), int(w), int(h))
            if self.band:
                p.fillRect(int(a.left()), int(cy - a.height() * 0.05), a.width(), int(a.height() * 0.1),
                           QColor(255, 255, 255, 50))
                p.setPen(QColor('#ffffff'))
                p.drawText(int(a.left()) + 6, int(cy - a.height() * 0.06), 'cut band')
        elif s == 'map':
            n = 14
            for i in range(n):
                for j in range(8):
                    v = math.exp(-((i - 4) / 1.5) ** 2 - ((j - 2) / 3) ** 2) + 0.7 * math.exp(-((i - 10) / 1.2) ** 2 - (j / 4) ** 2)
                    c = QColor.fromHsvF(max(0.0, 0.72 - 0.6 * min(v, 1)), 0.85, 0.25 + 0.75 * min(v, 1))
                    p.fillRect(int(a.left() + i * a.width() / n), int(a.bottom() - (j + 1) * a.height() / 8),
                               int(a.width() / n) + 1, int(a.height() / 8) + 1, c)
        elif s == 'gisaxs':
            p.setPen(QPen(QColor('#fde725'), 2))
            p.drawLine(int(a.left()), int(cy), a.right(), int(cy))
            p.setPen(QPen(QColor('#21918c'), 6))
            p.drawLine(int(cx), a.top(), int(cx), a.bottom())


class ResidualsSketch(PlotSketch):
    def __init__(self, parent=None):
        super().__init__('(y − fit)/σ', 'residuals', parent)
        self.setMinimumHeight(40)

    def sizeHint(self):
        return QSize(400, 50)

    def _curve(self, p, a):
        import random
        rnd = random.Random(2)
        p.setPen(QPen(QColor('#9aa1ad'), 1, Qt.DashLine))
        p.drawLine(a.left(), int(a.center().y()), a.right(), int(a.center().y()))
        self._dots(p, self._pts(a, lambda x: 0.5 + 0.25 * rnd.uniform(-1, 1), 50), theme.ACCENT, 1, 2)


# ---------------------------------------------------------------- the window

class NguiWindow(QMainWindow):
    """Built from layout.py; see the module docstring for what works."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window)
        self.setObjectName('ngui_window')
        self.setWindowTitle(TITLE)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.controls = {}          # inventory id or new name -> widget or action
        self.folds = []             # (button, body) of foldable groups
        self.dialogs = {}
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)    # the panel keeps the full height
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self._build_dock()
        self._build_tabs()
        self._build_panes()
        self._build_status()
        self._build_menus()
        self._build_dialogs()        # hidden until asked for; built now so that every placed control exists
        theme.apply(self)
        self.resize(*SIZE)

    # ---- generic pieces

    def _widget(self, item, parent):
        """(widget, label text or None) for a control item."""
        key = _key(item)
        kind = _kind(item)
        label = _label(item)
        tip = tooltip(item)
        w = None
        side = None                 # a label shown left of the widget
        if kind in ('button', 'action'):
            w = QPushButton(label or key, parent)
            w.setMinimumWidth(w.fontMetrics().horizontalAdvance(w.text()) + 22)   # Fusion's 80 px floor is too wide
            if key.startswith('movie_') or key == 'pilMoviePushButton':
                w.setMaximumWidth(40)
            if key in L.PRIMARY:
                w.setProperty('nguiPrimary', True)
        elif kind == 'checkbox':
            w = QCheckBox(label, parent)
        elif kind == 'radio':
            w = QRadioButton(label, parent)
        elif kind == 'toggle':
            w = QToolButton(parent)
            w.setText(label)
            w.setCheckable(True)
            w.setProperty('nguiToggle', True)
        elif kind == 'lineedit':
            w = QLineEdit(parent)
            w.setMinimumWidth(36)
            side = label
        elif kind == 'combo':
            w = QComboBox(parent)
            items = item.get('items') or COMBO_ITEMS.get(key) or ([label] if label else [])
            w.addItems([str(x) for x in items])
            w.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            w.setMinimumContentsLength(4)
            side = label if item.get('items') or COMBO_ITEMS.get(key) else None
        elif kind == 'spin':
            w = QDoubleSpinBox(parent)
            w.setMinimumWidth(56)
            side = label
        elif kind == 'slider':
            w = QSlider(Qt.Horizontal, parent)
            w.setMinimumWidth(50)
            w.setValue(30 if 'Min' in key or 'min' in key else 90)
            side = label
        elif kind in ('list', 'pane'):
            if kind == 'pane':
                w = QPlainTextEdit(parent)
                w.setPlaceholderText(label or {'messageView': 'Messages: what the reader did and found',
                                               'scriptView': '# the script of every reduction, as Python'}
                                     .get(key, ''))
            else:
                w = QListWidget(parent)
                w.addItems(SAMPLES.get(key, SAMPLES.get(_oname(key), [])))
                w.setMinimumHeight(48)
                w.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                if key in ('scanInfoDialog.impInfoTextBrowser', 'ngui_ref_savedList', 'ref_savedList',
                           'refRefFileListWidget', 'mcaFileListWidget', 'backgroundListWidget', 'refQzListWidget'):
                    w.setMaximumHeight(72)
            side = label or None
        elif kind == 'table':
            heads = TABLE_HEADERS.get(key) or [h.strip() for h in label.split('|')] if '|' in label else \
                TABLE_HEADERS.get(key, ['', ''])
            w = QTableWidget(3, len(heads), parent)
            w.setHorizontalHeaderLabels(heads)
            w.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            w.verticalHeader().setVisible(False)
            w.setMinimumHeight(80)
            if key in ('plotscale.scaleTW', 'prefFoilTable', 'peakfit.bgTW'):
                w.setMaximumHeight(120)
            side = label if '|' not in label else None
        elif kind == 'progress':
            w = QProgressBar(parent)
            w.setRange(0, 100)
            w.setValue(0)
            w.setMaximumWidth(120)
            w.setFormat('idle')
        elif kind == 'plot':
            w = PlotSketch(label or key, 'curves', parent)
        else:                       # label
            w = QLabel(label, parent)
            w.setWordWrap(True)
        w.setObjectName(_oname(key))
        w.setToolTip(tip)
        if not isinstance(w, (PlotSketch, QLabel)):
            w.setEnabled(False)
        self.controls[key] = w
        return w, side

    def _add_items(self, items, lay, parent):
        for it in items:
            if 'caption' in it:
                c = QLabel(it['caption'], parent)
                c.setProperty('nguiCaption', True)
                c.setWordWrap(True)
                lay.addWidget(c)
            elif 'row' in it:
                h = QHBoxLayout()
                h.setSpacing(6)
                for sub in it['row']:
                    self._add_one(sub, h, parent, inline=True)
                lay.addLayout(h)
            else:
                self._add_one(it, lay, parent)

    def _add_one(self, it, lay, parent, inline=False):
        w, side = self._widget(it, parent)
        if side and isinstance(w, (QListWidget, QTableWidget, QPlainTextEdit)) and not inline:
            c = QLabel(side, parent)
            c.setProperty('nguiCaption', True)
            lay.addWidget(c)
            lay.addWidget(w)
        elif side:
            lab = QLabel(side, parent)
            lab.setBuddy(w)
            lab.setToolTip(w.toolTip())
            if inline:
                lay.addWidget(lab)
                lay.addWidget(w, 1)
            else:
                h = QHBoxLayout()
                h.addWidget(lab)
                h.addWidget(w, 1)
                lay.addLayout(h)
        else:
            lay.addWidget(w, 1 if isinstance(w, (QListWidget, QTableWidget)) else 0)

    def _card(self, title, parent, role='', fold=False, tip='', name=None):
        """A titled card: (frame, body layout)."""
        f = QFrame(parent)
        f.setProperty('nguiCard', True)
        f.setMinimumWidth(0)
        f.setObjectName(_oname(name or ('card_' + (title or 'untitled').replace(' ', '_'))))
        v = QVBoxLayout(f)
        v.setContentsMargins(10, 6, 10, 8)
        v.setSpacing(5)
        body = QWidget(f)
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(5)
        if title:
            head = QHBoxLayout()
            if fold:
                b = QToolButton(f)
                b.setObjectName(_oname('fold_' + title.replace(' ', '_')))
                b.setText(title)
                b.setProperty('nguiFold', True)
                b.setCheckable(True)
                b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
                b.setArrowType(Qt.RightArrow)
                b.setToolTip((tip + ' ' if tip else '') + 'Click to open or fold this group.')

                def toggled(on, b=b, body=body):
                    body.setVisible(on)
                    b.setArrowType(Qt.DownArrow if on else Qt.RightArrow)
                b.toggled.connect(toggled)
                body.setVisible(False)
                self.folds.append(b)
                head.addWidget(b)
            else:
                t = QLabel(title, f)
                t.setProperty('nguiTitle', True)
                t.setToolTip(tip)
                head.addWidget(t)
            head.addStretch(1)
            if role and role != title:
                r = QLabel(role.upper(), f)
                r.setProperty('nguiRole', True)
                r.setToolTip('Template slot: Input (what is reduced), Reduce (settings that change numbers), '
                             'Display (only the picture), or this tab\'s own kind of group')
                head.addWidget(r)
            v.addLayout(head)
        if tip:
            f.setToolTip(tip)
        v.addWidget(body)
        return f, bl

    def _group(self, g, parent):
        tip = g.get('note') or ''
        if g['replaces']:
            tip = (tip + '. ' if tip else '') + 'Takes over: ' + _names(g['replaces'])
        f, bl = self._card(g['title'], parent, g['role'], g['fold'], tip,
                           name='group_%s' % g['title'].replace(' ', '_') if g['title'] else None)
        self._add_items(g['items'], bl, f)
        return f

    def expand_all(self, on=True):
        for b in self.folds:
            b.setChecked(on)

    # ---- selection dock

    def _build_dock(self):
        d = QDockWidget('Selection', self)
        d.setObjectName('ngui_selectionDock')
        d.setFeatures(QDockWidget.NoDockWidgetFeatures)
        d.setToolTip('The selection panel keeps the full height at the left (prototype.md, principle 2): '
                     'series, scans, frames with the display mode, background frames.')
        w = QWidget(d)
        w.setObjectName('ngui_selectionPanel')
        v = QVBoxLayout(w)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(6)
        for g in L.DOCK:
            card = self._group(g, w)
            stretch = 2 if g['title'] in ('Scans', 'Frames') else 0
            v.addWidget(card, stretch)
        w.setMinimumWidth(DOCK_W - 12)
        d.setWidget(w)
        d.setFixedWidth(DOCK_W)
        self.addDockWidget(Qt.LeftDockWidgetArea, d)
        self.selectionDock = d

    # ---- tabs

    def _build_tabs(self):
        tabs = QTabWidget(self)
        tabs.setObjectName('ngui_tabs')
        tabs.setIconSize(QSize(12, 12))
        for k, tab in enumerate(L.TABS):
            page = self._tab_page(tab)
            tabs.addTab(page, theme.chip_icon(L.WORKFLOW_COLOURS[tab['key']]), tab['title'])
            tabs.setTabToolTip(k, 'Was: %s. Takes over: %s. Chip: the %s workflow colour (always beside the '
                                  'name).' % (tab['was'], _names(tab['replaces']), tab['chip']))
        self.tabs = tabs
        self.setCentralWidget(tabs)

    def _tab_page(self, tab):
        page = QWidget()
        page.setObjectName(_oname('tab_' + tab['key']))
        h = QHBoxLayout(page)
        h.setContentsMargins(6, 6, 6, 6)
        h.setSpacing(8)
        scroll = QScrollArea(page)
        scroll.setObjectName(_oname(tab['key'] + '_leftScroll'))
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFixedWidth(LEFT_W)
        col = QWidget()
        col.setObjectName(_oname(tab['key'] + '_leftColumn'))
        cv = QVBoxLayout(col)
        cv.setContentsMargins(0, 0, 4, 0)
        cv.setSpacing(6)
        for g in tab['left']:
            cv.addWidget(self._group(g, col))
        if tab.get('legacy'):
            b = QPushButton(tab.get('legacy_label', 'Legacy…'), col)
            b.setObjectName(_oname(tab['key'] + '_legacyButton'))
            b.setProperty('nguiLink', True)
            b.setToolTip('The legacy paths of this tab, kept behind one button until the owner answers question '
                         '13: %s. Prototype: opens a sketch.' %
                         '; '.join(g['title'] for g in tab['legacy']))
            b.clicked.connect(lambda _=False, t=tab: self.show_legacy(t['key']))
            cv.addWidget(b)
        cv.addStretch(1)
        scroll.setWidget(col)
        h.addWidget(scroll)
        right = QVBoxLayout()
        right.setSpacing(6)
        for row in tab['right']:
            rh = QHBoxLayout()
            rh.setSpacing(6)
            stretch = 1
            for panel in row:
                w = self._panel(panel, page)
                s = panel.get('stretch', 1) if isinstance(panel, dict) else 1
                stretch = max(stretch, s)
                rh.addWidget(w, s)
            right.addLayout(rh, stretch)
        h.addLayout(right, 1)
        return page

    # ---- right-hand panels

    def _panel(self, panel, parent):
        if 'special' in panel:
            return getattr(self, '_special_' + panel['special'])(panel, parent)
        if 'plot' in panel:
            return self._plot_card(panel, parent)
        f, bl = self._card('', parent)
        self._add_items([panel], bl, f)
        return f

    def _plot_card(self, pl, parent, card=True):
        key = pl['plot'] or pl['name']
        holder = QFrame(parent)
        if card:
            holder.setProperty('nguiCard', True)
        holder.setObjectName(_oname(key + '_card'))
        v = QVBoxLayout(holder)
        v.setContentsMargins(6, 4, 6, 4)
        v.setSpacing(3)
        res = None
        if pl.get('residuals'):
            bar = QHBoxLayout()
            bar.addStretch(1)
            t = QToolButton(holder)
            t.setObjectName(_oname(key + '_residualsToggle'))
            t.setText('Residuals')
            t.setCheckable(True)
            t.setProperty('nguiToggle', True)
            t.setToolTip('Shows a residuals panel above the fit plot, about 15 % of its height, (y − fit)/σ, '
                         'χ²/dof in the legend; hidden by default (F74). Prototype: shows the sketch.')
            bar.addWidget(t)
            v.addLayout(bar)
            res = ResidualsSketch(holder)
            res.setObjectName(_oname(key + '_residuals'))
            res.setVisible(False)
            t.toggled.connect(res.setVisible)
            v.addWidget(res, 15)
        sk = PlotSketch(pl['caption'], pl['sketch'], holder)
        sk.setObjectName(_oname(key))
        item = {'id': pl['plot'], 'note': pl.get('note')} if pl['plot'] else {'new': key, 'note': pl.get('note')}
        sk.setToolTip(tooltip(item))
        self.controls[key] = sk
        v.addWidget(sk, 85)
        if pl.get('provenance') or pl.get('note_button'):
            v.addLayout(self._provenance(key, pl.get('provenance'), pl.get('note_button'), holder))
        return holder

    def _provenance(self, key, text, note_button, parent):
        h = QHBoxLayout()
        h.setSpacing(6)
        if isinstance(text, dict):          # the main window's line under the plot (F96): a label, as there
            lab = QLabel(text.get('label') or '', parent)
            lab.setObjectName(_oname(text['id']))
            lab.setProperty('nguiProvenance', True)
            lab.setMinimumWidth(80)
            lab.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)  # clipped, never widening the window
            lab.setToolTip(tooltip(text))
            self.controls[text['id']] = lab
            h.addWidget(lab, 1)
        elif text:
            b = QPushButton(text, parent)
            b.setObjectName(_oname(key + '_provenance'))
            b.setProperty('nguiProvenance', True)
            b.setFlat(True)
            b.setMinimumWidth(80)
            b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)    # clipped, never widening the window
            m = QMenu(b)
            for t in ('Add a note…', 'Show the recipe…', 'Versions of this result…'):
                a = m.addAction(t)
                a.setEnabled(False)
            b.setMenu(m)
            b.setToolTip('Provenance of this result: scans, method, error model, normalisation, and the version '
                         'saved into the workbook (automatically, D56, or with Save…). Click: add a note to the saved version, '
                         'see its recipe or its versions. Prototype: the menu items do nothing.')
            h.addWidget(b, 1)
        else:
            h.addStretch(1)
        if note_button:
            w, _ = self._widget(note_button, parent)
            w.setMaximumWidth(80)
            h.addWidget(w)
        return h

    def _special_column(self, sp, parent):
        w = QWidget(parent)
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        for p in sp['items']:
            v.addWidget(self._panel(p, w), 1)
        return w

    def _special_verdict(self, sp, parent):
        f = QFrame(parent)
        f.setObjectName('ngui_burn_verdictCard')
        f.setProperty('nguiVerdict', True)
        f.setToolTip('The burn verdict (owner 2026-11-23): did the sample change over the exposure that matters? '
                     'The best model, the time to a 5 % change, the absorber. New in ngui. ' + NOT_FUNCTIONAL)
        v = QVBoxLayout(f)
        v.setContentsMargins(14, 8, 14, 8)
        head = QLabel('No change over 400 s?   Yes — within 1.2 % (the limit is 5 %)', f)
        head.setObjectName('ngui_burn_verdictHead')
        head.setProperty('nguiVerdictHead', True)
        v.addWidget(head)
        lab = sp['label']
        w, _ = self._widget(dict(lab, label='Best model: constant · time to a 5 % change: > 2 h · absorber 2 · '
                                            '41 frames, 10 s each'), f)
        v.addWidget(w)
        f.setMaximumHeight(90)
        return f

    def _special_tabs(self, sp, parent):
        f = QFrame(parent)
        f.setProperty('nguiCard', True)
        f.setObjectName(_oname(sp['name']))
        v = QVBoxLayout(f)
        v.setContentsMargins(6, 4, 6, 6)
        if sp.get('title'):
            w, _ = self._widget(sp['title'], f)
            w.setProperty('nguiTitle', True)
            v.addWidget(w)
        tw = QTabWidget(f)
        if sp.get('tabwidget'):
            tw.setObjectName(_oname(sp['tabwidget']['id']))
            tw.setToolTip(tooltip(sp['tabwidget']))
            tw.setEnabled(True)
            self.controls[sp['tabwidget']['id']] = tw
        else:
            tw.setObjectName(_oname(sp['name'] + '_tabs'))
        for name, items in sp['pages']:
            page = QWidget()
            pv = QVBoxLayout(page)
            pv.setContentsMargins(4, 4, 4, 4)
            for it in items:
                if 'plot' in it:
                    pv.addWidget(self._plot_card(it, page, card=False), 1)
                else:
                    self._add_items([it], pv, page)
            tw.addTab(page, name)
        v.addWidget(tw, 1)
        if sp.get('footer'):
            self._add_items([{'row': sp['footer']}], v, f)
        return f

    def _special_joins(self, sp, parent):
        f = QFrame(parent)
        f.setProperty('nguiCard', True)
        f.setObjectName('ngui_ref_joins')
        f.setToolTip('The joins of the patch listed inline (factor ± error, how it was chosen, status), the '
                     'doubtful ones opened, instead of one window per join (prototype.md, Reflectivity > Patch).')
        v = QVBoxLayout(f)
        v.setContentsMargins(6, 4, 6, 6)
        v.setSpacing(4)
        w, _ = self._widget(dict(sp['title'], label='Joins'), f)
        w.setProperty('nguiTitle', True)
        v.addWidget(w)
        t = QTableWidget(3, 4, f)
        t.setObjectName('ngui_ref_joinsTable')
        t.setHorizontalHeaderLabels(['join', 'factor', 'chosen', 'status'])
        rows = [('6 → 7', '0.1242 ± 0.4 %', 'fit', 'ok'), ('7 → 8', '0.1198 ± 2.9 %', 'fit', 'ok'),
                ('8 → 9', '0.1235 ± 1.5 %', 'known ratio', 'doubtful')]
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                t.setItem(r, c, QTableWidgetItem(val))
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.verticalHeader().setVisible(False)
        t.setMaximumHeight(112)
        t.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        t.setEnabled(False)
        if sp.get('table'):              # the main window's join table (F96): its inventory entry
            t.setToolTip(tooltip(sp['table']))
            t.setObjectName(_oname(sp['table']['id']))
            self.controls[sp['table']['id']] = t
        else:
            t.setToolTip('New in ngui: every join at once. ' + NOT_FUNCTIONAL)
        v.addWidget(t)
        ctl = sp['controls']
        self._add_items([{'row': ctl[:2]}, {'row': ctl[2:4]}, {'row': ctl[4:]}], v, f)
        tw = QTabWidget(f)
        tw.setObjectName('ngui_ref_joinPlots')
        for name, pl in sp['pages']:
            tw.addTab(self._plot_card(pl, tw, card=False), name)
        v.addWidget(tw, 1)
        return f

    def _special_cut_panel(self, sp, parent):
        w = QWidget(parent)
        w.setObjectName('ngui_frames_cutPanel')
        v = QVBoxLayout(w)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(4)
        self._add_items([{'row': sp['toolbar']}], v, w)
        holder = self._plot_card(dict(sp['plot'], provenance=sp.get('provenance'),
                                      note_button=sp.get('note_button')), w, card=False)
        v.addWidget(holder, 1)
        half = (len(sp['options']) + 1) // 2
        self._add_items([{'row': sp['options'][:half]}, {'row': sp['options'][half:]}], v, w)
        return w

    def _special_frame_viewer(self, sp, parent):
        f = QFrame(parent)
        f.setProperty('nguiCard', True)
        f.setObjectName('ngui_frames_viewer')
        outer = QVBoxLayout(f)
        outer.setContentsMargins(6, 4, 6, 6)
        outer.setSpacing(4)

        # Raw frames: views, image, movie bar, metadata
        raw = QWidget()
        raw.setObjectName('ngui_frames_rawPage')
        rv = QVBoxLayout(raw)
        rv.setContentsMargins(4, 4, 4, 4)
        rv.setSpacing(4)
        top = QHBoxLayout()
        lab = QLabel('View', raw)
        lab.setProperty('nguiCaption', True)
        top.addWidget(lab)
        frames_b = QPushButton('Frames', raw)
        frames_b.setObjectName('ngui_frames_viewFrames')
        frames_b.setEnabled(False)
        frames_b.setProperty('nguiPrimary', True)
        frames_b.setToolTip(tooltip({'new': 'frames_viewFrames', 'note': 'The frames, as recorded'}))
        top.addWidget(frames_b)
        for name, it in sp['views']:
            if it:
                w, _ = self._widget(it, raw)
                top.addWidget(w)
        top.addStretch(1)
        fixed = self._widget({'new': 'frames_fixed2theta', 'label': 'Fixed in 2θ', 'kind': 'checkbox',
                              'note': 'Frames drawn on a common 2θ axis with the zoom held in angle: a real GID '
                                      'peak stands still, junk moves (M7)'}, raw)[0]
        top.addWidget(fixed)
        rv.addLayout(top)
        image = self._plot_card(sp['image'], raw, card=False)
        for extra in ('gisaxs', 'gioxs'):          # the other views (shown by the view switch)
            hidden = self._plot_card(sp[extra], raw, card=False)
            hidden.setVisible(False)
            rv.addWidget(hidden)
        rv.addWidget(image, 1)
        movie = QHBoxLayout()
        movie.setSpacing(4)
        mb = sp['movie_bar']           # the main window's movie bar (F69, built 2026-11-24)
        movie.addWidget(self._widget(mb['view'], raw)[0])
        movie.addWidget(self._widget(sp['movie'], raw)[0])
        movie.addWidget(self._widget({'new': 'movie_first', 'label': '|◀', 'kind': 'button', 'note': 'First frame'},
                                     raw)[0])
        for key in ('back', 'play', 'next'):
            movie.addWidget(self._widget(mb[key], raw)[0])
        movie.addWidget(self._widget({'new': 'movie_last', 'label': '▶▶|', 'kind': 'button', 'note': 'Last frame'},
                                     raw)[0])
        movie.addWidget(self._widget(mb['slider'], raw)[0], 1)
        movie.addWidget(self._widget(mb['counter'], raw)[0])
        rv.addLayout(movie)
        movie = QHBoxLayout()           # second line: speed, loop, colour scale, then the frame's metadata
        movie.setSpacing(4)
        movie.addWidget(self._widget(mb['speed'], raw)[0])
        movie.addWidget(self._widget(mb['loop'], raw)[0])
        movie.addWidget(self._widget({'new': 'movie_colour', 'label': 'colour', 'kind': 'combo',
                                      'items': ['shared', 'per frame', 'locked'],
                                      'note': 'Colour scale across the movie (M4)'}, raw)[0])
        meta = self._widget(mb['meta'], raw)[0]
        meta.setProperty('nguiCaption', True)
        meta.setMinimumWidth(60)
        movie.addWidget(meta, 1)
        rv.addLayout(movie)

        cuts = self._special_cut_panel(sp['cuts'], f)

        tw = QTabWidget(f)
        tw.setObjectName('ngui_frames_subTabs')
        tw.addTab(raw, 'Raw frames')
        tw.addTab(cuts, 'Line cuts')
        tw.setToolTip('Raw frames (with the movie bar) and Line cuts (the band is drawn on the raw image). '
                      'Split shows both at once.')
        split = QSplitter(Qt.Horizontal, f)
        split.setObjectName('ngui_frames_split')
        split.setVisible(False)

        bar = QHBoxLayout()
        bar.addStretch(1)
        t = QToolButton(f)
        t.setObjectName('ngui_frames_splitToggle')
        t.setText(sp['split']['label'])
        t.setCheckable(True)
        t.setProperty('nguiToggle', True)
        t.setToolTip(tooltip(sp['split'], 'Prototype: works (moves the two sub-tabs side by side).'))
        orient = QComboBox(f)
        orient.setObjectName('ngui_frames_splitOrientation')
        orient.addItems(['side by side', 'stacked'])
        orient.setToolTip('How Split arranges Raw frames and Line cuts. Prototype: works.')
        bar.addWidget(t)
        bar.addWidget(orient)

        def do_split(on):
            if on:
                split.setOrientation(Qt.Horizontal if orient.currentIndex() == 0 else Qt.Vertical)
                split.addWidget(raw)
                split.addWidget(cuts)
                raw.show()
                cuts.show()
                tw.hide()
                split.show()
            else:
                tw.addTab(raw, 'Raw frames')
                tw.addTab(cuts, 'Line cuts')
                split.hide()
                tw.show()
        t.toggled.connect(do_split)
        orient.currentIndexChanged.connect(
            lambda i: split.setOrientation(Qt.Horizontal if i == 0 else Qt.Vertical))
        self.framesSplitToggle = t
        self.framesSubTabs = tw
        outer.addLayout(bar)
        outer.addWidget(tw, 1)
        outer.addWidget(split, 1)
        return f

    # ---- panes, status bar, menus

    def _build_panes(self):
        self.panes = {}
        first = None
        for p in L.PANES:
            d = QDockWidget(p['title'], self)
            d.setObjectName(_oname(p['replaces'][0]))
            d.setAllowedAreas(Qt.BottomDockWidgetArea)
            w = QWidget(d)
            v = QVBoxLayout(w)
            v.setContentsMargins(6, 6, 6, 6)
            self._add_items(p['items'], v, w)
            if p['title'] == 'Errors':
                v.addStretch(1)
            d.setWidget(w)
            d.setToolTip('Under the tab area only, hidden by default, never raising itself (D59). '
                         'View > %s shows it.' % p['title'])
            self.addDockWidget(Qt.BottomDockWidgetArea, d)
            if first is None:
                first = d
            else:
                self.tabifyDockWidget(first, d)
            d.hide()
            self.panes[p['title']] = d

    def _build_status(self):
        sb = self.statusBar()
        sb.setObjectName('ngui_statusBar')
        sb.setToolTip(tooltip(L.STATUS[0]))
        sb.showMessage('ngui prototype: a sketch of the layout; nothing is read or reduced here')
        w, _ = self._widget(L.STATUS[1], sb)
        sb.addPermanentWidget(w)
        for item in L.STATUS[2:]:                  # the state badges, as built in the main window (F85)
            b, _ = self._widget(item, sb)
            b.setWordWrap(False)
            b.setProperty('nguiState', True)
            sb.addPermanentWidget(b)
        for text, tip in L.STATE_BAR:
            lab = QLabel(text, sb)
            lab.setObjectName(_oname('state_' + text.replace(' ', '_').replace('/', '')))
            lab.setProperty('nguiState', True)
            lab.setToolTip(tip + ' A setting that changes numbers everywhere (principle 5; question 12 is open). '
                           + NOT_FUNCTIONAL)
            sb.addPermanentWidget(lab)
        self.controls['statusBar'] = sb

    def _build_menus(self):
        mb = self.menuBar()
        mb.setObjectName('ngui_menuBar')
        for m in L.MENUS:
            menu = mb.addMenu(m['title'])
            menu.setObjectName(_oname('menu' + m['title']))
            menu.setToolTipsVisible(True)
            for it in m['items']:
                key = _key(it)
                if m['title'] == 'View':
                    d = self.panes[_label(it)]
                    a = d.toggleViewAction()
                    a.setText(_label(it))
                    a.setToolTip(tooltip(it, 'Prototype: works (shows or hides the pane).'))
                    menu.addAction(a)
                else:
                    a = QAction(_label(it), self)
                    handler = {'actionPreferences': self.show_preferences, 'file_export': self.show_export,
                               'help_retired': self.show_retired}.get(key)
                    a.setToolTip(tooltip(it, 'Prototype: opens the sketch.' if handler else None))
                    a.setEnabled(handler is not None)
                    if handler:
                        a.triggered.connect(lambda _=False, h=handler: h())
                    menu.addAction(a)
                a.setObjectName(_oname(key))
                self.controls[key] = a

    # ---- sketch dialogs (shown, never exec'd)

    def _build_dialogs(self):
        for tab in L.TABS:
            if tab.get('legacy'):
                self.show_legacy(tab['key'], show=False)
        self.show_export(show=False)
        self.show_preferences(show=False)

    def _dialog(self, key, title, groups=(), size=(520, 420), show=True):
        if key in self.dialogs:
            d = self.dialogs[key]
        else:
            d = QDialog(self)
            d.setObjectName(_oname(key + 'Dialog'))
            d.setWindowTitle(title)
            v = QVBoxLayout(d)
            for g in groups:
                if g['title']:
                    v.addWidget(self._group(g, d))
                else:
                    self._add_items(g['items'], v, d)
            d.resize(*size)
            theme.apply(d)
            self.dialogs[key] = d
        if show:
            d.show()
            d.raise_()
        return d

    def show_legacy(self, key, show=True):
        tab = next(t for t in L.TABS if t['key'] == key)
        d = self._dialog('legacy_' + key, '%s — %s (ngui sketch)' % (tab['title'], tab.get('legacy_label', 'Legacy…')
                                                                    .rstrip('…')), tab['legacy'], (560, 520),
                         show)
        return d

    def show_export(self, show=True):
        return self._dialog('export', 'Export (ngui sketch)', L.EXPORT, (460, 560), show)

    def show_preferences(self, show=True):
        return self._dialog('preferences', 'Preferences (ngui sketch: what stays in the dialog)', L.PREFERENCES,
                            (480, 360), show)

    def show_retired(self):
        if 'retired' in self.dialogs:
            d = self.dialogs['retired']
            d.show()
            d.raise_()
            return d
        d = QDialog(self)
        d.setObjectName('ngui_retiredDialog')
        d.setWindowTitle('Retired controls (ngui sketch)')
        v = QVBoxLayout(d)
        head = QLabel('%d controls of today\'s window have no place in ngui. Each is listed with its reason; '
                      'nothing is deleted until the owner agrees (questions 13 and 14).' % len(L.RETIRED), d)
        head.setWordWrap(True)
        v.addWidget(head)
        t = QTableWidget(len(L.RETIRED), 3, d)
        t.setObjectName('ngui_retiredTable')
        t.setHorizontalHeaderLabels(['control', 'was', 'reason'])
        for r, (cid, reason) in enumerate(L.RETIRED.items()):
            kind, label, where, does = INVENTORY.get(cid, ('', '', '', ''))
            for c, val in enumerate((cid, '%s (%s)' % (where, label) if label else where, reason)):
                it = QTableWidgetItem(val)
                it.setToolTip(does if c < 2 else reason)
                t.setItem(r, c, it)
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        t.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        t.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        t.verticalHeader().setVisible(False)
        t.setWordWrap(True)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        v.addWidget(t)
        d.resize(1100, 700)
        theme.apply(d)
        self.dialogs['retired'] = d
        d.show()
        d.raise_()
        t.resizeRowsToContents()          # the reasons wrap once the columns have their widths
        return d


def _names(ids):
    out = []
    for cid in ids:
        kind, label, where, does = INVENTORY.get(cid, ('', '', '', ''))
        out.append('%s (%s)' % (cid, label) if label and label != cid else cid)
    return ', '.join(out)


def open_window(parent=None):
    """Build and show the ngui window beside ``parent`` (a MainWindow)."""
    w = NguiWindow(parent)
    if parent is not None:
        g = parent.frameGeometry()
        w.move(g.right() + 10, g.top())
    w.show()
    return w
