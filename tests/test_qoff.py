"""Qc and Qoff of R/R_F (F79, lss_core.fresnel, 2026-11-24): Qc from the
subphase's electron density, the Fresnel curve the reader divides by, and
the Qoff proposed from the data (synthetic truth: an angle offset δα,
``xrr_scans.Beamline.angle_offset_deg``)."""
import math
from dataclasses import replace

import numpy as np
import pytest

from lss_core import fresnel as F, stitching
from synthetic import xrr, xrr_scans as xs


def test_qc_of_water_and_the_subphase_list():
    w = F.subphase('water')
    assert w.rho_e == pytest.approx(0.3333, abs=2e-4)                   # physics_notes: 0.3333 e/Å³
    assert w.qc == pytest.approx(0.02173, abs=1e-5)                     # the reader's preset 0.0217
    assert F.qc_from_density(F.density_from_qc(0.0221)) == pytest.approx(0.0221, rel=1e-12)
    assert F.subphase('NaCl 6 % (1.07 M)').qc == pytest.approx(0.0221, abs=1e-4)   # the owner's 1 M NaCl
    for s in F.SUBPHASES:
        assert s.source and (s.opened or 'from memory' in s.source)    # every density cited, marked if not opened
        assert 0.33 < s.rho_e < 0.36 and 0.0216 < s.qc < 0.0226
    with pytest.raises(KeyError):
        F.subphase('mercury')


def test_fresnel_is_the_readers():
    q = np.linspace(0.005, 0.5, 400)
    assert F.fresnel(q, 0.0217) == pytest.approx(stitching.fresnel(q, 0.0217), rel=1e-12)
    assert np.all(F.fresnel(q[q < 0.0217], 0.0217) == 1.0)
    assert F.rrf(q, F.fresnel(q + 3e-4, 0.0217), 0.0217, 3e-4) == pytest.approx(np.ones_like(q))


def _curve(offset_deg=0.005, seed=1, sample=None, counts=1.0, resolution=None):
    bl = xs.Beamline(**xs.REAL_MONITOR, angle_offset_deg=offset_deg)
    bl = replace(bl, flux=bl.flux * counts, max_rate=bl.max_rate * counts)
    d = xs.measure(sample or xrr.bare_water(), xs.nx_like_plan(), beamline=bl, resolution=resolution, seed=seed)
    q = np.concatenate([r[:, 0] for r in d.per_scan.values()])
    r = np.concatenate([r[:, 1] * d.scans[n].scale for n, r in d.per_scan.items()])
    s = np.concatenate([r_[:, 2] * d.scans[n].scale for n, r_ in d.per_scan.items()])
    return q, r, s


def test_the_angle_offset_of_the_synthetic_truth():
    """Qoff = (4π/λ) cos α δα, constant to 0.2 % below α = 3° (physics_notes)."""
    k = 4 * math.pi / xrr.WAVELENGTH
    assert float(xs.qoff_of(0.005, 0.02)) == pytest.approx(k * math.radians(0.005), rel=1e-4)
    q = np.array([0.02, 0.2, 0.5])
    assert np.ptp(xs.qoff_of(0.005, q)) / float(xs.qoff_of(0.005, 0.02)) < 0.002
    assert np.all(xs.true_qz(q, xs.Beamline()) == q)                  # no offset: the recorded Qz


@pytest.mark.parametrize('method', ['edge', 'smooth'])
def test_both_estimators_find_the_offset(method):
    truth = float(xs.qoff_of(0.005, 0.02))                              # 0.00088 Å⁻¹
    q, r, s = _curve()
    p = F.propose_qoff(q, r, s, qc=xrr.qc(xrr.RHO_WATER), method=method, bootstrap=30)
    assert p.ok and p.method == method
    assert p.qoff == pytest.approx(truth, abs=3e-5)                    # water's absorption: about −1e-5
    assert 0 < p.sigma < 2e-5
    assert p.note.startswith('Qoff +0.000')
    assert F.propose_qoff(q, r * 7.3, s * 7.3, qc=xrr.qc(xrr.RHO_WATER), method=method,
                          bootstrap=0).qoff == pytest.approx(p.qoff, abs=1e-6)   # the scale of R does not matter


def test_an_outlier_at_the_edge_and_qc_with_qoff():
    truth = float(xs.qoff_of(0.005, 0.02))
    qc = xrr.qc(xrr.RHO_WATER)
    q, r, s = _curve(seed=4)
    k = int(np.flatnonzero(q > qc - truth)[0])
    bad = r.copy()
    bad[k] *= 0.7                                                       # the first point above the edge, 30 % low
    p = F.propose_qoff(q, bad, s, qc=qc, bootstrap=0)                  # the edge fit (default) holds
    assert p.qoff == pytest.approx(truth, abs=1e-4)
    smooth = F.propose_qoff(q, bad, s, qc=qc, method='smooth', bootstrap=0)
    assert abs(smooth.qoff - truth) > 2e-4      # as coded: the smoothness is pulled (the point carries the edge)
    both = F.propose_qoff(q, r, s, qc=qc, fit_qc=True, bootstrap=20)
    assert both.correlation > 0.8                                       # Qc and Qoff nearly degenerate
    assert both.qc - both.qoff == pytest.approx(qc - truth, abs=1e-4)   # the edge's place is what is fixed
    assert 'correlation' in both.note


def test_a_wrong_qc_moves_qoff_one_for_one():
    """The subphase 1 M NaCl (Qc 0.0221) reduced at water's 0.0217: Qoff
    absorbs the difference (the edge stays where it is)."""
    rho = F.subphase('NaCl 6 % (1.07 M)').rho_e
    q, r, s = _curve(sample=replace(xrr.bare_water(), rho=rho))
    truth = float(xs.qoff_of(0.005, 0.02))
    p = F.propose_qoff(q, r, s, qc=0.0217, bootstrap=0)
    assert p.qoff - truth == pytest.approx(0.0217 - xrr.qc(rho), abs=5e-5)


def test_refusals():
    q = np.linspace(0.05, 0.4, 30)                                      # no edge measured
    p = F.propose_qoff(q, F.fresnel(q, 0.0217), None)
    assert not p.ok and 'edge' in p.note
    with pytest.raises(ValueError):
        F.propose_qoff(q, q, method='eye')
    with pytest.raises(ValueError):
        F.propose_qoff(q, q, method='smooth', fit_qc=True)
    with pytest.raises(ValueError):
        F.propose_qoff(q, q, loss='cauchy')
