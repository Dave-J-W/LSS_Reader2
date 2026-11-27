# Hand-off: Qoff and the Qz resolution fitted together at the edge, then extended on real data

For: **tools man** (builds it, after 2.0), then the **local data agent** (`xr-data-needs`, on the owner's
computer), who extends it with the real data tools man does not have. From: the local data agent,
2026-11-26, on the owner's word: "Qoffset also has to be fit, and this could be a useful ability to have
in reader", and "Eventually tools man will push something that I want you to extend with the real data you
have that he doesn't. He should have a handoff about doing that". The owner chose the scope: Qoff **and**
the resolution fitted together, not a fixed resolution or only an honest ±. The timing is after 2.0
(`docs/RELEASE_PLAN.md`, "After 2.0"). DATA_NEEDS row 18 tracks the real-data half.

Read first: `AGENTS.md` (rules 11–13; private data), `docs/studies/qoff/summary.md` (C50: the edge fit,
`propose_qoff`, why Qc and Qoff cannot be fitted together, the −0.15 ΔQ bias) and
`docs/studies/qz_resolution/summary.md` (DATA_NEEDS row 13: the real edge widths and the model used),
then TODO, "The Qoff proposal's ±". The model is hand-off 08's (`08-ref-patch-comparison.md`): tools man
writes the method and a survey tool, the local agent runs the tool on private files and returns the
derived numbers.

## Why

`fresnel.propose_qoff` fits the edge with a sharp R_F, so:
- it reads the beam's resolution as Qoff: C50 found about −0.15 ΔQ, which is −1.3 × 10⁻⁴ Å⁻¹ at the
  beamline's median ΔQ of 8.9 × 10⁻⁴ FWHM. That is about half of NX's proposal;
- its ± is the counting part only. On NX χ²/dof is 75, so the ± is about ×9 too small.

The resolution at the edge is the beam's convergence (37 µrad rms), not the slits, and it varies from run to
run (run medians 6.5–12.6 × 10⁻⁴ FWHM). Fitting the two together turns the proposal into the angle offset
itself, and gives every scan its own resolution as a by-product.

## The method (tools man)

    R(q) = N · [R_F(q + Qoff; Qc, β) ⊗ Gauss(σ_Q)](q) · (1 + a u + b u²),   u = (q − Qc) / Qc

- **Qc and β come from the subphase** (`fresnel.SUBPHASES` or a typed density) and are held fixed. Never
  fit Qc with Qoff: C50 §4 shows they lie on one line.
- **Free parameters:** N, Qoff, σ_Q, and the smooth factor a, b.
- **The model row 13 used** (`docs/studies/qz_resolution/summary.md`, "How it was estimated") is the
  starting point. Its range is 0.6 Qc to 0.030 Å⁻¹, with a soft-L1 loss for the odd spike. On known truth it
  recovered σ_Q within 2 % near the real value, and it cannot tell a width below about 1 × 10⁻⁴ from 0.
- **The ±:**
  - a bootstrap, as `propose_qoff` does;
  - scaled by √(χ²/dof) when that is above 1;
  - and a check that χ²/dof comes near 1 on NX, which is the point of the change.
- **Report** Qoff, σ_Q (also as FWHM and as µrad at the scan's energy), their errors and their correlation,
  χ²/dof, the points used, and flags: σ_Q at its bound, too few points below the edge, ill-conditioned.
- **Rule 12 before the Propose button offers it:**
  - a known-truth study (Qoff, σ_Q, the subphase's β wrong by ×2, fringes near the edge, an outlier at the
    first point above Qc, counts × 0.1);
  - tests;
  - a demonstrator on NX.

  Nothing applies the value by itself (C50's recommendation 4).

**What the local agent needs from you, so it can extend without changing your code:**

1. **The method in `lss_core`** (e.g. beside `propose_qoff` in `lss_core/fresnel.py`), taking arrays
   (qz, r, σ, qc, β, energy). The local agent feeds it scans it has already reduced and cached.
2. **A survey tool in `tests/tools/`** in the shape of `ref_patch_survey.py`:
   - `--spec FILE ...` or `--list sets.csv`;
   - finds the scans that cross the edge (Qz from below 0.8 Qc to above 1.2 Qc);
   - reduces them with `Experiment.reflectivity(..., errors='budget')`;
   - writes one CSV row per scan;
   - `--out` must refuse a path inside the repository that is not under `sample_data/private/`, as 08's tool
     does.
3. **The per-scan CSV columns:** spec key, scan, energy_kev, qc, beta, the points below and above Qc, qoff,
   qoff_err, sigma_q, sigma_q_err, corr, chi2_dof, flags, and today's `propose_qoff` beside it (qoff_sharp,
   its err) so the two can be compared on every scan. Everything else may be added freely.
4. **A function or flag that reruns your known truth at a given (Qoff, σ_Q, counts, Qz step).** The local
   agent then checks the method at the real data's own sampling: steps of 0.001 Å⁻¹, few points below the
   edge.
5. When it is on `main`, a comment on issue #55: `tools man → xr-data-needs: …`, naming the commit.

## The extension on real data (local data agent)

What the local agent will run, and what comes back. Only derived numbers are published, and runs are
labelled anonymously.

| Data | What it answers |
|---|---|
| **The 378 private edge scans of row 13** (17 runs, 10 keV, cached reductions) | σ_Q per scan against row 13's own fit: is the new method the same estimator? Qoff per scan and per run, and how much of today's proposal was resolution |
| **Edge scans of the same run** (one per series, several series per run) | how reproducible the angle offset is from series to series within a beamtime: the spread of Qoff between series. It sets how far one Qoff per run could be trusted, and how much a Qz-scale error shifts R/R_F far above the edge, (1 + δQ/Qz)⁴. It does not reach C63's set-aside between-scan question, since later scans in a series have no edge |
| **The released runs before 2019** (`docs/studies/excess_scatter/released/`; the owner's release covers reflectivity curves, fits and frames, minimal and anonymous) | the same on data anyone may see: an edge fit drawn over a real released edge with its residuals, for the walkthrough (rule 13), and a small CSV that regenerates it |
| **The S1 0.02 mm scans row 13 could not fit** (11 scans, 3 ill-conditioned) | whether fitting Qoff and σ_Q together pins them, or still refuses |
| **Subphases other than water**, where they can be told from the data | how much a wrong β moves σ_Q (row 13: ±15 % for β × 2) and whether Qoff follows |

**Returned as:**
- private per-scan CSVs under `sample_data/private/xr/`;
- a study `docs/studies/qoff_resolution_real/summary.md` with derived numbers per anonymous run;
- figures from the released runs only;
- a `docs/physics_notes.md` entry, DATA_NEEDS row 18 ticked, and a pull request into `main` from a
  `claude/local-data-*` branch (main man reviews and merges).

## Things that will bite

- **Only the first scan of a series crosses the edge.** Later scans have no edge and no Qoff of their own.
- **β is the largest model term.** Salt subphases absorb more than water, so a fixed water β reads their
  edge too narrow.
- **Per-point angle errors widen the fits' scatter:** row 13 found the scans scatter 3.5× their fit errors
  within a run. Quote the scatter between scans, not the fit error, until the new ± is checked against it.
- **Known truth at the real sampling:** row 13's check needed steps of 0.001 Å⁻¹ and enough points below
  the edge. NX's scan 6 has two points below the edge, and its fit collapsed to σ = 0, which was refused.
- **10 keV only** was measured in row 13. At another energy a fixed convergence gives ΔQ ∝ E.
