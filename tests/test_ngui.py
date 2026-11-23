"""The ngui prototype window (F82, docs/gui/prototype.md): it builds, it places
every inventoried control exactly once or retires it with a reason, and it
leaves the real window alone."""
import glob
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _inventory_ids():
    import yaml
    ids = []
    for path in sorted(glob.glob(os.path.join(ROOT, 'docs', 'gui', 'inventory', '*.yaml'))):
        with open(path, encoding='utf-8') as f:
            ids += [str(e['id']) for e in yaml.safe_load(f) or []]
    return ids


def test_every_inventory_id_is_placed_once_or_retired():
    from collections import Counter
    from ngui import layout
    inv = set(_inventory_ids())
    placed = Counter(cid for cid, _ in layout.placements())
    twice = {cid: [w for c, w in layout.placements() if c == cid] for cid, n in placed.items() if n > 1}
    assert twice == {}, twice
    assert sorted(set(placed) - inv) == [], 'placed but unknown to the inventory'
    assert sorted(set(layout.RETIRED) - inv) == [], 'retired but unknown to the inventory'
    assert sorted(set(placed) & set(layout.RETIRED)) == [], 'both placed and retired'
    assert sorted(inv - set(placed) - set(layout.RETIRED)) == [], 'neither placed nor retired'
    assert all(isinstance(r, str) and len(r) > 10 for r in layout.RETIRED.values())


def test_no_output_group_and_no_save_or_export_buttons_in_tabs():
    """D61 (owner 2026-11-23): results are saved automatically; each result plot has one Save… button;
    exporting is File > Export…, never a button in a tab. Each result area keeps one Save… button
    (a version with a note), placed beside its provenance strip, not in the left column."""
    from ngui import layout
    from ngui.inventory_text import INVENTORY
    for tab in layout.TABS:
        assert [g['title'] for g in tab['left'] if g['role'] == 'Output'] == [], tab['title']
        for g in tab['left'] + tab.get('legacy', []):
            for cid, _w, it in layout._walk_items(g['items'], ''):
                label = (it.get('label') or INVENTORY[cid][1]).lower()
                assert 'export' not in label and 'save' not in label, (tab['title'], cid, label)
    export_ids = {cid for g in layout.EXPORT for cid, _w, _ in layout._walk_items(g['items'], '')}
    assert {'refExportPushButton', 'refCovarianceCheckBox', 'spExportPushButton', 'cutExportPushButton',
            'mcaExportPushButton', 'mcaExportIntPushButton'} <= export_ids
    notes = {cid for cid, it in layout.placed_items().items() if it.get('label') == 'Save…'}
    assert {'refSaveWorkbookPushButton', 'specSaveWorkbookPushButton', 'cutSaveWorkbookPushButton',
            'mcaSaveWorkbookPushButton', 'burnSavePushButton', 'gidComboBox'} == notes


def test_generated_inventory_text_is_up_to_date():
    sys.path.insert(0, os.path.join(ROOT, 'tests', 'tools'))
    import ngui_inventory
    with open(ngui_inventory.OUT, encoding='utf-8') as f:
        assert f.read() == ngui_inventory.render(), 'rerun python tests/tools/ngui_inventory.py'


def test_ngui_does_not_import_the_core_or_yaml():
    """The packaged program ships neither docs/ nor PyYAML; ngui reads no data."""
    import re
    for path in glob.glob(os.path.join(ROOT, 'ngui', '*.py')):
        text = open(path, encoding='utf-8').read()
        assert not re.search(r'^\s*(from|import)\s+(lss_core|yaml|mainwindow|matplotlib)\b', text, re.M), path
        assert not re.search(r'^\s*(import (os|glob)|from os)\b|\bopen\(', text, re.M), path


@pytest.mark.gui
def test_window_builds_with_every_placed_control(qapp, recorder):
    from PyQt5.QtCore import QObject
    from PyQt5.QtWidgets import QApplication, QWidget
    from ngui import layout
    from ngui.window import NguiWindow, SIZE
    style, palette, sheet = QApplication.style().objectName(), QApplication.palette().color(10).name(), qapp.styleSheet()
    w = NguiWindow()
    w.show()
    qapp.processEvents()
    try:
        assert w.windowTitle() == 'LSS Reader — ngui (prototype)'
        assert (w.width(), w.height()) == SIZE
        assert [w.tabs.tabText(k) for k in range(w.tabs.count())] == [t['title'] for t in layout.TABS]
        for cid, item in layout.placed_items().items():
            assert cid in w.controls, cid
            o = w.controls[cid]
            assert o.objectName() == 'ngui_' + cid.replace('.', '_'), cid
            assert 'Was: ' in o.toolTip() and 'Does: ' in o.toolTip(), cid
        # placeholders do nothing: every inventoried widget except plots, labels and the working menu items
        for cid, o in w.controls.items():
            if cid in layout.placed_items() and isinstance(o, QWidget) and o.isEnabled():
                assert type(o).__name__ in ('PlotSketch', 'QLabel', 'QStatusBar', 'QTabWidget'), cid
        names = [o.objectName() for o in w.findChildren(QObject) if o.objectName()]
        qt_own = ('ScrollLeftButton', 'ScrollRightButton', '_layout')     # Qt's tab scrollers, QMainWindow's layout
        assert [n for n in names if not n.startswith(('ngui_', 'qt_')) and n not in qt_own] == []
        # panes hidden by default; the View menu shows them
        assert not any(d.isVisible() for d in w.panes.values())
        w.controls['messageDock_toggleViewAction'].trigger()
        qapp.processEvents()
        assert w.panes['Messages'].isVisible()
        # the working pieces of the sketch
        w.framesSplitToggle.setChecked(True)
        qapp.processEvents()
        w.framesSplitToggle.setChecked(False)
        qapp.processEvents()
        assert w.framesSubTabs.count() == 2
        assert [w.framesSubTabs.tabText(k) for k in range(2)] == ['Raw frames', 'Line cuts']
        w.expand_all(True)
        for key in [t['key'] for t in layout.TABS if t.get('legacy')]:
            w.show_legacy(key)
        w.show_export()
        w.show_preferences()
        d = w.show_retired()
        assert d.findChild(QWidget, 'ngui_retiredTable').rowCount() == len(layout.RETIRED)
        qapp.processEvents()
        # the application's look is untouched
        assert QApplication.style().objectName() == style and qapp.styleSheet() == sheet
        assert QApplication.palette().color(10).name() == palette
        assert recorder.exceptions == []
    finally:
        w.close()
        w.deleteLater()
        qapp.processEvents()
