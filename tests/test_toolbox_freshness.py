"""Freshness of the Tools collection's committed products (2026-11-25,
after the former patching session's review: "`--stale` flags 23 of 28
items, mostly wrongly"): fingerprints that ignore docstrings and comments
(lss_toolbox.fingerprint), the trace of what a run imported and read
(lss_toolbox.trace), and the verified record the audit writes and
--stale reads (lss_toolbox.staleness)."""
import os
import shutil
import subprocess
import sys

from lss_toolbox import ROOT, catalog, fingerprint, staleness
from lss_toolbox.__main__ import record_verdict


# ---------------------------------------------------------------- fingerprints

def test_a_fingerprint_counts_code_not_prose():
    base = b'"""Module doc."""\nimport os\n\n\ndef f(x):\n    """Doc."""\n    return x + 1  # one\n'
    fp = fingerprint.of_bytes('m.py', base)
    prose = b'"""Another doc."""\nimport os\n\n# a comment\n\ndef f(x):\n    """Changed."""\n    return x + 1\n'
    assert fingerprint.of_bytes('m.py', prose) == fp                    # docstrings, comments, blank lines
    assert fingerprint.of_bytes('m.py', base.replace(b'\n', b'\r\n')) == fp
    assert fingerprint.of_bytes('m.py', base.replace(b'x + 1', b'x + 2')) != fp      # a number
    assert fingerprint.of_bytes('m.py', base.replace(b'import os', b'import sys')) != fp
    assert fingerprint.of_bytes('m.py', base.replace(b'"""Doc."""\n    ', b'')) == fp   # a docstring removed
    first = b'def f(x):\n    "text"\n    return x\n'                   # the first string of a body is its doc
    assert fingerprint.of_bytes('m.py', first) == fingerprint.of_bytes('m.py', first.replace(b'"text"', b'"t2"'))
    later = b'def f(x):\n    y = 1\n    "text"\n    return x\n'         # a later one is code
    assert fingerprint.of_bytes('m.py', later) != fingerprint.of_bytes('m.py', later.replace(b'"text"', b'"t2"'))
    assert fingerprint.of_bytes('m.py', b'x = "\\|"\n') == fingerprint.of_bytes('m.py', b'x = "\\|"  # c\n')
    data = b'a,b\r\n1,2\r\n'
    assert fingerprint.of_bytes('t.csv', data) == fingerprint.of_bytes('t.csv', data.replace(b'\r\n', b'\n'))
    assert fingerprint.of_bytes('t.csv', data) != fingerprint.of_bytes('t.csv', b'a,b\n1,3\n')
    binary = b'\x89PNG\0\r\n'
    assert fingerprint.of_bytes('f.png', binary) != fingerprint.of_bytes('f.png', b'\x89PNG\0\n')   # bytes as they are
    assert fingerprint.of_bytes('bad.py', b'def (:\n') == fingerprint.of_bytes('bad.txt', b'def (:\n')
    assert len(fp) == 16 and fingerprint.of_file('no/such/file.py') == 'missing'


# ---------------------------------------------------------------- the trace

def test_the_trace_records_modules_and_reads(tmp_path):
    script = tmp_path / 'tool.py'
    out = tmp_path / 'made.txt'
    script.write_text(
        'import sys\nsys.path.insert(0, %r)\n'
        'from lss_core import fresnel\n'
        'open(%r).read()\n'
        'with open(%r, "w") as f:\n    f.write(str(fresnel.fresnel(0.05, 0.0217)))\n'
        'print("args", sys.argv[1:], __name__)\n'
        'sys.exit(3)\n' % (ROOT, os.path.join(ROOT, 'docs', 'TOOLS.md'), str(out)))
    rec = tmp_path / 'trace.json'
    r = subprocess.run([sys.executable, '-m', 'lss_toolbox.trace', str(rec), '--', str(script), '--x', '1'],
                       cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 3 and "args ['--x', '1'] __main__" in r.stdout      # as `python tool.py --x 1`
    import json
    t = json.loads(rec.read_text())
    assert {'lss_core/fresnel.py', 'lss_core/__init__.py'} <= set(t['modules'])
    assert not set(t['modules']) & {'lss_toolbox/trace.py', 'lss_toolbox/__init__.py'}   # the tracer's own
    assert t['reads'] == ['docs/TOOLS.md'] and t['args'] == ['--x', '1']           # files outside: not recorded
    assert out.exists()


# ---------------------------------------------------------------- a small repository

def _git(root, *args):
    subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false'] + list(args),
                   cwd=root, check=True, capture_output=True)


def _write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write(text)


FILES = {'tests/tools/make.py': 'from pkg import near\n', 'pkg/__init__.py': '',
         'pkg/near.py': '"""Near."""\nfrom pkg import far\nX = 1\n', 'pkg/far.py': '"""Far."""\nY = 1\n',
         'pkg/unused.py': 'Q = 1\n', 'out/fig.png': 'png', 'out/notes.md': 'hand-written', 'data.txt': 'd'}
ITEM = catalog.Tool('t', 'T', 'gid', 'figures', 'tests/tools/make.py', 'demo', committed=('out',),
                    inputs=('data.txt',))


def _repo(tmp_path):
    root = str(tmp_path / 'repo')
    for rel, text in FILES.items():
        _write(root, rel, text)
    _git(root, 'init', '-q')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'first')
    return root


def test_git_history_ignores_changes_to_prose(tmp_path):
    root = _repo(tmp_path)
    _write(root, 'pkg/far.py', '"""Far, explained better."""\n# why Y is 1\nY = 1\n')
    _git(root, 'commit', '-q', '-am', 'docs only')
    st = staleness.product_status(ITEM, root=root, verified={})
    assert st.state == 'current' and st.prose_only == ['pkg/far.py'] and st.changes == []
    assert 'comments or docstrings' in st.details()
    _write(root, 'pkg/far.py', '"""Far."""\nY = 2\n')
    st = staleness.product_status(ITEM, root=root, verified={})       # modified, not committed: code
    assert st.state == 'indirect' and st.dirty == ['pkg/far.py']
    _git(root, 'commit', '-q', '-am', 'code')
    _write(root, 'pkg/far.py', '"""Far."""\nY = 1\n')                   # and back: the same code as the products'
    assert staleness.product_status(ITEM, root=root, verified={}).state == 'current'
    assert staleness.code_changed('HEAD', ['pkg/far.py', 'pkg/gone.py'], root=root) == ['pkg/far.py']
    assert staleness.blobs_at('HEAD', ['pkg/far.py', 'pkg/gone.py'], root=root) == {
        'pkg/far.py': b'"""Far."""\nY = 2\n', 'pkg/gone.py': None}


def test_the_verified_record(tmp_path):
    root = _repo(tmp_path)
    _write(root, 'pkg/far.py', '"""Far."""\nY = 5\n')                  # code changed after the products
    _git(root, 'commit', '-q', '-am', 'far changes')
    assert staleness.product_status(ITEM, root=root).state == 'indirect'   # git: may be stale
    trace = {'modules': ['tests/tools/make.py', 'pkg/__init__.py', 'pkg/near.py', 'pkg/far.py'],
             'reads': ['data.txt']}
    entry = staleness.verification(ITEM, trace, ['out/fig.png'], 'same', root=root, unverified=['out/notes.md'])
    assert set(entry['modules']) == set(trace['modules']) and set(entry['reads']) == {'data.txt'}
    assert entry['products'] == {'out/fig.png': fingerprint.of_file('out/fig.png', root)}
    assert entry['commit'] and entry['modified'] == [] and 'python' in entry['environment']
    staleness.save_verified({'t': entry}, root=root)
    assert staleness.load_verified(root)['t']['verdict'] == 'same'
    st = staleness.product_status(ITEM, root=root)
    assert st.state == 'current' and st.verified and 'verified by a rerun' in st.line()
    assert 'pkg/unused.py' not in st.deps and 'Depends on' in st.details()
    _write(root, 'pkg/near.py', '"""Near, with a better docstring."""\nfrom pkg import far\nX = 1  # x\n')
    _write(root, 'pkg/unused.py', 'Q = 2\n')                             # imported by nothing that ran
    assert staleness.product_status(ITEM, root=root).state == 'current'
    _write(root, 'pkg/far.py', '"""Far."""\nY = 6\n')
    st = staleness.product_status(ITEM, root=root)
    assert st.state == 'indirect' and st.changed_files == ['pkg/far.py'] and st.dirty == ['pkg/far.py']
    assert 'since verification' in st.line()
    _write(root, 'data.txt', 'new data')
    st = staleness.product_status(ITEM, root=root)
    assert st.state == 'stale' and st.changed_direct == ['data.txt']
    _write(root, 'pkg/far.py', '"""Far."""\nY = 5\n')
    _write(root, 'data.txt', 'd')
    assert staleness.product_status(ITEM, root=root).state == 'current'
    _write(root, 'out/notes.md', 'edited by hand')                       # not a verified product: no matter
    assert staleness.product_status(ITEM, root=root).verified
    _write(root, 'out/fig.png', 'png2')                                  # products remade: the record no longer
    st = staleness.product_status(ITEM, root=root)                       # applies; git history decides
    assert st.verified is None and st.state == 'indirect'
    bare = str(tmp_path / 'bare')                                        # a checkout without git
    shutil.copytree(root, bare, ignore=shutil.ignore_patterns('.git'))
    _write(bare, 'out/fig.png', 'png')
    assert staleness.product_status(ITEM, root=bare).state == 'current'
    assert staleness.product_status(ITEM, root=bare, verified={}).state == 'unknown'


def test_what_the_audit_records():
    def counts(img, txt):
        return {'image': img, 'text': txt}
    assert record_verdict({}, counts((4, 0, 0), (3, 0, 0))) == 'same'
    assert record_verdict({}, counts((0, 0, 0), (2, 0, 1))) == 'same'                 # a hand-written file not made
    assert record_verdict({}, counts((0, 0, 0), (0, 0, 2))) is None                   # nothing compared
    assert record_verdict({}, counts((0, 0, 0), (2, 1, 0))) is None                   # a table differs
    assert record_verdict({'environment': 2}, counts((1, 2, 0), (0, 0, 1))) == 'environment'
    assert record_verdict({'environment': 1, 'code': 1}, counts((0, 2, 0), (0, 0, 0))) is None
    assert record_verdict({'unknown': 1}, counts((0, 1, 0), (0, 0, 0))) is None


def test_the_committed_record_names_real_items():
    """lss_toolbox/verified.json: every entry is a catalogue item with
    committed products, and records what a rerun used."""
    rec = staleness.load_verified()
    ids = {t.id for t in catalog.TOOLS if t.committed}
    assert set(rec) <= ids
    for item, e in rec.items():
        assert e['verdict'] in ('same', 'environment', 'stamp') and e['products'] and e['modules'], item
        assert catalog.get(item).script in e['modules'], item


def test_the_environment_a_figure_was_drawn_in():
    """What can change a figure without its code (2026-11-25, the review:
    two figures differed under the same pinned numpy, scipy, matplotlib and
    pillow): the run records name the machine, numpy's SIMD level, the
    freetype matplotlib draws text with and its helper libraries; the audit
    lists what differs from a record's environment."""
    from lss_toolbox import runner
    env = runner.environment_versions()
    assert {'python', 'machine', 'numpy', 'matplotlib', 'freetype', 'numpy_simd', 'kiwisolver'} <= set(env)
    assert runner.environment_diff(env, env) == []
    old = dict(env, matplotlib='3.0', gone='1')
    assert runner.environment_diff(old, env) == ['gone: 1 → —', 'matplotlib: 3.0 → %s' % env['matplotlib']]


def test_text_products_compared_apart_from_how_they_were_run(tmp_path):
    """The command a product echoes names the run's folder (2026-11-25:
    compare_methods' manifest, gid_compare_figures' summary, the guard
    study's data summary read 'differs' for that alone); an item's own
    volatile lines (wall times) are left out too."""
    from lss_toolbox import compare

    def put(name, text):
        p = tmp_path / name
        p.write_text(text)
        return str(p)
    a = put('a.json', '{"command": "python t.py", "x": [1, {"command": "y", "v": 2}]}')
    b = put('b.json', '{\n "x": [1, {"v": 2, "command": "z"}],\n "command": "python t.py --out /run/1"\n}')
    assert compare.tables_same(a, b)
    assert not compare.tables_same(a, put('c.json', '{"command": "python t.py", "x": [1, {"v": 3}]}'))
    md1 = put('a.md', 'Command line: `python t.py`\n- result 0.25\n- Total wall time: 109 s.\n')
    md2 = put('b.md', 'Command line: `python t.py --out /run/1`\n- result 0.25\n- Total wall time: 136 s.\n')
    assert not compare.tables_same(md1, md2)                                  # the wall time: not by default
    assert compare.tables_same(md1, md2, volatile=(r'wall time',))
    md3 = put('c.md', 'Command line: x\n- result 0.26\n- Total wall time: 1 s.\n')
    assert not compare.tables_same(md1, md3, volatile=(r'wall time',))          # a result changed
    csv1 = put('a.csv', '# Command line: python t.py\n# made in 3 s\nq,seconds\n1,0.2\n')
    csv2 = put('b.csv', '# Command line: python t.py --out /r\n# made in 4 s\nq,seconds\n1,0.9\n')
    assert compare.tables_same(csv1, csv2, volatile=(r'made in',))


def test_a_figure_compared_apart_from_its_revision_stamp(tmp_path):
    """Seven tools print their git revision into their figures, so a rerun
    never matches pixel for pixel (pinhole_figures, gid_patching_diagrams).
    The audit reruns with a dummy revision: what moves is the stamp, masked;
    the rest must be identical."""
    from PIL import Image, ImageDraw
    from lss_toolbox import compare

    def figure(name, stamp, dot=False):
        im = Image.new('RGB', (1200, 500), 'white')                           # a figure's size: a stamp is small
        d = ImageDraw.Draw(im)
        d.line((10, 20, 1190, 400), fill='blue', width=2)                     # the plot
        d.text((10, 470), 'tool.py ' + stamp + ' · NX scan 11', fill='black')  # the footer: text after the stamp
        if dot:
            d.point((600, 100), fill='red')                                   # a real change, away from the stamp
        p = str(tmp_path / name)
        im.save(p)
        return p
    committed = figure('c.png', '01be3fc')
    run = figure('r.png', 'eb88bda-dirty')
    dummy = figure('s.png', compare.STAMP_DUMMY)
    boxes = compare.stamp_boxes(run, dummy)
    assert boxes and all(t >= 455 for t, b, l, r in boxes)                    # only the footer moved
    assert compare.compare(run, committed).state == 'differ'
    assert compare.same_outside(run, committed, boxes)
    assert not compare.same_outside(figure('r2.png', 'eb88bda', dot=True), committed, boxes)
    assert compare.stamp_boxes(run, run) == []
    assert compare.same_outside(run, committed, None) is False
    moved = Image.new('RGB', (1200, 500), 'black')                            # more than 2 % moved: no mask
    moved.save(str(tmp_path / 'm.png'))
    assert compare.stamp_boxes(run, str(tmp_path / 'm.png')) is None
    assert record_verdict({'stamp': 2}, {'image': (3, 2, 0), 'text': (1, 0, 0)}) == 'stamp'
    assert record_verdict({'stamp': 1, 'environment': 1}, {'image': (0, 2, 0), 'text': (0, 0, 0)}) == 'environment'


def test_volatile_lines_and_stamps_named_in_the_catalogue():
    """An item's volatile patterns compile and each matches a line of its
    committed text products (a pattern that matches nothing hides nothing
    and has gone stale); the tools that print their revision take it from
    LSS_TOOLS_REVISION, so the audit can find the stamp."""
    import re
    from lss_toolbox import runner
    from lss_toolbox.__main__ import _prints_revision
    for t in catalog.TOOLS:
        if not t.volatile:
            continue
        lines = []
        for name, path in runner.product_files(t, 'committed').items():
            if os.path.splitext(name)[1].lower() in runner.TEXTS:
                with open(path, encoding='utf-8', errors='replace') as f:
                    lines += f.read().splitlines()
        for p in t.volatile:
            assert any(re.search(p, ln) for ln in lines), (t.id, p)
    assert _prints_revision(catalog.get('pinhole_figures')) and _prints_revision(catalog.get('gid_patching_diagrams'))
    assert not _prints_revision(catalog.get('burn_figures'))


def test_the_audit_verifies_a_check_item(tmp_path, monkeypatch):
    """A 'check' item (gui_map --check) is verified by its exit code, so
    the files it keeps in step are in the record too (2026-11-25: git
    flagged controls.md, the GUI map and the ngui inventory whenever
    mainwindow.py changed; all three were current)."""
    from lss_toolbox import __main__ as cli
    monkeypatch.setenv('LSS_READER_TOOLS_DIR', str(tmp_path / 'runs'))
    lines = cli.audit(only=['gui_map'], record=False)
    row = lines[-1].split(' | ')
    assert row[0] == '| gui_map' and row[2] == '0' and row[4] == '2 / 0 / 0'
