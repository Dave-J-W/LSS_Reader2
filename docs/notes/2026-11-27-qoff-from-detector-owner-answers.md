# F42, Qoff from where the reflection lands: the owner's answers (issue #174)

- **Date, who:** 2026-11-27, questor. Asked of the owner for main man's issue #174, part of #148. The question
  and its data are in `docs/notes/2026-11-27-qoff-from-detector-position.md`.
- **Answer, question by question** (the owner's words in quotation marks):
  1. **What forms the spot on the Pilatus?** The owner did not confirm or deny a narrow slit (S6) on the
     detector arm and gave no slit-to-detector distance. The answer was: "Since 2023 an Axilon curved mirror
     focuses the beam. S1 slits do cleanup on a Gaussian beam." Read together with the sh-scan finding (both
     spots stay at one row while Out_Ht moves), this points to the focused beam, not a detector-arm slit,
     as what the two spots are images of; that reading is ours, not the owner's. **Still open:** whether
     an S6-type slit exists on the arm and how far it is from the detector.
  2. **Which route did F42 mean?** **Both**: the absolute route (the separation of the direct beam and the
     reflection in the sh scans gives the true α at the alignment angle) **and** the relative route (each
     reflectivity frame's row against the sh scan's).
  3. **The absolute route's distance.** The distance is known to about **1 %**, and sh scans at several
     angles on one sample **are possible**. So distance and offset can be fitted together when such scans
     exist.
  4. **A change of the reflection's row.** "Usually surface tilt or curvature". Per the question's own
     arithmetic that shifts Qz by half of what an incident-angle error would, so the reader's default
     reading of a row change should be the tilt (half) and not the angle error.
- **How it is known:** the owner's answers only; nothing was run. The factor of one half for a tilt is
  taken from the question's text (issue #174), not rederived.
- **Numbers that changed:** none. Nothing changes in the reader until a coding session picks this up: the
  edge fits (`fresnel.propose_qoff`, `fit_edge_resolution`) stay the routes to Qoff.
