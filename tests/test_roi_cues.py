"""The ROI close-up's region, scale and cues (F71, image_display.md §2.4
R1, R5; lss_core.display). Display only: no sum changes.

Owner, 2026-11-23 (Q-IMG-7): cues at 25 % of the half-width off centre,
more than 1 % of the integral on or beyond the box edge, and a background
box within 2 px of the signal box. The rest (3 σ before position cues are
judged, 2 px "beyond", the local baseline across the background direction,
2 σ on the clipped part) are assumptions, documented in display.py."""
import numpy as np
import pytest

from lss_core import display

SHAPE = (120, 160)
SLIT = (21, 11)                     # 21 columns x 11 rows summed (odd slits: s pixels)


def _frame(col=80.0, row=60.0, sc=2.0, sr=1.0, amp=1000.0, flat=1.0):
    r, c = np.mgrid[0:SHAPE[0], 0:SHAPE[1]]
    return flat + amp * np.exp(-(c - col) ** 2 / 2 / sc ** 2 - (r - row) ** 2 / 2 / sr ** 2)


def _sums(img, boxes):
    v = [display.box_sum(img, b) for _, b in boxes]
    net = v[0] - (v[1] + v[2]) / 2.0
    return (v[0], np.sqrt(v[0]), v[1], np.sqrt(v[1]), v[2], np.sqrt(v[2]), net, np.sqrt(v[0] + (v[1] + v[2]) / 4))


def _cues(img, bg=1.4, cen=(80, 60), direction='H', **kw):
    boxes = display.roi_boxes(SLIT, cen, bg, direction)
    return display.roi_cues(img, np.sqrt(img), boxes, _sums(img, boxes), direction, **kw), boxes


def _keys(cues):
    return sorted(c['key'] for c in cues)


def test_a_centred_beam_well_inside_the_box_has_no_cue():
    cues, boxes = _cues(_frame())
    assert cues == []
    gap = dict(boxes)['signal'][2] - dict(boxes)['left'][3]
    assert gap > display.BG_GAP_PX                                    # 4 px between the boxes


def test_off_centre_beyond_a_quarter_of_the_half_width():
    """Half-width 10.5 columns: the cue from 2.6 px."""
    assert _keys(_cues(_frame(col=82.0))[0]) == []                    # 2 px: no cue
    cues = _cues(_frame(col=84.0))[0]                                # 4 px
    assert _keys(cues) == ['centre']
    assert cues[0]['text'].startswith('off centre +') and '(col)' in cues[0]['text']
    assert '25 %' in cues[0]['reason'] and 'Q-IMG-7' in cues[0]['reason']
    rows = _cues(_frame(row=62.0))[0]                                 # half-height 5.5: 2 rows is beyond 1.4
    assert [c['text'][-5:] for c in rows if c['key'] == 'centre'] == ['(row)']


def test_clipped_when_more_than_one_per_cent_lies_on_or_beyond_the_edge():
    """A beam of σ = 3 rows in an 11-row box: 22 % on the edge rows or the 2 rows past them."""
    assert 'clipped' not in _keys(_cues(_frame(sr=1.0))[0])
    cues = [c for c in _cues(_frame(sr=3.0))[0] if c['key'] == 'clipped']
    assert len(cues) == 1 and cues[0]['text'].endswith('(rows)')
    frac = float(cues[0]['text'].split()[1])
    assert 10.0 < frac < 40.0
    wide = [c for c in _cues(_frame(sc=6.0))[0] if c['key'] == 'clipped']   # σ 6 columns in 21
    assert [c['text'][-9:] for c in wide] == ['(columns)']


def test_far_intensity_is_not_the_beams_tail():
    """A second spot 6 rows below the box (the direct beam at low Qz on NX)
    is not clipping: only the edge pixels and the 2 px past them count, on
    the profile's own baseline across the background direction."""
    img = _frame() + _frame(row=48.0, amp=500.0, flat=0.0)
    assert 'clipped' not in _keys(_cues(img)[0])


def test_a_weak_peak_is_not_judged_for_position():
    rng = np.random.default_rng(1)
    img = rng.poisson(50.0, size=SHAPE).astype(float)                # noise only
    cues = _cues(img)[0]
    assert not {'centre', 'clipped'} & set(_keys(cues))


def test_a_background_box_two_pixels_or_less_from_the_signal_box():
    """sumROI's centres are int(80 ∓ bg × 19), truncated towards zero: at bg
    1.25 the left box is 3 px from the signal box and the right one 2 px."""
    for bg, gaps in ((1.15, (1, 0)), (1.2, (2, 1)), (1.25, (3, 2)), (1.3, (4, 3))):
        cues, boxes = _cues(_frame(), bg=bg)
        b = dict(boxes)
        assert (b['signal'][2] - b['left'][3], b['right'][2] - b['signal'][3]) == gaps
        texts = sorted(c['text'] for c in cues if c['key'] == 'gap')
        assert texts == sorted('%s bg %d px from signal' % (n, g) for n, g in zip(('left', 'right'), gaps)
                               if g <= display.BG_GAP_PX), (bg, texts)
    cues, _ = _cues(_frame(), bg=0.8)
    assert sorted(c['text'] for c in cues if c['key'] == 'gap') == ['left bg overlaps signal',
                                                                     'right bg overlaps signal']


def test_saturation_and_direct_beam_in_a_box():
    img = _frame()
    soft = np.zeros(SHAPE, bool)
    hard = np.zeros(SHAPE, bool)
    soft[60, 80] = hard[60, 80] = True
    soft[60, 81] = True
    soft[5, 5] = True                                                  # outside every box: not counted
    cues, boxes = _cues(img, saturated=(soft, hard))
    sat = [c for c in cues if c['key'] == 'saturation']
    assert len(sat) == 1 and sat[0]['level'] == 'stop' and sat[0]['text'] == '1 px > 1.5e5 cps: absorber needed'
    left = dict(boxes)['left']
    beam = ((left[0] + left[1] - 1) / 2.0, (left[2] + left[3] - 1) / 2.0)
    cues, _ = _cues(img, beam=beam)
    assert [c['text'] for c in cues if c['key'] == 'beam'] == ['direct beam in left box']
    cues, _ = _cues(img, beam=beam, kind='direct')                     # a direct-beam frame: its beam is the point
    assert 'beam' not in _keys(cues)
    cues, _ = _cues(img, beam=(10.0, 10.0))
    assert 'beam' not in _keys(cues)


def test_a_vertical_background_and_its_cues():
    img = _frame(sr=1.0)
    cues, boxes = _cues(img, bg=2.0, direction='V')
    assert [n for n, _ in boxes] == ['signal', 'up', 'down'] and cues == []


def test_the_region_holds_every_box_with_a_margin_and_stays_on_the_frame():
    boxes = display.roi_boxes(SLIT, (80, 60), 1.4, 'H')
    r0, r1, c0, c1 = display.roi_region(boxes, SHAPE, 'H')
    for _, b in boxes:
        assert r0 < b[0] and b[1] < r1 and c0 < b[2] and b[3] < c1
    sig = dict(boxes)['signal']
    assert sig[0] - r0 == 11 and c0 == dict(boxes)['left'][2] - 10    # one box height; half a box width
    edge = display.roi_boxes(SLIT, (12, 6), 1.4, 'H')
    r0, r1, c0, c1 = display.roi_region(edge, SHAPE, 'H')
    assert r0 == 0 and c0 == 0                                         # clipped to the frame
    assert display.roi_region(display.roi_boxes(SLIT, (500, 500), 1.4, 'H'), SHAPE) is None


def test_the_close_ups_scale_comes_from_the_signal_box():
    img = _frame()
    img[100, 10] = 1e6                                                 # a hot pixel far from the boxes
    boxes = display.roi_boxes(SLIT, (80, 60), 1.4, 'H')
    region = display.roi_region(boxes, SHAPE, 'H')
    lo, hi = display.roi_limits(img, boxes, region, log=True)
    assert 0 < lo <= 1.0 and 900 < hi <= 1001                          # every count shows; the peak, not the hot pixel
    lo, hi = display.roi_limits(img, boxes, region, log=False)
    assert lo == pytest.approx(1.0) and hi < 1001


def test_the_profiles_are_the_sums_across_the_signal_box():
    img = _frame()
    boxes = display.roi_boxes(SLIT, (80, 60), 1.4, 'H')
    region = display.roi_region(boxes, SHAPE, 'H')
    cols, colsum, rows, rowsum = display.roi_profiles(img, boxes, region)
    sig = dict(boxes)['signal']
    k = list(cols).index(sig[2])
    assert np.sum(colsum[k:k + sig[3] - sig[2]]) == pytest.approx(display.box_sum(img, sig))
    j = list(rows).index(sig[0])
    assert np.sum(rowsum[j:j + sig[1] - sig[0]]) == pytest.approx(display.box_sum(img, sig))


def test_the_numbers_text_is_short():
    t = display.roi_numbers_text((4.05e5, 6.2e2, 1.2e2, 11.0, 1.3e2, 11.4, 4.0488e5, 6.3e2))
    assert t.splitlines()[0].startswith('S 4.050e+05') and 'net 4.0488e+05' in t and '(0.16 %)' in t
    assert len(t.splitlines()) == 2
