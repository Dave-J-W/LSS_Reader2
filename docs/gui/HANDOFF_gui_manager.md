# Handoff: GUI manager session (written 2026-11-23, 21:30 UTC)

Owner: "Main is orchestrator; go ahead and build" (main window first, then
the timeline F83, then ngui). Report to Main (session_017UNj94caCtuQh48DiL9JQC,
send_message) and message it before large `mainwindow.py` edits. Standing
permission: merge my branch into `main` by PR + "Create a merge commit"
once the quick suite (and, for GUI changes, the sweep) pass; then merge
`main` back into the branch.

## State (updated 2026-11-24, 08:00 UTC)

- **On main:** everything through #34 (b6d7998): the main-window tranche (#32), the sticky display and the frame movie (F88, F70, F69), two GID crash fixes. The image display functions are no longer reserved.
- **On my branch, not yet merged** (each commit with its tests; quick suite 995 passed):
  - 87ae1bf F96: Ref Patch Back, Cancel, join table; refProvenanceLabel under the Reflectivity plot;
  - 5e60623 the reflectivity Save and title use the patch's scans (strict xfail removed);
  - 25d9b42 F95 part: the Ref Patch checks are a message plus marks; refBadPixListWidget wired.
- **The full sweep on 25d9b42** runs in `scratchpad/wt_sweep` (log `scratchpad/sweep_f95.log`). If it passes: PR into main, "Create a merge commit", fast-forward the branch, tell Main.

## Next, in order

1. Merge the branch (above).
2. F74: the residuals panel ((y − fit)/σ, about 15 % of the height, χ²/dof in the legend, hidden by default), as one shared plot helper for every fit plot.
3. F97 display side: the saturation cue (1e5 cps soft, 1.5e5 hard per pixel; needs the exposure time from the header, not checked), one ROI close-up panel.
4. F95 leftovers: B3's ROI threshold (changes numbers, so it needs an OUTPUT_DECISIONS row), B9 (Save vs Export names), B10 (dock frequent windows).
5. B7's live part: the live remake replays the stored joins through factors= (Main: live.parse accepts the dict).
6. Timeline (F83): 1a, the super-Gaussian fit as new functions in lss_core/peaks.py; 1b, lss_core/timeline.py. Ask the owner whether the tab goes in the main window.

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
