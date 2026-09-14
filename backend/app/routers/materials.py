import asyncio
import json
import io
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db, async_session
from app.models import User, Konspekt, Presentation, Test, Lecture, PracticalTask, Game, GameAttempt
from app.schemas import (
    KonspektCreate, KonspektUpdate, KonspektOut,
    PresentationCreate, PresentationUpdate, PresentationOut,
    TestCreate, TestUpdate, TestOut,
    LectureCreate, LectureUpdate, LectureOut,
    PracticalTaskCreate, PracticalTaskUpdate, PracticalTaskOut,
    GameCreate, GameUpdate, GameOut, GameAttemptCreate, GameAttemptOut,
    DashboardStats,
    GenerateRequest, GenerateResponse,
    GenerateKonspektStreamRequest,
    GenerateAllRequest,
    RegenerateItemRequest,
    RetryLessonImageRequest,
    RegenerateGameRequest,
    QuizSetRequest, QuizSetResponse, QuizSetQuestion,
    ChatEditRequest,
)
from app.auth import get_current_user
from app.ai_service import (
    generate_material, generate_all_materials, regenerate_item, generate_konspekt_stream,
    retry_lesson_image,
    chat_edit_material, summarize_previous_konspekt, summarize_previous_presentation,
    retry_visual_assets, generate_quiz_set,
)
from app.document_extract import extract_source_text
from app.docx_builder import (
    build_konspekt_docx, build_lecture_docx, build_test_docx, build_presentation_docx,
    build_practical_docx,
)
from app.export_builder import (
    build_presentation_pptx, build_konspekt_pdf, build_lecture_pdf, build_test_pdf, build_presentation_pdf,
    build_practical_pdf, _PRACTICAL_UI,
)
from app import limits, pptx_pdf
from app.security import enforce_user_quota
from app.logger import get_logger
from app.i18n import get_message
from app.config import get_settings

settings = get_settings()

logger = get_logger(__name__)
router = APIRouter(prefix="/api/materials", tags=["materials"])

_MATERIAL_MODELS = {
    "konspekt": Konspekt,
    "test": Test,
    "prezentatsiya": Presentation,
    "lektsiya": Lecture,
    "amaliy": PracticalTask,
    "igra": Game,
}

# The generation limit lives entirely in app/limits.py now — one free
# material per ACCOUNT (not one per type, which is what the six
# free_*_used flags below used to mean), then GENERATION_PRICE_DIRAMS for
# every one after it, claimed with an atomic conditional UPDATE before
# the AI call and refunded if the call fails. See that module's docstring
# for why the old read-check-generate-then-deduct shape here was
# defeatable by simply sending the same request twice at once.
#
# Re-exported under their old names because routers/curriculum.py imports
# them from this module.
GENERATION_PRICE_DIRAMS = limits.GENERATION_PRICE_DIRAMS
_PILOT_FREE_FOR_ALL = limits.PILOT_FREE_FOR_ALL

# The columns behind the per-type free tier. limits.FREE_SLOT_COLUMN is
# what reserve()/refund()/quote() actually read and write today, and it
# covers only the four types that have a free slot; this map is the wider
# historical set, kept for database.py's init_db backfills.
_FREE_USED_ATTR = {
    "konspekt": "free_konspekt_used",
    "lektsiya": "free_lektsiya_used",
    "test": "free_test_used",
    "prezentatsiya": "free_prezentatsiya_used",
    "amaliy": "free_amaliy_used",
    "igra": "free_igra_used",
}


async def enforce_generation_quota(user: User) -> None:
    """Caps how many generations ONE ACCOUNT can start per hour.

    Distinct from both of the other limits and not covered by either.
    The balance in app/limits.py bounds what a teacher can spend, not
    how fast — an account with a large credited balance can still open
    a hundred generations in a minute and saturate the AI queue for
    everyone else. rate_limit.py's per-IP cap can't see it either: the
    same account across a phone, a laptop and a script is three
    addresses, and one address behind CGNAT is many accounts.

    Sized well above real teaching use (a lesson kit is 5 materials, a
    curriculum month is ~25 days) so it only ever bites on scripted
    traffic."""
    await enforce_user_quota(
        user.id, "generate", get_settings().MAX_GENERATIONS_PER_HOUR
    )


async def enforce_ai_edit_quota(user: User) -> None:
    """The same idea for the cheaper-but-still-AI endpoints — chat-edit,
    per-item regeneration, quiz sets, game rerolls. These charge nothing
    against the balance (they refine a material the teacher already paid
    for rather than producing a new one), which means the balance is not
    a limit on them at all and this is the only thing bounding how many
    an account can run."""
    await enforce_user_quota(
        user.id, "ai_edit", get_settings().MAX_AI_EDITS_PER_HOUR
    )


def require_game_access(user: User, material_type: str) -> None:
    """The game section is not generally available yet.

    Hiding the entry points in the web app and the APK is presentation,
    not access control: the endpoints stay reachable with a bearer token
    and curl, and a hidden button is one devtools inspection away from
    being clicked anyway. This is the check that actually decides, and it
    runs on every path that can create, reroll or record a game.

    Gate is the admin role plus an explicit allow-list of account ids in
    GAME_ACCESS_USER_IDS, so the feature can be opened to a named tester
    without making them an administrator. 403 rather than 404: an
    authenticated teacher should be told the feature isn't open to them,
    not left guessing whether it exists."""
    if material_type != "igra":
        return
    if user.role == "admin":
        return
    allowed = {u.strip() for u in settings.GAME_ACCESS_USER_IDS.split(",") if u.strip()}
    if user.id in allowed or (user.short_id and user.short_id in allowed):
        return
    logger.warning(f"Game access denied for user {user.id} (role={user.role})")
    raise HTTPException(status_code=403, detail=get_message("game_locked", user.language))


# ── Dashboard stats ──────────────────────────────────────────────────────────

@router.get("/stats", response_model=DashboardStats)
async def get_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        k = await db.execute(select(func.count()).where(Konspekt.owner_id == user.id))
        t = await db.execute(select(func.count()).where(Test.owner_id == user.id))
        p = await db.execute(select(func.count()).where(Presentation.owner_id == user.id))
        l = await db.execute(select(func.count()).where(Lecture.owner_id == user.id))
        a = await db.execute(select(func.count()).where(PracticalTask.owner_id == user.id))
        g = await db.execute(select(func.count()).where(Game.owner_id == user.id))

        stats = DashboardStats(
            konspekt_count=k.scalar() or 0,
            test_count=t.scalar() or 0,
            presentation_count=p.scalar() or 0,
            lecture_count=l.scalar() or 0,
            practical_count=a.scalar() or 0,
            game_count=g.scalar() or 0,
        )
        logger.info(f"Stats fetched for user {user.email}: k={stats.konspekt_count} t={stats.test_count} p={stats.presentation_count}")
        return stats
    except Exception as e:
        logger.error(f"Stats fetch error for user {user.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")



# ── Search All Materials ─────────────────────────────────────────────────────

@router.get("/search")
async def search_materials(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    q: str = "",
    subject: str | None = None,
    grade: str | None = None,
):
    results = []
    for model_cls, type_name in [(Konspekt, "konspekt"), (Test, "test"), (Presentation, "prezentatsiya"), (Lecture, "lektsiya"),
                                 (PracticalTask, "amaliy"), (Game, "igra")]:
        query = select(model_cls).where(model_cls.owner_id == user.id)
        if q:
            query = query.where(model_cls.title.ilike(f"%{q}%"))
        if subject:
            query = query.where(model_cls.subject == subject)
        if grade:
            query = query.where(model_cls.grade == grade)
        items = (await db.execute(query.order_by(model_cls.created_at.desc()).limit(20))).scalars().all()
        for item in items:
            results.append({
                "id": item.id,
                "type": type_name,
                "title": item.title,
                "subject": item.subject,
                "grade": item.grade,
                "is_favorite": item.is_favorite,
                "created_at": item.created_at.isoformat(),
            })
    results.sort(key=lambda x: x["created_at"], reverse=True)
    return results


# ── Konspekts ───────────────────────────────────────────────────────────────

@router.post("/konspekts", response_model=KonspektOut, status_code=201)
async def create_konspekt(
    data: KonspektCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = Konspekt(**data.model_dump(), owner_id=user.id)
    db.add(item)
    await db.flush()
    return KonspektOut.model_validate(item)


@router.get("/konspekts", response_model=list[KonspektOut])
async def list_konspekts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    q: str | None = None,
    subject: str | None = None,
    grade: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    query = select(Konspekt).where(
        Konspekt.owner_id == user.id,
    )
    if q:
        query = query.where(Konspekt.title.ilike(f"%{q}%"))
    if subject:
        query = query.where(Konspekt.subject == subject)
    if grade:
        query = query.where(Konspekt.grade == grade)
    query = query.order_by(Konspekt.is_favorite.desc(), Konspekt.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return [KonspektOut.model_validate(i) for i in result.scalars().all()]


@router.get("/konspekts/{item_id}", response_model=KonspektOut)
async def get_konspekt(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Konspekt).where(Konspekt.id == item_id, Konspekt.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return KonspektOut.model_validate(item)


@router.put("/konspekts/{item_id}", response_model=KonspektOut)
async def update_konspekt(
    item_id: str,
    data: KonspektUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Konspekt).where(Konspekt.id == item_id, Konspekt.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    updates = data.model_dump(exclude_unset=True)
    # Snapshot the content as it was right before this change — the one
    # step a teacher can undo (e.g. after a section regeneration they end
    # up not liking) instead of the old content being gone the instant it
    # gets overwritten. Only when content is actually changing, so a
    # title/favorite-only update doesn't create a pointless checkpoint.
    if "content" in updates and updates["content"] != item.content:
        item.previous_content = item.content
    for k, v in updates.items():
        setattr(item, k, v)
    await db.flush()
    return KonspektOut.model_validate(item)


@router.post("/konspekts/{item_id}/undo", response_model=KonspektOut)
async def undo_konspekt_content(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Restores `content` to what it was right before the last change —
    single-level undo (see Konspekt.previous_content), not a full history."""
    result = await db.execute(
        select(Konspekt).where(Konspekt.id == item_id, Konspekt.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    if item.previous_content is None:
        raise HTTPException(status_code=400, detail="Nothing to undo")
    item.content, item.previous_content = item.previous_content, None
    await db.flush()
    return KonspektOut.model_validate(item)


@router.post("/konspekts/{item_id}/fetch-image", response_model=KonspektOut)
async def retry_konspekt_image(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retries the real-world photo/map the original generation asked for
    but didn't get (see ai_service.retry_visual_assets's docstring) — the
    only way to get one short of regenerating the whole konspekt, since
    that fetch never re-runs on its own once the document is saved."""
    result = await db.execute(
        select(Konspekt).where(Konspekt.id == item_id, Konspekt.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    content = json.loads(item.content or "{}")
    changed = await retry_visual_assets(content, item.title, item.subject)
    if not changed:
        raise HTTPException(status_code=404, detail="Нет изображения для загрузки")
    item.content = json.dumps(content, ensure_ascii=False)
    await db.flush()
    return KonspektOut.model_validate(item)


@router.post("/konspekts/{item_id}/replace-image", response_model=KonspektOut)
async def replace_konspekt_lesson_image(
    item_id: str,
    data: RetryLessonImageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Swaps ONE lesson_images entry (index `data.index`) for a different
    Commons result on the same query — unlike fetch-image above, this
    fires even when the slot already has a picture; it's "I have one, I
    want a DIFFERENT one," not "I have none." See
    ai_service.retry_lesson_image's docstring for why this never touches
    the shared LessonImageCache."""
    result = await db.execute(
        select(Konspekt).where(Konspekt.id == item_id, Konspekt.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    content = json.loads(item.content or "{}")
    changed = await retry_lesson_image(content, item.title, data.index)
    if not changed:
        raise HTTPException(status_code=404, detail="Не удалось найти другое изображение")
    item.content = json.dumps(content, ensure_ascii=False)
    await db.flush()
    return KonspektOut.model_validate(item)


@router.post("/konspekts/{item_id}/upload-image", response_model=KonspektOut)
async def upload_konspekt_lesson_image(
    item_id: str,
    index: int = 0,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lets a teacher place their OWN photo/diagram into a konspekt
    instead of only ever getting whatever Commons search returned — the
    one thing neither fetch-image nor replace-image above can do, since
    both only ever pick from Commons. Overwrites the lesson_images entry
    at `index` if one exists there (keeping its position_after so the
    picture stays anchored to the same section); appends a new entry
    otherwise, capped at the usual 2-picture limit every other path here
    already enforces."""
    result = await db.execute(
        select(Konspekt).where(Konspekt.id == item_id, Konspekt.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    raw = await file.read()
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Файл слишком большой (макс. 8 МБ)")
    from app.image_builder import _save_lesson_image
    saved = _save_lesson_image(raw)
    if not saved:
        raise HTTPException(status_code=422, detail="Не удалось прочитать изображение")
    path, width, height = saved
    content = json.loads(item.content or "{}")
    images = content.get("lesson_images")
    images = list(images) if isinstance(images, list) else []
    old_anchor = images[index].get("position_after", "") if 0 <= index < len(images) and isinstance(images[index], dict) else ""
    entry = {
        "path": path, "caption": "", "credit": "Загружено учителем", "explanation": "",
        "width": width, "height": height, "position_after": old_anchor,
    }
    if 0 <= index < len(images):
        images[index] = entry
    else:
        images = (images + [entry])[:2]
    content["lesson_images"] = images
    item.content = json.dumps(content, ensure_ascii=False)
    await db.flush()
    return KonspektOut.model_validate(item)


@router.delete("/konspekts/{item_id}", status_code=204)
async def delete_konspekt(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Konspekt).where(Konspekt.id == item_id, Konspekt.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)


# ── Lectures (лекция — explains a topic; конспект manages a lesson) ─────────

@router.post("/lectures", response_model=LectureOut, status_code=201)
async def create_lecture(
    data: LectureCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = Lecture(**data.model_dump(), owner_id=user.id)
    db.add(item)
    await db.flush()
    return LectureOut.model_validate(item)


@router.get("/lectures", response_model=list[LectureOut])
async def list_lectures(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    q: str | None = None,
    subject: str | None = None,
    grade: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    query = select(Lecture).where(Lecture.owner_id == user.id)
    if q:
        query = query.where(Lecture.title.ilike(f"%{q}%"))
    if subject:
        query = query.where(Lecture.subject == subject)
    if grade:
        query = query.where(Lecture.grade == grade)
    query = query.order_by(Lecture.is_favorite.desc(), Lecture.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return [LectureOut.model_validate(i) for i in result.scalars().all()]


@router.get("/lectures/{item_id}", response_model=LectureOut)
async def get_lecture(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Lecture).where(Lecture.id == item_id, Lecture.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return LectureOut.model_validate(item)


@router.put("/lectures/{item_id}", response_model=LectureOut)
async def update_lecture(
    item_id: str,
    data: LectureUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Lecture).where(Lecture.id == item_id, Lecture.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    updates = data.model_dump(exclude_unset=True)
    if "content" in updates and updates["content"] != item.content:
        item.previous_content = item.content
    for k, v in updates.items():
        setattr(item, k, v)
    await db.flush()
    return LectureOut.model_validate(item)


@router.post("/lectures/{item_id}/undo", response_model=LectureOut)
async def undo_lecture_content(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Lecture).where(Lecture.id == item_id, Lecture.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    if item.previous_content is None:
        raise HTTPException(status_code=400, detail="Nothing to undo")
    item.content, item.previous_content = item.previous_content, None
    await db.flush()
    return LectureOut.model_validate(item)


@router.post("/lectures/{item_id}/fetch-image", response_model=LectureOut)
async def retry_lecture_image(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lecture (лекция) counterpart of retry_konspekt_image — see that
    endpoint's docstring."""
    result = await db.execute(
        select(Lecture).where(Lecture.id == item_id, Lecture.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    content = json.loads(item.content or "{}")
    changed = await retry_visual_assets(content, item.title, item.subject)
    if not changed:
        raise HTTPException(status_code=404, detail="Нет изображения для загрузки")
    item.content = json.dumps(content, ensure_ascii=False)
    await db.flush()
    return LectureOut.model_validate(item)


@router.post("/lectures/{item_id}/replace-image", response_model=LectureOut)
async def replace_lecture_lesson_image(
    item_id: str,
    data: RetryLessonImageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lecture (лекция) counterpart of replace_konspekt_lesson_image — see
    that endpoint's docstring."""
    result = await db.execute(
        select(Lecture).where(Lecture.id == item_id, Lecture.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    content = json.loads(item.content or "{}")
    changed = await retry_lesson_image(content, item.title, data.index)
    if not changed:
        raise HTTPException(status_code=404, detail="Не удалось найти другое изображение")
    item.content = json.dumps(content, ensure_ascii=False)
    await db.flush()
    return LectureOut.model_validate(item)


@router.post("/lectures/{item_id}/upload-image", response_model=LectureOut)
async def upload_lecture_lesson_image(
    item_id: str,
    index: int = 0,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lecture (лекция) counterpart of upload_konspekt_lesson_image — see
    that endpoint's docstring."""
    result = await db.execute(
        select(Lecture).where(Lecture.id == item_id, Lecture.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    raw = await file.read()
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Файл слишком большой (макс. 8 МБ)")
    from app.image_builder import _save_lesson_image
    saved = _save_lesson_image(raw)
    if not saved:
        raise HTTPException(status_code=422, detail="Не удалось прочитать изображение")
    path, width, height = saved
    content = json.loads(item.content or "{}")
    images = content.get("lesson_images")
    images = list(images) if isinstance(images, list) else []
    old_anchor = images[index].get("position_after", "") if 0 <= index < len(images) and isinstance(images[index], dict) else ""
    entry = {
        "path": path, "caption": "", "credit": "Загружено учителем", "explanation": "",
        "width": width, "height": height, "position_after": old_anchor,
    }
    if 0 <= index < len(images):
        images[index] = entry
    else:
        images = (images + [entry])[:2]
    content["lesson_images"] = images
    item.content = json.dumps(content, ensure_ascii=False)
    await db.flush()
    return LectureOut.model_validate(item)


@router.delete("/lectures/{item_id}", status_code=204)
async def delete_lecture(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Lecture).where(Lecture.id == item_id, Lecture.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)


# ── Presentations ────────────────────────────────────────────────────────────

@router.post("/presentations", response_model=PresentationOut, status_code=201)
async def create_presentation(
    data: PresentationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = Presentation(**data.model_dump(), owner_id=user.id)
    db.add(item)
    await db.flush()
    return PresentationOut.model_validate(item)


@router.get("/presentations", response_model=list[PresentationOut])
async def list_presentations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    q: str | None = None,
    subject: str | None = None,
    grade: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    query = select(Presentation).where(Presentation.owner_id == user.id)
    if q:
        query = query.where(Presentation.title.ilike(f"%{q}%"))
    if subject:
        query = query.where(Presentation.subject == subject)
    if grade:
        query = query.where(Presentation.grade == grade)
    query = query.order_by(Presentation.is_favorite.desc(), Presentation.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return [PresentationOut.model_validate(i) for i in result.scalars().all()]


@router.get("/presentations/{item_id}", response_model=PresentationOut)
async def get_presentation(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Presentation).where(Presentation.id == item_id, Presentation.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return PresentationOut.model_validate(item)


@router.put("/presentations/{item_id}", response_model=PresentationOut)
async def update_presentation(
    item_id: str,
    data: PresentationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Presentation).where(Presentation.id == item_id, Presentation.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    await db.flush()
    return PresentationOut.model_validate(item)


@router.delete("/presentations/{item_id}", status_code=204)
async def delete_presentation(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Presentation).where(Presentation.id == item_id, Presentation.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)


# ── Tests ────────────────────────────────────────────────────────────────────

@router.post("/tests", response_model=TestOut, status_code=201)
async def create_test(
    data: TestCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = Test(**data.model_dump(), owner_id=user.id)
    db.add(item)
    await db.flush()
    return TestOut.model_validate(item)


@router.get("/tests", response_model=list[TestOut])
async def list_tests(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    q: str | None = None,
    subject: str | None = None,
    grade: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    query = select(Test).where(
        Test.owner_id == user.id,
    )
    if q:
        query = query.where(Test.title.ilike(f"%{q}%"))
    if subject:
        query = query.where(Test.subject == subject)
    if grade:
        query = query.where(Test.grade == grade)
    query = query.order_by(Test.is_favorite.desc(), Test.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return [TestOut.model_validate(i) for i in result.scalars().all()]


@router.get("/tests/{item_id}", response_model=TestOut)
async def get_test(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Test).where(Test.id == item_id, Test.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return TestOut.model_validate(item)


@router.put("/tests/{item_id}", response_model=TestOut)
async def update_test(
    item_id: str,
    data: TestUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Test).where(Test.id == item_id, Test.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    await db.flush()
    return TestOut.model_validate(item)


@router.delete("/tests/{item_id}", status_code=204)
async def delete_test(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Test).where(Test.id == item_id, Test.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)


# ── Practical tasks ("💡 Амалӣ супоришҳо") ────────────────────────────────────

@router.post("/practical-tasks", response_model=PracticalTaskOut, status_code=201)
async def create_practical_task(
    data: PracticalTaskCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = PracticalTask(**data.model_dump(), owner_id=user.id)
    db.add(item)
    await db.flush()
    return PracticalTaskOut.model_validate(item)


@router.get("/practical-tasks", response_model=list[PracticalTaskOut])
async def list_practical_tasks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    q: str | None = None,
    subject: str | None = None,
    grade: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    query = select(PracticalTask).where(PracticalTask.owner_id == user.id)
    if q:
        query = query.where(PracticalTask.title.ilike(f"%{q}%"))
    if subject:
        query = query.where(PracticalTask.subject == subject)
    if grade:
        query = query.where(PracticalTask.grade == grade)
    query = query.order_by(PracticalTask.is_favorite.desc(),
                           PracticalTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return [PracticalTaskOut.model_validate(i) for i in result.scalars().all()]


@router.get("/practical-tasks/{item_id}", response_model=PracticalTaskOut)
async def get_practical_task(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PracticalTask).where(PracticalTask.id == item_id, PracticalTask.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return PracticalTaskOut.model_validate(item)


@router.put("/practical-tasks/{item_id}", response_model=PracticalTaskOut)
async def update_practical_task(
    item_id: str,
    data: PracticalTaskUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PracticalTask).where(PracticalTask.id == item_id, PracticalTask.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    await db.flush()
    return PracticalTaskOut.model_validate(item)


@router.delete("/practical-tasks/{item_id}", status_code=204)
async def delete_practical_task(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PracticalTask).where(PracticalTask.id == item_id, PracticalTask.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)


# ── Games ("🎮 Интерактивные игры") ───────────────────────────────────────────

@router.post("/games", response_model=GameOut, status_code=201)
async def create_game(
    data: GameCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_game_access(user, "igra")
    item = Game(**data.model_dump(), owner_id=user.id)
    db.add(item)
    await db.flush()
    return GameOut.model_validate(item)


@router.get("/games", response_model=list[GameOut])
async def list_games(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    q: str | None = None,
    subject: str | None = None,
    grade: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    query = select(Game).where(Game.owner_id == user.id)
    if q:
        query = query.where(Game.title.ilike(f"%{q}%"))
    if subject:
        query = query.where(Game.subject == subject)
    if grade:
        query = query.where(Game.grade == grade)
    query = query.order_by(Game.is_favorite.desc(),
                           Game.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return [GameOut.model_validate(i) for i in result.scalars().all()]


@router.get("/games/{item_id}", response_model=GameOut)
async def get_game(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Game).where(Game.id == item_id, Game.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return GameOut.model_validate(item)


@router.put("/games/{item_id}", response_model=GameOut)
async def update_game(
    item_id: str,
    data: GameUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_game_access(user, "igra")
    result = await db.execute(
        select(Game).where(Game.id == item_id, Game.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    await db.flush()
    return GameOut.model_validate(item)


@router.post("/quiz-set", response_model=QuizSetResponse)
async def quiz_set(
    data: QuizSetRequest,
    user: User = Depends(get_current_user),
):
    """Ad-hoc questions for the "Қуттиҳои сеҳрнок" game's AI mode — the
    player picks subject/topic/difficulty/count and gets that many 4-option
    questions, each with an explanation of why its answer is right.

    Deliberately stateless: nothing is written to the database, because
    these questions belong to one play session rather than to a saved
    material. Like reroll-game (and for the same reason) it doesn't touch
    balance/free-tier flags — it produces no material the user keeps."""
    # The quiz set is the game section's live-play question source, so it
    # is behind the same gate the rest of that feature is — otherwise the
    # locked feature stays fully usable by calling this endpoint directly.
    require_game_access(user, "igra")
    await enforce_ai_edit_quota(user)
    try:
        logger.info(f"Quiz-set request: topic={data.topic[:60]} n={data.count} user={user.id}")
        questions = await generate_quiz_set(
            topic=data.topic,
            subject=data.subject,
            level=data.level,
            grade=data.grade,
            language=data.language,
            count=data.count,
        )
        return QuizSetResponse(questions=[QuizSetQuestion(**q) for q in questions])
    except Exception as e:
        logger.error(f"Quiz-set error for user {user.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=get_message("ai_busy", data.language))


@router.post("/games/{item_id}/reroll", response_model=GameOut)
async def reroll_game(
    item_id: str,
    data: RegenerateGameRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """A fresh 12-round set on the exact same topic/subject/grade — for
    "the same game, but a different kid's turn shouldn't see the same
    questions again" rather than making the teacher build a whole new
    material. Reuses the saved game's own title as the topic (see
    _game_prompt's title field: "mentioning {topic}", so titles already
    read as topic-ish) and overwrites game_json in place, same row —
    unlike POST /generate this never touches balance/free-tier flags,
    matching regenerate-item and chat-edit's "refining what's already
    paid for is free" precedent."""
    result = await db.execute(
        select(Game).where(Game.id == item_id, Game.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    require_game_access(user, "igra")
    await enforce_ai_edit_quota(user)
    try:
        logger.info(f"Reroll game request: id={item_id} title={item.title} user={user.id}")
        content = await generate_material(
            material_type="igra",
            topic=item.title,
            subject=item.subject,
            language=data.language,
            level=data.level,
            grade=item.grade,
        )
        content["title"] = item.title
        item.game_json = json.dumps(content, ensure_ascii=False)
        await db.flush()
        return GameOut.model_validate(item)
    except Exception as e:
        logger.error(f"Reroll game error for user {user.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=get_message("ai_busy", data.language))


@router.delete("/games/{item_id}", status_code=204)
async def delete_game(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Game).where(Game.id == item_id, Game.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)


# ── Game attempts (online play — see components/game/GameEngine.tsx) ────────

@router.post("/games/{item_id}/attempts", response_model=GameAttemptOut, status_code=201)
async def create_game_attempt(
    item_id: str,
    data: GameAttemptCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Game).where(Game.id == item_id, Game.owner_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Not found")
    require_game_access(user, "igra")
    item = GameAttempt(game_id=item_id, user_id=user.id, **data.model_dump())
    db.add(item)
    await db.flush()
    return GameAttemptOut.model_validate(item)


@router.get("/games/{item_id}/attempts", response_model=list[GameAttemptOut])
async def list_game_attempts(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Best scores first (not most-recent-first like TestAttempt's history
    # list) — this backs the start screen's "Ваши лучшие результаты", a
    # top-N-by-score list, not a chronological log.
    result = await db.execute(
        select(GameAttempt)
        .where(GameAttempt.game_id == item_id, GameAttempt.user_id == user.id)
        .order_by(GameAttempt.score.desc())
        .limit(20)
    )
    return [GameAttemptOut.model_validate(i) for i in result.scalars().all()]


# ── AI Generate ──────────────────────────────────────────────────────────────

# How many earlier konspekts on the same topic are described to the model
# in full as "do not repeat these". Capped, because each digest costs
# prompt space and by the fourth version the lesson shape and the
# do-not-repeat rules together have already moved the new konspekt well
# away from its predecessors.
_PREVIOUS_DETAIL_LIMIT = 4
# ...but the SHAPE/ANGLE of more of them is still read, cheaply: those two
# strings are all _pick_variant needs to avoid reusing a lesson shape, and
# there are eight shapes, so stopping at four would let the fifth konspekt
# on a topic repeat the first one's shape for no reason.
_PREVIOUS_VARIANTS_LIMIT = 10


async def _previous_digests(db: AsyncSession, user: User, material_type: str,
                            topic: str, subject: str) -> list[dict]:
    """What this teacher already has on this exact topic, digested for the
    prompt (see ai_service.summarize_previous_konspekt).

    This is what makes a second konspekt on one topic a different LESSON
    rather than the same one reworded: without it the model cannot know
    what it wrote last time, and every algebra lesson opens on 2x + 3 = 7.

    Matched on title AND subject, case-insensitively, because that is how
    a teacher regenerates a topic — same wizard, same words typed in.
    Never raises: a konspekt that cannot look up its predecessors is still
    a konspekt, just one that has to rely on the random lesson-shape pick
    alone to differ from them."""
    if material_type not in ("konspekt", "lektsiya", "prezentatsiya"):
        return []
    model_cls = _MATERIAL_MODELS.get(material_type)
    field = _CONTENT_FIELD.get(material_type)
    if model_cls is None or field is None:
        return []
    digest_of = (summarize_previous_presentation if material_type == "prezentatsiya"
                 else summarize_previous_konspekt)
    try:
        rows = await db.execute(
            select(getattr(model_cls, field))
            .where(model_cls.owner_id == user.id,
                   func.lower(model_cls.title) == (topic or "").strip().lower(),
                   func.lower(model_cls.subject) == (subject or "").strip().lower())
            .order_by(model_cls.created_at.desc())
            .limit(_PREVIOUS_VARIANTS_LIMIT)
        )
        digests = []
        for (raw,) in rows.all():
            if not raw:
                continue
            digest = digest_of(raw)
            if not digest:
                continue
            if len(digests) >= _PREVIOUS_DETAIL_LIMIT:
                # Older than the detail window: keep only which lesson
                # shape/angle it used, so those stay off the table
                # without its examples filling up the prompt.
                digest = {k: digest.get(k, "") for k in ("shape", "angle")}
            digests.append(digest)
        if digests:
            logger.info(f"Variation: {len(digests)} previous {material_type}(s) on topic={topic[:50]}")
        return digests
    except Exception as e:
        logger.warning(f"Previous-variant lookup failed for topic={topic[:50]}: {e}")
        return []

# Which JSON column each type's row keeps its generated body in — the one
# per-type difference in an otherwise identical save path.
_CONTENT_FIELD = {
    "konspekt": "content",
    "lektsiya": "content",
    "test": "questions_json",
    "prezentatsiya": "slides_json",
    "amaliy": "tasks_json",
    "igra": "game_json",
}

@router.post("/generate")
async def generate(
    data: GenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Generate request: type={data.material_type} topic={data.topic} user={user.id}")
    if data.material_type not in _MATERIAL_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown material type: {data.material_type}")
    require_game_access(user, data.material_type)
    await enforce_generation_quota(user)

    # Claimed BEFORE the AI call, atomically, and given back below if the
    # generation fails — see app/limits.py. Doing it the other way round
    # (check now, deduct after) is what let two simultaneous requests both
    # pass the check and both generate on one charge.
    charge = await limits.reserve(user.id, [data.material_type], language=user.language)
    try:
        # What this teacher already has on this topic, so a repeat request
        # produces a different lesson rather than the same one reworded.
        previous_digests = await _previous_digests(
            db, user, data.material_type, data.topic, data.subject)

        content = await generate_material(
            material_type=data.material_type,
            topic=data.topic,
            subject=data.subject,
            language=data.language,
            level=data.level,
            grade=data.grade,
            previous_digests=previous_digests,
            slide_count=data.slide_count,
            question_count=data.question_count,
            test_type=data.test_type,
            include_homework=data.include_homework,
            include_fun_facts=data.include_fun_facts,
            include_assessment=data.include_assessment,
            template=data.template,
            source_text=data.source_text,
        )
        content["title"] = data.topic

        model_cls = _MATERIAL_MODELS[data.material_type]
        item = model_cls(
            title=data.topic,
            subject=data.subject,
            grade=data.grade,
            owner_id=user.id,
            **{_CONTENT_FIELD[data.material_type]: json.dumps(content, ensure_ascii=False)},
        )
        db.add(item)
        await db.flush()

        return {
            "status": "ok",
            "id": item.id,
            "material_type": data.material_type,
            "content": content,
            "was_free": charge.free_count > 0,
            # Read back from the database rather than off `user`: the
            # reservation moved the balance on its own connection, so the
            # ORM object still holds the pre-charge value.
            "balance_somoni": (await limits.current_balance(user.id)) / 100,
        }

    except Exception as e:
        # Every failure path refunds — an AI timeout, a malformed
        # response, a database error on save. The teacher asked for a
        # material and did not get one; they must not have paid for it.
        await limits.refund(charge, reason=f"generate failed: {type(e).__name__}")
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Generate material error for user {user.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=get_message("ai_busy", data.language))


# ── Konspekt source upload ("book mode") ────────────────────────────────────

@router.post("/upload-source")
async def upload_source_endpoint(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """Extracts text from a teacher-uploaded .pdf/.docx/.txt so it can be
    used as the primary source for a "book mode" konspekt (see
    source_text on /generate-konspekt-stream). Stateless — nothing is
    written to disk or the database here; the caller holds onto the
    returned text and resubmits it with the generation request, the same
    way /curriculum/parse-docx's extracted text round-trips through the
    frontend."""
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_ext = [e.strip() for e in settings.ALLOWED_SOURCE_EXT.split(",") if e.strip()]
    if ext not in allowed_ext:
        raise HTTPException(
            status_code=400,
            detail=f"Qo'llab-quvvatlanmaydigan fayl turi. Ruxsat etilgan formatlar: {', '.join(allowed_ext)}",
        )

    raw = await file.read()
    if len(raw) > settings.MAX_SOURCE_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Fayl hajmi juda katta")

    try:
        text, truncated = extract_source_text(filename, raw)
    except ValueError as e:
        code = str(e)
        if code == "empty_document":
            raise HTTPException(status_code=422, detail="Faylda matn topilmadi")
        if code == "parse_error":
            raise HTTPException(status_code=422, detail="Faylni o'qib bo'lmadi — fayl buzilgan yoki noto'g'ri formatda")
        raise HTTPException(status_code=400, detail="Qo'llab-quvvatlanmaydigan fayl turi")
    except Exception as e:
        logger.error(f"upload-source extraction error for user {user.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=422, detail="Faylni o'qib bo'lmadi")

    logger.info(f"Source uploaded: user={user.email} filename={filename} chars={len(text)} truncated={truncated}")
    return {"status": "ok", "text": text, "truncated": truncated, "filename": filename}


# ── AI Generate (konspekt, streaming) ───────────────────────────────────────

@router.post("/generate-konspekt-stream")
async def generate_konspekt_stream_endpoint(
    data: GenerateKonspektStreamRequest,
    request: Request,
    user: User = Depends(get_current_user),
):
    """SSE counterpart to /generate, konspekt-only: streams real AI token
    output plus stage/field progress events (see
    ai_service.generate_konspekt_stream for the event shapes), then
    persists the finished konspekt exactly like /generate does — but only
    once, on the terminal "complete" event, so a cancelled/failed
    generation never leaves a half-written row behind.

    Uses its own DB session (async_session()) instead of the usual
    Depends(get_db) one: that request-scoped session gets torn down as
    soon as this endpoint function returns the StreamingResponse object,
    which happens well before the generator below has actually produced
    anything — the save has to happen with a session that's still alive
    partway through the stream.
    """
    source_text = data.source_text if data.generation_mode == "source" else None

    # Reserved before the stream even opens — an SSE response cannot
    # carry a 402 once streaming has started, so a refusal has to raise
    # here rather than inside event_stream(). Refunded on every path that
    # doesn't end in a saved konspekt: client disconnect, AI error, save
    # failure (see the generator's finally block below).
    await enforce_generation_quota(user)
    charge = await limits.reserve(user.id, ["konspekt"], language=user.language)

    try:
        async with async_session() as db:
            # Read on a short-lived session before the stream opens — the
            # request-scoped session is gone by the time event_stream()
            # actually runs.
            previous_digests = await _previous_digests(db, user, "konspekt", data.topic, data.subject)
    except Exception:
        await limits.refund(charge, reason="konspekt stream setup failed")
        raise

    async def event_stream():
        # Flipped to True only once a konspekt row is actually committed.
        # Every other way out of this generator — client disconnect, an
        # AI error event, a save failure, an exception thrown mid-stream
        # — leaves it False and the finally block gives the charge back,
        # so a reservation is never kept for a material the teacher
        # didn't receive.
        saved = False
        try:
            async for event in generate_konspekt_stream(
                topic=data.topic,
                subject=data.subject,
                language=data.language,
                level=data.level,
                grade=data.grade,
                include_homework=data.include_homework,
                include_fun_facts=data.include_fun_facts,
                include_assessment=data.include_assessment,
                source_text=source_text,
                previous_digests=previous_digests,
                template=data.template,
            ):
                if await request.is_disconnected():
                    logger.info(f"generate-konspekt-stream: client disconnected, stopping for user {user.id}")
                    return

                if event.get("type") == "complete":
                    content = event["content"]
                    content["title"] = data.topic
                    try:
                        async with async_session() as db:
                            item = Konspekt(
                                title=data.topic,
                                subject=data.subject,
                                grade=data.grade,
                                content=json.dumps(content, ensure_ascii=False),
                                owner_id=user.id,
                            )
                            db.add(item)
                            await db.commit()
                            await db.refresh(item)
                        saved = True
                        event = {"type": "complete", "content": content, "id": item.id}
                    except Exception as e:
                        logger.error(f"Failed to save streamed konspekt for user {user.id}: {str(e)}", exc_info=True)
                        error_event = {"type": "error", "message": "Konspekt saqlanmadi. Qayta urinib ko'ring.", "code": "save_error"}
                        yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
                        return

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            if not saved:
                await limits.refund(charge, reason="konspekt stream did not complete")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── AI Regenerate Single Item ─────────────────────────────────────────────

@router.post("/regenerate-item")
async def regenerate_item_endpoint(
    data: RegenerateItemRequest,
    user: User = Depends(get_current_user),
):
    if data.material_type not in ("test", "prezentatsiya", "konspekt", "lektsiya", "amaliy"):
        raise HTTPException(status_code=400, detail="Regenerating a single item is only supported for tests, presentations, konspekts, lectures, and practical tasks")
    if data.material_type in ("konspekt", "lektsiya") and not data.section:
        raise HTTPException(status_code=400, detail="'section' is required to regenerate a konspekt/lektsiya item")
    if data.material_type == "amaliy" and data.section not in ("individual_tasks", "group_tasks"):
        raise HTTPException(status_code=400, detail="'section' must be 'individual_tasks' or 'group_tasks' to regenerate a practical task")
    await enforce_ai_edit_quota(user)
    try:
        logger.info(
            f"Regenerate item request: type={data.material_type} topic={data.topic} "
            f"idx={data.item_index} section={data.section} user={user.email}"
        )

        item = await regenerate_item(
            material_type=data.material_type,
            topic=data.topic,
            subject=data.subject,
            language=data.language,
            level=data.level,
            grade=data.grade,
            item_index=data.item_index,
            existing_items=data.existing_items,
            section=data.section,
            existing_content=data.existing_content,
        )
        return {"status": "ok", "item": item}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Regenerate item error for user {user.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=get_message("ai_busy", data.language))


@router.post("/chat-edit")
async def chat_edit_endpoint(
    data: ChatEditRequest,
    user: User = Depends(get_current_user),
):
    """Free-text edit ('add 5 more questions', 'make it shorter', ...)
    applied to a whole material — see schemas.ChatEditRequest's docstring
    for why this has no DB side effects of its own (the frontend saves
    the returned content itself, through the same PUT endpoint the
    regenerate-item flow already uses)."""
    if data.material_type not in _MATERIAL_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown material type: {data.material_type}")
    require_game_access(user, data.material_type)
    await enforce_ai_edit_quota(user)
    try:
        logger.info(f"Chat-edit request: type={data.material_type} topic={data.topic} instruction={data.instruction[:80]!r} user={user.email}")
        updated = await chat_edit_material(
            material_type=data.material_type,
            content=data.content,
            instruction=data.instruction,
            topic=data.topic,
            subject=data.subject,
            language=data.language,
            level=data.level,
            grade=data.grade,
        )
        return {"status": "ok", "content": updated}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat-edit error for user {user.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=get_message("ai_busy", data.language))


# ── AI Generate All ──────────────────────────────────────────────────────

# Practical tasks belong here too: "everything at once" that quietly
# skipped one of the wizard's own material types left teachers making
# it separately every time, wondering why the button had not.
_GENERATE_ALL_TYPES = ["konspekt", "test", "prezentatsiya", "lektsiya", "amaliy"]


@router.post("/generate-all")
async def generate_all(
    data: GenerateAllRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """One topic → all four material types at once, billed exactly like
    generating each of the 4 separately would be: each type has its own
    free slot (see limits.FREE_SLOT_COLUMN), so a brand-new account pays
    nothing here and one that has already made a konspekt pays for that
    one type only.

    All four are reserved as ONE atomic unit up front (see
    limits.reserve) — 402 if the balance can't cover the whole set, so a
    partial balance can never let three of four "pass" a check against
    the same unspent money. Whatever the AI then fails to produce is
    refunded individually below, so a run where only two of four types
    came back is charged for exactly two."""
    # A subset when the teacher picked one, all five otherwise. Filtered
    # against _GENERATE_ALL_TYPES rather than trusted: the list decides
    # what gets billed and generated, so an unknown string here would
    # reserve a slot for a type nothing can produce, and the refund path
    # would then have to guess.
    if data.types:
        types_to_generate = [t for t in _GENERATE_ALL_TYPES if t in set(data.types)]
        if not types_to_generate:
            raise HTTPException(
                status_code=400,
                detail=f"No known material types requested. Pick from: {', '.join(_GENERATE_ALL_TYPES)}",
            )
    else:
        types_to_generate = list(_GENERATE_ALL_TYPES)
    skipped: list[str] = []

    await enforce_generation_quota(user)
    charge = await limits.reserve(user.id, types_to_generate, language=user.language)
    try:
        # logger, not print: a bare print() goes straight to the console
        # with its own encoding, which on Windows (cp1251) cannot encode
        # Tajik and raised UnicodeEncodeError mid-request — see
        # app/logger.py. The logger's file handlers are UTF-8 and its
        # console handler now writes UTF-8 too.
        logger.info(
            f"generate-all: topic={data.topic!r} subject={data.subject!r} "
            f"lang={data.language!r} level={data.level!r} grade={data.grade!r} "
            f"slides={data.slide_count} questions={data.question_count} "
            f"test_type={data.test_type!r} types={types_to_generate}")
        result = await generate_all_materials(
            topic=data.topic,
            subject=data.subject,
            language=data.language,
            level=data.level,
            grade=data.grade,
            slide_count=data.slide_count or 10,
            question_count=data.question_count or 10,
            test_type=data.test_type,
            types=types_to_generate,
        )
        if result.get("errors"):
            logger.warning(f"generate-all errors: {result.get('errors')}")
        logger.info("generate-all generated: " + " ".join(
            f"{t}={bool(result.get(t))}" for t in types_to_generate))

        saved_ids = {}

        if result.get("konspekt"):
            result["konspekt"]["title"] = data.topic
            item = Konspekt(
                title=data.topic,
                subject=data.subject,
                grade=data.grade,
                content=json.dumps(result["konspekt"], ensure_ascii=False),
                owner_id=user.id,
            )
            db.add(item)
            await db.flush()
            saved_ids["konspekt"] = item.id

        if result.get("test"):
            result["test"]["title"] = data.topic
            item = Test(
                title=data.topic,
                subject=data.subject,
                grade=data.grade,
                questions_json=json.dumps(result["test"], ensure_ascii=False),
                owner_id=user.id,
            )
            db.add(item)
            await db.flush()
            saved_ids["test"] = item.id

        if result.get("prezentatsiya"):
            result["prezentatsiya"]["title"] = data.topic
            item = Presentation(
                title=data.topic,
                subject=data.subject,
                grade=data.grade,
                slides_json=json.dumps(result["prezentatsiya"], ensure_ascii=False),
                owner_id=user.id,
            )
            db.add(item)
            await db.flush()
            saved_ids["prezentatsiya"] = item.id

        if result.get("lektsiya"):
            result["lektsiya"]["title"] = data.topic
            item = Lecture(
                title=data.topic,
                subject=data.subject,
                grade=data.grade,
                content=json.dumps(result["lektsiya"], ensure_ascii=False),
                owner_id=user.id,
            )
            db.add(item)
            await db.flush()
            saved_ids["lektsiya"] = item.id

        # PracticalTask stores its payload in tasks_json, not content —
        # the one type here whose column is not called "content".
        if result.get("amaliy"):
            result["amaliy"]["title"] = data.topic
            item = PracticalTask(
                title=data.topic,
                subject=data.subject,
                grade=data.grade,
                tasks_json=json.dumps(result["amaliy"], ensure_ascii=False),
                owner_id=user.id,
            )
            db.add(item)
            await db.flush()
            saved_ids["amaliy"] = item.id

        # Give back the reservation for every type that did NOT produce
        # and save a material — same "you only pay for what you got"
        # discipline the pay-after-success ordering used to provide, now
        # done as an explicit refund because the charge happens up front.
        failed = [t for t in types_to_generate if t not in saved_ids]
        if failed:
            await limits.refund(charge, failed, reason="generate-all: type produced nothing")

        # Which of the SAVED types was the free one, for the frontend's
        # "this one was free" badge. charge.items is in the same order as
        # types_to_generate, so a saved type's entry is found by name.
        free_types = {i.material_type for i in charge.items if i.was_free}

        return {
            "status": "ok",
            "ids": saved_ids,
            "content": result,
            "skipped": skipped or None,
            "was_free": {t: (t in free_types) for t in saved_ids},
            "balance_somoni": (await limits.current_balance(user.id)) / 100,
        }

    except Exception as e:
        await limits.refund(charge, reason=f"generate-all failed: {type(e).__name__}")
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Generate-all materials error for user {user.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=get_message("ai_busy", data.language))


# ── DOCX Download ──────────────────────────────────────────────────────────

from pydantic import BaseModel

class DocxRequest(BaseModel):
    material_type: str
    content: dict
    language: str = "Русский"


def _with_language(data: "DocxRequest") -> dict:
    """The content with a language on it.

    A konspekt carries its own (ai_service stamps it at generation), but
    tests — and, until that stamping grew a matching "amaliy" branch,
    every practical-tasks worksheet ever generated — stored before that
    did not, and the export then defaulted every one of them to Russian."""
    if data.content.get("language"):
        return data.content
    return {**data.content, "language": data.language}

@router.post("/download-docx")
async def download_docx(
    data: DocxRequest,
    user: User = Depends(get_current_user),
):
    try:
        # Every build_* here is a plain sync function (python-docx/reportlab
        # have no async API) — run off the event loop via to_thread so
        # building one teacher's document doesn't stall every other
        # concurrent request on this single-worker server for however
        # long that takes.
        if data.material_type == 'konspekt':
            buf = await asyncio.to_thread(build_konspekt_docx, data.content, data.language)
            raw_name = f"konspekt_{data.content.get('title', 'lesson').replace(' ', '_')[:30]}"
        elif data.material_type == 'lektsiya':
            buf = await asyncio.to_thread(build_lecture_docx, data.content, data.language)
            raw_name = f"lektsiya_{data.content.get('title', 'lecture').replace(' ', '_')[:30]}"
        elif data.material_type == 'test':
            # The sheet's own furniture — the name line, the instructions,
            # the answer key's heading — is written in the test's
            # language. Tests generated before that language was stored on
            # the content itself fall back to the request's.
            buf = await asyncio.to_thread(build_test_docx, _with_language(data))
            raw_name = f"test_{data.content.get('title', 'test').replace(' ', '_')[:30]}"
        elif data.material_type == 'prezentatsiya':
            buf = await asyncio.to_thread(build_presentation_docx, data.content)
            raw_name = f"presentation_{data.content.get('title', 'slides').replace(' ', '_')[:30]}"
        elif data.material_type == 'amaliy':
            # Every practical-tasks worksheet generated before "amaliy"
            # was added to ai_service's language-stamping list (see there)
            # has no "language" of its own — same backward-compat fallback
            # as the test branch above, or these would keep printing a
            # Russian header forever even after the root cause is fixed.
            buf = await asyncio.to_thread(build_practical_docx, _with_language(data))
            raw_name = f"amaliy_{data.content.get('title', 'tasks').replace(' ', '_')[:30]}"
        else:
            raise HTTPException(status_code=400, detail=f"Unknown material type: {data.material_type}")

        ascii_name = raw_name.encode('ascii', 'ignore').decode('ascii').strip('_').strip('.')
        if not ascii_name:
            ascii_name = 'document'
        encoded_name = quote(raw_name, safe='._-')
        content_disp = f"attachment; filename=\"{ascii_name}.docx\"; filename*=UTF-8''{encoded_name}.docx"

        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": content_disp},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DOCX export error for user {user.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="DOCX xatolik: fayl yaratilmadi")


# ── PPTX Download ─────────────────────────────────────────────────────────

@router.post("/download-pptx")
async def download_pptx(
    data: DocxRequest,
    user: User = Depends(get_current_user),
):
    try:
        if data.material_type == 'prezentatsiya':
            buf = await asyncio.to_thread(build_presentation_pptx, data.content)
            raw_name = f"presentation_{data.content.get('title', 'slides').replace(' ', '_')[:30]}"
        else:
            raise HTTPException(status_code=400, detail="PPTX only for presentations")

        ascii_name = raw_name.encode('ascii', 'ignore').decode('ascii').strip('_').strip('.')
        if not ascii_name:
            ascii_name = 'presentation'
        encoded_name = quote(raw_name, safe='._-')
        content_disp = f"attachment; filename=\"{ascii_name}.pptx\"; filename*=UTF-8''{encoded_name}.pptx"

        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": content_disp},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PPTX export error for user {user.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="PPTX xatolik: fayl yaratilmadi")


# ── PDF Download ───────────────────────────────────────────────────────────

def _presentation_pdf(content: dict) -> io.BytesIO:
    """A deck as PDF: the actual .pptx put through LibreOffice, falling
    back to the hand-built A4 rendering when LibreOffice is unavailable or
    chokes on the file.

    Both paths are real: the fallback is what every deployment without
    LibreOffice installed keeps using, so it must stay working rather than
    become dead code nobody notices has rotted."""
    try:
        # Cache lookup first: on a hit there is no .pptx to build and no
        # LibreOffice to run, which is the whole point — the preview
        # refetches on every screen open and the conversion is ~17s.
        key = pptx_pdf.cache_key_for(content)
        hit = pptx_pdf.cached(key)
        if hit is not None:
            return hit
        pptx = build_presentation_pptx(content).getvalue()
        converted = pptx_pdf.convert(pptx, key)
        if converted is not None:
            return converted
    except Exception as e:  # noqa: BLE001
        # A deck that cannot be built as pptx at all still has to produce
        # something the teacher can open.
        logger.warning(f"pptx->pdf path failed, using the built PDF instead: {e}")
    return build_presentation_pdf(content)


@router.post("/download-pdf")
async def download_pdf(
    data: DocxRequest,
    user: User = Depends(get_current_user),
):
    try:
        if data.material_type == 'konspekt':
            buf = await asyncio.to_thread(build_konspekt_pdf, data.content, data.language)
            raw_name = f"konspekt_{data.content.get('title', 'lesson').replace(' ', '_')[:30]}"
        elif data.material_type == 'lektsiya':
            buf = await asyncio.to_thread(build_lecture_pdf, data.content, data.language)
            raw_name = f"lektsiya_{data.content.get('title', 'lecture').replace(' ', '_')[:30]}"
        elif data.material_type == 'test':
            buf = await asyncio.to_thread(build_test_pdf, _with_language(data))
            raw_name = f"test_{data.content.get('title', 'test').replace(' ', '_')[:30]}"
        elif data.material_type == 'prezentatsiya':
            # The real .pptx, rendered by LibreOffice — so the preview the
            # app shows is the deck itself rather than a second, A4-shaped
            # rendering of the same content that could never quite match
            # it. build_presentation_pdf stays as the fallback for a
            # deployment without LibreOffice (see app/pptx_pdf.py).
            buf = await asyncio.to_thread(_presentation_pdf, data.content)
            raw_name = f"presentation_{data.content.get('title', 'slides').replace(' ', '_')[:30]}"
        elif data.material_type == 'amaliy':
            # Same backward-compat fallback as download-docx above.
            buf = await asyncio.to_thread(build_practical_pdf, _with_language(data))
            raw_name = f"amaliy_{data.content.get('title', 'tasks').replace(' ', '_')[:30]}"
        else:
            raise HTTPException(status_code=400, detail=f"Unknown material type: {data.material_type}")

        ascii_name = raw_name.encode('ascii', 'ignore').decode('ascii').strip('_').strip('.')
        if not ascii_name:
            ascii_name = 'document'
        encoded_name = quote(raw_name, safe='._-')
        content_disp = f"attachment; filename=\"{ascii_name}.pdf\"; filename*=UTF-8''{encoded_name}.pdf"

        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": content_disp},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF export error for user {user.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="PDF xatolik: fayl yaratilmadi")


# ── TXT Download ─────────────────────────────────────────────────────────

@router.post("/download-txt")
async def download_txt(
    data: DocxRequest,
    user: User = Depends(get_current_user),
):
    try:
        content = data.content
        lines = []

        title = content.get('title', '')
        if title:
            lines.append(title)
            lines.append('=' * len(title))
            lines.append('')

        if data.material_type in ('konspekt', 'lektsiya'):
            # Same field->label list for both — a лекция's content dict
            # simply omits the lesson-management keys (competencies,
            # objectives, lesson_program, ...), so this loop's `if val:`
            # guard already skips them with no branch needed.
            for key, label in [
                ('duration', 'Время'), ('competencies', 'Компетенции'),
                ('objectives', 'Цели'), ('key_concepts', 'Понятия'),
                ('key_terms', 'Термины'), ('fun_facts', 'Факты'),
                ('real_life_examples', 'Примеры'),
                ('lesson_program', 'Программа'), ('tools', 'Инструменты'),
                ('warmup', 'Разминка'), ('main_content', 'Контент'),
                ('pair_work', 'Парная работа'), ('consolidation', 'Закрепление'),
                ('group_work', 'Групповая работа'),
                ('visual_aid', 'Визуал'),
                ('common_mistakes', 'Ошибки'), ('summary', 'Итоги'),
                ('homework', 'Д/З'), ('assessment', 'Оценка'),
            ]:
                val = content.get(key)
                if val:
                    if isinstance(val, list):
                        lines.append(f'{label}: ' + '; '.join(val))
                    else:
                        lines.append(f'{label}: {val}')

        elif data.material_type == 'test':
            desc = content.get('description', '')
            if desc:
                lines.append(desc)
            for i, q in enumerate(content.get('questions', []), 1):
                lines.append(f'{i}. {q.get("question", "")}')
                opts = q.get('options', [])
                correct = q.get('correct_index', 0)
                opt_str = ' | '.join(f'{"*" if j == correct else ""}{chr(65+j)}) {opt}' for j, opt in enumerate(opts))
                lines.append(f'  {opt_str}')
                if q.get('explanation'):
                    lines.append(f'  >> {q["explanation"]}')

        elif data.material_type == 'prezentatsiya':
            desc = content.get('description', '')
            if desc:
                lines.append(desc)
            for i, s in enumerate(content.get('slides', []), 1):
                lines.append(f'[{i}] {s.get("title", "")}')
                lines.append('  ' + ' | '.join(s.get('bullet_points', [])))
                if s.get('speaker_notes'):
                    lines.append(f'  ~{s["speaker_notes"]}')

        elif data.material_type == 'amaliy':
            # Without this branch the export fell through with only the
            # title line written — a practical-tasks .txt came out at 22
            # bytes and looked like a broken download rather than a
            # missing case.
            #
            # Section labels follow the worksheet's own language, the
            # same table build_practical_pdf/_docx use — this used to
            # print "Индивидуальные задания"/"Групповые задания" even on
            # a worksheet written entirely in Tajik, because the labels
            # here were plain hardcoded Russian strings rather than a
            # lookup. `content.get('language')` covers a freshly
            # generated worksheet (ai_service now stamps it); the
            # `data.language` fallback covers one saved before that fix.
            _pui = _PRACTICAL_UI.get(content.get('language') or data.language,
                                     _PRACTICAL_UI['Русский'])
            desc = content.get('description', '')
            if desc:
                lines.append(desc)
            for label, key in ((_pui['individual'], 'individual_tasks'),
                               (_pui['group'], 'group_tasks')):
                items = content.get(key) or []
                if not items:
                    continue
                lines.append('')
                lines.append(label)
                for i, task in enumerate(items, 1):
                    if isinstance(task, str):
                        lines.append(f'{i}. {task}')
                        continue
                    lines.append(f'{i}. {task.get("title") or task.get("task") or ""}')
                    for field in ('description', 'instruction', 'expected_result', 'answer'):
                        val = task.get(field)
                        if val:
                            lines.append(f'  {val}')
                    for step in task.get('steps') or []:
                        lines.append(f'  - {step}')

        text = '\n'.join(lines)
        buf = io.BytesIO(text.encode('utf-8'))

        raw_name = f"{data.material_type}_{title.replace(' ', '_')[:30]}"
        ascii_name = raw_name.encode('ascii', 'ignore').decode('ascii').strip('_').strip('.')
        if not ascii_name:
            ascii_name = 'document'
        encoded_name = quote(raw_name, safe='._-')
        content_disp = f"attachment; filename=\"{ascii_name}.txt\"; filename*=UTF-8''{encoded_name}.txt"

        return StreamingResponse(
            buf,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": content_disp},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TXT export error for user {user.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="TXT xatolik: fayl yaratilmadi")


# ── ZIP Download (bundle) ───────────────────────────────────────────────────
# Used right after POST /generate-all — the frontend already has all four
# generated contents in memory at that point (no extra fetch needed), so
# it just re-posts whichever of the four it got back here and gets one
# .zip with each as its native export format (docx for konspekt/test/
# lektsiya, pptx for prezentatsiya — same formats download-docx/
# download-pptx already produce individually).

import zipfile


class DownloadZipRequest(BaseModel):
    topic: str
    language: str = "Русский"
    konspekt: dict | None = None
    test: dict | None = None
    prezentatsiya: dict | None = None
    lektsiya: dict | None = None
    amaliy: dict | None = None


def _build_materials_zip(data: "DownloadZipRequest") -> io.BytesIO:
    """Up to 5 documents built and zipped — the single biggest blocking
    chunk of work in this router, so it's the one call site here that
    gets its own helper instead of wrapping each build_* call in its own
    to_thread (that would still leave a synchronous zipfile write between
    them running on the event loop for no real benefit)."""
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if data.konspekt:
            zf.writestr("konspekt.docx", build_konspekt_docx(data.konspekt, data.language).getvalue())
        if data.test:
            zf.writestr("test.docx", build_test_docx(data.test).getvalue())
        if data.prezentatsiya:
            zf.writestr("prezentatsiya.pptx", build_presentation_pptx(data.prezentatsiya).getvalue())
        if data.lektsiya:
            zf.writestr("lektsiya.docx", build_lecture_docx(data.lektsiya, data.language).getvalue())
        if data.amaliy:
            zf.writestr("amaliy.docx", build_practical_docx(data.amaliy).getvalue())
    zip_buf.seek(0)
    return zip_buf


@router.post("/download-zip")
async def download_zip(
    data: DownloadZipRequest,
    user: User = Depends(get_current_user),
):
    if not any([data.konspekt, data.test, data.prezentatsiya, data.lektsiya, data.amaliy]):
        raise HTTPException(status_code=400, detail="Nothing to export")

    try:
        zip_buf = await asyncio.to_thread(_build_materials_zip, data)

        raw_name = data.topic.replace(" ", "_")[:40] or "materials"
        ascii_name = raw_name.encode("ascii", "ignore").decode("ascii").strip("_").strip(".") or "materials"
        encoded_name = quote(raw_name, safe="._-")
        content_disp = f"attachment; filename=\"{ascii_name}.zip\"; filename*=UTF-8''{encoded_name}.zip"

        return StreamingResponse(
            zip_buf,
            media_type="application/zip",
            headers={"Content-Disposition": content_disp},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ZIP export error for user {user.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="ZIP xatolik: fayl yaratilmadi")


# ── Lesson Kit ────────────────────────────────────────────────────────────
# "One subject + grade + topic -> every material for that exact lesson in
# one place" (the 5-rka-inspired concept) — built with NO new database
# table. generate() above already sets title=topic verbatim (see
# `content["title"] = data.topic`), and _previous_digests already matches
# rows by (owner_id, lower(title)==topic, lower(subject)==subject) for
# the same reason — a lesson's identity IS its (subject, grade, topic)
# tuple across the existing 5 tables, so grouping needs a query, not a
# schema change. "igra" is excluded, same as LIBRARY_TYPES on the
# frontend (a game is played in the moment, not a lesson document).
_LESSON_TYPES = ["konspekt", "lektsiya", "prezentatsiya", "test", "amaliy"]

lessons_router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@lessons_router.get("")
async def list_lessons(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Every distinct (subject, grade, topic) this teacher has at least one
    material for, most-recently-touched first — reconstructed from the 5
    existing tables, so every material ever created (before this feature
    existed) already shows up as a lesson with no backfill needed."""
    try:
        selects = [
            select(
                model_cls.subject.label("subject"),
                model_cls.grade.label("grade"),
                model_cls.title.label("topic"),
                model_cls.created_at.label("created_at"),
            ).where(model_cls.owner_id == user.id)
            for model_cls in (_MATERIAL_MODELS[t] for t in _LESSON_TYPES)
        ]
        union_q = selects[0].union_all(*selects[1:]).subquery()
        rows = (await db.execute(
            select(
                union_q.c.subject, union_q.c.grade, union_q.c.topic,
                func.max(union_q.c.created_at).label("last_touched"),
                func.count().label("material_count"),
            )
            .group_by(union_q.c.subject, union_q.c.grade, union_q.c.topic)
            .order_by(func.max(union_q.c.created_at).desc())
            .limit(200)
        )).all()
        return [
            {"subject": r.subject, "grade": r.grade, "topic": r.topic,
             "material_count": r.material_count, "last_touched": r.last_touched}
            for r in rows
        ]
    except Exception as e:
        logger.error(f"List lessons error for user {user.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Хатогӣ: рӯйхат бор нашуд")


@lessons_router.get("/materials")
async def get_lesson_materials(
    subject: str, grade: str, topic: str,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """Which of the 5 lesson-kit types already exist for this exact
    (subject, grade, topic), and their ids — same case-insensitive
    title/subject match _previous_digests already uses, plus grade."""
    out: dict[str, dict | None] = {}
    for t in _LESSON_TYPES:
        model_cls = _MATERIAL_MODELS[t]
        row = (await db.execute(
            select(model_cls.id, model_cls.created_at)
            .where(model_cls.owner_id == user.id,
                   func.lower(model_cls.title) == topic.strip().lower(),
                   func.lower(model_cls.subject) == subject.strip().lower(),
                   model_cls.grade == grade)
            .order_by(model_cls.created_at.desc())
            .limit(1)
        )).first()
        out[t] = {"id": row.id, "created_at": row.created_at} if row else None
    return {"subject": subject, "grade": grade, "topic": topic, "materials": out}


@lessons_router.post("/generate")
async def generate_lesson_material(
    data: GenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generates one material for a Lesson Kit slot — the exact same
    generation path as POST /materials/generate (same balance/free-slot
    check, same generate_material() call, same save), the only difference
    being which router calls it. Kept separate from /materials/generate
    rather than reused directly so the two call sites can evolve
    independently (e.g. lesson-kit-specific defaults later) without one
    changing the other's contract."""
    if data.material_type not in _LESSON_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown lesson material type: {data.material_type}")
    require_game_access(user, data.material_type)
    await enforce_generation_quota(user)
    charge = await limits.reserve(user.id, [data.material_type], language=user.language)
    try:
        previous_digests = await _previous_digests(
            db, user, data.material_type, data.topic, data.subject)

        content = await generate_material(
            material_type=data.material_type,
            topic=data.topic,
            subject=data.subject,
            language=data.language,
            level=data.level,
            grade=data.grade,
            previous_digests=previous_digests,
            slide_count=data.slide_count,
            question_count=data.question_count,
            test_type=data.test_type,
            include_homework=data.include_homework,
            include_fun_facts=data.include_fun_facts,
            include_assessment=data.include_assessment,
            template=data.template,
            source_text=data.source_text,
        )
        content["title"] = data.topic

        model_cls = _MATERIAL_MODELS[data.material_type]
        item = model_cls(
            title=data.topic,
            subject=data.subject,
            grade=data.grade,
            owner_id=user.id,
            **{_CONTENT_FIELD[data.material_type]: json.dumps(content, ensure_ascii=False)},
        )
        db.add(item)
        await db.flush()

        return {
            "status": "ok",
            "id": item.id,
            "material_type": data.material_type,
            "was_free": charge.free_count > 0,
            "balance_somoni": (await limits.current_balance(user.id)) / 100,
        }
    except Exception as e:
        await limits.refund(charge, reason=f"lesson generate failed: {type(e).__name__}")
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Lesson material generate error for user {user.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=get_message("ai_busy", data.language))
