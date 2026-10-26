"""DM configuration commands: /dm-config set, preview, description, variables."""

import logging
from typing import Optional, TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bot.checks import (
    RoleManagementError,
    has_manage_roles_permission,
    parse_and_validate_role_id,
)
from bot.services.template_service import (
    MAX_TEMPLATE_LENGTH,
    SUPPORTED_VARIABLES,
    TemplateService,
    TemplateValidationError,
)

if TYPE_CHECKING:
    from bot.main import HayatoBot

logger = logging.getLogger(__name__)


class DmConfigCog(commands.GroupCog, group_name="dm-config"):
    """Commands to customize DM templates and role-specific descriptions."""

    def __init__(self, bot: "HayatoBot") -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(
        name="set",
        description="Configure the reusable DM template for this server.",
    )
    @app_commands.describe(
        template="The message template. Use supported variables like {user}, {role}, {role_description}."
    )
    @has_manage_roles_permission()
    async def set_template(self, interaction: discord.Interaction, template: str) -> None:
        """Set the server's reusable DM template."""
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("❌ This command must be used in a server.", ephemeral=True)
            return

        try:
            async with self.bot.db.session() as session:
                saved = await TemplateService.set_guild_template(
                    session=session,
                    guild_id=interaction.guild.id,
                    template=template,
                )

            embed = discord.Embed(
                title="DM Template Updated",
                description="The server's dynamic DM template has been saved successfully.",
                color=discord.Color.green(),
            )
            embed.add_field(name="New Template", value=f"```\n{saved}\n```", inline=False)
            embed.set_footer(text=f"Character count: {len(saved)} / {MAX_TEMPLATE_LENGTH}")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except TemplateValidationError as exc:
            embed = discord.Embed(
                title="Invalid Template",
                description=f"❌ {str(exc)}",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as exc:
            logger.exception("Unexpected error in /dm-config set")
            await interaction.followup.send(f"❌ Failed to save template: `{str(exc)}`", ephemeral=True)

    @app_commands.command(
        name="preview",
        description="Preview a DM template using a selected role without sending a real DM.",
    )
    @app_commands.describe(
        role_id="The numeric ID of the role to preview with",
        custom_template="Optional candidate template string to preview instead of saved template",
    )
    @has_manage_roles_permission()
    async def preview_template(
        self,
        interaction: discord.Interaction,
        role_id: str,
        custom_template: Optional[str] = None,
    ) -> None:
        """Render a preview of a template."""
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild or not isinstance(interaction.user, discord.Member):
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

        try:
            async with self.bot.db.session() as session:
                if custom_template:
                    template_to_preview = custom_template
                else:
                    template_to_preview = await TemplateService.get_guild_template(
                        session=session,
                        guild_id=interaction.guild.id,
                    )

                role_desc = await TemplateService.get_role_description(
                    session=session,
                    guild_id=interaction.guild.id,
                    role_id=role.id,
                )

            rendered = TemplateService.render(
                template=template_to_preview,
                member=interaction.user,
                role=role,
                role_description=role_desc,
            )

            embed = discord.Embed(
                title="DM Template Preview",
                description="This is how the DM will appear to the member upon receiving the role.",
                color=discord.Color.blurple(),
            )
            embed.add_field(name="Role Evaluated", value=f"{role.mention} (`{role.id}`)", inline=True)
            embed.add_field(
                name="Role Description Applied",
                value=f"_{role_desc}_" if role_desc else "*(None configured)*",
                inline=True,
            )
            embed.add_field(
                name="Rendered Direct Message Output",
                value=rendered if len(rendered) < 1024 else f"{rendered[:1000]}...",
                inline=False,
            )
            embed.set_footer(text="Note: No actual DM was dispatched.")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as exc:
            logger.exception("Unexpected error in /dm-config preview")
            await interaction.followup.send(f"❌ Preview error: `{str(exc)}`", ephemeral=True)

    @app_commands.command(
        name="description",
        description="Configure or clear a role-specific description for the {role_description} variable.",
    )
    @app_commands.describe(
        role_id="The numeric ID of the role to describe",
        description="The description text (leave blank or type 'clear' to remove)",
    )
    @has_manage_roles_permission()
    async def set_description(
        self,
        interaction: discord.Interaction,
        role_id: str,
        description: Optional[str] = None,
    ) -> None:
        """Set or clear a role-specific description."""
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

        is_clearing = not description or description.strip().lower() in ("", "clear", "none")

        try:
            async with self.bot.db.session() as session:
                if is_clearing:
                    await TemplateService.delete_role_description(
                        session=session,
                        guild_id=interaction.guild.id,
                        role_id=role.id,
                    )
                    embed = discord.Embed(
                        title="Role Description Cleared",
                        description=f"Cleared custom description for **{role.name}** (`{role.id}`).",
                        color=discord.Color.dark_grey(),
                    )
                else:
                    await TemplateService.set_role_description(
                        session=session,
                        guild_id=interaction.guild.id,
                        role_id=role.id,
                        description=description,
                    )
                    embed = discord.Embed(
                        title="Role Description Saved",
                        description=f"Configured description for **{role.name}** (`{role.id}`).",
                        color=discord.Color.green(),
                    )
                    embed.add_field(name="Description Content", value=f"```\n{description.strip()}\n```", inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as exc:
            logger.exception("Unexpected error in /dm-config description")
            await interaction.followup.send(f"❌ Failed to update description: `{str(exc)}`", ephemeral=True)

    @app_commands.command(
        name="variables",
        description="Display all supported template variables and usage notes.",
    )
    async def list_variables(self, interaction: discord.Interaction) -> None:
        """List supported variables for the template engine."""
        embed = discord.Embed(
            title="Supported DM Template Variables",
            description=(
                "These variables are replaced dynamically when a role assignment occurs. "
                "Any unrecognized `{variable}` is preserved safely without crashing."
            ),
            color=discord.Color.teal(),
        )

        for var, desc in SUPPORTED_VARIABLES.items():
            embed.add_field(name=f"`{var}`", value=desc, inline=False)

        embed.add_field(
            name="Example Template",
            value=(
                "```\n"
                "Congratulations, {user}!\n\n"
                "You have received the {role} role.\n\n"
                "{role_description}\n\n"
                "Enjoy your new permissions!\n"
                "```"
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: "HayatoBot") -> None:
    """Register the DmConfig cog."""
    await bot.add_cog(DmConfigCog(bot))
