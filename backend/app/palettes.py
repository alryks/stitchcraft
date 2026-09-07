import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from skimage.color import rgb2lab

from .config import settings


@lru_cache(maxsize=4)
def load_palette(name: str) -> list[dict]:
    safe_name = name.lower()
    if safe_name not in {"dmc", "anchor"}:
        raise ValueError(f"Unsupported palette: {name}")
    path = Path(settings.palettes_dir) / f"{safe_name}.json"
    colors = json.loads(path.read_text(encoding="utf-8"))
    for color in colors:
        rgb = np.array(color["rgb"], dtype=np.float32).reshape(1, 1, 3) / 255.0
        color["lab"] = rgb2lab(rgb)[0, 0].round(3).tolist()
        color["hex"] = "#" + "".join(f"{v:02x}" for v in color["rgb"])
    return colors


def public_palette(name: str) -> dict:
    colors = load_palette(name)
    return {"id": name, "name": name.upper(), "colors": colors}

