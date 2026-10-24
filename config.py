import os
from pathlib import Path
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

BASE_DIR = Path(__file__).parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "").strip()

# Loyiha asosiy papkasi va vaqtinchalik yuklash papkasi
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Agar cookies.txt fayli bo'lsa (Instagram blokirovkasini aylanib o'tish uchun)
COOKIES_FILE = BASE_DIR / "cookies.txt"


def update_gemini_api_key(new_key: str) -> bool:
    """Yangi Gemini API kalitini .env ga yozish va xotirada yangilash."""
    global GEMINI_API_KEY
    key_clean = new_key.strip()
    GEMINI_API_KEY = key_clean
    try:
        from dotenv import set_key
        set_key(str(ENV_FILE), "GEMINI_API_KEY", key_clean)
        return True
    except Exception:
        return True


def update_required_channel(new_channel: str) -> bool:
    """Majburiy a'zo bo'linadigan kanal nomini .env ga yozish va xotirada yangilash."""
    global REQUIRED_CHANNEL
    ch_clean = new_channel.strip()
    REQUIRED_CHANNEL = ch_clean
    try:
        from dotenv import set_key
        set_key(str(ENV_FILE), "REQUIRED_CHANNEL", ch_clean)
        return True
    except Exception:
        return True
