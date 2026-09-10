import io

import numpy as np
from PIL import Image

from app.color import delta_e, rgb_to_lab
from app.materials import select_canvas
from app.models import PatternOptions
from app.processing import _background_mask, _backstitch, _proper_intersection, generate_pattern
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


def test_background_mask_only_removes_similar_area_connected_to_edge():
    image = np.full((7, 7, 3), 247, dtype=np.uint8)
    image[2:5, 2:5] = [190, 30, 40]
    image[3, 3] = [247, 247, 247]
    mask = _background_mask(image, np.full((7, 7), 255, dtype=np.uint8), 8)

    assert mask[0, 0]
    assert not mask[2, 2]
    assert not mask[3, 3]


def test_transparent_background_creates_no_background_stitches():
    image = Image.new("RGBA", (16, 16), (255, 255, 255, 0))
    for y in range(5, 11):
        for x in range(5, 11):
            image.putpixel((x, y), (200, 25, 45, 255))
    data = io.BytesIO()
    image.save(data, format="PNG")

    pattern = generate_pattern(
        data.getvalue(),
        PatternOptions(width=16, max_colors=4, remove_background=True,
                       blends=False, half_cross=False, backstitch=False),
    )

    assert pattern["metrics"]["background_removed"] > 0
    assert len(pattern["stitches"]) < 16 * 16
    assert all(not (stitch["x"] == 0 or stitch["y"] == 0) for stitch in pattern["stitches"])


def test_background_removal_does_not_change_remaining_stitches():
    image = Image.new("RGB", (18, 18), (245, 242, 235))
    for y in range(4, 14):
        for x in range(5, 13):
            image.putpixel((x, y), (35 + x * 8, 55 + y * 5, 150))
    data = io.BytesIO()
    image.save(data, format="PNG")
    common = dict(width=18, max_colors=6, backstitch=False)

    complete = generate_pattern(data.getvalue(), PatternOptions(**common, remove_background=False))
    cut_out = generate_pattern(data.getvalue(), PatternOptions(**common, remove_background=True))
    complete_at = {(stitch["x"], stitch["y"]): stitch for stitch in complete["stitches"]}

    assert len(cut_out["stitches"]) < len(complete["stitches"])
    for stitch in cut_out["stitches"]:
        original = complete_at[(stitch["x"], stitch["y"])]
        assert (stitch["primary_color"], stitch["secondary_color"], stitch["stitch_type"], stitch["symbol"]) == (
            original["primary_color"], original["secondary_color"], original["stitch_type"], original["symbol"]
        )


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
