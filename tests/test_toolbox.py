"""The Tools collection (lss_toolbox) stays in step with the repository:
every script in tests/tools is an item, every variation the documents
describe sets options its script really has, every committed figure
belongs to an item, docs/TOOLS.md is the catalogue's rendering; and the
pieces that keep runs from going stale work (parser capture, imports,
staleness from git, pixel comparison, run records). No Qt here; the window
is tested in test_toolbox_gui.py.
"""
import fnmatch
import glob
import os
import subprocess

import numpy as np
import pytest

from lss_toolbox import ROOT, catalog, compare, introspect, render, runner, staleness

TOOLS_DIR = os.path.join(ROOT, 'tests', 'tools')


@pytest.fixture(autouse=True)
def _runs_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv('LSS_READER_TOOLS_DIR', str(tmp_path / 'runs'))


@pytest.fixture(scope='module')
def parsers():
    return introspect.capture_parsers(catalog.scripts())


def _path(ref):
    return os.path.join(ROOT, ref.split(':')[0])


# ---------------------------------------------------------------- catalogue

def test_every_tool_script_is_an_item_or_a_listed_helper():
    on_disk = {os.path.basename(p) for p in glob.glob(os.path.join(TOOLS_DIR, '*.py'))}
    used = {os.path.basename(s) for s in catalog.scripts()}
    assert on_disk - used - set(catalog.HELPERS) == set(), 'add these scripts to lss_toolbox/catalog.py'
    assert used - on_disk == set()
    assert set(catalog.HELPERS) <= on_disk


def test_catalogue_entries_are_well_formed():
    ids = [t.id for t in catalog.TOOLS]
    assert len(ids) == len(set(ids))
    cats = {c for c, _ in catalog.CATEGORIES}
    for t in catalog.TOOLS:
        assert t.category in cats and t.kind in catalog.KINDS, t.id
        assert t.title and t.demonstrates, t.id
        assert t.runnable == (t.kind != 'external'), t.id
        if t.script:
            assert os.path.isfile(os.path.join(ROOT, t.script)), t.script
        for ref in t.docs:
            assert os.path.exists(_path(ref)), (t.id, ref)
        for c in t.committed:
            assert glob.glob(os.path.join(ROOT, c)), (t.id, c)
        for p in t.inputs:
            assert os.path.exists(os.path.join(ROOT, p)), (t.id, p)
        if t.repo_out:
            assert any(t.repo_out == c or c.startswith(t.repo_out) for c in t.committed), t.id
        for v in t.variations:
            assert v.label and v.shows, (t.id, v)
            path, _, line = v.source.partition(':')
            assert os.path.exists(os.path.join(ROOT, path)), (t.id, v.label, v.source)
            if line:
                with open(os.path.join(ROOT, path), encoding='utf-8') as f:
                    n = sum(1 for _ in f)
                assert 1 <= int(line) <= n, (t.id, v.label, v.source)


def test_every_option_a_variation_sets_exists_in_its_script(parsers):
    """The documented variations cannot drift from the scripts: each key is
    an option (or positional) of the script's own parser, each value of an
    option with choices is one of them."""
    for t in catalog.TOOLS:
        if not t.runnable:
            continue
        spec = parsers[t.script]
        sets = [('defaults', t.defaults), ('scratch_args', t.scratch_args)] + [(v.label, v.args) for v in t.variations]
        assert bool(spec.get('subcommands')) == bool(t.subcommand), t.id
        if t.subcommand:
            assert t.subcommand in spec['subcommands'], t.id
            spec = runner.effective(spec, t.subcommand)
        if spec.get('error'):
            assert spec['error'] == 'no argparse parser', (t.script, spec['error'])
            assert all(not args for _, args in sets), '%s has no options to set' % t.id
            continue
        for label, args in sets:
            for key, value in args.items():
                a = runner.action_for(spec, key)
                assert a is not None, '%s (%s): the script has no %s' % (t.id, label, key)
                if a['choices'] and isinstance(value, str) and value and runner.OUT not in value:
                    assert value in [str(c) for c in a['choices']], (t.id, label, key, value)
                if a['kind'] in ('flag', 'flag_false'):
                    assert isinstance(value, bool), (t.id, label, key)


def test_every_committed_figure_belongs_to_an_item():
    """A figure committed under docs/ that no item claims would be one
    nobody can regenerate from the Tools menu."""
    out = subprocess.run(['git', 'ls-files', 'docs'], cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip('no git')
    figures = [p for p in out.stdout.split() if os.path.splitext(p)[1].lower() in ('.png', '.svg', '.jpg', '.pdf')]
    assert figures
    claims = [c for t in catalog.TOOLS for c in t.committed]

    def claimed(p):
        return any(p == c or p.startswith(c.rstrip('/') + '/') or fnmatch.fnmatch(p, c) for c in claims)
    assert [p for p in figures if not claimed(p)] == []


def test_tools_page_is_the_rendering_of_the_catalogue():
    with open(render.PAGE, encoding='utf-8') as f:
        assert f.read() == render.page(), 'run: python -m lss_toolbox --render'


def test_rendered_commands_carry_the_variations():
    t = catalog.get('pinhole_beam_profile')
    assert render.command(t) == 'python tests/tools/pinhole_beam_profile.py'
    assert render.command(t, t.variations[0].args) == 'python tests/tools/pinhole_beam_profile.py --fwhm-v 0.060'
    t = catalog.get('patch_demo')
    edge = [v for v in t.variations if v.label == 'Critical-edge aside'][0]
    assert render.command(t, edge.args).endswith('--set truth=water --set plan=edge')
    t = catalog.get('ref_patch_survey')
    assert '--split' not in render.command(t, t.variations[0].args)


# ---------------------------------------------------------------- introspection

def test_parsers_are_read_from_the_scripts(parsers):
    spec = parsers['tests/tools/timeline_mock.py']
    assert set(spec['subcommands']) == {'survey', 'mock'}
    mock = runner.effective(spec, 'mock')
    assert runner.build_args(mock, {'--no-reduce': True}, None) == ['mock', '--no-reduce']
    spec = parsers['tests/tools/pinhole_beam_profile.py']
    fwhm = runner.action_for(spec, '--fwhm-v')
    assert fwhm['default'] == 0.030 and fwhm['type'] == 'float' and 'FWHM' in fwhm['help']
    spec = parsers['tests/tools/ref_patch_gauntlet.py']
    assert runner.action_for(spec, '--design')['choices'] == ['core', 'grid', 'random', 'all']
    assert runner.action_for(spec, '--out')['required']
    assert parsers['tests/tools/absorber_steps.py'] == {'error': 'no argparse parser'}
    assert runner.action_for(parsers['tests/tools/spec_epoch.py'], 'specs')['nargs'] == '*'


def test_capture_never_runs_a_script_past_its_parser(tmp_path):
    flag = tmp_path / 'ran.txt'
    with_parser = tmp_path / 'with_parser.py'
    with_parser.write_text('import argparse\nap = argparse.ArgumentParser()\nap.add_argument("--n", type=int, '
                           'default=3)\na = ap.parse_args()\nopen(%r, "w").write("ran")\n' % str(flag))
    without = tmp_path / 'without.py'
    without.write_text('open(%r, "w").write("ran")\n' % str(flag))
    got = introspect.capture_parsers([str(with_parser), str(without)])
    assert runner.action_for(got[str(with_parser)], '--n')['default'] == 3
    assert got[str(without)] == {'error': 'no argparse parser'}
    assert not flag.exists()


def test_imports_follow_tool_helpers_into_lss_core():
    deps = introspect.repo_imports('tests/tools/pinhole_figures.py')
    assert {'tests/tools/pinhole_figures.py', 'tests/tools/pinhole_frames.py', 'lss_core/pinhole.py',
            'lss_core/experiment.py'} <= set(deps)
    direct = introspect.direct_imports('tests/tools/pinhole_figures.py')
    assert 'lss_core/experiment.py' in direct          # through the helper pinhole_frames
    assert 'lss_core/patching.py' in deps and 'lss_core/patching.py' not in direct
    demo = introspect.repo_imports('tests/tools/patch_demo.py')
    assert 'tests/demonstrator/window.py' in demo and 'tests/synthetic/xrr.py' in demo


# ---------------------------------------------------------------- staleness

def _git(root, *args):
    subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false'] + list(args),
                   cwd=root, check=True, capture_output=True)


def test_staleness_from_git_history(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, 'tests', 'tools'))
    os.makedirs(os.path.join(root, 'pkg'))
    os.makedirs(os.path.join(root, 'out'))
    files = {'tests/tools/make.py': 'from pkg import near\n', 'pkg/__init__.py': '',
             'pkg/near.py': 'from pkg import far\nX = 1\n', 'pkg/far.py': 'Y = 1\n', 'out/fig.png': 'png',
             'data.txt': 'd'}
    for rel, text in files.items():
        with open(os.path.join(root, rel), 'w') as f:
            f.write(text)
    _git(root, 'init', '-q')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'first')
    item = catalog.Tool('t', 'T', 'gid', 'figures', 'tests/tools/make.py', 'demo', committed=('out',),
                        inputs=('data.txt',))
    st = staleness.product_status(item, root=root)
    assert st.state == 'current' and 'pkg/far.py' in st.deps and 'pkg/far.py' not in st.direct
    with open(os.path.join(root, 'pkg/far.py'), 'w') as f:
        f.write('Y = 2\n')
    _git(root, 'commit', '-q', '-am', 'far changes')
    st = staleness.product_status(item, root=root)
    assert st.state == 'indirect' and st.changed_files == ['pkg/far.py']
    with open(os.path.join(root, 'pkg/near.py'), 'a') as f:
        f.write('Z = 3\n')
    st = staleness.product_status(item, root=root)        # modified, not committed
    assert st.state == 'stale' and st.dirty == ['pkg/near.py'] and 'may be stale' in st.line()
    _git(root, 'commit', '-q', '-am', 'near changes')
    with open(os.path.join(root, 'out/fig.png'), 'w') as f:
        f.write('png2')
    _git(root, 'commit', '-q', '-am', 'figure remade')
    assert staleness.product_status(item, root=root).state == 'current'
    with open(os.path.join(root, 'data.txt'), 'w') as f:
        f.write('new data')
    _git(root, 'commit', '-q', '-am', 'data')
    st = staleness.product_status(item, root=root)
    assert st.state == 'stale' and st.changed_direct == ['data.txt']
    assert staleness.product_status(catalog.Tool('n', 'N', 'gid', 'text', 'tests/tools/make.py', 'd'),
                                    root=root).state == 'none'


# ---------------------------------------------------------------- comparison, runs

def test_pixel_comparison(tmp_path):
    from PIL import Image
    a = np.zeros((20, 30, 3), np.uint8)
    Image.fromarray(a).save(tmp_path / 'a.png')
    Image.fromarray(a).save(tmp_path / 'b.png')
    b = a.copy()
    b[5:7, 10:13] = 255
    Image.fromarray(b).save(tmp_path / 'c.png')
    Image.fromarray(np.zeros((21, 30, 3), np.uint8)).save(tmp_path / 'd.png')
    assert compare.compare(tmp_path / 'a.png', tmp_path / 'b.png').state == 'same'
    d = compare.compare(tmp_path / 'a.png', tmp_path / 'c.png')
    assert d.state == 'differ' and d.box == (5, 6, 10, 12) and d.fraction == pytest.approx(6 / 600)
    assert compare.compare(tmp_path / 'a.png', tmp_path / 'd.png').state == 'size'
    assert compare.difference_rgb(str(tmp_path / 'a.png'), d.mask)[5, 10].tolist() == [255, 255, 255]


def test_build_args():
    spec = {'actions': [
        {'dest': 'out', 'options': ['--out'], 'kind': 'store', 'default': None, 'choices': None, 'nargs': None,
         'required': False},
        {'dest': 'seeds', 'options': ['--seeds'], 'kind': 'store', 'default': 300, 'choices': None, 'nargs': None,
         'required': False},
        {'dest': 'scans', 'options': ['--scans'], 'kind': 'store', 'default': [11], 'choices': None, 'nargs': '+',
         'required': False},
        {'dest': 'set', 'options': ['--set'], 'kind': 'append', 'default': [], 'choices': None, 'nargs': None,
         'required': False},
        {'dest': 'quick', 'options': ['--quick'], 'kind': 'flag', 'default': False, 'choices': None, 'nargs': 0,
         'required': False},
        {'dest': 'path', 'options': [], 'kind': 'store', 'default': None, 'choices': None, 'nargs': None,
         'required': True}]}
    vals = {'--out': '{out}', '--seeds': '300', '--scans': '11 12', '--set': 'a=1 b=2', '--quick': True,
            'path': 'x y'}
    assert runner.build_args(spec, vals, '/r') == ['--out', '/r', '--scans', '11', '12', '--set', 'a=1', '--set',
                                                  'b=2', '--quick', 'x', 'y']
    assert runner.build_args(spec, dict(vals, **{'--quick': False}), None)[:2] == ['--scans', '11']
    assert runner.missing_required(spec, {'path': ''}) == ['path']
    assert runner.values_from(spec, {'--seeds': '60', 'path': 'p'}) == {'--seeds': '60', 'path': 'p'}
    with pytest.raises(KeyError):
        runner.values_from(spec, {'--nope': 1})
    assert runner.build_args({'actions': []}, {}, '/r', free='a "b c" {out}') == ['a', 'b c', '/r']
    # a value starting with '-' goes as --opt=value (argparse would read it as an option)
    assert runner.build_args(spec, {'--seeds': '-3'}, None) == ['--seeds=-3']


def test_a_run_writes_its_record_and_output(parsers, tmp_path):
    item = catalog.get('foil_fit_from_joins')
    run_dir, code = runner.run_item(item, parsers[item.script])
    assert code == 0 and run_dir.startswith(str(tmp_path / 'runs' / 'foil_fit_from_joins'))
    rec = runner.read_record(run_dir)
    assert rec['exit_code'] == 0 and rec['item'] == item.id and rec['finished']
    assert rec['command'] == 'python tests/tools/foil_fit_from_joins.py docs/handoff_out/03-answer/joins.csv'
    with open(os.path.join(run_dir, runner.STDOUT), encoding='utf-8') as f:
        assert '963 joins at 10 keV' in f.read()
    assert runner.past_runs(item.id) == [run_dir]
    assert list(runner.product_files(item, run_dir)) == [runner.STDOUT]
    figs = runner.product_files(catalog.get('pinhole_figures'), 'committed')
    assert 'case1_lab_frame_and_detector.png' in figs
    env = runner.environment(run_dir)
    assert env['QT_QPA_PLATFORM'] == 'offscreen' and env['LSS_READER_LOG_DIR'].startswith(run_dir)
    assert 'QT_QPA_PLATFORM' not in runner.environment(run_dir, base={}, gui=True)


def test_why_a_product_differs():
    """The audit's verdict from three comparisons (2026-11-23: the
    stray-light and beam figures differed only because they had been drawn
    in another environment; the products' own commit, run here, gave what
    the new code gives)."""
    assert runner.classify(True, None, False) == 'current'
    assert runner.classify(False, False, True) == 'environment'
    assert runner.classify(False, True, False) == 'code'
    assert runner.classify(False, False, False) == 'both'
    assert runner.classify(False, None, False) == 'unknown'


def test_a_run_records_its_environment(tmp_path):
    rec = runner.write_record(str(tmp_path), 'x', 'tests/tools/spec_epoch.py', [], 'now')
    env = rec['environment']
    assert env['python'] and env['matplotlib'] and env['numpy']
    assert runner.read_record(str(tmp_path))['environment'] == env



def test_every_demonstrator_setting_a_variation_names_exists():
    """``patch_demo.py --set KEY=VALUE`` takes free text, so the option test
    above cannot check it: each catalogued setting must be a field of the
    demonstrator's configs, with a value its own lists allow."""
    import sys
    sys.path.insert(0, TOOLS_DIR)
    import patch_demo
    from demonstrator import burnmode as bm, refl
    allowed = {'truth': refl.TRUTHS, 'plan': refl.PLANS, 'change': bm.CHANGES}
    for t in catalog.TOOLS:
        if t.script != 'tests/tools/patch_demo.py':
            continue
        for label, args in [('defaults', t.defaults)] + [(v.label, v.args) for v in t.variations]:
            pairs = args.get('--set', [])
            pairs = [pairs] if isinstance(pairs, str) else list(pairs)
            mode = args.get('--mode', t.defaults.get('--mode', 'refl'))
            r, b = patch_demo.configs(pairs, mode)            # raises SystemExit on an unknown key or value type
            for pair in pairs:
                key, value = pair.split('=', 1)
                name = key.rpartition('.')[2]
                if name in allowed:
                    assert value in allowed[name], (t.id, label, pair)
                if name == 'monitor' and mode == 'refl' and not key.startswith('burn.'):
                    assert value in refl.MONITORS, (t.id, label, pair)
