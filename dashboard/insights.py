"""
Caregiver intelligence layer
"""


from dashboard.reports import (
    get_performance_history,
    get_performance_summary
)



def generate_caregiver_insights():


    summary = get_performance_summary()

    history = get_performance_history(
        limit=100
    )


    insights = []


    total = summary.get(
        "total_activities",
        0
    )


    score = summary.get(
        "average_activity_score",
        0
    )


    if total == 0:

        return [
            "No activity data available yet."
        ]


    # Engagement

    if score >= 0.8:

        insights.append(
            "Patient is showing strong engagement with memory activities."
        )


    elif score >= 0.5:

        insights.append(
            "Patient is maintaining moderate recall performance."
        )


    else:

        insights.append(
            "Patient may benefit from simpler recall exercises."
        )



    # Assistance

    help_count = len(

        [

            x for x in history

            if x["result"] == "needs_help"

        ]

    )


    if help_count > 0:

        insights.append(

            f"{help_count} activities required caregiver assistance."

        )



    # Recommendation

    insights.append(

        "Continue using familiar people, places, and family events."

    )


    return insights