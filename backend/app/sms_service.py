import httpx
from app.config import get_settings

settings = get_settings()

TWILIO_MESSAGES_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

ROBITA_BASE = "https://sms.robita.tj"
ROBITA_LOGIN_URL = f"{ROBITA_BASE}/auth"
ROBITA_SEND_URL = f"{ROBITA_BASE}/home?page=message&send=one_done"


class RobitaClient:
    """Talks to sms.robita.tj the same way a browser would — Robita has
    no token-based REST API, only a session-cookie web portal (confirmed
    by inspecting the live site: the login form at "/" posts to /auth
    with fields login+password and no CSRF token, and the "Одиночная
    отправка" form posts to /home?page=message&send=one_done with fields
    customer+sender+text+plan, also no CSRF token — so a plain httpx
    session that logs in once and reuses the cookie is enough).

    Deliberately NOT a REST integration: if Robita ever changes this
    portal's markup, sending silently starts failing and send_sms_code()
    falls through to its console-print fallback (see below) rather than
    breaking registration/login. Re-login is attempted once per process
    lifetime and again automatically whenever a send looks logged-out."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._logged_in = False

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
        return self._client

    async def _login(self) -> bool:
        client = await self._ensure_client()
        try:
            resp = await client.post(
                ROBITA_LOGIN_URL,
                data={"login": settings.ROBITA_LOGIN, "password": settings.ROBITA_PASSWORD},
            )
            # The portal always answers 200 (it re-renders the page rather
            # than returning a real HTTP error), so check for the
            # dashboard's own markup instead of the status code.
            self._logged_in = resp.status_code < 400 and "Отправка SMS" in resp.text
            return self._logged_in
        except Exception as e:
            print(f"[SMS/Robita] login failed: {e}")
            self._logged_in = False
            return False

    async def send(self, phone: str, text: str) -> bool:
        if not self._logged_in and not await self._login():
            return False

        client = await self._ensure_client()
        # Robita numbers are local (no "+992" prefix) on this portal.
        customer = phone.lstrip("+").removeprefix("992")

        async def _post_once() -> httpx.Response:
            return await client.post(
                ROBITA_SEND_URL,
                data={
                    "customer": customer,
                    "sender": settings.ROBITA_SENDER,
                    "text": text,
                    "plan": "now",
                },
            )

        try:
            resp = await _post_once()
            # Session cookie expired mid-run — log in again and retry once.
            if resp.status_code >= 400 or "Одиночная отправка" not in resp.text and "успешно" not in resp.text.lower():
                if await self._login():
                    resp = await _post_once()
            ok = resp.status_code < 400 and ("успешно" in resp.text.lower() or "очеред" in resp.text.lower())
            if not ok:
                print(f"[SMS/Robita] send to {phone} did not confirm success (status {resp.status_code})")
            return ok
        except Exception as e:
            print(f"[SMS/Robita] send to {phone} failed: {e}")
            return False


_robita_client = RobitaClient()


# OTP text per user.language (see app/i18n.py — same 3 codes: ru/en/tg).
# Used to be hardcoded Tajik for every single user regardless of language,
# which is what a teacher using the app in Russian/English would actually
# see on their phone no matter what — now matches whichever language the
# account (or, before an account exists, the request) is in.
_OTP_TEXTS = {
    "ru": "Dastyor: код подтверждения — {code}. Действует 10 минут.",
    "en": "Dastyor: verification code — {code}. Valid for 10 minutes.",
    "tg": "Dastyor: код тасдиқ — {code}. Амал 10 дақиқа.",
}


def _otp_text(code: str, language: str) -> str:
    lang_code = (language or "ru").lower()[:2]
    template = _OTP_TEXTS.get(lang_code, _OTP_TEXTS["ru"])
    return template.format(code=code)


async def _send_via_robita(phone: str, code: str, language: str) -> bool:
    text = _otp_text(code, language)
    return await _robita_client.send(phone, text)


async def _send_via_twilio(phone: str, code: str, language: str) -> bool:
    sid = settings.TWILIO_ACCOUNT_SID
    token = settings.TWILIO_AUTH_TOKEN
    from_number = settings.TWILIO_FROM_NUMBER
    body = _otp_text(code, language)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TWILIO_MESSAGES_URL.format(sid=sid),
                auth=(sid, token),
                data={"From": from_number, "To": phone, "Body": body},
                timeout=10.0,
            )
        if resp.status_code not in (200, 201):
            print(f"[SMS] Twilio error {resp.status_code} sending to {phone}: {resp.text[:300]}")
            return False
        print(f"[SMS] Code sent to {phone} via Twilio")
        return True
    except Exception as e:
        print(f"[SMS] Twilio failed to send to {phone}: {e}")
        return False


async def send_sms_code(phone: str, code: str, language: str = "ru") -> bool:
    """Sends a 6-digit OTP code to `phone` (always "+992XXXXXXXXX" — see
    schemas._NormalizedPhone). Tries Robita first (the actually-funded,
    working account — see RobitaClient above), then Twilio if configured,
    and finally falls back to printing the code to the server console so
    registration/login/password-reset stay testable even with neither
    provider set up. `language` picks the OTP text (see _OTP_TEXTS) —
    callers pass the account's own User.language where one already exists
    (login, password reset); registration has no account yet, so it falls
    back to the "ru" default."""
    if settings.SMS_DRY_RUN:
        # Checked before every provider: a dry run must never reach a real
        # network, whatever is configured.
        print(f"[SMS DRY RUN] Would send code {code} to {phone} — nothing sent")
        return True

    if settings.ROBITA_LOGIN and settings.ROBITA_PASSWORD and settings.ROBITA_SENDER:
        if await _send_via_robita(phone, code, language):
            print(f"[SMS] Code sent to {phone} via Robita")
            return True
        print(f"[SMS] Robita failed for {phone}, falling back...")

    if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER:
        return await _send_via_twilio(phone, code, language)

    print(f"\n{'='*50}")
    print(f"[SMS CODE] Phone: {phone}")
    print(f"[SMS CODE] Code: {code}")
    print(f"[SMS CODE] No SMS provider configured — printed to console")
    print(f"{'='*50}\n")
    return True
