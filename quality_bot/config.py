import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def _parse_admin_ids(value: str) -> set[int]:
    if not value:
        return set()
    return {int(x.strip()) for x in value.split(",") if x.strip().isdigit()}

@dataclass(frozen=True)
class Config:
    bot_token: str
    database_url: str
    admin_ids: set[int]

def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    db_url = os.getenv("DATABASE_URL", "").strip()
    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

    if not bot_token:
        raise RuntimeError("BOT_TOKEN is empty")
    if not db_url:
        raise RuntimeError("DATABASE_URL is empty")

    return Config(bot_token=bot_token, database_url=db_url, admin_ids=admin_ids)