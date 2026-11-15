"""Synthetic SPEC, Pilatus and MCA files for tests.

The layouts here are reverse-engineered from what ``spec_routines.specread``,
``mca_routines.mcaread`` and ``TwoDDetector.openFile`` accept. They are a
stand-in until real beamline files are added to the repository; they prove
that the code runs, not that it reads real 15-ID-C files correctly.
"""
import os

import numpy as np
from PIL import Image

WAVELENGTH = 1.24          # Angstrom
S2D = 600.0                # sample-to-detector distance, mm
S7D = 300.0                # slit-to-detector distance, mm
DB_X, DB_Y = 97, 100       # direct-beam position stored in the SPEC header
PIL_W, PIL_H = 487, 195    # Pilatus 100K TIFF size (width, height)
ABSFAC = 1.42             # attenuation per absorber foil
QC = 0.0217                # critical Qz used for the synthetic curve
PEAK_AMPLITUDE = 1.0e6     # peak counts per pixel at total reflection
PEAK_SIGMA = 2.0           # pixels
MONITOR = 1.0e5
MOTORS = {
    'In_Rot': 0.1, 'Sample_H': 0.0, 'Two_Thet': 0.0, 'Chi': 0.0, 'Phi': 0.0,
    'S1T': 0.01, 'S1B': 0.01, 'S1L': 0.5, 'S1R': 0.5,
    'S4L': 0.5, 'S4R': 0.5, 'S5L': 0.5, 'S5R': 0.5,
}


def _header(num, command, name, qz, absorber=0, image=True, motors=None):
    m = dict(MOTORS)
    m.update(motors or {})
    lines = ['#S %d  %s' % (num, command),
             '#D Sat Nov 14 12:00:00 2026',
             '#G0 0 0 0 0 0 100.0 200.0 300.0 0',
             '#Q 0 0 %g' % qz,
             '#P0 ' + ' '.join(m),
             '# ' + ' '.join(repr(v) for v in m.values()),
             '#W x %g' % WAVELENGTH,
             '#A x %d' % absorber]
    if image:
        lines += ['#B0 %s_SCAN-%d_0000.tif' % (name, num),
                  '#B1 %d %d %g %g' % (DB_Y, DB_X, S2D, S7D)]
    return lines


def spec_scan(num, name, columns, rows, command='hklscan 0 0 0 0 0.01 0.1 5 1',
              **kw):
    """Text of one scan. ``rows`` is a 2D array, one row per point."""
    rows = np.asarray(rows, dtype=float)
    lcol = columns.index('L') if 'L' in columns else None
    qz = rows[0, lcol] if lcol is not None else 0.0
    lines = _header(num, command, name, qz, **kw)
    lines.append('#N %d' % len(columns))
    lines.append('#L ' + '  '.join(columns))
    lines += [' '.join('%.6g' % v for v in r) for r in rows]
    return '\n'.join(lines) + '\n\n'


def reflectivity(qz, qc=QC):
    """Fresnel reflectivity (no absorption) used for the synthetic peaks."""
    qz = np.asarray(qz, dtype=float)
    s = np.sqrt(np.maximum(qz ** 2 - qc ** 2, 0.0))
    return np.where(qz <= qc, 1.0, ((qz - s) / (qz + s)) ** 2)


def ref_rows(qz, counts=1000.0, monitor=MONITOR, seconds=1.0):
    """Rows for a specular scan with columns H K L Seconds Monc Pilatus."""
    qz = np.atleast_1d(qz).astype(float)
    z = np.zeros_like(qz)
    return np.column_stack([z, z, qz, z + seconds, z + monitor, z + counts])


REF_COLUMNS = ['H', 'K', 'L', 'Seconds', 'Monc', 'Pilatus']


def write_spec(path, scans_text):
    name = os.path.basename(path)
    with open(path, 'w') as f:
        f.write('#F %s\n#E 0\n#D Sat Nov 14 12:00:00 2026\n\n' % name)
        for s in scans_text:
            f.write(s)
    return path


def pilatus_image(peak=None, background=2.0, amplitude=5000.0,
                  sigma=PEAK_SIGMA):
    """Image as the reader returns it: shape (PIL_W, PIL_H) = (rows, cols).

    ``peak`` is (col, row) in that array, or None for a flat image.
    """
    img = np.full((PIL_W, PIL_H), float(background))
    if peak is not None:
        r, c = np.mgrid[0:PIL_W, 0:PIL_H]
        img += amplitude * np.exp(-((c - peak[0]) ** 2 + (r - peak[1]) ** 2)
                                  / 2.0 / sigma ** 2)
    return np.round(img)


def write_pilatus_tif(path, array):
    """Write ``array`` (shape (PIL_W, PIL_H)) so that openFile reads it back.

    openFile applies ROTATE_270 and reshapes to (width, height); this applies
    the inverse rotation.
    """
    a = np.asarray(array).astype(np.int32)
    # ROTATE_270 is np.rot90(T, 3), so the TIFF holds np.rot90(a, 1).
    im = Image.fromarray(np.ascontiguousarray(np.rot90(a, 1)))
    im.save(path)
    return path


def write_mca(path, spectra, monitor=1.0e5, qz=0.02, energy=10.0):
    """One MCA file holding ``spectra`` (list of 1D count arrays)."""
    with open(path, 'w') as f:
        f.write('#F %s\n\n' % os.path.basename(path))
        for i, y in enumerate(spectra):
            y = [int(v) for v in y]
            f.write('#S %d  getandsave_mca 1\n' % (i + 1))
            f.write('#@CTIME 1.0 1.0 0.9\n')
            f.write('#Monc %g\n' % monitor)
            f.write('#Q 0 0 %g\n' % qz)
            f.write('#@CALIB 0.0 0.01 0.0\n')
            f.write('#Energy %g\n' % energy)
            chunks = [y[k:k + 16] for k in range(0, len(y), 16)]
            assert len(chunks) > 1, 'reader needs at least two data lines'
            for k, ch in enumerate(chunks):
                head = '@A ' if k == 0 else ''
                tail = '\\\n' if k < len(chunks) - 1 else '\n'
                f.write(head + ' '.join(map(str, ch)) + tail)
            f.write('\n')
    return path


def make_dataset(root, name='sample'):
    """A small experiment directory: SPEC file, pilatus/ and vortex/.

    Scans: 1-2 specular reflectivity (Pilatus) with overlapping Qz ranges,
    scan 2 taken through one absorber foil (peaks attenuated by ABSFAC);
    3 a fluorescence scan (Vortex); 4 a plain motor scan (no images).
    The reflected peak is a Gaussian whose height follows ``reflectivity``.
    Returns the SPEC file path.
    """
    root = str(root)
    os.makedirs(os.path.join(root, 'pilatus'))
    os.makedirs(os.path.join(root, 'vortex'))
    qz1 = np.linspace(0.01, 0.05, 9)
    qz2 = np.linspace(0.04, 0.10, 7)
    scans = [spec_scan(1, name, REF_COLUMNS, ref_rows(qz1)),
             spec_scan(2, name, REF_COLUMNS, ref_rows(qz2), absorber=1)]
    scans.append('#S 3  getandsave_mca 1\n#Q 0 0 0.02\n#W x %g\n#A x 0\n\n'
                 % WAVELENGTH)
    x = np.linspace(-1, 1, 21)
    y = 1000 * np.exp(-x ** 2 / 2 / 0.2 ** 2) + 10
    scans.append(spec_scan(4, name, ['sh', 'Seconds', 'Monc', 'Apex2'],
                           np.column_stack([x, x * 0 + 1, x * 0 + 1e5, y]),
                           command='ascan sh -1 1 20 1', image=False))
    spec = write_spec(os.path.join(root, name), scans)
    peak = (PIL_H - DB_X - 1, DB_Y)   # reader flips x: col = NCOLS - X - 1
    for num, qzs, att in ((1, qz1, 1.0), (2, qz2, ABSFAC)):
        for j, q in enumerate(qzs):
            amp = PEAK_AMPLITUDE * reflectivity(q) / att
            write_pilatus_tif(
                os.path.join(root, 'pilatus', '%s_SCAN-%d_%04d.tif' % (name, num, j)),
                pilatus_image(peak=peak, amplitude=amp))
    ch = np.arange(1, 257)
    spectrum = 500 * np.exp(-(ch - 120.0) ** 2 / 2 / 5 ** 2) + 5
    write_mca(os.path.join(root, 'vortex', '%s_3_mca' % name),
              [spectrum, spectrum * 2])
    return spec



# ---- fluorescence near total reflection (XFNTR) ----------------------------

XF_QZ = np.round(np.linspace(0.012, 0.036, 9), 4)   # one MCA scan per Qz
XF_CHANNELS = 512
XF_CALIB = (0.0, 0.02, 0.0)        # keV = 0 + 0.02 * channel
XF_PEAK_CHANNEL = 320              # fluorescence line at 6.40 keV
XF_PEAK_SIGMA = 6.0                # channels
XF_ELASTIC_CHANNEL = 500           # elastic line at 10.0 keV
XF_REAL, XF_LIVE = 10.0, 9.0       # seconds
XF_MONITOR = 2.0e5


def xfntr_yield(qz, qc=QC):
    """Fluorescence counts in the line, per frame: a smooth curve peaking at
    the critical Qz, enough to tell the frames apart. Not a physical model."""
    qz = np.asarray(qz, dtype=float)
    return 4.0e4 * np.where(qz <= qc, (qz / qc) ** 2, (qc / qz) ** 3)


def xfntr_spectrum(qz):
    """Integer counts per channel for one frame, and the line's exact sum."""
    ch = np.arange(1, XF_CHANNELS + 1)
    line = np.exp(-(ch - XF_PEAK_CHANNEL) ** 2 / 2.0 / XF_PEAK_SIGMA ** 2)
    line = np.round(xfntr_yield(qz) * line / line.sum())
    elastic = np.round(3000.0 * np.exp(-(ch - XF_ELASTIC_CHANNEL) ** 2 / 2.0 / 4.0 ** 2))
    return line + elastic + 2.0, line


def make_xfntr_dataset(root, name='xf'):
    """SPEC file with one getandsave_mca scan per Qz, and vortex/ beside it.

    Returns (spec path, {scan number: counts in the fluorescence line}).
    """
    root = str(root)
    os.makedirs(os.path.join(root, 'vortex'))
    scans, truth = [], {}
    for n, q in enumerate(XF_QZ, start=1):
        scans.append('#S %d  getandsave_mca %g\n#Q 0 0 %g\n#W x %g\n#A x 0\n\n'
                     % (n, XF_REAL, q, WAVELENGTH))
        y, line = xfntr_spectrum(q)
        truth[n] = line
        path = os.path.join(root, 'vortex', '%s_%d_mca' % (name, n))
        with open(path, 'w') as f:
            f.write('#F %s\n\n#S 1  getandsave_mca %g\n' % (os.path.basename(path), XF_REAL))
            f.write('#@CTIME %g %g %g\n' % (XF_REAL, XF_REAL, XF_LIVE))
            f.write('#Monc %g\n#Q 0 0 %g\n' % (XF_MONITOR, q))
            f.write('#@CALIB %g %g %g\n#Energy 10.0\n' % XF_CALIB)
            vals = [int(v) for v in y]
            chunks = [vals[k:k + 16] for k in range(0, len(vals), 16)]
            for k, c in enumerate(chunks):
                f.write(('@A ' if k == 0 else '') + ' '.join(map(str, c))
                        + ('\\\n' if k < len(chunks) - 1 else '\n'))
            f.write('\n')
    return write_spec(os.path.join(root, name), scans), truth


# ---- burn test (same spot measured repeatedly) -----------------------------

BURN_TAU = 400.0        # seconds: reflected intensity decays as exp(-t/tau)
BURN_CTIME = 10.0       # seconds per frame
BURN_FRAMES = 21


def make_burn_dataset(root, name='burn'):
    """One reflectivity-geometry scan of BURN_FRAMES frames at fixed Qz whose
    reflected peak decays exponentially with time constant BURN_TAU."""
    root = str(root)
    os.makedirs(os.path.join(root, 'pilatus'))
    n = BURN_FRAMES
    z = np.zeros(n)
    rows = np.column_stack([z, z, z, z + 0.05, z + BURN_CTIME, z + MONITOR,
                            z + 1000.0])
    cols = ['In_Ht', 'H', 'K', 'L', 'Seconds', 'Monc', 'Pilatus']
    scan = spec_scan(1, name, cols, rows,
                     command='ascan  ih 0 0  %d %g' % (n - 1, BURN_CTIME))
    spec = write_spec(os.path.join(root, name), [scan])
    peak = (PIL_H - DB_X - 1, DB_Y)
    for j in range(n):
        amp = 2.0e5 * np.exp(-j * BURN_CTIME / BURN_TAU)
        write_pilatus_tif(os.path.join(root, 'pilatus', '%s_SCAN-1_%04d.tif' % (name, j)),
                          pilatus_image(peak=peak, amplitude=amp))
    return spec
