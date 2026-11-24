"""MCA spectra with known truth (tests/synthetic/mca.py, F90): every photon
is accounted for, each part sits where its physics puts it, and the files
written open in the reader with the counts written."""
import math

import numpy as np
import pytest

from synthetic import mca


def _centroid(e, y):
    return float(np.sum(e * y) / np.sum(y))


def test_every_photon_lands_in_one_part():
    """Photopeak + tail + shelf + escape = the photons of each source, when
    the channels cover everything (invariant)."""
    det = mca.Detector(tail=0.02, tail_slope=0.2, shelf=0.003, escape=2.0)
    s = mca.spectrum({'Zn': 5e4, 'Cu': 1e4}, elastic=1e6, beam=mca.Beam(compton_core=0.2), detector=det,
                     background=0.0)
    for src, n in s.photons.items():
        got = sum(v.sum() for (k, _), v in s.parts.items() if k == src)
        assert got == pytest.approx(n, rel=2e-3), src
    for src in ('Zn Ka1', 'Rayleigh'):
        e = mca.ELEMENTS['Zn'][1][0][1] if src == 'Zn Ka1' else 10.0
        f = s.parts[(src, 'peak')].sum() / s.photons[src]
        assert f == pytest.approx(1 - 0.02 - 0.003 - det.escape_fraction(e), abs=1e-4)


def test_line_energies_intensities_and_edges():
    assert mca.line_energy('Zn') == pytest.approx(8.6311, abs=1e-4)          # (100 × 8.63886 + 51 × 8.61578) / 151
    s = mca.spectrum({'Zn': 1e4}, detector=mca.Detector(escape=0.0))
    ka, kb = s.photopeak('Zn').sum(), s.photopeak('Zn', 'Kb').sum()
    assert kb / ka == pytest.approx(17 / 151, rel=1e-3)
    assert _centroid(s.energy, s.photopeak('Zn')) == pytest.approx(mca.line_energy('Zn'), abs=1e-3)
    below = mca.spectrum({'Zn': 1e4}, beam=mca.Beam(energy=9.5))            # Zn K edge 9.659 keV: not excited
    assert not any(k.startswith('Zn') for k, _ in below.parts)
    more = mca.spectrum({'Zn': 1e4}, kb_scale=1.25, detector=mca.Detector(escape=0.0))
    assert more.photopeak('Zn', 'Kb').sum() / more.photopeak('Zn').sum() == pytest.approx(1.25 * 17 / 151, rel=1e-3)


def test_compton_energy_and_profile():
    """E_C = E0 / (1 + E0/mc² (1 − cos 2θ)); the hydrogenic profile's FWHM
    is the one asked for; the core part stops at E0 − B."""
    assert mca.compton_energy(10.0, 90.0) == pytest.approx(10.0 / (1 + 10.0 / 510.99895), rel=1e-12)   # 9.808
    assert mca.compton_energy(10.0, 180.0) < mca.compton_energy(10.0, 90.0) < mca.compton_energy(10.0, 60.0)
    d, w = mca._hydrogenic(0.3, n=4001)
    above = d[w >= w.max() / 2]
    assert above.max() - above.min() == pytest.approx(0.3, abs=2 * (d[1] - d[0]))
    det = mca.Detector(noise=0.0, fano=1e-6, escape=0.0)
    s = mca.spectrum({}, elastic=1e6, beam=mca.Beam(compton_ratio=1.0, compton_fwhm=0.2), detector=det)
    assert _centroid(s.energy, s.part(['Compton'])) == pytest.approx(mca.compton_energy(10.0, 90.0), abs=2e-3)
    core = mca.spectrum({}, elastic=1e6, beam=mca.Beam(compton_ratio=1.0, compton_core=1.0), detector=det)
    c = core.part(['Compton'])
    assert c[core.energy > 10.0 - 0.532 + 0.02].sum() < 1e-6 * c.sum()
    assert core.photons['Compton'] < 0.5e6                                  # most of the bound electrons cannot scatter


def test_escape_peaks_sit_1740_eV_below_their_parents():
    s = mca.spectrum({'Zn': 1e5}, elastic=1e6, beam=mca.Beam(compton_ratio=0.0))
    esc = s.parts[('Rayleigh', 'escape')]
    assert _centroid(s.energy, esc) == pytest.approx(10.0 - 1.740, abs=1e-3)              # 8.26 keV
    assert esc.sum() / 1e6 == pytest.approx(mca.reed_escape(10.0), rel=1e-3)
    assert 0.5e-3 < mca.reed_escape(10.0) < mca.reed_escape(8.631) < 2.5e-3                # ≈ 0.10 % and 0.15 %
    assert mca.reed_escape(1.5) == 0.0
    none = mca.spectrum({'Zn': 1e5}, elastic=1e6, detector=mca.Detector(escape=0.0))
    assert not any(k == 'escape' for _, k in none.parts)


def test_tail_and_shelf_lie_below_their_line():
    det = mca.Detector(tail=0.05, tail_slope=0.2, shelf=0.01, escape=0.0)
    s = mca.spectrum({'Fe': 1e6}, detector=det, beam=mca.Beam(energy=10.0))
    tail, shelf = s.part(['Fe Ka1'], ['tail']), s.part(['Fe'], ['shelf'])
    assert _centroid(s.energy, tail) == pytest.approx(6.40384 - 0.2, abs=0.005)             # an exponential of 0.2 keV
    e0 = mca.line_energy('Fe')
    flat = shelf[(s.energy > 1.0) & (s.energy < e0 - 0.5)]
    assert flat.std() / flat.mean() < 0.01                                                  # flat below the line
    e_mean = sum(e * i for _, e, i in mca.ELEMENTS['Fe'][1]) / sum(i for *_, i in mca.ELEMENTS['Fe'][1])
    assert flat.mean() == pytest.approx(1e6 * 0.01 * 0.01 * np.mean(1 / e_mean), rel=0.02)    # spread over 0…E


def test_calibration_error_moves_the_lines_on_the_nominal_axis():
    """The file says (a, b, q); the channels really are at (a + offset, b(1 + gain), q)."""
    base = mca.spectrum({'Zn': 1e5}, detector=mca.Detector(escape=0.0))
    off = mca.spectrum({'Zn': 1e5}, detector=mca.Detector(escape=0.0), offset=0.03)
    gain = mca.spectrum({'Zn': 1e5}, detector=mca.Detector(escape=0.0), gain=0.005)
    c0 = _centroid(base.energy, base.photopeak('Zn'))
    assert _centroid(off.energy, off.photopeak('Zn')) == pytest.approx(c0 - 0.03, abs=1e-4)
    assert _centroid(gain.energy, gain.photopeak('Zn')) == pytest.approx(c0 / 1.005, abs=1e-4)
    assert off.photopeak('Zn').sum() == pytest.approx(base.photopeak('Zn').sum(), rel=1e-9)


def test_background_and_poisson():
    s = mca.spectrum({}, background=3.0, slope=0.5)
    bg = s.parts[('background', 'flat')]
    assert bg == pytest.approx(3.0 + 0.5 * s.energy_true)
    rng = np.random.default_rng(3)
    draws = np.array([s.draw(rng) for _ in range(200)])
    assert draws.sum(axis=1).mean() == pytest.approx(s.expected.sum(), rel=3 / math.sqrt(s.expected.sum() * 200))
    assert np.all(draws == np.round(draws))


def test_written_files_open_with_their_counts(tmp_path):
    """write_dataset: the reader's window sums of the written spectra equal
    the counts written (live = real, monitor as written)."""
    from lss_core.experiment import Experiment
    rng = np.random.default_rng(1)
    spectra = [mca.spectrum({'Zn': n}, elastic=1e5, channels=1200) for n in (1e3, 3e3)]
    counts = [s.draw(rng) for s in spectra]
    path = mca.write_dataset(tmp_path / 'mca', spectra, counts, qz=[0.01, 0.02], monitor=1e5)
    ex = Experiment(path)
    rows = np.array(ex.fluorescence(sorted(ex.scans), window=(8.2, 9.1)).rows)
    assert rows[:, 1] == pytest.approx([0.01, 0.02])
    for k, c in enumerate(counts):
        sel = (spectra[k].energy >= 8.2) & (spectra[k].energy <= 9.1)
        assert rows[k, 3] == pytest.approx(c[sel].sum() / 1e5, rel=1e-6)


def test_shell_profiles_are_normalised_and_hydrogen_is_exact():
    """The 'shells' Compton model (study B, 2026-11-24): each hydrogenic
    profile integrates to 1; hydrogen's 1s has J(0) = 8/(3π)."""
    q = np.linspace(-80, 80, 320001)
    for orb, z in (('1s', 1.0), ('2s', 4.49), ('2p', 4.45), ('1s', 7.658)):
        assert np.trapezoid(mca.hydrogenic_profile(q, orb, z), q) == pytest.approx(1.0, abs=2e-3), (orb, z)
    assert mca.hydrogenic_profile(0.0, '1s', 1.0) == pytest.approx(8 / (3 * math.pi), rel=2e-3)


def test_compton_pz_is_zero_at_the_compton_energy():
    ec = mca.compton_energy(10.0, 90.0)
    assert mca.compton_pz(10.0, ec, 90.0) == pytest.approx(0.0, abs=1e-9)
    assert mca.compton_pz(10.0, ec + 0.05, 90.0) > 0 > mca.compton_pz(10.0, ec - 0.05, 90.0)
    # 0.102 keV per atomic unit of p_z near the peak at 10 keV, 90° (√(E0² + E_C²)/137)
    d = (mca.compton_pz(10.0, ec + 0.01, 90.0) - mca.compton_pz(10.0, ec - 0.01, 90.0)) / 0.02
    assert 1 / d == pytest.approx(math.sqrt(10.0 ** 2 + ec ** 2) / 137.036, rel=0.02)


def test_shell_compton_cut_off_and_scales():
    """The O 1s part stops at E0 − 0.543 keV; core_scale scales it;
    doppler_scale widens every shell; photons are kept apart by part."""
    det = mca.Detector(noise=1e-4, fano=1e-6, escape=0.0)
    s = mca.spectrum({}, 1e6, mca.Beam(compton_model='shells'), det)
    core, val = s.part(['Compton core']), s.part(['Compton valence'])
    assert core[s.energy > 10.0 - 0.543 + 0.01].sum() < 1e-6 * core.sum()
    assert 0 < s.photons['Compton core'] < 0.25 * 2 / 10 * 1e6           # most O 1s electrons cannot scatter here
    s2 = mca.spectrum({}, 1e6, mca.Beam(compton_model='shells', core_scale=2.0), det)
    assert s2.photons['Compton core'] == pytest.approx(2 * s.photons['Compton core'], rel=1e-9)
    wide = mca.spectrum({}, 1e6, mca.Beam(compton_model='shells', doppler_scale=1.25), det).part(['Compton valence'])
    e, ec = s.energy, mca.compton_energy(10.0, 90.0)
    spread = lambda y: math.sqrt(np.sum(y * (e - ec) ** 2) / np.sum(y))
    assert spread(wide) > 1.15 * spread(val)
