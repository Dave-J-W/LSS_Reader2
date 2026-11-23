"""The incidence angle of each frame (P47, the fragility audit, 2026-11-23).

The scan header's In_Rot is written before the scan moves. Every frame took
it as its true incidence, so in a specular scan that moves L the exit angle
β = arcsin(2 sin α − sin α_true) of the reflected beam was not α. On NX
school it was 0.1073° for α 0.0989° (scan 6, first frame) and up to 4.187°
for 2.545° (scan 9, last frame). Now a specular scan (H = K = 0, L
moving) takes α = arcsin(L λ / 4π) per frame; scans at fixed incidence
keep the header's value. Qz axes hardly move: Qz = k (sin α_true + sin β)
cancels α_true at the reflected row."""
import os

import numpy as np
import pytest

import sweep
from lss_core import cuts
from lss_core.experiment import Experiment

NX = os.path.join('sample_data', 'NX_school', '2026sep', '20260923')
WL = 1.23984


def test_a_specular_scan_takes_its_incidence_from_l():
    L = np.array([0.02, 0.03, 0.04])
    spec = {'H': np.zeros(3), 'K': np.full(3, 4e-7), 'L': L}
    assert cuts.true_incidence(spec, 2, WL, 0.05) == pytest.approx(np.arcsin(0.04 * WL / 4 / np.pi), rel=1e-12)
    gid = {'H': np.linspace(1.3, 1.6, 3), 'K': np.full(3, 0.2), 'L': np.full(3, 0.016)}
    assert cuts.true_incidence(gid, 1, WL, 0.0905) == pytest.approx(np.radians(0.0905))   # fixed incidence: the header
    flat = {'H': np.zeros(3), 'K': np.zeros(3), 'L': np.full(3, 0.018)}
    assert cuts.true_incidence(flat, 0, WL, 0.1) == pytest.approx(np.radians(0.1))         # L constant: the header
    logged = dict(spec, In_Rot=np.array([0.11, 0.17, 0.23]))
    assert cuts.true_incidence(logged, 1, WL, 0.05) == pytest.approx(np.radians(0.17))     # an In_Rot column wins
    assert cuts.true_incidence({'H': None, 'K': None, 'L': None}, 0, WL, 0.1) == pytest.approx(np.radians(0.1))


@pytest.mark.parametrize('scan,which', [(6, 0), (6, -1), (8, -1), (9, -1)])
def test_the_reflected_beam_sits_at_beta_equal_alpha(scan, which):
    """Invariant I33: on the Angles axis of a 'Pix V' cut through the
    reflected beam's columns, the peak of a specular frame is at β = α."""
    e = Experiment(NX)
    f = e.frames([scan])[which]
    p = e.scans[scan].parameters
    xc = 194 - p['DBPos'][1]
    c = e.cut([scan], 'Pix V', (xc - 7, xc + 7), axes='Angles', points={scan: [f.index]}).cuts[0]
    alpha = np.degrees(np.arcsin(f.qz * p['Wavelength'] / 4 / np.pi))
    assert c[np.argmax(c[:, 1]), 0] == pytest.approx(alpha, abs=2e-4)


@pytest.mark.gui
def test_the_window_gives_specular_frames_their_own_incidence(loaded, qapp, recorder):
    w = loaded
    sweep._select_scans(w, qapp, [0])
    sweep._select_images(w, qapp)
    assert recorder.exceptions == []
    frames = list(w.selectedPilFramesNums)
    assert len(frames) > 2
    assert np.allclose([w.pilTrueAlpha[i] for i in frames], [w.pilAlpha[i] for i in frames], rtol=1e-12)
    assert not np.allclose([w.pilTrueAlpha[i] for i in frames], np.radians(0.1))   # the synthetic header's In_Rot
