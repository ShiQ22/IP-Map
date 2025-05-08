from pydantic import BaseSettings
from urllib.parse import quote_plus            # ← new import


class Settings(BaseSettings):
    app_name: str = "Naos IP Tool"
    secret_key: str

    mysql_host: str
    mysql_port: int = 3306
    mysql_db:   str
    mysql_user: str
    mysql_pass: str

    @property
    def db_uri(self) -> str:                    # ← updated
        pwd = quote_plus(self.mysql_pass)       # encodes @, %, etc.
        return (
            f"mysql+aiomysql://{self.mysql_user}:{pwd}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
