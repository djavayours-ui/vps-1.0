"""Bitta nusxa himoyasi.

Bir xil BOT_TOKEN bilan ikkinchi bot ishga tushsa Telegram «Conflict: terminated by other getUpdates request»
beradi — ikkala nusxa ham bir-birini uzib, bot javob bermay qoladi (userbot sessiyasi esa Telegram tomonidan bekor
qilinishi mumkin). Bu modul qulf (flock) orqali shuni oldini oladi:

* qulf jarayon qanday o'lmasin (kill -9 ham) OS tomonidan o'zi bo'shatiladi — «qotib qolgan» qulf bo'lmaydi;
* eski nusxa qulfni bermasa: avval kutadi, so'ng uni o'zi to'xtatadi (systemd xizmati bo'lsa `systemctl stop`,
  aks holda SIGTERM → SIGKILL). Xizmat to'xtatiladi (restart qilinmaydi), shuning uchun «ping-pong» bo'lmaydi.
"""
import fcntl, hashlib, json, os, re, signal, subprocess, time
from pathlib import Path

GRACE = 8        # eski nusxa o'zi chiqishi uchun kutish (s)
TERM_WAIT = 12   # to'xtatish buyrug'idan keyin kutish (s)
_fd = None       # qulf ochiq turishi kerak — jarayon tugaguncha yopilmaydi


def _lock_path(token: str) -> Path:
    name = f"vpsbot-{hashlib.sha1(token.encode()).hexdigest()[:10]}.lock"
    for d in (Path("/var/tmp"), Path.home(), Path("/tmp")):   # /tmp/vpsbot (janitor tozalaydi) ishlatilmaydi
        try:
            if os.access(d, os.W_OK):
                return d / name
        except OSError:
            pass
    return Path("/tmp") / name


def unit_of(pid: int) -> str:
    """Jarayon qaysi systemd xizmatida ishlayotganini aniqlaydi ('' — xizmat emas, qo'lda ishga tushirilgan)."""
    try:
        txt = Path(f"/proc/{pid}/cgroup").read_text()
    except OSError:
        return ""
    m = re.findall(r"/([^/\n]+\.service)(?:/|$)", txt)
    return m[-1] if m else ""


def _is_bot(pid: int) -> bool:
    try:
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
    except OSError:
        return False
    return "bot.py" in cmd or "vpsbot" in cmd


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _read(fd) -> dict:
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        return json.loads(os.read(fd, 4096).decode() or "{}")
    except (OSError, ValueError):
        return {}


def _try_lock(fd) -> bool:
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False


def _evict(info: dict, force: bool) -> str:
    """Eski nusxani to'xtatadi; nima qilingani haqida matn qaytaradi."""
    pid = int(info.get("pid") or 0)
    if not pid or pid == os.getpid() or not _alive(pid) or not _is_bot(pid):
        return ""
    unit = unit_of(pid)
    if force:
        os.kill(pid, signal.SIGKILL)
        return f"PID {pid} majburan o'chirildi (javob bermadi)"
    if unit and unit != unit_of(os.getpid()):
        try:
            subprocess.run(["systemctl", "stop", unit], timeout=TERM_WAIT + 5, capture_output=True)
            return f"«{unit}» xizmati to'xtatildi (PID {pid})"
        except Exception:
            pass
    os.kill(pid, signal.SIGTERM)
    return f"PID {pid} to'xtatildi"


def acquire(token: str) -> str:
    """Qulfni oladi (kerak bo'lsa eski nusxani to'xtatib). Nima qilingan bo'lsa — matn, aks holda ''."""
    global _fd
    path = _lock_path(token)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    t0, did, stage = time.time(), "", 0
    while not _try_lock(fd):
        el = time.time() - t0
        info = _read(fd)
        if stage == 0 and el > GRACE:
            print(f"⚠️ Boshqa bot nusxasi ishlayapti ({info}) — to'xtatilmoqda...", flush=True)
            did, stage = _evict(info, False), 1
        elif stage == 1 and el > GRACE + TERM_WAIT:
            print("⚠️ Eski nusxa javob bermadi — majburan o'chirilmoqda", flush=True)
            did = (did + "; " if did else "") + _evict(info, True)
            stage = 2
        elif stage == 2 and el > GRACE + TERM_WAIT + 8:
            raise SystemExit("Eski bot nusxasi o'chmadi — serverda: pkill -9 -f bot.py")
        time.sleep(0.5)
    os.ftruncate(fd, 0)
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, json.dumps({"pid": os.getpid(), "unit": unit_of(os.getpid()), "t": int(time.time())}).encode())
    _fd = fd
    return did
