# Pinned to 3.13 (not 3.14) to stay on the well-tested asyncpg path — see
# requirements.txt's python_version markers and database.py's comment on
# why this project avoids the psycopg/3.14 fallback in production.
FROM python:3.13-slim

WORKDIR /app

# libpq / build tools for asyncpg + Pillow's native deps; removed from the
# final layer isn't worth the complexity here since this is a single-stage
# image and the packages are small.
#
# The three below are not optional extras — the product is broken
# without them, and broken quietly, which is worse:
#
#   libreoffice-impress  renders the .pptx into the PDF the app shows as
#       the presentation preview and serves from /download-pdf (see
#       app/pptx_pdf.py). Without a soffice binary the code falls back to
#       build_presentation_pdf, which SUCCEEDS — so nothing errors and
#       no log line stands out, the teacher just silently gets an A4
#       re-rendering instead of their actual slides. -impress rather than
#       the full suite: ~400 MB against ~1 GB, and nothing here converts
#       spreadsheets.
#
#   fonts-dejavu-core  is THE font for generated PDFs on Linux —
#       export_builder._register_unicode_font looks for DejaVuSans.ttf by
#       absolute path on non-Windows and has no further fallback. Without
#       it every PDF comes out as empty boxes. DejaVu specifically,
#       because of what this product is for: Tajik needs
#       ғ қ ҳ ҷ ӣ ӯ, which the slimmer base fonts do not carry.
#
#   fonts-liberation  is metric-compatible with Arial/Times, so the decks
#       LibreOffice renders keep the line breaks they were laid out with
#       instead of reflowing into a substituted face.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc libpq-dev curl \
        libreoffice-impress fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Avatars/uploads and rembg's downloaded model (see app/image_builder.py)
# live here — mount a named volume over this path in docker-compose.yml so
# they survive container recreation instead of vanishing on redeploy.
RUN mkdir -p uploads/avatars

EXPOSE 8586

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8586/api/health || exit 1

# Single worker, though no longer for the reason this comment used to
# give: MAX_MATERIALS_PER_DAY stopped being enforced (see
# ai_service._call_ai_inner, which now only logs the count).
#
# It stays at one because every OTHER throttle here counts in a single
# process's memory: the AI concurrency semaphore (security.py's
# _ai_semaphore, MAX_CONCURRENT_AI_CALLS), the flood guard
# (rate_limit.py's _hits deque) and the Wikimedia circuit breaker
# (image_builder.py's _backoff_until). N workers do not share any of
# them, so each limit quietly becomes N times looser. The AI provider's
# per-minute token quota is the one that bites first — and it bites as
# 429s on everybody's generation, not just the excess ones. Move these
# counters to Redis before raising this.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8586", "--workers", "1"]
