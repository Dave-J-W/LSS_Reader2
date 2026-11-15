#!/usr/bin/env python3
"""Monte Carlo check of monitor-normalisation error propagation.

Companion to docs/reports/monitor_noise.md.  Not a pytest module.

    python3 tests/tools/monitor_noise_mc.py            # Monte Carlo + real-data look
    python3 tests/tools/monitor_noise_mc.py --no-real  # Monte Carlo only

Part 1  one frame: ROI sum S/M and net signal (S-(L+R)/2)/M with ONE shared
        monitor reading M.  Empirical standard deviation over many trials
        against (a) the formula the reader uses today (per-pixel monitor
        term, added in quadrature) and (b) the derived formula (monitor term
        applied once, to the summed or net signal).
Part 2  combining frames with different monitors: mean of ratios against
        ratio of sums.
Part 3  read-only look at sample_data/NX_school/2026sep/20260923: scatter of
        Monc, Monp and their ratio in repeated points against sqrt(counts).

The reader's formulas are re-typed here from TwoDDetector.sumFiles /
peakLocate / sumROI and mainwindow.pilRefPatchData; no application code is
imported, so the script has no Qt dependency.
"""
import argparse
import os
import sys

import numpy as np

SEED = 20261115
NTRIAL = 40000            # relative precision of an empirical sigma ~ 1/sqrt(2N) = 0.35 %
SPEC = os.path.join(os.path.dirname(__file__), '..', '..',
                    'sample_data', 'NX_school', '2026sep', '20260923')


# ---------------------------------------------------------------- helpers
def profile(npix, kind):
    """Expected fraction of the ROI total in each pixel (sums to 1)."""
    if kind == 'flat':
        p = np.ones(npix)
    else:  # 'peak': 2D Gaussian on a square ROI, or 1D Gaussian line + 20 % flat
        n = int(round(np.sqrt(npix)))
        if n * n == npix:
            y, x = np.mgrid[:n, :n] - (n - 1) / 2.0
            p = np.exp(-(x ** 2 + y ** 2) / (2 * (n / 6.0) ** 2))
        else:
            x = np.arange(npix) - (npix - 1) / 2.0
            p = np.exp(-x ** 2 / (2 * (npix / 8.0) ** 2))
            p = p / p.sum() * 0.8 + 0.2 / npix
    p = np.ravel(p)
    return p / p.sum()


def draw_monitor(rng, m0, model, g, size):
    """Recorded monitor counts for expected value(s) m0.

    'poisson' : M ~ Poisson(m0)                       u_M^2 = 1/m0
    'gain'    : M = m0 (1 + eps), eps ~ N(0, 1/(g m0)) u_M^2 = 1/(g m0)
    'exact'   : M = m0                                 u_M = 0
    """
    m0 = np.broadcast_to(np.asarray(m0, float), size)
    if model == 'poisson':
        return rng.poisson(m0).astype(float)
    if model == 'gain':
        return m0 * (1 + rng.standard_normal(size) / np.sqrt(g * m0))
    return m0.copy()


def u2_of(model, g, m):
    return {'poisson': 1.0 / m, 'gain': 1.0 / (g * m), 'exact': 0.0 * m}[model]


def rms(x):
    return float(np.sqrt(np.mean(x)))


# ---------------------------------------------------------------- part 1
def one_frame(rng, label, S0, L0, R0, M0, npix, kind, model, g=10.0, jitter=0.0):
    """Returns a dict of empirical and predicted sigmas for one configuration.

    jitter: fractional rms of the true beam intensity from frame to frame.
    Detector and monitor both see it, so it should cancel in the ratio.
    """
    n = NTRIAL
    beam = 1 + jitter * rng.standard_normal(n) if jitter else np.ones(n)
    pS = profile(npix, kind)
    pB = profile(npix, 'flat')
    I_S = rng.poisson(beam[:, None] * S0 * pS[None, :]).astype(float)
    I_L = rng.poisson(beam[:, None] * L0 * pB[None, :]).astype(float)
    I_R = rng.poisson(beam[:, None] * R0 * pB[None, :]).astype(float)
    M = draw_monitor(rng, beam * M0, model, g, n)
    S, L, R = I_S.sum(1), I_L.sum(1), I_R.sum(1)
    N = S - (L + R) / 2

    # (a) the reader today: per pixel var = I/M^2 + I^2/M^3, quadrature over ROI
    def code_var(I):
        return (I / M[:, None] ** 2 + I ** 2 / M[:, None] ** 3).sum(1)
    vS_code, vL_code, vR_code = code_var(I_S), code_var(I_L), code_var(I_R)
    vN_code = vS_code + (vL_code + vR_code) / 4

    # (b) derived: Poisson term on the counts, monitor term once on the total
    u2 = u2_of(model, g, M)              # the monitor model that was simulated
    u2p = 1.0 / M                        # Poisson-on-Monc, whatever the truth
    cnt_S = S / M ** 2
    cnt_N = (S + (L + R) / 4) / M ** 2
    out = dict(
        label=label,
        emp_S=np.std(S / M, ddof=1), emp_N=np.std(N / M, ddof=1),
        mean_S=np.mean(S / M), mean_N=np.mean(N / M),
        code_S=rms(vS_code), code_N=rms(vN_code),
        new_S=rms(cnt_S + (S / M) ** 2 * u2),
        new_N=rms(cnt_N + (N / M) ** 2 * u2),
        # correlation fixed, but Poisson still assumed for the monitor
        pois_S=rms(cnt_S + (S / M) ** 2 * u2p),
        pois_N=rms(cnt_N + (N / M) ** 2 * u2p),
        # monitor term applied per ROI as if S, L, R had independent monitors
        indep_N=rms(cnt_N + (S ** 2 + (L ** 2 + R ** 2) / 4) / M ** 2 * u2),
        cnt_N=rms(cnt_N),
    )
    return out


def part1(rng):
    # name, S0, L0, R0, M0, npix, profile
    regimes = [
        ('A low-Qz  S=7.9e5 M=2.2e5 121px peak', 7.9e5, 4.0e3, 4.0e3, 2.2e5, 121, 'peak'),
        ('A2 same, large bg L=R=2e5           ', 7.9e5, 2.0e5, 2.0e5, 2.2e5, 121, 'peak'),
        ('A3 same as A, flat profile          ', 7.9e5, 4.0e3, 4.0e3, 2.2e5, 121, 'flat'),
        ('B high-Qz S=50 L=R=20 M=2e6 121px   ', 50.0, 20.0, 20.0, 2.0e6, 121, 'peak'),
        ('C MCA 81 ch S=2e4 L=R=4e3 M=2.2e5   ', 2.0e4, 4.0e3, 4.0e3, 2.2e5, 81, 'peak'),
        ('C2 MCA 81 ch S=1e6 L=R=5e4 M=2.2e5  ', 1.0e6, 5.0e4, 5.0e4, 2.2e5, 81, 'peak'),
    ]
    monitors = [('poisson', 'Poisson u2=1/M '), ('gain', 'g=10 u2=1/(10M)'), ('exact', 'noiseless u=0 ')]
    print('PART 1  one frame, one shared monitor reading; %d trials, seed %d' % (NTRIAL, SEED))
    print('  emp     = empirical std of the normalised quantity over the trials')
    print('  code    = reader today: sum_i (I_i/M^2 + I_i^2/M^3), bg in quadrature')
    print('  derived = counts term + (value)^2 u_M^2 with the simulated u_M')
    print('  corr-P  = correlation fixed but u_M^2 = 1/M assumed regardless')
    print('  indep   = monitor term applied to S, L, R separately (no cancellation)')
    print('  ratios are predicted/empirical: 1.00 is right, <1 understates the error')
    hdr = ('%-37s %-15s | %10s %7s %7s %7s | %10s %7s %7s %7s %7s'
           % ('regime', 'monitor', 'emp S/M', 'code', 'derived', 'corr-P',
              'emp net/M', 'code', 'derived', 'corr-P', 'indep'))
    print(hdr)
    print('-' * len(hdr))
    for name, S0, L0, R0, M0, npix, kind in regimes:
        for model, mlabel in monitors:
            r = one_frame(rng, name, S0, L0, R0, M0, npix, kind, model)
            print('%-37s %-15s | %10.3e %7.3f %7.3f %7.3f | %10.3e %7.3f %7.3f %7.3f %7.3f'
                  % (name, mlabel, r['emp_S'], r['code_S'] / r['emp_S'], r['new_S'] / r['emp_S'],
                     r['pois_S'] / r['emp_S'], r['emp_N'], r['code_N'] / r['emp_N'],
                     r['new_N'] / r['emp_N'], r['pois_N'] / r['emp_N'], r['indep_N'] / r['emp_N']))
    # beam jitter: both detector and monitor follow the beam
    r = one_frame(rng, 'A + 2% beam jitter', 7.9e5, 4.0e3, 4.0e3, 2.2e5, 121, 'peak', 'gain', jitter=0.02)
    print('%-37s %-15s | %10.3e %7.3f %7.3f %7.3f | %10.3e %7.3f %7.3f %7.3f %7.3f'
          % ('A + 2 % real beam jitter (tracked)  ', 'g=10 u2=1/(10M)', r['emp_S'], r['code_S'] / r['emp_S'],
             r['new_S'] / r['emp_S'], r['pois_S'] / r['emp_S'], r['emp_N'], r['code_N'] / r['emp_N'],
             r['new_N'] / r['emp_N'], r['pois_N'] / r['emp_N'], r['indep_N'] / r['emp_N']))
    print()


# ---------------------------------------------------------------- part 2
def part2(rng):
    print('PART 2  combining n frames at one Qz, each with its own monitor')
    print('  MoR = mean of ratios (1/n) sum S_k/M_k  (what sumFiles does, per pixel)')
    print('  RoS = ratio of sums  sum S_k / sum M_k')
    print('  sig(code-like) = sqrt(sum_k var_k)/n with var_k = S_k/M_k^2 + S_k^2 u_k^2/M_k^2 (ROI level)')
    hdr = ('%-44s %-9s %10s | %9s %9s %9s | %9s %9s %9s'
           % ('case', 'monitor', 'truth', 'bias MoR', 'std MoR', 'sig/emp', 'bias RoS', 'std RoS', 'sig/emp'))
    print(hdr)
    print('-' * len(hdr))
    cases = [
        # label, rate (counts per monitor count), expected monitors per frame
        ('equal M: 5 frames M=2e6, 10 cts each', 5e-6, [2e6] * 5),
        ('unequal M: 0.25,0.5,1,2,4e6, rate 5e-6', 5e-6, [2.5e5, 5e5, 1e6, 2e6, 4e6]),
        ('unequal M, high counts: rate 3.5', 3.5, [2.5e4, 5e4, 1e5, 2e5, 4e5]),
        ('tiny M: 5 frames M=30, rate 2', 2.0, [30.0] * 5),
        ('tiny unequal M: 10,20,40,80,160, rate 2', 2.0, [10.0, 20.0, 40.0, 80.0, 160.0]),
    ]
    n = 200000
    for label, rate, m0 in cases:
        m0 = np.array(m0)
        for model in ('poisson', 'exact'):
            M = draw_monitor(rng, m0[None, :], model, 10.0, (n, len(m0)))
            M = np.maximum(M, 1.0)                 # avoid 1/0 in the tiny-M cases
            S = rng.poisson(rate * np.broadcast_to(m0, M.shape)).astype(float)
            u2 = u2_of(model, 10.0, M)
            mor = (S / M).mean(1)
            ros = S.sum(1) / M.sum(1)
            sig_mor = np.sqrt((S / M ** 2 + S ** 2 * u2 / M ** 2).sum(1)) / len(m0)
            Mt, St = M.sum(1), S.sum(1)
            u2t = (u2 * M ** 2).sum(1) / Mt ** 2   # independent monitors: variances of counts add
            sig_ros = np.sqrt(St / Mt ** 2 + St ** 2 * u2t / Mt ** 2)
            print('%-44s %-9s %10.3e | %+8.2f%% %9.3e %9.3f | %+8.2f%% %9.3e %9.3f'
                  % (label, model, rate, 100 * (mor.mean() / rate - 1), mor.std(ddof=1),
                     rms(sig_mor ** 2) / mor.std(ddof=1), 100 * (ros.mean() / rate - 1),
                     ros.std(ddof=1), rms(sig_ros ** 2) / ros.std(ddof=1)))
    print()


# ---------------------------------------------------------------- part 3
def read_spec(path):
    scans, cur = {}, None
    with open(path) as fh:
        for line in fh:
            if line.startswith('#S'):
                cur = int(line.split()[1])
                scans[cur] = dict(cmd=' '.join(line.split()[2:]), rows=[], cols=None, absorber='?')
            elif cur is None:
                continue
            elif line.startswith('#L'):
                scans[cur]['cols'] = line[3:].split()
            elif line.startswith('#A'):
                scans[cur]['absorber'] = line.split()[-1]
            elif line.strip() and not line.startswith('#') and scans[cur]['cols']:
                try:
                    v = [float(x) for x in line.split()]
                except ValueError:
                    continue
                if len(v) == len(scans[cur]['cols']):
                    scans[cur]['rows'].append(v)
    return scans


def col(scan, name):
    c = scan['cols']
    return np.array(scan['rows'])[:, len(c) - 1 - c[::-1].index(name)]   # last column of that name


def succ(x):
    """Relative scatter from successive differences (insensitive to slow drift)."""
    return float(np.sqrt(np.mean(np.diff(x) ** 2) / 2) / np.mean(x))


def part3():
    path = os.path.normpath(SPEC)
    if not os.path.exists(path):
        print('PART 3  skipped: %s not found' % path)
        return
    scans = read_spec(path)
    print('PART 3  real data, %s (read only)' % os.path.relpath(path))
    print('  "sd" = relative scatter from successive differences; "/P" = that divided by the')
    print('  Poisson-on-counts prediction (1/sqrt(M); for the ratio sqrt(1/Monc + 1/Monp)).')
    print('  With n points the statistical precision of each "/P" figure is roughly 1/sqrt(1.3 n).')
    hdr = ('%4s %-34s %3s %3s %4s | %10s %9s %5s | %10s %9s %5s | %9s %5s | %6s'
           % ('scan', 'command', 'abs', 'n', 'T/s', 'Monc', 'sd', '/P', 'Monp', 'sd', '/P',
              'sd ratio', '/P', 'r(dd)'))
    print(hdr)
    print('-' * len(hdr))
    for n in sorted(scans):
        s = scans[n]
        if len(s['rows']) < 4:
            continue
        mc, mp, t = col(s, 'Monc'), col(s, 'Monp'), col(s, 'Seconds')
        r = mc / mp
        pr = np.sqrt(1 / mc.mean() + 1 / mp.mean())
        rdd = np.corrcoef(np.diff(mc), np.diff(mp))[0, 1]
        print('%4d %-34s %3s %3d %4g | %10.4g %9.2e %5.2f | %10.4g %9.2e %5.2f | %9.2e %5.2f | %+6.2f'
              % (n, s['cmd'][:34], s['absorber'], len(mc), t[0], mc.mean(), succ(mc),
                 succ(mc) * np.sqrt(mc.mean()), mp.mean(), succ(mp), succ(mp) * np.sqrt(mp.mean()),
                 succ(r), succ(r) / pr, rdd))
    print()
    print('  Repeated-point scans 14 and 15 in more detail (21 points, 10 s each):')
    for n in (14, 15):
        if n not in scans:
            continue
        s = scans[n]
        mc, mp, p = col(s, 'Monc'), col(s, 'Monp'), col(s, 'Pilatus')
        print('  scan %d: Monc %.5g  full std %.2e  sd %.2e  Poisson %.2e'
              % (n, mc.mean(), mc.std(ddof=1) / mc.mean(), succ(mc), 1 / np.sqrt(mc.mean())))
        print('           Monp %.5g  full std %.2e  sd %.2e  Poisson %.2e'
              % (mp.mean(), mp.std(ddof=1) / mp.mean(), succ(mp), 1 / np.sqrt(mp.mean())))
        print('           SPEC "Pilatus" column mean %.1f: Pilatus/Monc sd %.2e; sqrt(1/P) %.2e; '
              'code-style sqrt(1/P+1/Monc) %.2e'
              % (p.mean(), succ(p / mc), 1 / np.sqrt(p.mean()), np.sqrt(1 / p.mean() + 1 / mc.mean())))
    dark = [n for n in sorted(scans) if scans[n]['rows'] and
            np.mean(col(scans[n], 'Monc') / col(scans[n], 'Seconds')) < 1000]
    for n in dark:
        s = scans[n]
        mc, mp, t = col(s, 'Monc'), col(s, 'Monp'), col(s, 'Seconds')
        print('  low-rate scan %d (%d pts, %g s): Monc %.1f /s (std %.1f counts), Monp %.1f /s (std %.1f counts)'
              % (n, len(mc), t[0], np.mean(mc / t), mc.std(ddof=1) if len(mc) > 1 else 0,
                 np.mean(mp / t), mp.std(ddof=1) if len(mp) > 1 else 0))
    print('  Monb max %g, Mond max %g over the whole file'
          % (max(col(s, 'Monb').max() for s in scans.values() if s['rows']),
             max(col(s, 'Mond').max() for s in scans.values() if s['rows'])))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--no-real', action='store_true', help='skip the look at the real SPEC file')
    args = ap.parse_args(argv)
    np.set_printoptions(linewidth=200)
    rng = np.random.default_rng(SEED)
    part1(rng)
    part2(rng)
    if not args.no_real:
        part3()
    return 0


if __name__ == '__main__':
    sys.exit(main())
