"""Lightweight asynchronous web server for Hayato On Fire landing page, Terms, and Privacy Policy."""

import logging
import os
from pathlib import Path
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("hayato_web")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [web]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


async def handle_index(request: web.Request) -> web.Response:
    """Serve home / landing page."""
    index_file = TEMPLATES_DIR / "index.html"
    return web.FileResponse(index_file)


async def handle_terms(request: web.Request) -> web.Response:
    """Serve Terms of Service page."""
    terms_file = TEMPLATES_DIR / "terms.html"
    return web.FileResponse(terms_file)


async def handle_privacy(request: web.Request) -> web.Response:
    """Serve Privacy Policy page."""
    privacy_file = TEMPLATES_DIR / "privacy.html"
    return web.FileResponse(privacy_file)


async def handle_health(request: web.Request) -> web.Response:
    """Health check endpoint for uptimerobot or hosting monitors."""
    return web.json_response({
        "status": "online",
        "bot": "Hayato On Fire",
        "version": "1.0.0",
    })


def create_app() -> web.Application:
    """Create and configure the aiohttp web application."""
    app = web.Application()

    # Route definitions
    app.router.add_get("/", handle_index)
    app.router.add_get("/terms", handle_terms)
    app.router.add_get("/terms.html", handle_terms)
    app.router.add_get("/privacy", handle_privacy)
    app.router.add_get("/privacy.html", handle_privacy)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/status", handle_health)

    # Static assets
    app.router.add_static("/static/", path=STATIC_DIR, name="static")

    return app


async def start_web_server_async(host: str = "0.0.0.0", port: int = 8080) -> web.AppRunner:
    """Start web server asynchronously inside an existing event loop."""
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("🌐 Web portal active at http://%s:%d", host if host != "0.0.0.0" else "localhost", port)
    logger.info("📄 Terms of Service: http://localhost:%d/terms", port)
    logger.info("🔒 Privacy Policy:  http://localhost:%d/privacy", port)
    return runner


def run() -> None:
    """Standalone runner entrypoint."""
    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("WEB_PORT", "8080")))
    app = create_app()
    logger.info("Starting Hayato Web Server on %s:%d...", host, port)
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    run()
