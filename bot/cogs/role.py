"""Role commands Cog: /role give, /role remove, /role info."""

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bot.checks import (
    RoleManagementError,
    has_manage_roles_permission,
    parse_and_validate_role_id,
)
from bot.services.role_service import RoleService
from bot.services.template_service import TemplateService

if TYPE_CHECKING:
    from bot.main import HayatoBot

logger = logging.getLogger(__name__)


class RoleCog(commands.GroupCog, group_name="role"):
    """Commands for managing guild roles and viewing role metadata."""

    def __init__(self, bot: "HayatoBot") -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(
        name="give",
        description="Assign a role to a member by Role ID and dispatch a personalized DM.",
    )
    @app_commands.describe(
        member="The guild member who will receive the role",
        role_id="The numeric ID of the role to assign",
    )
    @has_manage_roles_permission()
    async def give_role(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role_id: str,
    ) -> None:
        """Assign role with dynamic DM notification."""
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.followup.send(
                "❌ This command can only be used within a server.", ephemeral=True
            )
            return

        bot_member = interaction.guild.me

        try:
            async with self.bot.db.session() as session:
                result = await RoleService.assign_role(
                    session=session,
                    invoker=interaction.user,
                    bot_member=bot_member,
                    target_member=member,
                    role_id_raw=role_id,
                )

            if result.is_duplicate:
                embed = discord.Embed(
                    title="Role Already Assigned",
                    description=(
                        f"⚠️ {member.mention} already possesses the **{result.role.name}** "
                        f"(ID: `{result.role.id}`) role.\n\n"
                        "No modifications were made and no duplicate DM was sent."
                    ),
                    color=discord.Color.yellow(),
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Role assigned successfully
            embed = discord.Embed(
                title="Role Assigned Successfully",
                color=discord.Color.green(),
            )
            embed.add_field(name="Target Member", value=f"{member.mention} (`{member.id}`)", inline=True)
            embed.add_field(name="Role Assigned", value=f"**{result.role.name}** (`{result.role.id}`)", inline=True)

            if result.dm_status == "SENT":
                embed.add_field(
                    name="Direct Message",
                    value="✅ Delivered personalized DM to recipient.",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="Direct Message",
                    value=f"⚠️ Failed to deliver DM: {result.dm_error}",
                    inline=False,
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except RoleManagementError as exc:
            embed = discord.Embed(
                title="Role Assignment Failed",
                description=f"❌ {str(exc)}",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as exc:
            logger.exception("Unexpected error in /role give")
            embed = discord.Embed(
                title="Internal Error",
                description=f"❌ An unexpected error occurred: `{str(exc)}`",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="remove",
        description="Remove a role from a member by Role ID.",
    )
    @app_commands.describe(
        member="The guild member to remove the role from",
        role_id="The numeric ID of the role to remove",
    )
    @has_manage_roles_permission()
    async def remove_role(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role_id: str,
    ) -> None:
        """Remove a role from a member."""
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.followup.send(
                "❌ This command can only be used within a server.", ephemeral=True
            )
            return

        bot_member = interaction.guild.me

        try:
            async with self.bot.db.session() as session:
                result = await RoleService.remove_role(
                    session=session,
                    invoker=interaction.user,
                    bot_member=bot_member,
                    target_member=member,
                    role_id_raw=role_id,
                )

            embed = discord.Embed(
                title="Role Removed Successfully",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Target Member", value=f"{member.mention} (`{member.id}`)", inline=True)
            embed.add_field(name="Role Removed", value=f"**{result.role.name}** (`{result.role.id}`)", inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)

        except RoleManagementError as exc:
            embed = discord.Embed(
                title="Role Removal Failed",
                description=f"❌ {str(exc)}",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as exc:
            logger.exception("Unexpected error in /role remove")
            embed = discord.Embed(
                title="Internal Error",
                description=f"❌ An unexpected error occurred: `{str(exc)}`",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="info",
        description="Display role details including name, ID, position, permissions, and description.",
    )
    @app_commands.describe(role_id="The numeric ID of the role to inspect")
    async def role_info(self, interaction: discord.Interaction, role_id: str) -> None:
        """Display role details and its configured DM description."""
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("❌ This command must be used in a server.", ephemeral=True)
            return

        try:
            parsed_id = parse_and_validate_role_id(role_id)
        except RoleManagementError as exc:
            await interaction.followup.send(f"❌ {str(exc)}", ephemeral=True)
            return

        role = interaction.guild.get_role(parsed_id)
        if not role:
            await interaction.followup.send(
                f"❌ No role with ID `{parsed_id}` exists in this server.", ephemeral=True
            )
            return

        # Fetch configured description from DB
        desc_text = "*(None configured)*"
        try:
            async with self.bot.db.session() as session:
                custom_desc = await TemplateService.get_role_description(
                    session=session,
                    guild_id=interaction.guild.id,
                    role_id=role.id,
                )
                if custom_desc:
                    desc_text = custom_desc
        except Exception as exc:
            logger.warning("Could not fetch role description for info: %s", exc)

        embed = discord.Embed(
            title=f"Role Information: {role.name}",
            color=role.color if role.color.value != 0 else discord.Color.default(),
        )
        embed.add_field(name="Role ID", value=f"`{role.id}`", inline=True)
        embed.add_field(name="Mention", value=role.mention, inline=True)
        embed.add_field(name="Position", value=str(role.position), inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Members with Role", value=str(len(role.members)), inline=True)
        embed.add_field(name="Hoisted / Separate", value="Yes" if role.hoist else "No", inline=True)
        embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No", inline=True)
        embed.add_field(name="Managed (Integration)", value="Yes" if role.managed else "No", inline=True)
        embed.add_field(name="Configured DM Description", value=desc_text, inline=False)

        # Highlight key permissions
        perms = []
        if role.permissions.administrator:
            perms.append("Administrator")
        if role.permissions.manage_guild:
            perms.append("Manage Server")
        if role.permissions.manage_roles:
            perms.append("Manage Roles")
        if role.permissions.manage_channels:
            perms.append("Manage Channels")
        if role.permissions.ban_members:
            perms.append("Ban Members")
        if role.permissions.kick_members:
            perms.append("Kick Members")
        if role.permissions.mention_everyone:
            perms.append("Mention Everyone")

        embed.add_field(
            name="Key Permissions",
            value=", ".join(perms) if perms else "Standard / General Permissions",
            inline=False,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: "HayatoBot") -> None:
    """Register the Role cog."""
    await bot.add_cog(RoleCog(bot))
