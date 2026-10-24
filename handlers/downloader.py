import re
import os
import logging
from aiogram import Router, F
from aiogram.enums import ChatAction
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

from services.downloader import download_instagram_video, remove_file

router = Router()
logger = logging.getLogger(__name__)

# Instagram linklarini aniqlash uchun regex
INSTAGRAM_REGEX = re.compile(
    r"(https?:\/\/(?:www\.)?(?:instagram\.com|instagr\.am)\/(?:[a-zA-Z0-9_\.]+\/)?(?:p|reel|reels|tv|share)\/[A-Za-z0-9_-]+[^\s]*)",
    re.IGNORECASE,
)

TELEGRAM_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB limit Telegram Bot API uchun


@router.message(F.text.regexp(INSTAGRAM_REGEX))
async def handle_instagram_link(message: Message):
    match = INSTAGRAM_REGEX.search(message.text)
    if not match:
        return

    raw_url = match.group(1)
    # Qo'shimcha tracking parametrlarni (?igsh=..., ?dlrf=...) tozalash
    clean_url = raw_url.split("?")[0].rstrip("/") + "/"

    # Foydalanuvchiga jarayon boshlanganini bildiramiz
    status_msg = await message.reply("⏳ Video yuklanmoqda, iltimos kuting...")

    # Chatda "video yuklamoqda" statusini ko'rsatamiz
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.UPLOAD_VIDEO,
    )

    file_path = None
    try:
        # Videoni yuklab olamiz
        result = await download_instagram_video(clean_url)

        if not result or not result.get("file_path"):
            await status_msg.edit_text(
                "❌ <b>Videoni yuklab bo'lmadi!</b>\n\n"
                "Mumkin bo'lgan sabablar:\n"
                "• Profil yopiq (private) bo'lishi mumkin\n"
                "• Havola noto'g'ri yoki video o'chirilgan\n"
                "• Instagram tomonidan vaqtinchalik cheklov",
                parse_mode="HTML",
            )
            return

        file_path = result["file_path"]

        # Fayl hajmini tekshiramiz
        file_size = os.path.getsize(file_path)
        if file_size > TELEGRAM_MAX_FILE_SIZE:
            await status_msg.edit_text(
                "⚠️ <b>Video hajmi juda katta (50 MB dan ortiq)!</b>\n\n"
                "Telegram botlari orqali maksimal 50 MB gacha bo'lgan videolarni jo'natish mumkin.",
                parse_mode="HTML",
            )
            return

        # Tayyor videoni Telegramga jo'natish (dumaloq qilish tugmasi bilan)
        video_input = FSInputFile(path=file_path)
        caption = (
            f"🎬 <b>{result.get('title', 'Instagram Video')}</b>\n\n"
            f"📥 @{(await message.bot.get_me()).username} orqali yuklandi"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⚪ Dumaloq video qilish (Video Note)",
                        callback_data="make_round_video",
                    )
                ]
            ]
        )

        await message.reply_video(
            video=video_input,
            caption=caption,
            reply_markup=keyboard,
            parse_mode="HTML",
            duration=result.get("duration"),
            width=result.get("width"),
            height=result.get("height"),
            supports_streaming=True,
        )

        # Status xabarini o'chirib tashlaymiz
        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Xatolik yuz berdi: {e}", exc_info=True)
        await status_msg.edit_text(
            "❌ <b>Xatolik yuz berdi!</b>\n\n"
            "Videoni yuklab olishda muammo yuzaga keldi. Iltimos, havola to'g'riligini tekshirib qayta urinib ko'ring.",
            parse_mode="HTML",
        )
    finally:
        # Vaqtinchalik faylni xotiradan tozalaymiz
        if file_path:
            remove_file(file_path)
