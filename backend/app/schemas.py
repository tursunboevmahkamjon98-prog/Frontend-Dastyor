import re
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator


# ── Auth ─────────────────────────────────────────────────────────────────────
# Phone (Tajik, "+992XXXXXXXXX") is the primary login identifier — see
# app/models.py's User.phone docstring and app/sms_service.py for the OTP
# delivery side. Google Sign-In (GoogleAuthRequest below) is the other
# supported way in; a Google-created account simply has no phone until the
# teacher adds one.

_PHONE_RE = re.compile(r"^\+992\d{9}$")


class _NormalizedPhone(BaseModel):
    """Normalizes the `phone` field on every request that carries one to
    the canonical "+992XXXXXXXXX" form. Accepts a bare 9-digit local
    number ("938123456"), a 992-prefixed one with or without "+", or one
    already correctly formatted, with spaces/dashes/parens stripped —
    so however a teacher happens to type it, it compares equal to
    whatever's stored (same normalize-before-compare discipline the old
    _NormalizedEmail applied to email). Anything that doesn't resolve to
    a valid Tajik mobile number is rejected with a clear message rather
    than silently stored malformed.
    """

    @field_validator("phone", mode="before", check_fields=False)
    @classmethod
    def _normalize_phone(cls, v):
        if not isinstance(v, str):
            return v
        digits = re.sub(r"\D", "", v)
        if digits.startswith("992") and len(digits) == 12:
            normalized = "+" + digits
        elif len(digits) == 9:
            normalized = "+992" + digits
        else:
            normalized = "+" + digits
        if not _PHONE_RE.match(normalized):
            raise ValueError("Введите корректный номер телефона в формате +992XXXXXXXXX")
        return normalized


class UserRegister(_NormalizedPhone):
    """Final step of registration — POST /auth/register/send-code {phone}
    must be called first to get `code` sent via SMS; this creates the
    account only once that code is verified (see routers/auth.py's
    register endpoint, which checks it against PhoneVerificationCode
    before touching the users table at all)."""
    full_name: str
    phone: str
    code: str
    password: str


class SendRegisterCodeRequest(_NormalizedPhone):
    phone: str


class UserLogin(_NormalizedPhone):
    phone: str
    password: str


class LoginSendCodeRequest(_NormalizedPhone):
    """Step 1 of the OTP login — same credential check as UserLogin, but on
    success sends an SMS code instead of tokens. Tokens come back
    immediately (no SMS) when `phone` is settings.OTP_BYPASS_PHONE, when
    the account is an admin, or when `device_token` identifies a device
    this user already passed an OTP on — see routers/auth.py's
    login_send_code."""
    phone: str
    password: str
    # Opaque token the client got back from a previous successful
    # /login/verify on THIS device (see models.TrustedDevice). Optional and
    # untrusted input: an absent/expired/foreign value simply means the
    # normal SMS challenge runs, never an error.
    device_token: str | None = None


class LoginVerifyRequest(_NormalizedPhone):
    """Step 2 — trades the code LoginSendCodeRequest sent for tokens, and
    (unless [remember_device] is false) hands back a device token that lets
    this same device skip the SMS step next time."""
    phone: str
    code: str
    remember_device: bool = True


class EmailRegister(BaseModel):
    """Direct email+password registration — no OTP step (unlike the phone
    flow above): the account is created immediately, same trust level as
    a Google-created one (see routers/auth.py's /auth/register-email)."""
    full_name: str
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Введите корректный email")
        return v


class EmailLogin(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class GoogleAuthRequest(BaseModel):
    """The ID token (a signed JWT, not an access token) handed back by
    Google Identity Services' `credential` callback on the frontend — see
    routers/auth.py's /auth/google, which verifies it server-side before
    trusting any claim inside it."""
    credential: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserOut"
    # Only present on the response that just verified an SMS code (see
    # routers/auth.py's login_verify): the client stores it and replays it
    # on later logins to skip the code. Every other token-issuing endpoint
    # leaves it null — a device that never passed an OTP shouldn't be
    # handed a token that says it did.
    device_token: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class QrApproveRequest(BaseModel):
    session_id: str


class LogoutRequest(BaseModel):
    refresh_token: str


class SessionOut(BaseModel):
    """One entry in the mobile app's "Linked devices" list (Profile →
    Bog'langan qurilmalar) — one row per still-active web refresh token,
    i.e. one browser currently signed into this account. The mobile
    app's own session never appears here (see routers/auth.py's
    list_sessions — filtered to platform == "web")."""
    id: str
    user_agent: str | None
    login_at: datetime

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: str
    full_name: str
    # Nullable — only accounts that predate the phone switch (or the
    # ADMIN_EMAIL-seeded admin) still carry one; never collected at
    # registration anymore.
    email: str | None = None
    phone: str | None = None
    phone_verified: bool = False
    # Free tier: 1 konspekt + 1 test + 1 presentation + 1 lecture; a 2nd of
    # any one type needs is_premium=True (see routers/materials.py's
    # _check_free_limit). Only an admin can flip this today — no payment
    # gateway wired up yet.
    is_premium: bool = False
    balance_somoni: float = 0
    avatar_url: str | None = None
    language: str = "Русский"
    role: str = "user"
    created_at: datetime
    # 6-digit code the teacher reads out to an admin when paying for a
    # balance top-up outside the app — see models.py's User.short_id.
    # Optional only because a not-yet-backfilled account could in theory
    # be serialized before get_current_user's lazy assignment runs.
    short_id: str | None = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = None
    language: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordRequest(_NormalizedPhone):
    phone: str


class VerifyCodeRequest(_NormalizedPhone):
    phone: str
    code: str


class ResetPasswordRequest(_NormalizedPhone):
    phone: str
    code: str
    new_password: str


# ── Konspekt ─────────────────────────────────────────────────────────────────

class KonspektCreate(BaseModel):
    title: str
    subject: str
    grade: str
    content: str | None = None


class KonspektUpdate(BaseModel):
    title: str | None = None
    subject: str | None = None
    grade: str | None = None
    content: str | None = None
    is_favorite: bool | None = None


class KonspektOut(BaseModel):
    id: str
    title: str
    subject: str
    grade: str
    content: str | None
    is_favorite: bool
    has_undo: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Lecture (лекция — explains a topic; конспект manages a lesson) ──────────

class LectureCreate(BaseModel):
    title: str
    subject: str
    grade: str
    content: str | None = None


class LectureUpdate(BaseModel):
    title: str | None = None
    subject: str | None = None
    grade: str | None = None
    content: str | None = None
    is_favorite: bool | None = None


class LectureOut(BaseModel):
    id: str
    title: str
    subject: str
    grade: str
    content: str | None
    is_favorite: bool
    has_undo: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Presentation ─────────────────────────────────────────────────────────────

class PresentationCreate(BaseModel):
    title: str
    subject: str
    grade: str
    slides_json: str | None = None


class PresentationUpdate(BaseModel):
    title: str | None = None
    subject: str | None = None
    grade: str | None = None
    slides_json: str | None = None
    is_favorite: bool | None = None


class PresentationOut(BaseModel):
    id: str
    title: str
    subject: str
    grade: str
    slides_json: str | None
    is_favorite: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Test ─────────────────────────────────────────────────────────────────────

class TestCreate(BaseModel):
    title: str
    subject: str
    grade: str
    questions_json: str | None = None
    time_limit_seconds: int | None = None


class TestUpdate(BaseModel):
    title: str | None = None
    subject: str | None = None
    grade: str | None = None
    questions_json: str | None = None
    is_favorite: bool | None = None
    time_limit_seconds: int | None = None


class TestOut(BaseModel):
    id: str
    title: str
    subject: str
    grade: str
    questions_json: str | None
    time_limit_seconds: int | None = None
    is_favorite: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Game attempts (online play — see components/game/GameEngine.tsx) ───────

class GameAttemptCreate(BaseModel):
    mode: str  # solo | duel
    score: int
    score_p1: int | None = None
    score_p2: int | None = None
    won: bool
    rounds_cleared: int
    total_rounds: int
    max_streak: int = 0


class GameAttemptOut(BaseModel):
    id: str
    game_id: str
    mode: str
    score: int
    score_p1: int | None
    score_p2: int | None
    won: bool
    rounds_cleared: int
    total_rounds: int
    max_streak: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Practical tasks ──────────────────────────────────────────────────────────

class PracticalTaskCreate(BaseModel):
    title: str
    subject: str
    grade: str
    tasks_json: str | None = None


class PracticalTaskUpdate(BaseModel):
    title: str | None = None
    subject: str | None = None
    grade: str | None = None
    tasks_json: str | None = None
    is_favorite: bool | None = None


class PracticalTaskOut(BaseModel):
    id: str
    title: str
    subject: str
    grade: str
    tasks_json: str | None
    is_favorite: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Games ────────────────────────────────────────────────────────────────────

class GameCreate(BaseModel):
    title: str
    subject: str
    grade: str
    game_json: str | None = None


class GameUpdate(BaseModel):
    title: str | None = None
    subject: str | None = None
    grade: str | None = None
    game_json: str | None = None
    is_favorite: bool | None = None


class GameOut(BaseModel):
    id: str
    title: str
    subject: str
    grade: str
    game_json: str | None
    is_favorite: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Dashboard stats ──────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    konspekt_count: int
    test_count: int
    presentation_count: int
    lecture_count: int = 0
    practical_count: int = 0
    game_count: int = 0


# ── AI Generate ─────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    material_type: str  # konspekt, test, prezentatsiya
    topic: str
    subject: str
    language: str
    level: str
    grade: str
    slide_count: int | None = None
    question_count: int | None = None
    # "mixed" (default) or one of: multiple_choice, true_false, multiple_select, open_ended
    test_type: str | None = None
    # Konspekt-only optional sections — teacher toggles these off in the
    # create wizard when they don't apply (e.g. an in-class-only lesson
    # with no take-home work). Ignored for other material_types.
    include_homework: bool = True
    include_fun_facts: bool = True
    include_assessment: bool = True
    # Presentation-only wizard choice — which of the 5 PPTX/PDF layouts
    # (app/konspekt_templates.py's registry, reused as-is rather than a
    # separate presentation-only set) this deck uses. Ignored for other
    # material_types; None/unrecognized falls back to "klassik".
    template: str | None = None
    # "Book mode" — extracted text from a teacher-uploaded textbook/notes
    # (see POST /materials/upload-source), used as the primary source for
    # ALL 4 material_types instead of the model's general knowledge. None
    # (the default) is plain topic-only generation. See ai_service.py's
    # per-type _*_prompt functions for how this gets woven into the prompt.
    source_text: str | None = None


class GenerateKonspektStreamRequest(BaseModel):
    """Body for POST /materials/generate-konspekt-stream — the SSE
    streaming counterpart to GenerateRequest, konspekt-only (no
    material_type field, since this endpoint only ever makes a konspekt)."""
    topic: str
    subject: str
    language: str
    level: str
    grade: str
    include_homework: bool = True
    include_fun_facts: bool = True
    include_assessment: bool = True
    # "ai" (default) — generated purely from the model's own knowledge.
    # "source" — built primarily from source_text (see POST
    # /materials/upload-source, which extracts it from an uploaded
    # .pdf/.docx/.txt before the teacher ever submits this request).
    generation_mode: str = "ai"
    source_text: str | None = None
    # Which of the 5 PDF/DOCX export layouts (see app/konspekt_templates.py)
    # this konspekt uses — a teacher-facing wizard choice, unrelated to
    # subject. None/unrecognized falls back to "klassik".
    template: str | None = None


class GenerateAllRequest(BaseModel):
    topic: str
    subject: str
    language: str
    # Kept required so existing callers are unaffected, but the simplified
    # create screen no longer asks a teacher to pick one — it sends the
    # middle value. The AI prompts still read it (see ai_service.py).
    level: str
    grade: str
    slide_count: int | None = 10
    question_count: int | None = 10
    test_type: str | None = None
    # Which of routers/materials.py's _GENERATE_ALL_TYPES to make. None
    # means all of them, which is what "everything at once" always did and
    # what every existing caller still gets.
    #
    # This exists so ONE endpoint can serve both "make me a konspekt" and
    # "make me the lot": the single-material path used to go through
    # /generate, which pins no per-type template and bills each call
    # separately. Routing every request here instead means one atomic
    # reservation and the same _ALL_DEFAULT_TEMPLATES either way, so a deck
    # made alone looks like a deck made as part of a set.
    types: list[str] | None = None


class RegenerateItemRequest(BaseModel):
    material_type: str  # test, prezentatsiya, or konspekt
    topic: str
    subject: str
    language: str
    level: str
    grade: str
    item_index: int = 0
    existing_items: list[dict] = []
    section: str | None = None  # konspekt only — which field to rewrite
    existing_content: dict = {}  # konspekt only — the rest of the konspekt, for context


class RetryLessonImageRequest(BaseModel):
    """Body for POST /materials/{konspekts,lectures}/{id}/replace-image —
    which of the (0 or 1) lesson_images entries to swap for a different
    Commons result. Separate from the no-body fetch-image endpoint (that
    one only fires when a slot is EMPTY); this one replaces a slot that
    already has a picture the teacher doesn't want."""
    index: int = 0


class RegenerateGameRequest(BaseModel):
    """Body for POST /materials/games/{id}/reroll — a fresh 12-round set
    on the same topic/subject/grade an existing game already has (see
    that endpoint's docstring for why this is a reroll-in-place rather
    than a new material). `language` isn't stored on the Game row itself
    (see models.Game — _game_prompt's output never wrote it back), so the
    frontend passes along whatever the currently-loaded content's own
    "language" field says, falling back to Russian exactly like every
    other regenerate/chat-edit call already does."""
    language: str = "Русский"
    level: str = "Средний"


class QuizSetRequest(BaseModel):
    """Body for POST /materials/quiz-set — an ad-hoc set of 4-option
    questions (each with an explanation) for the "Қуттиҳои сеҳрнок" game's
    "let the AI write them" mode, where the player picks subject/topic/
    difficulty/count themselves rather than replaying a saved material's
    own questions. Not tied to any stored material, so nothing is written
    back to the database — the questions live only in the running game."""
    topic: str
    subject: str
    grade: str = "5"
    level: str = "Средний"
    language: str = "Таджикский"
    count: int = Field(default=10, ge=3, le=30)


class QuizSetQuestion(BaseModel):
    question: str
    options: list[str]
    correct_index: int
    explanation: str = ""


class QuizSetResponse(BaseModel):
    questions: list[QuizSetQuestion]


class ChatEditRequest(BaseModel):
    """Free-text edit instruction applied to a whole already-generated
    material (see ai_service.chat_edit_material) — the frontend posts the
    material's current content, gets back the updated content, and saves
    it itself via the existing PUT /materials/{...}/{id} (same place
    RegenerateItemRequest's result gets saved), so this endpoint has no
    DB side effects of its own."""
    material_type: str  # konspekt, lektsiya, test, or prezentatsiya
    topic: str
    subject: str
    language: str
    level: str
    grade: str
    instruction: str
    content: dict


class GenerateAllResponse(BaseModel):
    konspekt: dict | None = None
    test: dict | None = None
    prezentatsiya: dict | None = None
    lektsiya: dict | None = None
    errors: dict | None = None


class GenerateResponse(BaseModel):
    material_type: str
    content: dict



# ── Admin ─────────────────────────────────────────────────────────────────
# No separate admin login endpoint — an admin authenticates through the
# same POST /auth/login every other user does; these endpoints are gated
# by User.role == "admin" (see auth.py's get_current_admin) rather than a
# parallel credential/token system.

class AdminDashboardStats(BaseModel):
    total_users: int
    total_konspekts: int
    total_tests: int
    total_presentations: int
    total_materials: int


class AdminUserOut(BaseModel):
    id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    role: str
    is_premium: bool = False
    balance_somoni: float = 0
    language: str
    created_at: datetime
    konspekt_count: int
    test_count: int
    presentation_count: int
    # See UserOut.short_id — the lookup key an admin actually uses to find
    # who just paid, instead of the UUID id.
    short_id: str | None = None

    model_config = {"from_attributes": True}


# ── Admin materials browser ─────────────────────────────────────────────
# Lets an admin see (and delete) what's actually been generated across
# EVERY teacher's account, not just per-user counts — the pilot had no way
# to spot-check real output or clean up junk/test material without a
# direct DB query. One row shape covers all 6 material tables (they share
# id/title/subject/grade/owner_id/created_at exactly, see models.py) with
# `type` telling them apart, the same MaterialType strings the rest of the
# app already uses (routers/materials.py's LIST_PATH keys).
class AdminMaterialOut(BaseModel):
    id: str
    type: str
    title: str
    subject: str
    grade: str
    owner_id: str
    owner_name: str
    owner_phone: str | None = None
    created_at: datetime


class AdminMaterialsPage(BaseModel):
    items: list[AdminMaterialOut]
    total: int


class AdminRoleUpdate(BaseModel):
    role: str  # "user" | "admin"


class AdminPremiumUpdate(BaseModel):
    is_premium: bool


class AdminBalanceTopUp(BaseModel):
    """Manual top-up an admin applies after a teacher pays some other way
    (Telegram/WhatsApp/phone contact, then a bank transfer or cash — see
    routers/admin.py's add_balance). ADDS to the existing balance, same
    as app/limits.py deducts per paid generation — never a direct
    "set to X" so two admins crediting the same teacher around the same
    time can't clobber each other's top-up.

    Bounded on both ends. A top-up is typed by hand into a form, so the
    realistic mistakes are a slipped decimal point and a pasted number;
    an unbounded float here means one keystroke can mint an effectively
    infinite balance, and (as a float) a large enough value silently
    loses precision when it becomes an integer count of dirams."""
    amount_somoni: float = Field(gt=0, le=10_000)
    # Why this credit was given — the payment reference, "cash, staff
    # room", whatever the admin can point at later. Recorded in the
    # ledger (models.BalanceTransaction) against the admin who did it.
    reason: str | None = Field(default=None, max_length=255)


class BalanceTransactionOut(BaseModel):
    """One row of the balance ledger — see models.BalanceTransaction."""
    id: str
    kind: str
    amount_somoni: float
    balance_before_somoni: float
    balance_after_somoni: float
    actor_name: str | None = None
    reason: str | None = None
    material_type: str | None = None
    created_at: datetime


# ── Billing ──────────────────────────────────────────────────────────────
# Only a balance to read. Topping up happens through an administrator —
# see routers/billing.py and routers/admin.py's add_balance.

class BalanceOut(BaseModel):
    balance_somoni: float





