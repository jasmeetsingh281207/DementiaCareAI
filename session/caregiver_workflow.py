"""
Caregiver Workflow Manager

Connects:
Memory
Activities
Recommendations
Daily Sessions

Creates a complete caregiver experience.
"""


from session.daily_session import (
    create_daily_session
)

from analytics.recommendations import (
    generate_caregiver_recommendations
)

from memory.activity_engine import (
    create_activity
)



def create_caregiver_plan():

    session = create_daily_session()

    recommendations = (
        generate_caregiver_recommendations()
    )


    activity = create_activity()


    return {


        "workflow":
            "DementiaCareAI Caregiver Daily Plan",


        "session":

            session,


        "activity":

            activity,


        "guidance":

            recommendations,


        "caregiver_message":

            "Today's activity is designed using the patient's memories and previous interaction patterns."

    }