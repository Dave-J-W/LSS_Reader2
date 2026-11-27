# The beam's size at the sample is not tied to the Qz resolution

- **Date, who:** 2026-11-27, data session on the owner's PC (Reflection guy), asked by the owner: "how
  correlated are the beam size (from the sample-height scan's edge width) and the Qz sigma?"
- **Answer:** not correlated. Over 16 runs (10 keV, S1 0.04 mm, 349 edges) the run medians give r = +0.01
  (95 % bootstrap −0.42 to +0.55); within runs the Spearman correlation is +0.04 (p = 0.48). The beam stays
  at 14.7–18.1 µm while σ_Q goes from 2.7 to 5.3 × 10⁻⁴ Å⁻¹. So a run's height scans cannot predict its
  resolution: fit the edge. Geometrically, either the sample sits within about 0.2 m of the mirror's focus
  (95 % bound 0.21 m), or σ_Q's run-to-run changes are not the beam's (the surface or the edge model).
- **How it is known:** run, on the private files (`sample_data/private/xr/scripts/beamq_pair.py`,
  `beamq_publish.py`), with five synthetic cases and a known-truth check of the distance estimator from
  `tests/tools/beam_size_vs_resolution_synthetic.py`. Study: `docs/studies/beam_size_vs_resolution/summary.md`.
- **Numbers that changed:** none (no default touched).
