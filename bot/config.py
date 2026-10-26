"""Configuration settings for Hayato On Fire bot."""

import logging
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

DEFAULT_DM_TEMPLATE = (
    "Congratulations, {user}!\n\n"
    "You have received the {role} role.\n\n"
    "{role_description}\n\n"
    "Enjoy your new permissions!"
)


def normalize_database_url(url: str) -> str:
    """Normalize database URL for SQLAlchemy 2.x async drivers."""
    if not url:
        return "sqlite+aiosqlite:///bot.db"

    # Convert Heroku/Supabase/standard postgres URLs to asyncpg
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Convert standard sqlite URLs to aiosqlite
    if url.startswith("sqlite://") and not url.startswith("sqlite+"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)

    return url


@dataclass(frozen=True)
class Config:
    """Runtime configuration container."""

    token: str
    database_url: str
    dev_guild_id: Optional[int]
    log_level: str
    bot_name: str = "Hayato On Fire"
    default_dm_template: str = DEFAULT_DM_TEMPLATE
    enable_web: bool = True
    web_host: str = "0.0.0.0"
    web_port: int = 8080


def load_config() -> Config:
    """Load configuration from environment variables."""
    token = os.getenv("DISCORD_TOKEN", "").strip()

    raw_db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot.db").strip()
    database_url = normalize_database_url(raw_db_url)

    dev_guild_raw = os.getenv("DEV_GUILD_ID", "").strip()
    dev_guild_id: Optional[int] = None
    if dev_guild_raw and dev_guild_raw.isdigit():
        dev_guild_id = int(dev_guild_raw)

    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    enable_web_raw = os.getenv("ENABLE_WEB_PORTAL", "true").strip().lower()
    enable_web = enable_web_raw not in ("0", "false", "no", "off")

    web_host = os.getenv("WEB_HOST", "0.0.0.0").strip()
    web_port_raw = os.getenv("PORT", os.getenv("WEB_PORT", "8080")).strip()
    web_port = int(web_port_raw) if web_port_raw.isdigit() else 8080

    return Config(
        token=token,
        database_url=database_url,
        dev_guild_id=dev_guild_id,
        log_level=log_level,
        enable_web=enable_web,
        web_host=web_host,
        web_port=web_port,
    )


def setup_logging(log_level_name: str = "INFO") -> logging.Logger:
    """Set up structured logging."""
    level = getattr(logging, log_level_name.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear pre-existing handlers to prevent duplicated logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress excessive noise from external libraries
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)
    logging.getLogger("discord.client").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger = logging.getLogger("hayato_bot")
    logger.setLevel(level)
    return logger
