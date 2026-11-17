"""A SPEC file and its image frames, read without the window.

    from lss_core.experiment import Experiment
    exp = Experiment('sample_data/NX_school/2026sep/20260923')
    exp.scans                          # {number: Scan}
    frames = exp.frames([6, 7, 8, 9])  # Frame records, in scan/point order
    result = exp.reflectivity([6, 7, 8, 9])
    result.save('dppc')                # dppc_ref.txt, dppc_rrf.txt

Frames are matched to image files by the frame number in the file name,
and images are read through the shared cache (lss_core.images).
"""
import glob
import os
from dataclasses import dataclass, field

import numpy as np

from . import reflectivity as refl


@dataclass
class Scan:
    number: int
    command: str
    detector: str
    columns: dict
    parameters: dict


@dataclass
class Frame:
    scan: int
    index: int            # point number within the scan
    path: str
    qz: float
    monitor: float
    absorber: int
    beam_xy: tuple        # (X, Y) direct-beam pixel from the SPEC header
    distance: float       # sample-detector distance, mm


@dataclass
class ReflectivityResult:
    per_scan: dict        # scan number -> (N, 7) rows, see lss_core.reflectivity
    order: list
    patched: np.ndarray   # (N, 3) Qz, R, sigma before normalisation
    ref: np.ndarray
    rrf: np.ndarray = None
    beam_offsets: list = field(default_factory=list)  # (scan, point, dx, dy)

    def save(self, name):
        refl.save(name, self.ref, self.rrf)


class Experiment:
    def __init__(self, specfile, image_folder='pilatus'):
        from spec_routines import specread          # no Qt is needed
        self.specfile = os.path.abspath(specfile)
        self.folder = os.path.join(os.path.dirname(self.specfile), image_folder)
        r = specread(self.specfile)
        self._data, self._par = r.Data, r.Par
        self.scans = {}
        for n in sorted(set(r.Data.get('ScanNums', []))):
            d = r.Data[n]
            cols = {k: v for k, v in d.items() if isinstance(v, np.ndarray)}
            self.scans[n] = Scan(n, d['ScanLine'].split(None, 2)[-1].strip(),
                                 r.Par[n].get('Detector'), cols, r.Par[n])

    def frames(self, scans):
        """Frame records of the Pilatus scans ``scans`` that have an image."""
        out = []
        name = os.path.basename(self.specfile)
        for n in sorted(scans):
            scan = self.scans[n]
            if scan.detector != 'Pilatus':
                raise ValueError('scan %d is not a Pilatus scan' % n)
            files = {}
            for path in glob.glob(os.path.join(self.folder, '%s_SCAN-%d_*' % (name, n))):
                try:
                    files[int(path.split('_')[-1].split('.')[0])] = path
                except ValueError:
                    pass
            monc = scan.columns['Monc'] if 'Monc' in scan.columns else scan.columns['monc']
            p = scan.parameters
            for j, qz in enumerate(scan.columns['L']):
                if j in files:
                    out.append(Frame(n, j, files[j], float(qz), float(monc[j]),
                                     p['Absorber'], (p['DBPos'][1], p['DBPos'][0]),
                                     float(p['S2D_Dist'])))
        return out

    def reflectivity(self, scans, slit=(21, 11), bg_offset=0.5, direction='H',
                     qc=0.0217, qoff=0.0, norm_factor=None, rrf=True,
                     drops=None, merge_repeats=False, merge=None, low_qz_slit=False, points=None,
                     bad_pixel_iterations=0, bad_pixel_factor=1):
        """Specular reflectivity of ``scans``, as the window's Ref Patch with
        the same settings (defaults are the window's defaults for Pilatus
        data). ``drops``: {join number: [indices]} as typed into the patch
        dialog (several presses: a list of lists). ``merge_repeats``: average
        all repeated scans first; ``merge``: average only these groups. ``points``: {scan: [point numbers]} to use only
        some points of a scan (as when only some frames are selected)."""
        from TwoDDetector import TwoDDetector
        det = TwoDDetector('Pilatus')
        per_scan, offsets = {}, []
        for f in self.frames(scans):
            if points is not None and f.scan in points and f.index not in points[f.scan]:
                continue
            det.openFile(f.path, bad_pix=bad_pixel_iterations, bad_fac=bad_pixel_factor)
            image, error = det.imageData, det.errorData
            first = f.scan not in per_scan
            row, info = refl.frame_row(det, image, error, f.monitor, f.beam_xy, f.qz,
                                      slit, bg_offset, direction, f.distance,
                                      low_qz_slit=(first or low_qz_slit))
            per_scan[f.scan] = row if first else np.vstack((per_scan[f.scan], row))
            off = info['offset']
            if abs(off[0]) > 2 or abs(off[1]) > 2:
                offsets.append((f.scan, f.index, off[0], off[1]))
        per_scan = {k: np.atleast_2d(v) for k, v in per_scan.items()}
        if merge_repeats:
            for group in refl.identical_groups(per_scan):
                refl.merge_identical(per_scan, group)
        for group in merge or []:          # groups merged by hand, as in the window
            refl.merge_identical(per_scan, list(group))
        order = refl.order_scans(per_scan)
        patched = refl.patch(per_scan, order, drops)
        ref, out_rrf = refl.finish(patched[:, :3] if patched.shape[1] > 3 else patched,
                                   qc, qoff, norm_factor, rrf)
        return ReflectivityResult(per_scan, order, patched, ref, out_rrf, offsets)
