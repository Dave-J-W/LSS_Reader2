"""Synthetic data with known truth, for tests and method comparisons.

GUI-free generators; how to use each one, its parameters, sources and
limits are in docs/SYNTHETIC_DATA.md. The older writers (SPEC files,
Pilatus TIFFs, MCA files and the small data sets the GUI tests use) stay
in ``tests/synth.py``, whose outputs must not change.

- ``xrr``: reflectivity of layered liquid interfaces (Fresnel, Parratt,
  Névot–Croce, kinematic master formula, resolution), presets for bare
  water, a DPPC monolayer and a thick film.
- ``xrr_scans``: the measurement in reduced form: scans split as measured,
  absorbers, monitors, counting statistics, deliberate faults; rows like
  the reader's ``per_scan`` with the true factors beside them.
- ``xrr_images``: the same scans as a SPEC file and Pilatus frames whose
  ROI sums reproduce the reduced rows exactly.
- ``gid_levels``: a legacy GID set with three Qz levels (P36, P37).
- ``growing``: a SPEC file and its images written in steps (live mode).
- ``mca``: MCA spectra of fluorescence lines with the beam's Rayleigh and
  Compton scatter, the detector's tails, shelves and Si escape peaks, every
  part kept apart (F90).
"""
