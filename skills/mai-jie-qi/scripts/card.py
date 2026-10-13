#!/usr/bin/env python3
"""把 pairing.py 的输出渲染成一张 1080×1440 的节气卡片（SVG，仅标准库）。

视觉元素：四季配色 + 快餐红黄、手绘风格的通用汉堡/薯条盒/饮料杯图标、托盘纸条纹。
不使用任何品牌 Logo、字标或官方形象。
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import solar_term  # noqa: E402

W, H = 1080, 1440
SERIF = "'Noto Serif SC','Noto Serif CJK SC','Source Han Serif SC','Songti SC','STSong',serif"
SANS = "'PingFang SC','Noto Sans SC','Noto Sans CJK SC','Microsoft YaHei',sans-serif"
RED, YELLOW, BUN, BUN_DARK, PATTY, LETTUCE, CREAM = (
    "#DA291C", "#FFC72C", "#E9A23B", "#C7812A", "#6B3A1E", "#7CB342", "#FFF4DC")
DRINK_TAGS = {"热饮", "冰饮", "咖啡", "奶香"}


def wrap(text, width):
    lines, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= width:
            lines.append(cur)
            cur = ""
    if cur:
        lines.append(cur)
    return lines


def _t(x, y, text, size, fill, family=SANS, weight=400, anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" {extra}>{escape(str(text))}</text>')


# ---- 图标：都画在 100×100 的坐标系里，再平移缩放 ----

def _place(x, y, size, body, rotate=0):
    s = size / 100.0
    rot = f" rotate({rotate} 50 50)" if rotate else ""
    return f'<g transform="translate({x} {y}) scale({s:.3f}){rot}">{body}</g>'


def _steam(color, x0=50, y0=8, n=3):
    paths = []
    for i in range(n):
        x = x0 + (i - (n - 1) / 2) * 16
        paths.append(f'<path d="M{x},{y0} q-7,-9 0,-18 q7,-9 0,-18" fill="none" stroke="{color}" '
                     f'stroke-width="4" stroke-linecap="round" opacity="0.55"/>')
    return "".join(paths)


def burger(outline):
    return "".join([
        f'<path d="M8,48 Q8,12 50,12 Q92,12 92,48 Z" fill="{BUN}" stroke="{outline}" stroke-width="3"/>',
        *[f'<ellipse cx="{cx}" cy="{cy}" rx="3.2" ry="1.8" fill="{CREAM}" transform="rotate({r} {cx} {cy})"/>'
          for cx, cy, r in ((30, 28, -20), (45, 21, 10), (60, 25, -10), (72, 34, 25), (38, 38, 15), (55, 36, -25))],
        f'<path d="M6,50 q6,8 12,0 q6,8 12,0 q6,8 12,0 q6,8 12,0 q6,8 12,0 q6,8 12,0 q6,8 12,0 q6,8 8,0 L94,48 L6,48 Z" '
        f'fill="{LETTUCE}" stroke="{outline}" stroke-width="2.5"/>',
        f'<path d="M10,56 L90,56 L84,64 L74,58 L62,66 L50,58 L36,65 L26,58 L16,63 Z" fill="{YELLOW}" stroke="{outline}" stroke-width="2.5"/>',
        f'<rect x="8" y="60" width="84" height="13" rx="6.5" fill="{PATTY}" stroke="{outline}" stroke-width="3"/>',
        f'<path d="M10,75 L90,75 Q90,90 76,90 L24,90 Q10,90 10,75 Z" fill="{BUN_DARK}" stroke="{outline}" stroke-width="3"/>',
    ])


def fries(outline):
    sticks = "".join(
        f'<rect x="{x}" y="{y}" width="8" height="48" rx="2" fill="{YELLOW}" stroke="{outline}" stroke-width="2.2" '
        f'transform="rotate({r} {x + 4} {y + 48})"/>'
        for x, y, r in ((28, 10, -12), (38, 4, -5), (48, 2, 2), (58, 6, 8), (66, 12, 14), (43, 12, -2), (54, 14, 5)))
    carton = (f'<path d="M18,46 Q50,58 82,46 L72,96 L28,96 Z" fill="{RED}" stroke="{outline}" stroke-width="3"/>'
              f'<path d="M30,62 Q50,70 70,62" fill="none" stroke="{YELLOW}" stroke-width="3" stroke-linecap="round"/>')
    return sticks + carton


def cup(outline, hot):
    body = (f'<path d="M24,28 L76,28 L68,96 L32,96 Z" fill="#FFFFFF" stroke="{outline}" stroke-width="3"/>'
            f'<path d="M27,50 L73,50 L70,72 L30,72 Z" fill="{RED}"/>'
            f'<path d="M38,61 q6,-7 12,0 q6,7 12,0" fill="none" stroke="{YELLOW}" stroke-width="3" stroke-linecap="round"/>'
            f'<rect x="18" y="20" width="64" height="10" rx="4" fill="{"#FFFFFF" if hot else RED}" stroke="{outline}" stroke-width="3"/>')
    if hot:
        return body + _steam(outline, 50, 16)
    return f'<path d="M56,22 L66,0 L72,2" fill="none" stroke="{YELLOW}" stroke-width="6" stroke-linecap="round"/>' + body


def cone(outline):
    return (f'<path d="M30,48 L70,48 L50,98 Z" fill="{BUN}" stroke="{outline}" stroke-width="3"/>'
            f'<path d="M36,58 L60,82 M64,58 L44,86 M42,48 L62,74 M58,48 L40,72" stroke="{BUN_DARK}" stroke-width="2"/>'
            f'<path d="M26,50 Q22,34 38,32 Q36,16 52,16 Q56,4 64,14 Q78,18 72,32 Q82,40 74,50 Z" fill="{CREAM}" '
            f'stroke="{outline}" stroke-width="3"/>')


def pie(outline):
    return (f'<rect x="12" y="34" width="76" height="40" rx="10" fill="{BUN}" stroke="{outline}" stroke-width="3"/>'
            + "".join(f'<path d="M{x},46 l8,16" stroke="{BUN_DARK}" stroke-width="3" stroke-linecap="round"/>'
                      for x in (28, 44, 60)))


def item_icon(tags, outline):
    tags = set(tags or [])
    if "冰品" in tags:
        return cone(outline)
    if tags & DRINK_TAGS or ("甜" in tags and not tags & {"热食", "谷物", "油炸"}):
        return cup(outline, hot="热饮" in tags)
    if "油炸" in tags and "谷物" not in tags:
        return fries(outline)
    if "汤粥" in tags:
        return cup(outline, hot=True)
    if "甜" in tags and "谷物" not in tags:
        return pie(outline)
    return burger(outline)


def tray_stripe(y, x0=40, x1=W - 40, h=18):
    """托盘纸风格的红黄斜纹带。"""
    parts = [f'<clipPath id="stripe{y}"><rect x="{x0}" y="{y}" width="{x1 - x0}" height="{h}"/></clipPath>',
             f'<g clip-path="url(#stripe{y})"><rect x="{x0}" y="{y}" width="{x1 - x0}" height="{h}" fill="{YELLOW}"/>']
    x = x0 - h
    while x < x1 + h:
        parts.append(f'<path d="M{x},{y + h} L{x + h},{y} L{x + 2 * h},{y} L{x + h},{y + h} Z" fill="{RED}"/>')
        x += 2 * h
    parts.append("</g>")
    return "".join(parts)


def render(result):
    data = solar_term.load_data()
    t = result["term"]
    pal = data["seasons"][t["season"]]
    bg, ink, accent = pal["bg"], pal["ink"], pal["accent"]
    term_cfg = solar_term.term_by_name(data, t["name"])
    warm = any(term_cfg["prefer"].get(k, 0) > 0 for k in ("热饮", "热食", "汤粥"))

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" fill="{bg}"/>',
           tray_stripe(0, 0, W, 22), tray_stripe(H - 22, 0, W, 22),
           f'<rect x="40" y="52" width="{W - 80}" height="{H - 104}" fill="none" stroke="{accent}" stroke-width="2" opacity="0.5"/>']

    # 头部
    out.append(_t(90, 140, f"二十四节气 · {t['season']}", 30, accent, weight=600, extra='letter-spacing="6"'))
    if t.get("started_at"):
        d = datetime.fromisoformat(t["started_at"])
        sub = f"{d.month}月{d.day}日交节"
        if t.get("day_index"):
            sub += f" · 第{t['day_index']}天"
        out.append(_t(W - 90, 140, sub, 28, ink, anchor="end", extra='opacity="0.7"'))
    out.append(_t(90, 370, t["name"], 200, ink, SERIF, 700, extra='letter-spacing="20"'))
    out.append(_t(96, 435, t["pinyin"], 34, accent, extra='letter-spacing="4"'))
    out.append(_t(90, 505, "　".join(t["hou"]), 34, ink, SERIF, extra='opacity="0.85"'))

    # 右上角主视觉：大汉堡（应季热食时冒热气）
    out.append(f'<circle cx="{W - 205}" cy="300" r="135" fill="{YELLOW}" opacity="0.28"/>')
    out.append(_place(W - 330, 185, 250, burger(ink), rotate=-8))
    if warm:
        out.append(_place(W - 280, 168, 150, _steam(ink, 50, 40)))

    out.append(tray_stripe(548, 90, W - 90, 10))

    # 这一餐：红色菜单牌标题
    y = 600
    out.append(f'<rect x="90" y="{y}" width="250" height="60" rx="8" fill="{RED}"/>')
    out.append(_t(215, y + 42, "这一餐", 34, YELLOW, weight=700, anchor="middle", extra='letter-spacing="8"'))
    pick = result.get("pick")
    y += 120
    if pick:
        items = pick["items"]
        shown = items[:4] if len(items) <= 4 else items[:3]
        step = 72 if len(items) <= 3 else 62
        for it in shown:
            out.append(_place(100, y - 46, 58, item_icon(it.get("tags"), ink)))
            out.append(_t(180, y, it["name"], 40, ink))
            out.append(_t(W - 110, y, f"×{it['quantity']}", 36, ink, anchor="end", extra='opacity="0.6"'))
            y += step
        if len(items) > len(shown):
            out.append(_t(180, y - 14, f"等共 {len(items)} 样", 28, ink, extra='opacity="0.6"'))
            y += 36
        y += 30
        price = f"¥{pick['total_yuan']:.1f}"
        pw = 60 + 38 * len(price)
        out.append(f'<rect x="90" y="{y - 62}" width="{pw}" height="84" rx="42" fill="{YELLOW}"/>')
        out.append(_t(90 + pw / 2, y, price, 60, RED, weight=800, anchor="middle"))
        kcal = "热量未知" if pick["kcal"] is None else f"约 {pick['kcal']:.0f} kcal · 热量{pick['kcal_band']}"
        out.append(_t(W - 90, y - 8, kcal, 32, ink, anchor="end"))
        y += 80
        lines = wrap(pick["reason"], 27)
        if len(lines) > 2:
            lines = lines[:2]
            lines[1] = lines[1][:-1] + "…"
        for line in lines:
            out.append(_t(90, y, line, 32, ink))
            y += 50
    else:
        out.append(_t(110, y, "这次没有满足条件的搭配", 40, ink))
        y += 60

    # 民俗与小句，右下角薯条盒
    y = 1190
    out.append(_t(90, y, f"民俗　{t['custom']}", 30, ink, extra='opacity="0.8"'))
    out.append(_t(90, y + 80, f"「{t['line']}」", 40, accent, SERIF, 600))
    out.append(_place(W - 220, y - 70, 140, fries(ink), rotate=6))

    foot = result.get("disclaimer", "")
    if pick and pick.get("queried_at"):
        foot = f"价格查询于 {pick['queried_at'][:16].replace('T', ' ')} · " + foot
    for i, line in enumerate(wrap(foot, 44)[:2]):
        out.append(_t(90, H - 112 + i * 34, line, 22, ink, extra='opacity="0.55"'))
    if result.get("demo"):
        out.append(f'<g transform="rotate(-24 {W // 2} {H // 2})">'
                   + _t(W // 2, H // 2, "模拟数据 · 不可下单", 96, "#C0392B", weight=700, anchor="middle",
                        extra='opacity="0.16"') + '</g>')
    out.append("</svg>")
    return "\n".join(out)


def main(argv=None):
    p = argparse.ArgumentParser(description="生成节气卡片 SVG")
    p.add_argument("input", help="pairing.py 输出的 JSON；用 - 表示 stdin")
    p.add_argument("-o", "--out", required=True, help="输出 .svg 路径")
    args = p.parse_args(argv)
    raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    Path(args.out).write_text(render(json.loads(raw)), encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
