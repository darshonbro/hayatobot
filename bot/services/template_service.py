"""Dynamic DM Template Engine and Role Description Management."""

import re
from typing import Dict, List, Optional

import discord
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import DEFAULT_DM_TEMPLATE
from bot.models import GuildConfig, RoleDescription

MAX_TEMPLATE_LENGTH = 1900
MAX_DISCORD_MESSAGE_LENGTH = 2000

SUPPORTED_VARIABLES: Dict[str, str] = {
    "{user}": "Recipient's Discord mention (<@ID>)",
    "{user_name}": "Recipient's display name or nickname",
    "{user_id}": "Recipient's numeric Discord ID",
    "{server}": "Server / Guild name",
    "{role}": "Name of the assigned role",
    "{role_id}": "Numeric ID of the assigned role",
    "{role_description}": "Optional description configured for that specific role",
}


def sanitize_mentions(text: str) -> str:
    """Neutralize potential mass mentions (@everyone and @here) using zero-width spaces."""
    if not text:
        return ""
    return text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")


class TemplateValidationError(Exception):
    """Raised when a DM template fails validation."""
    pass


class TemplateService:
    """Engine for rendering, validating, and persisting DM templates and role descriptions."""

    @staticmethod
    def sanitize(text: str) -> str:
        """Expose mention sanitization."""
        return sanitize_mentions(text)

    @classmethod
    def validate_template(cls, template: str) -> None:
        """Validate template length and syntax."""
        if not template or not template.strip():
            raise TemplateValidationError("The template cannot be empty.")

        if len(template) > MAX_TEMPLATE_LENGTH:
            raise TemplateValidationError(
                f"Template length ({len(template)}) exceeds maximum allowed limit of {MAX_TEMPLATE_LENGTH} characters."
            )

    @classmethod
    def render(
        cls,
        template: str,
        member: discord.Member,
        role: discord.Role,
        role_description: Optional[str] = None,
    ) -> str:
        """
        Dynamically substitute supported placeholders with contextual values.
        Unknown placeholders are preserved safely without throwing KeyError.
        Mentions within dynamic values are safely sanitized.
        """
        # Build clean variable mapping
        variables = {
            "user": member.mention,
            "user_name": sanitize_mentions(member.display_name),
            "user_id": str(member.id),
            "server": sanitize_mentions(member.guild.name),
            "role": sanitize_mentions(role.name),
            "role_id": str(role.id),
            "role_description": sanitize_mentions(role_description) if role_description else "",
        }

        # Substitute matches safely using regex pattern
        def replace_var(match: re.Match) -> str:
            var_name = match.group(1)
            if var_name in variables:
                return variables[var_name]
            # Unknown variable preserved as-is
            return match.group(0)

        rendered = re.sub(r"\{([a-zA-Z0-9_]+)\}", replace_var, template)

        # Discord hard message boundary
        if len(rendered) > MAX_DISCORD_MESSAGE_LENGTH:
            rendered = rendered[: MAX_DISCORD_MESSAGE_LENGTH - 3] + "..."

        return rendered

    @classmethod
    async def get_guild_template(cls, session: AsyncSession, guild_id: int) -> str:
        """Retrieve the configured DM template for a guild, falling back to default."""
        stmt = select(GuildConfig.dm_template).where(GuildConfig.guild_id == guild_id)
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()
        return template if template is not None else DEFAULT_DM_TEMPLATE

    @classmethod
    async def set_guild_template(cls, session: AsyncSession, guild_id: int, template: str) -> str:
        """Configure and persist a server's reusable DM template."""
        cls.validate_template(template)

        stmt = select(GuildConfig).where(GuildConfig.guild_id == guild_id)
        result = await session.execute(stmt)
        config = result.scalar_one_or_none()

        if config:
            config.dm_template = template
        else:
            config = GuildConfig(guild_id=guild_id, dm_template=template)
            session.add(config)

        await session.flush()
        return config.dm_template

    @classmethod
    async def reset_guild_template(cls, session: AsyncSession, guild_id: int) -> str:
        """Reset a server's template to the default."""
        stmt = select(GuildConfig).where(GuildConfig.guild_id == guild_id)
        result = await session.execute(stmt)
        config = result.scalar_one_or_none()

        if config:
            config.dm_template = DEFAULT_DM_TEMPLATE
        else:
            config = GuildConfig(guild_id=guild_id, dm_template=DEFAULT_DM_TEMPLATE)
            session.add(config)

        await session.flush()
        return DEFAULT_DM_TEMPLATE

    @classmethod
    async def get_role_description(
        cls,
        session: AsyncSession,
        guild_id: int,
        role_id: int,
    ) -> Optional[str]:
        """Fetch role description for a specific guild and role."""
        stmt = select(RoleDescription.description).where(
            RoleDescription.guild_id == guild_id,
            RoleDescription.role_id == role_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def set_role_description(
        cls,
        session: AsyncSession,
        guild_id: int,
        role_id: int,
        description: str,
    ) -> None:
        """Store or update a role-specific description."""
        sanitized_desc = description.strip()
        if not sanitized_desc:
            await cls.delete_role_description(session, guild_id, role_id)
            return

        stmt = select(RoleDescription).where(
            RoleDescription.guild_id == guild_id,
            RoleDescription.role_id == role_id,
        )
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            record.description = sanitized_desc
        else:
            record = RoleDescription(
                guild_id=guild_id,
                role_id=role_id,
                description=sanitized_desc,
            )
            session.add(record)

        await session.flush()

    @classmethod
    async def delete_role_description(
        cls,
        session: AsyncSession,
        guild_id: int,
        role_id: int,
    ) -> bool:
        """Clear a role description. Returns True if a record was deleted."""
        stmt = delete(RoleDescription).where(
            RoleDescription.guild_id == guild_id,
            RoleDescription.role_id == role_id,
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount > 0

    @classmethod
    async def get_all_role_descriptions(
        cls,
        session: AsyncSession,
        guild_id: int,
    ) -> List[RoleDescription]:
        """Fetch all configured role descriptions for a guild."""
        stmt = (
            select(RoleDescription)
            .where(RoleDescription.guild_id == guild_id)
            .order_by(RoleDescription.updated_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
