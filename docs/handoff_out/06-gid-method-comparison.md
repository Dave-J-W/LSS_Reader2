# Hand-off: final judgment of the GID patching methods on a large data set

For: an agent with access to the owner's full GID data (many SPEC files,
all Pilatus frames). From: the LSS_Reader2 project, 2026-11-21. The owner
asked (2026-11-21): "commit your comparison work such that another agent
can pick up what you were doing with a much larger dataset for a final
judgment".

Read first: `AGENTS.md` (house rules; private data), the manual addendum
`docs/manual/gid_patching.md` (terms, every method, sections 3a–3d with the
reasoning and the measurements so far), and `docs/PHYSICS_ISSUES.md` P38–P43.

## The question

Which GID patching settings should be the reader's defaults, decided on
evidence from many data sets instead of the two public NX scans and nine
private scans used so far. Specifically:

| Decision | Now (default) | Alternatives | Evidence so far |
|---|---|---|---|
| Column response | `fit` (per column, with each scan's scale; P42 fixed) | `beam`, `physical`, `physical+fit`, `none` | `fit` best or near-best frames-agree χ²/dof on all 5 sets; `physical+fit` better on 3, much worse on the low-Det_Th set (addendum 3c) |
| Joins | applied (scan and level factors) | `apply_joins=False` (as collected, factors reported) | the owner's 163 + 164 + 165 join to 0.3 % as collected; NX levels 22 % apart as collected (physics_notes 2026-11-20) |
| S4–detector distance | header (`#B1` 4th number, 271 mm) unless the worksheet's Fit calibrates it | `pinhole.calibrate_distance` (single frames) | NX 265.7 ± 1.1 mm, owner's 163 262.0 ± 1.4 mm; at the calibrated distance the patched peak equals the single frames' (addendum 3d) |
| Footprint window | exact (P39), IDL's high edge on raised-arm frames (P40b streak) | `footprint='idl'` | NX +3.3 % counts, peak unmoved |
| Horizontal beam FWHM (physical responses) | 1 mm (owner's estimate) | measured | narrower fits slightly better on two sets |

The owner's principles for the judgment (from the conversation): the data
as collected are the honest base; fitted scalings are corrections that must
earn their place; an unpatched single frame is the ground truth for a
peak's position and width; users see every method through check boxes and
drop-downs, and the best method on the evidence is the default.

## The tool

    python tests/tools/gid_method_survey.py --spec FILE [--spec FILE ...] --out DIR [--split]
    python tests/tools/gid_method_survey.py --list sets.csv --out DIR [--split]

Run from the repository root. `--spec` finds the GID sets of a SPEC file
itself (inferred GID series, `lss_core.series.infer`, reduced to scans whose
frames are on disk); `--list` gives them by hand (CSV lines `spec,scans[,label
[,peak]]`, scans separated by `;` or `,`; a typed peak 2θ skips the peak
search). About 2–4 min per set; sets are independent, so split the list
across processes if needed. Private data: `--out` must be under
`sample_data/private/` or outside the repository (the tool checks).

A worked example on the public NX data is committed:
`docs/comparisons_data/gid_survey_nx/` (`summary.md` and the CSVs below).

## The outputs

`methods.csv`, one row per set × distance (header, calibrated) × method ×
Qz level:

| Column | Meaning |
|---|---|
| set, distance, method, level, scans, frames | what was run; `distance` 'calibrated' = the first reliable calibration of the set |
| two_theta_from, two_theta_to | the level's 2θ range |
| consistency_chi2 | **frames agree**: Poisson χ²/dof of every frame's and column's rows-summed counts against the map, after response and scan factors (`pinhole.frame_consistency`; 1 = counting noise; empty for legacy) |
| counts_used | raw counts that entered the level |
| beam_centre_mm, beam_fwhm_um, beam_fit_chi2 | the beam found by `physical` / `physical+fit` |
| seconds, error | run time; an exception, if any |

`joins.csv`, one row per fitted join: set, distance, method, label, kind
('horizontal (2theta)' = scan join within a level; 'vertical (beta)' =
level join), x_from, x_to (overlap), points, factor, error, chi2 (scatter of
the overlap ratios about the factor).

`calibration.csv`, one row per set × level: distance_mm ± error_mm,
header_mm, reliable, why (when not), peak_deg (the peak used), frames,
chi2_dof and drift at the calibrated distance, chi2_dof_header and
drift_header at the header distance, centre_deg and fwhm_deg of the single
frames there. A reliable calibration needs ≥ 5 frames, χ²/dof ≤ 25, |drift|
≤ 0.01 deg/deg, the best distance inside the scanned 0.90–1.06 × header,
and an error below 5 mm.

`truth.csv`, one row per set × distance × method: the single frames
(centre ± error, median FWHM, their χ²/dof) against the patched map of the
calibrated level (centre ± error, FWHM, width_ratio = patched / single).

`split.csv` (with `--split`): each level of a single scan with ≥ 30 frames
split into two overlapping scans, the second's counts × 0.8; per method,
`halves` (the factor at × 1, where the true value is 1 unless the scan
changed along its length) and `recovered` (should be 1.25).

`summary.md`: per set and level, the method with the lowest frames-agree
χ²/dof and the calibrated distance.

## How to judge (suggested)

1. **Distance.** Collect `calibration.csv` over all sets. Is the calibrated
   distance stable within a beamtime (same S4 position)? Does it differ
   between beamtimes? What fraction of sets calibrate reliably, and why do
   the others fail (`why`)? If the distance is stable per beamtime, the
   reader could calibrate once per beamtime and store it; if it is not, per
   set. At the calibrated distance the single frames' χ²/dof should be near
   1 (NX: 1.42); large values point at something else (c0, illumination
   slope across the peak, sample motion).
2. **Truth.** From `truth.csv` at the calibrated distance: is every pinhole
   method's centre within its error of the single frames' and its
   width_ratio ≤ ~1.03? At the header distance, how much broader? (NX: 1.00
   at both; owner's 163: 1.14 at the header distance, ~1.04 calibrated.)
3. **Response.** From `methods.csv` at the calibrated distance: rank the
   responses by frames-agree χ²/dof per level, and look at the worst case
   as well as the median, by data class (Det_Th range, α, beamtime). A
   method that wins on average but fails badly on a class (as
   `physical+fit` at low Det_Th) is not a safe default.
4. **Joins.** From `joins.csv`: the level factors with `none` or
   `physical` (absolute scales) say how far the levels are apart as
   collected; their spread over many sets says whether fitted joins are
   needed in general or only sometimes. The scan factors of repeated
   ranges (same Det_Th range twice) measure changes between measurements
   (owner's 137/139: 5 %).
5. **Split.** `recovered` should be 1.25 ± 1 % for every method (P42 fixed);
   `halves` away from 1 under every method means the scan changed along
   its length (time), which no method should hide.

Write the result as a short report for the owner with a table per
decision and a recommendation, private numbers in the owner's private
channel only (rule below), and the proposed default changes as rows for
`docs/OUTPUT_DECISIONS.md` (with before/after values).

## Known caveats

- **Stray light (P40):** light beyond the footprint is seen at both arm
  heights, and a sharp streak past S5 at the raised arm ("junk", owner). It
  affects frames-agree χ² and level joins near β ≈ β0.
- **Scan join against the first scan only (P41):** scans that overlap only
  in a chain get no factor; check `joins.csv` for NaN.
- **Single-frame fits are per column**, each column at its own mean 2θ. An
  earlier version binned on a fixed 2θ grid and aliased the columns
  (±0.02° in the centre, χ²/dof 5 instead of 1.4 on NX); do not
  reintroduce binning there.
- **The peak** used for the calibration is found automatically (the
  strongest feature that ≥ 5 single frames fit; rows at β −0.1…2°). On sets
  where it picks a poor feature the calibration says so (`reliable`
  False); give `peak` in `--list` to override.
- **Physical responses** assume one Gaussian beam per level with a 1 mm
  horizontal FWHM; they fail at low Det_Th, where cot 2θ spreads the
  horizontal width along the beam.
- **Legacy** has no frames-agree χ² (it does not bin cells) and ignores
  the distance.

## Privacy

`AGENTS.md`: the owner's data are private (git-ignored). A few derived
numbers in committed documents are acceptable, but **never peak locations,
raw data or images**. Keep survey outputs of private data under
`sample_data/private/` or outside the repository; quote peak positions only
in conversation with the owner.

## Code map

| What | Where |
|---|---|
| Survey | `tests/tools/gid_method_survey.py` |
| Single frames vs patches, one set, verbose | `tests/tools/single_frame_truth.py` |
| Distance calibration | `lss_core/pinhole.py`: `calibrate_distance`, `single_frame_peaks`, `frames_agree`, `strongest_peak`, `rows_for_beta` |
| Responses | `pinhole.column_response`, `beam_response`, `PhysicalResponse`, `fit_beam`, `level_map` |
| Frames agree | `pinhole.frame_consistency` |
| Joins | `pinhole.level_map` (scans), `pinhole.join_levels` (levels) |
| Settings | `lss_core/gid.py` `GIDParams` |
| Tests | `tests/test_pinhole.py`, `tests/test_gid_scan_join.py`, `tests/test_gid_worksheet.py` |
