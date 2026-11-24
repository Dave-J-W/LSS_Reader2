"""Default axes of a scan's plot (SpecPlot).

An hklscan's first columns are H, K, L. The window used to plot every one
of them against L, so a scan along H or K was drawn against a constant
(TODO area L, 2026-11-24). The x axis is now the index that moves: the
#S command's (``hklscan h1 h2 k1 k2 l1 l2 n t``), or else the column that
varies most. L stays the default when nothing moves. Any other scan keeps
its first column (the scanned motor).
"""
import numpy as np

HKL = ('H', 'K', 'L')


def _moving_from_command(command):
    """Indices 0, 1, 2 (H, K, L) that an ``hklscan`` command moves, by how
    far, largest first; [] when the command is not one."""
    words = str(command or '').split()
    if '#S' in words[:1]:
        words = words[2:]
    if not words or words[0] != 'hklscan' or len(words) < 7:
        return []
    try:
        ends = [float(w) for w in words[1:7]]
    except ValueError:
        return []
    span = [abs(ends[2 * i + 1] - ends[2 * i]) for i in range(3)]
    return [i for i in sorted(range(3), key=lambda i: -span[i]) if span[i] > 0]


def default_x(labels, columns=None, command=''):
    """Index of the default x column. ``labels``: the scan's #L names;
    ``columns``: {name: values} (for the spread); ``command``: the #S line."""
    labels = list(labels)
    if labels[:3] != list(HKL):
        return 0
    moving = _moving_from_command(command)
    if moving:
        return moving[0]
    spread = []
    for i, name in enumerate(HKL):
        v = None if columns is None else columns.get(name)
        try:
            spread.append(float(np.ptp(np.asarray(v, float))) if v is not None and len(v) else 0.0)
        except (TypeError, ValueError):
            spread.append(0.0)
    if max(spread) > 0:
        return int(np.argmax(spread))
    return 2
