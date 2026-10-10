import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.language import Language
from app.models.voice import Voice
from app.types.content import (
    LanguageItemResponse,
    TopicItemResponse,
    VoiceItemResponse,
)

logger = logging.getLogger("app.api.routes.content")

router = APIRouter(tags=["Content & Configuration"])

LANGUAGE_EXTRAS = {
    "en": {"native_name": "English", "flag": "🇬🇧"},
    "hi": {"native_name": "हिन्दी", "flag": "🇮🇳"},
}

VOICE_EXTRAS = {
    "simran": {
        "gender": "Female",
        "accent": "Indian (Warm & Natural)",
        "gradient": "from-violet-500 to-indigo-600",
        "preview_audio_url": "https://cdn.khooai.com/previews/simran.mp3",
        "sample_audio_text": {
            "english": "Hello! I'm Simran. Let's practice speaking naturally together.",
            "hindi": "नमस्ते! मैं सिमरन हूँ। चलिए साथ मिलकर आत्मविश्वास से बोलने का अभ्यास करते हैं।",
        },
    },
    "shubh": {
        "gender": "Male",
        "accent": "Indian (Crisp & Articulate)",
        "gradient": "from-emerald-500 to-teal-600",
        "preview_audio_url": "https://cdn.khooai.com/previews/shubh.mp3",
        "sample_audio_text": {
            "english": "Hello! I'm Shubh. I'm here to help you speak fluently and confidently.",
            "hindi": "नमस्ते! मैं शुभ हूँ। बेझिझक बोलिए, मैं आपकी हर बातचीत में मदद करूँगा।",
        },
    },
    "rohan": {
        "gender": "Male",
        "accent": "Indian (Energetic & Friendly)",
        "gradient": "from-amber-500 to-orange-600",
        "preview_audio_url": "https://cdn.khooai.com/previews/rohan.mp3",
        "sample_audio_text": {
            "english": "Hey there! Ready for an engaging English conversation today?",
            "hindi": "नमस्ते! क्या आप आज एक रोमांचक बातचीत के लिए तैयार हैं?",
        },
    },
    "priya": {
        "gender": "Female",
        "accent": "Indian (Gentle & Patient)",
        "gradient": "from-rose-500 to-pink-600",
        "preview_audio_url": "https://cdn.khooai.com/previews/priya.mp3",
        "sample_audio_text": {
            "english": "Hi! Take your time, there's no rush. Let's talk about anything you like.",
            "hindi": "नमस्ते! आराम से बोलिए, कोई जल्दबाज़ी नहीं है। जिस विषय पर चाहें बात करते हैं।",
        },
    },
    "aditya": {
        "gender": "Male",
        "accent": "Indian (Professional & Calm)",
        "gradient": "from-blue-500 to-cyan-600",
        "preview_audio_url": "https://cdn.khooai.com/previews/aditya.mp3",
        "sample_audio_text": {
            "english": "Greetings! Let's sharpen your interview and communication skills.",
            "hindi": "नमस्ते! आइए आपके इंटरव्यू और बातचीत के कौशल को और बेहतर बनाते हैं।",
        },
    },
    "kavya": {
        "gender": "Female",
        "accent": "Indian (Expressive & Clear)",
        "gradient": "from-purple-500 to-fuchsia-600",
        "preview_audio_url": "https://cdn.khooai.com/previews/kavya.mp3",
        "sample_audio_text": {
            "english": "Hello! Learning languages is a journey. I'm excited to practice with you.",
            "hindi": "नमस्ते! भाषा सीखना एक खूबसूरत सफर है। आपके साथ अभ्यास करके खुशी होगी।",
        },
    },
    "neha": {
        "gender": "Female",
        "accent": "Indian (Upbeat & Polite)",
        "gradient": "from-teal-500 to-emerald-600",
        "preview_audio_url": "https://cdn.khooai.com/previews/neha.mp3",
        "sample_audio_text": {
            "english": "Hi! Great to meet you. What interesting topic shall we discuss today?",
            "hindi": "नमस्ते! आपसे मिलकर बहुत अच्छा लगा। आज हम किस दिलचस्प विषय पर बात करें?",
        },
    },
    "kabir": {
        "gender": "Male",
        "accent": "Indian (Deep & Thoughtful)",
        "gradient": "from-slate-600 to-stone-700",
        "preview_audio_url": "https://cdn.khooai.com/previews/kabir.mp3",
        "sample_audio_text": {
            "english": "Welcome. Clear expression and structured thought will take you far.",
            "hindi": "स्वागत है। स्पष्ट अभिव्यक्ति और सही शब्द आपको जीवन में बहुत आगे ले जाएंगे।",
        },
    },
}

TOPICS_LIST = [
    {"id": "daily-life", "label": "Daily Life", "hindi_label": "दैनिक दिनचर्या", "category": "general"},
    {"id": "job-interview", "label": "Job Interview", "hindi_label": "नौकरी का इंटरव्यू", "category": "professional"},
    {"id": "travel", "label": "Travel & Exploration", "hindi_label": "यात्रा और सफ़र", "category": "lifestyle"},
    {"id": "technology", "label": "Technology & AI", "hindi_label": "टेक्नोलॉजी और AI", "category": "intellectual"},
    {"id": "movies", "label": "Movies & Arts", "hindi_label": "फ़िल्में और कला", "category": "entertainment"},
    {"id": "food", "label": "Food & Culture", "hindi_label": "खान-पान", "category": "culture"},
    {"id": "free-talk", "label": "Free Talk", "hindi_label": "स्वतंत्र चर्चा", "category": "open"},
]


@router.get(
    "/languages",
    response_model=list[LanguageItemResponse],
    summary="List available languages",
)
async def list_languages(db: AsyncSession = Depends(get_db)):
    """Returns database-managed active practice languages."""
    stmt = select(Language).where(Language.is_active == True)
    res = await db.execute(stmt)
    languages = res.scalars().all()

    result: list[LanguageItemResponse] = []
    # Deduplicate codes if needed
    seen_codes = set()
    for lang in languages:
        code_key = lang.code
        if code_key in seen_codes:
            continue
        seen_codes.add(code_key)

        extras = LANGUAGE_EXTRAS.get(code_key, {"native_name": lang.name, "flag": "🌐"})
        # Clean display name
        display_name = "English" if "en" in code_key.lower() else ("Hindi" if "hi" in code_key.lower() else lang.name)
        result.append(
            LanguageItemResponse(
                id=lang.id,
                code=lang.code,
                name=display_name,
                native_name=extras["native_name"],
                flag=extras["flag"],
                is_active=lang.is_active,
            )
        )

    return result


@router.get(
    "/voices",
    response_model=list[VoiceItemResponse],
    summary="List available AI partner voices",
)
async def list_voices(
    language_code: Optional[str] = Query(None, description="Optional language filter (e.g. en-IN, hi-IN)"),
    db: AsyncSession = Depends(get_db),
):
    """Returns dynamic AI voice partner options."""
    stmt = select(Voice).where(Voice.is_active == True)
    res = await db.execute(stmt)
    voices = res.scalars().all()

    # Prioritize voices configured in VOICE_EXTRAS
    result: list[VoiceItemResponse] = []
    seen_voice_ids = set()

    for voice in voices:
        v_key = voice.voice_id.lower()
        if v_key in seen_voice_ids:
            continue
        seen_voice_ids.add(v_key)

        extras = VOICE_EXTRAS.get(
            v_key,
            {
                "gender": (voice.gender or "Neutral").capitalize(),
                "accent": "Natural AI Voice",
                "gradient": "from-indigo-500 to-purple-600",
                "preview_audio_url": voice.preview_audio_url,
                "sample_audio_text": {
                    "english": f"Hello! I am {voice.name}. Let's practice speaking naturally together.",
                    "hindi": f"नमस्ते! मैं {voice.name} हूँ। चलिए साथ मिलकर बोलने का अभ्यास करते हैं।",
                },
            },
        )

        result.append(
            VoiceItemResponse(
                id=v_key,
                name=voice.name,
                gender=extras["gender"],
                accent=extras["accent"],
                gradient=extras["gradient"],
                preview_audio_url=extras["preview_audio_url"] or voice.preview_audio_url,
                sample_audio_text=extras["sample_audio_text"],
            )
        )

    return result


@router.get(
    "/topics",
    response_model=list[TopicItemResponse],
    summary="List practice discussion topics",
)
async def list_topics():
    """Returns curated conversation topics with localized labels."""
    return [TopicItemResponse(**t) for t in TOPICS_LIST]
