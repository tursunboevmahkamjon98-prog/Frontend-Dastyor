import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, default=None)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, default=None)
    phone_verified: Mapped[bool] = mapped_column(default=False)
    hashed_password: Mapped[str] = mapped_column(String(255))
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, default=None)
    avatar_url: Mapped[str | None] = mapped_column(String(500), default=None)
    language: Mapped[str] = mapped_column(String(20), default="Русский")
    role: Mapped[str] = mapped_column(String(20), default="user")
    is_premium: Mapped[bool] = mapped_column(default=False)
    free_konspekt_used: Mapped[int] = mapped_column(default=0)
    free_lektsiya_used: Mapped[int] = mapped_column(default=0)
    free_test_used: Mapped[int] = mapped_column(default=0)
    free_prezentatsiya_used: Mapped[int] = mapped_column(default=0)
    free_amaliy_used: Mapped[int] = mapped_column(default=0)
    free_igra_used: Mapped[int] = mapped_column(default=0)
    free_generation_used: Mapped[bool] = mapped_column(default=False)
    short_id: Mapped[str | None] = mapped_column(String(6), unique=True, index=True, default=None)
    balance_dirams: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    konspekts = relationship("Konspekt", back_populates="owner", cascade="all, delete-orphan")
    presentations = relationship("Presentation", back_populates="owner", cascade="all, delete-orphan")
    tests = relationship("Test", back_populates="owner", cascade="all, delete-orphan")
    lectures = relationship("Lecture", back_populates="owner", cascade="all, delete-orphan")
    practical_tasks = relationship("PracticalTask", back_populates="owner", cascade="all, delete-orphan")
    games = relationship("Game", back_populates="owner", cascade="all, delete-orphan")
    test_attempts = relationship("TestAttempt", back_populates="user", cascade="all, delete-orphan")
    game_attempts = relationship("GameAttempt", back_populates="user", cascade="all, delete-orphan")

    @property
    def balance_somoni(self) -> float:
        return self.balance_dirams / 100


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), index=True)
    code: Mapped[str] = mapped_column(String(6), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    verified: Mapped[bool] = mapped_column(default=False, index=True)
    used: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class PhoneVerificationCode(Base):
    __tablename__ = "phone_verification_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone: Mapped[str] = mapped_column(String(20), index=True)
    code: Mapped[str] = mapped_column(String(6), index=True)
    purpose: Mapped[str] = mapped_column(String(20), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    verified: Mapped[bool] = mapped_column(default=False, index=True)
    used: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class RateLimitAttempt(Base):
    __tablename__ = "rate_limit_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    purpose: Mapped[str] = mapped_column(String(30), index=True)
    key: Mapped[str] = mapped_column(String(120), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class QrLoginSession(Base):
    __tablename__ = "qr_login_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), default=None)
    access_token: Mapped[str | None] = mapped_column(Text, default=None)
    refresh_token: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    browser_user_agent: Mapped[str | None] = mapped_column(Text, default=None)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    user_agent: Mapped[str | None] = mapped_column(Text, default=None)
    login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    platform: Mapped[str] = mapped_column(String(10), default="mobile")


class TrustedDevice(Base):
    __tablename__ = "trusted_devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    user_agent: Mapped[str | None] = mapped_column(Text, default=None)
    platform: Mapped[str] = mapped_column(String(10), default="mobile")


class Konspekt(Base):
    __tablename__ = "konspekts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(120), index=True)
    grade: Mapped[str] = mapped_column(String(20), index=True)
    content: Mapped[str | None] = mapped_column(Text, default=None)
    previous_content: Mapped[str | None] = mapped_column(Text, default=None)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    is_favorite: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    owner = relationship("User", back_populates="konspekts")

    @property
    def has_undo(self) -> bool:
        return self.previous_content is not None


class Lecture(Base):
    __tablename__ = "lectures"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(120), index=True)
    grade: Mapped[str] = mapped_column(String(20), index=True)
    content: Mapped[str | None] = mapped_column(Text, default=None)
    previous_content: Mapped[str | None] = mapped_column(Text, default=None)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    is_favorite: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    owner = relationship("User", back_populates="lectures")

    @property
    def has_undo(self) -> bool:
        return self.previous_content is not None


class Presentation(Base):
    __tablename__ = "presentations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(120), index=True)
    grade: Mapped[str] = mapped_column(String(20), index=True)
    slides_json: Mapped[str | None] = mapped_column(Text, default=None)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    is_favorite: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    owner = relationship("User", back_populates="presentations")


class Test(Base):
    __tablename__ = "tests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(120), index=True)
    grade: Mapped[str] = mapped_column(String(20), index=True)
    questions_json: Mapped[str | None] = mapped_column(Text, default=None)
    time_limit_seconds: Mapped[int | None] = mapped_column(default=None)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    is_favorite: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    owner = relationship("User", back_populates="tests")
    attempts = relationship("TestAttempt", back_populates="test", cascade="all, delete-orphan")


class TestAttempt(Base):
    __tablename__ = "test_attempts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    test_id: Mapped[str] = mapped_column(ForeignKey("tests.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(default=0)
    total: Mapped[int] = mapped_column(default=0)
    answers_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    test = relationship("Test", back_populates="attempts")
    user = relationship("User", back_populates="test_attempts")


class PracticalTask(Base):
    __tablename__ = "practical_tasks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(120), index=True)
    grade: Mapped[str] = mapped_column(String(20), index=True)
    tasks_json: Mapped[str | None] = mapped_column(Text, default=None)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    is_favorite: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    owner = relationship("User", back_populates="practical_tasks")


class Game(Base):
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(120), index=True)
    grade: Mapped[str] = mapped_column(String(20), index=True)
    game_json: Mapped[str | None] = mapped_column(Text, default=None)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    is_favorite: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    owner = relationship("User", back_populates="games")
    attempts = relationship("GameAttempt", back_populates="game", cascade="all, delete-orphan")


class GameAttempt(Base):
    __tablename__ = "game_attempts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(10))
    score: Mapped[int] = mapped_column(default=0)
    score_p1: Mapped[int | None] = mapped_column(default=None)
    score_p2: Mapped[int | None] = mapped_column(default=None)
    won: Mapped[bool] = mapped_column(default=False)
    rounds_cleared: Mapped[int] = mapped_column(default=0)
    total_rounds: Mapped[int] = mapped_column(default=0)
    max_streak: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    game = relationship("Game", back_populates="attempts")
    user = relationship("User", back_populates="game_attempts")



class LessonImageCache(Base):
    __tablename__ = "lesson_image_cache"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    subject: Mapped[str] = mapped_column(String(120), index=True)
    topic_key: Mapped[str] = mapped_column(String(255), index=True)
    topic: Mapped[str] = mapped_column(String(255))
    slot: Mapped[int] = mapped_column(default=0)
    path: Mapped[str] = mapped_column(String(500))
    caption: Mapped[str | None] = mapped_column(Text, default=None)
    credit: Mapped[str | None] = mapped_column(String(255), default=None)
    source: Mapped[str | None] = mapped_column(String(500), default=None)
    explanation: Mapped[str | None] = mapped_column(Text, default=None)
    width: Mapped[int | None] = mapped_column(default=None)
    height: Mapped[int | None] = mapped_column(default=None)
    hit_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class BalanceTransaction(Base):
    __tablename__ = "balance_transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20), index=True)
    amount_dirams: Mapped[int] = mapped_column(default=0)
    balance_before: Mapped[int] = mapped_column(default=0)
    balance_after: Mapped[int] = mapped_column(default=0)
    actor_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None, index=True
    )
    reason: Mapped[str | None] = mapped_column(String(255), default=None)
    material_type: Mapped[str | None] = mapped_column(String(30), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class AdminLoginAttempt(Base):
    __tablename__ = "admin_login_attempts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    identifier: Mapped[str] = mapped_column(String(64), index=True)
    ip: Mapped[str | None] = mapped_column(String(60), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
