# -*- coding: utf-8 -*-
"""Flat-silhouette figures that explain a slide, built from vector shapes.

Why silhouettes
---------------
The brief asks for small illustrated characters that help explain the
material. This project has no image-generation capability and no
character asset library, and the two obvious substitutes both fail the
brief on their own terms: stock clipart is the "дешёвый школьный
ClipArt" it explicitly rules out, and a stick figure drawn from lines
looks worse than no character at all.

What IS achievable from PowerPoint primitives is the flat editorial
silhouette style — one solid figure in the subject's own colour, a prop
in a second tone, no faces. It is a deliberate illustration style rather
than a failed attempt at a cartoon; it scales cleanly on a projector;
and having no face sidesteps depicting a specific person entirely, which
matters for a product used across a whole country's classrooms.

How a pose is built
-------------------
Every figure is the same six parts — head, torso, two arms, two legs —
placed from one height. A pose only changes the ARM ANGLES and where the
prop sits, so poses stay consistent with each other and a new one is
three numbers rather than a new drawing.

Arm geometry, since it is the fiddly part: python-pptx rotates a shape
about its own centre, clockwise, in degrees. In screen coordinates
(x right, y down) a shape's downward axis (0, 1) rotated by θ becomes
(−sin θ, cos θ). So an arm hanging from shoulder S at angle θ has its
centre at S + (L/2)·(−sin θ, cos θ), and its hand at S + L·(−sin θ,
cos θ). θ = 0 hangs straight down, negative θ swings the arm to the
figure's right (the viewer's right), positive to the left.
"""

from __future__ import annotations

import math

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

from app import pptx_shapes


def _shape(slide, shape_type, x, y, w, h, fill=None, line=None,
           line_pt=1.0, rotation=None):
    """A figure part. Shadows off — python-pptx adds one to every shape by
    default and a silhouette with a drop shadow reads as clip art."""
    shp = slide.shapes.add_shape(shape_type, Inches(x), Inches(y),
                                 Inches(max(w, 0.008)), Inches(max(h, 0.008)))
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.fill.solid()
        shp.line.fill.fore_color.rgb = line
        shp.line.width = Pt(line_pt)
    if rotation is not None:
        shp.rotation = rotation
    return pptx_shapes.flatten(shp)


def _limb(slide, sx, sy, angle_deg, length, width, fill):
    """One arm or leg hanging from (sx, sy) at `angle_deg`. Returns the
    hand/foot point so a prop can be placed in it."""
    th = math.radians(angle_deg)
    dx, dy = -math.sin(th), math.cos(th)
    cx, cy = sx + dx * length / 2, sy + dy * length / 2
    shp = _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE,
                 cx - width / 2, cy - length / 2, width, length, fill,
                 rotation=angle_deg)
    try:
        shp.adjustments[0] = 0.5          # fully rounded ends
    except Exception:
        pass
    return sx + dx * length, sy + dy * length


# ── props ────────────────────────────────────────────────────────────────
#
# Each draws itself around a hand point. Kept small and readable in
# silhouette: at the sizes these appear (a figure is 1.2–1.9 inches tall)
# anything more detailed turns to mush.


def _prop_pointer(slide, hx, hy, h, accent, support, flip):
    # Short and thick. The first cut was 0.42h long and 0.028h thick,
    # which at figure scale rendered as a stray hairline crossing the
    # slide rather than as a pointer in someone's hand.
    d = -1 if flip else 1
    L, T = 0.26 * h, 0.05 * h
    x = hx if d > 0 else hx - L
    _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, hy - T / 2, L, T, support,
           rotation=-14 * d)
    _shape(slide, MSO_SHAPE.OVAL, (hx + L * d) - 0.035 * h, hy - 0.06 * h,
           0.07 * h, 0.07 * h, support)


def _prop_ruler(slide, hx, hy, h, accent, support, flip):
    d = -1 if flip else 1
    L, T = 0.30 * h, 0.085 * h
    x = hx if d > 0 else hx - L
    _shape(slide, MSO_SHAPE.RECTANGLE, x, hy - T / 2, L, T, support, rotation=-10 * d)
    for n in range(1, 4):
        _shape(slide, MSO_SHAPE.RECTANGLE, x + n * (L / 4), hy - T / 2,
               0.012 * h, T * 0.45, accent, rotation=-10 * d)


def _prop_flask(slide, hx, hy, h, accent, support, flip):
    w = 0.20 * h
    _shape(slide, MSO_SHAPE.TRAPEZOID, hx - w / 2, hy - 0.02 * h, w, 0.18 * h, support)
    _shape(slide, MSO_SHAPE.RECTANGLE, hx - 0.035 * h, hy - 0.13 * h,
           0.07 * h, 0.12 * h, support)
    _shape(slide, MSO_SHAPE.OVAL, hx - 0.04 * h, hy + 0.07 * h, 0.05 * h, 0.05 * h, accent)


def _prop_globe(slide, hx, hy, h, accent, support, flip):
    d = 0.26 * h
    _shape(slide, MSO_SHAPE.OVAL, hx - d / 2, hy - d / 2, d, d, support)
    _shape(slide, MSO_SHAPE.OVAL, hx - d / 6, hy - d / 2, d / 3, d, None,
           line=accent, line_pt=0.9)
    _shape(slide, MSO_SHAPE.RECTANGLE, hx - d / 2, hy - 0.01 * h, d, 0.018 * h, accent)


def _prop_magnifier(slide, hx, hy, h, accent, support, flip):
    d = 0.22 * h
    _shape(slide, MSO_SHAPE.DONUT, hx - d / 2, hy - d / 2, d, d, support)
    _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, hx + d * 0.28, hy + d * 0.28,
           0.035 * h, 0.16 * h, support, rotation=-40 if not flip else 40)


def _prop_scroll(slide, hx, hy, h, accent, support, flip):
    w, ht = 0.22 * h, 0.16 * h
    _shape(slide, MSO_SHAPE.RECTANGLE, hx - w / 2, hy - ht / 2, w, ht, support)
    for x in (hx - w / 2 - 0.022 * h, hx + w / 2 - 0.022 * h):
        _shape(slide, MSO_SHAPE.OVAL, x, hy - ht / 2 - 0.018 * h,
               0.044 * h, ht + 0.036 * h, accent)


def _prop_laptop(slide, hx, hy, h, accent, support, flip):
    w = 0.24 * h
    _shape(slide, MSO_SHAPE.PARALLELOGRAM, hx - w / 2, hy - 0.15 * h, w, 0.13 * h, support)
    _shape(slide, MSO_SHAPE.RECTANGLE, hx - w / 2 - 0.02 * h, hy - 0.022 * h,
           w + 0.04 * h, 0.04 * h, accent)


def _prop_book(slide, hx, hy, h, accent, support, flip):
    w = 0.20 * h
    _shape(slide, MSO_SHAPE.RECTANGLE, hx - w / 2, hy - 0.07 * h, w, 0.16 * h,
           support, rotation=-10)
    _shape(slide, MSO_SHAPE.RECTANGLE, hx - 0.012 * h, hy - 0.07 * h,
           0.024 * h, 0.16 * h, accent, rotation=-10)


def _prop_vector(slide, hx, hy, h, accent, support, flip):
    """Physics gets an arrow rather than a magnet: BLOCK_ARC rendered as an
    unreadable blob at this size, and a vector is both the more legible
    silhouette and the more universal physics object."""
    d = -1 if flip else 1
    L = 0.30 * h
    x = hx if d > 0 else hx - L
    _shape(slide, MSO_SHAPE.RIGHT_ARROW, x, hy - 0.045 * h, L, 0.09 * h,
           support, rotation=(-18 if d > 0 else 198))


def _prop_none(slide, hx, hy, h, accent, support, flip):
    return


_PROPS = {
    "pointer": _prop_pointer,
    "ruler": _prop_ruler,
    "flask": _prop_flask,
    "globe": _prop_globe,
    "magnifier": _prop_magnifier,
    "scroll": _prop_scroll,
    "laptop": _prop_laptop,
    "book": _prop_book,
    "vector": _prop_vector,
    "none": _prop_none,
}


# ── poses ────────────────────────────────────────────────────────────────
#
# (near-arm angle, far-arm angle, which hand holds the prop, head tilt).
# "near" is the arm on the viewer's left, "far" the one on the right.
# Angles follow the convention in the module docstring: 0 hangs straight
# down, negative swings toward the viewer's right.

_POSES = {
    # Explaining something to the RIGHT of the figure — the default when
    # the figure sits in the left margin beside content.
    "point_right": (18, -118, "far", 4),
    # Mirror, for a figure placed to the right of the content.
    "point_left": (118, -18, "near", -4),
    # Both hands open: introducing, or presenting a whole composition.
    "present": (42, -42, "far", 0),
    # Prop held at hip height, figure standing calmly.
    "hold": (14, -34, "far", 0),
    # Leaning in over something — a microscope, a worksheet.
    "observe": (26, -52, "far", 12),
    # Writing on a board/sheet in front and slightly up.
    "write": (12, -88, "far", 6),
    # Hand to chin.
    "think": (16, -140, "near", -8),
}

POSES = tuple(_POSES)


def draw(slide, x_in: float, y_in: float, height_in: float,
         accent: RGBColor, support: RGBColor,
         pose: str = "point_right", prop: str = "none") -> None:
    """Draw one figure whose FEET rest at `y_in` + `height_in`, with the
    body centred on `x_in`.

    Fail-soft: a character is decoration with a job, but it is still
    decoration — it must never be the reason an export fails."""
    try:
        _draw(slide, x_in, y_in, height_in, accent, support, pose, prop)
    except Exception:
        pass


def _draw(slide, x_in, y_in, h, accent, support, pose, prop):
    near_a, far_a, prop_hand, tilt = _POSES.get(pose, _POSES["point_right"])
    cx = x_in

    head_d = 0.23 * h
    torso_w, torso_h = 0.30 * h, 0.34 * h
    torso_top = y_in + 0.215 * h
    shoulder_y = torso_top + 0.06 * h
    arm_len, arm_w = 0.30 * h, 0.085 * h
    leg_len, leg_w = 0.40 * h, 0.115 * h

    # Legs first so the torso overlaps them at the hip.
    leg_top = torso_top + torso_h - 0.02 * h
    _limb(slide, cx - 0.075 * h, leg_top, 6, leg_len, leg_w, accent)
    _limb(slide, cx + 0.075 * h, leg_top, -6, leg_len, leg_w, accent)

    # Arms behind the torso, so the shoulder joint is hidden.
    near_hand = _limb(slide, cx - torso_w / 2 + 0.02 * h, shoulder_y,
                      near_a, arm_len, arm_w, accent)
    far_hand = _limb(slide, cx + torso_w / 2 - 0.02 * h, shoulder_y,
                     far_a, arm_len, arm_w, accent)

    torso = _shape(slide, MSO_SHAPE.ROUND_2_SAME_RECTANGLE,
                   cx - torso_w / 2, torso_top, torso_w, torso_h, accent)
    try:
        torso.adjustments[0] = 0.35
    except Exception:
        pass

    _shape(slide, MSO_SHAPE.OVAL, cx - head_d / 2, y_in, head_d, head_d,
           accent, rotation=tilt)

    fn = _PROPS.get(prop)
    if fn:
        hx, hy = near_hand if prop_hand == "near" else far_hand
        fn(slide, hx, hy, h, accent, support, prop_hand == "near")


# ── which figure a subject uses ──────────────────────────────────────────
#
# The prop is what makes a maths figure read as maths rather than as a
# recoloured biology one, so it is part of the subject template's identity
# rather than a random pick.

SUBJECT_PROP = {
    "mathematics": "ruler",
    "algebra": "pointer",
    "geometry": "ruler",
    "physics": "vector",
    "chemistry": "flask",
    "biology": "magnifier",
    "geography": "globe",
    "history": "scroll",
    "history_world": "scroll",
    "informatics": "laptop",
    "russian": "book",
    "literature": "book",
    "english": "book",
    "tajik": "book",
    "social_studies": "pointer",
    "ecology": "magnifier",
    "primary_school": "pointer",
    "general": "pointer",
}


# A prop named here but missing from _PROPS silently draws nothing — which
# is how physics ended up with an empty hand after "magnet" was replaced by
# "vector". Checked at import so the mistake cannot ship.
assert set(SUBJECT_PROP.values()) <= set(_PROPS), (
    "unknown prop(s): " + ", ".join(sorted(set(SUBJECT_PROP.values()) - set(_PROPS))))


def prop_for(template_id: str) -> str:
    return SUBJECT_PROP.get(str(template_id or ""), "pointer")
