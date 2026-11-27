"""Line cuts are remade live with their peak fits (issue #145, second part).

A saved cut's recipe is the Script pane's ``cut = exp.cut(...)``, with the
fit "Fit peaks" made (``fits = cut.fit(peaks.FitOptions(...))``) when the cut
was fitted. Before #145 the live parser accepted neither ``exp.cut`` nor
``absorbers.calibrated`` (the foils), so a stale cut could only be marked."""
import numpy as np
import pytest

import sweep
import synth
from lss_core import live, workbook
from lss_core.experiment import Experiment
from lss_core.peaks import FitOptions


def test_a_fitted_cut_recipe_is_parsed_and_remade(tmp_path):
    spec = synth.make_dataset(tmp_path / 'data')
    recipe = ("from lss_core import absorbers\nfrom lss_core import peaks\n"
              "cut = exp.cut([1, 2], 'Pix H', (90.0, 110.0), absfac=absorbers.calibrated(10.0))\n"
              "cut.save('result')\nfits = cut.fit(peaks.FitOptions(shape='gaussian', n_peaks=1))")
    call = live.parse(recipe)
    assert call.method == 'cut' and call.fitted and call.fit == FitOptions(shape='gaussian', n_peaks=1)
    assert call.kwargs['absfac'].energy_kev == 10.0                   # the foils, rebuilt from literals
    call, res, used, pts = live.remake(recipe, [1, 2], Experiment(spec))
    kind, items = live.item_for(call, res, used)
    assert kind == 'line cut' and len(items) == len(res.cuts) > 1
    assert items[0]['label'].startswith('S# 1 F# ') and items[0]['columns'] == ['Pix x', 'I', 'dI']
    assert items[0]['fits'] and items[0]['fits'][0][1][0].peaks                 # the fit came along
    plain = live.item_for(*live.remake(recipe.rsplit('\n', 1)[0], [1], Experiment(spec))[:2], [1])[1]
    assert plain[0]['fits'] == []
    summed = live.parse("cut = exp.cut([1], 'Pix H', (90, 110), summed=True)\ncut.summed_label = 'S# 1'")
    assert summed.summed_label == 'S# 1' and not summed.fitted
    with pytest.raises(live.RecipeError):
        live.parse("cut = exp.cut([1], 'Pix H', (90, 110))\nother.fit(None)")


@pytest.mark.gui
def test_a_saved_fitted_cut_is_remade_with_its_fit(loaded, qapp, dataset, recorder):
    w = loaded
    w.prefs['auto_save'] = False
    sweep.state_pilatus_one_frame(w, qapp, dataset)
    w.ui.pilCutDirComboBox.setCurrentIndex(2)
    w.ui.pilIntRangeLineEdit.setText('90:110')
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    w.cutFitPushButton.click()
    w.saveButtons['cut'].click()
    qapp.processEvents()
    wb = workbook.Workbook(w.workbookPath())
    row = wb.results(kind='line cut')[0]
    assert 'fits = cut.fit(peaks.FitOptions(' in row['recipe']
    live.parse(row['recipe'])                                       # accepted now
    w.remakeStale(wb, {row['id']: 'test'})
    w.finishRemakes()
    rows = workbook.Workbook(w.workbookPath()).results(kind='line cut')
    assert len(rows) == 2 and rows[1]['origin'] == 'live' and rows[1]['label'] == row['label']
    assert workbook.Workbook(w.workbookPath()).fits(rid=rows[1]['id'])     # remade with its fit
    assert np.allclose(workbook.Workbook(w.workbookPath()).data(rows[1]['id']), wb.data(row['id']))
    assert recorder.exceptions == []
