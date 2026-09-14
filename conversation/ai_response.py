"""
Natural Memory Conversation Generator

Uses memory data + personality layer
to create human friendly responses.
"""


from conversation.personality import (
    create_human_response
)



def generate_memory_response(
        memories,
        question=None
):


    if not memories:

        return (

            "I could not find a memory related to that. "
            "Would you like to add this memory?"

        )


    memory = memories[0]


    return create_human_response(
        memory
    )