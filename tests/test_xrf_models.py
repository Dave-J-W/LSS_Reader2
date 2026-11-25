"""The models study (docs/studies/xrf_models/README.md, 2026-11-25): the
line-shape ladder recovers a known shape, the model twins are what the
blank shootout reads, and the line shapes injected into the blanks are the
ones the study measured."""
import csv
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))

import xrf_blanks as xb               # noqa: E402
import xrf_lineshape as L             # noqa: E402
import xrf_models as M                # noqa: E402
from synthetic import mca, mca_more as mm   # noqa: E402

CAL = (0.0, 0.01, 0.0)                # readout B's file calibration: 10 eV per channel from 0 keV


def _line(detector, photons=5e5, seed=1):
    s = mm.spectrum({'Fe K': photons}, detector=detector, background=20.0, calib=CAL, channels=1000)
    return s.energy, np.random.default_rng(seed).poisson(s.expected).astype(float)


def _fit(e, n, shape):
    lf = L.LineFit(e, n, 'Fe K', 'B', shape)
    P, p, dev, dof = lf.fit()
    return P, dev / dof, lf


def test_the_ladder_recovers_a_known_short_tail():
    noise, fano = L.RESOLUTION['B']
    det = mca.Detector(noise=noise, fano=fano, tail=0.45, tail_slope=0.06, escape=L.ESCAPE['B'])
    e, n = _line(det)
    Pg, dg, _ = _fit(e, n, 'gauss')
    Pt, dt, lf = _fit(e, n, 'tail')
    assert dt < 1.3 < 5 < dg                                # the Gaussian misfits a tailed line, the one-tail shape does not
    assert Pt['tail'] == pytest.approx(0.45, abs=0.05) and Pt['tail_slope'] == pytest.approx(0.06, abs=0.015)
    assert Pt['noise'] == pytest.approx(noise, abs=0.01)
    assert mca.Detector(noise=Pg['noise'], fano=fano).fwhm(6.4) > 1.05 * det.fwhm(6.4)    # and reads it wider


def test_a_gaussian_line_needs_no_tail_and_reads_the_resolution():
    noise, fano = L.RESOLUTION['B']
    e, n = _line(mca.Detector(noise=noise, fano=fano, escape=L.ESCAPE['B']), seed=2)
    Pg, dg, _ = _fit(e, n, 'gauss')
    Pt, dt, _ = _fit(e, n, 'tail')
    assert dg < 1.3 and Pt['tail'] < 0.03
    assert Pg['noise'] == pytest.approx(noise, abs=0.005)


def test_the_family_is_found_and_the_probe_key():
    noise, fano = L.RESOLUTION['B']
    e, n = _line(mca.Detector(noise=noise, fano=fano), seed=3)
    assert L.identify(e, n, 'B') == 'Fe K'
    assert L.probe_key('B-K1-e3') == L.probe_key('B-K1-sum7raw') == 'B-K1' and L.probe_key('A-L2') == 'A-L2'


def _table(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


LINE_SHAPES = os.path.join('docs', 'studies', 'xrf_models', 'lines', 'line_shapes.csv')


@pytest.mark.skipif(not os.path.exists(LINE_SHAPES), reason='the line-shape table is not committed')
def test_the_injected_real_shapes_are_the_measured_medians():
    """xrf_blanks.LINE_SHAPES['line'] are the medians of line_shapes.csv
    (readout A: the 'tail_shelf' fits of its six probes; B: the 'tail' fits
    of its fourteen single elements)."""
    R = _table(LINE_SHAPES)
    A = [r for r in R if r['readout'] == 'A' and r['shape'] == 'tail_shelf']
    B = [r for r in R if r['readout'] == 'B' and r['shape'] == 'tail' and '-e' in r['probe']]
    assert len(A) == 6 and len(B) == 14
    for rows, ro in ((A, 'A'), (B, 'B')):
        want = xb.LINE_SHAPES['line'][ro]
        for k, col in (('tail', 'tail'), ('tail_slope', 'tail_slope_keV'), ('shelf', 'shelf')):
            assert want[k] == pytest.approx(np.median([float(r[col]) for r in rows]), abs=0.0015), (ro, k)


def test_the_line_shape_option_changes_only_the_tail_and_shelf():
    b = xb.load_blank(os.path.join(xb.BLANKS, 'E9.2-a.csv'))
    base = xb.BlankCond(b, 'Ni K', 1000, 1.0)
    g = xb.BlankCond(b, 'Ni K', 1000, 1.0, 'gaussian')
    ln = xb.BlankCond(b, 'Ni K', 1000, 1.0, 'line')
    assert base.cond.detector.tail > 0 and g.cond.detector.tail == 0 and g.cond.detector.shelf == 0
    assert ln.cond.detector.tail == xb.LINE_SHAPES['line']['B']['tail']
    for c in (g, ln):
        d0, d = base.cond.detector, c.cond.detector
        assert (d.noise, d.fano, d.escape) == (d0.noise, d0.fano, d0.escape)   # what the methods are told is unchanged
        assert c.p == base.p


def test_a_twin_is_a_blank_file_with_the_model_as_its_mean(tmp_path):
    b = xb.load_blank(os.path.join(xb.BLANKS, 'E6.1-a.csv'))
    mu = np.full(len(b['energy']), 400.0)
    p = tmp_path / 'E6.1-a.csv'
    M.write_twin(str(p), b, mu, 'full', np.random.default_rng(5))
    t = xb.load_blank(str(p))
    assert np.allclose(t['energy'], b['energy'], atol=1e-4) and t['beam'] == b['beam'] and t['readout'] == b['readout']
    assert t['counts'].mean() == pytest.approx(400.0, rel=0.01) and t['counts'].var() == pytest.approx(400.0, rel=0.2)
    assert 'twin' in open(p, encoding='utf-8').read().splitlines()[1]


def test_accurate_is_the_shootouts_rule():
    assert M.accurate(0.019, 0.001) and not M.accurate(0.03, 0.01) and M.accurate(0.03, 0.02)


def _run(d, bias, false):
    os.makedirs(d)
    with open(os.path.join(d, 'scores.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['condition', 'method', 'bias', 'bias_se', 'blank', 'target', 'background', 'ratio', 'pull_sd'])
        w.writerow(['E6.1-a|Ti K|1000|1', 'p1', bias, 0.01, 'E6.1-a', 'Ti K', 1000, 1, 1.0])
    with open(os.path.join(d, 'zero.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['condition', 'method', 'blank', 'target', 'false_per100', 'false_se'])
        w.writerow(['E6.1-a|Ti K|1000|0', 'p1', 'E6.1-a', 'Ti K', false, 0.5])


def test_the_floor_compares_a_second_draw_with_the_first_not_with_the_real(tmp_path):
    real, out = tmp_path / 'real', tmp_path / 'out'
    _run(str(real), 0.10, 9.0)
    _run(str(out / 'run_full'), 0.04, 3.0)
    _run(str(out / 'run_full_redraw'), 0.05, 4.0)
    M.main(['compare', '--out', str(out), '--real', str(real)])
    rows = {r['model']: r for r in _table(str(out / 'compare.csv'))}
    assert float(rows['full']['diff']) == pytest.approx(0.04 - 0.10)
    assert float(rows['full_redraw']['diff']) == pytest.approx(0.05 - 0.04)       # against the first twin
    z = {r['model']: r for r in _table(str(out / 'compare_zero.csv'))}
    assert float(z['full_redraw']['false_real']) == 3.0 and float(z['full_redraw']['false_twin']) == 4.0
