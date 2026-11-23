"""What a tool accepts and what it is made of, read from the tool itself,
so that the Tools window cannot drift from the scripts.

- ``docstring(path)``: the script's module docstring (static, no import);
- ``uses_argparse(path)``: whether the script builds an ``ArgumentParser``;
- ``capture_parsers(paths)``: each script's real parser (options, defaults,
  choices, help), captured in one subprocess by running the script as
  ``__main__`` until it calls ``parse_args``, which is replaced by a
  function that stops it there. Scripts without argparse are never run;
- ``repo_imports(path)``: the repository's Python files the script imports,
  followed recursively (static, from the import statements).

Command line (used by ``capture_parsers``)::

    python -m lss_toolbox.introspect SCRIPT [SCRIPT ...]     # JSON on stdout
"""
import ast
import json
import os
import subprocess
import sys

from . import ROOT


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def _tree(path):
    import warnings
    with warnings.catch_warnings():          # invalid escape sequences in old docstrings
        warnings.simplefilter('ignore')
        return ast.parse(_read(path), filename=path)


def docstring(path):
    """The module docstring of ``path`` ('' if none)."""
    try:
        return ast.get_docstring(_tree(path)) or ''
    except (OSError, SyntaxError):
        return ''


def summary(path):
    """First paragraph of the docstring, joined into one line."""
    para = docstring(path).strip().split('\n\n')[0]
    return ' '.join(para.split())


def uses_argparse(path):
    """True when the script calls ``ArgumentParser(...)`` anywhere."""
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Call):
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, 'id', '')
            if name == 'ArgumentParser':
                return True
    return False


# ---------------------------------------------------------------- parsers

def _jsonable(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    return repr(v)


def parser_spec(parser):
    """A JSON-able description of an ``argparse.ArgumentParser``: its
    description and one dict per argument (help excluded); a parser with
    subcommands also gets ``subcommands`` {name: description of its parser}."""
    import argparse
    fmt = parser._get_formatter()
    actions = []
    subcommands = {}
    for a in parser._actions:
        if isinstance(a, argparse._HelpAction):
            continue
        if isinstance(a, argparse._SubParsersAction):
            subcommands = {name: parser_spec(p) for name, p in a.choices.items()}
            continue
        if isinstance(a, argparse._StoreTrueAction):
            kind = 'flag'
        elif isinstance(a, argparse._StoreFalseAction):
            kind = 'flag_false'
        elif isinstance(a, argparse._AppendAction):
            kind = 'append'
        elif isinstance(a, argparse._StoreConstAction):
            kind = 'const'
        else:
            kind = 'store'
        try:
            text = fmt._expand_help(a) if a.help else ''
        except Exception:                      # a help string with stray % signs
            text = a.help or ''
        actions.append({
            'dest': a.dest,
            'options': list(a.option_strings),
            'kind': kind,
            'default': _jsonable(a.default),
            'type': getattr(a.type, '__name__', None) if a.type else None,
            'choices': _jsonable(list(a.choices)) if a.choices is not None else None,
            'nargs': _jsonable(a.nargs),
            'required': bool(a.required) if a.option_strings else a.nargs not in ('?', '*'),
            'metavar': _jsonable(a.metavar),
            'help': text,
        })
    out = {'prog': parser.prog, 'description': parser.description or '', 'actions': actions}
    if subcommands:
        out['subcommands'] = subcommands
    return out


class _Captured(BaseException):
    """Raised in place of parsing: carries the parser out of the script."""

    def __init__(self, parser):
        super().__init__('parser captured')
        self.parser = parser


def capture_one(path):
    """The parser spec of the script at ``path``, captured in this process
    (call it in a subprocess: the script's imports and module-level code run
    here). {'error': text} when it fails or never parses arguments."""
    import argparse
    import runpy
    if not uses_argparse(path):
        return {'error': 'no argparse parser'}

    def grab(self, args=None, namespace=None):
        raise _Captured(self)

    saved = (argparse.ArgumentParser.parse_args, argparse.ArgumentParser.parse_known_args,
             list(sys.argv), list(sys.path))
    argparse.ArgumentParser.parse_args = grab
    argparse.ArgumentParser.parse_known_args = grab
    sys.argv = [path]
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    try:
        runpy.run_path(path, run_name='__main__')
        return {'error': 'the script finished without parsing arguments'}
    except _Captured as c:
        return parser_spec(c.parser)
    except SystemExit as e:
        return {'error': 'the script exited (%s) before parsing arguments' % e.code}
    except Exception as e:                    # noqa: BLE001 (reported, not raised)
        return {'error': '%s: %s' % (type(e).__name__, e)}
    finally:
        (argparse.ArgumentParser.parse_args, argparse.ArgumentParser.parse_known_args,
         sys.argv[:], sys.path[:]) = saved


def capture_parsers(paths, timeout=180):
    """{path: spec} for every script, in one subprocess (each script's
    imports run there, never in the caller). Paths relative to the
    repository root are accepted."""
    paths = list(paths)
    if not paths:
        return {}
    env = dict(os.environ, MPLBACKEND='Agg', QT_QPA_PLATFORM='offscreen')
    full = [p if os.path.isabs(p) else os.path.join(ROOT, p) for p in paths]
    r = subprocess.run([sys.executable, '-m', 'lss_toolbox.introspect'] + full, cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=timeout)
    try:
        got = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {p: {'error': 'introspection failed: ' + (r.stderr.strip().splitlines() or ['?'])[-1]}
                for p in paths}
    return {p: got.get(f, {'error': 'not captured'}) for p, f in zip(paths, full)}


# ---------------------------------------------------------------- imports

def _module_file(name, dirs):
    """The repository file of module ``name`` (dotted) found in ``dirs``."""
    parts = name.split('.')
    for d in dirs:
        base = os.path.join(d, *parts)
        for cand in (base + '.py', os.path.join(base, '__init__.py')):
            if os.path.isfile(cand):
                return cand
    return None


def _imports_of(path, dirs):
    """Repository files imported by the file at ``path`` (one level)."""
    out = set()
    try:
        tree = _tree(path)
    except (OSError, SyntaxError):
        return out
    pkg_dir = os.path.dirname(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                parts = a.name.split('.')
                for i in range(1, len(parts) + 1):          # a.b.c imports a, a.b, a.b.c
                    f = _module_file('.'.join(parts[:i]), dirs)
                    if f:
                        out.add(f)
        elif isinstance(node, ast.ImportFrom):
            if node.level:                                   # relative: from . import x / from .x import y
                base = pkg_dir
                for _ in range(node.level - 1):
                    base = os.path.dirname(base)
                here = [base]
                mod = node.module or ''
                f = _module_file(mod, here) if mod else os.path.join(base, '__init__.py')
                if f and os.path.isfile(f):
                    out.add(f)
                for a in node.names:
                    g = _module_file('.'.join(filter(None, [mod, a.name])), here)
                    if g:
                        out.add(g)
            elif node.module:
                parts = node.module.split('.')
                for i in range(1, len(parts) + 1):
                    f = _module_file('.'.join(parts[:i]), dirs)
                    if f:
                        out.add(f)
                for a in node.names:
                    g = _module_file(node.module + '.' + a.name, dirs)
                    if g:
                        out.add(g)
    return out


def repo_imports(path, root=ROOT):
    """Sorted repository-relative paths of the Python files that ``path``
    imports, directly or through other repository files (the script itself
    included). Static: imports inside functions count, imports built at run
    time do not. Search path as the tools set it: the script's folder, the
    repository root, ``tests/``."""
    path = os.path.abspath(path if os.path.isabs(path) else os.path.join(root, path))
    dirs = [os.path.dirname(path), root, os.path.join(root, 'tests')]
    seen, todo = set(), [path]
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        todo.extend(_imports_of(f, dirs) - seen)
    return sorted(os.path.relpath(f, root).replace(os.sep, '/') for f in seen)


def direct_imports(path, root=ROOT):
    """The script, the repository files it imports itself, and what the
    tool-side helpers it imports (anything under ``tests/``: other tools,
    the demonstrator, the synthetic generators) import themselves: the
    files whose change most likely changes the products. ``repo_imports``
    gives everything further down as well."""
    path = os.path.abspath(path if os.path.isabs(path) else os.path.join(root, path))
    dirs = [os.path.dirname(path), root, os.path.join(root, 'tests')]
    tests = os.path.join(root, 'tests') + os.sep
    seen, todo = set(), [path]
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        if f == path or f.startswith(tests):
            todo.extend(_imports_of(f, dirs) - seen)
    return sorted(os.path.relpath(f, root).replace(os.sep, '/') for f in seen)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = {}
    for p in argv:
        out[p] = capture_one(p)
    sys.stdout.write('\n' + json.dumps(out) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
