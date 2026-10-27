"""Database side of the Telegram payment flow.

Everything that touches money lives here rather than in ``bot.py``, for
two reasons: the bot process is the least trusted part of the system (it
acts on input from strangers), and the rules below are the ones that need
tests more than anything else in this feature.

Deliberate design points
------------------------

**The bot shares the backend's database rather than calling it over
HTTP.** It runs from the same image and imports the same models, so there
is no new network surface, no internal service token to leak, and no
unauthenticated endpoint anywhere — which is what section 9 of the brief
asks for. The only HTTP route added by this feature is the one the *app*
calls to mint a link token, and that one is behind the normal JWT.

**A linking token is never stored.** Only ``sha256(token)`` is, exactly
as ``app.auth`` already does for refresh tokens. A database dump
therefore does not contain anything that can link an account.

**Approval is a compare-and-swap, not a read-then-write.** The status
transition and the balance update are one statement sequence in one
transaction, and the ``WHERE status = 'pending'`` clause is what makes a
double-click, a retried callback, a restart mid-flight and two admins
tapping at once all collapse to a single credit. Postgres re-evaluates
that clause against the committed row version after it unblocks
(EvalPlanQual under READ COMMITTED), so the loser of a race sees
``rowcount == 0`` and is told the request was already decided.

**The credited user comes from the request row, never from the caller.**
There is no code path in which a callback payload can redirect a credit
to a different account, which is why "admin approves a payment for
another user" is structurally impossible rather than merely checked.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import json
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import async_session
from app.limits import GENERATION_PRICE_DIRAMS
from app.logger import get_logger
from app.telegram.config import get_telegram_settings
from app.telegram.ocr import ReceiptScan, normalize_reference

logger = get_logger(__name__)

# Statuses a payment request can hold. "pending" means a receipt is in
# and an admin has not decided; it is the only status (with needs_info)
# from which a credit can happen.
STATUS_AWAITING_RECEIPT = "awaiting_receipt"
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_NEEDS_INFO = "needs_info"
STATUS_CANCELLED = "cancelled"

DECIDABLE = (STATUS_PENDING, STATUS_NEEDS_INFO)


# ---------------------------------------------------------------------
# Account linking
# ---------------------------------------------------------------------

def generate_link_token() -> str:
    """A 256-bit URL-safe token.

    ``secrets`` not ``random``: this value is the sole credential in the
    deep link. 32 bytes of CSPRNG output is not guessable, and the
    five-minute single-use window leaves nothing to brute-force.
    """
    return secrets.token_urlsafe(32)


def hash_link_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class IssuedLink:
    deep_link: str
    app_link: str
    start_command: str
    expires_at: datetime
    bot_username: str


@dataclass
class IssuedLinkCode:
    code: str
    expires_at: datetime


def hash_link_code(row_id: str, code: str) -> str:
    """Keyed, per-row hash so a database dump cannot brute-force 6 digits."""
    from app.config import get_settings

    message = f"telegram-link-code:{row_id}:{code}".encode()
    return hmac.new(get_settings().SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


async def issue_link_token(user_id: str, *, bot_username: str | None = None) -> IssuedLink:
    """Mint a single-use linking token for an already-authenticated user.

    The caller is responsible for having authenticated ``user_id`` — this
    function is only reachable from the JWT-guarded route and from tests.

    Any still-valid token the user holds is invalidated first, so a
    stale deep link left in a chat history stops working the moment a new
    one is requested.
    """
    settings = get_telegram_settings()
    raw = generate_link_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=settings.TELEGRAM_LINK_TOKEN_TTL_SECONDS
    )

    async with async_session() as db:
        conn = await db.connection()
        await conn.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:uid))"), {"uid": user_id}
        )
        await conn.execute(
            text(
                "UPDATE telegram_link_tokens SET used = TRUE, used_at = now() "
                "WHERE user_id = :uid AND used = FALSE"
            ),
            {"uid": user_id},
        )
        await conn.execute(
            text(
                "INSERT INTO telegram_link_tokens "
                "(id, user_id, token_hash, expires_at, used, created_at) "
                "VALUES (:id, :uid, :hash, :exp, FALSE, now())"
            ),
            {
                "id": str(uuid.uuid4()),
                "uid": user_id,
                "hash": hash_link_token(raw),
                "exp": expires_at,
            },
        )
        await db.commit()

    # user_id, not the token: the token is a live credential and the log
    # files in backend/logs/ persist.
    logger.info(f"Issued Telegram link token for user {user_id}, ttl "
                f"{settings.TELEGRAM_LINK_TOKEN_TTL_SECONDS}s")
    target_username = bot_username or settings.TELEGRAM_BOT_USERNAME
    return IssuedLink(
        deep_link=f"https://t.me/{target_username}?start={raw}",
        app_link=f"tg://resolve?domain={target_username}&start={raw}",
        start_command=f"/start {raw}",
        expires_at=expires_at,
        bot_username=target_username,
    )


async def issue_link_code(user_id: str) -> IssuedLinkCode:
    """Issue a five-minute, single-use six-digit code for authenticated linking."""
    settings = get_telegram_settings()

    code = f"{secrets.randbelow(1_000_000):06d}"
    row_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=min(
        300, settings.TELEGRAM_LINK_TOKEN_TTL_SECONDS
    ))
    async with async_session() as db:
        conn = await db.connection()
        await conn.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:uid))"), {"uid": user_id}
        )
        await conn.execute(
            text("UPDATE telegram_link_tokens SET used = TRUE, used_at = now() "
                 "WHERE user_id = :uid AND used = FALSE"),
            {"uid": user_id},
        )
        await conn.execute(
            text("INSERT INTO telegram_link_tokens "
                 "(id, user_id, token_hash, expires_at, used, created_at) "
                 "VALUES (:id, :uid, :hash, :exp, FALSE, now())"),
            {"id": row_id, "uid": user_id,
             "hash": hash_link_code(row_id, code), "exp": expires_at},
        )
        await db.commit()
    logger.info(f"Issued Telegram link code for user {user_id}, ttl "
                f"{min(300, settings.TELEGRAM_LINK_TOKEN_TTL_SECONDS)}s")
    return IssuedLinkCode(code=code, expires_at=expires_at)


@dataclass
class LinkedAccount:
    """The non-sensitive view of a linked Dastyor account.

    ``short_id`` and ``full_name`` only. No email, no phone, no password
    hash, no access token — the bot shows the teacher enough to recognise
    their own account and nothing that would be worth stealing from a
    chat history.
    """

    user_id: str
    short_id: str | None
    full_name: str
    language: str
    balance_dirams: int
    chat_id: int

    @property
    def label(self) -> str:
        return f"#{self.short_id} · {self.full_name}" if self.short_id else self.full_name


@dataclass
class RedeemResult:
    outcome: str  # linked | already_linked | invalid | expired | used | chat_taken
    account: LinkedAccount | None = None
    # True when this link activated an admin grant that was waiting for
    # the account to appear. The caller tells the new admin.
    became_admin: bool = False


async def account_for_chat(chat_id: int) -> LinkedAccount | None:
    async with async_session() as db:
        row = (await db.execute(
            text(
                "SELECT u.id, u.short_id, u.full_name, u.language, u.balance_dirams "
                "FROM telegram_accounts ta JOIN users u ON u.id = ta.user_id "
                "WHERE ta.chat_id = :chat AND ta.revoked = FALSE"
            ),
            {"chat": chat_id},
        )).first()
    if row is None:
        return None
    return LinkedAccount(
        user_id=row[0], short_id=row[1], full_name=row[2],
        language=row[3], balance_dirams=row[4], chat_id=chat_id,
    )


def normalize_username(raw: str | None) -> str | None:
    """Strip the @ and case-fold. Telegram usernames are case-insensitive."""
    if not raw:
        return None
    cleaned = raw.strip().lstrip("@").strip().lower()
    return cleaned or None


async def remember_username(telegram_user_id: int | None,
                            username: str | None) -> None:
    """Refresh the stored @username for a linked account.

    Called on every message, because a username can change at any time
    and the only moment we ever learn the new one is when its owner
    writes to the bot.
    """
    normalized = normalize_username(username)
    if telegram_user_id is None:
        return
    try:
        async with async_session() as db:
            await db.execute(
                text(
                    "UPDATE telegram_accounts SET username = :u, "
                    "  last_seen_at = now() "
                    "WHERE telegram_user_id = :tg AND revoked = FALSE "
                    "  AND (username IS DISTINCT FROM :u)"
                ),
                {"u": normalized, "tg": telegram_user_id},
            )
            await db.commit()
    except Exception as e:
        # Purely a convenience index for /addadmin. Never worth failing
        # a teacher's message over.
        logger.debug(f"Could not refresh username for {telegram_user_id}: {e}")


async def accounts_missing_username(limit: int = 200) -> list[tuple[int, int]]:
    """``(chat_id, telegram_user_id)`` for linked accounts with no username.

    Used by the startup backfill. Accounts that linked before usernames
    were recorded would otherwise stay invisible to ``/addadmin @name``
    until their owner happened to write to the bot again — which, for
    someone who already linked and is waiting to be made an admin, might
    be never.
    """
    async with async_session() as db:
        rows = (await db.execute(text(
            "SELECT chat_id, telegram_user_id FROM telegram_accounts "
            "WHERE revoked = FALSE AND username IS NULL "
            "  AND telegram_user_id IS NOT NULL LIMIT :lim"
        ), {"lim": limit})).all()
    return [(r[0], r[1]) for r in rows]


async def redeem_link_token(raw: str, chat_id: int,
                            telegram_user_id: int | None,
                            username: str | None = None) -> RedeemResult:
    """Validate a deep-link token and bind the chat to the account.

    Checked in this order, because each answer needs a different message
    to the user: unknown hash, already used, expired, chat already bound
    elsewhere. "Already used" is distinguished from "unknown" on purpose —
    it is the one case where the user may need to be told to change their
    password.
    """
    is_code = bool(re.fullmatch(r"[0-9]{6}", raw or ""))
    if not raw or (not is_code and len(raw) < 20):
        return RedeemResult(outcome="invalid")

    now = datetime.now(timezone.utc)

    async with async_session() as db:
        conn = await db.connection()

        if is_code:
            candidates = (await conn.execute(text(
                "SELECT id, token_hash FROM telegram_link_tokens "
                "WHERE used = FALSE AND expires_at >= :now"
            ), {"now": now})).all()
            token_id = next((candidate_id for candidate_id, stored_hash in candidates
                             if hmac.compare_digest(
                                 stored_hash, hash_link_code(candidate_id, raw))), None)
            row = (await conn.execute(text(
                "SELECT id, user_id, expires_at, used FROM telegram_link_tokens "
                "WHERE id = :id FOR UPDATE"
            ), {"id": token_id})).first() if token_id else None
        else:
            row = (await conn.execute(
                text(
                    "SELECT id, user_id, expires_at, used FROM telegram_link_tokens "
                    "WHERE token_hash = :hash FOR UPDATE"
                ),
                {"hash": hash_link_token(raw)},
            )).first()

        if row is None:
            await db.rollback()
            return RedeemResult(outcome="invalid")

        token_id, user_id, expires_at, used = row

        if used:
            await db.rollback()
            logger.warning(
                f"Telegram link token replay rejected for user {user_id} "
                f"from chat {chat_id}"
            )
            return RedeemResult(outcome="used")

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            # Burned even though it expired: an expired token must not
            # become usable again if the clock or the row is ever touched.
            await conn.execute(
                text("UPDATE telegram_link_tokens SET used = TRUE, used_at = now() "
                     "WHERE id = :id"),
                {"id": token_id},
            )
            await db.commit()
            return RedeemResult(outcome="expired")

        # Is this chat already bound to somebody else?
        existing_owner = (await conn.execute(
            text("SELECT user_id FROM telegram_accounts "
                 "WHERE chat_id = :chat AND revoked = FALSE"),
            {"chat": chat_id},
        )).scalar()

        if existing_owner is not None and existing_owner != user_id:
            await db.rollback()
            logger.warning(
                f"Telegram chat {chat_id} is linked to user {existing_owner}; "
                f"refused re-link to {user_id}"
            )
            return RedeemResult(outcome="chat_taken")

        await conn.execute(
            text(
                "UPDATE telegram_link_tokens "
                "SET used = TRUE, used_at = now(), used_by_chat_id = :chat "
                "WHERE id = :id"
            ),
            {"id": token_id, "chat": chat_id},
        )

        # One account per chat and one chat per account: re-linking the
        # same account from a new chat moves it rather than creating a
        # second row, so notifications never fan out to a stale chat.
        await conn.execute(
            text(
                "INSERT INTO telegram_accounts "
                "(id, user_id, chat_id, telegram_user_id, username, "
                " linked_at, last_seen_at, revoked) "
                "VALUES (:id, :uid, :chat, :tg, :uname, now(), now(), FALSE) "
                "ON CONFLICT (user_id) DO UPDATE SET "
                "  chat_id = EXCLUDED.chat_id, "
                "  telegram_user_id = EXCLUDED.telegram_user_id, "
                "  username = EXCLUDED.username, "
                "  last_seen_at = now(), revoked = FALSE"
            ),
            {
                "id": str(uuid.uuid4()),
                "uid": user_id,
                "chat": chat_id,
                "tg": telegram_user_id,
                "uname": normalize_username(username),
            },
        )

        account_row = (await conn.execute(
            text("SELECT id, short_id, full_name, language, balance_dirams "
                 "FROM users WHERE id = :uid"),
            {"uid": user_id},
        )).first()

        await db.commit()

    if account_row is None:
        return RedeemResult(outcome="invalid")

    logger.info(f"Linked Telegram chat {chat_id} to Dastyor user {user_id}")

    # A grant may have been waiting for exactly this moment. Done after
    # the link commits, and failure here must not undo the link — the
    # worst case is an admin who has to be re-added, not a teacher who
    # cannot use the bot.
    became_admin = False
    if telegram_user_id is not None:
        try:
            became_admin = await activate_pending_admin(user_id, telegram_user_id)
        except Exception as e:
            logger.error(
                f"Could not activate a pending admin grant for {user_id}: {e}"
            )

    return RedeemResult(
        outcome="linked",
        became_admin=became_admin,
        account=LinkedAccount(
            user_id=account_row[0], short_id=account_row[1],
            full_name=account_row[2], language=account_row[3],
            balance_dirams=account_row[4], chat_id=chat_id,
        ),
    )


@dataclass
class UnlinkResult:
    outcome: str  # unlinked | not_linked
    chat_id: int | None = None
    admin_revoked: bool = False
    open_requests: int = 0


async def unlink_account(*, user_id: str | None = None,
                         chat_id: int | None = None,
                         actor: str = "user") -> UnlinkResult:
    """Disconnect a Telegram chat from its Dastyor account.

    Reachable two ways, and both matter:

    * from the bot, by whoever holds the chat;
    * from the app or web, by whoever holds the Dastyor password — which
      is the path that still works when the Telegram account itself has
      been lost, sold with the phone, or taken over.

    The row is revoked, never deleted. Payment requests, receipts and
    the audit trail all reference it, and a money record that loses its
    subject is worse than one that keeps a disconnected one.

    Any admin grant riding on that Telegram id is revoked at the same
    time. The grant only existed because the link proved which Telegram
    account belonged to the Dastyor user; once that proof is withdrawn,
    the power it justified has to go with it.
    """
    if user_id is None and chat_id is None:
        raise ValueError("unlink_account needs user_id or chat_id")

    async with async_session() as db:
        conn = await db.connection()

        if chat_id is not None:
            row = (await conn.execute(text(
                "SELECT user_id, chat_id, telegram_user_id FROM telegram_accounts "
                "WHERE chat_id = :c AND revoked = FALSE"
            ), {"c": chat_id})).first()
        else:
            row = (await conn.execute(text(
                "SELECT user_id, chat_id, telegram_user_id FROM telegram_accounts "
                "WHERE user_id = :u AND revoked = FALSE"
            ), {"u": user_id})).first()

        if row is None:
            # No active link. When the caller named a Dastyor user we
            # still burn their outstanding link tokens: "disconnect my
            # Telegram" has to cancel a pending invitation too, or a
            # deep link requested moments earlier survives the very
            # action meant to sever everything.
            if user_id is not None:
                await conn.execute(text(
                    "UPDATE telegram_link_tokens "
                    "SET used = TRUE, used_at = now() "
                    "WHERE user_id = :u AND used = FALSE"
                ), {"u": user_id})
                await db.commit()
            else:
                await db.rollback()
            return UnlinkResult(outcome="not_linked")

        found_user, found_chat, telegram_user_id = row

        await conn.execute(text(
            "UPDATE telegram_accounts SET revoked = TRUE "
            "WHERE user_id = :u AND revoked = FALSE"
        ), {"u": found_user})

        # Unused link tokens die with the link, so a deep link left in a
        # chat history cannot silently re-establish it.
        await conn.execute(text(
            "UPDATE telegram_link_tokens SET used = TRUE, used_at = now() "
            "WHERE user_id = :u AND used = FALSE"
        ), {"u": found_user})

        admin_revoked = False
        if telegram_user_id is not None:
            result = await conn.execute(text(
                "UPDATE telegram_admins SET revoked = TRUE, revoked_at = now() "
                "WHERE revoked = FALSE AND (telegram_user_id = :tg "
                "   OR user_id = :u)"
            ), {"tg": telegram_user_id, "u": found_user})
            admin_revoked = (result.rowcount or 0) > 0

        # Requests already under review stay under review: the teacher
        # may well have sent real money, and dropping them would lose it.
        open_requests = (await conn.execute(text(
            "SELECT count(*) FROM payment_requests "
            "WHERE user_id = :u AND status IN (:p, :n, :a)"
        ), {"u": found_user, "p": STATUS_PENDING, "n": STATUS_NEEDS_INFO,
            "a": STATUS_AWAITING_RECEIPT})).scalar() or 0

        await db.commit()

    logger.warning(
        f"Telegram chat {found_chat} unlinked from Dastyor user {found_user} "
        f"by {actor}; admin_revoked={admin_revoked}, "
        f"open_requests={open_requests}"
    )
    return UnlinkResult(
        outcome="unlinked", chat_id=found_chat,
        admin_revoked=admin_revoked, open_requests=open_requests,
    )


PHONE_SHAPE = re.compile(r"^\+992\d{9}$")


def normalize_phone(raw: str | None) -> str | None:
    """Fold a typed phone into the stored ``+992XXXXXXXXX`` form.

    People type the number the way they say it — with spaces, dashes,
    a leading 992, or a local 9-digit form. Accepting only one spelling
    would make this path fail for most of the people it exists for.
    """
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 9:
        digits = "992" + digits
    elif digits.startswith("00992"):
        digits = digits[2:]
    candidate = "+" + digits
    return candidate if PHONE_SHAPE.match(candidate) else None


@dataclass
class PasswordLinkResult:
    outcome: str  # linked | bad_credentials | bad_phone | chat_taken | throttled
    account: LinkedAccount | None = None
    became_admin: bool = False


async def link_by_password(phone: str, password: str, chat_id: int,
                           telegram_user_id: int | None,
                           username: str | None = None) -> PasswordLinkResult:
    """Link a chat by Dastyor phone + password.

    An alternative to the deep link, added because ``t.me`` is blocked
    by ISPs in the region this serves, which makes every link form
    unusable there while Telegram itself keeps working.

    The password is used and discarded. It is never written to a column,
    never put in a log line, and never included in an exception message;
    the caller deletes the Telegram message carrying it as soon as this
    returns. Verification goes through the same ``app.auth`` bcrypt
    check the app and website use — there is no second, weaker password
    path.

    Failures are deliberately indistinguishable: a wrong password and an
    unknown phone both return ``bad_credentials``, so the bot cannot be
    used to discover which numbers are registered.
    """
    from app.auth import verify_password

    normalized = normalize_phone(phone)
    if normalized is None:
        return PasswordLinkResult(outcome="bad_phone")

    async with async_session() as db:
        conn = await db.connection()
        row = (await conn.execute(text(
            "SELECT id, hashed_password FROM users WHERE phone = :p"
        ), {"p": normalized})).first()

        existing_owner = (await conn.execute(text(
            "SELECT user_id FROM telegram_accounts "
            "WHERE chat_id = :c AND revoked = FALSE"
        ), {"c": chat_id})).scalar()

    # Always run a bcrypt comparison, even when the phone is unknown.
    # Returning early would make a missing account measurably faster
    # than a wrong password and turn this into a way to enumerate which
    # teachers are registered.
    stored_hash = row[1] if row else (
        "$2b$12$" + "." * 53  # structurally valid, matches nothing
    )
    try:
        ok = verify_password(password, stored_hash)
    except Exception:
        ok = False

    if row is None or not ok:
        logger.warning(
            f"Failed Telegram password login for {normalized} from chat {chat_id}"
        )
        return PasswordLinkResult(outcome="bad_credentials")

    user_id = row[0]

    if existing_owner is not None and existing_owner != user_id:
        return PasswordLinkResult(outcome="chat_taken")

    async with async_session() as db:
        conn = await db.connection()
        await conn.execute(text(
            "INSERT INTO telegram_accounts "
            "(id, user_id, chat_id, telegram_user_id, username, "
            " linked_at, last_seen_at, revoked) "
            "VALUES (:id, :uid, :chat, :tg, :uname, now(), now(), FALSE) "
            "ON CONFLICT (user_id) DO UPDATE SET "
            "  chat_id = EXCLUDED.chat_id, "
            "  telegram_user_id = EXCLUDED.telegram_user_id, "
            "  username = EXCLUDED.username, "
            "  last_seen_at = now(), revoked = FALSE"
        ), {
            "id": str(uuid.uuid4()), "uid": user_id, "chat": chat_id,
            "tg": telegram_user_id, "uname": normalize_username(username),
        })

        # Any outstanding deep-link token is spent: the account is
        # linked now, and a stale link must not re-bind it elsewhere.
        await conn.execute(text(
            "UPDATE telegram_link_tokens SET used = TRUE, used_at = now() "
            "WHERE user_id = :u AND used = FALSE"
        ), {"u": user_id})

        account_row = (await conn.execute(text(
            "SELECT id, short_id, full_name, language, balance_dirams "
            "FROM users WHERE id = :uid"
        ), {"uid": user_id})).first()
        await db.commit()

    became_admin = False
    if telegram_user_id is not None:
        try:
            became_admin = await activate_pending_admin(user_id, telegram_user_id)
        except Exception as e:
            logger.error(f"Pending admin activation failed for {user_id}: {e}")

    logger.info(
        f"Linked Telegram chat {chat_id} to Dastyor user {user_id} "
        f"by phone+password"
    )
    return PasswordLinkResult(
        outcome="linked",
        became_admin=became_admin,
        account=LinkedAccount(
            user_id=account_row[0], short_id=account_row[1],
            full_name=account_row[2], language=account_row[3],
            balance_dirams=account_row[4], chat_id=chat_id,
        ),
    )


async def link_status(user_id: str) -> dict:
    """What the app shows next to the Telegram button."""
    async with async_session() as db:
        row = (await db.execute(
            text("SELECT chat_id, linked_at FROM telegram_accounts "
                 "WHERE user_id = :uid AND revoked = FALSE"),
            {"uid": user_id},
        )).first()
    settings = get_telegram_settings()
    return {
        "linked": row is not None,
        "linked_at": row[1] if row else None,
        "bot_username": settings.TELEGRAM_BOT_USERNAME,
        "bot_configured": settings.configured,
    }


# ---------------------------------------------------------------------
# Payment requests
# ---------------------------------------------------------------------

@dataclass
class PaymentRequestView:
    id: str
    public_code: str
    user_id: str
    chat_id: int
    requested_dirams: int
    status: str
    credited_dirams: int = 0
    receipt_file_id: str | None = None
    receipt_mime: str | None = None
    ocr_confidence: int = 0
    ocr_warnings: list[str] = field(default_factory=list)
    reference_normalized: str | None = None
    created_at: datetime | None = None


def _new_public_code() -> str:
    """A short, speakable request id.

    Separate from the uuid primary key because this is the number a
    teacher reads out to support and an admin pastes into a chat; a uuid
    is unusable for that. Crockford-ish alphabet: no O/0 or I/1 confusion.
    """
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    body = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"DP-{body}"


async def create_payment_request(user_id: str, chat_id: int,
                                 requested_dirams: int) -> PaymentRequestView:
    """Open a request and return it, before any receipt exists.

    The id exists before the upload on purpose: the brief asks for a
    unique payment-request id created before a receipt is accepted, and
    it means an upload can always be attributed to exactly one request
    instead of being guessed at from timing.

    Any earlier request of this user's that is still waiting for a
    receipt is cancelled, so /pay twice does not leave two open requests
    that one receipt could plausibly belong to.
    """
    now_id = str(uuid.uuid4())

    async with async_session() as db:
        conn = await db.connection()

        await conn.execute(
            text(
                "UPDATE payment_requests SET status = :cancelled, updated_at = now() "
                "WHERE user_id = :uid AND status = :awaiting"
            ),
            {"cancelled": STATUS_CANCELLED, "uid": user_id,
             "awaiting": STATUS_AWAITING_RECEIPT},
        )

        code = None
        for _ in range(12):
            candidate = _new_public_code()
            clash = (await conn.execute(
                text("SELECT 1 FROM payment_requests WHERE public_code = :code"),
                {"code": candidate},
            )).scalar()
            if clash is None:
                code = candidate
                break
        if code is None:
            raise RuntimeError("could not allocate a unique payment request code")

        await conn.execute(
            text(
                "INSERT INTO payment_requests "
                "(id, public_code, user_id, chat_id, requested_dirams, status, "
                " credited_dirams, ocr_confidence, created_at, updated_at) "
                "VALUES (:id, :code, :uid, :chat, :amt, :status, 0, 0, now(), now())"
            ),
            {"id": now_id, "code": code, "uid": user_id, "chat": chat_id,
             "amt": requested_dirams, "status": STATUS_AWAITING_RECEIPT},
        )
        await _audit(conn, now_id, "created", "user", actor_user_id=user_id,
                     detail={"requested_dirams": requested_dirams})
        await db.commit()

    logger.info(
        f"Payment request {code} opened for user {user_id}: "
        f"{requested_dirams} dirams requested"
    )
    return PaymentRequestView(
        id=now_id, public_code=code, user_id=user_id, chat_id=chat_id,
        requested_dirams=requested_dirams, status=STATUS_AWAITING_RECEIPT,
    )


async def open_request_for_user(user_id: str) -> PaymentRequestView | None:
    """The request a newly uploaded receipt belongs to, if any."""
    async with async_session() as db:
        row = (await db.execute(
            text(
                "SELECT id, public_code, user_id, chat_id, requested_dirams, status, "
                "       credited_dirams, created_at "
                "FROM payment_requests "
                "WHERE user_id = :uid AND status IN (:awaiting, :needs_info) "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"uid": user_id, "awaiting": STATUS_AWAITING_RECEIPT,
             "needs_info": STATUS_NEEDS_INFO},
        )).first()
    if row is None:
        return None
    return PaymentRequestView(
        id=row[0], public_code=row[1], user_id=row[2], chat_id=row[3],
        requested_dirams=row[4], status=row[5], credited_dirams=row[6],
        created_at=row[7],
    )


async def get_request(request_id: str) -> PaymentRequestView | None:
    async with async_session() as db:
        row = (await db.execute(
            text(
                "SELECT id, public_code, user_id, chat_id, requested_dirams, status, "
                "       credited_dirams, receipt_file_id, receipt_mime, "
                "       ocr_confidence, ocr_warnings, reference_normalized, created_at "
                "FROM payment_requests WHERE id = :id"
            ),
            {"id": request_id},
        )).first()
    if row is None:
        return None
    return PaymentRequestView(
        id=row[0], public_code=row[1], user_id=row[2], chat_id=row[3],
        requested_dirams=row[4], status=row[5], credited_dirams=row[6],
        receipt_file_id=row[7], receipt_mime=row[8], ocr_confidence=row[9],
        ocr_warnings=json.loads(row[10]) if row[10] else [],
        reference_normalized=row[11], created_at=row[12],
    )


async def find_duplicate_reference(reference_normalized: str | None,
                                   exclude_request_id: str) -> str | None:
    """The public code of an earlier request carrying the same reference.

    Looks at approved and pending rows only. A rejected or cancelled
    request's reference is not a duplicate worth flagging — the money
    never counted, and flagging it would train the admin to ignore the
    warning that matters.
    """
    if not reference_normalized:
        return None
    async with async_session() as db:
        return (await db.execute(
            text(
                "SELECT public_code FROM payment_requests "
                "WHERE reference_normalized = :ref AND id <> :id "
                "  AND status IN (:approved, :pending) "
                "ORDER BY created_at LIMIT 1"
            ),
            {"ref": reference_normalized, "id": exclude_request_id,
             "approved": STATUS_APPROVED, "pending": STATUS_PENDING},
        )).scalar()


async def attach_receipt(request_id: str, *, file_id: str, mime: str | None,
                         size_bytes: int | None, scan: ReceiptScan,
                         stored_path: str | None = None) -> str | None:
    """Record the receipt and its scan, and move the request to pending.

    Returns the public code of a duplicate-reference request if there is
    one, so the caller can put it in front of the admin.

    The status change is guarded the same way approval is: only a request
    still waiting for a receipt (or sent back for more information) can
    receive one, so a late second upload cannot re-open a decided
    request.
    """
    reference_norm = normalize_reference(scan.reference)
    duplicate_of = await find_duplicate_reference(reference_norm, request_id)
    if duplicate_of and "reference_duplicate" not in scan.warnings:
        scan.add_warning("reference_duplicate")

    async with async_session() as db:
        conn = await db.connection()
        result = await conn.execute(
            text(
                "UPDATE payment_requests SET "
                "  status = :pending, "
                "  receipt_file_id = :file_id, receipt_path = :path, "
                "  receipt_mime = :mime, receipt_bytes = :size, "
                "  ocr_amount_dirams = :amount, ocr_currency = :currency, "
                "  ocr_sender = :sender, ocr_recipient = :recipient, "
                "  ocr_reference = :reference, ocr_paid_at_text = :paid_at, "
                "  ocr_status_text = :status_text, ocr_confidence = :confidence, "
                "  ocr_engine = :engine, ocr_warnings = :warnings, "
                "  ocr_raw_text = :raw_text, reference_normalized = :ref_norm, "
                "  updated_at = now() "
                "WHERE id = :id AND status IN (:awaiting, :needs_info)"
            ),
            {
                "id": request_id,
                "pending": STATUS_PENDING,
                "awaiting": STATUS_AWAITING_RECEIPT,
                "needs_info": STATUS_NEEDS_INFO,
                "file_id": file_id,
                "path": stored_path,
                "mime": mime,
                "size": size_bytes,
                "amount": scan.amount_dirams,
                "currency": scan.currency,
                "sender": (scan.sender or None),
                "recipient": (scan.recipient or None),
                "reference": (scan.reference or None),
                "paid_at": (scan.paid_at_text or None),
                "status_text": (scan.status_text or None),
                "confidence": scan.confidence,
                "engine": scan.engine,
                "warnings": json.dumps(scan.warnings, ensure_ascii=False),
                "raw_text": scan.raw_text[:8000] if scan.raw_text else None,
                "ref_norm": reference_norm,
            },
        )
        if result.rowcount != 1:
            await db.rollback()
            raise RequestNotOpen(request_id)

        await _audit(
            conn, request_id, "receipt_attached", "user",
            detail={
                "mime": mime,
                "size_bytes": size_bytes,
                "ocr_engine": scan.engine,
                "ocr_confidence": scan.confidence,
                "ocr_warnings": scan.warnings,
                "ocr_amount_dirams": scan.amount_dirams,
                "duplicate_of": duplicate_of,
            },
        )
        await db.commit()

    logger.info(
        f"Receipt attached to payment request {request_id}: engine={scan.engine} "
        f"confidence={scan.confidence} warnings={scan.warnings} "
        f"duplicate_of={duplicate_of}"
    )
    return duplicate_of


class RequestNotOpen(RuntimeError):
    def __init__(self, request_id: str):
        self.request_id = request_id
        super().__init__(f"payment request {request_id} is not open for this change")


# ---------------------------------------------------------------------
# Admin decisions
# ---------------------------------------------------------------------

@dataclass
class DecisionResult:
    outcome: str  # applied | already_decided | not_found | duplicate_reference | amount_conflict
    request: PaymentRequestView | None = None
    credited_dirams: int = 0
    new_balance_dirams: int = 0
    previous_status: str | None = None


async def _audit(conn, request_id: str, event: str, actor_kind: str, *,
                 actor_telegram_id: int | None = None,
                 actor_user_id: str | None = None,
                 detail: dict | None = None) -> None:
    """Append-only audit row.

    Written inside the caller's transaction so an audit entry can never
    exist for a credit that rolled back, nor a credit without its entry.
    Nothing in this module ever updates or deletes from this table.
    """
    await conn.execute(
        text(
            "INSERT INTO payment_audit_log "
            "(id, payment_request_id, event, actor_kind, actor_telegram_id, "
            " actor_user_id, detail, created_at) "
            "VALUES (:id, :req, :event, :kind, :tg, :uid, :detail, now())"
        ),
        {
            "id": str(uuid.uuid4()),
            "req": request_id,
            "event": event,
            "kind": actor_kind,
            "tg": actor_telegram_id,
            "uid": actor_user_id,
            "detail": json.dumps(detail or {}, ensure_ascii=False, default=str),
        },
    )


async def approve_payment(request_id: str, admin_telegram_id: int | None, *,
                          admin_user_id: str | None = None,
                          amount_override_dirams: int | None = None,
                          correction_reason: str | None = None) -> DecisionResult:
    """Credit the balance for a reviewed request, exactly once.

    Caller must already have checked that the acting admin is an
    administrator; this function records who acted but does not decide
    who may. The bot checks authorization before calling (tested
    separately); the web CRM's require_permission dependency does the
    same for ``admin_user_id`` callers.

    ``admin_telegram_id`` is the bot's caller shape and stays required
    in practice — every existing call site passes a real id. It is
    typed ``| None`` only so the CRM can call this directly for a web
    admin who has no linked Telegram chat at all: pass ``None`` here and
    the Dastyor user id as ``admin_user_id`` instead. Exactly one of the
    two should be set; the audit row and ledger reason record whichever
    one is.

    ``amount_override_dirams`` exists for the audited correction case the
    brief calls for — an admin who sees a receipt for a different figure
    than the teacher typed. It requires ``correction_reason``, is logged
    as its own event, and is **not** wired to any inline button: the
    one-tap path can only ever credit the amount that was reviewed.
    """
    if amount_override_dirams is not None:
        if correction_reason is None or not correction_reason.strip():
            return DecisionResult(outcome="amount_conflict")
        if amount_override_dirams <= 0:
            return DecisionResult(outcome="amount_conflict")

    # Segregation of duties, scaled to who the admin is.
    #
    # A GRANTED admin must not approve their own payment: promoting a
    # teacher would otherwise hand them an unlimited self-top-up, which
    # turns a convenience into the single worst hole in the system.
    #
    # A ROOT admin may, because they are the owner of the service and a
    # one-person operation would otherwise be unable to credit itself at
    # all. It is still recorded as its own audit event, so the ledger
    # never hides that the approver and the beneficiary were the same
    # person.
    settings = get_telegram_settings()
    self_approval = False
    existing = await get_request(request_id)
    if existing is not None and existing.chat_id == admin_telegram_id:
        self_approval = True
        if not settings.is_admin(admin_telegram_id):
            logger.warning(
                f"Granted admin {admin_telegram_id} tried to approve their "
                f"OWN request {existing.public_code}; refused"
            )
            return DecisionResult(outcome="self_approval", request=existing)

    actor_label = (
        f"telegram admin {admin_telegram_id}" if admin_telegram_id is not None
        else f"web admin {admin_user_id}"
    )

    async with async_session() as db:
        conn = await db.connection()
        try:
            # The compare-and-swap. Everything about not double-crediting
            # rests on this single statement: the row is locked, the
            # status is re-checked against the committed version, and the
            # loser of any race gets rowcount 0.
            row = (await conn.execute(
                text(
                    "UPDATE payment_requests SET "
                    "  status = :approved, "
                    "  decided_by_telegram_id = :admin, decided_at = now(), "
                    "  decision_note = :note, updated_at = now() "
                    "WHERE id = :id AND status IN (:pending, :needs_info) "
                    "RETURNING user_id, public_code, requested_dirams, chat_id, "
                    "          reference_normalized"
                ),
                {
                    "id": request_id,
                    "approved": STATUS_APPROVED,
                    "admin": admin_telegram_id,
                    "note": correction_reason,
                    "pending": STATUS_PENDING,
                    "needs_info": STATUS_NEEDS_INFO,
                },
            )).first()

            if row is None:
                await db.rollback()
                current = await get_request(request_id)
                if current is None:
                    return DecisionResult(outcome="not_found")
                logger.info(
                    f"Approve ignored for {current.public_code}: already "
                    f"{current.status} (admin {admin_telegram_id})"
                )
                return DecisionResult(
                    outcome="already_decided", request=current,
                    previous_status=current.status,
                )

            user_id, public_code, requested_dirams, chat_id, reference_norm = row
            amount = amount_override_dirams or requested_dirams

            # Credit. RETURNING gives the post-update balance, so
            # balance_before is derived rather than read separately —
            # a separate read could see a different value under load.
            new_balance = (await conn.execute(
                text(
                    "UPDATE users SET balance_dirams = balance_dirams + :amt "
                    "WHERE id = :uid RETURNING balance_dirams"
                ),
                {"uid": user_id, "amt": amount},
            )).scalar()

            if new_balance is None:
                # The account is gone. Roll the whole thing back rather
                # than leaving an approved request with no credit behind
                # it: a half-applied approval is worse than none.
                await db.rollback()
                logger.error(
                    f"Approve failed for {public_code}: user {user_id} no longer exists"
                )
                return DecisionResult(outcome="not_found")

            tx_id = str(uuid.uuid4())
            await conn.execute(
                text(
                    "INSERT INTO balance_transactions "
                    "(id, user_id, kind, amount_dirams, balance_before, balance_after, "
                    " actor_id, reason, material_type, created_at) "
                    "VALUES (:id, :uid, 'topup', :amt, :before, :after, "
                    "        NULL, :reason, NULL, now())"
                ),
                {
                    "id": tx_id,
                    "uid": user_id,
                    "amt": amount,
                    "before": new_balance - amount,
                    "after": new_balance,
                    # actor_id is a users.id FK and a Telegram admin need
                    # not have a Dastyor account, so the acting identity
                    # goes in reason, where the existing admin
                    # balance-history screen already shows it.
                    "reason": (
                        f"telegram payment {public_code} approved by {actor_label}"
                        + (" (SELF-APPROVED)" if self_approval else "")
                    ),
                },
            )

            await conn.execute(
                text(
                    "UPDATE payment_requests SET credited_dirams = :amt, "
                    "  balance_transaction_id = :tx WHERE id = :id"
                ),
                {"amt": amount, "tx": tx_id, "id": request_id},
            )

            if amount_override_dirams:
                event = "approved_with_correction"
            elif self_approval:
                # Its own event so a reader of the audit log never has
                # to cross-reference to notice it.
                event = "approved_self"
            else:
                event = "approved"

            await _audit(
                conn, request_id, event,
                "admin" if admin_telegram_id is not None else "admin_web",
                actor_telegram_id=admin_telegram_id,
                actor_user_id=admin_user_id,
                detail={
                    "requested_dirams": requested_dirams,
                    "credited_dirams": amount,
                    "balance_after": new_balance,
                    "balance_transaction_id": tx_id,
                    "correction_reason": correction_reason,
                    "self_approval": self_approval,
                },
            )

            await db.commit()

        except IntegrityError as e:
            # The partial unique index on (reference_normalized) WHERE
            # status='approved' fired: this bank reference has already
            # been credited on another request. Nothing is applied.
            await db.rollback()
            logger.warning(
                f"Approve rejected for request {request_id}: duplicate approved "
                f"reference ({type(e).__name__})"
            )
            current = await get_request(request_id)
            return DecisionResult(outcome="duplicate_reference", request=current)

    logger.info(
        f"Payment {public_code} approved by {actor_label}: "
        f"credited {amount} dirams to user {user_id}, new balance {new_balance}"
    )
    updated = await get_request(request_id)
    return DecisionResult(
        outcome="applied", request=updated, credited_dirams=amount,
        new_balance_dirams=new_balance, previous_status=STATUS_PENDING,
    )


async def _decide_without_credit(request_id: str, admin_telegram_id: int | None,
                                 new_status: str, event: str,
                                 note: str | None = None, *,
                                 admin_user_id: str | None = None) -> DecisionResult:
    """Shared body of reject and request-more-info.

    Same compare-and-swap as approval, and deliberately no balance
    statement at all: there is no code path here that could touch
    ``users.balance_dirams``.

    ``admin_telegram_id``/``admin_user_id`` follow approve_payment's
    convention: pass the Dastyor user id instead when the caller is a
    web admin with no linked Telegram chat.
    """
    async with async_session() as db:
        conn = await db.connection()
        row = (await conn.execute(
            text(
                "UPDATE payment_requests SET status = :new_status, "
                "  decided_by_telegram_id = :admin, decided_at = now(), "
                "  decision_note = :note, updated_at = now() "
                "WHERE id = :id AND status IN (:pending, :needs_info) "
                "RETURNING public_code, user_id, requested_dirams, chat_id"
            ),
            {
                "id": request_id, "new_status": new_status,
                "admin": admin_telegram_id, "note": note,
                "pending": STATUS_PENDING, "needs_info": STATUS_NEEDS_INFO,
            },
        )).first()

        if row is None:
            await db.rollback()
            current = await get_request(request_id)
            if current is None:
                return DecisionResult(outcome="not_found")
            return DecisionResult(outcome="already_decided", request=current,
                                  previous_status=current.status)

        await _audit(conn, request_id, event,
                     "admin" if admin_telegram_id is not None else "admin_web",
                     actor_telegram_id=admin_telegram_id,
                     actor_user_id=admin_user_id,
                     detail={"note": note, "status": new_status})
        await db.commit()

    actor_label = (
        f"telegram admin {admin_telegram_id}" if admin_telegram_id is not None
        else f"web admin {admin_user_id}"
    )
    logger.info(f"Payment {row[0]} set to {new_status} by {actor_label}")
    return DecisionResult(outcome="applied", request=await get_request(request_id))


async def reject_payment(request_id: str, admin_telegram_id: int | None,
                         note: str | None = None, *,
                         admin_user_id: str | None = None) -> DecisionResult:
    return await _decide_without_credit(
        request_id, admin_telegram_id, STATUS_REJECTED, "rejected", note,
        admin_user_id=admin_user_id,
    )


async def request_more_info(request_id: str, admin_telegram_id: int | None,
                            note: str | None = None, *,
                            admin_user_id: str | None = None) -> DecisionResult:
    """Send a request back for a better receipt, leaving it decidable.

    Lands in ``needs_info``, which is still in ``DECIDABLE``: the teacher
    can upload again and the admin can still approve or reject later. The
    balance is untouched and the original receipt row and audit trail
    stay exactly as they were.
    """
    return await _decide_without_credit(
        request_id, admin_telegram_id, STATUS_NEEDS_INFO, "more_info_requested", note,
        admin_user_id=admin_user_id,
    )


async def list_requests(user_id: str, limit: int = 8) -> list[PaymentRequestView]:
    async with async_session() as db:
        rows = (await db.execute(
            text(
                "SELECT id, public_code, user_id, chat_id, requested_dirams, status, "
                "       credited_dirams, created_at "
                "FROM payment_requests WHERE user_id = :uid "
                "ORDER BY created_at DESC LIMIT :lim"
            ),
            {"uid": user_id, "lim": limit},
        )).all()
    return [
        PaymentRequestView(
            id=r[0], public_code=r[1], user_id=r[2], chat_id=r[3],
            requested_dirams=r[4], status=r[5], credited_dirams=r[6],
            created_at=r[7],
        )
        for r in rows
    ]


@dataclass
class PendingReview:
    """A request waiting for a human decision, as the admin needs to see it."""

    id: str
    public_code: str
    user_id: str
    chat_id: int
    short_id: str | None
    full_name: str
    requested_dirams: int
    status: str
    created_at: datetime
    receipt_file_id: str | None
    ocr_confidence: int
    ocr_warnings: list[str]

    def age_hours(self, now: datetime | None = None) -> float:
        now = now or datetime.now(timezone.utc)
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return max(0.0, (now - created).total_seconds() / 3600)


async def list_pending_reviews(limit: int = 20) -> list[PendingReview]:
    """Everything awaiting an admin decision, oldest first.

    This is the safety net under the notification path. A review message
    can fail to arrive — the admin blocked the bot, the network dropped,
    the process restarted mid-send — and until now that left the request
    sitting in the database with nothing pointing at it. The row was
    always safe; it was simply unreachable.

    Oldest first because the one that has waited longest is the one a
    teacher is most likely chasing.
    """
    async with async_session() as db:
        rows = (await db.execute(text(
            "SELECT pr.id, pr.public_code, pr.user_id, pr.chat_id, "
            "       u.short_id, u.full_name, pr.requested_dirams, pr.status, "
            "       pr.created_at, pr.receipt_file_id, pr.ocr_confidence, "
            "       pr.ocr_warnings "
            "FROM payment_requests pr JOIN users u ON u.id = pr.user_id "
            "WHERE pr.status IN (:pending, :needs_info) "
            "ORDER BY pr.created_at LIMIT :lim"
        ), {"pending": STATUS_PENDING, "needs_info": STATUS_NEEDS_INFO,
            "lim": limit})).all()

    out: list[PendingReview] = []
    for r in rows:
        try:
            warnings = json.loads(r[11]) if r[11] else []
        except ValueError:
            warnings = []
        out.append(PendingReview(
            id=r[0], public_code=r[1], user_id=r[2], chat_id=r[3],
            short_id=r[4], full_name=r[5], requested_dirams=r[6],
            status=r[7], created_at=r[8], receipt_file_id=r[9],
            ocr_confidence=r[10], ocr_warnings=warnings,
        ))
    return out


async def count_pending_reviews() -> int:
    async with async_session() as db:
        return (await db.execute(text(
            "SELECT count(*) FROM payment_requests WHERE status IN "
            "(:pending, :needs_info)"
        ), {"pending": STATUS_PENDING, "needs_info": STATUS_NEEDS_INFO})).scalar() or 0


async def current_balance_dirams(user_id: str) -> int:
    async with async_session() as db:
        return (await db.execute(
            text("SELECT balance_dirams FROM users WHERE id = :uid"),
            {"uid": user_id},
        )).scalar() or 0


async def record_admin_message(request_id: str, messages: list[dict]) -> None:
    """Remember which admin chats got which message, to edit buttons later."""
    async with async_session() as db:
        await db.execute(
            text("UPDATE payment_requests SET admin_message_json = :payload "
                 "WHERE id = :id"),
            {"payload": json.dumps(messages), "id": request_id},
        )
        await db.commit()


async def admin_messages(request_id: str) -> list[dict]:
    async with async_session() as db:
        raw = (await db.execute(
            text("SELECT admin_message_json FROM payment_requests WHERE id = :id"),
            {"id": request_id},
        )).scalar()
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except ValueError:
        return []


# ---------------------------------------------------------------------
# Administrators
# ---------------------------------------------------------------------
#
# Two sources, deliberately unequal:
#
#   root    TELEGRAM_ADMIN_IDS from the environment. The bootstrap set.
#           Cannot be revoked through the bot, so no sequence of in-bot
#           actions can lock the owner out of their own reviews.
#   granted rows in telegram_admins, added by an existing admin.
#
# Authorization is the union. Revocation only ever touches the second.


@dataclass
class AdminEntry:
    telegram_user_id: int | None
    is_root: bool
    user_id: str | None = None
    short_id: str | None = None
    full_name: str | None = None
    added_by_telegram_id: int | None = None
    added_at: datetime | None = None

    @property
    def pending(self) -> bool:
        """Granted, but the account has not linked Telegram yet.

        A pending admin holds no power at all until they link: there is
        no Telegram id for a callback to match, so they cannot approve
        anything. It is a standing instruction, not an active grant.
        """
        return self.telegram_user_id is None


async def granted_admin_ids() -> set[int]:
    """Telegram ids of every linked account whose Dastyor User.role is
    'admin' right now.

    This used to read the telegram_admins table directly. It now
    resolves through TelegramAccount -> User instead, so an admin's bot
    authority follows the same User.role the web CRM edits - grant or
    revoke it on the web, and the bot side is already correct on the
    very next check, nothing else to keep in sync.

    telegram_admins is still written (add_admin_by_short_id/remove_admin
    flip User.role/admin_tier at the same time they touch that table)
    but is no longer read here. See its own docstring in models.py for
    what it is still for: pending grants and history.
    """
    async with async_session() as db:
        rows = (await db.execute(text(
            "SELECT ta.telegram_user_id FROM telegram_accounts ta "
            "JOIN users u ON u.id = ta.user_id "
            "WHERE ta.revoked = FALSE AND ta.telegram_user_id IS NOT NULL "
            "AND u.role = 'admin'"
        ))).scalars().all()
    return set(rows)


async def all_admin_ids() -> set[int]:
    """Everyone who may approve a payment right now."""
    settings = get_telegram_settings()
    try:
        granted = await granted_admin_ids()
    except Exception as e:
        # A database hiccup must not silently widen or narrow the admin
        # set without anyone noticing. Fall back to the root set, which
        # is the conservative direction, and say so.
        logger.error(f"Could not read granted admins, using root set only: {e}")
        granted = set()
    return set(settings.admin_ids) | granted


async def is_admin(telegram_user_id: int | None) -> bool:
    if telegram_user_id is None:
        return False
    settings = get_telegram_settings()
    if settings.is_admin(telegram_user_id):
        return True
    return telegram_user_id in await granted_admin_ids()


async def list_admins() -> list[AdminEntry]:
    settings = get_telegram_settings()
    entries = [
        AdminEntry(telegram_user_id=tg_id, is_root=True)
        for tg_id in sorted(settings.admin_ids)
    ]
    async with async_session() as db:
        rows = (await db.execute(text(
            "SELECT ta.telegram_user_id, ta.user_id, u.short_id, u.full_name, "
            "       ta.added_by_telegram_id, ta.added_at "
            "FROM telegram_admins ta LEFT JOIN users u ON u.id = ta.user_id "
            "WHERE ta.revoked = FALSE "
            "ORDER BY ta.telegram_user_id IS NULL, ta.added_at"
        ))).all()
    for r in rows:
        if r[0] is not None and r[0] in settings.admin_ids:
            # Also a root admin; already listed, and root wins.
            continue
        entries.append(AdminEntry(
            telegram_user_id=r[0], is_root=False, user_id=r[1],
            short_id=r[2], full_name=r[3],
            added_by_telegram_id=r[4], added_at=r[5],
        ))
    return entries


@dataclass
class AdminChangeResult:
    outcome: str  # added | removed | already | not_found | not_linked | is_root | last_admin
    entry: AdminEntry | None = None


async def add_admin_by_short_id(identifier: str, actor_telegram_id: int,
                                note: str | None = None,
                                tier: str | None = None) -> AdminChangeResult:
    """Promote a Dastyor account by @username or by 6-digit short id.

    Both forms resolve to the same thing: a Dastyor ``users`` row whose
    Telegram id (if any) came from that account's own verified link —
    which only its owner could have created, since linking needs a token
    minted for an authenticated session.

    On @username: the Bot API has no method to look a user up by
    username, so this resolves against ``telegram_accounts.username``,
    captured when that person wrote to the bot. Two consequences worth
    knowing:

    * only people who have linked can be found by username — nobody
      else's is known to us;
    * the stored copy can be stale, so a name released by one person and
      taken by another still resolves to whoever linked. That is the
      safe direction (it never grants the newcomer), but it can surprise,
      which is why the confirmation echoes the real name and short id.

    The grant itself is always keyed on telegram_user_id, never on the
    name.
    """
    raw = (identifier or "").strip()
    short_id = raw.lstrip("#")

    async with async_session() as db:
        conn = await db.connection()

        if short_id.isdigit():
            row = (await conn.execute(text(
                "SELECT u.id, u.short_id, u.full_name, ta.telegram_user_id "
                "FROM users u "
                "LEFT JOIN telegram_accounts ta "
                "  ON ta.user_id = u.id AND ta.revoked = FALSE "
                "WHERE u.short_id = :sid"
            ), {"sid": short_id})).first()
        else:
            username = normalize_username(raw)
            if not username:
                await db.rollback()
                return AdminChangeResult(outcome="not_found")
            row = (await conn.execute(text(
                "SELECT u.id, u.short_id, u.full_name, ta.telegram_user_id "
                "FROM telegram_accounts ta JOIN users u ON u.id = ta.user_id "
                "WHERE ta.username = :uname AND ta.revoked = FALSE"
            ), {"uname": username})).first()
            if row is None:
                await db.rollback()
                return AdminChangeResult(outcome="username_unknown")

        if row is None:
            await db.rollback()
            return AdminChangeResult(outcome="not_found")

        user_id, found_short, full_name, telegram_user_id = row

        # An unlinked account is granted PENDING rather than refused.
        # The owner should not have to wait for somebody to open the bot
        # and then remember to come back. Nothing is weakened: a pending
        # grant carries no Telegram id, so it authorizes nothing until
        # the account links and proves which Telegram account it is.
        already = (await conn.execute(text(
            "SELECT 1 FROM telegram_admins "
            "WHERE user_id = :uid AND revoked = FALSE"
        ), {"uid": user_id})).scalar()
        if already:
            await db.rollback()
            return AdminChangeResult(outcome="already")

        if telegram_user_id is not None:
            clash = (await conn.execute(text(
                "SELECT 1 FROM telegram_admins "
                "WHERE telegram_user_id = :tg AND revoked = FALSE"
            ), {"tg": telegram_user_id})).scalar()
            if clash:
                await db.rollback()
                return AdminChangeResult(outcome="already")

        await conn.execute(text(
            "INSERT INTO telegram_admins "
            "(id, telegram_user_id, user_id, added_by_telegram_id, added_at, "
            " activated_at, revoked, note) "
            "VALUES (:id, :tg, :uid, :actor, now(), :activated, FALSE, :note)"
        ), {
            "id": str(uuid.uuid4()),
            "tg": telegram_user_id,
            "uid": user_id,
            "actor": actor_telegram_id,
            "activated": datetime.now(timezone.utc) if telegram_user_id else None,
            "note": note,
        })

        # The grant's real authority is User.role (granted_admin_ids()
        # reads through it, not telegram_admins) - so this has to happen
        # in the same transaction as the row above, not as a follow-up
        # step that could fail or be skipped. Defaults a genuinely new
        # admin to 'support'; COALESCE means an account that is already
        # an admin with a tier (e.g. promoted directly from the CRM
        # worklist) keeps that tier instead of being downgraded by a
        # second, redundant grant.
        from app.admin_roles import ADMIN_TIERS
        tier_sql = "COALESCE(admin_tier, 'support')"
        params = {"uid": user_id}
        if tier in ADMIN_TIERS:
            tier_sql = ":tier"
            params["tier"] = tier
        await conn.execute(text(
            f"UPDATE users SET role = 'admin', admin_tier = {tier_sql} "
            "WHERE id = :uid"
        ), params)

        await _admin_audit(
            conn,
            "admin_granted" if telegram_user_id else "admin_granted_pending",
            actor_telegram_id,
            {
                "telegram_user_id": telegram_user_id,
                "dastyor_user_id": user_id,
                "short_id": found_short,
                "note": note,
                "tier": tier if tier in ADMIN_TIERS else "support",
            },
        )
        await db.commit()

    state = "GRANTED" if telegram_user_id else "GRANTED (pending link)"
    logger.warning(
        f"Telegram admin {state} to Dastyor #{found_short} "
        f"(telegram {telegram_user_id}) by admin {actor_telegram_id}"
    )
    return AdminChangeResult(
        outcome="added" if telegram_user_id else "added_pending",
        entry=AdminEntry(
            telegram_user_id=telegram_user_id, is_root=False, user_id=user_id,
            short_id=found_short, full_name=full_name,
            added_by_telegram_id=actor_telegram_id,
        ),
    )


async def activate_pending_admin(user_id: str, telegram_user_id: int) -> bool:
    """Fill in the Telegram id on a pending grant, at link time.

    Called from ``redeem_link_token``. Returns True when a pending grant
    was activated, so the caller can tell the new admin.
    """
    async with async_session() as db:
        conn = await db.connection()
        result = await conn.execute(text(
            "UPDATE telegram_admins "
            "SET telegram_user_id = :tg, activated_at = now() "
            "WHERE user_id = :uid AND revoked = FALSE "
            "  AND telegram_user_id IS NULL"
        ), {"tg": telegram_user_id, "uid": user_id})

        if result.rowcount != 1:
            await db.rollback()
            return False

        await _admin_audit(conn, "admin_activated", telegram_user_id, {
            "telegram_user_id": telegram_user_id,
            "dastyor_user_id": user_id,
        })
        await db.commit()

    logger.warning(
        f"Pending Telegram admin ACTIVATED for Dastyor user {user_id} "
        f"as telegram {telegram_user_id}"
    )
    return True


async def remove_admin(identifier: str, actor_telegram_id: int) -> AdminChangeResult:
    """Revoke a granted admin, by Telegram id or Dastyor short id."""
    settings = get_telegram_settings()
    raw = (identifier or "").strip()
    numeric = raw.lstrip("#")

    async with async_session() as db:
        conn = await db.connection()

        if not numeric.isdigit():
            # @username form. Resolves through the same stored copy
            # /addadmin uses.
            username = normalize_username(raw)
            row = (await conn.execute(text(
                "SELECT ta.id, ta.telegram_user_id, ta.user_id FROM telegram_admins ta "
                "JOIN telegram_accounts tac ON tac.user_id = ta.user_id "
                "WHERE tac.username = :uname AND tac.revoked = FALSE "
                "  AND ta.revoked = FALSE"
            ), {"uname": username})).first()
            if row is None:
                await db.rollback()
                return AdminChangeResult(outcome="not_found")
            numeric = None
        else:
            # Resolve by Dastyor short id first — that also catches a
            # PENDING grant, which has no Telegram id to name it by.
            # Fall back to treating the argument as a literal Telegram id.
            row = (await conn.execute(text(
                "SELECT ta.id, ta.telegram_user_id, ta.user_id FROM telegram_admins ta "
                "JOIN users u ON u.id = ta.user_id "
                "WHERE u.short_id = :sid AND ta.revoked = FALSE"
            ), {"sid": numeric})).first()

            if row is None:
                row = (await conn.execute(text(
                    "SELECT id, telegram_user_id, user_id FROM telegram_admins "
                    "WHERE telegram_user_id = :tg AND revoked = FALSE"
                ), {"tg": int(numeric)})).first()

        if row is None:
            # Not a granted admin. It may still be a ROOT one, which
            # deserves its own message — "not found" would send the
            # owner hunting for a typo that is not there.
            #
            # Only reachable from the numeric branch; the username
            # branch returns above. `numeric` is the cleaned digits.
            maybe_root = (await conn.execute(text(
                "SELECT ta.telegram_user_id FROM telegram_accounts ta "
                "JOIN users u ON u.id = ta.user_id "
                "WHERE u.short_id = :sid AND ta.revoked = FALSE"
            ), {"sid": numeric})).scalar() or int(numeric)
            await db.rollback()
            if maybe_root in settings.admin_ids:
                return AdminChangeResult(outcome="is_root")
            return AdminChangeResult(outcome="not_found")

        grant_id, telegram_user_id, revoked_user_id = row

        if telegram_user_id is not None and telegram_user_id in settings.admin_ids:
            # Root admins come from the environment. Letting the bot
            # revoke one would mean a single compromised admin could
            # lock the owner out of their own payment reviews.
            await db.rollback()
            return AdminChangeResult(outcome="is_root")

        # Never leave the system with nobody who can approve. Only
        # ACTIVE grants count — a pending one cannot approve anything,
        # so it must not be mistaken for cover.
        #
        # This counts telegram_admins rows, which is still correct here:
        # every admin that exists today got that way through this same
        # function. It stops being the complete picture once the web CRM
        # can promote a User to admin directly (no telegram_admins row
        # at all) — that count will need to include those too, or this
        # guard could let the last bot-reachable admin revoke themselves
        # while believing a CRM-only admin covers them.
        remaining = len(settings.admin_ids) + (await conn.execute(text(
            "SELECT count(*) FROM telegram_admins "
            "WHERE revoked = FALSE AND telegram_user_id IS NOT NULL "
            "  AND id <> :gid"
        ), {"gid": grant_id})).scalar()
        if remaining < 1:
            await db.rollback()
            return AdminChangeResult(outcome="last_admin")

        await conn.execute(text(
            "UPDATE telegram_admins SET revoked = TRUE, revoked_at = now(), "
            "  revoked_by_telegram_id = :actor WHERE id = :gid"
        ), {"gid": grant_id, "actor": actor_telegram_id})

        if revoked_user_id is not None:
            # Same transaction as the row above, for the same reason the
            # grant side writes both together: User.role is what
            # actually gates anything now, so it cannot be left to a
            # separate step that might not happen.
            await conn.execute(text(
                "UPDATE users SET role = 'user', admin_tier = NULL WHERE id = :uid"
            ), {"uid": revoked_user_id})

        await _admin_audit(conn, "admin_revoked", actor_telegram_id, {
            "telegram_user_id": telegram_user_id,
            "grant_id": grant_id,
        })
        await db.commit()

    logger.warning(
        f"Telegram admin REVOKED from {telegram_user_id} by {actor_telegram_id}"
    )
    return AdminChangeResult(
        outcome="removed",
        entry=AdminEntry(telegram_user_id=telegram_user_id, is_root=False),
    )


async def _admin_audit(conn, event: str, actor_telegram_id: int,
                       detail: dict) -> None:
    """Admin grants land in the same append-only log as payments.

    ``payment_request_id`` is reused as a generic subject key and holds
    "admin:<telegram id>" here, so one table remains the whole history
    of privileged actions rather than two half-stories.
    """
    await conn.execute(
        text(
            "INSERT INTO payment_audit_log "
            "(id, payment_request_id, event, actor_kind, actor_telegram_id, "
            " actor_user_id, detail, created_at) "
            "VALUES (:id, :subject, :event, 'admin', :tg, NULL, :detail, now())"
        ),
        {
            "id": str(uuid.uuid4()),
            "subject": f"admin:{detail.get('telegram_user_id')}",
            "event": event,
            "tg": actor_telegram_id,
            "detail": json.dumps(detail, ensure_ascii=False, default=str),
        },
    )


# ---------------------------------------------------------------------
# Update de-duplication and polling offset
# ---------------------------------------------------------------------

async def claim_update(bot: str, update_id: int) -> bool:
    """True if this update has not been handled before, for this bot.

    Telegram re-delivers an update whose offset was never confirmed, and
    a crash between handling and confirming is exactly when that happens.
    Without this, a redelivered callback would be a second approval
    attempt — which the status CAS would catch, but an insert that either
    succeeds or does not is a cheaper and clearer first line.

    ``bot`` is part of the key because update ids are allocated per bot.
    Keying on update_id alone would make the admin bot's update 7 look
    like a replay of the user bot's update 7, and the approval it carried
    would be dropped without a trace.
    """
    async with async_session() as db:
        result = await db.execute(
            text(
                "INSERT INTO telegram_processed_updates (bot, update_id, processed_at) "
                "VALUES (:bot, :uid, now()) ON CONFLICT (bot, update_id) DO NOTHING"
            ),
            {"bot": bot, "uid": update_id},
        )
        await db.commit()
    return result.rowcount == 1


async def get_state(key: str) -> str | None:
    async with async_session() as db:
        return (await db.execute(
            text("SELECT value FROM telegram_bot_state WHERE key = :k"), {"k": key}
        )).scalar()


async def set_state(key: str, value: str) -> None:
    async with async_session() as db:
        await db.execute(
            text(
                "INSERT INTO telegram_bot_state (key, value, updated_at) "
                "VALUES (:k, :v, now()) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, "
                "  updated_at = now()"
            ),
            {"k": key, "v": value},
        )
        await db.commit()


PAY_INSTRUCTIONS_KEY = "pay_instructions"


async def get_pay_instructions() -> str:
    """What /pay shows a teacher: where to send the money.

    Database first, environment second. The env var stays as the
    initial value for a fresh deployment, but once an admin sets this
    from the bot the stored value wins — otherwise changing a card
    number would mean editing a file on the server and restarting,
    which is not something the person who owns the card can do.
    """
    stored = await get_state(PAY_INSTRUCTIONS_KEY)
    if stored is not None and stored.strip():
        return stored
    return get_telegram_settings().TELEGRAM_PAY_INSTRUCTIONS


async def set_pay_instructions(value: str, actor_telegram_id: int) -> str | None:
    """Replace the payment details. Returns the previous text.

    This decides where every teacher's money goes, so it is the single
    most valuable thing an attacker who reached an admin account could
    change. Two consequences, both deliberate:

    * the old and new text both go into the append-only audit log, so
      a redirected card number is reconstructable afterwards;
    * the caller notifies every OTHER admin, so it cannot happen
      quietly.
    """
    previous = await get_state(PAY_INSTRUCTIONS_KEY)
    await set_state(PAY_INSTRUCTIONS_KEY, value)

    async with async_session() as db:
        conn = await db.connection()
        await _admin_audit(conn, "pay_instructions_changed", actor_telegram_id, {
            "telegram_user_id": actor_telegram_id,
            "previous": previous,
            "new": value,
        })
        await db.commit()

    logger.warning(
        f"Payment instructions changed by telegram admin {actor_telegram_id} "
        f"({len(previous or '')} chars -> {len(value)} chars)"
    )
    return previous


async def set_pay_instructions_web(value: str, actor_user_id: str) -> str | None:
    """The same change as ``set_pay_instructions``, made from the web admin
    console instead of `/paycontrol`.

    Stored under the same key, so whichever channel an admin used, the
    other sees the live value immediately. The audit entry says
    ``admin_web`` and carries the Dastyor user id rather than a
    Telegram id — the two channels authenticate differently, and the
    log should say which one was actually used, not force a fake
    Telegram id to make the row look like the other kind.

    This does NOT send the "another admin changed this" notice — a web
    admin has no Telegram chat id. The caller (the HTTP route) sends
    that over Telegram itself, because that message is a Bot API
    call, and this module deliberately never makes one — see the
    module docstring.
    """
    previous = await get_state(PAY_INSTRUCTIONS_KEY)
    await set_state(PAY_INSTRUCTIONS_KEY, value)

    async with async_session() as db:
        conn = await db.connection()
        await conn.execute(
            text(
                "INSERT INTO payment_audit_log "
                "(id, payment_request_id, event, actor_kind, actor_telegram_id, "
                " actor_user_id, detail, created_at) "
                "VALUES (:id, :subject, 'pay_instructions_changed', 'admin_web', "
                "        NULL, :actor, :detail, now())"
            ),
            {
                # payment_request_id is VARCHAR(36), sized for a uuid — exactly
                # what actor_user_id already is, so no prefix fits alongside it.
                # actor_kind='admin_web' + actor_user_id already disambiguate
                # this row from the telegram-bot ones without one.
                "id": str(uuid.uuid4()),
                "subject": actor_user_id,
                "actor": actor_user_id,
                "detail": json.dumps(
                    {"actor_user_id": actor_user_id, "previous": previous, "new": value},
                    ensure_ascii=False, default=str,
                ),
            },
        )
        await db.commit()

    logger.warning(
        f"Payment instructions changed by web admin {actor_user_id} "
        f"({len(previous or '')} chars -> {len(value)} chars)"
    )
    return previous


async def get_poll_offset(bot: str) -> int:
    """Per-bot, for the same reason claim_update is keyed per bot: two
    bots share no offset space, and one overwriting the other's would
    make a restart either replay or skip real updates."""
    raw = await get_state(f"poll_offset:{bot}")
    if raw is None and bot == "user":
        # Pre-split deployments stored a single un-namespaced offset.
        raw = await get_state("poll_offset")
    try:
        return int(raw) if raw else 0
    except ValueError:
        return 0


async def set_poll_offset(bot: str, offset: int) -> None:
    await set_state(f"poll_offset:{bot}", str(offset))


async def prune_processed_updates() -> int:
    settings = get_telegram_settings()
    async with async_session() as db:
        result = await db.execute(
            text(
                # Multiply a literal interval rather than building one by
                # string concatenation. `(:days || ' days')::interval`
                # makes asyncpg infer the parameter as text, so passing
                # the int it actually is raises DataError and the prune
                # silently never runs — leaving the dedupe table to grow
                # forever. Multiplication keeps the parameter numeric.
                "DELETE FROM telegram_processed_updates "
                "WHERE processed_at < now() - (interval '1 day' * :days)"
            ),
            {"days": settings.TELEGRAM_UPDATE_DEDUPE_RETENTION_DAYS},
        )
        await db.commit()
    return result.rowcount or 0


# ---------------------------------------------------------------------
# Amount parsing for the /pay conversation
# ---------------------------------------------------------------------

def parse_amount_to_dirams(raw: str) -> int | None:
    """Read a teacher-typed amount as somoni and return dirams.

    Accepts "25", "25.5", "25,50" and "1 000". Rejects anything else
    rather than guessing: a misread amount here becomes a mismatch
    warning later and wastes the admin's time.
    """
    import re

    text_value = (raw or "").strip().replace(" ", "").replace(" ", "")
    text_value = text_value.replace(",", ".")
    if not re.fullmatch(r"\d{1,9}(?:\.\d{1,2})?", text_value):
        return None
    from decimal import Decimal

    dirams = int((Decimal(text_value) * 100).to_integral_value(rounding="ROUND_HALF_UP"))
    return dirams if dirams > 0 else None


def validate_topup_dirams(dirams: int) -> str | None:
    """``None`` when acceptable, else a reason code for the caller to render."""
    settings = get_telegram_settings()
    if dirams < settings.TELEGRAM_MIN_TOPUP_DIRAMS:
        return "too_small"
    if dirams > settings.TELEGRAM_MAX_TOPUP_DIRAMS:
        return "too_large"
    return None


def generation_price_dirams() -> int:
    """Re-exported so the bot never hardcodes a second price."""
    return GENERATION_PRICE_DIRAMS


# ---------------------------------------------------------------------
# Tier-aware permission checks for bot-side admin actions
# ---------------------------------------------------------------------

async def resolve_admin_identity(telegram_user_id: int) -> tuple[str | None, str | None]:
    """(user_id, admin_tier) for a linked, active, role='admin' account;
    (None, None) otherwise. Does not cover root (TELEGRAM_ADMIN_IDS)
    admins - they have no User row by design; callers check
    settings.is_admin() separately."""
    async with async_session() as db:
        row = (await db.execute(text(
            "SELECT u.id, u.admin_tier FROM telegram_accounts ta "
            "JOIN users u ON u.id = ta.user_id "
            "WHERE ta.telegram_user_id = :tg AND ta.revoked = FALSE AND u.role = 'admin'"
        ), {"tg": telegram_user_id})).first()
    return (row[0], row[1]) if row else (None, None)


class _TierHolder:
    """Just enough of User for admin_roles.has_permission."""
    def __init__(self, admin_tier: str | None):
        self.admin_tier = admin_tier


async def has_admin_permission(telegram_user_id: int, permission: str) -> bool:
    """The backend-enforced check for every bot admin action that calls
    routers/admin_crm.py functions directly instead of over HTTP (where
    FastAPI's own Depends(require_permission(...)) would run). Calling
    an admin_crm.py function straight from Python skips that dependency
    entirely, so every bot handler that reaches one MUST call this
    first - hiding a button is not enough, per the product requirement.

    Reuses app.admin_roles.has_permission so the tier→permission table
    is defined in exactly one place.
    """
    settings = get_telegram_settings()
    if settings.is_admin(telegram_user_id):
        return True
    user_id, tier = await resolve_admin_identity(telegram_user_id)
    if user_id is None:
        return False
    from app import admin_roles
    return admin_roles.has_permission(_TierHolder(tier), permission)


async def admin_tier_label(telegram_user_id: int) -> str:
    """'super'|'finance'|'support'|'readonly' for keyboard filtering.
    Root admins and NULL-tier linked admins are both 'super', matching
    admin_roles' own fallback."""
    settings = get_telegram_settings()
    if settings.is_admin(telegram_user_id):
        return "super"
    _, tier = await resolve_admin_identity(telegram_user_id)
    return tier or "super"
