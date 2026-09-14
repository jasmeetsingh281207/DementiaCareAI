"""
DementiaCareAI - Multilingual Language Engine
==============================================

India-first multilingual language detection and companion language
preparation.

Supported languages:
    en       English
    hi       Hindi
    hinglish Hinglish
    as       Assamese
    bn       Bengali
    mr       Marathi
    ur       Urdu
    pa       Punjabi
    gu       Gujarati
    or       Odia
    ta       Tamil
    te       Telugu
    kn       Kannada
    ml       Malayalam
    ne       Nepali
    mni      Manipuri / Meitei
    brx      Bodo
    kha      Khasi
    grt      Garo
    lus      Mizo
    trp      Tripuri / Kokborok

Important:
    Language detection is 100% local.
    Gemini is NEVER used for detection.

Gemini may only be used by the explicit translation API.
"""

from __future__ import annotations

import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ============================================================================
# LANGUAGE DEFINITIONS
# ============================================================================

SUPPORTED_LANGUAGES: Dict[str, Dict[str, str]] = {
    "en": {
        "name": "English",
        "native_name": "English",
        "locale": "en-IN",
        "speech_locale": "en-IN",
        "script": "Latin",
        "base_language": "en",
    },
    "hi": {
        "name": "Hindi",
        "native_name": "हिन्दी",
        "locale": "hi-IN",
        "speech_locale": "hi-IN",
        "script": "Devanagari",
        "base_language": "hi",
    },
    "hinglish": {
        "name": "Hinglish",
        "native_name": "Hinglish",
        "locale": "hi-IN",
        "speech_locale": "hi-IN",
        "script": "Latin",
        "base_language": "hi",
    },
    "as": {
        "name": "Assamese",
        "native_name": "অসমীয়া",
        "locale": "as-IN",
        "speech_locale": "as-IN",
        "script": "Bengali",
        "base_language": "as",
    },
    "bn": {
        "name": "Bengali",
        "native_name": "বাংলা",
        "locale": "bn-IN",
        "speech_locale": "bn-IN",
        "script": "Bengali",
        "base_language": "bn",
    },
    "mr": {
        "name": "Marathi",
        "native_name": "मराठी",
        "locale": "mr-IN",
        "speech_locale": "mr-IN",
        "script": "Devanagari",
        "base_language": "mr",
    },
    "ur": {
        "name": "Urdu",
        "native_name": "اردو",
        "locale": "ur-IN",
        "speech_locale": "ur-IN",
        "script": "Arabic",
        "base_language": "ur",
    },
    "pa": {
        "name": "Punjabi",
        "native_name": "ਪੰਜਾਬੀ",
        "locale": "pa-IN",
        "speech_locale": "pa-IN",
        "script": "Gurmukhi",
        "base_language": "pa",
    },
    "gu": {
        "name": "Gujarati",
        "native_name": "ગુજરાતી",
        "locale": "gu-IN",
        "speech_locale": "gu-IN",
        "script": "Gujarati",
        "base_language": "gu",
    },
    "or": {
        "name": "Odia",
        "native_name": "ଓଡ଼ିଆ",
        "locale": "or-IN",
        "speech_locale": "or-IN",
        "script": "Odia",
        "base_language": "or",
    },
    "ta": {
        "name": "Tamil",
        "native_name": "தமிழ்",
        "locale": "ta-IN",
        "speech_locale": "ta-IN",
        "script": "Tamil",
        "base_language": "ta",
    },
    "te": {
        "name": "Telugu",
        "native_name": "తెలుగు",
        "locale": "te-IN",
        "speech_locale": "te-IN",
        "script": "Telugu",
        "base_language": "te",
    },
    "kn": {
        "name": "Kannada",
        "native_name": "ಕನ್ನಡ",
        "locale": "kn-IN",
        "speech_locale": "kn-IN",
        "script": "Kannada",
        "base_language": "kn",
    },
    "ml": {
        "name": "Malayalam",
        "native_name": "മലയാളം",
        "locale": "ml-IN",
        "speech_locale": "ml-IN",
        "script": "Malayalam",
        "base_language": "ml",
    },
    "ne": {
        "name": "Nepali",
        "native_name": "नेपाली",
        "locale": "ne-IN",
        "speech_locale": "ne-IN",
        "script": "Devanagari",
        "base_language": "ne",
    },
    "mni": {
        "name": "Manipuri / Meitei",
        "native_name": "মেইতেই / ꯃꯤꯇꯩ",
        "locale": "mni-IN",
        "speech_locale": "mni-IN",
        "script": "Meitei/Bengali",
        "base_language": "mni",
    },
    "brx": {
        "name": "Bodo",
        "native_name": "बर' / बड़ो",
        "locale": "brx-IN",
        "speech_locale": "brx-IN",
        "script": "Devanagari",
        "base_language": "brx",
    },
    "kha": {
        "name": "Khasi",
        "native_name": "Khasi",
        "locale": "kha-IN",
        "speech_locale": "kha-IN",
        "script": "Latin",
        "base_language": "kha",
    },
    "grt": {
        "name": "Garo",
        "native_name": "A·chik / Garo",
        "locale": "grt-IN",
        "speech_locale": "grt-IN",
        "script": "Latin",
        "base_language": "grt",
    },
    "lus": {
        "name": "Mizo",
        "native_name": "Mizo",
        "locale": "lus-IN",
        "speech_locale": "lus-IN",
        "script": "Latin",
        "base_language": "lus",
    },
    "trp": {
        "name": "Tripuri / Kokborok",
        "native_name": "Kokborok",
        "locale": "trp-IN",
        "speech_locale": "trp-IN",
        "script": "Latin",
        "base_language": "trp",
    },
}


SUPPORTED_LANGUAGE_COUNT = 21

DEFAULT_LANGUAGE = "en"
DEFAULT_INDIAN_LANGUAGE = "hi"

MAX_DETECTION_TEXT_LENGTH = 5000
MAX_TRANSLATION_TEXT_LENGTH = 10000


# ============================================================================
# ALIASES
# ============================================================================

LANGUAGE_ALIASES: Dict[str, str] = {
    "english": "en",
    "eng": "en",
    "en": "en",
    "en-in": "en",
    "en-us": "en",
    "en-gb": "en",

    "hindi": "hi",
    "hindi language": "hi",
    "हिंदी": "hi",
    "हिन्दी": "hi",
    "hi": "hi",
    "hi-in": "hi",

    "hinglish": "hinglish",
    "hinglish language": "hinglish",

    "assamese": "as",
    "অসমীয়া": "as",
    "অসমিয়া": "as",
    "as": "as",
    "as-in": "as",

    "bengali": "bn",
    "bangla": "bn",
    "বাংলা": "bn",
    "bn": "bn",
    "bn-in": "bn",

    "marathi": "mr",
    "मराठी": "mr",
    "mr": "mr",
    "mr-in": "mr",

    "urdu": "ur",
    "اردو": "ur",
    "ur": "ur",
    "ur-in": "ur",

    "punjabi": "pa",
    "ਪੰਜਾਬੀ": "pa",
    "pa": "pa",
    "pa-in": "pa",

    "gujarati": "gu",
    "ગુજરાતી": "gu",
    "gu": "gu",
    "gu-in": "gu",

    "odia": "or",
    "oriya": "or",
    "ଓଡ଼ିଆ": "or",
    "or": "or",
    "or-in": "or",

    "tamil": "ta",
    "தமிழ்": "ta",
    "ta": "ta",
    "ta-in": "ta",

    "telugu": "te",
    "తెలుగు": "te",
    "te": "te",
    "te-in": "te",

    "kannada": "kn",
    "ಕನ್ನಡ": "kn",
    "kn": "kn",
    "kn-in": "kn",

    "malayalam": "ml",
    "മലയാളം": "ml",
    "ml": "ml",
    "ml-in": "ml",

    "nepali": "ne",
    "नेपाली": "ne",
    "ne": "ne",
    "ne-in": "ne",

    "manipuri": "mni",
    "meitei": "mni",
    "মেইতেই": "mni",
    "ꯃꯤꯇꯩ": "mni",
    "mni": "mni",
    "mni-in": "mni",

    "bodo": "brx",
    "बरो": "brx",
    "बर'": "brx",
    "बड़ो": "brx",
    "brx": "brx",
    "brx-in": "brx",

    "khasi": "kha",
    "kha": "kha",
    "kha-in": "kha",

    "garo": "grt",
    "a·chik": "grt",
    "achik": "grt",
    "grt": "grt",
    "grt-in": "grt",

    "mizo": "lus",
    "lus": "lus",
    "lus-in": "lus",

    "tripuri": "trp",
    "kokborok": "trp",
    "kok borok": "trp",
    "trp": "trp",
    "trp-in": "trp",
}


# ============================================================================
# VOCABULARIES
# ============================================================================

HINDI_WORDS = {
    "मैं", "मुझे", "मेरा", "मेरी", "मेरे",
    "आप", "आपका", "आपकी", "आपके", "आपने",
    "तुम", "तुम्हें", "तुम्हारा", "तुम्हारी", "तुम्हारे",
    "यह", "ये", "वह", "वे",
    "क्या", "क्यों", "कैसे", "कैसा", "कैसी",
    "कब", "कहाँ", "हैं", "है", "था", "थी", "थे",
    "हूँ", "नहीं", "हाँ", "और", "लेकिन", "या",
    "क्योंकि", "अभी", "फिर",
    "दवा", "दवाई", "याद",
    "बेटी", "बेटा", "माँ", "मम्मी", "पापा",
    "परिवार", "बात", "करना", "करो", "करें",
    "चलो", "सोना", "उठना",
    "सुबह", "शाम", "रात",
    "घर", "पानी", "खाना",
    "कौन", "किस", "किसे", "किसका",
    "चाहता", "चाहती", "चाहते",
}

MARATHI_WORDS = {
    "मला", "माझा", "माझी", "माझे", "माझ्या", "माझं",
    "तुला", "तुम्हाला",
    "तुमचा", "तुमची", "तुमचे", "तुमच्या",
    "आपल्याला", "आपला", "आपली", "आपले",
    "आहे", "आहेत", "होता", "होते", "होती",
    "काय", "कसे", "कशी", "कसा",
    "आणि", "पण", "म्हणून", "उद्या",
    "जेवण", "आई", "वडील", "मुलगी", "मुलगा",
    "आठवण", "करा", "करतो", "करते", "करणे",
    "जाते", "जातो", "गेलो", "गेली",
    "येते", "येतो", "आलो", "आली",
    "कुठे", "कधी", "का", "पाहिजे", "नको",
    "छान", "ठीक", "बरं", "बर",
    "सकाळी", "संध्याकाळी", "रात्री",
    "पाणी",
}

NEPALI_WORDS = {
    "म", "मलाई", "मेरो", "मेरी", "हामी",
    "हामीलाई", "तपाईं", "तपाईँ", "तिम्रो",
    "के", "किन", "कसरी", "कहाँ", "कहिले",
    "छ", "छन्", "हो", "होइन",
    "पानी", "खाना", "घर", "आमा", "बुबा",
    "छोरी", "छोरा", "परिवार", "सम्झना",
    "चाहिन्छ", "जानु", "आउनु",
}

BODO_WORDS = {
    "आं", "आंनि", "नों", "नांगौ",
    "माबा", "माइ", "बिदा",
    "नङा", "नाय", "जों",
    "थांखि", "जानाय",
}

BENGALI_WORDS = {
    "আমি", "আমার", "আমাকে",
    "আপনি", "আপনার",
    "তুমি", "তোমার", "তোমাকে",
    "এটা", "ওটা",
    "কি", "কেন", "কোথায়", "কোথায়", "কখন",
    "আছে", "নেই", "হ্যাঁ", "না",
    "এবং", "কিন্তু",
    "জল", "পানি", "খাবার",
    "মা", "বাবা", "মেয়ে", "মেয়ে",
    "ছেলে", "বাড়ি", "বাড়ি",
    "মনে", "স্মৃতি",
}

ASSAMESE_WORDS = {
    "মই", "মোৰ", "মোক",
    "আপুনি", "আপোনাৰ",
    "তুমি", "তোমাৰ", "তোমাক",
    "এইটো", "সেইটো",
    "কি", "কিয়", "কিয়",
    "ক'ত", "কেতিয়া", "কেতিয়া",
    "আছে", "নাই",
    "হয়", "হয়",
    "নহয়", "নহয়",
    "আৰু", "কিন্তু",
    "পানী", "খোৱা", "ঘৰ",
    "মা", "দেউতা",
    "ছোৱালী", "ল'ৰা",
}

URDU_WORDS = {
    "میں", "مجھے", "میرا", "میری", "میرے",
    "آپ", "آپکا", "آپکی", "آپکے",
    "تم", "تمہیں", "تمہارا",
    "کیا", "کیوں", "کیسے", "کب", "کہاں",
    "ہے", "ہیں", "تھا", "تھی", "تھے",
    "نہیں", "ہاں", "اور", "لیکن", "یا",
    "پانی", "کھانا", "گھر",
    "ماں", "والد", "بیٹی", "بیٹا", "یاد",
}

HINGLISH_WORDS = {
    "aap", "mujhe", "mujko", "mera", "meri", "mere",
    "hum", "hume", "humen", "hamara", "hamari",
    "tum", "tumhe", "tumhara", "tumhari",
    "aapka", "aapki", "aapke",
    "main", "mein", "mai",
    "hai", "hain", "hoon",
    "tha", "thi", "the",
    "nahi", "nahin", "haan",
    "kya", "kyun", "kyon",
    "kaise", "kaisa", "kaisi",
    "kab", "kahan",
    "yaad", "batao", "bataiye",
    "bolo", "boliye",
    "karo", "karna", "karen",
    "chalo", "ghar",
    "paani", "pani",
    "khana", "dawai", "dawa",
    "beti", "beta",
    "mummy", "mumma", "papa",
    "parivar", "subah", "shaam", "sham", "raat",
    "abhi", "phir",
    "accha", "achha",
    "theek", "thik",
    "chahiye",
    "chahta", "chahti", "chahte",
}

ENGLISH_STRONG_WORDS = {
    "the", "this", "that", "these", "those",
    "what", "where", "when", "why", "how",
    "please", "thank", "thanks",
    "hello", "morning", "evening",
    "medicine", "remember", "family",
    "daughter", "father", "mother",
    "water", "food", "home",
}

KHASI_WORDS = {
    "nga", "phi", "ngi",
    "kumno", "shaei", "hangno",
    "sngewbha", "jing",
    "pyrshah", "bam", "dih",
    "kmie", "kpa",
    "lait", "laitluid",
}

GARO_WORDS = {
    "anga", "nang", "maikai",
    "wat", "achik", "a·chik",
    "chik", "nok", "nokdang",
    "bwtang",
}

MIZO_WORDS = {
    "min", "eng", "hei", "chu",
    "khaw", "chhungkua",
    "damdawi", "thil",
    "zawng", "engmah",
    "lawm", "sawi",
}

TRIPURI_WORDS = {
    "nini", "nono", "nwng",
    "niniwi", "borok", "kok",
    "khum", "mani",
    "bwtang", "nwi",
    "buba", "bising",
}


LATIN_STRONG_MARKERS: Dict[str, set[str]] = {
    "kha": {
        "nga", "phi", "ngi", "kumno",
        "shaei", "hangno", "sngewbha",
        "pyrshah", "kmie", "kpa",
    },
    "grt": {
        "anga", "nang", "maikai",
        "achik", "a·chik", "nokdang",
        "bwtang",
    },
    "lus": {
        "min", "hei", "chu", "khaw",
        "chhungkua", "damdawi",
        "engmah", "lawm",
    },
    "trp": {
        "nini", "nono", "nwng",
        "niniwi", "borok",
        "bwtang", "bising",
    },
}


# ============================================================================
# SCRIPT RANGES
# ============================================================================

SCRIPT_RANGES: Dict[str, Tuple[int, int]] = {
    "Devanagari": (0x0900, 0x097F),
    "Bengali": (0x0980, 0x09FF),
    "Gurmukhi": (0x0A00, 0x0A7F),
    "Gujarati": (0x0A80, 0x0AFF),
    "Odia": (0x0B00, 0x0B7F),
    "Tamil": (0x0B80, 0x0BFF),
    "Telugu": (0x0C00, 0x0C7F),
    "Kannada": (0x0C80, 0x0CFF),
    "Malayalam": (0x0D00, 0x0D7F),
    "Meitei": (0xABC0, 0xABFF),
    "Arabic": (0x0600, 0x06FF),
    "ArabicExtended": (0x0750, 0x077F),
}


# ============================================================================
# TEXT HELPERS
# ============================================================================

def _safe_text(
    value: Any,
    max_length: int = MAX_DETECTION_TEXT_LENGTH,
) -> str:

    if value is None:
        return ""

    try:
        text = str(value)
    except Exception:
        return ""

    text = unicodedata.normalize("NFC", text)
    text = text.replace("\x00", " ")
    text = text.strip()

    if len(text) > max_length:
        text = text[:max_length]

    return text


def _extract_language_value(language: Any) -> Any:

    if isinstance(language, dict):

        for key in (
            "code",
            "language",
            "language_code",
            "preferred_language",
            "target_language",
        ):
            value = language.get(key)

            if value is not None and not isinstance(value, dict):
                return value

        return None

    return language


def _unicode_words(text: str) -> List[str]:

    if not text:
        return []

    text = unicodedata.normalize("NFC", str(text))

    words: List[str] = []
    current: List[str] = []

    for char in text:

        category = unicodedata.category(char)

        if char.isspace():

            if current:
                words.append("".join(current))
                current = []

            continue

        if category.startswith("P"):

            if char in {"'", "’"} and current:
                current.append(char)

            else:
                if current:
                    words.append("".join(current))
                    current = []

            continue

        if category.startswith("S"):

            if current:
                words.append("".join(current))
                current = []

            continue

        current.append(char)

    if current:
        words.append("".join(current))

    return words


def _normalized_word_set(text: str) -> set[str]:

    return {
        unicodedata.normalize("NFC", word).casefold()
        for word in _unicode_words(text)
    }


def _count_characters_in_range(
    text: str,
    start: int,
    end: int,
) -> int:

    return sum(
        start <= ord(char) <= end
        for char in text
    )


def _script_character_count(
    text: str,
    script: str,
) -> int:

    if not text:
        return 0

    if script == "Arabic":
        return (
            _count_characters_in_range(
                text,
                *SCRIPT_RANGES["Arabic"],
            )
            +
            _count_characters_in_range(
                text,
                *SCRIPT_RANGES["ArabicExtended"],
            )
        )

    if script == "Latin":
        return sum(
            1
            for char in text
            if "LATIN" in unicodedata.name(char, "")
        )

    if script not in SCRIPT_RANGES:
        return 0

    return _count_characters_in_range(
        text,
        *SCRIPT_RANGES[script],
    )


def _has_script(
    text: str,
    script: str,
) -> bool:

    return _script_character_count(
        text,
        script,
    ) > 0


def _count_latin_letters(text: str) -> int:

    return _script_character_count(
        text,
        "Latin",
    )


def _count_letters(text: str) -> int:

    return sum(
        1
        for char in text
        if char.isalpha()
    )


def _language_word_score(
    text: str,
    vocabulary: Iterable[str],
) -> float:

    words = _normalized_word_set(text)

    if not words:
        return 0.0

    vocab = {
        unicodedata.normalize("NFC", word).casefold()
        for word in vocabulary
    }

    matches = words.intersection(vocab)

    if not matches:
        return 0.0

    return min(
        len(matches) / max(len(words), 1),
        1.0,
    )


def _matching_words(
    text: str,
    vocabulary: Iterable[str],
) -> set[str]:

    words = _normalized_word_set(text)

    vocab = {
        unicodedata.normalize("NFC", word).casefold()
        for word in vocabulary
    }

    return words.intersection(vocab)


def _latin_hinglish_score(text: str) -> float:

    words = _normalized_word_set(text)

    if not words:
        return 0.0

    matches = words.intersection(
        {
            word.casefold()
            for word in HINGLISH_WORDS
        }
    )

    if not matches:
        return 0.0

    score = len(matches) / max(len(words), 1)

    if len(matches) >= 2:
        score += 0.25

    if len(matches) >= 4:
        score += 0.20

    return min(score, 1.0)


# ============================================================================
# DETECTION RESULT
# ============================================================================

def _detection_result(
    code: str,
    confidence: float,
    method: str,
) -> Dict[str, Any]:

    if code not in SUPPORTED_LANGUAGES:
        code = DEFAULT_LANGUAGE

    metadata = SUPPORTED_LANGUAGES[code]

    confidence = max(
        0.0,
        min(float(confidence), 1.0),
    )

    return {
        "success": True,
        "code": code,
        "name": metadata["name"],
        "native_name": metadata["native_name"],
        "locale": metadata["locale"],
        "speech_locale": metadata["speech_locale"],
        "script": metadata["script"],
        "base_language": metadata["base_language"],
        "confidence": round(confidence, 3),
        "method": method,
        "local_detection": True,
        "is_hinglish": code == "hinglish",
    }


# ============================================================================
# DEVANAGARI DETECTION
# ============================================================================

def _detect_devanagari_language(
    text: str,
) -> Tuple[str, float, str]:

    words = _normalized_word_set(text)

    if not words:
        return (
            "hi",
            0.40,
            "devanagari_script",
        )

    hindi_matches = _matching_words(
        text,
        HINDI_WORDS,
    )

    marathi_matches = _matching_words(
        text,
        MARATHI_WORDS,
    )

    nepali_matches = _matching_words(
        text,
        NEPALI_WORDS,
    )

    bodo_matches = _matching_words(
        text,
        BODO_WORDS,
    )

    # ------------------------------------------------------------------
    # Strong language-specific words
    # ------------------------------------------------------------------

    hindi_unique = {
        "मैं", "मुझे", "मेरा", "मेरी", "मेरे",
        "आप", "आपका", "आपकी", "आपके",
        "तुम", "तुम्हें",
        "हैं", "हूँ", "नहीं",
        "क्योंकि", "याद",
        "चाहता", "चाहती", "चाहते",
    }

    marathi_unique = {
        "मला", "माझा", "माझी", "माझे",
        "माझ्या", "माझं",
        "तुला", "तुम्हाला",
        "आहे", "आहेत",
        "आणि", "पण",
        "म्हणून", "जेवण",
        "आई", "वडील",
        "आठवण", "करा",
        "कुठे", "पाहिजे",
        "नको",
    }

    nepali_unique = {
        "मलाई", "मेरो", "मेरी",
        "हामी", "हामीलाई",
        "तपाईं", "तपाईँ",
        "तिम्रो",
        "छ", "छन्",
        "होइन",
        "चाहिन्छ",
        "सम्झना",
    }

    bodo_unique = {
        "आं", "आंनि", "नों",
        "नांगौ", "जों",
        "थांखि",
    }

    hindi_specific = len(
        words.intersection(hindi_unique)
    )

    marathi_specific = len(
        words.intersection(marathi_unique)
    )

    nepali_specific = len(
        words.intersection(nepali_unique)
    )

    bodo_specific = len(
        words.intersection(bodo_unique)
    )

    scores = {
        "hi": (
            len(hindi_matches) * 1.0
            + hindi_specific * 2.5
        ),
        "mr": (
            len(marathi_matches) * 1.0
            + marathi_specific * 2.8
        ),
        "ne": (
            len(nepali_matches) * 1.0
            + nepali_specific * 2.8
        ),
        "brx": (
            len(bodo_matches) * 1.0
            + bodo_specific * 3.0
        ),
    }

    best_code = max(
        scores,
        key=scores.get,
    )

    best_score = scores[best_code]

    # ------------------------------------------------------------------
    # Strong lexical evidence
    # ------------------------------------------------------------------

    if best_score > 0:

        if best_code == "mr":
            confidence = min(
                0.78 + marathi_specific * 0.06,
                0.98,
            )

            return (
                "mr",
                confidence,
                "lexical_shared_script",
            )

        if best_code == "ne":
            confidence = min(
                0.78 + nepali_specific * 0.06,
                0.97,
            )

            return (
                "ne",
                confidence,
                "lexical_shared_script",
            )

        if best_code == "brx":
            confidence = min(
                0.78 + bodo_specific * 0.06,
                0.97,
            )

            return (
                "brx",
                confidence,
                "lexical_shared_script",
            )

        if best_code == "hi":
            confidence = min(
                0.78 + hindi_specific * 0.05,
                0.98,
            )

            return (
                "hi",
                confidence,
                "lexical_shared_script",
            )

    # Generic Devanagari fallback.
    #
    # IMPORTANT:
    # Never return English simply because a Devanagari sentence did not
    # match the vocabulary.
    return (
        "hi",
        0.60,
        "devanagari_script",
    )


# ============================================================================
# BENGALI / ASSAMESE DETECTION
# ============================================================================

def _detect_bengali_script_language(
    text: str,
) -> Tuple[str, float, str]:

    words = _normalized_word_set(text)

    bengali_matches = _matching_words(
        text,
        BENGALI_WORDS,
    )

    assamese_matches = _matching_words(
        text,
        ASSAMESE_WORDS,
    )

    assamese_markers = {
        "মই",
        "মোৰ",
        "মোক",
        "আপুনি",
        "আপোনাৰ",
        "আৰু",
        "পানী",
        "ঘৰ",
        "কিয়",
        "কিয়",
        "ক'ত",
        "কেতিয়া",
        "কেতিয়া",
        "হয়",
        "হয়",
        "নাই",
    }

    bengali_markers = {
        "আমি",
        "আমার",
        "আমাকে",
        "আপনি",
        "আপনার",
        "তোমার",
        "কোথায়",
        "কোথায়",
        "কখন",
        "কেন",
        "আছে",
        "নেই",
        "হ্যাঁ",
        "না",
    }

    assamese_specific = len(
        words.intersection(
            assamese_markers
        )
    )

    bengali_specific = len(
        words.intersection(
            bengali_markers
        )
    )

    assamese_score = (
        len(assamese_matches)
        + assamese_specific * 2.5
    )

    bengali_score = (
        len(bengali_matches)
        + bengali_specific * 2.5
    )

    if assamese_score > bengali_score:

        confidence = min(
            0.78
            + assamese_specific * 0.06,
            0.97,
        )

        return (
            "as",
            confidence,
            "lexical_shared_script",
        )

    if bengali_score > 0:

        confidence = min(
            0.78
            + bengali_specific * 0.06,
            0.97,
        )

        return (
            "bn",
            confidence,
            "lexical_shared_script",
        )

    # Bengali-family script fallback.
    return (
        "bn",
        0.58,
        "bengali_script",
    )


# ============================================================================
# MEITEI
# ============================================================================

def _detect_meitei_language(
    text: str,
) -> Tuple[str, float, str]:

    if _has_script(text, "Meitei"):
        return (
            "mni",
            0.99,
            "meitei_mayek_script",
        )

    meitei_words = {
        "মেইতেই",
        "ইমা",
        "ইপা",
        "নুপী",
        "নুপা",
        "ꯑꯩ",
        "ꯑꯩꯒꯤ",
        "ꯅꯥ",
        "ꯑꯗꯨ",
        "ꯃꯥ",
        "ꯄꯥꯄꯥ",
    }

    matches = _matching_words(
        text,
        meitei_words,
    )

    if matches:
        return (
            "mni",
            min(
                0.82 + len(matches) * 0.05,
                0.97,
            ),
            "lexical_meitei",
        )

    return (
        "bn",
        0.52,
        "shared_bengali_script",
    )


# ============================================================================
# ARABIC / URDU
# ============================================================================

def _detect_arabic_script_language(
    text: str,
) -> Tuple[str, float, str]:

    urdu_matches = _matching_words(
        text,
        URDU_WORDS,
    )

    urdu_specific_chars = set(
        "ٹ ڈ ڑ ں ھ ہ ی ے ژ چ گ پ"
    )

    specific_chars = sum(
        1
        for char in text
        if char in urdu_specific_chars
    )

    if urdu_matches or specific_chars:

        confidence = min(
            0.78
            + min(len(urdu_matches), 4) * 0.04
            + min(specific_chars, 4) * 0.03,
            0.98,
        )

        return (
            "ur",
            confidence,
            "urdu_script_lexical",
        )

    return (
        "ur",
        0.52,
        "arabic_script_fallback",
    )


# ============================================================================
# LATIN DETECTION
# ============================================================================

def _detect_latin_language(
    text: str,
) -> Optional[Tuple[str, float, str]]:

    words = _normalized_word_set(text)

    if not words:
        return None

    # Hinglish
    hinglish_score = _latin_hinglish_score(
        text
    )

    if hinglish_score >= 0.25:

        confidence = min(
            0.80 + hinglish_score * 0.20,
            0.98,
        )

        return (
            "hinglish",
            confidence,
            "lexical_hinglish",
        )

    # Northeast languages
    northeast_configs = {
        "kha": KHASI_WORDS,
        "grt": GARO_WORDS,
        "lus": MIZO_WORDS,
        "trp": TRIPURI_WORDS,
    }

    northeast_scores: Dict[str, float] = {}

    for code, vocabulary in northeast_configs.items():

        matches = _matching_words(
            text,
            vocabulary,
        )

        strong_matches = _matching_words(
            text,
            LATIN_STRONG_MARKERS[code],
        )

        if strong_matches:

            score = (
                len(strong_matches) * 0.35
                + len(matches) * 0.12
            )

            northeast_scores[code] = min(
                score,
                1.0,
            )

    if northeast_scores:

        best_code = max(
            northeast_scores,
            key=northeast_scores.get,
        )

        best_score = northeast_scores[
            best_code
        ]

        strong_matches = _matching_words(
            text,
            LATIN_STRONG_MARKERS[best_code],
        )

        if (
            len(strong_matches) >= 2
            or best_score >= 0.55
        ):

            confidence = min(
                0.68 + best_score * 0.30,
                0.95,
            )

            return (
                best_code,
                confidence,
                "lexical_latin_northeast",
            )

    # English
    english_matches = words.intersection(
        {
            word.casefold()
            for word in ENGLISH_STRONG_WORDS
        }
    )

    if english_matches:

        english_score = (
            len(english_matches)
            / max(len(words), 1)
        )

        confidence = min(
            0.62 + english_score * 0.35,
            0.94,
        )

        return (
            "en",
            confidence,
            "lexical_english",
        )

    return None


# ============================================================================
# NORMALIZATION
# ============================================================================

def normalize_language(
    language: Any,
) -> str:

    raw_value = _extract_language_value(
        language
    )

    if raw_value is None:
        return DEFAULT_LANGUAGE

    try:
        value = str(raw_value).strip()
    except Exception:
        return DEFAULT_LANGUAGE

    if not value:
        return DEFAULT_LANGUAGE

    normalized = unicodedata.normalize(
        "NFC",
        value,
    ).casefold()

    if normalized in SUPPORTED_LANGUAGES:
        return normalized

    if normalized in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[
            normalized
        ]

    normalized_dash = normalized.replace(
        "_",
        "-",
    )

    if normalized_dash in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[
            normalized_dash
        ]

    prefix = normalized_dash.split(
        "-",
        1,
    )[0]

    if prefix in SUPPORTED_LANGUAGES:
        return prefix

    if prefix in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[
            prefix
        ]

    return DEFAULT_LANGUAGE


def is_supported(
    language: Any,
) -> bool:

    raw_value = _extract_language_value(
        language
    )

    if raw_value is None:
        return False

    try:
        value = unicodedata.normalize(
            "NFC",
            str(raw_value).strip().casefold(),
        )
    except Exception:
        return False

    if not value:
        return False

    if value in SUPPORTED_LANGUAGES:
        return True

    if value in LANGUAGE_ALIASES:
        return True

    value = value.replace(
        "_",
        "-",
    )

    if value in SUPPORTED_LANGUAGES:
        return True

    if value in LANGUAGE_ALIASES:
        return True

    prefix = value.split(
        "-",
        1,
    )[0]

    return (
        prefix in SUPPORTED_LANGUAGES
        or prefix in LANGUAGE_ALIASES
    )


def get_language(
    language: Any = DEFAULT_LANGUAGE,
) -> Dict[str, str]:

    code = normalize_language(
        language
    )

    metadata = dict(
        SUPPORTED_LANGUAGES[code]
    )

    metadata["code"] = code

    return metadata


def language_code(
    language: Any,
) -> str:

    return normalize_language(
        language
    )


def language_name(
    language: Any,
) -> str:

    return get_language(
        language
    )["name"]


def speech_locale(
    language: Any,
) -> str:

    return get_language(
        language
    )["speech_locale"]


def locale(
    language: Any,
) -> str:

    return get_language(
        language
    )["locale"]


def base_language(
    language: Any,
) -> str:

    return get_language(
        language
    )["base_language"]


def is_hinglish(
    language: Any,
) -> bool:

    return (
        normalize_language(language)
        == "hinglish"
    )


def list_languages() -> List[Dict[str, str]]:

    result = []

    for code, metadata in SUPPORTED_LANGUAGES.items():

        item = dict(metadata)
        item["code"] = code

        result.append(item)

    return result


def get_supported_language_codes() -> List[str]:

    return list(
        SUPPORTED_LANGUAGES.keys()
    )


# ============================================================================
# PREFERRED LANGUAGE COMPATIBILITY
# ============================================================================

def _preferred_language_compatible(
    text: str,
    preferred_code: str,
) -> bool:

    if not text:
        return True

    metadata = SUPPORTED_LANGUAGES.get(
        preferred_code
    )

    if not metadata:
        return False

    script = metadata["script"]

    if script == "Latin":
        return (
            _has_script(text, "Latin")
            or _count_letters(text) == 0
        )

    if preferred_code == "mni":
        return (
            _has_script(text, "Meitei")
            or _has_script(text, "Bengali")
        )

    if script == "Meitei/Bengali":
        return (
            _has_script(text, "Meitei")
            or _has_script(text, "Bengali")
        )

    return _has_script(
        text,
        script,
    )


# ============================================================================
# MAIN LANGUAGE DETECTION
# ============================================================================

def detect_language(
    text: Any,
    preferred_language: Any = None,
) -> Dict[str, Any]:
    """
    Detect the most likely supported language.

    IMPORTANT:
        This function NEVER calls Gemini.
        Detection is completely local.
    """

    text = _safe_text(text)

    if not text:

        return _detection_result(
            DEFAULT_LANGUAGE,
            0.0,
            "empty_input",
        )

    # ========================================================================
    # Explicit preferred language
    # ========================================================================

    preferred_raw = _extract_language_value(
        preferred_language
    )

    preferred_code: Optional[str] = None

    if (
        preferred_raw is not None
        and is_supported(preferred_raw)
    ):

        preferred_code = normalize_language(
            preferred_raw
        )

    if preferred_code:

        compatible = _preferred_language_compatible(
            text,
            preferred_code,
        )

        if compatible:

            # English preference should not override obvious Hinglish.
            if preferred_code == "en":

                hinglish_score = _latin_hinglish_score(
                    text
                )

                if hinglish_score < 0.25:

                    return _detection_result(
                        "en",
                        0.90,
                        "explicit_preference",
                    )

            else:

                return _detection_result(
                    preferred_code,
                    0.92,
                    "explicit_preference",
                )

    # ========================================================================
    # SCRIPT-FIRST DETECTION
    #
    # This section is deliberately before Latin/unknown fallback.
    # ========================================================================

    # Meitei Mayek
    if _has_script(text, "Meitei"):

        code, confidence, method = (
            _detect_meitei_language(text)
        )

        return _detection_result(
            code,
            confidence,
            method,
        )

    # Gurmukhi -> Punjabi
    if _has_script(text, "Gurmukhi"):

        return _detection_result(
            "pa",
            0.98,
            "gurmukhi_script",
        )

    # Gujarati
    if _has_script(text, "Gujarati"):

        return _detection_result(
            "gu",
            0.98,
            "gujarati_script",
        )

    # Odia
    if _has_script(text, "Odia"):

        return _detection_result(
            "or",
            0.98,
            "odia_script",
        )

    # Tamil
    if _has_script(text, "Tamil"):

        return _detection_result(
            "ta",
            0.98,
            "tamil_script",
        )

    # Telugu
    if _has_script(text, "Telugu"):

        return _detection_result(
            "te",
            0.98,
            "telugu_script",
        )

    # Kannada
    if _has_script(text, "Kannada"):

        return _detection_result(
            "kn",
            0.98,
            "kannada_script",
        )

    # Malayalam
    if _has_script(text, "Malayalam"):

        return _detection_result(
            "ml",
            0.98,
            "malayalam_script",
        )

    # Devanagari -> Hindi / Marathi / Nepali / Bodo
    if _has_script(text, "Devanagari"):

        code, confidence, method = (
            _detect_devanagari_language(text)
        )

        return _detection_result(
            code,
            confidence,
            method,
        )

    # Bengali-family script -> Bengali / Assamese / Manipuri
    if _has_script(text, "Bengali"):

        meitei_result = _detect_meitei_language(
            text
        )

        if meitei_result[0] == "mni":

            code, confidence, method = (
                meitei_result
            )

            return _detection_result(
                code,
                confidence,
                method,
            )

        code, confidence, method = (
            _detect_bengali_script_language(
                text
            )
        )

        return _detection_result(
            code,
            confidence,
            method,
        )

    # Arabic script -> Urdu
    if _has_script(text, "Arabic"):

        code, confidence, method = (
            _detect_arabic_script_language(
                text
            )
        )

        return _detection_result(
            code,
            confidence,
            method,
        )

    # ========================================================================
    # LATIN
    # ========================================================================

    latin_count = _count_latin_letters(
        text
    )

    letter_count = _count_letters(
        text
    )

    if latin_count > 0 and letter_count > 0:

        latin_result = _detect_latin_language(
            text
        )

        if latin_result is not None:

            code, confidence, method = (
                latin_result
            )

            return _detection_result(
                code,
                confidence,
                method,
            )

        return _detection_result(
            "en",
            0.55,
            "latin_default",
        )

    # ========================================================================
    # UNKNOWN
    # ========================================================================

    return _detection_result(
        DEFAULT_LANGUAGE,
        0.25,
        "unknown_script",
    )


# ============================================================================
# COMPANION PREPARATION
# ============================================================================

def prepare_for_companion(
    text: Any,
    preferred_language: Any = None,
) -> Dict[str, Any]:

    text = _safe_text(text)

    detected = detect_language(
        text
    )

    preferred_raw = _extract_language_value(
        preferred_language
    )

    preferred_code: Optional[str] = None

    if (
        preferred_raw is not None
        and is_supported(preferred_raw)
    ):

        preferred_code = normalize_language(
            preferred_raw
        )

    if preferred_code:
        interaction_code = preferred_code
    else:
        interaction_code = detected["code"]

    metadata = get_language(
        interaction_code
    )

    return {
        "text": text,

        "detected_language": detected,

        "language": interaction_code,
        "language_code": interaction_code,

        "language_name": metadata["name"],
        "native_language_name": metadata[
            "native_name"
        ],

        "base_language": metadata[
            "base_language"
        ],

        "locale": metadata[
            "locale"
        ],

        "speech_locale": metadata[
            "speech_locale"
        ],

        "preferred_language": (
            preferred_code
            or interaction_code
        ),

        "preferred_language_name": language_name(
            preferred_code
            or interaction_code
        ),

        "is_hinglish": (
            interaction_code == "hinglish"
        ),

        "interaction_language": interaction_code,

        "script": metadata["script"],
    }


# ============================================================================
# SAFE LOCAL TRANSLATION FALLBACK
# ============================================================================

def _local_translation_fallback(
    text: str,
    source_language: Any,
    target_language: Any,
) -> str:

    source = normalize_language(
        source_language
    )

    target = normalize_language(
        target_language
    )

    if source == target:
        return text

    # Never invent a translation.
    return text


# ============================================================================
# GEMINI TRANSLATION
# ============================================================================

def _extract_gemini_text(
    result: Any,
) -> Optional[str]:

    if result is None:
        return None

    if isinstance(result, str):

        text = result.strip()

        return text or None

    if isinstance(result, dict):

        for key in (
            "text",
            "response",
            "message",
            "content",
            "output",
        ):

            value = result.get(key)

            if isinstance(value, str):

                value = value.strip()

                if value:
                    return value

    for attribute in (
        "text",
        "response",
        "message",
        "content",
        "output",
    ):

        try:
            value = getattr(
                result,
                attribute,
                None,
            )
        except Exception:
            value = None

        if isinstance(value, str):

            value = value.strip()

            if value:
                return value

    return None


def _try_gemini_translation(
    text: str,
    source_language: Any,
    target_language: Any,
) -> Optional[str]:

    try:

        from conversation.gemini_client import (
            generate_gemini_response,
        )

    except Exception:

        return None

    source_metadata = get_language(
        source_language
    )

    target_metadata = get_language(
        target_language
    )

    target_code = target_metadata["code"]

    if target_code == "hinglish":

        target_instruction = (
            "Use natural Romanized Hindi/Hinglish. "
            "Use Latin/Roman script, not Devanagari."
        )

    elif target_code == "hi":

        target_instruction = (
            "Use simple natural Hindi in Devanagari."
        )

    else:

        target_instruction = (
            "Use natural everyday language in the "
            "requested target language."
        )

    prompt = f"""
Translate the following text for DementiaCareAI.

Source language:
{source_metadata["name"]}

Target language:
{target_metadata["name"]}

Target code:
{target_code}

Requirements:
- Preserve the meaning.
- Use natural everyday language.
- Keep sentences short.
- Be warm and respectful.
- Do not add facts.
- Do not explain the translation.
- Do not mention AI.
- Return ONLY the translated text.
- {target_instruction}

Text:
{text}
""".strip()

    try:

        result = generate_gemini_response(
            message=text,
            context=prompt,
        )

    except Exception:

        return None

    translated = _extract_gemini_text(
        result
    )

    if not translated:
        return None

    failure_markers = (
        "resource_exhausted",
        "resource exhausted",
        "quota exceeded",
        "quota",
        "rate limit",
        "api error",
        "service unavailable",
        "gemini unavailable",
        "internal server error",
        "permission denied",
    )

    lowered = translated.casefold()

    if any(
        marker in lowered
        for marker in failure_markers
    ):
        return None

    return translated


# ============================================================================
# TRANSLATION API
# ============================================================================

def translate_text(
    text: Any,
    target_language: Any,
    source_language: Any = "auto",
) -> str:

    text = _safe_text(
        text,
        max_length=MAX_TRANSLATION_TEXT_LENGTH,
    )

    if not text:
        return ""

    target = normalize_language(
        target_language
    )

    source_raw = _extract_language_value(
        source_language
    )

    if source_raw is None:
        source_raw = "auto"

    try:
        source_value = str(
            source_raw
        ).strip().casefold()
    except Exception:
        source_value = "auto"

    if source_value in {
        "",
        "auto",
        "automatic",
        "detect",
    }:

        source = detect_language(
            text
        )["code"]

    else:

        source = normalize_language(
            source_raw
        )

    if source == target:
        return text

    translated = _try_gemini_translation(
        text,
        source,
        target,
    )

    if translated:
        return translated

    return _local_translation_fallback(
        text,
        source,
        target,
    )


# ============================================================================
# RESPONSE PREPARATION
# ============================================================================

def prepare_response(
    text: Any,
    target_language: Any = None,
    source_language: Any = "auto",
) -> Dict[str, Any]:

    text = _safe_text(
        text,
        max_length=MAX_TRANSLATION_TEXT_LENGTH,
    )

    if not text:

        detected = _detection_result(
            DEFAULT_LANGUAGE,
            0.0,
            "empty_input",
        )

        target = normalize_language(
            target_language
            if target_language is not None
            else DEFAULT_LANGUAGE
        )

        metadata = get_language(
            target
        )

        return {
            "text": "",
            "translated": False,
            "source_language": detected["code"],
            "target_language": target,
            "source_language_name": detected["name"],
            "target_language_name": metadata["name"],
            "speech_locale": metadata["speech_locale"],
            "locale": metadata["locale"],
            "base_language": metadata["base_language"],
            "is_hinglish": target == "hinglish",
            "detection": detected,
        }

    source_raw = _extract_language_value(
        source_language
    )

    if source_raw is None:
        source_raw = "auto"

    try:
        source_value = str(
            source_raw
        ).strip().casefold()
    except Exception:
        source_value = "auto"

    if source_value in {
        "",
        "auto",
        "automatic",
        "detect",
    }:

        detected = detect_language(
            text
        )

        source = detected["code"]

    else:

        source = normalize_language(
            source_raw
        )

        detected = _detection_result(
            source,
            1.0,
            "explicit_source_language",
        )

    target = (
        normalize_language(target_language)
        if target_language is not None
        else source
    )

    response_text = text
    translated = False

    if target != source:

        response_text = translate_text(
            text,
            target_language=target,
            source_language=source,
        )

        translated = (
            response_text != text
        )

    metadata = get_language(
        target
    )

    return {
        "text": response_text,
        "translated": translated,

        "source_language": source,
        "target_language": target,

        "source_language_name": language_name(
            source
        ),

        "target_language_name": metadata[
            "name"
        ],

        "speech_locale": metadata[
            "speech_locale"
        ],

        "locale": metadata[
            "locale"
        ],

        "base_language": metadata[
            "base_language"
        ],

        "is_hinglish": (
            target == "hinglish"
        ),

        "detection": detected,
    }


# ============================================================================
# STATUS
# ============================================================================

def get_language_status() -> Dict[str, Any]:

    return {
        "available": True,

        "default_language": DEFAULT_LANGUAGE,

        "default_locale": locale(
            DEFAULT_LANGUAGE
        ),

        "default_speech_locale": speech_locale(
            DEFAULT_LANGUAGE
        ),

        "hinglish": True,

        "script_detection": True,

        "shared_script_detection": True,

        "northeast_indian_languages": True,

        "translation_provider": (
            "gemini_with_safe_local_fallback"
        ),

        "translation_fallback_safe": True,

        "detection_network_free": True,

        "language_count": len(
            SUPPORTED_LANGUAGES
        ),

        "expected_language_count": (
            SUPPORTED_LANGUAGE_COUNT
        ),

        "language_count_valid": (
            len(SUPPORTED_LANGUAGES)
            == SUPPORTED_LANGUAGE_COUNT
        ),

        "supported_languages": list_languages(),

        "supported_language_codes": (
            get_supported_language_codes()
        ),
    }


# ============================================================================
# CONVENIENCE HELPERS
# ============================================================================

def detect_language_code(
    text: Any,
) -> str:

    return detect_language(
        text
    )["code"]


def detect_language_name(
    text: Any,
) -> str:

    return detect_language(
        text
    )["name"]


def get_language_metadata(
    language: Any,
) -> Dict[str, str]:

    return get_language(
        language
    )


# ============================================================================
# SELF TEST
# ============================================================================

if __name__ == "__main__":

    test_cases = [
        # Hindi
        "मुझे आज बहुत अच्छा लग रहा है",
        "आप मुझे याद हैं?",
        "मैं घर जाना चाहता हूँ",

        # Hinglish
        "Aap mujhe yaad hain?",
        "Mujhe ghar jaana hai",

        # Marathi
        "मला पाणी पाहिजे",
        "मला जेवण पाहिजे",
        "माझी मुलगी कुठे आहे?",

        # Nepali
        "मलाई पानी चाहिन्छ",

        # Assamese
        "মই পানী বিচাৰোঁ",

        # Bengali
        "আপনি কেমন আছেন",
        "আমি পানি চাই",

        # Urdu
        "مجھے پانی چاہیے",

        # Gujarati
        "મારે પાણી જોઈએ",

        # Punjabi
        "ਮੈਨੂੰ ਪਾਣੀ ਚਾਹੀਦਾ ਹੈ",

        # Tamil
        "எனக்கு தண்ணீர் வேண்டும்",

        # Telugu
        "నాకు నీళ్లు కావాలి",

        # Kannada
        "ನನಗೆ ನೀರು ಬೇಕು",

        # Malayalam
        "എനിക്ക് വെള്ളം വേണം",

        # Odia
        "ମୋତେ ପାଣି ଦରକାର",

        # English
        "I need some water",
        "Hello, how are you?",

        # Khasi
        "Nga sngewbha dih um",
    ]

    print("=" * 80)
    print("DementiaCareAI Language Engine")
    print("=" * 80)

    print()
    print(
        "Supported language count:",
        len(SUPPORTED_LANGUAGES),
    )

    print(
        "Expected language count:",
        SUPPORTED_LANGUAGE_COUNT,
    )

    print(
        "Language count valid:",
        len(SUPPORTED_LANGUAGES)
        == SUPPORTED_LANGUAGE_COUNT,
    )

    print()

    for text in test_cases:

        result = detect_language(
            text
        )

        print(
            f"{text}"
        )

        print(
            f"  -> {result['name']} "
            f"({result['code']})"
        )

        print(
            f"  confidence={result['confidence']}"
        )

        print(
            f"  method={result['method']}"
        )

        print(
            f"  local_detection={result['local_detection']}"
        )

        print(
            f"  locale={result['locale']}"
        )

        print(
            f"  speech={result['speech_locale']}"
        )

        print()

    print("=" * 80)