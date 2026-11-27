# Hand-off 10: GID burn peaks on a shoulder: answer P44's questions on more real data

For: the data sessions on the owner's PC (gid-data-needs holds the private GID data; `lane:local-data`), or any
agent with real GID burn frames. From: tools man, 2026-11-27. The owner (2026-11-27): "a handoff for the next agent to use more
real data to answer these questions". DATA_NEEDS row 19 is this request; the task is issue #155 (claim it
there, rule 15).

**Read first:**
- `AGENTS.md`: the private-data rules. Never commit raw data, frames, images or peak locations. Frame-by-frame
  curves of private burns are not published (owner, 2026-11-25); summary values are.
- `docs/studies/burn_shoulder/summary.md`: the study this extends, with the judgment.
- `docs/studies/burn_shoulder/walkthrough.md`: the whole chain on NX burn 15.

## What is known (synthetic burns and the public NX school burns)

- **P44 is real and large.** The template (the reader's default) stretches the broad shoulder with the
  peak.
  - On synthetic burns it reads a broadening at constant area as a +14 % gain, and a −20 % fade as −14 %.
  - It reads an NX 15-like burn (FWHM +20 %, intensity −13 %) as −0.2 %, and calls it "stable" every time.
- **The split estimators** fit a Gaussian to the shoulder beside the peak and stretch only the rest.
  - `split` (the shoulder's amplitude B free per frame) reads every synthetic case to 0.13 pp when the
    shoulder is a Gaussian, including the shoulder's own change.
  - Its σ is up to 25 % small.
  - On non-Gaussian shoulders it keeps a bias of up to 6 pp (12 pp with a second narrow hump), still
    smaller than the template's.
  - `split_fixed` (B = 1) is as good while the shoulder is steady, and badly wrong when it is not.
- **NX burn 15:**
  - template −1.5 % ± 1.5 % "stable";
  - split −13.3 % ± 2.4 % "changing";
  - split_fixed −15.2 % ± 1.3 % "changing";
  - the FWHM +18 to +21 % under each;
  - the shoulder steady (−2.8 % ± 2.8 %, B 0.96–1.15).
- **NX burn 14:** stable under all three.
- **At low counts the reference's noise biases both estimators** when the peak's width changes (summary,
  sections 4 and 6). On the NX 15-like burn the split reads the fade 2.0 pp too deep at NX 15's counts and
  6.1 pp at NX 14's, and only 75 % and 56 % of its intervals hold the truth (`split_fixed`: 0.8 and
  3.3 pp).
  - The reference is the mean frame every frame is fitted against.
  - A smoothed mean frame removes this bias on synthetic burns.
  - On NX 15 the smoothed mean moves the split's read by −0.3 pp only, not the +1 to +2 pp the synthetic
    burns predict at its noise. So whether the synthetic noise model transfers to real frames is open.

Two public burns cannot say how general any of this is. That is what this hand-off asks.

## The questions

1. **How often does P44 change a real verdict?**
   - For each GID burn: the intensity and FWHM verdicts and changes under the template, the split and
     split_fixed.
   - Count the burns where the template and the split disagree on a verdict, and the size of the
     disagreement in σ.
2. **Do real shoulders change under the beam?** The owner, 2026-11-26: not known. Look at:
   - the split's `shoulder` change and verdict;
   - B per frame (`b_mean`, `b_min`, `b_max`);
   - whether split and split_fixed disagree on the intensity by more than their σ (the sign of a changing
     shoulder in the synthetic study).
3. **Is a Gaussian a good enough shoulder?**
   - Compare the split's per-frame χ²/dof with the template's.
   - Note any burn where the split fits worse, or where the shoulder is not found (`shoulder_found`
     false).
   - Use the shape ratios (`shoulder_to_peak_area`, `shoulder_to_peak_fwhm`) to place each burn against
     the synthetic shoulders.
4. **At what counts are real burns, and does the reference's noise matter?**
   - Get the distribution of `frame_rel_error` (one frame's intensity error) and `mean_frame_noise` (the
     mean frame's noise as a share of its peak).
   - Get `smoothed_change − change` (the intensity re-read against the smoothed mean frame) for the template
     and the split.
   - Compare it with the synthetic shift at the same `mean_frame_noise` (table below), in units of its SD.
5. **Does the split change F76's dose-or-time answer?**
   - Only for series of burns of one sample at several fluxes (`docs/studies/xr_burns/` lists them for
     reflectivity; DATA_NEEDS row 14 for GID).
   - Read their rates under the template and the split, through `lss_core.reciprocity` as F76 does.
   - On NX, the drift-per-dose ratio of burns 15 to 14 moves from 0.79 (template) to 0.82 (split).
6. **What would settle the size?** List any burn with an independent measurement of the same peak before
   and after: a rod scan, or a GID scan of the same spot. Compare that peak's area change with each
   estimator's. One such burn would turn "the split reads −13 %" into a measurement.

## How to run

The tool is `tests/tools/burn_shoulder_study.py`. Its `--real` mode does questions 1 to 4 for every GID
burn of the files given. A burn is an `ascan ih` that does not move, with 2θ above 2°: the reader's own
tests. Write into the private folder:

    python tests/tools/burn_shoulder_study.py --out sample_data/private/burn_shoulder --real FILE1 FILE2 ...
    python tests/tools/burn_shoulder_study.py --out sample_data/private/burn_shoulder --real FILE --scans 23,35

- **`real.csv`:** one row per burn × estimator × quantity.
  - Burns are labelled G01, G02, … in the order found. No file, scan number, Qxy, frame or image is in it.
  - Columns:
    - `frames`, `duration_s`;
    - `frame_rel_error`, `mean_frame_noise`;
    - `estimator`, `quantity` (intensity, centre, fwhm, and the split's shoulder);
    - `change` (relative; the centre in Å⁻¹), `sigma`, `verdict`, `best`;
    - `frame_chi2_dof`, `frames_failed`;
    - for the splits: `shoulder_found`, `shoulder_to_peak_area`, `shoulder_to_peak_fwhm`, `b_mean`,
      `b_min`, `b_max`;
    - on the intensity rows of the template and split: `smoothed_change`, `smoothed_sigma`,
      `smoothed_verdict`.
- **`real_key.csv`: private.** Label → file and scan, and the error of any burn that failed. **It
  never leaves the private folder.**
- **The arithmetic:**
  - `change_of`: the linear trend's slope × the burn's duration over its value at t = 0;
  - σ by the delta method.
  - The verdict is the reader's: errors from the scatter; "changing" when a line beats a constant by
    more than 2 in AICc.
- **Tests on public data:** `tests/test_burn_shoulder_study.py::test_the_real_data_runner_on_nx`. Its
  numbers are NX burns 14 and 15 as G01 and G02.
- **Fails?** A burn that fails is listed in the key with its error and in `real.csv` with `failed` set.
  Fix the cause in its own commit with a test (AGENTS.md); do not drop the burn silently.

**For question 4, the synthetic expectation.** This is the split's and the template's shift
(`smoothed_change − change`, pp) on an NX 15-like burn (FWHM +20 %, intensity −13 %), from
`docs/studies/burn_shoulder/reference_noise.csv` (100 burns per row; the SD is of the shift itself, burn by
burn):

| burn | `mean_frame_noise` | split: shift ± SD | template: shift ± SD |
|---|---|---|---|
| synthetic, monitor 1e7 | 0.03 % | +0.01 ± 0.03 | −0.02 ± 0.04 |
| synthetic, monitor 6e4 | 0.35 % | +1.49 ± 1.00 | +2.12 ± 1.49 |
| synthetic, monitor 1e4 | 0.85 % | +5.02 ± 2.71 | +6.19 ± 3.44 |
| **NX 15** (FWHM +18 to +21 %) | 0.29 % | **−0.27** | **−0.82** |
| **NX 14** (FWHM steady: expect 0, as the `fade` rows: ±0.5 at 6e4, ±1.9 at 1e4) | 0.51 % | **−5.46** | **−3.62** |

Against the nearest synthetic row:
- **NX 15** sits 1.8 SD (split) and 2.0 SD (template) below the expectation.
- **NX 14** sits about 3 SD (split) below a steady peak's expectation.

So on these two burns the smoothing moves real reads the other way from synthetic ones. Two burns cannot
tell whether the synthetic noise model fails, or the smoothing spline itself misbehaves on real mean frames
(it may round a real peak that is sharper or less Gaussian than the synthetic one). Your burns can.
- If real shifts scatter around zero whatever the noise, the reference's noise is not a real-data problem.
- If they grow negative with `mean_frame_noise`, the spline is at fault.
- If they follow the synthetic rows, the noise is real and the smoothing fixes it.

A burn whose FWHM does not change should show no shift at any noise (the `fade` rows of the same file).

## What to publish, and where

- **`real.csv`** goes to `docs/studies/xr_burns/gid_split.csv`, after the privacy review (main man's
  `review-local-data-pr` skill; reflection guy's rulings on public data are the owner's word).
  - Its values are changes, errors, verdicts, fit qualities and shape ratios: summary values, the class
    the owner allows.
  - If the reviewer doubts the shape ratios (they describe a peak's form, not its place), drop those
    columns rather than hold the rest.
- **A section** "## 8. Real GID burns (non-cloud agent)" goes in `docs/studies/burn_shoulder/summary.md`,
  answering questions 1 to 6, each with how it was measured.
  - Counts and medians only.
  - A figure of the changes (template against split, one point per burn) is a summary figure and may be
    published.
  - **No frame-by-frame curve of a private burn** (owner, 2026-11-25). A figure that needs one stays
    under `sample_data/private/figures/`, and the section says how to regenerate it.
- **A pull request** from a `claude/local-data-*` branch; main man reviews and merges it. Report on issue
  #55: `gid-data-needs → tools man, main man:`.

## How to judge (suggested)

- **Question 1:** a disagreement matters when the verdicts differ, or when the changes differ by more
  than 2 × the larger σ.
  - The split's intervals are about 25 % short when the peak broadens (summary, section 3), so widen
    them by that before calling a disagreement significant.
- **Question 2:** a shoulder change is believable when the split calls it changing, B moves the same
  way, and split and split_fixed disagree on the intensity.
  - One of the three alone is not enough. In the synthetic study, a broadening peak moves B when the
    shoulder is not a Gaussian: a +30 % broadening reads as a shoulder fade of 4.6–6.3 pp, against 0.1 on a
    Gaussian shoulder (summary, section 2).
- **Question 3:** if the split's χ²/dof is not below the template's on most burns, the Gaussian shoulder
  is the weak point. The next estimator to try is the shoulder as the mean frame's own wings (no shape
  assumed), or a Lorentzian.
- **Question 4:** the three readings under the table in "How to run".
  - Plot the shift against `mean_frame_noise`, split and template, with the synthetic rows over it.
  - Only if the shifts follow the synthetic rows does the smoothed reference become a candidate option
    (After 2.0, rule 12).

## What is not asked

- No change to the reader's default (the template), or to the burn dialog. Both wait for the owner
  (rule 12, paused: `docs/rules_paused.md`; the rule-12 studies are issue #143).
- No new estimator in `lss_core` before questions 1 to 4 are answered.
