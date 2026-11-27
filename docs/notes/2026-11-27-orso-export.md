# ORSO export: a box on by default; Qz, R, sR, sQz; the owner from Preferences

- **Date, who:** 2026-11-27, main man (F25's open points, asked of the owner while doing #148)
- **Answers (owner):**
  - **When:** "checkbox, on by default". "+ ORSO" beside "+ covariance"; Export writes `<name>.ort` with `_ref.txt` and `_rrf.txt` while it is ticked.
  - **Columns:** "Qz, R, sR, sQz". R and sR as in `_ref.txt` (the error model in use), and sQz when the reduction records a Qz resolution.
  - **Header:** "From Preferences". The owner's name and affiliation are typed once in Preferences > ORSO header; the sample's name comes from the series macro, as Export's proposed name does.
- **What the file holds:** ORSO text format v1.2, written by `orsopy` 1.2.3 (the format's reference implementation; <https://www.reflectometry.org/>, <https://orsopy.readthedocs.io/>).
  - The header holds the owner and the experiment: beamline 15-ID-C ChemMatCARS, the Advanced Photon Source, probe x-ray, the date of the first scan's `#D`.
  - It holds the sample, the incident-angle range (α = asin(Qz λ / 4π) over the curve), the wavelength (`#W`), and the SPEC file with its scans.
  - It holds the reduction: software and version, the corrections in words, and `call`, the lss_core script that reproduces the curve.
- **Caveat, found while building:** no reduction in the reader records a Qz resolution today. The rows hold Qz, R and dR only, so the .ort files have three columns and a header comment saying so, until sQz is computed (issue #168).
- **How it is known:** test `tests/test_orso_export.py`. Files are read back with `orsopy.fileio.load_orso`, and the window's .ort holds the same curve as its `_ref.txt`.
- **Numbers that changed:** none. A new file beside the unchanged ones (`OUTPUT_DECISIONS`, 2026-11-27).
