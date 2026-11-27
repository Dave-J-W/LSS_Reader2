"""Remaking saved results when their raw data grow (live updates, L2;
owner, 2026-11-22).

A result saved in the workbook carries its ``recipe``: the lss_core call
that made it, as the Script pane shows it (``ref = exp.reflectivity([6,
7, 8, 9], slit=(21, 11), ...)``). When its series gains scans (or its
scans gain points), ``remake`` runs that call again on the series' scans
now, and ``item_for`` turns the result into a workbook item.

The recipe text comes from a file a user can edit, so it is **not
executed**: it is parsed, and only these forms are accepted, every
argument a Python literal (numbers, strings, tuples, lists, dicts, None,
True, False) or one of the constructors in ``CONSTRUCTORS`` with literal
arguments:

- ``from lss_core... import ...`` (ignored; the names are known here);
- ``<name> = exp.<method>(...)`` with ``method`` in ``METHODS``;
- ``<name>.merge(...)`` on a fluorescence result, and ``<name>.fit_lines(FitOptions(...), ...)`` (the
  window's "Fit lines", #145) before its merges;
- on a cut (#145): ``<name>.summed_label = '...'`` and ``fits = <name>.fit(FitOptions(...))``, so a
  line cut is remade with its peak fits;
- ``<name>.save(...)`` and ``print(...)`` (skipped: remaking writes no files).

Anything else makes ``remake`` raise ``RecipeError`` with the reason; the
result is then left stale for the user to redo.
"""
import ast
from dataclasses import dataclass

import numpy as np

METHODS = ('reflectivity', 'fluorescence', 'gid', 'burn', 'cut', 'curve')
KINDS = {'reflectivity': 'reflectivity', 'fluorescence': 'fluorescence', 'gid': 'gid map', 'burn': 'burn test',
         'cut': 'line cut', 'curve': 'scan'}
ONE_SCAN = ('burn', 'curve')     # their first argument is one scan, not a list (a burn test, a SpecPlot curve)


class RecipeError(ValueError):
    pass


def _constructors():
    from .gid import GIDParams
    from .peaks import FitOptions
    from .absorbers import Foils, calibrated      # absfac=absorbers.calibrated(10.0), as recipes write it (#145)
    return {'GIDParams': GIDParams, 'FitOptions': FitOptions, 'Foils': Foils, 'calibrated': calibrated}


def _value(node):
    """A literal, or an allowed constructor with literal arguments."""
    if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)):
        name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        cons = _constructors()
        if name not in cons:
            raise RecipeError('call to %s is not allowed in a recipe' % name)
        args = [_value(a) for a in node.args]
        kw = {k.arg: _value(k.value) for k in node.keywords}
        return cons[name](*args, **kw)
    try:
        return ast.literal_eval(node)
    except ValueError:
        raise RecipeError('argument %s is not a literal' % ast.dump(node)[:80])


@dataclass
class Call:
    method: str
    args: list
    kwargs: dict
    merges: list          # keyword dicts of .merge calls (fluorescence)
    fitted: bool = False  # a cut's ``fits = cut.fit(...)`` (#145)
    fit: object = None    # its FitOptions (None: the defaults)
    summed_label: str = None   # a cut's ``cut.summed_label = ...``
    lines: dict = None    # a fluorescence result's ``.fit_lines(...)`` keywords (#145)


def parse(recipe):
    """The one exp call of a recipe (and its merges), checked (module docstring)."""
    try:
        tree = ast.parse(recipe or '')
    except SyntaxError as e:
        raise RecipeError('not Python: %s' % e)
    call, var, merges = None, None, []
    for st in tree.body:
        if isinstance(st, (ast.ImportFrom, ast.Import)):
            mod = st.module if isinstance(st, ast.ImportFrom) else st.names[0].name
            if not (mod or '').startswith('lss_core'):
                raise RecipeError('import of %s is not allowed' % mod)
            continue
        if isinstance(st, ast.Assign) and isinstance(st.value, ast.Call):
            f = st.value.func
            if (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == 'exp'
                    and f.attr in METHODS and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name)):
                if call is not None:
                    raise RecipeError('more than one reduction in the recipe')
                call = Call(f.attr, [_value(a) for a in st.value.args],
                            {k.arg: _value(k.value) for k in st.value.keywords}, merges)
                var = st.targets[0].id
                continue
        if call is not None and call.method == 'cut' and isinstance(st, ast.Assign) and len(st.targets) == 1:
            t, v = st.targets[0], st.value
            if (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == var
                    and t.attr == 'summed_label'):
                call.summed_label = _value(v)
                continue
            if (isinstance(t, ast.Name) and isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute)
                    and isinstance(v.func.value, ast.Name) and v.func.value.id == var and v.func.attr == 'fit'):
                call.fitted = True
                call.fit = _value(v.args[0]) if v.args else (_value(v.keywords[0].value) if v.keywords else None)
                continue
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):
            f = st.value.func
            if isinstance(f, ast.Name) and f.id == 'print':
                continue
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == var:
                if f.attr == 'save':
                    continue
                if f.attr == 'fit_lines' and call is not None and call.method == 'fluorescence':
                    args = [_value(a) for a in st.value.args]
                    call.lines = dict(zip(('options', 'poisson', 'detector_width', 'noise_kev', 'strip_escapes'),
                                          args), **{k.arg: _value(k.value) for k in st.value.keywords})
                    continue
                if f.attr == 'merge' and call is not None and call.method == 'fluorescence':
                    merges.append(dict(zip(('window', 'x', 'jitter'), [_value(a) for a in st.value.args]),
                                       **{k.arg: _value(k.value) for k in st.value.keywords}))
                    continue
        raise RecipeError('statement not allowed in a recipe: %s' % ast.dump(st)[:80])
    if call is None:
        raise RecipeError('no exp.<reduction>(...) call in the recipe')
    return call


def carry_points(points, then, now):
    """The point selection for a remake (owner, 2026-11-22: "point selection
    ... should be preserved across updates"): every frame the user left out
    stays out; frames written since (indices from ``then[scan]``, the
    scan's points when the result was saved, up to ``now[scan]``) are
    added; scans without a selection are used whole. ``points``: the
    recipe's {scan: [frames]} or None; returns it updated, or None."""
    if not points:
        return None
    out = {}
    for scan, chosen in points.items():
        scan = int(scan)
        chosen = sorted(int(c) for c in chosen)
        t, n = (then or {}).get(scan), (now or {}).get(scan)
        if t is not None and n is not None and n > t:
            chosen += list(range(t, n))
        out[scan] = chosen
    return out


def remake(recipe, scans, exp, then=None, now=None):
    """Run the recipe's reduction again on ``scans`` (the series' data scans
    now; a burn test keeps its one scan), with its point selection carried
    over (``carry_points``; ``then``/``now``: {scan: points} when saved and
    now). Returns (Call, result, scans used, points used)."""
    call = parse(recipe)
    kw = dict(call.kwargs)
    raw = kw.pop('points', None)
    if call.method == 'burn' and isinstance(raw, (list, tuple)):       # a burn's points: one scan's list
        raw = {int(call.args[0]): list(raw)}
    pts = carry_points(raw, then, now)
    if call.method == 'burn':
        used = [int(call.args[0])]
        if pts is not None and used[0] in pts:
            kw['points'] = pts[used[0]]
        res = exp.burn(used[0], **kw)
    elif call.method == 'curve':                          # a SpecPlot curve: its one scan, all its points (#145)
        used = [int(call.args[0])]
        res = exp.curve(used[0], *call.args[1:], **kw)
    else:
        used = sorted(int(s) for s in scans)
        if pts is not None:
            kw['points'] = pts
        res = getattr(exp, call.method)(used, *call.args[1:], **kw)
    if call.method == 'cut':
        if call.summed_label is not None and getattr(res, 'summed_label', None) is not None:
            res.summed_label = call.summed_label
        res.fits = res.fit(call.fit) if call.fitted else None
    if call.lines is not None:
        res.fit_lines(**call.lines)
    for m in call.merges:
        res.merge(**m)
    return call, res, used, pts


def item_for(call, res, scans, label=''):
    """(kind, [workbook items]) for a remade result, as the window's Save makes them."""
    kind = KINDS[call.method]
    if call.method == 'reflectivity':
        scans = list(scans)
        d = np.asarray(res.ref, float)
        items = [dict(scans=scans, data=d, columns=['Qz', 'R', 'dR', 'dQz'][:d.shape[1]], label='R')]
        if res.rrf is not None and len(res.rrf):
            r = np.asarray(res.rrf, float)
            items.append(dict(scans=scans, data=r, columns=['Qz', 'R/RF', 'd(R/RF)', 'dQz'][:r.shape[1]],
                              label='R/RF'))
        return kind, items
    if call.method == 'fluorescence':
        d = np.asarray(res.rows, float)
        cols = ['frame', 'Qz', 'energy', 'I', 'dI'] + (['I_xeray', 'dI_xeray'] if d.ndim == 2 and d.shape[1] >= 7 else [])
        fits = []
        lines = getattr(res, 'lines', None)
        if lines and lines.get('each'):                   # as the window saves Fit lines' fits
            fits = [('sum of %d spectra' % len(lines['each']), lines['ref'])] + \
                [('frame %d' % int(r[0]), f) for r, f in zip(res.rows, lines['each'])]
        return kind, [dict(scans=list(scans), data=d, columns=cols, label=label or res.command, fits=fits)]
    if call.method == 'gid':
        return kind, [dict(scans=list(scans), map_xyz=(res.x, res.y, res.data, res.err),
                           label=label or '2theta, beta (deg)')]
    if call.method == 'curve':
        return kind, [dict(scans=[res.scan], data=np.column_stack([res.x, res.y, res.err]), columns=list(res.columns),
                           label=label or res.label, fits=[(res.fit_label, res.fit)] if res.fit is not None else [])]
    if call.method == 'cut':
        # one item per cut, labelled as the window labels its curves ('S# 1 F# 0', 'summed cuts'); the window
        # saves them as '<curve>, <direction> <range>' and matches a remade item by that prefix (#145)
        direction = call.args[1] if len(call.args) > 1 else call.kwargs.get('direction', '')
        cols = [str(direction).split()[0] + ' x', 'I', 'dI'] if direction else ['x', 'I', 'dI']
        fits = getattr(res, 'fits', None)
        items = []
        for k, c in enumerate(res.cuts):
            lab = 'summed cuts' if res.summed_label is not None else str(res.labels[k]).replace('_', ' ')
            items.append(dict(scans=list(scans), data=np.asarray(c, float)[:, :3], columns=cols, label=lab,
                              fits=[(lab, fits[k])] if fits else []))
        return kind, items
    cols, arr = res.data()
    return kind, [dict(scans=[res.scan], data=arr, columns=cols, label=label or res.kind,
                       trends=list(res.trends.items()), time_axis=res.time)]


def with_scans(recipe, scans, points=None):
    """The recipe text with its reduction's scans replaced by ``scans`` and
    its point selection by ``points`` (None: none), for the remade
    result's own recipe."""
    tree = ast.parse(recipe)
    for st in tree.body:
        if (isinstance(st, ast.Assign) and isinstance(st.value, ast.Call)
                and isinstance(st.value.func, ast.Attribute) and st.value.func.attr in METHODS):
            if st.value.func.attr not in ONE_SCAN and st.value.args:
                st.value.args[0] = ast.parse(repr(sorted(int(s) for s in scans)), mode='eval').body
            st.value.keywords = [k for k in st.value.keywords if k.arg != 'points']
            if points is not None:
                if st.value.func.attr == 'burn':
                    p = points.get(int(ast.literal_eval(st.value.args[0])))
                else:
                    p = points
                if p is not None:
                    st.value.keywords.append(ast.keyword('points', ast.parse(repr(p), mode='eval').body))
    return ast.unparse(tree)
