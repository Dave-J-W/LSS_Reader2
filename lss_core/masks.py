"""Dropped points as a mask over raw points, kept in the per-SPEC workbook
(F92, D2, F16; owner, 2026-11-23: "saved as a mask in the config file (the
per-SPEC state), and a 'Restore all' button is included in the patch
dialog").

A mask is a set of (scan, point): point numbers within the scan, as SPEC
counts them (the frame number of a Pilatus scan). The reduction leaves
those points out from the start (``Experiment.reflectivity(mask=...)``),
so it can always be repeated from the raw data, and undoing is a change to
the mask ("Restore all" empties it; owner: undo of single drops is not
asked for). The window's typed drops (indices into the curve joined so far
or into the new scan) are turned into raw points by
``lss_core.reflectivity.drop_points``.

Masks are kept in the workbook's Settings sheet, section ``masks``, one row
per kind of reduction ('reflectivity' today), the value a JSON list of
[scan, point] pairs, sorted. The workbook keeps its seven sheets (the
owner's limit: fewer than eight).
"""
import json

SECTION = 'masks'
KINDS = ('reflectivity',)


class Mask:
    """A set of (scan, point) pairs."""

    def __init__(self, points=()):
        self._p = set()
        self.add(points)

    @staticmethod
    def _pair(sp):
        s, p = sp
        return int(s), int(p)

    def add(self, points):
        for sp in points:
            self._p.add(self._pair(sp))
        return self

    def remove(self, points):
        for sp in points:
            self._p.discard(self._pair(sp))
        return self

    def restore_all(self):
        """Empty the mask (the patch dialog's "Restore all")."""
        self._p.clear()
        return self

    def of_scan(self, scan):
        """The masked points of ``scan``, sorted."""
        return sorted(p for s, p in self._p if s == int(scan))

    def scans(self):
        return sorted({s for s, _ in self._p})

    def pairs(self):
        """Sorted [scan, point] lists (the stored and the recipe form)."""
        return [[s, p] for s, p in sorted(self._p)]

    def __contains__(self, sp):
        return self._pair(sp) in self._p

    def __iter__(self):
        return iter(sorted(self._p))

    def __len__(self):
        return len(self._p)

    def __eq__(self, other):
        return isinstance(other, Mask) and self._p == other._p

    def __repr__(self):            # a script line rebuilds it
        return 'masks.Mask(%r)' % (self.pairs(),)


def load(workbook, kind='reflectivity'):
    """The mask of ``kind`` kept in ``workbook`` (empty when none, or when
    the stored value cannot be read)."""
    v = workbook.settings(SECTION).get(kind)
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except ValueError:
            v = None
    try:
        return Mask(v or ())
    except (TypeError, ValueError):
        return Mask()


def save(workbook, mask, kind='reflectivity'):
    """Keep ``mask`` as the mask of ``kind`` in ``workbook`` (the other
    kinds' masks unchanged; the workbook is written by its own ``save``)."""
    if kind not in KINDS:
        raise ValueError('mask kind %r: one of %s' % (kind, ', '.join(KINDS)))
    stored = workbook.settings(SECTION)
    stored[kind] = Mask(mask).pairs() if not isinstance(mask, Mask) else mask.pairs()
    workbook.set_settings(SECTION, {k: stored[k] for k in sorted(stored)})
