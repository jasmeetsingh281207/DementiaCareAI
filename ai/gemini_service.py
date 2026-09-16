"""Single, lazy Gemini integration used by every active AI feature.

The project uses google-genai's ``client.models.generate_content`` API.  This
module deliberately never contacts Gemini at import/startup time.
"""
from __future__ import annotations

import os
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    from google import genai
except Exception:  # optional dependency in offline/demo installs
    genai = None

_client: Any = None
_attempted = False

def model_name() -> str:
    return os.getenv("GEMINI_MODEL") or os.getenv("MODEL_NAME") or "gemini-3.6-flash"

def get_client() -> Any | None:
    global _client, _attempted
    if _attempted:
        return _client
    _attempted = True
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or genai is None:
        return None
    try:
        _client = genai.Client(api_key=key)
    except Exception:
        _client = None
    return _client

def generate(prompt: str, *, contents: Any | None = None, config: Any | None = None) -> str | None:
    client = get_client()
    if client is None:
        return None
    try:
        response = client.models.generate_content(
            model=model_name(), contents=contents if contents is not None else prompt, config=config
        )
        text = getattr(response, "text", None)
        return text.strip() if isinstance(text, str) and text.strip() else None
    except Exception:
        return None

def status() -> dict[str, Any]:
    configured = bool(os.getenv("GEMINI_API_KEY", "").strip())
    client = get_client() if configured else None
    return {
        "configured": configured,
        "client_initialized": client is not None,
        "usable": client is not None,
        "model": model_name(),
        "api": "google-genai client.models.generate_content",
        "network_checked": False,
        "fallback_available": True,
    }
