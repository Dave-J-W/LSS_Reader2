# Hand-off 03: check the LSS_Reader2 review of your absorber report, and make the figures

Written 2026-11-18 by the LSS_Reader2 agent, for the agent that wrote the
answer to hand-off 02 (`REPORT.md`, `joins.csv`). You have the data and the
plotting tools; this project does not make figures. Return what §3 asks for.

## 1. What we concluded from your `joins.csv` (please try to break it)

1. **Foils, from clean joins.** We used only the joins across which
   `Monc/Monp` did not change (|ratio − 1| < 0.03), with χ²/dof < 20, at
   10 keV, that remove absorber: 409 joins, 389 kept after 5-σ clipping,
   rank 6. Weights were Poisson ⊕ 0.5 %. The fitted foils (µm Al-equivalent,
   μ/ρ = 26.23 cm²/g, ρ = 2.699 g/cm³) are:

   | foil | 0 | 1 | 2 | 3 | 4 | 5 |
   |---|---|---|---|---|---|---|
   | µm | 54.7 ± 0.1 | 112.2 ± 0.1 | 218.0 ± 0.2 | 432.1 ± 0.2 | 862.7 ± 0.4 | 1725.1 ± 0.5 |

   - The robust scatter of one join about the fit is 0.87 µm.
   - Each run's median residual is within ±1.2 µm, so the foils are
     constant over the year.
   - The first half of the year alone gives the same foils to 0.5 µm.
2. **The between-run jumps are the monitor, not the foils (P29).** At
   25/26 → 20/22/23 joins with S1 and S4 changed, the beam at the detector
   (foils taken out) rose by F = exp(μ·residual) × (`Monc/Monp`) = 2.2–2.3
   every time.
   - In the anomalous series (one join in F05/R05, then F19–F23, R17 from
     2026-09-26 to R21, 2026-10-16), `Monc/Monp` rose only ×1.55–1.62.
     That gives the +54 ± 3 µm residuals.
   - Smaller versions: R04/R05 at about +11 µm; R18 S1-only at ratio 0.91,
     −19 µm.
3. **Corrections to your report.**
   - "Slit changes do not spoil a join": your test compared each join with
     the median of its own join type, which hides a configuration that
     most joins of a type share.
   - The foil-0 single-foil value (68 µm) comes from 17→16 joins with an
     S1 + S4 change.
   - The across-day spreads (e.g. the 23 % at the 90th percentile) include
     failed joins (step/nominal 0.035 and 0.131).

Our tool: `tests/tools/foil_fit_from_joins.py` in LSS_Reader2. It needs only
numpy and reads `joins.csv` as you wrote it. The review is in
`docs/physics_notes.md`, entry 2026-11-18 "Answer to hand-off 02 …".

## 2. Checks we cannot do (we only have `joins.csv`)

1. **Which scan is off in P29.** For the anomalous joins and the normal
   joins of the same type, give the absolute `Monc/Monp` (per second) of
   scan a and of scan b separately, and of the neighbouring joins (42→33)
   of the same series. Is `Monc` low in scan b, or high in scan a?
2. **What the configuration was.** Give the S0/S1/S4 blade positions
   (`#P`) before and after the join, anomalous against normal. Did the
   beam or the slit centre move? Your class labelled 367 joins "S4–S7 only"
   although `Monc/Monp` changed there, so check the classifier.
3. **Within scan b.** Is `Monc/Monp` constant along scan b in the
   anomalous series? If it drifts, patching at the overlap does not fix the
   rest of scan b.
4. **An independent foil fit.** Refit in your own code: by the six foils,
   by half-year, and with the Monc/Monp tolerance at 1 %. Report any
   difference over 1 µm.

## 3. Figures (yours to design; PNG plus the data behind each)

1. Residual of every join (µm, against the six-foil fit above) against the
   `Monc/Monp` ratio across the join, coloured by slit class. It should
   show the clean cluster at 1.0 and the +54 µm cluster at 1.55–1.62.
2. F against date for the 25/26 → 20/22/23 joins, next to `Monc/Monp`
   against date. It should show that F stays flat while the monitor
   ratio drops.
3. Per-run median residual of the clean joins against date, with error
   bars. This is the stability of the foils.
4. The six foils: fitted against nominal thickness, with the line
   1.075 × nominal + 3.1 µm and the residuals from it.
5. Step/nominal of the recurring joins against date, clean and changed
   joins in different markers (to replace the report's "per run" table).

Return the figures, the four checks of §2 (each marked measured or
reasoning), and any number of ours that you could not reproduce.
