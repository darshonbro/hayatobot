"""Sync web templates to docs/ folder with relative URLs for GitHub Pages."""

from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TEMPLATES = BASE / "web" / "templates"
DOCS = BASE / "docs"

pages = ["index.html", "terms.html", "privacy.html"]

for page in pages:
    src = TEMPLATES / page
    dest = DOCS / page
    content = src.read_text(encoding="utf-8")
    content = content.replace('href="/static/', 'href="static/')
    content = content.replace('src="/static/', 'src="static/')
    content = content.replace('href="/terms"', 'href="terms.html"')
    content = content.replace('href="/privacy"', 'href="privacy.html"')
    content = content.replace('href="/"', 'href="index.html"')
    content = content.replace('href="/#features"', 'href="index.html#features"')
    content = content.replace('href="/#commands"', 'href="index.html#commands"')
    dest.write_text(content, encoding="utf-8")

print("Docs synced for GitHub Pages successfully.")
