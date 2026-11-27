"""Qoff and the Qz resolution fitted together at the edge
(``lss_core.fresnel.fit_edge_resolution``, hand-off 09), its pieces, the
study's known truth and the survey tool."""
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tests', 'tools'))

from lss_core import fresnel as F           # noqa: E402
from synthetic import xrr                   # noqa: E402
import qoff_resolution_study as S           # noqa: E402

NX = os.path.join(ROOT, S.NX)


def test_the_absorbing_fresnel_is_parratts():
    q = np.linspace(0.005, 0.2, 400)
    qc = xrr.qc(xrr.RHO_WATER)
    got = F.fresnel_absorbing(q, qc, xrr.BETA_WATER_10KEV, 10.0)
    assert np.allclose(got, xrr.fresnel(q, xrr.RHO_WATER, xrr.BETA_WATER_10KEV, xrr.WAVELENGTH), rtol=1e-12, atol=0)
    rough = F.fresnel_absorbing(q, qc, xrr.BETA_WATER_10KEV, 10.0, roughness=3.0)
    assert np.allclose(rough, xrr.bare_water().reflectivity(q), rtol=1e-12, atol=0)       # Névot–Croce, 3 Å
    assert np.allclose(F.fresnel_absorbing(q, qc, 0.0), F.fresnel(q, qc), rtol=1e-12, atol=1e-15)


def test_the_smearing_is_accurate_at_the_edge():
    """The trapezoid rule against the generator's 'fine' Simpson rule (both
    good to 1e-7 against a 40001-point integral, measured 2026-11-27); the
    generator's default 31-node Gauss-Hermite rule is ~1 % off at the edge."""
    q = np.linspace(0.012, 0.03, 120)
    qc, b = xrr.qc(xrr.RHO_WATER), xrr.BETA_WATER_10KEV
    truth = lambda x: xrr.fresnel(x, xrr.RHO_WATER, b, xrr.WAVELENGTH)
    for sg in (1e-4, 3.8e-4, 8e-4):
        got = F.fresnel_smeared(q, qc, sg, b, 10.0)
        assert np.allclose(got, xrr.smear(q, truth, (F.fwhm_of(sg), 0.0, 'fine')), rtol=2e-5, atol=0), sg
    gh = xrr.smear(q, truth, (F.fwhm_of(3.8e-4), 0.0))
    assert np.max(np.abs(gh / F.fresnel_smeared(q, qc, 3.8e-4, b, 10.0) - 1)) > 5e-3
    assert np.array_equal(F.fresnel_smeared(q, qc, 0.0, b), F.fresnel_absorbing(q, qc, b))


def test_beta_of_the_subphases():
    """β = μλ/4π from xraylib's μ/ρ (total, with coherent): water at 10 keV
    5.24e-9 (xraylib's own Refractive_Index_Im: 5.242e-9; the synthetic
    generator's NIST 5.24e-9); salt absorbs more."""
    w = F.subphase_beta(F.subphase('water'), 10.0)
    assert w == pytest.approx(5.242e-9, rel=1e-3)
    assert w == pytest.approx(xrr.BETA_WATER_10KEV, rel=2e-3)
    assert F.mu_rho('H2O', 10.0) == 5.329                    # a table node exactly
    assert F.subphase_beta(F.subphase('NaCl 6 % (1.07 M)'), 10.0) > 1.4 * w
    assert F.subphase_beta(F.subphase('water'), 20.0) < w / 10
    with pytest.raises(ValueError):
        F.mu_rho('H2O', 5.0)


def test_a_noiseless_edge_is_read_exactly():
    """The expected counts (no noise) of bare water: with its 3 Å roughness
    in the model, Qoff and σ_Q come back exactly, at the owner's sampling and
    at NX's. Without it (the hand-off's model, the default) the smooth factor
    misses the roughness's small kink at Qc: σ_Q is within 1 % at the
    beamline's 3.8e-4 and above, but off by −8 % (owner's sampling) and
    +18 % (NX's) at 1e-4 (as measured 2026-11-27)."""
    for sampling in (S.OWNER, S.NX_SAMPLING):
        for sig in (1e-4, 3.8e-4, 6e-4):
            q, r, s = S.edge_scan(qoff=-2e-4, sigma_q=sig, expected=True, **sampling)
            f = F.fit_edge_resolution(q, r, s, qc=S.QC, beta=S.BETA, bootstrap=0, roughness=3.0)
            assert f.ok and not f.flags, (sampling, sig, f.flags)
            assert f.qoff == pytest.approx(S.true_qoff(-2e-4), abs=1e-8), (sampling, sig)
            assert f.sigma_q == pytest.approx(sig, rel=1e-4), (sampling, sig)
            g = F.fit_edge_resolution(q, r, s, qc=S.QC, beta=S.BETA, bootstrap=0)
            assert g.qoff == pytest.approx(S.true_qoff(-2e-4), abs=5e-6), (sampling, sig)
            if sig >= 3.8e-4:
                assert g.sigma_q == pytest.approx(sig, rel=0.01), (sampling, sig)
    q, r, s = S.edge_scan(qoff=-2e-4, sigma_q=1e-4, expected=True, **S.OWNER)
    assert F.fit_edge_resolution(q, r, s, qc=S.QC, beta=S.BETA, bootstrap=0).sigma_q / 1e-4 - 1 == \
        pytest.approx(-0.078, abs=0.01)


def test_noisy_edges_and_their_errors():
    """A few noisy edges at the beamline's resolution: within 3 σ each; the
    units of the report."""
    t = S.true_qoff(-2e-4)
    for seed in range(4):
        q, r, s = S.edge_scan(seed=[5, seed])
        f = F.fit_edge_resolution(q, r, s, qc=S.QC, beta=S.BETA, bootstrap=30, seed=seed)
        assert abs(f.qoff - t) < 3 * f.qoff_err and abs(f.sigma_q - 3.8e-4) < 3 * f.sigma_q_err
        assert f.qoff_err >= f.qoff_err_counting > 0 and -1 <= f.corr <= 1
    assert f.fwhm == pytest.approx(2.3548 * f.sigma_q, rel=1e-4)
    assert f.sigma_alpha_urad == pytest.approx(f.sigma_q / (4 * math.pi / F.wavelength(10.0)) * 1e6)
    assert np.allclose(f.model(f.points), np.exp(np.log(f.model(f.points))))
    assert 'σ_Q' in f.note and 'χ²/dof' in f.note


def test_refusals_and_flags():
    q, r, s = S.edge_scan(expected=True, start=0.023)          # no point below the edge
    f = F.fit_edge_resolution(q, r, s, qc=S.QC, beta=S.BETA, bootstrap=0)
    assert not f.ok and 'not fitted' in f.note
    q, r, s = S.edge_scan(expected=True, start=0.0205, step=0.00125)   # one point below the edge
    f = F.fit_edge_resolution(q, r, s, qc=S.QC, beta=S.BETA, bootstrap=0)
    assert f.ok and 'few points below the edge' in f.flags


def test_the_known_truth_runs():
    rows, reps = S.known_truth(replicates=2, bootstrap=5, workers=1)
    assert len(reps) == 2 and {(r['estimator'], r['quantity']) for r in rows} == {
        ('joint', 'qoff'), ('joint', 'sigma_q'), ('joint_r3', 'qoff'), ('joint_r3', 'sigma_q'), ('sharp', 'qoff')}
    j = [r for r in rows if r['estimator'] == 'joint' and r['quantity'] == 'qoff'][0]
    assert abs(j['bias']) < 2e-5 and j['n'] == 2


def test_the_survey_refuses_private_output_inside_the_repository(tmp_path):
    import qoff_resolution_survey as V
    with pytest.raises(SystemExit):
        V.main(['--spec', str(tmp_path / 'some_private_file'), '--out', os.path.join(ROOT, 'docs', 'x')])
    assert not os.path.exists(os.path.join(ROOT, 'docs', 'x'))
    assert V.crosses([0.015, 0.02, 0.03], 0.0217) and not V.crosses([0.0195, 0.03], 0.0217)
    assert V.crosses([0.0175, 0.04], 0.0217) and not V.crosses([0.0175, 0.04], 0.0217, below=0.8)   # NX scan 6


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
def test_the_survey_on_nx(tmp_path):
    """As measured 2026-11-27, at water's own Qc (0.021728, the subphase's;
    the reader's preset 0.0217 moves Qoff by the difference, one for one):
    scans 3 (a coarse survey, nothing in the fit's range: not fitted) and 6
    (the edge). On scan 6 σ_Q goes to its bound of 0, as DATA_NEEDS row 13
    found; Qoff −2.44e-4 with χ²/dof 100 (the study's section 4)."""
    import qoff_resolution_survey as V
    rows = V.main(['--spec', NX, '--out', str(tmp_path), '--bootstrap', '20'])
    assert [r['scan'] for r in rows] == [3, 6]
    assert rows[0]['qoff'] is None and rows[0]['flags'].startswith('not fitted')
    r = rows[1]
    assert r['error'] == '' and r['energy_kev'] == pytest.approx(10.0, abs=0.05)
    assert r['qc'] == pytest.approx(0.021728, abs=2e-6) and r['n_below'] == 4 and r['n_above'] == 7
    assert 'sigma_q at its bound' in r['flags'] and r['chi2_dof'] > 50
    assert r['qoff'] == pytest.approx(-2.44e-4, abs=0.1e-4)
    assert r['qoff_sharp'] == pytest.approx(-2.36e-4, abs=0.1e-4)
    assert r['qoff_err'] > 5 * r['qoff_err_counting']          # scaled by √(χ²/dof)
    assert (tmp_path / 'edges.csv').exists() and (tmp_path / 'summary.md').exists()
