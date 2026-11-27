# Burn tests against dose as well as time (F76)

`dose_14_15.png` (with `dose_14_15.csv`, `summary_14_15.json`), made by
`python tests/tools/burn_dose_figure.py` from the public NX school burn
scans 14 (absorber 12) and 15 (absorber 8): 21 frames of 10 s each of one
GID peak, the reader's burn estimator (stretched). Asked for in
`docs/handoff_out/07-burn-trends.md` ("Dose instead of time") and
`docs/physics_notes.md` (2026-11-23, "Damage or a changing sample").

A change caused by the beam follows the dose (flux × time), a sample
changing by itself follows time. Left: each quantity against clock time;
right: against the dose Σ Monc·T, T the foils' transmission at the scan's
absorber (the calibrated foils at 10 keV: T = 0.0100 and 0.0469, flux ratio
4.68; the nominal 1.4247 per unit gives 4.12, the docs' "4.1×").

Measured (2026-11-23; regenerated 2026-11-24 with the GID-burn rows from
the mean frame, Q-BURN-6: the position ratio 3.70 → 3.69, the ends
1.46617 and 1.46577 → 1.46620 and 1.46582 Å⁻¹, the rest as before):

- **Position**: scan 15 drifts 3.69× faster than scan 14 against time
  (26σ apart), 0.79× as fast against dose (2.8σ apart; 0.90×, 1.3σ, with
  the nominal foils). Against dose the two drifts nearly coincide: what
  a beam-driven change would give, not a sample changing by itself.
- Scan 15 starts (1.46620 Å⁻¹) where scan 14 ended (1.46582 Å⁻¹ after a
  dose of 0.66): consistent with one spot measured twice;
  `--join` draws 15's dose and time after 14's.
- **Intensity** stable in both; **FWHM** stable in 14 and rising in 15
  (+17 %): no ratio is quoted where a scan shows no significant change.
- Not proven: two scans also differ in when they were taken, and the
  absorber transmission rests on the foil calibration.
