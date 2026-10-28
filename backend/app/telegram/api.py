"""Minimal async Telegram Bot API client.

Why hand-rolled instead of python-telegram-bot: ``httpx`` is already a
dependency, this needs eight methods, and the deployment target is a 2 GB
VPS whose Dockerfile comment records a previous out-of-memory incident
caused by one heavyweight dependency. Eight methods are cheaper than a
framework and leave the polling loop's failure behaviour explicit.

The one thing this file is careful about: **the bot token is a path
segment of every request URL.** An unscrubbed ``httpx`` exception, or a
``repr()`` of a request, therefore prints the live token into
``backend/logs/``, where it persists. Every raised error passes through
:func:`scrub` first, and :class:`TokenScrubbingFilter` is installed on
the loggers so even a third-party library's record cannot leak it.
"""

import asyncio
import logging
import re

import httpx

from app.http_client import SSL_CONTEXT
from app.logger import get_logger
from app.telegram.config import get_telegram_settings

logger = get_logger(__name__)

API_ROOT = "https://api.telegram.org"

# Deliberately unanchored. An earlier version wrapped this in \b...\b,
# which silently failed in the one place it matters most: a token appears
# in a URL as ".../bot<token>/sendMessage", and there is no word boundary
# between the "t" of "bot" and the token's first digit, so every leaked
# request URL passed through unscrubbed. Matching without boundaries can
# at worst clip the tail of a longer digit run into the match, which
# still redacts the secret.
_TOKEN_SHAPE = re.compile(r"\d{6,12}:[A-Za-z0-9_-]{30,}")


def scrub(text: object) -> str:
    """Replace anything shaped like a bot token with a placeholder.

    Shape-based as well as value-based, so it also catches a token that
    is not the one this process is configured with — a stale token in a
    pasted traceback, or a second bot's token in the same line.
    """
    out = str(text)
    token = get_telegram_settings().TELEGRAM_BOT_TOKEN
    if token:
        out = out.replace(token, "<BOT_TOKEN>")
    return _TOKEN_SHAPE.sub("<BOT_TOKEN>", out)


class TokenScrubbingFilter(logging.Filter):
    """Scrubs bot tokens out of every record on the loggers it is added to."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = scrub(record.getMessage())
            record.args = ()
            if record.exc_info:
                # The traceback is rendered later by the formatter, so the
                # only way to be certain a URL inside it never reaches a
                # file is to collapse it into a scrubbed summary here.
                exc = record.exc_info[1]
                record.msg = f"{record.msg} | {type(exc).__name__}: {scrub(exc)}"
                record.exc_info = None
        except Exception:
            record.msg = "<log record suppressed by token scrubber>"
            record.args = ()
            record.exc_info = None
        return True


def install_token_scrubber() -> None:
    """Add the scrubbing filter to every handler the project installs."""
    seen: set[int] = set()
    for name in ("", "httpx", "httpcore", "app", __name__):
        lg = logging.getLogger(name)
        lg.addFilter(TokenScrubbingFilter())
        for handler in lg.handlers:
            if id(handler) not in seen:
                seen.add(id(handler))
                handler.addFilter(TokenScrubbingFilter())


class TelegramApiError(RuntimeError):
    """A Bot API call that returned a non-ok answer.

    ``retry_after`` is populated for 429s so the caller honours
    Telegram's own backoff instead of guessing one.
    """

    def __init__(self, method: str, status: int, description: str,
                 retry_after: float | None = None):
        self.method = method
        self.status = status
        self.description = scrub(description)
        self.retry_after = retry_after
        super().__init__(f"{method} failed ({status}): {self.description}")


class TelegramTransportError(RuntimeError):
    """The request never got an answer — DNS, TLS, timeout, reset."""


class ReceiptTooLarge(Exception):
    def __init__(self, size: int):
        self.size = size
        super().__init__(f"receipt exceeds the configured size limit ({size} bytes read)")


class TelegramClient:
    """One client per process; reuses a single connection pool.

    ``max_attempts`` covers transport failures and Telegram's own
    429/5xx answers. A 4xx that is not 429 is never retried: a malformed
    request does not become well-formed on a second try, and retrying a
    ``sendMessage`` Telegram rejected for content would post it once per
    attempt if it later succeeded.
    """

    def __init__(self, token: str | None = None, *, max_attempts: int = 4,
                 timeout: float = 40.0):
        settings = get_telegram_settings()
        self._token = token or settings.TELEGRAM_BOT_TOKEN
        if not self._token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN is not set. Put it in backend/.env.telegram "
                "(gitignored) or in the process environment - never in .env, "
                "which this repository commits."
            )
        self._max_attempts = max_attempts
        self._client = httpx.AsyncClient(
            timeout=timeout,
            verify=SSL_CONTEXT,
            # Telegram serves one getUpdates per bot anyway; a small pool
            # keeps the footprint flat on the 2 GB host.
            limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
        )

    @property
    def _base(self) -> str:
        return f"{API_ROOT}/bot{self._token}"

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "TelegramClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    async def call(self, method: str, payload: dict | None = None,
                   *, files: dict | None = None,
                   attempts: int | None = None) -> dict | list:
        """Invoke a Bot API method and return its ``result``."""
        max_attempts = attempts or self._max_attempts
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                if files:
                    resp = await self._client.post(
                        f"{self._base}/{method}",
                        data={k: v for k, v in (payload or {}).items() if v is not None},
                        files=files,
                    )
                else:
                    resp = await self._client.post(
                        f"{self._base}/{method}",
                        json={k: v for k, v in (payload or {}).items() if v is not None},
                    )
            except httpx.HTTPError as e:
                # str(e) can embed the request URL, hence scrub().
                last_error = TelegramTransportError(
                    f"{method}: {type(e).__name__}: {scrub(e)}"
                )
                if attempt == max_attempts:
                    break
                await asyncio.sleep(min(2 ** attempt, 30))
                continue

            try:
                body = resp.json()
            except ValueError:
                body = {}

            if resp.status_code == 200 and body.get("ok"):
                return body.get("result", {})

            description = body.get("description") or f"HTTP {resp.status_code}"
            retry_after = None
            params = body.get("parameters") or {}
            if isinstance(params, dict) and params.get("retry_after") is not None:
                try:
                    retry_after = float(params["retry_after"])
                except (TypeError, ValueError):
                    retry_after = None

            error = TelegramApiError(method, resp.status_code, description, retry_after)

            retriable = resp.status_code == 429 or resp.status_code >= 500
            if not retriable or attempt == max_attempts:
                raise error

            delay = retry_after if retry_after is not None else min(2 ** attempt, 30)
            logger.warning(
                f"Telegram {method} returned {resp.status_code}; retrying in "
                f"{delay:.1f}s (attempt {attempt}/{max_attempts})"
            )
            await asyncio.sleep(delay)
            last_error = error

        assert last_error is not None
        raise last_error

    # ---- the methods this bot actually uses --------------------------

    async def get_me(self) -> dict:
        result = await self.call("getMe")
        return result if isinstance(result, dict) else {}

    async def get_updates(self, offset: int, timeout: int,
                          allowed_updates: list[str] | None = None) -> list[dict]:
        result = await self.call(
            "getUpdates",
            {
                "offset": offset,
                "timeout": timeout,
                "allowed_updates": allowed_updates or ["message", "callback_query"],
            },
            # The loop retries and persists the offset itself; retrying
            # inside the call would stack two backoffs on top of each
            # other and hold the poll open past its timeout.
            attempts=1,
        )
        return result if isinstance(result, list) else []

    async def send_message(self, chat_id: int, text: str, *,
                           reply_markup: dict | None = None,
                           parse_mode: str | None = None,
                           disable_web_page_preview: bool = True) -> dict:
        result = await self.call("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": reply_markup,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        })
        return result if isinstance(result, dict) else {}

    async def send_photo(self, chat_id: int, photo: str, *,
                         caption: str | None = None,
                         reply_markup: dict | None = None,
                         parse_mode: str | None = None) -> dict:
        result = await self.call("sendPhoto", {
            "chat_id": chat_id,
            "photo": photo,
            "caption": caption,
            "reply_markup": reply_markup,
            "parse_mode": parse_mode,
        })
        return result if isinstance(result, dict) else {}

    async def send_document(self, chat_id: int, document: str, *,
                            caption: str | None = None,
                            reply_markup: dict | None = None,
                            parse_mode: str | None = None) -> dict:
        result = await self.call("sendDocument", {
            "chat_id": chat_id,
            "document": document,
            "caption": caption,
            "reply_markup": reply_markup,
            "parse_mode": parse_mode,
        })
        return result if isinstance(result, dict) else {}

    async def edit_message_reply_markup(self, chat_id: int, message_id: int,
                                        reply_markup: dict | None = None) -> dict:
        result = await self.call("editMessageReplyMarkup", {
            "chat_id": chat_id,
            "message_id": message_id,
            "reply_markup": reply_markup,
        })
        return result if isinstance(result, dict) else {}

    async def answer_callback_query(self, callback_query_id: str, *,
                                    text: str | None = None,
                                    show_alert: bool = False) -> dict:
        result = await self.call("answerCallbackQuery", {
            "callback_query_id": callback_query_id,
            "text": text,
            "show_alert": show_alert,
        })
        return result if isinstance(result, dict) else {}

    async def set_my_commands(self, commands: list[tuple[str, str]],
                              language_code: str | None = None) -> bool:
        """Populate Telegram's "/" menu with readable descriptions.

        Best-effort: a bot whose menu did not register still works, it
        is just less discoverable, so a failure here must not stop
        startup.
        """
        payload: dict = {
            "commands": [
                {"command": c, "description": d} for c, d in commands
            ],
        }
        if language_code:
            payload["language_code"] = language_code
        try:
            await self.call("setMyCommands", payload)
            return True
        except (TelegramApiError, TelegramTransportError) as e:
            logger.warning(f"setMyCommands failed ({language_code}): {e}")
            return False

    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        """Remove a message from a chat.

        Used to take a password back out of the conversation the instant
        it has been checked. A bot may delete incoming messages in a
        private chat, and only within 48 hours — neither limit matters
        here, since this runs milliseconds after the message arrives.

        Returns False rather than raising: failing to delete is worth a
        warning to the user, not an aborted login.
        """
        try:
            await self.call("deleteMessage", {
                "chat_id": chat_id,
                "message_id": message_id,
            })
            return True
        except (TelegramApiError, TelegramTransportError) as e:
            logger.warning(f"Could not delete message {message_id}: {e}")
            return False

    async def get_chat(self, chat_id: int) -> dict:
        """Chat details, including a private chat's current @username.

        Works only for chats this bot already knows — the Bot API has no
        lookup by username, and no way to see a stranger. For an account
        that linked through the deep link, the bot does know the chat,
        which is what makes the username backfill possible.
        """
        result = await self.call("getChat", {"chat_id": chat_id})
        return result if isinstance(result, dict) else {}

    async def get_file(self, file_id: str) -> dict:
        result = await self.call("getFile", {"file_id": file_id})
        return result if isinstance(result, dict) else {}

    async def download_file(self, file_path: str, *, max_bytes: int) -> bytes:
        """Stream a file down, aborting once it exceeds ``max_bytes``.

        Streamed rather than read whole because ``getFile``'s reported
        size is advisory: trusting it would let a body larger than the
        configured ceiling land in memory on a 2 GB host.
        """
        url = f"{API_ROOT}/file/bot{self._token}/{file_path}"
        chunks: list[bytes] = []
        total = 0
        try:
            async with self._client.stream("GET", url) as resp:
                if resp.status_code != 200:
                    raise TelegramApiError(
                        "downloadFile", resp.status_code, "download failed"
                    )
                async for chunk in resp.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise ReceiptTooLarge(total)
                    chunks.append(chunk)
        except httpx.HTTPError as e:
            raise TelegramTransportError(
                f"downloadFile: {type(e).__name__}: {scrub(e)}"
            ) from None
        return b"".join(chunks)
