# -*- coding: utf-8 -*-
"""Typesetting for the mathematics in a konspekt.

The model writes formulas in LaTeX (see the "latex" field and the $...$
convention in ai_service). This module turns that one source into the two
forms the exports need:

  * OMML — Office Math Markup Language, which IS the modern Microsoft
    Equation. A formula emitted this way is a native Word equation: the
    teacher can click it and edit it in the equation editor, and it prints
    with Word's own math typography. This is what makes the .docx a real
    mathematical document rather than a picture of one.

  * A drawn image, for the PDF. ReportLab has no math engine at all, so
    the alternative would be "x^2" printed literally. The same AST is laid
    out here with real baselines — stacked fractions, a radical with a
    vinculum, raised exponents — and drawn with PIL at 3x and downsampled,
    which is the same trick figure_builder uses.

Both come from ONE parse, so the PDF and the Word file can never disagree
about what a formula says — a risk that would be real if the PDF drew from
the LaTeX and Word re-parsed the plain-text form.

The LaTeX subset is deliberately small: what school mathematics through
grade 11 actually uses. Anything unrecognised degrades to upright text
rather than raising, because a konspekt must never fail to export over a
formula.
"""
import io
import re

from PIL import Image, ImageDraw, ImageFont

# ── fonts ───────────────────────────────────────────────────────────────
# Resolved per role from a candidate list, first existing file wins.
#
# These were four hardcoded C:\Windows\Fonts paths, which meant every
# formula in every PDF was silently broken the moment the app ran
# anywhere but a Windows dev machine. The failure was NOT a clean "no
# formula": _font() fell through Cambria -> times.ttf (also a Windows
# path) -> ImageFont.load_default(), and PIL's default is a fixed-size
# bitmap face that IGNORES the requested size. So _layout() measured
# every glyph at ~11px whatever size it asked for, and the page came out
# with formulas drawn on top of themselves, inline math missing entirely
# (box.w <= 0 makes render_png return None), and the odd raw "$x^{2}$"
# left as literal text. Confirmed on a real Dockerised deploy against a
# grade-8 quadratic-equations konspekt.
#
# Linux candidates are the two font packages the backend Dockerfile
# already installs (fonts-dejavu-core, fonts-liberation), so this needs
# no new image dependency:
#   * DejaVu Serif carries the widest math-symbol coverage of the two
#     (√ ± ∑ ∈ ≤ …) plus full Cyrillic, so it leads for upright text.
#   * DejaVu Serif's ITALIC lives in fonts-dejavu-extra, which is NOT
#     installed — so italic (variables, the default in maths) falls to
#     Liberation Serif Italic, which is metric-compatible with Times and
#     does ship in fonts-liberation.
import os as _os
import platform as _platform_mod


def _first_existing(*candidates: str) -> str:
    """The first path that exists, or the last candidate as a last resort
    so callers still get a string (and _font's own except-chain handles
    the miss) rather than None."""
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

SS = 3                      # supersampling, as in figure_builder
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
                # Last resort, and a genuinely broken state: PIL's default
                # is a fixed-size bitmap face that ignores `size`, so every
                # measurement _layout() makes from here is wrong and the
                # formulas come out overlapping or blank. Silent before —
                # which is exactly how a whole Dockerised deploy shipped
                # with unreadable mathematics. Warn once (not per glyph,
                # which would be thousands of lines per export).
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
    """Problems that would make formulas unreadable, for the startup check
    in main.py — same "say it at boot, not when a teacher notices"
    reasoning as export_builder's verify_pdf_fonts. Empty list = fine."""
    problems: list[str] = []
    for role, path in (("upright", _SERIF), ("italic", _SERIF_I), ("bold", _SERIF_B)):
        if not path or not _os.path.exists(path):
            problems.append(f"math {role} font not found at {path!r}")
            continue
        try:
            ImageFont.truetype(path, 16)
        except Exception as e:  # noqa: BLE001
            problems.append(f"math {role} font at {path!r} failed to load: {e}")
    return problems


# ── symbol table ────────────────────────────────────────────────────────
# LaTeX command -> the character to set. Greek letters are set upright the
# way Russian and Tajik school textbooks set them, not italic.
SYMBOLS = {
    "pm": "±", "mp": "∓", "times": "×", "cdot": "·", "div": "÷",
    "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠",
    "approx": "≈", "equiv": "≡", "infty": "∞", "propto": "∝",
    "rightarrow": "→", "to": "→", "Rightarrow": "⇒", "leftrightarrow": "↔",
    "longrightarrow": "⟶", "longleftarrow": "⟵", "leftarrow": "←",
    "Longrightarrow": "⟹", "Leftrightarrow": "⇔", "implies": "⇒", "iff": "⇔",
    # Chemistry sets reversible reactions with harpoons, and marks a gas
    # or a precipitate with an arrow beside the formula — a biology or
    # chemistry lesson is unreadable without these.
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
# Reaction arrows that carry their conditions. The label rides above the
# arrow ("\\xrightarrow{свет}"), and the arrow is drawn long enough to
# hold it — which is the whole reason chemistry uses these instead of a
# plain "→".
_X_ARROWS = {
    "xrightarrow": "→", "xleftarrow": "←",
    "xrightleftharpoons": "⇌", "xleftrightarrow": "↔",
}
_ARROW_CHARS = set("→←↔⇌⇄⟶⟵⇒⇔")

_seen_unknown_macros: set[str] = set()


def _log_unknown_macro(cmd: str) -> None:
    """Records a macro this module cannot set, once per name.

    Silence here is how "xrightarrow" reached a printed slide: the parser
    degraded quietly and nobody learned the notation was unsupported."""
    if cmd in _seen_unknown_macros:
        return
    _seen_unknown_macros.add(cmd)
    try:
        from app.logger import get_logger
        get_logger(__name__).info(f"math: unsupported LaTeX macro \\{cmd} — dropped")
    except Exception:
        pass


def _sole_arrow(node):
    """The arrow character `node` consists of, if that is all it is."""
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
    """mhchem chemistry notation -> the LaTeX this parser understands.

    "6CO2 + 6H2O -> C6H12O6 + 6O2" has to come out as it does in a
    textbook: element counts as subscripts, a real reaction arrow, and
    the stoichiometric coefficients left full size in front."""
    out = str(src or "")
    for src_arrow, latex in _CE_ARROWS:
        out = out.replace(src_arrow, f" {latex} ")
    # A digit directly after an element symbol is that element's count and
    # is set low; a digit at the START of a term is a coefficient and
    # stays full size, which is why the letter before it is required.
    out = re.sub(r"(?<=[A-Za-z])(\d+)", r"_{\1}", out)
    out = re.sub(r"\^(\d*[+-])", r"^{\1}", out)
    return out


# Set upright, not italic — these are function names, not variables.
FUNCTIONS = {"sin", "cos", "tan", "tg", "ctg", "cot", "log", "ln", "lg",
             "exp", "lim", "max", "min", "arcsin", "arccos", "arctan"}
BIG_OPS = {"sum": "∑", "prod": "∏", "int": "∫", "iint": "∬", "oint": "∮"}


# ── tokenizer ───────────────────────────────────────────────────────────
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
    # "**" is Python's power operator, not two multiplications — normalized
    # to "^" here so it flows straight into parse_scripts' existing
    # exponent handling below instead of needing its own AST node.
    return ["^" if t == "**" else t for t in _TOKEN.findall(src) if not t.isspace()]


# ── parser ──────────────────────────────────────────────────────────────
# AST nodes are plain tuples so both back ends can walk them without
# needing to import a class:
#   ("row", [children])          a horizontal run
#   ("txt", s, style)            style in {"it","up","op"}
#   ("frac", num, den)
#   ("sup", base, exp) / ("sub", base, idx) / ("subsup", base, idx, exp)
#   ("sqrt", radicand, index_or_None)
#   ("bigop", char, lower, upper, body)
#   ("fenced", open, close, body)
#   ("xarrow", char, above, below)   a reaction arrow carrying conditions

_CYRILLIC = re.compile(r"[\u0400-\u04ff]")


def _unwrap(node):
    """Drops brackets that a fraction rule has made redundant.

    "(a+b)/(2c)" is written with brackets only because it is on one line;
    once the parts sit above and below a rule, the brackets say nothing
    and a textbook omits them."""
    if node is not None and node[0] == "fenced" and node[1] == "(" and node[2] == ")":
        return node[3]
    return node


def _is_unit(node) -> bool:
    """True for a Cyrillic word — a unit of measurement, not a variable.

    "20/4" must become a stacked fraction, but "км/ч" and "м/с" are units
    and belong on one line the way a textbook prints them. The two are
    told apart by alphabet: in this material the variables are Latin
    (x, a, b, S, V) and the units are Cyrillic (м, с, км, ч), so a
    Cyrillic operand means the slash is "per", not "divided by"."""
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
            # A slash between two operands is a FRACTION, not a printed
            # "/". Teachers asked for this explicitly: a solution reading
            # "x = 20/4 = 5" has to print with 20 over 4 and a rule
            # between them, like a school textbook. Done here rather than
            # by rewriting the model's LaTeX, so it holds for "\frac{}{}"
            # and for a bare slash alike, and in Word as well as the PDF.
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
                # A sign standing in front of the numerator belongs INSIDE
                # it: "-10/5" is written with the minus above the rule,
                # not beside the whole fraction. Only a UNARY sign moves —
                # in "a - 10/5" the minus is a subtraction and stays put.
                if (out and out[-1][0] == "txt" and out[-1][1] in "−+"
                        and (len(out) == 1
                             or (out[-2][0] == "txt" and out[-2][1] in _BINARY))):
                    num = ("row", [out.pop(), num])
                atom = ("frac", num, _unwrap(den))
            if atom is not None:
                out.append(atom)
        return ("row", out)

    def parse_group(self):
        """A {...} group, or a single atom if there are no braces."""
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
        """The single "°" that "^{\\circ}" parses to, or None.

        LaTeX writes an angle as "30^\\circ" because in TeX the degree
        sign is a raised ring. The character U+00B0 IS already raised and
        already small, so setting it as an exponent on top of that prints
        a speck floating above the number. It belongs beside the digits
        at its own size, which is how a textbook sets it."""
        if node is None:
            return None
        if node[0] == "txt" and node[1] == "°":
            return node
        if node[0] == "row" and len(node[1]) == 1:
            return _Parser._degree_only(node[1][0])
        return None

    @staticmethod
    def _collapse_charge(group):
        """"2+" set as ONE atom rather than a number and an operator.

        The row layout puts air around a "+" because it is nearly always
        binary — correct in "a + b", wrong inside an ion's charge, where
        it printed "Ca² ⁺"."""
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
        """The text of the next {...} group, unparsed.

        \\ce's body is chemistry notation, not LaTeX — it has to be
        rewritten before it can be tokenised as maths."""
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
                # \left( ... \right) — the delimiter follows as its own token
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
            # "A \\xrightarrow{свет} B" — the arrow of a chemical
            # reaction, carrying its conditions above it (and a catalyst
            # or temperature below, in the optional [..]). Written by the
            # model for every equation in chemistry and biology; before
            # this it fell through to the unknown-command branch and
            # printed the literal word "xrightarrow" in the middle of the
            # equation, with no arrow at all.
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
                # \overset{label}{\to} and friends: the label goes over
                # (or under) whatever follows. An arrow underneath is the
                # same reaction arrow by another spelling, so it becomes
                # one rather than a second, differently-drawn thing.
                label = self.parse_group()
                base = self.parse_group()
                arrow = _sole_arrow(base)
                if arrow:
                    return (("xarrow", arrow, label, None) if cmd != "underset"
                            else ("xarrow", arrow, None, label))
                return (("stack", base, label, None) if cmd != "underset"
                        else ("stack", base, None, label))
            if cmd == "ce":
                # mhchem: "\ce{6CO2 + 6H2O -> C6H12O6}". Chemistry
                # notation the model reaches for on its own; rewritten
                # into the LaTeX this parser already knows.
                return _Parser(_tokenize(_ce_to_latex(self.parse_group_src()))).parse_row()
            if cmd in SYMBOLS:
                return ("txt", SYMBOLS[cmd], "op")
            if cmd in FUNCTIONS:
                return ("txt", cmd, "up")
            if cmd in ("mathrm", "text", "mathbf", "operatorname"):
                inner = self.parse_group()
                # "\text{x}" around a single Latin letter is the model
                # wrapping a VARIABLE, not writing a word — seen live in
                # generated konspekts ("$\text{x} + 11 = 20$"). Setting
                # that upright prints the unknown the way a unit is
                # printed; a variable is italic in every textbook.
                if (inner and inner[0] == "row" and len(inner[1]) == 1
                        and inner[1][0][0] == "txt"
                        and re.fullmatch(r"[A-Za-z]", inner[1][0][1] or "")):
                    return ("txt", inner[1][0][1], "it")
                return ("style", "up", inner)
            if cmd in ("," , ";", ":", " ", "!", "quad", "qquad"):
                return ("txt", " ", "up")
            # Unknown command. A macro name is FORMATTING, not content:
            # printing "xrightarrow" or "textbf" as a word in the middle
            # of an equation is worse than printing nothing, so a
            # multi-letter macro is dropped and only a one-letter one
            # (which is nearly always a variable, e.g. "\\R") survives as
            # itself. A konspekt still exports either way.
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
            # A run of letters is a variable product (xy) in maths, but a
            # word in Cyrillic-labelled formulas; letters are set italic
            # one by one so "ab" reads as a·b, which is what it means.
            return ("row", [("txt", ch, "it") for ch in tok])
        return ("txt", tok, "up")


# What a chemical equation looks like from the outside: a reaction arrow,
# or element symbols carrying counts ("H_2O", "C_6H_12O_6"). Two of those
# counts are required so that a physics formula with one indexed variable
# ("v_0 t") is not mistaken for chemistry.
_CHEM_COUNT = re.compile(r"[A-Z][a-z]?_\s*\{?\s*\d")
_CHEM_ARROW = re.compile(r"\\(?:ce|x?rightarrow|x?rightleftharpoons|longrightarrow)\b|[→⇌⇄⟶]")


# "H+", "OH-", "Ca2+", "SO4 2-": the charge is written level with the
# symbol by the model, and belongs raised. Only a sign hugging the symbol
# counts — the " + " between two reagents is an operator and must keep
# its spaces.
_CHARGE = re.compile(r"(?<=[A-Za-z\}])(\d{0,2})([+-])(?![\w\d])")
# "SO4 2-" — the model sometimes spaces the charge off. A DIGIT is
# required in that case: without it the rule would swallow the " + "
# between two reagents, which is an operator, not a charge.
_CHARGE_SPACED = re.compile(r"(?<=[A-Za-z\d\}])\s+(\d{1,2})([+-])(?![\w\d])")


def _charge_scripts(latex: str) -> str:
    out = _CHARGE_SPACED.sub(lambda m: "^{%s%s}" % (m.group(1), m.group(2)), latex)
    return _CHARGE.sub(lambda m: "^{%s%s}" % (m.group(1), m.group(2)), out)


def _looks_chemical(latex: str) -> bool:
    src = str(latex or "")
    return bool(_CHEM_ARROW.search(src)) or len(_CHEM_COUNT.findall(src)) >= 2


def _upright(node):
    """The same tree with its Latin letters set upright.

    In chemistry a letter is an ELEMENT, not a quantity: textbooks print
    H₂O upright and reserve italic for variables. Setting a reaction
    equation in the italic used for algebra is the single clearest sign
    that a document was typeset by something that did not know which of
    the two it was looking at."""
    kind = node[0]
    if kind == "txt":
        return ("txt", node[1], "up" if node[2] == "it" else node[2])
    if kind == "row":
        return ("row", [_upright(c) for c in node[1]])
    return tuple([kind] + [_upright(c) if isinstance(c, tuple) else
                           ([_upright(x) for x in c] if isinstance(c, list) else c)
                           for c in node[1:]])


def parse(latex: str):
    """The AST for one formula.

    "$" is stripped first: a dollar is a DELIMITER, never content, and a
    formula field that has been through normalize_math can carry a pair
    of them inside it ("Acid + Base → Salt + $H_2O$"). The parser used to
    have no rule for the character and printed it, so the dollars showed
    up on the page in the middle of the equation."""
    src = str(latex or "").replace("$", " ")
    if _looks_chemical(src):
        # Counts the model left flat ("SO4" beside a braced "H_{2}O") are
        # lowered here too, so one equation is not half-typeset.
        return _upright(_Parser(_tokenize(
            chemical_to_latex(_charge_scripts(src), wrap=False))).parse_row())
    return _Parser(_tokenize(src)).parse_row()


# A "formula" that is nothing but operator characters is not mathematics —
# it is a programming language's operator being named. Confirmed live on a
# Python lesson slide: "Қувва баробар ба $**$" typeset as "··", because
# the parser reads "*" as the multiplication dot, so the ONE thing the
# line existed to show disappeared. Anything in this shape is printed
# exactly as written instead.
_OPERATOR_ONLY = re.compile(r"^[\s*+\-/%=<>!&|^~.,;:]+$")


def is_literal_operator(latex: str) -> bool:
    """True for a span that must be printed verbatim, not typeset."""
    return bool(_OPERATOR_ONLY.fullmatch(str(latex or "").strip()))


# ══ layout / drawing ════════════════════════════════════════════════════
# Every node becomes a Box that knows its width and how far it reaches
# above and below the BASELINE. Composing on baselines rather than on
# bounding boxes is the whole difference between typeset mathematics and
# characters set next to each other.
#
# A Box does not know what it will be drawn ON. It emits two primitives —
# "set this string in this font at this point" and "draw this rule" — to a
# PAINTER, and there are two of those:
#
#   * PilPainter, which rasterises (still used for the .docx fallback and
#     for the odd caller that genuinely needs a bitmap);
#   * export_builder's canvas painter, which issues the same two
#     primitives as PDF drawing operators.
#
# That second one is why a fraction in an exported konspekt is now real
# vector art: the glyphs are the embedded font's outlines and the
# fraction rule is a PDF line, so both stay sharp at any zoom. Before
# this split there was only the rasteriser, and its output was downsampled
# to 72 dpi on the way out — which is exactly what "the formulas look
# blurry" was.

_scratch = ImageDraw.Draw(Image.new("RGB", (8, 8)))


class PilPainter:
    """Draws the layout into a PIL image, in supersampled units."""

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


# Binary operators get air around them; that spacing is most of what makes
# an expression readable rather than a string of glyphs.
_BINARY = set("+−=<>±∓×·÷≤≥≠≈≡→⇒↔∈∉⊂∪∩∝")


def _layout(node, size):
    kind = node[0]

    if kind == "txt":
        return _text_box(node[1], size, node[2])

    if kind == "style":
        return _layout(node[2], size)

    if kind == "row":
        # An operator is BINARY only when an operand precedes it. At the
        # start of a row, or after another operator, it is a SIGN on the
        # next term and must hug it: "-b" and "= -2", not "- b" / "= - 2".
        # Tracking only "was the last item an operator" is not enough —
        # after a binary operator the operand does want its space, after a
        # unary one it does not, so the three states are distinguished.
        kids = []
        prev = "none"           # none | unary | binary | operand | punct
        for child in node[1]:
            # A reaction arrow separates two sides of an equation, so it
            # needs the air a binary operator gets — without it the arrow
            # welds itself to the formulas on either end.
            is_op = ((child[0] == "txt" and child[1] in _BINARY)
                     or child[0] == "xarrow")
            # An arrow is never a sign on the term after it: "→ CaSO4"
            # always wants its air, even though what precedes it ("2−")
            # ends in an operator.
            is_arrow = child[0] == "xarrow" or (child[0] == "txt" and child[1] in _ARROW_CHARS)
            unary = is_op and not is_arrow and prev in ("none", "unary", "binary")
            if prev == "punct":
                # "свет, хлорофилл" — the tokenizer drops the space after
                # a comma, so it is put back here; without it a labelled
                # arrow reads "свет,хлорофилл".
                gap = 0.22 * size * SS
            elif prev in ("none", "unary"):
                gap = 0.0
            elif prev == "binary":
                gap = 0.24 * size * SS
            else:                                   # after an operand
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
        axis = -0.30 * size * SS          # where the fraction rule sits
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
        axis = -0.28 * size * SS            # the line the arrow rides on
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

        # An arrow long enough for its own label: drawn rather than set
        # from a glyph, because no font has a "→" that stretches, and a
        # label wider than the arrow it labels is the thing that makes
        # these equations look homemade.
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
                # In a reversible reaction each shaft carries one head, at
                # opposite ends — that pairing IS the notation.
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
            # Drawn, not a scaled glyph: a font radical stretched to the
            # height of a tall radicand distorts, and its own vinculum
            # never lines up with the overbar over the radicand.
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
        # Grown with the content: a fixed-size bracket around a fraction is
        # the clearest sign of mathematics that was set as ordinary text.
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
    """Draws one formula and returns a tightly cropped PNG, or None if the
    formula is empty or anything at all went wrong — an export must never
    fail because of a formula.

    `oversample` is how many device pixels the caller intends to pack into
    each point of page space. The old code laid out at SS=3 and then
    resized the result back down to 1 pixel per point — i.e. handed the
    PDF a 72 dpi picture of a formula, which is precisely why they went
    soft the moment anyone zoomed in. Nothing is downsampled now; pass
    oversample=4 and the image carries 4 pixels per point (~288 dpi), or
    use the vector path in export_builder and skip rasterising entirely."""
    try:
        box = _layout(parse(latex), size * oversample)
        if box.w <= 0:
            return None
        w = int(box.w + 2 * pad * SS * oversample) + 2
        h = int(box.asc + box.desc + 2 * pad * SS * oversample) + 2
        # The background is a parameter because ReportLab drops an inline
        # image placed inside a <font backColor=...> run — it paints the
        # highlight and loses the picture. Rendering the formula ONTO the
        # highlight colour is what lets a marked answer contain real
        # mathematics instead of an empty tinted box.
        # bg=None gives a transparent plate, which is what an inline
        # formula wants: dropped into a tinted card, an opaque white
        # rectangle around the fraction is plainly visible as a patch.
        if bg is None:
            img = Image.new("RGBA", (max(w, 4), max(h, 4)), (255, 255, 255, 0))
        else:
            img = Image.new("RGB", (max(w, 4), max(h, 4)), bg)
        box.paint(PilPainter(ImageDraw.Draw(img)), pad * SS * oversample,
                  pad * SS * oversample + box.asc)
        # Down to the requested pixels-per-point, never below it: the SS
        # factor is supersampling for smooth edges, `oversample` is real
        # resolution the page keeps.
        out = img.resize((max(1, round(w / SS)), max(1, round(h / SS))), Image.LANCZOS)
        buf = io.BytesIO()
        out.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def measure(latex: str, size: float = 15):
    """(width_pt, ascent_pt, descent_pt) for a formula at `size`, so a
    caller can align an inline image on the surrounding text's baseline."""
    try:
        box = _layout(parse(latex), size)
        return box.w / SS, box.asc / SS, box.desc / SS
    except Exception:
        return 0.0, 0.0, 0.0


# ══ OMML (Microsoft Equation) ═══════════════════════════════════════════
# Word's own equation format. A formula emitted here is a real equation
# object in the .docx: clickable, editable in Word's equation editor, and
# typeset by Word itself. Embedding a picture instead would look similar
# on screen and be useless to a teacher who wants to change a number.

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _run(text, upright):
    """One math run. OMML sets Latin letters italic by default, which is
    the correct convention for variables — so upright is requested only
    for numbers, operators and function names."""
    if text == "":
        return ""
    props = '<m:rPr><m:sty m:val="p"/></m:rPr>' if upright else ""
    return f'<m:r>{props}<m:t xml:space="preserve">{_esc(text)}</m:t></m:r>'


def _omml(node) -> str:
    kind = node[0]

    if kind == "txt":
        # The tokenizer drops whitespace, so a comma inside a label
        # ("свет, хлорофилл") would come out of Word closed up as
        # "свет,хлорофилл". A plain space cannot fix it — Word and
        # PowerPoint ignore spaces inside an equation — so the gap is a
        # THIN SPACE, which they keep.
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
        # Word has no stretchy arrow either, but it does have limits: the
        # label sits over (and under) the character as a real equation
        # object, so it stays editable and keeps its position when the
        # teacher retypes the formula.
        # Word cannot stretch an arrow under its label, so a labelled
        # arrow is set with the LONG glyph: "⟶" carries a word above it
        # without the label overhanging both its ends.
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
    """Emits a run of siblings, giving a big operator the rest of the row
    as its operand.

    In the AST a sum's operand simply follows it, because that is how it
    is drawn. OMML instead nests the operand inside the n-ary object, and
    a nary with an empty <m:e> shows up in Word as an empty dotted box —
    so the tail is folded in here rather than emitted alongside."""
    out = []
    for i, child in enumerate(children):
        if child[0] == "bigop" and child[4] is None:
            tail = ("row", list(children[i + 1:]))
            out.append(_omml(("bigop", child[1], child[2], child[3], tail)))
            break
        out.append(_omml(child))
    return "".join(out)


def to_omml(latex: str, display: bool = False) -> str:
    """The <m:oMath> XML for a formula, with the math namespace declared
    so it can be parsed and inserted on its own."""
    body = _omml(parse(latex))
    if display:
        return (f'<m:oMathPara xmlns:m="{M_NS}">'
                f'<m:oMathParaPr><m:jc m:val="center"/></m:oMathParaPr>'
                f'<m:oMath>{body}</m:oMath></m:oMathPara>')
    return f'<m:oMath xmlns:m="{M_NS}">{body}</m:oMath>'


def omml_element(latex: str, display: bool = False):
    """Parsed element ready to append to a python-docx paragraph, or None
    if the formula could not be built — a bad formula must degrade to
    plain text, never break the document."""
    try:
        from docx.oxml import parse_xml
        return parse_xml(to_omml(latex, display))
    except Exception:
        return None


# ══ normalisation of powers written outside the math pipeline ═══════════
# Everything above typesets only what arrives as LaTeX inside $...$. Two
# routes bypassed that and printed a power flat on the line, "x2" / "x^2":
#
#   * the model writes a power in prose without the dollars ("площадь S =
#     a^2", "10^-3 м") — it is told to wrap every expression, and mostly
#     does, but a konspekt is hundreds of strings and it slips;
#   * it writes the character itself ("x²", "A₁") — correct-looking in the
#     JSON, but the PDF's embedded font has no glyph for U+00B2 or U+2081,
#     so it printed as an empty box, and Word set it as ordinary text at
#     full size sitting on the baseline.
#
# Both are rewritten here into the ONE form the rest of the module already
# typesets properly: a $...$ span with a braced exponent. Nothing else in
# the export has to learn about powers.

SUP_CHARS = {
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6",
    "⁷": "7", "⁸": "8", "⁹": "9", "ⁿ": "n", "ⁱ": "i", "⁺": "+", "⁻": "-",
    "⁽": "(", "⁾": ")",
}
SUB_CHARS = {chr(0x2080 + d): str(d) for d in range(10)}
SUB_CHARS.update({"₊": "+", "₋": "-", "₌": "=", "₍": "(", "₎": ")",
                  "ₙ": "n", "ₖ": "k", "ᵢ": "i", "ₐ": "a", "ₓ": "x"})

# What a power may be attached to: a variable, a number, or a closing
# bracket — "x², 10³, (a+b)²".
_BASE = r"[A-Za-z0-9А-Яа-яЁёҲҳҚқӮӯҶҷҒғӢӣ)\]]"
_SUP_RUN = re.compile(f"({_BASE}+)([{''.join(SUP_CHARS)}]+)")
_SUB_RUN = re.compile(f"({_BASE}+)([{''.join(SUB_CHARS)}]+)")
# "x^2", "x^{2}", "10^-3", "e^{n+1}" written in prose without dollars.
_BARE_POW = re.compile(r"(" + _BASE + r"+)\^(?:\{([^{}$]{1,20})\}|(-?\w+))")
# "\text{-100}", "\frac{1}{2}" etc. written in prose with no $...$ around
# them at all — a LaTeX command outside dollars is not LaTeX to any of the
# exports, it is literal backslash-and-braces text on the page. Confirmed
# live: a teacher saw "\text{-100}" printed exactly like that mid-sentence.
# The prompt now tells the model not to do this (see ai_service.py's
# MATHEMATICAL NOTATION rule); this is the backend-side backstop for
# whenever it slips anyway — same belt-and-suspenders relationship
# _BARE_POW already has with that same prompt rule for bare powers.
_BARE_LATEX_CMD = re.compile(r"\\[A-Za-z]+\{[^{}$]{1,60}\}")
# "\begin{cases} x+y=5 \\ x-y=1 \end{cases}" — a system of equations, the
# one LaTeX environment the model reaches for on its own (systems come up
# constantly from Алгебра-7 onward). The tokenizer below has no notion of
# \begin/\end at all: \begin is an unknown macro (silently dropped, see
# its handling in _Parser), so the "{cases}" that follows lands as its own
# group and prints as the literal word "cases", and the "\\" line breaks
# print as literal backslashes — confirmed live: "$\begin{cases} x+y=5
# \\ x-y=1 \end{cases}$" rendered as "casesx + y = 5\x − y = 1cases" in a
# PDF's glossary example line. Flattened here, before any tokenizing, into
# the equations joined by "; " — no braces, no environment, just the
# content a reader needs.
_CASES_ENV = re.compile(r"\\begin\{cases\}(.*?)\\end\{cases\}", re.DOTALL)


def _flatten_cases_env(text: str) -> str:
    def repl(m: re.Match) -> str:
        parts = [p.strip() for p in re.split(r"\\\\", m.group(1)) if p.strip()]
        return "; ".join(parts)
    return _CASES_ENV.sub(repl, text)
# An exponent already inside LaTeX but written bare: "x^2" -> "x^{2}". The
# parser reads both, but Word's equation editor shows the braced form the
# way a textbook sets it, and a two-digit exponent ("2^10") is otherwise
# read as 2¹ followed by a 0.
_LATEX_POW = re.compile(r"([\^_])(?!\{)(\\?[A-Za-z0-9]+|-\d+)")


def _sup_to_latex(run: str) -> str:
    return "".join(SUP_CHARS.get(c, c) for c in run)


def _sub_to_latex(run: str) -> str:
    return "".join(SUB_CHARS.get(c, c) for c in run)


def brace_scripts(latex: str) -> str:
    """"x^2" -> "x^{2}" inside a formula that is already LaTeX."""
    return _LATEX_POW.sub(lambda m: f"{m.group(1)}{{{m.group(2)}}}", str(latex or ""))


def plain_to_latex(text: str) -> str:
    """Reads a formula written in the plain notation the "formula" field
    uses (a^2, √x, x₁) as LaTeX, so a formulas entry whose "latex" the
    model omitted is still typeset instead of printed as keyboard text."""
    s = str(text or "").strip()
    if not s:
        return ""
    s = _SUP_RUN.sub(lambda m: f"{m.group(1)}^{{{_sup_to_latex(m.group(2))}}}", s)
    s = _SUB_RUN.sub(lambda m: f"{m.group(1)}_{{{_sub_to_latex(m.group(2))}}}", s)
    # √ is a character here, not a command; give it the operand that
    # follows so it is drawn with a vinculum over the radicand.
    s = re.sub(r"√\s*\(([^()]{1,40})\)", r"\\sqrt{\1}", s)
    s = re.sub(r"√\s*([A-Za-z0-9^{}]+)", r"\\sqrt{\1}", s)
    return brace_scripts(s)


# Every chemical element symbol, so a formula in running text can be told
# from an ordinary word. "CO2" is carbon and oxygen and becomes CO₂;
# "COVID19" contains D, which is not an element, and is left alone.
_ELEMENTS = set("""
H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni
Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I
Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt
Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr
Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og
""".split())

# The lookbehind bars a LETTER, not a digit: "6CO2" is six molecules of
# CO₂, and blocking on the coefficient left exactly the formulas a
# chemistry lesson is made of unset.
_CHEM_WORD = re.compile(r"(?<![A-Za-z$\_])((?:[A-Z][a-z]?\d{0,3}){1,10}(?:\d{0,2}[+-])?)(?![\w])")
_CHEM_PART = re.compile(r"([A-Z][a-z]?)(\d{0,3})")
# The one-element molecules school chemistry and biology actually use.
_SIMPLE_MOLECULES = {"O2", "O3", "H2", "N2", "F2", "Cl2", "Br2", "I2",
                     "S8", "P4", "C60"}


_CHEM_CHARGE_TAIL = re.compile(r"(\d{0,2})([+-])$")


def _chemical_spans(token: str) -> str | None:
    """`token` as LaTeX with its counts subscripted, or None if it is not
    a chemical formula at all.

    Requires a real count somewhere: "CO" on its own is far more often
    the start of a Russian word or an abbreviation than carbon monoxide,
    and rewriting it would do more harm than the subscript does good."""
    charge = ""
    tail = _CHEM_CHARGE_TAIL.search(token)
    if tail:
        charge = tail.group(1) + tail.group(2)
        token = token[:tail.start()]
    parts = _CHEM_PART.findall(token)
    if not parts or "".join(a + b for a, b in parts) != token:
        return None
    # An ion is a formula even without a count: "H+" and "OH-" are exactly
    # what a neutralisation lesson is about, and neither carries a digit.
    if not charge and not any(count for _, count in parts):
        return None
    if not all(sym in _ELEMENTS for sym, _ in parts):
        return None
    # A chemical count is never 0 and never written as 1 — "CC0" is a
    # licence name (it printed as CC₀ under a figure), not a molecule.
    if any(count and (count[0] == "0" or count == "1") for _, count in parts):
        return None
    # A single element with a count is shaped exactly like a room number
    # or a label ("кабинет B2", "рис. C3"), so only the handful that a
    # school lesson actually writes are accepted; anything with two or
    # more element symbols is unambiguous enough to take as written.
    if len(parts) == 1 and not charge and token not in _SIMPLE_MOLECULES:
        return None
    body = "".join(f"{sym}_{{{count}}}" if count else sym for sym, count in parts)
    return f"{body}^{{{charge}}}" if charge else body


def chemical_to_latex(part: str, wrap: bool = True) -> str:
    """Rewrites the chemical formulas in one run of text into LaTeX.

    A lesson that says "растения поглощают CO2 и выделяют O2" is printing
    the numbers full size, level with the letters — which is not how any
    chemistry or biology textbook writes them, and is the first thing a
    subject teacher notices.

    `wrap` puts $...$ around each formula, which is what PROSE needs. A
    caller that is already inside a formula passes False: there, a dollar
    is not a delimiter but a character, and it would be printed."""
    def repl(m):
        latex = _chemical_spans(m.group(1))
        if not latex:
            return m.group(1)
        return f"${latex}$" if wrap else latex
    return _CHEM_WORD.sub(repl, part)


def normalize_math(text: str) -> str:
    """Rewrites powers and indices the model left outside the mathematics
    into $...$ spans, and braces the exponents inside spans it did write.

    Text already inside $...$ is passed through untouched apart from the
    bracing — it is LaTeX and the parser owns it."""
    raw = str(text or "")
    if not raw:
        return raw
    if "\\begin{cases}" in raw:
        raw = _flatten_cases_env(raw)
    if raw.count("$") % 2:
        # An unbalanced dollar makes the odd/even split below meaningless;
        # leaving the string alone is better than rewriting prose as if it
        # were mathematics.
        return raw
    out = []
    for i, part in enumerate(raw.split("$")):
        # Odd pieces are the insides of $...$ — already LaTeX.
        if i % 2:
            out.append(brace_scripts(part))
            continue
        # First, so a "\text{-100}" the caret/superscript rules below
        # would otherwise leave untouched (there's no ^/² in it for them
        # to match on) gets wrapped in dollars before anything else runs.
        part = _BARE_LATEX_CMD.sub(lambda m: f"${m.group(0)}$", part)
        # The caret form goes first. Run the other way round, "mc²" would
        # become "$mc^{2}$" and then match the caret rule again, wrapping
        # a second pair of dollars around a span that already had them.
        part = _BARE_POW.sub(
            lambda m: f"${m.group(1)}^{{{m.group(2) or m.group(3)}}}$", part)
        part = _SUP_RUN.sub(
            lambda m: f"${m.group(1)}^{{{_sup_to_latex(m.group(2))}}}$", part)
        part = _SUB_RUN.sub(
            lambda m: f"${m.group(1)}_{{{_sub_to_latex(m.group(2))}}}$", part)
        # Last, so it cannot re-match the spans the rules above just made.
        part = chemical_to_latex(part)
        out.append(part)
    joined = "$".join(out)
    # Where the rewrite butted two spans directly together ("$x^{2}$$y$")
    # they are one expression: merging them lets the typesetter set the
    # spacing between the parts instead of the join being lost.
    return joined.replace("$$", "")


# ══ script segments — powers for exports with no math engine ════════════
# The OMML above and the drawing before it both assume a caller that can
# place an equation object or an image. Most of the konspekt templates are
# ordinary flowing text — a Word run, a ReportLab paragraph — and those
# printed the formula as it was typed, "x^2".
#
# The great majority of school formulas are only a power or an index on
# otherwise plain text ("a^2 + b^2 = c^2", "x_1"), and BOTH of those
# targets can already set a real superscript in flowing text: Word with
# w:vertAlign, ReportLab with <super>. So a formula is split here into
# segments carrying that one piece of information, and each export renders
# them in its own way, with the surrounding font kept.
#
# Anything a run of text genuinely cannot express — a stacked fraction, a
# radical, a sum — returns None instead, and the caller falls back to the
# real typesetter (an equation object, or a drawn image).

_SCRIPTABLE = {"txt", "row", "sup", "sub", "subsup", "fenced", "style"}


def _flat_text(node) -> str | None:
    """The node as running text, or None if it needs real typesetting."""
    kind = node[0]
    if kind == "txt":
        return node[1]
    if kind == "style":
        return _flat_text(node[2])
    if kind == "row":
        # Binary operators get air around them, the way _layout spaces
        # them for the drawn form. An operator with no operand before it
        # is a SIGN and hugs what follows: "−3", not "− 3".
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
    """[(text, kind)] with kind in {"", "sup", "sub"} for a formula that
    flowing text can carry, or None if it needs the full typesetter.

    "a^2 + b^2" gives [("a",""),("2","sup"),(" + ",""),("b",""),("2","sup")]
    — which a Word run or a ReportLab paragraph can set as a true raised
    exponent in the surrounding font, rather than printing "a^2"."""
    try:
        root = parse(latex)
    except Exception:
        return None
    segs: list[tuple[str, str]] = []

    def walk(node, prev_op=True) -> bool:
        kind = node[0]
        if kind == "row":
            # Same operator spacing _flat_text applies inside a group; it
            # has to happen here too, because a row whose children carry
            # scripts is split into segments rather than flattened whole.
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
