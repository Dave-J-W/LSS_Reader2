# A burn's first frame far from the next ones flattens its line: flagged, kept

- **Date, who:** 2026-11-27, main man (#188), from GID guy's diagnosis on #184.
- **Answer:**
  - On one private GID burn (P4 of the burn-shoulder study), the first frame is half as bright as the next three
    (0.50; its shoulder amplitude B is 0.45, so the whole frame is low), about 30 σ below them.
  - The weighted line through all 51 frames then reads the intensity's change as −2.9 % ± 0.9. Without that frame it
    reads −12.9 % ± 0.8.
  - Of 118 well-measured private GID burns, 2 have a first frame below 0.8 of the next three.
  - The burn test now flags such a frame (more than 5 σ and 20 % from the median of the next three) and gives the
    linear change both ways. It keeps the frame: leaving it out by default is the owner's decision.
- **How it is known:** GID guy's numbers on #184 (run, private). The flag is checked by
  `tests/test_burn_first_frame.py` (synthetic: a 12 % fall with a first frame at 0.5 is flagged, and the change
  without it recovers the truth; clean burns and 2.5 σ outliers are not; NX 14 and 15 are not flagged).
- **Numbers that changed:** none (`OUTPUT_DECISIONS`, 2026-11-27, "Flag only").
