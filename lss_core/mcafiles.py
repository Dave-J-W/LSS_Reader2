"""Reading MCA files through the memory cache (2026-11-23).

The window read every selected scan's MCA file again on each change of the
scan selection, so adding one scan to a series re-parsed the whole series
(about 1 ms per spectrum, more over a network drive, which the disk cache
does not cover for MCA files). ``read_mca`` parses a file once per version:
it shares the image cache (``lss_core.images.CACHE``: one budget for the
data of both, keyed by path, size and modification time, so a file still
being written is read again). Callers get copies and may change them.
"""
import numpy as np

from .images import CACHE


def _nbytes(v):
    """Memory held, roughly: arrays by their size, lists and dicts by their
    items (a Python number in a list costs about 36 bytes; the spectra are
    lists of 2048 ints)."""
    if isinstance(v, np.ndarray):
        return v.nbytes
    if isinstance(v, dict):
        return 64 + sum(_nbytes(x) for x in v.values())
    if isinstance(v, (list, tuple)):
        if v and not isinstance(v[0], (dict, list, tuple, np.ndarray)):
            return 56 + 36 * len(v)
        return 56 + sum(_nbytes(x) for x in v)
    return 36


def _copy(v):
    """A copy deep enough that a caller's changes never reach the cache:
    dicts and lists rebuilt, arrays copied; numbers and strings shared
    (immutable). Several times faster than copy.deepcopy here."""
    if isinstance(v, dict):
        return {k: _copy(x) for k, x in v.items()}
    if isinstance(v, np.ndarray):
        return v.copy()
    if isinstance(v, list):
        if v and not isinstance(v[0], (dict, list, tuple, np.ndarray)):
            return list(v)                       # numbers (a spectrum): a shallow copy is enough
        return [_copy(x) for x in v]
    if isinstance(v, tuple):
        return tuple(_copy(x) for x in v)
    return v


def read_mca(path, beamline='APS-15IDC', cache=True):
    """``(Data, Par)`` of ``mca_routines.mcaread`` for ``path``, as copies."""
    from mca_routines import mcaread

    def load(p):
        r = mcaread(p, beamline=beamline)
        return (r.Data, r.Par)
    if not cache:
        return load(path)
    data, par = CACHE.get_or_load(path, load, _nbytes)
    return _copy(data), _copy(par)
