import io
import re

from PIL import Image, ImageDraw, ImageFont

import os as _os
import platform as _platform_mod


def _first_existing(*candidates: str) -> str:
    for path in candidates:
        if path and _os.path.exists(path):
            return path
    return candidates[-1] if candidates else ""


_WIN_FONTS = _os.path.join(_os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
_DEJAVU = "/usr/share/fonts/truetype/dejavu"
_LIBERATION = "/usr/share/fonts/truetype/liberation"
_IS_WINDOWS = _platform_mod.system() == "Windows"

_SERIF = _first_existing(
    _os.path.join(_WIN_FONTS, "cambria.ttc") if _IS_WINDOWS else "",
    f"{_DEJAVU}/DejaVuSerif.ttf",
    f"{_LIBERATION}/LiberationSerif-Regular.ttf",
    f"{_DEJAVU}/DejaVuSans.ttf",
)
_SERIF_I = _first_existing(
    _os.path.join(_WIN_FONTS, "cambriai.ttf") if _IS_WINDOWS else "",
    f"{_LIBERATION}/LiberationSerif-Italic.ttf",
    f"{_DEJAVU}/DejaVuSerif.ttf",
    f"{_DEJAVU}/DejaVuSans-Oblique.ttf",
)
_SERIF_B = _first_existing(
    _os.path.join(_WIN_FONTS, "cambriab.ttf") if _IS_WINDOWS else "",
    f"{_DEJAVU}/DejaVuSerif-Bold.ttf",
    f"{_LIBERATION}/LiberationSerif-Bold.ttf",
    f"{_DEJAVU}/DejaVuSans-Bold.ttf",
)
_FALLBACK = _first_existing(
    _os.path.join(_WIN_FONTS, "times.ttf") if _IS_WINDOWS else "",
    f"{_DEJAVU}/DejaVuSans.ttf",
    f"{_LIBERATION}/LiberationSerif-Regular.ttf",
    _SERIF,
)

SS = 3
INK = (17, 17, 17)

_font_cache: dict = {}


_default_font_warned = False


def _font(path, size):
    global _default_font_warned
    key = (path, int(size))
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(path, int(size))
        except Exception:
            try:
                _font_cache[key] = ImageFont.truetype(_FALLBACK, int(size))
            except Exception:
                if not _default_font_warned:
                    _default_font_warned = True
                    try:
                        from app.logger import get_logger
                        get_logger(__name__).error(
                            "MATH FONT MISSING: no usable TTF found (tried %r then %r) — "
                            "falling back to PIL's fixed-size bitmap font. Every formula "
                            "in every PDF will render overlapping or blank. Install "
                            "fonts-dejavu-core and fonts-liberation.", path, _FALLBACK,
                        )
                    except Exception:
                        pass
                _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]


def verify_math_fonts() -> list[str]:
    problems: list[str] = []
    for role, path in (("upright", _SERIF), ("italic", _SERIF_I), ("bold", _SERIF_B)):
        if not path or not _os.path.exists(path):
            problems.append(f"math {role} font not found at {path!r}")
            continue
        try:
            ImageFont.truetype(path, 16)
        except Exception as e:
            problems.append(f"math {role} font at {path!r} failed to load: {e}")
    return problems


SYMBOLS = {
    "pm": "±", "mp": "∓", "times": "×", "cdot": "·", "div": "÷",
    "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠",
    "approx": "≈", "equiv": "≡", "infty": "∞", "propto": "∝",
    "rightarrow": "→", "to": "→", "Rightarrow": "⇒", "leftrightarrow": "↔",
    "longrightarrow": "⟶", "longleftarrow": "⟵", "leftarrow": "←",
    "Longrightarrow": "⟹", "Leftrightarrow": "⇔", "implies": "⇒", "iff": "⇔",
    "rightleftharpoons": "⇌", "rightleftarrows": "⇄",
    "uparrow": "↑", "downarrow": "↓", "nearrow": "↗", "searrow": "↘",
    "sim": "∼", "simeq": "≃", "cong": "≅", "emptyset": "∅",
    "forall": "∀", "exists": "∃", "partial": "∂", "nabla": "∇",
    "in": "∈", "notin": "∉", "subset": "⊂", "cup": "∪", "cap": "∩",
    "angle": "∠", "perp": "⊥", "parallel": "∥", "degree": "°", "circ": "°",
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "varepsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "lambda": "λ",
    "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π", "rho": "ρ", "sigma": "σ",
    "tau": "τ", "phi": "φ", "varphi": "φ", "chi": "χ", "psi": "ψ",
    "omega": "ω", "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ",
    "Pi": "Π", "Sigma": "Σ", "Phi": "Φ", "Omega": "Ω",
    "ldots": "…", "dots": "…", "cdots": "⋯", "prime": "′",
}
_X_ARROWS = {
    "xrightarrow": "→", "xleftarrow": "←",
    "xrightleftharpoons": "⇌", "xleftrightarrow": "↔",
}
_ARROW_CHARS = set("→←↔⇌⇄⟶⟵⇒⇔")

_seen_unknown_macros: set[str] = set()


def _log_unknown_macro(cmd: str) -> None:
    if cmd in _seen_unknown_macros:
        return
    _seen_unknown_macros.add(cmd)
    try:
        from app.logger import get_logger
        get_logger(__name__).info(f"math: unsupported LaTeX macro \\{cmd} — dropped")
    except Exception:
        pass


def _sole_arrow(node):
    if node is None:
        return None
    if node[0] == "txt" and node[1] in _ARROW_CHARS:
        return node[1]
    if node[0] == "row" and len(node[1]) == 1:
        return _sole_arrow(node[1][0])
    return None


_CE_ARROWS = [("<=>", r"\rightleftharpoons"), ("<->", r"\leftrightarrow"),
              ("->", r"\rightarrow"), ("<-", r"\leftarrow")]


def _ce_to_latex(src: str) -> str:
    out = str(src or "")
    for src_arrow, latex in _CE_ARROWS:
        out = out.replace(src_arrow, f" {latex} ")
    out = re.sub(r"(?<=[A-Za-z])(\d+)", r"_{\1}", out)
    out = re.sub(r"\^(\d*[+-])", r"^{\1}", out)
    return out


FUNCTIONS = {"sin", "cos", "tan", "tg", "ctg", "cot", "log", "ln", "lg",
             "exp", "lim", "max", "min", "arcsin", "arccos", "arctan"}
BIG_OPS = {"sum": "∑", "prod": "∏", "int": "∫", "iint": "∬", "oint": "∮"}


_TOKEN = re.compile(r"""
    \\[A-Za-z]+          # command
  | \\[\\{}\[\],;: ]     # escaped char
  | \d+[.,]?\d*          # number
  | [A-Za-zА-Яа-яЁёҲҳҚқӮӯҶҷҒғӢӣ]+  # word (identifier or Cyrillic label)
  | \*\*                 # Python's power operator — must win over the
                         # single-"*" fallback below, or "a**b" tokenizes
                         # as two lone "*" ops and each becomes its own
                         # "·", printing "a· ·b" (confirmed live on a
                         # Python-lesson slide: "қувват = a**b").
  | \s+
  | .                    # any single char
""", re.VERBOSE)


def _tokenize(src: str):
    return ["^" if t == "**" else t for t in _TOKEN.findall(src) if not t.isspace()]



_CYRILLIC = re.compile(r"[\u0400-\u04ff]")


def _unwrap(node):
    if node is not None and node[0] == "fenced" and node[1] == "(" and node[2] == ")":
        return node[3]
    return node


def _is_unit(node) -> bool:
    if node is None:
        return False
    if node[0] == "txt":
        return bool(_CYRILLIC.search(node[1]))
    if node[0] == "row":
        return any(_is_unit(child) for child in node[1])
    return False


class _Parser:
    def __init__(self, tokens):
        self.t = tokens
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def next(self):
        tok = self.peek()
        if tok is not None:
            self.i += 1
        return tok

    def parse_row(self, stop=None):
        out = []
        while True:
            tok = self.peek()
            if tok is None or (stop and tok in stop):
                break
            atom = self.parse_atom()
            if atom is None:
                break
            atom = self.parse_scripts(atom)
            while self.peek() == "/" and not _is_unit(atom):
                self.next()
                den = self.parse_atom()
                if den is None:
                    out.append(atom)
                    out.append(("txt", "/", "op"))
                    return ("row", out)
                den = self.parse_scripts(den)
                if _is_unit(den):
                    out.extend([atom, ("txt", "/", "op"), den])
                    atom = None
                    break
                num = _unwrap(atom)
                if (out and out[-1][0] == "txt" and out[-1][1] in "−+"
                        and (len(out) == 1
                             or (out[-2][0] == "txt" and out[-2][1] in _BINARY))):
                    num = ("row", [out.pop(), num])
                atom = ("frac", num, _unwrap(den))
            if atom is not None:
                out.append(atom)
        return ("row", out)

    def parse_group(self):
        if self.peek() == "{":
            self.next()
            row = self.parse_row(stop={"}"})
            if self.peek() == "}":
                self.next()
            return row
        atom = self.parse_atom()
        return atom if atom is not None else ("row", [])

    @staticmethod
    def _degree_only(node):
        if node is None:
            return None
        if node[0] == "txt" and node[1] == "°":
            return node
        if node[0] == "row" and len(node[1]) == 1:
            return _Parser._degree_only(node[1][0])
        return None

    @staticmethod
    def _collapse_charge(group):
        if group is None or group[0] != "row":
            return group
        flat = ""
        for child in group[1]:
            if child[0] != "txt":
                return group
            flat += child[1]
        if re.fullmatch(r"\d{0,2}[+−-]", flat):
            return ("txt", flat.replace("−", "-"), "up")
        return group

    def parse_scripts(self, base):
        sub = sup = None
        while self.peek() in ("^", "_"):
            which = self.next()
            grp = self.parse_group()
            if which == "^":
                degree = self._degree_only(grp)
                if degree is not None:
                    base = ("row", [base, degree])
                    continue
                sup = self._collapse_charge(grp)
            else:
                sub = grp
        if sub is not None and sup is not None:
            return ("subsup", base, sub, sup)
        if sup is not None:
            return ("sup", base, sup)
        if sub is not None:
            return ("sub", base, sub)
        return base

    def parse_group_src(self) -> str:
        if self.peek() != "{":
            tok = self.next()
            return "" if tok is None else tok
        self.next()
        depth, parts = 1, []
        while True:
            tok = self.next()
            if tok is None:
                break
            if tok == "{":
                depth += 1
            elif tok == "}":
                depth -= 1
                if depth == 0:
                    break
            parts.append(tok)
        return " ".join(parts)

    def parse_atom(self):
        tok = self.next()
        if tok is None:
            return None
        if tok.startswith("\\"):
            cmd = tok[1:]
            if cmd == "frac" or cmd == "dfrac" or cmd == "tfrac":
                return ("frac", self.parse_group(), self.parse_group())
            if cmd == "sqrt":
                index = None
                if self.peek() == "[":
                    self.next()
                    index = self.parse_row(stop={"]"})
                    if self.peek() == "]":
                        self.next()
                return ("sqrt", self.parse_group(), index)
            if cmd in BIG_OPS:
                lower = upper = None
                while self.peek() in ("_", "^"):
                    which = self.next()
                    grp = self.parse_group()
                    if which == "_":
                        lower = grp
                    else:
                        upper = grp
                return ("bigop", BIG_OPS[cmd], lower, upper, None)
            if cmd in ("left", "right"):
                delim = self.next() or ""
                if cmd == "right":
                    return ("txt", "" if delim == "." else delim, "up")
                body = self.parse_row(stop={"\\right"})
                closing = ")"
                if self.peek() == "\\right":
                    self.next()
                    closing = self.next() or ")"
                return ("fenced", "" if delim == "." else delim,
                        "" if closing == "." else closing, body)
            if cmd in _X_ARROWS:
                below = None
                if self.peek() == "[":
                    self.next()
                    below = self.parse_row(stop={"]"})
                    if self.peek() == "]":
                        self.next()
                above = self.parse_group() if self.peek() == "{" else None
                return ("xarrow", _X_ARROWS[cmd], above, below)
            if cmd in ("overset", "underset", "stackrel"):
                label = self.parse_group()
                base = self.parse_group()
                arrow = _sole_arrow(base)
                if arrow:
                    return (("xarrow", arrow, label, None) if cmd != "underset"
                            else ("xarrow", arrow, None, label))
                return (("stack", base, label, None) if cmd != "underset"
                        else ("stack", base, None, label))
            if cmd == "ce":
                return _Parser(_tokenize(_ce_to_latex(self.parse_group_src()))).parse_row()
            if cmd in SYMBOLS:
                return ("txt", SYMBOLS[cmd], "op")
            if cmd in FUNCTIONS:
                return ("txt", cmd, "up")
            if cmd in ("mathrm", "text", "mathbf", "operatorname"):
                inner = self.parse_group()
                if (inner and inner[0] == "row" and len(inner[1]) == 1
                        and inner[1][0][0] == "txt"
                        and re.fullmatch(r"[A-Za-z]", inner[1][0][1] or "")):
                    return ("txt", inner[1][0][1], "it")
                return ("style", "up", inner)
            if cmd in ("," , ";", ":", " ", "!", "quad", "qquad"):
                return ("txt", " ", "up")
            _log_unknown_macro(cmd)
            return ("txt", cmd, "it") if len(cmd) == 1 else ("row", [])
        if tok == "{":
            row = self.parse_row(stop={"}"})
            if self.peek() == "}":
                self.next()
            return row
        if tok in ("}", "]"):
            return ("row", [])
        if tok in ("(", "["):
            close = ")" if tok == "(" else "]"
            body = self.parse_row(stop={close})
            if self.peek() == close:
                self.next()
            return ("fenced", tok, close, body)
        if tok[0].isdigit():
            return ("txt", tok.replace(",", ","), "up")
        if tok in "+-=<>*/|,.;:!?'":
            char = {"*": "·", "-": "−"}.get(tok, tok)
            return ("txt", char, "op")
        if re.match(r"^[A-Za-z]+$", tok):
            if tok in FUNCTIONS:
                return ("txt", tok, "up")
            if len(tok) == 1:
                return ("txt", tok, "it")
            return ("row", [("txt", ch, "it") for ch in tok])
        return ("txt", tok, "up")


_CHEM_COUNT = re.compile(r"[A-Z][a-z]?_\s*\{?\s*\d")
_CHEM_ARROW = re.compile(r"\\(?:ce|x?rightarrow|x?rightleftharpoons|longrightarrow)\b|[→⇌⇄⟶]")


_CHARGE = re.compile(r"(?<=[A-Za-z\}])(\d{0,2})([+-])(?![\w\d])")
_CHARGE_SPACED = re.compile(r"(?<=[A-Za-z\d\}])\s+(\d{1,2})([+-])(?![\w\d])")


def _charge_scripts(latex: str) -> str:
    out = _CHARGE_SPACED.sub(lambda m: "^{%s%s}" % (m.group(1), m.group(2)), latex)
    return _CHARGE.sub(lambda m: "^{%s%s}" % (m.group(1), m.group(2)), out)


def _looks_chemical(latex: str) -> bool:
    src = str(latex or "")
    return bool(_CHEM_ARROW.search(src)) or len(_CHEM_COUNT.findall(src)) >= 2


def _upright(node):
    kind = node[0]
    if kind == "txt":
        return ("txt", node[1], "up" if node[2] == "it" else node[2])
    if kind == "row":
        return ("row", [_upright(c) for c in node[1]])
    return tuple([kind] + [_upright(c) if isinstance(c, tuple) else
                           ([_upright(x) for x in c] if isinstance(c, list) else c)
                           for c in node[1:]])


def parse(latex: str):
    src = str(latex or "").replace("$", " ")
    if _looks_chemical(src):
        return _upright(_Parser(_tokenize(
            chemical_to_latex(_charge_scripts(src), wrap=False))).parse_row())
    return _Parser(_tokenize(src)).parse_row()


_OPERATOR_ONLY = re.compile(r"^[\s*+\-/%=<>!&|^~.,;:]+$")


def is_literal_operator(latex: str) -> bool:
    return bool(_OPERATOR_ONLY.fullmatch(str(latex or "").strip()))



_scratch = ImageDraw.Draw(Image.new("RGB", (8, 8)))


class PilPainter:

    def __init__(self, draw, ink=None):
        self.d = draw
        self.ink = ink or INK

    def text(self, x, y, s, font_path, size_px):
        self.d.text((x, y), s, font=_font(font_path, size_px), fill=self.ink, anchor="ls")

    def line(self, x1, y1, x2, y2, width):
        self.d.line([x1, y1, x2, y2], fill=self.ink, width=max(1, int(width)))


class Box:
    __slots__ = ("w", "asc", "desc", "paint")

    def __init__(self, w, asc, desc, paint):
        self.w, self.asc, self.desc, self.paint = w, asc, desc, paint


_EMPTY = None


def _empty():
    return Box(0, 0, 0, lambda p, x, y: None)


def _text_box(s, size, style):
    if not s:
        return _empty()
    path = _SERIF_I if style == "it" else _SERIF
    f = _font(path, size * SS)
    _, y0, _, y1 = _scratch.textbbox((0, 0), s, font=f, anchor="ls")
    w = _scratch.textlength(s, font=f)

    def paint(p, x, y, _s=s, _path=path, _px=size * SS):
        p.text(x, y, _s, _path, _px)
    return Box(w, max(0, -y0), max(0, y1), paint)


_BINARY = set("+−=<>±∓×·÷≤≥≠≈≡→⇒↔∈∉⊂∪∩∝")


def _layout(node, size):
    kind = node[0]

    if kind == "txt":
        return _text_box(node[1], size, node[2])

    if kind == "style":
        return _layout(node[2], size)

    if kind == "row":
        kids = []
        prev = "none"
        for child in node[1]:
            is_op = ((child[0] == "txt" and child[1] in _BINARY)
                     or child[0] == "xarrow")
            is_arrow = child[0] == "xarrow" or (child[0] == "txt" and child[1] in _ARROW_CHARS)
            unary = is_op and not is_arrow and prev in ("none", "unary", "binary")
            if prev == "punct":
                gap = 0.22 * size * SS
            elif prev in ("none", "unary"):
                gap = 0.0
            elif prev == "binary":
                gap = 0.24 * size * SS
            else:
                gap = 0.24 * size * SS if is_op else 0.0
            kids.append((child, _layout(child, size), False, gap))
            if child[0] == "txt" and child[1] in (",", ";"):
                prev = "punct"
            else:
                prev = ("unary" if unary else "binary") if is_op else "operand"
        w = sum(b.w + g for _, b, _, g in kids)
        asc = max([b.asc for _, b, _, _ in kids], default=0)
        desc = max([b.desc for _, b, _, _ in kids], default=0)

        def paint(p, x, y, _kids=kids):
            cx = x
            for _, b, _, g in _kids:
                cx += g
                b.paint(p, cx, y)
                cx += b.w
        return Box(w, asc, desc, paint)

    if kind == "frac":
        num = _layout(node[1], size * 0.94)
        den = _layout(node[2], size * 0.94)
        pad = 0.30 * size * SS
        gap = 0.22 * size * SS
        axis = -0.30 * size * SS
        w = max(num.w, den.w) + 2 * pad
        yb_num = axis - gap - num.desc
        yb_den = axis + gap + den.asc
        lw = max(1, int(0.055 * size * SS))

        def paint(p, x, y, _n=num, _d=den, _w=w, _pad=pad,
                  _yn=yb_num, _yd=yb_den, _ax=axis, _lw=lw):
            p.line(x + 0.10 * _pad, y + _ax, x + _w - 0.10 * _pad, y + _ax, _lw)
            _n.paint(p, x + (_w - _n.w) / 2, y + _yn)
            _d.paint(p, x + (_w - _d.w) / 2, y + _yd)
        return Box(w, -yb_num + num.asc, yb_den + den.desc, paint)

    if kind in ("sup", "sub", "subsup"):
        base = _layout(node[1], size)
        small = size * 0.68
        up_shift = 0.44 * size * SS
        dn_shift = 0.22 * size * SS
        sup = sub = None
        if kind == "sup":
            sup = _layout(node[2], small)
        elif kind == "sub":
            sub = _layout(node[2], small)
        else:
            sub = _layout(node[2], small)
            sup = _layout(node[3], small)
        sw = max(sup.w if sup else 0, sub.w if sub else 0)
        kern = 0.06 * size * SS

        def paint(p, x, y, _b=base, _sup=sup, _sub=sub, _k=kern,
                  _u=up_shift, _dn=dn_shift):
            _b.paint(p, x, y)
            if _sup:
                _sup.paint(p, x + _b.w + _k, y - _u)
            if _sub:
                _sub.paint(p, x + _b.w + _k, y + _dn)
        asc = max(base.asc, up_shift + sup.asc) if sup else base.asc
        desc = max(base.desc, dn_shift + sub.desc) if sub else base.desc
        return Box(base.w + kern + sw, asc, desc, paint)

    if kind in ("xarrow", "stack"):
        small = size * 0.62
        above = _layout(node[2], small) if node[2] else None
        below = _layout(node[3], small) if node[3] else None
        label_w = max(above.w if above else 0, below.w if below else 0)
        pad = 0.22 * size * SS
        axis = -0.28 * size * SS
        gap = 0.20 * size * SS

        if kind == "stack":
            base = _layout(node[1], size)
            w = max(base.w, label_w)

            def paint(p, x, y, _b=base, _a=above, _bl=below, _w=w,
                      _g=gap, _ax=axis):
                _b.paint(p, x + (_w - _b.w) / 2, y)
                if _a:
                    _a.paint(p, x + (_w - _a.w) / 2, y - _b.asc - _g - _a.desc)
                if _bl:
                    _bl.paint(p, x + (_w - _bl.w) / 2, y + _b.desc + _g + _bl.asc)
            asc = base.asc + (gap + above.asc + above.desc if above else 0)
            desc = base.desc + (gap + below.asc + below.desc if below else 0)
            return Box(w, asc, desc, paint)

        shaft = max(label_w + 2 * pad, 1.7 * size * SS)
        lw = max(1, int(0.055 * size * SS))
        head = 0.30 * size * SS
        char = node[1]
        left_head = char in ("←", "↔", "⇌")
        right_head = char in ("→", "↔", "⇌")

        def paint(p, x, y, _a=above, _b=below, _sh=shaft, _lw=lw, _hd=head,
                  _ax=axis, _g=gap, _lh=left_head, _rh=right_head,
                  _double=(char == "⇌")):
            x0, x1 = x + 0.10 * _hd, x + _sh - 0.10 * _hd
            rows = [_ax] if not _double else [_ax - 0.16 * _hd, _ax + 0.16 * _hd]
            for i, ay in enumerate(rows):
                p.line(x0, y + ay, x1, y + ay, _lw)
                if _rh and (not _double or i == 0):
                    p.line(x1 - _hd, y + ay - 0.42 * _hd, x1, y + ay, _lw)
                    p.line(x1 - _hd, y + ay + 0.42 * _hd, x1, y + ay, _lw)
                if _lh and (not _double or i == 1):
                    p.line(x0 + _hd, y + ay - 0.42 * _hd, x0, y + ay, _lw)
                    p.line(x0 + _hd, y + ay + 0.42 * _hd, x0, y + ay, _lw)
            if _a:
                _a.paint(p, x + (_sh - _a.w) / 2, y + _ax - _g - _a.desc)
            if _b:
                _b.paint(p, x + (_sh - _b.w) / 2, y + _ax + _g + _b.asc)

        asc = -axis + (gap + above.asc + above.desc if above else 0.2 * size * SS)
        desc = axis + (gap + below.asc + below.desc if below else 0.2 * size * SS)
        return Box(shaft, asc, max(desc, 0), paint)

    if kind == "sqrt":
        inner = _layout(node[1], size)
        pad = 0.16 * size * SS
        h = inner.asc + inner.desc + 2 * pad
        sign_w = 0.52 * size * SS
        idx = _layout(node[2], size * 0.55) if node[2] else None
        lead = (idx.w * 0.8 if idx else 0)
        w = lead + sign_w + inner.w + 2 * pad
        lw = max(1, int(0.05 * size * SS))

        def paint(p, x, y, _in=inner, _h=h, _sw=sign_w, _pad=pad,
                  _idx=idx, _lead=lead, _lw=lw):
            top = y - _in.asc - _pad
            x0 = x + _lead
            p.line(x0, top + 0.60 * _h, x0 + 0.20 * _sw, top + 0.52 * _h, _lw)
            p.line(x0 + 0.20 * _sw, top + 0.52 * _h, x0 + 0.46 * _sw, top + _h, _lw + 1)
            p.line(x0 + 0.46 * _sw, top + _h, x0 + _sw, top, _lw)
            p.line(x0 + _sw, top, x0 + _sw + _in.w + 2 * _pad, top, _lw)
            _in.paint(p, x0 + _sw + _pad, y)
            if _idx:
                _idx.paint(p, x, top + 0.52 * _h)
        return Box(w, inner.asc + 2 * pad, inner.desc, paint)

    if kind == "bigop":
        glyph = _text_box(node[1], size * 1.7, "up")
        lower = _layout(node[2], size * 0.62) if node[2] else None
        upper = _layout(node[3], size * 0.62) if node[3] else None
        w = max(glyph.w, lower.w if lower else 0, upper.w if upper else 0)
        gap = 0.10 * size * SS
        asc = glyph.asc + ((upper.asc + upper.desc + gap) if upper else 0)
        desc = glyph.desc + ((lower.asc + lower.desc + gap) if lower else 0)

        def paint(p, x, y, _g=glyph, _lo=lower, _up=upper, _w=w, _gap=gap):
            _g.paint(p, x + (_w - _g.w) / 2, y)
            if _up:
                _up.paint(p, x + (_w - _up.w) / 2, y - _g.asc - _gap - _up.desc)
            if _lo:
                _lo.paint(p, x + (_w - _lo.w) / 2, y + _g.desc + _gap + _lo.asc)
        return Box(w, asc, desc, paint)

    if kind == "fenced":
        inner = _layout(node[3], size)
        height = (inner.asc + inner.desc) / SS
        fsize = max(size, height * 0.92)
        lb = _text_box(node[1], fsize, "up") if node[1] else _empty()
        rb = _text_box(node[2], fsize, "up") if node[2] else _empty()
        shift = (inner.asc - inner.desc) / 2 - (lb.asc - lb.desc) / 2

        def paint(p, x, y, _l=lb, _r=rb, _in=inner, _s=shift):
            _l.paint(p, x, y + _s)
            _in.paint(p, x + _l.w, y)
            _r.paint(p, x + _l.w + _in.w, y + _s)
        return Box(lb.w + inner.w + rb.w,
                   max(inner.asc, lb.asc + shift),
                   max(inner.desc, lb.desc - shift), paint)

    return _empty()


def render_png(latex: str, size: float = 15, pad: int = 4,
               bg: str = "white", oversample: int = 1) -> bytes | None:
    try:
        box = _layout(parse(latex), size * oversample)
        if box.w <= 0:
            return None
        w = int(box.w + 2 * pad * SS * oversample) + 2
        h = int(box.asc + box.desc + 2 * pad * SS * oversample) + 2
        if bg is None:
            img = Image.new("RGBA", (max(w, 4), max(h, 4)), (255, 255, 255, 0))
        else:
            img = Image.new("RGB", (max(w, 4), max(h, 4)), bg)
        box.paint(PilPainter(ImageDraw.Draw(img)), pad * SS * oversample,
                  pad * SS * oversample + box.asc)
        out = img.resize((max(1, round(w / SS)), max(1, round(h / SS))), Image.LANCZOS)
        buf = io.BytesIO()
        out.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def measure(latex: str, size: float = 15):
    try:
        box = _layout(parse(latex), size)
        return box.w / SS, box.asc / SS, box.desc / SS
    except Exception:
        return 0.0, 0.0, 0.0



M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _run(text, upright):
    if text == "":
        return ""
    props = '<m:rPr><m:sty m:val="p"/></m:rPr>' if upright else ""
    return f'<m:r>{props}<m:t xml:space="preserve">{_esc(text)}</m:t></m:r>'


def _omml(node) -> str:
    kind = node[0]

    if kind == "txt":
        text = node[1] + " " if node[1] in (",", ";") else node[1]
        return _run(text, node[2] != "it")

    if kind == "style":
        return _omml(node[2])

    if kind == "row":
        return _omml_seq(node[1])

    if kind == "frac":
        return ('<m:f><m:fPr><m:type m:val="bar"/></m:fPr>'
                f'<m:num>{_omml(node[1])}</m:num>'
                f'<m:den>{_omml(node[2])}</m:den></m:f>')

    if kind == "sup":
        return (f'<m:sSup><m:e>{_omml(node[1])}</m:e>'
                f'<m:sup>{_omml(node[2])}</m:sup></m:sSup>')

    if kind == "sub":
        return (f'<m:sSub><m:e>{_omml(node[1])}</m:e>'
                f'<m:sub>{_omml(node[2])}</m:sub></m:sSub>')

    if kind == "subsup":
        return (f'<m:sSubSup><m:e>{_omml(node[1])}</m:e>'
                f'<m:sub>{_omml(node[2])}</m:sub>'
                f'<m:sup>{_omml(node[3])}</m:sup></m:sSubSup>')

    if kind == "sqrt":
        if node[2] is None:
            return ('<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr>'
                    f'<m:deg/><m:e>{_omml(node[1])}</m:e></m:rad>')
        return (f'<m:rad><m:radPr><m:degHide m:val="0"/></m:radPr>'
                f'<m:deg>{_omml(node[2])}</m:deg>'
                f'<m:e>{_omml(node[1])}</m:e></m:rad>')

    if kind == "bigop":
        lower, upper, body = node[2], node[3], node[4]
        props = [f'<m:chr m:val="{_esc(node[1])}"/>', '<m:limLoc m:val="undOvr"/>']
        if lower is None:
            props.append('<m:subHide m:val="1"/>')
        if upper is None:
            props.append('<m:supHide m:val="1"/>')
        return ('<m:nary><m:naryPr>' + "".join(props) + '</m:naryPr>'
                f'<m:sub>{_omml(lower) if lower else ""}</m:sub>'
                f'<m:sup>{_omml(upper) if upper else ""}</m:sup>'
                f'<m:e>{_omml(body) if body else ""}</m:e></m:nary>')

    if kind in ("xarrow", "stack"):
        char = node[1]
        if kind == "xarrow" and node[2] is not None:
            char = {"→": "⟶", "←": "⟵", "↔": "⟷"}.get(char, char)
        base = (_run(char, True) if kind == "xarrow" else _omml(node[1]))
        inner = f'<m:e>{base}</m:e>'
        if node[3] is not None:
            inner = (f'<m:limLow><m:e>{base}</m:e>'
                     f'<m:lim>{_omml(node[3])}</m:lim></m:limLow>')
            inner = f'<m:e>{inner}</m:e>'
        if node[2] is not None:
            return f'<m:limUpp>{inner}<m:lim>{_omml(node[2])}</m:lim></m:limUpp>'
        return inner[len('<m:e>'):-len('</m:e>')] if inner.startswith('<m:e>') else inner

    if kind == "fenced":
        return ('<m:d><m:dPr>'
                f'<m:begChr m:val="{_esc(node[1])}"/>'
                f'<m:endChr m:val="{_esc(node[2])}"/></m:dPr>'
                f'<m:e>{_omml(node[3])}</m:e></m:d>')

    return ""


def _omml_seq(children) -> str:
    out = []
    for i, child in enumerate(children):
        if child[0] == "bigop" and child[4] is None:
            tail = ("row", list(children[i + 1:]))
            out.append(_omml(("bigop", child[1], child[2], child[3], tail)))
            break
        out.append(_omml(child))
    return "".join(out)


def to_omml(latex: str, display: bool = False) -> str:
    body = _omml(parse(latex))
    if display:
        return (f'<m:oMathPara xmlns:m="{M_NS}">'
                f'<m:oMathParaPr><m:jc m:val="center"/></m:oMathParaPr>'
                f'<m:oMath>{body}</m:oMath></m:oMathPara>')
    return f'<m:oMath xmlns:m="{M_NS}">{body}</m:oMath>'


def omml_element(latex: str, display: bool = False):
    try:
        from docx.oxml import parse_xml
        return parse_xml(to_omml(latex, display))
    except Exception:
        return None



SUP_CHARS = {
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6",
    "⁷": "7", "⁸": "8", "⁹": "9", "ⁿ": "n", "ⁱ": "i", "⁺": "+", "⁻": "-",
    "⁽": "(", "⁾": ")",
}
SUB_CHARS = {chr(0x2080 + d): str(d) for d in range(10)}
SUB_CHARS.update({"₊": "+", "₋": "-", "₌": "=", "₍": "(", "₎": ")",
                  "ₙ": "n", "ₖ": "k", "ᵢ": "i", "ₐ": "a", "ₓ": "x"})

_BASE = r"[A-Za-z0-9А-Яа-яЁёҲҳҚқӮӯҶҷҒғӢӣ)\]]"
_SUP_RUN = re.compile(f"({_BASE}+)([{''.join(SUP_CHARS)}]+)")
_SUB_RUN = re.compile(f"({_BASE}+)([{''.join(SUB_CHARS)}]+)")
_BARE_POW = re.compile(r"(" + _BASE + r"+)\^(?:\{([^{}$]{1,20})\}|(-?\w+))")
_BARE_LATEX_CMD = re.compile(r"\\[A-Za-z]+\{[^{}$]{1,60}\}")
_CASES_ENV = re.compile(r"\\begin\{cases\}(.*?)\\end\{cases\}", re.DOTALL)


def _flatten_cases_env(text: str) -> str:
    def repl(m: re.Match) -> str:
        parts = [p.strip() for p in re.split(r"\\\\", m.group(1)) if p.strip()]
        return "; ".join(parts)
    return _CASES_ENV.sub(repl, text)
_LATEX_POW = re.compile(r"([\^_])(?!\{)(\\?[A-Za-z0-9]+|-\d+)")


def _sup_to_latex(run: str) -> str:
    return "".join(SUP_CHARS.get(c, c) for c in run)


def _sub_to_latex(run: str) -> str:
    return "".join(SUB_CHARS.get(c, c) for c in run)


def brace_scripts(latex: str) -> str:
    return _LATEX_POW.sub(lambda m: f"{m.group(1)}{{{m.group(2)}}}", str(latex or ""))


def plain_to_latex(text: str) -> str:
    s = str(text or "").strip()
    if not s:
        return ""
    s = _SUP_RUN.sub(lambda m: f"{m.group(1)}^{{{_sup_to_latex(m.group(2))}}}", s)
    s = _SUB_RUN.sub(lambda m: f"{m.group(1)}_{{{_sub_to_latex(m.group(2))}}}", s)
    s = re.sub(r"√\s*\(([^()]{1,40})\)", r"\\sqrt{\1}", s)
    s = re.sub(r"√\s*([A-Za-z0-9^{}]+)", r"\\sqrt{\1}", s)
    return brace_scripts(s)


_ELEMENTS = set("""
H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni
Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I
Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt
Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr
Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og
""".split())

_CHEM_WORD = re.compile(r"(?<![A-Za-z$\_])((?:[A-Z][a-z]?\d{0,3}){1,10}(?:\d{0,2}[+-])?)(?![\w])")
_CHEM_PART = re.compile(r"([A-Z][a-z]?)(\d{0,3})")
_SIMPLE_MOLECULES = {"O2", "O3", "H2", "N2", "F2", "Cl2", "Br2", "I2",
                     "S8", "P4", "C60"}


_CHEM_CHARGE_TAIL = re.compile(r"(\d{0,2})([+-])$")


def _chemical_spans(token: str) -> str | None:
    charge = ""
    tail = _CHEM_CHARGE_TAIL.search(token)
    if tail:
        charge = tail.group(1) + tail.group(2)
        token = token[:tail.start()]
    parts = _CHEM_PART.findall(token)
    if not parts or "".join(a + b for a, b in parts) != token:
        return None
    if not charge and not any(count for _, count in parts):
        return None
    if not all(sym in _ELEMENTS for sym, _ in parts):
        return None
    if any(count and (count[0] == "0" or count == "1") for _, count in parts):
        return None
    if len(parts) == 1 and not charge and token not in _SIMPLE_MOLECULES:
        return None
    body = "".join(f"{sym}_{{{count}}}" if count else sym for sym, count in parts)
    return f"{body}^{{{charge}}}" if charge else body


def chemical_to_latex(part: str, wrap: bool = True) -> str:
    def repl(m):
        latex = _chemical_spans(m.group(1))
        if not latex:
            return m.group(1)
        return f"${latex}$" if wrap else latex
    return _CHEM_WORD.sub(repl, part)


def normalize_math(text: str) -> str:
    raw = str(text or "")
    if not raw:
        return raw
    if "\\begin{cases}" in raw:
        raw = _flatten_cases_env(raw)
    if raw.count("$") % 2:
        return raw
    out = []
    for i, part in enumerate(raw.split("$")):
        if i % 2:
            out.append(brace_scripts(part))
            continue
        part = _BARE_LATEX_CMD.sub(lambda m: f"${m.group(0)}$", part)
        part = _BARE_POW.sub(
            lambda m: f"${m.group(1)}^{{{m.group(2) or m.group(3)}}}$", part)
        part = _SUP_RUN.sub(
            lambda m: f"${m.group(1)}^{{{_sup_to_latex(m.group(2))}}}$", part)
        part = _SUB_RUN.sub(
            lambda m: f"${m.group(1)}_{{{_sub_to_latex(m.group(2))}}}$", part)
        part = chemical_to_latex(part)
        out.append(part)
    joined = "$".join(out)
    return joined.replace("$$", "")



_SCRIPTABLE = {"txt", "row", "sup", "sub", "subsup", "fenced", "style"}


def _flat_text(node) -> str | None:
    kind = node[0]
    if kind == "txt":
        return node[1]
    if kind == "style":
        return _flat_text(node[2])
    if kind == "row":
        parts = []
        prev_op = True
        for child in node[1]:
            flat = _flat_text(child)
            if flat is None:
                return None
            is_op = child[0] == "txt" and child[1] in _BINARY
            if is_op and not prev_op:
                parts.append(f" {flat} ")
            else:
                parts.append(flat)
            prev_op = is_op
        return "".join(parts)
    if kind == "fenced":
        inner = _flat_text(node[3])
        return None if inner is None else f"{node[1]}{inner}{node[2]}"
    return None


def script_segments(latex: str):
    try:
        root = parse(latex)
    except Exception:
        return None
    segs: list[tuple[str, str]] = []

    def walk(node, prev_op=True) -> bool:
        kind = node[0]
        if kind == "row":
            for child in node[1]:
                is_op = child[0] == "txt" and child[1] in _BINARY
                if is_op and not prev_op:
                    segs.append((" ", ""))
                if not walk(child, prev_op):
                    return False
                if is_op and not prev_op:
                    segs.append((" ", ""))
                prev_op = is_op
            return True
        if kind == "style":
            return walk(node[2], prev_op)
        if kind in ("sup", "sub", "subsup"):
            base = _flat_text(node[1])
            if base is None:
                return False
            scripts = ([(node[2], "sub"), (node[3], "sup")]
                       if kind == "subsup" else
                       [(node[2], "sup" if kind == "sup" else "sub")])
            texts = [(_flat_text(n), k) for n, k in scripts]
            if any(t is None for t, _ in texts):
                return False
            segs.append((base, ""))
            segs.extend((t.strip(), k) for t, k in texts)
            return True
        flat = _flat_text(node)
        if flat is None:
            return False
        segs.append((flat, ""))
        return True

    if not walk(root):
        return None
    merged: list[tuple[str, str]] = []
    for text, kind in segs:
        if not text:
            continue
        if merged and merged[-1][1] == kind == "":
            merged[-1] = (merged[-1][0] + text, "")
        else:
            merged.append((text, kind))
    return merged or None


MATH_SPAN = re.compile(r"\$([^$\n]{1,400}?)\$")
