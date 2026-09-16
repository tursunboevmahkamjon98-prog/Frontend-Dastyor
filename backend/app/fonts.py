import os
import platform

_IS_WINDOWS = platform.system() == "Windows"
_WIN = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
_DEJAVU = "/usr/share/fonts/truetype/dejavu"
_LIBERATION = "/usr/share/fonts/truetype/liberation"


def _win(name: str) -> str:
    return os.path.join(_WIN, name) if _IS_WINDOWS else ""


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
    if role not in _resolved:
        _resolved[role] = next(
            (p for p in _CANDIDATES.get(role, ()) if p and os.path.exists(p)), ""
        )
    return _resolved[role]


def verify_fonts() -> list[str]:
    problems: list[str] = []
    for role in _CANDIDATES:
        path = font_path(role)
        if not path:
            problems.append(
                f"no font found for role {role!r} — tried "
                f"{[p for p in _CANDIDATES[role] if p]}"
            )
    return problems
