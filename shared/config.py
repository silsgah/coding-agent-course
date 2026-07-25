"""
Shared configuration for the Coding Agent Course.

Loads API keys from .env file, provides model selection,
and centralizes settings used across all weeks.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from the repo root (two levels up from shared/)
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _REPO_ROOT / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)


# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------------------
# Default model
# ---------------------------------------------------------------------------
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")


def get_api_key(provider: str = "gemini") -> str:
    """Return the API key for the given provider, or raise a clear error."""
    keys = {
        "gemini": GEMINI_API_KEY,
        "openrouter": OPENROUTER_API_KEY,
        "openai": OPENAI_API_KEY,
        "anthropic": ANTHROPIC_API_KEY,
    }
    key = keys.get(provider, "")
    if not key:
        raise ValueError(
            f"No API key found for provider '{provider}'. "
            f"Set {provider.upper()}_API_KEY in your .env file.\n"
            f"See .env.example for instructions."
        )
    return key


def validate_setup() -> None:
    """Check that at least one provider is configured. Called at course start."""
    providers = {
        "gemini": GEMINI_API_KEY,
        "openrouter": OPENROUTER_API_KEY,
        "openai": OPENAI_API_KEY,
        "anthropic": ANTHROPIC_API_KEY,
    }
    configured = [name for name, key in providers.items() if key]
    if not configured:
        raise SystemExit(
            "\n❌ No API keys configured!\n"
            "Copy .env.example to .env and add at least one API key.\n"
            "Gemini is free: https://aistudio.google.com/apikey\n"
        )
    print(f"✅ Configured providers: {', '.join(configured)}")
    print(f"📌 Default model: {DEFAULT_MODEL}")
