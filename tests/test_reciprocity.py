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
    relative = R.dose_or_time(burns, strip_relative=0.3)     # the scatter as a share of each rate (the truth's form)
    assert relative.p_dose > plain.p_dose and '30 % of the rate' in relative.note
    assert relative.beta_ci95[0] <= 1.0 <= relative.beta_ci95[1]       # the 95 % interval holds the truth
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


def test_rates_in_and_the_strip_scatter_from_repeats():
    """dose_or_time_rates takes a table's rates (C54's burns.csv) and gives
    what dose_or_time gives from the frames; strip_scatter_fit recovers a
    known strip scatter from repeated strips (REML), additive or relative."""
    burns, _ = bp.series(beta=1.0, fluxes=(1.0, 4.68, 10.0), change=0.1, noise=0.003, seed=2)
    frames = R.dose_or_time(burns)
    rs = [R.drift_rate(b) for b in burns]
    table = R.dose_or_time_rates([b.flux for b in burns], [v[0] for v in rs], [v[1] for v in rs])
    assert (table.verdict, table.beta, table.beta_ci) == (frames.verdict, frames.beta, frames.beta_ci)
    rng = np.random.default_rng(11)
    true_tau, true_rho = 30.0, 0.4
    add = [[(100.0 + rng.normal(0, true_tau) + rng.normal(0, 5.0), 5.0) for _ in range(3)] for _ in range(40)]
    tau, (lo, hi) = R.strip_scatter_fit(add, level=3.84)             # the 95 % interval
    assert lo <= true_tau <= hi and tau == pytest.approx(true_tau, rel=0.25)
    rel = []
    for _ in range(40):
        mu = rng.uniform(20, 500)
        rel.append([(mu * (1 + rng.normal(0, true_rho)) + rng.normal(0, 2.0), 2.0) for _ in range(3)])
    rho, (lo, hi) = R.strip_scatter_fit(rel, relative=True, level=3.84)
    assert lo <= true_rho <= hi
    with pytest.raises(ValueError):
        R.strip_scatter_fit([[(1.0, 1.0)]])

def test_repeated_strips_at_one_flux_are_pooled():
    """Strips at one flux that rise and fall are the strip scatter, not two
    processes: with the scatter admitted, the 'opposite signs' rule looks
    at each flux's pooled rate (2026-11-25; before, 'opposite signs' in 72 %
    of seeds with 4 strips per flux at ρ 1, now 0 %, measured)."""
    calls = []
    for seed in range(30):
        burns, _ = bp.series(beta=1.0, fluxes=(1.0,) * 4 + (10.0,) * 4, change=0.1, noise=0.003, strip=1.0, seed=seed)
        calls.append(R.dose_or_time(burns, strip_relative=1.0).verdict)
    assert calls.count('opposite signs') <= 3
    one, _ = bp.series(beta=1.0, fluxes=(1.0, 10.0), change=0.1, noise=0.003, seed=1)   # no repeats: as before
    assert R.dose_or_time(one).verdict == 'dose'
