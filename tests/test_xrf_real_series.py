"""The XRF shootout on real lines (tests/tools/xrf_real_series.py,
2026-11-25). The real series are private, so these tests use a small
stand-in for the bundle: the statistics, the calibration convention and the
line finder, with known answers."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))

import xrf_real_series as R      # noqa: E402
from synthetic import mca_more as mm   # noqa: E402


def test_unbiased_honest_estimates_read_zero_bias_and_unit_pulls():
    rng = np.random.default_rng(3)
    n, truth, sig = 21, 100.0, 5.0
    singles = [(truth + sig * rng.standard_normal(), sig) for _ in range(n)]
    s = (sum(v for v, _ in singles), 1.0)                  # the sum's answer: n x the mean
    r = R.stats(singles, s, n, ref=truth)
    assert r['failed'] == 0
    assert abs(r['self_bias']) < 1e-12                     # mean / (sum / n) - 1, exactly 0 when the sum is the sum
    assert abs(r['true_bias']) < 3 * sig / truth / np.sqrt(n)
    assert 0.6 < r['true_pull_sd'] < 1.4 and 0.6 < r['diff_pull_sd'] < 1.4


def test_errors_twice_too_small_double_the_pulls():
    rng = np.random.default_rng(4)
    sd = []
    for _ in range(200):
        x = 100 + 5 * rng.standard_normal(21)
        r = R.stats([(v, 2.5) for v in x], (x.sum(), 1.0), 21, ref=100.0)
        sd.append((r['true_pull_sd'], r['diff_pull_sd']))
    assert np.mean(sd, axis=0) == pytest.approx([2.0, 2.0], rel=0.05)


def test_failures_are_counted_and_too_few_answers_give_no_bias():
    r = R.stats([None] * 19 + [(1.0, 1.0), (1.0, 1.0)], (21.0, 1.0), 21)
    assert r['failed'] == 19 and 'self_bias' not in r


class _FakeBundle:
    """The two things ``condition`` and ``identify_line`` read."""

    def __init__(self, line_kev=None):
        self.spectra = {1: dict(refined_a_keV='0.25', refined_b_keV='0.005', calib_a_keV='0', calib_b_keV='0',
                                first_channel='600', n_channels='1600')}
        self.interest = {'p1_series': {'S10-x': {'spectra': [1, 1]}}}
        self.line = line_kev

    def summed(self, ids):
        e = 0.25 + 0.005 * np.arange(600, 2200)
        n = 5.0 + 1000.0 * np.exp(-0.5 * ((e - self.line) / 0.07) ** 2)
        return e, n


def test_the_condition_puts_channel_one_first():
    c = R.condition(_FakeBundle(), [1], 'Zn K')
    a, b, _ = c.calib
    assert a + b * 1 == pytest.approx(0.25 + 0.005 * 600)  # the first cropped channel's energy
    assert c.e_range[0] == pytest.approx(3.25) and c.channels == 1600


@pytest.mark.parametrize('family', ['Fe K', 'Co K', 'Ni K', 'Zn K'])
def test_the_line_is_found_from_the_data(family):
    peak = mm.main_line(family, 10.0)[0]
    assert R.identify_line(_FakeBundle(peak), ['S10-x'], window=(6.0, 9.0)) == family
