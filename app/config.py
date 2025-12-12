from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """アプリケーション設定"""

    database_url: str
    yamareco_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
