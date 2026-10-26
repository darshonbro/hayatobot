"""General configuration commands: /config view, /config reset."""

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bot.checks import has_manage_roles_permission
from bot.services.template_service import TemplateService

if TYPE_CHECKING:
    from bot.main import HayatoBot

logger = logging.getLogger(__name__)


class ResetConfirmView(discord.ui.View):
    """Interactive confirmation buttons for resetting the DM template."""

    def __init__(self, bot: "HayatoBot", invoker_id: int, guild_id: int):
        super().__init__(timeout=60)
        self.bot = bot
        self.invoker_id = invoker_id
        self.guild_id = guild_id
        self.value: bool = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.invoker_id:
            await interaction.response.send_message(
                "❌ You are not authorized to use these confirmation buttons.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Confirm Reset", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        try:
            async with self.bot.db.session() as session:
                default_template = await TemplateService.reset_guild_template(
                    session=session,
                    guild_id=self.guild_id,
                )

            self.value = True
            for child in self.children:
                child.disabled = True

            embed = discord.Embed(
                title="Configuration Reset",
                description="✅ The server's DM template has been reset to the default template.",
                color=discord.Color.green(),
            )
            embed.add_field(name="Default Template Restored", value=f"```\n{default_template}\n```", inline=False)
            await interaction.response.edit_message(embed=embed, view=self)
            self.stop()
        except Exception as exc:
            logger.exception("Error resetting guild template")
            await interaction.response.send_message(f"❌ Failed to reset template: `{str(exc)}`", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = False
        for child in self.children:
            child.disabled = True
        embed = discord.Embed(
            title="Reset Cancelled",
            description="The template reset request was cancelled. No changes were made.",
            color=discord.Color.dark_grey(),
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()


class ConfigCog(commands.GroupCog, group_name="config"):
    """Commands for viewing and resetting server-wide bot configuration."""

    def __init__(self, bot: "HayatoBot") -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(
        name="view",
        description="Display the current server configuration and DM template.",
    )
    @has_manage_roles_permission()
    async def view_config(self, interaction: discord.Interaction) -> None:
        """Display active server configuration."""
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("❌ This command must be used in a server.", ephemeral=True)
            return

        try:
            async with self.bot.db.session() as session:
                current_template = await TemplateService.get_guild_template(
                    session=session,
                    guild_id=interaction.guild.id,
                )
                role_descs = await TemplateService.get_all_role_descriptions(
                    session=session,
                    guild_id=interaction.guild.id,
                )

            embed = discord.Embed(
                title=f"Configuration for {interaction.guild.name}",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Server ID", value=f"`{interaction.guild.id}`", inline=True)
            embed.add_field(name="Configured Role Descriptions", value=str(len(role_descs)), inline=True)
            embed.add_field(
                name="Active DM Template",
                value=f"```\n{current_template}\n```",
                inline=False,
            )

            if role_descs:
                desc_lines = []
                for rd in role_descs[:5]:
                    role = interaction.guild.get_role(rd.role_id)
                    role_repr = f"**{role.name}**" if role else f"Role `{rd.role_id}`"
                    desc_lines.append(f"• {role_repr}: {rd.description[:60]}")
                if len(role_descs) > 5:
                    desc_lines.append(f"... and {len(role_descs) - 5} more.")
                embed.add_field(
                    name="Sample Configured Descriptions",
                    value="\n".join(desc_lines),
                    inline=False,
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as exc:
            logger.exception("Unexpected error in /config view")
            await interaction.followup.send(f"❌ Failed to view config: `{str(exc)}`", ephemeral=True)

    @app_commands.command(
        name="reset",
        description="Reset this server's DM template back to the factory default.",
    )
    @has_manage_roles_permission()
    async def reset_config(self, interaction: discord.Interaction) -> None:
        """Prompt confirmation before resetting the DM template."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Confirm Configuration Reset",
            description=(
                "Are you sure you want to reset this server's DM template back to the factory default?\n\n"
                "**This action cannot be undone.**"
            ),
            color=discord.Color.yellow(),
        )

        view = ResetConfirmView(
            bot=self.bot,
            invoker_id=interaction.user.id,
            guild_id=interaction.guild.id,
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: "HayatoBot") -> None:
    """Register the Config cog."""
    await bot.add_cog(ConfigCog(bot))
