"""Study A's tool (tests/tools/ref_guard_study.py, 2026-11-24): the guard's
choice redone from stored rungs is joint_factor's own, the AICc average
follows its formula (Burnham & Anderson 2002, eq. 6.12, the revised form
of Buckland et al. 1997; and the square-root form for comparison), and a
small run writes its figures, tables and summary."""
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))
import ref_guard_study as g          # noqa: E402
from lss_core import uncertainty as unc   # noqa: E402


@pytest.mark.parametrize('key', g.JOINS)
def test_stored_rung_selection_is_joint_factors_choice(key):
    """Every p of the sweep and the guard off, on three replicates of each
    join: δ and σ equal joint_factor's exactly."""
    n, bad = g.check_selection(key, range(3))
    assert n == 3 * (len(g.GUARD_PS) + 1) and bad == 0


def _table():
    """Two rungs in the largest window (±2), one in the overlap alone (±0)."""
    return dict(ladder=[(4, 2), (5, 2), (2, 0)],
                rungs=[(0.10, 0.010, 12.0, 10), (0.13, 0.012, 9.0, 9), (0.20, 0.03, 1.0, 4)],
                off=(0.10, 0.010, 12.0, 10), legacy=(0.11, 0.02))


def test_aicc_average_follows_its_formula():
    t = _table()
    K = np.array([6, 7])
    n = np.array([16, 16])
    chi2 = np.array([12.0, 9.0])
    aicc = chi2 + 2 * K + 2 * K * (K + 1) / (n - K - 1)
    w = np.exp(-0.5 * (aicc - aicc.min()))
    w /= w.sum()
    d = np.array([0.10, 0.13])
    s = np.array([unc.inflate(0.010, 12.0, 10), unc.inflate(0.012, 9.0, 9)])
    db = float(np.sum(w * d))
    got = g.average(t)
    assert got[0] == pytest.approx(db, rel=1e-12)
    assert got[1] == pytest.approx(math.sqrt(np.sum(w * (s ** 2 + (d - db) ** 2))), rel=1e-12)
    assert set(got[2]) == {0, 1}                       # the overlap-only rung fits other data: not weighed
    sq = g.average(t, sqrt_form=True)
    assert sq[1] == pytest.approx(np.sum(w * np.sqrt(s ** 2 + (d - db) ** 2)), rel=1e-12) and sq[1] <= got[1]
    assert set(g.average(t, all_windows=True)[2]) == {0, 1, 2}
    t['rungs'][:2] = [None, None]                      # no rung of the largest window fits: the next window
    assert g.average(t)[0] == pytest.approx(0.20) and set(g.average(t)[2]) == {2}


def test_guard_pick_keeps_the_first_adequate_rung_else_the_best_inflated():
    t = _table()
    assert g.guard_pick(t, 0.01) == (0, False)         # p(12, 10) = 0.285
    assert g.guard_pick(t, 0.3) == (1, False)          # p(9, 9) = 0.437
    assert g.guard_pick(t, 0.95) == (2, True)          # none adequate: the largest p, flagged
    assert g.estimate(t, 'guard_off')[:2] == (0.10, unc.inflate(0.010, 12.0, 10))
    assert g.estimate(t, 'legacy')[:2] == (0.11, 0.02)


def test_a_quick_run_writes_its_products(tmp_path):
    assert g.main(['--quick', '--out', str(tmp_path), '--figures', 'A1,A5,A8', '--procs', '1']) == 0
    for name in ('A1_what_the_fit_sees', 'A5_decision_curve', 'A8_nx_school'):
        assert (tmp_path / (name + '.png')).stat().st_size > 10000
        assert (tmp_path / (name + '.csv')).exists()
    text = (tmp_path / 'data_summary.md').read_text(encoding='utf-8')
    assert 'Not checked' in text and '| 0 |' in text           # C45 needs 400 replicates; no mismatches
    assert 'Burnham & Anderson 2002 (eq. 6.12)' in text
