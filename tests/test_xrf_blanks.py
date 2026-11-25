"""The XRF shootout on real blanks (tests/tools/xrf_blanks.py, 2026-11-25):
the committed real blanks with synthetic lines of known photons added. Only
the reader's methods run here (no PyMca, scikit-beam or Larch needed)."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))

import xrf_blanks as xb          # noqa: E402
import xrf_shootout as xs        # noqa: E402
from synthetic import mca_more as mm   # noqa: E402


def _blank(bid):
    return xb.load_blank(os.path.join(xb.BLANKS, bid + '.csv'))


@pytest.mark.parametrize('bid', xb.CLEAN)
def test_every_clean_blank_loads_with_a_linear_calibration(bid):
    b = _blank(bid)
    assert b['beam'] in xb.TARGETS
    assert b['calib_residual'] < 1e-3                      # keV: the file's energy column is linear in the channel
    assert abs(b['calib'][1] - float(b['header']['gain_keV_per_channel'])) < 2e-5
    assert np.all(b['counts'] >= 0) and np.all(b['counts'] == np.round(b['counts']))


def test_thinning_and_injection_keep_their_counts():
    b = _blank('E10-k')
    bc = xb.BlankCond(b, 'Zn K', 1000, 1.0)
    assert 0 < bc.p < 0.25                                  # replicates share under a quarter of their counts
    spec = bc.spectra()
    assert mm.family_photons(spec, 'Zn K') == pytest.approx(1000.0)
    rng = np.random.default_rng(1)
    lo, hi = bc.cond.box_range()
    box = (b['energy'] >= lo) & (b['energy'] <= hi)
    bg = [rng.binomial(b['counts'].astype(np.int64), bc.p)[box].sum() for _ in range(200)]
    assert np.mean(bg) == pytest.approx(1000.0, rel=0.01)  # the thinned blank holds the asked-for counts in the box
    drawn = np.mean([bc.draw(spec, rng).sum() for _ in range(200)])
    assert drawn == pytest.approx(b['counts'].sum() * bc.p + spec.expected.sum(), rel=0.005)


def test_the_line_is_drawn_with_the_blanks_measured_detector():
    det, beam, notes = xb.measured('E10-k')
    assert beam.energy == 10.0 and 85 < beam.angle < 95
    assert det.fano == pytest.approx(0.139, abs=0.001)      # its own Ar Ka and elastic widths
    assert det.fwhm(10.0) == pytest.approx(notes['elastic_fwhm'], rel=1e-6)
    _, _, notes_b = xb.measured('E6.1-a')
    assert notes_b['fano_from'].startswith('readout B')


def _false_line(method, bid='E9.2-a', target='Ni K', reps=3):
    """Calibrated photons a method reports on the bare thinned blank, per
    100 background counts in the box."""
    bc = xb.BlankCond(_blank(bid), target, 3000, 0.0)
    k = xs.calibrate('t', bc.cond, [method])[1][method][0]
    rows = xb.run_blank(('t', bc, [method], range(reps), 0))
    v = [r[4] for r in rows if r[4] is not None and np.isfinite(r[4])]
    return np.mean(v) / k / 3000 * 100, len(v) / len(rows)


def test_the_escape_peak_of_real_scatter_reads_as_a_line_unless_stripped():
    """Under a 9.2 keV beam the Si escape of the scatter (7.46 keV) sits on
    Ni Ka (7.47 keV). A box fit without the strip finds about 30 photons per
    100 background counts on a blank with no Ni at all (measured
    2026-11-25: 26-35 on the four 9.2 keV blanks); with the strip and the
    fixed width, 3-4."""
    plain, ok = _false_line('p1')
    assert ok == 1.0 and 20 < plain < 45
    stripped, _ = _false_line('p1p2p3')
    assert abs(stripped) < 8
