"""Configurações da aplicação, lidas de variáveis de ambiente ou do arquivo .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    sql_echo: bool = False

    @property
    def database_url(self) -> URL:
        # URL.create escapa caracteres especiais da senha (ex.: @, :, /)
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


settings = Settings()  # type: ignore[call-arg]  # valores obrigatórios vêm do ambiente
