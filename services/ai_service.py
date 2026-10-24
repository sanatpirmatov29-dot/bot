import logging
from pathlib import Path
from typing import Dict, List, Optional
import aiohttp

import config

logger = logging.getLogger(__name__)

# Foydalanuvchilarning suhbat tarixini xotirada saqlash {user_id: [{"role": "user"|"model", "text": "..."}]}
USER_CONVERSATIONS: Dict[int, List[Dict[str, str]]] = {}
MAX_HISTORY_LENGTH = 10  # Oxirgi 10 ta xabar eslab qolinadi

SYSTEM_PROMPT = (
    "Siz aqlli, xushmuomala va bilimdon sun'iy intellekt yordamchisisiz. "
    "O'zbek tilida ravon, chiroyli va tushunarli javob bering. "
    "Savollarga to'liq va aniq javob qaytaring. "
    "Javoblarda Telegramga mos chiroyli formatlashdan (paragraflar, ro'yxatlar, emojilar) foydalaning."
)


def reset_user_history(user_id: int) -> None:
    """Foydalanuvchi suhbat tarixini tozalash."""
    if user_id in USER_CONVERSATIONS:
        USER_CONVERSATIONS.pop(user_id, None)


async def _ask_gemini_api(prompt: str, history: List[Dict[str, str]]) -> Optional[str]:
    """Google Gemini API orqali javob olish."""
    api_key = getattr(config, "GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    # Gemini API formati: contents: [{"role": "user"|"model", "parts": [{"text": "..."}]}]
    contents = []
    for item in history:
        role = "user" if item["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": item["text"]}]
        })
    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    # Gemini modellarini sinab ko'ramiz
    models = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest"]
    async with aiohttp.ClientSession() as session:
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": contents,
                "systemInstruction": {
                    "parts": [{"text": SYSTEM_PROMPT}]
                },
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 2048,
                }
            }
            try:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=45)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                return parts[0].get("text", "").strip()
                    else:
                        err_text = await resp.text()
                        logger.warning(f"Gemini {model} xatolik berdi ({resp.status}): {err_text[:200]}")
            except Exception as e:
                logger.warning(f"Gemini {model} so'rovida xatolik: {e}")

    return None


async def _ask_fallback_ai(prompt: str, history: List[Dict[str, str]]) -> Optional[str]:
    """Bepul AI (Pollinations API) orqali javob olish."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history:
        role = "user" if item["role"] == "user" else "assistant"
        messages.append({"role": role, "content": item["text"]})
    messages.append({"role": "user", "content": prompt})

    url = "https://text.pollinations.ai/"
    payload = {
        "messages": messages,
        "model": "openai",
        "seed": 42,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=45)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    return text.strip()
    except Exception as e:
        logger.error(f"Fallback AI so'rovida xatolik: {e}")

    return None


async def ask_ai(user_id: int, prompt: str) -> str:
    """Sun'iy intellektdan javob olish va suhbat tarixini yangilash."""
    history = USER_CONVERSATIONS.get(user_id, [])

    # 1. Google Gemini API orqali sinab ko'ramiz
    reply = await _ask_gemini_api(prompt, history)

    # 2. Agar Gemini kaliti bo'lmasa yoki xato bersa, bepul fallback AI ishlaydi
    if not reply:
        reply = await _ask_fallback_ai(prompt, history)

    if not reply:
        return "Kechirasiz, sun'iy intellekt serveri bilan bog'lanishda xatolik yuz berdi. Iltimos birozdan so'ng qayta urinib ko'ring."

    # Suhbat tarixini xotiraga yozamiz
    history.append({"role": "user", "text": prompt})
    history.append({"role": "model", "text": reply})
    if len(history) > MAX_HISTORY_LENGTH * 2:
        history = history[-MAX_HISTORY_LENGTH * 2:]
    USER_CONVERSATIONS[user_id] = history

    return reply


async def ask_ai_with_audio(user_id: int, audio_path: Path, mime_type: str = "audio/ogg") -> str:
    """Ovozli xabarni (audio) qabul qilib, uni tushunib javob qaytarish."""
    import base64
    api_key = getattr(config, "GEMINI_API_KEY", "").strip()
    if not api_key:
        return (
            "⚠️ Ovozli xabarlarni tahlil qilish uchun Google Gemini API kaliti talab qilinadi.\n"
            "Iltimos, /setkey buyrug'i orqali API kalitingizni kiriting."
        )

    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        logger.error(f"Audio faylni o'qishda xatolik: {e}")
        return "Audio faylni qayta ishlashda xatolik yuz berdi."

    models = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest"]
    prompt = (
        "Foydalanuvchi sizga mikrofon orqali ovozli xabar yubordi. "
        "Uning gaplarini diqqat bilan tinglang va unga xuddi jonli suhbatdagidek tabiiy, "
        "ravon, ixcham va samimiy o'zbek tilida javob bering. "
        "Javobingiz ovoz chiqarib aytilishi uchun qulay bo'lsin (ortiqcha jadval yoki murakkab belgilar ishlatmang)."
    )

    contents = [
        {
            "role": "user",
            "parts": [
                {"text": prompt},
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": audio_b64,
                    }
                },
            ],
        }
    ]

    async with aiohttp.ClientSession() as session:
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": contents,
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 2048,
                },
            }
            try:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                reply = parts[0].get("text", "").strip()
                                history = USER_CONVERSATIONS.get(user_id, [])
                                history.append({"role": "user", "text": "[Ovozli xabar]"})
                                history.append({"role": "model", "text": reply})
                                USER_CONVERSATIONS[user_id] = history
                                return reply
                    else:
                        err = await resp.text()
                        logger.warning(f"Audio Gemini {model} ({resp.status}): {err[:200]}")
            except Exception as e:
                logger.warning(f"Audio Gemini {model} so'rovida xatolik: {e}")

    return "Kechirasiz, ovozli xabarni tahlil qilishda xatolik yuz berdi. Iltimos qayta urinib ko'ring."
