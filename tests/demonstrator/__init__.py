"""Demonstrator of the fitting methods on synthetic data with known truth
(owner, 2026-11-22: "a demonstration of fitting the synthetic data via plot
displays of the synthetic data, the denoised version, the fits of all
kinds, with a little gui to custom the plotted items and switch to new
replicate with spacebar. For burn tests i will also need a demo of the
line cut fits, so just add that as a mode to the demonstrator").

GUI-free and importable (tests, figure scripts and the window use the same
code):

- ``refl``: reflectivity patching. A replicate = a synthetic curve
  (``synthetic.xrr``) measured as overlapping scans (``synthetic.xrr_scans``)
  with counting noise from one seed; every patching method of
  ``lss_core.patching`` and the legacy ``lss_core.stitching`` applied; the
  truth (noise-free scans, true factors) beside the results.
- ``burnmode``: GID burn line cuts. A replicate = burn profiles
  (``synthetic.burn_profiles``) from one seed; every estimator of
  ``lss_core.burn`` with its per-frame fitted curve, and the trends
  (``lss_core.trends.compare``) of the values over time.
- ``draw``: matplotlib drawings of both, into any Figure (Agg or Qt), with
  a ``show`` set choosing the plotted items.

The window and the figure writer: ``python tests/tools/patch_demo.py``
(``--save DIR`` for figures without a display). Report:
``docs/reports/patch_demo.md``. Needs ``tests/`` on ``sys.path`` (as in
the test suite) for ``synthetic``.
"""
