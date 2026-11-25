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
        assert e['verdict'] in ('same', 'environment') and e['products'] and e['modules'], item
        assert catalog.get(item).script in e['modules'], item
