"""Modul docs generatori — hujjat KODDAN YASALADI, shuning uchun u kod bilan hech qachon farq qilmaydi.

Manbalar (o'zgarsa docs ham o'zgaradi):
  userbot_mods   — chegaralar, vaqt limitlari, RESERVED, HOOKS/HOOK_DOC, RISKY, nom qoidalari
  userbot_core   — HELP (o'rnatilgan buyruqlar), ModCtx (ctx API: docstring + ATTRS), o'rnatilgan buyruq patternlari
  modules_example/*.py — namuna modullar (yangi fayl qo'shilsa docsga o'zi kiradi)
  USERBOT_DIR/modules/<uid>/*.py + holat — o'rnatilgan modullar (nom, tavsif, buyruqlar, config o'zgaruvchilari va joriy qiymatlar)

Fayllar:
  docs/MODULES.md                      — loyiha ichida: faqat qo'llanma (bot ishga tushganda yangilanadi)
  USERBOT_DIR/docs/<uid>/MODULES.md    — shaxsiy: qo'llanma + SIZNING modullaringiz (har o'zgarishda yangilanadi)

Qo'lda:  python userbot_docs.py          (docs/MODULES.md ni yangilaydi)
         python userbot_docs.py --check  (eskirgan bo'lsa 1 qaytaradi — CI/pre-commit uchun)
"""
import hashlib, html, inspect, os, re, sys
from pathlib import Path

import userbot_mods as M

ROOT = Path(__file__).resolve().parent
PROJECT_DOC = ROOT / "docs" / "MODULES.md"
EXAMPLES = ROOT / "modules_example"
_STAMP = re.compile(r"<!-- sha:[0-9a-f]+ -->\n?")


def _core():
    import userbot_core            # kech import — userbot_core ham userbot_docs ni import qiladi
    return userbot_core


def _version() -> str:
    try:
        from version import VERSION
        return VERSION
    except Exception:
        return "?"


# ───────── yordamchilar ─────────
def _md_cell(x) -> str:
    return str(x).replace("|", "\\|").replace("\n", " ")


def _table(head: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(_md_cell(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def _html_to_md(h: str) -> str:
    h = re.sub(r"</?b>", "**", h)
    h = re.sub(r"</?code>", "`", h)
    h = re.sub(r"<[^>]+>", "", h)
    return html.unescape(h)


def builtin_commands() -> set[str]:
    """userbot_core ichidagi haqiqiy buyruq patternlaridan (`out(r"^\\.nom...`) o'rnatilgan buyruq nomlarini oladi."""
    src = Path(_core().__file__).read_text(encoding="utf-8")
    found = set()
    for m in re.finditer(r'out\(\s*(?:re\.compile\(\s*)?r"\^\\\.(\w+)(\?)?', src):
        found.add(m.group(1))
        if m.group(2):
            found.add(m.group(1)[:-1])
    return found


def _kind(spec: dict) -> str:
    return M.describe(spec)


# ───────── qo'llanma (statik qism — koddan) ─────────
def _ctx_api() -> str:
    U = _core()
    rows = [[f"`ctx.{k}`", "atribut", d] for k, d in U.ModCtx.ATTRS.items()]
    for name, obj in inspect.getmembers(U.ModCtx):
        if name.startswith("_") or name == "ATTRS":
            continue
        doc = " ".join((inspect.getdoc(obj) or "(tavsif yo'q)").split()).replace("DATA_MAX", f"{M.DATA_MAX // 1024} KB")
        if isinstance(obj, property):
            rows.append([f"`ctx.{name}`", "xossa", doc])
        elif callable(obj):
            try: sig = str(inspect.signature(obj)).replace("(self, ", "(").replace("(self)", "()").replace("_asyncio.Task", "asyncio.Task")
            except (TypeError, ValueError): sig = "()"
            kind = "async metod" if inspect.iscoroutinefunction(obj) else "metod"
            rows.append([f"`ctx.{name}{sig}`", kind, doc])
    return _table(["Nomi", "Turi", "Tavsif"], rows)


def _example_section() -> str:
    files = sorted(EXAMPLES.glob("*.py")) if EXAMPLES.is_dir() else []
    if not files:
        return "_(modules_example/ papkasida namuna yo'q)_"
    out = []
    for f in files:
        src = f.read_text(encoding="utf-8")
        try:
            meta = M.parse_meta(src)
            head = f"### `{f.name}` — {meta['name']} v{meta['version']}: {meta['description']}"
            sub = (f"Buyruqlar: {' '.join('`.' + c + '`' for c in meta['commands']) or '—'} · "
                   f"config: {', '.join('`' + k + '`' for k in meta['config']) or '—'} · hooklar: {', '.join(meta['hooks']) or '—'}")
        except M.ModError as ex:
            head, sub = f"### `{f.name}`", f"⚠️ Namuna yaroqsiz: {ex}"
        out.append(f"{head}\n\n{sub}\n\n```python\n{src.rstrip()}\n```")
    return "\n\n".join(out)


def build_guide() -> str:
    U = _core()
    help_md = re.sub(r"\n{3,}", "\n\n", _html_to_md(U.HELP).replace("\n", "\n\n"))
    builtins, reserved = builtin_commands(), set(M.RESERVED)
    drift = ""
    if builtins - reserved:
        drift = ("\n\n> ⚠️ **Diqqat (dasturchiga):** quyidagi o'rnatilgan buyruqlar `userbot_mods.RESERVED` da yo'q: "
                 + ", ".join(f"`.{c}`" for c in sorted(builtins - reserved)) + " — modul ularni egallab olishi mumkin.")
    hooks_ok = set(M.HOOKS) == set(M.HOOK_DOC)
    hook_rows = [[f"`{M.HOOK_DOC[h][0]}`" if h in M.HOOK_DOC else f"`{h}`", M.HOOK_DOC.get(h, ("", "(tavsif yo'q)"))[1]] for h in M.HOOKS]
    meta_req = {"NAME": ("majburiy", f"`str` — `{M.NAME_RE.pattern}` (a-z, 0-9, _; harf bilan boshlanadi; 2..24 belgi). Fayl nomi emas, shu nom ishlatiladi."),
                "DESCRIPTION": ("majburiy", "`str` — modul tavsifi (≤300 belgi ko'rsatiladi)."),
                "VERSION": ("ixtiyoriy", "`str` — standart `\"1.0\"` (≤16 belgi). Qayta yuklaganda eski config qiymatlari saqlanadi."),
                "AUTHOR": ("ixtiyoriy", "`str` — muallif (≤64 belgi)."),
                "CONFIG": ("ixtiyoriy", f"`dict` — `.config` va bot tugmalari bilan boshqariladigan o'zgaruvchilar (ko'pi bilan {M.MAX_VARS} ta)."),
                "COMMANDS": ("ixtiyoriy", f"`dict` — modul buyruqlari (ko'pi bilan {M.MAX_CMDS} ta). Har biri uchun `async def cmd_<nom>(e, args, ctx)` shart."),
                "REQUIREMENTS": ("ixtiyoriy", f"`list[str]` — pip kutubxonalari, masalan `[\"pillow\", \"pytz>=2023\"]` (ko'pi bilan {M.MAX_REQS} ta). O'rnatishda **avtomatik o'rnatiladi**, modul o'chirilsa **o'zi ham o'chadi** (bo'lim 9).")}
    meta_rows = [[f"`{k}`", *meta_req.get(k, ("?", "(tavsif yo'q)"))] for k in sorted(M.META_KEYS, key=lambda k: list(meta_req).index(k) if k in meta_req else 99)]
    return f"""# 🧩 Userbot modullari — yozish qo'llanmasi

> Bu fayl **avtomatik yaratiladi** (`userbot_docs.py`) va koddagi o'zgarishlar bilan birga yangilanadi — qo'lda tahrirlamang.
> Loyiha `v{_version()}` · userbot `v{U.USERBOT_VERSION}`

## 1. Modul nima?

Oddiy `.py` fayl. Botga yuboriladi (🤖 Userbot → 🧩 Modullar → 📥 Modul qo'shish) yoki chatda faylga reply qilib `.mod add` yoziladi.
Fayl **ishga tushirilmasdan** `ast` bilan tekshiriladi (nom, tavsif, buyruqlar, config, importlar); siz tasdiqlagach o'rnatiladi.

⚠️ Modul bot jarayonida **to'liq huquq** bilan ishlaydi. Xavfli importlar ({', '.join(f'`{r}`' for r in sorted(M.RISKY))}) o'rnatishdan oldin alohida ogohlantiriladi. Faqat ishonchli kodni o'rnating.

## 2. Metadata (fayl tepasida, oddiy literal sifatida)

{_table(["O'zgaruvchi", "Holat", "Tavsif"], meta_rows)}

Metadata **faqat literal** (matn/son/dict/list/tuple) bo'lishi shart — kod ishga tushmasdan o'qiladi, shuning uchun `NAME = get_name()` kabi yozib bo'lmaydi.
Maksimal fayl hajmi: **{M.MAX_SRC // 1024} KB**, kodlash: **UTF-8**.

## 3. CONFIG — `.config` orqali boshqariladigan o'zgaruvchilar

Kalit qoidasi: `{M.KEY_RE.pattern}`. Tur `default` qiymatdan aniqlanadi: `bool`, `int`, `float`, `str` (o'zgaruvchi qiymati `str` ≤ {M.STR_MAX} belgi).

```python
CONFIG = {{
    "greeting": {{"default": "Salom", "desc": "Salom matni"}},                    # to'liq shakl
    "repeat":   {{"default": 1, "desc": "Necha marta", "min": 1, "max": 5}},      # int, chegara bilan
    "mode":     {{"default": "a", "desc": "Rejim", "choices": ["a", "b"]}},       # variantlardan biri
    "loud":     (False, "Qisqa shakl: (default, tavsif)"),                        # bool
    "limit":    10,                                                              # eng qisqa shakl
}}
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

`bool` uchun qabul qilinadi: `{', '.join(sorted(M.TRUE))}` / `{', '.join(sorted(M.FALSE))}`.
Noto'g'ri qiymat (tur, chegara, variant) rad etiladi va eski qiymat saqlanadi. Config va `ctx.data` restart/ZIP yangilanishdan keyin ham saqlanadi.

## 4. COMMANDS — modul buyruqlari

```python
COMMANDS = {{"hello": {{"desc": "Salom yozadi", "usage": ".hello [ism]"}}, "roll": "Zar tashlaydi"}}

async def cmd_hello(e, args, ctx):      # e — Telethon hodisasi, args — buyruqdan keyingi matn
    await e.edit(f"{{ctx.cfg['greeting']}}, {{args}}!", parse_mode=None)
```

- Har bir `COMMANDS` kaliti uchun **`async def cmd_<nom>(e, args, ctx)`** bo'lishi shart (aks holda o'rnatishda rad etiladi).
- Buyruq faqat **o'zingiz yozganingizda** ishlaydi (istalgan chatda), nuqta bilan boshlanadi.
- Buyruq {M.CMD_TIMEOUT} soniyadan oshsa to'xtatiladi; xato userbotni yiqitmaydi — chatda `❌ [modul] ...` ko'rinadi.
- Ikki modul bitta buyruqni bo'lisha olmaydi; o'rnatilgan buyruq nomlarini ishlatib bo'lmaydi (bo'lim 7).

## 5. Hooklar (ixtiyoriy, hammasi `async def`)

{_table(["Imzo", "Qachon"], hook_rows)}

Vaqt limitlari: `on_load` {M.LOAD_TIMEOUT}s · `on_message` {M.MSG_TIMEOUT}s · `on_unload`/`on_config` {M.HOOK_TIMEOUT}s.{'' if hooks_ok else chr(10) + chr(10) + '> ⚠️ **Dasturchiga:** `userbot_mods.HOOKS` va `HOOK_DOC` mos emas.'}

## 6. `ctx` — modulga beriladigan kontekst

{_ctx_api()}

`ctx.data` hajmi ko'pi bilan **{M.DATA_MAX // 1024} KB**. Modul o'chirilsa/qayta yuklansa `ctx.on` handlerlari va `ctx.spawn` vazifalari avtomatik tozalanadi.

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
    await e.edit(f'{{ctx.emoji(5368324170671202286, "⚡️")}} Ping: <b>{{ms}}</b> ms', parse_mode=ctx.html)
```

## 7. Band buyruq nomlari

Quyidagilarni modul ishlata olmaydi: {', '.join(f'`.{c}`' for c in sorted(reserved))}.{drift}

## 8. Userbot buyruqlari (hozirgi `.help`)

{help_md}

## 9. Boshqaruv

| Buyruq | Vazifa |
|---|---|
| `.mod` | modullar ro'yxati (🟢 yuklangan · 🟡 kutilmoqda · ⚪ o'chiq · 🔴 xato) |
| `.mod add` | `.py` faylga reply — o'rnatish/yangilash |
| `.mod info\\|on\\|off\\|reload\\|del nom` | ma'lumot / yoqish / o'chirish / qayta yuklash / butunlay olib tashlash |
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

{_example_section()}
"""


# ───────── o'rnatilgan modullar (foydalanuvchiga xos) ─────────
def _status(uid: int, name: str, ent: dict) -> str:
    bot = _core().BOTS.get(uid)
    if bot and name in bot.mods: return "🟢 yuklangan"
    if bot and bot.mod_err.get(name): return "🔴 xato: " + bot.mod_err[name]
    return "⚪ o'chirilgan" if not ent.get("enabled", True) else "🟡 kutilmoqda (userbot ishga tushganda yuklanadi)"


def module_section(uid: int, name: str) -> str:
    U = _core()
    ent, meta = U.mods_cfg(uid).get(name), U.mod_meta(uid, name)
    if ent is None:
        raise M.ModError(f"«{name}» moduli yo'q")
    if not meta:
        return f"### ⚠️ {name}\n\nFayl topilmadi yoki yaroqsiz (`.mod del {name}` bilan olib tashlang).\n"
    vals = U.mod_values(uid, name, meta)
    lines = [f"### {name} `v{meta['version']}`" + (f" — {meta['author']}" if meta["author"] else ""), "", meta["description"], "",
             f"- **Holat:** {_status(uid, name, ent)}",
             f"- **Fayl:** `{U.mod_path(uid, name)}`",
             f"- **Hooklar:** {', '.join('`' + h + '`' for h in meta['hooks']) or '—'}"]
    if ent.get("pip"):
        lines.append("- **Kutubxonalar (modul o'chirilsa o'zi ham o'chadi):** " + (", ".join(f"`{x['name']}`" for x in ent["pip"].get("installed", [])) or "—"))
    if meta["imports"]:
        lines.append("- **Importlar:** " + ", ".join(("⚠️ " if i in meta["risky"] else "") + f"`{i}`" for i in meta["imports"]))
    lines += ["", "**Buyruqlar**", ""]
    lines += [_table(["Buyruq", "Ishlatilishi", "Tavsif"], [[f"`.{c}`", f"`{d['usage']}`", d["desc"]] for c, d in meta["commands"].items()])] if meta["commands"] else ["—"]
    lines += ["", f"**Config** (`.config {name} <o'zgaruvchi> <qiymat>`)", ""]
    if meta["config"]:
        lines.append(_table(["O'zgaruvchi", "Tur / chegara", "Standart", "Joriy qiymat", "Tavsif"],
                            [[f"`{k}`", _kind(sp), M.fmt(sp["default"]), "**" + M.fmt(vals[k]) + "**" + ("" if vals[k] == sp["default"] else " ✏️"), sp["desc"]]
                             for k, sp in meta["config"].items()]))
    else:
        lines.append("—")
    return "\n".join(lines) + "\n"


def installed_section(uid: int) -> str:
    U = _core()
    mods = U.mods_cfg(uid)
    head = "## 12. Sizning modullaringiz\n\n"
    if not mods:
        return head + "_Hozircha modul o'rnatilmagan. `.py` faylga reply qilib `.mod add` yozing yoki botdan yuboring._\n"
    summary = _table(["Modul", "Versiya", "Holat", "Buyruqlar", "Config"],
                     [[n, ent.get("version", "?"), _status(uid, n, ent),
                       " ".join(f".{c}" for c in (U.mod_meta(uid, n) or {}).get("commands", {})) or "—",
                       len((U.mod_meta(uid, n) or {}).get("config", {}))] for n, ent in sorted(mods.items())])
    return head + summary + "\n\n" + "\n".join(module_section(uid, n) for n in sorted(mods))


def module_text(uid: int, name: str) -> str:
    """`.docs nom` — chatga sig'adigan oddiy matn: nom, tavsif, buyruqlar, config o'zgaruvchilari va qiymatlari."""
    U = _core()
    ent, meta = U.mods_cfg(uid).get(name), U.mod_meta(uid, name)
    if ent is None or not meta:
        raise M.ModError(f"«{name}» moduli yo'q. .mod — ro'yxat")
    vals = U.mod_values(uid, name, meta)
    out = [f"🧩 {name} v{meta['version']}" + (f" — {meta['author']}" if meta["author"] else ""), meta["description"],
           f"Holat: {_status(uid, name, ent)}", "", "Buyruqlar:"]
    out += [f"  {d['usage']} — {d['desc']}" for d in meta["commands"].values()] or ["  —"]
    out += ["", f"Config (.config {name} <kalit> <qiymat>):"]
    out += [f"  {k} = {M.fmt(vals[k])}  [{_kind(sp)}; standart {M.fmt(sp['default'])}]" + (f" — {sp['desc']}" if sp["desc"] else "")
            for k, sp in meta["config"].items()] or ["  —"]
    return "\n".join(out)


def build_for_ai(uid: int) -> str:
    """AI ga beriladigan qo'llanma: to'liq guide + o'rnatilgan modullar va ularning BAND buyruqlari (to'qnashmaslik uchun)."""
    U = _core()
    taken = []
    for n in sorted(U.mods_cfg(uid)):
        meta = U.mod_meta(uid, n) or {}
        taken.append(f"- {n}: " + (" ".join(f".{c}" for c in meta.get("commands", {})) or "(buyruq yo'q)"))
    return (build_guide() + "\n\n## O'rnatilgan modullar (ularning buyruq nomlarini ISHLATMANG)\n\n" +
            ("\n".join(taken) or "(hozircha yo'q)") + "\n")


def build(uid: int | None = None) -> str:
    """Qo'llanma (+ uid berilsa, shu foydalanuvchining modullari)."""
    body = build_guide()
    if uid is not None:
        body += "\n" + installed_section(uid)
    return body


# ───────── fayllarga yozish ─────────
def _write_if_changed(path: Path, text: str, mode: int | None = None) -> bool:
    digest = hashlib.sha256(_STAMP.sub("", text).encode()).hexdigest()[:12]
    text = text.rstrip("\n") + f"\n\n<!-- sha:{digest} -->\n"
    try:
        if path.read_text(encoding="utf-8") == text:
            return False
    except OSError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    if mode:
        try: os.chmod(tmp, mode)
        except OSError: pass
    os.replace(tmp, path)
    return True


def user_doc_path(uid: int) -> Path:
    return _core().DIR / "docs" / str(int(uid)) / "MODULES.md"


def sync(uid: int) -> bool:
    """Foydalanuvchi docs faylini yangilaydi (o'zgargan bo'lsagina yozadi)."""
    return _write_if_changed(user_doc_path(uid), build(uid), 0o600)


def sync_project() -> bool:
    """docs/MODULES.md (faqat qo'llanma). Loyiha papkasi yozilmasa — jim o'tadi."""
    try:
        return _write_if_changed(PROJECT_DOC, build_guide())
    except OSError as ex:
        print("docs/MODULES.md yozilmadi:", ex)
        return False


def sync_all() -> None:
    """Bot ishga tushganda: loyiha docs + barcha userbotlar docs (kod yoki modullar ZIP bilan o'zgargan bo'lishi mumkin)."""
    sync_project()
    U = _core()
    for uid in U.all_uids():
        try: sync(uid)
        except Exception as ex: print(f"docs ({uid}) yangilanmadi:", ex)


if __name__ == "__main__":
    if "--check" in sys.argv:
        cur = PROJECT_DOC.read_text(encoding="utf-8") if PROJECT_DOC.exists() else ""
        new = build_guide()
        ok = _STAMP.sub("", cur).strip() == new.strip()
        print("docs yangi" if ok else "docs ESKIRGAN — `python userbot_docs.py` ni ishga tushiring")
        sys.exit(0 if ok else 1)
    print("yangilandi" if sync_project() else "o'zgarish yo'q", "→", PROJECT_DOC)
