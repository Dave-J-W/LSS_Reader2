"""The reader's Tools menu (MainWindow.initToolsMenu -> lss_toolbox.menu):
the one place the Tools collection touches the main window. The window and
its pages are tested on their own in test_toolbox_gui.py."""
import os
import sys

import pytest

pytestmark = pytest.mark.gui

HERE = os.path.dirname(os.path.abspath(__file__))


def test_tools_menu_sits_before_help_and_lists_every_item(window, recorder):
    from lss_toolbox import catalog
    titles = [a.text().replace('&', '') for a in window.menuBar().actions()]
    assert titles.index('Tools') == titles.index('Help') - 1
    assert set(window.ui.menuTools.toolActions) == {'all'} | {t.id for t in catalog.TOOLS}
    assert window.toolsWindow is None                      # built when first asked for
    assert recorder.exceptions == []


def test_a_synthetic_data_set_opens_in_the_reader(window, recorder, tmp_path, capsys):
    """The host the menu passes: the open SPEC file, opening one, the
    Messages pane."""
    sys.path.insert(0, os.path.join(HERE, 'tools'))
    import synthetic_dataset
    window.ui.menuTools.toolActions['synthetic_dataset'].trigger()
    tools = window.toolsWindow
    assert tools.stack.currentWidget() is tools.pages['synthetic_dataset']
    assert tools.host.spec_file() is None
    synthetic_dataset.main(['--out', str(tmp_path / 'burn'), '--kind', 'burn'])
    spec = capsys.readouterr().out.strip().splitlines()[-1][5:]
    tools.host.open_spec(spec)
    window.directory = str(tmp_path)
    assert window.specFileName == spec and tools.host.spec_file() == spec
    assert window.ui.scanListWidget.count() == 1
    tools.host.notify('Tools: a note')
    assert 'Tools: a note' in window.messageView.toPlainText()
    tools.wait_parsers(120)
    tools.close()
    assert recorder.exceptions == []
