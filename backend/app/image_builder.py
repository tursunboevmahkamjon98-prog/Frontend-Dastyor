
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

_WIKI_LANGS = {
    "Русский": "ru", "Таджикский": "tg", "English": "en", "Английский": "en",
}

_MAX_DIM = 900

_last_request_at = [0.0]
_pacer_lock = asyncio.Lock()
_MIN_REQUEST_INTERVAL = 0.6

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
    loop = asyncio.get_event_loop()
    if status == "429":
        _consecutive_429[0] += 1
        penalty = min(12.0, 1.5 * _consecutive_429[0])
        _backoff_until[0] = max(_backoff_until[0], loop.time() + penalty)
    elif status == "200":
        _consecutive_429[0] = 0


async def _curl_bytes(url: str, timeout: float = 10.0, _retries: int = 1) -> bytes | None:
    
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
                    return None
                logger.warning(f"Wikipedia HTTP {status} for {url} (attempt {attempt + 1}/{_retries + 1})")
                if status == "429":
                    continue
            else:
                logger.warning(f"curl failed ({returncode}) for {url}: {stderr[:200]!r}")
        except Exception as e:
            logger.warning(f"curl subprocess failed for {url}: {type(e).__name__}: {e!r}")
        if attempt < _retries:
            await asyncio.sleep(delay)
            delay *= 2
    return None


def _run_curl_sync(url: str, timeout: float) -> tuple[bytes, bytes, int]:
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


_GENERIC_IMAGE_WORDS = {
    "portrait", "photo", "photograph", "picture", "image", "statue", "monument",
    "map", "diagram", "illustration", "drawing", "painting", "model", "scene",
    "view", "closeup", "logo", "flag", "symbol", "icon", "sculpture",
    "anatomy", "internal", "structure", "structural",
    "simple", "complex", "basic", "general", "system",
}


def _significant_words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ]{3,}", text)}


def _title_matches_query(query: str, title: str) -> bool:
    q_words = _significant_words(query) - _GENERIC_IMAGE_WORDS
    if q_words:
        return bool(q_words & _significant_words(title))
    q_norm = re.sub(r"\s+", "", query.lower())
    if len(q_norm) < 2:
        return False
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
    if not query or not query.strip():
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



_rembg_session = None


def _rembg_remove_sync(data: bytes) -> bytes:
    global _rembg_session
    from rembg import remove, new_session
    if _rembg_session is None:
        _rembg_session = new_session("u2net")
    return remove(data, session=_rembg_session)


def _trim_transparent(img: Image.Image, pad: int = 14) -> Image.Image:
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    l, t = max(l - pad, 0), max(t - pad, 0)
    r, b = min(r + pad, img.width), min(b + pad, img.height)
    return img.crop((l, t, r, b))


async def _cutout_background(raw: bytes) -> bytes | None:
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

_PHOTO_GIVEAWAY_WORDS = (
    "photo", "photograph", "dissection", "dissected", "specimen", "cadaver",
    "postmortem", "post-mortem", "necropsy", "autopsy", "surgical", "graft",
    "hibernating", "taxidermy",
)


def _looks_like_photo(title: str, categories: str) -> bool:
    text = f"{title} {categories}".lower()
    return any(w in text for w in _PHOTO_GIVEAWAY_WORDS)


async def _commons_diagram_candidates(query: str) -> list[tuple[str, str]]:
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
    lo, _hi = img.getchannel("A").getextrema()
    return lo < 250


def _background_is_clean(img: Image.Image, tolerance: int = 32, noise_threshold: float = 0.02) -> bool:
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
        candidates = await _commons_diagram_candidates(query)
        random.shuffle(candidates)
        fallback: tuple[Image.Image, str] | None = None
        for image_url, title in candidates:
            raw = await _curl_bytes(image_url)
            if not raw:
                continue
            try:
                img = Image.open(io.BytesIO(raw)).convert("RGBA")
                if _has_real_transparency(img):
                    pass
                elif _background_is_clean(img):
                    img = _chroma_key_background(img)
                else:
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
    results = []
    for item in items:
        topic = (item or {}).get("topic", "")
        section = (item or {}).get("section", "")
        hit = await fetch_topic_image(topic, language)
        if hit:
            hit["section"] = section
            results.append(hit)
    return results



_SUBJECT_COVERS_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "subject_covers")
os.makedirs(_SUBJECT_COVERS_DIR, exist_ok=True)

_SUBJECT_COVER_QUERIES = {
    "Математика": "Abacus", "Алгебра": "Abacus", "Геометрия": "Compass and straightedge",
    "Информатика": "Laptop computer", "Физика": "Isaac Newton", "Химия": "Laboratory glassware",
    "Биология": "Biology", "География": "Geography",
    "История Таджикистана": "Silk Road", "Всемирная история": "Ancient Rome",
    "Таджикский язык": "Flag of Tajikistan", "Таджикская литература": "Illuminated manuscript",
    "Русский язык": "Flag of Russia", "Английский язык": "Flag of the United Kingdom",
}


def _subject_slug(subject: str) -> str:
    import re
    query = _SUBJECT_COVER_QUERIES.get(subject, subject)
    return re.sub(r'[^a-zA-Z0-9]+', '_', query).strip('_').lower() or "default"


async def get_subject_cover_image(subject: str) -> str | None:
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



_LESSON_IMAGE_EXTS = (".svg", ".png", ".jpg", ".jpeg")

_TEACHING_WORDS = (
    "diagram", "diagramm", "scheme", "schema", "schematic", "chart", "graph",
    "plot", "figure", "illustration", "drawing", "construction", "proof",
    "theorem", "geometry", "geometric", "triangle", "circle", "polygon",
    "parabola", "function", "curve", "axis", "axes", "coordinate", "vector",
    "angle", "fraction", "equation", "formula", "cycle", "structure",
    "anatomy", "cross-section", "cutaway", "model", "map", "timeline",
    "infographic", "visualisation", "visualization", "animation", "svg",
)

_FREE_LICENCE_MARKERS = (
    "cc0", "cc-zero", "public domain", "pd-", "cc by", "cc-by", "gfdl",
    "attribution", "share alike", "share-alike", "no restrictions",
)
_NON_FREE_MARKERS = ("fair use", "non-free", "nonfree", "copyrighted",
                     "with permission", "no license", "unknown")

_MIN_SOURCE_WIDTH = 420
_LESSON_MAX_DIM = 1500


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", str(value or "")).replace("&amp;", "&").strip()


def _extmeta(imageinfo: dict, key: str) -> str:
    return _strip_html(imageinfo.get("extmetadata", {}).get(key, {}).get("value", ""))


def _licence_is_free(imageinfo: dict) -> tuple[bool, str]:
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


_LANG_CODES = (r"vi|fr|de|es|it|pt|pl|nl|tr|ar|fa|zh|ja|ko|hi|id|cs|sv|fi|no|da"
               r"|hu|ro|el|he|th|bn|ta|ml|sr|hr|sk|sl|lt|lv|et|ka|hy|ms|sw|cy|ga")
_FOREIGN_LANG_SUFFIX = re.compile(
    rf"[-_ ]({_LANG_CODES})\d*\.\w+$"
    rf"|[-_]\s?({_LANG_CODES})\s?[-_.]",
    re.IGNORECASE,
)


async def _wikipedia_article_files(query: str) -> set[str]:
    try:
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


_ANTIQUE_MARKERS = (
    "lithograph", "chromolithograph", "engraving", "woodcut", "etching",
    "atlas", "plate", "(ia ", "internet archive", "scan", "facsimile",
    "publishing house", "antique", "vintage", "historical map", "old map",
)
_OLD_YEAR = re.compile(r"\b1[5-9]\d{2}\b")

_ETHNOGRAPHIC_MARKERS = (
    "races of", "race of", "racial", "ethnograph", "peoples of the",
    "tribes", "natives of", "negro", "savage", "primitive peoples",
)

_DRUG_MARKERS = (
    "psychedelic", "psychoactive", "psychotropic", "hallucinogen",
    "phenethylamine", "tryptamine drug", "cathinone", "nbome",
    "novel psychoactive", "designer drug", "research chemical",
    "recreational drug", "narcotic", "controlled substance",
    "entactogen", "empathogen", "dissociative drug", "opioid drug",
)


_MEANING_SHIFTERS = ("inverse", "converse", "counterexample", "generalization",
                     "generalisation", "failure", "paradox", "fallacy", "wrong")


_ADVANCED_MARKERS = ("differential", "calculus", "integral", "derivative",
                     "tensor", "quartic", "matrix", "eigen", "logarithmic",
                     "complex plane", "vector field", "topolog", "manifold")


def _too_advanced(title: str, description: str, grade: str | None) -> bool:
    try:
        grade_num = int(re.sub(r"\D", "", str(grade or "")) or 0)
    except ValueError:
        grade_num = 0
    if not grade_num or grade_num > 9:
        return False
    text = f"{title} {description}".lower()
    return any(marker in text for marker in _ADVANCED_MARKERS)


def _shifts_meaning(query: str, title: str) -> bool:
    title_words = _significant_words(title)
    query_words = _significant_words(query)
    return any(w in title_words and w not in query_words for w in _MEANING_SHIFTERS)


_ANATOMY_MARKERS = (
    "anatomy", "internal organs", "digestive system", "circulatory system",
    "nervous system", "skeletal system", "musculature", "dissection",
)
_ANATOMY_SUBJECTS = ("Биология", "Biology", "Биология одам", "Human anatomy")


def _is_off_topic_for_subject(subject: str | None, title: str, categories: str,
                              description: str) -> bool:
    if not subject or subject in _ANATOMY_SUBJECTS:
        return False
    text = f"{title} {categories} {description}".lower()
    return any(marker in text for marker in _ANATOMY_MARKERS)


def _is_unsuitable_for_class(title: str, categories: str, description: str) -> bool:
    text = f"{title} {categories} {description}".lower()
    if any(marker in text for marker in _ETHNOGRAPHIC_MARKERS):
        return True
    if any(marker in text for marker in _DRUG_MARKERS):
        return True
    return False


def _teaching_score(title: str, categories: str, description: str,
                    article_files: set[str] | None = None) -> int:
    text = f"{title} {categories} {description}".lower()
    score = sum(2 for w in _TEACHING_WORDS if w in text)
    if title.lower().endswith(".svg"):
        score += 3
    if any(marker in text for marker in _ANTIQUE_MARKERS):
        score -= 10
    if _OLD_YEAR.search(title):
        score -= 10
    if article_files and title in article_files:
        score += 5
    if _looks_like_photo(title, categories):
        score -= 8
    if _FOREIGN_LANG_SUFFIX.search(title):
        score -= 6
    return score


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
    stem = str(title or "").rsplit(".", 1)[0]
    stem = re.sub(r"^File:", "", stem, flags=re.I)
    tokens = _LANG_TOKEN.findall(stem.replace("_", " ").replace("-", " "))
    for pos, token in enumerate(tokens):
        low = token.lower()
        if low not in _LANG_MARKERS:
            continue
        if len(low) > 3 or pos >= max(1, len(tokens) - 3):
            return low
    return None


def _label_language_penalty(title: str, language: str | None) -> float:
    marker = _label_language(title)
    if marker is None:
        return 0.0
    named = _LANG_MARKERS.get(marker)
    if named in (str(language or "Русский"), "English"):
        return 0.0
    return 3.0 if named is not None else 6.0


async def _commons_lesson_candidates(query: str, limit: int = 18, grade: str | None = None,
                                     language: str | None = None,
                                     subject: str | None = None) -> list[dict]:
    seen: set[str] = set()
    scored: list[tuple[float, dict]] = []
    article_files = await _wikipedia_article_files(query)
    already_visual = any(w in query.lower() for w in
                         ("diagram", "scheme", "chart", "graph", "figure", "illustration"))
    passes = [query] if already_visual else [f"{query} diagram", query]
    subject_words = [w for w in re.findall(r"[\w'-]+", query)
                     if w.lower() not in _GENERIC_IMAGE_WORDS]
    shorter = " ".join(subject_words[:3])
    if shorter and shorter.lower() not in {x.lower() for x in passes}:
        passes.append(shorter)
    passes = passes[:2]

    for search_q in passes:
        if len(scored) >= 2:
            break
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
                continue
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

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored]


async def _openverse_lesson_candidates(query: str, limit: int = 10, grade: str | None = None,
                                       subject: str | None = None) -> list[dict]:
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
    if not candidate.get("url"):
        return None
    raw = await _curl_bytes(candidate["url"], timeout=10.0)
    if not raw:
        return None
    saved = _save_lesson_image(raw)
    if not saved:
        return None
    path, width, height = saved
    if width <= 0 or height <= 0 or not (0.35 <= width / height <= 3.2):
        return None
    credit = " · ".join(p for p in (source_label,
                                    candidate.get("author", ""),
                                    candidate.get("licence", "")) if p)
    return {
        "path": path,
        "caption": "",
        "file_title": _clean_file_title(candidate["title"]),
        "credit": credit,
        "source": candidate.get("descriptionurl", ""),
        "description": str(candidate.get("description") or "")[:400],
        "width": width,
        "height": height,
        "query": query,
    }


async def fetch_lesson_images(queries: list[str], count: int = 2, grade: str | None = None,
                              language: str | None = None, subject: str | None = None) -> list[dict]:
    results: list[dict] = []
    used_titles: set[str] = set()
    leftovers: list[tuple[str, dict]] = []

    for query in queries:
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

    for query, candidate in leftovers:
        if len(results) >= count:
            break
        if candidate["title"] in used_titles:
            continue
        got = await _take_lesson_candidate(candidate, query)
        if got:
            results.append(got)
            used_titles.add(candidate["title"])

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
                    break

    if len(results) < count:
        logger.info(f"Lesson images: got {len(results)} of {count} for {queries!r}")
    return results[:count]
