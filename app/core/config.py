from typing import List, Union
from pydantic_settings import BaseSettings
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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # JWT Keys for different user types
    ADMIN_SECRET_KEY: str
    ACADEMY_SECRET_KEY: str
    STUDENT_SECRET_KEY: str

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

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

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings() 