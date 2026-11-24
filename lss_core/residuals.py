"""Weighted residuals and the small panel above a fit plot (F74).

Owner, 2026-11-22: "a small residuals plot above every plot that shows a
fit", in the style of fluorescence-decay fitting. The main plot keeps most
of the height and about 15 % shows the residuals on their own scale. The
legend carries χ²/dof. The panel can be hidden, and is hidden by default.

The residuals are weighted by the point errors, (y − fit)/σ, as in decay
fitting (Lakowicz, *Principles of Fluorescence Spectroscopy*, 3rd ed.,
Springer 2006, ch. 4; cited from memory, not rechecked). For a good fit
and right errors they scatter as N(0, 1), so ±2 holds about 95 % of the
points. The assumption stands until the owner says otherwise
(FEATURE_REQUESTS F74). Where a point's σ is missing or not positive,
plain residuals y − fit are drawn and the axis label says so.

Matplotlib only, no Qt: the window and scripts can use it alike.
"""
import numpy as np

# the panel's height as a fraction of the main axes': 0.18 of it is 15 % of the pair
SIZE = '18%'
PAD = 0.08          # inches between the panel and the main axes


def weighted(y, model, sigma=None):
    """(residuals, weighted): (y − model)/σ when every σ is finite and
    positive, else y − model (``weighted`` False)."""
    y = np.asarray(y, dtype=float)
    r = y - np.asarray(model, dtype=float)
    if sigma is not None:
        s = np.asarray(sigma, dtype=float) * np.ones_like(y)
        if len(s) and np.all(np.isfinite(s) & (s > 0)):
            return r / s, True
    return r, False


def chi2_label(label, chi2_dof):
    """The fit's legend label with χ²/dof, when it is known."""
    if chi2_dof is None or not np.isfinite(chi2_dof):
        return label
    return '%s, χ²/dof %.2f' % (label, chi2_dof)


def panel(ax, show):
    """The residual axes above ``ax`` when ``show`` (made once, emptied
    each call), else None, and any earlier panel removed so that ``ax``
    gets its full height back."""
    rax = getattr(ax, '_lss_residuals', None)
    if rax is not None and (not show or rax.figure is None or rax not in rax.figure.axes):
        try:
            rax.remove()
        except (ValueError, KeyError, AttributeError):
            pass
        ax.set_axes_locator(None)
        ax._lss_residuals = rax = None
    if not show:
        return None
    if rax is None:
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        rax = make_axes_locatable(ax).append_axes('top', size=SIZE, pad=PAD, sharex=ax)
        ax._lss_residuals = rax
    else:
        rax.clear()
    rax.tick_params(labelbottom=False, labelsize='small')
    return rax


def draw(rax, x, y, model, sigma=None, color=None, label=None):
    """Draw the residuals of one curve in the panel; returns the residuals."""
    r, w = weighted(y, model, sigma)
    if not rax.lines or not any(getattr(l, '_lss_zero', False) for l in rax.lines):
        zero = rax.axhline(0.0, color='0.5', lw=0.8)
        zero._lss_zero = True
    rax.plot(np.asarray(x, dtype=float), r, 'o', ms=3, color=color, label=label)
    if w:
        rax.set_ylabel('(y−fit)/σ', fontsize='small')
    elif not rax.get_ylabel():
        rax.set_ylabel('y−fit', fontsize='small')
    return r
