"""A SPEC file and its image frames, read without the window.

    from lss_core.experiment import Experiment
    exp = Experiment('sample_data/NX_school/2026sep/20260923')
    exp.scans                          # {number: Scan}
    frames = exp.frames([6, 7, 8, 9])  # Frame records, in scan/point order
    result = exp.reflectivity([6, 7, 8, 9])
    result.save('dppc')                # dppc_ref.txt, dppc_rrf.txt
    result.save('dppc', covariance='sidecar')   # + dppc_ref.cov.json, dppc_rrf.cov.json (xmodfit)

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
    method: str = refl.DEFAULT_PATCH_METHOD           # how the patch factors were fitted
    notes: list = field(default_factory=list)         # (join, note) left by the fit
    settings: dict = field(default_factory=dict)       # qc, qoff, norm_factor, rrf, drops, factors, method, mask
    points: dict = field(default_factory=dict)         # scan -> the point number of each row of per_scan (F92)
    masked: list = field(default_factory=list)         # (scan, point) left out by the mask

    def covariance(self, method=None, error_column=None):
        """The stitched curve with its covariance, as written to the
        xmodfit sidecars (``lss_core.covariance_export``): (ref, rrf)
        ``CovData`` after the window's normalisation, sort, Q_z offset and
        Fresnel division (rrf None without R/R_F).

        ``method``: None (default) the patch this result was made with
        (``self.method``: 'joint' or 'legacy'), replayed with W and Σ carried
        beside it, so x and y are exactly ``self.ref``/``self.rrf``; or
        'legacy'/'joint' explicitly; 'corrected' (the hand-off's §3.2 chain);
        'stitched' (``lss_core.patching.chain``: every point as measured,
        averaged only where Q_z coincide). ``error_column``: 'legacy' (the
        patch's own folded column, as in the files) or 'total' (√diag C);
        default 'legacy' for the 'legacy'/'joint' replays, 'total' otherwise."""
        from . import covariance_export as ce
        st = self.settings
        method = method or self.method
        drops, factors = st.get('drops'), st.get('factors')
        if method in ('legacy', 'joint'):
            cd = ce.tracked_chain(self.per_scan, self.order, drops, factors, method).covdata(error_column or 'legacy')
        elif method == 'corrected':
            cd = ce.corrected_chain(self.per_scan, self.order, drops, factors).covdata(error_column or 'total')
        elif method == 'stitched':
            if error_column == 'legacy':
                raise ValueError("the 'stitched' output has no folded error column")
            cd = ce.joint_covdata(self.per_scan, self.order, drops, factors, qc=st.get('qc', 0.0217),
                                  qoff=st.get('qoff', 0.0))
        else:
            raise ValueError("method %r: None, 'joint', 'legacy', 'corrected' or 'stitched'" % method)
        return ce.finish(cd, st.get('qc', 0.0217), st.get('qoff', 0.0), st.get('norm_factor'), st.get('rrf', True))

    def save(self, name, covariance=None, method=None, combined=False):
        """<name>_ref.txt and <name>_rrf.txt as the window writes them.

        ``covariance`` (default None: just those files, unchanged):
        'sidecar' adds <name>_ref.cov.json / _rrf.cov.json describing the
        files written (``method`` default: the patch of this result, whose
        files are then byte for byte those of ``save(name)``); 'contract'
        writes the hand-off's two outputs (docs/handoff/19 §2.5): <name>_ref.txt
        / _rrf.txt from ``method`` (default: this result's patch) with the
        error column √diag C, their sidecars, and the legacy patch's files
        as <name>_ref_legacy.txt / _rrf_legacy.txt (byte for byte the
        legacy method's _ref.txt / _rrf.txt). ``combined``: also
        <name>_ref.json / _rrf.json (§2.6). Returns the paths written."""
        if covariance is None:
            refl.save(name, self.ref, self.rrf)
            return [name + '_ref.txt'] + ([name + '_rrf.txt'] if self.rrf is not None else [])
        from . import covariance_export as ce
        if covariance == 'sidecar':
            ref, rrf = self.covariance(method)
            return ce.save(name, ref, rrf, combined=combined)
        if covariance == 'contract':
            ref, rrf = self.covariance(method, 'total')
            lref, lrrf = self.covariance('legacy', 'legacy')
            return ce.save(name, ref, rrf, legacy=(lref.array(), None if lrrf is None else lrrf.array()),
                           combined=combined)
        raise ValueError("covariance %r: None, 'sidecar' or 'contract'" % covariance)


@dataclass
class CutResult:
    cuts: list            # (N, 3) x, I, sigma per frame, or one for the summed frames
    labels: list          # 'S# 1_F# 0' per frame, as the window's file names
    summed_label: str = None   # 'S# 1' when the frames were summed

    def save(self, name):
        return cutmod.save(name, self.cuts, self.labels, self.summed_label)

    def fit(self, options=None):
        """Peaks of every cut (lss_core.peaks.fit_all, as the window's "Fit
        peaks"): a list, per cut, of FitResult (one per group of peaks)."""
        from . import peaks
        return [peaks.fit_all(c[:, 0], c[:, 1], c[:, 2], options) for c in self.cuts]


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
            groups = sermod.all_series(info)
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
                     drops=None, merge_repeats=False, merge=None, repeats='monitors', low_qz_slit=False, points=None,
                     bad_pixel_iterations=0, bad_pixel_factor=1, errors=None, factors=None,
                     method=refl.DEFAULT_PATCH_METHOD, mask=None):
        """Specular reflectivity of ``scans``, as the window's Ref Patch with
        the same settings (defaults are the window's defaults for Pilatus
        data). ``drops``: {join number: [indices]} as typed into the patch
        dialog (several presses: a list of lists). ``merge_repeats``: merge
        all repeated scans first; ``merge``: merge only these groups;
        ``repeats``: how, 'monitors' (default since 2026-11-23, F81: counts
        and monitors summed point by point, ΣN/ΣM) or 'mean' (the legacy
        average of the normalised repeats). ``points``: {scan: [point numbers]} to use only
        some points of a scan (as when only some frames are selected).
        ``errors``: error model, 'legacy' (default: the window's numbers) or
        'budget' or an lss_core.errors.ErrorModel. ``factors``: {join number:
        (factor, error)} used instead of the fitted patch factor there, as
        when the window uses the known absorber ratio. ``method``: how the
        patch factors are fitted, 'joint' (default since 2026-11-22) or
        'legacy' (the window's files before then, byte for byte;
        ``lss_core.reflectivity.join_factor``). ``mask``: (scan, point)
        pairs left out (F92, ``lss_core.masks``), after repeats are merged:
        a point of a repeat merged into the group's first scan masks that
        point of the merged scan (where the window's drops are made);
        ``drops`` then apply to what is left."""
        from TwoDDetector import TwoDDetector
        det = TwoDDetector('Pilatus')
        det.errors = as_model(errors)
        per_scan, offsets, mons, pts = {}, [], {}, {}
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
            mons.setdefault(f.scan, []).append(f.monitor)
            pts.setdefault(f.scan, []).append(f.index)
            off = info['offset']
            if abs(off[0]) > 2 or abs(off[1]) > 2:
                offsets.append((f.scan, f.index, off[0], off[1]))
        per_scan = {k: np.atleast_2d(v) for k, v in per_scan.items()}
        if repeats not in ('monitors', 'mean'):
            raise ValueError("repeats: 'monitors' or 'mean'")
        weights = mons if repeats == 'monitors' else None
        alias = {}                         # a repeat merged away -> the scan it went into
        groups = refl.identical_groups(per_scan) if merge_repeats else []
        for group in groups + [list(g) for g in merge or []]:     # by hand too, as in the window
            refl.merge_identical(per_scan, list(group), weights)
            for m in group[1:]:
                alias[m] = group[0]
        masked = self._apply_mask(per_scan, pts, alias, mask) if mask else []
        order = refl.order_scans(per_scan)
        notes = []
        patched = refl.patch(per_scan, order, drops, factors, method=method, notes=notes)
        ref, out_rrf = refl.finish(patched[:, :3] if patched.shape[1] > 3 else patched,
                                   qc, qoff, norm_factor, rrf)
        return ReflectivityResult(per_scan, order, patched, ref, out_rrf, offsets, method, notes,
                                  dict(qc=qc, qoff=qoff, norm_factor=norm_factor, rrf=rrf, drops=drops,
                                       factors=factors, method=method, repeats=repeats,
                                       mask=[list(sp) for sp in masked] if mask else None),
                                  {k: list(pts[k]) for k in per_scan}, masked)

    @staticmethod
    def _apply_mask(per_scan, pts, alias, mask):
        """Leave the masked points out of ``per_scan`` (and ``pts``) in place;
        returns the (scan, point) pairs left out, sorted. A point of a repeat
        merged away masks the point at the same position of the scan it went
        into; masked points of scans not in the reduction are ignored."""
        from . import masks as maskmod
        want = {}
        for s_, p_ in maskmod.Mask(mask):
            tgt = s_
            while tgt in alias:
                tgt = alias[tgt]
            if tgt != s_:
                if s_ not in pts or p_ not in pts[s_] or tgt not in pts:
                    continue
                p_ = pts[tgt][pts[s_].index(p_)]
            want.setdefault(tgt, set()).add(p_)
        masked = []
        for s_ in sorted(want):
            if s_ not in per_scan:
                continue
            keep = [i for i, p_ in enumerate(pts[s_]) if p_ not in want[s_]]
            masked += [(s_, p_) for p_ in pts[s_] if p_ in want[s_]]
            if keep:
                per_scan[s_] = per_scan[s_][keep]
                pts[s_] = [pts[s_][i] for i in keep]
            else:
                del per_scan[s_]
        return sorted(masked)

    def cut(self, scans, direction, range, axes='Pixels', summed=False, points=None, sum_mode='monitors',
            absfac=ABSFAC_10KEV, errors=None, monitor_gain=False, distance=None, db_pos=None,
            pinhole=True, bad_pixel_iterations=0, bad_pixel_factor=1, per_photon=False):
        """Line cuts of the frames of ``scans``, as the window's Line/Area
        Cuts tab with the same settings (lss_core.cuts). ``direction``: one of
        cuts.DIRECTIONS ('Q H', 'Q V', 'Pix H', 'Pix V'); ``range``: (low,
        high) in Qz, Qxy or pixels; ``axes``: 'Pixels', 'Angles' or 'Q' (pixel
        cuts only), or a diffuse-cut axis for any cut it fits (F97,
        cuts.DIFFUSE_AXES: 'beta', 'beta-alpha', 'Qz' for vertical cuts,
        'Qxy' for horizontal ones); ``summed``: cut the mean of the frames (the window's
        "Sum"). Frames are divided by their monitor and multiplied by the
        absorber factor ``absfac`` (a number per unit, or
        lss_core.absorbers.Foils) first. ``points``: {scan: [point numbers]}
        to use only some frames. Geometry from the SPEC header, unless
        ``distance`` (mm) and ``db_pos`` (column, row of the direct beam) are
        given, as when the window's "use SPEC values" box is unticked;
        ``pinhole`` (default, as the window): frames at Det_Th > 1° take the
        S4-detector distance (S7D_Dist) for the horizontal Angles/Q axis. ``errors``,
        ``monitor_gain``, ``per_photon``: as for ``fluorescence`` (the
        monitor rate for the dark term is the scan's median Monc/Seconds).
        ``sum_mode`` (with ``summed``): 'monitors', the frames summed and
        normalised once, ΣN/ΣM (F91, the default since 2026-11-23); 'mean', the
        legacy mean of the normalised frames."""
        from TwoDDetector import TwoDDetector
        from .errors import MonitorTerms
        det = TwoDDetector('Pilatus')
        det.errors = model = as_model(errors)
        lo, hi = float(range[0]), float(range[1])
        frames = [f for f in self.frames(scans)
                  if points is None or f.scan not in points or f.index in points[f.scan]]
        if not frames:
            raise ValueError('no frames with images in scans %s' % list(scans))
        data, errs, terms, geoms, labels, norms = [], [], [], [], [], []
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
            norms.append(cutmod.frame_normaliser(f.monitor, absfac, f.absorber, g))
            terms.append(norm.frame_terms(('', k), d, f.monitor, model) if model.budget else None)
            wl = p['Wavelength']
            alpha = np.arcsin(f.qz * wl / 4.0 / np.pi)
            if 'Det_Th' in cols:
                dth = cols['Det_Th'][f.index] * np.pi / 180.0
            else:
                dth = 2.0 * np.arcsin(np.sqrt(cols['H'][f.index] ** 2 + cols['K'][f.index] ** 2) * wl / 4.0 / np.pi)
            dist = p['S2D_Dist'] if distance is None else float(distance)
            if pinhole and axes in ('Angles', 'Q') + cutmod.DIFFUSE_AXES and np.degrees(dth) > 1.0:
                dist = p['S7D_Dist']
            if db_pos is None:
                xc, yc = float(det.NCOLS) - 1 - p['DBPos'][1], p['DBPos'][0]
            else:
                xc, yc = float(db_pos[0]), float(db_pos[1])
            geoms.append(cutmod.Geometry(wl, alpha, cutmod.true_incidence(cols, f.index, wl, p['In_Rot']), dth,
                                         -p['g_l2'] * np.tan(alpha), dist, p['S2D_Dist'], xc, yc))
            labels.append('S# %d_F# %d' % (f.scan, f.index))
        if summed:
            if sum_mode not in ('monitors', 'mean'):
                raise ValueError("sum_mode must be 'monitors' or 'mean'")
            share = cutmod.sum_weights(norms, legacy=sum_mode == 'mean')
            t = None
            if model.budget:
                t = MonitorTerms()
                for x, wk in zip(terms, share):
                    if x is not None:
                        t.extend(x, wk)
            d, e = (cutmod.mean_frame(data, errs) if sum_mode == 'mean'
                    else cutmod.sum_frames(data, errs, norms))
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
                                       f.scan, f.qz, np.arcsin(f.qz * wl / 4.0 / np.pi),
                                       cutmod.true_incidence(cols, f.index, wl, p['In_Rot']),
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
        the window, and the frames' last row, ``GIDParams.for_detector``). ``axes``: 'Q' or 'Angles', what ``save`` writes;
        ``points``, ``db_pos`` (typed direct beam, column and row), the
        bad-pixel settings and ``errors`` (legacy patch only) as the window.
        Background-subtracted frames are not scriptable yet. Raises
        lss_core.gid.GIDError where the window shows a message and stops."""
        from . import gid as gidmod
        frames, det = self.gid_frames(scans, points, db_pos, bad_pixel_iterations, bad_pixel_factor, errors)
        gp = gidmod.GIDParams.for_detector(np.shape(frames[0].data)) if params is None else params   # the frames' last row
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

    def burn(self, scan, points=None, time='clock', qxy_range=None, rows='mean', fit=None,
             models=None, threshold=0.05, confidence=0.95, slit=(21, 11), bg_offset=0.5, direction='H',
             errors=None, db_pos=None, bad_pixel_iterations=0, bad_pixel_factor=1, overdispersion=True,
             estimator='template', trend_errors=None, limit=('intensity', 'fwhm'), axis='time',
             dose_unit='photons', beam_mm=None, shutter='closed'):
        """Burn test of one Pilatus scan (lss_core.burn): per frame the
        reflected intensity (Det_Th 0; ``slit``, ``bg_offset``,
        ``direction`` as Ref Patch) or the strongest GID peak's intensity,
        position and FWHM (``qxy_range`` to choose another peak; ``rows``
        (low, high) pixel rows summed, both included: 'mean' (default since
        2026-11-24, Q-BURN-6) the rows where the mean frame's signal is,
        lss_core.burn.signal_rows, all rows when no peak stands out; None
        all rows (before); ``fit``: a
        peaks.FitOptions, for ``estimator`` 'fit'; ``estimator``: 'template'
        (default), 'moments' (the legacy arithmetic) or 'fit', lss_core.burn.measure_gid),
        all per monitor count; then each quantity over
        ``time`` ('clock', default, the wall time; or 'exposure') compared by AICc over ``models``
        (lss_core.trends.MODELS), with the time until a ``threshold``
        change at ``confidence``. ``points``: point numbers to use.
        ``trend_errors``: 'scatter' (default for GID: the frames' errors
        only as relative weights, their scale from the scatter, since a
        relative change is what matters; owner, 2026-11-21) or 'given'
        (default for reflectivity: counting errors as they are). ``limit``:
        the quantities whose 5 % time sets ``safe_time`` (add 'centre' for
        the position: the user's judgment). ``axis``: what the trends are
        fitted against, 'time' (default) or 'dose' (F98: the dose received
        since the first frame began, at the middle of each frame,
        lss_core.dose; ``dose_unit`` 'photons' or 'monitor', ``beam_mm``
        (width, height) for photons/mm², ``shutter`` 'open' for fast mode);
        the limit is then a dose. The dose
        is worked out whenever it can be (``res.dose``), whatever the axis."""
        from . import burn as burnmod
        from . import trends
        sc = self.scans[scan]
        frames = [f for f in self.frames([scan]) if points is None or f.index in points]
        if len(frames) < 3:
            raise ValueError('scan %d: a burn test needs at least 3 frames with images (%d)' % (scan, len(frames)))
        idx = [f.index for f in frames]
        cols = sc.columns
        if 'Det_Th' in cols:
            dth = float(cols['Det_Th'][idx[0]])
        else:
            dth = float(np.degrees(2.0 * np.arcsin(np.sqrt(cols['H'][idx[0]] ** 2 + cols['K'][idx[0]] ** 2)
                                                   * sc.parameters['Wavelength'] / 4.0 / np.pi)))
        kind = 'gid' if burnmod.is_gid(dth) else 'reflectivity'
        try:
            pt = self.point_times(scan)
        except Exception:                     # times are a nicety: exposure time still works
            pt = None
        t, note = burnmod.frame_times(cols, pt, idx, time)
        used = 'clock' if note.startswith('clock:') else 'exposure'     # the axis actually used
        res = burnmod.BurnResult(scan, kind, t, used, idx, notes=[note], threshold=threshold,
                                 limit_quantities=tuple(limit),
                                 seconds=np.asarray(cols['Seconds'], float)[idx] if 'Seconds' in cols else None)
        if axis not in burnmod.AXES:
            raise ValueError('axis %r: one of %s' % (axis, ', '.join(burnmod.AXES)))
        try:
            d = self.dose(scan, idx, unit=dose_unit, beam_mm=beam_mm, shutter=shutter)
            from . import dose as dosemod
            sc_ = dosemod.engineering_scale(d.total())      # the axis in 1e12 photons etc.: lss_core.dose
            res.dose, res.dose_total, res.dose_scale = d.cumulative() / sc_, d.total() / sc_, sc_
            res.dose_unit, res.dose_notes = dosemod.scaled_unit(d.unit, sc_), list(d.notes)
        except (ValueError, KeyError) as e:   # dose.DoseError is a ValueError
            res.dose_notes = ['dose not known: %s' % e]
            if axis == 'dose':
                raise
        res.axis = axis
        if kind == 'reflectivity':
            r = self.reflectivity([scan], slit=slit, bg_offset=bg_offset, direction=direction,
                                  points={scan: idx}, errors=errors, rrf=False,
                                  bad_pixel_iterations=bad_pixel_iterations, bad_pixel_factor=bad_pixel_factor)
            rows_ = r.per_scan[scan]
            res.values['intensity'] = (rows_[:, 1].astype(float), rows_[:, 2].astype(float))
        else:
            from . import cuts as cutmod
            from .images import read_pilatus
            last = np.shape(read_pilatus(frames[0].path))[0] - 1
            lo, hi = 0, last
            if isinstance(rows, str):
                if rows != 'mean':
                    raise ValueError("rows: 'mean', None or (low, high), not %r" % (rows,))
                found = burnmod.signal_rows(self.mean_frame(frames))
                if found is None:
                    res.notes.append('rows: all (no peak stands out in the mean frame)')
                else:
                    lo, hi = found
                    res.notes.append('rows %d-%d: where the mean frame\'s signal is (Q-BURN-6)' % found)
            elif rows is not None:
                if len(rows) != 2:
                    raise ValueError('rows: (first, last), not %r' % (rows,))
                lo, hi = int(rows[0]), int(rows[1])
            res.rows = (max(int(lo), 0), min(int(hi), last))
            c = self.cut([scan], 'Pix H', (lo, hi), axes='Q', points={scan: idx}, errors=errors, db_pos=db_pos,
                         bad_pixel_iterations=bad_pixel_iterations, bad_pixel_factor=bad_pixel_factor)
            res.profiles = [np.asarray(p, float) for p in c.cuts]
            res.values, res.reference, res.window, res.frame_fits = burnmod.measure_gid(res.profiles, qxy_range, fit,
                                                                                         estimator)
            bad = sum(1 for f in res.frame_fits if not f['ok'])
            if bad:
                res.notes.append('%d frame(s) whose peak fit failed are left out' % bad)
        te = trend_errors or ('scatter' if kind == 'gid' else 'given')
        res.trend_errors = te
        res.trends = burnmod.analyse(res.x, res.values, models or trends.MODELS, threshold, confidence, overdispersion,
                                     errors=te)
        return res

    def beam_height(self, scans=None, near=None, counter='Pilatus', monitor='Monc'):
        """The beam's height at the sample for the dose (lss_core.dose,
        BeamHeight): 1.0645 × the median rising-edge FWHM of the accepted
        sample-height scans among ``scans`` (default every height scan of
        the file), or, with ``near`` a scan number, of the NEAR_SCANS nearest
        height scans with that scan's S1 gap; the study's default where none
        is accepted and its conditions hold."""
        from . import dose as dosemod
        from . import peaks
        cand = [n for n in sorted(self.scans if scans is None else scans)
                if peaks.is_height_scan(self.scans[n].command) and counter in self.scans[n].columns]
        ref = self.scans[near].parameters if near is not None else (self.scans[cand[0]].parameters if cand else
                                                                     next(iter(self.scans.values())).parameters)
        if near is not None:
            gap = dosemod.s1_gap_mm(ref)
            cand = [n for n in cand if gap is not None and dosemod.s1_gap_mm(self.scans[n].parameters) is not None
                    and abs(dosemod.s1_gap_mm(self.scans[n].parameters) - gap) < 1e-3]
        edges, refused = [], []
        for n in cand:
            x, y, s = dosemod.height_scan_data(self.scans[n].columns, counter, monitor)
            e = dosemod.rising_edge(x, y, s, scan=n)
            (edges if e.ok else refused).append(e)
        if near is not None:
            edges = sorted(edges, key=lambda e: (abs(e.scan - near), e.scan))[:dosemod.NEAR_SCANS]
        if not edges:
            h = dosemod.default_height(ref)
            h.refused = refused
            return h
        fw = float(np.median([e.fwhm for e in edges]))
        spread = (float(np.std([e.fwhm for e in edges], ddof=1)) / fw) if len(edges) > 1 else None
        return dosemod.BeamHeight(fw * dosemod.HEIGHT_PER_RISE_FWHM, 'height scans', spread, edges, refused,
                                  'median rising FWHM %.4f mm of scans %s' % (fw, ', '.join(str(e.scan) for e in edges)))

    def beam_width(self, scans=None, counter='Pilatus', monitor=None, motors=None):
        """The beam's width at the sample for the dose (lss_core.dose,
        BeamWidth, F109): √(2π)σx from the median FWHM of the accepted S1
        horizontal slit scans among ``scans`` (default every scan of
        ``motors``, dose.S1_H_MOTORS), each fitted by ``dose.slit_profile``
        (a peak corrected for the scan's S1 gap, an edge, or a box); the
        owner's 1 mm prefill when none is accepted. ``monitor``: None (the
        default) uses the counter as recorded, since a monitor downstream of
        S1 would divide the profile out."""
        from . import dose as dosemod
        motors = tuple(m.lower() for m in (motors or dosemod.S1_H_MOTORS))
        cand = [n for n in sorted(self.scans if scans is None else scans)
                if (scans is not None or dosemod.is_slit_scan(self.scans[n].command, motors))
                and counter in self.scans[n].columns]
        good, refused = [], []
        for n in cand:
            cols = self.scans[n].columns
            x = np.asarray(cols[next(iter(cols))], float)
            c = np.asarray(cols[counter], float)
            m = np.ones_like(c) if monitor is None else np.asarray(cols[monitor], float)
            pr = dosemod.slit_profile(x, c / m, np.sqrt(np.maximum(c, 1.0) + (0.01 * c) ** 2) / m,
                                      gap_mm=dosemod.s1_hgap_mm(self.scans[n].parameters), scan=n)
            (good if pr.ok else refused).append(pr)
        if not good:
            w = dosemod.default_width()
            w.refused = refused
            return w
        fw = float(np.median([p.fwhm for p in good]))
        return dosemod.BeamWidth(fw / dosemod.GAUSS_FWHM_PER_SIGMA * dosemod.WIDTH_PER_SIGMA, 'slit scans', fw, good,
                                 refused, 'median FWHM %.4f mm of S1 slit scans %s'
                                 % (fw, ', '.join(str(p.scan) for p in good)))

    def dose_summary(self, scan, points=None, beam_mm=None, unit='photons', absfac=None, monitor='Monc',
                     shutter='closed', extent=None, top=None):
        """The dose ``scan`` (its ``points``) gave the sample as peak, average
        and the split of F109 (lss_core.dose.dose_map, DoseSummary).
        ``beam_mm`` (width, height), √(2π)σ each; default the width from
        ``beam_width()`` and the height from ``beam_height(near=scan)``."""
        from . import dose as dosemod
        notes = []
        if beam_mm is None:
            bw, bh = self.beam_width(), self.beam_height(near=scan)
            if bh.height_mm is None:
                raise dosemod.DoseError('no beam height: %s; give beam_mm=(width, height)' % bh.note)
            beam_mm = (bw.width_mm, bh.height_mm)
            notes += ['width: %s' % (bw.note or bw.source), 'height: %s' % (bh.note or bh.source)]
        d = self.dose(scan, points, unit=unit, absfac=absfac, monitor=monitor, shutter=shutter)
        sc = self.scans[scan]
        alpha = dosemod.point_incidence(sc.columns, sc.parameters, d.points)
        unit_name = 'photons' if d.unit == 'photons' else d.unit
        r = dosemod.dose_map(d.per_point, np.sin(alpha), beam_mm[0], beam_mm[1],
                             dosemod.EXTENT_SHARE if extent is None else extent,
                             dosemod.TOP_AREA_SHARE if top is None else top, unit=unit_name)
        r.notes = list(d.notes) + notes + r.notes
        return r

    def dose(self, scan, points=None, unit='photons', beam_mm=None, absfac=None, monitor='Monc', shutter='closed'):
        """The dose each point of ``scan`` gives the sample (lss_core.dose.scan_dose:
        photons, or Monc counts at 5 µA/V with the absorbers taken out; per mm²
        of footprint with ``beam_mm``, the beam's (width, height); ``shutter``
        'open' in fast mode, from the scan's per-point times)."""
        from . import dose as dosemod
        sc = self.scans[scan]
        pt = self.point_times(scan) if shutter == 'open' else None
        return dosemod.scan_dose(sc.columns, sc.parameters, points, unit=unit, beam_mm=beam_mm, absfac=absfac,
                                 monitor=monitor, scan=scan, shutter=shutter, point_times=pt)

    def mean_frame(self, frames):
        """The mean of ``frames``' images per monitor count (rows × columns, as
        read; no bad-pixel removal), e.g. for burn.signal_rows."""
        from .images import read_pilatus
        return np.mean([np.asarray(read_pilatus(f.path), float) / f.monitor for f in frames], axis=0)

    def spectra(self, scans, channels=None):
        """(scan, spectrum number, Data, Par) for every MCA spectrum of the
        fluorescence scans ``scans``, in the window's list order. Files of a
        multi-element detector give one spectrum per point, the elements in
        ``channels`` summed (None: all; lss_core.fluorescence.combine_channels)."""
        from .mcafiles import read_mca
        out = []
        name = os.path.basename(self.specfile)
        for n in scans:
            data, par = read_mca(os.path.join(self.mca_folder, '%s_%d_mca' % (name, n)))   # parsed once per file version
            spec = fluo.combine_channels([(data[j], par[j]) for j in range(data['NumOfScans'])], channels)
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
