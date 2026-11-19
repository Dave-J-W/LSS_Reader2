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
| `bad_pixel_iterations=0`, `bad_pixel_factor=1` | | BPC iterations, factor |

`result` holds the per-scan points (`per_scan`, columns Qz, net signal,
error, signal, signal error, background 1, background 2), the scan order,
the patched curve before normalisation, `ref`, `rrf`, and the frames whose
beam was more than 2 pixels from its recorded position (`beam_offsets`).

Not yet available from scripts: background images, single-scan export,
GID, GISAXS, cuts, burn tests, peak fits. They follow in Stage 2.

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

## Cuts (2026-11-18)

    cut = exp.cut([1, 2], 'Pix H', (90, 110))            # one cut per frame
    cut = exp.cut([1, 2], 'Q H', (0.005, 0.02), summed=True)
    cut.save('dppc_')      # dppc_S# 1_F# 0_cut.txt ... or dppc_S# 1_sumcut.txt

Directions as the window lists them: 'Q H', 'Q V', 'Pix H', 'Pix V';
`axes` 'Pixels', 'Angles' or 'Q' for the pixel cuts. Frames are divided by
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
`GIDParams(response='beam')` fits the pinhole response along the beam axis
instead of per column (for a narrow beam); `gid.info['levels'][k]` then has
`beam` (profile, centre and FWHM on the sample, mm) and, always,
`two_theta_resolution_deg`. `gid.joins` is the worksheet's join table, `gid.levels` its level list,
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

