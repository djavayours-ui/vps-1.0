"""AI yordamida modul yaratish (DeepSeek). Telegram/aiogram'ga bog'liq emas — bot_ai.py shuni chaqiradi.

• API kalitni foydalanuvchi Telegramda o'zi kiritadi (userbot_core.ai_cfg da saqlanadi, chmod 600).
• Har foydalanuvchi uchun bitta SUHBAT (SESS): xabarlar tarixi saqlanadi, shuning uchun «o'zgartir» deyish mumkin.
• Docs (qo'llanma) suhbatga FAQAT BIR MARTA, birinchi so'rovga qo'shib yuboriladi va tarixda qoladi — qayta yuborilmaydi.
  Docs tugmasi ❌ bo'lsa umuman yuborilmaydi.
• AI javobidagi kod ishga tushirilmasdan tekshiriladi (ast + buyruq imzolari + nom to'qnashuvi); xato bo'lsa AI ga xato matni
  qaytarilib, o'zi tuzatadi (ko'pi bilan FIXES marta). Keyin foydalanuvchi tasdiqlagach o'rnatiladi.
"""
import ast, base64, os, re, time
from dataclasses import dataclass, field

import userbot_mods as M

BASE = os.getenv("DEEPSEEK_BASE", "https://api.deepseek.com").rstrip("/")     # sinov/proksi uchun almashtiriladi
# Rasm (skrinshot, dizayn namunasi) biriktirilgan so'rovlar shu modelda bajariladi: matnli modellar rasmni 400 xato bilan rad etadi.
VISION_MODEL = os.getenv("DEEPSEEK_VISION_MODEL", "deepseek-flash")
MAX_IMAGES = 4                 # bitta so'rovga ko'pi bilan
MAX_IMAGE_BYTES = 10 * 1024 * 1024
IMG_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MODELS = {"deepseek-chat": "⚡ Chat (tez)", "deepseek-reasoner": "🧠 Reasoner (chuqur, sekin)"}
FIXES = 2                      # kod tekshiruvdan o'tmasa AI ga qaytarib tuzattirish urinishlari
KEEP_TAIL = 8                  # tarixda: system (docs shu yerda, o'chirilmaydi) + oxirgi 8 ta xabar (juft — savol/javob juftligi buzilmaydi)
TTL = 6 * 3600                 # suhbat xotirada shuncha turadi (restartda ham tozalanadi)
MAX_TOKENS = {"deepseek-chat": 8000, "deepseek-reasoner": 32000}

SYSTEM = """You write Telegram USERBOT modules (single Python files) for the "VPS Manager" userbot (Telethon).
If a <QO'LLANMA> block follows this prompt, it is the official module-writing guide of this userbot. Follow it EXACTLY.
Hard rules:
- The user may attach images (screenshots, design references, error messages). Use them as guidance for what the module should do or look like; never describe them at length.
- Output: a SHORT explanation (1-3 sentences, in the user's language, Uzbek by default) and then exactly ONE complete module in a single ```python block. No other code blocks.
- Metadata (NAME, DESCRIPTION, VERSION, AUTHOR, CONFIG, COMMANDS) must be plain literals at module top level. NAME: a-z, 0-9, _ (starts with a letter, 2..24 chars).
- Every COMMANDS key needs `async def cmd_<key>(e, args, ctx)`. Hooks (on_load(ctx), on_unload(ctx), on_message(e, ctx), on_config(ctx, key, value)) are optional and must be `async def`.
- Configurable values go to CONFIG and are read via ctx.cfg["key"] at call time (never cache them). Persistent state: ctx.data + ctx.save().
- Reply to the user's own command message with `await e.edit(text, parse_mode=None)`. Never use blocking calls (time.sleep, requests); use asyncio / Telethon.
- PREMIUM (custom) EMOJI: the user's text may contain markers like `<tg-emoji emoji-id="5368324170671202286">⚡️</tg-emoji>` (ID + fallback emoji). Copy such markers into the module EXACTLY (same ID, same fallback) — never replace them with a plain emoji and never invent IDs. Messages containing them must be sent/edited as HTML with `parse_mode=ctx.html`, e.g. `await e.edit(f'<tg-emoji emoji-id="5368324170671202286">⚡️</tg-emoji> Ping: <b>{ms}</b> ms', parse_mode=ctx.html)` (or build the tag with `ctx.emoji(ID, "⚡️")`). In that HTML text escape every dynamic value with `html.escape(str(v))` (import html). Keep the user's wording/layout exactly as asked. When modifying an existing module, KEEP its existing `<tg-emoji>` tags and `parse_mode=ctx.html` unless the user asks to change them. Without premium emoji keep `parse_mode=None`.
- Do not use command names that are reserved or already used by installed modules (listed in the guide).
- Third-party libraries are installed AUTOMATICALLY by the userbot when the module is installed (and removed with the module). Prefer the standard library, aiohttp and Telethon (already installed). If you need another PyPI package, import it normally AND list its PIP name in `REQUIREMENTS = ["pillow"]` (a plain literal list, e.g. import PIL → "pillow", cv2 → "opencv-python-headless", bs4 → "beautifulsoup4"). Never pip-install from code, never use URLs/paths in REQUIREMENTS, at most 10 packages. Pick only real, well-known PyPI packages.
- Avoid os/subprocess/socket/shutil/sys unless the user explicitly needs them. Comments and user-facing texts in Uzbek unless asked otherwise.
- Refuse (explain briefly, NO code block) requests for spam/mass messaging, harassment, account theft, hacking, or anything harming other people's accounts.
- When asked to change the module, return the FULL updated file again (same NAME unless asked otherwise, bump VERSION)."""


class AIError(Exception):
    pass


# ───────── tarmoq (yagona joy — sinovda almashtiriladi) ─────────
async def _http(method: str, path: str, key: str, payload: dict | None, timeout: int):
    import aiohttp
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout, sock_connect=15)) as s:
            async with s.request(method, BASE + path, json=payload,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}) as r:
                txt = await r.text()
                try: body = await r.json(content_type=None)
                except Exception: body = None
                return r.status, body if isinstance(body, dict) else txt
    except aiohttp.ClientError as ex:
        raise AIError(f"DeepSeek bilan aloqa yo'q ({type(ex).__name__})")
    except TimeoutError:
        raise AIError("DeepSeek javob bermadi (vaqt tugadi). Qayta urinib ko'ring yoki ⚡ Chat modelini tanlang.")


def _err_text(status: int, body) -> str:
    msg = ""
    if isinstance(body, dict):
        e = body.get("error")
        msg = (e.get("message") if isinstance(e, dict) else str(e or ""))[:200]
    if status == 400 and "image" in msg.lower():
        return (f"Rasmni bu model qabul qilmadi ({msg}). Rasm so'rovlari {VISION_MODEL} modelida bajariladi — "
                "DEEPSEEK_VISION_MODEL (.env) ni DeepSeek hujjatidagi joriy vision model nomiga o'zgartiring yoki rasmsiz yozing.")
    return {401: "API kalit noto'g'ri yoki bekor qilingan", 402: "DeepSeek hisobida mablag' yetarli emas (balansni to'ldiring)",
            429: "So'rovlar juda ko'p — birozdan keyin urinib ko'ring", 400: f"So'rov rad etildi: {msg}",
            422: f"So'rov rad etildi: {msg}"}.get(status, f"DeepSeek xatosi {status}" + (f": {msg}" if msg else ""))


async def check_key(key: str) -> None:
    """Kalitni bepul /models so'rovi bilan tekshiradi. Yaroqsiz bo'lsa AIError."""
    st, body = await _http("GET", "/models", key, None, 20)
    if st != 200:
        raise AIError(_err_text(st, body))


async def chat(key: str, model: str, messages: list[dict], timeout: int = 300) -> str:
    if any(isinstance(m.get("content"), list) for m in messages):     # tarixda rasm bor — butun so'rov vision modelida
        model = VISION_MODEL
    payload = {"model": model, "messages": messages, "max_tokens": MAX_TOKENS.get(model, 8000), "stream": False}
    if model == "deepseek-chat":
        payload["temperature"] = 0.3
    st, body = await _http("POST", "/chat/completions", key, payload, timeout)
    if st != 200:
        raise AIError(_err_text(st, body))
    try:
        ch = body["choices"][0]
        text = (ch["message"].get("content") or "").strip()
    except (KeyError, IndexError, TypeError, AttributeError):
        raise AIError("DeepSeek kutilmagan javob qaytardi")
    if ch.get("finish_reason") == "length":
        raise AIError("Javob uzilib qoldi (juda uzun modul). Soddaroq yoki bo'lib-bo'lib so'rang.")
    if not text:
        raise AIError("DeepSeek bo'sh javob qaytardi")
    return text


# ───────── kodni ajratish va tekshirish ─────────
_FENCE = re.compile(r"```[ \t]*(?:python|py)?[ \t]*\n(.*?)```", re.S | re.I)


def extract(reply: str) -> tuple[str | None, str]:
    """AI javobidan (kod, izoh). Kod topilmasa kod=None."""
    blocks = [b for b in _FENCE.findall(reply) if "NAME" in b]
    if blocks:
        code = max(blocks, key=len)
        note = _FENCE.sub("", reply).strip()
    elif re.search(r"^NAME\s*=", reply, re.M) and "```" not in reply:
        code, note = reply, ""
    else:
        return None, reply.strip()
    return code.strip("\n") + "\n", re.sub(r"\n{3,}", "\n\n", note)


_SIGS = {"on_load": (1, 1), "on_unload": (1, 1), "on_message": (2, 2), "on_config": (3, 3)}     # (eng kam, eng ko'p) argument


def lint(src: str, meta: dict) -> None:
    """AI ning odatiy xatolari: funksiya imzolari. (Qo'lda o'rnatishga ta'sir qilmaydi.)"""
    tree = ast.parse(src)
    for n in tree.body:
        if not isinstance(n, ast.AsyncFunctionDef):
            continue
        a = n.args
        if a.vararg or a.kwarg:
            continue
        cnt, lo = len(a.posonlyargs) + len(a.args), len(a.posonlyargs) + len(a.args) - len(a.defaults)
        if n.name.startswith("cmd_") and n.name[4:] in meta["commands"] and not lo <= 3 <= cnt:
            raise M.ModError(f"{n.name} imzosi async def {n.name}(e, args, ctx) bo'lishi kerak")
        if n.name in _SIGS and not lo <= _SIGS[n.name][0] <= cnt:
            raise M.ModError(f"{n.name} imzosi: {M.HOOK_DOC[n.name][0]}")


# ───────── suhbat ─────────
@dataclass
class Session:
    msgs: list = field(default_factory=lambda: [{"role": "system", "content": SYSTEM}])
    docs_sent: bool = False         # docs suhbat tarixida bormi (bir marta yuboriladi)
    busy: bool = False
    ts: float = field(default_factory=time.time)
    last: dict | None = None        # oxirgi muvaffaqiyatli natija {"name", "version"}

    @property
    def turns(self) -> int:
        return sum(1 for m in self.msgs if m["role"] == "user")


SESS: dict[int, Session] = {}


def session(uid: int) -> Session:
    s = SESS.get(uid)
    if s and time.time() - s.ts > TTL:
        s = None
    if s is None:
        s = SESS[uid] = Session()
    return s


def reset(uid: int) -> None:
    SESS.pop(uid, None)


def _trim(msgs: list) -> None:
    """Tarix o'smasin: system (docs shu yerda — HECH QACHON o'chirilmaydi) + oxirgi KEEP_TAIL ta xabar."""
    if len(msgs) > 1 + KEEP_TAIL:
        msgs[1:] = msgs[-KEEP_TAIL:]


def img_part(mime: str, raw: bytes) -> dict:
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(raw).decode()}"}}


def _content(text: str, images: list | None):
    if not images:
        return text
    return [{"type": "text", "text": text}] + [img_part(mime, raw) for mime, raw in images[:MAX_IMAGES]]


def _strip_images(msgs: list) -> None:
    """Rasmlar faqat joriy so'rov uchun (tuzatish urinishlari ham shu so'rovda). Keyin tarixdan olib tashlanadi: xotira, token va model almashinuvi."""
    for m in msgs:
        if isinstance(m.get("content"), list):
            n = sum(1 for p in m["content"] if p.get("type") == "image_url")
            txt = "".join(p.get("text", "") for p in m["content"] if p.get("type") == "text")
            m["content"] = txt + f"\n[{n} ta rasm biriktirilgan edi]"


async def generate(uid: int, text: str, *, key: str, model: str, send_docs: bool, docs: str, validate, images: list | None = None) -> dict:
    """Foydalanuvchi so'rovidan modul yasaydi. validate(code) -> meta (ModError tashlashi mumkin).
    Muvaffaqiyat: {"src","meta","note","fixes","docs_now"}; xato: AIError (suhbat tarixi so'rov oldingi holatga qaytariladi)."""
    s = session(uid)
    if s.busy:
        raise AIError("Oldingi so'rov hali ishlayapti — kuting.")
    s.busy, snap, docs_was, sys_was = True, len(s.msgs), s.docs_sent, s.msgs[0]["content"]
    try:
        docs_now = False
        if send_docs and not s.docs_sent:                    # docs — suhbat tarixiga FAQAT BIR MARTA (system xabarga) qo'shiladi
            s.msgs[0]["content"] = f"{SYSTEM}\n\n<QO'LLANMA>\n{docs}\n</QO'LLANMA>"
            docs_now = True
        s.msgs.append({"role": "user", "content": _content(text, images)})
        fixes = 0
        while True:
            reply = await chat(key, model, s.msgs)
            s.msgs.append({"role": "assistant", "content": reply})
            code, note = extract(reply)
            if code is None:
                raise AIError("AI modul kodini bermadi: " + (note[:400] or "(bo'sh javob)"))
            try:
                meta = validate(code)
                lint(code, meta)
                break
            except (M.ModError, SyntaxError) as ex:
                err = str(ex)
                if fixes >= FIXES:
                    raise AIError(f"AI yaratgan kod {FIXES + 1} urinishda ham tekshiruvdan o'tmadi: {err[:300]}")
                fixes += 1
                s.msgs.append({"role": "user", "content": f"Kod tekshiruvdan o'tmadi: {err}\nTuzatib, TO'LIQ modul faylini bitta ```python blokda qayta yuboring."})
        if docs_now:
            s.docs_sent = True
        s.ts, s.last = time.time(), {"name": meta["name"], "version": meta["version"]}
        _strip_images(s.msgs)
        _trim(s.msgs)
        return {"src": code, "meta": meta, "note": note, "fixes": fixes, "docs_now": docs_now}
    except BaseException:
        del s.msgs[snap:]                                    # muvaffaqiyatsiz urinish tarixda qolmaydi (docs ham: keyingi safar qayta yuboriladi)
        s.msgs[0]["content"], s.docs_sent = sys_was, docs_was
        raise
    finally:
        s.busy = False
