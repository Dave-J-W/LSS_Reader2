"""XFNTR with known truth (tests/synthetic/xfntr.py): the field at the
surface, the penetration depth, the yield's shape, the line width, and the
reader's window sum on the written MCA files."""
import math

import numpy as np
import pytest

from lss_core.experiment import Experiment
from synthetic import xfntr as xf
from synthetic import xrr

QC = xrr.qc(xrr.RHO_WATER)


def test_field_at_the_surface_is_four_times_at_qc_and_one_far_above():
    assert float(xf.transmission(QC, beta=0.0)) == pytest.approx(4.0, rel=1e-9)
    assert 3.5 < float(xf.transmission(QC)) < 4.0            # absorption rounds the peak
    assert float(xf.transmission(40 * QC)) == pytest.approx(1.0, abs=1e-3)
    q = 0.5 * QC
    assert float(xf.transmission(q, beta=0.0)) == pytest.approx(1.0, rel=1e-9)   # |2q/(q + i k)|² = 4q²/(q²+k²)


def test_penetration_depth_below_and_above_qc():
    q = np.array([0.1, 0.5, 0.9]) * QC
    assert xf.penetration_depth(q) == pytest.approx(1 / np.sqrt(QC ** 2 - q ** 2), rel=1e-3)
    assert float(xf.penetration_depth(0.01 * QC)) == pytest.approx(1 / QC, rel=1e-3)      # ~46 Å
    # far above Qc: the absorption length along the surface normal, λ sin α / (4π β)
    q = 20 * QC
    sin_a = q * xrr.WAVELENGTH / (4 * math.pi)
    assert float(xf.penetration_depth(q)) == pytest.approx(xrr.WAVELENGTH * sin_a / (4 * math.pi * xrr.BETA_WATER_10KEV),
                                                           rel=0.01)


def test_surface_yield_peaks_at_qc_and_bulk_yield_rises_above_it():
    q = np.linspace(0.3 * QC, 3 * QC, 541)
    surf = xf.yield_curve(q, xf.Sample(1.0, 0.0))
    assert q[np.argmax(surf)] == pytest.approx(QC, rel=0.02)
    bulk = xf.yield_curve(q, xf.Sample(0.0, 1.0))
    assert bulk[q > 1.2 * QC].min() > 50 * bulk[q < 0.8 * QC].max()
    # escape absorption caps the bulk depth
    capped = xf.yield_curve(q, xf.Sample(0.0, 1.0, escape=1e-4))
    assert np.all(capped <= bulk) and capped[-1] < 1.1e4 * float(xf.transmission(q[-1]))
    # a detector that sees less than the footprint: v = view·sin α / beam
    v = xf.yield_curve(q, xf.Sample(1.0, 0.0), view_mm=0.5) / surf
    assert v[0] == pytest.approx(0.5 * q[0] * xrr.WAVELENGTH / (4 * math.pi) / 0.02, rel=1e-9)


def test_line_width_grows_with_energy():
    assert xf.fwhm_kev(0.0) == pytest.approx(xf.NOISE_FWHM_KEV)
    assert xf.fwhm_kev(6.4) == pytest.approx(math.sqrt(0.12 ** 2 + 8 * math.log(2) * 0.00365 * 0.115 * 6.4))
    assert xf.fwhm_kev(15.0) > xf.fwhm_kev(6.4) > xf.fwhm_kev(2.0)
    s, line = xf.spectrum(1000.0, background=0.0)
    assert line.sum() == pytest.approx(1000.0, rel=1e-6) and s.sum() == pytest.approx(1000.0, rel=1e-6)


@pytest.mark.parametrize('seed', [None, 4])
def test_reader_window_sum_is_the_known_counts(tmp_path, seed):
    qz = np.round(np.linspace(0.01, 0.04, 9), 4)
    counts, truth = xf.measure(qz, xf.Sample(1.0, 2e-4), seed=seed)
    spec = xf.write_dataset(tmp_path / 'xf', counts, truth)
    e = Experiment(spec)
    res = e.fluorescence(sorted(e.scans), window=(5.6, 7.6))
    rows = np.array(res.rows)
    energy = xf.CALIB[1] * np.arange(1, xf.CHANNELS + 1)
    w = (energy >= 5.6) & (energy <= 7.6)
    want = np.array([c[w].sum() for c in counts]) / truth.monitor * truth.real / truth.live
    assert rows[:, 1] == pytest.approx(qz)
    assert rows[:, 3] == pytest.approx(want, rel=1e-6)
    # the window holds the line and the flat background, nothing else
    expected = np.array([s[w].sum() for s in truth.spectra])
    assert expected == pytest.approx(truth.line_counts * 0.9999 + 2.0 * w.sum(), rel=2e-3)
