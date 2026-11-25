# A bad-pixel pass on the reflectivity ROI (F95 B3, C62): summary

*main man, 2026-11-25. Known truth, synthetic frames reduced by the reader's own arithmetic, plus the public
NX school frames. The whole chain, step by step: `walkthrough.md` (rule 13). Tool:
`tests/tools/roi_bad_pixel_study.py`. No default is changed.*

**The question:** should the reflectivity ROI get a bad-pixel pass of its own, which the owner asked to wire
(Q-UI-B3), and does a pass ever replace real signal on sparse frames?

**The answer:**
- **Hot pixels matter on sparse frames only, and there a lot.** At 0.5 hot pixels per frame (3–300 counts
  each), the end of a weak curve gains 11 error bars of extra scatter per point. The join factors' pull SD
  goes from 1.21 to 1.42. On bright frames hot pixels add at most 0.4 error bars.
- **The ROI pass at factor 10, the field's default,** removes 90 % of them on sparse frames. It brings the
  joins back to 1.22, and it never touched a frame without a hot pixel: 21,702 synthetic frames, closest
  margin 0.89, and the 96 real NX frames, closest 0.57.
- **Factor 3, and the whole-frame pass at factor 4** (today's Frames > Reduce option), take half of a real
  sparse point in 0.2–0.9 % of such frames.
- **Factor 40** leaves more behind (2.9 % bias at the end of the curve).
- **A background-only pass is worse than none** (+107 % bias).
- **On NX school** no pass changes anything at any factor (the frames are bright). Factor 10 as a default
  would leave every NX number, and so the legacy export fixtures, as they are.

**Recommendation (rule 12):**
- **Factor 10 on the three boxes is the candidate default.** Before the switch:
  1. a count on the owner's sparse high-Qz frames: how many ROI pixels factor 10 would replace, their
     margins, how far the points move (the local agent, DATA_NEEDS row 16);
  2. the core option in `lss_core` with tests;
  3. the window's field wired, off by default until then (GUI manager).
- **The whole-frame pass's tooltip** should say that factors below 10 can take real signal on sparse frames.

| figure | shows |
|---|---|
| R1 | one sparse frame, two hot pixels, what factors 10 and 3 replace |
| R2 | the extra scatter per point, by Qz, for each pass and condition |
| R3 | which hot pixels each pass replaces: the threshold |
| R4 | the join factors' pull SD |
| R5 | how close frames without a hot pixel come to being touched, at factors 3 and 10 |
