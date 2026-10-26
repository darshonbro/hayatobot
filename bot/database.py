"""Asynchronous Database connection and session management using SQLAlchemy 2.x."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages the lifecycle of the asynchronous database engine and sessions."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    def initialize(self) -> None:
        """Create the async engine and sessionmaker."""
        is_sqlite = "sqlite" in self.database_url

        engine_kwargs = {
            "echo": False,
            "future": True,
        }

        if is_sqlite:
            # Needed for SQLite multithreaded / async safety
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        else:
            # PostgreSQL connection pool settings for production
            engine_kwargs["pool_size"] = 10
            engine_kwargs["max_overflow"] = 20
            engine_kwargs["pool_pre_ping"] = True

        self._engine = create_async_engine(self.database_url, **engine_kwargs)
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        logger.info("Database engine initialized with driver: %s", self.database_url.split("://")[0])

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("Database engine is not initialized. Call initialize() first.")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("Session factory is not initialized. Call initialize() first.")
        return self._session_factory

    async def create_tables(self) -> None:
        """Create tables if they do not exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema verified and initialized.")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide an asynchronous transactional session scope."""
        session: AsyncSession = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def close(self) -> None:
        """Dispose of the database engine on shutdown."""
        if self._engine is not None:
            await self._engine.dispose()
            logger.info("Database engine disposed cleanly.")
