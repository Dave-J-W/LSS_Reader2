# To do

Current phase: **implementation**, following `SCOPE.md`. The owner gave the
go-ahead on 2026-11-17 ("begin the implementation plan").

| Stage | Status |
|---|---|
| 0 Safety net (error handler, durable log, messages pane) | **done** 2026-11-17 |
| 1 Repair what is plainly broken | **done** 2026-11-17 |
| 2 Readers and reduction out of the window; caching; scripting | **done** 2026-11-18 (quick 337, slow 542, sweep 67 passed) |
| 3 Saved state per SPEC file; live refresh | **started** 2026-11-19: series syntax proposed (`handoff_out/05`), reader parses it and SPEC's abort comment, guesses series in older files |
| 4 Detectors and inputs | not started |
| 5 Reflectivity export, uncertainty, ORSO/HDF5 | not started |
| 6 Sub-projects (GID patching, fitting, beam size, GUI) | **GID started** 2026-11-18 at the owner's request (D36: pinhole patch, worksheet, joins, beam response); fitting, beam size, GUI not started |

## Inputs needed from the owner (consolidated 2026-11-19)

Ordered by what they unblock. "Can proceed" means work goes on with a
stated assumption until the answer arrives.

| # | Input | Unblocks | Without it |
|---|---|---|---|
| 1 | Answers on the series proposal (`handoff_out/05`, four questions) | Stage 3 series in the window, live refresh | can proceed on the proposed syntax as provisional |
| 2 | ~~A complete low + high Qz GID pair~~: private pairs received 2026-11-19 (C22); a **public** pair is still wanted for C14 | C14 comparison, F62 check on real data, P36/P37 need three levels | C14 stays "not like for like" |
| 3 | One full two-module 200K frame (one module is saved on purpose, D43; the second lies along 2θ, F63); a new-format fluorescence/GID SPEC file (F28); HDF5/bluesky file (F29); ME7 notes (F35; mostly answered by D48, D49); Pilatus + Vortex in one scan (F53); 1M geometry conventions (F38) | Stage 4, item by item | Stage 4 not started |
| 4 | `lss_reference.py`, `covariance_core.py` (XModJointFit) | Stage 5 hand-off tests 5–6 | independent implementation from the hand-off text |
| 5 | ~~`Monc`'s own noise~~: not needed (owner, 2026-11-19, D44). Which monitor model the Budget uses by default when it becomes the default: Gaussian 0.04 % (D22, now) or Student t (D26)? | Stage 5: Budget as default | Gaussian stays the Budget's default |
| 6 | ~~IDL `IMG_COO_CONV`/`LIMG_COO_CONV`, `SCAN_JOIN`, `SPEC_FILE_INFO`~~ received 2026-11-19 (`docs/reference_code/idl/`); still wanted: IDL output for NX 11+12 | checking the pinhole map against IDL numbers | pinhole checked on synthetic data and by reading |
| 7 | IDL review §8: column response from data or geometry; per-column patch replacing or beside the 3-column one; PD_MERGE | GID defaults | pinhole default (D40), response fitted |
| 8 | Reflectivity series with overlaps at 6–7 keV; foil tolerance and alloy; Cu thickness at 30 keV | P28 below 10 keV; F49 at 30 keV | nominal Al below 10 keV; no factor at 30 keV |
| 9 | P29 mechanism (Monc high at narrow S1) | whether the 3 % Monc/Monp guard is right | guard as built |
| 10 | Confirm or change the open assumptions in `OUTPUT_DECISIONS.md` (3 % tolerance; per-photon gas and median rate; GID min frames, β step) | — | as built |
| 11 | Fitting requirements received (F22a, 2026-11-19); scoping later. Burn tests and peak fits scriptable: with that scoping | Stage 6 fitting | not started |
| 12 | Run the build workflow once; macOS signing decision | packaged releases | Linux build measured only |
| 13 | ~~`bu.zip` link sharing~~ off (owner, 2026-11-19); where sample data live; ~~resend scan-136 frames~~ received 2026-11-18 | — | — |
| 14 | P7 Merge: kept as is (owner). Merge window and XFNTR merging: the owner's rule is F65 (match within 0.1 × grid step, jitter 3e-5 1/Å in the errors, grouping, never across runs); its edge estimator is backlog. `S1T + S1T`: fixed. Per-point MCA files: to be handled (owner: yes, 2026-11-19); channels and dead time answered (D48, D49) | F65, per-point MCA | — |
| 15 | ~~P39~~: decided 2026-11-19 (D51), exact window to the S4 ramps' inner edges; IDL's as an option | — | — |
| 16 | Half-cut sh scans for the beam's vertical profile (F43; owner, 2026-11-19) | a measured beam for response 'beam' and for P39 | the profile fitted from the GID data |
| 17 | GID frames with little signal (mostly background) at both arm heights (P40; owner offered, 2026-11-19) | stray light and beam-path background in GID maps | P40 open |
| 19 | ~~S4–detector distance (P43)~~: calibrate from single frames (owner, 2026-11-21): built, worksheet Fit; automatic calibration and the final GID defaults: large-data survey, `docs/handoff_out/06-gid-method-comparison.md` | — | header value until Fit |
| 18 | GID overlap pixels: ΣN/ΣW (built) vs IDL's error-weighted mean (the owner chose "as the IDL code does", 2026-11-18; the error weights are biased at low counts, IDL review) | GID map values | ΣN/ΣW, to confirm |

### Stage 3 work list
- [x] Proposal for the "scan i of N" line (`docs/handoff_out/05-scan-series-syntax.md`).
- [x] Reader: `#U Series`, `#U SeriesMacro`, `#C … Scan aborted after k points`,
      `#C Series … end`; `lss_core/series.py` groups, finds missing scans and
      the status (complete, partial, in progress, aborted); `infer` for older files.
- [ ] Owner/beamline: answer the proposal's four questions; try the lines in SPEC.
- [ ] Window: series in the scan list (label "gid 2/2 (partial)", details in
      the tooltip), select a series as one action.
- [ ] Live refresh (F1–F5): poll the SPEC file and image folders, append, keep
      selections, re-reduce a series in progress.
- [ ] Per-SPEC saved state (F13–F16), dropped points as masks with undo.

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
- [ ] Gains the reader cannot interpret: malformed lines (D33), treated as
      unknown; nothing more to sort out unless the owner wants them read
      (`reports/monitor_gains.md`).
- [x] F54 core: photons/s from the monitor (`lss_core/flux.py`, xray_fluxor route D).
- [x] F54 in the window: "/ photon" option (MonC, dark 50 Hz when not recorded,
      D41), scripts `per_photon=True` (2026-11-19).
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
- [x] An unreadable `#A` line (one real case: an empty "#A Absorber " in
      bu/2026oct/20261019) was read as 63; now unknown: no factor, a message,
      "Abs=?", frames patched as usual (D42, 2026-11-19).
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
      (D22); Student t offered (ν = 4, D26; 3.6 was the first estimate).
- [x] Cuts scriptable (2026-11-18): `lss_core/cuts.py` (`frame_cut`, shared by
      the window and `Experiment.cut`); Export writes `exp.cut(...)` to the
      Script pane, reproducing the files byte for byte (all directions, axes,
      Sum, Budget, typed geometry, pinhole, partial frames). The window's cuts
      were unchanged in all 48 configurations compared before/after.
- [ ] Stage 3 frame object: normalise once at load; make each reduction's
      normalisation explicit (owner's expectation, 2026-11-17).
- [ ] New output formats record reduction steps and parameters (R7).
- [x] GID scriptable (2026-11-19): `Experiment.gid`, one implementation with
      the window (`lss_core/gid.py`), Save GID writes the call; byte-identical.
- [ ] GISAXS scriptable; background-subtracted GID and cuts scriptable.
- [x] Exact pinhole geometry per pixel (P38; owner 2026-11-19, "is your trig up
      to snuff?"): `pinhole.pixel_angles` (IMG_COO_CONV), GID patch binned in (2θ, β).
- [x] Beam profile: response 'beam' built as an option (2026-11-19); default 'fit'.
- [ ] The upper-level difference (pinhole vs legacy) on a private pair: the three central
      columns reproduce legacy; adding the outer columns changes the upper level relative
      to the lower; not area, polarisation or the response model. Next: maps from column
      groups (inner, middle, outer) per level, and the β-overlap cells of the Qz join.
- [ ] P38 remainder: exact angles also for the cuts' pinhole axis and the image
      display axes; the distance fit with exact angles.
- [ ] F63: second 200K module along 2θ for GID: detector description with the
      gap (Stage 4), then the pinhole patch over both modules; ask for a full frame.
- [x] Per-point times, old and new files (F37 reader side; owner's guidance 2026-11-19):
      `lss_core/timing.py`, `Experiment.point_times`.
- [x] Time as an x axis in the SPEC plot (`Time_s`, D46).
- [ ] Time as an x axis in the other plots: MCA integrals (per spectrum: its
      scan point's time), Ref/GID frame lists; burn tests (below).
- [ ] F65 step 3 (backlog): if built, the edge from the fitted element line
      (D47), not ln(Vortex/Monc).
- [ ] Use the measured times where the reader now assumes count time × frame
      (burn tests: `pilRefBurn`, `pilGidBurn`; would change their outputs: ask the
      owner, with F22a's burn-fit work) and show times in SpecPlot (x = time).
- [ ] Backlog (owner, 2026-11-19): F65's edge estimator (steps 3, 4, 6: steepest rise of
      ln(Vortex/Monc), outlier check against the group median, alignment).
- [ ] P36, P37 (legacy GID with three Qz levels): fix with a synthetic
      three-level GID data set; outputs change only for such maps.
- [ ] Docket (2026-11-18): F59 cuts for diffuse scattering (I vs β, β − α;
      the Q cuts' default ranges miss the detector and plot zeros silently),
      F60 contextual/automatic reduction. Not to be built yet.
- [x] F61 GID worksheet (2026-11-18): the patch's settings editable, joins
      tabulated; defaults reproduce the patch exactly.
- [x] F45 pinhole correction, first version (2026-11-18): worksheet switch,
      off by default; physics_notes 2026-11-18.
- [x] Pinhole the default (D40), P32 and P34 fixed (2026-11-18).
- [x] F62 flexible overlaps between Qz levels, pinhole mode (2026-11-19).
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

- [x] Remaining feature requests and complaints (received so far: F1–F16
      in `FEATURE_REQUESTS.md`; the owner called the latest list partial). (Requests received through F65; new ones are added as they come, 2026-11-19.)
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
- [ ] **Remind the owner:** a full two-module 200K frame (the 200K data received are one module, 2026-11-19); a reflectivity
      burn scan; a public low + high Q_z GID pair (private pairs received 2026-11-19); the new fluorescence &
      GID SPEC file (F28); an HDF5/bluesky file (F29); ME7 data notes (F35).
- [x] Monitor noise investigated (`reports/monitor_noise.md`).
- [x] Beam variation vs monitor noise examined (`physics_notes.md`,
      2026-11-16): `Monc`'s scatter in reflectivity scans is mostly real
      flux variation through S1, which the detector also sees.
- [x] ~~Measure `Monc`'s own noise before a normalisation model is chosen~~: not
      needed, the Student t model is good enough (owner, 2026-11-19, D44).
- [ ] **GID background data (P40, 2026-11-19; owner offered GID data with
      little signal):** frames at both arm heights with the same slits;
      if possible the sample lowered out of the beam, S5 nearly closed at
      the raised arm, the lower level repeated after the upper, and the S4
      and S5 vertical openings and the S5 → detector flight path.
- [x] Is the MCA "Merge" weighted mean Σ(y²/σ²)/Σ(y/σ²) intended? Explained 2026-11-19
      (it equals ΣN/ΣM, pooled counts over pooled monitor); owner to confirm. Owner, 2026-11-19: kept as is; the error is handled downstream (F65).
- [x] Scoping input for F22 (where better fitting is needed, which models)
      and F23 (GID patching: overlaps, methods). F22a received 2026-11-19; F23 superseded by the pinhole GID work (D36).
- [ ] Format of the photons-in estimate in the SPEC file (F21), when the
      beamline defines it.
- [x] Pilatus 1M: another version handles it but is not otherwise better;
      stay on this code base, 1M support is feature group F17–F19.
- [x] Should per-point MCA files (`mca_save_point`) be readable from the
      window? Open points on the 1M are listed under F17–F19. Owner, 2026-11-19: yes (F53).
- [x] Bruker/Apex CCD is defunct (D8): no fix; remove the code later.
- [x] Link sharing off on `bu.zip` (owner, 2026-11-19).
- [ ] Decide how sample data should be hosted (`bu` is 1.7 GB, local to the
      session only, git-ignored; NX school is committed at 104 MB).
- [ ] Questions in `ASSESSMENT.md` sections 6 and 7 still open: reference
      geometry for image axes vs cuts (P6), negative 2θ (P5). (S1T + S1T fixed
      2026-11-19; 9-ID-C answered, D17.)

## Original phase plan (superseded by SCOPE.md stages; kept for history)

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

- Note (owner, 2026-11-17): `getandsave_mca` is a test macro, not the normal
  XFNTR scan (`fluo_p`, an MCAscanpt hklscan with a `#V` line); the two
  items below matter only for it. Whether `fluo_p` scans write `#A` and
  `#M Monc Gain`: to check on the next new file.
- [ ] **`getandsave_mca` writes no absorber setting** (`#A`): checked on
      every sample file; the MCA file header has none either. The reader
      takes the last `#A` above the scan (D24), which cannot see a change
      made between scans by a command that is not a scan. (owner, 2026-11-17)
- [ ] **`getandsave_mca` writes no monitor gain** (`#M Monc Gain`), and the
      gain changes within files (P26, F52).
- [ ] Some `#M Monc Gain` lines have no unit ("200") or no value
      (bu/2026oct/20261019, 20261022); the reader treats them as unknown.
      Full list: `reports/monitor_gains.md`.
- [ ] `#V` detector-type flag, 1, 4 or 7 elements (F34).
- [ ] Series lines `#U Series …`, `#U SeriesMacro`, `#U SeriesT0` (F39;
      proposal `handoff_out/05`, under review by the owner's agent, 2026-11-19).
- [ ] Per-point `Tstart` and `Tend` in place of `Epoch` (F37; owner, 2026-11-19).
- [ ] Photons-in estimate in the SPEC file (F21), when the beamline defines it.
- [ ] Half-cut sh scans to characterise the beam (F43), and a height (sh) scan
      next to each GID level: the liquid's height drifts by several µm in half an
      hour to an hour (owner, 2026-11-19), which moves the footprint by mm.
- [ ] Multiple exposures per GID point (F40).
- [ ] A scan with both Pilatus and Vortex data should say so in its header
      in a way that does not let one line override the other (F53).
- [ ] **Gas conditions for photons/s** (F54; owner, 2026-11-19): record the
      ion-chamber temperature and pressure, or the current photons/s
      number from the monitor IOC. The reader now assumes the hand-off
      table's 24.9 °C and 98.99 kPa (±0.8 % from the site-mean pressure).
- [ ] **Dark counts** (F54, D41; owner, 2026-11-19): record the dark rate
      from the new monitor IOC. The reader now assumes 50 Hz on Monc.
- [ ] One `#A` line with no value (bu/2026oct/20261019, scan 1): the macro
      should always write the setting. The reader treats it as unknown (D42).

