# 🚀 N37 Telegram Multi-Tool & AI Bot

Ko'p funksiyali, zamonaviy va to'liq asinxron Telegram boti (**Python**, **aiogram 3.x**, **yt-dlp**, **Google Gemini AI**, **FFmpeg**, **Edge-TTS**, **Flux AI**).

---

## ⚡ Asosiy Imkoniyatlar

1. 📥 **Instagram Video Downloader**:
   - Reels, Post va IGTV videolarini yuqori sifatda yuklab beradi.
   - 50 MB gacha bo'lgan videolarni to'g'ridan-to'g'ri Telegram orqali yuboradi.
   - Yuklangan videoni bitta tugma bilan dumaloq video xabarga aylantirish mumkin.

2. ⚪ **4 burchak videolarni dumaloq qilish (Video Note / Kruglyash)**:
   - Galereyadan yoki Telegram orqali yuborilgan istalgan 4 burchak video, fayl yoki GIF animatsiyasini markazdan 1:1 kvadrat qilib qirqadi.
   - 480x480 o'lchamda haqiqiy Telegram dumaloq video xabari (video note) qilib qaytaradi.

3. 🤖 **Google Gemini AI Chat**:
   - Google Gemini modeli bilan o'zbek tilida tabiiy va samimiy suhbat.
   - Kontekst xotirasi (suhbat davomidagi savollarni eslab qoladi).
   - `/setkey` orqali shaxsiy Gemini API kalitini kiritish imkoniyati.

4. 🎙️ **Ovozli xabarlar (Mikrofon & Ovozli javob)**:
   - Foydalanuvchi mikrofondan yuborgan ovozli xabarni (Speech-to-Text) eshitib tushunadi.
   - Javobni foydalanuvchi xohishiga ko'ra **ovozli xabar (Telegram Voice)** yoki matn ko'rinishida taqdim etadi.
   - Tabiiy Microsoft Azure o'zbekcha ovozi (Edge-TTS) va Google TTS zaxirasi.

5. 🎨 **AI Rasm Generatsiya (Text-to-Image & Image-to-Image)**:
   - `/rasm <matn>` orqali ilg'or Flux AI modeli yordamida yangi rasmlar chizish.
   - Guruhda yoki shaxsiy chatda rasm yuborilganda, Gemini Vision tahlili orqali yangi badiiy variantlarni generatsiya qilish.

6. 👥 **Guruhlar uchun maxsus qoidalar**:
   - Guruh a'zolarining o'zaro suhbatiga aralashmaydi va spam qilmaydi.
   - Guruhda faqat botga **Reply** qilinganda, `@bot_username` deb chaqirilganda yoki buyruq berilganda javob beradi.

7. 📢 **Kanalga majburiy a'zolik (Obuna tekshiruvi)**:
   - Shaxsiy chatda botdan foydalanish uchun ma'lum kanalga a'zo bo'lish talabini o'rnatish mumkin (`/setchannel @kanal`).
   - «Kanalga a'zo bo'lish» va «Obunani tekshirish» interaktiv tugmalari.

---

## 📁 Loyiha Tuzilishi

```text
├── bot.py                  # Botni ishga tushiruvchi asosiy fayl
├── config.py               # Konfiguratsiya va muhit o'zgaruvchilari
├── requirements.txt        # Kerakli kutubxonalar ro'yxati
├── .env.example            # Muhit sozlamalari namunasi
├── .gitignore              # Git e'tibor bermaydigan fayllar
├── README.md               # Loyiha qo'llanmasi
├── handlers/               # Xabarlar va buyruqlar ishlovchilari
│   ├── start.py            # /start, /help, menyu va kanal tekshiruvi
│   ├── video_note.py       # 4 burchak videoni dumaloq qilish
│   ├── downloader.py       # Instagram video yuklovchi
│   └── ai.py               # AI matn, ovoz va rasm generatsiyasi
├── middlewares/            # O'rta dasturlar (Middleware)
│   └── subscription.py     # Majburiy obunani tekshiruvchi middleware
└── services/               # Yordamchi xizmatlar
    ├── downloader.py       # yt-dlp orqali Instagram yuklash
    ├── video_converter.py  # FFmpeg orqali dumaloq video konvertatsiyasi
    ├── ai_service.py       # Google Gemini AI xizmati
    ├── tts_service.py      # Edge-TTS va gTTS ovoz yaratish
    └── image_service.py    # Flux va Gemini Vision rasm generatsiyasi
```

---

## 🚀 O'rnatish va Ishga Tushirish

### 1. Loyihani yuklab olish
```bash
git clone https://github.com/norjongulm-boop/n37-telegram-bot.git
cd n37-telegram-bot
```

### 2. Virtual muhit yaratish va faollashtirish
```bash
# Virtual muhit yaratish
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate
```

### 3. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 4. Sozlamalarni kiritish
`.env.example` faylidan nusxa olib `.env` nomli fayl yarating:
```env
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
GEMINI_API_KEY=AIzaSy...
REQUIRED_CHANNEL=@sizning_kanalingiz
```

### 5. Botni ishga tushirish
```bash
python bot.py
```

---

## 📄 Litsenziya
Ushbu loyiha ochiq kodli bo'lib, ta'lim va shaxsiy foydalanish uchun mo'ljallangan.
