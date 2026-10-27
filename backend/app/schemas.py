import re
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator



_PHONE_RE = re.compile(r"^\+992\d{9}$")


class _NormalizedPhone(BaseModel):

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
    phone: str
    password: str
    device_token: str | None = None


class LoginVerifyRequest(_NormalizedPhone):
    phone: str
    code: str
    remember_device: bool = True


class EmailRegister(BaseModel):
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
    credential: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserOut"
    device_token: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class QrApproveRequest(BaseModel):
    session_id: str


class LogoutRequest(BaseModel):
    refresh_token: str


class SessionOut(BaseModel):
    id: str
    user_agent: str | None
    login_at: datetime

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    phone_verified: bool = False
    is_premium: bool = False
    balance_somoni: float = 0
    avatar_url: str | None = None
    language: str = "Русский"
    role: str = "user"
    created_at: datetime
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



class GameAttemptCreate(BaseModel):
    mode: str
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



class DashboardStats(BaseModel):
    konspekt_count: int
    test_count: int
    presentation_count: int
    lecture_count: int = 0
    practical_count: int = 0
    game_count: int = 0



class GenerateRequest(BaseModel):
    material_type: str
    topic: str
    subject: str
    language: str
    level: str
    grade: str
    slide_count: int | None = None
    question_count: int | None = None
    test_type: str | None = None
    include_homework: bool = True
    include_fun_facts: bool = True
    include_assessment: bool = True
    template: str | None = None
    source_text: str | None = None


class GenerateKonspektStreamRequest(BaseModel):
    topic: str
    subject: str
    language: str
    level: str
    grade: str
    include_homework: bool = True
    include_fun_facts: bool = True
    include_assessment: bool = True
    generation_mode: str = "ai"
    source_text: str | None = None
    template: str | None = None


class GenerateAllRequest(BaseModel):
    topic: str
    subject: str
    language: str
    level: str
    grade: str
    slide_count: int | None = 10
    question_count: int | None = 10
    test_type: str | None = None
    types: list[str] | None = None


class BookGenerateRequest(GenerateAllRequest):
    source_id: str
    scope: str = "all"
    chapter_index: int | None = None
    page_start: int | None = None
    page_end: int | None = None


class GenerationQuoteRequest(BaseModel):
    types: list[str]


class GenerationQuoteItem(BaseModel):
    material_type: str
    was_free: bool
    price_dirams: int


class GenerationQuoteOut(BaseModel):
    count: int
    free_count: int
    paid_count: int
    unit_price_dirams: int
    required_dirams: int
    balance_dirams: int
    affordable: bool
    items: list[GenerationQuoteItem]


class RegenerateItemRequest(BaseModel):
    material_type: str
    topic: str
    subject: str
    language: str
    level: str
    grade: str
    item_index: int = 0
    existing_items: list[dict] = []
    section: str | None = None
    existing_content: dict = {}


class RetryLessonImageRequest(BaseModel):
    index: int = 0


class RegenerateGameRequest(BaseModel):
    language: str = "Русский"
    level: str = "Средний"


class QuizSetRequest(BaseModel):
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
    material_type: str
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
    short_id: str | None = None

    model_config = {"from_attributes": True}


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
    role: str


class AdminPremiumUpdate(BaseModel):
    is_premium: bool


class AdminBalanceTopUp(BaseModel):
    amount_somoni: float = Field(gt=0, le=10_000)
    reason: str | None = Field(default=None, max_length=255)


class AdminSmsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=480)


class AdminBulkSmsRequest(BaseModel):
    user_ids: list[str] = Field(min_length=1, max_length=500)
    text: str = Field(min_length=1, max_length=480)


class AdminSmsResult(BaseModel):
    user_id: str
    full_name: str
    phone: str | None
    sent: bool
    error: str | None = None
    dry_run: bool = False


class AdminSmsReport(BaseModel):
    sent: int
    failed: int
    dry_run: bool = False
    results: list[AdminSmsResult]


class BalanceTransactionOut(BaseModel):
    id: str
    kind: str
    amount_somoni: float
    balance_before_somoni: float
    balance_after_somoni: float
    actor_name: str | None = None
    reason: str | None = None
    material_type: str | None = None
    created_at: datetime
    # Populated only by the global ledger browser (GET /admin/balance-
    # transactions) - the existing per-user balance-history endpoint
    # leaves these unset since the user is already implied by its URL.
    user_id: str | None = None
    user_name: str | None = None



class BalanceOut(BaseModel):
    balance_somoni: float







class TelegramLinkOut(BaseModel):
    deep_link: str
    app_link: str
    start_command: str
    bot_username: str
    expires_at: datetime
    expires_in_seconds: int


class TelegramLinkCodeOut(BaseModel):
    code: str
    bot_username: str
    expires_at: datetime
    expires_in_seconds: int


class TelegramLinkStatusOut(BaseModel):
    linked: bool
    bot_configured: bool
    bot_username: str
    linked_at: datetime | None = None


class PayInstructionsOut(BaseModel):
    text: str


class PayInstructionsUpdate(BaseModel):
    text: str = Field(max_length=2000)


class TopupRequestOut(BaseModel):
    id: str
    requested_somoni: float
    note: str | None = None
    receipt_url: str | None = None
    status: str
    credited_somoni: float | None = None
    admin_note: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None


class AdminTopupRequestOut(TopupRequestOut):
    user_id: str
    user_name: str
    user_phone: str | None = None
    user_short_id: str | None = None
    user_balance_somoni: float = 0


class AdminTopupApprove(BaseModel):
    credited_somoni: float = Field(gt=0, le=10_000)
    note: str | None = Field(default=None, max_length=255)


class AdminTopupReject(BaseModel):
    note: str | None = Field(default=None, max_length=255)


class AdminRosterEntry(BaseModel):
    user_id: str
    full_name: str
    short_id: str | None = None
    admin_tier: str | None = None  # NULL reads as "super" — see admin_roles.py


class UnreviewedTelegramAdminOut(BaseModel):
    """A telegram_admins grant whose Dastyor account is not (yet) a web
    admin — surfaced for a human to promote or dismiss, never acted on
    automatically."""
    grant_id: str
    telegram_user_id: int | None = None
    user_id: str | None = None
    full_name: str | None = None
    short_id: str | None = None
    added_at: datetime


class AdminRosterOut(BaseModel):
    admins: list[AdminRosterEntry]
    unreviewed: list[UnreviewedTelegramAdminOut]


class AdminPromoteRequest(BaseModel):
    action: str  # "promote" | "demote" | "ignore"
    admin_tier: str | None = None  # required when action == "promote"


class CardOut(BaseModel):
    id: str
    bank_name: str
    holder_name: str
    card_number_masked: str
    currency: str
    note: str | None = None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class CardDetailOut(CardOut):
    card_number: str  # decrypted - only this endpoint ever returns it


class CardCreate(BaseModel):
    bank_name: str = Field(min_length=1, max_length=120)
    holder_name: str = Field(min_length=1, max_length=120)
    card_number: str = Field(min_length=4, max_length=64)
    currency: str = Field(default="TJS", max_length=10)
    note: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    sort_order: int = 0


class CardUpdate(BaseModel):
    bank_name: str | None = Field(default=None, max_length=120)
    holder_name: str | None = Field(default=None, max_length=120)
    card_number: str | None = Field(default=None, min_length=4, max_length=64)
    currency: str | None = Field(default=None, max_length=10)
    note: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    sort_order: int | None = None


class ExpenseOut(BaseModel):
    id: str
    category: str
    amount_somoni: float
    note: str | None = None
    spent_at: datetime
    created_by: str | None = None
    created_at: datetime


class ExpenseCreate(BaseModel):
    category: str = Field(min_length=1, max_length=60)
    amount_somoni: float = Field(gt=0)
    note: str | None = Field(default=None, max_length=255)
    spent_at: datetime


class ExpenseUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=60)
    amount_somoni: float | None = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=255)
    spent_at: datetime | None = None


class AdminPaymentRequestOut(BaseModel):
    """The Telegram-side payment queue, as the CRM's unified Payments
    page needs to see it — same underlying payment_requests row the
    bot's own /pending queue reads, just with the user identified by
    name instead of chat id.

    receipt_url is deliberately absent: the bot never saves a Telegram
    receipt to local disk (see telegram/bot.py — only receipt_file_id,
    the OCR having already run on the in-memory bytes), so there is
    nothing under /uploads/... to link to yet. Serving that image needs
    a small proxy through the Bot API, which is Stage 8's job alongside
    the receipt lightbox component that would actually display it.
    """
    id: str
    public_code: str
    user_id: str
    user_name: str
    user_short_id: str | None = None
    requested_somoni: float
    status: str
    receipt_file_id: str | None = None
    receipt_mime: str | None = None
    ocr_amount_somoni: float | None = None
    ocr_sender: str | None = None
    ocr_recipient: str | None = None
    ocr_reference: str | None = None
    ocr_confidence: int = 0
    ocr_warnings: str | None = None
    credited_somoni: float | None = None
    decision_note: str | None = None
    created_at: datetime
    updated_at: datetime


class AdminPaymentDecision(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class AdminPaymentApprove(BaseModel):
    # Both set together or neither - see telegram.service.approve_payment,
    # which refuses an override with no reason attached.
    amount_override_somoni: float | None = Field(default=None, gt=0)
    correction_reason: str | None = Field(default=None, max_length=500)


class AuditLogEntryOut(BaseModel):
    id: str
    subject: str  # payment_request_id column, reused as a generic subject key
    event: str
    actor_kind: str
    actor_telegram_id: int | None = None
    actor_user_id: str | None = None
    actor_name: str | None = None
    detail: str | None = None  # raw JSON string; frontend parses as needed
    created_at: datetime
