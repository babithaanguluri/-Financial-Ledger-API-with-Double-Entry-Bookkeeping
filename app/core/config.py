
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Financial Ledger API"
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5435/ledger_db",
        env="DATABASE_URL"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
