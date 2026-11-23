"""How detector frames are shown: kinds, scales, robust limits, sampling and
the movie's frame stepping (F69, F70, F88; docs/gui/image_display.md Part 2).

Display only: nothing here changes a reduced number. The window
(``MainWindow.updatePilPlotData``) draws what these functions choose; the
functions need neither Qt nor matplotlib, so they are tested on their own
(``tests/test_display.py``).

Owner's answers (docs/gui/questions.md, 2026-11-23):

- Q7 (Q-IMG-1): a movie whenever ``MOVIE_MIN_FRAMES`` (3) or more frames
  are selected; space pauses or plays; any arrow key pauses, then steps
  (up, back, left: backward in time; down, forward, right: forward).
- Q8 (Q-IMG-5, 6): log for reflectivity, GID and GISAXS frames, linear for
  direct beam and dark; the top of the scale at the 99.9th percentile with
  the direct beam masked; values per monitor, absorber-corrected (the
  window's ``pilFrameNormalised``).
- Q-IMG-4: one colour scale shared by the whole selection.
- Q-IMG-8, 14: nearest-pixel rendering, viridis by default, jet kept.
"""
import numpy as np

# ---------------------------------------------------------------- kinds and defaults

KINDS = ('ref', 'gid', 'gisaxs', 'burn-ref', 'burn-gid', 'direct', 'dark', 'other')

# Q8: log for the scattering frames, linear for the direct beam and dark frames.
# 'other' (a scan of no known series) is drawn as log too: an assumption (most
# frames in this reader are scattering frames), not settled by the owner.
DEFAULT_LOG = {'ref': True, 'gid': True, 'gisaxs': True, 'burn-ref': True, 'burn-gid': True,
               'direct': False, 'dark': False, 'other': True}

DEFAULT_CMAP = 'viridis'                                     # Q-IMG-14
CMAPS = ('viridis', 'magma', 'inferno', 'cividis', 'jet', 'gray', 'hot', 'summer', 'winter', 'rainbow')
INTERPOLATION = 'nearest'                                    # Q-IMG-8: pixels are data

TOP_PERCENTILE = 99.9                                        # Q8
BOTTOM_PERCENTILE = 1.0                                      # image_display.md C1

MOVIE_MIN_FRAMES = 3                                         # Q7
MAX_TILES = 6                                                # image_display.md §2.1
TILE_CHOICES = (4, 6)
SPEEDS_FPS = (0.5, 1.0, 2.0, 5.0, 10.0)
DEFAULT_FPS = 2.0

# Half-size (rows, columns) of the box masked around the direct beam when the
# top of the scale is chosen. Measured on NX school scan 7 frame 0 (Qz 0.035):
# the attenuated direct beam is above 1 % of its peak over rows 31-33 and
# columns 42-53, 2-3 rows by 6 columns from its centre; the box is a little
# larger. An assumption to revisit with a 1M detector or wider slits.
BEAM_HALF = (4, 8)

PIXEL_MM = 0.172                                             # Pilatus pixel


def kind_of(series_kind=None, dth_deg=None, monc=None, qz=None):
    """The display kind of a frame (image_display.md K1).

    ``series_kind``: the kind of the frame's scan series (lss_core.series
    KINDS, or None); ``dth_deg``: the detector angle Det_Th; ``monc``: the
    frame's monitor; ``qz``: its Qz. A frame with no monitor counts is dark;
    a burn test is GID above 2° Det_Th and reflectivity at or below it
    (lss_core.burn.is_gid, owner Q10/F87); a reflectivity frame at Qz 0 is
    the direct beam."""
    try:
        if monc is not None and not float(monc) > 0:
            return 'dark'
    except (TypeError, ValueError):
        pass
    k = (series_kind or '').lower()
    if k == 'burn':
        from lss_core import burn
        try:
            return 'burn-gid' if dth_deg is not None and burn.is_gid(dth_deg) else 'burn-ref'
        except (TypeError, ValueError):
            return 'burn-ref'
    if k == 'reflectivity':
        if qz is not None and abs(float(qz)) < 1e-4:
            return 'direct'
        return 'ref'
    if k in ('direct_beam', 'alignment'):           # an sh scan shows the direct beam being cut (assumption)
        return 'direct'
    if k in ('gid', 'gisaxs'):
        return k
    return 'other'


def default_log(kind):
    """Q8: True (log) or False (linear) for a display kind."""
    return DEFAULT_LOG.get(kind, True)


def units(background=False):
    """The colour bar's label (image_display.md C5)."""
    text = 'counts / Monc, absorber-corrected'
    return text + ', minus background' if background else text


# ---------------------------------------------------------------- the direct beam

def direct_beam_pixel(xcenter, ycenter, alpha, truealpha, dth, distance, pixel=PIXEL_MM):
    """(row, column) where the direct beam meets the detector.

    The reader's geometry (``MainWindow.updatePilPlotData``): the row
    ``ycenter`` sees the exit angle β0 = asin(2 sin α − sin α_in) and the
    column ``xcenter`` the angle Det_Th; one pixel is ``pixel``/``distance``
    rad. The direct beam leaves at β = −α_in and 2θ = 0. On NX school scan 7
    frame 0 this gives row 30.9, column 47 where the brightest pixel is at
    row 32, column 48 (measured 2026-11-23). Angles in radians."""
    beta0 = np.arcsin(2.0 * np.sin(alpha) - np.sin(truealpha))
    row = ycenter + (-truealpha - beta0) * distance / pixel
    col = xcenter - dth * distance / pixel
    return float(row), float(col)


def beam_mask(shape, row, col, half=BEAM_HALF):
    """Boolean mask (True: left out) of a box around (row, col); all False
    when the box is off the frame."""
    m = np.zeros(shape, dtype=bool)
    r, c = int(round(row)), int(round(col))
    r0, r1 = max(r - half[0], 0), min(r + half[0] + 1, shape[0])
    c0, c1 = max(c - half[1], 0), min(c + half[1] + 1, shape[1])
    if r0 < r1 and c0 < c1:
        m[r0:r1, c0:c1] = True
    return m


# ---------------------------------------------------------------- limits

def robust_limits(frames, log=False, masks=None, top=TOP_PERCENTILE, bottom=BOTTOM_PERCENTILE):
    """(vmin, vmax) shared by ``frames`` (a list of 2D arrays): pixels in
    ``masks`` (one boolean array per frame, or None) and non-finite pixels
    are left out.

    - vmax: the ``top`` percentile of what remains (Q8: 99.9th, with the
      direct beam masked);
    - vmin, linear: the ``bottom`` percentile (0 for counting data);
    - vmin, log: the ``bottom`` percentile of the positive pixels, so that
      zeros and bad-pixel markers (−1, −2) never reach the logarithm.

    Always vmin < vmax, both finite, and both positive when ``log``."""
    vals = []
    for k, f in enumerate(frames):
        a = np.asarray(f, dtype=float)
        keep = np.isfinite(a)
        if masks is not None and masks[k] is not None:
            keep &= ~np.asarray(masks[k], dtype=bool)
        vals.append(a[keep])
    v = np.concatenate(vals) if vals else np.zeros(0)
    if v.size == 0:
        return (0.1, 1.0) if log else (0.0, 1.0)
    vmax = float(np.percentile(v, top))
    pos = v[v > 0]
    if log:
        if pos.size == 0:
            return 0.1, 1.0
        vmin = float(np.percentile(pos, bottom))
        if not vmax > vmin:
            vmax = float(pos.max())
        if not vmax > vmin:
            vmin = vmax / 10.0
        return vmin, vmax
    vmin = float(np.percentile(v, bottom))
    if not vmax > vmin:
        vmax = float(v.max())
    if not vmax > vmin:
        vmax = vmin + (abs(vmin) if vmin != 0 else 1.0)
    return vmin, vmax


def data_range(frames):
    """(smallest positive, largest) finite value of ``frames``: the ends of
    the Min and Max sliders. (1, 10) when there is nothing positive."""
    hi, lo = -np.inf, np.inf
    for f in frames:
        a = np.asarray(f, dtype=float)
        a = a[np.isfinite(a)]
        if a.size:
            hi = max(hi, float(a.max()))
            p = a[a > 0]
            if p.size:
                lo = min(lo, float(p.min()))
    if not np.isfinite(lo) or not np.isfinite(hi) or not hi > lo:
        return (1.0, 10.0) if not np.isfinite(lo) else (lo, lo * 10.0)
    return lo, hi


def safe_limits(vmin, vmax, log):
    """Typed limits made drawable: on a log scale both positive (a
    non-positive Min is replaced by Max/1000; the NaN norm of
    image_display.md §1.2 cannot happen), and vmin < vmax."""
    vmin, vmax = float(vmin), float(vmax)
    if not (np.isfinite(vmin) and np.isfinite(vmax)):
        return (0.1, 1.0) if log else (0.0, 1.0)
    if vmin > vmax:
        vmin, vmax = vmax, vmin
    if log:
        if not vmax > 0:
            return 0.1, 1.0
        if not vmin > 0:
            vmin = vmax / 1000.0
    if not vmax > vmin:
        vmax = vmin * 10.0 if (log or vmin > 0) else vmin + 1.0
    return vmin, vmax


def slider_value(pos, lo, hi, log, steps=100):
    """The value at slider position ``pos`` (0..steps) between ``lo`` and
    ``hi``, evenly in log10 when ``log`` (both positive). Before
    2026-11-23 the slider gave pos × (hi − lo) / 100, without ``lo``."""
    f = min(max(float(pos) / steps, 0.0), 1.0)
    if log and lo > 0 and hi > 0:
        return float(10 ** (np.log10(lo) + f * (np.log10(hi) - np.log10(lo))))
    return float(lo + f * (hi - lo))


def slider_position(value, lo, hi, log, steps=100):
    """The inverse of ``slider_value``, rounded and kept in 0..steps."""
    if not hi > lo:
        return 0
    if log and lo > 0 and hi > 0:
        f = (np.log10(value) - np.log10(lo)) / (np.log10(hi) - np.log10(lo)) if value > 0 else 0.0
    else:
        f = (float(value) - lo) / (hi - lo)
    if not np.isfinite(f):
        return 0
    return int(round(min(max(f, 0.0), 1.0) * steps))


# ---------------------------------------------------------------- what is shown

def sample(n_sel, n):
    """Positions of the frames shown as ``n`` tiles out of ``n_sel`` selected:
    the first, evenly spaced middles and the last, ``round(linspace(0,
    n_sel−1, n))`` without duplicates (image_display.md §2.1; 41 frames,
    4 tiles: 0, 13, 27, 40). All of them when ``n`` ≥ ``n_sel``."""
    n_sel, n = int(n_sel), int(n)
    if n_sel <= 0 or n <= 0:
        return []
    if n >= n_sel:
        return list(range(n_sel))
    if n == 1:
        return [0]
    return sorted(set(int(round(x)) for x in np.linspace(0, n_sel - 1, n)))


def mode_for(n_sel, view='movie', summed=False):
    """'sum', 'movie' or 'tiles' for a selection of ``n_sel`` frames: the
    summed image when "Sum All" is on; a movie from ``MOVIE_MIN_FRAMES``
    frames when the view chosen is the movie (Q7); otherwise tiles."""
    if summed:
        return 'sum'
    if n_sel >= MOVIE_MIN_FRAMES and view == 'movie':
        return 'movie'
    return 'tiles'


def tiles_title(shown, n_sel):
    """'4 of 41 shown (sampled)' when fewer tiles than frames, else ''."""
    return '%d of %d shown (sampled)' % (shown, n_sel) if shown < n_sel else ''


def step(index, delta, n, loop=False):
    """The movie's next position: ``index + delta`` in 0..n−1, wrapped round
    when ``loop``, else held at the ends."""
    if n <= 0:
        return 0
    k = index + delta
    if loop:
        return k % n
    return min(max(k, 0), n - 1)


# Q7: keys, by name (the window maps Qt's key codes to these names)
KEY_STEPS = {'space': 'toggle', 'up': -1, 'back': -1, 'left': -1, 'down': 1, 'forward': 1, 'right': 1}


def key_action(name):
    """'toggle', −1, +1 or None for a key name (Q7)."""
    return KEY_STEPS.get(name)


# ---------------------------------------------------------------- zoom

def convert_limits(lim, old_extent, new_extent):
    """A view range ``lim`` = (a, b) in the axis of ``old_extent`` = (lo, hi)
    mapped to the same pixels in ``new_extent`` (the image's extent is linear
    in pixels in every Axes choice, so a zoom survives a change of Axes)."""
    (a, b), (o0, o1), (n0, n1) = lim, old_extent, new_extent
    if o1 == o0:
        return n0, n1
    f = lambda x: n0 + (x - o0) * (n1 - n0) / (o1 - o0)
    return f(a), f(b)


def frame_text(scan, point, kind, qz=None, tth_deg=None, t_s=None, absorber=None, monc=None):
    """The movie's metadata line (image_display.md M3): scan, point number,
    Qz (reflectivity kinds) or 2θ (GID kinds), time from the first frame
    shown, absorber and monitor."""
    parts = ['S# %s' % scan, 'pt %s' % point]
    gidlike = kind in ('gid', 'burn-gid')
    if qz is not None and (not gidlike or kind == 'other'):
        parts.append('Qz %.4f 1/Å' % qz)
    if tth_deg is not None and (gidlike or kind == 'other'):
        parts.append('2θ %.2f°' % tth_deg)
    if t_s is not None and np.isfinite(t_s):
        parts.append('t %.0f s' % t_s)
    if absorber is not None:
        parts.append('abs %s' % absorber)
    if monc is not None:
        parts.append('Monc %.3g' % monc)
    return ' · '.join(parts)
