import math
import os
import uuid

from PIL import Image, ImageDraw, ImageFont
from app.fonts import font_path

_FIGURES_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "figures")

_FONT_REGULAR = font_path("sans")
_FONT_ITALIC = font_path("sans_italic")
_FONT_BOLD = font_path("sans_bold")

SS = 3
W, H = 620, 460

INK = (17, 17, 17)
GREY = (130, 130, 130)
FILL = (238, 242, 247)


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        try:
            return ImageFont.truetype(_FONT_REGULAR, size)
        except Exception:
            return ImageFont.load_default()


class Canvas:

    def __init__(self, w: int = W, h: int = H):
        self.w, self.h = w, h
        self.img = Image.new("RGB", (w * SS, h * SS), "white")
        self.d = ImageDraw.Draw(self.img)

    def line(self, p, q, width=2, dashed=False, color=INK):
        if not dashed:
            self.d.line([p[0] * SS, p[1] * SS, q[0] * SS, q[1] * SS],
                        fill=color, width=int(width * SS))
            return
        dx, dy = q[0] - p[0], q[1] - p[1]
        dist = math.hypot(dx, dy) or 1
        step = 7.0
        n = max(1, int(dist / step))
        for i in range(n):
            if i % 2:
                continue
            t0, t1 = i / n, min(1.0, (i + 1) / n)
            self.d.line([(p[0] + dx * t0) * SS, (p[1] + dy * t0) * SS,
                         (p[0] + dx * t1) * SS, (p[1] + dy * t1) * SS],
                        fill=color, width=int(width * SS))

    def poly(self, pts, width=2, fill=None, dashed=False, color=INK):
        if fill:
            self.d.polygon([(x * SS, y * SS) for x, y in pts], fill=fill)
        for i in range(len(pts)):
            self.line(pts[i], pts[(i + 1) % len(pts)], width, dashed, color)

    def ellipse(self, cx, cy, rx, ry, width=2, fill=None, color=INK):
        box = [(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS]
        if fill:
            self.d.ellipse(box, fill=fill)
        self.d.ellipse(box, outline=color, width=int(width * SS))

    def arc(self, cx, cy, rx, ry, start, end, width=2, dashed=False, color=INK):
        box = [(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS]
        if not dashed:
            self.d.arc(box, start, end, fill=color, width=int(width * SS))
            return
        span = end - start
        n = max(2, int(abs(span) / 9))
        for i in range(n):
            if i % 2:
                continue
            self.d.arc(box, start + span * i / n, start + span * (i + 1) / n,
                       fill=color, width=int(width * SS))

    def arrow(self, p, q, width=2, head=9, color=INK, dashed=False):
        self.line(p, q, width, dashed, color)
        ang = math.atan2(q[1] - p[1], q[0] - p[0])
        for s in (0.42, -0.42):
            self.d.line([q[0] * SS, q[1] * SS,
                         (q[0] - head * math.cos(ang - s)) * SS,
                         (q[1] - head * math.sin(ang - s)) * SS],
                        fill=color, width=int(width * SS))

    def text(self, x, y, s, size=17, anchor="mm", italic=False, bold=False, color=INK):
        if not s:
            return
        path = _FONT_ITALIC if italic else (_FONT_BOLD if bold else _FONT_REGULAR)
        self.d.text((x * SS, y * SS), str(s), font=_font(path, int(size * SS)),
                    fill=color, anchor=anchor)

    def dot(self, x, y, r=3.5, color=INK):
        self.d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=color)

    def right_angle(self, corner, p1, p2, size=15):
        def unit(a, b):
            dx, dy = b[0] - a[0], b[1] - a[1]
            m = math.hypot(dx, dy) or 1
            return dx / m, dy / m
        u1, u2 = unit(corner, p1), unit(corner, p2)
        a = (corner[0] + u1[0] * size, corner[1] + u1[1] * size)
        b = (corner[0] + (u1[0] + u2[0]) * size, corner[1] + (u1[1] + u2[1]) * size)
        c = (corner[0] + u2[0] * size, corner[1] + u2[1] * size)
        self.line(a, b, 1.4)
        self.line(b, c, 1.4)

    def label_edge(self, p, q, text, off=17, italic=True, size=17):
        if not text:
            return
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        dx, dy = q[0] - p[0], q[1] - p[1]
        m = math.hypot(dx, dy) or 1
        nx, ny = -dy / m, dx / m
        if (mx - self.w / 2) * nx + (my - self.h / 2) * ny < 0:
            nx, ny = -nx, -ny
        self.text(mx + nx * off, my + ny * off, text, size=size, italic=italic)

    def vertex(self, x, y, name, dx=0, dy=0, size=18):
        self.dot(x, y)
        self.text(x + dx, y + dy, name, size=size, italic=True)

    def finish(self) -> bytes:
        import io
        out = self.img.resize((self.w, self.h), Image.LANCZOS)
        from PIL import ImageChops, ImageOps
        grey = ImageOps.invert(out.convert("L"))
        box = grey.point(lambda p: 255 if p > 12 else 0).getbbox()
        if box:
            pad = 10
            out = out.crop((max(0, box[0] - pad), max(0, box[1] - pad),
                            min(self.w, box[2] + pad), min(self.h, box[3] + pad)))
        buf = io.BytesIO()
        out.save(buf, format="PNG")
        return buf.getvalue()


def _v(values, i, default=""):
    try:
        s = values[i]
        return "" if s is None else str(s)
    except Exception:
        return default



def _cube(c, v, square=True):
    w = 200 if square else 215
    h = 200 if square else 145
    dx, dy = 80, 52
    A = (160, 340); B = (A[0] + w, 340); C = (B[0] + dx, B[1] - dy); D = (A[0] + dx, A[1] - dy)
    A1 = (A[0], A[1] - h); B1 = (B[0], B[1] - h); C1 = (C[0], C[1] - h); D1 = (D[0], D[1] - h)
    c.poly([A1, B1, C1, D1], fill=FILL, width=0)
    for p, q in ((A, D), (D, C), (D, D1)):
        c.line(p, q, dashed=True, color=GREY)
    for p, q in ((A, B), (B, C), (A, A1), (B, B1), (C, C1),
                 (A1, B1), (B1, C1), (C1, D1), (D1, A1)):
        c.line(p, q)
    for pt, name, ox, oy in ((A, "A", -16, 14), (B, "B", 14, 16), (C, "C", 18, 8),
                             (D, "D", -16, -12), (A1, "A\u2081", -18, -8), (B1, "B\u2081", 16, 8),
                             (C1, "C\u2081", 18, -6), (D1, "D\u2081", -16, -16)):
        c.vertex(pt[0], pt[1], name, ox, oy)
    if square:
        c.label_edge(A, B, _v(v, 0), off=20)
    else:
        c.label_edge(A, B, _v(v, 0), off=20)
        c.label_edge(B, C, _v(v, 1), off=14)
        c.label_edge(B, B1, _v(v, 2), off=20)


def _cuboid(c, v):
    _cube(c, v, square=False)


def _pyramid(c, v):
    A = (170, 340); B = (380, 340); C = (450, 292); D = (240, 292)
    S = (310, 105)
    ctr = ((A[0] + C[0]) / 2, (A[1] + C[1]) / 2)
    for p, q in ((A, D), (D, C), (D, S)):
        c.line(p, q, dashed=True, color=GREY)
    c.line(S, ctr, dashed=True, color=GREY)
    for p, q in ((A, B), (B, C), (A, S), (B, S), (C, S)):
        c.line(p, q)
    c.right_angle(ctr, S, C, 12)
    for pt, name, ox, oy in ((A, "A", -16, 14), (B, "B", 14, 16), (C, "C", 18, 8),
                             (D, "D", -16, -12), (S, "S", 0, -18)):
        c.vertex(pt[0], pt[1], name, ox, oy)
    c.label_edge(A, B, _v(v, 0), off=20)
    c.label_edge(S, ctr, _v(v, 1), off=18)


def _prism(c, v):
    A = (175, 345); B = (355, 345); C = (265, 195)
    dx, dy = 85, 55
    A1 = (A[0] + dx, A[1] - dy); B1 = (B[0] + dx, B[1] - dy); C1 = (C[0] + dx, C[1] - dy)
    for p, q in ((A1, B1), (A1, C1), (A, A1)):
        c.line(p, q, dashed=True, color=GREY)
    for p, q in ((A, B), (B, C), (C, A), (B, B1), (C, C1), (B1, C1)):
        c.line(p, q)
    for pt, name, ox, oy in ((A, "A", -16, 12), (B, "B", 6, 20), (C, "C", -16, -10),
                             (A1, "A\u2081", 4, 18), (B1, "B\u2081", 16, 10), (C1, "C\u2081", 14, -12)):
        c.vertex(pt[0], pt[1], name, ox, oy)
    c.label_edge(A, B, _v(v, 0), off=20)
    c.label_edge(B, B1, _v(v, 1), off=16)


def _cylinder(c, v):
    cx, rx, ry = 310, 112, 34
    top, bot = 125, 335
    c.d.rectangle([(cx - rx) * SS, top * SS, (cx + rx) * SS, bot * SS], fill=FILL)
    c.arc(cx, bot, rx, ry, 180, 360, dashed=True, color=GREY)
    c.arc(cx, bot, rx, ry, 0, 180)
    c.line((cx - rx, top), (cx - rx, bot)); c.line((cx + rx, top), (cx + rx, bot))
    c.ellipse(cx, top, rx, ry, fill="white")
    c.line((cx, top), (cx, bot), dashed=True, color=GREY)
    c.line((cx, top), (cx + rx, top), width=1.6)
    c.dot(cx, top); c.dot(cx, bot)
    c.text(cx - 14, top + 14, "O", size=17, italic=True)
    c.label_edge((cx, top), (cx + rx, top), _v(v, 0), off=15)
    c.label_edge((cx, top), (cx, bot), _v(v, 1), off=20)


def _cone(c, v):
    cx, rx, ry = 310, 112, 34
    base, apex = 335, 100
    c.poly([(cx - rx, base), (cx, apex), (cx + rx, base)], fill=FILL, width=0)
    c.arc(cx, base, rx, ry, 180, 360, dashed=True, color=GREY)
    c.arc(cx, base, rx, ry, 0, 180)
    c.line((cx - rx, base), (cx, apex)); c.line((cx + rx, base), (cx, apex))
    c.line((cx, apex), (cx, base), dashed=True, color=GREY)
    c.line((cx, base), (cx + rx, base), width=1.6)
    c.right_angle((cx, base), (cx, apex), (cx + rx, base), 12)
    c.dot(cx, base); c.dot(cx, apex)
    c.text(cx, apex - 18, "S", size=17, italic=True)
    c.text(cx - 15, base + 15, "O", size=17, italic=True)
    c.label_edge((cx, base), (cx + rx, base), _v(v, 0), off=16)
    c.label_edge((cx, apex), (cx, base), _v(v, 1), off=22)


def _sphere(c, v):
    cx, cy, r = 310, 225, 140
    c.ellipse(cx, cy, r, r, fill=FILL)
    c.arc(cx, cy, r, 42, 180, 360, dashed=True, color=GREY)
    c.arc(cx, cy, r, 42, 0, 180)
    end = (cx + r * math.cos(math.radians(-38)), cy + r * math.sin(math.radians(-38)))
    c.line((cx, cy), end, width=1.6)
    c.dot(cx, cy)
    c.text(cx - 16, cy + 12, "O", size=17, italic=True)
    c.label_edge((cx, cy), end, _v(v, 0), off=14)



def _quad(c, pts, names, v, diagonals=False, right=False):
    c.poly(pts, fill=FILL, width=0)
    c.poly(pts)
    if diagonals:
        c.line(pts[0], pts[2], dashed=True, color=GREY)
        c.line(pts[1], pts[3], dashed=True, color=GREY)
    if right:
        for i in range(4):
            c.right_angle(pts[i], pts[(i + 1) % 4], pts[(i - 1) % 4], 14)
    ctr = (sum(p[0] for p in pts) / 4, sum(p[1] for p in pts) / 4)
    for pt, name in zip(pts, names):
        ox = 17 if pt[0] > ctr[0] else -17
        oy = 17 if pt[1] > ctr[1] else -17
        c.vertex(pt[0], pt[1], name, ox, oy)
    for i in range(4):
        c.label_edge(pts[i], pts[(i + 1) % 4], _v(v, i), off=19)


def _square_(c, v):
    _quad(c, [(200, 350), (440, 350), (440, 110), (200, 110)], "ABCD", v, right=True)


def _rectangle(c, v):
    _quad(c, [(150, 330), (470, 330), (470, 140), (150, 140)], "ABCD", v, right=True)


def _parallelogram(c, v):
    _quad(c, [(150, 345), (390, 345), (470, 140), (230, 140)], "ABCD", v)


def _trapezoid(c, v):
    _quad(c, [(130, 345), (490, 345), (400, 140), (220, 140)], "ABCD", v)


def _rhombus(c, v):
    _quad(c, [(310, 380), (480, 230), (310, 80), (140, 230)], "ABCD", v, diagonals=True)


def _triangle(c, v, right=False):
    if right:
        A = (170, 130); B = (170, 355); C = (470, 355)
    else:
        A = (300, 110); B = (140, 355); C = (480, 355)
    c.poly([A, B, C], fill=FILL, width=0)
    c.poly([A, B, C])
    if right:
        c.right_angle(B, A, C, 18)
    else:
        foot = (A[0], B[1])
        c.line(A, foot, dashed=True, color=GREY)
        c.right_angle(foot, A, C, 13)
        c.text(A[0] + 16, (A[1] + foot[1]) / 2, "h", size=17, italic=True)
    c.vertex(*A, "A", -18 if right else 0, 0 if right else -18)
    c.vertex(*B, "B", -18, 16)
    c.vertex(*C, "C", 18, 16)
    c.label_edge(B, C, _v(v, 0), off=20)
    c.label_edge(A, B, _v(v, 1), off=20)
    c.label_edge(A, C, _v(v, 2), off=20)


def _right_triangle(c, v):
    _triangle(c, v, right=True)


def _circle(c, v):
    cx, cy, r = 310, 225, 150
    c.ellipse(cx, cy, r, r, fill=FILL)
    end = (cx + r, cy)
    c.line((cx, cy), end, width=1.6)
    c.dot(cx, cy)
    c.text(cx - 16, cy + 14, "O", size=17, italic=True)
    c.label_edge((cx, cy), end, _v(v, 0) or "R", off=16)


def _angle(c, v):
    O = (150, 350)
    r1 = (520, 350)
    ang = math.radians(-38)
    r2 = (O[0] + 390 * math.cos(ang), O[1] + 390 * math.sin(ang))
    c.line(O, r1); c.line(O, r2)
    c.arc(O[0], O[1], 78, 78, -38, 0)
    c.text(O[0] + 100, O[1] - 30, _v(v, 0) or "\u03b1", size=19, italic=True)
    c.vertex(*O, "O", -18, 14)
    c.text(r1[0] - 4, r1[1] + 20, "A", size=17, italic=True)
    c.text(r2[0] + 14, r2[1] - 6, "B", size=17, italic=True)



_UNIT = 42
_OX, _OY = 300, 230
_XMIN, _XMAX, _YMIN, _YMAX = 70, 550, 55, 405


def _axes(c):
    x0, x1, y0, y1 = _XMIN, _XMAX, _YMIN, _YMAX
    for i in range(-8, 9):
        gx = _OX + i * _UNIT
        if x0 < gx < x1:
            c.line((gx, y0), (gx, y1), width=0.8, color=(226, 230, 236))
        gy = _OY + i * _UNIT
        if y0 < gy < y1:
            c.line((x0, gy), (x1, gy), width=0.8, color=(226, 230, 236))
    c.arrow((x0, _OY), (x1, _OY))
    c.arrow((_OX, y1), (_OX, y0))
    c.text(x1 - 4, _OY + 20, "x", size=18, italic=True)
    c.text(_OX + 20, y0 + 4, "y", size=18, italic=True)
    c.text(_OX - 14, _OY + 15, "0", size=16)
    for i in range(-5, 6):
        if i == 0:
            continue
        gx = _OX + i * _UNIT
        if x0 + 12 < gx < x1 - 22:
            c.line((gx, _OY - 5), (gx, _OY + 5), width=1.4)
            c.text(gx, _OY + 17, i, size=14, color=GREY)
        gy = _OY - i * _UNIT
        if y0 + 22 < gy < y1 - 12:
            c.line((_OX - 5, gy), (_OX + 5, gy), width=1.4)
            c.text(_OX - 17, gy, i, size=14, color=GREY)


def _num(values, i, default=1.0):
    try:
        return float(str(values[i]).replace(",", ".").strip())
    except Exception:
        return default


def _stroke(c, run):
    if len(run) > 1:
        c.d.line([(p[0] * SS, p[1] * SS) for p in run], fill=INK,
                 width=int(2.6 * SS), joint="curve")


def _plot(c, fn, label):
    _axes(c)
    run = []
    steps = 900
    span = (_XMAX - _XMIN) / _UNIT
    for k in range(steps + 1):
        xr = (_XMIN - _OX) / _UNIT + k * span / steps
        try:
            yr = fn(xr)
        except Exception:
            yr = None
        ok = isinstance(yr, (int, float)) and yr == yr and abs(yr) < 40
        py = _OY - yr * _UNIT if ok else 0
        if ok and _YMIN <= py <= _YMAX:
            run.append((_OX + xr * _UNIT, py))
        else:
            _stroke(c, run)
            run = []
    _stroke(c, run)
    if label:
        c.text(_XMAX - 12, _YMIN + 16, label, size=19, italic=True, anchor="rm")


def _fmt(n):
    return str(int(n)) if float(n) == int(n) else str(n)


def _term(coef, suffix):
    if not coef:
        return ""
    sign = "+" if coef > 0 else "−"
    mag = abs(coef)
    body = "" if (mag == 1 and suffix) else _fmt(mag)
    return " " + sign + " " + body + suffix


def _plot_linear(c, v):
    k, b = _num(v, 0, 1), _num(v, 1, 0)
    lead = ("" if k == 1 else ("−" if k == -1 else _fmt(k))) + "x"
    _plot(c, lambda x: k * x + b, "y = " + lead + _term(b, ""))


def _plot_parabola(c, v):
    a, b, d = _num(v, 0, 1), _num(v, 1, 0), _num(v, 2, 0)
    lead = ("" if a == 1 else ("−" if a == -1 else _fmt(a))) + "x²"
    _plot(c, lambda x: a * x * x + b * x + d,
          "y = " + lead + _term(b, "x") + _term(d, ""))


def _plot_hyperbola(c, v):
    k = _num(v, 0, 1)
    _plot(c, lambda x: None if abs(x) < 1e-6 else k / x, "y = " + _fmt(k) + "/x")


def _plot_sine(c, v):
    a, b = _num(v, 0, 1), _num(v, 1, 1)
    amp = "" if a == 1 else _fmt(a)
    freq = "" if b == 1 else _fmt(b)
    _plot(c, lambda x: a * math.sin(b * x), "y = " + amp + "sin " + freq + "x")


def _plot_exponential(c, v):
    a, k = _num(v, 0, 2), _num(v, 1, 1)
    if a <= 0:
        a = 2.0
    lead = "" if k == 1 else _fmt(k) + "·"
    _plot(c, lambda x: k * (a ** x), "y = " + lead + _fmt(a) + "ˣ")


def _coordinate_plane(c, v):
    _axes(c)



def _force_diagram(c, v):
    bx, by, bw, bh = 250, 230, 130, 90
    c.line((90, by + bh), (530, by + bh), width=2.4)
    for gx in range(100, 530, 26):
        c.line((gx, by + bh), (gx - 13, by + bh + 14), width=1.2, color=GREY)
    c.d.rectangle([bx * SS, by * SS, (bx + bw) * SS, (by + bh) * SS], fill=FILL,
                  outline=INK, width=int(2 * SS))
    cx, cy = bx + bw / 2, by + bh / 2
    c.dot(cx, cy)
    for (tx, ty), lab, dflt in (((cx, 90), _v(v, 2), "N"),
                                ((cx, 415), _v(v, 1), "mg"),
                                ((520, cy), _v(v, 0), "F"),
                                ((110, cy), _v(v, 3), "Fтр")):
        c.arrow((cx, cy), (tx, ty), width=2.4)
        offx = 0 if abs(tx - cx) < 1 else (20 if tx > cx else -22)
        offy = 0 if abs(ty - cy) < 1 else (16 if ty > cy else -16)
        c.text(tx + offx, ty + offy, lab or dflt, size=19, italic=True, bold=True)


def _inclined_plane(c, v):
    A = (110, 360)
    B = (510, 360)
    C = (510, 145)
    c.poly([A, B, C], fill=FILL, width=0)
    c.poly([A, B, C])
    c.right_angle(B, A, C, 18)
    c.arc(A[0], A[1], 92, 92, -28, 0)
    c.text(A[0] + 118, A[1] - 26, _v(v, 1) or "α", size=19, italic=True)
    for gx in range(120, 512, 26):
        c.line((gx, 360), (gx - 13, 374), width=1.2, color=GREY)
    px, py = (A[0] + C[0]) / 2, (A[1] + C[1]) / 2
    ang = math.atan2(C[1] - A[1], C[0] - A[0])
    ux, uy = math.cos(ang), math.sin(ang)
    nx, ny = -uy, ux
    hw, hh = 34, 46
    corners = [(px - ux * hw, py - uy * hw),
               (px + ux * hw, py + uy * hw),
               (px + ux * hw + nx * -hh, py + uy * hw + ny * -hh),
               (px - ux * hw + nx * -hh, py - uy * hw + ny * -hh)]
    c.poly(corners, fill=(255, 255, 255))
    bxc = sum(p[0] for p in corners) / 4
    byc = sum(p[1] for p in corners) / 4
    c.dot(bxc, byc)
    c.arrow((bxc, byc), (bxc, byc + 120), width=2.4)
    c.text(bxc + 26, byc + 128, _v(v, 0) or "mg", size=19, italic=True, bold=True)


def _pendulum(c, v):
    P = (310, 80)
    length, ang = 250, math.radians(60)
    bob = (P[0] + length * math.cos(ang), P[1] + length * math.sin(ang))
    low = (P[0], P[1] + length)
    c.line((200, 76), (420, 76), width=3)
    for gx in range(212, 420, 24):
        c.line((gx, 76), (gx - 12, 62), width=1.2, color=GREY)
    c.line(P, low, dashed=True, color=GREY)
    c.line(P, bob, width=2.2)
    c.arc(low[0], low[1], 168, 62, 200, 340, dashed=True, color=GREY)
    c.ellipse(bob[0], bob[1], 26, 26, fill=FILL)
    c.arc(P[0], P[1], 110, 110, 60, 90)
    c.text(P[0] + 42, P[1] + 112, _v(v, 1) or "α", size=19, italic=True)
    c.label_edge(P, bob, _v(v, 0) or "l", off=22)
    c.dot(*P)


def _circuit(c, v):
    L, R, T, B = 120, 500, 120, 350
    c.line((L, T), (R, T), width=2.4)
    c.line((L, B), (R, B), width=2.4)
    c.line((L, T), (L, B), width=2.4)
    c.line((R, T), (R, B), width=2.4)
    c.d.rectangle([292 * SS, (B - 24) * SS, 328 * SS, (B + 24) * SS], fill="white")
    c.line((300, B - 24), (300, B + 24), width=3.4)
    c.line((320, B - 13), (320, B + 13), width=2)
    c.text(310, B + 44, _v(v, 0) or "Источник", size=16)
    c.d.rectangle([265 * SS, (T - 18) * SS, 355 * SS, (T + 18) * SS],
                  fill="white", outline=INK, width=int(2 * SS))
    c.text(310, T - 40, _v(v, 1) or "R", size=18, italic=True)
    cy = (T + B) / 2
    c.ellipse(R, cy, 28, 28, fill="white")
    c.line((R - 20, cy - 20), (R + 20, cy + 20), width=1.8)
    c.line((R - 20, cy + 20), (R + 20, cy - 20), width=1.8)
    c.text(R - 48, cy, _v(v, 2) or "L", size=18, italic=True, anchor="rm")
    c.d.rectangle([(L - 7) * SS, (cy - 28) * SS, (L + 7) * SS, (cy + 28) * SS], fill="white")
    c.dot(L, cy - 28)
    c.dot(L, cy + 28)
    c.line((L, cy + 28), (L + 32, cy - 22), width=2.2)
    c.text(L + 48, cy, _v(v, 3) or "K", size=18, italic=True)



def _atom_model(c, v):
    cx, cy = 310, 225
    symbol = _v(v, 0) or "?"
    shells = [int(s) for s in (_v(v, 1) or "2,8,1").split(",") if s.strip().isdigit()]
    shells = shells[:4] or [2]
    for i, count in enumerate(shells):
        r = 62 + i * 46
        c.ellipse(cx, cy, r, r, width=1.4, color=GREY)
        for k in range(max(1, count)):
            a = 2 * math.pi * k / max(1, count) - math.pi / 2 + i * 0.4
            c.ellipse(cx + r * math.cos(a), cy + r * math.sin(a), 8, 8,
                      width=1.6, fill=INK)
    c.ellipse(cx, cy, 40, 40, fill=FILL)
    c.text(cx, cy - 6, symbol, size=24, bold=True)
    c.text(cx, cy + 15, _v(v, 2), size=13)


_MOLECULES = {
    "h2o": ("O", [("H", 145, 1), ("H", 35, 1)]),
    "co2": ("C", [("O", 180, 2), ("O", 0, 2)]),
    "ch4": ("C", [("H", 90, 1), ("H", 205, 1), ("H", 335, 1), ("H", 270, 1)]),
    "nh3": ("N", [("H", 150, 1), ("H", 30, 1), ("H", 270, 1)]),
    "h2": ("H", [("H", 0, 1)]),
    "o2": ("O", [("O", 0, 2)]),
    "n2": ("N", [("N", 0, 3)]),
    "hcl": ("Cl", [("H", 0, 1)]),
}


def _molecule(c, v):
    key = (_v(v, 0) or "h2o").lower().replace(" ", "")
    centre, arms = _MOLECULES.get(key, _MOLECULES["h2o"])
    cx, cy, bond, r = 310, 225, 132, 40
    for label, deg, order in arms:
        a = math.radians(-deg)
        ax, ay = cx + bond * math.cos(a), cy + bond * math.sin(a)
        nx, ny = -math.sin(a), math.cos(a)
        for o in {1: [0], 2: [-6, 6], 3: [-9, 0, 9]}[order]:
            c.line((cx + nx * o, cy + ny * o), (ax + nx * o, ay + ny * o), width=2.2)
        c.ellipse(ax, ay, r - 8, r - 8, fill=FILL)
        c.text(ax, ay, label, size=22, bold=True)
    c.ellipse(cx, cy, r, r, fill=FILL)
    c.text(cx, cy, centre, size=26, bold=True)



def _wrap_in(c, text, font_size, max_w):
    from PIL import ImageFont
    f = _font(_FONT_REGULAR, int(font_size * SS))
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if c.d.textlength(trial, font=f) / SS <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:3]


def _textbox(c, cx, cy, w, h, text, size=15, shape="rect", fill=FILL):
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    if shape == "oval":
        c.d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius=int(h / 2 * SS),
                              fill=fill, outline=INK, width=int(2 * SS))
    elif shape == "para":
        sk = h * 0.42
        c.poly([(x0 + sk, y0), (x1, y0), (x1 - sk, y1), (x0, y1)], fill=fill)
    elif shape == "diamond":
        c.poly([(cx, y0), (x1, cy), (cx, y1), (x0, cy)], fill=fill)
    else:
        c.d.rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], fill=fill,
                      outline=INK, width=int(2 * SS))
    lines = _wrap_in(c, text, size, w - (h * 0.9 if shape == "diamond" else 18))
    ly = cy - (len(lines) - 1) * (size + 3) / 2
    for line in lines:
        c.text(cx, ly, line, size=size)
        ly += size + 3


def _blok_sxema(c, v):
    KINDS = {"start": ("oval", 170, 46), "end": ("oval", 170, 46),
             "in": ("para", 250, 54), "out": ("para", 250, 54),
             "do": ("rect", 250, 54), "if": ("diamond", 290, 110),
             "yes": ("rect", 200, 54), "no": ("rect", 200, 54)}

    nodes = []
    for raw in v:
        text = str(raw or "").strip()
        if not text:
            continue
        kind, sep, rest = text.partition(":")
        k = kind.strip().lower()
        if sep and k in KINDS:
            nodes.append((k, rest.strip()))
        else:
            nodes.append((None, text))
    if not nodes:
        nodes = [("start", "Оғоз"), ("in", "Маълумот ворид кун"),
                 ("do", "Ҳисоб кун"), ("out", "Натиҷа"), ("end", "Анҷом")]
    if all(k is None for k, _ in nodes):
        YES = {"ҳа", "ха", "да", "ҳa", "yes", "ha", "хa"}
        NO = {"не", "нет", "no", "нест", "yo'q", "йўқ", "yoq"}
        IN_WORDS = {"ворид", "вориди", "ввод", "введите", "input", "kirit", "кирит"}
        OUT_WORDS = {"чоп", "натиҷа", "натича", "ҷавоб", "чавоб", "вывод",
                     "вывести", "печать", "output", "print", "chiqar"}
        guessed = []
        pending = None
        for i, (_, t) in enumerate(nodes):
            word = t.strip().strip(".:!,").lower()
            if word in YES or word in NO:
                pending = "yes" if word in YES else "no"
                continue
            if pending:
                guessed.append((pending, t))
                pending = None
            elif i == 0:
                guessed.append(("start", t))
            elif t.rstrip().endswith("?"):
                guessed.append(("if", t))
            else:
                head = t.split()[0].strip(":.,").lower() if t.split() else ""
                if head in IN_WORDS:
                    guessed.append(("in", t))
                elif head in OUT_WORDS:
                    guessed.append(("out", t))
                else:
                    guessed.append(("do", t))
        if guessed and guessed[-1][0] == "do":
            guessed[-1] = ("end", guessed[-1][1])
        nodes = guessed
    nodes = [(k or "do", t) for k, t in nodes][:9]

    cx = 300
    ends = []

    def connect(target_y, tx=cx):
        for px, py in ends:
            if abs(px - tx) < 1:
                c.arrow((px, py), (tx, target_y), width=1.8)
            else:
                my = (py + target_y) / 2
                c.line((px, py), (px, my), width=1.8)
                c.line((px, my), (tx, my), width=1.8)
                c.arrow((tx, my), (tx, target_y), width=1.8)

    y = 30
    i = 0
    while i < len(nodes):
        kind, text = nodes[i]
        shape, w, h = KINDS[kind]
        if ends:
            connect(y)
        _textbox(c, cx, y + h / 2, w, h, text, shape=shape,
                 size=13 if kind == "if" else 14)
        ends = [(cx, y + h)]
        y += h

        branches = []
        j = i + 1
        while j < len(nodes) and nodes[j][0] in ("yes", "no") and len(branches) < 2:
            branches.append(nodes[j])
            j += 1
        if kind == "if" and branches:
            by = y + 60
            xs = [cx - 160, cx + 160][:len(branches)]
            dia_y = y - h / 2
            for (bkind, btext), bx in zip(branches, xs):
                side = (cx - w / 2, dia_y) if bx < cx else (cx + w / 2, dia_y)
                c.line(side, (bx, dia_y), width=1.8)
                c.arrow((bx, dia_y), (bx, by), width=1.8)
                c.text((side[0] + bx) / 2, dia_y - 12,
                       "ҳа" if bkind == "yes" else "не", size=13)
                _textbox(c, bx, by + 27, 200, 54, btext, size=13)
            ends = [(x, by + 54) for x in xs]
            y = by + 54
            i = j
        else:
            i += 1
        y += 46

    return


def _computer_arch(c, v):
    cy = 250
    _textbox(c, 90, cy, 140, 70, _v(v, 0) or "Воридот")
    _textbox(c, 300, cy, 200, 130, "", shape="rect", fill=(255, 255, 255))
    c.text(300, cy - 46, _v(v, 1) or "Протсессор (CPU)", size=15, bold=True)
    _textbox(c, 250, cy + 10, 84, 46, _v(v, 4) or "АМБ", size=13)
    _textbox(c, 350, cy + 10, 84, 46, _v(v, 5) or "БИ", size=13)
    _textbox(c, 510, cy, 140, 70, _v(v, 2) or "Хориҷот")
    _textbox(c, 300, 70, 220, 70, _v(v, 3) or "Хотира")
    c.arrow((160, cy), (200, cy), width=2)
    c.arrow((400, cy), (440, cy), width=2)
    c.arrow((280, 105), (280, cy - 65), width=2)
    c.arrow((320, cy - 65), (320, 105), width=2)


def _network(c, v, kind="star"):
    label = _v(v, 0) or {"star": "Хаб", "bus": "Шина", "ring": "Ҳалқа"}[kind]
    names = [x for x in (v[1:] if len(v) > 1 else []) if x] or ["ПК 1", "ПК 2", "ПК 3", "ПК 4", "ПК 5"]
    names = names[:6]
    cx, cy = 300, 240
    if kind == "star":
        _textbox(c, cx, cy, 120, 56, label)
        for i, n in enumerate(names):
            a = 2 * math.pi * i / len(names) - math.pi / 2
            x, y = cx + 200 * math.cos(a), cy + 170 * math.sin(a)
            c.line((cx + 60 * math.cos(a), cy + 42 * math.sin(a)), (x, y), width=1.8)
            _textbox(c, x, y, 104, 46, n, size=13)
    elif kind == "bus":
        c.line((50, cy), (550, cy), width=4)
        c.text(300, cy + 26, label, size=14)
        for i, n in enumerate(names):
            x = 90 + i * (420 / max(1, len(names) - 1))
            up = -1 if i % 2 == 0 else 1
            c.line((x, cy), (x, cy + up * 60), width=1.8)
            _textbox(c, x, cy + up * 96, 104, 46, n, size=13)
    else:
        pts = []
        for i in range(len(names)):
            a = 2 * math.pi * i / len(names) - math.pi / 2
            pts.append((cx + 210 * math.cos(a), cy + 175 * math.sin(a)))
        for i in range(len(pts)):
            c.line(pts[i], pts[(i + 1) % len(pts)], width=1.8)
        for p, n in zip(pts, names):
            _textbox(c, p[0], p[1], 104, 46, n, size=13)
        c.text(cx, cy, label, size=15, bold=True)


def _network_star(c, v):
    _network(c, v, "star")


def _network_bus(c, v):
    _network(c, v, "bus")


def _network_ring(c, v):
    _network(c, v, "ring")


def _bezier(c, p0, p1, p2, width=2):
    pts = []
    for i in range(41):
        t = i / 40
        u = 1 - t
        pts.append(((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]) * SS,
                    (u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]) * SS))
    c.d.line(pts, fill=INK, width=int(width * SS), joint="curve")


def _logic_gate(c, v):
    kind = (_v(v, 0) or "and").lower().strip()
    x0, ymid, hh = 220, 230, 62
    y0, y1 = ymid - hh, ymid + hh
    nose = 0
    if kind in ("not", "нет", "инкор"):
        c.poly([(x0, y0), (x0, y1), (x0 + 120, ymid)], fill=FILL)
        c.ellipse(x0 + 134, ymid, 14, 14, fill="white")
        nose = x0 + 148
    elif kind in ("or", "ё", "или", "xor"):
        back = 26 if kind == "xor" else 0
        c.d.polygon([((x0 + back) * SS, y0 * SS), ((x0 + 150) * SS, ymid * SS),
                     ((x0 + back) * SS, y1 * SS)], fill=FILL)
        _bezier(c, (x0 + back, y0), (x0 + back + 60, ymid), (x0 + back + 150, ymid))
        _bezier(c, (x0 + back, y1), (x0 + back + 60, ymid), (x0 + back + 150, ymid))
        _bezier(c, (x0 + back, y0), (x0 + back + 46, ymid), (x0 + back, y1))
        if back:
            _bezier(c, (x0, y0), (x0 + 46, ymid), (x0, y1))
        nose = x0 + back + 150
    else:
        c.d.rectangle([x0 * SS, y0 * SS, (x0 + 70) * SS, y1 * SS], fill=FILL)
        c.d.pieslice([(x0 + 70 - hh) * SS, y0 * SS, (x0 + 70 + hh) * SS, y1 * SS],
                     -90, 90, fill=FILL)
        c.line((x0, y0), (x0 + 70, y0)); c.line((x0, y1), (x0 + 70, y1))
        c.line((x0, y0), (x0, y1))
        c.arc(x0 + 70, ymid, hh, hh, -90, 90)
        nose = x0 + 70 + hh
    single = kind in ("not", "нет", "инкор")
    ins = [ymid] if single else [ymid - 32, ymid + 32]
    for i, y in enumerate(ins):
        c.line((90, y), (x0 + (10 if not single else 0), y), width=2)
        c.text(74, y, _v(v, i + 1) or ("A" if i == 0 else "B"), size=18, italic=True, anchor="rm")
    c.line((nose, ymid), (nose + 110, ymid), width=2)
    c.text(nose + 124, ymid, _v(v, 3) or "F", size=18, italic=True, anchor="lm")
    c.text(300, 60, kind.upper(), size=22, bold=True)


def _binary_table(c, v):
    try:
        n = int(str(_v(v, 0) or "0").strip())
    except Exception:
        n = 0
    n = max(0, min(255, n))
    bits = format(n, "08b")
    weights = [128, 64, 32, 16, 8, 4, 2, 1]
    cw, x0, y = 62, 60, 190
    for i, (b, wt) in enumerate(zip(bits, weights)):
        x = x0 + i * cw
        c.text(x + cw / 2, y - 40, str(wt), size=15, color=GREY)
        c.d.rectangle([x * SS, y * SS, (x + cw) * SS, (y + 62) * SS],
                      fill=FILL if b == "1" else (255, 255, 255),
                      outline=INK, width=int(2 * SS))
        c.text(x + cw / 2, y + 31, b, size=24, bold=True)
    parts = " + ".join(str(wt) for b, wt in zip(bits, weights) if b == "1") or "0"
    c.text(300, y + 110, f"{parts} = {n}", size=20, bold=True)
    c.text(300, y + 150, f"{bits}₂ = {n}₁₀", size=17, italic=True)


def _array_cells(c, v):
    items = [x for x in v if x] or ["12", "7", "45", "3", "28"]
    items = items[:8]
    cw = min(78, 520 / len(items))
    x0 = 300 - cw * len(items) / 2
    y = 200
    cell_pad = 8
    for i, val in enumerate(items):
        x = x0 + i * cw
        c.d.rectangle([x * SS, y * SS, (x + cw) * SS, (y + 62) * SS],
                      fill=FILL, outline=INK, width=int(2 * SS))
        text = str(val)
        size = 17
        f = _font(_FONT_REGULAR, int(size * SS))
        while size > 9 and c.d.textlength(text, font=f) / SS > cw - cell_pad:
            size -= 1
            f = _font(_FONT_REGULAR, int(size * SS))
        if c.d.textlength(text, font=f) / SS > cw - cell_pad:
            while len(text) > 1 and c.d.textlength(text + "…", font=f) / SS > cw - cell_pad:
                text = text[:-1]
            text = text + "…"
        c.text(x + cw / 2, y + 31, text, size=size)
        c.text(x + cw / 2, y + 84, str(i), size=15, color=GREY)
    c.text(300, y + 124, "индекс", size=14, color=GREY)


def _folder_tree(c, v):
    root = _v(v, 0) or "Ҳуҷҷатҳо"
    kids = [x for x in v[1:] if x] or ["Расмҳо", "Мусиқӣ", "Матнҳо"]
    kids = kids[:5]

    def folder(x, y, name, size=15):
        c.poly([(x, y), (x + 22, y), (x + 28, y - 7), (x + 52, y - 7),
                (x + 52, y + 30), (x, y + 30)], fill=(0xF2, 0xD9, 0xA0))
        c.text(x + 64, y + 14, name, size=size, anchor="lm")

    folder(70, 60, root, 17)
    bar_x = 96
    last_y = 60
    for i, k in enumerate(kids):
        y = 130 + i * 66
        c.line((bar_x, last_y + 30 if i == 0 else y - 66 + 15), (bar_x, y + 15), width=1.6, color=GREY)
        c.line((bar_x, y + 15), (bar_x + 42, y + 15), width=1.6, color=GREY)
        folder(bar_x + 50, y, k)


def _client_server(c, v):
    cy = 220
    _textbox(c, 120, cy, 180, 90, _v(v, 0) or "Муштарӣ (Client)")
    _textbox(c, 480, cy, 180, 90, _v(v, 1) or "Сервер")
    c.arrow((212, cy - 22), (388, cy - 22), width=2)
    c.arrow((388, cy + 22), (212, cy + 22), width=2)
    c.text(300, cy - 46, _v(v, 2) or "Дархост", size=14)
    c.text(300, cy + 46, _v(v, 3) or "Ҷавоб", size=14)



SHAPES = {
    "cube": _cube, "cuboid": _cuboid, "pyramid": _pyramid, "prism": _prism,
    "cylinder": _cylinder, "cone": _cone, "sphere": _sphere,
    "square": _square_, "rectangle": _rectangle, "parallelogram": _parallelogram,
    "trapezoid": _trapezoid, "rhombus": _rhombus, "triangle": _triangle,
    "right_triangle": _right_triangle, "circle": _circle, "angle": _angle,
    "coordinate_plane": _coordinate_plane, "plot_linear": _plot_linear,
    "plot_parabola": _plot_parabola, "plot_hyperbola": _plot_hyperbola,
    "plot_sine": _plot_sine, "plot_exponential": _plot_exponential,
    "force_diagram": _force_diagram, "inclined_plane": _inclined_plane,
    "pendulum": _pendulum, "circuit": _circuit,
    "atom_model": _atom_model, "molecule": _molecule,
    "blok_sxema": _blok_sxema, "computer_arch": _computer_arch,
    "network_star": _network_star, "network_bus": _network_bus,
    "network_ring": _network_ring, "logic_gate": _logic_gate,
    "binary_table": _binary_table, "array_cells": _array_cells,
    "folder_tree": _folder_tree, "client_server": _client_server,
}

_CANVAS_SIZE = {
    "blok_sxema": (620, 900),
    "network_star": (620, 500),
    "network_ring": (620, 500),
    "network_bus": (620, 420),
    "folder_tree": (560, 480),
    "logic_gate": (620, 400),
}


def build_figure(shape: str, values: list | None = None) -> bytes | None:
    fn = SHAPES.get((shape or "").strip().lower())
    if fn is None:
        return None
    c = Canvas(*_CANVAS_SIZE.get(shape.strip().lower(), (W, H)))
    fn(c, list(values or []))
    return c.finish()


def save_figure(shape: str, values: list | None = None) -> str | None:
    try:
        png = build_figure(shape, values)
        if not png:
            return None
        os.makedirs(_FIGURES_DIR, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.png"
        with open(os.path.join(_FIGURES_DIR, filename), "wb") as f:
            f.write(png)
        return f"/uploads/figures/{filename}"
    except Exception:
        return None
