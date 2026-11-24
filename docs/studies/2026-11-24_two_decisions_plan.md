# Plan: full studies of two decisions, with figures and an ELI5 rationale

Owner, 2026-11-24, after answering questor's batch 15:

> "I want a full study (is real data needed? Better synthetic? Show some
> synthetic data replicates and their fits! Show me stats in graphical
> form!) illustrations, and a ELI5 rationale document with latex equations
> for those two decisions. But this will have to wait until 1am."

The two decisions:

- **A. How a reflectivity join is fitted, and how strict its guard is.** The
  joint-fit guard keeps p ≥ 0.3. Tools man found two things, C45 and
  physics_notes "Why five gauntlet joins are biased":
  - five gauntlet joins are biased by the curve model itself, not by
    noise;
  - the guard's choice of rung (post-selection) widens the first join's
    pulls to SD 1.13.

  At p = 0.01 the first join is cured, but the biased joins get worse.
  The owner has said the guard "needs further study".
- **B. How an MCA line intensity is measured (F90).** Tools man's synthetic
  study (C42) found:
  - the window sum fails once scatter sits under the box;
  - the reader's fit holds only on a smooth background;
  - P1 (the Poisson per-spectrum step) fixes low counts;
  - P2 (width fixed from the detector's resolution) with P3 (Si escape
    stripping) is the best combination, but passes only 38 % of the
    random conditions.

  The owner adopted P1 as the default, P2 and P3 as options, and P4 (box
  ±2 FWHM) waits.

Start: **1:00 am, America/Chicago (07:00 UTC, 2026-11-24)**, by a reminder
scheduled into the Main session. The time zone is an assumption (the
beamline is at the APS, Illinois); the owner can say otherwise. Until
then nothing of this runs. Tools man builds P1, P2 and P3 as code paths
but leaves the **current** "Fit lines" weighting as the default until the
study is in, since the owner wants the study before the decisions stand.

## What each study must answer

For each decision, the same five questions, answered in this order:

1. **What does each choice do on data whose truth we know?** Bias,
   spread, the pulls' mean and SD, coverage of the 68 % and 95 %
   intervals, and the rate of failures and flags. Synthetic, with
   replicates.
2. **Is the synthetic data good enough?** The generator is improved
   where an assumption could change the answer (the lists below), and
   the generator assumptions are swept over their plausible range: a
   **robustness map** says which conclusions hold over the whole range.
3. **Is real data needed?**
   - Not needed, if the conclusion holds over the whole plausible range
     of everything synthetic cannot know. Real data then only confirms.
   - Needed, if it does not hold. The study then names the measurement:
     which data, how many, what it settles (`DATA_NEEDS.md`). It also
     says what can be checked now on the public NX school data.
4. **What does it cost to be wrong?** The size of the effect on what the
   owner reports: film thickness and roughness from a downstream fit for
   A; the XFNTR curve's shape for B.
5. **The recommendation**, and what would change it.

## Study A: reflectivity joins and the guard

**Data and synthetic generator** (`tests/tools/ref_patch_gauntlet.py`, its
designs; `tests/synthetic/`):

- **Already there:** NX-like scans, layered films, staggered grids, the
  owner's monitor model (0.04 %, D22), the gauntlet's seeds.
- **Improve before the runs:**
  1. Curves from a physical model. Parratt recursion
     ([Parratt 1954, *Phys. Rev.* 95, 359](https://doi.org/10.1103/PhysRev.95.359))
     with Névot–Croce roughness, for:
     - a monolayer on water (DPPC-like);
     - a thick film with Kiessig fringes (50–300 Å);
     - bare water.
  2. The real sampling plans, all from the NX school file: the Qz grids
     and overlaps of NX scans 6–9, their count times, their absorber
     steps and count levels.
  3. Background subtraction noise from the background boxes.
  4. A slit or footprint change at a join (P29).

  The owner said fringes are rarely under-sampled, so under-sampled
  joins stay out of the design (physics_notes, the F91 entry).

**Choices compared:**
- legacy (the spline ratio);
- joint fit with the guard at p 0.3 (today's default);
- joint fit with the guard at 0.1, 0.03 and 0.01;
- guard off, at a fixed order and window (order 4, 2 points either side);
- option (c): one fit whose error accounts for the choice, a sketch;
- the known foil ratio where an absorber changes.

**Runs:** at least 400 replicates per condition, on the gauntlet's own
seeds where they exist, so that today's numbers come back exactly first.

**Figures** (each made by a catalogued tool, `lss_toolbox/catalog.py`):

- **A1. What the fit sees.** One join, the true curve, 6 replicates and
  each replicate's fit in ln(R/R_F), with the overlap shaded and the
  chosen order written on each. One panel per join type: smooth, fringe,
  staggered.
- **A2. Pulls.** A histogram of (f̂ − f)/σ̂ per choice, with N(0, 1) drawn
  over it and its QQ plot. One row per join type.
- **A3. Model bias.** The noise-free error per join and choice as a dot
  plot, against ±1 error bands.
- **A4. What the guard chooses.** Stacked bars of the rung shares per
  join, coloured by the mean pull of each rung. This is the
  post-selection picture.
- **A5. The decision curve.** Sweep the guard's p from 0.001 to 0.5 and
  plot the first join's pull SD against the mean |bias| of the biased
  joins, one point per p. The owner's choice is a point on this curve.
- **A6. Coverage.** Bars of the share of |pull| < 1 and < 2 per choice,
  against 68 % and 95 %.
- **A7. What it means physically.** Thickness and roughness from a
  downstream fit of the patched curves (the C35 machinery), as
  distributions per choice.
- **A8. Real data now.** On NX 6–9, every join's factor under each choice,
  beside the calibrated foil ratio with its error. The foil ratio is an
  independent estimate of the true factor where an absorber changes.

**Real data:**
- The public NX set gives four joins and A8.
- The decisive set is many joins with known foil ratios. That is the
  owner's series for hand-off 08 (`DATA_NEEDS.md` row 1, "not soon").
- The study states whether it is needed for the guard decision, using
  the robustness map over fringe sampling and count levels.

**Owner of the work:** Main, with one subagent for the figure tools (in a
worktree, merged by Main).

## Study B: MCA line intensities (F90)

**Data and synthetic generator** (`tests/synthetic/mca.py`, C42):

- **Already there:** the photopeak, Kα/Kβ, elastic, valence Compton, the
  O 1s Compton wing, Si escape, shelf and tail, background, XFNTR series.
- **Improve before the runs** (each is an assumption that changed an
  answer in C42):
  1. The **Compton profile** from tabulated Hartree–Fock profiles
     ([Biggs, Mendelsohn & Mann 1975, *At. Data Nucl. Data Tables* 16,
     201](https://doi.org/10.1016/0092-640X(75)90030-3)) instead of the
     hydrogenic O 1s approximation, and the impulse approximation's
     binding cut-off stated.
  2. The **escape fraction** from a physical model of the Si escape
     (Reed & Ware 1972, *J. Phys. E* 5, 582; DOI to be checked),
     instead of the figure from memory.
  3. **Detector response** (tail, shelf, Fano) over the range of typical
     silicon drift detectors, as a swept range, to be fitted to a blank
     when one arrives.
  4. **Count levels** of the owner's XFNTR series: derived numbers only,
     from the owner's non-cloud agent if available.

**Choices compared:**
- the window sum, and window − sides;
- the reader's fit as it is (data-weighted);
- P1 (Poisson step);
- P1 + P2 (fixed width);
- P1 + P3 (escape stripping);
- P1 + P2 + P3;
- the box at ±2 and ±3 FWHM (P4).

**Runs:** C42's design rerun on the improved generator, with at least
200 replicates per designed condition and 150 random conditions × 40.
Then the robustness sweep over the escape fraction, the O 1s wing,
Doppler width and counts.

**Figures:**

- **B1. Anatomy.** One spectrum, its parts stacked on a log scale
  (photopeak, Kβ, elastic, Compton valence and core, escapes, shelf and
  tail, background), with the ±2 and ±3 FWHM boxes.
- **B2. Replicates and their fits.** Six replicates at 90, 270 and 1000
  line counts, each with every estimator's fit drawn in, and residuals
  underneath.
- **B3. Why weighting matters.** Bias against counts for the
  data-weighted fit and for P1, with the expected curve drawn over the
  points (the derivation in the ELI5 document).
- **B4. One feature at a time.** A dot plot of bias ± its error per
  estimator, for each feature alone: escape, wing, Doppler, tail, gain,
  calibration.
- **B5. XFNTR series.** The ratio to truth against Qz per estimator, for
  the smooth and the hard series.
- **B6. Pass rates.** Over the random conditions, a heat map: estimator ×
  condition class, coloured by the share within 1 %.
- **B7. Robustness map.** For each conclusion (P1 better than legacy; P2+P3
  best; the window fails), the region of escape fraction × wing size
  where it holds.

**Real data:**
- The blank spectrum beside the sample's (pure water or the subphase, at
  the same Qz) measures the escape fraction and the wing directly.
  That is `DATA_NEEDS.md` row 3, promised by the owner along with
  nearby-element spectra.
- The study says which conclusions need it, using B7. P1's is expected
  not to need it: its effect is at low counts, whatever the background.

**Owner of the work:** tools man (the generator and the gauntlet are
theirs).

## The ELI5 rationale document

`docs/studies/eli5_two_decisions.md`. GitHub renders its LaTeX. A
standalone `.html` copy with MathML is made by `pandoc --mathml`, since
no LaTeX engine is installed here; it opens in any browser without a
network.

For each decision:
1. **The question, in one sentence**, and a picture: A1 or B2.
2. **The idea, for a non-specialist**, in one paragraph with an everyday
   analogy.
3. **The maths, short.**
   - B, Poisson versus data-weighted fitting: the likelihood
     $\ln L = \sum_i \left[n_i \ln \mu_i(\mathbf a) - \mu_i(\mathbf a)\right]$.
     Its stationarity condition is
     $\sum_i (n_i/\mu_i - 1)\,\partial\mu_i/\partial a_k = 0$.
     Neyman's $\chi^2 = \sum_i (n_i - \mu_i)^2/n_i$ biases low counts
     downward ([Cash 1979, *ApJ* 228, 939](https://doi.org/10.1086/156922);
     [Baker & Cousins 1984, *NIM* 221, 437](https://doi.org/10.1016/0167-5087(84)90016-4)).
     The window sum's expectation is
     $E[\hat A_{\rm win}] = A\,f_{\rm box} + B_{\rm box}$.
   - A, the joint fit: the model is
     $\ln\!\left(R/R_F\right) = \sum_{k \le m} c_k Q^k$, the second scan is
     scaled by $f$, and the guard accepts an order when
     $p = 1 - F_{\chi^2_\nu}(\chi^2) \ge p_0$. Choosing among models by
     the same data makes the reported $\sigma_f$ too small, which is
     post-selection
     ([Berk et al. 2013, *Ann. Stat.* 41, 802](https://doi.org/10.1214/12-AOS1077)).
     The trade-off is A5.
4. **What we decided and why, what it costs if we are wrong, and what
   would change it**, including the real data needed.
5. **References.** Each is checked for the claim it supports (the
   citation-verification skill) before the document is handed over. The
   DOIs in this plan were written from memory and are checked then too.

## Order of work from 1:00 am

1. **Main: dispatch.**
   - Tools man takes study B.
   - Main starts study A, with one subagent building the A-figure tools
     in a worktree.
   - Every figure tool is a catalogue item (AGENTS.md rule 11). Every
     result is a COMPARISONS row with CSV for public data.
2. **The studies.** About 2–3 hours of runs and figures in parallel. The
   outputs go to `docs/studies/reflectivity_guard/` and
   `docs/studies/mca_fit/`, each with a `summary.md` that answers the
   five questions.
3. **Main: the ELI5 document** from the two summaries, with the citations
   checked, and the `.html` copy.
4. **Hand-over.**
   - Main writes the owner a short message: what was found, the figures
     to look at first, and what needs the owner's decision.
   - questor records the owner's decisions.
   - The decisions of batch 15 stand until then; the P1 default switch
     waits.

## Done means

- [ ] `docs/studies/reflectivity_guard/summary.md`: A1–A8, the robustness
      map, and the five answers.
- [ ] `docs/studies/mca_fit/summary.md`: B1–B7, the improved generator
      documented in `docs/SYNTHETIC_DATA.md`, and the five answers.
- [ ] `docs/studies/eli5_two_decisions.md` and its `.html` copy, with
      every citation checked.
- [ ] COMPARISONS rows; catalogue items with their variations;
      `TOOLS.md` re-rendered.
- [ ] `DATA_NEEDS.md` updated with exactly what real data would settle,
      if any.
- [ ] Quick suite, slow suite and sweep on the merged tree; merged to
      main.
