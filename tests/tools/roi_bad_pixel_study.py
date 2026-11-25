"""B3 (F95; owner, Q-UI-B3: "wire them"): should the reflectivity ROI get a
bad-pixel pass of its own? Known truth first (AGENTS.md rule 12).

Synthetic reflectivity frames (``synthetic.xrr_images``: a smooth film, the
NX-like plan, the real monitor model) are reduced by the reader's own
arithmetic (``lss_core.reflectivity.frame_row``: peakLocate, sumROI, netROI)
after one of these passes:

    none     no pass: today's default (Frames > Reduce, iterations 0)
    frame4   the whole-frame pass as a user switches it on today
             (TwoDDetector.removeBadPix, 1 iteration, factor 4)
    roi3, roi10, roi40
             the same test, applied only to the ROI's three boxes, at factor
             3, 10 (the Reflectivity tab's field) and 40
    bg10     factor 10 on the two background boxes only (no signal there)

Hot pixels are added at random to the ROI's boxes, a Poisson number per
frame (mean 0, 0.1 or 0.5), each a log-uniform 3-300 counts. Every reduced
point is compared with the same frame reduced clean (no hot pixel, no pass),
so what is measured is what the hot pixels and the passes add:

- per Qz class: the bias of the net (in % of its expected value and in units
  of its error), the extra scatter (SD of (net - clean)/error), the share of
  clean frames a pass changes (false corrections) and of hot pixels it
  removes;
- per join: the pulls of the joint fit's factor (guard p 0.7) against the
  true step;
- NX school scans 6-9 (public, real): how many ROI pixels each pass changes,
  and by how much it moves each point.

    python tests/tools/roi_bad_pixel_study.py [--out docs/studies/roi_bad_pixels] [--reps 30] [--procs N]
"""
import argparse
import csv
import json
import math
import os
import sys
import time
import warnings

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [p for p in (ROOT, HERE, os.path.join(ROOT, 'tests')) if p not in sys.path]
os.chdir(ROOT)

import synth                                                  # noqa: E402
import ref_guard_study as A                                   # noqa: E402
from synthetic import xrr, xrr_images as xi, xrr_scans as xs  # noqa: E402
from lss_core import patching, reflectivity as refl           # noqa: E402
from lss_core.errors import as_model                          # noqa: E402

OUT_DEFAULT = os.path.join('docs', 'studies', 'roi_bad_pixels')
ARMS = ('none', 'frame4', 'roi3', 'roi10', 'roi40', 'bg10')
LABEL = {'none': 'no pass (today)', 'frame4': 'whole frame, factor 4', 'roi3': 'ROI, factor 3',
         'roi10': 'ROI, factor 10', 'roi40': 'ROI, factor 40', 'bg10': 'background boxes, factor 10'}
COLOR = {'none': '#222222', 'frame4': '#888888', 'roi3': '#d23', 'roi10': '#2a78d6', 'roi40': '#1baf7a',
         'bg10': '#d4a017'}
HOT = (0.0, 0.1, 0.5)                 # hot pixels per frame in the ROI's boxes (Poisson mean)
# conditions: the reflected beam's σ (rows, columns) in pixels and the flux relative to the NX-like beamline's
BEAMS = {'synthetic': ((0.6, 1.2), 1.0), 'sharp': ((0.3, 0.5), 1.0), 'sparse': ((0.6, 1.2), 2e-6)}
AMP = (3.0, 300.0)                    # their counts, log-uniform
QZ_CLASSES = ((0.0, 0.05), (0.05, 0.15), (0.15, 0.30), (0.30, 1.0))
GUARD = 0.7
SLIT, BG_DEG = xi.SLIT, xi.BG_OFFSET_DEG
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
NX_SCANS = (6, 7, 8, 9)


# ------------------------------------------------------------------ the passes

def neighbour_mean(data):
    """The mean of each pixel's 4 neighbours, edges replicated (as removeBadPix)."""
    big = np.pad(data, 1, mode='edge')
    return 0.25 * (big[:-2, 1:-1] + big[2:, 1:-1] + big[1:-1, :-2] + big[1:-1, 2:])


def bad_pixel_pass(data, iterations=1, factor=1.0, region=None):
    """``TwoDDetector.removeBadPix``'s test and replacement, restricted to
    ``region`` (a boolean mask; None: the whole frame). Returns (image, mask
    of the pixels replaced)."""
    data = np.asarray(data, float).copy()
    avg = (math.sqrt(np.average(data)) + 2) ** 2
    tre = (2 + 2 * iterations) / iterations
    changed = np.zeros(data.shape, bool)
    for _ in range(iterations):
        nb = neighbour_mean(data)
        bad = (data > tre * nb * factor) & (data > avg)
        if region is not None:
            bad &= region
        data = np.where(bad, nb, data)
        changed |= bad
    return data, changed


def margin(data, factor, region, iterations=1):
    """The largest ratio, over ``region``, of a pixel to the threshold it must
    pass to be replaced (``bad_pixel_pass``'s first iteration): above 1 is
    replaced. How close the frame came to a correction."""
    data = np.asarray(data, float)
    avg = (math.sqrt(np.average(data)) + 2) ** 2
    tre = (2 + 2 * iterations) / iterations
    thr = np.maximum(tre * neighbour_mean(data) * factor, avg)
    return float(np.max(data[region] / thr[region]))


def roi_masks(shape):
    """(all three boxes, the two background boxes) at the generator's nominal positions."""
    col, row = xi.beam_pixel()
    sc, lc, rc = xi.box_columns()
    allm, bgm = np.zeros(shape, bool), np.zeros(shape, bool)
    for c, is_bg in ((sc, False), (lc, True), (rc, True)):
        core, outer = xi._box(row, c)
        for sl in [core] + outer:
            allm[sl] = True
            if is_bg:
                bgm[sl] = True
    return allm, bgm


def apply_arm(arm, img, masks):
    if arm == 'none':
        return img, np.zeros(img.shape, bool)
    if arm == 'frame4':
        return bad_pixel_pass(img, 1, 4.0)
    if arm == 'bg10':
        return bad_pixel_pass(img, 1, 10.0, masks[1])
    return bad_pixel_pass(img, 1, float(arm[3:]), masks[0])


# ------------------------------------------------------------------ one replicate

def measure(beam, seed):
    """The synthetic scans of condition ``beam`` (BEAMS), and the generator set to its reflected beam."""
    (xi.SIGMA_ROW, xi.SIGMA_COL), flux = BEAMS[beam]
    bl = xs.Beamline(**xs.REAL_MONITOR)
    bl.flux *= flux
    return xs.measure(xrr.film(*A.COV_TRUTH), xs.nx_like_plan(), beamline=bl, seed=seed, errors='counting+monitor')


def reduce_frame(det, img, monitor, qz, core_only):
    row, info = refl.frame_row(det, img, np.sqrt(np.maximum(img, 0)), monitor, (synth.DB_X, synth.DB_Y), qz,
                               SLIT, BG_DEG, 'H', synth.S2D, low_qz_slit=bool(core_only))
    return float(row[1]), float(row[2])


def replicate(args):
    """Every frame of one replicate at one hot-pixel rate and beam, reduced clean and by every arm."""
    rep, hot, beam = args
    warnings.simplefilter('ignore')
    from TwoDDetector import TwoDDetector
    det = TwoDDetector('Pilatus')
    det.errors = as_model('legacy')
    r = measure(beam, rep)
    rng = np.random.default_rng(10007 * rep + int(1000 * hot) + 1 + 5 * list(BEAMS).index(beam))
    hrng = np.random.default_rng(7919 * rep + int(1000 * hot) + 3)
    masks = None
    frames, hots, nets = [], [], {a: {} for a in ('clean',) + ARMS}
    for num, rec in sorted(r.scans.items()):
        for k in range(len(rec.qz)):
            img0 = xi.frame(rec, k, rng)
            if masks is None:
                masks = roi_masks(img0.shape)
                where = np.argwhere(masks[0])
                sigm = masks[0] & ~masks[1]
            n_hot = hrng.poisson(hot)
            img = img0.copy()
            spots = where[hrng.choice(len(where), n_hot, replace=False)] if n_hot else np.zeros((0, 2), int)
            amps = np.round(np.exp(hrng.uniform(math.log(AMP[0]), math.log(AMP[1]), n_hot)))
            for (i, j), a in zip(spots, amps):
                img[i, j] += a
            q = float(rec.qz[k])
            m = float(rec.monc[k])
            nc, ec = reduce_frame(det, img0, m, q, rec.core_only[k])
            nets['clean'].setdefault(num, []).append((q, nc, ec))
            expected = float(r.truth(np.array([q]))[0]) / rec.scale
            in_sig = np.array([bool(sigm[i, j]) for i, j in spots], bool)
            row = dict(scan=num, point=k, qz=q, expected=expected, clean=nc, clean_err=ec, hot=int(n_hot),
                       hot_counts=float(amps.sum()), hot_signal=int(in_sig.sum()), hot_bg=int((~in_sig).sum()),
                       margin3=margin(img0, 3.0, masks[0]), margin10=margin(img0, 10.0, masks[0]))
            nb0 = neighbour_mean(img)
            for arm in ARMS:
                out, changed = apply_arm(arm, img, masks)
                n, e = reduce_frame(det, out, m, q, rec.core_only[k])
                nets[arm].setdefault(num, []).append((q, n, e))
                hit = int(sum(changed[i, j] for i, j in spots))
                row.update({arm: n, arm + '_err': e, arm + '_changed': int((changed & masks[0]).sum()),
                            arm + '_hit': hit})
            for (i, j), a, sg in zip(spots, amps, in_sig):
                hots.append(dict(qz=q, amp=float(a), neighbours=float(nb0[i, j]), box='signal' if sg else 'background',
                                 **{arm: bool(apply_arm(arm, img, masks)[1][i, j]) for arm in ARMS[1:]}))
            frames.append(row)
    joins = join_pulls(r, nets)
    return frames, joins, hots


def join_pulls(r, nets):
    """{arm: [pull of each join]} of the joint fit (guard p 0.7) against the true steps."""
    order = sorted(r.scans)
    steps = r.true_steps()
    truth = [math.log(steps[k]) for k in sorted(steps)] if isinstance(steps, dict) else [math.log(s) for s in steps]
    out = {}
    for arm, per in nets.items():
        sc = {n: patching.Scan(*(np.array(v, float).T)) for n, v in per.items()}
        pulls = []
        for j, (na, nb) in enumerate(zip(order[:-1], order[1:])):
            try:
                f = patching.joint_factor(sc[na], sc[nb], guard_p=GUARD)
            except (ValueError, np.linalg.LinAlgError):
                pulls.append(None)
                continue
            pulls.append((f.delta - truth[j]) / f.err if f.err > 0 else None)
        out[arm] = pulls
    return out


# ------------------------------------------------------------------ NX school (real)

def run_nx():
    """Each arm on the real frames of NX scans 6-9: pixels changed in the ROI and the net's move."""
    from lss_core.experiment import Experiment
    from TwoDDetector import TwoDDetector
    exp = Experiment(NX)
    det = TwoDDetector('Pilatus')
    det.errors = as_model('legacy')
    rows = []
    for f in exp.frames(list(NX_SCANS)):
        det.openFile(f.path, bad_pix=0, bad_fac=1)
        img = np.asarray(det.imageData, float)
        base, info = refl.frame_row(det, img, np.sqrt(np.maximum(img, 0)), f.monitor, f.beam_xy, f.qz, SLIT, BG_DEG,
                                    'H', f.distance, low_qz_slit=False)
        cx, cy = info['centre']
        masks = nx_masks(img.shape, cx, cy, info['bg'])
        row = dict(scan=f.scan, point=f.index, qz=float(f.qz), net=float(base[1]), err=float(base[2]),
                   margin3=margin(img, 3.0, masks[0]), margin10=margin(img, 10.0, masks[0]),
                   margin_frame4=margin(img, 4.0, np.ones(img.shape, bool)))
        for arm in ARMS[1:]:
            out, changed = apply_arm(arm, img, masks)
            r2, _ = refl.frame_row(det, out, np.sqrt(np.maximum(out, 0)), f.monitor, f.beam_xy, f.qz, SLIT, BG_DEG,
                                   'H', f.distance, low_qz_slit=False)
            row[arm + '_changed'] = int((changed & masks[0]).sum())
            row[arm + '_dz'] = float((r2[1] - base[1]) / base[2]) if base[2] > 0 else float('nan')
            row[arm + '_rel'] = float((r2[1] - base[1]) / base[1]) if base[1] else float('nan')
        rows.append(row)
    return rows


def nx_masks(shape, cx, cy, bg):
    """The ROI's boxes where the reader summed them on a real frame (centre found, 21 x 11, 'H')."""
    allm, bgm = np.zeros(shape, bool), np.zeros(shape, bool)
    w, h = SLIT[0] - 2, SLIT[1] - 2
    rows = slice(int(round(cy)) - h // 2 - 1, int(round(cy)) + h // 2 + 2)
    for c, is_bg in ((cx, False), (cx - bg * w, True), (cx + bg * w, True)):
        cols = slice(int(round(c)) - w // 2 - 1, int(round(c)) + w // 2 + 2)
        allm[rows, cols] = True
        if is_bg:
            bgm[rows, cols] = True
    return allm, bgm


# ------------------------------------------------------------------ statistics and output

def qz_class(q):
    for lo, hi in QZ_CLASSES:
        if lo <= q < hi:
            return '%.2f-%.2f' % (lo, hi)
    return 'other'


def summarise(frames):
    """Rows per (beam, hot, Qz class, arm)."""
    out = []
    keys = sorted({(f['_beam'], f['_hot'], qz_class(f['qz'])) for f in frames})
    for beam, hot, qc in keys:
        sel = [f for f in frames if f['_beam'] == beam and f['_hot'] == hot and qz_class(f['qz']) == qc]
        for arm in ARMS:
            d = np.array([f[arm] - f['clean'] for f in sel])
            z = d / np.array([f['clean_err'] for f in sel])
            rel = d / np.array([f['expected'] for f in sel])
            clean = [f for f in sel if f['hot'] == 0]
            false = float(np.mean([f[arm + '_changed'] > 0 for f in clean])) if clean else float('nan')
            loss = float(np.mean([(f[arm] - f['clean']) / f['expected'] for f in clean if f[arm + '_changed'] > 0])) \
                if any(f[arm + '_changed'] > 0 for f in clean) else 0.0
            n_hot = sum(f['hot'] for f in sel)
            only = lambda key: [((f[arm] - f['clean']) / f['expected']) for f in sel if f['hot'] and f[key] == f['hot']]
            bs, bb = only('hot_signal'), only('hot_bg')
            out.append(dict(beam=beam, hot=hot, qz=qc, arm=arm, frames=len(sel), bias_pct=100 * float(np.mean(rel)),
                            bias_signal_pct=100 * float(np.mean(bs)) if bs else float('nan'),
                            bias_bg_pct=100 * float(np.mean(bb)) if bb else float('nan'),
                            rms_pct=100 * float(np.sqrt(np.mean(rel ** 2))), bias_z=float(np.mean(z)),
                            sd_z=float(np.std(z, ddof=1)), false_rate=false, false_loss_pct=100 * loss,
                            hot_pixels=int(n_hot), removed=(sum(f[arm + '_hit'] for f in sel) / n_hot) if n_hot else None))
    return out


def join_stats(joins):
    out = []
    for beam in BEAMS:
        for hot in HOT:
            for arm in ('clean',) + ARMS:
                p = np.array([x for j in joins if j['_hot'] == hot and j['_beam'] == beam for x in j[arm]
                              if x is not None])
                out.append(dict(beam=beam, hot=hot, arm=arm, joins=len(p), pull_sd=float(np.std(p, ddof=1)),
                                mean_pull=float(np.mean(p)), cover1=float(np.mean(np.abs(p) < 1))))
    return out


def write_csv(path, rows):
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def example_frame(seed=4):
    """One sparse synthetic frame (the last point of the last scan, flux × 1e-3) with two hot pixels added, one
    in the signal box beside the beam and one in a background box: (image, clean image, record, k, spots)."""
    r = measure('sparse', seed)
    num = sorted(r.scans)[-1]
    rec = r.scans[num]
    k = len(rec.qz) - 1
    rng = np.random.default_rng(seed)
    img0 = None
    for kk in range(k + 1):
        img0 = xi.frame(rec, kk, rng)
    col, row = xi.beam_pixel()
    sc, lc, rc = xi.box_columns()
    spots = [(row + 1, sc + 3, 6.0), (row - 2, rc - 3, 5.0)]
    img = img0.copy()
    for i, j, a in spots:
        img[i, j] += a
    return img, img0, rec, k, spots, r


def figures(summ, jst, nx, hots, frames, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    classes = [qz_class(lo + 1e-9) for lo, _ in QZ_CLASSES]
    xs_ = np.arange(len(classes))

    def get(hot, arm, key, beam):
        return [next((r[key] for r in summ if r['hot'] == hot and r['qz'] == c and r['arm'] == arm
                      and r['beam'] == beam), np.nan) for c in classes]

    # R1: one frame, raw, and what the passes do to it
    img, img0, rec, k, spots, r = example_frame()
    masks = roi_masks(img.shape)
    from TwoDDetector import TwoDDetector
    det = TwoDDetector('Pilatus')
    det.errors = as_model('legacy')
    col, row = xi.beam_pixel()
    sc, lc, rc = xi.box_columns()
    r0, r1, c0, c1 = row - 8, row + 9, lc - 13, rc + 14
    fig, axes = plt.subplots(3, 1, figsize=(11, 6.6))
    nets = {}
    for ax, (title, im, arm) in zip(axes, (('(a) the frame as counted, two hot pixels added (circled)', img, None),
                                           ('(b) after the ROI pass at factor 10: pixels replaced (squares)', img, 'roi10'),
                                           ('(c) after the ROI pass at factor 3', img, 'roi3'))):
        out_img, changed = (im, np.zeros(im.shape, bool)) if arm is None else apply_arm(arm, im, masks)
        nets[arm or 'hot'] = reduce_frame(det, out_img, float(rec.monc[k]), float(rec.qz[k]), rec.core_only[k])
        imh = ax.imshow(out_img[r0:r1, c0:c1], cmap='viridis', aspect='auto', vmin=0, vmax=6,
                        extent=(c0 - 0.5, c1 - 0.5, r1 - 0.5, r0 - 0.5))
        fig.colorbar(imh, ax=ax, pad=0.01, fraction=0.03, label='counts')
        for cc, lab in ((sc, 'signal'), (lc, 'background'), (rc, 'background')):
            ax.add_patch(Rectangle((cc - 10.5, row - 5.5), 21, 11, fill=False, ec='w', lw=1))
            ax.text(cc, r0 + 0.3, lab, color='w', ha='center', va='top', fontsize=7)
        if arm is None:
            for i, j, a in spots:
                ax.plot(j, i, 'o', ms=12, mfc='none', mec='#ff4444', mew=1.5)
        for i, j in np.argwhere(changed[r0:r1, c0:c1]):
            ax.plot(j + c0, i + r0, 's', ms=9, mfc='none', mec='#1baf7a', mew=1.5)
        ax.set_title(title, fontsize=8)
        ax.set_yticks([])
    nets['clean'] = reduce_frame(det, img0, float(rec.monc[k]), float(rec.qz[k]), rec.core_only[k])
    axes[-1].set_xlabel('detector column')
    mk = float(rec.monc[k])
    fig.suptitle('R1. One sparse synthetic frame at Qz %.2f, net counts: %.1f ± %.1f clean, %.1f with the two hot '
                 'pixels, %.1f after factor 10, %.1f after factor 3' % (rec.qz[k], nets['clean'][0] * mk,
                                                                      nets['clean'][1] * mk, nets['hot'][0] * mk,
                                                                      nets['roi10'][0] * mk, nets['roi3'][0] * mk),
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'R1_one_frame.png'), dpi=A.DPI)
    plt.close(fig)
    example = dict(qz=float(rec.qz[k]), monitor=mk, counts_clean=nets['clean'][0] * mk, err_clean=nets['clean'][1] * mk,
                   counts_hot=nets['hot'][0] * mk, counts_roi10=nets['roi10'][0] * mk, counts_roi3=nets['roi3'][0] * mk,
                   spots=[[int(i), int(j), a] for i, j, a in spots], peak_pixel=float(img0[row, sc]),
                   neighbours=[float(neighbour_mean(img)[i, j]) for i, j, _ in spots],
                   floor=float((math.sqrt(np.average(img)) + 2) ** 2))

    # R2: the extra scatter, every condition
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=True)
    for ax, beam in zip(axes, BEAMS):
        for arm in ARMS:
            ax.plot(xs_, get(0.5, arm, 'sd_z', beam), 'o-', color=COLOR[arm], label=LABEL[arm])
        ax.set_xticks(xs_)
        ax.set_xticklabels(['Qz ' + c for c in classes], fontsize=8)
        ax.set_title('%s: beam σ %.1f × %.1f pixels, flux × %g; 0.5 hot pixels per frame'
                     % ((beam,) + BEAMS[beam][0] + (BEAMS[beam][1],)), fontsize=8)
    axes[0].set_ylabel('extra scatter: SD of (net − clean) / its error')
    axes[0].legend(fontsize=7, frameon=False)
    fig.suptitle('R2. The scatter hot pixels add to a point, in units of its error bar, and what each pass leaves',
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'R2_extra_scatter.png'), dpi=A.DPI)
    plt.close(fig)

    # R3: which hot pixels a pass removes: the threshold
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    hs = [h for h in hots if h['beam'] == 'sparse']
    nb = np.array([h['neighbours'] for h in hs])
    amp = np.array([h['amp'] for h in hs])
    for ax, arm, f in zip(axes, ('frame4', 'roi10', 'roi3'), (4.0, 10.0, 3.0)):
        hit = np.array([h[arm] for h in hs])
        ax.loglog(np.maximum(nb[~hit], 0.05), amp[~hit], '.', ms=3, color='#d23', label='kept (missed)')
        ax.loglog(np.maximum(nb[hit], 0.05), amp[hit], '.', ms=3, color='#1baf7a', label='replaced')
        xx = np.geomspace(0.05, 300, 50)
        ax.loglog(xx, 4 * f * xx, 'k-', lw=0.8, label='4 × factor × neighbours')
        ax.set_xlabel('mean of the 4 neighbours (counts)')
        ax.set_title('%s: %.0f %% of hot pixels replaced' % (LABEL[arm], 100 * hit.mean()), fontsize=9)
    axes[0].set_ylabel('hot pixel (counts added)')
    axes[0].legend(fontsize=7, frameon=False)
    fig.suptitle('R3. Sparse frames: a hot pixel is replaced when it beats 4 × factor × its neighbours and the '
                 'frame\'s floor (√mean + 2)² (about 4.5 counts here)', fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'R3_threshold.png'), dpi=A.DPI)
    plt.close(fig)

    # R4: the join factors
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
    w = 0.11
    for ax, beam in zip(axes, ('synthetic', 'sparse')):
        for i, arm in enumerate(('clean',) + ARMS):
            v = [next(r['pull_sd'] for r in jst if r['hot'] == hot and r['arm'] == arm and r['beam'] == beam)
                 for hot in HOT]
            ax.bar(np.arange(len(HOT)) + (i - 3) * w, v, w, color=COLOR.get(arm, '#bbbbbb'),
                   label=LABEL.get(arm, 'clean frames (no hot pixel)'))
        ax.axhline(1, color='k', lw=0.8)
        ax.set_xticks(range(len(HOT)))
        ax.set_xticklabels(['%.1f hot pixels per frame' % h for h in HOT], fontsize=8)
        ax.set_ylim(0, 1.7)
        ax.set_title('%s frames' % ('bright (NX-like)' if beam == 'synthetic' else 'sparse at high Qz'), fontsize=9)
    axes[0].set_ylabel('pull SD of the join factors (1: honest)')
    axes[1].legend(fontsize=7, frameon=False, ncol=2, loc='upper left')
    fig.suptitle('R4. The join factors (joint fit, guard p 0.7; %d joins per bar), in units of their errors'
                 % next(r['joins'] for r in jst), fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'R4_join_pulls.png'), dpi=A.DPI)
    plt.close(fig)

    # R5: how close a real or a clean pixel came to being replaced, at factors 3 and 10
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
    bins = np.geomspace(0.05, 5, 46)
    for ax, key, f in zip(axes, ('margin3', 'margin10'), (3, 10)):
        for beam, colr in (('synthetic', '#2a78d6'), ('sharp', '#d4a017'), ('sparse', '#d23')):
            m = np.array([fr[key] for fr in frames if fr['hot'] == 0 and fr['_beam'] == beam])
            ax.hist(m, bins=bins, histtype='step', color=colr, lw=1.5,
                    label='synthetic clean frames, %s (%d; %d past 1)' % (beam, len(m), int(np.sum(m > 1))))
        if nx:
            m = np.array([r_[key] for r_ in nx])
            ax.hist(m, bins=bins, histtype='stepfilled', color='#888888', alpha=0.6,
                    label='NX school scans 6-9, real (%d; %d past 1)' % (len(m), int(np.sum(m > 1))))
        ax.axvline(1, color='#d23', lw=1)
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlabel('ROI pixel closest to being replaced: its counts / its threshold')
        ax.set_title('factor %d: a frame past 1 has a pixel replaced' % f, fontsize=9)
        ax.legend(fontsize=6.5, frameon=False, loc='upper left')
    axes[0].set_ylabel('frames')
    fig.suptitle('R5. Frames with no hot pixel: at factor 10 none is touched, real or synthetic; at factor 3 a few '
                 'sparse ones are', fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'R5_margins.png'), dpi=A.DPI)
    plt.close(fig)
    return example


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=OUT_DEFAULT)
    ap.add_argument('--reps', type=int, default=30)
    ap.add_argument('--procs', type=int, default=os.cpu_count() or 1)
    ap.add_argument('--no-nx', action='store_true', help='without the NX school frames')
    o = ap.parse_args(argv)
    os.makedirs(o.out, exist_ok=True)
    patching.GUARD_P = GUARD
    warnings.simplefilter('ignore')
    t0 = time.time()
    # the restricted pass is the reader's own on the whole frame
    from TwoDDetector import TwoDDetector
    test = np.random.default_rng(0).poisson(3.0, (60, 40)).astype(float)
    test[10, 10] += 500
    ref, _ = TwoDDetector('Pilatus').removeBadPix(test.copy(), iteration=1, factor=4)
    assert np.allclose(bad_pixel_pass(test, 1, 4.0)[0], ref)
    tasks = [(rep, hot, beam) for beam in BEAMS for hot in HOT for rep in range(o.reps)]
    res = A._pmap(replicate, tasks, o.procs, chunk=1)
    frames, joins, hots = [], [], []
    for (rep, hot, beam), (fr, jn, ht) in zip(tasks, res):
        for h in ht:
            h['beam'], h['hot_rate'] = beam, hot
        hots += ht
        for f in fr:
            f['_hot'], f['_rep'], f['_beam'] = hot, rep, beam
        frames += fr
        jn['_hot'], jn['_beam'] = hot, beam
        joins.append(jn)
    summ, jst = summarise(frames), join_stats(joins)
    nx = [] if o.no_nx else run_nx()
    write_csv(os.path.join(o.out, 'stats.csv'), summ)
    write_csv(os.path.join(o.out, 'join_pulls.csv'), jst)
    write_csv(os.path.join(o.out, 'hot_pixels.csv'), hots)
    if nx:
        write_csv(os.path.join(o.out, 'nx_school.csv'), nx)
    clean = [f for f in frames if f['hot'] == 0]
    nums = dict(reps=o.reps, frames=len(frames), seconds=round(time.time() - t0, 1), hot_pixels=len(hots),
                clean_margin={b: dict(f3=float(max(f['margin3'] for f in clean if f['_beam'] == b)),
                                      f10=float(max(f['margin10'] for f in clean if f['_beam'] == b))) for b in BEAMS},
                nx_margin=dict(f3=float(max(r['margin3'] for r in nx)), f10=float(max(r['margin10'] for r in nx)),
                               frame4=float(max(r['margin_frame4'] for r in nx))) if nx else None,
                clean_check=float(np.max([abs(f['none'] - f['clean']) / f['clean_err'] for f in frames if f['hot'] == 0])),
                nx={arm: dict(frames_changed=int(sum(r[arm + '_changed'] > 0 for r in nx)),
                              pixels=int(sum(r[arm + '_changed'] for r in nx)),
                              max_abs_dz=float(np.nanmax(np.abs([r[arm + '_dz'] for r in nx]))))
                    for arm in ARMS[1:]} if nx else None)
    with open(os.path.join(o.out, 'numbers.json'), 'w') as f:
        json.dump(nums, f, indent=1)
    nums['example'] = figures(summ, jst, nx, hots, frames, o.out)
    with open(os.path.join(o.out, 'numbers.json'), 'w') as f:
        json.dump(nums, f, indent=1)
    print(json.dumps(nums, indent=1))
    for r in summ:
        print('%(beam)-9s %(hot).1f %(qz)s %(arm)-7s bias %(bias_pct)+7.2f%% rms %(rms_pct)6.2f%% sd_z %(sd_z)6.2f '
              'false %(false_rate).3f loss %(false_loss_pct)+.2f%%' % r, ('removed %.2f' % r['removed']) if r['removed']
              is not None else '')
    for r in jst:
        print('join %(beam)-9s %(hot).1f %(arm)-7s pull SD %(pull_sd).2f mean %(mean_pull)+.2f (%(joins)d)' % r)


if __name__ == '__main__':
    main()
