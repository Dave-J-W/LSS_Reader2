# tools man: handoff to my future self (2026-11-24, afternoon UTC)

**Communication (owner, 2026-11-24, evening): GitHub issue #55 only.** Do not
message other sessions directly. Post one comment per message, starting
`tools man → <recipient>:`. Follow the issue's rules (public repo: no names,
file names, scan numbers, dates or raw data). Issue comments do not wake this
session, so read #55 at the start of every turn.

Everything before 2026-11-24 is merged in main (PRs Dave-J-W/LSS_Reader2#26,
#28, #31, #36, #40). The older notes of this file are in its git history.

## On the branch `claude/gracious-knuth-e7ry2y`, not yet merged

Pushed; one PR into main once the sweep and the slow suite pass.

1. **The Pilatus 100K sizes** (Main, TODO area L, last row), three commits:
   - `08a4bdb` cut ranges from the frames (`cuts.default_range`,
     `images.SHAPE_100K` = (487 rows, 195 columns) as presented);
   - `321c17f` GID last row and columns limit (`GIDParams.for_detector`,
     `gidEffectiveParams` / `gidRowMaxFollows`, `gidScriptSettings`);
   - `d964675` the pixel written once (`images.PIXEL_MM`; the window uses
     `self.pilatus.pix_size`).
   No number changes on the 100K; `tests/test_detector_sizes.py`
   monkeypatches a 1M.
2. **F90 wrap-up** (`60a0dd0`): `docs/reports/mca_fit_demo.md`, the
   beam-energy figure (`tests/tools/mca_fit_demo.py`,
   `docs/figures/mca_fit_demo/`), Tools items and variations,
   `synthetic_dataset.py --kind mca`, SYNTHETIC_DATA marks the generator
   paused. No default changed.
3. **Q-BURN-6**:
   - `bd1938c` lit-column fix (`burn._illuminated`, NX unchanged bit for bit);
   - `4bacc00` the rows from the mean frame (`burn.signal_rows`,
     `exp.burn(rows='mean')`, the dialog's "Rows from frame"; NX 14 and 15
     rows 46–486; C49);
   - `659d6c8` field width and two screenshots.

## Checks

- The quick suite passed before every commit (last: 1076 passed).
- The burn suites, slow ones included, pass.
- The sweep is running at `659d6c8` in a worktree
  (`scratchpad/sweep_wt`, log `sweep_head.log`). An earlier run was cut at
  the 30-minute background limit, so give it a 2-hour limit and keep the
  CPUs free while it runs.
- The slow suite comes next, then the PR (merge commit), then
  `git merge --ff-only origin/main`, then the report to Main.

## Open

- The GUI manager okayed the sizes commits. There has been no reply yet on
  the burn dialog functions (setupBurnTrends, burnOptions*,
  burnArguments, burnTrends). Mention it in the report.
- Two left-overs for the user: `/refg` (rm was blocked earlier), and
  xraylib (the install was denied, so Hartree–Fock Compton tables are not
  used).
