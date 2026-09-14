"""
DementiaCareAI Emotion Understanding Engine

Purpose:
- Detect emotional signals from conversation
- Adjust response style
- Provide supportive communication guidance

This is NOT a medical diagnosis system.
It only analyzes language patterns.
"""


# ==========================================================
# EMOTION KEYWORDS
# ==========================================================


EMOTION_PATTERNS = {


  "confusion": [

    "i don't know",
    "i dont know",
    "i forgot",
    "i forget",
    "i don't remember",
    "i dont remember",
    "i cannot remember",
    "i can't remember",
    "i can't recall",
    "i cannot recall",
    "who is that",
    "who was that"
    "what happened",
    "where am i",
    "remind me",
    "can you remind me"

],



    "sadness": [

        "sad",
        "lonely",
        "miss",
        "cry",
        "upset",
        "unhappy"

    ],



    "frustration": [

        "why can't i",
        "why cant i",
        "this is difficult",
        "i cannot",
        "it's hard",
        "too hard"

    ],



    "anxiety": [

        "worried",
        "scared",
        "afraid",
        "nervous",
        "help me"

    ]

}







# ==========================================================
# DETECT EMOTION
# ==========================================================


def detect_emotion(message):


    if not message:


        return {

            "emotion":
                "neutral",

            "confidence":
                0

        }



    text = (

        message
        .lower()
        .strip()

    )



    detected = []



    for emotion, patterns in EMOTION_PATTERNS.items():


        for pattern in patterns:


            if pattern in text:

                detected.append(
                    emotion
                )

                break




    if not detected:


        return {


            "emotion":
                "neutral",


            "confidence":
                0

        }




    return {


        "emotion":
            detected[0],


        "confidence":
            round(
                1 / len(detected),
                2
            )

    }






# ==========================================================
# RESPONSE STRATEGY
# ==========================================================


def get_support_strategy(emotion):


    strategies = {


        "confusion":

            "Provide reassurance and gentle memory hints.",



        "sadness":

            "Use warm supportive language and emotional reassurance.",



        "frustration":

            "Avoid correction. Encourage slowly.",



        "anxiety":

            "Provide calm reassurance and safety-focused language.",



        "neutral":

            "Provide normal conversational response."

    }



    return strategies.get(

        emotion,

        strategies["neutral"]

    )