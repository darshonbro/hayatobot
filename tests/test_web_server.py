"""Unit tests for the web portal: index, terms of service, privacy policy, and health check."""

import pytest
from aiohttp.test_utils import TestClient, TestServer
from web.server import create_app


@pytest.mark.asyncio
async def test_web_routes():
    """Ensure web server serves index, terms, privacy, and health status properly."""
    app = create_app()
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()

    try:
        # 1. Health endpoint
        resp = await client.get("/health")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "online"
        assert data["bot"] == "Hayato On Fire"

        # 2. Terms of service
        resp_terms = await client.get("/terms")
        assert resp_terms.status == 200
        terms_html = await resp_terms.text()
        assert "Terms of Service" in terms_html
        assert "Hayato On Fire" in terms_html

        # 3. Privacy policy
        resp_privacy = await client.get("/privacy")
        assert resp_privacy.status == 200
        privacy_html = await resp_privacy.text()
        assert "Privacy Policy" in privacy_html
        assert "Discord" in privacy_html

        # 4. Landing page
        resp_index = await client.get("/")
        assert resp_index.status == 200
        index_html = await resp_index.text()
        assert "Hayato" in index_html
        assert "Role Management" in index_html
    finally:
        await client.close()
