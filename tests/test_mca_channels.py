"""Multi-element fluorescence detector (owner, 2026-11-19): per-point MCA
files with one block per element (#@CHANNEL); a global element selector
(Preferences); EXAFS sums all seven, XFNTR uses the central one. The
7-element detector corrects its own dead time (#@CTIME 1 1 1)."""
import os

import numpy as np
import pytest

import sweep
import synth
from lss_core import fluorescence as fl
from lss_core.experiment import Experiment
from test_script_console import _run_script

NPTS, NCH, NBINS = 3, 7, 1000


def _mca_text(scan, name):
    out = ['#F ./vortex/%s_%d_mca' % (name, scan), '#E 0', '#D (date removed)', '']
    k = 1
    for p in range(NPTS):
        for c in range(1, NCH + 1):
            y = np.zeros(NBINS, int)
            y[495:505] = 100 * c * (p + 1)                 # element c, point p: a line at 5 keV
            out += ['#S %d mca_save_point Point:%d Scan:%d Datafile:%s' % (k, p, scan, name),
                    '#Monc 100000 0', '#Q 0 0 %g' % (0.01 + 0.005 * p), '#@CHANNEL %d' % c,
                    '#@CTIME 1 1 1', '#@CALIB 0 0.01 0', '#Energy 10']
            vals = [str(v) for v in y]
            chunks = [vals[i:i + 32] for i in range(0, len(vals), 32)]
            for i, ch in enumerate(chunks):
                out.append(('@A ' if i == 0 else '') + ' '.join(ch) + ('\\' if i < len(chunks) - 1 else ''))
            out.append('')
            k += 1
    return '\n'.join(out) + '\n'


@pytest.fixture
def me7(tmp_path):
    root = tmp_path / 'me7'
    os.makedirs(root / 'vortex')
    rows = np.column_stack([np.zeros(NPTS), np.zeros(NPTS), 0.01 + 0.005 * np.arange(NPTS), np.ones(NPTS),
                            np.full(NPTS, 1e5), np.zeros(NPTS)])
    text = synth.spec_scan(1, 'm', ['H', 'K', 'L', 'Seconds', 'Monc', 'Vortex'], rows,
                           command='hklscan 0 0 0 0 0.01 0.02 2 1', image=False)
    head, body = text.split('\n', 1)
    spec = synth.write_spec(str(root / 'm'), [head + '\n#V vortex data:./vortex/m_1_mca\n' + body])
    (root / 'vortex' / 'm_1_mca').write_text(_mca_text(1, 'm'))
    return spec


def test_reader_and_combination(me7):
    import mca_routines
    m = mca_routines.mcaread(os.path.join(os.path.dirname(me7), 'vortex', 'm_1_mca'))
    assert m.Data['NumOfScans'] == NPTS * NCH and m.Par[0]['Channel'] == 1 and m.Par[7]['Point'] == 1
    spectra = [(m.Data[j], m.Par[j]) for j in range(m.Data['NumOfScans'])]
    all7 = fl.combine_channels(spectra)
    assert len(all7) == NPTS and all7[1][1]['Channels'] == list(range(1, 8))
    assert max(all7[1][0]['Vortex']) == 100 * 28 * 2                       # elements 1..7, point 1
    centre = fl.combine_channels(spectra, [4])
    assert max(centre[2][0]['Vortex']) == 100 * 4 * 3 and centre[0][1]['Channels'] == [4]
    single = [(m.Data[0], {'Calib': [0, 1, 0]})]
    assert fl.combine_channels(single) == single                          # single-element files unchanged


def test_scripted_fluorescence_by_element(me7):
    exp = Experiment(me7)
    a = np.array(exp.fluorescence([1], window=(4.9, 5.1)).rows)
    c = np.array(exp.fluorescence([1], window=(4.9, 5.1), channels=[4]).rows)
    assert len(a) == NPTS and a[:, 3] == pytest.approx(c[:, 3] * 7)       # sum of 1..7 = 7 × element 4


@pytest.mark.gui
def test_preferences_selector_reloads_and_is_scripted(window, qapp, recorder, me7, tmp_path):
    w = window
    w.openSpecFile(fname=me7)
    w.directory = str(tmp_path)
    sweep._select_scans(w, qapp, [0])
    texts = [w.ui.imageListWidget.item(k).text() for k in range(w.ui.imageListWidget.count())]
    assert len(texts) == NPTS and all(t.endswith('ch 1,2,3,4,5,6,7') for t in texts)
    d = w.buildPreferences()
    for k, b in enumerate(d.prefMcaChannelBoxes, 1):
        b.setChecked(k == 4)                                              # the central element only
    qapp.processEvents()
    assert w.prefs['mca_channels'] == [4]
    texts = [w.ui.imageListWidget.item(k).text() for k in range(w.ui.imageListWidget.count())]
    assert all(t.endswith('ch 4') for t in texts), (texts, recorder.messages[-3:])
    sweep._select_images(w, qapp, None)
    w.ui.mcaRanLineEdit.setText('4.9:5.1')
    w.ui.mcaSumAllPushButton.click()
    qapp.processEvents()
    gui = str(tmp_path / 'gui')
    recorder.save_name = gui
    w.ui.mcaExportIntPushButton.click()
    qapp.processEvents()
    text = w.scriptView.toPlainText()
    assert 'channels=[4]' in text
    _run_script(text.replace(repr(gui), repr(str(tmp_path / 'script'))), tmp_path)
    assert open(gui + '_flu.txt', 'rb').read() == open(str(tmp_path / 'script') + '_flu.txt', 'rb').read()
    from PyQt5.QtWidgets import QPushButton
    d.findChild(QPushButton, 'prefMcaAllPushButton').click()
    assert w.prefs['mca_channels'] == []
    assert recorder.exceptions == []
