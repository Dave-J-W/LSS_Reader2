"""File names as the reader shows and builds them, whatever the separator.

A path from Qt's file dialogs has '/' on every system; one typed, stored
in preferences or written on Windows may have '\\'. Splitting on one of
them by hand gave the whole path as a plot legend on Linux and macOS, and
splitting on '.' hid a scan's images when the SPEC name had a dot in it
(``run.v2``; TODO area L, 2026-11-24). These helpers treat both separators
alike and take extensions with ``splitext``.
"""
import posixpath


def _norm(path):
    return str(path).replace('\\', '/').rstrip('/')


def base(path):
    """The file's name: 'a/b/run.v2' and 'a\\b\\run.v2' -> 'run.v2'."""
    return posixpath.basename(_norm(path))


def parent(path):
    """The name of the folder holding it ('' at the top)."""
    return posixpath.basename(posixpath.dirname(_norm(path)))


def short(path):
    """'<folder><sep><name>' as the plot-file lists show it, with the path's
    own separator ('\\' when it has one, else '/')."""
    sep = '\\' if '\\' in str(path) else '/'
    p = parent(path)
    return p + sep + base(path) if p else base(path)


def ext(path):
    """Extension in lower case, with its dot: 'x_0001.TIF' -> '.tif'."""
    return posixpath.splitext(base(path))[1].lower()


def stem(path):
    """The name without its last extension: 'run.v2_SCAN-6_00001.tif' ->
    'run.v2_SCAN-6_00001'."""
    return posixpath.splitext(base(path))[0]
