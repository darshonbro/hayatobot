"""Security, permission, and hierarchy validation for Hayato On Fire."""

import discord
from discord import app_commands


class RoleManagementError(Exception):
    """Base exception for role management failures."""
    pass


class InvalidRoleIDError(RoleManagementError):
    """Raised when a provided Role ID is malformed or invalid."""
    pass


class RoleNotFoundError(RoleManagementError):
    """Raised when the specified role does not exist in the guild."""
    pass


class DefaultRoleError(RoleManagementError):
    """Raised when an operation is attempted on the @everyone role."""
    pass


class ManagedRoleError(RoleManagementError):
    """Raised when an operation is attempted on an integration-managed role."""
    pass


class BotHierarchyError(RoleManagementError):
    """Raised when the bot's top role is lower than or equal to the target role."""
    pass


class UserHierarchyError(RoleManagementError):
    """Raised when the invoking user's top role is lower than or equal to the target role."""
    pass


class BotMissingPermissionsError(RoleManagementError):
    """Raised when the bot lacks the Manage Roles permission."""
    pass


class UserMissingPermissionsError(RoleManagementError):
    """Raised when the invoking user lacks the Manage Roles permission."""
    pass


class DuplicateRoleError(RoleManagementError):
    """Raised when assigning a role the member already possesses."""
    pass


class MemberLacksRoleError(RoleManagementError):
    """Raised when removing a role the member does not possess."""
    pass


def parse_and_validate_role_id(role_id_raw: str) -> int:
    """Parse a role ID string, stripping whitespace or mention format (<@&id>)."""
    clean_id = role_id_raw.strip()
    if clean_id.startswith("<@&") and clean_id.endswith(">"):
        clean_id = clean_id[3:-1]

    if not clean_id.isdigit():
        raise InvalidRoleIDError(
            f"Invalid Role ID `{role_id_raw}`. A Role ID must be a numeric Discord snowflake."
        )

    role_id = int(clean_id)
    if role_id <= 0:
        raise InvalidRoleIDError("Role ID must be a positive integer.")

    return role_id


def validate_user_permissions(member: discord.Member) -> None:
    """Validate that the user is the guild owner or has Manage Roles/Administrator."""
    if member.guild.owner_id == member.id:
        return

    permissions = member.guild_permissions
    if not (permissions.manage_roles or permissions.administrator):
        raise UserMissingPermissionsError(
            "You require the **Manage Roles** permission to execute this command."
        )


def validate_bot_permissions(bot_member: discord.Member) -> None:
    """Validate that the bot possesses the Manage Roles permission."""
    permissions = bot_member.guild_permissions
    if not (permissions.manage_roles or permissions.administrator):
        raise BotMissingPermissionsError(
            "I require the **Manage Roles** permission in this server to modify roles."
        )


def validate_role_eligibility(role: discord.Role) -> None:
    """Ensure the target role is not @everyone or an integration-managed role."""
    if role.is_default() or role.id == role.guild.id:
        raise DefaultRoleError("The `@everyone` role cannot be assigned or removed.")

    if role.managed:
        raise ManagedRoleError(
            f"The role `{role.name}` is managed by an integration, bot, or booster system and cannot be assigned manually."
        )


def validate_hierarchy(
    invoker: discord.Member,
    bot_member: discord.Member,
    target_role: discord.Role,
) -> None:
    """Validate that both the invoker and the bot have sufficient hierarchy over the target role."""
    bot_top_pos = getattr(bot_member.top_role, "position", 0)
    target_pos = getattr(target_role, "position", 0)

    # 1. Bot hierarchy check
    if bot_top_pos <= target_pos:
        raise BotHierarchyError(
            f"My highest role (`{bot_member.top_role.name}`) is not positioned higher than `{target_role.name}`. "
            "Please move my role above the target role in Server Settings > Roles."
        )

    # 2. Invoker hierarchy check (guild owner bypasses hierarchy)
    if invoker.guild.owner_id != invoker.id:
        invoker_top_pos = getattr(invoker.top_role, "position", 0)
        if invoker_top_pos <= target_pos:
            raise UserHierarchyError(
                f"Your highest role (`{invoker.top_role.name}`) is not positioned higher than `{target_role.name}`."
            )


def has_manage_roles_permission():
    """Slash command check ensuring the user has Manage Roles or is Server Owner."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False
        validate_user_permissions(interaction.user)
        return True

    return app_commands.check(predicate)
