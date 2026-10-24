import os
import uuid
import logging
from pathlib import Path
from typing import Optional
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

from config import DOWNLOADS_DIR
from services.downloader import remove_file
from services.video_converter import convert_to_video_note

router = Router()
logger = logging.getLogger(__name__)

# Telegram Bot API getFile cheklovi: 20 MB
MAX_VIDEO_SIZE = 20 * 1024 * 1024


async def process_and_send_video_note(
    target_message: Message,
    bot: Bot,
    file_id: str,
    file_size: Optional[int] = None,
    duration: Optional[int] = None,
    status_msg: Optional[Message] = None,
):
    """Videoni yuklab olib, dumaloq video xabarga aylantirib yuboruvchi asosiy funksiya."""
    if file_size and file_size > MAX_VIDEO_SIZE:
        size_mb = file_size / (1024 * 1024)
        error_text = (
            f"⚠️ <b>Video hajmi juda katta ({size_mb:.1f} MB)!</b>\n\n"
            "Telegram Bot API orqali faqat <b>20 MB gacha</b> bo'lgan videolarni qabul qilish mumkin.\n"
            "Iltimos, hajmi 20 MB dan kichikroq video yuboring."
        )
        if status_msg:
            await status_msg.edit_text(error_text, parse_mode="HTML")
        else:
            await target_message.reply(error_text, parse_mode="HTML")
        return

    if not status_msg:
        if duration and duration > 60:
            status_text = (
                "⏳ <b>Video qabul qilindi.</b>\n"
                "Telegram dumaloq video limiti 60 soniya bo'lgani sababli, "
                "uning dastlabki 60 soniyasi dumaloq shaklga keltirilmoqda..."
            )
        else:
            status_text = "⏳ Video qabul qilindi, dumaloq shaklga (video xabar) keltirilmoqda..."
        status_msg = await target_message.reply(status_text, parse_mode="HTML")

    # Chat action ko'rsatamiz: video xabar yozilmoqda
    try:
        await bot.send_chat_action(chat_id=target_message.chat.id, action=ChatAction.RECORD_VIDEO_NOTE)
    except Exception:
        pass

    input_path = None
    note_path = None
    try:
        # Faylni Telegram serveridan yuklab olamiz
        file = await bot.get_file(file_id)
        input_path = DOWNLOADS_DIR / f"raw_{uuid.uuid4().hex[:10]}.mp4"
        await bot.download_file(file.file_path, destination=input_path)

        # Dumaloq video note formatiga (480x480, 1:1) aylantiramiz
        note_path = await convert_to_video_note(input_path)

        if not note_path or not note_path.exists():
            await status_msg.edit_text("❌ Videoni dumaloq shaklga keltirishda xatolik yuz berdi.")
            return

        # Dumaloq video xabar (video_note) sifatida jo'natamiz
        await target_message.reply_video_note(
            video_note=FSInputFile(note_path),
            length=480,
        )

        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Dumaloq video tayyorlashda xatolik: {e}", exc_info=True)
        try:
            await status_msg.edit_text("❌ Xatolik yuz berdi. Iltimos qayta urinib ko'ring.")
        except Exception:
            pass
    finally:
        remove_file(input_path)
        remove_file(note_path)


@router.message(F.video)
async def handle_video_message(message: Message, bot: Bot):
    """Foydalanuvchi to'g'ridan-to'g'ri 4 burchak video yuborganda uni dumaloq qilib berish."""
    video = message.video
    await process_and_send_video_note(
        target_message=message,
        bot=bot,
        file_id=video.file_id,
        file_size=video.file_size,
        duration=video.duration,
    )


@router.message(F.animation)
async def handle_animation_message(message: Message, bot: Bot):
    """GIF yoki qisqa animatsiya yuborilganda."""
    anim = message.animation
    await process_and_send_video_note(
        target_message=message,
        bot=bot,
        file_id=anim.file_id,
        file_size=anim.file_size,
        duration=anim.duration,
    )


@router.message(F.document)
async def handle_document_video(message: Message, bot: Bot):
    """Video hujjat (fayl) sifatida yuborilgan bo'lsa."""
    doc = message.document
    is_video = (doc.mime_type and doc.mime_type.startswith("video/")) or (
        doc.file_name and doc.file_name.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm", ".3gp"))
    )
    if not is_video:
        return

    await process_and_send_video_note(
        target_message=message,
        bot=bot,
        file_id=doc.file_id,
        file_size=doc.file_size,
        duration=None,
    )


@router.message(F.video_note)
async def handle_video_note_already(message: Message):
    """Video allaqachon dumaloq bo'lsa."""
    await message.reply("⚪ Bu video allaqachon dumaloq shaklda! Yangi 4 burchak video yuborsangiz, uni dumaloq qilib beraman. 😊")


@router.callback_query(F.data == "make_round_video")
async def handle_callback_make_round(callback: CallbackQuery, bot: Bot):
    """Yuklangan video ostidagi 'Dumaloq video qilish' tugmasi bosilganda."""
    if not callback.message or not callback.message.video:
        await callback.answer("⚠️ Video topilmadi!", show_alert=True)
        return

    await callback.answer()
    video = callback.message.video
    status_msg = await callback.message.reply("⏳ Video dumaloq shaklga keltirilmoqda...")
    await process_and_send_video_note(
        target_message=callback.message,
        bot=bot,
        file_id=video.file_id,
        file_size=video.file_size,
        duration=video.duration,
        status_msg=status_msg,
    )
