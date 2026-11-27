"""Qz shifts from where the reflection lands on the Pilatus: F42's relative
route (issue #148; the owner's answers, docs/notes/2026-11-27-qoff-from-
detector-owner-answers.md).

The owner (F42): "When the reflection is not at its normal height on the
camera, the Q_z offset is calculated. The normal position can be found from
the sh-scan (sample-height scan) images that always precede a reflectivity
experiment." Both routes were meant (2026-11-27); this module is the
relative one.

**What is measured.** The detector arm follows the reflection, so a
reflection that leaves at the set angle lands on the same detector row at
every Qz. Each frame's reflected row is found to a fraction of a pixel
(``reflection_row``: a Gaussian plus a constant fitted to the row profile,
summed over the columns about the expected beam). The reference is the row
on the plateau of a sample-height scan (``sh_reference``), taken at the
alignment angle. A row Δ pixels from it means the reflection left at
Δβ = Δ · pixel / D from where the arm expected it (D the sample-detector
distance, S2D_Dist; pixel 0.172 mm).

**What it means.** The owner: a change of row is "usually surface tilt or
curvature". A surface tilted by τ changes the incidence by τ and moves the
reflection by 2τ, so δα = Δβ / 2 (``reading='tilt'``, the default). An error
in the incident angle δ moves it by δ itself (``reading='incident'``,
δα = Δβ). Either way δQz = (4π/λ) cos α · δα: Qz + δQz is where the point
was really measured.

**What it cannot see.** An offset already present at the alignment angle:
the reference is taken there, so the shift at the sh scan's own angle is
zero by construction. That is the absolute route's job (the direct beam
against the reflection in the sh scans, which needs the distance from what
forms the spot to the detector; open, issue #174).

**Sign.** A larger row index is a larger exit angle when the direct beam
lies at smaller row indices than the reflection, as on the NX school
Pilatus (direct beam row 42.4, reflection 53.0). ``direction`` is found from
the sh scan when both beams show (``sh_reference``), else +1.

Nothing here changes a reduced number: ``relative_shifts`` reports, and the
user decides (rule 12 is paused, but a default that moves Qz is the owner's).
"""
import math
from dataclasses import dataclass, field

import numpy as np

from lss_core import images, peaks

ROW_HALF = 6          # rows fitted on each side of the expected reflection row
COL_HALF = 7          # columns summed on each side of the expected beam column
PLATEAU = 0.8         # sh-scan frames within this fraction of the scan's maximum (per monitor) are the plateau
DIRECT_MIN_PX = 3.0   # the direct beam is told from the reflection only when at least this far from it


@dataclass
class Row:
    """A spot's row on the detector: centre and its error (pixels), width
    (σ, pixels), the counts in the fit and whether the fit worked."""
    row: float = math.nan
    error: float = math.nan
    sigma: float = math.nan
    counts: float = 0.0
    ok: bool = False


def expected_pixel(image, beam_xy):
    """(column, row) of the expected beam from the header's (X, Y), as
    reflectivity.frame_row places it."""
    return int(image.shape[1] - beam_xy[0] - 1), int(beam_xy[1])


def reflection_row(image, beam_xy, row=None, row_half=ROW_HALF, col_half=COL_HALF):
    """The reflected spot's row in ``image``: a Gaussian plus a constant
    fitted to the row profile summed over ``col_half`` columns either side of
    the expected column, within ``row_half`` rows of ``row`` (default the
    header's Y), weighted by √(N + 1). A failed or degenerate fit gives
    ``ok`` False."""
    from scipy.optimize import curve_fit
    img = np.asarray(image, float)
    c0, r0 = expected_pixel(img, beam_xy)
    r0 = int(round(r0 if row is None else row))
    lo, hi = max(r0 - row_half, 0), min(r0 + row_half + 1, img.shape[0])
    cl, ch = max(c0 - col_half, 0), min(c0 + col_half + 1, img.shape[1])
    prof = np.clip(img[lo:hi, cl:ch], 0, None).sum(axis=1)
    r = np.arange(lo, hi, dtype=float)
    if prof.size < 5 or prof.max() <= 0:
        return Row(counts=float(prof.sum()) if prof.size else 0.0)

    def g(x, a, m, s, b):
        return a * np.exp(-0.5 * ((x - m) / s) ** 2) + b

    k = int(np.argmax(prof))
    try:
        p, cov = curve_fit(g, r, prof, p0=[prof[k] - np.median(prof), r[k], 0.5, float(np.median(prof))],
                           sigma=np.sqrt(prof + 1.0), absolute_sigma=True,
                           bounds=([0, lo, 0.1, -np.inf], [np.inf, hi - 1, row_half, np.inf]), maxfev=20000)
    except (RuntimeError, ValueError):
        return Row(counts=float(prof.sum()))
    e = float(math.sqrt(cov[1, 1])) if np.isfinite(cov[1, 1]) else math.nan
    ok = bool(np.isfinite(p[1]) and np.isfinite(e) and e < 1.0 and lo < p[1] < hi - 1)
    return Row(float(p[1]), e, float(abs(p[2])), float(prof.sum()), ok)


@dataclass
class Reference:
    """The reflection's row on a sample-height scan's plateau: the weighted
    mean of the plateau frames' rows, its error (their scatter / √n, or the
    fit errors' when larger), the frames used, the direct beam's row where
    it shows, and the direction (+1: a larger row is a larger exit angle)."""
    scan: int
    row: float = math.nan
    error: float = math.nan
    frames: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    direct_row: float = math.nan
    direction: int = 1
    alpha_deg: float = math.nan       # the sh scan's incident angle (from its L and the wavelength)
    notes: list = field(default_factory=list)


def sh_reference(exp, scan, counter='Pilatus', monitor='Monc', plateau=PLATEAU):
    """The reference row from sample-height scan ``scan`` of ``exp``
    (lss_core.experiment.Experiment): the frames whose ``counter`` per
    ``monitor`` is within ``plateau`` of the scan's maximum, each fitted by
    ``reflection_row``. The direct beam's row is looked for in the scan's
    first frame (lowest sample, where the beam passes over the surface) to
    set the direction."""
    sc = exp.scans[scan]
    if not peaks.is_height_scan(sc.command):
        raise ValueError('scan %d is not a sample-height scan (%s)' % (scan, sc.command.strip()))
    frames = exp.frames([scan])
    if not frames:
        raise ValueError('scan %d has no Pilatus frames' % scan)
    out = Reference(scan)
    cols = sc.columns
    y = np.asarray(cols[counter], float) / np.asarray(cols[monitor], float)
    keep = {j for j in range(len(y)) if np.isfinite(y[j]) and y[j] >= plateau * np.nanmax(y)}
    rows, errs = [], []
    for f in frames:
        if f.index not in keep:
            continue
        r = reflection_row(images.read_pilatus(f.path), f.beam_xy)
        if r.ok:
            out.frames.append(f.index)
            rows.append(r.row)
            errs.append(r.error)
    out.rows = rows
    if not rows:
        out.notes.append('no plateau frame gave a reflection row')
        return out
    w = 1 / np.square(errs)
    out.row = float(np.sum(w * rows) / np.sum(w))
    spread = float(np.std(rows, ddof=1) / math.sqrt(len(rows))) if len(rows) > 1 else math.nan
    out.error = float(np.nanmax([spread, 1 / math.sqrt(np.sum(w))]))
    wl = sc.parameters.get('Wavelength')
    if wl and 'L' in cols:
        out.alpha_deg = float(np.degrees(np.arcsin(float(np.median(cols['L'])) * wl / (4 * np.pi))))
    # the direct beam: the brightest row of the first frame, if it is clearly apart from the reflection
    first = images.read_pilatus(frames[0].path)
    c0, _ = expected_pixel(first, frames[0].beam_xy)
    prof = np.clip(np.asarray(first, float)[:, max(c0 - COL_HALF, 0):c0 + COL_HALF + 1], 0, None).sum(axis=1)
    lo = max(int(out.row) - 4 * ROW_HALF, 0)
    hi = min(int(out.row) + 4 * ROW_HALF + 1, prof.size)
    k = lo + int(np.argmax(prof[lo:hi]))
    if abs(k - out.row) >= DIRECT_MIN_PX:
        d = reflection_row(first, frames[0].beam_xy, row=k, row_half=2)
        out.direct_row = d.row if d.ok else float(k)
        out.direction = 1 if out.row > out.direct_row else -1
    else:
        out.notes.append('the direct beam does not show apart from the reflection; direction +1 assumed')
    return out


@dataclass
class Shifts:
    """Per reflectivity frame: scan, point, Qz, the reflected row and its
    error, Δβ (rad), δQz (Å⁻¹) and its error; with the reference, the
    reading ('tilt' or 'incident') and a summary."""
    reference: Reference
    reading: str
    table: np.ndarray            # columns: scan, point, qz, row, row_error, dbeta, dqz, dqz_error
    notes: list = field(default_factory=list)

    COLUMNS = ('scan', 'point', 'qz', 'row', 'row_error', 'dbeta_rad', 'dqz', 'dqz_error')

    def summary(self):
        """The median δQz and the range of δQz over the frames, in Å⁻¹."""
        d = self.table[:, 6]
        d = d[np.isfinite(d)]
        if not d.size:
            return 'no frame gave a reflection row'
        return ('δQz (%s reading): median %+.2g, range %+.2g to %+.2g Å⁻¹ over %d frames (reference: scan %d, '
                'row %.3f ± %.3f)' % (self.reading, np.median(d), d.min(), d.max(), d.size, self.reference.scan,
                                      self.reference.row, self.reference.error))


def relative_shifts(exp, scans, sh_scan, reading='tilt', reference=None):
    """δQz of every frame of the reflectivity ``scans`` of ``exp`` from its
    reflected row against the plateau row of sample-height scan ``sh_scan``
    (or a ``reference`` from ``sh_reference``). ``reading``: 'tilt' (the
    owner: usually surface tilt or curvature; δα = Δβ/2) or 'incident'
    (δα = Δβ). Reports; nothing is applied."""
    if reading not in ('tilt', 'incident'):
        raise ValueError("reading: 'tilt' or 'incident'")
    ref = sh_reference(exp, sh_scan) if reference is None else reference
    factor = 0.5 if reading == 'tilt' else 1.0
    rows = []
    for f in exp.frames(scans):
        wl = exp.scans[f.scan].parameters['Wavelength']
        r = reflection_row(images.read_pilatus(f.path), f.beam_xy, row=ref.row if np.isfinite(ref.row) else None)
        alpha = math.asin(min(f.qz * wl / (4 * math.pi), 1.0))
        k = 4 * math.pi / wl * math.cos(alpha) * factor * images.PIXEL_MM / f.distance * ref.direction
        if r.ok and np.isfinite(ref.row):
            d = r.row - ref.row
            de = math.hypot(r.error, ref.error)
            rows.append((f.scan, f.index, f.qz, r.row, r.error, ref.direction * d * images.PIXEL_MM / f.distance,
                         k * d, abs(k) * de))
        else:
            rows.append((f.scan, f.index, f.qz, math.nan, math.nan, math.nan, math.nan, math.nan))
    out = Shifts(ref, reading, np.array(rows, float).reshape(-1, 8))
    bad = int(np.sum(~np.isfinite(out.table[:, 6])))
    if bad:
        out.notes.append('%d frame(s) gave no reflection row' % bad)
    return out
