"""QR-code pairing login — website shows a QR code, the already-signed-in
mobile app scans it and approves, the website's next poll picks up a
completely normal access+refresh token pair for that user. See
models.QrLoginSession's docstring for the full flow/security reasoning.
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import QrLoginSession, User
from app.schemas import QrApproveRequest, UserOut
from app.auth import get_current_user, create_access_token, create_refresh_token
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/auth/qr", tags=["qr-auth"])

_SESSION_TTL = timedelta(minutes=3)


def _expired(session: QrLoginSession) -> bool:
    expires_at = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)
    return expires_at < datetime.now(timezone.utc)


@router.post("/create", status_code=201)
async def create_qr_session(request: Request, db: AsyncSession = Depends(get_db)):
    """No auth — anyone can ask for a QR code to *display*; it grants
    nothing by itself. 3-minute expiry, same as the website's poll
    interval assumption (see QrLoginScreen): short enough that a code
    left on a shared/public screen isn't a standing risk, long enough
    for a teacher to actually get their phone out and scan it."""
    session = QrLoginSession(
        expires_at=datetime.now(timezone.utc) + _SESSION_TTL,
        browser_user_agent=request.headers.get("user-agent"),
    )
    db.add(session)
    await db.flush()
    return {"session_id": session.id, "expires_in": int(_SESSION_TTL.total_seconds())}


@router.get("/status/{session_id}")
async def qr_session_status(session_id: str, db: AsyncSession = Depends(get_db)):
    """Polled by the website every few seconds. 404 covers "never
    existed", "expired", and "already consumed" alike — the website
    reacts to all three the same way (mint a fresh QR code), so there's
    no reason to tell them apart in the response. On "approved", the
    token pair is handed back exactly once: the row is deleted in the
    same request before returning, so a second poll (or a second tab
    racing this one) can never replay it."""
    result = await db.execute(select(QrLoginSession).where(QrLoginSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    if _expired(session):
        await db.delete(session)
        await db.commit()
        raise HTTPException(status_code=404, detail="Session not found or expired")
    if session.status == "pending":
        return {"status": "pending"}

    # status == "approved"
    user_result = await db.execute(select(User).where(User.id == session.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        # The approving account was deleted between approve and this poll —
        # astronomically unlikely, but fail closed rather than hand back
        # tokens for a user row that no longer exists.
        await db.delete(session)
        await db.commit()
        raise HTTPException(status_code=404, detail="Session not found or expired")

    response = {
        "status": "approved",
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
        "user": UserOut.model_validate(user).model_dump(mode="json"),
    }
    await db.delete(session)
    await db.commit()
    logger.info(f"QR login consumed for user {user.phone or user.email}")
    return response


@router.post("/approve")
async def approve_qr_session(
    data: QrApproveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Called by the mobile app after the teacher scans the code and
    confirms — this is the only step that actually authenticates
    anything (via the app's own bearer token); the QR code itself is
    just an opaque session id with no credentials in it."""
    result = await db.execute(select(QrLoginSession).where(QrLoginSession.id == data.session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    if _expired(session):
        await db.delete(session)
        await db.commit()
        raise HTTPException(status_code=404, detail="Session not found or expired")
    if session.status != "pending":
        raise HTTPException(status_code=400, detail="Session already used")

    session.status = "approved"
    session.user_id = user.id
    session.access_token = create_access_token(user.id)
    # Always "web", regardless of what device is doing the approving —
    # this token is for the browser that showed the QR code, not the
    # phone confirming it (see RefreshToken.platform's docstring).
    session.refresh_token = await create_refresh_token(
        db, user.id, user_agent=session.browser_user_agent, platform="web"
    )
    await db.commit()
    logger.info(f"QR login approved by {user.phone or user.email} for session {data.session_id}")
    return {"status": "ok"}
