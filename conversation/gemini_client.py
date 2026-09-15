"""
DementiaCareAI Gemini Conversation Layer
=========================================

Responsibilities
----------------
- Detect the language of the incoming user message.
- Generate natural responses in the same language.
- Preserve DementiaCareAI as the source of truth.
- Use Gemini for natural-language generation.
- Provide a safe multilingual local fallback when Gemini is unavailable.
- Keep responses suitable for dementia-friendly voice interaction.
- Never diagnose or invent patient facts.

This module is intentionally independent from the UI.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types
from ai.gemini_service import get_client as _canonical_gemini_client, model_name as _canonical_model_name

try:
    from language import (
        detect_language,
        get_language,
        normalize_language,
    )
except Exception:
    detect_language = None
    get_language = None
    normalize_language = None


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Keep the known-working project model.
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    _canonical_model_name(),
)

# Do not repeatedly hit a known-exhausted Gemini quota.
QUOTA_COOLDOWN_SECONDS = 60 * 60

_last_quota_error_at = 0.0

_client = None


# ============================================================
# LANGUAGE CONFIGURATION
# ============================================================

LANGUAGE_FALLBACKS: dict[str, dict[str, str]] = {
    "en": {
        "unknown": (
            "I don't have enough information to answer that yet."
        ),
        "confusion": (
            "That's okay. We can take it slowly. "
            "I don't have enough information to answer that yet."
        ),
        "frustration": (
            "Let's take it slowly. "
            "I don't have enough information to answer that yet."
        ),
        "remember": "I remember {name}.",
        "relationship": "{name} is your {relationship}.",
        "description": "{name}. {description}.",
    },

    "hi": {
        "unknown": (
            "यह ठीक है। हम धीरे-धीरे बात कर सकते हैं। "
            "मेरे पास अभी इसका जवाब देने के लिए पर्याप्त जानकारी नहीं है।"
        ),
        "confusion": (
            "कोई बात नहीं। हम धीरे-धीरे बात करते हैं। "
            "मेरे पास अभी इसका जवाब देने के लिए पर्याप्त जानकारी नहीं है।"
        ),
        "frustration": (
            "हम धीरे-धीरे करते हैं। "
            "मेरे पास अभी इसका जवाब देने के लिए पर्याप्त जानकारी नहीं है।"
        ),
        "remember": "मुझे {name} याद हैं।",
        "relationship": "{name} आपके {relationship} हैं।",
        "description": "{name}। {description}।",
    },

    "hinglish": {
        "unknown": (
            "Koi baat nahi. Hum dheere dheere baat kar sakte hain. "
            "Mere paas abhi iska jawab dene ke liye enough information nahi hai."
        ),
        "confusion": (
            "Koi baat nahi. Hum aaram se, dheere dheere baat karte hain."
        ),
        "frustration": (
            "Let's take it slowly. Hum aaram se baat karte hain."
        ),
        "remember": "Mujhe {name} yaad hain.",
        "relationship": "{name} aapke {relationship} hain.",
        "description": "{name}. {description}.",
    },

    "mr": {
        "unknown": (
            "काही हरकत नाही. आपण हळूहळू बोलूया. "
            "माझ्याकडे आत्ता याचे उत्तर देण्यासाठी पुरेशी माहिती नाही."
        ),
        "confusion": (
            "काही हरकत नाही. आपण हळूहळू बोलूया."
        ),
        "frustration": (
            "आपण हळूहळू करूया. काळजी करू नका."
        ),
        "remember": "मला {name} आठवतात.",
        "relationship": "{name} तुमचे {relationship} आहेत.",
        "description": "{name}. {description}.",
    },

    "bn": {
        "unknown": (
            "কোনো সমস্যা নেই। আমরা ধীরে ধীরে কথা বলতে পারি। "
            "এখন এর উত্তর দেওয়ার মতো যথেষ্ট তথ্য আমার কাছে নেই।"
        ),
        "confusion": (
            "কোনো সমস্যা নেই। আমরা ধীরে ধীরে কথা বলি।"
        ),
        "frustration": (
            "আমরা ধীরে ধীরে করি। চিন্তা করবেন না।"
        ),
        "remember": "আমার {name}-এর কথা মনে আছে।",
        "relationship": "{name} আপনার {relationship}।",
        "description": "{name}। {description}।",
    },

    "ta": {
        "unknown": (
            "பரவாயில்லை. நாம் மெதுவாகப் பேசலாம். "
            "இதற்குப் பதிலளிக்க என்னிடம் இப்போது போதுமான தகவல் இல்லை."
        ),
        "confusion": (
            "பரவாயில்லை. நாம் மெதுவாகப் பேசலாம்."
        ),
        "frustration": (
            "நாம் மெதுவாகச் செய்வோம். கவலைப்பட வேண்டாம்."
        ),
        "remember": "{name} எனக்கு நினைவில் இருக்கிறார்.",
        "relationship": "{name} உங்கள் {relationship}.",
        "description": "{name}. {description}.",
    },

    "te": {
        "unknown": (
            "పర్వాలేదు. మనం నెమ్మదిగా మాట్లాడుకుందాం. "
            "దానికి సమాధానం చెప్పడానికి నా దగ్గర ఇంకా తగినంత సమాచారం లేదు."
        ),
        "confusion": (
            "పర్వాలేదు. మనం నెమ్మదిగా మాట్లాడుకుందాం."
        ),
        "frustration": (
            "మనం నెమ్మదిగా చేద్దాం. ఆందోళన పడకండి."
        ),
        "remember": "నాకు {name} గుర్తున్నారు.",
        "relationship": "{name} మీ {relationship}.",
        "description": "{name}. {description}.",
    },

    "gu": {
        "unknown": (
            "કોઈ વાત નથી. આપણે ધીમે ધીમે વાત કરી શકીએ. "
            "મારી પાસે અત્યારે તેનો જવાબ આપવા માટે પૂરતી માહિતી નથી."
        ),
        "confusion": (
            "કોઈ વાત નથી. આપણે ધીમે ધીમે વાત કરીએ."
        ),
        "frustration": (
            "ચાલો ધીમે ધીમે કરીએ. ચિંતા ન કરો."
        ),
        "remember": "મને {name} યાદ છે.",
        "relationship": "{name} તમારા {relationship} છે.",
        "description": "{name}. {description}.",
    },

    "pa": {
        "unknown": (
            "ਕੋਈ ਗੱਲ ਨਹੀਂ। ਅਸੀਂ ਹੌਲੀ-ਹੌਲੀ ਗੱਲ ਕਰ ਸਕਦੇ ਹਾਂ। "
            "ਮੇਰੇ ਕੋਲ ਇਸ ਵੇਲੇ ਇਸ ਦਾ ਜਵਾਬ ਦੇਣ ਲਈ ਕਾਫ਼ੀ ਜਾਣਕਾਰੀ ਨਹੀਂ ਹੈ।"
        ),
        "confusion": (
            "ਕੋਈ ਗੱਲ ਨਹੀਂ। ਅਸੀਂ ਹੌਲੀ-ਹੌਲੀ ਗੱਲ ਕਰਦੇ ਹਾਂ।"
        ),
        "frustration": (
            "ਆਓ ਹੌਲੀ-ਹੌਲੀ ਕਰੀਏ। ਚਿੰਤਾ ਨਾ ਕਰੋ।"
        ),
        "remember": "ਮੈਨੂੰ {name} ਯਾਦ ਹਨ।",
        "relationship": "{name} ਤੁਹਾਡੇ {relationship} ਹਨ।",
        "description": "{name}। {description}।",
    },

    "ur": {
        "unknown": (
            "کوئی بات نہیں۔ ہم آہستہ آہستہ بات کر سکتے ہیں۔ "
            "میرے پاس ابھی اس کا جواب دینے کے لیے کافی معلومات نہیں ہیں۔"
        ),
        "confusion": (
            "کوئی بات نہیں۔ ہم آہستہ آہستہ بات کرتے ہیں۔"
        ),
        "frustration": (
            "ہم آہستہ آہستہ کرتے ہیں۔ فکر نہ کریں۔"
        ),
        "remember": "مجھے {name} یاد ہیں۔",
        "relationship": "{name} آپ کے {relationship} ہیں۔",
        "description": "{name}۔ {description}۔",
    },

    "kn": {
        "unknown": (
            "ಪರವಾಗಿಲ್ಲ. ನಾವು ನಿಧಾನವಾಗಿ ಮಾತನಾಡಬಹುದು. "
            "ಇದಕ್ಕೆ ಉತ್ತರಿಸಲು ನನ್ನ ಬಳಿ ಈಗ ಸಾಕಷ್ಟು ಮಾಹಿತಿ ಇಲ್ಲ."
        ),
        "confusion": (
            "ಪರವಾಗಿಲ್ಲ. ನಾವು ನಿಧಾನವಾಗಿ ಮಾತನಾಡೋಣ."
        ),
        "frustration": (
            "ನಾವು ನಿಧಾನವಾಗಿ ಮಾಡೋಣ. ಚಿಂತಿಸಬೇಡಿ."
        ),
        "remember": "ನನಗೆ {name} ನೆನಪಿದ್ದಾರೆ.",
        "relationship": "{name} ನಿಮ್ಮ {relationship}.",
        "description": "{name}. {description}.",
    },

    "ml": {
        "unknown": (
            "സാരമില്ല. നമുക്ക് പതുക്കെ സംസാരിക്കാം. "
            "ഇതിന് ഉത്തരം നൽകാൻ ഇപ്പോൾ എന്റെ പക്കൽ മതിയായ വിവരമില്ല."
        ),
        "confusion": (
            "സാരമില്ല. നമുക്ക് പതുക്കെ സംസാരിക്കാം."
        ),
        "frustration": (
            "നമുക്ക് പതുക്കെ ചെയ്യാം. വിഷമിക്കേണ്ട."
        ),
        "remember": "എനിക്ക് {name} ഓർമ്മയുണ്ട്.",
        "relationship": "{name} നിങ്ങളുടെ {relationship} ആണ്.",
        "description": "{name}. {description}.",
    },

    "or": {
        "unknown": (
            "କିଛି ଅସୁବିଧା ନାହିଁ। ଆମେ ଧୀରେ ଧୀରେ କଥା ହୋଇପାରିବା। "
            "ଏହାର ଉତ୍ତର ଦେବା ପାଇଁ ମୋ ପାଖରେ ଏବେ ପର୍ଯ୍ୟାପ୍ତ ସୂଚନା ନାହିଁ।"
        ),
        "confusion": (
            "କିଛି ଅସୁବିଧା ନାହିଁ। ଆମେ ଧୀରେ ଧୀରେ କଥା ହେବା।"
        ),
        "frustration": (
            "ଆମେ ଧୀରେ ଧୀରେ କରିବା। ଚିନ୍ତା କରନ୍ତୁ ନାହିଁ।"
        ),
        "remember": "ମୋତେ {name} ମନେ ଅଛନ୍ତି।",
        "relationship": "{name} ଆପଣଙ୍କ {relationship}।",
        "description": "{name}। {description}।",
    },

    "as": {
        "unknown": (
            "কোনো কথা নাই। আমি এতিয়া ইয়াৰ উত্তৰ দিবলৈ পৰ্যাপ্ত তথ্য নাজানো।"
        ),
        "confusion": (
            "কোনো কথা নাই। আমি লাহে লাহে কথা পাতোঁ।"
        ),
        "frustration": (
            "আমি লাহে লাহে কৰোঁ। চিন্তা নকৰিব।"
        ),
        "remember": "মোৰ {name} মনত আছে।",
        "relationship": "{name} আপোনাৰ {relationship}।",
        "description": "{name}। {description}।",
    },

    "es": {
        "unknown": (
            "Está bien. Podemos ir despacio. "
            "Todavía no tengo suficiente información para responder."
        ),
        "confusion": (
            "Está bien. Podemos ir despacio."
        ),
        "frustration": (
            "Vamos a hacerlo con calma. No se preocupe."
        ),
        "remember": "Recuerdo a {name}.",
        "relationship": "{name} es su {relationship}.",
        "description": "{name}. {description}.",
    },

    "fr": {
        "unknown": (
            "Ce n'est pas grave. Nous pouvons prendre notre temps. "
            "Je n'ai pas encore assez d'informations pour répondre."
        ),
        "confusion": (
            "Ce n'est pas grave. Nous pouvons prendre notre temps."
        ),
        "frustration": (
            "Prenons notre temps. Ne vous inquiétez pas."
        ),
        "remember": "Je me souviens de {name}.",
        "relationship": "{name} est votre {relationship}.",
        "description": "{name}. {description}.",
    },

    "de": {
        "unknown": (
            "Das ist in Ordnung. Wir können ganz in Ruhe vorgehen. "
            "Ich habe noch nicht genug Informationen für eine Antwort."
        ),
        "confusion": (
            "Das ist in Ordnung. Wir können ganz in Ruhe vorgehen."
        ),
        "frustration": (
            "Wir machen ganz langsam weiter. Keine Sorge."
        ),
        "remember": "Ich erinnere mich an {name}.",
        "relationship": "{name} ist Ihr {relationship}.",
        "description": "{name}. {description}.",
    },

    "it": {
        "unknown": (
            "Va bene. Possiamo andare con calma. "
            "Non ho ancora abbastanza informazioni per rispondere."
        ),
        "confusion": (
            "Va bene. Possiamo andare con calma."
        ),
        "frustration": (
            "Facciamo con calma. Non si preoccupi."
        ),
        "remember": "Ricordo {name}.",
        "relationship": "{name} è il suo {relationship}.",
        "description": "{name}. {description}.",
    },

    "pt": {
        "unknown": (
            "Tudo bem. Podemos ir devagar. "
            "Ainda não tenho informações suficientes para responder."
        ),
        "confusion": (
            "Tudo bem. Podemos ir devagar."
        ),
        "frustration": (
            "Vamos com calma. Não se preocupe."
        ),
        "remember": "Eu me lembro de {name}.",
        "relationship": "{name} é seu {relationship}.",
        "description": "{name}. {description}.",
    },

    "ja": {
        "unknown": (
            "大丈夫です。ゆっくり話しましょう。"
            "今は答えるための十分な情報がありません。"
        ),
        "confusion": (
            "大丈夫です。ゆっくり話しましょう。"
        ),
        "frustration": (
            "ゆっくり進めましょう。心配しないでください。"
        ),
        "remember": "{name}のことを覚えています。",
        "relationship": "{name}はあなたの{relationship}です。",
        "description": "{name}。{description}。",
    },

    "ko": {
        "unknown": (
            "괜찮아요. 천천히 이야기해도 됩니다. "
            "아직 답변할 충분한 정보가 없어요."
        ),
        "confusion": (
            "괜찮아요. 천천히 이야기해요."
        ),
        "frustration": (
            "천천히 해볼게요. 걱정하지 마세요."
        ),
        "remember": "{name}을 기억하고 있어요.",
        "relationship": "{name}은 당신의 {relationship}이에요.",
        "description": "{name}. {description}.",
    },

    "zh": {
        "unknown": (
            "没关系。我们可以慢慢来。"
            "我现在还没有足够的信息来回答这个问题。"
        ),
        "confusion": (
            "没关系。我们慢慢来。"
        ),
        "frustration": (
            "我们慢慢来，不用担心。"
        ),
        "remember": "我记得{name}。",
        "relationship": "{name}是您的{relationship}。",
        "description": "{name}。{description}。",
    },

    "ar": {
        "unknown": (
            "لا بأس. يمكننا أن نتحدث بهدوء وببطء. "
            "ليس لدي معلومات كافية للإجابة الآن."
        ),
        "confusion": (
            "لا بأس. يمكننا أن نتحدث بهدوء."
        ),
        "frustration": (
            "لنأخذ الأمر بهدوء. لا تقلق."
        ),
        "remember": "أتذكر {name}.",
        "relationship": "{name} هو {relationship} الخاص بك.",
        "description": "{name}. {description}.",
    },

    "ru": {
        "unknown": (
            "Ничего страшного. Мы можем поговорить спокойно и не спеша. "
            "У меня пока недостаточно информации для ответа."
        ),
        "confusion": (
            "Ничего страшного. Давайте поговорим спокойно."
        ),
        "frustration": (
            "Давайте не спеша. Не волнуйтесь."
        ),
        "remember": "Я помню {name}.",
        "relationship": "{name} — ваш {relationship}.",
        "description": "{name}. {description}.",
    },
}


# ============================================================
# RELATIONSHIP TRANSLATIONS FOR LOCAL FALLBACK
# ============================================================

RELATIONSHIPS: dict[str, dict[str, str]] = {
    "hi": {
        "daughter": "बेटी",
        "son": "बेटा",
        "wife": "पत्नी",
        "husband": "पति",
        "mother": "माँ",
        "father": "पिता",
        "sister": "बहन",
        "brother": "भाई",
        "friend": "दोस्त",
        "caregiver": "देखभाल करने वाले व्यक्ति",
    },
    "mr": {
        "daughter": "मुलगी",
        "son": "मुलगा",
        "wife": "पत्नी",
        "husband": "पती",
        "mother": "आई",
        "father": "वडील",
        "sister": "बहीण",
        "brother": "भाऊ",
        "friend": "मित्र",
        "caregiver": "काळजी घेणारी व्यक्ती",
    },
    "bn": {
        "daughter": "মেয়ে",
        "son": "ছেলে",
        "wife": "স্ত্রী",
        "husband": "স্বামী",
        "mother": "মা",
        "father": "বাবা",
        "sister": "বোন",
        "brother": "ভাই",
        "friend": "বন্ধু",
    },
    "ta": {
        "daughter": "மகள்",
        "son": "மகன்",
        "wife": "மனைவி",
        "husband": "கணவர்",
        "mother": "அம்மா",
        "father": "அப்பா",
        "sister": "சகோதரி",
        "brother": "சகோதரர்",
        "friend": "நண்பர்",
    },
    "te": {
        "daughter": "కూతురు",
        "son": "కొడుకు",
        "wife": "భార్య",
        "husband": "భర్త",
        "mother": "అమ్మ",
        "father": "నాన్న",
        "sister": "సోదరి",
        "brother": "సోదరుడు",
        "friend": "స్నేహితుడు",
    },
    "gu": {
        "daughter": "દીકરી",
        "son": "દીકરો",
        "wife": "પત્ની",
        "husband": "પતિ",
        "mother": "માતા",
        "father": "પિતા",
        "sister": "બહેન",
        "brother": "ભાઈ",
        "friend": "મિત્ર",
    },
    "pa": {
        "daughter": "ਧੀ",
        "son": "ਪੁੱਤਰ",
        "wife": "ਪਤਨੀ",
        "husband": "ਪਤੀ",
        "mother": "ਮਾਂ",
        "father": "ਪਿਤਾ",
        "sister": "ਭੈਣ",
        "brother": "ਭਰਾ",
        "friend": "ਦੋਸਤ",
    },
    "ur": {
        "daughter": "بیٹی",
        "son": "بیٹا",
        "wife": "بیوی",
        "husband": "شوہر",
        "mother": "ماں",
        "father": "والد",
        "sister": "بہن",
        "brother": "بھائی",
        "friend": "دوست",
    },
    "es": {
        "daughter": "hija",
        "son": "hijo",
        "wife": "esposa",
        "husband": "esposo",
        "mother": "madre",
        "father": "padre",
        "sister": "hermana",
        "brother": "hermano",
        "friend": "amigo",
    },
    "fr": {
        "daughter": "fille",
        "son": "fils",
        "wife": "épouse",
        "husband": "mari",
        "mother": "mère",
        "father": "père",
        "sister": "sœur",
        "brother": "frère",
        "friend": "ami",
    },
    "de": {
        "daughter": "Tochter",
        "son": "Sohn",
        "wife": "Ehefrau",
        "husband": "Ehemann",
        "mother": "Mutter",
        "father": "Vater",
        "sister": "Schwester",
        "brother": "Bruder",
        "friend": "Freund",
    },
    "it": {
        "daughter": "figlia",
        "son": "figlio",
        "wife": "moglie",
        "husband": "marito",
        "mother": "madre",
        "father": "padre",
        "sister": "sorella",
        "brother": "fratello",
        "friend": "amico",
    },
    "pt": {
        "daughter": "filha",
        "son": "filho",
        "wife": "esposa",
        "husband": "marido",
        "mother": "mãe",
        "father": "pai",
        "sister": "irmã",
        "brother": "irmão",
        "friend": "amigo",
    },
    "ja": {
        "daughter": "娘",
        "son": "息子",
        "wife": "妻",
        "husband": "夫",
        "mother": "母",
        "father": "父",
        "sister": "姉妹",
        "brother": "兄弟",
        "friend": "友人",
    },
    "ko": {
        "daughter": "딸",
        "son": "아들",
        "wife": "아내",
        "husband": "남편",
        "mother": "어머니",
        "father": "아버지",
        "sister": "자매",
        "brother": "형제",
        "friend": "친구",
    },
    "zh": {
        "daughter": "女儿",
        "son": "儿子",
        "wife": "妻子",
        "husband": "丈夫",
        "mother": "母亲",
        "father": "父亲",
        "sister": "姐妹",
        "brother": "兄弟",
        "friend": "朋友",
    },
    "ar": {
        "daughter": "ابنة",
        "son": "ابن",
        "wife": "زوجة",
        "husband": "زوج",
        "mother": "أم",
        "father": "أب",
        "sister": "أخت",
        "brother": "أخ",
        "friend": "صديق",
    },
    "ru": {
        "daughter": "дочь",
        "son": "сын",
        "wife": "жена",
        "husband": "муж",
        "mother": "мама",
        "father": "отец",
        "sister": "сестра",
        "brother": "брат",
        "friend": "друг",
    },
}


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_gemini_client():
    """
    Lazily create the Gemini client.
    """

    return _canonical_gemini_client()


# ============================================================
# LANGUAGE HELPERS
# ============================================================

def _detect_response_language(
    message: str,
) -> dict[str, Any]:
    """
    Detect the language of the incoming message.

    The existing language.py module remains the authority.
    """

    default = {
        "code": "en",
        "name": "English",
        "native_name": "English",
        "locale": "en-IN",
        "speech_locale": "en-IN",
        "confidence": 0.0,
        "method": "default",
    }

    if not message:
        return default

    try:
        if detect_language is None:
            return default

        result = detect_language(message)

        if not isinstance(result, dict):
            return default

        code = (
            result.get("code")
            or result.get("language_code")
            or "en"
        )

        return {
            "code": str(code),
            "name": result.get(
                "name",
                code,
            ),
            "native_name": result.get(
                "native_name",
                result.get("name", code),
            ),
            "locale": result.get(
                "locale",
                f"{code}-IN",
            ),
            "speech_locale": result.get(
                "speech_locale",
                result.get(
                    "locale",
                    f"{code}-IN",
                ),
            ),
            "confidence": result.get(
                "confidence",
                0.0,
            ),
            "method": result.get(
                "method",
                "language_module",
            ),
        }

    except Exception:
        logger.exception(
            "Language detection failed."
        )
        return default


def _normalize_language_code(
    language: dict[str, Any],
) -> str:
    code = str(
        language.get("code", "en")
    ).strip().lower()

    if code in LANGUAGE_FALLBACKS:
        return code

    return "en"


def get_last_language_info(
    message: str,
) -> dict[str, Any]:
    """
    Public helper for API layers.

    The Flask application can use this later to expose:
        language
        locale
        speech_locale
        confidence
    """

    return _detect_response_language(
        message
    )


# ============================================================
# SYSTEM INSTRUCTION
# ============================================================

SYSTEM_INSTRUCTION = """
You are the conversational intelligence layer of DementiaCareAI.

You are speaking with a person who may have memory difficulties.

Your communication must be:

calm, warm, respectful, patient, natural, simple,
reassuring, compassionate, and human.

You are not a doctor.
You do not diagnose medical conditions.
You do not make medication decisions.
You do not provide unsafe medical instructions.

SOURCE OF TRUTH:

The DementiaCareAI application provides trusted patient
context and is the source of truth.

Only use facts explicitly supplied by the application.

Never invent:

names
family members
relationships
dates
locations
events
memories
personal history
medical conditions
diagnoses
medications
emotions
personality traits
visual details
activities
preferences

If information is unavailable, say that you do not have
that information.

Do not guess.

CONVERSATION:

Use the supplied conversation history to understand
follow-up questions, pronouns, and references.

Do not unnecessarily ask the person to repeat information
that is already available.

If a follow-up cannot be resolved safely, say so naturally.

NATURAL STYLE:

Do not sound like a database.

Do not expose internal fields.

Do not mention JSON.

Do not mention databases.

Do not mention match scores.

Do not mention Gemini.

Do not mention internal application systems.

Do not repeatedly use the person's name.

Avoid repetitive sentence patterns.

Keep responses concise and natural.

VOICE:

The response may be spoken aloud.

Use short, natural spoken sentences.

Avoid markdown.

Avoid bullet points unless explicitly requested.

Avoid emojis.

Avoid excessive punctuation.

Avoid technical language.

LANGUAGE:

The application will provide the detected language of
the person's current message.

Respond in that exact language.

If the detected language is Hinglish, respond naturally
in Hinglish using a comfortable mixture of Hindi and
English as the person naturally would.

Do not translate the person's message into English first.

Do not answer in English when another language is specified.

Preserve names and factual information exactly when
appropriate.

If the language is uncertain, follow the language explicitly
specified by the application. Otherwise use the language
of the person's current message.

IMPORTANT:

Return only the response intended for the person.

Do not return language labels.

Do not return JSON.

Do not return explanations about these instructions.

Dementia-friendly behavior:

If the person seems confused, reassure gently.

If frustrated, slow the conversation down.

If sad, acknowledge the feeling without pretending to know
exactly how they feel.

If the same question is repeated, answer patiently.

Never shame the person.

Never say "you are wrong."

SAFETY:

If the person describes an emergency or immediate danger,
encourage contacting local emergency services or a trusted
person nearby.

Use the application context as the source of truth.

Never sacrifice factual accuracy for conversational fluency.
"""


# ============================================================
# BASIC HELPERS
# ============================================================

def _clean_text(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def _clean_list(
    value: Any,
) -> list[str]:

    if not value:
        return []

    if isinstance(value, str):
        value = [value]

    if not isinstance(
        value,
        (list, tuple),
    ):
        return []

    result: list[str] = []

    for item in value:
        text = _clean_text(item)

        if text:
            result.append(text)

    return result


# ============================================================
# MEMORY SANITIZATION
# ============================================================

def sanitize_memory(
    memory: dict[str, Any] | None,
) -> dict[str, Any] | None:

    if not isinstance(
        memory,
        dict,
    ):
        return None

    visual_context = memory.get(
        "visual_context"
    )

    if isinstance(
        visual_context,
        list,
    ):
        if (
            visual_context
            and isinstance(
                visual_context[0],
                dict,
            )
        ):
            visual_context = visual_context[0]
        else:
            visual_context = None

    elif not isinstance(
        visual_context,
        dict,
    ):
        visual_context = None

    result = {
        "name": _clean_text(
            memory.get("name")
        ),
        "category": _clean_text(
            memory.get("category")
        ),
        "relationship": _clean_text(
            memory.get("relationship")
        ),
        "description": _clean_text(
            memory.get("description")
        ),
        "event_date": _clean_text(
            memory.get("event_date")
        ),
        "tags": _clean_list(
            memory.get("tags")
        ),
        "visual_context": visual_context,
    }

    return {
        key: value
        for key, value in result.items()
        if value not in (
            None,
            "",
            [],
            {},
        )
    }


# ============================================================
# HISTORY SANITIZATION
# ============================================================

def sanitize_history(
    history: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:

    if not history:
        return []

    cleaned: list[dict[str, str]] = []

    for item in history[-10:]:

        if not isinstance(
            item,
            dict,
        ):
            continue

        user_message = _clean_text(
            item.get("user")
            or item.get("message")
        )

        assistant_message = _clean_text(
            item.get("assistant")
            or item.get("response")
        )

        if not user_message:
            continue

        cleaned.append(
            {
                "user": user_message,
                "assistant": (
                    assistant_message or ""
                ),
            }
        )

    return cleaned


# ============================================================
# PATIENT PROFILE SANITIZATION
# ============================================================

def sanitize_patient_profile(
    profile: dict[str, Any] | None,
) -> dict[str, Any]:

    if not isinstance(
        profile,
        dict,
    ):
        return {}

    try:
        serialized = json.dumps(
            profile,
            ensure_ascii=False,
            default=str,
        )

        result = json.loads(
            serialized
        )

        if isinstance(
            result,
            dict,
        ):
            return result

    except Exception:
        logger.exception(
            "Unable to sanitize patient profile."
        )

    return {}


# ============================================================
# CONTEXT BUILDER
# ============================================================

def build_gemini_context(
    *,
    message: str,
    memories: list[dict[str, Any]] | None = None,
    emotion: str = "neutral",
    emotion_confidence: float = 0.0,
    patient_profile: dict[str, Any] | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    previous_memory: dict[str, Any] | None = None,
    follow_up: bool = False,
    intent: str | None = None,
    language: dict[str, Any] | None = None,
) -> dict[str, Any]:

    safe_memories: list[
        dict[str, Any]
    ] = []

    for memory in memories or []:

        safe_memory = sanitize_memory(
            memory
        )

        if safe_memory:
            safe_memories.append(
                safe_memory
            )

    safe_previous_memory = (
        sanitize_memory(
            previous_memory
        )
    )

    safe_history = sanitize_history(
        conversation_history
    )

    safe_profile = (
        sanitize_patient_profile(
            patient_profile
        )
    )

    try:
        safe_confidence = round(
            float(
                emotion_confidence
                or 0
            ),
            2,
        )
    except (
        TypeError,
        ValueError,
    ):
        safe_confidence = 0.0

    language = language or {
        "code": "en",
        "name": "English",
        "native_name": "English",
        "locale": "en-IN",
        "speech_locale": "en-IN",
        "confidence": 0.0,
        "method": "default",
    }

    return {
        "current_user_message": (
            _clean_text(message)
            or ""
        ),
        "intent": (
            _clean_text(intent)
            or "general"
        ),
        "follow_up": bool(
            follow_up
        ),
        "emotion": (
            _clean_text(emotion)
            or "neutral"
        ),
        "emotion_confidence": (
            safe_confidence
        ),
        "language": {
            "code": language.get(
                "code",
                "en",
            ),
            "name": language.get(
                "name",
                "English",
            ),
            "native_name": language.get(
                "native_name",
                "English",
            ),
            "locale": language.get(
                "locale",
                "en-IN",
            ),
            "speech_locale": language.get(
                "speech_locale",
                "en-IN",
            ),
            "confidence": language.get(
                "confidence",
                0.0,
            ),
            "method": language.get(
                "method",
                "default",
            ),
        },
        "relevant_memories": (
            safe_memories
        ),
        "previous_memory": (
            safe_previous_memory
        ),
        "patient_profile": (
            safe_profile
        ),
        "recent_conversation": (
            safe_history
        ),
    }


# ============================================================
# RESPONSE CLEANING
# ============================================================

def clean_generated_response(
    response: str | None,
) -> str:

    if not response:
        return ""

    text = str(
        response
    ).strip()

    text = re.sub(
        r"^```(?:text|plaintext)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    prefixes = (
        "assistant:",
        "ai:",
        "gemini:",
        "response:",
    )

    lower = text.lower()

    for prefix in prefixes:

        if lower.startswith(
            prefix
        ):
            text = text[
                len(prefix):
            ].strip()

            break

    if (
        len(text) >= 2
        and text[0] == '"'
        and text[-1] == '"'
    ):
        text = text[1:-1].strip()

    return text


# ============================================================
# LOCAL MULTILINGUAL FALLBACK
# ============================================================

def generate_fallback_response(
    *,
    language: dict[str, Any],
    memories: list[dict[str, Any]] | None = None,
    emotion: str = "neutral",
    previous_memory: dict[str, Any] | None = None,
) -> str:

    code = _normalize_language_code(
        language
    )

    phrases = LANGUAGE_FALLBACKS.get(
        code,
        LANGUAGE_FALLBACKS["en"],
    )

    memories = memories or []

    memory = (
        memories[0]
        if memories
        else previous_memory
    )

    # No memory available.
    if not memory:

        if emotion == "confusion":
            return phrases[
                "confusion"
            ]

        if emotion == "frustration":
            return phrases[
                "frustration"
            ]

        return phrases[
            "unknown"
        ]

    name = _clean_text(
        memory.get("name")
    )

    relationship = _clean_text(
        memory.get("relationship")
    )

    description = _clean_text(
        memory.get("description")
    )

    if not name:
        return phrases[
            "unknown"
        ]

    translated_relationship = (
        relationship
        or ""
    )

    relationship_map = (
        RELATIONSHIPS.get(
            code,
            {},
        )
    )

    relationship_key = (
        translated_relationship
        .strip()
        .lower()
    )

    translated_relationship = (
        relationship_map.get(
            relationship_key,
            translated_relationship,
        )
    )

    if (
        name
        and translated_relationship
    ):
        response = phrases[
            "relationship"
        ].format(
            name=name,
            relationship=(
                translated_relationship
            ),
        )

    elif (
        name
        and description
    ):
        # Avoid pretending that an English description
        # has been translated when Gemini is unavailable.
        if code == "en":
            response = phrases[
                "description"
            ].format(
                name=name,
                description=description,
            )
        else:
            response = phrases[
                "remember"
            ].format(
                name=name
            )

    else:
        response = phrases[
            "remember"
        ].format(
            name=name
        )

    if emotion == "confusion":
        prefix = phrases[
            "confusion"
        ]

        # Use the reassurance alone when it already
        # contains a complete response.
        if code != "en":
            return (
                prefix
                + " "
                + response
            )

    if emotion == "frustration":
        prefix = phrases[
            "frustration"
        ]

        if code != "en":
            return (
                prefix
                + " "
                + response
            )

    return response


# ============================================================
# GEMINI RESPONSE
# ============================================================

def generate_gemini_response(
    message: str = "",
    context: dict[str, Any] | None = None,
) -> str:

    message = (
        _clean_text(message)
        or ""
    )

    if not message:

        return (
            "I'm here with you. "
            "What would you like to talk about?"
        )

    raw_context = (
        context
        if isinstance(
            context,
            dict,
        )
        else {}
    )

    memories = raw_context.get(
        "relevant_memories",
        [],
    )

    if not isinstance(
        memories,
        list,
    ):
        memories = []

    emotion = (
        _clean_text(
            raw_context.get(
                "emotion"
            )
        )
        or "neutral"
    )

    emotion_confidence = (
        raw_context.get(
            "emotion_confidence",
            0.0,
        )
    )

    patient_profile = (
        raw_context.get(
            "patient_profile",
            {},
        )
    )

    conversation_history = (
        raw_context.get(
            "conversation_history",
            raw_context.get(
                "recent_conversation",
                [],
            ),
        )
    )

    if not isinstance(
        conversation_history,
        list,
    ):
        conversation_history = []

    previous_memory = (
        raw_context.get(
            "previous_memory"
        )
    )

    follow_up = bool(
        raw_context.get(
            "follow_up",
            False,
        )
    )

    intent = (
        _clean_text(
            raw_context.get(
                "intent"
            )
        )
        or "general"
    )

    # --------------------------------------------------------
    # Detect language automatically.
    # --------------------------------------------------------

    language = (
        raw_context.get(
            "language"
        )
    )

    if not isinstance(
        language,
        dict,
    ):
        language = (
            _detect_response_language(
                message
            )
        )

    language_code = (
        _normalize_language_code(
            language
        )
    )

    # --------------------------------------------------------
    # Build trusted context.
    # --------------------------------------------------------

    safe_context = (
        build_gemini_context(
            message=message,
            memories=memories,
            emotion=emotion,
            emotion_confidence=(
                emotion_confidence
            ),
            patient_profile=(
                patient_profile
            ),
            conversation_history=(
                conversation_history
            ),
            previous_memory=(
                previous_memory
            ),
            follow_up=follow_up,
            intent=intent,
            language=language,
        )
    )

    # --------------------------------------------------------
    # Always have a local fallback.
    # --------------------------------------------------------

    fallback = (
        generate_fallback_response(
            language=language,
            memories=(
                safe_context[
                    "relevant_memories"
                ]
            ),
            emotion=safe_context[
                "emotion"
            ],
            previous_memory=(
                safe_context.get(
                    "previous_memory"
                )
            ),
        )
    )

    # --------------------------------------------------------
    # Respect known quota cooldown.
    # --------------------------------------------------------

    global _last_quota_error_at

    if (
        _last_quota_error_at
        and (
            time.time()
            - _last_quota_error_at
            < QUOTA_COOLDOWN_SECONDS
        )
    ):
        return fallback

    # --------------------------------------------------------
    # Gemini generation.
    # --------------------------------------------------------

    try:

        client = (
            get_gemini_client()
        )

        trusted_context = json.dumps(
            safe_context,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        language_name = (
            language.get(
                "name",
                language_code,
            )
        )

        language_locale = (
            language.get(
                "locale",
                f"{language_code}-IN",
            )
        )

        prompt = f"""
TRUSTED DEMENTIACAREAI APPLICATION CONTEXT

The following information comes from the DementiaCareAI
application and is the source of truth.

{trusted_context}


CURRENT USER MESSAGE

{message}


LANGUAGE REQUIREMENT

Detected response language:
{language_name}

Language code:
{language_code}

Locale:
{language_locale}

You MUST respond in the detected response language.

The response must be natural for a native speaker.

If the language is Hinglish, use natural Hinglish rather
than formal Hindi or formal English.

Do not translate the response into English.

Do not explain which language you are using.


RESPONSE REQUIREMENTS

1. Answer the person's current message directly.

2. Use only facts contained in the trusted application
   context.

3. Never invent a person, relationship, event, date,
   location, memory, medical fact, emotion, or visual detail.

4. Use conversation history for follow-up questions.

5. If the subject cannot be identified safely, say so.

6. Be warm and dementia-friendly.

7. Keep the response concise.

8. Make it natural for text-to-speech.

9. Do not mention the application.

10. Do not mention JSON.

11. Do not mention databases.

12. Do not mention internal fields.

13. Do not mention match scores.

14. Do not mention Gemini.

15. Do not provide medical diagnosis.

16. Do not provide unsafe medical instructions.

17. Do not use markdown.

18. Do not use bullet points unless explicitly requested.

19. Return ONLY the spoken response.

20. Never invent missing information.
"""

        response = (
            client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=(
                    types.GenerateContentConfig(
                        system_instruction=(
                            SYSTEM_INSTRUCTION
                        ),
                        temperature=0.35,
                        max_output_tokens=180,
                    )
                ),
            )
        )

        generated = (
            clean_generated_response(
                getattr(
                    response,
                    "text",
                    "",
                )
            )
        )

        if not generated:
            logger.warning(
                "Gemini returned an empty response."
            )

            return fallback

        return generated

    except Exception as exc:

        error_text = str(
            exc
        ).lower()

        # Gemini free-tier quota exhaustion.
        if (
            "resource_exhausted"
            in error_text
            or "quota" in error_text
            or "429" in error_text
        ):
            _last_quota_error_at = (
                time.time()
            )

            logger.warning(
                "Gemini quota unavailable. "
                "Using multilingual local fallback."
            )

        else:
            logger.warning(
                "Gemini generation failed. "
                "Using local fallback: %s",
                exc,
            )

        return fallback


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def generate_response(
    message: str,
    context: dict[str, Any] | None = None,
) -> str:
    """
    Compatibility alias for older code.
    """

    return generate_gemini_response(
        message=message,
        context=context,
    )


# ============================================================
# STATUS
# ============================================================

def get_gemini_status() -> dict[str, Any]:
    """
    Return safe runtime information.
    """

    quota_cooldown_active = False

    if _last_quota_error_at:
        quota_cooldown_active = (
            time.time()
            - _last_quota_error_at
            < QUOTA_COOLDOWN_SECONDS
        )

    return {
        "configured": bool(
            GEMINI_API_KEY
        ),
        "model": GEMINI_MODEL,
        "multilingual": True,
        "local_fallback": True,
        "quota_cooldown_active": (
            quota_cooldown_active
        ),
        "language_detection": (
            detect_language is not None
        ),
    }
