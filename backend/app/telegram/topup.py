"""Administrator-initiated balance top-ups.

The flow this module serves, from the brief: an admin picks a user,
types an amount, adds a note, confirms — and the balance moves. No
receipt from the teacher, no "did the money arrive" buttons. The admin
already knows the money arrived; they are recording it, not
investigating it.

Everything money-touching lives here rather than in ``bot.py`` for the
same reason the review flow does: the bot process acts on input from
strangers, and these are the rules that most need testing.

Three properties it is built around
-----------------------------------

**Exactly once.** The confirm button carries an idempotency key minted
when the preview was shown. A double tap, a redelivered update and a
retry after a timeout all arrive carrying the SAME key, and the unique
index on ``balance_transactions.idempotency_key`` rejects every attempt
after the first. The loser is told the credit already happened — with
its operation number — rather than being left to guess.

**Atomic.** The balance update and the ledger row are one transaction.
There is no window in which a balance has moved without a record, or a
record exists for money that never moved.

**Reconstructable.** Every credit stores who did it (Telegram id), what
they typed as a reason, the balance before and after, and a short
operation code the teacher can quote. Nothing here deletes or rewrites
a ledger row.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import async_session
from app.logger import get_logger
from app.telegram.config import get_telegram_settings

logger = get_logger(__name__)

# Crockford-ish: no O/0 or I/1 to confuse when read aloud.
_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def new_operation_code() -> str:
    return "TX-" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))


def new_idempotency_key() -> str:
    return uuid.uuid4().hex


# ---------------------------------------------------------------------
# Amount parsing and validation
# ---------------------------------------------------------------------

def parse_amount(raw: str) -> int | None:
    """Admin-typed somoni to integer dirams, or None if unreadable.

    ``Decimal``, never ``float``: 0.1 + 0.2 is not 0.3 in binary
    floating point, and this is money. The value is converted to whole
    dirams immediately and stays an int from there on.
    """
    text_value = (raw or "").strip().replace(" ", "").replace(" ", "")
    text_value = text_value.replace(",", ".")
    if not text_value:
        return None
    # Reject anything that is not a plain decimal: "1e5", "0x10", "--5"
    # and "5 somoni" must not be guessed at.
    if not _looks_like_plain_decimal(text_value):
        return None
    try:
        value = Decimal(text_value)
    except (InvalidOperation, ValueError):
        return None
    if value != value.quantize(Decimal("0.01")):
        # More than two decimal places is not a somoni figure.
        return None
    return int((value * 100).to_integral_value(rounding="ROUND_HALF_UP"))


def _looks_like_plain_decimal(value: str) -> bool:
    if value.count(".") > 1:
        return False
    body = value[1:] if value[:1] == "-" else value
    # ASCII digits only. str.isdigit() is true for full-width "２５" and
    # for Arabic-Indic digits, and Decimal accepts them, so without this
    # an amount could be written in a form that does not look like the
    # one in the ledger beside it. A money parser is worth more
    # predictable than accommodating.
    return bool(body) and all(c in "0123456789." for c in body)


@dataclass
class AmountCheck:
    ok: bool
    dirams: int = 0
    problem: str | None = None  # not_a_number | not_positive | too_large


def validate_amount(raw: str) -> AmountCheck:
    """Reject zero, negative, malformed and over-limit amounts."""
    dirams = parse_amount(raw)
    if dirams is None:
        return AmountCheck(ok=False, problem="not_a_number")
    if dirams <= 0:
        return AmountCheck(ok=False, problem="not_positive")
    ceiling = get_telegram_settings().TELEGRAM_MAX_TOPUP_DIRAMS
    if dirams > ceiling:
        return AmountCheck(ok=False, dirams=dirams, problem="too_large")
    return AmountCheck(ok=True, dirams=dirams)


# ---------------------------------------------------------------------
# Finding the user to credit
# ---------------------------------------------------------------------

@dataclass
class FoundUser:
    user_id: str
    short_id: str | None
    full_name: str
    balance_dirams: int
    language: str
    chat_id: int | None  # None when they have not linked Telegram

    @property
    def label(self) -> str:
        return f"#{self.short_id} · {self.full_name}" if self.short_id \
            else self.full_name


_FIND_SELECT = (
    "SELECT u.id, u.short_id, u.full_name, u.balance_dirams, u.language, "
    "       ta.chat_id "
    "FROM users u "
    "LEFT JOIN telegram_accounts ta "
    "  ON ta.user_id = u.id AND ta.revoked = FALSE "
)


def _row_to_user(row) -> FoundUser:
    return FoundUser(
        user_id=row[0], short_id=row[1], full_name=row[2],
        balance_dirams=row[3], language=row[4], chat_id=row[5],
    )


async def find_user(identifier: str) -> FoundUser | None:
    """Resolve one user by Dastyor short id, uuid or phone.

    Exact matches only. A fuzzy match here would mean an admin could
    credit the wrong person by typing a near-miss, which is the one
    mistake this flow must not make easy. Name search exists
    separately, returns a list, and makes the admin pick.
    """
    needle = (identifier or "").strip().lstrip("#")
    if not needle:
        return None

    async with async_session() as db:
        if needle.isdigit() and len(needle) == 6:
            row = (await db.execute(
                text(_FIND_SELECT + "WHERE u.short_id = :v"), {"v": needle}
            )).first()
        elif needle.count("-") == 4 and len(needle) == 36:
            row = (await db.execute(
                text(_FIND_SELECT + "WHERE u.id = :v"), {"v": needle}
            )).first()
        else:
            from app.telegram.service import normalize_phone

            phone = normalize_phone(needle)
            if phone is None:
                return None
            row = (await db.execute(
                text(_FIND_SELECT + "WHERE u.phone = :v"), {"v": phone}
            )).first()

    return _row_to_user(row) if row else None


async def search_users(query: str, limit: int = 8) -> list[FoundUser]:
    """Name search, for when the admin does not know the id.

    Returns candidates for the admin to choose from — it never picks
    one. ``ILIKE`` with the term escaped, so a name containing % or _
    does not silently widen the search.
    """
    needle = (query or "").strip()
    if len(needle) < 2:
        return []
    escaped = needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    async with async_session() as db:
        rows = (await db.execute(
            text(_FIND_SELECT +
                 "WHERE u.full_name ILIKE :q ESCAPE '\\' "
                 "ORDER BY u.full_name LIMIT :lim"),
            {"q": f"%{escaped}%", "lim": limit},
        )).all()
    return [_row_to_user(r) for r in rows]


async def current_balance(user_id: str) -> int | None:
    async with async_session() as db:
        return (await db.execute(
            text("SELECT balance_dirams FROM users WHERE id = :u"),
            {"u": user_id},
        )).scalar()


# ---------------------------------------------------------------------
# The credit itself
# ---------------------------------------------------------------------

@dataclass
class CreditResult:
    outcome: str  # applied | duplicate | user_gone | invalid_amount
    operation_code: str | None = None
    credited_dirams: int = 0
    balance_before: int = 0
    balance_after: int = 0
    user: FoundUser | None = None


async def find_by_idempotency_key(key: str) -> CreditResult | None:
    """Has a credit with this key already landed?

    The brief's "if a request ended in an unknown state because of a
    network error, check the operation in the database before crediting
    again". The bot calls this when it is unsure, instead of retrying
    blind.
    """
    async with async_session() as db:
        row = (await db.execute(text(
            "SELECT public_code, amount_dirams, balance_before, balance_after, "
            "       user_id "
            "FROM balance_transactions WHERE idempotency_key = :k"
        ), {"k": key})).first()
    if row is None:
        return None
    return CreditResult(
        outcome="duplicate", operation_code=row[0], credited_dirams=row[1],
        balance_before=row[2], balance_after=row[3],
    )


async def credit_user(user_id: str, dirams: int, admin_telegram_id: int,
                      idempotency_key: str,
                      note: str | None = None) -> CreditResult:
    """Add ``dirams`` to a balance, exactly once, atomically.

    The amount is re-validated here even though the bot checked it:
    this function is the trust boundary, and a caller that skipped the
    check must not be able to write a negative or unbounded credit.
    """
    if dirams <= 0:
        return CreditResult(outcome="invalid_amount")
    ceiling = get_telegram_settings().TELEGRAM_MAX_TOPUP_DIRAMS
    if dirams > ceiling:
        return CreditResult(outcome="invalid_amount")

    # A key that has already been used means the credit happened. Check
    # before attempting, so the common double-tap gets a clean answer
    # rather than an IntegrityError in the log.
    existing = await find_by_idempotency_key(idempotency_key)
    if existing is not None:
        logger.info(
            f"Top-up with key {idempotency_key[:8]}… already applied as "
            f"{existing.operation_code}; not crediting again"
        )
        return existing

    code = new_operation_code()

    async with async_session() as db:
        conn = await db.connection()
        try:
            # RETURNING gives the post-update balance from the same
            # statement that wrote it, so balance_before is derived
            # rather than read separately — a second read could see a
            # different value under concurrent generation charges.
            new_balance = (await conn.execute(text(
                "UPDATE users SET balance_dirams = balance_dirams + :amt "
                "WHERE id = :uid RETURNING balance_dirams"
            ), {"uid": user_id, "amt": dirams})).scalar()

            if new_balance is None:
                await db.rollback()
                logger.error(f"Top-up failed: user {user_id} does not exist")
                return CreditResult(outcome="user_gone")

            await conn.execute(text(
                "INSERT INTO balance_transactions "
                "(id, user_id, kind, amount_dirams, balance_before, "
                " balance_after, actor_id, reason, material_type, created_at, "
                " actor_telegram_id, idempotency_key, public_code) "
                "VALUES (:id, :uid, 'topup', :amt, :before, :after, "
                "        NULL, :reason, NULL, now(), :tg, :key, :code)"
            ), {
                "id": str(uuid.uuid4()),
                "uid": user_id,
                "amt": dirams,
                "before": new_balance - dirams,
                "after": new_balance,
                "reason": (note or "").strip()[:255] or None,
                "tg": admin_telegram_id,
                "key": idempotency_key,
                "code": code,
            })
            await db.commit()

        except IntegrityError:
            # The unique index fired: a concurrent attempt with the same
            # key won the race. Nothing was applied by this call.
            await db.rollback()
            logger.info(
                f"Concurrent top-up with key {idempotency_key[:8]}… lost the "
                f"race; reading the winning row"
            )
            winner = await find_by_idempotency_key(idempotency_key)
            if winner is not None:
                return winner
            return CreditResult(outcome="invalid_amount")

    logger.warning(
        f"Balance credited: {dirams} dirams to user {user_id} by telegram "
        f"admin {admin_telegram_id}, operation {code}, "
        f"balance {new_balance - dirams} -> {new_balance}"
    )
    return CreditResult(
        outcome="applied", operation_code=code, credited_dirams=dirams,
        balance_before=new_balance - dirams, balance_after=new_balance,
    )


# ---------------------------------------------------------------------
# History and statistics
# ---------------------------------------------------------------------

@dataclass
class LedgerEntry:
    operation_code: str | None
    user_id: str
    short_id: str | None
    full_name: str
    amount_dirams: int
    balance_after: int
    admin_telegram_id: int | None
    note: str | None
    created_at: datetime
    # Only set by user_ledger, which does not filter by kind. 'topup'
    # and 'charge' read very differently to the person they happened to.
    kind: str = "topup"
    material_type: str | None = None

    @property
    def is_charge(self) -> bool:
        return self.amount_dirams < 0 or self.kind != "topup"


async def topup_history(user_id: str | None = None,
                        since: date | None = None,
                        until: date | None = None,
                        limit: int = 20) -> list[LedgerEntry]:
    """Telegram top-ups, newest first, optionally narrowed.

    Only rows this bot wrote: ``actor_telegram_id IS NOT NULL``. The
    ledger also holds generation charges and the website's own admin
    top-ups, and mixing them into "top-ups I made here" would misreport
    the totals an admin is checking.
    """
    clauses = ["bt.actor_telegram_id IS NOT NULL"]
    params: dict = {"lim": limit}
    if user_id:
        clauses.append("bt.user_id = :uid")
        params["uid"] = user_id
    if since:
        clauses.append("bt.created_at >= :since")
        params["since"] = datetime.combine(
            since, datetime.min.time(), tzinfo=timezone.utc)
    if until:
        clauses.append("bt.created_at < :until + interval '1 day'")
        params["until"] = datetime.combine(
            until, datetime.min.time(), tzinfo=timezone.utc)

    async with async_session() as db:
        rows = (await db.execute(text(
            "SELECT bt.public_code, bt.user_id, u.short_id, u.full_name, "
            "       bt.amount_dirams, bt.balance_after, bt.actor_telegram_id, "
            "       bt.reason, bt.created_at "
            "FROM balance_transactions bt "
            "LEFT JOIN users u ON u.id = bt.user_id "
            f"WHERE {' AND '.join(clauses)} "
            "ORDER BY bt.created_at DESC LIMIT :lim"
        ), params)).all()

    return [
        LedgerEntry(
            operation_code=r[0], user_id=r[1], short_id=r[2],
            full_name=r[3] or "—", amount_dirams=r[4], balance_after=r[5],
            admin_telegram_id=r[6], note=r[7], created_at=r[8],
        )
        for r in rows
    ]


async def user_ledger(user_id: str, limit: int = 10) -> list[LedgerEntry]:
    """Everything that moved one teacher's balance, newest first.

    Unlike :func:`topup_history` this is not filtered to the bot's own
    rows. A teacher asking "what happened to my balance" means the
    charges too; showing only the top-ups would make the number at the
    bottom look wrong.
    """
    async with async_session() as db:
        rows = (await db.execute(text(
            "SELECT bt.public_code, bt.user_id, u.short_id, u.full_name, "
            "       bt.amount_dirams, bt.balance_after, bt.actor_telegram_id, "
            "       bt.reason, bt.created_at, bt.kind, bt.material_type "
            "FROM balance_transactions bt "
            "LEFT JOIN users u ON u.id = bt.user_id "
            "WHERE bt.user_id = :uid "
            "ORDER BY bt.created_at DESC LIMIT :lim"
        ), {"uid": user_id, "lim": limit})).all()

    return [
        LedgerEntry(
            operation_code=r[0], user_id=r[1], short_id=r[2],
            full_name=r[3] or "—", amount_dirams=r[4], balance_after=r[5],
            admin_telegram_id=r[6], note=r[7], created_at=r[8],
            kind=r[9], material_type=r[10],
        )
        for r in rows
    ]


@dataclass
class TopupStats:
    today_count: int = 0
    today_dirams: int = 0
    month_count: int = 0
    month_dirams: int = 0
    total_count: int = 0
    total_dirams: int = 0
    distinct_users: int = 0


async def topup_stats() -> TopupStats:
    async with async_session() as db:
        row = (await db.execute(text(
            "SELECT "
            " count(*) FILTER (WHERE created_at >= date_trunc('day', now())), "
            " coalesce(sum(amount_dirams) FILTER "
            "   (WHERE created_at >= date_trunc('day', now())), 0), "
            " count(*) FILTER (WHERE created_at >= date_trunc('month', now())), "
            " coalesce(sum(amount_dirams) FILTER "
            "   (WHERE created_at >= date_trunc('month', now())), 0), "
            " count(*), coalesce(sum(amount_dirams), 0), "
            " count(DISTINCT user_id) "
            "FROM balance_transactions WHERE actor_telegram_id IS NOT NULL"
        ))).first()

    return TopupStats(
        today_count=row[0], today_dirams=row[1],
        month_count=row[2], month_dirams=row[3],
        total_count=row[4], total_dirams=row[5], distinct_users=row[6],
    )


@dataclass
class LedgerReconciliation:
    """How much of a balance the ledger accounts for."""

    stored: int
    from_ledger: int

    @property
    def unexplained(self) -> int:
        """Balance not covered by any recorded transaction.

        Not automatically a fault. An account that held a balance
        before this ledger existed, or one seeded directly in the
        database, carries an opening amount with no row behind it, and
        that shows up here forever as a constant.

        What matters is that it does not MOVE. A constant difference is
        history; a difference that grows means something changed a
        balance without recording it, which is the bug worth catching.
        """
        return self.stored - self.from_ledger

    @property
    def fully_explained(self) -> bool:
        return self.unexplained == 0


async def reconcile_balance(user_id: str) -> LedgerReconciliation | None:
    """Compare a stored balance against the sum of its ledger rows.

    The brief asks for this check. Deliberately reported as a number
    rather than a pass/fail: see ``unexplained`` for why a non-zero
    result is not on its own evidence of a bug.
    """
    async with async_session() as db:
        stored = (await db.execute(
            text("SELECT balance_dirams FROM users WHERE id = :u"),
            {"u": user_id},
        )).scalar()
        if stored is None:
            return None
        summed = (await db.execute(text(
            "SELECT coalesce(sum(amount_dirams), 0) "
            "FROM balance_transactions WHERE user_id = :u"
        ), {"u": user_id})).scalar()

    return LedgerReconciliation(stored=stored, from_ledger=summed)
