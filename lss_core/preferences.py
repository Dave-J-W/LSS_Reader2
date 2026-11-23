"""User preferences of the window, kept between sessions.

A small JSON file: ``$LSS_READER_PREFS`` if set (the tests set it to a
temporary file), otherwise ``~/.lss_reader/preferences.json``. Unknown or
unreadable values fall back to the defaults; nothing here is needed by
scripts, which pass every choice explicitly.
"""
import json
import os

ENV = 'LSS_READER_PREFS'

DEFAULTS = {
    # absorbers: calibrated foils (lss_core.absorbers.Foils) where they apply
    'calibrated_foils': True,
    # Ref Patch: use the known absorber ratio instead of the fitted factor
    # when the fit's relative error is above the threshold (lss_core.reflectivity.patch_choice)
    'patch_auto_known_ratio': True,
    'patch_threshold_percent': 3.0,
    # Ref Patch: how the factor at a join is fitted, 'joint' (one curve through both
    # scans, lss_core.patching; default since 2026-11-22, the gauntlet) or 'legacy'
    'ref_patch_method': 'joint',
    # multi-element fluorescence detector: elements to sum (empty: all). EXAFS sums
    # all seven; XFNTR uses the central one (owner, 2026-11-19)
    'mca_channels': [],
    # fitting (lss_core.peaks.FitOptions as a dict; owner, 2026-11-21: "save all the fitting
    # preferences in the config"): line cuts, and MCA lines (Rayleigh spill-over: quadratic)
    'peak_fit': {},
    'mca_fit': {'background': 'quadratic', 'n_peaks': 1},
    # the per-SPEC workbook (lss_core.workbook): ask for a note on every Save
    'save_asks_note': True,
    # save every finished reduction into the workbook (owner, 2026-11-22)
    'auto_save': True,
    # live updates: seconds between looks at the SPEC file (owner, 2026-11-22)
    'live_interval_s': 5.0,
    # burn tests (lss_core.burn, lss_core.trends): models compared, estimator, time axis,
    # the change that matters (%), automatic peak
    'burn': {},
    # the scan list: clicking a scan selects its whole series (owner, 2026-11-21)
    'select_whole_series': True,
    # detector frames are shown, cut and summed per Monc (owner, 2026-11-23). "Sum All":
    # counts and monitors summed, then normalised once, ΣN/ΣM (F91); True: the legacy mean
    # of the normalised frames. GISAXS: True shows the legacy raw counts (their mean when summed)
    'sum_all_legacy_average': False,
    'gisaxs_raw_counts': False,
    # ngui: a second window sketching the proposed layout (non-functional prototype, F82;
    # docs/gui/prototype.md); off by default (owner, 2026-11-23)
    'ngui': False,
}


def path():
    return os.environ.get(ENV) or os.path.join(os.path.expanduser('~'), '.lss_reader', 'preferences.json')


def load():
    prefs = dict(DEFAULTS)
    try:
        with open(path()) as f:
            stored = json.load(f)
    except (OSError, ValueError):
        return prefs
    for k, v in stored.items():
        if k in DEFAULTS and type(v) is type(DEFAULTS[k]) or (k in DEFAULTS and isinstance(DEFAULTS[k], float)
                                                               and isinstance(v, int) and not isinstance(v, bool)):
            prefs[k] = type(DEFAULTS[k])(v)
    return prefs


def save(prefs):
    """Write ``prefs``; returns the error text, or None."""
    p = path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as f:
            json.dump({k: prefs[k] for k in DEFAULTS if k in prefs}, f, indent=1)
    except OSError as e:
        return str(e)
    return None
