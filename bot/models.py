"""SQLAlchemy 2.x Asynchronous Database Models for Hayato On Fire."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bot.config import DEFAULT_DM_TEMPLATE


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


class GuildConfig(Base):
    """Configuration per Discord guild/server."""

    __tablename__ = "guild_configs"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dm_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=DEFAULT_DM_TEMPLATE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<GuildConfig guild_id={self.guild_id}>"


class RoleDescription(Base):
    """Role-specific descriptions for DM templates."""

    __tablename__ = "role_descriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("guild_id", "role_id", name="uq_guild_role_desc"),
    )

    def __repr__(self) -> str:
        return f"<RoleDescription guild_id={self.guild_id} role_id={self.role_id}>"


class AuditLog(Base):
    """Audit log records for role assignments and DM statuses."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    actor_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    actor_name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    target_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    role_name: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    dm_status: Mapped[str] = mapped_column(String(50), nullable=False)
    dm_failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} guild_id={self.guild_id} "
            f"action={self.action} target_id={self.target_id} role_id={self.role_id}>"
        )
