"""Packaged builds (F46): the recipe bundles every file the program loads,
names the modules .ui files import, and the self-test a build runs passes
from source."""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, 'packaging', 'lss_reader.spec')


def _sources():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ('tests', 'build', 'dist', '.git', 'sample_data', 'docs')]
        for f in files:
            if f.endswith('.py'):
                yield os.path.join(base, f)


def test_recipe_bundles_every_resource_the_program_loads():
    text = open(SPEC).read()
    loaded = set()
    for p in _sources():
        loaded |= set(re.findall(r"resource\('([^']+)'\)", open(p, encoding='utf-8', errors='replace').read()))
    loaded.discard('mainwindow.py')        # only dated by the About box, which copes without it
    for name in sorted(loaded):
        assert name.endswith('.ui') or name in text, name     # .ui files: the *.ui glob
    assert "glob.glob(os.path.join(ROOT, '*.ui'))" in text
    assert 'C:\\\\' not in text and '/home/' not in text            # nothing machine-specific


def test_recipe_names_the_custom_widget_modules():
    headers = set()
    for f in os.listdir(ROOT):
        if f.endswith('.ui'):
            headers |= set(re.findall(r'<header[^>]*>([^<]+)</header>', open(os.path.join(ROOT, f)).read()))
    text = open(SPEC).read()
    assert headers and all("'%s'" % h in text for h in headers), headers


def test_about_box_without_source_files(window, qapp, recorder, tmp_path, monkeypatch):
    """A packaged build has no .py files next to it (it raised before)."""
    import mainwindow
    (tmp_path / 'logo.png').write_bytes(b'x')
    monkeypatch.setattr(mainwindow, 'resource', lambda name: str(tmp_path / name))
    window.showAbout()
    assert recorder.exceptions == []
    assert any('Last Update' in m for m in recorder.messages)


def test_about_box_shows_the_release(window, recorder):
    """Help > About said "Version: 1.1", the original's number, until
    2026-11-26; it shows ``lss_core.__version__`` (2.0, the release plan's)."""
    import lss_core
    window.showAbout()
    assert lss_core.__version__ == '2.0'
    assert any('Version: 2.0\n' in m for m in recorder.messages) and not any('1.1' in m for m in recorder.messages)
    assert recorder.exceptions == []


@pytest.mark.slow
def test_self_test_passes_from_source(tmp_path):
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', LSS_SELFTEST_REPORT=str(tmp_path / 'r.txt'))
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'LSS_Reader.py'), '--self-test',
                        os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923'),
                        os.path.join(ROOT, 'tests', 'reference', 'legacy_export', 'nx_scans_6-9')],
                       cwd=str(tmp_path), env=env, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / 'r.txt').read_text().strip().endswith('self-test passed')
