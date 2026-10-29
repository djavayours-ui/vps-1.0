"""Modul kutubxonalarini AVTOMATIK o'rnatish va modul bilan birga o'chirish (pip, botning o'z venv'iga).

Qanday ishlaydi:
• Modul o'rnatilganda: REQUIREMENTS = [...] dagi talablar + kodda import qilingan, lekin o'rnatilmagan kutubxonalar
  (import nomi → pip nomi: PIL → pillow, cv2 → opencv-python-headless ...) pip bilan o'rnatiladi.
• Aynan nima yangi o'rnatilgani (bog'liq kutubxonalar bilan) pip'dan OLDIN/KEYIN solishtirib topiladi va modul yozuviga
  saqlanadi (mods[nom]["pip"] = {"needs": [...], "installed": [{"name", "version"}]}).
• Modul o'chirilganda: faqat O'SHA modul o'rnatgan kutubxonalar o'chiriladi. Boshqa modul ham ishlatayotgan kutubxona
  (va uning bog'liqliklari) o'chirilmaydi — egalik o'sha modulga o'tadi. Bot o'zining kutubxonalari (requirements.txt) hech qachon o'chirilmaydi.
• Bot o'z kutubxonalarini buzmasligi uchun pip'ga «constraints» beriladi (aiogram, telethon... joriy versiyada qoladi).
• Xavfsizlik: talablar userbot_mods.REQ_RE bilan tekshiriladi (URL, fayl yo'li, pip parametrlari yo'q), pip shell'siz ishga tushadi.
Telegram/aiogram'ga bog'liq emas.
"""
import asyncio, importlib, importlib.metadata as md, importlib.util, os, re, sys, tempfile
from pathlib import Path

import userbot_mods as M

PROJECT = Path(__file__).resolve().parent
PIP_TIMEOUT = 900            # bitta pip buyrug'i uchun (soniya) — og'ir kutubxonalar uchun yetarli
UNINSTALL_TIMEOUT = 300
_LOCK = asyncio.Lock()       # bir vaqtda faqat bitta pip (parallel pip muhitni buzadi)

# import nomi → pip nomi (nomlari farq qiladiganlar). Boshqalar uchun import nomi pip nomi deb olinadi.
PIP_MAP = {
    "PIL": "pillow", "cv2": "opencv-python-headless", "bs4": "beautifulsoup4", "yaml": "pyyaml", "sklearn": "scikit-learn",
    "skimage": "scikit-image", "dateutil": "python-dateutil", "Crypto": "pycryptodome", "Cryptodome": "pycryptodomex",
    "serial": "pyserial", "telegram": "python-telegram-bot", "jwt": "pyjwt", "OpenSSL": "pyopenssl", "attr": "attrs",
    "git": "gitpython", "docx": "python-docx", "pptx": "python-pptx", "fitz": "pymupdf", "magic": "python-magic",
    "usb": "pyusb", "zmq": "pyzmq", "nacl": "pynacl", "socks": "pysocks", "psycopg2": "psycopg2-binary",
    "MySQLdb": "mysqlclient", "speech_recognition": "SpeechRecognition", "deep_translator": "deep-translator",
    "yt_dlp": "yt-dlp", "youtube_dl": "youtube-dl", "speedtest": "speedtest-cli", "whois": "python-whois",
    "dns": "dnspython", "barcode": "python-barcode", "sentry_sdk": "sentry-sdk", "dotenv": "python-dotenv",
    "multipart": "python-multipart", "slugify": "python-slugify", "ruamel": "ruamel.yaml", "Xlib": "python-xlib",
    "win32api": "pywin32", "gi": "pygobject", "wx": "wxpython", "tgcrypto": "tgcrypto", "pyaes": "pyaes",
    "google_play_scraper": "google-play-scraper", "fake_useragent": "fake-useragent", "ffmpeg": "ffmpeg-python",
    "flask_cors": "flask-cors", "pyquery": "pyquery", "pkg_resources": "setuptools", "markdown2": "markdown2",
}
_CORE_EXTRA = {"pip", "setuptools", "wheel"}


class LibError(M.ModError):
    pass


# ───────── nomlar / muhit ─────────
def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def req_name(spec: str) -> str:
    m = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", spec.strip())
    return norm(m.group(0)) if m else ""


def installed_map() -> dict[str, str]:
    """{pip nomi (normallashgan): versiya} — hozir muhitda o'rnatilganlar."""
    out = {}
    for d in md.distributions():
        try:
            n = d.metadata["Name"]
        except Exception:
            continue
        if n:
            out[norm(n)] = d.version or "?"
    return out


def _deps_map() -> dict[str, list[str]]:
    out = {}
    for d in md.distributions():
        try:
            n = d.metadata["Name"]
        except Exception:
            continue
        if not n:
            continue
        deps = []
        for r in d.requires or []:
            base, _, marker = r.partition(";")
            if "extra" in marker:                 # ixtiyoriy (extra) bog'liqlik — asosiy emas
                continue
            m = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", base)
            if m:
                deps.append(norm(m.group(1)))
        out[norm(n)] = deps
    return out


def closure(roots, deps: dict[str, list[str]] | None = None) -> set[str]:
    """roots va ularning (rekursiv) bog'liq kutubxonalari."""
    deps = deps if deps is not None else _deps_map()
    seen, stack = set(), [norm(r) for r in roots]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(deps.get(n, []))
    return seen


def core_names() -> set[str]:
    """Bot o'zining kutubxonalari (requirements.txt) + pip/setuptools — ularga TEGILMAYDI."""
    names = set(_CORE_EXTRA)
    try:
        for line in (PROJECT / "requirements.txt").read_text(encoding="utf-8").splitlines():
            n = req_name(line.split("#")[0])
            if n:
                names.add(n)
    except OSError:
        pass
    return names


def importable(top: str) -> bool:
    """Import nomi (yuqori daraja) hozir import qilinadimi (stdlib, loyiha fayli yoki o'rnatilgan kutubxona)."""
    if top == "__future__" or top in sys.stdlib_module_names or top in sys.modules:
        return True
    if (PROJECT / f"{top}.py").exists() or (PROJECT / top).is_dir():
        return True
    try:
        return importlib.util.find_spec(top) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def pip_name(top: str) -> str:
    return PIP_MAP.get(top, top)


def dists_of(top: str) -> list[str]:
    """Import nomi (masalan PIL) qaysi o'rnatilgan pip kutubxona(lar)ga tegishli (pillow). Topilmasa — bo'sh."""
    try:
        return sorted({norm(x) for x in md.packages_distributions().get(top, [])})
    except Exception:
        return []


# ───────── reja ─────────
def plan(meta: dict) -> dict:
    """Modul uchun nima o'rnatilishini ko'rsatadi (hech narsa o'rnatmaydi, tez).
    {"explicit": REQUIREMENTS, "auto": importlardan topilgan, "install": pip'ga beriladigan talablar, "needs": barcha pip nomlari}"""
    explicit = list(meta.get("requirements") or [])
    have = installed_map()
    covered = {req_name(s) for s in explicit}
    install, auto = [], []
    for spec in explicit:
        n = req_name(spec)
        if n and (n not in have or re.search(r"[<>=!~]", spec)):       # versiya sharti bor bo'lsa pip o'zi tekshiradi
            install.append(spec)
    used = set()                                   # modul ishlatayotgan, ALLAQACHON o'rnatilgan kutubxonalar (boshqa modul o'rnatgan bo'lishi mumkin)
    for top in meta.get("imports") or []:
        if importable(top):
            if top not in sys.stdlib_module_names and not (PROJECT / f"{top}.py").exists() and not (PROJECT / top).is_dir():
                used.update(dists_of(top))
            continue
        pn = pip_name(top)
        if norm(pn) in covered or pn in auto:
            continue
        auto.append(pn)
    install += auto
    if len(install) > M.MAX_REQS:
        raise LibError(f"Bir modul uchun ko'pi bilan {M.MAX_REQS} ta kutubxona o'rnatiladi (kerak: {len(install)}). "
                       "REQUIREMENTS ni qisqartiring yoki kutubxonalarni kamaytiring.")
    for s in auto:
        if not M.REQ_RE.match(s):
            raise LibError(f"Import nomidan yaroqli kutubxona nomi chiqmadi: {s!r}")
    # needs: modul tayanadigan hamma kutubxonalar. Boshqa modul o'rnatgan kutubxonaga tayansangiz ham yoziladi —
    # shunda o'sha modul o'chirilganda kutubxona o'chib ketmaydi (egalik sizga o'tadi).
    needs = sorted({req_name(s) for s in explicit + auto if req_name(s)} | (used - core_names()))
    return {"explicit": explicit, "auto": auto, "install": install, "needs": needs}


# ───────── pip ─────────
async def _run(args: list[str], timeout: int) -> tuple[int, str]:
    env = {**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_INPUT": "1", "PYTHONUNBUFFERED": "1"}
    p = await asyncio.create_subprocess_exec(sys.executable, *args, stdout=asyncio.subprocess.PIPE,
                                             stderr=asyncio.subprocess.STDOUT, env=env, start_new_session=True)
    try:
        out, _ = await asyncio.wait_for(p.communicate(), timeout)
    except asyncio.TimeoutError:
        try: p.kill()
        except ProcessLookupError: pass
        return 124, "⏱ pip vaqti tugadi (timeout)"
    except asyncio.CancelledError:
        try: p.kill()
        except ProcessLookupError: pass
        raise
    return p.returncode or 0, out.decode(errors="replace")


async def _pip(args: list[str], timeout: int) -> tuple[int, str]:
    rc, out = await _run(["-m", "pip", *args], timeout)
    if rc != 0 and "No module named pip" in out:                       # venv'da pip yo'q bo'lsa — o'zi o'rnatadi
        rc2, _ = await _run(["-m", "ensurepip", "--upgrade"], 180)
        if rc2 == 0:
            rc, out = await _run(["-m", "pip", *args], timeout)
    return rc, out


def _tail(out: str, n: int = 600) -> str:
    lines = [l for l in out.strip().splitlines() if l.strip()]
    err = [l for l in lines if "ERROR" in l or "error:" in l.lower()]
    text = "\n".join((err or lines)[-6:])
    return text[-n:] or "(pip chiqishi bo'sh)"


def _constraints() -> str:
    """Bot kutubxonalarini joriy versiyada ushlab turadigan fayl (modul talabi ularni yangilab/buzib yubormasin)."""
    have = installed_map()
    core = sorted(n for n in core_names() if n in have and n not in _CORE_EXTRA)
    fd, path = tempfile.mkstemp(prefix="vpsbot-constraints-", suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write("".join(f"{n}=={have[n]}\n" for n in core))
    return path


async def install(reqs: list[str]) -> list[dict]:
    """Talablarni o'rnatadi. Yangi paydo bo'lgan kutubxonalar (bog'liqlari bilan) ro'yxatini qaytaradi: [{"name", "version"}].
    Xatoda — LibError va yarim o'rnatilganlar tozalanadi."""
    reqs = [r.strip() for r in reqs if r.strip()]
    if not reqs:
        return []
    for r in reqs:
        if not M.REQ_RE.match(r):
            raise LibError(f"Noto'g'ri talab: {r[:60]!r}")
    async with _LOCK:
        importlib.invalidate_caches()
        before = installed_map()
        cons = _constraints()
        try:
            rc, out = await _pip(["install", "-c", cons, *reqs], PIP_TIMEOUT)
        finally:
            try: os.unlink(cons)
            except OSError: pass
        importlib.invalidate_caches()
        after = installed_map()
        new = [{"name": n, "version": v} for n, v in sorted(after.items()) if n not in before]
        if rc != 0:
            leftovers = [x["name"] for x in new if x["name"] not in core_names()]
            if leftovers:
                await _pip(["uninstall", "-y", *leftovers], UNINSTALL_TIMEOUT)
                importlib.invalidate_caches()
            raise LibError(f"Kutubxona o'rnatilmadi ({', '.join(reqs)}):\n{_tail(out)}")
        return new


async def uninstall(names: list[str]) -> tuple[list[str], str]:
    """Kutubxonalarni o'chiradi (bot o'z kutubxonalaridan tashqari). (o'chirilganlar, xato matni) qaytaradi."""
    protected = core_names()
    names = sorted({norm(n) for n in names if n and norm(n) not in protected})
    if not names:
        return [], ""
    async with _LOCK:
        have = installed_map()
        names = [n for n in names if n in have]                    # allaqachon yo'q bo'lsa — kerak emas
        if not names:
            return [], ""
        rc, out = await _pip(["uninstall", "-y", *names], UNINSTALL_TIMEOUT)
        importlib.invalidate_caches()
        gone = [n for n in names if n not in installed_map()]
    return gone, ("" if rc == 0 else _tail(out))


# ───────── egalik (qaysi modul qaysi kutubxonani o'rnatgan) ─────────
def owned(ent: dict | None) -> list[str]:
    return [x["name"] for x in ((ent or {}).get("pip") or {}).get("installed", [])]


def add_record(ent: dict, needs: list[str], new: list[dict]) -> None:
    """Modul yozuviga (mods[nom]) kutubxonalar ma'lumotini qo'shadi (mavjudlarini saqlab)."""
    p = ent.setdefault("pip", {})
    p["needs"] = sorted(set(p.get("needs", [])) | set(needs))
    have = {x["name"] for x in p.get("installed", [])}
    p["installed"] = list(p.get("installed", [])) + [x for x in new if x["name"] not in have]
    if not p["needs"] and not p["installed"]:
        ent.pop("pip", None)


def release(mods: dict, name: str) -> list[str]:
    """Modul o'chirilayotganda: mods dan `name` ni olib tashlaydi va OCHIRILADIGAN kutubxonalar ro'yxatini qaytaradi.
    Boshqa modul ishlatayotgan kutubxona (yoki ularning bog'liqligi) o'chirilmaydi — egalik o'sha modulga o'tadi."""
    ent = mods.pop(name, None) or {}
    mine = {x["name"]: x for x in ((ent.get("pip") or {}).get("installed", []))}
    if not mine:
        return []
    deps = _deps_map()
    remaining = set(mine)
    for other, oe in mods.items():
        if not remaining:
            break
        op = oe.get("pip") or {}
        roots = set(op.get("needs", [])) | {x["name"] for x in op.get("installed", [])}
        if not roots:
            continue
        keep = remaining & closure(roots, deps)
        if keep:
            add_record(oe, [], [mine[k] for k in sorted(keep)])
            remaining -= keep
    return sorted(remaining)


def summary(ent: dict | None) -> str:
    """Qisqa matn: «pillow 10.1, qrcode 7.4» (shu modul o'rnatganlar)."""
    items = ((ent or {}).get("pip") or {}).get("installed", [])
    return ", ".join(f"{x['name']} {x.get('version', '')}".strip() for x in items)
