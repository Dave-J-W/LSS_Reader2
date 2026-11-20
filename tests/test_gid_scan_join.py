"""Joining scans of one Qz level across 2θ (owner, 2026-11-20: "I want more
on that"). Illustration on real data: NX scan 11 split into two scans, A =
frames 0–20 (Det_Th 14.0–16.0°) and B = frames 15–40 (15.5–18.0°; frames
15–20 in both), B's counts × s, so the factor A/B should change by 1/s.
Measured 2026-11-20: legacy 1.006 → 1.257 (ratio 1.250, exact); pinhole with
response 'fit' 0.963 → 1.130 (ratio 1.173): the column response is fitted
on all frames before the scans are joined and absorbs part of a scale
difference between scans (P42)."""
import dataclasses
import os

import numpy as np
import pytest

from lss_core import gid as gm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
pytestmark = [pytest.mark.slow, pytest.mark.skipif(not os.path.exists(SPEC), reason='NX_school sample data not present')]


@pytest.fixture(scope='module')
def scan11():
    from lss_core.experiment import Experiment
    return Experiment(SPEC).gid_frames([11])


def _split(frames, s):
    b = [dataclasses.replace(f, scan=f.scan + 1000, data=np.asarray(f.data, float) * s,
                             error=np.asarray(f.error, float) * s) for f in frames[15:]]
    return frames[:21] + b


def _factor(frames, det, pinhole, response='fit'):
    log = []
    if pinhole:
        gm.pinhole_patch(frames, gm.GIDParams(response=response), log=log)
    else:
        gm.legacy_patch(frames, gm.GIDParams(pinhole=False), det, log=log)
    j = [x for x in log if x.get('kind') == 'horizontal (2theta)']
    assert len(j) == 1
    return j[0]['factor']


def test_legacy_scan_join_recovers_a_scale_between_scans(scan11):
    frames, det = scan11
    ratio = _factor(_split(frames, 0.8), det, False) / _factor(_split(frames, 1.0), det, False)
    assert ratio == pytest.approx(1.25, rel=1e-6)


def test_pinhole_scan_join_without_response_recovers_most_of_it(scan11):
    """As coded: with response 'none' the join itself sees the scale (the
    0.8 counts change the Poisson weights a little: 1.240)."""
    frames, det = scan11
    ratio = _factor(_split(frames, 0.8), det, True, 'none') / _factor(_split(frames, 1.0), det, True, 'none')
    assert ratio == pytest.approx(1.25, rel=0.015)


@pytest.mark.xfail(strict=True, reason='P42: the column response is fitted before scans are joined '
                                       'and absorbs part of a scale between scans (1.173 for 1.25)')
def test_pinhole_scan_join_recovers_a_scale_between_scans(scan11):
    frames, det = scan11
    ratio = _factor(_split(frames, 0.8), det, True) / _factor(_split(frames, 1.0), det, True)
    assert ratio == pytest.approx(1.25, rel=0.01)


@pytest.mark.xfail(strict=True, reason='P42: two halves of one scan join at 0.963 ± 0.003 (chi2 6.9), not 1')
def test_pinhole_halves_of_one_scan_join_at_one(scan11):
    frames, det = scan11
    assert _factor(_split(frames, 1.0), det, True) == pytest.approx(1.0, abs=0.01)


def test_physical_response_scan_join_recovers_a_scale_between_scans(scan11):
    """With the physical response (owner, 2026-11-20) each scan has its own
    scale in the beam fit, so the scan join sees a scale between scans:
    measured 1.2549 for 1.25 (response 'fit': 1.173)."""
    frames, det = scan11
    ratio = (_factor(_split(frames, 0.8), det, True, 'physical') /
             _factor(_split(frames, 1.0), det, True, 'physical'))
    assert ratio == pytest.approx(1.25, rel=0.01)
