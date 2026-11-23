"""Controls the owner agreed to remove (2026-11-23, question 14).

Each removed control keeps its inventory entry with a ``removed:`` field
(`docs/gui/inventory/`), so the record of what the window had survives.
"""
import glob
import os

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _removed_ids():
    ids = {}
    for path in glob.glob(os.path.join(ROOT, 'docs', 'gui', 'inventory', '*.yaml')):
        for e in yaml.safe_load(open(path, encoding='utf-8')) or []:
            if isinstance(e, dict) and e.get('removed'):
                ids[str(e['id'])] = e['removed']
    return ids


def test_unused_peak_fit_dialogs_are_gone():
    for name in ('peakfit2.ui', 'peakfitpara.ui'):
        assert not os.path.exists(os.path.join(ROOT, name))
    assert os.path.exists(os.path.join(ROOT, 'peakfit.ui'))      # the one in use stays
    removed = _removed_ids()
    assert 'peakfit2' in removed and 'peakfitpara' in removed


def test_every_removed_entry_says_when_and_why():
    removed = _removed_ids()
    assert removed
    for cid, why in removed.items():
        assert why.startswith('2026-') and len(why) > 20, cid


@pytest.mark.gui
def test_removed_controls_are_not_in_the_window(window, recorder):
    from PyQt5.QtCore import QObject
    assert window.findChild(QObject, 'scanListWidget') is not None    # the lookup does find controls
    for cid in _removed_ids():
        if '.' in cid or cid in ('peakfit2', 'peakfitpara'):
            continue                       # dialogs: checked by their files above
        assert not hasattr(window.ui, cid), cid
        assert window.findChild(QObject, cid) is None, cid
    assert recorder.exceptions == []
