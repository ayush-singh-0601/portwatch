"""
Application configuration via pydantic-settings.

All settings are loaded from environment variables or a .env file.
Sensible defaults are provided for local development.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """PortWatch application settings.

    Attributes:
        DATABASE_URL: Async PostgreSQL connection string
            (e.g. ``postgresql+asyncpg://user:pass@host:5432/portwatch``).
        AISSTREAM_API_KEY: API key for aisstream.io WebSocket feed.
        MOCK_DATA_MODE: When ``True`` the system will use deterministic
            seed data instead of live AIS feeds.
        APP_ENV: Deployment environment identifier.
        APP_DEBUG: Enable verbose logging and debug endpoints.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    DATABASE_URL: str = "postgresql+asyncpg://portwatch:portwatch@localhost:5432/portwatch"
    AISSTREAM_API_KEY: str = ""
    MOCK_DATA_MODE: bool = True
    APP_ENV: str = "development"
    APP_DEBUG: bool = True


# Singleton instance — import this throughout the application.
settings = Settings()
