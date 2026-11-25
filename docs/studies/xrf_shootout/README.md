# XRF shootout: how it was run

The study is in `summary.md`, the questions and their answers in
`QUESTIONS.md`, and the survey of other packages in `survey.md`. This page
says how to reproduce it.

## Environment

The reader's own environment does not need any of this. The shootout
needs the other packages, so it ran in its own conda environment
(Windows 10, 16 cores and 32 threads, 128 GB RAM; 2026-11-25):

    conda create -p <env> -c conda-forge python=3.12 pymca xraylib fisx scikit-beam exspy \
        numpy scipy matplotlib lmfit pyqt pytest pytest-xdist pyyaml sympy pillow openpyxl pandas
    <env>/python -m pip install xraylarch

| Package | Version |
|---|---|
| Python | 3.12.16 |
| PyMca5 | 5.9.7 |
| xraylib | 4.3.0 |
| scikit-beam | 0.0.27 |
| xraylarch | 2026.3.1 |
| lmfit | 1.3.4 |
| numpy / scipy | 2.5.5 / 1.18.1 |

XeRay is MATLAB, so it was ported rather than installed. The port is
`xeray()` in `tests/tools/xrf_shootout.py`, from `functions/fluoCurveFit.m`
and `XeLineshape.m` of github.com/ZhiliangGong/xeray as of 2026-11-25.

## Commands (from the repository root)

    # 1. tables from xraylib (lines, Compton profiles) and the check of the remembered constants
    python tests/tools/xrf_tables.py --check docs/studies/xrf_shootout

    # 2. the shootout: 40 conditions x 100 series of 10 spectra, 7 XFNTR curves x 40 (about an hour, 30 workers)
    python tests/tools/xrf_shootout.py --out docs/studies/xrf_shootout/run --replicates 100 \
        --series-replicates 40 --chunk 5 --jobs 30
    # 2b. the measured-detector conditions, added after the main run
    python tests/tools/xrf_shootout.py --out docs/studies/xrf_shootout/run_measured --replicates 100 \
        --series-replicates 40 --chunk 5 --jobs 30 \
        --conditions measured,measured_strong,measured_12keV,xfntr_measured

    # 2c. PyMca with other background settings (to give it its best chance), every condition
    python tests/tools/xrf_shootout.py --out docs/studies/xrf_shootout/run_pymca --replicates 100 \
        --series-replicates 40 --chunk 5 --jobs 30 --methods pymca_snip60,pymca_snip100,pymca_poly

    # 3. figures, tables.md and wins.csv
    python tests/tools/xrf_shootout_figures.py --out docs/studies/xrf_shootout \
        --run docs/studies/xrf_shootout/run,docs/studies/xrf_shootout/run_measured,docs/studies/xrf_shootout/run_pymca

All three are in the Tools menu under Fluorescence (MCA). `--rows` makes
step 2 also write `estimates.csv`, every estimate (tens of MB; not
committed).

**Things that bite.**
- The script sets `OPENBLAS_NUM_THREADS=1` and its relatives before it
  imports numpy. Without that, 30 workers × 32 OpenBLAS threads exhaust
  Windows' commit limit and the pool dies ("Memory allocation still failed
  after 10 retries"). Measured on this machine.
- PyMca prints "Needed 10 iterations" to standard output. This is not an
  error.
- Larch prints "No conda env active, defaulting to base" on import. This
  is harmless.
