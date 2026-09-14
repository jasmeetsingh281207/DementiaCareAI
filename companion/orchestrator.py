from datetime import datetime

from companion.state import (
    get_state,
    get_current_activity,
    get_next_activity,
    get_mood,
)

from memory.activity_engine import create_activity

from memory.memory_store import get_memories

from tools.reminders import (
    update_due_reminders,
    get_next_due_reminder,
    start_reminder,
)


# ============================================================
# ACTION TYPES
# ============================================================

ACTION_REMINDER = "reminder"
ACTION_COGNITIVE = "cognitive_activity"
ACTION_MEMORY = "memory_activity"
ACTION_CHECK_IN = "check_in"
ACTION_CONVERSATION = "conversation"


# ============================================================
# PRIORITIES
# ============================================================

PRIORITY_REMINDER = 1
PRIORITY_COGNITIVE = 2
PRIORITY_MEMORY = 3
PRIORITY_CHECK_IN = 4
PRIORITY_CONVERSATION = 5


# ============================================================
# TIME HELPERS
# ============================================================

def _now():
    return datetime.now()


def _parse_timestamp(value):
    """
    Safely convert a stored timestamp into datetime.
    """
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _minutes_since(value):
    """
    Return number of minutes since timestamp.
    """
    timestamp = _parse_timestamp(value)

    if timestamp is None:
        return None

    difference = _now() - timestamp

    return difference.total_seconds() / 60


# ============================================================
# ACTIVITY HELPERS
# ============================================================

def _activity_is_active(activity):
    """
    Determine whether an activity is still active.
    """
    if not activity:
        return False

    status = str(activity.get("status", "")).lower()

    return status not in {
        "completed",
        "cancelled",
        "canceled",
        "skipped",
    }


# ============================================================
# CURRENT COMPANION CONTEXT
# ============================================================

def get_current_context():
    """
    Collect all information required by the companion
    decision engine.
    """

    try:
        state = get_state() or {}
    except Exception as error:
        print("COMPANION STATE ERROR:", error)
        state = {}

    try:
        current_activity = get_current_activity()
    except Exception as error:
        print("CURRENT ACTIVITY ERROR:", error)
        current_activity = None

    try:
        next_activity = get_next_activity()
    except Exception as error:
        print("NEXT ACTIVITY ERROR:", error)
        next_activity = None

    try:
        mood = get_mood()
    except Exception as error:
        print("MOOD ERROR:", error)
        mood = "unknown"

    return {
        "state": state,
        "current_activity": current_activity,
        "next_activity": next_activity,
        "mood": mood,
        "last_interaction": state.get("last_interaction"),
        "last_memory_activity": state.get("last_memory_activity"),
    }


# ============================================================
# REMINDERS
# ============================================================

def get_due_reminder():
    """
    Update reminder states and return the next due reminder.
    """

    try:
        update_due_reminders()
    except Exception as error:
        print("REMINDER UPDATE ERROR:", error)
        return None

    try:
        return get_next_due_reminder()
    except Exception as error:
        print("GET DUE REMINDER ERROR:", error)
        return None


# ============================================================
# CHECK-IN LOGIC
# ============================================================

def should_check_in(context):
    """
    Start a gentle check-in when the patient has not interacted
    with the companion for approximately one hour.
    """

    last_interaction = context.get("last_interaction")

    if not last_interaction:
        return True

    minutes = _minutes_since(last_interaction)

    if minutes is None:
        return True

    return minutes >= 60


# ============================================================
# COGNITIVE ACTIVITY LOGIC
# ============================================================

def should_start_cognitive_activity(context):
    """
    Start the next scheduled cognitive activity when there is
    no currently active activity.
    """

    current_activity = context.get("current_activity")

    if _activity_is_active(current_activity):
        return False

    next_activity = context.get("next_activity")

    if not next_activity:
        return False

    activity_type = str(
        next_activity.get("type", "")
    ).lower()

    return activity_type in {
        "game",
        "cognitive",
        "cognitive_activity",
    }


# ============================================================
# MEMORY ACTIVITY LOGIC
# ============================================================

def should_start_memory_activity(context):
    """
    Determine whether a memory activity should be started.

    A memory activity is allowed when:
    - there is no active activity
    - memories exist
    - the previous memory activity is completed
    - at least 30 minutes have passed since completion
    """

    current_activity = context.get("current_activity")

    if _activity_is_active(current_activity):
        return False

    try:
        memories = get_memories()
    except Exception as error:
        print("MEMORY LOAD ERROR:", error)
        return False

    if not memories:
        return False

    last_memory_activity = context.get(
        "last_memory_activity"
    )

    if not last_memory_activity:
        return True

    status = str(
        last_memory_activity.get("status", "")
    ).lower()

    if status not in {
        "completed",
        "cancelled",
        "canceled",
        "skipped",
    }:
        return False

    completed_at = last_memory_activity.get(
        "completed_at"
    )

    minutes = _minutes_since(completed_at)

    if minutes is None:
        return True

    return minutes >= 30


# ============================================================
# CREATE MEMORY ACTIVITY
# ============================================================

def _create_next_memory_activity(context):
    """
    Select a memory and create a memory activity.

    Avoid repeating the immediately previous memory when
    multiple memories are available.
    """

    try:
        memories = get_memories()
    except Exception as error:
        print("MEMORY LOAD ERROR:", error)
        return None

    if not memories:
        return None

    last_activity = context.get(
        "last_memory_activity"
    )

    last_memory_id = None

    if last_activity:
        last_memory_id = last_activity.get(
            "memory_id"
        )

    candidates = []

    for memory in memories:

        if not isinstance(memory, dict):
            continue

        memory_id = memory.get("id")

        if memory_id is None:
            continue

        if str(memory_id) != str(last_memory_id):
            candidates.append(memory)

    if not candidates:
        candidates = [
            memory
            for memory in memories
            if isinstance(memory, dict)
            and memory.get("id") is not None
        ]

    if not candidates:
        return None

    memory = candidates[0]

    try:
        activity = create_activity(
            memory_id=memory["id"]
        )

        return activity

    except Exception as error:
        print(
            "MEMORY ACTIVITY CREATION ERROR:",
            error,
        )

        return None


# ============================================================
# DECISION ENGINE
# ============================================================

def decide_next_action(context):
    """
    Decide what the companion should do next.

    Priority:

        1. Reminder
        2. Cognitive activity
        3. Memory activity
        4. Check-in
        5. Normal conversation
    """

    # --------------------------------------------------------
    # 1. REMINDER
    # --------------------------------------------------------

    reminder = get_due_reminder()

    if reminder:
        return {
            "action": ACTION_REMINDER,
            "priority": PRIORITY_REMINDER,
            "reminder": reminder,
        }

    # --------------------------------------------------------
    # 2. COGNITIVE ACTIVITY
    # --------------------------------------------------------

    if should_start_cognitive_activity(context):

        return {
            "action": ACTION_COGNITIVE,
            "priority": PRIORITY_COGNITIVE,
            "activity": context.get(
                "next_activity"
            ),
        }

    # --------------------------------------------------------
    # 3. MEMORY ACTIVITY
    # --------------------------------------------------------

    if should_start_memory_activity(context):

        activity = _create_next_memory_activity(
            context
        )

        if activity:

            return {
                "action": ACTION_MEMORY,
                "priority": PRIORITY_MEMORY,
                "activity": activity,
            }

    # --------------------------------------------------------
    # 4. CHECK-IN
    # --------------------------------------------------------

    if should_check_in(context):

        return {
            "action": ACTION_CHECK_IN,
            "priority": PRIORITY_CHECK_IN,
        }

    # --------------------------------------------------------
    # 5. NORMAL CONVERSATION
    # --------------------------------------------------------

    return {
        "action": ACTION_CONVERSATION,
        "priority": PRIORITY_CONVERSATION,
    }


# ============================================================
# ACTION EXECUTION
# ============================================================

def execute_next_action(decision, context=None):
    """
    Convert a decision into a companion action response.
    """

    if not decision:
        return {
            "success": True,
            "action": ACTION_CONVERSATION,
            "priority": PRIORITY_CONVERSATION,
            "message": None,
        }

    action = decision.get("action")

    # ========================================================
    # REMINDER
    # ========================================================

    if action == ACTION_REMINDER:

        reminder = decision.get("reminder")

        if not reminder:
            return {
                "success": True,
                "action": ACTION_CONVERSATION,
                "priority": PRIORITY_CONVERSATION,
                "message": None,
            }

        reminder_id = reminder.get("id")

        if reminder_id is None:
            return {
                "success": True,
                "action": ACTION_REMINDER,
                "priority": PRIORITY_REMINDER,
                "reminder": reminder,
                "message": reminder.get(
                    "message",
                    "I have a gentle reminder for you.",
                ),
            }

        try:
            started_reminder = start_reminder(
                reminder_id
            )

            if started_reminder:
                reminder = started_reminder

        except Exception as error:
            print(
                "REMINDER START ERROR:",
                error,
            )

        reminder_message = reminder.get(
            "message",
            "I have a gentle reminder for you.",
        )

        return {
            "success": True,
            "action": ACTION_REMINDER,
            "priority": PRIORITY_REMINDER,
            "reminder": reminder,
            "message": (
                "Just a gentle reminder: "
                f"{reminder_message}"
            ),
        }

    # ========================================================
    # COGNITIVE ACTIVITY
    # ========================================================

    if action == ACTION_COGNITIVE:

        activity = decision.get("activity")

        return {
            "success": True,
            "action": ACTION_COGNITIVE,
            "priority": PRIORITY_COGNITIVE,
            "activity": activity,
            "message": (
                "Would you like to do a short "
                "activity with me?"
            ),
        }

    # ========================================================
    # MEMORY ACTIVITY
    # ========================================================

    if action == ACTION_MEMORY:

        activity = decision.get("activity")

        if not activity:

            return {
                "success": True,
                "action": ACTION_CONVERSATION,
                "priority": PRIORITY_CONVERSATION,
                "message": None,
            }

        return {
            "success": True,
            "action": ACTION_MEMORY,
            "priority": PRIORITY_MEMORY,
            "activity": activity,
            "message": (
                "Let's spend a little time "
                "remembering together."
            ),
        }

    # ========================================================
    # CHECK-IN
    # ========================================================

    if action == ACTION_CHECK_IN:

        return {
            "success": True,
            "action": ACTION_CHECK_IN,
            "priority": PRIORITY_CHECK_IN,
            "message": (
                "How are you feeling right now?"
            ),
        }

    # ========================================================
    # NORMAL CONVERSATION
    # ========================================================

    return {
        "success": True,
        "action": ACTION_CONVERSATION,
        "priority": PRIORITY_CONVERSATION,
        "message": None,
    }


# ============================================================
# MAIN COMPANION ACTION
# ============================================================

def get_next_companion_action():
    """
    Main public entry point used by app.py.

    This is the function your Flask application imports.
    """

    context = get_current_context()

    decision = decide_next_action(
        context
    )

    result = execute_next_action(
        decision,
        context,
    )

    result["context"] = context

    return result


# ============================================================
# COMPATIBILITY HELPERS
# ============================================================

def get_companion_decision():
    """
    Compatibility alias for callers that want only the decision.
    """

    context = get_current_context()

    return decide_next_action(
        context
    )


def run_companion_cycle():
    """
    Compatibility alias for running one complete companion cycle.
    """

    return get_next_companion_action()


# ============================================================
# MODULE EXPORTS
# ============================================================

__all__ = [
    "ACTION_REMINDER",
    "ACTION_COGNITIVE",
    "ACTION_MEMORY",
    "ACTION_CHECK_IN",
    "ACTION_CONVERSATION",
    "get_current_context",
    "get_due_reminder",
    "should_check_in",
    "should_start_cognitive_activity",
    "should_start_memory_activity",
    "decide_next_action",
    "execute_next_action",
    "get_next_companion_action",
    "get_companion_decision",
    "run_companion_cycle",
]