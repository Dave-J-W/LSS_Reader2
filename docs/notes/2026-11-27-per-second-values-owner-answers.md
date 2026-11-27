# F20, per-second values: the owner's answers (issue #175)

- **Date, who:** 2026-11-27, questor. Asked of the owner for main man's issue #175, part of #148.
- **Already decided** (owner, 2026-11-15, `docs/PROJECT_CONTEXT.md` Q1): the default stays per monitor
  count; the per-second value is an additional output, divided by the point's counting time (SPEC `Seconds`),
  with the same relative error.
- **Answer, question by question:**
  1. **Which quantities?** The owner had no preference and left the choice to the sessions.
  2. **Raw or normalised?** No preference, left to the sessions.
  3. **Where, and the scale?** "Photons/s instead of counts/s **where the per-photon option exists**" (F54,
     the per-photon monitor option). So where a per-photon route exists the per-second value is in
     photons/s; elsewhere it stays counts/s.
- **What this leaves to the sessions:** the list of quantities (the issue's candidates are the reflectivity
  ROI's raw signal and background, the fluorescence line areas, GID intensities and cuts, the burn frames),
  raw against monitor-normalised, and whether the value is an extra column pair in the exported files, a
  "per s" choice on the plots, or both. A reasonable minimum: the ROI signal and background (where
  saturation and absorber choices show), as a plot choice, in photons/s when the per-photon option is on.
  That is a suggestion, not the owner's choice.
- **How it is known:** the owner's answers only; nothing was run.
- **Numbers that changed:** none.
