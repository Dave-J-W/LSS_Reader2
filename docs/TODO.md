# To do

Current phase: **tests, assessment and scoping only.** No changes to
application code until the full list of feature requests has been received
(owner's instruction, 2026-11-14).

## Next up (this phase)

- [ ] Time the full selection path on real data (select scan → frame list →
      frames shown; reflectivity patch; MCA selection), per step, so the
      speed requests F6–F9 have a baseline. Include Pilatus 1M file reads.
- [ ] Extend the crash sweep to the controls inside secondary dialogs
      (peak fit, GIOXS, burn test, form factor, ref patch, MCA merge,
      plot scale, g_l2/g_l3, absorber ratio).
- [ ] Extend the crash sweep to file dialogs that return a path (save and
      open), writing into a temporary directory.
- [ ] Add multi-step sequences to the sweep (random walks with a fixed seed)
      to cover "whichever buttons are pushed afterwards".
- [ ] Make the sweep cheaper: the two-scan state takes 22 of its 25 minutes
      because it reloads 16 images before every control.
- [ ] Rerun `pytest -m slow` in full; two markers/assertions were edited
      after their last run (`test_real_nx_school.py` minimum window,
      `test_real_bu.py` expected failure for `20260615`).
- [ ] Characterisation tests still missing for: GID patching
      (`pilGIDpatchData`, `imagehjoin`, `imagevjoin`), GISAXS, line/area cuts
      through the GUI, burn tests, g_l2/g_l3 and absorber-ratio fits,
      MCA peak fit / sum / merge, peak-fit dialog, 2D plot tab, Bruker path.
- [ ] Use the NX school GID scans (11–12) and the shipped
      `extracted_data/dppc_*_gid.txt` as a GID reference case.
- [ ] Test the error formula of invariant I4 directly (background-subtracted
      ROI error); it is only read from code so far.
- [ ] Python 2 → 3 audit: list every remaining leftover with a failing or
      expected-failure test (`map` used as a list, integer division,
      `print` tuples, string/bytes in the Bruker header reader, `eval`).
- [ ] Write the scoping document once the feature list is complete:
      target architecture, order of work, what each request needs.

## Waiting on the owner

- [ ] Remaining feature requests and complaints.
- [ ] Is there a newer production version of the reader that reads
      Pilatus 1M data (`#B5` header, `pilatus1m/` folder)? This repository's
      version does not.
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
- [x] Feature requests F1–F9 recorded.
