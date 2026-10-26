"""Test fixtures, database setup, and Discord object mocks."""

from unittest.mock import AsyncMock, MagicMock
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.models import Base


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory SQLite database session for unit testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def mock_guild():
    """Mock Discord Guild."""
    guild = MagicMock()
    guild.id = 987654321
    guild.name = "Hayato Arena"
    guild.owner_id = 111111111
    return guild


@pytest.fixture
def mock_role(mock_guild):
    """Mock Discord Role."""
    role = MagicMock()
    role.id = 555555555
    role.name = "Champion"
    role.guild = mock_guild
    role.managed = False
    role.is_default.return_value = False
    role.position = 10
    return role


@pytest.fixture
def mock_target_member(mock_guild):
    """Mock target Discord Member."""
    member = MagicMock()
    member.id = 222222222
    member.display_name = "SpeedyGamer"
    member.mention = "<@222222222>"
    member.guild = mock_guild
    member.roles = []
    member.send = AsyncMock()
    member.add_roles = AsyncMock()
    member.remove_roles = AsyncMock()
    return member


@pytest.fixture
def mock_invoker_admin(mock_guild):
    """Mock invoker with administrative permissions."""
    invoker = MagicMock()
    invoker.id = 333333333
    invoker.display_name = "AdminUser"
    invoker.guild = mock_guild
    invoker.guild_permissions.manage_roles = True
    invoker.guild_permissions.administrator = False

    top_role = MagicMock()
    top_role.position = 50
    top_role.name = "Moderator"
    invoker.top_role = top_role
    return invoker


@pytest.fixture
def mock_bot_member(mock_guild):
    """Mock Bot Member."""
    bot_member = MagicMock()
    bot_member.id = 999999999
    bot_member.display_name = "Hayato On Fire"
    bot_member.guild = mock_guild
    bot_member.guild_permissions.manage_roles = True
    bot_member.guild_permissions.administrator = False

    top_role = MagicMock()
    top_role.position = 100
    top_role.name = "Hayato On Fire Role"
    bot_member.top_role = top_role
    return bot_member
