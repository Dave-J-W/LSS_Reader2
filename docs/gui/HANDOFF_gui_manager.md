# Handoff: GUI manager session (written 2026-11-23, 21:30 UTC)

Owner: "Main is orchestrator; go ahead and build" (main window first, then
the timeline F83, then ngui). Report to Main (session_017UNj94caCtuQh48DiL9JQC,
send_message) and message it before large `mainwindow.py` edits. Standing
permission: merge my branch into `main` by PR + "Create a merge commit"
once the quick suite (and, for GUI changes, the sweep) pass; then merge
`main` back into the branch.

## State (updated 2026-11-24, 03:00 UTC)

- **On main:** everything through #32 (4b0cc45):
  - the Q14 removals; Quit and Documentation; D59 panes;
  - F85 badges; F86 Reduction options (with the test-speed session's keys sum_all_legacy_average, gisaxs_raw_counts, repeats_legacy_average);
  - the Q-GID-5 buttons; the Q-UI-A10 grey-out;
  - the crash fixes.

  My branch equals main.
- **Subagent (worktree `.claude/worktrees/agent-a8f7f050e5d54f80a`, branch `worktree-agent-a8f7f050e5d54f80a`):** building F88 (sticky display, Home/Fit all) and the F69 movie, keeping the display per Monc (pilFrameNormalised / pilSumNormalised; tests/test_monc_normalised must pass unchanged). On its report:
  1. merge its branch, then main;
  2. quick suite; full sweep in `scratchpad/wt_sweep`;
  3. PR;
  4. tell Main the image display is free, so it can do the list item-data plumbing.
- **The image display functions are reserved** for that work: updatePilPlotData, pilMovieShow, update2dPlots, the pilMin/Max sliders.

## Next, in order

1. Merge the F88/F69 subagent's work (above).
2. F96 Ref Patch window: Back; a Cancel that does not abandon silently; a join table kept with the result; the provenance line under results. Message Main with the function list first.
3. F95 (wire the bad-pixel controls; Ref Patch warnings as messages and marks), F97 display side (saturation cue; one ROI close-up panel), F74 weighted residuals panel.
4. Timeline (F83): 1a, the super-Gaussian fit as new functions in lss_core/peaks.py, leaving height_scan_options and is_height_scan unchanged; 1b, lss_core/timeline.py. Ask the owner whether the tab goes in the main window (Main reads it so).

## Lessons

- After `git rm`, stage with `git add -A`, not a path list: a missing path aborts the whole add.
- A new control needs:
  - an inventory entry;
  - a place in `ngui/layout.py` (check that it is not already placed);
  - `python tests/tools/ngui_inventory.py`;
  - `dump_tooltips` regenerated.
- New preference keys go into `tests/test_gui_preferences.py`'s expected dict.
- Run the sweep in a separate worktree so that editing doesn't change files under it.
