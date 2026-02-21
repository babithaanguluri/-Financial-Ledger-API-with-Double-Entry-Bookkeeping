
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Financial Ledger API"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5435/ledger_db"

    class Config:
        case_sensitive = True

settings = Settings()
