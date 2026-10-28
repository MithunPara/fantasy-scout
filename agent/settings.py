from dotenv import load_dotenv
from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # .env variables do not NEED to have a matching value in Settings
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    LLM_MODEL: str = "groq:openai/gpt-oss-20b"

    LLM_TEMPERATURE: float = 0.0

    LLM_TIMEOUT: float = Field(default=30.0, gt=0)

    LLM_MAX_RETRIES: int = Field(default=2, ge=0)

    groq_api_key = SecretStr

    MAX_MESSAGE_LENGTH: int = Field(default=500, ge=1)

    AGENT_RECURSION_LIMIT: int = Field(default=10, ge=1)

settings = Settings()
