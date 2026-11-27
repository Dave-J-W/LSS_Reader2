"""F42's relative route (issue #148; the owner's answers 2026-11-27): each
reflectivity frame's reflected row against a sample-height scan's plateau
row gives where the point was really measured, δQz, read as a surface tilt
(the owner: "usually surface tilt or curvature") by default."""
import math

import numpy as np
import pytest

from lss_core import detector_qoff as dq

SPEC = 'sample_data/NX_school/2026sep/20260923'


def _spot(row, col=47, sigma=0.45, height=5000.0, bg=2.0, shape=(195, 487), seed=0):
    """A Pilatus-sized frame with a Gaussian spot centred at (``col``, ``row``), Poisson noise."""
    r, c = np.mgrid[0:shape[0], 0:shape[1]]
    lam = bg + height * np.exp(-0.5 * ((r - row) / sigma) ** 2 - 0.5 * ((c - col) / 1.5) ** 2)
    return np.random.default_rng(seed).poisson(lam).astype(float)


def test_the_row_is_found_to_a_fraction_of_a_pixel():
    for true in (52.62, 53.0, 53.37):
        img = _spot(true)
        r = dq.reflection_row(img, (img.shape[1] - 47 - 1, 53))
        assert r.ok and abs(r.row - true) < 0.02 and r.error < 0.02
    assert not dq.reflection_row(np.zeros((195, 487)), (439, 53)).ok          # nothing there


def test_nx_references_agree_and_set_the_direction():
    from lss_core.experiment import Experiment
    exp = Experiment(SPEC)
    refs = [dq.sh_reference(exp, n) for n in (5, 10, 13)]
    rows = [r.row for r in refs]
    assert max(rows) - min(rows) < 0.08 and all(len(r.frames) >= 5 for r in refs)
    assert all(r.direction == 1 and r.direct_row < r.row - 8 for r in refs)   # the direct beam lies below
    assert refs[0].alpha_deg == pytest.approx(0.1016, abs=2e-4)
    with pytest.raises(ValueError):
        dq.sh_reference(exp, 6)                                                # a reflectivity scan


def test_nx_shifts_are_small_zero_at_the_alignment_angle_and_halved_by_the_tilt():
    from lss_core.experiment import Experiment
    exp = Experiment(SPEC)
    ref = dq.sh_reference(exp, 5)
    tilt = dq.relative_shifts(exp, [6, 7, 8, 9], 5, reference=ref)
    t = tilt.table
    assert t.shape[1] == len(dq.Shifts.COLUMNS) and np.all(np.isfinite(t[:, 6])) and tilt.notes == []
    assert np.max(np.abs(t[:, 6])) < 3e-4                                     # Å⁻¹: the arm follows the reflection
    i = int(np.argmin(np.abs(t[:, 2] - 0.0187)))                              # next to the sh scan's own angle
    assert abs(t[i, 6]) < 2.5 * t[i, 7]
    edge = (t[:, 2] > 0.021) & (t[:, 2] < 0.026)                              # just about the critical edge
    assert np.all(t[edge, 6] < 0)                                             # the same sign as the edge fits' Qoff
    inc = dq.relative_shifts(exp, [6], 5, reading='incident', reference=ref).table
    six = t[t[:, 0] == 6]
    assert np.allclose(inc[:, 6], 2 * six[:, 6]) and np.allclose(inc[:, 5], six[:, 5])
    with pytest.raises(ValueError):
        dq.relative_shifts(exp, [6], 5, reading='both', reference=ref)
    assert 'tilt reading' in tilt.summary() and 'scan 5' in tilt.summary()


def test_the_conversion_is_the_geometry():
    """δQz = (4π/λ) cos α · Δβ / 2 for a tilt, Δβ = Δrow · 0.172 mm / D."""
    from lss_core.experiment import Experiment
    exp = Experiment(SPEC)
    ref = dq.sh_reference(exp, 5)
    s = dq.relative_shifts(exp, [8], 5, reference=ref).table
    wl, d = exp.scans[8].parameters['Wavelength'], float(exp.scans[8].parameters['S2D_Dist'])
    for scan, pt, qz, row, re, dbeta, dqz, dqe in s:
        a = math.asin(qz * wl / (4 * math.pi))
        assert dbeta == pytest.approx((row - ref.row) * 0.172 / d, rel=1e-9)
        assert dqz == pytest.approx(4 * math.pi / wl * math.cos(a) * dbeta / 2, rel=1e-9)
