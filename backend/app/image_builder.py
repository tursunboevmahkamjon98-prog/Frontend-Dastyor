"""Fetches a real, topic-relevant photo from Wikipedia — not a generic stock
image or an AI-generated illustration, but an actual photograph/illustration
Wikipedia already hosts for a specific, notable person/place/species/
artifact/phenomenon. Used to illustrate konspekts for every subject except
geography (which gets the more specialized OpenStreetMap map instead — see
app/map_builder.py).

Talks to Wikipedia via `curl` subprocesses rather than httpx: Wikimedia's
edge blocks httpx's TLS fingerprint outright ("Please respect our robot
policy" 403, confirmed even with a compliant User-Agent and matching
headers) while the exact same request via curl succeeds — a known class of
issue with Python HTTP clients against Cloudflare-fronted sites. curl ships
with Windows 10+ and every normal Linux distro, so this doesn't add a new
runtime dependency.

Same fail-soft philosophy as map_builder.py: any error here just means the
konspekt goes out without an image, never a broken generation. And since the
whole point is a topic-specific picture (not decoration), the AI is free to
say "no good image exists for this" and this module then does nothing."""

import asyncio
import json
import os
import random
import re
import urllib.parse
import uuid
from PIL import Image
import io
from app.logger import get_logger

logger = get_logger(__name__)

_USER_AGENT = "TeachAIweb/1.0 (educational konspekt illustration)"
_IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "images")
os.makedirs(_IMAGES_DIR, exist_ok=True)

# Wikipedia language subdomains for each language the app generates lessons
# in — English is always tried as a fallback since it has by far the deepest
# image coverage (a Tajik-language lesson about a topic with no tg.wikipedia
# article should still get its picture from en.wikipedia).
_WIKI_LANGS = {
    "Русский": "ru", "Таджикский": "tg", "English": "en", "Английский": "en",
}

_MAX_DIM = 900

# A caller-side concurrency limit (e.g. asyncio.Semaphore in ai_service.py)
# only bounds how many requests are IN FLIGHT at once — asyncio.gather still
# launches every task back-to-back, so as each one finishes it's instantly
# replaced by the next, keeping the request RATE just as high. Confirmed
# live: Wikimedia throttled this app's IP after a handful of requests
# within a couple seconds even with concurrency capped at 2-3. This is a
# global pacer at the actual network call site (every _curl_bytes call,
# regardless of which function or how many concurrent callers) that spaces
# request *starts* apart by a minimum interval — the real fix, since it
# caps the one thing that actually matters (requests per second landing on
# Wikimedia's edge), not how many happen to be waiting at once.
_last_request_at = [0.0]
_pacer_lock = asyncio.Lock()
_MIN_REQUEST_INTERVAL = 0.6  # seconds between request starts, globally

# A shared circuit breaker on top of the fixed-interval pacer above.
#
# The pacer alone assumes Wikimedia's limit is a simple rate — space
# requests 0.6s apart and you're safe. Measured live under real concurrent
# load (eight slides fetching pictures at once) that assumption is wrong:
# once Wikimedia starts answering 429, EVERY concurrent caller keeps
# independently retrying into the same wall at the same fixed spacing,
# which cannot recover because nothing backs off — a storm of 429s just
# stays a storm. A real deck came back with zero images out of fifteen
# slides this way.
#
# `_backoff_until` is a shared deadline every caller waits out, pushed
# further into the future by each 429 rather than reset per-request: the
# whole app cools down together, and the push-back compounds if the block
# is still active on the next attempt instead of firing straight into it
# again 0.6s later.
_backoff_until = [0.0]
_consecutive_429 = [0]


async def _pace_request():
    async with _pacer_lock:
        loop = asyncio.get_event_loop()
        now = loop.time()
        wait = max(_last_request_at[0] + _MIN_REQUEST_INTERVAL,
                   _backoff_until[0]) - now
        if wait > 0:
            await asyncio.sleep(wait)
        _last_request_at[0] = loop.time()


def _note_response(status: str) -> None:
    """Feeds one HTTP outcome into the shared circuit breaker."""
    loop = asyncio.get_event_loop()
    if status == "429":
        _consecutive_429[0] += 1
        # Capped growth, not unbounded exponential: a 429 storm should
        # cost seconds, not lock out the rest of the deck's own timeout
        # budget (75s — see ai_service._render_slide_images).
        penalty = min(12.0, 1.5 * _consecutive_429[0])
        _backoff_until[0] = max(_backoff_until[0], loop.time() + penalty)
    elif status == "200":
        _consecutive_429[0] = 0


async def _curl_bytes(url: str, timeout: float = 10.0, _retries: int = 1) -> bytes | None:
    """Confirmed live: a real, well-matched thumb.wikimedia.org URL (not
    upload.wikimedia.org, which serves cached originals fast) can take
    8+ seconds on a cache-miss — Wikimedia renders that thumbnail size on
    first request rather than serving a pre-made file. The previous 6.0s
    default was shorter than that, so curl hit its own --max-time and
    returned exit code 28 (timeout) on a request that was actually
    succeeding, just slowly — confirmed by re-running the exact same URL
    outside the 6s budget and getting a real HTTP 200 at ~8s. A whole
    presentation's worth of slides each lost a real, relevant picture to
    this, silently falling back to a bullet-only layout. 10.0s is still
    well under what a deck-generation request's own caller-side deadline
    budgets for a single image lookup.

    Confirmed live: Wikimedia's edge starts returning HTTP errors (429/5xx)
    to this app's IP after just a handful of requests in quick succession —
    a whole presentation's worth of per-slide image lookups fired together
    was silently losing most of its images to this. Retries once on
    rate-limit/server errors (and on connection-level failures like a
    timeout), but NOT on a real 404 — that's a genuine "no such page",
    retrying it would just waste time for the same empty result.

    Deliberately just ONE retry with a short, flat backoff — an earlier
    version retried 3x with exponential backoff (up to 14s of sleeping per
    URL), and since a single image needs up to 5 of these calls, a
    multi-slide deck's total generation time could stack up to several
    minutes and read as the app being stuck. fetch_topic_image callers
    additionally wrap each slide in its own hard deadline (see
    ai_service.py) so one bad lookup still can't hang the whole request.

    Reads the actual HTTP status via curl's -w flag (previously used -f,
    which made curl itself swallow the status and just exit non-zero for
    any 4xx/5xx alike, so a rate-limit couldn't be told apart from a
    not-found).

    Runs curl via the SYNCHRONOUS subprocess module inside a worker thread
    (loop.run_in_executor), not asyncio.create_subprocess_exec — that call
    needs the event loop's own subprocess transport, which uvicorn
    deliberately disables on Windows the moment it's run with `--reload`
    (it switches to WindowsSelectorEventLoopPolicy so its own reloader
    subprocess behaves; see uvicorn/loops/asyncio.py's asyncio_setup).
    Under that policy every asyncio subprocess call raises a bare
    NotImplementedError, so every image fetch silently failed in dev
    specifically because of --reload — production's `--workers 1` (no
    --reload) was never affected, but this worker-thread approach means
    dev doesn't need to avoid --reload to get real images either."""
    delay = 1.0
    for attempt in range(_retries + 1):
        await _pace_request()
        try:
            stdout, stderr, returncode = await asyncio.get_event_loop().run_in_executor(
                None, _run_curl_sync, url, timeout
            )
            if returncode == 0:
                body, _, status_line = stdout.rpartition(b"\n")
                status = status_line.decode("ascii", "ignore").strip()
                _note_response(status)
                if status == "200":
                    return body
                if status != "429" and not status.startswith("5"):
                    return None  # a real 4xx (404 etc.) — not found, no point retrying
                logger.warning(f"Wikipedia HTTP {status} for {url} (attempt {attempt + 1}/{_retries + 1})")
            else:
                logger.warning(f"curl failed ({returncode}) for {url}: {stderr[:200]!r}")
        except Exception as e:
            logger.warning(f"curl subprocess failed for {url}: {type(e).__name__}: {e!r}")
        if attempt < _retries:
            await asyncio.sleep(delay)
            delay *= 2
    return None


def _run_curl_sync(url: str, timeout: float) -> tuple[bytes, bytes, int]:
    """The actual blocking curl call — always run off the event loop thread
    via run_in_executor (see _curl_bytes). Plain subprocess.run has no
    dependency on the event loop's subprocess transport, unlike
    asyncio.create_subprocess_exec, so it works under any event loop
    policy uvicorn picks."""
    import subprocess
    proc = subprocess.run(
        ["curl", "-s", "-L", "--max-time", str(int(timeout)), "-A", _USER_AGENT, "-w", "\n%{http_code}", url],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return proc.stdout, proc.stderr, proc.returncode


async def _curl_json(url: str, timeout: float = 8.0) -> dict | None:
    raw = await _curl_bytes(url, timeout)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Non-JSON response from {url}: {e}")
        return None


# Generic descriptor words that legitimately appear in an image_query
# ("portrait", "photo"...) but almost never appear in the Wikipedia article
# title itself — requiring them to match would reject good results, so
# they're excluded before checking overlap between query and title.
_GENERIC_IMAGE_WORDS = {
    "portrait", "photo", "photograph", "picture", "image", "statue", "monument",
    "map", "diagram", "illustration", "drawing", "painting", "model", "scene",
    "view", "closeup", "logo", "flag", "symbol", "icon", "sculpture",
    # "diagram"-style queries ("Frog internal anatomy") are built from a
    # subject word ("Frog") plus these descriptor words — confirmed live:
    # without excluding them, "Frog internal anatomy" matched Wikipedia's
    # generic "Anatomy" article (a human-skeleton woodcut, nothing to do
    # with a frog) purely on the shared word "anatomy". Excluding them
    # forces the match to hinge on the actual subject word instead.
    "anatomy", "internal", "structure", "structural",
    # Homonym adjectives: "simple"/"complex" describe a substance in
    # chemistry AND a signal in electronics AND a number in math. Confirmed
    # live: a chemistry query for "simple complex substance comparison"
    # matched a Fourier-transform waveform figure purely on the shared word
    # "complex" — nothing to do with the lesson. Excluding them from the
    # match forces the overlap to hinge on the actual subject noun.
    "simple", "complex", "basic", "general", "system",
}


def _significant_words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ]{3,}", text)}


def _title_matches_query(query: str, title: str) -> bool:
    """Wikipedia's/Commons' full-text search is fuzzy enough to return
    completely unrelated results for a specific query — confirmed live:
    "Francois Viet portrait" (asking for the mathematician François
    Viète) matched "Vietnam War" (its search engine apparently weighting
    the "Viet" substring), and a Commons logo search for "C++ logo"
    returned "UAAR logo 2012.svg" (an unrelated Italian atheist
    organization) as its very top hit. A wrong photo/logo is worse than
    no photo for a teacher's material, so require the query and the
    title it matched to actually overlap before trusting the result.

    Primary check: at least one real (3+ letter) word in common. Short or
    symbolic queries a real programming language/tech name often is
    ("C++", "C#", ".NET", "R") have NO 3+ letter word at all — treating
    that as "nothing to check, so don't block" (an earlier version of
    this function) is exactly what let the C++/UAAR mismatch through. The
    fallback for those is a literal substring check — but it must keep
    the query's symbol characters (+, #, .) rather than stripping down to
    bare alphanumerics: a first attempt at this fallback stripped "C++"
    down to just "c" (1 character), which then substring-matched almost
    any title at all (confirmed live: matched "Mercedes-Benz Logo 2010"
    next, WORSE than the original bug). Below a certain length there's no
    safe substring left to check at all, so short queries that still
    produce fewer than 2 characters after normalization are rejected
    outright rather than trusted."""
    q_words = _significant_words(query) - _GENERIC_IMAGE_WORDS
    if q_words:
        return bool(q_words & _significant_words(title))
    q_norm = re.sub(r"\s+", "", query.lower())
    if len(q_norm) < 2:
        return False  # too short to safely validate against — don't trust it
    return q_norm in re.sub(r"\s+", "", title.lower())


async def _search_title(lang: str, query: str) -> str | None:
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 1,
    })
    data = await _curl_json(url)
    if not data:
        return None
    results = data.get("query", {}).get("search", [])
    if not results:
        return None
    title = results[0]["title"]
    if not _title_matches_query(query, title):
        logger.warning(f"Rejecting unrelated Wikipedia match: query={query!r} matched title={title!r}")
        return None
    return title


async def _fetch_summary_thumbnail(lang: str, title: str) -> tuple[str, str] | None:
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
    data = await _curl_json(url)
    if not data:
        return None
    thumb = data.get("thumbnail", {}).get("source")
    if not thumb:
        return None
    return thumb, data.get("title", title)


async def fetch_topic_image(query: str, language: str = "Русский") -> dict | None:
    """Looks up `query` on Wikipedia (the lesson's own language first, then
    English as a fallback), downloads the page's thumbnail, saves it under
    uploads/images/, and returns {"path": "/uploads/images/<uuid>.jpg",
    "caption": "<actual page title>"} — or None if nothing usable turned up."""
    if not query or not query.strip():
        return None

    # The AI is instructed to write image_topic in English, so searching
    # English Wikipedia first gets the most precise match — searching the
    # lesson's own language wiki with an English query first was actually
    # producing wrong matches (e.g. "Snow leopard" hit the "Mac OS X Snow
    # Leopard" article on ru.wikipedia instead of the animal). The lesson's
    # own-language wiki is still tried second in case English has no article.
    primary = _WIKI_LANGS.get(language, "ru")
    langs_to_try = ["en"] if primary == "en" else ["en", primary]

    for lang in langs_to_try:
        title = await _search_title(lang, query)
        if not title:
            continue
        hit = await _fetch_summary_thumbnail(lang, title)
        if not hit:
            continue
        image_url, page_title = hit
        raw = await _curl_bytes(image_url)
        if not raw:
            continue
        try:
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            img.thumbnail((_MAX_DIM, _MAX_DIM))
            filename = f"{uuid.uuid4().hex}.jpg"
            out_path = os.path.join(_IMAGES_DIR, filename)
            img.save(out_path, "JPEG", quality=88)
            return {"path": f"/uploads/images/{filename}", "caption": page_title}
        except Exception as e:
            logger.warning(f"Image decode/save failed for '{image_url}': {e}")
            continue
    return None


# ── Real-world logos / background-removed photo cutouts ────────────────────
#
# Separate from fetch_topic_image (which flattens everything to a plain
# rectangular JPEG) — these two "real_image_style" variants need to KEEP a
# transparent subject instead of a boxed photo: a company/software logo
# should render as a clean mark, and a named animal/plant photo should read
# as a cutout placed directly on the page instead of framed inside a photo
# rectangle. Uses rembg (a local ONNX background-removal model, no external
# API) for the "cutout" style — the first call on a fresh machine downloads
# the ~176MB u2net model once; every call after that is local and fast.

_rembg_session = None


def _rembg_remove_sync(data: bytes) -> bytes:
    """Runs on a worker thread via asyncio.to_thread — rembg's inference is
    a blocking CPU (or GPU, if available) call, and running it directly on
    the event loop would stall every other in-flight request for the
    couple of seconds it takes. Session is cached at module level so the
    ONNX model is loaded from disk only once per process, not once per
    image."""
    global _rembg_session
    from rembg import remove, new_session
    if _rembg_session is None:
        _rembg_session = new_session("u2net")
    return remove(data, session=_rembg_session)


def _trim_transparent(img: Image.Image, pad: int = 14) -> Image.Image:
    """Crops a RGBA image down to its actual opaque content (plus a small
    even padding) instead of leaving whatever margin the source photo
    happened to have — a rembg cutout or a logo PNG both tend to sit in a
    canvas much bigger than the subject itself, which otherwise shows up
    as unwanted empty space once embedded in the document (exactly what
    the teacher asked to avoid: "chiroyli joylashtirib bosh joy
    qolmasin")."""
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    l, t = max(l - pad, 0), max(t - pad, 0)
    r, b = min(r + pad, img.width), min(b + pad, img.height)
    return img.crop((l, t, r, b))


async def _cutout_background(raw: bytes) -> bytes | None:
    """raw -> a background-removed RGBA PNG, trimmed to its subject and
    resized to _MAX_DIM first so the model runs on a reasonably sized
    image (both faster and avoids rembg choking on a huge original)."""
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img.thumbnail((_MAX_DIM, _MAX_DIM))
        buf_in = io.BytesIO()
        img.save(buf_in, "PNG")
        cut = await asyncio.to_thread(_rembg_remove_sync, buf_in.getvalue())
        trimmed = _trim_transparent(Image.open(io.BytesIO(cut)).convert("RGBA"))
        buf_out = io.BytesIO()
        trimmed.save(buf_out, "PNG")
        return buf_out.getvalue()
    except Exception as e:
        logger.warning(f"Background removal failed: {e}")
        return None


def _prepare_logo(raw: bytes) -> bytes | None:
    """raw -> RGBA PNG, trimmed to content — preserving whatever
    transparency the source image already has (most Wikipedia/Commons logo
    renditions are already a clean mark on a transparent or white
    background) — no ML background removal needed for logos, just a
    straight decode/trim/resize/re-encode."""
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        img = _trim_transparent(img)
        img.thumbnail((_MAX_DIM, _MAX_DIM))
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()
    except Exception as e:
        logger.warning(f"Logo image decode failed: {e}")
        return None


_LOGO_FILE_EXTS = (".png", ".svg", ".jpg", ".jpeg", ".webp")


async def _commons_logo_url(query: str) -> str | None:
    """Searches Wikimedia Commons' File namespace for a dedicated logo
    file, instead of pulling a Wikipedia ARTICLE's lead thumbnail —
    confirmed live that e.g. the "Windows 11" article's thumbnail is a
    full desktop screenshot, not the corporate logo mark. Commons' file
    search reliably surfaces the actual standalone logo image. Returns a
    raster (PNG/JPG) URL — SVG originals are requested via iiurlwidth so
    MediaWiki returns a rendered PNG thumbnail instead of the raw .svg
    (which PIL can't decode).

    Validates each candidate against the ORIGINAL query (not the
    "... logo"-suffixed search string) via _title_matches_query —
    confirmed live this was missing entirely and a "C++ logo" search's
    top hit was "UAAR logo 2012.svg" (an unrelated Italian atheist
    organization's logo), which went straight into konspekts with no
    check at all. Walks the search results in order and returns the
    first one that actually matches."""
    search_q = query if "logo" in query.lower() else f"{query} logo"
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "list": "search", "srsearch": search_q,
        "srnamespace": 6, "format": "json", "srlimit": 10,
    })
    data = await _curl_json(url)
    if not data:
        return None
    for r in data.get("query", {}).get("search", []):
        title = r.get("title", "")
        if not title.lower().endswith(_LOGO_FILE_EXTS):
            continue
        if not _title_matches_query(query, title):
            continue
        info_url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "titles": title, "prop": "imageinfo",
            "iiprop": "url", "iiurlwidth": 800, "format": "json",
        })
        info = await _curl_json(info_url)
        if not info:
            continue
        for page in info.get("query", {}).get("pages", {}).values():
            imageinfo = page.get("imageinfo")
            if imageinfo:
                image_url = imageinfo[0].get("thumburl") or imageinfo[0].get("url")
                if image_url and not image_url.lower().endswith(".svg"):
                    return image_url
    return None


def _clean_logo_caption(query: str) -> str:
    return re.sub(r"\s+logo$", "", query, flags=re.IGNORECASE).strip() or query


_DIAGRAM_FILE_EXTS = (".png", ".svg", ".jpg", ".jpeg", ".webp", ".gif")

# Title/category words that give away a real photograph rather than a
# drawn diagram — confirmed live: "Internal anatomy Common frog (lat.
# Rana temporaria).jpg" (title alone gives no hint at all — this is what
# defeated a plain title-keyword filter) turned out, per its Commons
# category list, to be an entry from "European Science Photo Competition
# 2015" — an actual dissection photograph. Checked against BOTH the title
# and the file's Commons categories (via extmetadata, see
# _looks_like_photo) since the giveaway is often only in the latter.
_PHOTO_GIVEAWAY_WORDS = (
    "photo", "photograph", "dissection", "dissected", "specimen", "cadaver",
    "postmortem", "post-mortem", "necropsy", "autopsy", "surgical", "graft",
    "hibernating", "taxidermy",
)


def _looks_like_photo(title: str, categories: str) -> bool:
    text = f"{title} {categories}".lower()
    return any(w in text for w in _PHOTO_GIVEAWAY_WORDS)


async def _commons_diagram_candidates(query: str) -> list[tuple[str, str]]:
    """Searches Wikimedia Commons' File namespace for internal-anatomy
    diagram files — NOT via a Wikipedia article's summary thumbnail (that
    API only ever returns the article's lead/infobox image, which for an
    animal is essentially always a live photo, never an embedded internal
    diagram even when the article body has one). Commons indexes diagram
    files by their own title/description regardless of which article
    embeds them, the same reason _commons_logo_url uses it for logos.

    Validates each candidate two ways before including it: title vs
    query overlap (_title_matches_query — same "Anatomy" article mismatch
    problem as elsewhere) AND title+categories vs a photograph-giveaway
    wordlist (_looks_like_photo — see its docstring for why categories
    matter, not just the title). A real photograph is worse than no image
    for this style, same rule as _title_matches_query's own docstring.

    Returns ALL qualifying candidates in search-relevance order (not just
    the first) — {(image_url, cleaned_title), ...} — so the caller
    (fetch_real_image) can additionally reject a candidate for having a
    noisy/textured background (an old book-scan plate; see
    _background_is_clean) and fall through to try the next one, instead
    of the whole lookup dead-ending on the very first hit."""
    search_q = query if "diagram" in query.lower() or "anatomy" in query.lower() else f"{query} anatomy diagram"
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "list": "search", "srsearch": search_q,
        "srnamespace": 6, "format": "json", "srlimit": 15,
    })
    data = await _curl_json(url)
    if not data:
        return []
    candidates: list[tuple[str, str]] = []
    for r in data.get("query", {}).get("search", []):
        title = r.get("title", "")
        if not title.lower().endswith(_DIAGRAM_FILE_EXTS):
            continue
        if not _title_matches_query(query, title):
            continue
        info_url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "titles": title, "prop": "imageinfo",
            "iiprop": "url|extmetadata", "iiurlwidth": 900, "format": "json",
        })
        info = await _curl_json(info_url)
        if not info:
            continue
        for page in info.get("query", {}).get("pages", {}).values():
            imageinfo = page.get("imageinfo")
            if not imageinfo:
                continue
            categories = imageinfo[0].get("extmetadata", {}).get("Categories", {}).get("value", "")
            if _looks_like_photo(title, categories):
                continue
            image_url = imageinfo[0].get("thumburl") or imageinfo[0].get("url")
            if image_url and not image_url.lower().endswith(".svg"):
                clean_title = re.sub(r"^File:", "", title, flags=re.IGNORECASE)
                clean_title = re.sub(r"\.\w+$", "", clean_title).strip() or query
                candidates.append((image_url, clean_title))
    return candidates


def _has_real_transparency(img: Image.Image) -> bool:
    """True if img (already RGBA) has at least some meaningfully
    non-opaque pixels — i.e. the source SVG's own canvas was already
    transparent, so no further background removal is needed."""
    lo, _hi = img.getchannel("A").getextrema()
    return lo < 250


def _background_is_clean(img: Image.Image, tolerance: int = 32, noise_threshold: float = 0.02) -> bool:
    """True if the image's background reads as a flat, uniform color — a
    modern diagram's plain white/off-white canvas — rather than a
    textured/noisy one (an old scanned book-page plate: paper grain,
    foxing, scan artifacts). Used to reject a noisy-scan candidate for
    "diagram" style outright rather than accept a background-removed-but-
    speckled result.

    Sampling only the four corners to check uniformity (an earlier
    version of this check) is NOT enough — confirmed live: scan artifacts
    are sparse and scattered, so a small corner patch can land in a
    locally-clean spot and read as "flat" even though the full page is
    visibly speckled elsewhere. Instead, this keys the WHOLE image
    against the corner-sampled color (same as _chroma_key_background)
    and measures how much a median filter has to "correct" that raw
    mask: a genuinely flat background changes almost no pixels; a noisy
    scan flips many isolated speckle pixels. That correction fraction
    IS the actual noise the color-key would leave behind, so it's a
    direct measure of exactly what we're trying to avoid shipping."""
    import numpy as np
    from PIL import ImageFilter
    arr = np.array(img.convert("RGB")).astype(np.int16)
    h, w = arr.shape[:2]
    c = max(4, min(h, w) // 20)
    corners = np.concatenate([
        arr[:c, :c].reshape(-1, 3), arr[:c, -c:].reshape(-1, 3),
        arr[-c:, :c].reshape(-1, 3), arr[-c:, -c:].reshape(-1, 3),
    ])
    bg_color = np.median(corners, axis=0)
    dist = np.sqrt(((arr - bg_color) ** 2).sum(axis=-1))
    raw_mask = dist <= tolerance
    raw_img = Image.fromarray((raw_mask * 255).astype(np.uint8), "L")
    filtered_mask = np.array(raw_img.filter(ImageFilter.MedianFilter(size=5))) > 127
    noise_ratio = float(np.mean(raw_mask != filtered_mask))
    return noise_ratio <= noise_threshold


def _chroma_key_background(img: Image.Image, tolerance: int = 32) -> Image.Image:
    """RGBA -> RGBA with the image's OWN background color made
    transparent, sampled adaptively from its four corners rather than
    assumed to be pure white — confirmed live: a Commons diagram sourced
    from a century-old textbook scan (e.g. "The biology of the frog"
    plate) has a yellowed/beige page background, not white, so a
    fixed-white-only threshold left that border fully opaque. Any pixel
    within `tolerance` (Euclidean RGB distance) of the sampled corner
    color is keyed out instead.

    Used instead of rembg for "diagram" style: rembg's semantic
    segmentation is trained on photos of objects and isn't reliable on
    line-art diagrams (real risk of erasing thin strokes/labels it
    doesn't recognize as "foreground"), whereas a diagram's actual
    background is reliably just whatever flat color sits in its corners —
    a plain color-distance key removes exactly that without touching the
    drawn content. Vectorized with numpy (a transitive dep via
    rembg/onnxruntime, already available) since a naive per-pixel Python
    loop over a ~900px image is slow enough to feel stuck.

    Finishes with a median filter over the resulting opaque/transparent
    mask — confirmed live: an old book-scan page's background isn't a
    perfectly flat color (scan grain/foxing), so the raw distance-key
    left a "salt and pepper" speckle of stray opaque pixels scattered
    across what should be a clean transparent area. The median filter
    treats an isolated opaque speck surrounded by transparency as noise
    and drops it, while leaving the actual (much thicker) drawn strokes
    intact."""
    import numpy as np
    from PIL import ImageFilter
    arr = np.array(img.convert("RGBA")).astype(np.int16)
    h, w = arr.shape[:2]
    c = max(4, min(h, w) // 20)
    corners = np.concatenate([
        arr[:c, :c, :3].reshape(-1, 3), arr[:c, -c:, :3].reshape(-1, 3),
        arr[-c:, :c, :3].reshape(-1, 3), arr[-c:, -c:, :3].reshape(-1, 3),
    ])
    bg_color = np.median(corners, axis=0)
    dist = np.sqrt(((arr[..., :3] - bg_color) ** 2).sum(axis=-1))
    mask = np.where(dist <= tolerance, 0, 255).astype(np.uint8)
    mask = np.array(Image.fromarray(mask, "L").filter(ImageFilter.MedianFilter(size=5)))
    arr[..., 3] = np.minimum(arr[..., 3], mask)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


async def fetch_real_image(query: str, language: str = "Русский", style: str = "cutout") -> dict | None:
    """style="logo": searches Wikimedia Commons' File namespace for a
    dedicated brand/software/product logo file (see _commons_logo_url) and
    saves it trimmed to content, no background removal (most logo files
    are already a clean mark). style="cutout": looks up `query` on
    Wikipedia (English first, then the lesson language — same pipeline as
    fetch_topic_image), downloads the page's thumbnail photo, and runs it
    through rembg to remove the background (a named animal/plant/object).
    style="diagram": searches Commons' File namespace (see
    _commons_diagram_candidates) rather than a Wikipedia article's summary
    thumbnail — used for an organism's internal-anatomy illustration
    (query like "Frog internal anatomy"). Candidates whose title/category
    metadata reads as a real photograph (_looks_like_photo) are excluded
    entirely. Background removed via an adaptive color-key
    (_chroma_key_background), NOT rembg — rembg's photo-trained
    segmentation risks eating thin strokes/labels it doesn't recognize as
    "foreground", whereas a diagram's actual background is reliably just
    one flat color. Prefers a candidate with a genuinely clean/uniform
    background (_background_is_clean) over one with a noisy/speckled
    scanned-page background (an old textbook plate), but falls back to
    the best noisy one available rather than returning nothing if that's
    all Commons has for this query. Saves under uploads/images/ and
    returns {"path": "/uploads/images/
    <uuid>.png|.jpg", "caption": "..."} or None."""
    if not query or not query.strip():
        return None

    if style == "logo":
        image_url = await _commons_logo_url(query)
        if not image_url:
            return None
        raw = await _curl_bytes(image_url)
        if not raw:
            return None
        processed = _prepare_logo(raw)
        if not processed:
            return None
        try:
            filename = f"{uuid.uuid4().hex}.png"
            out_path = os.path.join(_IMAGES_DIR, filename)
            with open(out_path, "wb") as f:
                f.write(processed)
            return {"path": f"/uploads/images/{filename}", "caption": _clean_logo_caption(query)}
        except Exception as e:
            logger.warning(f"Logo image save failed for '{image_url}': {e}")
            return None

    if style == "diagram":
        # Commons file search, not the Wikipedia article-summary pipeline
        # below — see _commons_diagram_candidates' docstring for why the
        # latter reliably mismatches for this style (an article's lead
        # thumbnail is a live photo, not the internal diagram, so it
        # doesn't even find the right image family to begin with).
        candidates = await _commons_diagram_candidates(query)
        # Shuffled rather than walked in raw search-relevance order —
        # otherwise, whenever a topic genuinely has more than one valid
        # diagram on Commons, regenerating the same konspekt always landed
        # on the exact same one anyway (Commons search is deterministic
        # for an identical query), which read as "always the same image"
        # even though other valid options existed. Search relevance still
        # decides WHICH files qualify (via _title_matches_query/
        # _looks_like_photo above); this only decides which of the
        # already-qualified ones wins on any given call.
        random.shuffle(candidates)
        # Kept only as a last resort — the first noisy-background candidate
        # we're able to process, used only if the loop below finds no
        # clean one at all. Better a speckled diagram than no diagram.
        fallback: tuple[Image.Image, str] | None = None
        for image_url, title in candidates:
            raw = await _curl_bytes(image_url)
            if not raw:
                continue
            try:
                img = Image.open(io.BytesIO(raw)).convert("RGBA")
                if _has_real_transparency(img):
                    pass  # SVG's own canvas was already transparent
                elif _background_is_clean(img):
                    img = _chroma_key_background(img)
                else:
                    # A noisy/textured background (old book-scan plate) —
                    # no color-key fully cleans this without also eating
                    # into the actual line art (see _background_is_clean's
                    # docstring). Still run the best-effort key (leaves
                    # some speckle) and hold onto it as a fallback, but
                    # keep looking for a genuinely clean candidate first.
                    if fallback is None:
                        fallback = (_chroma_key_background(img), title)
                    continue
                img = _trim_transparent(img)
                img.thumbnail((_MAX_DIM, _MAX_DIM))
                filename = f"{uuid.uuid4().hex}.png"
                out_path = os.path.join(_IMAGES_DIR, filename)
                img.save(out_path, "PNG")
                return {"path": f"/uploads/images/{filename}", "caption": title}
            except Exception as e:
                logger.warning(f"Diagram image save failed for '{image_url}': {e}")
                continue

        if fallback is not None:
            try:
                img, title = fallback
                img = _trim_transparent(img)
                img.thumbnail((_MAX_DIM, _MAX_DIM))
                filename = f"{uuid.uuid4().hex}.png"
                out_path = os.path.join(_IMAGES_DIR, filename)
                img.save(out_path, "PNG")
                return {"path": f"/uploads/images/{filename}", "caption": title}
            except Exception as e:
                logger.warning(f"Diagram fallback image save failed: {e}")
        return None

    primary = _WIKI_LANGS.get(language, "ru")
    langs_to_try = ["en"] if primary == "en" else ["en", primary]

    for lang in langs_to_try:
        title = await _search_title(lang, query)
        if not title:
            continue
        hit = await _fetch_summary_thumbnail(lang, title)
        if not hit:
            continue
        image_url, page_title = hit
        raw = await _curl_bytes(image_url)
        if not raw:
            continue
        processed = await _cutout_background(raw)
        if not processed:
            continue
        try:
            filename = f"{uuid.uuid4().hex}.png"
            out_path = os.path.join(_IMAGES_DIR, filename)
            with open(out_path, "wb") as f:
                f.write(processed)
            return {"path": f"/uploads/images/{filename}", "caption": page_title}
        except Exception as e:
            logger.warning(f"Real image save failed for '{image_url}': {e}")
            continue
    return None


async def fetch_topic_images(items: list[dict], language: str = "Русский") -> list[dict]:
    """Batch version of fetch_topic_image — `items` is a list of {"topic":
    ..., "section": ...} dicts (the AI's image_topics field). Fetches each
    independently and returns only the ones that actually succeeded, each
    carrying its "section" through so the caller can place it next to the
    right part of the konspekt. One failed lookup never drops the others."""
    results = []
    for item in items:
        topic = (item or {}).get("topic", "")
        section = (item or {}).get("section", "")
        hit = await fetch_topic_image(topic, language)
        if hit:
            hit["section"] = section
            results.append(hit)
    return results


# ── Subject cover image (for the PDF cover page — see cover_builder.py) ────
#
# One fixed, generic photo PER SUBJECT (e.g. always the same representative
# "Biology" picture), not tied to any individual lesson's topic — fetched
# once per subject and cached on disk under a subject-slug filename so every
# later konspekt of that subject reuses the same file instantly, no repeat
# network calls.

_SUBJECT_COVERS_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "subject_covers")
os.makedirs(_SUBJECT_COVERS_DIR, exist_ok=True)

_SUBJECT_COVER_QUERIES = {
    # Deliberately concrete, photographable subjects rather than the
    # abstract field name — confirmed live that e.g. "Chemistry" and
    # "Computer science" mostly have non-photo thumbnails (a Gibbs-energy
    # diagram, a near-blank icon), while a specific real-world object
    # almost always has a proper photo.
    "Математика": "Abacus", "Алгебра": "Abacus", "Геометрия": "Compass and straightedge",
    "Информатика": "Laptop computer", "Физика": "Isaac Newton", "Химия": "Laboratory glassware",
    "Биология": "Biology", "География": "Geography",
    "История Таджикистана": "Silk Road", "Всемирная история": "Ancient Rome",
    "Таджикский язык": "Flag of Tajikistan", "Таджикская литература": "Illuminated manuscript",
    "Русский язык": "Flag of Russia", "Английский язык": "Flag of the United Kingdom",
}


def _subject_slug(subject: str) -> str:
    import re
    # subject names are Cyrillic, which a plain ASCII-only regex strips down
    # to nothing (every subject collapsing to the same "default" slug/file
    # was a real bug here) — slug from the English lookup query instead,
    # which is already ASCII, so each subject keeps its own cache file.
    query = _SUBJECT_COVER_QUERIES.get(subject, subject)
    return re.sub(r'[^a-zA-Z0-9]+', '_', query).strip('_').lower() or "default"


async def get_subject_cover_image(subject: str) -> str | None:
    """Returns the cached cover photo path for `subject` (fetching and
    caching it the first time it's ever needed), or None if the subject
    isn't recognized or nothing could be found — the cover just falls back
    to a plain gradient in that case."""
    query = _SUBJECT_COVER_QUERIES.get(subject)
    if not query:
        return None
    slug = _subject_slug(subject)
    cached_path = os.path.join(_SUBJECT_COVERS_DIR, f"{slug}.jpg")
    if os.path.exists(cached_path):
        return f"/uploads/subject_covers/{slug}.jpg"
    result = await fetch_topic_image(query, "English")
    if not result:
        return None
    try:
        import shutil
        src = os.path.join(os.path.dirname(__file__), "..", result["path"].lstrip("/"))
        shutil.copyfile(src, cached_path)
        return f"/uploads/subject_covers/{slug}.jpg"
    except Exception as e:
        logger.warning(f"Failed to cache subject cover for '{subject}': {e}")
        return None


# ══ the two teaching illustrations a konspekt carries ═══════════════════
# A konspekt gets exactly two pictures from Wikimedia Commons, one per
# page, and both have to EXPLAIN the topic — a diagram, a construction, a
# graph, a labelled scientific figure. A pretty but generic photograph is
# not wanted here: a pupil learns nothing from a stock picture of a
# classroom blackboard next to a lesson on the Pythagorean theorem.
#
# So a candidate has to clear four gates, in this order:
#
#   1. it is a file whose title actually overlaps the query
#      (_title_matches_query — Commons search is fuzzy enough to answer
#      "Pythagorean theorem" with an unrelated village called Pythagoreio);
#   2. it reads as TEACHING material, not a snapshot — the title and its
#      categories carry a diagram/graph/figure word and no photograph
#      giveaway;
#   3. its licence is one of the free ones Commons documents in
#      extmetadata, so the teacher may legally print and hand it out;
#   4. it is big enough to print sharply on an A4 page.
#
# What comes back carries the author and licence with it, because a
# printed teaching sheet has to name them.

# Vector and lossless raster first: a diagram's value is its labels, and
# those are exactly what JPEG artefacts eat.
_LESSON_IMAGE_EXTS = (".svg", ".png", ".jpg", ".jpeg")

# The words that mark a file as made to explain something.
_TEACHING_WORDS = (
    "diagram", "diagramm", "scheme", "schema", "schematic", "chart", "graph",
    "plot", "figure", "illustration", "drawing", "construction", "proof",
    "theorem", "geometry", "geometric", "triangle", "circle", "polygon",
    "parabola", "function", "curve", "axis", "axes", "coordinate", "vector",
    "angle", "fraction", "equation", "formula", "cycle", "structure",
    "anatomy", "cross-section", "cutaway", "model", "map", "timeline",
    "infographic", "visualisation", "visualization", "animation", "svg",
)

# Commons hosts only freely-licensed work, but its extmetadata is what a
# teacher would have to cite, and a handful of files still carry usage
# restrictions (trademark, personality rights). Only licences that are
# unambiguously free to reprint in a school handout are accepted.
_FREE_LICENCE_MARKERS = (
    "cc0", "cc-zero", "public domain", "pd-", "cc by", "cc-by", "gfdl",
    "attribution", "share alike", "share-alike", "no restrictions",
)
_NON_FREE_MARKERS = ("fair use", "non-free", "nonfree", "copyrighted",
                     "with permission", "no license", "unknown")

# Below this a diagram either prints soft on A4 or has to be blown up past
# the point where its labels stay readable (see the brief's rule 11).
_MIN_SOURCE_WIDTH = 420
# What gets saved. Bigger than _MAX_DIM (900) on purpose: these are printed
# a whole page-column wide, where 900px shows its pixels.
_LESSON_MAX_DIM = 1500


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", str(value or "")).replace("&amp;", "&").strip()


def _extmeta(imageinfo: dict, key: str) -> str:
    return _strip_html(imageinfo.get("extmetadata", {}).get(key, {}).get("value", ""))


def _licence_is_free(imageinfo: dict) -> tuple[bool, str]:
    """(usable, licence name) from a file's extmetadata."""
    licence = _extmeta(imageinfo, "LicenseShortName") or _extmeta(imageinfo, "UsageTerms")
    restrictions = _extmeta(imageinfo, "Restrictions").lower()
    probe = f"{licence} {_extmeta(imageinfo, 'UsageTerms')}".lower()
    if not probe.strip():
        return False, ""
    if any(m in probe for m in _NON_FREE_MARKERS):
        return False, licence
    if "trademark" in restrictions:
        return False, licence
    return any(m in probe for m in _FREE_LICENCE_MARKERS), licence


# Commons keeps one file per language for a translated diagram, named with
# the language code ("Water cycle diagram-vi.svg" is the Vietnamese one).
# A diagram whose labels a pupil cannot read teaches nothing, and the
# lessons this app writes are in Russian, Tajik or English — so a
# file marked for some other language is pushed down the ranking, though
# not excluded outright (a labelled foreign diagram still beats none).
_LANG_CODES = (r"vi|fr|de|es|it|pt|pl|nl|tr|ar|fa|zh|ja|ko|hi|id|cs|sv|fi|no|da"
               r"|hu|ro|el|he|th|bn|ta|ml|sr|hr|sk|sl|lt|lv|et|ka|hy|ms|sw|cy|ga")
_FOREIGN_LANG_SUFFIX = re.compile(
    # At the end of the name ("Water cycle diagram-vi.svg") ...
    rf"[-_ ]({_LANG_CODES})\d*\.\w+$"
    # ... or as a dash-delimited token in the middle of it, which is the
    # other convention Commons uses ("World, administrative divisions -
    # hu - colored.svg" is the Hungarian one). Requiring a dash or
    # underscore on at least one side keeps ordinary words out: "Carte de
    # France" has "de" between plain spaces and is not a language tag.
    rf"|[-_]\s?({_LANG_CODES})\s?[-_.]",
    re.IGNORECASE,
)


async def _wikipedia_article_files(query: str) -> set[str]:
    """The File: titles actually used in the English Wikipedia article on
    `query` — the strongest relevance signal available.

    Commons full-text search ranks by title text, which answers "water
    cycle diagram" with every translated variant of it, including ones
    whose labels are in a language nobody in the class reads. A file the
    English article itself illustrates the topic with is, by definition,
    the picture an encyclopaedia chose to explain this exact subject —
    so those get a large bonus in the ranking below. Two requests, and a
    failure just means the bonus is not applied to anything."""
    try:
        # "water cycle diagram" has to be asked as "water cycle": the
        # descriptor words are what the file search needs, but Wikipedia
        # has no article called that, and searching with them matched
        # "Phase diagram" — which _search_title's own relevance guard
        # then (correctly) threw away, leaving no article at all.
        subject_words = [w for w in re.findall(r"[\w'-]+", query)
                         if w.lower() not in _GENERIC_IMAGE_WORDS]
        article_query = " ".join(subject_words) or query
        title = await _search_title("en", article_query)
        if not title:
            return set()
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "titles": title, "prop": "images",
            "imlimit": 60, "format": "json",
        })
        data = await _curl_json(url)
        if not data:
            return set()
        used = set()
        for page in (data.get("query") or {}).get("pages", {}).values():
            for image in page.get("images") or []:
                name = image.get("title", "")
                if name.lower().endswith(_LESSON_IMAGE_EXTS):
                    used.add(name)
        return used
    except Exception as e:
        logger.warning(f"Wikipedia article images lookup failed for {query[:60]!r}: {e}")
        return set()


# Commons' full-text search leans heavily on digitised 19th-century atlases
# and museum plates — they have long, keyword-rich descriptions, so they
# outrank modern diagrams on a plain topic query. A scanned 1887 plate is
# the wrong picture for a school lesson twice over: its geography is out of
# date, and its typography is unreadable at the size a konspekt prints it.
_ANTIQUE_MARKERS = (
    "lithograph", "chromolithograph", "engraving", "woodcut", "etching",
    "atlas", "plate", "(ia ", "internet archive", "scan", "facsimile",
    "publishing house", "antique", "vintage", "historical map", "old map",
)
_OLD_YEAR = re.compile(r"\b1[5-9]\d{2}\b")

# 19th-century "peoples of the world" plates are ethnographic race
# typologies — dated science, and racial caricature that has no place in a
# child's lesson sheet. Excluded outright rather than merely ranked down.
_ETHNOGRAPHIC_MARKERS = (
    "races of", "race of", "racial", "ethnograph", "peoples of the",
    "tribes", "natives of", "negro", "savage", "primitive peoples",
)

# Commons hosts a structure diagram for every named chemical compound,
# controlled or not — a "chemical structure" or "molecule diagram" query
# has no way to tell those apart on its own, and a novel psychoactive
# substance's diagram looks exactly as clean and textbook-like as
# caffeine's. These never belong in front of a schoolchild, whatever else
# they score on. Category/family names Commons actually files these
# under, not the informal street name of any one substance.
_DRUG_MARKERS = (
    "psychedelic", "psychoactive", "psychotropic", "hallucinogen",
    "phenethylamine", "tryptamine drug", "cathinone", "nbome",
    "novel psychoactive", "designer drug", "research chemical",
    "recreational drug", "narcotic", "controlled substance",
    "entactogen", "empathogen", "dissociative drug", "opioid drug",
)


# Words that turn a file into a DIFFERENT statement from the one asked
# for. "Proof of the inverse Pythagorean theorem" answers a search for
# "Pythagorean theorem proof diagram" and looks right, but it proves
# something else — and the sentence printed under it then tells the pupil
# to look for squares that are not in the picture.
_MEANING_SHIFTERS = ("inverse", "converse", "counterexample", "generalization",
                     "generalisation", "failure", "paradox", "fallacy", "wrong")


# Commons holds a university-level treatment of almost every school topic
# — a calculus proof of Pythagoras, a tensor derivation of a force law.
# Correct, on-topic, and useless to a 13-year-old, so they are ranked down
# for the grades that have not met the machinery they use.
_ADVANCED_MARKERS = ("differential", "calculus", "integral", "derivative",
                     "tensor", "quartic", "matrix", "eigen", "logarithmic",
                     "complex plane", "vector field", "topolog", "manifold")


def _too_advanced(title: str, description: str, grade: str | None) -> bool:
    """True when the file is pitched above the class it is meant for."""
    try:
        grade_num = int(re.sub(r"\D", "", str(grade or "")) or 0)
    except ValueError:
        grade_num = 0
    if not grade_num or grade_num > 9:
        return False
    text = f"{title} {description}".lower()
    return any(marker in text for marker in _ADVANCED_MARKERS)


def _shifts_meaning(query: str, title: str) -> bool:
    """True when the file's title carries a qualifier the query did not."""
    title_words = _significant_words(title)
    query_words = _significant_words(query)
    return any(w in title_words and w not in query_words for w in _MEANING_SHIFTERS)


# Living-organism anatomy diagrams score very well as generic "teaching
# diagram" candidates (SVG, numbered labels, a word match on "anatomy"/
# "structure") for almost ANY topic — confirmed live: a labelled snail
# anatomy diagram reached a Tajik-language 8th-grade konspekt about simple
# vs. compound SENTENCES, because the model asked for it on purpose as a
# metaphor ("compare a snail's complex internal structure to a complex
# sentence's structure") rather than by accident. A pupil reading a
# language konspekt sees a snail with no explanation of why, whatever
# caption gets written for it. Restricted to the one subject where an
# organism's internal anatomy actually IS the lesson.
_ANATOMY_MARKERS = (
    "anatomy", "internal organs", "digestive system", "circulatory system",
    "nervous system", "skeletal system", "musculature", "dissection",
)
_ANATOMY_SUBJECTS = ("Биология", "Biology", "Биология одам", "Human anatomy")


def _is_off_topic_for_subject(subject: str | None, title: str, categories: str,
                              description: str) -> bool:
    """True when the file belongs to a field the lesson's subject gives no
    reason to reach into, whatever score it earned as a generic diagram."""
    if not subject or subject in _ANATOMY_SUBJECTS:
        return False
    text = f"{title} {categories} {description}".lower()
    return any(marker in text for marker in _ANATOMY_MARKERS)


def _is_unsuitable_for_class(title: str, categories: str, description: str) -> bool:
    """True for material that must never reach a pupil's sheet whatever
    else it scores — currently the colonial-era ethnographic plates, one
    of which (an 1887 "Climates, Peoples, Industries" chromolithograph
    covered in racial-type portraits) reached a real geography konspekt;
    and controlled-substance structure diagrams, one of which (3C-DFM, a
    psychedelic phenethylamine — Commons category "3C (psychedelics)")
    reached a real 8th-grade chemistry konspekt on a generic "chemical
    compound structure" query."""
    text = f"{title} {categories} {description}".lower()
    if any(marker in text for marker in _ETHNOGRAPHIC_MARKERS):
        return True
    if any(marker in text for marker in _DRUG_MARKERS):
        return True
    return False


def _teaching_score(title: str, categories: str, description: str,
                    article_files: set[str] | None = None) -> int:
    """How much the file looks like something drawn to teach with."""
    text = f"{title} {categories} {description}".lower()
    score = sum(2 for w in _TEACHING_WORDS if w in text)
    if title.lower().endswith(".svg"):
        score += 3          # vector line art: the ideal case for print
    if any(marker in text for marker in _ANTIQUE_MARKERS):
        score -= 10
    if _OLD_YEAR.search(title):
        score -= 10
    if article_files and title in article_files:
        # A tie-breaker, not an override: being the picture the
        # encyclopaedia article uses is good evidence, but a +12 here
        # was enough to pull a climate-statistics bar chart out of the
        # "Water cycle" article ahead of an actual water-cycle diagram.
        score += 5
    if _looks_like_photo(title, categories):
        score -= 8
    if _FOREIGN_LANG_SUFFIX.search(title):
        score -= 6
    return score


# Commons marks a translated diagram in its own file name: "Chloroplast
# diagram bs plain.svg" is the Bosnian one, "Photosynthese-de.svg" the
# German. The markers are what make it possible to keep a Russian lesson
# from being handed a diagram labelled in Serbo-Croatian — which is what
# happened live, on a 7th-grade biology lecture about photosynthesis.
_LANG_MARKERS = {
    "ru": "Русский", "rus": "Русский", "russian": "Русский", "russisch": "Русский",
    "tg": "Таджикский", "tajik": "Таджикский",
    "en": "English", "eng": "English", "english": "English",
    "bs": None, "hr": None, "sr": None, "de": None, "fr": None, "es": None,
    "it": None, "nl": None, "pl": None, "pt": None, "cs": None, "sk": None,
    "sv": None, "no": None, "da": None, "fi": None, "hu": None, "ro": None,
    "tr": None, "ar": None, "fa": None, "he": None, "zh": None, "ja": None,
    "ko": None, "hi": None, "id": None, "vi": None, "uk": None, "bg": None,
    "el": None, "ca": None, "eu": None, "lt": None, "lv": None, "et": None,
    "sl": None, "mk": None, "sq": None,
    # The rest of ISO 639-1 that Commons actually uses on file names. "af"
    # was missing and an Afrikaans reaction diagram ("H+ heg homself aan
    # OH-") went into a Russian chemistry lecture.
    "af": None, "am": None, "az": None, "be": None, "bn": None, "br": None,
    "ceb": None, "cy": None, "eo": None, "fo": None, "ga": None, "gl": None,
    "hy": None, "is": None, "ka": None, "kk": None, "km": None, "ky": None,
    "la": None, "lb": None, "mn": None, "ms": None, "mt": None, "my": None,
    "ne": None, "nn": None, "oc": None, "pa": None, "ps": None, "si": None,
    "sw": None, "ta": None, "te": None, "th": None, "tt": None, "ur": None,
    "yi": None, "zu": None,
    "bosnian": None, "croatian": None,
    "serbian": None, "german": None, "french": None, "spanish": None,
    "italian": None, "dutch": None, "polish": None, "czech": None,
    "swedish": None, "turkish": None, "chinese": None, "japanese": None,
    "ukrainian": None, "deutsch": None, "espanol": None, "francais": None,
}
_LANG_TOKEN = re.compile(r"[A-Za-z]+")


def _label_language(title: str) -> str | None:
    """The language a Commons file says its labels are in, or None.

    Only a marker standing on its own counts: "de" as a word is the
    German edition, but the "de" inside "model" is not."""
    stem = str(title or "").rsplit(".", 1)[0]
    stem = re.sub(r"^File:", "", stem, flags=re.I)
    tokens = _LANG_TOKEN.findall(stem.replace("_", " ").replace("-", " "))
    for pos, token in enumerate(tokens):
        low = token.lower()
        if low not in _LANG_MARKERS:
            continue
        # A full language NAME ("Bosnian") counts wherever it appears. A
        # two- or three-letter CODE only counts in the tail of the name,
        # where Commons puts it — otherwise "In" in "Insects" and "de" in
        # "Modelo de..." would read as language markers.
        if len(low) > 3 or pos >= max(1, len(tokens) - 3):
            return low
    return None


def _label_language_penalty(title: str, language: str | None) -> float:
    """How much to dock a file for its labels being in a language the
    class does not read — a SOFT signal now, not a hard filter.

    This used to `continue` the candidate out of scoring entirely the
    moment its file name carried any marker other than the target
    language or English. Measured live on real lesson topics ("Материки",
    "Строение клетки"): Commons' modern vector diagrams are very often
    translated-and-forked per language (a German biology diagram, a
    Bosnian one, a Vietnamese one, all clones of the same original with
    only the labels changed), and the hard block meant EVERY fork except
    a Russian/English one was invisible to scoring — on several real
    queries that left nothing at all. A diagram whose shapes and layout
    are exactly right is still the best available teaching image even
    with labels a Tajik or Russian class cannot read directly; it is
    worse than a matching-language file, not worthless. Callers that want
    to relabel it themselves (see image_builder's own PPTX-side caption
    overlays) can still use it.

    Unlabelled files (marker is None — most photos, and diagrams whose
    file name carries no language code at all) pay nothing: there is no
    evidence they are in the wrong language, so there is nothing to
    penalise."""
    marker = _label_language(title)
    if marker is None:
        return 0.0
    named = _LANG_MARKERS.get(marker)
    if named in (str(language or "Русский"), "English"):
        return 0.0
    # A recognised-but-wrong language (French, German, ...) costs less
    # than an unrecognised script (Arabic, Chinese, Thai marker names):
    # the former is still visually legible as a diagram even if a pupil
    # can't read the caption, the latter risks a non-Latin label baked
    # into the image itself, which reads as noise on a slide.
    return 3.0 if named is not None else 6.0


async def _commons_lesson_candidates(query: str, limit: int = 18, grade: str | None = None,
                                     language: str | None = None,
                                     subject: str | None = None) -> list[dict]:
    """Files on Commons that could illustrate `query`, best first.

    Searched in the File namespace directly rather than through a
    Wikipedia article, for the reason _commons_diagram_candidates gives:
    an article's lead image is its photograph, while the diagram that
    explains the subject is indexed on Commons under its own title. The
    article's own file list is still fetched, but as a RANKING signal
    (see _wikipedia_article_files) rather than as the source."""
    seen: set[str] = set()
    scored: list[tuple[float, dict]] = []
    article_files = await _wikipedia_article_files(query)
    # The explicit "diagram" pass first: it is what the brief asks for, and
    # Commons ranks a bare topic query towards photographs. A query that
    # already says "diagram" (the model is told to write them that way)
    # does not get the word twice — that was a wasted request against a
    # rate-limited API, asking for "... diagram diagram".
    already_visual = any(w in query.lower() for w in
                         ("diagram", "scheme", "chart", "graph", "figure", "illustration"))
    passes = [query] if already_visual else [f"{query} diagram", query]
    # Then the SAME query with words peeled off. Commons search ANDs its
    # terms, so a five-word phrase only matches files whose description
    # happens to contain all five — which, for "World continents map
    # labeled diagram", meant nothing but digitised 18th-century atlases
    # (their long catalogue text hits every word) while the clean modern
    # "7 continents map.svg" matched none of it. Dropping to the two or
    # three words that carry the subject is what surfaces the teaching
    # diagrams; confirmed live on exactly that query.
    subject_words = [w for w in re.findall(r"[\w'-]+", query)
                     if w.lower() not in _GENERIC_IMAGE_WORDS]
    # Only ONE peeled-down variant, not two (3-word AND 2-word). Every
    # entry in `passes` is a full Commons round-trip against an API that
    # rate-limits this app's IP (see _pace_request) — up to 4 requests for
    # ONE query was the actual volume behind the "8 slides x 4 queries x
    # several HTTP requests" problem, not the query count alone. The
    # 3-word version already does the peeling's real job (dropping filler
    # so Commons' AND-search stops requiring every word to hit); the
    # 2-word fallback recovered few enough candidates in practice to not
    # be worth its own request.
    shorter = " ".join(subject_words[:3])
    if shorter and shorter.lower() not in {x.lower() for x in passes}:
        passes.append(shorter)
    passes = passes[:2]

    for search_q in passes:
        # Enough good candidates already — the second pass exists to
        # rescue a query that found nothing, not to dilute one that
        # worked, and every extra pass is another rate-limited request.
        if len(scored) >= 2:
            break
        # ONE request per phrase, not one per hit: generator=search feeds
        # the search results straight into prop=imageinfo, so the URL,
        # size and licence of all 18 candidates come back together. The
        # earlier shape (a search call, then an imageinfo call per title)
        # meant ~20 requests per phrase, which Wikimedia answered with
        # HTTP 429 halfway through — the konspekt then got one picture
        # instead of two, or none at all.
        # "filetype:bitmap|drawing" is doing real work: the File namespace
        # also holds scanned PDFs and DJVU books, and a plain topic query
        # came back mostly those ("FM 3-25.26 Map Reading.djvu",
        # "Computer Gaming World issue 2.5.pdf") — none of them an image
        # at all, so a konspekt on continents ended up with no picture.
        url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "generator": "search",
            "gsrsearch": f"{search_q} filetype:bitmap|drawing",
            "gsrnamespace": 6, "gsrlimit": limit, "prop": "imageinfo",
            "iiprop": "url|size|extmetadata", "iiurlwidth": _LESSON_MAX_DIM,
            "format": "json",
        })
        data = await _curl_json(url)
        if not data:
            continue
        pages = (data.get("query") or {}).get("pages") or {}
        # "index" is the generator's own relevance ordering; dict order
        # from the JSON is not it.
        for page in sorted(pages.values(), key=lambda p: p.get("index", 999)):
            title = page.get("title", "")
            rank = int(page.get("index", 99))
            if title in seen or not title.lower().endswith(_LESSON_IMAGE_EXTS):
                continue
            seen.add(title)
            if not _title_matches_query(query, title):
                continue
            imageinfo = (page.get("imageinfo") or [None])[0]
            if not imageinfo:
                continue
            free, licence = _licence_is_free(imageinfo)
            if not free:
                continue
            # An SVG has no meaningful pixel width of its own — it is
            # rendered to whatever size is asked for, so it always
            # prints sharply and the size gate does not apply to it.
            is_vector = title.lower().endswith(".svg")
            if not is_vector and int(imageinfo.get("width") or 0) < _MIN_SOURCE_WIDTH:
                continue
            categories = _extmeta(imageinfo, "Categories")
            description = _extmeta(imageinfo, "ImageDescription")[:400]
            if _is_unsuitable_for_class(title, categories, description):
                continue
            if _is_off_topic_for_subject(subject, title, categories, description):
                continue
            if _shifts_meaning(query, title):
                continue
            if _too_advanced(title, description, grade):
                continue
            lang_penalty = _label_language_penalty(title, language)
            teaching = _teaching_score(title, categories, description, article_files)
            if teaching <= 0:
                continue        # a snapshot, or nothing to learn from
            # Search rank breaks ties between teaching-worthy files; it
            # used to be subtracted outright, which meant a good diagram
            # sitting at rank 10 needed a score above 10 to survive at
            # all. That is how a konspekt on continents ended up with
            # nothing: every real map was ranked below the noise.
            score = teaching - rank * 0.4 - lang_penalty
            if lang_penalty:
                logger.info(f"Commons: {title!r} labels not in {language} (-{lang_penalty})")
            scored.append((score, {
                "title": title,
                "url": imageinfo.get("thumburl") or imageinfo.get("url"),
                "descriptionurl": imageinfo.get("descriptionurl", ""),
                "licence": licence,
                "author": _extmeta(imageinfo, "Artist")[:120],
                "description": description,
            }))

    # The article's file list is deliberately NOT used as a source of
    # candidates, only as the ranking bonus applied above. Tried both
    # ways: an article carries plenty of peripheral figures beside its
    # lead diagram — the "Water cycle" article also holds climate-trend
    # bar charts and a rock-cycle drawing — and pulling those in gave a
    # geography lesson on the water cycle an EPA precipitation-statistics
    # chart. The word-overlap gate does not separate them, because they
    # do share the topic's words. Commons' own search, which ranks on the
    # whole file description, picks the teaching diagram reliably.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored]


async def _openverse_lesson_candidates(query: str, limit: int = 10, grade: str | None = None,
                                       subject: str | None = None) -> list[dict]:
    """Fallback source for fetch_lesson_images, tried only when Commons'
    own File-namespace search (_commons_lesson_candidates) comes back
    empty for every query. Confirmed live: MANY lessons were finishing
    with zero illustrations even after that widened Commons search —
    either the topic genuinely has no Commons file, or Wikimedia's rate
    limit (see _pace_request/_note_response) was already tripped from
    other requests in the same batch and every Commons attempt for this
    lesson ate a 429 in a row.

    Openverse (openverse.org, a Creative-Commons-run search engine, not
    a Wikimedia project) indexes openly-licensed images from Commons AND
    Flickr, the Met, Smithsonian, Europeana, the British Library and
    others under one search — so a topic Commons' own title-based search
    missed, or a request that only failed because of Commons' OWN rate
    limit, often still turns up something here, against a completely
    separate API with its own separate limit.

    license_type=commercial,modification only — Dastyor resells the
    materials these images end up printed in, and a teacher crops/resizes
    them into slides, so a non-commercial or no-derivatives licence
    (which Openverse would otherwise happily return) would not actually
    be usable here.

    No API key: openverse.org's anonymous tier works but is capped
    harder than an authenticated one would be — acceptable BECAUSE this
    only runs as a last resort, never on every lesson.

    Tried at up to two phrasings, same reason as Commons' own word-peeling
    (_commons_lesson_candidates): Openverse ANDs every word in `q`, so a
    descriptive multi-word phrase the model wrote for Commons — built to
    survive an AND-search THERE — routinely matches nothing here even
    when a good picture exists. Confirmed live: 'Rudaki poet portrait
    manuscript' → 0 results, 'Rudaki portrait' → 0, but 'Rudaki' alone
    → 240, including 'Statue of Rudaki' and 'Rudaki profile'. The peeled
    phrase is only tried when the full one comes back empty, so a query
    that already works costs one request, same as before.

    Peeling to the first two remaining words after dropping
    _GENERIC_IMAGE_WORDS is still naive on its own — first attempt at
    this kept "Tajik national" for 'Tajik national ornament pattern' and
    dropped the actual subject ("ornament pattern"), and confirmed live
    that phrase alone matches Tajik ARMY photos on Openverse (any title
    sharing just "Tajik"+"national" passes the normal one-word overlap
    check in _title_matches_query). _LOW_SPECIFICITY_QUALIFIERS below
    additionally drops words like "national"/"traditional" for THIS
    peel specifically — not from the shared _GENERIC_IMAGE_WORDS, which
    Commons' own matching also reads and has already been tuned against
    real Commons results; a word that is a problem for a peeled 2-word
    Openverse search is not necessarily one for Commons' full-phrase
    search. (A stricter alternative — requiring the peeled-phrase hit to
    also carry a word the peel DROPPED — was tried and reverted: for
    'Archimedes force buoyancy diagram' it rejected "Archimedes' thrust"
    for not literally containing "buoyancy", and for 'Rudaki poet
    portrait manuscript' it rejected "Rudaki the Persian Poet" for not
    containing "manuscript" — both genuinely good matches lost to a
    check with no actual sense of synonymy.)"""
    _LOW_SPECIFICITY_QUALIFIERS = {
        "national", "traditional", "local", "regional", "modern",
        "ancient", "historical", "cultural", "folk", "official",
    }
    subject_words = [w for w in re.findall(r"[\w'-]+", query)
                     if w.lower() not in _GENERIC_IMAGE_WORDS
                     and w.lower() not in _LOW_SPECIFICITY_QUALIFIERS]
    peeled = " ".join(subject_words[:2])
    passes = [query] if not peeled or peeled.lower() == query.lower() else [query, peeled]

    results_raw: list[dict] = []
    for search_q in passes:
        try:
            url = "https://api.openverse.org/v1/images/?" + urllib.parse.urlencode({
                "q": search_q, "license_type": "commercial,modification",
                "mature": "false", "page_size": limit,
            })
            data = await _curl_json(url)
        except Exception as e:
            logger.warning(f"Openverse search failed for {search_q[:60]!r}: {e}")
            continue
        results_raw = (data or {}).get("results") or []
        if results_raw:
            break
    if not results_raw:
        return []
    scored: list[tuple[float, dict]] = []
    for i, r in enumerate(results_raw):
        title = str(r.get("title") or "").strip()
        # PIL (_save_lesson_image) cannot open an .svg directly — it needs
        # the rasterised PNG Openverse's OWN thumbnail proxy renders on
        # request. Confirmed live: that proxy occasionally 424s on a
        # specific source SVG even though the SVG itself downloads fine,
        # so this still falls back to the raw url for anything that isn't
        # an SVG to begin with (a real photo from Flickr/a museum, say) —
        # those are already a raster format and gain nothing from being
        # routed through the same proxy, just another dependency to fail.
        raw_url = str(r.get("url") or "")
        image_url = r.get("thumbnail") if raw_url.lower().endswith(".svg") else (raw_url or r.get("thumbnail"))
        if not title or not image_url:
            continue
        width = int(r.get("width") or 0)
        if width and width < _MIN_SOURCE_WIDTH:
            continue
        description = str(r.get("description") or title)[:400]
        if not _title_matches_query(query, title):
            continue
        if _is_unsuitable_for_class(title, "", description):
            continue
        if _is_off_topic_for_subject(subject, title, "", description):
            continue
        if _shifts_meaning(query, title):
            continue
        if _too_advanced(title, description, grade):
            continue
        licence = f"{str(r.get('license') or '').upper()} {r.get('license_version') or ''}".strip()
        provider = str(r.get("provider") or r.get("source") or "").strip()
        source_label = f"Openverse · {provider}" if provider else "Openverse"
        # Only Openverse's own list-order ranking to break ties on — no
        # per-file teaching-content score the way Commons candidates get
        # (that score reads Commons' structured Categories/description
        # extmetadata, which Openverse results don't carry the same way).
        scored.append((-i, {
            "title": title,
            "url": image_url,
            "descriptionurl": r.get("foreign_landing_url") or r.get("related_url") or r.get("detail_url") or "",
            "licence": licence,
            "author": str(r.get("creator") or "")[:120],
            "description": description,
            "source_label": source_label,
        }))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored]


def _clean_file_title(title: str) -> str:
    out = re.sub(r"^File:", "", title, flags=re.IGNORECASE)
    out = re.sub(r"\.\w+$", "", out)
    out = out.replace("_", " ").strip()
    return out


def _save_lesson_image(raw: bytes) -> tuple[str, int, int] | None:
    """Writes the download to uploads/images/ and returns (path, w, h).

    Flattened onto white rather than kept transparent: these are printed
    inside a light figure card, and a transparent PNG placed on a coloured
    panel comes out with black behind the line art in some PDF viewers."""
    try:
        img = Image.open(io.BytesIO(raw))
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            flat = Image.new("RGB", img.size, (255, 255, 255))
            flat.paste(img, mask=img.split()[-1])
            img = flat
        else:
            img = img.convert("RGB")
        img.thumbnail((_LESSON_MAX_DIM, _LESSON_MAX_DIM), Image.LANCZOS)
        filename = f"{uuid.uuid4().hex}.png"
        img.save(os.path.join(_IMAGES_DIR, filename), "PNG")
        return f"/uploads/images/{filename}", img.width, img.height
    except Exception as e:
        logger.warning(f"Lesson image save failed: {e}")
        return None


async def _take_lesson_candidate(candidate: dict, query: str, source_label: str = "Wikimedia Commons") -> dict | None:
    """One candidate downloaded, saved and described, or None if it turned
    out to be unusable (unreachable, unreadable, or a banner/sliver shape
    no textbook figure has) — in which case the caller simply tries the
    next file Commons offered.

    `source_label` names where the file actually came from in the printed
    credit line — "Wikimedia Commons" for a _commons_lesson_candidates
    result, but a candidate from _openverse_lesson_candidates (see
    fetch_lesson_images' fallback) carries its own real provider name
    (e.g. "Openverse · Flickr") instead. Crediting every fallback image as
    Commons regardless of where it actually came from would be a wrong
    attribution, not just a cosmetic slip — the licences these run under
    require naming the real source."""
    if not candidate.get("url"):
        return None
    raw = await _curl_bytes(candidate["url"], timeout=10.0)
    if not raw:
        return None
    saved = _save_lesson_image(raw)
    if not saved:
        return None
    path, width, height = saved
    # A picture wider than about three times its height (a banner) or
    # taller than twice its width prints as a sliver or eats the page;
    # neither reads as a textbook figure.
    if width <= 0 or height <= 0 or not (0.35 <= width / height <= 3.2):
        return None
    credit = " · ".join(p for p in (source_label,
                                    candidate.get("author", ""),
                                    candidate.get("licence", "")) if p)
    return {
        "path": path,
        # The Commons file NAME is not a caption. "Chloroplast diagram bs
        # plain" printed as the figure's heading in a Russian lecture is
        # both meaningless to the class and a giveaway that nobody looked
        # at the output. ai_service writes the real caption from what the
        # picture shows (_rewrite_image_explanations); this stays as the
        # last-resort fallback, and the credit line below still carries
        # the attribution the licence requires.
        "caption": "",
        "file_title": _clean_file_title(candidate["title"]),
        "credit": credit,
        "source": candidate.get("descriptionurl", ""),
        # Commons' own description of the file. Carried through so
        # ai_service can write the pupil's reading instruction from what
        # the picture ACTUALLY shows rather than from what was searched
        # for — see _rewrite_image_explanations.
        "description": str(candidate.get("description") or "")[:400],
        "width": width,
        "height": height,
        "query": query,
    }


async def fetch_lesson_images(queries: list[str], count: int = 2, grade: str | None = None,
                              language: str | None = None, subject: str | None = None) -> list[dict]:
    """`count` teaching illustrations from Wikimedia Commons, one per
    query, never the same file twice.

    Each result is {"path", "caption", "credit", "source", "width",
    "height"} — the credit line is not optional decoration: the licences
    Commons uses require the author and the licence to travel with the
    picture onto the printed sheet.

    A query that finds nothing usable does NOT cost the konspekt a
    picture: the leftover candidates the other queries turned up are used
    to fill the gap, and only if those run out too does the konspekt go
    out with fewer than `count`. That fallback is the difference between
    "two illustrations per konspekt" and "two when the model's second
    search phrase happened to match a Commons file title" — measured
    live, the second phrase misses often enough to matter.

    Fail-soft like every other illustration lookup in this app: a network
    failure yields fewer pictures, never a failed konspekt."""
    results: list[dict] = []
    used_titles: set[str] = set()
    leftovers: list[tuple[str, dict]] = []

    for query in queries:
        # Once `count` is satisfied, STOP — searching the remaining
        # queries anyway (and only using their results as unused spares)
        # used to cost a full Commons round-trip (1 Wikipedia call + up to
        # 4 word-peeled Commons searches, see _commons_lesson_candidates)
        # for candidates that were thrown away. On a real deck that meant
        # every slide's SECOND query fired even when the first one had
        # already found its picture — half the request volume against an
        # API that rate-limits this app's IP, for zero benefit. Measured
        # live: cutting this is what took a real "Материки" deck from 0
        # images in 4 slides to images actually arriving.
        if len(results) >= count:
            break
        query = str(query or "").strip()
        if not query:
            continue
        try:
            candidates = await _commons_lesson_candidates(query, grade=grade,
                                                          language=language, subject=subject)
        except Exception as e:
            logger.warning(f"Commons lesson search failed for {query[:60]!r}: {e}")
            continue
        taken = False
        for i, candidate in enumerate(candidates):
            if candidate["title"] in used_titles:
                continue
            if taken:
                leftovers.append((query, candidate))
                continue
            got = await _take_lesson_candidate(candidate, query)
            if got:
                results.append(got)
                used_titles.add(candidate["title"])
                taken = True

    # Fill-up: a query that yielded nothing gets its slot from another
    # query's runners-up rather than leaving the konspekt short.
    for query, candidate in leftovers:
        if len(results) >= count:
            break
        if candidate["title"] in used_titles:
            continue
        got = await _take_lesson_candidate(candidate, query)
        if got:
            results.append(got)
            used_titles.add(candidate["title"])

    # Openverse fallback: Commons (direct search + leftover fill-up above)
    # still hasn't filled every slot. Only reached when Commons genuinely
    # came up short — a lesson that already got its `count` pictures from
    # Commons never touches this, so this fallback's own (harder) rate
    # limit is spent only on the lessons that actually need it.
    if len(results) < count:
        for query in queries:
            if len(results) >= count:
                break
            query = str(query or "").strip()
            if not query:
                continue
            try:
                candidates = await _openverse_lesson_candidates(query, grade=grade, subject=subject)
            except Exception as e:
                logger.warning(f"Openverse lesson search failed for {query[:60]!r}: {e}")
                continue
            for candidate in candidates:
                if len(results) >= count:
                    break
                if candidate["title"] in used_titles:
                    continue
                got = await _take_lesson_candidate(candidate, query, source_label=candidate["source_label"])
                if got:
                    results.append(got)
                    used_titles.add(candidate["title"])
                    break  # one picture per query is enough, same as the Commons pass

    if len(results) < count:
        logger.info(f"Lesson images: got {len(results)} of {count} for {queries!r}")
    return results[:count]
