from html import escape


def printable_html(pattern: dict) -> str:
    color_map = {c["id"]: c for c in pattern["colors"]}
    cells = []
    for stitch in pattern["stitches"]:
        color = color_map[stitch["primary_color"]]
        classes = ["cell"]
        if stitch["x"] % 10 == 0 or stitch["y"] % 10 == 0:
            classes.append("major")
        if stitch["stitch_type"] == "half_forward":
            classes.append("half-forward")
        elif stitch["stitch_type"] == "half_backward":
            classes.append("half-backward")
        secondary = stitch.get("secondary_color")
        if secondary:
            classes.append("blend")
        secondary_hex = color_map[secondary]["hex"] if secondary else "#315f82"
        class_name = " ".join(classes)
        cells.append(f'<span class="{class_name}" style="--c:{color["hex"]};--s:{secondary_hex}">{escape(stitch["symbol"])}</span>')
    legend = "".join(f'<li><i style="background:{c["hex"]}"></i><b>{escape(c["symbol"])}</b> {escape(c["id"])} — {escape(c["name"])}</li>' for c in pattern["colors"])
    threads = "".join(f'<tr><td>{escape(t["id"])}</td><td>{escape(t["name"])}</td><td>{t["metres"]} м</td><td>{t["skeins"]}</td></tr>' for t in pattern["materials"]["threads"])
    backstitch_enabled = pattern.get("options", {}).get("backstitch", bool(pattern["backstitch"]))
    backstitch = "".join(f'<line x1="{s["from_x"]*16}" y1="{s["from_y"]*16}" x2="{s["to_x"]*16}" y2="{s["to_y"]*16}" />' for s in pattern["backstitch"]) if backstitch_enabled else ""
    backstitch_svg = f'<svg viewBox="0 0 {pattern["width"]*16} {pattern["height"]*16}" aria-label="Шов назад иголку">{backstitch}</svg>' if backstitch_enabled else ""
    blend_pairs = sorted({(s["primary_color"], s["secondary_color"]) for s in pattern["stitches"] if s.get("secondary_color")})
    blends = "".join(f'<li>{escape(a)} + {escape(b)}</li>' for a, b in blend_pairs)
    stitch_legend = '''<li><b class="stitch-mark half-forward"></b> Полукрест вперёд</li>
<li><b class="stitch-mark half-backward"></b> Полукрест назад</li>
<li><b class="stitch-mark blend"></b> Второй цвет смешанного стежка</li>'''
    if backstitch_enabled:
        stitch_legend += '<li><b class="stitch-mark backstitch"></b> Шов назад иголку</li>'
    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Схема {pattern["id"]}</title>
<style>@page{{size:A4 landscape;margin:12mm}}*{{box-sizing:border-box}}body{{font:12px Arial;color:#20242c}}h1{{font-size:22px}}.grid{{position:relative;display:grid;grid-template-columns:repeat({pattern["width"]},16px);width:max-content;border:1px solid #222}}.cell{{position:relative;width:16px;height:16px;display:grid;place-items:center;font-size:8px;font-weight:600;background:color-mix(in srgb,var(--c) 32%,white);border-right:1px solid #ddd;border-bottom:1px solid #ddd;isolation:isolate}}.cell::before,.cell::after{{content:"";position:absolute;inset:0;pointer-events:none;z-index:-1}}.half-forward::before{{background:linear-gradient(135deg,transparent 46%,#20242c 48%,#20242c 52%,transparent 54%)}}.half-backward::before{{background:linear-gradient(45deg,transparent 46%,#20242c 48%,#20242c 52%,transparent 54%)}}.blend::after{{background:linear-gradient(45deg,transparent 46%,var(--s) 48%,var(--s) 52%,transparent 54%)}}.major{{border-color:#59677c}}.stitch-mark{{position:relative;display:inline-block;width:16px;height:16px;vertical-align:-3px;margin-right:6px;border:1px solid #c8ced2;background:#fff}}.stitch-mark::before,.stitch-mark::after{{content:"";position:absolute;inset:0}}.stitch-mark.half-forward::before{{background:linear-gradient(135deg,transparent 46%,#20242c 48%,#20242c 52%,transparent 54%)}}.stitch-mark.half-backward::before{{background:linear-gradient(45deg,transparent 46%,#20242c 48%,#20242c 52%,transparent 54%)}}.stitch-mark.blend::after{{background:linear-gradient(45deg,transparent 46%,#315f82 48%,#315f82 52%,transparent 54%)}}.stitch-mark.backstitch::before{{inset:7px -2px auto -2px;height:2px;background:#1c2028;transform:rotate(-25deg)}}svg{{position:absolute;inset:0;width:{pattern["width"]*16}px;height:{pattern["height"]*16}px;pointer-events:none}}line{{stroke:#1c2028;stroke-width:1.4}}.cols{{display:grid;grid-template-columns:2fr 1fr;gap:24px}}ul{{columns:2;list-style:none;padding:0}}i{{display:inline-block;width:12px;height:12px;margin-right:5px}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ccc;padding:5px;text-align:left}}@media print{{.grid{{transform-origin:top left}}}}</style></head>
<body><h1>Схема вышивки</h1><p>{pattern["width"]} × {pattern["height"]} крестиков · {pattern["physical_width_mm"]} × {pattern["physical_height_mm"]} мм · Aida {pattern["options"]["canvas_count"]}</p><div class="cols"><div class="grid">{"".join(cells)}{backstitch_svg}</div><section><h2>Условные обозначения</h2><ul>{legend}</ul><h2>Стежки</h2><ul class="stitch-legend">{stitch_legend}</ul>{f'<h2>Смешанные цвета</h2><ul>{blends}</ul>' if blends else ''}<h2>Материалы</h2><table><tr><th>Цвет</th><th>Название</th><th>Длина</th><th>Мотки</th></tr>{threads}</table></section></div></body></html>'''
