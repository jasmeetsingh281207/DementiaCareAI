"""
DementiaCareAI Natural Memory Response Generator

Converts stored memories into natural conversational responses.

Designed for:
- dementia companion conversations
- text-to-speech output
- caregiver assistance

Rules:
- Never assumes unknown family structure
- Never invents information
- Uses only stored memory data
"""


# ==========================================================
# HELPERS
# ==========================================================


def clean(value):

    if not value:
        return None

    return str(value).strip()



def human_relationship(value):

    if not value:
        return None


    relationship = (
        value
        .strip()
        .lower()
    )


    mapping = {

        "daughter":
            "daughter",

        "son":
            "son",

        "wife":
            "wife",

        "husband":
            "husband",

        "friend":
            "friend",

        "mother":
            "mother",

        "father":
            "father"

    }


    return mapping.get(
        relationship,
        relationship
    )





# ==========================================================
# PERSON MEMORY RESPONSE
# ==========================================================


def generate_person_response(memory):


    name = clean(
        memory.get("name")
    )


    relationship = human_relationship(
        memory.get("relationship")
    )


    description = clean(
        memory.get("description")
    )


    tags = memory.get(
        "tags",
        []
    )



    response = (
        f"I remember {name}."
    )



    if relationship:


        response += (

            f" {name} is your "
            f"{relationship}."

        )



    elif description:


        response += (

            f" {description}."

        )



    if tags:


        useful_tags = [

            tag

            for tag in tags

            if tag.lower()
            not in [
                relationship,
                "family"
            ]

        ]


        if useful_tags:


            response += (

                " I remember this "
                "connection with "
                +
                ", ".join(useful_tags)
                +
                "."

            )



    return response





# ==========================================================
# EVENT MEMORY RESPONSE
# ==========================================================


def generate_event_response(memory):


    name = clean(
        memory.get("name")
    )


    description = clean(
        memory.get("description")
    )


    response = (

        f"I remember {name}."

    )


    if description:


        response += (

            f" {description}."

        )


    return response





# ==========================================================
# GENERAL MEMORY RESPONSE
# ==========================================================


def generate_general_response(memory):


    name = clean(
        memory.get("name")
    )


    description = clean(
        memory.get("description")
    )


    response = (

        f"I remember {name}."

    )


    if description:


        response += (

            f" {description}."

        )


    return response





# ==========================================================
# MAIN GENERATOR
# ==========================================================


def generate_memory_response(
        memories,
        question=None
):


    if not memories:


        return (

            "I could not find this memory "
            "yet. You can add more details "
            "so I can remember it better."

        )



    memory = memories[0]


    category = (

        memory.get(
            "category",
            ""
        )
        .lower()

    )



    if category == "people":


        return generate_person_response(
            memory
        )



    elif category == "events":


        return generate_event_response(
            memory
        )



    else:


        return generate_general_response(
            memory
        )