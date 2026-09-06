from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: SecretStr
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5.6-luna"
    database_url: str = "sqlite+aiosqlite:///./pantry.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
