# 🧩 Userbot modullari — yozish qo'llanmasi

> Bu fayl **avtomatik yaratiladi** (`userbot_docs.py`) va koddagi o'zgarishlar bilan birga yangilanadi — qo'lda tahrirlamang.
> Loyiha `v2.3` · userbot `v2.4`

## 1. Modul nima?

Oddiy `.py` fayl. Botga yuboriladi (🤖 Userbot → 🧩 Modullar → 📥 Modul qo'shish) yoki chatda faylga reply qilib `.mod add` yoziladi.
Fayl **ishga tushirilmasdan** `ast` bilan tekshiriladi (nom, tavsif, buyruqlar, config, importlar); siz tasdiqlagach o'rnatiladi.

⚠️ Modul bot jarayonida **to'liq huquq** bilan ishlaydi. Xavfli importlar (`asyncio.subprocess`, `builtins`, `ctypes`, `importlib`, `marshal`, `multiprocessing`, `os`, `pickle`, `pty`, `shutil`, `signal`, `socket`, `subprocess`, `sys`) o'rnatishdan oldin alohida ogohlantiriladi. Faqat ishonchli kodni o'rnating.

## 2. Metadata (fayl tepasida, oddiy literal sifatida)

| O'zgaruvchi | Holat | Tavsif |
|---|---|---|
| `NAME` | majburiy | `str` — `^[a-z][a-z0-9_]{1,23}$` (a-z, 0-9, _; harf bilan boshlanadi; 2..24 belgi). Fayl nomi emas, shu nom ishlatiladi. |
| `DESCRIPTION` | majburiy | `str` — modul tavsifi (≤300 belgi ko'rsatiladi). |
| `VERSION` | ixtiyoriy | `str` — standart `"1.0"` (≤16 belgi). Qayta yuklaganda eski config qiymatlari saqlanadi. |
| `AUTHOR` | ixtiyoriy | `str` — muallif (≤64 belgi). |
| `CONFIG` | ixtiyoriy | `dict` — `.config` va bot tugmalari bilan boshqariladigan o'zgaruvchilar (ko'pi bilan 30 ta). |
| `COMMANDS` | ixtiyoriy | `dict` — modul buyruqlari (ko'pi bilan 30 ta). Har biri uchun `async def cmd_<nom>(e, args, ctx)` shart. |
| `REQUIREMENTS` | ixtiyoriy | `list[str]` — pip kutubxonalari, masalan `["pillow", "pytz>=2023"]` (ko'pi bilan 10 ta). O'rnatishda **avtomatik o'rnatiladi**, modul o'chirilsa **o'zi ham o'chadi** (bo'lim 9). |

Metadata **faqat literal** (matn/son/dict/list/tuple) bo'lishi shart — kod ishga tushmasdan o'qiladi, shuning uchun `NAME = get_name()` kabi yozib bo'lmaydi.
Maksimal fayl hajmi: **256 KB**, kodlash: **UTF-8**.

## 3. CONFIG — `.config` orqali boshqariladigan o'zgaruvchilar

Kalit qoidasi: `^[a-z][a-z0-9_]{0,23}$`. Tur `default` qiymatdan aniqlanadi: `bool`, `int`, `float`, `str` (o'zgaruvchi qiymati `str` ≤ 500 belgi).

```python
CONFIG = {
    "greeting": {"default": "Salom", "desc": "Salom matni"},                    # to'liq shakl
    "repeat":   {"default": 1, "desc": "Necha marta", "min": 1, "max": 5},      # int, chegara bilan
    "mode":     {"default": "a", "desc": "Rejim", "choices": ["a", "b"]},       # variantlardan biri
    "loud":     (False, "Qisqa shakl: (default, tavsif)"),                        # bool
    "limit":    10,                                                              # eng qisqa shakl
}
```

| Kalit | Ma'nosi |
|---|---|
| `default` | majburiy; turni belgilaydi (`type` bilan majburan ko'rsatish ham mumkin) |
| `desc` | tavsif (≤200 belgi) |
| `min` / `max` | `int`/`float` uchun chegara |
| `choices` | ruxsat etilgan qiymatlar (1..20 ta) |

Modul ichida: `ctx.cfg["repeat"]` — doim **joriy** qiymat. Foydalanuvchi o'zgartiradi:

- `.config` — config bor modullar ro'yxati
- `.config modul` — barcha o'zgaruvchilar, joriy qiymat, tur va tavsif
- `.config modul kalit` — bitta qiymat
- `.config modul kalit qiymat` — o'rnatish (`-r` — standartga qaytarish)
- bot: 🤖 Userbot → 🧩 Modullar → modul (bool — bir bosishda, qolganlari — qiymat yozish)

`bool` uchun qabul qilinadi: `+, 1, ha, ok, on, true, yes` / `-, 0, false, no, off, yo'q, yoq`.
Noto'g'ri qiymat (tur, chegara, variant) rad etiladi va eski qiymat saqlanadi. Config va `ctx.data` restart/ZIP yangilanishdan keyin ham saqlanadi.

## 4. COMMANDS — modul buyruqlari

```python
COMMANDS = {"hello": {"desc": "Salom yozadi", "usage": ".hello [ism]"}, "roll": "Zar tashlaydi"}

async def cmd_hello(e, args, ctx):      # e — Telethon hodisasi, args — buyruqdan keyingi matn
    await e.edit(f"{ctx.cfg['greeting']}, {args}!", parse_mode=None)
```

- Har bir `COMMANDS` kaliti uchun **`async def cmd_<nom>(e, args, ctx)`** bo'lishi shart (aks holda o'rnatishda rad etiladi).
- Buyruq faqat **o'zingiz yozganingizda** ishlaydi (istalgan chatda), nuqta bilan boshlanadi.
- Buyruq 120 soniyadan oshsa to'xtatiladi; xato userbotni yiqitmaydi — chatda `❌ [modul] ...` ko'rinadi.
- Ikki modul bitta buyruqni bo'lisha olmaydi; o'rnatilgan buyruq nomlarini ishlatib bo'lmaydi (bo'lim 7).

## 5. Hooklar (ixtiyoriy, hammasi `async def`)

| Imzo | Qachon |
|---|---|
| `async def on_load(ctx)` | Modul yuklanganda (userbot ishga tushganda, `.mod on/reload/add` dan keyin). Xato bersa modul yuklanmaydi (🔴). |
| `async def on_unload(ctx)` | Modul o'chirilganda/qayta yuklanganda. Resurslarni shu yerda yoping. `ctx.on` handlerlari va `ctx.spawn` vazifalari o'zi tozalanadi. |
| `async def on_message(e, ctx)` | Har bir KIRUVCHI xabar uchun (`e` — Telethon NewMessage hodisasi). Xatosi boshqa modullarga tegmaydi. |
| `async def on_config(ctx, key, value)` | `.config` yoki bot tugmasi bilan o'zgaruvchi o'zgarganda (`value` — allaqachon turga o'tkazilgan). |

Vaqt limitlari: `on_load` 30s · `on_message` 30s · `on_unload`/`on_config` 10s.

## 6. `ctx` — modulga beriladigan kontekst

| Nomi | Turi | Tavsif |
|---|---|---|
| `ctx.uid` | atribut | Userbot egasining Telegram ID si. |
| `ctx.name` | atribut | Modulning NAME qiymati. |
| `ctx.meta` | atribut | Tahlil qilingan metadata (name, description, version, author, config, commands, hooks...). |
| `ctx.cfg` | atribut | Config qiymatlari: `ctx.cfg["kalit"]` / `ctx.cfg.get("kalit", x)` / `ctx.cfg.all()`. Har safar joriy qiymatni beradi — `.config` bilan o'zgartirilsa darhol ko'rinadi. |
| `ctx.client` | xossa | Telethon TelegramClient (userbot hisobi nomidan). |
| `ctx.data` | xossa | Doimiy xotira (dict, JSON-ga o'tadigan qiymatlar). O'zgartirgach `ctx.save()` chaqiring; restart/ZIP yangilanishdan keyin ham saqlanadi. |
| `ctx.emoji(emoji_id: int, fallback: str = '⭐') -> str` | metod | `ctx.emoji(ID, "⚡️")` — premium emoji uchun `<tg-emoji>` HTML belgisini qaytaradi; `parse_mode=ctx.html` bilan yuboriladigan matn ichiga qo'yiladi. |
| `ctx.html` | xossa | `parse_mode=ctx.html` — HTML (<b>, <i>, <code>, <a href>...) VA premium emoji: `<tg-emoji emoji-id="ID">⚡️</tg-emoji>`. Masalan: `await e.edit(f'{ctx.emoji(5368324170671202286, "⚡️")} Ping: <b>{ms}</b> ms', parse_mode=ctx.html)`. Premium bo'lmagan joyda ichidagi oddiy emoji ko'rinadi. O'zgaruvchan matnlarni `html.escape()` bilan o'tkazing. |
| `ctx.log(*a) -> None` | metod | `ctx.log(...)` — bot logiga `[modul:nom]` belgisi bilan yozadi. |
| `ctx.me` | xossa | Userbot egasi (Telethon User). |
| `ctx.on(event)` | metod | Dekorator: `@ctx.on(events.NewMessage(...))` — Telethon handleri; modul o'chirilganda avtomatik olib tashlanadi. |
| `ctx.save() -> None` | metod | `ctx.data` ni diskka yozadi (hajm chegarasi — 64 KB). |
| `ctx.spawn(coro) -> asyncio.Task` | metod | `ctx.spawn(coro)` — fon vazifa; modul o'chirilganda bekor qilinadi, xatosi userbotni yiqitmaydi. |

`ctx.data` hajmi ko'pi bilan **64 KB**. Modul o'chirilsa/qayta yuklansa `ctx.on` handlerlari va `ctx.spawn` vazifalari avtomatik tozalanadi.

### Formatlash va PREMIUM emoji

- Oddiy matn: `await e.edit(text, parse_mode=None)`.
- HTML (`<b>`, `<i>`, `<code>`, `<pre>`, `<a href>`) va **premium (custom) emoji** uchun: `parse_mode=ctx.html`. Premium emoji `<tg-emoji emoji-id="ID">⚡️</tg-emoji>` ko'rinishida yoziladi (ichidagi oddiy emoji — fallback), yoki `ctx.emoji(ID, "⚡️")` bilan hosil qilinadi.
- Dinamik qiymatlarni `html.escape(str(v))` dan o'tkazing (HTML buzilmasligi uchun).
- Userbot hisobi **Telegram Premium** bo'lishi kerak; bo'lmasa (yoki klient ko'rsatolmasa) fallback emoji ko'rinadi.
- Emoji ID ni olish: AI bo'limida («✏️ O'zgartirish» yoki yangi modul) botga **premium emoji yozing** — bot ID ni o'zi ushlab AI ga beradi va modulda aynan o'sha emoji saqlanadi.

```python
async def cmd_ping(e, args, ctx):
    t = time.perf_counter()
    await e.edit("…", parse_mode=None)
    ms = round((time.perf_counter() - t) * 1000)
    await e.edit(f'{ctx.emoji(5368324170671202286, "⚡️")} Ping: <b>{ms}</b> ms', parse_mode=ctx.html)
```

## 7. Band buyruq nomlari

Quyidagilarni modul ishlata olmaydi: `.afk`, `.calc`, `.clock`, `.config`, `.del`, `.docs`, `.font`, `.fonts`, `.help`, `.id`, `.info`, `.mod`, `.mods`, `.note`, `.notes`, `.ping`, `.remind`, `.save`, `.stats`, `.time`, `.type`, `.unafk`, `.vps`.

## 8. Userbot buyruqlari (hozirgi `.help`)

**Userbot buyruqlari** (istalgan chatda o'zingiz yozasiz)

`.ping` · `.time` · `.id` · `.info` · `.stats` · `.vps`

`.calc 2+2*3` — kalkulyator

`.type matn` — yozilayotgandek animatsiya

`.del N` — oxirgi N ta xabaringizni o'chirish

`.afk sabab` / `.unafk` — AFK avtojavob (restartdan keyin ham saqlanadi)

`.remind 10m matn` — «Saqlangan xabarlar»ga eslatma (`30s 10m 2h 1d 1h30m` yoki `18:30`)

`.note add nom matn` · `.note nom` · `.note del nom` · `.notes`

`.save` — reply qilingan xabarni «Saqlangan»ga yuborish

`.font nom matn` · `.fonts` — matnni chiroyli shriftda yozish

**Modullar** (.py)

`.mod` · `.mod info|on|off|reload|del nom` · `.mod add` (.py faylga reply)

`.mod libs` — modullar o'rnatgan kutubxonalar (avtomatik o'rnatiladi, modul o'chsa o'zi ham o'chadi) · `.mod libs fix nom`

`.config` · `.config modul` · `.config modul o'zgaruvchi qiymat` (`-r` — standart)

`.docs` — modul yozish qo'llanmasi + o'rnatilgan modullar (fayl, «Saqlangan»ga) · `.docs modul` — bitta modul

**Profil soati**

`.clock on|off` · `.clock fonts` · `.clock font nom|№`

`.clock fmt №|shablon` — `{t}` vaqt, `{e}` 🕒 (soatga mos), `{d}` sana

`.clock where last|first|bio` — familiya / ism / bio

`.clock tz Asia/Tashkent` — vaqt zonasi

## 9. Boshqaruv

| Buyruq | Vazifa |
|---|---|
| `.mod` | modullar ro'yxati (🟢 yuklangan · 🟡 kutilmoqda · ⚪ o'chiq · 🔴 xato) |
| `.mod add` | `.py` faylga reply — o'rnatish/yangilash |
| `.mod info\|on\|off\|reload\|del nom` | ma'lumot / yoqish / o'chirish / qayta yuklash / butunlay olib tashlash |
| `.mod libs [nom]` | modullar o'rnatgan kutubxonalar ro'yxati |
| `.mod libs fix nom` | modulning yetishmayotgan kutubxonalarini o'rnatib, qayta yuklash (bot: 📚 Kutubxonalarni tekshirish) |
| `.docs` | shu docs (o'rnatilgan modullaringiz bilan) «Saqlangan xabarlar»ga fayl sifatida |
| `.docs nom` | bitta modul haqida qisqacha |
| bot: 🧩 Modullar → 🤖 AI bilan yaratish | DeepSeek yordamida modul yozdirish (API kalit Telegramda kiritiladi; bu qo'llanma AI ga suhbatda bir marta yuboriladi) |

Fayllar: `USERBOT_DIR/modules/<id>/<nom>.py` — ZIP yangilash o'chirmaydi. Yoqilgan modullar restartdan keyin o'zi yuklanadi.

### Kutubxonalar (pip) — avtomatik

- **O'rnatishda:** `REQUIREMENTS` dagi talablar + kodda `import` qilingan, lekin o'rnatilmagan kutubxonalar (`PIL` → `pillow`, `cv2` → `opencv-python-headless`, `bs4` → `beautifulsoup4` ...) botning o'z venv'iga pip bilan **o'zi o'rnatiladi**. Tasdiqlash ekranida ro'yxat ko'rsatiladi. O'rnatilmasa (nom xato, tarmoq yo'q) modul saqlanmaydi va sabab ko'rsatiladi.
- **Yuklashda:** `ModuleNotFoundError` chiqsa (eski modul, venv qayta yaratilgan, kod ichida dinamik import) bot kutubxonani o'zi o'rnatib qayta urinadi.
- **O'chirishda:** modul o'chirilsa (`.mod del`, bot tugmasi, userbotni o'chirish) **aynan u o'rnatgan** kutubxonalar (bog'liqliklari bilan) o'chadi. Boshqa modul ishlatayotgani qoladi (egalik o'sha modulga o'tadi). Botning o'z kutubxonalari (`requirements.txt`) hech qachon o'chirilmaydi va talab bilan yangilanib buzilmaydi.
- **Qoidalar:** `REQUIREMENTS` faqat `nom` yoki `nom>=versiya` (URL, fayl yo'li, pip parametrlari mumkin emas); modul koddan pip chaqirmasin. Import nomi pip nomidan farq qilsa (`PIL` ≠ `pillow`) — `REQUIREMENTS` ga pip nomini yozing. Imkon qadar standart kutubxona, `aiohttp`, `telethon` ishlating.

## 10. Xato bo'lsa

- **«NAME majburiy»**, **«DESCRIPTION majburiy»** — metadata yo'q yoki literal emas.
- **«COMMANDS da «x» bor, lekin async def cmd_x yo'q»** — funksiya nomi `cmd_` + buyruq nomi bo'lishi kerak va `async` bo'lishi shart.
- **«.x buyrug'i «boshqa» modulida band»** — buyruq nomini o'zgartiring.
- 🔴 holatda modul yuklanmagan: sababi `.mod info nom` yoki bot tugmalarida ko'rinadi; tuzatib qayta yuboring yoki `.mod reload nom`.

## 11. Namunalar (`modules_example/`)

### `example.py` — example v1.0: Namuna modul: salomlashish va zar tashlash

Buyruqlar: `.hello` `.roll` · config: `greeting`, `repeat`, `style`, `emoji` · hooklar: on_load

```python
"""Namuna modul. Botga yuboring: 🤖 Userbot → 🧩 Modullar → 📥 Modul qo'shish (yoki .py faylga reply qilib `.mod add`).
Keyin: .hello  .roll 20  .config example  .config example greeting Assalomu alaykum
"""
import random

NAME = "example"
DESCRIPTION = "Namuna modul: salomlashish va zar tashlash"
VERSION = "1.0"
AUTHOR = "VPS Manager"

CONFIG = {
    "greeting": {"default": "Salom", "desc": "Salom matni"},
    "repeat": {"default": 1, "desc": "Salom necha marta", "min": 1, "max": 5},
    "style": {"default": "oddiy", "desc": "Ko'rinish", "choices": ["oddiy", "katta"]},
    "emoji": (True, "Emoji qo'shish"),
}
COMMANDS = {
    "hello": {"desc": "Salom yozadi", "usage": ".hello [ism]"},
    "roll": {"desc": "Zar tashlaydi", "usage": ".roll [n]"},
}


async def on_load(ctx):
    ctx.data["loads"] = ctx.data.get("loads", 0) + 1     # ctx.data — doimiy xotira (restartdan keyin ham saqlanadi)
    ctx.save()
    ctx.log("yuklandi, jami:", ctx.data["loads"])


async def cmd_hello(e, args, ctx):
    text = " ".join([f"{ctx.cfg['greeting']}, {args or 'do‘stim'}!"] * ctx.cfg["repeat"])
    if ctx.cfg["style"] == "katta":
        text = text.upper()
    await e.edit(text + (" 👋" if ctx.cfg["emoji"] else ""), parse_mode=None)


async def cmd_roll(e, args, ctx):
    n = int(args) if args.isdigit() and 2 <= int(args) <= 1000 else 6
    await e.edit(f"🎲 {random.randint(1, n)} / {n}", parse_mode=None)
```

<!-- sha:4459b1b9370d -->
