import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
DEFAULT_MIN_SCORE = int(os.getenv("CONTENT_MIN_SCORE", "70"))
DEFAULT_MAX_ATTEMPTS = int(os.getenv("CONTENT_MAX_ATTEMPTS", "3"))


def get_openai_api_key() -> str:
    """Read the API key from the environment."""

    return os.getenv("OPENAI_API_KEY", "").strip()
