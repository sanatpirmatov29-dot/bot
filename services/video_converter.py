import asyncio
import logging
import subprocess
import uuid
from pathlib import Path
from typing import Optional
import imageio_ffmpeg

from config import DOWNLOADS_DIR

logger = logging.getLogger(__name__)


def convert_to_video_note_sync(input_path: Path) -> Optional[Path]:
    """Videoni Telegram dumaloq video (Video Note) formatiga o'tkazish.
    
    Talablar:
    - 1:1 kvadrat nisbat (markazdan qirqib olinadi)
    - 480x480 o'lcham
    - Maksimal 60 soniya (Telegram video note talabi)
    - H.264 video kodek, AAC audio kodek
    """
    output_path = DOWNLOADS_DIR / f"note_{uuid.uuid4().hex[:10]}.mp4"
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # 1-urinish: video + audio (agar audio bo'lsa avtomatik ulaydi)
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(input_path),
        "-t", "60",
        "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=480:480,setsar=1",
        "-map", "0:v:0",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "26",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-movflags", "+faststart",
        str(output_path),
    ]

    try:
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        if process.returncode != 0:
            logger.warning(f"FFmpeg audio bilan xato berdi, audiosiz urinib ko'ramiz: {process.stderr[-300:]}")
            # 2-urinish: audiosiz (-an) agar audio kodekda yoki oqimda muammo bo'lsa
            cmd_no_audio = [
                ffmpeg_exe,
                "-y",
                "-i", str(input_path),
                "-t", "60",
                "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=480:480,setsar=1",
                "-map", "0:v:0",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "26",
                "-pix_fmt", "yuv420p",
                "-an",
                "-movflags", "+faststart",
                str(output_path),
            ]
            res2 = subprocess.run(
                cmd_no_audio,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
            if res2.returncode != 0:
                logger.error(f"FFmpeg ikkinchi urinishda ham xato berdi: {res2.stderr[-300:]}")
                return None

        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path
        return None
    except Exception as e:
        logger.error(f"Video note konvertatsiyasida xatolik: {e}")
        return None


async def convert_to_video_note(input_path: Path) -> Optional[Path]:
    """Asinxron o'ram: konvertatsiyani alohida threadda bajaradi."""
    return await asyncio.to_thread(convert_to_video_note_sync, input_path)
