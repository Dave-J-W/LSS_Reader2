"""Reduced reflectivity scans (``synthetic.xrr_scans``) as a SPEC file and
Pilatus frames, so that the whole reader (``Experiment.reflectivity``, the
window's Ref Patch) can be run against a known curve.

Each frame holds the counts the reduced row was made from, placed where
the reader sums them (``lss_core.reflectivity.frame_row`` with the window's
defaults: slit 21 × 11, background offset 0.5° to both sides, 'H'):

* the signal box (21 columns × 11 rows around the direct-beam pixel of the
  SPEC header, column mirrored as the reader does: NCOLS − X − 1) holds
  exactly S_core counts in its 5 central rows and S_outer in the other 6;
  the reflected beam is a pixel-integrated Gaussian (σ 0.6 rows × 1.2
  columns, an assumption: the real beam is a few pixels) cut to the
  5 × 21 core, on the flat background;
* the two background boxes, at the columns the reader computes from the
  0.5° offset and S2D, hold exactly B1 and B2 (core and outer rows apart);
* every other pixel is Poisson(background per pixel), independent.

Drawn counts are spread over a box's pixels multinomially (in proportion
to the expected counts per pixel), so the box sums, hence the reader's net
value, are the reduced row's exactly (int32 TIFF, as the detector writes).
Data made with ``measure(..., expected=True)`` are written as float32
expected values instead (exact to float32 rounding, about 1e-7).

The reader's beam search (``peakLocate``: brightest pixel within ±3 of the
header position, then the centroid of a 5 × 5 box) must land on the
nominal pixel for the sums to match. It does whenever the reflected beam
stands well above the background in that box; on very weak frames noise
can move the box by a pixel, as on real data (``ReflectivityResult.
beam_offsets`` lists moves of more than 2 pixels). Other slits or offsets
in the window give other sums: the exact match holds for the defaults.
"""
import math
import os

import numpy as np
from PIL import Image
from scipy.special import erf

import synth
from . import xrr_scans

PIXEL_MM = 0.172               # as lss_core.reflectivity
SIGMA_ROW, SIGMA_COL = 0.6, 1.2
COLUMNS = ['H', 'K', 'L', 'Seconds', 'Monc', 'Monp', 'Pilatus']
SLIT = (21, 11)
BG_OFFSET_DEG = 0.5


def beam_pixel():
    """(column, row) of the direct beam in the reader's array (synth's header)."""
    return synth.PIL_H - synth.DB_X - 1, synth.DB_Y


def box_columns(distance=synth.S2D, slit=SLIT, bg_offset_deg=BG_OFFSET_DEG):
    """Centre columns (signal, left background, right background) as the
    reader's frame_row / sumROI compute them."""
    c, _ = beam_pixel()
    bg = bg_offset_deg * distance * math.pi / 180 / PIXEL_MM / slit[0]
    w = slit[0] - 2
    return c, int(c - bg * w), int(c + bg * w)


def _box(row, col):
    """Slices (core rows, outer rows) of a 21-column box centred at (row, col)."""
    half_c = (SLIT[0] - 2 + 1) // 2           # 10
    cols = slice(col - half_c, col + half_c + 1)
    hc = (xrr_scans.CORE_ROWS - 1) // 2      # 2
    ho = (xrr_scans.ROI_ROWS - 1) // 2       # 5
    core = (slice(row - hc, row + hc + 1), cols)
    outer = [(slice(row - ho, row - hc), cols), (slice(row + hc + 1, row + ho + 1), cols)]
    return core, outer


def peak_shape():
    """The reflected beam over the 5 × 21 core box, summing to 1."""
    hr, hc = (xrr_scans.CORE_ROWS - 1) // 2, (SLIT[0] - 2 + 1) // 2

    def pix(h, s):
        e = np.arange(-h, h + 2) - 0.5
        return np.diff(erf(e / (s * math.sqrt(2))))
    p = np.outer(pix(hr, SIGMA_ROW), pix(hc, SIGMA_COL))
    return p / p.sum()


def _spread(total, weights, rng, integer):
    """``total`` counts over cells in proportion to ``weights``."""
    w = np.asarray(weights, float)
    p = (w / w.sum()).ravel()
    if integer:
        return rng.multinomial(int(round(total)), p).reshape(w.shape).astype(float)
    return (total * p).reshape(w.shape)


def frame(record, k, rng, integer=True):
    """Image (rows, cols) = (PIL_W, PIL_H) for point ``k`` of ``record``."""
    c = record.counts
    b = float(record.background_per_pixel[k])
    img = rng.poisson(b, (synth.PIL_W, synth.PIL_H)).astype(float) if integer \
        else np.full((synth.PIL_W, synth.PIL_H), b)
    _, row = beam_pixel()
    sc, lc, rc = box_columns()
    shape = peak_shape()
    for col, key in ((sc, 'S'), (lc, 'B1'), (rc, 'B2')):
        core, outer = _box(row, col)
        w = np.full(shape.shape, b) + (shape * c['peak'][k] if key == 'S' else 0.0)
        if b == 0 and key != 'S':
            w = np.ones(shape.shape)
        img[core] = _spread(c[key + '_core'][k], w, rng, integer)
        n_out = (xrr_scans.ROI_ROWS - xrr_scans.CORE_ROWS) // 2        # 3 rows above, 3 below
        out = _spread(c[key + '_outer'][k], np.ones((2 * n_out, SLIT[0])), rng, integer)
        img[outer[0]] = out[:n_out]
        img[outer[1]] = out[n_out:]
    return img


def write_tif(path, image, integer=True):
    """As synth.write_pilatus_tif; float32 for expected (non-integer) counts."""
    if integer:
        return synth.write_pilatus_tif(path, image)
    Image.fromarray(np.ascontiguousarray(np.rot90(np.asarray(image, np.float32), 1))).save(path)
    return path


def _is_integer(data):
    return all(np.all(np.asarray(r.counts[k]) == np.round(r.counts[k]))
               for r in data.scans.values() for k in ('S_core', 'S_outer', 'B1_core', 'B2_core'))


def spec_text(data, name):
    """The SPEC scans (text) of ``data``: columns H K L Seconds Monc Monp
    Pilatus, #A the absorber setting, #W the beamline's wavelength."""
    out = []
    for num, r in sorted(data.scans.items()):
        z = np.zeros_like(r.qz)
        rows = np.column_stack([z, z, r.qz, r.seconds, r.monc, r.monp, r.pilatus])
        cmd = 'hklscan 0 0 0 0 %g %g %d %g' % (r.qz[0], r.qz[-1], len(r.qz) - 1, r.seconds[0])
        text = synth.spec_scan(num, name, COLUMNS, rows, command=cmd, fmt='%.12g', absorber=r.absorber)
        out.append(text.replace('#W x %g' % synth.WAVELENGTH, '#W x %.6f' % data.beamline.wavelength))
    return out


def render(data, root, name='xrr', seed=0):
    """Write ``root``/``name`` (SPEC) and ``root``/pilatus/ frames for every
    point of every scan of ``data`` (ReducedScans). Returns the SPEC path."""
    root = str(root)
    os.makedirs(os.path.join(root, 'pilatus'), exist_ok=True)
    rng = np.random.default_rng(seed)
    integer = _is_integer(data)
    spec = synth.write_spec(os.path.join(root, name), spec_text(data, name))
    for num, r in sorted(data.scans.items()):
        for k in range(len(r.qz)):
            write_tif(os.path.join(root, 'pilatus', '%s_SCAN-%d_%04d.tif' % (name, num, k)),
                      frame(r, k, rng, integer), integer)
    return spec
