# Review of the to-do lists, 2026-11-21

**Applied 2026-11-21** (owner: "move on to the review work"): section 1 in
the docs; sections 2 and 3 as "Remaining work by area" in `TODO.md`;
section 4 step R1 in `lss_core/series.py`. Next steps: R2 (series in the
scan list), R3 (workbook ties), M1 (questions to the owner). Line numbers
below refer to the docs before these changes.

Asked by the owner (2026-11-21): what has been knocked off, what needs
regrouping, what was forgotten, and a plan for scan macros and series built
on a little new metadata. Sources: the docs, the 198 commits and
`lss_core/series.py`. **Measured** marks what was run for this review;
everything else was read.

## 1. Done, but still open in the docs

| File : line | Now says | Change to | Evidence |
|---|---|---|---|
| TODO:14 | Stage 6 "fitting … not started" | "fitting started 2026-11-21 (D52 peak module)" | 9c909ae, `lss_core/peaks.py`, `test_peaks.py` |
| TODO:95–97 | [ ] Gains the reader cannot interpret | [x], "nothing to do (D33)" | the line itself says nothing remains |
| TODO:122–130 | [ ] P28 nominal steps off | [x] calibrated (F56); the 6–7 keV part stays at line 140 | 8bbf319, ebc1e13 |
| TODO:161–164 | [ ] upper-level difference; "Next: maps from column groups" | [x] done; continues as P40 and hand-off 06 | 2d85881, 8595952, c94cfea |
| TODO:194–201 | [ ] IDL review §8 list | keep only: IDL output for NX 11+12, PD_MERGE, overlap arithmetic (input 18), one absorber per GID set. Routines received (36c0432); S7D_Dist is S4–detector, 271 mm (e2959ac); pinhole the default (D40); legacy kept beside it; column response from data (`fit`) and geometry (`physical`) both built (c94cfea) | as cited |
| TODO:29 (input 7) | column response; per-column replacing or beside | "both built as options; PD_MERGE open" | c94cfea, d4d9f55 |
| TODO:202–203 | [ ] resend scan-136 frames | [x] received 2026-11-18 (input 13 already says so) | TODO:35 |
| TODO:204–206 | burn tests and peak fits scriptable | "peak fits of cuts scriptable (`cut.fit`, 9c909ae); burn tests remain" | `test_gui_peak_fit.py` |
| TODO:274–278 | missing characterisation: GID multi-scan joining, MCA merge | strike both | `test_gid_scan_join.py` (legacy 2θ join recovers 1.25 exactly), `test_gid_script.py` (NX 11+12), `test_mca_merge.py` |
| TODO:294–296 | benchmarks missing: GID export bytes, synthetic GID with known truth | strike GID bytes; "synthetic GID truth: partly" | `test_gid_script.py`, `test_gid_worksheet.py`; `test_pinhole.py` (synthetic beam, distance 262 recovered) |
| TODO:311–312 | [ ] (superseded) write the scoping document | delete | line 310 |
| TODO:328–330 | **[x]** stitch bias "Do not forget" | **[ ]**, move to the Stage 5 group: a ticked "do not forget" is how it gets forgotten | P1, D13; TODO:302 still open |
| TODO:396–399 | whether `fluo_p` writes `#A` and `#M Monc Gain`: check on the next file | answered: yes | **measured** on the private XFNTR file: all 153 `#V` hklscans have both; only the 7 `getandsave_mca` scans have neither |
| TODO:40 (input 19) | P43 decision | "built (5fbebf8); automatic calibration: hand-off 06" | — |
| SCOPE:5–6 | "Nothing here has been built. Implementation starts when the owner says so" | "Stages 0–2 done; Stages 3 and 6 under way (TODO.md)" | 029541a, ea73014, 62f7750 |
| SCOPE:149, 154–157 | open questions F26, F23/F45, F22, P7/P13, 9-ID-C | delete these rows (the paragraph above them says they are answered) | D44, D41, D36, F22a, D17 |
| SCOPE:161 | "Changes to SPEC macros" out of scope | "the project proposes macro changes (beamline to-do, hand-off 05); it does not make them" | — |
| FEATURE_REQUESTS:10 | R2 "none fixed yet" | "Stage 1 fixed defects 1–7, 14, D14" | be82f11, 50c40d0, ac281d3, 7452692, b017661, c513b18, 57ae1cd, 78ce013 |
| FEATURE_REQUESTS:11 | R3 "420 combinations raise" | "0 failing controls, 0 crash sites (2026-11-17); sweep 67 passed (Stage 2)" | ea73014, 62f7750 |
| FEATURE_REQUESTS:119 | F22a "nothing built" | "(2) and (6) built in the core: `peaks.fit`, `fit_series`; not yet in the MCA tab or SpecPlot" | 9c909ae |
| FEATURE_REQUESTS:226 | "F44 (multiple exposures)" | F40 (F44 was never assigned) | line 236 |
| FEATURE_REQUESTS:235 | F39 "Nothing groups scans today" | "reader side built (`series.py`); window not yet" | 14d6cff |
| FEATURE_REQUESTS:240 | F45 "Today a pinhole check box only swaps the distance" | "built: exact per-pixel geometry, the default" | 4719f74, bf672fb, a809e95 |
| FEATURE_REQUESTS:272 | F49 "Open: … foils at 10.05 and 10.52 keV" | answered, D37 | 89c0d8f |
| FEATURE_REQUESTS:277 | F54 "waiting for the scalar" | "built from the xray_fluxor hand-off" | 89c0d8f, 0ebdd4d |
| FEATURE_REQUESTS:330 | "Beam response (option)" row inside the decisions table | move to "Status of built items" | 6a53a54 |
| FEATURE_REQUESTS:342ff | Built table lacks recent work | add rows: P39 (0923a96), physical response and as-collected joins (c94cfea), P42 (d4d9f55), distance calibration (5fbebf8), D52 peaks (9c909ae), F37 times (261fb9d) | — |
| PHYSICS_ISSUES:6–7 | "Nothing here is fixed yet … not repaired" | "Status column says what is fixed" | P13, P23, P24, P32, P34, P38, P39, P42 fixed |
| PHYSICS_ISSUES:31 | P16 open | "factor part fixed 2026-11-17 (defect 14); gap neighbours open (D11)" | 57ae1cd, `test_known_defects.py::test_bad_pixel_factor_controls_replacement` |
| PHYSICS_ISSUES:29–30, 47 | P14, P15 and P31 | the same two defects as P36 and P37: keep P36/P37, mark P14, P15, P31 "see P36/P37" | text of the rows |
| PHYSICS_ISSUES:24, 35 | P9, P20 open | "remedy exists in `lss_core/peaks.py` (√(2π) area); not wired in" | 9c909ae, physics_notes 2026-11-21 |

## 2. Proposed regrouping of the remaining work

TODO.md today is ordered by stage and date; Stage 2's list holds most of the
GID, absorber and fluorescence work. Proposed: one table per area, each
row with its source; the stage table at the top stays as the summary.

**A. GID (pinhole patching)**

| Item | Source |
|---|---|
| Final defaults from many data sets (distance, response, joins) | hand-off 06; input 19 |
| Scan join against everything joined so far | P41 |
| Stray light, streak mask, background frames | P40; input 17 |
| Exact angles for cut axes, display, distance fit | P38 remainder |
| Legacy three-level map (synthetic three-level set) | P36, P37 (= P14, P15, P31) |
| Second 200K module | F63, D43; input 3 |
| ΣN/ΣW vs IDL error weights | input 18 |
| Multiple exposures, cosmic rays | F40 |
| GID scan designer | F32 |
| GISAXS one column off; GISAXS and background-subtracted GID scriptable | P35; TODO:157 |

**B. Reflectivity and export (Stage 5)**

| Item | Source |
|---|---|
| Two-file export, covariance sidecar; Budget then the default | F24, F24a, F24c; P4; input 5 |
| Stitch-factor bias, measured on real overlaps, then remedied | P1, D13 |
| Same-absorber scans share a factor (question to the hand-off author never sent) | F41 |
| Qz offset from sh-scan images | F42 |
| Per-second option | F20 |
| ORSO, HDF5 export; steps and parameters recorded | F25, F30, R7 |
| Synthetic K = 3–5 generator; hand-off tests 2–6 | hand-off §5; input 4 |

**C. Fluorescence, MCA, EXAFS**

| Item | Source |
|---|---|
| MCA tab and SpecPlot fits on the peak module; `fit_series` for spectrum series | P9, P20, F22a(6), D47 |
| Per-point MCA files of scans without `#V` (October `ascan`) | input 14; physics_notes 2026-11-19 |
| EXAFS output (energy axis, line fit per point) | F36 |
| Edge estimator (backlog; now listed twice, TODO:174 and 179) | F65 steps 3, 4, 6 |
| Pilatus and Vortex in one scan | F53 |
| Line markers, escape peaks | F47, I14 |

**D. Monitor, absorbers, normalisation**

| Item | Source |
|---|---|
| Monc high at narrow S1 | P29; input 9 |
| Foil composition (6–7 keV overlaps); Cu at 30 keV | P28, F49; input 8 |
| Dark offset in ordinary normalisation | P21 |
| Frame object: normalise once at load | owner 2026-11-17; TODO:152 |
| End-to-end photons-in/photons-out for GID, GISAXS, cuts, MCA | TODO:305 |

**E. Scan series, live refresh, time**

| Item | Source |
|---|---|
| Series in the scan list; select a series as one action | F39; Stage 3 |
| Fix `series.infer` (section 4, R1) | this review |
| Contextual reduction from `kind` | F60 |
| Live refresh by polling | F1–F5 |
| Time axis in MCA, Ref/GID lists; measured times in burn tests | D46, D50, F37 |

**F. Per-SPEC state and saving**

| Item | Source |
|---|---|
| Excel workbook per SPEC file (scans, saved results, data, fits, settings) | owner, 2026-11-21 (no F-number yet) |
| Config beside the SPEC file; read-only second instance, yellow light; atomic writes | F13–F16, D1–D3 |
| Dropped points as masks, undo | F16, D2 |
| Disk-cache settings dialog | TODO:68–69 |

**G. Fitting, burn tests, beam**

| Item | Source |
|---|---|
| Burn tests monitor-normalised, robust dynamics fit, largest GID peak by default | P30, F22a(3, 4), R6 |
| Half-cut fit for the beam profile | F43, F22a(5); input 16 |
| Remaining characterisation tests: GISAXS, burn, g_l2/g_l3, 2D plot tab | TODO:274 |

**H. Detectors and inputs (Stage 4)**: 1M (F17–F19, F38, D11), 100K/200K models (F33), ME7 tab (F34, F35), new-format SPEC (F28), HDF5 (F29). All wait on input 3.

**I. GUI, speed, packaging**: GUI reorganisation (R4) with redraw in place (TODO:61) and diffuse cuts (F59); slow-file-system timing; `timings.md` regenerated; build workflow and macOS signing (input 12); sample-data hosting.

**J. Beamline / SPEC macros**: series lines (F39, section 4); `Tstart`/`Tend` (F37); `#V` detector flag (F34); Pilatus + Vortex header (F53); gas conditions and dark rate (F54, D41); photons-in (F21); half-cuts and an sh scan next to each GID level (F43); `#A` always written (D42); `getandsave_mca` `#A`/gain (test macro only, low priority).

**K. Owner inputs**: keep TODO's table, but renumber (18 sits after 19) and add the rows of section 3 marked "owner".

## 3. Forgotten or dropped

| What | Asked or found | On a list? |
|---|---|---|
| MCA tab, SpecPlot fit and MCA series moved to the peak module | physics_notes 2026-11-21, "Next (not done)" | no |
| P41 (chain of scans: undefined factor); remedy known | physics_notes 2026-11-20 | no |
| P9–P12, P19, P35 "may be intended": never put to the owner | PHYSICS_ISSUES | not in the inputs table |
| P21 dark subtraction in ordinary normalisation (D41 covers per photon only) | PHYSICS_ISSUES P21 | no |
| Stitch bias "do not forget" ticked as done | D13; TODO:328 | ticked |
| F41's question to the hand-off author | SCOPE open questions | no request in `handoff_out/` |
| F20, F42, F32, F47, F30 | 2026-11-15/16 | only in SCOPE's stage text |
| Per-point MCA files of plain scans (owner "yes", 2026-11-19); EXAFS reduction (macros read 2026-11-19) | physics_notes 2026-11-19 | input 14 only; no work item |
| Telling users which old reductions to redo (non-zero absorbers before P24; bu at 6.21/7.51/9.9 keV before F49) | TODO:104–110 | no release note or manual line |
| Disk-cache settings dialog "with the per-SPEC config, Stage 3" | TODO:68 | not in the Stage 3 list |
| GID burn test: largest peak by default, override | F22a(4) | no |
| The Excel workbook per SPEC file | owner, 2026-11-21 | not in FEATURE_REQUESTS; relation to D1–D3 unrecorded |
| sh scans paired with GID levels (sample height drifts by µm in 30–60 min) | physics_notes 2026-11-19 | beamline side only; no reader item |
| **`series.infer` calls XFNTR scans reflectivity.** All 153 `fluo_p` (`#V` hklscan) scans of the private XFNTR file are inferred as reflectivity series, and some of those series also hold Pilatus scans; `Experiment.point_times` uses these series for the macro start | **measured** for this review | new |
| `group(info) or infer(info)`: a file whose later scans have series lines and earlier ones not gets no inferred series at all | `experiment.py:182` (read) | new |
| `#U SeriesMacro` is parsed into the scan's parameters but never reaches `Series.macro` (`group` looks for a `macro` key in the Series fields) | `series.py`, `spec_routines.py:209` (read) | new |

## 4. Plan: scan macros and series with a little new metadata

### What is parsed already

| Line | Parsed | Used |
|---|---|---|
| `#U Series id= i= n= kind= role=` (any further `key=value` kept) | yes, `spec_routines` → `parse_series` | `series.group`: grouping, missing scans, status, resumed runs |
| `#U SeriesMacro …` | yes, into the scan's parameters | not attached to the series (section 3) |
| `#U SeriesT0 <s>` | yes | `timing.point_times` (time since the macro started) |
| `#C Series id= end status= after=` | yes | status |
| `#C … Scan aborted after k points.` (SPEC already writes it) | yes | partial and aborted status |
| no lines (every file so far) | `series.infer`: reflectivity and GID only | GID survey, point times |

### The minimum new metadata

Hand-off 05 is nearly minimal; the review cuts it to five fields and three lines.

| Line | Fields | Essential? | Gives |
|---|---|---|---|
| `#U Series` on each data scan | `id`, `i`, `n`, `kind` | **essential** | (a) grouping, (d) missing/aborted/in progress, (b) the reduction |
| `#U Series` on other scans of the run | `id`, `kind`, `role` (align, direct, background, check), no `i` | **essential** | alignment out of reductions; direct beam and background found |
| `#U SeriesT0` on the first scan | Unix s | essential for new files (time since start) | dose and time axes |
| `#C Series id= end status=completed\|aborted after=i` | from the macro's cleanup | strongly recommended | removes the one remaining guess (last series of a file that stopped growing) |
| `#U SeriesMacro` | command as typed | nice | provenance, re-running |
| `level=k` | GID Qz level, or the level an sh scan belongs to | nice | pairs height scans and background frames with levels (P40, sample drift) |
| `line=<El>_<Ka>` | fluorescence line of interest | nice | XFNTR/EXAFS fit without asking (D47) |
| `sample=` | sample name or counter | later | group several series of one sample (hand-off 05, question 3) |

Not needed from the macros: absorber, gain, slits, Qz, energy, detector
(already in each header; `fluo_p` writes `#A` and gain, measured above).
No version field: the reader versions its own results (below).

**SPEC side, kept small:** the experiment macro sets four globals (id, i,
n, kind; role defaults to data) before each scan and clears them at the
end; one per-scan header hook (`Fheader`, already used for `#A`, `#B0`,
`#W`) prints the `#U Series` line when the id is set, and `cleanup_once`
writes the end line. The scan macros themselves (`hklscan`, `ascan`,
`MCAscanpt`) are not changed. Hook names are from reading, not tried.

### Which macros write what

| Macro | kind | n | Other scans (role) |
|---|---|---|---|
| reflectivity (Qz segments) | reflectivity | segments planned | sh/oh realignments: align; direct-beam scan: direct |
| GID levels (`ascan dth` per Qz level) | gid | levels × Det_Th ranges | sh scan per level: align, `level=k`; background frames: background |
| XFNTR loop over `fluo_p` | xfntr | repeats planned (one hklscan each, spectrum per point) | alignment: align |
| `fluo_p` by hand | xfntr | 1 (own id) | — |
| EXAFS `<el>_exafs`, `*_edge` (`MCAscanpt escan_14`) | energy | energy scans planned | — |
| burn tests (fixed-position `ascan`) | burn | scans planned | — |
| `eb_expose` (no scan) | — | — | a `#C Series id= expose t= abs=` comment, nice (dose on the time axis) |
| alignment macros run alone | alignment | — | nothing needed: inferred |

### What the reader does with each

| Need | Reader action | Status |
|---|---|---|
| (a) group | scan list shows "gid 2/2 (partial)"; one click selects the series; tooltip gives the why | core done; window to do |
| (b) reduction | `kind` → offer (F60): reflectivity → Ref Patch; gid → GID worksheet; xfntr → MCA sum/`fit_series` + Merge; energy → `fit_series` against energy; burn → burn test; role align/check hidden; direct → normalisation reference | new |
| (c) results | workbook "Scans" sheet: scan, series id, i/n, kind, role, status, inferred; "Saved results": result id, series id, scans used, reduction, settings hash, reader commit, time, status at save; a result is flagged stale when its series later gains scans | new; workbook in progress |
| (d) cancel, resume, live | status from `group`; same id later = resumed, missing i filled, saved results marked stale; live mode polls the file while the last series is in progress, re-reduces on each new scan, stops at the end line or at n | status done; polling to do |

Inferred series have ids `inferred-<first scan>`, which shift if the rules
change: the workbook must store the scans list with every result, and map
an inferred series to a real id when one appears.

### Staged plan

| Step | Work | Size | Needs |
|---|---|---|---|
| R1 | `infer`: `#V` hklscans as xfntr, `escan` as energy, fixed-position Pilatus `ascan` as burn; group lined scans and infer the rest; attach `SeriesMacro`; tests on synthetic files and the NX file | S | — |
| R2 | Window: series in the scan list, select a series | M | — |
| R3 | Workbook ties (columns above), stale flag | S–M | workbook agent |
| R4 | `kind` → offered reduction (offer, not run) | M | — |
| M1 | Owner answers hand-off 05's four questions and this minimum | S | owner |
| M2 | Reflectivity and GID macros write the lines; a test SPEC session; one real file to the repo (public sample) | M | beamline |
| M3 | `fluo_p`, EXAFS, burn, end line from cleanup | S each | beamline |
| R5 | Fixture from M2's file; live refresh against a growing file in `tmp_path`; resumed-run and aborted cases already in `test_series.py` | L | M2 |

## 5. Top 10 next actions

| # | Action | Size | Owner? |
|---|---|---|---|
| 1 | Apply section 1's corrections (one docs commit, after the concurrent work lands) | S | no |
| 2 | Fix `series.infer` and the `SeriesMacro` gap (R1) | S | no |
| 3 | Send the owner hand-off 05's questions with section 4's minimum | S | yes |
| 4 | Workbook per SPEC tied to series id and scans used; record it as a feature request with D1–D3 | M | confirm layout |
| 5 | Series in the scan list and selection as one action (R2) | M | no |
| 6 | MCA tab and SpecPlot fits on the peak module; `fit_series` for MCA series (P9, P20, F22a) | M | no |
| 7 | P41: join against everything joined so far | S | no |
| 8 | Hand-off 06 run on the large GID data set | L | yes (data) |
| 9 | Live refresh by polling (F1–F5), driven by series status | L | no |
| 10 | Ask the owner the forgotten questions in one batch: P9–P12, P19, P35, P21, open assumptions, F41 (to the hand-off author) | S | yes |
