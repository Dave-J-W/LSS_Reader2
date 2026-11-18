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
