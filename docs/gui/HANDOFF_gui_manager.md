# Handoff: GUI manager session (written 2026-11-23, 21:30 UTC)

Owner: "Main is orchestrator; go ahead and build" (main window first, then
the timeline F83, then ngui). Report to Main (session_017UNj94caCtuQh48DiL9JQC,
send_message) and message it before large `mainwindow.py` edits. Standing
permission: merge my branch into `main` by PR + "Create a merge commit"
once the quick suite (and, for GUI changes, the sweep) pass; then merge
`main` back into the branch.

## State of `claude/funny-noether-09opxa`

- **Merged into main earlier:** ngui (#4), ngui candidates (#21), and others.
- **Tested but not yet merged (07ad9e7; quick suite 871 passed; pushed):**
  - removals: Beamlines menu, `peakfit2`/`peakfitpara`, the Command line row, the Apex tab (its colour map moved to `pilCMapComboBox`);
  - tabs addressed by widget, not by index;
  - Quit and Documentation;
  - D59 (panes in `paneHost`, under the tabs);
  - F85 badges;
  - two sweep-found crash fixes (Drop past the last join; one-scan Export);
  - the F86 answer recorded.
- **The sweep on 07ad9e7** is running in the worktree `scratchpad/wt_sweep`, output in `scratchpad/sweep2.out`. The first sweep found 2 new random-walk sites, now fixed; check that this one passes.
- **Committed after 07ad9e7, local only (not pushed yet):**
  - a906e99, F86: the Reduction options page (quick suite 876 passed);
  - 6840e1f, Q-GID-5 GID Patch and Worksheet buttons (map and ngui tests pass; full quick suite still to rerun).
- **Subagent (worktree) building F88 sticky display and F69 movie:** it reports back with a branch to merge. Review it, merge into my branch, run quick suite and sweep, then PR.

## Next, in order

1. If sweep2 passed, push, then PR-merge 07ad9e7 or the branch head, whichever was swept. Rerun the quick suite and the sweep for a906e99 and 6840e1f first.
2. Merge the subagent's F88/F69 branch: review, quick suite, sweep, PR.
3. Greyed-out tool groups (Q-UI-A10: grey out with a tooltip saying what is needed, by series kind; enable everything when the kind is unknown).
4. F95, F96, display side of F97, F74 weighted residuals. Message Main before editing Ref Patch functions (F96).
5. Then the timeline (F83, `docs/gui/timeline/research.md`): phases 1a and 1b need no owner answers.

## Lessons

- After `git rm`, stage with `git add -A`, not a path list: a missing path aborts the whole add.
- A new control needs:
  - an inventory entry;
  - a place in `ngui/layout.py` (check that it is not already placed);
  - `python tests/tools/ngui_inventory.py`;
  - `dump_tooltips` regenerated.
- New preference keys go into `tests/test_gui_preferences.py`'s expected dict.
- Run the sweep in a separate worktree so that editing doesn't change files under it.
