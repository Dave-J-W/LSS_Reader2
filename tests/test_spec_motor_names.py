"""Motor names, cut and whole (TODO area L, 2026-11-24).

The beamline's macro writes each scan's #P names cut to 8 characters
('Two_Thet', 'Sample_T'), and the code looks motors up by those names.
The file header's #O lines hold the full names in the same positions.
Both are now kept, so 'Two_Thet' and 'Two_Theta' both work, whichever
the macro writes; nothing that reads the 8-character names changes."""
import os

import pytest

import synth
from spec_routines import specread

NX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sample_data', 'NX_school', '2026sep',
                  '20260923')


@pytest.mark.skipif(not os.path.exists(NX), reason='NX school data not present')
def test_nx_motors_answer_to_both_names():
    p = specread(NX, data={}, par={}).Par
    for short, full in [('Two_Thet', 'Two_Theta'), ('Sample_T', 'Sample_Th'), ('X_Pinhol', 'X_Pinhole'),
                        ('MIR_HSiz', 'MIR_HSize')]:
        assert p[6][full] == p[6][short], full
    assert p[6]['In_Rot'] == p[6]['In_Rot']                  # whole already: no second key needed
    assert 'In_Rot'[:8] == 'In_Rot'


def test_a_macro_writing_whole_names_answers_to_the_cut_ones(tmp_path):
    spec = synth.make_dataset(str(tmp_path))
    lines = open(spec).read().split('\n')
    k = next(i for i, l in enumerate(lines) if l.startswith('#P0 '))
    names = lines[k][4:].split()
    j = names.index('Two_Thet')
    names[j] = 'Two_Theta'                                   # a macro that writes the whole name
    lines[k] = '#P0 ' + ' '.join(names)
    open(spec, 'w').write('\n'.join(lines))
    want = float(lines[k + 1][1:].split()[j])
    p = specread(spec, data={}, par={}).Par
    assert p[1]['Two_Theta'] == want and p[1]['Two_Thet'] == want


def test_nothing_without_a_header(tmp_path):
    """No #O lines (the synthetic files): the 8-character names as before."""
    spec = synth.make_dataset(str(tmp_path))
    p = specread(spec, data={}, par={}).Par
    names = set(synth.MOTORS)
    assert names <= set(p[1]) and not any(k for k in p[1] if k not in names and k[:8] in names and k != k[:8])
