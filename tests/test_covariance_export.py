"""The xmodfit covariance sidecar (lss_core.covariance_export): the hand-off's
acceptance tests (docs/handoff/19-lss-reader-covariance-contract.md §5) on
synthetic scans (tests/synthetic/xrr_scans.py), and the invariants of the
covariance under the transforms a reduction applies (docs/physics_notes.md
I10, I27, I28; design: docs/reports/downstream_covariance.md).

Hand-off test 5 asks for XModJointFit's ``tests/lss_reference.py`` as the
oracle; it has not been supplied (FEATURE_REQUESTS D13 note), so
``_oracle`` below is an independent implementation written from the
hand-off's text (§3.1–3.4) alone. Test 6 (loading in XModFit itself) needs
XModFit; ``lss_core.gls.problems`` / ``match_problems`` implement its §2.3
checks instead."""
import json
import math
import os
import warnings

import numpy as np
import pytest
from scipy.interpolate import interp1d

from lss_core import covariance_export as ce, gls, reflectivity as refl, uncertainty as unc
from synthetic import xrr, xrr_scans as xs

QC = 0.0217


def _reduced(plan='standard', seed=1, **kw):
    plans = {'standard': lambda: xs.standard_plan(4), 'nx': xs.nx_like_plan, 'back': xs.reaching_back_plan,
             'five': lambda: xs.standard_plan(5), 'staggered': lambda: xs.standard_plan(4, grid='staggered')}
    return xs.measure(xrr.film(25.0, 0.39, 3.5), plans[plan](), seed=seed, errors='counting+monitor', **kw)


def _oracle(scans):
    """Hand-off §3.1–3.4 written out from the text (corrected chain, no
    drops): merged x, y, σ_meas, W and per join fac, facerr_counting,
    χ²_red, facerr, δ, a_m; then Σ by the recursion, with explicit loops."""
    K = len(scans)
    x, y, sm = (np.array(v, float) for v in scans[0])
    W = np.zeros((len(x), K))
    W[:, 0] = 1
    rec = []

    def err_at(x2, s2, xo):
        v = interp1d(x2, s2, kind='cubic')(xo)
        bad = ~np.isfinite(v) | (v <= 0)
        v[bad] = np.interp(xo[bad], x2, s2)
        return v
    for m in range(1, K):
        x2, y2, s2 = (np.array(v, float) for v in scans[m])
        ov = x >= x2[0]
        xo = x[ov]
        f = interp1d(x2, y2, kind='cubic')(xo)
        fe = err_at(x2, s2, xo)
        r = y[ov] / f
        re = r * np.sqrt((sm[ov] / y[ov]) ** 2 + (fe / f) ** 2)
        w = 1 / re ** 2
        fac = np.sum(w * r) / np.sum(w)
        fc = np.sum(w) ** -0.5
        n = len(r)
        chi = np.sum(((r - fac) / re) ** 2) / (n - 1) if n >= 2 else 1.0
        facerr = fc * max(1.0, math.sqrt(chi))
        a = W[ov].mean(axis=0)
        rec.append(dict(fac=fac, fc=fc, chi=chi, facerr=facerr, delta=facerr / fac, a=a))
        e = np.zeros(K)
        e[m] = 1
        y2s, s2s = y2 * fac, s2 * fac
        yi = (y[ov] + interp1d(x2, y2s, kind='cubic')(xo)) / 2
        si = np.sqrt(sm[ov] ** 2 + err_at(x2, s2s, xo) ** 2) / 2
        Wi = 0.5 * W[ov] + 0.5 * e
        beyond = x2 > x[-1]
        x = np.concatenate([x[~ov], xo, x2[beyond]])
        y = np.concatenate([y[~ov], yi, y2s[beyond]])
        sm = np.concatenate([sm[~ov], si, s2s[beyond]])
        W = np.vstack([W[~ov], Wi, np.tile(e, (int(beyond.sum()), 1))])
    S = np.zeros((K, K))
    for m in range(1, K):
        a = rec[m - 1]['a']
        for j in range(m):
            S[m, j] = S[j, m] = sum(a[i] * S[i, j] for i in range(K))
        S[m, m] = sum(a[i] * S[i, l] * a[l] for i in range(K) for l in range(K)) + rec[m - 1]['delta'] ** 2
    return x, y, sm, W, S, rec


def _scans_of(r):
    return [tuple(r.per_scan[k][:, c] for c in range(3)) for k in r.order]


# ---- hand-off acceptance tests ----------------------------------------------------------------

@pytest.mark.parametrize('method', ['legacy', 'joint'])
@pytest.mark.parametrize('plan', ['standard', 'nx', 'back', 'five', 'staggered'])
def test_tracked_chain_reproduces_the_patch_bit_for_bit(plan, method):
    """Test 1 at the core: the tracked chain's data are reflectivity.patch's
    for the same method (the default joint fit, and the legacy fit), so
    the files written from them cannot change; with drops and with a
    known factor too."""
    r = _reduced(plan)
    cases = [dict(), dict(drops={0: [-1]}), dict(drops={0: [0, -1], 1: [[0], [-1]]}),
             dict(factors={1: (0.5, 0.005)})]
    for kw in cases:
        if plan == 'back' and 'factors' in kw:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            p = refl.patch(r.per_scan, r.order, method=method, **kw)
            t = ce.tracked_chain(r.per_scan, r.order, method=method, **kw)
        assert np.array_equal(p[:, :3], t.data, equal_nan=True), kw
        assert t.W.shape == (len(p), len(r.order)) and t.sigma_meas.shape == (len(p),)
        assert t.method == method


def test_joint_sigma_uses_the_counting_spread_of_the_fit_used():
    """The joint chain's Σ (``_joint_counting``): at the first join (the
    old curve is scan 1, whose error is counting only) the step error is
    the joint fit's own reported error; at later joins it is smaller than
    the fit's error against the folded curve's errors (which hold the
    earlier factors' errors, inherited through Σ instead), and a_m sums to 1."""
    r = _reduced('nx', seed=9)
    t = ce.joint_chain(r.per_scan, r.order)
    a, b = r.per_scan[r.order[0]][:, :3], r.per_scan[r.order[1]][:, :3]
    f, e, _ = refl.join_factor(a, b, 'joint')
    assert t.joins[0].fac == f
    assert t.joins[0].facerr == pytest.approx(e, rel=2e-3)      # sensitivity vs the fit's own covariance
    data = refl.patch({k: r.per_scan[k] for k in r.order[:2]}, r.order[:2], method='joint')
    f2, e2, _ = refl.join_factor(data[:, :3], r.per_scan[r.order[2]][:, :3], 'joint')
    assert t.joins[1].fac == f2
    assert t.joins[1].facerr_counting < e2
    for j in t.joins:
        assert j.a.sum() == pytest.approx(1.0, abs=1e-12)


@pytest.mark.parametrize('plan', ['standard', 'nx', 'back', 'staggered'])
def test_oracle_agrees_with_the_corrected_chain(plan):
    """Test 5: x and W exactly; the §3.2 values, δ, a_m, Σ, σ_meas and y to
    1e-10 relative."""
    r = _reduced(plan, seed=3)
    x, y, sm, W, S, rec = _oracle(_scans_of(r))
    c = ce.corrected_chain(r.per_scan, r.order)
    assert np.array_equal(c.data[:, 0], x)
    assert np.array_equal(c.W, W)
    assert np.allclose(c.data[:, 1], y, rtol=1e-10, atol=0)
    assert np.allclose(c.sigma_meas, sm, rtol=1e-10, atol=0)
    for j, o in zip(c.joins, rec):
        assert j.fac == pytest.approx(o['fac'], rel=1e-10)
        assert j.facerr_counting == pytest.approx(o['fc'], rel=1e-10)
        assert j.chi2_red == pytest.approx(o['chi'], rel=1e-10)
        assert j.facerr == pytest.approx(o['facerr'], rel=1e-10)
        assert np.allclose(j.a, o['a'], rtol=1e-10, atol=1e-15)
    assert np.allclose(c.Sigma, S, rtol=1e-10, atol=1e-18)


@pytest.mark.parametrize('method', ['legacy', 'corrected', 'joint'])
@pytest.mark.parametrize('plan', ['standard', 'back', 'five'])
def test_weights_sigma_and_total_error(plan, method):
    """Tests 2–4 and invariant I10: W rows sum to 1, simple-chain overlap rows
    exactly 0.5/0.5; Σ symmetric, PSD, anchor row and column zero; a simple
    chain is a random walk (diag = cumulative δ², Σ[k, l] = Σ[min, min]),
    otherwise the §3.4 recursion; σ_total ≥ σ_meas, equal on scan 1's points
    outside the overlap."""
    r = _reduced(plan, seed=5)
    t = getattr(ce, method + '_chain')(r.per_scan, r.order)
    W, S = t.W, t.Sigma
    assert np.allclose(W.sum(axis=1), 1.0, rtol=0, atol=1e-15)
    assert np.all(t.sigma_meas > 0)
    assert np.allclose(S, S.T, rtol=0, atol=0)
    assert np.linalg.eigvalsh(S).min() >= -1e-12 * np.abs(S).max()
    assert np.all(S[0] == 0) and np.all(S[:, 0] == 0)
    d2 = np.array([j.facerr / j.fac for j in t.joins]) ** 2
    one_hot = all(np.count_nonzero(j.a) == 1 for j in t.joins)
    if one_hot:
        assert set(np.unique(W[(W > 0).sum(axis=1) > 1])) <= {0.0, 0.5}
        assert np.allclose(np.diag(S)[1:], np.cumsum(d2), rtol=1e-12)
        for k in range(len(S)):
            for l in range(len(S)):
                assert S[k, l] == pytest.approx(S[min(k, l), min(k, l)], rel=1e-12, abs=1e-20)
    else:
        assert plan == 'back' or method == 'joint'
        assert np.allclose(S, unc.chain_covariance([j.a for j in t.joins], np.sqrt(d2)), rtol=1e-12)
    cd = t.covdata('total')
    tot = cd.sigma_total()
    assert np.all(tot >= cd.sigma_meas)
    only_first = W[:, 0] == 1.0
    assert np.array_equal(tot[only_first], cd.sigma_meas[only_first])
    assert np.all(tot[~only_first] > cd.sigma_meas[~only_first])


def _write(tmp_path, res, layout, method=None, combined=False):
    name = str(tmp_path / ('%s_%s' % (layout, method)))
    paths = res.save(name, covariance=layout, method=method, combined=combined)
    return name, paths


def _result(r, qoff=0.0, norm_factor=None, rrf=True, drops=None, factors=None, method='joint'):
    """An Experiment ReflectivityResult made from synthetic reduced scans
    (the script's code path: reflectivity.patch, then finish)."""
    from lss_core.experiment import ReflectivityResult
    patched = refl.patch(r.per_scan, r.order, drops, factors, method=method)
    ref, out_rrf = refl.finish(patched[:, :3], QC, qoff, norm_factor, rrf)
    return ReflectivityResult(r.per_scan, r.order, patched, ref, out_rrf, [], method, [],
                              dict(qc=QC, qoff=qoff, norm_factor=norm_factor, rrf=rrf, drops=drops, factors=factors,
                                   method=method))


@pytest.mark.parametrize('kw', [dict(), dict(drops={0: [-1], 1: [0]}), dict(norm_factor=2.5), dict(qoff=0.0005),
                                dict(rrf=False)])
@pytest.mark.parametrize('patch', ['joint', 'legacy'])
@pytest.mark.parametrize('layout,method', [('sidecar', None), ('contract', None), ('contract', 'corrected'),
                                           ('contract', 'stitched')])
def test_written_sidecars_load_and_match_their_files(tmp_path, kw, patch, layout, method):
    """Test 6 (as XModFit checks, §2.3) and test 2 for both layouts; test 1:
    'sidecar' leaves the patch's own files byte for byte; 'contract' writes
    the legacy patch's files as <name>_ref_legacy.txt, byte for byte."""
    if method == 'stitched' and kw.get('drops'):
        kw = dict(drops={0: [0], 1: [0]})         # the stitched output takes drops of single scans only
    r = _reduced('nx', seed=7)
    res = _result(r, method=patch, **kw)
    name = str(tmp_path / ('%s_%s' % (layout, method)))
    res.save(name, covariance=layout, method=method)
    plain = str(tmp_path / 'plain')
    res.save(plain)
    legacy = str(tmp_path / 'legacy')
    _result(r, method='legacy', **kw).save(legacy)
    for kind in ('ref', 'rrf'):
        txt = '%s_%s.txt' % (name, kind)
        if kind == 'rrf' and not kw.get('rrf', True):
            assert not os.path.exists(txt) and not os.path.exists(txt[:-4] + '.cov.json')
            continue
        if layout == 'sidecar':
            with open('%s_%s.txt' % (plain, kind), 'rb') as f, open(txt, 'rb') as g:
                assert g.read() == f.read()
        else:
            with open('%s_%s.txt' % (legacy, kind), 'rb') as f, open('%s_%s_legacy.txt' % (name, kind), 'rb') as g:
                assert g.read() == f.read()
        sc = gls.load(txt[:-4] + '.cov.json')
        d = np.loadtxt(txt)
        assert not sc.match_problems(d[:, 0], d[:, 1])
        with open(txt[:-4] + '.cov.json') as f:
            raw = json.load(f)
        assert raw['format'] == 'xmodfit-covariance' and raw['version'] == 1
        assert raw['data_file'] == os.path.basename(txt)
        t = sc.term('stitch')
        assert t.scope == 'dataset' and t.kind == 'multiplicative' and len(t.labels) == len(r.order)
        assert t.labels == ['S%d' % k for k in r.order]
        if layout == 'contract':          # test 2: the error column is √diag C, to the file's rounding
            tot = np.sqrt(sc.sigma_meas ** 2 + sc.y ** 2 * np.einsum('ik,kl,il->i', t.weights, t.cov, t.weights))
            assert np.allclose(d[:, 2], tot, rtol=1e-4, atol=0)
            assert np.all(d[:, 2] >= sc.sigma_meas * (1 - 1e-4))
    if layout == 'sidecar' and kw.get('rrf', True):     # x of _rrf is q + qoff, of _ref q (trap T8 note)
        a, b = gls.load(name + '_ref.cov.json'), gls.load(name + '_rrf.cov.json')
        assert np.sort(b.x) - np.sort(a.x) == pytest.approx(kw.get('qoff', 0.0), abs=1e-15)
        assert np.array_equal(a.term('stitch').cov, b.term('stitch').cov)


def test_the_two_sidecars_of_one_reduction_share_the_stitch_term(tmp_path):
    r = _reduced('nx', seed=2)
    name, _ = _write(tmp_path, _result(r, qoff=0.0003), 'contract', None)
    a, b = gls.load(name + '_ref.cov.json'), gls.load(name + '_rrf.cov.json')
    ta, tb = a.term('stitch'), b.term('stitch')
    assert np.array_equal(ta.cov, tb.cov)
    o = np.argsort(b.x)                       # _rrf is in patch order, _ref sorted
    assert np.array_equal(ta.weights, tb.weights[o])


def test_combined_file_has_the_data_block(tmp_path):
    r = _reduced('standard')
    name, paths = _write(tmp_path, _result(r), 'contract', None, combined=True)
    with open(name + '_ref.json') as f:
        d = json.load(f)
    assert d['data']['columns'] == {'Qz': 'x', 'R': 'y', 'R_err': 'yerr'}
    assert len(d['data']['yerr']) == len(d['x'])
    assert not gls.problems(d)
    txt = np.loadtxt(name + '_ref.txt')
    assert np.allclose(np.array(d['data']['yerr']), txt[:, 2], rtol=1e-4, atol=0)


def test_single_scan_has_no_stitch_term(tmp_path):
    """§3.5 and invariant I27: one scan, Σ = 0, terms [] and σ_total = σ_meas."""
    r = _reduced('standard')
    one = {r.order[0]: r.per_scan[r.order[0]]}
    t = ce.legacy_chain(one, [r.order[0]])
    assert t.Sigma.shape == (1, 1) and t.Sigma[0, 0] == 0
    cd = t.covdata('total')
    assert np.array_equal(cd.sigma_total(), cd.sigma_meas)
    d = ce.sidecar_dict(cd)
    assert d['terms'] == [] and not gls.problems(d)


def test_sidecar_from_a_failed_join_is_refused():
    """§3.5: no partial or broken sidecar (a NaN anywhere is refused)."""
    r = _reduced('standard')
    cd = ce.legacy_chain(r.per_scan, r.order).covdata()
    cd.sigma_meas[3] = np.nan
    with pytest.raises(ValueError, match='sigma_meas'):
        ce.sidecar_dict(cd)


def test_validator_refuses_what_xmodfit_refuses():
    r = _reduced('standard')
    good = ce.sidecar_dict(ce.legacy_chain(r.per_scan, r.order).covdata())
    assert gls.problems(good) == []

    def bad(change):
        d = json.loads(json.dumps(good))
        change(d)
        return gls.problems(d)
    assert bad(lambda d: d.update(version=2))
    assert bad(lambda d: d.update(format='other'))
    assert bad(lambda d: d['sigma_meas'].__setitem__(0, 0.0))
    assert bad(lambda d: d['terms'][0]['weights'].pop())
    assert bad(lambda d: d['terms'][0]['cov'][1].__setitem__(2, 1.0))           # not symmetric
    assert bad(lambda d: d['terms'][0]['cov'].__setitem__(1, [0.0, -1.0, 0.0, 0.0]))
    assert bad(lambda d: d['terms'].append(dict(d['terms'][0])))             # duplicate name
    assert bad(lambda d: d['terms'][0]['labels'].pop())
    assert not bad(lambda d: d.update(unknown_key=[1, 2, 3]))               # §2.6: unknown keys are ignored
    with pytest.raises(ValueError, match='refused'):
        gls.load(dict(good, version=2))


@pytest.mark.parametrize('method', ['corrected', 'legacy', 'joint'])
def test_statistical_sanity_of_sigma(method):
    """Test 7: over noise seeds the spread of ln(factor) of scan m about the
    truth agrees with √Σ_mm. 300 seeds; the SD of an SD from 300 draws is
    ≈ 4 %. Measured (2026-11-22, the owner's monitor model): √Σ / spread
    1.08–1.11 for the §3.2 chain and the legacy factors (inflate-only, as
    XModJointFit's 6–17 % above), 0.88–0.95 for the joint fit, whose first
    join's own error is ≈ 12 % small on these scans (its pull SD 1.13, the
    same with reflectivity.join_factor's reported error)."""
    bl = xs.Beamline(**xs.REAL_MONITOR)
    errs, sig = [], []
    for seed in range(300):
        r = xs.measure(xrr.film(25.0, 0.39, 3.5), xs.nx_like_plan(), beamline=bl, seed=seed, errors='counting+monitor')
        truth = r.true_join_factors()
        c = getattr(ce, method + '_chain')(r.per_scan, r.order)
        errs.append([math.log(j.fac / truth[i]) for i, j in enumerate(c.joins)])
        sig.append(np.sqrt(np.diag(c.Sigma)[1:]))
    errs, sig = np.array(errs), np.array(sig)
    ratio = np.sqrt(np.mean(sig ** 2, axis=0)) / errs.std(axis=0, ddof=1)
    assert np.all(np.abs(errs.mean(axis=0)) < 3 * errs.std(axis=0) / math.sqrt(len(errs)) + 2e-4)
    lo = 0.8 if method == 'joint' else 0.92
    assert np.all((ratio > lo) & (ratio < 1.3)), ratio
    pull = errs / sig
    assert np.all((pull.std(axis=0) > 0.75) & (pull.std(axis=0) < 1.2)), pull.std(axis=0)


# ---- transforms commute with the covariance (invariant I28) -------------------------------------

def _cd(plan='back'):
    r = _reduced(plan, seed=11)
    return ce.corrected_chain(r.per_scan, r.order).covdata('total')


def test_permutation_and_removal_select_rows_and_columns_of_C():
    cd = _cd()
    C = cd.covariance('log')
    rng = np.random.default_rng(0)
    idx = rng.permutation(cd.n)[: cd.n - 5]
    sub = cd.take(idx)
    assert np.allclose(sub.covariance('log'), C[np.ix_(idx, idx)], rtol=1e-14, atol=0)
    cut = cd.cut(0.03, 0.12)
    keep = np.flatnonzero((cd.x >= 0.03) & (cd.x <= 0.12))
    assert np.allclose(cut.covariance('log'), C[np.ix_(keep, keep)], rtol=1e-14, atol=0)
    assert np.all(np.diff(cd.take(rng.permutation(cd.n)).sort().x) >= 0)


def test_scaling_leaves_log_C_and_scales_linear_C():
    """Normalisation and Fresnel division (and the Qz offset, which moves x
    only): C_log unchanged, C_lin → D⁻¹ C_lin D⁻¹."""
    cd = _cd()
    f = 1.0 / (1.0 + cd.x ** 2)
    s = cd.scale(3.0).divide(f).shift_x(0.001)
    assert np.allclose(s.covariance('log'), cd.covariance('log'), rtol=1e-13, atol=0)
    D = 1.0 / (3.0 * f)
    assert np.allclose(s.covariance('linear'), D[:, None] * cd.covariance('linear') * D[None, :], rtol=1e-12, atol=0)
    assert np.allclose(s.sigma_total(), cd.sigma_total() * D, rtol=1e-13)
    assert np.allclose(s.x, cd.x + 0.001)


def test_finish_matches_the_reflectivity_finish_and_keeps_the_covariance():
    r = _reduced('nx', seed=4)
    t = ce.legacy_chain(r.per_scan, r.order)
    for kw in (dict(), dict(qoff=0.0005), dict(norm_factor=2.0)):
        ref, rrf = ce.finish(t.covdata('legacy'), QC, kw.get('qoff', 0.0), kw.get('norm_factor'), True)
        R, F = refl.finish(t.data, QC, kw.get('qoff', 0.0), kw.get('norm_factor'), True)
        assert np.array_equal(ref.array(), R) and np.array_equal(rrf.array(), F)
        perm = np.argsort(t.data[:, 0])
        C0 = t.covdata('legacy').covariance('log')
        assert np.allclose(ref.covariance('log'), C0[np.ix_(perm, perm)], rtol=1e-12, atol=0)
        assert np.allclose(rrf.covariance('log'), C0, rtol=1e-12, atol=0)
        assert ref.provenance['norm'] > 0 and 0 < ref.provenance['norm_rel_err'] < 0.05


def test_average_is_the_linearised_combination():
    """Binning: the W row of an average is Σ_j (w_j y_j/ȳ) W_j, so the log
    covariance of the average agrees with the exact (Monte Carlo) one to
    first order, rows still summing to 1."""
    cd = _cd()
    groups = [list(range(i, min(i + 3, cd.n))) for i in range(0, cd.n, 3)]
    av = cd.average(groups)
    assert np.allclose(av.W.sum(axis=1), 1.0, atol=1e-14)
    rng = np.random.default_rng(1)
    L = np.linalg.cholesky(cd.Sigma[1:, 1:])
    phis = np.zeros((4000, cd.k))
    phis[:, 1:] = rng.standard_normal((4000, cd.k - 1)) @ L.T
    ys = cd.y[None, :] * np.exp(phis @ cd.W.T)          # scale errors only
    w = [1 / cd.sigma_meas[g] ** 2 / np.sum(1 / cd.sigma_meas[g] ** 2) for g in groups]
    yb = np.column_stack([ys[:, g] @ wj for g, wj in zip(groups, w)])
    emp = np.cov(np.log(yb), rowvar=False)
    pred = av.W @ cd.Sigma @ av.W.T
    assert np.allclose(emp, pred, rtol=0.1, atol=0.05 * pred.max())


def test_concat_adds_the_link_to_every_scan_of_the_second_set():
    a, b = _cd('standard'), _cd('back')
    b = ce.CovData(b.x + 1, b.y, b.sigma_meas, b.W, b.Sigma, ['T%d' % i for i in range(b.k)])
    j = a.concat(b, link_error=0.01)
    k1 = a.k
    assert np.allclose(j.Sigma[:k1, :k1], a.Sigma)
    assert np.allclose(j.Sigma[k1:, k1:], b.Sigma + (a.Sigma[-1, -1] + 1e-4))
    assert np.allclose(j.Sigma[:k1, k1:], a.Sigma[:, [-1]])
    assert np.linalg.eigvalsh(j.Sigma).min() > -1e-14
    with pytest.raises(ValueError, match='share scans'):
        a.concat(a, 0.01)


def test_error_interpolation_falls_back_to_linear_where_the_cubic_is_not_positive():
    """Hand-off §3.1: a cubic interpolant of an error column can dip below
    zero next to a sharp change; there the linear value is used and the
    point is listed (XModFit refuses σ_meas ≤ 0). Review 2026-11-24: the
    fallback had no test of its own."""
    x2 = np.arange(6.0)
    s2 = np.array([1.0, 1e-3, 1e-3, 1e-3, 1e-3, 1.0])
    x = np.array([0.5, 1.5, 2.5, 3.5, 4.5])
    cubic = interp1d(x2, s2, kind='cubic')(x)
    assert np.any(cubic <= 0)
    v, fb = ce._interp_error(x2, s2, x)
    assert fb == [int(i) for i in np.flatnonzero(cubic <= 0)]
    assert np.all(v > 0)
    assert np.array_equal(v[fb], np.interp(x[fb], x2, s2))
    keep = np.setdiff1d(np.arange(len(x)), fb)
    assert np.array_equal(v[keep], cubic[keep])


@pytest.mark.parametrize('kw', [dict(mask=[(1, 8)]), dict(mask=[(2, 0)], method='legacy')])
def test_masked_reduction_gets_a_matching_sidecar(dataset, tmp_path, kw):
    """F92 (points left out by a mask, 2026-11-23): the replay starts from
    the masked scans the result holds, so the sidecar matches the files."""
    from lss_core.experiment import Experiment
    res = Experiment(dataset).reflectivity([1, 2], **kw)
    assert res.masked
    name = str(tmp_path / 'm')
    res.save(name, covariance='sidecar')
    plain = str(tmp_path / 'p')
    res.save(plain)
    for kind in ('ref', 'rrf'):
        with open('%s_%s.txt' % (name, kind), 'rb') as f, open('%s_%s.txt' % (plain, kind), 'rb') as g:
            assert f.read() == g.read()
        sc = gls.load('%s_%s.cov.json' % (name, kind))
        d = np.loadtxt('%s_%s.txt' % (name, kind))
        assert not sc.match_problems(d[:, 0], d[:, 1])
