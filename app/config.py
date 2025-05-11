# app/config.py

from pydantic import BaseSettings, Field
from urllib.parse import quote_plus


class Settings(BaseSettings):
    # Application
    app_name: str = "Naos IP Tool"
    secret_key: str

    # MySQL / Database
    mysql_host: str
    mysql_port: int = 3306
    mysql_db: str
    mysql_user: str
    mysql_pass: str

    # Cookie / Auth
    cookie_name: str = Field("access_token", description="Name of the auth cookie")
    cookie_secure: bool = Field(False, description="Set True when serving over HTTPS")
    cookie_max_age: int = Field(60 * 60 * 24, description="Cookie validity in seconds")
    cookie_domain: str | None = Field(None, description="Domain for the auth cookie")

    @property
    def db_uri(self) -> str:
        """
        Constructs a SQLAlchemy URI for MySQL using aiomysql.
        The password is URL-encoded to handle special characters.
        """
        pwd = quote_plus(self.mysql_pass)
        return (
            f"mysql+aiomysql://{self.mysql_user}:{pwd}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instantiate as a module-level singleton
settings = Settings()
