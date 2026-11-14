# Physics notes and Q&A log

Running record of questions asked during the work on this fork and the answers
given, with emphasis on invariant quantities. Newest entries at the bottom.
Each entry says whether the answer was verified (by test, by running, or by
reading only).

## Invariants

Collected here as they are established; each should point to a test once one
exists.

| # | Invariant | Status |
|---|---|---|
| I1 | Fresnel reflectivity R_F(q) = 1 for q ≤ q_c | read from code, spot-checked by running `fresnel` |
| I2 | R_F(q) → (q_c / 2q)⁴ for q ≫ q_c | spot-checked: q = 0.3, q_c = 0.0217 gives 1.720e-6 vs (q_c/2q)⁴ = 1.711e-6 |
| I3 | Monitor-normalised intensity I/M has σ² = σ_I²/M² + I²/M³ | read from code, no test yet |
| I4 | Background-subtracted ROI signal S − (L+R)/2 has σ² = σ_S² + (σ_L² + σ_R²)/4 | read from code, no test yet |
| I5 | Normalised GID footprint area lies in [0, 1] | read from code, one value computed (0.7355), no test yet |

## Q&A

### 2026-11-14 — What is in LSS_Reader and what state is it in?

**Q.** Familiarise with the repository ahead of verification tests, debugging,
refactoring, new features and GUI reorganisation.

**A.** See [ASSESSMENT.md](ASSESSMENT.md). In short: a single 5400-line Qt
class holds the GUI and all physics; there are no tests; 18 defects were found
by reading, of which the most serious for users on current SciPy is that GID
multi-scan patching depends on the removed `interp2d`. The physics that tests
must preserve is tabulated in section 2 of the assessment.

Verification: source read; app launched headless; defects not yet reproduced.
