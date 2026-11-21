"""Joining scans of one Qz level across 2θ (owner, 2026-11-20: "I want more
on that"). Illustration on real data: NX scan 11 split into two scans, A =
frames 0–20 (Det_Th 14.0–16.0°) and B = frames 15–40 (15.5–18.0°; frames
15–20 in both), B's counts × s, so the factor A/B should change by 1/s.
Measured 2026-11-20: legacy 1.006 → 1.257 (ratio 1.250, exact); pinhole with
response 'fit' 0.963 → 1.130 (ratio 1.173): the column response was fitted
on all frames before the scans were joined and absorbed part of a scale
difference between scans (P42). Fixed the same day: each scan's scale is
now fitted together with the response (1.2565)."""
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


@pytest.mark.parametrize('response', ['fit', 'beam', 'physical+fit'])
def test_pinhole_scan_join_recovers_a_scale_between_scans(scan11, response):
    """P42 fixed (2026-11-20): every response fits each scan's scale together
    with the response, so the scale is not absorbed. Measured: fit 1.2565,
    beam 1.2567, physical+fit 1.2530 for 1.25 (before: 1.173)."""
    frames, det = scan11
    ratio = _factor(_split(frames, 0.8), det, True, response) / _factor(_split(frames, 1.0), det, True, response)
    assert ratio == pytest.approx(1.25, rel=0.01)


def test_halves_of_one_scan_differ_under_every_column_model(scan11):
    """As measured (2026-11-20): the two halves of NX scan 11 (Det_Th 14.0–
    16.0° and 15.5–18.0°, measured one after the other) join at 0.95–0.96
    under every column model ('fit' 0.951, 'beam' 0.952, 'physical+fit'
    0.962), not at 1: a change along the scan (the sample height drifts by
    microns in half an hour, owner 2026-11-19), not an artefact of one model.
    A characterisation: it changes only with the method."""
    frames, det = scan11
    f = {r: _factor(_split(frames, 1.0), det, True, r) for r in ('fit', 'beam', 'physical+fit')}
    assert f['fit'] == pytest.approx(0.951, abs=0.005)
    assert max(f.values()) - min(f.values()) < 0.02 and max(f.values()) < 0.975


def test_physical_response_scan_join_recovers_a_scale_between_scans(scan11):
    """With the physical response (owner, 2026-11-20) each scan has its own
    scale in the beam fit, so the scan join sees a scale between scans:
    measured 1.2549 for 1.25 (response 'fit': 1.173)."""
    frames, det = scan11
    ratio = (_factor(_split(frames, 0.8), det, True, 'physical') /
             _factor(_split(frames, 1.0), det, True, 'physical'))
    assert ratio == pytest.approx(1.25, rel=0.01)
