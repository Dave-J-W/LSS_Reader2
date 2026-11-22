# Hand-off: test and extend the burn-test trends

For: an agent working in this repository (LSS_Reader2) on a later day.
From: the LSS_Reader2 project, 2026-11-21. The owner asked (2026-11-21):
"write the handoff for another agent to test and extend what you just
built". Built in commits c3c5cd3, fb897b3 and the one that adds this file.

Read first: `AGENTS.md` (house rules; private data; one change per
commit with its test; never weaken a test), then the entries of
2026-11-21 in `docs/physics_notes.md` ("Burn tests: trends over time")
and the rows of that date in `docs/OUTPUT_DECISIONS.md` and
`docs/COMPARISONS.md` (C31).

## What the owner asked for

1. Compare the validity of an average over time, a linear change, an
   exponential and a double exponential by an information criterion.
2. "When an average (flat line) has the same confidence of fit as a linear
   fit then we know we're in a good regime for avoiding beam damage."
3. "A confident suggestion about how much time causes a less than 5 %
   change in the quantity of merit."
4. GID burns: all three quantities (intensity, position, width) at once;
   then: each on its own panel, the right-hand axis normalised in percent,
   the summary to the right of the panels, not in the title.
5. GID: a relative change matters, so less weight on absolute σ; the
   legacy GID burn test worked once its fit range was constrained, use it
   as the inspiration.
6. Answers: the shutter closes between exposures by default, wall time is
   better (clock is the default); whether a position change matters is the
   user's judgment; burn scans are, for now, an `ascan ih` that does not
   move; more burn data will be asked for later.

## What exists

| Piece | Where | What it does |
|---|---|---|
| Trend comparison | `lss_core/trends.py` | `compare(t, y, sigma)`: constant, linear, exponential a·e^(kt), double exponential; AICc (QAICc when the scatter exceeds given errors); Akaike weights; `stable` = AICc(const) − AICc(lin) ≤ 2; `errors='scatter'` uses σ only as relative weights; `change_time`: the 95 % confident time to a threshold change (2000 draws from the covariance, 5 % quantile of the crossing times) from the best model that beats the constant, else the linear one |
| Burn measurement | `lss_core/burn.py` | `frame_times` (clock default, exposure), `choose_window` (strongest peak of the mean frame, 3 FWHM either side, inside the lit columns), `measure_gid` (estimators `template` default, `moments` = legacy arithmetic, `fit`), `analyse`, `BurnResult` (`safe_time`, `summary`, `table`, `data`), `plot` (the figure the dialog and the tool draw), `summary_text` |
| Script entry | `Experiment.burn(scan, ...)` in `lss_core/experiment.py` | reflectivity (Det_Th 0): the Ref Patch ROI per Monc; GID: per-frame profiles (all rows, Q axis with the pinhole distance) then `measure_gid`; `time`, `models`, `threshold`, `estimator`, `qxy_range`, `rows`, `trend_errors`, `limit` |
| Burn scans | `lss_core/series.py` `is_burn`, `infer` | `ascan ih a a n t`, a = b, n ≥ 2: one inferred series of kind 'burn' each |
| Dialog | `mainwindow.py`: `buildBurnDialog`, `setupBurnTrends`, `burnTrends`, `burnArguments`, `plotBurnTrends`, `saveBurnToWorkbook` | Trends tab (analysed on opening), Legacy tab (old plots, unchanged); options kept in the preference `burn` |
| Workbook | `lss_core/workbook.py` | kind 'burn test'; Data (time and each quantity ± error, up to 8 columns); Trends sheet (one row per quantity × model) |
| Tests | `tests/test_trends.py`, `tests/test_burn_trends.py`, `tests/test_gui_burn_trends.py`, `tests/test_burn.py` (legacy), `tests/test_series.py` | synthetic truths, coverage (slow), NX scans 14 and 15 (slow) |
| Figures, CSVs | `python tests/tools/burn_figures.py [--spec F --scans N ... --out DIR]` | `docs/figures/burn_trends/`, `docs/comparisons_data/burn_nx/` (values per estimator, `estimators.csv`) |

Data with a burn test: public NX school scans 14 and 15 (GID, 21 frames
of 10 s, absorber 12 then 8, same spot); a synthetic reflectivity burn
(`tests/synth.py` `make_burn_dataset`, τ = 400 s). No real reflectivity
burn and no private burn frames are in the repository; the private file
`sample_data/private/gid_scans_136-146/gid` lists burn scans 23, 35, 51,
211, 275, 277, 278 (frames not on disk) and the XFNTR file scans 19 and 20
(`ascan ih` without movement, fluorescence).

## Evidence so far (what is measured, what is only assumed)

Measured (tests or the tool): τ recovered to 1e-3 on synthetic data and
the 5 % time = τ·ln(1/0.95); coverage of the confident time 5.5 % misses
for a nominal 5 % (linear truth, 200 draws); a constant called stable in
95 % of draws; template per-frame χ²/dof ≈ 1 on NX 14; template position
scatter 3 × below the moments'; moments dilute a peak's shift by a steady
shoulder (0.004 → 0.0023 Å⁻¹, synthetic). NX (clock, template): 14
stable in intensity and width, position +0.0024 Å⁻¹; 15 intensity stable,
width +19 %, position +0.008 Å⁻¹ (≈ 4 × the flux).

Assumed, not tested: the coverage of the confident time for the
exponential and double-exponential models (their covariance is a
linearisation; the double exponential's is often wide and skewed); the
template's behaviour when the peak's shape changes a lot (NX 15: per-frame
χ²/dof 4); that all rows of the frame are the right ones to sum.

## What to test (suggested, in order)

1. **Coverage for curved models.** Repeat
   `test_the_confident_time_is_conservative_at_its_stated_level` with an
   exponential truth (τ from 50 to 2000 s over a 210 s test) and a double
   exponential (a fast 10 % drop plus a slow drift), all four models
   fitted. If the miss rate is far from 5 %, try a parametric bootstrap
   (refit synthetic draws from the best model) or a profile likelihood for
   the crossing time, and compare.
2. **False alarms of the curved models.** On constant data, how often does
   the double exponential win (AICc) and drive the 5 % time down? The
   verdict text flags "a change a line misses"; check that it is rare
   (NX 14's intensity, before the area fix, was such a case).
3. **Estimators on synthetic GID frames** (generator: `tests/synthetic/burn_profiles.py`, `docs/SYNTHETIC_DATA.md`; first look: PHYSICS_ISSUES P44) made like pinhole frames
   (`tests/test_burn_trends.py` `_gid_profiles`): a peak that broadens at a
   constant area, a peak that shifts, a peak that fades under a steady
   shoulder, and a background that rises. Which estimator reads each
   truth, with what bias and scatter? Add rows to C31.
4. **Noise level.** The moments degrade faster than the template as the
   counts fall (their baseline uses 3 points at each end); find the counts
   per frame where each becomes unusable.
5. **GUI sweep.** The crash sweep does not drive the burn dialog's own
   controls; add a sweep state with a burn scan selected and the dialog
   open (`tests/sweep.py`), and run `pytest -m sweep`.

## What to extend (suggested)

- **Exponential to a plateau** c + a·e^(kt) (three parameters): a common
  physical form (damage that saturates), missing from the four models.
  Adding it changes the criteria of every comparison: an OUTPUT_DECISIONS
  row with before/after on NX.
- **Dose instead of time.** Flux ∝ Monc × absfac^n (absorber setting n;
  `lss_core.absorbers`); a dose axis Σ Monc·absfac^n·Seconds would let
  scans at different absorbers (NX 14 and 15) be compared, and joined when
  they are consecutive scans on one spot. Test whether 14's and 15's
  position drifts fall on one curve against dose (they drift 3.3 × apart
  at 4.1 × the flux).
- **Fluorescence burns** (XFNTR scans 19, 20 of the private file): the
  line intensity per spectrum from `peaks.fit_series` (the MCA tab's "Fit
  lines") over time, through `trends.compare`.
- **Row range for GID** (`rows=`): the Bragg rod's β range instead of all
  rows; a control in the dialog.
- **Contextual reduction (F60):** offer the burn test when a burn scan
  (`series.is_burn`) is selected.

## Rules that apply

- Never weaken a test; a changed number is a bug or a deliberate change
  recorded in `docs/physics_notes.md` and `docs/OUTPUT_DECISIONS.md` with
  before/after.
- Every method change: a row in `docs/COMPARISONS.md`; stale figures
  regenerated with `tests/tools/burn_figures.py` in the same commit.
- Controls: a tooltip, a line in `docs/MANUAL_NOTES.md`, then `python
  tests/tools/dump_tooltips.py > docs/manual/controls.md`.
- Private data (`sample_data/private/`, `sample_data/bu/`): never
  committed; a few derived numbers in docs are acceptable, never peak
  locations, raw data or images; figures of private data under
  `sample_data/private/figures/` (the tool refuses `docs/` for them).
- Ask the owner for more burn data when it is needed (owner: "ask later").
