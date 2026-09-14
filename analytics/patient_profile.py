"""
DementiaCareAI
Patient Profile & Caregiver Intelligence Analytics

Production analytics layer.

This module converts application data into a structured,
caregiver-facing patient profile.

IMPORTANT:
- This is application analytics.
- It is NOT a medical assessment.
- It does NOT diagnose dementia or any other condition.
- It does NOT infer medical conclusions.
- Missing data is represented as unavailable/empty data.
"""

from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from typing import Any

from database import (
    fetch_all,
    fetch_one,
)

logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTS
# ============================================================

TODAY = date.today()

DEFAULT_HISTORY_LIMIT = 100
DEFAULT_CONVERSATION_LIMIT = 100
DEFAULT_COGNITIVE_LIMIT = 100
DEFAULT_ACTIVITY_LIMIT = 100
DEFAULT_REMINDER_LIMIT = 100


# ============================================================
# SAFE HELPERS
# ============================================================

def _safe_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _safe_int(
    value: Any,
    default: int = 0,
) -> int:

    try:
        return int(value or 0)
    except (
        TypeError,
        ValueError,
    ):
        return default


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:
        return float(value or 0)
    except (
        TypeError,
        ValueError,
    ):
        return default


def _percentage(
    numerator: int,
    denominator: int,
) -> float:

    if denominator <= 0:
        return 0.0

    return round(
        (
            numerator
            / denominator
        ) * 100,
        1,
    )


def _today_string() -> str:
    return date.today().isoformat()


def _date_from_value(
    value: Any,
) -> date | None:

    text = _safe_text(value)

    if not text:
        return None

    # ISO date / datetime
    try:
        return datetime.fromisoformat(
            text.replace("Z", "+00:00")
        ).date()

    except Exception:
        pass

    try:
        return date.fromisoformat(
            text[:10]
        )

    except Exception:
        return None


def _is_today(
    value: Any,
) -> bool:

    parsed = _date_from_value(
        value
    )

    return (
        parsed == date.today()
        if parsed
        else False
    )


def _row_dict(
    row: Any,
) -> dict[str, Any]:

    if row is None:
        return {}

    try:
        return dict(row)
    except Exception:
        return {}


def _safe_query(
    query: str,
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:

    try:

        rows = fetch_all(
            query,
            params,
        )

        return [
            _row_dict(row)
            for row in rows
        ]

    except Exception as exc:

        logger.warning(
            "Analytics query failed: %s",
            exc,
        )

        return []


def _safe_one(
    query: str,
    params: tuple[Any, ...] = (),
) -> dict[str, Any]:

    try:

        row = fetch_one(
            query,
            params,
        )

        return _row_dict(
            row
        )

    except Exception as exc:

        logger.warning(
            "Analytics query failed: %s",
            exc,
        )

        return {}


# ============================================================
# PATIENT
# ============================================================

def _get_patient() -> dict[str, Any]:

    row = _safe_one(
        """
        SELECT *
        FROM patient
        ORDER BY id
        LIMIT 1
        """
    )

    if not row:
        return {}

    allowed = (
        "id",
        "name",
        "age",
        "gender",
        "date_of_birth",
        "preferred_language",
        "caregiver_name",
        "caregiver_phone",
        "created_at",
        "updated_at",
    )

    return {
        key: row.get(key)
        for key in allowed
        if key in row
        and row.get(key) not in (
            None,
            "",
        )
    }


# ============================================================
# MEMORY ANALYTICS
# ============================================================

def _get_memory_analytics() -> dict[str, Any]:

    memories = _safe_query(
        """
        SELECT *
        FROM memories
        ORDER BY created_at DESC
        """
    )

    total_memories = len(
        memories
    )

    categories: dict[str, int] = {}

    people_count = 0
    event_count = 0

    for memory in memories:

        category = (
            _safe_text(
                memory.get("category")
            ).lower()
            or "uncategorized"
        )

        categories[
            category
        ] = (
            categories.get(
                category,
                0,
            ) + 1
        )

        if category == "people":
            people_count += 1

        if category == "events":
            event_count += 1

    media_count_row = _safe_one(
        """
        SELECT COUNT(*) AS count
        FROM memory_media
        """
    )

    media_items = _safe_int(
        media_count_row.get(
            "count"
        )
    )

    recent_memory_count = sum(
        1
        for memory in memories
        if _is_today(
            memory.get(
                "created_at"
            )
        )
    )

    return {
        "total_memories": total_memories,
        "people_memories": people_count,
        "event_memories": event_count,
        "categories": categories,
        "media_items": media_items,
        "memories_added_today": (
            recent_memory_count
        ),
        "available": (
            total_memories > 0
        ),
    }


# ============================================================
# REMINDER ANALYTICS
# ============================================================

def _get_reminder_analytics() -> dict[str, Any]:

    rows = _safe_query(
        """
        SELECT *
        FROM reminders
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            DEFAULT_REMINDER_LIMIT,
        ),
    )

    total = len(rows)

    completed = 0
    missed = 0
    pending = 0
    in_progress = 0
    cancelled = 0

    today_total = 0
    today_completed = 0
    today_missed = 0

    status_counts: dict[str, int] = {}

    for reminder in rows:

        status = (
            _safe_text(
                reminder.get("status")
            ).lower()
            or "unknown"
        )

        status_counts[
            status
        ] = (
            status_counts.get(
                status,
                0,
            ) + 1
        )

        if status in {
            "completed",
            "complete",
            "done",
        }:
            completed += 1

        elif status in {
            "missed",
            "expired",
            "failed",
        }:
            missed += 1

        elif status in {
            "pending",
            "scheduled",
            "upcoming",
        }:
            pending += 1

        elif status == "in_progress":
            in_progress += 1

        elif status in {
            "cancelled",
            "canceled",
        }:
            cancelled += 1

        reminder_date = (
            reminder.get("time")
            or reminder.get(
                "reminder_time"
            )
            or reminder.get(
                "created_at"
            )
        )

        if _is_today(
            reminder_date
        ):

            today_total += 1

            if status in {
                "completed",
                "complete",
                "done",
            }:
                today_completed += 1

            if status in {
                "missed",
                "expired",
                "failed",
            }:
                today_missed += 1

    active_total = (
        total
        - cancelled
    )

    completion_rate = _percentage(
        completed,
        active_total,
    )

    today_completion_rate = _percentage(
        today_completed,
        today_total,
    )

    return {
        "total": total,
        "completed": completed,
        "missed": missed,
        "pending": pending,
        "in_progress": in_progress,
        "cancelled": cancelled,
        "completion_rate_percent": completion_rate,
        "today_total": today_total,
        "today_completed": today_completed,
        "today_missed": today_missed,
        "today_completion_rate_percent": (
            today_completion_rate
        ),
        "status_counts": status_counts,
        "available": total > 0,
    }


# ============================================================
# ACTIVITY ANALYTICS
# ============================================================

def _get_activity_analytics() -> dict[str, Any]:

    rows = _safe_query(
        """
        SELECT *
        FROM activities
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            DEFAULT_ACTIVITY_LIMIT,
        ),
    )

    total = len(rows)

    completed = 0
    pending = 0
    missed = 0
    in_progress = 0

    today_total = 0
    today_completed = 0

    status_counts: dict[str, int] = {}

    for activity in rows:

        status = (
            _safe_text(
                activity.get("status")
            ).lower()
            or "unknown"
        )

        status_counts[
            status
        ] = (
            status_counts.get(
                status,
                0,
            ) + 1
        )

        if status in {
            "completed",
            "complete",
            "done",
        }:
            completed += 1

        elif status in {
            "missed",
            "failed",
            "skipped",
        }:
            missed += 1

        elif status == "in_progress":
            in_progress += 1

        else:
            pending += 1

        activity_date = (
            activity.get(
                "completed_at"
            )
            or activity.get(
                "created_at"
            )
            or activity.get(
                "date"
            )
        )

        if _is_today(
            activity_date
        ):

            today_total += 1

            if status in {
                "completed",
                "complete",
                "done",
            }:
                today_completed += 1

    completion_rate = _percentage(
        completed,
        total,
    )

    today_rate = _percentage(
        today_completed,
        today_total,
    )

    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "missed": missed,
        "in_progress": in_progress,
        "completion_rate_percent": (
            completion_rate
        ),
        "today_total": today_total,
        "today_completed": (
            today_completed
        ),
        "today_completion_rate_percent": (
            today_rate
        ),
        "status_counts": status_counts,
        "available": total > 0,
    }


# ============================================================
# COGNITIVE ANALYTICS
# ============================================================

def _get_cognitive_analytics() -> dict[str, Any]:

    rows = _safe_query(
        """
        SELECT *
        FROM cognitive_records
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            DEFAULT_COGNITIVE_LIMIT,
        ),
    )

    if not rows:

        return {
            "available": False,
            "total_records": 0,
            "average_score": 0.0,
            "latest_score": None,
            "highest_score": None,
            "lowest_score": None,
            "trend": "unavailable",
            "recent_records": [],
        }

    scores: list[float] = []

    for row in rows:

        value = (
            row.get("score")
            if row.get("score") is not None
            else row.get(
                "performance"
            )
        )

        if value is None:
            value = row.get(
                "result"
            )

        numeric = _safe_float(
            value,
            default=-1,
        )

        if numeric >= 0:
            scores.append(
                numeric
            )

    average_score = (
        round(
            sum(scores)
            / len(scores),
            2,
        )
        if scores
        else 0.0
    )

    latest_score = (
        scores[0]
        if scores
        else None
    )

    highest_score = (
        max(scores)
        if scores
        else None
    )

    lowest_score = (
        min(scores)
        if scores
        else None
    )

    trend = "stable"

    if len(scores) >= 4:

        recent = (
            sum(scores[:2])
            / 2
        )

        previous = (
            sum(scores[2:4])
            / 2
        )

        difference = (
            recent
            - previous
        )

        if difference > 0.5:
            trend = "improving"

        elif difference < -0.5:
            trend = "declining"

    recent_records = []

    for row in rows[:10]:

        recent_records.append(
            {
                key: row.get(key)
                for key in (
                    "id",
                    "activity_id",
                    "score",
                    "performance",
                    "result",
                    "created_at",
                )
                if key in row
            }
        )

    return {
        "available": True,
        "total_records": len(rows),
        "average_score": average_score,
        "latest_score": latest_score,
        "highest_score": highest_score,
        "lowest_score": lowest_score,
        "trend": trend,
        "recent_records": recent_records,
    }


# ============================================================
# CONVERSATION ANALYTICS
# ============================================================

def _get_conversation_analytics() -> dict[str, Any]:

    table_name = None

    try:

        exists = fetch_one(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'conversation_messages'
            """
        )

        if exists:
            table_name = (
                "conversation_messages"
            )

    except Exception:
        pass

    if not table_name:

        try:

            exists = fetch_one(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'conversation_history'
                """
            )

            if exists:
                table_name = (
                    "conversation_history"
                )

        except Exception:
            pass

    if not table_name:

        return {
            "available": False,
            "total_messages": 0,
            "user_messages": 0,
            "assistant_messages": 0,
            "today_messages": 0,
            "today_user_messages": 0,
            "today_assistant_messages": 0,
        }

    rows = _safe_query(
        f"""
        SELECT *
        FROM {table_name}
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            DEFAULT_CONVERSATION_LIMIT,
        ),
    )

    total_messages = len(rows)

    user_messages = 0
    assistant_messages = 0
    today_messages = 0
    today_user_messages = 0
    today_assistant_messages = 0

    for row in rows:

        role = (
            _safe_text(
                row.get("role")
            ).lower()
        )

        timestamp = (
            row.get("created_at")
            or row.get("timestamp")
        )

        if role == "user":
            user_messages += 1

        elif role == "assistant":
            assistant_messages += 1

        if _is_today(
            timestamp
        ):

            today_messages += 1

            if role == "user":
                today_user_messages += 1

            elif role == "assistant":
                today_assistant_messages += 1

    return {
        "available": True,
        "total_messages": total_messages,
        "user_messages": user_messages,
        "assistant_messages": assistant_messages,
        "today_messages": today_messages,
        "today_user_messages": (
            today_user_messages
        ),
        "today_assistant_messages": (
            today_assistant_messages
        ),
        "today_conversation_active": (
            today_messages > 0
        ),
    }


# ============================================================
# COMPANION ANALYTICS
# ============================================================

def _get_companion_analytics() -> dict[str, Any]:

    rows = _safe_query(
        """
        SELECT *
        FROM companion_state
        """
    )

    state: dict[str, Any] = {}

    for row in rows:

        key = _safe_text(
            row.get("key")
        )

        if not key:
            continue

        value = row.get(
            "value"
        )

        # State values are frequently
        # JSON encoded.
        if isinstance(
            value,
            str,
        ):

            try:
                import json

                value = json.loads(
                    value
                )

            except Exception:
                pass

        state[key] = value

    mood = _safe_text(
        state.get(
            "mood",
            "unknown",
        )
    ).lower()

    return {
        "mood": mood or "unknown",
        "current_activity": (
            state.get(
                "current_activity"
            )
        ),
        "next_activity": (
            state.get(
                "next_activity"
            )
        ),
        "last_interaction": (
            state.get(
                "last_interaction"
            )
        ),
        "last_memory_activity": (
            state.get(
                "last_memory_activity"
            )
        ),
        "conversation_active": (
            state.get(
                "conversation_active"
            )
        ),
        "state": state,
        "available": bool(state),
    }


# ============================================================
# TODAY SNAPSHOT
# ============================================================

def get_today_snapshot() -> dict[str, Any]:

    reminders = _get_reminder_analytics()
    activity = _get_activity_analytics()
    conversation = _get_conversation_analytics()
    companion = _get_companion_analytics()
    memory = _get_memory_analytics()

    return {
        "date": _today_string(),

        "reminders": {
            "total": reminders.get(
                "today_total",
                0,
            ),
            "completed": reminders.get(
                "today_completed",
                0,
            ),
            "missed": reminders.get(
                "today_missed",
                0,
            ),
            "completion_rate_percent": (
                reminders.get(
                    "today_completion_rate_percent",
                    0,
                )
            ),
        },

        "activity": {
            "total": activity.get(
                "today_total",
                0,
            ),
            "completed": activity.get(
                "today_completed",
                0,
            ),
            "completion_rate_percent": (
                activity.get(
                    "today_completion_rate_percent",
                    0,
                )
            ),
        },

        "conversation": {
            "messages": conversation.get(
                "today_messages",
                0,
            ),
            "user_messages": conversation.get(
                "today_user_messages",
                0,
            ),
            "assistant_messages": conversation.get(
                "today_assistant_messages",
                0,
            ),
            "active": conversation.get(
                "today_conversation_active",
                False,
            ),
        },

        "memory": {
            "total_memories": memory.get(
                "total_memories",
                0,
            ),
            "media_items": memory.get(
                "media_items",
                0,
            ),
            "added_today": memory.get(
                "memories_added_today",
                0,
            ),
        },

        "companion": {
            "mood": companion.get(
                "mood",
                "unknown",
            ),
            "current_activity": companion.get(
                "current_activity"
            ),
            "next_activity": companion.get(
                "next_activity"
            ),
        },
    }


# ============================================================
# FULL PATIENT PROFILE
# ============================================================

def build_patient_profile() -> dict[str, Any]:

    patient = _get_patient()
    memory = _get_memory_analytics()
    reminders = _get_reminder_analytics()
    activity = _get_activity_analytics()
    cognitive = _get_cognitive_analytics()
    conversation = _get_conversation_analytics()
    companion = _get_companion_analytics()

    today = get_today_snapshot()

    return {
        "success": True,

        "generated_at": (
            datetime.now().isoformat()
        ),

        "patient": patient,

        "today": today,

        "memory": memory,

        "cognitive": cognitive,

        "activity": activity,

        "reminders": reminders,

        "conversation": conversation,

        "companion": companion,

        "analytics": {
            "data_sources": [
                "patient",
                "memories",
                "memory_media",
                "reminders",
                "activities",
                "cognitive_records",
                "conversation_messages",
                "companion_state",
            ],

            "non_diagnostic": True,

            "note": (
                "This profile summarizes "
                "application activity and "
                "does not provide medical "
                "assessment or diagnosis."
            ),
        },
    }


# ============================================================
# WEEKLY SNAPSHOT
# ============================================================

def get_weekly_snapshot() -> dict[str, Any]:

    profile = build_patient_profile()

    reminders = profile.get(
        "reminders",
        {},
    )

    activity = profile.get(
        "activity",
        {},
    )

    conversation = profile.get(
        "conversation",
        {},
    )

    cognitive = profile.get(
        "cognitive",
        {},
    )

    return {
        "success": True,

        "period": {
            "type": "weekly",
            "ending": _today_string(),
        },

        "reminders": reminders,

        "activity": activity,

        "conversation": conversation,

        "cognitive": cognitive,

        "note": (
            "Weekly values summarize "
            "available application records "
            "and are not medical conclusions."
        ),
    }


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "build_patient_profile",
    "get_today_snapshot",
    "get_weekly_snapshot",
]