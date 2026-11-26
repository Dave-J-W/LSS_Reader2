"""The older Fit Peak dialog's Accept appends one row to the MCA integral
list. Since F110 (2026-11-26) Fit lines leaves 7-column rows (the reader's
fit's I, dI, then XeRay's) and a Merge leaves an array; an accepted row must
join either without breaking the plot, the export or the workbook save
(release push, 2026-11-26: crashes in the main workflows)."""
import numpy as np
import pytest

import sweep
import synth

pytestmark = pytest.mark.gui

WINDOW = '5.6:7.2'


@pytest.fixture
def xf(window, qapp, tmp_path):
    spec, truth = synth.make_xfntr_dataset(tmp_path / 'xf')
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    window.prefs['auto_save'] = False
    qapp.processEvents()
    sweep._select_scans(window, qapp, None)
    sweep._select_images(window, qapp, None)
    return window


def _accept_one(w, qapp, row=4):
    sweep._select_images(w, qapp, [row])
    w.ui.mcaFitPushButton.click()
    qapp.processEvents()
    d = w.uipeakfit
    d.rangeLineEdit.setText(WINDOW)
    for j, v in enumerate((6.3, 1e-2, 0.1)):
        d.peakTW.item(0, j).setText(str(v))
    d.fitPushButton.click()
    qapp.processEvents()
    w.ui.mcaAcceptPushButton.click()



def test_accept_after_fit_lines(xf, qapp, recorder, tmp_path):
    w = xf
    w.mcaFitLinesPushButton.click()
    qapp.processEvents()
    n = len(w.mcaIntData)
    assert n and len(w.mcaIntData[0]) >= 7
    _accept_one(w, qapp)
    rows = w.mcaIntData
    assert len(rows) == n + 1 and len({len(r) for r in rows}) == 1        # one width for every row
    assert np.isnan(rows[-1][5]) and np.isnan(rows[-1][6])                # no XeRay fit for that point
    w.updateMcaIntPlot()
    assert not any('no mca integral data' in m for m in recorder.messages)
    w.saveButtons['mca'].click()
    qapp.processEvents()
    recorder.save_name = str(tmp_path / 'flu')
    w.mcaSaveIntData()
    flu = np.loadtxt(str(tmp_path / 'flu_flu.txt'))
    xeray = np.loadtxt(str(tmp_path / 'flu_flu_xeray.txt'))
    assert len(flu) == n + 1 and len(xeray) == n                          # the accepted point has no XeRay fit
    assert np.all(np.isfinite(xeray))
    assert recorder.exceptions == []


def test_accept_after_a_merge(xf, qapp, recorder):
    """Before the fix the append failed on the array ('numpy.ndarray' has no append)."""
    from lss_core import fluorescence
    w = xf
    w.ui.mcaRanLineEdit.setText(WINDOW)
    w.ui.mcaSumAllPushButton.click()
    qapp.processEvents()
    w.mcaIntData = fluorescence.merge_rows(w.mcaIntData, 'frame', 0.0)    # as Merge leaves them
    n = len(w.mcaIntData)
    _accept_one(w, qapp)
    assert len(w.mcaIntData) == n + 1
    w.updateMcaIntPlot()
    w.saveButtons['mca'].click()
    qapp.processEvents()
    assert recorder.exceptions == []
