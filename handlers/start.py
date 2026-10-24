from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton

router = Router()


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Asosiy menyu tugmalari."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🤖 AI Chat"), KeyboardButton(text="⚪ Dumaloq Video")],
            [KeyboardButton(text="📥 Instagram Yuklovchi"), KeyboardButton(text="🔑 Gemini API Key")],
        ],
        resize_keyboard=True,
    )


@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start(message: Message):
    user_name = message.from_user.first_name if message.from_user else "Foydalanuvchi"
    text = (
        f"Assalomu alaykum, <b>{user_name}</b>! 🎬🤖\n\n"
        "Men ko'p funksiyali yordamchi botman:\n\n"
        "1. 🤖 <b>AI Chat (Google Gemini):</b> Istalgan savolingizni bering, sun'iy intellekt javob beradi.\n"
        "2. ⚪ <b>Dumaloq Video:</b> 4 burchak videoni Telegram dumaloq video xabariga (kruglyash) aylantirib beraman.\n"
        "3. 📥 <b>Instagram Video:</b> Reels yoki Post havolasini yuborsangiz, videoni yuklab beraman.\n"
        "4. 🔑 <b>Gemini API Key:</b> O'z shaxsiy Google Gemini API kalitingizni ulab, undan to'liq foydalanishingiz mumkin.\n\n"
        "<i>Quyidagi menyudan kerakli bo'limni tanlang yoki to'g'ridan-to'g'ri video/savol yuboring! 👇</i>"
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "<b>📖 Botdan foydalanish qo'llanmasi:</b>\n\n"
        "🤖 <b>1. AI Chat (Sun'iy intellekt):</b>\n"
        "Botga istalgan matn yoki savolingizni yuboring, Google Gemini AI o'zbek tilida javob beradi. Suhbat tarixini tozalash uchun /clear buyrug'idan foydalaning.\n\n"
        "⚪ <b>2. 4 burchak videoni dumaloq qilish:</b>\n"
        "Galereyangizdan istalgan videoni botga yuboring. Bot uni 1:1 formatda qirqib, video note qilib qaytaradi (maksimal 20 MB / 60 soniya).\n\n"
        "📥 <b>3. Instagram video yuklash:</b>\n"
        "Instagram'dan nusxalangan havolani yuboring, video tezda yuklanadi.\n\n"
        "🔑 <b>4. Gemini API Key:</b>\n"
        "O'z API kalitingizni o'rnatish uchun /setkey buyrug'idan foydalaning."
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")


@router.message(F.text == "⚪ Dumaloq Video")
async def btn_round_video(message: Message):
    text = (
        "⚪ <b>Dumaloq video (Video Note) bo'limi:</b>\n\n"
        "Menga istalgan 4 burchak video yoki GIF yuboring!\n"
        "Men uni avtomatik tarzda markazdan 1:1 kvadrat qilib qirqib, "
        "Telegram dumaloq videosi (kruglyash) ko'rinishida sizga jo'nataman. 🚀\n\n"
        "⚠️ <i>Eslatma: Video hajmi 20 MB dan oshmasligi va davomiyligi 60 soniyagacha bo'lishi maqsadga muvofiq.</i>"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "📥 Instagram Yuklovchi")
async def btn_instagram_downloader(message: Message):
    text = (
        "📥 <b>Instagram Video Yuklovchi bo'limi:</b>\n\n"
        "Instagram Reels, Post yoki Video <b>havolasini (linkini)</b> yuboring, "
        "men uni yuqori sifatda yuklab beraman.\n\n"
        "<i>Namuna:</i>\n<code>https://www.instagram.com/reel/C8x...</code>\n\n"
        "💡 <i>Yuklangan videoni ham bitta tugma orqali dumaloq video xabarga aylantirish mumkin!</i>"
    )
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "check_subscription")
async def handle_check_subscription(callback: CallbackQuery, bot: Bot):
    """Foydalanuvchi kanalga a'zo bo'lganini qayta tekshirish."""
    import config
    from middlewares.subscription import is_subscribed

    channel = getattr(config, "REQUIRED_CHANNEL", "").strip()
    if not channel:
        await callback.answer("✅ Obuna talab etilmaydi!", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        return

    subscribed = await is_subscribed(bot, callback.from_user.id, channel)
    if subscribed:
        await callback.answer("✅ Obuna tasdiqlandi! Rahmat.", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "🎉 <b>Xush kelibsiz!</b> Endi botning barcha imkoniyatlaridan to'liq foydalanishingiz mumkin.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML",
        )
    else:
        await callback.answer(
            "⚠️ Siz hali kanalga a'zo bo'lmadingiz! Iltimos, avval kanalga kiring va 'Qo'shilish' tugmasini bosing.",
            show_alert=True,
        )


@router.message(Command("setchannel"))
async def handle_setchannel(message: Message):
    """Majburiy a'zolik kanalini o'rnatish: /setchannel @kanal_nomi"""
    import config
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        curr = getattr(config, "REQUIRED_CHANNEL", "") or "o'rnatilmagan"
        await message.reply(
            f"📢 <b>Hozirgi kanal:</b> <code>{curr}</code>\n\n"
            "Yangi kanal o'rnatish uchun quyidagicha yuboring:\n"
            "<code>/setchannel @sizning_kanalingiz</code>\n\n"
            "⚠️ <i>Eslatma: Bot ushbu kanalda <b>Administrator</b> bo'lishi kerak!</i>",
            parse_mode="HTML",
        )
        return

    new_channel = args[1].strip()
    config.update_required_channel(new_channel)
    await message.reply(
        f"✅ <b>Kanal muvaffaqiyatli saqlandi:</b> <code>{new_channel}</code>\n\n"
        "Endi shaxsiy chatdagi foydalanuvchilar ushbu kanalga a'zo bo'lmaguncha botdan foydalana olmaydi.\n"
        "⚠️ <i>Botni kanalingizga administrator qilib qo'shishni unutmang!</i>",
        parse_mode="HTML",
    )
