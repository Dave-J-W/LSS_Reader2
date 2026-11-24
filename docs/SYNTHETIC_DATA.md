# Synthetic data: catalogue, how to use it, what is missing

Written 2026-11-22 (owner: "Spearhead a synthetic data revolution. Catalog
all the synthetic data generation we have, the unmet needs, and then fill
the gaps. Reflectivity synthetic data should be first made in the reduced
form, rather than images. Kiessig fringes and the response of water-air
interface are critical components of the synthesis. Keep notes for other
agents to use the generators for testing.").

Two places hold generators:

- `tests/synth.py`: the original writers (SPEC text, Pilatus TIFF, MCA)
  and the small data sets the GUI tests and fixtures use. **Its outputs
  must not change**: the legacy export fixtures, the crash baselines and
  many tests depend on them byte for byte. Add new generators elsewhere.
- `tests/synthetic/` (new, a package; import as `from synthetic import
  xrr` from any test, since `tests/` is on `sys.path`): generators with
  known truth, GUI-free, each with its own tests (`tests/test_synthetic_*.py`).

Throughout, "measured" means a number computed here by running the code;
"read" means taken from a document or code without running it; values
"from memory" are literature values not checked against the source in this
session (the NIST site could not be reached).

## 1. Quick start

```python
from synthetic import xrr, xrr_scans as xs, xrr_images as xi

profile = xrr.dppc()                                   # or bare_water(), film(100.0)
data = xs.measure(profile, xs.nx_like_plan(), seed=3)  # reduced scans, Poisson noise
data.per_scan[1]          # (N, 7) Qz, net, σ, S, σ_S, B1, B2 per Monc: as ReflectivityResult.per_scan
data.true_join_factors()  # {join: factor} the legacy chain should find
data.nominal_join_factors()   # {join: (factor, rel. error)}: the foils' known ratios
data.truth(qz)            # R(Qz) the scans were drawn from

from lss_core import reflectivity as refl
joined = refl.patch(data.per_scan, data.order)         # the reader's legacy chain
spec = xi.render(data, tmp_path, 'xrr')                # SPEC + pilatus/ frames: the whole GUI path
```

`measure(..., expected=True)` gives the expectations (no noise) for exact
checks; `seed` may be a `numpy.random.Generator` for Monte Carlo loops
(1.3 ms per NX-like data set, measured).

## 2. Catalogue

### 2.1 New (`tests/synthetic/`)

| Module | Makes | Physics | Tests |
|---|---|---|---|
| `xrr` | R(Qz), R/R_F, ρ(z) of layered liquid interfaces | Fresnel with absorption; Parratt recursion (dynamical); Névot–Croce or Debye–Waller roughness per interface; capillary-wave σ; kinematic master formula; Gaussian Qz resolution; presets bare water, DPPC, film | `test_synthetic_xrr.py` |
| `xrr_scans` | Reduced reflectivity scans as measured, with truth | counts = R·flux·t·slits/attenuation; calibrated foils; Monc/Monp; flat background through the foils; the reader's ROI boxes; Poisson; faults (P29 monitor, foil off) | `test_synthetic_xrr_scans.py` |
| `xrr_images` | SPEC file + Pilatus TIFFs from those scans | box sums reproduce the reduced rows exactly | `test_synthetic_xrr_images.py` |
| `gid_levels` | Legacy GID frames (in memory) with 1–3+ Qz levels and known map T(2θ, β) | the legacy patch's geometry, area and polarisation corrections put in so the patch can divide them out | `test_synthetic_gid_levels.py` (P36, P37 strict xfails) |
| `burn_profiles` | GID burn profiles over time with a stated change | fade, broaden at constant area, shift, fade under a shoulder, rising floor, none; Poisson on counts | `test_synthetic_burn_profiles.py` |
| `xfntr` | XFNTR yield curves, MCA spectra and files | \|T\|², penetration depth 1/Im Q_s, surface + bulk ions, escape absorption, footprint seen; Si-detector resolution FWHM(E); Kα/Kβ, elastic, background | `test_synthetic_xfntr.py` |
| `mca` (2026-11-23, F90) | MCA spectra of fluorescence lines with the beam's scatter under them, every part kept apart per channel, with known truth; MCA files for the reader (`write_dataset`) | Kα1/Kα2/Kβ1 at X-ray Data Booklet energies (Fe, Ni, Cu, Zn, Ga, Br), excited above their K edges; Rayleigh; Compton at E0/(1+(E0/mc²)(1−cos 2θ)) with a hydrogenic Doppler profile (valence) and an O 1s core wing cut off at E0 − 0.532 keV (impulse approximation); Si-detector photopeak (Fano), exponential tail and shelf (Hypermet), Si K escape peaks at E − 1.740 keV (Reed's fraction, 0.10 % at 10 keV); background; calibration offset and gain error; Poisson | `test_synthetic_mca.py` |
| `growing` | A finished data set replayed into another folder line by line, images late | SPEC writes line by line; images lag; MCA files with their scan | `test_synthetic_growing.py` |
| `tests/tools/synthetic_dataset.py` (2026-11-23, a writer, not a generator) | A data set on disk for the reader to open (Tools > Synthetic data sets): `--kind xrr` (four NX-like scans of `--truth` film/water/DPPC, `--thickness`, `--counts`, `--monitor real\|poisson`, `--fault none\|slits\|foil`, rendered by `xrr_images.render`, with `truth.csv` and `truth.json` holding R(Qz) and the true join factors), `--kind xfntr` (18 spectra, `xfntr.measure`), `--kind burn` (`synth.make_burn_dataset`) | the generators' own; choices made here (assumptions, demonstration only): `slits` = Monc registers 70 % of the slit change at scans 3–4 (P29 measured ×1.55–1.62 for ×2.0–2.3), `foil` = scan 3's foils transmit 2 % less than calibrated | `test_synthetic_dataset.py` |

### 2.2 Old: `tests/synth.py`

| Name | Makes | Physics / truth | Used by |
|---|---|---|---|
| constants | λ = 1.24 Å, S2D 600, S7D 300 mm, beam (97, 100) in the header, 487 × 195 frames, `ABSFAC` 1.42 (not the reader's 1.4247), `QC` 0.0217, `MONITOR` 1e5, `MOTORS` | — | everywhere |
| `spec_scan`, `write_spec`, `ref_rows`, `REF_COLUMNS` | SPEC text of a scan (header `#S #D #G0 #Q #P0 #W #A #B0 #B1 #N #L`), the file | layout reverse-engineered, then checked on the NX header | ~25 test files |
| `reflectivity` | Fresnel R(Qz), no absorption, no roughness | exact for a sharp interface | `make_dataset`, `_ref_scan`, `test_known_ratio_patch` |
| `pilatus_image`, `write_pilatus_tif` | Gaussian peak (σ 2 px) on a flat background, rounded, no noise; TIFF with the reader's rotation undone | — | GUI tests, `test_twod_detector` |
| `write_mca` | one MCA file of several spectra (CTIME 1 1 0.9) | — | `make_dataset`, live tests |
| `make_dataset` | the `dataset` fixture: refl scans 1–2 (scan 2 through one foil, ×1/1.42), MCA scan 3, motor scan 4 | peaks ∝ Fresnel; no noise | conftest, GUI workflows, legacy fixtures |
| `make_identical_scans_dataset` | scans 1–2 plus a repeat of 2 at ×1.02 | — | identical-scans dialog |
| `make_absorber_patch_dataset` | two refl scans at absorbers n_a, n_b through the calibrated foils, Poisson, `Monp` with a jump | known foil ratio, P29 jump | known-ratio patch tests |
| `make_burn_dataset` | one refl scan, 21 frames, peak ∝ exp(−t/400 s) | known τ | `test_burn`, `test_burn_trends`, live tests |
| `XF_*`, `xfntr_yield`, `xfntr_spectrum`, `make_xfntr_dataset` | XFNTR scans (one MCA file per Qz), known line counts | yield a smooth hump, **not physical** (see `synthetic.xfntr`) | `test_xfntr`, `test_fluorescence_absorber`, `test_mca_*` |

### 2.3 Old: helpers inside test files and tools

| Where | Makes | Notes |
|---|---|---|
| `test_series.py` `_scan`, `_groups` | SPEC scans with `#U Series` lines, abort comments, `#U SeriesMacro` | series inference (F39) |
| `test_burn_trends.py` `_gid_profiles` | GID burn profiles (decay, shift, grow), Gaussian noise | generalised by `synthetic.burn_profiles` (same defaults) |
| `test_gui_live.py` `_split`, `_ref_scan` | a SPEC file cut after k data lines; a refl scan's text + frames | `synthetic.growing` does the general case |
| `test_gid_scan_join.py` `_split`, `_chain` | **real** NX scan 11 split into 2–3 scans, one × s | semi-synthetic: real frames, known scale |
| `test_pinhole.py` `_geom`, `_frames`, `_level`, `_two_levels`, `_beam_lit`, `_physical_lit` | pinhole-geometry frames (exact per-pixel angles) with intensity(2θ, β), column response, wrong distance, two Qz levels with factor 1.25, Gaussian beam light | in memory (`PinholeFrame`); the reference for exact-geometry GID |
| `test_error_budget.py` `_frame`, Monte Carlo | Poisson peak frames; flat frames with a noisy monitor | monitor error models (P2) |
| `test_known_ratio_patch.py` `_curves` | two reduced curves, Fresnel × 100 and × 7, 5 % Gaussian noise | the first reduced-form synthetic; `xrr_scans` supersedes it |
| `test_foil_fit_from_joins.py` `_write` | joins table from the true foils, 0.2 % noise, a monitor fault | foil fit |
| `test_mca_merge.py` `_rows` | repeated XFNTR rows with Qz jitter | merge rule |
| `test_peaks.py`, `test_trends.py` | Gaussians on slopes with Poisson noise; trends with Gaussian noise | peak and trend fitting |
| `test_lss_core.py`, `test_twod_detector.py`, `test_monitor_gain.py`, `test_interp_compat.py` | random images, grids | readers, arithmetic |
| `tools/monitor_noise_mc.py` | Monte Carlo of monitor normalisation | `docs/reports/monitor_noise.md` |
| `tools/pinhole_beam_profile.py` | frames lit by a Gaussian beam | C23 |

The other tools in `tests/tools/` read real data only.

## 3. Reflectivity (reduced first)

### 3.1 `synthetic.xrr`: the interface

| Quantity | Default | Source |
|---|---|---|
| r_e | 2.8179403262e-5 Å | CODATA 2018 |
| energy, λ | 10 keV, 1.239842 Å | beamline default; hc = 12.39842 keV·Å as `lss_core.absorbers` |
| ρ water | 0.334 e/Å³ | 1 g/cm³ → 0.3343 (computed) |
| Qc = 4√(π r_e ρ) | 0.02175 Å⁻¹ | computed; the reader's default 0.0217 |
| β water | 5.24e-9 | μ/ρ = 5.329 cm²/g at 10 keV (NIST SRD 126, from memory), 0.997 g/cm³ |
| σ water | 3.0 Å | inside the measured 2.5–3.3 Å (Braslau et al. 1985, from memory); not a fit |
| capillary σ | √(σ0² + kT/2πγ ln(q_max/q_min)); kT/2πγ = 0.910 Å² | γ = 71.97 mN/m, 298.15 K; q_max = 1, q_min = 1e-7 Å⁻¹ (assumed) → 3.83 Å |
| DPPC tails / heads | 16.0 Å, 0.320 e/Å³ / 9.0 Å, 0.460 e/Å³ | representative of Helm et al. 1987, Kjaer 1994 (from memory); consistent with the electron count at 48 Å² per molecule (computed) |
| film | 100 Å, 0.383 e/Å³ | PMMA-like (computed from 1.18 g/cm³); a test object |

Roughness: Névot–Croce (default), factor exp(−Q_j Q_{j+1} σ²/2) on each
interface's Fresnel coefficient; `roughness='debye-waller'` uses
exp(−Q_j² σ²/2); `'none'`. For one interface Névot–Croce gives exactly
R = R_F exp(−Qz Re(Q_s) σ²) (tested), i.e. exp(−Qz²σ²) far above Qc and
almost no damping below it.

```python
w = xrr.bare_water()                        # Profile
w.reflectivity(q)                           # Parratt, with roughness
w.reflectivity(q, resolution=(0.001, 0.0))  # Gaussian FWHM dq + dq_rel·Qz
w.fresnel(q)                                # sharp, with β; absorption=False for the reader's form
w.rrf(q)                                    # R / R_F(sharp, with β)
w.kinematic(q)                              # master formula
xrr.Profile([xrr.Layer(30, 0.36, 3.0), xrr.Layer(12, 0.31, 3.0)])   # any slab stack on water
xrr.film(150.0).density(z)                  # ρ(z), error-function interfaces
```

Measured (tests): R_F = 1 below Qc without β and 0.95–1 with it; R_F →
(Qc/2Qz)⁴ with a correction ≲ 1.5 (Qc/Qz)²; Kiessig period 2π/d within
2 % for d = 60–200 Å (measured 0.0624–0.0630 against 0.0628 for 100 Å);
kinematic vs Parratt for a weak-contrast bilayer: 2.5 % at 8–25 Qc, 1.1 %
at 30–50 Qc (refraction shifts the phases by about Qc² d / 2Qz); a
resolution of a third of the fringe period raises the minima by 11–17 %.

### 3.2 `synthetic.xrr_scans`: the measurement

Model per point (full statement in the module docstring): reflected counts
N = R·flux·t·g·trend/A, A = calibrated-foil attenuation × `attenuation_error`;
background per pixel through the same foils plus dark; Monc ~
Poisson(monc_rate·t·h·trend), h = g unless a P29 fault; Monp ~
Poisson(monp_rate·t); the reader's three boxes (21 × 11 px; 5-row core
apart, for P18); net = (S − (B1+B2)/2)/M; σ = √(S + (B1+B2)/4)/M
(`errors='counting'`), plus net²/M (`'counting+monitor'`).

`Beamline` defaults, read from the public NX school file, scans 6–9:
Monc 1.1e5/s, Monp 2.15e5/s, about 4e5 counts/s in the ROI at each scan's
first point (absorbers 41, 31, 24, 18); with the calibrated foils that is
flux 2.5e12 counts/s at R = 1 (the generator then also picks 41 for the
first scan: tested). Background 2e-10 × flux per pixel: an assumption.

Plans (lists of `ScanSpec`):

| Plan | Scans |
|---|---|
| `nx_like_plan()` | NX 6–9: 0.0175–0.04 / 0.035–0.10 / 0.09–0.19 / 0.17–0.45, steps 0.00125/0.0025/0.005/0.01, 2/2/2/5 s, slits ×2.7, ×3.2 for the last two. Overlaps share some points and not others, as measured |
| `standard_plan(n, qz_max, overlap, grid)` | n = 3–5 scans (hand-off §5's K), first to 0.04, step doubling, `overlap` shared points; `grid='staggered'`: shared points moved by half a step |
| `reaching_back_plan()` | hand-off §5's non-one-hot case: scan 3 starts inside the 1–2 overlap |
| `chain_plan(ranges, overlap, grid, **faults)` | anything else |

Faults, one value per scan, in any plan: `absorber=[...]`,
`slit_gain=[...]` (true beam), `monitor_gain=[...]` (what Monc saw;
P29: e.g. 2.27 and 1.55), `attenuation_error=[...]`, `seconds=[...]`,
`trend` (a callable on Qz: beam and Monc both follow it).

Truth: `scans[k].scale` (E[net]·scale = R), `true_join_factors()` (legacy
chain, scans in the reader's Qz order: s_{order[j+1]}/s_{order[0]}),
`true_steps()` (consecutive), `nominal_join_factors()` (the window's known
ratios: `Foils.step` chained, blind to the faults), `combine(scales)`
(inverse-variance mean at equal Qz; with the true scales it is the truth
to 1e-12, tested).

Measured with these generators (2026-11-22; bare water unless said):

- No noise, legacy fitted factor (`stitching.fitted_factor`) against the
  true step: coinciding grids exact (< 1e-9); staggered grids above Qc
  0.01–0.04 % low; staggered points straddling the critical edge
  (`chain_plan([(0.01, 0.0266, 0.0025), (0.0266, 0.07, 0.005)], grid='staggered')`)
  **16.7 % low** (P1: the cubic spline across the edge); NX-like grids
  −0.02 % (water), up to +0.09 % (100 Å film, third join).
- No noise, `reflectivity.patch` with the true factors: exact where all
  overlap points coincide; on NX-like grids up to 5e-4 off at the points
  of scan 6 that scan 7 lacks (interpolated).
- Poisson, 200 seeds, NX-like plan: fitted factors unbiased within ±0.04 %
  (1σ); their scatter 0.50 %, 0.52 %, 0.27 % against reported errors 0.49 %,
  0.47 %, 0.26 % (counting errors only, Monc's own noise not in σ);
  staggered and coinciding standard plans alike (scatter 0.73–0.97 %,
  reported 0.66–0.84 %).
- Pulls with `'counting+monitor'` have unit scatter (300 draws, tested);
  with `'counting'` they are > 1.2 where the box holds > 3e5 counts.

### 3.3 `synthetic.xrr_images`: frames from the reduced scans

`render(data, root, name)` writes `root/name` and `root/pilatus/` (int32
TIFFs for drawn counts, float32 expected values for `expected=True`). The
drawn S, B1, B2 of each row are spread over their boxes' pixels
multinomially, so `Experiment.reflectivity` (or the window's Ref Patch at
its default slit, offset and direction) gives the same net, S, B1, B2 per
Monc exactly (tested, 1e-12; float32: 2e-6). The error column then is the
reader's legacy one, 0.6–1.5 % larger than the counting error (the
per-pixel I²/M³ term, P2). Box positions: signal centred on column 97,
row 100; background boxes centred on columns 69 and 124 (`box_columns()`:
0.5° at 600 mm, as the reader truncates). Rendering costs 3.7 ms per frame
(measured). A GUI test (`test_ref_patch_in_the_window_gives_the_known_curve`)
runs select → Ref Patch → Next → Export and compares `_ref.txt` with the
truth.

Limits: the exact match needs the reader's default slit (21 × 11),
background offset (0.5°) and direction ('H'), and the beam found on its
nominal pixel (true unless a frame is very weak: the brightest pixel in
the ±3 search box must be the beam's). The background is flat (no
diffuse ridge, no Yoneda wings); no bad pixels; the beam is a 0.6 × 1.2 px
Gaussian cut to 5 × 21 pixels.

## 4. Other generators

**GID with three Qz levels** (`synthetic.gid_levels.make_frames`): levels
given as (β offset °, efficiency, number of scans); Det_Th 14–18.5° in
0.1° steps split between a level's scans with 0.6° overlap; scan monitors
1e5 × 1.03^(scan−1); truth `default_truth` (a rod at 2θ = 16.2° on a smooth
background) or any T(2θ, β). Returns `(frames, det, GIDTruth)`;
`truth.at(patch)` evaluates T on a legacy patch. Measured: two levels
give the truth to ±2.5 % (expected counts; the joins' interpolation);
three levels: everything within 5 % except the first frame of each
high-Qz scan, 1/M_s (8.9e-6) of the truth where only the high level covers
β (P36; strict xfail `test_three_levels_give_back_the_truth`), and a lone
high-Qz scan of its own raises KeyError (P37; strict xfail). Pass
`scan_numbers=[[1, 2], [3, 4], [3]]` for P37's harmless case. Counts at
the default monitor are ~1 per pixel; use `monitor=1e9` for 0.6 % per point.
In memory only (no SPEC file); geometry is the legacy one, not pinhole
(use `test_pinhole.py`'s helpers for that).

**GID burn profiles** (`synthetic.burn_profiles.profiles`): `change` one of
none, fade, broaden, shift, shoulder, background; `amount`, `tau`,
`monitor` (sets the counts), `seed`. Returns profiles for
`lss_core.burn.measure_gid` and the truth per frame. First look (one seed,
`amount` 0.2 / 0.3 / 0.004 Å⁻¹, last over first frame; measured, not a
study — that is hand-off 07 item 3):

| Change | True | template | moments | fit |
|---|---|---|---|---|
| fade (area) | 0.809 | 0.871 | 0.922 | 0.916 |
| broaden: FWHM / area | 1.284 / 1.000 | 1.246 / **1.155** | **1.015** / 1.001 | 1.362 / 1.132 |
| shift (Å⁻¹) | 0.0038 | 0.0037 | **0.0017** | 0.0036 |
| fade under a 3× shoulder | 0.809 | 0.914 | 0.964 | 1.024 |
| floor ×1.5, area | 1.000 | 1.001 | 1.004 | 0.989 |

Every estimator under-reads a fading peak on a shoulder (the window holds
part of it); the template reads a broadening at constant area as a 15 %
gain; the moments barely see a broadening or half a shift.

**XFNTR** (`synthetic.xfntr`): `yield_curve(qz, Sample(surface, bulk,
escape))`, `transmission`, `penetration_depth`, `fwhm_kev(E)`,
`spectrum(...)`, `measure(qz, ...)` (Poisson spectra and the truth),
`write_dataset(root, counts, truth)` (SPEC + vortex/, the layout of
`synth.make_xfntr_dataset`). Tested: |T|² = 4 at Qc without β, Λ =
1/√(Qc² − Qz²) below Qc (46 Å at low Qz), surface yield peaks at Qc,
`Experiment.fluorescence` window sums equal the written counts (live-time
corrected) to 1e-6. Detector noise 0.12 keV FWHM, Kβ/Kα 0.13, Fe lines by
default: assumptions.

**MCA spectra with the beam's scatter** (`synthetic.mca`, F90):
`spectrum(lines, elastic, beam=Beam(...), detector=Detector(...),
background, slope, calib, channels, offset, gain, kb_scale)` returns a
`Spectrum`:
- `energy`, the nominal keV per channel; `energy_true`;
- `expected`;
- `parts[(source, kind)]`, with source 'Zn Ka1', …, 'Rayleigh', 'Compton'
  or 'background', and kind 'peak', 'tail', 'shelf', 'escape' or 'flat';
- `photopeak(element, 'Ka' | 'Kb')`, the truth a line fit should find;
- `part(sources, kinds)`;
- `draw(rng)`, Poisson counts.

Also in the module:
- `line_energy(element)`, intensity-weighted (Zn Kα 8.631 keV);
- `compton_energy(e0, angle)`;
- `reed_escape(e)`;
- `write_dataset(root, spectra, counts, qz, monitor)`, SPEC + `vortex/`
  through `xfntr.write_dataset`, which now takes the calibration.

Tested:
- every photon lands in exactly one part (photopeak + tail + shelf +
  escape = the photons, to 0.2 %);
- Kβ/Kα = 17/151;
- the Compton centroid is at 9.808 keV (10 keV, 90°);
- the core part is zero above E0 − B;
- the escape peaks sit 1.740 keV below their parents, with Reed's
  fraction;
- the shelf is flat;
- a calibration offset or gain moves the lines on the nominal axis;
- the reader's window sums of written files equal the counts written.

Assumptions, all from memory:
- intensities 100 : 51 : 17;
- the hydrogenic profile shapes;
- the O 1s Z_eff of 7.7 (core FWHM 0.8 keV);
- Reed's constants (ω_K 0.050, μ(Si Kα) 350 cm²/g, μ(E) ∝ E^−2.75);
- noise 0.12 keV FWHM.

With E0 = 10 keV, the elastic and Compton escapes (8.26 and 8.07 keV) and
the core wing fall under Zn Kα: the hard case of F90. The gauntlet that
uses it is `tests/tools/mca_fit_gauntlet.py` (COMPARISONS C42).

**Growing files** (`synthetic.growing.Growing(src_spec, dst_dir,
image_lag)`): `advance(n)`, `advance_to(scan, points)`, `flush_images()`,
`finish()` (the copy then equals the source byte for byte), `points`,
`images`. Replays any data set from `synth` or `xrr_images.render`. The
destination SPEC file is empty until the first `advance`.

## 5. Unmet needs (not built)

| Need | For | Notes |
|---|---|---|
| Pilatus 1M frames (`pilatus1m/`), second 200K module | D11, F63 | no writer; the reader does not look in `pilatus1m/` |
| Per-point MCA files, multi-element MCA as a data set | F22, `test_mca_channels` | `synth.write_mca` writes one file of several spectra; multi-element files are built inline in that test |
| GID data sets on disk (SPEC + frames) with pinhole geometry, several scans and levels | GUI GID tests, hand-off 06 | today in memory (`test_pinhole.py`, `gid_levels`); GUI GID tests use NX 11/12 |
| Three-level GID through the window | P36, P37 fixes | `gid_levels` is in memory; writing its frames needs a GID SPEC header (`Det_Th`, slits, g_l) |
| GID burn as frames (images), reflectivity burn with noise | burn dialog, hand-off 07 | profiles and `synth.make_burn_dataset` only |
| XFNTR series with a `#U Series` recipe; energy scans across an edge | live series, F65 | |
| MCA spectra with the beam's scatter as a data set the reader opens (an XFNTR series of `mca.spectrum` through `mca.write_dataset`, a Tools item) | F90 in the window | `mca.write_dataset` exists; no `synthetic_dataset.py --kind` uses it yet |
| Compton profiles from tables (Biggs, Mendelsohn and Mann 1975) instead of the hydrogenic shapes; multiple scattering; pile-up; a measured detector response | F90 against real spectra | the gauntlet's hard case rests on the hydrogenic O 1s wing |
| Diffuse background, Yoneda wings, sh scans, Qz offset | F42, F59 | `xrr_images` background is flat |
| Bad pixels, cosmic rays, multiple exposures, stray light | F40, P40 | |
| Monitor noise with heavy tails (Student t, drifts) | `reports/monitor_noise.md` | `Beamline.monitor_jitter` is Gaussian |
| **Monc as it is** (owner, 2026-11-22): "monc doesn't have poisson noise, it's more like a strict 0.05% uncertainty" (xray_fluxor) | `xrr_scans.REAL_MONITOR` = `Beamline(monitor_poisson=False, monitor_jitter=0.0005)`; `errors='counting+monitor'` then adds (net × 0.0005)² | the default stays Poisson so that older tests keep their numbers; use `REAL_MONITOR` for anything that judges error models (the gauntlet does) |
| GISAXS, GIOXS, calibration fits (g_l2, g_l3) | R5 benchmarks | |
| The covariance contract's acceptance tests 2–6 | hand-off 19 §5 | the generator provides K = 3–5 and the non-one-hot case; the tests belong to the patching work |

## 6. How the generators serve the planned comparisons

- **Reflectivity patching** (joint fits, the stitch factor's correlated
  error; `reports/ref_patch_joint_fit.md`, `lss_core/patching.py`, not part
  of this work): draw many seeds of one plan with `measure(..., seed=rng)`;
  score a method's factors against `true_join_factors()` / `true_steps()`
  and its curve against `truth()`; `nominal_join_factors()` is the prior
  the known-ratio option uses, so faults (`monitor_gain`,
  `attenuation_error`) show where a prior misleads; `expected=True`
  separates bias from noise; `standard_plan(3..5)` and
  `reaching_back_plan()` are the hand-off's K = 3–5 and non-one-hot
  cases; `xrr_images.render` checks that a method gives the same answer
  from frames as from rows.
- **GID**: `gid_levels` to fix P36/P37 (remove the xfail markers in the
  same commit); `test_pinhole.py`'s helpers for the pinhole methods
  (hand-off 06); single-frame truth on real data stays the judge there.
- **Burn trends** (hand-off 07): `burn_profiles` for items 3 (which
  estimator reads which change) and 4 (lower `monitor` until each
  estimator fails); `synth.make_burn_dataset` for the reflectivity path.
- **Live mode**: `growing.Growing` over any data set, instead of cutting
  SPEC files by hand.

## 7. The fit demonstrator (every method on these generators, with a window)

`tests/demonstrator/` (2026-11-22; report `docs/reports/patch_demo.md`)
wraps the reflectivity and burn generators with every method that fits
them, GUI-free, so tests, figure scripts and the window share one code
path:

```python
from demonstrator import refl, burnmode as bm        # tests/ on sys.path, as in the suite
rep = refl.replicate(refl.Config(truth='film', plan='nx', thickness=100, counts=1.0), seed=3)
rep.scans, rep.expected, rep.true_steps, rep.prior    # noisy and noise-free Scans, truth, foil prior
res = refl.run_all(rep)                               # every patching method + the legacy chain
clean = refl.run_all(refl.denoised(rep))              # the same on the expected counts: bias alone
summary, rows = refl.survey(refl.Config(plan='staggered'), range(200))   # bias, SD, pulls per method/join
b = bm.replicate(bm.Config(change='broaden'), 1)     # burn profiles, noisy and clean, truth per frame
r = bm.run_all(b); bm.frame_curve(b, r['template'], 20)   # each estimator's curve on a frame's line cut
```

`refl.Config`: truth `water`/`dppc`/`film` (thickness), plan `nx`,
`nx_staggered` (NX ranges, every overlap staggered), `standard`,
`staggered`, `edge` (an aside: the P1 overlap across Qc, which the owner
does not patch), `counts` (beam and monitors scaled together), `monitor`
(`'real'`, the default: `xrr_scans.REAL_MONITOR`, no Poisson, 0.05 %;
`'poisson'`), `foil_error` (true foil steps drawn from the prior's
covariance per replicate, default on). Methods: `refl.METHODS` (`joint` =
`patching.joint_factor` defaults, `reader` = the reader's chain with the
joint factor, `legacy`, `fixed_*` = one fit without the guard, ...).
Plots: `demonstrator.draw.refl_figure` / `burn_figure` into any
matplotlib Figure. Window: `python tests/tools/patch_demo.py` (space bar:
new replicate), or from code `demonstrator.window.open_demo(parent, mode)`;
figures: `--save DIR` (headless). Tests: `tests/test_patch_demo.py`. The
burn profiles are normalised by a fixed monitor (no monitor noise).

## 8. Rules for adding generators

- New generators go in `tests/synthetic/`, with a test file
  `tests/test_synthetic_<name>.py` asserting physics invariants (not only
  "it runs"), fast enough for the quick suite.
- State the truth beside the data (a dataclass), cite the physics in the
  docstring, mark assumptions and values from memory as such.
- Never write into `sample_data/`; tests write under `tmp_path`.
- Leave `tests/synth.py` byte-stable; call its writers rather than copying
  them where the layout matters.
- Add the generator to section 2 and its limits to section 5 here.
