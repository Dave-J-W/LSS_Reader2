"""The exported _rrf.txt (and the workbook's R/RF) must be the R/R_F of the
curve exported beside it (release push, 2026-11-26; blocker 2, wrong
numbers in a file xmodfit reads). R/R_F was computed only while the R/RF
box was ticked and never cleared, so after unticking it and changing the
curve, Export wrote the old curve's R/R_F beside the new _ref.txt."""
import numpy as np
import pytest

import sweep

pytestmark = pytest.mark.gui


def test_no_stale_rrf_after_unticking(loaded, qapp, recorder, tmp_path):
    w = loaded
    w.directory = str(tmp_path)
    w.prefs['auto_save'] = False
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    w.ui.refRRFCheckBox.setChecked(True)
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    w.uirefpatch.nextPushButton.click()
    qapp.processEvents()
    assert w.RrfData is not None and len(w.RrfData)
    w.ui.refRRFCheckBox.setChecked(False)
    qapp.processEvents()
    w.ui.refNormLineEdit.setText('0.5')                              # the curve changes: normalised by 0.5
    w.ui.refNormFacCheckBox.setChecked(True)
    qapp.processEvents()
    w.updateRefPlotData()
    recorder.save_name = str(tmp_path / 'film')
    w.ui.refExportPushButton.click()
    ref = np.loadtxt(str(tmp_path / 'film_ref.txt'))
    rrf = np.loadtxt(str(tmp_path / 'film_rrf.txt'))                  # always written (owner, 2026-11-26)
    rf = w.fresnel(ref[:, 0] + w.refQoff, w.refQc)
    assert rrf[:, 1] == pytest.approx(ref[:, 1] / rf, rel=1e-3)        # the R/R_F of this curve
    items = w.refWorkbookItems()
    for it in items:
        if it['label'] == 'R/RF':
            rf = w.fresnel(np.asarray(it['data'])[:, 0], w.refQc)
            assert np.asarray(it['data'])[:, 1] == pytest.approx(np.asarray(w.normRefData)[:, 1] / rf, rel=1e-3)
    assert recorder.exceptions == []
