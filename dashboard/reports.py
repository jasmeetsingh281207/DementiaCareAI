from datetime import datetime

from database import (
    execute,
    fetch_all
)


# =========================================================
# RECORD MEMORY ACTIVITY RESULT
# =========================================================
#
# NOTE:
# This module does NOT perform medical assessment.
#
# It only stores interaction results from AI activities.
#
# Results mean:
#
# correct      -> patient recalled information
# partial      -> patient recalled some information
# needs_help   -> patient needed assistance
#
# These are activity outcomes only.
# =========================================================


def record_performance(
    activity_type,
    result,
    score,
    memory_id=None,
    activity_id=None,
    answer=None
):

    timestamp = datetime.now().isoformat()


    try:

        score = float(score)

    except Exception:

        score = 0.0


    score = max(
        0.0,
        min(
            1.0,
            score
        )
    )


    record_id = execute(
        """
        INSERT INTO cognitive_records
        (
            activity_type,
            result,
            score,
            memory_id,
            activity_id,
            answer,
            timestamp
        )

        VALUES
        (?, ?, ?, ?, ?, ?, ?)

        """,
        (
            activity_type,
            result,
            score,
            memory_id,
            activity_id,
            answer,
            timestamp
        )
    )


    return {

        "id": record_id,

        "activity_type":
            activity_type,

        "result":
            result,

        "score":
            score,

        "memory_id":
            memory_id,

        "activity_id":
            activity_id,

        "answer":
            answer,

        "timestamp":
            timestamp

    }



# =========================================================
# GET ACTIVITY HISTORY
# =========================================================


def get_performance_history(
    limit=50
):

    limit = max(
        1,
        min(
            int(limit),
            500
        )
    )


    return fetch_all(
        """
        SELECT

            id,
            activity_type,
            result,
            score,
            memory_id,
            activity_id,
            answer,
            timestamp

        FROM cognitive_records

        ORDER BY timestamp DESC

        LIMIT ?

        """,
        (
            limit,
        )
    )



# =========================================================
# ACTIVITY SUMMARY
# =========================================================
#
# This is NOT a health score.
#
# It only summarizes interaction history.
# =========================================================


def get_performance_summary():


    records = fetch_all(
        """
        SELECT

            result,
            score

        FROM cognitive_records

        ORDER BY timestamp ASC

        """
    )


    if not records:

        return {

            "total_activities":0,

            "responses":{

                "correct":0,

                "partial":0,

                "needs_help":0

            },

            "average_activity_score":0

        }



    total = len(records)


    response_count = {

        "correct":0,

        "partial":0,

        "needs_help":0

    }


    total_score = 0



    for record in records:


        result = record.get(
            "result"
        )


        if result in response_count:

            response_count[result] += 1



        total_score += float(
            record.get(
                "score",
                0
            )
        )



    return {

        "total_activities":
            total,


        "responses":
            response_count,


        "average_activity_score":
            round(
                total_score / total,
                3
            )

    }



# =========================================================
# ACTIVITY CATEGORY SUMMARY
# =========================================================


def get_activity_summary_by_type(
    activity_type
):


    records = fetch_all(
        """
        SELECT

            result,
            score,
            timestamp

        FROM cognitive_records

        WHERE activity_type = ?

        ORDER BY timestamp DESC

        """,
        (
            activity_type,
        )
    )


    return {

        "activity_type":
            activity_type,


        "total_attempts":
            len(records),


        "records":
            records

    }



# =========================================================
# MEMORY ENGAGEMENT HISTORY
# =========================================================


def get_memory_activity_history(
    memory_id,
    limit=50
):


    return fetch_all(
        """
        SELECT

            id,
            activity_type,
            result,
            score,
            activity_id,
            answer,
            timestamp

        FROM cognitive_records

        WHERE memory_id = ?

        ORDER BY timestamp DESC

        LIMIT ?

        """,
        (
            memory_id,
            limit
        )
    )



# =========================================================
# RECENT ACTIVITY LOG
# =========================================================


def get_recent_activity(
    limit=10
):


    return fetch_all(
        """
        SELECT

            id,
            activity_type,
            result,
            score,
            memory_id,
            activity_id,
            answer,
            timestamp

        FROM cognitive_records

        ORDER BY timestamp DESC

        LIMIT ?

        """,
        (
            limit
        )
    )



# =========================================================
# DASHBOARD FRIENDLY SUMMARY
# =========================================================


def get_interaction_dashboard():


    summary = get_performance_summary()


    return {

        "system":

            "DementiaCareAI Memory Interaction Summary",


        "description":

            "Shows AI activity participation only. "
            "It is not a medical assessment.",


        "summary":

            summary

    }



# =========================================================
# DELETE HISTORY
# =========================================================


def clear_performance_history():


    execute(
        """
        DELETE FROM cognitive_records
        """
    )


    return True

# =========================================================
# CAREGIVER DASHBOARD COMPATIBILITY WRAPPER
# =========================================================

def get_caregiver_dashboard():

    return get_interaction_dashboard()  