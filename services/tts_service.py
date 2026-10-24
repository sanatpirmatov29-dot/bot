import asyncio
import logging
import subprocess
import uuid
from pathlib import Path
from typing import Optional
import edge_tts
from gtts import gTTS
import imageio_ffmpeg

from config import DOWNLOADS_DIR

logger = logging.getLogger(__name__)

# Microsoft Azure ning tabiiy o'zbek ayol ovozi
VOICE_UZBEK = "uz-UZ-MadinaNeural"


async def text_to_speech(text: str) -> Optional[Path]:
    """Matnni Telegram ovozli xabari (OGG Opus) formatiga aylantirish."""
    # Belgilarni va ortiqcha formatlashlarni tozalash
    clean_text = (
        text.replace("*", "")
        .replace("#", "")
        .replace("`", "")
        .replace("<b>", "")
        .replace("</b>", "")
        .replace("<i>", "")
        .replace("</i>", "")
        .strip()
    )
    if not clean_text:
        return None

    # Ovozli xabar juda cho'zilib ketmasligi uchun dastlabki 700 belgini gapirish
    if len(clean_text) > 700:
        clean_text = clean_text[:697] + "..."

    mp3_path = DOWNLOADS_DIR / f"tts_{uuid.uuid4().hex[:10]}.mp3"
    ogg_path = DOWNLOADS_DIR / f"voice_{uuid.uuid4().hex[:10]}.ogg"

    # 1. edge-tts (Tabiiy o'zbek ovozi) orqali urinib ko'ramiz
    success = False
    try:
        communicate = edge_tts.Communicate(clean_text, VOICE_UZBEK)
        await communicate.save(str(mp3_path))
        if mp3_path.exists() and mp3_path.stat().st_size > 0:
            success = True
    except Exception as e:
        logger.warning(f"edge-tts xatolik berdi: {e}")

    # 2. Agar edge-tts ishlamasa, gTTS (Google TTS) orqali zaxira
    if not success:
        try:
            def _gtts_run():
                tts = gTTS(text=clean_text, lang="uz")
                tts.save(str(mp3_path))
            await asyncio.to_thread(_gtts_run)
            if mp3_path.exists() and mp3_path.stat().st_size > 0:
                success = True
        except Exception as e:
            logger.error(f"gTTS zaxirada ham xatolik berdi: {e}")

    if not success or not mp3_path.exists():
        return None

    # 3. MP3 faylni Telegram Voice (OGG Opus, 48000Hz, mono) formatiga aylantirish
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(mp3_path),
        "-c:a", "libopus",
        "-b:a", "32k",
        "-vbr", "on",
        "-ar", "48000",
        "-ac", "1",
        str(ogg_path),
    ]

    try:
        def _convert_opus():
            return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        proc = await asyncio.to_thread(_convert_opus)
        if proc.returncode == 0 and ogg_path.exists() and ogg_path.stat().st_size > 0:
            return ogg_path
        # Agar opus konvertatsiya bo'lmasa, mp3 ning o'zini qaytaramiz
        return mp3_path
    except Exception as e:
        logger.error(f"FFmpeg opus konvertatsiyasida xatolik: {e}")
        return mp3_path
    finally:
        # mp3 faylni tozalash (agar ogg tayyor bo'lsa)
        if ogg_path.exists() and mp3_path.exists():
            try:
                mp3_path.unlink(missing_ok=True)
            except Exception:
                pass
