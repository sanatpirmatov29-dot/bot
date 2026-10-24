import base64
import logging
import urllib.parse
import uuid
from pathlib import Path
from typing import Optional
import aiohttp

import config
from config import DOWNLOADS_DIR

logger = logging.getLogger(__name__)


async def generate_ai_image(prompt: str) -> Optional[Path]:
    """Pollinations AI (Flux modeli) orqali matndan rasm generatsiya qilish."""
    if not prompt or not prompt.strip():
        return None

    clean_prompt = prompt.strip()
    encoded_prompt = urllib.parse.quote(clean_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true&seed={uuid.uuid4().int % 100000}"

    output_path = DOWNLOADS_DIR / f"ai_img_{uuid.uuid4().hex[:10]}.jpg"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    image_bytes = await resp.read()
                    if image_bytes and len(image_bytes) > 1000:
                        with open(output_path, "wb") as f:
                            f.write(image_bytes)
                        return output_path
                else:
                    logger.warning(f"Pollinations AI rasm generatsiyasida xatolik ({resp.status})")
    except Exception as e:
        logger.error(f"Rasm generatsiya qilishda xatolik: {e}")

    return None


async def analyze_and_generate_from_photo(photo_path: Path, user_prompt: str = "") -> Optional[Path]:
    """Foydalanuvchi yuborgan rasmni Gemini orqali tahlil qilib, yangi AI rasm generatsiya qilish."""
    api_key = getattr(config, "GEMINI_API_KEY", "").strip()

    creative_prompt = user_prompt.strip()

    # Agar Gemini API kalit bo'lsa, rasmni ko'rib boyitilgan inglizcha prompt tuzamiz
    if api_key and photo_path.exists():
        try:
            with open(photo_path, "rb") as f:
                photo_b64 = base64.b64encode(f.read()).decode("utf-8")

            system_instruction = (
                "You are an expert AI prompt engineer for Midjourney and Flux image generators. "
                "Look at the uploaded image and user's instruction. "
                "Create a vivid, highly artistic, cinematic prompt in English to generate an incredible reimagined version of this image. "
                "Output ONLY the prompt in plain text without any introductory words or explanations."
            )

            user_instruction = (
                f"Foydalanuvchi ko'rsatmasi: '{user_prompt}'. "
                "Ushbu rasmni professional, chiroyli va yuqori sifatli qilib yangidan chizish uchun inglizcha prompt yozib ber."
                if user_prompt
                else "Ushbu rasmni zamonaviy san'at va yuqori sifatli AI uslubida yangidan chizish uchun inglizcha batafsil prompt yozib ber."
            )

            models = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest"]
            async with aiohttp.ClientSession() as session:
                for model in models:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                    payload = {
                        "contents": [
                            {
                                "role": "user",
                                "parts": [
                                    {"text": user_instruction},
                                    {
                                        "inlineData": {
                                            "mimeType": "image/jpeg",
                                            "data": photo_b64,
                                        }
                                    },
                                ],
                            }
                        ],
                        "systemInstruction": {"parts": [{"text": system_instruction}]},
                        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 300},
                    }
                    try:
                        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=45)) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                candidates = data.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    if parts:
                                        gemini_prompt = parts[0].get("text", "").strip()
                                        if gemini_prompt:
                                            creative_prompt = gemini_prompt
                                            break
                    except Exception as e:
                        logger.warning(f"Vision Gemini {model} xatolik: {e}")

        except Exception as e:
            logger.error(f"Rasm tahlilida xatolik: {e}")

    if not creative_prompt:
        creative_prompt = "masterpiece, cinematic photo, high detail, 8k resolution, artistic reimagining"

    # Yangi rasmni generatsiya qilamiz
    return await generate_ai_image(creative_prompt)
