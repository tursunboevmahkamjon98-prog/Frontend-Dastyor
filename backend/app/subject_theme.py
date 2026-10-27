
import os

_SUBJECT_ACCENTS: dict[str, str] = {
    "Таджикский язык": "#0e7c86",
    "Таджикская литература": "#6b3fa0",
    "Русский язык": "#c62839",
    "Английский язык": "#1d5fc2",
    "Математика": "#4a3aa7",
    "Алгебра": "#7c3aed",
    "Геометрия": "#0f9b6e",
    "Информатика": "#2a78d6",
    "Физика": "#eb6834",
    "Химия": "#0891b2",
    "Биология": "#008300",
    "География": "#a3702d",
    "История Таджикистана": "#8a2635",
    "Всемирная история": "#b5502e",
}

_DEFAULT_ACCENT = "#3B82F6"


def get_subject_accent_hex(subject: str | None) -> str:
    if not subject:
        return _DEFAULT_ACCENT
    return _SUBJECT_ACCENTS.get(subject, _DEFAULT_ACCENT)


def get_subject_accent_rgb(subject: str | None) -> tuple[int, int, int]:
    hex_str = get_subject_accent_hex(subject).lstrip("#")
    return int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)


_SUBJECT_ILLUSTRATIONS: dict[str, str] = {
    "Математика": "matematika.png",
    "Алгебра": "algebra.png",
    "Геометрия": "geometriya.png",
    "Информатика": "informatika.png",
    "Физика": "fizika.png",
    "Химия": "himiya.png",
    "Биология": "biologiya.png",
    "География": "geografiya.png",
    "Русский язык": "til.png",
    "Английский язык": "til.png",
    "Таджикский язык": "til.png",
    "Таджикская литература": "adabiyot.png",
    "История Таджикистана": "tarix_tj.png",
    "Всемирная история": "tarix_dunyo.png",
}

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets", "subjects")


def get_subject_illustration_path(subject: str | None) -> str | None:
    if not subject:
        return None
    fname = _SUBJECT_ILLUSTRATIONS.get(subject)
    if not fname:
        return None
    path = os.path.join(_ASSETS_DIR, fname)
    return path if os.path.exists(path) else None


def resolve_accent_hex(content: dict) -> str:
    """The accent for a rendered material.

    Colour used to be a property of the subject alone. A composed template may
    now carry its own palette, and when it does it wins; templates without one
    (including all seven original ones) keep falling back to the subject, so
    nothing that existed before this function changes.
    """
    from app.konspekt_templates import get_template

    template = get_template(content.get("template"))
    return template.accent or get_subject_accent_hex(content.get("subject"))


def resolve_accent_rgb(content: dict) -> tuple[int, int, int]:
    hex_str = resolve_accent_hex(content).lstrip("#")
    return int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
