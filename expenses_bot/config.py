"""Everything the bot reads from its environment, in one place.

Values come from real environment variables: in Docker, compose's `env_file: .env`
injects them and the .env file itself never enters the image. load_dotenv() fills the
same os.environ from a local .env for `python -m expenses_bot` on a dev machine -- it
never overrides a variable that is already set.

API_KEY is deliberately *not* validated here: importing the app (tests do) must not
need a token. main() checks it before building the Bot.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

API_KEY = os.environ.get("API_KEY") or None

# Gates the 🧪 Тест sandbox button/router (SEC-8) -- a development tool that exposes
# internals (variant keys, character budgets), not meant for every user in production.
_admin_id_raw = os.environ.get("ADMIN_ID")
ADMIN_ID = int(_admin_id_raw) if _admin_id_raw else None

# Message bodies are personal data (SEC-5) -- off by default, opt in for local debugging.
LOG_MESSAGE_TEXT = os.environ.get("LOG_MESSAGE_TEXT") == "1"

# Anchored on this file, not the cwd, so the bot starts the same from any directory.
# The image sets DATA_DIR=/app/data, which compose bind-mounts from ./data on the host.
DATA_DIR = Path(os.environ.get("DATA_DIR") or REPO_ROOT / "data")
