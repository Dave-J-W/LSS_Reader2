# On private GID burns, the split and the template disagree on 1 burn in 3, and the shoulder drives it

- **Date, who:** 2026-11-27, GID guy (local data agent), issue #155, hand-off 10.
- **Answer:**
  - Of the 155 private GID burns read (118 well measured), the template and the split give different
    intensity verdicts on 15 (13 %). They disagree in some way on 39 (33 %).
  - Real widths are steady: the median change is 1.4 %, and only 5 burns change by 10 % or more. So the
    driver is not P44's width mechanism. It is shoulders that change: about a quarter of them do. A changing
    shoulder is seen on 67 % of the disagreeing burns and on 27 % of the agreeing ones.
  - At real counts, the frames fit a Gaussian shoulder no better and no worse than the template
    (χ²/dof 1.1 under both).
  - A smoothed mean frame doesn't move the steady burns' reads.
  - The split changes F76's verdict in 3–5 of 14 flux series.
- **How it is known:**
  - Run: `python tests/tools/burn_shoulder_study.py --real …` on every private file with GID burns, then
    `sample_data/private/burn_shoulder/analyse_final.py` and `q5_q6.py` (private).
  - The published summary `docs/studies/xr_burns/gid_split.csv` regenerates figures R1 and R2 and the
    counts (`--only G`, test `test_the_published_real_burns_give_section_8s_counts`).
  - Details: `docs/studies/burn_shoulder/summary.md` section 8.
- **Numbers that changed:** none in the reader. The default stays the template.
