"""
Centralized app configuration.

Every setting the app needs (API keys, connection strings) is declared
once here, typed, and imported everywhere else as `settings`.

We also call load_dotenv() so third-party libraries that read
os.environ directly (like litellm, for Groq auth) can see the same
values without us wiring them manually.
"""

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    groq_api_key: str = ""
    groq_model: str = "groq/llama-3.3-70b-versatile"

    pinecone_api_key: str = ""
    pinecone_index_name: str = "compliance-agent"

    redis_url: str = "redis://localhost:6379/0"


settings = Settings()
