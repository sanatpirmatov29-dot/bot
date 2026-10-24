import asyncio
import logging
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
import yt_dlp

from config import DOWNLOADS_DIR, COOKIES_FILE

logger = logging.getLogger(__name__)


def _download_sync(url: str) -> Optional[Dict[str, Any]]:
    """Sinxron tarzda yt-dlp orqali videoni yuklab olish."""
    file_id = uuid.uuid4().hex[:10]
    output_template = str(DOWNLOADS_DIR / f"insta_{file_id}_%(id)s.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "format": "best[ext=mp4]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    # Agar cookies.txt mavjud bo'lsa, uni ulaymiz (Instagram cheklovlariga qarshi)
    if COOKIES_FILE.exists():
        ydl_opts["cookiefile"] = str(COOKIES_FILE)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
            if not info:
                return None

            # Ba'zida playlist/entries shaklida qaytadi
            if "entries" in info and info["entries"]:
                entry = info["entries"][0]
            else:
                entry = info

            # Yuklangan fayl nomini aniqlash
            filename = ydl.prepare_filename(entry)
            file_path = Path(filename)

            # Agar format konvertatsiya qilingan bo'lsa (masalan .mp4 ga)
            if not file_path.exists():
                mp4_variant = file_path.with_suffix(".mp4")
                if mp4_variant.exists():
                    file_path = mp4_variant
                else:
                    # Papkadan mos prefiksli faylni qidiramiz
                    matching = list(DOWNLOADS_DIR.glob(f"insta_{file_id}_*"))
                    if matching:
                        file_path = matching[0]
                    else:
                        return None

            title = entry.get("title") or entry.get("description") or "Instagram Video"
            if len(title) > 300:
                title = title[:297] + "..."

            return {
                "file_path": file_path,
                "title": title,
                "duration": entry.get("duration"),
                "width": entry.get("width"),
                "height": entry.get("height"),
            }
        except Exception as e:
            logger.error(f"yt-dlp yuklashda xatolik: {e}")
            raise e


async def download_instagram_video(url: str) -> Optional[Dict[str, Any]]:
    """Asinxron o'ram: yt-dlp ni alohida threadda ishga tushiradi."""
    return await asyncio.to_thread(_download_sync, url)


def remove_file(file_path: Optional[Path]) -> None:
    """Vaqtinchalik faylni xavfsiz o'chirish."""
    if file_path and file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            logger.warning(f"Faylni o'chirishda xatolik {file_path}: {e}")
