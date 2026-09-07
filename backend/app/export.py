from html import escape


def printable_html(pattern: dict) -> str:
    color_map = {c["id"]: c for c in pattern["colors"]}
    cells = []
    for stitch in pattern["stitches"]:
        color = color_map[stitch["primary_color"]]
        cls = " major" if stitch["x"] % 10 == 0 or stitch["y"] % 10 == 0 else ""
        cells.append(f'<span class="cell{cls}" style="--c:{color["hex"]}">{escape(stitch["symbol"])}</span>')
    legend = "".join(f'<li><i style="background:{c["hex"]}"></i><b>{escape(c["symbol"])}</b> {escape(c["id"])} — {escape(c["name"])}</li>' for c in pattern["colors"])
    threads = "".join(f'<tr><td>{escape(t["id"])}</td><td>{escape(t["name"])}</td><td>{t["metres"]} м</td><td>{t["skeins"]}</td></tr>' for t in pattern["materials"]["threads"])
    backstitch = "".join(f'<line x1="{s["from_x"]*16}" y1="{s["from_y"]*16}" x2="{s["to_x"]*16}" y2="{s["to_y"]*16}" />' for s in pattern["backstitch"])
    blend_pairs = sorted({(s["primary_color"], s["secondary_color"]) for s in pattern["stitches"] if s.get("secondary_color")})
    blends = "".join(f'<li>{escape(a)} + {escape(b)}</li>' for a, b in blend_pairs)
    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Схема {pattern["id"]}</title>
<style>@page{{size:A4 landscape;margin:12mm}}*{{box-sizing:border-box}}body{{font:12px Arial;color:#20242c}}h1{{font-size:22px}}.grid{{position:relative;display:grid;grid-template-columns:repeat({pattern["width"]},16px);width:max-content;border:1px solid #222}}.cell{{width:16px;height:16px;display:grid;place-items:center;font-size:8px;background:color-mix(in srgb,var(--c) 32%,white);border-right:1px solid #ddd;border-bottom:1px solid #ddd}}.major{{border-color:#59677c}}svg{{position:absolute;inset:0;width:{pattern["width"]*16}px;height:{pattern["height"]*16}px;pointer-events:none}}line{{stroke:#1c2028;stroke-width:1.4}}.cols{{display:grid;grid-template-columns:2fr 1fr;gap:24px}}ul{{columns:2;list-style:none;padding:0}}i{{display:inline-block;width:12px;height:12px;margin-right:5px}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ccc;padding:5px;text-align:left}}@media print{{.grid{{transform-origin:top left}}}}</style></head>
<body><h1>Схема вышивки</h1><p>{pattern["width"]} × {pattern["height"]} крестиков · {pattern["physical_width_mm"]} × {pattern["physical_height_mm"]} мм · Aida {pattern["options"]["canvas_count"]}</p><div class="cols"><div class="grid">{"".join(cells)}<svg viewBox="0 0 {pattern["width"]*16} {pattern["height"]*16}" aria-label="Шов назад иголку">{backstitch}</svg></div><section><h2>Условные обозначения</h2><ul>{legend}</ul>{f'<h2>Смешанные цвета</h2><ul>{blends}</ul>' if blends else ''}<h2>Материалы</h2><table><tr><th>Цвет</th><th>Название</th><th>Длина</th><th>Мотки</th></tr>{threads}</table></section></div></body></html>'''
