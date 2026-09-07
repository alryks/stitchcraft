CANVASES = [
    {"id": "white", "name": "Белая", "rgb": [250, 249, 244], "counts": [11, 14, 16, 18]},
    {"id": "antique-white", "name": "Античная белая", "rgb": [235, 226, 205], "counts": [11, 14, 16, 18]},
    {"id": "natural", "name": "Натуральный лён", "rgb": [190, 173, 143], "counts": [14, 16, 18]},
    {"id": "black", "name": "Чёрная", "rgb": [30, 31, 33], "counts": [14, 16, 18]},
    {"id": "navy", "name": "Тёмно-синяя", "rgb": [35, 45, 66], "counts": [14, 16]},
    {"id": "pale-blue", "name": "Бледно-голубая", "rgb": [204, 220, 222], "counts": [14, 16]},
]

NEEDLES = [(11, 22), (14, 24), (16, 26), (18, 26), (32, 28)]


def needle_for_count(count: int) -> int:
    return min(NEEDLES, key=lambda pair: abs(pair[0] - count))[1]

