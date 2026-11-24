# Handoff: GUI manager session (written 2026-11-23, 21:30 UTC)

Owner: "Main is orchestrator; go ahead and build" (main window first, then
the timeline F83, then ngui). Report to Main (session_017UNj94caCtuQh48DiL9JQC,
send_message) and message it before large `mainwindow.py` edits. Standing
permission: merge my branch into `main` by PR + "Create a merge commit"
once the quick suite (and, for GUI changes, the sweep) pass; then merge
`main` back into the branch.

## State (updated 2026-11-24, 14:40 UTC)

- **On main:** everything through #44 (848b059):
  - F96, F95 part, F74 (scan, cut and burn fits), the F97 saturation cue;
  - F78 / timeline 1a, F83 / timeline 1b (lss_core/timeline.py);
  - the ROI close-up panel (F71, F97: lss_core.display.roi_boxes, roipanel.py);
  - the mca_fit_poisson switch.
- **The owner answered (2026-11-24):** the timeline tab goes **in the main window**.
- **Work in:** the worktree `.claude/worktrees/agent-ab9975ffcaf2237a8` (branch worktree-agent-ab9975ffcaf2237a8, the session's working directory since the restart). Fast-forward `claude/funny-noether-09opxa` from it with `git -C /home/user/LSS_Reader2 merge --ff-only worktree-agent-ab9975ffcaf2237a8`, then push that branch.
- **Building now:** timeline 1c, a 'Timeline' tab added last in PlotWidget (timelineview.py, a QGraphicsView of lss_core.timeline). test_reader_log's 'started 7' becomes 8 (deliberate).

## Next, in order

1. Timeline 1c: lanes (events, sx, sh scans, scans), zoom on the time axis, pan, fit, tooltips, click to select a scan; built when the tab is shown; rebuilt on a new SPEC file or live update.
2. F95: B3's threshold (needs an OUTPUT_DECISIONS row), B9 (Save vs Export names), B10 (dock frequent windows).
3. F97: the diffuse axes. F74 on the Ref Patch join preview and the older dialogs.
4. B7's live part: replay the stored joins through factors=.

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
