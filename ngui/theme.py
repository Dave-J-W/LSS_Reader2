"""Palette and style sheet of the ngui window only (docs/gui/prototype.md, principle 12).

Nothing here touches the application: no QApplication.setStyle, setPalette or
setStyleSheet. ``apply(widget)`` gives one top-level ngui widget (the window
or one of its sketch dialogs) Qt's Fusion style, one light palette and the
style sheet below; the real window looks exactly as before.
"""
from PyQt5.QtGui import QColor, QPalette

ACCENT = '#2f6fdf'          # the one accent colour: current tab, primary action of a group
ACCENT_DARK = '#2457b3'
WINDOW = '#eef0f3'          # background behind the cards
CARD = '#ffffff'
BORDER = '#d5d9e0'
TEXT = '#1f2329'
MUTED = '#5d6573'           # captions, provenance, disabled placeholders (still readable)
FIELD = '#f8f9fb'

SHEET = """
QMainWindow#ngui_window, QDialog { background: %(WINDOW)s; }
QWidget { font-size: 9pt; color: %(TEXT)s; }
QFrame[nguiCard="true"] { background: %(CARD)s; border: 1px solid %(BORDER)s; border-radius: 6px; }
QLabel[nguiTitle="true"] { font-weight: 600; font-size: 9.5pt; color: %(TEXT)s; }
QLabel[nguiRole="true"] { color: %(MUTED)s; font-size: 7.5pt; }
QLabel[nguiCaption="true"] { color: %(MUTED)s; font-size: 8pt; }
QLabel:disabled, QCheckBox:disabled, QRadioButton:disabled { color: %(MUTED)s; }
QLineEdit, QComboBox, QAbstractSpinBox, QListWidget, QTableWidget, QPlainTextEdit {
    background: %(FIELD)s; border: 1px solid %(BORDER)s; border-radius: 3px; padding: 1px 4px; }
QLineEdit:disabled, QComboBox:disabled, QAbstractSpinBox:disabled, QListWidget:disabled,
QTableWidget:disabled, QPlainTextEdit:disabled { color: %(MUTED)s; }
QPushButton { background: #f4f5f7; border: 1px solid %(BORDER)s; border-radius: 4px; padding: 3px 10px; }
QPushButton:disabled { color: %(MUTED)s; }
QPushButton[nguiPrimary="true"] { background: %(ACCENT)s; color: white; border: 1px solid %(ACCENT_DARK)s;
    font-weight: 600; }
QPushButton[nguiPrimary="true"]:disabled { background: #7fa3e8; color: white; border-color: #6d93db; }
QPushButton[nguiLink="true"] { background: transparent; border: 1px dashed %(BORDER)s; color: %(ACCENT_DARK)s; }
QToolButton[nguiFold="true"] { border: none; font-weight: 600; font-size: 9.5pt; text-align: left; }
QPushButton[nguiProvenance="true"] { border: none; background: transparent; color: %(MUTED)s; font-size: 8pt;
    text-align: left; padding: 1px 2px; }
QPushButton[nguiProvenance="true"]:hover { color: %(ACCENT_DARK)s; text-decoration: underline; }
QPushButton[nguiProvenance="true"]::menu-indicator { width: 0px; }
QToolButton[nguiToggle="true"] { border: 1px solid %(BORDER)s; border-radius: 4px; padding: 2px 8px;
    background: #f4f5f7; }
QToolButton[nguiToggle="true"]:checked { background: %(ACCENT)s; color: white; border-color: %(ACCENT_DARK)s; }
QLabel[nguiState="true"] { border: 1px solid %(BORDER)s; border-radius: 8px; padding: 0px 8px;
    background: %(CARD)s; color: %(TEXT)s; font-size: 8pt; }
QFrame[nguiVerdict="true"] { background: #fff7f0; border: 1px solid #e07b39; border-left: 5px solid #e07b39;
    border-radius: 6px; }
QLabel[nguiVerdictHead="true"] { font-size: 12pt; font-weight: 600; }
QTabWidget::pane { border: 1px solid %(BORDER)s; border-radius: 4px; background: %(WINDOW)s; top: -1px; }
QTabBar::tab { background: #e2e5ea; border: 1px solid %(BORDER)s; border-bottom: none; padding: 5px 12px;
    margin-right: 2px; border-top-left-radius: 5px; border-top-right-radius: 5px; color: %(TEXT)s; }
QTabBar::tab:selected { background: %(CARD)s; border-top: 3px solid %(ACCENT)s; font-weight: 600; }
QTabWidget#ngui_tabs > QTabBar::tab { padding: 6px 16px; font-size: 10pt; }
QDockWidget { font-weight: 600; }
QDockWidget::title { background: #e2e5ea; padding: 4px 6px; }
QStatusBar { background: #e2e5ea; border-top: 1px solid %(BORDER)s; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QHeaderView::section { background: #eceef2; border: none; border-right: 1px solid %(BORDER)s;
    padding: 2px 4px; color: %(MUTED)s; }
""" % dict(ACCENT=ACCENT, ACCENT_DARK=ACCENT_DARK, WINDOW=WINDOW, CARD=CARD, BORDER=BORDER, TEXT=TEXT,
           MUTED=MUTED, FIELD=FIELD)


def palette():
    p = QPalette()
    for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
        p.setColor(group, QPalette.Window, QColor(WINDOW))
        p.setColor(group, QPalette.Base, QColor(FIELD))
        p.setColor(group, QPalette.AlternateBase, QColor('#f1f3f6'))
        p.setColor(group, QPalette.Button, QColor('#f4f5f7'))
        p.setColor(group, QPalette.Highlight, QColor(ACCENT))
        p.setColor(group, QPalette.HighlightedText, QColor('white'))
        p.setColor(group, QPalette.ToolTipBase, QColor('#fffdf2'))
        p.setColor(group, QPalette.ToolTipText, QColor(TEXT))
        fg = QColor(MUTED) if group == QPalette.Disabled else QColor(TEXT)
        for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
            p.setColor(group, role, fg)
    return p


def apply(top):
    """Fusion style, the palette and the sheet on ``top`` and every widget under it."""
    from PyQt5.QtWidgets import QStyleFactory, QWidget
    style = getattr(top, '_ngui_style', None)
    if style is None:
        style = QStyleFactory.create('Fusion')
        if style is not None:
            style.setParent(top)          # disposed with the window
            style.setObjectName('ngui_style')
        top._ngui_style = style
    top.setPalette(palette())
    top.setStyleSheet(SHEET)
    if style is not None:
        for w in [top] + top.findChildren(QWidget):
            w.setStyle(style)


def chip_icon(colour, size=12):
    """A small rounded colour square for a tab title (always beside its text)."""
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QIcon, QPainter, QPixmap
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(colour))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)
    p.end()
    return QIcon(pm)
