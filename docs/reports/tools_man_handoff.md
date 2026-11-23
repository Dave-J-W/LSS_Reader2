# tools man: handoff to my future self (2026-11-23, about 20:55 UTC)

## Already in main (Dave-J-W/LSS_Reader2#26, merge 6cd3927)

- Item 1: the three failing real-data tests.
- Item 2: the gauntlet's records and its physics_notes Q&A.
- F90, synthetic half: C42, `tests/synthetic/mca.py`, `tests/tools/mca_fit_gauntlet.py`.
- The report went to Main (session_017UNj94caCtuQh48DiL9JQC).

## On the branch, not merged

`tests/tools/ref_patch_biased_joins.py` is catalogued, and
`test_toolbox` passes. Its run is in the scratchpad (`bj/`), not
committed.

## Item 4, measured but not yet recorded

Run: `python tests/tools/ref_patch_biased_joins.py --out DIR`, 400 replicates on the gauntlet's own seeds. The default reproduces the gauntlet's committed pulls exactly: −0.21, −0.31, +0.25, +0.24, −0.33.

**The five biased joins.**
- The cause is the model, not noise. The noise-free bias of the default is:

  | Join | Noise-free bias (median errors) |
  |---|---|
  | layer_dppc j3 | −1.03 |
  | layer_film150 j2 | −0.64 |
  | overlap_3_staggered j3 | +0.27 |
  | overlap_6 j1 | +0.73 |
  | scans_5 j2 | −0.63 |

- The guard's chosen order matters. In layer_dppc j3 the noise-free choice is order 6. Over the replicates, order 7 (43 %) gives a mean pull of +0.39 and order 6 (28 %) gives −1.26.
- The pull depends on which order the ladder picks, so the order rungs disagree in sign. The mean is a mixture of opposite model biases (post-selection over a model that is wrong at every order near a fringe), not a narrowed error.
- Turning the guard off does not cure it: fixed order 4 gives noise-free +0.42 / −0.42 / +0.27 / +0.57 / +0.01, with inflated errors.
- `e1_off` (1 point either side, order 4) is the least biased on overlap_6 (−0.09) and scans_5 (−0.11), but not on dppc or film150 (−0.65, −0.49).
- The log likelihood makes no difference.

**The covariance study's first join (25 Å film, nx_like_plan, 300 seeds).**
- The default's pull SD is 1.13, reproduced; its mean pull is +0.05; the noise-free bias is 0.
- With the guard off, or at p 0.01, the pull SD is 1.05. Fixed order 5 or 6 gives 1.05, 1 point either side gives 1.04.
- So **the p 0.3 ladder causes the 1.13**: choosing the window and order after seeing χ² makes the error about 7 % small. The model is not biased there.

## Next

1. Record item 4: physics_notes entry, update TODO B's row 53, a COMPARISONS note under C36, and commit `bj/` outputs to `docs/comparisons_data/ref_patch_biased_joins/` with a `committed=` line in the catalogue.
2. Quick suite, merge main, PR, merge (D60), report to Main.
3. No default changes. Possible proposal: report the error over the ladder's choices, or apply a post-selection correction.

## Main's reply (21:14 UTC): updates the Next list

1. Extension 4: approved as planned (above).
2. Then **P5 is a defect**. "Fit lines" must report the element's line, not `r.peaks[0]` (`mainwindow.mcaFitLines`). Fix it with its test and an OUTPUT_DECISIONS row.
3. Send **P1–P4 and the guard question** to questor (session_017UNj95VQdNdKBGwLQWYfq2) as one batch, with the numbers. These are the owner's decisions; change no default.
   - Recommend P5 now and P1 on the evidence (90 counts: −21 → +3.6 %; 270 counts: −5.8 → +0.6 %).
   - Say that P2 and P3 wait for the blank spectra (F105).
   - The guard: join 7→8 of NX 6–9 is flagged at p 0.3 and passes at 0.01; the factors agree to 0.1 %.
4. Extensions 6 and 7 stay "parked by Main"; no names needed.
5. The GUI manager holds updatePilPlotData, pilMovieShow, update2dPlots and the pilMin/Max slider handlers. Stay out of those.
