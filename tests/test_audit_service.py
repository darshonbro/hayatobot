"""Unit tests for AuditService persistence, querying, and multi-server isolation."""

import pytest
from bot.services.audit_service import AuditService


@pytest.mark.asyncio
async def test_audit_log_persistence_and_queries(db_session):
    """Test creating audit entries and querying recent logs."""
    guild_id = 12345

    # Log 3 distinct actions
    await AuditService.log_action(
        session=db_session,
        guild_id=guild_id,
        actor_id=1,
        actor_name="ModAlpha",
        target_id=10,
        target_name="UserOne",
        role_id=100,
        role_name="VIP",
        action="ROLE_ASSIGN",
        dm_status="SENT",
    )

    await AuditService.log_action(
        session=db_session,
        guild_id=guild_id,
        actor_id=1,
        actor_name="ModAlpha",
        target_id=20,
        target_name="UserTwo",
        role_id=200,
        role_name="Supporter",
        action="ROLE_ASSIGN",
        dm_status="FAILED",
        dm_failure_reason="DMs disabled",
    )

    await AuditService.log_action(
        session=db_session,
        guild_id=guild_id,
        actor_id=2,
        actor_name="ModBeta",
        target_id=10,
        target_name="UserOne",
        role_id=100,
        role_name="VIP",
        action="ROLE_REMOVE",
        dm_status="N/A",
    )

    # Test get_recent_logs
    recent = await AuditService.get_recent_logs(db_session, guild_id=guild_id, limit=2)
    assert len(recent) == 2
    # Verify order is descending by timestamp (latest first)
    assert recent[0].action == "ROLE_REMOVE"
    assert recent[1].target_name == "UserTwo"

    # Test get_user_logs for UserOne (target_id=10)
    user_one_logs = await AuditService.get_user_logs(db_session, guild_id=guild_id, user_id=10)
    assert len(user_one_logs) == 2
    assert all(log.target_id == 10 for log in user_one_logs)


@pytest.mark.asyncio
async def test_audit_log_server_isolation(db_session):
    """Ensure audit logs for Guild A never leak into queries for Guild B."""
    guild_a = 777
    guild_b = 888

    await AuditService.log_action(
        session=db_session,
        guild_id=guild_a,
        actor_id=1,
        actor_name="ModA",
        target_id=10,
        target_name="TargetA",
        role_id=101,
        role_name="RoleA",
        action="ROLE_ASSIGN",
        dm_status="SENT",
    )

    logs_b = await AuditService.get_recent_logs(db_session, guild_id=guild_b)
    assert len(logs_b) == 0

    logs_a = await AuditService.get_recent_logs(db_session, guild_id=guild_a)
    assert len(logs_a) == 1
    assert logs_a[0].guild_id == guild_a
