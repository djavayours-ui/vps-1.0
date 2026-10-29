"""Loyiha versiyasi.

QOIDA (dasturchi va AI uchun): har yangilanishda versiya 0.1 ga oshiriladi: 1.0 → 1.1 → 1.2 → …
Yangilashdan oldin: 1) VERSION ni ko'taring, 2) CHANGELOG ga YANGI qatorni eng tepaga qo'shing.
Versiya botning bosh menyu xabarida «--version X.Y» ko'rinishida chiqadi (bot.py → START_TEXT).
"""
VERSION = "2.3"

# CHANGELOG (yangisi tepada)
# 2.3 — 💎 PREMIUM EMOJI modullarda: AI bo'limida (yangi modul / ✏️ O'zgartirish) premium emoji yozsangiz, bot uning ID sini ushlab AI ga
#       `<tg-emoji emoji-id="..">⚡️</tg-emoji>` ko'rinishida beradi va modulda aynan shu emoji saqlanadi. Yangi: userbot_emoji.py (Telethon uchun HTML+custom emoji parser),
#       `ctx.html` (parse_mode) va `ctx.emoji(ID, "⚡️")`. AI prompt va docs («Formatlash va PREMIUM emoji») moslandi. Userbot hisobi Premium bo'lishi kerak.
# 2.2 — 🖼 AI bo'limida RASM + MATN: modul yaratish va ✏️ O'zgartirish (AI) da rasm (skrinshot, namuna, xato; albom ≤4 ta) izoh bilan BIRGA yuboriladi.
#       Rasm izohsiz kelsa saqlanadi va keyingi matnga qo'shiladi. Rasmli so'rovlar vision modelida (DEEPSEEK_VISION_MODEL, standart «deepseek-flash»)
#       bajariladi; rasm faqat shu so'rov uchun — keyin suhbat tarixidan olib tashlanadi.
# 2.1 — Modul ekrani: ✏️ O'zgartirish (AI) — nimani o'zgartirish kerakligini yozasiz, AI joriy kodni ko'rib TO'LIQ yangilangan modulni qaytaradi (NAME o'zgarmaydi),
#       tasdiqlasangiz yangilanadi (config/ma'lumotlar saqlanadi). ♻️ Qayta yuklash endi — shu modulning yangi .py faylini yuborasiz, eski fayl almashtiriladi.
#       📥 Yuklab olish — modul .py fayli botga yuboriladi. Modul ekraniga o'tilganda kutilayotgan holatlar (fayl/AI so'rovi) bekor qilinadi.
# 2.0 — Userbot v2.4: 📚 MODUL KUTUBXONALARI AVTOMATIK. Modul o'rnatilganda (qo'lda, `.mod add`, AI yaratgan) REQUIREMENTS va kodda import qilingan
#       yetishmayotgan kutubxonalar (PIL→pillow, cv2→opencv ...) venv'ga pip bilan o'zi o'rnatiladi; modul yuklanganda ModuleNotFoundError bo'lsa ham o'zi
#       o'rnatib qayta urinadi. Modul (yoki userbot) o'chirilsa — aynan u o'rnatgan kutubxonalar (bog'liqliklari bilan) o'chadi; boshqa modul ishlatayotgani
#       qoladi. Bot kutubxonalari (requirements.txt) himoyalangan (constraints). Yangi: userbot_libs.py, REQUIREMENTS metadata, `.mod libs [fix nom]`,
#       bot: 📚 Kutubxonalarni tekshirish, tasdiqlash/o'chirish ekranlarida kutubxonalar ro'yxati; AI prompt va docs yangilandi.
# 1.9 — Userbot v2.3: 🤖 AI BILAN MODUL YARATISH (🧩 Modullar → 🤖 AI bilan yaratish, DeepSeek). API kalit Telegramda kiritiladi (xabar o'chiriladi,
#       /models bilan tekshiriladi). Oddiy tilda so'raladi → AI modul yozadi → kod ISHGA TUSHIRILMASDAN tekshiriladi (ast, imzolar, buyruq to'qnashuvi),
#       xato bo'lsa AI ga qaytarilib o'zi tuzatadi → fayl + tahlil ko'rsatiladi → ✅ bo'lsa o'rnatiladi. Suhbat saqlanadi (✏️ O'zgartirish).
#       📖 Docs tugmasi ✅/❌: ✅ — qo'llanma AI ga suhbatda FAQAT BIR MARTA yuboriladi va tarixda qoladi; ❌ — yuborilmaydi.
#       Yangi: userbot_ai.py (mantiq), bot_ai.py (UI), userbot_core.mod_check/ai_cfg/ai_set, userbot_docs.build_for_ai.
# 1.8 — Userbot v2.2: 📖 MODUL DOCS. Modul yozish qo'llanmasi KODDAN avtomatik yasaladi (userbot_docs.py): metadata, CONFIG shakllari,
#       hooklar, ctx API, band buyruqlar, namunalar + foydalanuvchining o'rnatilgan modullari (nom, tavsif, buyruqlar, config o'zgaruvchilari
#       va joriy qiymatlar, holat). Modul qo'shilsa/o'chirilsa/config o'zgarsa/holat o'zgarsa va bot ishga tushganda (ZIP yangilashdan keyin ham)
#       yangilanadi. `.docs` / `.docs modul` buyruqlari, botda 🧩 Modullar → 📖 Docs. Fayl: docs/MODULES.md va USERBOT_DIR/docs/<id>/MODULES.md.
#       Chegara va vaqt limitlari userbot_mods.py dagi konstantalarga ko'chirildi (docs va kod bir manbadan).
# 1.7 — Userbot v2.1: 🧩 MODUL TIZIMI. .py modullar (NAME, DESCRIPTION, CONFIG, COMMANDS) bot orqali yoki `.mod add` bilan o'rnatiladi;
#       kod ishga tushirilmasdan tekshiriladi (ast), xavfli importlar ko'rsatiladi; `.config modul kalit qiymat` va bot tugmalari bilan
#       boshqariladi (str/int/float/bool, min/max/choices); modullar restart/ZIP yangilanishdan keyin o'zi yuklanadi; ctx.data doimiy xotira.
# 1.6 — Userbot v2.0: restart / ZIP yangilash / reboot'dan keyin userbotlar o'zi ko'tariladi va TO'XTAGAN JOYIDAN davom etadi
#       (supervisor: ulanish uzilsa qayta ulaydi; soat, AFK, shrift, zona saqlanadi; Stop bosilgan bo'lsa o'chiq qoladi; sessiya .bak nusxasi).
#       Profil soati: 14 xil shrift, joyi (familiya/ism/bio), 8 shablon (🕒 soatga mos emoji), vaqt zonasi — bot tugmalari va .clock buyruqlari.
#       Yangi buyruqlar: .font/.fonts, .remind, .note/.notes, .save, .info, .stats; AFK guruhda ham (mention).
# 1.5 — Userbot o'rnatish: kod QAYERGA yuborilgani aniq ko'rsatiladi (ilova/SMS/qo'ng'iroq/email), kelmasa «qayta yuborish» (SMS/qo'ng'iroq)
#       tugmasi, 📷 QR bilan kirish (kodsiz — VPS IP da kod kelmaganda), raqamni almashtirish, aniq xato turlari. Yangi kutubxona: segno.
# 1.4 — Bot UI: /buyruqlar olib tashlandi (faqat /start qoldi), hammasi inline tugmalarda: 🖥 Terminal (tayyor buyruq tugmalari bilan),
#       ♻️ Qayta yuklash, 🔎 Boshqa xizmat; bosh menyuda jonli CPU/RAM/Disk; alert xabarlarida AI fix/Log/Restart tugmalari;
#       umumiy matn/ZIP handlerlari boshqa bo'limlarning xabarini yutmasligi uchun holat filtrlari qo'shildi.
# 1.3 — «Conflict» xatosi tuzatildi: bitta nusxa himoyasi (instance.py), bot o'zini ZIP bilan yangilaganda o'zini o'ldirmaydi
#       (selfupdate.py: tashqi qayta ishga tushirish + ishlamasa avtomatik eski kodga qaytish), cloudflared chiqishda yopiladi.
# 1.2 — 🤖 Userbot bo'limi (userbot v1.0, Telethon): bot ichidan o'rnatish ustasi (API ID → API HASH → telefon → kod xxx.xx → 2FA),
#       Start/Stop/Restart, profil soati, .ping/.calc/.afk/.vps/... buyruqlari, sessiya loyiha papkasidan tashqarida (chmod 600).
# 1.1 — cloudflared apt'da yo'q: topilmasa bot rasmiy binarni o'zi yuklaydi; xato xabaridagi noto'g'ri apt buyrug'i tuzatildi.
# 1.0 — ZIP nomi o'xshash ilovani yangilaydi (nusxa yaratmaydi), venv avtomatik, .env.example dan kalitlar +
#       to'ldirish ustasi, rollback olib tashlandi (xatoda eski kod avtomatik tiklanadi, muvaffaqiyatda zaxira o'chadi),
#       cloudflared tunnel (http2, ulangach URL yuboriladi, /panel), AdminOnly/appctl nom xatolari tuzatildi,
#       port band bo'lsa keyingi bo'sh portni oladi.
