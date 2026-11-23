"""Three crashes the crash sweep's random walks reached on 2026-11-23 (found
by the Tools-menu session; the walks' draws shifted with its new control).
They were latent on main; each is fixed in the window."""
import numpy as np
import pytest

import sweep

pytestmark = pytest.mark.gui


def test_ref_close_up_with_vertical_background(loaded, qapp, recorder, dataset):
    """refQzListSelectionChanged scaled the vertical-background close-up with
    the horizontal background's centres (bglcen, bgrcen), which setROI sets
    only for 'H': AttributeError on a fresh detector, a stale region after
    an 'H' run. Now the region the close-up shows."""
    sweep.state_pilatus_two_scans_all_frames(loaded, qapp, dataset)
    loaded.ui.refBGDirComboBox.setCurrentIndex(loaded.ui.refBGDirComboBox.findText('V'))
    qapp.processEvents()
    loaded.ui.pilRefPushButton.click()                     # a fresh detector: no 'H' centres at all
    qapp.processEvents()
    assert loaded.ui.refQzListWidget.count() > 0
    loaded.ui.refCenCheckBox.setChecked(True)
    loaded.ui.refQzListWidget.clearSelection()
    loaded.ui.refQzListWidget.item(0).setSelected(True)
    qapp.processEvents()
    assert recorder.exceptions == []
    d = loaded.pilatus
    s, c = loaded.slit, loaded.cen
    shown = d.imageData[max(0, d.bgucen - s[1]):d.bgdcen + s[1] + 1, c[0] - s[0]:c[0] + s[0] + 1]
    assert loaded.vmax == pytest.approx(np.max(shown))
