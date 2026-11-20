"""Shared paths and data loading for the static site."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "requests.json"
SITE_DIR = ROOT / "site"

GENERATED_FILES = (
    "index.html",
    "404.html",
    "robots.txt",
    "sitemap.xml",
    "llms.txt",
    "requests.json",
)


def load_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def page_url(data, path):
    host = data["site"]["pagesHost"].rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return host + path
