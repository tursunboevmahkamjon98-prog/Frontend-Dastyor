#!/usr/bin/env bash
# One-shot bootstrap + launcher for the Dastyor Docker stack.
#
#     ./start.sh
#
# What it does, in order:
#   1. Generates ./.env (Postgres password + host ports) if it does not
#      exist yet — never overwrites one that's already there.
#   2. Generates backend/.env from backend/.env.example if it does not
#      exist yet, filling in SECRET_KEY, ADMIN_PASSWORD and the Postgres
#      credentials automatically. Also never overwrites an existing file,
#      so real production secrets (AI keys, SMTP, ROBITA...) are never
#      touched once they've been filled in by hand.
#   3. Runs `docker compose up -d --build`, which builds two images
#      (backend, frontend — `db` is the stock postgres:16-alpine image,
#      nothing to build) and starts three containers: db + backend +
#      frontend, wired together on the compose network.
#
# Safe to re-run any time (e.g. after `git pull`): existing .env files
# are left alone, and compose only rebuilds what changed.
set -euo pipefail

cd "$(dirname "$0")"

# ── defaults (only used the first time .env is generated) ────────────────
DEFAULT_FRONTEND_PORT=8090
DEFAULT_BACKEND_PORT=8586

log()  { echo "-> $*"; }
warn() { echo "   WARNING: $*" >&2; }

# ── random secrets, without depending on any one specific tool ───────────
rand_hex() {
    local bytes="${1:-24}"
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex "$bytes"
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "import secrets; print(secrets.token_hex(${bytes}))"
    else
        head -c "$bytes" /dev/urandom | od -An -tx1 | tr -d ' \n'
    fi
}

rand_urlsafe() {
    local bytes="${1:-32}"
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -base64 "$bytes" | tr '+/' '-_' | tr -d '=\n'
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "import secrets; print(secrets.token_urlsafe(${bytes}))"
    else
        head -c "$bytes" /dev/urandom | base64 | tr '+/' '-_' | tr -d '=\n'
    fi
}

# Readable password: alnum only, no quoting/escaping surprises wherever it
# ends up (.env file, shell, docker logs).
rand_password() {
    local len="${1:-16}"
    rand_urlsafe 24 | tr -dc 'A-Za-z0-9' | head -c "$len"
}

# ── 0. docker compose must exist ──────────────────────────────────────────
if docker compose version >/dev/null 2>&1; then
    DC=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    DC=(docker-compose)
else
    echo "FATAL: 'docker compose' (plugin) yoki 'docker-compose' topilmadi." >&2
    echo "       O'rnating: sudo apt install -y docker.io docker-compose-plugin" >&2
    exit 1
fi

# ── 1. root .env — Postgres password + host ports for docker-compose.yml ─
ROOT_ENV=".env"
if [ ! -f "$ROOT_ENV" ]; then
    log ".env yaratilmoqda (Postgres paroli avtomatik, portlar: backend=${DEFAULT_BACKEND_PORT}, frontend=${DEFAULT_FRONTEND_PORT})..."
    GEN_POSTGRES_PASSWORD="$(rand_hex 24)"
    cat > "$ROOT_ENV" <<EOF
# Avtomatik yaratildi: $(date -u +%Y-%m-%dT%H:%M:%SZ) by start.sh — qo'lda o'zgartirsangiz bo'ladi,
# start.sh bu faylni qayta ishga tushirilganda tegmaydi (agar u allaqachon mavjud bo'lsa).
#
# docker-compose.yml Compose'ning o'zi bu faylni (papkadagi .env) avtomatik o'qiydi.

# Postgres paroli — faqat postgres_data volume BIRINCHI marta yaratilganda
# ishlatiladi (qara docker-compose.yml). Volume yaratilgandan keyin buni
# o'zgartirish hech narsa qilmaydi, volume'ni o'chirib qayta yaratish kerak.
POSTGRES_PASSWORD=${GEN_POSTGRES_PASSWORD}

# Stack qaysi HOST portlarida javob beradi.
BACKEND_PORT=${DEFAULT_BACKEND_PORT}
FRONTEND_PORT=${DEFAULT_FRONTEND_PORT}
EOF
    log "POSTGRES_PASSWORD avtomatik yaratildi va .env ga yozildi."
else
    log ".env allaqachon mavjud — tegilmadi."
fi

# Load it so POSTGRES_PASSWORD/BACKEND_PORT/FRONTEND_PORT are available
# below (for backend/.env generation and the final printout).
set -a
# shellcheck disable=SC1091
source "$ROOT_ENV"
set +a

# ── 2. backend/.env — app secrets, generated once ─────────────────────────
BACKEND_ENV="backend/.env"
if [ ! -f "$BACKEND_ENV" ]; then
    if [ ! -f "backend/.env.example" ]; then
        echo "FATAL: backend/.env.example topilmadi, backend/.env yarata olmadim." >&2
        exit 1
    fi
    log "backend/.env yaratilmoqda (backend/.env.example asosida, kalitlar avtomatik)..."
    cp backend/.env.example "$BACKEND_ENV"

    GEN_SECRET_KEY="$(rand_urlsafe 32)"
    GEN_ADMIN_PASSWORD="$(rand_password 16)"

    # db xizmati docker-compose.yml'da POSTGRES_DB=dastyor_db, POSTGRES_USER=postgres
    # bilan ishga tushadi — shu bilan mos bo'lishi uchun (compose baribir
    # DATABASE_URL'ni environment: bo'limida db:5432'ga qarab qayta yozadi,
    # bu yerdagi qiymat asosan Docker'siz to'g'ridan-to'g'ri ishga tushirish
    # uchun kerak).
    sed -i \
        -e "s#^DATABASE_URL=.*#DATABASE_URL=postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@localhost:5432/dastyor_db#" \
        -e "s#^DATABASE_URL_SYNC=.*#DATABASE_URL_SYNC=postgresql://postgres:${POSTGRES_PASSWORD}@localhost:5432/dastyor_db#" \
        -e "s#^SECRET_KEY=.*#SECRET_KEY=${GEN_SECRET_KEY}#" \
        -e "s#^ADMIN_PASSWORD=.*#ADMIN_PASSWORD=${GEN_ADMIN_PASSWORD}#" \
        "$BACKEND_ENV"

    log "SECRET_KEY va ADMIN_PASSWORD avtomatik yaratildi."
    log "ADMIN_PASSWORD: ${GEN_ADMIN_PASSWORD}  (buni hozir saqlab qo'ying — boshqa joyda qayta ko'rsatilmaydi)"
    echo ""
    warn "backend/.env quyidagilarsiz to'liq ishlamaydi — qo'lda to'ldiring:"
    warn "  AI_API_KEY          - AI generatsiya (Cerebras)"
    warn "  ADMIN_EMAIL / ADMIN_PHONE - admin akkaunt"
    warn "  SMTP_USER / SMTP_PASSWORD - email yuborish"
    warn "  GOOGLE_CLIENT_ID     - Google orqali kirish"
    warn "  ROBITA_* yoki TWILIO_* - SMS OTP"
    warn "  CORS_ORIGINS         - haqiqiy domeningiz"
    echo ""
else
    log "backend/.env allaqachon mavjud — tegilmadi (mavjud maxfiy kalitlar saqlanib qoladi)."
fi

# ── 3. build + start ───────────────────────────────────────────────────────
log "Docker image'lar qurilmoqda va konteynerlar ishga tushirilmoqda (db + backend + frontend)..."
"${DC[@]}" up -d --build

echo ""
log "Tayyor."
echo "   Holat:    ${DC[*]} ps"
echo "   Loglar:   ${DC[*]} logs -f backend   (yoki frontend / db)"
echo "   Frontend: http://localhost:${FRONTEND_PORT:-$DEFAULT_FRONTEND_PORT}"
echo "   Backend:  http://localhost:${BACKEND_PORT:-$DEFAULT_BACKEND_PORT}/api/health"
