from datetime import datetime


def process_patient_response(
    activity,
    answer
):

    return {

        "activity_id":
            activity.get("id"),

        "question":
            activity.get("question"),

        "patient_answer":
            answer,

        "answered_at":
            datetime.now().isoformat(),

        "status":
            "received"

    }