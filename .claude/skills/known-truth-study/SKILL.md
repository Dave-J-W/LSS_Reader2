---
name: known-truth-study
description: Design, run and present a study of an estimator or test in LSS_Reader2 the way the owner requires - synthetic data with a known truth, replicates, calls/bias/pulls/coverage, the public NX check, real-data comparison from derived tables, and a walkthrough that shows the whole data chain with fit examples and ELI5 statistics (AGENTS.md rules 11, 12, 13). Use whenever a new method, a default change, or a verdict on data is being built or reported (burn trends, patching, Qoff, MCA fits, GID methods, dose or time).
---

# A known-truth study, presented end to end

Distilled from tools man's F76 (dose or time), F79 (Qoff), F90 (MCA) and the P44 prototype, 2026-11-24/25.

## 1. Before writing code

- **Say what "right" means** for each truth. For F76: dose → "dose", time → "time", β 0.5 → "neither",
  no change → "no change". Every later number is a share of right calls, so fix this first.
- **Write the generator with the truth stated frame by frame.** Put it in `tests/synthetic/` (see
  `docs/SYNTHETIC_DATA.md`), seeded and deterministic. Examples: `burn_pairs.series`,
  `burn_profiles.profiles`, `xrr_scans`.
- **Prototype in the scratchpad first.** Compare against the current default on 5 seeds per case. A
  prototype that wins only on the generator's own assumptions is not finished.
  - The split template beat the template on Gaussian shoulders because the model was a Gaussian. Its
    advantage shrank on Lorentzian, asymmetric and two-component shoulders. Always add cases that break
    the model's assumptions.

## 2. The study tool (`tests/tools/<topic>_study.py`)

- **Designs × conditions × truths × replicates**, 300 replicates per cell by default, in parallel where
  slow. For each cell report:
  - the share of each verdict, and the share right;
  - the bias and SD of the estimate;
  - the **pull SD** ((estimate − truth)/σ; 1 means honest errors);
  - the **coverage** of the 68 % and 95 % intervals.
- **Add a public real-data check** (NX school) and, where the non-cloud agent has published derived tables
  (`docs/studies/xr_*`), a comparison on them. Read derived tables only: never raw private files, never
  frame-by-frame curves of private burns.
- **Write the outputs:**
  - `results.csv` (one row per cell);
  - `numbers.json` (everything the text quotes);
  - figures named by section (R1, R2, …).
- **Tests:** a tiny run of the tool (3 replicates) in `tests/test_<topic>_study.py`, plus pins of the
  quoted real-data numbers.

## 3. The records (rule 11), in the same tranche

- a COMPARISONS row (old vs new, data, result, evidence, how to regenerate);
- OUTPUT_DECISIONS only if an output number changes, with before → after;
- physics_notes, dated, with "Verified by: run / test / reading";
- DATA_NEEDS when the conclusion is "real data must settle it", saying exactly what data;
- a catalogue item with its variations (`path#heading` anchors), then `python -m lss_toolbox --render`;
- `controls.md` (`dump_tooltips`), since a new Tools item is a new menu action.

## 4. The walkthrough (rule 13, the owner's standing order)

`docs/studies/<topic>/walkthrough.md` and a tool `tests/tools/<topic>_walkthrough.py` that makes every
figure. Follow `docs/studies/reciprocity/walkthrough.md`. In order:

1. **The question in one paragraph,** in everyday words: what would we see if A, what if B.
2. **The raw data:** a frame or scan as it comes in, with what each axis and colour means, and where the
   error bars come from (√counts for counting).
3. **Each processing step on one public example,** with its plot: rows summed → line cut → window → one
   number per frame.
4. **At least one fit over its data, with residuals in units of σ.** Read the residuals aloud: random, or
   a pattern (NX burn 15's drift slowed: χ²/dof 2.73, a smile-shaped residual)?
5. **Every statistic, explained once, as a table row "value | in words":** χ² and χ²/dof, the
   Δχ² = 1 / 3.84 intervals, p-values ("how often noise alone would do this"), Akaike weights,
   likelihood and REML, likelihood ratios, pulls, coverage.
6. **Calibration on synthetic data:** draw 60 intervals as bars against the truth and count the hits
   (W6). A promise of 68 % must be checked, not assumed.
7. **The judgment, with a confidence in plain words** ("high that…, low on…"), and what would settle it.

Check every number in the text against `numbers.json` before committing. In the F76 walkthrough, six
sentences written from memory were off: "about 2σ" was 2.8σ, "once in 4" was once in 5, and so on.

## 5. Changing a default (rule 12)

Only after the study, the tests and the walkthrough. Then make the switch in its own commit, with the
OUTPUT_DECISIONS row and every re-pinned test named.
