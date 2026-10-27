"""Cards and Expenses CRUD — pytest.

Run via pytest (conftest.py in this directory does the test-database
setup):

    python -m pytest tests/test_cards_expenses_crud.py -v

Covers Stage 3 of the CRM build: app/routers/admin_crm.py's Cards and
Expenses endpoints. The two guarantees that matter here are not about
money moving correctly (neither table can move money at all) but about
it NOT moving: this suite asserts balance_dirams and balance_transactions
are untouched by any Cards/Expenses call, and that a card's plaintext
number only ever appears decrypted behind the one gated detail
endpoint - everywhere else it is masked.

created_by on both tables is a real FK to users.id, so every test here
uses a real make_user()-created row as the "admin" actor rather than a
bare string id - a fabricated id would just fail the FK constraint on
insert.

Needs backend/.env to have a real CARD_ENCRYPTION_KEY set (added
alongside this stage) - without one, every card endpoint answers 503 by
design, and these tests would have nothing to test.
"""

import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from conftest import async_test  # noqa: E402
from test_telegram_payments import balance_of, cleanup_user, make_user  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import async_session  # noqa: E402
from app.routers.admin_crm import (  # noqa: E402
    _mask_card_number,
    create_card,
    create_expense,
    delete_card,
    delete_expense,
    get_card_detail,
    list_cards,
    list_expenses,
    update_card,
    update_expense,
)
from app.schemas import CardCreate, CardUpdate, ExpenseCreate, ExpenseUpdate  # noqa: E402
from app.telegram import service  # noqa: E402


class _FakeAdmin:
    def __init__(self, id: str, full_name: str = "Test Admin"):
        self.id = id
        self.full_name = full_name


async def _make_actor() -> _FakeAdmin:
    uid = await make_user()
    return _FakeAdmin(id=uid)


async def _cleanup_cards(*card_ids: str) -> None:
    async with async_session() as db:
        for cid in card_ids:
            await db.execute(text("DELETE FROM payment_cards WHERE id = :id"), {"id": cid})
        await db.commit()


async def _cleanup_expenses(*expense_ids: str) -> None:
    async with async_session() as db:
        for eid in expense_ids:
            await db.execute(text("DELETE FROM expenses WHERE id = :id"), {"id": eid})
        await db.commit()


async def _clear_pay_instructions() -> None:
    async with async_session() as db:
        await db.execute(text(
            "DELETE FROM telegram_bot_state WHERE key = 'pay_instructions'"
        ))
        await db.commit()


def test_mask_card_number_keeps_only_last_four():
    assert _mask_card_number("1234567890123456") == "••••••••••••3456"
    assert _mask_card_number("12") == "••"
    assert _mask_card_number("1234") == "••••"


@async_test
async def test_create_card_round_trips_through_pgcrypto():
    assert get_settings().CARD_ENCRYPTION_KEY, (
        "backend/.env needs a real CARD_ENCRYPTION_KEY for this suite to test anything"
    )
    actor = await _make_actor()
    async with async_session() as db:
        created = await create_card(
            data=CardCreate(
                bank_name="Корти Милли", holder_name="Dastyor LLC",
                card_number="9154123456781234", currency="TJS",
            ),
            admin=actor, db=db,
        )
        await db.commit()
    try:
        assert created.card_number_masked == "••••••••••••1234"

        async with async_session() as db:
            detail = await get_card_detail(card_id=created.id, admin=actor, db=db)
        assert detail.card_number == "9154123456781234", (
            "the detail endpoint must decrypt to exactly what was written"
        )
    finally:
        await _cleanup_cards(created.id)
        await cleanup_user(actor.id)


@async_test
async def test_list_cards_never_exposes_plaintext():
    actor = await _make_actor()
    async with async_session() as db:
        created = await create_card(
            data=CardCreate(bank_name="Bank", holder_name="Holder", card_number="4000111122223333"),
            admin=actor, db=db,
        )
        await db.commit()
    try:
        async with async_session() as db:
            rows = await list_cards(admin=actor, db=db)
        match = next(r for r in rows if r.id == created.id)
        assert match.card_number_masked.endswith("3333")
        assert "4000111122223333" not in match.card_number_masked
        assert not hasattr(match, "card_number")  # CardOut has no plaintext field at all
    finally:
        await _cleanup_cards(created.id)
        await cleanup_user(actor.id)


@async_test
async def test_activating_a_card_updates_pay_instructions():
    actor = await _make_actor()
    async with async_session() as db:
        created = await create_card(
            data=CardCreate(
                bank_name="Алиф Банк", holder_name="Dastyor",
                card_number="5555000011112222", is_active=True,
            ),
            admin=actor, db=db,
        )
        await db.commit()
    try:
        shown = await service.get_pay_instructions()
        assert "5555000011112222" in shown
        assert "Алиф Банк" in shown

        async with async_session() as db:
            await update_card(
                card_id=created.id, data=CardUpdate(is_active=False), admin=actor, db=db,
            )
            await db.commit()

        shown_after = await service.get_pay_instructions()
        assert "5555000011112222" not in shown_after, (
            "deactivating a card must remove it from what /pay shows"
        )
    finally:
        await _cleanup_cards(created.id)
        await cleanup_user(actor.id)
        await _clear_pay_instructions()


@async_test
async def test_card_crud_never_touches_balance():
    actor = await _make_actor()
    uid = await make_user(balance_dirams=1000)
    try:
        before = await balance_of(uid)

        async with async_session() as db:
            created = await create_card(
                data=CardCreate(bank_name="B", holder_name="H", card_number="1111222233334444"),
                admin=actor, db=db,
            )
            await db.commit()
        try:
            async with async_session() as db:
                await update_card(
                    card_id=created.id, data=CardUpdate(note="updated"), admin=actor, db=db,
                )
                await db.commit()

            async with async_session() as db:
                tx_count = (await db.execute(text(
                    "SELECT count(*) FROM balance_transactions WHERE user_id = :uid"
                ), {"uid": uid})).scalar()
            assert tx_count == 0
            assert await balance_of(uid) == before
        finally:
            async with async_session() as db:
                await delete_card(card_id=created.id, admin=actor, db=db)
                await db.commit()
    finally:
        await cleanup_user(uid)
        await cleanup_user(actor.id)
        await _clear_pay_instructions()


@async_test
async def test_delete_card_404s_for_unknown_id():
    actor = await _make_actor()
    try:
        async with async_session() as db:
            with pytest.raises(HTTPException) as exc_info:
                await delete_card(card_id=str(uuid.uuid4()), admin=actor, db=db)
            assert exc_info.value.status_code == 404
    finally:
        await cleanup_user(actor.id)


# ---------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------

@async_test
async def test_create_expense_converts_somoni_to_dirams():
    actor = await _make_actor()
    try:
        async with async_session() as db:
            created = await create_expense(
                data=ExpenseCreate(
                    category="hosting", amount_somoni=49.50,
                    spent_at=datetime.now(timezone.utc),
                ),
                admin=actor, db=db,
            )
            await db.commit()
        try:
            assert created.amount_somoni == 49.50

            async with async_session() as db:
                amount_dirams = (await db.execute(text(
                    "SELECT amount_dirams FROM expenses WHERE id = :id"
                ), {"id": created.id})).scalar()
            assert amount_dirams == 4950
        finally:
            await _cleanup_expenses(created.id)
    finally:
        await cleanup_user(actor.id)


@async_test
async def test_expense_crud_never_touches_balance_tables():
    actor = await _make_actor()
    try:
        async with async_session() as db:
            created = await create_expense(
                data=ExpenseCreate(category="ads", amount_somoni=10, spent_at=datetime.now(timezone.utc)),
                admin=actor, db=db,
            )
            await db.commit()
        try:
            async with async_session() as db:
                await update_expense(
                    expense_id=created.id, data=ExpenseUpdate(amount_somoni=15), admin=actor, db=db,
                )
                await db.commit()

            async with async_session() as db:
                updated = (await db.execute(text(
                    "SELECT amount_dirams FROM expenses WHERE id = :id"
                ), {"id": created.id})).scalar()
            assert updated == 1500

            async with async_session() as db:
                orphan_tx = (await db.execute(text(
                    "SELECT count(*) FROM balance_transactions WHERE reason LIKE '%expense%'"
                ))).scalar()
            assert orphan_tx == 0
        finally:
            async with async_session() as db:
                await delete_expense(expense_id=created.id, admin=actor, db=db)
                await db.commit()
    finally:
        await cleanup_user(actor.id)


@async_test
async def test_list_expenses_filters_by_category():
    actor = await _make_actor()
    try:
        async with async_session() as db:
            a = await create_expense(
                data=ExpenseCreate(category="hosting_filter_test", amount_somoni=5,
                                   spent_at=datetime.now(timezone.utc)),
                admin=actor, db=db,
            )
            b = await create_expense(
                data=ExpenseCreate(category="other_filter_test", amount_somoni=5,
                                   spent_at=datetime.now(timezone.utc)),
                admin=actor, db=db,
            )
            await db.commit()
        try:
            async with async_session() as db:
                rows = await list_expenses(category="hosting_filter_test", admin=actor, db=db)
            assert all(r.category == "hosting_filter_test" for r in rows)
            assert any(r.id == a.id for r in rows)
            assert not any(r.id == b.id for r in rows)
        finally:
            await _cleanup_expenses(a.id, b.id)
    finally:
        await cleanup_user(actor.id)
