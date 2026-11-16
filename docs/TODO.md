# To do

Current phase: **tests, assessment and scoping only.** No changes to
application code until the full list of feature requests has been received
(owner's instruction, 2026-11-14).

The owner supplied "the rest of the feature set" on 2026-11-16, and the plan
is written (`SCOPE.md`). **Implementation has not been authorised yet**:
wait for the owner's explicit go-ahead, then start with Stage 0 of
`SCOPE.md` and change this paragraph and `AGENTS.md` in the same commit.

## Next up (this phase)

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
