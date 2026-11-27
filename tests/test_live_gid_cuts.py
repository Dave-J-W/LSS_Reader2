"""GID cuts keep a recipe: the GID map's exp.gid(...) and cut = gid.cut(...),
remade live with the map (issue #145, its last part). Before, a GID cut was
saved without a recipe and could only be marked out of date."""
import os

import numpy as np
import pytest

from lss_core import live

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')


def test_the_gid_cut_line_is_parsed_and_kept():
    recipe = "gid = exp.gid([11], axes='Q')\ngid.save('result')\ncut = gid.cut('Q H', (0.1, 0.2))"
    call = live.parse(recipe)
    assert call.method == 'gid' and call.gid_cut == (['Q H', (0.1, 0.2)], {})
    again = live.with_scans(recipe, [11, 12])
    assert "exp.gid([11, 12]" in again and "gid.cut('Q H', (0.1, 0.2))" in again    # the cut's own line untouched
    with pytest.raises(live.RecipeError):
        live.parse("gid = exp.gid([11])\ncut = other.cut('Q H', (0.1, 0.2))")


@pytest.mark.gui
@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school sample data not present')
@pytest.mark.parametrize('direction', [0, 1])
def test_a_saved_gid_cut_is_remade_from_its_recipe(window, qapp, recorder, tmp_path, direction):
    import sweep
    from lss_core import workbook
    from lss_core.experiment import Experiment
    w = window
    w.openSpecFile(fname=NX)
    w.directory = str(tmp_path)
    w.prefs['auto_save'] = False
    qapp.processEvents()
    sweep._select_scans(w, qapp, [10])                       # scan 11, a GID scan
    sweep._select_images(w, qapp)
    w.gidPatchPushButton.click()
    qapp.processEvents()
    axis = w.pilGIDYAxs_Q[:, 0] if direction == 0 else w.pilGIDXAxs_Q[0, :]
    lo, hi = float(axis[len(axis) // 3]), float(axis[2 * len(axis) // 3])
    w.ui.pilCutDirComboBox.setCurrentIndex(direction)
    w.ui.pilIntRangeLineEdit.setText('%r:%r' % (lo, hi))
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    w.saveButtons['cut'].click()
    qapp.processEvents()
    wb = workbook.Workbook(w.workbookPath())
    row = wb.results(kind='gid cut')[-1]
    assert row['label'].startswith('GID cut, ') and 'cut = gid.cut(' in row['recipe']
    call, res, used, pts = live.remake(row['recipe'], [11], Experiment(NX))
    kind, items = live.item_for(call, res, used)
    assert kind == 'gid cut' and row['label'].startswith(items[0]['label'] + ',')
    assert np.allclose(items[0]['data'], wb.data(row['id']), equal_nan=True)     # the window's cut
    assert recorder.exceptions == []
