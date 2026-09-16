from pathlib import Path

from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory,
)

# ============================================================
# LANGUAGE
# ============================================================

import language

print("=" * 70)
print("LANGUAGE MODULE LOADED FROM:")
print(language.__file__)
print("=" * 70)

from language import (
    normalize_language,
    detect_language,
    get_language,
    list_languages,
    translate_text,
    prepare_for_companion,
    prepare_response,
    get_language_status,
)


# ============================================================
# VOICE
# ============================================================

from voice import (
    get_voice_config,
    get_voice_status,
    browser_voice_instruction,
    process_voice_transcript,
    validate_audio_payload,
)


# ============================================================
# CAREGIVER INTELLIGENCE
# ============================================================

from dashboard.caregiver import (
    get_caregiver_overview,
    get_caregiver_today,
    get_caregiver_weekly,
    get_caregiver_activity,
    get_caregiver_cognitive,
    get_caregiver_memory,
    get_caregiver_reminders,
    get_caregiver_conversation,
    get_caregiver_companion,
    get_caregiver_recommendations,
    generate_caregiver_report,
)


# ============================================================
# DATABASE
# ============================================================

from database import (
    initialize_database,
)


# ============================================================
# COMPANION
# ============================================================

from companion.orchestrator import (
    get_next_companion_action,
)

from companion.engine import (
    get_engine_status,
)

# HTTP conversation requests use the canonical, database-first engine.
# Keep companion.engine available for its non-conversation status support.
from conversation.conversation_engine import (
    process_message,
)

from companion.state import (
    get_state,
    set_current_activity,
    set_next_activity,
    set_mood,
)

from companion.daily_plan import (
    get_daily_plan,
    get_next_activity,
    get_next_activities,
    start_activity,
    complete_activity,
    get_companion_recommendation,
)


# ============================================================
# REMINDERS
# ============================================================

from tools.reminders import (
    create_reminder,
    get_reminders,
    cancel_reminder,
    start_reminder_service,
    complete_reminder,
)


# ============================================================
# MEMORY
# ============================================================

from memory.memory_store import (
    initialize_storage,
    add_memory,
    get_memories,
    get_memory,
    delete_memory,
    add_memory_media,
    get_memory_media,
    get_memory_media_by_id,
    delete_memory_media,
)


# ============================================================
# MEMORY ACTIVITY
# ============================================================

from memory.activity_engine import (
    create_activity,
    evaluate_answer,
)


# ============================================================
# MEMORY VISION
# ============================================================

from memory.vision import (
    analyze_media,
)


# ============================================================
# COGNITIVE TRACKING
# ============================================================

from cognitive.tracker import (
    get_performance_history,
    get_performance_summary,
)


# ============================================================
# APPLICATION
# ============================================================

app = Flask(__name__)
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
app.config["JSON_SORT_KEYS"] = False


# ============================================================
# CORS / FRONTEND CONNECTION
# ============================================================

@app.after_request
def add_api_headers(response):
    """
    Lightweight CORS and API headers.

    Allows the separate UI/frontend application to communicate
    with the Flask backend during development.
    """

    response.headers["Access-Control-Allow-Origin"] = "*"

    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization"
    )

    response.headers["Access-Control-Allow-Methods"] = (
        "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    )

    response.headers["Access-Control-Max-Age"] = "3600"

    response.headers["X-Content-Type-Options"] = "nosniff"

    return response


@app.before_request
def handle_options_request():
    """
    Allow browser preflight requests from the UI.
    """

    if request.method == "OPTIONS":
        return "", 204

    return None


# ============================================================
# UTILITY HELPERS
# ============================================================

def _json_body():
    """
    Safely return the incoming JSON body.
    """

    return (
        request.get_json(
            silent=True
        )
        or {}
    )


def _required_text(
    data,
    field_name,
):
    """
    Extract and validate a required text field.
    """

    value = data.get(
        field_name
    )

    if not isinstance(
        value,
        str,
    ):
        return None

    value = value.strip()

    if not value:
        return None

    return value


def _optional_session_id(data):
    """
    Safely extract an optional conversation session ID.
    """

    session_id = data.get(
        "session_id"
    )

    if session_id is None:
        return None, None

    if not isinstance(
        session_id,
        str,
    ):
        return (
            None,
            "session_id must be text.",
        )

    session_id = session_id.strip()

    if not session_id:
        return None, None

    if len(session_id) > 200:
        return (
            None,
            "session_id is too long.",
        )

    return (
        session_id,
        None,
    )


def _optional_language(data):
    """
    Safely extract and normalize a requested language.

    The language module remains the single source of truth for
    supported languages and aliases.

    IMPORTANT:
    If no language is supplied, None is returned. This allows
    the conversation engine to perform local automatic
    language detection.
    """

    language = data.get(
        "language"
    )

    if language is None:
        return None, None

    if not isinstance(
        language,
        str,
    ):
        return (
            None,
            "language must be text.",
        )

    language = language.strip()

    if not language:
        return None, None

    normalized = normalize_language(
        language
    )

    if not normalized:
        return (
            None,
            "Unsupported language.",
        )

    return (
        normalized,
        None,
    )


def _get_language_info(
    language_code,
    fallback=None,
):
    """
    Resolve canonical language metadata.

    The language.py module owns the actual language definitions.
    """

    if language_code:
        try:
            info = get_language(
                language_code
            )

            if isinstance(
                info,
                dict,
            ):
                return info

        except Exception:
            pass

    if isinstance(
        fallback,
        dict,
    ):
        return fallback

    return {
        "code": language_code or "en",
        "name": "English",
        "native_name": "English",
        "base_language": "en",
        "speech_locale": "en-IN",
        "is_hinglish": False,
    }


def _prepare_language_context(
    message,
    requested_language=None,
):
    """
    Prepare language information before entering the companion
    engine.

    Language detection must remain local.

    If the caller explicitly selected a language, that language
    is authoritative for the interaction.

    If no language was selected, language.py performs local
    detection.
    """

    context = prepare_for_companion(
        message,
        requested_language,
    )

    if not isinstance(
        context,
        dict,
    ):
        context = {}

    selected_code = requested_language

    detected_code = (
        context.get(
            "detected_language"
        )
        or context.get(
            "language"
        )
    )

    if selected_code:
        interaction_code = selected_code
        selection_source = "explicit_selection"

    else:
        interaction_code = (
            detected_code
            or "en"
        )
        selection_source = "local_detection"

    language_info = _get_language_info(
        interaction_code
    )

    detected_info = _get_language_info(
        detected_code or interaction_code
    )

    context["language"] = interaction_code

    context.setdefault(
        "detected_language",
        detected_code or interaction_code,
    )

    context.setdefault(
        "language_info",
        language_info,
    )

    context.setdefault(
        "detected_language_info",
        detected_info,
    )

    context.setdefault(
        "selection_source",
        selection_source,
    )

    context.setdefault(
        "base_language",
        language_info.get(
            "base_language",
            interaction_code,
        ),
    )

    context.setdefault(
        "is_hinglish",
        bool(
            language_info.get(
                "is_hinglish",
                interaction_code == "hinglish",
            )
        ),
    )

    return context


def _attach_language_metadata(
    result,
    language_context,
    api_path,
):
    """
    Add consistent multilingual metadata to a companion result.
    """

    if not isinstance(
        result,
        dict,
    ):
        result = {
            "success": True,
            "response": str(result),
        }

    response_text = (
        result.get("response")
        or result.get("message")
        or ""
    )

    result["success"] = result.get(
        "success",
        True,
    )

    result["response"] = (
        str(response_text).strip()
    )

    result["api"] = api_path

    result["pipeline"] = (
        "unified_companion"
    )

    if not isinstance(
        language_context,
        dict,
    ):
        language_context = {}

    interaction_language = (
        language_context.get(
            "language"
        )
        or "en"
    )

    detected_language = (
        language_context.get(
            "detected_language"
        )
        or interaction_language
    )

    language_info = language_context.get(
        "language_info"
    )

    if not isinstance(
        language_info,
        dict,
    ):
        language_info = _get_language_info(
            interaction_language
        )

    detected_info = (
        language_context.get(
            "detected_language_info"
        )
    )

    if not isinstance(
        detected_info,
        dict,
    ):
        detected_info = _get_language_info(
            detected_language
        )

    result["language"] = (
        interaction_language
    )

    result["detected_language"] = (
        detected_language
    )

    result["language_info"] = (
        language_info
    )

    result["detected_language_info"] = (
        detected_info
    )

    if "confidence" in language_context:
        result["language_confidence"] = (
            language_context.get(
                "confidence"
            )
        )

    result["language_selection"] = (
        language_context.get(
            "selection_source",
            "local_detection",
        )
    )

    result["base_language"] = (
        language_info.get(
            "base_language",
            interaction_language,
        )
    )

    result["is_hinglish"] = bool(
        language_info.get(
            "is_hinglish",
            interaction_language == "hinglish",
        )
    )

    result["language_context"] = (
        language_context
    )

    return result


def _safe_integer(
    value,
    default,
    minimum,
    maximum,
):
    """
    Convert a value into an integer while enforcing limits.
    """

    try:
        value = int(value)

    except (
        TypeError,
        ValueError,
    ):
        value = default

    return max(
        minimum,
        min(
            value,
            maximum,
        ),
    )


def _api_error(
    message,
    status_code=500,
    **extra,
):
    """
    Consistent JSON API error response.
    """

    payload = {
        "success": False,
        "error": message,
    }

    payload.update(
        extra
    )

    return jsonify(
        payload
    ), status_code


# ============================================================
# CAREGIVER INTELLIGENCE
# ============================================================

@app.route(
    "/api/caregiver/overview",
    methods=["GET"],
)
def caregiver_overview_api():

    try:
        return jsonify(
            get_caregiver_overview()
        )

    except Exception as error:

        print(
            "CAREGIVER OVERVIEW ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            500,
        )


@app.route(
    "/api/caregiver/today",
    methods=["GET"],
)
def caregiver_today_api():

    try:
        return jsonify(
            get_caregiver_today()
        )

    except Exception as error:

        print(
            "CAREGIVER TODAY ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            500,
        )


@app.route(
    "/api/caregiver/weekly",
    methods=["GET"],
)
def caregiver_weekly_api():

    try:
        return jsonify(
            get_caregiver_weekly()
        )

    except Exception as error:

        print(
            "CAREGIVER WEEKLY ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            500,
        )


@app.route(
    "/api/caregiver/activity",
    methods=["GET"],
)
def caregiver_activity_api():

    try:
        return jsonify(
            get_caregiver_activity()
        )

    except Exception as error:

        print(
            "CAREGIVER ACTIVITY ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            500,
        )


@app.route(
    "/api/caregiver/cognitive",
    methods=["GET"],
)
def caregiver_cognitive_api():

    try:
        return jsonify(
            get_caregiver_cognitive()
        )

    except Exception as error:

        print(
            "CAREGIVER COGNITIVE ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            500,
        )


@app.route(
    "/api/caregiver/memory",
    methods=["GET"],
)
def caregiver_memory_api():

    try:
        return jsonify(
            get_caregiver_memory()
        )

    except Exception as error:

        print(
            "CAREGIVER MEMORY ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            500,
        )


@app.route(
    "/api/caregiver/reminders",
    methods=["GET"],
)
def caregiver_reminders_api():

    try:
        return jsonify(
            get_caregiver_reminders()
        )

    except Exception as error:

        print(
            "CAREGIVER REMINDERS ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            500,
        )


@app.route(
    "/api/caregiver/conversation",
    methods=["GET"],
)
def caregiver_conversation_api():

    try:
        return jsonify(
            get_caregiver_conversation()
        )

    except Exception as error:

        print(
            "CAREGIVER CONVERSATION ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            500,
        )


@app.route(
    "/api/caregiver/companion",
    methods=["GET"],
)
def caregiver_companion_api():

    try:
        return jsonify(
            get_caregiver_companion()
        )

    except Exception as error:

        print(
            "CAREGIVER COMPANION ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            500,
        )


@app.route(
    "/api/caregiver/recommendations",
    methods=["GET"],
)
def caregiver_recommendations_api():

    try:
        return jsonify(
            get_caregiver_recommendations()
        )

    except Exception as error:

        print(
            "CAREGIVER RECOMMENDATIONS ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            500,
        )


@app.route(
    "/api/caregiver/report",
    methods=["GET"],
)
def caregiver_report_api():

    try:
        return jsonify(
            generate_caregiver_report()
        )

    except Exception as error:

        print(
            "CAREGIVER REPORT ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            500,
        )


@app.route(
    "/api/caregiver/status",
    methods=["GET"],
)
def caregiver_status_api():

    return jsonify({
        "success": True,
        "service": "caregiver_intelligence",
        "available": True,
        "analytics": True,
        "recommendations": True,
        "reports": True,
        "non_diagnostic": True,
        "gemini_required": False,
    })


# ============================================================
# LANGUAGE STATUS
# ============================================================

@app.route(
    "/api/language/status",
    methods=["GET"],
)
def language_status():

    try:

        return jsonify(
            get_language_status()
        )

    except Exception as exc:

        return _api_error(
            str(exc),
            500,
        )


# ============================================================
# LANGUAGE LIST
# ============================================================

@app.route(
    "/api/language/languages",
    methods=["GET"],
)
def language_list():

    try:

        languages = list_languages()

        return jsonify({
            "success": True,
            "languages": languages,
        })

    except Exception as exc:

        return _api_error(
            str(exc),
            500,
        )


# ============================================================
# LANGUAGE DETECTION
# ============================================================

@app.route(
    "/api/language/detect",
    methods=["POST"],
)
def language_detect():

    try:

        data = _json_body()

        text = data.get(
            "text",
            "",
        )

        if not isinstance(
            text,
            str,
        ):
            return _api_error(
                "text_must_be_text",
                400,
            )

        text = text.strip()

        if not text:
            return _api_error(
                "text_required",
                400,
            )

        if len(text) > 5000:
            return _api_error(
                "text_too_long",
                400,
            )

        # ----------------------------------------------------
        # IMPORTANT:
        # detect_language() must remain a LOCAL operation.
        # This endpoint must never call Gemini simply to
        # identify a language.
        # ----------------------------------------------------

        result = detect_language(
            text
        )

        if not isinstance(
            result,
            dict,
        ):
            result = {
                "success": True,
                "language": str(result),
            }

        detected_code = (
            result.get(
                "language"
            )
            or result.get(
                "detected_language"
            )
        )

        if detected_code:

            result.setdefault(
                "detected_language",
                detected_code,
            )

            result.setdefault(
                "language_info",
                _get_language_info(
                    detected_code
                ),
            )

        result.setdefault(
            "success",
            True,
        )

        result["local_detection"] = True

        return jsonify(
            result
        )

    except Exception as exc:

        print(
            "LANGUAGE DETECTION ERROR:"
        )
        print(exc)

        return _api_error(
            str(exc),
            500,
        )


# ============================================================
# LANGUAGE TRANSLATION
# ============================================================

@app.route(
    "/api/language/translate",
    methods=["POST"],
)
def language_translate():

    try:

        data = _json_body()

        text = data.get(
            "text",
            "",
        )

        target_language = (
            data.get(
                "target_language"
            )
            or data.get(
                "language"
            )
        )

        source_language = data.get(
            "source_language"
        )

        if not isinstance(
            text,
            str,
        ):
            return _api_error(
                "text_must_be_text",
                400,
            )

        text = text.strip()

        if not text:
            return _api_error(
                "text_required",
                400,
            )

        if len(text) > 5000:
            return _api_error(
                "text_too_long",
                400,
            )

        if not target_language:
            return _api_error(
                "target_language_required",
                400,
            )

        normalized_target = normalize_language(
            target_language
        )

        if not normalized_target:
            return _api_error(
                "unsupported_target_language",
                400,
            )

        normalized_source = None

        if source_language:

            normalized_source = normalize_language(
                source_language
            )

            if not normalized_source:
                return _api_error(
                    "unsupported_source_language",
                    400,
                )

        result = translate_text(
            text,
            normalized_target,
            source_language=normalized_source,
        )

        return jsonify(
            result
        )

    except Exception as exc:

        print(
            "LANGUAGE TRANSLATION ERROR:"
        )
        print(exc)

        return _api_error(
            str(exc),
            500,
        )


# ============================================================
# LANGUAGE PREPARE
# ============================================================

@app.route(
    "/api/language/prepare",
    methods=["POST"],
)
def language_prepare():

    try:

        data = _json_body()

        text = data.get(
            "text",
            "",
        )

        language = data.get(
            "language"
        )

        if not isinstance(
            text,
            str,
        ):
            return _api_error(
                "text_must_be_text",
                400,
            )

        text = text.strip()

        if not text:
            return _api_error(
                "text_required",
                400,
            )

        if len(text) > 5000:
            return _api_error(
                "text_too_long",
                400,
            )

        if language:

            if not isinstance(
                language,
                str,
            ):
                return _api_error(
                    "language must be text.",
                    400,
                )

            language = normalize_language(
                language
            )

            if not language:
                return _api_error(
                    "unsupported_language",
                    400,
                )

        result = prepare_for_companion(
            text,
            language,
        )

        if not isinstance(
            result,
            dict,
        ):
            result = {
                "success": True,
                "language": language or "en",
                "result": result,
            }

        result.setdefault(
            "success",
            True,
        )

        result["local_language_processing"] = True

        return jsonify(
            result
        )

    except Exception as exc:

        print(
            "LANGUAGE PREPARE ERROR:"
        )
        print(exc)

        return _api_error(
            str(exc),
            500,
        )


# ============================================================
# VOICE STATUS
# ============================================================

@app.route(
    "/api/voice/status",
    methods=["GET"],
)
def voice_status():

    try:

        return jsonify(
            get_voice_status()
        )

    except Exception as exc:

        return _api_error(
            str(exc),
            500,
            service="voice",
        )


# ============================================================
# VOICE CONFIG
# ============================================================

@app.route(
    "/api/voice/config",
    methods=["GET"],
)
def voice_config():

    try:

        language = request.args.get(
            "language"
        )

        if language:

            language = normalize_language(
                language
            )

            if not language:
                return _api_error(
                    "unsupported_language",
                    400,
                )

        return jsonify(
            get_voice_config(
                language
            )
        )

    except Exception as exc:

        return _api_error(
            str(exc),
            500,
            service="voice",
        )


# ============================================================
# VOICE INSTRUCTIONS
# ============================================================

@app.route(
    "/api/voice/instructions",
    methods=["GET"],
)
def voice_instructions():

    try:

        language = request.args.get(
            "language"
        )

        if language:

            language = normalize_language(
                language
            )

            if not language:
                return _api_error(
                    "unsupported_language",
                    400,
                )

        return jsonify(
            browser_voice_instruction(
                language
            )
        )

    except Exception as exc:

        return _api_error(
            str(exc),
            500,
            service="voice",
        )


# ============================================================
# VOICE TRANSCRIPT
# ============================================================

@app.route(
    "/api/voice/transcript",
    methods=["POST"],
)
def voice_transcript():

    try:

        data = _json_body()

        text = data.get(
            "text",
            "",
        )

        language = data.get(
            "language"
        )

        if not isinstance(
            text,
            str,
        ):
            return _api_error(
                "text_must_be_text",
                400,
            )

        text = text.strip()

        if not text:
            return _api_error(
                "text_required",
                400,
            )

        if len(text) > 5000:
            return _api_error(
                "text_too_long",
                400,
            )

        if language:

            if not isinstance(
                language,
                str,
            ):
                return _api_error(
                    "language must be text.",
                    400,
                )

            language = normalize_language(
                language
            )

            if not language:
                return _api_error(
                    "unsupported_language",
                    400,
                )

        result = process_voice_transcript(
            text,
            language,
        )

        if not isinstance(
            result,
            dict,
        ):
            result = {
                "success": True,
                "text": text,
                "language": language,
            }

        if not result.get(
            "success",
            False,
        ):
            return jsonify(
                result
            ), 400

        return jsonify(
            result
        )

    except Exception as exc:

        print(
            "VOICE TRANSCRIPT ERROR:"
        )
        print(exc)

        return _api_error(
            str(exc),
            500,
            service="voice",
        )


# ============================================================
# VOICE AUDIO VALIDATION
# ============================================================

@app.route(
    "/api/voice/audio/validate",
    methods=["POST"],
)
def voice_audio_validate():

    try:

        data = _json_body()

        audio = data.get(
            "audio"
        )

        content_type = data.get(
            "content_type"
        )

        result = validate_audio_payload(
            audio,
            content_type,
        )

        if not result.get(
            "valid",
            False,
        ):
            return jsonify(
                result
            ), 400

        return jsonify(
            result
        )

    except Exception as exc:

        print(
            "VOICE AUDIO VALIDATION ERROR:"
        )
        print(exc)

        return _api_error(
            str(exc),
            500,
            service="voice",
        )


# ============================================================
# API INFORMATION
# ============================================================

@app.route(
    "/api",
    methods=["GET"],
)
def api_information():

    try:
        languages = list_languages()
    except Exception:
        languages = []

    return jsonify({
        "success": True,
        "service": "DementiaCareAI",
        "version": "3.2",
        "api": "DementiaCareAI Backend API",

        "architecture": {
            "conversation": (
                "unified_companion_pipeline"
            ),
            "memory": True,
            "reminders": True,
            "cognitive": True,
            "daily_companion": True,
            "caregiver_intelligence": True,
            "persistent_history": True,
            "multilingual": True,
            "voice": True,
            "gemini_fallback": True,
            "local_language_detection": True,
        },

        "language": {
            "detection": (
                "/api/language/detect"
            ),
            "languages": (
                "/api/language/languages"
            ),
            "translation": (
                "/api/language/translate"
            ),
            "prepare": (
                "/api/language/prepare"
            ),
            "status": (
                "/api/language/status"
            ),
            "supported": languages,
        },

        "voice": {
            "status": (
                "/api/voice/status"
            ),
            "config": (
                "/api/voice/config"
            ),
            "instructions": (
                "/api/voice/instructions"
            ),
            "transcript": (
                "/api/voice/transcript"
            ),
            "audio_validation": (
                "/api/voice/audio/validate"
            ),
        },

        "endpoints": {
            "health": "/api/health",
            "status": "/api/status",
            "database": "/api/database/status",
            "chat": "/api/chat",

            "companion": {
                "status": "/api/companion/status",
                "message": "/api/companion/message",
                "next": "/api/companion/next",
                "state": "/api/companion/state",
                "mood": "/api/companion/mood",
                "recommendation": (
                    "/api/companion/recommendation"
                ),
                "daily_plan": (
                    "/api/companion/daily-plan"
                ),
                "next_activity": (
                    "/api/companion/next-activity"
                ),
                "upcoming": (
                    "/api/companion/upcoming"
                ),
                "complete": (
                    "/api/companion/complete"
                ),
            },

            "caregiver": {
                "overview": (
                    "/api/caregiver/overview"
                ),
                "today": (
                    "/api/caregiver/today"
                ),
                "weekly": (
                    "/api/caregiver/weekly"
                ),
                "activity": (
                    "/api/caregiver/activity"
                ),
                "cognitive": (
                    "/api/caregiver/cognitive"
                ),
                "memory": (
                    "/api/caregiver/memory"
                ),
                "reminders": (
                    "/api/caregiver/reminders"
                ),
                "conversation": (
                    "/api/caregiver/conversation"
                ),
                "companion": (
                    "/api/caregiver/companion"
                ),
                "recommendations": (
                    "/api/caregiver/recommendations"
                ),
                "report": (
                    "/api/caregiver/report"
                ),
                "status": (
                    "/api/caregiver/status"
                ),
            },
        },
    })


# ============================================================
# ROOT
# ============================================================

@app.route(
    "/",
    methods=["GET"],
)
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/style.css", methods=["GET"])
def frontend_style():
    return send_from_directory(FRONTEND_DIR, "style.css")


@app.route("/script.js", methods=["GET"])
def frontend_script():
    return send_from_directory(FRONTEND_DIR, "script.js")


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route(
    "/api/health",
    methods=["GET"],
)
def health_check():

    try:

        state = get_state()

        engine_status = (
            get_engine_status()
        )

        language_info = (
            get_language_status()
        )

        voice_info = (
            get_voice_status()
        )

        return jsonify({
            "success": True,
            "status": "healthy",
            "service": "DementiaCareAI",

            "database": "available",
            "companion": "available",
            "memory": "available",
            "state": "available",

            "language": {
                "available": True,
                "status": language_info,
            },

            "voice": {
                "available": True,
                "status": voice_info,
            },

            "gemini": (
                engine_status.get(
                    "gemini",
                    engine_status.get(
                        "gemini_available",
                        "fallback",
                    ),
                )
                if isinstance(
                    engine_status,
                    dict,
                )
                else "fallback"
            ),

            "companion_engine": engine_status,

            "current_mood": state.get(
                "current_mood",
                "unknown",
            ),
        })

    except Exception as error:

        print(
            "HEALTH CHECK ERROR:"
        )
        print(error)

        return jsonify({
            "success": False,
            "status": "degraded",
            "service": "DementiaCareAI",
            "error": str(error),
        }), 500


# ============================================================
# COMPLETE BACKEND STATUS
# ============================================================

@app.route(
    "/api/status",
    methods=["GET"],
)
def api_status():

    try:

        engine_status = (
            get_engine_status()
        )

        language_info = (
            get_language_status()
        )

        voice_info = (
            get_voice_status()
        )

        return jsonify({
            "success": True,
            "service": "DementiaCareAI",
            "status": "operational",

            "api": True,
            "database": True,
            "memory": True,
            "companion": True,
            "conversation": True,
            "persistent_history": True,
            "caregiver_intelligence": True,
            "reminders": True,
            "cognitive_tracking": True,

            "language": True,
            "voice": True,

            "multilingual": True,

            "local_language_detection": True,

            "gemini": True,

            "language_status": language_info,
            "voice_status": voice_info,

            "engine": engine_status,
        })

    except Exception as error:

        print(
            "API STATUS ERROR:"
        )
        print(error)

        return _api_error(
            "Unable to determine backend status.",
            500,
        )


# ============================================================
# DATABASE STATUS
# ============================================================

@app.route(
    "/api/database/status",
    methods=["GET"],
)
def database_status():

    try:

        memories = get_memories()

        reminders = get_reminders()

        return jsonify({
            "success": True,
            "database": "connected",
            "memories": len(
                memories
            ),
            "reminders": len(
                reminders
            ),
        })

    except Exception as error:

        print(
            "DATABASE STATUS ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            500,
        )


# ============================================================
# COMPANION STATUS
# ============================================================

@app.route(
    "/api/companion/status",
    methods=["GET"],
)
def companion_status():

    try:

        engine_status = (
            get_engine_status()
        )

        state = get_state()

        return jsonify({
            "success": True,
            "service": "companion",
            "available": True,

            "engine": engine_status,

            "state_available": True,

            "current_mood": state.get(
                "current_mood",
                "unknown",
            ),

            "unified_pipeline": True,
            "persistent_history": True,
            "memory_context": True,
            "patient_context": True,

            "multilingual": True,
            "local_language_detection": True,
            "voice_ready": True,

            "gemini_fallback": True,
        })

    except Exception as error:

        print(
            "COMPANION STATUS ERROR:"
        )
        print(error)

        return _api_error(
            "Unable to determine companion status.",
            500,
        )


# ============================================================
# UNIFIED AI CHAT
# ============================================================

@app.route(
    "/api/chat",
    methods=["POST"],
)
def chat():
    """
    Main general conversation endpoint.

    Uses the canonical conversation engine pipeline, shared with
    /api/companion/message.

    Language behavior:

    1. If the frontend supplies "language", that language is
       authoritative.
    2. If language is omitted, the language module performs
       local detection.
    3. Language detection never requires Gemini.
    4. The resolved language is passed into the companion
       engine so Gemini/local fallback can respond in that
       language.
    """

    data = _json_body()

    message = _required_text(
        data,
        "message",
    )

    if not message:
        return _api_error(
            "Message is required.",
            400,
        )

    if len(message) > 2000:
        return _api_error(
            "Message is too long.",
            400,
        )

    session_id, session_error = (
        _optional_session_id(
            data
        )
    )

    if session_error:
        return _api_error(
            session_error,
            400,
        )

    requested_language, language_error = (
        _optional_language(
            data
        )
    )

    if language_error:
        return _api_error(
            language_error,
            400,
        )

    try:

        # ----------------------------------------------------
        # Prepare language context locally.
        # ----------------------------------------------------

        language_context = (
            _prepare_language_context(
                message,
                requested_language,
            )
        )

        resolved_language = (
            language_context.get(
                "language"
            )
        )

        # ----------------------------------------------------
        # Canonical database-first conversation engine.
        # ----------------------------------------------------

        result = process_message(
            message,
            session_id=session_id,
            language=resolved_language,
            language_info=language_context.get(
                "language_info"
            ),
            patient_id=int(data.get("patient_id", 1) or 1),
        )

        result = _attach_language_metadata(
            result,
            language_context,
            "/api/chat",
        )

        return jsonify(
            result
        )

    except ValueError as error:

        return _api_error(
            str(error),
            400,
        )

    except Exception as error:

        print()
        print(
            "CHAT ERROR:"
        )
        print(error)
        print()

        return _api_error(
            "Unable to process the conversation.",
            500,
        )


# ============================================================
# UNIFIED COMPANION MESSAGE
# ============================================================

@app.route(
    "/api/companion/message",
    methods=["POST"],
)
def companion_message():
    """
    Unified companion conversation endpoint using the canonical
    database-first conversation engine.

    Language behavior is identical to /api/chat.
    """

    data = _json_body()

    message = _required_text(
        data,
        "message",
    )

    if not message:
        return _api_error(
            "Message is required.",
            400,
        )

    if len(message) > 2000:
        return _api_error(
            "Message is too long.",
            400,
        )

    session_id, session_error = (
        _optional_session_id(
            data
        )
    )

    if session_error:
        return _api_error(
            session_error,
            400,
        )

    requested_language, language_error = (
        _optional_language(
            data
        )
    )

    if language_error:
        return _api_error(
            language_error,
            400,
        )

    try:

        language_context = (
            _prepare_language_context(
                message,
                requested_language,
            )
        )

        resolved_language = (
            language_context.get(
                "language"
            )
        )

        result = process_message(
            message,
            session_id=session_id,
            language=resolved_language,
            language_info=language_context.get(
                "language_info"
            ),
            patient_id=int(data.get("patient_id", 1) or 1),
        )

        result = _attach_language_metadata(
            result,
            language_context,
            "/api/companion/message",
        )

        return jsonify(
            result
        )

    except ValueError as error:

        return _api_error(
            str(error),
            400,
        )

    except Exception as error:

        print()
        print(
            "COMPANION MESSAGE ERROR:"
        )
        print(error)
        print()

        return _api_error(
            "Unable to process the companion message.",
            500,
        )


# ============================================================
# COMPANION ORCHESTRATOR
# ============================================================

@app.route(
    "/api/companion/next",
    methods=["GET"],
)
def companion_next():

    try:

        result = (
            get_next_companion_action()
        )

        return jsonify(
            result
        )

    except Exception as error:

        print()
        print(
            "COMPANION ORCHESTRATOR ERROR:"
        )
        print(error)
        print()

        return _api_error(
            "Unable to determine the next companion action.",
            500,
        )


# ============================================================
# REMINDERS
# ============================================================

@app.route(
    "/api/reminders",
    methods=["POST"],
)
def create_reminder_api():

    data = _json_body()

    message = _required_text(
        data,
        "message",
    )

    reminder_time = (
        data.get(
            "reminder_time"
        )
        or data.get(
            "time"
        )
    )

    if not message:
        return _api_error(
            "Reminder message is required.",
            400,
        )

    if reminder_time is None:
        return _api_error(
            "Reminder time is required.",
            400,
        )

    try:

        reminder = create_reminder(
            message=message,
            reminder_time=reminder_time,
        )

        return jsonify({
            "success": True,
            "reminder": reminder,
        }), 201

    except Exception as error:

        print(
            "CREATE REMINDER ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            400,
        )


@app.route(
    "/api/reminders",
    methods=["GET"],
)
def list_reminders():

    try:

        reminders = get_reminders()

        return jsonify({
            "success": True,
            "reminders": reminders,
        })

    except Exception as error:

        return _api_error(
            str(error),
            500,
        )


@app.route(
    "/api/reminders/<int:reminder_id>",
    methods=["DELETE"],
)
def delete_reminder(
    reminder_id,
):

    try:

        reminder = cancel_reminder(
            reminder_id
        )

        if not reminder:
            return _api_error(
                "Reminder not found.",
                404,
            )

        return jsonify({
            "success": True,
            "reminder": reminder,
        })

    except Exception as error:

        return _api_error(
            str(error),
            400,
        )


@app.route(
    "/api/reminders/<int:reminder_id>/complete",
    methods=["POST"],
)
def complete_reminder_api(
    reminder_id,
):

    try:

        reminder = complete_reminder(
            reminder_id
        )

        if reminder is None:
            return _api_error(
                "Reminder not found.",
                404,
            )

        return jsonify({
            "success": True,
            "reminder": reminder,
        })

    except Exception as error:

        print(
            "REMINDER COMPLETION ERROR:"
        )
        print(error)

        return _api_error(
            "Unable to complete reminder.",
            500,
        )


# ============================================================
# MEMORY LIBRARY
# ============================================================

@app.route(
    "/api/memories",
    methods=["POST"],
)
def create_memory_api():

    data = _json_body()

    try:

        memory = add_memory(
            category=data.get(
                "category"
            ),
            name=data.get(
                "name"
            ),
            relationship=data.get(
                "relationship"
            ),
            description=data.get(
                "description"
            ),
            tags=data.get(
                "tags",
                [],
            ),
            event_date=data.get(
                "event_date"
            ),
        )

        return jsonify({
            "success": True,
            "memory": memory,
        }), 201

    except Exception as error:

        print(
            "CREATE MEMORY ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            400,
        )


@app.route(
    "/api/memories",
    methods=["GET"],
)
def list_memories():

    category = request.args.get(
        "category"
    )

    try:

        memories = get_memories(
            category=category
        )

        return jsonify({
            "success": True,
            "memories": memories,
        })

    except Exception as error:

        return _api_error(
            str(error),
            400,
        )


@app.route(
    "/api/memories/<memory_id>",
    methods=["GET"],
)
def get_memory_api(
    memory_id,
):

    try:

        memory = get_memory(
            memory_id
        )

    except Exception as error:

        return _api_error(
            str(error),
            500,
        )

    if not memory:
        return _api_error(
            "Memory not found.",
            404,
        )

    return jsonify({
        "success": True,
        "memory": memory,
    })


@app.route(
    "/api/memories/<memory_id>",
    methods=["DELETE"],
)
def delete_memory_api(
    memory_id,
):

    try:

        memory = delete_memory(
            memory_id
        )

    except Exception as error:

        return _api_error(
            str(error),
            400,
        )

    if not memory:
        return _api_error(
            "Memory not found.",
            404,
        )

    return jsonify({
        "success": True,
        "memory": memory,
    })


# ============================================================
# MEMORY MEDIA - LIST
# ============================================================

@app.route(
    "/api/memories/<memory_id>/media",
    methods=["GET"],
)
def list_memory_media_api(
    memory_id,
):

    memory = get_memory(
        memory_id
    )

    if not memory:
        return _api_error(
            "Memory not found.",
            404,
        )

    try:

        media = get_memory_media(
            memory_id
        )

        return jsonify({
            "success": True,
            "memory_id": memory_id,
            "media": media,
        })

    except Exception as error:

        return _api_error(
            str(error),
            400,
        )


# ============================================================
# MEMORY MEDIA - UPLOAD
# ============================================================

@app.route(
    "/api/memories/<memory_id>/media",
    methods=["POST"],
)
def upload_memory_media(
    memory_id,
):

    memory = get_memory(
        memory_id
    )

    if not memory:
        return _api_error(
            "Memory not found.",
            404,
        )

    if "file" not in request.files:
        return _api_error(
            (
                "No file was uploaded. "
                "Use form field 'file'."
            ),
            400,
        )

    uploaded_file = (
        request.files["file"]
    )

    if not uploaded_file.filename:
        return _api_error(
            "The uploaded file has no filename.",
            400,
        )

    media_type = request.form.get(
        "media_type"
    )

    caption = request.form.get(
        "caption"
    )

    if not media_type:

        content_type = (
            uploaded_file.content_type
            or ""
        ).lower()

        if content_type.startswith(
            "image/"
        ):
            media_type = "photo"

        elif content_type.startswith(
            "video/"
        ):
            media_type = "video"

    if media_type not in {
        "photo",
        "video",
    }:
        return _api_error(
            (
                "media_type must be "
                "'photo' or 'video'."
            ),
            400,
        )

    allowed_photo_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }

    allowed_video_extensions = {
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".webm",
    }

    if media_type == "photo":
        allowed_extensions = (
            allowed_photo_extensions
        )
    else:
        allowed_extensions = (
            allowed_video_extensions
        )

    filename = (
        uploaded_file.filename.lower()
    )

    extension = Path(
        filename
    ).suffix.lower()

    if extension not in allowed_extensions:
        return _api_error(
            "Unsupported file type.",
            400,
        )

    try:

        media = add_memory_media(
            memory_id=memory_id,
            file_storage=uploaded_file,
            media_type=media_type,
            caption=caption,
        )

        return jsonify({
            "success": True,
            "media": media,
        }), 201

    except Exception as error:

        print(
            "MEMORY MEDIA UPLOAD ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            400,
        )


# ============================================================
# MEMORY MEDIA - SERVE FILE
# ============================================================

@app.route(
    "/api/memories/<memory_id>/media/<media_id>/file",
    methods=["GET"],
)
def serve_memory_media(
    memory_id,
    media_id,
):

    media = get_memory_media_by_id(
        media_id
    )

    if not media:
        return _api_error(
            "Media not found.",
            404,
        )

    if str(
        media["memory_id"]
    ) != str(
        memory_id
    ):
        return _api_error(
            "Media does not belong to this memory.",
            403,
        )

    file_path = Path(
        media["file_path"]
    )

    if not file_path.exists():
        return _api_error(
            "Media file does not exist.",
            404,
        )

    return send_from_directory(
        file_path.parent,
        file_path.name,
    )


# ============================================================
# MEMORY MEDIA - GEMINI ANALYSIS
# ============================================================

@app.route(
    "/api/memories/<memory_id>/media/<media_id>/analyze",
    methods=["POST"],
)
def analyze_memory_media(
    memory_id,
    media_id,
):

    try:

        result = analyze_media(
            media_id=media_id,
            memory_id=memory_id,
        )

        return jsonify(
            result
        )

    except FileNotFoundError as error:

        return _api_error(
            str(error),
            404,
        )

    except ValueError as error:

        return _api_error(
            str(error),
            400,
        )

    except Exception as error:

        print(
            "MEDIA ANALYSIS ERROR:"
        )
        print(error)

        return _api_error(
            "Unable to analyze the media.",
            500,
        )


# ============================================================
# MEMORY MEDIA - DELETE
# ============================================================

@app.route(
    "/api/memories/<memory_id>/media/<media_id>",
    methods=["DELETE"],
)
def delete_media_api(
    memory_id,
    media_id,
):

    try:

        media = delete_memory_media(
            memory_id,
            media_id,
        )

        if not media:
            return _api_error(
                "Media not found.",
                404,
            )

        return jsonify({
            "success": True,
            "media": media,
        })

    except Exception as error:

        return _api_error(
            str(error),
            400,
        )


# ============================================================
# MEMORY RECALL ACTIVITY
# ============================================================

@app.route(
    "/api/memory-activity",
    methods=["GET"],
)
def memory_activity():

    memory_id = request.args.get(
        "memory_id"
    )

    category = request.args.get(
        "category"
    )

    try:

        activity = create_activity(
            memory_id=memory_id,
            category=category,
        )

        if not activity:
            return _api_error(
                "No suitable memory was found.",
                404,
            )

        return jsonify({
            "success": True,
            "activity": activity,
        })

    except Exception as error:

        print(
            "MEMORY ACTIVITY ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            400,
        )


# ============================================================
# CREATE MEMORY ACTIVITY
# ============================================================

@app.route(
    "/api/activity/create",
    methods=["GET"],
)
def api_create_activity():

    memory_id = request.args.get(
        "memory_id"
    )

    category = request.args.get(
        "category"
    )

    try:

        activity = create_activity(
            memory_id=memory_id,
            category=category,
        )

        if not activity:
            return _api_error(
                "No suitable memory is available.",
                404,
            )

        return jsonify({
            "success": True,
            "activity": activity,
        })

    except Exception as error:

        print(
            "CREATE ACTIVITY ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            400,
        )


# ============================================================
# EVALUATE MEMORY ANSWER
# ============================================================

@app.route(
    "/api/memory-activity/evaluate",
    methods=["POST"],
)
def evaluate_memory_activity():

    data = _json_body()

    activity = data.get(
        "activity"
    )

    answer = data.get(
        "answer",
        "",
    )

    if not activity:
        return _api_error(
            "Activity is required.",
            400,
        )

    if not isinstance(
        answer,
        str,
    ):
        return _api_error(
            "Answer must be text.",
            400,
        )

    answer = answer.strip()

    if not answer:
        return _api_error(
            "Answer is required.",
            400,
        )

    try:

        result = evaluate_answer(
            activity=activity,
            answer=answer,
        )

        return jsonify({
            "success": True,
            "result": result,
        })

    except Exception as error:

        print(
            "MEMORY ANSWER EVALUATION ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            400,
        )


# ============================================================
# ACTIVITY ANSWER - COMPATIBILITY ENDPOINT
# ============================================================

@app.route(
    "/api/activity/answer",
    methods=["POST"],
)
def api_submit_answer():

    data = _json_body()

    activity = data.get(
        "activity"
    )

    answer = data.get(
        "answer"
    )

    if not activity:
        return _api_error(
            "activity is required.",
            400,
        )

    if not isinstance(
        answer,
        str,
    ):
        return _api_error(
            "answer must be text.",
            400,
        )

    answer = answer.strip()

    if not answer:
        return _api_error(
            "answer is required.",
            400,
        )

    try:

        result = evaluate_answer(
            activity,
            answer,
        )

        return jsonify({
            "success": True,
            "result": result,
        })

    except Exception as error:

        print(
            "ACTIVITY ANSWER ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            400,
        )


# ============================================================
# COGNITIVE PERFORMANCE
# ============================================================

@app.route(
    "/api/cognitive/performance",
    methods=["GET"],
)
def cognitive_performance():

    try:

        summary = (
            get_performance_summary()
        )

        return jsonify({
            "success": True,
            "summary": summary,
        })

    except Exception as error:

        return _api_error(
            str(error),
            500,
        )


# ============================================================
# COGNITIVE HISTORY
# ============================================================

@app.route(
    "/api/cognitive/history",
    methods=["GET"],
)
def cognitive_history():

    limit = _safe_integer(
        request.args.get(
            "limit"
        ),
        default=50,
        minimum=1,
        maximum=500,
    )

    try:

        history = (
            get_performance_history(
                limit
            )
        )

        return jsonify({
            "success": True,
            "history": history,
        })

    except Exception as error:

        return _api_error(
            str(error),
            500,
        )


# ============================================================
# COMPANION STATE
# ============================================================

@app.route(
    "/api/companion/state",
    methods=["GET"],
)
def companion_state():

    try:

        return jsonify({
            "success": True,
            "state": get_state(),
        })

    except Exception as error:

        return _api_error(
            str(error),
            500,
        )


# ============================================================
# COMPANION MOOD
# ============================================================

@app.route(
    "/api/companion/mood",
    methods=["POST"],
)
def companion_mood():

    data = _json_body()

    mood = _required_text(
        data,
        "mood",
    )

    if not mood:
        return _api_error(
            "Mood is required.",
            400,
        )

    if len(mood) > 100:
        return _api_error(
            "Mood value is too long.",
            400,
        )

    try:

        set_mood(
            mood
        )

        return jsonify({
            "success": True,
            "mood": mood,
            "state": get_state(),
        })

    except Exception as error:

        return _api_error(
            str(error),
            400,
        )


# ============================================================
# COMPANION RECOMMENDATION
# ============================================================

@app.route(
    "/api/companion/recommendation",
    methods=["GET"],
)
def companion_recommendation():

    try:

        recommendation = (
            get_companion_recommendation()
        )

        return jsonify({
            "success": True,
            "recommendation": recommendation,
        })

    except Exception as error:

        return _api_error(
            str(error),
            500,
        )


# ============================================================
# DAILY PLAN
# ============================================================

@app.route(
    "/api/companion/daily-plan",
    methods=["GET"],
)
def daily_plan():

    try:

        plan = get_daily_plan()

        return jsonify({
            "success": True,
            "plan": plan,
        })

    except Exception as error:

        return _api_error(
            str(error),
            500,
        )


# ============================================================
# DAILY PLAN - NEXT ACTIVITY
# ============================================================

@app.route(
    "/api/companion/next-activity",
    methods=["POST"],
)
def companion_next_activity():

    data = _json_body()

    activity_id = data.get(
        "activity_id"
    )

    try:

        if activity_id:

            activity = start_activity(
                activity_id
            )

        else:

            activity = get_next_activity()

        if not activity:
            return _api_error(
                "No upcoming activity.",
                404,
            )

        set_current_activity(
            activity
        )

        next_activity = (
            get_next_activity()
        )

        set_next_activity(
            next_activity
        )

        return jsonify({
            "success": True,
            "activity": activity,
            "next_activity": next_activity,
            "state": get_state(),
        })

    except Exception as error:

        print(
            "NEXT ACTIVITY ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            400,
        )


# ============================================================
# UPCOMING ACTIVITIES
# ============================================================

@app.route(
    "/api/companion/upcoming",
    methods=["GET"],
)
def upcoming_activities():

    limit = _safe_integer(
        request.args.get(
            "limit"
        ),
        default=3,
        minimum=1,
        maximum=10,
    )

    try:

        activities = (
            get_next_activities(
                limit
            )
        )

        return jsonify({
            "success": True,
            "activities": activities,
        })

    except Exception as error:

        return _api_error(
            str(error),
            500,
        )


# ============================================================
# COMPLETE DAILY ACTIVITY
# ============================================================

@app.route(
    "/api/companion/complete",
    methods=["POST"],
)
def complete_companion_activity():

    data = _json_body()

    activity_id = data.get(
        "activity_id"
    )

    if not activity_id:
        return _api_error(
            "activity_id is required.",
            400,
        )

    try:

        result = complete_activity(
            activity_id
        )

        try:

            current_activity = (
                get_state().get(
                    "current_activity"
                )
            )

            if (
                current_activity
                and str(
                    current_activity.get(
                        "id"
                    )
                )
                == str(
                    activity_id
                )
            ):

                set_current_activity(
                    None
                )

        except Exception as state_error:

            print(
                "ACTIVITY STATE UPDATE WARNING:"
            )
            print(
                state_error
            )

        return jsonify({
            "success": True,
            "result": result,
            "state": get_state(),
        })

    except Exception as error:

        print(
            "COMPLETE ACTIVITY ERROR:"
        )
        print(error)

        return _api_error(
            str(error),
            400,
        )


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(413)
def request_too_large(error):

    return jsonify({
        "success": False,
        "error": (
            "Uploaded file is too large. "
            "Maximum size is 100 MB."
        ),
    }), 413


@app.errorhandler(400)
def bad_request(error):

    return jsonify({
        "success": False,
        "error": "Bad request.",
    }), 400


@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "success": False,
        "error": "API endpoint not found.",
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):

    return jsonify({
        "success": False,
        "error": "HTTP method not allowed.",
    }), 405


@app.errorhandler(500)
def internal_error(error):

    return jsonify({
        "success": False,
        "error": "Internal server error.",
    }), 500


# ============================================================
# DEVELOPMENT VOICE TEST
# ============================================================

@app.route(
    "/voice-test",
    methods=["GET"],
)
def voice_test():
    """
    Temporary browser voice test page.

    The selected language is sent to /api/chat.

    The backend returns the resolved language metadata and
    the browser uses the returned speech locale.

    This page is for backend testing only; the production UI
    should use the /api/voice/* endpoints.
    """

    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>DementiaCareAI Voice</title>

    <style>

        body {
            font-family: Arial, sans-serif;
            max-width: 760px;
            margin: 40px auto;
            padding: 20px;
        }

        textarea {
            width: 100%;
            height: 120px;
            font-size: 20px;
            padding: 12px;
            box-sizing: border-box;
            margin-top: 10px;
        }

        select {
            width: 100%;
            padding: 12px;
            font-size: 18px;
            margin-top: 10px;
        }

        button {
            margin-top: 15px;
            padding: 14px 25px;
            font-size: 18px;
            cursor: pointer;
        }

        button:disabled {
            cursor: not-allowed;
            opacity: 0.6;
        }

        #status {
            margin-top: 20px;
            font-weight: bold;
        }

        #languageInfo {
            margin-top: 10px;
            padding: 10px;
            background: #eeeeee;
            border-radius: 8px;
            font-size: 15px;
        }

        #response {
            margin-top: 15px;
            padding: 15px;
            background: #f3f3f3;
            border-radius: 8px;
            font-size: 18px;
            min-height: 40px;
        }

    </style>
</head>

<body>

<h1>🧠 DementiaCareAI</h1>

<label for="language">
    Language
</label>

<select id="language">

    <option value="">
        Auto Detect
    </option>

    <option value="en">
        English
    </option>

    <option value="hi">
        Hindi
    </option>

    <option value="hinglish">
        Hinglish
    </option>

    <option value="as">
        Assamese
    </option>

    <option value="bn">
        Bengali
    </option>

    <option value="mr">
        Marathi
    </option>

    <option value="ur">
        Urdu
    </option>

    <option value="pa">
        Punjabi
    </option>

    <option value="gu">
        Gujarati
    </option>

    <option value="or">
        Odia
    </option>

    <option value="ta">
        Tamil
    </option>

    <option value="te">
        Telugu
    </option>

    <option value="kn">
        Kannada
    </option>

    <option value="ml">
        Malayalam
    </option>

    <option value="ne">
        Nepali
    </option>

    <option value="mni">
        Manipuri / Meitei
    </option>

    <option value="brx">
        Bodo
    </option>

    <option value="kha">
        Khasi
    </option>

    <option value="grt">
        Garo
    </option>

    <option value="lus">
        Mizo
    </option>

    <option value="trp">
        Tripuri / Kokborok
    </option>

</select>

<textarea
    id="message"
    placeholder="Type your message here..."
></textarea>

<button
    id="talk"
    type="button"
>
    🔊 Talk to DementiaCareAI
</button>

<div id="status"></div>

<div id="languageInfo"></div>

<div id="response"></div>

<script>

const message =
    document.getElementById("message");

const language =
    document.getElementById("language");

const button =
    document.getElementById("talk");

const status =
    document.getElementById("status");

const languageInfo =
    document.getElementById("languageInfo");

const responseBox =
    document.getElementById("response");


function getSpeechLocale(data) {

    if (
        data
        && data.language_info
        && data.language_info.speech_locale
    ) {

        return data.language_info.speech_locale;
    }

    const languageCode =
        data.language
        || data.detected_language
        || "";

    const locales = {

        "en": "en-IN",

        "hi": "hi-IN",

        "hinglish": "hi-IN",

        "as": "as-IN",

        "bn": "bn-IN",

        "mr": "mr-IN",

        "ur": "ur-IN",

        "pa": "pa-IN",

        "gu": "gu-IN",

        "or": "or-IN",

        "ta": "ta-IN",

        "te": "te-IN",

        "kn": "kn-IN",

        "ml": "ml-IN",

        "ne": "ne-IN",

        "mni": "mni-IN",

        "brx": "brx-IN",

        "kha": "kha-IN",

        "grt": "grt-IN",

        "lus": "lus-IN",

        "trp": "trp-IN"

    };

    return (
        locales[languageCode]
        || "en-IN"
    );
}


button.addEventListener(
    "click",
    async function () {

        const text =
            message.value.trim();

        const selectedLanguage =
            language.value;

        if (!text) {

            status.textContent =
                "Please type something first.";

            message.focus();

            return;
        }

        button.disabled = true;

        status.textContent =
            "DementiaCareAI is thinking...";

        languageInfo.textContent = "";

        responseBox.textContent = "";

        try {

            const body = {
                message: text,

                session_id:
                    "voice-demo"
            };

            /*
             * Only send language when the user explicitly
             * selected one.
             *
             * Empty language means automatic local detection.
             */

            if (selectedLanguage) {

                body.language =
                    selectedLanguage;
            }

            const result =
                await fetch(
                    "/api/chat",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify(
                            body
                        )
                    }
                );

            const data =
                await result.json();

            if (
                !result.ok
                || !data.success
            ) {

                throw new Error(
                    data.error
                    || data.message
                    || "Chat failed"
                );
            }

            const answer =
                data.response
                || data.message
                || "";

            responseBox.textContent =
                answer;

            const selected =
                data.language
                || "en";

            const detected =
                data.detected_language
                || selected;

            const confidence =
                data.language_confidence;

            languageInfo.textContent =
                "Response language: "
                + selected
                + " | Detected: "
                + detected
                + (
                    confidence !== undefined
                    ? " | Confidence: "
                        + confidence
                    : ""
                );

            status.textContent =
                "DementiaCareAI is speaking...";

            if (
                "speechSynthesis"
                in window
            ) {

                window.speechSynthesis.cancel();

                const speech =
                    new SpeechSynthesisUtterance(
                        answer
                    );

                speech.lang =
                    getSpeechLocale(
                        data
                    );

                speech.rate = 0.88;

                speech.pitch = 1.0;

                speech.volume = 1.0;

                speech.onend =
                    function () {

                        status.textContent =
                            "DementiaCareAI finished speaking.";

                    };

                speech.onerror =
                    function (event) {

                        status.textContent =
                            "Speech error: "
                            + event.error;

                    };

                window.speechSynthesis.speak(
                    speech
                );

            } else {

                status.textContent =
                    "Speech synthesis is not supported by this browser.";

            }

        } catch (error) {

            console.error(error);

            status.textContent =
                "Error: "
                + error.message;

        } finally {

            button.disabled = false;

        }

    }
);

</script>

</body>
</html>
"""


# ============================================================
# STARTUP
# ============================================================

def initialize_application():
    """
    Initialize all backend services.

    Database and local storage are required.

    Reminder service is started independently so that a
    reminder initialization problem does not prevent the
    entire API from starting.
    """

    print()
    print(
        "=============================================="
    )
    print(
        "        DementiaCareAI Backend"
    )
    print(
        "=============================================="
    )

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    try:

        initialize_database()

        print(
            "[OK] Database initialized"
        )

    except Exception as error:

        print(
            "[ERROR] Database initialization failed:"
        )

        print(error)

        raise

    # --------------------------------------------------------
    # MEMORY STORAGE
    # --------------------------------------------------------

    try:

        initialize_storage()

        print(
            "[OK] Memory storage initialized"
        )

    except Exception as error:

        print(
            "[ERROR] Memory storage initialization failed:"
        )

        print(error)

        raise

    # --------------------------------------------------------
    # REMINDER SERVICE
    # --------------------------------------------------------

    try:

        start_reminder_service()

        print(
            "[OK] Reminder service started"
        )

    except Exception as error:

        print(
            "[WARNING] Reminder service could not start:"
        )

        print(error)

    # --------------------------------------------------------
    # SERVICES
    # --------------------------------------------------------

    print(
        "[OK] Companion system loaded"
    )

    print(
        "[OK] Memory system loaded"
    )

    print(
        "[OK] Vision system loaded"
    )

    print(
        "[OK] Cognitive tracking loaded"
    )

    print(
        "[OK] Caregiver intelligence loaded"
    )

    # --------------------------------------------------------
    # LANGUAGE / VOICE
    # --------------------------------------------------------

    try:

        language_status_info = (
            get_language_status()
        )

        print(
            "[OK] Language system loaded"
        )

        print(
            "[OK] Supported languages: "
            + str(
                language_status_info.get(
                    "supported_languages",
                    language_status_info.get(
                        "count",
                        "available",
                    ),
                )
            )
        )

    except Exception as error:

        print(
            "[WARNING] Language status unavailable:"
        )

        print(error)

    try:

        get_voice_status()

        print(
            "[OK] Voice system loaded"
        )

    except Exception as error:

        print(
            "[WARNING] Voice system status unavailable:"
        )

        print(error)

    print()

    print(
        "DementiaCareAI backend is ready."
    )

    print(
        "=============================================="
    )

    print()


# ============================================================
# INITIALIZE APPLICATION
# ============================================================

initialize_application()


# ============================================================
# DEVELOPMENT SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "Starting DementiaCareAI..."
    )

    print(
        "Server: http://127.0.0.1:5000"
    )

    print(
        "API: http://127.0.0.1:5000/api"
    )

    print(
        "Health: http://127.0.0.1:5000/api/health"
    )

    print(
        "Status: http://127.0.0.1:5000/api/status"
    )

    print(
        "Language: "
        "http://127.0.0.1:5000/api/language/status"
    )

    print(
        "Voice: "
        "http://127.0.0.1:5000/api/voice/status"
    )

    print(
        "Companion: "
        "http://127.0.0.1:5000/api/companion/status"
    )

    print()

    print(
        "The API uses the unified Companion Engine."
    )

    print(
        "Language detection is performed locally."
    )

    print(
        "Explicit language selection is respected."
    )

    print(
        "Gemini is only called when an AI operation "
        "actually requires it."
    )

    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
