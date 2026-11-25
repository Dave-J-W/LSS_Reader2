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

    # 2d. lines injected into the real blanks (tests/reference/mca_scatter): 240 conditions x 50 series of 10
    #     (about 50 minutes, 22 workers)
    python tests/tools/xrf_blanks.py --out docs/studies/xrf_shootout/run_blanks --replicates 50 --chunk 5 --jobs 22
    # 2e. the reader's single options (P1+P2, P1+P3) on the same spectra (a minute)
    python tests/tools/xrf_blanks.py --out docs/studies/xrf_shootout/run_blanks_options --replicates 50 --chunk 5 \
        --jobs 24 --methods p1p2,p1p3
    # 2f. real lines in real scatter: the 19 private burn series (needs the decrypted bundle; a few minutes)
    python tests/tools/xrf_real_series.py --out docs/studies/xrf_shootout/run_real --twins 20 --jobs 19

    # 3. figures, tables.md and wins.csv (and X9-X11, blanks_tables.md from run_blanks, X12, real_tables.md
    #    from run_real)
    python tests/tools/xrf_shootout_figures.py --out docs/studies/xrf_shootout \
        --run docs/studies/xrf_shootout/run,docs/studies/xrf_shootout/run_measured,docs/studies/xrf_shootout/run_pymca

All of them are in the Tools menu under Fluorescence (MCA). `--rows` makes
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
- Larch's fit window (`larch.xafs.xafsft.ftwindow`) indexes the energy
  array as if it began at 0 keV, so a spectrum that starts higher (the
  real blanks start 2.5 keV below the beam) fails with an IndexError. The
  shootout pads such spectra with empty channels down to 0 keV
  (`_larch_pad`).

**The private bundle (step 2f).** The spectra travel encrypted on the
transfer branch `claude/local-data-mca-encrypted` (never merged). Decrypt
them as `sample_data/encrypted/mca_spectra/README.md` there says, with the
owner's key in the environment variable `MCA_KEY`, into
`sample_data/private/mca_scatter_cloud/` (git-ignored). The script finds
the series' line from the data (`--line auto`) and writes no element
name, spectrum or frame-by-frame curve: only summary values per series.
