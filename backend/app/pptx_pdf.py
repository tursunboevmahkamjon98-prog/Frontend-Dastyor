import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import threading
from collections import OrderedDict

from app.config import get_settings
from app.logger import get_logger

logger = get_logger(__name__)

_CACHE_MAX = 12
_cache: "OrderedDict[str, bytes]" = OrderedDict()

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
    for name in _CANDIDATE_BINARIES:
        found = shutil.which(name) if os.path.basename(name) == name else (
            name if os.path.exists(name) else None
        )
        if found:
            return found
    return None


def cache_key_for(content: dict) -> str:
    blob = json.dumps(content, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def cached(key: str) -> io.BytesIO | None:
    hit = _cache.get(key)
    if hit is None:
        return None
    _cache.move_to_end(key)
    return io.BytesIO(hit)


_convert_slots: "threading.Semaphore | None" = None
_slots_lock = threading.Lock()


def _slots() -> threading.Semaphore:
    global _convert_slots
    if _convert_slots is None:
        with _slots_lock:
            if _convert_slots is None:
                try:
                    n = max(1, get_settings().MAX_CONCURRENT_PPTX_CONVERSIONS)
                except Exception:
                    n = 1
                _convert_slots = threading.Semaphore(n)
    return _convert_slots


def convert(pptx_bytes: bytes, cache_key: str) -> io.BytesIO | None:
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
        profile = os.path.join(work, "profile")
        try:
            with _slots():
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
        except Exception as e:
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
