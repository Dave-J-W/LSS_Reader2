# Decisions that change the numbers in output files

One central register (owner, 2026-11-19): every choice, large or small,
that changes a number the reader writes or plots, with its rationale and
**how the rationale is proven**. For reviewers, for the figure agent
(`COMPARISONS.md`), and for the manual writer (`MANUAL_NOTES.md`).

Evidence: **O** the owner said so (date); **T** a test pins it; **M**
measured on data (entry in `physics_notes.md`); **L** taken from
literature or a hand-off (cited); **A** an assumption of this project, not
yet confirmed. A row with only **A** is a candidate question for the owner.

Rule (AGENTS.md rule 11): a commit that changes an output number adds or
updates a row here in the same commit, with before and after values.

## Defaults (what a user gets without touching anything)

| Setting | Default | Effect on output | Rationale | Evidence | Where (code; test) | Since |
|---|---|---|---|---|---|---|
| Normalisation | per monitor count (Monc) | all intensities | D6: stays as the original | O 2026-11-15 | `lss_core/normalise.py`; legacy fixtures | original |
| Error model | Legacy | error columns | D20: budget is an option until the two-file export exists | O 2026-11-17; T `test_error_budget.py` | `lss_core/errors.py` | original |
| Monitor uncertainty (budget) | Gaussian, σ = 0.04 % of Monc | budget errors | D22: monitors' scatter is beam variation of that size | M (`reports/monitor_noise.md`, 2026-11-16); O 2026-11-17 | `errors.MonitorModel` | 2026-11-17 |
| Student t option | ν = 4, scale 0.94 × 0.039 % | budget errors when chosen | D26 | M + O | `errors.MonitorModel` | 2026-11-17 |
| Absorber factor per unit | from the energy ("from E" on): calibrated foils at 9.70–10.30 keV, else 50 µm Al exp(μ/ρ·ρ·t); 1.4247 at 10 keV | any non-patched value at n ≠ 0 (cuts, background images, frame averages, GID, fluorescence) | D25, D28, D30, D34, D37; calibrated set from the owner's joins | L (NIST SRD 126); M (hand-off 03); O; T `test_absorbers.py` | `lss_core/absorbers.py` | 2026-11-17/18 |
| Calibrated-foil uncertainty | run-to-run σ ⊕ 0.5 %, ×3.2 when the overlap starts at Qz ≥ 0.25 | known-ratio errors; choice of known ratio vs patch | owner's note on high-Qz trust | M (`ABSORBER_RATIOS.md`); O 2026-11-18 | `absorbers.Foils.step` | 2026-11-18 |
| Known ratio instead of patch | on; used when the fit's error exceeds the ratio's and Monc/Monp is continuous within 3 % | patched `_ref` scale between scans | owner's request; P29 guard | O 2026-11-18; T `test_known_ratio_patch.py`; threshold 3 % is **A** | `reflectivity.patch_choice`, `MONITOR_TOLERANCE` | 2026-11-18 |
| MCA Merge window | 0.1 × the Qz grid step on the Qz axis, 0 on frame/energy | which points merge | owner's XFNTR rule (F65 step 2): repeats of one target within 0.1 step | O 2026-11-19; T `test_mca_merge.py` | `fluorescence.default_merge_window` | 2026-11-19 |
| MCA Merge errors | counting part as before (P7) ⊕ Qz jitter 3e-5 1/Å on the Qz axis | merged σ | owner (F65 step 5); the jitter figure is from monotonic scans, untested for peaked ones | O; T | `fluorescence.merge_rows` | 2026-11-19 |
| Multi-element detector elements | all summed (Preferences; `channels=`) | spectra and window sums of multi-element files | owner D49 (EXAFS all; XFNTR the central one) | O 2026-11-19; T `test_mca_channels.py` | `fluorescence.combine_channels` | 2026-11-19 |
| Dead-time correction | real/live time from #@CTIME (1 for the 7-element detector, which corrects itself) | fluorescence values | owner D48 | O; as coded | `fluorescence.normalise_spectrum` | original |
| Unknown absorber setting | n = 0 (no factor), no known ratio | frames of that scan; unpatched outputs only | D42 | O 2026-11-19; T `test_absorber_unknown.py` | `experiment.absorber_setting`, `spec_routines` | 2026-11-19 (was 63) |
| MCA scan absorber | last `#A` above the scan | fluorescence values ×absfacⁿ | D24 | O 2026-11-17 | `spec_routines`, `fluorescence.absorber_factor` | 2026-11-17 |
| Monitor gain | off; S_ref = 5 µA/V when on | ×S_ref/S | D29, D32, D39 | O; T `test_monitor_gain.py` | `lss_core/monitor.py` | 2026-11-17/18 |
| Per photon | off; when on: q(E) table, dark 50 Hz, gas 24.9 °C / 98.99 kPa, median scan rate | ×M/N | F54, D41 | L (xray_fluxor hand-off); O (dark); gas and median rate **A**; T `test_per_photon.py` | `lss_core/flux.py` | 2026-11-19 |
| GID columns | pinhole geometry at Det_Th > 1° | GID maps | D40 | O 2026-11-18; T `test_gid_worksheet.py` | `lss_core/pinhole.py` | 2026-11-18 |
| Pinhole angles | exact per pixel (Mati Meron's IMG_COO_CONV), binned in (2θ, β); β kept over the range every 2θ bin shares | GID maps (pinhole) | owner: "the geometry needs to be more exact the further we go from the direct-beam position" | O 2026-11-19; L (IMG_COO_CONV); T (ray construction, `test_pinhole.py`); M (NX: join χ²/dof 1.31 → 0.83) | `pinhole.pixel_angles`, `level_map` | 2026-11-19 |
| Pinhole distance | `#B1` 4th number (271 mm) unless typed | 2θ per column | owner; the fit is unstable (258–280) | O; M (NX 11) | `GIDParams.pinhole_distance_mm` | 2026-11-18 |
| Column response | fitted from the data | GID weights | IDL practice | M; L (IDL code, `docs/reference_code/idl/`) | `pinhole.column_response` | 2026-11-18 |
| Minimum frames per bin | 2 | GID bins kept | **A** | T | `GIDParams.min_frames` | 2026-11-18 |
| Qz-level join, 2θ range | common (intersection) | GID map extent | as the IDL `IMG_JOIN` | O ("as the IDL code does"); L | `GIDParams.transverse` | 2026-11-19 |
| Join factor | equal-weight cell intensities over shared cells | GID level scale | summed counts biased the factor 2.6 % | T (synthetic) | `pinhole.join_levels` | 2026-11-19 |
| β grid step | the largest row step of any level | GID map rows | no level skips a bin | **A**; T | `pinhole.join_levels` | 2026-11-19 |
| Cuts, horizontal axis distance | S4–detector at Det_Th > 1° (pinhole) | Q H / Angles cut axes | D40, P32 | O; T `test_cut_script.py` | `Experiment.cut(pinhole=True)` | 2026-11-18 |
| Pix V β distance | sample–detector | β axis of V cuts | P34 fix (was ×2) | T | `cuts.frame_cut` | 2026-11-18 |
| Polarisation, area correction (GID) | on | GID maps | legacy behaviour | legacy fixtures | `GIDParams` | original |
| Dead time (MCA) | real/live time | fluorescence | original | legacy | `fluorescence.normalise_spectrum` | original |

## Changes of output, with before and after

Each is also in `physics_notes.md` under its date.

| Date | Change | Before → after | Who decided |
|---|---|---|---|
| 2026-11-17 | Absorber default 1.606 → 1.4247 (D25) | ×(1.4247/1.606)ⁿ | owner |
| 2026-11-17 | Fluorescence scaled by absfacⁿ (F50) | XFNTR hashes `77be46ea…` → `e23206a9…` → `1cfab3ab…` | owner |
| 2026-11-17 | P24: factor in use = factor shown | was 1.606 until a GID/Ref action | defect fix |
| 2026-11-17 | Cuts monitor-normalised (D19, P23) | raw counts → per monitor count | owner |
| 2026-11-18 | Calibrated foils at 10 keV | n = 3: 2.892 → 3.259 | owner |
| 2026-11-18 | Known-ratio error | 42→33: 1.23 % → 0.86 % / 2.75 % | owner's note |
| 2026-11-18 | `AL_MAX_KEV` 10 → 10.52 | 10.52 keV: 1.3565 per unit where the field kept its value | owner (D37) |
| 2026-11-18 | S_ref 1 → 5 µA/V | gain factors ÷5; ratios unchanged | owner (D39) |
| 2026-11-18 | Pinhole default (D40); P32, P34 | GID maps, cut axes | owner |
| 2026-11-19 | Pinhole Qz join (F62) | interpolated vertical join → shared grids | owner (D36) |
| 2026-11-19 | GID moved to `lss_core/gid.py` (scriptable) | none: maps byte-identical (tests); Save GID with Pixels axes now a message instead of a crash | refactor |
| 2026-11-19 | Pinhole angles per axis → exact per pixel (P38) | NX 11: Bragg peak 2θ centroid 16.6456 → 16.6473°, map 472 rows → 460 β bins; NX 11+12 (arm raised 6.5°): level factor 1.029 ± 0.011 → 1.097 ± 0.013, join χ²/dof 1.31 → 0.83, β of the high level's maximum 8.41 → 7.80° | owner |
| 2026-11-19 | MCA Merge on the Qz axis: Qz jitter 3e-5 1/Å added to the errors (σ_j = I·\|d ln I/dQz\|·3e-5·√Σw²/Σw); default window 0.1 × the Qz grid step (was 0, typed) | values unchanged; errors grow near the edge only (a step or two); merges made with the old default (0) merged only identical Qz | owner (F65 steps 2, 5) |
| 2026-11-19 | Legacy GID footprint: S1 vertical = S1T + S1B (was S1T + S1T, defect 10) | none on any file here (S1T = S1B in all 643 scans); for an asymmetric S1 the footprint length is now right | owner |
| 2026-11-19 | Unreadable `#A`: 63 → unknown | unpatched outputs of such scans ÷absfac⁶³ | owner (D42) |

## Open assumptions (A) to confirm with the owner

- Known-ratio Monc/Monp tolerance 3 %.
- Per-photon: gas at the table's conditions; one factor per scan from the
  median rate (dark term ≲ 0.05 %).
- GID: minimum 2 frames per bin; β grid step = the largest row step.
