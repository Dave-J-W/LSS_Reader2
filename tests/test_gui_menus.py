"""File > Quit and Help > Documentation (owner, 2026-11-23, Q-UI-A12): both
were in the menus and connected to nothing."""
import os

import pytest

pytestmark = pytest.mark.gui


def test_documentation_opens_the_quick_start_guide(window, recorder, monkeypatch):
    """Since 2026-11-26 the quick-start guide, the manual's first part (Q-UI-A12:
    the scripting guide until the manual exists); before, docs/SCRIPTING.md."""
    from PyQt5.QtGui import QDesktopServices
    opened = []
    monkeypatch.setattr(QDesktopServices, 'openUrl', staticmethod(lambda url: opened.append(url) or True))
    window.ui.actionDocumentation.trigger()
    assert len(opened) == 1 and opened[0].isLocalFile()
    assert os.path.normpath(opened[0].toLocalFile()).endswith(os.path.join('docs', 'manual', 'quick_start.md'))
    assert os.path.exists(opened[0].toLocalFile())
    assert window.ui.actionDocumentation.toolTip()
    assert recorder.exceptions == [] and recorder.messages == []


def test_documentation_falls_back_to_github_without_the_docs_folder(window, recorder, monkeypatch):
    from PyQt5.QtGui import QDesktopServices
    import mainwindow
    opened = []
    monkeypatch.setattr(QDesktopServices, 'openUrl', staticmethod(lambda url: opened.append(url) or True))
    monkeypatch.setattr(mainwindow, 'resource', lambda name: os.path.join('/nonexistent', name))
    window.ui.actionDocumentation.trigger()
    assert opened and opened[0].toString() == window.DOCS_URL
    assert recorder.exceptions == []


def test_quit_closes_the_window(window, qapp, recorder):
    assert window.isVisible()
    assert window.ui.actionQuit.shortcut().toString() == 'Ctrl+Q'
    window.ui.actionQuit.trigger()
    qapp.processEvents()
    assert not window.isVisible()
    assert recorder.exceptions == []
