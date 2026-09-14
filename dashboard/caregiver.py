"""
DementiaCareAI
Caregiver Intelligence Service

Clean backend interface for the caregiver dashboard.

The UI layer can consume these objects directly.

This service is deterministic and does not consume Gemini
quota for routine analytics/report generation.

No medical diagnosis is generated here.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from analytics.patient_profile import (
    build_patient_profile,
    get_today_snapshot,
    get_weekly_snapshot,
)

from analytics.recommendations import (
    generate_recommendations,
)

logger = logging.getLogger(__name__)


# ============================================================
# SAFE HELPERS
# ============================================================

def _safe_profile() -> dict[str, Any]:

    try:

        profile = build_patient_profile()

        if isinstance(
            profile,
            dict,
        ):
            return profile

    except Exception as exc:

        logger.exception(
            "Unable to build caregiver profile: %s",
            exc,
        )

    return {
        "success": False,
        "patient": {},
        "today": {},
        "memory": {},
        "cognitive": {},
        "activity": {},
        "reminders": {},
        "conversation": {},
        "companion": {},
    }


def _safe_recommendations(
    profile: dict[str, Any],
) -> list[dict[str, Any]]:

    try:

        result = generate_recommendations(
            profile
        )

        if isinstance(
            result,
            list,
        ):
            return result

    except Exception as exc:

        logger.exception(
            "Unable to generate caregiver recommendations: %s",
            exc,
        )

    return []


# ============================================================
# OVERVIEW
# ============================================================

def get_caregiver_overview() -> dict[str, Any]:

    profile = _safe_profile()

    recommendations = (
        _safe_recommendations(
            profile
        )
    )

    return {
        "success": True,

        "generated_at": (
            datetime.now().isoformat()
        ),

        "patient": profile.get(
            "patient",
            {},
        ),

        "today": profile.get(
            "today",
            {},
        ),

        "memory": profile.get(
            "memory",
            {},
        ),

        "cognitive": profile.get(
            "cognitive",
            {},
        ),

        "activity": profile.get(
            "activity",
            {},
        ),

        "reminders": profile.get(
            "reminders",
            {},
        ),

        "conversation": profile.get(
            "conversation",
            {},
        ),

        "companion": profile.get(
            "companion",
            {},
        ),

        "recommendations": recommendations,

        "meta": {
            "non_diagnostic": True,
            "source": "application_activity",
            "gemini_used": False,
        },
    }


# ============================================================
# TODAY
# ============================================================

def get_caregiver_today() -> dict[str, Any]:

    try:

        snapshot = get_today_snapshot()

        return {
            "success": True,
            **snapshot,
        }

    except Exception as exc:

        logger.exception(
            "Unable to generate today's caregiver snapshot: %s",
            exc,
        )

        return {
            "success": False,
            "date": datetime.now().date().isoformat(),
            "error": str(exc),
        }


# ============================================================
# WEEKLY
# ============================================================

def get_caregiver_weekly() -> dict[str, Any]:

    try:

        snapshot = get_weekly_snapshot()

        return {
            "success": True,
            **snapshot,
        }

    except Exception as exc:

        logger.exception(
            "Unable to generate weekly caregiver snapshot: %s",
            exc,
        )

        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# ACTIVITY
# ============================================================

def get_caregiver_activity() -> dict[str, Any]:

    profile = _safe_profile()

    return {
        "success": True,
        "activity": profile.get(
            "activity",
            {},
        ),
    }


# ============================================================
# COGNITIVE
# ============================================================

def get_caregiver_cognitive() -> dict[str, Any]:

    profile = _safe_profile()

    return {
        "success": True,
        "cognitive": profile.get(
            "cognitive",
            {},
        ),
    }


# ============================================================
# MEMORY
# ============================================================

def get_caregiver_memory() -> dict[str, Any]:

    profile = _safe_profile()

    return {
        "success": True,
        "memory": profile.get(
            "memory",
            {},
        ),
    }


# ============================================================
# REMINDERS
# ============================================================

def get_caregiver_reminders() -> dict[str, Any]:

    profile = _safe_profile()

    return {
        "success": True,
        "reminders": profile.get(
            "reminders",
            {},
        ),
    }


# ============================================================
# CONVERSATION
# ============================================================

def get_caregiver_conversation() -> dict[str, Any]:

    profile = _safe_profile()

    return {
        "success": True,
        "conversation": profile.get(
            "conversation",
            {},
        ),
    }


# ============================================================
# COMPANION
# ============================================================

def get_caregiver_companion() -> dict[str, Any]:

    profile = _safe_profile()

    return {
        "success": True,
        "companion": profile.get(
            "companion",
            {},
        ),
    }


# ============================================================
# RECOMMENDATIONS
# ============================================================

def get_caregiver_recommendations() -> dict[str, Any]:

    profile = _safe_profile()

    recommendations = (
        _safe_recommendations(
            profile
        )
    )

    high_priority = [
        item
        for item in recommendations
        if item.get(
            "priority"
        ) == "high"
    ]

    normal_priority = [
        item
        for item in recommendations
        if item.get(
            "priority"
        ) == "normal"
    ]

    low_priority = [
        item
        for item in recommendations
        if item.get(
            "priority"
        ) == "low"
    ]

    return {
        "success": True,

        "recommendations": (
            recommendations
        ),

        "attention_items": (
            high_priority
        ),

        "counts": {
            "total": len(
                recommendations
            ),
            "high": len(
                high_priority
            ),
            "normal": len(
                normal_priority
            ),
            "low": len(
                low_priority
            ),
        },
    }


# ============================================================
# REPORT
# ============================================================

def generate_caregiver_report() -> dict[str, Any]:

    overview = (
        get_caregiver_overview()
    )

    recommendations = overview.get(
        "recommendations",
        [],
    )

    high_priority = [
        item
        for item in recommendations
        if item.get(
            "priority"
        ) == "high"
    ]

    normal_priority = [
        item
        for item in recommendations
        if item.get(
            "priority"
        ) == "normal"
    ]

    low_priority = [
        item
        for item in recommendations
        if item.get(
            "priority"
        ) == "low"
    ]

    return {
        "success": True,

        "generated_at": (
            datetime.now().isoformat()
        ),

        "report_type": (
            "caregiver_application_activity"
        ),

        "summary": {
            "patient": overview.get(
                "patient",
                {},
            ),

            "today": overview.get(
                "today",
                {},
            ),
        },

        "observations": {
            "memory": overview.get(
                "memory",
                {},
            ),

            "activity": overview.get(
                "activity",
                {},
            ),

            "reminders": overview.get(
                "reminders",
                {},
            ),

            "conversation": overview.get(
                "conversation",
                {},
            ),

            "cognitive": overview.get(
                "cognitive",
                {},
            ),

            "companion": overview.get(
                "companion",
                {},
            ),
        },

        "attention_items": (
            high_priority
        ),

        "recommendations": (
            normal_priority
        ),

        "additional_notes": (
            low_priority
        ),

        "recommendation_counts": {
            "high": len(
                high_priority
            ),
            "normal": len(
                normal_priority
            ),
            "low": len(
                low_priority
            ),
            "total": len(
                recommendations
            ),
        },

        "note": (
            "This report summarizes "
            "application activity and "
            "is not a medical assessment "
            "or diagnosis."
        ),

        "meta": {
            "non_diagnostic": True,
            "gemini_used": False,
            "deterministic": True,
        },
    }


# ============================================================
# SINGLE SERVICE ENTRY POINT
# ============================================================

def get_caregiver_dashboard() -> dict[str, Any]:

    return get_caregiver_overview()


# ============================================================
# COMPATIBILITY ALIASES
# ============================================================

def get_dashboard_summary() -> dict[str, Any]:

    return get_caregiver_overview()


def get_caregiver_report() -> dict[str, Any]:

    return generate_caregiver_report()


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "get_caregiver_overview",
    "get_caregiver_today",
    "get_caregiver_weekly",
    "get_caregiver_activity",
    "get_caregiver_cognitive",
    "get_caregiver_memory",
    "get_caregiver_reminders",
    "get_caregiver_conversation",
    "get_caregiver_companion",
    "get_caregiver_recommendations",
    "generate_caregiver_report",
    "get_caregiver_dashboard",
    "get_dashboard_summary",
    "get_caregiver_report",
]