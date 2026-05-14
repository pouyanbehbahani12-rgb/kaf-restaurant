from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str = ""
    database_url: str = "sqlite:///./kaf.db"
    weekly_generation_cron: str = "0 9 * * MON"
    upload_dir: str = "./uploads"
    debug: bool = False

    @property
    def sqlalchemy_database_url(self) -> str:
        # Railway provides postgresql:// but SQLAlchemy needs postgresql+psycopg2://
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url


settings = Settings()
