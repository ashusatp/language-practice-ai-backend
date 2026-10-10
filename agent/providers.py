from livekit.plugins import deepgram, sarvam
from config import config
from typing import Literal

LanguageType = Literal["english", "hindi"]

SARVAM_SPEAKERS = {
    # Female
    "amelia", "ishita", "kavitha", "kavya", "neha", "pooja", "priya",
    "ritu", "roopa", "rupali", "shruti", "shreya", "simran", "sophia",
    "suhani", "tanya",
    # Male
    "aayan", "aditya", "advait", "amit", "ashutosh", "dev", "kabir",
    "manan", "rahul", "ratan", "rohan", "shubh", "sumit", "varun",
}


class STT:
    def __init__(self, language: LanguageType, model="nova-3"):
        self.language_map = {
            "english": "en",
            "hindi": "hi",
        }

        self.stt = deepgram.STT(
            api_key=config.deepgram_api_key,
            model=model,
            language=self.language_map[language],
        )


class TTS:
    def __init__(
        self,
        language: LanguageType = "english",
        speaker: str = "shubh",
        model: str = "bulbul:v3",
        pace: float = 1.0,
    ):
        self.language_map = {
            "english": "en-IN",
            "hindi": "hi-IN",
        }

        # Normalize speaker or fallback to default
        speaker_clean = speaker.lower().strip() if speaker else "shubh"
        selected_speaker = speaker_clean if speaker_clean in SARVAM_SPEAKERS else "shubh"

        self.tts = sarvam.TTS(
            target_language_code=self.language_map.get(language, "en-IN"),
            model=model,
            speaker=selected_speaker,
            speech_sample_rate=22050,
            pace=pace,
            output_audio_bitrate="128k",
            output_audio_codec="mp3",
            min_buffer_size=50,
            max_chunk_length=150,
            send_completion_event=True,
            api_key=config.sarvam_api_key or None,
        )
