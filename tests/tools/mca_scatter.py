"""The scattered beam in real MCA spectra (DATA_NEEDS row 3, F90): fit a measured spectrum with the
synthetic generator's own physics (``tests/synthetic/mca.py``) and every uncertain axis free, and
draw the study's figures (``docs/studies/mca_scatter/summary.md``).

    python tests/tools/mca_scatter.py --out docs/studies/mca_scatter

The figures come from public files only:
* ``scatter_fits.csv``: the anonymised table of fitted numbers, made by the owner's non-cloud agent
  from the private spectra with this module's model;
* ``quantities.csv``: every quantity per example in long form, including the P1 check on real
  series.

S1 (example spectra, refitted) runs only on a folder of example spectra named with ``--fixtures``
(``energy_keV,counts`` CSV files). None are committed: a scrubbed spectrum is published only with
the owner's yes. Until then S1 is a private figure.

The model, over E0 − 2.4 to E0 + 0.6 keV, by Poisson maximum likelihood (deviance residuals):

* A elastic (Rayleigh) photons at the beam energy E0;
* R·A Compton photons from water's shells (``mca.shell_compton``, the 'shells' model of study B)
  at a free scattering angle 2θ, the O 1s part × ``core`` (1: water's impulse-approximation wing)
  and every momentum width × ``doppler`` (which also takes the detector's spread of angles);
* every photon through the generator's detector (``mca._response``): Gaussian photopeak with
  FWHM² = noise² + 8 ln2 ε F E (``noise`` free, Fano 0.115), low-energy exponential tail
  (``tail``, ``tail_slope``), shelf (``shelf``) and Si K escape (``escape`` × Reed's fraction);
* plus what the generator lacks: a **high-energy exponential tail** (``rtail``, ``rtail_slope``:
  pile-up and count-rate effects, seen on every readout at high rates);
* nuisance K (and a few L) lines of elements whose lines fall in the region, each a Kα + Kβ
  photopeak (Kβ/Kα 0.15) through the same response, amplitude ≥ 0;
* a flat background ``bg0`` (no slope: a slope stood in for the missing high-energy tail);
* the calibration's offset free (the gain comes from the elastic line across beam energies or from
  the elastic line and Ar Kα, done before the fit).

Uncertainties: the inverse of JᵀJ of the deviance residuals, scaled by √(deviance/dof) when that
exceeds 1 (the model is not exact at 10⁶ counts per channel).
"""
import argparse
import csv
import json
import math
import os
import sys

import numpy as np
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                  # tests/
from synthetic import mca                                  # noqa: E402

# candidate K lines (keV): Ka (weighted), Kb, K edge  -- X-ray Data Booklet values (from memory)
KLINES = {
    'Ar': (2.957, 3.190, 3.206), 'K': (3.313, 3.590, 3.608), 'Ca': (3.691, 4.013, 4.038),
    'Ti': (4.509, 4.932, 4.966), 'Cr': (5.411, 5.947, 5.989), 'Mn': (5.895, 6.490, 6.539),
    'Fe': (6.400, 7.058, 7.112), 'Co': (6.925, 7.649, 7.709), 'Ni': (7.472, 8.265, 8.333),
    'Cu': (8.041, 8.905, 8.979), 'Zn': (8.631, 9.572, 9.659), 'Ga': (9.243, 10.264, 10.367),
    'Ge': (9.876, 10.982, 11.103), 'As': (10.532, 11.726, 11.867), 'Se': (11.209, 12.496, 12.658),
    'Br': (11.909, 13.291, 13.474), 'Rb': (13.375, 14.961, 15.200), 'Sr': (14.142, 15.836, 16.105),
}
# L lines that turn up (Pb, Hg, Au, W): La, Lb1, L3 edge
LLINES = {'Pb': (10.551, 12.614, 13.035), 'Au': (9.713, 11.442, 11.919), 'Hg': (9.989, 11.823, 12.284),
          'W': (8.398, 9.672, 10.207), 'Pt': (9.442, 11.071, 11.564)}

PNAMES = ['logA', 'logR', 'angle', 'core', 'doppler', 'noise', 'escape', 'tail', 'tail_slope', 'shelf',
          'bg0', 'bg1', 'offset', 'rtail', 'rtail_slope']


def energy_axis(calib, nch):
    a, b, q = calib
    if abs(b) > 0.5:                       # eV per channel
        a, b, q = a / 1000.0, b / 1000.0, q / 1000.0
    return (a, b, q)


def _rtail(edges, e, n, det, frac, slope):
    """High-energy exponential tail (mirror of mca's low-energy one): pile-up and ballistic effects at
    high count rates, which the generator does not model."""
    from scipy.special import erfc, erfcx
    e = np.atleast_1d(np.asarray(e, float))[:, None]
    n = np.atleast_1d(np.asarray(n, float))[:, None]
    lo, hi = edges[None, :-1], edges[None, 1:]
    mid, width = 0.5 * (lo + hi), hi - lo
    sig = np.array([det.fwhm(v) for v in e[:, 0]])[:, None] / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    b = slope
    z = ((e - mid) / sig + sig / b) / math.sqrt(2)
    a = (e - mid) / b + sig ** 2 / (2 * b ** 2)
    with np.errstate(over='ignore', invalid='ignore'):
        t = np.where(z > 0, np.exp(a - z ** 2) * erfcx(np.maximum(z, 0)), np.exp(np.minimum(a, 700)) * erfc(z))
    return np.sum(n * frac * t / (2 * b) * width, axis=0)


class ScatterModel:
    def __init__(self, counts, calib_kev, e0, lo=2.4, hi=0.6, lines=None, de=0.01, fix=None):
        self.e0 = float(e0)
        self.calib = calib_kev
        a, b, q = calib_kev
        ch = np.arange(1, len(counts) + 1, dtype=float)
        e = a + b * ch + q * ch ** 2
        self.sel = np.where((e > self.e0 - lo) & (e < self.e0 + hi))[0]
        self.ch = ch[self.sel]
        self.n = np.asarray(counts, float)[self.sel]
        self.de = de
        reg_lo, reg_hi = self.e0 - lo - 0.2, self.e0 + hi + 0.2
        cand = []
        for el, (ka, kb, edge) in KLINES.items():
            if edge < self.e0 and ((reg_lo < ka < reg_hi) or (reg_lo < kb < reg_hi) or (reg_lo < ka - mca.SI_KA_KEV < reg_hi)):
                cand.append((el, ka, kb))
        for el, (la, lb, edge) in LLINES.items():
            if edge < self.e0 and ((reg_lo < la < reg_hi) or (reg_lo < lb < reg_hi)):
                cand.append((el + 'L', la, lb))
        self.lines = cand if lines is None else lines
        self.fix = {'bg1': 0.0}
        self.fix.update(fix or {})
        self.names = PNAMES + ['line_' + c[0] for c in self.lines]

    def edges(self, offset):
        a, b, q = self.calib
        c = np.concatenate([self.ch - 0.5, [self.ch[-1] + 0.5]])
        return (a + offset) + b * c + q * c ** 2

    def parts(self, p):
        P = dict(zip(self.names, p))
        P.update(self.fix)
        det = mca.Detector(noise=P['noise'], tail=P['tail'], tail_slope=P['tail_slope'], shelf=P['shelf'],
                           escape=P['escape'])
        edges = self.edges(P['offset'])
        out = {}

        def resp(name, e, nn):
            acc = {k: np.zeros(len(self.ch)) for k in ('peak', 'tail', 'shelf', 'escape')}
            mca._response(edges, e, nn, det, acc)
            if P['rtail'] > 0:
                acc['rtail'] = _rtail(edges, e, nn, det, P['rtail'], P['rtail_slope'])
                acc['peak'] = acc['peak'] * (1.0 - P['rtail'])
            out[name] = acc

        A = math.exp(P['logA'])
        resp('elastic', [self.e0], [A])
        beam = mca.Beam(energy=self.e0, angle=P['angle'], compton_model='shells', core_scale=1.0,
                        doppler_scale=P['doppler'])
        ec = beam.compton
        e1 = np.arange(ec - 3.0, min(ec + 1.0, self.e0), self.de)
        val, core = fast_shell_compton(beam, e1)
        nc = A * math.exp(P['logR'])
        w = nc * (val + P['core'] * core) * self.de
        resp('compton', e1, w)
        for (el, ka, kb) in self.lines:
            amp = P['line_' + el]
            if amp > 0:
                resp('line ' + el, [ka, kb], [amp, amp * 0.15])
        mid = 0.5 * (edges[:-1] + edges[1:])
        bg = np.clip(P['bg0'] + P['bg1'] * (mid - self.e0), 0, None)
        out['background'] = {'flat': bg}
        return out

    def mu(self, p):
        tot = np.zeros(len(self.ch))
        for d in self.parts(p).values():
            for v in d.values():
                tot += v
        return np.maximum(tot, 1e-9)

    def resid(self, p):
        mu = self.mu(p)
        n = self.n
        with np.errstate(divide='ignore', invalid='ignore'):
            t = np.where(n > 0, n * np.log(n / mu), 0.0)
        dev = 2 * (mu - n + t)
        return np.sign(n - mu) * np.sqrt(np.maximum(dev, 0))

    def start(self):
        n = self.n
        a, b, q = self.calib
        e = a + b * self.ch
        top = (e > self.e0 - 0.15) & (e < self.e0 + 0.15)
        A = max(n[top].sum(), 10.0)
        bg = max(np.percentile(n, 10), 0.1)
        p = [math.log(A), math.log(1.0), 95.0, 1.0, 1.0, 0.12, 1.0, 0.01, 0.15, 2e-3, bg, 0.0, 0.0, 0.01, 0.1]
        p += [10.0] * len(self.lines)
        lo = [math.log(A) - 6, math.log(0.01), 30.0, 0.0, 0.3, 0.03, 0.0, 0.0, 0.02, 0.0, 0.0, -1e5, -0.15, 0.0, 0.01]
        hi = [math.log(A) + 6, math.log(100.0), 175.0, 5.0, 3.0, 0.5, 20.0, 0.3, 1.5, 0.05, 1e6, 1e5, 0.15, 0.3, 1.0]
        lo += [0.0] * len(self.lines)
        hi += [1e12] * len(self.lines)
        return np.array(p, float), np.array(lo, float), np.array(hi, float)

    def fit(self, p0=None):
        p, lo, hi = self.start()
        if p0 is not None:
            p = np.clip(p0, lo, hi)
        free = [i for i, k in enumerate(self.names) if k not in self.fix]
        pf = p.copy()

        def r(x):
            q = pf.copy()
            q[free] = x
            return self.resid(q)
        best = None
        for angle0 in ([p[2]] if p0 is not None else [70.0, 95.0, 120.0]):
            x0 = p[free].copy()
            if 'angle' not in self.fix:
                x0[free.index(2)] = angle0
            sol = least_squares(r, x0, bounds=(lo[free], hi[free]), x_scale='jac', max_nfev=400)
            if best is None or sol.cost < best.cost:
                best = sol
        pf[free] = best.x
        J = best.jac
        try:
            cov = np.linalg.pinv(J.T @ J)
            err = np.sqrt(np.clip(np.diag(cov), 0, None))
        except np.linalg.LinAlgError:
            err = np.full(len(free), np.nan)
        perr = np.full(len(pf), np.nan)
        perr[free] = err
        dev = float(np.sum(self.resid(pf) ** 2))
        dof = len(self.n) - len(free)
        return pf, perr, dev, dof


# ---- speed: cached hydrogenic profiles (same mathematics as mca.hydrogenic_profile) ----
_PROF = {}


def _profile_table(orbital, z):
    k = (orbital, z)
    if k not in _PROF:
        n = {'1s': 1, '2s': 2, '2p': 2}[orbital]
        p0 = z / n
        p = np.linspace(0.0, 40.0 * p0, 20001)
        _PROF[k] = (p, mca.hydrogenic_profile(p, orbital, z))
    return _PROF[k]


def fast_shell_compton(beam, e1):
    e1 = np.asarray(e1, float)
    pz = mca.compton_pz(beam.energy, e1, beam.angle)
    dpz = np.abs(np.gradient(pz, e1))
    total = sum(n for _, n, _, _, _ in mca.WATER_SHELLS)
    val, core = np.zeros_like(e1), np.zeros_like(e1)
    lam = beam.doppler_scale
    for name, n, orb, z, b in mca.WATER_SHELLS:
        p, j = _profile_table(orb, z)
        jj = np.interp(np.abs(pz / lam), p, j, right=0.0) / lam
        w = (n / total) * jj * dpz * (beam.energy - e1 > b)
        if name == 'O 1s':
            core += beam.core_scale * w
        else:
            val += w
    return val, core



# ------------------------------------------------------------------ helpers for the study
GENERATOR_HARD = dict(noise=0.12, escape=1.0, tail=0.01, tail_slope=0.15, shelf=2e-3, rtail=0.0, rtail_slope=0.1,
                      core=1.0, doppler=1.0, bg0=0.0)    # study B's hard case (mca_fit_gauntlet.HARD_DET, 'shells')


def fit_errors_scaled(perr, dev, dof):
    """Statistical errors scaled by √(deviance/dof) when the model is worse than Poisson."""
    return perr * math.sqrt(max(1.0, dev / max(dof, 1)))


def rebin_shift(counts, a, b, shift):
    """Counts moved by ``shift`` keV on the same channel grid (cumulative-count interpolation): how
    pre-edge points of an energy scan at slightly different beam energies are aligned and summed."""
    n = len(counts)
    edges = a + b * (np.arange(n + 1) + 0.5)
    cum = np.concatenate([[0], np.cumsum(counts)])
    return np.diff(np.interp(edges - shift, edges, cum))


def escape_template(e, n, e0, window=(0.55, 0.35)):
    """Model-free Si escape fraction: around E0 − 1.740 keV, n(E) = f·n(E + 1.740) + quadratic, the
    parent taken from the measured spectrum itself (P3's picture, ``fluorescence.strip_escape``).
    Returns (f, its error, χ²/dof)."""
    ce = e0 - mca.SI_KA_KEV
    w = (e > ce - window[0]) & (e < ce + window[1])
    T = np.interp(e[w] + mca.SI_KA_KEV, e, n)
    x = e[w] - ce
    A = np.vstack([T, np.ones_like(x), x, x ** 2]).T
    wt = 1.0 / np.sqrt(np.maximum(n[w], 1.0))
    coef, *_ = np.linalg.lstsq(A * wt[:, None], n[w] * wt, rcond=None)
    cov = np.linalg.pinv((A * wt[:, None]).T @ (A * wt[:, None]))
    chi = float(np.sum(((n[w] - A @ coef) * wt) ** 2) / max(1, w.sum() - 4))
    return float(coef[0]), float(math.sqrt(cov[0, 0] * max(chi, 1.0))), chi


def band_numbers(sm, p):
    """Counts per parent photon per keV in the band under a line, E0 − 1.55 keV to the Compton peak −
    0.35 keV, after the fitted lines and flat background: the data's and the generator's hard case's
    (same photons, angle and offset)."""
    P = dict(zip(sm.names, p)); P.update(sm.fix)
    edges = sm.edges(P['offset']); mid = 0.5 * (edges[:-1] + edges[1:])
    parts = sm.parts(p)
    lines = sum((sum(v.values()) for k, v in parts.items() if k.startswith('line')), np.zeros(len(mid)))
    bg = parts['background']['flat']
    atot = math.exp(P['logA']) * (1 + math.exp(P['logR']))
    ec = mca.compton_energy(sm.e0, P['angle'])
    lo, hi = sm.e0 - 1.55, ec - 0.35
    band = (mid > lo) & (mid < hi)
    pg = generator_vector(sm, p)
    data = float((sm.n - lines - bg)[band].sum()) / atot / (hi - lo)
    gen = float(sm.mu(pg)[band].sum()) / atot / (hi - lo)
    return data, gen, (lo, hi)


def generator_vector(sm, p):
    """The fitted parameters with the generator's hard-case detector and Compton (no lines, no background)."""
    pg = np.array(p, float).copy()
    for k, v in GENERATOR_HARD.items():
        if k in sm.names:
            pg[sm.names.index(k)] = v
    for k in sm.names:
        if k.startswith('line_'):
            pg[sm.names.index(k)] = 0.0
    return pg


def read_fixture(path):
    """(meta comment, energy keV, counts) of an anonymised example spectrum."""
    with open(path, encoding='utf-8') as fh:
        head = fh.readline().strip()
        rows = list(csv.DictReader(fh))
    e = np.array([float(r['energy_keV']) for r in rows])
    n = np.array([float(r['counts']) for r in rows])
    return head, e, n


def fit_fixture(path, e0=10.0):
    """Refit an example spectrum (its energy axis is already calibrated: gain from the file, offset
    fitted again)."""
    head, e, n = read_fixture(path)
    b = float(np.median(np.diff(e)))
    a = e[0] - b                                        # channel 1 at e[0]
    sm = ScatterModel(n, (a, b, 0.0), e0)
    p, perr, dev, dof = sm.fit()
    return dict(path=path, head=head, energy=e, counts=n, sm=sm, p=p, perr=fit_errors_scaled(perr, dev, dof),
                dev=dev, dof=dof)


def _fit_worker(path):
    r = fit_fixture(path)
    return {k: r[k] for k in ('path', 'p', 'perr', 'dev', 'dof')}


# ------------------------------------------------------------------ figures
def _read_table(path):
    with open(path, encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float('nan')


def figure_examples(fits, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    k = len(fits)
    fig, axs = plt.subplots(3, k, figsize=(4.6 * k, 9.6), gridspec_kw=dict(height_ratios=[3.2, 1.1, 1.6]),
                            squeeze=False)
    for j, r in enumerate(fits):
        sm, p = r['sm'], r['p']
        P = dict(zip(sm.names, p)); P.update(sm.fix)
        edges = sm.edges(P['offset']); mid = 0.5 * (edges[:-1] + edges[1:])
        mu = sm.mu(p); mu_g = sm.mu(generator_vector(sm, p))
        i_core = sm.names.index('core')
        p0 = p.copy(); p0[i_core] = 0.0
        name = os.path.splitext(os.path.basename(r['path']))[0]
        ax = axs[0, j]
        ax.semilogy(mid, np.maximum(sm.n, 0.5), '.', color='k', ms=2.5, label='measured (counts per channel)')
        ax.semilogy(mid, mu, '-', color='C3', lw=1.1, label='fit: generator physics, all axes free')
        ax.semilogy(mid, mu_g, '--', color='C0', lw=1.0, label="generator's hard case (same photons, angle)")
        ax.semilogy(mid, sm.mu(p0), ':', color='C2', lw=1.0, label='fit with the O 1s wing removed')
        ax.axvline(sm.e0 - mca.SI_KA_KEV, color='0.6', lw=0.6)
        ax.text(sm.e0 - mca.SI_KA_KEV, 0.6, ' elastic − 1.740 keV\n (Si escape)', fontsize=6.5, color='0.4',
                transform=ax.get_xaxis_transform(), va='top')
        ax.set_ylim(max(0.5, np.percentile(sm.n, 1) / 3), sm.n.max() * 3)
        ax.set_title('%s  (readout %s)' % (name, r['readout']), fontsize=10)
        ax.set_ylabel('counts per channel (%.1f eV)' % (1000 * (edges[1] - edges[0])))
        if j == 0:
            ax.legend(fontsize=6.5, loc='upper left')
        res = (sm.n - mu) / np.sqrt(np.maximum(mu, 1.0))
        axs[1, j].plot(mid, res, '.', color='k', ms=2)
        axs[1, j].axhline(0, color='C3', lw=0.8)
        axs[1, j].set_ylabel('(measured − fit) / √fit')
        axs[1, j].set_xlabel('energy (keV)')
        ec = mca.compton_energy(sm.e0, P['angle'])
        data_b, gen_b, (lo, hi) = band_numbers(sm, p)
        axs[0, j].axvspan(lo, hi, color='C1', alpha=0.08)
        lines = [
            'COUNTS   %.2g in the fitted region (%d channels)' % (sm.n.sum(), len(sm.n)),
            'FIT      deviance/dof %.2f' % (r['dev'] / r['dof']),
            'ELASTIC  FWHM %.0f eV (noise %.0f eV); generator %.0f eV' % (
                1000 * mca.Detector(noise=P['noise']).fwhm(sm.e0), 1000 * P['noise'], 1000 * mca.Detector().fwhm(sm.e0)),
            'COMPTON  2θ = %.1f°: free-electron peak %.3f keV;' % (P['angle'], ec),
            '         Compton/Rayleigh photons %.2f' % math.exp(P['logR']),
            '         momentum widths × %.2f of water\'s' % P['doppler'],
            'ESCAPE   × %.2f of Reed (Reed %.3f %% at %.1f keV)' % (P['escape'], 100 * mca.reed_escape(sm.e0), sm.e0),
            'O 1s     wing × %.2f of water\'s (see the summary:' % P['core'],
            '         it trades against the detector tail)',
            'TAILS    low %.1f %% (%.2f keV), shelf %.2f %%,' % (100 * P['tail'], P['tail_slope'], 100 * P['shelf']),
            '         high %.1f %% (%.2f keV); generator 1 %%, 0.2 %%, 0' % (100 * P['rtail'], P['rtail_slope']),
            'BAND     shaded, %.2f to %.2f keV: %.2e per photon per keV' % (lo, hi, data_b),
            '         = %.2f × the generator\'s hard case' % (data_b / gen_b),
        ]
        ax3 = axs[2, j]
        ax3.axis('off')
        ax3.text(0.0, 1.0, '\n'.join(lines), family='monospace', fontsize=6.6, va='top', transform=ax3.transAxes)
    fig.suptitle('Real 10 keV MCA spectra of the scattered beam (anonymised examples), fitted with the generator\'s '
                 'physics; dashed: the generator\'s hard case', fontsize=10.5, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.975))
    path = os.path.join(out, 'S1_examples.png')
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def figure_vs_energy(rows, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    ok = [r for r in rows if r['fit_ok'] == 'True']
    not_shown = [r for r in rows if r['fit_ok'] != 'True']
    mk = {'A': ('o', 'C0', 'readout A (single element)'), 'B': ('s', 'C3', 'readout B (one element of seven)')}
    fig, axs = plt.subplots(2, 3, figsize=(15, 9.4))
    ax = axs.ravel()

    def scatter(a, key, err=None, offset=0.0, filled=True, label=True, sel=None):
        for ro, (m, c, lab) in mk.items():
            rs = [r for r in ok if r['readout'] == ro and (sel is None or sel(r))]
            if not rs:
                continue
            x = np.array([_f(r['beam_keV']) for r in rs]) + offset
            y = np.array([_f(r[key]) for r in rs])
            ye = np.array([_f(r[err]) for r in rs]) if err else None
            a.errorbar(x, y, yerr=ye, fmt=m, color=c, mfc=c if filled else 'none', ms=5, lw=0.8, capsize=2,
                       label=lab if label else None)
    E = np.linspace(5.8, 10.3, 100)
    # (a) escape
    scatter(ax[0], 'escape_fit_x_reed', 'escape_fit_x_reed_err', sel=lambda r: r['escape_ok'] == 'True')
    scatter(ax[0], 'escape_template_x_reed', 'escape_template_x_reed_err', offset=0.06, filled=False, label=False,
            sel=lambda r: r['escape_ok'] == 'True')
    ax[0].axhline(1.0, color='k', lw=0.8, ls='--')
    ax[0].text(5.85, 1.02, "generator: Reed's fraction (× 1)", fontsize=7)
    ax[0].set_ylabel('Si escape fraction / Reed\'s fraction')
    ax[0].set_title('(a) Si escape: filled = model fit, open = shifted-parent template', fontsize=9)
    ax[0].text(5.85, 0.62, "Reed's fraction: %.3f %% at 6 keV, %.3f %% at 8 keV, %.3f %% at 10 keV" % tuple(
        100 * mca.reed_escape(v) for v in (6.0, 8.0, 10.0)), fontsize=7)
    # (b) band ratio
    scatter(ax[1], 'band_ratio_real_over_generator')
    ax[1].axhline(1.0, color='k', lw=0.8, ls='--')
    ax[1].set_ylim(0, None)
    ax[1].set_ylabel('counts under a line: real / generator')
    ax[1].set_title('(b) scatter in the band E0−1.55 keV … Compton−0.35 keV,\nper parent photon, real over the hard case',
                    fontsize=9)
    # (c) resolution
    scatter(ax[2], 'elastic_fwhm_keV', 'elastic_fwhm_err_keV')
    ax[2].plot(E, [mca.Detector().fwhm(v) for v in E], 'k--', lw=0.8, label='generator (noise 0.12 keV, Fano 0.115)')
    ax[2].set_ylabel('elastic line FWHM (keV)')
    ax[2].set_title('(c) detector resolution at the elastic line', fontsize=9)
    ax[2].legend(fontsize=7)
    # (d) O 1s wing
    scatter(ax[3], 'o1s_core_scale', 'o1s_core_scale_err')
    ax[3].axhline(1.0, color='k', lw=0.8, ls='--')
    ax[3].set_ylabel("fitted O 1s wing / water's impulse-approximation wing")
    ax[3].set_title('(d) O 1s Compton wing (degenerate with the detector tail:\nsee the profile in the summary)',
                    fontsize=9)
    # (e) tails
    scatter(ax[4], 'tail_fraction')
    scatter(ax[4], 'high_tail_fraction', offset=0.06, filled=False, label=False)
    ax[4].axhline(0.01, color='k', lw=0.8, ls='--')
    ax[4].text(5.85, 0.0105, 'generator low tail 1 % (0.15 keV); high tail 0', fontsize=7)
    ax[4].set_ylabel('fraction of every photon')
    ax[4].set_title('(e) detector tails: filled = low-energy, open = high-energy', fontsize=9)
    # (f) Compton
    scatter(ax[5], 'compton_over_rayleigh')
    ax[5].axhline(1.0, color='k', lw=0.8, ls='--')
    ax[5].text(5.85, 1.03, "generator default 1 (a free parameter)", fontsize=7)
    ax[5].set_ylabel('Compton / Rayleigh photons')
    ax[5].set_title('(f) Compton / elastic photons (angle, polarisation)', fontsize=9)
    for a in ax:
        a.set_xlabel('beam energy (keV, to 0.1)')
        a.set_xlim(5.7, 10.4)
    ax[0].legend(fontsize=7, loc='upper left')
    txt = 'NOT SHOWN (fit failed, a strong line dominates the region, or the detector tail sat at its bound): ' + \
        ', '.join('%s (%s)' % (r['id'], r['excluded_because']) for r in not_shown)
    txt += '.   Escape points also omit spectra with Cu Kα (8.04 keV) under the Compton escape at 10 keV.'
    import textwrap
    fig.text(0.01, 0.005, '\n'.join(textwrap.wrap(txt, 230)), fontsize=6.8, va='bottom')
    fig.suptitle('Real scatter against the synthetic generator, by beam energy (%d spectra; each point one '
                 'spectrum or one aligned pre-edge sum)' % len(ok), fontsize=11)
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    path = os.path.join(out, 'S2_vs_energy.png')
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def figure_p1(q, out):
    """S3: the bias of data weights and of Poisson weights (P1) on real series of repeated spectra,
    against the line counts per spectrum; truth = the fit of the summed spectrum / N."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    by = {}
    for r in q:
        if r['quantity'].startswith('p1_'):
            by.setdefault(r['example'], {})[r['quantity']] = (_f(r['value']), _f(r['error']))
    ex = sorted(by, key=lambda k: by[k]['p1_series_mean_line_counts'][0])
    if not ex:
        raise SystemExit('S3: no p1_ rows in the quantities table')
    x = np.array([by[k]['p1_series_mean_line_counts'][0] for k in ex])
    fig, ax = plt.subplots(1, 1, figsize=(8.5, 5.6))
    for key, m, c, lab, dx in (('p1_bias_data_weights', 's', 'C3', "data weights (weights='data', before)", 0.97),
                               ('p1_bias_poisson', 'o', 'C0', "Poisson weights (weights='poisson', P1, the default)", 1.03)):
        y = np.array([100 * by[k][key][0] for k in ex]); e = np.array([100 * by[k][key][1] for k in ex])
        ax.errorbar(x * dx, y, yerr=e, fmt=m, color=c, ms=5, capsize=2, lw=0.8, label=lab)
    xx = np.logspace(np.log10(x.min() * 0.8), np.log10(x.max() * 1.2), 100)
    ax.plot(xx, -1900 / xx, 'k--', lw=0.8, label='study B, synthetic: -19 / line counts')
    ax.axhline(0, color='0.5', lw=0.6)
    ax.set_xscale('log')
    ax.set_ylim(-45, 20)
    ax.set_xlabel('line counts per spectrum (fit of the summed spectrum / N)')
    ax.set_ylabel('bias of the mean of N fits (%), ± its standard error')
    n = int(by[ex[0]]['p1_series_N'][0])
    ax.set_title('P1 on real data: %d series of %d repeated spectra (one run, one readout, 10 keV beam);\n'
                 "a line near 8 keV, Gaussian on a quadratic, box ±2 FWHM (the reader's defaults)" % (len(ex), n),
                 fontsize=9.5)
    ax.legend(fontsize=8, loc='lower right')
    fig.text(0.01, 0.01, "The box sits on the 10 keV Compton and elastic escape peaks, a far larger background than "
             "study B's clean line.\nData weights: near -27 % up to ~200 counts (smaller than -19/N below ~70, larger "
             "above), ~-1 % by 3000.\nP1: within its errors from 200 counts up; +2 to +6 % at 25-50 counts.",
             fontsize=7)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    path = os.path.join(out, 'S3_p1_real_series.png')
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def summarise(rows):
    """Per beam energy and readout: medians and ranges of the headline numbers (good fits only)."""
    out = {}
    ok = [r for r in rows if r['fit_ok'] == 'True']
    keys = sorted(set((r['beam_keV'], r['readout']) for r in ok), key=lambda t: (-float(t[0]), t[1]))
    for e, ro in keys:
        rs = [r for r in ok if r['beam_keV'] == e and r['readout'] == ro]
        esc = [r for r in rs if r['escape_ok'] == 'True']
        d = {'n': len(rs)}
        for k in ('elastic_fwhm_keV', 'generator_fwhm_keV', 'band_ratio_real_over_generator', 'o1s_core_scale',
                  'tail_fraction', 'tail_slope_keV', 'shelf_fraction', 'high_tail_fraction', 'compton_over_rayleigh',
                  'angle_2theta_deg', 'doppler_scale', 'compton_fwhm_keV', 'compton_fwhm_generator_keV',
                  'profile_ddev_core1', 'profile_ddev_core0'):
            v = np.array([_f(r.get(k)) for r in rs]); v = v[np.isfinite(v)]
            if len(v):
                d[k] = [float(np.median(v)), float(v.min()), float(v.max())]
        for k in ('escape_fit_x_reed', 'escape_template_x_reed'):
            v = np.array([_f(r[k]) for r in esc]); v = v[np.isfinite(v)]
            if len(v):
                d[k] = [float(np.median(v)), float(v.min()), float(v.max())]
        d['n_escape'] = len(esc)
        out['%s keV, readout %s' % (e, ro)] = d
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out', default='docs/studies/mca_scatter', help='folder for the figures and CSV')
    ap.add_argument('--table', default='docs/studies/mca_scatter/scatter_fits.csv',
                    help='the anonymised table of fitted numbers (from the private spectra)')
    ap.add_argument('--quantities', default='docs/studies/mca_scatter/quantities.csv',
                    help='the per-example quantities in long form (for S3)')
    ap.add_argument('--fixtures', default='', help='folder of example spectra (energy_keV,counts CSV) for S1; '
                    'none are committed (private until the owner agrees)')
    ap.add_argument('--only', default='S2,S3', help='figures to make: S1 (examples, refitted: about 1 min per '
                    'spectrum; needs --fixtures), S2 (numbers against beam energy), S3 (P1 on real series)')
    ap.add_argument('--jobs', type=int, default=4, help='processes for the refits')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    only = set(a.only.split(','))
    rows = _read_table(a.table)
    made = []
    if 'S1' in only and not a.fixtures:
        print('S1 skipped: no --fixtures folder (example spectra are private until the owner agrees)')
    if 'S1' in only and a.fixtures:
        paths = sorted(os.path.join(a.fixtures, f) for f in os.listdir(a.fixtures) if f.endswith('.csv'))
        if a.jobs > 1 and len(paths) > 1:
            from multiprocessing import Pool
            with Pool(min(a.jobs, len(paths))) as pool:
                raw = pool.map(_fit_worker, paths)
        else:
            raw = [_fit_worker(p) for p in paths]
        fits = []
        readout = {r['id']: r['readout'] for r in rows}
        for r in raw:
            head, e, n = read_fixture(r['path'])
            b = float(np.median(np.diff(e)))
            sm = ScatterModel(n, (e[0] - b, b, 0.0), 10.0)
            name = os.path.splitext(os.path.basename(r['path']))[0]
            fits.append(dict(r, sm=sm, readout=readout.get(name, '?')))
        made.append(figure_examples(fits, a.out))
        with open(os.path.join(a.out, 'S1_example_fits.csv'), 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['id', 'parameter', 'value', 'error', 'deviance_per_dof'])
            for r in fits:
                name = os.path.splitext(os.path.basename(r['path']))[0]
                for k, v, s in zip(r['sm'].names, r['p'], r['perr']):
                    w.writerow([name, k, '%.6g' % v, '%.3g' % s, '%.3f' % (r['dev'] / r['dof'])])
                d, g, _ = band_numbers(r['sm'], r['p'])
                w.writerow([name, 'band_ratio_real_over_generator', '%.4f' % (d / g), '', '%.3f' % (r['dev'] / r['dof'])])
    if 'S2' in only:
        made.append(figure_vs_energy(rows, a.out))
        with open(os.path.join(a.out, 'numbers.json'), 'w', encoding='utf-8') as fh:
            json.dump(summarise(rows), fh, indent=1)
    if 'S3' in only:
        made.append(figure_p1(_read_table(a.quantities), a.out))
    for p in made:
        print(p)
    return made


if __name__ == '__main__':
    main()
