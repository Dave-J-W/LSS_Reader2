"""The script handed over in docs/handoff_out/02 reproduces, from the SPEC
columns alone (ROI counter / Monc), the absorber steps measured from the
images on NX school 20260923 scans 6-9 (tests/test_absorber_steps.py).
Reads only."""
import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
SCRIPT = os.path.join(ROOT, 'docs', 'handoff_out', '02-absorber_steps.py')


def _module():
    spec = importlib.util.spec_from_file_location('absorber_steps_handoff', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_handoff_script_reproduces_the_image_based_steps(capsys):
    out = _module().main([SPEC, '--roi', 'Pilatus'])      # series found automatically
    rows = out['rows']
    assert [(r[0], r[1], r[2], r[3]) for r in rows] == [(6, 7, 41, 31), (7, 8, 31, 24), (8, 9, 24, 18)]
    ratios = [r[6] / r[8] for r in rows]
    assert ratios == pytest.approx([0.789, 0.762, 0.870], abs=1.5e-3)   # images: 0.788, 0.762, 0.870
    assert [r[10] for r in rows] == pytest.approx([33.6, 38.3, 19.6], abs=0.3)
    # one common fraction for every foil does not describe these steps
    assert out['f'] == pytest.approx(0.0743, abs=5e-4)
    assert out['chi2_f'] > 100
    assert '| S6→S7 |' in capsys.readouterr().out


def test_unreadable_absorber_line_is_unknown_not_63(tmp_path):
    m = _module()
    p = tmp_path / 's'
    p.write_text('#S 1  hklscan  0 0  0 0  0.01 0.02  2 1\n#A Absorber ??\n#L H  K  L  Monc  proi\n'
                 '0 0 0.01 100 50\n0 0 0.02 100 40\n')
    assert m.read_spec(str(p))[0]['A'] is None
