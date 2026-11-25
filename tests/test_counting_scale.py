"""The budget model's scale on the counting part of a reflectivity point's
error (lss_core.errors.ErrorModel.counting_scale; C63 measured s ≈ 1.12, C64
showed it explains and fixes the real splits' under-coverage). An option, 1
by default, until rule 12 and the owner's word (MQ-3).

Invariant: the values never change; only the counting part of the error is
scaled, so err(s)² − err(1)² = (s² − 1) × the counting part; s = 1 is the
budget model as before; the legacy model refuses a scale (its numbers never
change)."""
import numpy as np
import pytest

import synth
from lss_core import reflectivity as refl
from lss_core.errors import ErrorModel, as_model, script_kw
from lss_core.experiment import Experiment
from TwoDDetector import TwoDDetector
from synthetic import xrr, xrr_images as xi, xrr_scans as xs


def _row(model, img, monitor=1.0e5, qz=0.05):
    d = TwoDDetector('Pilatus')
    d.errors = model
    row, _ = refl.frame_row(d, img, np.sqrt(np.maximum(img, 0)), monitor, (synth.DB_X, synth.DB_Y), qz,
                            xi.SLIT, xi.BG_OFFSET_DEG, 'H', synth.S2D, low_qz_slit=False)
    return row, d.roiParts


def _frame(seed=1):
    bl = xs.Beamline(**xs.REAL_MONITOR)
    r = xs.measure(xrr.bare_water(), xs.chain_plan([(0.03, 0.08, 0.005)], overlap=0), beamline=bl, seed=seed)
    rec = r.scans[sorted(r.scans)[0]]
    return xi.frame(rec, 3, np.random.default_rng(seed))


def test_only_the_counting_part_is_scaled():
    img = _frame()
    one, parts = _row(as_model('budget'), img)
    s = 1.12
    scaled, _ = _row(as_model({'mode': 'budget', 'counting_scale': s}), img)
    assert scaled[1] == one[1] and scaled[0] == one[0]               # the value never changes
    cS, cL, cR = parts['counting']
    counting = cS ** 2 + (cL ** 2 + cR ** 2) / 4
    assert scaled[2] ** 2 - one[2] ** 2 == pytest.approx((s ** 2 - 1) * counting, rel=1e-9)
    assert scaled[2] > one[2]
    same, _ = _row(as_model({'mode': 'budget', 'counting_scale': 1.0}), img)
    assert same[2] == one[2]


def test_the_model_round_trips_and_legacy_refuses():
    m = as_model({'mode': 'budget', 'counting_scale': 1.12})
    assert m.counting_scale == 1.12 and 'counting part x 1.12' in m.describe()
    kw = script_kw(m)
    assert "'counting_scale': 1.12" in kw
    assert as_model(eval(kw[len('errors='):])).counting_scale == 1.12
    assert 'counting_scale' not in script_kw(as_model('budget'))
    with pytest.raises(ValueError):
        ErrorModel('legacy', counting_scale=1.12)
    with pytest.raises(ValueError):
        as_model({'mode': 'budget', 'counting_scale': 0})


def test_experiment_reflectivity_values_unchanged_errors_scaled(tmp_path):
    d = xs.measure(xrr.bare_water(), xs.chain_plan([(0.015, 0.045, 0.0025), (0.04, 0.12, 0.005)], overlap=3),
                   seed=3)
    spec = xi.render(d, tmp_path, 'xrr')
    exp = Experiment(spec)
    scans = sorted(d.scans)
    base = exp.reflectivity(scans, errors='budget')
    scaled = exp.reflectivity(scans, errors={'mode': 'budget', 'counting_scale': 1.12})
    for n in scans:
        a, b = base.per_scan[n], scaled.per_scan[n]
        assert np.array_equal(a[:, 1], b[:, 1])                          # the values
        ratio = b[:, 2] / a[:, 2]
        assert np.all(ratio > 1.0) and np.all(ratio <= 1.12 + 1e-12)     # the monitor part is not scaled
    assert np.median(scaled.ref[:, 2] / base.ref[:, 2]) > 1.05           # the curve's error column follows
