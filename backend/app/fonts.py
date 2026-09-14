# -*- coding: utf-8 -*-
"""One place that answers "where is a usable TTF for this role".

Every module that draws with PIL — cover_builder, figure_builder,
timeline_builder, math_render — used to carry its own
``_FONT_DIR = r"C:\\Windows\\Fonts"`` and build paths off it. That is
correct on a Windows dev machine and wrong on every server, and the way
it failed made it hard to notice: PIL's ``ImageFont.load_default()``
fallback is a FIXED-SIZE bitmap face that silently ignores the size it is
asked for, so pages came out with text squeezed into illegible specks and
formulas drawn on top of themselves rather than with an error anyone
could act on. Confirmed on a real Dockerised deploy: the konspekt body
(ReportLab, which resolves its own font separately and correctly) was
perfectly readable on the same page as a cover rendered in 2pt mush.

Resolution is per ROLE, not per file: ask for ``sans_bold`` and get
whatever this machine actually has for that, Windows or Linux. Linux
candidates come from the two font packages backend/Dockerfile already
installs (``fonts-dejavu-core``, ``fonts-liberation``) so this adds no
image dependency.

Anything that still cannot be resolved is reported by
:func:`verify_fonts`, which main.py's startup check calls — the point
being that a missing font is announced at boot, not discovered by a
teacher looking at a ruined PDF.
"""
import os
import platform

_IS_WINDOWS = platform.system() == "Windows"
_WIN = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
_DEJAVU = "/usr/share/fonts/truetype/dejavu"
_LIBERATION = "/usr/share/fonts/truetype/liberation"


def _win(name: str) -> str:
    """A Windows font path, or "" off Windows so it never wins a lookup."""
    return os.path.join(_WIN, name) if _IS_WINDOWS else ""


# Per role, best first. Windows entries collapse to "" elsewhere, so the
# Linux candidates take over without a platform branch at each call site.
#
# Segoe UI is the Windows house sans here; DejaVu Sans is the closest
# thing on the Linux side that also carries full Cyrillic (which every
# Tajik/Russian material needs) — Liberation Sans is the metric-compatible
# Arial stand-in and serves as the second string.
_CANDIDATES: dict[str, tuple[str, ...]] = {
    "sans": (
        _win("segoeui.ttf"),
        f"{_DEJAVU}/DejaVuSans.ttf",
        f"{_LIBERATION}/LiberationSans-Regular.ttf",
    ),
    "sans_bold": (
        _win("segoeuib.ttf"),
        f"{_DEJAVU}/DejaVuSans-Bold.ttf",
        f"{_LIBERATION}/LiberationSans-Bold.ttf",
    ),
    "sans_italic": (
        _win("segoeuii.ttf"),
        # DejaVu Sans Oblique is in fonts-dejavu-core; Liberation's italic
        # is the backup in case only that package is present.
        f"{_DEJAVU}/DejaVuSans-Oblique.ttf",
        f"{_LIBERATION}/LiberationSans-Italic.ttf",
        f"{_DEJAVU}/DejaVuSans.ttf",
    ),
    "serif": (
        _win("times.ttf"),
        f"{_DEJAVU}/DejaVuSerif.ttf",
        f"{_LIBERATION}/LiberationSerif-Regular.ttf",
    ),
    "serif_bold": (
        _win("timesbd.ttf"),
        f"{_DEJAVU}/DejaVuSerif-Bold.ttf",
        f"{_LIBERATION}/LiberationSerif-Bold.ttf",
    ),
    "serif_italic": (
        _win("timesi.ttf"),
        # DejaVu Serif's italic lives in fonts-dejavu-EXTRA, which is not
        # installed — Liberation Serif Italic is the one that actually
        # exists in the image, so it leads on Linux.
        f"{_LIBERATION}/LiberationSerif-Italic.ttf",
        f"{_DEJAVU}/DejaVuSerif.ttf",
    ),
    "mono": (
        _win("consola.ttf"),
        f"{_DEJAVU}/DejaVuSansMono.ttf",
        f"{_LIBERATION}/LiberationMono-Regular.ttf",
    ),
}

_resolved: dict[str, str] = {}


def font_path(role: str) -> str:
    """The first existing file for `role`, cached.

    Returns "" when nothing matches, rather than raising: a missing font
    must degrade a picture, never fail an export. Callers still pass the
    result to PIL, whose own error path handles "" — but by then
    verify_fonts() has already said so at startup.
    """
    if role not in _resolved:
        _resolved[role] = next(
            (p for p in _CANDIDATES.get(role, ()) if p and os.path.exists(p)), ""
        )
    return _resolved[role]


def verify_fonts() -> list[str]:
    """Roles with no usable file on this machine — empty list means fine.

    Called from main.py's startup block so a server that cannot draw
    legible pages says so in its first ten lines of log.
    """
    problems: list[str] = []
    for role in _CANDIDATES:
        path = font_path(role)
        if not path:
            problems.append(
                f"no font found for role {role!r} — tried "
                f"{[p for p in _CANDIDATES[role] if p]}"
            )
    return problems
