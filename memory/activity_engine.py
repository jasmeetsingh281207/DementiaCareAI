from datetime import datetime
import json
import uuid


from ai.gemini_service import get_client, generate


from memory.memory_store import (
    get_memories,
    get_memory_media
)

from memory.vision import (
    get_all_media_analysis
)

from companion.state import (
    record_memory_activity,
    record_activity
)


from cognitive.tracker import (
    record_performance
)
from database import execute



# =========================================================
# GEMINI INITIALIZATION
# =========================================================


def get_gemini_client():
    """Compatibility alias for the canonical lazy Gemini client."""
    return get_client()



# =========================================================
# HELPERS
# =========================================================


def normalize_answer(
    answer
):

    if not answer:

        return ""

    return " ".join(
        str(answer)
        .lower()
        .strip()
        .split()
    )



def safe_json_parse(
    text
):

    if not text:

        return None


    text = text.strip()


    if text.startswith(
        "```"
    ):

        text = (
            text
            .replace(
                "```json",
                ""
            )
            .replace(
                "```",
                ""
            )
            .strip()
        )


    start = text.find(
        "{"
    )

    end = text.rfind(
        "}"
    )


    if start != -1 and end != -1:

        text = text[
            start:end+1
        ]


    try:

        return json.loads(
            text
        )

    except Exception:

        return None



def build_media_response(
    media
):

    result = []


    for item in media:


        data = dict(
            item
        )


        data["media_url"] = (
            "/api/memories/"
            f"{item['memory_id']}"
            "/media/"
            f"{item['id']}"
            "/file"
        )


        result.append(
            data
        )


    return result



# =========================================================
# MEMORY CONTEXT
# =========================================================

def build_memory_context(
    memory,
    media
):

    visual_context = []


    # =====================================================
    # LOAD GEMINI VISION ANALYSIS
    # =====================================================

    try:

        analyses = get_all_media_analysis(
            memory["id"]
        )


        for item in analyses:

            analysis = item.get(
                "analysis"
            )


            if analysis:

                visual_context.append(
                    analysis
                )


    except Exception as error:

        print(
            "VISION CONTEXT ERROR:",
            error
        )



    return {

        "name":
            memory.get(
                "name"
            ),


        "category":
            memory.get(
                "category"
            ),


        "relationship":
            memory.get(
                "relationship"
            ),


        "description":
            memory.get(
                "description"
            ),


        "event_date":
            memory.get(
                "event_date"
            ),


        "tags":
            memory.get(
                "tags",
                []
            ),


        "visual_context":
            visual_context

    }


    return {

        "name":
            memory.get(
                "name"
            ),

        "category":
            memory.get(
                "category"
            ),

        "relationship":
            memory.get(
                "relationship"
            ),

        "description":
            memory.get(
                "description"
            ),

        "event_date":
            memory.get(
                "event_date"
            ),

        "tags":
            memory.get(
                "tags",
                []
            ),

        "visual_context":
            visual_context
    }



# =========================================================
# GEMINI QUESTION GENERATOR
# =========================================================


def generate_question(
    context
):


    gemini_client = get_gemini_client()

    if not gemini_client:

        return None



    prompt = f"""

Create one gentle memory recall question
for a dementia care companion.

Memory:

{json.dumps(
    context,
    indent=2,
    ensure_ascii=False
)}


Rules:

- Use simple language.
- Ask only one question.
- Do not identify faces.
- Do not guess names from images.
- Use caregiver information as truth.
- Use visual information only as context.
- Make the question comfortable.
- Avoid pressure.

Return only the question.

"""


    try:

        return generate(prompt)


    except Exception as error:

        print(
            "Question generation error:",
            error
        )

        return None



# =========================================================
# CREATE MEMORY ACTIVITY
# =========================================================


def create_activity(
    memory_id=None,
    category=None
):


    memories = get_memories(
        category
    )


    if memory_id:


        memories = [

            m

            for m in memories

            if str(
                m["id"]
            )
            ==
            str(memory_id)

        ]



    if not memories:

        return None



    memory = memories[0]



    media = get_memory_media(
        memory["id"]
    )


    context = build_memory_context(
        memory,
        media
    )



    question = generate_question(
        context
    )



    if not question:


        fallback = {

            "people":
            "Do you remember this person?",

            "places":
            "Do you remember this place?",

            "events":
            "Do you remember this event?"

        }


        question = fallback.get(

            memory.get(
                "category"
            ),

            "Do you remember this memory?"

        )



    activity = {


        "id":
            str(
                uuid.uuid4()
            ),


        "type":
            f"{memory.get('category')}_recall",


        "memory_id":
            memory["id"],


        "question":
            question,


        "status":
            "pending",



        "memory":{


            "id":
                memory["id"],


            "name":
                memory.get(
                    "name"
                ),


            "category":
                memory.get(
                    "category"
                ),


            "relationship":
                memory.get(
                    "relationship"
                ),


            "description":
                memory.get(
                    "description"
                ),


            "tags":
                memory.get(
                    "tags",
                    []
                ),


            "media":
                build_media_response(
                    media
                ),


            "visual_context":
                context[
                    "visual_context"
                ]

        },


        "created_at":
            datetime.now()
            .isoformat()

    }



    record_memory_activity(
        activity
    )

    # Persist activities as well as companion state so caregiver analytics
    # and restart-safe completion tracking use real records.
    execute("""INSERT OR REPLACE INTO activities
        (id, activity_type, memory_id, question, result, created_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)""", (
        activity["id"], activity["type"], activity["memory_id"], activity["question"],
        None, activity["created_at"], None,
    ))


    return activity



# =========================================================
# ANSWER MATCHING
# =========================================================


def get_expected_answers(
    memory
):


    answers=[]


    for key in [

        "name",

        "relationship"

    ]:


        value = memory.get(
            key
        )


        if value:

            answers.append(
                normalize_answer(
                    value
                )
            )


    for tag in memory.get(
        "tags",
        []
    ):


        answers.append(
            normalize_answer(
                tag
            )
        )


    return answers



def local_match(
    answer,
    expected
):


    answer = normalize_answer(
        answer
    )


    for item in expected:


        if (

            answer == item

            or

            item in answer

        ):

            return True


    return False



# =========================================================
# GEMINI ANSWER CHECK
# =========================================================


def evaluate_with_gemini(
    activity,
    answer
):


    gemini_client = get_gemini_client()

    if not gemini_client:

        return None



    prompt=f"""

Evaluate dementia memory recall.

Memory:

{json.dumps(
activity["memory"],
indent=2
)}


Question:

{activity["question"]}


Patient answer:

{answer}


Return JSON only:

{{
"result":"correct",
"score":1,
"encouragement":""
}}


Allowed:

correct

partial

needs_help

"""


    try:


        response_text = generate(prompt)
        return safe_json_parse(response_text) if response_text else None


    except Exception:

        return None



# =========================================================
# FINAL EVALUATION
# =========================================================


def evaluate_answer(
    activity,
    answer
):


    memory = activity.get(
        "memory"
    )


    expected = get_expected_answers(
        memory
    )



    result = None


    ai = evaluate_with_gemini(
        activity,
        answer
    )



    if ai:

        result = ai.get(
            "result"
        )

        score=float(
            ai.get(
                "score",
                0
            )
        )

    elif local_match(
        answer,
        expected
    ):

        result="correct"

        score=1.0


    else:

        result="needs_help"

        score=0.0



    if result=="partial":

        score=0.5

        result="needs_help"



    performance = record_performance(

        activity_type=
            activity.get(
                "type"
            ),

        result=result,

        score=score,

        memory_id=
            memory.get(
                "id"
            ),

        activity_id=
            activity.get(
                "id"
            ),

        answer=answer

    )



    completed=dict(
        activity
    )


    completed["status"]="completed"


    completed["completed_at"]=(
        datetime.now()
        .isoformat()
    )



    response={


        "result":
            result,


        "score":
            score,


        "encouragement":
            (
            "You remembered that!"
            if result=="correct"
            else
            "That's okay. Let's remember together."
            ),


        "performance":
            performance,


        "timestamp":
            datetime.now()
            .isoformat()

    }



    record_activity(
        completed,
        response
    )

    execute("""UPDATE activities SET result = ?, completed_at = ? WHERE id = ?""", (
        result, completed["completed_at"], activity.get("id"),
    ))


    return response
