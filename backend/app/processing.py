from __future__ import annotations

import io
import math
from collections import Counter

import cv2
import numpy as np
from PIL import Image, ImageOps
from skimage.metrics import structural_similarity

from .canvas import CANVASES
from .color import apply_blends, delta_e, match_palette, rgb_to_lab
from .materials import calculate_materials, select_canvas
from .models import PatternOptions
from .palettes import load_palette
from .regions import build_regions, reduce_confetti

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


def _prepare_image(data: bytes, width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    image = Image.open(io.BytesIO(data))
    image = ImageOps.exif_transpose(image).convert("RGBA")
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
    return prepared, importance


def _quantize_lab(image: np.ndarray, colors: int) -> tuple[np.ndarray, np.ndarray]:
    lab = rgb_to_lab(image)
    pixels = lab.reshape(-1, 3).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 35, 0.15)
    cv2.setRNGSeed(42)
    _, labels, centers = cv2.kmeans(pixels, colors, None, criteria, 4, cv2.KMEANS_PP_CENTERS)
    quantized = centers[labels.ravel()].reshape(lab.shape)
    return lab, quantized


def _backstitch(importance: np.ndarray, palette: list[dict], enabled: bool) -> list[dict]:
    if not enabled:
        return []
    mask = (importance > max(0.62, float(np.quantile(importance, 0.8)))).astype(np.uint8) * 255
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    darkest = min(palette, key=lambda c: sum(c["rgb"]))["id"]
    segments = []
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:18]:
        if cv2.arcLength(contour, True) < 3:
            continue
        simplified = cv2.approxPolyDP(contour, 0.8, False).reshape(-1, 2)
        for a, b in zip(simplified, simplified[1:]):
            if np.linalg.norm(b-a) >= 0.8:
                segments.append({"from_x": int(a[0]), "from_y": int(a[1]),
                                 "to_x": int(b[0]), "to_y": int(b[1]), "color": darkest})
    return segments[:160]


def generate_pattern(data: bytes, options: PatternOptions) -> dict:
    source = Image.open(io.BytesIO(data))
    width, height = _dimensions(source, options)
    prepared, importance = _prepare_image(data, width, height)
    original_lab, quantized_lab = _quantize_lab(prepared, min(options.max_colors, width * height))
    palette = load_palette(options.palette)
    indices, errors = match_palette(quantized_lab, palette)
    palette_labs = np.asarray([c["lab"] for c in palette], dtype=np.float32)
    indices, removed = reduce_confetti(indices, original_lab, palette_labs, importance, options.min_component_size)
    errors = delta_e(original_lab, palette_labs[indices])
    secondary = np.full(indices.shape, -1, dtype=np.int16)
    if options.blends:
        secondary, errors = apply_blends(original_lab, indices, errors, palette)

    used_indices = sorted(set(indices.ravel().tolist()) | {int(v) for v in secondary.ravel() if v >= 0})
    symbols = {idx: SYMBOLS[pos % len(SYMBOLS)] for pos, idx in enumerate(used_indices)}
    edge_cutoff = max(0.68, float(np.quantile(importance, 0.88)))
    stitches = []
    for y in range(height):
        for x in range(width):
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
    canvas = select_canvas(prepared.mean(axis=(0, 1)).tolist(), [c["rgb"] for c in used_colors], options.canvas_color)
    lookup = {c["id"]: c for c in palette}
    materials = calculate_materials(stitches, lookup, width, height, options.canvas_count, options.strands, canvas)
    rendered = np.asarray([[lookup[s["primary_color"]]["rgb"] for s in stitches[y*width:(y+1)*width]] for y in range(height)], dtype=np.uint8)
    min_side = min(width, height)
    ssim = structural_similarity(prepared, rendered, channel_axis=2, data_range=255,
                                 win_size=min(7, min_side if min_side % 2 else min_side-1))
    return {
        "width": width, "height": height,
        "physical_width_mm": round(width * 25.4 / options.canvas_count, 1),
        "physical_height_mm": round(height * 25.4 / options.canvas_count, 1),
        "options": options.model_dump(), "stitches": stitches, "regions": regions,
        "backstitch": _backstitch(importance, palette, options.backstitch),
        "colors": used_colors, "canvas_options": CANVASES, "materials": materials,
        "plans": {},
        "metrics": {"mean_delta_e": round(float(np.mean(errors)), 2), "ssim": round(float(ssim), 3),
                    "color_count": len(used_colors), "regions": len(regions),
                    "confetti_replaced": removed, "half_crosses": sum(s["stitch_type"] != "full" for s in stitches),
                    "blended_stitches": int(np.sum(secondary >= 0))},
    }

