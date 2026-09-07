import numpy as np

from app.color import delta_e, rgb_to_lab
from app.materials import select_canvas
from app.processing import _backstitch, _proper_intersection
from app.regions import build_regions, components


def test_rgb_lab_and_delta_e_identity():
    lab = rgb_to_lab(np.array([[[255, 0, 0]]], dtype=np.uint8))
    assert lab.shape == (1, 1, 3)
    assert float(delta_e(lab, lab)[0, 0]) == 0.0


def test_connected_components():
    values = np.array([[1, 1, 2], [1, 2, 2], [3, 3, 2]])
    assert sorted(map(len, components(values))) == [2, 3, 4]


def test_region_keeps_adjacent_stitch_types_together():
    stitches = [
        {"id": "a", "x": 0, "y": 0, "primary_color": "310", "secondary_color": None,
         "stitch_type": "full"},
        {"id": "b", "x": 1, "y": 0, "primary_color": "310", "secondary_color": None,
         "stitch_type": "half_forward"},
    ]
    regions = build_regions(stitches, 2, 1)
    assert len(regions) == 1
    assert regions[0]["stitch_type"] == "mixed"


def test_canvas_matches_source_background():
    assert select_canvas([252, 250, 246], None)["id"] == "white"
    assert select_canvas([20, 23, 29], None)["id"] == "black"


def test_backstitch_has_no_duplicate_or_crossing_segments():
    rgbs = np.array([[255, 255, 255], [220, 45, 75], [24, 24, 28]], dtype=np.uint8)
    labs = rgb_to_lab(rgbs[None, :, :])[0]
    palette = [{"id": str(index), "rgb": rgb.tolist(), "lab": lab.tolist()}
               for index, (rgb, lab) in enumerate(zip(rgbs, labs))]
    indices = np.zeros((24, 24), dtype=np.int16)
    indices[4:20, 4:20] = 1
    indices[8:16, 10:13] = 2
    image = rgbs[indices]
    segments = _backstitch(image, indices, np.ones(indices.shape, dtype=np.float32), palette, True)
    lines = [((s["from_x"], s["from_y"]), (s["to_x"], s["to_y"])) for s in segments]

    assert lines
    assert len(lines) == len({tuple(sorted(line)) for line in lines})
    assert not any(_proper_intersection(*first, *second)
                   for index, first in enumerate(lines) for second in lines[index+1:])
