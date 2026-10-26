"""Unit tests for the dynamic DM template engine and server isolation."""

import pytest
from bot.config import DEFAULT_DM_TEMPLATE
from bot.services.template_service import (
    TemplateService,
    TemplateValidationError,
    sanitize_mentions,
)


def test_dynamic_role_name_substitution(mock_target_member, mock_role):
    """Ensure {role} and {role_id} are dynamically substituted."""
    template = "Welcome! You got the {role} role (ID: {role_id}) on {server}."
    rendered = TemplateService.render(
        template=template,
        member=mock_target_member,
        role=mock_role,
        role_description=None,
    )

    assert "Champion" in rendered
    assert "555555555" in rendered
    assert "Hayato Arena" in rendered
    assert "{role}" not in rendered


def test_role_description_substitution(mock_target_member, mock_role):
    """Ensure {role_description} is replaced when provided and empty when omitted."""
    template = "Role: {role}\nPerks: {role_description}"

    # With description
    rendered = TemplateService.render(
        template=template,
        member=mock_target_member,
        role=mock_role,
        role_description="VIP Lounge and Weekly Giveaways",
    )
    assert "VIP Lounge and Weekly Giveaways" in rendered

    # Without description (None)
    rendered_empty = TemplateService.render(
        template=template,
        member=mock_target_member,
        role=mock_role,
        role_description=None,
    )
    assert "Perks: \n" in rendered_empty or rendered_empty.endswith("Perks: ") or "Perks: " in rendered_empty
    assert "{role_description}" not in rendered_empty


def test_unknown_template_variables_safety(mock_target_member, mock_role):
    """Ensure unknown variables do not raise KeyError and are preserved safely."""
    template = "Hello {user}! Your balance is {fake_variable} coins in {server}."
    rendered = TemplateService.render(
        template=template,
        member=mock_target_member,
        role=mock_role,
        role_description=None,
    )

    assert mock_target_member.mention in rendered
    assert "{fake_variable}" in rendered
    assert "Hayato Arena" in rendered


def test_mass_mention_prevention(mock_target_member, mock_role):
    """Ensure @everyone and @here inside user/server/role names or descriptions are neutralized."""
    mock_target_member.display_name = "Troll @everyone @here"
    mock_role.name = "Malicious @everyone"

    template = "{user_name} received {role} with perks: {role_description}"
    desc = "Ping test: @everyone and @here"

    rendered = TemplateService.render(
        template=template,
        member=mock_target_member,
        role=mock_role,
        role_description=desc,
    )

    # Raw '@everyone' and '@here' should not be present
    assert "@everyone" not in rendered
    assert "@here" not in rendered
    # But neutralized variants with zero-width space should exist
    assert "@\u200beveryone" in rendered
    assert "@\u200bhere" in rendered


def test_template_validation_rules():
    """Ensure template validation rejects empty or oversized templates."""
    with pytest.raises(TemplateValidationError, match="cannot be empty"):
        TemplateService.validate_template("   ")

    oversized = "A" * 1901
    with pytest.raises(TemplateValidationError, match="exceeds maximum allowed limit"):
        TemplateService.validate_template(oversized)


@pytest.mark.asyncio
async def test_per_server_configuration_isolation(db_session):
    """Ensure one server's DM template never affects another server."""
    guild_1 = 10001
    guild_2 = 20002

    custom_tmpl_1 = "Server 1 Custom: {role} for {user}!"
    custom_tmpl_2 = "Server 2 Distinct: Welcome {user} to {role}!"

    # Save distinct templates
    await TemplateService.set_guild_template(db_session, guild_1, custom_tmpl_1)
    await TemplateService.set_guild_template(db_session, guild_2, custom_tmpl_2)

    # Verify isolation
    retrieved_1 = await TemplateService.get_guild_template(db_session, guild_1)
    retrieved_2 = await TemplateService.get_guild_template(db_session, guild_2)
    unconfigured = await TemplateService.get_guild_template(db_session, 30003)

    assert retrieved_1 == custom_tmpl_1
    assert retrieved_2 == custom_tmpl_2
    assert unconfigured == DEFAULT_DM_TEMPLATE


@pytest.mark.asyncio
async def test_role_description_server_isolation(db_session):
    """Ensure role descriptions are strictly isolated by guild and role ID."""
    guild_a = 111
    guild_b = 222
    role_id = 999  # same role ID in two different guilds

    await TemplateService.set_role_description(db_session, guild_a, role_id, "Guild A Description")
    await TemplateService.set_role_description(db_session, guild_b, role_id, "Guild B Description")

    desc_a = await TemplateService.get_role_description(db_session, guild_a, role_id)
    desc_b = await TemplateService.get_role_description(db_session, guild_b, role_id)

    assert desc_a == "Guild A Description"
    assert desc_b == "Guild B Description"

    # Deleting in Guild A leaves Guild B intact
    deleted = await TemplateService.delete_role_description(db_session, guild_a, role_id)
    assert deleted is True
    assert await TemplateService.get_role_description(db_session, guild_a, role_id) is None
    assert await TemplateService.get_role_description(db_session, guild_b, role_id) == "Guild B Description"
