"""Reduced reflectivity rendered as SPEC + Pilatus frames
(tests/synthetic/xrr_images.py), reduced again by the reader: the box sums
and net values are the reduced rows' exactly, and the window's Ref Patch
gives the known curve."""
import numpy as np
import pytest

from lss_core.experiment import Experiment
from synthetic import xrr
from synthetic import xrr_images as xi
from synthetic import xrr_scans as xs


def _small_plan():
    # three scans, 26 frames, crossing the low-Qz slit range and the critical edge
    return xs.chain_plan([(0.015, 0.045, 0.0025), (0.04, 0.12, 0.005), (0.10, 0.30, 0.01)], overlap=3)


@pytest.mark.parametrize('expected', [False, True])
def test_reader_reduces_the_frames_to_the_reduced_rows(tmp_path, expected):
    d = xs.measure(xrr.dppc(), _small_plan(), seed=4, expected=expected)
    spec = xi.render(d, tmp_path, 'xrr')
    res = Experiment(spec).reflectivity(sorted(d.scans))
    assert res.beam_offsets == []
    tol = 1e-12 if not expected else 2e-6          # float32 frames for expected counts
    for k, mine in d.per_scan.items():
        got = res.per_scan[k]
        assert got.shape == mine.shape
        assert got[:, 0] == pytest.approx(mine[:, 0], rel=1e-12)
        for col in (1, 3, 5, 6):                      # net, S, B1, B2 per Monc
            assert got[:, col] == pytest.approx(mine[:, col], rel=tol, abs=1e-300)
        # the legacy error adds the per-pixel monitor term I²/M³ (P2): never smaller
        assert np.all(got[:, 2] >= mine[:, 2] * (1 - 1e-9))
    assert res.order == d.order


def test_frames_put_the_beam_where_the_header_says(tmp_path):
    d = xs.measure(xrr.bare_water(), _small_plan(), seed=1)
    spec = xi.render(d, tmp_path, 'xrr')
    e = Experiment(spec)
    f = e.frames([1])[0]
    assert f.beam_xy == (xi.synth.DB_X, xi.synth.DB_Y)
    assert f.absorber == d.scans[1].absorber and f.monitor == d.scans[1].monc[0]
    assert e.scans[1].parameters['Wavelength'] == pytest.approx(d.beamline.wavelength, rel=1e-6)
    from lss_core.images import read_pilatus
    img = read_pilatus(f.path, cache=False)
    c, r = xi.beam_pixel()
    assert np.unravel_index(np.argmax(img), img.shape) == (r, c)
    assert img.sum() > d.scans[1].counts['peak'][0] * 0.99


@pytest.mark.gui
def test_ref_patch_in_the_window_gives_the_known_curve(window, qapp, recorder, tmp_path):
    """The whole GUI path: select the scans and their frames, Ref Patch,
    Next through the joins, Export; _ref.txt is the true curve (normalised
    to its highest point below Qc, as the reader does) within the errors."""
    d = xs.measure(xrr.film(100.0), _small_plan(), seed=9)
    spec = xi.render(d, tmp_path / 'data', 'xrr')
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    qapp.processEvents()
    from test_ref_export_golden import reduce_and_save
    ref, _ = reduce_and_save(window, qapp, recorder, str(tmp_path / 'out'), [0, 1, 2], rrf=False)
    got = np.loadtxt(ref)
    truth = d.truth(got[:, 0])
    below = got[:, 0] < 0.0217
    truth = truth / truth[below].max()
    # one common scale (the normalisation point and the join factors carry
    # correlated errors, P4), then every point within its error of the truth
    w = (truth / got[:, 2]) ** 2
    c = np.sum(w * got[:, 1] / truth) / np.sum(w)
    assert c == pytest.approx(1.0, abs=0.03)
    pull = (got[:, 1] - c * truth) / got[:, 2]
    assert np.abs(pull).max() < 4 and np.mean(pull ** 2) < 3
    assert recorder.exceptions == []
