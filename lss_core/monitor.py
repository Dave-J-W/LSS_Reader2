"""The `Monc` amplifier gain, for normalising by monitor current, not counts.

`Monc` is a current amplifier (SR570) followed by a voltage-to-frequency
converter (V2F). The SR570 sensitivity S (A/V, e.g. "5 uA/V") gives
V = I / S, and the V2F gives counts M = G · V · t, so

    I · t = M · S / G .

Counts per photon therefore scale as 1/S: two scans taken at different
sensitivities are on different scales after dividing by M. SPEC records S
in the scan header as ``#M Monc Gain 5 uA/V`` (Stanford Research Systems,
SR570 manual, https://www.thinksrs.com/downloads/pdfs/manuals/SR570m.pdf).

Option "monitor gain" (F52; owner, 2026-11-17): divide by M · S / S_ref
instead of M, i.e. multiply a normalised value (and its error) by
S_ref / S. S_ref = 1 µA/V, so values read as "per monitor count at
1 µA/V". G (the V2F scale) is the same for all scans and is not needed for
comparisons; a conversion to photons per second (owner, later) will bring
G and the monitor's efficiency as one scalar.

A line without a unit ("#M Monc Gain 200") or without a value is read as
unknown: no factor is applied and the window says so.
"""
UNITS = {'pA/V': 1e-12, 'nA/V': 1e-9, 'uA/V': 1e-6, 'µA/V': 1e-6, 'mA/V': 1e-3, 'A/V': 1.0}
REFERENCE = 1e-6          # A/V: values are per monitor count at 1 µA/V


def parse_gain(words):
    """Sensitivity in A/V from the words after '#M Monc Gain' (None: unknown)."""
    if len(words) != 2 or words[1] not in UNITS:
        return None
    try:
        value = float(words[0])
    except ValueError:
        return None
    return value * UNITS[words[1]] if value > 0 else None


def gain_factor(sensitivity, reference=REFERENCE):
    """S_ref / S, the factor on a value normalised by M (1 when S is unknown)."""
    if sensitivity is None:
        return 1.0
    # 12 significant digits: S and S_ref are decimal settings, so this
    # removes binary rounding (1e-6 / 2e-7 gives 4.999999999999999)
    return float('%.12g' % (reference / sensitivity))
