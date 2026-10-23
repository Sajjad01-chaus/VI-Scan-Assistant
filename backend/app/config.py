import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env', encoding='utf-8-sig')

class Settings:
    mode = os.getenv('AI_MODE', 'fixture')
    database_url = os.getenv('DATABASE_URL', f'sqlite:///{(ROOT / "data" / "viscan.db").as_posix()}')
    google_key = os.getenv('GOOGLE_API_KEY', '')
    groq_key = os.getenv('GROQ_API_KEY', '')
    llm_model = os.getenv('LLM_MODEL', 'openai/gpt-oss-120b')
    google_stt = os.getenv('GOOGLE_STT_MODEL', 'gemini-3.5-transcribe-live')
    groq_stt = os.getenv('GROQ_STT_MODEL', 'whisper-large-v3')
    groq_tts = os.getenv('GROQ_TTS_MODEL', 'canopylabs/orpheus-v1-english')
    google_tts = os.getenv('GOOGLE_TTS_MODEL', 'gemini-3.8-flash-lite-tts')
    voice = os.getenv('TTS_VOICE', 'troy')
    origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000').split(',')
    cookie_secure = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'

settings = Settings()
