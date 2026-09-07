from itertools import combinations

import numpy as np
from skimage.color import deltaE_ciede2000, rgb2lab


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    return rgb2lab(np.asarray(rgb, dtype=np.float32) / 255.0)


def delta_e(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return deltaE_ciede2000(np.asarray(a), np.asarray(b))


def match_palette(target_lab: np.ndarray, palette: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    labs = np.asarray([c["lab"] for c in palette], dtype=np.float32)
    flat = target_lab.reshape(-1, 1, 3)
    errors = deltaE_ciede2000(flat, labs.reshape(1, -1, 3))
    indices = np.argmin(errors, axis=1)
    best = np.take_along_axis(errors, indices[:, None], axis=1)[:, 0]
    return indices.reshape(target_lab.shape[:2]), best.reshape(target_lab.shape[:2])


def apply_blends(target_lab: np.ndarray, indices: np.ndarray, errors: np.ndarray,
                 palette: list[dict], improvement: float = 2.4) -> tuple[np.ndarray, np.ndarray]:
    used, counts = np.unique(indices, return_counts=True)
    candidates = used[np.argsort(counts)[-min(18, len(used)):]]
    pairs = list(combinations(candidates.tolist(), 2))[:120]
    secondary = np.full(indices.shape, -1, dtype=np.int16)
    if not pairs:
        return secondary, errors
    blend_rgb = np.array([(np.array(palette[a]["rgb"]) + np.array(palette[b]["rgb"])) / 2 for a, b in pairs])
    blend_lab = rgb_to_lab(blend_rgb.reshape(1, -1, 3))[0]
    flat = target_lab.reshape(-1, 1, 3)
    blend_errors = deltaE_ciede2000(flat, blend_lab.reshape(1, -1, 3))
    choice = np.argmin(blend_errors, axis=1)
    chosen_error = np.take_along_axis(blend_errors, choice[:, None], axis=1)[:, 0]
    old_error = errors.ravel()
    use = chosen_error + improvement < old_error
    flat_primary = indices.ravel()
    flat_secondary = secondary.ravel()
    for pos in np.flatnonzero(use):
        a, b = pairs[int(choice[pos])]
        flat_primary[pos] = a
        flat_secondary[pos] = b
        old_error[pos] = chosen_error[pos]
    return secondary, old_error.reshape(errors.shape)

