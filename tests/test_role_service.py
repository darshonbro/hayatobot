"""Unit tests for RoleService: assignment, duplicate prevention, DM dispatch, and removal."""

import discord
import pytest
from unittest.mock import AsyncMock, MagicMock

from bot.checks import MemberLacksRoleError, RoleNotFoundError
from bot.services.role_service import RoleService


@pytest.mark.asyncio
async def test_successful_role_assignment(
    db_session,
    mock_invoker_admin,
    mock_bot_member,
    mock_target_member,
    mock_role,
    mock_guild,
):
    """Test full successful role assignment and DM dispatch."""
    mock_guild.get_role.return_value = mock_role

    result = await RoleService.assign_role(
        session=db_session,
        invoker=mock_invoker_admin,
        bot_member=mock_bot_member,
        target_member=mock_target_member,
        role_id_raw=str(mock_role.id),
    )

    assert result.success is True
    assert result.is_duplicate is False
    assert result.dm_status == "SENT"
    assert result.role == mock_role

    # Discord member role addition called
    mock_target_member.add_roles.assert_awaited_once()

    # Discord member DM send called
    mock_target_member.send.assert_awaited_once()

    # Audit log entry created
    assert result.audit_entry is not None
    assert result.audit_entry.action == "ROLE_ASSIGN"
    assert result.audit_entry.dm_status == "SENT"


@pytest.mark.asyncio
async def test_duplicate_role_assignment_prevention(
    db_session,
    mock_invoker_admin,
    mock_bot_member,
    mock_target_member,
    mock_role,
    mock_guild,
):
    """Ensure duplicate role assignments are handled gracefully without duplicate DMs."""
    mock_guild.get_role.return_value = mock_role
    # Member already has the role
    mock_target_member.roles = [mock_role]

    result = await RoleService.assign_role(
        session=db_session,
        invoker=mock_invoker_admin,
        bot_member=mock_bot_member,
        target_member=mock_target_member,
        role_id_raw=str(mock_role.id),
    )

    assert result.success is False
    assert result.is_duplicate is True
    assert result.dm_status == "SKIPPED_DUPLICATE"

    # No role addition or DM dispatched
    mock_target_member.add_roles.assert_not_awaited()
    mock_target_member.send.assert_not_awaited()

    # Audit logged with duplicate status
    assert result.audit_entry.action == "ROLE_ASSIGN_DUPLICATE"
    assert result.audit_entry.dm_status == "SKIPPED_DUPLICATE"


@pytest.mark.asyncio
async def test_dm_delivery_failure_preserves_role_assignment(
    db_session,
    mock_invoker_admin,
    mock_bot_member,
    mock_target_member,
    mock_role,
    mock_guild,
):
    """Ensure that if member DMs are closed (Forbidden), the role is still assigned and failure recorded."""
    mock_guild.get_role.return_value = mock_role
    mock_target_member.roles = []
    # Simulate Discord 403 Forbidden (DMs disabled)
    mock_target_member.send = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "Cannot send messages to this user"))

    result = await RoleService.assign_role(
        session=db_session,
        invoker=mock_invoker_admin,
        bot_member=mock_bot_member,
        target_member=mock_target_member,
        role_id_raw=str(mock_role.id),
    )

    # Role assignment was still successful!
    assert result.success is True
    assert result.is_duplicate is False
    mock_target_member.add_roles.assert_awaited_once()

    # DM status indicates failure with reason
    assert result.dm_status == "FAILED"
    assert "disabled" in result.dm_error.lower()
    assert result.audit_entry.dm_status == "FAILED"
    assert result.audit_entry.dm_failure_reason is not None


@pytest.mark.asyncio
async def test_role_removal_flow(
    db_session,
    mock_invoker_admin,
    mock_bot_member,
    mock_target_member,
    mock_role,
    mock_guild,
):
    """Test removing a role that the member possesses."""
    mock_guild.get_role.return_value = mock_role
    mock_target_member.roles = [mock_role]

    result = await RoleService.remove_role(
        session=db_session,
        invoker=mock_invoker_admin,
        bot_member=mock_bot_member,
        target_member=mock_target_member,
        role_id_raw=str(mock_role.id),
    )

    assert result.success is True
    mock_target_member.remove_roles.assert_awaited_once()
    assert result.audit_entry.action == "ROLE_REMOVE"


@pytest.mark.asyncio
async def test_role_removal_fails_if_member_lacks_role(
    db_session,
    mock_invoker_admin,
    mock_bot_member,
    mock_target_member,
    mock_role,
    mock_guild,
):
    """Ensure removing an unpossessed role raises MemberLacksRoleError."""
    mock_guild.get_role.return_value = mock_role
    mock_target_member.roles = []

    with pytest.raises(MemberLacksRoleError):
        await RoleService.remove_role(
            session=db_session,
            invoker=mock_invoker_admin,
            bot_member=mock_bot_member,
            target_member=mock_target_member,
            role_id_raw=str(mock_role.id),
        )


@pytest.mark.asyncio
async def test_assign_nonexistent_role_raises_error(
    db_session,
    mock_invoker_admin,
    mock_bot_member,
    mock_target_member,
    mock_guild,
):
    """Ensure trying to assign a role ID not in guild raises RoleNotFoundError."""
    mock_guild.get_role.return_value = None

    with pytest.raises(RoleNotFoundError):
        await RoleService.assign_role(
            session=db_session,
            invoker=mock_invoker_admin,
            bot_member=mock_bot_member,
            target_member=mock_target_member,
            role_id_raw="999999999999",
        )
