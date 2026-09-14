from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    # A teacher opening the app after the 24h access token expired used to
    # just get silently logged out (auth-context.tsx's /auth/me 401 ->
    # clearToken). This lets the frontend trade a still-valid refresh token
    # for a new access token instead — 30 days covers "didn't open the app
    # over the weekend" without being an effectively-forever session.
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    # How long a device stays "already verified" before login asks it for
    # an SMS code again (see models.TrustedDevice). Long enough that a
    # teacher's own laptop/phone isn't re-challenged every few weeks,
    # short enough that a device they stopped using eventually falls out.
    TRUSTED_DEVICE_EXPIRE_DAYS: int = 90
    AI_API_KEY: str
    AI_API_KEY_2: str = ""
    AI_API_KEY_3: str = ""
    AI_API_KEY_4: str = ""
    AI_API_KEY_5: str = ""
    # gemma-4-31b used to be the default and had to go: Cerebras still
    # lists it under /models, but every chat/completions call answers
    # 404 "Model does not exist or you do not have access to it" — on
    # every key tried. A model that is visible but not callable is the
    # worst kind of default, because the listing makes it look fine.
    AI_MODEL: str = "gpt-oss-120b"
    AI_BASE_URL: str = "https://api.cerebras.ai/v1"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "Dastyor"

    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    ADMIN_NAME: str = "Admin"
    # Login switched to phone-only (see schemas.UserLogin) — without a
    # phone number the ADMIN_EMAIL-seeded account has no way to actually
    # log in anymore. Set this ("+992XXXXXXXXX") to give it one; left
    # blank, the account still gets created/promoted to admin as before,
    # it just can't sign in until a phone is added by hand.
    ADMIN_PHONE: str = ""

    # SMS OTP for phone registration/login/password-reset (see
    # app/sms_service.py) — Twilio's plain REST API, hit directly with
    # httpx rather than pulling in the twilio SDK as a dependency. Left
    # blank until the user supplies a real Twilio account; while empty,
    # send_sms_code() prints the code to the server console instead (same
    # "not configured yet" fallback email_service.py already uses for
    # SMTP), so registration/login stays testable end-to-end without it.
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # Robita (sms.robita.tj) — Tajik SMS gateway used as the actual OTP
    # sender since Robita has no token-based REST API, only a session-
    # cookie web portal (see sms_service.py's RobitaClient). Tried before
    # Twilio in send_sms_code(); leave blank to skip straight to Twilio
    # (or to the console fallback if neither is configured).
    ROBITA_LOGIN: str = ""
    ROBITA_PASSWORD: str = ""
    ROBITA_SENDER: str = ""  # the sender-ID value from the portal's dropdown, e.g. "0176"

    # Login OTP (mobile app only, see routers/auth.py's login/send-code +
    # login/verify) skips the SMS step entirely for whichever phone number
    # this holds — a fixed test/demo account that always needs to log in
    # without waiting on a real code. Credentials are still checked first;
    # this only short-circuits the OTP requirement, never authentication
    # itself.
    #
    # Empty by default on purpose: the number used to be hardcoded here,
    # so a deploy whose .env never mentioned OTP_BYPASS_PHONE still had a
    # live bypass for that one account without anyone setting it. Now the
    # bypass exists only where .env explicitly asks for it, and "" matches
    # no phone (schemas._NormalizedPhone always yields "+992XXXXXXXXX").
    OTP_BYPASS_PHONE: str = ""

    # Web OAuth Client ID from Google Cloud Console — checked as the `aud`
    # claim on every credential POSTed to /auth/google (see routers/auth.py)
    # so a token minted for some other app can't be replayed here. Must
    # match the frontend's NEXT_PUBLIC_GOOGLE_CLIENT_ID exactly.
    GOOGLE_CLIENT_ID: str = ""

    CORS_ORIGINS: str = "http://localhost:3000"

    # Serves /docs, /redoc and /openapi.json. Off unless a .env asks for
    # it, which is the way round that fails safe: a production deploy
    # copies .env.example and gets a closed API surface without anyone
    # having to remember, while this repo's own .env turns it back on for
    # local work. It publishes every route, schema and admin endpoint —
    # not a way in by itself, but a free map for anyone looking for one.
    DOCS_ENABLED: bool = False

    # Rate limiting
    MAX_FORGOT_ATTEMPTS: int = 5
    MAX_VERIFY_ATTEMPTS: int = 10
    MAX_LOGIN_ATTEMPTS: int = 10
    MAX_REGISTER_CODE_ATTEMPTS: int = 5
    RATE_WINDOW: int = 300  # 5 minutes

    # Per-IP caps. The per-phone limiter above cannot see an attacker who
    # rotates numbers; these can. Sized for the fact that one address is
    # often MANY people — a school's Wi-Fi, or a mobile operator's CGNAT
    # pool — so they are built as a tight burst window plus a loose
    # hourly ceiling rather than one small number.
    #
    # A loop sending codes trips the burst limit on its sixth request
    # inside a minute. Thirty teachers registering during one staff
    # meeting do not: they arrive seconds apart, not milliseconds, and
    # the hourly ceiling is high enough for all of them.
    # Machine speed only: forty requests inside ten seconds is not a room
    # of people, it is a loop. A staffroom of thirty registering at once
    # passes this untouched — which the first, tighter version did not,
    # and it locked out twenty-four of them in testing.
    MAX_SMS_PER_IP_BURST: int = 40
    RATE_WINDOW_IP_BURST: int = 10          # 10 seconds
    MAX_SMS_PER_IP: int = 150
    MAX_REGISTER_PER_IP: int = 60
    RATE_WINDOW_IP: int = 3600              # 1 hour

    # The hard stop on the SMS bill, counted across EVERY address.
    # Per-IP limits cannot bound spend — an attacker with a hundred
    # addresses simply gets a hundred quotas — and SMS is the one thing
    # in this app that costs money per request. Past this, codes stop
    # being sent and the log says so loudly; raise it deliberately when
    # real usage grows into it.
    MAX_SMS_PER_DAY: int = 500

    # Sends nothing and prints the code instead, with every rate limit
    # still running. Exists because load-testing the OTP endpoints against
    # a live provider sends real texts to whoever owns the numbers in the
    # test — which happened here before this flag existed. Anything that
    # exercises these endpoints in bulk must set it.
    SMS_DRY_RUN: bool = False

    # Requests per minute per IP, across the whole API — the crude flood
    # guard in rate_limit.py. Also sized for a shared address: a dashboard
    # page load is a handful of calls, and a school of thirty on one line
    # must stay well under this.
    MAX_REQUESTS_PER_MINUTE: int = 900

    # ── Game section access (see routers/materials.py's
    # require_game_access) ────────────────────────────────────────────
    # Comma-separated account ids (the UUID `id`, or the 6-digit
    # `short_id`, whichever is easier to copy) allowed to use the game
    # section without being administrators. Admins always have access
    # regardless of this list. Empty by default: admins only.
    GAME_ACCESS_USER_IDS: str = ""

    # ── Per-user throttles on the expensive endpoints ────────────────
    # rate_limit.py's per-IP cap cannot see a single authenticated
    # account working from many addresses, and an AI generation is the
    # one request here that costs real money to serve. These are counted
    # per user id, in the database, so they hold across workers and
    # across devices.
    MAX_GENERATIONS_PER_HOUR: int = 40
    MAX_AI_EDITS_PER_HOUR: int = 60

    # How many AI generations this process will run at once. Past this,
    # requests queue rather than piling more concurrent upstream calls
    # onto the provider (which returns 429s and makes every in-flight
    # request slower, not just the new ones). The queue is what keeps
    # ordinary non-AI API calls responsive while generations are in
    # flight — they never touch this semaphore.
    MAX_CONCURRENT_AI_CALLS: int = 8

    # How many LibreOffice conversions may run at once (see
    # app/pptx_pdf.py). Each one is a real soffice process holding
    # 300-500 MB, and nothing bounded this before — two teachers
    # exporting a deck at the same moment were enough to run a 2 GB VPS
    # out of memory, which surfaces as the whole API erroring rather
    # than as a slow export. 1 is the safe default for the server size
    # DEPLOY.md recommends; raise it only after checking the box has the
    # RAM for N x 500 MB on top of Postgres and the app itself.
    MAX_CONCURRENT_PPTX_CONVERSIONS: int = 1
    # How long a request will wait for a slot before giving up with 503.
    # Long enough to ride out a burst, short enough that a client is not
    # left holding an open connection indefinitely.
    AI_QUEUE_TIMEOUT_SECONDS: int = 120

    # Hard ceiling on a request body, enforced before the body is read
    # (see app/security.py). Without it, one client can make the server
    # buffer an arbitrary amount of memory just by declaring a large
    # Content-Length. The konspekt "book mode" upload is the largest
    # legitimate body, at MAX_SOURCE_FILE_SIZE.
    MAX_REQUEST_BODY_BYTES: int = 20 * 1024 * 1024  # 20 MB

    # ── Admin sign-in brute-force lockout ────────────────────────────
    # Counted per targeted admin account rather than per IP, because a
    # distributed guessing attempt stays under every per-IP limit by
    # design. Cleared on a successful sign-in.
    MAX_ADMIN_LOGIN_ATTEMPTS: int = 5
    ADMIN_LOCKOUT_SECONDS: int = 900  # 15 minutes

    # Minimum strength for an account that holds the admin role. Enforced
    # on password change/reset, never retroactively at login — locking an
    # existing admin out of their own panel over a policy change would
    # need a database console to undo.
    ADMIN_MIN_PASSWORD_LENGTH: int = 10

    # ── Database pool ────────────────────────────────────────────────
    # Was hardcoded at 5+10. Overridable because the right number depends
    # on the deployment: it must be (pool + overflow) x workers <= the
    # server's max_connections, or the pool exhausts into connection
    # errors under exactly the load it exists to survive.
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800  # seconds; below most managed-PG idle timeouts
    DB_POOL_TIMEOUT: int = 30    # seconds to wait for a free connection

    # File upload
    MAX_AVATAR_SIZE: int = 5 * 1024 * 1024  # 5 MB
    ALLOWED_AVATAR_EXT: str = ".jpg,.jpeg,.png,.webp"

    # Konspekt "book mode" source document upload (see
    # app/document_extract.py / POST /materials/upload-source) — a teacher's
    # textbook chapter/lecture notes to generate the konspekt from.
    MAX_SOURCE_FILE_SIZE: int = 15 * 1024 * 1024  # 15 MB
    ALLOWED_SOURCE_EXT: str = ".pdf,.docx,.txt"

    # AI Cost Management — same cap as the Flutter app's backend; a single
    # curriculum (~1 month, ~22 lesson days) needs roughly 1 roadmap call +
    # 2 calls per day (generate + verify) = ~45 calls.
    MAX_MATERIALS_PER_DAY: int = 100

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
