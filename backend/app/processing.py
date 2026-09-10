from __future__ import annotations

import io
import math
from collections import defaultdict

import cv2
import numpy as np
from PIL import Image, ImageOps
from skimage.metrics import structural_similarity

from .canvas import CANVASES
from .color import apply_blends, delta_e, match_palette, rgb_to_lab
from .materials import calculate_materials, select_canvas
from .models import PatternOptions
from .palettes import load_palette
from .regions import build_regions, components, reduce_confetti

SYMBOLS = list("●◆■▲✦✚✖◇□△○⊕⊗♠♣♥☀☂☘☯") + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def _dimensions(image: Image.Image, options: PatternOptions) -> tuple[int, int]:
    aspect = image.height / image.width
    if options.size_unit == "cm" and options.physical_size:
        stitches = max(8, round(options.physical_size / 2.54 * options.canvas_count))
        width = stitches if options.size_axis == "width" else round(stitches / aspect)
        height = round(stitches * aspect) if options.size_axis == "width" else stitches
    elif options.height and not options.width:
        height, width = options.height, round(options.height / aspect)
    else:
        width = options.width or 80
        height = options.height or round(width * aspect)
    scale = min(1.0, 220 / max(width, height))
    return max(8, round(width * scale)), max(8, round(height * scale))


def _prepare_image(data: bytes, width: int, height: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    image = Image.open(io.BytesIO(data))
    image = ImageOps.exif_transpose(image).convert("RGBA")
    alpha = np.asarray(image.getchannel("A").resize((width, height), Image.Resampling.LANCZOS), dtype=np.uint8)
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    background.alpha_composite(image)
    rgb = background.convert("RGB")
    reduced = np.asarray(rgb.resize((width, height), Image.Resampling.LANCZOS), dtype=np.uint8)
    soft = cv2.bilateralFilter(reduced, 5, 28, 28)
    gray = cv2.cvtColor(reduced, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 55, 135).astype(np.float32) / 255.0
    local = cv2.Laplacian(gray, cv2.CV_32F)
    local = np.abs(local)
    local /= max(1.0, float(local.max()))
    importance = np.clip(edges * 0.72 + local * 0.28, 0, 1)
    # Preserve significant contours before quantisation with a restrained unsharp pass.
    sharpened = cv2.addWeighted(reduced, 1.22, soft, -0.22, 0)
    mask = importance[..., None]
    prepared = np.clip(reduced * (1-mask*0.24) + sharpened * (mask*0.24), 0, 255).astype(np.uint8)
    return prepared, importance, alpha


def _background_mask(image: np.ndarray, alpha: np.ndarray, tolerance: float) -> np.ndarray:
    """Find background-like cells connected to the outside edge of the image."""
    border = np.concatenate((image[0], image[-1], image[1:-1, 0], image[1:-1, -1]))
    background_lab = rgb_to_lab(np.median(border, axis=0)[None, None, :])[0, 0]
    distance = delta_e(rgb_to_lab(image), background_lab[None, None, :])
    candidates = (distance <= tolerance) | (alpha < 128)
    count, labels = cv2.connectedComponents(candidates.astype(np.uint8), connectivity=8)
    if count <= 1:
        return np.zeros(candidates.shape, dtype=bool)
    border_labels = np.unique(np.concatenate((labels[0], labels[-1], labels[1:-1, 0], labels[1:-1, -1])))
    border_labels = border_labels[border_labels != 0]
    return np.isin(labels, border_labels)


def _quantize_lab(
    image: np.ndarray, colors: int, included: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    lab = rgb_to_lab(image)
    pixels = lab[included].astype(np.float32) if included is not None else lab.reshape(-1, 3).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 35, 0.15)
    cv2.setRNGSeed(42)
    _, labels, centers = cv2.kmeans(pixels, colors, None, criteria, 4, cv2.KMEANS_PP_CENTERS)
    if included is None:
        quantized = centers[labels.ravel()].reshape(lab.shape)
    else:
        quantized = lab.copy()
        quantized[included] = centers[labels.ravel()]
    return lab, quantized


GridPoint = tuple[int, int]
GridEdge = tuple[GridPoint, GridPoint]


def _edge_trails(edges: dict[GridEdge, float]) -> list[tuple[list[GridPoint], float]]:
    """Join a planar set of unit grid edges into maximal, non-repeating trails."""
    neighbours: dict[GridPoint, set[GridPoint]] = defaultdict(set)
    for a, b in edges:
        neighbours[a].add(b)
        neighbours[b].add(a)

    unused = set(edges)
    trails = []

    def take(start: GridPoint, first: GridPoint) -> tuple[list[GridPoint], float]:
        points = [start, first]
        key = tuple(sorted((start, first)))
        score = edges[key]
        unused.discard(key)
        previous, current = start, first
        while len(neighbours[current]) == 2:
            following = next(point for point in neighbours[current] if point != previous)
            key = tuple(sorted((current, following)))
            if key not in unused:
                break
            points.append(following)
            score += edges[key]
            unused.remove(key)
            previous, current = current, following
        return points, score

    # Junctions and endpoints split the graph into unambiguous trails.
    for start in sorted(point for point, adjacent in neighbours.items() if len(adjacent) != 2):
        for first in sorted(neighbours[start]):
            key = tuple(sorted((start, first)))
            if key in unused:
                trails.append(take(start, first))

    # Components with degree two everywhere are closed loops.
    while unused:
        start, first = next(iter(unused))
        trails.append(take(start, first))
    return trails


def _proper_intersection(a: GridPoint, b: GridPoint, c: GridPoint, d: GridPoint) -> bool:
    if {a, b} & {c, d}:
        return False

    def orient(p, q, r):
        return (q[0]-p[0]) * (r[1]-p[1]) - (q[1]-p[1]) * (r[0]-p[0])

    return orient(a, b, c) * orient(a, b, d) < 0 and orient(c, d, a) * orient(c, d, b) < 0


def _suppress_parallel_edges(
    edges: dict[GridEdge, float], radius: int = 2,
) -> dict[GridEdge, float]:
    """Keep one response across a thick source line instead of tracing both sides."""
    result = {}
    for edge, score in edges.items():
        (x1, y1), (x2, y2) = edge
        competitors = []
        if x1 == x2:
            for offset in range(-radius, radius + 1):
                candidate = tuple(sorted(((x1 + offset, y1), (x2 + offset, y2))))
                if candidate in edges:
                    competitors.append((edges[candidate], candidate))
        else:
            for offset in range(-radius, radius + 1):
                candidate = tuple(sorted(((x1, y1 + offset), (x2, y2 + offset))))
                if candidate in edges:
                    competitors.append((edges[candidate], candidate))
        best_score = max(value for value, _ in competitors)
        best_edge = min(candidate for value, candidate in competitors if value >= best_score-1e-6)
        if score >= best_score-1e-6 and edge == best_edge:
            result[edge] = score
    return result


def _backstitch(
    image: np.ndarray, indices: np.ndarray, importance: np.ndarray,
    palette: list[dict], enabled: bool, foreground: np.ndarray | None = None,
) -> list[dict]:
    if not enabled:
        return []

    height, width = indices.shape
    palette_labs = np.asarray([color["lab"] for color in palette], dtype=np.float32)
    border = np.concatenate((image[0], image[-1], image[1:-1, 0], image[1:-1, -1]))
    background_lab = rgb_to_lab(np.median(border, axis=0)[None, None, :])[0, 0]
    background_distance = delta_e(palette_labs[:, None, :], background_lab[None, None, :]).reshape(-1)

    vertical_contrast = delta_e(palette_labs[indices[:, :-1]], palette_labs[indices[:, 1:]])
    horizontal_contrast = delta_e(palette_labs[indices[:-1, :]], palette_labs[indices[1:, :]])
    vertical_active = np.ones(vertical_contrast.shape, dtype=bool)
    horizontal_active = np.ones(horizontal_contrast.shape, dtype=bool)
    if foreground is not None:
        vertical_active = foreground[:, :-1] | foreground[:, 1:]
        horizontal_active = foreground[:-1, :] | foreground[1:, :]
    positive = np.concatenate((vertical_contrast[(vertical_contrast > 0) & vertical_active],
                               horizontal_contrast[(horizontal_contrast > 0) & horizontal_active]))
    if not len(positive):
        return []

    # A relative threshold adapts to photographs while the floor prevents subtle
    # quantisation bands from being outlined in simple artwork.
    contrast_cutoff = max(14.0, float(np.quantile(positive, 0.62)))
    importance_cutoff = max(0.16, float(np.quantile(importance, 0.58)))
    edge_support = cv2.dilate(importance, np.ones((3, 3), dtype=np.uint8))
    edges: dict[GridEdge, float] = {}

    def add_edge(a, b, contrast, edge_strength, first_index, second_index, active):
        if not active:
            return
        if contrast < contrast_cutoff or edge_strength < importance_cutoff:
            return
        # Variations close to the border median are usually paper, sky, or scan
        # texture. They should not compete with the subject's silhouette.
        if background_distance[first_index] < 24 and background_distance[second_index] < 24:
            return
        edges[tuple(sorted((a, b)))] = float(contrast * (0.55 + edge_strength))

    for y in range(height):
        for x in range(width-1):
            add_edge(
                (x + 1, y), (x + 1, y + 1), vertical_contrast[y, x],
                max(edge_support[y, x], edge_support[y, x + 1]),
                indices[y, x], indices[y, x + 1],
                foreground is None or foreground[y, x] or foreground[y, x + 1],
            )
    for y in range(height-1):
        for x in range(width):
            add_edge(
                (x, y + 1), (x + 1, y + 1), horizontal_contrast[y, x],
                max(edge_support[y, x], edge_support[y + 1, x]),
                indices[y, x], indices[y + 1, x],
                foreground is None or foreground[y, x] or foreground[y + 1, x],
            )

    if not edges:
        return []

    edges = _suppress_parallel_edges(edges)

    # Discard isolated fragments, then rank coherent trails by length and contrast.
    trails = [(points, score) for points, score in _edge_trails(edges)
              if len(points) >= (9 if points[0] == points[-1] else 4)]
    trails.sort(key=lambda item: item[1] * math.sqrt(len(item[0])), reverse=True)
    darkest = min(palette, key=lambda c: sum(c["rgb"]))["id"]
    accepted: list[GridEdge] = []
    accepted_keys: set[GridEdge] = set()

    for points, _ in trails[:36]:
        closed = points[0] == points[-1]
        curve = np.asarray(points, dtype=np.int32).reshape(-1, 1, 2)
        simplified = [
            tuple(map(int, point))
            for point in cv2.approxPolyDP(curve, 0.72, closed).reshape(-1, 2)
        ]
        if closed and simplified and simplified[0] != simplified[-1]:
            simplified.append(simplified[0])
        candidate = list(zip(simplified, simplified[1:]))
        crosses = any(_proper_intersection(a, b, c, d) for a, b in candidate for c, d in accepted)
        chosen = list(zip(points, points[1:])) if crosses else candidate
        for a, b in chosen:
            key = tuple(sorted((a, b)))
            if a != b and key not in accepted_keys:
                accepted.append((a, b))
                accepted_keys.add(key)
        if len(accepted) >= 220:
            break

    return [{"from_x": a[0], "from_y": a[1], "to_x": b[0], "to_y": b[1], "color": darkest}
            for a, b in accepted[:220]]


def generate_pattern(data: bytes, options: PatternOptions) -> dict:
    source = Image.open(io.BytesIO(data))
    width, height = _dimensions(source, options)
    prepared, importance, alpha = _prepare_image(data, width, height)
    border = np.concatenate((prepared[0], prepared[-1], prepared[1:-1, 0], prepared[1:-1, -1]))
    canvas = select_canvas(np.median(border, axis=0).tolist(), options.canvas_color)
    background = (_background_mask(prepared, alpha, options.background_tolerance)
                  if options.remove_background else np.zeros((height, width), dtype=bool))
    foreground = ~background
    foreground_count = int(np.sum(foreground))
    palette = load_palette(options.palette)
    palette_labs = np.asarray([c["lab"] for c in palette], dtype=np.float32)
    original_lab, quantized_lab = _quantize_lab(prepared, min(options.max_colors, width * height))
    indices, errors = match_palette(quantized_lab, palette)
    indices, removed = reduce_confetti(
        indices, original_lab, palette_labs, importance, options.min_component_size,
    )
    errors = delta_e(original_lab, palette_labs[indices])
    secondary = np.full(indices.shape, -1, dtype=np.int16)
    if options.blends:
        secondary, errors = apply_blends(original_lab, indices, errors, palette)
        blend_keys = indices * (len(palette) + 1) + secondary + 1
        for part in components(blend_keys):
            x, y = part[0]
            if secondary[y, x] >= 0 and len(part) < options.min_component_size:
                for px, py in part:
                    secondary[py, px] = -1
        errors = delta_e(original_lab, palette_labs[indices])
        blended = secondary >= 0
        if np.any(blended):
            blend_rgb = (np.asarray([palette[idx]["rgb"] for idx in indices[blended]], dtype=np.float32)
                         + np.asarray([palette[idx]["rgb"] for idx in secondary[blended]], dtype=np.float32)) / 2
            errors[blended] = delta_e(original_lab[blended], rgb_to_lab(blend_rgb))

    symbol_indices = sorted(set(indices.ravel().tolist()) | {int(v) for v in secondary.ravel() if v >= 0})
    used_indices = sorted(set(indices[foreground].tolist()) | {int(v) for v in secondary[foreground] if v >= 0})
    symbols = {idx: SYMBOLS[pos % len(SYMBOLS)] for pos, idx in enumerate(symbol_indices)}
    edge_cutoff = max(0.68, float(np.quantile(importance, 0.88)))
    stitches = []
    for y in range(height):
        for x in range(width):
            if background[y, x]:
                continue
            primary_index = int(indices[y, x]); secondary_index = int(secondary[y, x])
            stitch_type = "full"
            if options.half_cross and importance[y, x] >= edge_cutoff and (x + y) % 3 == 0:
                stitch_type = "half_forward" if (x + y) % 2 == 0 else "half_backward"
            stitches.append({
                "id": f"s{x}_{y}", "x": x, "y": y,
                "primary_color": palette[primary_index]["id"],
                "secondary_color": palette[secondary_index]["id"] if secondary_index >= 0 else None,
                "stitch_type": stitch_type, "region_id": None,
                "importance": round(float(importance[y, x]), 3),
                "symbol": symbols[primary_index],
            })
    regions = build_regions(stitches, width, height)
    used_colors = [{**palette[idx], "symbol": symbols[idx]} for idx in used_indices]
    lookup = {c["id"]: c for c in palette}
    materials = calculate_materials(stitches, lookup, width, height, options.canvas_count, options.strands, canvas)
    rendered = np.empty((height, width, 3), dtype=np.uint8)
    rendered[:] = canvas["rgb"]
    rendered[foreground] = np.asarray([palette[idx]["rgb"] for idx in indices[foreground]], dtype=np.uint8)
    min_side = min(width, height)
    ssim = structural_similarity(prepared, rendered, channel_axis=2, data_range=255,
                                 win_size=min(7, min_side if min_side % 2 else min_side-1))
    return {
        "width": width, "height": height,
        "physical_width_mm": round(width * 25.4 / options.canvas_count, 1),
        "physical_height_mm": round(height * 25.4 / options.canvas_count, 1),
        "options": options.model_dump(), "stitches": stitches, "regions": regions,
        "backstitch": _backstitch(prepared, indices, importance, palette, options.backstitch, foreground),
        "colors": used_colors, "canvas_options": CANVASES, "materials": materials,
        "plans": {},
        "metrics": {"mean_delta_e": round(float(np.mean(errors[foreground])), 2) if foreground_count else 0.0,
                    "ssim": round(float(ssim), 3),
                    "color_count": len(used_colors), "regions": len(regions),
                    "confetti_replaced": removed, "half_crosses": sum(s["stitch_type"] != "full" for s in stitches),
                    "blended_stitches": int(np.sum(secondary >= 0)),
                    "background_removed": int(np.sum(background))},
    }
