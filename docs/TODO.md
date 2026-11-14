# To do

Current phase: **tests, assessment and scoping only.** No changes to
application code until the full list of feature requests has been received
(owner's instruction, 2026-11-14).

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
      MCA peak fit / sum / merge, peak-fit dialog, 2D plot tab, Bruker path.
- [x] NX school GID scan 11 frozen as a reference; low + high Q_z patch
      pinned as an expected failure (interp2d). The shipped
      `dppc_*_gid.txt` come from other scans and are not comparable.
- [ ] Find or make a complete low + high Q_z GID pair to test patching
      (scan 12 here has only 4 frames).
- [x] Invariant I4 (ROI error propagation) tested directly.
- [x] Python 2 → 3 audit → `ASSESSMENT.md` section 8; Bruker reading and
      the g_l2 dialog pinned as expected failures.
- [ ] Tests for the output file formats (`*_ref.txt`, `*_rrf.txt`, GID,
      cut and `*_flu.txt` files): columns, units, number formats, since
      xmodfit reads them.
- [ ] End-to-end "known photons per monitor count in, same number and
      Poisson error out" check for each reduction path (GID, GISAXS, cuts,
      MCA sum), as already done for reflectivity.
- [ ] Regenerate `docs/timings.md` on an idle machine (the committed table
      predates the file-count columns).
- [ ] Write the scoping document once the feature list is complete:
      target architecture, order of work, what each request needs.

## Waiting on the owner

- [ ] Remaining feature requests and complaints (received so far: F1–F16
      in `FEATURE_REQUESTS.md`; the owner called the latest list partial).
- [ ] Answers to the three questions in `PROJECT_CONTEXT.md` (divide by
      counting time? which fitting features stay? which output files does
      xmodfit read?).
- [x] Pilatus 1M: another version handles it but is not otherwise better;
      stay on this code base, 1M support is feature group F17–F19.
- [ ] Should per-point MCA files (`mca_save_point`) be readable from the
      window? Open points on the 1M are listed under F17–F19.
- [ ] Is the Bruker/Apex CCD path still needed? It cannot read any image
      under Python 3.
- [ ] Turn link-sharing off on `bu.zip` in Drive.
- [ ] Decide how sample data should be hosted (`bu` is 1.7 GB, local to the
      session only, git-ignored; NX school is committed at 104 MB).
- [ ] Questions in `ASSESSMENT.md` sections 6 and 7 (S1T + S1T, reference
      geometry for image axes vs cuts, 9-ID-C still needed, negative 2θ).

## Later phases (not started, by instruction)

1. Bug fixes from `ASSESSMENT.md` section 4, one test each.
2. Empty the crash inventory (`tests/known_crashes.json`).
3. Extract physics and readers into GUI-free modules.
4. Feature requests in `FEATURE_REQUESTS.md`.
5. GUI reorganisation.

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
