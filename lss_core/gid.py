"""Settings of the GID patch (the window's "GID Patch"), in one place.

Every value here was a number written into the patch code; the defaults
are those numbers, so the patch is unchanged until a value is edited in
the GID worksheet (F61). Where each one acts:

- ``columns``: pixels summed across each frame around the direct-beam
  column (the window's H slit field); one profile per frame, placed at the
  frame's detector angle.
- ``row_min``, ``row_max``: detector rows used (β range).
- ``qz_decimals``: frames are grouped into Qz levels by their Qz rounded
  to this many decimals (at most three levels: low, middle, high; any
  further level goes into "high").
- ``dth_decimals``: the detector angle (degrees) is rounded to this many
  decimals before frames are ordered and joined.
- ``area_correction``: divide by the illuminated footprint fraction seen
  through the slits (``calArea``); ``hard_slit_offset_mm`` is the 32 mm by
  which the sample-detector distance is shortened there with hard slits.
- ``polarisation``: divide by 1 − (sin 2θ cos β)².
- ``vjoin_kind``: interpolation of the β-integrated profiles in the
  vertical join (Qz levels); the horizontal join is linear.
- ``pinhole``: patch in pinhole geometry instead (lss_core.pinhole, F45):
  every usable column at its own 2θ; the default (owner, 2026-11-18: pinhole
  is how GID is measured); off gives the patch above exactly as before. ``pinhole_distance_mm``: S4 → detector, 0 for the header
  value; ``response``: 'fit' or 'none' (column response);
  ``arm_correction``: the g_l3 term in the vertical distance;
  ``min_frames``: 2θ bins seen by fewer frames are left out (map edges);
  ``transverse``: 2θ range of a map joined from several Qz levels,
  'intersection' (common to all, IDL) or 'union' (F62).
"""
from dataclasses import dataclass, fields


@dataclass
class GIDParams:
    columns: int = 3
    row_min: int = 15
    row_max: int = 486
    qz_decimals: int = 3
    dth_decimals: int = 3
    area_correction: bool = True
    hard_slit_offset_mm: float = 32.0
    polarisation: bool = True
    vjoin_kind: str = 'cubic'
    pinhole: bool = True
    pinhole_distance_mm: float = 0.0
    response: str = 'fit'
    arm_correction: bool = True
    min_frames: int = 2
    transverse: str = 'intersection'

    def changed(self):
        """Names of the settings that differ from the defaults."""
        d = GIDParams()
        return [f.name for f in fields(self) if getattr(self, f.name) != getattr(d, f.name)]


def reduced_chi2(x, y, yerr, fac):
    """χ²/dof of the overlap ratios y ± yerr about the fitted factor."""
    n = len(x)
    if n < 2:
        return float('nan')
    return float(sum(((yi - fac) / ei) ** 2 for yi, ei in zip(y, yerr)) / (n - 1))
