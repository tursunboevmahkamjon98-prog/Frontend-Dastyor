from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    TRUSTED_DEVICE_EXPIRE_DAYS: int = 90
    AI_API_KEY: str
    AI_API_KEY_2: str = ""
    AI_API_KEY_3: str = ""
    AI_API_KEY_4: str = ""
    AI_API_KEY_5: str = ""
    AI_MODEL: str = "gpt-oss-120b"
    AI_BASE_URL: str = "https://api.cerebras.ai/v1"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "Dastyor"

    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    ADMIN_NAME: str = "Admin"
    ADMIN_PHONE: str = ""

    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    ROBITA_LOGIN: str = ""
    ROBITA_PASSWORD: str = ""
    ROBITA_SENDER: str = ""

    OTP_BYPASS_PHONE: str = ""

    GOOGLE_CLIENT_ID: str = ""

    CORS_ORIGINS: str = "http://localhost:3000"

    DOCS_ENABLED: bool = False

    MAX_FORGOT_ATTEMPTS: int = 5
    MAX_VERIFY_ATTEMPTS: int = 10
    MAX_LOGIN_ATTEMPTS: int = 10
    MAX_REGISTER_CODE_ATTEMPTS: int = 5
    RATE_WINDOW: int = 300

    MAX_SMS_PER_IP_BURST: int = 40
    RATE_WINDOW_IP_BURST: int = 10
    MAX_SMS_PER_IP: int = 150
    MAX_REGISTER_PER_IP: int = 60
    RATE_WINDOW_IP: int = 3600

    MAX_SMS_PER_DAY: int = 500

    SMS_DRY_RUN: bool = False

    MAX_REQUESTS_PER_MINUTE: int = 900

    GAME_ACCESS_USER_IDS: str = ""

    MAX_GENERATIONS_PER_HOUR: int = 40
    MAX_AI_EDITS_PER_HOUR: int = 60

    FREE_GENERATIONS_PER_TYPE: int = 10

    MAX_CONCURRENT_AI_CALLS: int = 8

    MAX_CONCURRENT_PPTX_CONVERSIONS: int = 1
    AI_QUEUE_TIMEOUT_SECONDS: int = 120

    MAX_REQUEST_BODY_BYTES: int = 20 * 1024 * 1024

    MAX_ADMIN_LOGIN_ATTEMPTS: int = 5
    ADMIN_LOCKOUT_SECONDS: int = 900

    ADMIN_MIN_PASSWORD_LENGTH: int = 10

    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_RECYCLE: int = 1800
    DB_POOL_TIMEOUT: int = 30

    MAX_AVATAR_SIZE: int = 5 * 1024 * 1024
    ALLOWED_AVATAR_EXT: str = ".jpg,.jpeg,.png,.webp"

    MAX_SOURCE_FILE_SIZE: int = 15 * 1024 * 1024
    ALLOWED_SOURCE_EXT: str = ".pdf,.docx,.txt"

    MAX_MATERIALS_PER_DAY: int = 100

    APP_LATEST_BUILD: int = 1
    APP_LATEST_VERSION: str = "1.0.0"
    APP_MIN_BUILD: int = 0
    APP_APK_URL: str = "/dastyor.apk"
    APP_UPDATE_NOTES: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
