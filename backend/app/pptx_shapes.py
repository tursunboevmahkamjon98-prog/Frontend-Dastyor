
from __future__ import annotations


def flatten(shape):
    try:
        shape.shadow.inherit = False
    except Exception:
        pass
    try:
        style = shape._element.find(
            "{http://schemas.openxmlformats.org/presentationml/2006/main}style")
        if style is not None:
            ref = style.find(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}effectRef")
            if ref is not None:
                ref.set("idx", "0")
    except Exception:
        pass
    return shape
