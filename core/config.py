from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    telegram_bot_token: str
    sec_user_agent: str
    groq_api_key: str

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
 
 
settings = Settings()