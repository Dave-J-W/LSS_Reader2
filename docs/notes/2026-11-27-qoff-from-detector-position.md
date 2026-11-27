# Qoff from where the reflection lands on the Pilatus (F42): what NX school shows

- **Date, who:** 2026-11-27, main man (found while doing #148, F42)
- **Answer:** NX school shows both beams on the detector in its sample-height scans, and the reflection's row
  barely moves during reflectivity. But neither gives a Qz offset until two facts about the instrument are
  known, which are the owner's (issue #174).
  - **Two spots in every sh scan** (4, 5, 10, 13; all at α 0.1017°, Sample_H −2.1985):
    - the direct beam at row 42.40 ± 0.05, one pixel tall (σ 0.24 px);
    - the reflection at row 52.95–53.07 on the plateau (σ 0.38–0.45 px).

    Their intensities trade off as the height rises. **Neither spot moves while Out_Ht travels 0.32 mm
    (1.86 px).** The reflection's staying put is the a2scan's purpose. The direct beam's staying put means the
    spot is not where the direct beam meets the detector. A narrow slit on the detector arm (S6 gap 0.05 mm)
    would explain it, with each spot an image of that slit.
  - **The separation is 10.55 px, where the nominal α and S2D_Dist predict 11.38 px** (2α · 551 mm / 0.172 mm).
    Read as an angle at 551 mm, it gives Qoff ≈ −1.3 × 10⁻³ Å⁻¹. The edge fits give −1.2 to −2.8 × 10⁻⁴
    (`docs/studies/qoff_resolution/summary.md` §4). At −2.7 × 10⁻⁴ the separation needs an effective distance
    of 518 mm. **So the absolute route needs the distance from the spot-forming slit to the detector to
    about 1 % per 2 × 10⁻⁴ Å⁻¹.** NX has sh scans at one angle only, so it cannot fit the distance and the
    offset together.
  - **During reflectivity (scans 6–9) the reflection's row is 52.90–53.08 from Qz 0.019 to 0.44.**
    - At Qz 0.0187, near the sh scans' angle, it is 52.98, the sh plateau's value.
    - It dips to 52.90–52.93 just above the edge.
    - It drifts up by 0.18 px to Qz 0.44.

    So the angle changes along the curve by at most 3–6 × 10⁻⁵ rad. That is about 1.5 × 10⁻⁴ Å⁻¹ near the edge
    and 0.15 % of Qz at 0.4. Measured against the sh scan's row, this relative route cannot see an offset
    that is already present at the alignment angle. Its factor also depends on the cause: an error in the
    incident angle moves the spot by δα · d, a tilt of the surface by 2τ · d.
  - **The reader today** compares the peak with the header's DBPos rounded to whole pixels, and warns above
    2 px (`reflectivity.frame_row`, F95). Every NX frame passes.
- **How it is known:** run, on NX school frames. A Gaussian (or two) plus a constant was fitted to the row
  profile summed over columns 40–54, weighted by √N. These were scratch scripts, not a committed tool. Out_Ht
  following the reflection was checked from scans 6–9's #P lines: −9.69 mm, against −9.76 mm for
  Sample_H + 551 tan α.
- **Numbers that changed:** none.
