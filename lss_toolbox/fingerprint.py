"""Fingerprints of what a tool's products depend on (2026-11-25; the
former patching session's review: "`--stale` flags 23 of 28 items, mostly
wrongly").

A Python file counts **by its syntax tree without docstrings and
comments**: editing prose does not make a product stale, while any change
to code (a number, a string, a default, an import) does. The tree is
written out without positions and without the empty fields some Python
versions add or drop, so the fingerprint does not depend on the Python
version. Other files (data, ``.ui``) count by their bytes, text with its
line ends made '\\n' (a Windows checkout gives the same fingerprint).

The design is the archived ``claude/archive-tools-freshness`` branch's
(``lss_tools/freshness.py``), brought into the toolbox.
"""
import ast
import hashlib
import os
import warnings

from . import ROOT

_SKIP_DOC = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _canon(node, out):
    if isinstance(node, ast.AST):
        out.append(type(node).__name__ + '(')
        body_doc = isinstance(node, _SKIP_DOC)
        for name in node._fields:
            v = getattr(node, name, None)
            if body_doc and name == 'body' and v and isinstance(v[0], ast.Expr) and \
                    isinstance(v[0].value, ast.Constant) and isinstance(v[0].value.value, str):
                v = v[1:]                                    # the docstring
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


def code_bytes(source):
    """What of Python source counts: its syntax tree without docstrings."""
    out = []
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', SyntaxWarning)         # an old escape sequence: still the same code
        tree = ast.parse(source)
    _canon(tree, out)
    return ''.join(out).encode('utf-8')


def data_bytes(raw):
    if b'\0' not in raw[:8192]:                              # text: line ends as '\n'
        raw = raw.replace(b'\r\n', b'\n')
    return raw


_CACHE = {}                                                  # (is code, SHA-256 of the raw bytes) -> fingerprint


def of_bytes(path, raw):
    """16 hex digits of SHA-256 of what counts in ``raw``, the content of
    ``path``. Cached by content: --stale meets the same modules in every
    item."""
    key = (path.endswith('.py'), hashlib.sha256(raw).digest())
    if key not in _CACHE:
        _CACHE[key] = _of_bytes(path, raw)
    return _CACHE[key]


def _of_bytes(path, raw):
    if path.endswith('.py'):
        try:
            raw = code_bytes(raw)
        except (SyntaxError, ValueError):
            raw = data_bytes(raw)
    else:
        raw = data_bytes(raw)
    return hashlib.sha256(raw).hexdigest()[:16]


def of_file(rel, root=ROOT):
    """The fingerprint of a repository file now ('missing' when it is gone)."""
    p = os.path.join(root, *rel.split('/'))
    if not os.path.isfile(p):
        return 'missing'
    with open(p, 'rb') as f:
        return of_bytes(rel, f.read())


def of_files(rels, root=ROOT):
    return {r: of_file(r, root) for r in sorted(set(rels))}
