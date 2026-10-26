"""Unit tests for permission, hierarchy, and role validation checks."""

from unittest.mock import MagicMock
import pytest
from bot.checks import (
    BotHierarchyError,
    BotMissingPermissionsError,
    DefaultRoleError,
    InvalidRoleIDError,
    ManagedRoleError,
    UserHierarchyError,
    UserMissingPermissionsError,
    parse_and_validate_role_id,
    validate_bot_permissions,
    validate_hierarchy,
    validate_role_eligibility,
    validate_user_permissions,
)


def test_parse_and_validate_role_id():
    """Test snowflake parsing across raw numbers, whitespace, and role mentions."""
    assert parse_and_validate_role_id("123456789012345678") == 123456789012345678
    assert parse_and_validate_role_id("  987654321  ") == 987654321
    assert parse_and_validate_role_id("<@&123456789012345678>") == 123456789012345678

    with pytest.raises(InvalidRoleIDError):
        parse_and_validate_role_id("not-a-number")

    with pytest.raises(InvalidRoleIDError):
        parse_and_validate_role_id("-12345")


def test_validate_user_permissions(mock_invoker_admin, mock_guild):
    """Test user permission checks."""
    # Invoker with manage_roles succeeds
    validate_user_permissions(mock_invoker_admin)

    # Server owner bypasses permission requirements
    owner_invoker = MagicMock()
    owner_invoker.id = mock_guild.owner_id
    owner_invoker.guild = mock_guild
    owner_invoker.guild_permissions.manage_roles = False
    owner_invoker.guild_permissions.administrator = False
    validate_user_permissions(owner_invoker)

    # Regular user fails
    peon = MagicMock()
    peon.id = 777777777
    peon.guild = mock_guild
    peon.guild_permissions.manage_roles = False
    peon.guild_permissions.administrator = False
    with pytest.raises(UserMissingPermissionsError):
        validate_user_permissions(peon)


def test_validate_bot_permissions(mock_bot_member):
    """Test bot permission check."""
    validate_bot_permissions(mock_bot_member)

    mock_bot_member.guild_permissions.manage_roles = False
    mock_bot_member.guild_permissions.administrator = False
    with pytest.raises(BotMissingPermissionsError):
        validate_bot_permissions(mock_bot_member)


def test_validate_role_eligibility(mock_guild, mock_role):
    """Ensure @everyone and managed roles are blocked."""
    validate_role_eligibility(mock_role)

    # Test @everyone
    mock_role.is_default.return_value = True
    with pytest.raises(DefaultRoleError):
        validate_role_eligibility(mock_role)

    mock_role.is_default.return_value = False
    mock_role.id = mock_guild.id  # @everyone ID matches guild ID
    with pytest.raises(DefaultRoleError):
        validate_role_eligibility(mock_role)

    # Test managed role
    mock_role.id = 555555555
    mock_role.managed = True
    with pytest.raises(ManagedRoleError):
        validate_role_eligibility(mock_role)


def test_validate_hierarchy(mock_invoker_admin, mock_bot_member, mock_role, mock_guild):
    """Test hierarchy checks for both bot and invoking user."""
    # Normal pass: Bot pos 100 > Invoker pos 50 > Role pos 10
    mock_role.position = 10
    validate_hierarchy(mock_invoker_admin, mock_bot_member, mock_role)

    # Bot top role <= target role fails
    mock_bot_member.top_role.position = 5
    with pytest.raises(BotHierarchyError):
        validate_hierarchy(mock_invoker_admin, mock_bot_member, mock_role)

    # Restore bot role
    mock_bot_member.top_role.position = 100

    # Invoker top role <= target role fails
    mock_invoker_admin.top_role.position = 8
    with pytest.raises(UserHierarchyError):
        validate_hierarchy(mock_invoker_admin, mock_bot_member, mock_role)

    # Server owner bypasses user hierarchy check
    owner_invoker = MagicMock()
    owner_invoker.id = mock_guild.owner_id
    owner_invoker.guild = mock_guild
    owner_invoker.top_role.position = 2  # Lower than target role position 10
    # Does not raise UserHierarchyError
    validate_hierarchy(owner_invoker, mock_bot_member, mock_role)
