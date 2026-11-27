# Scripting the reduction

The `lss_core` package reads SPEC files and images and reduces them
without the window and without Qt. It is the same code the window uses,
so a script gives the same numbers as the GUI. For reflectivity this is
checked byte for byte against files saved by the window
(`tests/test_api.py`).

Run scripts from the repository folder, or put that folder on `sys.path`.

## Reflectivity

```python
from lss_core.experiment import Experiment

exp = Experiment('sample_data/NX_school/2026sep/20260923')
result = exp.reflectivity([6, 7, 8, 9])
result.save('dppc')                     # dppc_ref.txt and dppc_rrf.txt
```

Options, with the window's defaults for Pilatus data:

| Option | Default | Window control |
|---|---|---|
| `slit=(21, 11)` | 21 × 11 pixels | Slit |
| `bg_offset=0.5` | degrees | BG offset |
| `direction='H'` | `'H'` or `'V'` | BG direction |
| `qc=0.0217` | Å⁻¹ | Qc |
| `qoff=0.0` | Å⁻¹, R/R_F only | Qoff |
| `norm_factor=None` | extra division | Norm. factor box |
| `rrf=True` | also compute R/R_F | R/RF box |
| `drops={0: [-1], 2: [0, -1]}` | none | "Drop" in the patch dialog, per join |
| `merge_repeats=False` | | "Merge" in the identical-scans dialog |
| `low_qz_slit=False` | | Low Qz Corr. |
| `merge=[[2, 3]]` | | groups merged in the identical-scans dialog |
| `points={7: [0, 1, 3]}` | all points | frames selected in the image list |
| `mask=[(7, 3), (8, 0)]` | none | dropped points kept in the workbook (F92; `lss_core.masks`) |
| `roi_bad_pixel_factor=10` | none | the Reflectivity tab's "Bad Pixel Correction fac": a bad-pixel pass over the ROI's three boxes (F95 B3, C62; off by default) |
| `bad_pixel_iterations=0`, `bad_pixel_factor=1` | | BPC iterations, factor |

`result` holds the per-scan points (`per_scan`, columns Qz, net signal,
error, signal, signal error, background 1, background 2), the scan order,
the patched curve before normalisation, `ref`, `rrf`, and the frames whose
beam was more than 2 pixels from its recorded position (`beam_offsets`),
and the point number of each per-scan row (`points`) with the masked
points left out (`masked`).

Dropped points as a mask over raw points (F92, 2026-11-24):

```python
from lss_core import masks, reflectivity as refl
from lss_core.workbook import Workbook
r = exp.reflectivity([6, 7, 8, 9])
removed, origins = refl.drop_points(r.per_scan, r.order, r.points, {1: [-1]})   # typed drops -> (scan, point)
wb = Workbook('20260923_reader.xlsx')
m = masks.load(wb).add(removed)                 # the mask kept in the workbook's Settings sheet
masks.save(wb, m); wb.save()
r = exp.reflectivity([6, 7, 8, 9], mask=m)      # the points left out from the start
masks.save(wb, m.restore_all()); wb.save()      # "Restore all"
```

`origins` is the (scan, point) of each row of the patched curve: every row
sits at one raw point's Qz.

One reader writes a workbook; a second opens it read-only (D1, 2026-11-25):

```python
from lss_core import readerlock
lock = readerlock.ReaderLock('20260923_reader.xlsx')
wb = Workbook('20260923_reader.xlsx', read_only=not lock.acquire())   # save() raises WorkbookReadOnly when read-only
lock.describe()        # 'this reader writes the workbook', or who has it open
lock.refresh()         # every 30 s while open; False if another reader took it meanwhile
lock.release()         # on close, or the one click that gives up the write access (owner, Q5)
lock.request_release(note='')   # a read-only reader asks the holder (writes <workbook>.lock.request)
lock.release_requested()        # the holder: the pending request (who, when, note) or None
lock.decline_request()          # the holder keeps it; the next acquire() clears any request left
```

Not yet available from scripts: background images, single-scan export,
GISAXS. (GID, cuts, peak fits and burn tests followed: sections below.)

## Qc and Qoff of R/R_F (2026-11-24, F79)

```python
from lss_core import fresnel
fresnel.subphase('NaCl 6 % (1.07 M)').qc          # 0.0221: Qc from the subphase's electron density
fresnel.qc_from_density(0.3333)                   # 0.02173 (water at 25 °C)
ref = exp.reflectivity([6, 7, 8, 9]).ref           # Qz, R, σ
p = fresnel.propose_qoff(ref[:, 0], ref[:, 1], ref[:, 2], qc=0.0217)
p.qoff, p.sigma, p.note                           # NX school: -0.00028 Å⁻¹ (the window's preset is 0)
exp.reflectivity([6, 7, 8, 9], qoff=p.qoff)        # R/R_F with it
```

`propose_qoff` proposes; nothing applies it. `method='edge'` (default) fits
the plateau and the drop at the edge, ln R = ln A + ln R_F(Qz + Qoff) +
a smooth factor, by robust least squares; `method='smooth'` minimises the
roughness of ln R/R_F near the edge (the owner's by-eye criterion), robust
to one or two outliers away from the edge. `fit_qc=True` (edge only) fits
Qc too and reports their correlation: near +1, because Qc and Qoff move
the edge together, so Qc is better taken from the subphase
(`fresnel.SUBPHASES`, each density with its source; or a typed density).
σ comes from a bootstrap over the counting errors and does not include the
biases the study found (`docs/studies/qoff/summary.md`): the Qz resolution
reads as a negative Qoff, and a wrong Qc moves Qoff one for one.

**Qoff and the Qz resolution together** (2026-11-27, hand-off 09, issue #154):

```python
d = exp.reflectivity([6], errors='budget').per_scan[6]          # one scan through the edge: Qz, R, σ
beta = fresnel.subphase_beta(fresnel.subphase('water'), 10.0)   # 5.24e-9: β = μλ/4π (xraylib's μ/ρ table)
f = fresnel.fit_edge_resolution(d[:, 0], d[:, 1], d[:, 2], qc=0.0217, beta=beta, energy_kev=10.0)
f.qoff, f.qoff_err, f.sigma_q, f.sigma_q_err, f.corr, f.chi2_dof, f.flags
f.fwhm, f.sigma_alpha_urad, f.qoff_deg, f.note                   # the resolution as FWHM and as an angle
```

It fits R = N · [R_F(Qz + Qoff; Qc, β) ⊗ Gauss(σ_Q)] · (1 + a u + b u²) over 0.6 Qc to 0.030 Å⁻¹ by a
soft-L1 loss. Qc and β stay fixed at the subphase's. The errors are a bootstrap scaled by √(χ²/dof) when
that is above 1. `roughness=3.0` puts a fixed Névot–Croce roughness in R_F (default 0). The flags are
'sigma_q at its bound', 'few points below the edge', 'few points above the edge', 'ill-conditioned' and
'bootstrap failures'. Nothing applies the value. The study is `docs/studies/qoff_resolution/summary.md`.
`fresnel_absorbing` and `fresnel_smeared` are its R_F, sharp and smeared.

## Fluorescence (XFNTR)

```python
exp = Experiment('sample_data/bu/2026sep/20260902')
flu = exp.fluorescence([74, 75, 76, 77, 78, 79], window=(1, 1000))
flu.save('zinc', x='qz')               # zinc_flu.txt, as "Export" in the MCA tab
```

`window` is the "Sum" range (energy with the file's calibration);
`monitor` is `'Monc'` (default), `'Monb'`, `'Mond'` or `None`;
`calibration=(c0, c1, c2)` overrides the file's; `absfac` (default
1.4247, 50 µm Al at 10 keV, `lss_core.absorbers`; at another energy use
`absorbers.factor_at(E_keV)[0]`, which the window writes in when "from E" sets
the field) is the transmission factor per absorber unit: normalised spectra
are multiplied by absfac**n, n the scan's absorber setting, which for
`getandsave_mca` scans is the last `#A` above them in the SPEC file
(`exp.scans[n].parameters['AbsorberFrom']` names that scan; no `#A` above:
no factor).
The normalised value is N · (t_real/t_live) · absfac**n / M per channel:
proportional to fluorescence per photon on the sample while the monitor
gain, energy and geometry stay the same (`physics_notes.md`, 2026-11-17;
`monitor_gain=True` also divides by the
`Monc` gain, i.e. by M·S/(5 µA/V), S from `#M Monc Gain` (the last one
above an MCA scan); scans whose gain is unknown get no factor and are
listed in `flu.unknown_gain`. `per_photon=True` divides by the incident
photons instead, N = (M − 50 Hz·t)·q(E)·S/(500 nA/V) (`lss_core.flux`,
xray_fluxor route D; includes the gain; bounds ±3.6 % below 13 keV, a
common scale not in the errors); scans where it is not known are listed
the same way). `flu.spectra` holds the
normalised spectra, `flu.rows` the [frame, Qz, energy, intensity, error]
rows. Checked byte for byte against the window's `_flu.txt` on synthetic
and real data.

## Error model

Both `reflectivity` and `fluorescence` take `errors=`: `'legacy'` (the
default, the window's numbers byte for byte) or `'budget'`, or a dict with
the monitor model:

```python
ref = exp.reflectivity([6, 7, 8, 9], errors='budget')    # monitor: Gaussian, 0.04 %
ref = exp.reflectivity([6, 7, 8, 9],
                       errors={'mode': 'budget', 'kind': 'student_t',
                               'sigma_scan': 0.00039, 'width': 0.94, 'nu': 4.0})
ref = exp.reflectivity([6, 7, 8, 9],
                       errors={'mode': 'budget', 'kind': 'counting', 'f': 0.0, 'sigma_dark': 0.0, 'g': 10.0})
ref = exp.reflectivity([6, 7, 8, 9], errors={'mode': 'budget', 'counting_scale': 1.12})
#   the counting part of each point's error x 1.12 (C63's within-scan scale; C64): an option, 1 by default
```

Budget applies the monitor's relative uncertainty once to each whole sum
of a frame (`lss_core/errors.py`, `docs/reports/error_propagation.md`).
The default, a Gaussian of 0.04 % at every count, and the Student t
(scale width × σ_scan, ν = 4) describe the present `Monc` electronics
(SR570 + V2F). The window's
Errors pane sets the same model, and the Script pane writes the matching
`errors=`.

## The Script pane

The window has a "Script" pane (bottom, next to Messages). Opening a
SPEC file, exporting a patched reflectivity and exporting fluorescence
intensities add the equivalent Python
there, with every setting, merge and drop the user made; running it writes
the same files. It is also written to the log.

## Lower-level pieces

| Module | What |
|---|---|
| `lss_core.experiment` | `Experiment`: scans, frames, reflectivity |
| `lss_core.reflectivity` | per-frame signal, scan ordering, merging repeats, drops, patching, normalisation, saving |
| `lss_core.fluorescence` | spectrum normalisation, window sum, `_flu.txt` |
| `lss_core.normalise` | monitor and absorber normalisation of a frame |
| `lss_core.stitching` | joining two curves (`join`), Fresnel reflectivity |
| `lss_core.images` | `read_pilatus`: fast, cached, bit-identical image reading |
| `lss_core.cache` | the memory cache (budget from `LSS_READER_RAM_CACHE_MB`) |
| `lss_core.numbers` | number parsing for SPEC/MCA text, without `eval` |
| `spec_routines.specread` | the SPEC reader (no Qt needed) |

## Absorbers and the known ratio (2026-11-18)

- `absorbers.calibrated(E_keV)`: the calibrated foils (9.70–10.30 keV),
  or None. Pass it as `absfac=` wherever a number was accepted
  (`exp.fluorescence(..., absfac=absorbers.calibrated(10.0))`); the
  factor at setting n is then `foils.factor(n)`.
- `foils.step(n_a, n_b)`: (ratio, relative error) between two settings.
- `exp.reflectivity(..., factors={join: (factor, error)})`: use these
  instead of the fitted patch factor at those joins (join 0 is the first
  pair). The window writes this when it used the known ratio.

## Workbook (2026-11-21)

    from lss_core import workbook
    wb = workbook.Workbook(workbook.path_for(spec, out_dir))      # <SPEC file>_reader.xlsx
    rid = wb.add_result('line cut', [11], cut.cuts[0], ['Qxy', 'I', 'dI'], label='S# 11 F# 20',
                        note='first look', fits=[('S# 11 F# 20', fits[0])])
    wb.save()
    wb.results(kind='line cut'), wb.data(rid), wb.fits(scan=11), wb.settings('peak_fit')

The window's Save buttons do the same (and every finished reduction is
saved automatically); the sheets are described in `lss_core/workbook.py`.

Series, stale results and remakes (2026-11-22):

    from lss_core import series, live
    info = series.scan_info(spec.Data, spec.Par)           # spec: a spec_routines.specread
    found = series.all_series(info)                        # lined and guessed series
    s = workbook.series_for([6, 7, 8, 9], found)           # the dict add_result(series=...) stores
    stale = wb.mark_stale(found, points={6: 21, 7: 21})    # {result id: why it is out of date}
    call, res, used, pts = live.remake(row['recipe'], scans, exp, then, now)   # parsed, not executed
    kind, items = live.item_for(call, res, used)
    X, Y, V, E = wb.map(rid)                               # a saved GID map, as a grid

## Peaks (2026-11-21)

    from lss_core import peaks
    res = peaks.fit(x, y, sigma)                          # find and fit, automatic
    res.peaks[0].centre, res.peaks[0].fwhm, res.peaks[0].area, res.chi2_dof, res.ok, res.message
    res = peaks.fit(x, y, sigma, peaks.FitOptions(shape='pseudo-voigt', background='quadratic', n_peaks=2))
    fits = cut.fit(peaks.FitOptions())                    # every cut of exp.cut(...), as "Fit peaks"
    ref, each = peaks.fit_series(energy, spectra, sigmas, peaks.FitOptions(centres=(6.93,)))   # MCA series
    line = peaks.fit_lines(energy, counts, [6.40, 7.06], sigma)
    shape = peaks.fit_scan(x, y, sigma)                   # 'peak', 'edge' or 'box' (SpecPlot); fit_edge for half-cuts

`fit_series` fits the sum of a series of spectra for the lines' positions
and widths, then each spectrum with those fixed (owner's rule for MCA
series); each spectrum by Poisson maximum likelihood (`weights='poisson'`,
the default since 2026-11-24; `weights='data'` for least squares weighted
by the σ given, as before). `peaks.find_peaks` alone gives the candidates.
"Fit peaks" in the window writes the `cut.fit(...)` call to the Script pane.

The MCA tab's "Fit lines" fits each spectrum two ways (F110, the owner's
decision of 2026-11-26, revised the same day), and so can a script:

    from lss_core import fluorescence as fl
    both = fl.fit_line_series(flu.spectra, peaks.FitOptions(centres=(8.64,), x_range=(8.3, 8.9)))
    both['each'][k].peaks[both['j']].area / both['step']   # the reader's fit of spectrum k: the default (_flu.txt)
    both['xeray']                         # one XeRayFit per spectrum, beside it (_flu_xeray.txt)
    r = fl.xeray_fit(energy, y, sigma, x_range=(8.3, 8.9), centre=8.64)   # XeRay on one spectrum
    r.area, r.area_err, r.centre, r.fwhm, r.ok, r.message

The reader's fit is Poisson, with the Si escapes stripped
(`strip_escapes=True`) and the line's position and width from the sum of
the series; `detector_width=True` (with `noise_kev`) fixes the width at the
detector model's instead, which needs the detector's own noise. XeRay is one
Gaussian on a straight line by unweighted least squares, with the error
√(counts in the window): too small where the background is large (the XRF
shootout's pull SD 1.92). `fl.merge_rows` merges every (I, σ) pair of a row.

An ORSO file (the format v1.2, via orsopy; 2026-11-27, F25), as Export writes it with "+ ORSO":

    from lss_core import orso
    orso.write_ort('run.ort', ref.ref, spec_path, [6, 7, 8, 9], 1.23984, owner_name='...', owner_affiliation='...',
                   sample_name='dppc', corrections=['...'], call='ref = exp.reflectivity([6, 7, 8, 9], ...)')

A cut of a GID map in Q, as the window's GID cut (2026-11-27, #145):

    gid = exp.gid([11], axes='Q')
    cut = gid.cut('Q H', (0.05, 0.10))     # (N, 3): Qxy, the sum over the Qz rows in the range, its error; 'Q V' along Qz

One scan's column against another, as the SpecPlot saves it (2026-11-27, #145; the recipe of a saved
SpecPlot curve, remade live when the scan gains points):

    c = exp.curve(4, 'sh', 'Apex2', monitor='Monc', fit=True)   # c.x, c.y, c.err, c.columns; c.fit: the scan-shape fit

From a fluorescence result, as the window's "Fit lines" (2026-11-27, #145; Export after Fit lines writes
this line to the Script pane):

    flu = exp.fluorescence([3], window=(5.6, 7.2))
    flu.fit_lines(peaks.FitOptions(background='quadratic', n_peaks=1, x_range=(5.6, 7.2)))   # rows: the reader's fit, then XeRay's
    flu.save('zinc', x='qz')            # zinc_flu.txt (the reader's fit) and zinc_flu_xeray.txt

## Burn tests (2026-11-21)

```python
burn = exp.burn(15)                            # NX school: a GID burn scan
burn.rows                                      # (46, 486): the rows of the mean frame's signal (Q-BURN-6)
exp.burn(15, rows=None)                        # every detector row, as before 2026-11-24; or rows=(first, last)
print(burn.summary())                          # verdicts, best models, the 5 % time
burn.trends['centre'].table()                  # every model: chi2/dof, AICc, Δ, weight, parameters
cols, values = burn.data()                     # time and each quantity with its error
burn = exp.burn(14, estimator='moments', time='clock', threshold=0.10, qxy_range=(1.40, 1.52))
d = exp.dose(14)                               # photons each point gives the sample (lss_core.dose, F98)
d.per_point, d.cumulative(), d.total(), d.unit, d.notes, d.bounds
exp.dose(14, unit='monitor')                   # Monc counts at 5 uA/V with the absorbers taken out: M/(A g)
from lss_core import reciprocity               # beam damage or the sample by itself? (F76)
v = reciprocity.dose_or_time([reciprocity.from_result(exp.burn(n), 'centre') for n in (14, 15)])
v.verdict, v.beta, v.beta_ci, v.weight_dose    # NX: 'neither', 0.85 [0.80, 0.89], 1.00 (on counting errors alone)
reciprocity.dose_or_time(burns, strip_scatter=0.88 / 3600)   # admit the strips' own scatter (C54: 88 %/h)
reciprocity.dose_or_time(burns, strip_relative=1.13)          # as a share of each rate: C54's repeats fit this better
reciprocity.dose_or_time_rates(fluxes, rates, errors)         # from a table of drift rates (any unit, the same for all)
reciprocity.strip_scatter_fit(groups, relative=True)          # ρ (or τ) by REML from repeats: [(rate, σ), ...] per flux
exp.dose(14, beam_mm=(2.0, 0.1))               # photons/mm2 of footprint, for a beam of that width and height
exp.dose(14, shutter='open')                   # fast mode: the beam also between points (from the point times)
h = exp.beam_height(near=7)                    # the beam's height from the height scans' rising edge (#60's rule)
h.height_mm, h.source, h.note, h.refused       # 1.0645 x the median rising FWHM; or the default 0.040 mm (10 keV, S1 <= 0.04)
exp.dose(7, beam_mm=(1.0, h.height_mm))        # the peak dose per mm2 (the width typed: it is not measured)
burn = exp.burn(14, axis='dose')               # trends against the dose; the limit is a dose
r = exp.dose_summary(14, beam_mm=(1.0, h.height_mm))   # the dose as peak and average, the peak split (F109)
r.peak, r.average, r.top, r.rest, r.area_mm2, r.text() # NX 14: 1.54e12 peak, 6.0e11 over 43 mm2 (90 % of the dose)
exp.dose_summary(14, beam_mm=(1.0, 0.033), extent=0.5)  # the extents: the area that received 50 % of the dose
w = exp.beam_width()                           # sqrt(2 pi) sigma_x from S1 horizontal slit scans; else the 1 mm prefill
w.width_mm, w.fwhm_mm, w.source, w.profiles, w.refused
exp.beam_width(scans=[31, 32], counter='Pilatus', monitor=None)   # named scans; the counter as recorded
from lss_core import dose
dose.dose_map(per_point, sin_alpha, width_mm, height_mm)   # the same from any doses and incidences
burn.dose, burn.dose_unit, burn.dose_scale     # the axis: NX 14 in '1e+12 photons' (dose_scale 1e12), 28.9 at the end
```

Reflectivity geometry (Det_Th 0): the Ref Patch ROI per Monc (`slit`,
`bg_offset`, `direction`); GID: the strongest peak's integrated intensity,
position and FWHM per Monc (`estimator` 'stretched' (default; the names 'template', 'split' and
'split_fixed' of before 2026-11-27 still work), 'moments'
(legacy arithmetic) or 'fit' with `fit=FitOptions(...)`; or, P44, not yet in
the burn dialog, 'separated' and 'separated_held': the stretched reading with the broad
shoulder split off and held unstretched, its amplitude free per frame
(then the quantity 'shoulder' as well) or held at 1, and
`lss_core.burn.frame_model(burn.reference, burn.frame_fits[k], x)` the
curve fitted to frame k; `qxy_range` to
choose the peak; `rows` the pixel rows summed: 'mean', the default since
2026-11-24, where the mean frame's signal is; None, all; or (first, last)). Each quantity over `time`
('exposure' default, or 'clock') is compared over `models`
(`lss_core.trends.MODELS`) by AICc; `trend_errors` 'scatter' (GID default)
or 'given'. `lss_core.trends.compare(t, y, sigma)` does the comparison for
any series.

A first frame more than 5 σ and 20 % from the median of the next three (intensity, FWHM) is
flagged, not left out (#188): `burn.first_frame` holds `{quantity: {'ratio', 'z', 'with', 'without'}}`,
the last two the linear change over the burn (change, σ) with every frame and without the first, and
`burn.notes` says it. `lss_core.burn.first_frame_check(x, y, sigma, span)` checks any series.

## Reflectivity patching and uncertainty (2026-11-22)

```python
from lss_core import patching, absorbers
r = exp.reflectivity([6, 7, 8, 9], errors='budget')
scans = patching.scans_from_reflectivity(r)            # each scan's Qz, net signal, error
res = patching.chain(scans)                             # joint fit at each join (order 4, R/R_F, 2 points either side, the guard ladder)
[(j.factor, j.err, j.chi2 / j.dof, j.flags) for j in res.joins]
res.phi, res.Sigma                                      # each scan's log factor to the first, and their covariance
st = res.stitch(scans)                                  # every point on the first scan's scale
st.sigma_total(), st.covariance('log')                  # per-point error with the factors'; the N x N covariance
prior = patching.known_steps(absorbers.calibrated(10.0), [41, 31, 24, 18])
res = patching.chain(scans, prior=prior, monitor_ratios=[1.005, 4.35, 1.32])   # foil prior where it applies
```

`patching.interp_factor`, `coincident_factor` and `global_fit` are the
alternatives the survey compares (`tests/tools/ref_patch_survey.py`,
hand-off 08). **`global_fit` is experimental:** it has no guard ladder and
applies one χ² inflation to every join, so where one window cannot follow
the curve that join is biased and every join's error is inflated (−3.4 %
and about ten-fold on a 100 Å film at NX steps; `docs/reports/patch_demo.md`,
figure 2). Nothing in the reader calls it; use `chain` (with `prior=` for
correlated foils). `lss_core.uncertainty` holds the method-free pieces
(`chain_covariance`, `steps_to_phi`, `combine`, `total_sigma`,
`stitched_covariance`, `pulls`). The legacy patch and export are
unchanged.

### Exporting the covariance for model fits (2026-11-22)

```python
r = exp.reflectivity([6, 7, 8, 9], errors='budget')
r.save('dppc')                                   # unchanged: dppc_ref.txt, dppc_rrf.txt
r.save('dppc', covariance='sidecar')             # + dppc_ref.cov.json, dppc_rrf.cov.json (the files byte for byte)
r.save('dppc', covariance='contract')            # hand-off §2.5: error column √diag C + sidecars + *_legacy.txt
r.save('dppc', covariance='contract', method='stitched', combined=True)   # points as measured; + dppc_ref.json (§2.6)
ref, rrf = r.covariance()                        # CovData of the patch r was made with (r.method: 'joint' by default)
                                                 # .take/.cut/.scale/.average/.concat; methods 'legacy', 'corrected', 'stitched'

from lss_core import gls
sc = gls.load('dppc_rrf.cov.json')               # refuses what XModFit refuses (hand-off §2.3)
d = np.loadtxt('dppc_rrf.txt'); assert not sc.match_problems(d[:, 0], d[:, 1])
fit = gls.fit(sc, model, p0)                     # model(q, *p) -> R/R_F; log space, free overall scale
fit.params, fit.errors, fit.chi2 / fit.dof, fit.shifts['stitch']     # shifts: each scan's fitted level error
gls.fit(sc, model, p0, mode='diagonal', yerr=d[:, 2])   # the same fit with the file's errors, to compare
gls.chi2(sc, model_curve)                         # GLS chi2 of a curve (Woodbury)
```

Without Experiment: `covariance_export.tracked_chain(per_scan, order,
drops, factors, method)` (the patch replayed: 'joint' or 'legacy'),
`corrected_chain(...)`, `joint_covdata(...)` (stitched points), then
`finish(cd.covdata(), qc, qoff, norm_factor, rrf)` and `save(name, ref,
rrf)`. Why and what it changes: `docs/reports/downstream_covariance.md`.

## Cuts (2026-11-18)

    cut = exp.cut([1, 2], 'Pix H', (90, 110))            # one cut per frame
    cut = exp.cut([1, 2], 'Q H', (0.005, 0.02), summed=True)
    cut.save('dppc_')      # dppc_S# 1_F# 0_cut.txt ... or dppc_S# 1_sumcut.txt
    cut = exp.cut([7], 'Q V', (-0.005, 0.005), axes='beta-alpha')   # diffuse: I vs beta - alpha (F97)
    cut = exp.cut([7], 'Pix V', (90, 104), axes='beta')            # or 'Qz'; horizontal cuts: axes='Qxy'
    from lss_core import cuts
    cuts.covered_range('Q V', geometry, (487, 195))   # the Qxy the detector covers (geometry: cuts.Geometry)
    cuts.centred_range('Q V', geometry, 10)           # a band of 10 columns either side of the beam

Directions as the window lists them: 'Q H', 'Q V', 'Pix H', 'Pix V';
`axes` 'Pixels', 'Angles' or 'Q' for the pixel cuts, or for any cut a
diffuse-cut axis (F97, 2026-11-24): 'beta', 'beta-alpha' (α from Qz),
'Qz' for vertical cuts and 'Qxy' (exact) for horizontal ones; the
intensities are the cut's own, the x axis converted from its pixels. Frames are divided by
the monitor and multiplied by `absfac` (a number or
`absorbers.calibrated(10.0)`) first. `points`, `errors`, `monitor_gain`, `per_photon`,
`distance` and `db_pos` (typed geometry), `pinhole`, and the bad-pixel
settings work as in the window. Background-subtracted cuts are not
scriptable yet. Exporting a cut in the window writes this call.

## Pinhole GID (2026-11-18)

    import sys; sys.path.insert(0, 'tests/tools')
    from pinhole_frames import frames_for          # frames from a SPEC file, as the window reads them
    from lss_core import pinhole
    frames = frames_for('sample_data/NX_school/2026sep/20260923', [11])
    two_theta, beta, I, sigma, info = pinhole.level_map(frames, 15, 486)

`level_map` bins every usable column at its own 2θ (one Qz level);
`info` holds the column response, the scan factors, counts used and frames
per bin.

## GID maps (2026-11-19)

    from lss_core.gid import GIDParams
    gid = exp.gid([11, 12])                                  # pinhole geometry, as the window
    old = exp.gid([11, 12], params=GIDParams(pinhole=False)) # the legacy 3-column patch
    gid.save('dppc', axes='Angles')                          # the window's three "Save GID" files
    q = gid.products('Q')                                    # x, y, data, err, h, v, vc as plotted

The window's "GID Patch" (`relax=True`: "GID Patch Relax", the larger Q
grid), with the GID worksheet's settings in `params` (every field of
`GIDParams`; `columns` is the window's H slit field). `points`, `db_pos`,
`errors` (legacy patch only) and the bad-pixel settings as for cuts.
Distance from single frames: `from lss_core import gid, pinhole;
level = gid.pinhole_frames(exp.gid_frames([11])[0], gid.GIDParams())[0];
cal = pinhole.calibrate_distance(level)` (`cal.distance_mm`, `.error_mm`,
`.reliable`, `.why`), then `GIDParams(pinhole_distance_mm=cal.distance_mm)`.
`GIDParams(response='physical')` computes the response from the geometry and
a Gaussian beam (`beam_fwhm_um`, `beam_centre_mm` fitted unless given;
`gid.info['levels'][k]['physical']` holds the beam found), and
`GIDParams(apply_joins=False)` leaves the data as collected (factors only in
`gid.joins`, each with `applied`). `GIDParams(response='beam')` fits the pinhole response along the beam axis
instead of per column (for a narrow beam); `gid.info['levels'][k]` then has
`beam` (profile, centre and FWHM on the sample, mm) and, always,
`two_theta_resolution_deg`. `GIDParams(unmatched_levels='unscaled')` (a
stopgap, 2026-11-26) joins a level that shares no β with the levels below as
collected instead of refusing; `gid.unscaled_seams` lists each such seam (β gap,
the intensity ratio across it) and `gid.save` then writes a `#` line saying so
(tradeoffs: `docs/studies/gid_unscaled_seams/summary.md`). `gid.joins` is the worksheet's join table, `gid.levels` its level list,
`gid.info` the pinhole details. "Save GID" writes the equivalent call to
the Script pane; running it writes the same files byte for byte (both
geometries, both axes, relaxed grid, typed columns, some frames:
`tests/test_gid_script.py`). Background-subtracted frames are not
scriptable yet. Window and script share `lss_core/gid.py` (the joins,
`calArea`, the map products and the save were moved there unchanged).

## Multi-element detectors (2026-11-19)

    flu = exp.fluorescence(scans, window=(5.1, 5.4))               # all elements summed (EXAFS)
    flu = exp.fluorescence(scans, window=(5.1, 5.4), channels=[4])  # one element (XFNTR: the central one)

Per-point MCA files of a multi-element detector hold one block per element
(`#@CHANNEL`); `channels` selects the elements summed into one spectrum per
point (`exp.spectra(scans, channels)` gives them). Single-element files
are not affected.

## Merging fluorescence points (2026-11-19)

    flu = exp.fluorescence([2, 3, 4, 12, 13, 14], window=(5.6, 7.2))
    flu.merge()                    # default window: 0.1 × the Qz grid step
    flu.merge(0.03, x='qz')        # or a typed window, as in the window's Merge dialog
    flu.save('out', x='qz')

The window's Merge: points closer than the window on the x axis are
merged with weights y/σ² (total counts over total monitor). On the Qz axis
the Qz jitter (3e-5 1/Å) is added to the errors. Choose scans of one run,
wavelength, sample and signal shape; the reader does not check.

## Per-point times (2026-11-19)

    t = exp.point_times(11)
    t.format          # 'new' (Tstart, Tend), 'old' (Epoch) or 'none', from the #L line
    t.start           # Unix s when each point's counting began (old files: #D + Epoch differences, ~1 s)
    t.end, t.overhead # new files only: Tend, and Tend - Tstart - Seconds
    t.since_series    # s since the macro started (new: Tstart - SeriesT0; old: from the inferred series' first #D)
    t.notes           # how each was obtained

Old files: the scan's #D is the anchor and Epoch only spaces the points
(Epoch's base is wrong; #E + Epoch is never used). #D is local time; its
zone comes from the file header's #E/#D pair (UTC−5 on the NX file).
Missing columns are noted in `t.notes`, never an error.

## Photons per second (2026-11-18)

    from lss_core import flux
    best, low, high, flags = flux.photons_per_second(counts, seconds, 10.0, 5e-6, lane='MonC')

Photons/s at the ion chamber's exit plane (xray_fluxor hand-off, route D);
`flags` lists what was assumed (dark 0, 24.9 °C, 98.99 kPa unless given).

## Sample-height scans and the sample timeline (2026-11-24)

    from lss_core import peaks, timeline
    from lss_core.experiment import Experiment
    exp = Experiment('20260923')
    sc = exp.scans[10]
    x = sc.columns[next(iter(sc.columns))]                 # Sample_H, mm
    f = peaks.fit_super_gaussian(x, sc.columns['Pilatus'], sc.columns['Monc'])
    print(f.summary('µm', 1000.0))     # FWHM 81.07 ± 0.53 µm, p 3.38 ± 0.082 (χ²/dof 3.1; Gaussian 28)
    tl = timeline.build(exp)
    tl.of_kind('set-zero')             # 'set Sample_H 0: new sample?' after scan 4
    tl.steps                           # sx moves between scans, from #P
    tl.heights                         # every sh scan with its fit

`fit_super_gaussian` (F78) fits A exp(−|(h − h0)/w|^p) + b; FWHM =
2w(ln 2)^(1/p), p = 2 a Gaussian, larger p flatter. It refuses a scan with
no reflected beam. `timeline.build` (F83 phase 1b) gives scan spans
(start, end, kind), events read from the file's dated `#C` lines (`set`
resets, aborts, macro files), SPEC session restarts, gaps, motor steps,
sh scans with their fits, and the mnemonic table (sh → Sample_H). Times
are Unix seconds (UTC). Research: `docs/gui/timeline/research.md`.

Notes on the timeline are workbook Saved rows of kind `note`:
`timeline.note_item(t0, label, text, scans, event, answer)` gives the
`Workbook.add_result` keywords, `timeline.notes_from_rows(wb.results('note'))`
reads them back, and `timeline.answers(notes)(event)` gives the latest
answer to a "set sh 0: new sample?".

## Comparing saved curves (2026-11-24)

    from lss_core import compare, workbook
    wb = workbook.Workbook('20260923_reader.xlsx')
    curves = compare.order(compare.entries(wb), 'time')      # or 'series', 'sx' (pass positions={scan: sx})
    q, r, s = compare.ratio(curves[0].data, curves[1].data)   # the second over the first, on the first's Qz

`entries` reads the saved reflectivities (label 'R', or 'R/RF') with their
data. `ratio` interpolates the second curve in log R against log Qz and adds
the relative errors in quadrature.

