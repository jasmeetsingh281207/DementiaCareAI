"""
DementiaCareAI Conversation Personality Engine

Purpose:
Transforms raw memory information into warm,
human-like dementia-friendly communication.

This module does NOT create memories.
It only improves communication style.

Works with:
- people
- pets
- places
- objects
- events
- family memories
- future AI vision memories
"""


import random



# ---------------------------------------------------------
# RESPONSE STYLE SETTINGS
# ---------------------------------------------------------


WARM_OPENINGS = [

    "Yes, I remember",

    "I remember",

    "This memory reminds me of",

    "I found this memory about"

]



SUPPORTIVE_ENDINGS = [

    "This seems like a meaningful memory.",

    "It looks like this memory is special to you.",

    "This is a wonderful memory to keep.",

    "This memory is connected with something important in your life."

]





# ---------------------------------------------------------
# TEXT CLEANING
# ---------------------------------------------------------


def clean_text(text):

    if not text:
        return None


    text = str(text).strip()


    replacements = {


        "patient daughter":
            "your daughter",


        "patient son":
            "your son",


        "patient wife":
            "your wife",


        "patient husband":
            "your husband",


        "patient":
            "you"

    }


    lower = text.lower()


    for old,new in replacements.items():

        if lower == old:

            return new


    return text





# ---------------------------------------------------------
# RELATIONSHIP HANDLER
# ---------------------------------------------------------


def describe_relationship(
        relationship
):


    if not relationship:

        return None


    relation = relationship.lower().strip()



    # Do not assume unknown relations

    known = {


        "daughter":
            "someone special in your family",


        "son":
            "someone special in your family",


        "wife":
            "someone important in your life",


        "husband":
            "someone important in your life",


        "friend":
            "a person connected with your life"


    }



    return known.get(

        relation,

        f"someone connected with your life"

    )





# ---------------------------------------------------------
# MAIN PERSONALITY TRANSFORMER
# ---------------------------------------------------------



def create_human_response(
        memory
):


    if not memory:


        return (

            "I could not find this memory yet. "
            "We can add more details whenever you want."

        )



    name = memory.get(
        "name",
        "this memory"
    )


    category = memory.get(
        "category",
        ""
    )


    relationship = describe_relationship(

        memory.get(
            "relationship"
        )

    )


    description = clean_text(

        memory.get(
            "description"
        )

    )


    tags = memory.get(
        "tags",
        []
    )



    opening = random.choice(
        WARM_OPENINGS
    )





    # -----------------------------------------------------
    # PEOPLE
    # -----------------------------------------------------


    if category == "people":



        sentence = f"{opening} {name}."


        if relationship:


            sentence += (

                f" {name} is {relationship}."

            )


        elif description:


            sentence += (

                f" {description}."

            )


        sentence += (

            " This memory is connected with "
            + ", ".join(tags)
            + "."

        ) if tags else ""


        sentence += " " + random.choice(
            SUPPORTIVE_ENDINGS
        )


        return sentence





    # -----------------------------------------------------
    # EVENTS
    # -----------------------------------------------------


    if category == "events":


        sentence = (

            f"{opening} {name}."

        )


        if description:

            sentence += (

                f" {description}."

            )


        sentence += (

            " It looks like this was an important moment."

        )


        return sentence





    # -----------------------------------------------------
    # PETS / OBJECTS / PLACES / UNKNOWN
    # -----------------------------------------------------


    sentence = (

        f"{opening} {name}."

    )


    if description:


        sentence += (

            f" {description}."

        )


    if tags:


        sentence += (

            " Related details include "
            + ", ".join(tags)
            + "."

        )


    sentence += (

        " This memory may have a special meaning for you."

    )


    return sentence