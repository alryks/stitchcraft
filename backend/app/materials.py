import math
from collections import Counter

from .canvas import CANVASES, needle_for_count


def select_canvas(background_rgb: list[float], requested: str | None) -> dict:
    if requested:
        found = next((c for c in CANVASES if c["id"] == requested), None)
        if found:
            return found
    # The edge median is a robust estimate of the source background. Matching
    # it makes the fabric extend the image naturally and avoids dark surprises.
    def distance(canvas: dict) -> float:
        return sum((a-b) ** 2 for a, b in zip(background_rgb, canvas["rgb"])) ** 0.5
    return min(CANVASES, key=distance)


def calculate_materials(stitches: list[dict], palette_lookup: dict[str, dict], width: int, height: int,
                        count: int, strands: int, canvas: dict) -> dict:
    cell_mm = 25.4 / count
    margin_mm = 80
    usage = Counter()
    for stitch in stitches:
        factor = 2.15 if stitch["stitch_type"] == "full" else 1.15
        secondary = stitch.get("secondary_color")
        usage[stitch["primary_color"]] += cell_mm * factor * (1 if secondary else strands)
        if secondary:
            usage[secondary] += cell_mm * factor
    threads = []
    for color_id, millimetres in usage.most_common():
        metres = millimetres / 1000 * 1.18
        color = palette_lookup[color_id]
        threads.append({"id": color_id, "name": color["name"], "hex": color["hex"],
                        "metres": round(metres, 2), "skeins": max(1, math.ceil(metres / 8.0))})
    return {
        "canvas": {**canvas, "width_mm": round(width * cell_mm + margin_mm),
                   "height_mm": round(height * cell_mm + margin_mm), "count": count},
        "needle": {"type": "Гобеленовая", "size": needle_for_count(count)},
        "threads": threads,
        "total_thread_m": round(sum(t["metres"] for t in threads), 2),
    }
