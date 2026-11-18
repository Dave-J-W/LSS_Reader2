# To do

Current phase: **implementation**, following `SCOPE.md`. The owner gave the
go-ahead on 2026-11-17 ("begin the implementation plan").

| Stage | Status |
|---|---|
| 0 Safety net (error handler, durable log, messages pane) | **done** 2026-11-17 |
| 1 Repair what is plainly broken | **done** 2026-11-17 |
| 2 Readers and reduction out of the window; caching; scripting | **done** 2026-11-18 (quick 337, slow 542, sweep 67 passed) |
| 3 Saved state per SPEC file; live refresh | **next** (needs the "Scan i of N" header syntax) |
| 4 Detectors and inputs | not started |
| 5 Reflectivity export, uncertainty, ORSO/HDF5 | not started |
| 6 Sub-projects (GID patching, fitting, beam size, GUI) | not started |

### Stage 2 work list
- [x] Fast, cached image reading, bit-identical (`lss_core/images.py`,
      `lss_core/cache.py`); no file is re-read on a selection change (D5,
      F7, F9).
- [x] Rapid image-list selection changes (drag, shift-click, keyboard) are
      merged into one redraw after 150 ms: 27 quick clicks 24 s -> 1.1 s.
- [ ] Redraw itself (~1 s for 9-10 frames): build the axes once and update
      the images in place when only the selection changed; `tight_layout`
      is ~20 % of it. Belongs with the GUI reorganisation (Stage 6).
- [x] SPEC and MCA readers without `eval` (`lss_core/numbers.py`): identical
      results on every sample file; MCA 24 → 1.2 ms per spectrum (F6).
- [x] Disk cache for network drives (F8): `lss_core/diskcache.py`; decoded
      frames as `.npy` in `~/.lss_reader/cache`, only for files on another
      file system by default, 5 GB limit (D18), LRU; settings by environment
      variable (a settings dialog comes with the per-SPEC config, Stage 3).
- [x] Reflectivity reduction scriptable without Qt (`lss_core/experiment.py`,
      `reflectivity.py`, `stitching.py`; `docs/SCRIPTING.md`): byte-identical
      to the window's files on synthetic and real data (F31, first part).
      The window uses the shared stitching code.
- [x] The window's Ref Patch computes each point with
      `lss_core.reflectivity.frame_row` (one implementation; the duplicated
      per-frame branches are gone). Scan order, drops and finishing in the
      window still mirror `lss_core` and are checked by the same fixtures.
- [x] Fluorescence (MCA window sum) scriptable and shared with the window;
      byte-identical `_flu.txt`; Script pane line on export.
- [x] Cuts normalised by monitor and absorber (D19, P23 fixed).
- [x] Error budget (D20): "Budget" error model, monitor term on whole sums,
      in every non-patched path and in Ref Patch's per-frame points;
      Errors pane; `errors=` in scripts. Legacy stays default.
- [x] Absorbers consistent (D21): messages when frames of different foil
      counts are combined on the nominal factor.
- [x] `Monc` is upstream of the absorbers (owner): a^n does not double-count.
- [x] Foils are before the sample; `#A` is in units of the absorber factor
      (≈ 1.414 at 10 keV, now the default).
- [x] F50 (D24): MCA scans take the absorber of the last `#A` above them;
      normalised spectra × absfac**n; the window says where each came from.
- [x] F52 option: normalise by `Monc` × its recorded gain (MCA, SpecPlot,
      scripts). Off by default.
- [x] F52 in the Pilatus paths (cuts, background images, GID data, frames
      at one Q_z).
- [ ] Sort out the gains the reader cannot interpret (owner, later):
      `reports/monitor_gains.md`.
- [x] F54 core: photons/s from the monitor (`lss_core/flux.py`, xray_fluxor route D).
- [ ] F54 in the window: "per incident photon" normalisation option (needs the dark rate
      or an accepted 0, and which lane: MonC by default).
- [x] Student t: σ_scan · w · t₄, w ≈ 0.94, σ_scan 0.039 % if unknown (D22).
- [x] "width" is the t's scale (owner); σ_scan per scan declined: fixed t (D26).
- [x] Absorber factor default: 50 µm Al at 10 keV, 1.4247 (D25).
- [x] **P24 fixed**: the factor in use is the one shown (it was 1.606 from
      start-up until a GID/Ref action re-read the field). Old background-
      subtracted reductions at non-zero absorber settings should be redone.
- [ ] F53: Pilatus and Vortex from the same scans (tabs); needs a sample file.
- [x] F49 for Al (2026-11-18): the field follows the scans' energy ("from E").
      Reductions of bu scans at 6.21 / 7.51 / 9.9 keV with absorbers in
      should be redone (factor was 1.4247 per unit).
- [x] Crash site found by the sweep after "from E" (2026-11-18; the extra
      control changed the random walks): SPEC plot with log Y and a column
      that is 0 (Y2 = H in an L scan) raised FreeType 'raster overflow' on the
      point labels. Labels of points a log axis cannot show are now hidden.
      Sweep before the fix: 65 passed, 2 failed (this site); after: both pass.
- [ ] F49 for Cu at 30 keV: needs the unit thickness (owner).
- [x] Foils at 10.05 and 10.52 keV: aluminium (owner, D37).
- [x] `#A` 52 and 63 are real settings (owner, D38).
- [ ] Issue: an unreadable `#A` line is read as 63 (`spec_routines.py`), which looks
      like a real setting; it should be "unknown" (no factor, a message).
- [ ] P28: nominal absorber steps 7–11 % off measured (NX school). Owner:
      reflectivity sets with overlapping joins from several days, to test
      day-to-day variation and calibrate per foil (`tests/tools/absorber_steps.py`);
      foil tolerance (flat µm or %) and alloy, if known.
      Hand-off for that analysis written 2026-11-18:
      `docs/handoff_out/02-absorber-patch-check.md` (+ `02-absorber_steps.py`);
      Answered 2026-11-18 (`handoff_out/02-answer-report.md`), reviewed
      in physics_notes: foils calibrated at 10 keV, stable over the year;
      the jumps are the monitor (P29).
- [x] Calibrated foil table in the reader (F56), Preferences (F57), known
      ratio in Ref Patch (F58), 2026-11-18. Off 9.70–10.30 keV the
      composition is needed (P28).
- [ ] Owner (P29): in R04/R05 and R17–R21 `Monc` reads high at S1 = 0.04 mm
      (scan a), by up to ×1.46; not an offset (needs beam). Scatter from the
      S1 blades into Monc, or where the beam sits on the narrow slit? Known
      at the beamline only.
- [x] Hand-off 03 answered (`handoff_out/03-answer/`): fit reproduced to
      0.1 µm; P29 is scan a's Monc reading high at the narrow S1 gap; figures.
- [ ] Owner (P28): reflectivity series with overlaps at 6–7 keV, to
      separate foil composition from thickness.
- [x] Gain reference S_ref = 5 µA/V (owner, D39).
- [ ] When the corrected/legacy two-file export (hand-off §2.5) is built,
      make Budget the default and carry the counting part as `sigma_meas`.
- [x] Monitor model default from the owner's analysis: Gaussian 0.04 %
      (D22); Student t ν = 3.6 offered.
- [x] Cuts scriptable (2026-11-18): `lss_core/cuts.py` (`frame_cut`, shared by
      the window and `Experiment.cut`); Export writes `exp.cut(...)` to the
      Script pane, reproducing the files byte for byte (all directions, axes,
      Sum, Budget, typed geometry, pinhole, partial frames). The window's cuts
      were unchanged in all 48 configurations compared before/after.
- [ ] Stage 3 frame object: normalise once at load; make each reduction's
      normalisation explicit (owner's expectation, 2026-11-17).
- [ ] New output formats record reduction steps and parameters (R7).
- [ ] GID and GISAXS scriptable: part of the GID sub-project (F23), which
      the owner wants scoped separately.
- [ ] Docket (2026-11-18): F59 cuts for diffuse scattering (I vs β, β − α;
      the Q cuts' default ranges miss the detector and plot zeros silently),
      F60 contextual/automatic reduction. Not to be built yet.
- [x] F61 GID worksheet (2026-11-18): the patch's settings editable, joins
      tabulated; defaults reproduce the patch exactly.
- [x] F45 pinhole correction, first version (2026-11-18): worksheet switch,
      off by default; physics_notes 2026-11-18.
- [ ] GID next: F62 flexible overlaps between Qz levels (common range,
      count-over-weight overlap); P34 and P32 fixes; then decide with the
      owner whether pinhole mode becomes the default for Det_Th > 1°.
- [x] Distances settled (owner, 2026-11-18): 551 sample→detector, 271
      S4→detector, 556 = g_l3 (sample → output-arm rotation centre).
- [ ] Owner (IDL review §8): the missing routines `SCAN_PD_READ`,
      `SCAN_PD_LCOO`, `IMG_JOIN`, `PD_GID_READ`, `PD_PIN_RANGE` (+ FILDAT
      definitions) and IDL output for NX scans 11+12; is `S7D_Dist` the
      S4-to-detector distance; are GID scans routinely pinhole mode (switch
      on from the S4 gap?); per-column mode replacing or beside the 3-column
      patch; column response from the data or geometric; overlap arithmetic;
      β per column; one absorber setting for GID; what PD_MERGE's pinhole
      data are.
- [ ] Owner: resend the scan-136 GID frames as a zip (the image uploads
      arrived as float16 zeros).
- [ ] → Stage 6: burn tests and peak fits scriptable, with the fitting
      sub-project (analysis tools, not reduction); P30 (burn test not
      monitor-normalised) to be fixed then.
- [x] Script pane (F48, first part): opening a SPEC file and exporting a
      patched reflectivity write the equivalent `lss_core` Python, which
      reproduces the exported files byte for byte (tested), including merges,
      drops and partial frame selections. Other actions follow as they
      become scriptable.
- [x] Resources (`.ui`, icons) loaded relative to the program, not the
      working directory (`lss_core/resources.py`; prerequisite for F46).
- [x] F46 packaged builds (2026-11-18): `packaging/lss_reader.spec`, pinned
      libraries, `--self-test`, GitHub workflow (Windows, macOS; manual or
      tag). Linux build measured here (self-test passed). The old recipe and
      the committed `build/` folder (an old .exe) are removed. The About box
      no longer needs the .py files (it raised in a build).
- [ ] Owner: start the build workflow once (Actions → build → Run
      workflow) and try the Windows/macOS builds; macOS signing is a
      decision (docs/PACKAGING.md).

### Stage 1 work list
- [x] Typos and leftovers: defects 2, 3, 4, 5, 6, 7, 14 and the shared
      default dictionaries; NumPy 2 scan-list formatting with one helper
      (D14).
- [x] `interp2d` replaced (`interp_compat.py`); GID low + high Q_z patching
      works on current SciPy and reproduces the SciPy 1.13 reference
      (defect 1).
- [x] Qz² export fix (F24b).
- [x] Crash inventory, image-display and 2D-plot handlers (153 pairs).
- [x] Crash inventory, reflectivity handlers (93 pairs).
- [x] Crash inventory, everything else: cuts, MCA, SpecPlot, images and
      background, calibration actions (151 pairs).
- [x] Baselines regenerated: 420 single-control combinations -> 3, then 0
      after the background-factor field was rewired.
- [x] Failures reached only by sequences: stale selections forgotten when
      the scan selection changes; movie frame indexing; cut export and fit
      button check their data; background sum with nothing selected; MCA
      log axes; 9-ID-C says it is unsupported.
- [x] All save handlers write nothing when the file chooser is cancelled.
- [x] Graceful opening: non-SPEC files (defect 4) and repeated scan
      numbers (F27).
- [x] Graceful opening (F27): missing images (also fixed a normalisation
      misalignment, PHYSICS_ISSUES P22), scan numbers not starting at 1,
      missing image folders with the chooser cancelled.
- [x] Bruker/CCD code removed (D8, F38); geometry kept in
      `ccd_geometry_precedent.md`; Apex tab hidden pending the GUI work.
- [x] Final sweep of Stage 1 (2026-11-17): 0 single-control failures in 14
      runs, 0 crash sites in 24 random sequences of 150 actions.
- [ ] Remaining read-only defects of `ASSESSMENT.md` §4 (8: 9-ID-C reader —
      removed, not needed, D17; 10–13, 15:
      physics, tracked in `PHYSICS_ISSUES.md` and not to be changed without
      the owner).

Working method for the crash inventory: Sonnet sub-agents, one at a time,
each given one group of handlers; the main session reviews the diff,
reruns the quick, real-data and export-fixture checks, and commits.

## Carried over from the tests-and-scoping phase

- [x] Time the full selection path on real data → `docs/timings.md`
      (`pytest -m bench`). Pilatus 1M and per-point MCA could not be timed
      through the window: this version cannot load them.
- [ ] Time the same path against a deliberately slow file system, to
      separate network cost from redraw cost.
- [x] Crash sweep covers controls inside secondary dialogs (one level).
- [x] Crash sweep runs each state with file dialogs cancelled and with
      file dialogs returning paths.
- [x] Random walks (150 steps, 3 seeds, 3 states) pinned by crash site.
- [x] Sweep made cheaper (one selection signal per action), then made
      stricter (fresh window per control).
- [x] `pytest -m slow` rerun in full: all pass, expected failures as marked.
- [ ] Characterisation tests still missing for: GID multi-scan joining
      (`imagehjoin`, `imagevjoin`), GISAXS, line/area cuts
      through the GUI, burn tests, g_l2/g_l3 and absorber-ratio fits,
      MCA peak fit / sum / merge, peak-fit dialog, 2D plot tab. (All fitting
      features stay, D7, so each needs tests. Bruker is defunct: none.)
- [x] NX school GID scan 11 frozen as a reference; low + high Q_z patch
      pinned as an expected failure (interp2d). The shipped
      `dppc_*_gid.txt` come from other scans and are not comparable.
- [x] GID low + high Q_z patch run under SciPy 1.13 and stored as the
      reference (NX school scans 11 + 12; scan 12 has 4 frames).
- [x] Invariant I4 (ROI error propagation) tested directly.
- [x] Python 2 → 3 audit → `ASSESSMENT.md` section 8; Bruker reading and
      the g_l2 dialog pinned as expected failures.
- [x] Reflectivity export pinned byte for byte (`test_ref_export_golden.py`)
      as the legacy fixtures the hand-off asks for.
- [x] XFNTR benchmark: synthetic with known line counts, `_flu.txt` bytes,
      and a hash of the real `bu` export.
- [x] Benchmarks added (R5, R6): burn tests (synthetic reflectivity with
      known τ; real GID burn), MCA peak fit, line cuts on real frames and
      through a real GID map.
- [ ] Benchmarks still missing (R5): GISAXS, GIOXS, calibration fits
      (g_l2, g_l3, absorber ratio), GID and cut export bytes, synthetic GID
      with known truth, a real reflectivity burn scan (none in the samples).
- [ ] Run each reduction path on Pilatus 1M frames by calling the code
      directly, to measure what the module gaps do (D11).
- [ ] Synthetic K = 3–5 scan generator with known factors and a non-one-hot
      overlap, as hand-off §5 requires, and the acceptance tests 2–4 written
      against the contract as expected failures.
- [ ] Measure the stitch-factor interpolation bias on real overlaps.
- [ ] ORSO export (F25): read the format specification and list the header
      fields the reader can and cannot fill.
- [ ] End-to-end "known photons per monitor count in, same number and
      Poisson error out" check for each reduction path (GID, GISAXS, cuts,
      MCA sum), as already done for reflectivity.
- [ ] Regenerate `docs/timings.md` on an idle machine (the committed table
      predates the file-count columns).
- [x] Scoping document written: `SCOPE.md`.
- [ ] (superseded) Write the scoping document once the feature list is complete:
      target architecture, order of work, what each request needs.

## Waiting on the owner

- [x] **Monitor noise analysis** (hand-off `handoff_out/01-monitor-noise-analysis.md`):
      answered 2026-11-17, Gaussian σ = 0.04 % (D22).

- [ ] Remaining feature requests and complaints (received so far: F1–F16
      in `FEATURE_REQUESTS.md`; the owner called the latest list partial).
- [x] Counting time and fitting questions answered (2026-11-15; D6, D7,
      F20–F22).
- [x] Hand-off on the xmodfit export received (F24, F25).
- [ ] **Remind the owner:** `tests/lss_reference.py` and
      `covariance_core.py` from XModJointFit (unreleased, not public) for
      hand-off acceptance tests 5 and 6. Until then, work around it with an
      independent implementation of hand-off §3 written from the text.
- [x] Stitch-factor interpolation bias: experiments ensure shared Q_z
      points for now (D13). **Do not forget:** it is to be remedied later
      in the corrected chain.
- [ ] **Remind the owner:** 200K sample data (offered); a reflectivity
      burn scan; a complete low + high Q_z GID pair; the new fluorescence &
      GID SPEC file (F28); an HDF5/bluesky file (F29); ME7 data notes (F35).
- [x] Monitor noise investigated (`reports/monitor_noise.md`).
- [x] Beam variation vs monitor noise examined (`physics_notes.md`,
      2026-11-16): `Monc`'s scatter in reflectivity scans is mostly real
      flux variation through S1, which the detector also sees.
- [ ] Before any normalisation model is chosen (owner's condition):
      measure `Monc`'s own noise with a bright steady signal (repeated
      direct-beam or total-reflection frames); decide whether to subtract
      the dark rate (~100 counts/s `Monc`).
- [ ] Is the MCA "Merge" weighted mean Σ(y²/σ²)/Σ(y/σ²) intended?
- [ ] Scoping input for F22 (where better fitting is needed, which models)
      and F23 (GID patching: overlaps, methods).
- [ ] Format of the photons-in estimate in the SPEC file (F21), when the
      beamline defines it.
- [x] Pilatus 1M: another version handles it but is not otherwise better;
      stay on this code base, 1M support is feature group F17–F19.
- [ ] Should per-point MCA files (`mca_save_point`) be readable from the
      window? Open points on the 1M are listed under F17–F19.
- [x] Bruker/Apex CCD is defunct (D8): no fix; remove the code later.
- [ ] Turn link-sharing off on `bu.zip` in Drive.
- [ ] Decide how sample data should be hosted (`bu` is 1.7 GB, local to the
      session only, git-ignored; NX school is committed at 104 MB).
- [ ] Questions in `ASSESSMENT.md` sections 6 and 7 (S1T + S1T, reference
      geometry for image axes vs cuts, 9-ID-C still needed, negative 2θ).

## Later phases (not started, by instruction)

1. Process-wide exception handler and durable log (F10–F12, D4): turns
   every hard abort into a logged failure. Agreed as the first step.
2. Bug fixes from `ASSESSMENT.md` section 4, one test each; empty the crash
   inventory (`tests/known_crashes.json`); remove the Bruker path (D8).
3. Extract physics and readers into GUI-free modules.
4. Feature requests in `FEATURE_REQUESTS.md` (caching and no re-reading on
   selection change, D5; live refresh; per-SPEC config with read-only
   second instance, D1–D3; Pilatus 1M; per-second option, F20; covariance
   export for xmodfit, F24, which needs the merge logic factored out of the
   dialogs; ORSO export, F25).
5. Sub-projects that need their own scoping: GID patching (F23), fitting
   improvements (F22).
6. GUI reorganisation.

## Done

- [x] First assessment (`ASSESSMENT.md`) and addendum with measured results.
- [x] Test scaffolding, synthetic data, fast suite (47 pass, 8 expected
      failures).
- [x] Crash inventory baseline, confirmed repeatable.
- [x] NX school sample data committed; real-data reflectivity regression.
- [x] `bu` sample data local; robustness run over all eight SPEC files.
- [x] Feature requests F1–F16 and project context recorded.
- [x] Never-writes-to-SPEC rule pinned by a test; hard-abort on a raising
      handler demonstrated and pinned as an expected failure.

## Beamline to-do (SPEC macros at 15-ID-C)

Things the data files should record and do not. The reader works around
them; the fix belongs in the macros.

- [ ] **`getandsave_mca` writes no absorber setting** (`#A`): checked on
      every sample file; the MCA file header has none either. The reader
      takes the last `#A` above the scan (D24), which cannot see a change
      made between scans by a command that is not a scan. (owner, 2026-11-17)
- [ ] **`getandsave_mca` writes no monitor gain** (`#M Monc Gain`), and the
      gain changes within files (P26, F52).
- [ ] Some `#M Monc Gain` lines have no unit ("200") or no value
      (bu/2026oct/20261019, 20261022); the reader treats them as unknown.
      Full list: `reports/monitor_gains.md`.
- [ ] A scan with both Pilatus and Vortex data should say so in its header
      in a way that does not let one line override the other (F53).

