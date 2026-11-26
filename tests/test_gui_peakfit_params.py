"""The Plot tab's Fit Peak dialog exports its parameters when lmfit could
not estimate the errors (release push, 2026-11-26): lmfit then leaves every
stderr None (an exact or degenerate fit, a parameter at its bound), and
formatting None raised a TypeError half-way through the file. A missing
error is now written 'nan'; the file is complete."""
import numpy as np
import pytest

pytestmark = pytest.mark.gui


def _fit_and_export(w, qapp, recorder, tmp_path, y):
    x = np.linspace(-1.0, 1.0, 41)
    f = tmp_path / 'peak.txt'
    np.savetxt(f, np.column_stack([x, y, np.sqrt(np.maximum(y, 1.0))]))
    w.directory = str(tmp_path)
    w.plotfiles = [str(f)]
    w.updatePlotFile()
    w.ui.plotFileListWidget.item(0).setSelected(True)
    qapp.processEvents()
    w.updateSelectedPlotFile()
    w.ui.plotPFPushButton.click()
    qapp.processEvents()
    d = w.uipeakfit
    d.rangeLineEdit.setText('-1:1')
    d.bgTW.item(0, 0).setText('10')
    d.peakTW.selectAll()                                     # the peak varies; the background is fixed
    d.fitPushButton.click()
    qapp.processEvents()
    recorder.save_name = str(tmp_path / 'p')
    d.exportParaPushButton.click()
    qapp.processEvents()
    lines = open(str(tmp_path / 'p_par.txt')).read().splitlines()
    return {l.split(':')[0]: l.split('\t') for l in lines if ':\t' in l and l.startswith(('Peak #', 'Background'))}


X = np.linspace(-1.0, 1.0, 41)
EXACT = 300.0 * np.exp(-X ** 2 / 2 / 0.2 ** 2) + 10.0


def test_no_error_estimate_writes_nan_and_a_whole_file(window, qapp, recorder, tmp_path):
    rows = _fit_and_export(window, qapp, recorder, tmp_path, EXACT)       # an exact fit: no error estimate
    assert window.peakresult.errorbars is False
    assert recorder.exceptions == []
    assert set(rows) == {'Peak #1 pos', 'Peak #1 int', 'Peak #1 wid', 'Background C0'}
    assert all(r[3] == 'nan' for r in rows.values())
    assert float(rows['Peak #1 wid'][1]) == pytest.approx(0.2, rel=1e-3)


def test_with_error_estimates_the_numbers_are_written(window, qapp, recorder, tmp_path):
    y = np.random.default_rng(4).poisson(EXACT).astype(float)
    rows = _fit_and_export(window, qapp, recorder, tmp_path, y)
    assert recorder.exceptions == []
    assert float(rows['Peak #1 pos'][3]) > 0 and rows['Background C0'][2] == 'False'
