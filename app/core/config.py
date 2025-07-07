from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, validator
import json


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "SAYAN Educational Platform"
    PROJECT_NAME: str = "SAYAN API"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # شهر كامل (30 يوم × 24 ساعة × 60 دقيقة)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # JWT Keys for different user types
    ADMIN_SECRET_KEY: str
    ACADEMY_SECRET_KEY: str
    STUDENT_SECRET_KEY: str

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # Email Settings - New Mail Configuration
    MAIL_MAILER: str = "smtp"
    MAIL_HOST: str = ""
    MAIL_PORT: int = 465
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_ENCRYPTION: str = "ssl"
    MAIL_FROM_ADDRESS: str = ""
    MAIL_FROM_NAME: str = "SAYAN Platform"
    
    # Legacy Email Settings - SMTP Configuration (for compatibility)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    EMAIL_FROM: str = ""
    EMAIL_FROM_NAME: str = "SAYAN Platform"
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    OTP_RATE_LIMIT_PER_HOUR: int = 3
    PASSWORD_RESET_RATE_LIMIT_PER_HOUR: int = 3
    
    # Security Settings
    BCRYPT_ROUNDS: int = 12
    OTP_EXPIRY_MINUTES: int = 15
    PASSWORD_RESET_EXPIRY_MINUTES: int = 15

    # Platform Settings
    PLATFORM_FEE_PERCENTAGE: float = 10.0  # رسوم المنصة كنسبة مئوية

    # Payment Gateway Settings - Moyasar
    MOYASAR_API_KEY: str = ""
    MOYASAR_WEBHOOK_SECRET: str = ""
    MOYASAR_ENVIRONMENT: str = "test"  # test or live
    MOYASAR_PUBLIC_KEY: str = ""

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # pydantic-settings (v2) يسمح بتخصيص مصدر الإعدادات.
    # نحدد ملف env الافتراضي، ونمنع مصادر OS Environment variables.

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """استخدم .env فقط (مع init_settings) وتجاهل env_settings."""
        return (
            init_settings,    # kwargs أثناء التهيئة (إن وُجدت)
            dotenv_settings,  # قيم من ملف .env
            file_secret_settings,  # secrets/* إذا استُخدمت
            # لا نُرجع env_settings ⇒ يتم تجاهل متغيرات البيئة
        )


settings = Settings() 