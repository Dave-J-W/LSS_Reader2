"""L as Qz: the beamline's SPEC lattice (TODO area L, 2026-11-24).

At 15-ID-C the SPEC lattice is set so that L is Qz in Å⁻¹ and H, K are the
in-plane components (Qx, Qy): L = (2π/λ)(sin α + sin β), with α the
incidence (header In_Rot) and β the exit angle (header Out_Rot). In a
specular scan α = β and L = 4π sin α/λ. Measured on NX school: every scan
at fixed L agrees to better than 0.1 % (physics_notes 2026-11-24, I35),
the raised GID level of scan 12 included (β = 6.5°).

A changed lattice would scale every Qz silently, so a scan at fixed L
whose L disagrees with its angles by more than ``TOLERANCE`` is noted at
load time. Only scans whose header gives both angles are checked: without
Out_Rot a raised detector arm (a GID level) would look like a wrong
lattice. Nothing is changed.
"""
import math

import numpy as np

TOLERANCE = 0.01          # relative
MIN_L = 1e-3              # 1/Å: below it (direct-beam scans, L ≈ 0) the ratio means nothing


def qz_from_angles(alpha_deg, beta_deg, wavelength):
    """(2π/λ)(sin α + sin β), Å⁻¹; β None: the specular 4π sin α/λ."""
    a = math.radians(alpha_deg)
    b = a if beta_deg is None else math.radians(beta_deg)
    return 2 * math.pi / wavelength * (math.sin(a) + math.sin(b))


def relative_difference(columns, parameters):
    """L / Qz(angles) − 1 for a scan at fixed L; None when L moves, In_Rot,
    Out_Rot or the wavelength is missing, or L is too small to compare."""
    l = columns.get('L') if isinstance(columns, dict) else None
    lam, alpha, beta = parameters.get('Wavelength'), parameters.get('In_Rot'), parameters.get('Out_Rot')
    if l is None or lam is None or alpha is None or beta is None:
        return None             # without the exit angle a raised detector arm (GID) cannot be told apart
    try:
        l = np.asarray(l, float)
        lam, alpha, beta = float(lam), float(alpha), float(beta)
    except (TypeError, ValueError):
        return None
    if l.size == 0 or not np.all(np.isfinite(l)) or lam <= 0 or np.ptp(l) > 1e-9 * max(abs(l).max(), 1.0):
        return None
    q = qz_from_angles(alpha, beta, lam)
    if abs(l[0]) < MIN_L or abs(q) < MIN_L:
        return None
    return float(l[0] / q - 1.0)


def l_mismatch(columns, parameters, tolerance=TOLERANCE):
    """``relative_difference`` when it exceeds ``tolerance``, else None."""
    d = relative_difference(columns, parameters)
    return d if d is not None and abs(d) > tolerance else None
