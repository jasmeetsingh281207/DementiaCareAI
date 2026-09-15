import json
import mimetypes
from datetime import datetime
from pathlib import Path

from ai.gemini_service import generate, status as gemini_status

from database import execute, fetch_one, fetch_all
from memory.memory_store import (
    get_memory,
    get_memory_media_by_id,
)



def initialize_vision_database():
    """
    Creates a separate table for AI visual analysis.

    We keep analysis separate from memory_media.caption so that:
    - caregiver captions are never overwritten
    - AI analysis can be regenerated
    - multiple analyses can be tracked safely
    """

    execute("""
        CREATE TABLE IF NOT EXISTS memory_media_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_id TEXT NOT NULL UNIQUE,
            memory_id TEXT NOT NULL,
            analysis_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    return True


def _get_mime_type(media):
    """
    Determine MIME type from stored media information.
    """

    file_path = media.get("file_path")

    if file_path:
        mime_type, _ = mimetypes.guess_type(file_path)

        if mime_type:
            return mime_type

    media_type = media.get("media_type")

    if media_type == "photo":
        return "image/jpeg"

    if media_type == "video":
        return "video/mp4"

    raise ValueError("Unable to determine media MIME type.")


def _get_media_kind(media):
    """
    Convert our internal media type into Gemini input type.
    """

    media_type = media.get("media_type")

    if media_type == "photo":
        return "image"

    if media_type == "video":
        return "video"

    raise ValueError("Unsupported media type.")


def _parse_json_response(text):
    """
    Gemini may occasionally wrap JSON in markdown fences.
    Clean those fences before parsing.
    """

    if not text:
        raise ValueError("Gemini returned an empty response.")

    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    try:
        return json.loads(text)

    except json.JSONDecodeError:
        # Try extracting the first JSON object.
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])

        raise ValueError(
            "Gemini returned a response that was not valid JSON."
        )


def _build_analysis_prompt(memory, media):
    """
    Prompt Gemini to describe observable visual information.

    IMPORTANT:
    Gemini must not identify people by face.

    Caregiver-provided:
    - name
    - relationship
    - memory description

    remain the source of truth for identity.
    """

    caregiver_name = memory.get("name") or ""
    relationship = memory.get("relationship") or ""
    description = memory.get("description") or ""
    category = memory.get("category") or ""

    caption = media.get("caption") or ""

    return f"""
You are a visual memory assistant for a dementia-care companion.

Analyze the attached photo or video carefully.

This media belongs to a caregiver-created memory.

Caregiver information:
- Memory category: {category}
- Caregiver-provided name: {caregiver_name}
- Caregiver-provided relationship: {relationship}
- Caregiver description: {description}
- Caregiver caption: {caption}

IMPORTANT SAFETY RULES:

1. Do NOT identify a person by facial recognition.
2. Do NOT claim that someone is a specific named person based on their face.
3. Do NOT infer someone's family relationship from appearance.
4. Do NOT invent names, relationships, locations, dates, or events.
5. Treat caregiver-provided names and relationships as the source of truth.
6. Only describe things that are visibly or clearly observable.
7. If something is uncertain, say so.
8. The purpose is to provide gentle memory cues for a dementia-care companion.

Return ONLY valid JSON in this structure:

{{
    "summary": "A short description of what is visibly shown.",
    "people_count": 0,
    "people_description": [
        "General non-identifying description of people visible."
    ],
    "setting": "Where the scene appears to take place, if observable.",
    "objects": [
        "Important visible objects."
    ],
    "activities": [
        "Visible activities or actions."
    ],
    "event_cues": [
        "Visible clues that may help remember an event."
    ],
    "text_visible": [
        "Any clearly readable text."
    ],
    "visual_memory_cues": [
        "Simple visual cues that could help a dementia patient remember this scene."
    ],
    "uncertainties": [
        "Things that cannot be determined confidently."
    ]
}}
"""


def get_media_analysis(media_id):
    """
    Retrieve previously generated AI analysis.
    """

    row = fetch_one("""
        SELECT
            id,
            media_id,
            memory_id,
            analysis_json,
            created_at,
            updated_at
        FROM memory_media_analysis
        WHERE media_id = ?
    """, (media_id,))

    if not row:
        return None

    result = dict(row)

    try:
        result["analysis"] = json.loads(
            result.get("analysis_json") or "{}"
        )
    except json.JSONDecodeError:
        result["analysis"] = {}

    result.pop("analysis_json", None)

    return result


def analyze_media(media_id, memory_id=None, force=False):
    """
    Analyze one caregiver-uploaded photo/video using Gemini.

    Returns:
        {
            "media_id": ...,
            "memory_id": ...,
            "analysis": {...}
        }
    """

    initialize_vision_database()

    media = get_memory_media_by_id(media_id)

    if not media:
        raise ValueError("Media not found.")

    actual_memory_id = media.get("memory_id")

    if memory_id and actual_memory_id != memory_id:
        raise ValueError(
            "This media does not belong to the specified memory."
        )

    memory_id = actual_memory_id

    memory = get_memory(memory_id)

    if not memory:
        raise ValueError("Memory not found.")

    existing = get_media_analysis(media_id)

    if existing and not force:
        return existing

    file_path = media.get("file_path")

    if not file_path:
        raise ValueError("Media file path is missing.")

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Media file does not exist: {path}"
        )

    mime_type = _get_mime_type(media)
    media_kind = _get_media_kind(media)

    prompt = _build_analysis_prompt(
        memory=memory,
        media=media
    )

    # ``Part.from_bytes`` avoids a Files API dependency and is compatible
    # with the same generate_content API used by conversation and activities.
    try:
        from google.genai import types
        response_text = generate(prompt, contents=[prompt, types.Part.from_bytes(data=path.read_bytes(), mime_type=mime_type)])
    except Exception:
        response_text = None
    if not response_text:
        raise RuntimeError("Vision analysis is unavailable; configure a usable Gemini service and try again.")

    analysis = _parse_json_response(response_text)

    now = datetime.now().isoformat()

    analysis_json = json.dumps(
        analysis,
        ensure_ascii=False
    )

    if existing:
        execute("""
            UPDATE memory_media_analysis
            SET
                memory_id = ?,
                analysis_json = ?,
                updated_at = ?
            WHERE media_id = ?
        """, (
            memory_id,
            analysis_json,
            now,
            media_id
        ))

    else:
        execute("""
            INSERT INTO memory_media_analysis (
                media_id,
                memory_id,
                analysis_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            media_id,
            memory_id,
            analysis_json,
            now,
            now
        ))

    return {
        "media_id": media_id,
        "memory_id": memory_id,
        "analysis": analysis,
        "created_at": existing["created_at"] if existing else now,
        "updated_at": now
    }


def analyze_memory(memory_id, force=False):
    """
    Analyze every photo/video attached to a memory.
    """

    initialize_vision_database()

    memory = get_memory(memory_id)

    if not memory:
        raise ValueError("Memory not found.")

    media_items = memory.get("media", [])

    results = []

    for media in media_items:
        result = analyze_media(
            media_id=media["id"],
            memory_id=memory_id,
            force=force
        )

        results.append(result)

    return {
        "memory_id": memory_id,
        "media_count": len(results),
        "results": results
    }


def get_visual_context(media_id):
    """
    Return a compact text representation of the visual analysis.

    This is useful later when the companion needs to talk naturally
    about a memory.
    """

    result = get_media_analysis(media_id)

    if not result:
        return ""

    analysis = result.get("analysis") or {}

    context_parts = []

    if analysis.get("summary"):
        context_parts.append(
            f"Scene: {analysis['summary']}"
        )

    if analysis.get("setting"):
        context_parts.append(
            f"Setting: {analysis['setting']}"
        )

    if analysis.get("objects"):
        context_parts.append(
            "Objects: " +
            ", ".join(
                str(item)
                for item in analysis["objects"]
            )
        )

    if analysis.get("activities"):
        context_parts.append(
            "Activities: " +
            ", ".join(
                str(item)
                for item in analysis["activities"]
            )
        )

    if analysis.get("event_cues"):
        context_parts.append(
            "Event cues: " +
            ", ".join(
                str(item)
                for item in analysis["event_cues"]
            )
        )

    if analysis.get("visual_memory_cues"):
        context_parts.append(
            "Memory cues: " +
            ", ".join(
                str(item)
                for item in analysis["visual_memory_cues"]
            )
        )

    return "\n".join(context_parts)


def get_all_media_analysis(memory_id):
    """
    Return analysis for every media item belonging to a memory.
    """

    initialize_vision_database()

    rows = fetch_all("""
        SELECT
            id,
            media_id,
            memory_id,
            analysis_json,
            created_at,
            updated_at
        FROM memory_media_analysis
        WHERE memory_id = ?
        ORDER BY created_at ASC
    """, (memory_id,))

    results = []

    for row in rows:
        item = dict(row)

        try:
            item["analysis"] = json.loads(
                item.get("analysis_json") or "{}"
            )
        except json.JSONDecodeError:
            item["analysis"] = {}

        item.pop("analysis_json", None)

        results.append(item)

    return results
