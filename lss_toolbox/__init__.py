"""The reader's Tools collection: every demonstration and figure generator
of the repository, run from the repository's own code (owner, 2026-11-23:
"Make sure they are generated without staleness, meaning they are built
from what's in the repo and so don't drift").

- ``catalog``: what exists (one entry per menu item: the script, what it
  demonstrates, where its committed products live, the documented
  variations "change this parameter and regenerate to show that");
- ``introspect``: what a script accepts, read from the script itself (its
  argparse parser, captured in a subprocess; its docstring; the repository
  files it imports);
- ``staleness``: whether committed products predate a change to the code
  that makes them: the verified record the audit writes
  (``verified.json``), else git history of the generator and what it
  imports; ``fingerprint`` (code without docstrings and comments) and
  ``trace`` (what a run imported and read) serve it;
- ``runner``: the command line of a run, its output folder, its record;
- ``render``: ``docs/TOOLS.md``, written from the catalogue (a test keeps
  it in step);
- ``window`` / ``menu`` (Qt): the Tools window with one page per item, and
  the Tools menu the reader installs (``menu.install(main_window)``).

Runs as its own program too: ``python -m lss_toolbox`` (the window),
``python -m lss_toolbox --render`` (rewrites docs/TOOLS.md),
``python -m lss_toolbox --stale`` (staleness of every committed product),
``python -m lss_toolbox --audit --record`` (rerun, compare, keep what
matched).
Nothing here is imported by ``lss_core``; the GUI-free parts need no Qt.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def available():
    """(True, '') when tools can be run: a source checkout with tests/tools
    and a Python interpreter (not a packaged build); else (False, why)."""
    if getattr(sys, 'frozen', False):
        return False, 'This packaged build holds neither the tools nor Python; run the reader from the repository.'
    if not os.path.isdir(os.path.join(ROOT, 'tests', 'tools')):
        return False, 'tests/tools is not beside the program (not a source checkout).'
    return True, ''
