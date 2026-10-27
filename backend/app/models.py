import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, BigInteger, LargeBinary
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

    # Which kind of admin, when role == "admin". NULL for a plain user
    # and for an admin whose tier predates this column (require_permission
    # in app/admin_roles.py treats that NULL as "super", not "no access" -
    # an existing admin never silently loses capability from this column
    # merely existing). 'super' | 'finance' | 'support' | 'readonly'.
    # role itself stays a plain "user"/"admin" gate everywhere it already
    # was - this column only adds granularity on top, it never replaces
    # that check.
    admin_tier: Mapped[str | None] = mapped_column(String(20), default=None)

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

    # --- Telegram top-ups -------------------------------------------
    #
    # Added to the EXISTING ledger rather than a parallel table. This
    # row is already the single source of truth for a balance: a second
    # table would have to be kept in step with it, and the first time
    # they disagreed nobody would know which was right.

    # The acting administrator's numeric Telegram id. Distinct from
    # actor_id, which is a users.id FK — an admin who reviews payments
    # in Telegram need not have a Dastyor account at all.
    actor_telegram_id: Mapped[int | None] = mapped_column(BigInteger, default=None)

    # What makes a credit happen exactly once. The confirm button
    # carries this value, so a double tap, a retried callback and a
    # redelivered update all arrive with the SAME key and the unique
    # index rejects every attempt after the first. It is also what the
    # bot looks up after a network error to find out whether the credit
    # it lost the answer to actually landed.
    idempotency_key: Mapped[str | None] = mapped_column(String(64), default=None)

    # The operation number shown to the teacher ("TX-7F3K9A2B"). Short
    # and speakable, unlike the uuid primary key, so it can be read out
    # to support.
    public_code: Mapped[str | None] = mapped_column(String(20), default=None, index=True)


class BalanceTopupRequest(Base):
    """A teacher's in-app "I sent money, please credit it" declaration.

    This table exists so the Balance page can offer a top-up path that
    does not require Telegram, for the teachers who do not have it. It
    changes nothing about who can move money: exactly like the Telegram
    flow, submitting one of these credits nothing by itself. An
    administrator reads it, verifies the transfer against their own bank
    app, and types the amount to credit — the same manual trust boundary
    as `BalanceTransaction.actor_id`, just reached from the web admin
    console instead of the bot's `/pending` queue.
    """

    __tablename__ = "balance_topup_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    requested_dirams: Mapped[int] = mapped_column(default=0)
    note: Mapped[str | None] = mapped_column(String(255), default=None)
    receipt_path: Mapped[str | None] = mapped_column(String(500), default=None)

    # pending | approved | rejected
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    credited_dirams: Mapped[int | None] = mapped_column(default=None)
    admin_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    admin_note: Mapped[str | None] = mapped_column(String(255), default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class AdminLoginAttempt(Base):
    __tablename__ = "admin_login_attempts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    identifier: Mapped[str] = mapped_column(String(64), index=True)
    ip: Mapped[str | None] = mapped_column(String(60), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, default=None, index=True)

    # The @username, lower-cased, WITHOUT the leading @. Captured at link
    # time and refreshed on every message, because Telegram's Bot API
    # offers no way to look a user up by username — a bot only learns one
    # from someone who has written to it. This column is what makes
    # "/addadmin @name" possible at all.
    #
    # It is a convenience for finding people, never an identity: grants
    # are keyed on telegram_user_id. A username can be changed and the
    # freed name taken by somebody else, so the stored copy can go stale
    # between refreshes.
    username: Mapped[str | None] = mapped_column(String(64), default=None, index=True)

    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    revoked: Mapped[bool] = mapped_column(default=False, index=True)


class TelegramLinkToken(Base):
    __tablename__ = "telegram_link_tokens"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used: Mapped[bool] = mapped_column(default=False, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    used_by_chat_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class PaymentRequest(Base):
    __tablename__ = "payment_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    public_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    client_request_key: Mapped[str | None] = mapped_column(String(100), unique=True, default=None)
    standalone_notification_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)

    requested_dirams: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(20), default="awaiting_receipt", index=True)

    receipt_file_id: Mapped[str | None] = mapped_column(String(255), default=None)
    receipt_path: Mapped[str | None] = mapped_column(String(500), default=None)
    receipt_mime: Mapped[str | None] = mapped_column(String(100), default=None)
    receipt_kind: Mapped[str | None] = mapped_column(String(20), default=None)
    receipt_bytes: Mapped[int | None] = mapped_column(default=None)

    ocr_amount_dirams: Mapped[int | None] = mapped_column(default=None)
    ocr_currency: Mapped[str | None] = mapped_column(String(16), default=None)
    ocr_sender: Mapped[str | None] = mapped_column(String(255), default=None)
    ocr_recipient: Mapped[str | None] = mapped_column(String(255), default=None)
    ocr_reference: Mapped[str | None] = mapped_column(String(120), default=None)
    ocr_paid_at_text: Mapped[str | None] = mapped_column(String(120), default=None)
    ocr_status_text: Mapped[str | None] = mapped_column(String(120), default=None)
    ocr_confidence: Mapped[int] = mapped_column(default=0)
    ocr_engine: Mapped[str | None] = mapped_column(String(40), default=None)
    ocr_warnings: Mapped[str | None] = mapped_column(Text, default=None)
    ocr_raw_text: Mapped[str | None] = mapped_column(Text, default=None)

    reference_normalized: Mapped[str | None] = mapped_column(String(120), default=None, index=True)

    credited_dirams: Mapped[int] = mapped_column(default=0)
    balance_transaction_id: Mapped[str | None] = mapped_column(String(36), default=None)

    decided_by_telegram_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    decision_note: Mapped[str | None] = mapped_column(Text, default=None)

    admin_message_json: Mapped[str | None] = mapped_column(Text, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class PaymentAuditLog(Base):
    __tablename__ = "payment_audit_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    payment_request_id: Mapped[str] = mapped_column(String(36), index=True)
    event: Mapped[str] = mapped_column(String(40), index=True)
    actor_kind: Mapped[str] = mapped_column(String(20))
    actor_telegram_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), default=None)
    detail: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class TelegramProcessedUpdate(Base):
    __tablename__ = "telegram_processed_updates"

    # Composite key, NOT update_id alone. Every bot has its own
    # independent update_id sequence, so once a second (admin) bot exists
    # the two collide: admin update 7 would be seen as "already
    # processed" because user update 7 was. The symptom would be
    # silently dropped approvals, which is the worst possible thing for
    # this table to get wrong.
    bot: Mapped[str] = mapped_column(String(20), primary_key=True)
    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )


class TelegramAdmin(Base):
    """An administrator granted at runtime, from inside the bot.

    Complements ``TELEGRAM_ADMIN_IDS``, which stays the bootstrap set:
    those ids are "root" and cannot be revoked through the bot, so a
    mistake — or a compromised added admin — can never lock the owner
    out of their own payment reviews.

    Rows are revoked, never deleted: who granted whom, and who took it
    away, is exactly the history worth keeping for a permission that can
    move money.

    Authorization itself no longer reads this table directly (see
    telegram/service.py's granted_admin_ids(), which now resolves
    through TelegramAccount -> User.role instead) - a grant or revoke
    made here writes User.role/admin_tier at the same time, specifically
    so the two never drift apart. This table is kept for exactly two
    things now: a grant can still sit PENDING for an account that has
    not linked Telegram yet (there is no other place to park that), and
    it is the historical record the web CRM's audit views read from.
    """

    __tablename__ = "telegram_admins"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # NULL until the account links Telegram. A grant can be made for any
    # Dastyor user, including one who has never opened the bot — it then
    # sits PENDING and activates the moment they link, because only then
    # does a Telegram id exist to authorize against. Granting still
    # cannot invent an identity; it just stops the owner having to wait
    # and remember.
    telegram_user_id: Mapped[int | None] = mapped_column(
        BigInteger, default=None, index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None, index=True
    )
    added_by_telegram_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    revoked: Mapped[bool] = mapped_column(default=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    revoked_by_telegram_id: Mapped[int | None] = mapped_column(
        BigInteger, default=None
    )
    note: Mapped[str | None] = mapped_column(String(255), default=None)

    # Set once a human has looked at this grant on the CRM's
    # migration-review worklist and either promoted the linked User to
    # role='admin' or explicitly chosen to leave it alone. NULL is what
    # keeps a grant ON that worklist - it is never set automatically by
    # anything, including add_admin_by_short_id, which already flips
    # User.role itself and has nothing left here to "review".
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class StandaloneBotAdmin(Base):
    """Backend authorization for the separate bot's review interface."""
    __tablename__ = "standalone_bot_admins"

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    granted_by_telegram_id: Mapped[int] = mapped_column(BigInteger)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class TelegramBotState(Base):
    __tablename__ = "telegram_bot_state"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class PaymentCard(Base):
    """A bank card or requisite teachers are shown when topping up.

    Plural and structured, unlike TelegramBotState.pay_instructions
    (the single free-text blob the bot's /pay and /paycontrol already
    read/write). That blob stays the one thing both the bot and the web
    app actually display - this table is the CRM's management surface
    for it: activating or deactivating a card here regenerates the blob
    through telegram.service.set_pay_instructions_web(), so there is
    still exactly one value shown to a teacher and exactly one audit
    trail for changing it (see routers/admin_crm.py).

    card_number_encrypted is never the plaintext card number. It is
    pgcrypto's pgp_sym_encrypt() output, decrypted only by the one
    detail endpoint gated on the cards.manage permission - see that
    endpoint's own comment for why this is done in Postgres rather than
    in the Python process.
    """

    __tablename__ = "payment_cards"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    bank_name: Mapped[str] = mapped_column(String(120))
    holder_name: Mapped[str] = mapped_column(String(120))
    card_number_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    currency: Mapped[str] = mapped_column(String(10), default="TJS")
    note: Mapped[str | None] = mapped_column(String(255), default=None)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class Expense(Base):
    """A bookkeeping entry for the Reports/profit page - never a path
    to move money. Nothing here ever reads or writes balance_dirams,
    BalanceTransaction or any payment table; it exists purely so
    "approved top-ups minus expenses" has a real expenses side instead
    of always being reported as "not yet counted"."""

    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    category: Mapped[str] = mapped_column(String(60), index=True)
    amount_dirams: Mapped[int] = mapped_column()
    note: Mapped[str | None] = mapped_column(String(255), default=None)
    spent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
