"""L is Qz (lss_core.lattice; TODO area L, 2026-11-24): the beamline's
SPEC lattice makes L = (2π/λ)(sin α + sin β), α = In_Rot, β = Out_Rot. A
fixed-L scan that disagrees by more than 1 % is noted at load, and the
window says so once. Nothing is changed."""
import math
import os

import numpy as np
import pytest

import sweep
from lss_core import lattice
from lss_core.experiment import Experiment
from spec_routines import specread

NX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sample_data', 'NX_school', '2026sep',
                  '20260923')


def test_qz_from_angles():
    assert lattice.qz_from_angles(0.1, None, 1.23984) == pytest.approx(4 * math.pi * math.sin(math.radians(0.1)) / 1.23984)
    assert lattice.qz_from_angles(0.09, 6.5, 1.23984) == pytest.approx(
        2 * math.pi / 1.23984 * (math.sin(math.radians(0.09)) + math.sin(math.radians(6.5))))


@pytest.mark.skipif(not os.path.exists(NX), reason='NX school data not present')
def test_nx_l_is_qz_at_every_fixed_l_scan():
    """Invariant I35, measured 2026-11-24: every NX scan at fixed L agrees
    with its angles to better than 0.001 % (scans 4, 5, 10-15; scan 12 at
    the raised GID level, β = 6.5°)."""
    p = specread(NX, data={}, par={})
    got = {n: lattice.relative_difference(p.Data[n], p.Par[n]) for n in range(1, 16)}
    checked = {n: d for n, d in got.items() if d is not None}
    assert sorted(checked) == [4, 5, 10, 11, 12, 13, 14, 15]
    assert max(abs(d) for d in checked.values()) < 1e-5
    assert all('LMismatch' not in p.Par[n] for n in range(1, 16))


def _fixed_l_scan(dataset, l_value):
    """Scan 4 of the synthetic set at fixed L, with the header's angles
    giving Qz 0.02 Å⁻¹ (α = β)."""
    lines = open(dataset).read().split('\n')
    s = [k for k, l in enumerate(lines) if l.startswith('#S 4 ')][0]
    k = next(k for k in range(s, len(lines)) if lines[k].startswith('#L'))
    labels = lines[k][3:].split()
    lam = float(next(l for l in lines[s:] if l.startswith('#W')).split()[2])
    alpha = math.degrees(math.asin(0.02 * lam / 4 / math.pi))
    p = next(i for i in range(s, len(lines)) if lines[i].startswith('#P0 '))
    names = lines[p][4:].split()
    vals = lines[p + 1][1:].split()
    vals[names.index('In_Rot')] = repr(alpha)
    lines[p] += ' Out_Rot'                                     # the exit angle: specular, β = α
    lines[p + 1] = '# ' + ' '.join(vals + [repr(alpha)])
    lines[k] = '#L L  ' + '  '.join(labels)
    j = k + 1
    while j < len(lines) and lines[j] and not lines[j].startswith('#'):
        lines[j] = '%r ' % l_value + lines[j]
        j += 1
    open(dataset, 'w').write('\n'.join(lines))


def test_an_l_off_its_angles_is_noted(dataset):
    _fixed_l_scan(dataset, 0.02 * 1.05)                        # a lattice 5 % off
    assert Experiment(dataset).scans[4].parameters['LMismatch'] == pytest.approx(0.05, abs=1e-6)


def test_an_l_on_its_angles_is_not(dataset):
    _fixed_l_scan(dataset, 0.02 * 1.005)                       # within 1 %
    assert 'LMismatch' not in Experiment(dataset).scans[4].parameters


def test_no_exit_angle_no_check(dataset):
    """The synthetic files have no Out_Rot: nothing is checked (a raised
    GID arm would otherwise look like a wrong lattice)."""
    assert all('LMismatch' not in s.parameters for s in Experiment(dataset).scans.values())


def test_the_window_says_it_once(window, dataset, qapp, recorder):
    _fixed_l_scan(dataset, 0.02 * 1.05)
    sweep.state_spec_loaded(window, qapp, dataset)
    said = [m for m in recorder.messages if 'L differs from the Qz' in str(m)]
    assert len(said) == 1 and 'Scan(s) 4' in str(said[0]) and '+5.0 %' in str(said[0])
    assert recorder.exceptions == []
