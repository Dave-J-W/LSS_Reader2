"""Beam damage or a sample changing by itself (F76, lss_core.reciprocity,
2026-11-25): burns at several fluxes; the drift rate goes as flux^β, β = 1
the dose, β = 0 time. Synthetic truth from synthetic.burn_pairs."""
import math
import os

import numpy as np
import pytest

from lss_core import reciprocity as R
from synthetic import burn_pairs as bp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')


def test_the_drift_rate_of_one_burn():
    burns, truth = bp.series(beta=1.0, fluxes=(1.0, 2.0), change=0.2, noise=1e-4, seed=1)
    for b, true in zip(burns, truth['rates']):
        rate, s = R.drift_rate(b)
        assert rate == pytest.approx(true, rel=0.01)        # ln y: an exponential's rate exactly
        assert 0 < s < abs(rate) / 10
    add = R.Burn(np.arange(10.0), 1.5 + 0.002 * np.arange(10.0), np.full(10, 1e-4), 1.0, relative=False)
    assert R.drift_rate(add)[0] == pytest.approx(0.002, rel=1e-6)   # a position: the slope itself
    assert math.isnan(R.drift_rate(R.Burn(np.arange(2.0), np.ones(2), np.ones(2), 1.0))[0])


@pytest.mark.parametrize('beta, verdict', [(1.0, 'dose'), (0.0, 'time')])
def test_a_clear_truth_is_called(beta, verdict):
    burns, _ = bp.series(beta=beta, fluxes=(1.0, 4.68, 10.0), change=0.1, noise=0.003, seed=2)
    v = R.dose_or_time(burns)
    assert v.verdict == verdict
    assert v.beta == pytest.approx(beta, abs=0.15)
    assert v.beta_ci[0] <= beta <= v.beta_ci[1] or abs(v.beta - beta) < 0.1
    assert (v.weight_dose > 0.99) == (beta == 1.0)
    assert verdict in v.note or ('dose' if beta else 'time') in v.note


def test_what_cannot_be_told():
    flat, _ = bp.series(beta=None, noise=0.01, seed=3)
    assert R.dose_or_time(flat).verdict == 'no change'
    tiny, _ = bp.series(beta=1.0, fluxes=(1.0, 1.5), change=0.01, noise=0.002, frames=21, seed=4)
    assert R.dose_or_time(tiny).verdict in ('cannot tell', 'no change')
    up, _ = bp.series(beta=1.0, fluxes=(1.0,), change=0.2, noise=0.002, seed=5, rise=True)
    down, _ = bp.series(beta=1.0, fluxes=(4.0,), change=0.2, noise=0.002, seed=6)
    assert R.dose_or_time(up + down).verdict == 'opposite signs'
    steep, _ = bp.series(beta=2.5, fluxes=(1.0, 3.0, 9.0), change=0.03, noise=0.001, seed=7)
    v = R.dose_or_time(steep)
    assert v.verdict == 'neither' and v.beta > 1.5           # a dose-rate effect: neither pure law


def test_strip_scatter_and_refusals():
    burns, truth = bp.series(beta=1.0, fluxes=(1.0, 2.0, 4.0, 8.0), change=0.1, noise=0.001, strip=0.3, seed=8)
    plain = R.dose_or_time(burns)
    tau = 0.3 * float(np.median(np.abs(truth['rates'])))
    widened = R.dose_or_time(burns, strip_scatter=tau)
    assert widened.p_dose > plain.p_dose                     # the strips' scatter, admitted, lets β = 1 pass
    assert widened.beta_ci[1] - widened.beta_ci[0] > plain.beta_ci[1] - plain.beta_ci[0]
    assert 'strip scatter' in widened.note
    with pytest.raises(ValueError):
        R.dose_or_time(burns[:1])
    same = [R.Burn(b.t, b.y, b.sigma, 1.0) for b in burns[:2]]
    with pytest.raises(ValueError):
        R.dose_or_time(same)


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
def test_nx_school_burns_14_and_15():
    """Two GID burns of one spot, absorbers 12 and 8 (flux ×4.68, the
    calibrated foils): the position drifts 3.7 × faster in 15, so β = 0.85
    ± 0.04, close to the dose and far from time; on counting errors alone
    β = 1 fails narrowly (p 0.004): 'neither', with all the weight on the
    dose. The intensity changes in neither burn. Measured 2026-11-25."""
    from lss_core.experiment import Experiment
    e = Experiment(NX)
    r14, r15 = e.burn(14), e.burn(15)
    c = R.dose_or_time([R.from_result(r, 'centre') for r in (r14, r15)])
    assert c.verdict == 'neither' and c.beta == pytest.approx(0.85, abs=0.03) and c.weight_dose > 0.99
    assert c.rates[1][1] / c.rates[0][1] == pytest.approx(4.68, rel=0.01)
    assert R.dose_or_time([r14, r15]).verdict == 'no change'           # intensity: BurnResults directly
    tau = 0.1 * c.rates[1][2]                                          # 10 % strip scatter: then the dose
    assert R.dose_or_time([R.from_result(r, 'centre') for r in (r14, r15)], strip_scatter=tau).verdict == 'dose'
