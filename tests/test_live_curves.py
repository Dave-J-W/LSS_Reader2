"""SpecPlot curves keep a recipe: exp.curve(...), remade live when the scan
gains points (issue #145, its last part for SpecPlot). Before, a saved
SpecPlot curve had no recipe, so live updates could only mark it out of date."""
import numpy as np
import pytest

import sweep
from lss_core import live, workbook
from lss_core.experiment import Experiment

pytestmark = pytest.mark.gui


@pytest.mark.parametrize('normalised', [False, True])
def test_a_saved_curve_is_remade_from_its_recipe(loaded, qapp, dataset, recorder, normalised):
    w = loaded
    w.prefs['auto_save'] = False
    sweep.state_motor_scan(w, qapp, dataset)
    w.ui.spNComboBox.setCurrentIndex(w.ui.spNComboBox.findText('Monc'))
    w.ui.spNCheckBox.setChecked(normalised)
    qapp.processEvents()
    w.saveButtons['spec'].click()
    qapp.processEvents()
    wb = workbook.Workbook(w.workbookPath())
    row = wb.results(kind='scan')[-1]
    assert row['recipe'].startswith('curve = exp.curve(4, ')
    assert ("monitor='Monc'" in row['recipe']) == normalised
    call, res, used, pts = live.remake(row['recipe'], [4], Experiment(dataset))
    kind, items = live.item_for(call, res, used)
    assert kind == 'scan' and items[0]['label'] == row['label'] and used == [4]
    assert np.allclose(items[0]['data'], wb.data(row['id']))                     # the window's numbers
    if wb.fits(rid=row['id']):
        assert items[0]['fits']                                                  # the shape fit comes along
    assert recorder.exceptions == []


def test_curve_in_scripts(dataset):
    exp = Experiment(dataset)
    c = exp.curve(4, 'sh', 'Apex2', monitor='Monc', fit=True)
    assert c.columns == ['sh', 'Apex2/Monc', 'd(Apex2/Monc)'] and len(c.x) == len(c.y) == len(c.err)
    assert c.fit is not None and c.fit_label == 'Apex2 vs sh'
    assert 'exp.curve(4' in live.with_scans("curve = exp.curve(4, 'sh', 'Apex2')", [4, 5])   # one scan: kept
    with pytest.raises(ValueError):
        exp.curve(4, 'sh', 'nope')
