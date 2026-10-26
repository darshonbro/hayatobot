"""Unit tests for bot initialization, extension loading, and configuration."""

from unittest.mock import AsyncMock, patch
import pytest

from bot.config import Config, DEFAULT_DM_TEMPLATE, normalize_database_url
from bot.main import INITIAL_EXTENSIONS, HayatoBot


def test_normalize_database_url():
    """Ensure database URL scheme normalization works for Postgres and SQLite."""
    assert normalize_database_url("postgres://user:pass@host/db") == "postgresql+asyncpg://user:pass@host/db"
    assert normalize_database_url("postgresql://user:pass@host/db") == "postgresql+asyncpg://user:pass@host/db"
    assert normalize_database_url("sqlite:///bot.db") == "sqlite+aiosqlite:///bot.db"
    assert normalize_database_url("") == "sqlite+aiosqlite:///bot.db"


@pytest.mark.asyncio
async def test_bot_setup_and_extensions_loading():
    """Ensure all declared cogs load cleanly into HayatoBot without syntax/runtime issues."""
    config = Config(
        token="MOCK_TOKEN",
        database_url="sqlite+aiosqlite:///:memory:",
        dev_guild_id=123456789,
        log_level="INFO",
        enable_web=False,
    )
    bot = HayatoBot(config)

    # Mock database creation and tree sync
    bot.db.create_tables = AsyncMock()
    bot.tree.sync = AsyncMock(return_value=[])

    with patch.object(bot.tree, "copy_global_to"):
        await bot.setup_hook()

    # Verify all initial extensions were loaded
    for ext in INITIAL_EXTENSIONS:
        assert ext in bot.extensions

    # Verify database tables were requested
    bot.db.create_tables.assert_awaited_once()

    await bot.db.close()
