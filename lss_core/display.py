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


# ---------------------------------------------------------------- saturation cue (F97)

# Owner, 2026-11-23 (Q-IMG-10): per pixel, a soft limit at 1e5 counts per second
# and a hard one at 1.5e5 counts per second, above which an absorber is needed.
# Counts per second = the frame's raw counts over its counting time (the SPEC
# 'Seconds' of its point). Not checked against the detector's own count-rate
# correction (whether the counts written are corrected is not known here).
SOFT_CPS = 1.0e5
HARD_CPS = 1.5e5
SOFT_RGBA = (1.0, 0.85, 0.0, 0.85)       # amber: near the limit
HARD_RGBA = (1.0, 0.0, 0.0, 0.95)        # red: an absorber is needed


def saturation(counts, seconds, soft=SOFT_CPS, hard=HARD_CPS):
    """(above soft, above hard, highest cps) for a frame of raw ``counts``
    counted for ``seconds``; (None, None, None) when the time is not known
    or not positive. 'Above soft' includes the pixels above hard."""
    try:
        t = float(seconds)
    except (TypeError, ValueError):
        return None, None, None
    if not np.isfinite(t) or t <= 0:
        return None, None, None
    cps = np.asarray(counts, dtype=float) / t
    finite = np.where(np.isfinite(cps), cps, 0.0)
    return finite > soft, finite > hard, float(finite.max()) if finite.size else 0.0


def saturation_rgba(above_soft, above_hard):
    """An RGBA overlay: clear, amber where above the soft limit, red where above the hard one."""
    out = np.zeros(np.shape(above_soft) + (4,), dtype=float)
    out[np.asarray(above_soft, bool)] = SOFT_RGBA
    out[np.asarray(above_hard, bool)] = HARD_RGBA
    return out


def saturation_text(n_soft, n_hard):
    """The short note for a frame's title ('' when nothing is above the soft limit)."""
    if n_hard:
        return '%d px > %s cps: absorber needed' % (n_hard, _short(HARD_CPS))
    if n_soft:
        return '%d px > %s cps' % (n_soft, _short(SOFT_CPS))
    return ''


def _short(v):
    """1.5e5 for 150000, 1e5 for 100000."""
    m, e = ('%.2g' % v).split('e')
    return '%se%d' % (m, int(e))


# ---------------------------------------------------------------- the reflectivity ROI close-up (F71)

# image_display.md §2.4 R1-R6. Owner, 2026-11-23: Q-IMG-7, "a side panel, always
# visible beside the frame, the same for both tabs"; its second half, the cue
# thresholds as proposed (display only); Q-IMG-16, one panel with the box moved to
# the found peak and the old box dashed; F71 on the zoom: "not too close, we do want
# to see the diffuse scattering around it, and the background zones to the sides.
# But still a healthy zoom".

ROI_KINDS = ('ref', 'burn-ref', 'direct')     # frames whose ROI sum is a reduction (Ref Patch, burn)

OFF_CENTRE_FRACTION = 0.25     # Q-IMG-7: the peak more than 25 % of the half-width from the box centre
CLIPPED_FRACTION = 0.01        # Q-IMG-7: more than 1 % of the integral on or beyond the box edge
BG_GAP_PX = 2                  # Q-IMG-7: a background box within 2 px of the signal box
# Assumptions, not settled by the owner's answers (display only; measured on NX school
# scans 6-9, physics_notes 2026-11-24):
# - the position and clipping cues are judged only on a peak of net > 3 sigma (a box of
#   noise has a random centroid);
# - "beyond the box edge" is the CLIP_NEAR_PX pixels just past it: intensity farther out
#   is not the beam's tail (on NX: the direct beam 6 rows below the box at Qz 0.0175);
# - the baseline of a profile is the background boxes' level along the background
#   direction (what netROI subtracts) and, across it, where no box measures it, the
#   profile's own median from CLIP_NEAR_PX + 1 to one box size beyond the edges: on NX
#   the specular column carries a diffuse ridge above the side boxes' level, which with
#   their level flagged 87 of the 96 frames, with the local one 27 (Qz 0.024-0.03, most
#   of Qz >= 0.3, where the box cuts the broad base of the specular peak);
# - the part on or beyond the edge must also exceed 2 sigma of its counting error, so
#   that the noise of a weak frame does not flag it.
PEAK_SIGMAS = 3.0
CLIP_SIGMAS = 2.0
CLIP_NEAR_PX = 2
ROI_MARGIN_MIN = 5             # pixels: the close-up's smallest margin around the boxes (assumption)


def roi_boxes(slit, cen, bg=None, direction='H'):
    """The boxes ``TwoDDetector.sumROI`` sums, by its arithmetic exactly:
    ``[(name, (r0, r1, c0, c1)), ...]``, rows ``r0:r1`` and columns
    ``c0:c1`` as numpy slices (stop excluded; a negative start is read by
    numpy from the far end, as in sumROI). The signal box first, then the
    background boxes in sumROI's order: 'left', 'right' (lower, higher
    column) for ``direction`` 'H'; 'up', 'down' (higher, lower row) for
    anything else, since sumROI tests ``dir == 'H'``.

    ``slit`` = (horizontal, vertical) as typed (Slit(H,V)); sumROI uses
    slit − 2 in both (PHYSICS_ISSUES P12), a box of 2·((s − 1)//2) + 1
    pixels: s for an odd s, s − 1 for an even one. ``cen`` = (column, row).
    ``bg``: the background offset in units of the typed slit (the window's
    degrees × distance / pixel / slit); sumROI puts the background centres
    at int(centre ± bg × (slit − 2)), truncated towards zero, so they sit
    closer than the typed offset (NX school, slit 21, 0.5°: 25.3 px, not
    28.0). ValueError for a slit below 1, where sumROI raises IndexError."""
    s_rows = slit[1] - 2
    s_cols = slit[0] - 2
    row, col = cen[1], cen[0]

    def box(r, c):
        x = range(c - (s_cols + 1) // 2, c + (s_cols + 1) // 2 + 1)
        y = range(r - (s_rows + 1) // 2, r + (s_rows + 1) // 2 + 1)
        if len(x) == 0 or len(y) == 0:
            raise ValueError('slit %r gives an empty box' % (tuple(slit),))
        return int(y[0]), int(y[-1] + 1), int(x[0]), int(x[-1] + 1)

    out = [('signal', box(row, col))]
    if bg is not None:
        if direction == 'H':
            left = list(map(int, [row, col - bg * s_cols]))
            right = list(map(int, [row, col + bg * s_cols]))
            out += [('left', box(*left)), ('right', box(*right))]
        else:
            up = list(map(int, [row + bg * s_rows, col]))
            down = list(map(int, [row - bg * s_rows, col]))
            out += [('up', box(*up)), ('down', box(*down))]
    return out


def box_on_frame(box, shape):
    """The pixels numpy sums for ``box`` on a frame of ``shape``: (r0, r1,
    c0, c1) as numpy reads the slices, or None when that is nothing. A box
    past the far edge loses the part outside; a box that starts before the
    first row or column is read from the far end (negative indices), which
    for these boxes is nothing at all."""
    r0, r1, _ = slice(box[0], box[1]).indices(shape[0])
    c0, c1, _ = slice(box[2], box[3]).indices(shape[1])
    if r1 <= r0 or c1 <= c0:
        return None
    return r0, r1, c0, c1


def box_leaves_frame(box, shape):
    """True when ``box`` (as roi_boxes gives it) is not wholly on the frame."""
    return box[0] < 0 or box[2] < 0 or box[1] > shape[0] or box[3] > shape[1]


def box_sum(image, box):
    """The sum sumROI makes over ``box``: the same slices of the same array."""
    return np.sum(image[box[0]:box[1], box[2]:box[3]])


def roi_region(boxes, shape, direction='H'):
    """(r0, r1, c0, c1) shown by the close-up: every box on the frame, with
    a margin of one signal-box size across the background direction (the
    diffuse scattering above and below a row of boxes) and half a box along
    it (beyond the outer background boxes), at least ``ROI_MARGIN_MIN``
    pixels, clipped to the frame. None when no box is on the frame. Owner,
    F71: "not too close ... But still a healthy zoom"; the margins are an
    assumption (display only)."""
    on = [box_on_frame(b, shape) for _, b in boxes]
    on = [b for b in on if b is not None]
    if not on:
        return None
    sig = boxes[0][1]
    h, w = sig[1] - sig[0], sig[3] - sig[2]
    if len(boxes) == 1:
        mr, mc = h, w
    elif direction == 'H':
        mr, mc = h, w // 2
    else:
        mr, mc = h // 2, w
    mr, mc = max(mr, ROI_MARGIN_MIN), max(mc, ROI_MARGIN_MIN)
    r0 = max(min(b[0] for b in on) - mr, 0)
    r1 = min(max(b[1] for b in on) + mr, shape[0])
    c0 = max(min(b[2] for b in on) - mc, 0)
    c1 = min(max(b[3] for b in on) + mc, shape[1])
    return r0, r1, c0, c1


def roi_profiles(image, boxes, region):
    """The close-up's two profiles over ``region`` (R3): (columns, each
    column summed over the signal box's rows; rows, each row summed over
    its columns). None when the signal box is not on the frame."""
    a = np.asarray(image, dtype=float)
    sig = box_on_frame(boxes[0][1], a.shape)
    if sig is None or region is None:
        return None
    r0, r1, c0, c1 = region
    colsum = a[sig[0]:sig[1], c0:c1].sum(axis=0)
    rowsum = a[r0:r1, sig[2]:sig[3]].sum(axis=1)
    return np.arange(c0, c1), colsum, np.arange(r0, r1), rowsum


def roi_limits(image, boxes, region, log):
    """(vmin, vmax) of the close-up, its own scale (R1): the top at the
    ``TOP_PERCENTILE`` of the signal box, the bottom at the
    ``BOTTOM_PERCENTILE`` of the region (of its positive pixels on a log
    scale, so that single counts show). Always drawable (safe_limits)."""
    a = np.asarray(image, dtype=float)
    if region is None:
        return safe_limits(0.1, 1.0, log)
    r0, r1, c0, c1 = region
    lo, hi = robust_limits([a[r0:r1, c0:c1]], log)
    top = hi
    sig = box_on_frame(boxes[0][1], a.shape)
    if sig is not None:
        v = a[sig[0]:sig[1], sig[2]:sig[3]]
        v = v[np.isfinite(v)]
        if v.size:
            top = float(np.percentile(v, TOP_PERCENTILE))
    if not top > lo:
        top = hi
    return safe_limits(lo, top, log)


def _box_mask(box, shape):
    m = np.zeros(shape, dtype=bool)
    on = box_on_frame(box, shape)
    if on is not None:
        m[on[0]:on[1], on[2]:on[3]] = True
    return m


def roi_cues(image, error, boxes, sums=None, direction='H', beam=None, saturated=None, kind='ref'):
    """The close-up's cues (R5): a list of dicts with key, text (short, on
    the panel), reason (its tooltip, rule 9) and level ('warn' or 'stop').
    Display only: nothing here changes a sum.

    ``image``, ``error``: the frame the boxes were summed from and its
    errors, in the same units; ``boxes``: roi_boxes; ``sums``: (signal, its
    error, background 1, its error, background 2, its error, net, its
    error) from sumROI and netROI, or None; ``beam``: (row, column) of the
    direct beam on this frame, or None; ``saturated``: (above the soft
    limit, above the hard limit) boolean frames (``saturation``), or None;
    ``kind``: the frame's display kind (no direct-beam cue on a direct-beam
    frame, whose beam is the point).

    Thresholds (owner, Q-IMG-7, 2026-11-23): off centre beyond
    ``OFF_CENTRE_FRACTION`` of the half-width; clipped when more than
    ``CLIPPED_FRACTION`` of the integral lies on or beyond the box edge; a
    background box ``BG_GAP_PX`` pixels or fewer from the signal box."""
    a = np.asarray(image, dtype=float)
    e = None if error is None else np.asarray(error, dtype=float)
    shape = a.shape
    cues = []
    for name, b in boxes:
        if box_leaves_frame(b, shape):
            on = box_on_frame(b, shape)
            what = ('only the part on the frame is summed' if on is not None and b[0] >= 0 and b[2] >= 0 else
                    'and none of it is summed: numpy reads a slice that starts before the first pixel from '
                    'the far end, so this box\'s sum is 0 (or that of another region)')
            cues.append({'key': 'frame', 'level': 'stop', 'text': '%s box off frame' % name,
                         'reason': 'The %s box (rows %d–%d, columns %d–%d) runs past the frame (rows 0–%d, '
                                   'columns 0–%d): %s.' % (name, b[0], b[1] - 1, b[2], b[3] - 1, shape[0] - 1,
                                                           shape[1] - 1, what)})
    sig_nom = boxes[0][1]
    bgs = list(boxes[1:])
    for name, b in bgs:            # pixels strictly between a background box and the signal box
        if direction == 'H':
            gap = max(b[2] - sig_nom[3], sig_nom[2] - b[3])
        else:
            gap = max(b[0] - sig_nom[1], sig_nom[0] - b[1])
        if gap <= BG_GAP_PX:
            cues.append({'key': 'gap', 'level': 'warn',
                         'text': '%s bg overlaps signal' % name if gap < 0 else '%s bg %d px from signal' % (name, gap),
                         'reason': 'The %s background box is %s the signal box: it may hold the tails of the '
                                   'reflected beam, which netROI then subtracts as background. Shown when %d '
                                   'or fewer pixels lie between the boxes (owner, Q-IMG-7).'
                                   % (name, 'overlapping' if gap < 0 else '%d px from' % gap, BG_GAP_PX)})
    sig = box_on_frame(sig_nom, shape)
    if sig is not None:
        n_sig = (sig[1] - sig[0]) * (sig[3] - sig[2])
        bsum = 0.0
        for _, b in bgs:
            on = box_on_frame(b, shape)
            if on is not None:
                bsum += float(np.sum(a[on[0]:on[1], on[2]:on[3]]))
        level = bsum / 2.0 / n_sig if bgs else 0.0      # per pixel, as netROI subtracts (B1 + B2)/2
        significant = True
        if sums is not None:
            net, neterr = float(sums[6]), float(sums[7])
            significant = bool(np.isfinite(net) and np.isfinite(neterr) and net > PEAK_SIGMAS * neterr)
        if significant:
            cues += _position_cues(a, e, sig, sig_nom, bgs, level, direction)
    cues += _saturation_cues(boxes, shape, saturated)
    if beam is not None and kind != 'direct':
        cues += _beam_cues(boxes, shape, beam)
    return cues


def _position_cues(a, e, sig, sig_nom, bgs, level, direction):
    """Off centre and clipped, along the columns and along the rows. The
    baseline of each profile: the background boxes' level per pixel
    (``level``, what netROI subtracts) along the background direction;
    across it, the profile's own median beyond the near pixels (see
    CLIP_NEAR_PX)."""
    shape = a.shape
    out = []
    bgmask = np.zeros(shape, dtype=bool)
    for _, b in bgs:
        bgmask |= _box_mask(b, shape)
    for axis, label in ((1, 'columns'), (0, 'rows')):
        lo, hi = (sig_nom[2], sig_nom[3]) if axis == 1 else (sig_nom[0], sig_nom[1])
        a0, a1 = (sig[0], sig[1]) if axis == 1 else (sig[2], sig[3])
        size = hi - lo
        w0, w1 = max(lo - size, 0), min(hi + size, shape[axis])
        if w1 <= w0:
            continue
        idx = np.arange(w0, w1)
        if axis == 1:
            block, eblock = a[a0:a1, w0:w1], None if e is None else e[a0:a1, w0:w1]
            excluded = bgmask[a0:a1, w0:w1].any(axis=0)
        else:
            block, eblock = a[w0:w1, a0:a1].T, None if e is None else e[w0:w1, a0:a1].T
            excluded = bgmask[w0:w1, a0:a1].any(axis=1)
        prof = block.sum(axis=0)
        inside = (idx >= lo) & (idx < hi)
        if not inside.any():
            continue
        near = ~inside & (idx >= lo - CLIP_NEAR_PX) & (idx < hi + CLIP_NEAR_PX) & ~excluded
        outer = ~inside & ~near & ~excluded
        along = bool(bgs) and ((axis == 1) == (direction == 'H'))
        if along:
            base, how = level * (a1 - a0), "the background boxes' level"
        elif outer.any():
            base = float(np.median(prof[outer]))
            how = "the profile's median %d to %d px beyond the edges" % (CLIP_NEAR_PX + 1, size)
        else:
            base, how = 0.0, 'zero'
        net = prof - base
        # off centre: the centroid of the net profile inside the box, negative parts left out
        wts = np.clip(np.where(inside, net, 0.0), 0.0, None)
        if wts.sum() > 0:
            centroid = float(np.sum(idx * wts) / np.sum(wts))
            centre = (lo + hi - 1) / 2.0
            off = centroid - centre
            if abs(off) > OFF_CENTRE_FRACTION * size / 2.0:
                peak = int(idx[inside][np.argmax(net[inside])])
                out.append({'key': 'centre', 'level': 'warn',
                            'text': 'off centre %+.1f px (%s)' % (off, 'col' if axis == 1 else 'row'),
                            'reason': 'Along the %s the centroid of the peak (inside the signal box, above %s) '
                                      'is at %.1f, %+.1f px from the box centre %.1f; shown beyond %d %% of the '
                                      'half-width, %.1f px (owner, Q-IMG-7). Brightest %s: %d.'
                                      % (label, how, centroid, off, centre, round(100 * OFF_CENTRE_FRACTION),
                                         OFF_CENTRE_FRACTION * size / 2.0, label[:-1], peak)})
        # clipped: the intensity above the baseline on the box's two edge pixels and the near pixels past them
        edge = (idx == lo) | (idx == hi - 1) | near
        total = float(np.sum(net[inside | near]))
        if not total > 0:
            continue
        on_edge = float(np.sum(net[edge]))
        frac = on_edge / total
        sigma = 0.0 if eblock is None else float(np.sqrt(np.sum(eblock[:, edge] ** 2)))
        if frac > CLIPPED_FRACTION and on_edge > CLIP_SIGMAS * sigma:
            out.append({'key': 'clipped', 'level': 'warn',
                        'text': 'clipped %.1f %% (%s)' % (100 * frac, label),
                        'reason': "%.1f %% of the intensity along the %s (above %s) lies on the signal box's "
                                  "edge pixels or on the %d px just past them: the box may cut the beam's tails "
                                  "(or a broad base under the peak). Shown above %g %% (owner, Q-IMG-7) when that "
                                  "part is also above %g σ of its counting error (%.3g ± %.2g). The typed slit "
                                  "is summed 2 px smaller (P12). How 'beyond' and the baseline are taken is an "
                                  "assumption (lss_core.display)."
                                  % (100 * frac, label, how, CLIP_NEAR_PX, 100 * CLIPPED_FRACTION, CLIP_SIGMAS,
                                     on_edge, sigma)})
    return out


def _saturation_cues(boxes, shape, saturated):
    if saturated is None or saturated[0] is None:
        return []
    soft, hard = np.asarray(saturated[0], bool), np.asarray(saturated[1], bool)
    if soft.shape != tuple(shape):
        return []
    inbox = np.zeros(shape, dtype=bool)
    for _, b in boxes:
        inbox |= _box_mask(b, shape)
    n_soft, n_hard = int((soft & inbox).sum()), int((hard & inbox).sum())
    if not n_soft:
        return []
    return [{'key': 'saturation', 'level': 'stop' if n_hard else 'warn',
             'text': saturation_text(n_soft, n_hard),
             'reason': '%d pixel(s) of the boxes above %s counts per second, %d above %s, where an absorber '
                       'is needed (owner, Q-IMG-10; raw counts over the point\'s counting time, F97). Marked '
                       'with squares on the close-up.' % (n_soft, _short(SOFT_CPS), n_hard, _short(HARD_CPS))}]


def _beam_cues(boxes, shape, beam):
    try:
        row, col = float(beam[0]), float(beam[1])
    except (TypeError, ValueError, IndexError):
        return []
    if not (np.isfinite(row) and np.isfinite(col)):
        return []
    r, c = int(round(row)), int(round(col))
    out = []
    for name, b in boxes:
        on = box_on_frame(b, shape)
        if on is None:
            continue
        if (r - BEAM_HALF[0] < on[1] and r + BEAM_HALF[0] + 1 > on[0] and
                c - BEAM_HALF[1] < on[3] and c + BEAM_HALF[1] + 1 > on[2]):
            out.append({'key': 'beam', 'level': 'warn', 'text': 'direct beam in %s box' % name,
                        'reason': 'The direct beam is expected at row %.1f, column %.1f of this frame (the '
                                  'reader\'s geometry, direct_beam_pixel); its box (±%d rows, ±%d columns, the '
                                  'one left out of the colour scale) overlaps the %s box, whose sum then holds '
                                  'direct-beam counts. Marked × on the close-up.'
                                  % (row, col, BEAM_HALF[0], BEAM_HALF[1], name)})
    return out


def roi_numbers_text(sums):
    """The panel's numbers (R4), short: signal ± σ, the two backgrounds,
    net ± σ and σ in per cent, as sumROI and netROI give them (``sums`` as
    in roi_cues)."""
    sig, sigerr, b1, _, b2, _, net, neterr = [float(v) for v in sums]
    pct = '%.2g %%' % (100.0 * neterr / net) if net != 0 and np.isfinite(net) else '–'
    return 'S %.3e ± %.1e   B %.2e | %.2e\nnet %.4e ± %.2e (%s)' % (sig, sigerr, b1, b2, net, neterr, pct)


def roi_cues_text(cues):
    """The short cue texts on one line ('' when there is none)."""
    return ' · '.join(c['text'] for c in cues)
