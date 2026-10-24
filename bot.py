import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from handlers.start import router as start_router
from handlers.video_note import router as video_note_router
from handlers.downloader import router as downloader_router
from handlers.ai import router as ai_router
from middlewares.subscription import SubscriptionMiddleware

# Windows konsolida UTF-8 (emojilar) xatosiz chiqishi uchun
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Log sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def main():
    if not BOT_TOKEN:
        logger.error(
            "XATOLIK: BOT_TOKEN aniqlanmadi!\n"
            "Iltimos, '.env' faylini ochib, @BotFather bergan tokenni kiriting:\n"
            "BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        )
        sys.exit(1)

    # Bot va Dispatcher yaratish
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Majburiy obunani faqat shaxsiy (lichka) chatlarda tekshiruvchi middleware
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())

    # Routerlarni ulash (tartibi muhim: start -> video_note -> downloader -> ai)
    dp.include_router(start_router)
    dp.include_router(video_note_router)
    dp.include_router(downloader_router)
    dp.include_router(ai_router)

    # Eski kutilayotgan update'larni tozalash
    await bot.delete_webhook(drop_pending_updates=True)

    bot_info = await bot.get_me()
    logger.info(f"Bot muvaffaqiyatli ishga tushdi: @{bot_info.username}")
    print(f"\n==========================================")
    print(f"🚀 Bot ishlamoqda: @{bot_info.username}")
    print(f"To'xtatish uchun: Ctrl + C")
    print(f"==========================================\n")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Dastur to'xtatildi.")
