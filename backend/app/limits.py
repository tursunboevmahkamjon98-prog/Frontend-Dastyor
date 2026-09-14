# -*- coding: utf-8 -*-
"""The generation limit, enforced where it cannot be argued with.

The rule
--------
An account's FIRST generated material is free — one, across every type.
Every generation after it costs GENERATION_PRICE_DIRAMS (50 dirams = 0.5
somoni). That is the whole rule; there is no per-type allowance anymore.

Why this module exists
----------------------
The previous implementation read `user.free_X_used` / `user.balance_dirams`
off an ORM object, ran a sixty-second AI call, and only then wrote
`user.balance_dirams -= 50` back. That is a read-modify-write with an
enormous window in the middle, and it was reachable from six different
call sites, each with its own copy of the arithmetic. Two requests fired
at the same moment both read the same balance, both passed the check, and
both subtracted from the same starting value — the account got two
materials for one charge. Firing N requests at once got N materials for
one charge. No frontend change was needed to do it; `curl` twice was
enough.

Two things fix that, and both are load-bearing:

1. **Charge first, refund on failure.** The cost is claimed BEFORE the AI
   call, not after it. Deciding up front and paying up later is what
   leaves the window open. A generation that then fails is refunded (with
   a ledger row for both movements), so a teacher still never pays for a
   material they did not receive — which is what the pay-after ordering
   was protecting, and it is preserved.

2. **The claim is one conditional UPDATE.** Not a SELECT then an UPDATE:

       UPDATE users SET balance_dirams = balance_dirams - 50
        WHERE id = :uid AND balance_dirams >= 50

   PostgreSQL takes a row lock for the duration of that statement, and a
   concurrent UPDATE that blocks on the lock re-evaluates its WHERE
   clause against the committed row once the lock is released. So of two
   simultaneous charges against a 50-diram balance, exactly one matches
   and the other's rowcount is 0. The database decides, not the
   application, and it decides for every worker process at once — an
   in-process lock would only cover one uvicorn worker.

Each claim runs in its OWN short-lived session that commits immediately,
rather than the request's session. The request's session stays open for
the whole AI call; claiming inside it would hold the users-row lock for
the length of a generation, serializing every one of that teacher's
requests behind the slowest one and pinning a pooled connection while it
waited.

What this closes
----------------
Because the decision is a single statement in the database, keyed on the
user id from the verified JWT, none of these change the outcome: editing
JavaScript, replaying the request, sending it straight to the API without
the frontend, changing a body parameter, clearing localStorage,
reinstalling the app, or firing a hundred requests at once. Passing a
different user id changes nothing either — no charging path here accepts
a user id from the request body; it always comes from the authenticated
token (see routers/*.py's `Depends(get_current_user)`).
"""
import uuid
from dataclasses import dataclass, field

from fastapi import HTTPException
from sqlalchemy import text

from app.database import async_session
from app.i18n import get_message
from app.logger import get_logger

logger = get_logger(__name__)

# 50 dirams = half a somoni = "0.5 лимита" per generation once the free
# slot for that material type has been used. Integer subunits, never a
# float: 0.5 somoni is exactly 50 dirams, and 0.5 as a float would start
# rounding the moment balances are summed.
GENERATION_PRICE_DIRAMS = 50

# One free generation PER MATERIAL TYPE, not one per account: a new
# teacher gets a konspekt, a lecture, a test and a presentation for free
# and only pays from the second of any one type. This is what i18n.py's
# "free_limit_reached" and the UserResponse docstring have always
# promised; the account-wide single freebie that briefly replaced it
# contradicted both.
#
# Maps the material_type strings reserve() is called with (see
# routers/materials.py's _GENERATE_ALL_TYPES) to the boolean columns that
# already exist on users — see database.py's init_db, which has been
# adding them since the original per-type rule. A type that is absent
# here simply has no free slot and is always charged, which is why "igra"
# is not listed.
#
# "amaliy" is listed, and it has to be: generate-all reserves all of its
# types as ONE atomic unit, so a single chargeable type among them makes
# the whole request 402 for an account with an empty balance — a brand-new
# teacher pressing "everything at once" would get nothing at all rather
# than four free materials and one refusal.
FREE_SLOT_COLUMN = {
    "konspekt": "free_konspekt_used",
    "lektsiya": "free_lektsiya_used",
    "test": "free_test_used",
    "prezentatsiya": "free_prezentatsiya_used",
    "amaliy": "free_amaliy_used",
}

# Every generation is free for everyone and nothing is deducted. Kept as
# a switch (it was on through the teacher pilot and off since 2026-09-08)
# — while it is on, reserve() still writes its ledger rows, so turning it
# off later does not leave a gap in the history.
PILOT_FREE_FOR_ALL = False


@dataclass
class Charge:
    """What a reserve() call actually took, and what a refund would give
    back. `items` holds one entry per unit reserved so a multi-material
    request (generate-all, a curriculum day) can refund exactly the parts
    that failed rather than all-or-nothing."""
    user_id: str
    items: list["ChargeItem"] = field(default_factory=list)

    @property
    def dirams(self) -> int:
        return sum(i.dirams for i in self.items)

    @property
    def free_count(self) -> int:
        return sum(1 for i in self.items if i.was_free)

    def __bool__(self) -> bool:
        return bool(self.items)


@dataclass
class ChargeItem:
    material_type: str
    was_free: bool
    dirams: int


class InsufficientBalance(HTTPException):
    def __init__(self, language: str = "Русский"):
        super().__init__(status_code=402, detail=get_message("insufficient_balance", language))


async def _claim_free(conn, user_id: str, material_type: str) -> bool:
    """Claims this account's free slot for [material_type], atomically.
    True only for the single request that wins it; every later (or
    concurrent) call sees rowcount 0 because the flag is already TRUE by
    the time their UPDATE re-evaluates its WHERE clause.

    Returns False immediately for a type with no free slot (see
    FREE_SLOT_COLUMN), so those are always paid."""
    column = FREE_SLOT_COLUMN.get(material_type)
    if column is None:
        return False
    # The column name is interpolated because a bound parameter cannot
    # name a column. It never comes from a request: it is a value of
    # FREE_SLOT_COLUMN, looked up above by an exact dict hit.
    result = await conn.execute(
        text(
            f"UPDATE users SET {column} = TRUE "
            f"WHERE id = :uid AND {column} = FALSE"
        ),
        {"uid": user_id},
    )
    return result.rowcount == 1


async def _claim_balance(conn, user_id: str, dirams: int) -> tuple[bool, int]:
    """Deducts [dirams], but only if the balance actually covers it.
    Returns (claimed, balance_after). The RETURNING clause gives the
    post-deduction balance from the same statement that made the
    deduction — reading it back with a second SELECT would be reading a
    value another transaction may already have moved."""
    result = await conn.execute(
        text(
            "UPDATE users SET balance_dirams = balance_dirams - :amt "
            "WHERE id = :uid AND balance_dirams >= :amt "
            "RETURNING balance_dirams"
        ),
        {"uid": user_id, "amt": dirams},
    )
    row = result.first()
    return (row is not None), (row[0] if row else 0)


async def _ledger(conn, *, user_id: str, kind: str, amount: int, before: int, after: int,
                  material_type: str | None = None, reason: str | None = None,
                  actor_id: str | None = None) -> None:
    """One ledger row, written on the same connection (and therefore in
    the same transaction) as the balance movement it describes — so the
    two can never disagree."""
    await conn.execute(
        text(
            "INSERT INTO balance_transactions "
            "(id, user_id, kind, amount_dirams, balance_before, balance_after, "
            " actor_id, reason, material_type, created_at) "
            "VALUES (:id, :uid, :kind, :amt, :before, :after, "
            "        :actor, :reason, :mtype, now())"
        ),
        {
            # Generated here rather than with gen_random_uuid(): that
            # function is only built in from PostgreSQL 13 and needs the
            # pgcrypto extension before it, which this deployment does not
            # install. Every other id in this schema is a Python-side
            # uuid4 anyway (see models.py).
            "id": str(uuid.uuid4()),
            "uid": user_id, "kind": kind, "amt": amount, "before": before, "after": after,
            "actor": actor_id, "reason": reason, "mtype": material_type,
        },
    )


async def reserve(user_id: str, material_types: list[str], *, language: str = "Русский") -> Charge:
    """Claims payment for [material_types] up front — one unit per entry,
    so ["konspekt", "test"] reserves two.

    Raises 402 without taking anything if the account cannot cover the
    whole request: a half-paid generate-all would leave a teacher charged
    for materials they were then refused. Anything already claimed inside
    this call is rolled back before raising, because it is all one
    transaction.

    The caller MUST call refund() for whatever part of the work ends up
    failing. Nothing else undoes a reservation."""
    if not material_types:
        return Charge(user_id=user_id, items=[])

    if PILOT_FREE_FOR_ALL:
        return Charge(
            user_id=user_id,
            items=[ChargeItem(material_type=t, was_free=True, dirams=0) for t in material_types],
        )

    charge = Charge(user_id=user_id, items=[])
    async with async_session() as db:
        conn = await db.connection()
        for mtype in material_types:
            if await _claim_free(conn, user_id, mtype):
                balance = (await conn.execute(
                    text("SELECT balance_dirams FROM users WHERE id = :uid"), {"uid": user_id}
                )).scalar() or 0
                await _ledger(conn, user_id=user_id, kind="free", amount=0,
                              before=balance, after=balance, material_type=mtype,
                              reason=f"first free {mtype}")
                charge.items.append(ChargeItem(material_type=mtype, was_free=True, dirams=0))
                continue

            claimed, after = await _claim_balance(conn, user_id, GENERATION_PRICE_DIRAMS)
            if not claimed:
                # Roll the whole request back — including any unit already
                # claimed in this loop — then refuse. Leaving a partial
                # reservation standing would charge for work that is about
                # to be rejected.
                await db.rollback()
                logger.warning(
                    f"Generation refused for user {user_id}: balance does not cover "
                    f"{len(material_types)} x {GENERATION_PRICE_DIRAMS} dirams"
                )
                raise InsufficientBalance(language)
            await _ledger(conn, user_id=user_id, kind="charge",
                          amount=-GENERATION_PRICE_DIRAMS,
                          before=after + GENERATION_PRICE_DIRAMS, after=after,
                          material_type=mtype, reason="generation")
            charge.items.append(
                ChargeItem(material_type=mtype, was_free=False, dirams=GENERATION_PRICE_DIRAMS)
            )
        await db.commit()

    logger.info(
        f"Reserved {len(charge.items)} generation(s) for user {user_id}: "
        f"{charge.free_count} free, {charge.dirams} dirams"
    )
    return charge


async def refund(charge: Charge, material_types: list[str] | None = None,
                 *, reason: str = "generation failed") -> None:
    """Gives back what [charge] took, for the units named in
    [material_types] (default: all of them).

    Never raises. A refund failing must not turn a failed generation into
    a 500 that hides the real error from the teacher — the loss is one
    teacher's 50 dirams, recoverable by an admin from the ledger, whereas
    a masked error is unrecoverable information."""
    if not charge or not charge.items:
        return
    try:
        pending = list(charge.items)
        if material_types is not None:
            wanted = list(material_types)
            pending = []
            for item in charge.items:
                if item.material_type in wanted:
                    wanted.remove(item.material_type)
                    pending.append(item)
        if not pending:
            return

        async with async_session() as db:
            conn = await db.connection()
            for item in pending:
                if item.was_free:
                    # Hand the free slot back rather than crediting 50
                    # dirams the account never had — a failed first
                    # generation must leave the teacher exactly where they
                    # started, still holding their free one. It goes back
                    # to the slot for THIS type: a failed presentation
                    # must not return the konspekt's freebie.
                    column = FREE_SLOT_COLUMN.get(item.material_type)
                    if column is not None:
                        # Interpolated for the same reason as in
                        # _claim_free, and equally not request data.
                        await conn.execute(
                            text(f"UPDATE users SET {column} = FALSE WHERE id = :uid"),
                            {"uid": charge.user_id},
                        )
                    balance = (await conn.execute(
                        text("SELECT balance_dirams FROM users WHERE id = :uid"),
                        {"uid": charge.user_id},
                    )).scalar() or 0
                    await _ledger(conn, user_id=charge.user_id, kind="refund", amount=0,
                                  before=balance, after=balance,
                                  material_type=item.material_type, reason=reason)
                    continue
                after = (await conn.execute(
                    text(
                        "UPDATE users SET balance_dirams = balance_dirams + :amt "
                        "WHERE id = :uid RETURNING balance_dirams"
                    ),
                    {"uid": charge.user_id, "amt": item.dirams},
                )).scalar()
                if after is None:
                    continue  # account deleted mid-generation; nothing to credit
                await _ledger(conn, user_id=charge.user_id, kind="refund", amount=item.dirams,
                              before=after - item.dirams, after=after,
                              material_type=item.material_type, reason=reason)
            await db.commit()
        logger.info(f"Refunded {len(pending)} generation(s) to user {charge.user_id}: {reason}")
    except Exception as e:  # noqa: BLE001 — see docstring
        logger.error(
            f"REFUND FAILED for user {charge.user_id} ({reason}): {e}. "
            f"Items: {[(i.material_type, i.dirams) for i in charge.items]}",
            exc_info=True,
        )


async def current_balance(user_id: str) -> int:
    """The committed balance in dirams, read fresh.

    Needed because reserve()/refund() move the balance on their own
    connections: the ORM `User` the request is holding still has the
    value from when the request started, and returning that to the
    frontend would show a teacher a balance that is one generation out of
    date."""
    async with async_session() as db:
        return (await db.execute(
            text("SELECT balance_dirams FROM users WHERE id = :uid"), {"uid": user_id}
        )).scalar() or 0


async def quote(user_id: str, count: int,
                material_types: list[str] | None = None) -> dict:
    """What [count] generations would cost this account right now, without
    taking anything — for the "generate all" / whole-course estimate
    screens. Advisory only: the real decision is always reserve()'s
    conditional UPDATE, which re-checks at the moment of the charge.

    [material_types] is what those generations will actually be, so the
    per-type free slots (see FREE_SLOT_COLUMN) can be counted properly: a
    course of twenty konspekts covers one free slot, a konspekt plus a
    test covers two. Callers that genuinely do not know the types yet can
    omit it, and then no free slot is assumed — an estimate that is too
    high only shows a teacher a price they will not be charged, whereas
    one that is too low would promise a discount reserve() then refuses."""
    columns = ", ".join(FREE_SLOT_COLUMN.values())
    async with async_session() as db:
        row = (await db.execute(
            text(f"SELECT balance_dirams, {columns} FROM users WHERE id = :uid"),
            {"uid": user_id},
        )).first()
    if row is None:
        balance, used = 0, {t: True for t in FREE_SLOT_COLUMN}
    else:
        balance = row[0]
        used = {t: bool(v) for t, v in zip(FREE_SLOT_COLUMN, row[1:])}
    if PILOT_FREE_FOR_ALL:
        return {"count": count, "free_count": count, "paid_count": 0,
                "required_dirams": 0, "balance_dirams": balance, "affordable": True}
    free_count = 0
    if material_types:
        # Only the FIRST occurrence of each type is free, exactly as
        # reserve()'s loop claims them, so a request for three konspekts
        # is quoted as one free and two paid.
        for mtype in material_types[:count]:
            if mtype in used and not used[mtype]:
                used[mtype] = True
                free_count += 1
    paid_count = count - free_count
    required = paid_count * GENERATION_PRICE_DIRAMS
    return {
        "count": count,
        "free_count": free_count,
        "paid_count": paid_count,
        "required_dirams": required,
        "balance_dirams": balance,
        "affordable": required <= balance,
    }
