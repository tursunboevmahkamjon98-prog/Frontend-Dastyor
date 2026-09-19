import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, delete as sa_delete
from sqlalchemy.orm import aliased
from app.database import get_db
from app.models import (
    User, Konspekt, Lecture, Test, Presentation, PracticalTask, Game,
    BalanceTransaction,
)
from app.schemas import (
    AdminDashboardStats, AdminUserOut, AdminRoleUpdate, AdminPremiumUpdate, AdminBalanceTopUp,
    AdminMaterialOut, AdminMaterialsPage, BalanceTransactionOut,
    AdminSmsRequest, AdminBulkSmsRequest, AdminSmsResult, AdminSmsReport,
)
from app.auth import get_current_admin
from app.logger import get_logger
from app.sms_service import send_sms_text
from app.config import get_settings

logger = get_logger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=AdminDashboardStats)
async def get_admin_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    konspekts = (await db.execute(select(func.count()).select_from(Konspekt))).scalar() or 0
    tests = (await db.execute(select(func.count()).select_from(Test))).scalar() or 0
    presentations = (await db.execute(select(func.count()).select_from(Presentation))).scalar() or 0
    return AdminDashboardStats(
        total_users=users,
        total_konspekts=konspekts,
        total_tests=tests,
        total_presentations=presentations,
        total_materials=konspekts + tests + presentations,
    )


_USER_SORTS = {
    "created_desc": lambda k, t, p: User.created_at.desc(),
    "created_asc": lambda k, t, p: User.created_at.asc(),
    "balance_desc": lambda k, t, p: User.balance_dirams.desc(),
    "balance_asc": lambda k, t, p: User.balance_dirams.asc(),
    "materials_desc": lambda k, t, p: (k + t + p).desc(),
    "materials_asc": lambda k, t, p: (k + t + p).asc(),
    "name_asc": lambda k, t, p: User.full_name.asc(),
}


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    q: str | None = None,
    sort: str = "created_desc",
    premium_only: bool = False,
    admin_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    k_count = (
        select(func.count()).select_from(Konspekt).where(Konspekt.owner_id == User.id).scalar_subquery()
    )
    t_count = (
        select(func.count()).select_from(Test).where(Test.owner_id == User.id).scalar_subquery()
    )
    p_count = (
        select(func.count()).select_from(Presentation).where(Presentation.owner_id == User.id).scalar_subquery()
    )
    query = select(
        User.id, User.full_name, User.email, User.phone, User.role, User.is_premium, User.balance_dirams,
        User.language, User.created_at, User.short_id,
        k_count.label("konspekt_count"), t_count.label("test_count"), p_count.label("presentation_count"),
    )
    if q:
        query = query.where(
            User.phone.ilike(f"%{q}%") | User.email.ilike(f"%{q}%") | User.full_name.ilike(f"%{q}%")
            | User.id.ilike(f"%{q}%") | User.short_id.ilike(f"%{q}%")
        )
    if premium_only:
        query = query.where(User.is_premium.is_(True))
    if admin_only:
        query = query.where(User.role == "admin")
    order = _USER_SORTS.get(sort, _USER_SORTS["created_desc"])(k_count, t_count, p_count)
    query = query.order_by(order).limit(min(limit, 200)).offset(max(offset, 0))

    rows = (await db.execute(query)).all()
    return [
        AdminUserOut(
            id=r.id, full_name=r.full_name, email=r.email, phone=r.phone, role=r.role, is_premium=r.is_premium,
            balance_somoni=r.balance_dirams / 100,
            language=r.language, created_at=r.created_at, konspekt_count=r.konspekt_count, test_count=r.test_count,
            presentation_count=r.presentation_count, short_id=r.short_id,
        )
        for r in rows
    ]


@router.get("/users/count")
async def count_users(
    q: str | None = None,
    premium_only: bool = False,
    admin_only: bool = False,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(func.count()).select_from(User)
    if q:
        query = query.where(
            User.phone.ilike(f"%{q}%") | User.email.ilike(f"%{q}%") | User.full_name.ilike(f"%{q}%")
            | User.id.ilike(f"%{q}%") | User.short_id.ilike(f"%{q}%")
        )
    if premium_only:
        query = query.where(User.is_premium.is_(True))
    if admin_only:
        query = query.where(User.role == "admin")
    total = (await db.execute(query)).scalar() or 0
    return {"total": total}


@router.put("/users/{user_id}/role", response_model=AdminUserOut)
async def update_user_role(
    user_id: str,
    data: AdminRoleUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if data.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="role must be 'user' or 'admin'")
    if user_id == admin.id and data.role != "admin":
        raise HTTPException(status_code=400, detail="You can't remove your own admin role")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = data.role
    await db.flush()
    logger.info(f"Admin {admin.email} set role={data.role} for user {user.email}")

    k = (await db.execute(select(func.count()).select_from(Konspekt).where(Konspekt.owner_id == user.id))).scalar() or 0
    t = (await db.execute(select(func.count()).select_from(Test).where(Test.owner_id == user.id))).scalar() or 0
    p = (await db.execute(select(func.count()).select_from(Presentation).where(Presentation.owner_id == user.id))).scalar() or 0
    return AdminUserOut(
        id=user.id, full_name=user.full_name, email=user.email, phone=user.phone, role=user.role,
        is_premium=user.is_premium, balance_somoni=user.balance_somoni, language=user.language,
        created_at=user.created_at, konspekt_count=k, test_count=t, presentation_count=p,
        short_id=user.short_id,
    )


@router.put("/users/{user_id}/premium", response_model=AdminUserOut)
async def set_premium(
    user_id: str,
    data: AdminPremiumUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_premium = data.is_premium
    await db.flush()
    logger.info(f"Admin {admin.phone} set is_premium={data.is_premium} for user {user.phone}")

    k = (await db.execute(select(func.count()).select_from(Konspekt).where(Konspekt.owner_id == user.id))).scalar() or 0
    t = (await db.execute(select(func.count()).select_from(Test).where(Test.owner_id == user.id))).scalar() or 0
    p = (await db.execute(select(func.count()).select_from(Presentation).where(Presentation.owner_id == user.id))).scalar() or 0
    return AdminUserOut(
        id=user.id, full_name=user.full_name, email=user.email, phone=user.phone, role=user.role,
        is_premium=user.is_premium, balance_somoni=user.balance_somoni, language=user.language,
        created_at=user.created_at, konspekt_count=k, test_count=t, presentation_count=p,
        short_id=user.short_id,
    )


@router.put("/users/{user_id}/balance", response_model=AdminUserOut)
async def add_balance(
    user_id: str,
    data: AdminBalanceTopUp,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    amount_dirams = round(data.amount_somoni * 100)
    if amount_dirams <= 0:
        raise HTTPException(status_code=400, detail="amount_somoni must be positive")

    new_balance = (await db.execute(
        text(
            "UPDATE users SET balance_dirams = balance_dirams + :amt "
            "WHERE id = :uid RETURNING balance_dirams"
        ),
        {"uid": user_id, "amt": amount_dirams},
    )).scalar()
    if new_balance is None:
        raise HTTPException(status_code=404, detail="User not found")

    db.add(BalanceTransaction(
        id=str(uuid.uuid4()),
        user_id=user_id,
        kind="topup",
        amount_dirams=amount_dirams,
        balance_before=new_balance - amount_dirams,
        balance_after=new_balance,
        actor_id=admin.id,
        reason=(data.reason or "").strip()[:255] or "admin top-up",
    ))
    await db.flush()

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
    logger.info(
        f"Admin {admin.id} credited {data.amount_somoni} somoni to user {user_id} "
        f"(new balance: {new_balance / 100}) reason={data.reason!r}"
    )

    k = (await db.execute(select(func.count()).select_from(Konspekt).where(Konspekt.owner_id == user.id))).scalar() or 0
    t = (await db.execute(select(func.count()).select_from(Test).where(Test.owner_id == user.id))).scalar() or 0
    p = (await db.execute(select(func.count()).select_from(Presentation).where(Presentation.owner_id == user.id))).scalar() or 0
    return AdminUserOut(
        id=user.id, full_name=user.full_name, email=user.email, phone=user.phone, role=user.role,
        is_premium=user.is_premium, balance_somoni=user.balance_somoni, language=user.language,
        created_at=user.created_at, konspekt_count=k, test_count=t, presentation_count=p,
        short_id=user.short_id,
    )


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You can't delete your own account from here")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    logger.info(f"Admin {admin.email} deleted user {user.email}")


_MATERIAL_MODELS = {
    "konspekt": Konspekt,
    "lektsiya": Lecture,
    "test": Test,
    "prezentatsiya": Presentation,
    "amaliy": PracticalTask,
    "igra": Game,
}


async def _query_materials(db: AsyncSession, type: str | None, q: str | None,
                           owner_id: str | None = None):
    if type is not None and type not in _MATERIAL_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown material type: {type}")
    types = [type] if type else list(_MATERIAL_MODELS.keys())
    out = []
    for t in types:
        model = _MATERIAL_MODELS[t]
        query = select(model.id, model.title, model.subject, model.grade, model.owner_id, model.created_at)
        if q:
            query = query.where(model.title.ilike(f"%{q}%") | model.subject.ilike(f"%{q}%"))
        if owner_id:
            query = query.where(model.owner_id == owner_id)
        rows = (await db.execute(query)).all()
        out.extend((t, r) for r in rows)
    return out


@router.get("/materials", response_model=AdminMaterialsPage)
async def list_materials(
    type: str | None = None,
    q: str | None = None,
    user_id: str | None = None,
    limit: int = 30,
    offset: int = 0,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    tagged = await _query_materials(db, type, q, owner_id=user_id)
    tagged.sort(key=lambda pair: pair[1].created_at, reverse=True)
    total = len(tagged)
    page = tagged[offset: offset + min(limit, 100)]

    owner_ids = {r.owner_id for _, r in page}
    owners: dict[str, User] = {}
    if owner_ids:
        owner_rows = (await db.execute(select(User).where(User.id.in_(owner_ids)))).scalars().all()
        owners = {u.id: u for u in owner_rows}

    items = []
    for t, r in page:
        owner = owners.get(r.owner_id)
        items.append(AdminMaterialOut(
            id=r.id, type=t, title=r.title, subject=r.subject, grade=r.grade,
            owner_id=r.owner_id, owner_name=owner.full_name if owner else "?",
            owner_phone=owner.phone if owner else None, created_at=r.created_at,
        ))
    return AdminMaterialsPage(items=items, total=total)


@router.delete("/materials/{type}/{item_id}", status_code=204)
async def delete_material(
    type: str,
    item_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    model = _MATERIAL_MODELS.get(type)
    if model is None:
        raise HTTPException(status_code=400, detail=f"Unknown material type: {type}")
    result = await db.execute(select(model).where(model.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Material not found")
    await db.delete(item)
    logger.info(f"Admin {admin.email} deleted {type} {item_id}")



async def _send_to_user(user: User, text: str) -> AdminSmsResult:
    dry_run = get_settings().SMS_DRY_RUN
    if not user.phone:
        return AdminSmsResult(
            user_id=user.id, full_name=user.full_name, phone=None,
            sent=False, error="У пользователя нет номера телефона", dry_run=dry_run,
        )
    try:
        ok = await send_sms_text(user.phone, text)
    except Exception as e:
        logger.error(f"Admin SMS to {user.id} raised: {e}", exc_info=True)
        return AdminSmsResult(
            user_id=user.id, full_name=user.full_name, phone=user.phone,
            sent=False, error=f"{type(e).__name__}: {e}", dry_run=dry_run,
        )
    return AdminSmsResult(
        user_id=user.id, full_name=user.full_name, phone=user.phone,
        sent=ok, error=None if ok else "Оператор не подтвердил отправку", dry_run=dry_run,
    )


@router.post("/users/{user_id}/sms", response_model=AdminSmsResult)
async def send_sms_to_user(
    user_id: str,
    data: AdminSmsRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    outcome = await _send_to_user(user, data.text)
    logger.info(
        f"Admin {admin.email} sent SMS to {user.id} ({outcome.phone}): "
        f"sent={outcome.sent} len={len(data.text)}"
    )
    return outcome


@router.post("/sms", response_model=AdminSmsReport)
async def send_sms_to_users(
    data: AdminBulkSmsRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(User).where(User.id.in_(data.user_ids)))).scalars().all()
    found = {u.id: u for u in rows}

    results: list[AdminSmsResult] = []
    for user_id in data.user_ids:
        user = found.get(user_id)
        if user is None:
            results.append(AdminSmsResult(
                user_id=user_id, full_name="?", phone=None,
                sent=False, error="Пользователь не найден",
            ))
            continue
        results.append(await _send_to_user(user, data.text))

    sent = sum(1 for r in results if r.sent)
    logger.info(
        f"Admin {admin.email} sent SMS to {len(data.user_ids)} users: "
        f"{sent} delivered, {len(results) - sent} failed, len={len(data.text)}"
    )
    return AdminSmsReport(
        sent=sent, failed=len(results) - sent,
        dry_run=get_settings().SMS_DRY_RUN, results=results,
    )


@router.get("/users/{user_id}/balance-history", response_model=list[BalanceTransactionOut])
async def balance_history(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    actor = aliased(User)
    rows = (await db.execute(
        select(BalanceTransaction, actor.full_name)
        .outerjoin(actor, actor.id == BalanceTransaction.actor_id)
        .where(BalanceTransaction.user_id == user_id)
        .order_by(BalanceTransaction.created_at.desc())
        .limit(min(limit, 200))
        .offset(max(offset, 0))
    )).all()
    return [
        BalanceTransactionOut(
            id=tx.id,
            kind=tx.kind,
            amount_somoni=tx.amount_dirams / 100,
            balance_before_somoni=tx.balance_before / 100,
            balance_after_somoni=tx.balance_after / 100,
            actor_name=actor_name,
            reason=tx.reason,
            material_type=tx.material_type,
            created_at=tx.created_at,
        )
        for tx, actor_name in rows
    ]
