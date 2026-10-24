import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, Bot
from aiogram.enums import ChatType
from aiogram.types import TelegramObject, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import config

logger = logging.getLogger(__name__)


async def is_subscribed(bot: Bot, user_id: int, channel: str) -> bool:
    """Foydalanuvchi kanalga a'zo ekanligini tekshirish."""
    if not channel:
        return True

    channel_clean = channel.strip()
    if channel_clean.startswith("https://t.me/"):
        channel_clean = "@" + channel_clean.replace("https://t.me/", "").rstrip("/")

    try:
        member = await bot.get_chat_member(chat_id=channel_clean, user_id=user_id)
        # creator, administrator, member, restricted (agar a'zo bo'lsa)
        if member.status in ["creator", "administrator", "member"]:
            return True
        if member.status == "restricted" and getattr(member, "is_member", True):
            return True
        return False
    except Exception as e:
        logger.warning(f"Kanal a'zoligini tekshirishda xatolik ({channel_clean}): {e}")
        # Agar bot kanalga admin qilinmagan bo'lsa, foydalanuvchini bloklab qo'ymaslik uchun True qaytaramiz
        return True


def get_subscription_keyboard(channel: str) -> InlineKeyboardMarkup:
    """Kanalga a'zo bo'lish tugmasi."""
    channel_clean = channel.strip()
    if channel_clean.startswith("@"):
        url = f"https://t.me/{channel_clean[1:]}"
    elif channel_clean.startswith("https://t.me/"):
        url = channel_clean
    else:
        url = f"https://t.me/{channel_clean}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=url)],
            [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subscription")],
        ]
    )


class SubscriptionMiddleware(BaseMiddleware):
    """Faqat shaxsiy (lichka) chatlarda majburiy obunani tekshiruvchi middleware."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        channel = getattr(config, "REQUIRED_CHANNEL", "").strip()
        if not channel:
            return await handler(event, data)

        bot: Bot = data.get("bot")

        # 1. CallbackQuery holati
        if isinstance(event, CallbackQuery):
            if event.data == "check_subscription":
                # Tekshirish tugmasi bosilganda to'siqsiz handlerga o'tkazamiz
                return await handler(event, data)

            if event.message and event.message.chat.type == ChatType.PRIVATE:
                user_id = event.from_user.id
                subscribed = await is_subscribed(bot, user_id, channel)
                if not subscribed:
                    await event.answer("⚠️ Botdan foydalanish uchun avval kanalimizga a'zo bo'ling!", show_alert=True)
                    return

            return await handler(event, data)

        # 2. Message holati
        if isinstance(event, Message):
            # Guruhlarni tekshirmaymiz (faqat shaxsiy chatda)
            if event.chat.type != ChatType.PRIVATE:
                return await handler(event, data)

            # /setchannel buyrug'i uchun tekshiruvni chetlab o'tamiz
            if event.text and event.text.startswith("/setchannel"):
                return await handler(event, data)

            user_id = event.from_user.id
            subscribed = await is_subscribed(bot, user_id, channel)

            if not subscribed:
                text = (
                    "⚠️ <b>Botdan to'liq foydalanish uchun rasmiy kanalimizga a'zo bo'ling!</b>\n\n"
                    "Kanalga a'zo bo'lib, quyidagi <b>«✅ Obunani tekshirish»</b> tugmasini bosing:"
                )
                await event.answer(text, reply_markup=get_subscription_keyboard(channel), parse_mode="HTML")
                return

        return await handler(event, data)
