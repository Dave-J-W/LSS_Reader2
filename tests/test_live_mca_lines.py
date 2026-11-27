"""MCA "Fit lines" keeps a recipe: scriptable and remade live (issue #145).

Before #145 a Fit lines result was saved without a recipe ("these
intensities came from peak fits"), so live updates could only mark it out
of date. Its recipe is now exp.fluorescence(...) followed by
flu.fit_lines(...) with the fit the window made."""
import os

import numpy as np
import pytest

import sweep
from lss_core import live, workbook
from lss_core.experiment import Experiment

pytestmark = pytest.mark.gui


def test_the_recipe_remakes_the_windows_rows(loaded, qapp, dataset, recorder, tmp_path):
    w = loaded
    w.prefs['auto_save'] = False
    sweep.state_mca_frames(w, qapp, dataset)
    w.mcaFitLinesPushButton.click()
    qapp.processEvents()
    rows = np.asarray(w.mcaIntData, float)
    assert rows.shape[1] == 7
    recipe = w.recipe(w.fluorescenceScript)
    assert 'flu.fit_lines(peaks.FitOptions(' in recipe and 'exp.fluorescence(' in recipe
    call, res, used, pts = live.remake(recipe, w.mcaSumScript[0], Experiment(dataset))
    assert np.allclose(np.asarray(res.rows, float), rows, equal_nan=True, rtol=1e-9)   # the window's numbers
    kind, items = live.item_for(call, res, used)
    assert kind == 'fluorescence' and items[0]['columns'][-2:] == ['I_xeray', 'dI_xeray']
    assert items[0]['fits'] and items[0]['fits'][0][0].startswith('sum of')
    res.save(str(tmp_path / 'scripted'), x='qz')                                     # the files the window writes
    assert os.path.exists(str(tmp_path / 'scripted_flu.txt'))
    assert os.path.exists(str(tmp_path / 'scripted_flu_xeray.txt'))
    w.saveButtons['mca'].click()
    qapp.processEvents()
    row = workbook.Workbook(w.workbookPath()).results(kind='fluorescence')[-1]
    assert row['recipe'] and live.parse(row['recipe']).lines is not None             # saved with its recipe
    assert recorder.exceptions == []


def test_sum_all_keeps_its_plain_recipe(loaded, qapp, dataset, recorder):
    w = loaded
    sweep.state_mca_frames(w, qapp, dataset)
    w.mcaFitLinesPushButton.click()
    qapp.processEvents()
    w.ui.mcaSumAllPushButton.click()                         # back to window sums: no fit in the recipe
    qapp.processEvents()
    assert 'fit_lines' not in w.recipe(w.fluorescenceScript)
    assert recorder.exceptions == []
