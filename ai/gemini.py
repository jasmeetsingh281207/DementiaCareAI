import json
import os
from datetime import datetime

from dotenv import load_dotenv
from google import genai
from ai.gemini_service import get_client as _canonical_gemini_client, model_name as _canonical_model_name

from database import (
    get_conversation_history,
    save_conversation_message
)

from patient.context import (
    get_patient_context
)

from memory.memory_store import (
    get_memories
)

from companion.state import (
    get_state
)

from companion.daily_plan import (
    get_companion_recommendation
)

from tools.reminders import (
    create_reminder
)


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

api_key = os.getenv(
    "GEMINI_API_KEY"
)

# =========================================================
# GEMINI CLIENT
# =========================================================

client = None  # legacy module; initialize only when its compatibility entrypoint is invoked


MODEL_NAME = _canonical_model_name()


# =========================================================
# SYSTEM INSTRUCTION
# =========================================================

SYSTEM_INSTRUCTION = """

You are DementiaCareAI.

You are a warm, calm, patient AI companion designed
to support people living with dementia and their caregivers.

Your goal is to behave like a continuous daily companion,
not like a generic chatbot.

You are NOT just a question-answering chatbot.

You should behave like a familiar,
kind household companion.

=========================================================
COMMUNICATION STYLE
=========================================================

- Be warm and friendly.
- Be patient.
- Be gentle.
- Use short, simple sentences.
- Use everyday language.
- Avoid complicated explanations.
- Ask only one question at a time.
- Never sound robotic.
- Never shame the patient.
- Never make the patient feel embarrassed.
- Never aggressively correct the patient.
- Encourage the patient.
- If the patient seems confused, gently guide them.
- Repeat information calmly when appropriate.
- Prefer reassurance over correction.
- Keep conversations natural.
- Do not overwhelm the patient with many choices.

=========================================================
CONTINUOUS COMPANION BEHAVIOR
=========================================================

You are a daily companion.

Use the current time, patient context,
conversation history, companion state,
stored memories, and daily recommendation
to make the conversation feel continuous.

If an appropriate daily activity is coming up,
you may gently mention it.

Examples:

"Good morning. How are you feeling today?"

"It is almost time for breakfast."

"Would you like to do a small memory activity?"

"It looks like we have a quiet afternoon.
Would you like to chat?"

Do not constantly talk about schedules.

Do not make every conversation about dementia.

The patient should feel like they are talking
to a familiar person.

=========================================================
MEMORY BEHAVIOR
=========================================================

The system provides stored patient memories.

Use those memories naturally when relevant.

Never invent memories.

Never invent family relationships.

Never invent names.

Never invent events.

Never invent dates.

If the information exists in the provided memories,
use it naturally.

Example stored memory:

Name: Simran
Relationship: Daughter

If the patient asks:

"Who is Simran?"

You should answer:

"Simran is your daughter."

Do NOT answer:

"I don't have any information."

when the information exists in stored memories.

If only a name is known:

"I remember Simran."

If the system does not contain the requested information,
say that you are not sure and gently suggest asking
a caregiver.

=========================================================
CONVERSATION MEMORY
=========================================================

You will receive recent conversation history.

Use it to understand the current conversation.

Do not repeat questions unnecessarily.

If the patient already explained something,
do not immediately ask for the same information again.

Do not claim to remember something unless
it exists in the supplied conversation history
or stored memory.

Use previous conversation naturally.

=========================================================
PATIENT CONTEXT
=========================================================

You will receive structured patient information.

Use it to personalize conversations when appropriate.

Never expose:

- database IDs
- database structure
- file paths
- API details
- technical information
- internal state names

=========================================================
COMPANION STATE
=========================================================

You will receive the current companion state.

Use it to understand:

- current activity
- current mood
- recent interaction
- memory activity
- conversation state
- daily activity progress

Do not tell the patient about internal state fields.

=========================================================
DAILY RECOMMENDATION
=========================================================

You may receive a companion recommendation.

Use it to understand what the companion
thinks may be appropriate next.

Do not force the recommendation.

If the patient wants something else,
follow the patient's conversation.

The recommendation is guidance,
not an instruction.

=========================================================
DEMENTIA SUPPORT
=========================================================

When the patient forgets something:

Do not say:

"You are wrong."

Do not say:

"You forgot again."

Instead say things such as:

"That's okay. Let's remember together."

"That's alright. We can take our time."

"I can help you with that."

When appropriate, gently provide the known information.

=========================================================
LANGUAGE
=========================================================

The patient may speak in:

- English
- Hindi
- Hinglish
- simple Indian English
- other languages

Respond in the language the patient is using
whenever reasonably possible.

If the patient switches language,
you may switch with them.

Keep the language simple and natural.

=========================================================
REMINDERS
=========================================================

Use create_reminder only when the patient
explicitly asks to be reminded about something.

The reminder time must use:

YYYY-MM-DD HH:MM

If the time is unclear,
ask the patient for the time.

Never claim that a reminder was created
unless the reminder tool confirms it.

=========================================================
SAFETY
=========================================================

You are not a doctor.

Never diagnose a medical condition.

Never tell the patient to start medication.

Never tell the patient to stop medication.

Never change medication doses.

Never present a medical guess as a diagnosis.

If there is a possible emergency,
encourage contacting a caregiver,
doctor, or emergency medical service.

If the patient appears frightened,
confused, or distressed,
respond calmly and encourage contacting
a trusted caregiver when appropriate.

=========================================================
PRIMARY GOAL
=========================================================

Your primary goal is to make the patient feel:

- supported
- remembered
- safe
- respected
- understood
- calm
- cared for

You are DementiaCareAI,
a continuous daily companion.
"""


# =========================================================
# GEMINI TOOL
# =========================================================

CREATE_REMINDER_TOOL = {

    "type": "function",

    "name": "create_reminder",

    "description": (
        "Create a reminder for the patient. "
        "Use this function only when the patient "
        "explicitly asks to be reminded about something."
    ),

    "parameters": {

        "type": "object",

        "properties": {

            "message": {

                "type": "string",

                "description": (
                    "What the patient wants to remember."
                )
            },

            "reminder_time": {

                "type": "string",

                "description": (
                    "Exact reminder time in "
                    "YYYY-MM-DD HH:MM format."
                )
            }
        },

        "required": [
            "message",
            "reminder_time"
        ]
    }
}


# =========================================================
# TOOL EXECUTION
# =========================================================

def execute_tool(
    name,
    arguments
):

    print()
    print("TOOL CALL DETECTED")
    print("Tool:", name)
    print("Arguments:", arguments)

    if name == "create_reminder":

        message = arguments.get(
            "message"
        )

        reminder_time = arguments.get(
            "reminder_time"
        )

        if not message:

            raise ValueError(
                "Reminder message is required."
            )

        if not reminder_time:

            raise ValueError(
                "Reminder time is required."
            )

        result = create_reminder(
            message=message,
            reminder_time=reminder_time
        )

        print(
            "TOOL RESULT:",
            result
        )

        return result

    raise ValueError(
        f"Unknown tool: {name}"
    )


# =========================================================
# MEMORY CONTEXT
# =========================================================

def build_memory_context():

    memories = get_memories()

    if not memories:

        return (
            "No stored memories are available."
        )

    simplified_memories = []

    for memory in memories:

        simplified_memories.append({

            "category": memory.get(
                "category"
            ),

            "name": memory.get(
                "name"
            ),

            "relationship": memory.get(
                "relationship"
            ),

            "description": memory.get(
                "description"
            ),

            "event_date": memory.get(
                "event_date"
            ),

            "tags": memory.get(
                "tags",
                []
            )
        })

    return json.dumps(
        simplified_memories,
        ensure_ascii=False,
        indent=2
    )


# =========================================================
# CONVERSATION CONTEXT
# =========================================================

def build_conversation_context():

    history = get_conversation_history(
        limit=20
    )

    if not history:

        return (
            "No previous conversation."
        )

    lines = []

    for item in history:

        role = item.get(
            "role"
        )

        message = item.get(
            "message",
            ""
        )

        if role == "user":

            label = "Patient"

        else:

            label = "DementiaCareAI"

        lines.append(
            f"{label}: {message}"
        )

    return "\n".join(
        lines
    )


# =========================================================
# PATIENT CONTEXT
# =========================================================

def build_patient_context():

    context = get_patient_context()

    return json.dumps(
        context,
        ensure_ascii=False,
        indent=2
    )


# =========================================================
# COMPANION STATE
# =========================================================

def build_companion_context():

    state = get_state()

    return json.dumps(
        state,
        ensure_ascii=False,
        indent=2
    )


# =========================================================
# COMPANION RECOMMENDATION
# =========================================================

def build_companion_recommendation():

    try:

        recommendation = (
            get_companion_recommendation()
        )

    except Exception as error:

        print(
            "COMPANION RECOMMENDATION ERROR:",
            error
        )

        recommendation = {
            "available": False
        }

    return json.dumps(
        recommendation,
        ensure_ascii=False,
        indent=2
    )


# =========================================================
# MAIN GEMINI FUNCTION
# =========================================================

def ask_gemini(message):

    if not message:

        raise ValueError(
            "Message is required."
        )

    # Compatibility entrypoint retained for older callers.  The former
    # interactions.create tool loop is obsolete; all active generation now
    # runs through the canonical conversation pipeline.
    from conversation.conversation_engine import process_message
    result = process_message(str(message))
    return result.get("response", "I'm here with you.")


    # -----------------------------------------------------
    # Current date and time
    # -----------------------------------------------------

    current_datetime = (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )
    )


    # -----------------------------------------------------
    # Load persistent context
    # -----------------------------------------------------

    patient_context = (
        build_patient_context()
    )

    memory_context = (
        build_memory_context()
    )

    conversation_context = (
        build_conversation_context()
    )

    companion_context = (
        build_companion_context()
    )

    recommendation_context = (
        build_companion_recommendation()
    )


    # -----------------------------------------------------
    # Build Gemini input
    # -----------------------------------------------------

    user_input = f"""

CURRENT DATE AND TIME:
{current_datetime}

PATIENT PROFILE:
{patient_context}

STORED PATIENT MEMORIES:
{memory_context}

CURRENT COMPANION STATE:
{companion_context}

CURRENT COMPANION RECOMMENDATION:
{recommendation_context}

RECENT CONVERSATION:
{conversation_context}

NEW PATIENT MESSAGE:
{message}

Respond naturally as DementiaCareAI.
"""


    # -----------------------------------------------------
    # Save patient message
    # -----------------------------------------------------

    save_conversation_message(
        role="user",
        message=message
    )


    # -----------------------------------------------------
    # First Gemini interaction
    # -----------------------------------------------------

    interaction = client.interactions.create(

        model=MODEL_NAME,

        system_instruction=(
            SYSTEM_INSTRUCTION
        ),

        input=user_input,

        tools=[
            CREATE_REMINDER_TOOL
        ]
    )


    print()
    print("==============================================")
    print("GEMINI INTERACTION")
    print("==============================================")

    print(
        "Interaction ID:",
        interaction.id
    )


    # -----------------------------------------------------
    # Debug interaction steps
    # -----------------------------------------------------

    try:

        for step in interaction.steps:

            print(
                "STEP:",
                step.type,
                getattr(
                    step,
                    "name",
                    None
                )
            )

    except Exception as error:

        print(
            "STEP DEBUG ERROR:",
            error
        )


    # -----------------------------------------------------
    # Find function calls
    # -----------------------------------------------------

    function_calls = [

        step

        for step in interaction.steps

        if step.type == "function_call"
    ]


    # -----------------------------------------------------
    # Normal response
    # -----------------------------------------------------

    if not function_calls:

        response = (
            interaction.output_text
        )

        if not response:

            response = (
                "I'm here with you. "
                "How are you feeling?"
            )

        save_conversation_message(

            role="assistant",

            message=response
        )

        print()
        print(
            "FINAL GEMINI RESPONSE:"
        )

        print(
            response
        )

        return response


    # -----------------------------------------------------
    # Execute tools
    # -----------------------------------------------------

    function_results = []


    for function_call in function_calls:

        try:

            arguments = (
                function_call.arguments
            )

            if isinstance(
                arguments,
                str
            ):

                arguments = json.loads(
                    arguments
                )


            result = execute_tool(

                function_call.name,

                arguments
            )


            result_text = json.dumps(

                result,

                ensure_ascii=False
            )


        except Exception as error:

            print()
            print(
                "TOOL ERROR:",
                error
            )

            result_text = json.dumps({

                "success": False,

                "error": str(error)
            })


        function_results.append({

            "type": "function_result",

            "name": (
                function_call.name
            ),

            "call_id": (
                function_call.id
            ),

            "result": [

                {
                    "type": "text",

                    "text": result_text
                }
            ]
        })


    # -----------------------------------------------------
    # Continue Gemini interaction
    # -----------------------------------------------------

    final_interaction = (
        client.interactions.create(

            model=MODEL_NAME,

            previous_interaction_id=(
                interaction.id
            ),

            input=function_results
        )
    )


    response = (
        final_interaction.output_text
    )


    if not response:

        response = (
            "Okay. I've taken care of that for you."
        )


    # -----------------------------------------------------
    # Save assistant response
    # -----------------------------------------------------

    save_conversation_message(

        role="assistant",

        message=response
    )


    print()
    print(
        "FINAL GEMINI RESPONSE:"
    )

    print(
        response
    )

    return response
