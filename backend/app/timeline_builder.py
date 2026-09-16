
import io
import math
import os
import uuid
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from app.fonts import font_path

_TIMELINES_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "timelines")

_FONT_REGULAR = font_path("sans")
_FONT_BOLD = font_path("sans_bold")

_PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#008300", "#4a3aa7", "#e34948"]

_CARD_W = 250
_CARD_H = 150
_GAP = 22
_MARGIN = 20
_LINE_Y_PAD = 22

_SHADOW_COLOR = (15, 23, 42, 60)
_SHADOW_OFFSET = (0, 5)
_SHADOW_BLUR = 7


def _with_shadows(base: Image.Image, boxes: list[tuple[list[float], int]]) -> Image.Image:
    shadow_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_layer)
    ox, oy = _SHADOW_OFFSET
    for box, radius in boxes:
        x0, y0, x1, y1 = box
        sd.rounded_rectangle([x0 + ox, y0 + oy, x1 + ox, y1 + oy], radius=radius, fill=_SHADOW_COLOR)
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(_SHADOW_BLUR))
    composited = base.convert("RGBA")
    composited.alpha_composite(shadow_layer)
    return composited.convert("RGB")


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _wrap(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for w in words:
        trial = f"{current} {w}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def build_timeline_image(events: list[dict]) -> bytes | None:
    events = [e for e in (events or []) if isinstance(e, dict) and (e.get("label") or e.get("description"))][:6]
    if not events:
        return None

    n = len(events)
    W = _MARGIN * 2 + n * _CARD_W + (n - 1) * _GAP
    H = _MARGIN * 2 + _CARD_H + _LINE_Y_PAD + 24

    img = Image.new("RGB", (W, H), "#FFFFFF")

    card_boxes = []
    for i in range(n):
        x0 = _MARGIN + i * (_CARD_W + _GAP)
        y0 = _MARGIN
        card_boxes.append(([x0, y0, x0 + _CARD_W, y0 + _CARD_H], 14))
    img = _with_shadows(img, card_boxes)
    draw = ImageDraw.Draw(img)

    title_font = _font(_FONT_BOLD, 17)
    sub_font = _font(_FONT_REGULAR, 13)
    body_font = _font(_FONT_REGULAR, 13)

    line_y = _MARGIN + _CARD_H + _LINE_Y_PAD
    centers = []

    for i, ev in enumerate(events):
        x0 = _MARGIN + i * (_CARD_W + _GAP)
        y0 = _MARGIN
        x1, y1 = x0 + _CARD_W, y0 + _CARD_H
        color = _PALETTE[i % len(_PALETTE)]
        centers.append(x0 + _CARD_W / 2)

        draw.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=color)

        pad = 13
        ty = y0 + pad
        label = ev.get("label") or ""
        for line in _wrap(draw, label, title_font, _CARD_W - pad * 2)[:2]:
            draw.text((x0 + pad, ty), line, font=title_font, fill="#FFFFFF")
            ty += 21

        date = ev.get("date") or ""
        if date:
            draw.text((x0 + pad, ty + 1), date, font=sub_font, fill="#FFFFFF")
            ty += 20

        ty += 6
        draw.line([(x0 + pad, ty), (x1 - pad, ty)], fill=(255, 255, 255, 120), width=1)
        ty += 8

        desc = ev.get("description") or ""
        for line in _wrap(draw, desc, body_font, _CARD_W - pad * 2)[:4]:
            if ty > y1 - 18:
                break
            draw.text((x0 + pad, ty), line, font=body_font, fill="#FFFFFF")
            ty += 18

    if len(centers) > 1:
        draw.line([(centers[0], line_y), (centers[-1], line_y)], fill="#CBD5E1", width=4)
    for i, cx in enumerate(centers):
        color = _PALETTE[i % len(_PALETTE)]
        r = 10
        draw.ellipse([cx - r, line_y - r, cx + r, line_y + r], fill=color, outline="#FFFFFF", width=3)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def build_process_image(steps: list[dict]) -> bytes | None:
    steps = [s for s in (steps or []) if isinstance(s, dict) and (s.get("title") or s.get("description"))][:6]
    if not steps:
        return None

    n = len(steps)
    arrow_w = 32
    W = _MARGIN * 2 + n * _CARD_W + (n - 1) * (_GAP + arrow_w)
    H = _MARGIN * 2 + _CARD_H + 14

    img = Image.new("RGB", (W, H), "#FFFFFF")

    card_boxes = []
    for i in range(n):
        x0 = _MARGIN + i * (_CARD_W + _GAP + arrow_w)
        y0 = _MARGIN + 12
        card_boxes.append(([x0, y0, x0 + _CARD_W, y0 + _CARD_H - 12], 14))
    img = _with_shadows(img, card_boxes)
    draw = ImageDraw.Draw(img)

    badge_font = _font(_FONT_BOLD, 15)
    title_font = _font(_FONT_BOLD, 15)
    body_font = _font(_FONT_REGULAR, 13)

    for i, step in enumerate(steps):
        x0 = _MARGIN + i * (_CARD_W + _GAP + arrow_w)
        y0 = _MARGIN + 12
        x1, y1 = x0 + _CARD_W, y0 + _CARD_H - 12
        color = _PALETTE[i % len(_PALETTE)]

        draw.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=color)

        pad = 13
        ty = y0 + pad + 4
        for line in _wrap(draw, step.get("title") or "", title_font, _CARD_W - pad * 2)[:2]:
            draw.text((x0 + pad, ty), line, font=title_font, fill="#FFFFFF")
            ty += 20
        ty += 6
        for line in _wrap(draw, step.get("description") or "", body_font, _CARD_W - pad * 2)[:5]:
            if ty > y1 - 18:
                break
            draw.text((x0 + pad, ty), line, font=body_font, fill="#FFFFFF")
            ty += 18

        br = 17
        bcx, bcy = x0, y0
        draw.ellipse([bcx - br, bcy - br, bcx + br, bcy + br], fill="#FFFFFF", outline=color, width=3)
        num = str(i + 1)
        nbbox = draw.textbbox((0, 0), num, font=badge_font)
        nw, nh = nbbox[2] - nbbox[0], nbbox[3] - nbbox[1]
        draw.text((bcx - nw / 2 - nbbox[0], bcy - nh / 2 - nbbox[1]), num, font=badge_font, fill=color)

        if i < n - 1:
            ay = y0 + (_CARD_H - 24) / 2
            ax0 = x1 + 6
            ax1 = ax0 + arrow_w - 12
            draw.line([(ax0, ay), (ax1, ay)], fill="#94A3B8", width=3)
            draw.polygon([(ax1 - 1, ay - 7), (ax1 + 9, ay), (ax1 - 1, ay + 7)], fill="#94A3B8")

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _box_edge_point(sx: float, sy: float, tx: float, ty: float, half_w: float, half_h: float) -> tuple[float, float]:
    dx, dy = tx - sx, ty - sy
    if dx == 0 and dy == 0:
        return tx, ty
    candidates = []
    if dx != 0:
        candidates.append(half_w / abs(dx))
    if dy != 0:
        candidates.append(half_h / abs(dy))
    scale = min(candidates + [1.0])
    return tx - dx * scale, ty - dy * scale


def build_concept_map_image(nodes: list[dict], edges: list[dict]) -> bytes | None:
    node_list = [n for n in (nodes or []) if isinstance(n, dict) and (n.get("label") or n.get("id"))][:8]
    if not node_list:
        return None
    id_to_label = {n.get("id"): (n.get("label") or n.get("id")) for n in node_list}
    edge_list = [
        e for e in (edges or [])
        if isinstance(e, dict) and e.get("from") in id_to_label and e.get("to") in id_to_label
    ]
    if not edge_list:
        return None

    n = len(node_list)
    radius = 110 if n <= 4 else 165 if n <= 6 else 220
    box_w, box_h = 140, 48
    W = int(radius * 2 + box_w + 40)
    H = int(radius * 2 + box_h + 40)
    cx, cy = W // 2, H // 2

    positions = {}
    for i, node in enumerate(node_list):
        angle = -math.pi / 2 + 2 * math.pi * i / n
        positions[node.get("id")] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))

    img = Image.new("RGB", (W, H), "#FFFFFF")
    node_boxes = [
        ([px - box_w / 2, py - box_h / 2, px + box_w / 2, py + box_h / 2], 12)
        for px, py in positions.values()
    ]
    img = _with_shadows(img, node_boxes)
    draw = ImageDraw.Draw(img)

    label_font = _font(_FONT_BOLD, 13)
    edge_font = _font(_FONT_REGULAR, 11)

    for edge in edge_list:
        x0, y0 = positions[edge["from"]]
        x1, y1 = positions[edge["to"]]
        ax, ay = _box_edge_point(x0, y0, x1, y1, box_w / 2, box_h / 2)
        draw.line([(x0, y0), (ax, ay)], fill="#94A3B8", width=3)
        ang = math.atan2(ay - y0, ax - x0)
        head_len, head_w = 12, 6
        bx, by = ax - head_len * math.cos(ang), ay - head_len * math.sin(ang)
        left = (bx - head_w * math.sin(ang), by + head_w * math.cos(ang))
        right = (bx + head_w * math.sin(ang), by - head_w * math.cos(ang))
        draw.polygon([(ax, ay), left, right], fill="#94A3B8")
        label = edge.get("label")
        if label:
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            tw = draw.textlength(label, font=edge_font)
            pad = 4
            draw.rectangle([mx - tw / 2 - pad, my - 8, mx + tw / 2 + pad, my + 8], fill="#FFFFFF")
            draw.text((mx - tw / 2, my - 7), label, font=edge_font, fill="#64748B")

    for i, node in enumerate(node_list):
        px, py = positions[node.get("id")]
        color = _PALETTE[i % len(_PALETTE)]
        box = [px - box_w / 2, py - box_h / 2, px + box_w / 2, py + box_h / 2]
        draw.rounded_rectangle(box, radius=12, fill=color)
        lines = _wrap(draw, id_to_label[node.get("id")], label_font, box_w - 20)[:2]
        line_h = 16
        ty = py - (len(lines) * line_h) / 2
        for line in lines:
            tw = draw.textlength(line, font=label_font)
            draw.text((px - tw / 2, ty), line, font=label_font, fill="#FFFFFF")
            ty += line_h

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _save_image(builder, *args) -> str | None:
    try:
        png = builder(*args)
        if not png:
            return None
        os.makedirs(_TIMELINES_DIR, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.png"
        out_path = os.path.join(_TIMELINES_DIR, filename)
        with open(out_path, "wb") as f:
            f.write(png)
        return f"/uploads/timelines/{filename}"
    except Exception:
        return None


def save_timeline_image(events: list[dict]) -> str | None:
    return _save_image(build_timeline_image, events)


def save_process_image(steps: list[dict]) -> str | None:
    return _save_image(build_process_image, steps)


def save_concept_map_image(nodes: list[dict], edges: list[dict]) -> str | None:
    return _save_image(build_concept_map_image, nodes, edges)
