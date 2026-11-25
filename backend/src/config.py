import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT
ENV_FILE = BACKEND_ROOT / ".env"

load_dotenv(ENV_FILE, override=False)


def get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or not value.strip() or value.startswith("CHANGE_ME_"):
        raise RuntimeError(f"{name} must be set in {ENV_FILE} or the process environment")
    return value


def get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")
