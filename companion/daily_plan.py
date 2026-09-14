from datetime import datetime, date

from companion.state import (
    set_current_activity,
    set_next_activity,
    add_today_activity,
    get_state
)


# =========================================================
# DAILY ROUTINE
# =========================================================

DAILY_PLAN = [
    {
        "id": "morning_greeting",
        "time": "08:00",
        "type": "conversation",
        "title": "Morning greeting",
        "description": "Greet the patient warmly and ask how they are feeling.",
        "duration_minutes": 5,
        "priority": 1,
        "requires_completion": True
    },

    {
        "id": "morning_routine",
        "time": "09:00",
        "type": "routine",
        "title": "Morning routine",
        "description": "Gently guide the patient through their morning routine.",
        "duration_minutes": 30,
        "priority": 2,
        "requires_completion": True
    },

    {
        "id": "breakfast",
        "time": "09:30",
        "type": "routine",
        "title": "Breakfast",
        "description": "Remind the patient about breakfast.",
        "duration_minutes": 30,
        "priority": 2,
        "requires_completion": True
    },

    {
        "id": "memory_activity",
        "time": "11:00",
        "type": "memory",
        "title": "Memory activity",
        "description": "Practice recognition of familiar people, places, or events.",
        "duration_minutes": 10,
        "priority": 3,
        "requires_completion": True
    },

    {
        "id": "morning_conversation",
        "time": "11:30",
        "type": "conversation",
        "title": "Friendly conversation",
        "description": "Have a short friendly conversation with the patient.",
        "duration_minutes": 10,
        "priority": 3,
        "requires_completion": True
    },

    {
        "id": "lunch",
        "time": "13:00",
        "type": "routine",
        "title": "Lunch",
        "description": "Remind the patient about lunch.",
        "duration_minutes": 30,
        "priority": 2,
        "requires_completion": True
    },

    {
        "id": "afternoon_conversation",
        "time": "14:00",
        "type": "conversation",
        "title": "Afternoon conversation",
        "description": "Check in with the patient and talk about their day.",
        "duration_minutes": 10,
        "priority": 3,
        "requires_completion": True
    },

    {
        "id": "cognitive_game",
        "time": "16:00",
        "type": "game",
        "title": "Cognitive activity",
        "description": "Play a short and gentle cognitive activity.",
        "duration_minutes": 10,
        "priority": 3,
        "requires_completion": True
    },

    {
        "id": "evening_checkin",
        "time": "19:00",
        "type": "conversation",
        "title": "Evening check-in",
        "description": "Ask how the patient's day went.",
        "duration_minutes": 10,
        "priority": 2,
        "requires_completion": True
    },

    {
        "id": "dinner",
        "time": "19:30",
        "type": "routine",
        "title": "Dinner",
        "description": "Remind the patient about dinner.",
        "duration_minutes": 30,
        "priority": 2,
        "requires_completion": True
    },

    {
        "id": "bedtime_routine",
        "time": "21:00",
        "type": "routine",
        "title": "Bedtime routine",
        "description": "Gently guide the patient toward their bedtime routine.",
        "duration_minutes": 30,
        "priority": 2,
        "requires_completion": True
    }
]


# =========================================================
# TIME HELPERS
# =========================================================

def get_current_time():
    return datetime.now().strftime("%H:%M")


def get_current_datetime():
    return datetime.now().isoformat()


def get_today():
    return date.today().isoformat()


def time_to_minutes(time_string):
    hour, minute = time_string.split(":")
    return int(hour) * 60 + int(minute)


# =========================================================
# PLAN ACCESS
# =========================================================

def get_daily_plan():
    return DAILY_PLAN


def get_activity_by_id(activity_id):

    for activity in DAILY_PLAN:

        if activity["id"] == activity_id:
            return activity

    return None


# =========================================================
# TODAY'S COMPLETED ACTIVITIES
# =========================================================

def get_completed_activity_ids():

    state = get_state()

    completed = state.get(
        "today_activities",
        []
    )

    result = []

    for activity in completed:

        if isinstance(activity, dict):

            activity_id = activity.get("id")

            if activity_id:
                result.append(activity_id)

        elif isinstance(activity, str):

            result.append(activity)

    return result


# =========================================================
# FIND NEXT ACTIVITY
# =========================================================

def get_next_activity():

    current_minutes = time_to_minutes(
        get_current_time()
    )

    completed_ids = get_completed_activity_ids()


    # -----------------------------------------------------
    # First: find activities that are currently due
    # -----------------------------------------------------

    due_activities = []

    for activity in DAILY_PLAN:

        activity_minutes = time_to_minutes(
            activity["time"]
        )

        if activity["id"] in completed_ids:
            continue

        if activity_minutes <= current_minutes:

            due_activities.append(
                activity
            )


    if due_activities:

        # Most recent unfinished activity
        # gets priority.
        due_activities.sort(
            key=lambda item: (
                time_to_minutes(item["time"]),
                -item.get("priority", 0)
            ),
            reverse=True
        )

        selected = due_activities[0]

        set_next_activity(
            selected
        )

        return selected


    # -----------------------------------------------------
    # Otherwise find the next future activity
    # -----------------------------------------------------

    future_activities = []

    for activity in DAILY_PLAN:

        if activity["id"] in completed_ids:
            continue

        activity_minutes = time_to_minutes(
            activity["time"]
        )

        if activity_minutes > current_minutes:

            future_activities.append(
                activity
            )


    future_activities.sort(
        key=lambda item: time_to_minutes(
            item["time"]
        )
    )


    if future_activities:

        selected = future_activities[0]

        set_next_activity(
            selected
        )

        return selected


    # -----------------------------------------------------
    # Everything completed
    # -----------------------------------------------------

    set_next_activity(None)

    return None


# =========================================================
# UPCOMING ACTIVITIES
# =========================================================

def get_next_activities(limit=5):

    current_minutes = time_to_minutes(
        get_current_time()
    )

    completed_ids = get_completed_activity_ids()

    upcoming = []

    for activity in DAILY_PLAN:

        if activity["id"] in completed_ids:
            continue

        activity_minutes = time_to_minutes(
            activity["time"]
        )

        if activity_minutes > current_minutes:

            upcoming.append(
                activity
            )


    upcoming.sort(
        key=lambda item: time_to_minutes(
            item["time"]
        )
    )

    return upcoming[:limit]


# =========================================================
# START ACTIVITY
# =========================================================

def start_activity(activity_id):

    activity = get_activity_by_id(
        activity_id
    )

    if activity is None:
        return None


    set_current_activity(
        activity
    )

    add_today_activity(
        activity
    )


    # Immediately calculate what comes next.
    get_next_activity()


    return activity


# =========================================================
# COMPLETE ACTIVITY
# =========================================================

def complete_activity(activity_id):

    activity = get_activity_by_id(
        activity_id
    )

    if activity is None:
        return None


    state = get_state()

    completed = state.get(
        "completed_today",
        []
    )

    if not isinstance(
        completed,
        list
    ):
        completed = []


    if activity_id not in completed:

        completed.append(
            activity_id
        )


    from companion.state import set_state

    set_state(
        "completed_today",
        completed
    )


    # Calculate next activity.
    next_activity = get_next_activity()


    return {
        "completed": activity,
        "next": next_activity
    }


# =========================================================
# CURRENT ACTIVITY
# =========================================================

def get_current_activity():

    state = get_state()

    return state.get(
        "current_activity"
    )


# =========================================================
# COMPANION RECOMMENDATION
# =========================================================

def get_companion_recommendation():

    current_activity = get_current_activity()

    if current_activity:

        return {
            "action": "continue",
            "activity": current_activity,
            "reason": "An activity is currently in progress."
        }


    next_activity = get_next_activity()


    if next_activity is None:

        return {
            "action": "rest",
            "activity": None,
            "reason": "Today's planned activities are complete."
        }


    current_minutes = time_to_minutes(
        get_current_time()
    )

    activity_minutes = time_to_minutes(
        next_activity["time"]
    )


    if activity_minutes <= current_minutes:

        action = "start"

        reason = (
            "This activity is due now "
            "and has not been completed."
        )

    else:

        action = "wait"

        reason = (
            "This is the next planned activity "
            "for the patient."
        )


    return {
        "action": action,
        "activity": next_activity,
        "reason": reason
    }