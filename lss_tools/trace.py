"""Run a tool as its documented command does, and record what of the
repository it used.

    python -m lss_tools.trace RECORD.json -- tests/tools/burn_figures.py [ARGS ...]

The script runs as ``python SCRIPT ARGS`` would run it (``__name__`` is
'__main__', ``sys.argv`` and ``sys.path[0]`` as for a script). When it
exits, RECORD.json lists, as paths relative to the repository root:

- ``modules``: every module of the repository it imported (its own
  source, lss_core, tests/synthetic, tests/demonstrator, sibling tools,
  ...), i.e. the code that actually ran, lazy imports included only when
  they were reached;
- ``reads``: every other file of the repository it opened for reading
  (SPEC files, images, .ui files, CSV inputs), from Python's 'open' audit
  event (built-in open, io.open, os.open).

Files outside the repository (Python, the libraries, fonts) are not
recorded: the third-party versions are written to the manifest for
information but do not make an output stale (docs/TOOLS.md).
"""
import atexit
import json
import os
import runpy
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _inside(path):
    p = os.path.abspath(path)
    return p.startswith(ROOT + os.sep) and os.sep + '.git' + os.sep not in p[len(ROOT):]


def _rel(path):
    return os.path.relpath(os.path.abspath(path), ROOT).replace(os.sep, '/')


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 3 or argv[1] != '--':
        sys.exit('usage: python -m lss_tools.trace RECORD.json -- SCRIPT [ARGS ...]')
    record, script, args = argv[0], argv[2], argv[3:]
    reads = set()
    writing_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC

    def hook(event, a):
        if event != 'open' or not a:
            return
        path = a[0]
        if isinstance(path, bytes):
            path = os.fsdecode(path)
        if not isinstance(path, str):
            return                                   # a file descriptor
        mode = a[1] if len(a) > 1 else None
        flags = a[2] if len(a) > 2 else 0
        if isinstance(mode, str) and any(c in mode for c in 'wax+'):
            return
        if mode is None and isinstance(flags, int) and flags & writing_flags:
            return
        try:
            if _inside(path) and os.path.isfile(path):
                reads.add(_rel(path))
        except (OSError, ValueError):
            pass

    def dump():
        mods = set()
        for m in list(sys.modules.values()):
            f = getattr(m, '__file__', None)
            if f and f.endswith('.py') and _inside(f) and os.path.isfile(f):
                mods.add(_rel(f))
        mods.add(_rel(script))
        out = {'script': _rel(script), 'args': args, 'modules': sorted(mods),
               'reads': sorted(r for r in reads if not r.endswith(('.py', '.pyc')) and '__pycache__' not in r)}
        with open(record, 'w') as f:
            json.dump(out, f, indent=1)

    atexit.register(dump)
    sys.addaudithook(hook)
    sys.argv = [script] + args
    sys.path[0] = os.path.dirname(os.path.abspath(script))
    runpy.run_path(script, run_name='__main__')


if __name__ == '__main__':
    main()
