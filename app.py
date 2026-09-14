from pathlib import Path

from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory,
    Response,
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
    synthesize_speech,
)


def _sanitize_patient_response_text(response: str) -> str:
    """Final API boundary protection for the known malformed response."""
    if not isinstance(response, str):
        return ""
    cleaned = " ".join(response.strip().split())
    lowered = cleaned.casefold()
    patterns = (
        "birthday celebration is your family",
        "birthday celebration is your relative",
        "birthday celebration is your mother",
        "birthday celebration is your father",
        "birthday celebration is your sister",
        "birthday celebration is your brother",
    )
    if any(pattern in lowered for pattern in patterns):
        return "I don't have enough information to answer that yet."
    return cleaned


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
    process_message,
    get_engine_status,
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

    If no language is supplied, None is returned so that the
    language module can perform local automatic detection.
    """

    language_value = data.get(
        "language"
    )

    if language_value is None:
        return None, None

    if not isinstance(
        language_value,
        str,
    ):
        return (
            None,
            "language must be text.",
        )

    language_value = language_value.strip()

    if not language_value:
        return None, None

    normalized = normalize_language(
        language_value
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

    This helper accepts either a language code string or a language
    metadata dictionary. This is important because local detection
    may return a full dictionary.
    """

    if isinstance(
        language_code,
        dict,
    ):
        language_code = (
            language_code.get("code")
            or language_code.get("language")
            or language_code.get("detected_language")
        )

    if isinstance(
        language_code,
        str,
    ):
        language_code = language_code.strip()

        if language_code:
            try:
                normalized_code = normalize_language(
                    language_code
                )

                if normalized_code:
                    language_code = normalized_code

            except Exception:
                pass

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

    IMPORTANT:
    - Language detection is always local.
    - Explicit language selection is authoritative.
    - detected_language may be either a language code string
      OR a full detection dictionary returned by language.py.
    - All language values passed to the companion engine are
      canonical language codes.
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

    # ------------------------------------------------------------
    # Explicit language selection is authoritative.
    # ------------------------------------------------------------

    if requested_language:
        interaction_code = normalize_language(
            requested_language
        )

        if not interaction_code:
            interaction_code = "en"

        selection_source = "explicit_selection"

    else:
        # --------------------------------------------------------
        # Local automatic detection.
        #
        # prepare_for_companion() may return:
        #   detected_language = "hi"
        # OR
        #   detected_language = {"code": "hi", ...}
        #
        # Never pass the dictionary itself to get_language().
        # --------------------------------------------------------

        raw_detected = context.get(
            "detected_language"
        )

        detected_code = None

        if isinstance(
            raw_detected,
            dict,
        ):
            detected_code = (
                raw_detected.get("code")
                or raw_detected.get("language")
                or raw_detected.get("detected_language")
            )

        elif isinstance(
            raw_detected,
            str,
        ):
            detected_code = raw_detected

        # Some implementations may store the detected code in
        # context["language"] instead.
        if not detected_code:
            raw_language = context.get(
                "language"
            )

            if isinstance(
                raw_language,
                dict,
            ):
                detected_code = (
                    raw_language.get("code")
                    or raw_language.get("language")
                    or raw_language.get("detected_language")
                )

            elif isinstance(
                raw_language,
                str,
            ):
                detected_code = raw_language

        if detected_code:
            detected_code = normalize_language(
                detected_code
            )

        interaction_code = (
            detected_code
            or "en"
        )

        selection_source = "local_detection"

    # ------------------------------------------------------------
    # Canonical metadata for the interaction language.
    # ------------------------------------------------------------

    language_info = _get_language_info(
        interaction_code
    )

    # ------------------------------------------------------------
    # Canonical metadata for the detected language.
    # ------------------------------------------------------------

    raw_detected = context.get(
        "detected_language"
    )

    detected_code = None
    detected_info = None

    if isinstance(
        raw_detected,
        dict,
    ):
        detected_code = (
            raw_detected.get("code")
            or raw_detected.get("language")
            or raw_detected.get("detected_language")
        )

        if detected_code:
            detected_code = normalize_language(
                detected_code
            )

        # Preserve the detailed local detection result when
        # language.py already provided it.
        if detected_code:
            detected_info = dict(
                raw_detected
            )

    elif isinstance(
        raw_detected,
        str,
    ):
        detected_code = normalize_language(
            raw_detected
        )

    if not detected_code:
        detected_code = interaction_code

    if not isinstance(
        detected_info,
        dict,
    ):
        detected_info = _get_language_info(
            detected_code
        )

    # ------------------------------------------------------------
    # Store one consistent shape for every caller.
    # ------------------------------------------------------------

    context["language"] = interaction_code
    context["detected_language"] = detected_code
    context["language_info"] = language_info
    context["detected_language_info"] = detected_info
    context["selection_source"] = selection_source

    context["base_language"] = language_info.get(
        "base_language",
        interaction_code,
    )

    context["is_hinglish"] = bool(
        language_info.get(
            "is_hinglish",
            interaction_code == "hinglish",
        )
    )

    if isinstance(
        raw_detected,
        dict,
    ):
        confidence = raw_detected.get(
            "confidence"
        )

        if confidence is not None:
            context["confidence"] = confidence

    # This flag makes it explicit that language detection happened
    # locally and never through Gemini.
    context["local_detection"] = True

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

    result["response"] = _sanitize_patient_response_text(
        str(response_text)
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


def _gemini_available_from_status(engine_status):
    """
    Return a reliable boolean Gemini availability value.

    Do not assume Gemini is configured merely because the companion
    engine exists. Prefer explicit boolean status fields.
    """

    if not isinstance(
        engine_status,
        dict,
    ):
        return False

    value = engine_status.get(
        "gemini_available"
    )

    if isinstance(
        value,
        bool,
    ):
        return value

    value = engine_status.get(
        "gemini"
    )

    if isinstance(
        value,
        bool,
    ):
        return value

    if isinstance(
        value,
        str,
    ):
        return value.strip().lower() in {
            "true",
            "available",
            "configured",
            "ready",
            "connected",
            "active",
            "enabled",
        }

    return False


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
    """
    Detect the language of text using language.py only.

    This endpoint is intentionally local-only. Gemini is never
    called for language detection.
    """

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

        # --------------------------------------------------------
        # LOCAL DETECTION ONLY.
        # --------------------------------------------------------

        result = detect_language(
            text
        )

        if not isinstance(
            result,
            dict,
        ):
            result = {
                "success": True,
                "code": str(result),
            }

        detected_code = (
            result.get("code")
            or result.get("language")
            or result.get("detected_language")
        )

        # Handle the unlikely case where the detector returns
        # another nested language dictionary.
        if isinstance(
            detected_code,
            dict,
        ):
            detected_code = (
                detected_code.get("code")
                or detected_code.get("language")
                or detected_code.get("detected_language")
            )

        if detected_code:
            detected_code = normalize_language(
                detected_code
            )

        if not detected_code:
            detected_code = "en"

        language_info = _get_language_info(
            detected_code
        )

        result["success"] = True
        result["code"] = detected_code
        result["language"] = detected_code
        result["detected_language"] = detected_code
        result["language_info"] = language_info
        result["base_language"] = language_info.get(
            "base_language",
            detected_code,
        )
        result["is_hinglish"] = bool(
            language_info.get(
                "is_hinglish",
                detected_code == "hinglish",
            )
        )
        result["local_detection"] = True

        # Keep the detector's method/confidence when supplied.
        result["method"] = result.get(
            "method",
            "local",
        )

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
            local_detection=True,
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
# SERVER-SIDE TTS
# ============================================================

@app.route(
    "/api/voice/speak",
    methods=["POST"],
)
def voice_speak():
    """Return MP3 speech for the requested language.

    This is the primary TTS endpoint for the patient UI. The frontend first
    tries this endpoint so Punjabi and other supported languages do not depend
    on a browser-installed voice.
    """
    try:
        data = _json_body()
        text = data.get("text", "")
        language = data.get("language") or "en"

        if not isinstance(text, str):
            return _api_error("text_must_be_text", 400)
        text = text.strip()
        if not text:
            return _api_error("text_required", 400)

        if not isinstance(language, str):
            return _api_error("language_must_be_text", 400)

        language = normalize_language(language)
        if not language:
            return _api_error("unsupported_language", 400)

        result = synthesize_speech(
            text=text,
            language=language,
        )

        if not result.get("success"):
            status = 503 if result.get("error") in {
                "server_tts_dependency_missing",
                "server_tts_language_not_supported",
                "server_tts_failed",
            } else 400
            return jsonify(result), status

        return Response(
            result["audio"],
            mimetype="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=dementiacareai-response.mp3",
                "Cache-Control": "no-store",
                "X-DementiaCareAI-Language": result["language"],
                "X-DementiaCareAI-Voice-Provider": result["provider"],
            },
        )

    except Exception as exc:
        print("VOICE SPEAK ERROR:")
        print(exc)
        return _api_error(str(exc), 500, service="voice")


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
            "speak": (
                "/api/voice/speak"
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

    return jsonify({
        "name": "DementiaCareAI",
        "status": "running",
        "version": "3.2",
        "service": "DementiaCareAI Backend",
        "api": "/api",
        "health": "/api/health",

        "features": [
            "AI conversation",
            "multilingual conversation",
            "automatic local language detection",
            "Indian language support",
            "Northeast Indian language support",
            "Hinglish support",
            "unified companion conversation",
            "persistent memory",
            "conversation history",
            "smart reminders",
            "memory recall activities",
            "photo memory",
            "video memory",
            "Gemini visual memory analysis",
            "AI memory questions",
            "AI memory answer evaluation",
            "cognitive tracking",
            "daily companion",
            "daily routine",
            "companion orchestration",
            "caregiver intelligence",
            "caregiver recommendations",
            "caregiver reports",
            "voice interaction",
            "browser speech support",
        ],
    })


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

            "gemini": _gemini_available_from_status(
                engine_status
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

            "gemini": _gemini_available_from_status(
                engine_status
            ),

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

    Uses the same Companion Engine pipeline as
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
        # Unified companion engine.
        #
        # IMPORTANT:
        # No TypeError retry is used here.
        #
        # The updated companion.engine.process_message()
        # accepts language and language_info explicitly.
        # ----------------------------------------------------

        result = process_message(
            message,
            session_id=session_id,
            language=resolved_language,
            language_info=language_context.get(
                "language_info"
            ),
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
    Unified companion conversation endpoint.

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
# DEVELOPMENT VOICE TEST / STT + TTS DEMO
# ============================================================

@app.route("/voice-test", methods=["GET"])
def voice_test():
    """Patient-friendly companion UI with persistent text and voice input."""
    return r'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DementiaCareAI - Companion</title>
<style>
:root{font-family:Arial,sans-serif;color:#17202a;background:#f7f8fa}
*{box-sizing:border-box}
html,body{margin:0;min-height:100%;background:#f7f8fa}
body{padding:0 0 128px}
.app{max-width:920px;margin:0 auto;padding:18px 18px 30px}
.header{background:#fff;border-radius:16px;padding:20px;margin-bottom:14px;box-shadow:0 2px 12px rgba(0,0,0,.07)}
.header h1{margin:0 0 8px;font-size:30px}
.header p{margin:0;color:#5d6670;line-height:1.5}
.controls{background:#fff;border-radius:16px;padding:16px;margin-bottom:14px;box-shadow:0 2px 12px rgba(0,0,0,.07)}
label{font-weight:700;display:block;margin-bottom:8px}
select{width:100%;font-size:17px;padding:12px;border:1px solid #cfd5db;border-radius:10px;background:#fff}
.status{margin-top:12px;padding:11px 13px;border-radius:10px;background:#eef5ee;font-weight:700}
.language-info{margin-top:8px;color:#59636e;font-size:14px}
.chat{min-height:420px;padding:8px 0 18px}
.empty{background:#fff;border-radius:16px;padding:28px 22px;color:#69727c;text-align:center;box-shadow:0 2px 12px rgba(0,0,0,.05)}
.message{max-width:78%;margin:12px 0;padding:14px 16px;border-radius:17px;line-height:1.55;white-space:pre-wrap;word-break:break-word;box-shadow:0 1px 5px rgba(0,0,0,.06)}
.message.patient{margin-left:auto;background:#e8f0fe;border-bottom-right-radius:5px}
.message.ai{margin-right:auto;background:#fff;border-bottom-left-radius:5px}
.message-label{font-size:12px;font-weight:700;color:#66717d;margin-bottom:5px}
.composer-shell{position:fixed;left:0;right:0;bottom:0;background:rgba(247,248,250,.97);border-top:1px solid #dfe3e7;padding:10px 14px 14px;z-index:1000;backdrop-filter:blur(8px)}
.composer{max-width:920px;margin:0 auto;background:#fff;border:1px solid #cfd5db;border-radius:18px;padding:9px;box-shadow:0 5px 24px rgba(0,0,0,.12)}
.composer-row{display:flex;align-items:flex-end;gap:8px}
#message{flex:1;min-height:48px;max-height:150px;resize:none;border:0;outline:0;font:inherit;font-size:17px;line-height:1.4;padding:10px 9px;background:transparent}
.icon-button,.send-button{height:46px;border:0;border-radius:13px;cursor:pointer;font-size:20px;font-weight:700;flex:0 0 auto}
.icon-button{width:50px;background:#edf1f5}
.icon-button.recording{background:#fbe4e4}
.send-button{padding:0 18px;background:#17202a;color:#fff;font-size:16px}
button:disabled{opacity:.5;cursor:not-allowed}
.composer-hint{font-size:12px;color:#6d7680;padding:5px 8px 0}
#interim{font-size:13px;color:#65707b;margin:8px 4px 0;min-height:18px}
@media(max-width:600px){
  .app{padding:12px 10px 25px}
  .header h1{font-size:25px}
  .message{max-width:90%}
  .send-button{padding:0 13px}
  .composer-hint{display:none}
}
</style>
</head>
<body>
<div class="app">
  <section class="header">
    <h1>🧠 DementiaCareAI</h1>
    <p>Talk naturally with the companion. The patient can <strong>type</strong> or use the <strong>microphone</strong> at any time. Both inputs use the same companion conversation pipeline.</p>
  </section>

  <section class="controls">
    <label for="language">Language</label>
    <select id="language">
      <option value="">Auto Detect</option>
      <option value="en">English</option>
      <option value="hi">Hindi</option>
      <option value="hinglish">Hinglish</option>
      <option value="as">Assamese</option>
      <option value="bn">Bengali</option>
      <option value="mr">Marathi</option>
      <option value="ur">Urdu</option>
      <option value="pa">Punjabi</option>
      <option value="gu">Gujarati</option>
      <option value="or">Odia</option>
      <option value="ta">Tamil</option>
      <option value="te">Telugu</option>
      <option value="kn">Kannada</option>
      <option value="ml">Malayalam</option>
      <option value="ne">Nepali</option>
      <option value="mni">Manipuri / Meitei</option>
      <option value="brx">Bodo</option>
      <option value="kha">Khasi</option>
      <option value="grt">Garo</option>
      <option value="lus">Mizo</option>
      <option value="trp">Tripuri / Kokborok</option>
    </select>
    <div id="status" class="status">Ready.</div>
    <div id="languageInfo" class="language-info"></div>
  </section>

  <main id="chat" class="chat">
    <div id="empty" class="empty">Your conversation will appear here. Type a message or press 🎤 below.</div>
  </main>
</div>

<div class="composer-shell">
  <div class="composer">
    <div class="composer-row">
      <textarea id="message" rows="1" placeholder="Message DementiaCareAI..." aria-label="Message DementiaCareAI"></textarea>
      <button id="micButton" class="icon-button" type="button" title="Voice input" aria-label="Start voice input">🎤</button>
      <button id="stopButton" class="icon-button" type="button" title="Stop listening" aria-label="Stop listening" disabled>⏹</button>
      <button id="sendButton" class="send-button" type="button">Send</button>
    </div>
    <div id="interim"></div>
    <div class="composer-hint">Enter sends the message. Shift+Enter makes a new line. The microphone fills the message box, then you can review and send it.</div>
  </div>
</div>

<script>
const languageSelect = document.getElementById("language");
const messageBox = document.getElementById("message");
const micButton = document.getElementById("micButton");
const stopButton = document.getElementById("stopButton");
const sendButton = document.getElementById("sendButton");
const statusBox = document.getElementById("status");
const languageInfoBox = document.getElementById("languageInfo");
const chat = document.getElementById("chat");
const empty = document.getElementById("empty");
const interimBox = document.getElementById("interim");

const VOICE_LOCALES = {
  en:"en-IN", hi:"hi-IN", hinglish:"hi-IN", as:"as-IN", bn:"bn-IN", mr:"mr-IN",
  ur:"ur-IN", pa:"pa-IN", gu:"gu-IN", or:"or-IN", ta:"ta-IN", te:"te-IN",
  kn:"kn-IN", ml:"ml-IN", ne:"ne-NP", mni:"mni-IN", brx:"brx-IN", kha:"kha-IN",
  grt:"grt-IN", lus:"lus-IN", trp:"trp-IN"
};

let recognition = null;
let listening = false;
let finalTranscript = "";

function setStatus(text){ statusBox.textContent = text; }
function localeForLanguage(code){ return VOICE_LOCALES[code] || "en-IN"; }
function recognitionConstructor(){ return window.SpeechRecognition || window.webkitSpeechRecognition || null; }

function addMessage(role, text){
  if(empty) empty.remove();
  const wrapper = document.createElement("div");
  wrapper.className = "message " + role;
  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = role === "patient" ? "You" : "DementiaCareAI";
  const content = document.createElement("div");
  content.textContent = text;
  wrapper.appendChild(label);
  wrapper.appendChild(content);
  chat.appendChild(wrapper);
  wrapper.scrollIntoView({behavior:"smooth", block:"end"});
}

function availableVoices(){
  return "speechSynthesis" in window ? (window.speechSynthesis.getVoices() || []) : [];
}

function findExactVoice(locale){
  const wanted = String(locale || "").toLowerCase();
  return availableVoices().find(v => v.lang && v.lang.toLowerCase() === wanted) || null;
}

let currentAudio = null;

async function speakResponse(text, languageCode, locale){
  const code = String(languageCode || "en").trim().toLowerCase();
  const speechLocale = String(locale || localeForLanguage(code)).trim();

  if(currentAudio){
    try{ currentAudio.pause(); currentAudio.currentTime = 0; }catch(e){}
    currentAudio = null;
  }

  if("speechSynthesis" in window){
    window.speechSynthesis.cancel();
  }

  // Primary TTS: server-side gTTS. This does not depend on an installed
  // Windows/browser voice and uses the exact requested language code.
  try{
    setStatus("DementiaCareAI is preparing the voice response...");

    const ttsResponse = await fetch("/api/voice/speak", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({text:text, language:code})
    });

    if(ttsResponse.ok){
      const blob = await ttsResponse.blob();
      if(blob && blob.size > 0){
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        currentAudio = audio;
        audio.onplay = () => setStatus("DementiaCareAI is speaking in " + speechLocale + ".");
        audio.onended = () => {
          URL.revokeObjectURL(url);
          if(currentAudio === audio) currentAudio = null;
          setStatus("DementiaCareAI finished speaking.");
        };
        audio.onerror = () => {
          URL.revokeObjectURL(url);
          if(currentAudio === audio) currentAudio = null;
          fallbackToBrowserSpeech(text, speechLocale);
        };
        await audio.play();
        return;
      }
    }

    let detail = "";
    try{
      const errorData = await ttsResponse.json();
      detail = errorData.error || "";
    }catch(e){}

    console.warn("Server TTS unavailable", ttsResponse.status, detail);
  }catch(error){
    console.warn("Server TTS request failed", error);
  }

  // Fallback: browser speech only when an exact locale voice exists.
  fallbackToBrowserSpeech(text, speechLocale);
}

function fallbackToBrowserSpeech(text, locale){
  if(!("speechSynthesis" in window)){
    setStatus("Text response is ready, but this browser does not support speech output.");
    return;
  }

  const voice = findExactVoice(locale);
  if(!voice){
    setStatus("Text response is ready. Server voice was unavailable and no exact installed voice was found for " + locale + ". No unrelated-language voice will be used.");
    return;
  }

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = locale;
  utterance.voice = voice;
  utterance.rate = 0.88;
  utterance.pitch = 1;
  utterance.volume = 1;
  utterance.onstart = () => setStatus("DementiaCareAI is speaking using " + voice.name + " (" + voice.lang + ").");
  utterance.onend = () => setStatus("DementiaCareAI finished speaking.");
  utterance.onerror = e => setStatus("Speech output error: " + (e.error || "unknown"));
  window.speechSynthesis.speak(utterance);
}

async function sendToCompanion(text){
  const selectedLanguage = languageSelect.value;
  const body = {message:text, session_id:"voice-demo"};
  if(selectedLanguage) body.language = selectedLanguage;

  const response = await fetch("/api/chat", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify(body)
  });

  const data = await response.json();
  if(!response.ok || !data.success){
    throw new Error(data.error || data.message || "Conversation failed.");
  }

  const answer = data.response || data.message || "";
  addMessage("ai", answer);

  const selected = data.language || selectedLanguage || "en";
  const detected = data.detected_language || selected;
  const confidence = data.language_confidence;
  const locale = data.speech_locale || localeForLanguage(selected);

  languageInfoBox.textContent =
    "Response language: " + selected +
    " | Detected: " + detected +
    (confidence !== undefined ? " | Confidence: " + confidence : "") +
    " | Speech locale: " + locale;

  speakResponse(answer, selected, locale);
}

async function sendCurrentMessage(){
  const text = messageBox.value.trim();
  if(!text){
    setStatus("Please type a message or use the microphone.");
    messageBox.focus();
    return;
  }

  try{
    sendButton.disabled = true;
    micButton.disabled = true;
    addMessage("patient", text);
    messageBox.value = "";
    autoResize();
    interimBox.textContent = "";
    setStatus("DementiaCareAI is thinking...");
    await sendToCompanion(text);
  }catch(error){
    console.error(error);
    setStatus("Error: " + error.message);
  }finally{
    sendButton.disabled = false;
    micButton.disabled = false;
    messageBox.focus();
  }
}

function createRecognition(){
  const Recognition = recognitionConstructor();
  if(!Recognition) return null;

  const instance = new Recognition();
  instance.continuous = false;
  instance.interimResults = true;
  instance.maxAlternatives = 1;
  instance.lang = localeForLanguage(languageSelect.value || "en");

  instance.onstart = () => {
    listening = true;
    finalTranscript = "";
    micButton.disabled = true;
    stopButton.disabled = false;
    micButton.classList.add("recording");
    setStatus("Listening... speak naturally.");
  };

  instance.onresult = event => {
    let interim = "";
    let finalText = "";

    for(let i = event.resultIndex; i < event.results.length; i++){
      const piece = event.results[i][0].transcript;
      if(event.results[i].isFinal) finalText += piece;
      else interim += piece;
    }

    if(interim) interimBox.textContent = "Hearing: " + interim;
    if(finalText.trim()){
      finalTranscript = finalText.trim();
      messageBox.value = finalTranscript;
      autoResize();
      interimBox.textContent = "Transcript ready. Review it in the message box, then press Send.";
    }
  };

  instance.onerror = event => {
    console.error("STT error", event);
    listening = false;
    micButton.disabled = false;
    stopButton.disabled = true;
    micButton.classList.remove("recording");

    if(event.error === "not-allowed" || event.error === "service-not-allowed"){
      setStatus("Microphone permission was denied. Please allow microphone access.");
    }else if(event.error === "language-not-supported"){
      setStatus("This browser does not provide speech recognition for " + instance.lang + ". You can still type the message.");
    }else{
      setStatus("Speech recognition error: " + (event.error || "unknown"));
    }
  };

  instance.onend = () => {
    listening = false;
    micButton.disabled = false;
    stopButton.disabled = true;
    micButton.classList.remove("recording");

    if(finalTranscript.trim()){
      messageBox.value = finalTranscript.trim();
      autoResize();
      setStatus("Voice transcript is in the message box. Review and press Send.");
    }else if(!messageBox.value.trim()){
      setStatus("No speech was captured. Please try again or type a message.");
    }
  };

  return instance;
}

micButton.addEventListener("click", () => {
  const Recognition = recognitionConstructor();
  if(!Recognition){
    setStatus("This browser does not support SpeechRecognition. Please use Chrome or Edge, or type the message.");
    return;
  }
  if(listening) return;

  recognition = createRecognition();
  if(!recognition) return;

  try{
    recognition.start();
  }catch(error){
    console.error(error);
    setStatus("Could not start the microphone: " + error.message);
  }
});

stopButton.addEventListener("click", () => {
  if(recognition && listening){
    recognition.stop();
    setStatus("Stopping microphone...");
  }
});

sendButton.addEventListener("click", sendCurrentMessage);

messageBox.addEventListener("keydown", event => {
  if(event.key === "Enter" && !event.shiftKey){
    event.preventDefault();
    sendCurrentMessage();
  }
});

function autoResize(){
  messageBox.style.height = "auto";
  messageBox.style.height = Math.min(messageBox.scrollHeight, 150) + "px";
}
messageBox.addEventListener("input", autoResize);
autoResize();

languageSelect.addEventListener("change", () => {
  const locale = localeForLanguage(languageSelect.value || "en");
  if(recognition && !listening) recognition.lang = locale;
  setStatus("Voice language set to " + locale + ".");
});

if("speechSynthesis" in window){
  window.speechSynthesis.getVoices();
  window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}
</script>
</body>
</html>'''

# ============================================================
# CAREGIVER DASHBOARD FRONTEND
# ============================================================

@app.route(
    "/caregiver-dashboard",
    methods=["GET"],
)
def caregiver_dashboard():
    return """
<!DOCTYPE html>
<html lang="en">
<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>DementiaCareAI — Caregiver Dashboard</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family:
        Inter,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
    background: #f5f7fb;
    color: #172033;
}

button,
input,
select,
textarea {
    font: inherit;
}

button {
    cursor: pointer;
}

.layout {
    display: flex;
    min-height: 100vh;
}

.sidebar {
    width: 250px;
    background: #172033;
    color: white;
    padding: 24px 16px;
    position: fixed;
    inset: 0 auto 0 0;
    overflow-y: auto;
}

.brand {
    font-size: 22px;
    font-weight: 800;
    padding: 8px 12px 26px;
}

.brand span {
    display: block;
    font-size: 12px;
    font-weight: 500;
    opacity: .65;
    margin-top: 5px;
}

.nav {
    display: grid;
    gap: 6px;
}

.nav button {
    border: 0;
    background: transparent;
    color: rgba(255,255,255,.72);
    text-align: left;
    padding: 12px 14px;
    border-radius: 10px;
}

.nav button:hover,
.nav button.active {
    background: rgba(255,255,255,.1);
    color: white;
}

.main {
    margin-left: 250px;
    width: calc(100% - 250px);
    padding: 28px;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
    margin-bottom: 24px;
}

.header h1 {
    margin: 0;
    font-size: 28px;
}

.header p {
    margin: 5px 0 0;
    color: #697386;
}

.refresh {
    border: 0;
    border-radius: 10px;
    padding: 11px 16px;
    background: #172033;
    color: white;
}

.cards {
    display: grid;
    grid-template-columns:
        repeat(4, minmax(0, 1fr));
    gap: 16px;
    margin-bottom: 22px;
}

.card {
    background: white;
    border-radius: 16px;
    padding: 20px;
    box-shadow:
        0 5px 20px rgba(20,30,50,.06);
    border: 1px solid #e8ebf1;
}

.metric-label {
    color: #707b8e;
    font-size: 13px;
    margin-bottom: 8px;
}

.metric {
    font-size: 30px;
    font-weight: 800;
}

.grid {
    display: grid;
    grid-template-columns:
        repeat(2, minmax(0, 1fr));
    gap: 20px;
}

.panel {
    background: white;
    border-radius: 16px;
    padding: 20px;
    border: 1px solid #e8ebf1;
    box-shadow:
        0 5px 20px rgba(20,30,50,.05);
}

.panel h2 {
    margin-top: 0;
    font-size: 18px;
}

.table-wrap {
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th,
td {
    padding: 11px 8px;
    border-bottom: 1px solid #edf0f5;
    text-align: left;
    font-size: 13px;
}

th {
    color: #707b8e;
    font-weight: 600;
}

.status {
    margin-bottom: 18px;
    padding: 12px 15px;
    border-radius: 10px;
    background: #eef4ff;
    color: #35558a;
}

.form-grid {
    display: grid;
    grid-template-columns:
        repeat(2, minmax(0, 1fr));
    gap: 12px;
}

.field {
    display: grid;
    gap: 6px;
}

.field.full {
    grid-column: 1 / -1;
}

.field label {
    font-size: 13px;
    font-weight: 600;
}

.field input,
.field select,
.field textarea {
    width: 100%;
    border: 1px solid #dce1ea;
    border-radius: 9px;
    padding: 10px 12px;
    background: white;
}

.field textarea {
    min-height: 100px;
    resize: vertical;
}

.primary {
    border: 0;
    border-radius: 9px;
    padding: 11px 16px;
    background: #315efb;
    color: white;
    font-weight: 700;
}

.secondary {
    border: 1px solid #dce1ea;
    border-radius: 9px;
    padding: 10px 14px;
    background: white;
}

.actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 12px;
}

.image-preview {
    width: 100%;
    max-height: 320px;
    object-fit: contain;
    border-radius: 12px;
    background: #f2f4f8;
    margin-top: 14px;
}

.answer-box {
    margin-top: 16px;
    padding: 15px;
    border-radius: 12px;
    background: #f7f8fb;
}

.result {
    margin-top: 12px;
    padding: 13px;
    border-radius: 10px;
    background: #edf8f0;
}

pre {
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 12px;
    max-height: 420px;
    overflow: auto;
}

.view {
    display: none;
}

.view.active {
    display: block;
}

@media (max-width: 1100px) {

    .cards {
        grid-template-columns:
            repeat(2, minmax(0, 1fr));
    }

    .grid {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 760px) {

    .sidebar {
        position: static;
        width: 100%;
    }

    .layout {
        display: block;
    }

    .main {
        margin-left: 0;
        width: 100%;
        padding: 16px;
    }

    .cards {
        grid-template-columns: 1fr;
    }

    .form-grid {
        grid-template-columns: 1fr;
    }
}

</style>

</head>

<body>

<div class="layout">

<aside class="sidebar">

<div class="brand">
    DementiaCareAI
    <span>Caregiver Intelligence</span>
</div>

<div class="nav">

<button
    class="active"
    data-view="dashboard"
>
    Dashboard
</button>

<button data-view="performance">
    Patient Performance
</button>

<button data-view="interactions">
    Interactions
</button>

<button data-view="memories">
    Memories & Images
</button>

<button data-view="recognition">
    Recognition Activity
</button>

<button data-view="reminders">
    Reminders
</button>

<button data-view="companion">
    Companion
</button>

<button data-view="recommendations">
    Recommendations
</button>

<button data-view="report">
    Reports
</button>

<button data-view="system">
    System Status
</button>

</div>

</aside>

<main class="main">

<div class="header">

<div>
    <h1 id="pageTitle">
        Caregiver Dashboard
    </h1>

    <p>
        Monitor patient engagement,
        memory activities and companion interactions.
    </p>
</div>

<button
    class="refresh"
    onclick="loadEverything()"
>
    Refresh
</button>

</div>

<div
    id="status"
    class="status"
>
    Loading caregiver data...
</div>

<section
    id="dashboard"
    class="view active"
>

<div class="cards">

<div class="card">
    <div class="metric-label">
        Total Interactions
    </div>
    <div
        id="metricInteractions"
        class="metric"
    >—</div>
</div>

<div class="card">
    <div class="metric-label">
        Correct Interactions
    </div>
    <div
        id="metricCorrect"
        class="metric"
    >—</div>
</div>

<div class="card">
    <div class="metric-label">
        Images Uploaded
    </div>
    <div
        id="metricImages"
        class="metric"
    >—</div>
</div>

<div class="card">
    <div class="metric-label">
        Current Mood
    </div>
    <div
        id="metricMood"
        class="metric"
    >—</div>
</div>

</div>

<div class="grid">

<div class="panel">

<h2>Overview</h2>

<pre id="overviewOutput">
Loading...
</pre>

</div>

<div class="panel">

<h2>Today's Activity</h2>

<pre id="todayOutput">
Loading...
</pre>

</div>

</div>

</section>


<section
    id="performance"
    class="view"
>

<div class="panel">

<h2>Patient Performance</h2>

<pre id="performanceOutput">
Loading...
</pre>

</div>

</section>


<section
    id="interactions"
    class="view"
>

<div class="panel">

<h2>Conversation & Interaction History</h2>

<pre id="conversationOutput">
Loading...
</pre>

</div>

</section>


<section
    id="memories"
    class="view"
>

<div class="grid">

<div class="panel">

<h2>Patient Memories</h2>

<div
    id="memoryList"
>
Loading...
</div>

</div>

<div class="panel">

<h2>Upload Patient Image</h2>

<div class="field">

<label>
Memory
</label>

<select
    id="memorySelect"
>
<option value="">
Loading memories...
</option>
</select>

</div>

<div class="field">

<label>
Image
</label>

<input
    id="imageFile"
    type="file"
    accept="image/jpeg,image/png,image/webp"
>

</div>

<div class="field">

<label>
Caption
</label>

<input
    id="imageCaption"
    type="text"
    placeholder="Example: Family photo"
>

</div>

<div class="actions">

<button
    class="primary"
    onclick="uploadImage()"
>
Upload Image
</button>

</div>

<div id="uploadResult"></div>

</div>

</div>

</section>


<section
    id="recognition"
    class="view"
>

<div class="grid">

<div class="panel">

<h2>Recognition / Memory Activity</h2>

<div class="field">

<label>
Patient Memory
</label>

<select
    id="activityMemorySelect"
>
<option value="">
Select memory
</option>
</select>

</div>

<div class="actions">

<button
    class="primary"
    onclick="createActivity()"
>
Start Activity
</button>

</div>

<div
    id="activityQuestion"
    class="answer-box"
>
No activity started.
</div>

</div>

<div class="panel">

<h2>Patient Answer</h2>

<div class="field">

<label>
Answer
</label>

<textarea
    id="patientAnswer"
    placeholder="Enter the patient's answer here..."
></textarea>

</div>

<div class="actions">

<button
    class="primary"
    onclick="evaluateActivity()"
>
Evaluate Answer
</button>

</div>

<div id="evaluationResult"></div>

</div>

</div>

</section>


<section
    id="reminders"
    class="view"
>

<div class="panel">

<h2>Reminders</h2>

<pre id="remindersOutput">
Loading...
</pre>

</div>

</section>


<section
    id="companion"
    class="view"
>

<div class="panel">

<h2>Companion State</h2>

<pre id="companionOutput">
Loading...
</pre>

</div>

</section>


<section
    id="recommendations"
    class="view"
>

<div class="panel">

<h2>Caregiver Recommendations</h2>

<pre id="recommendationsOutput">
Loading...
</pre>

</div>

</section>


<section
    id="report"
    class="view"
>

<div class="panel">

<h2>Caregiver Report</h2>

<pre id="reportOutput">
Loading...
</pre>

</div>

</section>


<section
    id="system"
    class="view"
>

<div class="grid">

<div class="panel">

<h2>Backend Status</h2>

<pre id="systemOutput">
Loading...
</pre>

</div>

<div class="panel">

<h2>Database Status</h2>

<pre id="databaseOutput">
Loading...
</pre>

</div>

</div>

</section>

</main>

</div>


<script>

const statusBox =
    document.getElementById("status");

const pageTitle =
    document.getElementById("pageTitle");


function setStatus(
    message
) {
    statusBox.textContent =
        message;
}


async function api(
    url,
    options = {}
) {

    const response =
        await fetch(
            url,
            options
        );

    let data = null;

    try {
        data =
            await response.json();
    } catch (_) {
        data = {};
    }

    if (!response.ok) {

        throw new Error(
            data.error ||
            data.message ||
            `Request failed: ${response.status}`
        );
    }

    return data;
}


function pretty(
    value
) {

    return JSON.stringify(
        value,
        null,
        2
    );
}


function findNumber(
    object,
    keys
) {

    if (
        object === null ||
        object === undefined
    ) {
        return null;
    }

    if (
        typeof object !== "object"
    ) {
        return null;
    }

    for (
        const key of keys
    ) {

        if (
            typeof object[key] ===
            "number"
        ) {
            return object[key];
        }
    }

    for (
        const value of Object.values(
            object
        )
    ) {

        if (
            value &&
            typeof value === "object"
        ) {

            const result =
                findNumber(
                    value,
                    keys
                );

            if (
                result !== null
            ) {
                return result;
            }
        }
    }

    return null;
}


function findArray(
    object,
    keys
) {

    if (
        !object ||
        typeof object !== "object"
    ) {
        return null;
    }

    for (
        const key of keys
    ) {

        if (
            Array.isArray(
                object[key]
            )
        ) {
            return object[key];
        }
    }

    for (
        const value of Object.values(
            object
        )
    ) {

        if (
            value &&
            typeof value === "object"
        ) {

            const result =
                findArray(
                    value,
                    keys
                );

            if (
                result
            ) {
                return result;
            }
        }
    }

    return null;
}


async function loadOverview() {

    const data =
        await api(
            "/api/caregiver/overview"
        );

    document.getElementById(
        "overviewOutput"
    ).textContent =
        pretty(data);

    const total =
        findNumber(
            data,
            [
                "total_interactions",
                "totalInteractions",
                "interactions",
                "total"
            ]
        );

    if (
        total !== null
    ) {
        document.getElementById(
            "metricInteractions"
        ).textContent =
            total;
    }
}


async function loadToday() {

    const data =
        await api(
            "/api/caregiver/today"
        );

    document.getElementById(
        "todayOutput"
    ).textContent =
        pretty(data);
}


async function loadPerformance() {

    const [
        cognitive,
        activity
    ] =
        await Promise.all([
            api(
                "/api/caregiver/cognitive"
            ),
            api(
                "/api/caregiver/activity"
            )
        ]);

    document.getElementById(
        "performanceOutput"
    ).textContent =
        pretty({
            cognitive,
            activity
        });

    const correct =
        findNumber(
            cognitive,
            [
                "correct_interactions",
                "correctInteractions",
                "correct_answers",
                "correctAnswers",
                "correct"
            ]
        );

    if (
        correct !== null
    ) {

        document.getElementById(
            "metricCorrect"
        ).textContent =
            correct;
    }
}


async function loadConversation() {

    const data =
        await api(
            "/api/caregiver/conversation"
        );

    document.getElementById(
        "conversationOutput"
    ).textContent =
        pretty(data);
}


async function loadMemories() {

    const data =
        await api(
            "/api/caregiver/memory"
        );

    document.getElementById(
        "memoryList"
    ).innerHTML =
        `<pre>${pretty(data)}</pre>`;

    const memories =
        await api(
            "/api/memories"
        );

    const list =
        Array.isArray(
            memories.memories
        )
            ? memories.memories
            : [];

    const selects = [
        document.getElementById(
            "memorySelect"
        ),
        document.getElementById(
            "activityMemorySelect"
        )
    ];

    for (
        const select of selects
    ) {

        select.innerHTML =
            `<option value="">
                Select memory
            </option>`;

        for (
            const memory of list
        ) {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                memory.id ??
                memory.memory_id ??
                "";

            option.textContent =
                memory.name ||
                memory.title ||
                memory.description ||
                "Memory";

            if (
                option.value
            ) {
                select.appendChild(
                    option
                );
            }
        }
    }

    let imageCount =
        findNumber(
            data,
            [
                "images_uploaded",
                "image_count",
                "images",
                "photo_count"
            ]
        );

    if (
        imageCount === null
    ) {

        imageCount =
            findArray(
                data,
                [
                    "media",
                    "images",
                    "photos"
                ]
            );

        if (
            Array.isArray(
                imageCount
            )
        ) {
            imageCount =
                imageCount.length;
        }
    }

    if (
        typeof imageCount === "number"
    ) {

        document.getElementById(
            "metricImages"
        ).textContent =
            imageCount;
    }
}


async function loadReminders() {

    const data =
        await api(
            "/api/caregiver/reminders"
        );

    document.getElementById(
        "remindersOutput"
    ).textContent =
        pretty(data);
}


async function loadCompanion() {

    const data =
        await api(
            "/api/caregiver/companion"
        );

    document.getElementById(
        "companionOutput"
    ).textContent =
        pretty(data);

    const mood =
        data.current_mood ||
        data.mood ||
        data.state?.current_mood;

    if (
        mood
    ) {

        document.getElementById(
            "metricMood"
        ).textContent =
            mood;
    }
}


async function loadRecommendations() {

    const data =
        await api(
            "/api/caregiver/recommendations"
        );

    document.getElementById(
        "recommendationsOutput"
    ).textContent =
        pretty(data);
}


async function loadReport() {

    const data =
        await api(
            "/api/caregiver/report"
        );

    document.getElementById(
        "reportOutput"
    ).textContent =
        pretty(data);
}


async function loadSystem() {

    const [
        status,
        database
    ] =
        await Promise.all([
            api(
                "/api/status"
            ),
            api(
                "/api/database/status"
            )
        ]);

    document.getElementById(
        "systemOutput"
    ).textContent =
        pretty(status);

    document.getElementById(
        "databaseOutput"
    ).textContent =
        pretty(database);
}


async function uploadImage() {

    const memoryId =
        document.getElementById(
            "memorySelect"
        ).value;

    const file =
        document.getElementById(
            "imageFile"
        ).files[0];

    const caption =
        document.getElementById(
            "imageCaption"
        ).value;

    if (
        !memoryId
    ) {

        alert(
            "Select a memory first."
        );

        return;
    }

    if (
        !file
    ) {

        alert(
            "Select an image first."
        );

        return;
    }

    const form =
        new FormData();

    form.append(
        "file",
        file
    );

    form.append(
        "media_type",
        "photo"
    );

    form.append(
        "caption",
        caption
    );

    try {

        setStatus(
            "Uploading patient image..."
        );

        const result =
            await api(
                `/api/memories/${encodeURIComponent(memoryId)}/media`,
                {
                    method: "POST",
                    body: form
                }
            );

        document.getElementById(
            "uploadResult"
        ).innerHTML =
            `<div class="result">
                Image uploaded successfully.
                <pre>${pretty(result)}</pre>
            </div>`;

        setStatus(
            "Patient image uploaded successfully."
        );

        await loadMemories();

    } catch (
        error
    ) {

        setStatus(
            error.message
        );
    }
}


let currentActivity =
    null;


async function createActivity() {

    const memoryId =
        document.getElementById(
            "activityMemorySelect"
        ).value;

    if (
        !memoryId
    ) {

        alert(
            "Select a memory first."
        );

        return;
    }

    try {

        setStatus(
            "Creating patient activity..."
        );

        const result =
            await api(
                `/api/activity/create?memory_id=${encodeURIComponent(memoryId)}`
            );

        currentActivity =
            result.activity;

        document.getElementById(
            "activityQuestion"
        ).textContent =
            currentActivity?.question ||
            currentActivity?.prompt ||
            currentActivity?.title ||
            "Activity created. See activity data below.";

        setStatus(
            "Recognition / memory activity ready."
        );

    } catch (
        error
    ) {

        setStatus(
            error.message
        );
    }
}


async function evaluateActivity() {

    if (
        !currentActivity
    ) {

        alert(
            "Start an activity first."
        );

        return;
    }

    const answer =
        document.getElementById(
            "patientAnswer"
        ).value.trim();

    if (
        !answer
    ) {

        alert(
            "Enter the patient's answer."
        );

        return;
    }

    try {

        setStatus(
            "Evaluating patient response..."
        );

        const result =
            await api(
                "/api/memory-activity/evaluate",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        activity:
                            currentActivity,

                        answer:
                            answer
                    })
                }
            );

        document.getElementById(
            "evaluationResult"
        ).innerHTML =
            `<div class="result">
                <strong>Patient response recorded.</strong>
                <pre>${pretty(result)}</pre>
            </div>`;

        setStatus(
            "Patient response evaluated and recorded."
        );

        await loadPerformance();

    } catch (
        error
    ) {

        setStatus(
            error.message
        );
    }
}


async function loadEverything() {

    setStatus(
        "Loading caregiver dashboard..."
    );

    try {

        await Promise.all([
            loadOverview(),
            loadToday(),
            loadPerformance(),
            loadConversation(),
            loadMemories(),
            loadReminders(),
            loadCompanion(),
            loadRecommendations(),
            loadReport(),
            loadSystem()
        ]);

        setStatus(
            "Caregiver dashboard is connected."
        );

    } catch (
        error
    ) {

        console.error(
            error
        );

        setStatus(
            "Dashboard connection error: "
            + error.message
        );
    }
}


document.querySelectorAll(
    ".nav button"
).forEach(
    button => {

        button.addEventListener(
            "click",
            () => {

                document.querySelectorAll(
                    ".nav button"
                ).forEach(
                    item =>
                        item.classList.remove(
                            "active"
                        )
                );

                button.classList.add(
                    "active"
                );

                document.querySelectorAll(
                    ".view"
                ).forEach(
                    view =>
                        view.classList.remove(
                            "active"
                        )
                );

                const id =
                    button.dataset.view;

                const target =
                    document.getElementById(
                        id
                    );

                if (
                    target
                ) {
                    target.classList.add(
                        "active"
                    );
                }

                pageTitle.textContent =
                    button.textContent.trim();
            }
        );

    }
);


loadEverything();

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