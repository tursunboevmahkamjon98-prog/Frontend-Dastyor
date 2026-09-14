"""Renders a .pptx to PDF by handing it to LibreOffice.

The presentation preview in the mobile app is a PDF viewer, and the PDF it
used to show was a separate A4 portrait document built by
export_builder.build_presentation_pdf — same content, but shaped like a
report rather than a deck, so a teacher checking their slides saw
something that did not look like the file they were about to download.

Converting the real .pptx removes the second implementation entirely: the
preview IS the deck, including every layout, chart and decoration
export_builder puts in it, and it cannot drift from the download the way
two builders inevitably did.

LibreOffice is optional at runtime. When it is missing or fails, convert()
returns None and the caller keeps using the old PDF builder, so a
deployment without it degrades to exactly the previous behaviour instead
of breaking downloads.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
from collections import OrderedDict

from app.logger import get_logger

logger = get_logger(__name__)

# Enough for one class's worth of back-and-forth on the same deck. Each
# entry is a rendered PDF held in memory, hence the small bound: the
# preview refetches on every screen open, and re-running LibreOffice for a
# deck nothing has changed about is seconds of CPU for an identical file.
_CACHE_MAX = 12
_cache: "OrderedDict[str, bytes]" = OrderedDict()

# 90s is generous for a 20-slide deck (a few seconds in practice) while
# still bounding a hung soffice, which otherwise holds the worker forever.
_TIMEOUT_SECONDS = 90

_CANDIDATE_BINARIES = (
    "soffice",
    "libreoffice",
    "/usr/bin/soffice",
    "/usr/bin/libreoffice",
    "/usr/lib/libreoffice/program/soffice",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
)


def find_binary() -> str | None:
    """Path to a usable LibreOffice, or None if this machine has none."""
    for name in _CANDIDATE_BINARIES:
        found = shutil.which(name) if os.path.basename(name) == name else (
            name if os.path.exists(name) else None
        )
        if found:
            return found
    return None


def cache_key_for(content: dict) -> str:
    """A stable key for a deck's rendered PDF.

    Deliberately derived from the material's own JSON rather than from the
    .pptx bytes: python-pptx writes fresh timestamps and part ids into the
    zip on every build, so two builds of an unchanged deck differ byte for
    byte and a hash of them never hits. Keying the content instead is what
    makes the cache actually work — measured 17s on both calls before this,
    since every lookup missed."""
    blob = json.dumps(content, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def cached(key: str) -> io.BytesIO | None:
    """An already-rendered PDF for [key], if one is still held. Checked
    before building the .pptx at all — on a hit there is nothing to
    convert and nothing to build."""
    hit = _cache.get(key)
    if hit is None:
        return None
    _cache.move_to_end(key)
    return io.BytesIO(hit)


def convert(pptx_bytes: bytes, cache_key: str) -> io.BytesIO | None:
    """The deck as a PDF, or None if LibreOffice could not produce one.

    Never raises: every failure path here has a working fallback in the
    caller, and turning a preview into a 500 would be worse than showing
    the older, document-shaped PDF."""
    key = cache_key
    hit = cached(key)
    if hit is not None:
        return hit

    binary = find_binary()
    if binary is None:
        logger.info("LibreOffice not installed — falling back to the built PDF")
        return None

    with tempfile.TemporaryDirectory(prefix="pptx2pdf-") as work:
        src = os.path.join(work, "deck.pptx")
        with open(src, "wb") as fh:
            fh.write(pptx_bytes)
        # A private profile per conversion. Sharing the default one makes
        # concurrent soffice invocations fight over the same lock and fail
        # intermittently, which is exactly the kind of bug that only shows
        # up once two teachers export at the same time.
        profile = os.path.join(work, "profile")
        try:
            result = subprocess.run(
                [
                    binary,
                    f"-env:UserInstallation=file:///{profile.replace(os.sep, '/').lstrip('/')}",
                    "--headless",
                    "--norestore",
                    "--convert-to", "pdf",
                    "--outdir", work,
                    src,
                ],
                capture_output=True,
                timeout=_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            logger.error(f"LibreOffice timed out after {_TIMEOUT_SECONDS}s converting a deck")
            return None
        except Exception as e:  # noqa: BLE001 — see docstring
            logger.error(f"LibreOffice could not be started: {e}")
            return None

        out = os.path.join(work, "deck.pdf")
        if not os.path.exists(out):
            logger.error(
                f"LibreOffice produced no PDF (exit {result.returncode}): "
                f"{result.stderr[:300].decode('utf-8', 'replace')}"
            )
            return None
        with open(out, "rb") as fh:
            pdf = fh.read()

    if not pdf.startswith(b"%PDF"):
        logger.error("LibreOffice output was not a PDF")
        return None

    _cache[key] = pdf
    while len(_cache) > _CACHE_MAX:
        _cache.popitem(last=False)
    return io.BytesIO(pdf)
