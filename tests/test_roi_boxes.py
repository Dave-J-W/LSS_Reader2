"""The ROI boxes the close-up draws are the boxes the reduction sums (F71,
image_display.md §2.4 R2; invariant I38 in docs/physics_notes.md).

``lss_core.display.roi_boxes`` copies ``TwoDDetector.sumROI``'s arithmetic
(slit − 2, P12; int truncation of the background centres). Summing an image
over its boxes must give sumROI's values exactly, bit for bit, for any
slit, centre, offset and direction, also where a box runs off the frame.
Before 2026-11-24 the close-up burned its outlines into the pixels with
setROI's other arithmetic: the right background box shown was 2 px away
from the one summed (NX school, measured; image_display.md §1.5)."""
import numpy as np
import pytest

from TwoDDetector import TwoDDetector
from lss_core import display


def _detector(image):
    d = TwoDDetector('Pilatus')
    d.imageData = image
    d.errorData = np.sqrt(np.abs(image))
    return d


@pytest.mark.parametrize('seed', range(8))
def test_summing_over_the_drawn_boxes_gives_sumROIs_values(seed):
    rng = np.random.default_rng(seed)
    shape = (487, 195)
    image = rng.poisson(3.0, size=shape).astype(float) * rng.uniform(1e-6, 1e-4)
    d = _detector(image)
    off_frame = 0
    for _ in range(250):
        slit = (int(rng.integers(1, 40)), int(rng.integers(1, 40)))
        cen = (int(rng.integers(-5, shape[1] + 5)), int(rng.integers(-5, shape[0] + 5)))
        direction = str(rng.choice(['H', 'V', 'h']))           # sumROI: anything but 'H' is vertical
        bg = None if rng.random() < 0.1 else float(rng.uniform(0.0, 4.0))
        values = d.sumROI(slit=list(slit), cen=list(cen), dir=direction, bg=bg)
        boxes = display.roi_boxes(slit, cen, bg, direction)
        assert len(boxes) == (3 if bg is not None else 1)
        for k, (_, b) in enumerate(boxes):
            assert display.box_sum(image, b) == values[2 * k]          # exactly, not approximately
            on = display.box_on_frame(b, shape)
            drawn = 0.0 if on is None else np.sum(image[on[0]:on[1], on[2]:on[3]])
            assert drawn == values[2 * k]                               # the pixels outlined are those summed
            off_frame += display.box_leaves_frame(b, shape)
    assert off_frame > 20                                               # the frame's edges were exercised


def test_a_slit_below_one_is_refused_by_both():
    d = _detector(np.ones((40, 40)))
    with pytest.raises(IndexError):
        d.sumROI(slit=[0, 11], cen=[20, 20])
    with pytest.raises(ValueError):
        display.roi_boxes((0, 11), (20, 20))


def test_the_nx_school_boxes_and_the_old_burned_borders():
    """NX school scan 7 frame 0 (image_display.md §1.5): slit 21,11, BG
    offset 0.5° at 551 mm, direction H, centre column 47. sumROI sums the
    background boxes centred at columns 21 and 72; setROI burned borders
    centred at 20 and 74. The signal box border matched (37–57)."""
    slit, cen = (21, 11), (47, 53)
    bg = 0.5 * 551.0 * np.pi / 180 / 0.172 / slit[0]
    boxes = dict(display.roi_boxes(slit, cen, bg, 'H'))
    assert boxes['signal'] == (48, 59, 37, 58)                         # 11 rows, 21 columns (odd slit: s)
    assert [(b[2] + b[3] - 1) / 2 for b in (boxes['left'], boxes['right'])] == [21, 72]
    d = _detector(np.ones((487, 195)))
    d.setROI(d.imageData, d.errorData, slit=list(slit), cen=list(cen), bg=bg, dir='H')
    assert (d.bglcen, d.bgrcen) == (20, 74)                            # what the burned strip showed


def test_even_slits_and_vertical_backgrounds():
    """An even slit s sums s − 1 pixels (P12); 'V' (any direction but 'H')
    puts the background boxes above ('up', higher rows) and below."""
    boxes = dict(display.roi_boxes((20, 10), (100, 200), 2.0, 'V'))
    assert boxes['signal'] == (196, 205, 91, 110)                      # 9 rows, 19 columns
    assert boxes['up'] == (212, 221, 91, 110) and boxes['down'] == (180, 189, 91, 110)
    # an offset of one slit puts the boxes 8 px apart (slit - 2), less than their 9 rows: they overlap
    near = display.roi_boxes((20, 10), (100, 200), 1.0, 'V')
    assert dict(near)['up'][0] < dict(near)['signal'][1]
    cues = display.roi_cues(np.ones((400, 200)), None, near, direction='V')
    assert sorted(c['text'] for c in cues if c['key'] == 'gap') == ['down bg overlaps signal',
                                                                    'up bg overlaps signal']


def test_a_box_that_starts_before_the_frame_sums_nothing():
    """numpy reads a slice with a negative start from the far end: a
    background box starting before column 0 sums nothing (or another
    region), which the close-up says (a 'frame' cue)."""
    image = np.ones((60, 40))
    boxes = display.roi_boxes((11, 5), (8, 30), 1.2, 'H')
    left = dict(boxes)['left']
    assert left[2] < 0 < left[3]
    assert display.box_sum(image, left) == 0.0
    assert display.box_on_frame(left, image.shape) is None
    cues = display.roi_cues(image, None, boxes, kind='ref')
    assert [c['key'] for c in cues if c['key'] == 'frame'] == ['frame']
    assert 'none of it is summed' in [c for c in cues if c['key'] == 'frame'][0]['reason']
