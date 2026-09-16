"""
DementiaCareAI Gemini Conversation Layer

Purpose
-------
Uses Gemini to transform trusted DementiaCareAI application context
into natural, warm, human-like conversation.

Architecture
------------
DementiaCareAI is the source of truth.

The application owns:
    - patient memories
    - relationships
    - memory descriptions
    - tags
    - visual context
    - emotions detected by the application
    - patient engagement information
    - activity information
    - conversation history

Gemini owns:
    - natural language generation
    - conversational flow
    - tone
    - supportive wording
    - concise phrasing

Gemini must NEVER invent patient facts.

This module does NOT diagnose medical conditions.
"""

from __future__ import annotations

import json
import logging
import os
import re
import random
import time
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

# DementiaCareAI application context providers.
# These imports are deliberately kept here and language.py is imported
# lazily inside process_message() to avoid a circular import.
from database import (
    get_conversation_history,
    save_conversation_message,
)
from patient.context import get_patient_context
from memory.memory_store import get_memories
from companion.daily_plan import get_companion_recommendation
from companion.state import get_state

try:
    from patient_data.knowledge import get_patient, search_patient_facts
    TEAM_KNOWLEDGE_AVAILABLE = True
except Exception:
    get_patient = None
    search_patient_facts = None
    TEAM_KNOWLEDGE_AVAILABLE = False


# ==========================================================
# ENVIRONMENT
# ==========================================================

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Keep the known-working model for this project.
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)


# ==========================================================
# GEMINI CLIENT
# ==========================================================

_client = None


def get_gemini_client():
    """
    Lazily create and return the Gemini client.
    """

    global _client

    if _client is not None:
        return _client

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. "
            "Add GEMINI_API_KEY to the project's .env file."
        )

    _client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    return _client


# ==========================================================
# SYSTEM INSTRUCTION
# ==========================================================

SYSTEM_INSTRUCTION = """
You are the conversational intelligence layer of DementiaCareAI.

You are speaking with a person who may have memory difficulties.

Your communication should be:

- calm
- warm
- respectful
- patient
- natural
- simple
- reassuring
- human

Your role is NOT to diagnose dementia.
Your role is NOT to act as a doctor.
Do not provide medical diagnosis or unsafe medical instructions.

==========================================================
SOURCE OF TRUTH
==========================================================

The DementiaCareAI application provides trusted context.

The application is the source of truth.

Only use facts explicitly provided in the application context.

NEVER invent:

- names
- family members
- relationships
- dates
- locations
- events
- memories
- personal history
- medical conditions
- diagnoses
- medications
- emotions
- personality traits
- visual details
- activities
- preferences

If information is unavailable, say that you do not have that information.

Do not guess.

==========================================================
CONVERSATION CONTINUITY
==========================================================

The supplied conversation history is important.

Use recent conversation history to understand references such as:

- he
- she
- him
- her
- they
- them
- that person
- this person
- that event
- this event
- tell me more
- what about her
- what about him
- where is she
- who was he
- remind me
- what happened then

When a previous message established a person, event, or memory,
continue naturally from that context.

Do not force the user to repeat information that is already
available in the supplied conversation context.

However, never invent information that is not present.

If a follow-up refers to something that cannot be identified
from the available context, politely say that you are not sure
which person or memory they mean.

==========================================================
MEMORY HANDLING
==========================================================

When trusted memory information is supplied:

Use it naturally.

Do not describe it as:

- a database record
- a memory record
- stored information
- retrieved context
- an application entry
- JSON
- metadata
- match score

Do not expose internal application fields.

For a known person:

Use the supplied relationship when appropriate.

For a known event:

Use the supplied event description.

For supplied visual context:

Use only the supplied visual information.

Never pretend that you personally saw an image unless the
application context explicitly establishes the relevant details.

==========================================================
NATURAL CONVERSATION
==========================================================

Do not answer like a database.

Do not mechanically repeat the person's name.

Do not unnecessarily repeat the same sentence.

Do not begin every answer with:

"I remember..."

Do not use the same response pattern repeatedly.

Vary natural wording while remaining faithful to the facts.

If the user asks a simple question, give a simple answer.

If the user wants more detail, provide more detail using only
available information.

If the user asks a follow-up question, connect it naturally
to the previous conversation.

==========================================================
DEMENTIA-FRIENDLY COMMUNICATION
==========================================================

If the person appears confused:

- stay calm
- reassure gently
- provide known information
- avoid harsh correction
- never say "you are wrong"
- never shame or embarrass the person

If the person appears frustrated:

- slow the conversation down
- acknowledge the difficulty
- offer one simple next step

If the person appears sad:

- respond warmly
- acknowledge their feeling
- do not claim to know exactly how they feel

If the person asks the same question repeatedly:

- answer patiently
- do not complain
- do not point out that they already asked

==========================================================
EMOTION
==========================================================

The application may provide an emotion and confidence value.

Treat that information as trusted application context.

Use it only to adapt tone.

Do not invent additional emotional states.

==========================================================
PATIENT PROFILE
==========================================================

The patient profile is supporting context.

Use it only when relevant.

Never expose internal analytics terminology.

Never describe the profile as a medical assessment.

Never make medical conclusions from it.

==========================================================
VOICE OUTPUT
==========================================================

Responses may be converted to speech.

Therefore:

- use natural spoken sentences
- keep sentences reasonably short
- avoid unnecessary lists
- avoid markdown
- avoid emojis
- avoid excessive punctuation
- avoid technical language
- avoid long paragraphs
- make the response easy to understand when heard aloud

==========================================================
SAFETY
==========================================================

You are a supportive conversational system.

You are not a medical professional.

Do not diagnose conditions.

Do not make medication decisions.

Do not give unsafe medical treatment instructions.

For emergency situations, encourage contacting local emergency
services or a trusted person nearby.

==========================================================
FINAL RULE
==========================================================

Use the DementiaCareAI application context as the source of truth.

Generate the most natural, warm, compassionate response possible.

Never sacrifice factual accuracy for conversational fluency.

If something is unknown, do not invent it.
"""


# ==========================================================
# BASIC SANITIZATION
# ==========================================================

def _clean_text(value: Any) -> str | None:
    """
    Convert a value to clean text.
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def _clean_list(value: Any) -> list[str]:
    """
    Convert supported values into a clean list of strings.
    """

    if not value:
        return []

    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []

    if not isinstance(value, (list, tuple)):
        return []

    result: list[str] = []

    for item in value:
        text = _clean_text(item)

        if text:
            result.append(text)

    return result


# ==========================================================
# MEMORY SANITIZATION
# ==========================================================

def sanitize_memory(
    memory: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """
    Keep only trusted, conversation-relevant memory fields.
    """

    if not isinstance(memory, dict):
        return None

    visual_context = memory.get("visual_context")

    # Some parts of the application may provide visual_context
    # as a list containing one dictionary.
    if isinstance(visual_context, list):

        if visual_context and isinstance(
            visual_context[0],
            dict,
        ):
            visual_context = visual_context[0]
        else:
            visual_context = None

    elif not isinstance(visual_context, dict):
        visual_context = None

    result: dict[str, Any] = {
        "name": _clean_text(
            memory.get("name")
        ),
        "category": _clean_text(
            memory.get("category")
        ),
        "relationship": _clean_text(
            memory.get("relationship")
        ),
        "description": _clean_text(
            memory.get("description")
        ),
        "event_date": _clean_text(
            memory.get("event_date")
        ),
        "tags": _clean_list(
            memory.get("tags")
        ),
        "visual_context": visual_context,
    }

    return {
        key: value
        for key, value in result.items()
        if value not in (
            None,
            "",
            [],
            {},
        )
    }


# ==========================================================
# HISTORY SANITIZATION
# ==========================================================

def sanitize_history(
    history: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    """
    Normalize conversation history.

    Supports both:

        {
            "user": "...",
            "assistant": "..."
        }

    and:

        {
            "message": "...",
            "response": "..."
        }
    """

    if not history:
        return []

    cleaned: list[dict[str, str]] = []

    for item in history[-10:]:

        if not isinstance(item, dict):
            continue

        user_message = _clean_text(
            item.get("user")
            or item.get("message")
        )

        assistant_message = _clean_text(
            item.get("assistant")
            or item.get("response")
        )

        if not user_message:
            continue

        cleaned.append(
            {
                "user": user_message,
                "assistant": assistant_message or "",
            }
        )

    return cleaned


# ==========================================================
# PATIENT PROFILE SANITIZATION
# ==========================================================

def sanitize_patient_profile(
    profile: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Keep patient profile JSON-safe.

    The profile is already generated by the application,
    so we preserve its structure while removing obviously
    unsafe non-serializable values.
    """

    if not isinstance(profile, dict):
        return {}

    try:
        serialized = json.dumps(
            profile,
            ensure_ascii=False,
            default=str,
        )

        result = json.loads(serialized)

        if isinstance(result, dict):
            return result

    except Exception:
        logger.warning(
            "Unable to sanitize patient profile.",
            exc_info=True,
        )

    return {}


# ==========================================================
# CONTEXT BUILDER
# ==========================================================

def build_gemini_context(
    *,
    message: str,
    memories: list[dict[str, Any]] | None = None,
    emotion: str = "neutral",
    emotion_confidence: float = 0.0,
    patient_profile: dict[str, Any] | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    previous_memory: dict[str, Any] | None = None,
    follow_up: bool = False,
    intent: str | None = None,
    language: str = "en",
    language_name: str = "English",
    base_language: str = "en",
) -> dict[str, Any]:
    """
    Build the trusted context sent to Gemini.
    """

    safe_memories: list[dict[str, Any]] = []

    for memory in memories or []:

        safe_memory = sanitize_memory(memory)

        if safe_memory:
            safe_memories.append(safe_memory)

    safe_previous_memory = sanitize_memory(
        previous_memory
    )

    safe_history = sanitize_history(
        conversation_history
    )

    safe_profile = sanitize_patient_profile(
        patient_profile
    )

    cleaned_message = _clean_text(message) or ""

    try:
        safe_confidence = round(
            float(emotion_confidence or 0),
            2,
        )
    except (TypeError, ValueError):
        safe_confidence = 0.0

    context: dict[str, Any] = {
        "current_user_message": cleaned_message,
        "intent": _clean_text(intent) or "general",
        "follow_up": bool(follow_up),
        "emotion": _clean_text(emotion) or "neutral",
        "emotion_confidence": safe_confidence,
        "relevant_memories": safe_memories,
        "previous_memory": safe_previous_memory,
        "patient_profile": safe_profile,
        "recent_conversation": safe_history,
        "language": language,
        "language_name": language_name,
        "base_language": base_language,
        "patient_id": None,
        "team_patient_data": {},
        "relevant_patient_facts": [],
    }

    return context


# ==========================================================
# RESPONSE CLEANING
# ==========================================================

def clean_generated_response(
    response: str | None,
) -> str:
    """
    Clean Gemini output before it reaches the application.
    """

    if not response:
        return ""

    text = str(response).strip()

    # Remove accidental code fences.
    text = re.sub(
        r"^```(?:text|plaintext)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    text = text.strip()

    # Remove obvious assistant/meta prefixes.
    prefixes = (
        "assistant:",
        "ai:",
        "gemini:",
        "response:",
    )

    lower = text.lower()

    for prefix in prefixes:

        if lower.startswith(prefix):
            text = text[len(prefix):].strip()
            break

    # Remove accidental leading/trailing quotation marks.
    if (
        len(text) >= 2
        and text[0] == '"'
        and text[-1] == '"'
    ):
        text = text[1:-1].strip()

    return text


# ==========================================================
# FALLBACK RESPONSE
# ==========================================================

def _looks_like_event_or_activity_name(name: str) -> bool:
    """
    Return True when a memory title is clearly an event/activity rather
    than a person's name. This prevents malformed outputs such as
    "Birthday Celebration is your family."
    """
    if not isinstance(name, str):
        return False
    normalized = " ".join(name.strip().lower().split())
    if not normalized:
        return False
    event_markers = (
        "birthday", "celebration", "party", "wedding", "anniversary",
        "festival", "event", "meeting", "appointment", "reminder",
        "activity", "game", "trip", "vacation", "holiday", "dinner",
        "lunch", "breakfast", "picnic", "function", "ceremony",
        "photo", "video",
    )
    return any(marker in normalized for marker in event_markers)


def generate_fallback_response(
    memories: list[dict[str, Any]] | None = None,
    emotion: str = "neutral",
    previous_memory: dict[str, Any] | None = None,
    follow_up: bool = False,
    message: str | None = None,
    language: str = "en",
) -> str:
    """
    Safe fallback when Gemini cannot be reached.

    This is intentionally conservative.
    """

    memories = memories or []

    # Deterministic small-talk fallback. This must not depend on memories,
    # Gemini availability, or the first item in the memory store.
    normalized_message = " ".join(
        str(message or "").strip().lower().split()
    )

    # Treat whitespace before punctuation as insignificant.
    normalized_message = re.sub(
        r"\s+([?.!,;:])",
        r"\1",
        normalized_message,
    )

    if normalized_message in {
        "hello", "hi", "hey", "hello there", "hi there", "hey there",
    }:
        return "Hello. It is lovely to hear from you. How are you feeling today?"

    if normalized_message in {
        "how are you", "how are you?", "how are you doing",
        "how are you doing?", "how do you feel", "how do you feel?",
    }:
        return "I am doing well, thank you. It is nice to talk with you. How are you feeling today?"

    if normalized_message in {
        "good morning", "good afternoon", "good evening", "good night",
    }:
        return "It is lovely to hear from you. I hope you are having a nice day."

    # Never use an arbitrary stored memory as the fallback answer.
    # A memory may be used only when the caller has explicitly supplied it
    # as relevant (for example, a genuine follow-up).
    memory = None
    if follow_up:
        memory = (
            memories[0]
            if memories
            else previous_memory
        )

    if not memory:

        if emotion == "confusion":
            return (
                "That's okay. We can take it slowly. "
                "I don't have enough information to answer that yet."
            )

        if emotion == "frustration":
            return (
                "Let's take it slowly. "
                "I don't have enough information to answer that yet."
            )

        return (
            "I don't have enough information to answer that yet."
        )

    name = _clean_text(
        memory.get("name")
    )

    relationship = _clean_text(
        memory.get("relationship")
    )

    description = _clean_text(
        memory.get("description")
    )

    if (
        name
        and relationship
        and not _looks_like_event_or_activity_name(name)
    ):
        response = (
            f"{name} is your "
            f"{relationship.lower()}."
        )

    elif name and description:

        response = (
            f"{name}. "
            f"{description}."
        )

    elif name and _looks_like_event_or_activity_name(name):
        response = (
            "I have that information, but I don't have enough "
            "personal details to describe who it is."
        )

    elif name:
        response = (
            f"I remember {name}."
        )

    elif description:

        response = description

    else:

        response = (
            "I have some information about that, "
            "but not enough to explain it right now."
        )

    if emotion == "confusion":

        return (
            "That's okay. "
            + response
        )

    if emotion == "frustration":

        return (
            "Let's take it slowly. "
            + response
        )

    return response


def _reject_known_malformed_relationship_response(response: str) -> str:
    """Reject the known malformed event-as-relationship response."""
    if not isinstance(response, str):
        return ""
    cleaned = " ".join(response.strip().split())
    lowered = cleaned.casefold()
    patterns = (
        "birthday celebration is your family",
        "birthday celebration is your relative",
        "birthday celebration is your mother",
        "birthday celebration is your father",
        "birthday celebration is your sister",
        "birthday celebration is your brother",
        "birthday celebration. a family birthday event memory",
        "birthday celebration a family birthday event memory",
    )
    if any(pattern in lowered for pattern in patterns):
        logger.warning("Rejected malformed relationship response: %s", cleaned)
        return ""
    return cleaned


# ==========================================================
# GEMINI RETRY / ERROR HANDLING
# ==========================================================

# The google-genai Python SDK already retries many transient errors.
# These application-level retries run only after an exception escapes
# the SDK, giving the request one more controlled chance before the
# application falls back locally.
GEMINI_TRANSIENT_RETRIES = 2
GEMINI_RETRY_BASE_SECONDS = 1.5
GEMINI_RETRY_MAX_SECONDS = 8.0


def _gemini_error_status(exc: Exception) -> int | None:
    """Best-effort extraction of an HTTP status from a Gemini exception."""

    for attr in ("status_code", "code", "http_status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())

    text = str(exc).lower()

    # Common google-genai exception formats.
    for code in (503, 504, 429, 408):
        if re.search(rf"\b{code}\b", text):
            return code

    if "resource_exhausted" in text or "rate limit" in text or "too many requests" in text:
        return 429

    if "unavailable" in text or "service_unavailable" in text:
        return 503

    if "deadline_exceeded" in text or "timed out" in text or "timeout" in text:
        return 504

    return None


def _gemini_is_transient(exc: Exception) -> bool:
    """Return True only for errors where another attempt can reasonably help."""

    status = _gemini_error_status(exc)
    if status in {408, 429, 500, 502, 503, 504}:
        return True

    text = str(exc).lower()

    return any(
        marker in text
        for marker in (
            "resource_exhausted",
            "rate_limit_exceeded",
            "too_many_requests",
            "service_unavailable",
            "temporarily unavailable",
        )
    )


def _gemini_retry_delay(attempt: int) -> float:
    """Exponential backoff with small jitter, capped for interactive chat."""

    delay = min(
        GEMINI_RETRY_MAX_SECONDS,
        GEMINI_RETRY_BASE_SECONDS * (2 ** max(0, attempt - 1)),
    )
    return delay + random.uniform(0.0, 0.5)


def _response_finish_reason(response: Any) -> str:
    """Return Gemini's candidate finish reason as a normalized string."""
    try:
        candidates = getattr(response, "candidates", None) or []
        if candidates:
            reason = getattr(candidates[0], "finish_reason", None)
            if reason is not None:
                return str(getattr(reason, "name", reason)).upper()
    except Exception:
        pass
    return ""


def _response_needs_completion(response: Any, text: str) -> bool:
    """Reject output that is very likely truncated before showing it to users."""
    reason = _response_finish_reason(response)
    if any(token in reason for token in ("MAX_TOKENS", "LENGTH")):
        return True

    cleaned = clean_generated_response(text)
    if not cleaned:
        return True

    # The model is explicitly instructed to return spoken sentences. A missing
    # terminal mark is a strong signal of truncation for this application.
    terminal = ".!?।॥。！？…"
    if cleaned[-1] not in terminal:
        return True

    return False


def _gemini_retry_label(exc: Exception) -> str:
    """Return a safe human-readable classification for logs."""

    status = _gemini_error_status(exc)

    if status == 503:
        return "503 service unavailable"

    if status == 429:
        return "429 rate/quota limit"

    if status == 504:
        return "504 timeout"

    if status == 408:
        return "408 request timeout"

    if status in {500, 502}:
        return f"{status} transient server error"

    return "transient Gemini error"


def _generate_gemini_content_with_retry(
    client: Any,
    prompt: str,
) -> Any:
    """Call Gemini and retry escaped transient 503/429-style failures."""

    last_exc: Exception | None = None

    for attempt in range(0, GEMINI_TRANSIENT_RETRIES + 1):
        try:
            return client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.35,
                    max_output_tokens=2048,
                ),
            )

        except Exception as exc:
            last_exc = exc

            if not _gemini_is_transient(exc):
                raise

            if attempt >= GEMINI_TRANSIENT_RETRIES:
                logger.error(
                    "Gemini request failed after %s attempt(s): %s",
                    attempt + 1,
                    _gemini_retry_label(exc),
                )
                raise

            delay = _gemini_retry_delay(attempt + 1)
            logger.warning(
                "Gemini %s. Retrying in %.1f seconds (attempt %s/%s).",
                _gemini_retry_label(exc),
                delay,
                attempt + 1,
                GEMINI_TRANSIENT_RETRIES,
            )
            time.sleep(delay)

    # Defensive guard; the loop either returns or raises.
    if last_exc is not None:
        raise last_exc

    raise RuntimeError("Gemini request failed without an exception.")


# ==========================================================
# MAIN GEMINI RESPONSE FUNCTION
# ==========================================================

def generate_gemini_response(
    message: str = "",
    context: dict[str, Any] | None = None,
) -> str:
    """
    Generate a natural response using Gemini.

    IMPORTANT:
    This signature is intentionally compatible with the
    current conversation_engine.py:

        generate_gemini_response(
            message=message,
            context=context,
        )

    The application context remains the source of truth.
    """

    message = _clean_text(message) or ""

    if not message:
        return (
            "I'm here with you. "
            "What would you like to talk about?"
        )

    # ------------------------------------------------------
    # Normalize incoming context
    # ------------------------------------------------------

    raw_context = (
        context
        if isinstance(context, dict)
        else {}
    )

    memories = raw_context.get(
        "relevant_memories",
        [],
    )

    if not isinstance(memories, list):
        memories = []

    emotion = (
        _clean_text(
            raw_context.get("emotion")
        )
        or "neutral"
    )

    emotion_confidence = raw_context.get(
        "emotion_confidence",
        0.0,
    )

    patient_profile = raw_context.get(
        "patient_profile",
        {},
    )

    conversation_history = raw_context.get(
        "conversation_history",
        raw_context.get(
            "recent_conversation",
            [],
        ),
    )

    if not isinstance(
        conversation_history,
        list,
    ):
        conversation_history = []

    previous_memory = raw_context.get(
        "previous_memory"
    )

    follow_up = bool(
        raw_context.get(
            "follow_up",
            False,
        )
    )

    intent = (
        _clean_text(
            raw_context.get("intent")
        )
        or "general"
    )

    # Language metadata is supplied by language.py/app.py.
    # Keep this module independent from the language detector so
    # there is no circular import.
    language = (
        _clean_text(raw_context.get("language"))
        or "en"
    )
    language_name = (
        _clean_text(raw_context.get("language_name"))
        or "English"
    )
    base_language = (
        _clean_text(raw_context.get("base_language"))
        or language
    )

    # ------------------------------------------------------
    # Rebuild a strictly sanitized context
    # ------------------------------------------------------

    safe_context = build_gemini_context(
        message=message,
        memories=memories,
        emotion=emotion,
        emotion_confidence=emotion_confidence,
        patient_profile=patient_profile,
        conversation_history=conversation_history,
        previous_memory=previous_memory,
        follow_up=follow_up,
        intent=intent,
        language=language,
        language_name=language_name,
        base_language=base_language,
    )

    # ------------------------------------------------------
    # Fallback
    # ------------------------------------------------------

    fallback = generate_fallback_response(
        memories=safe_context[
            "relevant_memories"
        ],
        emotion=safe_context[
            "emotion"
        ],
        previous_memory=safe_context.get(
            "previous_memory"
        ),
        follow_up=safe_context.get(
            "follow_up",
            False,
        ),
        message=message,
        language=language,
    )

    # ------------------------------------------------------
    # Gemini request
    # ------------------------------------------------------

    try:

        client = get_gemini_client()

        trusted_context = json.dumps(
            safe_context,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        prompt = f"""
TRUSTED DEMENTIACAREAI APPLICATION CONTEXT

The following information comes from the DementiaCareAI
application and is the source of truth.

Do not invent facts that are not present here.

{trusted_context}


CURRENT USER MESSAGE

{message}


RESPONSE TASK

LANGUAGE REQUIREMENT

Requested language: {language_name} ({language})
Base language: {base_language}

Respond naturally to the person's current message.
Respond only in the requested language; use English only when English is requested.

Important rules:

1. Use only facts contained in the trusted application context.
2. Never invent a person, relationship, event, date, location,
   memory, medical fact, emotion, or visual detail.
3. Use recent conversation history to understand follow-up
   questions and pronouns.
4. If previous_memory identifies the subject of a follow-up,
   continue naturally from that memory.
5. If the subject cannot be determined, say so naturally rather
   than guessing.
6. Answer the actual question directly.
7. Be warm, patient, and dementia-friendly.
8. Keep the response concise.
9. Make the response comfortable for text-to-speech.
10. Do not mention the application context.
11. Do not mention JSON.
12. Do not mention databases.
13. Do not mention internal fields.
14. Do not mention match scores.
15. Do not mention Gemini.
16. Do not describe yourself as an AI unless directly necessary.
17. Do not diagnose or provide medical advice.
18. Do not use markdown.
19. Do not use bullet points unless the user explicitly asks for them.
20. Return only the spoken response.
21. Always finish the response as a complete, natural sentence. Never stop mid-sentence, mid-phrase, or with an unfinished thought.
22. Prefer 1 to 3 short sentences rather than a fragment.
23. Do not end with an incomplete phrase merely to keep the response concise.

If the person asks for information that is not available,
say that you do not have that information yet.

If the person asks a follow-up about a known person or memory,
answer from the supplied previous memory and conversation history.
"""

        response = _generate_gemini_content_with_retry(
            client=client,
            prompt=prompt,
        )

        generated = clean_generated_response(
            getattr(response, "text", "")
        )

        # Never expose a response that Gemini itself reports as length-limited
        # or that otherwise looks like a sentence cut off mid-thought. Retry
        # with a focused completion instruction. This applies identically to
        # all supported languages because the validator is language-agnostic.
        if _response_needs_completion(response, generated):
            logger.warning(
                "Gemini response appears incomplete; requesting a complete response retry."
            )
            completion_prompt = prompt + """

IMPORTANT COMPLETION CHECK:
The previous generation was incomplete or ended before the thought was finished.
Generate the answer again from the beginning. Return only a complete, natural response
in the requested language. Use 1 to 3 short sentences. End with a complete sentence and
terminal punctuation. Never stop at a partial word, phrase, or unfinished thought.
"""
            response = _generate_gemini_content_with_retry(
                client=client,
                prompt=completion_prompt,
            )
            generated = clean_generated_response(
                getattr(response, "text", "")
            )

        if not generated or _response_needs_completion(response, generated):
            logger.warning(
                "Gemini did not return a confidently complete response; using safe fallback."
            )
            return fallback

        return generated

    except Exception as exc:

        status = _gemini_error_status(exc)

        if status == 503:
            logger.warning(
                "Gemini remained unavailable after retrying. "
                "Using local fallback response."
            )
        elif status == 429:
            logger.warning(
                "Gemini rate/quota limit remained active after retrying. "
                "Using local fallback response."
            )
        else:
            logger.exception(
                "Gemini response generation failed: %s",
                exc,
            )

        return fallback


# ==========================================================
# OPTIONAL BACKWARD-COMPATIBILITY FUNCTION
# ==========================================================

def generate_response(
    message: str,
    context: dict[str, Any] | None = None,
) -> str:
    """
    Compatibility alias for code that may call
    generate_response().
    """

    return generate_gemini_response(
        message=message,
        context=context,
    )

# ==========================================================
# UNIFIED COMPANION MESSAGE PIPELINE
# ==========================================================

def _resolve_language_context(
    language: str | dict[str, Any] | None,
    language_info: dict[str, Any] | None,
    message: str,
) -> dict[str, Any]:
    """
    Resolve language metadata without using Gemini.

    The application normally supplies an already-resolved language.
    If it does not, language.py performs local detection.
    """
    resolved_info: dict[str, Any] = {}

    if isinstance(language_info, dict):
        resolved_info.update(language_info)

    # A language argument may itself be the metadata dictionary.
    if isinstance(language, dict):
        for key, value in language.items():
            if key not in resolved_info or not resolved_info.get(key):
                resolved_info[key] = value
        code = (
            resolved_info.get("code")
            or resolved_info.get("language")
            or resolved_info.get("base_language")
        )
    else:
        code = language

    if not isinstance(code, str) or not code.strip():
        # Lazy import is intentional: language.py imports the conversation
        # layer for explicit translation support.
        from language import detect_language, get_language, normalize_language

        detected = detect_language(message)

        if isinstance(detected, dict):
            code = (
                detected.get("code")
                or detected.get("language")
                or detected.get("detected_language")
            )
        else:
            code = detected

        if isinstance(code, str):
            code = normalize_language(code)

        if isinstance(detected, dict):
            for key, value in detected.items():
                if key not in resolved_info or not resolved_info.get(key):
                    resolved_info[key] = value

        if isinstance(code, str) and code:
            try:
                canonical = get_language(code)
                if isinstance(canonical, dict):
                    for key, value in canonical.items():
                        if key not in resolved_info or not resolved_info.get(key):
                            resolved_info[key] = value
            except Exception:
                pass

    if not isinstance(code, str) or not code.strip():
        code = "en"

    code = code.strip().lower()

    resolved_info["code"] = code
    resolved_info["language"] = code
    resolved_info.setdefault("base_language", code)
    resolved_info.setdefault("name", "English" if code == "en" else code)
    resolved_info.setdefault("native_name", resolved_info["name"])
    resolved_info.setdefault("speech_locale", "en-IN" if code == "en" else code)
    resolved_info.setdefault("is_hinglish", code == "hinglish")

    if code == "hinglish":
        resolved_info["base_language"] = "hi"
        resolved_info["speech_locale"] = "hi-IN"
        resolved_info["is_hinglish"] = True

    return resolved_info


def _extract_emotion(context: dict[str, Any]) -> tuple[str, float]:
    """Extract trusted emotion information safely."""
    emotion = _clean_text(context.get("emotion")) or "neutral"

    try:
        confidence = round(
            float(context.get("emotion_confidence", 0.0) or 0.0),
            2,
        )
    except (TypeError, ValueError):
        confidence = 0.0

    return emotion, confidence


def _is_casual_message(message: str) -> bool:
    """Return True for greetings/small-talk that should not surface memories."""
    normalized = " ".join((message or "").strip().lower().split())
    if not normalized:
        return True

    casual_phrases = {
        "hello",
        "hi",
        "hey",
        "hello there",
        "hi there",
        "hey there",
        "good morning",
        "good afternoon",
        "good evening",
        "good night",
        "how are you",
        "how are you?",
        "how are you doing",
        "how are you doing?",
        "how do you feel",
        "how do you feel?",
        "what are you doing",
        "what are you doing?",
    }
    return normalized in casual_phrases


def _memory_matches_message(
    memory: dict[str, Any],
    message: str,
) -> bool:
    """Conservatively decide whether a memory is relevant to this turn."""
    if not isinstance(memory, dict):
        return False

    if _is_casual_message(message):
        return False

    message_words = set(re.findall(r"[a-z0-9]+", (message or "").lower()))
    if not message_words:
        return False

    fields = (
        memory.get("name"),
        memory.get("category"),
        memory.get("relationship"),
        memory.get("description"),
        memory.get("event_date"),
        " ".join(memory.get("tags", []))
        if isinstance(memory.get("tags"), list)
        else memory.get("tags"),
    )
    memory_text = " ".join(
        str(value).lower()
        for value in fields
        if value
    )
    memory_words = set(re.findall(r"[a-z0-9]+", memory_text))

    # Require a meaningful lexical overlap; do not expose the first stored
    # memory merely because it exists.
    return bool(message_words & memory_words)


def _load_team_patient_knowledge(message: str, patient_id: int = 1) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load trusted read-only facts from the team database without breaking chat."""
    if not TEAM_KNOWLEDGE_AVAILABLE or get_patient is None or search_patient_facts is None:
        return {}, []
    try:
        patient = get_patient(patient_id) or {}
    except Exception:
        logger.warning("Unable to load team patient data.", exc_info=True)
        patient = {}
    try:
        facts = search_patient_facts(message, patient_id=patient_id) or []
    except Exception:
        logger.warning("Unable to search team patient data.", exc_info=True)
        facts = []
    return (
        patient if isinstance(patient, dict) else {},
        facts if isinstance(facts, list) else [],
    )


def _answer_from_team_patient_data(
    message: str,
    patient_data: dict[str, Any],
    facts: list[dict[str, Any]],
    language: str = "en",
) -> str | None:
    """Answer high-confidence personal questions directly from trusted team DB facts."""
    text = " ".join((message or "").strip().lower().split())

    def has_any(*terms: str) -> bool:
        return any(term.lower() in text for term in terms)

    preferred_name = patient_data.get("preferred_name") or ""
    full_name = patient_data.get("full_name") or preferred_name
    if has_any("what is my name", "what is my full name", "what's my name", "who am i", "my name", "my full name", "मेरा नाम", "मेरा पूरा नाम", "আমার নাম", "আমার পুরো নাম", "ਮੇਰਾ ਨਾਮ", "ਮੇਰਾ ਪੂਰਾ ਨਾਮ", "என் பெயர்", "என் முழு பெயர்"):
        if not full_name:
            return None
        if language == "hi":
            if preferred_name and preferred_name != full_name:
                return f"आपका नाम {full_name} है। परिवार आपको {preferred_name} कहता है।"
            return f"आपका नाम {full_name} है।"
        if language == "bn":
            return f"আপনার নাম {full_name}।"
        if language == "pa":
            return f"ਤੁਹਾਡਾ ਨਾਮ {full_name} ਹੈ।"
        if language == "ta":
            return f"உங்கள் பெயர் {full_name}."
        return f"Your name is {full_name}."

    if has_any("what does my family call me", "what does family call me", "my nickname", "family nickname", "मुझे क्या कहते हैं", "परिवार मुझे", "আমাকে কী বলে", "ਪਰਿਵਾਰ ਮੈਨੂੰ", "என்னை என்ன அழைப்பார்கள்"):
        if not preferred_name:
            return None
        if language == "hi": return f"आपका परिवार आपको {preferred_name} कहता है।"
        if language == "bn": return f"আপনার পরিবার আপনাকে {preferred_name} বলে।"
        if language == "pa": return f"ਤੁਹਾਡਾ ਪਰਿਵਾਰ ਤੁਹਾਨੂੰ {preferred_name} ਕਹਿੰਦਾ ਹੈ।"
        if language == "ta": return f"உங்கள் குடும்பம் உங்களை {preferred_name} என்று அழைக்கிறது."
        return f"Your family calls you {preferred_name}."

    family = [
        item.get("data", {})
        if isinstance(item, dict) and item.get("type") == "family_member"
        else item
        for item in facts
    ] if isinstance(facts, list) else []

    def find_relation(relation: str):
        wanted = relation.casefold()
        for item in family:
            if isinstance(item, dict) and str(item.get("relation", "")).casefold() == wanted:
                return item
        return None

    for relation, phrases, labels in [
        ("Daughter", ("my daughter", "who is my daughter", "daughter", "मेरी बेटी", "बेटी", "আমার মেয়ে", "মেয়ে", "ਮੇਰੀ ਧੀ", "ਧੀ", "என் மகள்", "மகள்"), ("बेटी", "মেয়ে", "ਧੀ", "மகள்")),
        ("Grandson", ("my grandson", "who is my grandson", "grandson", "मेरा पोता", "पोता", "আমার নাতি", "নাতি", "ਮੇਰਾ ਪੋਤਾ", "ਪੋਤਾ", "என் பேரன்", "பேரன்"), ("पोता", "নাতি", "ਪੋਤਾ", "பேரன்")),
        ("Son", ("my son", "who is my son", "son", "मेरा बेटा", "बेटा", "আমার ছেলে", "ছেলে", "ਮੇਰਾ ਪੁੱਤਰ", "ਪੁੱਤਰ", "என் மகன்", "மகன்"), ("बेटा", "ছেলে", "ਪੁੱਤਰ", "மகன்")),
        ("Sister", ("my sister", "who is my sister", "sister", "मेरी बहन", "बहन", "আমার বোন", "বোন", "ਮੇਰੀ ਭੈਣ", "ਭੈਣ", "என் சகோதரி", "சகோதரி"), ("बहन", "বোন", "ਭੈਣ", "சகோதரி")),
    ]:
        if has_any(*phrases):
            person = find_relation(relation)
            if not person:
                return None
            name = person.get("name")
            if not name:
                return None
            if relation == "Daughter":
                if language == "hi": return f"आपकी बेटी का नाम {name} है।"
                if language == "bn": return f"আপনার মেয়ের নাম {name}।"
                if language == "pa": return f"ਤੁਹਾਡੀ ਧੀ ਦਾ ਨਾਮ {name} ਹੈ।"
                if language == "ta": return f"உங்கள் மகளின் பெயர் {name}."
                return f"Your daughter's name is {name}."
            if relation == "Son":
                if language == "hi": return f"आपके बेटे का नाम {name} है।"
                if language == "bn": return f"আপনার ছেলের নাম {name}।"
                if language == "pa": return f"ਤੁਹਾਡੇ ਪੁੱਤਰ ਦਾ ਨਾਮ {name} ਹੈ।"
                if language == "ta": return f"உங்கள் மகனின் பெயர் {name}."
                return f"Your son's name is {name}."
            if relation == "Grandson":
                if language == "hi": return f"आपके पोते का नाम {name} है।"
                if language == "bn": return f"আপনার নাতির নাম {name}।"
                if language == "pa": return f"ਤੁਹਾਡੇ ਪੋਤੇ ਦਾ ਨਾਮ {name} ਹੈ।"
                if language == "ta": return f"உங்கள் பேரனின் பெயர் {name}."
                return f"Your grandson's name is {name}."
            if language == "hi": return f"आपकी बहन का नाम {name} है।"
            if language == "bn": return f"আপনার বোনের নাম {name}।"
            if language == "pa": return f"ਤੁਹਾਡੀ ਭੈਣ ਦਾ ਨਾਮ {name} ਹੈ।"
            if language == "ta": return f"உங்கள் சகோதரியின் பெயர் {name}."
            return f"Your sister's name is {name}."

    if has_any("my medicine", "my medication", "what medicine", "which medicine", "medicine do i take", "medication do i take", "दवाई", "दवा", "मेरी दवाई", "আমার ওষুধ", "ওষুধ", "ਮੇਰੀ ਦਵਾਈ", "ਦਵਾਈ", "என் மருந்து", "மருந்து"):
        medications = patient_data.get("medications")
        medication = medications[0] if isinstance(medications, list) and medications else None
        if medication is None:
            medication = next((x for x in family if isinstance(x, dict) and (x.get("medicine_name") or x.get("medication_name"))), None)
        if not medication:
            return None
        name = medication.get("medicine_name") or medication.get("medication_name")
        dosage = medication.get("dosage") or ""
        instructions = medication.get("instructions") or ""
        if not name:
            return None
        if language == "hi":
            answer = f"आपकी दवाई {name}"
            if dosage: answer += f", {dosage}"
            if instructions: answer += f"। निर्देश: {instructions}."
            else: answer += "।"
            return answer
        if language == "bn":
            answer = f"আপনার ওষুধ {name}"
            if dosage: answer += f", {dosage}"
            if instructions: answer += f"। নির্দেশনা: {instructions}."
            else: answer += "।"
            return answer
        if language == "pa":
            answer = f"ਤੁਹਾਡੀ ਦਵਾਈ {name}"
            if dosage: answer += f", {dosage}"
            if instructions: answer += f"। ਹਦਾਇਤ: {instructions}."
            else: answer += "।"
            return answer
        if language == "ta":
            answer = f"உங்கள் மருந்து {name}"
            if dosage: answer += f", {dosage}"
            if instructions: answer += f". வழிமுறை: {instructions}."
            else: answer += "."
            return answer
        answer = f"Your medicine is {name}"
        if dosage: answer += f", {dosage}"
        if instructions: answer += f". Instructions: {instructions}."
        else: answer += "."
        return answer

    if has_any("graduation", "graduate", "iit roorkee", "roorkee", "ग्रेजुएशन", "स्नातक", "আইআইটি রুরকি", "গ্র্যাজুয়েশন", "ਆਈਆਈਟੀ ਰੁੜਕੀ", "ਗ੍ਰੈਜੂਏਸ਼ਨ", "ஐஐடி ரூர்க்கி", "பட்டமளிப்பு"):
        memory = next((x for x in family if isinstance(x, dict) and ("iit roorkee" in str(x.get("title", "")).lower() or "roorkee" in str(x.get("location", "")).lower())), None)
        if not memory:
            return None
        title = memory.get("title") or "IIT Roorkee graduation"
        year = memory.get("year")
        if language == "hi": return f"आपकी यादों में {title}" + (f", {year} में" if year else "") + " दर्ज है।"
        if language == "bn": return f"আপনার স্মৃতিতে {title}" + (f", {year} সালে" if year else "") + " আছে।"
        if language == "pa": return f"ਤੁਹਾਡੀਆਂ ਯਾਦਾਂ ਵਿੱਚ {title}" + (f", {year} ਵਿੱਚ" if year else "") + " ਦਰਜ ਹੈ।"
        if language == "ta": return f"உங்கள் நினைவுகளில் {title}" + (f", {year} ஆம் ஆண்டு" if year else "") + " பதிவு செய்யப்பட்டுள்ளது."
        return f"Your memories include {title}" + (f" in {year}" if year else "") + "."

    return None


def _build_runtime_context(
    message: str,
    language_info: dict[str, Any],
    patient_id: int = 1,
) -> dict[str, Any]:
    """
    Gather trusted application context for one companion turn.
    """
    try:
        memories = get_memories()
    except Exception:
        logger.warning("Unable to load memories.", exc_info=True)
        memories = []

    if not isinstance(memories, list):
        memories = []

    try:
        patient_profile = get_patient_context()
    except Exception:
        logger.warning("Unable to load patient context.", exc_info=True)
        patient_profile = {}

    try:
        history = get_conversation_history(limit=10)
    except Exception:
        logger.warning(
            "Unable to load conversation history.",
            exc_info=True,
        )
        history = []

    if not isinstance(history, list):
        history = []

    try:
        companion_state = get_state()
    except Exception:
        logger.warning("Unable to load companion state.", exc_info=True)
        companion_state = {}

    try:
        recommendation = get_companion_recommendation()
    except Exception:
        logger.warning(
            "Unable to load companion recommendation.",
            exc_info=True,
        )
        recommendation = {}

    # Keep only trusted fields, and only expose memories that are relevant
    # to the current turn. Casual greetings must not surface unrelated events.
    safe_memories = []
    for memory in memories:
        safe_memory = sanitize_memory(memory)
        if safe_memory and _memory_matches_message(safe_memory, message):
            safe_memories.append(safe_memory)

    safe_history = sanitize_history(history)
    safe_profile = sanitize_patient_profile(patient_profile)

    previous_memory = (
        safe_memories[0]
        if safe_memories
        else None
    )

    # The existing context builder is the final sanitizer.
    context = build_gemini_context(
        message=message,
        memories=safe_memories,
        emotion="neutral",
        emotion_confidence=0.0,
        patient_profile=safe_profile,
        conversation_history=safe_history,
        previous_memory=previous_memory,
        follow_up=False,
        intent="general",
        language=language_info.get("code", "en"),
        language_name=language_info.get(
            "name",
            language_info.get("native_name", "English"),
        ),
        base_language=language_info.get(
            "base_language",
            language_info.get("code", "en"),
        ),
    )

    # These are useful application facts for future prompt/context use.
    # Keep them separate from the strict context schema so the Gemini
    # function can decide what is appropriate to expose.
    context["companion_state"] = companion_state
    context["companion_recommendation"] = recommendation
    context["patient_id"] = patient_id

    team_patient_data, relevant_patient_facts = _load_team_patient_knowledge(
        message, patient_id=patient_id
    )
    context["team_patient_data"] = team_patient_data
    context["relevant_patient_facts"] = relevant_patient_facts

    return context


def process_message(
    message: str,
    session_id: str | None = None,
    language: str | dict[str, Any] | None = None,
    language_info: dict[str, Any] | None = None,
    patient_id: int = 1,
) -> dict[str, Any]:
    """
    Unified companion conversation entry point.

    Contract used by companion.engine/app.py:
        process_message(
            message,
            session_id=session_id,
            language=language,
            language_info=language_info,
        )

    Responsibilities:
    - validate the message
    - resolve language locally
    - load trusted application context
    - call Gemini exactly once through generate_gemini_response()
      unless transient retry handling is needed inside that function
    - persist the user and assistant messages exactly once
    - return a stable API dictionary

    session_id is accepted for API compatibility. The current database
    conversation store exposes a single active conversation history and
    does not accept a session_id argument, so it is not passed into the
    database layer.
    """
    cleaned_message = _clean_text(message)

    if not cleaned_message:
        raise ValueError("Message is required.")

    if len(cleaned_message) > 2000:
        raise ValueError("Message is too long.")

    resolved_language_info = _resolve_language_context(
        language=language,
        language_info=language_info,
        message=cleaned_message,
    )

    context = _build_runtime_context(
        message=cleaned_message,
        language_info=resolved_language_info,
        patient_id=patient_id,
    )

    # Preserve the selected language as the authoritative generation context.
    context["language"] = resolved_language_info.get("code", "en")
    context["language_name"] = resolved_language_info.get(
        "name", resolved_language_info.get("native_name", "English")
    )
    context["base_language"] = resolved_language_info.get(
        "base_language", context["language"]
    )

    # High-confidence personal facts are answered directly from the trusted
    # team database. Gemini is used only when no deterministic answer exists.
    database_answer = _answer_from_team_patient_data(
        message=cleaned_message,
        patient_data=context.get("team_patient_data", {}),
        facts=context.get("relevant_patient_facts", []),
        language=context.get("language", "en"),
    )

    # Persist the patient message once, before generation.
    try:
        save_conversation_message(
            role="user",
            message=cleaned_message,
        )
    except Exception:
        logger.warning(
            "Unable to persist patient message.",
            exc_info=True,
        )

    if database_answer:
        response_text = database_answer
        database_answer_used = True
    else:
        response_text = generate_gemini_response(
            message=cleaned_message,
            context=context,
        )
        database_answer_used = False

    response_text = clean_generated_response(
        response_text
    )

    response_text = _reject_known_malformed_relationship_response(
        response_text
    )

    if not response_text:
        response_text = generate_fallback_response(
            memories=context.get("relevant_memories", []),
            emotion=context.get("emotion", "neutral"),
            previous_memory=context.get("previous_memory"),
            follow_up=bool(context.get("follow_up", False)),
            message=cleaned_message,
            language=context.get("language", "en"),
        )

    # Persist the assistant response once.
    try:
        save_conversation_message(
            role="assistant",
            message=response_text,
        )
    except Exception:
        logger.warning(
            "Unable to persist assistant message.",
            exc_info=True,
        )

    return {
        "success": True,
        "response": response_text,
        "message": response_text,
        "session_id": session_id,
        "language": resolved_language_info.get("code", "en"),
        "language_name": resolved_language_info.get(
            "name",
            resolved_language_info.get("native_name", "English"),
        ),
        "base_language": resolved_language_info.get(
            "base_language",
            resolved_language_info.get("code", "en"),
        ),
        "speech_locale": resolved_language_info.get(
            "speech_locale",
            "en-IN",
        ),
        "detected_language": resolved_language_info.get(
            "code",
            "en",
        ),
        "is_hinglish": bool(
            resolved_language_info.get(
                "is_hinglish",
                False,
            )
        ),
        "local_detection": bool(
            resolved_language_info.get(
                "local_detection",
                False,
            )
        ),
        "database_answer_used": database_answer_used,
        "patient_id": patient_id,
    }


def get_engine_status() -> dict[str, Any]:
    """
    Return conversation-engine health without making a Gemini request.
    """
    configured = bool(GEMINI_API_KEY)

    return {
        "available": True,
        "engine": "conversation_engine",
        "gemini_configured": configured,
        "gemini_model": GEMINI_MODEL,
        "local_fallback": True,
        "transient_retry_enabled": True,
        "transient_retries": GEMINI_TRANSIENT_RETRIES,
        "multilingual_context": True,
        "local_language_detection": True,
        "team_patient_database": TEAM_KNOWLEDGE_AVAILABLE,
        "team_patient_database_read_only": True,
    }

