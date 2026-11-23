"""The MCA line-fit gauntlet (tests/tools/mca_fit_gauntlet.py, F90): its
own pieces are right (the linear step is the reader's, the Poisson step
removes Neyman's bias, escape stripping removes the escapes, the truth is
accounted for), and a small run writes its tables and figures."""
import csv
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))
import mca_fit_gauntlet as g          # noqa: E402
from lss_core import peaks            # noqa: E402
from synthetic import mca             # noqa: E402


def _series(cond, n, seed):
    s = cond.spectrum()
    rng = np.random.default_rng(seed)
    counts = [s.draw(rng) for _ in range(n)]
    data = [g.normalise(c, s.calib) for c in counts]
    return s, data, data[0][:, 0], [d[:, 1] for d in data], [d[:, 2] for d in data]


def test_the_linear_step_is_the_readers():
    """linear_step with data weights gives fit_series' per-spectrum heights
    and errors exactly (so fit_known and fit_irls differ from the reader
    only where they say)."""
    cond = g.core()['smooth']
    s, data, x, Y, S = _series(cond, 5, 1)
    o = g.fit_options(cond, [cond.line])
    ref, each = peaks.fit_series(x, Y, S, o)
    assert ref.ok and len(each) == 5
    mine = g.linear_step(x, Y, S, ref, o, 'data')
    for r, (coef, err) in zip(each, mine):
        assert coef[0] == pytest.approx(r.peaks[0].height, rel=1e-9)
        assert err[0] == pytest.approx(r.peaks[0].height_err, rel=1e-9)


def test_model_weights_remove_neymans_bias_at_low_counts():
    """A clean line of ~300 counts on 1 count per channel: weights from the
    data pull the area low (Neyman's χ²); the Poisson step does not
    (measured, 2026-11-23: about −2.5 % against −0.1 %)."""
    cond = g.replace(g.core()['clean'], photons=340.0)
    est = {'fit': [], 'fit_irls': []}
    for seed in range(30):
        s = cond.spectrum()
        rng = np.random.default_rng([4, seed])
        counts = [s.draw(rng) for _ in range(cond.series)]
        r = g.estimate(cond, [s] * cond.series, counts, ['fit', 'fit_irls'])
        for m in est:
            est[m] += [v[0] / v[2] - 1 for v in r[m] if v is not None]
    fit, irls = np.mean(est['fit']), np.mean(est['fit_irls'])
    se = np.std(est['fit']) / np.sqrt(len(est['fit']))
    assert fit < -3 * se and fit < -0.01
    assert abs(irls) < max(3 * se, 0.005)


def test_escape_stripping_removes_the_escapes():
    """On the expected spectrum, stripping leaves the escape-free spectrum
    to within the width mismatch (the escape's resolution is that of the
    lower energy): under 5 % of the escape counts in any band."""
    cond = g.replace(g.core()['smooth'], detector=mca.Detector(escape=1.0))
    s = cond.spectrum()
    s0 = g.replace(cond, detector=mca.Detector(escape=0.0)).spectrum()
    d = g.strip_escape(g.normalise(s.expected, s.calib), 1.0)
    e = d[:, 0]
    diff = d[:, 1] * g.scale() - s0.expected
    esc = s.part(None, ['escape'])
    for a, b in [(7.9, 8.2), (8.2, 8.35), (8.35, 8.6), (8.6, 9.2)]:
        m = (e >= a) & (e < b)
        assert abs(diff[m].sum()) < 0.05 * esc[(e >= 7.9) & (e < 8.6)].sum() + 1.0, (a, b)
    raw = g.normalise(np.r_[np.zeros(5), np.ones(s.energy.size - 5)], s.calib)
    assert np.all(g.strip_escape(raw)[:5, 2] == 0)               # zero counts keep σ = 0, as the reader has them


def test_the_window_truth_is_the_photopeak_in_the_box():
    """The window sum's excess over its truth is exactly the rest of the
    spectrum in the box (expected values)."""
    cond = g.core()['hard']
    s = cond.spectrum()
    lo, hi = cond.box_range()
    r = g.estimate(cond, [s], [s.expected], ['window'])['window'][0]
    box = (s.energy >= lo) & (s.energy <= hi)
    assert r[2] == pytest.approx(s.photopeak('Zn')[box].sum(), rel=1e-12)
    assert r[0] - r[2] == pytest.approx((s.expected - s.photopeak('Zn'))[box].sum(), rel=1e-9)


def test_known_centres_are_where_the_physics_puts_them():
    cond = g.replace(g.core()['hard_cu'], box=3.0)
    c = g.known_centres(cond)
    assert c[0] == cond.line
    assert any(abs(v - 8.260) < 1e-9 for v in c)                    # the elastic's escape
    assert any(abs(v - (mca.compton_energy(10, 90) - 1.740)) < 1e-9 for v in c)
    assert any(abs(v - mca.line_energy('Cu')) < 1e-9 for v in c)
    assert g.known_centres(g.core()['smooth']) == [g.core()['smooth'].line]   # no escapes, no neighbours


def test_a_small_run_writes_everything(tmp_path):
    out = tmp_path / 'g'
    g.main(['--out', str(out), '--design', 'all', '--replicates', '3', '--random', '2', '--random-replicates', '2',
            '--series-replicates', '2', '--conditions', 'clean,smooth,hard,random_000,xfntr_smooth', '--jobs', '2'])
    for name in ('conditions.csv', 'verdict.csv', 'pooled.csv', 'series.csv', 'series_verdict.csv', 'f90.csv',
                 'summary.md', 'hard_case.png', 'series.png', 'log.txt'):
        assert (out / name).is_file(), name
    with open(out / 'verdict.csv') as f:
        rows = list(csv.DictReader(f))
    assert {r['condition'] for r in rows} == {'clean', 'smooth', 'hard', 'random_000'}
    assert {r['method'] for r in rows} == set(g.KEY_METHODS)
    hard_window = next(r for r in rows if r['condition'] == 'hard' and r['method'] == 'window')
    assert float(hard_window['rel_bias']) > 1.0                     # the box holds more scatter than line
    text = (out / 'summary.md').read_text()
    assert '## Verdict per method' in text and '## Series' in text and 'xfntr_smooth' in text
