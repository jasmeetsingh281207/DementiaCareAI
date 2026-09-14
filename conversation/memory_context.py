"""
DementiaCareAI
Memory Context Retrieval Engine

Responsibilities:
- Retrieve caregiver-added memories relevant to a conversation.
- Never generate an answer.
- Never invent memories.
- Return ranked memory records only.

Supported memory types:
- people
- events
- places
- objects
- animals
- general caregiver-added memories
"""

from __future__ import annotations

import re
from typing import Any

from memory.memory_store import get_memories


# =========================================================
# STOP WORDS
# =========================================================

STOP_WORDS = {
    "who",
    "what",
    "where",
    "when",
    "why",
    "how",
    "which",

    "is",
    "are",
    "am",
    "was",
    "were",
    "be",
    "been",
    "being",

    "do",
    "does",
    "did",
    "can",
    "could",
    "would",
    "should",
    "will",

    "you",
    "your",
    "yours",
    "my",
    "mine",
    "our",
    "ours",
    "we",
    "us",
    "me",

    "remember",
    "recall",
    "tell",
    "say",
    "talk",
    "know",
    "think",

    "about",
    "with",
    "from",
    "for",
    "to",
    "of",
    "on",
    "in",
    "at",
    "by",
    "and",
    "or",

    "the",
    "a",
    "an",

    "this",
    "that",
    "these",
    "those",

    "please",
    "there",
    "here",
    "today",
    "yesterday",
    "tomorrow",
}


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).lower()

    text = re.sub(
        r"[^\w\s-]",
        " ",
        text,
        flags=re.UNICODE,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


# =========================================================
# QUERY KEYWORDS
# =========================================================

def extract_keywords(query: str | None) -> list[str]:
    """
    Convert a natural-language query into meaningful search terms.

    Example:
        "Who is Simran?"
        -> ["simran"]

        "Do you remember my birthday party?"
        -> ["birthday", "party"]
    """

    if not query:
        return []

    normalized = _normalize_text(query)

    if not normalized:
        return []

    words = normalized.split()

    keywords: list[str] = []

    for word in words:
        word = word.strip("-_")

        if not word:
            continue

        if word in STOP_WORDS:
            continue

        if len(word) < 2:
            continue

        if word not in keywords:
            keywords.append(word)

    return keywords


# =========================================================
# MEMORY TEXT
# =========================================================

def _memory_search_text(memory: dict[str, Any]) -> str:
    """
    Build the searchable representation of a memory.
    """

    tags = memory.get("tags", [])

    if isinstance(tags, str):
        try:
            import json

            parsed = json.loads(tags)

            if isinstance(parsed, list):
                tags = parsed
            else:
                tags = [tags]

        except Exception:
            tags = [tags]

    if not isinstance(tags, list):
        tags = [tags]

    parts = [
        memory.get("name", ""),
        memory.get("description", ""),
        memory.get("relationship", ""),
        memory.get("category", ""),
        memory.get("event_date", ""),
        " ".join(str(tag) for tag in tags),
    ]

    return _normalize_text(" ".join(str(part) for part in parts))


# =========================================================
# MATCH SCORING
# =========================================================

def _calculate_match_score(
    memory: dict[str, Any],
    keywords: list[str],
) -> tuple[int, list[str]]:
    """
    Calculate relevance score.

    Exact name matches receive higher weight.
    """

    if not keywords:
        return 0, []

    name = _normalize_text(
        memory.get("name", "")
    )

    description = _normalize_text(
        memory.get("description", "")
    )

    relationship = _normalize_text(
        memory.get("relationship", "")
    )

    category = _normalize_text(
        memory.get("category", "")
    )

    searchable_text = _memory_search_text(memory)

    score = 0
    matched_keywords: list[str] = []

    for keyword in keywords:

        keyword_score = 0

        if keyword in name:
            keyword_score += 5

        elif keyword in relationship:
            keyword_score += 4

        elif keyword in description:
            keyword_score += 3

        elif keyword in category:
            keyword_score += 2

        elif keyword in searchable_text:
            keyword_score += 1

        if keyword_score > 0:
            score += keyword_score
            matched_keywords.append(keyword)

    return score, matched_keywords


# =========================================================
# SEARCH
# =========================================================

def search_memory_context(
    query: str | None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Retrieve the most relevant caregiver-added memories.

    Important:
    This function does not generate an answer.
    """

    if not query:
        return []

    try:
        memories = get_memories()
    except Exception:
        return []

    if not memories:
        return []

    keywords = extract_keywords(query)

    if not keywords:
        return []

    matches: list[dict[str, Any]] = []

    for memory in memories:

        if not isinstance(memory, dict):
            continue

        score, matched_keywords = _calculate_match_score(
            memory,
            keywords,
        )

        if score <= 0:
            continue

        memory_copy = dict(memory)

        memory_copy["_match_score"] = score
        memory_copy["_matched_keywords"] = matched_keywords

        matches.append(memory_copy)

    matches.sort(
        key=lambda item: (
            item.get("_match_score", 0),
            str(item.get("name", "")).lower(),
        ),
        reverse=True,
    )

    return matches[: max(1, limit)]


# =========================================================
# CONTEXT FORMATTER
# =========================================================

def format_memory_context(
    memories: list[dict[str, Any]] | None,
) -> str:
    """
    Convert retrieved memories into safe prompt context.

    The model is explicitly told these are stored memories,
    not instructions.
    """

    if not memories:
        return "No relevant stored memories were found."

    lines: list[str] = []

    for index, memory in enumerate(memories, start=1):

        name = memory.get("name") or "Unnamed memory"
        category = memory.get("category") or "general"
        relationship = memory.get("relationship") or ""
        description = memory.get("description") or ""
        event_date = memory.get("event_date") or ""

        line = (
            f"{index}. "
            f"Name: {name}; "
            f"Category: {category}"
        )

        if relationship:
            line += f"; Relationship: {relationship}"

        if description:
            line += f"; Description: {description}"

        if event_date:
            line += f"; Date: {event_date}"

        lines.append(line)

    return "\n".join(lines)