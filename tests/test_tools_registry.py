"""The registry of tools (lss_tools.registry), the freshness of the committed
documentation outputs (docs/figures/MANIFEST.json) and the hashing rules.

Fast: hashing only, nothing is regenerated. When test_documentation_outputs_fresh
fails, run ``python -m lss_tools.regenerate`` (it reruns exactly the stale
jobs and records them) and commit what it wrote; ``--check`` says why.
"""
import glob
import os

import pytest

from lss_tools import freshness as fr
from lss_tools import registry as reg

ROOT = reg.ROOT


def test_every_tool_script_is_registered():
    scripts = {t.script for t in reg.TOOLS if t.script}
    found = {os.path.relpath(p, ROOT).replace(os.sep, '/') for p in glob.glob(os.path.join(ROOT, 'tests', 'tools', '*.py'))}
    missing = sorted(found - scripts - set(reg.HELPERS))
    assert missing == [], 'tools not in lss_tools/registry.py: %s' % missing
    for s in scripts | set(reg.HELPERS):
        assert os.path.isfile(os.path.join(ROOT, s)), s


def test_registry_entries_are_complete():
    ids = [t.id for t in reg.TOOLS]
    assert len(ids) == len(set(ids))
    job_ids = [j.id for _, j in reg.jobs()]
    assert len(job_ids) == len(set(job_ids))
    kinds = {k for k, _ in reg.KINDS}
    for t in reg.TOOLS:
        assert t.kind in kinds and t.data in reg.DATA and t.summary and t.title, t.id
        assert bool(t.script) + bool(t.module) == 1 or t.kind == 'demo', t.id
        assert not any(w in t.title.lower() for w in ('quit', 'exit', 'close')), t.id   # the sweep skips those
        if t.kind == 'demo':
            assert ':' in t.demo, t.id
        for j in t.jobs:
            assert j.outputs and j.out, j.id
            for g in j.outputs + j.ignore:
                if j.private:
                    assert g.startswith(reg.PRIVATE_FIGURES + '/'), (j.id, g)
                else:
                    assert not g.startswith('sample_data/'), (j.id, g)
            if j.private:
                assert j.out.startswith(reg.PRIVATE_FIGURES), j.id


def test_tools_doc_lists_every_tool_and_job():
    with open(os.path.join(ROOT, 'docs', 'TOOLS.md'), encoding='utf-8') as f:
        text = f.read()
    for t in reg.TOOLS:
        assert '`%s`' % t.id in text, t.id
    for _, j in reg.jobs():
        assert '`%s`' % j.id in text, j.id


def test_code_hash_ignores_prose_not_code(tmp_path):
    a = tmp_path / 'a.py'
    a.write_text('"""Doc."""\nimport os\n\ndef f(x):\n    """What f does."""\n    return x + 1  # one\n')
    base = fr.code_text(str(a))
    a.write_text('"""Another docstring,\nlonger."""\nimport os\n\n\ndef f(x):\n    # a comment\n'
                 '    """Changed."""\n    return x + 1\n')
    assert fr.code_text(str(a)) == base
    a.write_text('"""Doc."""\nimport os\n\ndef f(x):\n    return x + 2\n')
    assert fr.code_text(str(a)) != base
    a.write_text('"""Doc."""\nimport os\n\ndef f(x):\n    return x + 1\nLABEL = "Qz (1/A)"\n')
    assert fr.code_text(str(a)) != base            # strings that are not docstrings count


def test_text_data_hash_ignores_line_ends(tmp_path):
    a, b = tmp_path / 'a.txt', tmp_path / 'b.txt'
    a.write_bytes(b'#S 1 scan\n1 2 3\n')
    b.write_bytes(b'#S 1 scan\r\n1 2 3\r\n')
    assert fr.data_bytes(str(a)) == fr.data_bytes(str(b))


def test_generated_folders_hold_only_job_outputs():
    """Every committed file under docs/figures, docs/comparisons_data and
    docs/manual/figures (but README.md) belongs to a job of the registry."""
    assert fr.unclaimed() == []


def test_documentation_outputs_fresh():
    """Each public job's recorded inputs (code by syntax tree, data by
    content) are unchanged, and its outputs are the ones it wrote."""
    res, _ = fr.check()
    bad = {k: v for k, v in res.items() if v[0] != 'fresh'}
    msg = '; '.join('%s: %s (%s)' % (k, s, ', '.join(why[:3])) for k, (s, why) in sorted(bad.items()))
    assert bad == {}, 'stale documentation outputs; run python -m lss_tools.regenerate: ' + msg


@pytest.mark.parametrize('private', [False])
def test_manifest_commands_match_registry(private):
    m = fr.load(private)
    for t, j in reg.jobs(private=private):
        e = m['jobs'].get(j.id)
        if e is not None:
            assert e['tool'] == t.id
            assert e['command'].split()[1] == t.script, j.id


def test_trace_records_the_code_and_data_a_run_used(tmp_path):
    """lss_tools.trace: repository modules imported (not merely importable)
    and repository files opened for reading; writes are not inputs."""
    import json
    import subprocess
    import sys
    script = tmp_path / 'tool.py'
    script.write_text('import sys\nsys.path.insert(0, %r)\nfrom lss_core import absorbers\n'
                      'open(%r).read()\nopen(%r, "w").write("x")\n'
                      % (ROOT, os.path.join(ROOT, 'pyproject.toml'), str(tmp_path / 'out.txt')))
    rec = tmp_path / 'rec.json'
    subprocess.run([sys.executable, '-m', 'lss_tools.trace', str(rec), '--', str(script)], cwd=ROOT, check=True)
    r = json.loads(rec.read_text())
    assert 'lss_core/absorbers.py' in r['modules'] and 'lss_core/burn.py' not in r['modules']
    assert r['reads'] == ['pyproject.toml']
