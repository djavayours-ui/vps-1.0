#!/usr/bin/env python3
"""Bot O'ZINI yangilaganda ishlaydigan alohida yordamchi (faqat standart kutubxona).

Nega kerak: bot o'z xizmatini `systemctl stop` qilsa, o'zini ham o'ldiradi va yangilash yarim yo'lda qoladi
(bot javob bermaydi). Shuning uchun fayllar almashtirilgach, qayta ishga tushirish va tekshiruvni shu skript
bot jarayonidan TASHQARIDA (systemd-run) bajaradi. Yangi kod ishlamasa — eski kod avtomatik tiklanadi.

Ishlatilishi: selfupdate.py <args.json>
"""
import json, os, re, shutil, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path

DB_RE = re.compile(r"\.(db|sqlite3?|session)(-\w+)?$")


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True, timeout=180)


def notify(cfg, text):
    for a in cfg.get("admins", []):
        try:
            data = urllib.parse.urlencode({"chat_id": a, "text": text}).encode()
            urllib.request.urlopen(f"https://api.telegram.org/bot{cfg['token']}/sendMessage", data, timeout=15)
        except Exception:
            pass


def probe(unit):
    kv = dict(l.split("=", 1) for l in sh("systemctl", "show", unit, "-p", "ActiveState,NRestarts").stdout.splitlines() if "=" in l)
    return kv.get("ActiveState", "inactive"), int(kv.get("NRestarts") or 0)


def healthy(unit, boot=40, stable=10):
    t0, n0 = time.time(), None
    while time.time() - t0 < boot:
        st, nr = probe(unit)
        if st == "active":
            n0 = nr
            break
        if st == "failed":
            return False, "xizmat 'failed' holatiga tushdi"
        time.sleep(0.5)
    if n0 is None:
        return False, f"{boot}s ichida ishga tushmadi"
    end = time.time() + stable
    while time.time() < end:
        time.sleep(1)
        st, nr = probe(unit)
        if st != "active" or nr > n0:
            return False, "ishga tushdi, lekin qulab tushdi (crash/restart loop)"
    return True, "ok"


def kept(p: Path, keep) -> bool:
    return p.name in keep or bool(DB_RE.search(p.name))


def restore(bak: Path, dst: Path, keep):
    for p in list(dst.iterdir()):
        if kept(p, keep):
            continue
        shutil.rmtree(p) if p.is_dir() and not p.is_symlink() else p.unlink()
    for p in bak.iterdir():
        if kept(p, keep) and (dst / p.name).exists():
            continue
        if p.is_dir() and not p.is_symlink():
            shutil.copytree(p, dst / p.name, symlinks=True)
        else:
            shutil.copy2(p, dst / p.name, follow_symlinks=False)


def main():
    cfgp = Path(sys.argv[1])
    cfg = json.loads(cfgp.read_text())
    cfgp.unlink(missing_ok=True)
    unit, d, bak, keep = cfg["unit"], Path(cfg["dir"]), Path(cfg["backup"]), set(cfg["keep"])
    time.sleep(cfg.get("delay", 4))                 # bot «yangilandi» xabarini ulgursin
    sh("systemctl", "restart", unit)
    ok, why = healthy(unit, stable=cfg.get("stable", 10))
    if ok:
        if os.getenv("KEEP_BACKUP", "0") != "1":
            shutil.rmtree(bak, ignore_errors=True)
        return
    notify(cfg, f"⚠️ Yangi kod ishlamadi ({why}). Eski kodga qaytarilmoqda…")
    sh("systemctl", "stop", unit)
    try:
        restore(bak, d, keep)
    except Exception as e:
        notify(cfg, f"❌ Tiklashda xato: {e}\nZaxira: {bak}")
        return
    sh("systemctl", "restart", unit)
    ok2, why2 = healthy(unit, stable=5)
    if ok2:
        shutil.rmtree(bak, ignore_errors=True)
        notify(cfg, "↩️ Eski kod tiklandi va ishlayapti. Yangi ZIP ichidagi xatoni tuzating.")
    else:
        notify(cfg, f"❌ Eski kod ham ishga tushmadi ({why2}). Serverda: journalctl -u {unit} -n 50\nZaxira: {bak}")


if __name__ == "__main__":
    main()
