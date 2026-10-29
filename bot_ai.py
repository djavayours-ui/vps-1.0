"""Bot: 🧩 Modullar → 🤖 AI bilan yaratish (DeepSeek).

API kalitni foydalanuvchi shu yerda, Telegramda kiritadi (xabar chatdan o'chiriladi). Mantiq userbot_ai.py da.
Docs tugmasi: ✅ — qo'llanma AI ga suhbatda FAQAT BIR MARTA yuboriladi va tarixda qoladi; ❌ — yuborilmaydi.
Yaratilgan modul avvalgi tasdiq oqimi (ub:mok / ub:mcx) orqali o'rnatiladi — hech narsa o'zi ishga tushmaydi.
"""
import asyncio, re, time

from aiogram import F, Router
from aiogram.filters import BaseFilter
from aiogram.types import BufferedInputFile, CallbackQuery, Message

import bot_userbot as bu
import userbot_ai as AI
import userbot_core as ub
import userbot_docs
import userbot_emoji as EM
import userbot_mods as M
from common import B, K, edit, esc

router = Router()
KEY_RE = re.compile(r"^[A-Za-z0-9_\-]{16,200}$")
CANCEL = K([[B("❌ Bekor qilish", "uai")]])


class InAI(BaseFilter):
    def __init__(self, *modes: str): self.modes = modes

    async def __call__(self, m: Message) -> bool:
        v = bu.AIWAIT.get(m.from_user.id)
        return bool(v and v[0] in self.modes and time.time() - v[1] < bu.TTL)


ALBUM: dict[tuple, list] = {}        # (uid, media_group_id) -> xabarlar (bir nechta rasm bitta albom bo'lib kelganda)


def _mask(k: str) -> str:
    return f"{k[:5]}…{k[-4:]}" if len(k) > 12 else "•••"


def ai_view(uid: int, note: str = ""):
    c = ub.ai_cfg(uid)
    s = AI.SESS.get(uid)
    if s and time.time() - s.ts > AI.TTL:
        s = None
    key = f"✅ <code>{esc(_mask(c['key']))}</code>" if c["key"] else "❌ kiritilmagan"
    chat = (f"{s.turns} ta so'rov · docs: {'✅ tarixda bor' if s.docs_sent else '— yuborilmagan'}" if s and s.turns else "yangi (bo'sh)")
    text = (f"{note}🤖 <b>AI bilan modul yaratish</b> · DeepSeek\n\n"
            f"🔑 API kalit: {key}\n🧠 Model: <code>{esc(c['model'])}</code>\n"
            f"📖 Docs yuborish: {'✅ yoqilgan' if c['send_docs'] else '❌ o‘chirilgan'}\n💬 Suhbat: {chat}\n\n"
            "<i>Nima xohlayotganingizni yozasiz — AI modul yozadi, bot uni ishga tushirmasdan tekshiradi va sizga ko'rsatadi; "
            "tasdiqlasangiz o'rnatiladi. Natijani «✏️ O'zgartirish» bilan davom ettirish mumkin — suhbat saqlanadi.\n"
            "📖 ✅ bo'lsa, modul yozish qo'llanmasi AI ga suhbatda <b>bir marta</b> yuboriladi va tarixda qoladi (qayta yuborilmaydi); ❌ bo'lsa yuborilmaydi.</i>")
    rows = [[B("✍️ Modul yaratish", "uai:new")],
            [B("🔑 API kalit" + (" (almashtirish)" if c["key"] else ""), "uai:key")] + ([B("🗑", "uai:keydel")] if c["key"] else []),
            [B(f"📖 Docs yuborish: {'✅' if c['send_docs'] else '❌'}", "uai:docs")],
            [B(f"🧠 Model: {AI.MODELS.get(c['model'], c['model'])}", "uai:model")],
            [B("🧹 Yangi suhbat", "uai:reset")],
            [B("⬅️ Modullar", "ub:mods"), B("❌ Yopish", "x")]]
    return text, K(rows)


async def show(msg, uid: int, note: str = ""):
    text, kb = ai_view(uid, note)
    await edit(msg, text, kb)


async def _guard(c: CallbackQuery) -> bool:
    if ub.installed(c.from_user.id):
        return True
    await edit(c.message, "⚠️ Avval userbotni o'rnating (🤖 Userbot → 📥 O'rnatish).", K([[B("⬅️ Modullar", "ub:mods")]]))
    return False


@router.callback_query(F.data == "uai")
async def cb_ai(c: CallbackQuery):
    await c.answer()
    if not await _guard(c): return
    await bu.cancel(c.from_user.id)
    await show(c.message, c.from_user.id)


@router.callback_query(F.data == "uai:key")
async def cb_key(c: CallbackQuery):
    await c.answer()
    if not await _guard(c): return
    uid = c.from_user.id
    await bu.cancel(uid)
    bu.AIWAIT[uid] = ("key", time.time())
    await edit(c.message, "🔑 <b>DeepSeek API kaliti</b>\n\nKalitni shu yerga yuboring (platform.deepseek.com → API keys).\n"
                          "Xabaringiz chatdan <b>o'chiriladi</b>; kalit tekshiriladi va faqat sizning userbot sozlamangizda (<code>chmod 600</code>) saqlanadi.", CANCEL)


@router.callback_query(F.data == "uai:keydel")
async def cb_keydel(c: CallbackQuery):
    await c.answer()
    if not await _guard(c): return
    ub.ai_set(c.from_user.id, key="")
    await show(c.message, c.from_user.id, "🗑 Kalit o'chirildi.\n\n")


@router.callback_query(F.data == "uai:docs")
async def cb_docs(c: CallbackQuery):
    await c.answer()
    if not await _guard(c): return
    uid = c.from_user.id
    on = not ub.ai_cfg(uid)["send_docs"]
    ub.ai_set(uid, send_docs=on)
    s = AI.SESS.get(uid)
    if on:
        note = "📖 Docs ✅ — keyingi so'rovda AI ga bir marta yuboriladi.\n\n" if not (s and s.docs_sent) else "📖 Docs ✅ — suhbatda allaqachon bor, qayta yuborilmaydi.\n\n"
    else:
        note = ("📖 Docs ❌ — yangi so'rovlarga qo'shilmaydi." +
                (" (Joriy suhbat tarixida allaqachon bor; to'liq olib tashlash uchun «🧹 Yangi suhbat».)" if s and s.docs_sent else "") + "\n\n")
    await show(c.message, uid, note)


@router.callback_query(F.data == "uai:model")
async def cb_model(c: CallbackQuery):
    await c.answer()
    if not await _guard(c): return
    uid, names = c.from_user.id, list(AI.MODELS)
    cur = ub.ai_cfg(uid)["model"]
    ub.ai_set(uid, model=names[(names.index(cur) + 1) % len(names)] if cur in names else names[0])
    await show(c.message, uid)


@router.callback_query(F.data == "uai:reset")
async def cb_reset(c: CallbackQuery):
    await c.answer()
    AI.reset(c.from_user.id)
    bu.AIEDIT.pop(c.from_user.id, None)
    await show(c.message, c.from_user.id, "🧹 Suhbat tozalandi.\n\n")


@router.callback_query(F.data.in_({"uai:new", "uai:more"}))
async def cb_new(c: CallbackQuery):
    await c.answer()
    if not await _guard(c): return
    uid = c.from_user.id
    if not ub.ai_cfg(uid)["key"]:
        return await cb_key(c)
    await bu.cancel(uid)
    if c.data == "uai:new":
        bu.AIEDIT.pop(uid, None)                         # yangi modul — eski modulni o'zgartirish rejimi tugaydi
    bu.AIWAIT[uid] = ("edit" if c.data == "uai:more" and uid in bu.AIEDIT else "prompt", time.time())
    more = c.data == "uai:more" and AI.SESS.get(uid)
    await edit(c.message, ("✏️ <b>Nimani o'zgartiray?</b>\nAI oldingi modulni eslab turibdi — o'zgarishni yozing (🖼 rasm + izoh ham bo'ladi)." if more else
                           "✍️ <b>Qanday modul kerak?</b>\n\nOddiy tilda yozing: nima qilsin, qaysi buyruq bilan, qaysi qiymatlar <code>.config</code> orqali o'zgartirilsin.\n"
                           "🖼 Rasm (skrinshot, namuna) ham yuborishingiz mumkin — <b>rasm + izoh</b> birga yuboriladi.\n\n"
                           "<i>Masalan: «.quote buyrug'i — reply qilingan xabarni chiroyli iqtibos qilib yozsin; ramka belgisi va maksimal uzunlik config'da bo'lsin»</i>"),
               CANCEL)


@router.message(F.text & ~F.text.startswith("/"), InAI("key"))
async def on_key(m: Message):
    uid, key = m.from_user.id, (m.text or "").strip()
    try: await m.delete()
    except Exception: pass                                   # maxfiy ma'lumot chatda qolmasin
    if not KEY_RE.match(key):
        return await m.answer("❌ Kalit formati noto'g'ri (harf/raqam/-/_, 16+ belgi). Qayta yuboring:", reply_markup=CANCEL)
    wait = await m.answer("⏳ Kalit tekshirilmoqda…")
    try:
        await AI.check_key(key)
    except AI.AIError as ex:
        return await edit(wait, f"❌ {esc(str(ex))}\n\nQayta yuboring:", CANCEL)
    ub.ai_set(uid, key=key)
    bu.AIWAIT.pop(uid, None)
    text, kb = ai_view(uid, "✅ Kalit tekshirildi va saqlandi.\n\n")
    await edit(wait, text, kb)


@router.callback_query(F.data.startswith("ub:me:"))
async def cb_mod_edit(c: CallbackQuery):
    """✏️ O'zgartirish (modul ekranida): foydalanuvchi nimani o'zgartirish kerakligini yozadi — AI shu modulni tahrirlaydi."""
    await c.answer()
    if not await _guard(c): return
    uid, name = c.from_user.id, c.data[6:]
    if name not in ub.mods_cfg(uid) or not ub.mod_meta(uid, name):
        return await edit(c.message, "❌ Modul topilmadi yoki fayli yaroqsiz.", K([[B("⬅️ Modullar", "ub:mods")]]))
    if not ub.ai_cfg(uid)["key"]:
        return await cb_key(c)
    await bu.cancel(uid)
    AI.reset(uid)                                        # suhbat faqat shu modul haqida bo'lsin
    bu.AIEDIT[uid], bu.AIWAIT[uid] = name, ("edit", time.time())
    await edit(c.message, f"✏️ <b>{esc(name)}</b> — AI bilan o'zgartirish\n\nNimani o'zgartirish kerakligini yozing. AI joriy kodni ko'radi va TO'LIQ yangilangan modulni qaytaradi; "
                          "siz ko'rib chiqib tasdiqlaysiz (modul NAME o'zgarmaydi, config va ma'lumotlar saqlanadi).\n"
                          "🖼 Matn bilan birga <b>rasm</b> ham yuborishingiz mumkin (skrinshot, namuna, xato) — rasm izoh (caption) bilan birga ketadi.\n"
                          "💎 <b>Premium emoji</b> yozsangiz ham bo'ladi — modulda aynan o'sha emoji bilan yuboriladi (userbot hisobi Premium bo'lishi kerak, aks holda oddiy emoji ko'rinadi).\n\n"
                          "<i>Masalan: «font_size standarti 40 bo'lsin va .quote2 buyrug'i qo'sh»</i>",
               K([[B("❌ Bekor qilish", f"ub:m:{name}")]]))


def _utext(text: str, entities) -> str:
    """Foydalanuvchi matni: premium emoji'lar `<tg-emoji emoji-id=..>` belgisiga aylantiriladi (AI shuni modulga aynan ko'chiradi)."""
    return EM.from_entities(text or "", entities)[:6000]


@router.message(F.text & ~F.text.startswith("/"), InAI("edit"))
async def on_edit(m: Message):
    await _edit_text(m, _utext(m.text, m.entities))


async def _edit_text(m: Message, text: str):
    uid, name = m.from_user.id, bu.AIEDIT.get(m.from_user.id)
    if name and AI.session(uid).turns == 0:              # birinchi so'rov — joriy kod AI ga beriladi (keyingilarida suhbat tarixida bor)
        try:
            src = ub.mod_path(uid, name).read_text(encoding="utf-8")
        except OSError:
            bu.AIWAIT.pop(uid, None)
            return await m.answer("❌ Modul fayli topilmadi.", reply_markup=K([[B("⬅️ Modullar", "ub:mods")]]))
        text = (f"Mavjud «{name}» modulini o'zgartiring. NAME = \"{name}\" o'zgarmasin, VERSION ni oshiring, config va buyruqlarni keraksiz buzmang. "
                f"TO'LIQ yangilangan faylni qaytaring.\n\nJoriy kod:\n```python\n{src}\n```\n\nO'zgartirish: {text}")
    await _generate(m, text, name)


@router.message(F.text & ~F.text.startswith("/"), InAI("prompt"))
async def on_prompt(m: Message):
    await _generate(m, _utext(m.text, m.entities), None)


async def _generate(m: Message, text: str, lock: str | None):
    """AI dan modul oladi. lock — modul nomi: AI NAME ni o'zgartirsa, tekshiruv rad etadi va AI o'zi tuzatadi."""
    uid, c = m.from_user.id, ub.ai_cfg(m.from_user.id)
    bu.AIWAIT.pop(uid, None)
    images = bu.AIIMG.pop(uid, [])[:AI.MAX_IMAGES]

    def validate(code: str):
        meta = ub.mod_check(uid, code)[0]
        if lock and meta["name"] != lock:
            raise M.ModError(f'NAME = "{lock}" bo\'lishi kerak (hozir "{meta["name"]}"): mavjud modul o\'zgartirilmoqda')
        return meta
    if not c["key"]:
        return await m.answer("🔑 Avval API kalitni kiriting.", reply_markup=K([[B("🔑 API kalit", "uai:key")]]))
    s = AI.session(uid)
    wait = await m.answer(f"⏳ AI modul yozyapti… (⚡ ~20–60 s, 🧠 ko'proq ketishi mumkin)" +
                          (f"\n🖼 {len(images)} ta rasm bilan — {AI.VISION_MODEL} modelida" if images else ""))
    docs = userbot_docs.build_for_ai(uid) if c["send_docs"] and not s.docs_sent else ""
    try:
        r = await AI.generate(uid, text, key=c["key"], model=c["model"], send_docs=c["send_docs"], docs=docs, validate=validate, images=images)
    except AI.AIError as ex:
        return await edit(wait, f"❌ {esc(str(ex))}", K([[B("✍️ Qayta yozish", "uai:more" if lock else "uai:new")], [B("⬅️ Modul" if lock else "⬅️ AI", f"ub:m:{lock}" if lock else "uai"), B("❌ Yopish", "x")]]))
    except Exception as ex:
        return await edit(wait, f"❌ {type(ex).__name__}: {esc(str(ex)[:200])}", K([[B("⬅️ AI", "uai")]]))
    meta = r["meta"]
    bu.MODPEND[uid] = {"src": r["src"].encode("utf-8"), "meta": meta}
    s = AI.session(uid)
    info = ("📖 Docs AI ga yuborildi — suhbat tarixida qoladi, qayta yuborilmaydi.\n" if r["docs_now"] else
            "📖 Docs suhbat tarixida bor (qayta yuborilmadi).\n" if s.docs_sent and c["send_docs"] else
            "📖 Docs yuborilmadi (❌).\n")
    if r["fixes"]:
        info += f"🔧 AI kodni tekshiruvdan keyin {r['fixes']} marta o'zi tuzatdi.\n"
    if r["note"]:
        info += f"💬 {esc(r['note'][:500])}\n"
    try: await wait.delete()
    except Exception: pass
    await m.answer_document(BufferedInputFile(r["src"].encode("utf-8"), filename=f"{meta['name']}.py"),
                            caption=f"🤖 AI yaratdi: {meta['name']} v{meta['version']}")
    await m.answer(bu.pending_text(uid, meta, info + "\n"),
                   reply_markup=K([[B("✅ O'rnatish va yoqish", "ub:mok"), B("✏️ O'zgartirish", "uai:more")],
                                   [B("❌ Bekor", "ub:mcx"), B("⬅️ AI", "uai")]]))


# ───────── 🖼 rasm + matn ─────────
@router.message(InAI("prompt", "edit"), F.photo | F.document.mime_type.in_(AI.IMG_MIMES))
async def on_ai_image(m: Message):
    """Rasm (izoh bilan yoki izohsiz; albom ham bo'ladi). Izoh bor — rasm+matn birga AI ga ketadi; yo'q — rasm saqlanadi, keyingi matnga qo'shiladi."""
    uid = m.from_user.id
    msgs = [m]
    if m.media_group_id:                                  # albom: xabarlar alohida keladi — qisqa kutib yig'amiz
        k = (uid, m.media_group_id)
        if k in ALBUM:
            ALBUM[k].append(m)
            return
        ALBUM[k] = [m]
        await asyncio.sleep(1.2)
        msgs = ALBUM.pop(k, [m])
    mode = bu.AIWAIT.get(uid, ("prompt",))[0]
    got, bad = bu.AIIMG.setdefault(uid, []), ""
    for x in msgs:
        if len(got) >= AI.MAX_IMAGES:
            bad = f"Ko'pi bilan {AI.MAX_IMAGES} ta rasm — ortiqchasi qabul qilinmadi.\n"
            break
        f, mime, size = ((x.photo[-1], "image/jpeg", x.photo[-1].file_size or 0) if x.photo else
                         (x.document, x.document.mime_type, x.document.file_size or 0))
        if size > AI.MAX_IMAGE_BYTES:
            bad = "Rasm 10 MB dan katta — o'tkazib yuborildi.\n"
            continue
        try:
            buf = await m.bot.download(f)
            got.append((mime, buf.read()))
        except Exception:
            bad = "Rasmni yuklab bo'lmadi.\n"
    cap = next((x.caption for x in msgs if x.caption), "") or ""
    if not got:
        return await m.answer("❌ " + (bad or "Rasm qabul qilinmadi."), reply_markup=CANCEL)
    if not cap.strip():                                   # faqat rasm — matnni kutamiz
        bu.AIWAIT[uid] = (mode, time.time())
        return await m.answer(f"🖼 {bad}Rasm qabul qilindi ({len(got)} ta). Endi nima kerakligini <b>matn</b> bilan yozing — rasm unga qo'shib yuboriladi "
                              "(yoki yana rasm yuboring).", reply_markup=CANCEL if mode == "prompt" else K([[B("❌ Bekor qilish", f"ub:m:{bu.AIEDIT.get(uid, '')}")]]))
    cap = _utext(cap, next((x.caption_entities for x in msgs if x.caption), None))
    if mode == "edit":
        await _edit_text(m, cap)
    else:
        await _generate(m, cap, None)
