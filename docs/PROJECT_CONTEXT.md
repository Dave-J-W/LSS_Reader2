# Project context

As described by the project owner (2026-11-14), with notes on how the
current code relates to each point. The owner's statements are quoted or
closely paraphrased; the notes are observations from this repository.

## What the reader is

"LSS_Reader", usually just "reader".

1. **A parser and loader.** It parses a text SPEC output file and pulls raw
   data from disk: TIFF images (one file per frame) and text files of
   multichannel analyzer (MCA) data, which hold several 1D spectra (frames)
   per file. The data files live in directories with a fixed structure
   relative to the SPEC file.
2. **A data-reduction platform.** The SPEC file holds beam-monitor counts
   that are used to normalise the raw data; this is the first reduction
   step. Raw counts (pixels, groups of pixels called regions of interest,
   MCA channels, and others) are divided by the monitor counts. Each
   quantity has a Poissonian uncertainty that is propagated through every
   calculation. The effective normalised signal is akin to

       signal_photons / (counting_time × input_photons)

3. **Not a fitting platform.** Fitting is done downstream in a separate
   program, "xmodfit".

## How the current code relates

| Point | In this repository |
|---|---|
| Fixed directory structure | `pilatus/`, `apex/`, `vortex/` beside the SPEC file; file names `<spec>_SCAN-<n>_<frame>.tif` and `<spec>_<n>_mca` (`readSpecFile`). The October `bu` run also has `pilatus1m/`, which this version does not look in. |
| Monitor normalisation | Image data: counts / `Monc`, times `absfac**absorber` (`TwoDDetector.sumFiles`, `peakLocate`). MCA: counts / monitor × (real time / live time) (`updateMcaPlotData`). SpecPlot: optional division by a chosen column. |
| Poisson errors, propagated | σ_I = √I for Pilatus and MCA; for I/M the code uses σ² = σ_I²/M² + I²/M³, i.e. Poisson on both I and M. Sums and background subtraction add in quadrature. Tested as invariants I3 and I4 (`physics_notes.md`). |
| Per counting time | **Not explicit for images.** The code divides by monitor counts only; counting time enters only through the monitor, which integrates over the same time. For MCA a real/live time ratio (dead-time correction) is applied, which is not a division by counting time either. See question 1. |
| Not a fitting platform | The window nevertheless contains fitting: SpecPlot peak/edge fit shown in the plot title, a multi-peak fit dialog (Gaussian/Lorentzian + polynomial, via lmfit) for MCA and plot data, 2D Gaussian peak finding for the Bruker reflectivity ROI, burn-test exponential fits, g_l2/g_l3 and absorber-ratio calibration fits, and form-factor minima overlays on GID maps. See question 2. |
| Hand-off to xmodfit | Outputs are tab-separated text: `*_ref.txt` / `*_rrf.txt` (Q, R, σ), `*_qxy_gid.txt`, `*_qz_gid.txt`, `*_q2d_gid.txt`, `*_flu.txt`, cut files. These formats are an interface to keep stable. See question 3. |

## Consequences for testing and scope

- Monitor normalisation and its error propagation are the core contract.
  They are already pinned by unit tests; every reduction path (reflectivity,
  GID, GISAXS, cuts, MCA sums) should get an end-to-end check that a known
  number of photons per monitor count comes out with the Poisson error.
- The fitting features inside the reader all stay (owner, 2026-11-15), so
  they need characterisation tests like any other feature, even though the
  reader is not the fitting platform.
- The output file formats need tests of their own (columns, units, number
  formats) because another program reads them.

## Questions and answers

1. *Should image-derived signals be divided by counting time explicitly?*
   **Answered 2026-11-15:** keep the normalisation as it is by default (per
   monitor count). A per-second option for important quantities would be
   nice (F20). A photons-in estimate is planned to be stored in the SPEC
   file by the beamline; the reader should use it when it exists (F21).
2. *Which fitting features inside the reader must stay?*
   **Answered 2026-11-15:** everything already in the reader stays. xmodfit
   is far more sophisticated and remains the fitting platform. Some places
   in the reader need better fitting and more fit types (F22, to be scoped).
3. *Which reader output files does xmodfit read, and are their formats
   fixed?* **Pending:** the owner will provide a hand-off document.

Also decided 2026-11-15: the Bruker/Apex CCD detector is defunct and will
not be used again.
