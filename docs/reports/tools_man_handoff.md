# tools man: handoff to my future self (2026-11-25, late UTC)

> **Update (project manager, 2026-11-27): Reader 2.0 is tagged and released.** The tag is `v2.0.0`, and the
> GitHub release is "Reader 2". The release push below is over; read it as history.
> - **Rules 12 and 13 are paused** (owner, 2026-11-27, "Let's pause those rules again"), and that
>   includes the standing order just below. Do not start a known-truth study or a walkthrough unless the
>   owner asks.
> - P44 is no longer waiting for the tag. It is on the "After 2.0" backlog (`docs/RELEASE_PLAN.md`).
>   It is a rule-12 study, so it waits for the owner to resume rule 12 or ask for it.
> - The clean-PC test is still not done and no longer blocks anything. Never run it in Windows Sandbox
>   on the owner's PC.

**Communication (owner, 2026-11-24): GitHub issue #55 only.** Do not message other sessions directly. Post
one comment per message, starting `tools man → <recipient>:`. Follow the issue's rules (public repo: no
names, file names, scan numbers, dates or raw data). Issue comments do not wake this session, so read #55
at the start of every turn.

**Standing order (owner, 2026-11-25; AGENTS.md rule 13):** every study, report or answer shows the whole
chain:
- the raw data;
- each processing step on an example;
- at least one fit with its residuals;
- every statistic explained ELI5;
- the judgment, with its confidence.

The model is `docs/studies/reciprocity/walkthrough.md`; the method is `.claude/skills/known-truth-study`.
Also read `.claude/skills/fit-statistics-pitfalls` and `.claude/skills/tools-freshness`.

## Release push (2026-11-26): my jobs, owner's choice "release jobs first"

- ~~**P44 is parked until 2.0 is tagged**~~ (2.0 is tagged; see the update at the top) (`docs/RELEASE_PLAN.md`; the owner chose this over starting it now).
  Its answers are recorded: the shoulder is free per frame, with both fits reported; strips are often not
  re-aligned in height; NX is pure water. `xraylib` was installed in the 2026-11-26 session only.
- **Blocker 4: the builds pass** (#118). The workflow ran on main twice (latest run 45753156275).
  - Windows and macOS self-tests passed.
  - The run's page has the Windows and macOS zips and `LSS_Reader-sample-data`.
  - **Waiting:** a person runs the clean-PC test (`docs/PACKAGING.md`), and reports on #55.
- **Item 9: the quick-start guide** is done (`docs/manual/quick_start.md`), and Help → Documentation opens
  it.
- **Waiting on main man:**
  - the two Windows `test_toolbox_gui` failures' `E` lines. I guess the pixel test: fonts;
  - About still says "Version: 1.1".

## State

Merged in main:
- #80: tools freshness (the verified record);
- #84: F76 on C54's real series, the likelihood fix under ρ, the Qoff note.

Done for the standing order, on the branch (2026-11-25):
- the F76 walkthrough (`docs/studies/reciprocity/walkthrough.md`, W1–W6);
- the Qoff walkthrough (`docs/studies/qoff/walkthrough.md`, QW1–QW5);
- an ELI5 of how the Tools audit decides (`docs/reports/tools_audit.md`);
- rule 13;
- the three skills;
- the questions and insights, on #55.

**The Qoff walkthrough found two things:**
- **The edge fit's χ²/dof on NX is 75** (the rounded edge), so the proposal's ± is about ×9 too small. This
  is in TODO: scale σ by √(χ²/dof), or fit R_F convolved with the measured resolution.
- **Resolution is between a quarter and nine tenths of NX's offset** on NX's own grid, about half at the
  median. Earlier today I quoted a linear −1.0 to −1.9 × 10⁻⁴; that is corrected in the summary and
  physics_notes.

**Next:**
- P44, presented as a walkthrough from the start;
- then the proposer's σ (TODO), with a study first (rule 12).

## Unanswered questions (posted for questor on #55, 2026-11-25)

1. **The foil prior as the default for patching?** The owner decides. There is real-data evidence now
   (ref_patch_real §6, C56): the prior moves a factor by more than 1σ at 2.4 % of joins, and the last
   level's uncertainty falls from 1.96 % to 1.72 %.
2. **Pin contourpy, kiwisolver and fontTools in `packaging/requirements-build.txt`?** The owner decides;
   this is main man's MQ-11.
3. **Can a GID burn's broad shoulder change under the beam?** This decides whether P44's shoulder
   amplitude is free or fixed. Never asked before.
4. **Why do strips of one sample differ by about their own rate?** Candidates: film inhomogeneity, the
   specular spot moving in the ROI, the background. Never asked of the owner. The GUI manager's Q7
   (default ρ) quotes 88 %/h only; ρ = 1.13 is the better form.
5. **The NX school subphase: pure water, or a salt or buffer?**
   - Temperature cannot explain NX's remaining Qoff: 20 → 25 °C moves Qc by about 1.3 × 10⁻⁵.
   - About 0.4 M NaCl-equivalent would explain it.
6. **The burn NaN crash on current main:** the traceback, from xr-data-needs. Asked twice; no reply. #73
   may have fixed it (`peakLocate` 0/0).
7. **Left for the user:**
   - `/refg` still exists;
   - xraylib is not installed, so the MCA generator uses the shell Compton model.

## Insights passed on (#55, 2026-11-25)

- **Real strips scatter by about their rate** (ρ 1.13). The burn dialog's default ρ of 0 gives
  overconfident verdicts on real data, and single calls at ρ ≈ 1 are overconfident anyway (95 % coverage
  0.87).
- **One additive τ hid five rise-and-fall series.**
- **Drift rates come from the slope of ln y, not y.**
- **With ρ, fit k by maximum likelihood.**
- **NX 14/15:**
  - β 0.85; time excluded; one spot.
  - Burn 15's drift slows (χ²/dof 2.73, curved residuals), which fits saturation.
- **About half of NX's Qoff is resolution.**
  - A proposal is an angle offset only with R_F convolved with the resolution.
  - Set Qc before Qoff.
- **`--stale` reads `verified.json`.** After regenerating products, run `--audit --record --only …`.
  New Tools items need `controls.md` regenerated.
- **Ties ordered by set iteration** make a tool's output change from run to run.
- **The GID template reads a 30 % broadening as +14 % area and a +0.00066 Å⁻¹ shift** (P44). Verdicts on
  broadening peaks are suspect until P44 is done.

## P44 prototype (scratchpad, not committed)

- **Shape:** the mean of the frames less its chord. Outside ±1.5 FWHM it is fitted by a Gaussian plus a
  line.
- **Split:** S = the Gaussian (the shoulder), P = the shape − Gaussian − line (the peak).
- **Each frame:** A·P(stretched by w, shifted by δ) + B·S + a line.
- **Results:**
  - Gaussian shoulders: |bias| ≤ 0.3 % in every case, against the template's +15 % (broadening), +6 %
    (fade) and +11 % (fade under a shoulder);
  - Lorentzian or asymmetric shoulders: errors 2–4× smaller than the template's;
  - a narrow second component: no estimator copes.
- The code to transplant is in the scratchpad's `p44/burn_split_draft.py` (it may be gone after a restart;
  the design above is enough to rebuild it).
