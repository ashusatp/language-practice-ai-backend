import asyncio
import logging
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.language import Language
from app.models.voice import Voice

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("seed")

# Data from agent/providers.py
LANGUAGES_TO_SEED = [
    {"code": "en-IN", "name": "English (India)"},
    {"code": "hi-IN", "name": "Hindi (India)"},
    {"code": "en", "name": "English"},
    {"code": "hi", "name": "Hindi"},
]

SARVAM_FEMALE_SPEAKERS = [
    "amelia", "ishita", "kavitha", "kavya", "neha", "pooja", "priya",
    "ritu", "roopa", "rupali", "shruti", "shreya", "simran", "sophia",
    "suhani", "tanya",
]

SARVAM_MALE_SPEAKERS = [
    "aayan", "aditya", "advait", "amit", "ashutosh", "dev", "kabir",
    "manan", "rahul", "ratan", "rohan", "shubh", "sumit", "varun",
]


async def seed() -> None:
    logger.info("Starting database seed for languages and voices...")

    async with AsyncSessionLocal() as session:
        # 1. Seed Languages
        language_map = {}
        for lang_data in LANGUAGES_TO_SEED:
            stmt = select(Language).where(Language.code == lang_data["code"])
            res = await session.execute(stmt)
            existing_lang = res.scalar_one_or_none()

            if not existing_lang:
                lang = Language(code=lang_data["code"], name=lang_data["name"], is_active=True)
                session.add(lang)
                await session.flush()
                logger.info("Created language: %s (%s)", lang.name, lang.code)
                language_map[lang.code] = lang
            else:
                logger.info("Language already exists: %s (%s)", existing_lang.name, existing_lang.code)
                language_map[existing_lang.code] = existing_lang

        # Primary default language for Sarvam Indian voices
        default_lang = language_map.get("en-IN") or language_map.get("en")
        default_lang_id = default_lang.id if default_lang else None

        # 2. Seed Voices (Female)
        voices_created = 0
        for speaker in SARVAM_FEMALE_SPEAKERS:
            stmt = select(Voice).where(Voice.voice_id == speaker, Voice.provider == "sarvam")
            res = await session.execute(stmt)
            existing_voice = res.scalar_one_or_none()

            if not existing_voice:
                voice = Voice(
                    name=speaker.capitalize(),
                    voice_id=speaker,
                    provider="sarvam",
                    gender="female",
                    language_id=default_lang_id,
                    is_active=True,
                )
                session.add(voice)
                voices_created += 1

        # 3. Seed Voices (Male)
        for speaker in SARVAM_MALE_SPEAKERS:
            stmt = select(Voice).where(Voice.voice_id == speaker, Voice.provider == "sarvam")
            res = await session.execute(stmt)
            existing_voice = res.scalar_one_or_none()

            if not existing_voice:
                voice = Voice(
                    name=speaker.capitalize(),
                    voice_id=speaker,
                    provider="sarvam",
                    gender="male",
                    language_id=default_lang_id,
                    is_active=True,
                )
                session.add(voice)
                voices_created += 1

        await session.commit()
        logger.info(
            "Seeding complete! %d new voices inserted (Total Sarvam speakers: %d).",
            voices_created,
            len(SARVAM_FEMALE_SPEAKERS) + len(SARVAM_MALE_SPEAKERS),
        )


if __name__ == "__main__":
    asyncio.run(seed())
