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
    # Nullable now — phone (below) is the actual login identifier for every
    # new account; email survives only for accounts that predate the phone
    # switch (and for the ADMIN_EMAIL-seeded admin account in main.py),
    # never required or shown during registration/login anymore.
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, default=None)
    # E.164-ish, always "+992XXXXXXXXX" (see schemas._NormalizedPhone) —
    # the actual login identifier. Nullable at the DB level only so the
    # column can be added to the existing `users` table without a real
    # migration tool (see database.py's init_db); every row created through
    # POST /auth/register always has one.
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, default=None)
    # True the instant the row is created — see routers/auth.py's register
    # flow, which only ever creates the User row AFTER the SMS code is
    # verified (unlike the old email flow, there's no "registered but
    # unconfirmed" account sitting in the table).
    phone_verified: Mapped[bool] = mapped_column(default=False)
    hashed_password: Mapped[str] = mapped_column(String(255))
    # Google's stable per-user "sub" claim — set only for accounts created
    # or linked via POST /auth/google (see routers/auth.py). Nullable/
    # unique like phone/email above: most accounts still sign in with
    # phone+password and never get one.
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, default=None)
    avatar_url: Mapped[str | None] = mapped_column(String(500), default=None)
    language: Mapped[str] = mapped_column(String(20), default="Русский")
    role: Mapped[str] = mapped_column(String(20), default="user")
    # Free tier: every new account gets exactly 1 free konspekt, 1 test, 1
    # presentation, 1 lecture (see routers/materials.py's _check_free_limit)
    # — generating a 2nd of any one type requires is_premium. No payment
    # gateway wired up yet (that's a separate, later task needing its own
    # provider account) — for now this is only ever flipped by an admin,
    # by hand, in the admin panel (see routers/admin.py's set_premium),
    # once a teacher has actually paid some other way.
    is_premium: Mapped[bool] = mapped_column(default=False)
    # One flag per material type, set True the moment that type's single
    # free generation is used (see routers/materials.py's
    # _check_can_generate). Deliberately NOT derived from "does the user
    # currently have any row of this type" — that broke the free limit:
    # deleting every konspekt reset the count to 0, making the account
    # look like it had never used its free one and letting it generate
    # for free again indefinitely. These flags never get reset by delete.
    free_konspekt_used: Mapped[bool] = mapped_column(default=False)
    free_lektsiya_used: Mapped[bool] = mapped_column(default=False)
    free_test_used: Mapped[bool] = mapped_column(default=False)
    free_prezentatsiya_used: Mapped[bool] = mapped_column(default=False)
    free_amaliy_used: Mapped[bool] = mapped_column(default=False)
    free_igra_used: Mapped[bool] = mapped_column(default=False)
    # Historical. For a while pricing ran off a single account-wide
    # freebie instead of the per-type flags above, and this is the column
    # that held it; init_db still backfills it so the record of who spent
    # what stays intact, but nothing reads it to make a decision anymore.
    #
    # Pricing is per-type again: app/limits.py's FREE_SLOT_COLUMN claims
    # the four flags above (konspekt, lektsiya, test, prezentatsiya),
    # atomically, one free each. Going back that way is why init_db
    # replays kind='free' ledger rows onto those columns — accounts that
    # spent the account-wide freebie have it set here and nowhere else.
    free_generation_used: Mapped[bool] = mapped_column(default=False)
    # Short 6-digit code a teacher can read out loud/type to an admin when
    # paying for a balance top-up outside the app — the real `id` above is
    # a UUID, unusable for that over Telegram/WhatsApp/phone. Nullable at
    # the DB level (existing rows get backfilled, new ones get assigned
    # lazily) — see app/auth.py's get_current_user, the one place every
    # authenticated request passes through, so every account ends up with
    # one without needing to hook every registration code path.
    short_id: Mapped[str | None] = mapped_column(String(6), unique=True, index=True, default=None)
    # Wallet balance, in dirams (1 somoni = 100 dirams) — integer, never a
    # float, so nothing here is ever subject to floating-point rounding.
    # Only ever changed by an administrator crediting a payment made
    # "completed" — never incremented speculatively/optimistically, since
    # an unconfirmed credit here would be real (if fake) money on the
    # account.
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
    """Now unused by the actual reset-password flow (that's phone/SMS-based
    via PhoneVerificationCode below) — left in place only because it's an
    existing table with no migration tool to drop it cleanly, and nothing
    currently references it."""
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), index=True)
    code: Mapped[str] = mapped_column(String(6), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    verified: Mapped[bool] = mapped_column(default=False, index=True)
    used: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class PhoneVerificationCode(Base):
    """SMS OTP codes for every phone flow that needs one — registration,
    login (mobile app only), and password reset — distinguished by
    `purpose` so a code sent for one can never be replayed for another
    (e.g. a leaked registration code for a phone number can't be used to
    reset that same number's password once an account exists). Mirrors
    PasswordResetToken's verified/used two-step shape (see
    routers/auth.py's forgot-password -> verify-code -> reset-password)
    for the reset purpose; register and login only ever need `used` —
    verify+act happens in one request for both."""
    __tablename__ = "phone_verification_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone: Mapped[str] = mapped_column(String(20), index=True)
    code: Mapped[str] = mapped_column(String(6), index=True)
    purpose: Mapped[str] = mapped_column(String(20), index=True)  # "register" | "login" | "reset"
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    verified: Mapped[bool] = mapped_column(default=False, index=True)
    used: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class RateLimitAttempt(Base):
    """One row per checked attempt for auth.py's rate limiters (login, OTP
    verify, password reset, register-code, ...) — replaces what used to be
    a handful of plain in-memory dicts. Those reset on every restart and
    can't be shared across multiple worker processes/replicas, which
    quietly weakens brute-force protection exactly when scaling to more
    than one process is what makes it matter. `purpose` keeps each
    limiter's counters independent (a login attempt never counts against
    the verify-code limiter for the same phone); `key` is whatever the
    limiter keys on — almost always a phone number, occasionally an
    email. Rows older than every limiter's RATE_WINDOW are harmless
    dead weight rather than a correctness problem, so nothing here
    deletes them proactively — _check_rate_limit's own WHERE clause
    already ignores them, and a periodic cleanup job (or just letting
    the table grow — attempts are tiny rows) is a fine later addition,
    not something this feature depends on."""
    __tablename__ = "rate_limit_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    purpose: Mapped[str] = mapped_column(String(30), index=True)
    key: Mapped[str] = mapped_column(String(120), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class QrLoginSession(Base):
    """A short-lived pairing code the website shows as a QR (id encoded
    as-is, no extra wrapper) — scanned by the already-signed-in mobile
    app to log that browser in as the same account, the same pattern
    WhatsApp Web/Telegram Desktop use. Never carries a password: the app
    just tells the backend "I am <user>, approve this session", and the
    backend mints a completely normal access+refresh token pair for that
    user — the QR code itself grants nothing on its own.

    access_token/refresh_token sit here in plaintext only for the few
    seconds between the app approving and the website's next poll
    picking them up — routers/qr_auth.py's status endpoint deletes the
    row the instant it hands them back, so a session can only ever be
    consumed once (a second poll, or a second browser tab racing the
    first, gets 404 instead of a replayed token pair)."""
    __tablename__ = "qr_login_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending | approved
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), default=None)
    access_token: Mapped[str | None] = mapped_column(Text, default=None)
    refresh_token: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    # Captured from the browser's own request at /qr/create (the one
    # request in this whole flow that actually comes from the browser
    # being paired, not the phone approving it) — carried through to the
    # refresh_token minted in /approve so it shows up right in the
    # "Linked devices" list instead of as the *phone's* user agent.
    browser_user_agent: Mapped[str | None] = mapped_column(Text, default=None)


class RefreshToken(Base):
    """A long-lived credential a client trades for a fresh short-lived JWT
    access token (see app/auth.py's create_refresh_token/rotate_refresh_token)
    once the access token expires, instead of forcing a full re-login every
    ACCESS_TOKEN_EXPIRE_MINUTES. Only the SHA-256 hash of the raw token is
    stored — same "never persist the actual secret" discipline as
    User.hashed_password — so a database read alone can't be replayed as a
    session. Rotated (not just re-validated) on every refresh: each use
    revokes itself and issues a new row, which both limits a leaked token's
    lifetime to one use and gives a cheap tell for theft (a revoked token
    being presented again means two parties now have a copy)."""
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    # Added for the "Linked devices" feature (Profile → Bog'langan
    # qurilmalar, mobile-app-only). Rotation (see auth.py's
    # rotate_refresh_token) replaces this row entirely on every use, so
    # login_at/user_agent/platform are explicitly carried forward from the
    # token being rotated — created_at above drifts to "last refreshed at"
    # for the live row, login_at is the one field that stays put across
    # that whole chain, i.e. what the list screen shows.
    user_agent: Mapped[str | None] = mapped_column(Text, default=None)
    login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    # "web" | "mobile" — set from the X-Client-Platform header ApiClient
    # sends on every request (see qr_auth.py's approve for the one
    # exception: that token is always for the browser being paired, not
    # whatever device is doing the approving). Sessions list only ever
    # shows "web" rows — the phone's own session isn't a "linked device"
    # any more than it is in WhatsApp's own such screen.
    platform: Mapped[str] = mapped_column(String(10), default="mobile")


class TrustedDevice(Base):
    """A browser/phone this user has already proved control of the phone
    number from, so the SMS step of login can be skipped there.

    Login used to send an OTP on *every* sign-in, which meant a teacher
    who logs in daily from the same laptop waited on (and the project paid
    for) an SMS every single time. The code now verifies the *device*
    once: on a successful OTP verification the server mints an opaque
    device token, the client stores it, and presenting it on a later login
    lets the password alone through. A new/unknown device still gets the
    full OTP challenge, so the code keeps doing the job it exists for —
    proving the person holds that phone number — instead of re-proving it
    to the same laptop forever.

    Only the SHA-256 hash is stored, same "never persist the actual
    secret" discipline as RefreshToken/User.hashed_password: a database
    read alone can't be replayed as a trusted device. Unlike a refresh
    token this is NOT a credential on its own — it never grants a session
    by itself, it only waives the second factor for a request that still
    has to pass the password check."""
    __tablename__ = "trusted_devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    # Bumped on every successful skip, so an "active devices" view (and any
    # future prune of long-unused rows) has something truthful to sort on.
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    user_agent: Mapped[str | None] = mapped_column(Text, default=None)
    # "web" | "mobile", from the X-Client-Platform header — same source as
    # RefreshToken.platform.
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
    # Snapshot of `content` from right before its last change (e.g. a
    # section regeneration) — lets a teacher undo one step if they don't
    # like the result, instead of the old content being gone for good the
    # instant they click "regenerate". Single-level only (not full
    # history): set whenever content changes, cleared once undone.
    previous_content: Mapped[str | None] = mapped_column(Text, default=None)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    is_favorite: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    owner = relationship("User", back_populates="konspekts")

    @property
    def has_undo(self) -> bool:
        return self.previous_content is not None


# Deliberately its own table/model rather than a "type" column on Konspekt
# — a лекция explains a topic (deep content: explanation, key concepts,
# examples, visual diagrams) while a конспект manages a lesson (goals,
# competencies, lesson program, pair work, homework, assessment); teacher
# feedback was explicit that these are two different kinds of material a
# teacher picks between, not two views of the same one — so it gets its
# own row in "My materials" the same way presentations/tests do, not a
# checkbox on an existing konspekt.
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
    # ORPHANED as of the online-play removal (2026-09-14): this drove the
    # per-question countdown in the quiz runner, and nothing reads it now
    # that a test is a printable document only. Kept rather than dropped
    # because removing a column means a destructive migration against
    # live data for zero functional gain — an unread column costs
    # nothing. Delete it (with the matching ALTER TABLE) only if online
    # play is ruled out for good.
    time_limit_seconds: Mapped[int | None] = mapped_column(default=None)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    is_favorite: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    owner = relationship("User", back_populates="tests")
    attempts = relationship("TestAttempt", back_populates="test", cascade="all, delete-orphan")


class TestAttempt(Base):
    """One completed online play-through of a Test.

    ORPHANED as of 2026-09-14: online test play was removed on purpose —
    the quiz runner, its /play route and both /tests/{id}/attempts
    endpoints are gone, and a test is now a printable document only. No
    code writes or reads this table anymore.

    Kept rather than dropped because dropping it destroys whatever
    attempt history already exists, irreversibly, to save nothing — an
    unused table costs no runtime. Drop it (and the `attempts`
    relationships on Test/User) only once that history is confirmed
    worthless AND online play is ruled out for good.

    Original shape, still accurate if it is ever revived: a separate
    table rather than a column on Test because a test is played many
    times by the same account (retakes) and each play needs its own
    score/answers kept, not overwritten. Auto-graded question types
    (multiple_choice/true_false/multiple_select) counted toward
    score/total; open_ended answers were stored in answers_json for
    review but excluded from both."""
    __tablename__ = "test_attempts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    test_id: Mapped[str] = mapped_column(ForeignKey("tests.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(default=0)
    total: Mapped[int] = mapped_column(default=0)
    # JSON list of {index, type, given, correct, timedOut} — one entry per
    # question, in question order; see TestPlayer.tsx's Answer shape.
    answers_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    test = relationship("Test", back_populates="attempts")
    user = relationship("User", back_populates="test_attempts")


class PracticalTask(Base):
    """💡 Амалӣ супоришҳо — individual/group practical assignments at a
    chosen difficulty, as their own printable document (worksheet-style),
    same shape as Test/Konspekt rather than a variant of either."""
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
    """🎮 Интерактивные игры — quiz/matching/true-false/speed-round content
    played in the app (web + mobile), not printed. game_json holds one
    "rounds" list, each round tagged with its own "type" (see
    app/ai_service.py's _game_prompt for the shape) so the player UI can
    dispatch per round without a separate table per game type."""
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
    """One completed play-through of a Game (solo or duel — see
    components/game/GameEngine.tsx's GameResult) — same reasoning as
    TestAttempt above: a game gets replayed many times, each run keeps its
    own row rather than overwriting a single "best score" column, so the
    start screen's "Ваши лучшие результаты" list has real history to show,
    not just one number.

    There is no multi-student login/roster in this app (see User model —
    every account is its own teacher/owner), so this is NOT a cross-student
    leaderboard: every attempt on one game is by the same account that
    owns it, replaying it. The start screen labels this "your own past
    runs," not "other players," to stay honest about what the data
    actually is."""
    __tablename__ = "game_attempts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(10))  # solo | duel
    score: Mapped[int] = mapped_column(default=0)
    # Duel keeps both sides too (score above holds the winning side's score,
    # so solo and duel runs can share one "score" column for sorting) —
    # null for solo runs.
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
    """One Wikimedia Commons illustration a konspekt/lecture generation
    already fetched AND passed the AI relevance check for (see
    ai_service.py's _caption_and_verify_images) — reused for the next
    generation on the same (subject, topic) instead of searching Commons
    again from scratch.

    Not owned by a user — this is shared reference material, the same way
    the pre-cached official textbooks (_TEXTBOOK_CACHE_DIR) are shared
    across every teacher, not per-account. Matched the same way
    routers/materials.py's _previous_digests already matches a konspekt's
    predecessors: (subject, topic) case-insensitively, no grade — a
    diagram of the Pythagorean theorem is the same diagram whether the
    lesson is grade 8 or grade 9's review of it, and narrowing by grade
    too would mean two teachers on the same topic in different grades
    both pay the Commons search cost the cache exists to avoid.

    `hit_count`/`last_used_at` are not read by anything yet — kept so a
    future cleanup pass (Commons occasionally deletes/renames a file)
    can prioritise checking the images actually still being served over
    ones nobody has hit in months, without needing a schema change to
    add that later."""
    __tablename__ = "lesson_image_cache"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    subject: Mapped[str] = mapped_column(String(120), index=True)
    # Lowercased/stripped topic — the lookup key. Kept separate from the
    # display-cased `topic` below so matching is exact-normalized while
    # what's shown in an admin listing still reads naturally.
    topic_key: Mapped[str] = mapped_column(String(255), index=True)
    topic: Mapped[str] = mapped_column(String(255))
    # One row per (subject, topic_key, slot) — slot distinguishes a
    # topic's 1st vs 2nd lesson_images entry, since they illustrate
    # different sections (different "position_after") and aren't
    # interchangeable.
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
    """Append-only ledger of every change to User.balance_dirams and of
    every claim of the account's one free generation.

    Nothing in this table is ever updated or deleted. A balance that only
    exists as one mutable integer column can be wrong with no way to find
    out how it got that way — which matters here because that integer is
    real money a teacher paid outside the app. Two questions have to be
    answerable after the fact: "who credited this account, when, and
    why", and "what did this account actually spend its balance on".

    Written by app/limits.py (charges and refunds, in the same
    transaction as the balance UPDATE itself, so a row can never be
    missing for a movement that happened) and by routers/admin.py's
    add_balance (top-ups)."""
    __tablename__ = "balance_transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # ondelete="SET NULL", not CASCADE. This table's own docstring says
    # "nothing in this table is ever deleted" — CASCADE quietly broke that
    # promise for the one column that matters most: an admin deleting a
    # teacher's account (routers/admin.py's delete_user) took their whole
    # payment history down with it. If that teacher later says "I paid,
    # where's my balance", the ledger that would prove it is gone. Same
    # fix already applied to actor_id below; this was the one column that
    # didn't get it. Nullable so the row can outlive the account.
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # "topup" | "charge" | "refund" | "free" — "free" is the zero-amount
    # row recording that the account's single free generation was spent,
    # kept in the same ledger so one query answers "what has this account
    # generated and what did each one cost".
    kind: Mapped[str] = mapped_column(String(20), index=True)
    # Signed, in dirams: positive credits, negative debits, 0 for "free".
    amount_dirams: Mapped[int] = mapped_column(default=0)
    balance_before: Mapped[int] = mapped_column(default=0)
    balance_after: Mapped[int] = mapped_column(default=0)
    # The admin who did it, for "topup" — NULL when the movement was the
    # user's own generation. ondelete="SET NULL" rather than CASCADE: an
    # admin account being deleted later must not erase the record of the
    # top-ups they made.
    actor_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None, index=True
    )
    # Free text: the admin's stated reason for a top-up, or the material
    # type for a charge/refund.
    reason: Mapped[str | None] = mapped_column(String(255), default=None)
    material_type: Mapped[str | None] = mapped_column(String(30), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class AdminLoginAttempt(Base):
    """Failed sign-ins against an account that holds the admin role.

    Separate from RateLimitAttempt (which counts requests per IP/phone to
    throttle floods) because this answers a different question: has THIS
    admin account been under a password-guessing attempt, regardless of
    how many addresses the guesses came from. A distributed brute force
    stays under every per-IP limit by design; locking the targeted
    account itself is what stops it.

    Cleared on a successful login — see routers/auth.py."""
    __tablename__ = "admin_login_attempts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # The identifier the attempt was made against (normalized phone), not
    # a user id — an attempt against a non-existent account still needs
    # counting, and looking the user up first would leak which phone
    # numbers are admins by timing.
    identifier: Mapped[str] = mapped_column(String(64), index=True)
    ip: Mapped[str | None] = mapped_column(String(60), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
