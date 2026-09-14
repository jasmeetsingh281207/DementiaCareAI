from datetime import datetime
import json

from database import (
    fetch_one,
    execute
)


# =========================================================
# TIME HELPERS
# =========================================================

def _now():

    return datetime.now().isoformat()



def _today():

    return datetime.now().strftime(
        "%Y-%m-%d"
    )



# =========================================================
# STATE STORAGE
# =========================================================

def set_state(
    key,
    value
):

    # SQLite cannot store dict/list directly
    # Convert them into JSON strings

    if isinstance(
        value,
        (dict, list)
    ):

        value = json.dumps(
            value
        )


    execute(
        """
        INSERT INTO companion_state (
            key,
            value,
            updated_at
        )
        VALUES (?, ?, ?)

        ON CONFLICT(key)
        DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
        """,
        (
            key,
            value,
            _now()
        )
    )


    return value



def get_state():

    rows = {}

    from database import fetch_all


    state_rows = fetch_all(
        """
        SELECT
            key,
            value
        FROM companion_state
        """
    )


    for row in state_rows:


        value = row["value"]


        # Convert JSON strings back
        # into dict/list

        if isinstance(
            value,
            str
        ):

            try:

                value = json.loads(
                    value
                )

            except Exception:

                pass


        rows[
            row["key"]
        ] = value


    return rows



# =========================================================
# CURRENT ACTIVITY
# =========================================================

def set_current_activity(
    activity
):

    if activity is None:

        return set_state(
            "current_activity",
            None
        )


    return set_state(
        "current_activity",
        activity
    )



def get_current_activity():

    state = get_state()

    return state.get(
        "current_activity"
    )



# =========================================================
# NEXT ACTIVITY
# =========================================================

def set_next_activity(
    activity
):

    if activity is None:

        return set_state(
            "next_activity",
            None
        )


    return set_state(
        "next_activity",
        activity
    )



def get_next_activity():

    state = get_state()

    return state.get(
        "next_activity"
    )



# =========================================================
# MOOD
# =========================================================

def set_mood(
    mood
):

    if not mood:

        mood = "unknown"


    return set_state(
        "current_mood",
        mood
    )



def get_mood():

    state = get_state()

    return state.get(
        "current_mood",
        "unknown"
    )



# =========================================================
# LAST INTERACTION
# =========================================================

def record_interaction(
    message
):

    set_state(
        "last_interaction",
        _now()
    )


    set_state(
        "conversation_active",
        "true"
    )


    return True



# =========================================================
# LAST MEMORY ACTIVITY
# =========================================================

def record_memory_activity(
    activity
):

    set_state(
        "last_memory_activity",
        activity
    )


    set_current_activity(
        activity
    )


    return activity



def get_last_memory_activity():

    state = get_state()


    return state.get(
        "last_memory_activity"
    )



# =========================================================
# TODAY'S ACTIVITIES
# =========================================================

def add_today_activity(
    activity
):

    state = get_state()


    today = _today()


    activities = state.get(
        "today_activities"
    )


    if not isinstance(
        activities,
        list
    ):

        activities = []



    activity_copy = dict(
        activity
    )


    activity_copy[
        "date"
    ] = today


    activity_copy[
        "status"
    ] = activity_copy.get(
        "status",
        "pending"
    )


    activities.append(
        activity_copy
    )


    set_state(
        "today_activities",
        activities
    )


    return activity_copy



# =========================================================
# MARK ACTIVITY COMPLETED
# =========================================================

def mark_activity_completed(
    activity_id,
    result=None
):

    state = get_state()


    activities = state.get(
        "today_activities"
    )


    if not isinstance(
        activities,
        list
    ):

        activities = []



    updated = False



    for activity in activities:


        if activity.get(
            "id"
        ) == activity_id:


            activity[
                "status"
            ] = "completed"


            activity[
                "completed_at"
            ] = _now()



            if result is not None:


                activity[
                    "result"
                ] = result



            updated = True



    if updated:


        set_state(
            "today_activities",
            activities
        )



    current = get_current_activity()



    if (
        current
        and current.get(
            "id"
        )
        == activity_id
    ):


        set_current_activity(
            None
        )



    return updated



# =========================================================
# RESET DAILY STATE
# =========================================================

def reset_daily_state():

    set_state(
        "today_activities",
        []
    )


    set_state(
        "last_activity_date",
        _today()
    )


    set_current_activity(
        None
    )


    return True



# =========================================================
# RECORD ACTIVITY
# =========================================================

def record_activity(
    activity,
    response
):


    activity_record = {

        "activity": activity,

        "response": response,

        "timestamp": _now(),

        "status": "completed"

    }



    activity_id = activity.get(
        "id"
    )



    if activity_id:


        mark_activity_completed(
            activity_id,
            response.get(
                "result"
            )
        )



    add_today_activity(
        activity_record
    )


    return activity_record



# =========================================================
# GET COMPANION STATE
# =========================================================

def get_companion_state():

    return get_state()