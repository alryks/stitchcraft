from collections import Counter, deque

import numpy as np


NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def components(values: np.ndarray) -> list[list[tuple[int, int]]]:
    height, width = values.shape
    seen = np.zeros((height, width), dtype=bool)
    result = []
    for y in range(height):
        for x in range(width):
            if seen[y, x]:
                continue
            target = values[y, x]
            queue, part = deque([(x, y)]), []
            seen[y, x] = True
            while queue:
                cx, cy = queue.popleft()
                part.append((cx, cy))
                for dx, dy in NEIGHBOURS:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < width and 0 <= ny < height and not seen[ny, nx] and values[ny, nx] == target:
                        seen[ny, nx] = True
                        queue.append((nx, ny))
            result.append(part)
    return result


def reduce_confetti(indices: np.ndarray, target_lab: np.ndarray, palette_labs: np.ndarray,
                    importance: np.ndarray, minimum: int) -> tuple[np.ndarray, int]:
    result = indices.copy()
    changed = 0
    for part in sorted(components(result), key=len):
        if len(part) >= minimum:
            continue
        neighbours = []
        for x, y in part:
            for dx, dy in NEIGHBOURS:
                nx, ny = x + dx, y + dy
                if 0 <= nx < result.shape[1] and 0 <= ny < result.shape[0] and (nx, ny) not in part:
                    neighbours.append(int(result[ny, nx]))
        if not neighbours:
            continue
        source = int(result[part[0][1], part[0][0]])
        candidates = Counter(neighbours).most_common(4)
        mean_target = np.mean([target_lab[y, x] for x, y in part], axis=0)
        mean_importance = float(np.mean([importance[y, x] for x, y in part]))
        scored = [(float(np.linalg.norm(mean_target - palette_labs[idx])) - count * 0.8 + mean_importance * 5.0, idx)
                  for idx, count in candidates]
        replacement = min(scored)[1]
        if replacement != source and mean_importance < 0.72:
            for x, y in part:
                result[y, x] = replacement
            changed += len(part)
    return result, changed


def build_regions(stitches: list[dict], width: int, height: int) -> list[dict]:
    by_key: dict[tuple, set[tuple[int, int]]] = {}
    stitch_at = {}
    for stitch in stitches:
        # A region follows the thread combination. Full and half crosses can be
        # stitched in one pass, so splitting them creates artificial confetti.
        key = (stitch["primary_color"], stitch.get("secondary_color"))
        point = (stitch["x"], stitch["y"])
        by_key.setdefault(key, set()).add(point)
        stitch_at[point] = stitch
    regions = []
    sequence = 1
    for key, remaining in by_key.items():
        while remaining:
            start = next(iter(remaining)); queue = deque([start]); remaining.remove(start); points = []
            while queue:
                point = queue.popleft(); points.append(point)
                for dx, dy in NEIGHBOURS:
                    nxt = (point[0] + dx, point[1] + dy)
                    if nxt in remaining:
                        remaining.remove(nxt); queue.append(nxt)
            region_id = f"r{sequence}"; sequence += 1
            members = []
            for point in points:
                stitch_at[point]["region_id"] = region_id
                members.append(stitch_at[point]["id"])
            xs, ys = zip(*points)
            stitch_types = {stitch_at[point]["stitch_type"] for point in points}
            regions.append({"id": region_id, "color": key[0], "secondary_color": key[1],
                            "stitch_type": next(iter(stitch_types)) if len(stitch_types) == 1 else "mixed",
                            "stitches": members,
                            "bounding_box": {"x": min(xs), "y": min(ys),
                                             "width": max(xs)-min(xs)+1, "height": max(ys)-min(ys)+1}})
    return regions
