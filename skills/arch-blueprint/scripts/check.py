#!/usr/bin/env python3
"""arch-blueprint 架構圖自檢（純標準函式庫，不需安裝任何套件）。

    python3 scripts/check.py docs/architecture/overview.svg [more.svg ...]

把 SKILL.md 裡能量化的規則全部跑一遍：

  結構   viewBox 1200 寬、role="img"、<title>/<desc> 齊全、字型含 JetBrains Mono
  語言   圖內文字全英文（不得出現 CJK 字元）
  顏色   只有米白 #faf8f4 與墨黑 #1a1a1a；禁止漸層、濾鏡、陰影、外部圖片
  數量   節點 ≤ 12、連線 ≤ 12、資料流標籤 ≤ 6
  標籤   g.label 的 data-edge 指向既有連線、遮罩貼著該線 4–12px、
         不壓到節點／其他線／其他標籤／分區標題、文字 ≤ 14 字元且全大寫
  留白   所有圖形與文字距離畫布邊緣 ≥ 60px
  容器   分區互不重疊、節點與分區邊界內距 ≥ 24px、節點都在某個分區內
  節點   節點互不重疊且間距 ≥ 20px、尺寸落在 4px 格線、文字不溢出
  icon   每個節點恰有一個 <use href="#icon-*">，symbol 內容與 assets/icons.svg 一致
  連線   只能水平／垂直（直角轉彎；跳線用小圓弧 A）、不穿過節點或分區標題、
         與非端點節點保持 ≥ 16px（警告）、端點停在節點邊緣外 2–12px 並與邊垂直、
         同一邊的接點相距 ≥ 12px、不同連線不可重疊、交叉處必須有跳線

錯誤（E）會讓結束碼變 1；警告（W）只提示。
"""

from __future__ import annotations

import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

PAPER = "#faf8f4"
INK = "#1a1a1a"
ALLOWED_COLORS = {PAPER, INK, "none", "transparent"}
FORBIDDEN_TAGS = {"linearGradient", "radialGradient", "filter", "pattern", "image", "foreignObject", "script"}
MARGIN = 60
ZONE_PAD = 24
NODE_GAP = 20
MAX_NODES = 12
MAX_EDGES = 12
MAX_LABELS = 6
LABEL_MAX_CHARS = 14
LABEL_GAP_MIN, LABEL_GAP_MAX = 4.0, 12.0
FAN_GAP = 12
NEAR_GAP = 16
END_GAP_MIN, END_GAP_MAX = 2.0, 12.0
START_GAP_MAX = 12.0
ICON_LIB = Path(__file__).resolve().parent.parent / "assets" / "icons.svg"


# ---------------------------------------------------------------- helpers ---

def tag(el: ET.Element) -> str:
    return el.tag.split("}", 1)[-1]


def num(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)", value)
    return float(m.group(1)) if m else default


def href(el: ET.Element) -> str | None:
    return el.get("href") or el.get(f"{{{XLINK_NS}}}href")


def style_props(el: ET.Element) -> dict[str, str]:
    props = {}
    for part in (el.get("style") or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            props[k.strip()] = v.strip()
    return props


def paint(el: ET.Element, prop: str) -> str | None:
    return style_props(el).get(prop, el.get(prop))


def is_cjk(ch: str) -> bool:
    o = ord(ch)
    return o >= 0x2E80 and not (0xFF61 <= o <= 0xFF9F)


def text_width(s: str, font_size: float, letter_spacing: float = 0.0) -> float:
    w = sum(font_size * (1.0 if is_cjk(c) else 0.6) for c in s)
    return w + letter_spacing * max(len(s) - 1, 0)


class Rect:
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x: float, y: float, w: float, h: float) -> None:
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def x2(self) -> float:
        return self.x + self.w

    @property
    def y2(self) -> float:
        return self.y + self.h

    def contains(self, other: "Rect", inset: float = 0.0) -> bool:
        return (other.x >= self.x + inset - 0.01 and other.y >= self.y + inset - 0.01
                and other.x2 <= self.x2 - inset + 0.01 and other.y2 <= self.y2 - inset + 0.01)

    def overlaps(self, other: "Rect", gap: float = 0.0) -> bool:
        return not (other.x >= self.x2 + gap or other.x2 <= self.x - gap
                    or other.y >= self.y2 + gap or other.y2 <= self.y - gap)

    def contains_point(self, px: float, py: float, inset: float = 0.0) -> bool:
        return self.x + inset < px < self.x2 - inset and self.y + inset < py < self.y2 - inset

    def __repr__(self) -> str:
        return f"({self.x:g},{self.y:g} {self.w:g}×{self.h:g})"


def rect_of(el: ET.Element) -> Rect:
    return Rect(num(el.get("x")), num(el.get("y")), num(el.get("width")), num(el.get("height")))


def text_bbox(el: ET.Element, inherited_size: float = 14.0) -> Rect:
    """粗估文字外框：中文字寬 ≈ 字級 × 1.0，英文 ≈ × 0.6。"""
    fs = num(el.get("font-size"), inherited_size)
    ls = num(el.get("letter-spacing"), 0.0)
    content = "".join(el.itertext()).strip()
    w = text_width(content, fs, ls)
    x = num(el.get("x"))
    y = num(el.get("y"))
    anchor = el.get("text-anchor", "start")
    if anchor == "middle":
        x -= w / 2
    elif anchor == "end":
        x -= w
    return Rect(x, y - fs * 0.75, w, fs)


# ----------------------------------------------------------- path parsing ---

class Seg:
    """一段直線（水平或垂直時 axis 為 'h'/'v'，否則 'diag'）。"""
    __slots__ = ("x1", "y1", "x2", "y2")

    def __init__(self, x1, y1, x2, y2) -> None:
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2

    @property
    def axis(self) -> str:
        if abs(self.y1 - self.y2) < 0.5:
            return "h"
        if abs(self.x1 - self.x2) < 0.5:
            return "v"
        return "diag"

    @property
    def length(self) -> float:
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)

    def hits_rect(self, r: Rect) -> bool:
        """線段是否進入矩形內部（碰到邊線不算）。"""
        if self.axis == "h":
            lo, hi = sorted((self.x1, self.x2))
            return r.y < self.y1 < r.y2 and lo < r.x2 and hi > r.x
        if self.axis == "v":
            lo, hi = sorted((self.y1, self.y2))
            return r.x < self.x1 < r.x2 and lo < r.y2 and hi > r.y
        # 斜線：取樣檢查
        n = max(int(self.length / 2), 2)
        for i in range(1, n):
            t = i / n
            if r.contains_point(self.x1 + (self.x2 - self.x1) * t, self.y1 + (self.y2 - self.y1) * t):
                return True
        return False


class Arc:
    __slots__ = ("cx", "cy", "r")

    def __init__(self, cx, cy, r) -> None:
        self.cx, self.cy, self.r = cx, cy, r


class ParsedPath:
    def __init__(self) -> None:
        self.segs: list[Seg] = []
        self.arcs: list[Arc] = []
        self.corners: list[tuple[float, float]] = []
        self.errors: list[str] = []
        self.start: tuple[float, float] | None = None
        self.end: tuple[float, float] | None = None


TOKEN_RE = re.compile(r"[MmLlHhVvQqAaZzCcSsTt]|-?\d*\.?\d+(?:e[-+]?\d+)?")


def parse_path(d: str) -> ParsedPath:
    out = ParsedPath()
    tokens = TOKEN_RE.findall(d)
    i = 0
    cmd = None
    cx = cy = 0.0
    sx = sy = 0.0

    def take(n: int) -> list[float]:
        nonlocal i
        vals = []
        for _ in range(n):
            if i >= len(tokens) or re.match(r"[A-Za-z]", tokens[i]):
                raise ValueError("path 參數不足")
            vals.append(float(tokens[i]))
            i += 1
        return vals

    try:
        while i < len(tokens):
            t = tokens[i]
            if re.match(r"[A-Za-z]", t):
                cmd = t
                i += 1
                if cmd in "Zz":
                    out.segs.append(Seg(cx, cy, sx, sy))
                    cx, cy = sx, sy
                    continue
            if cmd is None:
                raise ValueError("path 不是以 M 開頭")
            if cmd in "Mm":
                x, y = take(2)
                if cmd == "m":
                    x, y = cx + x, cy + y
                cx, cy = sx, sy = x, y
                if out.start is None:
                    out.start = (x, y)
                cmd = "L" if cmd == "M" else "l"
            elif cmd in "Ll":
                x, y = take(2)
                if cmd == "l":
                    x, y = cx + x, cy + y
                out.segs.append(Seg(cx, cy, x, y))
                cx, cy = x, y
            elif cmd in "Hh":
                (x,) = take(1)
                if cmd == "h":
                    x = cx + x
                out.segs.append(Seg(cx, cy, x, cy))
                cx = x
            elif cmd in "Vv":
                (y,) = take(1)
                if cmd == "v":
                    y = cy + y
                out.segs.append(Seg(cx, cy, cx, y))
                cy = y
            elif cmd in "Qq":
                qx, qy, x, y = take(4)
                if cmd == "q":
                    qx, qy, x, y = cx + qx, cy + qy, cx + x, cy + y
                # 圓角轉彎：控制點必須是直角頂點（與起點同 x 或 y，與終點同另一軸）
                ok = ((abs(qx - cx) < 0.5 and abs(qy - y) < 0.5) or (abs(qy - cy) < 0.5 and abs(qx - x) < 0.5))
                if not ok or max(abs(x - cx), abs(y - cy)) > 16:
                    out.errors.append(f"Q 曲線 ({cx:g},{cy:g})→({x:g},{y:g}) 不是直角圓角轉彎")
                out.corners.append((qx, qy))
                cx, cy = x, y
            elif cmd in "Aa":
                rx, ry, _rot, _large, _sweep, x, y = take(7)
                if cmd == "a":
                    x, y = cx + x, cy + y
                if rx > 10 or ry > 10:
                    out.errors.append(f"圓弧半徑 {rx:g} 太大；A 只能用來畫交叉跳線（r ≤ 10）")
                out.arcs.append(Arc((cx + x) / 2, (cy + y) / 2, max(rx, ry)))
                cx, cy = x, y
            else:
                raise ValueError(f"不支援的指令 {cmd}（只允許 M L H V Q A）")
    except ValueError as exc:
        out.errors.append(str(exc))
    out.end = (cx, cy)
    return out


# --------------------------------------------------------------- checker ---

class Report:
    def __init__(self, name: str) -> None:
        self.name = name
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def E(self, code: str, msg: str) -> None:
        self.errors.append(f"E-{code}: {msg}")

    def W(self, code: str, msg: str) -> None:
        self.warnings.append(f"W-{code}: {msg}")


def load_icon_library() -> dict[str, str]:
    if not ICON_LIB.exists():
        return {}
    root = ET.parse(ICON_LIB).getroot()
    return {sym.get("id"): normalize_symbol(sym) for sym in root.iter(f"{{{SVG_NS}}}symbol")}


def normalize_symbol(sym: ET.Element) -> str:
    parts = []
    for child in sym:
        attrs = sorted((k, re.sub(r"\s+", " ", v.strip())) for k, v in child.attrib.items())
        parts.append(tag(child) + "".join(f" {k}={v}" for k, v in attrs))
    return "|".join(parts)


def label(el: ET.Element, fallback: str) -> str:
    return el.get("id") or fallback


def check_svg(path: Path) -> Report:
    rep = Report(str(path))
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        rep.E("XML", f"無法解析：{exc}")
        return rep
    if tag(root) != "svg":
        rep.E("XML", "根元素不是 <svg>")
        return rep

    # --- 結構 -----------------------------------------------------------
    vb = [num(v) for v in (root.get("viewBox") or "").replace(",", " ").split()]
    if len(vb) != 4 or vb[0] != 0 or vb[1] != 0 or vb[2] != 1200:
        rep.E("VIEWBOX", f'viewBox 必須是 "0 0 1200 H"，現在是 "{root.get("viewBox")}"')
        W, H = 1200.0, vb[3] if len(vb) == 4 else 800.0
    else:
        W, H = vb[2], vb[3]

    children = list(root)
    if root.get("role") != "img":
        rep.E("A11Y", '<svg> 缺少 role="img"')
    title_el = next((c for c in children if tag(c) == "title"), None)
    desc_el = next((c for c in children if tag(c) == "desc"), None)
    if title_el is None or not (title_el.text or "").strip():
        rep.E("A11Y", "<svg> 缺少有內容的 <title>")
    elif children[0] is not title_el:
        rep.E("A11Y", "<title> 必須是 <svg> 的第一個子元素")
    if desc_el is None or not (desc_el.text or "").strip():
        rep.E("A11Y", "<svg> 缺少有內容的 <desc>")
    labelled = set((root.get("aria-labelledby") or "").split())
    ids = {title_el.get("id") if title_el is not None else None, desc_el.get("id") if desc_el is not None else None}
    if None in ids or not ids <= labelled:
        rep.E("A11Y", 'aria-labelledby 必須同時指向 <title> 與 <desc> 的 id')

    families = [el.get("font-family") or "" for el in root.iter() if el.get("font-family")]
    if not any("JetBrains Mono" in f for f in families):
        rep.W("FONT", "沒有任何元素宣告 'JetBrains Mono' 字型")

    # --- 語言：圖內文字一律英文 ------------------------------------------------
    for t in root.iter(f"{{{SVG_NS}}}text"):
        content = "".join(t.itertext()).strip()
        if any(is_cjk(c) for c in content):
            rep.E("LANG", f"文字「{content}」含中日韓字元；圖內文字一律英文")

    # --- 顏色與禁用元素 ----------------------------------------------------
    for el in root.iter():
        t = tag(el)
        if t in FORBIDDEN_TAGS:
            rep.E("COLOR", f"禁止使用 <{t}>（不可有漸層、濾鏡、陰影、外部圖片、script）")
        for prop in ("fill", "stroke", "stop-color", "color"):
            v = paint(el, prop)
            if v is None:
                continue
            v = v.strip().lower()
            if v.startswith("url("):
                continue  # marker/pattern 參照；pattern 已在上面擋掉
            if v not in ALLOWED_COLORS:
                rep.E("COLOR", f"<{t} {label(el, '')}> {prop}=\"{v}\" 不是米白 {PAPER} 或墨黑 {INK}")
        if "filter" in el.attrib or "filter" in style_props(el) or "box-shadow" in (el.get("style") or ""):
            rep.E("COLOR", f"<{t} {label(el, '')}> 使用了 filter／陰影")

    # --- 收集節點、分區、連線 ------------------------------------------------
    nodes: list[tuple[str, Rect, ET.Element]] = []
    zones: list[tuple[str, Rect, ET.Element]] = []
    zone_titles: list[tuple[str, Rect]] = []
    edges: list[tuple[str, ET.Element]] = []
    labels: list[tuple[str, Rect, str, str]] = []  # (id, mask, text, data-edge)
    free_texts: list[Rect] = []

    def classes(el: ET.Element) -> set[str]:
        return set((el.get("class") or "").split())

    for idx, g in enumerate(root.iter(f"{{{SVG_NS}}}g")):
        cls = classes(g)
        if "node" in cls:
            r = g.find(f"{{{SVG_NS}}}rect")
            name = label(g, f"node#{idx}")
            if r is None:
                rep.E("NODE", f"{name}：g.node 裡找不到 <rect>（節點外框一律用矩形）")
                continue
            nodes.append((name, rect_of(r), g))
        elif "zone" in cls:
            r = g.find(f"{{{SVG_NS}}}rect")
            name = label(g, f"zone#{idx}")
            if r is None:
                rep.E("ZONE", f"{name}：g.zone 裡找不到 <rect>")
                continue
            zones.append((name, rect_of(r), g))
            for t in g.iter(f"{{{SVG_NS}}}text"):
                zone_titles.append((name, text_bbox(t)))
                content = "".join(t.itertext()).strip()
                if content != content.upper():
                    rep.W("ZONE", f"{name} 的標題「{content}」應全大寫")
        elif "label" in cls:
            r = g.find(f"{{{SVG_NS}}}rect")
            t = g.find(f"{{{SVG_NS}}}text")
            name = label(g, f"label#{idx}")
            if r is None or t is None:
                rep.E("LABEL", f"{name}：g.label 必須包含一個遮罩 <rect> 與一個 <text>")
                continue
            content = "".join(t.itertext()).strip()
            mask = rect_of(r)
            if not mask.contains(text_bbox(t, 10.0)):
                rep.E("LABEL", f"{name}：文字「{content}」超出遮罩 {mask}")
            if (paint(r, "fill") or "").strip().lower() != PAPER:
                rep.E("LABEL", f"{name}：遮罩必須是不透明米白 fill=\"{PAPER}\"")
            if len(content) > LABEL_MAX_CHARS:
                rep.E("LABEL", f"{name}：「{content}」{len(content)} 字元，標籤 ≤ {LABEL_MAX_CHARS}")
            if content != content.upper():
                rep.W("LABEL", f"{name}：「{content}」應全大寫")
            labels.append((name, mask, content, g.get("data-edge") or ""))

    for el in root.iter():
        if tag(el) in ("path", "line") and "edge" in classes(el):
            edges.append((label(el, f"edge#{len(edges) + 1}"), el))

    # 不屬於任何 node/zone/label 的文字（主標題等）
    in_group = {id(t) for _, _, g in nodes + zones for t in g.iter(f"{{{SVG_NS}}}text")}
    in_group |= {id(t) for g in root.iter(f"{{{SVG_NS}}}g") if "label" in classes(g)
                 for t in g.iter(f"{{{SVG_NS}}}text")}
    for t in root.iter(f"{{{SVG_NS}}}text"):
        if id(t) not in in_group:
            free_texts.append(text_bbox(t))

    if not nodes:
        rep.E("NODE", "找不到任何 <g class=\"node\">；每個節點必須包在 g.node 裡")
    if not edges:
        rep.W("EDGE", "找不到任何 class=\"edge\" 的 <path>/<line>")

    # --- 數量 -------------------------------------------------------------
    if len(nodes) > MAX_NODES:
        rep.E("COUNT", f"節點 {len(nodes)} 個，超過上限 {MAX_NODES}；回到提案步驟重新拆解")
    if len(edges) > MAX_EDGES:
        rep.E("COUNT", f"連線 {len(edges)} 條，超過上限 {MAX_EDGES}")
    if len(labels) > MAX_LABELS:
        rep.E("COUNT", f"資料流標籤 {len(labels)} 個，超過上限 {MAX_LABELS}；只標 payload 不明顯的線")

    # --- 留白 -------------------------------------------------------------
    canvas = Rect(MARGIN, MARGIN, W - 2 * MARGIN, H - 2 * MARGIN)
    for name, r, _ in nodes + zones:
        if not canvas.contains(r):
            rep.E("MARGIN", f"{name} {r} 距畫布邊緣不足 {MARGIN}px")
    for tb in free_texts:
        if not canvas.contains(tb):
            rep.E("MARGIN", f"文字外框 {tb} 距畫布邊緣不足 {MARGIN}px")

    # --- 分區 -------------------------------------------------------------
    for i, (na, ra, _) in enumerate(zones):
        for nb, rb, _ in zones[i + 1:]:
            if ra.overlaps(rb):
                rep.E("ZONE", f"分區 {na} 與 {nb} 重疊")
    for zname, zr, _ in zones:
        for tname, tb in zone_titles:
            if tname == zname and not zr.contains(tb):
                rep.E("ZONE", f"分區 {zname} 的標題文字 {tb} 超出容器")
    for name, r, _ in nodes:
        owners = [zn for zn, zr, _ in zones if zr.overlaps(r)]
        if not owners:
            rep.W("ZONE", f"{name} 不在任何分區內")
        for zn in owners:
            zr = next(z for n, z, _ in zones if n == zn)
            if not zr.contains(r, ZONE_PAD):
                rep.E("ZONE", f"{name} 與分區 {zn} 邊界內距不足 {ZONE_PAD}px（或跨越分區）")
        for tname, tb in zone_titles:
            if r.overlaps(tb):
                rep.E("ZONE", f"{name} 壓到分區 {tname} 的標題文字")

    # --- 節點 -------------------------------------------------------------
    for i, (na, ra, _) in enumerate(nodes):
        for nb, rb, _ in nodes[i + 1:]:
            if ra.overlaps(rb, NODE_GAP):
                rep.E("NODE", f"{na} 與 {nb} 重疊或間距不足 {NODE_GAP}px")
    for name, r, g in nodes:
        if any(v % 4 for v in (r.x, r.y, r.w, r.h)):
            rep.W("GRID", f"{name} {r} 的位置或尺寸不在 4px 格線上")
        texts = list(g.iter(f"{{{SVG_NS}}}text"))
        if not texts:
            rep.W("TEXT", f"{name} 沒有文字")
        for t in texts:
            tb = text_bbox(t)
            if tb.x < r.x + 4 or tb.x2 > r.x2 - 4 or tb.y < r.y or tb.y2 > r.y2:
                rep.E("TEXT", f"{name} 的文字「{''.join(t.itertext()).strip()}」估計寬 {tb.w:.0f}px，溢出矩形 {r}")
        uses = [u for u in g.iter(f"{{{SVG_NS}}}use") if (href(u) or "").startswith("#icon-")]
        if len(uses) > 1:
            rep.W("ICON", f"{name} 最多 1 個 <use href=\"#icon-…\">，現在 {len(uses)} 個")
        for u in uses:
            ur = Rect(num(u.get("x")), num(u.get("y")), num(u.get("width"), 24), num(u.get("height"), 24))
            if not r.contains(ur):
                rep.E("ICON", f"{name} 的 icon {ur} 超出節點矩形")
            for tb in (text_bbox(t) for t in texts):
                if ur.overlaps(tb):
                    rep.E("ICON", f"{name} 的 icon 與文字重疊")

    # --- icon 必須來自 icon 庫 ------------------------------------------------
    library = load_icon_library()
    local_symbols = {s.get("id"): s for s in root.iter(f"{{{SVG_NS}}}symbol")}
    used_ids = {(href(u) or "")[1:] for u in root.iter(f"{{{SVG_NS}}}use")}
    for sid in sorted(used_ids):
        if not sid.startswith("icon-"):
            continue
        if sid not in local_symbols:
            rep.E("ICON", f"<use href=\"#{sid}\"> 找不到對應的 <symbol>（要複製到 <defs>）")
        elif library and sid not in library:
            rep.E("ICON", f"#{sid} 不在 icon 庫 assets/icons.svg 裡；找不到對應 icon 就不放")
        elif library and normalize_symbol(local_symbols[sid]) != library[sid]:
            rep.E("ICON", f"#{sid} 的內容與 icon 庫不同；請原樣複製，不要自行修改")

    # --- 連線 -------------------------------------------------------------
    parsed: dict[str, ParsedPath] = {}
    for name, el in edges:
        if tag(el) == "line":
            p = ParsedPath()
            p.start = (num(el.get("x1")), num(el.get("y1")))
            p.end = (num(el.get("x2")), num(el.get("y2")))
            p.segs.append(Seg(*p.start, *p.end))
        else:
            p = parse_path(el.get("d") or "")
        parsed[name] = p
        for err in p.errors:
            rep.E("EDGE", f"{name}：{err}")
        if p.start is None or p.end is None:
            rep.E("EDGE", f"{name}：無法讀出起點／終點")
            continue
        has_marker = bool(el.get("marker-end") or "marker-end" in style_props(el))
        dashed = bool(el.get("stroke-dasharray") or "stroke-dasharray" in style_props(el))
        if not has_marker and not dashed:
            rep.W("EDGE", f"{name}：既沒有箭頭 marker-end 也不是虛線；主要資料流要有箭頭，次要關係用虛線")
        if has_marker and dashed:
            rep.W("EDGE", f"{name}：虛線不加箭頭")

        for s in p.segs:
            if s.axis == "diag":
                rep.E("EDGE", f"{name}：線段 ({s.x1:g},{s.y1:g})→({s.x2:g},{s.y2:g}) 是斜線；只能水平或垂直")

        # 端點
        for which, pt, seg in (("起點", p.start, p.segs[0] if p.segs else None),
                               ("終點", p.end, p.segs[-1] if p.segs else None)):
            gap_max = END_GAP_MAX if (which == "終點" and has_marker) else START_GAP_MAX
            gap_min = END_GAP_MIN if (which == "終點" and has_marker) else 0.0
            attach = attach_info(pt, nodes)
            if attach is None:
                rep.E("EDGE", f"{name}：{which} ({pt[0]:g},{pt[1]:g}) 沒有落在任何節點邊緣外 0–{START_GAP_MAX:g}px 的範圍")
                continue
            nname, side, gap, along = attach
            if gap < gap_min - 0.01 or gap > gap_max + 0.01:
                rep.E("EDGE", f"{name}：{which}距 {nname} 的{side}邊 {gap:.1f}px，應在 {gap_min:g}–{gap_max:g}px 之間（建議 6px）")
            if seg is not None and seg.axis != "diag":
                want = "v" if side in ("上", "下") else "h"
                if seg.axis != want:
                    rep.E("EDGE", f"{name}：{which}從 {nname} 的{side}邊出入，第一段必須與該邊垂直")
            if along < 8:
                rep.W("EDGE", f"{name}：{which}距 {nname} 的角落只有 {along:.0f}px，會落在圓角上")

        # 穿越與擦邊
        endpoint_nodes = {a[0] for a in (attach_info(p.start, nodes), attach_info(p.end, nodes)) if a}
        for s in p.segs:
            for nname, r, _ in nodes:
                if s.hits_rect(r):
                    rep.E("EDGE", f"{name}：線段 ({s.x1:g},{s.y1:g})→({s.x2:g},{s.y2:g}) 穿過節點 {nname}")
                elif nname not in endpoint_nodes and s.hits_rect(
                        Rect(r.x - NEAR_GAP, r.y - NEAR_GAP, r.w + 2 * NEAR_GAP, r.h + 2 * NEAR_GAP)):
                    rep.W("EDGE", f"{name}：線段 ({s.x1:g},{s.y1:g})→({s.x2:g},{s.y2:g}) 與節點 {nname} 距離不足 {NEAR_GAP}px")
            for zname, tb in zone_titles:
                if s.hits_rect(tb):
                    rep.E("EDGE", f"{name}：線段穿過分區 {zname} 的標題文字")
            for tb in free_texts:
                if s.hits_rect(tb):
                    rep.E("EDGE", f"{name}：線段穿過文字 {tb}")

    # 同一邊接點間距
    attach_points: dict[tuple[str, str], list[tuple[str, float]]] = {}
    for name, p in parsed.items():
        for pt in (p.start, p.end):
            if pt is None:
                continue
            a = attach_info(pt, nodes)
            if a:
                nname, side, _, _ = a
                coord = pt[0] if side in ("上", "下") else pt[1]
                attach_points.setdefault((nname, side), []).append((name, coord))
    for (nname, side), pts in attach_points.items():
        pts.sort(key=lambda t: t[1])
        for (ea, ca), (eb, cb) in zip(pts, pts[1:]):
            if cb - ca < FAN_GAP - 0.01:
                rep.E("EDGE", f"{ea} 與 {eb} 在 {nname} 的{side}邊接點只相距 {cb - ca:.0f}px，需 ≥ {FAN_GAP}px")

    # 重疊與交叉
    names = list(parsed)
    for i, na in enumerate(names):
        for nb in names[i + 1:]:
            pa, pb = parsed[na], parsed[nb]
            for sa in pa.segs:
                for sb in pb.segs:
                    if sa.axis == "diag" or sb.axis == "diag":
                        continue
                    if sa.axis == sb.axis:
                        if collinear_overlap(sa, sb) > 4:
                            rep.E("EDGE", f"{na} 與 {nb} 有重疊的平行線段；平行線至少錯開 12px")
                    else:
                        x = crossing(sa, sb)
                        if x is not None:
                            hop = any(math.hypot(a.cx - x[0], a.cy - x[1]) <= 10 for a in pa.arcs + pb.arcs)
                            if not hop:
                                rep.E("EDGE", f"{na} 與 {nb} 在 ({x[0]:g},{x[1]:g}) 交叉但沒有跳線；在次要的那條加半圓跳線或改路徑")

    # --- 資料流標籤 ---------------------------------------------------------
    for i, (lname, mask, content, edge_id) in enumerate(labels):
        if edge_id not in parsed:
            rep.E("LABEL", f"{lname}：data-edge=\"{edge_id}\" 不是任何連線的 id")
        else:
            gaps = [g for g in (seg_mask_gap(s, mask) for s in parsed[edge_id].segs) if g is not None]
            gap = min(gaps) if gaps else None
            if gap is None or gap > LABEL_GAP_MAX + 0.01:
                rep.E("LABEL", f"{lname}：遮罩 {mask} 沒有貼著連線 {edge_id}（需與某線段相距 {LABEL_GAP_MIN:g}–{LABEL_GAP_MAX:g}px）")
            elif gap < LABEL_GAP_MIN - 0.01:
                rep.E("LABEL", f"{lname}：遮罩距連線 {edge_id} 只有 {gap:.0f}px，需 ≥ {LABEL_GAP_MIN:g}px")
        for nname, r, _ in nodes:
            if mask.overlaps(r):
                rep.E("LABEL", f"{lname}：遮罩壓到節點 {nname}")
        for zname, tb in zone_titles:
            if mask.overlaps(tb):
                rep.E("LABEL", f"{lname}：遮罩壓到分區 {zname} 的標題")
        for oname, omask, _, _ in labels[i + 1:]:
            if mask.overlaps(omask):
                rep.E("LABEL", f"{lname} 與 {oname} 的遮罩重疊")
        for ename, p in parsed.items():
            if any(s.hits_rect(mask) for s in p.segs):
                rep.E("LABEL", f"{lname}：連線 {ename} 穿過遮罩；標籤要放在線旁邊，不是線上")
    return rep


def seg_mask_gap(s: Seg, m: Rect) -> float | None:
    """水平／垂直線段與遮罩的垂直距離；線段沒有正對遮罩時回傳 None。"""
    if s.axis == "h":
        lo, hi = sorted((s.x1, s.x2))
        if hi < m.x or lo > m.x2:
            return None
        if m.y <= s.y1 <= m.y2:
            return 0.0
        return min(abs(s.y1 - m.y), abs(s.y1 - m.y2))
    if s.axis == "v":
        lo, hi = sorted((s.y1, s.y2))
        if hi < m.y or lo > m.y2:
            return None
        if m.x <= s.x1 <= m.x2:
            return 0.0
        return min(abs(s.x1 - m.x), abs(s.x1 - m.x2))
    return None


def attach_info(pt: tuple[float, float], nodes) -> tuple[str, str, float, float] | None:
    """回傳 (節點, 邊, 與邊的距離, 與最近角落的距離)；點必須在節點外且正對某一邊。"""
    best = None
    px, py = pt
    for name, r, _ in nodes:
        if r.contains_point(px, py):
            return (name, "內部", -1.0, 0.0)
        cands = []
        if r.x - 0.01 <= px <= r.x2 + 0.01:
            cands.append(("上", r.y - py, min(px - r.x, r.x2 - px)))
            cands.append(("下", py - r.y2, min(px - r.x, r.x2 - px)))
        if r.y - 0.01 <= py <= r.y2 + 0.01:
            cands.append(("左", r.x - px, min(py - r.y, r.y2 - py)))
            cands.append(("右", px - r.x2, min(py - r.y, r.y2 - py)))
        for side, gap, along in cands:
            if -0.01 <= gap <= START_GAP_MAX + 0.01 and (best is None or gap < best[2]):
                best = (name, side, max(gap, 0.0), along)
    return best


def collinear_overlap(a: Seg, b: Seg) -> float:
    if a.axis == "h":
        if abs(a.y1 - b.y1) > 1:
            return 0.0
        lo = max(min(a.x1, a.x2), min(b.x1, b.x2))
        hi = min(max(a.x1, a.x2), max(b.x1, b.x2))
    else:
        if abs(a.x1 - b.x1) > 1:
            return 0.0
        lo = max(min(a.y1, a.y2), min(b.y1, b.y2))
        hi = min(max(a.y1, a.y2), max(b.y1, b.y2))
    return hi - lo


def crossing(a: Seg, b: Seg) -> tuple[float, float] | None:
    h, v = (a, b) if a.axis == "h" else (b, a)
    hx1, hx2 = sorted((h.x1, h.x2))
    vy1, vy2 = sorted((v.y1, v.y2))
    if hx1 + 0.5 < v.x1 < hx2 - 0.5 and vy1 + 0.5 < h.y1 < vy2 - 0.5:
        return (v.x1, h.y1)
    return None


# ------------------------------------------------------------------ main ---

def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv if not a.startswith("-")]
    if not files:
        print(__doc__)
        return 2
    failed = 0
    for f in files:
        if not f.exists():
            print(f"✗ {f}: 檔案不存在")
            failed += 1
            continue
        rep = check_svg(f)
        status = "✗" if rep.errors else "✓"
        print(f"{status} {rep.name}  ({len(rep.errors)} 錯誤, {len(rep.warnings)} 警告)")
        for e in rep.errors:
            print(f"    {e}")
        for w in rep.warnings:
            print(f"    {w}")
        if rep.errors:
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
