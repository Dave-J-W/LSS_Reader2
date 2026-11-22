"""Is every committed output up to date with what made it?

For each job of ``registry`` the manifest (``docs/figures/MANIFEST.json``;
private jobs: ``sample_data/private/figures/MANIFEST.json``, git-ignored)
records the command, a hash of every input and of every output. An input
is a file of the repository that the run used, as ``lss_tools.trace``
recorded it:

- the code that ran: the tool and every repository module it imported
  (lss_core, tests/synthetic, tests/demonstrator, sibling tools), hashed
  **by its syntax tree without docstrings and comments**, so that editing
  prose or comments does not make an output stale, while any change to
  code (a number, a string, a default) does;
- the data it opened (the NX school SPEC file and the frames it read, a
  CSV), hashed by content (text files with their line ends made '\\n',
  so that a Windows checkout gives the same hash).

Not inputs: Python and the libraries (NumPy, SciPy, matplotlib; their
versions are written to the manifest so that a difference can be
explained), modules that a tool's imports could reach but the run never
imported, and files outside the repository. A job whose registry entry
lists ``inputs`` globs counts only the traced files matching them
(``controls.md``: the tooltips are in mainwindow.py and the .ui files, not
in lss_core).

``check()`` compares the recorded hashes with the files as they are:
hashing only, nothing is run (the freshness test calls it).
"""
import ast
import datetime
import fnmatch
import glob
import hashlib
import json
import os
import subprocess
import sys

from . import registry as reg

ROOT = reg.ROOT
MANIFEST = 'docs/figures/MANIFEST.json'
PRIVATE_MANIFEST = reg.PRIVATE_FIGURES + '/MANIFEST.json'
_SKIP_DOC = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def abspath(rel):
    return os.path.join(ROOT, *rel.split('/'))


def rel(path):
    return os.path.relpath(os.path.abspath(path), ROOT).replace(os.sep, '/')


# ---------------------------------------------------------------- hashing

def _canon(node, out):
    """Syntax tree as text, independent of the Python version: fields that
    are empty or None (which new versions add or drop) are left out, and
    positions are not fields."""
    if isinstance(node, ast.AST):
        out.append(type(node).__name__ + '(')
        body_doc = isinstance(node, _SKIP_DOC)
        for name in node._fields:
            v = getattr(node, name, None)
            if body_doc and name == 'body' and v and isinstance(v[0], ast.Expr) and \
                    isinstance(v[0].value, ast.Constant) and isinstance(v[0].value.value, str):
                v = v[1:]                            # the docstring
            if v is None or (isinstance(v, list) and not v):
                continue
            out.append(name + '=')
            _canon(v, out)
            out.append(',')
        out.append(')')
    elif isinstance(node, list):
        out.append('[')
        for x in node:
            _canon(x, out)
            out.append(',')
        out.append(']')
    else:
        out.append(repr(node))


def code_text(path):
    """What of a Python file counts: its syntax tree without docstrings."""
    with open(path, 'rb') as f:
        tree = ast.parse(f.read(), filename=path)
    out = []
    _canon(tree, out)
    return ''.join(out).encode('utf-8')


def data_bytes(path):
    with open(path, 'rb') as f:
        b = f.read()
    if b'\0' not in b[:8192]:                        # text: line ends as '\n'
        b = b.replace(b'\r\n', b'\n')
    return b


def file_hash(relpath, cache=None):
    """16 hex digits of SHA-256; Python files by their code only."""
    if cache is not None and relpath in cache:
        return cache[relpath]
    p = abspath(relpath)
    if not os.path.isfile(p):
        h = 'missing'
    else:
        try:
            b = code_text(p) if relpath.endswith('.py') else data_bytes(p)
        except SyntaxError:
            b = data_bytes(p)
        h = hashlib.sha256(b).hexdigest()[:16]
    if cache is not None:
        cache[relpath] = h
    return h


def combined(hashes):
    """One hash for a {path: hash} set."""
    text = ''.join('%s %s\n' % kv for kv in sorted(hashes.items()))
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


# ---------------------------------------------------------------- outputs of a job

def _matches(path, globs):
    return any(fnmatch.fnmatchcase(path, g) for g in globs)


def owned_files(job):
    """The files the job's output globs match now (its ignored ones excepted;
    README.md files are hand-written and never outputs)."""
    found = set()
    for g in job.outputs:
        for p in glob.glob(abspath(g)):
            r = rel(p)
            if os.path.isfile(p) and not _matches(r, tuple(job.ignore) + tuple(reg.FROZEN)) and \
                    os.path.basename(r) != 'README.md' \
                    and r not in (MANIFEST, PRIVATE_MANIFEST):
                found.add(r)
    return sorted(found)


def inputs_from_trace(job, record):
    """{path: hash} of a job's inputs from a trace record."""
    files = set(record.get('modules', [])) | set(record.get('reads', []))
    outs = set(job.outputs) | set(job.ignore) | ({job.stdout} if job.stdout else set())
    files = {f for f in files if not _matches(f, outs) and f not in (MANIFEST, 'lss_tools/trace.py', 'lss_tools/__init__.py')}
    if job.inputs:
        files = {f for f in files if _matches(f, job.inputs)}
    cache = {}
    return {f: file_hash(f, cache) for f in sorted(files)}


# ---------------------------------------------------------------- manifest

def manifest_path(private=False):
    return abspath(PRIVATE_MANIFEST if private else MANIFEST)


def load(private=False):
    p = manifest_path(private)
    if not os.path.isfile(p):
        return {'jobs': {}}
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def save(manifest, private=False):
    p = manifest_path(private)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    manifest['about'] = ('Written by python -m lss_tools.regenerate; do not edit by hand. For every job '
                         '(lss_tools/registry.py): its command, the hash of each input (code by syntax '
                         'tree, data by content) and of each output. docs/TOOLS.md explains.')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(manifest, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write('\n')


def libraries():
    out = {'python': '%d.%d.%d' % sys.version_info[:3]}
    for name in ('numpy', 'scipy', 'matplotlib', 'PyQt5.QtCore'):
        try:
            m = __import__(name, fromlist=['x'])
            out[name.split('.')[0]] = getattr(m, '__version__', None) or getattr(m, 'PYQT_VERSION_STR', '')
        except Exception:
            pass
    return out


def commit():
    try:
        r = subprocess.run(['git', 'describe', '--always', '--dirty'], cwd=ROOT,
                           capture_output=True, text=True, timeout=20)
        return r.stdout.strip()
    except Exception:
        return ''


def entry(tool, job, record, seconds):
    """The manifest entry of a finished run."""
    ins = inputs_from_trace(job, record)
    outs = {f: file_hash(f) for f in owned_files(job)}
    cmd = ' '.join([tool.command] + [_quote(a) for a in job.argv()])
    if job.stdout:
        cmd += ' > ' + job.stdout
    return {'tool': tool.id, 'command': cmd, 'inputs': ins, 'inputs_hash': combined(ins),
            'outputs': outs, 'seconds': round(seconds, 1), 'made': datetime.date.today().isoformat(),
            'commit': commit(), 'libraries': libraries()}


def _quote(a):
    return a if a and all(c.isalnum() or c in '-_./,:=+' for c in a) else '"%s"' % a


# ---------------------------------------------------------------- checking

def status(job, manifest, cache=None):
    """(state, reasons) of one job: 'fresh', 'stale' (an input changed),
    'unrecorded' (never run through regenerate), or 'outputs' (outputs
    missing, changed or added since the recorded run)."""
    e = manifest.get('jobs', {}).get(job.id)
    if e is None:
        return 'unrecorded', ['no entry in the manifest']
    cache = {} if cache is None else cache
    changed = [f for f, h in e['inputs'].items() if file_hash(f, cache) != h]
    if changed:
        return 'stale', ['input changed: ' + f for f in changed]
    why = []
    now = owned_files(job)
    for f, h in e['outputs'].items():
        cur = file_hash(f, cache)
        if cur == 'missing':
            why.append('output missing: ' + f)
        elif cur != h:
            why.append('output differs from the recorded run: ' + f)
    why += ['output not made by the recorded run: ' + f for f in now if f not in e['outputs']]
    if not e['outputs']:
        why.append('the recorded run wrote no output')
    return ('outputs', why) if why else ('fresh', [])


def unclaimed():
    """Files in the generated folders that no public job owns."""
    owned = set()
    ignored = []
    for _, j in reg.jobs(private=False):
        owned.update(owned_files(j))
        ignored += list(j.ignore)
    out = []
    for d in reg.GENERATED_DIRS:
        for dirpath, _, names in os.walk(abspath(d)):
            for n in names:
                r = rel(os.path.join(dirpath, n))
                if n == 'README.md' or r == MANIFEST or r in owned or _matches(r, ignored + list(reg.FROZEN)):
                    continue
                out.append(r)
    return sorted(out)


def check(private=False):
    """{job id: (state, reasons)} for every job of that kind, and the
    unclaimed files (public only)."""
    m = load(private)
    cache = {}
    res = {j.id: status(j, m, cache) for _, j in reg.jobs(private=private)}
    return res, ([] if private else unclaimed())
