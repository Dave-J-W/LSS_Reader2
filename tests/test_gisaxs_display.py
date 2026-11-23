"""'Show GISAXS' wherever the direct beam is: at, right of or left of the centre
(found while testing the per-Monc GISAXS, 2026-11-23).

The Qxy bin count was len(row) × (whole span) / (last column − first
column) of the first row. |Qxy| folds at the direct beam, so with the beam
centred (column 97 of the Pilatus 100K's 195, the synthetic data's) the two
ends have the same Qxy: a division by zero and OverflowError; right of the
centre the count was negative and np.linspace raised ValueError. Now the
size of the difference, the row's full span (max − min) when it is zero, as
many bins as columns when that is zero too; left of the centre unchanged."""
import numpy as np
import pytest

import sweep

pytestmark = pytest.mark.gui


def _show_gisaxs(w, qapp):
    i = w.ui.gisaxsComboBox.findText('Show GISAXS')
    w.ui.gisaxsComboBox.setCurrentIndex(i)
    w.ui.gisaxsComboBox.activated.emit(i)
    qapp.processEvents()


@pytest.mark.parametrize('column', [None, 140, 60])       # None: the SPEC header's, centred
def test_show_gisaxs_wherever_the_beam(loaded, qapp, recorder, column):
    w = loaded
    sweep._select_scans(w, qapp, [1])
    sweep._select_images(w, qapp, [0])
    if column is not None:
        w.ui.pilSpecCheckBox.setChecked(False)
        w.ui.pilSDDistLineEdit.setText('600')
        w.ui.pilDBPosLineEdit.setText('%d,100' % column)
    _show_gisaxs(w, qapp)
    assert recorder.exceptions == []
    if column is None:
        assert w.xcenter[0] == (w.pilatus.NCOLS - 1) / 2                    # the case that divided by zero
    qxy = w.pilXbin[0]
    assert len(qxy) >= w.pilatus.NCOLS and np.all(np.diff(qxy) > 0)
    assert w.pilDataBin.shape == w.pilXbin.shape
