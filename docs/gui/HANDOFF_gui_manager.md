# Handoff: GUI manager session (written 2026-11-23, 21:30 UTC)

Owner: "Main is orchestrator; go ahead and build" (main window first, then
the timeline F83, then ngui). Report to Main (session_017UNj94caCtuQh48DiL9JQC,
send_message) and message it before large `mainwindow.py` edits. Standing
permission: merge my branch into `main` by PR + "Create a merge commit"
once the quick suite (and, for GUI changes, the sweep) pass; then merge
`main` back into the branch.

## State (updated 2026-11-25, 10 am Chicago time)

- **On main:** through #83 (137c09c): F105, F79, F97/F59, the peakLocate
  fix (#73); F92 masks, the closed patch window fix (#77); D1's yellow
  light (#78); F98 in the burn dialog (#83).
- **On the branch, next PR:** the screenshots remade whole and recorded by
  the Tools audit, with gui_screens made reproducible (d82d09c, swept);
  F107 the timeline's dose colouring (0e30404); the merge of main
  (22e7466). The sweep on 0e30404 and the quick suite on 22e7466 were
  running. If both passed: PR, merge commit, fast-forward.
- **Questions for the owner** went to questor on issue #55 (2026-11-25,
  13 numbered: the Q-cut band, Restore all's reach, masks in exports, when
  D1 locks, saving after read-only, the default ρ, the beam width default,
  OQ-4, the series id in names, F107's own-burn rule, one spot, sh scans).
  Watch #55 for "questor → GUI manager" and apply the answers.
- **Evidence since:** tools man's real-data ρ = 1.13 (0.88–1.50) for the
  strip scatter (issue #55, #84). Rule 12 holds the default at 0 until a
  decision. When tools man's `strip_scatter_fit` lands, the Dose or time
  tab can offer "from repeats".
- **The screenshot tool:** keeps the Messages clock at 12:00:00, holds the
  frame movie on its frame, stops the text cursor blinking, waits for the
  GISAXS view's timers, and keeps the committed Observations. After a
  change to the window, remake with `python tests/tools/gui_screens.py`
  and record with `python -m lss_toolbox --audit --record --only
  gui_screens` (and dump_tooltips, gui_map, ngui_inventory after a
  mainwindow.py change).
- **Work in:** the main checkout, branch `claude/funny-noether-09opxa`.
  The crash sweep runs in the worktree `scratchpad/wt_sweep` (re-created
  after a restart with `git worktree add --detach`).
- **Messages:** GitHub issue #55 only. Wake-up timers don't survive a
  session restart (scheduled tasks are off for the organisation).

## Next, in order (main man's of 2026-11-25)

1. Merge the branch (above).
2. The timeline's reduced-data and environment lanes.
3. F95 B9/B10; B3 (needs rule 12); the owner's answers from questor.

## APIs received for the next items (2026-11-24)

- **F79 (tools man, #56, `lss_core/fresnel.py`):**
  - `p = fresnel.propose_qoff(q, r, sigma, qc=...)` gives:
    - `p.ok`;
    - `p.qoff`, in refQoffLineEdit's convention (R/R_F divides by R_F(Qz + Qoff));
    - `p.sigma`, a bootstrap standard error;
    - `p.note`, one line for the Messages pane;
    - `p.outliers`, the Qz of the points it down-weighted.
  - About 0.5 s (`bootstrap=50` is faster). `method='smooth'` gives the owner's by-eye criterion as a second opinion.
  - `fresnel.SUBPHASES` holds `.name`, `.qc`, `.rho_e` and `.source`; the densities are "from memory". Also `fresnel.subphase(name)` and `fresnel.qc_from_density(rho_e)`.
  - **Study findings:** set Qc before Qoff; never fit Qc from the curve (it is degenerate with Qoff). NX 6–9 proposes −0.00028 Å⁻¹. Never apply a value by itself (rule 12). The calls are shown in `tests/test_qoff.py`.
  - **Planned:** a Qc menu of the subphases plus a typed density; Qoff proposed, then filled only when accepted, with the note and ±σ in Messages and the 'smooth' answer in the tooltip.
- **F97 diffuse axes (main man, #59, `lss_core.cuts`):**
  - `frame_cut` and `exp.cut` take `axes` from `cuts.DIFFUSE_AXES`: 'beta', 'beta-alpha' and 'Qz' for vertical cuts (Q V, Pix V); 'Qxy' for horizontal ones. The intensities are unchanged (I41).
  - `cuts.AXIS_FITS[axis]` gives the directions an axis fits; `cuts.axis_label(direction, axes)` gives its label.
  - **F59:** `cuts.covered_range(direction, geometry, shape)` and `cuts.centred_range(direction, geometry, half_px)`; `self.cutGeometry(j)` gives the geometry. Q cuts' defaults lie off a reflectivity frame, so they sum zeros silently (measured).
  - **Planned:** a cut-axis choice beside Line/Area Cuts, separate from pilAxesComboBox.
- **F92 masks (#54) and F98 dose (#52):** see main man's messages of 2026-11-24. In short:
  - `masks.load/save(wb)` and `Mask.add/restore_all/pairs`;
  - `exp.reflectivity(..., mask=)`;
  - `reflectivity.drop_points` returns `(removed, origins)`;
  - `exp.dose(scan, unit=, beam_mm=)` and `exp.burn(n, axis='dose')`.
- **Talking to main man and tools man: GitHub issue #55 only** (owner, 2026-11-24, after `send_message` from this session was refused as an untrusted device).
  - **Post:** one comment per message, starting `GUI manager → main man:` (or `→ tools man:`) and ending with the "Generated by Claude Code" footer: `gh api repos/Dave-J-W/LSS_Reader2/issues/55/comments -F body=@file`.
  - **Read:** `gh api "repos/Dave-J-W/LSS_Reader2/issues/55/comments?per_page=100"`.
  - **The issue's rules (public repository):** no PI or group names, macro or do-file names, file names, scan numbers or dates; derived numbers only.
  - Their `send_message` to this session still arrives.

## Lessons

- After `git rm`, stage with `git add -A`, not a path list: a missing path aborts the whole add.
- A new control needs:
  - an inventory entry;
  - a place in `ngui/layout.py` (check that it is not already placed);
  - `python tests/tools/ngui_inventory.py`;
  - `dump_tooltips` regenerated.
- New preference keys go into `tests/test_gui_preferences.py`'s expected dict.
- Run the sweep in a separate worktree so that editing doesn't change files under it.
- ngui: every inventory id must be placed or retired, removed: entries included; a placed id needs a widget named ngui_<id> whose tooltip has "Was:"/"Does:", and an enabled widget must be a plot, label or tab widget. Keep the default window at 1440 × 900 (test_ngui).
- Regenerate screenshots into a scratch folder, then copy only the ones the change makes stale.
- New controls change the sweep's random walks, which then reach old defects: fix them in their own commit with a test (e.g. fitCuts after ax.clear, 2026-11-24).
- matplotlib 3.11: removing an artist after ax.clear() raises NotImplementedError; check artist.axes first.
- Timer-driven GUI tests race on a loaded machine; disconnect the timer's slot and step by hand.
