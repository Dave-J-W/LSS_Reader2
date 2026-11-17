"""Replacement for ``scipy.interpolate.interp2d(x, y, z, kind='linear')``.

SciPy removed ``interp2d`` in version 1.14. The GID patching code used it
to resample one detector strip onto another strip's grid, so on a current
SciPy the patch could not run at all.

``interp2d_linear`` reproduces what ``interp2d`` did for the way this
program calls it (regular grid, linear, default bounds handling), including
its quirks, so that results are unchanged:

* ``z`` has shape ``(len(y), len(x))``;
* ``x`` and ``y`` may be given in any order (they are sorted, with ``z``);
* the points asked for are **sorted** before evaluation, and the result is
  returned for the sorted points, shape ``(len(ynew), len(xnew))``;
* points outside the grid take the value at the nearest edge;
* a result with a single row is returned as a 1-D array.

Checked against the real ``interp2d`` under SciPy 1.13 in
``tests/test_interp_compat.py``.
"""
import numpy as np
from scipy.interpolate import RectBivariateSpline


def interp2d_linear(x, y, z):
    """Return ``f(xnew, ynew)`` behaving like linear ``interp2d(x, y, z)``."""
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    z = np.asarray(z, dtype=float)
    if z.ndim == 1:
        z = z.reshape(len(y), len(x))
    if z.shape != (len(y), len(x)):
        raise ValueError('z must have shape (len(y), len(x)) = (%d, %d), got %s'
                         % (len(y), len(x), z.shape))
    if np.any(x[1:] < x[:-1]):
        order = np.argsort(x, kind='mergesort')
        x, z = x[order], z[:, order]
    if np.any(y[1:] < y[:-1]):
        order = np.argsort(y, kind='mergesort')
        y, z = y[order], z[order, :]
    spline = RectBivariateSpline(x, y, z.T, kx=1, ky=1, s=0)

    def evaluate(xnew, ynew):
        xs = np.sort(np.atleast_1d(np.asarray(xnew, dtype=float)).ravel())
        ys = np.sort(np.atleast_1d(np.asarray(ynew, dtype=float)).ravel())
        out = np.atleast_2d(spline(xs, ys, grid=True)).T
        if len(out) == 1:
            out = out[0]
        return np.array(out)

    return evaluate
