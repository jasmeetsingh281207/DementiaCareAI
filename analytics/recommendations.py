"""
DementiaCareAI - Caregiver Recommendations

Deterministic, non-diagnostic caregiver intelligence.

This module generates practical recommendations from the
application's observed data.

IMPORTANT:
- No Gemini/API calls are made here.
- No medical diagnosis is generated.
- No clinical conclusions are made.
- Recommendations are based only on application-level data.
"""

from __future__ import annotations

import logging
from typing import Any

from analytics.patient_profile import build_patient_profile

logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTS
# ============================================================

PRIORITY_ORDER = {
    "high": 0,
    "normal": 1,
    "low": 2,
}

ATTENTION_MOODS = {
    "sad",
    "frustrated",
    "confused",
    "anxious",
    "distressed",
    "upset",
}


# ============================================================
# SAFE HELPERS
# ============================================================

def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default

        if isinstance(value, bool):
            return int(value)

        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        if value is None:
            return default

        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_text(
    value: Any,
    default: str = "",
) -> str:
    if value is None:
        return default

    text = str(value).strip()

    return text if text else default


def _recommendation(
    *,
    recommendation_id: str,
    title: str,
    message: str,
    priority: str = "normal",
    category: str = "general",
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:

    if priority not in PRIORITY_ORDER:
        priority = "normal"

    return {
        "id": recommendation_id,
        "title": title,
        "message": message,
        "priority": priority,
        "category": category,
        "evidence": evidence or {},
    }


def _append_unique(
    recommendations: list[dict[str, Any]],
    recommendation: dict[str, Any],
) -> None:

    recommendation_id = recommendation.get("id")

    if any(
        item.get("id") == recommendation_id
        for item in recommendations
    ):
        return

    recommendations.append(recommendation)


# ============================================================
# REMINDER RECOMMENDATIONS
# ============================================================

def _build_reminder_recommendations(
    profile: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> None:

    reminders = profile.get("reminders") or {}

    available = bool(
        reminders.get(
            "available",
            False,
        )
    )

    if not available:
        return

    total = _safe_int(
        reminders.get("total")
    )

    completed = _safe_int(
        reminders.get("completed")
    )

    missed = _safe_int(
        reminders.get("missed")
    )

    pending = _safe_int(
        reminders.get("pending")
    )

    completion_rate = _safe_float(
        reminders.get(
            "completion_rate_percent"
        )
    )

    if missed > 0:

        _append_unique(
            recommendations,
            _recommendation(
                recommendation_id="missed_reminders",
                title="Check missed reminders",
                message=(
                    f"There are {missed} reminder(s) "
                    "recorded as missed. Consider checking "
                    "whether the reminder timing, wording, "
                    "or routine needs adjustment."
                ),
                priority="high",
                category="reminders",
                evidence={
                    "missed": missed,
                    "total": total,
                    "completion_rate_percent": (
                        completion_rate
                    ),
                },
            ),
        )

    if (
        total > 0
        and completion_rate < 50
        and missed == 0
    ):

        _append_unique(
            recommendations,
            _recommendation(
                recommendation_id="low_reminder_completion",
                title="Review reminder routine",
                message=(
                    "Less than half of the recorded "
                    "reminders are marked completed. "
                    "Consider reviewing reminder timing "
                    "and keeping important prompts simple "
                    "and consistent."
                ),
                priority="normal",
                category="reminders",
                evidence={
                    "total": total,
                    "completed": completed,
                    "pending": pending,
                    "completion_rate_percent": (
                        completion_rate
                    ),
                },
            ),
        )

    elif (
        total >= 3
        and completion_rate >= 80
    ):

        _append_unique(
            recommendations,
            _recommendation(
                recommendation_id="consistent_reminders",
                title="Reminder routine looks consistent",
                message=(
                    "Most recorded reminders are being "
                    "completed. Keeping the existing routine "
                    "consistent may be helpful."
                ),
                priority="low",
                category="reminders",
                evidence={
                    "total": total,
                    "completed": completed,
                    "completion_rate_percent": (
                        completion_rate
                    ),
                },
            ),
        )


# ============================================================
# ACTIVITY RECOMMENDATIONS
# ============================================================

def _build_activity_recommendations(
    profile: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> None:

    activity = profile.get("activity") or {}

    available = bool(
        activity.get(
            "available",
            False,
        )
    )

    if not available:
        return

    total = _safe_int(
        activity.get("total")
    )

    completed = _safe_int(
        activity.get("completed")
    )

    pending = _safe_int(
        activity.get("pending")
    )

    completion_rate = _safe_float(
        activity.get(
            "completion_rate_percent"
        )
    )

    today_total = _safe_int(
        activity.get("today_total")
    )

    today_completed = _safe_int(
        activity.get("today_completed")
    )

    if (
        total > 0
        and completed == 0
    ):

        _append_unique(
            recommendations,
            _recommendation(
                recommendation_id="no_completed_activities",
                title="Activity engagement is low",
                message=(
                    "No recorded activities have been "
                    "completed in the available activity data. "
                    "Consider offering one simple, familiar "
                    "activity at a time."
                ),
                priority="normal",
                category="activity",
                evidence={
                    "total": total,
                    "completed": completed,
                    "pending": pending,
                },
            ),
        )

        return

    if (
        total > 0
        and completion_rate < 50
    ):

        _append_unique(
            recommendations,
            _recommendation(
                recommendation_id="low_activity_completion",
                title="Keep activities simple",
                message=(
                    "Activity completion is below half of "
                    "the recorded activities. Consider offering "
                    "fewer activities at a time and keeping "
                    "instructions short and familiar."
                ),
                priority="normal",
                category="activity",
                evidence={
                    "total": total,
                    "completed": completed,
                    "pending": pending,
                    "completion_rate_percent": (
                        completion_rate
                    ),
                },
            ),
        )

    if (
        today_total > 0
        and today_completed == 0
    ):

        _append_unique(
            recommendations,
            _recommendation(
                recommendation_id="no_activity_completed_today",
                title="Offer one familiar activity",
                message=(
                    "No activity is currently recorded as "
                    "completed today. Consider offering one "
                    "simple and familiar activity rather than "
                    "several choices at once."
                ),
                priority="normal",
                category="activity",
                evidence={
                    "today_total": today_total,
                    "today_completed": today_completed,
                },
            ),
        )


# ============================================================
# CONVERSATION RECOMMENDATIONS
# ============================================================

def _build_conversation_recommendations(
    profile: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> None:

    conversation = profile.get(
        "conversation"
    ) or {}

    available = bool(
        conversation.get(
            "available",
            False,
        )
    )

    if not available:
        return

    total_messages = _safe_int(
        conversation.get(
            "total_messages"
        )
    )

    today_messages = _safe_int(
        conversation.get(
            "today_messages"
        )
    )

    if total_messages == 0:

        _append_unique(
            recommendations,
            _recommendation(
                recommendation_id="no_conversation_activity",
                title="No conversation activity recorded",
                message=(
                    "There is no conversation activity in "
                    "the available records. If appropriate, "
                    "a caregiver may want to check in and "
                    "offer a familiar conversation."
                ),
                priority="low",
                category="conversation",
                evidence={
                    "total_messages": total_messages,
                    "today_messages": today_messages,
                },
            ),
        )


# ============================================================
# MEMORY RECOMMENDATIONS
# ============================================================

def _build_memory_recommendations(
    profile: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> None:

    memory = profile.get(
        "memory"
    ) or {}

    available = bool(
        memory.get(
            "available",
            False,
        )
    )

    if not available:
        return

    total_memories = _safe_int(
        memory.get(
            "total_memories"
        )
    )

    media_items = _safe_int(
        memory.get(
            "media_items"
        )
    )

    if total_memories == 0:

        _append_unique(
            recommendations,
            _recommendation(
                recommendation_id="no_personal_memories",
                title="Add familiar memories",
                message=(
                    "No personal memories are currently "
                    "recorded. Adding approved information "
                    "about familiar people, meaningful events, "
                    "or important places can give the companion "
                    "more useful context."
                ),
                priority="normal",
                category="memory",
                evidence={
                    "total_memories": total_memories,
                    "media_items": media_items,
                },
            ),
        )

        return

    if media_items == 0:

        _append_unique(
            recommendations,
            _recommendation(
                recommendation_id="no_memory_media",
                title="Consider adding memory media",
                message=(
                    "Personal memories exist, but no memory "
                    "media is currently recorded. Approved "
                    "photos or other supported media may provide "
                    "additional conversation context."
                ),
                priority="low",
                category="memory",
                evidence={
                    "total_memories": total_memories,
                    "media_items": media_items,
                },
            ),
        )


# ============================================================
# COGNITIVE DATA RECOMMENDATIONS
# ============================================================

def _build_cognitive_recommendations(
    profile: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> None:

    cognitive = profile.get(
        "cognitive"
    ) or {}

    available = bool(
        cognitive.get(
            "available",
            False,
        )
    )

    if not available:
        return

    records = _safe_int(
        cognitive.get(
            "total_records"
        )
    )

    trend = _safe_text(
        cognitive.get(
            "observed_score_trend",
            cognitive.get(
                "trend",
                "insufficient_data",
            ),
        ),
        "insufficient_data",
    ).lower()

    if records == 0:

        _append_unique(
            recommendations,
            _recommendation(
                recommendation_id="no_cognitive_records",
                title="No cognitive activity recorded",
                message=(
                    "There are currently no recorded "
                    "cognitive activity results. More "
                    "application data may be needed before "
                    "a simple activity trend can be shown."
                ),
                priority="low",
                category="cognitive",
                evidence={
                    "total_records": records,
                    "observed_score_trend": trend,
                },
            ),
        )

        return

    if trend == "declining":

        _append_unique(
            recommendations,
            _recommendation(
                recommendation_id="observed_cognitive_change",
                title="Review recent cognitive activity",
                message=(
                    "The recorded cognitive activity shows "
                    "a lower recent score pattern than earlier "
                    "records. This is an application-level data "
                    "trend, not a medical assessment. A caregiver "
                    "may want to review the recent activity "
                    "context."
                ),
                priority="normal",
                category="cognitive",
                evidence={
                    "total_records": records,
                    "observed_score_trend": trend,
                    "latest_score": cognitive.get(
                        "latest_score"
                    ),
                    "average_score": cognitive.get(
                        "average_score"
                    ),
                },
            ),
        )


# ============================================================
# COMPANION / WELLBEING RECOMMENDATIONS
# ============================================================

def _build_companion_recommendations(
    profile: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> None:

    companion = profile.get(
        "companion"
    ) or {}

    available = bool(
        companion.get(
            "available",
            False,
        )
    )

    if not available:
        return

    mood = _safe_text(
        companion.get(
            "mood",
            "unknown",
        ),
        "unknown",
    ).lower()

    if mood in ATTENTION_MOODS:

        _append_unique(
            recommendations,
            _recommendation(
                recommendation_id="gentle_companion_checkin",
                title="Consider a gentle check-in",
                message=(
                    "The companion state contains a recent "
                    f"{mood} mood signal. A calm, familiar "
                    "conversation or nearby caregiver check-in "
                    "may be helpful."
                ),
                priority="normal",
                category="wellbeing",
                evidence={
                    "mood": mood,
                },
            ),
        )


# ============================================================
# MAIN RECOMMENDATION ENGINE
# ============================================================

def generate_recommendations(
    profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Generate caregiver-facing recommendations.

    The function is deterministic and does not call Gemini.
    """

    if profile is None:
        profile = build_patient_profile()

    if not isinstance(profile, dict):
        profile = {}

    recommendations: list[
        dict[str, Any]
    ] = []

    _build_reminder_recommendations(
        profile,
        recommendations,
    )

    _build_activity_recommendations(
        profile,
        recommendations,
    )

    _build_conversation_recommendations(
        profile,
        recommendations,
    )

    _build_memory_recommendations(
        profile,
        recommendations,
    )

    _build_cognitive_recommendations(
        profile,
        recommendations,
    )

    _build_companion_recommendations(
        profile,
        recommendations,
    )

    # --------------------------------------------------------
    # DEFAULT
    # --------------------------------------------------------

    if not recommendations:

        _append_unique(
            recommendations,
            _recommendation(
                recommendation_id="routine_stable",
                title="Routine looks stable",
                message=(
                    "There are no immediate application-level "
                    "attention items in the available data."
                ),
                priority="low",
                category="general",
                evidence={
                    "source": "application_activity",
                },
            ),
        )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    recommendations.sort(
        key=lambda item: (
            PRIORITY_ORDER.get(
                item.get(
                    "priority",
                    "normal",
                ),
                1,
            ),
            item.get(
                "category",
                "general",
            ),
            item.get(
                "title",
                "",
            ),
        )
    )

    return recommendations


# ============================================================
# PUBLIC COMPATIBILITY FUNCTION
# ============================================================

def get_recommendations(
    profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:

    return generate_recommendations(
        profile
    )


# ============================================================
# SERVICE STATUS
# ============================================================

def get_recommendation_status() -> dict[str, Any]:
    return {
        "available": True,
        "engine": "deterministic",
        "gemini_used": False,
        "diagnostic": False,
    }