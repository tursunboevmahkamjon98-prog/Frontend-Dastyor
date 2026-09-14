# Pinned to 3.13 (not 3.14) to stay on the well-tested asyncpg path — see
# requirements.txt's python_version markers and database.py's comment on
# why this project avoids the psycopg/3.14 fallback in production.
FROM python:3.13-slim

WORKDIR /app

# libpq / build tools for asyncpg + Pillow's native deps; removed from the
# final layer isn't worth the complexity here since this is a single-stage
# image and the packages are small.
#
# libreoffice-impress WAS here and is deliberately gone (2026-09-14). It
# existed only to convert the generated .pptx into a PDF so the app could
# show the real slides in-browser. Each conversion is a headless soffice
# process holding 300-500 MB, and on the 2 GB VPS this is deployed to,
# two teachers opening a deck at the same moment was enough to exhaust
# the machine — the visible symptom being the entire API erroring, not a
# slow preview. A deck is downloaded and opened in PowerPoint now, so the
# ~400 MB of LibreOffice buys nothing and costs the whole server.
#
# app/pptx_pdf.py is still present and degrades on purpose: find_binary()
# returns None, convert() returns None, and /download-pdf falls back to
# export_builder.build_presentation_pdf (an A4 rendering). Reinstalling
# the package here is all it would take to turn the old path back on.
#
# The two font packages are NOT optional — without them the product is
# broken quietly, which is worse than loudly:
#
#   fonts-dejavu-core  is THE font for generated PDFs on Linux, for both
#       ReportLab (export_builder._register_unicode_font) and every PIL
#       drawing surface (app/fonts.py: covers, figures, timelines, and
#       math_render's formulas). Without it PDFs come out as empty boxes
#       and drawn pages as illegible specks. DejaVu specifically because
#       of what this product is for: Tajik needs ғ қ ҳ ҷ ӣ ӯ, which the
#       slimmer base fonts do not carry.
#
#   fonts-liberation  supplies the italic face app/fonts.py resolves for
#       mathematics (DejaVu Serif's own italic ships in the -extra
#       package, which is not installed). Variables are set in italic by
#       convention, so this is most of the glyphs in any formula.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc libpq-dev curl \
        fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Avatars/uploads and rembg's downloaded model (see app/image_builder.py)
# live here — mount a named volume over this path in docker-compose.yml so
# they survive container recreation instead of vanishing on redeploy.
RUN mkdir -p uploads/avatars

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8001/api/health || exit 1

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
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
