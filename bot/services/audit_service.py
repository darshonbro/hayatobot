"""Audit logging service for tracking role assignments, removals, and DM delivery."""

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Service for creating and querying audit log records."""

    @classmethod
    async def log_action(
        cls,
        session: AsyncSession,
        guild_id: int,
        actor_id: int,
        actor_name: str,
        target_id: int,
        target_name: str,
        role_id: int,
        role_name: str,
        action: str,
        dm_status: str,
        dm_failure_reason: Optional[str] = None,
    ) -> AuditLog:
        """Create and persist an audit log record."""
        entry = AuditLog(
            guild_id=guild_id,
            actor_id=actor_id,
            actor_name=actor_name[:100],
            target_id=target_id,
            target_name=target_name[:100],
            role_id=role_id,
            role_name=role_name[:100],
            action=action,
            dm_status=dm_status,
            dm_failure_reason=dm_failure_reason[:500] if dm_failure_reason else None,
        )
        session.add(entry)
        await session.flush()
        logger.info(
            "Audit recorded: guild=%s actor=%s target=%s role=%s action=%s dm_status=%s",
            guild_id,
            actor_id,
            target_id,
            role_id,
            action,
            dm_status,
        )
        return entry

    @classmethod
    async def get_recent_logs(
        cls,
        session: AsyncSession,
        guild_id: int,
        limit: int = 10,
    ) -> List[AuditLog]:
        """Fetch recent audit entries for a guild, capped at requested limit."""
        bounded_limit = max(1, min(limit, 50))
        stmt = (
            select(AuditLog)
            .where(AuditLog.guild_id == guild_id)
            .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
            .limit(bounded_limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_user_logs(
        cls,
        session: AsyncSession,
        guild_id: int,
        user_id: int,
        limit: int = 10,
    ) -> List[AuditLog]:
        """Fetch audit entries affecting a specific member, capped at requested limit."""
        bounded_limit = max(1, min(limit, 50))
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.guild_id == guild_id,
                AuditLog.target_id == user_id,
            )
            .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
            .limit(bounded_limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
