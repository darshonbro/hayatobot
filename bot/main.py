"""Entry point and bot core for Hayato On Fire (Master Role Bot)."""

import asyncio
import logging
import sys
from typing import List

import discord
from discord import app_commands
from discord.ext import commands

from bot.checks import RoleManagementError
from bot.config import Config, load_config, setup_logging
from bot.database import DatabaseManager

logger = logging.getLogger("hayato_bot")

INITIAL_EXTENSIONS: List[str] = [
    "bot.cogs.role",
    "bot.cogs.dm_config",
    "bot.cogs.configuration",
    "bot.cogs.audit",
]


class HayatoBot(commands.Bot):
    """Production-grade Discord bot with dynamic role management and templated DMs."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.db = DatabaseManager(self.config.database_url)
        self.web_runner = None

        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True  # Required for role changes and member lookups

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self) -> None:
        """Asynchronous initialization called before connection."""
        logger.info("Starting database initialization...")
        self.db.initialize()
        await self.db.create_tables()

        logger.info("Loading extension cogs...")
        for ext in INITIAL_EXTENSIONS:
            try:
                await self.load_extension(ext)
                logger.info("Loaded extension: %s", ext)
            except Exception:
                logger.exception("Failed to load extension %s", ext)
                raise

        # Centralized App Command error handler
        self.tree.on_error = self.on_app_command_error

        # Synchronize slash commands
        if self.config.dev_guild_id:
            dev_guild = discord.Object(id=self.config.dev_guild_id)
            self.tree.copy_global_to(guild=dev_guild)
            synced = await self.tree.sync(guild=dev_guild)
            logger.info(
                "⚡ Fast-synced %d commands to development guild ID: %d",
                len(synced),
                self.config.dev_guild_id,
            )
        else:
            synced = await self.tree.sync()
            logger.info("🌐 Globally synchronized %d slash commands across Discord.", len(synced))

        # Start built-in web portal for Discord verification (Terms & Privacy)
        if self.config.enable_web:
            try:
                from web.server import start_web_server_async
                self.web_runner = await start_web_server_async(
                    host=self.config.web_host,
                    port=self.config.web_port,
                )
            except Exception as exc:
                logger.warning(
                    "Could not launch web portal on port %s: %s",
                    self.config.web_port,
                    exc,
                )

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        """Centralized error dispatcher for Discord application commands."""
        # Unwrap nested invoke errors
        if isinstance(error, app_commands.CommandInvokeError):
            original = error.original
        else:
            original = error

        if isinstance(original, RoleManagementError):
            message = f"❌ {str(original)}"
        elif isinstance(original, app_commands.CheckFailure):
            message = "❌ You do not have permission to execute this administrative command."
        elif isinstance(original, app_commands.CommandOnCooldown):
            message = f"⏳ This command is on cooldown. Try again in {original.retry_after:.1f}s."
        else:
            logger.exception("Unhandled command error in %s", interaction.command)
            message = "❌ An unexpected error occurred while executing the command."

        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except Exception:
            logger.exception("Failed to send error message back to user")

    async def on_ready(self) -> None:
        """Event triggered when Discord connection is established."""
        if not self.user:
            return
        logger.info("=" * 60)
        logger.info("🤖 %s is online and ready!", self.config.bot_name)
        logger.info("User: %s (ID: %s)", self.user.name, self.user.id)
        logger.info("Connected to %d servers", len(self.guilds))
        logger.info("=" * 60)

        # Set rich presence activity
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="roles | /role give",
        )
        await self.change_presence(activity=activity)

    async def close(self) -> None:
        """Graceful shutdown handler."""
        logger.info("Initiating graceful shutdown...")
        if self.web_runner is not None:
            await self.web_runner.cleanup()
            logger.info("Web portal shut down.")
        await self.db.close()
        await super().close()


def run() -> None:
    """Run bot entrypoint."""
    config = load_config()
    setup_logging(config.log_level)

    if not config.token:
        logger.error(
            "DISCORD_TOKEN is missing or blank in .env! "
            "Please copy .env.example to .env and configure your bot credentials."
        )
        sys.exit(1)

    bot = HayatoBot(config)
    try:
        bot.run(config.token)
    except KeyboardInterrupt:
        logger.info("Shutting down from KeyboardInterrupt.")


if __name__ == "__main__":
    run()
