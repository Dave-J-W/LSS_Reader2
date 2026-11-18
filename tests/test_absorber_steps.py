"""Absorber steps measured on NX school scans 6-9 (owner's question,
2026-11-18: binary foil set; tolerance flat 1-2 µm rather than 2 %?).

As measured, not invariants: the ratios at Q_z measured in both scans of
each join, against the nominal 50 µm Al per unit. A change here means the
reduction changed (rule 1 of AGENTS.md).
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))
from absorber_steps import steps  # noqa: E402

pytestmark = pytest.mark.slow
SPEC = os.path.join(os.path.dirname(HERE), 'sample_data', 'NX_school', '2026sep', '20260923')


def test_measured_steps_are_larger_than_nominal():
    s = steps(SPEC, [6, 7, 8, 9])
    assert [x['n'] for x in s] == [(41, 31), (31, 24), (24, 18)]
    assert all(len(x['qz']) == 3 for x in s)
    ratio = [x['measured'] / x['nominal'] for x in s]
    assert ratio == pytest.approx([0.788, 0.762, 0.870], abs=1e-3)
    # each is many counting errors from 1: not a 1-2 µm effect
    assert all((1 - x['measured'] / x['nominal']) / (x['error'] / x['nominal']) > 20 for x in s)
    assert [round(x['extra_um'], 1) for x in s] == [33.6, 38.3, 19.6]
