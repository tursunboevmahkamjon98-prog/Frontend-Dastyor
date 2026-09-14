# -*- coding: utf-8 -*-
"""One shared fix for the drop shadow python-pptx puts on every autoshape.

Every new autoshape carries a `<p:style>` block whose `<a:effectRef>`
points at the theme's soft drop shadow. Setting `shape.shadow.inherit =
False` writes an empty `<a:effectLst/>` into `<p:spPr>`, which is the
documented override — and PowerPoint honours it.

LibreOffice does not. It keeps drawing the themed shadow from the style
reference regardless, so every card, badge and figure comes out with a
grey halo behind it: the exact 2007-clipart look this deck's design is
trying to get away from.

That is not a cosmetic detail for this product. The in-app presentation
preview is a PDF rendered by LibreOffice (see app/pptx_pdf.py), so
LibreOffice's output is what a teacher actually looks at on their phone.
Zeroing the effect reference as well as the effect list makes both
renderers agree on a flat shape.
"""

from __future__ import annotations


def flatten(shape):
    """Remove the inherited drop shadow in a way BOTH PowerPoint and
    LibreOffice respect. Returns the shape, so it can wrap a call."""
    try:
        shape.shadow.inherit = False
    except Exception:
        pass
    try:
        # `<a:effectRef idx="0">` means "no effect from the theme". The
        # element is required to have an idx, so it is zeroed rather than
        # removed — dropping it outright makes some readers fall back to
        # the style default, which is the shadow again.
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
