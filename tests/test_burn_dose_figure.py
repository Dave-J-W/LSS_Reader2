"""tests/tools/burn_dose_figure.py (F76, 2026-11-23): burn quantities
against dose as well as time. The dose is the cumulative Monc times the
foils' transmission; slopes and ratios as the figure states them."""
import json
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))
import burn_dose_figure as bd  # noqa: E402


def test_slope_of_a_line_and_its_error():
    x = np.arange(20.0)
    y = 2.0 + 0.5 * x
    s, e = bd.slope(x, y, np.full(20, 0.1))
    assert s == pytest.approx(0.5) and e > 0
    assert np.isnan(bd.slope(x[:2], y[:2], [1, 1])[0])


def test_a_dose_effect_coincides_against_dose():
    """Two synthetic burns at flux ratio 4: a drift proportional to the dose
    gives a dose-slope ratio of 1 and a time-slope ratio of 4."""
    t = np.arange(21) * 10.0
    series = []
    for scan, T in ((1, 0.01), (2, 0.04)):
        dose = np.cumsum(np.full(21, 3e6) * T) / 1e6
        y = 1.46 + 0.003 * dose
        series.append(dict(scan=scan, absorber=0, transmission=T, t=t.copy(), dose=dose,
                           values={'centre': (y, np.full(21, 1e-5))}))
    out = bd.analyse(series)
    r = out['ratios']['centre']
    assert out['flux_ratio'] == pytest.approx(4.0)
    assert r['significant'] and r['vs_dose'] == pytest.approx(1.0) and r['vs_time'] == pytest.approx(4.0)


def test_nx_burns_14_and_15(tmp_path):
    assert bd.main(['--out', str(tmp_path)]) == 0
    with open(tmp_path / 'summary_14_15.json', encoding='utf-8') as f:
        s = json.load(f)
    assert s['absorbers'] == [12, 8]
    from lss_core import absorbers
    cal = absorbers.calibrated(10.0)
    assert s['flux_ratio'] == pytest.approx(absorbers.attenuation(cal, 12) / absorbers.attenuation(cal, 8), rel=1e-3)
    pos = s['ratios']['centre']
    assert pos['significant'] and pos['vs_time'] > 3 and 0.6 < pos['vs_dose'] < 1.2     # measured 3.70, 0.79
    assert not s['ratios']['intensity']['significant']
    d = np.genfromtxt(tmp_path / 'dose_14_15.csv', delimiter=',', names=True)
    assert np.all(np.diff(d['dose_1e6'][d['scan'] == 14]) > 0)
    assert os.path.exists(tmp_path / 'dose_14_15.png')
