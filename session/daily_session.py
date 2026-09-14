"""
Daily Care Session Generator

Creates caregiver-friendly daily activities
using existing memories and patient profile.

This is not medical treatment.
It only organizes DementiaCareAI activities.
"""


from datetime import datetime


from memory.memory_store import (
    get_memories
)


from analytics.patient_profile import (
    generate_patient_profile
)



# =====================================================
# SELECT MEMORY
# =====================================================


def select_memory():


    memories = get_memories()


    if not memories:

        return None


    # Prefer memories with people/events
    preferred = []


    for memory in memories:

        if memory.get("category") in [
            "people",
            "events"
        ]:

            preferred.append(memory)



    if preferred:

        return preferred[0]


    return memories[0]



# =====================================================
# CREATE QUESTION
# =====================================================


def create_question(memory):


    category = memory.get(
        "category"
    )


    name = memory.get(
        "name"
    )


    if category == "people":


        return (
            f"Do you remember {name}?"
        )



    if category == "events":


        return (
            f"Do you remember the {name}?"
        )



    return (
        f"Can you tell me about {name}?"
    )



# =====================================================
# DAILY SESSION
# =====================================================


def create_daily_session():


    memory = select_memory()



    if not memory:


        return {

            "status":
            "No memories available"

        }



    profile = generate_patient_profile()



    engagement = profile[

        "activity_analysis"

    ].get(

        "engagement_level",

        "Unknown"

    )



    question = create_question(
        memory
    )



    return {


        "session":

        "Daily Memory Engagement Session",



        "date":

        datetime.now().date().isoformat(),



        "activity":

        {


            "memory":

            memory.get("name"),



            "category":

            memory.get("category"),



            "question":

            question,



            "difficulty":

            (
                "Easy"
                if engagement == "High"
                else "Very Easy"
            )

        },



        "caregiver_tip":

        "Use photos or gentle hints if the patient needs support.",



        "generated_from":

        "Patient memory and interaction history"

    }