"""Audit commands Cog: /audit recent, /audit user."""

import logging
from typing import TYPE_CHECKING, List

import discord
from discord import app_commands
from discord.ext import commands

from bot.checks import has_manage_roles_permission
from bot.models import AuditLog
from bot.services.audit_service import AuditService

if TYPE_CHECKING:
    from bot.main import HayatoBot

logger = logging.getLogger(__name__)


def format_audit_embed(
    title: str,
    logs: List[AuditLog],
    guild: discord.Guild,
) -> discord.Embed:
    """Helper to render audit log entries into an informative Discord embed."""
    embed = discord.Embed(
        title=title,
        color=discord.Color.dark_teal(),
    )

    if not logs:
        embed.description = "No audit log records found."
        return embed

    for entry in logs:
        # Generate unix timestamp for Discord dynamic formatting
        ts = int(entry.timestamp.timestamp())
        time_str = f"<t:{ts}:f> (<t:{ts}:R>)"

        action_symbol = "➕" if "ASSIGN" in entry.action else "➖"
        if "DUPLICATE" in entry.action:
            action_symbol = "⚠️"

        status_text = entry.dm_status
        if entry.dm_status == "SENT":
            dm_repr = "✅ Delivered"
        elif entry.dm_status == "FAILED":
            dm_repr = f"❌ Failed ({entry.dm_failure_reason or 'Unknown'})"
        elif entry.dm_status == "SKIPPED_DUPLICATE":
            dm_repr = "⚠️ Skipped (Already possessed)"
        else:
            dm_repr = entry.dm_status

        field_title = f"{action_symbol} {entry.action} — {time_str}"
        field_content = (
            f"• **Target:** `{entry.target_name}` (<@{entry.target_id}>)\n"
            f"• **Role:** `{entry.role_name}` (ID: `{entry.role_id}`)\n"
            f"• **Actor:** `{entry.actor_name}` (<@{entry.actor_id}>)\n"
            f"• **DM Status:** {dm_repr}"
        )
        embed.add_field(name=field_title, value=field_content, inline=False)

    return embed


class AuditCog(commands.GroupCog, group_name="audit"):
    """Commands to query role-management audit logs and DM delivery histories."""

    def __init__(self, bot: "HayatoBot") -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(
        name="recent",
        description="Display recent role assignment, removal, and DM delivery records.",
    )
    @app_commands.describe(limit="Number of records to fetch (1-25, default 10)")
    @has_manage_roles_permission()
    async def audit_recent(
        self,
        interaction: discord.Interaction,
        limit: int = 10,
    ) -> None:
        """Display recent audit logs for the server."""
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("❌ This command must be used in a server.", ephemeral=True)
            return

        bounded_limit = max(1, min(limit, 25))

        try:
            async with self.bot.db.session() as session:
                logs = await AuditService.get_recent_logs(
                    session=session,
                    guild_id=interaction.guild.id,
                    limit=bounded_limit,
                )

            embed = format_audit_embed(
                title=f"Recent Audit Logs for {interaction.guild.name} (Last {len(logs)})",
                logs=logs,
                guild=interaction.guild,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as exc:
            logger.exception("Unexpected error in /audit recent")
            await interaction.followup.send(f"❌ Failed to query audit logs: `{str(exc)}`", ephemeral=True)

    @app_commands.command(
        name="user",
        description="Display recent role-related actions for a specific member.",
    )
    @app_commands.describe(
        member="The member to view audit history for",
        limit="Number of records to fetch (1-25, default 10)",
    )
    @has_manage_roles_permission()
    async def audit_user(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        limit: int = 10,
    ) -> None:
        """Display audit logs for a specific member."""
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("❌ This command must be used in a server.", ephemeral=True)
            return

        bounded_limit = max(1, min(limit, 25))

        try:
            async with self.bot.db.session() as session:
                logs = await AuditService.get_user_logs(
                    session=session,
                    guild_id=interaction.guild.id,
                    user_id=member.id,
                    limit=bounded_limit,
                )

            embed = format_audit_embed(
                title=f"Audit Records for {member.display_name} (Last {len(logs)})",
                logs=logs,
                guild=interaction.guild,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as exc:
            logger.exception("Unexpected error in /audit user")
            await interaction.followup.send(f"❌ Failed to query user audit logs: `{str(exc)}`", ephemeral=True)


async def setup(bot: "HayatoBot") -> None:
    """Register the Audit cog."""
    await bot.add_cog(AuditCog(bot))
