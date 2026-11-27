# Stopgap: patching GID levels that share no overlap (unscaled seams)

Local data agent, 2026-11-26, at the owner's request: "Please propose a stopgap solution for patching image
that don't share any overlap, even if there are tradeoffs. Just spell out the tradeoffs and build it."

## What it does

A pinhole GID patch joins its Qz levels by fitting one factor per level where its rows overlap the level
below in β (`pinhole.join_levels`). When a level's rows share **no** β with the levels below, there is
nothing to fit the factor on, and the patch stops ("does not overlap in beta with the levels below it").

The stopgap is opt-in: the worksheet check box **"Join levels without overlap (unscaled)"**, or
`GIDParams(unmatched_levels='unscaled')` in a script. With it, such a level is added **as collected**:
- each frame normalised by its own monitor and absorber, as in every pinhole patch;
- the level's own column response, as chosen;
- **no join factor** (1, with no error).

The seam is marked in four places:
- the joins table: kind "vertical (beta), unscaled", label "… UNSCALED, no overlap", the intensity ratio across it;
- a message after the patch;
- a `#` line at the top of every file Save GID writes (`gid.seam_note`);
- `GIDResult.unscaled_seams` and the join info's `unscaled_seams` in scripts.

The default is unchanged: off, the patch refuses as before, and its message now names the check box.
Levels that do overlap are joined exactly as before with the option on (tested bit for bit), and files
without an unscaled seam are written byte for byte as before.

This is the simplest honest option. Placing each frame by its own motor geometry is what the pinhole patch
already does: every pixel sits at its exact (2θ, β). The only thing missing across a gap is the relative
scale. The stopgap leaves that scale as measured instead of inventing one, and says so.

## Tradeoffs

1. **The relative scale across the seam is not checked.** A monitor, absorber or illumination difference
   between the levels shows as a step at the seam, and nothing in the map tells it from real structure.
   - **Known truth, synthetic:** the upper level's monitor reads 25 % high, so its efficiency is 0.8. The
     stopgap puts that level at exactly 0.800 × the truth and the lower one at 1.000. The step passes
     1 : 1 into the map. This is the test `test_a_wrong_monitor_shows_as_a_step_and_is_not_hidden`.
2. **Monitor and absorber errors pass straight through.**
   - **Monitor:** where the monitor is the only difference, the step is its error. This beamline's monitor
     noise is far below 1 % per point, so for one level that error is small.
   - **Absorber:** if the two levels use different absorbers, the absorber model's error goes into the
     step in full. The nominal and calibrated absorber factors differ by up to 13 % at three foils
     (COMPARISONS C6).
3. **The column response sets part of the scale.** With the default response `fit` (and with `beam`),
   each level's response is normalised within that level. So an unscaled level's scale also carries that
   normalisation.
   - **Measured on the 15 real seams:** the intensity ratio across the seam under `fit` differs from
     the one under `none` by a median 7 %, and by up to 28 %.
   - **With `none`** the scale is "as collected" (monitor and absorber only), but the map keeps the
     column structure that a response removes: frames agree 5× worse (`docs/studies/gid_method_survey/`).
   - Neither choice is free. Comparing the two is a quick check of how much of a step is response.
4. **The ratio across the seam is a diagnostic, not a correction.** It is the 2θ-averaged intensity of the
   three β bins on each side, upper over lower. It cannot separate a scale error from a real change of
   the intensity across the gap, and on these sets the gap is 0.5–6.1° wide. GID rods usually fall with β,
   so a ratio below 1 is expected.
   - **On the 15 real seams:** 0.69–1.10, median 0.90, under `fit`; 0.70–1.00, median 0.82, under `none`.
   - **Known truth:** the ratio equals the truth's own change across the gap (1.124) when the monitors are
     right, and 0.8 × that with the wrong monitor.
5. **The errors are counting only.** No uncertainty for the unknown scale is added, because there is
   nothing to estimate it from. A fit across the seam therefore over-trusts the relative scale.
6. **A geometry error at one level cannot be seen.** Without overlap, an error in one level's arm angle (its
   β) or its distance shifts or stretches that level, and no shared feature shows it. 2θ is less affected:
   both levels use the same 2θ bins, and a distance error moves both alike.
7. **The map has no rows in the gap.** The β (or Qz) axis jumps from one level to the next; a plot may
   stretch the edge rows across the gap. Read a seam in Angles, and look at both sides separately.

## On the private data

The survey of 194 sets (`docs/studies/gid_method_survey/`) listed 18 that no pinhole method could join.
Run again with the stopgap (all three responses; the private generator is
`sample_data/private/gid/scripts/stopgap_real.py`; `seams.csv` here):

| Outcome | Sets |
|---|---|
| A real β gap, now joined with one unscaled seam | 15 (5 beamtimes); gaps 0.47–6.10°, median 3.8° |
| No β gap after all: its upper level's 2θ bins shared no β range, so it kept no β rows and the join stopped on a zero-size array. Fixed 2026-11-27 (the level keeps the window with the most cells; 10 of its 270 bins dropped): it now overlaps and joins with a fitted factor, by default | 1 |
| No β gap: they had failed only with the `physical` responses at one distance, and join with fitted factors under `fit`, `beam` and `none` | 2 |

So 15 of the 18 have a real gap, not 18 as the survey summary said, and all 15 patch with the stopgap; the other 3 patch by default (corrected 2026-11-27: this said 16 and 15 of 16; `sample_data/private/gid/scripts/join_recheck.py`).

## Files

| File | What |
|---|---|
| `seams.csv` | per set: outcome, seams, the β gap, the ratio across the seam under `fit`, `beam` and `none`, and fit ÷ none |
