"""An unreadable `#A` line ("#A Absorber " with no value, seen once in a real
file) is an unknown setting, not 63, which is a real setting (D38). Pilatus
frames of such a scan get no absorber factor and are patched as usual (owner,
2026-11-19, D42); MCA scans below it take "unknown" from it (no factor)."""
import numpy as np
import pytest

import sweep
import synth
from lss_core.experiment import Experiment, absorber_setting
from spec_routines import specread


def _blank_absorber(spec, scan):
    """Replace scan ``scan``'s #A line by an empty one."""
    lines = open(spec).read().split('\n')
    k = [l.startswith('#S %d ' % scan) for l in lines].index(True)
    j = next(i for i in range(k, len(lines)) if lines[i].startswith('#A'))
    lines[j] = '#A Absorber '
    open(spec, 'w').write('\n'.join(lines))
    return spec


def test_reader_gives_none_and_keeps_the_text(tmp_path):
    spec = _blank_absorber(synth.make_dataset(tmp_path / 'd'), 2)
    p = specread(spec, data={}, par={}).Par
    assert p[2]['Absorber'] is None and p[2]['AbsorberText'] == ''
    assert p[1]['Absorber'] == 0 and p[1]['AbsorberText'] == '0'
    assert absorber_setting(p[2]) == 0 and absorber_setting(p[1]) == 0 and absorber_setting({}) == 0


def test_mca_scans_below_an_unreadable_line_are_unknown(tmp_path):
    spec, _ = synth.make_xfntr_dataset(tmp_path / 'x', absorber=None, lead_absorber=2)
    _blank_absorber(spec, 1)
    p = specread(spec, data={}, par={}).Par
    assert p[2]['Absorber'] is None and p[2]['AbsorberFrom'] == 1
    exp = Experiment(spec)
    rows = exp.fluorescence([2, 3], window=(5.6, 7.2), absfac=1.4247).rows
    assert rows == exp.fluorescence([2, 3], window=(5.6, 7.2), absfac=1.0).rows    # no factor


def test_script_frames_of_an_unknown_scan_have_no_factor(tmp_path):
    spec = _blank_absorber(synth.make_dataset(tmp_path / 'd'), 2)
    frames = Experiment(spec).frames([2])
    assert frames and all(f.absorber == 0 for f in frames)


@pytest.mark.gui
def test_window_lists_patches_and_says_so_once(window, qapp, recorder, tmp_path):
    spec = _blank_absorber(synth.make_dataset(tmp_path / 'd'), 2)
    w = window
    w.openSpecFile(fname=spec)
    w.directory = str(tmp_path)
    sweep._select_scans(w, qapp, [0, 1])
    n2 = [w.ui.imageListWidget.item(k).text() for k in range(w.ui.imageListWidget.count()) if k >= w.pilScanNum.index(2)]
    assert n2 and all(t.endswith('Abs=?') for t in n2)          # every frame listed (none dropped)
    assert all(w.pil_AbsNum[k] == 0 for k, s in enumerate(w.pilScanNum) if s == 2)
    said = [m for m in recorder.messages if 'absorber setting unknown' in m]
    assert len(said) == 1 and '"#A "' in said[0]
    sweep._select_scans(w, qapp, [1])
    sweep._select_scans(w, qapp, [0, 1])
    assert len([m for m in recorder.messages if 'absorber setting unknown' in m]) == 1
    assert recorder.exceptions == []


@pytest.mark.gui
def test_patch_without_the_setting_gives_the_same_curve(window, qapp, recorder, tmp_path):
    """Owner (2026-11-19): such scans "get patched and normalized all the
    same". The fitted factor absorbs the missing absfac**n, so the patched
    curve equals the one with the setting known (known ratio off in both)."""
    from test_ref_export_golden import reduce_and_save
    out = {}
    for tag, blank in (('known', False), ('blank', True)):
        spec = synth.make_absorber_patch_dataset(tmp_path / tag)
        if blank:
            _blank_absorber(spec, 2)
        window.openSpecFile(fname=spec)
        window.directory = str(tmp_path)
        window.setPreference('patch_auto_known_ratio', False)
        qapp.processEvents()
        out[tag] = str(tmp_path / ('out_' + tag))
        reduce_and_save(window, qapp, recorder, out[tag], [0, 1])
    assert window.refFactors == {}
    a, b = (np.loadtxt(out[t] + '_ref.txt') for t in ('known', 'blank'))
    assert a.shape == b.shape
    assert b == pytest.approx(a, rel=1e-6)
    assert recorder.exceptions == []
