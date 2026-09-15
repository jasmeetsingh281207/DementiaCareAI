"""
DementiaCareAI voice layer.

This module provides one canonical voice layer for DementiaCareAI.
- STT is performed by the browser's SpeechRecognition/Web Speech API.
- TTS first uses server-side Google gTTS when available, so supported languages
  do not depend on an installed browser voice.
- The frontend may still use browser speechSynthesis as a local fallback.

The application never silently changes a requested language. Hinglish
intentionally uses Hindi speech (hi-IN).
"""

from __future__ import annotations

import base64
import binascii
from typing import Any
from io import BytesIO

try:
    from language import detect_language, get_language, normalize_language
except Exception:  # pragma: no cover - startup/import fallback
    detect_language = None
    get_language = None
    normalize_language = None

try:
    from gtts import gTTS
except Exception:  # pragma: no cover - optional dependency
    gTTS = None


SUPPORTED_VOICE_LANGUAGES: dict[str, dict[str, Any]] = {
    "en": {"name": "English", "native_name": "English", "speech_locale": "en-IN", "stt_locale": "en-IN", "base_language": "en"},
    "hi": {"name": "Hindi", "native_name": "हिन्दी", "speech_locale": "hi-IN", "stt_locale": "hi-IN", "base_language": "hi"},
    "hinglish": {"name": "Hinglish", "native_name": "Hinglish", "speech_locale": "hi-IN", "stt_locale": "hi-IN", "base_language": "hi", "is_hinglish": True},
    "as": {"name": "Assamese", "native_name": "অসমীয়া", "speech_locale": "as-IN", "stt_locale": "as-IN", "base_language": "as"},
    "bn": {"name": "Bengali", "native_name": "বাংলা", "speech_locale": "bn-IN", "stt_locale": "bn-IN", "base_language": "bn"},
    "mr": {"name": "Marathi", "native_name": "मराठी", "speech_locale": "mr-IN", "stt_locale": "mr-IN", "base_language": "mr"},
    "ur": {"name": "Urdu", "native_name": "اردو", "speech_locale": "ur-IN", "stt_locale": "ur-IN", "base_language": "ur"},
    "pa": {"name": "Punjabi", "native_name": "ਪੰਜਾਬੀ", "speech_locale": "pa-IN", "stt_locale": "pa-IN", "base_language": "pa"},
    "gu": {"name": "Gujarati", "native_name": "ગુજરાતી", "speech_locale": "gu-IN", "stt_locale": "gu-IN", "base_language": "gu"},
    "or": {"name": "Odia", "native_name": "ଓଡ଼ିଆ", "speech_locale": "or-IN", "stt_locale": "or-IN", "base_language": "or"},
    "ta": {"name": "Tamil", "native_name": "தமிழ்", "speech_locale": "ta-IN", "stt_locale": "ta-IN", "base_language": "ta"},
    "te": {"name": "Telugu", "native_name": "తెలుగు", "speech_locale": "te-IN", "stt_locale": "te-IN", "base_language": "te"},
    "kn": {"name": "Kannada", "native_name": "ಕನ್ನಡ", "speech_locale": "kn-IN", "stt_locale": "kn-IN", "base_language": "kn"},
    "ml": {"name": "Malayalam", "native_name": "മലയാളം", "speech_locale": "ml-IN", "stt_locale": "ml-IN", "base_language": "ml"},
    "ne": {"name": "Nepali", "native_name": "नेपाली", "speech_locale": "ne-NP", "stt_locale": "ne-NP", "base_language": "ne"},
    "mni": {"name": "Manipuri / Meitei", "native_name": "মৈতৈলোন্", "speech_locale": "mni-IN", "stt_locale": "mni-IN", "base_language": "mni"},
    "brx": {"name": "Bodo", "native_name": "बड़ो", "speech_locale": "brx-IN", "stt_locale": "brx-IN", "base_language": "brx"},
    "kha": {"name": "Khasi", "native_name": "Khasi", "speech_locale": "kha-IN", "stt_locale": "kha-IN", "base_language": "kha"},
    "grt": {"name": "Garo", "native_name": "A·chik", "speech_locale": "grt-IN", "stt_locale": "grt-IN", "base_language": "grt"},
    "lus": {"name": "Mizo", "native_name": "Mizo", "speech_locale": "lus-IN", "stt_locale": "lus-IN", "base_language": "lus"},
    "trp": {"name": "Tripuri / Kokborok", "native_name": "Kokborok", "speech_locale": "trp-IN", "stt_locale": "trp-IN", "base_language": "trp"},
}


# Google gTTS language identifiers. gTTS support is intentionally explicit:
# if a language is not in this table, the server never substitutes another
# language. The browser fallback can still be used when an exact local voice
# exists.
GTTS_LANGUAGE_CODES = {
    "en": "en",
    "hi": "hi",
    "hinglish": "hi",
    "as": "as",
    "bn": "bn",
    "mr": "mr",
    "ur": "ur",
    "pa": "pa",
    "gu": "gu",
    "or": "or",
    "ta": "ta",
    "te": "te",
    "kn": "kn",
    "ml": "ml",
    "ne": "ne",
}


ALIASES = {
    "english": "en", "en-in": "en",
    "hindi": "hi", "hi-in": "hi",
    "hinglish": "hinglish",
    "assamese": "as", "as-in": "as",
    "bengali": "bn", "bangla": "bn", "bn-in": "bn",
    "marathi": "mr", "mr-in": "mr",
    "urdu": "ur", "ur-in": "ur",
    "punjabi": "pa", "pa-in": "pa",
    "gujarati": "gu", "gu-in": "gu",
    "odia": "or", "oriya": "or", "or-in": "or",
    "tamil": "ta", "ta-in": "ta",
    "telugu": "te", "te-in": "te",
    "kannada": "kn", "kn-in": "kn",
    "malayalam": "ml", "ml-in": "ml",
    "nepali": "ne", "ne-np": "ne",
    "manipuri": "mni", "meitei": "mni", "mni-in": "mni",
    "bodo": "brx", "brx-in": "brx",
    "khasi": "kha", "kha-in": "kha",
    "garo": "grt", "grt-in": "grt",
    "mizo": "lus", "lus-in": "lus",
    "tripuri": "trp", "kokborok": "trp", "trp-in": "trp",
}


def _normalize(code: str | None) -> str | None:
    if not isinstance(code, str):
        return None
    value = code.strip().lower()
    if not value:
        return None
    if value in SUPPORTED_VOICE_LANGUAGES:
        return value
    if value in ALIASES:
        return ALIASES[value]
    if normalize_language is not None:
        try:
            normalized = normalize_language(value)
            if isinstance(normalized, str) and normalized in SUPPORTED_VOICE_LANGUAGES:
                return normalized
        except Exception:
            pass
    return None


def _info(code: str) -> dict[str, Any]:
    data = dict(SUPPORTED_VOICE_LANGUAGES[code])
    data["code"] = code
    data.setdefault("is_hinglish", code == "hinglish")
    return data


def get_voice_config(language: str | None = None) -> dict[str, Any]:
    """Return one voice configuration or the complete 21-language table."""
    if language is None or not str(language).strip():
        return {
            "success": True,
            "provider": "browser_stt_server_tts",
            "stt": "SpeechRecognition / webkitSpeechRecognition",
            "tts": "server_gtts_with_browser_fallback",
            "languages": [_info(code) for code in SUPPORTED_VOICE_LANGUAGES],
            "language_count": len(SUPPORTED_VOICE_LANGUAGES),
        }

    code = _normalize(language)
    if code is None:
        raise ValueError("Unsupported voice language.")

    return {
        "success": True,
        "provider": "browser_stt_server_tts",
        "stt": "SpeechRecognition / webkitSpeechRecognition",
        "tts": "server_gtts_with_browser_fallback",
        "language": _info(code),
    }


def get_voice_status(language: str | None = None) -> dict[str, Any]:
    """Return backend voice status without pretending a browser voice exists."""
    config = get_voice_config(language)
    return {
        "success": True,
        "available": True,
        "provider": "browser_stt_server_tts",
        "stt": {
            "available": True,
            "requires_browser_speech_recognition": True,
            "note": "Actual recognition support depends on the browser/device.",
        },
        "tts": {
            "available": bool(gTTS),
            "server_provider": "gTTS" if gTTS else None,
            "browser_fallback": True,
            "note": "Server TTS requires gTTS and network access; browser speechSynthesis is a client-side fallback.",
        },
        "language_count": len(SUPPORTED_VOICE_LANGUAGES),
        "languages": config.get("languages") or [config["language"]],
    }


def browser_voice_instruction(language: str | None = None) -> dict[str, Any]:
    """Return frontend instructions for browser STT/TTS."""
    code = _normalize(language) if language else None
    if language and code is None:
        raise ValueError("Unsupported voice language.")

    return {
        "success": True,
        "provider": "browser_stt_server_tts",
        "language": _info(code) if code else None,
        "stt": {
            "api": "SpeechRecognition",
            "fallback_api": "webkitSpeechRecognition",
            "continuous": False,
            "interim_results": True,
        },
        "tts": {
            "server_api": "/api/voice/speak",
            "browser_api": "speechSynthesis",
            "server_language_supported": bool(code in GTTS_LANGUAGE_CODES) if code else False,
            "exact_locale_required": True,
            "fallback_to_unrelated_language": False,
        },
    }


def process_voice_transcript(text: str, language: str | None = None) -> dict[str, Any]:
    """Validate browser STT text and resolve its language locally."""
    if not isinstance(text, str):
        return {"success": False, "error": "text_must_be_text"}

    cleaned = text.strip()
    if not cleaned:
        return {"success": False, "error": "text_required"}
    if len(cleaned) > 5000:
        return {"success": False, "error": "text_too_long"}

    explicit = _normalize(language) if language else None
    if language and explicit is None:
        return {"success": False, "error": "unsupported_language"}

    detected = None
    confidence = None
    if explicit:
        detected = explicit
    elif detect_language is not None:
        try:
            result = detect_language(cleaned)
            if isinstance(result, dict):
                detected = _normalize(
                    result.get("code")
                    or result.get("language")
                    or result.get("detected_language")
                )
                confidence = result.get("confidence")
            else:
                detected = _normalize(result)
        except Exception:
            detected = None

    detected = detected or "en"
    info = _info(detected)
    return {
        "success": True,
        "text": cleaned,
        "language": detected,
        "detected_language": detected,
        "language_info": info,
        "speech_locale": info["speech_locale"],
        "confidence": confidence,
        "local_detection": not bool(explicit),
    }


def synthesize_speech(text: str, language: str) -> dict[str, Any]:
    """Generate exact-language MP3 audio using server-side gTTS.

    Returns bytes in-memory so Flask can stream them directly. No unrelated
    language is ever substituted.
    """
    if not isinstance(text, str) or not text.strip():
        return {"success": False, "error": "text_required"}
    if len(text) > 5000:
        return {"success": False, "error": "text_too_long"}

    code = _normalize(language)
    if code is None:
        return {"success": False, "error": "unsupported_language"}

    gtts_code = GTTS_LANGUAGE_CODES.get(code)
    if not gtts_code:
        return {
            "success": False,
            "error": "server_tts_language_not_supported",
            "language": code,
            "speech_locale": SUPPORTED_VOICE_LANGUAGES[code]["speech_locale"],
        }

    if gTTS is None:
        return {
            "success": False,
            "error": "server_tts_dependency_missing",
            "language": code,
        }

    audio = BytesIO()
    try:
        tts = gTTS(text=text.strip(), lang=gtts_code, slow=False)
        tts.write_to_fp(audio)
        audio.seek(0)
        return {
            "success": True,
            "language": code,
            "speech_locale": SUPPORTED_VOICE_LANGUAGES[code]["speech_locale"],
            "content_type": "audio/mpeg",
            "audio": audio.read(),
            "provider": "gTTS",
        }
    except Exception as exc:
        return {
            "success": False,
            "error": "server_tts_failed",
            # Do not expose provider/network implementation details to clients.
            "language": code,
        }


def validate_audio_payload(audio: Any, content_type: str | None = None) -> dict[str, Any]:
    """Validate an optional base64 audio payload for future server-side STT."""
    if audio is None:
        return {"success": False, "valid": False, "error": "audio_required"}
    if not isinstance(audio, str):
        return {"success": False, "valid": False, "error": "audio_must_be_base64_text"}
    if len(audio) > 100 * 1024 * 1024:
        return {"success": False, "valid": False, "error": "audio_too_large"}
    try:
        raw = base64.b64decode(audio, validate=True)
    except (binascii.Error, ValueError):
        return {"success": False, "valid": False, "error": "invalid_base64_audio"}
    if not raw:
        return {"success": False, "valid": False, "error": "empty_audio"}
    return {
        "success": True,
        "valid": True,
        "bytes": len(raw),
        "content_type": content_type or "application/octet-stream",
    }


# Backward-compatible aliases for code that may use these names.
get_tts_config = get_voice_config
get_stt_config = get_voice_config


__all__ = [
    "SUPPORTED_VOICE_LANGUAGES",
    "get_voice_config",
    "get_voice_status",
    "browser_voice_instruction",
    "process_voice_transcript",
    "validate_audio_payload",
    "synthesize_speech",
    "get_tts_config",
    "get_stt_config",
]
