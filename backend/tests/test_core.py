import numpy as np

from app.color import delta_e, rgb_to_lab
from app.materials import select_canvas
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
