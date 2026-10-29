"""Userbot yadrosi (Telethon) — aiogram'siz. Har bir admin uchun alohida userbot.

Holat USERBOT_DIR/<admin_id>.json da (api_id, api_hash, session, sozlamalar, AFK, eslatmalar) — chmod 600, .bak nusxa bilan.
Loyiha papkasidan TASHQARIDA: ZIP bilan yangilash / restart / reboot uni o'chirmaydi.

Avto-davom: `enabled` bayrog'i faqat foydalanuvchi ⏹ Stop bosganda o'chadi. Bot qayta ko'tarilganda `supervise()` har bir
userbotni TO'XTAGAN JOYIDAN davom ettiradi: soat (shrift/joy/shablon/zona), AFK (kimga javob berilgani ham), eslatmalar.
"""
import ast, asyncio, html, importlib.util, inspect, io, json, operator as op, os, re, shutil, sys, time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import psutil
from telethon import TelegramClient, events
from telethon.errors import (AuthKeyDuplicatedError, AuthKeyUnregisteredError, FloodWaitError, SessionExpiredError,
                             SessionRevokedError, UserDeactivatedBanError, UserDeactivatedError)
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.users import GetFullUserRequest

import userbot_emoji as EM
import userbot_libs as L
import userbot_mods as M

USERBOT_VERSION = "2.4"
# Loyiha papkasidan TASHQARIDA — ZIP bilan yangilanganda sessiya yo'qolmaydi
DIR = Path(os.getenv("USERBOT_DIR", "/var/lib/vpsbot-userbot"))
try:
    DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    DIR = Path.home() / ".vpsbot-userbot"
    DIR.mkdir(parents=True, exist_ok=True)
try:
    os.chmod(DIR, 0o700)
except OSError:
    pass
TZ = ZoneInfo(os.getenv("TZ_NAME", "Asia/Tashkent"))
TZS = ["Asia/Tashkent", "Asia/Almaty", "Europe/Moscow", "Europe/Istanbul", "Asia/Dubai", "Europe/London", "UTC"]

HELP = (
    "<b>Userbot buyruqlari</b> (istalgan chatda o'zingiz yozasiz)\n"
    "<code>.ping</code> · <code>.time</code> · <code>.id</code> · <code>.info</code> · <code>.stats</code> · <code>.vps</code>\n"
    "<code>.calc 2+2*3</code> — kalkulyator\n"
    "<code>.type matn</code> — yozilayotgandek animatsiya\n"
    "<code>.del N</code> — oxirgi N ta xabaringizni o'chirish\n"
    "<code>.afk sabab</code> / <code>.unafk</code> — AFK avtojavob (restartdan keyin ham saqlanadi)\n"
    "<code>.remind 10m matn</code> — «Saqlangan xabarlar»ga eslatma (<code>30s 10m 2h 1d 1h30m</code> yoki <code>18:30</code>)\n"
    "<code>.note add nom matn</code> · <code>.note nom</code> · <code>.note del nom</code> · <code>.notes</code>\n"
    "<code>.save</code> — reply qilingan xabarni «Saqlangan»ga yuborish\n"
    "<code>.font nom matn</code> · <code>.fonts</code> — matnni chiroyli shriftda yozish\n\n"
    "<b>Modullar</b> (.py)\n"
    "<code>.mod</code> · <code>.mod info|on|off|reload|del nom</code> · <code>.mod add</code> (.py faylga reply)\n"
    "<code>.mod libs</code> — modullar o'rnatgan kutubxonalar (avtomatik o'rnatiladi, modul o'chsa o'zi ham o'chadi) · <code>.mod libs fix nom</code>\n"
    "<code>.config</code> · <code>.config modul</code> · <code>.config modul o'zgaruvchi qiymat</code> (<code>-r</code> — standart)\n"
    "<code>.docs</code> — modul yozish qo'llanmasi + o'rnatilgan modullar (fayl, «Saqlangan»ga) · <code>.docs modul</code> — bitta modul\n\n"
    "<b>Profil soati</b>\n"
    "<code>.clock on|off</code> · <code>.clock fonts</code> · <code>.clock font nom|№</code>\n"
    "<code>.clock fmt №|shablon</code> — <code>{t}</code> vaqt, <code>{e}</code> 🕒 (soatga mos), <code>{d}</code> sana\n"
    "<code>.clock where last|first|bio</code> — familiya / ism / bio\n"
    "<code>.clock tz Asia/Tashkent</code> — vaqt zonasi"
)


# ───────── shriftlar ─────────
def _rng(start: int, n: int) -> list[str]:
    return [chr(start + i) for i in range(n)]


# raqamli shriftlar (soat uchun): kalit -> (nomi, 10 ta raqam)
DIGITS: dict[str, tuple[str, list[str]]] = {
    "normal": ("Oddiy", list("0123456789")),
    "bold": ("Qalin", _rng(0x1D7CE, 10)),
    "double": ("Qo'sh chiziq", _rng(0x1D7D8, 10)),
    "sans": ("Sans", _rng(0x1D7E2, 10)),
    "sansbold": ("Sans qalin", _rng(0x1D7EC, 10)),
    "mono": ("Mono", _rng(0x1D7F6, 10)),
    "full": ("Keng", _rng(0xFF10, 10)),
    "circle": ("Doira", ["⓪"] + _rng(0x2460, 9)),
    "negcircle": ("To'q doira", ["⓿"] + _rng(0x2776, 9)),
    "dingbat": ("Dingbat", ["⓪"] + _rng(0x2780, 9)),
    "sup": ("Yuqori", list("⁰¹²³⁴⁵⁶⁷⁸⁹")),
    "sub": ("Quyi", _rng(0x2080, 10)),
    "keycap": ("Keycap", [d + "\ufe0f\u20e3" for d in "0123456789"]),
    "seg": ("Segment", _rng(0x1FBF0, 10)),
}
DIGIT_KEYS = list(DIGITS)
SEPS = {"full": "："}

# harfli shriftlar (.font uchun): kalit -> (nomi, bosh harf boshlanishi, kichik harf boshlanishi, istisnolar)
_LET = {
    "bold": ("Qalin", 0x1D400, 0x1D41A, {}),
    "italic": ("Kursiv", 0x1D434, 0x1D44E, {"h": "ℎ"}),
    "bolditalic": ("Qalin kursiv", 0x1D468, 0x1D482, {}),
    "script": ("Yozma", 0x1D4D0, 0x1D4EA, {}),
    "fraktur": ("Gotika", 0x1D56C, 0x1D586, {}),
    "double": ("Qo'sh chiziq", 0x1D538, 0x1D552, {"C": "ℂ", "H": "ℍ", "N": "ℕ", "P": "ℙ", "Q": "ℚ", "R": "ℝ", "Z": "ℤ"}),
    "sans": ("Sans", 0x1D5A0, 0x1D5BA, {}),
    "sansbold": ("Sans qalin", 0x1D5D4, 0x1D5EE, {}),
    "sansitalic": ("Sans kursiv", 0x1D608, 0x1D622, {}),
    "mono": ("Mono", 0x1D670, 0x1D68A, {}),
    "circle": ("Doira", 0x24B6, 0x24D0, {}),
    "full": ("Keng", 0xFF21, 0xFF41, {}),
    "square": ("Kvadrat", 0x1F130, 0x1F130, {}),
    "negsquare": ("To'q kvadrat", 0x1F170, 0x1F170, {}),
}
_SMALL = "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
LETTER_NAMES = {k: v[0] for k, v in _LET.items()} | {"small": "Kichik bosh"}
LETTER_KEYS = list(LETTER_NAMES)


def _letter_map(key: str) -> dict[str, str]:
    m: dict[str, str] = {}
    if key == "small":
        for i, ch in enumerate(_SMALL):
            m[chr(97 + i)] = m[chr(65 + i)] = ch
        return m
    _, up, lo, exc = _LET[key]
    for i in range(26):
        m[chr(65 + i)] = exc.get(chr(65 + i), chr(up + i))
        m[chr(97 + i)] = exc.get(chr(97 + i), chr(lo + i))
    if key in ("square", "negsquare"):          # faqat bosh harf — kichiklari ham shunga o'tadi
        for i in range(26):
            m[chr(97 + i)] = chr(up + i)
    return m


_LMAPS = {k: _letter_map(k) for k in LETTER_KEYS}


def digits_in(font: str, s: str) -> str:
    """Vaqt/sana qatoridagi raqamlarni tanlangan shriftga o'tkazadi (':' ham moslanadi)."""
    ds = DIGITS.get(font, DIGITS["normal"])[1]
    sep = SEPS.get(font, ":")
    return "".join(ds[int(ch)] if ch.isdigit() else (sep if ch == ":" else ch) for ch in s)


def stylize(key: str, text: str) -> str:
    m = _LMAPS.get(key, {})
    dm = DIGITS[key][1] if key in DIGITS and key != "normal" else None
    out = []
    for ch in text:
        if ch in m:
            out.append(m[ch])
        elif dm and ch.isdigit() and ch.isascii():
            out.append(dm[int(ch)])
        else:
            out.append(ch)
    return "".join(out)


def pick(arg: str, keys: list[str]) -> str | None:
    """«3» (tartib raqami) yoki nom bo'yicha kalit topadi."""
    arg = arg.strip().lower()
    if arg.isdigit():
        i = int(arg) - 1
        return keys[i] if 0 <= i < len(keys) else None
    return arg if arg in keys else None


# ───────── soat shablonlari ─────────
PRESETS = ["| {t}", "{t}", "🕒 {t}", "{e} {t}", "⏰ {t}", "「{t}」", "• {t} •", "{t} · {d}"]
_FACE = "🕛🕐🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚"
_HALF = "🕧🕜🕝🕞🕟🕠🕡🕢🕣🕤🕥🕦"


def tz_of(d: dict | None) -> ZoneInfo:
    try:
        return ZoneInfo((d or {}).get("tz") or "")
    except Exception:
        return TZ


def render(d: dict, dt: datetime | None = None) -> str:
    """Sozlamalarga ko'ra profil soati matni (shrift + shablon)."""
    dt = dt or datetime.now(tz_of(d))
    font = d.get("clock_font", "normal")
    face = (_HALF if dt.minute >= 30 else _FACE)[dt.hour % 12]
    tpl = d.get("clock_tpl") or PRESETS[0]
    return (tpl.replace("{t}", digits_in(font, dt.strftime("%H:%M"))).replace("{e}", face)
            .replace("{d}", digits_in(font, dt.strftime("%d.%m")))).strip()


def parse_when(s: str, tz) -> datetime:
    s = s.strip().lower()
    now = datetime.now(tz)
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", s)
    if m:
        h, mi = int(m[1]), int(m[2])
        if h > 23 or mi > 59:
            raise ValueError("vaqt noto'g'ri")
        t = now.replace(hour=h, minute=mi, second=0, microsecond=0)
        return t if t > now + timedelta(seconds=15) else t + timedelta(days=1)
    parts = re.findall(r"(\d+)([smhd])", s)
    if not parts or "".join(f"{n}{u}" for n, u in parts) != s:
        raise ValueError("vaqt formati: 30s, 10m, 2h, 1d, 1h30m yoki 18:30")
    sec = sum(int(n) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[u] for n, u in parts)
    if not 15 <= sec <= 365 * 86400:
        raise ValueError("kamida 15 soniya, ko'pi bilan 1 yil")
    return now + timedelta(seconds=sec)


def dur(sec: float) -> str:
    sec = int(sec)
    if sec >= 86400:
        return f"{sec // 86400}k {sec % 86400 // 3600}s"
    if sec >= 3600:
        return f"{sec // 3600}s {sec % 3600 // 60}d"
    return f"{max(sec // 60, 0)} daqiqa"


# ───────── sozlamalar fayli ─────────
def _path(uid: int) -> Path:
    return DIR / f"{int(uid)}.json"


def load(uid: int) -> dict | None:
    p = _path(uid)
    for f in (p, p.with_suffix(".bak")):       # asosiy fayl buzilsa — zaxira nusxadan
        try:
            d = json.loads(f.read_text())
            if isinstance(d, dict):
                return d
        except (OSError, ValueError):
            continue
    return None


def save(uid: int, data: dict) -> None:
    p = _path(uid)
    tmp = p.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    if p.exists():
        try:
            shutil.copy2(p, p.with_suffix(".bak"))
        except OSError:
            pass
    os.replace(tmp, p)


def delete(uid: int) -> None:
    for suf in (".json", ".bak", ".tmp"):
        _path(uid).with_suffix(suf).unlink(missing_ok=True)
    shutil.rmtree(DIR / "modules" / str(int(uid)), ignore_errors=True)
    shutil.rmtree(DIR / "docs" / str(int(uid)), ignore_errors=True)


def installed(uid: int) -> bool:
    d = load(uid)
    return bool(d and d.get("session"))


def wants_run(d: dict | None) -> bool:
    """Foydalanuvchi to'xtatmagan bo'lsa — restart/yangilanishdan keyin ham ishlashi kerak."""
    return bool(d and d.get("session") and d.get("enabled", d.get("autostart", True)))


def all_uids() -> list[int]:
    try:
        return sorted(int(p.stem) for p in DIR.glob("*.json") if p.stem.isdigit())
    except OSError:
        return []


# ───────── yordamchilar ─────────
def now_str(fmt: str = "%H:%M", tz=None) -> str:
    return datetime.now(tz or TZ).strftime(fmt)


_OPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow,
        ast.Mod: op.mod, ast.FloorDiv: op.floordiv, ast.USub: op.neg, ast.UAdd: op.pos}


def safe_eval(node):
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        a, b = safe_eval(node.left), safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and (abs(b) > 100 or abs(a) > 1e6):
            raise ValueError("daraja juda katta")
        return _OPS[type(node.op)](a, b)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](safe_eval(node.operand))
    raise ValueError("noto'g'ri ifoda")


def make_client(api_id: int, api_hash: str, session: str = "") -> TelegramClient:
    return TelegramClient(StringSession(session), api_id, api_hash, device_model="VPS Manager",
                          app_version=USERBOT_VERSION, connection_retries=10, retry_delay=3, auto_reconnect=True)


# ───────── modullar: saqlash (userbot ishlamayotgan bo'lsa ham ishlaydi) ─────────
MODDIR = DIR / "modules"        # USERBOT_DIR/modules/<uid>/<nom>.py — loyiha papkasidan tashqarida (ZIP yangilash o'chirmaydi)


def mods_cfg(uid: int) -> dict:
    """{nom: {"enabled", "config": {...}, "data": {...}, "version"}}"""
    return dict((load(uid) or {}).get("mods") or {})


def _mods_write(uid: int, mods: dict) -> None:
    d = load(uid)
    if d is None:
        raise M.ModError("Userbot o'rnatilmagan")
    d["mods"] = mods
    save(uid, d)


def _docs_sync(uid: int) -> None:
    """Modul/config/holat o'zgarganda docs faylini yangilaydi (xato bo'lsa jim — asosiy ishga halal bermaydi)."""
    try:
        import userbot_docs
        userbot_docs.sync(uid)
    except Exception as ex:
        print("docs yangilanmadi:", ex)


# ───────── AI (DeepSeek) sozlamalari: kalit foydalanuvchi tomonidan Telegramda kiritiladi ─────────
AI_DEFAULT = {"key": "", "model": "deepseek-chat", "send_docs": True}


def ai_cfg(uid: int) -> dict:
    return {**AI_DEFAULT, **((load(uid) or {}).get("ai") or {})}


def ai_set(uid: int, **kw) -> dict:
    d = load(uid)
    if d is None:
        raise M.ModError("Userbot o'rnatilmagan")
    cur = {**AI_DEFAULT, **(d.get("ai") or {}), **kw}
    d["ai"] = cur
    save(uid, d)
    return cur


def mod_path(uid: int, name: str) -> Path:
    return MODDIR / str(int(uid)) / f"{name}.py"


def mod_meta(uid: int, name: str) -> dict | None:
    try:
        return M.parse_meta(mod_path(uid, name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def mod_values(uid: int, name: str, meta: dict | None = None) -> dict:
    meta = meta or mod_meta(uid, name) or {"config": {}}
    st = (mods_cfg(uid).get(name) or {}).get("config") or {}
    return {k: st.get(k, sp["default"]) for k, sp in meta["config"].items()}


def mod_check(uid: int, raw: bytes | str) -> tuple[dict, str]:
    """Modulni YOZMASDAN tekshiradi (sintaksis, metadata, boshqa modullar bilan buyruq to'qnashuvi). (meta, matn) qaytaradi."""
    try:
        src = raw if isinstance(raw, str) else raw.decode("utf-8")
    except UnicodeDecodeError:
        raise M.ModError("Fayl UTF-8 matn bo'lishi kerak")
    meta = M.parse_meta(src)
    if load(uid) is None:
        raise M.ModError("Userbot o'rnatilmagan")
    for other in mods_cfg(uid):
        om = mod_meta(uid, other) if other != meta["name"] else None
        clash = sorted(set((om or {}).get("commands", {})) & set(meta["commands"]))
        if clash:
            raise M.ModError(f".{clash[0]} buyrug'i «{other}» modulida band")
    return meta, src


def mod_install(uid: int, raw: bytes, libs: dict | None = None) -> tuple[dict, str | None]:
    """Modulni tekshirib saqlaydi (kodni ishga tushirmaydi). (meta, eski_versiya) qaytaradi.
    libs={"needs": [...], "new": [...]} — shu modul uchun o'rnatilgan kutubxonalar (userbot_libs) yozuvga qo'shiladi."""
    meta, src = mod_check(uid, raw)
    name, mods = meta["name"], mods_cfg(uid)
    p = mod_path(uid, name)
    p.parent.mkdir(parents=True, exist_ok=True)
    try: os.chmod(p.parent, 0o700)
    except OSError: pass
    tmp = p.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(src)
    os.replace(tmp, p)
    old = mods.get(name)
    cfgv = {}
    for k, sp in meta["config"].items():       # yangilashda eski qiymatlar (hali yaroqli bo'lsa) saqlanadi
        if old and k in (old.get("config") or {}):
            try: cfgv[k] = M.coerce(sp, old["config"][k])
            except M.ModError: pass
    mods[name] = {"enabled": old.get("enabled", True) if old else True, "config": cfgv,
                  "data": (old or {}).get("data", {}), "version": meta["version"]}
    if (old or {}).get("pip"):                  # yangilashda eski kutubxona yozuvi saqlanadi (o'chirishda kerak)
        mods[name]["pip"] = old["pip"]
    if libs:
        L.add_record(mods[name], libs.get("needs", []), libs.get("new", []))
    _mods_write(uid, mods)
    _docs_sync(uid)
    return meta, (old or {}).get("version")


def mod_remove(uid: int, name: str) -> list[str]:
    """Modul faylini va yozuvini o'chiradi. O'CHIRILISHI kerak kutubxonalar ro'yxatini qaytaradi (o'chirishni mod_delete qiladi)."""
    mods = mods_cfg(uid)
    rm = L.release(mods, name)
    _mods_write(uid, mods)
    mod_path(uid, name).unlink(missing_ok=True)
    _docs_sync(uid)
    return rm


def mod_libs_add(uid: int, name: str, needs: list[str], new: list[dict]) -> None:
    """Modul yozuviga kutubxonalar ma'lumotini qo'shadi (modul yuklash paytida topilgan yetishmayotganlar uchun)."""
    mods = mods_cfg(uid)
    if name in mods:
        L.add_record(mods[name], needs, new)
        _mods_write(uid, mods)


async def mod_install_full(uid: int, raw, progress=None) -> tuple[dict, str | None, dict]:
    """Modulni tekshiradi → KUTUBXONALARINI avtomatik o'rnatadi → saqlaydi. (meta, eski_versiya, {"installed": [...], "need": [...]}).
    progress(list_of_reqs) — o'rnatish boshlanishidan oldin chaqiriladi (UI uchun). Kutubxona o'rnatilmasa modul saqlanmaydi."""
    meta, src = mod_check(uid, raw)
    pl = L.plan(meta)
    new = []
    if pl["install"]:
        if progress:
            await progress(pl["install"])
        new = await L.install(pl["install"])
    try:
        meta, old = mod_install(uid, src, libs={"needs": pl["needs"], "new": new})
    except BaseException:
        if new:
            await L.uninstall([x["name"] for x in new])
        raise
    return meta, old, {"installed": [x["name"] for x in new], "need": pl["install"]}


def mod_set(uid: int, name: str, key: str, raw) -> object:
    """Config qiymatini tekshirib saqlaydi. raw=None — standartga qaytarish."""
    meta, mods = mod_meta(uid, name), mods_cfg(uid)
    if not meta or name not in mods:
        raise M.ModError(f"«{name}» moduli yo'q")
    spec = meta["config"].get(key)
    if not spec:
        raise M.ModError(f"«{name}» da «{key}» o'zgaruvchisi yo'q")
    cfg = dict(mods[name].get("config") or {})
    if raw is None:
        cfg.pop(key, None)
        val = spec["default"]
    else:
        val = cfg[key] = M.coerce(spec, raw)
    mods[name]["config"] = cfg
    _mods_write(uid, mods)
    _docs_sync(uid)
    return val


class _CfgView:
    """ctx.cfg["kalit"] — joriy qiymat (har safar yangisi: .config bilan o'zgartirilsa darhol ko'rinadi)."""
    def __init__(self, uid, name, meta): self._u, self._n, self._m = uid, name, meta
    def all(self) -> dict: return mod_values(self._u, self._n, self._m)
    def __getitem__(self, k): return self.all()[k]
    def get(self, k, default=None): return self.all().get(k, default)
    def __iter__(self): return iter(self.all())
    def __repr__(self): return repr(self.all())


class ModCtx:
    """Modulga beriladigan kontekst: client, me, cfg, data (doimiy), on(event), spawn(coro), log()."""
    ATTRS = {      # __init__ da o'rnatiladigan atributlar — docs (userbot_docs.py) shundan oladi
        "uid": "Userbot egasining Telegram ID si.",
        "name": "Modulning NAME qiymati.",
        "meta": "Tahlil qilingan metadata (name, description, version, author, config, commands, hooks...).",
        "cfg": "Config qiymatlari: `ctx.cfg[\"kalit\"]` / `ctx.cfg.get(\"kalit\", x)` / `ctx.cfg.all()`. Har safar joriy qiymatni beradi — `.config` bilan o'zgartirilsa darhol ko'rinadi.",
    }

    def __init__(self, ub, name: str, meta: dict):
        self._ub, self.uid, self.name, self.meta = ub, ub.uid, name, meta
        self.cfg = _CfgView(ub.uid, name, meta)
        self._handlers: list = []
        self._tasks: list = []
        self._data: dict | None = None

    @property
    def client(self):
        """Telethon TelegramClient (userbot hisobi nomidan)."""
        return self._ub.client

    @property
    def me(self):
        """Userbot egasi (Telethon User)."""
        return self._ub.me

    @property
    def data(self) -> dict:
        """Doimiy xotira (dict, JSON-ga o'tadigan qiymatlar). O'zgartirgach `ctx.save()` chaqiring; restart/ZIP yangilanishdan keyin ham saqlanadi."""
        if self._data is None:
            self._data = dict((mods_cfg(self.uid).get(self.name) or {}).get("data") or {})
        return self._data

    def save(self) -> None:
        """`ctx.data` ni diskka yozadi (hajm chegarasi — DATA_MAX)."""
        if len(json.dumps(self.data, ensure_ascii=False).encode("utf-8")) > M.DATA_MAX:
            raise M.ModError(f"ctx.data {M.DATA_MAX // 1024} KB dan oshdi")
        mods = mods_cfg(self.uid)
        if self.name in mods:
            mods[self.name]["data"] = self.data
            _mods_write(self.uid, mods)

    def on(self, event):
        """Dekorator: `@ctx.on(events.NewMessage(...))` — Telethon handleri; modul o'chirilganda avtomatik olib tashlanadi."""
        def deco(cb):
            self.client.add_event_handler(cb, event)
            self._handlers.append((cb, event))
            return cb
        return deco

    @property
    def html(self):
        """`parse_mode=ctx.html` — HTML (<b>, <i>, <code>, <a href>...) VA premium emoji: `<tg-emoji emoji-id="ID">⚡️</tg-emoji>`. Masalan: `await e.edit(f'{ctx.emoji(5368324170671202286, "⚡️")} Ping: <b>{ms}</b> ms', parse_mode=ctx.html)`. Premium bo'lmagan joyda ichidagi oddiy emoji ko'rinadi. O'zgaruvchan matnlarni `html.escape()` bilan o'tkazing."""
        return EM.PremiumHTML

    def emoji(self, emoji_id: int, fallback: str = "⭐") -> str:
        """`ctx.emoji(ID, "⚡️")` — premium emoji uchun `<tg-emoji>` HTML belgisini qaytaradi; `parse_mode=ctx.html` bilan yuboriladigan matn ichiga qo'yiladi."""
        return EM.tag(emoji_id, fallback)

    def spawn(self, coro) -> asyncio.Task:
        """`ctx.spawn(coro)` — fon vazifa; modul o'chirilganda bekor qilinadi, xatosi userbotni yiqitmaydi."""
        async def run():
            try: await coro
            except asyncio.CancelledError: raise
            except Exception as ex: self.log("vazifa xatosi:", ex)
        t = asyncio.create_task(run())
        self._tasks.append(t)
        return t

    def log(self, *a) -> None:
        """`ctx.log(...)` — bot logiga `[modul:nom]` belgisi bilan yozadi."""
        print(f"[modul:{self.name}]", *a)

    async def _cleanup(self) -> None:
        for cb, ev in self._handlers:
            try: self.client.remove_event_handler(cb, ev)
            except Exception: pass
        for t in self._tasks:
            if not t.done():
                t.cancel()
        for t in self._tasks:
            try: await t
            except (asyncio.CancelledError, Exception): pass
        self._handlers.clear(); self._tasks.clear()


class LoadedMod:
    def __init__(self, name, module, meta, ctx):
        self.name, self.module, self.meta, self.ctx = name, module, meta, ctx
        self.on_message = getattr(module, "on_message", None)


class SessionDead(RuntimeError):
    """Sessiya Telegram tomonidan bekor qilingan — qayta urinish foydasiz, qayta o'rnatish kerak."""


_DEAD = (AuthKeyUnregisteredError, AuthKeyDuplicatedError, SessionRevokedError, SessionExpiredError,
         UserDeactivatedError, UserDeactivatedBanError)


# ───────── userbot ─────────
class UserBot:
    def __init__(self, uid: int):
        self.uid = uid
        self.client: TelegramClient | None = None
        self.me = None
        self.started = 0.0
        self.error = ""
        self.lock = asyncio.Lock()
        self.clock_task: asyncio.Task | None = None
        self._poke = asyncio.Event()
        self.afk_reason: str | None = None
        self.afk_since = 0.0
        self.afk_notified: set[int] = set()
        self.afk_chat_ts: dict[int, float] = {}
        self.mods: dict[str, LoadedMod] = {}
        self.mod_cmds: dict[str, tuple[LoadedMod, object]] = {}
        self.mod_err: dict[str, str] = {}
        self.fails, self.next_try, self.disc_since, self.last_save, self.alerted = 0, 0.0, 0.0, 0.0, False

    # --- sozlama ---
    def cfg(self) -> dict:
        return load(self.uid) or {}

    def cfg_set(self, **kw) -> None:
        d = load(self.uid)
        if not d:               # o'chirilgan (logout) userbot fayli qayta paydo bo'lmasin
            return
        d.update(kw)
        save(self.uid, d)

    def poke(self) -> None:
        self._poke.set()

    @property
    def running(self) -> bool:
        return bool(self.client and self.client.is_connected() and self.me)

    @property
    def clock_on(self) -> bool:
        return bool(self.clock_task and not self.clock_task.done())

    # --- start / stop ---
    async def start(self, *, persist: bool = True) -> None:
        """persist=True — foydalanuvchi bosgan Start (avto-davom yoqiladi); False — supervisor (bayroqqa tegmaydi)."""
        async with self.lock:
            await self._start(persist)

    async def _start(self, persist: bool) -> None:
        if self.client and not self.running:
            await self._teardown(restore=False)
        if self.running:
            if persist:
                self.cfg_set(enabled=True)
            return
        d = self.cfg()
        if not d.get("session"):
            raise RuntimeError("Sessiya yo'q — avval o'rnating.")
        self.error = ""
        client = make_client(int(d["api_id"]), d["api_hash"], d["session"])
        try:
            await client.connect()
            if not await client.is_user_authorized():
                raise SessionDead("Sessiya yaroqsiz (Telegram'dan chiqarilgan). Qayta o'rnating.")
            self.me = await client.get_me()
        except Exception as e:
            self.error = str(e)[:200]
            try: await client.disconnect()
            except Exception: pass
            if isinstance(e, _DEAD) and not isinstance(e, SessionDead):
                raise SessionDead(f"Sessiya bekor qilingan ({type(e).__name__}). Qayta o'rnating.") from e
            raise
        self.client = client
        self.started, self.disc_since, self.last_save = time.time(), 0.0, time.time()
        self._load_afk(d)
        self._register()
        await self._mods_load_all()
        if persist:
            self.cfg_set(enabled=True)
        if d.get("clock"):
            self.clock_task = asyncio.create_task(self._clock_loop())

    async def stop(self) -> None:
        """Foydalanuvchi to'xtatdi: restartdan keyin ham o'chiq turadi."""
        async with self.lock:
            self.cfg_set(enabled=False)
            await self._teardown(restore=True)

    async def suspend(self) -> None:
        """Bot restart/yangilanishda: bayroqlar SAQLANADI — yangi jarayon davom ettiradi."""
        async with self.lock:
            await self._teardown(restore=True)

    async def _teardown(self, restore: bool) -> None:
        t, self.clock_task = self.clock_task, None
        if t and not t.done():
            t.cancel()
            try: await t
            except (asyncio.CancelledError, Exception): pass
        await self._mods_unload_all()
        c = self.client
        if c:
            if restore and c.is_connected():
                await self._restore_applied()
            self._save_session()
            try: await c.disconnect()
            except Exception: pass
        self.client, self.me = None, None

    def _save_session(self) -> None:
        """Telethon sessiyasi (DC/auth key) o'zgargan bo'lsa — faylga yangilab qo'yamiz."""
        try:
            s = self.client.session.save() if self.client else ""
            if s and self.cfg().get("session") != s:
                self.cfg_set(session=s)
        except Exception:
            pass

    async def logout(self) -> None:
        """Telegram'dagi sessiyani ham tugatadi va fayllarni o'chiradi."""
        async with self.lock:
            try: await self.clock_off()
            except Exception: pass
            if self.client:
                try: await self.client.log_out()
                except Exception: pass
            await self._teardown(restore=False)
            await _purge_libs(self.uid)
            delete(self.uid)

    # --- profil soati ---
    async def clock_on_(self) -> None:
        self.cfg_set(clock=True)
        if self.client and not self.clock_on:
            self.clock_task = asyncio.create_task(self._clock_loop())
        self.poke()

    async def clock_off(self, keep_flag: bool = False) -> None:
        t, self.clock_task = self.clock_task, None
        if t and not t.done():
            t.cancel()
            try: await t
            except (asyncio.CancelledError, Exception): pass
        if self.client and self.client.is_connected():
            await self._restore_applied()
        d = self.cfg()
        if d and not keep_flag:
            d.pop("orig", None)
            d.update(clock=False, clock_applied=None)
            save(self.uid, d)

    def set_clock(self, **kw) -> None:
        """Soat sozlamalarini saqlaydi (userbot ishlamayotgan bo'lsa ham) va darhol qo'llaydi."""
        self.cfg_set(**kw)
        self.poke()

    async def _capture_orig(self) -> None:
        if self.cfg().get("orig"):
            return
        me = await self.client.get_me()
        about = ""
        try:
            about = (await self.client(GetFullUserRequest(me))).full_user.about or ""
        except Exception:
            pass
        self.cfg_set(orig={"first": me.first_name or "", "last": me.last_name or "", "about": about})

    def _kw(self, where: str, text: str | None, orig: dict) -> dict:
        """where: last|first|bio. text=None — asl qiymatni tiklash."""
        if where == "first":
            return {"first_name": (orig["first"] if text is None else f"{orig['first']} {text}")[:64]}
        if where == "bio":
            lim = 140 if getattr(self.me, "premium", False) else 70
            if text is None:
                return {"about": orig["about"]}
            about = f"{orig['about']} {text}".strip()
            return {"about": (about if len(about) <= lim else text)[:lim]}
        return {"last_name": orig["last"] if text is None else text[:64]}

    async def _restore_applied(self) -> None:
        d = self.cfg()
        w, orig = d.get("clock_applied"), d.get("orig")
        if not (w and orig and self.client):
            return
        try:
            await self.client(UpdateProfileRequest(**self._kw(w, None, orig)))
            self.cfg_set(clock_applied=None)
        except Exception:
            pass

    async def _clock_loop(self) -> None:
        last = None
        try:
            await self._capture_orig()
            while True:
                self._poke.clear()
                d = self.cfg()
                where, orig, applied = d.get("clock_where", "last"), d.get("orig") or {}, d.get("clock_applied")
                if applied and applied != where:        # joy almashtirildi — eskisini tiklaymiz
                    await self._restore_applied()
                    last = None
                text = render(d)
                if text != last and orig:
                    try:
                        await self.client(UpdateProfileRequest(**self._kw(where, text, orig)))
                        last = text
                        if d.get("clock_applied") != where:
                            self.cfg_set(clock_applied=where)
                    except FloodWaitError as e:
                        await asyncio.sleep(e.seconds + 1)
                        continue
                    except Exception as e:
                        self.error = f"soat: {str(e)[:150]}"
                        await asyncio.sleep(30)
                        continue
                wait = 60 - datetime.now(tz_of(d)).second + 1
                try:
                    await asyncio.wait_for(self._poke.wait(), wait)
                except asyncio.TimeoutError:
                    pass
        except asyncio.CancelledError:
            raise

    # --- AFK (restartdan keyin ham saqlanadi) ---
    def _load_afk(self, d: dict) -> None:
        a = d.get("afk") or {}
        self.afk_reason, self.afk_since = a.get("reason"), float(a.get("since") or 0)
        self.afk_notified = set(a.get("seen") or [])

    def _afk_save(self) -> None:
        self.cfg_set(afk={"reason": self.afk_reason, "since": self.afk_since,
                          "seen": list(self.afk_notified)[-500:]} if self.afk_reason else None)

    # --- modullar (ish vaqtida) ---
    def help_html(self) -> str:
        extra = "".join(f"\n• <b>{html.escape(n)}</b>: " + " ".join(f"<code>.{c}</code>" for c in lm.meta["commands"])
                        for n, lm in sorted(self.mods.items()) if lm.meta["commands"])
        return HELP + (f"\n\n<b>Yuklangan modullar</b>{extra}" if extra else "")

    def _import_mod(self, name: str):
        modname = f"ubmod_{self.uid}_{name}"
        spec = importlib.util.spec_from_file_location(modname, mod_path(self.uid, name))
        m = importlib.util.module_from_spec(spec)
        sys.modules[modname] = m
        old_flag, sys.dont_write_bytecode = sys.dont_write_bytecode, True     # modullar papkasida __pycache__ qolmasin
        try:
            spec.loader.exec_module(m)
        except SystemExit:
            sys.modules.pop(modname, None)
            raise M.ModError("modul chiqishga (exit) urindi")
        except Exception:
            sys.modules.pop(modname, None)
            raise
        finally:
            sys.dont_write_bytecode = old_flag
        return m

    async def _import_mod_auto(self, name: str):
        """Modulni import qiladi; yetishmayotgan kutubxona bo'lsa (eski modul, o'chib ketgan venv, dinamik import) uni o'zi o'rnatib qayta urinadi."""
        tried: set[str] = set()
        while True:
            try:
                return self._import_mod(name)
            except ModuleNotFoundError as ex:
                top = (ex.name or "").split(".")[0]
                if not top or top in tried or len(tried) >= 3 or L.importable(top):
                    raise                                  # kutubxona emas (yoki o'rnatib bo'lmadi) — haqiqiy xato
                tried.add(top)
                pn = L.pip_name(top)
                if not M.REQ_RE.match(pn):
                    raise
                new = await L.install([pn])
                mod_libs_add(self.uid, name, [L.req_name(pn)], new)
                _docs_sync(self.uid)

    async def mod_load(self, name: str) -> None:
        if name in self.mods:
            await self.mod_unload(name)
        meta = mod_meta(self.uid, name)
        if not meta:
            raise M.ModError("modul fayli topilmadi yoki yaroqsiz")
        m = await self._import_mod_auto(name)
        ctx = ModCtx(self, name, meta)
        lm = LoadedMod(name, m, meta, ctx)
        fns = {}
        try:
            for cmd in meta["commands"]:
                fn = getattr(m, f"cmd_{cmd}", None)
                if not inspect.iscoroutinefunction(fn):
                    raise M.ModError(f"cmd_{cmd} async funksiya emas")
                owner = self.mod_cmds.get(cmd)
                if owner and owner[0].name != name:
                    raise M.ModError(f".{cmd} buyrug'i «{owner[0].name}» modulida band")
                fns[cmd] = fn
            if "on_load" in meta["hooks"]:
                await asyncio.wait_for(m.on_load(ctx), M.LOAD_TIMEOUT)
        except BaseException:
            await ctx._cleanup()
            sys.modules.pop(f"ubmod_{self.uid}_{name}", None)
            raise
        for cmd, fn in fns.items():
            self.mod_cmds[cmd] = (lm, fn)
        self.mods[name] = lm
        self.mod_err.pop(name, None)

    async def _mod_load_safe(self, name: str) -> None:
        try:
            await self.mod_load(name)
        except Exception as ex:
            self.mod_err[name] = f"{type(ex).__name__}: {str(ex)[:200]}"
            print(f"modul {name} yuklanmadi: {ex}")
            raise

    async def mod_unload(self, name: str) -> None:
        lm = self.mods.pop(name, None)
        if not lm:
            return
        for c in [c for c, (l, _) in self.mod_cmds.items() if l is lm]:
            self.mod_cmds.pop(c, None)
        if "on_unload" in lm.meta["hooks"]:
            try: await asyncio.wait_for(lm.module.on_unload(lm.ctx), M.HOOK_TIMEOUT)
            except Exception as ex: lm.ctx.log("on_unload xatosi:", ex)
        await lm.ctx._cleanup()
        sys.modules.pop(f"ubmod_{self.uid}_{name}", None)

    async def _mods_load_all(self) -> None:
        for name, ent in sorted(mods_cfg(self.uid).items()):
            if ent.get("enabled", True):
                try: await self._mod_load_safe(name)
                except Exception: pass        # xato mod_err da — userbotning o'zi ishlayveradi
        _docs_sync(self.uid)

    async def _mods_unload_all(self) -> None:
        for name in list(self.mods):
            try: await self.mod_unload(name)
            except Exception: pass
        _docs_sync(self.uid)

    async def mod_enable(self, name: str, on: bool) -> None:
        mods = mods_cfg(self.uid)
        if name not in mods:
            raise M.ModError(f"«{name}» moduli yo'q")
        mods[name]["enabled"] = on
        _mods_write(self.uid, mods)
        try:
            if on and self.client:
                await self._mod_load_safe(name)
            elif not on:
                await self.mod_unload(name)
                self.mod_err.pop(name, None)
        finally:
            _docs_sync(self.uid)

    async def mod_reload(self, name: str) -> None:
        if name not in mods_cfg(self.uid):
            raise M.ModError(f"«{name}» moduli yo'q")
        try:
            if self.client and mods_cfg(self.uid)[name].get("enabled", True):
                await self._mod_load_safe(name)
        finally:
            _docs_sync(self.uid)

    async def mod_delete(self, name: str) -> tuple[list[str], str]:
        """Modulni va UNING o'rnatgan kutubxonalarini o'chiradi. (o'chirilgan kutubxonalar, xato matni) qaytaradi."""
        await self.mod_unload(name)
        self.mod_err.pop(name, None)
        gone, err = await L.uninstall(mod_remove(self.uid, name))
        return gone, err

    async def mod_libs_fix(self, name: str) -> list[str]:
        """Modulning yetishmayotgan kutubxonalarini o'rnatadi (🔁 tugma / .mod libs fix nom), keyin qayta yuklaydi. Yangi o'rnatilganlar ro'yxati."""
        meta = mod_meta(self.uid, name)
        if not meta or name not in mods_cfg(self.uid):
            raise M.ModError(f"«{name}» moduli yo'q")
        pl = L.plan(meta)
        new = await L.install(pl["install"]) if pl["install"] else []
        mod_libs_add(self.uid, name, pl["needs"], new)
        _docs_sync(self.uid)
        if mods_cfg(self.uid)[name].get("enabled", True) and self.client:
            try: await self._mod_load_safe(name)
            except Exception: pass
        return [x["name"] for x in new]

    async def mod_config_set(self, name: str, key: str, raw) -> object:
        """raw=None — standart qiymatga qaytarish. Modulda on_config(ctx, key, value) bo'lsa chaqiriladi."""
        val = mod_set(self.uid, name, key, raw)
        lm = self.mods.get(name)
        if lm and "on_config" in lm.meta["hooks"]:
            try: await asyncio.wait_for(lm.module.on_config(lm.ctx, key, val), M.HOOK_TIMEOUT)
            except Exception as ex: lm.ctx.log("on_config xatosi:", ex)
        return val

    def _mod_lines(self) -> str:
        mods = mods_cfg(self.uid)
        if not mods:
            return "🧩 Modul yo'q. .py faylga reply qilib: .mod add"
        out = []
        for n, ent in sorted(mods.items()):
            meta = mod_meta(self.uid, n) or {}
            ic = "🟢" if n in self.mods else ("🔴" if self.mod_err.get(n) else ("⚪" if not ent.get("enabled", True) else "🟡"))
            out.append(f"{ic} {n} v{ent.get('version', '?')} — {meta.get('description', '?')}")
        return "🧩 Modullar:\n" + "\n".join(out) + "\n\n.mod info|on|off|reload|del nom · .mod add · .config nom"

    def _mod_info(self, name: str) -> str:
        ent, meta = mods_cfg(self.uid).get(name), mod_meta(self.uid, name)
        if ent is None or not meta:
            raise M.ModError(f"«{name}» moduli yo'q")
        st = "yuklangan" if name in self.mods else (f"xato: {self.mod_err[name]}" if self.mod_err.get(name) else
                                                    ("o'chirilgan" if not ent.get("enabled", True) else "kutilmoqda"))
        lines = [f"🧩 {name} v{meta['version']}" + (f" — {meta['author']}" if meta["author"] else ""), meta["description"],
                 f"Holat: {st}", ""]
        lines += [f"{c['usage']} — {c['desc']}" for c in meta["commands"].values()] or ["(buyruq yo'q)"]
        lines += ["", f"Config: .config {name}"] if meta["config"] else []
        libs = L.summary(ent)
        if libs or meta["requirements"]:
            lines += ["", "📚 Kutubxonalar: " + (libs or "—") + " (modul o'chirilsa, ular ham o'chadi)"]
        return "\n".join(lines)

    def _config_text(self, name: str) -> str:
        meta = mod_meta(self.uid, name)
        if not meta or name not in mods_cfg(self.uid):
            raise M.ModError(f"«{name}» moduli yo'q")
        vals = mod_values(self.uid, name, meta)
        if not meta["config"]:
            return f"⚙️ {name}: sozlanadigan o'zgaruvchi yo'q."
        lines = [f"⚙️ {name} v{meta['version']} — {meta['description']}"]
        for k, sp in meta["config"].items():
            lines.append(f"• {k} = {M.fmt(vals[k])}  ({M.describe(sp)})" + (f" — {sp['desc']}" if sp["desc"] else ""))
        return "\n".join(lines) + f"\n\n.config {name} <o'zgaruvchi> <qiymat>  ·  -r — standart"

    async def _config_cmd(self, arg: str) -> str:
        parts = arg.split(None, 2)
        if not parts:
            mods = mods_cfg(self.uid)
            if not mods:
                return "⚙️ Modul yo'q."
            return "⚙️ Config bor modullar:\n" + "\n".join(
                f"• {n} — {len((mod_meta(self.uid, n) or {}).get('config', {}))} ta o'zgaruvchi" for n in sorted(mods)) + "\n\n.config modul"
        name = parts[0].lower()
        if len(parts) == 1:
            return self._config_text(name)
        key = parts[1].lower()
        if len(parts) == 2:
            meta = mod_meta(self.uid, name)
            sp = (meta or {}).get("config", {}).get(key)
            if not sp:
                raise M.ModError(f"«{name}» da «{key}» o'zgaruvchisi yo'q")
            return f"⚙️ {name}.{key} = {M.fmt(mod_values(self.uid, name, meta)[key])}  ({M.describe(sp)})\n{sp['desc']}"
        raw = parts[2].strip()
        val = await self.mod_config_set(name, key, None if raw == "-r" else raw)
        return f"✅ {name}.{key} = {M.fmt(val)}" + ("  (standart)" if raw == "-r" else "")

    async def _mod_cmd(self, e, sub: str, rest: str) -> str:
        name = rest.strip().lower()
        if sub in ("list", "ls"):
            return self._mod_lines()
        if sub == "add":
            r = await e.get_reply_message()
            doc = getattr(r, "document", None) if r else None
            fname = next((a.file_name for a in getattr(doc, "attributes", []) if hasattr(a, "file_name")), "") or ""
            if not doc or not fname.lower().endswith(".py"):
                raise M.ModError(".py faylga reply qiling: .mod add")
            if doc.size > M.MAX_SRC:
                raise M.ModError(f"Fayl {M.MAX_SRC // 1024} KB dan katta")
            raw = await r.download_media(file=bytes)

            async def _prog(reqs):
                await e.edit("⏳ Kutubxonalar o'rnatilmoqda: " + ", ".join(reqs) + " …", parse_mode=None)
            meta, old, lib = await mod_install_full(self.uid, raw, progress=_prog)
            try:
                await self.mod_reload(meta["name"])
                st = "yuklandi" if meta["name"] in self.mods else "saqlandi"
            except Exception as ex:
                st = f"saqlandi, lekin yuklanmadi: {ex}"
            cmds = " ".join(f".{c}" for c in meta["commands"]) or "—"
            libs = f"\n📚 O'rnatildi: {', '.join(lib['installed'])}" if lib["installed"] else ""
            return f"✅ {meta['name']} v{meta['version']} {'yangilandi' if old else 'o‘rnatildi'}, {st}\nBuyruqlar: {cmds}{libs}"
        if sub == "libs":
            parts = name.split()
            if parts and parts[0] == "fix":
                if len(parts) < 2:
                    raise M.ModError(".mod libs fix nom")
                await e.edit("⏳ Kutubxonalar tekshirilmoqda…", parse_mode=None)
                got = await self.mod_libs_fix(parts[1].lower())
                return f"✅ {parts[1].lower()}: " + (f"o'rnatildi: {', '.join(got)}" if got else "hammasi joyida")
            mods = mods_cfg(self.uid)
            rows = [f"• {n}: {L.summary(ent)}" for n, ent in sorted(mods.items()) if L.owned(ent) and (not parts or n == parts[0].lower())]
            return ("📚 Modullar o'rnatgan kutubxonalar (modul o'chirilsa o'zi ham o'chadi):\n" + "\n".join(rows)
                    if rows else "📚 Modullar o'rnatgan kutubxona yo'q.") + "\n\n.mod libs fix nom — yetishmayotganini o'rnatish"
        if not name:
            raise M.ModError("Modul nomini yozing. .mod — ro'yxat")
        if sub == "info":
            return self._mod_info(name)
        if sub in ("on", "off"):
            await self.mod_enable(name, sub == "on")
            return f"✅ {name} {'yoqildi' if sub == 'on' else 'o‘chirildi'}"
        if sub == "reload":
            await self.mod_reload(name)
            return f"♻️ {name} qayta yuklandi"
        if sub in ("del", "rm", "delete"):
            if name not in mods_cfg(self.uid):
                raise M.ModError(f"«{name}» moduli yo'q")
            gone, err = await self.mod_delete(name)
            return (f"🗑 {name} o'chirildi" + (f"\n🧹 Kutubxonalar ham o'chirildi: {', '.join(gone)}" if gone else "")
                    + (f"\n⚠️ Kutubxonani o'chirishda xato: {err}" if err else ""))
        raise M.ModError("Buyruqlar: list, add, info, on, off, reload, del, libs")

    # --- buyruqlar ---
    def _clock_cmd(self, arg: str) -> str:
        d, low = self.cfg(), arg.lower()
        prev = lambda: f"\n👁 Ko'rinish: <b>{render(self.cfg())}</b>"  # noqa: E731
        if low == "fonts":
            return "<b>Soat shriftlari</b> — <code>.clock font №</code>\n" + "\n".join(
                f"{i}. {DIGITS[k][0]}: {digits_in(k, '12:34')}" for i, k in enumerate(DIGIT_KEYS, 1))
        m = re.fullmatch(r"font\s+(\S+)", low)
        if m:
            k = pick(m[1], DIGIT_KEYS)
            if not k:
                return "❌ Bunday shrift yo'q. <code>.clock fonts</code> — ro'yxat."
            self.set_clock(clock_font=k)
            return f"✅ Shrift: <b>{DIGITS[k][0]}</b>" + prev()
        if low.startswith("fmt"):
            a = arg[3:].strip()
            if not a:
                return "<b>Shablonlar</b> — <code>.clock fmt №</code> yoki o'zingiznikini yozing\n" + "\n".join(
                    f"{i}. <code>{p}</code>" for i, p in enumerate(PRESETS, 1)) + "\n<code>{t}</code> vaqt · <code>{e}</code> 🕒 · <code>{d}</code> sana"
            tpl = PRESETS[int(a) - 1] if a.isdigit() and 1 <= int(a) <= len(PRESETS) else a
            if "{t}" not in tpl and "{e}" not in tpl or len(tpl) > 40:
                return "❌ Shablonda <code>{t}</code> bo'lishi va 40 belgidan oshmasligi kerak."
            self.set_clock(clock_tpl=tpl)
            return "✅ Shablon qabul qilindi" + prev()
        m = re.fullmatch(r"where\s+(last|first|bio)", low)
        if m:
            self.set_clock(clock_where=m[1])
            return f"✅ Joyi: <b>{ {'last': 'familiya', 'first': 'ism', 'bio': 'bio'}[m[1]] }</b>" + prev()
        m = re.fullmatch(r"tz\s+(\S+)", arg, re.I)
        if m:
            try:
                ZoneInfo(m[1])
            except Exception:
                return "❌ Zona topilmadi. Masalan: <code>Asia/Tashkent</code>"
            self.set_clock(tz=m[1])
            return f"✅ Zona: <b>{m[1]}</b>" + prev()
        w = {"last": "familiya", "first": "ism", "bio": "bio"}[d.get("clock_where", "last")]
        return (f"🕒 Soat: <b>{'yoqilgan' if self.clock_on else 'o‘chiq'}</b> · joyi: {w} · "
                f"shrift: {DIGITS.get(d.get('clock_font', 'normal'), DIGITS['normal'])[0]}" + prev() +
                "\n<code>.clock on|off|fonts|font №|fmt №|where last|first|bio|tz Zona</code>")

    def _register(self) -> None:
        c = self.client
        out = lambda pat, **kw: events.NewMessage(outgoing=True, pattern=pat, **kw)  # noqa: E731

        @c.on(out(r"^\.help$"))
        async def _help(e):
            await e.edit(self.help_html(), parse_mode="html")

        @c.on(out(r"^\.ping$"))
        async def _ping(e):
            t0 = time.perf_counter()
            await e.edit("🏓 ...")
            await e.edit(f"🏓 Pong! `{(time.perf_counter() - t0) * 1000:.0f} ms`")

        @c.on(out(r"^\.time$"))
        async def _time(e):
            tz = tz_of(self.cfg())
            await e.edit(f"🕒 {now_str('%H:%M:%S', tz)}\n📅 {now_str('%d.%m.%Y', tz)}")

        @c.on(out(r"^\.id$"))
        async def _id(e):
            text = f"💬 Chat ID: `{e.chat_id}`"
            if e.is_reply:
                r = await e.get_reply_message()
                text += f"\n👤 User ID: `{r.sender_id}`"
            await e.edit(text)

        @c.on(out(r"^\.info$"))
        async def _info(e):
            r = await e.get_reply_message()
            u = await (r.get_sender() if r else e.get_sender())
            name = " ".join(x for x in (getattr(u, "first_name", None), getattr(u, "last_name", None)) if x) or getattr(u, "title", "?")
            lines = [f"👤 **{name}**", f"🆔 `{u.id}`"]
            if getattr(u, "username", None):
                lines.append(f"🔗 @{u.username}")
            if getattr(u, "premium", False):
                lines.append("⭐ Premium")
            if getattr(u, "bot", False):
                lines.append("🤖 Bot")
            await e.edit("\n".join(lines))

        @c.on(out(r"^\.stats$"))
        async def _stats(e):
            d = self.cfg()
            rss = psutil.Process().memory_info().rss / 1048576
            await e.edit(f"📊 **Userbot** v{USERBOT_VERSION}\n⏱ Ishlash: {dur(time.time() - self.started)}\n"
                         f"💾 Xotira: {rss:.0f} MB\n🕒 Soat: {'yoqilgan' if self.clock_on else 'o‘chiq'}\n"
                         f"😴 AFK: {self.afk_reason or 'yo‘q'}\n📝 Eslatmalar: {len(d.get('notes') or {})}")

        @c.on(out(r"^\.calc\s+(.+)$"))
        async def _calc(e):
            expr = e.pattern_match.group(1).strip()
            try:
                res = safe_eval(ast.parse(expr, mode="eval"))
                await e.edit(f"🧮 `{expr}` = **{res}**")
            except Exception as ex:
                await e.edit(f"❌ Xato: {ex}")

        @c.on(out(re.compile(r"^\.type\s+(.+)$", re.S)))
        async def _type(e):
            text, shown = e.pattern_match.group(1), ""
            for ch in text[:300]:
                shown += ch
                try: await e.edit(shown + "▌")
                except Exception: pass
                await asyncio.sleep(0.1)
            await e.edit(text[:300])

        @c.on(out(r"^\.del\s+(\d+)$"))
        async def _del(e):
            n = min(int(e.pattern_match.group(1)), 100)
            ids = [e.id]
            async for m in c.iter_messages(e.chat_id, from_user="me", limit=n + 1):
                if m.id != e.id:
                    ids.append(m.id)
            await c.delete_messages(e.chat_id, ids)

        @c.on(out(r"^\.vps$"))
        async def _vps(e):
            vm, du = psutil.virtual_memory(), psutil.disk_usage("/")
            await e.edit(f"🖥 **VPS**\nCPU: {psutil.cpu_percent(interval=0.3):.0f}%\n"
                         f"RAM: {vm.percent:.0f}%\nDisk: {du.percent:.0f}%")

        @c.on(out(r"^\.save$"))
        async def _save(e):
            r = await e.get_reply_message()
            if not r:
                return await e.edit("❌ Saqlash uchun xabarga reply qiling.")
            await c.forward_messages("me", r)
            await e.edit("💾 «Saqlangan xabarlar»ga yuborildi.")

        # ---- shriftlar ----
        @c.on(out(re.compile(r"^\.font(?:\s+(\S+)(?:\s+(.+))?)?$", re.S)))
        async def _font(e):
            name, text = e.pattern_match.group(1), e.pattern_match.group(2)
            if not name:
                lst = "\n".join(f"{i}. {LETTER_NAMES[k]}: {stylize(k, 'Hello 123')}" for i, k in enumerate(LETTER_KEYS, 1))
                return await e.edit("Shriftlar — .font № matn\n\n" + lst, parse_mode=None)
            k = pick(name, LETTER_KEYS)
            if not k:
                return await e.edit("❌ Bunday shrift yo'q. .font — ro'yxat.", parse_mode=None)
            if not text:
                r = await e.get_reply_message()
                text = (r.raw_text if r else "") or ""
            if not text:
                return await e.edit("❌ Matn yozing: .font bold salom", parse_mode=None)
            await e.edit(stylize(k, text), parse_mode=None)

        @c.on(out(r"^\.fonts$"))
        async def _fonts(e):
            lst = "\n".join(f"{i}. {LETTER_NAMES[k]}: {stylize(k, 'Hello 123')}" for i, k in enumerate(LETTER_KEYS, 1))
            await e.edit("Shriftlar — .font № matn\n\n" + lst, parse_mode=None)

        # ---- profil soati ----
        @c.on(out(r"^\.clock(?:\s+(.+))?$"))
        async def _clock(e):
            arg = (e.pattern_match.group(1) or "").strip()
            if arg.lower() == "on":
                await self.clock_on_()
                return await e.edit("🕒 Profil soati yoqildi.\n" + f"Ko'rinish: {render(self.cfg())}", parse_mode=None)
            if arg.lower() == "off":
                await self.clock_off()
                return await e.edit("🕒 Profil soati o'chirildi, asl nom/bio tiklandi.", parse_mode=None)
            await e.edit(self._clock_cmd(arg), parse_mode="html")

        # ---- eslatma (Telegram serverida rejalanadi — bot o'chib qolsa ham keladi) ----
        @c.on(out(re.compile(r"^\.remind\s+(\S+)\s+(.+)$", re.S)))
        async def _remind(e):
            tz = tz_of(self.cfg())
            try:
                when = parse_when(e.pattern_match.group(1), tz)
            except ValueError as ex:
                return await e.edit(f"❌ {ex}", parse_mode=None)
            text = e.pattern_match.group(2).strip()[:1000]
            await c.send_message("me", f"⏰ {text}", schedule=when)
            await e.edit(f"⏰ Eslatma o'rnatildi: {when.strftime('%d.%m %H:%M')} — {text[:100]}", parse_mode=None)

        # ---- qaydlar ----
        @c.on(out(re.compile(r"^\.notes?(?:\s+(.+))?$", re.S)))
        async def _note(e):
            arg = (e.pattern_match.group(1) or "").strip()
            notes = dict(self.cfg().get("notes") or {})
            if not arg:
                return await e.edit("📝 Qaydlar: " + (", ".join(notes) or "yo'q") +
                                    "\n.note add nom matn · .note nom · .note del nom", parse_mode=None)
            m = re.match(r"add\s+([\w.-]{1,32})\s+(.+)$", arg, re.S)
            if m:
                if len(notes) >= 100 and m[1] not in notes:
                    return await e.edit("❌ 100 tadan ko'p qayd bo'lmaydi.", parse_mode=None)
                notes[m[1]] = m[2].strip()[:2000]
                self.cfg_set(notes=notes)
                return await e.edit(f"📝 «{m[1]}» saqlandi.", parse_mode=None)
            m = re.match(r"del\s+([\w.-]{1,32})$", arg)
            if m:
                ok = notes.pop(m[1], None) is not None
                self.cfg_set(notes=notes)
                return await e.edit(f"🗑 «{m[1]}» o'chirildi." if ok else "❌ Bunday qayd yo'q.", parse_mode=None)
            await e.edit(notes.get(arg) or f"❌ «{arg[:32]}» topilmadi.", parse_mode=None)

        # ---- modullar ----
        @c.on(out(re.compile(r"^\.mods?(?:\s+(.+))?$", re.S)))
        async def _mod(e):
            parts = (e.pattern_match.group(1) or "").strip().split(None, 1)
            try:
                text = await self._mod_cmd(e, parts[0].lower() if parts else "list", parts[1] if len(parts) > 1 else "")
            except M.ModError as ex:
                text = f"❌ {ex}"
            except Exception as ex:
                text = f"❌ {type(ex).__name__}: {str(ex)[:200]}"
            await e.edit(text[:4000], parse_mode=None)

        @c.on(out(re.compile(r"^\.config(?:\s+(.+))?$", re.S)))
        async def _config(e):
            try:
                text = await self._config_cmd((e.pattern_match.group(1) or "").strip())
            except M.ModError as ex:
                text = f"❌ {ex}"
            except Exception as ex:
                text = f"❌ {type(ex).__name__}: {str(ex)[:200]}"
            await e.edit(text[:4000], parse_mode=None)

        @c.on(out(r"^\.docs(?:\s+(\S+))?$"))
        async def _docs(e):
            import userbot_docs
            name = (e.pattern_match.group(1) or "").lower()
            try:
                if name:
                    return await e.edit(userbot_docs.module_text(self.uid, name)[:4000], parse_mode=None)
                bio = io.BytesIO(userbot_docs.build(self.uid).encode("utf-8"))
                bio.name = "MODULES.md"
                await c.send_file("me", bio, caption=f"📖 Modul docs · userbot v{USERBOT_VERSION}")
                await e.edit("📖 Docs «Saqlangan xabarlar»ga yuborildi. Bitta modul: .docs nom", parse_mode=None)
            except M.ModError as ex:
                await e.edit(f"❌ {ex}", parse_mode=None)
            except Exception as ex:
                await e.edit(f"❌ {type(ex).__name__}: {str(ex)[:200]}", parse_mode=None)

        @c.on(events.NewMessage(outgoing=True, pattern=re.compile(r"^\.(\w+)(?:\s+(.*))?$", re.S)))
        async def _mod_dispatch(e):          # modul buyruqlari (o'rnatilganlar bilan to'qnashmaydi — o'rnatishda tekshiriladi)
            ent = self.mod_cmds.get(e.pattern_match.group(1).lower())
            if not ent:
                return
            lm, fn = ent
            try:
                await asyncio.wait_for(fn(e, (e.pattern_match.group(2) or "").strip(), lm.ctx), M.CMD_TIMEOUT)
            except asyncio.TimeoutError:
                await e.edit(f"⏱ [{lm.name}] vaqt tugadi", parse_mode=None)
            except Exception as ex:
                lm.ctx.log("buyruq xatosi:", ex)
                try: await e.edit(f"❌ [{lm.name}] {type(ex).__name__}: {str(ex)[:200]}", parse_mode=None)
                except Exception: pass

        @c.on(events.NewMessage(incoming=True))
        async def _mod_incoming(e):
            for lm in list(self.mods.values()):
                if lm.on_message and "on_message" in lm.meta["hooks"]:
                    try: await asyncio.wait_for(lm.on_message(e, lm.ctx), M.MSG_TIMEOUT)
                    except Exception as ex: lm.ctx.log("on_message xatosi:", ex)

        # ---- AFK ----
        @c.on(out(r"^\.afk(?:\s+(.+))?$"))
        async def _afk(e):
            self.afk_reason = e.pattern_match.group(1) or "Band"
            self.afk_since = time.time()
            self.afk_notified.clear()
            self.afk_chat_ts.clear()
            self._afk_save()
            await e.edit(f"😴 AFK yoqildi: {self.afk_reason}")

        @c.on(out(r"^\.unafk$"))
        async def _unafk(e):
            self.afk_reason = None
            self.afk_notified.clear()
            self._afk_save()
            await e.edit("✅ AFK o'chirildi.")

        @c.on(events.NewMessage(incoming=True, func=lambda e: e.is_private or bool(getattr(e.message, "mentioned", False))))
        async def _afk_reply(e):
            if not self.afk_reason:
                return
            if e.is_private:
                if e.sender_id in self.afk_notified:
                    return
            elif time.time() - self.afk_chat_ts.get(e.chat_id, 0) < 1800:    # guruhda 30 daqiqada bir marta
                return
            s = await e.get_sender()
            if not s or getattr(s, "bot", False):
                return
            if e.is_private:
                self.afk_notified.add(e.sender_id)
            else:
                self.afk_chat_ts[e.chat_id] = time.time()
            self._afk_save()
            await e.reply(f"😴 Hozir band: {self.afk_reason}\n⏱ {dur(time.time() - self.afk_since)}dan beri yo'q.")


# ───────── ro'yxat ─────────
BOTS: dict[int, UserBot] = {}
on_event = None         # async (uid, matn) — bot.py o'rnatadi (qayta ishga tushdi / ulana olmayapti xabarlari)
STOPPING = False


async def _purge_libs(uid: int) -> None:
    """Userbot butunlay o'chirilganda — uning barcha modullari o'rnatgan kutubxonalar ham olib tashlanadi."""
    try:
        mods = mods_cfg(uid)
        rm: list[str] = []
        for n in list(mods):
            rm += L.release(mods, n)
        if rm:
            await L.uninstall(rm)
    except Exception as ex:
        print("kutubxonalarni tozalab bo'lmadi:", ex)


def get(uid: int) -> UserBot:
    if uid not in BOTS:
        BOTS[uid] = UserBot(uid)
    return BOTS[uid]


async def _emit(uid: int, text: str) -> None:
    if on_event:
        try: await on_event(uid, text)
        except Exception: pass


async def _tick(uid: int, resumed: set[int]) -> None:
    d = load(uid)
    if STOPPING or not wants_run(d):
        return
    bot = get(uid)
    if bot.lock.locked():
        return
    now = time.time()
    if bot.client is None:
        if now < bot.next_try:
            return
        try:
            await bot.start(persist=False)
        except SessionDead as e:
            bot.cfg_set(enabled=False)
            await _emit(uid, f"❌ Userbot sessiyasi bekor qilingan: {e}\n🤖 Userbot → 📥 Qayta o'rnatish.")
            return
        except Exception as e:
            bot.fails += 1
            bot.error = str(e)[:200]
            bot.next_try = now + min(300, 15 * 2 ** min(bot.fails, 5))
            if bot.fails == 3 and not bot.alerted:
                bot.alerted = True
                await _emit(uid, f"⚠️ Userbot ulana olmayapti ({bot.error}). Bot o'zi qayta urinishda davom etadi.")
            return
        bot.fails, bot.alerted = 0, False
        if uid not in resumed:
            resumed.add(uid)
            d = load(uid) or {}
            extra = (" · 🕒 soat" if d.get("clock") else "") + (" · 😴 AFK" if d.get("afk") else "")
            await _emit(uid, f"🤖 Userbot avtomatik davom ettirildi{extra}")
    elif not bot.client.is_connected():
        if not bot.disc_since:
            bot.disc_since = now
        elif now - bot.disc_since > 90:         # 90 soniya uzilib qolsa — toza qayta ulanish
            async with bot.lock:
                await bot._teardown(restore=False)
    else:
        bot.disc_since = 0.0
        if now - bot.last_save > 600:
            bot.last_save = now
            bot._save_session()


async def supervise() -> None:
    """Fon vazifa: sessiyasi bor va foydalanuvchi to'xtatmagan har bir userbotni ko'taradi va tirik ushlaydi.
    Restart / ZIP yangilash / server reboot'dan keyin userbotlar to'xtagan joyidan o'zi davom etadi."""
    resumed: set[int] = set()
    while not STOPPING:
        for uid in all_uids():
            try:
                await _tick(uid, resumed)
            except Exception as e:
                print(f"userbot {uid} supervisor: {e}")
        await asyncio.sleep(15)


async def autostart(uids=None) -> None:     # eski nom (moslik uchun)
    await supervise()


async def shutdown() -> None:
    """Bot o'chayotganda: bayroqlarga TEGMAYDI (yangi jarayon davom ettiradi), faqat toza uzadi."""
    global STOPPING
    STOPPING = True
    for ub in list(BOTS.values()):
        try: await asyncio.wait_for(ub.suspend(), 10)
        except Exception: pass
