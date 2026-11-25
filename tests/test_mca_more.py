"""The extended MCA generator (``tests/synthetic/mca_more.py``): tabulated
lines and water's tabulated Compton profiles (XRF shootout, 2026-11-25)."""
import math

import numpy as np
import pytest

from synthetic import mca, mca_more as mm


def test_every_tabulated_family_sums_to_one():
    for key, entry in mm.TABLES['lines'].items():
        for beam, ls in entry['beams'].items():
            assert sum(i for _, _, i in ls) == pytest.approx(1.0, abs=1e-5), (key, beam)
            assert all(i > 0 and e > 0 for _, e, i in ls)


def test_lines_follow_the_edge():
    assert mm.family_lines('Zn K', 9.5) == []            # below the Zn K edge (9.659 keV)
    assert mm.family_lines('Zn K', 10.0)
    assert mm.family_lines('Br K', 13.0) == []           # Br K edge 13.474 keV
    names = [n for n, _, _ in mm.family_lines('Pb L', 14.0)]
    assert 'La1' in names and 'Lb1' not in names         # Lb1 needs the L2 edge (15.2 keV)


def test_main_lines_are_the_tabulated_ones():
    assert mm.main_line('Zn K', 10.0)[0] == pytest.approx(mca.line_energy('Zn'), abs=2e-3)
    assert mm.main_line('Pb L', 14.0)[0] == pytest.approx(10.54, abs=0.02)


def test_photons_are_conserved():
    s = mm.spectrum({'Zn K': 1e3, 'Pb L': 500.0}, 0.0, mca.Beam(energy=14.0), mca.Detector(escape=0.0), 0.0)
    assert mm.family_photons(s, 'Zn K') == pytest.approx(1e3, rel=1e-4)      # intensities kept to 6 decimals
    assert mm.family_photons(s, 'Pb L') == pytest.approx(500.0, rel=1e-4)
    # an ideal detector puts every photon in its photopeak
    assert mm.photopeak_family(s, 'Zn K').sum() == pytest.approx(1e3, rel=1e-3)


def test_tabulated_compton_matches_the_shell_model_under_zn():
    """The O 1s wing under Zn Kα at 10 keV: tabulated Hartree-Fock (Biggs)
    profiles against study B's hydrogenic shells, within 3 % (measured
    0.99, 2026-11-25)."""
    e = None
    core = {}
    for model in ('shells', 'biggs'):
        s = mm.spectrum({}, 1e6, mca.Beam(), mca.Detector(escape=0.0), 0.0, compton=model)
        e = s.energy
        box = (e > 8.63 - 0.3) & (e < 8.63 + 0.3)
        core[model] = s.part(sources=['Compton core'])[box].sum()
    assert core['biggs'] / core['shells'] == pytest.approx(1.0, abs=0.03)


def test_core_compton_stops_at_the_binding():
    b = mca.Beam()
    e1 = np.linspace(9.0, 9.99, 400)
    val, core = mm.biggs_compton(b, e1)
    o1s = [s for s in mm._SHELLS if s[0] == 'O 1s'][0][3]
    assert np.all(core[b.energy - e1 < o1s] == 0)
    assert core[b.energy - e1 > o1s + 0.05].max() > 0


def test_compton_total_matches_the_incoherent_scattering_function():
    """Binding cuts water's Compton scatter at 10 keV and 90° to S(x)/Z of
    the free-electron value: xraylib's SF_Compt gives (S_O + 2 S_H)/10 =
    0.808 at x = 0.570 1/Å (computed 2026-11-25, xraylib 4.3.0; an
    independent table from the Compton profiles). The impulse approximation
    on the tabulated profiles gives 0.799 (measured): within 2 %."""
    b = mca.Beam()
    de = 0.002
    e1 = np.arange(b.compton - 4.0, b.energy, de)
    val, core = mm.biggs_compton(b, e1)
    total = (val.sum() + core.sum()) * de
    assert math.isfinite(total)
    assert total == pytest.approx(0.808, rel=0.02)
