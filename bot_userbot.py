"""Bot: 🤖 Userbot bo'limi — o'rnatish ustasi (API ID → API HASH → telefon → kod yoki QR → 2FA) va boshqaruv."""
import asyncio, io, re, time

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import BaseFilter
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton as IB, Message
from telethon.errors import (ApiIdInvalidError, FloodWaitError, PasswordHashInvalidError, PhoneCodeExpiredError,
                             PhoneCodeInvalidError, PhoneNumberBannedError, PhoneNumberFloodError,
                             PhoneNumberInvalidError, SessionPasswordNeededError)
from telethon.tl.functions.auth import ResendCodeRequest

import userbot_core as ub
import userbot_libs as L
import userbot_mods as M
from common import B, K, edit, esc

router = Router()
SETUP: dict[int, dict] = {}     # uid -> {"step", "client", "api_id", "api_hash", "phone", "hash", "ts"}
TTL = 600                       # o'rnatish bosqichi 10 daqiqa
MODWAIT: dict[int, float] = {}  # uid -> .py fayl kutilmoqda (vaqt)
MODPEND: dict[int, dict] = {}   # uid -> {"src": bytes, "meta": dict} — tasdiq kutilmoqda
MODIN: dict[int, tuple] = {}    # uid -> (modul, kalit, vaqt) — config qiymati kutilmoqda
MODFOR: dict[int, str] = {}     # uid -> modul nomi: «♻️ Qayta yuklash» — shu modul fayli yangi .py bilan almashtiriladi
AIEDIT: dict[int, str] = {}     # uid -> modul nomi: AI shu modulni o'zgartirmoqda (NAME o'zgarmasligi shart)
AIIMG: dict[int, list] = {}     # uid -> [(mime, bytes)] — AI so'roviga biriktirilgan rasmlar (matn kutilmoqda)
AIWAIT: dict[int, tuple] = {}   # uid -> ("key"|"prompt", vaqt) — AI bo'limi (bot_ai.py) matn kutmoqda


# ───────── ko'rinish ─────────
def _uptime(t: float) -> str:
    s = int(time.time() - t)
    return f"{s // 86400}k {s % 86400 // 3600}s {s % 3600 // 60}d" if s >= 86400 else f"{s // 3600}s {s % 3600 // 60}d"


def view(uid: int, note: str = ""):
    bot = ub.get(uid)
    d = ub.load(uid) or {}
    if not ub.installed(uid):
        text = (f"🤖 <b>Userbot</b> <code>v{ub.USERBOT_VERSION}</code>\n\n⚪ O'rnatilmagan\n\n"
                "Userbot — sizning shaxsiy akkauntingizda ishlaydi: <code>.ping</code>, <code>.calc</code>, "
                "<code>.afk</code>, <code>.remind</code>, <code>.note</code>, <code>.font</code>, profilda <b>jonli soat</b> (14 xil shrift) va boshqalar.")
        return note + text, K([[B("📥 O'rnatish", "ub:inst")], [B("⬅️ Menyu", "menu"), B("❌ Yopish", "x")]])
    want = ub.wants_run(d)
    if bot.running:
        me = bot.me
        who = esc(" ".join(x for x in (me.first_name, me.last_name) if x)) + (f" (@{esc(me.username)})" if me.username else "")
        state = f"🟢 Ishlayapti — {who}\n⏱ {_uptime(bot.started)}"
    elif want:
        state = "🟡 Ulanmoqda… (bot o'zi qayta urinadi)" + (f"\n⚠️ {esc(bot.error[:200])}" if bot.error else "")
    else:
        state = "🔴 To'xtatilgan (siz to'xtatgansiz — restartdan keyin ham o'chiq turadi)" + (f"\n⚠️ {esc(bot.error[:200])}" if bot.error else "")
    if want:
        state += "\n♻️ Avto-davom: bot restart / ZIP yangilanishidan keyin o'zi ko'taradi"
    clock = "🕒 Profil soati: " + (f"<b>yoqilgan</b> · {esc(ub.DIGITS.get(d.get('clock_font', 'normal'), ub.DIGITS['normal'])[0])}" if d.get("clock") else "o'chiq")
    afk = f"\n😴 AFK: {esc(str(bot.afk_reason or (d.get('afk') or {}).get('reason')))}" if (bot.afk_reason or d.get("afk")) else ""
    mods = d.get("mods") or {}
    modl = f"\n🧩 Modullar: {sum(1 for n in mods if n in bot.mods)}/{len(mods)} yuklangan" if mods else ""
    text = f"🤖 <b>Userbot</b> <code>v{ub.USERBOT_VERSION}</code>\n\n{state}\n{clock}{afk}{modl}\n🌍 Vaqt zonasi: {esc(str(ub.tz_of(d)))}"
    rows = [[B("▶️ Start", "ub:start"), B("⏹ Stop", "ub:stop"), B("🔄 Restart", "ub:restart")],
            [B("🕒 Profil soati", "ub:clk"), B("🧩 Modullar", "ub:mods")],
            [B("📖 Buyruqlar", "ub:help")],
            [B("📥 Qayta o'rnatish", "ub:inst"), B("🗑 O'chirish", "ub:del")],
            [B("🔄", "ub"), B("⬅️ Menyu", "menu"), B("❌ Yopish", "x")]]
    return note + text, K(rows)


async def show(msg, uid: int, note: str = ""):
    text, kb = view(uid, note)
    await edit(msg, text, kb)


# ───────── boshqaruv tugmalari ─────────
@router.callback_query(F.data == "ub")
async def cb_ub(c: CallbackQuery):
    await c.answer()
    await show(c.message, c.from_user.id)


@router.callback_query(F.data.in_({"ub:start", "ub:stop", "ub:restart"}))
async def cb_ctl(c: CallbackQuery):
    await c.answer()
    uid, act = c.from_user.id, c.data[3:]
    bot = ub.get(uid)
    if not ub.installed(uid):
        return await show(c.message, uid)
    note = ""
    try:
        if act in ("stop", "restart"):
            await bot.stop()
        if act in ("start", "restart"):
            await bot.start()
        note = "✅ Bajarildi\n\n"
    except Exception as e:
        note = f"❌ {esc(str(e)[:300])}\n\n"
    await show(c.message, uid, note)


# ───────── profil soati menyusi (userbot ishlamayotgan bo'lsa ham sozlanadi — ishga tushganda qo'llanadi) ─────────
CLK_WHERE = ["last", "first", "bio"]
WHERE_NAME = {"last": "Familiya", "first": "Ism", "bio": "Bio"}


def clk_view(uid: int, note: str = ""):
    bot = ub.get(uid)
    d = ub.load(uid) or {}
    on = bool(d.get("clock"))
    font = d.get("clock_font", "normal")
    where = d.get("clock_where", "last")
    text = (f"{note}🕒 <b>Profil soati</b>\n\nHolat: {'🟢 yoqilgan' if on else '⚪ o‘chiq'}"
            f"{'' if bot.running else ' (userbot ishga tushganda boshlanadi)'}\n"
            f"📍 Joyi: <b>{WHERE_NAME[where]}</b>\n🔤 Shrift: <b>{esc(ub.DIGITS.get(font, ub.DIGITS['normal'])[0])}</b>\n"
            f"🎨 Shablon: <code>{esc(d.get('clock_tpl') or ub.PRESETS[0])}</code>\n🌍 Zona: {esc(str(ub.tz_of(d)))}\n\n"
            f"👁 Ko'rinish: <b>{esc(ub.render(d))}</b>")
    rows = [[B("🕒 Soatni o'chirish" if on else "🕒 Soatni yoqish", "ub:cl")],
            [B("🔤 Shrift", "ub:cfl"), B("📍 Joyi", "ub:cw")],
            [B("🎨 Shablon", "ub:ctp"), B("🌍 Zona", "ub:ctz")],
            [B("⬅️ Userbot", "ub"), B("❌ Yopish", "x")]]
    return text, K(rows)


async def show_clk(msg, uid: int, note: str = ""):
    text, kb = clk_view(uid, note)
    await edit(msg, text, kb)


@router.callback_query(F.data.in_({"ub:clk", "ub:clock"}))
async def cb_clk(c: CallbackQuery):
    await c.answer()
    await show_clk(c.message, c.from_user.id)


@router.callback_query(F.data == "ub:cl")
async def cb_clock(c: CallbackQuery):
    await c.answer()
    uid, bot = c.from_user.id, ub.get(c.from_user.id)
    try:
        if (ub.load(uid) or {}).get("clock"):
            await bot.clock_off()
            note = "🕒 Soat o'chirildi, asl nom/bio tiklandi.\n\n"
        else:
            await bot.clock_on_()
            note = "🕒 Soat yoqildi.\n\n"
    except Exception as e:
        note = f"❌ {esc(str(e)[:300])}\n\n"
    await show_clk(c.message, uid, note)


@router.callback_query(F.data == "ub:cfl")
async def cb_fonts(c: CallbackQuery):
    await c.answer()
    cur = (ub.load(c.from_user.id) or {}).get("clock_font", "normal")
    btns = [B(("✅ " if k == cur else "") + f"{ub.digits_in(k, '12:34')}", f"ub:cf:{k}") for k in ub.DIGIT_KEYS]
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)] + [[B("⬅️ Soat", "ub:clk")]]
    await edit(c.message, "🔤 <b>Soat shriftini tanlang</b>", K(rows))


@router.callback_query(F.data.startswith("ub:cf:"))
async def cb_font(c: CallbackQuery):
    await c.answer()
    k = c.data[6:]
    if k in ub.DIGITS:
        ub.get(c.from_user.id).set_clock(clock_font=k)
    await show_clk(c.message, c.from_user.id, f"✅ Shrift: {ub.DIGITS.get(k, ('?',))[0]}\n\n")


@router.callback_query(F.data == "ub:cw")
async def cb_where(c: CallbackQuery):
    await c.answer()
    uid = c.from_user.id
    cur = (ub.load(uid) or {}).get("clock_where", "last")
    nxt = CLK_WHERE[(CLK_WHERE.index(cur) + 1) % 3] if cur in CLK_WHERE else "last"
    ub.get(uid).set_clock(clock_where=nxt)
    await show_clk(c.message, uid, f"✅ Joyi: {WHERE_NAME[nxt]}\n\n")


@router.callback_query(F.data == "ub:ctp")
async def cb_tpl(c: CallbackQuery):
    await c.answer()
    uid = c.from_user.id
    cur = (ub.load(uid) or {}).get("clock_tpl") or ub.PRESETS[0]
    nxt = ub.PRESETS[(ub.PRESETS.index(cur) + 1) % len(ub.PRESETS)] if cur in ub.PRESETS else ub.PRESETS[0]
    ub.get(uid).set_clock(clock_tpl=nxt)
    await show_clk(c.message, uid, "✅ Shablon almashtirildi\n\n")


@router.callback_query(F.data == "ub:ctz")
async def cb_tzs(c: CallbackQuery):
    await c.answer()
    btns = [B(z, f"ub:tz:{i}") for i, z in enumerate(ub.TZS)]
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)] + [[B("⬅️ Soat", "ub:clk")]]
    await edit(c.message, "🌍 <b>Vaqt zonasini tanlang</b>\n<i>Boshqasi: userbotda </i><code>.clock tz Zona/Shahar</code>", K(rows))


@router.callback_query(F.data.startswith("ub:tz:"))
async def cb_tz(c: CallbackQuery):
    await c.answer()
    i = c.data[6:]
    if i.isdigit() and int(i) < len(ub.TZS):
        ub.get(c.from_user.id).set_clock(tz=ub.TZS[int(i)])
    await show_clk(c.message, c.from_user.id, "✅ Zona almashtirildi\n\n")


@router.callback_query(F.data == "ub:help")
async def cb_help(c: CallbackQuery):
    await c.answer()
    await edit(c.message, ub.get(c.from_user.id).help_html(), K([[B("⬅️ Userbot", "ub"), B("❌ Yopish", "x")]]))


@router.callback_query(F.data == "ub:del")
async def cb_del(c: CallbackQuery):
    await c.answer()
    await edit(c.message, "🗑 Userbot o'chirilsinmi?\nSessiya Telegram'dan ham chiqariladi (log out), saqlangan ma'lumotlar va modullar o'rnatgan kutubxonalar o'chadi.",
               K([[B("✅ Ha, o'chirish", "ub:delyes"), B("Bekor", "ub")]]))


@router.callback_query(F.data == "ub:delyes")
async def cb_delyes(c: CallbackQuery):
    await c.answer()
    uid = c.from_user.id
    try:
        await ub.get(uid).logout()
    except Exception:
        ub.delete(uid)
    ub.BOTS.pop(uid, None)
    await show(c.message, uid, "🗑 Userbot o'chirildi.\n\n")


# ───────── o'rnatish ustasi ─────────
STEPS = {
    "api_id": ("1/5", "🔢 <b>API ID</b> ni yozing (faqat raqam).\n\n"
                      "Olish: https://my.telegram.org → <i>API development tools</i> → ilova yarating."),
    "api_hash": ("2/5", "🔑 <b>API HASH</b> ni yozing (32 ta belgi)."),
    "phone": ("3/5", "📱 Akkaunt <b>telefon raqami</b>ni xalqaro formatda yozing:\n<code>+998901234567</code>\n\n"
                     "<i>Kod kelmayaptimi? «📷 QR bilan kirish» — kodsiz, raqam ham kerak emas.</i>"),
    "password": ("5/5", "🔐 Akkauntda <b>ikki bosqichli parol (2FA)</b> bor. Parolni yozing:"),
}

# Telegram kodni QAYERGA yuborganini aniq aytamiz (ilova / SMS / qo'ng'iroq / email) — «keldi» deb faraz qilmaymiz
WHERE = {
    "SentCodeTypeApp": "💬 <b>Telegram ilovasi ichiga</b> — boshqa qurilmangizdagi Telegramni oching, "
                       "<b>«Telegram»</b> (rasmiy, ko'k belgi) chatida kod turibdi",
    "SentCodeTypeSms": "📩 <b>SMS</b> orqali (raqamingizga)",
    "SentCodeTypeCall": "📞 <b>telefon qo'ng'irog'i</b> orqali — robot kodni ovoz bilan aytadi",
    "SentCodeTypeFlashCall": "📞 <b>qo'ng'iroq</b>: kelgan raqamning oxirgi raqamlari kod bo'ladi",
    "SentCodeTypeMissedCall": "📞 <b>javobsiz qo'ng'iroq</b>: qo'ng'iroq qilgan raqamning oxirgi raqamlari kod bo'ladi",
    "SentCodeTypeEmailCode": "📧 <b>emailingizga</b>",
    "SentCodeTypeFragmentSms": "💎 <b>Fragment</b> (anonim raqam) orqali",
    "SentCodeTypeFirebaseSms": "📩 <b>SMS</b> orqali (raqamingizga)",
    "SentCodeTypeSetUpEmailRequired": "⚠️ Telegram bu akkaunt uchun <b>email bog'lashni</b> talab qilmoqda — kod yuborilmaydi. "
                                      "<b>«📷 QR bilan kirish»</b> ni tanlang",
}
NEXT_BTN = {
    "SentCodeTypeSms": "📩 SMS yuborish", "SentCodeTypeFirebaseSms": "📩 SMS yuborish",
    "SentCodeTypeCall": "📞 Qo'ng'iroq qilish", "SentCodeTypeFlashCall": "📞 Qo'ng'iroq qilish",
    "SentCodeTypeMissedCall": "📞 Qo'ng'iroq qilish", "SentCodeTypeApp": "💬 Ilovaga qayta yuborish",
    "SentCodeTypeEmailCode": "📧 Emailga yuborish", "SentCodeTypeFragmentSms": "💎 Fragment orqali",
}


def _tn(x) -> str:
    return type(x).__name__ if x is not None else ""


def _store_sent(s: dict, sent) -> None:
    s["hash"] = sent.phone_code_hash
    s["sent_type"] = _tn(sent.type)
    s["next"] = _tn(getattr(sent, "next_type", None))
    s["timeout"] = int(getattr(sent, "timeout", 0) or 0)
    s["sent_at"] = time.time()
    s["email"] = getattr(sent.type, "email_pattern", "") or ""


def _code_text(s: dict, note: str = "") -> str:
    t = s.get("sent_type", "")
    where = WHERE.get(t, f"noma'lum usul (<code>{esc(t)}</code>)")
    if s.get("email"):
        where += f" <code>{esc(s['email'])}</code>"
    tips = ("\n\n<b>Kelmadimi?</b>\n"
            "• Boshqa qurilmadagi Telegramda <b>«Telegram»</b> chatini (yoki arxivni) tekshiring\n"
            + ("• Pastdagi tugma bilan boshqa usulda yuboring\n" if s.get("next") in NEXT_BTN else "")
            + "• Baribir kelmasa — <b>📷 QR bilan kirish</b> (kod kerak emas; VPS IP larida kod ko'pincha kelmaydi)")
    return (f"{note}<b>O'rnatish 4/5</b>\n📨 Kod yuborildi: {where}\n\n"
            "💬 Kelgan <b>kodni nuqta bilan</b> yozing: <code>123.45</code>\n"
            "⚠️ Nuqtasiz yozmang — Telegram kodni o'zi bekor qilib qo'yadi." + tips)


def _kb(step: str, s: dict):
    rows = []
    if step == "code":
        if s.get("next") in NEXT_BTN:
            rows.append([B(NEXT_BTN[s["next"]], "ub:resend")])
        rows.append([B("📷 QR bilan kirish", "ub:qr"), B("📱 Boshqa raqam", "ub:phone")])
    elif step == "phone":
        rows.append([B("📷 QR bilan kirish (kodsiz)", "ub:qr")])
    rows.append([B("❌ Bekor qilish", "ub:cx")])
    return K(rows)


def _cancel_kb():
    return K([[B("❌ Bekor qilish", "ub:cx")]])


async def _ask(m: Message, uid: int, step: str, note: str = ""):
    s = SETUP[uid]
    s["step"], s["ts"] = step, time.time()
    if step == "code":
        text = _code_text(s, note)
    else:
        n, txt = STEPS[step]
        text = f"{note}<b>O'rnatish {n}</b>\n{txt}"
    await m.answer(text, reply_markup=_kb(step, s))


async def cancel(uid: int) -> bool:
    for d in (MODWAIT, MODPEND, MODIN, MODFOR, AIWAIT, AIIMG):
        d.pop(uid, None)
    s = SETUP.pop(uid, None)
    if s:
        t = s.get("qr")
        if t and not t.done():
            t.cancel()
        if s.get("client"):
            try: await s["client"].disconnect()
            except Exception: pass
    return bool(s)


@router.callback_query(F.data == "ub:inst")
async def cb_inst(c: CallbackQuery):
    await c.answer()
    uid = c.from_user.id
    await cancel(uid)
    SETUP[uid] = {"step": "api_id", "ts": time.time(), "client": None}
    n, txt = STEPS["api_id"]
    await edit(c.message, f"📥 <b>Userbot o'rnatish</b> — {n}\n{txt}\n\n"
                          "🔒 Yuborgan ma'lumotlaringiz xabarlari chatdan o'chiriladi.", _cancel_kb())


@router.callback_query(F.data == "ub:cx")
async def cb_cx(c: CallbackQuery):
    await c.answer()
    await cancel(c.from_user.id)
    await show(c.message, c.from_user.id, "❌ O'rnatish bekor qilindi.\n\n")


class InSetup(BaseFilter):
    async def __call__(self, m: Message) -> bool:
        return m.from_user.id in SETUP


async def _finish(m: Message, uid: int, s: dict):
    """Sessiyani saqlaydi, vaqtinchalik ulanishni yopadi va userbotni ishga tushiradi."""
    client = s["client"]
    session = client.session.save()
    me = await client.get_me()
    await client.disconnect()
    SETUP.pop(uid, None)
    old = ub.BOTS.get(uid)
    if old:
        await old.stop()
    prev = ub.load(uid) or {}      # qayta o'rnatishda shrift/shablon/zona/qaydlar saqlanadi
    keep = {k: prev[k] for k in ("clock_font", "clock_tpl", "clock_where", "tz", "notes", "mods", "ai") if k in prev}
    ub.save(uid, {**keep, "api_id": s["api_id"], "api_hash": s["api_hash"], "session": session,
                  "installed": int(time.time()), "enabled": True})
    note = f"✅ <b>{esc(me.first_name or '')}</b> akkaunti ulandi!\n\n"
    try:
        await ub.get(uid).start()
    except Exception as e:
        note += f"⚠️ Ishga tushmadi: {esc(str(e)[:200])}\n\n"
    text, kb = view(uid, note)
    await m.answer(text, reply_markup=kb)


def _err(e: Exception) -> str:
    return f"<code>{esc(type(e).__name__)}</code> {esc(str(e)[:200])}"


async def _connect(s: dict):
    """Vaqtinchalik mijozni (kerak bo'lsa) yaratib ulaydi."""
    if not s.get("client"):
        s["client"] = ub.make_client(s["api_id"], s["api_hash"])
    if not s["client"].is_connected():
        await s["client"].connect()
    return s["client"]


# ───────── kodni qayta yuborish / raqamni almashtirish ─────────
@router.callback_query(F.data == "ub:resend")
async def cb_resend(c: CallbackQuery):
    uid = c.from_user.id
    s = SETUP.get(uid)
    if not s or s.get("step") != "code":
        return await c.answer("Bu bosqich eskirgan.", show_alert=True)
    left = s["sent_at"] + s["timeout"] - time.time()
    if left > 0:      # Telegram qayta yuborishga ruxsat berguncha kutish kerak
        return await c.answer(f"⏳ {int(left) + 1} soniyadan keyin bosing.", show_alert=True)
    await c.answer()
    try:
        sent = await s["client"](ResendCodeRequest(phone_number=s["phone"], phone_code_hash=s["hash"]))
    except FloodWaitError as e:
        return await c.message.answer(f"⛔ Telegram cheklov qo'ydi: {e.seconds // 60 + 1} daqiqadan keyin urining.",
                                      reply_markup=_kb("code", s))
    except Exception as e:
        s["next"] = ""      # boshqa usul qolmagan bo'lishi mumkin
        return await c.message.answer(f"❌ Qayta yuborib bo'lmadi: {_err(e)}\n\n"
                                      "Boshqa usul qolmagan bo'lishi mumkin — <b>📷 QR bilan kirish</b> ni sinang.",
                                      reply_markup=_kb("code", s))
    _store_sent(s, sent)
    await _ask(c.message, uid, "code", "🔁 Kod qayta yuborildi.\n\n")


@router.callback_query(F.data == "ub:phone")
async def cb_phone(c: CallbackQuery):
    await c.answer()
    s = SETUP.get(c.from_user.id)
    if s and s.get("step") == "code":
        await _ask(c.message, c.from_user.id, "phone")


# ───────── QR bilan kirish (kodsiz) ─────────
def qr_png(url: str) -> bytes | None:
    try:
        import segno
    except ImportError:
        return None
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="png", scale=8, border=3)
    return buf.getvalue()


async def _send_qr(msg: Message, url: str, note: str = "") -> Message:
    caption = (f"{note}📷 <b>QR bilan kirish</b>\n"
               "1) Bu xabarni <b>boshqa qurilmada</b> oching (kompyuter yoki boshqa telefon)\n"
               "2) Telegram → <b>Sozlamalar → Qurilmalar → Desktop qurilmani ulash</b> → QR ni skanerlang\n\n"
               "Bitta telefon bo'lsa — «📲 Shu qurilmada tasdiqlash» tugmasini bosing.\n"
               "⏱ QR har ~30 soniyada yangilanadi.")
    png = qr_png(url)
    cancel_row = [B("❌ Bekor qilish", "ub:cx")]
    kb_link = K([[IB(text="📲 Shu qurilmada tasdiqlash", url=url)], cancel_row])
    kb_plain = K([cancel_row])
    if png is None:     # segno o'rnatilmagan — havolaning o'zini beramiz
        txt = caption + f"\n\n<code>{esc(url)}</code>\n<i>(QR rasm uchun: pip install segno)</i>"
        try: return await msg.answer(txt, reply_markup=kb_link)
        except TelegramBadRequest: return await msg.answer(txt, reply_markup=kb_plain)
    photo = BufferedInputFile(png, filename="login-qr.png")
    try:
        return await msg.answer_photo(photo, caption=caption, reply_markup=kb_link)
    except TelegramBadRequest:      # tg:// havola tugmada qabul qilinmasa — tugmasiz yuboramiz
        return await msg.answer_photo(BufferedInputFile(png, filename="login-qr.png"), caption=caption, reply_markup=kb_plain)


async def _qr_loop(msg: Message, uid: int):
    s = SETUP.get(uid)
    if not s:
        return
    shown = None

    async def drop():
        nonlocal shown
        if shown:
            try: await shown.delete()
            except Exception: pass
            shown = None

    try:
        client = await _connect(s)
        qr = await client.qr_login()
        for _ in range(8):                       # ~4 daqiqa
            await drop()
            shown = await _send_qr(msg, qr.url)
            try:
                await qr.wait(timeout=30)
                break
            except asyncio.TimeoutError:
                await qr.recreate()
        else:
            raise asyncio.TimeoutError()
    except asyncio.CancelledError:
        await drop()
        raise
    except SessionPasswordNeededError:
        await drop()
        if uid in SETUP:
            await _ask(msg, uid, "password", "🔓 QR tasdiqlandi.\n\n")
        return
    except asyncio.TimeoutError:
        await drop()
        return await msg.answer("⌛ QR muddati tugadi. Qaytadan urinib ko'ring.",
                                reply_markup=_kb("phone", s))
    except Exception as e:
        await drop()
        return await msg.answer(f"❌ QR bilan kirib bo'lmadi: {_err(e)}", reply_markup=_kb("phone", s))
    await drop()
    if uid in SETUP:
        await _finish(msg, uid, s)


@router.callback_query(F.data == "ub:qr")
async def cb_qr(c: CallbackQuery):
    await c.answer()
    uid = c.from_user.id
    s = SETUP.get(uid)
    if not s or s.get("step") not in ("phone", "code", "qr") or not s.get("api_hash"):
        return await c.message.answer("Bu bosqich eskirgan. Qaytadan: 🤖 Userbot → 📥 O'rnatish.",
                                      reply_markup=K([[B("🤖 Userbot", "ub")]]))
    t = s.get("qr")
    if t and not t.done():
        t.cancel()
    s["step"], s["ts"] = "qr", time.time()
    s["qr"] = asyncio.create_task(_qr_loop(c.message, uid))


@router.message(F.text & ~F.text.startswith("/"), InSetup())
async def on_setup_text(m: Message):
    uid, s = m.from_user.id, SETUP[m.from_user.id]
    try: await m.delete()          # maxfiy ma'lumot chatda qolmasin
    except Exception: pass
    # QR kutilayotganda 10 daqiqalik TTL tekshirilmaydi (QR sikli o'zi ~4 daqiqada tugaydi)
    if s["step"] != "qr" and time.time() - s["ts"] > TTL:
        await cancel(uid)
        return await m.answer("⌛ Vaqt tugadi. Qaytadan boshlang.", reply_markup=K([[B("🤖 Userbot", "ub")]]))
    txt, step = m.text.strip(), s["step"]

    if step == "qr":
        return          # QR tasdiqlanishini kutyapmiz — matn kerak emas

    if step == "api_id":
        if not txt.isdigit() or not (3 <= len(txt) <= 12):
            return await _ask(m, uid, "api_id", "❌ API ID faqat raqamlardan iborat. Qayta yozing.\n\n")
        s["api_id"] = int(txt)
        return await _ask(m, uid, "api_hash", "✅ API ID qabul qilindi.\n\n")

    if step == "api_hash":
        if not re.fullmatch(r"[0-9a-fA-F]{32}", txt):
            return await _ask(m, uid, "api_hash", "❌ API HASH 32 ta belgidan (0-9, a-f) iborat. Qayta yozing.\n\n")
        s["api_hash"] = txt.lower()
        return await _ask(m, uid, "phone", "✅ API HASH qabul qilindi.\n\n")

    if step == "phone":
        phone = "+" + re.sub(r"\D", "", txt)
        if not re.fullmatch(r"\+\d{7,15}", phone):
            return await _ask(m, uid, "phone", "❌ Raqam noto'g'ri. Masalan: <code>+998901234567</code>\n\n")
        wait = await m.answer("⏳ Kod so'ralmoqda...")
        try:
            client = await _connect(s)
            sent = await client.send_code_request(phone)
        except ApiIdInvalidError:
            await cancel(uid)
            SETUP[uid] = {"step": "api_id", "ts": time.time(), "client": None}
            return await wait.edit_text("❌ API ID / API HASH noto'g'ri. Qaytadan, API ID ni yozing:", reply_markup=_cancel_kb())
        except (PhoneNumberInvalidError, PhoneNumberBannedError) as e:
            return await wait.edit_text(f"❌ Telefon raqam yaroqsiz yoki bloklangan ({type(e).__name__}). Boshqa raqam yozing:",
                                        reply_markup=_kb("phone", s))
        except (FloodWaitError, PhoneNumberFloodError) as e:
            sec = getattr(e, "seconds", 0)
            await cancel(uid)
            return await wait.edit_text(f"⛔ Telegram vaqtincha cheklov qo'ydi{f' ({sec // 60 + 1} daqiqa)' if sec else ''}. Keyinroq urinib ko'ring.")
        except Exception as e:
            await cancel(uid)
            return await wait.edit_text(f"❌ Ulanib bo'lmadi: {_err(e)}")
        s["phone"] = phone
        _store_sent(s, sent)
        await wait.delete()
        return await _ask(m, uid, "code")

    if step == "code":
        digits = re.sub(r"\D", "", txt)
        if not 5 <= len(digits) <= 6:
            return await _ask(m, uid, "code", "❌ Kod 5 ta raqamdan iborat (masalan <code>123.45</code>). Qayta yozing.\n\n")
        client = s["client"]
        try:
            await client.sign_in(s["phone"], digits, phone_code_hash=s["hash"])
        except SessionPasswordNeededError:
            return await _ask(m, uid, "password", "🔓 Kod to'g'ri.\n\n")
        except PhoneCodeInvalidError:
            return await _ask(m, uid, "code", "❌ Kod noto'g'ri. Qayta yozing (<code>123.45</code>).\n\n")
        except PhoneCodeExpiredError:
            try:
                _store_sent(s, await client.send_code_request(s["phone"]))
                return await _ask(m, uid, "code", "⌛ Kod eskirgan — yangi kod yuborildi.\n\n")
            except Exception as e:
                await cancel(uid)
                return await m.answer(f"❌ {_err(e)}")
        except Exception as e:
            await cancel(uid)
            return await m.answer(f"❌ {_err(e)}\nQaytadan boshlang.", reply_markup=K([[B("🤖 Userbot", "ub")]]))
        return await _finish(m, uid, s)

    if step == "password":
        try:
            await s["client"].sign_in(password=txt)
        except PasswordHashInvalidError:
            return await _ask(m, uid, "password", "❌ Parol noto'g'ri. Qayta yozing.\n\n")
        except FloodWaitError as e:
            await cancel(uid)
            return await m.answer(f"⛔ Juda ko'p urinish. {e.seconds // 60 + 1} daqiqadan keyin qayta urining.")
        except Exception as e:
            await cancel(uid)
            return await m.answer(f"❌ {_err(e)}\nQaytadan boshlang.", reply_markup=K([[B("🤖 Userbot", "ub")]]))
        return await _finish(m, uid, s)


# ───────── 🧩 modullar ─────────
WARN = "⚠️ Modul bot jarayonida <b>to'liq huquq</b> bilan ishlaydi (fayl, tarmoq, server). Faqat ishonchli kodni o'rnating."


def _icon(bot, name: str, ent: dict) -> str:
    if name in bot.mods: return "🟢"
    if bot.mod_err.get(name): return "🔴"
    return "🟡" if ent.get("enabled", True) else "⚪"


def mods_view(uid: int, note: str = ""):
    bot, mods = ub.get(uid), ub.mods_cfg(uid)
    rows = [[B(f"{_icon(bot, n, e)} {n} v{e.get('version', '?')}", f"ub:m:{n}")] for n, e in sorted(mods.items())]
    body = ("\n".join(f"{_icon(bot, n, e)} <b>{esc(n)}</b> — {esc((ub.mod_meta(uid, n) or {}).get('description', '?'))}"
                      for n, e in sorted(mods.items())) or "Hozircha modul yo'q.")
    text = (f"{note}🧩 <b>Modullar</b>\n\n{body}\n\n🟢 yuklangan · 🟡 kutilmoqda · ⚪ o'chiq · 🔴 xato\n"
            "<i>.py modul yuboring: 📥 tugma, yoki chatda faylga reply: </i><code>.mod add</code>")
    rows += [[B("📥 Modul qo'shish", "ub:madd"), B("📖 Docs", "ub:docs")], [B("🤖 AI bilan yaratish", "uai")],
             [B("⬅️ Userbot", "ub"), B("❌ Yopish", "x")]]
    return text, K(rows)


async def show_mods(msg, uid: int, note: str = ""):
    text, kb = mods_view(uid, note)
    await edit(msg, text, kb)


def mod_view(uid: int, name: str, note: str = ""):
    bot, ent, meta = ub.get(uid), ub.mods_cfg(uid).get(name), ub.mod_meta(uid, name)
    if ent is None or not meta:
        return mods_view(uid, "❌ Modul topilmadi.\n\n")
    vals = ub.mod_values(uid, name, meta)
    if name in bot.mods: st = "🟢 Yuklangan"
    elif bot.mod_err.get(name): st = "🔴 Xato: " + esc(bot.mod_err[name])
    elif not ent.get("enabled", True): st = "⚪ O'chirilgan"
    else: st = "🟡 Userbot ishga tushganda yuklanadi"
    cmds = "\n".join(f"<code>{esc(c['usage'])}</code> — {esc(c['desc'])}" for c in meta["commands"].values()) or "—"
    cfg = "\n".join(f"• <code>{k}</code> = <b>{esc(M.fmt(vals[k]))}</b> <i>({esc(M.describe(sp))})</i>" + (f" — {esc(sp['desc'])}" if sp["desc"] else "")
                    for k, sp in sorted(meta["config"].items())) or "yo'q"
    libs = L.summary(ent)
    libs_txt = (f"\n\n📚 <b>Kutubxonalar</b>: {esc(libs)}\n<i>modul o'chirilsa, ular ham o'chadi</i>" if libs else "")
    text = (f"{note}🧩 <b>{esc(name)}</b> <code>v{esc(meta['version'])}</code>" + (f" · {esc(meta['author'])}" if meta["author"] else "") +
            f"\n{esc(meta['description'])}\n\nHolat: {st}\n\n<b>Buyruqlar</b>\n{cmds}\n\n"
            f"<b>Config</b> (<code>.config {esc(name)} kalit qiymat</code>)\n{cfg}{libs_txt}")
    on = ent.get("enabled", True)
    cb = []
    for i, (k, sp) in enumerate(sorted(meta["config"].items())):
        cb.append(B(f"🔘 {k}: {'on' if vals[k] else 'off'}" if sp["type"] == "bool" else f"✏️ {k}", f"ub:mc:{name}:{i}"))
    rows = [[B("⏸ O'chirish" if on else "▶️ Yoqish", f"ub:mt:{name}"), B("♻️ Qayta yuklash", f"ub:mr:{name}")]]
    rows += [cb[i:i + 2] for i in range(0, len(cb), 2)]
    rows += [[B("📥 Yuklab olish", f"ub:mdl:{name}"), B("📚 Kutubxonalar", f"ub:ml:{name}")],
             [B("✏️ O'zgartirish (AI)", f"ub:me:{name}"), B("🗑 Modulni o'chirish", f"ub:md:{name}")],
             [B("⬅️ Modullar", "ub:mods"), B("❌ Yopish", "x")]]
    return text, K(rows)


async def show_mod(msg, uid: int, name: str, note: str = ""):
    text, kb = mod_view(uid, name, note)
    await edit(msg, text, kb)


def _e(ex: Exception) -> str:
    return f"❌ {esc(str(ex)[:300])}\n\n"


@router.callback_query(F.data == "ub:docs")
async def cb_docs(c: CallbackQuery):
    """Modul yozish qo'llanmasi + foydalanuvchining modullari — har safar koddan yangidan yasaladi."""
    import userbot_docs
    uid = c.from_user.id
    try:
        text = userbot_docs.build(uid)
        userbot_docs.sync(uid)
    except Exception as ex:
        return await c.message.answer(f"❌ Docs yaratilmadi: {esc(str(ex)[:200])}")
    await c.message.answer_document(BufferedInputFile(text.encode("utf-8"), filename="MODULES.md"),
                                    caption=f"📖 Modul docs · userbot v{ub.USERBOT_VERSION}\n<i>Kod va modullar o'zgarsa, bu fayl ham yangilanadi.</i>")


@router.callback_query(F.data == "ub:mods")
async def cb_mods(c: CallbackQuery):
    await c.answer()
    MODIN.pop(c.from_user.id, None)
    MODWAIT.pop(c.from_user.id, None)
    MODPEND.pop(c.from_user.id, None)
    AIWAIT.pop(c.from_user.id, None)
    await show_mods(c.message, c.from_user.id)


@router.callback_query(F.data.startswith("ub:m:"))
async def cb_mod(c: CallbackQuery):
    await c.answer()
    await cancel(c.from_user.id)             # kutilayotgan holatlar (fayl, AI so'rovi, config qiymati) bekor qilinadi
    await show_mod(c.message, c.from_user.id, c.data[5:])


@router.callback_query(F.data.startswith("ub:mt:"))
async def cb_mt(c: CallbackQuery):
    await c.answer()
    uid, name = c.from_user.id, c.data[6:]
    ent = ub.mods_cfg(uid).get(name)
    note = ""
    if ent is not None:
        try:
            await ub.get(uid).mod_enable(name, not ent.get("enabled", True))
        except Exception as ex:
            note = _e(ex)
    await show_mod(c.message, uid, name, note)


@router.callback_query(F.data.startswith("ub:mr:"))
async def cb_mr(c: CallbackQuery):
    """♻️ Qayta yuklash: foydalanuvchi shu modulning yangi .py faylini yuboradi — eski fayl almashtiriladi (config va ma'lumotlar saqlanadi)."""
    await c.answer()
    uid, name = c.from_user.id, c.data[6:]
    if name not in ub.mods_cfg(uid):
        return await show_mods(c.message, uid, "❌ Modul topilmadi.\n\n")
    await cancel(uid)
    MODWAIT[uid] = time.time()
    MODFOR[uid] = name
    await edit(c.message, f"♻️ <b>{esc(name)}</b> — qayta yuklash\n\nModulning yangi <code>.py</code> faylini shu yerga yuboring (≤256 KB).\n"
                          f"Faylda <code>NAME = \"{esc(name)}\"</code> bo'lishi shart. Eski fayl almashtiriladi; config qiymatlari va saqlangan ma'lumotlar qoladi.\n\n"
                          "<i>Avval joriy faylni yuklab olib, tahrirlab yuborishingiz mumkin.</i>\n\n" + WARN,
               K([[B("📥 Joriy faylni yuklab olish", f"ub:mdl:{name}")], [B("❌ Bekor qilish", f"ub:m:{name}")]]))


@router.callback_query(F.data.startswith("ub:mdl:"))
async def cb_mdl(c: CallbackQuery):
    """📥 Yuklab olish: modul faylini .py ko'rinishida botga (shu chatga) yuboradi."""
    uid, name = c.from_user.id, c.data[7:]
    try:
        raw = ub.mod_path(uid, name).read_bytes()
    except OSError:
        return await c.answer("Modul fayli topilmadi", show_alert=True)
    await c.answer()
    meta = ub.mod_meta(uid, name) or {}
    await c.message.answer_document(BufferedInputFile(raw, filename=f"{name}.py"),
                                    caption=f"📥 {name}" + (f" v{meta['version']}" if meta.get("version") else ""))


@router.callback_query(F.data.startswith("ub:ml:"))
async def cb_ml(c: CallbackQuery):
    await c.answer()
    uid, name = c.from_user.id, c.data[6:]
    await edit(c.message, f"⏳ <b>{esc(name)}</b>: kutubxonalar tekshirilmoqda…")
    try:
        got = await ub.get(uid).mod_libs_fix(name)
        note = (f"📚 O'rnatildi: {esc(', '.join(got))}\n\n" if got else "📚 Kutubxonalar joyida.\n\n")
    except Exception as ex:
        note = _e(ex)
    await show_mod(c.message, uid, name, note)


@router.callback_query(F.data.startswith("ub:mc:"))
async def cb_mc(c: CallbackQuery):
    await c.answer()
    uid = c.from_user.id
    try:
        _, _, name, i = c.data.split(":")
    except ValueError:
        return
    meta = ub.mod_meta(uid, name)
    keys = sorted(meta["config"]) if meta else []
    if not meta or not i.isdigit() or int(i) >= len(keys):
        return await show_mods(c.message, uid, "❌ Modul topilmadi.\n\n")
    key = keys[int(i)]
    spec, cur = meta["config"][key], ub.mod_values(uid, name, meta)[key]
    if spec["type"] == "bool":
        try:
            await ub.get(uid).mod_config_set(name, key, not cur)
            note = ""
        except Exception as ex:
            note = _e(ex)
        return await show_mod(c.message, uid, name, note)
    MODIN[uid] = (name, key, time.time())
    await edit(c.message, f"✏️ <b>{esc(name)}.{esc(key)}</b> <i>({esc(M.describe(spec))})</i>\n{esc(spec['desc'])}\n\n"
                          f"Hozirgi: <code>{esc(M.fmt(cur))}</code> · standart: <code>{esc(M.fmt(spec['default']))}</code>\n\nYangi qiymatni yozing:",
               K([[B("↩️ Standartga qaytarish", f"ub:mx:{name}:{i}")], [B("⬅️ Orqaga", f"ub:m:{name}")]]))


@router.callback_query(F.data.startswith("ub:mx:"))
async def cb_mx(c: CallbackQuery):
    await c.answer()
    uid = c.from_user.id
    MODIN.pop(uid, None)
    try:
        _, _, name, i = c.data.split(":")
        key = sorted((ub.mod_meta(uid, name) or {"config": {}})["config"])[int(i)]
        await ub.get(uid).mod_config_set(name, key, None)
        note = "↩️ Standart qiymat tiklandi\n\n"
    except Exception as ex:
        note = _e(ex)
        name = c.data.split(":")[2]
    await show_mod(c.message, uid, name, note)


@router.callback_query(F.data.startswith("ub:md:"))
async def cb_md(c: CallbackQuery):
    await c.answer()
    name = c.data[6:]
    libs = L.summary(ub.mods_cfg(c.from_user.id).get(name))
    await edit(c.message, f"🗑 <b>{esc(name)}</b> moduli o'chirilsinmi?\nFayl, config va saqlangan ma'lumotlari o'chadi."
                          + (f"\n📚 Shu modul o'rnatgan kutubxonalar ham o'chadi: <b>{esc(libs)}</b>\n<i>(boshqa modul ishlatayotgani qoladi)</i>" if libs else ""),
               K([[B("✅ Ha, o'chirish", f"ub:mdy:{name}"), B("Bekor", f"ub:m:{name}")]]))


@router.callback_query(F.data.startswith("ub:mdy:"))
async def cb_mdy(c: CallbackQuery):
    await c.answer()
    uid, name = c.from_user.id, c.data[7:]
    try:
        await edit(c.message, f"⏳ <b>{esc(name)}</b> o'chirilmoqda…")
        gone, err = await ub.get(uid).mod_delete(name)
        note = (f"🗑 {esc(name)} o'chirildi.\n" + (f"🧹 Kutubxonalar ham o'chirildi: {esc(', '.join(gone))}\n" if gone else "")
                + (f"⚠️ Kutubxonani o'chirishda xato: {esc(err[:300])}\n" if err else "") + "\n")
    except Exception as ex:
        note = _e(ex)
    await show_mods(c.message, uid, note)


# --- modul qo'shish: .py fayl → tahlil → tasdiq → o'rnatish ---
@router.callback_query(F.data == "ub:madd")
async def cb_madd(c: CallbackQuery):
    await c.answer()
    uid = c.from_user.id
    if not ub.installed(uid):
        return await show(c.message, uid, "⚠️ Avval userbotni o'rnating.\n\n")
    await cancel(uid)
    MODWAIT[uid] = time.time()
    await edit(c.message, "📥 <b>Modul qo'shish</b>\n\n<code>.py</code> faylni shu yerga yuboring (≤256 KB).\n"
                          "Fayl avval <b>ishga tushirilmasdan</b> tekshiriladi va sizga ko'rsatiladi.\n\n" + WARN,
               K([[B("❌ Bekor qilish", "ub:mods")]]))


class InModWait(BaseFilter):
    async def __call__(self, m: Message) -> bool:
        t = MODWAIT.get(m.from_user.id)
        return bool(t and time.time() - t < TTL)


class InModIn(BaseFilter):
    async def __call__(self, m: Message) -> bool:
        v = MODIN.get(m.from_user.id)
        return bool(v and time.time() - v[2] < TTL)


def pending_text(uid: int, meta: dict, extra: str = "") -> str:
    """Tasdiq oldidan modul tahlili (qo'lda yuborilgan ham, AI yaratgan ham shu ko'rinishda chiqadi)."""
    old = ub.mods_cfg(uid).get(meta["name"])
    cmds = " ".join(f"<code>.{c}</code>" for c in meta["commands"]) or "—"
    cfg = ", ".join(f"<code>{k}</code>={esc(M.fmt(sp['default']))}" for k, sp in meta["config"].items()) or "—"
    risky = f"\n🚨 Xavfli import: <b>{esc(', '.join(meta['risky']))}</b>" if meta["risky"] else ""
    try:
        need = L.plan(meta)["install"]
    except M.ModError as ex:
        need, risky = [], risky + f"\n❌ {esc(str(ex))}"
    if need:
        risky += (f"\n📚 Avtomatik o'rnatiladi (pip): <b>{esc(', '.join(need))}</b>\n"
                  "<i>Nomlar to'g'riligini tekshiring. Modul o'chirilsa, ular ham o'chadi.</i>")
    return (f"📦 <b>{esc(meta['name'])}</b> <code>v{esc(meta['version'])}</code>" + (f" · {esc(meta['author'])}" if meta["author"] else "") +
            (f"\n♻️ Yangilanadi: v{esc(str(old.get('version', '?')))} → v{esc(meta['version'])}" if old else "") +
            f"\n{esc(meta['description'])}\n\nBuyruqlar: {cmds}\nConfig: {cfg}\nImport: {esc(', '.join(meta['imports']) or '—')}{risky}\n\n{extra}{WARN}")[:4000]


@router.message(F.document, InModWait())
async def on_mod_file(m: Message):
    uid, d = m.from_user.id, m.document
    tgt = MODFOR.get(uid)
    stop = K([[B("❌ Bekor qilish", f"ub:m:{tgt}" if tgt else "ub:mods")]])
    if not (d.file_name or "").lower().endswith(".py"):
        return await m.answer("❌ Faqat <code>.py</code> fayl qabul qilinadi.", reply_markup=stop)
    if (d.file_size or 0) > M.MAX_SRC:
        return await m.answer("❌ Fayl 256 KB dan katta.", reply_markup=stop)
    buf = await m.bot.download(d)
    raw = buf.read()
    try:
        meta = M.parse_meta(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return await m.answer("❌ Fayl UTF-8 matn bo'lishi kerak.", reply_markup=stop)
    except M.ModError as ex:
        return await m.answer(f"❌ Modul yaroqsiz: {esc(str(ex))}\n\nTuzatib qayta yuboring.", reply_markup=stop)
    if tgt and meta["name"] != tgt:
        return await m.answer(f"❌ Faylda <code>NAME = \"{esc(meta['name'])}\"</code>, lekin <b>{esc(tgt)}</b> moduli almashtirilmoqda.\n"
                              f"NAME ni <code>\"{esc(tgt)}\"</code> qilib qayta yuboring.", reply_markup=stop)
    MODFOR.pop(uid, None)
    MODWAIT.pop(uid, None)
    MODPEND[uid] = {"src": raw, "meta": meta}
    await m.answer(pending_text(uid, meta), reply_markup=K([[B("✅ O'rnatish va yoqish", "ub:mok"), B("❌ Bekor", "ub:mcx")]]))


@router.callback_query(F.data == "ub:mcx")
async def cb_mcx(c: CallbackQuery):
    await c.answer()
    MODPEND.pop(c.from_user.id, None)
    await show_mods(c.message, c.from_user.id, "❌ Bekor qilindi.\n\n")


@router.callback_query(F.data == "ub:mok")
async def cb_mok(c: CallbackQuery):
    await c.answer()
    uid = c.from_user.id
    pend = MODPEND.pop(uid, None)
    AIEDIT.pop(uid, None)
    if not pend:
        return await show_mods(c.message, uid, "⌛ Eskirgan. Faylni qayta yuboring.\n\n")
    async def prog(reqs):
        await edit(c.message, "⏳ <b>Kutubxonalar o'rnatilmoqda</b> (bir necha daqiqa ketishi mumkin):\n"
                              + esc(", ".join(reqs)) + "\n\n<i>Tugagach modul o'rnatiladi.</i>")
    try:
        meta, old, lib = await ub.mod_install_full(uid, pend["src"], progress=prog)
    except M.ModError as ex:
        return await show_mods(c.message, uid, _e(ex))
    note = (f"📚 O'rnatildi: {esc(', '.join(lib['installed']))}\n" if lib["installed"] else "") + \
           f"✅ {esc(meta['name'])} {'yangilandi' if old else 'o‘rnatildi'}"
    bot = ub.get(uid)
    try:
        await bot.mod_reload(meta["name"])
        note += " va yuklandi.\n\n" if meta["name"] in bot.mods else " (userbot ishga tushganda yuklanadi).\n\n"
    except Exception as ex:
        note += f", lekin yuklanmadi: {esc(str(ex)[:300])}\n\n"
    await show_mod(c.message, uid, meta["name"], note)


@router.message(F.text & ~F.text.startswith("/"), InModIn())
async def on_mod_value(m: Message):
    uid = m.from_user.id
    name, key, _ = MODIN[uid]
    try: await m.delete()
    except Exception: pass
    try:
        val = await ub.get(uid).mod_config_set(name, key, m.text)
    except M.ModError as ex:
        return await m.answer(f"❌ {esc(str(ex))}. Qayta yozing:", reply_markup=K([[B("⬅️ Orqaga", f"ub:m:{name}")]]))
    MODIN.pop(uid, None)
    text, kb = mod_view(uid, name, f"✅ {esc(key)} = {esc(M.fmt(val))}\n\n")
    await m.answer(text, reply_markup=kb)
