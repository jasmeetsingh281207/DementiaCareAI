"""
DementiaCareAI Dialogue Manager

Maintains short-term conversation context.

Responsibilities:
- Maintain conversation sessions
- Store recent user/assistant exchanges
- Track the most recently relevant memory
- Track the current conversation topic
- Support follow-up questions
- Provide context to the conversation engine

This module:
- Does NOT diagnose
- Does NOT generate medical advice
- Does NOT create permanent memories
- Does NOT call Gemini

Permanent information belongs in the database.
Short-term conversational state belongs here.
"""

from datetime import datetime


# =========================================================
# CONFIGURATION
# =========================================================

MAX_SESSION_MESSAGES = 20


# =========================================================
# INTERNAL SESSION MEMORY
# =========================================================

conversation_sessions = {}


# =========================================================
# CREATE SESSION
# =========================================================

def create_session():
    """
    Create a new short-term conversation session.

    Returns:
        str: Unique session ID
    """

    session_id = datetime.now().strftime(
        "%Y%m%d%H%M%S%f"
    )

    conversation_sessions[session_id] = {
        "messages": [],
        "last_memory": None,
        "last_topic": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    return session_id


# =========================================================
# GET SESSION
# =========================================================

def get_session(session_id):
    """
    Return an existing conversation session.
    """

    if not session_id:
        return None

    return conversation_sessions.get(session_id)


# =========================================================
# STORE MESSAGE
# =========================================================

def add_message(
    session_id,
    user_message,
    ai_response,
    memory=None
):
    """
    Store one user/assistant exchange.

    If a relevant memory is supplied, it becomes the
    current conversational memory.
    """

    session = get_session(session_id)

    if not session:
        return False

    if not user_message:
        return False

    if not ai_response:
        return False

    session["messages"].append(
        {
            "user": str(user_message).strip(),
            "assistant": str(ai_response).strip(),
            "time": datetime.now().isoformat(),
        }
    )

    # Keep only recent conversational exchanges.
    if len(session["messages"]) > MAX_SESSION_MESSAGES:
        session["messages"] = session["messages"][
            -MAX_SESSION_MESSAGES:
        ]

    # Update contextual memory when available.
    if memory:
        session["last_memory"] = memory

        memory_name = memory.get("name")

        if memory_name:
            session["last_topic"] = memory_name

    session["updated_at"] = datetime.now().isoformat()

    return True


# =========================================================
# UPDATE CONTEXT MEMORY
# =========================================================

def set_context_memory(session_id, memory):
    """
    Explicitly set the current conversational memory.

    Useful when a memory is identified separately from
    storing an assistant response.
    """

    session = get_session(session_id)

    if not session:
        return False

    if not memory:
        return False

    session["last_memory"] = memory

    memory_name = memory.get("name")

    if memory_name:
        session["last_topic"] = memory_name

    session["updated_at"] = datetime.now().isoformat()

    return True


# =========================================================
# FOLLOW-UP DETECTION
# =========================================================

def is_follow_up_question(message):
    """
    Determine whether the current message appears to depend
    on previous conversation context.

    This is intentionally broad.

    It does not decide what the user means.
    It only tells the conversation engine that previous
    context may be useful.
    """

    if not message:
        return False

    text = str(message).lower().strip()

    follow_up_patterns = [
        "tell me more",
        "more about",
        "what about",
        "who is that",
        "who was that",
        "who is she",
        "who is he",
        "who was she",
        "who was he",
        "what does she",
        "what does he",
        "where is she",
        "where is he",
        "where does she",
        "where does he",
        "when did she",
        "when did he",
        "when was she",
        "when was he",
        "why did she",
        "why did he",
        "how old is she",
        "how old is he",
        "tell me again",
        "remind me",
        "again",
        "about her",
        "about him",
        "about them",
        "she",
        "he",
        "her",
        "him",
        "they",
        "them",
        "that person",
        "that event",
        "that memory",
    ]

    return any(
        pattern in text
        for pattern in follow_up_patterns
    )


# =========================================================
# GET CONTEXT MEMORY
# =========================================================

def get_context_memory(session_id):
    """
    Return the most recently relevant memory.
    """

    session = get_session(session_id)

    if not session:
        return None

    return session.get("last_memory")


# =========================================================
# GET LAST TOPIC
# =========================================================

def get_last_topic(session_id):
    """
    Return the name of the most recent conversational topic.
    """

    session = get_session(session_id)

    if not session:
        return None

    return session.get("last_topic")


# =========================================================
# GET RECENT HISTORY
# =========================================================

def get_conversation_history(session_id, limit=10):
    """
    Return recent conversation exchanges.

    Most recent messages are returned last so the result can
    be passed naturally into Gemini context.
    """

    session = get_session(session_id)

    if not session:
        return []

    messages = session.get("messages", [])

    if limit <= 0:
        return []

    return messages[-limit:]


# =========================================================
# GENERATE CONTEXT REFERENCE
# =========================================================

def generate_context_reference(session_id):
    """
    Generate a compact human-readable reference to the
    currently active memory.

    This is primarily useful for debugging or lightweight
    context display.
    """

    memory = get_context_memory(session_id)

    if not memory:
        return None

    name = memory.get("name")
    relationship = memory.get("relationship")
    description = memory.get("description")

    if name and relationship:
        reference = (
            f"The current conversation is about {name}, "
            f"who is described in the saved memory as "
            f"the patient's {relationship.lower()}."
        )

        if description:
            reference += f" Description: {description}."

        return reference

    if name:
        reference = (
            f"The current conversation is about {name}."
        )

        if description:
            reference += f" Description: {description}."

        return reference

    return None


# =========================================================
# CLEAR SESSION
# =========================================================

def clear_session(session_id):
    """
    Remove a conversation session from short-term memory.
    """

    if session_id in conversation_sessions:
        del conversation_sessions[session_id]
        return True

    return False


# =========================================================
# CLEAR ALL SESSIONS
# =========================================================

def clear_all_sessions():
    """
    Clear all in-memory conversation sessions.
    """

    conversation_sessions.clear()

    return True