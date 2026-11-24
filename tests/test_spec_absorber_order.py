"""#A wins over the Absorber motor whatever the line order (TODO area L,
2026-11-24). NX files write the scan's #P4 line, whose motor named
Absorber gives the setting, and then #A; the later line won, which was
#A by luck of order. A macro writing #A first would have let the motor
win. Now #A wins by rule, and a motor value that differs is kept as
'AbsorberMotor'."""
import synth
from spec_routines import specread


def _with_motor(spec, scan, motor, a_first):
    lines = open(spec).read().split('\n')
    s = [k for k, l in enumerate(lines) if l.startswith('#S %d ' % scan)][0]
    p = next(k for k in range(s, len(lines)) if lines[k].startswith('#P0 '))
    lines[p] += ' Absorber'
    lines[p + 1] += ' %r' % motor
    a = next(k for k in range(s, len(lines)) if lines[k].startswith('#A '))
    if a_first:
        lines.insert(p, lines.pop(a))
    open(spec, 'w').write('\n'.join(lines))


def test_a_wins_when_written_first(tmp_path):
    spec = synth.make_dataset(str(tmp_path))
    want = specread(spec, data={}, par={}).Par[2]['Absorber']
    _with_motor(spec, 2, 7.0, a_first=True)
    p = specread(spec, data={}, par={}).Par[2]
    assert p['Absorber'] == want and p['AbsorberMotor'] == 7.0


def test_a_wins_when_written_last_and_agreeing_says_nothing(tmp_path):
    spec = synth.make_dataset(str(tmp_path))
    want = specread(spec, data={}, par={}).Par[2]['Absorber']
    _with_motor(spec, 2, float(want), a_first=False)
    p = specread(spec, data={}, par={}).Par[2]
    assert p['Absorber'] == want and 'AbsorberMotor' not in p
