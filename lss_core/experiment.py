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

from . import fluorescence as fluo
from . import reflectivity as refl
from .errors import as_model
from .absorbers import ABSFAC_10KEV
from .monitor import gain_factor


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


@dataclass
class FluorescenceResult:
    spectra: list         # (N, 3) energy, normalised counts, error, per spectrum
    rows: list            # [frame, qz, energy, intensity, error] per spectrum
    command: str
    unknown_gain: list = field(default_factory=list)   # scans with no known Monc gain

    def save(self, name, x='qz'):
        fluo.save_flu(name, self.rows, self.command, x=x)


class Experiment:
    def __init__(self, specfile, image_folder='pilatus', mca_folder='vortex'):
        from spec_routines import specread          # no Qt is needed
        self.specfile = os.path.abspath(specfile)
        self.folder = os.path.join(os.path.dirname(self.specfile), image_folder)
        self.mca_folder = os.path.join(os.path.dirname(self.specfile), mca_folder)
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
                     bad_pixel_iterations=0, bad_pixel_factor=1, errors=None, factors=None):
        """Specular reflectivity of ``scans``, as the window's Ref Patch with
        the same settings (defaults are the window's defaults for Pilatus
        data). ``drops``: {join number: [indices]} as typed into the patch
        dialog (several presses: a list of lists). ``merge_repeats``: average
        all repeated scans first; ``merge``: average only these groups. ``points``: {scan: [point numbers]} to use only
        some points of a scan (as when only some frames are selected).
        ``errors``: error model, 'legacy' (default: the window's numbers) or
        'budget' or an lss_core.errors.ErrorModel. ``factors``: {join number:
        (factor, error)} used instead of the fitted patch factor there, as
        when the window uses the known absorber ratio."""
        from TwoDDetector import TwoDDetector
        det = TwoDDetector('Pilatus')
        det.errors = as_model(errors)
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
        patched = refl.patch(per_scan, order, drops, factors)
        ref, out_rrf = refl.finish(patched[:, :3] if patched.shape[1] > 3 else patched,
                                   qc, qoff, norm_factor, rrf)
        return ReflectivityResult(per_scan, order, patched, ref, out_rrf, offsets)

    def spectra(self, scans):
        """(scan, spectrum number, Data, Par) for every MCA spectrum of the
        fluorescence scans ``scans``, in the window's list order."""
        from mca_routines import mcaread
        out = []
        name = os.path.basename(self.specfile)
        for n in scans:
            m = mcaread(os.path.join(self.mca_folder, '%s_%d_mca' % (name, n)))
            for j in range(m.Data['NumOfScans']):
                out.append((n, j + 1, m.Data[j], m.Par[j]))
        return out

    def fluorescence(self, scans, window=(1, 1000), monitor='Monc',
                     calibration=None, errors=None, absfac=ABSFAC_10KEV, monitor_gain=False):
        """Fluorescence intensity per spectrum, as the window's "Sum All".

        ``window``: energy range (keV with the file's calibration);
        ``monitor``: 'Monc', 'Monb', 'Mond' or None; ``calibration``:
        (constant, linear, quadratic) to override the file's; ``errors``:
        error model as for ``reflectivity``; ``absfac``: transmission factor
        per absorber unit (default 50 µm Al at 10 keV, lss_core.absorbers); normalised spectra are multiplied by absfac**n,
        n the scan's absorber setting (``Scan.parameters['Absorber']``; for
        getandsave_mca scans the last #A above them). ``monitor_gain``: also
        divide by the `Monc` gain, i.e. by M·S/S_ref instead of M
        (lss_core.monitor; only with monitor='Monc'); scans whose gain is
        unknown get no factor and are listed in ``result.unknown_gain``.
        """
        model = as_model(errors)
        spectra, rows, unknown = [], [], []
        for k, (scan, num, data, par) in enumerate(self.spectra(scans)):
            cal = calibration if calibration is not None else par['Calib']
            mon = None if monitor is None else data[monitor]
            p = self.scans[scan].parameters
            a = fluo.absorber_factor(absfac, p.get('Absorber'))
            g = 1.0
            if monitor_gain and monitor == 'Monc':
                g = gain_factor(p.get('MoncGain'))
                if p.get('MoncGain') is None and scan not in unknown:
                    unknown.append(scan)
            s = fluo.normalise_spectrum(data['Vortex'], par, mon, cal, model, a, g)
            u = float(model.monitor.relative(mon)) if (model.budget and mon is not None) else None
            inten, err, ini, fin = fluo.window_sum(s, window[0], window[1], u)
            energy = par.get('Energy', 10.0)
            spectra.append(s)
            rows.append([k + 1, par['Q'][2], energy, inten, err])
        command = ('Flu Sum, scans=[' + ', '.join(str(n) for n in sorted(scans))
                   + '], energy range=[' + str(ini) + ':' + str(fin) + ']')
        return FluorescenceResult(spectra, rows, command, unknown)
