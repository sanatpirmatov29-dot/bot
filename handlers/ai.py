import os
import re
import uuid
import logging
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction, ChatType
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

import config
from config import DOWNLOADS_DIR, update_gemini_api_key
from services.downloader import remove_file
from services.ai_service import ask_ai, ask_ai_with_audio, reset_user_history
from services.tts_service import text_to_speech
from services.image_service import generate_ai_image, analyze_and_generate_from_photo

router = Router()
logger = logging.getLogger(__name__)

# Telegram xabari maksimal 4096 belgi bo'lishi mumkin
MAX_TELEGRAM_MSG_LEN = 4000

# Ovozli xabarlar uchun kutilayotgan javoblar xotirasi {req_id: response_text}
PENDING_VOICE_RESPONSES: dict = {}


async def is_bot_addressed(message: Message, bot: Bot) -> tuple[bool, str]:
    """Xabar botga qaratilganligini aniqlash (guruhlar uchun).
    Qaytaradi: (addressed: bool, clean_text: str)
    """
    # 1. Shaxsiy (lichka) chat bo'lsa - har doim botga qaratilgan
    if message.chat.type == ChatType.PRIVATE:
        return True, (message.text or message.caption or "").strip()

    # 2. Guruh bo'lsa:
    bot_info = await bot.get_me()
    bot_username = f"@{bot_info.username}".lower()
    text = (message.text or message.caption or "").strip()

    # Botga javob (reply) qilinganmi?
    if (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot.id
    ):
        clean_text = re.sub(re.escape(bot_username), "", text, flags=re.IGNORECASE).strip()
        return True, clean_text

    # Bot username zikr qilinganmi (@bot_username)?
    if bot_username in text.lower():
        clean_text = re.sub(re.escape(bot_username), "", text, flags=re.IGNORECASE).strip()
        return True, clean_text

    return False, text


async def reply_in_chunks(message: Message, text: str):
    """Uzun matnlarni Telegram chekloviga ko'ra bo'lib jo'natish (HTML xatosiz)."""
    chunks = [text[i : i + MAX_TELEGRAM_MSG_LEN] for i in range(0, len(text), MAX_TELEGRAM_MSG_LEN)]
    for chunk in chunks:
        try:
            await message.reply(chunk, parse_mode="HTML")
        except Exception:
            await message.reply(chunk, parse_mode=None)


@router.message(Command("clear"))
@router.message(Command("reset"))
async def cmd_clear_ai(message: Message):
    """Suhbat tarixini tozalash."""
    reset_user_history(message.from_user.id if message.from_user else 0)
    await message.reply("🔄 <b>Suhbat tarixi tozalandi!</b> Yangi mavzuda savol berishingiz mumkin.", parse_mode="HTML")


@router.message(F.text == "🤖 AI Chat")
async def btn_ai_chat_menu(message: Message):
    """AI Chat bo'limi tugmasi bosilganda."""
    current_key = getattr(config, "GEMINI_API_KEY", "").strip()
    status_str = "✅ Google Gemini ulandi" if current_key else "⚡ Bepul AI rejimida ishlamoqda"

    text = (
        "🤖 <b>AI Chat bo'limiga xush kelibsiz!</b>\n\n"
        f"Holat: <b>{status_str}</b>\n\n"
        "Menga quyidagi usullarda murojaat qilishingiz mumkin:\n"
        "✍️ <b>Matn:</b> Istalgan savolingizni yozing.\n"
        "🎤 <b>Ovozli xabar:</b> Ovoz yuboring, men tushunib ovoz yoki matn bilan javob beraman.\n"
        "🎨 <b>Rasm generatsiya:</b> /rasm &lt;matn&gt; deb yozing yoki rasm yuboring!\n\n"
        "👥 <i>Guruhda botga savol berish uchun uni @ belgisi bilan chaqiring yoki uning xabariga 'Reply' qiling!</i>"
    )
    await message.reply(text, parse_mode="HTML")


@router.message(F.text == "🔑 Gemini API Key")
@router.message(Command("setkey"))
async def handle_setkey_command(message: Message):
    """Gemini API kalitini ko'rish yoki yangilash."""
    args = message.text.split(maxsplit=1)
    
    if len(args) > 1 and args[1].strip():
        new_key = args[1].strip()
        update_gemini_api_key(new_key)
        masked_key = new_key[:8] + "..." + new_key[-4:] if len(new_key) > 12 else "***"
        await message.reply(
            f"✅ <b>Gemini API Key muvaffaqiyatli saqlandi!</b>\n\n"
            f"🔑 Kalit: <code>{masked_key}</code>\n"
            f"🚀 Endi barcha savollaringiz Google Gemini modeli orqali qayta ishlanadi.",
            parse_mode="HTML",
        )
        return

    current_key = getattr(config, "GEMINI_API_KEY", "").strip()
    if current_key:
        masked_key = current_key[:8] + "..." + current_key[-4:] if len(current_key) > 12 else "***"
        key_status = f"✅ <b>Hozirgi kalit:</b> <code>{masked_key}</code>"
    else:
        key_status = "⚠️ <b>Hozirda shaxsiy API kalit o'rnatilmagan</b> (bepul rejimda ishlamoqda)."

    text = (
        "🔑 <b>Google Gemini API Key bo'limi:</b>\n\n"
        f"{key_status}\n\n"
        "<b>Qanday qilib API kalit olish mumkin?</b>\n"
        "1. <a href='https://aistudio.google.com/apikey'>Google AI Studio</a> saytiga kiring (bepul).\n"
        "2. Google hisobingiz bilan kirib, <b>«Create API Key»</b> tugmasini bosing.\n"
        "3. Olingan kalitni botga quyidagi formatda yuboring:\n\n"
        "<code>/setkey AIzaSy...sizning_kalitingiz...</code>\n\n"
        "<i>Yoki to'g'ridan-to'g'ri kalitning o'zini shu yerga yuborishingiz mumkin!</i>"
    )
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("ai"))
async def cmd_ai(message: Message, bot: Bot):
    """Maxsus /ai buyrug'i orqali savol berish."""
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.reply(
            "Iltimos, savolingizni yozing! 🤖\n\n"
            "<i>Namuna:</i>\n"
            "<code>/ai O'zbekistonning diqqatga sazovor joylari haqida aytib ber</code>",
            parse_mode="HTML",
        )
        return

    prompt = args[1].strip()
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status_msg = await message.reply("🧠 <i>Javob tayyorlanmoqda...</i>", parse_mode="HTML")

    try:
        user_id = message.from_user.id if message.from_user else message.chat.id
        response = await ask_ai(user_id=user_id, prompt=prompt)
        try:
            await status_msg.delete()
        except Exception:
            pass
        await reply_in_chunks(message, response)
    except Exception as e:
        logger.error(f"AI javob berishda xatolik: {e}", exc_info=True)
        try:
            await message.reply("❌ Sun'iy intellektdan javob olishda xatolik yuz berdi. Iltimos qayta urinib ko'ring.", parse_mode=None)
        except Exception:
            pass


# 🎨 Matndan rasm generatsiya qilish buyrug'i: /image, /draw, /rasm
@router.message(Command("image"))
@router.message(Command("draw"))
@router.message(Command("rasm"))
async def cmd_generate_image(message: Message, bot: Bot):
    """Matn asosida yangi rasm generatsiya qilish."""
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.reply(
            "Qanday rasm chizish kerakligini yozing! 🎨\n\n"
            "<i>Namuna:</i>\n"
            "<code>/rasm Kosmosda suzayotgan futuristik shahar</code>\n"
            "<code>/rasm Samarqand Registon maydoni neon uslubida</code>",
            parse_mode="HTML",
        )
        return

    prompt = args[1].strip()
    status_msg = await message.reply("🎨 <i>Rasm chizilmoqda, iltimos biroz kuting...</i>", parse_mode="HTML")
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)

    gen_path = None
    try:
        gen_path = await generate_ai_image(prompt)
        if gen_path and gen_path.exists():
            try:
                await status_msg.delete()
            except Exception:
                pass
            await message.reply_photo(
                photo=FSInputFile(gen_path),
                caption=f"✨ <b>Generatsiya natijasi:</b>\n<i>«{prompt[:200]}»</i>",
                parse_mode="HTML",
            )
        else:
            await status_msg.edit_text("❌ Rasm chizishda xatolik yuz berdi. Iltimos qayta urinib ko'ring.")
    except Exception as e:
        logger.error(f"Rasm generatsiyasida xatolik: {e}", exc_info=True)
        try:
            await status_msg.edit_text("❌ Rasm generatsiya qilib bo'lmadi.")
        except Exception:
            pass
    finally:
        remove_file(gen_path)


# 🖼️ Rasm yuborilganda uni tahlil qilib yangi AI rasm generatsiya qilish
@router.message(F.photo)
async def handle_photo_message(message: Message, bot: Bot):
    """Rasm yuborilganda uni tahlil qilib, yangi rasm generatsiya qilish."""
    addressed, clean_caption = await is_bot_addressed(message, bot)

    # Guruhda bo'lsa va bot chaqirilmagan bo'lsa - e'tibor bermaymiz (spam bo'lmasligi uchun)
    if message.chat.type != ChatType.PRIVATE and not addressed:
        return

    photo = message.photo[-1]  # Eng yuqori sifatli versiyasini olamiz
    status_msg = await message.reply("🎨 <i>Rasm qabul qilindi, sun'iy intellekt yangi variantini chizmoqda...</i>", parse_mode="HTML")
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)

    input_photo_path = None
    gen_path = None
    try:
        file = await bot.get_file(photo.file_id)
        input_photo_path = DOWNLOADS_DIR / f"photo_in_{uuid.uuid4().hex[:10]}.jpg"
        await bot.download_file(file.file_path, destination=input_photo_path)

        gen_path = await analyze_and_generate_from_photo(input_photo_path, clean_caption)

        if gen_path and gen_path.exists():
            try:
                await status_msg.delete()
            except Exception:
                pass

            caption_text = f"✨ <b>Sizning rasmingiz asosida yangi AI variant:</b>"
            if clean_caption:
                caption_text += f"\n<i>Ko'rsatma: «{clean_caption[:150]}»</i>"

            await message.reply_photo(
                photo=FSInputFile(gen_path),
                caption=caption_text,
                parse_mode="HTML",
            )
        else:
            await status_msg.edit_text("❌ Rasmni qayta chizishda muammo yuzaga keldi. Iltimos qayta urinib ko'ring.")

    except Exception as e:
        logger.error(f"Rasm qayta ishlashda xatolik: {e}", exc_info=True)
        try:
            await status_msg.edit_text("❌ Rasm bilan ishlashda xatolik yuz berdi.")
        except Exception:
            pass
    finally:
        remove_file(input_photo_path)
        remove_file(gen_path)


@router.message(F.voice | F.audio)
async def handle_voice_message(message: Message, bot: Bot):
    """Mikrofon orqali yuborilgan ovozli xabarni tinglab, qanday formatda javob berishni so'rash."""
    addressed, _ = await is_bot_addressed(message, bot)
    if message.chat.type != ChatType.PRIVATE and not addressed:
        return

    voice = message.voice or message.audio
    if not voice:
        return

    if voice.file_size and voice.file_size > 20 * 1024 * 1024:
        await message.reply("⚠️ Ovozli xabar hajmi 20 MB dan kichik bo'lishi kerak.")
        return

    status_msg = await message.reply("🎤 <i>Ovozingiz tinglanmoqda va javob tayyorlanmoqda...</i>", parse_mode="HTML")
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    audio_path = None
    try:
        file = await bot.get_file(voice.file_id)
        ext = "ogg" if message.voice else "mp3"
        audio_path = DOWNLOADS_DIR / f"voice_in_{uuid.uuid4().hex[:10]}.{ext}"
        await bot.download_file(file.file_path, destination=audio_path)

        user_id = message.from_user.id if message.from_user else message.chat.id
        mime = "audio/ogg" if message.voice else "audio/mp3"

        response_text = await ask_ai_with_audio(user_id=user_id, audio_path=audio_path, mime_type=mime)

        req_id = uuid.uuid4().hex[:8]
        PENDING_VOICE_RESPONSES[req_id] = response_text
        if len(PENDING_VOICE_RESPONSES) > 200:
            PENDING_VOICE_RESPONSES.pop(next(iter(PENDING_VOICE_RESPONSES)), None)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🎙️ Ovozli xabar", callback_data=f"ans_mode:voice:{req_id}"),
                    InlineKeyboardButton(text="✍️ Matnli xabar", callback_data=f"ans_mode:text:{req_id}"),
                ],
                [
                    InlineKeyboardButton(text="✨ Ikkalasida ham (Ovoz + Matn)", callback_data=f"ans_mode:both:{req_id}"),
                ],
            ]
        )

        try:
            await status_msg.edit_text(
                "🎙️ <b>Ovozingiz eshitildi va javob tayyor!</b>\n\n"
                "Javobni qanday qabul qilishni xohlaysiz?",
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        except Exception:
            await message.reply(
                "🎙️ <b>Ovozingiz eshitildi va javob tayyor!</b>\n\n"
                "Javobni qanday qabul qilishni xohlaysiz?",
                reply_markup=keyboard,
                parse_mode="HTML",
            )

    except Exception as e:
        logger.error(f"Ovozli xabarni qayta ishlashda xatolik: {e}", exc_info=True)
        try:
            await status_msg.edit_text("❌ Ovozli xabarni tushunishda xatolik yuz berdi. Iltimos qaytadan gapirib ko'ring.")
        except Exception:
            pass
    finally:
        remove_file(audio_path)


@router.callback_query(F.data.startswith("ans_mode:"))
async def handle_answer_mode_selection(callback: CallbackQuery, bot: Bot):
    """Foydalanuvchi javob formatini (ovozli, matn yoki ikkalasi) tanlaganda."""
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer()
        return

    mode = parts[1]
    req_id = parts[2]
    response_text = PENDING_VOICE_RESPONSES.pop(req_id, None)

    if not response_text:
        await callback.answer("⚠️ Ushbu javobning vaqti tugagan, iltimos qaytadan ovoz yuboring.", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        return

    chat_id = callback.message.chat.id

    try:
        await callback.message.delete()
    except Exception:
        pass

    if mode == "text":
        for chunk in [response_text[i : i + MAX_TELEGRAM_MSG_LEN] for i in range(0, len(response_text), MAX_TELEGRAM_MSG_LEN)]:
            try:
                await bot.send_message(chat_id=chat_id, text=chunk, parse_mode="HTML")
            except Exception:
                await bot.send_message(chat_id=chat_id, text=chunk, parse_mode=None)

    elif mode == "voice":
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)
        voice_path = None
        try:
            voice_path = await text_to_speech(response_text)
            if voice_path and voice_path.exists():
                await bot.send_voice(chat_id=chat_id, voice=FSInputFile(voice_path))
            else:
                for chunk in [response_text[i : i + MAX_TELEGRAM_MSG_LEN] for i in range(0, len(response_text), MAX_TELEGRAM_MSG_LEN)]:
                    try:
                        await bot.send_message(chat_id=chat_id, text=chunk, parse_mode="HTML")
                    except Exception:
                        await bot.send_message(chat_id=chat_id, text=chunk, parse_mode=None)
        finally:
            remove_file(voice_path)

    elif mode == "both":
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)
        voice_path = None
        try:
            voice_path = await text_to_speech(response_text)
            if voice_path and voice_path.exists():
                await bot.send_voice(chat_id=chat_id, voice=FSInputFile(voice_path))
            text_to_send = f"📝 <i>Matnli nusxasi:</i>\n{response_text}"
            for chunk in [text_to_send[i : i + MAX_TELEGRAM_MSG_LEN] for i in range(0, len(text_to_send), MAX_TELEGRAM_MSG_LEN)]:
                try:
                    await bot.send_message(chat_id=chat_id, text=chunk, parse_mode="HTML")
                except Exception:
                    await bot.send_message(chat_id=chat_id, text=chunk, parse_mode=None)
        finally:
            remove_file(voice_path)


@router.message(F.text)
async def handle_general_text_with_ai(message: Message, bot: Bot):
    """Foydalanuvchi oddiy matn yozganida avtomatik sun'iy intellekt orqali javob berish."""
    addressed, clean_text = await is_bot_addressed(message, bot)

    # Guruhda bo'lsa va bot chaqirilmagan bo'lsa - e'tibor bermaymiz!
    if message.chat.type != ChatType.PRIVATE and not addressed:
        return

    if not clean_text:
        return

    # Agar foydalanuvchi API kalitining o'zini (AIzaSy... yoki AQ....) yuborgan bo'lsa
    if (clean_text.startswith("AIzaSy") or clean_text.startswith("AQ.")) and len(clean_text) >= 25 and " " not in clean_text:
        update_gemini_api_key(clean_text)
        masked_key = clean_text[:8] + "..." + clean_text[-4:]
        await message.reply(
            f"✅ <b>Gemini API Key muvaffaqiyatli qabul qilindi va saqlandi!</b>\n\n"
            f"🔑 Kalit: <code>{masked_key}</code>\n"
            f"Endi barcha savollaringizga Google Gemini javob beradi! 🚀",
            parse_mode="HTML",
        )
        return

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status_msg = await message.reply("🧠 <i>Javob tayyorlanmoqda...</i>", parse_mode="HTML")

    try:
        user_id = message.from_user.id if message.from_user else message.chat.id
        response = await ask_ai(user_id=user_id, prompt=clean_text)
        try:
            await status_msg.delete()
        except Exception:
            pass
        await reply_in_chunks(message, response)
    except Exception as e:
        logger.error(f"AI javob berishda xatolik: {e}", exc_info=True)
        try:
            await message.reply("❌ Sun'iy intellektdan javob olishda xatolik yuz berdi. Iltimos qayta urinib ko'ring.", parse_mode=None)
        except Exception:
            pass
