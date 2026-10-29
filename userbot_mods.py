"""Userbot modullari: .py faylni KODNI ISHGA TUSHIRMASDAN tahlil qilish (ast) va config qiymatlarini tekshirish.

Modul fayli (oddiy .py):

    NAME = "example"                    # majburiy: a-z, 0-9, _ (2..24 belgi)
    DESCRIPTION = "Modul tavsifi"       # majburiy
    VERSION = "1.0"                     # ixtiyoriy
    AUTHOR = "Ism"                      # ixtiyoriy
    REQUIREMENTS = ["qrcode[pil]"]      # ixtiyoriy: pip kutubxonalar (o'rnatishda avtomatik o'rnatiladi, modul o'chsa o'zi ham o'chadi)
    CONFIG = {                          # ixtiyoriy: .config orqali boshqariladi
        "greeting": {"default": "Salom", "desc": "Salom matni"},                  # tur defaultdan aniqlanadi
        "repeat":   {"default": 1, "desc": "Necha marta", "min": 1, "max": 5},
        "mode":     {"default": "a", "desc": "Rejim", "choices": ["a", "b"]},
        "loud":     (False, "Qisqa shakl: (default, tavsif)"),
        "limit":    10,                                                           # eng qisqa shakl
    }
    COMMANDS = {"hello": "Salom yozadi", "roll": {"desc": "Zar", "usage": ".roll [n]"}}

    async def cmd_hello(e, args, ctx): ...      # har bir buyruq uchun cmd_<nom>
    async def on_load(ctx): ...                 # ixtiyoriy hooklar: on_load, on_unload, on_message(e, ctx), on_config(ctx, key, value)

Metadata (NAME, CONFIG, COMMANDS ...) faqat oddiy literal bo'lishi shart — shuning uchun kod ishga tushmasdan o'qib chiqiladi.
"""
import ast, math, re

# Chegaralar va vaqt limitlari — userbot_core va docs shu yerdan oladi (docs kod bilan hech qachon farq qilmaydi)
MAX_SRC = 256 * 1024         # modul fayli (bayt)
MAX_VARS = 30                # CONFIG dagi o'zgaruvchilar soni
MAX_CMDS = 30                # COMMANDS dagi buyruqlar soni
STR_MAX = 500                # str qiymat uzunligi
DATA_MAX = 64 * 1024         # ctx.data hajmi (bayt)
CMD_TIMEOUT = 120            # buyruq (cmd_*) vaqti, soniya
LOAD_TIMEOUT = 30            # on_load
MSG_TIMEOUT = 30             # on_message
HOOK_TIMEOUT = 10            # on_unload, on_config
# userbot_core dagi o'rnatilgan buyruqlar bilan bir xil bo'lishi kerak
RESERVED = {"help", "ping", "time", "id", "info", "stats", "vps", "calc", "type", "del", "save", "font", "fonts", "clock",
            "remind", "note", "notes", "afk", "unafk", "mod", "mods", "config", "docs"}
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,23}$")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,23}$")
META_KEYS = {"NAME", "DESCRIPTION", "VERSION", "AUTHOR", "CONFIG", "COMMANDS", "REQUIREMENTS"}
MAX_REQS = 10                # REQUIREMENTS dagi kutubxonalar soni (importlardan avtomatik topilganlar ham shu chegarada)
# pip talabi: nom[extras] va ixtiyoriy versiya sharti. URL, fayl yo'li va pip parametrlari (-r, --index-url ...) QABUL QILINMAYDI.
REQ_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}(\[[A-Za-z0-9._,-]{1,40}\])?\s*"
                    r"((==|>=|<=|~=|!=|<|>)\s*[A-Za-z0-9.*+!_-]{1,32}(\s*,\s*(==|>=|<=|~=|!=|<|>)\s*[A-Za-z0-9.*+!_-]{1,32})*)?$")
HOOKS = ("on_load", "on_unload", "on_message", "on_config")
HOOK_DOC = {       # (imzo, tavsif) — docs shundan olinadi; yangi hook qo'shsangiz bu yerga ham yozing (docs.py tekshiradi)
    "on_load": ("async def on_load(ctx)", "Modul yuklanganda (userbot ishga tushganda, `.mod on/reload/add` dan keyin). Xato bersa modul yuklanmaydi (🔴)."),
    "on_unload": ("async def on_unload(ctx)", "Modul o'chirilganda/qayta yuklanganda. Resurslarni shu yerda yoping. `ctx.on` handlerlari va `ctx.spawn` vazifalari o'zi tozalanadi."),
    "on_message": ("async def on_message(e, ctx)", "Har bir KIRUVCHI xabar uchun (`e` — Telethon NewMessage hodisasi). Xatosi boshqa modullarga tegmaydi."),
    "on_config": ("async def on_config(ctx, key, value)", "`.config` yoki bot tugmasi bilan o'zgaruvchi o'zgarganda (`value` — allaqachon turga o'tkazilgan)."),
}
RISKY = {"os", "subprocess", "socket", "shutil", "ctypes", "importlib", "sys", "pty", "multiprocessing", "signal",
         "builtins", "marshal", "pickle", "asyncio.subprocess"}
TYPES = {bool: "bool", int: "int", float: "float", str: "str"}
TRUE = {"1", "true", "on", "yes", "ha", "ok", "+"}
FALSE = {"0", "false", "off", "no", "yo'q", "yoq", "-"}


class ModError(ValueError):
    pass


def coerce(spec: dict, raw):
    """Matn (yoki tayyor qiymat)ni o'zgaruvchi turiga o'tkazadi va chegaralarni tekshiradi."""
    t = spec["type"]
    if t == "bool":
        if isinstance(raw, bool):
            v = raw
        else:
            s = str(raw).strip().lower()
            if s in TRUE: v = True
            elif s in FALSE: v = False
            else: raise ModError("on/off (yoki ha/yo'q) yozing")
    elif t in ("int", "float"):
        try:
            v = int(str(raw).strip()) if t == "int" else float(str(raw).strip().replace(",", "."))
        except ValueError:
            raise ModError("son kerak" if t == "float" else "butun son kerak")
        if isinstance(v, float) and not math.isfinite(v):
            raise ModError("son kerak")
        if spec.get("min") is not None and v < spec["min"]: raise ModError(f"eng kami {spec['min']}")
        if spec.get("max") is not None and v > spec["max"]: raise ModError(f"eng ko'pi {spec['max']}")
    else:
        v = str(raw)
        if len(v) > STR_MAX: raise ModError(f"{STR_MAX} belgidan oshmasin")
    if spec.get("choices") and v not in spec["choices"]:
        raise ModError("variantlar: " + ", ".join(map(str, spec["choices"])))
    return v


def fmt(v) -> str:
    return ("on" if v else "off") if isinstance(v, bool) else str(v)


def describe(spec: dict) -> str:
    s = spec["type"]
    if spec.get("choices"): s += ": " + "|".join(map(str, spec["choices"]))
    elif spec.get("min") is not None or spec.get("max") is not None:
        s += f" {'' if spec.get('min') is None else spec['min']}..{'' if spec.get('max') is None else spec['max']}"
    return s


def _norm_var(key, v) -> dict:
    if not isinstance(key, str) or not KEY_RE.match(key):
        raise ModError(f"CONFIG kaliti noto'g'ri: {key!r} (a-z, 0-9, _; 1..24 belgi)")
    if isinstance(v, dict):
        d = dict(v)
    elif isinstance(v, tuple) and len(v) == 2 and isinstance(v[1], str):
        d = {"default": v[0], "desc": v[1]}
    else:
        d = {"default": v}
    if "default" not in d:
        raise ModError(f"CONFIG[{key!r}] da default yo'q")
    t = d.get("type") or TYPES.get(type(d["default"]))
    if t not in ("str", "int", "float", "bool"):
        raise ModError(f"CONFIG[{key!r}] turi: str/int/float/bool bo'lishi kerak")
    spec = {"type": t, "desc": str(d.get("desc", ""))[:200], "choices": None, "min": d.get("min"), "max": d.get("max")}
    ch = d.get("choices")
    if ch is not None:
        if not isinstance(ch, (list, tuple)) or not 1 <= len(ch) <= 20: raise ModError(f"CONFIG[{key!r}] choices noto'g'ri")
        spec["choices"] = list(ch)
    for b in ("min", "max"):
        if spec[b] is not None and (isinstance(spec[b], bool) or not isinstance(spec[b], (int, float))):
            raise ModError(f"CONFIG[{key!r}] {b} son bo'lishi kerak")
    try:
        spec["default"] = coerce(spec, d["default"])
    except ModError as e:
        raise ModError(f"CONFIG[{key!r}] default xato: {e}")
    return spec


def parse_meta(src: str) -> dict:
    """Modulni ishga tushirmasdan metadata + xavfsizlik ma'lumotini oladi. Xato bo'lsa ModError."""
    if len(src.encode("utf-8")) > MAX_SRC:
        raise ModError(f"Fayl {MAX_SRC // 1024} KB dan katta")
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        raise ModError(f"Sintaksis xatosi: {e.msg} (qator {e.lineno})")
    raw, afuncs, sfuncs, imports = {}, set(), set(), set()
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id in META_KEYS:
            try:
                raw[n.targets[0].id] = ast.literal_eval(n.value)
            except Exception:
                raise ModError(f"{n.targets[0].id} oddiy literal (matn/son/dict) bo'lishi kerak — kod emas")
        elif isinstance(n, ast.AsyncFunctionDef):
            afuncs.add(n.name)
        elif isinstance(n, ast.FunctionDef):
            sfuncs.add(n.name)
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imports.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            imports.add(n.module)
    name = raw.get("NAME")
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise ModError("NAME majburiy: a-z, 0-9, _ (harf bilan boshlanadi, 2..24 belgi)")
    desc = raw.get("DESCRIPTION")
    if not isinstance(desc, str) or not desc.strip():
        raise ModError("DESCRIPTION majburiy (matn)")
    version, author = str(raw.get("VERSION", "1.0"))[:16], str(raw.get("AUTHOR", ""))[:64]
    cfg_raw = raw.get("CONFIG", {})
    if not isinstance(cfg_raw, dict) or len(cfg_raw) > MAX_VARS:
        raise ModError(f"CONFIG dict bo'lishi kerak (ko'pi bilan {MAX_VARS} ta o'zgaruvchi)")
    config = {k: _norm_var(k, v) for k, v in cfg_raw.items()}
    cmd_raw = raw.get("COMMANDS", {})
    if not isinstance(cmd_raw, dict) or len(cmd_raw) > MAX_CMDS:
        raise ModError(f"COMMANDS dict bo'lishi kerak (ko'pi bilan {MAX_CMDS} ta)")
    commands = {}
    for k, v in cmd_raw.items():
        if not isinstance(k, str) or not KEY_RE.match(k):
            raise ModError(f"Buyruq nomi noto'g'ri: {k!r}")
        if k in RESERVED:
            raise ModError(f".{k} — o'rnatilgan buyruq, boshqa nom tanlang")
        if f"cmd_{k}" in sfuncs:
            raise ModError(f"cmd_{k} async bo'lishi kerak (async def)")
        if f"cmd_{k}" not in afuncs:
            raise ModError(f"COMMANDS da «{k}» bor, lekin async def cmd_{k}(e, args, ctx) yo'q")
        d = v if isinstance(v, dict) else {"desc": v}
        commands[k] = {"desc": str(d.get("desc", ""))[:200], "usage": str(d.get("usage", f".{k}"))[:100]}
    for h in HOOKS:
        if h in sfuncs:
            raise ModError(f"{h} async bo'lishi kerak (async def)")
    req_raw = raw.get("REQUIREMENTS", [])
    if isinstance(req_raw, str):
        req_raw = [req_raw]
    if not isinstance(req_raw, (list, tuple)) or len(req_raw) > MAX_REQS or not all(isinstance(r, str) for r in req_raw):
        raise ModError(f"REQUIREMENTS matnlar ro'yxati bo'lishi kerak (ko'pi bilan {MAX_REQS} ta), masalan [\"qrcode[pil]\", \"pytz>=2023\"]")
    requirements = []
    for r in req_raw:
        r = r.strip()
        if not REQ_RE.match(r):
            raise ModError(f"REQUIREMENTS da noto'g'ri talab: {r[:60]!r} (faqat «nom» yoki «nom>=versiya»; URL/parametr mumkin emas)")
        if r not in requirements:
            requirements.append(r)
    tops = {i.split(".")[0] for i in imports}
    return {"name": name, "description": desc.strip()[:300], "version": version, "author": author, "config": config,
            "commands": commands, "requirements": requirements, "imports": sorted(tops), "risky": sorted(t for t in tops if t in RISKY),
            "hooks": [h for h in HOOKS if h in afuncs]}
