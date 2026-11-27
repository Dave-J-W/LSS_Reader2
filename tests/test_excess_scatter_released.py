"""The released (pre-2019) reflectivity extract behind C63's real-data figures R1-R4 is self-consistent."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))
import excess_scatter as E                 # noqa: E402
import excess_scatter_released as R        # noqa: E402


def test_the_frame_boxes_sum_to_the_readers_numbers():
    meta = json.load(open(os.path.join(R.DATA, 'frames.json'), encoding='utf-8'))['frames']
    px = {}
    for r in R._read('frames.csv'):
        px.setdefault(int(r['frame']), []).append((int(r['row']), int(r['col']), float(r['counts'])))
    for m in meta:
        img = np.zeros(m['shape'])
        for y, x, v in px[m['frame']]:
            img[y, x] = v
        b = R._boxes(m['centre'], m['slit'], m['bg_offset_px'])
        assert abs(img[b['signal']].sum() - m['signal']) <= 0.5
        assert abs(img[b['left background']].sum() - m['left_bg']) <= 0.5
        assert abs(img[b['right background']].sum() - m['right_bg']) <= 0.5
        bg = 0.5 * (m['left_bg'] + m['right_bg'])
        assert abs((m['signal'] - bg) / m['monitor'] - m['net']) <= 1e-6 * max(abs(m['net']), 1e-12) + 1e-9


def test_the_windows_of_the_shown_series_are_those_of_windows_csv():
    win = R.load_windows()
    for lab, scans in R.load_series().items():
        mine = []
        for q, y, s, c in scans:
            t = E.curvature_terms(q, y, s)
            if t is not None:
                mine += list(t['d'])
        theirs = win['d'][win['series'] == lab]
        assert len(mine) == len(theirs), lab
        # |d|: the sign of a window's weights is arbitrary (SVD); Qz is rounded to 7 decimals in the CSV
        assert np.allclose(np.sort(np.abs(mine)), np.sort(np.abs(theirs)), rtol=1e-4, atol=2e-6), lab   # y and σ carry 7 significant figures


def test_the_big_windows_at_the_minimum_are_counted_as_numbers_json_says():
    m = json.load(open(os.path.join(R.DATA, 'numbers.json'), encoding='utf-8'))['minimum']
    win = R.load_windows()
    big = np.abs(win['d'] / win['sd']) > 10
    near = np.abs(win['q'] - m['minimum_qz']) <= m['band'] + 1e-9
    assert (int(np.sum(big & near)), int(np.sum(big))) == (m['beyond10_near'], m['beyond10_all'])
    assert abs(np.mean(near) - m['share_of_windows_in_band']) < 1e-12


def test_the_extract_is_anonymous_and_small():
    head = open(os.path.join(R.DATA, 'series.csv'), encoding='utf-8').readline().strip().split(',')
    assert head == ['series', 'scan', 'qz', 'y', 'sigma', 'counts']
    scans = {r['scan'] for r in R._read('series.csv')}
    assert max(int(s) for s in scans) <= 7                          # an index within its series, not a scan number
    assert set(R.load_series()) == {'A', 'B', 'C', 'D'}
    assert len(json.load(open(os.path.join(R.DATA, 'frames.json'), encoding='utf-8'))['frames']) == 2
