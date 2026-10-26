"""Role management service orchestrating assignment, DM dispatch, and audit logging."""

import logging
from dataclasses import dataclass
from typing import Optional

import discord
from sqlalchemy.ext.asyncio import AsyncSession

from bot.checks import (
    DuplicateRoleError,
    MemberLacksRoleError,
    RoleNotFoundError,
    parse_and_validate_role_id,
    validate_bot_permissions,
    validate_hierarchy,
    validate_role_eligibility,
    validate_user_permissions,
)
from bot.models import AuditLog
from bot.services.audit_service import AuditService
from bot.services.template_service import TemplateService

logger = logging.getLogger(__name__)


@dataclass
class RoleAssignmentResult:
    """Result summary of a role assignment operation."""

    success: bool
    role: discord.Role
    target_member: discord.Member
    is_duplicate: bool
    dm_status: str  # "SENT", "FAILED", "SKIPPED_DUPLICATE"
    dm_error: Optional[str]
    rendered_dm: Optional[str]
    audit_entry: Optional[AuditLog]


@dataclass
class RoleRemovalResult:
    """Result summary of a role removal operation."""

    success: bool
    role: discord.Role
    target_member: discord.Member
    audit_entry: Optional[AuditLog]


class RoleService:
    """Service handling Discord role operations, DM delivery, and auditing."""

    @classmethod
    async def assign_role(
        cls,
        session: AsyncSession,
        invoker: discord.Member,
        bot_member: discord.Member,
        target_member: discord.Member,
        role_id_raw: str,
    ) -> RoleAssignmentResult:
        """
        Validate, assign a role, send a personalized DM, and record the action.
        Guarantees that role assignment is preserved even if the DM fails.
        """
        guild = invoker.guild

        # 1. Parse and validate ID format
        role_id = parse_and_validate_role_id(role_id_raw)

        # 2. Check role existence in current guild
        role = guild.get_role(role_id)
        if not role:
            raise RoleNotFoundError(
                f"No role with ID `{role_id}` exists in this server (`{guild.name}`)."
            )

        # 3. Check invoker permissions
        validate_user_permissions(invoker)

        # 4. Check bot permissions
        validate_bot_permissions(bot_member)

        # 5. Role eligibility (not @everyone or managed)
        validate_role_eligibility(role)

        # 6. Role hierarchy check
        validate_hierarchy(invoker=invoker, bot_member=bot_member, target_role=role)

        # 7. Check if member already has the role
        if role in target_member.roles:
            audit = await AuditService.log_action(
                session=session,
                guild_id=guild.id,
                actor_id=invoker.id,
                actor_name=str(invoker),
                target_id=target_member.id,
                target_name=str(target_member),
                role_id=role.id,
                role_name=role.name,
                action="ROLE_ASSIGN_DUPLICATE",
                dm_status="SKIPPED_DUPLICATE",
                dm_failure_reason="Member already possessed the role.",
            )
            return RoleAssignmentResult(
                success=False,
                role=role,
                target_member=target_member,
                is_duplicate=True,
                dm_status="SKIPPED_DUPLICATE",
                dm_error="Member already possessed the role.",
                rendered_dm=None,
                audit_entry=audit,
            )

        # 8. Assign role to target member
        reason = f"Assigned by {invoker} ({invoker.id}) via Hayato On Fire"
        await target_member.add_roles(role, reason=reason)

        # 9. Render DM template
        template = await TemplateService.get_guild_template(session, guild.id)
        role_desc = await TemplateService.get_role_description(session, guild.id, role.id)
        rendered_dm = TemplateService.render(
            template=template,
            member=target_member,
            role=role,
            role_description=role_desc,
        )

        # 10. Send Direct Message to recipient
        dm_status = "SENT"
        dm_error: Optional[str] = None
        try:
            # Enforce allowed_mentions to prevent accidental mass pings in DMs
            allowed = discord.AllowedMentions(users=True, roles=False, everyone=False)
            await target_member.send(rendered_dm, allowed_mentions=allowed)
            logger.info("DM successfully dispatched to %s (%s)", target_member, target_member.id)
        except discord.Forbidden:
            dm_status = "FAILED"
            dm_error = "User has direct messages disabled or has blocked the bot."
            logger.warning("Failed to DM %s: Direct messages disabled/blocked", target_member)
        except discord.HTTPException as exc:
            dm_status = "FAILED"
            dm_error = f"Discord API HTTP Error {exc.status}: {exc.text}"
            logger.warning("Failed to DM %s: %s", target_member, exc)
        except Exception as exc:
            dm_status = "FAILED"
            dm_error = f"Unexpected error delivering DM: {str(exc)}"
            logger.exception("Unexpected error delivering DM to %s", target_member)

        # 11. Record in audit log
        audit = await AuditService.log_action(
            session=session,
            guild_id=guild.id,
            actor_id=invoker.id,
            actor_name=str(invoker),
            target_id=target_member.id,
            target_name=str(target_member),
            role_id=role.id,
            role_name=role.name,
            action="ROLE_ASSIGN",
            dm_status=dm_status,
            dm_failure_reason=dm_error,
        )

        return RoleAssignmentResult(
            success=True,
            role=role,
            target_member=target_member,
            is_duplicate=False,
            dm_status=dm_status,
            dm_error=dm_error,
            rendered_dm=rendered_dm,
            audit_entry=audit,
        )

    @classmethod
    async def remove_role(
        cls,
        session: AsyncSession,
        invoker: discord.Member,
        bot_member: discord.Member,
        target_member: discord.Member,
        role_id_raw: str,
    ) -> RoleRemovalResult:
        """Validate and remove a role from a member, recording to audit log."""
        guild = invoker.guild

        role_id = parse_and_validate_role_id(role_id_raw)
        role = guild.get_role(role_id)
        if not role:
            raise RoleNotFoundError(
                f"No role with ID `{role_id}` exists in this server (`{guild.name}`)."
            )

        validate_user_permissions(invoker)
        validate_bot_permissions(bot_member)
        validate_role_eligibility(role)
        validate_hierarchy(invoker=invoker, bot_member=bot_member, target_role=role)

        if role not in target_member.roles:
            raise MemberLacksRoleError(
                f"{target_member.mention} does not currently have the `{role.name}` role."
            )

        reason = f"Removed by {invoker} ({invoker.id}) via Hayato On Fire"
        await target_member.remove_roles(role, reason=reason)

        audit = await AuditService.log_action(
            session=session,
            guild_id=guild.id,
            actor_id=invoker.id,
            actor_name=str(invoker),
            target_id=target_member.id,
            target_name=str(target_member),
            role_id=role.id,
            role_name=role.name,
            action="ROLE_REMOVE",
            dm_status="N/A",
            dm_failure_reason=None,
        )

        return RoleRemovalResult(
            success=True,
            role=role,
            target_member=target_member,
            audit_entry=audit,
        )
