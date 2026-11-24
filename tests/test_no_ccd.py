"""D8/F38: the Bruker/Apex CCD is defunct and its code is gone."""
import os
import re

import pytest

import sweep
import synth
from TwoDDetector import TwoDDetector

pytestmark = pytest.mark.gui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MESSAGE = 'Bruker CCD images (.sfrm) are no longer supported by this reader.'


def test_bruker_detector_is_refused():
    with pytest.raises(ValueError, match='unsupported detector'):
        TwoDDetector('Bruker')
    assert TwoDDetector('Pilatus').pix_size == 0.172


def test_apex_tab_is_gone_and_pilatus_tab_unchanged(window):
    # the hidden Apex (CCD) tab was removed (owner, 2026-11-23, Q14); before,
    # it sat hidden at index 1 with Pilatus at 2
    pw = window.ui.PlotWidget
    assert 'Apex' not in [pw.tabText(i) for i in range(pw.count())]
    assert pw.tabText(1) == 'Pilatus'
    assert pw.isTabVisible(1)


def test_sfrm_scan_is_unsupported_with_one_message(window, qapp, recorder, tmp_path):
    scan = synth.spec_scan(1, 'c', synth.REF_COLUMNS,
                           synth.ref_rows([0.02, 0.03]))
    scan = scan.replace('.tif', '.sfrm')
    spec = synth.write_spec(str(tmp_path / 'c'), [scan])
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    assert window.specPar[1]['Detector'] == 'Unsupported'
    recorder.messages[:] = []
    sweep._select_scans(window, qapp, [0])
    assert recorder.exceptions == []
    assert recorder.messages == [MESSAGE]
    assert window.ui.imageListWidget.count() == 0


@pytest.mark.parametrize('name', ['mainwindow.py', 'TwoDDetector.py'])
def test_no_bruker_comparison_left(name):
    text = open(os.path.join(ROOT, name)).read()
    assert 'Bruker' not in text.replace(MESSAGE, '')
    assert not re.search(r'\bbruker\b|selectedCcd|ccdSelected|updateCcd', text)
