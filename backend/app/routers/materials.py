import asyncio
import json
import io
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db, async_session, released
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

GENERATION_PRICE_DIRAMS = limits.GENERATION_PRICE_DIRAMS
_PILOT_FREE_FOR_ALL = limits.PILOT_FREE_FOR_ALL

_FREE_USED_ATTR = {
    "konspekt": "free_konspekt_used",
    "lektsiya": "free_lektsiya_used",
    "test": "free_test_used",
    "prezentatsiya": "free_prezentatsiya_used",
    "amaliy": "free_amaliy_used",
    "igra": "free_igra_used",
}


def _readable(model_cls, item_id: str, user: User):
    q = select(model_cls).where(model_cls.id == item_id)
    if user.role != "admin":
        q = q.where(model_cls.owner_id == user.id)
    return q


async def enforce_generation_quota(user: User) -> None:
    await enforce_user_quota(
        user.id, "generate", get_settings().MAX_GENERATIONS_PER_HOUR
    )


async def enforce_ai_edit_quota(user: User) -> None:
    await enforce_user_quota(
        user.id, "ai_edit", get_settings().MAX_AI_EDITS_PER_HOUR
    )


def require_game_access(user: User, material_type: str) -> None:
    if material_type != "igra":
        return
    if user.role == "admin":
        return
    allowed = {u.strip() for u in settings.GAME_ACCESS_USER_IDS.split(",") if u.strip()}
    if user.id in allowed or (user.short_id and user.short_id in allowed):
        return
    logger.warning(f"Game access denied for user {user.id} (role={user.role})")
    raise HTTPException(status_code=403, detail=get_message("game_locked", user.language))



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
    result = await db.execute(_readable(Konspekt, item_id, user))
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
    result = await db.execute(_readable(Lecture, item_id, user))
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
    result = await db.execute(_readable(Presentation, item_id, user))
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
    result = await db.execute(_readable(Test, item_id, user))
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
    result = await db.execute(_readable(PracticalTask, item_id, user))
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
    result = await db.execute(_readable(Game, item_id, user))
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
        async with released(db):
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
    result = await db.execute(
        select(GameAttempt)
        .where(GameAttempt.game_id == item_id, GameAttempt.user_id == user.id)
        .order_by(GameAttempt.score.desc())
        .limit(20)
    )
    return [GameAttemptOut.model_validate(i) for i in result.scalars().all()]



_PREVIOUS_DETAIL_LIMIT = 4
_PREVIOUS_VARIANTS_LIMIT = 10


async def _previous_digests(db: AsyncSession, user: User, material_type: str,
                            topic: str, subject: str) -> list[dict]:
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
                digest = {k: digest.get(k, "") for k in ("shape", "angle")}
            digests.append(digest)
        if digests:
            logger.info(f"Variation: {len(digests)} previous {material_type}(s) on topic={topic[:50]}")
        return digests
    except Exception as e:
        logger.warning(f"Previous-variant lookup failed for topic={topic[:50]}: {e}")
        return []

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
    async with released(db):
        await enforce_generation_quota(user)
        charge = await limits.reserve(user.id, [data.material_type], language=user.language)
    try:
        previous_digests = await _previous_digests(
            db, user, data.material_type, data.topic, data.subject)

        async with released(db):
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
            "balance_somoni": (await limits.current_balance(user.id)) / 100,
        }

    except Exception as e:
        await limits.refund(charge, reason=f"generate failed: {type(e).__name__}")
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Generate material error for user {user.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=get_message("ai_busy", data.language))



@router.post("/upload-source")
async def upload_source_endpoint(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
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



@router.post("/generate-konspekt-stream")
async def generate_konspekt_stream_endpoint(
    data: GenerateKonspektStreamRequest,
    request: Request,
    user: User = Depends(get_current_user),
):
    source_text = data.source_text if data.generation_mode == "source" else None

    await enforce_generation_quota(user)
    charge = await limits.reserve(user.id, ["konspekt"], language=user.language)

    try:
        async with async_session() as db:
            previous_digests = await _previous_digests(db, user, "konspekt", data.topic, data.subject)
    except Exception:
        await limits.refund(charge, reason="konspekt stream setup failed")
        raise

    async def event_stream():
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

        async with released(db):
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
    if data.material_type not in _MATERIAL_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown material type: {data.material_type}")
    require_game_access(user, data.material_type)
    await enforce_ai_edit_quota(user)
    try:
        logger.info(f"Chat-edit request: type={data.material_type} topic={data.topic} instruction={data.instruction[:80]!r} user={user.email}")
        async with released(db):
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



_GENERATE_ALL_TYPES = ["konspekt", "test", "prezentatsiya", "lektsiya", "amaliy"]


async def _generate_all_impl(
    data: GenerateAllRequest,
    user: User,
    db: AsyncSession,
) -> dict:
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
        logger.info(
            f"generate-all: topic={data.topic!r} subject={data.subject!r} "
            f"lang={data.language!r} level={data.level!r} grade={data.grade!r} "
            f"slides={data.slide_count} questions={data.question_count} "
            f"test_type={data.test_type!r} types={types_to_generate}")
        async with released(db):
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

        failed = [t for t in types_to_generate if t not in saved_ids]
        if failed:
            await limits.refund(charge, failed, reason="generate-all: type produced nothing")

        free_types = {i.material_type for i in charge.items if i.was_free}

        return {
            "status": "ok",
            "ids": saved_ids,
            "content": result,
            "skipped": skipped or None,
            "was_free": {t: (t in free_types) for t in saved_ids},
            "balance_somoni": (await limits.current_balance(user.id)) / 100,
        }

    except asyncio.CancelledError:
        await limits.refund(charge, reason="generate-all cancelled")
        raise
    except Exception as e:
        await limits.refund(charge, reason=f"generate-all failed: {type(e).__name__}")
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Generate-all materials error for user {user.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=get_message("ai_busy", data.language))


@router.post("/generate-all")
async def generate_all(
    data: GenerateAllRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _generate_all_impl(data, user, db)


GENERATE_KEEPALIVE_SECONDS = 10


@router.post("/generate-all-stream")
async def generate_all_stream(
    data: GenerateAllRequest,
    request: Request,
    user: User = Depends(get_current_user),
):
    async def event_stream():
        async with async_session() as db:
            task = asyncio.create_task(_generate_all_impl(data, user, db))
            try:
                while True:
                    try:
                        payload = await asyncio.wait_for(
                            asyncio.shield(task), timeout=GENERATE_KEEPALIVE_SECONDS
                        )
                        break
                    except asyncio.TimeoutError:
                        if await request.is_disconnected():
                            logger.info(
                                f"generate-all-stream: client disconnected, stopping for user {user.id}"
                            )
                            task.cancel()
                            return
                        yield ": keep-alive\n\n"

                await asyncio.wait_for(db.commit(), timeout=20.0)
                yield f"data: {json.dumps({'type': 'complete', **payload}, ensure_ascii=False)}\n\n"

            except HTTPException as e:
                await db.rollback()
                yield f"data: {json.dumps({'type': 'error', 'message': e.detail}, ensure_ascii=False)}\n\n"
            except Exception as e:
                await db.rollback()
                logger.error(
                    f"generate-all-stream error for user {user.id}: {str(e)}", exc_info=True
                )
                message = get_message("ai_busy", data.language)
                yield f"data: {json.dumps({'type': 'error', 'message': message}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )



from pydantic import BaseModel

class DocxRequest(BaseModel):
    material_type: str
    content: dict
    language: str = "Русский"


def _with_language(data: "DocxRequest") -> dict:
    if data.content.get("language"):
        return data.content
    return {**data.content, "language": data.language}

@router.post("/download-docx")
async def download_docx(
    data: DocxRequest,
    user: User = Depends(get_current_user),
):
    try:
        if data.material_type == 'konspekt':
            buf = await asyncio.to_thread(build_konspekt_docx, data.content, data.language)
            raw_name = f"konspekt_{data.content.get('title', 'lesson').replace(' ', '_')[:30]}"
        elif data.material_type == 'lektsiya':
            buf = await asyncio.to_thread(build_lecture_docx, data.content, data.language)
            raw_name = f"lektsiya_{data.content.get('title', 'lecture').replace(' ', '_')[:30]}"
        elif data.material_type == 'test':
            buf = await asyncio.to_thread(build_test_docx, _with_language(data))
            raw_name = f"test_{data.content.get('title', 'test').replace(' ', '_')[:30]}"
        elif data.material_type == 'prezentatsiya':
            buf = await asyncio.to_thread(build_presentation_docx, data.content)
            raw_name = f"presentation_{data.content.get('title', 'slides').replace(' ', '_')[:30]}"
        elif data.material_type == 'amaliy':
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



def _presentation_pdf(content: dict) -> io.BytesIO:
    try:
        key = pptx_pdf.cache_key_for(content)
        hit = pptx_pdf.cached(key)
        if hit is not None:
            return hit
        pptx = build_presentation_pptx(content).getvalue()
        converted = pptx_pdf.convert(pptx, key)
        if converted is not None:
            return converted
    except Exception as e:
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
            buf = await asyncio.to_thread(_presentation_pdf, data.content)
            raw_name = f"presentation_{data.content.get('title', 'slides').replace(' ', '_')[:30]}"
        elif data.material_type == 'amaliy':
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


_LESSON_TYPES = ["konspekt", "lektsiya", "prezentatsiya", "test", "amaliy"]

lessons_router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@lessons_router.get("")
async def list_lessons(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
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
    if data.material_type not in _LESSON_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown lesson material type: {data.material_type}")
    require_game_access(user, data.material_type)
    await enforce_generation_quota(user)
    charge = await limits.reserve(user.id, [data.material_type], language=user.language)
    try:
        previous_digests = await _previous_digests(
            db, user, data.material_type, data.topic, data.subject)

        async with released(db):
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
