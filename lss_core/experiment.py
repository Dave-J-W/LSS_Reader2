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

from . import cuts as cutmod
from . import fluorescence as fluo
from . import normalise as norm
from . import reflectivity as refl
from .errors import as_model
from .absorbers import ABSFAC_10KEV, energy_kev
from .flux import photon_factor
from .monitor import gain_factor, scan_rate


def absorber_setting(params):
    """A Pilatus scan's absorber setting n for the arithmetic: 0 (no factor)
    when ``#A`` is missing or unreadable (Absorber None). Such scans are
    scaled by the patch like any other (owner, 2026-11-19); only a known
    ratio is not available for their joins."""
    n = params.get('Absorber')
    return 0 if n is None else n


def monitor_factor(params, monitor_gain=False, per_photon=False, rate_hz=None):
    """(factor, known) on a value divided by Monc counts: 1 (counts), the
    gain factor S_ref/S (``monitor_gain``) or M/N per incident photon
    (``per_photon``, lss_core.flux.photon_factor; includes the gain). Not
    known (the gain or energy unknown, energy outside 5-30 keV): factor 1."""
    if per_photon:
        wl = params.get('Wavelength')
        e = energy_kev(wl) if isinstance(wl, (int, float)) and wl > 0 else None
        f, _ = photon_factor(params.get('MoncGain'), e, rate_hz)
        return (1.0, False) if f is None else (f, True)
    if monitor_gain:
        return (1.0, False) if params.get('MoncGain') is None else (gain_factor(params['MoncGain']), True)
    return 1.0, True


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
class CutResult:
    cuts: list            # (N, 3) x, I, sigma per frame, or one for the summed frames
    labels: list          # 'S# 1_F# 0' per frame, as the window's file names
    summed_label: str = None   # 'S# 1' when the frames were summed

    def save(self, name):
        return cutmod.save(name, self.cuts, self.labels, self.summed_label)


@dataclass
class FluorescenceResult:
    spectra: list         # (N, 3) energy, normalised counts, error, per spectrum
    rows: list            # [frame, qz, energy, intensity, error] per spectrum
    command: str
    unknown_gain: list = field(default_factory=list)   # scans with no known Monc gain

    def save(self, name, x='qz'):
        fluo.save_flu(name, self.rows, self.command, x=x)

    def merge(self, window=None, x='qz', jitter=fluo.QZ_JITTER):
        """The window's "Merge" (lss_core.fluorescence.merge_rows): rows
        within ``window`` on axis ``x`` merged; default window 0.1 × the Qz
        grid step; on the Qz axis the Qz jitter is added to the errors.
        Changes ``rows`` in place and returns them."""
        self.rows = [list(r) for r in fluo.merge_rows(self.rows, x, window, jitter)]
        return self.rows


@dataclass
class GIDResult:
    """A GID map as the window makes it (lss_core.gid). ``x``, ``y``: 2θ and
    β meshes (degrees); ``data``, ``err``: the map; ``joins``: one entry per
    join (label, kind, overlap, points, factor ± error, χ²/dof); ``levels``:
    (name, scans, frames, 2θ from, 2θ to) per Qz level; ``info``: the
    pinhole patch's per-level and join details (None for the legacy one)."""
    x: np.ndarray
    y: np.ndarray
    data: np.ndarray
    err: np.ndarray
    joins: list
    levels: list
    params: object
    alpha: float
    wavelength: float
    relax: bool = False
    info: dict = None

    def products(self, axes='Q'):
        """The window's plotted and saved arrays in 'Angles' or 'Q'."""
        from . import gid as gidmod
        return gidmod.products(self.x, self.y, self.data, self.err, axes, self.alpha, self.wavelength, self.relax)

    def save(self, name, axes=None):
        """The window's "Save GID" files; ``axes`` defaults to the one given
        to Experiment.gid."""
        from . import gid as gidmod
        return gidmod.save(name, self.products(axes or self.axes))


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

    def point_times(self, scan):
        """When each point of ``scan`` was measured (lss_core.timing.PointTimes):
        new files from Tstart/Tend and #U SeriesT0; old files from the scan's
        #D plus Epoch differences, and the time since the macro started from
        the #D of the first scan of the series lss_core.series infers (its
        '#U Series' lines when present). Never fails for a missing column:
        the result's ``format`` and ``notes`` say what was available."""
        from . import series as sermod
        from . import timing
        p = self.scans[scan].parameters
        offset = timing.utc_offset(p.get('FileEpoch'), p.get('FileDate'))
        first_date = None
        if timing.time_format(self.scans[scan].columns) == 'old':
            info = sermod.scan_info(self._data, self._par)
            groups = sermod.group(info) or sermod.infer(info)
            for g in groups:
                members = set(g.scans.values()) | set(n for n, _ in g.aux)
                if scan in members:
                    first_date = self.scans[min(members)].parameters.get('Date')
                    break
        return timing.point_times(self.scans[scan].columns, p.get('Date'), offset,
                                  series_t0=p.get('SeriesT0'), series_first_date=first_date)

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
                                     absorber_setting(p), (p['DBPos'][1], p['DBPos'][0]),
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

    def cut(self, scans, direction, range, axes='Pixels', summed=False, points=None,
            absfac=ABSFAC_10KEV, errors=None, monitor_gain=False, distance=None, db_pos=None,
            pinhole=True, bad_pixel_iterations=0, bad_pixel_factor=1, per_photon=False):
        """Line cuts of the frames of ``scans``, as the window's Line/Area
        Cuts tab with the same settings (lss_core.cuts). ``direction``: one of
        cuts.DIRECTIONS ('Q H', 'Q V', 'Pix H', 'Pix V'); ``range``: (low,
        high) in Qz, Qxy or pixels; ``axes``: 'Pixels', 'Angles' or 'Q' (pixel
        cuts only); ``summed``: cut the mean of the frames (the window's
        "Sum"). Frames are divided by their monitor and multiplied by the
        absorber factor ``absfac`` (a number per unit, or
        lss_core.absorbers.Foils) first. ``points``: {scan: [point numbers]}
        to use only some frames. Geometry from the SPEC header, unless
        ``distance`` (mm) and ``db_pos`` (column, row of the direct beam) are
        given, as when the window's "use SPEC values" box is unticked;
        ``pinhole`` (default, as the window): frames at Det_Th > 1° take the
        S4-detector distance (S7D_Dist) for the horizontal Angles/Q axis. ``errors``,
        ``monitor_gain``, ``per_photon``: as for ``fluorescence`` (the
        monitor rate for the dark term is the scan's median Monc/Seconds)."""
        from TwoDDetector import TwoDDetector
        from .errors import MonitorTerms
        det = TwoDDetector('Pilatus')
        det.errors = model = as_model(errors)
        lo, hi = float(range[0]), float(range[1])
        frames = [f for f in self.frames(scans)
                  if points is None or f.scan not in points or f.index in points[f.scan]]
        if not frames:
            raise ValueError('no frames with images in scans %s' % list(scans))
        data, errs, terms, geoms, labels = [], [], [], [], []
        for k, f in enumerate(frames):
            det.openFile(f.path, bad_pix=bad_pixel_iterations, bad_fac=bad_pixel_factor)
            p = self.scans[f.scan].parameters
            cols = self.scans[f.scan].columns
            g = monitor_factor(p, monitor_gain, per_photon,
                               scan_rate(cols) if per_photon else None)[0]
            d, e = norm.normalise_frame(det.imageData, det.errorData, f.monitor, absfac, f.absorber,
                                        model=model, gain=g)
            data.append(d)
            errs.append(e)
            terms.append(norm.frame_terms(('', k), d, f.monitor, model) if model.budget else None)
            wl = p['Wavelength']
            alpha = np.arcsin(f.qz * wl / 4.0 / np.pi)
            if 'Det_Th' in cols:
                dth = cols['Det_Th'][f.index] * np.pi / 180.0
            else:
                dth = 2.0 * np.arcsin(np.sqrt(cols['H'][f.index] ** 2 + cols['K'][f.index] ** 2) * wl / 4.0 / np.pi)
            dist = p['S2D_Dist'] if distance is None else float(distance)
            if pinhole and axes in ('Angles', 'Q') and np.degrees(dth) > 1.0:
                dist = p['S7D_Dist']
            if db_pos is None:
                xc, yc = float(det.NCOLS) - 1 - p['DBPos'][1], p['DBPos'][0]
            else:
                xc, yc = float(db_pos[0]), float(db_pos[1])
            geoms.append(cutmod.Geometry(wl, alpha, p['In_Rot'] * np.pi / 180.0, dth,
                                         -p['g_l2'] * np.tan(alpha), dist, p['S2D_Dist'], xc, yc))
            labels.append('S# %d_F# %d' % (f.scan, f.index))
        if summed:
            t = None
            if model.budget:
                t = MonitorTerms()
                for x in terms:
                    if x is not None:
                        t.extend(x, 1.0 / len(frames))
            d, e = cutmod.mean_frame(data, errs)
            out = cutmod.frame_cut(det, d, e, direction, lo, hi, geoms[0], axes, absfac=absfac,
                                   absnum=frames[0].absorber, terms=t)
            return CutResult([out], labels, 'S# %d' % min(scans))
        out = [cutmod.frame_cut(det, d, e, direction, lo, hi, g, axes, absfac=absfac, absnum=f.absorber, terms=t)
               for d, e, g, f, t in zip(data, errs, geoms, frames, terms)]
        return CutResult(out, labels)

    def gid_frames(self, scans, points=None, db_pos=None, bad_pixel_iterations=0, bad_pixel_factor=1,
                   errors=None):
        """lss_core.gid.GIDFrame for the frames of ``scans`` (in the window's
        list order), with the values the window takes from the SPEC file;
        and the detector object the legacy patch sums with."""
        from TwoDDetector import TwoDDetector
        from . import gid as gidmod
        det = TwoDDetector('Pilatus')
        det.errors = as_model(errors)
        out = []
        for f in self.frames(sorted(scans)):
            if points is not None and f.scan in points and f.index not in points[f.scan]:
                continue
            det.openFile(f.path, bad_pix=bad_pixel_iterations, bad_fac=bad_pixel_factor)
            p = self.scans[f.scan].parameters
            cols = self.scans[f.scan].columns
            wl = p['Wavelength']
            if 'Det_Th' in cols:
                dth = cols['Det_Th'][f.index] * np.pi / 180.0
            else:
                dth = 2.0 * np.arcsin(np.sqrt(cols['H'][f.index] ** 2 + cols['K'][f.index] ** 2) * wl / 4.0 / np.pi)
            if db_pos is None:
                centre = (float(det.NCOLS) - 1 - p['DBPos'][1], p['DBPos'][0])
            else:
                centre = (float(db_pos[0]), float(db_pos[1]))
            out.append(gidmod.GIDFrame(np.array(det.imageData), np.array(det.errorData), f.monitor, f.absorber,
                                       f.scan, f.qz, np.arcsin(f.qz * wl / 4.0 / np.pi), p['In_Rot'] * np.pi / 180.0,
                                       dth, wl, centre, p['S2D_Dist'], p['S7D_Dist'], p['Sample_H'],
                                       (p['S1L'] + p['S1R'], p['S1T'] + p['S1B'], p['S4L'] + p['S4R'], p['S5L'] + p['S5R']),
                                       p))
        if not out:
            raise ValueError('no frames with images in scans %s' % list(scans))
        return out, det

    def gid(self, scans, params=None, axes='Q', relax=False, points=None, db_pos=None, errors=None,
            bad_pixel_iterations=0, bad_pixel_factor=1):
        """GID map of the frames of ``scans``, as the window's "GID Patch"
        (``relax``: "GID Patch Relax") with the GID worksheet's settings
        ``params`` (lss_core.gid.GIDParams; default: pinhole geometry, as
        the window). ``axes``: 'Q' or 'Angles', what ``save`` writes;
        ``points``, ``db_pos`` (typed direct beam, column and row), the
        bad-pixel settings and ``errors`` (legacy patch only) as the window.
        Background-subtracted frames are not scriptable yet. Raises
        lss_core.gid.GIDError where the window shows a message and stops."""
        from . import gid as gidmod
        gp = gidmod.GIDParams() if params is None else params
        frames, det = self.gid_frames(scans, points, db_pos, bad_pixel_iterations, bad_pixel_factor, errors)
        log, warnings = [], []
        info = None
        if gp.pinhole:
            patch, levels, level_info, jinfo = gidmod.pinhole_patch(frames, gp, log=log)
            info = dict(levels=level_info, join=jinfo)
        else:
            patch, levels = gidmod.legacy_patch(frames, gp, det, log=log, warn=warnings.append)
        X, Y, D, E = gidmod.map_arrays(patch)
        res = GIDResult(X, Y, D, E, log, levels, gp, frames[0].true_alpha, frames[0].wavelength, bool(relax), info)
        res.axes = axes
        res.warnings = warnings
        return res

    def spectra(self, scans, channels=None):
        """(scan, spectrum number, Data, Par) for every MCA spectrum of the
        fluorescence scans ``scans``, in the window's list order. Files of a
        multi-element detector give one spectrum per point, the elements in
        ``channels`` summed (None: all; lss_core.fluorescence.combine_channels)."""
        from mca_routines import mcaread
        out = []
        name = os.path.basename(self.specfile)
        for n in scans:
            m = mcaread(os.path.join(self.mca_folder, '%s_%d_mca' % (name, n)))
            spec = fluo.combine_channels([(m.Data[j], m.Par[j]) for j in range(m.Data['NumOfScans'])], channels)
            for j, (d, p) in enumerate(spec):
                out.append((n, j + 1, d, p))
        return out

    def fluorescence(self, scans, window=(1, 1000), monitor='Monc',
                     calibration=None, errors=None, absfac=ABSFAC_10KEV, monitor_gain=False,
                     per_photon=False, channels=None):
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
        ``per_photon``: divide by the incident photons instead (F54;
        lss_core.flux.photon_factor: xray_fluxor route D, Monc dark 50 Hz,
        each spectrum's rate Monc / real time; bounds ±3.6 % below 13 keV, a
        common scale not in the errors); includes the gain. Scans where it is
        not known (gain or energy unknown) get no factor and are listed in
        ``result.unknown_gain``.
        """
        model = as_model(errors)
        spectra, rows, unknown = [], [], []
        for k, (scan, num, data, par) in enumerate(self.spectra(scans, channels)):
            cal = calibration if calibration is not None else par['Calib']
            mon = None if monitor is None else data[monitor]
            p = self.scans[scan].parameters
            a = fluo.absorber_factor(absfac, p.get('Absorber'))
            g = 1.0
            if (monitor_gain or per_photon) and monitor == 'Monc':
                rate = None
                if per_photon:
                    try:
                        rate = float(mon) / float(par['Time'][1])
                    except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError):
                        rate = None
                g, known = monitor_factor(p, monitor_gain, per_photon, rate)
                if not known and scan not in unknown:
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
