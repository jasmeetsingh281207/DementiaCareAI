"""
DementiaCareAI Supportive Response Layer

Adds emotional support before memory responses.

This module:
- does not diagnose
- does not provide medical advice
- only adjusts conversational tone
"""


def add_emotional_support(
        response,
        emotion
):


    if emotion == "confusion":


        return (

            "That's okay. "
            "Sometimes memories can be difficult to recall. "

            +
            response

        )



    if emotion == "sadness":


        return (

            "I'm here with you. "

            +
            response

        )



    if emotion == "frustration":


        return (

            "Let's take it slowly. "

            +
            response

        )



    if emotion == "anxiety":


        return (

            "You're safe. "
            "Let's look at this memory together. "

            +
            response

        )

    return response