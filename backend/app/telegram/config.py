"""Configuration for the Telegram payment bot.

Why this is a separate settings class and not more fields on
``app.config.Settings``:

``Settings`` reads ``.env``, and in this repository ``backend/.env`` is
committed on purpose (see backend/.gitignore's own note — the repo is
private). A bot token in a committed file is a bot token in Git, which is
exactly the failure this module exists to avoid. So the secret is read
from the process environment or from ``.env.telegram``, which **is**
gitignored, and the loader order below makes the gitignored file win.

Nothing here is ever logged. ``redacted()`` is what goes into a log line
or a report; the raw token is only ever handed to httpx.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings

from app.limits import GENERATION_PRICE_DIRAMS


class TelegramSettings(BaseSettings):
    # The @BotFather token. No default: a missing token must stop the bot
    # at startup with a clear message, never fall through to an empty
    # string that turns every API call into a confusing 401.
    TELEGRAM_BOT_TOKEN: str = ""

    # The bot's @username without the @. Used only to build the deep link
    # the app opens; it is not a secret and it is not proof of anything.
    TELEGRAM_BOT_USERNAME: str = ""

    # A SECOND @BotFather bot, used only to review payments.
    #
    # Why two bots rather than one that behaves differently per chat: the
    # teacher-facing bot is public — anyone can find and message it — and
    # every receipt a teacher uploads carries a name, part of a card
    # number and an amount. Routing the review channel through its own
    # bot means the approve/reject buttons physically do not exist in the
    # public bot's update stream, so a bug in the authorization check
    # cannot expose them. It also keeps the owner's review chat out of a
    # bot whose chat list is full of teachers.
    #
    # Empty = fall back to the single-bot arrangement: reviews go to the
    # admin ids through the user bot, exactly as before. That keeps an
    # existing deployment working when it pulls this change.
    TELEGRAM_ADMIN_BOT_TOKEN: str = ""

    # Language of the review messages and buttons. Russian by default:
    # the reviewer is one known person, not the Tajik-speaking teachers
    # the rest of the bot serves.
    TELEGRAM_ADMIN_LANGUAGE: str = "ru"

    # Comma-separated Telegram numeric user IDs allowed to approve or
    # reject a payment. Empty = nobody can approve, which is the correct
    # failure direction: an unconfigured deployment must not be one where
    # any passer-by is an admin.
    #
    # These are the ids the ADMIN bot accepts actions from. Being able to
    # message the admin bot is not enough on its own.
    TELEGRAM_ADMIN_IDS: str = ""

    # Owner-written transfer instructions shown by /pay. Empty = /pay says
    # it is not configured yet. This module never invents an account
    # number, a bank or a card: a wrong one sends a teacher's money to a
    # stranger.
    TELEGRAM_PAY_INSTRUCTIONS: str = ""

    # The name/account the receipt is expected to show, used only to
    # compare against OCR output and flag a mismatch for the admin.
    TELEGRAM_PAY_RECIPIENT: str = ""

    # One-time account-linking token lifetime. Short on purpose: the token
    # travels through a deep link, which lands in Telegram's chat history
    # and possibly a clipboard.
    TELEGRAM_LINK_TOKEN_TTL_SECONDS: int = 300

    # Receipt upload limits.
    TELEGRAM_MAX_RECEIPT_BYTES: int = 8 * 1024 * 1024
    TELEGRAM_ALLOWED_RECEIPT_MIME: str = (
        "image/jpeg,image/png,image/webp,image/heic,image/heif,application/pdf"
    )

    # Top-up bounds, in dirams (1 somoni = 100 dirams), matching the
    # existing balance column's unit.
    TELEGRAM_MIN_TOPUP_DIRAMS: int = GENERATION_PRICE_DIRAMS
    TELEGRAM_MAX_TOPUP_DIRAMS: int = 500_000

    # Preset buttons, expressed as generation counts rather than prices,
    # so they stay correct if GENERATION_PRICE_DIRAMS changes. See
    # topup_presets_dirams() — this deliberately derives from the existing
    # price instead of introducing a second, divergent price list.
    TELEGRAM_TOPUP_PRESET_GENERATIONS: str = "10,20,50,100"

    # Long-polling knobs.
    TELEGRAM_POLL_TIMEOUT_SECONDS: int = 25
    TELEGRAM_POLL_ERROR_BACKOFF_SECONDS: float = 3.0

    # How many days of processed-update ids to keep for replay protection.
    TELEGRAM_UPDATE_DEDUPE_RETENTION_DAYS: int = 3

    model_config = {
        # Later files win, so a gitignored .env.telegram overrides the
        # committed .env for every key it defines.
        "env_file": (".env", ".env.telegram"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def admin_ids(self) -> frozenset[int]:
        out: set[int] = set()
        for part in self.TELEGRAM_ADMIN_IDS.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                out.add(int(part))
            except ValueError:
                # A typo must not silently widen or narrow the admin set
                # in a way nobody notices; bot startup logs the count it
                # actually parsed.
                continue
        return frozenset(out)

    @property
    def allowed_receipt_mimes(self) -> frozenset[str]:
        return frozenset(
            m.strip().lower()
            for m in self.TELEGRAM_ALLOWED_RECEIPT_MIME.split(",")
            if m.strip()
        )

    def topup_presets_dirams(self) -> list[int]:
        out: list[int] = []
        for part in self.TELEGRAM_TOPUP_PRESET_GENERATIONS.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                count = int(part)
            except ValueError:
                continue
            if count > 0:
                out.append(count * GENERATION_PRICE_DIRAMS)
        return sorted(set(out))

    def is_admin(self, telegram_user_id: int | None) -> bool:
        return telegram_user_id is not None and telegram_user_id in self.admin_ids

    @property
    def configured(self) -> bool:
        return bool(self.TELEGRAM_BOT_TOKEN and self.TELEGRAM_BOT_USERNAME)

    @property
    def has_separate_admin_bot(self) -> bool:
        """True when reviews should go through their own bot.

        A token identical to the user bot's is treated as "no separate
        bot" rather than started twice — two pollers on one token fight
        over getUpdates and Telegram answers 409 to whichever asks
        second, which looks like the bot randomly ignoring people.
        """
        token = self.TELEGRAM_ADMIN_BOT_TOKEN.strip()
        return bool(token) and token != self.TELEGRAM_BOT_TOKEN.strip()

    @staticmethod
    def _token_state(token: str) -> str:
        if not token:
            return "MISSING"
        # The numeric prefix before ':' is the bot's own id and is public
        # (it is in every getMe response); the secret is the part after
        # it, which never appears here.
        return f"set (bot id {token.split(':', 1)[0]})"

    def redacted(self) -> str:
        """A safe one-line summary for logs and health output."""
        if self.has_separate_admin_bot:
            admin_state = self._token_state(self.TELEGRAM_ADMIN_BOT_TOKEN)
        elif self.TELEGRAM_ADMIN_BOT_TOKEN.strip():
            admin_state = "SAME AS USER BOT (ignored)"
        else:
            admin_state = "none (reviews go through the user bot)"
        return (
            f"token={self._token_state(self.TELEGRAM_BOT_TOKEN)} username="
            f"{self.TELEGRAM_BOT_USERNAME or 'MISSING'} "
            f"admin_bot={admin_state} "
            f"admin_lang={self.TELEGRAM_ADMIN_LANGUAGE} "
            f"admins={len(self.admin_ids)} "
            f"pay_instructions={'set' if self.TELEGRAM_PAY_INSTRUCTIONS else 'MISSING'}"
        )

    def deep_link(self, token: str) -> str:
        """The universal https link. Works without Telegram installed."""
        return f"https://t.me/{self.TELEGRAM_BOT_USERNAME}?start={token}"

    def app_link(self, token: str) -> str:
        """The native scheme, which needs no DNS at all.

        ``t.me`` is blocked by some ISPs in the region this product
        serves — measured on the developer's own connection, where
        api.telegram.org answers but t.me does not resolve. For those
        users the https link above is dead, and with it the entire
        account-linking flow.

        ``tg://`` is handled locally by the installed Telegram client,
        so it never performs a lookup and is unaffected by that
        blocking. It fails silently when Telegram is not installed,
        which is why both links are returned and the clients try this
        one first with the https link kept as the visible fallback.
        """
        return (
            f"tg://resolve?domain={self.TELEGRAM_BOT_USERNAME}&start={token}"
        )


@lru_cache
def get_telegram_settings() -> TelegramSettings:
    return TelegramSettings()
