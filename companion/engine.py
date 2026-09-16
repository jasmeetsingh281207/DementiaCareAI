"""
DementiaCareAI
Companion Engine

The companion engine is the public interface used by Flask/API
and other application components.

Conversation intelligence is delegated to the unified
conversation engine.

Language handling is delegated to language.py.

This prevents duplicate AI generation and duplicate database writes.
"""

from __future__ import annotations

from typing import Any

from conversation.conversation_engine import (
    process_message as process_conversation_message,
    get_engine_status as get_conversation_engine_status,
)

from database import (
    get_conversation_history,
)

from companion.state import (
    get_companion_state,
)


# =========================================================
# HISTORY
# =========================================================

def _safe_get_history(
    limit: int = 20,
) -> list[dict[str, Any]]:

    try:
        history = get_conversation_history(limit)

        if isinstance(history, list):
            return history

        return []

    except Exception:
        return []


def _format_history(
    history: list[dict[str, Any]],
) -> str:

    if not history:
        return "No conversation history."

    lines = []

    for item in history:

        if not isinstance(item, dict):
            continue

        role = item.get(
            "role",
            "unknown",
        )

        message = item.get(
            "message",
            "",
        )

        if not message:
            continue

        lines.append(
            f"{str(role).upper()}: {message}"
        )

    return "\n".join(lines)


# =========================================================
# STATE
# =========================================================

def _safe_get_state() -> dict[str, Any]:

    try:

        state = get_companion_state()

        if isinstance(state, dict):
            return state

        return {}

    except Exception:
        return {}


def _format_state(
    state: dict[str, Any],
) -> str:

    if not state:
        return "No companion state."

    lines = []

    for key, value in state.items():

        if value is None:
            continue

        lines.append(
            f"{key}: {value}"
        )

    return "\n".join(lines)


# =========================================================
# COMPATIBILITY PROMPT
# =========================================================

def build_companion_prompt(
    message: str,
    history: list[dict[str, Any]] | None = None,
    state: dict[str, Any] | None = None,
) -> str:
    """
    Compatibility helper.

    The actual production conversation prompt is built by
    conversation.conversation_engine.
    """

    if history is None:
        history = _safe_get_history()

    if state is None:
        state = _safe_get_state()

    return (
        "CURRENT USER MESSAGE:\n"
        f"{message}\n\n"
        "RECENT HISTORY:\n"
        f"{_format_history(history)}\n\n"
        "COMPANION STATE:\n"
        f"{_format_state(state)}"
    )


# =========================================================
# RESPONSE EXTRACTION
# =========================================================

def _extract_response(
    result: Any,
) -> str:

    if isinstance(result, str):
        return result.strip()

    if isinstance(result, dict):

        response = (
            result.get("response")
            or result.get("message")
            or result.get("text")
        )

        if response is not None:
            return str(response).strip()

    return ""


# =========================================================
# LANGUAGE INFORMATION
# =========================================================

def _extract_language_info(
    result: Any,
) -> dict[str, Any] | None:

    if not isinstance(result, dict):
        return None

    language_info = result.get("language")

    if isinstance(language_info, dict):
        return language_info

    return None


# =========================================================
# MAIN COMPANION PROCESSOR
# =========================================================

def process_message(
    message: str,
    session_id: str | None = None,
    language: str | dict[str, Any] | None = None,
    language_info: dict[str, Any] | None = None,
    patient_id: int = 1,
) -> dict[str, Any]:
    """
    Process a message through the unified AI conversation
    pipeline.

    Parameters
    ----------
    message:
        User's message.

    session_id:
        Optional conversation/session identifier.

    language:
        Optional language code or language metadata supplied
        by the client.

    language_info:
        Optional normalized language metadata.

    Important
    ---------
    This function does NOT independently save messages.
    conversation_engine handles persistence exactly once.
    """

    message = (
        str(message).strip()
        if message is not None
        else ""
    )

    if not message:

        return {
            "success": False,
            "response": (
                "I'm here. What would you like to talk about?"
            ),
            "error": "empty_message",
        }

    # -----------------------------------------------------
    # Build arguments for the unified conversation engine
    # -----------------------------------------------------

    conversation_kwargs: dict[str, Any] = {
        "message": message,
        "session_id": session_id,
        "patient_id": patient_id,
    }

    if language is not None:
        conversation_kwargs["language"] = language

    if language_info is not None:
        conversation_kwargs["language_info"] = language_info

    # -----------------------------------------------------
    # Process through ONE unified pipeline
    # -----------------------------------------------------

    try:

        result = process_conversation_message(
            **conversation_kwargs
        )

    except TypeError:
        """
        Backward compatibility.

        If an older conversation_engine.py does not yet accept
        language/language_info, retry using the original API.

        This can be removed once conversation_engine.py has been
        updated to accept language parameters.
        """

        try:

            result = process_conversation_message(
                message=message,
                session_id=session_id,
            )

        except Exception as exc:

            return {
                "success": False,
                "response": (
                    "I'm here with you. "
                    "Let's try that again."
                ),
                "error": str(exc),
            }

    except Exception as exc:

        return {
            "success": False,
            "response": (
                "I'm here with you. "
                "Let's try that again."
            ),
            "error": str(exc),
        }

    # -----------------------------------------------------
    # Normalize response
    # -----------------------------------------------------

    response = _extract_response(result)

    if not response:

        response = (
            "I'm here with you. "
            "What would you like to talk about?"
        )

    # -----------------------------------------------------
    # Preserve the complete result returned by the
    # unified conversation engine
    # -----------------------------------------------------

    if isinstance(result, dict):

        final_result = dict(result)

    else:

        final_result = {
            "success": True
        }

    final_result["response"] = response

    final_result["companion_engine"] = True

    # -----------------------------------------------------
    # Preserve language metadata if returned by the engine
    # -----------------------------------------------------

    detected_language = _extract_language_info(
        final_result
    )

    if detected_language is not None:
        final_result["language"] = detected_language

    elif isinstance(language_info, dict):
        final_result["language"] = language_info

    return final_result


# =========================================================
# CHAT COMPATIBILITY
# =========================================================

def chat(
    message: str,
    session_id: str | None = None,
    language: str | dict[str, Any] | None = None,
    language_info: dict[str, Any] | None = None,
    patient_id: int = 1,
) -> dict[str, Any]:

    return process_message(
        message,
        session_id=session_id,
        language=language,
        language_info=language_info,
        patient_id=patient_id,
    )


# =========================================================
# STATUS
# =========================================================

def get_engine_status() -> dict[str, Any]:

    try:

        conversation_status = (
            get_conversation_engine_status()
        )

    except Exception:

        conversation_status = {}

    return {
        "engine": "companion",
        "success": True,

        "conversation_engine": (
            conversation_status
        ),

        "state_available": True,

        "persistent_history": True,

        "unified_pipeline": True,

        "duplicate_message_writes": False,

        "language_aware": True,

        "supported_language_handling": (
            "delegated_to_conversation_engine"
        ),
    }