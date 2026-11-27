# P44: a GID burn peak on a shoulder, read with the shoulder split off

- **Date, who:** 2026-11-27, tools man. The owner asked for it ("go ahead with P44"), and the owner's answer
  in batch 26 (2026-11-25, `docs/physics_notes.md`) set the design: "the shoulder is not known to be steady;
  keep it free per frame and compare against fixing it".
- **Answer:**
  - **P44 is real.** The template stretches the broad shoulder with the peak. On a Gaussian shoulder at high
    counts it reads:
    - a −20 % fade as −13.6 %;
    - a +30 % broadening at constant area as +14.4 %, "changing" every time;
    - an NX 15-like burn (FWHM +20 %, −13 %) as −0.2 %, "stable" every time.
  - **The split estimators read every case to 0.13 pp on a Gaussian shoulder.** These are `split` (B free
    per frame) and `split_fixed` (B = 1), via `burn.measure_gid(..., estimator=…)`. On a Lorentzian, lopsided
    or two-hump shoulder they are 1.4–6.2 × less biased.
  - **`split_fixed` is wrong when the shoulder changes.** So the free and fixed splits disagreeing is the
    sign of a changing shoulder.
  - **NX burn 15:**
    - template −1.5 % ± 1.5 % "stable";
    - split −13.3 % ± 2.4 % "changing";
    - split_fixed −15.2 % ± 1.3 % "changing";
    - the shoulder steady (−2.8 % ± 2.8 %, B 0.96–1.15).
  - **NX burn 14** is steady under all three. For these two burns, "keep it free and compare" gives the same
    answer either way.
  - **At NX counts the mean frame's noise biases every fitted estimator** when the width changes:
    - the split by −2.0 pp at NX 15's counts and −6.1 pp at NX 14's;
    - a smoothed mean frame fixes this on synthetic burns, but moves NX's reads the other way (open).
- **A correction:** I first called monitor 1e7 "NX-like". It is not: at 1e7 one frame's intensity is known to
  0.19 %, against NX's 3.8 % (burn 14) and 2.0 % (burn 15). The matching monitors are 1e4 and 6e4
  (`NX_MONITORS`), and part B and the walkthrough's step 6 now run at them.
- **How it is known:**
  - run: `tests/tools/burn_shoulder_study.py` (300 synthetic burns per cell; part R, 100);
  - tests: `tests/test_burn_split.py`, `tests/test_burn_shoulder_study.py` (the NX numbers, slow);
  - study: `docs/studies/burn_shoulder/summary.md`, C70.
- **Numbers that changed:** none. The template stays the default and the dialog is unchanged (the owner's
  choice; rule 12 paused). See the `OUTPUT_DECISIONS` "Burn test: GID estimator" row.
- **Next:** real burns, `docs/handoff_out/10-gid-burn-shoulder.md` (DATA_NEEDS row 19).
