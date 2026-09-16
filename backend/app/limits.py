import uuid
from dataclasses import dataclass, field

from fastapi import HTTPException
from sqlalchemy import text

from app.config import get_settings
from app.database import async_session
from app.i18n import get_message
from app.logger import get_logger

logger = get_logger(__name__)

GENERATION_PRICE_DIRAMS = 50

FREE_SLOT_COLUMN = {
    "konspekt": "free_konspekt_used",
    "lektsiya": "free_lektsiya_used",
    "test": "free_test_used",
    "prezentatsiya": "free_prezentatsiya_used",
    "amaliy": "free_amaliy_used",
}

PILOT_FREE_FOR_ALL = False


@dataclass
class Charge:
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
    column = FREE_SLOT_COLUMN.get(material_type)
    if column is None:
        return False
    result = await conn.execute(
        text(
            f"UPDATE users SET {column} = {column} + 1 "
            f"WHERE id = :uid AND {column} < :limit"
        ),
        {"uid": user_id, "limit": get_settings().FREE_GENERATIONS_PER_TYPE},
    )
    return result.rowcount == 1


async def _claim_balance(conn, user_id: str, dirams: int) -> tuple[bool, int]:
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
    await conn.execute(
        text(
            "INSERT INTO balance_transactions "
            "(id, user_id, kind, amount_dirams, balance_before, balance_after, "
            " actor_id, reason, material_type, created_at) "
            "VALUES (:id, :uid, :kind, :amt, :before, :after, "
            "        :actor, :reason, :mtype, now())"
        ),
        {
            "id": str(uuid.uuid4()),
            "uid": user_id, "kind": kind, "amt": amount, "before": before, "after": after,
            "actor": actor_id, "reason": reason, "mtype": material_type,
        },
    )


async def reserve(user_id: str, material_types: list[str], *, language: str = "Русский") -> Charge:
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
                    column = FREE_SLOT_COLUMN.get(item.material_type)
                    if column is not None:
                        await conn.execute(
                            text(f"UPDATE users SET {column} = GREATEST({column} - 1, 0) "
                                 f"WHERE id = :uid"),
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
                    continue
                await _ledger(conn, user_id=charge.user_id, kind="refund", amount=item.dirams,
                              before=after - item.dirams, after=after,
                              material_type=item.material_type, reason=reason)
            await db.commit()
        logger.info(f"Refunded {len(pending)} generation(s) to user {charge.user_id}: {reason}")
    except Exception as e:
        logger.error(
            f"REFUND FAILED for user {charge.user_id} ({reason}): {e}. "
            f"Items: {[(i.material_type, i.dirams) for i in charge.items]}",
            exc_info=True,
        )


async def current_balance(user_id: str) -> int:
    async with async_session() as db:
        return (await db.execute(
            text("SELECT balance_dirams FROM users WHERE id = :uid"), {"uid": user_id}
        )).scalar() or 0


async def quote(user_id: str, count: int,
                material_types: list[str] | None = None) -> dict:
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
